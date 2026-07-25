#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from PIL import Image


SCHEMA_VERSION = 1
EXPECTED_ARCHIVE_HASHES = {
    "Sprites 1.zip": "a26b2fb59fba19b494c97c278dc5da4cd0df5a2d58e989759da521804a1206a8",
    "Sprites 2.zip": "570d20086ad833b018188eee9c7d3368e5a156139e67c62b474f86cb50bfa749",
    "Sprites 3.zip": "f9f7dfe99c1043e2008f58b25999e36888515f48fa64e337bde97a8af0bb9a52",
}
AUTHORITY_ROSTER = (
    ("serena-quill", "Serena Quill"),
    ("aurelia-finch", "Aurelia Finch"),
    ("selene-hart", "Selene Hart"),
    ("thorne-vale", "Thorne Vale"),
    ("elara-voss", "Elara Voss"),
    ("kai-renner", "Kai Renner"),
    ("mira-solen", "Mira Solen"),
    ("draven-holt", "Draven Holt"),
    ("liora-kane", "Liora Kane"),
    ("rohan-slate", "Rohan Slate"),
    ("finn-calder", "Finn Calder"),
    ("orion-vale", "Orion Vale"),
)
SUPPLIED_EXTRA_CHARACTERS = (("crystail", "Crystail"),)
REFERENCE_CHARACTERS = (("wizard-joe", "Wizard Joe"),)
KNOWN_CHARACTERS = (
    *AUTHORITY_ROSTER,
    *SUPPLIED_EXTRA_CHARACTERS,
    *REFERENCE_CHARACTERS,
)
SEQUENCE_PATTERN = re.compile(r"(?:^|[-_])([wgp]\d+[ab]?)$", re.IGNORECASE)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as destination:
        json.dump(value, destination, indent=2, sort_keys=True)
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())
    temporary.replace(path)


def _normalized_stem(member_name: str) -> str:
    return Path(member_name).stem.lower().replace("_", "-")


def _character_id(member_name: str) -> str | None:
    stem = _normalized_stem(member_name)
    for character_id, _display_name in sorted(
        KNOWN_CHARACTERS, key=lambda item: len(item[0]), reverse=True
    ):
        if character_id in stem:
            return character_id
    return None


def _category(member_name: str) -> str:
    stem = _normalized_stem(member_name)
    if stem.startswith("char-"):
        return "character_reference"
    if stem.startswith("strip-"):
        return "sprite_strip"
    if stem.startswith("sheet-"):
        return "sprite_sheet"
    if stem.startswith("vehicle-"):
        return "vehicle_reference"
    return "unclassified"


def _sequence_id(member_name: str) -> str | None:
    match = SEQUENCE_PATTERN.search(_normalized_stem(member_name))
    return match.group(1).lower() if match else None


def _alpha_profile(image: Image.Image) -> dict[str, Any]:
    has_alpha = "A" in image.getbands() or "transparency" in image.info
    if not has_alpha:
        return {
            "has_alpha": False,
            "minimum": None,
            "maximum": None,
            "transparent_pixels": 0,
            "partial_alpha_pixels": 0,
            "opaque_pixels": image.width * image.height,
        }
    alpha = image.convert("RGBA").getchannel("A")
    histogram = alpha.histogram()
    minimum = next(index for index, count in enumerate(histogram) if count)
    maximum = next(
        index for index in range(255, -1, -1) if histogram[index]
    )
    return {
        "has_alpha": True,
        "minimum": minimum,
        "maximum": maximum,
        "transparent_pixels": histogram[0],
        "partial_alpha_pixels": sum(histogram[1:255]),
        "opaque_pixels": histogram[255],
    }


def _corner_rgb(image: Image.Image) -> list[list[int]]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    return [
        list(rgb.getpixel(point))
        for point in (
            (0, 0),
            (width - 1, 0),
            (0, height - 1),
            (width - 1, height - 1),
        )
    ]


def _inspect_member(
    archive_id: str, member_name: str, payload: bytes
) -> dict[str, Any]:
    with Image.open(io.BytesIO(payload)) as image:
        image.load()
        return {
            "archive_id": archive_id,
            "member_name": member_name,
            "bytes": len(payload),
            "sha256": _sha256_bytes(payload),
            "declared_extension": Path(member_name).suffix.lower(),
            "decoded_format": image.format,
            "mode": image.mode,
            "width": image.width,
            "height": image.height,
            "alpha": _alpha_profile(image),
            "corner_rgb": _corner_rgb(image),
            "category": _category(member_name),
            "character_id": _character_id(member_name),
            "sequence_id": _sequence_id(member_name),
        }


def _archive_record(path: Path, archive_index: int) -> dict[str, Any]:
    archive_id = f"sprites-{archive_index}"
    expected_sha256 = EXPECTED_ARCHIVE_HASHES.get(path.name)
    actual_sha256 = _sha256_file(path)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ValueError(
            f"{path.name} checksum mismatch: expected {expected_sha256}, "
            f"got {actual_sha256}"
        )
    with zipfile.ZipFile(path) as archive:
        member_names = sorted(
            name for name in archive.namelist() if not name.endswith("/")
        )
        members = [
            _inspect_member(archive_id, name, archive.read(name))
            for name in member_names
        ]
    return {
        "archive_id": archive_id,
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": actual_sha256,
        "expected_sha256": expected_sha256,
        "hash_matches_expected": expected_sha256 in (None, actual_sha256),
        "member_count": len(members),
        "members": members,
    }


