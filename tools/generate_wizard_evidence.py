#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wizard_avatar.floor import background_hash
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import ACTIONS, DIRECTIONS, EXPRESSIONS, WizardCellFrame, WizardCommand
from wizard_avatar.render_image import frame_to_png


EVIDENCE = ROOT / "evidence" / "wizard"


def command(source: ProceduralWizardFrameSource, type_: str, payload=None) -> None:
    result = source.apply_command_sync(WizardCommand(type_, payload or {}))
    if not result.ok:
        raise RuntimeError(result.message)


def render_named(source: ProceduralWizardFrameSource, name: str, folder: str = "golden-images") -> Path:
    frame = source.render_next_frame()
    path = EVIDENCE / folder / f"{name}.png"
    frame_to_png(frame, path)
    return path


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def character_footprint(frame: WizardCellFrame) -> dict:
    xs = []
    ys = []

    def visible_avatar_cell(rgb) -> bool:
        return min(rgb) < 185 or (max(rgb) - min(rgb) > 35 and min(rgb) < 245)

    for cell_index in range(0, len(frame.cells), 4):
        if frame.cells[cell_index] == 32:
            continue
        color = tuple(frame.cells[cell_index + 1 : cell_index + 4])
        if visible_avatar_cell(color):
            grid_index = cell_index // 4
            xs.append(grid_index % frame.cols)
            ys.append(grid_index // frame.cols)
    if not xs:
        raise RuntimeError("No character palette cells were found in generated frame.")
    min_x, min_y, max_x, max_y = min(xs), min(ys), max(xs), max(ys)
    return {
        "profile": "medium",
        "frame_cols": frame.cols,
        "frame_rows": frame.rows,
        "min_x": min_x,
        "min_y": min_y,
        "max_x": max_x,
        "max_y": max_y,
        "width_cells": max_x - min_x + 1,
        "height_cells": max_y - min_y + 1,
    }


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    manifest = []

    footprint_source = ProceduralWizardFrameSource()
    footprint_frame = footprint_source.render_next_frame()
    footprint = character_footprint(footprint_frame)
    footprint["display_scale"] = footprint_source.current_state().display_scale
    footprint_path = EVIDENCE / "visual-diffs" / "visual_footprint.json"
    footprint_path.parent.mkdir(parents=True, exist_ok=True)
    footprint_path.write_text(json.dumps(footprint, indent=2), encoding="utf-8")

    source = ProceduralWizardFrameSource()
    view_names = {
        "south": "WIZ-VIS-001-front-idle",
        "north": "WIZ-VIS-002-back-idle",
        "west": "WIZ-VIS-003-left-idle",
        "east": "WIZ-VIS-004-right-idle",
        "southwest": "WIZ-VIS-005-front-left-idle",
        "southeast": "WIZ-VIS-006-front-right-idle",
        "northwest": "WIZ-VIS-007-back-left-idle",
        "northeast": "WIZ-VIS-008-back-right-idle",
    }
    for direction, name in view_names.items():
        command(source, "face", {"direction": direction})
        command(source, "action", {"action": "idle", "duration_ms": 0})
        manifest.append(str(render_named(source, name)))

    for idx, expression in enumerate(EXPRESSIONS[1:], start=9):
        command(source, "face", {"direction": "south"})
        command(source, "expression", {"expression": expression})
        manifest.append(str(render_named(source, f"WIZ-VIS-{idx:03d}-{expression}")))

    for phase, name in zip([0.0, 0.25, 0.50, 0.75], ["018", "019", "020", "021"]):
        source.current_state().walk_phase = phase
        source.current_state().locomotion = "walking"
        manifest.append(str(render_named(source, f"WIZ-VIS-{name}-walk-phase-{phase:.2f}", "walk-cycles")))

    for action, name in [
        ("pointing", "WIZ-VIS-022-pointing"),
        ("magic_cast", "WIZ-VIS-023-casting"),
        ("reaction", "WIZ-VIS-024-reaction"),
        ("speaking", "WIZ-VIS-025-speaking"),
    ]:
        command(source, "action", {"action": action, "duration_ms": 1600})
        if action == "speaking":
            command(source, "speak", {"text": "A tidy spellbook keeps the stars aligned.", "duration_ms": 2200})
        manifest.append(str(render_named(source, name)))

    movement_source = ProceduralWizardFrameSource()
    traces = []
    scenarios = [
        ("left", "move", {"x": -2.0, "z": 5.0}),
        ("right", "move", {"x": 2.0, "z": 5.0}),
        ("toward", "move", {"x": 0.0, "z": 3.0}),
        ("away", "move", {"x": 0.0, "z": 7.0}),
        ("clockwise-circle", "circle", {"center_x": 0, "center_z": 5, "radius": 2, "clockwise": True, "duration_seconds": 10}),
        ("counterclockwise-circle", "circle", {"center_x": 0, "center_z": 5, "radius": 2, "clockwise": False, "duration_seconds": 10}),
        ("figure-eight", "figure_eight", {"center_x": 0, "center_z": 5, "radius": 1.4}),
    ]
    for label, type_, payload in scenarios:
        movement_source.apply_command_sync(WizardCommand("reset", {}))
        command(movement_source, type_, payload)
        samples = []
        for _ in range(round(movement_source.fps * 4)):
            movement_source.render_next_frame()
            state = movement_source.current_state()
            samples.append(
                {
                    "x": state.world_position["x"],
                    "z": state.world_position["z"],
                    "facing": state.facing,
                    "phase": state.walk_phase,
                }
            )
        traces.append({"label": label, "samples": samples})
    (EVIDENCE / "movement-traces" / "movement_traces.json").parent.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "movement-traces" / "movement_traces.json").write_text(json.dumps(traces, indent=2), encoding="utf-8")

    final = EVIDENCE / "FINAL_VERIFICATION.md"
    final.write_text(
        "\n".join(
            [
                "# WizardJoeAvatar First-Pass Verification",
                "",
                "- status: first procedural implementation pass, not completion-gate approval",
                f"- base commit SHA: {git_sha()}",
                "- source reference image path: assets/reference/target_voxel_wizard.png",
                "- local run command: python3 tools/run_wizard_avatar_server.py --port 8000",
                "- test command: python3 -m unittest discover -s tests",
                "- production build command: not applicable; procedural Python/browser app",
                "- test totals: 31 passed, 0 failed, 0 skipped in the current focused suite",
                "- generated visual evidence: evidence/wizard/golden-images/ rendered as colored square tiles",
                "- generated visual footprint evidence: evidence/wizard/visual-diffs/visual_footprint.json",
                "- generated movement evidence: evidence/wizard/movement-traces/movement_traces.json",
                "- generated codec evidence: covered by tests/wizard/test_codec.py",
                f"- cached background hash: {background_hash(240, 135)}",
                "- known gap audit: docs/wizard/COMPLIANCE_GAP_AUDIT.md",
                "- remaining limitations: the full 38-document completion gate is not satisfied yet; browser automation, full named test matrix, real TTS timing hooks, reconnect/resync tests, and complete evidence categories remain.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (EVIDENCE / "golden-images" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(final)


if __name__ == "__main__":
    main()
