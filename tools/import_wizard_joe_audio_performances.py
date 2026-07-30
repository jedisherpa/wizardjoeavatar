#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.performance_authoring.media import canonicalize_pcm, probe_media


DEFAULT_PACKAGE = Path(
    "/Users/paul/Downloads/Wizard_Joe_Corrected_Voice_Audio_Package"
)
DEFAULT_OUTPUT = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "wizard-joe"
    / "audio-performances-v1"
)
DEFAULT_HD_INDEX = (
    ROOT / "assets" / "reference" / "hd_canonical" / "compiled" / "library-index.json"
)
JOEVILLE_COMMIT = "a65e0a434dc202f8e69b78cb2bb22a843ce758d4"
APPROACH_POSES = (
    "246_camera_approach",
)
FLIGHT_APPROACH_POSES = (
    "177_flight_glide_forward",
    "174_flight_powerstroke_down",
    "175_flight_recoverystroke_up",
    "184_flight_accelerate",
)
HOVER_POSE = "176_flight_hover_neutral"
AIR_SPEECH_POSES = (
    "174_flight_powerstroke_down",
    "175_flight_recoverystroke_up",
    "176_flight_hover_neutral",
    "178_flight_bank_left",
    "179_flight_bank_right",
    "180_flight_turn_toward_camera",
    "186_flight_stationary_listen",
    "187_flight_stationary_speak",
    "188_flight_staff_forward",
)
SETTLE_POSE = "013_idle_warm_camera_ready"
MIN_MOTION_BEAT_SPACING_MS = 1450
MAX_AUTHORED_MOTION_BEAT_GAP_MS = 4800
MOTION_REPETITION_WINDOW = 4
BODY_TRANSITION_MS = 160


HERO_CHOREOGRAPHY: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "WJ_LEDGER_001": (
        ("define", ("044_speak_define_term", "042_speak_explain_precise")),
        ("sequence", ("043_speak_explain_sequence", "059_speak_count_one")),
        ("build", ("060_speak_count_two", "061_speak_count_three")),
        ("comic_release", ("078_emotion_amused", "243_comedy_recover_dignity")),
    ),
    "WJ_INTRO_001": (
        ("distant_greeting", ("177_flight_glide_forward", "174_flight_powerstroke_down")),
        ("approach", ("175_flight_recoverystroke_up", "184_flight_accelerate")),
        ("brake", ("185_flight_brake", "187_flight_stationary_speak")),
        ("hover_arrival", ("176_flight_hover_neutral", "187_flight_stationary_speak")),
    ),
    "WJ_INTRO_002": (
        ("hover_notice", ("176_flight_hover_neutral", "187_flight_stationary_speak")),
        ("hover_explain", ("187_flight_stationary_speak", "174_flight_powerstroke_down", "188_flight_staff_forward")),
        ("hover_congratulate", ("175_flight_recoverystroke_up", "187_flight_stationary_speak")),
        ("hover_reassure", ("188_flight_staff_forward", "187_flight_stationary_speak", "176_flight_hover_neutral")),
    ),
    "WJ_INTRO_003": (
        ("introduce", ("041_speak_explain_open", "077_emotion_joy")),
        ("staff", ("123_staff_plant", "057_speak_quote")),
        ("punchline", ("078_emotion_amused", "243_comedy_recover_dignity")),
    ),
    "WJ_INTRO_004": (
        ("administrative_note", ("042_speak_explain_precise", "044_speak_define_term")),
        ("projection", ("043_speak_explain_sequence", "200_magic_trace_symbol")),
        ("tutorial", ("041_speak_explain_open", "051_speak_reassure")),
        ("questions", ("055_speak_question", "056_speak_answer")),
        ("entrance_joke", ("078_emotion_amused", "243_comedy_recover_dignity")),
    ),
    "WJ_INTRO_005": (
        ("reassure", ("051_speak_reassure", "050_speak_confide")),
        ("reset", ("075_speech_yield_floor", "085_emotion_relief")),
        ("pixels", ("067_story_begin", "070_story_reveal", "078_emotion_amused")),
    ),
    "WJ_FIRST_QUESTION_BOUNDARY": (
        ("protect", ("052_speak_warn", "118_hand_stop")),
        ("options", ("043_speak_explain_sequence", "059_speak_count_one", "060_speak_count_two")),
        ("permission", ("051_speak_reassure", "119_hand_invite")),
        ("tree_joke", ("078_emotion_amused", "243_comedy_recover_dignity")),
    ),
    "WJ_FIRST_QUESTION_ENOUGH": (
        ("steps", ("043_speak_explain_sequence", "059_speak_count_one", "060_speak_count_two")),
        ("promise", ("051_speak_reassure", "050_speak_confide")),
        ("freedom", ("108_emotion_hopeful", "120_hand_fist_resolve")),
        ("instructions_joke", ("078_emotion_amused", "243_comedy_recover_dignity")),
    ),
    "WJ_FIRST_QUESTION_JOE": (
        ("challenge", ("055_speak_question", "053_speak_challenge")),
        ("evidence", ("059_speak_count_one", "060_speak_count_two", "061_speak_count_three")),
        ("answer", ("056_speak_answer", "054_speak_persuade")),
        ("hypercube", ("200_magic_trace_symbol", "078_emotion_amused")),
    ),
    "WJ_FIRST_QUESTION_NOT_READY": (
        ("validate", ("051_speak_reassure", "082_emotion_compassion")),
        ("options", ("043_speak_explain_sequence", "119_hand_invite")),
        ("wait", ("036_wait_patient", "050_speak_confide")),
        ("door_joke", ("078_emotion_amused", "243_comedy_recover_dignity")),
    ),
    "WJ_FIRST_QUESTION_REAL": (
        ("answer", ("056_speak_answer", "042_speak_explain_precise")),
        ("categories", ("043_speak_explain_sequence", "059_speak_count_one", "060_speak_count_two")),
        ("uncertainty", ("055_speak_question", "044_speak_define_term")),
        ("interface_joke", ("078_emotion_amused", "243_comedy_recover_dignity")),
    ),
    "WJ_FIRST_QUESTION_WHY": (
        ("systems", ("042_speak_explain_precise", "068_story_build")),
        ("author", ("067_story_begin", "070_story_reveal")),
        ("congratulate", ("077_emotion_joy", "041_speak_explain_open")),
        ("qa_joke", ("078_emotion_amused", "243_comedy_recover_dignity")),
    ),
    "WJ_BOUNDARY_DECLINE": (
        ("clean_no", ("118_hand_stop", "107_emotion_solemn")),
        ("clean_explanation", ("045_speak_clarify", "042_speak_explain_precise")),
    ),
}


