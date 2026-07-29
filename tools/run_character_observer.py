#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "tools" / "run_wizard_avatar_server.py"
DEFAULT_CURRENT_PACKAGE = (
    ROOT
    / "wizard_avatar"
    / "definitions"
    / "characters"
    / "serena_quill"
    / "serena_quill_character_package_v2.json"
)
DEFAULT_PERFORMANCE_REVIEW_MANIFEST = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "wizard-joe"
    / "audio-performances-v1"
    / "manifest.json"
)
DEFAULT_MOUTH_PAIR_MANIFEST = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "wizard-joe"
    / "mouth-pairs-v1"
    / "mouth-pair-manifest.json"
)
DEFAULT_MOUTH_REVIEW_INDEX = (
    ROOT
    / "assets"
    / "reference"
    / "wizard-joe-mouth-review-library-index.json"
)


def _mouth_pair_states(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    pairs = payload.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError("mouth-pair manifest must contain pairs")
    result: dict[str, dict[str, str]] = {}
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        base_pose_id = pair.get("base_pose_id")
        states = pair.get("states")
        if not isinstance(base_pose_id, str) or not isinstance(states, dict):
            continue
        resolved: dict[str, str] = {}
        for state in ("closed", "open"):
            state_record = states.get(state)
            if (
                isinstance(state_record, dict)
                and isinstance(state_record.get("pose_id"), str)
            ):
                resolved[state] = state_record["pose_id"]
        if set(resolved) == {"closed", "open"}:
            result[base_pose_id] = resolved
    return result


def _health(port: int, timeout: float = 0.75) -> dict[str, Any]:
    try:
        with urlopen(
            f"http://127.0.0.1:{port}/api/companion/health",
            timeout=timeout,
        ) as response:
            payload = json.load(response)
    except (OSError, URLError, ValueError) as exc:
        return {"status": "offline", "detail": type(exc).__name__}
    if not isinstance(payload, dict):
        return {"status": "invalid"}
    return payload


def _wait_ready(process: subprocess.Popen[bytes], port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"character runtime on port {port} exited with code {process.returncode}"
            )
        if _health(port).get("status") == "ready":
            return
        time.sleep(0.1)
    raise TimeoutError(f"character runtime on port {port} did not become ready")


def _observer_health(
    *,
    joe: dict[str, Any],
    current: dict[str, Any],
    current_label: str,
    current_meta: str,
    review_character_id: str | None,
    review_projection: bool,
    runtime_admitted: bool,
) -> dict[str, Any]:
    ready = joe.get("status") == "ready" and current.get("status") == "ready"
    return {
        "schema_version": 1,
        "status": "ready" if ready else "degraded",
        "baseline": {
            "display_name": "HD Wizard Joe",
            "runtime": joe,
        },
        "review": {
            "character_id": review_character_id,
            "display_name": current_label,
            "summary": current_meta,
            "review_projection": review_projection,
            "runtime_admitted": runtime_admitted,
            "runtime": current,
        },
    }


def _observer_html(
    *,
    joe_port: int,
    current_port: int,
    joe_path: str,
    current_path: str,
    current_label: str,
    current_meta: str,
    joe_meta: str = "250 approved source frames",
) -> bytes:
    safe_label = html.escape(current_label)
    safe_joe_meta = html.escape(joe_meta)
    safe_current_meta = html.escape(current_meta)
    safe_joe_path = html.escape(joe_path, quote=True)
    safe_current_path = html.escape(current_path, quote=True)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Character Director Observer</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #eef1f3;
        color: #17201d;
      }}
      * {{ box-sizing: border-box; }}
      html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; }}
      body {{ display: grid; grid-template-rows: 56px minmax(0, 1fr); }}
      header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 8px 16px;
        border-bottom: 1px solid #c9d0ce;
        background: #fff;
      }}
      .title {{ min-width: 0; }}
      .title strong {{ display: block; font-size: 15px; }}
      .title span {{ display: block; color: #65706c; font-size: 12px; }}
      .status {{ display: flex; align-items: center; gap: 8px; color: #52605b; font-size: 12px; }}
      .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #b67a1f; }}
      .status.ready .dot {{ background: #1c8c67; }}
      button {{
        min-height: 34px;
        padding: 0 11px;
        border: 1px solid #aeb8b4;
        border-radius: 6px;
        background: #fff;
        color: #17201d;
        font: inherit;
        cursor: pointer;
      }}
      button:hover {{ background: #f3f6f5; }}
      main {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); min-height: 0; }}
      section {{
        display: grid;
        grid-template-rows: 44px minmax(0, 1fr);
        min-width: 0;
        min-height: 0;
        border-right: 1px solid #c9d0ce;
        background: #fff;
      }}
      section:last-child {{ border-right: 0; }}
      .panel-title {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 7px 12px;
        border-bottom: 1px solid #dde2e0;
      }}
      h1 {{ margin: 0; color: #33413c; font-size: 13px; font-weight: 650; }}
      .panel-title span {{ color: #78827e; font-size: 11px; white-space: nowrap; }}
      iframe {{ width: 100%; height: 100%; border: 0; background: #fff; }}
      @media (max-width: 760px) {{
        body {{ grid-template-rows: auto minmax(0, 1fr); }}
        header {{ align-items: flex-start; }}
        .title span {{ display: none; }}
        main {{ grid-template-columns: 1fr; grid-template-rows: repeat(2, minmax(0, 1fr)); }}
        section {{ border-right: 0; border-bottom: 1px solid #c9d0ce; }}
      }}
    </style>
  </head>
  <body>
    <header>
      <div class="title">
        <strong>Character Director Observer</strong>
        <span>Approved HD baseline beside the package currently under development</span>
      </div>
      <div class="status" id="status"><span class="dot"></span><span id="status-text">Starting runtimes</span></div>
      <button type="button" id="restart">Restart views</button>
    </header>
    <main>
      <section>
        <div class="panel-title">
          <h1>HD Wizard Joe</h1>
          <span>{safe_joe_meta}</span>
        </div>
        <iframe
          id="joe"
          title="HD Wizard Joe approved animation"
          src="http://127.0.0.1:{joe_port}{safe_joe_path}"
        ></iframe>
      </section>
      <section>
        <div class="panel-title">
          <h1>{safe_label}</h1>
          <span>{safe_current_meta}</span>
        </div>
        <iframe
          id="current"
          title="{safe_label} current animation package"
          src="http://127.0.0.1:{current_port}{safe_current_path}"
        ></iframe>
      </section>
    </main>
    <script>
      const status = document.getElementById("status");
      const statusText = document.getElementById("status-text");
      async function refreshStatus() {{
        try {{
          const response = await fetch("/health", {{ cache: "no-store" }});
          const health = await response.json();
          const ready = health.status === "ready";
          status.classList.toggle("ready", ready);
          statusText.textContent = ready
            ? "Live · HD Wizard Joe + {safe_label}"
            : "Waiting for character runtimes";
        }} catch (_error) {{
          status.classList.remove("ready");
          statusText.textContent = "Observer status unavailable";
        }}
      }}
      document.getElementById("restart").addEventListener("click", () => {{
        for (const id of ["joe", "current"]) {{
          const frame = document.getElementById(id);
          frame.src = frame.src;
        }}
      }});
      refreshStatus();
      setInterval(refreshStatus, 2000);
    </script>
  </body>
</html>
""".encode("utf-8")


def _performance_review_html(
    *,
    joe_port: int,
    observer_port: int,
    joe_path: str,
    joe_meta: str,
) -> bytes:
    safe_joe_path = html.escape(joe_path, quote=True)
    safe_joe_meta = html.escape(joe_meta)
    controller_origin = f"http://127.0.0.1:{observer_port}"
    performance_path = (
        "/?hd-performance=1&controller-origin="
        + html.escape(controller_origin, quote=True)
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Wizard Joe Audio Performance Review</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #eef1f3;
        color: #17201d;
      }}
      * {{ box-sizing: border-box; }}
      html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; }}
      body {{ display: grid; grid-template-rows: auto minmax(0, 1fr); }}
      header {{
        display: grid;
        gap: 8px;
        padding: 10px 14px;
        border-bottom: 1px solid #c9d0ce;
        background: #fff;
      }}
      .controls {{
        display: grid;
        grid-template-columns: minmax(220px, 1fr) auto minmax(180px, 1.2fr) auto auto;
        align-items: center;
        gap: 8px;
      }}
      select, button, input, textarea {{
        min-height: 36px;
        border: 1px solid #aeb8b4;
        border-radius: 6px;
        background: #fff;
        color: #17201d;
        font: inherit;
      }}
      select, textarea {{ padding: 6px 9px; }}
      button {{ padding: 0 11px; cursor: pointer; }}
      button:hover, button:focus-visible {{ background: #f1f5f3; outline: 2px solid #8ab8a7; }}
      button.primary {{ border-color: #1c755b; background: #1f7d61; color: #fff; }}
      button[aria-pressed="true"] {{ border-color: #1c755b; background: #e4f2ed; color: #155740; }}
      input[type="range"] {{ width: 100%; min-height: 28px; border: 0; }}
      .time {{ min-width: 104px; color: #56635e; font-variant-numeric: tabular-nums; font-size: 12px; }}
      .meta {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 10px;
        align-items: start;
      }}
      .now {{ min-width: 0; }}
      .now strong {{ display: block; font-size: 13px; }}
      .now span {{
        display: block;
        overflow: hidden;
        color: #66716d;
        font-size: 12px;
        text-overflow: ellipsis;
        white-space: nowrap;
      }}
      details {{ min-width: 0; font-size: 12px; }}
      summary {{ cursor: pointer; color: #40504a; }}
      .review {{
        display: grid;
        grid-template-columns: auto auto minmax(180px, 320px) auto;
        gap: 7px;
        align-items: center;
      }}
      .review textarea {{ min-height: 36px; height: 36px; resize: none; }}
      #save-state {{ color: #65706c; font-size: 11px; }}
      main {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); min-height: 0; }}
      section {{
        display: grid;
        grid-template-rows: 42px minmax(0, 1fr);
        min-width: 0;
        min-height: 0;
        border-right: 1px solid #c9d0ce;
        background: #fff;
      }}
      section:last-child {{ border-right: 0; }}
      .panel-title {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 7px 12px;
        border-bottom: 1px solid #dde2e0;
      }}
      h1 {{ margin: 0; color: #33413c; font-size: 13px; font-weight: 650; }}
      .panel-title span {{ color: #78827e; font-size: 11px; white-space: nowrap; }}
      iframe {{ width: 100%; height: 100%; border: 0; background: #fff; }}
      @media (max-width: 860px) {{
        .controls {{ grid-template-columns: minmax(0, 1fr) auto auto; }}
        .controls input[type="range"] {{ grid-column: 1 / -1; grid-row: 2; }}
        .review {{ grid-template-columns: repeat(3, auto); }}
        .review textarea {{ grid-column: 1 / -1; grid-row: 2; width: 100%; }}
        main {{ grid-template-columns: 1fr; grid-template-rows: repeat(2, minmax(0, 1fr)); }}
        section {{ border-right: 0; border-bottom: 1px solid #c9d0ce; }}
      }}
    </style>
  </head>
  <body>
    <header>
      <div class="controls">
        <select id="clip" aria-label="Wizard Joe audio performance"></select>
        <button type="button" id="play" class="primary" aria-label="Play or pause">▶ Play</button>
        <input id="seek" type="range" min="0" max="1000" value="0" aria-label="Performance position">
        <span class="time" id="time">0:00 / 0:00</span>
        <button type="button" id="restart" aria-label="Restart performance">↻ Restart</button>
      </div>
      <div class="meta">
        <div class="now">
          <strong id="cue">Loading choreography</strong>
          <span id="transcript"></span>
        </div>
        <div class="review">
          <button type="button" id="needs-work">Needs changes</button>
          <button type="button" id="approve">Approve choreography</button>
          <textarea id="notes" aria-label="Review notes" placeholder="Review note"></textarea>
          <span id="save-state">Unreviewed</span>
        </div>
      </div>
    </header>
    <main>
      <section>
        <div class="panel-title">
          <h1>Approved HD Wizard Joe</h1>
          <span>{safe_joe_meta}</span>
        </div>
        <iframe
          id="baseline"
          title="Approved HD Wizard Joe baseline"
          src="http://127.0.0.1:{joe_port}{safe_joe_path}"
        ></iframe>
      </section>
      <section>
        <div class="panel-title">
          <h1>Audio-Directed Walk and Talk</h1>
          <span id="performance-state">Candidate review</span>
        </div>
        <iframe
          id="performance"
          title="Wizard Joe audio-directed performance"
          src="http://127.0.0.1:{joe_port}{performance_path}"
        ></iframe>
      </section>
    </main>
    <audio id="audio" preload="auto"></audio>
    <script>
      const controllerOrigin = {json.dumps(controller_origin)};
      const audio = document.getElementById("audio");
      const clipSelect = document.getElementById("clip");
      const playButton = document.getElementById("play");
      const seek = document.getElementById("seek");
      const timeLabel = document.getElementById("time");
      const cueLabel = document.getElementById("cue");
      const transcriptLabel = document.getElementById("transcript");
      const notes = document.getElementById("notes");
      const saveState = document.getElementById("save-state");
      const needsWork = document.getElementById("needs-work");
      const approve = document.getElementById("approve");
      const performanceFrame = document.getElementById("performance");
      let manifest = null;
      let reviewState = null;
      let activeClip = null;
      let projectorReady = false;
      let raf = 0;

      const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
      const formatTime = (seconds) => {{
        if (!Number.isFinite(seconds)) return "0:00";
        const whole = Math.max(0, Math.floor(seconds));
        return `${{Math.floor(whole / 60)}}:${{String(whole % 60).padStart(2, "0")}}`;
      }};
      const easeSineOut = (value) => Math.sin(clamp(value, 0, 1) * Math.PI / 2);
      const decisionFor = (clipId) => (
        reviewState?.decisions?.[clipId] || {{ status: "unreviewed", notes: "" }}
      );
      const activeCue = (positionMs) => {{
        const cues = activeClip.performance.body_cues;
        return cues.find((item) => positionMs >= item.start_ms && positionMs < item.end_ms)
          || cues[cues.length - 1];
      }};
      const envelopeAt = (positionMs) => {{
        const envelope = activeClip.performance.speech_envelope;
        const index = clamp(
          Math.floor(positionMs / envelope.window_ms),
          0,
          envelope.values_milli.length - 1,
        );
        return Number(envelope.values_milli[index] || 0);
      }};
      const mouthStateAt = (positionMs, amplitude) => {{
        if (amplitude < 85) return "closed";
        const phase = Math.floor(positionMs / 170) % 4;
        return phase === 3 ? "closed" : "open";
      }};
      const poseForMouthState = (basePoseId, mouthState) => (
        manifest.mouth_pair_states?.[basePoseId]?.[mouthState] || basePoseId
      );
      const frameAt = (positionMs) => {{
        const approach = activeClip.performance.approach;
        if (positionMs < approach.end_ms) {{
          const elapsed = Math.max(0, positionMs - approach.start_ms);
          const frameMs = 1000 / approach.fps;
          const step = Math.floor(elapsed / frameMs);
          const poseIds = approach.pose_ids;
          const basePoseId = poseIds[step % poseIds.length];
          const amplitude = envelopeAt(positionMs);
          const mouthState = mouthStateAt(positionMs, amplitude);
          const progress = easeSineOut(elapsed / Math.max(1, approach.end_ms - approach.start_ms));
          const stride = Math.sin((elapsed / 1000) * Math.PI * 2.2);
          return {{
            poseId: poseForMouthState(basePoseId, mouthState),
            basePoseId,
            mouthState,
            nextPoseId: null,
            blendMilli: 0,
            scaleMilli: Math.round(
              approach.start_scale_milli
              + (approach.end_scale_milli - approach.start_scale_milli) * progress
            ),
            offsetXPx: Math.round(stride * 4),
            offsetYPx: Math.round(-Math.abs(stride) * 5),
            cue: "Walk toward camera",
          }};
        }}
        const cue = activeCue(positionMs);
        const amplitude = envelopeAt(positionMs);
        const beats = activeClip.performance.motion_beats || [];
        const beat = beats.reduce(
          (selected, item) => item.time_ms <= positionMs ? item : selected,
          null,
        );
        const basePoseId = beat?.pose_id || cue.pose_ids[0];
        const mouthState = mouthStateAt(positionMs, amplitude);
        return {{
          poseId: poseForMouthState(basePoseId, mouthState),
          basePoseId,
          mouthState,
          nextPoseId: null,
          blendMilli: 0,
          scaleMilli: approach.end_scale_milli,
          offsetXPx: Math.round(Math.sin(positionMs / 920) * 2),
          offsetYPx: Math.round(-amplitude / 500),
          cue: cue.label.replaceAll("_", " "),
        }};
      }};
      const sendFrame = (positionMs, override = null) => {{
        if (!projectorReady || !activeClip) return;
        const frame = override || frameAt(positionMs);
        performanceFrame.contentWindow.postMessage(
          {{
            type: "wizard-hd-performance-frame",
            ...frame,
            mediaPositionMs: Math.round(positionMs),
          }},
          `http://127.0.0.1:{joe_port}`,
        );
        cueLabel.textContent = frame.cue || "Performance";
      }};
      const refreshTransport = () => {{
        if (!activeClip) return;
        const duration = activeClip.audio.duration_ms / 1000;
        const position = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
        seek.value = String(duration > 0 ? Math.round(position * 1000 / duration) : 0);
        timeLabel.textContent = `${{formatTime(position)}} / ${{formatTime(duration)}}`;
        playButton.textContent = audio.paused ? "▶ Play" : "Ⅱ Pause";
        sendFrame(position * 1000);
      }};
      const animate = () => {{
        refreshTransport();
        raf = requestAnimationFrame(animate);
      }};
      const loadClip = (clipId) => {{
        const selected = manifest.clips.find((item) => item.clip_id === clipId);
        if (!selected) return;
        activeClip = selected;
        audio.pause();
        audio.src = `/performance-audio/${{encodeURIComponent(clipId)}}.mp3`;
        audio.load();
        transcriptLabel.textContent = selected.transcript;
        const decision = decisionFor(clipId);
        notes.value = decision.notes || "";
        saveState.textContent = decision.status.replaceAll("_", " ");
        needsWork.setAttribute("aria-pressed", String(decision.status === "needs_changes"));
        approve.setAttribute(
          "aria-pressed",
          String(decision.status === "approved_choreography"),
        );
        sendFrame(0);
        refreshTransport();
      }};
      const saveDecision = async (status) => {{
        if (!activeClip) return;
        const response = await fetch("/api/performance-review/decision", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            clip_id: activeClip.clip_id,
            status,
            notes: notes.value,
          }}),
        }});
        if (!response.ok) throw new Error(await response.text());
        reviewState = await response.json();
        loadClip(activeClip.clip_id);
      }};

      window.addEventListener("message", (event) => {{
        if (
          event.origin === `http://127.0.0.1:{joe_port}`
          && event.source === performanceFrame.contentWindow
          && event.data?.type === "wizard-hd-performance-ready"
        ) {{
          projectorReady = true;
          sendFrame((audio.currentTime || 0) * 1000);
        }}
      }});
      clipSelect.addEventListener("change", () => loadClip(clipSelect.value));
      playButton.addEventListener("click", async () => {{
        if (!activeClip) return;
        if (audio.ended) audio.currentTime = 0;
        if (audio.paused) await audio.play();
        else audio.pause();
      }});
      document.getElementById("restart").addEventListener("click", async () => {{
        audio.currentTime = 0;
        await audio.play();
      }});
      seek.addEventListener("input", () => {{
        if (!activeClip) return;
        audio.currentTime = activeClip.audio.duration_ms * Number(seek.value) / 1000000;
        refreshTransport();
      }});
      audio.addEventListener("ended", () => {{
        const settle = activeClip.performance.settle_pose_id;
        sendFrame(activeClip.audio.duration_ms, {{
          poseId: settle,
          nextPoseId: null,
          blendMilli: 0,
          scaleMilli: activeClip.performance.approach.end_scale_milli,
          offsetXPx: 0,
          offsetYPx: 0,
          cue: "Settled",
        }});
      }});
      needsWork.addEventListener("click", () => void saveDecision("needs_changes"));
      approve.addEventListener("click", () => void saveDecision("approved_choreography"));

      Promise.all([
        fetch("/api/performance-review/manifest", {{ cache: "no-store" }}).then(r => r.json()),
        fetch("/api/performance-review/state", {{ cache: "no-store" }}).then(r => r.json()),
      ]).then(([loadedManifest, loadedState]) => {{
        manifest = loadedManifest;
        reviewState = loadedState;
        for (const clip of manifest.clips) {{
          const option = document.createElement("option");
          option.value = clip.clip_id;
          option.textContent = clip.display_name;
          clipSelect.append(option);
        }}
        loadClip(manifest.clips[0].clip_id);
        cancelAnimationFrame(raf);
        animate();
      }}).catch((error) => {{
        cueLabel.textContent = "Review failed to load";
        transcriptLabel.textContent = error instanceof Error ? error.message : String(error);
      }});
    </script>
  </body>
</html>
""".encode("utf-8")


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            json.dump(value, target, indent=2)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
        Path(temp_name).replace(path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _record_review_decision(
    state_path: Path,
    manifest: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    clip_ids = {
        str(item["clip_id"])
        for item in manifest.get("clips", [])
        if isinstance(item, dict) and isinstance(item.get("clip_id"), str)
    }
    clip_id = payload.get("clip_id")
    status = payload.get("status")
    notes = payload.get("notes", "")
    if clip_id not in clip_ids:
        raise ValueError("unknown_clip")
    if status not in {"unreviewed", "needs_changes", "approved_choreography"}:
        raise ValueError("invalid_status")
    if not isinstance(notes, str) or len(notes) > 4000:
        raise ValueError("invalid_notes")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_review_state") from exc
    if not isinstance(state, dict) or not isinstance(state.get("decisions"), dict):
        raise ValueError("invalid_review_state")
    state["decisions"][clip_id] = {
        "status": status,
        "notes": notes.strip(),
    }
    _atomic_write_json(state_path, state)
    return state


class ObserverHandler(BaseHTTPRequestHandler):
    joe_port = 0
    current_port = 0
    joe_path = "/?hd-sequence=approved_hd_frames"
    joe_meta = "250 approved source frames"
    current_path = "/?embedded=1"
    current_label = ""
    current_meta = ""
    review_character_id: str | None = None
    review_projection = False
    runtime_admitted = False
    performance_manifest: dict[str, Any] | None = None
    performance_manifest_path: Path | None = None
    performance_review_state_path: Path | None = None
    observer_port = 0

    def do_GET(self) -> None:
        request_path = urlsplit(self.path).path
        if request_path in {"/", "/index.html"}:
            if self.performance_manifest is not None:
                body = _performance_review_html(
                    joe_port=self.joe_port,
                    observer_port=self.observer_port,
                    joe_path=self.joe_path,
                    joe_meta=self.joe_meta,
                )
            else:
                body = _observer_html(
                    joe_port=self.joe_port,
                    current_port=self.current_port,
                    joe_path=self.joe_path,
                    joe_meta=self.joe_meta,
                    current_path=self.current_path,
                    current_label=self.current_label,
                    current_meta=self.current_meta,
                )
            self._respond(200, "text/html; charset=utf-8", body)
            return
        if request_path == "/health":
            joe = _health(self.joe_port)
            current = _health(self.current_port)
            payload = _observer_health(
                joe=joe,
                current=current,
                current_label=self.current_label,
                current_meta=self.current_meta,
                review_character_id=self.review_character_id,
                review_projection=self.review_projection,
                runtime_admitted=self.runtime_admitted,
            )
            self._respond(
                200,
                "application/json",
                json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            )
            return
        if request_path == "/api/performance-review/manifest":
            if self.performance_manifest is None:
                self._respond(404, "application/json", b'{"detail":"Not found"}')
                return
            self._respond(
                200,
                "application/json",
                json.dumps(self.performance_manifest, separators=(",", ":")).encode(
                    "utf-8"
                ),
            )
            return
        if request_path == "/api/performance-review/state":
            if self.performance_review_state_path is None:
                self._respond(404, "application/json", b'{"detail":"Not found"}')
                return
            try:
                body = self.performance_review_state_path.read_bytes()
            except OSError:
                self._respond(500, "application/json", b'{"detail":"State unavailable"}')
                return
            self._respond(200, "application/json", body)
            return
        if request_path.startswith("/performance-audio/"):
            self._serve_performance_audio(request_path)
            return
        self._respond(404, "text/plain; charset=utf-8", b"Not found\n")

    def do_POST(self) -> None:
        request_path = urlsplit(self.path).path
        if request_path != "/api/performance-review/decision":
            self._respond(404, "text/plain; charset=utf-8", b"Not found\n")
            return
        if (
            self.performance_manifest is None
            or self.performance_review_state_path is None
        ):
            self._respond(404, "application/json", b'{"detail":"Not found"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 1 or length > 16 * 1024:
            self._respond(400, "application/json", b'{"detail":"Invalid body"}')
            return
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("invalid_body")
            state = _record_review_decision(
                self.performance_review_state_path,
                self.performance_manifest,
                payload,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            self._respond(
                400,
                "application/json",
                json.dumps({"detail": str(exc)}, separators=(",", ":")).encode("utf-8"),
            )
            return
        self._respond(
            200,
            "application/json",
            json.dumps(state, separators=(",", ":")).encode("utf-8"),
        )

    def _serve_performance_audio(self, request_path: str) -> None:
        if (
            self.performance_manifest is None
            or self.performance_manifest_path is None
        ):
            self._respond(404, "text/plain; charset=utf-8", b"Not found\n")
            return
        filename = unquote(request_path.removeprefix("/performance-audio/"))
        if not filename.endswith(".mp3") or "/" in filename or "\\" in filename:
            self._respond(404, "text/plain; charset=utf-8", b"Not found\n")
            return
        clip_id = filename[:-4]
        record = next(
            (
                item
                for item in self.performance_manifest.get("clips", [])
                if isinstance(item, dict) and item.get("clip_id") == clip_id
            ),
            None,
        )
        if not isinstance(record, dict):
            self._respond(404, "text/plain; charset=utf-8", b"Not found\n")
            return
        audio = record.get("audio")
        if not isinstance(audio, dict) or not isinstance(audio.get("path"), str):
            self._respond(404, "text/plain; charset=utf-8", b"Not found\n")
            return
        root = self.performance_manifest_path.parent.resolve()
        path = (root / audio["path"]).resolve()
        if root not in path.parents or not path.is_file():
            self._respond(404, "text/plain; charset=utf-8", b"Not found\n")
            return
        self._respond(200, "audio/mpeg", path.read_bytes())

    def log_message(self, format: str, *args: object) -> None:
        return

    def _respond(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def _terminate(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 4.0
    for process in processes:
        if process.poll() is not None:
            continue
        timeout = max(0.0, deadline - time.monotonic())
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2.0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an isolated HD Joe/current-character observer."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8665)
    parser.add_argument("--joe-port", type=int, default=8666)
    parser.add_argument("--current-port", type=int, default=8667)
    parser.add_argument("--joe-sequence", default="approved_hd_frames")
    parser.add_argument(
        "--joe-review-library-index",
        type=Path,
        help=(
            "Project the baseline from an isolated review-only HD library "
            "instead of loading the default canonical library."
        ),
    )
    parser.add_argument("--joe-meta", default="250 approved source frames")
    parser.add_argument(
        "--performance-review-manifest",
        type=Path,
        help=(
            "Run the Wizard Joe audio-performance review surface using the "
            "manifest-bound HTML audio clock and HD pixel projector."
        ),
    )
    parser.add_argument(
        "--review-sequence",
        help="Compare a second Wizard Joe HD sequence instead of starting another character.",
    )
    parser.add_argument(
        "--review-library-index",
        type=Path,
        help=(
            "Project --review-sequence from an isolated review-only HD "
            "library on the current-character runtime."
        ),
    )
    parser.add_argument(
        "--current-package",
        type=Path,
        default=DEFAULT_CURRENT_PACKAGE,
    )
    parser.add_argument("--current-label", default="Serena Quill")
    parser.add_argument("--current-meta", default="current package candidate")
    parser.add_argument("--startup-timeout", type=float, default=20.0)
    args = parser.parse_args()

    if args.host != "127.0.0.1":
        parser.error("the observer binds only to 127.0.0.1")
    if args.review_library_index and not args.review_sequence:
        parser.error("--review-library-index requires --review-sequence")
    if args.performance_review_manifest and (
        args.review_sequence or args.review_library_index
    ):
        parser.error(
            "--performance-review-manifest cannot be combined with review-sequence options"
        )
    performance_review = bool(args.performance_review_manifest)
    review_runtime = bool(args.review_library_index)
    active_ports = (
        {args.port, args.joe_port}
        if (args.review_sequence and not review_runtime) or performance_review
        else {args.port, args.joe_port, args.current_port}
    )
    expected_port_count = (
        2
        if (args.review_sequence and not review_runtime) or performance_review
        else 3
    )
    if len(active_ports) != expected_port_count or any(
        port < 1 or port > 65535 for port in active_ports
    ):
        parser.error("observer and active runtime ports must be distinct valid TCP ports")
    current_package = args.current_package.expanduser().resolve()
    if not args.review_sequence and not current_package.is_file():
        parser.error(f"current character package not found: {current_package}")
    review_library_index = (
        args.review_library_index.expanduser().resolve()
        if args.review_library_index
        else None
    )
    joe_review_library_index = (
        args.joe_review_library_index.expanduser().resolve()
        if args.joe_review_library_index
        else None
    )
    if (
        joe_review_library_index is not None
        and not joe_review_library_index.is_file()
    ):
        parser.error(
            "Joe review library index not found: "
            f"{joe_review_library_index}"
        )
    if review_library_index is not None and not review_library_index.is_file():
        parser.error(
            f"review library index not found: {review_library_index}"
        )
    review_identity: dict[str, Any] = {}
    if review_library_index is not None:
        try:
            review_identity = json.loads(
                review_library_index.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            parser.error(f"review library index is unreadable: {exc}")
        if not isinstance(review_identity, dict):
            parser.error("review library index must contain a JSON object")
    performance_manifest_path = (
        args.performance_review_manifest.expanduser().resolve()
        if args.performance_review_manifest
        else None
    )
    performance_manifest: dict[str, Any] | None = None
    performance_review_state_path: Path | None = None
    if performance_manifest_path is not None:
        if not performance_manifest_path.is_file():
            parser.error(
                f"performance review manifest not found: {performance_manifest_path}"
            )
        try:
            performance_manifest = json.loads(
                performance_manifest_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            parser.error(f"performance review manifest is unreadable: {exc}")
        if (
            not isinstance(performance_manifest, dict)
            or not isinstance(performance_manifest.get("clips"), list)
            or not performance_manifest["clips"]
        ):
            parser.error("performance review manifest must contain clips")
        if DEFAULT_MOUTH_PAIR_MANIFEST.is_file():
            try:
                mouth_pair_manifest = json.loads(
                    DEFAULT_MOUTH_PAIR_MANIFEST.read_text(encoding="utf-8")
                )
                performance_manifest = {
                    **performance_manifest,
                    "mouth_pair_states": _mouth_pair_states(mouth_pair_manifest),
                }
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                parser.error(f"mouth-pair manifest is unreadable: {exc}")
            if joe_review_library_index is None:
                if not DEFAULT_MOUTH_REVIEW_INDEX.is_file():
                    parser.error(
                        "mouth-pair review index is missing: "
                        f"{DEFAULT_MOUTH_REVIEW_INDEX}"
                    )
                joe_review_library_index = DEFAULT_MOUTH_REVIEW_INDEX.resolve()
        performance_review_state_path = (
            performance_manifest_path.parent / "review-state.json"
        )
        if not performance_review_state_path.is_file():
            parser.error(
                f"performance review state not found: {performance_review_state_path}"
            )

    ObserverHandler.joe_port = args.joe_port
    ObserverHandler.current_port = (
        args.current_port
        if review_runtime
        else args.joe_port
        if args.review_sequence or performance_review
        else args.current_port
    )
    ObserverHandler.observer_port = args.port
    ObserverHandler.performance_manifest = performance_manifest
    ObserverHandler.performance_manifest_path = performance_manifest_path
    ObserverHandler.performance_review_state_path = performance_review_state_path
    ObserverHandler.joe_path = f"/?hd-sequence={args.joe_sequence}"
    ObserverHandler.joe_meta = args.joe_meta
    ObserverHandler.current_path = (
        (
            f"/?hd-sequence={args.review_sequence}&hd-center-isolated=1"
            if review_identity.get("identity_side") in {"left", "right"}
            else f"/?hd-sequence={args.review_sequence}"
        )
        if args.review_sequence
        else "/?embedded=1"
    )
    ObserverHandler.current_label = args.current_label
    ObserverHandler.current_meta = args.current_meta
    ObserverHandler.review_character_id = (
        review_identity.get("character_id")
        if isinstance(review_identity.get("character_id"), str)
        else None
    )
    ObserverHandler.review_projection = (
        review_identity.get("review_projection") is True
    )
    ObserverHandler.runtime_admitted = (
        review_identity.get("runtime_admitted") is True
    )
    server = ThreadingHTTPServer((args.host, args.port), ObserverHandler)
    processes: list[subprocess.Popen[bytes]] = []
    stopping = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        if stopping.is_set():
            return
        stopping.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    common = [sys.executable, str(RUNNER), "--host", args.host, "--quiet"]
    try:
        joe_command = common + ["--port", str(args.joe_port)]
        if joe_review_library_index is not None:
            joe_command.extend(
                [
                    "--review-library-index",
                    str(joe_review_library_index),
                ]
            )
        joe = subprocess.Popen(joe_command, cwd=ROOT)
        processes.append(joe)
        _wait_ready(joe, args.joe_port, args.startup_timeout)
        if review_runtime:
            current = subprocess.Popen(
                common
                + [
                    "--port",
                    str(args.current_port),
                    "--review-library-index",
                    str(review_library_index),
                ],
                cwd=ROOT,
            )
            processes.append(current)
            _wait_ready(current, args.current_port, args.startup_timeout)
        elif not args.review_sequence and not performance_review:
            current = subprocess.Popen(
                common
                + [
                    "--port",
                    str(args.current_port),
                    "--character-package",
                    str(current_package),
                ],
                cwd=ROOT,
            )
            processes.append(current)
            _wait_ready(current, args.current_port, args.startup_timeout)
        print(
            f"Character observer ready at http://{args.host}:{args.port}/ "
            f"(HD Joe {args.joe_port}, {args.current_label} "
            f"{ObserverHandler.current_port})",
            flush=True,
        )
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        _terminate(processes)


if __name__ == "__main__":
    main()
