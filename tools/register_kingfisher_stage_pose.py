#!/usr/bin/env python3
"""Register a generated Kingfisher stage pose to the HD review canvas."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CANVAS_SIZE = (960, 540)
TARGET_VISIBLE_HEIGHT = 432
TARGET_BASELINE_Y = 529
TARGET_CENTER_X = 480
MAX_VISIBLE_WIDTH = 900


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable_receipt_path(path: Path) -> str:
    normalized = Path(os.path.normpath(os.fspath(path)))
    if not normalized.is_absolute():
        return normalized.as_posix()
    resolved = normalized.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return f"external/{resolved.name}"


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    payload = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    )
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def register_pose(
    source_path: Path,
    output_path: Path,
    *,
    ordinal: int,
    slug: str,
) -> dict[str, object]:
    source_report_path = portable_receipt_path(source_path)
    output_report_path = portable_receipt_path(output_path)
    source_path = Path(source_path).resolve()
    output_path = Path(output_path).resolve()
    with Image.open(source_path) as loaded:
        source = loaded.convert("RGBA")
    alpha = source.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("Kingfisher stage source has no visible pixels")
    subject = source.crop(bbox)
    scale = min(
        TARGET_VISIBLE_HEIGHT / subject.height,
        MAX_VISIBLE_WIDTH / subject.width,
    )
    registered_size = (
        max(1, round(subject.width * scale)),
        max(1, round(subject.height * scale)),
    )
    subject = subject.resize(registered_size, Image.Resampling.NEAREST)
    binary_alpha = subject.getchannel("A").point(
        lambda value: 255 if value >= 128 else 0
    )
    subject.putalpha(binary_alpha)
    subject_bbox = binary_alpha.getbbox()
    if subject_bbox is None:
        raise ValueError("Kingfisher stage source vanished after alpha threshold")
    subject = subject.crop(subject_bbox)

    x = TARGET_CENTER_X - subject.width // 2
    y = TARGET_BASELINE_Y - subject.height
    if x <= 0 or y <= 0:
        raise ValueError("Kingfisher stage source does not fit the review canvas")
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(subject, (x, y))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", optimize=True)

    output_alpha = canvas.getchannel("A")
    output_bbox = output_alpha.getbbox()
    if output_bbox is None:
        raise ValueError("registered Kingfisher pose is empty")
    alpha_values = set(output_alpha.getdata())
    if alpha_values != {0, 255}:
        raise ValueError("registered Kingfisher pose must use binary alpha")
    if output_bbox[3] != TARGET_BASELINE_Y:
        raise ValueError("registered Kingfisher pose baseline drifted")

    audit = {
        "schema_version": 1,
        "character_id": "kingfisher",
        "pose_id": f"kingfisher.act.{ordinal:03d}.{slug.replace('_', '-')}",
        "ordinal": ordinal,
        "slug": slug,
        "source": {
            "path": source_report_path,
            "sha256": sha256_path(source_path),
            "canvas_size": list(source.size),
            "visible_bbox": list(bbox),
        },
        "registration": {
            "policy": "kingfisher_stage_bottom_center_v1",
            "canvas_size": list(CANVAS_SIZE),
            "target_visible_height": TARGET_VISIBLE_HEIGHT,
            "target_baseline_y": TARGET_BASELINE_Y,
            "target_center_x": TARGET_CENTER_X,
            "maximum_visible_width": MAX_VISIBLE_WIDTH,
            "interpolation": "nearest_neighbor",
            "alpha_mode": "binary_straight",
            "visible_bbox": list(output_bbox),
        },
        "output": {
            "path": output_report_path,
            "sha256": sha256_path(output_path),
            "foreground_pixels": output_alpha.histogram()[255],
        },
        "approval_state": "candidate_visual_review",
        "review_projection": True,
        "runtime_admitted": False,
    }
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register one generated Kingfisher stage pose."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ordinal", type=int, required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()
    audit = register_pose(
        args.source,
        args.output,
        ordinal=args.ordinal,
        slug=args.slug,
    )
    if args.audit:
        _write_json_atomic(args.audit, audit)
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
