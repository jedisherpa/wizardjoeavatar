#!/usr/bin/env python3
"""Remove explicitly bounded alpha specks from a registered pose frame."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import deque
from pathlib import Path

from PIL import Image


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _save_png_atomic(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        image.save(temporary, format="PNG", optimize=True)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _alpha_components(image: Image.Image) -> list[list[tuple[int, int]]]:
    alpha = image.getchannel("A")
    width, height = alpha.size
    pixels = alpha.load()
    visited: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0 or (x, y) in visited:
                continue
            component: list[tuple[int, int]] = []
            queue = deque([(x, y)])
            visited.add((x, y))
            while queue:
                current_x, current_y = queue.popleft()
                component.append((current_x, current_y))
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    point = (next_x, next_y)
                    if (
                        0 <= next_x < width
                        and 0 <= next_y < height
                        and pixels[next_x, next_y] > 0
                        and point not in visited
                    ):
                        visited.add(point)
                        queue.append(point)
            components.append(component)
    return components


def remove_isolated_components(
    input_path: Path,
    output_path: Path,
    receipt_path: Path,
    *,
    maximum_area: int,
) -> dict[str, object]:
    if maximum_area < 1:
        raise ValueError("maximum component area must be positive")
    input_sha256 = _sha256_path(input_path)
    image = Image.open(input_path).convert("RGBA")
    removed: list[dict[str, object]] = []
    pixels = image.load()
    for component in _alpha_components(image):
        if len(component) > maximum_area:
            continue
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        for x, y in component:
            pixels[x, y] = (0, 0, 0, 0)
        removed.append(
            {
                "area": len(component),
                "bbox": [
                    min(xs),
                    min(ys),
                    max(xs) + 1,
                    max(ys) + 1,
                ],
            }
        )
    if not removed:
        raise ValueError("no isolated alpha components matched the limit")

    _save_png_atomic(image, output_path)
    receipt = {
        "schema_version": 1,
        "method": "bounded_isolated_alpha_component_removal_v1",
        "input_path": input_path.as_posix(),
        "input_sha256": input_sha256,
        "output_path": output_path.as_posix(),
        "output_sha256": _sha256_path(output_path),
        "maximum_area": maximum_area,
        "removed_components": removed,
        "removed_pixel_count": sum(
            int(component["area"]) for component in removed
        ),
    }
    _write_json_atomic(receipt_path, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove small disconnected alpha components from a pose."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--maximum-area", type=int, required=True)
    args = parser.parse_args()
    receipt = remove_isolated_components(
        args.input,
        args.output,
        args.receipt,
        maximum_area=args.maximum_area,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