def _duplicate_records(
    archives: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for archive in archives:
        for member in archive["members"]:
            occurrence = {
                "archive_id": archive["archive_id"],
                "member_name": member["member_name"],
                "sha256": member["sha256"],
            }
            by_name[member["member_name"]].append(occurrence)
            by_hash[member["sha256"]].append(occurrence)
    duplicate_names = [
        {
            "member_name": member_name,
            "occurrences": occurrences,
            "byte_identical": len({item["sha256"] for item in occurrences}) == 1,
        }
        for member_name, occurrences in sorted(by_name.items())
        if len(occurrences) > 1
    ]
    duplicate_payloads = [
        {
            "sha256": sha256,
            "occurrences": occurrences,
            "same_member_name": len(
                {item["member_name"] for item in occurrences}
            )
            == 1,
        }
        for sha256, occurrences in sorted(by_hash.items())
        if len(occurrences) > 1
    ]
    return duplicate_names, duplicate_payloads


def _character_records(archives: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    display_names = dict(KNOWN_CHARACTERS)
    authority_ids = {character_id for character_id, _name in AUTHORITY_ROSTER}
    extra_ids = {
        character_id for character_id, _name in SUPPLIED_EXTRA_CHARACTERS
    }
    reference_ids = {
        character_id for character_id, _name in REFERENCE_CHARACTERS
    }
    members_by_character: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for archive in archives:
        for member in archive["members"]:
            character_id = member["character_id"]
            if character_id is not None:
                members_by_character[character_id].append(
                    {
                        "archive_id": archive["archive_id"],
                        "member_name": member["member_name"],
                        "category": member["category"],
                        "sequence_id": member["sequence_id"],
                        "sha256": member["sha256"],
                        "width": member["width"],
                        "height": member["height"],
                        "mode": member["mode"],
                        "has_alpha": member["alpha"]["has_alpha"],
                    }
                )
    records: list[dict[str, Any]] = []
    for character_id, display_name in KNOWN_CHARACTERS:
        members = sorted(
            members_by_character.get(character_id, []),
            key=lambda item: (item["archive_id"], item["member_name"]),
        )
        if character_id in authority_ids:
            roster_state = "authority_roster"
        elif character_id in extra_ids:
            roster_state = "supplied_extra_not_admitted"
        elif character_id in reference_ids:
            roster_state = "reference_baseline"
        else:
            roster_state = "unclassified"
        records.append(
            {
                "character_id": character_id,
                "display_name": display_names[character_id],
                "roster_state": roster_state,
                "source_member_count": len(members),
                "members": members,
            }
        )
    return records


def census(archive_paths: Iterable[Path]) -> dict[str, Any]:
    paths = [path.resolve() for path in archive_paths]
    if not paths:
        raise ValueError("at least one sprite archive is required")
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"sprite archives not found: {', '.join(missing)}")
    archives = [
        _archive_record(path, archive_index)
        for archive_index, path in enumerate(paths, start=1)
    ]
    duplicate_names, duplicate_payloads = _duplicate_records(archives)
    unclassified = sorted(
        {
            member["member_name"]
            for archive in archives
            for member in archive["members"]
            if member["character_id"] is None
            and member["category"] != "vehicle_reference"
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": {
            "purpose": "JoeVille 12-character 48-motion source census",
            "runtime_admission": False,
            "visual_parity": "not_evaluated",
            "source_art_only": True,
        },
        "authority_roster": [
            {"character_id": character_id, "display_name": display_name}
            for character_id, display_name in AUTHORITY_ROSTER
        ],
        "supplied_extra_characters": [
            {"character_id": character_id, "display_name": display_name}
            for character_id, display_name in SUPPLIED_EXTRA_CHARACTERS
        ],
        "archives": archives,
        "characters": _character_records(archives),
        "duplicate_member_names": duplicate_names,
        "duplicate_payloads": duplicate_payloads,
        "unclassified_image_members": unclassified,
        "totals": {
            "archive_count": len(archives),
            "image_member_count": sum(
                archive["member_count"] for archive in archives
            ),
            "authority_character_count": len(AUTHORITY_ROSTER),
            "supplied_extra_character_count": len(
                SUPPLIED_EXTRA_CHARACTERS
            ),
            "duplicate_member_name_count": len(duplicate_names),
            "duplicate_payload_count": len(duplicate_payloads),
            "unclassified_image_member_count": len(unclassified),
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fingerprint and inspect JoeVille sprite archives without "
            "extracting or admitting pose art."
        )
    )
    parser.add_argument(
        "archives",
        nargs="+",
        type=Path,
        help="Sprite ZIP archives in deterministic pack order.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination JSON census.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = census(args.archives)
    _write_json_atomic(args.output.resolve(), result)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "archives": result["totals"]["archive_count"],
                "members": result["totals"]["image_member_count"],
                "authority_characters": result["totals"][
                    "authority_character_count"
                ],
                "supplied_extra_characters": result["totals"][
                    "supplied_extra_character_count"
                ],
                "duplicate_member_names": result["totals"][
                    "duplicate_member_name_count"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
