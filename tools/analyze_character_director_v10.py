#!/usr/bin/env python3
"""Evaluate the machine-verifiable Character Director V10 framing proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_character_director_visual_review import validate_manifest
from wizard_avatar.animation_trace import AnimationTruthTraceV1


REPORT_SCHEMA = "character_director_v10_machine_acceptance_v1"
PROGRAM_ID = "v10-responsive-framing"
EXPECTED_SCENARIOS = (
    "v10-center",
    "v10-near",
    "v10-far",
    "v10-left-edge",
    "v10-right-edge",
)
EXPECTED_FRAME_COUNTS = {
    "v10-center": 48,
    "v10-near": 96,
    "v10-far": 144,
    "v10-left-edge": 120,
    "v10-right-edge": 120,
}
EXPECTED_TARGETS = {
    "v10-center": (0.0, 5.0),
    "v10-near": (0.0, 1.5),
    "v10-far": (0.0, 10.0),
    "v10-left-edge": (-3.2, 5.0),
    "v10-right-edge": (3.2, 5.0),
}
EXPECTED_TOTAL_FRAMES = sum(EXPECTED_FRAME_COUNTS.values())
TERMINAL_HOLD_FRAMES = 24
EDGE_SAFE_BOUNDARY_MARGIN_CELLS = 30
REQUIRED_PROFILES = {
    "desktop-dpr1": (1280, 720, 1.0, False),
    "desktop-dpr2": (1280, 720, 2.0, False),
    "mobile-390x844-dpr3": (390, 844, 3.0, True),
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _check(report: Dict[str, Any], name: str, passed: bool, detail: object) -> None:
    report["checks"].append(
        {"name": name, "passed": bool(passed), "detail": detail}
    )


def _finite(value: object) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _root(trace: Mapping[str, Any]) -> Optional[Tuple[float, float]]:
    x = _finite(trace.get("world_root_x"))
    z = _finite(trace.get("world_root_z"))
    return None if x is None or z is None else (x, z)


def _span(trace: Mapping[str, Any]) -> Optional[Tuple[int, int, int, int]]:
    value = trace.get("silhouette_raster_span")
    if not isinstance(value, Mapping):
        return None
    coordinates = (
        value.get("min_x"),
        value.get("max_x"),
        value.get("min_y"),
        value.get("max_y"),
    )
    if any(type(item) is not int for item in coordinates):
        return None
    return tuple(int(item) for item in coordinates)  # type: ignore[return-value]


def _rect(value: object) -> Optional[Tuple[float, float, float, float]]:
    if not isinstance(value, Mapping):
        return None
    coordinates = (
        _finite(value.get("x")),
        _finite(value.get("y")),
        _finite(value.get("width")),
        _finite(value.get("height")),
    )
    if any(item is None for item in coordinates):
        return None
    x, y, width, height = (float(item) for item in coordinates)
    if width < 0 or height < 0:
        return None
    return x, y, width, height


def _overlaps(
    left: Tuple[float, float, float, float],
    right: Tuple[float, float, float, float],
) -> bool:
    return (
        left[0] < right[0] + right[2]
        and left[0] + left[2] > right[0]
        and left[1] < right[1] + right[3]
        and left[1] + left[3] > right[1]
    )


def _css_pixels(value: object) -> Optional[float]:
    if not isinstance(value, str) or not value.endswith("px"):
        return None
    try:
        result = float(value[:-2])
    except ValueError:
        return None
    return result if math.isfinite(result) and result > 0 else None


def _expected_browser_start(
    traces: Sequence[Mapping[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not traces:
        return None
    first = min(traces, key=lambda item: item.get("frame_index", math.inf))
    channels = first.get("presentation_channels")
    if not isinstance(channels, Mapping):
        return None
    result = {
        "frame_index": first.get("frame_index"),
        "frame_fnv1a32": first.get("frame_fnv1a32"),
        "world_root_x": first.get("world_root_x"),
        "world_root_z": first.get("world_root_z"),
        "presented_facing": first.get("presented_facing"),
        "action": channels.get("action"),
        "expression": channels.get("expression"),
        "mouth": channels.get("rendered_mouth_shape"),
    }
    if (
        type(result["frame_index"]) is not int
        or not isinstance(result["frame_fnv1a32"], str)
        or not re.fullmatch(r"fnv1a32:[0-9a-f]{8}", result["frame_fnv1a32"])
        or any(
            _finite(result[field]) is None
            for field in ("world_root_x", "world_root_z")
        )
        or any(
            not isinstance(result[field], str)
            for field in ("presented_facing", "action", "expression", "mouth")
        )
    ):
        return None
    return result


def _browser_start_identity_report(
    metrics: Mapping[str, Any],
    traces: Sequence[Mapping[str, Any]],
    dpr: float,
) -> Dict[str, Any]:
    expected = _expected_browser_start(traces)
    declared = metrics.get("expected_start_identity")
    snapshots = {
        "synchronized_pre_roll": metrics.get("synchronized_pre_roll"),
        "first_encoded_identity": metrics.get("first_encoded_identity"),
    }
    failures: List[str] = []
    if expected is None or declared != expected:
        failures.append("declared_start_identity_mismatch")
    for label, snapshot in snapshots.items():
        if not isinstance(snapshot, Mapping) or expected is None:
            failures.append("{}:missing".format(label))
            continue
        client = snapshot.get("client_metrics")
        state_response = snapshot.get("state_response")
        diagnostics_text = snapshot.get("diagnostics_text")
        canvas = client.get("canvas") if isinstance(client, Mapping) else None
        state = (
            state_response.get("state")
            if isinstance(state_response, Mapping)
            else None
        )
        diagnostics = (
            state_response.get("diagnostics")
            if isinstance(state_response, Mapping)
            else None
        )
        position = state.get("world_position") if isinstance(state, Mapping) else None
        if not isinstance(client, Mapping):
            failures.append("{}:missing_client_metrics".format(label))
            continue
        if client.get("rawQueueDepth") != 0:
            failures.append("{}:raw_queue_not_drained".format(label))
        decoded_depth = client.get("decodedQueueDepth")
        if type(decoded_depth) is not int or not 0 <= decoded_depth <= 2:
            failures.append("{}:decoded_queue_out_of_bounds".format(label))
        if (
            not isinstance(canvas, Mapping)
            or canvas.get("lastPresentedLogicalHash")
            != expected["frame_fnv1a32"]
            or _finite(canvas.get("dpr")) != dpr
        ):
            failures.append("{}:canvas_identity_mismatch".format(label))
        if not isinstance(position, Mapping):
            failures.append("{}:missing_runtime_position".format(label))
        else:
            for coordinate, expected_field in (
                ("x", "world_root_x"),
                ("z", "world_root_z"),
            ):
                observed = _finite(position.get(coordinate))
                target = _finite(expected[expected_field])
                if (
                    observed is None
                    or target is None
                    or abs(observed - target) > 0.01
                ):
                    failures.append(
                        "{}:runtime_{}_mismatch".format(label, coordinate)
                    )
        if (
            not isinstance(state, Mapping)
            or state.get("facing") != expected["presented_facing"]
            or state.get("action") != expected["action"]
            or state.get("expression") != expected["expression"]
        ):
            failures.append("{}:runtime_state_mismatch".format(label))
        if (
            not isinstance(diagnostics, Mapping)
            or diagnostics.get("presented_facing")
            != expected["presented_facing"]
        ):
            failures.append("{}:presented_facing_mismatch".format(label))
        required_text = (
            "x {:.2f}  z {:.2f}".format(
                float(expected["world_root_x"]),
                float(expected["world_root_z"]),
            ),
            "facing {}".format(expected["presented_facing"]),
            "action {}".format(expected["action"]),
            "dpr {:.2f}".format(dpr),
        )
        if not isinstance(diagnostics_text, str) or any(
            item not in diagnostics_text for item in required_text
        ):
            failures.append("{}:diagnostics_text_mismatch".format(label))
    first = snapshots["first_encoded_identity"]
    if (
        not isinstance(first, Mapping)
        or type(first.get("screencast_sequence")) is not int
        or first.get("screencast_sequence") <= 0
    ):
        failures.append("first_encoded_identity:invalid_screencast_sequence")
    return {
        "passed": not failures,
        "expected": expected,
        "declared": declared,
        "failures": failures,
    }


def _profile_report(
    metrics: Mapping[str, Any],
    manifest: Mapping[str, Any],
    manifest_sha256: str,
    traces: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    profile = metrics.get("viewport_profile")
    name = profile.get("name") if isinstance(profile, Mapping) else None
    expected = REQUIRED_PROFILES.get(str(name))
    result: Dict[str, Any] = {
        "name": name,
        "passed": False,
        "checks": {},
    }
    if expected is None or not isinstance(profile, Mapping):
        result["checks"]["known_profile"] = False
        return result

    width, height, dpr, mobile = expected
    layout = metrics.get("layout")
    viewport = layout.get("viewport") if isinstance(layout, Mapping) else None
    canvas = layout.get("canvas") if isinstance(layout, Mapping) else None
    canvas_rect = _rect(canvas)
    toolbar_rect = _rect(layout.get("toolbar")) if isinstance(layout, Mapping) else None
    status_rect = _rect(layout.get("mediaStatus")) if isinstance(layout, Mapping) else None
    client = metrics.get("final_client_metrics")
    canvas_metrics = client.get("canvas") if isinstance(client, Mapping) else None
    cols = int(manifest.get("init", {}).get("cols", 0) or 0)
    rows = int(manifest.get("init", {}).get("rows", 0) or 0)

    observed_viewport = (
        _finite(viewport.get("width")) if isinstance(viewport, Mapping) else None,
        _finite(viewport.get("height")) if isinstance(viewport, Mapping) else None,
        _finite(viewport.get("dpr")) if isinstance(viewport, Mapping) else None,
    )
    result["checks"]["exact_viewport"] = (
        profile.get("width") == width
        and profile.get("height") == height
        and _finite(profile.get("device_scale_factor")) == dpr
        and profile.get("mobile") is mobile
        and observed_viewport == (float(width), float(height), dpr)
    )
    candidate = manifest.get("provenance", {}).get("head")
    result["checks"]["capture_binding"] = (
        metrics.get("schema") == "character_director_browser_layout_v1"
        and metrics.get("schema_version") == 1
        and metrics.get("run_id") == manifest.get("source_epoch")
        and metrics.get("candidate_commit") == candidate
        and metrics.get("capture_manifest_sha256") == manifest_sha256
        and metrics.get("frame_count") == EXPECTED_TOTAL_FRAMES
        and metrics.get("expected_frame_count") == EXPECTED_TOTAL_FRAMES
    )
    result["checks"]["runtime_integrity"] = (
        isinstance(client, Mapping)
        and client.get("decodeErrorCount") == 0
        and client.get("droppedFrames") == 0
        and client.get("rawMessagesDropped") == 0
        and client.get("resyncCount") == 0
        and client.get("waitingForKeyframe") is False
        and not metrics.get("page_errors")
        and not metrics.get("console_events")
    )
    start_identity = _browser_start_identity_report(metrics, traces, dpr)
    result["checks"]["synchronized_first_encoded_frame"] = start_identity["passed"]
    result["start_identity"] = start_identity

    canvas_inside = False
    letterbox = False
    aspect = False
    if canvas_rect is not None:
        x, y, canvas_width, canvas_height = canvas_rect
        canvas_inside = (
            x >= -0.01
            and y >= -0.01
            and x + canvas_width <= width + 0.01
            and y + canvas_height <= height + 0.01
        )
        aspect = (
            canvas_height > 0
            and cols > 0
            and rows > 0
            and abs(canvas_width / canvas_height - cols / rows) <= 1e-6
        )
        letterbox = (
            abs(x - (width - x - canvas_width)) <= 1.0
            and abs(y - (height - y - canvas_height)) <= 1.0
        )
    result["checks"]["canvas_containment_aspect_letterbox"] = (
        canvas_inside and aspect and letterbox
    )

    crisp = False
    if isinstance(canvas_metrics, Mapping) and canvas_rect is not None:
        device_cell = canvas_metrics.get("deviceCell")
        backing_width = canvas_metrics.get("backingWidth")
        backing_height = canvas_metrics.get("backingHeight")
        css_width = _css_pixels(canvas_metrics.get("cssWidth"))
        css_height = _css_pixels(canvas_metrics.get("cssHeight"))
        crisp = (
            type(device_cell) is int
            and device_cell >= 1
            and backing_width == cols * device_cell
            and backing_height == rows * device_cell
            and _finite(canvas_metrics.get("dpr")) == dpr
            and css_width is not None
            and css_height is not None
            and abs(css_width - canvas_rect[2]) <= 0.01
            and abs(css_height - canvas_rect[3]) <= 0.01
            and abs(float(backing_width) / css_width - dpr) <= 1e-6
            and abs(float(backing_height) / css_height - dpr) <= 1e-6
            and isinstance(canvas, Mapping)
            and canvas.get("backingWidth") == backing_width
            and canvas.get("backingHeight") == backing_height
            and canvas.get("imageSmoothingEnabled") is False
            and canvas.get("imageRendering") in {"pixelated", "crisp-edges"}
            and canvas_metrics.get("verticalUiReserveCssPx") == 144
            and canvas_metrics.get("safeViewportHeight") == height - 144
        )
    result["checks"]["integer_physical_pixel_projection"] = crisp

    overlap_failures: List[Dict[str, Any]] = []
    if (
        canvas_rect is None
        or toolbar_rect is None
        or status_rect is None
        or cols <= 0
        or rows <= 0
    ):
        overlap_failures.append({"reason": "missing_layout_geometry"})
    else:
        for trace in traces:
            span = _span(trace)
            if span is None:
                overlap_failures.append(
                    {
                        "frame_index": trace.get("frame_index"),
                        "reason": "missing_silhouette",
                    }
                )
                continue
            min_x, max_x, min_y, max_y = span
            projected = (
                canvas_rect[0] + min_x * canvas_rect[2] / cols,
                canvas_rect[1] + min_y * canvas_rect[3] / rows,
                (max_x - min_x + 1) * canvas_rect[2] / cols,
                (max_y - min_y + 1) * canvas_rect[3] / rows,
            )
            if _overlaps(projected, toolbar_rect) or _overlaps(projected, status_rect):
                overlap_failures.append(
                    {
                        "frame_index": trace.get("frame_index"),
                        "projected_silhouette": projected,
                    }
                )
    result["checks"]["avatar_avoids_controls"] = not overlap_failures
    result["overlap_failure_count"] = len(overlap_failures)
    result["overlap_failures"] = overlap_failures[:12]
    result["passed"] = bool(result["checks"]) and all(result["checks"].values())
    return result


def analyze_v10(
    manifest: Mapping[str, Any],
    trace_records: Sequence[Mapping[str, Any]],
    browser_metrics: Sequence[Mapping[str, Any]],
    capture_manifest_sha256: str,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "acceptance_scenario": "V10",
        "passed": False,
        "checks": [],
        "metrics": {},
        "analyzer": {
            "path": "tools/analyze_character_director_v10.py",
            "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "review_boundary": (
            "Machine checks prove transport, crop margins, target positions, "
            "browser sizing, physical-pixel projection, and control overlap. "
            "Two human reviewers must still judge scale, grounding, portrait "
            "balance, and readability at normal and quarter speed."
        ),
    }
    program = manifest.get("scenario_program")
    _check(
        report,
        "scenario_program_identity",
        isinstance(program, Mapping)
        and program.get("schema") == "character_director_scenario_program_v2"
        and program.get("schema_version") == 2
        and program.get("program_id") == PROGRAM_ID
        and program.get("acceptance_scenario") == "V10"
        and program.get("scenario_count") == len(EXPECTED_SCENARIOS)
        and program.get("maximum_capture_frame_count") == EXPECTED_TOTAL_FRAMES,
        program,
    )
    scenario_names = tuple(
        item.get("name")
        for item in manifest.get("scenarios", ())
        if isinstance(item, Mapping)
    )
    _check(
        report,
        "scenario_order",
        scenario_names == EXPECTED_SCENARIOS,
        list(scenario_names),
    )

    frames = [
        item for item in manifest.get("frames", ()) if isinstance(item, Mapping)
    ]
    trace_by_index = {
        item.get("frame_index"): item
        for item in trace_records
        if type(item.get("frame_index")) is int
    }
    indexes = [item.get("frame_index") for item in frames]
    owned = [item for item in frames if item.get("capture_owned") is True]
    counts = {
        name: sum(item.get("scenario") == name for item in owned)
        for name in EXPECTED_SCENARIOS
    }
    owned_traces = {
        name: [
            trace_by_index[item["frame_index"]]
            for item in owned
            if item.get("scenario") == name and item.get("frame_index") in trace_by_index
        ]
        for name in EXPECTED_SCENARIOS
    }
    contiguous = bool(indexes) and all(
        type(left) is int and type(right) is int and right == left + 1
        for left, right in zip(indexes, indexes[1:])
    )
    _check(
        report,
        "complete_contiguous_capture",
        len(owned) == EXPECTED_TOTAL_FRAMES
        and counts == EXPECTED_FRAME_COUNTS
        and len(trace_records) == len(frames)
        and len(trace_by_index) == len(frames)
        and contiguous
        and all(
            len(owned_traces[name]) == EXPECTED_FRAME_COUNTS[name]
            for name in EXPECTED_SCENARIOS
        ),
        {
            "manifest_frame_count": len(frames),
            "trace_count": len(trace_records),
            "owned_frame_count": len(owned),
            "scenario_frame_counts": counts,
            "transport_contiguous": contiguous,
        },
    )

    cols = int(manifest.get("init", {}).get("cols", 0) or 0)
    rows = int(manifest.get("init", {}).get("rows", 0) or 0)
    clipped = []
    for trace in trace_records:
        span = _span(trace)
        if (
            span is None
            or span[0] < 4
            or span[1] > cols - 1 - 4
            or span[2] < 4
            or span[3] > rows - 1 - 6
        ):
            clipped.append(
                {"frame_index": trace.get("frame_index"), "span": span}
            )
    _check(
        report,
        "canonical_silhouette_margins",
        cols == 240 and rows == 135 and bool(trace_records) and not clipped,
        {
            "stage": [cols, rows],
            "required_margins": {"top": 4, "side": 4, "bottom": 6},
            "failure_count": len(clipped),
            "failures": clipped[:12],
        },
    )

    target_details: Dict[str, Any] = {}
    targets_pass = True
    scales: Dict[str, float] = {}
    for name in EXPECTED_SCENARIOS:
        terminal = owned_traces[name][-TERMINAL_HOLD_FRAMES:]
        roots = [_root(item) for item in terminal]
        valid_roots = [item for item in roots if item is not None]
        target = EXPECTED_TARGETS[name]
        errors = [
            math.dist(root, target)
            for root in valid_roots
        ]
        scale_values = [
            value
            for item in terminal
            for value in [_finite(item.get("render_scale"))]
            if value is not None
        ]
        scale = (
            sum(scale_values) / len(scale_values)
            if scale_values
            else math.nan
        )
        scales[name] = scale
        passed = (
            len(terminal) == TERMINAL_HOLD_FRAMES
            and len(valid_roots) == TERMINAL_HOLD_FRAMES
            and bool(errors)
            and max(errors) <= 0.08
            and max(math.dist(left, right) for left in valid_roots for right in valid_roots)
            <= 0.04
            and math.isfinite(scale)
        )
        targets_pass = targets_pass and passed
        target_details[name] = {
            "passed": passed,
            "target": target,
            "maximum_error": max(errors) if errors else None,
            "terminal_root_span": (
                max(math.dist(left, right) for left in valid_roots for right in valid_roots)
                if valid_roots
                else None
            ),
            "mean_render_scale": scale,
        }
    _check(report, "terminal_target_holds", targets_pass, target_details)
    _check(
        report,
        "near_center_far_scale_order",
        scales.get("v10-near", math.nan)
        > scales.get("v10-center", math.nan)
        > scales.get("v10-far", math.nan)
        > 0,
        scales,
    )

    left_spans = [
        _span(item) for item in owned_traces["v10-left-edge"][-TERMINAL_HOLD_FRAMES:]
    ]
    right_spans = [
        _span(item) for item in owned_traces["v10-right-edge"][-TERMINAL_HOLD_FRAMES:]
    ]
    edge_pass = (
        all(item is not None for item in left_spans + right_spans)
        and max(item[0] for item in left_spans if item is not None)
        <= EDGE_SAFE_BOUNDARY_MARGIN_CELLS
        and min(item[1] for item in right_spans if item is not None)
        >= cols - 1 - EDGE_SAFE_BOUNDARY_MARGIN_CELLS
    )
    _check(
        report,
        "edge_pass_reaches_safe_frame_boundary",
        edge_pass,
        {
            "left_terminal_min_x": sorted(
                {item[0] for item in left_spans if item is not None}
            ),
            "right_terminal_max_x": sorted(
                {item[1] for item in right_spans if item is not None}
            ),
            "maximum_safe_boundary_margin_cells": (
                EDGE_SAFE_BOUNDARY_MARGIN_CELLS
            ),
        },
    )
    contact = manifest.get("contact_verification")
    _check(
        report,
        "grounding_contact_verification",
        isinstance(contact, Mapping) and contact.get("passed") is True,
        contact,
    )

    profile_reports = [
        _profile_report(
            metrics,
            manifest,
            capture_manifest_sha256,
            trace_records,
        )
        for metrics in browser_metrics
    ]
    profile_names = [item.get("name") for item in profile_reports]
    _check(
        report,
        "responsive_browser_profile_matrix",
        len(profile_reports) == len(REQUIRED_PROFILES)
        and set(profile_names) == set(REQUIRED_PROFILES)
        and len(set(profile_names)) == len(profile_names)
        and all(item.get("passed") is True for item in profile_reports),
        profile_reports,
    )

    report["metrics"] = {
        "owned_frame_count": len(owned),
        "scenario_frame_counts": counts,
        "terminal_scales": scales,
        "browser_profiles": profile_reports,
    }
    report["passed"] = bool(report["checks"]) and all(
        item["passed"] for item in report["checks"]
    )
    return report


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_and_analyze(
    manifest_path: Path,
    browser_metric_paths: Sequence[Path],
) -> Dict[str, Any]:
    evidence_dir = manifest_path.resolve().parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest, evidence_dir)
    trace_path = evidence_dir / manifest["animation_truth_trace"]["path"]
    traces: List[Mapping[str, Any]] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if line:
            traces.append(
                AnimationTruthTraceV1.from_mapping(json.loads(line)).to_mapping()
            )
    metrics = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in browser_metric_paths
    ]
    manifest_sha256 = _sha256_file(manifest_path)
    if not SHA256_RE.fullmatch(manifest_sha256):
        raise ValueError("invalid capture manifest digest")
    return analyze_v10(manifest, traces, metrics, manifest_sha256)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze Character Director V10 responsive framing evidence."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--browser-metrics",
        type=Path,
        action="append",
        required=True,
        help="Repeat exactly three times for desktop DPR1/DPR2 and mobile DPR3.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if len(args.browser_metrics) != len(REQUIRED_PROFILES):
        parser.error("--browser-metrics must be supplied exactly three times")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    report = load_and_analyze(args.manifest, args.browser_metrics)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
