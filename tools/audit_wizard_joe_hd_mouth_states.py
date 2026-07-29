#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any, Iterable

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import HDPoseLibrary


DEFAULT_INDEX = (
    ROOT / "assets" / "reference" / "hd_canonical" / "compiled" / "library-index.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "wizard-joe"
    / "mouth-pairs-v1"
    / "mouth-state-ledger.json"
)
APPROVED_POSE_COUNT = 250
NOT_VISIBLE_POSE_IDS = {
    "004_turn_back_3q_left",
    "005_turn_back_neutral",
    "006_turn_back_3q_right",
    "010_neutral_back_wings_part_folded",
    "181_flight_turn_away_camera",
}
MANUAL_MOUTH_OVERRIDES = {
    "007_turn_right_profile": ("closed", [675, 430, 750, 500]),
    "087_emotion_surprise": ("open", [560, 390, 645, 435]),
    "136_turn_left_anticipation": ("closed", [500, 425, 600, 505]),
    "138_turn_left_complete": ("open", [540, 375, 655, 475]),
    "139_walk_start_left": ("open", [410, 450, 500, 535]),
    "140_walk_down_left": ("closed", [480, 500, 590, 610]),
    "142_walk_passing_left": ("closed", [480, 470, 590, 580]),
    "143_walk_up_left": ("open", [490, 470, 610, 570]),
    "144_walk_contact_right": ("open", [500, 460, 610, 570]),
    "145_walk_stop_anticipation": ("open", [510, 480, 630, 580]),
    "162_jump_land_contact": ("closed", [570, 590, 735, 690]),
    "194_flight_landing_contact": ("open", [620, 665, 750, 755]),
    "210_magic_shield_break": ("open", [490, 455, 610, 530]),
    "242_comedy_stumble": ("open", [620, 520, 785, 610]),
    "249_hero_bow": ("closed", [440, 520, 650, 640]),
}


def _components(mask: Image.Image) -> list[dict[str, int]]:
    width, height = mask.size
    pixels = mask.load()
    seen: set[tuple[int, int]] = set()
    result: list[dict[str, int]] = []
    for y in range(height):
        for x in range(width):
            if not pixels[x, y] or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            left = right = x
            top = bottom = y
            area = 0
            while queue:
                current_x, current_y = queue.popleft()
                area += 1
                left = min(left, current_x)
                right = max(right, current_x)
                top = min(top, current_y)
                bottom = max(bottom, current_y)
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if (
                        0 <= next_x < width
                        and 0 <= next_y < height
                        and pixels[next_x, next_y]
                        and (next_x, next_y) not in seen
                    ):
                        seen.add((next_x, next_y))
                        queue.append((next_x, next_y))
            result.append(
                {
                    "left": left,
                    "top": top,
                    "right": right + 1,
                    "bottom": bottom + 1,
                    "width": right - left + 1,
                    "height": bottom - top + 1,
                    "area": area,
                    "center_x": (left + right) // 2,
                    "center_y": (top + bottom) // 2,
                }
            )
    return result


def _white_eye_candidates(image: Image.Image) -> list[dict[str, int]]:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    mask = Image.new("1", rgba.size)
    source = rgba.load()
    target = mask.load()
    for y in range(min(height, 620)):
        for x in range(width):
            red, green, blue, alpha = source[x, y]
            target[x, y] = bool(
                alpha >= 220
                and red >= 210
                and green >= 205
                and blue >= 190
                and max(red, green, blue) - min(red, green, blue) <= 45
            )
    return [
        component
        for component in _components(mask)
        if 80 <= component["area"] <= 8000
        and 12 <= component["width"] <= 125
        and 8 <= component["height"] <= 95
        and 120 <= component["center_y"] <= 540
    ]


def _hat_band_candidates(image: Image.Image) -> list[dict[str, int]]:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    mask = Image.new("1", rgba.size)
    source = rgba.load()
    target = mask.load()
    for y in range(min(height, 850)):
        for x in range(width):
            red, green, blue, alpha = source[x, y]
            target[x, y] = bool(
                alpha >= 220
                and red >= 175
                and green >= 125
                and blue <= 90
                and red >= green * 1.05
                and green >= blue * 1.8
            )
    return [
        component
        for component in _components(mask)
        if component["area"] >= 300
        and 160 <= component["width"] <= 350
        and 35 <= component["height"] <= 120
        and component["width"] >= component["height"] * 2
    ]