def _approach_for_clip(clip_id: str, duration_ms: int) -> dict[str, Any]:
    if clip_id == "WJ_INTRO_001":
        return {
            "mode": "fly_toward_camera",
            "start_ms": 0,
            "end_ms": duration_ms,
            "pose_ids": list(FLIGHT_APPROACH_POSES),
            "fps": 2.4,
            "start_scale_milli": 260,
            "end_scale_milli": 1080,
            "start_offset_y_px": -42,
            "end_offset_y_px": 0,
            "arrival_transition_ms": 1200,
            "arrival_pose_ids": ["185_flight_brake", HOVER_POSE],
            "frame_blend_ms": 110,
            "easing_id": "cubic_in_out",
            "ground_anchor": "center",
            "source_contract": "authored:wizard-joe:intro-001:camera-flight",
        }
    if clip_id == "WJ_INTRO_002":
        return {
            "mode": "hover",
            "start_ms": 0,
            "end_ms": 0,
            "pose_ids": [HOVER_POSE],
            "fps": 2,
            "start_scale_milli": 1080,
            "end_scale_milli": 1080,
            "start_offset_y_px": 0,
            "end_offset_y_px": 0,
            "easing_id": "none",
            "ground_anchor": "center",
            "source_contract": "authored:wizard-joe:intro-002:hover-talk",
        }
    return {
        "mode": "walk_toward_camera",
        "start_ms": 0,
        "end_ms": min(2800, max(900, round(duration_ms * 0.2))),
        "pose_ids": list(APPROACH_POSES),
        "fps": 1,
        "start_scale_milli": 720,
        "end_scale_milli": 1080,
        "start_offset_y_px": 0,
        "end_offset_y_px": 0,
        "arrival_transition_ms": 500,
        "arrival_pose_ids": ["247_camera_intimate_hold"],
        "frame_blend_ms": BODY_TRANSITION_MS,
        "easing_id": "sine_out",
        "ground_anchor": "center_bottom",
        "source_contract": "authored:wizard-joe:stable-camera-approach:v4",
    }


def _settle_pose_for_clip(clip_id: str) -> str:
    if clip_id in {"WJ_INTRO_001", "WJ_INTRO_002"}:
        return HOVER_POSE
    return SETTLE_POSE

