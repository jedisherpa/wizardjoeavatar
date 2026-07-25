#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import URLError
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
) -> bytes:
    safe_label = html.escape(current_label)
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
          <span>250 approved source frames</span>
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


class ObserverHandler(BaseHTTPRequestHandler):
    joe_port = 0
    current_port = 0
    joe_path = "/?hd-sequence=approved_hd_frames"
    current_path = "/?embedded=1"
    current_label = ""
    current_meta = ""
    review_character_id: str | None = None
    review_projection = False
    runtime_admitted = False

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            body = _observer_html(
                joe_port=self.joe_port,
                current_port=self.current_port,
                joe_path=self.joe_path,
                current_path=self.current_path,
                current_label=self.current_label,
                current_meta=self.current_meta,
            )
            self._respond(200, "text/html; charset=utf-8", body)
            return
        if self.path == "/health":
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
        self._respond(404, "text/plain; charset=utf-8", b"Not found\n")

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
    review_runtime = bool(args.review_library_index)
    active_ports = (
        {args.port, args.joe_port}
        if args.review_sequence and not review_runtime
        else {args.port, args.joe_port, args.current_port}
    )
    expected_port_count = (
        2 if args.review_sequence and not review_runtime else 3
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

    ObserverHandler.joe_port = args.joe_port
    ObserverHandler.current_port = (
        args.current_port
        if review_runtime
        else args.joe_port
        if args.review_sequence
        else args.current_port
    )
    ObserverHandler.joe_path = f"/?hd-sequence={args.joe_sequence}"
    ObserverHandler.current_path = (
        f"/?hd-sequence={args.review_sequence}"
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
        joe = subprocess.Popen(common + ["--port", str(args.joe_port)], cwd=ROOT)
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
        elif not args.review_sequence:
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
