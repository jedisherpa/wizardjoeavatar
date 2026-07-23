from __future__ import annotations

from typing import Any, Mapping


def hd_source_import_policy(manifest: Mapping[str, Any]) -> dict[str, Any]:
    raw = manifest.get("hd_source_import_policy")
    if not isinstance(raw, dict):
        raise ValueError("hd_source_import_policy is required by HD-authored poses")
    required = {
        "purpose",
        "required_approval_state",
        "native_runtime_admission_required",
        "derived_runtime_admission_authority",
    }
    if set(raw) != required:
        raise ValueError(
            "hd_source_import_policy must contain exactly: "
            + ", ".join(sorted(required))
        )
    if raw["purpose"] != "offline_canonical_graph_derivation":
        raise ValueError("HD source import purpose is unsupported")
    if raw["required_approval_state"] != "approved_production_alpha":
        raise ValueError("HD source import requires approved production alpha art")
    if not isinstance(raw["native_runtime_admission_required"], bool):
        raise ValueError("native_runtime_admission_required must be a boolean")
    if (
        raw["derived_runtime_admission_authority"]
        != "wizard_avatar/definitions/reference_avatar_animation_graph_v2.json"
    ):
        raise ValueError("HD derived-runtime admission authority is unsupported")
    return dict(raw)


def expand_derived_bridge_series(
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Expand compact bridge declarations into canonical manifest poses."""

    raw_series = manifest.get("derived_bridge_series", [])
    if not isinstance(raw_series, list):
        raise ValueError("derived_bridge_series must be a list")
    raw_poses = manifest.get("poses", [])
    if not isinstance(raw_poses, list) or not all(
        isinstance(pose, dict) for pose in raw_poses
    ):
        raise ValueError("manifest poses must be a list of objects")
    poses = [dict(pose) for pose in raw_poses]
    known_ids = {str(pose.get("id")) for pose in poses}
    for series_index, series in enumerate(raw_series):
        path = f"derived_bridge_series[{series_index}]"
        if not isinstance(series, dict):
            raise ValueError(f"{path} must be an object")
        required = {
            "id_prefix",
            "from_pose_id",
            "to_pose_id",
            "progress_milli",
            "lock_anchor",
            "facing",
            "locomotion",
            "actions",
            "tags",
        }
        missing = sorted(required - set(series))
        if missing:
            raise ValueError(f"{path} is missing: {', '.join(missing)}")
        progress_values = series["progress_milli"]
        if (
            not isinstance(progress_values, list)
            or not progress_values
            or any(
                isinstance(progress, bool)
                or not isinstance(progress, int)
                or progress <= 0
                or progress >= 1000
                for progress in progress_values
            )
        ):
            raise ValueError(
                f"{path}.progress_milli must contain integers in 1..999"
            )
        if progress_values != sorted(set(progress_values)):
            raise ValueError(f"{path}.progress_milli must be unique and increasing")
        for endpoint in ("from_pose_id", "to_pose_id"):
            if series[endpoint] not in known_ids:
                raise ValueError(f"{path}.{endpoint} references an unknown pose")
        prealign_lock_anchor = series.get("prealign_lock_anchor", True)
        if not isinstance(prealign_lock_anchor, bool):
            raise ValueError(f"{path}.prealign_lock_anchor must be a boolean")
        prefix = series["id_prefix"]
        if not isinstance(prefix, str) or not prefix:
            raise ValueError(f"{path}.id_prefix must be a nonempty string")
        for progress in progress_values:
            pose_id = f"{prefix}_{progress}"
            if pose_id in known_ids:
                raise ValueError(f"{path} creates duplicate pose id {pose_id!r}")
            method = series.get("method", "topology_splat")
            poses.append(
                {
                    "id": pose_id,
                    "source": (
                        "derived_landmark_warp:"
                        f"{series['from_pose_id']}+{series['to_pose_id']}"
                        f"@{progress}/1000:lock={series['lock_anchor']}:"
                        f"method={method}"
                    ),
                    "description": (
                        f"{series.get('description', prefix)} at "
                        f"{progress / 10:g} percent"
                    ),
                    "derived_landmark_warp": {
                        "from_pose_id": series["from_pose_id"],
                        "to_pose_id": series["to_pose_id"],
                        "progress_milli": progress,
                        "lock_anchor": series["lock_anchor"],
                        "prealign_lock_anchor": prealign_lock_anchor,
                        "method": method,
                        **(
                            {"staff_transition": series["staff_transition"]}
                            if "staff_transition" in series
                            else {}
                        ),
                    },
                    "facing": series["facing"],
                    "locomotion": series["locomotion"],
                    "actions": list(series["actions"]),
                    "phase": series.get("phase"),
                    "tags": list(series["tags"]),
                }
            )
            known_ids.add(pose_id)
    return {**manifest, "poses": poses}
