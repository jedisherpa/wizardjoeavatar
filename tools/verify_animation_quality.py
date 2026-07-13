#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCellFrame, WizardCommand


DEFAULT_OUTPUT = ROOT / "evidence" / "animation-quality" / "final"
PRE_FRAMES = 12
POST_FRAMES = 18


@dataclass(frozen=True)
class Step:
    command_type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TransitionScenario:
    scenario_id: str
    description: str
    setup: tuple[Step, ...] = ()
    boundary: tuple[Step, ...] = ()
    setup_frames: int = 0
    pre_frames: int = PRE_FRAMES
    post_frames: int = POST_FRAMES
    fixed_world: bool = True
    expected_final: dict[str, Any] = field(default_factory=dict)
    allow_root_motion: bool = False


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def command(source: ProceduralWizardFrameSource, step: Step) -> None:
    result = source.apply_command_sync(WizardCommand(step.command_type, dict(step.payload)))
    if not result.ok:
        raise RuntimeError(f"{step.command_type} failed: {result.message}")


def frame_hash(frame: WizardCellFrame) -> str:
    return hashlib.sha256(frame.cells).hexdigest()


def changed_cell_count(previous: bytes | None, current: bytes) -> int:
    if previous is None or len(previous) != len(current):
        return len(current) // 4
    return sum(
        1
        for offset in range(0, len(current), 4)
        if previous[offset : offset + 4] != current[offset : offset + 4]
    )


def sample_frame(
    source: ProceduralWizardFrameSource,
    phase: str,
    ordinal: int,
    previous_cells: bytes | None,
) -> tuple[dict[str, Any], bytes]:
    frame = source.render_next_frame()
    state = source.current_state().as_public_dict()
    sample = {
        "phase": phase,
        "ordinal": ordinal,
        "frame_index": frame.frame_index,
        "hash": frame_hash(frame),
        "changed_cells": changed_cell_count(previous_cells, frame.cells),
        "state": {
            "time_seconds": round(state["time_seconds"], 6),
            "world_position": state["world_position"],
            "screen_position": state["screen_position"],
            "display_scale": state["display_scale"],
            "facing": state["facing"],
            "locomotion": state["locomotion"],
            "action": state["action"],
            "upper_body_action": state["upper_body_action"],
            "staff_state": state["staff_state"],
            "expression": state["expression"],
            "mouth": state["mouth"],
            "speech_id": state["speech_id"],
            "walk_phase": state["walk_phase"],
            "pose_id": state.get("pose_id"),
            "pose_transition_progress": state.get("pose_transition_progress"),
        },
    }
    return sample, frame.cells


def run_frames(source: ProceduralWizardFrameSource, frames: int) -> None:
    for _ in range(frames):
        source.render_next_frame()


