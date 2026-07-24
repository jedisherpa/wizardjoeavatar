import json
import tempfile
import unittest
from pathlib import Path

from tools.prepare_character_director_v9_fixture import (
    CAPTURE_FRAMES,
    MEDIA_SHA256,
    PROFILE_ORDER,
    build_scenario_program,
    build_score_document,
    load_score,
    prepare_fixture,
)
from tools.run_character_director_visual_review import load_scenario_program
from wizard_avatar.character_capabilities import derive_character_capability_manifest
from wizard_avatar.media_session import MediaSessionSnapshotV1
from wizard_avatar.performance_scheduler import PerformanceScheduler


class CharacterDirectorV9FixtureTests(unittest.TestCase):
    def test_score_is_strict_character_bound_and_deterministic(self):
        first = load_score()
        second = load_score()
        sources = derive_character_capability_manifest()["sources"]

        self.assertEqual(first.artifact_sha256, second.artifact_sha256)
        self.assertEqual(first.to_dict(), build_score_document())
        self.assertEqual(first.media_sha256, MEDIA_SHA256)
        self.assertEqual(first.package_digest, sources["package_sha256"])
        self.assertEqual(
            first.to_dict()["character"]["pose_library_digest"],
            sources["pose_library_sha256"],
        )
        self.assertEqual(
            first.to_dict()["character"]["graph_digest"],
            sources["animation_graph_sha256"],
        )

    def test_program_replays_one_score_across_all_motion_profiles(self):
        score = load_score()
        program = build_scenario_program(score)
        encoded = json.dumps(
            program,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        snapshots = []
        for scenario, profile in zip(program["scenarios"], PROFILE_ORDER):
            self.assertEqual(scenario["name"], "v9-{}-profile".format(profile))
            self.assertEqual(scenario["timing"]["capture_frames"], CAPTURE_FRAMES)
            self.assertEqual(len(scenario["timing"]["scheduled_commands"]), 8)
            snapshots.append(scenario["payload"])
            snapshots.extend(
                item["payload"]
                for item in scenario["timing"]["scheduled_commands"]
            )

        parsed = [MediaSessionSnapshotV1.from_mapping(item) for item in snapshots]
        self.assertLess(len(encoded), 64 * 1024)
        self.assertEqual([item.sequence for item in parsed], list(range(1, 28)))
        self.assertEqual(
            [parsed[index * 9].performance.motion_profile for index in range(3)],
            list(PROFILE_ORDER),
        )
        self.assertEqual(
            {item.performance.score_sha256 for item in parsed},
            {score.artifact_sha256},
        )
        self.assertEqual(
            {item.performance.character_package_sha256 for item in parsed},
            {score.package_digest},
        )

    def test_scheduler_preserves_face_and_speech_while_suppressing_body(self):
        scheduler = PerformanceScheduler(load_score())
        for media_time in (1000, 3000, 4500, 6500):
            full = scheduler.evaluate(media_time, motion_profile="full")
            reduced = scheduler.evaluate(media_time, motion_profile="reduced")
            still = scheduler.evaluate(media_time, motion_profile="still")

            self.assertEqual(reduced.world_position_milli, (0, 0))
            self.assertEqual(still.world_position_milli, (0, 0))
            self.assertFalse(
                reduced.owned_channels
                & {"body", "body_base", "gesture", "effects", "locomotion", "stage"}
            )
            self.assertFalse(
                still.owned_channels
                & {"body", "body_base", "gesture", "effects", "locomotion", "stage"}
            )
            self.assertTrue(reduced.owned_channels & {"face", "gaze", "eyes"})
            self.assertTrue(still.owned_channels & {"face", "gaze", "eyes"})
            if media_time < 5600:
                self.assertTrue(full.speaking)
                self.assertTrue(reduced.speaking)
                self.assertTrue(still.speaking)
                self.assertIn("mouth", reduced.owned_channels)
                self.assertIn("mouth", still.owned_channels)

        full_walk = scheduler.evaluate(6500, motion_profile="full")
        self.assertNotEqual(full_walk.world_position_milli, (0, 0))
        self.assertTrue(full_walk.owned_channels & {"locomotion", "stage"})

    def test_fixture_publishes_and_reloads_through_real_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = prepare_fixture(root / "scores", root / "v9.json")
            program = load_scenario_program(root / "v9.json")

            self.assertEqual(result["score_sha256"], load_score().artifact_sha256)
            self.assertEqual(result["total_capture_frames"], 648)
            self.assertEqual(program.acceptance_scenario, "V9")
            self.assertEqual(program.maximum_capture_frame_count, 648)


if __name__ == "__main__":
    unittest.main()
