"""Compile local Music3 structured files into direct caption and lyrics text.

Standard library only. Reads local JSON and writes the requested output path.
It does not connect to a model service, validate a deployment, or submit a job.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from validate_bundle import ValidationError, validate_lyrics, validate_spec

TAGS = {
    "Intro",
    "Verse",
    "Pre-Chorus",
    "Chorus",
    "Post-Chorus",
    "Bridge",
    "Instrumental",
    "Solo",
    "Outro",
}
MAX_CAPTION_LENGTH = 12_000
MAX_LYRICS_LENGTH = 20_000
REPEAT_PLACEHOLDER = re.compile(r"\s*(同上|副歌\s*[xX×*]\s*\d+|repeat chorus)\s*", re.I)
TERMINAL_PUNCTUATION = "。.?!！？;；:：,，"


class CompileError(ValueError):
    """Raised when a bundle cannot produce a valid direct Music3 input."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CompileError(message)


def text_value(
    value,
    path: str,
    *,
    allow_empty: bool = False,
    strip_terminal: bool = False,
    max_length: int | None = None,
) -> str:
    require(isinstance(value, str), f"{path} must be a string")
    require("\r" not in value and "\n" not in value, f"{path} must not contain CR/LF")
    result = value.strip()
    if not allow_empty:
        require(bool(result), f"{path} must not be empty")
    if strip_terminal:
        result = result.rstrip(TERMINAL_PUNCTUATION).rstrip()
        require(allow_empty or bool(result), f"{path} must contain non-punctuation text")
    return result


def list_values(
    value,
    path: str,
    *,
    max_length: int = 1000,
    unique: bool = False,
) -> list[str]:
    require(isinstance(value, list), f"{path} must be an array")
    result = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        text = text_value(item, item_path, strip_terminal=True, max_length=max_length)
        result.append(text)
    if unique:
        require(len(result) == len(set(result)), f"{path} must not contain duplicate items")
    return result


def join_items(items, path: str) -> str:
    return ", ".join(list_values(items, path))


