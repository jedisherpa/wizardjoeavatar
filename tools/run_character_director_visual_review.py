#!/usr/bin/env python3
"""Capture strict visual-review evidence from an already-running WizardJoe runtime."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import websockets

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.commanding import COMMAND_KINDS
from wizard_avatar.animation_trace import AnimationTruthTraceV1
from wizard_avatar.contact_verifier import DecodedRasterFrameV1, verify_contact_trace
from wizard_avatar.frame_hash import frame_hash
from wizard_avatar.protocol import CELL_BYTES, decode_frame


DEFAULT_BASE_URL = "http://127.0.0.1:8875"
DEFAULT_OUTPUT_DIR = ROOT / "evidence" / "character-director" / "real-runtime-visual-review"
PROTECTED_LEGACY_PORT = 8765
SOURCE_ID = "character-director-visual-review"
MANIFEST_SCHEMA_VERSION = 3
SUPPORTED_MANIFEST_SCHEMA_VERSIONS = {2, MANIFEST_SCHEMA_VERSION}
EVIDENCE_KIND = "external_real_runtime_visual_review"
PAIRING_DESCRIPTION = "atomic_animation_truth_trace_v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_OBJECT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
SCENARIO_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SCENARIO_PROGRAM_SCHEMA = "character_director_scenario_program_v1"
SCENARIO_PROGRAM_VERSION = 1
SCENARIO_PROGRAM_V2_SCHEMA = "character_director_scenario_program_v2"
SCENARIO_PROGRAM_V2_VERSION = 2
SCENARIO_PROGRAM_MAX_BYTES = 64 * 1024
SCENARIO_PROGRAM_MAX_STEPS = 64
SCENARIO_PROGRAM_MAX_SECONDS = 10 * 60
ACCEPTANCE_SCENARIO_RE = re.compile(r"^V(?:[1-9]|10)$")
REVIEW_BUNDLE_SCHEMA = "character_director_review_bundle_manifest_v1"
REVIEW_BUNDLE_VERSION = 2
SUPPORTED_REVIEW_BUNDLE_VERSIONS = {1, REVIEW_BUNDLE_VERSION}
SENSITIVE_TEXT_FIELDS = frozenset({"speech_text"})
CONTENT_MINIMIZATION_SCHEMA = "evidence_content_minimization_v1"
MEDIA_SESSION_SCENARIO_KIND = "media_session"
SCENARIO_KINDS = frozenset(COMMAND_KINDS) | {MEDIA_SESSION_SCENARIO_KIND}


class EvidenceFailure(RuntimeError):
    pass


class QueueOverflowError(EvidenceFailure):
    pass


class FrameGapError(EvidenceFailure):
    pass


class FrameDecodeError(EvidenceFailure):
    pass


class ManifestValidationError(ValueError):
    pass


def _text_evidence(value: str) -> Dict[str, Any]:
    encoded = value.encode("utf-8")
    return {
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "utf8_bytes": len(encoded),
        "character_count": len(value),
    }


def minimize_evidence_content(value: Any) -> Any:
    """Replace sensitive runtime text with non-reversible verification metadata."""

    if isinstance(value, Mapping):
        result: Dict[str, Any] = {}
        for key, item in value.items():
            if key in SENSITIVE_TEXT_FIELDS:
                evidence_key = "{}_evidence".format(key)
                if evidence_key in value:
                    raise EvidenceFailure(
                        "runtime payload contains both {} and {}".format(key, evidence_key)
                    )
                if item is None:
                    continue
                if not isinstance(item, str):
                    raise EvidenceFailure("runtime payload {} must be text".format(key))
                result[evidence_key] = _text_evidence(item)
            else:
                result[key] = minimize_evidence_content(item)
        return result
    if isinstance(value, (list, tuple)):
        return [minimize_evidence_content(item) for item in value]
    return value


def validate_evidence_content_minimization(value: Any, path: str = "$") -> None:
    """Reject raw sensitive text or malformed replacement evidence anywhere in a manifest."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            item_path = "{}.{}".format(path, key)
            _manifest_error(
                key not in SENSITIVE_TEXT_FIELDS,
                "raw sensitive field remains in evidence: {}".format(item_path),
            )
            if key in {"{}_evidence".format(name) for name in SENSITIVE_TEXT_FIELDS}:
                _manifest_error(
                    isinstance(item, Mapping)
                    and set(item) == {"sha256", "utf8_bytes", "character_count"}
                    and bool(SHA256_RE.fullmatch(str(item.get("sha256", ""))))
                    and _plain_int(item.get("utf8_bytes"))
                    and _plain_int(item.get("character_count")),
                    "invalid sensitive-text evidence: {}".format(item_path),
                )
            validate_evidence_content_minimization(item, item_path)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            validate_evidence_content_minimization(item, "{}[{}]".format(path, index))


@dataclass(frozen=True)
class InitMetadata:
    raw: str
    fps: float
    render_mode: int
    cols: int
    rows: int
    pixel_mode: int
    source_index: int
    duration_seconds: float
    cell_bytes: int
    extras: Dict[str, str]

    @property
    def expected_decoded_length(self) -> int:
        return self.cols * self.rows * self.cell_bytes

    def to_manifest(self) -> Dict[str, Any]:
        result = asdict(self)
        result["expected_decoded_length"] = self.expected_decoded_length
        return result


def _finite_number(value: str, name: str, minimum: float = 0.0, exclusive: bool = False) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("INIT {} must be numeric".format(name)) from exc
    if not math.isfinite(result) or result < minimum or (exclusive and result == minimum):
        comparator = ">" if exclusive else ">="
        raise ValueError("INIT {} must be finite and {} {}".format(name, comparator, minimum))
    return result


def _integer(value: str, name: str, minimum: int = 0) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("INIT {} must be an integer".format(name)) from exc
    if str(result) != value and not (value.startswith("+") and str(result) == value[1:]):
        raise ValueError("INIT {} must use integer syntax".format(name))
    if result < minimum:
        raise ValueError("INIT {} must be >= {}".format(name, minimum))
    return result


def parse_init(message: str) -> InitMetadata:
    """Parse the legacy INIT prefix and optional strict key/value extensions."""

    if not isinstance(message, str):
        raise ValueError("ASCILINE INIT must be text")
    parts = message.split(":")
    if len(parts) < 8 or parts[0] != "INIT":
        raise ValueError("missing ASCILINE INIT bootstrap")
    if (len(parts) - 8) % 2:
        raise ValueError("INIT extensions must be key/value pairs")

    extras: Dict[str, str] = {}
    for offset in range(8, len(parts), 2):
        key, value = parts[offset], parts[offset + 1]
        if not key or not value or key in extras:
            raise ValueError("INIT extensions require unique non-empty keys and values")
        extras[key] = value

    fps = _finite_number(parts[1], "fps", exclusive=True)
    render_mode = _integer(parts[2], "render_mode")
    cols = _integer(parts[3], "cols", 1)
    rows = _integer(parts[4], "rows", 1)
    pixel_mode = _integer(parts[5], "pixel_mode")
    source_index = _integer(parts[6], "source_index")
    duration_seconds = _finite_number(parts[7], "duration_seconds")
    cell_bytes = _integer(extras.get("CELL_BYTES", str(CELL_BYTES)), "cell_bytes", 1)
    if cell_bytes != CELL_BYTES:
        raise ValueError("INIT cell width {} is incompatible with decoder width {}".format(cell_bytes, CELL_BYTES))
    if render_mode != 5 or pixel_mode != 0:
        raise ValueError("INIT must describe ASCILINE render mode 5 and pixel mode 0")
    if "CODEC" in extras and extras["CODEC"] != "1":
        raise ValueError("INIT CODEC must be adaptive codec 1")

    return InitMetadata(
        raw=message,
        fps=fps,
        render_mode=render_mode,
        cols=cols,
        rows=rows,
        pixel_mode=pixel_mode,
        source_index=source_index,
        duration_seconds=duration_seconds,
        cell_bytes=cell_bytes,
        extras=extras,
    )


@dataclass(frozen=True)
class Scenario:
    name: str
    kind: str
    payload: Dict[str, Any]
    settle_seconds: float
    capture_seconds: float

    def to_mapping(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TraceTriggerV2:
    authored_frame: int
    clip: Optional[str] = None
    marker_id: Optional[str] = None

    def matches(self, trace: Mapping[str, Any]) -> bool:
        if self.clip is not None:
            return (
                trace.get("animation_clip_id") == self.clip
                and trace.get("animation_authored_frame") == self.authored_frame
            )
        return any(
            isinstance(event, Mapping)
            and event.get("marker_id") == self.marker_id
            and event.get("animation_authored_frame") == self.authored_frame
            for event in trace.get("presentation_marker_events", ())
        )

    def to_mapping(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"authored_frame": self.authored_frame}
        if self.clip is not None:
            result["clip"] = self.clip
        if self.marker_id is not None:
            result["marker_id"] = self.marker_id
        return result


@dataclass(frozen=True)
class ScenarioV2:
    name: str
    kind: str
    payload: Dict[str, Any]
    capture_frames: Optional[int] = None
    until_trace: Optional[TraceTriggerV2] = None
    max_frames: Optional[int] = None
    scheduled_commands: Tuple["ScheduledCommandV2", ...] = ()

    def planned_frame_count(self, fps: float) -> int:
        del fps
        return self.capture_frames if self.capture_frames is not None else int(self.max_frames or 0)

    def to_mapping(self) -> Dict[str, Any]:
        timing: Dict[str, Any]
        if self.capture_frames is not None:
            timing = {"capture_frames": self.capture_frames}
            if self.scheduled_commands:
                timing["scheduled_commands"] = [
                    command.to_mapping() for command in self.scheduled_commands
                ]
        else:
            timing = {
                "until_trace": self.until_trace.to_mapping() if self.until_trace else {},
                "max_frames": self.max_frames,
            }
        return {
            "name": self.name,
            "kind": self.kind,
            "payload": self.payload,
            "timing": timing,
        }


@dataclass(frozen=True)
class ScheduledCommandV2:
    name: str
    at_frame: int
    kind: str
    payload: Dict[str, Any]

    def to_mapping(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioProgramV1:
    schema: str
    schema_version: int
    program_id: str
    acceptance_scenario: str
    scenarios: Tuple[Scenario, ...]
    source_sha256: str
    source_bytes: bytes = field(repr=False, compare=False)

    @property
    def total_duration_seconds(self) -> float:
        return sum(item.settle_seconds + item.capture_seconds for item in self.scenarios)

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "program_id": self.program_id,
            "acceptance_scenario": self.acceptance_scenario,
            "scenario_count": len(self.scenarios),
            "total_duration_seconds": round(self.total_duration_seconds, 6),
            "source_sha256": self.source_sha256,
            "artifact_path": "scenario-program.json",
        }


@dataclass(frozen=True)
class ScenarioProgramV2:
    schema: str
    schema_version: int
    program_id: str
    acceptance_scenario: str
    scenarios: Tuple[ScenarioV2, ...]
    source_sha256: str
    source_bytes: bytes = field(repr=False, compare=False)

    @property
    def maximum_capture_frame_count(self) -> int:
        return sum(item.planned_frame_count(24.0) for item in self.scenarios)

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "program_id": self.program_id,
            "acceptance_scenario": self.acceptance_scenario,
            "scenario_count": len(self.scenarios),
            "maximum_capture_frame_count": self.maximum_capture_frame_count,
            "source_sha256": self.source_sha256,
            "artifact_path": "scenario-program.json",
        }


