#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import zipfile
from collections import deque
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import HDPoseLibrary, sha256_path, write_pose_artifact


HD_ROOT = ROOT / "assets" / "reference" / "hd_canonical"
DEFAULT_SOURCE_MANIFEST = (
    HD_ROOT
    / "source-metadata"
    / "phazer"
    / "phazer_sprite_manifest_v001.json"
)
DEFAULT_AUTHORITY_MANIFEST = HD_ROOT / "manifest.json"
DEFAULT_OUTPUT = HD_ROOT / "compiled"
DEFAULT_REVIEW = (
    HD_ROOT
    / "source-metadata"
    / "phazer"
    / "phazer_review_contact_sheet_v001.png"
)
PHAZER_SHARD_ID = "phazer_motion_v001"
PHAZER_SHARD_FILENAME = "candidate-phazer-motion-v001.wjpose"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_background_candidate(
    rgb: tuple[int, int, int], *, minimum: int, spread: int
) -> bool:
    return min(rgb) >= minimum and max(rgb) - min(rgb) <= spread


def _edge_connected_background(
    image: Image.Image, *, minimum: int, spread: int
) -> bytearray:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    background = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def enqueue(x: int, y: int) -> None:
        index = y * width + x
        if background[index]:
            return
        if not _is_background_candidate(
            pixels[x, y], minimum=minimum, spread=spread
        ):
            return
        background[index] = 1
        queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        if x > 0:
            enqueue(x - 1, y)
        if x + 1 < width:
            enqueue(x + 1, y)
        if y > 0:
            enqueue(x, y - 1)
        if y + 1 < height:
            enqueue(x, y + 1)
    return background


def _retained_foreground(
    background: bytearray, width: int, height: int, *, minimum_area: int
) -> bytearray:
    visited = bytearray(width * height)
    retained = bytearray(width * height)
    for start in range(width * height):
        if background[start] or visited[start]:
            continue
        component: list[int] = []
        queue = deque([start])
        visited[start] = 1
        while queue:
            index = queue.popleft()
            component.append(index)
            x = index % width
            y = index // width
            for neighbor in (
                index - 1 if x > 0 else -1,
                index + 1 if x + 1 < width else -1,
                index - width if y > 0 else -1,
                index + width if y + 1 < height else -1,
            ):
                if (
                    neighbor >= 0
                    and not background[neighbor]
                    and not visited[neighbor]
                ):
                    visited[neighbor] = 1
                    queue.append(neighbor)
        if len(component) >= minimum_area:
            for index in component:
                retained[index] = 1
    return retained


def _foreground_components(
    mask: bytearray, width: int, height: int
) -> list[list[int]]:
    visited = bytearray(width * height)
    components: list[list[int]] = []
    for start in range(width * height):
        if not mask[start] or visited[start]:
            continue
        component: list[int] = []
        queue = deque([start])
        visited[start] = 1
        while queue:
            index = queue.popleft()
            component.append(index)
            x = index % width
            y = index // width
            for neighbor in (
                index - 1 if x > 0 else -1,
                index + 1 if x + 1 < width else -1,
                index - width if y > 0 else -1,
                index + width if y + 1 < height else -1,
            ):
                if (
                    neighbor >= 0
                    and mask[neighbor]
                    and not visited[neighbor]
                ):
                    visited[neighbor] = 1
                    queue.append(neighbor)
        components.append(component)
    return components