INTENT_POSES: dict[str, tuple[str, ...]] = {
    "open": (
        "041_speak_explain_open",
        "047_speak_emphasize_low",
        "049_speak_emphasize_high",
        "111_hand_open_relaxed",
        "119_hand_invite",
        "062_news_presenter_open",
        "015_idle_speaking_ready",
        "074_speech_resume",
        "075_speech_yield_floor",
    ),
    "explain": (
        "041_speak_explain_open",
        "042_speak_explain_precise",
        "043_speak_explain_sequence",
        "044_speak_define_term",
        "045_speak_clarify",
        "046_speak_summarize",
        "047_speak_emphasize_low",
        "048_speak_emphasize_medium",
        "113_hand_present_screen_left",
        "112_hand_present_screen_right",
        "062_news_presenter_open",
        "063_news_presenter_serious",
    ),
    "sequence": (
        "043_speak_explain_sequence",
        "059_speak_count_one",
        "060_speak_count_two",
        "061_speak_count_three",
        "044_speak_define_term",
        "046_speak_summarize",
        "112_hand_present_screen_right",
        "113_hand_present_screen_left",
    ),
    "question": (
        "055_speak_question",
        "080_emotion_curious",
        "027_think_consider",
        "028_think_upward_recall",
        "031_realization_small",
        "032_realization_clear",
        "035_acknowledge_uncertain",
        "116_hand_point_up",
    ),
    "reassure": (
        "051_speak_reassure",
        "050_speak_confide",
        "082_emotion_compassion",
        "085_emotion_relief",
        "106_emotion_serene",
        "022_listen_user_warm",
        "111_hand_open_relaxed",
        "119_hand_invite",
    ),
    "boundary": (
        "052_speak_warn",
        "054_speak_persuade",
        "063_news_presenter_serious",
        "118_hand_stop",
        "045_speak_clarify",
        "119_hand_invite",
        "101_emotion_defiant",
        "107_emotion_solemn",
    ),
    "resolve": (
        "047_speak_emphasize_low",
        "048_speak_emphasize_medium",
        "049_speak_emphasize_high",
        "100_emotion_determined",
        "101_emotion_defiant",
        "120_hand_fist_resolve",
        "081_emotion_confident",
        "083_emotion_proud",
    ),
    "celebrate": (
        "077_emotion_joy",
        "083_emotion_proud",
        "086_emotion_gratitude",
        "087_emotion_surprise",
        "081_emotion_confident",
        "120_hand_fist_resolve",
    ),
    "story": (
        "057_speak_quote",
        "066_news_field_report",
        "067_story_begin",
        "068_story_build",
        "069_story_suspense",
        "070_story_reveal",
        "071_story_character_voice",
        "072_story_moral",
    ),
    "interface": (
        "133_touch_ui_panel",
        "134_drag_ui_panel",
        "064_news_point_graphic_left",
        "114_hand_point_screen_left",
        "115_hand_point_screen_right",
        "117_hand_point_down",
        "042_speak_explain_precise",
    ),
    "magic": (
        "196_magic_sense",
        "197_magic_prepare_small",
        "198_magic_gather_staff",
        "199_magic_gather_hand",
        "200_magic_trace_symbol",
        "207_magic_cast_recover",
    ),
    "comic": (
        "078_emotion_amused",
        "084_emotion_playful",
        "095_emotion_embarrassed",
        "243_comedy_recover_dignity",
        "110_emotion_recover_composure",
    ),
    "recovery": (
        "013_idle_warm_camera_ready",
        "014_idle_attentive",
        "015_idle_speaking_ready",
        "038_shift_listen_to_speak",
        "039_shift_speak_to_listen",
        "085_emotion_relief",
        "110_emotion_recover_composure",
        "073_speech_interrupted",
        "074_speech_resume",
        "051_speak_reassure",
        "040_settle_to_neutral",
    ),
}

FAMILY_ARCS: dict[str, tuple[str, ...]] = {
    "INTRO": ("open", "story", "explain", "open"),
    "WORLD": ("open", "story", "explain", "open"),
    "PURPOSE": ("open", "sequence", "resolve", "open"),
    "ENTER": ("open", "question", "resolve", "open"),
    "QUEST": ("open", "sequence", "resolve", "celebrate"),
    "STAGE": ("open", "explain", "resolve", "celebrate"),
    "PROJECT": ("open", "sequence", "explain", "open"),
    "AI": ("explain", "explain", "boundary", "open"),
    "LEDGER": ("open", "sequence", "celebrate", "open"),
    "MENTOR": ("reassure", "explain", "open", "celebrate"),
    "RETURN": ("reassure", "open", "question"),
    "FIRST": ("question", "explain", "reassure", "open"),
    "COMPASS": ("interface", "explain", "open"),
    "NOTEBOOK": ("interface", "explain", "celebrate", "open"),
    "CLARITY": ("celebrate", "explain", "open"),
    "BOUNDARY": ("boundary", "explain", "reassure", "open"),
    "FOCUS": ("reassure", "recovery", "open"),
    "BOULDER": ("story", "explain", "interface", "open"),
    "GITHUB": ("interface", "explain", "recovery", "open"),
}