def distance(a: dict[str, float], b: dict[str, float]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def analyze_samples(scenario: TransitionScenario, samples: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[str] = []
    adjacent_root_deltas: list[float] = []
    adjacent_scale_deltas: list[float] = []
    adjacent_churn_ratios: list[float] = []
    total_cells = 240 * 135
    for left, right in zip(samples, samples[1:]):
        left_state = left["state"]
        right_state = right["state"]
        adjacent_root_deltas.append(
            distance(left_state["screen_position"], right_state["screen_position"])
        )
        adjacent_scale_deltas.append(
            abs(float(left_state["display_scale"]) - float(right_state["display_scale"]))
        )
        adjacent_churn_ratios.append(right["changed_cells"] / total_cells)

    pre = [sample for sample in samples if sample["phase"] == "pre"]
    post = [sample for sample in samples if sample["phase"] == "post"]
    boundary_root_delta = None
    boundary_scale_delta = None
    if pre and post:
        boundary_root_delta = distance(
            pre[-1]["state"]["screen_position"],
            post[0]["state"]["screen_position"],
        )
        boundary_scale_delta = abs(
            float(pre[-1]["state"]["display_scale"])
            - float(post[0]["state"]["display_scale"])
        )
        if scenario.fixed_world and not scenario.allow_root_motion:
            if boundary_root_delta > 1.0:
                issues.append(f"fixed-world root jump {boundary_root_delta:.3f} cells")
            if boundary_scale_delta > 1e-9:
                issues.append(f"fixed-world scale changed {boundary_scale_delta:.6f}")

    final_state = samples[-1]["state"] if samples else {}
    for key, expected in scenario.expected_final.items():
        actual = final_state.get(key)
        if actual != expected:
            issues.append(f"expected final {key}={expected!r}, got {actual!r}")

    return {
        "max_adjacent_root_delta": max(adjacent_root_deltas, default=0.0),
        "max_adjacent_scale_delta": max(adjacent_scale_deltas, default=0.0),
        "max_adjacent_churn_ratio": max(adjacent_churn_ratios, default=0.0),
        "average_adjacent_churn_ratio": (
            sum(adjacent_churn_ratios) / len(adjacent_churn_ratios)
            if adjacent_churn_ratios
            else 0.0
        ),
        "boundary_root_delta": boundary_root_delta,
        "boundary_scale_delta": boundary_scale_delta,
        "unique_poses": sorted({sample["state"].get("pose_id") for sample in samples}),
        "unique_facings": sorted({sample["state"]["facing"] for sample in samples}),
        "unique_actions": sorted({sample["state"]["action"] for sample in samples}),
        "issues": issues,
        "passed": not issues,
    }


def run_scenario(scenario: TransitionScenario) -> dict[str, Any]:
    source = ProceduralWizardFrameSource()
    previous_cells: bytes | None = None
    for step in scenario.setup:
        command(source, step)
    run_frames(source, scenario.setup_frames)

    samples: list[dict[str, Any]] = []
    for idx in range(scenario.pre_frames):
        sample, previous_cells = sample_frame(source, "pre", idx, previous_cells)
        samples.append(sample)
    for step in scenario.boundary:
        command(source, step)
    for idx in range(scenario.post_frames):
        sample, previous_cells = sample_frame(source, "post", idx, previous_cells)
        samples.append(sample)

    metrics = analyze_samples(scenario, samples)
    return {
        "scenario_id": scenario.scenario_id,
        "description": scenario.description,
        "fixed_world": scenario.fixed_world,
        "setup": [step.__dict__ for step in scenario.setup],
        "boundary": [step.__dict__ for step in scenario.boundary],
        "metrics": metrics,
        "samples": samples,
    }


def scenarios() -> list[TransitionScenario]:
    return [
        TransitionScenario(
            "idle_to_walk",
            "idle -> walk",
            boundary=(Step("move", {"x": 4.0, "z": 5.0}),),
            fixed_world=False,
            expected_final={"locomotion": "walking"},
        ),
        TransitionScenario(
            "walk_to_idle",
            "walk -> idle",
            setup=(Step("move", {"x": 4.0, "z": 5.0}),),
            setup_frames=18,
            boundary=(Step("stop", {}),),
            fixed_world=False,
            expected_final={"locomotion": "idle"},
        ),
        TransitionScenario(
            "walk_to_turn",
            "walk -> turn",
            setup=(Step("move", {"x": 4.0, "z": 5.0}),),
            setup_frames=18,
            boundary=(Step("face", {"direction": "north"}),),
            fixed_world=False,
        ),
        TransitionScenario(
            "turn_to_walk",
            "turn -> walk",
            setup=(Step("face", {"direction": "east"}),),
            boundary=(Step("move", {"x": -1.4, "z": 5.0}),),
            fixed_world=False,
            expected_final={"locomotion": "walking"},
        ),
        TransitionScenario(
            "front_to_diagonal",
            "front -> diagonal",
            setup=(Step("face", {"direction": "south"}),),
            boundary=(Step("face", {"direction": "southwest"}),),
        ),
        TransitionScenario(
            "diagonal_to_side",
            "diagonal -> side",
            setup=(Step("face", {"direction": "southwest"}),),
            boundary=(Step("face", {"direction": "west"}),),
        ),
        TransitionScenario(
            "side_to_back",
            "side -> back",
            setup=(Step("face", {"direction": "west"}),),
            boundary=(Step("face", {"direction": "north"}),),
        ),
        TransitionScenario(
            "forward_to_backward",
            "forward movement -> backward movement",
            setup=(Step("move", {"x": 0.0, "z": 3.0}),),
            setup_frames=20,
            boundary=(Step("move", {"x": 0.0, "z": 7.0}),),
            fixed_world=False,
            expected_final={"locomotion": "walking"},
        ),
        TransitionScenario(
            "clockwise_circle_reversal",
            "clockwise circle direction change",
            setup=(Step("circle", {"center_x": 0, "center_z": 5, "radius": 1.6, "clockwise": True, "duration_seconds": 8}),),
            setup_frames=24,
            boundary=(Step("circle", {"center_x": 0, "center_z": 5, "radius": 1.6, "clockwise": False, "duration_seconds": 8}),),
            fixed_world=False,
        ),
        TransitionScenario(
            "counterclockwise_circle_reversal",
            "counterclockwise circle direction change",
            setup=(Step("circle", {"center_x": 0, "center_z": 5, "radius": 1.6, "clockwise": False, "duration_seconds": 8}),),
            setup_frames=24,
            boundary=(Step("circle", {"center_x": 0, "center_z": 5, "radius": 1.6, "clockwise": True, "duration_seconds": 8}),),
            fixed_world=False,
        ),
        TransitionScenario(
            "figure_eight_start",
            "figure-eight crossover path start",
            boundary=(Step("figure_eight", {"center_x": 0, "center_z": 5, "radius": 1.2}),),
            fixed_world=False,
            post_frames=36,
        ),
        TransitionScenario(
            "walk_to_speak",
            "walk -> speak",
            setup=(Step("move", {"x": 4.0, "z": 5.0}),),
            setup_frames=18,
            boundary=(Step("speak", {"text": "Still walking.", "duration_ms": 500}),),
            fixed_world=False,
            expected_final={"locomotion": "walking"},
        ),
        TransitionScenario(
            "speak_to_walk",
            "speak -> walk",
            setup=(Step("speak", {"text": "And now we walk.", "duration_ms": 900}),),
            setup_frames=8,
            boundary=(Step("move", {"x": 4.0, "z": 5.0}),),
            fixed_world=False,
            expected_final={"locomotion": "walking"},
        ),
        TransitionScenario(
            "idle_to_explain",
            "idle -> explain",
            boundary=(Step("action", {"action": "explaining", "duration_ms": 4000}),),
        ),
        TransitionScenario(
            "idle_to_dash",
            "idle -> airborne dash",
            boundary=(Step("action", {"action": "dash", "duration_ms": 4000}),),
            expected_final={"action": "dash", "pose_id": "run_front_airborne_reach"},
        ),
        TransitionScenario(
            "dash_to_idle",
            "airborne dash -> idle",
            setup=(Step("action", {"action": "dash", "duration_ms": 4000}),),
            setup_frames=8,
            boundary=(Step("action", {"action": "idle", "duration_ms": 0}),),
            expected_final={"action": "idle", "pose_id": "front_idle"},
        ),
        TransitionScenario(
            "explain_to_walk",
            "explain -> walk",
            setup=(Step("action", {"action": "explaining", "duration_ms": 4000}),),
            setup_frames=8,
            boundary=(Step("move", {"x": 4.0, "z": 5.0}),),
            fixed_world=False,
            expected_final={"locomotion": "walking"},
        ),
        TransitionScenario(
            "walk_to_point",
            "walk -> point",
            setup=(Step("move", {"x": 4.0, "z": 5.0}),),
            setup_frames=18,
            boundary=(Step("action", {"action": "pointing", "duration_ms": 4000}),),
            fixed_world=False,
            expected_final={"locomotion": "walking"},
        ),
        TransitionScenario(
            "point_to_idle",
            "point -> idle",
            setup=(Step("action", {"action": "pointing", "duration_ms": 4000}),),
            setup_frames=8,
            boundary=(Step("action", {"action": "idle", "duration_ms": 0}),),
            expected_final={"action": "idle"},
        ),
        TransitionScenario(
            "idle_to_think",
            "idle -> think",
            boundary=(Step("action", {"action": "thinking", "duration_ms": 4000}),),
        ),
        TransitionScenario(
            "think_to_speak",
            "think -> speak",
            setup=(Step("action", {"action": "thinking", "duration_ms": 4000}),),
            setup_frames=8,
            boundary=(Step("speak", {"text": "The thought became a sentence.", "duration_ms": 500}),),
            expected_final={"action": "thinking"},
        ),
        TransitionScenario(
            "idle_to_cast",
            "idle -> cast",
            boundary=(Step("action", {"action": "magic_cast", "duration_ms": 5000}),),
        ),
        TransitionScenario(
            "cast_to_idle",
            "cast -> idle",
            setup=(Step("action", {"action": "magic_cast", "duration_ms": 5000}),),
            setup_frames=8,
            boundary=(Step("action", {"action": "idle", "duration_ms": 0}),),
            expected_final={"action": "idle", "staff_state": "held"},
        ),
        TransitionScenario(
            "reaction_to_previous",
            "reaction -> previous stable state",
            setup=(Step("action", {"action": "magic_cast", "duration_ms": 5000}),),
            setup_frames=8,
            boundary=(Step("action", {"action": "reaction", "duration_ms": 400}),),
            post_frames=36,
            expected_final={"action": "magic_cast", "staff_state": "cast"},
        ),
        TransitionScenario(
            "expression_during_locomotion",
            "expression changes during locomotion",
            setup=(Step("move", {"x": 4.0, "z": 5.0}),),
            setup_frames=18,
            boundary=(Step("expression", {"expression": "surprised"}),),
            fixed_world=False,
            expected_final={"expression": "surprised", "locomotion": "walking"},
        ),
        TransitionScenario(
            "blink_during_speech",
            "blink during speech",
            setup=(Step("speak", {"text": "Blink while speaking.", "duration_ms": 900}),),
            setup_frames=8,
            boundary=(Step("expression", {"expression": "focused"}),),
            expected_final={"expression": "focused"},
        ),
        TransitionScenario(
            "mouth_closure_after_speech",
            "mouth closure after speech",
            setup=(Step("speak", {"text": "Close clearly.", "duration_ms": 250}),),
            setup_frames=4,
            boundary=(),
            post_frames=18,
            expected_final={"speech_id": None},
        ),
        TransitionScenario(
            "staff_during_turning",
            "staff position during turning",
            setup=(Step("action", {"action": "magic_cast", "duration_ms": 5000}),),
            setup_frames=8,
            boundary=(Step("face", {"direction": "east"}),),
            expected_final={"staff_state": "cast"},
        ),
        TransitionScenario(
            "staff_during_gesture",
            "staff position during arm gestures",
            setup=(Step("action", {"action": "explaining", "duration_ms": 4000}),),
            setup_frames=8,
            boundary=(Step("action", {"action": "pointing", "duration_ms": 4000}),),
        ),
        TransitionScenario(
            "depth_scaling_forward",
            "depth scaling while walking forward",
            boundary=(Step("move", {"x": 0.0, "z": 3.0}),),
            fixed_world=False,
            allow_root_motion=True,
            post_frames=30,
        ),
        TransitionScenario(
            "root_position_view_change",
            "root position during view changes",
            setup=(Step("face", {"direction": "south"}),),
            boundary=(Step("face", {"direction": "north"}),),
        ),
        TransitionScenario(
            "animation_interruption_cancel",
            "animation interruption and cancellation",
            setup=(Step("action", {"action": "magic_cast", "duration_ms": 5000}),),
            setup_frames=8,
            boundary=(Step("stop", {}),),
            expected_final={"locomotion": "idle"},
        ),
    ]


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Python 8765 Transition Matrix Verification",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- branch: `{report['branch']}`",
        f"- commit: `{report['commit']}`",
        f"- scenarios: `{report['summary']['scenario_count']}`",
        f"- passed: `{report['summary']['passed_count']}`",
        f"- with issues: `{report['summary']['issue_count']}`",
        "",
        "## Scenario Summary",
        "",
        "| Scenario | Passed | Boundary Root | Boundary Scale | Max Churn | Issues |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for result in report["results"]:
        metrics = result["metrics"]
        issues = "; ".join(metrics["issues"]) if metrics["issues"] else ""
        boundary_root = metrics["boundary_root_delta"]
        boundary_scale = metrics["boundary_scale_delta"]
        lines.append(
            "| {scenario} | {passed} | {root} | {scale} | {churn:.3f} | {issues} |".format(
                scenario=result["scenario_id"],
                passed="yes" if metrics["passed"] else "no",
                root="" if boundary_root is None else f"{boundary_root:.3f}",
                scale="" if boundary_scale is None else f"{boundary_scale:.6f}",
                churn=metrics["max_adjacent_churn_ratio"],
                issues=issues.replace("|", "\\|"),
            )
        )
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Python WizardJoe transition quality and write evidence.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any scenario has issues.")
    args = parser.parse_args()

    results = [run_scenario(scenario) for scenario in scenarios()]
    issue_count = sum(0 if result["metrics"]["passed"] else 1 for result in results)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "branch": subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True).strip(),
        "commit": git_sha(),
        "summary": {
            "scenario_count": len(results),
            "passed_count": len(results) - issue_count,
            "issue_count": issue_count,
        },
        "results": results,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "transition-matrix-8765.json"
    markdown_path = args.output_dir / "TRANSITION_MATRIX_8765.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, markdown_path)
    print(json.dumps({"json": str(json_path), "markdown": str(markdown_path), **report["summary"]}, indent=2))
    if args.strict and issue_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
