#!/usr/bin/env python3
"""Evaluate the machine-verifiable portion of Character Director scenario V2."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_character_director_visual_review import sha256_file, validate_manifest
from wizard_avatar.animation_trace import AnimationTruthTraceV1


REPORT_SCHEMA = "character_director_v2_machine_acceptance_v1"
EXPECTED_SCENARIOS = (
    "speech-steady-center",
    "speech-gaze-left",
    "speech-return-center-one",
    "speech-gaze-right",
    "speech-return-center-two",
)
EXPECTED_GAZE = {
    "speech-steady-center": 0,
    "speech-gaze-left": -1,
    "speech-return-center-one": 0,
    "speech-gaze-right": 1,
    "speech-return-center-two": 0,
}
EXPECTED_FRAME_COUNTS = {
    "speech-steady-center": 84,
    "speech-gaze-left": 72,
    "speech-return-center-one": 96,
    "speech-gaze-right": 72,
    "speech-return-center-two": 156,
}
OPEN_MOUTHS = {"open_small", "open_medium", "open_wide", "rounded"}
MINIMUM_MOUTH_SWITCHES = 20
MAXIMUM_MOUTH_SWITCHES_PER_SECOND = 8.0
MOUTH_APERTURE = {
    "closed": 0,
    "open_small": 1,
    "rounded": 1,
    "smile": 1,
    "frown": 1,
    "open_medium": 2,
    "open_wide": 3,
}


def _check(report: Dict[str, Any], name: str, passed: bool, detail: object) -> None:
    report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})


def _closed_ranges(records: Sequence[Mapping[str, Any]]) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
    start: Optional[int] = None
    for index, record in enumerate(records):
        closed = record["presentation_channels"]["blink_closed"]
        if closed and start is None:
            start = index
        elif not closed and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(records)))
    return runs


def _percentile_nearest_rank(values: Sequence[int], percentile: float) -> Optional[int]:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _time_regressions(values: Sequence[int]) -> List[int]:
    return [
        earlier - later
        for earlier, later in zip(values, values[1:])
        if later < earlier
    ]


def _mouth_runs(channels: Sequence[Mapping[str, Any]]) -> List[Tuple[str, int]]:
    runs: List[Tuple[str, int]] = []
    for item in channels:
        shape = str(item.get("rendered_mouth_shape"))
        if runs and runs[-1][0] == shape:
            previous_shape, previous_length = runs[-1]
            runs[-1] = (previous_shape, previous_length + 1)
        else:
            runs.append((shape, 1))
    return runs


def _owned_channel_segments(
    paired: Sequence[Tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> List[List[Mapping[str, Any]]]:
    segments: List[List[Mapping[str, Any]]] = []
    current: List[Mapping[str, Any]] = []
    previous_index: Optional[int] = None
    for frame, trace in paired:
        frame_index = frame.get("frame_index")
        owned = frame.get("capture_owned") is True
        contiguous = (
            type(frame_index) is int
            and previous_index is not None
            and frame_index == previous_index + 1
        )
        if not owned:
            if current:
                segments.append(current)
                current = []
            previous_index = None
            continue
        if current and not contiguous:
            segments.append(current)
            current = []
        current.append(trace["presentation_channels"])
        previous_index = frame_index if type(frame_index) is int else None
    if current:
        segments.append(current)
    return segments


def analyze_v2(
    manifest: Mapping[str, Any],
    trace_records: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any],
    manifest_sha256: str,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "acceptance_scenario": "V2",
        "passed": False,
        "checks": [],
        "metrics": {},
        "review_boundary": (
            "Machine checks do not replace normal-speed, quarter-speed, or "
            "two-independent-reviewer acting and AV judgment."
        ),
    }
    program = manifest.get("scenario_program")
    _check(
        report,
        "scenario_program_identity",
        isinstance(program, Mapping)
        and program.get("program_id") == "v2-governed-speech"
        and program.get("acceptance_scenario") == "V2"
        and program.get("total_duration_seconds") == 20.0,
        program,
    )
    scenario_names = tuple(item.get("name") for item in manifest.get("scenarios", ()))
    _check(
        report,
        "scenario_order",
        scenario_names == EXPECTED_SCENARIOS,
        list(scenario_names),
    )
    atomic_capture = receipt.get("atomic_capture", {})
    runtime_start = manifest.get("runtime_binding", {}).get("start", {})
    binding_detail = {
        "receipt_manifest_sha256": atomic_capture.get("manifest_sha256") if isinstance(atomic_capture, Mapping) else None,
        "actual_manifest_sha256": manifest_sha256,
        "receipt_source_epoch": atomic_capture.get("source_epoch") if isinstance(atomic_capture, Mapping) else None,
        "manifest_source_epoch": manifest.get("source_epoch"),
        "receipt_candidate_commit": atomic_capture.get("candidate_commit") if isinstance(atomic_capture, Mapping) else None,
        "manifest_candidate_commit": manifest.get("provenance", {}).get("head"),
        "receipt_runtime_epoch": atomic_capture.get("runtime_epoch") if isinstance(atomic_capture, Mapping) else None,
        "manifest_runtime_epoch": runtime_start.get("runtime_epoch") if isinstance(runtime_start, Mapping) else None,
    }
    _check(
        report,
        "receipt_manifest_runtime_binding",
        isinstance(atomic_capture, Mapping)
        and atomic_capture.get("exit_code") == 0
        and atomic_capture.get("manifest_sha256") == manifest_sha256
        and atomic_capture.get("source_epoch") == manifest.get("source_epoch")
        and atomic_capture.get("candidate_commit") == manifest.get("provenance", {}).get("head")
        and atomic_capture.get("runtime_epoch") == runtime_start.get("runtime_epoch"),
        binding_detail,
    )

    frames = manifest.get("frames", ())
    trace_by_index = {item.get("frame_index"): item for item in trace_records}
    paired = [
        (frame, trace_by_index.get(frame.get("frame_index"))) for frame in frames
    ]
    missing = [frame.get("frame_index") for frame, trace in paired if trace is None]
    paired = [(frame, trace) for frame, trace in paired if trace is not None]
    _check(
        report,
        "atomic_channel_coverage",
        len(paired) == len(frames) == len(trace_records)
        and not missing
        and all(isinstance(trace.get("presentation_channels"), Mapping) for _, trace in paired),
        {
            "frame_count": len(frames),
            "trace_count": len(trace_records),
            "paired_count": len(paired),
            "missing_trace_frames": missing,
        },
    )

    by_scenario: Dict[str, List[Mapping[str, Any]]] = {
        name: [] for name in EXPECTED_SCENARIOS
    }
    for frame, trace in paired:
        if frame.get("capture_owned") is True and frame.get("scenario") in by_scenario:
            by_scenario[str(frame["scenario"])].append(trace)
    _check(
        report,
        "exact_twenty_second_capture",
        all(
            len(by_scenario[name]) == EXPECTED_FRAME_COUNTS[name]
            for name in EXPECTED_SCENARIOS
        ),
        {name: len(by_scenario[name]) for name in EXPECTED_SCENARIOS},
    )
    owned_frames = [frame for frame in frames if frame.get("capture_owned") is True]
    capture_wall_span = (
        float(owned_frames[-1].get("elapsed_seconds", math.nan))
        - float(owned_frames[0].get("elapsed_seconds", math.nan))
        if len(owned_frames) >= 2
        else math.nan
    )
    expected_wall_span = (
        (len(owned_frames) - 1) / fps
        if (fps := float(manifest.get("init", {}).get("fps", 0.0) or 0.0)) > 0.0
        else math.nan
    )
    wall_ratio = (
        capture_wall_span / expected_wall_span
        if expected_wall_span > 0.0 and math.isfinite(capture_wall_span)
        else math.nan
    )
    _check(
        report,
        "capture_wall_clock_cadence",
        math.isfinite(wall_ratio) and 0.90 <= wall_ratio <= 1.20,
        {
            "owned_frame_count": len(owned_frames),
            "expected_span_seconds": round(expected_wall_span, 6)
            if math.isfinite(expected_wall_span)
            else None,
            "actual_span_seconds": round(capture_wall_span, 6)
            if math.isfinite(capture_wall_span)
            else None,
            "actual_to_expected_ratio": round(wall_ratio, 6)
            if math.isfinite(wall_ratio)
            else None,
            "allowed_ratio": [0.90, 1.20],
        },
    )

    all_trace = [trace for _, trace in paired]
    channels = [trace["presentation_channels"] for trace in all_trace]
    owned_channel_segments = _owned_channel_segments(paired)
    owned_channels = [
        channel for segment in owned_channel_segments for channel in segment
    ]
    authorities = sorted({item.get("speech_mouth_authority") for item in owned_channels})
    actions = sorted({item.get("action") for item in owned_channels})
    locomotion = sorted({item.get("locomotion") for item in owned_channels})
    mouth_counts: Dict[str, int] = {}
    for item in owned_channels:
        shape = str(item.get("rendered_mouth_shape"))
        mouth_counts[shape] = mouth_counts.get(shape, 0) + 1
    _check(
        report,
        "governed_aligned_speech_authority",
        bool(owned_channels)
        and authorities == ["media_alignment"]
        and set(actions).issubset({"speaking", "explaining"})
        and locomotion == ["idle"],
        {
            "speech_authorities": authorities,
            "actions": actions,
            "locomotion": locomotion,
        },
    )
    _check(
        report,
        "aligned_mouth_shape_coverage",
        mouth_counts.get("closed", 0) > 0
        and all(mouth_counts.get(shape, 0) > 0 for shape in OPEN_MOUTHS),
        mouth_counts,
    )
    mouth_pixel_hashes: Dict[str, set] = {}
    mouth_pixel_counts: Dict[str, List[int]] = {}
    for item in owned_channels:
        shape = str(item.get("rendered_mouth_shape"))
        mouth_pixel_hashes.setdefault(shape, set()).add(item.get("mouth_pixel_sha256"))
        mouth_pixel_counts.setdefault(shape, []).append(int(item.get("mouth_painted_cells", 0)))
    visible_mouth_hashes = {
        shape: sorted(value)
        for shape, value in mouth_pixel_hashes.items()
        if shape in {"closed"} | OPEN_MOUTHS
    }
    _check(
        report,
        "visible_mouth_pixel_animation",
        set(visible_mouth_hashes) == {"closed"} | OPEN_MOUTHS
        and all(
            len(hashes) == 1
            and "legacy_unspecified" not in hashes
            and min(mouth_pixel_counts[shape]) > 0
            for shape, hashes in visible_mouth_hashes.items()
        )
        and len({hashes[0] for hashes in visible_mouth_hashes.values()}) >= 5,
        {
            "pixel_hashes_by_shape": visible_mouth_hashes,
            "painted_cell_ranges": {
                shape: [min(values), max(values)]
                for shape, values in mouth_pixel_counts.items()
                if values
            },
        },
    )

    mouth_run_segments = [
        _mouth_runs(segment) for segment in owned_channel_segments if segment
    ]
    mouth_runs = [run for segment in mouth_run_segments for run in segment]
    mouth_switch_count = sum(max(0, len(segment) - 1) for segment in mouth_run_segments)
    mouth_duration_seconds = len(owned_channels) / fps if fps else 0.0
    mouth_switch_rate = (
        mouth_switch_count / mouth_duration_seconds
        if mouth_duration_seconds > 0.0
        else math.inf
    )
    short_internal_runs = [
        {
            "segment_index": segment_index,
            "run_index": run_index,
            "shape": shape,
            "frames": length,
        }
        for segment_index, segment in enumerate(mouth_run_segments)
        for run_index, (shape, length) in enumerate(segment[1:-1], start=1)
        if length < 3
    ]
    aperture_jumps = []
    for segment_index, segment in enumerate(mouth_run_segments):
        for transition_index, ((left, _), (right, _)) in enumerate(
            zip(segment, segment[1:])
        ):
            left_rank = MOUTH_APERTURE.get(left)
            right_rank = MOUTH_APERTURE.get(right)
            delta = (
                None
                if left_rank is None or right_rank is None
                else abs(left_rank - right_rank)
            )
            if delta is None or delta > 1:
                aperture_jumps.append(
                    {
                        "segment_index": segment_index,
                        "transition_index": transition_index,
                        "from": left,
                        "to": right,
                        "aperture_delta": delta,
                    }
                )
    run_length_counts = Counter(length for _, length in mouth_runs)
    _check(
        report,
        "readable_mouth_presentation_cadence",
        bool(mouth_runs)
        and mouth_switch_count >= MINIMUM_MOUTH_SWITCHES
        and mouth_switch_rate <= MAXIMUM_MOUTH_SWITCHES_PER_SECOND
        and not short_internal_runs
        and not aperture_jumps,
        {
            "run_count": len(mouth_runs),
            "segment_count": len(mouth_run_segments),
            "switch_count": mouth_switch_count,
            "switches_per_second": round(mouth_switch_rate, 3)
            if math.isfinite(mouth_switch_rate)
            else None,
            "minimum_switch_count": MINIMUM_MOUTH_SWITCHES,
            "maximum_switches_per_second": MAXIMUM_MOUTH_SWITCHES_PER_SECOND,
            "run_length_frame_counts": {
                str(length): count
                for length, count in sorted(run_length_counts.items())
            },
            "minimum_internal_hold_frames": 3,
            "short_internal_runs": short_internal_runs,
            "aperture_jumps": aperture_jumps,
        },
    )

    gaze_detail: Dict[str, object] = {}
    gaze_passed = True
    for name, expected in EXPECTED_GAZE.items():
        scenario_channels = [item["presentation_channels"] for item in by_scenario[name]]
        aims = sorted({item.get("gaze_aim") for item in scenario_channels})
        authoritative = sorted(
            {item.get("gaze_authoritative") for item in scenario_channels}
        )
        visible_offsets = []
        for item in scenario_channels:
            if item.get("blink_closed"):
                continue
            apertures = item.get("eye_apertures", ())
            blue = item.get("eye_blue_cells", ())
            if not apertures or not blue:
                continue
            per_eye = []
            for aperture in apertures:
                points = [
                    point
                    for point in blue
                    if aperture["min_x"] <= point["x"] <= aperture["max_x"]
                    and aperture["min_y"] <= point["y"] <= aperture["max_y"]
                ]
                if points:
                    center = (aperture["min_x"] + aperture["max_x"]) / 2.0
                    per_eye.append(sum(point["x"] for point in points) / len(points) - center)
            if len(per_eye) == len(apertures):
                visible_offsets.append(round(sum(per_eye) / len(per_eye), 3))
        expected_visible = bool(visible_offsets) and all(
            (-1.5 <= offset <= -0.5)
            if expected < 0
            else (0.5 <= offset <= 1.5)
            if expected > 0
            else (-0.25 <= offset <= 0.25)
            for offset in visible_offsets
        )
        gaze_detail[name] = {
            "aims": aims,
            "authoritative": authoritative,
            "visible_eye_offsets": sorted(set(visible_offsets)),
        }
        gaze_passed = (
            gaze_passed
            and aims == [expected]
            and authoritative == [True]
            and expected_visible
        )
    _check(report, "left_center_right_gaze_returns", gaze_passed, gaze_detail)

    blink_ranges = _closed_ranges(all_trace)
    blink_lengths = [end - start for start, end in blink_ranges]
    blink_durations_ms = [
        round(length * 1000.0 / fps, 3) for length in blink_lengths
    ] if fps else []
    visible_blinks = []
    blink_onset_mouths = []
    blink_frame_mouths = []
    for start, end in blink_ranges:
        visible_blinks.append(
            all(
                int(channels[index].get("blink_painted_cells", 0)) > 0
                for index in range(start, end)
            )
            and (start == 0 or all_trace[start]["frame_sha256"] != all_trace[start - 1]["frame_sha256"])
            and (end == len(all_trace) or all_trace[end - 1]["frame_sha256"] != all_trace[end]["frame_sha256"])
        )
        blink_onset_mouths.append(channels[start].get("rendered_mouth_shape"))
        blink_frame_mouths.extend(
            channels[index].get("rendered_mouth_shape") for index in range(start, end)
        )
    _check(
        report,
        "visible_blinks_during_speech",
        bool(blink_ranges)
        and all(3 <= length <= 4 for length in blink_lengths)
        and all(100.0 <= duration <= 200.0 for duration in blink_durations_ms)
        and all(visible_blinks),
        {
            "closed_frame_runs": blink_lengths,
            "durations_ms": blink_durations_ms,
            "visible_runs": visible_blinks,
        },
    )
    _check(
        report,
        "mouth_blink_independence",
        "closed" in blink_frame_mouths
        and bool(OPEN_MOUTHS.intersection(blink_frame_mouths))
        and len(set(blink_onset_mouths)) >= 2,
        {
            "blink_onset_mouths": blink_onset_mouths,
            "blink_frame_mouths": sorted(set(blink_frame_mouths)),
        },
    )

    roots = [
        (float(item.get("world_root_x", math.inf)), float(item.get("world_root_z", math.inf)))
        for item in all_trace
    ]
    baseline_root = roots[0] if roots else (math.inf, math.inf)
    planted_frames = sum(
        root == baseline_root
        and trace.get("animation_root_policy") == "fixed"
        and trace.get("support_contact") == "both_feet"
        and trace["presentation_channels"].get("locomotion") == "idle"
        for root, trace in zip(roots, all_trace)
    )
    body_hashes = [item.get("body_pixel_sha256") for item in channels]
    body_hash_counts = Counter(body_hashes)
    dominant_body_count = body_hash_counts.most_common(1)[0][1] if body_hash_counts else 0
    body_still_percentage = round(
        100.0 * dominant_body_count / len(body_hashes), 3
    ) if body_hashes else 0.0
    planted_percentage = round(
        100.0 * planted_frames / len(all_trace), 3
    ) if all_trace else 0.0
    contact = manifest.get("contact_verification", {})
    _check(
        report,
        "purposeful_planted_body_stillness",
        body_still_percentage >= 90.0
        and planted_percentage >= 90.0
        and "legacy_unspecified" not in body_hash_counts
        and isinstance(contact, Mapping)
        and contact.get("passed") is True
        and float(contact.get("maximum_planted_drift_cells", math.inf)) <= 1.0,
        {
            "body_still_percentage": body_still_percentage,
            "planted_percentage": planted_percentage,
            "body_pixel_hash_counts": dict(body_hash_counts),
            "contact_passed": contact.get("passed") if isinstance(contact, Mapping) else None,
            "maximum_planted_drift_cells": (
                contact.get("maximum_planted_drift_cells")
                if isinstance(contact, Mapping)
                else None
            ),
        },
    )

    eye_failures = []
    for trace in all_trace:
        presented = trace["presentation_channels"]
        apertures = presented.get("eye_apertures", ())
        for point in presented.get("eye_blue_cells", ()):
            if not any(
                aperture["min_x"] <= point["x"] <= aperture["max_x"]
                and aperture["min_y"] <= point["y"] <= aperture["max_y"]
                for aperture in apertures
            ):
                eye_failures.append(trace.get("frame_index"))
    _check(
        report,
        "eye_pixels_remain_in_apertures",
        bool(all_trace)
        and all(item["presentation_channels"].get("eye_apertures") for item in all_trace)
        and not eye_failures,
        {"escaped_frames": eye_failures},
    )

    edge = receipt.get("capture_edge", {})
    browser = edge.get("browser", {}) if isinstance(edge, Mapping) else {}
    wizard_media = edge.get("wizard_media", {}) if isinstance(edge, Mapping) else {}
    application = wizard_media.get("application", {}) if isinstance(wizard_media, Mapping) else {}
    governed = wizard_media.get("governed_speech", {}) if isinstance(wizard_media, Mapping) else {}
    wizard_state = edge.get("wizard_state", {}) if isinstance(edge, Mapping) else {}
    session = wizard_media.get("session", {}) if isinstance(wizard_media, Mapping) else {}
    audio_artifact = receipt.get("audio_artifact", {})
    browser_time = browser.get("currentTimeMs")
    application_time = application.get("media_time_ms")
    av_offset_ms = (
        abs(int(browser_time) - int(application_time))
        if isinstance(browser_time, int) and isinstance(application_time, int)
        else None
    )
    _check(
        report,
        "real_governed_prism_edge",
        receipt.get("schema") == "character_director_prism_governed_speech_v1"
        and isinstance(browser.get("durationMs"), int)
        and browser["durationMs"] >= 20_000
        and browser.get("paused") is False
        and int(browser.get("currentTimeMs", 0)) > 0
        and application.get("active") is True
        and application.get("source_slot") == "speech"
        and governed.get("active") is True
        and governed.get("status") == "release_active"
        and wizard_state.get("speech_mouth_authority") == "media_alignment"
        and isinstance(wizard_state.get("speech_id"), str)
        and isinstance(audio_artifact, Mapping)
        and isinstance(audio_artifact.get("sha256"), str)
        and len(audio_artifact["sha256"]) == 64
        and int(audio_artifact.get("bytes", 0)) > 0
        and audio_artifact.get("speech_id") == wizard_state.get("speech_id")
        and str(audio_artifact.get("declared_sha256", "")).removeprefix("sha256:")
        == audio_artifact.get("sha256"),
        {
            "receipt_schema": receipt.get("schema"),
            "duration_ms": browser.get("durationMs"),
            "browser_paused": browser.get("paused"),
            "application": application,
            "governed": governed,
            "mouth_authority": wizard_state.get("speech_mouth_authority"),
            "speech_id": wizard_state.get("speech_id"),
            "audio_artifact": audio_artifact,
        },
    )

    timeline = receipt.get("av_timeline", {})
    timeline_samples = timeline.get("samples", ()) if isinstance(timeline, Mapping) else ()
    valid_timeline = [
        sample
        for sample in timeline_samples
        if isinstance(sample, Mapping)
        and isinstance(sample.get("browser_media_time_ms"), int)
        and isinstance(sample.get("wizard_media_time_ms"), int)
        and isinstance(sample.get("absolute_offset_ms"), int)
    ]
    timeline_offsets = [int(sample["absolute_offset_ms"]) for sample in valid_timeline]
    timeline_p95 = _percentile_nearest_rank(timeline_offsets, 0.95)
    elapsed_span = (
        int(valid_timeline[-1].get("elapsed_ms", 0))
        - int(valid_timeline[0].get("elapsed_ms", 0))
        if valid_timeline
        else 0
    )
    speech_ids = sorted(
        {sample.get("speech_id") for sample in valid_timeline},
        key=lambda value: str(value),
    )
    media_prefixes = sorted(
        {sample.get("media_hash_prefix") for sample in valid_timeline},
        key=lambda value: str(value),
    )
    audio_sha = audio_artifact.get("sha256") if isinstance(audio_artifact, Mapping) else None
    expected_media_prefix = "sha256:{}".format(audio_sha[:8]) if isinstance(audio_sha, str) else None
    browser_times = [int(sample["browser_media_time_ms"]) for sample in valid_timeline]
    wizard_times = [int(sample["wizard_media_time_ms"]) for sample in valid_timeline]
    browser_regressions = _time_regressions(browser_times)
    wizard_regressions = _time_regressions(wizard_times)
    regression_limit = max(1, math.ceil(len(valid_timeline) * 0.02))
    bounded_times = (
        not browser_regressions
        and len(wizard_regressions) <= regression_limit
        and max(wizard_regressions, default=0) <= 50
    )
    _check(
        report,
        "browser_wizard_av_timeline_alignment",
        isinstance(timeline, Mapping)
        and timeline.get("schema") == "character_director_av_timeline_v1"
        and len(valid_timeline) >= 100
        and len(valid_timeline) == len(timeline_samples)
        and elapsed_span >= 19_000
        and timeline_p95 is not None
        and timeline_p95 <= 250
        and bounded_times
        and speech_ids == [wizard_state.get("speech_id")]
        and media_prefixes == [expected_media_prefix]
        and all(sample.get("browser_playing") is True for sample in valid_timeline)
        and all(sample.get("application_active") is True for sample in valid_timeline)
        and all(sample.get("application_source_slot") == "speech" for sample in valid_timeline)
        and all(sample.get("speech_mouth_authority") == "media_alignment" for sample in valid_timeline),
        {
            "sample_count": len(valid_timeline),
            "elapsed_span_ms": elapsed_span,
            "absolute_offset_p95_ms": timeline_p95,
            "absolute_offset_max_ms": max(timeline_offsets) if timeline_offsets else None,
            "speech_ids": speech_ids,
            "media_hash_prefixes": media_prefixes,
            "expected_media_hash_prefix": expected_media_prefix,
            "browser_time_regressions_ms": browser_regressions,
            "wizard_time_regressions_ms": wizard_regressions,
            "wizard_regression_count_limit": regression_limit,
            "wizard_regression_size_limit_ms": 50,
            "bounded_media_times": bounded_times,
            "maximum_offset_ms": 250,
        },
    )

    report["metrics"] = {
        "frame_count": len(frames),
        "owned_frame_count": sum(frame.get("capture_owned") is True for frame in frames),
        "capture_wall_span_seconds": round(capture_wall_span, 6)
        if math.isfinite(capture_wall_span)
        else None,
        "capture_wall_ratio": round(wall_ratio, 6)
        if math.isfinite(wall_ratio)
        else None,
        "audio_duration_ms": browser.get("durationMs"),
        "av_edge_offset_ms": av_offset_ms,
        "av_timeline_offset_p95_ms": timeline_p95,
        "av_timeline_sample_count": len(valid_timeline),
        "body_still_percentage": body_still_percentage,
        "planted_percentage": planted_percentage,
        "unique_body_pixel_hashes": len(body_hash_counts),
        "blink_count": len(blink_ranges),
        "blink_durations_ms": blink_durations_ms,
        "blink_onset_mouths": blink_onset_mouths,
        "mouth_shape_counts": mouth_counts,
        "mouth_presentation_run_count": len(mouth_runs),
        "mouth_presentation_switch_count": mouth_switch_count,
        "mouth_presentation_switches_per_second": round(mouth_switch_rate, 3)
        if math.isfinite(mouth_switch_rate)
        else None,
        "mouth_presentation_short_internal_run_count": len(short_internal_runs),
        "mouth_presentation_aperture_jump_count": len(aperture_jumps),
        "action_values": actions,
        "speech_authorities": authorities,
        "unique_presented_frame_hashes": len(
            {item.get("frame_sha256") for item in all_trace}
        ),
    }
    report["passed"] = bool(report["checks"]) and all(
        item["passed"] for item in report["checks"]
    )
    return report


def load_and_analyze(manifest_path: Path, receipt_path: Path) -> Dict[str, Any]:
    evidence_dir = manifest_path.resolve().parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest, evidence_dir)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    trace_path = evidence_dir / manifest["animation_truth_trace"]["path"]
    trace_records: List[Mapping[str, Any]] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if line:
            trace_records.append(
                AnimationTruthTraceV1.from_mapping(json.loads(line)).to_mapping()
            )
    report = analyze_v2(
        manifest,
        trace_records,
        receipt,
        manifest_sha256=sha256_file(manifest_path),
    )
    audio_record = receipt.get("audio_artifact", {})
    audio_path = None
    audio_integrity = False
    if isinstance(audio_record, Mapping):
        relative = audio_record.get("path")
        if (
            isinstance(relative, str)
            and relative
            and not Path(relative).is_absolute()
            and ".." not in Path(relative).parts
        ):
            candidate = (evidence_dir / relative).resolve()
            try:
                candidate.relative_to(evidence_dir)
            except ValueError:
                candidate = None
            if candidate is not None and candidate.is_file():
                audio_path = candidate
                audio_integrity = (
                    candidate.stat().st_size == audio_record.get("bytes")
                    and sha256_file(candidate) == audio_record.get("sha256")
                )
    _check(
        report,
        "retained_audio_artifact_integrity",
        audio_integrity,
        {
            "path": audio_record.get("path") if isinstance(audio_record, Mapping) else None,
            "bytes": audio_record.get("bytes") if isinstance(audio_record, Mapping) else None,
            "sha256": audio_record.get("sha256") if isinstance(audio_record, Mapping) else None,
        },
    )
    browser_record = receipt.get("browser_presentation", {})
    browser_video = None
    browser_metrics_path = None
    browser_integrity = False
    if isinstance(browser_record, Mapping) and browser_record.get("exit_code") == 0:
        video_relative = browser_record.get("video_path")
        metrics_relative = browser_record.get("metrics_path")
        if all(
            isinstance(value, str)
            and value
            and not Path(value).is_absolute()
            and ".." not in Path(value).parts
            for value in (video_relative, metrics_relative)
        ):
            browser_video = (evidence_dir / video_relative).resolve()
            browser_metrics_path = (evidence_dir / metrics_relative).resolve()
            if browser_video.is_file() and browser_metrics_path.is_file():
                browser_metrics = json.loads(browser_metrics_path.read_text(encoding="utf-8"))
                frame_count = int(browser_metrics.get("frame_count", 0))
                browser_integrity = (
                    browser_metrics.get("schema") == "character_director_browser_layout_v1"
                    and browser_metrics.get("candidate_commit") == manifest.get("provenance", {}).get("head")
                    and browser_metrics.get("capture_manifest_sha256") == sha256_file(manifest_path)
                    and not browser_metrics.get("page_errors")
                    and browser_metrics.get("video_sha256") == sha256_file(browser_video)
                    and browser_metrics.get("video_bytes") == browser_video.stat().st_size
                    and frame_count > 0
                    and int(browser_metrics.get("screencast_event_count", 0)) >= round(frame_count * 0.50)
                    and int(browser_metrics.get("duplicate_sample_count", frame_count)) <= round(frame_count * 0.50)
                )
    _check(
        report,
        "real_browser_presentation_integrity",
        browser_integrity,
        {
            "video_path": browser_record.get("video_path") if isinstance(browser_record, Mapping) else None,
            "metrics_path": browser_record.get("metrics_path") if isinstance(browser_record, Mapping) else None,
        },
    )
    report["evidence_bindings"] = {
        "manifest": {
            "path": manifest_path.name,
            "bytes": manifest_path.stat().st_size,
            "sha256": sha256_file(manifest_path),
        },
        "trace": {
            "path": trace_path.relative_to(evidence_dir).as_posix(),
            "bytes": trace_path.stat().st_size,
            "sha256": sha256_file(trace_path),
        },
        "receipt": {
            "path": receipt_path.name,
            "bytes": receipt_path.stat().st_size,
            "sha256": sha256_file(receipt_path),
        },
        "audio": {
            "path": audio_path.relative_to(evidence_dir).as_posix() if audio_path else None,
            "bytes": audio_path.stat().st_size if audio_path else None,
            "sha256": sha256_file(audio_path) if audio_path else None,
        },
        "browser_presentation_video": {
            "path": browser_video.relative_to(evidence_dir).as_posix() if browser_video else None,
            "bytes": browser_video.stat().st_size if browser_video and browser_video.is_file() else None,
            "sha256": sha256_file(browser_video) if browser_video and browser_video.is_file() else None,
        },
        "browser_presentation_metrics": {
            "path": browser_metrics_path.relative_to(evidence_dir).as_posix() if browser_metrics_path else None,
            "bytes": browser_metrics_path.stat().st_size if browser_metrics_path and browser_metrics_path.is_file() else None,
            "sha256": sha256_file(browser_metrics_path) if browser_metrics_path and browser_metrics_path.is_file() else None,
        },
    }
    report["passed"] = bool(report["checks"]) and all(
        item["passed"] for item in report["checks"]
    )
    return report


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Character Director V2 evidence.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    report = load_and_analyze(args.manifest, args.receipt)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
