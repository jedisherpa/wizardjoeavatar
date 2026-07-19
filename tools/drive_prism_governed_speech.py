#!/usr/bin/env python3
"""Start one real governed Prism speech turn and expose its capture edge."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from record_character_director_browser import (
    BrowserCaptureFailure,
    CDPClient,
    CHROME,
    free_loopback_port,
    utc_now,
    wait_for_page_target,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT = (
    "Tell me a detailed warm fictional story in five complete paragraphs about a "
    "traveler who pauses at sunset to listen carefully to a friend. Include the "
    "setting, the friend's concern, the traveler's attentive response, their walk "
    "across an old bridge, and a calm resolution beneath the first stars. Give "
    "each paragraph several full sentences and finish the story without asking a "
    "question. This is only a creative-writing request; no action, clarification, "
    "or advice is needed."
)
SCHEMA = "character_director_prism_governed_speech_v1"
MEDIA_SESSION_ROUTE = "/api/connectors/wizard/media-session"
PROTECTED_LOCAL_PORTS = frozenset({8765, 8875})


def validate_disposable_loopback_url(value: str, label: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("{} must use an HTTP loopback endpoint".format(label))
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("{} must not contain credentials, query, or fragment".format(label))
    if parsed.port is None:
        raise ValueError("{} must include an explicit disposable port".format(label))
    if parsed.port in PROTECTED_LOCAL_PORTS:
        raise ValueError("{} uses protected local port {}".format(label, parsed.port))
    if parsed.path not in {"", "/"}:
        raise ValueError("{} must target the endpoint root".format(label))
    return value.rstrip("/")


def get_json(url: str, token: str = "") -> Mapping[str, Any]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer {}".format(token)
    with urlopen(Request(url, headers=headers), timeout=2.0) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, Mapping):
        raise BrowserCaptureFailure("expected a JSON object from {}".format(url))
    return value


async def wait_for_prism(
    cdp: CDPClient,
    timeout: float,
    require_completed_greeting: bool = True,
) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = await cdp.evaluate(
            """
            (() => {
              const prompt = document.querySelector('textarea[aria-label="Message CDISS"]');
              const status = document.querySelector('.prism-wizard-status small');
              const audio = document.querySelector('audio[data-source-slot="speech"]');
              const completedAgentMessages = [...document.querySelectorAll(
                '.prism-dodecahedron-cdiss-message.is-agent p'
              )].filter(node => node.textContent?.trim()).length;
              return {
                promptReady: Boolean(prompt && !prompt.disabled),
                connector: status?.textContent?.trim() ?? null,
                audioPresent: Boolean(audio),
                completedAgentMessages
              };
            })()
            """
        )
        if (
            isinstance(state, dict)
            and state.get("promptReady")
            and state.get("audioPresent")
            and (
                not require_completed_greeting
                or int(state.get("completedAgentMessages", 0)) > 0
            )
            and "connected" in str(state.get("connector", "")).lower()
        ):
            return state
        await asyncio.sleep(0.1)
    raise BrowserCaptureFailure("Prism did not become ready with a connected Wizard")


async def submit_prompt(cdp: CDPClient, prompt: str) -> None:
    populated = await cdp.evaluate(
        """
        (() => {
          const prompt = document.querySelector('textarea[aria-label="Message CDISS"]');
          if (!prompt || prompt.disabled) return {ok:false};
          const setter = Object.getOwnPropertyDescriptor(
            HTMLTextAreaElement.prototype,
            'value'
          ).set;
          setter.call(prompt, %s);
          prompt.dispatchEvent(new Event('input', {bubbles:true}));
          return {ok:true};
        })()
        """ % json.dumps(prompt)
    )
    if not isinstance(populated, dict) or populated.get("ok") is not True:
        raise BrowserCaptureFailure("could not submit the governed Prism prompt")
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        submitted = await cdp.evaluate(
            """
            (() => {
              const button = document.querySelector(
                'button.prism-dodecahedron-prompt-send-button'
              );
              if (!button || button.disabled) return false;
              button.click();
              return true;
            })()
            """
        )
        if submitted is True:
            return
        await asyncio.sleep(0.05)
    raise BrowserCaptureFailure("Prism prompt did not become submittable")


async def install_media_session_probe(cdp: CDPClient) -> None:
    installed = await cdp.evaluate(
        """
        (() => {
          if (window.__wizardMediaSessionProbeInstalled) return true;
          const originalFetch = window.fetch.bind(window);
          window.__wizardMediaSessionProbe = [];
          window.fetch = async (...args) => {
            const input = args[0];
            const init = args[1] ?? {};
            const url = typeof input === 'string' ? input : input?.url ?? '';
            if (!url.includes('/api/connectors/wizard/media-session')) {
              return originalFetch(...args);
            }
            const requestBytes = typeof init.body === 'string' ? init.body.length : 0;
            try {
              const response = await originalFetch(...args);
              const responseBody = await response.clone().text();
              window.__wizardMediaSessionProbe.push({
                url,
                status: response.status,
                requestBytes,
                responseBytes: responseBody.length
              });
              window.__wizardMediaSessionProbe = window.__wizardMediaSessionProbe.slice(-20);
              return response;
            } catch (error) {
              window.__wizardMediaSessionProbe.push({
                url,
                status: null,
                requestBytes,
                responseBytes: 0,
                errorName: error?.name ?? 'Error'
              });
              window.__wizardMediaSessionProbe = window.__wizardMediaSessionProbe.slice(-20);
              throw error;
            }
          };
          window.__wizardMediaSessionProbeInstalled = true;
          return true;
        })()
        """
    )
    if installed is not True:
        raise BrowserCaptureFailure("could not install the media-session wire probe")


async def browser_speech_state(cdp: CDPClient) -> Mapping[str, Any]:
    value = await cdp.evaluate(
        """
        (() => {
          const audios = [...document.querySelectorAll('audio')];
          const audio = document.querySelector('audio[data-source-slot="speech"]');
          const stage = [...document.querySelectorAll('*')]
            .find(node => node.children.length === 0 && node.textContent?.trim() === 'Speaking');
          const messages = [...document.querySelectorAll(
            '.prism-dodecahedron-cdiss-message'
          )].slice(-6).map(node => ({
            role: [...node.classList].find(name => name.startsWith('is-')) ?? null,
            textLength: node.querySelector('p')?.textContent?.trim().length ?? 0
          }));
          return {
            audioCount: audios.length,
            audios: audios.map((candidate, index) => ({
              index,
              sourceSlot: candidate.dataset.sourceSlot ?? null,
              paused: candidate.paused,
              ended: candidate.ended,
              currentTimeMs: Math.round(candidate.currentTime * 1000),
              durationMs: Number.isFinite(candidate.duration)
                ? Math.round(candidate.duration * 1000)
                : null,
              readyState: candidate.readyState
            })),
            paused: audio?.paused ?? true,
            ended: audio?.ended ?? false,
            currentTimeMs: Math.round((audio?.currentTime ?? 0) * 1000),
            durationMs: Number.isFinite(audio?.duration)
              ? Math.round(audio.duration * 1000)
              : null,
            readyState: audio?.readyState ?? 0,
            stageVisible: Boolean(stage),
            messages,
            mediaSessionProbe: Array.isArray(window.__wizardMediaSessionProbe)
              ? window.__wizardMediaSessionProbe.slice(-8)
              : []
          };
        })()
        """
    )
    return value if isinstance(value, Mapping) else {}


async def wait_for_capture_edge(
    cdp: CDPClient,
    wizard_url: str,
    connector_token: str,
    timeout: float,
) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_observation: Dict[str, Any] = {}
    edge_samples = []
    while time.monotonic() < deadline:
        browser = await browser_speech_state(cdp)
        status = await asyncio.to_thread(
            get_json,
            wizard_url.rstrip("/") + "/api/avatar/wizard/media-session/status",
            connector_token,
        )
        state = await asyncio.to_thread(
            get_json,
            wizard_url.rstrip("/") + "/api/avatar/wizard/state",
        )
        application = status.get("application", {})
        governed = status.get("governed_speech", {})
        wizard_state = state.get("state", {})
        edge_sample = {
            "browser_playing": browser.get("paused") is False
            and browser.get("ended") is False
            and int(browser.get("currentTimeMs", 0)) > 0,
            "browser_time_ms": int(browser.get("currentTimeMs", 0)),
            "application_active": application.get("active") is True,
            "application_source_slot": application.get("source_slot"),
            "governed_active": governed.get("active") is True,
            "governed_status": governed.get("status"),
            "mouth_authority": wizard_state.get("speech_mouth_authority"),
            "wizard_action": wizard_state.get("action"),
            "wizard_mouth": wizard_state.get("mouth"),
            "simulation_tick": wizard_state.get("simulation_tick"),
        }
        if (
            edge_sample["browser_playing"]
            or edge_sample["application_active"]
            or edge_sample["governed_active"]
            or edge_sample["mouth_authority"] == "media_alignment"
        ):
            edge_samples.append(edge_sample)
            edge_samples = edge_samples[-20:]
        media_requests = [
            {
                "request_id": event.get("requestId"),
                "url": event.get("request", {}).get("url"),
                "method": event.get("request", {}).get("method"),
            }
            for event in cdp.network_requests
            if MEDIA_SESSION_ROUTE in str(event.get("request", {}).get("url", ""))
        ][-8:]
        media_responses = [
            {
                "request_id": event.get("requestId"),
                "url": event.get("response", {}).get("url"),
                "status": event.get("response", {}).get("status"),
                "mime_type": event.get("response", {}).get("mimeType"),
            }
            for event in cdp.network_responses
            if MEDIA_SESSION_ROUTE in str(event.get("response", {}).get("url", ""))
        ][-8:]
        last_observation = {
            "browser": dict(browser),
            "application": application,
            "governed_speech": governed,
            "wizard_state": {
                "simulation_tick": wizard_state.get("simulation_tick"),
                "speech_id": wizard_state.get("speech_id"),
                "speech_mouth_authority": wizard_state.get(
                    "speech_mouth_authority"
                ),
                "mouth": wizard_state.get("mouth"),
                "action": wizard_state.get("action"),
            },
            "browser_console_event_count": len(cdp.console_events),
            "browser_page_error_count": len(cdp.page_errors),
            "media_session_requests": media_requests,
            "media_session_responses": media_responses,
            "edge_samples": edge_samples,
        }
        if (
            browser.get("paused") is False
            and browser.get("ended") is False
            and int(browser.get("currentTimeMs", 0)) > 0
            and application.get("active") is True
            and application.get("source_slot") == "speech"
            and governed.get("active") is True
            and wizard_state.get("speech_mouth_authority") == "media_alignment"
        ):
            return {
                "observed_at_utc": utc_now(),
                "browser": dict(browser),
                "wizard_media": status,
                "wizard_state": {
                    "simulation_tick": wizard_state.get("simulation_tick"),
                    "speech_id": wizard_state.get("speech_id"),
                    "speech_mouth_authority": wizard_state.get(
                        "speech_mouth_authority"
                    ),
                    "mouth": wizard_state.get("mouth"),
                },
            }
        await asyncio.sleep(0.05)
    raise BrowserCaptureFailure(
        "governed speech did not reach the real capture edge; last observation: {}".format(
            json.dumps(last_observation, sort_keys=True)
        )
    )


async def run(args: argparse.Namespace) -> None:
    if not CHROME.is_file():
        raise BrowserCaptureFailure("Google Chrome is required")
    connector_token = os.environ.get("WIZARD_MEDIA_CONNECTOR_TOKEN", "").strip()
    if not connector_token:
        raise BrowserCaptureFailure("WIZARD_MEDIA_CONNECTOR_TOKEN is required")
    port = free_loopback_port()
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="prism-v2-governed-") as temporary:
        temporary_path = Path(temporary)
        with (temporary_path / "chrome.log").open("wb") as log_stream:
            process = subprocess.Popen(
                (
                    str(CHROME),
                    "--headless=new",
                    "--autoplay-policy=no-user-gesture-required",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--remote-debugging-address=127.0.0.1",
                    "--remote-debugging-port={}".format(port),
                    "--user-data-dir={}".format(temporary_path / "profile"),
                    "--window-size=1280,720",
                    "--force-device-scale-factor=1",
                    args.prism_url.rstrip("/") + "/",
                ),
                cwd=str(ROOT),
                stdout=log_stream,
                stderr=subprocess.STDOUT,
            )
            cdp: Optional[CDPClient] = None
            started_at = utc_now()
            try:
                cdp = CDPClient(await wait_for_page_target(port))
                await cdp.connect()
                await cdp.command("Page.enable")
                await cdp.command("Runtime.enable")
                await cdp.command("Log.enable")
                await cdp.command("Network.enable")
                await cdp.command("Page.bringToFront")
                initial = await wait_for_prism(
                    cdp,
                    args.timeout,
                    require_completed_greeting=not args.capture_opening,
                )
                await install_media_session_probe(cdp)
                if not args.capture_opening:
                    await submit_prompt(cdp, args.prompt)
                edge = await wait_for_capture_edge(
                    cdp,
                    args.wizard_url,
                    connector_token,
                    args.timeout,
                )
                duration_ms = edge.get("browser", {}).get("durationMs")
                minimum_duration_ms = round(args.minimum_audio_seconds * 1000)
                if (
                    not isinstance(duration_ms, int)
                    or duration_ms < minimum_duration_ms
                ):
                    raise BrowserCaptureFailure(
                        "governed audio is {} ms; at least {} ms is required".format(
                            duration_ms,
                            minimum_duration_ms,
                        )
                    )
                receipt = {
                    "schema": SCHEMA,
                    "schema_version": 1,
                    "started_at_utc": started_at,
                    "capture_edge": edge,
                    "prism_url": args.prism_url,
                    "wizard_url": args.wizard_url,
                    "prompt_sha256": hashlib.sha256(
                        args.prompt.encode("utf-8")
                    ).hexdigest()
                    if not args.capture_opening
                    else None,
                    "performance_source": "startup_greeting"
                    if args.capture_opening
                    else "submitted_prompt",
                    "initial_browser_state": initial,
                    "browser_console_event_count": len(cdp.console_events),
                    "browser_page_error_count": len(cdp.page_errors),
                }
                args.receipt.write_text(
                    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                print("CAPTURE_EDGE {}".format(args.receipt), flush=True)
                if args.capture_output is not None:
                    capture_command = (
                        sys.executable,
                        str(ROOT / "tools" / "run_character_director_visual_review.py"),
                        "--base-url",
                        args.wizard_url,
                        "--output-dir",
                        str(args.capture_output),
                        "--scenarios-file",
                        str(args.scenarios_file),
                        "--sample-every-frames",
                        "12",
                    )
                    capture = await asyncio.to_thread(
                        subprocess.run,
                        capture_command,
                        cwd=str(ROOT),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False,
                    )
                    receipt["atomic_capture"] = {
                        "command": list(capture_command[1:]),
                        "exit_code": capture.returncode,
                        "output_dir": str(args.capture_output),
                        "stdout": capture.stdout.decode(
                            "utf-8", errors="replace"
                        ).strip(),
                        "stderr": capture.stderr.decode(
                            "utf-8", errors="replace"
                        ).strip(),
                    }
                    manifest_path = args.capture_output / "manifest.json"
                    if capture.returncode == 0 and not manifest_path.is_file():
                        receipt["atomic_capture"]["exit_code"] = 1
                        receipt["atomic_capture"]["stderr"] = (
                            "capture exited without creating manifest.json"
                        )
                    receipt["completed_at_utc"] = utc_now()
                    args.receipt.write_text(
                        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    if receipt["atomic_capture"]["exit_code"]:
                        raise BrowserCaptureFailure(
                            "atomic V2 capture failed: {}".format(
                                receipt["atomic_capture"]["stderr"]
                                or receipt["atomic_capture"]["stdout"]
                            )
                        )
                    print("ATOMIC_CAPTURE {}".format(args.capture_output), flush=True)
                hold_until = time.monotonic() + args.hold_seconds
                while time.monotonic() < hold_until:
                    state = await browser_speech_state(cdp)
                    if state.get("ended") is True:
                        break
                    await asyncio.sleep(0.1)
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
    parser.add_argument("--prism-url", default="http://127.0.0.1:8890")
    parser.add_argument("--wizard-url", default="http://127.0.0.1:8896")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--capture-opening", action="store_true")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--hold-seconds", type=float, default=40.0)
    parser.add_argument("--minimum-audio-seconds", type=float, default=24.0)
    parser.add_argument("--capture-output", type=Path)
    parser.add_argument(
        "--scenarios-file",
        type=Path,
        default=ROOT
        / "tools"
        / "character_director_scenarios"
        / "v2-governed-speech.json",
    )
    args = parser.parse_args(argv)
    if (
        args.timeout <= 0
        or args.hold_seconds <= 0
        or args.minimum_audio_seconds <= 0
    ):
        parser.error("timeouts must be positive")
    try:
        args.prism_url = validate_disposable_loopback_url(args.prism_url, "--prism-url")
        args.wizard_url = validate_disposable_loopback_url(args.wizard_url, "--wizard-url")
    except ValueError as exc:
        parser.error(str(exc))
    args.receipt = args.receipt.resolve()
    args.scenarios_file = args.scenarios_file.resolve()
    if not args.scenarios_file.is_file():
        parser.error("--scenarios-file does not exist")
    if args.capture_output is not None:
        args.capture_output = args.capture_output.resolve()
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        asyncio.run(run(args))
    except (BrowserCaptureFailure, OSError, ValueError) as exc:
        print("FAILED: {}".format(exc), file=__import__("sys").stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
