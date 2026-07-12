#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.render_image import frame_to_image


ANIMATION_DIR = ROOT / "evidence" / "wizard" / "animations"


def apply(source: ProceduralWizardFrameSource, command_type: str, payload=None) -> None:
    result = source.apply_command_sync(WizardCommand(command_type, payload or {}))
    if not result.ok:
        raise RuntimeError(result.message)


def collect_frames(
    source: ProceduralWizardFrameSource,
    seconds: float,
    output_fps: int = 12,
    cell_size: Tuple[int, int] = (3, 3),
):
    stride = max(1, round(source.fps / output_fps))
    total = max(1, round(source.fps * seconds))
    frames = []
    for index in range(total):
        frame = source.render_next_frame()
        if index % stride == 0:
            frames.append(frame_to_image(frame, cell_size))
    return frames


def save_gif(frames: List, path: Path, fps: int = 12) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = round(1000 / fps)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
    )


def render_clip(label: str, commands: Iterable[Tuple[str, dict]], seconds: float) -> Path:
    source = ProceduralWizardFrameSource()
    apply(source, "reset", {})
    for command_type, payload in commands:
        apply(source, command_type, payload)
    frames = collect_frames(source, seconds)
    path = ANIMATION_DIR / f"{label}.gif"
    save_gif(frames, path)
    return path


def main() -> None:
    clips = [
        ("idle-breathe", [], 3.0),
        ("speaking", [("speak", {"text": "The stars prefer a tidy spellbook.", "duration_ms": 2600})], 3.0),
        ("thinking", [("action", {"action": "thinking", "duration_ms": 2600})], 3.0),
        ("magic-cast", [("action", {"action": "magic_cast", "duration_ms": 2600})], 3.0),
        ("walk-toward", [("move", {"x": 0.0, "z": 3.0, "speed": 0.9})], 4.0),
    ]
    manifest = []
    montage_frames = []
    for label, commands, seconds in clips:
        path = render_clip(label, commands, seconds)
        manifest.append({"label": label, "path": str(path.relative_to(ROOT))})

        source = ProceduralWizardFrameSource()
        apply(source, "reset", {})
        for command_type, payload in commands:
            apply(source, command_type, payload)
        montage_frames.extend(collect_frames(source, min(seconds, 2.2)))

    montage = ANIMATION_DIR / "wizard-animation-montage.gif"
    save_gif(montage_frames, montage)
    manifest.insert(0, {"label": "montage", "path": str(montage.relative_to(ROOT))})
    (ANIMATION_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(montage)


if __name__ == "__main__":
    main()
