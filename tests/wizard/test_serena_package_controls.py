import json
import shutil
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.character_registry import CharacterAdmissionV1
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.governed_performance import GovernedPerformanceApprovalV1
from wizard_avatar.media_session import MediaSessionSnapshotV1
from wizard_avatar.models import STAFF_STATES, WizardCommand
from wizard_avatar.performance_release import (
    GovernedSpeechError,
    GovernedSpeechRegistrationV1,
    PerformanceContextRequestV1,
)
from wizard_avatar.stream import WizardFrameHub

from tests.wizard.test_media_session import snapshot_mapping
from tests.wizard.test_performance_release import (
    MEDIA_DIGEST,
    MEDIA_ID,
    TEXT,
    alignment_mapping,
    context_request_mapping,
    text_digest,
)


SERENA_PACKAGE_PATH = (
    Path(__file__).resolve().parents[2]
    / "wizard_avatar"
    / "definitions"
    / "characters"
    / "serena_quill"
    / "serena_quill_character_package_v2.json"
)


class SerenaPackageControlTests(unittest.IsolatedAsyncioTestCase):
    def create_source(self, package_path=SERENA_PACKAGE_PATH):
        return ProceduralWizardFrameSource(
            cols=96,
            rows=54,
            fps=24,
            character_package_path=package_path,
        )

    def create_admitted_source(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        package_root = root / "serena_quill"
        shutil.copytree(SERENA_PACKAGE_PATH.parent, package_root)
        package_path = package_root / SERENA_PACKAGE_PATH.name
        source = self.create_source(package_path)
        package = source.character_package
        admission = CharacterAdmissionV1.build(
            persona_id="serena-quill",
            character_id=package.character_id,
            package_sha256=package.package_sha256,
        )
        registry_path = root / "character_registry.json"
        registry_path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "default_character_id": package.character_id,
                    "characters": [
                        {
                            "character_id": package.character_id,
                            "persona_id": admission.persona_id,
                            "package": str(package_path.relative_to(root)),
                            "package_sha256": package.package_sha256,
                            "admission_sha256": admission.admission_sha256,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return source, registry_path

    def test_staffless_package_state_is_in_public_runtime_vocabulary(self):
        source = self.create_source()

        self.assertEqual(source.controller.state.staff_state, "none")
        self.assertIn(source.controller.state.staff_state, STAFF_STATES)

    def test_facing_uses_the_package_graph(self):
        source = self.create_source()

        result = source.controller.apply_command(
            WizardCommand("face", {"direction": "east"})
        )
        source.controller.advance_tick()
        source.resolve_authoritative_animation_state()

        self.assertTrue(result.ok)
        self.assertEqual(source.controller.state.pose_id, "neutral_right_profile")
        self.assertEqual(
            source.controller.state.animation_node_id,
            "node_neutral_right_profile",
        )

    def test_package_declared_action_selects_its_authored_pose(self):
        source = self.create_source()

        result = source.controller.apply_command(
            WizardCommand(
                "action",
                {"action": "mentoring_invitation", "duration_ms": 1200},
            )
        )
        source.controller.advance_tick()
        source.resolve_authoritative_animation_state()

        self.assertTrue(result.ok)
        self.assertEqual(source.controller.state.action, "mentoring_invitation")
        self.assertEqual(source.controller.state.pose_id, "mentoring_invitation")
        self.assertEqual(
            source.controller.state.animation_node_id,
            "node_mentoring_invitation",
        )

    def test_unbound_airborne_action_is_not_admitted_as_a_static_action(self):
        source = self.create_source()
        before = source.controller.state.as_public_dict()

        result = source.controller.apply_command(
            WizardCommand(
                "action",
                {"action": "jump", "duration_ms": 1200},
            )
        )

        self.assertFalse(result.ok)
        self.assertIn("Unsupported action", result.message)
        self.assertEqual(source.controller.state.as_public_dict(), before)

    def test_wizard_only_action_is_rejected_without_state_mutation(self):
        source = self.create_source()
        before = source.controller.state.as_public_dict()
        source.controller._prism_manual_suppressed.clear()

        result = source.controller.apply_command(
            WizardCommand("action", {"action": "staff_spin"})
        )

        self.assertFalse(result.ok)
        self.assertIn("Unsupported action", result.message)
        self.assertEqual(source.controller.state.as_public_dict(), before)
        self.assertNotIn("action", source.controller._prism_manual_suppressed)

    def test_package_cast_uses_generic_action_timing_not_wizard_markers(self):
        source = self.create_source()

        result = source.controller.apply_command(
            WizardCommand(
                "action",
                {"action": "magic_cast", "duration_ms": 100},
            )
        )
        self.assertTrue(result.ok)
        for _ in range(7):
            source.controller.advance_tick()
            source.resolve_authoritative_animation_state()

        self.assertEqual(source.controller.state.action, "idle")

    def test_invalid_action_duration_is_atomic(self):
        source = self.create_source()
        source.controller._queued_speech = {
            "speech_id": "queued",
            "text": "Keep me queued.",
            "duration_ms": 900,
        }
        source.controller._prism_manual_suppressed.clear()
        before = source.controller.state.as_public_dict()
        queued_before = dict(source.controller._queued_speech)

        result = source.controller.apply_command(
            WizardCommand(
                "action",
                {
                    "action": "mentoring_invitation",
                    "duration_ms": "not-an-integer",
                },
            )
        )

        self.assertFalse(result.ok)
        self.assertIn("duration_ms", result.message)
        self.assertEqual(source.controller.state.as_public_dict(), before)
        self.assertEqual(source.controller._queued_speech, queued_before)
        self.assertNotIn("action", source.controller._prism_manual_suppressed)

    def test_invalid_speech_duration_is_atomic(self):
        source = self.create_source()
        before = source.controller.state.as_public_dict()

        result = source.controller.apply_command(
            WizardCommand(
                "speak",
                {
                    "speech_id": "invalid-duration",
                    "text": "This must not start.",
                    "duration_ms": "not-an-integer",
                },
            )
        )

        self.assertFalse(result.ok)
        self.assertIn("duration_ms", result.message)
        self.assertEqual(source.controller.state.as_public_dict(), before)
        self.assertEqual(source.controller._prism_suspensions, {})

    def test_speech_mouth_shape_selects_explicit_package_viseme(self):
        source = self.create_source()

        result = source.controller.apply_command(
            WizardCommand(
                "speak",
                {
                    "speech_id": "serena-speech",
                    "text": "A careful answer.",
                    "duration_ms": 1000,
                },
            )
        )
        self.assertTrue(result.ok)
        source.controller.state.mouth = "open_wide"
        source.controller.advance_tick()
        source.resolve_authoritative_animation_state()

        self.assertEqual(source.controller.state.pose_id, "viseme_wide_vowel")
        self.assertEqual(
            source.controller.state.animation_node_id,
            "node_viseme_wide_vowel",
        )
        self.assertEqual(source.controller.state.upper_body_action, "none")
        self.assertEqual(source.controller.state.staff_state, "none")

    def test_idle_blink_selects_explicit_package_closed_pose(self):
        source = self.create_source()

        source.controller.advance_tick()
        source.controller.state.blink_phase = 1.0
        source.resolve_authoritative_animation_state()

        self.assertEqual(source.controller.state.pose_id, "blink_closed")
        self.assertEqual(
            source.controller.state.animation_node_id,
            "node_blink_closed",
        )

    def test_missing_locomotion_cycle_rejects_before_movement_mutation(self):
        source = self.create_source()
        before = source.controller.state.as_public_dict()

        result = source.controller.apply_command(
            WizardCommand("move", {"x": 4.0, "z": 5.0})
        )

        self.assertFalse(result.ok)
        self.assertIn("walk locomotion is not admitted", result.message)
        self.assertEqual(source.controller.state.as_public_dict(), before)
        self.assertFalse(source.controller.locomotion.path.active)
        self.assertIsNone(source.controller.locomotion.movement.target_x)
        self.assertIsNone(source.controller.locomotion.movement.target_z)

    async def test_performance_application_uses_the_package_graph(self):
        source = self.create_source()
        hub = WizardFrameHub(source)

        self.assertIs(hub.performance.animation_graph, source.animation_graph)
        self.assertIs(
            hub.performance.runtime_profile,
            source.character_package.runtime_profile_contract,
        )
        self.assertTrue(hub.performance.supports_action("mentoring_invitation"))
        self.assertFalse(hub.performance.supports_action("staff_spin"))
        await hub.stop()

    async def test_reduced_motion_releases_package_owned_action(self):
        source = self.create_source()
        hub = WizardFrameHub(source)
        source.controller._set_action("mentoring_invitation", 0)
        hub.performance._last_applied_action = "mentoring_invitation"

        hub.performance._release_body_projection(source.controller)

        self.assertEqual(source.controller.state.action, "idle")
        self.assertIsNone(hub.performance._last_applied_action)
        await hub.stop()

    async def test_governed_speech_viseme_owns_serenas_whole_pose(self):
        source, registry_path = self.create_admitted_source()
        hub = WizardFrameHub(
            source,
            allow_scoreless_governed_speech=True,
            character_registry_path=registry_path,
        )
        performance = hub.performance
        package_digest = performance.package_digest
        character_id = performance.character_id
        pending = snapshot_mapping(
            sequence=0,
            media_epoch=4,
            state="paused",
            position_ms=0,
            source_slot="speech",
            kind="tts",
            media_id=MEDIA_ID,
            mode="speech",
            with_hashes=True,
        )
        pending["performance"].update(
            {
                "score_id": None,
                "score_revision": None,
                "score_sha256": None,
                "character_id": character_id,
                "character_package_sha256": package_digest,
            }
        )
        pending_snapshot = MediaSessionSnapshotV1.from_mapping(pending)
        self.assertEqual(
            performance.accept_snapshot(pending_snapshot, 1_000_000).disposition,
            "accepted",
        )
        context = performance.capture_performance_context(
            PerformanceContextRequestV1.from_mapping(context_request_mapping()),
            source.controller,
            1_010_000,
        )
        alignment = alignment_mapping()
        approval_content = {
            "schema_version": 1,
            "approval_id": "approval:serena-turn-0042",
            "turn_id": "turn:0042",
            "reply_sha256": text_digest(),
            "speech_media": {
                "kind": "speech",
                "identity": alignment["speech_id"],
                "sha256": MEDIA_DIGEST,
            },
            "performance_context_sha256": context.context_sha256,
            "character_id": character_id,
            "package_digest": package_digest,
            "allowed_sinks": ["animation", "speech", "text"],
            "issued_at_ms": 1_000,
            "expires_at_ms": 5_000,
            "revocation_generation": 0,
            "reconciliation_generation": (
                context.runtime.reconciliation_generation
            ),
        }
        legacy_approval = GovernedPerformanceApprovalV1.build(approval_content)
        legacy_registration = GovernedSpeechRegistrationV1.from_mapping(
            {
                "schema_version": 1,
                "approved_text": TEXT,
                "approval": legacy_approval.to_dict(),
                "performance_context": context.to_dict(),
                "alignment": alignment,
            }
        )
        with self.assertRaises(GovernedSpeechError) as missing_persona:
            performance.register_governed_speech(
                legacy_registration,
                now_wall_ms=1_100,
                now_monotonic_us=1_020_000,
            )
        self.assertEqual(
            missing_persona.exception.code,
            "missing_persona_identity",
        )

        mismatched_approval = GovernedPerformanceApprovalV1.build(
            {
                **approval_content,
                "persona_id": "persona:other",
                "voice_id": alignment["voice_id"],
            }
        )
        mismatched_registration = GovernedSpeechRegistrationV1.from_mapping(
            {
                "schema_version": 1,
                "approved_text": TEXT,
                "approval": mismatched_approval.to_dict(),
                "performance_context": context.to_dict(),
                "alignment": alignment,
            }
        )
        with self.assertRaises(GovernedSpeechError) as identity_mismatch:
            performance.register_governed_speech(
                mismatched_registration,
                now_wall_ms=1_100,
                now_monotonic_us=1_020_000,
            )
        self.assertEqual(
            identity_mismatch.exception.code,
            "persona_character_binding_mismatch",
        )

        approval = GovernedPerformanceApprovalV1.build(
            {
                **approval_content,
                "persona_id": "serena-quill",
                "voice_id": alignment["voice_id"],
            }
        )
        registration = GovernedSpeechRegistrationV1.from_mapping(
            {
                "schema_version": 1,
                "approved_text": TEXT,
                "approval": approval.to_dict(),
                "performance_context": context.to_dict(),
                "alignment": alignment,
            }
        )
        performance.register_governed_speech(
            registration,
            now_wall_ms=1_100,
            now_monotonic_us=1_020_000,
        )
        playing = dict(pending)
        playing["sequence"] = 1
        playing["cause"] = "playing"
        playing["playback"] = dict(playing["playback"])
        playing["playback"]["state"] = "playing"
        playing_snapshot = MediaSessionSnapshotV1.from_mapping(playing)
        performance.accept_snapshot(playing_snapshot, 1_100_000)

        source.controller.state.pose_override_id = "mentoring_invitation"
        performance._last_applied_pose = "mentoring_invitation"
        result = performance.apply(source.controller, 1_500_000)
        source.resolve_authoritative_animation_state()
        source.controller.advance_tick()
        performance.apply(source.controller, 1_516_667)
        source.resolve_authoritative_animation_state()

        self.assertTrue(result.active)
        self.assertEqual(source.controller.state.speech_id, "speech:turn-0042")
        self.assertEqual(source.controller.state.mouth, "smile")
        self.assertIsNone(source.controller.state.pose_override_id)
        self.assertEqual(
            source.controller.state.pose_id,
            "viseme_smile_speaking",
        )
        self.assertEqual(
            source.controller.state.animation_node_id,
            "node_viseme_smile_speaking",
        )
        self.assertIn(
            "whole_pose_speech_authority",
            source.controller.state.performance_suppression_codes,
        )
        await hub.stop()

    async def test_review_only_serena_cannot_enter_the_governed_pipeline(self):
        source = self.create_source()
        hub = WizardFrameHub(
            source,
            allow_scoreless_governed_speech=True,
        )
        performance = hub.performance
        pending = snapshot_mapping(
            sequence=0,
            media_epoch=4,
            state="paused",
            position_ms=0,
            source_slot="speech",
            kind="tts",
            media_id=MEDIA_ID,
            mode="speech",
            with_hashes=True,
        )
        pending["performance"].update(
            {
                "score_id": None,
                "score_revision": None,
                "score_sha256": None,
                "character_id": performance.character_id,
                "character_package_sha256": performance.package_digest,
            }
        )
        performance.accept_snapshot(
            MediaSessionSnapshotV1.from_mapping(pending),
            1_000_000,
        )

        with self.assertRaises(GovernedSpeechError) as context_denied:
            performance.capture_performance_context(
                PerformanceContextRequestV1.from_mapping(
                    context_request_mapping()
                ),
                source.controller,
                1_010_000,
            )
        with self.assertRaises(GovernedSpeechError) as binding_denied:
            await hub.performance_binding()
        with self.assertRaises(GovernedSpeechError) as compile_denied:
            performance.compile_live_speech_score(None, duration_ms=1)
        with self.assertRaises(GovernedSpeechError) as publish_denied:
            performance.publish_live_speech_score(None)

        for denied in (
            context_denied,
            binding_denied,
            compile_denied,
            publish_denied,
        ):
            self.assertEqual(
                denied.exception.code,
                "character_not_runtime_admitted",
            )
        await hub.stop()


if __name__ == "__main__":
    unittest.main()
