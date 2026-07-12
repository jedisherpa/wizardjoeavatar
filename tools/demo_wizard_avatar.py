#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.render_image import frame_to_png


DEMO_DIR = ROOT / "evidence" / "wizard" / "demo"


def apply(source: ProceduralWizardFrameSource, command_type: str, payload=None) -> None:
    result = source.apply_command_sync(WizardCommand(command_type, payload or {}))
    if not result.ok:
        raise RuntimeError(result.message)


def run_for(source: ProceduralWizardFrameSource, seconds: float, label: str, snapshots) -> None:
    frames = max(1, round(source.fps * seconds))
    for _ in range(frames):
        frame = source.render_next_frame()
    path = DEMO_DIR / f"{len(snapshots):02d}-{label}.png"
    frame_to_png(frame, path)
    snapshots.append(
        {
            "label": label,
            "path": str(path.relative_to(ROOT)),
            "state": source.current_state().as_public_dict(),
        }
    )


def main() -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    source = ProceduralWizardFrameSource()
    snapshots = []

    run_for(source, 3.0, "idle", snapshots)
    source.current_state().time_seconds = 0.02
    run_for(source, 0.2, "blink", snapshots)
    apply(source, "expression", {"expression": "happy"})
    run_for(source, 0.5, "happy", snapshots)
    apply(source, "speak", {"text": "The stars prefer a tidy spellbook.", "duration_ms": 2200})
    run_for(source, 2.2, "speak", snapshots)
    apply(source, "move", {"x": -2.0, "z": 5.0})
    run_for(source, 2.2, "walk-left", snapshots)
    apply(source, "move", {"x": 2.0, "z": 5.0})
    run_for(source, 3.5, "walk-right", snapshots)
    apply(source, "move", {"x": 0.0, "z": 7.0})
    run_for(source, 2.8, "walk-away", snapshots)
    apply(source, "move", {"x": 0.0, "z": 3.0})
    run_for(source, 3.0, "walk-toward", snapshots)
    apply(source, "move", {"x": -1.7, "z": 3.3})
    run_for(source, 2.2, "walk-front-left", snapshots)
    apply(source, "move", {"x": 1.7, "z": 6.7})
    run_for(source, 3.0, "walk-back-right", snapshots)
    apply(source, "circle", {"center_x": 0, "center_z": 5, "radius": 2, "clockwise": True, "duration_seconds": 10})
    run_for(source, 10.5, "clockwise-circle", snapshots)
    apply(source, "circle", {"center_x": 0, "center_z": 5, "radius": 2, "clockwise": False, "duration_seconds": 10})
    run_for(source, 10.5, "counterclockwise-circle", snapshots)
    apply(source, "figure_eight", {"center_x": 0, "center_z": 5, "radius": 1.4})
    run_for(source, 9.0, "figure-eight", snapshots)
    apply(source, "move", {"x": 0.0, "z": 5.0})
    run_for(source, 3.0, "center", snapshots)
    for action in ["thinking", "pointing", "explaining", "magic_cast", "reaction"]:
        apply(source, "action", {"action": action, "duration_ms": 1800})
        run_for(source, 1.8, action, snapshots)
    apply(source, "expression", {"expression": "neutral"})
    apply(source, "action", {"action": "idle", "duration_ms": 0})
    run_for(source, 10.0, "neutral-idle", snapshots)

    manifest = {
        "sequence": [
            "idle",
            "blink",
            "happy",
            "speak",
            "walk-left",
            "walk-right",
            "walk-away",
            "walk-toward",
            "walk-front-left",
            "walk-back-right",
            "clockwise-circle",
            "counterclockwise-circle",
            "figure-eight",
            "center",
            "thinking",
            "pointing",
            "explaining",
            "magic_cast",
            "reaction",
            "neutral-idle",
        ],
        "snapshots": snapshots,
        "server_run_command": "python3 tools/run_wizard_avatar_server.py --port 8000",
        "browser_url": "http://127.0.0.1:8000/",
    }
    (DEMO_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(DEMO_DIR / "manifest.json")


if __name__ == "__main__":
    main()
