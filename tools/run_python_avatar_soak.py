#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import websockets

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.protocol import decode_frame


@dataclass
class ViewerResult:
    viewer_id: int
    slow: bool
    frames: int = 0
    sequence_regressions: int = 0
    decode_errors: int = 0
    first_sequence: Optional[int] = None
    last_sequence: Optional[int] = None
    last_frame_sha256: Optional[str] = None
    error: Optional[str] = None


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
) -> ViewerResult:
    result = ViewerResult(viewer_id=viewer_id, slow=slow)
    previous = None
    try:
        async with websockets.connect(
            uri,
            additional_headers=(
                {"Authorization": "Bearer " + app_token}
                if app_token
                else None
            ),
            max_size=None,
            max_queue=None,
            open_timeout=5.0,
            close_timeout=1.0,
        ) as socket:
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
                result.first_sequence = sequence if result.first_sequence is None else result.first_sequence
                result.last_sequence = sequence
                result.frames += 1
                result.last_frame_sha256 = hashlib.sha256(previous).hexdigest()
                if slow:
                    await asyncio.sleep(0.24)
    except Exception as exc:
        result.error = "{}: {}".format(type(exc).__name__, exc)
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
    latencies: List[float] = []
    command_errors: List[str] = []
    next_action = 0.0
    next_speech = 0.0
    next_prism = 0.0
    airborne = False

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
            latencies.append(latency)
            if isinstance(response, dict) and response.get("ok") is False:
                command_errors.append(str(response.get("message", "control rejected")))
        except Exception as exc:
            command_errors.append(str(exc))

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
                latencies.append(latency)
            except Exception as exc:
                command_errors.append(str(exc))
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
                latencies.append(latency)
            except Exception as exc:
                command_errors.append(str(exc))
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
                latencies.append(latency)
            except Exception as exc:
                command_errors.append(str(exc))
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
        latencies.append(latency)
    except Exception as exc:
        command_errors.append(str(exc))
    return {
        "sent_control_count": sequence + 1,
        "sent_prism_count": prism_sequence,
        "request_count": len(latencies),
        "latency_ms_p50": percentile(latencies, 50),
        "latency_ms_p95": percentile(latencies, 95),
        "latency_ms_max": max(latencies) if latencies else None,
        "command_errors": command_errors,
    }


def percentile(values: List[float], quantile: int) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(quantile / 100.0 * len(ordered)) - 1))
    return round(ordered[index], 3)


def optional_float(mapping: Dict[str, Any], key: str) -> Optional[float]:
    value = mapping.get(key)
    return None if value is None else round(float(value), 3)


async def run(args: argparse.Namespace) -> Dict[str, Any]:
    base_url = args.url.rstrip("/")
    parsed = urllib.parse.urlparse(base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_uri = "{}://{}{}".format(ws_scheme, parsed.netloc, "/ws/avatar/wizard?codec=adaptive")
    initial, _ = await request_json_async(
        "GET", base_url + "/api/avatar/wizard/state", bearer=args.app_token
    )
    initial_tick = int(initial["state"]["simulation_tick"])
    initial_diagnostics = initial["diagnostics"]
    stop = asyncio.Event()
    viewer_tasks = [
        asyncio.create_task(
            viewer(
                ws_uri,
                index,
                args.slow_viewer and index == args.viewers - 1,
                stop,
                args.app_token,
            )
        )
        for index in range(args.viewers)
    ]
    started = time.perf_counter()
    control_result = await exercise_controls(
        base_url,
        args.duration_seconds,
        stop,
        args.app_token,
        args.media_token,
    )
    control_elapsed = time.perf_counter() - started
    stop.set()
    viewers = await asyncio.gather(*viewer_tasks)
    final, _ = await request_json_async(
        "GET", base_url + "/api/avatar/wizard/state", bearer=args.app_token
    )
    elapsed = time.perf_counter() - started
    final_tick = int(final["state"]["simulation_tick"])
    final_diagnostics = final["diagnostics"]
    simulation_hz = (final_tick - initial_tick) / max(elapsed, 0.001)

    failures = []
    for result in viewers:
        if result.error:
            failures.append("viewer {} error: {}".format(result.viewer_id, result.error))
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
    if control_result["command_errors"]:
        failures.append("command errors: {}".format(len(control_result["command_errors"])))
    if control_result["latency_ms_p95"] is None or control_result["latency_ms_p95"] > 100.0:
        failures.append("command latency p95 exceeded 100 ms")
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

    return {
        "schema_version": 1,
        "result": "passed" if not failures else "failed",
        "architecture": "asciline_python",
        "url": base_url,
        "duration_requested_seconds": args.duration_seconds,
        "duration_actual_seconds": round(elapsed, 3),
        "control_window_actual_seconds": round(control_elapsed, 3),
        "viewer_count": args.viewers,
        "slow_viewer_enabled": args.slow_viewer,
        "simulation_hz": round(simulation_hz, 3),
        "initial_tick": initial_tick,
        "final_tick": final_tick,
        "initial_hub_actual_fps": optional_float(initial_diagnostics, "hub_actual_fps"),
        "final_hub_actual_fps": optional_float(final_diagnostics, "hub_actual_fps"),
        "initial_hub_window_fps": optional_float(initial_diagnostics, "hub_window_fps"),
        "final_hub_window_fps": optional_float(final_diagnostics, "hub_window_fps"),
        "hub_queue_drops": int(final_diagnostics.get("hub_queue_drops", 0))
        - int(initial_diagnostics.get("hub_queue_drops", 0)),
        "schedule_overruns": int(final_diagnostics.get("schedule_overruns", 0))
        - int(initial_diagnostics.get("schedule_overruns", 0)),
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
    if args.duration_seconds <= 0:
        parser.error("--duration-seconds must be positive")
    if args.viewers < 1:
        parser.error("--viewers must be at least 1")
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
