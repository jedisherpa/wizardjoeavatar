#!/usr/bin/env python3
"""Rank captured browser frames by avatar fragmentation and temporal discontinuity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def robust_z(values: np.ndarray) -> np.ndarray:
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    return (values - median) / max(mad * 1.4826, 1e-6)


def frame_metrics(path: Path, previous: np.ndarray | None) -> tuple[dict, np.ndarray]:
    image = Image.open(path).convert("RGB")
    image.thumbnail((838, 461), Image.Resampling.LANCZOS)
    rgb = np.asarray(image, dtype=np.uint8)
    hsv = np.asarray(image.convert("HSV"), dtype=np.uint8)

    # The floor and white stage are low-saturation; Wizard Joe's authored palette is not.
    mask = (hsv[:, :, 1] > 52) & (hsv[:, :, 2] > 36)
    labels, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=np.uint8))
    sizes = np.bincount(labels.ravel())[1:]
    significant = sizes[sizes >= 4]
    colored = int(mask.sum())
    largest = int(significant.max()) if significant.size else 0

    ys, xs = np.nonzero(mask)
    if xs.size:
        bounds = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        width = bounds[2] - bounds[0] + 1
        height = bounds[3] - bounds[1] + 1
    else:
        bounds = [0, 0, 0, 0]
        width = height = 0

    horizontal_starts = mask & ~np.pad(mask[:, :-1], ((0, 0), (1, 0)))
    vertical_starts = mask & ~np.pad(mask[:-1, :], ((1, 0), (0, 0)))
    run_density = float((horizontal_starts.sum() + vertical_starts.sum()) / max(colored, 1))

    temporal_diff = 0.0
    if previous is not None:
        temporal_diff = float(np.abs(rgb.astype(np.int16) - previous.astype(np.int16)).mean())

    return (
        {
            "frame": int(path.stem.split("-")[-1]),
            "file": path.name,
            "colored_pixels": colored,
            "significant_components": int(significant.size),
            "largest_component_fraction": float(largest / max(colored, 1)),
            "run_density": run_density,
            "temporal_diff": temporal_diff,
            "bounds": bounds,
            "bounds_width": width,
            "bounds_height": height,
        },
        rgb,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("frames", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--duration", type=float, required=True)
    args = parser.parse_args()

    paths = sorted(args.frames.glob("frame-*.jpg"))
    if not paths:
        paths = sorted(args.frames.glob("*.png"))
    previous = None
    metrics = []
    for path in paths:
        metric, previous = frame_metrics(path, previous)
        metrics.append(metric)

    arrays = {
        key: np.asarray([metric[key] for metric in metrics], dtype=np.float64)
        for key in (
            "colored_pixels",
            "significant_components",
            "largest_component_fraction",
            "run_density",
            "temporal_diff",
            "bounds_width",
            "bounds_height",
        )
    }
    fragmentation = (
        np.maximum(robust_z(arrays["significant_components"]), 0.0)
        + np.maximum(robust_z(arrays["run_density"]), 0.0)
        + np.maximum(-robust_z(arrays["largest_component_fraction"]), 0.0)
        + np.maximum(-robust_z(arrays["colored_pixels"]), 0.0)
    )
    discontinuity = np.maximum(robust_z(arrays["temporal_diff"]), 0.0)
    scores = fragmentation * 1.4 + discontinuity
    fps = len(metrics) / args.duration
    for index, metric in enumerate(metrics):
        metric["time_seconds"] = (metric["frame"] - 1) / fps
        metric["fragmentation_score"] = float(fragmentation[index])
        metric["discontinuity_score"] = float(discontinuity[index])
        metric["anomaly_score"] = float(scores[index])

    ranked = sorted(metrics, key=lambda metric: metric["anomaly_score"], reverse=True)
    output = {
        "frame_count": len(metrics),
        "duration_seconds": args.duration,
        "estimated_fps": fps,
        "medians": {key: float(np.median(value)) for key, value in arrays.items()},
        "top_anomalies": ranked[:120],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["top_anomalies"][:20], indent=2))


if __name__ == "__main__":
    main()