def _mask_bbox(
    mask: bytearray, width: int, height: int
) -> tuple[int, int, int, int]:
    xs: list[int] = []
    ys: list[int] = []
    for y in range(height):
        row = y * width
        for x in range(width):
            if mask[row + x]:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise ValueError("no foreground found in reconstructed frame")
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def _extract_sheet_frames(
    image: Image.Image,
    *,
    frame_count: int,
    minimum: int,
    spread: int,
    minimum_area: int,
) -> list[dict[str, Any]]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    background = _edge_connected_background(rgb, minimum=minimum, spread=spread)
    mask = _retained_foreground(
        background, width, height, minimum_area=minimum_area
    )
    frame_masks = [bytearray(width * height) for _ in range(frame_count)]
    expected_centers = [
        width * (index + 0.5) / frame_count for index in range(frame_count)
    ]
    for component in _foreground_components(mask, width, height):
        centroid_x = sum(index % width for index in component) / len(component)
        frame_index = min(
            range(frame_count),
            key=lambda index: abs(centroid_x - expected_centers[index]),
        )
        frame_mask = frame_masks[frame_index]
        for pixel_index in component:
            frame_mask[pixel_index] = 1
    pixels = rgb.load()
    frames: list[dict[str, Any]] = []
    for frame_index, frame_mask in enumerate(frame_masks):
        bbox = _mask_bbox(frame_mask, width, height)
        x0, y0, x1, y1 = bbox
        rgba = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        output = rgba.load()
        for y in range(y0, y1):
            row = y * width
            for x in range(x0, x1):
                if frame_mask[row + x]:
                    output[x - x0, y - y0] = (*pixels[x, y], 255)
        frames.append(
            {
                "frame_index": frame_index,
                "source_bbox": bbox,
                "image": rgba,
            }
        )
    return frames


def _premultiplied_resize(
    image: Image.Image,
    size: tuple[int, int],
    *,
    sharpen: bool = True,
) -> Image.Image:
    rgba = image.convert("RGBA")
    red, green, blue, alpha = rgba.split()
    premultiplied = Image.merge(
        "RGBA",
        tuple(
            channel.point(lambda value: value)
            for channel in (red, green, blue, alpha)
        ),
    )
    source = list(premultiplied.getdata())
    premultiplied.putdata(
        [
            (
                round(r * a / 255),
                round(g * a / 255),
                round(b * a / 255),
                a,
            )
            for r, g, b, a in source
        ]
    )
    resized = premultiplied.resize(size, Image.Resampling.LANCZOS)
    unpremultiplied = []
    for r, g, b, a in resized.getdata():
        if a == 0:
            unpremultiplied.append((0, 0, 0, 0))
        else:
            unpremultiplied.append(
                (
                    min(255, round(r * 255 / a)),
                    min(255, round(g * 255 / a)),
                    min(255, round(b * 255 / a)),
                    a,
                )
            )
    resized.putdata(unpremultiplied)
    if sharpen:
        alpha = resized.getchannel("A")
        sharpened = resized.convert("RGB").filter(
            ImageFilter.UnsharpMask(radius=1.4, percent=170, threshold=2)
        )
        sharpened.putalpha(alpha)
        resized = sharpened
    return resized


def _normalize_sheet_frames(
    frames: list[dict[str, Any]],
    *,
    profile: dict[str, Any],
    maximum_scale: float,
    sharpen: bool = True,
) -> list[dict[str, Any]]:
    canvas_width = int(profile["canvas_width"])
    canvas_height = int(profile["canvas_height"])
    baseline_y = int(profile["baseline_y"])
    margin = int(profile["minimum_margin"])
    source_baseline = max(frame["source_bbox"][3] for frame in frames)
    source_top = min(frame["source_bbox"][1] for frame in frames)
    maximum_width = max(
        frame["source_bbox"][2] - frame["source_bbox"][0] for frame in frames
    )
    scale = min(
        maximum_scale,
        (baseline_y - margin) / max(1, source_baseline - source_top),
        (canvas_width - margin * 2) / max(1, maximum_width),
    )
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("invalid phazer normalization scale")

    normalized: list[dict[str, Any]] = []
    for frame in frames:
        x0, y0, x1, y1 = frame["source_bbox"]
        width = max(1, round((x1 - x0) * scale))
        height = max(1, round((y1 - y0) * scale))
        resized = _premultiplied_resize(
            frame["image"], (width, height), sharpen=sharpen
        )
        paste_x = round((canvas_width - width) / 2)
        paste_y = round(baseline_y + (y0 - source_baseline) * scale)
        if (
            paste_x < 0
            or paste_y < 0
            or paste_x + width > canvas_width
            or paste_y + height > canvas_height
        ):
            raise ValueError("normalized phazer frame exceeds canonical canvas")
        canvas = Image.new(
            "RGBA", (canvas_width, canvas_height), (0, 0, 0, 0)
        )
        canvas.alpha_composite(resized, (paste_x, paste_y))
        alpha_bbox = canvas.getchannel("A").getbbox()
        if alpha_bbox is None:
            raise ValueError("normalized phazer frame is transparent")
        if any(
            canvas.getchannel("A").getpixel(point) != 0
            for point in (
                (0, 0),
                (canvas_width - 1, 0),
                (0, canvas_height - 1),
                (canvas_width - 1, canvas_height - 1),
            )
        ):
            raise ValueError("normalized phazer frame has an occupied corner")
        normalized.append(
            {
                **frame,
                "image": canvas,
                "scale": scale,
                "output_bbox": alpha_bbox,
            }
        )
    return normalized


