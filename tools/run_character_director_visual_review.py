#!/usr/bin/env python3
"""Capture strict visual-review evidence from an already-running WizardJoe runtime."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
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
from wizard_avatar.contact_verifier import verify_contact_trace
from wizard_avatar.protocol import CELL_BYTES, decode_frame


DEFAULT_BASE_URL = "http://127.0.0.1:8875"
DEFAULT_OUTPUT_DIR = ROOT / "evidence" / "character-director" / "real-runtime-visual-review"
PROTECTED_LEGACY_PORT = 8765
SOURCE_ID = "character-director-visual-review"
MANIFEST_SCHEMA_VERSION = 1
EVIDENCE_KIND = "external_real_runtime_visual_review"
PAIRING_DESCRIPTION = "atomic_animation_truth_trace_v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_OBJECT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
SCENARIO_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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
        if not isinstance(kind, str) or kind not in COMMAND_KINDS:
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
    scenario: str
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


@dataclass
class ScenarioClock:
    current: str = "bootstrap"


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
        branch = run("branch", "--show-current").decode("utf-8").strip()
        status = run("status", "--porcelain=v1", "--untracked-files=all")
        tracked_diff = run("diff", "--binary", "HEAD")
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        raise EvidenceFailure("cannot establish Git provenance: {}".format(exc)) from exc
    if not GIT_OBJECT_RE.fullmatch(head):
        raise EvidenceFailure("Git HEAD is not a full SHA-1/SHA-256 object ID")
    return {
        "head": head,
        "branch": branch,
        "worktree_clean": not status,
        "status_sha256": hashlib.sha256(status).hexdigest(),
        "tracked_diff_sha256": hashlib.sha256(tracked_diff).hexdigest(),
        "status_lines": status.decode("utf-8", errors="replace").splitlines(),
    }


def request_json(method: str, url: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
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
    method: str, url: str, payload: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], float]:
    started = time.perf_counter()
    result = await asyncio.to_thread(request_json, method, url, payload)
    return result, (time.perf_counter() - started) * 1000.0


def runtime_urls(base_url: str) -> Tuple[str, str, str, str]:
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("--base-url must be an absolute http(s) URL")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("--base-url contains an invalid port") from exc
    if port == PROTECTED_LEGACY_PORT:
        raise ValueError("the visual-review harness must never contact protected port 8765")
    base_path = parsed.path.rstrip("/")
    http_base = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, base_path, "", ""))
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = urllib.parse.urlunsplit(
        (ws_scheme, parsed.netloc, base_path + "/ws/avatar/wizard", "codec=adaptive", "")
    )
    return (
        ws_url,
        http_base + "/api/avatar/wizard/command",
        http_base + "/api/avatar/wizard/state",
        http_base + "/api/avatar/wizard/animation-trace",
    )


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
                    scenario=scenario_clock.current,
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
                records.frames.append(
                    {
                        "frame_index": frame.frame_index,
                        "sha256": digest,
                        "wire_sha256": wire_digest,
                        "wire_offset": wire_offset,
                        "wire_size": wire_size,
                        "codec_tag": frame.codec_tag,
                        "scenario": frame.scenario,
                        "received_at_utc": frame.received_at_utc,
                        "elapsed_seconds": round(frame.received_monotonic - capture_started, 6),
                    }
                )
                wire_offset += wire_size
                image = await asyncio.to_thread(
                    square_cell_image, frame.cells, init.cols, init.rows, cell_size
                )
                await sink.write(image.tobytes())
                should_sample = frame.scenario not in sampled_scenarios or processed % sample_every_frames == 0
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
                            "frame_sha256": digest,
                        }
                    )
                    sampled_scenarios.add(frame.scenario)
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
        "body": body,
    }
    records.state_snapshots.append(snapshot)
    return snapshot


async def drive_scenarios(
    scenarios: Sequence[Scenario],
    command_url: str,
    state_url: str,
    source_epoch: str,
    scenario_clock: ScenarioClock,
    records: CaptureRecords,
    terminal: asyncio.Event,
    integrity: CaptureIntegrity,
) -> None:
    for source_sequence, scenario in enumerate(scenarios, start=1):
        if terminal.is_set():
            raise EvidenceFailure(integrity.failure_reason or "capture terminated")
        scenario_clock.current = scenario.name
        command_id = "{}-{:04d}-{}".format(source_epoch, source_sequence, scenario.name)
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
            "payload": scenario.payload,
            "request_started_at_utc": utc_now(),
            "ack": None,
            "response_state": None,
            "state_snapshot": None,
            "error": None,
        }
        records.commands.append(outcome)
        try:
            response, latency_ms = await request_json_async("POST", command_url, envelope)
            outcome["request_completed_at_utc"] = utc_now()
            outcome["request_latency_ms"] = round(latency_ms, 3)
            outcome["ack"] = response.get("ack")
            outcome["response_state"] = response.get("state")
            if not isinstance(outcome["ack"], dict):
                raise EvidenceFailure("command {} returned no acknowledgement".format(command_id))
            if outcome["ack"].get("command_id") != command_id:
                raise EvidenceFailure("command acknowledgement ID mismatch")
            if outcome["ack"].get("source_sequence") != source_sequence:
                raise EvidenceFailure("command acknowledgement sequence mismatch")
            if outcome["ack"].get("disposition") != "applied":
                raise EvidenceFailure(
                    "command {} was not applied: {}".format(command_id, outcome["ack"].get("disposition"))
                )
            outcome["state_snapshot"] = await record_state_snapshot(
                state_url, "{}-after-ack".format(scenario.name), records
            )
            await wait_or_terminal(scenario.settle_seconds, terminal, integrity)
            outcome["capture_started_at_utc"] = utc_now()
            await wait_or_terminal(scenario.capture_seconds, terminal, integrity)
            outcome["capture_completed_at_utc"] = utc_now()
        except Exception as exc:
            outcome["error"] = "{}: {}".format(type(exc).__name__, exc)
            integrity.invalidate("scenario {} failed: {}".format(scenario.name, exc))
            terminal.set()
            raise


def create_contact_sheet(sample_paths: Sequence[Path], output_path: Path) -> None:
    if not sample_paths:
        raise EvidenceFailure("cannot create contact sheet without sampled PNGs")
    from PIL import Image, ImageDraw

    columns = min(3, len(sample_paths))
    thumb_width = 384
    label_height = 28
    loaded = []
    for path in sample_paths:
        with Image.open(path) as source:
            image = source.convert("RGB")
            thumb_height = max(1, round(image.height * thumb_width / image.width))
            loaded.append(image.resize((thumb_width, thumb_height), Image.Resampling.NEAREST))
    thumb_height = max(image.height for image in loaded)
    rows = math.ceil(len(loaded) / columns)
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (path, image) in enumerate(zip(sample_paths, loaded)):
        x = (index % columns) * thumb_width
        y = (index // columns) * (thumb_height + label_height)
        sheet.paste(image, (x, y))
        draw.text((x + 6, y + thumb_height + 7), path.stem[-72:], fill=(20, 20, 20))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, "PNG")


def artifact_record(path: Path, output_dir: Path, media_type: str) -> Dict[str, Any]:
    return {
        "path": path.relative_to(output_dir).as_posix(),
        "media_type": media_type,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


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
                "first_received_at_utc": selected[0]["received_at_utc"] if selected else None,
                "last_received_at_utc": selected[-1]["received_at_utc"] if selected else None,
            }
        )
    return ranges


def _manifest_error(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestValidationError(message)


def _plain_int(value: object, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def validate_manifest(manifest: Mapping[str, Any], output_dir: Optional[Path] = None) -> None:
    """Validate evidence semantics; invalid runs remain valid manifest documents."""

    _manifest_error(isinstance(manifest, Mapping), "manifest must be an object")
    _manifest_error(manifest.get("schema_version") == MANIFEST_SCHEMA_VERSION, "unsupported schema_version")
    _manifest_error(manifest.get("evidence_kind") == EVIDENCE_KIND, "unsupported evidence_kind")
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
    try:
        scenarios = validate_scenarios(raw_scenarios)
    except ValueError as exc:
        raise ManifestValidationError("invalid scenario schema: {}".format(exc)) from exc

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

    if valid:
        _manifest_error(manifest["dropped_frames"] == 0, "valid evidence must have zero dropped frames")
        _manifest_error(queue["overrun_count"] == 0, "valid evidence cannot have queue overruns")
        _manifest_error(not gaps, "valid evidence cannot have decoded gaps")
        _manifest_error(not errors, "valid evidence cannot have decoder errors")
        _manifest_error(bool(frames), "valid evidence requires decoded frames")
        _manifest_error(len(commands) == len(scenarios), "valid evidence requires one command per scenario")
        for command in commands:
            _manifest_error(
                isinstance(command.get("ack"), Mapping) and command["ack"].get("disposition") == "applied",
                "valid evidence requires applied command acknowledgements",
            )
            _manifest_error(command.get("response_state") is not None, "valid evidence requires response state")
            _manifest_error(command.get("state_snapshot") is not None, "valid evidence requires state snapshot")
        for item in ranges:
            _manifest_error(_plain_int(item.get("frame_count"), 1), "every valid scenario requires frames")
        _manifest_error(bool(artifacts), "valid evidence requires hashed artifacts")


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
) -> Dict[str, Any]:
    ranges = scenario_ranges(scenarios, records.frames)
    if integrity.valid and not records.frames:
        integrity.invalidate("capture produced no decoded frames")
    if integrity.valid and any(item["frame_count"] == 0 for item in ranges):
        integrity.invalidate("one or more scenarios captured no frames")
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

    first = records.frames[0]["frame_index"] if records.frames else None
    last = records.frames[-1]["frame_index"] if records.frames else None
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "evidence_kind": EVIDENCE_KIND,
        "valid": integrity.valid,
        "failure_reason": integrity.failure_reason,
        "base_runtime": "external",
        "source_id": SOURCE_ID,
        "source_epoch": source_epoch,
        "subscriber_count": 1,
        "replay_exported": False,
        "frame_state_pairing": PAIRING_DESCRIPTION,
        "frame_state_pairing_note": (
            "Every captured wire frame is matched by frame index, decoded-frame SHA-256, and "
            "published codec to animation_truth_trace_v1 emitted from the accepted render candidate. "
            "HTTP state snapshots remain time-adjacent diagnostics only."
        ),
        "provenance": dict(provenance),
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
            "first_frame_index": first,
            "last_frame_index": last,
        },
        "queue": queue_stats.to_mapping(),
        "decoded_gaps": list(integrity.decoded_gaps),
        "decoder_errors": list(integrity.decoder_errors),
        "dropped_frames": dropped_frame_count(integrity, queue_stats),
        "scenarios": [scenario.to_mapping() for scenario in scenarios],
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


async def run_visual_review(
    base_url: str,
    output_dir: Path,
    queue_capacity: int = 16,
    cell_size: int = 4,
    sample_every_frames: int = 12,
    scenarios: Sequence[Scenario] = DEFAULT_SCENARIOS,
) -> Tuple[Path, Dict[str, Any]]:
    if queue_capacity <= 0 or cell_size <= 0 or sample_every_frames <= 0:
        raise ValueError("queue capacity, cell size, and sample interval must be positive")
    output_dir = output_dir.resolve()
    provenance = collect_git_provenance()
    output_dir.mkdir(parents=True, exist_ok=True)
    ws_url, command_url, state_url, animation_trace_url = runtime_urls(base_url)
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

    try:
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
                state_url,
                source_epoch,
                scenario_clock,
                records,
                terminal,
                integrity,
            )
            await record_state_snapshot(state_url, "capture-end", records)
            closing.set()
            await socket.close()
    except Exception as exc:
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

    if records.sample_paths:
        candidate = output_dir / "{}-contact-sheet.png".format(run_id)
        try:
            await asyncio.to_thread(create_contact_sheet, records.sample_paths, candidate)
            contact_path = candidate
        except Exception as exc:
            integrity.invalidate("contact sheet generation failed: {}".format(exc))

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
                AnimationTruthTraceV1.from_mapping(record)
                for record in records.animation_truth_trace
            )
            records.contact_verification = contact_report.to_mapping()
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

    capture_ended = time.perf_counter()
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
    args = parser.parse_args(argv)
    if args.queue_capacity <= 0:
        parser.error("--queue-capacity must be positive")
    if args.cell_size <= 0:
        parser.error("--cell-size must be positive")
    if args.sample_every_frames <= 0:
        parser.error("--sample-every-frames must be positive")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    manifest_path, manifest = asyncio.run(
        run_visual_review(
            args.base_url,
            args.output_dir,
            queue_capacity=args.queue_capacity,
            cell_size=args.cell_size,
            sample_every_frames=args.sample_every_frames,
        )
    )
    print(manifest_path)
    if not manifest["valid"]:
        print("INVALID: {}".format(manifest["failure_reason"]), file=sys.stderr)
        return 1
    print("VALID: {} contiguous frames, zero dropped frames".format(manifest["capture"]["frame_count"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
