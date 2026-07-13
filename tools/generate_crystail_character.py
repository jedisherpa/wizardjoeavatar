#!/usr/bin/env python3
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wizard_avatar.crystail import (
    CRYSTAIL_POSE_IDS,
    CRYSTAIL_ROOT_ANCHOR,
    FACING_POSES,
    PALETTE,
)


DEFINITIONS = ROOT / "wizard_avatar" / "definitions"
WORKSHEETS = ROOT / "assets" / "reference" / "crystail" / "canonical-worksheets"

EXPRESSION_NAMES = (
    "neutral", "calm", "joy", "amusement", "excitement", "curiosity",
    "confidence", "compassion", "surprise", "confusion", "skepticism",
    "concern", "sadness", "shame", "embarrassment", "fear", "anxiety",
    "anger", "frustration", "determination", "fatigue", "contemplation",
)

# Leave enough transparent cells around every authored pose for scaled blits,
# wing follow-through, and sub-cell projection rounding.  A one-cell border
# reads as a clipped wing tip even when no source pixels are discarded.
POSE_MAX_WIDTH = 64
POSE_MAX_HEIGHT = 88


def _source_map() -> dict[str, tuple[str, int, int, int]]:
    result: dict[str, tuple[str, int, int, int]] = {}

    turnaround = "02-turnaround-sheet-candidate-v1.png"
    for index, pose_id in enumerate(FACING_POSES.values()):
        result[pose_id] = (turnaround, 4, 2, index)

    neutral = "03-neutral-base-poses-candidate-v1.png"
    result.update(
        {
            "idle_relaxed": (neutral, 4, 2, 4),
            "idle_attentive": (neutral, 4, 2, 5),
            "idle_speaking": (neutral, 4, 2, 6),
            "idle_listening": (neutral, 4, 2, 7),
            "gesture_explain": (neutral, 4, 2, 6),
            "gesture_point": (neutral, 4, 2, 6),
            "gesture_present": (neutral, 4, 2, 6),
            "gesture_think": (neutral, 4, 2, 5),
            "gesture_react": (neutral, 4, 2, 5),
            "gesture_celebrate": (neutral, 4, 2, 6),
            "gesture_containment": (neutral, 4, 2, 7),
            "magic_cast": (neutral, 4, 2, 6),
            "listen_compassionate": (neutral, 4, 2, 7),
        }
    )

    ground = "06-ground-motion-sheet-v1.png"
    for index, pose_id in enumerate(
        (
            "walk_contact_left", "walk_passing_left", "walk_contact_right",
            "walk_passing_right", "run_reach", "run_drive", "turn_left",
            "turn_right", "crouch", "jump_airborne", "fall", "land",
        )
    ):
        result[pose_id] = (ground, 4, 3, index)
    result["jump_anticipation"] = (ground, 4, 3, 8)

    flight = "07-flight-motion-sheet-v1.png"
    result.update(
        {
            "takeoff": (flight, 4, 3, 1),
            "hover_up": (flight, 4, 3, 2),
            "hover_down": (flight, 4, 3, 3),
            "glide": (flight, 4, 3, 4),
            "bank_left": (flight, 4, 3, 6),
            "bank_right": (flight, 4, 3, 7),
            "touchdown": (flight, 4, 3, 11),
        }
    )

    expression = "04-expression-sheet-candidate-v1.png"
    for index, name in enumerate(EXPRESSION_NAMES):
        result["expression_{}".format(name)] = (expression, 5, 5, index)
    return result


POSE_SOURCES = _source_map()


@lru_cache(maxsize=None)
def _panel(sheet_name: str, columns: int, rows: int, index: int) -> Image.Image:
    image = Image.open(WORKSHEETS / sheet_name).convert("RGB")
    column = index % columns
    row = index // columns
    left = round(column * image.width / columns) + 3
    right = round((column + 1) * image.width / columns) - 3
    top = round(row * image.height / rows) + 3
    bottom = round((row + 1) * image.height / rows) - 3
    return image.crop((left, top, right, bottom))