def load_scenario_program(path: Path) -> Any:
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise ValueError("cannot read scenario program: {}".format(exc)) from exc
    if not source or len(source) > SCENARIO_PROGRAM_MAX_BYTES:
        raise ValueError("scenario program must be between 1 and {} bytes".format(SCENARIO_PROGRAM_MAX_BYTES))
    try:
        raw = json.loads(source.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("scenario program must be UTF-8 JSON") from exc
    required = {
        "schema",
        "schema_version",
        "program_id",
        "acceptance_scenario",
        "scenarios",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        supplied = set(raw) if isinstance(raw, Mapping) else set()
        raise ValueError(
            "scenario program schema mismatch; missing={} unknown={}".format(
                sorted(required.difference(supplied)),
                sorted(supplied.difference(required)),
            )
        )
    schema_pair = raw["schema"], raw["schema_version"]
    if schema_pair not in {
        (SCENARIO_PROGRAM_SCHEMA, SCENARIO_PROGRAM_VERSION),
        (SCENARIO_PROGRAM_V2_SCHEMA, SCENARIO_PROGRAM_V2_VERSION),
    }:
        raise ValueError("unsupported scenario program schema or version")
    if not isinstance(raw["program_id"], str) or not SCENARIO_NAME_RE.fullmatch(raw["program_id"]):
        raise ValueError("scenario program_id must be a lowercase kebab-case identifier")
    if not isinstance(raw["acceptance_scenario"], str) or not ACCEPTANCE_SCENARIO_RE.fullmatch(raw["acceptance_scenario"]):
        raise ValueError("acceptance_scenario must be V1 through V10")
    scenarios = (
        validate_scenarios(raw["scenarios"])
        if schema_pair == (SCENARIO_PROGRAM_SCHEMA, SCENARIO_PROGRAM_VERSION)
        else validate_scenarios_v2(raw["scenarios"])
    )
    if len(scenarios) > SCENARIO_PROGRAM_MAX_STEPS:
        raise ValueError("scenario program exceeds the step limit")
    if schema_pair == (SCENARIO_PROGRAM_SCHEMA, SCENARIO_PROGRAM_VERSION):
        total = sum(item.settle_seconds + item.capture_seconds for item in scenarios)
        if total > SCENARIO_PROGRAM_MAX_SECONDS:
            raise ValueError("scenario program exceeds the duration limit")
        return ScenarioProgramV1(
            schema=SCENARIO_PROGRAM_SCHEMA,
            schema_version=SCENARIO_PROGRAM_VERSION,
            program_id=raw["program_id"],
            acceptance_scenario=raw["acceptance_scenario"],
            scenarios=scenarios,
            source_sha256=hashlib.sha256(source).hexdigest(),
            source_bytes=source,
        )
    return ScenarioProgramV2(
        schema=SCENARIO_PROGRAM_V2_SCHEMA,
        schema_version=SCENARIO_PROGRAM_V2_VERSION,
        program_id=raw["program_id"],
        acceptance_scenario=raw["acceptance_scenario"],
        scenarios=scenarios,
        source_sha256=hashlib.sha256(source).hexdigest(),
        source_bytes=source,
    )


def _duration(value: object, name: str, allow_zero: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("{} must be a finite number".format(name))
    result = float(value)
    if not math.isfinite(result) or result < 0 or (not allow_zero and result == 0):
        raise ValueError("{} must be {}".format(name, "nonnegative" if allow_zero else "positive"))
    return result


def _copy_json(value: object, path: str = "payload") -> Any:
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("{} keys must be strings".format(path))
            result[key] = _copy_json(item, "{}.{}".format(path, key))
        return result
    if isinstance(value, list):
        return [_copy_json(item, "{}[]".format(path)) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError("{} must contain only finite JSON values".format(path))


def validate_scenarios(values: Sequence[Mapping[str, Any]]) -> Tuple[Scenario, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
        raise ValueError("scenarios must be a non-empty sequence")
    required = {"name", "kind", "payload", "settle_seconds", "capture_seconds"}
    result: List[Scenario] = []
    names = set()
    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise ValueError("scenario {} must be an object".format(index))
        if set(value) != required:
            missing = sorted(required - set(value))
            unknown = sorted(set(value) - required)
            raise ValueError("scenario {} schema mismatch; missing={} unknown={}".format(index, missing, unknown))
        name = value["name"]
        kind = value["kind"]
        payload = value["payload"]
        if not isinstance(name, str) or not SCENARIO_NAME_RE.fullmatch(name):
            raise ValueError("scenario name must be a lowercase kebab-case identifier")
        if name in names:
            raise ValueError("scenario names must be unique")
        if not isinstance(kind, str) or kind not in SCENARIO_KINDS:
            raise ValueError("unsupported scenario command kind: {}".format(kind))
        if not isinstance(payload, Mapping):
            raise ValueError("scenario payload must be an object")
        payload_copy = _copy_json(payload)
        names.add(name)
        result.append(
            Scenario(
                name=name,
                kind=kind,
                payload=payload_copy,
                settle_seconds=_duration(value["settle_seconds"], "settle_seconds", True),
                capture_seconds=_duration(value["capture_seconds"], "capture_seconds", False),
            )
        )
    return tuple(result)


def _positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("{} must be a positive integer".format(name))
    return value


def _trace_trigger_v2(value: object) -> TraceTriggerV2:
    if not isinstance(value, Mapping):
        raise ValueError("until_trace must be an object")
    supplied = set(value)
    if supplied not in (
        {"clip", "authored_frame"},
        {"marker_id", "authored_frame"},
    ):
        raise ValueError(
            "until_trace requires exactly authored_frame and either clip or marker_id"
        )
    authored_frame = value.get("authored_frame")
    if isinstance(authored_frame, bool) or not isinstance(authored_frame, int) or authored_frame < 0:
        raise ValueError("until_trace.authored_frame must be a nonnegative integer")
    clip = value.get("clip")
    marker_id = value.get("marker_id")
    if clip is not None and (
        not isinstance(clip, str) or not SCENARIO_NAME_RE.fullmatch(clip.replace("_", "-"))
    ):
        raise ValueError("until_trace.clip must be a lowercase clip identifier")
    if marker_id is not None and (
        not isinstance(marker_id, str)
        or marker_id
        not in {
            "action_commit",
            "action_effect",
            "action_recoverable",
            "action_settled",
        }
    ):
        raise ValueError("until_trace.marker_id is not an accepted action marker")
    return TraceTriggerV2(
        authored_frame=authored_frame,
        clip=clip,
        marker_id=marker_id,
    )


def _scheduled_commands_v2(
    values: object,
    capture_frames: int,
) -> Tuple[ScheduledCommandV2, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
        raise ValueError("timing.scheduled_commands must be a non-empty sequence")
    result: List[ScheduledCommandV2] = []
    names = set()
    previous_frame = 0
    required = {"name", "at_frame", "kind", "payload"}
    for index, value in enumerate(values):
        if not isinstance(value, Mapping) or set(value) != required:
            raise ValueError("scheduled command {} schema mismatch".format(index))
        name = value["name"]
        at_frame = value["at_frame"]
        kind = value["kind"]
        payload = value["payload"]
        if not isinstance(name, str) or not SCENARIO_NAME_RE.fullmatch(name):
            raise ValueError("scheduled command name must be a lowercase kebab-case identifier")
        if name in names:
            raise ValueError("scheduled command names must be unique within a capture")
        if (
            isinstance(at_frame, bool)
            or not isinstance(at_frame, int)
            or at_frame <= previous_frame
            or at_frame >= capture_frames
        ):
            raise ValueError(
                "scheduled command at_frame values must be strictly increasing within the capture"
            )
        if not isinstance(kind, str) or kind not in SCENARIO_KINDS:
            raise ValueError("unsupported scheduled command kind: {}".format(kind))
        if not isinstance(payload, Mapping):
            raise ValueError("scheduled command payload must be an object")
        names.add(name)
        previous_frame = at_frame
        result.append(
            ScheduledCommandV2(
                name=name,
                at_frame=at_frame,
                kind=kind,
                payload=_copy_json(payload),
            )
        )
    return tuple(result)


def validate_scenarios_v2(values: Sequence[Mapping[str, Any]]) -> Tuple[ScenarioV2, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
        raise ValueError("scenarios must be a non-empty sequence")
    required = {"name", "kind", "payload", "timing"}
    result: List[ScenarioV2] = []
    names = set()
    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise ValueError("scenario {} must be an object".format(index))
        if set(value) != required:
            raise ValueError("scenario {} schema mismatch".format(index))
        name, kind, payload, timing = (
            value["name"],
            value["kind"],
            value["payload"],
            value["timing"],
        )
        if not isinstance(name, str) or not SCENARIO_NAME_RE.fullmatch(name):
            raise ValueError("scenario name must be a lowercase kebab-case identifier")
        if name in names:
            raise ValueError("scenario names must be unique")
        if not isinstance(kind, str) or kind not in SCENARIO_KINDS:
            raise ValueError("unsupported scenario command kind: {}".format(kind))
        if not isinstance(payload, Mapping):
            raise ValueError("scenario payload must be an object")
        if not isinstance(timing, Mapping):
            raise ValueError("scenario timing must be an object")
        supplied_timing = set(timing)
        if supplied_timing in (
            {"capture_frames"},
            {"capture_frames", "scheduled_commands"},
        ):
            capture_frames = _positive_integer(
                timing["capture_frames"], "timing.capture_frames"
            )
            scenario = ScenarioV2(
                name=name,
                kind=kind,
                payload=_copy_json(payload),
                capture_frames=capture_frames,
                scheduled_commands=(
                    _scheduled_commands_v2(
                        timing["scheduled_commands"],
                        capture_frames,
                    )
                    if "scheduled_commands" in timing
                    else ()
                ),
            )
        elif supplied_timing == {"until_trace", "max_frames"}:
            scenario = ScenarioV2(
                name=name,
                kind=kind,
                payload=_copy_json(payload),
                until_trace=_trace_trigger_v2(timing["until_trace"]),
                max_frames=_positive_integer(timing["max_frames"], "timing.max_frames"),
            )
        else:
            raise ValueError(
                "scenario timing requires capture_frames or until_trace plus max_frames"
            )
        names.add(name)
        result.append(scenario)
    if sum(item.planned_frame_count(24.0) for item in result) > int(
        SCENARIO_PROGRAM_MAX_SECONDS * 24
    ):
        raise ValueError("scenario program exceeds the frame budget")
    return tuple(result)


DEFAULT_SCENARIOS = validate_scenarios(
    [
        {
            "name": "front-idle",
            "kind": "reset",
            "payload": {},
            "settle_seconds": 0.25,
            "capture_seconds": 0.75,
        },
        {
            "name": "gaze-left",
            "kind": "gaze",
            "payload": {"target": "left"},
            "settle_seconds": 0.15,
            "capture_seconds": 0.65,
        },
        {
            "name": "gaze-right",
            "kind": "gaze",
            "payload": {"target": "right"},
            "settle_seconds": 0.15,
            "capture_seconds": 0.65,
        },
        {
            "name": "happy-expression",
            "kind": "expression",
            "payload": {"expression": "happy"},
            "settle_seconds": 0.15,
            "capture_seconds": 0.75,
        },
        {
            "name": "thinking-expression",
            "kind": "expression",
            "payload": {"expression": "thinking"},
            "settle_seconds": 0.15,
            "capture_seconds": 0.75,
        },
        {
            "name": "walk-left",
            "kind": "move",
            "payload": {"x": -1.5, "z": 5.0, "speed": 1.0},
            "settle_seconds": 0.0,
            "capture_seconds": 1.4,
        },
        {
            "name": "walk-reversal",
            "kind": "move",
            "payload": {"x": 1.5, "z": 5.0, "speed": 1.0},
            "settle_seconds": 0.0,
            "capture_seconds": 2.0,
        },
        {
            "name": "walk-stop",
            "kind": "stop",
            "payload": {},
            "settle_seconds": 0.1,
            "capture_seconds": 0.75,
        },
        {
            "name": "face-back",
            "kind": "face",
            "payload": {"direction": "north"},
            "settle_seconds": 0.1,
            "capture_seconds": 0.65,
        },
        {
            "name": "face-front",
            "kind": "face",
            "payload": {"direction": "south"},
            "settle_seconds": 0.1,
            "capture_seconds": 0.65,
        },
        {
            "name": "magic-cast",
            "kind": "action",
            "payload": {"action": "magic_cast", "duration_ms": 1400},
            "settle_seconds": 0.0,
            "capture_seconds": 1.4,
        },
        {
            "name": "speaking",
            "kind": "speak",
            "payload": {
                "speech_id": "character-director-visual-review",
                "text": "Deterministic visual review line.",
                "duration_ms": 1600,
            },
            "settle_seconds": 0.0,
            "capture_seconds": 1.4,
        },
        {
            "name": "speech-interruption",
            "kind": "speech_stop",
            "payload": {"speech_id": "character-director-visual-review"},
            "settle_seconds": 0.15,
            "capture_seconds": 0.75,
        },
    ]
)


@dataclass
class CaptureIntegrity:
    failure_reason: Optional[str] = None
    decoded_gaps: List[Dict[str, int]] = field(default_factory=list)
    decoder_errors: List[Dict[str, str]] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.failure_reason is None

    def invalidate(self, reason: str) -> None:
        if self.failure_reason is None:
            self.failure_reason = reason

    def record_decoder_error(self, exc: BaseException) -> None:
        self.decoder_errors.append({"type": type(exc).__name__, "message": str(exc)})
        self.invalidate("adaptive frame decoder error: {}".format(exc))


@dataclass
class QueueStats:
    capacity: int
    high_water_mark: int = 0
    overrun_count: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.capacity, bool) or not isinstance(self.capacity, int) or self.capacity <= 0:
            raise ValueError("queue capacity must be a positive integer")

    def to_mapping(self) -> Dict[str, int]:
        return asdict(self)


def enqueue_decoded_frame(
    queue: "asyncio.Queue[DecodedFrame]",
    frame: "DecodedFrame",
    stats: QueueStats,
    integrity: CaptureIntegrity,
) -> None:
    try:
        queue.put_nowait(frame)
    except asyncio.QueueFull as exc:
        stats.overrun_count += 1
        integrity.invalidate("decoded frame queue overflow")
        raise QueueOverflowError("decoded frame queue overflow") from exc
    stats.high_water_mark = max(stats.high_water_mark, queue.qsize())


class StrictFrameDecoder:
    def __init__(self, expected_length: int, integrity: CaptureIntegrity) -> None:
        if isinstance(expected_length, bool) or not isinstance(expected_length, int) or expected_length <= 0:
            raise ValueError("expected decoded length must be a positive integer")
        self.expected_length = expected_length
        self.integrity = integrity
        self.previous_frame: Optional[bytes] = None
        self.previous_frame_index: Optional[int] = None

    def decode(self, message: bytes) -> Tuple[int, bytes]:
        try:
            frame_index, decoded = decode_frame(message, self.previous_frame)
        except Exception as exc:
            self.integrity.record_decoder_error(exc)
            raise FrameDecodeError(str(exc)) from exc

        if len(decoded) != self.expected_length:
            exc = ValueError(
                "decoded length {} does not equal expected {}".format(len(decoded), self.expected_length)
            )
            self.integrity.record_decoder_error(exc)
            raise FrameDecodeError(str(exc))

        if self.previous_frame_index is not None and frame_index != self.previous_frame_index + 1:
            gap = {
                "previous_frame_index": self.previous_frame_index,
                "expected_frame_index": self.previous_frame_index + 1,
                "actual_frame_index": frame_index,
            }
            self.integrity.decoded_gaps.append(gap)
            self.integrity.invalidate(
                "frame index gap: expected {}, received {}".format(
                    gap["expected_frame_index"], gap["actual_frame_index"]
                )
            )
            raise FrameGapError(self.integrity.failure_reason)

        self.previous_frame = decoded
        self.previous_frame_index = frame_index
        return frame_index, decoded


@dataclass(frozen=True)
class DecodedFrame:
    frame_index: int
    cells: bytes
    received_monotonic: float
    received_at_utc: str
    scenario: Optional[str]
    wire_message: bytes
    codec_tag: int


@dataclass
class CaptureRecords:
    frames: List[Dict[str, Any]] = field(default_factory=list)
    commands: List[Dict[str, Any]] = field(default_factory=list)
    state_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    samples: List[Dict[str, Any]] = field(default_factory=list)
    sample_paths: List[Path] = field(default_factory=list)
    animation_truth_trace: List[Dict[str, Any]] = field(default_factory=list)
    contact_verification: Optional[Dict[str, Any]] = None
    decoded_raster_frames: Dict[int, DecodedRasterFrameV1] = field(default_factory=dict)


@dataclass
class ScenarioClock:
    """Assign an exact number of subsequently published frames to one scenario."""

    current: Optional[str] = None
    remaining_frames: int = 0
    claimed_frames: int = 0
    completed: asyncio.Event = field(default_factory=asyncio.Event)

    def activate(self, scenario: str, frame_count: int) -> None:
        if self.current is not None or self.remaining_frames:
            raise EvidenceFailure("a scenario capture window is already active")
        if not scenario or frame_count <= 0:
            raise ValueError("scenario capture windows require a name and positive frame count")
        self.current = scenario
        self.remaining_frames = frame_count
        self.claimed_frames = 0
        self.completed = asyncio.Event()

    def claim(self) -> Optional[str]:
        scenario = self.current
        if scenario is None:
            return None
        self.remaining_frames -= 1
        self.claimed_frames += 1
        if self.remaining_frames == 0:
            self.current = None
            self.completed.set()
        return scenario

    def finish(self, scenario: str) -> None:
        if self.current != scenario:
            raise EvidenceFailure(
                "cannot finish inactive scenario capture window: {}".format(scenario)
            )
        self.current = None
        self.remaining_frames = 0
        self.completed.set()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_git_provenance(root: Path = ROOT) -> Dict[str, Any]:
    def run(*args: str) -> bytes:
        completed = subprocess.run(
            ("git", *args),
            cwd=str(root),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return completed.stdout

    try:
        head = run("rev-parse", "HEAD").decode("ascii").strip()
        head_tree = run("rev-parse", "{}^{{tree}}".format(head)).decode("ascii").strip()
        branch = run("branch", "--show-current").decode("utf-8").strip()
        status = run("status", "--porcelain=v1", "--untracked-files=all")
        tracked_diff = run("diff", "--binary", "HEAD")
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        raise EvidenceFailure("cannot establish Git provenance: {}".format(exc)) from exc
    if not GIT_OBJECT_RE.fullmatch(head):
        raise EvidenceFailure("Git HEAD is not a full SHA-1/SHA-256 object ID")
    if not GIT_OBJECT_RE.fullmatch(head_tree):
        raise EvidenceFailure("Git HEAD tree is not a full SHA-1/SHA-256 object ID")
    return {
        "head": head,
        "head_tree": head_tree,
        "branch": branch,
        "worktree_clean": not status,
        "status_sha256": hashlib.sha256(status).hexdigest(),
        "tracked_diff_sha256": hashlib.sha256(tracked_diff).hexdigest(),
        "status_lines": status.decode("utf-8", errors="replace").splitlines(),
    }


def request_json(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    extra_headers: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise EvidenceFailure("{} {} failed: HTTP {} {}".format(method, url, exc.code, detail)) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise EvidenceFailure("{} {} failed: {}".format(method, url, exc)) from exc
    if not isinstance(body, dict):
        raise EvidenceFailure("{} {} returned non-object JSON".format(method, url))
    return body


async def request_json_async(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    extra_headers: Optional[Mapping[str, str]] = None,
) -> Tuple[Dict[str, Any], float]:
    started = time.perf_counter()
    result = await asyncio.to_thread(
        request_json,
        method,
        url,
        payload,
        extra_headers,
    )
    return result, (time.perf_counter() - started) * 1000.0


def canonical_runtime_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("--base-url must be an absolute http(s) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("--base-url must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("--base-url must not contain a query or fragment")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("--base-url contains an invalid port") from exc
    if parsed.hostname is None:
        raise ValueError("--base-url must contain a hostname")
    if port == PROTECTED_LEGACY_PORT:
        raise ValueError("the visual-review harness must never contact protected port 8765")
    base_path = parsed.path.rstrip("/")
    host = "[{}]".format(parsed.hostname) if ":" in parsed.hostname else parsed.hostname
    authority = "{}:{}".format(host, port) if port is not None else host
    return urllib.parse.urlunsplit((parsed.scheme.lower(), authority, base_path, "", ""))


def runtime_urls(base_url: str) -> Tuple[str, str, str, str, str]:
    http_base = canonical_runtime_base_url(base_url)
    parsed = urllib.parse.urlsplit(http_base)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = urllib.parse.urlunsplit(
        (ws_scheme, parsed.netloc, parsed.path + "/ws/avatar/wizard", "codec=adaptive", "")
    )
    return (
        ws_url,
        http_base + "/api/avatar/wizard/command",
        http_base + "/api/avatar/wizard/state",
        http_base + "/api/avatar/wizard/animation-trace",
        http_base + "/api/avatar/wizard/runtime-identity",
    )


def media_session_url(base_url: str) -> str:
    return canonical_runtime_base_url(base_url) + "/api/avatar/wizard/media-session"


def validate_runtime_binding(
    start: Mapping[str, Any],
    end: Mapping[str, Any],
    provenance: Mapping[str, Any],
    base_url: str,
    init: Optional[InitMetadata] = None,
    evidence_output_dir: Optional[Path] = None,
) -> None:
    """Require one stable clean runtime built from the harness candidate."""

    immutable_start = dict(start)
    immutable_end = dict(end)
    immutable_start.pop("git", None)
    immutable_end.pop("git", None)
    if immutable_start != immutable_end:
        raise EvidenceFailure("runtime identity changed during capture")
    if start.get("schema") != "wizard_runtime_identity_v1" or start.get("schema_version") != 1:
        raise EvidenceFailure("runtime returned an unsupported identity schema")
    runtime_epoch = start.get("runtime_epoch")
    if not isinstance(runtime_epoch, str) or not runtime_epoch:
        raise EvidenceFailure("runtime identity is missing its process epoch")
    if not _plain_int(start.get("pid"), 1):
        raise EvidenceFailure("runtime identity is missing its process ID")
    if not isinstance(start.get("started_at_utc"), str) or not _plain_int(
        start.get("started_at_monotonic_ns"), 1
    ):
        raise EvidenceFailure("runtime identity is missing fixed startup timing")
    if start.get("repository_root") != str(ROOT.resolve()):
        raise EvidenceFailure("runtime repository root does not match the evidence checkout")
    if start.get("working_directory") != str(ROOT.resolve()):
        raise EvidenceFailure("runtime working directory does not match the evidence checkout")
    git = start.get("git")
    end_git = end.get("git")
    if not isinstance(git, Mapping) or git.get("available") is not True:
        raise EvidenceFailure("runtime cannot establish its Git identity")
    if not isinstance(end_git, Mapping) or end_git.get("available") is not True:
        raise EvidenceFailure("runtime lost its Git identity during capture")
    if git.get("head") != provenance.get("head"):
        raise EvidenceFailure("runtime Git HEAD does not match the evidence checkout")
    if git.get("branch") != provenance.get("branch"):
        raise EvidenceFailure("runtime Git branch does not match the evidence checkout")
    if git.get("worktree_clean") is not True or provenance.get("worktree_clean") is not True:
        raise EvidenceFailure("runtime and evidence checkout must both start clean")
    if git.get("head_tree") != provenance.get("head_tree"):
        raise EvidenceFailure("runtime Git tree does not match the evidence checkout HEAD")
    for field in ("status_sha256", "tracked_diff_sha256"):
        if git.get(field) != provenance.get(field):
            raise EvidenceFailure("runtime Git {} does not match the evidence checkout".format(field))
    for field in ("head", "head_tree", "branch", "tracked_diff_sha256"):
        if end_git.get(field) != git.get(field):
            raise EvidenceFailure("runtime Git {} changed during capture".format(field))
    if end_git.get("worktree_clean") is True:
        if end_git.get("status_sha256") != git.get("status_sha256"):
            raise EvidenceFailure("runtime Git status changed during capture")
    else:
        if evidence_output_dir is None:
            raise EvidenceFailure("runtime worktree became dirty during capture")
        try:
            allowed_root = evidence_output_dir.resolve().relative_to(ROOT.resolve())
        except ValueError as exc:
            raise EvidenceFailure(
                "runtime worktree dirtiness is outside the evidence checkout"
            ) from exc
        allowed_text = allowed_root.as_posix().rstrip("/")
        status_lines = end_git.get("status_lines")
        if not isinstance(status_lines, list) or not status_lines:
            raise EvidenceFailure("runtime dirty status is missing its path evidence")
        for line in status_lines:
            if not isinstance(line, str) or not line.startswith("?? "):
                raise EvidenceFailure("runtime tracked source changed during capture")
            path = line[3:].rstrip("/")
            if path != allowed_text and not path.startswith(allowed_text + "/"):
                raise EvidenceFailure(
                    "runtime worktree changed outside the evidence output directory"
                )
    python = start.get("python")
    launch = start.get("launch")
    if not isinstance(python, Mapping) or not SHA256_RE.fullmatch(
        str(python.get("executable_sha256", ""))
    ):
        raise EvidenceFailure("runtime Python executable is not content-addressed")
    expected_python = Path(sys.executable).resolve()
    if python.get("executable") != str(expected_python):
        raise EvidenceFailure("runtime Python executable does not match the evidence harness")
    if python.get("executable_sha256") != sha256_file(expected_python):
        raise EvidenceFailure("runtime Python executable hash does not match the evidence harness")
    if not isinstance(launch, Mapping) or not SHA256_RE.fullmatch(
        str(launch.get("argv_sha256", ""))
    ):
        raise EvidenceFailure("runtime launch command is not content-addressed")
    argv = launch.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
        raise EvidenceFailure("runtime launch argv is missing or malformed")
    argv_sha256 = hashlib.sha256("\0".join(argv).encode("utf-8")).hexdigest()
    if launch.get("argv_sha256") != argv_sha256:
        raise EvidenceFailure("runtime launch argv hash does not match its command")
    expected_launcher = (ROOT / "tools" / "run_wizard_avatar_server.py").resolve()
    if launch.get("launcher") != str(expected_launcher):
        raise EvidenceFailure("runtime was not launched by the canonical server entry point")
    if launch.get("launcher_sha256") != sha256_file(expected_launcher):
        raise EvidenceFailure("runtime launcher hash does not match the evidence checkout")
    server = start.get("server")
    parsed = urllib.parse.urlsplit(base_url)
    if not isinstance(server, Mapping) or server.get("port") != parsed.port:
        raise EvidenceFailure("runtime server port does not match the capture endpoint")
    if server.get("host") != parsed.hostname:
        raise EvidenceFailure("runtime server host does not match the capture endpoint")
    if server.get("companion_mode") is not False:
        raise EvidenceFailure("visual evidence runtime must use isolated non-companion mode")
    if init is not None:
        render = start.get("render")
        expected = {
            "cols": init.cols,
            "rows": init.rows,
            "fps": init.fps,
            "cell_bytes": init.cell_bytes,
        }
        if not isinstance(render, Mapping) or dict(render) != expected:
            raise EvidenceFailure("runtime render configuration does not match ASCILINE INIT")


def select_atomic_animation_trace(
    payload: Mapping[str, Any],
    frames: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Select and verify the exact accepted trace record for every wire frame."""

    if payload.get("schema") != "animation_truth_trace_v1":
        raise EvidenceFailure("runtime returned an unsupported animation trace schema")
    records = payload.get("records")
    if not isinstance(records, list):
        raise EvidenceFailure("runtime animation trace records must be an array")
    by_index: Dict[int, Mapping[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise EvidenceFailure("runtime animation trace record must be an object")
        frame_index = record.get("frame_index")
        if not isinstance(frame_index, int) or isinstance(frame_index, bool):
            raise EvidenceFailure("runtime animation trace frame_index must be an integer")
        if frame_index in by_index:
            raise EvidenceFailure("runtime animation trace contains duplicate frame indexes")
        by_index[frame_index] = record

    selected: List[Dict[str, Any]] = []
    for frame in frames:
        frame_index = frame["frame_index"]
        record = by_index.get(frame_index)
        if record is None:
            raise EvidenceFailure(
                "runtime animation trace is missing captured frame {}".format(frame_index)
            )
        if record.get("frame_sha256") != frame.get("sha256"):
            raise EvidenceFailure(
                "runtime animation trace hash mismatch for frame {}".format(frame_index)
            )
        if record.get("codec_tag") != frame.get("codec_tag"):
            raise EvidenceFailure(
                "runtime animation trace codec mismatch for frame {}".format(frame_index)
            )
        selected.append(dict(record))
    return selected


def select_capture_owned_contact_records(
    records: Sequence[AnimationTruthTraceV1],
    frames: Sequence[Mapping[str, Any]],
) -> Tuple[AnimationTruthTraceV1, ...]:
    """Keep transport warmup rows replayable without treating them as proof."""

    if len(records) != len(frames):
        raise EvidenceFailure("contact record and frame counts differ")
    ownership_declared = any("capture_owned" in frame for frame in frames)
    selected = []
    for record, frame in zip(records, frames):
        if record.frame_index != frame.get("frame_index"):
            raise EvidenceFailure("contact record and frame indexes differ")
        if not ownership_declared or frame.get("capture_owned") is True:
            selected.append(record)
    return tuple(selected)


def square_cell_image(cells: bytes, cols: int, rows: int, cell_size: int):
    from PIL import Image

    expected = cols * rows * CELL_BYTES
    if len(cells) != expected:
        raise ValueError("cannot render {} bytes as {}x{} cells".format(len(cells), cols, rows))
    # Pillow's raw XRGB decoder discards the protocol glyph byte and copies
    # RGB in native code. A Python per-cell loop cannot keep up with 24 FPS.
    image = Image.frombytes("RGB", (cols, rows), cells, "raw", "XRGB")
    return image.resize((cols * cell_size, rows * cell_size), resample=Image.Resampling.NEAREST)


class FFmpegSink:
    def __init__(self, executable: Optional[str], output_path: Path, width: int, height: int, fps: float) -> None:
        self.executable = executable
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.process: Optional[asyncio.subprocess.Process] = None
        self.succeeded = False
        self.error: Optional[str] = None
        self.frame_count = 0

    @property
    def available(self) -> bool:
        return self.executable is not None

    async def start(self) -> None:
        if not self.executable:
            return
        self.process = await asyncio.create_subprocess_exec(
            self.executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            "{}x{}".format(self.width, self.height),
            "-framerate",
            "{:.6f}".format(self.fps),
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-y",
            str(self.output_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

    async def write(self, rgb: bytes) -> None:
        if not self.process or not self.process.stdin:
            return
        self.process.stdin.write(rgb)
        await self.process.stdin.drain()
        self.frame_count += 1

    async def close(self) -> None:
        if not self.process:
            return
        if self.process.stdin:
            self.process.stdin.close()
            try:
                await self.process.stdin.wait_closed()
            except (BrokenPipeError, ConnectionResetError):
                pass
        stderr = await self.process.stderr.read() if self.process.stderr else b""
        return_code = await self.process.wait()
        if return_code:
            self.error = stderr.decode("utf-8", errors="replace").strip() or "ffmpeg exited {}".format(return_code)
            raise EvidenceFailure("ffmpeg H.264 encoding failed: {}".format(self.error))
        self.succeeded = self.output_path.is_file() and self.output_path.stat().st_size > 0
        if not self.succeeded:
            self.error = "ffmpeg produced no MP4 artifact"
            raise EvidenceFailure(self.error)


async def receive_frames(
    socket: Any,
    decoder: StrictFrameDecoder,
    queue: "asyncio.Queue[DecodedFrame]",
    queue_stats: QueueStats,
    integrity: CaptureIntegrity,
    terminal: asyncio.Event,
    producer_done: asyncio.Event,
    closing: asyncio.Event,
    scenario_clock: ScenarioClock,
) -> None:
    try:
        while True:
            try:
                message = await socket.recv()
            except Exception as exc:
                if not closing.is_set():
                    integrity.invalidate("WebSocket receive failed: {}".format(exc))
                    terminal.set()
                return
            if not isinstance(message, bytes):
                integrity.invalidate("unexpected text message after INIT")
                terminal.set()
                return
            try:
                frame_index, cells = decoder.decode(message)
                frame = DecodedFrame(
                    frame_index=frame_index,
                    cells=cells,
                    received_monotonic=time.perf_counter(),
                    received_at_utc=utc_now(),
                    scenario=scenario_clock.claim(),
                    wire_message=bytes(message),
                    codec_tag=message[4],
                )
                enqueue_decoded_frame(queue, frame, queue_stats, integrity)
            except EvidenceFailure:
                terminal.set()
                return
    finally:
        producer_done.set()


async def write_frames(
    queue: "asyncio.Queue[DecodedFrame]",
    producer_done: asyncio.Event,
    terminal: asyncio.Event,
    integrity: CaptureIntegrity,
    records: CaptureRecords,
    init: InitMetadata,
    sink: FFmpegSink,
    output_dir: Path,
    run_id: str,
    capture_started: float,
    cell_size: int,
    sample_every_frames: int,
) -> None:
    sampled_scenarios = set()
    processed = 0
    wire_path = output_dir / "wire" / "frames.bin"
    wire_path.parent.mkdir(parents=True, exist_ok=True)
    wire_offset = 0
    try:
        with wire_path.open("wb") as wire_file:
            while not producer_done.is_set() or not queue.empty():
                try:
                    frame = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                digest = hashlib.sha256(frame.cells).hexdigest()
                wire_digest = hashlib.sha256(frame.wire_message).hexdigest()
                wire_size = len(frame.wire_message)
                wire_file.write(frame.wire_message)
                capture_owned = frame.scenario is not None
                records.frames.append(
                    {
                        "frame_index": frame.frame_index,
                        "sha256": digest,
                        "wire_sha256": wire_digest,
                        "wire_offset": wire_offset,
                        "wire_size": wire_size,
                        "codec_tag": frame.codec_tag,
                        "scenario": frame.scenario,
                        "capture_owned": capture_owned,
                        "presentation_frame_index": processed if capture_owned else None,
                        "received_at_utc": frame.received_at_utc,
                        "elapsed_seconds": round(frame.received_monotonic - capture_started, 6),
                    }
                )
                records.decoded_raster_frames[frame.frame_index] = DecodedRasterFrameV1(
                    cols=init.cols,
                    rows=init.rows,
                    cells=frame.cells,
                )
                wire_offset += wire_size
                if capture_owned:
                    image = await asyncio.to_thread(
                        square_cell_image, frame.cells, init.cols, init.rows, cell_size
                    )
                    await sink.write(image.tobytes())
                    should_sample = (
                        frame.scenario not in sampled_scenarios
                        or processed % sample_every_frames == 0
                    )
                else:
                    should_sample = False
                if should_sample:
                    sample_name = "{}-{:04d}-{}-frame-{}.png".format(
                        run_id, len(records.samples) + 1, frame.scenario, frame.frame_index
                    )
                    sample_path = output_dir / "samples" / sample_name
                    sample_path.parent.mkdir(parents=True, exist_ok=True)
                    await asyncio.to_thread(image.save, sample_path, "PNG")
                    records.sample_paths.append(sample_path)
                    records.samples.append(
                        {
                            "path": sample_path.relative_to(output_dir).as_posix(),
                            "frame_index": frame.frame_index,
                            "scenario": frame.scenario,
                            "presentation_frame_index": processed,
                            "frame_sha256": digest,
                            "sample_reason": (
                                "scenario_start"
                                if frame.scenario not in sampled_scenarios
                                else "cadence"
                            ),
                        }
                    )
                    sampled_scenarios.add(frame.scenario)
                if capture_owned:
                    processed += 1
                queue.task_done()
    except Exception as exc:
        integrity.invalidate("frame writer failed: {}".format(exc))
        terminal.set()


async def wait_or_terminal(seconds: float, terminal: asyncio.Event, integrity: CaptureIntegrity) -> None:
    if seconds <= 0:
        return
    try:
        await asyncio.wait_for(terminal.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        return
    raise EvidenceFailure(integrity.failure_reason or "capture terminated")


async def wait_for_scenario_frames(
    scenario_clock: ScenarioClock,
    terminal: asyncio.Event,
    integrity: CaptureIntegrity,
    timeout_seconds: float,
) -> None:
    completion = asyncio.create_task(scenario_clock.completed.wait())
    terminated = asyncio.create_task(terminal.wait())
    try:
        done, _ = await asyncio.wait(
            (completion, terminated),
            timeout=timeout_seconds,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if completion in done and completion.result():
            return
        if terminated in done and terminated.result():
            raise EvidenceFailure(integrity.failure_reason or "capture terminated")
        raise EvidenceFailure("scenario capture window timed out before receiving its frame budget")
    finally:
        completion.cancel()
        terminated.cancel()
        await asyncio.gather(completion, terminated, return_exceptions=True)


def _matching_trigger_record(
    payload: Mapping[str, Any],
    records: CaptureRecords,
    scenario: str,
    trigger: TraceTriggerV2,
) -> Optional[Dict[str, Any]]:
    if payload.get("schema") != "animation_truth_trace_v1":
        raise EvidenceFailure("runtime returned an unsupported animation trace schema")
    trace_records = payload.get("records")
    if not isinstance(trace_records, list):
        raise EvidenceFailure("runtime animation trace records must be an array")
    owned_indexes = {
        frame.get("frame_index")
        for frame in records.frames
        if frame.get("capture_owned") is True and frame.get("scenario") == scenario
    }
    matches = [
        trace
        for trace in trace_records
        if isinstance(trace, Mapping)
        and trace.get("frame_index") in owned_indexes
        and trigger.matches(trace)
    ]
    if not matches:
        return None
    return dict(min(matches, key=lambda item: int(item["frame_index"])))


async def wait_for_trace_trigger(
    scenario: ScenarioV2,
    animation_trace_url: str,
    scenario_clock: ScenarioClock,
    records: CaptureRecords,
    terminal: asyncio.Event,
    integrity: CaptureIntegrity,
    fps: float,
) -> Dict[str, Any]:
    if scenario.until_trace is None or scenario.max_frames is None:
        raise ValueError("trace-triggered scenarios require a trigger and frame bound")
    deadline = time.monotonic() + max(5.0, scenario.max_frames / fps * 3.0)
    while time.monotonic() < deadline:
        if terminal.is_set():
            raise EvidenceFailure(integrity.failure_reason or "capture terminated")
        payload, _ = await request_json_async("GET", animation_trace_url)
        matched = _matching_trigger_record(
            payload,
            records,
            scenario.name,
            scenario.until_trace,
        )
        if matched is not None:
            if scenario_clock.current == scenario.name:
                scenario_clock.finish(scenario.name)
            return {
                "frame_index": matched.get("frame_index"),
                "simulation_tick": matched.get("simulation_tick"),
                "state_revision": matched.get("state_revision"),
                "animation_clip_id": matched.get("animation_clip_id"),
                "animation_authored_frame": matched.get("animation_authored_frame"),
                "marker_id": scenario.until_trace.marker_id,
            }
        if scenario_clock.completed.is_set():
            break
        await asyncio.sleep(min(0.05, 1.0 / fps))
    raise EvidenceFailure(
        "scenario {} reached its {}-frame bound without trace trigger {}".format(
            scenario.name,
            scenario.max_frames,
            scenario.until_trace.to_mapping(),
        )
    )


async def record_state_snapshot(
    state_url: str,
    label: str,
    records: CaptureRecords,
) -> Dict[str, Any]:
    observed_at = utc_now()
    body, latency_ms = await request_json_async("GET", state_url)
    snapshot = {
        "label": label,
        "observed_at_utc": observed_at,
        "request_latency_ms": round(latency_ms, 3),
        "body": minimize_evidence_content(body),
    }
    records.state_snapshots.append(snapshot)
    return snapshot


async def dispatch_runtime_operation(
    *,
    kind: str,
    payload: Dict[str, Any],
    envelope: Dict[str, Any],
    command_url: str,
    media_url: str,
    media_token: Optional[str],
) -> Tuple[Dict[str, Any], Dict[str, Any], Any, float, str]:
    if kind == MEDIA_SESSION_SCENARIO_KIND:
        if not media_token:
            raise EvidenceFailure(
                "media-session scenarios require WIZARD_MEDIA_CONNECTOR_TOKEN"
            )
        response, latency_ms = await request_json_async(
            "POST",
            media_url,
            payload,
            {"Authorization": "Bearer " + media_token},
        )
        ack = response
        if ack.get("disposition") != "accepted":
            raise EvidenceFailure(
                "media-session snapshot was not accepted: {}".format(
                    ack.get("disposition")
                )
            )
        return response, ack, minimize_evidence_content(response), latency_ms, "media_session"

    response, latency_ms = await request_json_async(
        "POST",
        command_url,
        envelope,
    )
    ack = response.get("ack")
    if not isinstance(ack, dict):
        raise EvidenceFailure(
            "command {} returned no acknowledgement".format(
                envelope["command_id"]
            )
        )
    if ack.get("command_id") != envelope["command_id"]:
        raise EvidenceFailure("command acknowledgement ID mismatch")
    if ack.get("source_sequence") != envelope["source_sequence"]:
        raise EvidenceFailure("command acknowledgement sequence mismatch")
    if ack.get("disposition") != "applied":
        raise EvidenceFailure(
            "command {} was not applied: {}".format(
                envelope["command_id"],
                ack.get("disposition"),
            )
        )
    return (
        response,
        ack,
        minimize_evidence_content(response.get("state")),
        latency_ms,
        "command",
    )


async def dispatch_scheduled_commands(
    scenario: ScenarioV2,
    command_url: str,
    media_url: str,
    media_token: Optional[str],
    source_epoch: str,
    first_source_sequence: int,
    scenario_clock: ScenarioClock,
    records: CaptureRecords,
    terminal: asyncio.Event,
    integrity: CaptureIntegrity,
    fps: float,
) -> None:
    for offset, command in enumerate(scenario.scheduled_commands):
        while (
            not terminal.is_set()
            and scenario_clock.current == scenario.name
            and scenario_clock.claimed_frames < command.at_frame
        ):
            await asyncio.sleep(min(0.01, 1.0 / fps / 4.0))
        if terminal.is_set():
            raise EvidenceFailure(integrity.failure_reason or "capture terminated")
        if (
            scenario_clock.current != scenario.name
            or scenario_clock.claimed_frames < command.at_frame
        ):
            raise EvidenceFailure(
                "scheduled command {} missed frame boundary {}".format(
                    command.name,
                    command.at_frame,
                )
            )

        source_sequence = first_source_sequence + offset
        command_id = "{}-{:04d}-{}".format(
            source_epoch,
            source_sequence,
            command.name,
        )
        envelope = {
            "schema_version": 1,
            "command_id": command_id,
            "source_id": SOURCE_ID,
            "source_kind": "api",
            "source_sequence": source_sequence,
            "source_epoch": source_epoch,
            "kind": command.kind,
            "payload": command.payload,
            "priority_class": "user",
        }
        outcome: Dict[str, Any] = {
            "scenario": command.name,
            "scheduled_for_scenario": scenario.name,
            "scheduled_at_frame": command.at_frame,
            "dispatch_observed_after_frame_count": scenario_clock.claimed_frames,
            "command_id": command_id,
            "source_id": SOURCE_ID,
            "source_epoch": source_epoch,
            "source_sequence": source_sequence,
            "kind": command.kind,
            "transport": (
                "media_session"
                if command.kind == MEDIA_SESSION_SCENARIO_KIND
                else "command"
            ),
            "payload": command.payload,
            "request_started_at_utc": utc_now(),
            "ack": None,
            "response_state": None,
            "error": None,
        }
        records.commands.append(outcome)
        scheduled_task: Optional[asyncio.Task[None]] = None
        try:
            (
                _response,
                ack,
                response_state,
                latency_ms,
                transport,
            ) = await dispatch_runtime_operation(
                kind=command.kind,
                payload=command.payload,
                envelope=envelope,
                command_url=command_url,
                media_url=media_url,
                media_token=media_token,
            )
            outcome["request_completed_at_utc"] = utc_now()
            outcome["request_latency_ms"] = round(latency_ms, 3)
            outcome["dispatch_completed_after_frame_count"] = scenario_clock.claimed_frames
            outcome["transport"] = transport
            outcome["ack"] = ack
            outcome["response_state"] = response_state
        except Exception as exc:
            outcome["error"] = "{}: {}".format(type(exc).__name__, exc)
            integrity.invalidate(
                "scheduled command {} failed: {}".format(command.name, exc)
            )
            terminal.set()
            raise


async def drive_scenarios(
    scenarios: Sequence[Any],
    command_url: str,
    media_url: str,
    media_token: Optional[str],
    state_url: str,
    animation_trace_url: str,
    source_epoch: str,
    scenario_clock: ScenarioClock,
    records: CaptureRecords,
    terminal: asyncio.Event,
    integrity: CaptureIntegrity,
    fps: float,
) -> None:
    next_source_sequence = 1
    for scenario in scenarios:
        if terminal.is_set():
            raise EvidenceFailure(integrity.failure_reason or "capture terminated")
        source_sequence = next_source_sequence
        scheduled_commands = (
            scenario.scheduled_commands
            if isinstance(scenario, ScenarioV2)
            else ()
        )
        next_source_sequence += 1 + len(scheduled_commands)
        command_id = "{}-{:04d}-{}".format(source_epoch, source_sequence, scenario.name)
        planned_frames = (
            scenario.planned_frame_count(fps)
            if isinstance(scenario, ScenarioV2)
            else max(1, int(round(scenario.capture_seconds * fps)))
        )
        envelope = {
            "schema_version": 1,
            "command_id": command_id,
            "source_id": SOURCE_ID,
            "source_kind": "api",
            "source_sequence": source_sequence,
            "source_epoch": source_epoch,
            "kind": scenario.kind,
            "payload": scenario.payload,
            "priority_class": "user",
        }
        outcome: Dict[str, Any] = {
            "scenario": scenario.name,
            "command_id": command_id,
            "source_id": SOURCE_ID,
            "source_epoch": source_epoch,
            "source_sequence": source_sequence,
            "kind": scenario.kind,
            "transport": (
                "media_session"
                if scenario.kind == MEDIA_SESSION_SCENARIO_KIND
                else "command"
            ),
            "payload": scenario.payload,
            "capture_planned_frame_count": planned_frames,
            "capture_timing_mode": (
                "trace_trigger"
                if isinstance(scenario, ScenarioV2) and scenario.until_trace is not None
                else "fixed"
            ),
            "trace_trigger": (
                scenario.until_trace.to_mapping()
                if isinstance(scenario, ScenarioV2) and scenario.until_trace is not None
                else None
            ),
            "trace_trigger_observation": None,
            "request_started_at_utc": utc_now(),
            "ack": None,
            "response_state": None,
            "state_snapshot": None,
            "error": None,
        }
        records.commands.append(outcome)
        try:
            (
                _response,
                ack,
                response_state,
                latency_ms,
                transport,
            ) = await dispatch_runtime_operation(
                kind=scenario.kind,
                payload=scenario.payload,
                envelope=envelope,
                command_url=command_url,
                media_url=media_url,
                media_token=media_token,
            )
            outcome["request_completed_at_utc"] = utc_now()
            outcome["request_latency_ms"] = round(latency_ms, 3)
            outcome["transport"] = transport
            outcome["ack"] = ack
            outcome["response_state"] = response_state
            outcome["state_snapshot"] = await record_state_snapshot(
                state_url, "{}-after-ack".format(scenario.name), records
            )
            await wait_or_terminal(
                scenario.settle_seconds if isinstance(scenario, Scenario) else 0.0,
                terminal,
                integrity,
            )
            outcome["capture_started_at_utc"] = utc_now()
            scenario_clock.activate(scenario.name, planned_frames)
            scheduled_task = (
                asyncio.create_task(
                    dispatch_scheduled_commands(
                        scenario,
                        command_url,
                        media_url,
                        media_token,
                        source_epoch,
                        source_sequence + 1,
                        scenario_clock,
                        records,
                        terminal,
                        integrity,
                        fps,
                    )
                )
                if isinstance(scenario, ScenarioV2)
                and scenario.scheduled_commands
                else None
            )
            if isinstance(scenario, ScenarioV2) and scenario.until_trace is not None:
                outcome["trace_trigger_observation"] = await wait_for_trace_trigger(
                    scenario,
                    animation_trace_url,
                    scenario_clock,
                    records,
                    terminal,
                    integrity,
                    fps,
                )
            else:
                capture_seconds = (
                    scenario.capture_seconds
                    if isinstance(scenario, Scenario)
                    else planned_frames / fps
                )
                await wait_for_scenario_frames(
                    scenario_clock,
                    terminal,
                    integrity,
                    timeout_seconds=max(5.0, capture_seconds * 3.0),
                )
            if scheduled_task is not None:
                await scheduled_task
            outcome["capture_completed_at_utc"] = utc_now()
        except Exception as exc:
            if scheduled_task is not None:
                scheduled_task.cancel()
                await asyncio.gather(scheduled_task, return_exceptions=True)
            outcome["error"] = "{}: {}".format(type(exc).__name__, exc)
            integrity.invalidate("scenario {} failed: {}".format(scenario.name, exc))
            terminal.set()
            raise


def add_transition_samples(
    records: CaptureRecords,
    init: InitMetadata,
    output_dir: Path,
    run_id: str,
    cell_size: int,
) -> None:
    """Add exact event-boundary frames omitted by cadence-only sampling."""

    frame_by_index = {item["frame_index"]: item for item in records.frames}
    sampled_indexes = {item["frame_index"] for item in records.samples}
    previous_signature = None
    for trace in records.animation_truth_trace:
        frame_index = trace["frame_index"]
        frame = frame_by_index.get(frame_index)
        channels = trace.get("presentation_channels") or {}
        signature = (
            channels.get("rendered_head_pose_id"),
            channels.get("head_eye_phase"),
            channels.get("blink_closed"),
            channels.get("head_offset_x"),
            channels.get("head_offset_y"),
        )
        if frame is None or not frame.get("capture_owned"):
            previous_signature = signature
            continue
        if previous_signature is None or signature != previous_signature:
            if frame_index not in sampled_indexes:
                raster = records.decoded_raster_frames.get(frame_index)
                if raster is None:
                    raise EvidenceFailure(
                        "transition sample {} has no owned decoded frame".format(
                            frame_index
                        )
                    )
                sample_name = "{}-event-{:04d}-{}-frame-{}.png".format(
                    run_id,
                    len(records.samples) + 1,
                    frame.get("scenario"),
                    frame_index,
                )
                sample_path = output_dir / "samples" / sample_name
                image = square_cell_image(
                    raster.cells,
                    raster.cols,
                    raster.rows,
                    cell_size,
                )
                image.save(sample_path, "PNG")
                records.sample_paths.append(sample_path)
                records.samples.append(
                    {
                        "path": sample_path.relative_to(output_dir).as_posix(),
                        "frame_index": frame_index,
                        "scenario": frame.get("scenario"),
                        "presentation_frame_index": frame.get(
                            "presentation_frame_index"
                        ),
                        "frame_sha256": frame.get("sha256"),
                        "sample_reason": "presentation_transition",
                    }
                )
                sampled_indexes.add(frame_index)
        previous_signature = signature


def create_contact_sheet(
    samples: Sequence[Mapping[str, Any]],
    animation_truth_trace: Sequence[Mapping[str, Any]],
    commands: Sequence[Mapping[str, Any]],
    output_dir: Path,
    output_path: Path,
    fps: float,
) -> None:
    if not samples:
        raise EvidenceFailure("cannot create contact sheet without sampled PNGs")
    from PIL import Image, ImageDraw

    trace_by_index = {item.get("frame_index"): item for item in animation_truth_trace}
    command_by_scenario = {item.get("scenario"): item for item in commands}
    ordered_samples = sorted(samples, key=lambda item: item["frame_index"])
    columns = min(3, len(ordered_samples))
    thumb_width = 540
    label_height = 68
    loaded = []
    for sample in ordered_samples:
        path = output_dir / sample["path"]
        with Image.open(path) as source:
            image = source.convert("RGB")
            thumb_height = max(1, round(image.height * thumb_width / image.width))
            loaded.append(image.resize((thumb_width, thumb_height), Image.Resampling.NEAREST))
    thumb_height = max(image.height for image in loaded)
    rows = math.ceil(len(loaded) / columns)
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (sample, image) in enumerate(zip(ordered_samples, loaded)):
        x = (index % columns) * thumb_width
        y = (index // columns) * (thumb_height + label_height)
        sheet.paste(image, (x, y))
        trace = trace_by_index.get(sample["frame_index"], {})
        command = command_by_scenario.get(sample.get("scenario"), {})
        presentation_index = sample.get("presentation_frame_index")
        presentation_seconds = (
            float(presentation_index) / fps
            if isinstance(presentation_index, int) and fps > 0
            else 0.0
        )
        label = (
            "frame={} tick={} time={:.3f}s scenario={} reason={}\n"
            "command={}\n"
            "state_sha256={}\n"
            "frame_sha256={}"
        ).format(
            sample["frame_index"],
            trace.get("simulation_tick", "missing"),
            presentation_seconds,
            sample.get("scenario"),
            sample.get("sample_reason", "legacy"),
            command.get("command_id", "missing"),
            trace.get("authoritative_state_sha256", "missing"),
            sample.get("frame_sha256", "missing"),
        )
        draw.multiline_text(
            (x + 6, y + thumb_height + 4),
            label,
            fill=(20, 20, 20),
            spacing=1,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, "PNG")


def artifact_record(path: Path, output_dir: Path, media_type: str) -> Dict[str, Any]:
    return {
        "path": path.relative_to(output_dir).as_posix(),
        "media_type": media_type,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def build_review_bundle_manifest(
    capture_manifest_path: Path,
    output_dir: Path,
    review_artifacts: Sequence[Tuple[str, Path, str, Path]],
) -> Dict[str, Any]:
    capture_manifest_path = capture_manifest_path.resolve()
    output_dir = output_dir.resolve()
    capture_manifest = json.loads(capture_manifest_path.read_text(encoding="utf-8"))
    validate_manifest(capture_manifest, output_dir)
    records = []
    for role, path, media_type, source_path in review_artifacts:
        path = path.resolve()
        source_path = source_path.resolve()
        records.append(
            {
                "role": role,
                "path": path.relative_to(output_dir).as_posix(),
                "media_type": media_type,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "source_path": source_path.relative_to(output_dir).as_posix(),
                "source_sha256": sha256_file(source_path),
            }
        )
    manifest = {
        "schema": REVIEW_BUNDLE_SCHEMA,
        "schema_version": REVIEW_BUNDLE_VERSION,
        "run_id": capture_manifest.get("source_epoch"),
        "candidate_commit": capture_manifest.get("provenance", {}).get("head"),
        "complete": {item["role"] for item in records}
        == {"browser_layout", "machine_acceptance", "quarter_speed"},
        "capture_manifest": {
            "path": capture_manifest_path.relative_to(output_dir).as_posix(),
            "bytes": capture_manifest_path.stat().st_size,
            "sha256": sha256_file(capture_manifest_path),
        },
        "artifacts": records,
    }
    validate_review_bundle_manifest(manifest, output_dir)
    return manifest


def validate_review_bundle_manifest(
    manifest: Mapping[str, Any],
    output_dir: Path,
) -> None:
    expected_fields = {
        "schema",
        "schema_version",
        "run_id",
        "candidate_commit",
        "complete",
        "capture_manifest",
        "artifacts",
    }
    _manifest_error(
        isinstance(manifest, Mapping) and set(manifest) == expected_fields,
        "invalid review bundle manifest schema",
    )
    _manifest_error(
        manifest.get("schema") == REVIEW_BUNDLE_SCHEMA
        and manifest.get("schema_version") in SUPPORTED_REVIEW_BUNDLE_VERSIONS,
        "unsupported review bundle manifest",
    )
    _manifest_error(
        isinstance(manifest.get("run_id"), str) and manifest["run_id"],
        "review bundle run ID is missing",
    )
    _manifest_error(
        bool(GIT_OBJECT_RE.fullmatch(str(manifest.get("candidate_commit", "")))),
        "review bundle candidate commit is invalid",
    )
    _manifest_error(isinstance(manifest.get("complete"), bool), "review bundle complete must be boolean")

    root = output_dir.resolve()

    def validate_file_record(record: object, expected_fields: set, label: str) -> Path:
        _manifest_error(
            isinstance(record, Mapping) and set(record) == expected_fields,
            "invalid {} record".format(label),
        )
        relative = record.get("path")
        _manifest_error(
            isinstance(relative, str)
            and relative
            and not Path(relative).is_absolute()
            and ".." not in Path(relative).parts,
            "invalid {} path".format(label),
        )
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ManifestValidationError("{} resolves outside output directory".format(label)) from exc
        _manifest_error(candidate.is_file(), "missing {}: {}".format(label, relative))
        _manifest_error(_plain_int(record.get("bytes"), 1), "invalid {} byte count".format(label))
        _manifest_error(candidate.stat().st_size == record["bytes"], "{} byte count mismatch".format(label))
        _manifest_error(
            bool(SHA256_RE.fullmatch(str(record.get("sha256", ""))))
            and sha256_file(candidate) == record["sha256"],
            "{} SHA-256 mismatch".format(label),
        )
        return candidate

    capture_record = manifest.get("capture_manifest")
    capture_path = validate_file_record(
        capture_record,
        {"path", "bytes", "sha256"},
        "capture manifest",
    )
    capture_manifest = json.loads(capture_path.read_text(encoding="utf-8"))
    validate_manifest(capture_manifest, root)
    scenario_program = capture_manifest.get("scenario_program")
    acceptance_scenario = (
        scenario_program.get("acceptance_scenario")
        if isinstance(scenario_program, Mapping)
        else "V1"
    )
    _manifest_error(
        isinstance(acceptance_scenario, str)
        and bool(ACCEPTANCE_SCENARIO_RE.fullmatch(acceptance_scenario)),
        "review bundle acceptance scenario is invalid",
    )
    artifact_prefix = acceptance_scenario.lower()
    _manifest_error(
        manifest["run_id"] == capture_manifest.get("source_epoch"),
        "review bundle run ID differs from capture manifest",
    )
    _manifest_error(
        manifest["candidate_commit"] == capture_manifest.get("provenance", {}).get("head"),
        "review bundle candidate differs from capture manifest",
    )

    artifacts = manifest.get("artifacts")
    _manifest_error(isinstance(artifacts, list), "review bundle artifacts must be an array")
    roles = []
    paths = []
    for artifact in artifacts:
        validate_file_record(
            artifact,
            {
                "role",
                "path",
                "media_type",
                "bytes",
                "sha256",
                "source_path",
                "source_sha256",
            },
            "review artifact",
        )
        role = artifact.get("role")
        supported_roles = {"machine_acceptance", "quarter_speed"}
        if manifest["schema_version"] >= 2:
            supported_roles.add("browser_layout")
        _manifest_error(
            role in supported_roles,
            "unsupported review artifact role",
        )
        _manifest_error(
            isinstance(artifact.get("media_type"), str) and artifact["media_type"],
            "review artifact media type is missing",
        )
        expected_media_type = {
            "browser_layout": "video/mp4",
            "machine_acceptance": "application/json",
            "quarter_speed": "video/mp4",
        }[role]
        _manifest_error(
            artifact["media_type"] == expected_media_type,
            "review artifact media type does not match its role",
        )
        source_relative = artifact.get("source_path")
        _manifest_error(
            isinstance(source_relative, str)
            and source_relative
            and not Path(source_relative).is_absolute()
            and ".." not in Path(source_relative).parts,
            "invalid review artifact source path",
        )
        source = (root / source_relative).resolve()
        _manifest_error(source.is_file(), "review artifact source does not exist")
        _manifest_error(
            bool(SHA256_RE.fullmatch(str(artifact.get("source_sha256", ""))))
            and sha256_file(source) == artifact["source_sha256"],
            "review artifact source SHA-256 mismatch",
        )
        if role == "machine_acceptance":
            _manifest_error(
                artifact["path"] == "{}-machine-acceptance.json".format(artifact_prefix)
                and source_relative == capture_record["path"]
                and artifact["source_sha256"] == capture_record["sha256"],
                "machine report is not bound to the immutable capture manifest",
            )
        elif role == "quarter_speed":
            _manifest_error(
                artifact["path"] == "{}-quarter-speed.mp4".format(artifact_prefix)
                and source_relative == capture_manifest.get("video", {}).get("path"),
                "quarter-speed review is not bound to the normal-speed video",
            )
        else:
            _manifest_error(
                artifact["path"] == "{}-browser-layout.mp4".format(artifact_prefix)
                and source_relative
                == "{}-browser-layout-metrics.json".format(artifact_prefix),
                "browser layout review is not bound to its metrics",
            )
            browser_metrics = json.loads(source.read_text(encoding="utf-8"))
            _manifest_error(
                browser_metrics.get("schema") == "character_director_browser_layout_v1"
                and browser_metrics.get("schema_version") == 1,
                "unsupported browser layout metrics",
            )
            _manifest_error(
                browser_metrics.get("run_id") == manifest["run_id"]
                and browser_metrics.get("candidate_commit") == manifest["candidate_commit"]
                and browser_metrics.get("capture_manifest_sha256") == capture_record["sha256"],
                "browser layout metrics are not bound to this capture",
            )
            _manifest_error(
                browser_metrics.get("video_path") == artifact["path"]
                and browser_metrics.get("video_sha256") == artifact["sha256"]
                and browser_metrics.get("video_bytes") == artifact["bytes"],
                "browser layout metrics do not bind the browser video",
            )
            final_metrics = browser_metrics.get("final_client_metrics", {})
            canvas_metrics = final_metrics.get("canvas", {})
            _manifest_error(
                browser_metrics.get("frame_count") == browser_metrics.get("expected_frame_count")
                and final_metrics.get("decodeErrorCount") == 0
                and canvas_metrics.get("cols") == capture_manifest.get("init", {}).get("cols")
                and canvas_metrics.get("rows") == capture_manifest.get("init", {}).get("rows")
                and not browser_metrics.get("page_errors"),
                "browser layout metrics failed runtime integrity checks",
            )
        roles.append(role)
        paths.append(artifact["path"])
    _manifest_error(len(roles) == len(set(roles)), "review artifact roles must be unique")
    _manifest_error(len(paths) == len(set(paths)), "review artifact paths must be unique")
    expected_complete_roles = {"machine_acceptance", "quarter_speed"}
    if manifest["schema_version"] >= 2:
        expected_complete_roles.add("browser_layout")
    expected_complete = set(roles) == expected_complete_roles
    _manifest_error(manifest["complete"] == expected_complete, "review bundle completeness mismatch")


def generate_v1_review_products(
    capture_manifest_path: Path,
    capture_manifest: Mapping[str, Any],
) -> Path:
    output_dir = capture_manifest_path.resolve().parent
    program = capture_manifest.get("scenario_program")
    if not isinstance(program, Mapping) or program.get("acceptance_scenario") != "V1":
        raise EvidenceFailure("V1 review products require a V1 scenario program")
    video = capture_manifest.get("video")
    if not isinstance(video, Mapping) or video.get("available") is not True:
        raise EvidenceFailure("V1 review products require the normal-speed video")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise EvidenceFailure("ffmpeg is required for quarter-speed review output")

    normal_video = (output_dir / video["path"]).resolve()
    quarter_speed = output_dir / "v1-quarter-speed.mp4"
    quarter_speed.unlink(missing_ok=True)
    quarter = subprocess.run(
        (
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(normal_video),
            "-an",
            "-vf",
            "setpts=4.0*PTS,fps={:.6f}".format(float(capture_manifest["init"]["fps"])),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-y",
            str(quarter_speed),
        ),
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if quarter.returncode or not quarter_speed.is_file() or not quarter_speed.stat().st_size:
        raise EvidenceFailure(
            "quarter-speed generation failed: {}".format(
                quarter.stderr.decode("utf-8", errors="replace").strip()
            )
        )

    machine_report = output_dir / "v1-machine-acceptance.json"
    machine_report.unlink(missing_ok=True)
    analysis = subprocess.run(
        (
            sys.executable,
            str(ROOT / "tools" / "analyze_character_director_v1.py"),
            "--manifest",
            str(capture_manifest_path),
            "--output",
            str(machine_report),
        ),
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if analysis.returncode not in {0, 1} or not machine_report.is_file() or not machine_report.stat().st_size:
        raise EvidenceFailure(
            "V1 machine analysis failed to produce a report: {}".format(
                analysis.stderr.decode("utf-8", errors="replace").strip()
            )
        )

    browser_video = output_dir / "v1-browser-layout.mp4"
    browser_metrics = output_dir / "v1-browser-layout-metrics.json"
    browser_video.unlink(missing_ok=True)
    browser_metrics.unlink(missing_ok=True)
    browser_capture = subprocess.run(
        (
            sys.executable,
            str(ROOT / "tools" / "record_character_director_browser.py"),
            "--manifest",
            str(capture_manifest_path),
            "--video",
            str(browser_video),
            "--metrics",
            str(browser_metrics),
        ),
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if (
        browser_capture.returncode
        or not browser_video.is_file()
        or not browser_video.stat().st_size
        or not browser_metrics.is_file()
        or not browser_metrics.stat().st_size
    ):
        raise EvidenceFailure(
            "V1 browser layout capture failed: {}".format(
                browser_capture.stderr.decode("utf-8", errors="replace").strip()
            )
        )

    bundle = build_review_bundle_manifest(
        capture_manifest_path,
        output_dir,
        (
            ("quarter_speed", quarter_speed, "video/mp4", normal_video),
            ("machine_acceptance", machine_report, "application/json", capture_manifest_path),
            ("browser_layout", browser_video, "video/mp4", browser_metrics),
        ),
    )
    bundle_path = output_dir / "review-bundle-manifest.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validate_review_bundle_manifest(bundle, output_dir)
    return bundle_path


def scenario_ranges(scenarios: Sequence[Scenario], frames: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    ranges = []
    for scenario in scenarios:
        selected = [frame for frame in frames if frame.get("scenario") == scenario.name]
        ranges.append(
            {
                "name": scenario.name,
                "first_frame_index": selected[0]["frame_index"] if selected else None,
                "last_frame_index": selected[-1]["frame_index"] if selected else None,
                "frame_count": len(selected),
                "first_presentation_frame_index": (
                    selected[0]["presentation_frame_index"] if selected else None
                ),
                "last_presentation_frame_index": (
                    selected[-1]["presentation_frame_index"] if selected else None
                ),
                "first_received_at_utc": selected[0]["received_at_utc"] if selected else None,
                "last_received_at_utc": selected[-1]["received_at_utc"] if selected else None,
            }
        )
    return ranges


def _acknowledgement_runtime_epoch(command: Mapping[str, Any]) -> Optional[str]:
    ack = command.get("ack")
    if not isinstance(ack, Mapping):
        return None
    field = (
        "wizard_runtime_epoch"
        if command.get("transport", "command") == "media_session"
        else "runtime_epoch"
    )
    value = ack.get(field)
    return value if isinstance(value, str) and value else None


def collect_runtime_observations(
    runtime_identity: Mapping[str, Any],
    records: CaptureRecords,
) -> Dict[str, Any]:
    """Reconcile process identity with command/state runtime observations."""

    process_epoch = runtime_identity.get("runtime_epoch")
    if not isinstance(process_epoch, str) or not process_epoch:
        raise EvidenceFailure("runtime identity process epoch is missing")

    snapshot_epochs: List[str] = []
    subscriber_counts: List[int] = []
    for snapshot in records.state_snapshots:
        body = snapshot.get("body")
        diagnostics = body.get("diagnostics") if isinstance(body, Mapping) else None
        if not isinstance(diagnostics, Mapping):
            raise EvidenceFailure("state snapshot is missing diagnostics")
        epoch = diagnostics.get("runtime_epoch")
        subscribers = diagnostics.get("subscriber_count")
        if not isinstance(epoch, str) or not epoch:
            raise EvidenceFailure("state snapshot is missing command runtime epoch")
        if not _plain_int(subscribers, 1):
            raise EvidenceFailure("state snapshot has an invalid subscriber count")
        snapshot_epochs.append(epoch)
        subscriber_counts.append(subscribers)

    acknowledgement_epochs: List[str] = []
    for command in records.commands:
        epoch = _acknowledgement_runtime_epoch(command)
        if epoch is None:
            raise EvidenceFailure(
                "{} acknowledgement is missing runtime epoch".format(
                    command.get("transport", "command")
                )
            )
        acknowledgement_epochs.append(epoch)

    if not snapshot_epochs or not acknowledgement_epochs:
        raise EvidenceFailure("runtime observations require snapshots and acknowledgements")
    command_epochs = set(snapshot_epochs + acknowledgement_epochs)
    if len(command_epochs) != 1:
        raise EvidenceFailure("command runtime epoch changed during capture")
    if len(set(subscriber_counts)) != 1:
        raise EvidenceFailure("subscriber count changed during capture")

    return {
        "schema": "character_director_runtime_observations_v1",
        "schema_version": 1,
        "identity_process_epoch": process_epoch,
        "command_runtime_epoch": next(iter(command_epochs)),
        "subscriber_count": subscriber_counts[0],
        "snapshot_count": len(snapshot_epochs),
        "acknowledgement_count": len(acknowledgement_epochs),
    }


def _manifest_error(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestValidationError(message)


def _plain_int(value: object, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _read_ndjson(path: Path, label: str) -> List[Mapping[str, Any]]:
    records: List[Mapping[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ManifestValidationError("cannot read {}: {}".format(label, exc)) from exc
    for line_number, line in enumerate(lines, 1):
        _manifest_error(bool(line.strip()), "{} contains a blank row".format(label))
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ManifestValidationError(
                "{} row {} is not valid JSON: {}".format(label, line_number, exc)
            ) from exc
        _manifest_error(isinstance(record, Mapping), "{} rows must be objects".format(label))
        records.append(record)
    return records


def validate_artifact_semantics(manifest: Mapping[str, Any], output_dir: Path) -> None:
    """Replay captured transport bytes and independently reconstruct evidence truth."""

    root = output_dir.resolve()
    wire_path = root / "wire" / "frames.bin"
    index_path = root / "wire" / "index.ndjson"
    trace_path = root / "animation_truth_trace.ndjson"
    contact_path = root / "contact_verification.json"
    for path, label in (
        (wire_path, "wire frames"),
        (index_path, "wire index"),
        (trace_path, "animation truth trace"),
        (contact_path, "contact verification"),
    ):
        _manifest_error(path.is_file(), "missing semantic artifact: {}".format(label))

    frames = manifest.get("frames")
    init = manifest.get("init")
    _manifest_error(isinstance(frames, list), "manifest frames are required for semantic replay")
    _manifest_error(isinstance(init, Mapping), "manifest INIT is required for semantic replay")
    index_records = _read_ndjson(index_path, "wire index")
    trace_mappings = _read_ndjson(trace_path, "animation truth trace")
    _manifest_error(len(index_records) == len(frames), "wire index frame coverage mismatch")
    _manifest_error(len(trace_mappings) == len(frames), "truth trace frame coverage mismatch")

    try:
        wire = wire_path.read_bytes()
    except OSError as exc:
        raise ManifestValidationError("cannot read wire frames: {}".format(exc)) from exc

    expected_decoded_length = init.get("expected_decoded_length")
    cols = init.get("cols")
    rows = init.get("rows")
    cell_bytes = init.get("cell_bytes")
    _manifest_error(_plain_int(expected_decoded_length, 1), "invalid semantic replay frame length")
    _manifest_error(_plain_int(cols, 1) and _plain_int(rows, 1), "invalid semantic replay raster size")
    _manifest_error(_plain_int(cell_bytes, 1), "invalid semantic replay cell size")

    previous: Optional[bytes] = None
    decoded_frames: Dict[int, DecodedRasterFrameV1] = {}
    trace_records: List[AnimationTruthTraceV1] = []
    final_offset = 0
    for position, (frame, index_record, trace_mapping) in enumerate(
        zip(frames, index_records, trace_mappings)
    ):
        _manifest_error(isinstance(frame, Mapping), "manifest frame records must be objects")
        expected_index = frame.get("frame_index")
        offset = index_record.get("offset")
        size = index_record.get("size")
        _manifest_error(index_record.get("frame_index") == expected_index, "wire index frame mismatch")
        _manifest_error(index_record.get("codec_tag") == frame.get("codec_tag"), "wire index codec mismatch")
        _manifest_error(offset == frame.get("wire_offset"), "wire index offset mismatch")
        _manifest_error(size == frame.get("wire_size"), "wire index size mismatch")
        _manifest_error(index_record.get("sha256") == frame.get("wire_sha256"), "wire index hash mismatch")
        _manifest_error(index_record.get("scenario") == frame.get("scenario"), "wire index scenario mismatch")
        if manifest.get("schema_version") >= 3:
            _manifest_error(
                index_record.get("capture_owned") == frame.get("capture_owned"),
                "wire index ownership mismatch",
            )
            _manifest_error(
                index_record.get("presentation_frame_index")
                == frame.get("presentation_frame_index"),
                "wire index presentation order mismatch",
            )
        _manifest_error(
            index_record.get("received_at_utc") == frame.get("received_at_utc"),
            "wire index receive timestamp mismatch",
        )
        _manifest_error(_plain_int(offset) and _plain_int(size, 5), "invalid wire byte range")
        _manifest_error(offset == final_offset, "wire index byte ranges are not contiguous")
        end = offset + size
        _manifest_error(end <= len(wire), "wire byte range exceeds frames.bin")
        message = wire[offset:end]
        _manifest_error(hashlib.sha256(message).hexdigest() == frame.get("wire_sha256"), "wire message hash mismatch")
        _manifest_error(message[4] == frame.get("codec_tag"), "wire message codec tag mismatch")
        try:
            decoded_index, decoded = decode_frame(message, previous, cell_bytes=cell_bytes)
        except (ValueError, zlib.error, struct.error) as exc:
            raise ManifestValidationError(
                "wire frame {} failed to decode: {}".format(expected_index, exc)
            ) from exc
        _manifest_error(decoded_index == expected_index, "decoded frame index mismatch")
        _manifest_error(len(decoded) == expected_decoded_length, "decoded frame length mismatch")
        decoded_sha256 = hashlib.sha256(decoded).hexdigest()
        _manifest_error(decoded_sha256 == frame.get("sha256"), "decoded frame SHA-256 mismatch")

        try:
            trace_record = AnimationTruthTraceV1.from_mapping(trace_mapping)
        except (TypeError, ValueError) as exc:
            raise ManifestValidationError(
                "truth trace row {} is invalid: {}".format(position + 1, exc)
            ) from exc
        _manifest_error(trace_record.frame_index == expected_index, "truth trace frame index mismatch")
        _manifest_error(trace_record.codec_tag == frame.get("codec_tag"), "truth trace codec mismatch")
        _manifest_error(trace_record.encoded_size == size, "truth trace encoded size mismatch")
        _manifest_error(trace_record.frame_sha256 == decoded_sha256, "truth trace SHA-256 mismatch")
        _manifest_error(trace_record.frame_fnv1a32 == frame_hash(decoded), "truth trace FNV-1a mismatch")

        decoded_frames[decoded_index] = DecodedRasterFrameV1(cols=cols, rows=rows, cells=decoded)
        trace_records.append(trace_record)
        previous = decoded
        final_offset = end

    _manifest_error(final_offset == len(wire), "frames.bin contains unindexed trailing bytes")
    recomputed = verify_contact_trace(
        select_capture_owned_contact_records(trace_records, frames),
        decoded_frames=decoded_frames,
        strict_raster_evidence=True,
    ).to_mapping()
    recomputed["path"] = "contact_verification.json"
    recomputed = json.loads(json.dumps(recomputed, sort_keys=True))
    try:
        stored_contact = json.loads(contact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestValidationError("contact verification is not valid JSON: {}".format(exc)) from exc
    _manifest_error(stored_contact == recomputed, "stored contact report differs from semantic replay")
    _manifest_error(manifest.get("contact_verification") == recomputed, "manifest contact summary differs from semantic replay")


def validate_manifest(manifest: Mapping[str, Any], output_dir: Optional[Path] = None) -> None:
    """Validate evidence semantics; invalid runs remain valid manifest documents."""

    _manifest_error(isinstance(manifest, Mapping), "manifest must be an object")
    schema_version = manifest.get("schema_version")
    _manifest_error(
        schema_version in SUPPORTED_MANIFEST_SCHEMA_VERSIONS,
        "unsupported schema_version",
    )
    _manifest_error(manifest.get("evidence_kind") == EVIDENCE_KIND, "unsupported evidence_kind")
    content_minimization = manifest.get("content_minimization")
    _manifest_error(
        isinstance(content_minimization, Mapping)
        and content_minimization.get("schema") == CONTENT_MINIMIZATION_SCHEMA
        and content_minimization.get("sensitive_fields") == sorted(SENSITIVE_TEXT_FIELDS)
        and content_minimization.get("replacement") == "sha256_and_size_metadata",
        "manifest must declare sensitive-content minimization",
    )
    validate_evidence_content_minimization(manifest)
    valid = manifest.get("valid")
    _manifest_error(isinstance(valid, bool), "valid must be boolean")
    reason = manifest.get("failure_reason")
    if valid:
        _manifest_error(reason is None, "valid evidence cannot have a failure reason")
    else:
        _manifest_error(isinstance(reason, str) and bool(reason), "invalid evidence requires a failure reason")
    _manifest_error(manifest.get("replay_exported") is False, "visual capture must not export replay data")
    _manifest_error(
        manifest.get("frame_state_pairing") == PAIRING_DESCRIPTION,
        "manifest must declare atomic animation truth pairing",
    )

    init = manifest.get("init")
    _manifest_error(isinstance(init, Mapping), "manifest requires INIT metadata")
    for key in ("cols", "rows", "cell_bytes", "expected_decoded_length"):
        _manifest_error(_plain_int(init.get(key), 1), "INIT {} must be positive".format(key))
    _manifest_error(
        init["expected_decoded_length"] == init["cols"] * init["rows"] * init["cell_bytes"],
        "INIT expected decoded length is inconsistent",
    )
    _manifest_error(
        isinstance(init.get("fps"), (int, float)) and not isinstance(init.get("fps"), bool) and init["fps"] > 0,
        "INIT fps must be positive",
    )

    timings = manifest.get("timings")
    _manifest_error(isinstance(timings, Mapping), "manifest requires timings")
    _manifest_error(isinstance(timings.get("started_at_utc"), str), "missing capture start timestamp")
    _manifest_error(isinstance(timings.get("ended_at_utc"), str), "missing capture end timestamp")
    _manifest_error(
        isinstance(timings.get("duration_seconds"), (int, float))
        and not isinstance(timings.get("duration_seconds"), bool)
        and timings["duration_seconds"] >= 0,
        "duration_seconds must be nonnegative",
    )

    queue = manifest.get("queue")
    _manifest_error(isinstance(queue, Mapping), "manifest requires queue stats")
    _manifest_error(_plain_int(queue.get("capacity"), 1), "queue capacity must be positive")
    _manifest_error(_plain_int(queue.get("high_water_mark")), "queue high-water mark must be nonnegative")
    _manifest_error(queue["high_water_mark"] <= queue["capacity"], "queue high-water exceeds capacity")
    _manifest_error(_plain_int(queue.get("overrun_count")), "queue overrun count must be nonnegative")
    _manifest_error(_plain_int(manifest.get("dropped_frames")), "dropped_frames must be nonnegative")
    gaps = manifest.get("decoded_gaps")
    errors = manifest.get("decoder_errors")
    _manifest_error(isinstance(gaps, list), "decoded_gaps must be an array")
    _manifest_error(isinstance(errors, list), "decoder_errors must be an array")

    raw_scenarios = manifest.get("scenarios")
    scenario_program_summary = manifest.get("scenario_program")
    try:
        scenarios = (
            validate_scenarios_v2(raw_scenarios)
            if isinstance(scenario_program_summary, Mapping)
            and scenario_program_summary.get("schema") == SCENARIO_PROGRAM_V2_SCHEMA
            else validate_scenarios(raw_scenarios)
        )
    except ValueError as exc:
        raise ManifestValidationError("invalid scenario schema: {}".format(exc)) from exc
    if scenario_program_summary is not None:
        is_v2 = scenario_program_summary.get("schema") == SCENARIO_PROGRAM_V2_SCHEMA
        expected_program_fields = (
            {
                "schema",
                "schema_version",
                "program_id",
                "acceptance_scenario",
                "scenario_count",
                "maximum_capture_frame_count",
                "source_sha256",
                "artifact_path",
            }
            if is_v2
            else {
                "schema",
                "schema_version",
                "program_id",
                "acceptance_scenario",
                "scenario_count",
                "total_duration_seconds",
                "source_sha256",
                "artifact_path",
            }
        )
        _manifest_error(
            isinstance(scenario_program_summary, Mapping)
            and set(scenario_program_summary) == expected_program_fields,
            "invalid scenario program summary",
        )
        _manifest_error(
            (
                scenario_program_summary.get("schema"),
                scenario_program_summary.get("schema_version"),
            )
            in {
                (SCENARIO_PROGRAM_SCHEMA, SCENARIO_PROGRAM_VERSION),
                (SCENARIO_PROGRAM_V2_SCHEMA, SCENARIO_PROGRAM_V2_VERSION),
            },
            "unsupported scenario program summary",
        )
        _manifest_error(
            isinstance(scenario_program_summary.get("program_id"), str)
            and bool(SCENARIO_NAME_RE.fullmatch(scenario_program_summary["program_id"])),
            "invalid scenario program ID",
        )
        _manifest_error(
            isinstance(scenario_program_summary.get("acceptance_scenario"), str)
            and bool(ACCEPTANCE_SCENARIO_RE.fullmatch(scenario_program_summary["acceptance_scenario"])),
            "invalid acceptance scenario",
        )
        _manifest_error(
            scenario_program_summary.get("scenario_count") == len(scenarios),
            "scenario program count mismatch",
        )
        if is_v2:
            _manifest_error(
                scenario_program_summary.get("maximum_capture_frame_count")
                == sum(item.planned_frame_count(24.0) for item in scenarios),
                "scenario program frame budget mismatch",
            )
        else:
            expected_duration = round(
                sum(item.settle_seconds + item.capture_seconds for item in scenarios),
                6,
            )
            _manifest_error(
                scenario_program_summary.get("total_duration_seconds") == expected_duration,
                "scenario program duration mismatch",
            )
        _manifest_error(
            bool(SHA256_RE.fullmatch(str(scenario_program_summary.get("source_sha256", "")))),
            "invalid scenario program SHA-256",
        )
        _manifest_error(
            scenario_program_summary.get("artifact_path") == "scenario-program.json",
            "invalid scenario program artifact path",
        )

    frames = manifest.get("frames")
    _manifest_error(isinstance(frames, list), "frames must be an array")
    for index, frame in enumerate(frames):
        _manifest_error(isinstance(frame, Mapping), "frame records must be objects")
        _manifest_error(_plain_int(frame.get("frame_index")), "frame index must be nonnegative")
        _manifest_error(bool(SHA256_RE.fullmatch(str(frame.get("sha256", "")))), "invalid frame SHA-256")
        _manifest_error(bool(SHA256_RE.fullmatch(str(frame.get("wire_sha256", "")))), "invalid wire SHA-256")
        _manifest_error(_plain_int(frame.get("wire_offset")), "wire offset must be nonnegative")
        _manifest_error(_plain_int(frame.get("wire_size"), 5), "wire message must include header")
        _manifest_error(frame.get("codec_tag") in {0, 1, 2, 3}, "invalid adaptive codec tag")
        if schema_version >= 3:
            capture_owned = frame.get("capture_owned")
            _manifest_error(isinstance(capture_owned, bool), "frame capture_owned must be boolean")
            _manifest_error(
                (capture_owned and isinstance(frame.get("scenario"), str) and bool(frame["scenario"]))
                or (not capture_owned and frame.get("scenario") is None),
                "frame scenario ownership is inconsistent",
            )
            presentation_index = frame.get("presentation_frame_index")
            _manifest_error(
                (_plain_int(presentation_index) if capture_owned else presentation_index is None),
                "frame presentation index is inconsistent with ownership",
            )
        else:
            _manifest_error(isinstance(frame.get("scenario"), str), "frame scenario must be text")
        if index:
            _manifest_error(
                frame["frame_index"] == frames[index - 1]["frame_index"] + 1,
                "manifest frame indexes are not contiguous",
            )
            _manifest_error(
                frame["wire_offset"]
                == frames[index - 1]["wire_offset"] + frames[index - 1]["wire_size"],
                "wire message offsets are not contiguous",
            )

    capture = manifest.get("capture")
    _manifest_error(isinstance(capture, Mapping), "manifest requires capture summary")
    _manifest_error(capture.get("frame_count") == len(frames), "capture frame count mismatch")
    if schema_version >= 3:
        owned_frame_count = sum(frame.get("capture_owned") is True for frame in frames)
        presentation_indexes = [
            frame["presentation_frame_index"]
            for frame in frames
            if frame.get("capture_owned") is True
        ]
        _manifest_error(
            presentation_indexes == list(range(owned_frame_count)),
            "presentation frame indexes are not contiguous",
        )
        _manifest_error(
            capture.get("owned_frame_count") == owned_frame_count,
            "owned capture frame count mismatch",
        )
        _manifest_error(
            capture.get("unowned_frame_count") == len(frames) - owned_frame_count,
            "unowned capture frame count mismatch",
        )
    if frames:
        _manifest_error(capture.get("first_frame_index") == frames[0]["frame_index"], "first frame mismatch")
        _manifest_error(capture.get("last_frame_index") == frames[-1]["frame_index"], "last frame mismatch")

    trace = manifest.get("animation_truth_trace")
    _manifest_error(isinstance(trace, Mapping), "manifest requires animation truth trace summary")
    _manifest_error(
        trace.get("schema") == "animation_truth_trace_v1",
        "unsupported animation truth trace schema",
    )
    _manifest_error(
        _plain_int(trace.get("record_count")),
        "animation truth trace record_count must be nonnegative",
    )
    if valid:
        _manifest_error(
            trace["record_count"] == len(frames),
            "animation truth trace frame coverage mismatch",
        )
        _manifest_error(
            trace.get("path") == "animation_truth_trace.ndjson",
            "animation truth trace artifact path mismatch",
        )
        if frames:
            _manifest_error(
                trace.get("first_frame_index") == frames[0]["frame_index"],
                "animation truth trace first frame mismatch",
            )
            _manifest_error(
                trace.get("last_frame_index") == frames[-1]["frame_index"],
                "animation truth trace last frame mismatch",
            )

    contact = manifest.get("contact_verification")
    _manifest_error(isinstance(contact, Mapping), "manifest requires contact verification")
    _manifest_error(
        contact.get("schema") == "contact_verification_report_v1",
        "unsupported contact verification schema",
    )
    _manifest_error(
        isinstance(contact.get("passed"), bool),
        "contact verification passed must be boolean",
    )
    if valid:
        _manifest_error(contact.get("passed") is True, "contact verification failed")
        _manifest_error(
            contact.get("path") == "contact_verification.json",
            "contact verification artifact path mismatch",
        )
    commands = manifest.get("commands")
    _manifest_error(isinstance(commands, list), "commands must be an array")
    command_ids = [command.get("command_id") for command in commands if isinstance(command, Mapping)]
    sequences = [command.get("source_sequence") for command in commands if isinstance(command, Mapping)]
    _manifest_error(len(command_ids) == len(commands), "command outcomes must be objects")
    _manifest_error(len(command_ids) == len(set(command_ids)), "command IDs must be unique")
    _manifest_error(sequences == list(range(1, len(commands) + 1)), "source sequences must be strictly contiguous")

    ranges = manifest.get("scenario_ranges")
    _manifest_error(isinstance(ranges, list), "scenario_ranges must be an array")
    range_names = [item.get("name") for item in ranges if isinstance(item, Mapping)]
    _manifest_error(len(range_names) == len(ranges), "scenario ranges must be objects")
    _manifest_error(range_names == [scenario.name for scenario in scenarios], "scenario range names/order mismatch")
    if schema_version >= 3:
        commands_by_scenario = {
            command.get("scenario"): command
            for command in commands
            if isinstance(command, Mapping)
        }
        for item in ranges:
            selected = [
                frame for frame in frames if frame.get("scenario") == item["name"]
            ]
            _manifest_error(
                item.get("frame_count") == len(selected)
                and item.get("first_frame_index")
                == (selected[0]["frame_index"] if selected else None)
                and item.get("last_frame_index")
                == (selected[-1]["frame_index"] if selected else None),
                "scenario range contains pre/post-window spill",
            )
            _manifest_error(
                item.get("first_presentation_frame_index")
                == (selected[0]["presentation_frame_index"] if selected else None)
                and item.get("last_presentation_frame_index")
                == (selected[-1]["presentation_frame_index"] if selected else None),
                "scenario range presentation indexes are inconsistent",
            )
            command = commands_by_scenario.get(item["name"])
            if not valid and command is None:
                continue
            _manifest_error(
                isinstance(command, Mapping)
                and _plain_int(command.get("capture_planned_frame_count"), 1),
                "scenario command is missing its exact frame plan",
            )
            if valid:
                timing_mode = command.get("capture_timing_mode", "fixed")
                captured_count = item.get("frame_count")
                planned_count = command["capture_planned_frame_count"]
                _manifest_error(
                    (
                        timing_mode == "fixed"
                        and captured_count == planned_count
                    )
                    or (
                        timing_mode == "trace_trigger"
                        and _plain_int(captured_count, 1)
                        and captured_count <= planned_count
                        and isinstance(
                            command.get("trace_trigger_observation"),
                            Mapping,
                        )
                    ),
                    "scenario range contains pre/post-window spill",
                )

    artifacts = manifest.get("artifacts")
    _manifest_error(isinstance(artifacts, list), "artifacts must be an array")
    artifact_paths = []
    for artifact in artifacts:
        _manifest_error(isinstance(artifact, Mapping), "artifact records must be objects")
        path = artifact.get("path")
        _manifest_error(isinstance(path, str) and path and not Path(path).is_absolute(), "artifact path must be relative")
        _manifest_error(".." not in Path(path).parts, "artifact path cannot traverse its output directory")
        _manifest_error(bool(SHA256_RE.fullmatch(str(artifact.get("sha256", "")))), "invalid artifact SHA-256")
        _manifest_error(_plain_int(artifact.get("bytes"), 1), "artifact bytes must be positive")
        if output_dir is not None:
            root = output_dir.resolve()
            candidate = (root / path).resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise ManifestValidationError("artifact resolves outside output directory") from exc
            _manifest_error(candidate.is_file(), "artifact does not exist: {}".format(path))
            _manifest_error(candidate.stat().st_size == artifact["bytes"], "artifact byte count mismatch: {}".format(path))
            _manifest_error(sha256_file(candidate) == artifact["sha256"], "artifact SHA-256 mismatch: {}".format(path))
        artifact_paths.append(path)
    _manifest_error(len(artifact_paths) == len(set(artifact_paths)), "artifact paths must be unique")
    if valid:
        _manifest_error(
            trace["path"] in artifact_paths,
            "animation truth trace is not registered as an artifact",
        )
        _manifest_error(
            contact["path"] in artifact_paths,
            "contact verification is not registered as an artifact",
        )
        for required_path in ("wire/frames.bin", "wire/index.ndjson"):
            _manifest_error(
                required_path in artifact_paths,
                "semantic replay artifact is not registered: {}".format(required_path),
            )
        if scenario_program_summary is not None:
            program_path = scenario_program_summary["artifact_path"]
            _manifest_error(
                program_path in artifact_paths,
                "scenario program is not registered as an artifact",
            )
            if output_dir is not None:
                try:
                    loaded_program = load_scenario_program(output_dir / program_path)
                except ValueError as exc:
                    raise ManifestValidationError(
                        "scenario program replay failed: {}".format(exc)
                    ) from exc
                _manifest_error(
                    loaded_program.to_manifest() == dict(scenario_program_summary),
                    "scenario program summary differs from its artifact",
                )
                _manifest_error(
                    [item.to_mapping() for item in loaded_program.scenarios]
                    == [item.to_mapping() for item in scenarios],
                    "scenario program steps differ from the manifest",
                )

    video = manifest.get("video")
    _manifest_error(isinstance(video, Mapping) and isinstance(video.get("available"), bool), "invalid video summary")
    if video["available"]:
        _manifest_error(isinstance(video.get("path"), str) and video.get("codec") == "h264", "available video must be H.264")
    else:
        _manifest_error(video.get("path") is None and video.get("codec") is None, "unavailable video cannot name an artifact")

    rendering = manifest.get("rendering")
    _manifest_error(
        isinstance(rendering, Mapping)
        and rendering.get("cell_shape") == "square"
        and rendering.get("pixel_format") == "rgb24",
        "rendering must be square-cell RGB",
    )
    provenance = manifest.get("provenance")
    _manifest_error(isinstance(provenance, Mapping), "manifest requires Git provenance")
    _manifest_error(bool(GIT_OBJECT_RE.fullmatch(str(provenance.get("head", "")))), "invalid Git HEAD")
    _manifest_error(isinstance(provenance.get("branch"), str) and provenance["branch"], "missing Git branch")
    _manifest_error(isinstance(provenance.get("worktree_clean"), bool), "invalid worktree cleanliness")
    _manifest_error(isinstance(provenance.get("status_lines"), list), "invalid Git status lines")
    for field in ("status_sha256", "tracked_diff_sha256"):
        _manifest_error(
            bool(SHA256_RE.fullmatch(str(provenance.get(field, "")))),
            "invalid {}".format(field),
        )

    runtime_binding = manifest.get("runtime_binding")
    _manifest_error(isinstance(runtime_binding, Mapping), "manifest requires runtime binding")
    _manifest_error(isinstance(runtime_binding.get("verified"), bool), "invalid runtime binding status")
    start_identity = runtime_binding.get("start")
    end_identity = runtime_binding.get("end")
    _manifest_error(
        start_identity is None or isinstance(start_identity, Mapping),
        "invalid starting runtime identity",
    )
    _manifest_error(
        end_identity is None or isinstance(end_identity, Mapping),
        "invalid ending runtime identity",
    )
    if schema_version >= 3:
        observations = manifest.get("runtime_observations")
        expected_observation_fields = {
            "schema",
            "schema_version",
            "identity_process_epoch",
            "command_runtime_epoch",
            "subscriber_count",
            "snapshot_count",
            "acknowledgement_count",
        }
        _manifest_error(
            isinstance(observations, Mapping)
            and set(observations) == expected_observation_fields,
            "invalid runtime observations schema",
        )
        _manifest_error(
            observations.get("schema") == "character_director_runtime_observations_v1"
            and observations.get("schema_version") == 1,
            "unsupported runtime observations",
        )
        if valid:
            _manifest_error(
                isinstance(observations.get("identity_process_epoch"), str)
                and observations["identity_process_epoch"]
                == start_identity.get("runtime_epoch"),
                "process epoch differs from runtime identity",
            )
            _manifest_error(
                isinstance(observations.get("command_runtime_epoch"), str)
                and observations["command_runtime_epoch"],
                "command runtime epoch is missing",
            )
            _manifest_error(
                observations.get("subscriber_count") == 1
                and manifest.get("subscriber_count") == 1,
                "valid evidence requires one consistently observed subscriber",
            )
            _manifest_error(
                observations.get("snapshot_count") == len(manifest.get("state_snapshots", ())),
                "runtime observation snapshot count mismatch",
            )
            _manifest_error(
                observations.get("acknowledgement_count") == len(commands),
                "runtime observation acknowledgement count mismatch",
            )
            for command in commands:
                _manifest_error(
                    _acknowledgement_runtime_epoch(command)
                    == observations["command_runtime_epoch"],
                    "command acknowledgement runtime epoch mismatch",
                )
            for snapshot in manifest.get("state_snapshots", ()):
                diagnostics = snapshot.get("body", {}).get("diagnostics", {})
                _manifest_error(
                    diagnostics.get("runtime_epoch")
                    == observations["command_runtime_epoch"],
                    "state snapshot runtime epoch mismatch",
                )
                _manifest_error(
                    diagnostics.get("subscriber_count")
                    == observations["subscriber_count"],
                    "state snapshot subscriber count mismatch",
                )

    if valid:
        _manifest_error(runtime_binding["verified"] is True, "valid evidence requires verified runtime binding")
        try:
            validate_runtime_binding(
                start_identity,
                end_identity,
                provenance,
                runtime_binding.get("base_url", ""),
                InitMetadata(
                    "manifest",
                    init["fps"],
                    5,
                    init["cols"],
                    init["rows"],
                    0,
                    0,
                    0.0,
                    init["cell_bytes"],
                    {},
                ),
                output_dir,
            )
        except (EvidenceFailure, TypeError, ValueError) as exc:
            raise ManifestValidationError("runtime binding validation failed: {}".format(exc)) from exc
        _manifest_error(manifest["dropped_frames"] == 0, "valid evidence must have zero dropped frames")
        _manifest_error(queue["overrun_count"] == 0, "valid evidence cannot have queue overruns")
        _manifest_error(not gaps, "valid evidence cannot have decoded gaps")
        _manifest_error(not errors, "valid evidence cannot have decoder errors")
        _manifest_error(bool(frames), "valid evidence requires decoded frames")
        capture_owner_commands = [
            command
            for command in commands
            if _plain_int(command.get("capture_planned_frame_count"), 1)
        ]
        _manifest_error(
            len(capture_owner_commands) == len(scenarios),
            "valid evidence requires one capture-owning command per scenario",
        )
        for command in commands:
            transport = command.get("transport", "command")
            expected_disposition = (
                "accepted" if transport == "media_session" else "applied"
            )
            _manifest_error(
                transport in {"command", "media_session"},
                "valid evidence requires a recognized command transport",
            )
            _manifest_error(
                isinstance(command.get("ack"), Mapping)
                and command["ack"].get("disposition") == expected_disposition,
                "valid evidence requires {} {} acknowledgements".format(
                    expected_disposition,
                    transport,
                ),
            )
            _manifest_error(command.get("response_state") is not None, "valid evidence requires response state")
        for command in capture_owner_commands:
            _manifest_error(
                command.get("state_snapshot") is not None,
                "valid evidence requires capture-owner state snapshots",
            )
        for item in ranges:
            _manifest_error(_plain_int(item.get("frame_count"), 1), "every valid scenario requires frames")
        if schema_version >= 3:
            _manifest_error(
                video["available"] is True,
                "valid evidence requires an H.264 review video",
            )
            _manifest_error(
                video.get("path") in artifact_paths,
                "normal-speed video is not registered as an artifact",
            )
            _manifest_error(
                video.get("frame_count") == capture.get("owned_frame_count"),
                "review video must contain exactly the scenario-owned frames",
            )
        _manifest_error(bool(artifacts), "valid evidence requires hashed artifacts")
        if output_dir is not None:
            validate_artifact_semantics(manifest, output_dir)


def dropped_frame_count(integrity: CaptureIntegrity, queue_stats: QueueStats) -> int:
    count = queue_stats.overrun_count + len(integrity.decoder_errors)
    for gap in integrity.decoded_gaps:
        difference = gap["actual_frame_index"] - gap["expected_frame_index"]
        count += difference if difference > 0 else 1
    return count


def build_manifest(
    integrity: CaptureIntegrity,
    init: InitMetadata,
    scenarios: Sequence[Scenario],
    records: CaptureRecords,
    queue_stats: QueueStats,
    artifacts: List[Dict[str, Any]],
    sink: FFmpegSink,
    capture_started_utc: str,
    capture_ended_utc: str,
    capture_started: float,
    capture_ended: float,
    source_epoch: str,
    cell_size: int,
    contact_sheet_path: Optional[Path],
    output_dir: Path,
    provenance: Mapping[str, Any],
    runtime_binding: Mapping[str, Any],
    runtime_observations: Mapping[str, Any],
    scenario_program: Optional[ScenarioProgramV1],
) -> Dict[str, Any]:
    ranges = scenario_ranges(scenarios, records.frames)
    if integrity.valid and not records.frames:
        integrity.invalidate("capture produced no decoded frames")
    if integrity.valid and any(item["frame_count"] == 0 for item in ranges):
        integrity.invalidate("one or more scenarios captured no frames")
    if integrity.valid and not sink.available:
        integrity.invalidate("ffmpeg is required for exact-frame visual evidence")
    if integrity.valid and sink.available and not sink.succeeded:
        integrity.invalidate("ffmpeg was available but no H.264 MP4 was produced")
    if integrity.valid and not records.sample_paths:
        integrity.invalidate("capture produced no sampled PNGs")
    if integrity.valid and contact_sheet_path is None:
        integrity.invalidate("capture produced no contact sheet")
    if integrity.valid and len(records.animation_truth_trace) != len(records.frames):
        integrity.invalidate("atomic animation trace does not cover every captured frame")
    if integrity.valid and records.contact_verification is None:
        integrity.invalidate("contact verification report is missing")
    owned_frame_count = sum(frame.get("capture_owned") is True for frame in records.frames)
    for command in records.commands:
        planned_value = command.get("capture_planned_frame_count")
        if isinstance(planned_value, bool) or not isinstance(planned_value, int):
            continue
        actual = sum(
            frame.get("capture_owned") is True
            and frame.get("scenario") == command.get("scenario")
            for frame in records.frames
        )
        planned = planned_value
        mode = command.get("capture_timing_mode", "fixed")
        if integrity.valid and (
            actual <= 0
            or (mode == "fixed" and actual != planned)
            or (mode == "trace_trigger" and actual > planned)
        ):
            integrity.invalidate(
                "scenario-owned frame count violates its {} capture plan".format(mode)
            )

    first = records.frames[0]["frame_index"] if records.frames else None
    last = records.frames[-1]["frame_index"] if records.frames else None
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "evidence_kind": EVIDENCE_KIND,
        "content_minimization": {
            "schema": CONTENT_MINIMIZATION_SCHEMA,
            "sensitive_fields": sorted(SENSITIVE_TEXT_FIELDS),
            "replacement": "sha256_and_size_metadata",
        },
        "valid": integrity.valid,
        "failure_reason": integrity.failure_reason,
        "base_runtime": "external",
        "source_id": SOURCE_ID,
        "source_epoch": source_epoch,
        "subscriber_count": runtime_observations.get("subscriber_count"),
        "runtime_observations": dict(runtime_observations),
        "replay_exported": False,
        "frame_state_pairing": PAIRING_DESCRIPTION,
        "frame_state_pairing_note": (
            "Every captured wire frame is matched by frame index, decoded-frame SHA-256, and "
            "published codec to animation_truth_trace_v1 emitted from the accepted render candidate. "
            "HTTP state snapshots remain time-adjacent diagnostics only."
        ),
        "provenance": dict(provenance),
        "runtime_binding": dict(runtime_binding),
        "init": init.to_manifest(),
        "timings": {
            "started_at_utc": capture_started_utc,
            "ended_at_utc": capture_ended_utc,
            "duration_seconds": round(capture_ended - capture_started, 6),
            "first_frame_elapsed_seconds": records.frames[0]["elapsed_seconds"] if records.frames else None,
            "last_frame_elapsed_seconds": records.frames[-1]["elapsed_seconds"] if records.frames else None,
        },
        "capture": {
            "frame_count": len(records.frames),
            "owned_frame_count": owned_frame_count,
            "unowned_frame_count": len(records.frames) - owned_frame_count,
            "first_frame_index": first,
            "last_frame_index": last,
        },
        "queue": queue_stats.to_mapping(),
        "decoded_gaps": list(integrity.decoded_gaps),
        "decoder_errors": list(integrity.decoder_errors),
        "dropped_frames": dropped_frame_count(integrity, queue_stats),
        "scenarios": [scenario.to_mapping() for scenario in scenarios],
        "scenario_program": (
            None if scenario_program is None else scenario_program.to_manifest()
        ),
        "scenario_ranges": ranges,
        "commands": records.commands,
        "state_snapshots": records.state_snapshots,
        "frames": records.frames,
        "animation_truth_trace": {
            "schema": "animation_truth_trace_v1",
            "record_count": len(records.animation_truth_trace),
            "first_frame_index": (
                records.animation_truth_trace[0]["frame_index"]
                if records.animation_truth_trace
                else None
            ),
            "last_frame_index": (
                records.animation_truth_trace[-1]["frame_index"]
                if records.animation_truth_trace
                else None
            ),
            "path": (
                "animation_truth_trace.ndjson"
                if records.animation_truth_trace
                else None
            ),
        },
        "contact_verification": records.contact_verification
        or {
            "schema": "contact_verification_report_v1",
            "schema_version": 1,
            "passed": False,
            "path": None,
        },
        "samples": records.samples,
        "artifacts": artifacts,
        "video": {
            "ffmpeg_available": sink.available,
            "available": sink.succeeded,
            "path": sink.output_path.relative_to(output_dir).as_posix() if sink.succeeded else None,
            "codec": "h264" if sink.succeeded else None,
            "frame_count": sink.frame_count,
            "error": sink.error,
        },
        "rendering": {
            "cell_shape": "square",
            "cell_size_pixels": cell_size,
            "pixel_format": "rgb24",
            "width_pixels": init.cols * cell_size,
            "height_pixels": init.rows * cell_size,
            "glyph_byte_ignored": True,
        },
    }
    return minimize_evidence_content(manifest)


async def run_visual_review(
    base_url: str,
    output_dir: Path,
    queue_capacity: int = 16,
    cell_size: int = 4,
    sample_every_frames: int = 12,
    scenarios: Sequence[Scenario] = DEFAULT_SCENARIOS,
    scenario_program: Optional[ScenarioProgramV1] = None,
) -> Tuple[Path, Dict[str, Any]]:
    if queue_capacity <= 0 or cell_size <= 0 or sample_every_frames <= 0:
        raise ValueError("queue capacity, cell size, and sample interval must be positive")
    base_url = canonical_runtime_base_url(base_url)
    output_dir = output_dir.resolve()
    provenance = collect_git_provenance()
    scenario_program_path = (
        None if scenario_program is None else output_dir / "scenario-program.json"
    )
    if scenario_program is not None and tuple(scenarios) != scenario_program.scenarios:
        raise ValueError("scenario program and supplied scenarios disagree")
    ws_url, command_url, state_url, animation_trace_url, runtime_identity_url = runtime_urls(base_url)
    media_url = media_session_url(base_url)
    media_token = os.environ.get("WIZARD_MEDIA_CONNECTOR_TOKEN")
    source_epoch = "visual-review-{}".format(uuid.uuid4().hex[:12])
    run_id = source_epoch
    records = CaptureRecords()
    integrity = CaptureIntegrity()
    queue_stats = QueueStats(queue_capacity)
    scenario_clock = ScenarioClock()
    terminal = asyncio.Event()
    producer_done = asyncio.Event()
    closing = asyncio.Event()
    capture_started = time.perf_counter()
    capture_started_utc = utc_now()
    init: Optional[InitMetadata] = None
    sink: Optional[FFmpegSink] = None
    contact_path: Optional[Path] = None
    artifacts: List[Dict[str, Any]] = []
    receiver_task: Optional[asyncio.Task] = None
    writer_task: Optional[asyncio.Task] = None
    runtime_identity_start: Optional[Dict[str, Any]] = None
    runtime_identity_end: Optional[Dict[str, Any]] = None
    runtime_binding_error: Optional[str] = None
    runtime_observations: Dict[str, Any] = {
        "schema": "character_director_runtime_observations_v1",
        "schema_version": 1,
        "identity_process_epoch": None,
        "command_runtime_epoch": None,
        "subscriber_count": None,
        "snapshot_count": 0,
        "acknowledgement_count": 0,
    }

    try:
        runtime_identity_start, _ = await request_json_async("GET", runtime_identity_url)
        validate_runtime_binding(
            runtime_identity_start,
            runtime_identity_start,
            provenance,
            base_url,
        )
        # Seal both clean Git identities before writing evidence inside the
        # checkout. Otherwise the evidence directory itself makes the live
        # runtime appear dirty and invalidates an otherwise reproducible run.
        output_dir.mkdir(parents=True, exist_ok=True)
        if scenario_program_path is not None and scenario_program is not None:
            scenario_program_path.write_bytes(scenario_program.source_bytes)
        async with websockets.connect(
            ws_url,
            max_size=16 * 1024 * 1024,
            max_queue=queue_capacity,
            open_timeout=5.0,
            close_timeout=2.0,
        ) as socket:
            bootstrap = await asyncio.wait_for(socket.recv(), timeout=5.0)
            init = parse_init(bootstrap)
            decoder = StrictFrameDecoder(init.expected_decoded_length, integrity)
            queue: "asyncio.Queue[DecodedFrame]" = asyncio.Queue(maxsize=queue_capacity)
            video_path = output_dir / "{}-capture.mp4".format(run_id)
            sink = FFmpegSink(
                shutil.which("ffmpeg"),
                video_path,
                init.cols * cell_size,
                init.rows * cell_size,
                init.fps,
            )
            await sink.start()
            receiver_task = asyncio.create_task(
                receive_frames(
                    socket,
                    decoder,
                    queue,
                    queue_stats,
                    integrity,
                    terminal,
                    producer_done,
                    closing,
                    scenario_clock,
                )
            )
            writer_task = asyncio.create_task(
                write_frames(
                    queue,
                    producer_done,
                    terminal,
                    integrity,
                    records,
                    init,
                    sink,
                    output_dir,
                    run_id,
                    capture_started,
                    cell_size,
                    sample_every_frames,
                )
            )
            await record_state_snapshot(state_url, "capture-start", records)
            await drive_scenarios(
                scenarios,
                command_url,
                media_url,
                media_token,
                state_url,
                animation_trace_url,
                source_epoch,
                scenario_clock,
                records,
                terminal,
                integrity,
                init.fps,
            )
            await record_state_snapshot(state_url, "capture-end", records)
            closing.set()
            await socket.close()
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        if (
            scenario_program_path is not None
            and scenario_program is not None
            and not scenario_program_path.exists()
        ):
            scenario_program_path.write_bytes(scenario_program.source_bytes)
        integrity.invalidate("{}: {}".format(type(exc).__name__, exc))
        terminal.set()
    finally:
        closing.set()
        if receiver_task:
            try:
                await asyncio.wait_for(receiver_task, timeout=3.0)
            except asyncio.TimeoutError:
                receiver_task.cancel()
                integrity.invalidate("WebSocket receiver did not stop")
            except Exception as exc:
                integrity.invalidate("WebSocket receiver failed: {}".format(exc))
        else:
            producer_done.set()
        if writer_task:
            try:
                await asyncio.wait_for(writer_task, timeout=15.0)
            except asyncio.TimeoutError:
                writer_task.cancel()
                integrity.invalidate("frame writer did not drain")
            except Exception as exc:
                integrity.invalidate("frame writer failed: {}".format(exc))
        if sink:
            try:
                await sink.close()
            except Exception as exc:
                integrity.invalidate(str(exc))

    if init is None:
        # A failed handshake still emits a structurally inspectable invalid manifest.
        init = InitMetadata("INIT:0:5:1:1:0:0:0", 1.0, 5, 1, 1, 0, 0, 0.0, CELL_BYTES, {})
        integrity.invalidate("capture ended before a valid INIT was received")
    if sink is None:
        sink = FFmpegSink(None, output_dir / "{}-capture.mp4".format(run_id), 4, 4, 1.0)

    wire_path = output_dir / "wire" / "frames.bin"
    wire_index_path = output_dir / "wire" / "index.ndjson"
    animation_trace_path = output_dir / "animation_truth_trace.ndjson"
    contact_verification_path = output_dir / "contact_verification.json"
    if records.frames and wire_path.is_file():
        wire_index_path.write_text(
            "".join(
                json.dumps(
                    {
                        "frame_index": frame["frame_index"],
                        "codec_tag": frame["codec_tag"],
                        "offset": frame["wire_offset"],
                        "size": frame["wire_size"],
                        "sha256": frame["wire_sha256"],
                        "scenario": frame["scenario"],
                        "capture_owned": frame["capture_owned"],
                        "presentation_frame_index": frame["presentation_frame_index"],
                        "received_at_utc": frame["received_at_utc"],
                    },
                    sort_keys=True,
                )
                + "\n"
                for frame in records.frames
            ),
            encoding="utf-8",
        )

    if records.frames:
        try:
            trace_payload, _ = await request_json_async("GET", animation_trace_url)
            records.animation_truth_trace = select_atomic_animation_trace(
                trace_payload,
                records.frames,
            )
            animation_trace_path.write_text(
                "".join(
                    json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
                    for record in records.animation_truth_trace
                ),
                encoding="utf-8",
            )
            contact_report = verify_contact_trace(
                select_capture_owned_contact_records(
                    tuple(
                        AnimationTruthTraceV1.from_mapping(record)
                        for record in records.animation_truth_trace
                    ),
                    records.frames,
                ),
                decoded_frames=records.decoded_raster_frames,
                strict_raster_evidence=True,
            )
            records.contact_verification = json.loads(
                json.dumps(contact_report.to_mapping(), sort_keys=True)
            )
            records.contact_verification["path"] = "contact_verification.json"
            contact_verification_path.write_text(
                json.dumps(
                    records.contact_verification,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            if not contact_report.passed:
                integrity.invalidate("planted-foot contact verification failed")
        except Exception as exc:
            integrity.invalidate("atomic animation trace capture failed: {}".format(exc))

    if records.animation_truth_trace:
        candidate = output_dir / "{}-contact-sheet.png".format(run_id)
        try:
            await asyncio.to_thread(
                add_transition_samples,
                records,
                init,
                output_dir,
                run_id,
                cell_size,
            )
            await asyncio.to_thread(
                create_contact_sheet,
                records.samples,
                records.animation_truth_trace,
                records.commands,
                output_dir,
                candidate,
                init.fps,
            )
            contact_path = candidate
        except Exception as exc:
            integrity.invalidate("contact sheet generation failed: {}".format(exc))

    try:
        runtime_identity_end, _ = await request_json_async("GET", runtime_identity_url)
        if runtime_identity_start is None:
            raise EvidenceFailure("starting runtime identity was not captured")
        validate_runtime_binding(
            runtime_identity_start,
            runtime_identity_end,
            provenance,
            base_url,
            init,
            output_dir,
        )
    except Exception as exc:
        runtime_binding_error = "{}: {}".format(type(exc).__name__, exc)
        integrity.invalidate("runtime binding failed: {}".format(exc))

    if runtime_identity_start is not None:
        try:
            runtime_observations = collect_runtime_observations(
                runtime_identity_start,
                records,
            )
            if runtime_observations["subscriber_count"] != 1:
                integrity.invalidate(
                    "strict evidence requires exactly one ASCILINE subscriber; observed {}".format(
                        runtime_observations["subscriber_count"]
                    )
                )
        except EvidenceFailure as exc:
            integrity.invalidate("runtime observations failed: {}".format(exc))

    for path in records.sample_paths:
        if path.is_file():
            artifacts.append(artifact_record(path, output_dir, "image/png"))
    if contact_path and contact_path.is_file():
        artifacts.append(artifact_record(contact_path, output_dir, "image/png"))
    if sink.succeeded and sink.output_path.is_file():
        artifacts.append(artifact_record(sink.output_path, output_dir, "video/mp4"))
    if wire_path.is_file() and wire_path.stat().st_size > 0:
        artifacts.append(artifact_record(wire_path, output_dir, "application/octet-stream"))
    if wire_index_path.is_file() and wire_index_path.stat().st_size > 0:
        artifacts.append(artifact_record(wire_index_path, output_dir, "application/x-ndjson"))
    if animation_trace_path.is_file() and animation_trace_path.stat().st_size > 0:
        artifacts.append(
            artifact_record(
                animation_trace_path,
                output_dir,
                "application/x-ndjson",
            )
        )
    if contact_verification_path.is_file() and contact_verification_path.stat().st_size > 0:
        artifacts.append(
            artifact_record(
                contact_verification_path,
                output_dir,
                "application/json",
            )
        )
    if scenario_program_path is not None and scenario_program_path.is_file():
        artifacts.append(
            artifact_record(
                scenario_program_path,
                output_dir,
                "application/json",
            )
        )

    capture_ended = time.perf_counter()
    runtime_binding = {
        "verified": runtime_binding_error is None,
        "failure_reason": runtime_binding_error,
        "base_url": base_url,
        "start": runtime_identity_start,
        "end": runtime_identity_end,
    }
    manifest = build_manifest(
        integrity,
        init,
        scenarios,
        records,
        queue_stats,
        artifacts,
        sink,
        capture_started_utc,
        utc_now(),
        capture_started,
        capture_ended,
        source_epoch,
        cell_size,
        contact_path,
        output_dir,
        provenance,
        runtime_binding,
        runtime_observations,
        scenario_program,
    )
    try:
        validate_manifest(manifest, output_dir)
    except ManifestValidationError as exc:
        if integrity.valid:
            integrity.invalidate("manifest validation failed: {}".format(exc))
            manifest = build_manifest(
                integrity,
                init,
                scenarios,
                records,
                queue_stats,
                artifacts,
                sink,
                capture_started_utc,
                utc_now(),
                capture_started,
                time.perf_counter(),
                source_epoch,
                cell_size,
                contact_path,
                output_dir,
                provenance,
                runtime_binding,
                runtime_observations,
                scenario_program,
            )
            validate_manifest(manifest, output_dir)
        else:
            raise

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path, manifest


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Strict external real-runtime Character Director visual review capture."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--queue-capacity", type=int, default=16)
    parser.add_argument("--cell-size", type=int, default=4)
    parser.add_argument("--sample-every-frames", type=int, default=12)
    parser.add_argument("--scenarios-file", type=Path)
    args = parser.parse_args(argv)
    if args.queue_capacity <= 0:
        parser.error("--queue-capacity must be positive")
    if args.cell_size <= 0:
        parser.error("--cell-size must be positive")
    if args.sample_every_frames <= 0:
        parser.error("--sample-every-frames must be positive")
    try:
        args.scenario_program = (
            None
            if args.scenarios_file is None
            else load_scenario_program(args.scenarios_file)
        )
    except ValueError as exc:
        parser.error(str(exc))
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    scenarios = (
        DEFAULT_SCENARIOS
        if args.scenario_program is None
        else args.scenario_program.scenarios
    )
    manifest_path, manifest = asyncio.run(
        run_visual_review(
            args.base_url,
            args.output_dir,
            queue_capacity=args.queue_capacity,
            cell_size=args.cell_size,
            sample_every_frames=args.sample_every_frames,
            scenarios=scenarios,
            scenario_program=args.scenario_program,
        )
    )
    print(manifest_path)
    if not manifest["valid"]:
        print("INVALID: {}".format(manifest["failure_reason"]), file=sys.stderr)
        return 1
    if (
        args.scenario_program is not None
        and args.scenario_program.acceptance_scenario == "V1"
    ):
        try:
            bundle_path = generate_v1_review_products(manifest_path, manifest)
        except (EvidenceFailure, ManifestValidationError, OSError, ValueError) as exc:
            print("INVALID REVIEW BUNDLE: {}".format(exc), file=sys.stderr)
            return 1
        print(bundle_path)
    print("VALID: {} contiguous frames, zero dropped frames".format(manifest["capture"]["frame_count"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