def _fallback_mouth_search_region(
    image: Image.Image,
) -> tuple[int, int, int, int] | None:
    candidates = _hat_band_candidates(image)
    if not candidates:
        return None
    band = min(candidates, key=lambda item: (item["top"], -item["area"]))
    padding_x = round(band["width"] * 0.1)
    top = band["bottom"] + round(band["height"] * 0.45)
    bottom = band["bottom"] + round(band["height"] * 3.8)
    return (
        max(0, band["left"] - padding_x),
        max(0, top),
        min(image.width, band["right"] + padding_x),
        min(image.height, bottom),
    )


def _select_eyes(candidates: Iterable[dict[str, int]]) -> list[dict[str, int]]:
    ordered = sorted(candidates, key=lambda item: (item["center_y"], item["center_x"]))
    best: list[dict[str, int]] = []
    best_score = -1
    for index, first in enumerate(ordered):
        single_score = first["area"]
        if single_score > best_score:
            best = [first]
            best_score = single_score
        for second in ordered[index + 1 :]:
            separation = abs(first["center_x"] - second["center_x"])
            vertical_delta = abs(first["center_y"] - second["center_y"])
            if 35 <= separation <= 260 and vertical_delta <= 55:
                score = first["area"] + second["area"] + separation * 3 - vertical_delta * 5
                if score > best_score:
                    best = sorted((first, second), key=lambda item: item["center_x"])
                    best_score = score
    return best


def _mouth_region(
    eyes: list[dict[str, int]],
    canvas: tuple[int, int],
) -> tuple[int, int, int, int] | None:
    if not eyes:
        return None
    width, height = canvas
    center_x = round(sum(item["center_x"] for item in eyes) / len(eyes))
    eye_y = round(sum(item["center_y"] for item in eyes) / len(eyes))
    if len(eyes) == 2:
        eye_span = eyes[1]["center_x"] - eyes[0]["center_x"]
        region_width = max(105, round(eye_span * 1.15))
    else:
        region_width = max(90, round(eyes[0]["width"] * 1.7))
    region_height = max(75, round(region_width * 0.64))
    top = eye_y + max(70, round(region_height * 0.72))
    left = center_x - region_width // 2
    return (
        max(0, left),
        max(0, top),
        min(width, left + region_width),
        min(height, top + region_height),
    )


def _mouth_color_counts(
    image: Image.Image,
    region: tuple[int, int, int, int],
) -> dict[str, int]:
    crop = image.convert("RGBA").crop(region)
    counts = {"teeth": 0, "tongue": 0, "dark_cavity": 0, "opaque": 0}
    for red, green, blue, alpha in crop.getdata():
        if alpha < 180:
            continue
        counts["opaque"] += 1
        if red >= 185 and green >= 180 and blue >= 170 and max(red, green, blue) - min(
            red, green, blue
        ) <= 28:
            counts["teeth"] += 1
        if (
            red >= 105
            and red >= green * 1.45
            and 35 <= blue <= 145
            and green <= 105
            and red - blue <= 145
        ):
            counts["tongue"] += 1
        if red <= 80 and green <= 55 and blue <= 42:
            counts["dark_cavity"] += 1
    return counts


def _articulation_region(
    image: Image.Image,
    search_region: tuple[int, int, int, int],
) -> tuple[tuple[int, int, int, int], dict[str, int]] | None:
    crop = image.convert("RGBA").crop(search_region)
    source = crop.load()
    mask = Image.new("1", crop.size)
    target = mask.load()
    for y in range(crop.height):
        for x in range(crop.width):
            red, green, blue, alpha = source[x, y]
            target[x, y] = bool(
                alpha >= 180 and red < 95 and green < 70 and blue < 60
            )
    candidates = [
        component
        for component in _components(mask)
        if component["width"] >= 24
        and component["width"] >= component["height"] * 1.35
        and component["center_y"] <= round(crop.height * 0.68)
    ]
    if not candidates:
        return None
    component = max(candidates, key=lambda item: item["area"])
    padding_x = max(4, round(component["width"] * 0.05))
    padding_y = max(4, round(component["height"] * 0.12))
    left = max(search_region[0], search_region[0] + component["left"] - padding_x)
    top = max(search_region[1], search_region[1] + component["top"] - padding_y)
    right = min(search_region[2], search_region[0] + component["right"] + padding_x)
    bottom = min(search_region[3], search_region[1] + component["bottom"] + padding_y)
    return (left, top, right, bottom), component