def _panel_cells(sheet_name: str, columns: int, rows: int, index: int) -> list[dict]:
    panel = _panel(sheet_name, columns, rows, index)
    pixels = np.asarray(panel, dtype=np.uint8)
    maximum = pixels.max(axis=2)
    minimum = pixels.min(axis=2)
    chroma = maximum.astype(np.int16) - minimum.astype(np.int16)
    red = pixels[:, :, 0].astype(np.int16)
    green = pixels[:, :, 1].astype(np.int16)
    blue = pixels[:, :, 2].astype(np.int16)
    colorful = (chroma > 18) & (maximum < 252)
    cream = (red > 105) & (green > 85) & (blue < 175) & ((red - blue) > 18)
    core = colorful | cream
    core_image = Image.fromarray((core.astype(np.uint8) * 255))
    closed = np.asarray(
        core_image.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7)),
        dtype=np.uint8,
    ) > 0
    nearby = np.asarray(core_image.filter(ImageFilter.MaxFilter(21)), dtype=np.uint8) > 0
    dark_detail = (maximum < 125) & nearby & (chroma > 8)
    mask = core | closed | dark_detail
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise ValueError("No subject found in {} panel {}".format(sheet_name, index))
    x0, x1 = max(0, int(xs.min()) - 3), min(panel.width, int(xs.max()) + 4)
    y0, y1 = max(0, int(ys.min()) - 3), min(panel.height, int(ys.max()) + 4)
    rgba = panel.convert("RGBA")
    alpha = Image.fromarray((mask.astype(np.uint8) * 255))
    rgba.putalpha(alpha)
    subject = rgba.crop((x0, y0, x1, y1))

    scale = min(POSE_MAX_WIDTH / subject.width, POSE_MAX_HEIGHT / subject.height)
    target_width = max(1, round(subject.width * scale))
    target_height = max(1, round(subject.height * scale))
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    subject = subject.resize((target_width, target_height), resampling)
    subject_pixels = np.asarray(subject, dtype=np.uint8)
    origin_x = (72 - target_width) // 2
    origin_y = 94 - target_height
    cells: list[dict] = []
    for y in range(target_height):
        for x in range(target_width):
            r, g, b, a = (int(channel) for channel in subject_pixels[y, x])
            if a < 42:
                continue
            # Four-channel cell colors retain the worksheet's cube-face lighting.
            cells.append({"x": origin_x + x, "y": origin_y + y, "rgb": [r, g, b]})
    return cells


def pose_payload() -> dict:
    poses = []
    for pose_id in CRYSTAIL_POSE_IDS:
        try:
            source = POSE_SOURCES[pose_id]
        except KeyError as exc:
            raise ValueError("Missing worksheet source for {}".format(pose_id)) from exc
        cells = _panel_cells(*source)
        poses.append(
            {
                "id": pose_id,
                "description": pose_id.replace("_", " "),
                "source": "assets/reference/crystail/canonical-worksheets/{}#panel-{}".format(source[0], source[3]),
                "cols": 72,
                "rows": 96,
                "root_anchor": list(CRYSTAIL_ROOT_ANCHOR),
                "facing": next((facing for facing, value in FACING_POSES.items() if value == pose_id), "south"),
                "anchors": {
                    "root": list(CRYSTAIL_ROOT_ANCHOR),
                    "mouth": [38, 34],
                    "left_eye": [31, 25],
                    "right_eye": [41, 25],
                    "left_hand": [21, 61],
                    "right_hand": [51, 61],
                    "left_foot": [28, 91],
                    "right_foot": [44, 91],
                    "left_wing_tip": [8, 38],
                    "right_wing_tip": [64, 38],
                    "tail_tip": [58, 81],
                },
                "cells": cells,
            }
        )
    return {
        "schema_version": 2,
        "version": 1,
        "asset_set_id": "crystail-worksheet-motion-v2",
        "generation_method": "canonical_worksheet_raster_to_direct_square_cells",
        "canonical": {
            "cols": 72,
            "rows": 96,
            "root_anchor": list(CRYSTAIL_ROOT_ANCHOR),
            "baseline_y": CRYSTAIL_ROOT_ANCHOR[1],
            "safe_inset": {"left": 4, "right": 4, "top": 4},
        },
        "palette": {name: list(rgb) for name, rgb in PALETTE.items()},
        "poses": poses,
    }


def graph_payload() -> dict:
    clips = []
    families = {
        "idle": ["idle_relaxed", "idle_attentive", "idle_listening", "idle_speaking"],
        "walk": ["walk_contact_left", "walk_passing_left", "walk_contact_right", "walk_passing_right"],
        "run": ["run_reach", "run_drive"],
        "turn": ["turn_left", "neutral_front", "turn_right"],
        "jump_land": ["jump_anticipation", "jump_airborne", "fall", "land"],
        "flight": ["takeoff", "hover_up", "hover_down", "glide", "touchdown"],
        "bank": ["bank_left", "glide", "bank_right"],
        "conversation": ["idle_listening", "gesture_explain", "gesture_present", "gesture_point", "gesture_containment"],
        "performance": ["gesture_think", "gesture_react", "gesture_celebrate", "magic_cast"],
    }
    for clip_id, pose_ids in families.items():
        clips.append(
            {
                "clip_id": f"crystail_{clip_id}",
                "loop": clip_id in {"idle", "walk", "run", "flight", "conversation"},
                "samples": [
                    {"pose_id": pose_id, "tick": index * 6, "contact": "none" if clip_id in {"flight", "bank"} else "authored"}
                    for index, pose_id in enumerate(pose_ids)
                ],
            }
        )
    clips.append({"clip_id": "crystail_turnaround", "loop": True, "samples": [{"pose_id": pose_id, "tick": index * 12} for index, pose_id in enumerate(FACING_POSES.values())]})
    return {
        "schema_version": 2,
        "asset_set_id": "crystail-worksheet-motion-v2",
        "authored_fps": 24,
        "simulation_hz": 60,
        "default_node_id": "idle",
        "motion_profile": {
            "quality": "smooth_feminine_performance",
            "principles": ["graceful_hand_arcs", "subtle_hip_counter_sway", "soft_landings", "wing_follow_through", "enthusiastic_anticipation", "containment_recovery"],
            "identity_note": "Femininity is communicated through performance only; anatomy and costume are unchanged.",
        },
        "clips": clips,
    }


