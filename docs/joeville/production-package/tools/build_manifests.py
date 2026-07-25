#!/usr/bin/env python3
"""Build deterministic Joeville production manifests from the approved set roster.

This generates planning artifacts only; it does not modify the visualizer.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SETS = [
    ("TWN", "Joeville Town", "Townwide", "overview, montage, geographic orientation", 13),
    ("COF", "Lantern & Lark Coffee", "Downtown", "intimacy, work, comic ordering", 5),
    ("CHA", "Grace Meadow and Assembly Hall", "Meadow", "community, picnics, trail departure", 13),
    ("FAL", "Joeville Falls", "Canyon", "wonder, intimacy, reflection", 5),
    ("MED", "Thirteen Stones Meditation Circle", "Castle Ridge", "ritual, reflection, council", 13),
    ("DAN", "Current Hall", "Creek Corridor", "ecstatic dance, celebration, decompression", 13),
    ("TRL", "Foothill Trail System", "Mountain", "walking dialogue, challenge, discovery", 5),
    ("CAS", "Castle Grace", "Castle Ridge", "home base, council, feast, celebration", 13),
    ("PRL", "Lantern Walk", "Downtown", "public life, shopping, buskers, encounters", 13),
    ("JUI", "Brightroot Juice Bar", "Wellness", "quick meetings, healthy ritual, comedy", 5),
    ("TON", "Juniper Tonic House", "Wellness", "intimate counsel, apothecary ritual", 5),
    ("SUS", "Riverstone Sushi", "Creek Corridor", "meals, dates, ensemble celebration", 13),
    ("GRO", "Joeville Commons Market", "Wellness", "shopping, chance encounters, errands", 8),
    ("CRK", "Joeville Creek Path", "Creek Corridor", "walking dialogue and transitions", 5),
    ("RES", "Sunward Residential Street", "Residential", "home transitions, quiet daily life", 5),
    ("PLZ", "Civic Weave Plaza", "Downtown", "public gathering, announcements, ensemble", 13),
    ("BRG", "Rainbow Footbridge", "Creek Corridor", "crossing, meeting, visual transition", 5),
    ("OVR", "Westlight Overlook", "Mountain", "reflection, town POV, sunset", 5),
    ("TRH", "Meadow Trailhead", "Meadow", "arrival, parking, gear, departures", 8),
    ("ENT", "Joeville East Gate", "Residential", "town arrival and departure", 13),
]

ANGLES = [
    ("EST-EW", "extreme-wide establishing", "24mm-equivalent elevated", "large center-safe ensemble zone"),
    ("EXT-MAS", "exterior master", "28mm-equivalent eye-level", "arrival path and doorway clear"),
    ("EXT-REV", "exterior reverse", "35mm-equivalent eye-level", "departure path and town orientation clear"),
    ("INT-MAS", "interior or primary-area master", "28mm-equivalent", "full walkable floor and all exits visible"),
    ("INT-REV", "reverse master", "32mm-equivalent", "reverse eyelines and window continuity"),
    ("DLG-2S", "clean dialogue two-shot", "50mm-equivalent", "two 34x52-cell figures plus gesture clearance"),
    ("DLG-OTS-L", "clean over-shoulder left", "65mm-equivalent", "left foreground occluder delivered separately"),
    ("DLG-OTS-R", "clean over-shoulder right", "65mm-equivalent", "right foreground occluder delivered separately"),
    ("DLG-GRP", "three-to-five group dialogue", "40mm-equivalent", "five anchors with non-crossing eyelines"),
    ("ENS-13", "full-cast ensemble master", "28mm-equivalent", "thirteen anchors; only where capacity allows"),
    ("MOVE-LR", "side-tracking movement plate", "35mm orthogonal-feel", "unbroken lateral path across 70 percent width"),
    ("POV", "character point of view", "45mm-equivalent", "no baked character; clear focal subject"),
    ("INS-SGN", "controlled signage insert", "70mm-equivalent", "blank sign substrate for graphic pass"),
    ("CLN", "empty clean plate", "matching master lens", "no people or characters; restoration-ready"),
]

TIMES = [("DAY", "clear late-morning"), ("GOLD", "golden hour"), ("NIGHT", "blue-hour-to-night")]

CLIP_CLASSES = [
    ("MIC", 3, "micro insert", "non-looping", "subtle local action"),
    ("EST", 8, "establishing move", "non-looping", "slow push or drift"),
    ("AMB", 16, "ambient loop", "seamless", "foliage, water, practical light only"),
    ("DLG", 24, "dialogue loop", "seamless", "very low-amplitude background motion"),
    ("LONG", 45, "long environmental loop", "seamless", "meditative non-distracting motion"),
    ("TRV", 10, "travel transition", "non-looping", "forward or lateral camera travel"),
]

BASE_STYLE = (
    "stylized square-cell voxel/ASCII production environment matching Wizard Joe's crisp grid logic; "
    "orthogonal stepped silhouettes, matte local-color blocks, sparse highlight glyph texture, readable depth, "
    "Boulder-inspired foothill light, no photoreal microtexture"
)
NEGATIVE = (
    "no people, no characters, no Wizard Joe, no logos, no trademarked signage, no generated readable text, "
    "no warped furniture, no impossible stairs, no broken perspective, no blocked walking floor, no random castle changes, "
    "no dense visual noise behind dialogue zones, no watermark"
)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def shot_rows() -> list[dict[str, object]]:
    rows = []
    for sid, name, district, function, capacity in SETS:
        for angle, shot, lens, safe in ANGLES:
            if angle == "ENS-13" and capacity < 13:
                continue
            for time_code, light in (TIMES if angle in {"EST-EW", "EXT-MAS", "INT-MAS", "CLN"} else TIMES[:1]):
                shot_id = f"JV-{sid}-STL-{angle}-{time_code}-V001"
                rows.append({
                    "shot_id": shot_id, "set_id": f"JV-{sid}", "set_name": name, "district": district,
                    "shot_class": shot, "camera": lens, "time": light, "season": "summer master",
                    "dramatic_use": function, "cast_capacity": capacity, "character_safe_area": safe,
                    "ground_horizon": "author against runtime projection; provisional horizon 56% until integration upgrade",
                    "layers": "far_bg|bg|midground|character_plane|foreground|fx|lighting|shadow",
                    "clean_plate": "required", "status": "PLANNED-NOT-CREATED",
                })
    return rows


def clip_rows() -> list[dict[str, object]]:
    rows = []
    for sid, name, district, function, capacity in SETS:
        for code, duration, klass, loop, movement in CLIP_CLASSES:
            clip_id = f"JV-{sid}-CLP-{code}-DAY-SUM-V001"
            rows.append({
                "clip_id": clip_id, "set_id": f"JV-{sid}", "set_name": name, "class": klass,
                "description": f"{name} {klass}", "dramatic_use": function, "camera_behavior": movement,
                "duration_seconds": duration, "looping": loop, "fps": 24, "master_resolution": "3840x2160",
                "character_safe_area": "center/lower stage remains unobstructed; follow matching still master",
                "foreground_motion": "separate optional pass", "background_motion": "wind/water/practicals as applicable",
                "lighting_change": "none for loops; motivated only for transition", "weather_fx": "separate optional pass",
                "sound_suggestion": f"location-authentic {district.lower()} ambience",
                "required_source_art": "approved layered master plus clean plate", "generation_method": "2.5D multiplane or controlled video generation",
                "visualizer_compatibility": "REQUIRES RUNTIME UPGRADE: current verified runtime accepts procedural cell frames, not environment video",
                "transition_requirement": "first/last frames match for loops; 8-frame handles for editorial", "status": "PLANNED-NOT-CREATED",
            })
    return rows


def location_rows() -> list[dict[str, object]]:
    rows = []
    for sid, name, district, function, capacity in SETS:
        rows.append({
            "set_id": f"JV-{sid}", "set_name": name, "district": district, "narrative_function": function,
            "fictionalization": "fictional Boulder-inspired analogue", "architecture": "low-rise regional masonry/wood with stepped square-cell silhouette",
            "palette": "sandstone|ponderosa|creek-blue|sun-gold|night-indigo|rainbow accent <=5%",
            "materials": "local-stone analogue|warm brick|dark steel|weathered wood|clear glass|woven textiles",
            "entrances_exits": "minimum two readable routes; hero entry plus service/continuity exit",
            "dialogue_zones": "intimate 2-shot zone|3-5 group zone|standing transition zone",
            "group_capacity": capacity, "camera_positions": "master|reverse|two OTS|profile|movement axis|insert",
            "variants": "day|golden|night|rain|snow|spring|summer|autumn|winter as relevant",
            "legal": "no real trade dress or copied private interior; clear reference license before direct use",
            "status": "DESIGN-SPECIFIED; ART-PENDING",
        })
    return rows


def blocking_rows() -> list[dict[str, object]]:
    rows = []
    for sid, name, _district, _function, capacity in SETS:
        for cast in (1, 2, 3, 5, 8, 13):
            feasible = cast <= capacity
            rows.append({
                "set_id": f"JV-{sid}", "set_name": name, "cast_size": cast,
                "feasible": "yes" if feasible else "no-use-larger-set",
                "anchor_pattern": "single center-third" if cast == 1 else ("open V / profile pair" if cast == 2 else "staggered arc with two depth rows"),
                "depth_order": "foreground speaker|primary row|secondary row|environment",
                "eyelines": "converge within group; no crossing through faces",
                "entrance_exit": "opposed routes; preserve one emergency clear lane",
                "camera": "medium" if cast <= 2 else ("wide" if cast <= 5 else "extreme wide/elevated"),
                "note": "requires verified 13-character silhouettes before final approval" if cast > 1 else "use verified character root anchor",
            })
    return rows


def image_prompt(shot: dict[str, object]) -> str:
    return (
        f"Use case: stylized-concept\nAsset type: clean scenic production plate\nPrimary request: {shot['shot_class']} for {shot['set_name']} in Joeville.\n"
        f"Scene/backdrop: {shot['district']}; narrative use: {shot['dramatic_use']}.\nStyle/medium: {BASE_STYLE}.\n"
        f"Composition/framing: {shot['camera']}; {shot['character_safe_area']}; preserve lower-floor movement and a readable horizon.\n"
        f"Lighting/mood: {shot['time']}, emotionally warm but dialogue-readable.\nColor palette: sandstone, ponderosa green, creek blue, sun gold, night indigo; rainbow only as a restrained recurring accent.\n"
        f"Materials/textures: regional stone, brick, weathered wood, dark steel, clear glass, block-cell foliage.\n"
        f"Continuity: set ID {shot['set_id']}; west/mountain side remains screen-consistent; use approved town map and matching master architecture.\n"
        f"Output: 3840x2160 master, compose for 16:9; layer plan {shot['layers']}; filename {shot['shot_id']}.png.\n"
        f"Constraints: empty clean plate; signage surfaces blank for controlled graphic pass.\nAvoid: {NEGATIVE}."
    )


def video_prompt(clip: dict[str, object]) -> str:
    return (
        f"Use case: stylized-concept\nAsset type: environment clip\nPrimary request: {clip['description']} for {clip['dramatic_use']}.\n"
        f"Style/medium: {BASE_STYLE}.\nCamera: {clip['camera_behavior']}; duration {clip['duration_seconds']} seconds at {clip['fps']} fps; {clip['looping']}.\n"
        f"Character-safe zone: {clip['character_safe_area']}. Foreground: {clip['foreground_motion']}. Background: {clip['background_motion']}.\n"
        f"Lighting/weather: {clip['lighting_change']}; {clip['weather_fx']}. Motion must remain low-amplitude and deterministic behind dialogue.\n"
        f"Output: {clip['master_resolution']}, ProRes 4444 for alpha passes or ProRes 422 HQ clean plate; filename {clip['clip_id']}.mov.\n"
        f"Loop rule: {clip['transition_requirement']}. Required art: {clip['required_source_art']}.\n"
        f"Avoid: {NEGATIVE}, camera breathing, texture crawl, temporal warping, exposure pumping, visible loop jump."
    )


def write_prompt_library(path: Path, title: str, rows: list[dict[str, object]], id_key: str, builder) -> None:
    parts = [f"# {title}\n", "> Status: production prompts authored; generated assets are tracked separately.\n"]
    for row in rows:
        parts.append(f"\n## {row[id_key]}\n\n```text\n{builder(row)}\n```\n")
    path.write_text("".join(parts), encoding="utf-8")


def main() -> None:
    shots = shot_rows()
    clips = clip_rows()
    locations = location_rows()
    blocking = blocking_rows()
    write_csv(ROOT / "manifests" / "STILL_SHOT_MANIFEST.csv", list(shots[0]), shots)
    write_csv(ROOT / "manifests" / "ENVIRONMENT_CLIP_MANIFEST.csv", list(clips[0]), clips)
    write_csv(ROOT / "manifests" / "SET_REGISTER.csv", list(locations[0]), locations)
    write_csv(ROOT / "manifests" / "CHARACTER_BLOCKING_MATRIX.csv", list(blocking[0]), blocking)
    write_prompt_library(ROOT / "prompts" / "IMAGE_PROMPT_LIBRARY.md", "Joeville Image-Generation Prompt Library", shots, "shot_id", image_prompt)
    write_prompt_library(ROOT / "prompts" / "VIDEO_PROMPT_LIBRARY.md", "Joeville Video-Generation Prompt Library", clips, "clip_id", video_prompt)
    summary = (
        "# Generated Manifest Inventory\n\n"
        f"- Sets: {len(SETS)}\n- Still-shot records: {len(shots)}\n- Clip records: {len(clips)}\n"
        f"- Blocking tests: {len(blocking)}\n- Image prompts: {len(shots)}\n- Video prompts: {len(clips)}\n"
        "- Cast intake: 2 verified characters, 11 ready-to-intake slots\n\n"
        "All records are planning specifications unless an asset is explicitly marked created in the concept-art index.\n"
    )
    (ROOT / "manifests" / "INVENTORY.md").write_text(summary, encoding="utf-8")


if __name__ == "__main__":
    main()
