#!/usr/bin/env python3
"""Build and audit the review-only Dragon interim pose candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from PIL import Image, ImageChops, ImageOps

ROOT = Path(__file__).resolve().parent.parent
DRAGON_ROOT = ROOT / "assets" / "reference" / "characters" / "dragon"
SOURCE_ROOT = DRAGON_ROOT / "source" / "alphas"
DEFAULT_OUTPUT = DRAGON_ROOT / "interim-v001"
CANVAS_SIZE = (1920, 1080)
SCHEMA_VERSION = "1.0.0"
PROMPT_CONTRACT_ID = "dragon-drg001-identity-locked-chroma-v001"
PROMPT_CONTRACT = {
    "use_case": "stylized-concept",
    "subject_contract": (
        "Preserve DRG001 identity, orange-and-cobalt scale pattern, cream belly, "
        "amber eyes, horns, fins, wings, proportions, materials, and render style."
    ),
    "composition_contract": (
        "Exactly one complete centered Dragon on a 16:9 canvas with generous "
        "padding and no cropped anatomy."
    ),
    "performance_contract": (
        "Render the asset-specific body, hand, flight, or speech intent while "
        "keeping the character readable as a single animation frame."
    ),
    "background_contract": (
        "Perfectly flat solid #00ff00 chroma background with no floor, shadow, "
        "gradient, texture, reflection, text, prop, or watermark."
    ),
}

MIRRORS = {
    "CAN007": (
        "CAN002",
        SOURCE_ROOT / "CAN002_DRG001_front_three_quarter_left_v001_alpha.png",
        "CAN007_DRG001_front_three_quarter_right_v001_alpha.png",
    ),
    "ACT007": (
        "ACT002",
        SOURCE_ROOT / "002_ACT002_front_three_quarter_left_alpha.png",
        "007_ACT007_front_three_quarter_right_alpha.png",
    ),
}

GENERATED = {
    "ACT032": "032_ACT032_cause_and_effect_alpha.png",
    "ACT044": "044_ACT044_excitement_alpha.png",
    "ACT060": "060_ACT060_fatigue_alpha.png",
    "ACT081": "081_ACT081_run_passing_alpha.png",
    "ACT082": "082_ACT082_flight_downstroke_alpha.png",
    "ACT083": "083_ACT083_flight_upstroke_alpha.png",
    "ACT084": "084_ACT084_glide_hover_alpha.png",
    "ACT085": "085_ACT085_speech_small_open_alpha.png",
    "ACT086": "086_ACT086_speech_wide_open_alpha.png",
    "ACT087": "087_ACT087_speech_rounded_alpha.png",
    "ACT088": "088_ACT088_flight_bank_left_alpha.png",
    "ACT089": "089_ACT089_flight_bank_right_alpha.png",
    "ACT090": "090_ACT090_flight_ascend_alpha.png",
    "ACT091": "091_ACT091_flight_descend_alpha.png",
    "ACT092": "092_ACT092_flight_brake_alpha.png",
    "ACT093": "093_ACT093_flight_takeoff_alpha.png",
    "ACT094": "094_ACT094_flight_landing_alpha.png",
    "ACT095": "095_ACT095_hover_listening_alpha.png",
    "ACT096": "096_ACT096_hover_speech_small_open_alpha.png",
    "ACT097": "097_ACT097_hover_speech_wide_open_alpha.png",
    "ACT098": "098_ACT098_hover_speech_rounded_alpha.png",
    "ACT099": "099_ACT099_hover_emphatic_speaking_alpha.png",
    "ACT100": "100_ACT100_explain_small_open_alpha.png",
    "ACT101": "101_ACT101_explain_wide_open_alpha.png",
    "ACT102": "102_ACT102_point_left_rounded_alpha.png",
    "ACT103": "103_ACT103_point_right_small_open_alpha.png",
    "ACT104": "104_ACT104_compare_wide_open_alpha.png",
    "ACT105": "105_ACT105_count_one_rounded_alpha.png",
    "ACT106": "106_ACT106_count_two_small_open_alpha.png",
    "ACT107": "107_ACT107_count_three_wide_open_alpha.png",
    "ACT108": "108_ACT108_present_left_small_open_alpha.png",
    "ACT109": "109_ACT109_present_right_rounded_alpha.png",
    "ACT110": "110_ACT110_describe_vast_wide_open_alpha.png",
    "ACT111": "111_ACT111_tiny_detail_rounded_alpha.png",
    "ACT112": "112_ACT112_reassure_small_open_alpha.png",
    "ACT113": "113_ACT113_confidence_rounded_alpha.png",
    "ACT114": "114_ACT114_declaration_wide_open_alpha.png",
    "ACT115": "115_ACT115_question_rounded_alpha.png",
    "ACT116": "116_ACT116_whisper_small_open_alpha.png",
    "ACT117": "117_ACT117_cause_effect_wide_open_alpha.png",
    "ACT118": "118_ACT118_invitation_small_open_alpha.png",
    "ACT119": "119_ACT119_insight_wide_open_alpha.png",
    "ACT120": "120_ACT120_detail_down_rounded_alpha.png",
    "ACT121": "121_ACT121_warm_welcome_small_open_alpha.png",
    "ACT122": "122_ACT122_skeptical_explain_rounded_alpha.png",
    "ACT123": "123_ACT123_conclusion_wide_open_alpha.png",
}
CHROMA_HELPER = (
    Path.home()
    / ".codex"
    / "skills"
    / ".system"
    / "imagegen"
    / "scripts"
    / "remove_chroma_key.py"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _manifest_path(path: Path, output_dir: Path) -> str:
    try:
        return _repo_path(path)
    except ValueError:
        return path.resolve().relative_to(output_dir.resolve()).as_posix()


def _transparent_rgb_is_zero(image: Image.Image) -> bool:
    red, green, blue, alpha = image.split()
    transparent = alpha.point(lambda value: 255 if value == 0 else 0)
    return all(
        ImageChops.multiply(channel, transparent).getextrema() == (0, 0)
        for channel in (red, green, blue)
    )


def _audit(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.mode != "RGBA":
            raise ValueError(f"{path.name} must be an RGBA PNG")
        if image.size != CANVAS_SIZE:
            raise ValueError(f"{path.name} must be 1920x1080")
        alpha = image.getchannel("A")
        histogram = alpha.histogram()
        if alpha.getextrema() != (0, 255) or sum(histogram[1:255]):
            raise ValueError(f"{path.name} must use binary alpha")
        if not _transparent_rgb_is_zero(image):
            raise ValueError(f"{path.name} has RGB below transparent pixels")
        bbox = alpha.getbbox()
        if bbox is None:
            raise ValueError(f"{path.name} has no visible pixels")
        if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == 1920 or bbox[3] == 1080:
            raise ValueError(f"{path.name} touches the canvas edge")
        return {
            "canvas_size": [1920, 1080],
            "mode": "RGBA",
            "alpha_mode": "binary_straight",
            "transparent_rgb_zero": True,
            "visible_bbox": list(bbox),
            "opaque_pixel_count": histogram[255],
        }


def _save_binary_rgba(image: Image.Image, path: Path) -> None:
    rgba = image.convert("RGBA")
    red, green, blue, alpha = rgba.split()
    alpha = alpha.point(lambda value: 255 if value >= 128 else 0)
    empty = Image.new("L", rgba.size, 0)
    red = Image.composite(red, empty, alpha)
    green = Image.composite(green, empty, alpha)
    blue = Image.composite(blue, empty, alpha)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.merge("RGBA", (red, green, blue, alpha)).save(path, optimize=False)


def extract_generated_sources(output_dir: Path = DEFAULT_OUTPUT) -> None:
    source_dir = output_dir / "generated-source"
    alpha_dir = output_dir / "alphas"
    intermediate_dir = output_dir / ".extracted"
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    for asset_id, filename in GENERATED.items():
        keyed = source_dir / filename.replace("_alpha.png", "_chroma.png")
        if not keyed.is_file():
            raise ValueError(f"missing keyed source for {asset_id}: {keyed}")
        extracted = intermediate_dir / filename
        subprocess.run(
            [
                sys.executable,
                str(CHROMA_HELPER),
                "--input",
                str(keyed),
                "--out",
                str(extracted),
                "--auto-key",
                "border",
                "--soft-matte",
                "--transparent-threshold",
                "12",
                "--opaque-threshold",
                "220",
                "--despill",
                "--force",
            ],
            check=True,
        )
        with Image.open(extracted) as image:
            image.load()
            rgba = image.convert("RGBA")
            margin = 24
            scale = min(
                1.0,
                (CANVAS_SIZE[0] - margin * 2) / rgba.width,
                (CANVAS_SIZE[1] - margin * 2) / rgba.height,
            )
            if scale < 1.0:
                rgba = rgba.resize(
                    (
                        max(1, round(rgba.width * scale)),
                        max(1, round(rgba.height * scale)),
                    ),
                    Image.Resampling.LANCZOS,
                )
            canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
            canvas.alpha_composite(
                rgba,
                (
                    (CANVAS_SIZE[0] - rgba.width) // 2,
                    (CANVAS_SIZE[1] - rgba.height) // 2,
                ),
            )
            _save_binary_rgba(canvas, alpha_dir / filename)
    for path in intermediate_dir.iterdir():
        path.unlink()
    intermediate_dir.rmdir()


def _write_atomic(path: Path, value: object) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def build_dragon_interim_candidates(
    output_dir: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    alpha_dir = output_dir / "alphas"
    records: list[dict[str, Any]] = []

    for asset_id, (source_id, source_path, filename) in MIRRORS.items():
        destination = alpha_dir / filename
        with Image.open(source_path) as image:
            image.load()
            _save_binary_rgba(ImageOps.mirror(image), destination)
        records.append(
            {
                "asset_id": asset_id,
                "filename": filename,
                "path": _manifest_path(destination, output_dir),
                "method": "deterministic_horizontal_mirror",
                "source_asset_id": source_id,
                "source_path": _repo_path(source_path),
                "source_sha256": _sha256(source_path),
                "sha256": _sha256(destination),
                "image_audit": _audit(destination),
                "identity_review": "derived_from_validated_source",
                "motion_review": "pending",
                "canonical_equivalence_review": "pending",
                "runtime_admitted": False,
            }
        )

    missing: list[str] = []
    for asset_id, filename in GENERATED.items():
        path = alpha_dir / filename
        if not path.is_file():
            missing.append(asset_id)
            continue
        chroma_path = (
            output_dir
            / "generated-source"
            / filename.replace("_alpha.png", "_chroma.png")
        )
        if not chroma_path.is_file():
            raise ValueError(f"missing chroma provenance for {asset_id}: {chroma_path}")
        generation_intent = (
            filename.removeprefix(f"{int(asset_id[3:]):03d}_{asset_id}_")
            .removesuffix("_alpha.png")
            .replace("_", " ")
        )
        records.append(
            {
                "asset_id": asset_id,
                "filename": filename,
                "path": _manifest_path(path, output_dir),
                "method": "identity_locked_image_generation_then_chroma_extraction",
                "prompt_contract_id": PROMPT_CONTRACT_ID,
                "generation_intent": generation_intent,
                "chroma_source_path": _manifest_path(chroma_path, output_dir),
                "chroma_source_sha256": _sha256(chroma_path),
                "sha256": _sha256(path),
                "image_audit": _audit(path),
                "identity_review": "pending",
                "motion_review": "pending",
                "canonical_equivalence_review": "pending",
                "runtime_admitted": False,
            }
        )

    records.sort(key=lambda record: (record["asset_id"][:3], int(record["asset_id"][3:])))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "manifest_type": "dragon_interim_candidate_set",
        "candidate_set_id": "dragon-drg001-interim-48-v001",
        "prompt_contract_id": PROMPT_CONTRACT_ID,
        "prompt_contract": PROMPT_CONTRACT,
        "approval_state": (
            "candidate_inventory_complete"
            if not missing
            else "candidate_inventory_incomplete"
        ),
        "candidate_count": len(records),
        "expected_candidate_count": 48,
        "missing_asset_ids": missing,
        "review_projection": False,
        "runtime_admitted": False,
        "assets": records,
    }
    _write_atomic(output_dir / "interim-candidate-manifest-v001.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--extract-generated", action="store_true")
    args = parser.parse_args()
    if args.extract_generated:
        extract_generated_sources(args.output)
    manifest = build_dragon_interim_candidates(args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
