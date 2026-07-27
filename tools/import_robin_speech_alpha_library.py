#!/usr/bin/env python3
"""Ingest shared-canvas Robin/Speech alphas into review-only HD libraries."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import (  # noqa: E402
    HDPoseLibrary,
    sha256_path,
    write_pose_artifact_from_loader,
)

ROBIN_SPEECH_BASE_ARCHIVE_SHA256 = (
    "138750624356c7ddc8e56cd277da1e213df74eff0a72938e0c3c59a4a9dc5cfd"
)
PAIR_ARCHIVE_SHA256 = (
    "95a951a765ee3098342a0a5d385b7386716919c44241fc0c1d76f8223a7ff720"
)
CONTAMINATED_ARCHIVE_SHA256 = (
    "c7378b144453a9af98518f72025ac5237f17d44906d33c5a5683f1d45a1e1805"
)
DEFAULT_SOURCE_ROOT = (
    ROOT / "assets" / "reference" / "characters" / "robin_speech" / "source"
)
DEFAULT_OUTPUT_ROOT = (
    ROOT / "assets" / "reference" / "characters" / "robin_speech" / "compiled"
)
CANVAS_SIZE = (1920, 1080)
IDENTITY_SPLIT_X = 960
SOURCE_MANIFEST_NAME = "source-manifest-v003.json"
FRAME_PATTERN = re.compile(
    r"^(?P<ordinal>\d{3})_"
    r"(?P<family>ACT|FLY|INT)(?P<family_index>\d{3})_"
    r"(?P<slug>[a-z0-9_]+)_alpha\.png$"
)
FAMILY_RANGES = {
    "ACT": (1, 100, 0),
    "FLY": (1, 50, 100),
    "INT": (1, 50, 150),
}
IDENTITIES = {
    "robin": {
        "display_name": "Robin",
        "side": "left",
        "sequence": "robin-all",
    },
    "speech": {
        "display_name": "Speech",
        "side": "right",
        "sequence": "speech-all",
    },
}
PROFILE = {
    "profile_id": "robin_speech_hd_alpha_1920x1080_v003",
    "canvas_width": CANVAS_SIZE[0],
    "canvas_height": CANVAS_SIZE[1],
    "identity_split_x": IDENTITY_SPLIT_X,
    "identity_partition_policy": "seeded_component_geodesic_spatial_v003",
    "color_space": "sRGB",
    "alpha_mode": "binary_straight",
    "coordinate_policy": "preserve_shared_source_canvas",
}
SHARD_SIZE = 25
MIN_IDENTITY_SEED_PIXELS = 16


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as destination:
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _chroma_masks(image: Image.Image) -> tuple[Image.Image, Image.Image]:
    red, green, blue, alpha = image.convert("RGBA").split()

    def threshold(channel: Image.Image) -> Image.Image:
        return channel.point(lambda value: 255 if value > 10 else 0)

    green_mask = ImageChops.multiply(
        threshold(ImageChops.subtract(green, red)),
        threshold(ImageChops.subtract(green, blue)),
    )
    blue_mask = ImageChops.multiply(
        threshold(ImageChops.subtract(blue, red)),
        threshold(ImageChops.subtract(blue, green)),
    )
    return (
        ImageChops.multiply(green_mask, alpha),
        ImageChops.multiply(blue_mask, alpha),
    )


def _identity_seams(image: Image.Image) -> list[int]:
    green_mask, blue_mask = _chroma_masks(image)
    green = green_mask.tobytes()
    blue = blue_mask.tobytes()
    width, height = image.size
    candidates: list[int | None] = []
    for y in range(height):
        start = y * width
        end = start + width
        green_right = green.rfind(b"\xff", start, end)
        blue_left = blue.find(b"\xff", start, end)
        if green_right >= start and blue_left >= start:
            candidates.append(
                max(1, min(width - 1, (green_right - start + blue_left - start) // 2))
            )
        else:
            candidates.append(None)
    valid_rows = [index for index, value in enumerate(candidates) if value is not None]
    if not valid_rows:
        raise ValueError("frame does not contain both Robin-green and Speech-blue")
    seams = [IDENTITY_SPLIT_X] * height
    nearest = valid_rows[0]
    next_index = 0
    for y in range(height):
        while (
            next_index + 1 < len(valid_rows)
            and abs(valid_rows[next_index + 1] - y)
            <= abs(valid_rows[next_index] - y)
        ):
            next_index += 1
        nearest = valid_rows[next_index]
        seams[y] = int(candidates[nearest])
    smoothed = []
    for y in range(height):
        window = sorted(seams[max(0, y - 2) : min(height, y + 3)])
        smoothed.append(window[len(window) // 2])
    return smoothed


def _mask_seed(mask: Image.Image) -> tuple[int, int]:
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("identity seed mask is empty")
    center_x = (bbox[0] + bbox[2] - 1) // 2
    center_y = (bbox[1] + bbox[3] - 1) // 2
    pixels = mask.load()
    max_radius = max(bbox[2] - bbox[0], bbox[3] - bbox[1])
    for radius in range(max_radius + 1):
        top = max(bbox[1], center_y - radius)
        bottom = min(bbox[3] - 1, center_y + radius)
        left = max(bbox[0], center_x - radius)
        right = min(bbox[2] - 1, center_x + radius)
        for x in range(left, right + 1):
            if pixels[x, top]:
                return x, top
            if pixels[x, bottom]:
                return x, bottom
        for y in range(top + 1, bottom):
            if pixels[left, y]:
                return left, y
            if pixels[right, y]:
                return right, y
    raise ValueError("identity seed mask has no visible pixel")


def _seeded_component(alpha: Image.Image, seed_mask: Image.Image) -> Image.Image:
    component = alpha.copy()
    ImageDraw.floodfill(component, _mask_seed(seed_mask), 128, thresh=0)
    return component.point(lambda value: 255 if value == 128 else 0)


def _significant_chroma_mask(mask: Image.Image) -> Image.Image:
    significant = Image.new("L", CANVAS_SIZE, 0)
    remaining = mask
    while remaining.getbbox() is not None:
        component = _seeded_component(remaining, remaining)
        if component.histogram()[255] >= MIN_IDENTITY_SEED_PIXELS:
            significant = ImageChops.lighter(significant, component)
        remaining = ImageChops.subtract(remaining, component)
    return significant


def _consume_identity_components(
    residual: Image.Image,
    identity_seed: Image.Image,
    opposite_seed: Image.Image,
) -> tuple[Image.Image, Image.Image, Image.Image]:
    owned = Image.new("L", CANVAS_SIZE, 0)
    ambiguous = Image.new("L", CANVAS_SIZE, 0)
    remaining = residual
    while True:
        remaining_seed = ImageChops.multiply(identity_seed, remaining)
        if remaining_seed.getbbox() is None:
            return owned, ambiguous, remaining
        component = _seeded_component(remaining, remaining_seed)
        opposite_pixels = ImageChops.multiply(
            component,
            opposite_seed,
        ).histogram()[255]
        if opposite_pixels <= 64:
            owned = ImageChops.lighter(owned, component)
        else:
            ambiguous = ImageChops.lighter(ambiguous, component)
        remaining = ImageChops.subtract(remaining, component)


def _geodesic_identity_masks(
    component: Image.Image,
    green_seed: Image.Image,
    blue_seed: Image.Image,
) -> tuple[Image.Image, Image.Image]:
    bbox = component.getbbox()
    if bbox is None:
        blank = Image.new("L", CANVAS_SIZE, 0)
        return blank, blank.copy()
    cropped_component = component.crop(bbox)
    cropped_green = ImageChops.multiply(component, green_seed).crop(bbox)
    cropped_blue = ImageChops.multiply(component, blue_seed).crop(bbox)
    width, height = cropped_component.size
    visible = cropped_component.tobytes()
    green = cropped_green.tobytes()
    blue = cropped_blue.tobytes()
    labels = bytearray(width * height)
    frontier: deque[int] = deque()
    for index, value in enumerate(visible):
        if not value:
            continue
        if green[index]:
            labels[index] = 1
            frontier.append(index)
        elif blue[index]:
            labels[index] = 2
            frontier.append(index)
    if not frontier:
        raise ValueError("ambiguous identity component has no chromatic seed")
    while frontier:
        index = frontier.popleft()
        label = labels[index]
        x = index % width
        for neighbor in (
            index - width if index >= width else -1,
            index + width if index + width < len(labels) else -1,
            index - 1 if x else -1,
            index + 1 if x + 1 < width else -1,
        ):
            if (
                neighbor >= 0
                and visible[neighbor]
                and not labels[neighbor]
            ):
                labels[neighbor] = label
                frontier.append(neighbor)
    robin_crop = Image.frombytes(
        "L",
        (width, height),
        bytes(255 if label == 1 else 0 for label in labels),
    )
    speech_crop = Image.frombytes(
        "L",
        (width, height),
        bytes(255 if label == 2 else 0 for label in labels),
    )
    robin = Image.new("L", CANVAS_SIZE, 0)
    speech = Image.new("L", CANVAS_SIZE, 0)
    robin.paste(robin_crop, (bbox[0], bbox[1]))
    speech.paste(speech_crop, (bbox[0], bbox[1]))
    return robin, speech


def _identity_divider(
    green_seed: Image.Image,
    blue_seed: Image.Image,
) -> int:
    green_bbox = green_seed.getbbox()
    blue_bbox = blue_seed.getbbox()
    if green_bbox is None or blue_bbox is None:
        raise ValueError("frame does not contain both identity color signals")
    green_center = (green_bbox[0] + green_bbox[2]) // 2
    blue_center = (blue_bbox[0] + blue_bbox[2]) // 2
    return max(1, min(CANVAS_SIZE[0] - 1, (green_center + blue_center) // 2))


def _consume_spatial_components(
    residual: Image.Image,
    *,
    divider_x: int,
) -> tuple[Image.Image, Image.Image]:
    robin = Image.new("L", CANVAS_SIZE, 0)
    speech = Image.new("L", CANVAS_SIZE, 0)
    remaining = residual
    while True:
        bbox = remaining.getbbox()
        if bbox is None:
            return robin, speech
        component = _seeded_component(remaining, remaining)
        component_bbox = component.getbbox()
        if component_bbox is None:
            raise ValueError("residual component unexpectedly disappeared")
        left, _top, right, _bottom = component_bbox
        center_x = (left + right) // 2
        if left < divider_x < right and abs(center_x - divider_x) <= 24:
            left_mask = Image.new("L", CANVAS_SIZE, 0)
            ImageDraw.Draw(left_mask).rectangle(
                (0, 0, divider_x - 1, CANVAS_SIZE[1] - 1),
                fill=255,
            )
            robin = ImageChops.lighter(
                robin,
                ImageChops.multiply(component, left_mask),
            )
            speech = ImageChops.lighter(
                speech,
                ImageChops.subtract(component, left_mask),
            )
        elif center_x < divider_x:
            robin = ImageChops.lighter(robin, component)
        else:
            speech = ImageChops.lighter(speech, component)
        remaining = ImageChops.subtract(remaining, component)


def _identity_layers(image: Image.Image) -> tuple[Image.Image, Image.Image, list[int]]:
    rgba = image.convert("RGBA")
    seams = _identity_seams(rgba)
    alpha = rgba.getchannel("A")
    raw_green_seed, raw_blue_seed = _chroma_masks(rgba)
    green_seed = _significant_chroma_mask(raw_green_seed)
    blue_seed = _significant_chroma_mask(raw_blue_seed)
    if green_seed.getbbox() is None or blue_seed.getbbox() is None:
        raise ValueError("frame does not contain significant identity color signals")
    robin_mask = Image.new("L", CANVAS_SIZE, 0)
    speech_mask = Image.new("L", CANVAS_SIZE, 0)
    residual = alpha
    robin_owned, robin_ambiguous, residual = _consume_identity_components(
        residual,
        green_seed,
        blue_seed,
    )
    speech_owned, speech_ambiguous, residual = _consume_identity_components(
        residual,
        blue_seed,
        green_seed,
    )
    robin_mask = ImageChops.lighter(robin_mask, robin_owned)
    speech_mask = ImageChops.lighter(speech_mask, speech_owned)
    ambiguous = ImageChops.lighter(robin_ambiguous, speech_ambiguous)
    robin_ambiguous_mask, speech_ambiguous_mask = _geodesic_identity_masks(
        ambiguous,
        green_seed,
        blue_seed,
    )
    robin_mask = ImageChops.lighter(robin_mask, robin_ambiguous_mask)
    speech_mask = ImageChops.lighter(speech_mask, speech_ambiguous_mask)
    robin_unresolved, speech_unresolved = _consume_spatial_components(
        residual,
        divider_x=_identity_divider(green_seed, blue_seed),
    )
    robin_mask = ImageChops.lighter(robin_mask, robin_unresolved)
    speech_mask = ImageChops.lighter(speech_mask, speech_unresolved)
    assigned = ImageChops.lighter(robin_mask, speech_mask)
    if ImageChops.subtract(alpha, assigned).getbbox() is not None:
        raise ValueError("identity partition left visible pixels unassigned")
    if ImageChops.multiply(robin_mask, speech_mask).getbbox() is not None:
        raise ValueError("identity partition assigned pixels to both identities")
    robin = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    speech = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    robin.paste(rgba, (0, 0), robin_mask)
    speech.paste(rgba, (0, 0), speech_mask)
    return robin, speech, seams


def _project_path(path: Path, role: str) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{role} must stay inside the project root") from exc
    if not relative.parts:
        raise ValueError(f"{role} cannot be the project root")
    return relative.as_posix()


def _parse_frame_name(name: str) -> dict[str, Any]:
    match = FRAME_PATTERN.fullmatch(name)
    if match is None:
        raise ValueError(f"invalid alpha filename: {name}")
    ordinal = int(match["ordinal"])
    family = match["family"]
    family_index = int(match["family_index"])
    first, last, offset = FAMILY_RANGES[family]
    if not first <= family_index <= last:
        raise ValueError(f"family index is out of range: {name}")
    if ordinal != offset + family_index:
        raise ValueError(f"ordinal/family index mismatch: {name}")
    return {
        "ordinal": ordinal,
        "family": family,
        "family_index": family_index,
        "slug": match["slug"],
        "pose_suffix": (
            f"{family.lower()}.{family_index:03d}."
            f"{match['slug'].replace('_', '-')}"
        ),
    }


def _validate_png(payload: bytes, *, name: str) -> dict[str, Any]:
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            if image.format != "PNG":
                raise ValueError(f"{name} is not a PNG")
            if image.mode != "RGBA":
                raise ValueError(f"{name} must be RGBA")
            if image.size != CANVAS_SIZE:
                raise ValueError(f"{name} must be exactly 1920x1080")
            alpha = image.getchannel("A")
            extrema = alpha.getextrema()
            if extrema != (0, 255):
                raise ValueError(f"{name} must contain transparent and opaque pixels")
            histogram = alpha.histogram()
            if sum(histogram[1:255]):
                raise ValueError(f"{name} alpha must be binary")
            robin, speech, seams = _identity_layers(image)
            robin_bbox = robin.getchannel("A").getbbox()
            speech_bbox = speech.getchannel("A").getbbox()
            if robin_bbox is None or speech_bbox is None:
                raise ValueError(f"{name} must contain both Robin and Speech")
            if (robin_bbox[0] + robin_bbox[2]) >= (
                speech_bbox[0] + speech_bbox[2]
            ):
                raise ValueError(f"{name} violates Robin-left/Speech-right ordering")
            robin_green, robin_blue = _chroma_masks(robin)
            speech_green, speech_blue = _chroma_masks(speech)
            robin_blue_pixels = robin_blue.histogram()[255]
            speech_green_pixels = speech_green.histogram()[255]
            if robin_green.getbbox() is None:
                raise ValueError(f"{name} has no Robin-green identity signal")
            if speech_blue.getbbox() is None:
                raise ValueError(f"{name} has no Speech-blue identity signal")
            if robin_blue_pixels > 64:
                raise ValueError(f"{name} leaks Speech-blue pixels into Robin")
            if speech_green_pixels > 64:
                raise ValueError(f"{name} leaks Robin-green pixels into Speech")
            full_bbox = alpha.getbbox()
            if full_bbox is None:
                raise ValueError(f"{name} has no visible pixels")
            return {
                "canvas_size": list(image.size),
                "mode": image.mode,
                "alpha_extrema": list(extrema),
                "full_bbox": list(full_bbox),
                "robin_bbox": list(robin_bbox),
                "speech_bbox": list(speech_bbox),
                "identity_partition_policy": (
                    "seeded_component_geodesic_spatial_v003"
                ),
                "identity_seam_min_x": min(seams),
                "identity_seam_max_x": max(seams),
                "identity_order": ["robin", "speech"],
                "robin_blue_leak_pixel_count": robin_blue_pixels,
                "speech_green_leak_pixel_count": speech_green_pixels,
                "opaque_pixel_count": histogram[255],
                "transparent_pixel_count": histogram[0],
            }
    except OSError as exc:
        raise ValueError(f"{name} is not a readable PNG") from exc


def _zip_payloads(
    archive_path: Path,
    *,
    expected_sha256: str,
    expected_ordinals: range,
) -> dict[str, bytes]:
    if sha256_path(archive_path) != expected_sha256:
        raise ValueError(f"archive checksum mismatch: {archive_path.name}")
    with zipfile.ZipFile(archive_path) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        archive_names = [info.filename for info in infos]
        names = [Path(name).name for name in archive_names]
        if len(archive_names) != len(set(archive_names)):
            raise ValueError(f"{archive_path.name} contains duplicate paths")
        if len(names) != len(set(names)):
            raise ValueError(f"{archive_path.name} contains duplicate basenames")
        if any(
            Path(name).is_absolute() or ".." in Path(name).parts
            for name in archive_names
        ):
            raise ValueError(f"{archive_path.name} contains unsafe paths")
        parsed = [_parse_frame_name(name) for name in names]
        expected = set(expected_ordinals)
        actual = {value["ordinal"] for value in parsed}
        if actual != expected or len(actual) != len(names):
            raise ValueError(f"{archive_path.name} inventory mismatch")
        return {
            Path(info.filename).name: archive.read(info)
            for info in infos
        }


def ingest_alpha_archives(
    *,
    robin_speech_archive: Path,
    pair_archive: Path,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    replace: bool = False,
) -> dict[str, Any]:
    robin_speech_archive = robin_speech_archive.resolve()
    pair_archive = pair_archive.resolve()
    source_root = source_root.resolve()
    _project_path(source_root, "source root")
    robin_speech = _zip_payloads(
        robin_speech_archive,
        expected_sha256=ROBIN_SPEECH_BASE_ARCHIVE_SHA256,
        expected_ordinals=range(1, 161),
    )
    pairs = _zip_payloads(
        pair_archive,
        expected_sha256=PAIR_ARCHIVE_SHA256,
        expected_ordinals=range(151, 201),
    )
    by_ordinal: dict[int, tuple[str, bytes, str]] = {}
    duplicates = []
    for archive_role, payloads in (
        ("robin_speech_base", robin_speech),
        ("pair_tail", pairs),
    ):
        for name, payload in payloads.items():
            parsed = _parse_frame_name(name)
            ordinal = parsed["ordinal"]
            prior = by_ordinal.get(ordinal)
            if prior is not None:
                if prior[0] != name or prior[1] != payload:
                    raise ValueError(f"overlap differs between archives: {name}")
                duplicates.append(
                    {
                        "ordinal": ordinal,
                        "path": name,
                        "sha256": _sha256_bytes(payload),
                    }
                )
                continue
            by_ordinal[ordinal] = (name, payload, archive_role)
    if set(by_ordinal) != set(range(1, 201)):
        raise ValueError("canonical alpha inventory must contain ordinals 001-200")

    source_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{source_root.name}-",
            dir=source_root.parent,
        )
    )
    records = []
    try:
        alpha_root = staging / "alphas"
        alpha_root.mkdir(parents=True)
        for ordinal in range(1, 201):
            name, payload, archive_role = by_ordinal[ordinal]
            parsed = _parse_frame_name(name)
            image_audit = _validate_png(payload, name=name)
            destination = alpha_root / name
            destination.write_bytes(payload)
            records.append(
                {
                    **parsed,
                    "path": f"alphas/{name}",
                    "sha256": _sha256_bytes(payload),
                    "bytes": len(payload),
                    "archive_role": archive_role,
                    "image_audit": image_audit,
                }
            )
        manifest = {
            "schema_version": 1,
            "manifest_type": "robin_speech_shared_canvas_alpha_source",
            "asset_set_id": "robin-speech-shared-canvas-200-v003",
            "frame_count": 200,
            "canvas": {
                "width": CANVAS_SIZE[0],
                "height": CANVAS_SIZE[1],
                "identity_split_x": IDENTITY_SPLIT_X,
                "identity_partition_policy": (
                    "seeded_component_geodesic_spatial_v003"
                ),
                "coordinate_policy": "preserve_shared_source_canvas",
                "robin_side": "left",
                "speech_side": "right",
            },
            "archives": {
                "robin_speech_base_001_160": {
                    "filename": robin_speech_archive.name,
                    "sha256": ROBIN_SPEECH_BASE_ARCHIVE_SHA256,
                    "entry_count": 160,
                },
                "pair_tail_151_200": {
                    "filename": pair_archive.name,
                    "sha256": PAIR_ARCHIVE_SHA256,
                    "entry_count": 50,
                },
            },
            "deduplicated_overlap_count": len(duplicates),
            "deduplicated_overlaps": duplicates,
            "frames": records,
            "approval_state": "candidate_visual_review",
            "review_projection": True,
            "runtime_admitted": False,
        }
        _write_atomic(staging / SOURCE_MANIFEST_NAME, _json_bytes(manifest))
        if source_root.exists():
            if not replace:
                raise ValueError(f"source root already exists: {source_root}")
            shutil.rmtree(source_root)
        staging.replace(source_root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def _audit_source_root(source_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_root = source_root.resolve()
    _project_path(source_root, "source root")
    manifest = _read_json(source_root / SOURCE_MANIFEST_NAME)
    if manifest.get("schema_version") != 1:
        raise ValueError("source manifest schema mismatch")
    if manifest.get("manifest_type") != "robin_speech_shared_canvas_alpha_source":
        raise ValueError("source manifest type mismatch")
    if manifest.get("frame_count") != 200:
        raise ValueError("source manifest must declare 200 frames")
    if manifest.get("review_projection") is not True:
        raise ValueError("source manifest must remain review-only")
    if manifest.get("runtime_admitted") is not False:
        raise ValueError("source manifest cannot be runtime-admitted")
    if manifest.get("canvas") != {
        "width": CANVAS_SIZE[0],
        "height": CANVAS_SIZE[1],
        "identity_split_x": IDENTITY_SPLIT_X,
        "identity_partition_policy": "seeded_component_geodesic_spatial_v003",
        "coordinate_policy": "preserve_shared_source_canvas",
        "robin_side": "left",
        "speech_side": "right",
    }:
        raise ValueError("shared-canvas identity contract mismatch")
    if manifest.get("deduplicated_overlap_count") != 10:
        raise ValueError("source manifest must record ten duplicate overlaps")
    records = manifest.get("frames")
    if not isinstance(records, list) or len(records) != 200:
        raise ValueError("source manifest frame inventory mismatch")
    expected_paths = {SOURCE_MANIFEST_NAME}
    audited = []
    for expected_ordinal, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise ValueError("source frame record must be an object")
        if record.get("ordinal") != expected_ordinal:
            raise ValueError("source frame records must be ordinal-sorted")
        relative = Path(str(record.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("source alpha path must be contained")
        path = (source_root / relative).resolve()
        try:
            path.relative_to(source_root)
        except ValueError as exc:
            raise ValueError("source alpha path escaped source root") from exc
        if not path.is_file():
            raise ValueError(f"source alpha is missing: {relative}")
        expected_paths.add(relative.as_posix())
        digest = sha256_path(path)
        if digest != record.get("sha256"):
            raise ValueError(f"source alpha checksum mismatch: {relative}")
        parsed = _parse_frame_name(path.name)
        for key in ("ordinal", "family", "family_index", "slug", "pose_suffix"):
            if record.get(key) != parsed[key]:
                raise ValueError(f"source alpha metadata mismatch: {relative}")
        image_audit = _validate_png(path.read_bytes(), name=path.name)
        if image_audit != record.get("image_audit"):
            raise ValueError(f"source alpha image audit mismatch: {relative}")
        audited.append({**record, "resolved_path": path})
    actual_paths = {
        path.relative_to(source_root).as_posix()
        for path in source_root.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise ValueError("source root contains unmanifested files")
    return manifest, audited


def _identity_image(path: Path, identity: str) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    robin, speech, _ = _identity_layers(image)
    if identity == "robin":
        isolated = robin
    elif identity == "speech":
        isolated = speech
    else:
        raise ValueError(f"unknown identity: {identity}")
    if isolated.getchannel("A").getbbox() is None:
        raise ValueError(f"{identity} isolation erased {path.name}")
    return isolated


def _chunks(values: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _write_artifact(
    destination: Path,
    records: list[dict[str, Any]],
    *,
    identity: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    by_pose = {
        f"{identity}.{record['pose_suffix']}": record
        for record in records
    }
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        receipt = write_pose_artifact_from_loader(
            temporary,
            by_pose,
            load_pose=lambda pose_id: _identity_image(
                by_pose[pose_id]["resolved_path"],
                identity,
            ),
            profile=PROFILE,
            provenance=provenance,
        )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        **receipt,
        "path": destination.name,
        "sha256": sha256_path(destination),
        "bytes": destination.stat().st_size,
    }


def _build_identity_library(
    *,
    identity: str,
    records: list[dict[str, Any]],
    source_manifest_sha256: str,
    output_root: Path,
) -> dict[str, Any]:
    identity_config = IDENTITIES[identity]
    destination = output_root / identity
    destination.mkdir(parents=True, exist_ok=True)
    shards = []
    pose_catalog = []
    sequence_families: dict[str, list[str]] = defaultdict(list)
    for record in records:
        pose_id = f"{identity}.{record['pose_suffix']}"
        sequence_families[record["family"].lower()].append(pose_id)
        pose_catalog.append(
            {
                "pose_id": pose_id,
                "ordinal": record["ordinal"],
                "family": record["family"],
                "family_index": record["family_index"],
                "slug": record["slug"],
                "source_path": record["path"],
                "source_sha256": record["sha256"],
                "source_bbox": record["image_audit"][
                    f"{identity}_bbox"
                ],
                "identity_side": identity_config["side"],
            }
        )
    for family in ("ACT", "FLY", "INT"):
        family_records = [record for record in records if record["family"] == family]
        for chunk in _chunks(family_records, SHARD_SIZE):
            first = chunk[0]["family_index"]
            last = chunk[-1]["family_index"]
            shard_id = f"{identity}_{family.lower()}_{first:03d}_{last:03d}"
            path = destination / f"{shard_id}.wjpose"
            provenance = {
                "schema_version": 1,
                "character_id": identity,
                "display_name": identity_config["display_name"],
                "asset_set_id": f"{identity}-shared-canvas-200-v003",
                "source_asset_set_id": "robin-speech-shared-canvas-200-v003",
                "source_manifest_sha256": source_manifest_sha256,
                "identity_side": identity_config["side"],
                "identity_split_x": IDENTITY_SPLIT_X,
                "identity_partition_policy": (
                    "seeded_component_geodesic_spatial_v003"
                ),
                "coordinate_policy": "preserve_shared_source_canvas",
                "approval_state": "candidate_visual_review",
                "review_projection": True,
                "runtime_admitted": False,
            }
            receipt = _write_artifact(
                path,
                chunk,
                identity=identity,
                provenance=provenance,
            )
            shards.append(
                {
                    "shard_id": shard_id,
                    "path": path.name,
                    "sha256": receipt["sha256"],
                    "bytes": receipt["bytes"],
                    "pose_count": receipt["pose_count"],
                    "pose_ids": receipt["pose_ids"],
                    "source": "robin_speech_shared_canvas_alpha_source",
                    "approval_state": "candidate_visual_review",
                    "review_projection": True,
                    "runtime_admitted": False,
                }
            )
    all_pose_ids = [record["pose_id"] for record in pose_catalog]
    sequences = {
        identity_config["sequence"]: {
            "fps": 6,
            "loop": True,
            "pose_ids": all_pose_ids,
            "approval_state": "candidate_visual_review",
            "review_projection": True,
            "runtime_admitted": False,
        },
        f"{identity}-acting": {
            "fps": 6,
            "loop": True,
            "pose_ids": sequence_families["act"],
            "approval_state": "candidate_visual_review",
            "review_projection": True,
            "runtime_admitted": False,
        },
        f"{identity}-flight": {
            "fps": 8,
            "loop": True,
            "pose_ids": sequence_families["fly"],
            "approval_state": "candidate_visual_review",
            "review_projection": True,
            "runtime_admitted": False,
        },
        f"{identity}-interaction": {
            "fps": 6,
            "loop": True,
            "pose_ids": sequence_families["int"],
            "approval_state": "candidate_visual_review",
            "review_projection": True,
            "runtime_admitted": False,
        },
    }
    acceptance = {
        "schema_version": 1,
        "character_id": identity,
        "asset_set_id": f"{identity}-shared-canvas-200-v003",
        "review_projection": True,
        "runtime_admitted": False,
        "checks": {
            "source_integrity": {
                "passed": True,
                "frame_count": 200,
                "source_manifest_sha256": source_manifest_sha256,
            },
            "shared_canvas_identity": {
                "passed": True,
                "side": identity_config["side"],
                "split_x": IDENTITY_SPLIT_X,
                "partition_policy": "seeded_component_geodesic_spatial_v003",
                "canvas": list(CANVAS_SIZE),
            },
            "fixed_stage_projection": {
                "passed": True,
                "per_pose_normalization": False,
                "coordinate_policy": "preserve_shared_source_canvas",
            },
            "motion_anchor_contract": {
                "passed": False,
                "reason": (
                    "source alphas do not declare Character Director root, "
                    "foot-contact, airborne-trajectory, or transition anchors"
                ),
            },
            "speech_family_contract": {
                "passed": False,
                "reason": "source alphas do not include approved viseme families",
            },
            "rights_and_product_approval": {
                "passed": False,
                "reason": (
                    "archive hashes establish source identity but do not establish "
                    "redistribution rights or independent product approval"
                ),
            },
        },
        "runtime_admission_recommendation": "blocked",
        "blocking_reasons": [
            "motion and semantic contact anchors are not authored",
            "speech viseme families are not authored",
            "rights, product approval, and governance admission are not closed",
        ],
    }
    acceptance_path = destination / "candidate-acceptance-audit.json"
    _write_atomic(acceptance_path, _json_bytes(acceptance))
    index = {
        "schema_version": 1,
        "character_id": identity,
        "display_name": identity_config["display_name"],
        "asset_set_id": f"{identity}-shared-canvas-200-v003",
        "source_asset_set_id": "robin-speech-shared-canvas-200-v003",
        "source_manifest_sha256": source_manifest_sha256,
        "payload_encoding": "rgba8-zlib",
        "profile": PROFILE,
        "pose_count": 200,
        "approved_pose_count": 0,
        "candidate_pose_count": 200,
        "identity_side": identity_config["side"],
        "approval_state": "candidate_visual_review",
        "review_projection": True,
        "runtime_admitted": False,
        "candidate_acceptance_audit": {
            "path": acceptance_path.name,
            "sha256": sha256_path(acceptance_path),
            "runtime_admission_recommendation": "blocked",
        },
        "shards": shards,
        "sequences": sequences,
        "poses": pose_catalog,
        "review_guidance": {
            "acceptance_surface": "live_full_resolution_observer",
            "source_pair_frames_preserve_interaction_context": True,
            "runtime_admission_requires_separate_approval": True,
        },
    }
    index_path = destination / "library-index.json"
    _write_atomic(index_path, _json_bytes(index))
    library = HDPoseLibrary(index_path)
    if len(library.pose_ids) != 200 or library.canvas_size != CANVAS_SIZE:
        raise ValueError(f"{identity} library failed load verification")
    receipt = {
        "schema_version": 1,
        "character_id": identity,
        "asset_set_id": index["asset_set_id"],
        "source_manifest_sha256": source_manifest_sha256,
        "profile": PROFILE,
        "pose_count": 200,
        "identity_side": identity_config["side"],
        "review_projection": True,
        "runtime_admitted": False,
        "library_index": {
            "path": "library-index.json",
            "sha256": sha256_path(index_path),
        },
        "candidate_acceptance_audit": index["candidate_acceptance_audit"],
        "shards": shards,
    }
    _write_atomic(destination / "build-receipt.json", _json_bytes(receipt))
    return receipt


def build_review_libraries(
    *,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    output_root = output_root.resolve()
    _project_path(source_root, "source root")
    _project_path(output_root, "output root")
    manifest, records = _audit_source_root(source_root)
    manifest_path = source_root / SOURCE_MANIFEST_NAME
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    identity_receipts = {}
    for identity in IDENTITIES:
        identity_receipts[identity] = _build_identity_library(
            identity=identity,
            records=records,
            source_manifest_sha256=sha256_path(manifest_path),
            output_root=output_root,
        )
    receipt = {
        "schema_version": 1,
        "asset_set_id": manifest["asset_set_id"],
        "source_manifest": {
            "path": _project_path(manifest_path, "source manifest"),
            "sha256": sha256_path(manifest_path),
        },
        "canvas": manifest["canvas"],
        "frame_count": 200,
        "identities": identity_receipts,
        "review_projection": True,
        "runtime_admitted": False,
    }
    _write_atomic(output_root / "build-receipt.json", _json_bytes(receipt))
    return receipt


def _output_hashes(output_root: Path) -> dict[str, str]:
    return {
        path.relative_to(output_root).as_posix(): sha256_path(path)
        for path in sorted(output_root.rglob("*"))
        if path.is_file()
    }


def verify_deterministic_build(
    *,
    source_root: Path = DEFAULT_SOURCE_ROOT,
) -> dict[str, str]:
    source_root = source_root.resolve()
    with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
        base = Path(temporary)
        first = base / "first"
        second = base / "second"
        build_review_libraries(source_root=source_root, output_root=first)
        build_review_libraries(source_root=source_root, output_root=second)
        first_hashes = _output_hashes(first)
        second_hashes = _output_hashes(second)
        if first_hashes != second_hashes:
            raise ValueError("Robin/Speech builds are not deterministic")
        return first_hashes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest and compile shared-canvas Robin/Speech alphas."
    )
    parser.add_argument("--robin-speech-archive", type=Path)
    parser.add_argument("--pair-archive", type=Path)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--replace-source", action="store_true")
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()
    if args.ingest:
        if args.robin_speech_archive is None or args.pair_archive is None:
            parser.error("--ingest requires both archive paths")
        ingest_alpha_archives(
            robin_speech_archive=args.robin_speech_archive,
            pair_archive=args.pair_archive,
            source_root=args.source_root,
            replace=args.replace_source,
        )
    receipt = build_review_libraries(
        source_root=args.source_root,
        output_root=args.output_root,
    )
    if args.verify_determinism:
        receipt["deterministic_hashes"] = verify_deterministic_build(
            source_root=args.source_root,
        )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
