import hashlib
import json
import unittest
from copy import deepcopy

from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.governed_performance import GovernedPerformanceApprovalV1
from wizard_avatar.media_session import MediaSessionSnapshotV1
from wizard_avatar.performance_application import PerformanceApplication
from wizard_avatar.performance_context import PerformanceContextV1
from wizard_avatar.performance_release import (
    GovernedSpeechError,
    GovernedSpeechRegistrationV1,
    PerformanceContextRequestV1,
)
from wizard_avatar.voice_alignment import VoiceAlignmentV1

from tests.wizard.test_media_session import snapshot_mapping


TEXT = "Hello quiet world."
PACKAGE_DIGEST = "sha256:" + "a" * 64
MANIFEST_DIGEST = "sha256:" + "b" * 64
MEDIA_DIGEST = "sha256:" + "2" * 64
MEDIA_ID = "media:sha256:" + "2" * 64


def text_digest(text=TEXT):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def speech_snapshot(
    sequence=0,
    state="paused",
    position_ms=0,
    media_epoch=4,
    **overrides,
):
    value = snapshot_mapping(
        sequence=sequence,
        media_epoch=media_epoch,
        cause=overrides.pop("cause", "initial" if sequence == 0 else state),
        state=state,
        position_ms=position_ms,
        source_slot="speech",
        kind="tts",
        media_id=MEDIA_ID,
        mode="speech",
        with_hashes=True,
    )
    for section, changes in overrides.items():
        value[section].update(changes)
    value["performance"]["score_id"] = None
    value["performance"]["score_revision"] = None
    value["performance"]["score_sha256"] = None
    value["performance"]["character_package_sha256"] = PACKAGE_DIGEST
    return MediaSessionSnapshotV1.from_mapping(value)


def context_request_mapping():
    return {
        "schema_version": 1,
        "turn_id": "turn:0042",
        "utterance_id": "utterance:0042:1",
        "media_id": MEDIA_ID,
        "reply_sha256": text_digest(),
        "intent": "explain",
        "tone": "warm",
        "sensitivity": "ordinary",
        "urgency": "normal",
        "relational_stance": "collaborative",
        "pending_action_posture": "none",
        "display_profile": "desktop",
    }


def alignment_mapping():
    return {
        "schema_version": 1,
        "alignment_id": "alignment:turn-0042-v1",
        "approved_content_sha256": text_digest(),
        "approved_text_length": len(TEXT),
        "media_id": MEDIA_ID,
        "media_sha256": MEDIA_DIGEST,
        "speech_id": "speech:turn-0042",
        "voice_id": "voice:wizard-joe-v1",
        "duration_ms": 10000,
        "word_spans": [
            {"start_ms": 0, "end_ms": 900, "start_char": 0, "end_char": 5},
            {"start_ms": 900, "end_ms": 1900, "start_char": 6, "end_char": 11},
            {"start_ms": 1900, "end_ms": 3000, "start_char": 12, "end_char": 18},
        ],
        "character_spans": [],
        "phoneme_spans": [
            {"start_ms": 0, "end_ms": 900, "phoneme_class": "e"},
            {"start_ms": 900, "end_ms": 1900, "phoneme_class": "o"},
            {"start_ms": 1900, "end_ms": 3000, "phoneme_class": "a"},
        ],
    }


