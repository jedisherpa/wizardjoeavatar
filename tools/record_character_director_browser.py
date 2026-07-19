#!/usr/bin/env python3
"""Record a deterministic real-browser layout pass for Character Director review."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

import websockets

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SCHEMA = "character_director_browser_layout_v1"
SOURCE_ID = "character-director-browser-review"


class BrowserCaptureFailure(RuntimeError):
    pass


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
    program = json.loads(scenario_path.read_text(encoding="utf-8"))
    scenarios = program.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise BrowserCaptureFailure("browser proof requires copied scenario program steps")
    fps = float(manifest["init"]["fps"])
    expected_frames = sum(
        max(1, int(round(float(item["capture_seconds"]) * fps)))
        for item in scenarios
    )
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
                await cdp.command("Page.bringToFront")
                initial_metrics = await wait_for_wizard(cdp)
                layout = await cdp.evaluate(
                    """
                    (() => {
                      const rect = element => {
                        const value = element.getBoundingClientRect();
                        return {x:value.x,y:value.y,width:value.width,height:value.height};
                      };
                      return {
                        viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},
                        canvas:rect(document.querySelector('#wizard-canvas')),
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
                for source_sequence, scenario in enumerate(scenarios, start=1):
                    commands.append(
                        await post_browser_command(cdp, source_epoch, source_sequence, scenario)
                    )
                    settle = float(scenario["settle_seconds"])
                    if settle > 0:
                        await asyncio.sleep(settle)
                    next_frame_at = max(next_frame_at, time.perf_counter())
                    frame_count = max(1, int(round(float(scenario["capture_seconds"]) * fps)))
                    for _ in range(frame_count):
                        delay = next_frame_at - time.perf_counter()
                        if delay > 0:
                            await asyncio.sleep(delay)
                        if cdp.latest_screencast is None:
                            raise BrowserCaptureFailure("Chrome produced no screencast frame")
                        output_index += 1
                        sequence = cdp.latest_screencast_sequence
                        if sequence == previous_sequence:
                            duplicate_frames += 1
                        sampled_sequences.append(sequence)
                        (frames_dir / "{:06d}.jpg".format(output_index)).write_bytes(
                            cdp.latest_screencast
                        )
                        previous_sequence = sequence
                        next_frame_at += 1.0 / fps
                await cdp.command("Page.stopScreencast")
                final_metrics = await cdp.evaluate("window.__wizardJoeMetrics()")
                if output_index != expected_frames:
                    raise BrowserCaptureFailure("browser capture frame budget mismatch")
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
                    "started_at_utc": started_at,
                    "completed_at_utc": utc_now(),
                    "viewport": {"width": width, "height": height, "device_scale_factor": 1},
                    "layout": layout,
                    "fps": fps,
                    "frame_count": output_index,
                    "expected_frame_count": expected_frames,
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
    args = parser.parse_args(argv)
    if args.width < 640 or args.height < 360:
        parser.error("browser viewport must be at least 640x360")
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
