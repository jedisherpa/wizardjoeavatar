#!/usr/bin/env python3
"""Start one real governed Prism speech turn and expose its capture edge."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from record_character_director_browser import (
    BrowserCaptureFailure,
    CDPClient,
    CHROME,
    free_loopback_port,
    sha256_file,
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
GOVERNED_SPEECH_ROUTE = "/api/connectors/wizard/governed-speech"
PROTECTED_LOCAL_PORTS = frozenset({8765, 8875})
AV_TIMELINE_SCHEMA = "character_director_av_timeline_v1"
REVIEW_BUNDLE_SCHEMA = "character_director_v2_review_bundle_v1"


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


def _request_json(event: Mapping[str, Any]) -> Mapping[str, Any]:
    post_data = event.get("request", {}).get("postData")
    if not isinstance(post_data, str):
        return {}
    try:
        value = json.loads(post_data)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, Mapping) else {}


def summarize_media_session_request(event: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = _request_json(event)
    media = payload.get("media", {})
    playback = payload.get("playback", {})
    performance = payload.get("performance", {})
    return {
        "request_id": event.get("requestId"),
        "sequence": payload.get("sequence"),
        "media_epoch": payload.get("media_epoch"),
        "cause": payload.get("cause"),
        "source_slot": media.get("source_slot"),
        "media_id": media.get("media_id"),
        "media_sha256": media.get("media_sha256"),
        "playback_state": playback.get("state"),
        "position_ms": playback.get("position_ms"),
        "character_id": performance.get("character_id"),
        "character_package_sha256": performance.get("character_package_sha256"),
    }


def summarize_governed_registration_request(
    event: Mapping[str, Any],
) -> Mapping[str, Any]:
    payload = _request_json(event)
    source = payload.get("performance_context", {}).get("source", {})
    return {
        "request_id": event.get("requestId"),
        "connector_session_id": source.get("connector_session_id"),
        "accepted_sequence": source.get("accepted_sequence"),
        "media_epoch": source.get("media_epoch"),
        "source_slot": source.get("source_slot"),
        "media_id": source.get("media_id"),
        "media_sha256": source.get("media_sha256"),
    }


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


async def establish_audio_user_gesture(cdp: CDPClient) -> None:
    target = await cdp.evaluate(
        """
        (() => {
          const prompt = document.querySelector('textarea[aria-label="Message CDISS"]');
          if (!prompt) return null;
          const rect = prompt.getBoundingClientRect();
          prompt.scrollIntoView({block: 'nearest', inline: 'nearest'});
          return {
            x: Math.max(1, Math.min(window.innerWidth - 1, rect.left + rect.width / 2)),
            y: Math.max(1, Math.min(window.innerHeight - 1, rect.top + rect.height / 2))
          };
        })()
        """
    )
    if (
        not isinstance(target, Mapping)
        or not isinstance(target.get("x"), (int, float))
        or not isinstance(target.get("y"), (int, float))
    ):
        raise BrowserCaptureFailure("could not locate the Prism prompt for audio activation")
    event = {
        "x": float(target["x"]),
        "y": float(target["y"]),
        "button": "left",
        "clickCount": 1,
    }
    await cdp.command("Input.dispatchMouseEvent", {**event, "type": "mousePressed"})
    await cdp.command("Input.dispatchMouseEvent", {**event, "type": "mouseReleased"})
    await asyncio.sleep(0.1)
    activated = await cdp.evaluate(
        "Boolean(navigator.userActivation && navigator.userActivation.hasBeenActive)"
    )
    if activated is not True:
        raise BrowserCaptureFailure("Chrome did not accept the audio activation gesture")


async def install_media_session_probe(cdp: CDPClient) -> None:
    installed = await cdp.evaluate(
        """
        (() => {
          if (window.__wizardMediaSessionProbeInstalled) return true;
          const originalFetch = window.fetch.bind(window);
          window.__wizardMediaSessionProbe = [];
          window.__wizardMediaElementEvents = [];
          const observedEvents = [
            'loadedmetadata', 'durationchange', 'play', 'playing', 'pause',
            'waiting', 'stalled', 'seeking', 'seeked', 'ratechange', 'ended',
            'emptied', 'error', 'volumechange'
          ];
          for (const audio of document.querySelectorAll('audio')) {
            for (const eventName of observedEvents) {
              audio.addEventListener(eventName, () => {
                window.__wizardMediaElementEvents.push({
                  event: eventName,
                  sourceSlot: audio.dataset.sourceSlot ?? null,
                  paused: audio.paused,
                  ended: audio.ended,
                  muted: audio.muted,
                  volume: audio.volume,
                  readyState: audio.readyState,
                  currentTimeMs: Math.round(audio.currentTime * 1000),
                  observedAtMs: Math.round(performance.now())
                });
                window.__wizardMediaElementEvents =
                  window.__wizardMediaElementEvents.slice(-40);
              }, {capture: true});
            }
          }
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
              readyState: candidate.readyState,
              muted: candidate.muted,
              volume: candidate.volume,
              networkState: candidate.networkState,
              errorCode: candidate.error?.code ?? null
            })),
            paused: audio?.paused ?? true,
            ended: audio?.ended ?? false,
            currentTimeMs: Math.round((audio?.currentTime ?? 0) * 1000),
            durationMs: Number.isFinite(audio?.duration)
              ? Math.round(audio.duration * 1000)
              : null,
            readyState: audio?.readyState ?? 0,
            muted: audio?.muted ?? false,
            volume: audio?.volume ?? 1,
            networkState: audio?.networkState ?? 0,
            errorCode: audio?.error?.code ?? null,
            stageVisible: Boolean(stage),
            messages,
            playbackRecovery: window.__wizardPlaybackRecovery ?? null,
            governedSpeechTrace: Array.isArray(window.__prismGovernedSpeechTrace)
              ? window.__prismGovernedSpeechTrace.slice(-20)
              : [],
            mediaElementEvents: Array.isArray(window.__wizardMediaElementEvents)
              ? window.__wizardMediaElementEvents.slice(-20)
              : [],
            mediaSessionProbe: Array.isArray(window.__wizardMediaSessionProbe)
              ? window.__wizardMediaSessionProbe.slice(-8)
              : []
          };
        })()
        """
    )
    return value if isinstance(value, Mapping) else {}


async def resume_speech_playback_with_user_gesture(
    cdp: CDPClient,
) -> Mapping[str, Any]:
    target = await cdp.evaluate(
        """
        (() => {
          const prompt = document.querySelector('textarea[aria-label="Message CDISS"]');
          if (!prompt) return null;
          const rect = prompt.getBoundingClientRect();
          return {
            x: Math.max(1, Math.min(window.innerWidth - 1, rect.left + rect.width / 2)),
            y: Math.max(1, Math.min(window.innerHeight - 1, rect.top + rect.height / 2))
          };
        })()
        """
    )
    if (
        not isinstance(target, Mapping)
        or not isinstance(target.get("x"), (int, float))
        or not isinstance(target.get("y"), (int, float))
    ):
        return {"attempted": False, "reason": "missing_gesture_target"}
    event = {
        "x": float(target["x"]),
        "y": float(target["y"]),
        "button": "left",
        "clickCount": 1,
    }
    await cdp.command("Input.dispatchMouseEvent", {**event, "type": "mousePressed"})
    await cdp.command("Input.dispatchMouseEvent", {**event, "type": "mouseReleased"})
    await asyncio.sleep(0.1)
    value = await cdp.evaluate(
        """
        (() => {
          const audio = document.querySelector('audio[data-source-slot="speech"]');
          const status = !audio?.src
            ? 'gesture_dispatched_no_source'
            : !audio.paused && !audio.ended
              ? 'playing'
              : 'awaiting_application_resume';
          window.__wizardPlaybackRecovery = {
            attemptedAtMs: Math.round(performance.now()),
            status
          };
          return {attempted:true, status};
        })()
        """
    )
    return value if isinstance(value, Mapping) else {"attempted": True}


async def retain_governed_audio(cdp: CDPClient, output_dir: Path) -> Mapping[str, Any]:
    candidates = []
    for event in cdp.network_responses:
        response = event.get("response", {})
        url = str(response.get("url", ""))
        if url.rstrip("/").endswith("/api/tts"):
            candidates.append(event)
    if not candidates:
        raise BrowserCaptureFailure("governed /api/tts response was unavailable")
    event = candidates[-1]
    value = await cdp.command(
        "Network.getResponseBody",
        {"requestId": event.get("requestId")},
    )
    body = value.get("body") if isinstance(value, Mapping) else None
    if not isinstance(body, str):
        raise BrowserCaptureFailure("governed /api/tts body was unavailable")
    try:
        payload = base64.b64decode(body, validate=True) if value.get("base64Encoded") else body.encode("latin-1")
    except (UnicodeEncodeError, ValueError, TypeError) as exc:
        raise BrowserCaptureFailure("governed /api/tts body could not be decoded") from exc
    if not payload:
        raise BrowserCaptureFailure("governed audio artifact was empty")
    response = event.get("response", {})
    headers = {
        str(key).lower(): str(header_value)
        for key, header_value in response.get("headers", {}).items()
    }
    media_type = str(headers.get("content-type") or response.get("mimeType") or "application/octet-stream").split(";", 1)[0]
    suffix = ".mp3" if media_type in {"audio/mpeg", "audio/mp3"} else ".wav" if media_type == "audio/wav" else ".bin"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / ("governed-speech-audio" + suffix)
    path.write_bytes(payload)
    artifact_sha256 = sha256_file(path)
    declared_sha256 = headers.get("x-prism-audio-sha256")
    if declared_sha256 and declared_sha256.removeprefix("sha256:") != artifact_sha256:
        raise BrowserCaptureFailure("governed audio digest differs from its TTS identity header")
    return {
        "path": path.name,
        "media_type": media_type,
        "bytes": path.stat().st_size,
        "sha256": artifact_sha256,
        "declared_sha256": declared_sha256,
        "speech_id": headers.get("x-prism-speech-id"),
        "turn_id": headers.get("x-prism-turn-id"),
    }


async def collect_av_timeline(
    cdp: CDPClient,
    wizard_url: str,
    connector_token: str,
    capture_task: "asyncio.Task[subprocess.CompletedProcess]",
) -> Mapping[str, Any]:
    started = time.monotonic()
    samples = []
    while True:
        browser = await browser_speech_state(cdp)
        status = await asyncio.to_thread(
            get_json,
            wizard_url + "/api/avatar/wizard/media-session/status",
            connector_token,
        )
        state = await asyncio.to_thread(
            get_json,
            wizard_url + "/api/avatar/wizard/state",
        )
        application = status.get("application", {})
        session = status.get("session", {})
        wizard_state = state.get("state", {})
        browser_time = browser.get("currentTimeMs")
        wizard_time = application.get("media_time_ms")
        samples.append(
            {
                "observed_at_utc": utc_now(),
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "browser_media_time_ms": browser_time,
                "wizard_media_time_ms": wizard_time,
                "absolute_offset_ms": (
                    abs(int(browser_time) - int(wizard_time))
                    if isinstance(browser_time, int) and isinstance(wizard_time, int)
                    else None
                ),
                "browser_playing": browser.get("paused") is False and browser.get("ended") is False,
                "application_active": application.get("active") is True,
                "application_source_slot": application.get("source_slot"),
                "speech_id": wizard_state.get("speech_id"),
                "speech_mouth_authority": wizard_state.get("speech_mouth_authority"),
                "media_hash_prefix": session.get("media_hash_prefix"),
            }
        )
        if capture_task.done():
            break
        await asyncio.sleep(0.1)
    return {
        "schema": AV_TIMELINE_SCHEMA,
        "schema_version": 1,
        "sample_interval_target_ms": 100,
        "samples": samples,
    }


def _artifact(path: Path, output_dir: Path, media_type: str) -> Mapping[str, Any]:
    return {
        "path": path.resolve().relative_to(output_dir.resolve()).as_posix(),
        "media_type": media_type,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def manifest_artifact_path(
    manifest: Mapping[str, Any],
    output_dir: Path,
    *,
    path_suffix: str,
    media_type: str,
) -> Path:
    matches = [
        record
        for record in manifest.get("artifacts", ())
        if isinstance(record, Mapping)
        and record.get("media_type") == media_type
        and str(record.get("path", "")).endswith(path_suffix)
    ]
    if len(matches) != 1:
        raise BrowserCaptureFailure(
            "expected exactly one {} artifact ending in {!r}".format(
                media_type,
                path_suffix,
            )
        )
    relative = Path(str(matches[0]["path"]))
    if relative.is_absolute() or ".." in relative.parts:
        raise BrowserCaptureFailure("manifest artifact path escapes capture output")
    candidate = (output_dir / relative).resolve()
    try:
        candidate.relative_to(output_dir.resolve())
    except ValueError as exc:
        raise BrowserCaptureFailure(
            "manifest artifact path escapes capture output"
        ) from exc
    if not candidate.is_file():
        raise BrowserCaptureFailure("manifest artifact is missing: {}".format(relative))
    return candidate


def generate_v2_review_products(capture_output: Path, receipt_path: Path) -> Path:
    manifest_path = capture_output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    video_record = manifest.get("video", {})
    normal_video = capture_output / str(video_record.get("path", ""))
    if not video_record.get("available") or not normal_video.is_file():
        raise BrowserCaptureFailure("V2 review products require a normal-speed video")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise BrowserCaptureFailure("ffmpeg is required for V2 review products")

    copied_receipt = capture_output / "governed-speech-receipt.json"
    if receipt_path.resolve() != copied_receipt.resolve():
        shutil.copyfile(receipt_path, copied_receipt)
    receipt = json.loads(copied_receipt.read_text(encoding="utf-8"))
    audio_record = receipt.get("audio_artifact", {})
    audio_path = capture_output / str(audio_record.get("path", ""))
    if not audio_path.is_file() or sha256_file(audio_path) != audio_record.get("sha256"):
        raise BrowserCaptureFailure("retained governed audio failed integrity verification")

    machine_report = capture_output / "v2-machine-acceptance.json"
    analysis = subprocess.run(
        (
            sys.executable,
            str(ROOT / "tools" / "analyze_character_director_v2.py"),
            "--manifest",
            str(manifest_path),
            "--receipt",
            str(copied_receipt),
            "--output",
            str(machine_report),
        ),
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if analysis.returncode or not machine_report.is_file():
        raise BrowserCaptureFailure(
            "V2 machine acceptance failed: {}".format(
                analysis.stderr.decode("utf-8", errors="replace").strip()
                or analysis.stdout.decode("utf-8", errors="replace").strip()
            )
        )

    fps = float(manifest["init"]["fps"])
    quarter_speed = capture_output / "v2-quarter-speed.mp4"
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
            "setpts=4.0*PTS,fps={:.6f}".format(fps),
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
        raise BrowserCaptureFailure(
            "V2 quarter-speed generation failed: {}".format(
                quarter.stderr.decode("utf-8", errors="replace").strip()
            )
        )

    first_frame_utc = _parse_utc(manifest["frames"][0]["received_at_utc"])
    timeline_samples = receipt["av_timeline"]["samples"]
    nearest = min(
        timeline_samples,
        key=lambda sample: abs(
            (_parse_utc(sample["observed_at_utc"]) - first_frame_utc).total_seconds()
        ),
    )
    audio_offset_seconds = max(0.0, float(nearest["browser_media_time_ms"]) / 1000.0)
    audible_review = capture_output / "v2-audible-review.mp4"
    audible = subprocess.run(
        (
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(normal_video),
            "-ss",
            "{:.6f}".format(audio_offset_seconds),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-t",
            "20.0",
            "-movflags",
            "+faststart",
            "-y",
            str(audible_review),
        ),
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if audible.returncode or not audible_review.is_file() or not audible_review.stat().st_size:
        raise BrowserCaptureFailure(
            "V2 audible review generation failed: {}".format(
                audible.stderr.decode("utf-8", errors="replace").strip()
            )
        )

    contact_sheet = manifest_artifact_path(
        manifest,
        capture_output,
        path_suffix="-contact-sheet.png",
        media_type="image/png",
    )
    browser_record = receipt.get("browser_presentation", {})
    browser_video = capture_output / str(browser_record.get("video_path", ""))
    browser_metrics_path = capture_output / str(browser_record.get("metrics_path", ""))
    if not browser_video.is_file() or not browser_metrics_path.is_file():
        raise BrowserCaptureFailure("V2 browser presentation artifacts are missing")
    browser_metrics = json.loads(browser_metrics_path.read_text(encoding="utf-8"))
    browser_frame_count = int(browser_metrics.get("frame_count", 0))
    if (
        browser_metrics.get("schema") != "character_director_browser_layout_v1"
        or browser_metrics.get("candidate_commit") != manifest["provenance"]["head"]
        or browser_metrics.get("capture_manifest_sha256") != sha256_file(manifest_path)
        or browser_metrics.get("page_errors")
        or browser_frame_count <= 0
        or int(browser_metrics.get("screencast_event_count", 0)) < round(browser_frame_count * 0.50)
        or int(browser_metrics.get("duplicate_sample_count", browser_frame_count)) > round(browser_frame_count * 0.50)
    ):
        raise BrowserCaptureFailure("V2 browser presentation failed cadence or integrity checks")
    bundle = {
        "schema": REVIEW_BUNDLE_SCHEMA,
        "schema_version": 1,
        "acceptance_scenario": "V2",
        "run_id": manifest["source_epoch"],
        "candidate_commit": manifest["provenance"]["head"],
        "audio_offset_seconds": round(audio_offset_seconds, 6),
        "complete_for_independent_review": True,
        "artifacts": {
            "capture_manifest": _artifact(manifest_path, capture_output, "application/json"),
            "speech_receipt": _artifact(copied_receipt, capture_output, "application/json"),
            "animation_truth_trace": _artifact(
                capture_output / manifest["animation_truth_trace"]["path"],
                capture_output,
                "application/x-ndjson",
            ),
            "normal_speed_video": _artifact(normal_video, capture_output, "video/mp4"),
            "audible_review_video": _artifact(audible_review, capture_output, "video/mp4"),
            "quarter_speed_video": _artifact(quarter_speed, capture_output, "video/mp4"),
            "browser_presentation_video": _artifact(browser_video, capture_output, "video/mp4"),
            "browser_presentation_metrics": _artifact(
                browser_metrics_path,
                capture_output,
                "application/json",
            ),
            "retained_audio": _artifact(audio_path, capture_output, str(audio_record["media_type"])),
            "machine_acceptance": _artifact(machine_report, capture_output, "application/json"),
            "contact_sheet": _artifact(contact_sheet, capture_output, "image/png"),
        },
    }
    bundle_path = capture_output / "v2-review-bundle-manifest.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle_path


async def wait_for_capture_edge(
    cdp: CDPClient,
    wizard_url: str,
    connector_token: str,
    timeout: float,
) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_observation: Dict[str, Any] = {}
    edge_samples = []
    playback_recovery_attempts = []
    next_playback_recovery_at = 0.0
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
        now = time.monotonic()
        if (
            len(playback_recovery_attempts) < 3
            and now >= next_playback_recovery_at
            and governed.get("active") is True
            and application.get("active") is not True
            and browser.get("paused") is True
            and browser.get("ended") is False
            and int(browser.get("readyState", 0)) >= 2
        ):
            recovery = dict(await resume_speech_playback_with_user_gesture(cdp))
            recovery["attempted_at_utc"] = utc_now()
            playback_recovery_attempts.append(recovery)
            next_playback_recovery_at = now + 1.0
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
            summarize_media_session_request(event)
            for event in cdp.network_requests
            if MEDIA_SESSION_ROUTE in str(event.get("request", {}).get("url", ""))
        ][-8:]
        media_transition_requests = [
            summary
            for summary in (
                summarize_media_session_request(event)
                for event in cdp.network_requests
                if MEDIA_SESSION_ROUTE
                in str(event.get("request", {}).get("url", ""))
            )
            if summary.get("cause") != "heartbeat"
        ][-20:]
        governed_registration_requests = [
            summarize_governed_registration_request(event)
            for event in cdp.network_requests
            if GOVERNED_SPEECH_ROUTE
            in str(event.get("request", {}).get("url", ""))
        ][-2:]
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
            "media_session_transition_requests": media_transition_requests,
            "media_session_responses": media_responses,
            "governed_registration_requests": governed_registration_requests,
            "edge_samples": edge_samples,
            "playback_recovery_attempts": playback_recovery_attempts,
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
                "playback_recovery_attempts": playback_recovery_attempts,
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
                await establish_audio_user_gesture(cdp)
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
                audio_artifact = (
                    await retain_governed_audio(cdp, args.capture_output)
                    if args.capture_output is not None
                    else None
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
                    "audio_artifact": audio_artifact,
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
                    capture_task = asyncio.create_task(
                        asyncio.to_thread(
                            subprocess.run,
                            capture_command,
                            cwd=str(ROOT),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=False,
                        )
                    )
                    timeline_task = asyncio.create_task(
                        collect_av_timeline(
                            cdp,
                            args.wizard_url,
                            connector_token,
                            capture_task,
                        )
                    )
                    capture = await capture_task
                    receipt["av_timeline"] = await timeline_task
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
                    if receipt["atomic_capture"]["exit_code"] == 0:
                        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                        runtime_binding = manifest.get("runtime_binding", {})
                        runtime_start = runtime_binding.get("start", {})
                        receipt["atomic_capture"].update(
                            {
                                "manifest_sha256": sha256_file(manifest_path),
                                "source_epoch": manifest.get("source_epoch"),
                                "candidate_commit": manifest.get("provenance", {}).get("head"),
                                "runtime_epoch": runtime_start.get("runtime_epoch"),
                                "first_frame_received_at_utc": manifest.get("frames", [{}])[0].get("received_at_utc"),
                                "last_frame_received_at_utc": manifest.get("frames", [{}])[-1].get("received_at_utc"),
                            }
                        )
                        browser_video = args.capture_output / "v2-browser-presentation.mp4"
                        browser_metrics = args.capture_output / "v2-browser-presentation-metrics.json"
                        browser_command = (
                            sys.executable,
                            str(ROOT / "tools" / "record_character_director_browser.py"),
                            "--manifest",
                            str(manifest_path),
                            "--video",
                            str(browser_video),
                            "--metrics",
                            str(browser_metrics),
                        )
                        browser_capture = await asyncio.to_thread(
                            subprocess.run,
                            browser_command,
                            cwd=str(ROOT),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=False,
                        )
                        receipt["browser_presentation"] = {
                            "command": list(browser_command[1:]),
                            "exit_code": browser_capture.returncode,
                            "video_path": browser_video.name,
                            "metrics_path": browser_metrics.name,
                            "stdout": browser_capture.stdout.decode("utf-8", errors="replace").strip(),
                            "stderr": browser_capture.stderr.decode("utf-8", errors="replace").strip(),
                        }
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
                    if receipt.get("browser_presentation", {}).get("exit_code"):
                        raise BrowserCaptureFailure(
                            "V2 browser presentation capture failed: {}".format(
                                receipt["browser_presentation"]["stderr"]
                                or receipt["browser_presentation"]["stdout"]
                            )
                        )
                    print("ATOMIC_CAPTURE {}".format(args.capture_output), flush=True)
                    if args.defer_review_products:
                        print("REVIEW_PRODUCTS_DEFERRED", flush=True)
                    else:
                        bundle_path = generate_v2_review_products(
                            args.capture_output, args.receipt
                        )
                        print("REVIEW_BUNDLE {}".format(bundle_path), flush=True)
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
    parser.add_argument("--minimum-audio-seconds", type=float, default=45.0)
    parser.add_argument("--capture-output", type=Path)
    parser.add_argument(
        "--defer-review-products",
        action="store_true",
        help=(
            "Stop after atomic capture and browser replay so a scenario-specific "
            "acceptance analyzer can produce the final review bundle."
        ),
    )
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
