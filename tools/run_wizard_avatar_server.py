#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any


class ServerShutdownSignal:
    def __init__(self) -> None:
        self._server: Any = None
        self.requested = False

    def attach(self, server: Any) -> None:
        self._server = server
        if self.requested:
            server.should_exit = True

    def request(self) -> None:
        self.requested = True
        if self._server is not None:
            self._server.should_exit = True


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the WizardJoeAvatar demo server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--cols", type=int, default=240)
    parser.add_argument("--rows", type=int, default=135)
    parser.add_argument("--fps", type=float, default=24.0)
    parser.add_argument(
        "--character-package",
        type=Path,
        help=(
            "Boot one hash-verified character package through the existing "
            "Python hub and server. Defaults to Wizard Joe."
        ),
    )
    parser.add_argument(
        "--review-library-index",
        type=Path,
        help=(
            "Load an isolated package-local HD library for loopback review. "
            "The index must be review-only and runtime-admitted false."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress routine access logs for long-running local or evidence sessions.",
    )
    parser.add_argument(
        "--companion",
        action="store_true",
        help="Enable app-owned lifecycle and authentication using WIZARD_COMPANION_APP_TOKEN.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))

    import uvicorn
    from wizard_avatar.character_package import load_character_package
    from wizard_avatar.frame_source import ProceduralWizardFrameSource
    from wizard_avatar.hd_rgba_frame_source import HDPoseFrameSource
    from wizard_avatar.server import create_app, is_literal_loopback_host

    environment_companion_mode = os.environ.get("WIZARD_COMPANION_MODE", "").lower() in {
        "1", "true", "yes", "on"
    }
    companion_mode = args.companion or environment_companion_mode
    if not is_literal_loopback_host(args.host):
        parser.error("Wizard Joe only supports a literal loopback --host")

    shutdown_signal = ServerShutdownSignal()
    package = (
        load_character_package(args.character_package)
        if args.character_package is not None
        else None
    )
    frame_source = (
        HDPoseFrameSource(
            fps=args.fps,
            character_package_path=args.character_package,
        )
        if package is not None
        and package.renderer_adapter_id == "asciline.hd_rgba_pose.v1"
        else ProceduralWizardFrameSource(
            args.cols,
            args.rows,
            args.fps,
            character_package_path=args.character_package,
        )
    )
    app = create_app(
        frame_source,
        companion_mode=companion_mode,
        shutdown_signal=shutdown_signal.request,
        runtime_server_config={
            "host": args.host,
            "port": args.port,
            "companion_mode": companion_mode,
            "quiet": args.quiet,
            "render_mode": frame_source.render_mode,
        },
        hd_review_index_path=args.review_library_index,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=args.host,
            port=args.port,
            access_log=not args.quiet,
            log_level="warning" if args.quiet else "info",
        )
    )
    shutdown_signal.attach(server)
    server.run()


if __name__ == "__main__":
    main()
