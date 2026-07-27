import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from tools.build_hd_rgba_character_candidate import build_candidate
from wizard_avatar.character_package import load_character_package
from wizard_avatar.character_registry import (
    CharacterRegistryValidationError,
    load_character_registry,
)
from wizard_avatar.hd_rgba_frame_source import HDPoseFrameSource, _translate_rgba
from wizard_avatar.models import WizardCommand
from wizard_avatar.protocol import (
    KEYFRAME_INTERVAL,
    TAG_DELTA,
    decode_frame,
    encode_rgba_frame,
)
from wizard_avatar.stream import WizardFrameHub


ROOT = Path(__file__).resolve().parents[2]
SHARED_CANVAS_ROOT = (
    ROOT
    / "assets"
    / "reference"
    / "characters"
    / "robin_speech"
    / "compiled"
)
CANDIDATE_TEMP = None
CANDIDATES = {}


def setUpModule():
    global CANDIDATE_TEMP
    CANDIDATE_TEMP = tempfile.TemporaryDirectory(
        prefix=".runtime-candidate-test-",
        dir=str(SHARED_CANVAS_ROOT),
    )
    candidate_root = Path(CANDIDATE_TEMP.name)
    for character_id, expected_offset in (
        ("robin", 480),
        ("speech", -480),
    ):
        destination = candidate_root / character_id
        build_candidate(
            SHARED_CANVAS_ROOT / character_id / "library-index.json",
            destination,
        )
        CANDIDATES[character_id] = (
            destination
            / "{}-character-package-v2.json".format(character_id),
            expected_offset,
        )


def tearDownModule():
    CANDIDATES.clear()
    if CANDIDATE_TEMP is not None:
        CANDIDATE_TEMP.cleanup()


class HDRGBAProtocolTests(unittest.TestCase):
    def test_changed_rgba_frame_round_trips_as_keyframe(self):
        rgba = bytes((index * 17) % 256 for index in range(8 * 6 * 4))

        encoded = encode_rgba_frame(rgba, None, 1)
        frame_index, decoded = decode_frame(encoded.message, None)

        self.assertEqual(frame_index, 1)
        self.assertEqual(decoded, rgba)
        self.assertTrue(encoded.is_keyframe)
        self.assertEqual(encoded.changed_cells, 48)

    def test_identical_rgba_hold_is_a_tiny_empty_delta(self):
        rgba = bytes((24, 80, 160, 255)) * 48

        encoded = encode_rgba_frame(rgba, rgba, 1)
        frame_index, decoded = decode_frame(encoded.message, rgba)

        self.assertEqual(frame_index, 1)
        self.assertEqual(decoded, rgba)
        self.assertEqual(encoded.tag, TAG_DELTA)
        self.assertEqual(encoded.changed_cells, 0)
        self.assertLessEqual(encoded.encoded_size, 16)
        self.assertFalse(encoded.is_keyframe)

    def test_periodic_rgba_keyframe_is_not_suppressed(self):
        rgba = bytes((8, 16, 32, 255)) * 12

        encoded = encode_rgba_frame(
            rgba,
            rgba,
            KEYFRAME_INTERVAL,
        )

        self.assertTrue(encoded.is_keyframe)
        self.assertNotEqual(encoded.tag, TAG_DELTA)

    def test_rgba_translation_preserves_pixels_without_resampling(self):
        source = bytearray(4 * 3 * 4)
        source[(1 * 4 + 1) * 4 : (1 * 4 + 2) * 4] = bytes((1, 2, 3, 255))

        translated = _translate_rgba(bytes(source), 4, 3, 2, -1)

        expected = bytearray(4 * 3 * 4)
        expected[(0 * 4 + 3) * 4 : (0 * 4 + 4) * 4] = bytes((1, 2, 3, 255))
        self.assertEqual(translated, bytes(expected))


