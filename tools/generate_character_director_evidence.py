#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.performance_application import PerformanceApplication
from wizard_avatar.permission_world import CapabilityPermissionV1, PermissionWorldStateV1
from wizard_avatar.render_image import frame_to_png


def apply(source: ProceduralWizardFrameSource, command: str, payload: dict) -> None:
    result = source.apply_command_sync(WizardCommand(command, payload))
    if not result.ok:
        raise RuntimeError(f"{command} failed: {result.message}")


def permission(kind: str, posture: str) -> CapabilityPermissionV1:
    granted = posture == "granted"
    return CapabilityPermissionV1(
        capability_kind=kind,
        posture=posture,
        required_scope_class="current_surface",
        granted_scope_class="current_surface" if granted else None,
        purpose_code="character_director_evidence",
        granted_at_ms=1 if granted else None,
        affected_surfaces=("companion.stage",),
        app_link_state="linked",
        expires_at_ms=None,
        revoked=False,
    )


def permission_source(
    effect_posture: str,
    staff_posture: str,
) -> ProceduralWizardFrameSource:
    source = ProceduralWizardFrameSource(240, 135, 24)
    manifest = {
        "permission_world": {
            "bindings": {
                "world_state_ids": ["default"],
                "effect_ids": ["magic_effect"],
                "prop_ids": ["staff"],
            }
        },
        "capabilities": [
            {
                "admission": "graph_admitted",
                "mapping": {
                    "effect_ids": ["magic_effect"],
                    "prop_ids": ["staff"],
                },
            }
        ]
    }
    application = PerformanceApplication(
        "character-director-evidence",
        character_id=source.character_package.character_id,
        capability_manifest=manifest,
    )
    state = PermissionWorldStateV1.build(
        source_epoch=f"evidence:{effect_posture}:{staff_posture}",
        observed_at_ms=1,
        permissions=(
            permission("world_state:default", "granted"),
            permission("effect:magic_effect", effect_posture),
            permission("prop:staff", staff_posture),
        ),
    )
    application.accept_permission_world(state)
    application.apply(source.controller, 1_000)
    return source


def visible_bounds(frame) -> dict[str, int] | None:
    points = []
    for index in range(0, len(frame.cells), 4):
        if frame.cells[index] == 32:
            continue
        rgb = tuple(frame.cells[index + 1 : index + 4])
        if rgb == (255, 255, 255):
            continue
        cell = index // 4
        points.append((cell % frame.cols, cell // frame.cols))
    if not points:
        return None
    xs, ys = zip(*points)
    return {
        "min_x": min(xs),
        "min_y": min(ys),
        "max_x": max(xs),
        "max_y": max(ys),
    }


def save(source: ProceduralWizardFrameSource, output: Path, name: str) -> dict:
    frame = source.render_current_frame()
    path = output / f"{name}.png"
    frame_to_png(frame, path)
    return {
        "name": name,
        "file": path.name,
        "cols": frame.cols,
        "rows": frame.rows,
        "frame_sha256": hashlib.sha256(frame.cells).hexdigest(),
        "visible_bounds": visible_bounds(frame),
        "state": {
            "pose_id": source.current_state().pose_id,
            "facing": source.current_state().facing,
            "expression": source.current_state().expression,
            "mouth": source.current_state().mouth,
            "gaze_aim": source.current_state().gaze_aim,
            "gaze_vertical_aim": source.current_state().gaze_vertical_aim,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic Character Director visual evidence."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "evidence" / "character-director" / "visual-review",
    )
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    records = []

    desktop = ProceduralWizardFrameSource(240, 135, 24)
    records.append(save(desktop, output, "desktop-front-idle"))

    portrait = ProceduralWizardFrameSource(135, 240, 24)
    records.append(save(portrait, output, "portrait-front-idle"))

    gaze = ProceduralWizardFrameSource(240, 135, 24)
    apply(gaze, "gaze", {"target": "left"})
    records.append(save(gaze, output, "gaze-left"))
    apply(gaze, "gaze", {"target": "right"})
    records.append(save(gaze, output, "gaze-right"))
    apply(
        gaze,
        "speak",
        {"speech_id": "evidence-speech", "text": "Evidence line.", "duration_ms": 2_000},
    )
    records.append(save(gaze, output, "speaking"))
    apply(gaze, "speech_stop", {})
    records.append(save(gaze, output, "interruption-recovery"))

    granted = permission_source("granted", "granted")
    apply(granted, "action", {"action": "magic_cast", "duration_ms": 2_000})
    records.append(save(granted, output, "permission-granted"))

    denied = permission_source("denied", "denied")
    apply(denied, "action", {"action": "magic_cast", "duration_ms": 2_000})
    records.append(save(denied, output, "permission-denied"))

    manifest = {
        "schema_version": 1,
        "renderer": "asciline_square_cell_pixel_graph",
        "generation": "deterministic",
        "records": records,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)


if __name__ == "__main__":
    main()