BOOK_POSES: tuple[str, ...] = ()
MAGIC_ACTION_POSES = (
    "204_magic_cast_release",
    "205_magic_cast_hold",
    "206_magic_cast_recoil",
    "220_magic_mastery_hero",
)
PHYSICAL_COMEDY_POSES: dict[str, tuple[str, ...]] = {
    "double take": ("238_comedy_double_take_one", "239_comedy_double_take_two"),
    "staff tangle": ("240_comedy_staff_tangle",),
    "hat": ("241_comedy_hat_save",),
    "hats": ("241_comedy_hat_save",),
    "stumble": ("242_comedy_stumble",),
    "trip": ("242_comedy_stumble",),
    "cartwheel": ("242_comedy_stumble", "243_comedy_recover_dignity"),
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _split_thought_groups(text: str) -> list[str]:
    groups = [
        item.strip()
        for item in text.replace("\u2026", "...").split("...")
        if item.strip()
    ]
    if len(groups) > 1:
        return groups
    sentences = [
        item.strip()
        for item in text.replace("?", "?|").replace("!", "!|").replace(". ", ".|").split("|")
        if item.strip()
    ]
    return sentences or [text.strip()]


def _partition_groups(groups: list[str], count: int) -> list[str]:
    if count <= 0:
        raise ValueError("choreography requires at least one cue")
    if not groups:
        return [""] * count
    result: list[str] = []
    for index in range(count):
        start = round(index * len(groups) / count)
        end = round((index + 1) * len(groups) / count)
        result.append(" ".join(groups[start:max(start + 1, end)]).strip())
    return result


def _family(clip_id: str) -> str:
    parts = clip_id.split("_")
    if len(parts) > 2 and parts[1] == "FIRST":
        return "FIRST"
    return parts[1] if len(parts) > 1 else "INTRO"


def _stable_index(key: str, size: int) -> int:
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:4], "big") % size


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    return any(
        re.search(rf"\b{re.escape(keyword)}\b", text, flags=re.IGNORECASE)
        is not None
        for keyword in keywords
    )


def _intent_for_text(text: str, fallback: str) -> str:
    lower = text.lower()
    if "?" in text:
        return "question"
    if _contains_keyword(
        lower,
        (
            "boundary",
            "consent",
            "decline",
            "endorse",
            "no contact",
            "put thoughts",
            "quiet",
        ),
    ):
        return "boundary"
    if _contains_keyword(
        lower,
        (
            "sorry",
            "rest",
            "take your time",
            "when you are ready",
            "not ready",
            "try again",
        ),
    ):
        return "reassure"
    if _contains_keyword(
        lower,
        ("unlock", "complete", "congratulate", "congratulations"),
    ):
        return "celebrate"
    if _contains_keyword(
        lower,
        ("first", "second", "third", "steps", "three", "list"),
    ):
        return "sequence"
    if _contains_keyword(
        lower,
        ("map", "button", "dial", "panel", "source trail", "github"),
    ):
        return "interface"
    if _contains_keyword(
        lower,
        ("cast", "spell", "hypercube", "projection", "summon"),
    ):
        return "magic"
    if _contains_keyword(
        lower,
        ("story", "lore", "once", "world", "adventure"),
    ):
        return "story"
    if _contains_keyword(
        lower,
        (
            "cartwheel",
            "funny",
            "haunted",
            "hat",
            "hamster",
            "joke",
            "mattress",
            "squirrel",
            "snack",
            "stumble",
            "trip",
            "trench coat",
            "villain",
        ),
    ):
        if len(text) <= 180:
            return "comic"
        return fallback
    if _contains_keyword(
        lower,
        ("must", "keep", "choose", "decide", "promise"),
    ):
        return "resolve"
    return fallback


