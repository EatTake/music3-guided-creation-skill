"""Validate a Music3 guided-creation bundle. Standard library only; read-only; no network."""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
TOP_SPEC = {"schema_version", "project_id", "revision", "global", "vocal", "arrangement"}
GLOBAL_FIELDS = {
    "primary_genre",
    "fusion_genres",
    "primary_mood",
    "secondary_moods",
    "tempo_mode",
    "bpm",
    "key",
    "energy",
    "imagery",
    "production",
    "custom_notes",
}
VOCAL_FIELDS = {"mode", "lead", "timbre", "delivery", "harmony", "effects"}
ARRANGEMENT_FIELDS = {
    "template_id",
    "primary_layers",
    "secondary_layers",
    "foundation",
    "transitions",
    "section_development",
}
SECTION_FIELDS = {"section_id", "tag", "title", "instrumental", "lines", "music_intent"}
GENERATION_FIELDS = {
    "duration_mode",
    "duration_seconds",
    "seed_mode",
    "seed",
    "versions",
    "fade_out_seconds",
}
REPEAT_PLACEHOLDER = re.compile(r"\s*(同上|副歌\s*[xX×*]\s*\d+|repeat chorus)\s*", re.I)
NEGATIVE_TERMS = re.compile(r"\b(BPM|model|seed|CFG|Top-K|API|shell)\b|模型|文件路径", re.I)


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path):
    path = path.resolve()
    require(path.is_file(), f"Missing file: {path.name}")
    require(path.stat().st_size <= 2_000_000, f"File exceeds 2 MB: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def find_file(directory: Path, exact_name: str, suffix: str) -> Path:
    exact = directory / exact_name
    if exact.is_file():
        return exact
    matches = sorted(directory.glob(f"*.{suffix}"))
    require(len(matches) == 1, f"Expected one *.{suffix}; found {len(matches)}")
    return matches[0]


def is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def string_list(value, name: str, max_length: int, *, unique: bool = False) -> None:
    require(isinstance(value, list), f"{name} must be an array")
    require(
        all(isinstance(item, str) and item.strip() and len(item) <= max_length and "\n" not in item and "\r" not in item for item in value),
        f"Invalid {name} item",
    )
    if unique:
        require(len(value) == len(set(value)), f"Duplicate {name} item")


def validate_guidance(guidance, policy) -> None:
    require(isinstance(guidance, dict), "guidance must be an object")
    require(set(guidance) == {"version", "song_id", "stages", "draft"}, "guidance fields mismatch")
    require(guidance["version"] == "1.0", "Unsupported guidance version")
    require(isinstance(guidance["song_id"], str) and re.fullmatch(r"[A-Za-z0-9_-]+", guidance["song_id"]), "Unsafe song_id")
    require(isinstance(guidance["stages"], dict) and set(guidance["stages"]) == {"intent", "music_design"}, "Invalid stages")

    for stage_name in ("intent", "music_design"):
        stage = guidance["stages"][stage_name]
        rule = policy[stage_name]
        require(isinstance(stage, dict) and set(stage) == {"questions", "confirmed"}, f"Invalid {stage_name} stage")
        require(stage["confirmed"] is True, f"{stage_name} summary is not confirmed")
        require(isinstance(stage["questions"], list), f"{stage_name}.questions must be an array")
        ids = set()
        counted = []
        for question in stage["questions"]:
            expected = {"id", "dimension", "question", "answer", "source", "asked", "resolved", "recommendation_status"}
            require(isinstance(question, dict) and set(question) == expected, f"Invalid {stage_name} question fields")
            require(isinstance(question["id"], str) and question["id"] and question["id"] not in ids, f"Duplicate question id in {stage_name}")
            ids.add(question["id"])
            require(isinstance(question["dimension"], str) and question["dimension"], f"Missing dimension in {stage_name}")
            require(isinstance(question["question"], str) and question["question"].strip(), f"Missing question text in {stage_name}")
            require(isinstance(question["answer"], str) and question["answer"].strip(), f"Missing answer in {stage_name}")
            require(question["source"] in {"user_answer", "confirmed_existing", "prefilled"}, f"Invalid answer source in {stage_name}")
            require(type(question["asked"]) is bool and type(question["resolved"]) is bool, f"Invalid question state in {stage_name}")
            require(question["recommendation_status"] in {"not_applicable", "pending", "confirmed"}, f"Invalid recommendation status in {stage_name}")
            if question["source"] == "prefilled":
                require(not question["asked"], f"Prefilled information cannot count as an asked question in {stage_name}")
            if question["asked"]:
                require(question["source"] in {"user_answer", "confirmed_existing"}, f"Asked question must have user-backed source in {stage_name}")
                require(question["resolved"], f"Asked question is unresolved in {stage_name}")
                counted.append(question)
        minimum = max(rule["minimum_questions"], len(rule["required_dimensions"]))
        require(len(counted) >= minimum, f"{stage_name} has {len(counted)} counted questions; needs {minimum}")
        coverage = {item["dimension"] for item in counted}
        require(set(rule["required_dimensions"]) <= coverage, f"{stage_name} missing required dimensions")
        require(not any(item["recommendation_status"] == "pending" for item in stage["questions"]), f"{stage_name} has pending recommendations")

    draft = guidance["draft"]
    require(isinstance(draft, dict) and set(draft) == {"accepted", "generation_authorized"}, "Invalid draft state")
    require(type(draft["accepted"]) is bool and type(draft["generation_authorized"]) is bool, "Draft flags must be booleans")
    require(not draft["generation_authorized"] or draft["accepted"], "Generation cannot be authorized before draft acceptance")


def validate_spec(spec, warnings) -> None:
    require(isinstance(spec, dict) and set(spec) == TOP_SPEC, "creative_spec fields mismatch")
    require(spec["schema_version"] == "2.0", "Unsupported creative_spec version")
    require(is_uuid(spec["project_id"]), "project_id must be a UUID")
    require(type(spec["revision"]) is int and spec["revision"] >= 0, "Invalid revision")

    global_data = spec["global"]
    require(isinstance(global_data, dict) and set(global_data) == GLOBAL_FIELDS, "global fields mismatch")
    require(isinstance(global_data["primary_genre"], str) and global_data["primary_genre"].strip() and len(global_data["primary_genre"]) <= 100 and "\n" not in global_data["primary_genre"] and "\r" not in global_data["primary_genre"], "Invalid primary_genre")
    require(isinstance(global_data["primary_mood"], str) and global_data["primary_mood"].strip() and len(global_data["primary_mood"]) <= 100 and "\n" not in global_data["primary_mood"] and "\r" not in global_data["primary_mood"], "Invalid primary_mood")
    string_list(global_data["fusion_genres"], "fusion_genres", 100, unique=True)
    require(len(global_data["fusion_genres"]) <= 3, "Too many fusion_genres")
    string_list(global_data["secondary_moods"], "secondary_moods", 100, unique=True)
    require(global_data["tempo_mode"] in {"slow", "medium", "fast", "bpm", None}, "Invalid tempo_mode")
    if global_data["tempo_mode"] == "bpm":
        require(type(global_data["bpm"]) is int and 20 <= global_data["bpm"] <= 300, "bpm mode needs BPM 20-300")
    else:
        require(global_data["bpm"] is None, "bpm must be null unless tempo_mode is bpm")
    require(global_data["key"] is None or (isinstance(global_data["key"], str) and len(global_data["key"]) <= 100 and global_data["key"].strip() and "\n" not in global_data["key"] and "\r" not in global_data["key"]), "Invalid key")
    require(global_data["energy"] is None or (isinstance(global_data["energy"], str) and len(global_data["energy"]) <= 100 and global_data["energy"].strip() and "\n" not in global_data["energy"] and "\r" not in global_data["energy"]), "Invalid energy")
    string_list(global_data["imagery"], "imagery", 300)
    string_list(global_data["production"], "production", 300)
    require(isinstance(global_data["custom_notes"], str) and len(global_data["custom_notes"]) <= 4000 and "\n" not in global_data["custom_notes"] and "\r" not in global_data["custom_notes"], "Invalid custom_notes")

    vocal = spec["vocal"]
    require(isinstance(vocal, dict) and set(vocal) == VOCAL_FIELDS, "vocal fields mismatch")
    require(vocal["mode"] in {"vocal", "instrumental"}, "Invalid vocal mode")
    require(vocal["lead"] is None or (isinstance(vocal["lead"], str) and len(vocal["lead"]) <= 100 and vocal["lead"].strip() and "\n" not in vocal["lead"] and "\r" not in vocal["lead"]), "Invalid lead")
    for name, limit in (("timbre", 200), ("delivery", 300), ("harmony", 300), ("effects", 300)):
        string_list(vocal[name], name, limit, unique=True)
    if vocal["mode"] == "instrumental":
        require(vocal["lead"] is None and not any(vocal[name] for name in ("timbre", "delivery", "harmony", "effects")), "Instrumental mode must clear vocal settings")

    arrangement = spec["arrangement"]
    require(isinstance(arrangement, dict) and set(arrangement) == ARRANGEMENT_FIELDS, "arrangement fields mismatch")
    require(arrangement["template_id"] is None or (isinstance(arrangement["template_id"], str) and len(arrangement["template_id"]) <= 100 and arrangement["template_id"].strip() and "\n" not in arrangement["template_id"] and "\r" not in arrangement["template_id"]), "Invalid template_id")
    for name in ("primary_layers", "secondary_layers", "foundation", "transitions", "section_development"):
        string_list(arrangement[name], name, 1000)
    require(not arrangement["section_development"], "section_development must be empty; use lyrics music_intent")

    list_fields = [
        *global_data["imagery"],
        *global_data["production"],
        *vocal["timbre"],
        *vocal["delivery"],
        *vocal["harmony"],
        *vocal["effects"],
        *arrangement["primary_layers"],
        *arrangement["secondary_layers"],
        *arrangement["foundation"],
        *arrangement["transitions"],
    ]
    if any(item.rstrip().endswith((".", "。")) for item in list_fields):
        warnings.append("A list item ends with punctuation; a compiler may add duplicate punctuation")


def validate_lyrics(lyrics, vocal_mode: str, warnings) -> None:
    require(isinstance(lyrics, dict) and set(lyrics) == {"schema_version", "language", "sections"}, "lyrics_document fields mismatch")
    require(lyrics["schema_version"] == "2.0", "Unsupported lyrics version")
    require(isinstance(lyrics["language"], str) and lyrics["language"].strip() and 2 <= len(lyrics["language"]) <= 35 and "\n" not in lyrics["language"] and "\r" not in lyrics["language"], "Invalid language")
    require(isinstance(lyrics["sections"], list) and lyrics["sections"], "At least one section is required")
    if vocal_mode == "instrumental":
        require(lyrics["language"] == "und", "Instrumental language must be und")
    ids = set()
    for section in lyrics["sections"]:
        require(isinstance(section, dict) and set(section) == SECTION_FIELDS, "Section fields mismatch")
        require(is_uuid(section["section_id"]) and section["section_id"] not in ids, "Invalid or duplicate section_id")
        ids.add(section["section_id"])
        require(section["tag"] in TAGS, "Unsupported section tag")
        require(isinstance(section["title"], str) and len(section["title"]) <= 200 and "\n" not in section["title"] and "\r" not in section["title"], "Invalid section title")
        require(type(section["instrumental"]) is bool, "instrumental must be boolean")
        require(isinstance(section["lines"], list), "lines must be an array")
        require(isinstance(section["music_intent"], str) and len(section["music_intent"]) <= 1000, "Invalid music_intent")
        if section["instrumental"]:
            require(not section["lines"], "Instrumental section must have empty lines")
        else:
            require(vocal_mode == "vocal", "Instrumental spec cannot contain vocal sections")
            require(section["lines"], "Vocal section needs lyric lines")
        for line in section["lines"]:
            require(isinstance(line, str) and line.strip() and len(line) <= 1000 and "\n" not in line and "\r" not in line, "Invalid lyric line")
            require(not REPEAT_PLACEHOLDER.fullmatch(line), "Repeat placeholders must be expanded")
            if NEGATIVE_TERMS.search(line):
                warnings.append(f"Technical term found in lyric line: {line}")


def validate_generation(request) -> None:
    require(isinstance(request, dict) and set(request) == GENERATION_FIELDS, "generation_request fields mismatch")
    require(request["duration_mode"] in {"auto", "target"}, "Invalid duration_mode")
    if request["duration_mode"] == "auto":
        require(request["duration_seconds"] is None, "auto requires duration_seconds=null")
    else:
        seconds = request["duration_seconds"]
        require(type(seconds) is int and 10 <= seconds <= 300 and seconds % 10 == 0, "target duration must be a 10-second step from 10 to 300")
    require(request["seed_mode"] in {"random", "fixed"}, "Invalid seed_mode")
    if request["seed_mode"] == "random":
        require(request["seed"] is None, "random seed_mode requires seed=null")
    else:
        require(type(request["seed"]) is int and 0 <= request["seed"] <= 2147483647, "Invalid fixed seed")
    require(type(request["versions"]) is int and 1 <= request["versions"] <= 8, "Invalid versions")
    require(isinstance(request["fade_out_seconds"], (int, float)) and not isinstance(request["fade_out_seconds"], bool) and 0 <= request["fade_out_seconds"] <= 30, "Invalid fade_out_seconds")


def validate_bundle(directory: Path):
    directory = directory.resolve()
    require(directory.is_dir(), "Bundle path must be a directory")
    policy = load_json(ROOT / "references" / "interaction-policy.json")
    paths = {
        "guidance": find_file(directory, "guidance.json", "guidance.json"),
        "creative_spec": find_file(directory, "creative_spec.json", "creative_spec.json"),
        "lyrics_document": find_file(directory, "lyrics_document.json", "lyrics_document.json"),
        "generation_request": find_file(directory, "generation_request.json", "generation_request.json"),
    }
    guidance = load_json(paths["guidance"])
    spec = load_json(paths["creative_spec"])
    lyrics = load_json(paths["lyrics_document"])
    generation = load_json(paths["generation_request"])
    warnings = []
    validate_guidance(guidance, policy)
    validate_spec(spec, warnings)
    validate_lyrics(lyrics, spec["vocal"]["mode"], warnings)
    validate_generation(generation)
    return {
        "valid": True,
        "song_id": guidance["song_id"],
        "sections": len(lyrics["sections"]),
        "draft_accepted": guidance["draft"]["accepted"],
        "generation_authorized": guidance["draft"]["generation_authorized"],
        "warnings": warnings,
        "files": {name: path.name for name, path in paths.items()},
        "network_used": False,
        "files_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Directory containing the four bundle JSON files")
    args = parser.parse_args()
    try:
        print(json.dumps(validate_bundle(args.bundle), ensure_ascii=False, indent=2))
        return 0
    except (ValidationError, json.JSONDecodeError, OSError, TypeError, KeyError) as error:
        print(json.dumps({"valid": False, "error": str(error), "network_used": False, "files_written": False}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
