#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from collections import deque
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

import websockets

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.protocol import decode_frame


@dataclass
class ViewerResult:
    viewer_id: int
    slow: bool
    connections: int = 0
    reconnects: int = 0
    connection_errors: int = 0
    frames: int = 0
    sequence_regressions: int = 0
    decode_errors: int = 0
    first_sequence: Optional[int] = None
    last_sequence: Optional[int] = None
    last_frame_sha256: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class RuntimeSample:
    elapsed_seconds: float
    simulation_tick: int
    state_latency_ms: float
    event_loop_lag_ms: float
    hub_actual_fps: Optional[float]
    hub_window_fps: Optional[float]
    hub_queue_drops: int
    schedule_overruns: int
    rss_bytes: Optional[int]


@dataclass(frozen=True)
class RollingWindow:
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    complete: bool
    simulation_hz: float
    presentation_fps_min: Optional[float]
    presentation_fps_mean: Optional[float]
    state_latency_ms_p95: Optional[float]
    event_loop_lag_ms_p95: Optional[float]
    hub_queue_drops: int
    schedule_overruns: int
    rss_bytes_start: Optional[int]
    rss_bytes_end: Optional[int]


LATENCY_BUCKET_UPPER_BOUNDS_MS = (
    1.0,
    2.0,
    3.0,
    5.0,
    8.0,
    10.0,
    12.0,
    16.0,
    20.0,
    25.0,
    32.0,
    40.0,
    50.0,
    63.0,
    80.0,
    100.0,
    125.0,
    160.0,
    200.0,
    250.0,
    320.0,
    400.0,
    500.0,
    630.0,
    800.0,
    1000.0,
    2000.0,
    5000.0,
    10000.0,
)


class BoundedLatencyStats:
    def __init__(self, recent_capacity: int = 2048) -> None:
        if recent_capacity <= 0:
            raise ValueError("recent latency capacity must be positive")
        self._counts = [0] * (len(LATENCY_BUCKET_UPPER_BOUNDS_MS) + 1)
        self._recent: Deque[float] = deque(maxlen=recent_capacity)
        self.count = 0
        self.maximum: Optional[float] = None

    def add(self, value: float) -> None:
        if not math.isfinite(value) or value < 0:
            raise ValueError("latency must be finite and nonnegative")
        self.count += 1
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        self._recent.append(value)
        for index, upper_bound in enumerate(LATENCY_BUCKET_UPPER_BOUNDS_MS):
            if value <= upper_bound:
                self._counts[index] += 1
                break
        else:
            self._counts[-1] += 1

    def percentile_upper_bound(self, quantile: int) -> Optional[float]:
        if not self.count:
            return None
        target = max(1, math.ceil((quantile / 100.0) * self.count))
        cumulative = 0
        for index, count in enumerate(self._counts):
            cumulative += count
            if cumulative >= target:
                if index < len(LATENCY_BUCKET_UPPER_BOUNDS_MS):
                    return LATENCY_BUCKET_UPPER_BOUNDS_MS[index]
                return round(float(self.maximum), 3) if self.maximum is not None else None
        return None

    def to_mapping(self) -> Dict[str, Any]:
        return {
            "request_count": self.count,
            "retained_recent_latency_count": len(self._recent),
            "latency_ms_p50_recent": percentile(list(self._recent), 50),
            "latency_ms_p95_recent": percentile(list(self._recent), 95),
            "latency_ms_p50_upper_bound": self.percentile_upper_bound(50),
            "latency_ms_p95_upper_bound": self.percentile_upper_bound(95),
            "latency_ms_max": round(self.maximum, 3) if self.maximum is not None else None,
            "histogram": {
                "upper_bounds_ms": list(LATENCY_BUCKET_UPPER_BOUNDS_MS),
                "bucket_counts": list(self._counts),
            },
        }


def request_json(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    bearer: Optional[str] = None,
) -> Dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=3.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError("{} {} failed: {} {}".format(method, url, exc.code, body)) from exc


async def request_json_async(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    bearer: Optional[str] = None,
) -> tuple[Dict[str, Any], float]:
    started = time.perf_counter()
    result = await asyncio.to_thread(request_json, method, url, payload, bearer)
    return result, (time.perf_counter() - started) * 1000.0


