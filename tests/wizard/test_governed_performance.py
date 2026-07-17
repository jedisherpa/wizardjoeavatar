import copy
import json
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from wizard_avatar.artifact_hashing import canonical_json_v1, sha256_ref
from wizard_avatar.governed_performance import (
    GOVERNED_PERFORMANCE_MAX_LIFETIME_MS,
    GovernedPerformanceApprovalV1,
    GovernedPerformanceBindingsV1,
    GovernedPerformanceError,
    GovernedPerformanceGate,
    SpeechMediaBindingV1,
    validate_governed_performance_approval,
)


NOW_MS = 1_000_000
ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    ROOT / "wizard_avatar" / "definitions" / "governed_performance_approval_v1.schema.json"
)


def approval_content(**overrides):
    value = {
        "schema_version": 1,
        "approval_id": "approval:turn-0042:v1",
        "turn_id": "turn:0042",
        "reply_sha256": sha256_ref(b"private reply bytes"),
        "speech_media": {
            "kind": "speech",
            "identity": "utterance:0042:1",
            "sha256": sha256_ref(b"private speech bytes"),
        },
        "performance_context_sha256": "sha256:" + "1" * 64,
        "character_id": "wizard-joe",
        "package_digest": "sha256:" + "2" * 64,
        "allowed_sinks": ["animation", "speech", "text"],
        "issued_at_ms": NOW_MS - 100,
        "expires_at_ms": NOW_MS + 10_000,
        "revocation_generation": 4,
        "reconciliation_generation": 7,
    }
    value.update(overrides)
    return value


def approval(**overrides):
    return GovernedPerformanceApprovalV1.build(approval_content(**overrides))


