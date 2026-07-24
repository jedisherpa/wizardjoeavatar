#!/usr/bin/env python3
"""Publish the deterministic V9 score and emit its three-profile proof program."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_character_director_visual_review import load_scenario_program
from wizard_avatar.character_capabilities import derive_character_capability_manifest
from wizard_avatar.media_session import MediaSessionSnapshotV1
from wizard_avatar.performance_score import (
    CompiledPerformanceScore,
    CompiledScoreLoader,
    CompiledScoreRepository,
)


PROGRAM_SCHEMA = "character_director_scenario_program_v2"
PROGRAM_ID = "v9-accessibility-profiles"
MEDIA_BYTES = b"wizardjoe-character-director-v9-accessibility-fixture-v1"
MEDIA_HEX = hashlib.sha256(MEDIA_BYTES).hexdigest()
MEDIA_SHA256 = "sha256:" + MEDIA_HEX
MEDIA_ID = "media:sha256:" + MEDIA_HEX
CONNECTOR_SESSION_ID = "00000000-0000-4000-8000-000000000909"
CAPTURE_FRAMES = 216
FPS = 24
PROFILE_ORDER = ("full", "reduced", "still")
MARKER_MAP = {
    "anticipation": None,
    "stroke": None,
    "hold": None,
    "release": None,
    "settle": None,
}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def _sha_ref(value: object) -> str:
    data = value if isinstance(value, bytes) else _canonical_bytes(value)
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _cue(
    cue_id: str,
    start_ms: int,
    end_ms: int,
    intent: str,
    owned_channels: Sequence[str],
    *,
    priority: int,
    amplitude_milli: int,
    mapping_id: str,
    clip_id: Optional[str] = None,
    node_id: Optional[str] = None,
    phase_ranges: Optional[Mapping[str, Sequence[int]]] = None,
    execution: Optional[Mapping[str, object]] = None,
) -> Dict[str, object]:
    identity = {
        "cue_id": cue_id,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "intent": intent,
        "owned_channels": list(owned_channels),
        "mapping_id": mapping_id,
        "clip_id": clip_id,
        "node_id": node_id,
        "execution": execution,
    }
    result: Dict[str, object] = {
        "cue_id": cue_id,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "intent": intent,
        "source_ids": ["v9.acceptance"],
        "priority": priority,
        "amplitude_milli": amplitude_milli,
        "capability_requirements": [intent],
        "fallback_intents": ["body.characterful_neutral"],
        "interrupt_policy": "at_phase_boundary",
        "cooldown_class": "v9.acceptance",
        "motif_id": "v9.accessibility",
        "confidence": {
            "alignment_milli": 1000,
            "evidence_milli": 1000,
            "planner_milli": 1000,
        },
        "manual": {"locked": False, "disabled": False},
        "mapping_id": mapping_id,
        "clip_id": clip_id,
        "node_id": node_id,
        "phase_marker_map": dict(MARKER_MAP),
        "owned_channels": list(owned_channels),
        "resolved_fallback_path": [intent, "body.characterful_neutral"],
        "preload_asset_ids": [clip_id] if clip_id is not None else [],
        "resolution_hash": _sha_ref(identity),
    }
    if phase_ranges is not None:
        result["phase_ranges"] = {
            name: list(bounds) for name, bounds in phase_ranges.items()
        }
    if execution is not None:
        result["execution"] = dict(execution)
    return result


def _body_cues() -> List[Dict[str, object]]:
    return [
        _cue(
            "v9.body.cast",
            500,
            2200,
            "body.cast",
            ("body", "gesture", "effects"),
            priority=700,
            amplitude_milli=800,
            mapping_id="body.cast",
            clip_id="cast_front",
            node_id="cast",
            phase_ranges={
                "anticipation": (500, 800),
                "stroke": (800, 1200),
                "hold": (1200, 1600),
                "release": (1600, 1900),
                "settle": (1900, 2200),
            },
            execution={"facing": "south"},
        ),
        _cue(
            "v9.body.explain",
            2600,
            3800,
            "body.explain",
            ("body", "gesture"),
            priority=650,
            amplitude_milli=600,
            mapping_id="body.explain",
            clip_id="explain_front",
            node_id="explain",
            phase_ranges={
                "anticipation": (2600, 2800),
                "stroke": (2800, 3100),
                "hold": (3100, 3400),
                "release": (3400, 3600),
                "settle": (3600, 3800),
            },
            execution={"facing": "south"},
        ),
        _cue(
            "v9.body.point",
            4200,
            5200,
            "body.point",
            ("body", "gesture"),
            priority=650,
            amplitude_milli=600,
            mapping_id="body.point",
            clip_id="point_front",
            node_id="point",
            phase_ranges={
                "anticipation": (4200, 4400),
                "stroke": (4400, 4650),
                "hold": (4650, 4900),
                "release": (4900, 5050),
                "settle": (5050, 5200),
            },
            execution={"facing": "south"},
        ),
    ]


def _speech_cues() -> List[Dict[str, object]]:
    shapes = ("closed", "open", "wide", "open")
    cues: List[Dict[str, object]] = []
    for index, start_ms in enumerate(range(200, 5600, 300)):
        end_ms = start_ms + 300
        cues.append(
            _cue(
                "v9.speech.{:02d}".format(index + 1),
                start_ms,
                end_ms,
                "speech.approved_line",
                ("speech", "mouth"),
                priority=900,
                amplitude_milli=700,
                mapping_id="speech.mouth." + shapes[index % len(shapes)],
                execution={
                    "mouth_shape": shapes[index % len(shapes)],
                    "speaking": True,
                    "phrase_phase_origin_ms": 200,
                },
            )
        )
    return cues


def build_score_document() -> Dict[str, object]:
    manifest = derive_character_capability_manifest()
    sources = manifest["sources"]
    character = manifest["character"]
    score_identity = {
        "program_id": PROGRAM_ID,
        "media_sha256": MEDIA_SHA256,
        "package_sha256": sources["package_sha256"],
        "pose_library_sha256": sources["pose_library_sha256"],
        "animation_graph_sha256": sources["animation_graph_sha256"],
    }
    return {
        "schema_version": 1,
        "compiled_score_id": "compiled:v9-accessibility-profiles",
        "performance_score_sha256": _sha_ref(score_identity),
        "character": {
            "character_id": character["character_id"],
            "package_version": "1.0.0",
            "package_digest": sources["package_sha256"],
            "pose_library_digest": sources["pose_library_sha256"],
            "graph_digest": sources["animation_graph_sha256"],
        },
        "mapping_policy_sha256": sources["semantic_mapping_sha256"],
        "runtime_api_version": 2,
        "media": {
            "media_id": MEDIA_ID,
            "media_sha256": MEDIA_SHA256,
            "duration_ms": 9000,
        },
        "tracks": [
            {
                "track_id": "v9-body",
                "kind": "body_base",
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "characterful_neutral",
                "cues": _body_cues(),
            },
            {
                "track_id": "v9-stage",
                "kind": "locomotion",
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "clear",
                "cues": [
                    _cue(
                        "v9.stage.walk",
                        5600,
                        8000,
                        "stage.travel",
                        ("locomotion", "stage"),
                        priority=750,
                        amplitude_milli=700,
                        mapping_id="stage.walk",
                        clip_id="walk_front",
                        node_id="ground_walk",
                        execution={
                            "trajectory": {
                                "source_position_milli": [350, 600],
                                "destination_position_milli": [650, 600],
                                "easing_id": "smoothstep_v1",
                            },
                            "facing": "south",
                        },
                    )
                ],
            },
            {
                "track_id": "v9-face",
                "kind": "face",
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "neutral",
                "cues": [
                    _cue(
                        "v9.face.engaged",
                        0,
                        8000,
                        "face.engaged",
                        ("face",),
                        priority=500,
                        amplitude_milli=450,
                        mapping_id="face.explaining",
                        execution={"expression": "explaining"},
                    )
                ],
            },
            {
                "track_id": "v9-gaze",
                "kind": "gaze",
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "neutral",
                "cues": [
                    _cue(
                        "v9.gaze.viewer",
                        0,
                        4000,
                        "gaze.viewer",
                        ("gaze", "eyes"),
                        priority=550,
                        amplitude_milli=400,
                        mapping_id="gaze.viewer",
                        execution={"gaze_target": "viewer"},
                    ),
                    _cue(
                        "v9.gaze.right",
                        4000,
                        8000,
                        "gaze.right",
                        ("gaze", "eyes"),
                        priority=550,
                        amplitude_milli=400,
                        mapping_id="gaze.right",
                        execution={"gaze_target": "right"},
                    ),
                ],
            },
            {
                "track_id": "v9-speech",
                "kind": "speech",
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "clear",
                "cues": _speech_cues(),
            },
        ],
        "checkpoints": [],
        "fallback_records": [],
        "validation": {
            "decision": "accepted",
            "report_sha256": _sha_ref({"gate": "V9", "decision": "accepted"}),
        },
    }


def load_score() -> CompiledPerformanceScore:
    return CompiledScoreLoader().from_mapping(build_score_document())


def _message_id(sequence: int) -> str:
    return "00000000-0000-4000-8000-{:012x}".format(sequence)


def _snapshot(
    score: CompiledPerformanceScore,
    *,
    profile: str,
    sequence: int,
    media_epoch: int,
    position_ms: int,
    cause: str,
) -> Dict[str, object]:
    value = {
        "schema_version": 1,
        "message_id": _message_id(sequence),
        "connector_session_id": CONNECTOR_SESSION_ID,
        "sequence": sequence,
        "media_epoch": media_epoch,
        "cause": cause,
        "sampled_at_monotonic_ms": sequence * 1000,
        "media": {
            "media_id": score.media_id,
            "media_sha256": score.media_sha256,
            "kind": "audiobook",
            "source_slot": "main",
            "source_kind": "studio_chapter",
            "book_id": "book:v9",
            "chapter_id": "chapter:v9",
            "duration_ms": score.duration_ms,
        },
        "playback": {
            "state": "playing",
            "position_ms": position_ms,
            "rate_milli": 1000,
            "ready_state": 4,
            "seeking": False,
        },
        "performance": {
            "mode": "narrative",
            "score_id": score.compiled_score_id,
            "score_revision": score.revision,
            "score_sha256": score.artifact_sha256,
            "character_id": score.character_id,
            "character_package_sha256": score.package_digest,
            "intensity_milli": 700,
            "motion_profile": profile,
            "disabled_channels": [],
        },
    }
    return dict(MediaSessionSnapshotV1.from_mapping(value).to_dict())


def build_scenario_program(score: CompiledPerformanceScore) -> Dict[str, object]:
    scenarios = []
    sequence = 1
    for profile_index, profile in enumerate(PROFILE_ORDER):
        epoch = profile_index
        parent = _snapshot(
            score,
            profile=profile,
            sequence=sequence,
            media_epoch=epoch,
            position_ms=0,
            cause="initial" if profile_index == 0 else "seeked",
        )
        sequence += 1
        scheduled = []
        for second in range(1, 9):
            scheduled.append(
                {
                    "name": "v9-{}-heartbeat-{:02d}".format(profile, second),
                    "at_frame": second * FPS,
                    "kind": "media_session",
                    "payload": _snapshot(
                        score,
                        profile=profile,
                        sequence=sequence,
                        media_epoch=epoch,
                        position_ms=second * 1000,
                        cause="heartbeat",
                    ),
                }
            )
            sequence += 1
        scenarios.append(
            {
                "name": "v9-{}-profile".format(profile),
                "kind": "media_session",
                "payload": parent,
                "timing": {
                    "capture_frames": CAPTURE_FRAMES,
                    "scheduled_commands": scheduled,
                },
            }
        )
    return {
        "schema": PROGRAM_SCHEMA,
        "schema_version": 2,
        "program_id": PROGRAM_ID,
        "acceptance_scenario": "V9",
        "scenarios": scenarios,
    }


def prepare_fixture(score_root: Path, scenario_out: Path) -> Dict[str, object]:
    score = load_score()
    repository = CompiledScoreRepository(score_root)
    publication = repository.publish(score)
    reloaded = repository.load_current(MEDIA_SHA256)
    if reloaded.artifact_sha256 != score.artifact_sha256:
        raise RuntimeError("published V9 score failed immutable reload")

    program = build_scenario_program(score)
    scenario_out.parent.mkdir(parents=True, exist_ok=True)
    scenario_out.write_bytes(_canonical_bytes(program) + b"\n")
    loaded_program = load_scenario_program(scenario_out)
    if loaded_program.acceptance_scenario != "V9":
        raise RuntimeError("generated scenario program failed V9 replay validation")

    return {
        "schema": "character_director_v9_fixture_v1",
        "score_root": str(score_root.resolve()),
        "scenario_path": str(scenario_out.resolve()),
        "scenario_sha256": _sha_ref(scenario_out.read_bytes()),
        "score_id": score.compiled_score_id,
        "score_sha256": score.artifact_sha256,
        "media_id": score.media_id,
        "media_sha256": score.media_sha256,
        "package_sha256": score.package_digest,
        "publication": publication.to_dict(),
        "profiles": list(PROFILE_ORDER),
        "capture_frames_per_profile": CAPTURE_FRAMES,
        "total_capture_frames": CAPTURE_FRAMES * len(PROFILE_ORDER),
        "snapshot_count": sum(
            1 + len(item["timing"]["scheduled_commands"])
            for item in program["scenarios"]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare the deterministic Character Director V9 proof fixture."
    )
    parser.add_argument("--score-root", type=Path, required=True)
    parser.add_argument("--scenario-out", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            prepare_fixture(args.score_root, args.scenario_out),
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
