import asyncio
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.build_dragon_repair_review import build_dragon_repair_review
from tools.build_hd_rgba_character_candidate import build_candidate
from wizard_avatar.character_package import load_character_package
from wizard_avatar.hd_rgba_frame_source import HDPoseFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.stream import WizardFrameHub


ROOT = Path(__file__).resolve().parents[2]
DRAGON_ROOT = ROOT / "assets" / "reference" / "characters" / "dragon"
TEMPORARY = None
REVIEW_INDEX = None
CANDIDATE_ROOT = None
PACKAGE_PATH = None
RECEIPT = None


def setUpModule():
    global TEMPORARY, REVIEW_INDEX, CANDIDATE_ROOT, PACKAGE_PATH, RECEIPT
    TEMPORARY = tempfile.TemporaryDirectory(
        prefix=".dragon-runtime-candidate-test-",
        dir=str(DRAGON_ROOT),
    )
    root = Path(TEMPORARY.name)
    review_root = root / "review"
    CANDIDATE_ROOT = root / "candidate"
    build_dragon_repair_review(output_dir=review_root)
    REVIEW_INDEX = review_root / "library-index.json"
    RECEIPT = build_candidate(
        REVIEW_INDEX,
        CANDIDATE_ROOT,
    )
    PACKAGE_PATH = CANDIDATE_ROOT / "dragon-character-package-v2.json"


def tearDownModule():
    global TEMPORARY, REVIEW_INDEX, CANDIDATE_ROOT, PACKAGE_PATH, RECEIPT
    if TEMPORARY is not None:
        TEMPORARY.cleanup()
    TEMPORARY = None
    REVIEW_INDEX = None
    CANDIDATE_ROOT = None
    PACKAGE_PATH = None
    RECEIPT = None


class DragonRuntimeCandidateTests(unittest.TestCase):
    def test_candidate_rebuild_is_byte_identical(self):
        def output_hashes():
            return {
                path.relative_to(CANDIDATE_ROOT).as_posix(): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in sorted(CANDIDATE_ROOT.rglob("*"))
                if path.is_file()
            }

        first = output_hashes()
        build_candidate(REVIEW_INDEX, CANDIDATE_ROOT)

        self.assertEqual(output_hashes(), first)

    def test_candidate_is_digest_bound_and_review_only(self):
        package = load_character_package(PACKAGE_PATH)

        self.assertEqual(package.character_id, "dragon")
        self.assertEqual(package.renderer_adapter_id, "asciline.hd_rgba_pose.v1")
        self.assertEqual(package.render_mode, "rgba")
        self.assertFalse(package.runtime_admitted)
        self.assertEqual(RECEIPT["pose_count"], 134)
        self.assertEqual(
            package.choreography_dictionary_contract.library_class,
            "comprehensive_performance",
        )
        self.assertIn("hover_speech_cycle", package.capabilities)
        self.assertIn("storytelling_speech_cycle", package.capabilities)

    def test_runtime_profile_declares_flight_and_body_locked_speech(self):
        package = load_character_package(PACKAGE_PATH)
        profile = package.runtime_profile_contract

        self.assertEqual(profile.schema_version, 3)
        self.assertEqual(len(profile.locomotion_cycles["walk"]), 4)
        self.assertEqual(len(profile.locomotion_cycles["run"]), 2)
        self.assertEqual(len(profile.locomotion_cycles["flight"]), 15)
        self.assertEqual(len(profile.speech_poses), 31)
        self.assertEqual(
            profile.speech_pose_pairs["dragon.act.001.neutral-front"],
            "dragon.act.085.speech-small-open",
        )
        self.assertEqual(
            profile.speech_pose_pairs["dragon.act.084.glide-hover"],
            "dragon.act.096.hover-speech-small-open",
        )
        self.assertEqual(
            profile.speech_pose_pairs["dragon.act.095.hover-listening"],
            "dragon.act.099.hover-emphatic-speaking",
        )

    def test_graph_uses_authored_dragon_flight_and_speech_order(self):
        package = load_character_package(PACKAGE_PATH)
        graph = json.loads(package.animation_graph.read_text(encoding="utf-8"))
        clips = graph["clips"]

        self.assertEqual(
            [sample["pose_id"] for sample in clips["landing_cycle"]["samples"]],
            [
                "dragon.act.092.flight-brake",
                "dragon.act.091.flight-descend",
                "dragon.act.094.flight-landing",
            ],
        )
        self.assertEqual(
            len(clips["hover_speech_cycle"]["samples"]), 5
        )
        self.assertEqual(
            len(clips["storytelling_speech_cycle"]["samples"]), 24
        )

    def test_full_resolution_frame_uses_the_package_pixel_graph(self):
        source = HDPoseFrameSource(
            fps=24,
            character_package_path=PACKAGE_PATH,
        )

        candidate = source.render_captured_candidate_sync(
            source.capture_render_state()
        )
        message, frame = source.commit_render_candidate(candidate)

        self.assertEqual((source.cols, source.rows), (1920, 1080))
        self.assertEqual(source.render_mode, "rgba")
        self.assertEqual(len(frame.cells), 1920 * 1080 * 4)
        self.assertTrue(frame.is_keyframe)
        self.assertGreater(len(message), 1000)
        self.assertEqual(
            candidate.animation_truth.rendered_pose_id,
            "dragon.act.001.neutral-front",
        )


class DragonRuntimeCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_flight_hover_speech_and_storytelling_poses_are_reachable(self):
        source = HDPoseFrameSource(
            fps=24,
            character_package_path=PACKAGE_PATH,
        )
        hub = WizardFrameHub(source)
        try:
            for pose_id in (
                "dragon.act.082.flight-downstroke",
                "dragon.act.095.hover-listening",
                "dragon.act.096.hover-speech-small-open",
                "dragon.act.100.explain-small-open",
                "dragon.act.123.conclusion-wide-open",
            ):
                result = await hub.apply_command(
                    WizardCommand(
                        "pose",
                        {"pose_id": pose_id, "duration_ms": 80},
                    )
                )
                self.assertTrue(result.ok, result.message)
                await asyncio.sleep(0.02)
                self.assertFalse(hub._task.done())
            self.assertEqual(hub._task_failure_count, 0)
        finally:
            await hub.stop()


if __name__ == "__main__":
    unittest.main()