def _authored_templates(
    clip_id: str,
    text: str,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if clip_id in HERO_CHOREOGRAPHY:
        return HERO_CHOREOGRAPHY[clip_id]
    groups = _split_thought_groups(text)
    arc = FAMILY_ARCS.get(_family(clip_id), FAMILY_ARCS["INTRO"])
    count = max(1, min(7, len(groups)))
    templates: list[tuple[str, tuple[str, ...]]] = []
    previous_pose = ""
    for index in range(count):
        group = groups[min(index, len(groups) - 1)]
        fallback = arc[min(index, len(arc) - 1)]
        intent = _intent_for_text(group, fallback)
        bank = INTENT_POSES[intent]
        start = _stable_index(f"{clip_id}:{index}:{intent}", len(bank))
        selected = [bank[(start + offset) % len(bank)] for offset in range(min(3, len(bank)))]
        if selected[0] == previous_pose:
            selected = selected[1:] + selected[:1]
        previous_pose = selected[-1]
        templates.append((intent, tuple(selected)))
    return tuple(templates)


def _timed_cues(
    clip_id: str,
    text: str,
    duration_ms: int,
) -> list[dict[str, Any]]:
    templates = _authored_templates(clip_id, text)
    cue_texts = _partition_groups(_split_thought_groups(text), len(templates))
    weights = [max(1, len(item)) for item in cue_texts]
    total = sum(weights)
    cursor = 0
    cues: list[dict[str, Any]] = []
    for index, ((label, pose_ids), cue_text, weight) in enumerate(
        zip(templates, cue_texts, weights)
    ):
        end_ms = (
            duration_ms
            if index == len(templates) - 1
            else max(cursor + 1, round(duration_ms * sum(weights[: index + 1]) / total))
        )
        cues.append(
            {
                "cue_id": f"{clip_id.lower()}:body:{index + 1:02d}",
                "label": label,
                "start_ms": cursor,
                "end_ms": end_ms,
                "text": cue_text,
                "pose_ids": list(pose_ids),
                "pose_hold_ms": (
                    MIN_MOTION_BEAT_SPACING_MS
                    + _stable_index(f"{clip_id}:{index}:hold", 650)
                ),
                "crossfade_ms": BODY_TRANSITION_MS,
            }
        )
        cursor = end_ms
    return cues


def _cue_pose_bank(cue: dict[str, Any], clip_id: str) -> list[str]:
    if clip_id in {"WJ_INTRO_001", "WJ_INTRO_002"}:
        return list(
            dict.fromkeys(
                [
                    *(
                        pose_id
                        for pose_id in cue["pose_ids"]
                        if "_flight_" in str(pose_id)
                    ),
                    *AIR_SPEECH_POSES,
                ]
            )
        )
    label = str(cue.get("label", ""))
    fallback_intent = label if label in INTENT_POSES else "open"
    cue_text = str(cue.get("text", ""))
    cue_text_lower = cue_text.lower()
    intent = _intent_for_text(cue_text, fallback_intent)
    candidates = [*cue["pose_ids"], *INTENT_POSES[intent]]
    if _contains_keyword(cue_text_lower, ("book", "notebook", "page", "read")):
        candidates.extend(BOOK_POSES)
    if _contains_keyword(
        cue_text_lower,
        ("cast", "portal", "spell", "summon"),
    ):
        candidates.extend(MAGIC_ACTION_POSES)
    if intent == "comic":
        for phrase, pose_ids in PHYSICAL_COMEDY_POSES.items():
            if _contains_keyword(cue_text_lower, (phrase,)):
                candidates.extend(pose_ids)
    else:
        broad_comedy = {
            pose_id
            for pose_ids in PHYSICAL_COMEDY_POSES.values()
            for pose_id in pose_ids
        }
        candidates = [pose_id for pose_id in candidates if pose_id not in broad_comedy]
    return list(dict.fromkeys(str(pose_id) for pose_id in candidates))


def _select_nonrepeating_pose(
    candidates: list[str],
    *,
    offset: int,
    recent_poses: list[str],
    used_transitions: set[tuple[str, str]],
    next_pose_id: str | None = None,
    forbidden_pose_ids: set[str] | None = None,
) -> str:
    if not candidates:
        raise ValueError("motion beat requires at least one pose candidate")
    blocked_pose_ids = {
        *recent_poses[-MOTION_REPETITION_WINDOW:],
        *(forbidden_pose_ids or set()),
    }
    for index in range(len(candidates)):
        pose_id = candidates[(offset + index) % len(candidates)]
        previous_pose_id = recent_poses[-1] if recent_poses else None
        if (
            pose_id not in blocked_pose_ids
            and (
                previous_pose_id is None
                or (previous_pose_id, pose_id) not in used_transitions
            )
            and (
                next_pose_id is None
                or (pose_id, next_pose_id) not in used_transitions
            )
        ):
            return pose_id
    for index in range(len(candidates)):
        pose_id = candidates[(offset + index) % len(candidates)]
        if pose_id not in blocked_pose_ids:
            return pose_id
    return candidates[offset % len(candidates)]


def _fill_long_motion_gaps(
    clip_id: str,
    beats: list[dict[str, Any]],
    cues: list[dict[str, Any]],
    envelope: list[int],
    *,
    window_ms: int,
) -> list[dict[str, Any]]:
    while True:
        gap_index = next(
            (
                index
                for index, (first, second) in enumerate(zip(beats, beats[1:]))
                if int(second["time_ms"]) - int(first["time_ms"])
                > MAX_AUTHORED_MOTION_BEAT_GAP_MS
            ),
            None,
        )
        duration_ms = int(cues[-1]["end_ms"])
        terminal_gap = (
            duration_ms - int(beats[-1]["time_ms"])
            if beats
            else duration_ms
        )
        if gap_index is None and terminal_gap <= MAX_AUTHORED_MOTION_BEAT_GAP_MS:
            return beats
        terminal = gap_index is None
        if terminal:
            first = beats[-1]
            second = None
            time_ms = round((int(first["time_ms"]) + duration_ms) / 2)
        else:
            first = beats[gap_index]
            second = beats[gap_index + 1]
            time_ms = round((int(first["time_ms"]) + int(second["time_ms"])) / 2)
        cue = next(
            item
            for item in cues
            if int(item["start_ms"]) <= time_ms < int(item["end_ms"])
        )
        pose_ids = [str(item["pose_id"]) for item in beats]
        used_transitions = set(zip(pose_ids, pose_ids[1:]))
        if second is not None:
            used_transitions.discard(
                (str(first["pose_id"]), str(second["pose_id"]))
            )
        candidates = _cue_pose_bank(cue, clip_id)
        pose_id = _select_nonrepeating_pose(
            candidates,
            offset=_stable_index(
                f"{clip_id}:{cue['cue_id']}:{time_ms}:bridge",
                len(candidates),
            ),
            recent_poses=(
                pose_ids[-MOTION_REPETITION_WINDOW:]
                if terminal
                else pose_ids[
                    max(0, gap_index - MOTION_REPETITION_WINDOW + 1) :
                    gap_index + 1
                ]
            ),
            used_transitions=used_transitions,
            next_pose_id=str(second["pose_id"]) if second is not None else None,
            forbidden_pose_ids=(
                set()
                if terminal
                else set(
                    pose_ids[
                        gap_index + 1 : gap_index + 1 + MOTION_REPETITION_WINDOW
                    ]
                )
            ),
        )
        record = {
            "time_ms": time_ms,
            "pose_id": pose_id,
            "cue_id": cue["cue_id"],
            "accent_milli": (
                envelope[min(len(envelope) - 1, time_ms // window_ms)]
                if envelope
                else 0
            ),
            "authored_reason": (
                "terminal_hold_semantic_bridge"
                if terminal
                else "long_gap_semantic_bridge"
            ),
        }
        if terminal:
            beats.append(record)
        else:
            beats.insert(gap_index + 1, record)


def _settle_airborne_speech(clip_id: str, beats: list[dict[str, Any]]) -> None:
    if clip_id != "WJ_INTRO_002" or not beats:
        return
    settled_candidates = (
        "176_flight_hover_neutral",
        "186_flight_stationary_listen",
        "187_flight_stationary_speak",
    )
    recent_pose_ids = [
        str(item["pose_id"])
        for item in beats[max(0, len(beats) - MOTION_REPETITION_WINDOW - 1) : -1]
    ]
    terminal_pose_id = next(
        (
            pose_id
            for pose_id in settled_candidates
            if pose_id not in recent_pose_ids
        ),
        settled_candidates[0],
    )
    pose_ids = [str(item["pose_id"]) for item in beats]
    used_transitions = set(zip(pose_ids, pose_ids[1:]))
    previous_pose_id = str(beats[-2]["pose_id"]) if len(beats) > 1 else ""
    if (
        len(beats) > 2
        and (previous_pose_id, terminal_pose_id) in used_transitions
    ):
        turn_pose_id = "180_flight_turn_toward_camera"
        prior_pose_id = str(beats[-3]["pose_id"])
        recent_before_turn = {
            str(item["pose_id"])
            for item in beats[
                max(0, len(beats) - MOTION_REPETITION_WINDOW - 2) : -2
            ]
        }
        if (
            turn_pose_id not in recent_before_turn
            and (prior_pose_id, turn_pose_id) not in used_transitions
            and (turn_pose_id, terminal_pose_id) not in used_transitions
        ):
            beats[-2]["pose_id"] = turn_pose_id
            beats[-2]["authored_reason"] = "terminal_turn_toward_camera"
    beats[-1]["pose_id"] = terminal_pose_id
    beats[-1]["authored_reason"] = "terminal_stationary_hover"


def _motion_beats(
    clip_id: str,
    cues: list[dict[str, Any]],
    envelope: list[int],
    *,
    window_ms: int = 50,
) -> list[dict[str, Any]]:
    beats: list[dict[str, Any]] = []
    recent_poses: list[str] = []
    used_transitions: set[tuple[str, str]] = set()
    for cue_index, cue in enumerate(cues):
        start = int(cue["start_ms"])
        end = int(cue["end_ms"])
        duration = end - start
        target_count = max(1, min(4, math.ceil(duration / 3200)))
        candidates: list[tuple[int, int]] = []
        first_window = max(0, start // window_ms)
        last_window = min(len(envelope), math.ceil(end / window_ms))
        for sample_index in range(first_window + 1, max(first_window + 1, last_window - 1)):
            value = envelope[sample_index]
            if (
                value >= 480
                and value >= envelope[sample_index - 1]
                and value >= envelope[sample_index + 1]
            ):
                candidates.append((sample_index * window_ms, value))
        selected_times = (
            [start]
            if (
                not beats
                or start - int(beats[-1]["time_ms"])
                >= MIN_MOTION_BEAT_SPACING_MS
            )
            else []
        )
        for time_ms, _ in sorted(candidates, key=lambda item: (-item[1], item[0])):
            if time_ms - start < 500 or end - time_ms < 350:
                continue
            if (
                (
                    not beats
                    or time_ms - int(beats[-1]["time_ms"])
                    >= MIN_MOTION_BEAT_SPACING_MS
                )
                and all(
                    abs(time_ms - existing) >= MIN_MOTION_BEAT_SPACING_MS
                    for existing in selected_times
                )
            ):
                selected_times.append(time_ms)
            if len(selected_times) >= target_count:
                break
        for slot in range(1, target_count + 1):
            if len(selected_times) >= target_count:
                break
            time_ms = start + round(duration * slot / target_count)
            time_ms = min(end - 350, time_ms)
            if time_ms <= start:
                continue
            if (
                (not beats or time_ms - int(beats[-1]["time_ms"]) >= MIN_MOTION_BEAT_SPACING_MS)
                and all(
                    abs(time_ms - existing) >= MIN_MOTION_BEAT_SPACING_MS
                    for existing in selected_times
                )
            ):
                selected_times.append(time_ms)
        selected_times.sort()
        poses = _cue_pose_bank(cue, clip_id)
        offset = _stable_index(f"{clip_id}:{cue_index}:beats", len(poses))
        for beat_index, time_ms in enumerate(selected_times):
            pose = _select_nonrepeating_pose(
                poses,
                offset=offset + beat_index,
                recent_poses=recent_poses,
                used_transitions=used_transitions,
            )
            beats.append(
                {
                    "time_ms": time_ms,
                    "pose_id": pose,
                    "cue_id": cue["cue_id"],
                    "accent_milli": envelope[min(len(envelope) - 1, time_ms // window_ms)]
                    if envelope
                    else 0,
                }
            )
            if recent_poses:
                used_transitions.add((recent_poses[-1], pose))
            recent_poses.append(pose)
    beats = _fill_long_motion_gaps(
        clip_id,
        beats,
        cues,
        envelope,
        window_ms=window_ms,
    )
    _settle_airborne_speech(clip_id, beats)
    return beats


def _rms_envelope(pcm_path: Path, window_samples: int = 800) -> list[int]:
    payload = pcm_path.read_bytes()
    if len(payload) % 2:
        raise ValueError("canonical PCM payload is not aligned to signed 16-bit samples")
    samples = struct.unpack(f"<{len(payload) // 2}h", payload)
    rms_values: list[float] = []
    for start in range(0, len(samples), window_samples):
        window = samples[start : start + window_samples]
        if not window:
            continue
        mean_square = sum(value * value for value in window) / len(window)
        rms_values.append(math.sqrt(mean_square))
    nonzero = sorted(value for value in rms_values if value > 0)
    if not nonzero:
        return [0 for _ in rms_values]
    reference = nonzero[min(len(nonzero) - 1, round((len(nonzero) - 1) * 0.95))]
    return [min(1000, max(0, round(value * 1000 / reference))) for value in rms_values]


def _pose_ids(index: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for shard in index["shards"]:
        result.update(str(item) for item in shard["pose_ids"])
    return result


def _validate_pose_references(index: dict[str, Any]) -> None:
    available = _pose_ids(index)
    required = {
        SETTLE_POSE,
        HOVER_POSE,
        *AIR_SPEECH_POSES,
        *APPROACH_POSES,
        *FLIGHT_APPROACH_POSES,
    }
    for clip_id in HERO_CHOREOGRAPHY:
        approach = _approach_for_clip(clip_id, 10_000)
        required.update(approach["pose_ids"])
        required.update(approach.get("arrival_pose_ids", ()))
        required.add(_settle_pose_for_clip(clip_id))
    for templates in HERO_CHOREOGRAPHY.values():
        for _, pose_ids in templates:
            required.update(pose_ids)
    for pose_ids in INTENT_POSES.values():
        required.update(pose_ids)
    required.update(BOOK_POSES)
    required.update(MAGIC_ACTION_POSES)
    for pose_ids in PHYSICAL_COMEDY_POSES.values():
        required.update(pose_ids)
    missing = sorted(required - available)
    if missing:
        raise ValueError(f"HD pose library is missing choreography poses: {missing}")


def import_performances(
    package_dir: Path,
    output_dir: Path,
    hd_index_path: Path,
    *,
    joeville_commit: str = JOEVILLE_COMMIT,
) -> dict[str, Any]:
    package_dir = package_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    hd_index_path = hd_index_path.expanduser().resolve()
    transcript_records = _read_json(package_dir / "wizard_joe_tts_manifest.json")
    clip_ids = tuple(str(item["id"]) for item in transcript_records)
    transcripts = {str(item["id"]): str(item["text"]) for item in transcript_records}
    hd_index = _read_json(hd_index_path)
    _validate_pose_references(hd_index)

    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    clips: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="wizard-joe-audio-performance-") as temp_name:
        temp_dir = Path(temp_name)
        for clip_id in clip_ids:
            source = package_dir / "audio" / f"{clip_id}.mp3"
            if not source.is_file():
                raise FileNotFoundError(source)
            if clip_id not in transcripts:
                raise ValueError(f"canonical transcript missing for {clip_id}")
            probe = probe_media(source)
            destination = audio_dir / source.name
            shutil.copyfile(source, destination)
            pcm_path = temp_dir / f"{clip_id}.s16le"
            pcm = canonicalize_pcm(source, pcm_path)
            envelope = _rms_envelope(pcm_path)
            transcript = transcripts[clip_id]
            body_cues = _timed_cues(clip_id, transcript, probe.duration_ms)
            clips.append(
                {
                    "clip_id": clip_id,
                    "display_name": clip_id.replace("WJ_", "").replace("_", " ").title(),
                    "audio": {
                        "path": f"audio/{source.name}",
                        "sha256": probe.source_sha256,
                        "bytes": probe.byte_length,
                        "duration_ms": probe.duration_ms,
                        "mime_type": probe.mime_type,
                        "codec_name": probe.codec_name,
                        "sample_rate_hz": probe.sample_rate_hz,
                        "channels": probe.channels,
                        "canonical_pcm_sha256": pcm.pcm_sha256,
                        "decoder_build_sha256": pcm.decoder_build_sha256,
                        "decoder_arguments_sha256": pcm.decoder_arguments_sha256,
                    },
                    "transcript": transcript,
                    "performance": {
                        "performance_id": (
                            f"wizard-joe:{clip_id.lower()}:"
                            f"{_approach_for_clip(clip_id, probe.duration_ms)['mode']}:v2"
                        ),
                        "approval_state": "candidate_visual_review",
                        "runtime_admitted": False,
                        "clock": "html_audio_element_current_time",
                        "motion_style": (
                            "hover"
                            if clip_id in {"WJ_INTRO_001", "WJ_INTRO_002"}
                            else "grounded"
                        ),
                        "body_transition_ms": BODY_TRANSITION_MS,
                        "approach": _approach_for_clip(
                            clip_id,
                            probe.duration_ms,
                        ),
                        "body_cues": body_cues,
                        "motion_beats": _motion_beats(
                            clip_id,
                            body_cues,
                            envelope,
                        ),
                        "speech_envelope": {
                            "window_ms": 50,
                            "values_milli": envelope,
                            "source": "canonical_pcm_rms",
                        },
                        "settle_pose_id": _settle_pose_for_clip(clip_id),
                    },
                }
            )

    hd_index_sha256 = _sha256_file(hd_index_path)
    manifest = {
        "schema_version": 1,
        "program_id": "wizard-joe-joeville-audio-performance-review-v1",
        "character_id": "wizard-joe-v1",
        "display_name": "Wizard Joe",
        "source_game": {
            "repository": "https://github.com/jedisherpa/joeville",
            "commit": joeville_commit,
            "motion_contracts": {
                "timeline": "client/src/intro/introTimeline.ts",
                "scene": "client/src/game/scenes/Intro.ts",
                "front_walk_fps": 10,
                "walk_push_ms": 4200,
                "idle_scale_milli": 1080,
                "ground_y_fraction_milli": 820,
            },
        },
        "projector": {
            "library_index": hd_index_path.relative_to(ROOT).as_posix(),
            "library_index_sha256": hd_index_sha256,
            "canvas_width": int(hd_index["profile"]["canvas_width"]),
            "canvas_height": int(hd_index["profile"]["canvas_height"]),
            "pixel_format": "rgba8",
            "render_assets": "compiled_colored_pixel_graphs",
        },
        "audio_package": {
            "source_manifest_sha256": _sha256_file(
                package_dir / "wizard_joe_tts_manifest.json"
            ),
            "voice_record": "user-supplied corrected Wizard Joe voice package",
        },
        "clips": clips,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    review_state = {
        "schema_version": 1,
        "program_id": manifest["program_id"],
        "decisions": {
            clip_id: {"status": "unreviewed", "notes": ""}
            for clip_id in clip_ids
        },
    }
    review_path = output_dir / "review-state.json"
    if review_path.exists():
        existing = _read_json(review_path)
        for clip_id, decision in existing.get("decisions", {}).items():
            if clip_id in review_state["decisions"]:
                review_state["decisions"][clip_id] = decision
    review_path.write_text(json.dumps(review_state, indent=2) + "\n", encoding="utf-8")
    return {
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "manifest_sha256": _sha256_file(manifest_path),
        "review_state": review_path.relative_to(ROOT).as_posix(),
        "clip_count": len(clips),
        "audio_bytes": sum(int(item["audio"]["bytes"]) for item in clips),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import the governed Wizard Joe voice lines and author review choreography."
    )
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--hd-index", type=Path, default=DEFAULT_HD_INDEX)
    parser.add_argument("--joeville-commit", default=JOEVILLE_COMMIT)
    args = parser.parse_args()
    receipt = import_performances(
        args.package,
        args.output,
        args.hd_index,
        joeville_commit=args.joeville_commit,
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
