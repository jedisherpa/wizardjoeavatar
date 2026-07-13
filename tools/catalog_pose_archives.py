#!/usr/bin/env python3
"""Build the reproducible catalog for deferred WizardJoe pose references."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
INTAKE = ROOT / "evidence" / "pose-library-expansion" / "intake"
REGISTRY = ROOT / "docs" / "pose-library-expansion" / "registry.json"
OUTPUT = INTAKE / "manifest.json"
CONTACT_SHEETS = INTAKE / "contact-sheets"

PACKS = (
    {
        "id": "wizard-joe-poses-2",
        "directory": "poses2",
        "archive_name": "Wizard Joe Poses 2.zip",
        "archive_sha256": "2d81094336d8151958056b635c77998b2143a596af76200e0dbba7a175551df6",
        "candidate_prefix": "WJP2",
        "columns": 5,
    },
    {
        "id": "wizard-joe-poses-flying-and-action",
        "directory": "flying-action",
        "archive_name": "Wizard Joe Poses Flying and Action.zip",
        "archive_sha256": "c00e56b139c00c42d51652b3683109ae38263768dc959a25b17f83e533b5bfff",
        "candidate_prefix": "WJFA",
        "columns": 5,
    },
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_number(path: Path) -> int:
    match = re.search(r"\((\d+)\)\.png$", path.name)
    if match is None:
        raise ValueError(f"cannot determine source order for {path.name}")
    return int(match.group(1))


def build_contact_sheet(pack: dict[str, object], records: list[dict[str, object]]) -> Path:
    tile_width, tile_height = 320, 420
    columns = int(pack["columns"])
    rows = (len(records) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * tile_width, rows * tile_height), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=16)

    for index, record in enumerate(records):
        source = ROOT / str(record["repository_path"])
        with Image.open(source) as image:
            preview = image.convert("RGB")
            preview.thumbnail((tile_width - 24, tile_height - 58), Image.Resampling.LANCZOS)
        x = (index % columns) * tile_width
        y = (index // columns) * tile_height
        image_x = x + (tile_width - preview.width) // 2
        image_y = y + 8
        canvas.paste(preview, (image_x, image_y))
        label = f"{record['candidate_id']}  {record['semantic_id']}"
        draw.text((x + 10, y + tile_height - 38), label, fill="#111111", font=font)

    CONTACT_SHEETS.mkdir(parents=True, exist_ok=True)
    destination = CONTACT_SHEETS / f"{pack['id']}.jpg"
    canvas.save(destination, quality=92, optimize=True)
    return destination


def build_catalog() -> dict[str, object]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    candidates = {entry["archive_entry"]: entry for entry in registry["candidates"]}
    packs: list[dict[str, object]] = []
    total = 0

    for pack_config in PACKS:
        source_dir = INTAKE / str(pack_config["directory"])
        paths = sorted(source_dir.glob("*.png"), key=source_number)
        records: list[dict[str, object]] = []
        for path in paths:
            candidate = candidates[path.name]
            if not str(candidate["id"]).startswith(str(pack_config["candidate_prefix"])):
                raise ValueError(f"candidate/pack mismatch for {path.name}")
            with Image.open(path) as image:
                width, height = image.size
                mode = image.mode
            records.append(
                {
                    "candidate_id": candidate["id"],
                    "semantic_id": candidate["semantic_id"],
                    "source_filename": path.name,
                    "source_order": source_number(path),
                    "repository_path": str(path.relative_to(ROOT)),
                    "sha256": sha256(path),
                    "width": width,
                    "height": height,
                    "mode": mode,
                    "runtime_disposition": "reference_only",
                }
            )

        contact_sheet = build_contact_sheet(pack_config, records)
        packs.append(
            {
                "id": pack_config["id"],
                "archive_name": pack_config["archive_name"],
                "archive_sha256": pack_config["archive_sha256"],
                "image_count": len(records),
                "contact_sheet": str(contact_sheet.relative_to(ROOT)),
                "images": records,
            }
        )
        total += len(records)

    catalog = {
        "schema_version": 1,
        "generated_on": "2026-07-12",
        "purpose": "Deferred visual references for procedural WizardJoe pose integration",
        "runtime_policy": "Never load these PNGs at runtime; translate approved references into canonical cell geometry, anchors, regions, and transition rules.",
        "image_count": total,
        "packs": packs,
    }
    OUTPUT.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    return catalog


if __name__ == "__main__":
    result = build_catalog()
    print(json.dumps({"manifest": str(OUTPUT), "image_count": result["image_count"]}, indent=2))
