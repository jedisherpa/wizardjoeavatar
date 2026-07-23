#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.hd_pose_artifact import write_pose_artifact


DEFAULT_MANIFEST = ROOT / "assets" / "reference" / "hd_canonical" / "manifest.json"
DEFAULT_OUTPUT = ROOT / "assets" / "reference" / "hd_canonical" / "compiled"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _archive_member(prefix: str, relative: str) -> str:
    return f"{prefix.rstrip('/')}/{relative.lstrip('/')}"


def _validate_rgba(payload: bytes, filename: str, size: tuple[int, int]) -> Image.Image:
    image = Image.open(io.BytesIO(payload))
    image.load()
    if image.mode != "RGBA":
        raise ValueError(f"{filename} is not RGBA")
    if image.size != size:
        raise ValueError(f"{filename} has unexpected dimensions {image.size}")
    alpha = image.getchannel("A")
    alpha_min, alpha_max = alpha.getextrema()
    if alpha_min != 0 or alpha_max == 0:
        raise ValueError(f"{filename} does not contain a usable transparent silhouette")
    corners = ((0, 0), (size[0] - 1, 0), (0, size[1] - 1), (size[0] - 1, size[1] - 1))
    if any(alpha.getpixel(point) != 0 for point in corners):
        raise ValueError(f"{filename} has a nontransparent canvas corner")
    return image


def _pose_number(pose_id: str) -> int:
    return int(pose_id.split("_", 1)[0])


def _production_groups(
    poses: dict[str, Image.Image], categories: Iterable[dict[str, Any]]
) -> list[tuple[dict[str, Any], dict[str, Image.Image]]]:
    groups = []
    assigned: set[str] = set()
    for category in categories:
        start, end = (int(value) for value in category["range"])
        selected = {
            pose_id: image
            for pose_id, image in poses.items()
            if start <= _pose_number(pose_id) <= end
        }
        expected = end - start + 1
        if len(selected) != expected:
            raise ValueError(f"{category['id']} expected {expected} poses, found {len(selected)}")
        assigned.update(selected)
        groups.append((category, selected))
    if assigned != set(poses):
        raise ValueError("production shard ranges do not cover the complete pose set")
    return groups


def _load_production_poses(
    archive_path: Path, source: dict[str, Any], size: tuple[int, int]
) -> tuple[dict[str, Image.Image], dict[str, Any]]:
    if _sha256_file(archive_path) != source["archive_sha256"]:
        raise ValueError("production alpha archive checksum mismatch")
    prefix = source["archive_prefix"]
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(
            archive.read(_archive_member(prefix, source["manifest_path"]))
        )
        if manifest["pack_id"] != source["pack_id"] or manifest["status"] != source["status"]:
            raise ValueError("production alpha manifest authority mismatch")
        if len(manifest["assets"]) != int(source["frame_count"]):
            raise ValueError("production alpha manifest frame count mismatch")
        poses = {}
        for record in manifest["assets"]:
            if record["status"] != "approved_production_alpha" or record["qa_status"] != "pass":
                raise ValueError(f"production alpha is not approved: {record['filename']}")
            filename = record["filename"]
            payload = archive.read(
                _archive_member(prefix, f"{source['alpha_directory']}/{filename}")
            )
            if _sha256_bytes(payload) != record["output_sha256"]:
                raise ValueError(f"production alpha checksum mismatch: {filename}")
            pose_id = Path(filename).stem
            if pose_id in poses:
                raise ValueError(f"duplicate production pose id: {pose_id}")
            poses[pose_id] = _validate_rgba(payload, filename, size)
    return poses, manifest


def _load_flight_poses(
    archive_path: Path, source: dict[str, Any], size: tuple[int, int]
) -> tuple[dict[str, Image.Image], dict[str, Any], list[str]]:
    if _sha256_file(archive_path) != source["archive_sha256"]:
        raise ValueError("forward-flight archive checksum mismatch")
    prefix = source["archive_prefix"]
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(
            archive.read(_archive_member(prefix, source["manifest_path"]))
        )
        if manifest["pack_id"] != source["pack_id"] or manifest["status"] != source["status"]:
            raise ValueError("forward-flight manifest authority mismatch")
        assets = {record["filename"]: record for record in manifest["assets"]}
        order = []
        poses = {}
        for filename in manifest["playback"]["order"]:
            record = assets[filename]
            payload = archive.read(
                _archive_member(prefix, f"{source['alpha_directory']}/{filename}")
            )
            if _sha256_bytes(payload) != record["output_sha256"]:
                raise ValueError(f"forward-flight alpha checksum mismatch: {filename}")
            pose_id = Path(filename).stem.lower()
            poses[pose_id] = _validate_rgba(payload, filename, size)
            order.append(pose_id)
    if len(poses) != int(source["frame_count"]):
        raise ValueError("forward-flight frame count mismatch")
    return poses, manifest, order