def matrix_payload() -> dict:
    groups = {
        "idle": ["neutral", "relaxed", "attentive", "speaking", "listening", "breathing", "blink", "look_left", "look_right", "weight_shift"],
        "locomotion": ["walk_forward", "walk_backward", "walk_left", "walk_right", "run_forward", "run_burst", "start", "stop", "turn_left", "turn_right", "crouch", "jump", "fall", "land"],
        "flight": ["takeoff", "hover", "flap", "glide", "travel_forward", "travel_backward", "travel_left", "travel_right", "bank_left", "bank_right", "ascend", "descend", "fall", "touchdown"],
        "conversation": ["explain", "point", "present", "listen", "agree", "disagree", "question", "answer", "interrupt_excitedly", "laugh", "joke", "think", "compassion", "containment", "settle", "speech_emphasis"],
        "emotion": ["calm", "joy", "amusement", "excitement", "curiosity", "confidence", "compassion", "surprise", "confusion", "skepticism", "concern", "sadness", "shame", "embarrassment", "fear", "anxiety", "anger", "frustration", "determination", "fatigue", "contemplation"],
        "interaction": ["reach", "open_hand", "close_hand", "fist", "grip", "hold", "write", "magic_cast", "celebrate", "react"],
        "speech": ["rest", "closed_lips", "slightly_open", "wide_vowel", "open_vowel", "rounded_vowel", "teeth_consonant", "lower_lip_consonant", "tongue_consonant", "smile_speaking", "frown_speaking", "speech_emphasis", "breath_pause"],
    }
    rows = []
    for group, names in groups.items():
        for name in names:
            rows.append({"behavior_id": f"{group}.{name}", "group": group, "runtime": "worksheet_pose_plus_semantic_channel", "status": "production", "transition": "anticipate_action_follow_through_recover"})
    assert len(rows) == 98
    return {"schema_version": 1, "character_id": "crystail-v1", "row_count": len(rows), "rows": rows}


def manifest_payload(pose_hash: str, graph_hash: str, matrix_hash: str) -> dict:
    original_path = ROOT / "assets" / "reference" / "crystail" / "original-reference.png"
    original_hash = hashlib.sha256(original_path.read_bytes()).hexdigest() if original_path.is_file() else None
    worksheet_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(WORKSHEETS.glob("*.png"))
    }
    return {
        "schema_version": 1,
        "character_id": "crystail-v1",
        "display_name": "CrystAIl",
        "identity_lock": {
            "immutable": ["voxel dragon silhouette", "deep emerald body", "cream segmented throat and belly", "large rectangular head", "long squared muzzle", "paired stepped horns", "tan rectangular eyes", "four upper teeth", "rainbow-banded wings with blue tips", "two forward toes", "three articulated hand digits", "thick stepped tail"],
            "articulated": ["jaw", "brows", "eyelids", "neck", "shoulders", "elbows", "wrists", "digits", "hips", "knees", "ankles", "tail segments", "wing roots and folds"],
            "default_prop": None,
            "femininity": "performance_only",
            "folded_wings_keep_rainbow_bands": True,
        },
        "origin": {"root_anchor": list(CRYSTAIL_ROOT_ANCHOR), "baseline_y": CRYSTAIL_ROOT_ANCHOR[1], "canvas": [72, 96]},
        "attachment_points": ["mouth", "left_eye", "right_eye", "left_hand", "right_hand", "left_foot", "right_foot", "left_wing_tip", "right_wing_tip", "tail_tip"],
        "derivation": {
            "original_reference": "assets/reference/crystail/original-reference.png",
            "approved_worksheets": "assets/reference/crystail/canonical-worksheets/",
            "runtime_art": "deterministic worksheet-derived direct cell library",
            "flattened_runtime_dependency": False
        },
        "hashes": {
            "original_reference_sha256": original_hash,
            "worksheet_sha256": worksheet_hashes,
            "pose_library_sha256": pose_hash,
            "animation_graph_sha256": graph_hash,
            "animation_matrix_sha256": matrix_hash
        },
    }


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    pose_text = canonical_json(pose_payload())
    graph_text = canonical_json(graph_payload())
    matrix_text = canonical_json(matrix_payload())
    outputs = {
        DEFINITIONS / "crystail_pose_cells.json": pose_text,
        DEFINITIONS / "crystail_animation_graph.json": graph_text,
        DEFINITIONS / "crystail_animation_matrix.json": matrix_text,
        DEFINITIONS / "crystail_character_manifest.json": canonical_json(manifest_payload(digest(pose_text), digest(graph_text), digest(matrix_text))),
    }
    if args.check:
        mismatches = [str(path) for path, content in outputs.items() if not path.is_file() or path.read_text(encoding="utf-8") != content]
        if mismatches:
            raise SystemExit("generated CrystAIl assets differ: " + ", ".join(mismatches))
        print("CrystAIl generated assets are deterministic")
        return 0
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
    print("Generated {} CrystAIl assets".format(len(outputs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