class SharedCanvasHDRuntimeCandidateTests(unittest.TestCase):
    def test_candidate_package_is_bound_and_fail_closed(self):
        for character_id, (candidate_path, _) in CANDIDATES.items():
            with self.subTest(character_id=character_id):
                package = load_character_package(candidate_path)
                self.assertEqual(package.character_id, character_id)
                self.assertEqual(
                    package.renderer_adapter_id,
                    "asciline.hd_rgba_pose.v1",
                )
                self.assertEqual(package.render_mode, "rgba")
                self.assertFalse(package.runtime_admitted)
                self.assertEqual(len(package.assets), 15)
                self.assertEqual(
                    package.choreography_dictionary_contract.library_class,
                    "comprehensive_performance",
                )
                self.assertTrue(
                    package.choreography_dictionary_contract
                    .supports_phrase_level_acting
                )

    def test_review_only_candidate_cannot_enter_character_registry(self):
        for character_id, (candidate_path, _) in CANDIDATES.items():
            with self.subTest(character_id=character_id):
                package = load_character_package(candidate_path)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".json",
                    dir=package.package_path.parent,
                    delete=False,
                    encoding="utf-8",
                ) as registry:
                    registry_path = Path(registry.name)
                    registry_path.write_text(
                        json.dumps(
                            {
                                "schema_version": 2,
                                "default_character_id": character_id,
                                "characters": [
                                    {
                                        "character_id": character_id,
                                        "persona_id": "persona:" + character_id,
                                        "package": package.package_path.name,
                                        "package_sha256": package.package_sha256,
                                        "admission_sha256": "sha256:" + "0" * 64,
                                    }
                                ],
                            }
                        ),
                        encoding="utf-8",
                    )
                try:
                    with self.assertRaises(
                        CharacterRegistryValidationError
                    ):
                        load_character_registry(registry_path)
                finally:
                    registry_path.unlink(missing_ok=True)

    def test_centered_candidate_preserves_canvas_and_hold_efficiency(self):
        for character_id, (
            candidate_path,
            expected_offset,
        ) in CANDIDATES.items():
            with self.subTest(character_id=character_id):
                source = HDPoseFrameSource(
                    fps=24,
                    character_package_path=candidate_path,
                )

                candidate = source.render_captured_candidate_sync(
                    source.capture_render_state()
                )
                first_message, first_frame = (
                    source.commit_render_candidate(candidate)
                )
                second_message, second_frame = (
                    source.next_encoded_frame_sync()
                )

                self.assertEqual((source.cols, source.rows), (1920, 1080))
                self.assertEqual(source.render_mode, "rgba")
                self.assertEqual(len(first_frame.cells), 1920 * 1080 * 4)
                self.assertEqual(
                    source._presentation_offset_x,
                    expected_offset,
                )
                self.assertTrue(first_frame.is_keyframe)
                self.assertEqual(second_frame.codec_tag, TAG_DELTA)
                self.assertEqual(second_frame.changed_cells, 0)
                self.assertLessEqual(len(second_message), 16)
                _, decoded = decode_frame(first_message, None)
                self.assertEqual(decoded, first_frame.cells)

                trace = candidate.animation_truth
                self.assertEqual(
                    trace.rendered_pose_id,
                    "{}.act.001.neutral-front".format(character_id),
                )
                self.assertEqual(
                    trace.frame_fnv1a32,
                    "unavailable:hd-rgba",
                )
                self.assertEqual(trace.presented_root_stage.x, 960)


class SharedCanvasHDControllerIntegrationTests(
    unittest.IsolatedAsyncioTestCase
):
    async def test_all_package_poses_are_admitted_without_hub_failure(self):
        for character_id, (candidate_path, _) in CANDIDATES.items():
            with self.subTest(character_id=character_id):
                source = HDPoseFrameSource(
                    fps=24,
                    character_package_path=candidate_path,
                )
                hub = WizardFrameHub(source)
                try:
                    for pose_id in source.hd_library.pose_ids:
                        result = await hub.apply_command(
                            WizardCommand(
                                "pose",
                                {
                                    "pose_id": pose_id,
                                    "duration_ms": 50,
                                },
                            )
                        )
                        self.assertTrue(
                            result.ok,
                            "{} rejected {!r}: {}".format(
                                character_id,
                                pose_id,
                                result.message,
                            ),
                        )
                        await asyncio.sleep(0.01)
                        self.assertFalse(
                            hub._task.done(),
                            "frame hub stopped while admitting {!r}".format(
                                pose_id
                            ),
                        )
                    self.assertEqual(hub._task_failure_count, 0)
                finally:
                    await hub.stop()

    async def test_shared_controller_path_and_pose_sequence_do_not_fail_hub(
        self,
    ):
        for character_id, (candidate_path, _) in CANDIDATES.items():
            with self.subTest(character_id=character_id):
                await self._exercise_path_and_poses(candidate_path)

    async def _exercise_path_and_poses(self, candidate_path: Path) -> None:
        source = HDPoseFrameSource(
            fps=24,
            character_package_path=candidate_path,
        )
        hub = WizardFrameHub(source)
        try:
            result = await hub.apply_command(
                WizardCommand(
                    "path",
                    {
                        "points": [
                            {"x": -2.4, "z": 4.2},
                            {"x": 2.4, "z": 4.2},
                            {"x": 2.0, "z": 6.4},
                            {"x": -2.0, "z": 6.4},
                        ],
                        "loop": True,
                        "speed": 0.85,
                    },
                )
            )
            self.assertTrue(result.ok)

            for pose_id in source.hd_library.pose_ids[:12]:
                result = await hub.apply_command(
                    WizardCommand(
                        "pose",
                        {"pose_id": pose_id, "duration_ms": 150},
                    )
                )
                self.assertTrue(result.ok)
                await asyncio.sleep(0.16)
                self.assertFalse(
                    hub._task.done(),
                    "frame hub stopped while presenting {!r}".format(pose_id),
                )

            diagnostics = hub.diagnostics_extra()
            self.assertEqual(diagnostics["frame_hub_failure_count"], 0)
            self.assertIsNone(diagnostics["frame_hub_error_code"])
        finally:
            await hub.stop()


if __name__ == "__main__":
    unittest.main()
