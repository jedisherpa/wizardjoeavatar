#!/usr/bin/env python3
"""Build an honest choreography dictionary from one review library index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _pose_ids(index: Mapping[str, Any]) -> list[str]:
    sequences = index.get("sequences")
    if not isinstance(sequences, Mapping):
        raise ValueError("library index must contain sequences")
    pose_ids: list[str] = []
    for sequence in sequences.values():
        if not isinstance(sequence, Mapping):
            raise ValueError("library sequence must be an object")
        values = sequence.get("pose_ids")
        if not isinstance(values, list):
            raise ValueError("library sequence must contain pose_ids")
        for pose_id in values:
            if not isinstance(pose_id, str) or not pose_id:
                raise ValueError("pose_id must be non-empty text")
            if pose_id not in pose_ids:
                pose_ids.append(pose_id)
    if not pose_ids:
        raise ValueError("library index has no poses")
    return pose_ids


def build_game_motion_dictionary(index_path: Path) -> Path:
    index_path = Path(index_path)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(index, Mapping):
        raise ValueError("library index must be an object")
    if index.get("runtime_admitted") is not False:
        raise ValueError("game-motion dictionary builder accepts review libraries only")
    character_id = index.get("character_id")
    if not isinstance(character_id, str) or not character_id:
        raise ValueError("library index must identify a character")
    authored_pose_ids = _pose_ids(index)
    default_pose_id = authored_pose_ids[0]
    pose_ids = sorted(authored_pose_ids)
    dictionary = {
        "schema_version": 1,
        "dictionary_id": "choreography:{}-game-v1".format(character_id),
        "character_id": character_id,
        "library_class": "game_motion",
        "instructions": {
            "selection_unit": "command",
            "transition_policy": "neutral_bridge",
            "speech_motion_policy": "unsupported",
            "locomotion_speech_policy": "unsupported",
            "unsupported_intent_policy": "default_pose",
            "repetition_window_ms": 4000,
            "minimum_stillness_ms": 500,
            "maximum_gestures_per_phrase": 0,
        },
        "intent_bindings": {
            "neutral": {
                "roles": ["neutral", "recovery"],
                "pose_ids": [default_pose_id],
                "action_ids": [],
                "clip_ids": [],
                "speech_compatible": False,
                "interrupt_policy": "immediate",
                "minimum_hold_ms": 500,
                "recovery_intent": None,
            },
            "game_cycle": {
                "roles": ["game_action"],
                "pose_ids": pose_ids,
                "action_ids": [],
                "clip_ids": [],
                "speech_compatible": False,
                "interrupt_policy": "commit_then_recover",
                "minimum_hold_ms": 750,
                "recovery_intent": "neutral",
            },
        },
    }
    output = index_path.with_name(
        "{}-choreography-dictionary-v1.json".format(character_id)
    )
    output.write_bytes(_json_bytes(dictionary))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build one review-only game-motion choreography dictionary."
    )
    parser.add_argument("library_index", type=Path)
    args = parser.parse_args()
    print(build_game_motion_dictionary(args.library_index))


if __name__ == "__main__":
    main()