async def viewer(
    uri: str,
    viewer_id: int,
    slow: bool,
    stop: asyncio.Event,
    app_token: Optional[str],
    client_max_queue: int,
    client_max_message_bytes: int,
    slow_delay_seconds: float,
) -> ViewerResult:
    result = ViewerResult(viewer_id=viewer_id, slow=slow)
    while not stop.is_set():
        previous = None
        try:
            async with websockets.connect(
                uri,
                additional_headers=(
                    {"Authorization": "Bearer " + app_token}
                    if app_token
                    else None
                ),
                max_size=client_max_message_bytes,
                max_queue=client_max_queue,
                open_timeout=5.0,
                close_timeout=1.0,
            ) as socket:
                result.connections += 1
                if result.connections > 1:
                    result.reconnects += 1
                bootstrap = await asyncio.wait_for(socket.recv(), timeout=5.0)
                if not isinstance(bootstrap, str) or not bootstrap.startswith("INIT:"):
                    raise RuntimeError("missing ASCILINE bootstrap")
                while not stop.is_set():
                    try:
                        message = await asyncio.wait_for(socket.recv(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
                    if not isinstance(message, bytes):
                        continue
                    try:
                        sequence, previous = decode_frame(message, previous)
                    except Exception:
                        result.decode_errors += 1
                        previous = None
                        await socket.send(json.dumps({"type": "resync", "payload": {}}))
                        continue
                    if result.last_sequence is not None and sequence <= result.last_sequence:
                        result.sequence_regressions += 1
                    result.first_sequence = (
                        sequence if result.first_sequence is None else result.first_sequence
                    )
                    result.last_sequence = sequence
                    result.frames += 1
                    result.last_frame_sha256 = hashlib.sha256(previous).hexdigest()
                    if slow:
                        await asyncio.sleep(slow_delay_seconds)
        except Exception as exc:
            result.connection_errors += 1
            result.error = type(exc).__name__
            if stop.is_set():
                break
            await asyncio.sleep(0.25)
    return result


async def exercise_controls(
    base_url: str,
    duration: float,
    stop: asyncio.Event,
    app_token: Optional[str],
    media_token: Optional[str],
) -> Dict[str, Any]:
    source_epoch = "soak-{}".format(uuid.uuid4())
    source_id = "soak-controller-{}".format(uuid.uuid4())
    lease_id = "soak-lease-{}".format(uuid.uuid4())
    started = time.monotonic()
    sequence = 0
    prism_sequence = 0
    latencies = BoundedLatencyStats()
    command_errors: Deque[str] = deque(maxlen=100)
    command_error_count = 0
    next_action = 0.0
    next_speech = 0.0
    next_prism = 0.0
    airborne = False

    def record_latency(value: float) -> None:
        latencies.add(value)

    def record_error(code: str) -> None:
        nonlocal command_error_count
        command_error_count += 1
        command_errors.append(code)

    while not stop.is_set():
        elapsed = time.monotonic() - started
        if elapsed >= duration:
            break
        phase = elapsed % 16.0
        angle = elapsed * 0.72
        move_x = math.cos(angle)
        move_z = math.sin(angle)
        mobility_request = "keep"
        if not airborne and 4.0 <= phase < 4.15:
            airborne = True
            mobility_request = "takeoff"
        elif airborne and 13.0 <= phase < 13.15:
            airborne = False
            mobility_request = "land"
        ascend = 0.45 * math.sin(elapsed * 0.55) if airborne else 0.0
        control = {
            "command_id": "soak-control-{}".format(sequence),
            "source_id": source_id,
            "source_kind": "keyboard",
            "source_sequence": sequence,
            "source_epoch": source_epoch,
            "lease_id": lease_id,
            "ttl_ms": 250,
            "intent": {
                "move_x": move_x,
                "move_z": move_z,
                "ascend": ascend,
                "speed_mode": "run" if int(elapsed) % 7 < 2 else "walk",
                "mobility_request": mobility_request,
                "held_actions": [],
            },
        }
        sequence += 1
        try:
            response, latency = await request_json_async(
                "POST", base_url + "/api/avatar/wizard/control", control, app_token
            )
            record_latency(latency)
            if isinstance(response, dict) and response.get("ok") is False:
                record_error("control_rejected")
        except Exception as exc:
            record_error(type(exc).__name__)

        if elapsed >= next_action:
            action = ("thinking", "explaining", "pointing", "magic_cast", "reaction")[
                int(elapsed / 2.5) % 5
            ]
            try:
                _, latency = await request_json_async(
                    "POST",
                    base_url + "/api/avatar/wizard/action",
                    {"action": action, "duration_ms": 800},
                    app_token,
                )
                record_latency(latency)
            except Exception as exc:
                record_error(type(exc).__name__)
            next_action = elapsed + 2.5

        if elapsed >= next_speech:
            try:
                _, latency = await request_json_async(
                    "POST",
                    base_url + "/api/avatar/wizard/speak",
                    {
                        "speech_id": "soak-line-{}".format(int(elapsed)),
                        "text": "A deterministic local animation line.",
                        "duration_ms": 1200,
                    },
                    app_token,
                )
                record_latency(latency)
            except Exception as exc:
                record_error(type(exc).__name__)
            next_speech = elapsed + 5.0

        if elapsed >= next_prism:
            prism_sequence += 1
            now_ms = int(time.time() * 1000)
            try:
                _, latency = await request_json_async(
                    "POST",
                    base_url + "/api/avatar/wizard/prism-signal",
                    {
                        "schema_version": 1,
                        "event_id": str(uuid.uuid4()),
                        "source_epoch": source_epoch,
                        "source_sequence": prism_sequence,
                        "emitted_at_ms": now_ms,
                        "ttl_ms": 2000,
                        "kind": "stage",
                        "classification": "visual_advisory_only",
                        "provenance_class": "runtime_lifecycle",
                        "sanitization_version": 1,
                        "payload": {
                            "stage": ("listening", "drafting", "reviewing", "ready")[
                                prism_sequence % 4
                            ],
                            "status": "active",
                        },
                    },
                    media_token,
                )
                record_latency(latency)
            except Exception as exc:
                record_error(type(exc).__name__)
            next_prism = elapsed + 3.0

        await asyncio.sleep(0.1)

    release = {
        "command_id": "soak-control-{}".format(sequence),
        "source_id": source_id,
        "source_kind": "keyboard",
        "source_sequence": sequence,
        "source_epoch": source_epoch,
        "lease_id": lease_id,
        "ttl_ms": 250,
        "intent": {
            "move_x": 0.0,
            "move_z": 0.0,
            "ascend": 0.0,
            "speed_mode": "walk",
            "mobility_request": "land" if airborne else "keep",
            "held_actions": [],
        },
    }
    try:
        _, latency = await request_json_async(
            "POST", base_url + "/api/avatar/wizard/control", release, app_token
        )
        record_latency(latency)
    except Exception as exc:
        record_error(type(exc).__name__)
    return {
        "sent_control_count": sequence + 1,
        "sent_prism_count": prism_sequence,
        **latencies.to_mapping(),
        "command_error_count": command_error_count,
        "command_errors": list(command_errors),
    }


def percentile(values: Sequence[float], quantile: int) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(quantile / 100.0 * len(ordered)) - 1))
    return round(ordered[index], 3)