def _build_contact_sheet(
    poses: dict[str, Image.Image],
    records: list[dict[str, Any]],
    destination: Path,
) -> None:
    thumbnail_size = 256
    columns = 6
    rows = math.ceil(len(records) / columns)
    label_height = 28
    sheet = Image.new(
        "RGB",
        (columns * thumbnail_size, rows * (thumbnail_size + label_height)),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    checker = Image.new("RGB", (thumbnail_size, thumbnail_size), (246, 246, 246))
    checker_draw = ImageDraw.Draw(checker)
    cell = 16
    for y in range(0, thumbnail_size, cell):
        for x in range(0, thumbnail_size, cell):
            if (x // cell + y // cell) % 2:
                checker_draw.rectangle(
                    (x, y, x + cell - 1, y + cell - 1),
                    fill=(226, 226, 226),
                )
    for index, record in enumerate(records):
        pose_id = record["pose_id"]
        x = (index % columns) * thumbnail_size
        y = (index // columns) * (thumbnail_size + label_height)
        preview = poses[pose_id].resize(
            (thumbnail_size, thumbnail_size), Image.Resampling.LANCZOS
        )
        tile = checker.copy()
        tile.paste(preview.convert("RGB"), mask=preview.getchannel("A"))
        sheet.paste(tile, (x, y))
        draw.text((x + 6, y + thumbnail_size + 6), pose_id, fill=(20, 20, 20))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    sheet.save(temporary, format="PNG", optimize=True)
    temporary.replace(destination)


def _artifact_record(
    path: Path, receipt: dict[str, Any], *, pose_ids: Iterable[str]
) -> dict[str, Any]:
    return {
        "shard_id": PHAZER_SHARD_ID,
        "source": "phazer_contact_sheet_reconstruction",
        "approval_state": "candidate_visual_parity",
        "runtime_admitted": False,
        "path": path.name,
        "sha256": receipt["sha256"],
        "bytes": receipt["bytes"],
        "pose_count": receipt["pose_count"],
        "pose_ids": list(pose_ids),
    }


def build(
    *,
    archive_path: Path,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
    authority_manifest_path: Path = DEFAULT_AUTHORITY_MANIFEST,
    output_dir: Path = DEFAULT_OUTPUT,
    review_path: Path = DEFAULT_REVIEW,
) -> dict[str, Any]:
    source_manifest = _read_json(source_manifest_path.resolve())
    authority = _read_json(authority_manifest_path.resolve())
    if _sha256_file(archive_path.resolve()) != source_manifest["archive_sha256"]:
        raise ValueError("phazer source archive checksum mismatch")
    profile = authority["master_profile"]
    output_contract = source_manifest["output_contract"]
    for key in ("canvas_width", "canvas_height", "baseline_y", "minimum_margin"):
        if int(output_contract[key]) != int(profile[key]):
            raise ValueError(f"phazer output contract differs from HD profile: {key}")
    extraction = source_manifest["extraction"]
    frame_count = int(source_manifest["frames_per_sheet"])
    poses: dict[str, Image.Image] = {}
    records: list[dict[str, Any]] = []
    sequence_pose_ids: dict[str, list[str]] = {}

    with zipfile.ZipFile(archive_path.resolve()) as archive:
        actual_members = sorted(
            name for name in archive.namelist() if not name.endswith("/")
        )
        expected_members = sorted(sheet["member"] for sheet in source_manifest["sheets"])
        if actual_members != expected_members:
            raise ValueError("phazer source archive member inventory mismatch")
        pose_number = 1
        for sheet_number, sheet_record in enumerate(
            source_manifest["sheets"], start=1
        ):
            member = sheet_record["member"]
            payload = archive.read(member)
            image = Image.open(io.BytesIO(payload))
            image.load()
            expected_size = (
                int(sheet_record["width"]),
                int(sheet_record["height"]),
            )
            if image.size != expected_size:
                raise ValueError(f"{member} has unexpected dimensions {image.size}")
            frames = _extract_sheet_frames(
                image,
                frame_count=frame_count,
                minimum=int(extraction["background_min_channel"]),
                spread=int(extraction["background_max_channel_spread"]),
                minimum_area=int(extraction["minimum_component_area"]),
            )
            frames = _normalize_sheet_frames(
                frames,
                profile=profile,
                maximum_scale=float(extraction["maximum_source_scale"]),
            )
            sequence_id = sheet_record["sequence_id"]
            sequence_pose_ids[sequence_id] = []
            for local_index, frame in enumerate(frames, start=1):
                pose_id = (
                    f"phazer_{pose_number:03d}_s{sheet_number:02d}_f{local_index:02d}"
                )
                poses[pose_id] = frame["image"]
                sequence_pose_ids[sequence_id].append(pose_id)
                rgba = frame["image"].tobytes()
                records.append(
                    {
                        "pose_id": pose_id,
                        "sheet": member,
                        "sheet_sha256": hashlib.sha256(payload).hexdigest(),
                        "sheet_frame_index": local_index,
                        "source_bbox": list(frame["source_bbox"]),
                        "normalization_scale": round(frame["scale"], 8),
                        "output_bbox": list(frame["output_bbox"]),
                        "rgba_sha256": hashlib.sha256(rgba).hexdigest(),
                        "status": "candidate_visual_parity",
                    }
                )
                pose_number += 1

    if len(poses) != int(source_manifest["frame_count"]):
        raise ValueError("phazer reconstruction frame count mismatch")

    output_dir.mkdir(parents=True, exist_ok=True)
    shard_path = output_dir / PHAZER_SHARD_FILENAME
    temporary_shard_path = shard_path.with_name(shard_path.name + ".tmp")
    receipt = write_pose_artifact(
        temporary_shard_path,
        poses,
        profile=profile,
        provenance={
            "asset_set_id": authority["asset_set_id"],
            "source_pack_id": source_manifest["pack_id"],
            "source_archive_sha256": source_manifest["archive_sha256"],
            "approval_state": "candidate_visual_parity",
            "runtime_admitted": False,
            "reconstruction": "edge_connected_checkerboard_alpha_v1",
        },
    )
    temporary_shard_path.replace(shard_path)
    receipt["path"] = str(shard_path)
    shard_record = _artifact_record(
        shard_path, receipt, pose_ids=receipt["pose_ids"]
    )

    index_path = output_dir / "library-index.json"
    index = _read_json(index_path)
    old_shards = [
        shard
        for shard in index["shards"]
        if shard["shard_id"] != PHAZER_SHARD_ID
    ]
    old_pose_ids = {
        pose_id
        for shard in old_shards
        for pose_id in shard["pose_ids"]
    }
    if old_pose_ids.intersection(poses):
        raise ValueError("phazer pose IDs collide with the HD library")
    index["shards"] = old_shards + [shard_record]
    base_pose_ids = [
        pose_id
        for pose_id in index["sequences"]["all_hd_frames"]["pose_ids"]
        if pose_id not in poses
    ]
    phazer_pose_ids = list(poses)
    index["sequences"]["all_hd_frames"]["pose_ids"] = (
        base_pose_ids + phazer_pose_ids
    )
    index["sequences"]["all_hd_frames"][
        "approval_state"
    ] = "mixed_250_approved_58_candidate"
    index["sequences"]["all_hd_frames"][
        "runtime_note"
    ] = "Review reel only; includes approved production alphas and gated flight/phazer candidates."
    approved_pose_ids = [
        pose_id
        for shard in index["shards"]
        if shard["approval_state"] == "approved_production_alpha"
        for pose_id in shard["pose_ids"]
    ]
    index["sequences"]["approved_hd_frames"] = {
        "fps": 6,
        "loop": True,
        "pose_ids": approved_pose_ids,
        "approval_state": "approved_production_alpha",
        "runtime_admitted": False,
        "runtime_note": "Approved source-art baseline for visual comparison; motion admission remains separately governed.",
    }
    index["sequences"]["phazer_all"] = {
        "fps": 8,
        "loop": True,
        "pose_ids": phazer_pose_ids,
        "approval_state": "candidate_visual_parity",
        "runtime_admitted": False,
        "runtime_note": "Recovered alpha motion review; admission requires visual parity and animation gates.",
    }
    for sequence_id, pose_ids in sequence_pose_ids.items():
        index["sequences"][sequence_id] = {
            "fps": 8,
            "loop": True,
            "pose_ids": pose_ids,
            "approval_state": "candidate_visual_parity",
            "runtime_admitted": False,
        }
    index["pose_count"] = sum(int(shard["pose_count"]) for shard in index["shards"])
    index["approved_pose_count"] = sum(
        int(shard["pose_count"])
        for shard in index["shards"]
        if shard["approval_state"] == "approved_production_alpha"
    )
    index["candidate_pose_count"] = (
        index["pose_count"] - index["approved_pose_count"]
    )
    _write_json_atomic(index_path, index)

    _build_contact_sheet(poses, records, review_path)
    reconstruction_manifest = {
        "schema_version": 1,
        "pack_id": source_manifest["pack_id"],
        "source_archive_sha256": source_manifest["archive_sha256"],
        "profile": profile,
        "frame_count": len(records),
        "shard": shard_record,
        "review_contact_sheet": {
            "path": str(review_path.relative_to(HD_ROOT)),
            "sha256": sha256_path(review_path),
        },
        "frames": records,
    }
    reconstruction_path = source_manifest_path.parent / "reconstruction_manifest_v001.json"
    _write_json_atomic(reconstruction_path, reconstruction_manifest)

    index_sha256 = sha256_path(index_path)
    authority["sources"]["phazer_motion"] = {
        "archive_filename": source_manifest["archive_filename"],
        "archive_sha256": source_manifest["archive_sha256"],
        "manifest_path": str(source_manifest_path.relative_to(HD_ROOT)),
        "pack_id": source_manifest["pack_id"],
        "status": source_manifest["status"],
        "frame_count": len(records),
        "approval_scope": "reconstructed transparent alpha candidates",
    }
    authority["compiled_library_index"] = {
        "path": "compiled/library-index.json",
        "sha256": index_sha256,
        "pose_count": index["pose_count"],
        "approved_pose_count": index["approved_pose_count"],
        "candidate_pose_count": index["candidate_pose_count"],
        "runtime_admitted": False,
    }
    _write_json_atomic(authority_manifest_path, authority)
    return {
        "schema_version": 1,
        "pack_id": source_manifest["pack_id"],
        "pose_count": len(records),
        "library_pose_count": index["pose_count"],
        "library_index_sha256": index_sha256,
        "shard": shard_record,
        "reconstruction_manifest": str(reconstruction_path),
        "review_contact_sheet": str(review_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recover Wizard Joe phazer sheets into HD RGBA pixel artifacts"
    )
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument(
        "--authority-manifest", type=Path, default=DEFAULT_AUTHORITY_MANIFEST
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW)
    args = parser.parse_args()
    receipt = build(
        archive_path=args.archive,
        source_manifest_path=args.source_manifest,
        authority_manifest_path=args.authority_manifest,
        output_dir=args.output,
        review_path=args.review_output,
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
