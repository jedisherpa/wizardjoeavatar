#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_hd_phazer_pose_masters import (
    _build_contact_sheet,
    _extract_sheet_frames,
    _normalize_sheet_frames,
)
from wizard_avatar.hd_pose_artifact import write_pose_artifact


DEFAULT_CENSUS = (
    ROOT
    / "assets"
    / "reference"
    / "joeville_48_parity"
    / "source-metadata"
    / "archive-census-v001.json"
)
DEFAULT_TRACKER = (
    ROOT
    / "assets"
    / "reference"
    / "joeville_48_parity"
    / "source-metadata"
    / "parity-tracker-v001.json"
)
DEFAULT_AUTHORITY = (
    ROOT / "assets" / "reference" / "hd_canonical" / "manifest.json"
)
DEFAULT_OUTPUT_ROOT = (
    ROOT / "assets" / "reference" / "joeville_48_parity"
)
EXTRACTION_PROFILE = {
    "background_min_channel": 210,
    "background_max_channel_spread": 64,
    "minimum_component_area": 24,
    "maximum_source_scale": 2.1,
    "frame_grouping": "nearest_expected_center_by_component_centroid",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as destination:
        json.dump(value, destination, indent=2, sort_keys=True)
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())
    temporary.replace(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _archive_paths_by_id(
    census: dict[str, Any], paths: Iterable[Path]
) -> dict[str, Path]:
    supplied = [path.expanduser().resolve() for path in paths]
    by_hash = {_sha256_file(path): path for path in supplied}
    resolved: dict[str, Path] = {}
    for archive in census["archives"]:
        path = by_hash.get(archive["sha256"])
        if path is None:
            raise ValueError(
                f"missing archive {archive['filename']} with SHA-256 "
                f"{archive['sha256']}"
            )
        resolved[archive["archive_id"]] = path
    return resolved


def _character_record(
    tracker: dict[str, Any], character_id: str
) -> dict[str, Any]:
    for character in tracker["characters"]:
        if character["character_id"] == character_id:
            return character
    raise ValueError(f"unknown JoeVille authority character: {character_id}")


def _selected_source(sequence: dict[str, Any]) -> dict[str, Any] | None:
    selected = sequence.get("selected_source")
    if selected is not None:
        return selected
    candidates = sequence.get("source_candidates", [])
    unique_hashes = {candidate["member_sha256"] for candidate in candidates}
    if len(candidates) == 1 and len(unique_hashes) == 1:
        return candidates[0]
    return None


def _local_background_rgb(
    rgb_pixels: Any,
    alpha_pixels: Any,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    radius: int = 4,
) -> tuple[int, int, int]:
    samples: list[tuple[int, int, int]] = []
    for sample_y in range(max(0, y - radius), min(height, y + radius + 1)):
        for sample_x in range(
            max(0, x - radius), min(width, x + radius + 1)
        ):
            if alpha_pixels[sample_x, sample_y] == 0:
                sample = rgb_pixels[sample_x, sample_y]
                if max(sample) >= 200:
                    samples.append(sample)
    if not samples:
        return 250, 250, 250
    return tuple(
        round(sum(sample[channel] for sample in samples) / len(samples))
        for channel in range(3)
    )


def _refine_checkerboard_matte(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    eroded = alpha.filter(ImageFilter.MinFilter(5))
    rgb = rgba.convert("RGB")
    rgb_pixels = rgb.load()
    alpha_pixels = alpha.load()
    eroded_pixels = eroded.load()
    width, height = rgba.size
    output = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    output_pixels = output.load()
    for y in range(height):
        for x in range(width):
            if alpha_pixels[x, y] == 0:
                continue
            source_rgb = rgb_pixels[x, y]
            if eroded_pixels[x, y] > 0:
                output_pixels[x, y] = (*source_rgb, 255)
                continue
            background_rgb = _local_background_rgb(
                rgb_pixels,
                alpha_pixels,
                x=x,
                y=y,
                width=width,
                height=height,
            )
            contrast = max(
                abs(source_rgb[channel] - background_rgb[channel])
                for channel in range(3)
            )
            chroma = max(source_rgb) - min(source_rgb)
            estimated_alpha = min(1.0, max(contrast, chroma) / 96.0)
            if estimated_alpha < 0.25:
                continue
            foreground = tuple(
                max(
                    0,
                    min(
                        255,
                        round(
                            (
                                source_rgb[channel]
                                - (1.0 - estimated_alpha)
                                * background_rgb[channel]
                            )
                            / estimated_alpha
                        ),
                    ),
                )
                for channel in range(3)
            )
            output_pixels[x, y] = (
                *foreground,
                round(estimated_alpha * 255),
            )
    return output


def _trim_neutral_fringe(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    red, green, blue, alpha = rgba.split()
    alpha = alpha.point(lambda value: 0 if value < 32 else value)
    opaque = alpha.point(lambda value: 255 if value else 0)
    boundary_band = ImageChops.subtract(
        opaque, opaque.filter(ImageFilter.MinFilter(5))
    )
    minimum = ImageChops.darker(ImageChops.darker(red, green), blue)
    maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    spread = ImageChops.subtract(maximum, minimum)
    bright_neutral = ImageChops.multiply(
        minimum.point(lambda value: 255 if value > 220 else 0),
        spread.point(lambda value: 255 if value < 70 else 0),
    )
    remove = ImageChops.multiply(boundary_band, bright_neutral)
    alpha = ImageChops.subtract(alpha, remove)
    kept = alpha.point(lambda value: 255 if value else 0)
    rgb = Image.merge("RGB", (red, green, blue))
    rgb = Image.composite(rgb, Image.new("RGB", rgba.size), kept)
    rgb.putalpha(alpha)
    return rgb


def _library_index(
    *,
    character_id: str,
    display_name: str,
    profile: dict[str, Any],
    receipt: dict[str, Any],
    sequence_pose_ids: dict[str, list[str]],
    complete: bool,
) -> dict[str, Any]:
    all_pose_ids = [
        pose_id
        for sequence in sequence_pose_ids.values()
        for pose_id in sequence
    ]
    approval_state = (
        "candidate_visual_parity"
        if complete
        else "candidate_source_partial"
    )
    shard_id = f"{character_id}-source-motion-v001"
    return {
        "schema_version": 1,
        "asset_set_id": shard_id,
        "character_id": character_id,
        "display_name": display_name,
        "profile": profile,
        "pose_count": len(all_pose_ids),
        "approved_pose_count": 0,
        "candidate_pose_count": len(all_pose_ids),
        "review_projection": True,
        "runtime_admitted": False,
        "sequences": {
            f"{character_id}-source-all": {
                "fps": 8,
                "loop": True,
                "pose_ids": all_pose_ids,
                "approval_state": approval_state,
                "runtime_admitted": False,
            },
            **{
                sequence_id: {
                    "fps": 8,
                    "loop": True,
                    "pose_ids": pose_ids,
                    "approval_state": approval_state,
                    "runtime_admitted": False,
                }
                for sequence_id, pose_ids in sequence_pose_ids.items()
            },
        },
        "shards": [
            {
                "shard_id": shard_id,
                "source": "joeville_contact_sheet_reconstruction",
                "approval_state": approval_state,
                "runtime_admitted": False,
                "path": receipt["path"],
                "sha256": receipt["sha256"],
                "bytes": receipt["bytes"],
                "pose_count": receipt["pose_count"],
                "pose_ids": receipt["pose_ids"],
            }
        ],
    }


def build_character(
    *,
    character_id: str,
    archive_paths: Iterable[Path],
    census_path: Path = DEFAULT_CENSUS,
    tracker_path: Path = DEFAULT_TRACKER,
    authority_path: Path = DEFAULT_AUTHORITY,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    allow_partial: bool = False,
) -> dict[str, Any]:
    census = _read_json(census_path.resolve())
    tracker = _read_json(tracker_path.resolve())
    authority = _read_json(authority_path.resolve())
    character = _character_record(tracker, character_id)
    archives = _archive_paths_by_id(census, archive_paths)
    profile = dict(authority["master_profile"])
    selected_sequences: list[tuple[dict[str, Any], dict[str, Any]]] = []
    missing_sequences: list[str] = []
    for sequence in character["source_sequences"]:
        source = _selected_source(sequence)
        if source is None:
            missing_sequences.append(sequence["sequence_id"])
            continue
        selected_sequences.append((sequence, source))
    if missing_sequences and not allow_partial:
        raise ValueError(
            f"{character_id} is missing source sequences: "
            + ", ".join(missing_sequences)
        )

    poses: dict[str, Image.Image] = {}
    records: list[dict[str, Any]] = []
    sequence_pose_ids: dict[str, list[str]] = {}
    pose_number = 1
    for sequence, source in selected_sequences:
        archive_path = archives[source["archive_id"]]
        with zipfile.ZipFile(archive_path) as archive:
            payload = archive.read(source["member_name"])
        payload_sha256 = hashlib.sha256(payload).hexdigest()
        if payload_sha256 != source["member_sha256"]:
            raise ValueError(
                f"{source['member_name']} no longer matches its selected hash"
            )
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            if image.size != (source["width"], source["height"]):
                raise ValueError(
                    f"{source['member_name']} dimensions differ from census"
                )
            frames = _extract_sheet_frames(
                image,
                frame_count=int(sequence["expected_pose_count"]),
                minimum=EXTRACTION_PROFILE["background_min_channel"],
                spread=EXTRACTION_PROFILE[
                    "background_max_channel_spread"
                ],
                minimum_area=EXTRACTION_PROFILE["minimum_component_area"],
            )
            for frame in frames:
                frame["image"] = _refine_checkerboard_matte(frame["image"])
        frames = _normalize_sheet_frames(
            frames,
            profile=profile,
            maximum_scale=EXTRACTION_PROFILE["maximum_source_scale"],
            sharpen=False,
        )
        for frame in frames:
            frame["image"] = _trim_neutral_fringe(frame["image"])
            output_bbox = frame["image"].getchannel("A").getbbox()
            if output_bbox is None:
                raise ValueError("neutral-fringe removal erased a source pose")
            frame["output_bbox"] = output_bbox
        sequence_pose_ids[sequence["sequence_id"]] = []
        for local_index, frame in enumerate(frames, start=1):
            pose_id = (
                f"{character_id.replace('-', '_')}_motion_{pose_number:03d}"
            )
            poses[pose_id] = frame["image"]
            sequence_pose_ids[sequence["sequence_id"]].append(pose_id)
            rgba = frame["image"].tobytes()
            records.append(
                {
                    "pose_id": pose_id,
                    "motion_slot_id": f"motion-{pose_number:03d}",
                    "sequence_id": sequence["sequence_id"],
                    "source_frame_index": local_index,
                    "source_archive_id": source["archive_id"],
                    "source_archive_sha256": source["archive_sha256"],
                    "source_member": source["member_name"],
                    "source_member_sha256": source["member_sha256"],
                    "source_bbox": list(frame["source_bbox"]),
                    "normalization_scale": round(frame["scale"], 8),
                    "output_bbox": list(frame["output_bbox"]),
                    "rgba_sha256": hashlib.sha256(rgba).hexdigest(),
                    "approval_state": "pending_visual_parity",
                    "runtime_admitted": False,
                }
            )
            pose_number += 1
    if not poses:
        raise ValueError(f"{character_id} has no selected source poses")

    complete = len(poses) == int(
        tracker["contract"]["target_pose_count_per_character"]
    )
    compiled_dir = output_root / "compiled" / character_id
    compiled_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = f"{character_id}-candidate-source-motion-v001.wjpose"
    artifact_path = compiled_dir / artifact_name
    temporary_artifact = artifact_path.with_name(
        f".{artifact_path.name}.{os.getpid()}.tmp"
    )
    receipt = write_pose_artifact(
        temporary_artifact,
        poses,
        profile=profile,
        provenance={
            "asset_set_id": f"{character_id}-source-motion-v001",
            "character_id": character_id,
            "source_census_sha256": _sha256_file(census_path.resolve()),
            "parity_tracker_sha256": _sha256_file(tracker_path.resolve()),
            "approval_state": (
                "candidate_visual_parity"
                if complete
                else "candidate_source_partial"
            ),
            "runtime_admitted": False,
            "reconstruction": "edge_connected_checkerboard_alpha_v1",
        },
    )
    temporary_artifact.replace(artifact_path)
    receipt["path"] = artifact_name

    index = _library_index(
        character_id=character_id,
        display_name=character["display_name"],
        profile=profile,
        receipt=receipt,
        sequence_pose_ids=sequence_pose_ids,
        complete=complete,
    )
    index_path = compiled_dir / "library-index.json"
    _write_json_atomic(index_path, index)

    review_dir = output_root / "source-metadata" / character_id
    contact_sheet_path = review_dir / "source-motion-contact-sheet-v001.png"
    _build_contact_sheet(poses, records, contact_sheet_path)
    reconstruction = {
        "schema_version": 1,
        "character_id": character_id,
        "display_name": character["display_name"],
        "status": (
            "candidate_visual_parity"
            if complete
            else "candidate_source_partial"
        ),
        "runtime_admitted": False,
        "target_pose_count": 48,
        "compiled_pose_count": len(poses),
        "missing_sequences": missing_sequences,
        "source_census_sha256": _sha256_file(census_path.resolve()),
        "parity_tracker_sha256": _sha256_file(tracker_path.resolve()),
        "extraction_profile": EXTRACTION_PROFILE,
        "artifact": {
            **receipt,
            "path": str(artifact_path.relative_to(output_root)),
        },
        "library_index": {
            "path": str(index_path.relative_to(output_root)),
            "sha256": _sha256_file(index_path),
        },
        "review_contact_sheet": {
            "path": str(contact_sheet_path.relative_to(output_root)),
            "sha256": _sha256_file(contact_sheet_path),
        },
        "sequences": sequence_pose_ids,
        "poses": records,
    }
    reconstruction_path = review_dir / "reconstruction-manifest-v001.json"
    _write_json_atomic(reconstruction_path, reconstruction)
    return {
        "character_id": character_id,
        "complete": complete,
        "pose_count": len(poses),
        "missing_sequences": missing_sequences,
        "artifact_path": str(artifact_path),
        "artifact_sha256": receipt["sha256"],
        "library_index_path": str(index_path),
        "library_index_sha256": _sha256_file(index_path),
        "reconstruction_manifest_path": str(reconstruction_path),
        "contact_sheet_path": str(contact_sheet_path),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct selected JoeVille source sheets as transparent "
            "canonical-canvas pixel-graph artifacts."
        )
    )
    parser.add_argument("character_id")
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("--census", type=Path, default=DEFAULT_CENSUS)
    parser.add_argument("--tracker", type=Path, default=DEFAULT_TRACKER)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Compile available selected poses without padding missing slots.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = build_character(
        character_id=args.character_id,
        archive_paths=args.archives,
        census_path=args.census,
        tracker_path=args.tracker,
        authority_path=args.authority,
        output_root=args.output_root,
        allow_partial=args.allow_partial,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