class GovernedPerformanceApprovalTests(unittest.TestCase):
    def assert_code(self, code, value):
        with self.assertRaises(GovernedPerformanceError) as caught:
            GovernedPerformanceApprovalV1.from_mapping(value)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_envelope_is_frozen_deeply_immutable_and_canonical(self):
        item = approval()
        value = item.to_dict()

        self.assertEqual(item.canonical_json(), canonical_json_v1(value))
        self.assertEqual(item.approval_sha256, item.computed_approval_sha256())
        self.assertIsInstance(item.allowed_sinks, tuple)
        self.assertIsInstance(item.speech_media, SpeechMediaBindingV1)
        self.assertNotIn("private reply bytes", item.canonical_json().decode("utf-8"))
        self.assertNotIn("private speech bytes", item.canonical_json().decode("utf-8"))
        with self.assertRaises(FrozenInstanceError):
            item.turn_id = "turn:other"
        with self.assertRaises(FrozenInstanceError):
            item.speech_media.kind = "none"
        self.assertEqual(validate_governed_performance_approval(item.canonical_json()), item)

    def test_hash_is_stable_across_mapping_order_and_seals_every_field(self):
        value = approval_content()
        reordered = {key: value[key] for key in reversed(value)}
        self.assertEqual(approval().approval_sha256, GovernedPerformanceApprovalV1.build(reordered).approval_sha256)

        tampered = approval().to_dict()
        tampered["turn_id"] = "turn:0043"
        self.assert_code("hash_mismatch", tampered)

    def test_unknown_missing_float_duplicate_and_bad_version_fail_closed(self):
        value = approval().to_dict()
        value["unexpected"] = True
        self.assert_code("unknown_field", value)

        value = approval().to_dict()
        value["speech_media"]["unexpected"] = True
        self.assert_code("unknown_field", value)

        value = approval().to_dict()
        value.pop("turn_id")
        self.assert_code("missing_field", value)

        value = approval().to_dict()
        value["reconciliation_generation"] = 7.0
        self.assert_code("non_integer_identity_value", value)

        raw = '{"schema_version":1,"schema_version":1}'
        with self.assertRaises(GovernedPerformanceError) as caught:
            GovernedPerformanceApprovalV1.from_json(raw)
        self.assertEqual(caught.exception.code, "duplicate_json_key")

        value = approval().to_dict()
        value["schema_version"] = 2
        self.assert_code("schema_version_unsupported", value)

    def test_private_raw_content_is_rejected_without_echoing_it(self):
        for field in ("reply_text", "raw_audio_bytes", "transcript", "payload"):
            with self.subTest(field=field):
                value = approval().to_dict()
                value[field] = "private-canary"
                caught = self.assert_code("private_content", value)
                self.assertNotIn("private-canary", str(caught))

        value = approval().to_dict()
        value["unknown-private-canary"] = 1.5
        caught = self.assert_code("non_integer_identity_value", value)
        self.assertNotIn("private-canary", str(caught))

    def test_speech_media_binding_and_sink_set_are_strict(self):
        self.assertEqual(
            approval(speech_media={"kind": "media", "identity": "media:0042", "sha256": None}).speech_media.kind,
            "media",
        )

        for speech_media, code in (
            ({"kind": "speech", "identity": None, "sha256": None}, "missing_speech_media_binding"),
            ({"kind": "none", "identity": "utterance:0042", "sha256": None}, "invalid_speech_media"),
            ({"kind": "other", "identity": None, "sha256": None}, "invalid_speech_media"),
        ):
            with self.subTest(speech_media=speech_media):
                with self.assertRaises(GovernedPerformanceError) as caught:
                    approval(speech_media=speech_media)
                self.assertEqual(caught.exception.code, code)

        for sinks, code in (
            ([], "missing_sink"),
            (["text", "animation"], "invalid_order"),
            (["text", "text"], "invalid_order"),
            (["filesystem"], "invalid_sink"),
        ):
            with self.subTest(sinks=sinks):
                with self.assertRaises(GovernedPerformanceError) as caught:
                    approval(allowed_sinks=sinks)
                self.assertEqual(caught.exception.code, code)

        with self.assertRaises(GovernedPerformanceError) as caught:
            approval(
                allowed_sinks=["speech"],
                speech_media={"kind": "none", "identity": None, "sha256": None},
            )
        self.assertEqual(caught.exception.code, "missing_speech_media_binding")

    def test_time_window_is_positive_and_bounded(self):
        with self.assertRaises(GovernedPerformanceError) as caught:
            approval(issued_at_ms=NOW_MS, expires_at_ms=NOW_MS)
        self.assertEqual(caught.exception.code, "invalid_time_window")

        with self.assertRaises(GovernedPerformanceError) as caught:
            approval(
                issued_at_ms=NOW_MS,
                expires_at_ms=NOW_MS + GOVERNED_PERFORMANCE_MAX_LIFETIME_MS + 1,
            )
        self.assertEqual(caught.exception.code, "approval_lifetime_exceeded")

    def test_schema_is_v1_and_closes_every_object_boundary(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)

        def inspect(node):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIs(node.get("additionalProperties"), False)
                for child in node.values():
                    inspect(child)
            elif isinstance(node, list):
                for child in node:
                    inspect(child)

        inspect(schema)