def read_process_rss_bytes(pid: int) -> int:
    """Read resident bytes for one local process without adding a dependency."""

    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("process PID must be a positive integer")
    status_path = Path("/proc") / str(pid) / "status"
    if status_path.is_file():
        for line in status_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                fields = line.split()
                if len(fields) >= 2 and fields[1].isdigit():
                    return int(fields[1]) * 1024
        raise RuntimeError("process RSS is absent from proc status")
    completed = subprocess.run(
        ["ps", "-o", "rss=", "-p", str(pid)],
        capture_output=True,
        check=False,
        text=True,
        timeout=2.0,
    )
    value = completed.stdout.strip()
    if completed.returncode != 0 or not value.isdigit():
        raise RuntimeError("process RSS is unavailable")
    return int(value) * 1024


def _mean(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _rss_slope_bytes_per_hour(samples: Sequence[RuntimeSample]) -> Optional[float]:
    points = [
        (sample.elapsed_seconds, float(sample.rss_bytes))
        for sample in samples
        if sample.rss_bytes is not None
    ]
    if len(points) < 2 or points[-1][0] <= points[0][0]:
        return None
    mean_time = sum(point[0] for point in points) / len(points)
    mean_rss = sum(point[1] for point in points) / len(points)
    denominator = sum((point[0] - mean_time) ** 2 for point in points)
    if denominator <= 0:
        return None
    slope_per_second = sum(
        (point[0] - mean_time) * (point[1] - mean_rss) for point in points
    ) / denominator
    return round(slope_per_second * 3600.0, 3)


def summarize_process_samples(
    samples: Sequence[RuntimeSample],
    warmup_seconds: float,
    total_sample_count: int,
) -> Dict[str, Any]:
    rss_samples = [sample for sample in samples if sample.rss_bytes is not None]
    stable = [sample for sample in rss_samples if sample.elapsed_seconds >= warmup_seconds]
    if len(stable) < 2:
        stable = rss_samples
    common = {
        "total_sample_count": total_sample_count,
        "retained_sample_count": len(samples),
        "dropped_sample_count": max(0, total_sample_count - len(samples)),
        "warmup_seconds": warmup_seconds,
    }
    if not stable:
        return {
            **common,
            "sample_count": 0,
            "baseline_rss_bytes": None,
            "final_rss_bytes": None,
            "minimum_rss_bytes": None,
            "peak_rss_bytes": None,
            "rss_growth_bytes": None,
            "peak_growth_bytes": None,
            "rss_slope_bytes_per_hour": None,
            "measurement_seconds": 0.0,
        }
    baseline = stable[0]
    final = stable[-1]
    rss_values = [int(sample.rss_bytes) for sample in stable if sample.rss_bytes is not None]
    return {
        **common,
        "sample_count": len(stable),
        "baseline_rss_bytes": baseline.rss_bytes,
        "final_rss_bytes": final.rss_bytes,
        "minimum_rss_bytes": min(rss_values),
        "peak_rss_bytes": max(rss_values),
        "rss_growth_bytes": int(final.rss_bytes) - int(baseline.rss_bytes),
        "peak_growth_bytes": max(rss_values) - int(baseline.rss_bytes),
        "rss_slope_bytes_per_hour": _rss_slope_bytes_per_hour(stable),
        "measurement_seconds": round(final.elapsed_seconds - baseline.elapsed_seconds, 3),
    }


def build_rolling_windows(
    samples: Sequence[RuntimeSample], window_seconds: float
) -> List[RollingWindow]:
    if window_seconds <= 0:
        raise ValueError("rolling window must be positive")
    ordered = sorted(samples, key=lambda item: item.elapsed_seconds)
    windows: List[RollingWindow] = []
    start_index = 0
    while start_index < len(ordered) - 1:
        start = ordered[start_index]
        end_index = start_index + 1
        while (
            end_index < len(ordered) - 1
            and ordered[end_index].elapsed_seconds - start.elapsed_seconds < window_seconds
        ):
            end_index += 1
        end = ordered[end_index]
        duration = end.elapsed_seconds - start.elapsed_seconds
        if duration <= 0:
            start_index += 1
            continue
        complete = duration >= window_seconds * 0.8
        if not complete and duration < min(5.0, window_seconds * 0.5):
            break
        members = ordered[start_index : end_index + 1]
        presentation = [
            float(sample.hub_window_fps)
            for sample in members
            if sample.hub_window_fps is not None
        ]
        if not presentation:
            presentation = [
                float(sample.hub_actual_fps)
                for sample in members
                if sample.hub_actual_fps is not None
            ]
        rss_start = next(
            (sample.rss_bytes for sample in members if sample.rss_bytes is not None), None
        )
        rss_end = next(
            (sample.rss_bytes for sample in reversed(members) if sample.rss_bytes is not None),
            None,
        )
        windows.append(
            RollingWindow(
                start_seconds=round(start.elapsed_seconds, 3),
                end_seconds=round(end.elapsed_seconds, 3),
                duration_seconds=round(duration, 3),
                complete=complete,
                simulation_hz=round(
                    (end.simulation_tick - start.simulation_tick) / duration, 3
                ),
                presentation_fps_min=(round(min(presentation), 3) if presentation else None),
                presentation_fps_mean=_mean(presentation),
                state_latency_ms_p95=percentile(
                    [sample.state_latency_ms for sample in members], 95
                ),
                event_loop_lag_ms_p95=percentile(
                    [sample.event_loop_lag_ms for sample in members], 95
                ),
                hub_queue_drops=end.hub_queue_drops - start.hub_queue_drops,
                schedule_overruns=end.schedule_overruns - start.schedule_overruns,
                rss_bytes_start=rss_start,
                rss_bytes_end=rss_end,
            )
        )
        start_index = end_index
    return windows


def optional_float(mapping: Dict[str, Any], key: str) -> Optional[float]:
    value = mapping.get(key)
    return None if value is None else round(float(value), 3)


async def _sample_runtime(
    base_url: str,
    app_token: Optional[str],
    pid: int,
    started: float,
    event_loop_lag_ms: float,
) -> RuntimeSample:
    state, latency = await request_json_async(
        "GET", base_url + "/api/avatar/wizard/state", bearer=app_token
    )
    rss_bytes = await asyncio.to_thread(read_process_rss_bytes, pid)
    diagnostics = state["diagnostics"]
    return RuntimeSample(
        elapsed_seconds=round(time.perf_counter() - started, 6),
        simulation_tick=int(state["state"]["simulation_tick"]),
        state_latency_ms=round(latency, 3),
        event_loop_lag_ms=round(max(0.0, event_loop_lag_ms), 3),
        hub_actual_fps=optional_float(diagnostics, "hub_actual_fps"),
        hub_window_fps=optional_float(diagnostics, "hub_window_fps"),
        hub_queue_drops=int(diagnostics.get("hub_queue_drops", 0)),
        schedule_overruns=int(diagnostics.get("schedule_overruns", 0)),
        rss_bytes=rss_bytes,
    )


async def monitor_runtime(
    base_url: str,
    app_token: Optional[str],
    pid: int,
    started: float,
    stop: asyncio.Event,
    interval_seconds: float,
    samples: Deque[RuntimeSample],
) -> Tuple[int, int, List[str]]:
    total_samples = 0
    error_count = 0
    errors: Deque[str] = deque(maxlen=100)
    deadline = time.perf_counter() + interval_seconds
    while not stop.is_set():
        delay = max(0.0, deadline - time.perf_counter())
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
            break
        except asyncio.TimeoutError:
            pass
        awakened = time.perf_counter()
        lag_ms = max(0.0, (awakened - deadline) * 1000.0)
        try:
            samples.append(
                await _sample_runtime(base_url, app_token, pid, started, lag_ms)
            )
            total_samples += 1
        except Exception as exc:
            error_count += 1
            errors.append(type(exc).__name__)
        deadline += interval_seconds
        if deadline < time.perf_counter() - interval_seconds:
            deadline = time.perf_counter() + interval_seconds
    return total_samples, error_count, list(errors)


def _is_local_loopback(parsed: urllib.parse.ParseResult) -> bool:
    return parsed.scheme in {"http", "https"} and parsed.hostname in {
        "127.0.0.1",
        "::1",
    }


async def resolve_server_pid(
    base_url: str, parsed: urllib.parse.ParseResult, explicit_pid: Optional[int]
) -> Tuple[int, Dict[str, Any]]:
    if not _is_local_loopback(parsed):
        raise RuntimeError("RSS sampling requires a literal local loopback URL")
    health, _ = await request_json_async("GET", base_url + "/api/companion/health")
    health_pid = health.get("pid")
    if isinstance(health_pid, bool) or not isinstance(health_pid, int) or health_pid <= 0:
        raise RuntimeError("health response does not expose a valid process PID")
    if explicit_pid is not None and explicit_pid != health_pid:
        raise RuntimeError("explicit process PID does not match the server health contract")
    return health_pid, health


async def run(args: argparse.Namespace) -> Dict[str, Any]:
    base_url = args.url.rstrip("/")
    parsed = urllib.parse.urlparse(base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_uri = "{}://{}{}".format(ws_scheme, parsed.netloc, "/ws/avatar/wizard?codec=adaptive")
    server_pid, health = await resolve_server_pid(base_url, parsed, args.server_pid)
    started = time.perf_counter()
    initial, initial_latency = await request_json_async(
        "GET", base_url + "/api/avatar/wizard/state", bearer=args.app_token
    )
    initial_tick = int(initial["state"]["simulation_tick"])
    initial_diagnostics = initial["diagnostics"]
    runtime_samples: Deque[RuntimeSample] = deque(maxlen=args.max_runtime_samples)
    runtime_samples.append(
        RuntimeSample(
            elapsed_seconds=round(time.perf_counter() - started, 6),
            simulation_tick=initial_tick,
            state_latency_ms=round(initial_latency, 3),
            event_loop_lag_ms=0.0,
            hub_actual_fps=optional_float(initial_diagnostics, "hub_actual_fps"),
            hub_window_fps=optional_float(initial_diagnostics, "hub_window_fps"),
            hub_queue_drops=int(initial_diagnostics.get("hub_queue_drops", 0)),
            schedule_overruns=int(initial_diagnostics.get("schedule_overruns", 0)),
            rss_bytes=await asyncio.to_thread(read_process_rss_bytes, server_pid),
        )
    )
    stop = asyncio.Event()
    monitor_task = asyncio.create_task(
        monitor_runtime(
            base_url,
            args.app_token,
            server_pid,
            started,
            stop,
            args.sample_interval_seconds,
            runtime_samples,
        )
    )
    viewer_tasks = [
        asyncio.create_task(
            viewer(
                ws_uri,
                index,
                args.slow_viewer and index == args.viewers - 1,
                stop,
                args.app_token,
                args.client_max_queue,
                args.client_max_message_bytes,
                args.slow_viewer_delay_seconds,
            )
        )
        for index in range(args.viewers)
    ]
    control_result = await exercise_controls(
        base_url,
        args.duration_seconds,
        stop,
        args.app_token,
        args.media_token,
    )
    control_elapsed = time.perf_counter() - started
    stop.set()
    monitored_sample_count, monitor_error_count, monitor_errors = await monitor_task
    viewers = await asyncio.gather(*viewer_tasks)
    final, final_latency = await request_json_async(
        "GET", base_url + "/api/avatar/wizard/state", bearer=args.app_token
    )
    elapsed = time.perf_counter() - started
    final_tick = int(final["state"]["simulation_tick"])
    final_diagnostics = final["diagnostics"]
    final_health, _ = await request_json_async("GET", base_url + "/api/companion/health")
    runtime_samples.append(
        RuntimeSample(
            elapsed_seconds=round(elapsed, 6),
            simulation_tick=final_tick,
            state_latency_ms=round(final_latency, 3),
            event_loop_lag_ms=0.0,
            hub_actual_fps=optional_float(final_diagnostics, "hub_actual_fps"),
            hub_window_fps=optional_float(final_diagnostics, "hub_window_fps"),
            hub_queue_drops=int(final_diagnostics.get("hub_queue_drops", 0)),
            schedule_overruns=int(final_diagnostics.get("schedule_overruns", 0)),
            rss_bytes=await asyncio.to_thread(read_process_rss_bytes, server_pid),
        )
    )
    retained_samples = list(runtime_samples)
    total_sample_count = monitored_sample_count + 2
    process_summary = summarize_process_samples(
        retained_samples,
        args.resource_warmup_seconds,
        total_sample_count,
    )
    rolling_windows = build_rolling_windows(
        retained_samples, args.rolling_window_seconds
    )
    complete_windows = [window for window in rolling_windows if window.complete]
    simulation_hz = (final_tick - initial_tick) / max(elapsed, 0.001)
    hub_queue_drops = int(final_diagnostics.get("hub_queue_drops", 0)) - int(
        initial_diagnostics.get("hub_queue_drops", 0)
    )
    schedule_overruns = int(final_diagnostics.get("schedule_overruns", 0)) - int(
        initial_diagnostics.get("schedule_overruns", 0)
    )
    schedule_overruns_per_minute = schedule_overruns / max(elapsed / 60.0, 0.001)
    hub_queue_drops_per_minute = hub_queue_drops / max(elapsed / 60.0, 0.001)

    failures = []
    for result in viewers:
        if result.connection_errors and not result.slow:
            failures.append(
                "viewer {} connection errors: {}".format(
                    result.viewer_id, result.connection_errors
                )
            )
        if result.slow:
            reconnects_per_minute = result.reconnects / max(elapsed / 60.0, 0.001)
            if reconnects_per_minute > args.max_slow_viewer_reconnects_per_minute:
                failures.append("slow viewer reconnect rate exceeded limit")
        if result.decode_errors:
            failures.append("viewer {} decode errors: {}".format(result.viewer_id, result.decode_errors))
        if result.sequence_regressions:
            failures.append(
                "viewer {} sequence regressions: {}".format(
                    result.viewer_id, result.sequence_regressions
                )
            )
        minimum_rate = 3.0 if result.slow else 18.0
        if result.frames < control_elapsed * minimum_rate:
            failures.append(
                "viewer {} frame rate below {} fps".format(result.viewer_id, minimum_rate)
            )
    if control_result["command_error_count"]:
        failures.append("command errors: {}".format(control_result["command_error_count"]))
    if (
        control_result["latency_ms_p95_upper_bound"] is None
        or control_result["latency_ms_p95_upper_bound"] > 100.0
    ):
        failures.append("command latency p95 exceeded 100 ms")
    if monitor_error_count:
        failures.append("runtime monitoring errors: {}".format(monitor_error_count))
    if final_health.get("status") != "ready" or not final_health.get("frame_hub_running"):
        failures.append("server health was not ready after the soak")
    if final_health.get("pid") != server_pid:
        failures.append("server PID changed during the soak")
    if final_health.get("runtime_epoch") != health.get("runtime_epoch"):
        failures.append("runtime epoch changed during the soak")
    if process_summary["sample_count"] < 2:
        failures.append("process RSS sampling is incomplete")
    if not 55.0 <= simulation_hz <= 65.0:
        failures.append("simulation cadence outside 60 Hz tolerance: {:.3f}".format(simulation_hz))
    presentation_fps = final_diagnostics.get(
        "hub_window_fps", final_diagnostics.get("hub_actual_fps")
    )
    if presentation_fps is None:
        failures.append("presentation cadence diagnostic is unavailable")
    elif not 21.0 <= float(presentation_fps) <= 27.0:
        failures.append(
            "presentation cadence outside 24 fps tolerance: {:.3f}".format(
                float(presentation_fps)
            )
        )
    allowed_drop_rate = args.max_hub_queue_drops_per_minute if args.slow_viewer else 0.0
    if hub_queue_drops_per_minute > allowed_drop_rate:
        failures.append("hub queue drop rate exceeded limit")
    if schedule_overruns_per_minute > args.max_schedule_overruns_per_minute:
        failures.append(
            "schedule overruns exceeded {:.3f} per minute".format(
                args.max_schedule_overruns_per_minute
            )
        )

    if args.duration_seconds >= args.rolling_window_seconds and not complete_windows:
        failures.append("rolling cadence windows are unavailable")
    if complete_windows:
        bad_simulation = sum(
            not 55.0 <= window.simulation_hz <= 65.0 for window in complete_windows
        )
        bad_presentation = sum(
            window.presentation_fps_mean is None
            or not 21.0 <= float(window.presentation_fps_mean) <= 27.0
            for window in complete_windows
        )
        simulation_breach_fraction = bad_simulation / len(complete_windows)
        presentation_breach_fraction = bad_presentation / len(complete_windows)
        if simulation_breach_fraction > args.max_rolling_breach_fraction:
            failures.append("rolling simulation cadence breach fraction exceeded limit")
        if presentation_breach_fraction > args.max_rolling_breach_fraction:
            failures.append("rolling presentation cadence breach fraction exceeded limit")
    else:
        simulation_breach_fraction = None
        presentation_breach_fraction = None

    loop_lag_p95 = percentile(
        [sample.event_loop_lag_ms for sample in retained_samples], 95
    )
    if loop_lag_p95 is None or loop_lag_p95 > args.max_event_loop_lag_p95_ms:
        failures.append("event-loop monitor lag p95 exceeded limit")

    maximum_growth_bytes = int(args.max_rss_growth_mib * 1024 * 1024)
    peak_growth = process_summary["peak_growth_bytes"]
    if peak_growth is None or peak_growth > maximum_growth_bytes:
        failures.append("process RSS peak growth exceeded limit")
    slope = process_summary["rss_slope_bytes_per_hour"]
    if (
        process_summary["measurement_seconds"] >= args.min_rss_slope_duration_seconds
        and (
            slope is None
            or slope > args.max_rss_slope_mib_per_hour * 1024 * 1024
        )
    ):
        failures.append("process RSS growth slope exceeded limit")

    return {
        "schema_version": 2,
        "result": "passed" if not failures else "failed",
        "architecture": "asciline_python",
        "url": base_url,
        "server_process": {
            "pid": server_pid,
            "runtime_epoch": health.get("runtime_epoch"),
            "initial_health_status": health.get("status"),
            "initial_frame_hub_running": health.get("frame_hub_running"),
            "final_health_status": final_health.get("status"),
            "final_frame_hub_running": final_health.get("frame_hub_running"),
        },
        "duration_requested_seconds": args.duration_seconds,
        "duration_actual_seconds": round(elapsed, 3),
        "control_window_actual_seconds": round(control_elapsed, 3),
        "viewer_count": args.viewers,
        "slow_viewer_enabled": args.slow_viewer,
        "transport_limits": {
            "client_max_queue": args.client_max_queue,
            "client_max_message_bytes": args.client_max_message_bytes,
            "slow_viewer_delay_seconds": args.slow_viewer_delay_seconds,
        },
        "strict_thresholds": {
            "rolling_window_seconds": args.rolling_window_seconds,
            "sample_interval_seconds": args.sample_interval_seconds,
            "max_rolling_breach_fraction": args.max_rolling_breach_fraction,
            "max_event_loop_lag_p95_ms": args.max_event_loop_lag_p95_ms,
            "max_schedule_overruns_per_minute": args.max_schedule_overruns_per_minute,
            "max_hub_queue_drops_per_minute": args.max_hub_queue_drops_per_minute,
            "max_slow_viewer_reconnects_per_minute": args.max_slow_viewer_reconnects_per_minute,
            "max_rss_growth_mib": args.max_rss_growth_mib,
            "max_rss_slope_mib_per_hour": args.max_rss_slope_mib_per_hour,
            "min_rss_slope_duration_seconds": args.min_rss_slope_duration_seconds,
        },
        "simulation_hz": round(simulation_hz, 3),
        "initial_tick": initial_tick,
        "final_tick": final_tick,
        "initial_hub_actual_fps": optional_float(initial_diagnostics, "hub_actual_fps"),
        "final_hub_actual_fps": optional_float(final_diagnostics, "hub_actual_fps"),
        "initial_hub_window_fps": optional_float(initial_diagnostics, "hub_window_fps"),
        "final_hub_window_fps": optional_float(final_diagnostics, "hub_window_fps"),
        "hub_queue_drops": hub_queue_drops,
        "hub_queue_drops_per_minute": round(hub_queue_drops_per_minute, 3),
        "schedule_overruns": schedule_overruns,
        "schedule_overruns_per_minute": round(schedule_overruns_per_minute, 3),
        "event_loop_lag_ms_p95": loop_lag_p95,
        "runtime_monitor_error_count": monitor_error_count,
        "runtime_monitor_errors": monitor_errors,
        "process_memory": process_summary,
        "rolling_summary": {
            "window_count": len(rolling_windows),
            "complete_window_count": len(complete_windows),
            "simulation_breach_fraction": (
                round(simulation_breach_fraction, 6)
                if simulation_breach_fraction is not None
                else None
            ),
            "presentation_breach_fraction": (
                round(presentation_breach_fraction, 6)
                if presentation_breach_fraction is not None
                else None
            ),
        },
        "runtime_samples": [asdict(sample) for sample in retained_samples],
        "rolling_windows": [asdict(window) for window in rolling_windows],
        "control": control_result,
        "viewers": [asdict(result) for result in viewers],
        "final_state": {
            "world_position": final["state"]["world_position"],
            "airborne": final["state"]["airborne"],
            "altitude": final["state"]["altitude"],
            "semantic_cue": final["state"]["semantic_cue"],
        },
        "failures": failures,
    }


def write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Soak the live ASCILINE Python avatar service")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--duration-seconds", type=float, default=30.0)
    parser.add_argument("--viewers", type=int, default=4)
    parser.add_argument("--slow-viewer", action="store_true")
    parser.add_argument("--server-pid", type=int)
    parser.add_argument("--client-max-queue", type=int, default=2)
    parser.add_argument("--client-max-message-bytes", type=int, default=2 * 1024 * 1024)
    parser.add_argument("--slow-viewer-delay-seconds", type=float, default=0.12)
    parser.add_argument("--sample-interval-seconds", type=float, default=5.0)
    parser.add_argument("--rolling-window-seconds", type=float, default=30.0)
    parser.add_argument("--resource-warmup-seconds", type=float, default=30.0)
    parser.add_argument("--max-runtime-samples", type=int, default=20000)
    parser.add_argument("--max-rolling-breach-fraction", type=float, default=0.05)
    parser.add_argument("--max-event-loop-lag-p95-ms", type=float, default=250.0)
    parser.add_argument("--max-schedule-overruns-per-minute", type=float, default=60.0)
    parser.add_argument("--max-hub-queue-drops-per-minute", type=float, default=1500.0)
    parser.add_argument("--max-slow-viewer-reconnects-per-minute", type=float, default=6.0)
    parser.add_argument("--max-rss-growth-mib", type=float, default=64.0)
    parser.add_argument("--max-rss-slope-mib-per-hour", type=float, default=8.0)
    parser.add_argument("--min-rss-slope-duration-seconds", type=float, default=600.0)
    parser.add_argument(
        "--app-token",
        default=os.environ.get("WIZARD_COMPANION_APP_TOKEN"),
        help="Companion app bearer; defaults to WIZARD_COMPANION_APP_TOKEN.",
    )
    parser.add_argument(
        "--media-token",
        default=os.environ.get("WIZARD_MEDIA_CONNECTOR_TOKEN"),
        help="Prism relay bearer; defaults to WIZARD_MEDIA_CONNECTOR_TOKEN.",
    )
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0 < args.duration_seconds <= 86400:
        parser.error("--duration-seconds must be between 0 and 86400")
    if args.viewers < 1:
        parser.error("--viewers must be at least 1")
    if args.server_pid is not None and args.server_pid <= 0:
        parser.error("--server-pid must be positive")
    if not 1 <= args.client_max_queue <= 64:
        parser.error("--client-max-queue must be between 1 and 64")
    if not 1024 <= args.client_max_message_bytes <= 16 * 1024 * 1024:
        parser.error("--client-max-message-bytes must be between 1024 and 16777216")
    if not 0.05 <= args.slow_viewer_delay_seconds <= 2.0:
        parser.error("--slow-viewer-delay-seconds must be between 0.05 and 2")
    if not 0.25 <= args.sample_interval_seconds <= 60.0:
        parser.error("--sample-interval-seconds must be between 0.25 and 60")
    if args.rolling_window_seconds < args.sample_interval_seconds * 2:
        parser.error("--rolling-window-seconds must span at least two samples")
    if not 0 <= args.resource_warmup_seconds <= args.duration_seconds:
        parser.error("--resource-warmup-seconds must be within the soak duration")
    if not 10 <= args.max_runtime_samples <= 100000:
        parser.error("--max-runtime-samples must be between 10 and 100000")
    required_samples = math.ceil(args.duration_seconds / args.sample_interval_seconds) + 2
    if args.max_runtime_samples < required_samples:
        parser.error(
            "--max-runtime-samples must retain every requested interval (need {})".format(
                required_samples
            )
        )
    if not 0 <= args.max_rolling_breach_fraction <= 1:
        parser.error("--max-rolling-breach-fraction must be between 0 and 1")
    for name in (
        "max_event_loop_lag_p95_ms",
        "max_schedule_overruns_per_minute",
        "max_hub_queue_drops_per_minute",
        "max_slow_viewer_reconnects_per_minute",
        "max_rss_growth_mib",
        "max_rss_slope_mib_per_hour",
        "min_rss_slope_duration_seconds",
    ):
        if getattr(args, name) < 0:
            parser.error("--{} must be nonnegative".format(name.replace("_", "-")))
    return args


def main() -> int:
    args = parse_args()
    result = asyncio.run(run(args))
    if args.output:
        write_json_atomic(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if args.strict and result["result"] != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