def validate_inputs(spec: dict, lyrics: dict) -> None:
    require(isinstance(spec, dict), "creative_spec must be an object")
    require(isinstance(lyrics, dict), "lyrics_document must be an object")
    require(isinstance(spec.get("global"), dict), "creative_spec.global must be an object")
    require(isinstance(spec.get("vocal"), dict), "creative_spec.vocal must be an object")
    require(isinstance(spec.get("arrangement"), dict), "creative_spec.arrangement must be an object")
    require(spec["vocal"].get("mode") in {"vocal", "instrumental"}, "vocal.mode must be vocal or instrumental")

    global_data = spec["global"]
    text_value(global_data.get("primary_genre"), "global.primary_genre", strip_terminal=True, max_length=100)
    text_value(global_data.get("primary_mood"), "global.primary_mood", strip_terminal=True, max_length=100)
    list_values(global_data.get("fusion_genres"), "global.fusion_genres", max_length=100, unique=True)
    require(len(global_data["fusion_genres"]) <= 3, "global.fusion_genres cannot contain more than 3 items")
    list_values(global_data.get("secondary_moods"), "global.secondary_moods", max_length=100, unique=True)
    require(global_data.get("tempo_mode") in {"slow", "medium", "fast", "bpm", None}, "global.tempo_mode is invalid")
    if global_data.get("tempo_mode") == "bpm":
        require(type(global_data.get("bpm")) is int and 20 <= global_data["bpm"] <= 300, "global.bpm must be 20-300 in bpm mode")
    if global_data.get("key") is not None:
        text_value(global_data["key"], "global.key", strip_terminal=True, max_length=100)
    if global_data.get("energy") is not None:
        text_value(global_data["energy"], "global.energy", strip_terminal=True, max_length=100)
    list_values(global_data.get("imagery"), "global.imagery", max_length=300)
    list_values(global_data.get("production"), "global.production", max_length=300, unique=True)
    require(isinstance(global_data.get("custom_notes"), str), "global.custom_notes must be a string")
    text_value(global_data["custom_notes"], "global.custom_notes", allow_empty=True, strip_terminal=True, max_length=4000)

    vocal = spec["vocal"]
    if vocal["mode"] == "instrumental":
        require(vocal.get("lead") is None, "instrumental vocal.lead must be null")
        for name in ("timbre", "delivery", "harmony", "effects"):
            require(vocal.get(name) == [], f"instrumental vocal.{name} must be empty")
    else:
        if vocal.get("lead") is not None:
            text_value(vocal["lead"], "vocal.lead", strip_terminal=True, max_length=100)
        for name, max_length in (("timbre", 200), ("delivery", 300), ("harmony", 300), ("effects", 300)):
            list_values(vocal.get(name), f"vocal.{name}", max_length=max_length, unique=True)

    arrangement = spec["arrangement"]
    if arrangement.get("template_id") is not None:
        text_value(arrangement["template_id"], "arrangement.template_id", strip_terminal=True, max_length=100)
    for name in ("primary_layers", "secondary_layers", "foundation", "transitions"):
        list_values(arrangement.get(name), f"arrangement.{name}", max_length=1000)

    require(isinstance(lyrics.get("sections"), list) and lyrics["sections"], "lyrics.sections must contain at least one section")
    for index, section in enumerate(lyrics["sections"]):
        path = f"sections[{index}]"
        require(isinstance(section, dict), f"{path} must be an object")
        require(section.get("tag") in TAGS, f"{path}.tag is not a supported Music3 tag")
        require(type(section.get("instrumental")) is bool, f"{path}.instrumental must be boolean")
        intent = text_value(section.get("music_intent"), f"{path}.music_intent", allow_empty=True, strip_terminal=True)
        require(len(intent) <= 1000, f"{path}.music_intent exceeds 1000 characters")
        lines = section.get("lines")
        require(isinstance(lines, list), f"{path}.lines must be an array")
        if section["instrumental"]:
            require(not lines, f"{path}.lines must be empty for instrumental sections")
        else:
            require(vocal["mode"] == "vocal", f"{path} contains vocal text in an instrumental bundle")
            require(lines, f"{path}.lines must contain lyric lines")
            for line_index, line in enumerate(lines):
                line_path = f"{path}.lines[{line_index}]"
                text = text_value(line, line_path)
                require(len(text) <= 1000, f"{line_path} exceeds 1000 characters")
                require(not REPEAT_PLACEHOLDER.fullmatch(text), f"{line_path} must expand repeated lyrics")
    if vocal["mode"] == "instrumental":
        require(all(section["instrumental"] for section in lyrics["sections"]), "instrumental bundle cannot contain vocal sections")


