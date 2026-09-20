"""Compile local Music3 structured files into direct caption and lyrics text.

Standard library only. Reads local JSON and writes the requested output path.
It does not connect to a model service, validate a deployment, or submit a job.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def join_items(items: list[str]) -> str:
    return ", ".join(item.rstrip("。.") for item in items)


def compile_caption(spec: dict, lyrics: dict) -> str:
    global_data = spec["global"]
    vocal = spec["vocal"]
    arrangement = spec["arrangement"]
    tempo = global_data["bpm"] if global_data["tempo_mode"] == "bpm" else global_data["tempo_mode"]
    basic = f"{global_data['primary_genre']}"
    if global_data["fusion_genres"]:
        basic += " with " + ", ".join(global_data["fusion_genres"])
    basic += f"; {tempo or 'unspecified tempo'}"
    if global_data["key"]:
        basic += f"; {global_data['key']}"
    lines = [
        "Global Metadata",
        f"Basic Attributes: {basic}.",
        f"Global Emotional Progression: {global_data['primary_mood']}" + (f" with {join_items(global_data['secondary_moods'])}" if global_data["secondary_moods"] else "") + f"; {global_data['energy']}.",
        f"Application Scenarios & Imagery: {join_items(global_data['imagery']) or 'unspecified'}.",
        f"Sonics & Production Profile: {join_items(global_data['production']) or 'unspecified'}.",
        f"Creative Notes: {global_data['custom_notes'] or 'none'}.",
        "",
        "Vocal Details",
    ]
    if vocal["mode"] == "instrumental":
        lines.append("Instrumental track - No vocals.")
        lead = join_items(arrangement["primary_layers"]) or "an unspecified lead instrument"
        lines.append(f"The lead melodic role is carried by {lead}.")
    else:
        lines.extend([
            f"Vocal Gender & Timbre: {vocal['lead'] or 'unspecified'}" + (f"; {join_items(vocal['timbre'])}" if vocal["timbre"] else "") + ".",
            f"Vocal Style: {join_items(vocal['delivery']) or 'unspecified'}.",
            f"Harmony/Backing Vocals: {join_items(vocal['harmony']) or 'none specified'}.",
            f"Vocal FX: {join_items(vocal['effects']) or 'none specified'}.",
        ])
    lines.extend([
        "",
        "Arrangement",
        f"Arrangement Template: {arrangement['template_id'] or 'none specified'}.",
        f"Instrument Lifecycle Description (Primary/Secondary Layering): primary {join_items(arrangement['primary_layers']) or 'unspecified'}; secondary {join_items(arrangement['secondary_layers']) or 'unspecified'}.",
        f"Groove & Foundation Progression: {join_items(arrangement['foundation']) or 'unspecified'}.",
        f"Opening, Transitions, Climax & Spatial FX: {join_items(arrangement['transitions']) or 'unspecified'}.",
    ])
    development = []
    for section in lyrics["sections"]:
        development.append(f"[{section['tag']}]: {section['music_intent']}")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="Output JSON path; refuses overwrite")
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    spec = json.loads((bundle / "creative_spec.json").read_text(encoding="utf-8"))
    lyrics = json.loads((bundle / "lyrics_document.json").read_text(encoding="utf-8"))
    result = {
        "caption": compile_caption(spec, lyrics),
        "lyrics": compile_lyrics(lyrics),
    }
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"written": str(args.out.resolve()), "generation_submitted": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
