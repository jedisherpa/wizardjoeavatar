#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the WizardJoeAvatar demo server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--cols", type=int, default=240)
    parser.add_argument("--rows", type=int, default=135)
    parser.add_argument("--fps", type=float, default=24.0)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))

    import uvicorn
    from wizard_avatar.server import create_app

    app = create_app(cols=args.cols, rows=args.rows, fps=args.fps)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