class GovernedPerformanceGateTests(unittest.TestCase):
    def setUp(self):
        self.approval = approval()
        self.current = GovernedPerformanceBindingsV1.from_approval(self.approval)
        self.gate = GovernedPerformanceGate()

    def assert_gate_code(self, code, *, item=None, sink="text", current=None, now_ms=NOW_MS):
        with self.assertRaises(GovernedPerformanceError) as caught:
            self.gate.authorize(
                item or self.approval,
                sink,
                current or self.current,
                now_ms,
            )
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_each_approved_sink_is_released_once(self):
        for sink in ("text", "speech", "animation"):
            release = self.gate.authorize(self.approval, sink, self.current, NOW_MS)
            self.assertEqual(release.sink, sink)
            self.assertEqual(release.turn_id, self.approval.turn_id)
            self.assertEqual(release.approval_sha256, self.approval.approval_sha256)

        for sink in ("text", "speech", "animation"):
            with self.subTest(sink=sink):
                self.assert_gate_code("replay_detected", sink=sink)
        self.assertEqual(self.gate.replay_approval_count, 1)

    def test_missing_unknown_and_unapproved_sinks_fail(self):
        item = approval(allowed_sinks=["text"])
        current = GovernedPerformanceBindingsV1.from_approval(item)
        for sink, code in ((None, "missing_sink"), ("filesystem", "invalid_sink"), ("speech", "sink_not_approved")):
            with self.subTest(sink=sink):
                self.assert_gate_code(code, item=item, sink=sink, current=current)

    def test_every_live_binding_mismatch_has_a_stable_code(self):
        replacements = {
            "turn_id": ("turn:other", "turn_mismatch"),
            "reply_sha256": ("sha256:" + "a" * 64, "content_mismatch"),
            "speech_media": (SpeechMediaBindingV1("speech", "utterance:other", None), "speech_media_mismatch"),
            "performance_context_sha256": ("sha256:" + "b" * 64, "context_mismatch"),
            "character_id": ("other-character", "character_mismatch"),
            "package_digest": ("sha256:" + "c" * 64, "package_mismatch"),
            "reconciliation_generation": (8, "reconciliation_generation_mismatch"),
            "revocation_generation": (3, "revocation_generation_mismatch"),
        }
        for field, (value, code) in replacements.items():
            with self.subTest(field=field):
                self.assert_gate_code(code, current=replace(self.current, **{field: value}))

        self.assert_gate_code("approval_revoked", current=replace(self.current, revocation_generation=5))

    def test_future_stale_and_expired_approvals_fail(self):
        self.assert_gate_code("approval_not_yet_valid", now_ms=self.approval.issued_at_ms - 1)
        self.assert_gate_code("approval_expired", now_ms=self.approval.expires_at_ms)

    def test_conflicting_envelope_with_reused_id_fails_as_replay(self):
        self.gate.authorize(self.approval, "text", self.current, NOW_MS)
        conflict = approval(
            reply_sha256="sha256:" + "d" * 64,
            allowed_sinks=["speech"],
        )
        current = GovernedPerformanceBindingsV1.from_approval(conflict)
        self.assert_gate_code("replay_conflict", item=conflict, sink="speech", current=current)

    def test_gate_revalidates_frozen_instances_and_does_not_log_forged_content(self):
        forged = replace(self.approval, approval_sha256="private-canary")
        self.assert_gate_code("invalid_hash", item=forged)
        self.assertNotIn("private-canary", repr(self.gate.events))

        forged = replace(self.approval, approval_sha256="sha256:" + "f" * 64)
        self.assert_gate_code("hash_mismatch", item=forged)

    def test_bounded_replay_table_fails_closed_then_prunes_expired_records(self):
        gate = GovernedPerformanceGate(max_replay_approvals=1)
        first = approval(approval_id="approval:first", expires_at_ms=NOW_MS + 100)
        gate.authorize(first, "text", GovernedPerformanceBindingsV1.from_approval(first), NOW_MS)

        second = approval(approval_id="approval:second", issued_at_ms=NOW_MS, expires_at_ms=NOW_MS + 200)
        with self.assertRaises(GovernedPerformanceError) as caught:
            gate.authorize(second, "text", GovernedPerformanceBindingsV1.from_approval(second), NOW_MS)
        self.assertEqual(caught.exception.code, "replay_capacity_exceeded")

        release = gate.authorize(
            second,
            "text",
            GovernedPerformanceBindingsV1.from_approval(second),
            NOW_MS + 100,
        )
        self.assertEqual(release.approval_id, "approval:second")
        self.assertEqual(gate.replay_approval_count, 1)

    def test_event_retention_is_bounded_and_content_free(self):
        gate = GovernedPerformanceGate(max_events=2)
        gate.authorize(self.approval, "text", self.current, NOW_MS)
        for sink in ("text", "filesystem"):
            with self.assertRaises(GovernedPerformanceError):
                gate.authorize(self.approval, sink, self.current, NOW_MS)

        self.assertEqual(gate.total_event_count, 3)
        self.assertEqual(gate.evicted_event_count, 1)
        self.assertEqual(len(gate.events), 2)
        encoded = repr(gate.events)
        self.assertNotIn("private reply bytes", encoded)
        self.assertNotIn("private speech bytes", encoded)
        self.assertEqual([event.code for event in gate.events], ["replay_detected", "invalid_sink"])


if __name__ == "__main__":
    unittest.main()
