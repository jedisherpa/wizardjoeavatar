#!/usr/bin/env python3
"""Translate a full-size RGBA source onto the canonical JoeVille canvas."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUTHORITY = (
    ROOT / "assets" / "reference" / "hd_canonical" / "manifest.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt_path(path: Path, path_root: Path | None) -> str:
    resolved = path.resolve()
    if path_root is None:
        return str(resolved)
    try:
        return str(resolved.relative_to(path_root.resolve()))
    except ValueError as exc:
        raise ValueError("receipt path escapes path_root") from exc


def canonicalize(
    *,
    source_path: Path,
    destination_path: Path,
    authority_path: Path = DEFAULT_AUTHORITY,
    fit_oversize: bool = False,
    ground_support_band_height: int | None = None,
    receipt_path_root: Path | None = None,
) -> dict[str, Any]:
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    profile = authority["master_profile"]
    expected_size = (
        int(profile["canvas_width"]),
        int(profile["canvas_height"]),
    )
    baseline_y = int(profile["baseline_y"])
    minimum_margin = int(profile["minimum_margin"])
    with Image.open(source_path) as source:
        source.load()
        if source.format != "PNG" or source.mode != "RGBA":
            raise ValueError("authored alpha source must be an RGBA PNG")
        image = source.copy()
    if image.size != expected_size:
        raise ValueError("authored alpha source must match canonical canvas")
    alpha = image.getchannel("A")
    source_bbox = alpha.getbbox()
    if source_bbox is None:
        raise ValueError("authored alpha source has no visible silhouette")
    bbox = source_bbox
    resampled = False
    scale = 1.0
    if fit_oversize:
        available_width = expected_size[0] - (minimum_margin * 2)
        available_height = baseline_y - minimum_margin
        source_width = bbox[2] - bbox[0]
        source_height = bbox[3] - bbox[1]
        scale = min(
            1.0,
            available_width / source_width,
            available_height / source_height,
        )
        if scale < 1.0:
            target_size = (
                max(1, math.floor(source_width * scale)),
                max(1, math.floor(source_height * scale)),
            )
            subject = image.crop(bbox).convert("RGBa")
            subject = subject.resize(
                target_size,
                resample=Image.Resampling.LANCZOS,
            ).convert("RGBA")
            image = Image.new("RGBA", expected_size, (0, 0, 0, 0))
            image.alpha_composite(subject, (0, 0))
            bbox = image.getchannel("A").getbbox()
            if bbox is None:
                raise ValueError("oversize fitting removed the silhouette")
            resampled = True
    if (
        ground_support_band_height is not None
        and ground_support_band_height <= 0
    ):
        raise ValueError("ground support band height must be positive")
    target_center_x = expected_size[0] / 2
    source_ground_support_bbox: tuple[int, int, int, int] | None = None
    if ground_support_band_height is None:
        alignment_mode = "silhouette_center"
        source_center_x = (bbox[0] + bbox[2]) / 2
    else:
        band_top = max(bbox[1], bbox[3] - ground_support_band_height)
        support_crop_bbox = image.getchannel("A").crop(
            (0, band_top, expected_size[0], bbox[3])
        ).getbbox()
        if support_crop_bbox is None:
            raise ValueError("ground support band contains no visible pixels")
        source_ground_support_bbox = (
            support_crop_bbox[0],
            band_top + support_crop_bbox[1],
            support_crop_bbox[2],
            band_top + support_crop_bbox[3],
        )
        alignment_mode = "ground_support_center"
        source_center_x = (
            source_ground_support_bbox[0] + source_ground_support_bbox[2]
        ) / 2
    offset_x = round(target_center_x - source_center_x)
    offset_y = baseline_y - bbox[3]
    destination_bbox = (
        bbox[0] + offset_x,
        bbox[1] + offset_y,
        bbox[2] + offset_x,
        bbox[3] + offset_y,
    )
    if (
        destination_bbox[0] < minimum_margin
        or destination_bbox[1] < minimum_margin
        or expected_size[0] - destination_bbox[2] < minimum_margin
        or destination_bbox[3] != baseline_y
    ):
        raise ValueError("authored silhouette cannot fit canonical margins")
    canvas = Image.new("RGBA", expected_size, (0, 0, 0, 0))
    canvas.alpha_composite(image, (offset_x, offset_y))
    if canvas.getchannel("A").getbbox() != destination_bbox:
        raise ValueError("authored alpha translation changed its silhouette")
    destination_ground_support_bbox = (
        [
            source_ground_support_bbox[0] + offset_x,
            source_ground_support_bbox[1] + offset_y,
            source_ground_support_bbox[2] + offset_x,
            source_ground_support_bbox[3] + offset_y,
        ]
        if source_ground_support_bbox is not None
        else None
    )
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination_path.with_name(
        f".{destination_path.name}.{os.getpid()}.tmp"
    )
    canvas.save(temporary, format="PNG", optimize=True)
    temporary.replace(destination_path)
    return {
        "schema_version": 1,
        "profile_id": profile["profile_id"],
        "authority_manifest_sha256": _sha256(authority_path),
        "source_path": _receipt_path(source_path, receipt_path_root),
        "source_sha256": _sha256(source_path),
        "destination_path": _receipt_path(
            destination_path, receipt_path_root
        ),
        "destination_sha256": _sha256(destination_path),
        "destination_rgba_sha256": hashlib.sha256(
            canvas.tobytes()
        ).hexdigest(),
        "source_bbox": list(source_bbox),
        "fitted_bbox": list(bbox),
        "destination_bbox": list(destination_bbox),
        "translation": {"x": offset_x, "y": offset_y},
        "alignment_mode": alignment_mode,
        "alignment_source_center_x": source_center_x,
        "alignment_target_center_x": target_center_x,
        "ground_support_band_height": ground_support_band_height,
        "source_ground_support_bbox": (
            list(source_ground_support_bbox)
            if source_ground_support_bbox is not None
            else None
        ),
        "destination_ground_support_bbox": destination_ground_support_bbox,
        "resampled": resampled,
        "scale": scale,
        "resample_filter": "lanczos" if resampled else None,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Center and baseline-align an RGBA JoeVille authoring source "
            "without resampling it by default."
        )
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument(
        "--fit-oversize",
        action="store_true",
        help=(
            "Deterministically downscale only silhouettes that cannot fit the "
            "canonical safety margins, recording the transform in the receipt."
        ),
    )
    parser.add_argument(
        "--ground-support-band-height",
        type=int,
        help=(
            "Align the visible support pixels in the bottom N rows of the "
            "silhouette to stage center instead of centering the full "
            "silhouette bounding box."
        ),
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        help="Optional JSON path for the canonicalization receipt.",
    )
    parser.add_argument(
        "--receipt-path-root",
        type=Path,
        help="Store receipt paths relative to this root.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = canonicalize(
        source_path=args.source.resolve(),
        destination_path=args.destination.resolve(),
        authority_path=args.authority.resolve(),
        fit_oversize=args.fit_oversize,
        ground_support_band_height=args.ground_support_band_height,
        receipt_path_root=(
            args.receipt_path_root.resolve()
            if args.receipt_path_root is not None
            else None
        ),
    )
    if args.receipt is not None:
        receipt_path = args.receipt.resolve()
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
