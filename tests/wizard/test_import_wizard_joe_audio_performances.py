import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.import_wizard_joe_audio_performances import (
    AIR_SPEECH_POSES,
    APPROACH_POSES,
    BOOK_POSES,
    FLIGHT_APPROACH_POSES,
    HERO_CHOREOGRAPHY,
    HOVER_POSE,
    INTENT_POSES,
    MAGIC_ACTION_POSES,
    MIN_MOTION_BEAT_SPACING_MS,
    MOTION_REPETITION_WINDOW,
    PHYSICAL_COMEDY_POSES,
    SETTLE_POSE,
    _approach_for_clip,
    _authored_templates,
    _contains_keyword,
    _cue_pose_bank,
    _intent_for_text,
    _motion_beats,
    _partition_groups,
    _timed_cues,
    _validate_pose_references,
)


class WizardJoeAudioPerformanceImportTests(unittest.TestCase):
    def test_semantic_keywords_use_word_boundaries(self):
        self.assertTrue(_contains_keyword("arranging hats", ("hat", "hats")))
        self.assertFalse(_contains_keyword("that is enough", ("hat",)))

    def test_generic_interface_bank_keeps_staff_on_canonical_side(self):
        self.assertNotIn("065_news_point_graphic_right", INTENT_POSES["interface"])

    def test_generic_semantics_keep_calm_language_restrained(self):
        self.assertEqual(
            _intent_for_text("When you are ready, the door will still be here.", "resolve"),
            "reassure",
        )
        self.assertEqual(
            _intent_for_text("The little wizard can compare these sources.", "explain"),
            "explain",
        )
        self.assertEqual(
            _intent_for_text("Enjoy the magic, but check the labels.", "open"),
            "open",
        )
        self.assertNotIn("053_speak_challenge", INTENT_POSES["boundary"])
        self.assertEqual(BOOK_POSES, ())

    def test_magic_noun_does_not_trigger_a_full_cast(self):
        pose_ids = _cue_pose_bank(
            {
                "label": "magic",
                "text": "The most powerful magic in the game.",
                "pose_ids": ["196_magic_sense", "200_magic_trace_symbol"],
            },
            "WJ_BOUNDARY_001",
        )
        self.assertTrue(set(pose_ids).isdisjoint(MAGIC_ACTION_POSES))

    def test_hero_clips_keep_explicit_authored_choreography(self):
        self.assertEqual(len(HERO_CHOREOGRAPHY), 13)
        self.assertTrue(all(HERO_CHOREOGRAPHY.values()))
        self.assertIn("WJ_BOUNDARY_DECLINE", HERO_CHOREOGRAPHY)

    def test_any_package_clip_receives_deterministic_semantic_choreography(self):
        first = _authored_templates(
            "WJ_GITHUB_CONFLICT",
            "A merge conflict. Nobody is evil. Choose deliberately.",
        )
        second = _authored_templates(
            "WJ_GITHUB_CONFLICT",
            "A merge conflict. Nobody is evil. Choose deliberately.",
        )
        self.assertEqual(first, second)
        self.assertTrue(first)
        self.assertTrue(all(pose_ids for _, pose_ids in first))

    def test_timed_cues_cover_the_complete_audio_without_gaps(self):
        cues = _timed_cues(
            "WJ_INTRO_001",
            "First thought. ... Second thought. ... Third thought.",
            26471,
        )

        self.assertEqual(cues[0]["start_ms"], 0)
        self.assertEqual(cues[-1]["end_ms"], 26471)
        for previous, current in zip(cues, cues[1:]):
            self.assertEqual(previous["end_ms"], current["start_ms"])
        self.assertTrue(all(cue["end_ms"] > cue["start_ms"] for cue in cues))

    def test_partitioning_retains_all_supplied_thought_groups(self):
        groups = ["one", "two", "three", "four", "five"]
        partitioned = _partition_groups(groups, 3)

        self.assertEqual(" ".join(partitioned), " ".join(groups))

    def test_pose_validation_requires_approach_settle_and_body_cues(self):
        required = {SETTLE_POSE, HOVER_POSE, *APPROACH_POSES, *FLIGHT_APPROACH_POSES}
        required.update(AIR_SPEECH_POSES)
        for templates in HERO_CHOREOGRAPHY.values():
            for _, pose_ids in templates:
                required.update(pose_ids)
        for pose_ids in INTENT_POSES.values():
            required.update(pose_ids)
        required.update(BOOK_POSES)
        required.update(MAGIC_ACTION_POSES)
        for pose_ids in PHYSICAL_COMEDY_POSES.values():
            required.update(pose_ids)
        required.add("247_camera_intimate_hold")
        index = {
            "shards": [
                {
                    "pose_ids": sorted(required),
                }
            ]
        }

        _validate_pose_references(index)
        index["shards"][0]["pose_ids"].remove(SETTLE_POSE)
        with self.assertRaisesRegex(ValueError, SETTLE_POSE):
            _validate_pose_references(index)

    def test_intro_one_flies_from_distance_until_hovering_on_final_word(self):
        approach = _approach_for_clip("WJ_INTRO_001", 26_471)

        self.assertEqual(approach["mode"], "fly_toward_camera")
        self.assertEqual(approach["start_ms"], 0)
        self.assertEqual(approach["end_ms"], 26_471)
        self.assertLess(approach["start_scale_milli"], 400)
        self.assertEqual(approach["end_scale_milli"], 1080)
        self.assertEqual(approach["arrival_pose_ids"][-1], HOVER_POSE)

    def test_intro_two_is_authored_as_hovering_airborne_speech(self):
        approach = _approach_for_clip("WJ_INTRO_002", 40_960)
        poses = {
            pose
            for _, sequence in HERO_CHOREOGRAPHY["WJ_INTRO_002"]
            for pose in sequence
        }

        self.assertEqual(approach["mode"], "hover")
        self.assertEqual(approach["end_ms"], 0)
        self.assertIn("187_flight_stationary_speak", poses)
        self.assertIn("174_flight_powerstroke_down", poses)
        self.assertIn("175_flight_recoverystroke_up", poses)
        self.assertIn("188_flight_staff_forward", poses)
        self.assertNotIn("190_flight_reach", poses)

    def test_intro_two_motion_beats_remain_airborne(self):
        cues = _timed_cues(
            "WJ_INTRO_002",
            "Notice this. ... Let me explain it. ... There you are.",
            12_000,
        )
        beats = _motion_beats("WJ_INTRO_002", cues, [700] * 240)

        self.assertTrue(beats)
        self.assertTrue(
            all("_flight_" in beat["pose_id"] for beat in beats)
        )
        self.assertIn(
            beats[-1]["pose_id"],
            {
                "176_flight_hover_neutral",
                "186_flight_stationary_listen",
                "187_flight_stationary_speak",
            },
        )

    def test_grounded_approach_never_cycles_through_retreat_or_recovery(self):
        approach = _approach_for_clip("WJ_WORLD_001", 23_684)

        self.assertEqual(approach["pose_ids"], ["246_camera_approach"])
        self.assertEqual(approach["arrival_pose_ids"], ["247_camera_intimate_hold"])
        self.assertNotIn("248_camera_retreat", approach["pose_ids"])

    def test_motion_beats_follow_audio_accents_without_rapid_repetition(self):
        cues = [
            {
                "cue_id": "cue:1",
                "start_ms": 0,
                "end_ms": 4000,
                "pose_ids": ["one", "two", "three"],
            }
        ]
        envelope = [0] * 80
        for index, value in ((10, 700), (30, 900), (52, 800), (70, 850)):
            envelope[index] = value
        beats = _motion_beats("WJ_TEST", cues, envelope)
        self.assertEqual(beats[0]["time_ms"], 0)
        for previous, current in zip(beats, beats[1:]):
            self.assertGreaterEqual(
                current["time_ms"] - previous["time_ms"],
                MIN_MOTION_BEAT_SPACING_MS,
            )
            self.assertNotEqual(previous["pose_id"], current["pose_id"])
        pose_ids = [beat["pose_id"] for beat in beats]
        for index, pose_id in enumerate(pose_ids):
            self.assertNotIn(
                pose_id,
                pose_ids[max(0, index - MOTION_REPETITION_WINDOW) : index],
            )


if __name__ == "__main__":
    unittest.main()