def _artifact_record(path: Path, receipt: dict[str, Any], **metadata: Any) -> dict[str, Any]:
    return {
        **metadata,
        "path": path.name,
        "sha256": receipt["sha256"],
        "bytes": receipt["bytes"],
        "pose_count": receipt["pose_count"],
        "pose_ids": receipt["pose_ids"],
    }


def build(
    manifest_path: Path,
    output_dir: Path,
    production_archive: Path,
    flight_archive: Path,
) -> dict[str, Any]:
    authority = _read_json(manifest_path.resolve())
    profile = authority["master_profile"]
    size = (int(profile["canvas_width"]), int(profile["canvas_height"]))
    production_source = authority["sources"]["production_alpha_set"]
    flight_source = authority["sources"]["forward_camera_flight_cycle"]
    production, production_manifest = _load_production_poses(
        production_archive.resolve(), production_source, size
    )
    flight, flight_manifest, flight_order = _load_flight_poses(
        flight_archive.resolve(), flight_source, size
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    shards = []
    for category, poses in _production_groups(production, authority["categories"]):
        artifact_path = output_dir / f"production-{category['id']}.wjpose"
        receipt = write_pose_artifact(
            artifact_path,
            poses,
            profile=profile,
            provenance={
                "asset_set_id": authority["asset_set_id"],
                "source_pack_id": production_manifest["pack_id"],
                "source_archive_sha256": production_source["archive_sha256"],
                "approval_state": "approved_production_alpha",
                "runtime_admitted": False,
            },
        )
        shards.append(
            _artifact_record(
                artifact_path,
                receipt,
                shard_id=category["id"],
                source="production_alpha_set",
                approval_state="approved_production_alpha",
                runtime_admitted=False,
            )
        )

    flight_path = output_dir / "candidate-forward-camera-flight.wjpose"
    flight_receipt = write_pose_artifact(
        flight_path,
        flight,
        profile=profile,
        provenance={
            "asset_set_id": authority["asset_set_id"],
            "source_pack_id": flight_manifest["pack_id"],
            "source_archive_sha256": flight_source["archive_sha256"],
            "approval_state": "candidate_review",
            "runtime_admitted": False,
        },
    )
    shards.append(
        _artifact_record(
            flight_path,
            flight_receipt,
            shard_id="forward_camera_flight",
            source="forward_camera_flight_cycle",
            approval_state="candidate_review",
            runtime_admitted=False,
        )
    )

    index = {
        "schema_version": 1,
        "asset_set_id": authority["asset_set_id"],
        "profile": profile,
        "payload_encoding": "rgba8-zlib",
        "review_projection": True,
        "runtime_admitted": False,
        "pose_count": len(production) + len(flight),
        "approved_pose_count": len(production),
        "candidate_pose_count": len(flight),
        "shards": shards,
        "sequences": {
            "all_hd_frames": {
                "fps": 6,
                "loop": True,
                "pose_ids": sorted(production, key=_pose_number) + flight_order,
                "approval_state": "mixed_250_approved_10_candidate",
                "runtime_admitted": False,
                "runtime_note": "Review reel only; each authored pose is held as a discrete HD frame.",
            },
            "forward_camera_flight": {
                "fps": int(flight_manifest["playback"]["fps"]),
                "loop": True,
                "pose_ids": flight_order,
                "approval_state": "candidate_review",
                "runtime_admitted": False,
                "runtime_note": flight_manifest["runtime_note"],
            }
        },
    }
    index_path = output_dir / "library-index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema_version": 1,
        "asset_set_id": authority["asset_set_id"],
        "source_archives": {
            "production": production_source["archive_sha256"],
            "forward_camera_flight": flight_source["archive_sha256"],
        },
        "library_index": {
            "path": index_path.name,
            "sha256": _sha256_file(index_path),
        },
        "pose_count": index["pose_count"],
        "approved_pose_count": index["approved_pose_count"],
        "candidate_pose_count": index["candidate_pose_count"],
        "shards": shards,
    }
    (output_dir / "build-receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    canonical_output = (manifest_path.resolve().parent / "compiled").resolve()
    if output_dir.resolve() == canonical_output:
        authority["compiled_library_index"] = {
            "path": "compiled/library-index.json",
            "sha256": receipt["library_index"]["sha256"],
            "pose_count": index["pose_count"],
            "approved_pose_count": index["approved_pose_count"],
            "candidate_pose_count": index["candidate_pose_count"],
            "runtime_admitted": False,
        }
        manifest_path.write_text(
            json.dumps(authority, indent=2) + "\n", encoding="utf-8"
        )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile approved Wizard Joe HD alphas into colored-pixel artifacts"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--production-archive", type=Path, required=True)
    parser.add_argument("--flight-archive", type=Path, required=True)
    args = parser.parse_args()
    receipt = build(
        args.manifest,
        args.output,
        args.production_archive,
        args.flight_archive,
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
