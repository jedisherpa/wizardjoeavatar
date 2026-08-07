import tempfile
import unittest
from pathlib import Path

from tools.build_kingfisher_runtime_candidate import build_candidate
from wizard_avatar.character_package import load_character_package
from wizard_avatar.hd_rgba_frame_source import HDPoseFrameSource
from wizard_avatar.models import WizardCommand


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "assets/reference/characters/kingfisher/pair-review-compiled"
SOURCE_INDEX = SOURCE_ROOT / "library-index.json"
TEMPORARY = None
CANDIDATE_ROOT = None
PACKAGE_PATH = None


def setUpModule():
    global TEMPORARY, CANDIDATE_ROOT, PACKAGE_PATH
    TEMPORARY = tempfile.TemporaryDirectory(
        prefix=".kingfisher-runtime-candidate-test-",
        dir=str(SOURCE_ROOT),
    )
    CANDIDATE_ROOT = Path(TEMPORARY.name)
    build_candidate(SOURCE_INDEX, CANDIDATE_ROOT)
    PACKAGE_PATH = CANDIDATE_ROOT / "kingfisher-character-package-v2.json"


def tearDownModule():
    global TEMPORARY
    if TEMPORARY is not None:
        TEMPORARY.cleanup()


class BuildKingfisherRuntimeCandidateTests(unittest.TestCase):
    def test_candidate_is_loadable_but_not_runtime_admitted(self):
        package = load_character_package(PACKAGE_PATH)

        self.assertEqual(package.character_id, "kingfisher")
        self.assertFalse(package.runtime_admitted)
        self.assertEqual(package.render_mode, "rgba")
        self.assertEqual(package.runtime_profile_contract.schema_version, 3)
        self.assertEqual(
            len(package.runtime_profile_contract.speech_pose_pairs),
            88,
        )
        self.assertEqual(
            package.choreography_dictionary_contract.library_class,
            "comprehensive_performance",
        )

    def test_open_and_closed_mouth_preserve_the_selected_body_pose(self):
        source = HDPoseFrameSource(
            fps=24,
            character_package_path=PACKAGE_PATH,
        )
        resting = "kingfisher.act.012.explain-one-point"
        speaking = "kingfisher.act.122.explain-one-point-speaking-beak"
        state = source.controller.state
        state.pose_override_id = resting
        state.pose_override_until = 0.0
        source.resolve_authoritative_animation_state()
        self.assertEqual(state.pose_id, resting)

        result = source.controller.apply_command(
            WizardCommand(
                "speak",
                {
                    "speech_id": "kingfisher-pair-test",
                    "text": "This pose remains authored while the beak moves.",
                    "duration_ms": 1200,
                },
            )
        )
        self.assertTrue(result.ok)
        state.blink_phase = 0.0
        state.mouth = "open_wide"
        source.controller.advance_tick()
        source.resolve_authoritative_animation_state()
        self.assertEqual(state.pose_id, speaking)

        state.mouth = "closed"
        source.controller.advance_tick()
        source.resolve_authoritative_animation_state()
        self.assertEqual(state.pose_id, resting)

        state.mouth = "open_medium"
        state.blink_phase = 1.0
        source.controller.advance_tick()
        source.resolve_authoritative_animation_state()
        self.assertEqual(state.pose_id, speaking)

    def test_stage_pacing_pose_has_its_own_speaking_mate(self):
        package = load_character_package(PACKAGE_PATH)
        pairs = package.runtime_profile_contract.speech_pose_pairs

        self.assertEqual(
            pairs["kingfisher.act.069.left-step-anticipation-resting-beak"],
            "kingfisher.act.070.left-step-anticipation-speaking-beak",
        )
        self.assertEqual(
            pairs["kingfisher.act.109.warm-resolution-resting-beak"],
            "kingfisher.act.110.warm-resolution-speaking-beak",
        )


if __name__ == "__main__":
    unittest.main()
