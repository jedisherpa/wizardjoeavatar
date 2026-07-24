#!/usr/bin/env python3
"""Record a deterministic real-browser layout pass for Character Director review."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import math
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional, Sequence, Tuple

import websockets

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.commanding import COMMAND_KINDS

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SCHEMA = "character_director_browser_layout_v1"
SOURCE_ID = "character-director-browser-review"
SCENARIO_PROGRAM_V1 = ("character_director_scenario_program_v1", 1)
SCENARIO_PROGRAM_V2 = ("character_director_scenario_program_v2", 2)
SCENARIO_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ACCEPTANCE_SCENARIO_RE = re.compile(r"^V(?:[1-9]|10)$")


class BrowserCaptureFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class BrowserCommand:
    name: str
    kind: str
    payload: Dict[str, Any]
    at_frame: Optional[int] = None

    def to_mapping(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class BrowserScenario:
    command: BrowserCommand
    settle_seconds: float
    capture_frames: int
    scheduled_commands: Tuple[BrowserCommand, ...] = ()


@dataclass(frozen=True)
class BrowserScenarioProgram:
    schema: str
    schema_version: int
    scenarios: Tuple[BrowserScenario, ...]

    @property
    def expected_frame_count(self) -> int:
        return sum(scenario.capture_frames for scenario in self.scenarios)


def _finite_number(value: object, field: str, allow_zero: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BrowserCaptureFailure("{} must be a finite number".format(field))
    result = float(value)
    if not math.isfinite(result) or result < 0 or (not allow_zero and result == 0):
        qualifier = "nonnegative" if allow_zero else "positive"
        raise BrowserCaptureFailure("{} must be {}".format(field, qualifier))
    return result


def _positive_integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BrowserCaptureFailure("{} must be a positive integer".format(field))
    return value


def _json_object(value: object, field: str) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BrowserCaptureFailure("{} must be an object".format(field))
    try:
        encoded = json.dumps(value, allow_nan=False, separators=(",", ":"))
        decoded = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise BrowserCaptureFailure(
            "{} must contain only finite JSON values".format(field)
        ) from exc
    if not isinstance(decoded, dict) or any(not isinstance(key, str) for key in value):
        raise BrowserCaptureFailure("{} keys must be strings".format(field))
    return decoded


def _browser_command(
    value: Mapping[str, Any],
    required: set,
    field: str,
    at_frame: Optional[int] = None,
) -> BrowserCommand:
    supplied = set(value)
    if supplied != required:
        raise BrowserCaptureFailure(
            "{} schema mismatch; missing={} unknown={}".format(
                field,
                sorted(required - supplied),
                sorted(supplied - required),
            )
        )
    name = value["name"]
    kind = value["kind"]
    if not isinstance(name, str) or not SCENARIO_NAME_RE.fullmatch(name):
        raise BrowserCaptureFailure(
            "{} name must be a lowercase kebab-case identifier".format(field)
        )
    if not isinstance(kind, str) or kind not in COMMAND_KINDS:
        raise BrowserCaptureFailure(
            "unsupported {} command kind: {}".format(field, kind)
        )
    return BrowserCommand(
        name=name,
        kind=kind,
        payload=_json_object(value["payload"], "{} payload".format(field)),
        at_frame=at_frame,
    )


def parse_browser_scenario_program(
    program: object,
    fps: float,
) -> BrowserScenarioProgram:
    fps = _finite_number(fps, "fps", allow_zero=False)
    required = {
        "schema",
        "schema_version",
        "program_id",
        "acceptance_scenario",
        "scenarios",
    }
    if not isinstance(program, Mapping) or set(program) != required:
        supplied = set(program) if isinstance(program, Mapping) else set()
        raise BrowserCaptureFailure(
            "scenario program schema mismatch; missing={} unknown={}".format(
                sorted(required - supplied),
                sorted(supplied - required),
            )
        )
    schema = program["schema"]
    schema_version = program["schema_version"]
    if (
        not isinstance(schema, str)
        or isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
    ):
        raise BrowserCaptureFailure("unsupported scenario program schema or version")
    schema_pair = (schema, schema_version)
    if schema_pair not in {SCENARIO_PROGRAM_V1, SCENARIO_PROGRAM_V2}:
        raise BrowserCaptureFailure("unsupported scenario program schema or version")
    if (
        not isinstance(program["program_id"], str)
        or not SCENARIO_NAME_RE.fullmatch(program["program_id"])
    ):
        raise BrowserCaptureFailure(
            "scenario program_id must be a lowercase kebab-case identifier"
        )
    if (
        not isinstance(program["acceptance_scenario"], str)
        or not ACCEPTANCE_SCENARIO_RE.fullmatch(program["acceptance_scenario"])
    ):
        raise BrowserCaptureFailure("acceptance_scenario must be V1 through V10")
    raw_scenarios = program["scenarios"]
    if (
        isinstance(raw_scenarios, (str, bytes))
        or not isinstance(raw_scenarios, Sequence)
        or not raw_scenarios
    ):
        raise BrowserCaptureFailure("scenarios must be a non-empty sequence")

    scenarios = []
    scenario_names = set()
    for scenario_index, value in enumerate(raw_scenarios):
        field = "scenario {}".format(scenario_index)
        if not isinstance(value, Mapping):
            raise BrowserCaptureFailure("{} must be an object".format(field))
        if schema_pair == SCENARIO_PROGRAM_V1:
            command = _browser_command(
                value,
                {"name", "kind", "payload", "settle_seconds", "capture_seconds"},
                field,
            )
            settle_seconds = _finite_number(
                value["settle_seconds"],
                "{} settle_seconds".format(field),
                allow_zero=True,
            )
            capture_seconds = _finite_number(
                value["capture_seconds"],
                "{} capture_seconds".format(field),
                allow_zero=False,
            )
            capture_frames = max(1, int(round(capture_seconds * fps)))
            scheduled_commands: Tuple[BrowserCommand, ...] = ()
        else:
            command = _browser_command(
                value,
                {"name", "kind", "payload", "timing"},
                field,
            )
            timing = value["timing"]
            if not isinstance(timing, Mapping):
                raise BrowserCaptureFailure("{} timing must be an object".format(field))
            if set(timing) not in (
                {"capture_frames"},
                {"capture_frames", "scheduled_commands"},
            ):
                raise BrowserCaptureFailure(
                    "{} v2 timing supports only capture_frames with optional "
                    "scheduled_commands".format(field)
                )
            capture_frames = _positive_integer(
                timing["capture_frames"],
                "{} timing.capture_frames".format(field),
            )
            settle_seconds = 0.0
            scheduled_values = timing.get("scheduled_commands", ())
            if "scheduled_commands" in timing and (
                isinstance(scheduled_values, (str, bytes))
                or not isinstance(scheduled_values, Sequence)
                or not scheduled_values
            ):
                raise BrowserCaptureFailure(
                    "{} timing.scheduled_commands must be a non-empty sequence".format(
                        field
                    )
                )
            parsed_scheduled = []
            scheduled_names = set()
            previous_frame = 0
            for command_index, scheduled in enumerate(scheduled_values):
                command_field = "{} scheduled command {}".format(field, command_index)
                if not isinstance(scheduled, Mapping):
                    raise BrowserCaptureFailure(
                        "{} must be an object".format(command_field)
                    )
                at_frame = scheduled.get("at_frame")
                if (
                    isinstance(at_frame, bool)
                    or not isinstance(at_frame, int)
                    or at_frame <= previous_frame
                    or at_frame >= capture_frames
                ):
                    raise BrowserCaptureFailure(
                        "{} at_frame values must be strictly increasing within "
                        "the capture".format(field)
                    )
                parsed = _browser_command(
                    scheduled,
                    {"name", "at_frame", "kind", "payload"},
                    command_field,
                    at_frame=at_frame,
                )
                if parsed.name in scheduled_names:
                    raise BrowserCaptureFailure(
                        "{} scheduled command names must be unique".format(field)
                    )
                scheduled_names.add(parsed.name)
                previous_frame = at_frame
                parsed_scheduled.append(parsed)
            scheduled_commands = tuple(parsed_scheduled)

        if command.name in scenario_names:
            raise BrowserCaptureFailure("scenario names must be unique")
        scenario_names.add(command.name)
        scenarios.append(
            BrowserScenario(
                command=command,
                settle_seconds=settle_seconds,
                capture_frames=capture_frames,
                scheduled_commands=scheduled_commands,
            )
        )
    return BrowserScenarioProgram(
        schema=schema,
        schema_version=schema_version,
        scenarios=tuple(scenarios),
    )


def scenario_capture_events(
    scenario: BrowserScenario,
) -> Iterator[Tuple[int, Optional[BrowserCommand]]]:
    scheduled_by_frame = {
        command.at_frame: command for command in scenario.scheduled_commands
    }
    for frame_offset in range(1, scenario.capture_frames + 1):
        yield frame_offset, None
        scheduled = scheduled_by_frame.get(frame_offset)
        if scheduled is not None:
            yield frame_offset, scheduled


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def get_json(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=2.0) as response:
        return json.loads(response.read().decode("utf-8"))


class CDPClient:
    def __init__(self, websocket_url: str) -> None:
        self.websocket_url = websocket_url
        self.websocket = None
        self.reader = None
        self.next_id = 1
        self.pending: Dict[int, asyncio.Future] = {}
        self.latest_screencast: Optional[bytes] = None
        self.latest_screencast_sequence = 0
        self.screencast_event = asyncio.Event()
        self.console_events = []
        self.page_errors = []
        self.network_requests = []
        self.network_responses = []
        self.network_failures = []

    async def connect(self) -> None:
        self.websocket = await websockets.connect(
            self.websocket_url,
            open_timeout=5.0,
            max_size=32 * 1024 * 1024,
        )
        self.reader = asyncio.create_task(self._read())

    async def close(self) -> None:
        if self.websocket is not None:
            await self.websocket.close()
        if self.reader is not None:
            await asyncio.gather(self.reader, return_exceptions=True)

    async def _read(self) -> None:
        assert self.websocket is not None
        async for raw in self.websocket:
            message = json.loads(raw)
            response_id = message.get("id")
            if isinstance(response_id, int):
                future = self.pending.pop(response_id, None)
                if future is not None and not future.done():
                    if "error" in message:
                        future.set_exception(BrowserCaptureFailure(str(message["error"])))
                    else:
                        future.set_result(message.get("result", {}))
                continue
            method = message.get("method")
            params = message.get("params", {})
            if method == "Page.screencastFrame":
                self.latest_screencast = base64.b64decode(params["data"])
                self.latest_screencast_sequence += 1
                self.screencast_event.set()
                await self.notify(
                    "Page.screencastFrameAck",
                    {"sessionId": params["sessionId"]},
                )
            elif method == "Runtime.consoleAPICalled":
                self.console_events.append(params)
            elif method == "Runtime.exceptionThrown":
                self.page_errors.append(params)
            elif method == "Log.entryAdded":
                entry = params.get("entry", {})
                if entry.get("level") in {"error", "warning"}:
                    self.console_events.append(params)
            elif method == "Network.requestWillBeSent":
                self.network_requests.append(params)
                self.network_requests = self.network_requests[-200:]
            elif method == "Network.responseReceived":
                self.network_responses.append(params)
                self.network_responses = self.network_responses[-200:]
            elif method == "Network.loadingFailed":
                self.network_failures.append(params)
                self.network_failures = self.network_failures[-200:]

    async def command(self, method: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        if self.websocket is None:
            raise BrowserCaptureFailure("CDP client is not connected")
        message_id = self.next_id
        self.next_id += 1
        future = asyncio.get_running_loop().create_future()
        self.pending[message_id] = future
        await self.websocket.send(
            json.dumps({"id": message_id, "method": method, "params": dict(params or {})})
        )
        return await asyncio.wait_for(future, timeout=10.0)

    async def notify(self, method: str, params: Optional[Mapping[str, Any]] = None) -> None:
        if self.websocket is None:
            return
        message_id = self.next_id
        self.next_id += 1
        await self.websocket.send(
            json.dumps({"id": message_id, "method": method, "params": dict(params or {})})
        )

    async def evaluate(self, expression: str) -> Any:
        result = await self.command(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
            },
        )
        value = result.get("result", {})
        if value.get("subtype") == "error":
            raise BrowserCaptureFailure("browser evaluation failed: {}".format(value))
        return value.get("value")


async def wait_for_page_target(port: int, timeout: float = 10.0) -> str:
    deadline = time.monotonic() + timeout
    list_url = "http://127.0.0.1:{}/json/list".format(port)
    while time.monotonic() < deadline:
        try:
            targets = await asyncio.to_thread(get_json, list_url)
            for target in targets:
                if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                    return str(target["webSocketDebuggerUrl"])
        except Exception:
            pass
        await asyncio.sleep(0.1)
    raise BrowserCaptureFailure("Chrome DevTools page target did not become ready")


async def wait_for_wizard(cdp: CDPClient, timeout: float = 10.0) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        metrics = await cdp.evaluate(
            "typeof window.__wizardJoeMetrics === 'function' ? window.__wizardJoeMetrics() : null"
        )
        if (
            isinstance(metrics, dict)
            and metrics.get("presentedFrames", 0) >= 2
            and metrics.get("canvas", {}).get("cols", 0) > 0
        ):
            return metrics
        await asyncio.sleep(0.1)
    raise BrowserCaptureFailure("browser wizard canvas did not present frames")


async def post_browser_command(
    cdp: CDPClient,
    source_epoch: str,
    source_sequence: int,
    scenario: Mapping[str, Any],
) -> Dict[str, Any]:
    command_id = "{}-{:04d}-{}".format(
        source_epoch,
        source_sequence,
        scenario["name"],
    )
    envelope = {
        "schema_version": 1,
        "command_id": command_id,
        "source_id": SOURCE_ID,
        "source_kind": "api",
        "source_sequence": source_sequence,
        "source_epoch": source_epoch,
        "kind": scenario["kind"],
        "payload": scenario["payload"],
        "priority_class": "user",
    }
    expression = """
      fetch('/api/avatar/wizard/command', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(%s)
      }).then(async response => ({status: response.status, body: await response.json()}))
    """ % json.dumps(envelope, separators=(",", ":"))
    started = time.perf_counter()
    result = await cdp.evaluate(expression)
    if not isinstance(result, dict) or result.get("status") != 200:
        raise BrowserCaptureFailure("browser command failed: {}".format(result))
    ack = result.get("body", {}).get("ack")
    if not isinstance(ack, dict) or ack.get("disposition") != "applied":
        raise BrowserCaptureFailure("browser command was not applied: {}".format(result))
    return {
        "scenario": scenario["name"],
        "command_id": command_id,
        "source_sequence": source_sequence,
        "kind": scenario["kind"],
        "payload": scenario["payload"],
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "ack": ack,
    }


async def capture_browser_layout(
    capture_manifest_path: Path,
    output_video: Path,
    output_metrics: Path,
    width: int,
    height: int,
    device_scale_factor: float = 1.0,
    mobile: bool = False,
    profile: str = "desktop-dpr1",
) -> None:
    manifest = json.loads(capture_manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("valid"):
        raise BrowserCaptureFailure("browser proof requires a valid atomic capture manifest")
    base_url = manifest.get("runtime_binding", {}).get("base_url")
    if not isinstance(base_url, str) or not base_url.startswith("http"):
        raise BrowserCaptureFailure("capture manifest has no browser-safe runtime URL")
    if ":8765" in base_url:
        raise BrowserCaptureFailure("browser proof must not contact protected port 8765")
    scenario_path = capture_manifest_path.parent / "scenario-program.json"
    fps = float(manifest["init"]["fps"])
    program = parse_browser_scenario_program(
        json.loads(scenario_path.read_text(encoding="utf-8")),
        fps,
    )
    expected_frames = program.expected_frame_count
    if not CHROME.is_file():
        raise BrowserCaptureFailure("Google Chrome is required for browser layout proof")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise BrowserCaptureFailure("ffmpeg is required for browser layout proof")

    port = free_loopback_port()
    source_epoch = "browser-layout-{}".format(uuid.uuid4().hex)
    output_video.parent.mkdir(parents=True, exist_ok=True)
    output_metrics.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wizard-browser-layout-") as temporary:
        temporary_path = Path(temporary)
        frames_dir = temporary_path / "frames"
        frames_dir.mkdir()
        chrome_log = temporary_path / "chrome.log"
        with chrome_log.open("wb") as log_stream:
            process = subprocess.Popen(
                (
                    str(CHROME),
                    "--headless=new",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--hide-scrollbars",
                    "--remote-debugging-address=127.0.0.1",
                    "--remote-debugging-port={}".format(port),
                    "--user-data-dir={}".format(temporary_path / "profile"),
                    "--window-size={},{}".format(width, height),
                    "--force-device-scale-factor=1",
                    base_url + "/",
                ),
                cwd=str(ROOT),
                stdout=log_stream,
                stderr=subprocess.STDOUT,
            )
            cdp = None
            started_at = utc_now()
            commands = []
            sampled_sequences = []
            try:
                websocket_url = await wait_for_page_target(port)
                cdp = CDPClient(websocket_url)
                await cdp.connect()
                await cdp.command("Page.enable")
                await cdp.command("Runtime.enable")
                await cdp.command("Log.enable")
                await cdp.command(
                    "Emulation.setDeviceMetricsOverride",
                    {
                        "width": width,
                        "height": height,
                        "deviceScaleFactor": device_scale_factor,
                        "mobile": mobile,
                        "screenWidth": width,
                        "screenHeight": height,
                        "positionX": 0,
                        "positionY": 0,
                    },
                )
                await cdp.command("Page.reload", {"ignoreCache": True})
                await cdp.command("Page.bringToFront")
                initial_metrics = await wait_for_wizard(cdp)
                layout = await cdp.evaluate(
                    """
                    (() => {
                      const rect = element => {
                        const value = element.getBoundingClientRect();
                        return {x:value.x,y:value.y,width:value.width,height:value.height};
                      };
                      const canvas = document.querySelector('#wizard-canvas');
                      const context = canvas.getContext('2d');
                      return {
                        viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},
                        visualViewport:window.visualViewport ? {
                          width:window.visualViewport.width,
                          height:window.visualViewport.height,
                          scale:window.visualViewport.scale,
                          offsetLeft:window.visualViewport.offsetLeft,
                          offsetTop:window.visualViewport.offsetTop
                        } : null,
                        canvas:{
                          ...rect(canvas),
                          backingWidth:canvas.width,
                          backingHeight:canvas.height,
                          imageRendering:getComputedStyle(canvas).imageRendering,
                          imageSmoothingEnabled:context.imageSmoothingEnabled
                        },
                        toolbar:rect(document.querySelector('.toolbar')),
                        mediaStatus:rect(document.querySelector('.media-status'))
                      };
                    })()
                    """
                )
                await cdp.command(
                    "Page.startScreencast",
                    {
                        "format": "jpeg",
                        "quality": 95,
                        "maxWidth": width,
                        "maxHeight": height,
                        "everyNthFrame": 1,
                    },
                )
                await asyncio.wait_for(cdp.screencast_event.wait(), timeout=5.0)
                next_frame_at = time.perf_counter()
                previous_sequence = None
                duplicate_frames = 0
                output_index = 0
                source_sequence = 1
                for scenario in program.scenarios:
                    commands.append(
                        await post_browser_command(
                            cdp,
                            source_epoch,
                            source_sequence,
                            scenario.command.to_mapping(),
                        )
                    )
                    source_sequence += 1
                    if scenario.settle_seconds > 0:
                        await asyncio.sleep(scenario.settle_seconds)
                    next_frame_at = max(next_frame_at, time.perf_counter())
                    for frame_offset, scheduled in scenario_capture_events(scenario):
                        if scheduled is None:
                            delay = next_frame_at - time.perf_counter()
                            if delay > 0:
                                await asyncio.sleep(delay)
                            if cdp.latest_screencast is None:
                                raise BrowserCaptureFailure(
                                    "Chrome produced no screencast frame"
                                )
                            output_index += 1
                            sequence = cdp.latest_screencast_sequence
                            if sequence == previous_sequence:
                                duplicate_frames += 1
                            sampled_sequences.append(sequence)
                            (
                                frames_dir / "{:06d}.jpg".format(output_index)
                            ).write_bytes(cdp.latest_screencast)
                            previous_sequence = sequence
                            next_frame_at += 1.0 / fps
                            continue
                        outcome = await post_browser_command(
                            cdp,
                            source_epoch,
                            source_sequence,
                            scheduled.to_mapping(),
                        )
                        outcome.update(
                            {
                                "scheduled_for_scenario": scenario.command.name,
                                "scheduled_at_frame": scheduled.at_frame,
                                "dispatch_observed_after_frame_count": frame_offset,
                            }
                        )
                        commands.append(outcome)
                        source_sequence += 1
                        next_frame_at = max(next_frame_at, time.perf_counter())
                await cdp.command("Page.stopScreencast")
                final_metrics = await cdp.evaluate("window.__wizardJoeMetrics()")
                if output_index != expected_frames:
                    raise BrowserCaptureFailure(
                        "browser capture frame budget mismatch: expected {}, captured {}".format(
                            expected_frames,
                            output_index,
                        )
                    )
                encoded = subprocess.run(
                    (
                        ffmpeg,
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-framerate",
                        "{:.6f}".format(fps),
                        "-i",
                        str(frames_dir / "%06d.jpg"),
                        "-vf",
                        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p",
                        "-movflags",
                        "+faststart",
                        "-y",
                        str(output_video),
                    ),
                    cwd=str(ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                if encoded.returncode or not output_video.is_file() or not output_video.stat().st_size:
                    raise BrowserCaptureFailure(
                        "browser video encoding failed: {}".format(
                            encoded.stderr.decode("utf-8", errors="replace").strip()
                        )
                    )
                report = {
                    "schema": SCHEMA,
                    "schema_version": 1,
                    "run_id": manifest["source_epoch"],
                    "browser_capture_id": source_epoch,
                    "candidate_commit": manifest["provenance"]["head"],
                    "capture_manifest_sha256": sha256_file(capture_manifest_path),
                    "runtime_epoch": manifest["runtime_binding"]["start"]["runtime_epoch"],
                    "viewport_profile": {
                        "name": profile,
                        "width": width,
                        "height": height,
                        "device_scale_factor": device_scale_factor,
                        "mobile": mobile,
                    },
                    "started_at_utc": started_at,
                    "completed_at_utc": utc_now(),
                    "viewport": {
                        "width": width,
                        "height": height,
                        "device_scale_factor": device_scale_factor,
                        "mobile": mobile,
                    },
                    "layout": layout,
                    "fps": fps,
                    "frame_count": output_index,
                    "expected_frame_count": expected_frames,
                    "scenario_program_schema": program.schema,
                    "scenario_program_schema_version": program.schema_version,
                    "screencast_event_count": cdp.latest_screencast_sequence,
                    "duplicate_sample_count": duplicate_frames,
                    "sampled_screencast_sequences": sampled_sequences,
                    "commands": commands,
                    "initial_client_metrics": initial_metrics,
                    "final_client_metrics": final_metrics,
                    "console_events": cdp.console_events,
                    "page_errors": cdp.page_errors,
                    "video_path": output_video.name,
                    "video_bytes": output_video.stat().st_size,
                    "video_sha256": sha256_file(output_video),
                }
                output_metrics.write_text(
                    json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            finally:
                if cdp is not None:
                    await cdp.close()
                process.terminate()
                try:
                    process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5.0)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--device-scale-factor", type=float, default=1.0)
    parser.add_argument("--mobile", action="store_true")
    parser.add_argument("--profile", default="desktop-dpr1")
    args = parser.parse_args(argv)
    if args.width < 640 or args.height < 360:
        if not args.mobile or args.width < 320 or args.height < 568:
            parser.error(
                "desktop viewport must be at least 640x360 and mobile "
                "viewport must be at least 320x568"
            )
    if not math.isfinite(args.device_scale_factor) or not (
        1.0 <= args.device_scale_factor <= 4.0
    ):
        parser.error("device scale factor must be between 1 and 4")
    if not isinstance(args.profile, str) or not SCENARIO_NAME_RE.fullmatch(
        args.profile
    ):
        parser.error("profile must be a lowercase kebab-case identifier")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        asyncio.run(
            capture_browser_layout(
                args.manifest.resolve(),
                args.video.resolve(),
                args.metrics.resolve(),
                args.width,
                args.height,
                args.device_scale_factor,
                args.mobile,
                args.profile,
            )
        )
    except (BrowserCaptureFailure, OSError, ValueError, KeyError) as exc:
        print("BROWSER CAPTURE FAILED: {}".format(exc), file=__import__("sys").stderr)
        return 1
    print(args.video.resolve())
    print(args.metrics.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