def audit_pose(pose_id: str, image: Image.Image) -> dict[str, Any]:
    if pose_id in NOT_VISIBLE_POSE_IDS:
        return {
            "pose_id": pose_id,
            "mouth_visibility": "not_visible",
            "mouth_state": "not_visible",
            "confidence_milli": 1000,
            "eye_landmarks": [],
            "mouth_region": None,
            "evidence": {"reason": "hand_reviewed_rear_facing"},
        }
    manual = MANUAL_MOUTH_OVERRIDES.get(pose_id)
    if manual is not None:
        state, manual_region = manual
        return {
            "pose_id": pose_id,
            "mouth_visibility": "visible",
            "mouth_state": state,
            "confidence_milli": 1000,
            "eye_landmarks": [],
            "mouth_region": manual_region,
            "mouth_search_region": manual_region,
            "evidence": {"reason": "hand_reviewed_extreme_posture"},
        }
    eyes = _select_eyes(_white_eye_candidates(image))
    region = _mouth_region(eyes, image.size)
    if region is None:
        region = _fallback_mouth_search_region(image)
        if region is None:
            return {
                "pose_id": pose_id,
                "mouth_visibility": "needs_review",
                "mouth_state": "needs_review",
                "confidence_milli": 0,
                "eye_landmarks": [],
                "mouth_region": None,
                "evidence": {"reason": "no_face_geometry"},
            }
    articulation = _articulation_region(image, region)
    if articulation is None and eyes:
        fallback_region = _fallback_mouth_search_region(image)
        if fallback_region is not None:
            region = fallback_region
            articulation = _articulation_region(image, region)
    if articulation is None:
        return {
            "pose_id": pose_id,
            "mouth_visibility": "needs_review",
            "mouth_state": "needs_review",
            "confidence_milli": 0,
            "eye_landmarks": [
                [item["center_x"], item["center_y"], item["width"], item["height"]]
                for item in eyes
            ],
            "mouth_region": None,
            "evidence": {"reason": "mouth_geometry_not_found"},
        }
    mouth_region, component = articulation
    counts = _mouth_color_counts(image, mouth_region)
    aspect_milli = round(component["height"] * 1000 / max(1, component["width"]))
    open_score = aspect_milli
    state = "open" if aspect_milli >= 280 else "closed"
    confidence = min(
        1000,
        550 + abs(aspect_milli - 280) * 3,
    )
    if not eyes:
        confidence = min(confidence, 760)
    return {
        "pose_id": pose_id,
        "mouth_visibility": "visible",
        "mouth_state": state,
        "confidence_milli": confidence,
        "eye_landmarks": [
            [item["center_x"], item["center_y"], item["width"], item["height"]]
            for item in eyes
        ],
        "mouth_region": list(mouth_region),
        "mouth_search_region": list(region),
        "evidence": {
            **counts,
            "geometry_source": "eyes" if eyes else "hat_brim_fallback",
            "dark_component_width": component["width"],
            "dark_component_height": component["height"],
            "dark_component_aspect_milli": aspect_milli,
            "open_score": open_score,
        },
    }


def audit_library(index_path: Path, output_path: Path) -> dict[str, Any]:
    library = HDPoseLibrary(index_path.resolve())
    approved_ids = tuple(library.pose_ids[:APPROVED_POSE_COUNT])
    records = [audit_pose(pose_id, library.load_pose(pose_id)) for pose_id in approved_ids]
    summary = {
        state: sum(1 for record in records if record["mouth_state"] == state)
        for state in ("open", "closed", "not_visible", "needs_review")
    }
    payload = {
        "schema_version": 1,
        "character_id": "wizard-joe-v1",
        "source_library": index_path.resolve().relative_to(ROOT).as_posix(),
        "scope": "approved_production_alpha_001_250",
        "pose_count": len(records),
        "states": summary,
        "review_policy": {
            "opposite_variant_required_when": "mouth_visibility == visible",
            "rear_facing_policy": "record not_visible; do not synthesize a mouth",
            "outside_articulation_region": "must remain byte-identical",
            "manual_review_threshold_milli": 700,
        },
        "poses": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "output": output_path.resolve().relative_to(ROOT).as_posix(),
        "pose_count": len(records),
        "states": summary,
        "low_confidence": sum(
            1 for record in records if int(record["confidence_milli"]) < 700
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit open/closed mouth state for every approved Wizard Joe HD pose."
    )
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(audit_library(args.index, args.output), indent=2))


if __name__ == "__main__":
    main()
