import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.import_wizard_joe_audio_performances import (
    APPROACH_POSES,
    FLIGHT_APPROACH_POSES,
    HERO_CHOREOGRAPHY,
    HOVER_POSE,
    INTENT_POSES,
    SETTLE_POSE,
    _approach_for_clip,
    _authored_templates,
    _motion_beats,
    _partition_groups,
    _timed_cues,
    _validate_pose_references,
)


class WizardJoeAudioPerformanceImportTests(unittest.TestCase):
    def test_hero_clips_keep_explicit_authored_choreography(self):
        self.assertEqual(len(HERO_CHOREOGRAPHY), 12)
        self.assertTrue(all(HERO_CHOREOGRAPHY.values()))

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
        for templates in HERO_CHOREOGRAPHY.values():
            for _, pose_ids in templates:
                required.update(pose_ids)
        for pose_ids in INTENT_POSES.values():
            required.update(pose_ids)
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
        self.assertIn("190_flight_reach", poses)
        self.assertIn("188_flight_staff_forward", poses)

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
            self.assertGreaterEqual(current["time_ms"] - previous["time_ms"], 950)
            self.assertNotEqual(previous["pose_id"], current["pose_id"])


if __name__ == "__main__":
    unittest.main()