def compile_caption(spec: dict, lyrics: dict) -> str:
    global_data = spec["global"]
    vocal = spec["vocal"]
    arrangement = spec["arrangement"]
    tempo = global_data["bpm"] if global_data["tempo_mode"] == "bpm" else global_data["tempo_mode"]
    basic = text_value(global_data["primary_genre"], "global.primary_genre", strip_terminal=True)
    fusion = join_items(global_data["fusion_genres"], "global.fusion_genres")
    if fusion:
        basic += " with " + fusion
    basic += f"; {tempo or 'unspecified tempo'}"
    if global_data["key"]:
        basic += f"; {text_value(global_data['key'], 'global.key', strip_terminal=True)}"

    secondary_moods = join_items(global_data["secondary_moods"], "global.secondary_moods")
    energy = text_value(global_data["energy"], "global.energy", strip_terminal=True)
    imagery = join_items(global_data["imagery"], "global.imagery") or "unspecified"
    production = join_items(global_data["production"], "global.production") or "unspecified"
    notes = text_value(global_data["custom_notes"], "global.custom_notes", allow_empty=True, strip_terminal=True) or "none"

    lines = [
        "Global Metadata",
        f"Basic Attributes: {basic}.",
        f"Global Emotional Progression: {text_value(global_data['primary_mood'], 'global.primary_mood', strip_terminal=True)}" + (f" with {secondary_moods}" if secondary_moods else "") + f"; {energy}.",
        f"Application Scenarios & Imagery: {imagery}.",
        f"Sonics & Production Profile: {production}.",
        f"Creative Notes: {notes}.",
        "",
        "Vocal Details",
    ]
    if vocal["mode"] == "instrumental":
        lead = join_items(arrangement["primary_layers"], "arrangement.primary_layers") or "an unspecified lead instrument"
        lines.extend(["Instrumental track - No vocals.", f"Lead melodic role: {lead}."])
    else:
        lead = text_value(vocal["lead"], "vocal.lead", strip_terminal=True) if vocal["lead"] else "unspecified"
        timbre = join_items(vocal["timbre"], "vocal.timbre")
        delivery = join_items(vocal["delivery"], "vocal.delivery") or "unspecified"
        harmony = join_items(vocal["harmony"], "vocal.harmony") or "none specified"
        effects = join_items(vocal["effects"], "vocal.effects") or "none specified"
        lines.extend([
            f"Vocal Gender & Timbre: {lead}" + (f"; {timbre}" if timbre else "") + ".",
            f"Vocal Style: {delivery}.",
            f"Harmony/Backing Vocals: {harmony}.",
            f"Vocal FX: {effects}.",
        ])
    primary = join_items(arrangement["primary_layers"], "arrangement.primary_layers") or "unspecified"
    secondary = join_items(arrangement["secondary_layers"], "arrangement.secondary_layers") or "unspecified"
    foundation = join_items(arrangement["foundation"], "arrangement.foundation") or "unspecified"
    transitions = join_items(arrangement["transitions"], "arrangement.transitions") or "unspecified"
    template = text_value(arrangement["template_id"], "arrangement.template_id", strip_terminal=True) if arrangement["template_id"] else "none specified"
    lines.extend([
        "",
        "Arrangement",
        f"Arrangement Template: {template}.",
        f"Instrument Lifecycle Description (Primary/Secondary Layering): Primary - {primary}; Secondary - {secondary}.",
        f"Groove & Foundation Progression: {foundation}.",
        f"Opening, Transitions, Climax & Spatial FX: {transitions}.",
    ])
    development = []
    for index, section in enumerate(lyrics["sections"]):
        intent = text_value(section["music_intent"], f"sections[{index}].music_intent", allow_empty=True, strip_terminal=True) or "no additional development"
        development.append(f"[{section['tag']}]: {intent}")
    lines.append("Section-by-Section Development: " + "; ".join(development) + ".")
    return "\n".join(lines)


def compile_lyrics(lyrics: dict) -> str:
    chunks = []
    for section in lyrics["sections"]:
        chunks.append(f"[{section['tag']}]")
        if section["instrumental"]:
            chunks.append("(instrumental)")
        else:
            chunks.extend(section["lines"])
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def compile_bundle(spec: dict, lyrics: dict) -> dict[str, str]:
    validate_inputs(spec, lyrics)
    result = {"caption": compile_caption(spec, lyrics), "lyrics": compile_lyrics(lyrics)}
    require(1 <= len(result["caption"]) <= MAX_CAPTION_LENGTH, f"caption length {len(result['caption'])} exceeds {MAX_CAPTION_LENGTH}")
    require(1 <= len(result["lyrics"]) <= MAX_LYRICS_LENGTH, f"lyrics length {len(result['lyrics'])} exceeds {MAX_LYRICS_LENGTH}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="Output JSON path; refuses overwrite")
    args = parser.parse_args()
    try:
        bundle = args.bundle.resolve()
        spec = json.loads((bundle / "creative_spec.json").read_text(encoding="utf-8"))
        lyrics = json.loads((bundle / "lyrics_document.json").read_text(encoding="utf-8"))
        result = compile_bundle(spec, lyrics)
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(json.dumps({"written": str(args.out.resolve()), "caption_chars": len(result["caption"]), "lyrics_chars": len(result["lyrics"]), "generation_submitted": False}, ensure_ascii=False))
        return 0
    except (CompileError, json.JSONDecodeError, OSError, TypeError, KeyError) as error:
        print(json.dumps({"valid": False, "error": str(error), "generation_submitted": False}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
