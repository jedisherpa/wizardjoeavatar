from __future__ import annotations

from pathlib import Path
from typing import Tuple


def frame_to_image(frame, cell_size: Tuple[int, int] = (6, 6)):
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError("Pillow is required for PNG evidence: python3 -m pip install -r requirements.txt") from exc

    cell_w, cell_h = cell_size
    tile_size = max(1, min(cell_w, cell_h))
    image = Image.new("RGB", (frame.cols * cell_w, frame.rows * cell_h), "white")
    draw = ImageDraw.Draw(image)
    for i in range(0, len(frame.cells), 4):
        index = i // 4
        col = index % frame.cols
        row = index // frame.cols
        char = chr(frame.cells[i])
        if char == " ":
            continue
        rgb = tuple(frame.cells[i + 1 : i + 4])
        x = col * cell_w
        y = row * cell_h
        draw.rectangle((x, y, x + tile_size - 1, y + tile_size - 1), fill=rgb)
    return image


def frame_to_png(frame, path: str | Path, cell_size: Tuple[int, int] = (6, 6)) -> None:
    image = frame_to_image(frame, cell_size)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