class GovernedSpeechReleaseTests(unittest.TestCase):
    def setUp(self):
        self.application = PerformanceApplication(
            "runtime:test:0001",
            character_id="wizard-joe",
            package_digest=PACKAGE_DIGEST,
            manifest_digest=MANIFEST_DIGEST,
        )
        self.controller = WizardAvatarController(("front_idle",), "wizard-joe")
        self.application.accept_snapshot(speech_snapshot(), 1_000_000)
        self.context = self.application.capture_performance_context(
            PerformanceContextRequestV1.from_mapping(context_request_mapping()),
            self.controller,
            1_010_000,
        )

    def registration(
        self,
        text=TEXT,
        *,
        context=None,
        alignment=None,
        approval_overrides=None,
    ):
        context = context or self.context
        alignment = deepcopy(alignment or alignment_mapping())
        approval_content = {
            "schema_version": 1,
            "approval_id": "approval:turn-0042",
            "turn_id": "turn:0042",
            "reply_sha256": text_digest(text),
            "speech_media": {
                "kind": "speech",
                "identity": "speech:turn-0042",
                "sha256": MEDIA_DIGEST,
            },
            "performance_context_sha256": context.context_sha256,
            "character_id": "wizard-joe",
            "package_digest": PACKAGE_DIGEST,
            "allowed_sinks": ["animation", "speech", "text"],
            "issued_at_ms": 1_000,
            "expires_at_ms": 5_000,
            "revocation_generation": 0,
            "reconciliation_generation": context.runtime.reconciliation_generation,
        }
        approval_content.update(approval_overrides or {})
        approval = GovernedPerformanceApprovalV1.build(
            approval_content
        )
        return GovernedSpeechRegistrationV1.from_mapping(
            {
                "schema_version": 1,
                "approved_text": text,
                "approval": approval.to_dict(),
                "performance_context": context.to_dict(),
                "alignment": alignment,
            }
        )

    def context_with(self, **sections):
        value = self.context.content_dict()
        for section, changes in sections.items():
            value[section].update(changes)
        return PerformanceContextV1.build(value)

    def assert_registration_code(self, expected, registration, now_wall_ms=1_100):
        with self.assertRaises(GovernedSpeechError) as caught:
            self.application.register_governed_speech(
                registration,
                now_wall_ms=now_wall_ms,
                now_monotonic_us=1_020_000,
            )
        self.assertEqual(caught.exception.code, expected)

    def test_approved_text_mouth_and_body_share_authoritative_media_time(self):
        self.application.register_governed_speech(
            self.registration(),
            now_wall_ms=1_100,
            now_monotonic_us=1_020_000,
        )
        self.application.accept_snapshot(speech_snapshot(1, "playing", 0), 1_100_000)

        result = self.application.apply(self.controller, 1_500_000)

        self.assertTrue(result.active)
        self.assertEqual(result.media_time_ms, 400)
        self.assertEqual(self.controller.state.speech_text, "Hello")
        self.assertEqual(self.controller.state.speech_id, "speech:turn-0042")
        self.assertEqual(self.controller.state.mouth, "smile")
        self.assertIn(self.controller.state.action, {"speaking", "explaining"})

    def test_pause_seek_and_replay_reproject_text_and_mouth_from_media_time(self):
        self.application.register_governed_speech(
            self.registration(),
            now_wall_ms=1_100,
            now_monotonic_us=1_020_000,
        )
        self.application.accept_snapshot(speech_snapshot(1, "playing", 0), 1_100_000)
        first = self.application.apply(self.controller, 1_500_000)
        self.assertEqual(
            (first.media_time_ms, self.controller.state.speech_text, self.controller.state.mouth),
            (400, "Hello", "smile"),
        )

        self.application.accept_snapshot(
            speech_snapshot(2, "paused", 400, cause="pause"),
            1_500_000,
        )
        paused = self.application.apply(self.controller, 2_000_000)
        self.assertFalse(paused.active)
        self.assertIsNone(self.controller.state.speech_text)
        self.assertNotEqual(self.controller.state.mouth, "smile")

        self.application.accept_snapshot(
            speech_snapshot(3, "playing", 2_000, cause="seeked"),
            2_100_000,
        )
        seeked = self.application.apply(self.controller, 2_100_000)
        self.assertEqual(
            (seeked.media_time_ms, self.controller.state.speech_text, self.controller.state.mouth),
            (2_000, TEXT, "open_wide"),
        )

        self.application.accept_snapshot(
            speech_snapshot(4, "playing", 400, cause="seeked"),
            2_600_000,
        )
        replayed = self.application.apply(self.controller, 2_600_000)
        self.assertEqual(
            (
                replayed.media_time_ms,
                self.controller.state.speech_text,
                self.controller.state.mouth,
            ),
            (400, "Hello", "smile"),
        )

    def test_unapproved_speech_is_audible_clock_only_and_cannot_animate(self):
        self.application.accept_snapshot(speech_snapshot(1, "playing", 0), 1_100_000)
        self.controller.state.mouth = "open_wide"

        result = self.application.apply(self.controller, 1_500_000)

        self.assertTrue(result.active)
        self.assertEqual(result.mouth, "closed")
        self.assertIsNone(self.controller.state.speech_text)
        self.assertIsNone(self.controller.state.speech_id)
        self.assertNotIn(self.controller.state.action, {"speaking", "explaining"})

    def test_content_tampering_and_replay_fail_closed(self):
        registration = self.registration()
        self.application.register_governed_speech(
            registration,
            now_wall_ms=1_100,
            now_monotonic_us=1_020_000,
        )
        with self.assertRaises(GovernedSpeechError) as replay:
            self.application.register_governed_speech(
                registration,
                now_wall_ms=1_101,
                now_monotonic_us=1_021_000,
            )
        self.assertEqual(replay.exception.code, "replay_detected")

        tampered = registration.to_dict()
        tampered["approved_text"] = TEXT + "x"
        parsed = GovernedSpeechRegistrationV1.from_mapping(tampered)
        self.assert_registration_code("content_mismatch", parsed, 1_200)

    def test_runtime_rejects_each_sealed_binding_mismatch(self):
        other_digest = "sha256:" + "c" * 64
        cases = (
            (
                "runtime_epoch_mismatch",
                self.registration(
                    context=self.context_with(
                        runtime={"wizard_runtime_epoch": "runtime:test:other"}
                    )
                ),
            ),
            (
                "reconciliation_generation_mismatch",
                self.registration(
                    context=self.context_with(
                        runtime={
                            "reconciliation_generation": (
                                self.context.runtime.reconciliation_generation + 1
                            )
                        }
                    )
                ),
            ),
            (
                "connector_session_mismatch",
                self.registration(
                    context=self.context_with(
                        source={
                            "connector_session_id": "00000000-0000-4000-8000-000000000003"
                        }
                    )
                ),
            ),
            (
                "sequence_mismatch",
                self.registration(
                    context=self.context_with(source={"accepted_sequence": 1})
                ),
            ),
            (
                "media_epoch_mismatch",
                self.registration(
                    context=self.context_with(source={"media_epoch": 5})
                ),
            ),
            (
                "source_slot_mismatch",
                self.registration(
                    context=self.context_with(source={"source_slot": "main"})
                ),
            ),
            (
                "turn_mismatch",
                self.registration(
                    context=self.context_with(source={"turn_id": "turn:other"})
                ),
            ),
            (
                "character_mismatch",
                self.registration(
                    context=self.context_with(character={"character_id": "wizard-other"})
                ),
            ),
            (
                "package_mismatch",
                self.registration(
                    context=self.context_with(
                        character={"package_digest": other_digest},
                        evidence={"package_digest": other_digest},
                    )
                ),
            ),
        )
        for expected, registration in cases:
            with self.subTest(expected=expected):
                self.assert_registration_code(expected, registration)

    def test_approval_content_alignment_and_hash_bindings_fail_closed(self):
        cases = (
            (
                "context_mismatch",
                self.registration(
                    approval_overrides={"performance_context_sha256": "sha256:" + "c" * 64}
                ),
            ),
            (
                "presentation_not_approved",
                self.registration(
                    context=self.context_with(
                        approval={
                            "presentation_state": "denied",
                            "presentation_artifact_sha256": None,
                        }
                    )
                ),
            ),
            (
                "content_mismatch",
                self.registration(
                    approval_overrides={"reply_sha256": text_digest(TEXT + "x")}
                ),
            ),
            (
                "speech_media_mismatch",
                self.registration(
                    approval_overrides={
                        "speech_media": {
                            "kind": "speech",
                            "identity": "speech:other",
                            "sha256": MEDIA_DIGEST,
                        }
                    }
                ),
            ),
            (
                "sink_not_approved",
                self.registration(approval_overrides={"allowed_sinks": ["speech", "text"]}),
            ),
            (
                "text_length_mismatch",
                self.registration(
                    alignment={**alignment_mapping(), "approved_text_length": len(TEXT) + 1}
                ),
            ),
            (
                "duration_mismatch",
                self.registration(
                    alignment={**alignment_mapping(), "duration_ms": 9_999}
                ),
            ),
        )
        for expected, registration in cases:
            with self.subTest(expected=expected):
                self.assert_registration_code(expected, registration)

        raw = self.registration().to_dict()
        raw["approval"]["turn_id"] = "turn:forged"
        with self.assertRaises(GovernedSpeechError) as forged:
            GovernedSpeechRegistrationV1.from_mapping(raw)
        self.assertEqual(forged.exception.code, "hash_mismatch")

    def test_live_binding_change_clears_an_active_release(self):
        self.application.register_governed_speech(
            self.registration(),
            now_wall_ms=1_100,
            now_monotonic_us=1_020_000,
        )
        self.application.accept_snapshot(speech_snapshot(1, "playing", 0), 1_100_000)
        self.application.apply(self.controller, 1_500_000)
        self.assertEqual(self.controller.state.speech_text, "Hello")

        self.application.accept_snapshot(
            speech_snapshot(
                2,
                "playing",
                500,
                media_epoch=5,
                cause="trackchange",
            ),
            1_600_000,
        )
        changed = self.application.apply(self.controller, 1_600_000)
        self.assertTrue(changed.active)
        self.assertIsNone(self.controller.state.speech_text)
        self.assertEqual(self.controller.state.mouth, "closed")
        self.assertEqual(
            self.application.governed_speech.diagnostics()["status"],
            "binding_changed",
        )

    def test_revocation_and_exact_expiry_release_owned_state(self):
        self.application.register_governed_speech(
            self.registration(),
            now_wall_ms=1_100,
            now_monotonic_us=1_020_000,
        )
        self.application.accept_snapshot(speech_snapshot(1, "playing", 0), 1_100_000)
        self.application.apply(self.controller, 1_500_000)
        self.assertEqual(self.controller.state.speech_text, "Hello")

        self.application.accept_snapshot(
            speech_snapshot(2, "playing", 3_700, cause="heartbeat"),
            4_800_000,
        )
        before_expiry = self.application.apply(self.controller, 4_919_999)
        self.assertTrue(before_expiry.active)
        self.assertTrue(self.application.governed_speech.diagnostics()["active"])
        at_expiry = self.application.apply(self.controller, 4_920_000)
        self.assertTrue(at_expiry.active)
        self.assertIsNone(self.controller.state.speech_text)
        self.assertEqual(self.controller.state.mouth, "closed")
        self.assertEqual(
            self.application.governed_speech.diagnostics()["status"],
            "approval_expired",
        )

        fresh = PerformanceApplication(
            "runtime:test:0001",
            character_id="wizard-joe",
            package_digest=PACKAGE_DIGEST,
            manifest_digest=MANIFEST_DIGEST,
        )
        fresh.accept_snapshot(speech_snapshot(), 1_000_000)
        fresh.register_governed_speech(
            self.registration(),
            now_wall_ms=1_100,
            now_monotonic_us=1_020_000,
        )
        fresh.accept_snapshot(speech_snapshot(1, "playing", 0), 1_100_000)
        fresh.apply(self.controller, 1_500_000)
        governed_mouth = self.controller.state.mouth
        self.controller.state.facing = "north"
        self.controller.state.world_position = {"x": 2.25, "y": 0.0, "z": 7.5}
        position_before_revoke = dict(self.controller.state.world_position)
        fresh.revoke_governed_speech(1, self.controller)
        self.assertIsNone(self.controller.state.speech_text)
        self.assertNotEqual(self.controller.state.mouth, governed_mouth)
        self.assertEqual(self.controller.state.expression, "neutral")
        self.assertEqual(self.controller.state.facing, "south")
        self.assertEqual(self.controller.state.world_position, position_before_revoke)
        self.assertEqual(fresh.governed_speech.diagnostics()["status"], "approval_revoked")
        with self.assertRaises(GovernedSpeechError) as stale:
            fresh.revoke_governed_speech(1, self.controller)
        self.assertEqual(stale.exception.code, "revocation_generation_stale")

    def test_revocation_does_not_reorient_an_active_human_control_lease(self):
        self.application.register_governed_speech(
            self.registration(),
            now_wall_ms=1_100,
            now_monotonic_us=1_020_000,
        )
        self.application.accept_snapshot(speech_snapshot(1, "playing", 0), 1_100_000)
        self.application.apply(self.controller, 1_500_000)
        self.controller.state.facing = "north"
        control = type(
            "Command",
            (),
            {
                "type": "control",
                "payload": {
                    "source_kind": "keyboard",
                    "source_id": "interruption-test",
                    "source_sequence": 1,
                    "source_epoch": "interruption-test:v1",
                    "lease_id": "manual-interruption-test",
                    "ttl_ms": 1000,
                    "intent": {"move_x": 1.0, "move_z": 0.0},
                },
            },
        )()
        self.assertTrue(self.controller.apply_command(control).ok)

        self.application.revoke_governed_speech(1, self.controller)

        self.assertEqual(self.controller.state.facing, "north")
        self.assertEqual(self.controller.state.control_lease_id, "manual-interruption-test")
        self.assertIsNone(self.controller.state.speech_text)

    def test_registration_rejects_not_yet_valid_and_expired_approval(self):
        self.assert_registration_code(
            "approval_not_yet_valid",
            self.registration(),
            now_wall_ms=999,
        )
        self.assert_registration_code(
            "approval_expired",
            self.registration(),
            now_wall_ms=5_000,
        )

    def test_strict_json_rejects_duplicate_keys_floats_and_unknown_fields(self):
        with self.assertRaises(GovernedSpeechError) as duplicate:
            PerformanceContextRequestV1.from_json(
                b'{"schema_version":1,"schema_version":1}'
            )
        self.assertEqual(duplicate.exception.code, "duplicate_json_key")

        value = context_request_mapping()
        value["urgency"] = 1.5
        with self.assertRaises(GovernedSpeechError) as floating:
            PerformanceContextRequestV1.from_json(json.dumps(value).encode("utf-8"))
        self.assertEqual(floating.exception.code, "non_integer_number")

        value = context_request_mapping()
        value["raw_text"] = "private-canary"
        with self.assertRaises(GovernedSpeechError) as unknown:
            PerformanceContextRequestV1.from_mapping(value)
        self.assertEqual(unknown.exception.code, "schema_invalid")
        self.assertNotIn("private-canary", str(unknown.exception))


if __name__ == "__main__":
    unittest.main()
