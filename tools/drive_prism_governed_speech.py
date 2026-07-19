#!/usr/bin/env python3
"""Start one real governed Prism speech turn and expose its capture edge."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence
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
    "Tell me a warm ninety-five-word story about a traveler who pauses at "
    "sunset to listen to a friend. This is only a creative writing request; "
    "no action or clarification is needed."
)
SCHEMA = "character_director_prism_governed_speech_v1"


def get_json(url: str, token: str = "") -> Mapping[str, Any]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer {}".format(token)
    with urlopen(Request(url, headers=headers), timeout=2.0) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, Mapping):
        raise BrowserCaptureFailure("expected a JSON object from {}".format(url))
    return value


async def wait_for_prism(cdp: CDPClient, timeout: float) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = await cdp.evaluate(
            """
            (() => {
              const prompt = document.querySelector('textarea[aria-label="Message CDISS"]');
              const status = document.querySelector('.prism-wizard-status small');
              const audio = document.querySelectorAll('audio')[1];
              return {
                promptReady: Boolean(prompt && !prompt.disabled),
                connector: status?.textContent?.trim() ?? null,
                audioPresent: Boolean(audio)
              };
            })()
            """
        )
        if (
            isinstance(state, dict)
            and state.get("promptReady")
            and state.get("audioPresent")
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


async def browser_speech_state(cdp: CDPClient) -> Mapping[str, Any]:
    value = await cdp.evaluate(
        """
        (() => {
          const audio = document.querySelectorAll('audio')[1];
          const stage = [...document.querySelectorAll('*')]
            .find(node => node.children.length === 0 && node.textContent?.trim() === 'Speaking');
          return {
            paused: audio?.paused ?? true,
            ended: audio?.ended ?? false,
            currentTimeMs: Math.round((audio?.currentTime ?? 0) * 1000),
            durationMs: Number.isFinite(audio?.duration)
              ? Math.round(audio.duration * 1000)
              : null,
            readyState: audio?.readyState ?? 0,
            stageVisible: Boolean(stage)
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
    raise BrowserCaptureFailure("governed speech did not reach the real capture edge")


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
                await cdp.command("Page.bringToFront")
                initial = await wait_for_prism(cdp, args.timeout)
                await submit_prompt(cdp, args.prompt)
                edge = await wait_for_capture_edge(
                    cdp,
                    args.wizard_url,
                    connector_token,
                    args.timeout,
                )
                receipt = {
                    "schema": SCHEMA,
                    "schema_version": 1,
                    "started_at_utc": started_at,
                    "capture_edge": edge,
                    "prism_url": args.prism_url,
                    "wizard_url": args.wizard_url,
                    "prompt_sha256": __import__("hashlib").sha256(
                        args.prompt.encode("utf-8")
                    ).hexdigest(),
                    "initial_browser_state": initial,
                    "browser_console_events": cdp.console_events,
                    "browser_page_errors": cdp.page_errors,
                }
                args.receipt.write_text(
                    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                print("CAPTURE_EDGE {}".format(args.receipt), flush=True)
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
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--hold-seconds", type=float, default=40.0)
    args = parser.parse_args(argv)
    if args.timeout <= 0 or args.hold_seconds <= 0:
        parser.error("timeouts must be positive")
    args.receipt = args.receipt.resolve()
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
