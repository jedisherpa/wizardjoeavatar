import inspect
import json
import unittest
import uuid
from pathlib import Path

from wizard_avatar.prism_signals import (
    PrismAdvisoryStateMachine,
    PrismAnimationSignalV1,
    PrismAnimationSignalV2,
    PrismSignalAdapter,
    PrismSignalParser,
    PrismSignalValidationError,
)
from wizard_avatar.semantic_animation import map_prism_signal


NOW_MS = 1_000_000


def envelope(
    *,
    event_id=None,
    source_epoch="epoch-a",
    source_sequence=1,
    emitted_at_ms=NOW_MS - 10,
    ttl_ms=1_000,
    kind="stage",
    provenance_class="runtime_lifecycle",
    payload=None
):
    return {
        "schema_version": 1,
        "event_id": event_id or str(uuid.uuid4()),
        "source_epoch": source_epoch,
        "source_sequence": source_sequence,
        "emitted_at_ms": emitted_at_ms,
        "ttl_ms": ttl_ms,
        "kind": kind,
        "classification": "visual_advisory_only",
        "provenance_class": provenance_class,
        "sanitization_version": 1,
        "payload": {"stage": "understanding", "status": "active"}
        if payload is None
        else payload,
    }


def envelope_v2(*, turn_id="turn-a", utterance_id=None, **overrides):
    value = envelope(**overrides)
    value["schema_version"] = 2
    value["turn_id"] = turn_id
    if utterance_id is not None:
        value["utterance_id"] = utterance_id
    return value


class PrismAnimationSignalTests(unittest.TestCase):
    def test_valid_signal_is_typed_immutable_and_content_free(self):
        parsed = PrismAnimationSignalV1.from_mapping(envelope())

        self.assertEqual(parsed.producer_epoch, "epoch-a")
        self.assertEqual(parsed.sequence, 1)
        self.assertEqual(parsed.issued_at_ms, NOW_MS - 10)
        self.assertEqual(parsed.expires_at_ms, NOW_MS + 990)
        self.assertEqual(parsed.payload["stage"], "understanding")
        with self.assertRaises(TypeError):
            parsed.payload["stage"] = "ready"

    def test_every_supported_kind_accepts_only_sanitized_payload_shapes(self):
        cases = {
            "stage": {"stage": "drafting", "status": "started"},
            "terminal_posture": {
                "posture": "needs_clarification",
                "confidence_bucket": "medium",
                "serious_mode": True,
            },
            "persona_style": {"style": "measured"},
            "recall_summary": {
                "selected_count_bucket": "2_plus",
                "selected_count": 2,
                "memory_selected": True,
                "backstory_selected": False,
            },
            "retrieval_summary": {
                "result_count_bucket": "1",
                "result_count": 1,
                "occurred": True,
            },
            "approval_posture": {"approval_state": "pending"},
            "continuity": {
                "continuity_state": "restored",
                "age_bucket": "recent",
                "recent_turns_count": 3,
            },
            "topic_shift": {"changed": True, "cause": "semantic"},
            "health": {
                "health_state": "degraded",
                "audit_healthy": False,
                "signal_age_ms": 12,
            },
        }

        for sequence, (kind, payload) in enumerate(cases.items(), 1):
            with self.subTest(kind=kind):
                parsed = PrismAnimationSignalV1.from_mapping(
                    envelope(
                        source_sequence=sequence,
                        kind=kind,
                        provenance_class=(
                            "runtime_health" if kind == "health" else "sanitized_aggregate"
                        ),
                        payload=payload,
                    )
                )
                self.assertEqual(parsed.kind, kind)
                self.assertEqual(dict(parsed.payload), payload)

    def test_unknown_fields_and_free_text_are_rejected(self):
        unsafe_values = (
            {**envelope(), "prompt": "private question"},
            {**envelope(), "authority_claim": "approved"},
            envelope(payload={"stage": "understanding", "status": "active", "note": "hello"}),
            envelope(payload={"stage": "the user asked for a file", "status": "active"}),
            envelope(payload={"stage": "understanding", "status": ["active"]}),
        )

        for value in unsafe_values:
            with self.subTest(value=value):
                with self.assertRaises(PrismSignalValidationError):
                    PrismAnimationSignalV1.from_mapping(value)

    def test_private_content_and_authority_vocabulary_are_forbidden_recursively(self):
        forbidden_keys = (
            "reply",
            "memory_body",
            "embedding_vector",
            "source_path",
            "approval_payload",
            "model_name",
            "authority_level",
            "world_target",
            "locomotion",
            "execute_action",
        )
        for key in forbidden_keys:
            unsafe = envelope()
            unsafe["payload"] = {"stage": "ready", "status": "active", key: "x"}
            with self.subTest(key=key):
                with self.assertRaisesRegex(PrismSignalValidationError, "forbidden"):
                    PrismAnimationSignalV1.from_mapping(unsafe)

    def test_strict_types_versions_bounds_and_identifiers(self):
        mutations = (
            {"schema_version": True},
            {"schema_version": 2},
            {"sanitization_version": 2},
            {"event_id": "not-a-uuid"},
            {"source_epoch": "epoch with prose"},
            {"source_sequence": True},
            {"source_sequence": -1},
            {"emitted_at_ms": 1.5},
            {"ttl_ms": 0},
            {"ttl_ms": 300_001},
            {"classification": "command"},
            {"kind": "movement"},
            {"provenance_class": "user_text"},
        )
        for mutation in mutations:
            value = envelope()
            value.update(mutation)
            with self.subTest(mutation=mutation):
                with self.assertRaises(PrismSignalValidationError):
                    PrismAnimationSignalV1.from_mapping(value)

        with self.assertRaises(PrismSignalValidationError):
            PrismAnimationSignalV1.from_mapping(
                envelope(
                    kind="retrieval_summary",
                    payload={"result_count_bucket": "2_plus", "result_count": 10_001},
                )
            )

    def test_exact_v2_json_is_duplicate_free_and_maps_reviewing(self):
        fixture_path = (
            Path(__file__).parent / "fixtures" / "prism_animation_signal_v2.json"
        )
        parsed = PrismAnimationSignalV2.from_json(fixture_path.read_bytes())
        self.assertEqual(parsed.turn_id, "turn-20260715-0017")
        self.assertEqual(parsed.utterance_id, "utterance-03")

        reviewing = envelope_v2(
            turn_id="turn-review",
            payload={"stage": "reviewing", "status": "active"},
        )
        intent = map_prism_signal(reviewing, now_ms=NOW_MS)
        self.assertTrue(intent.recognized)
        self.assertEqual(intent.cue, "review")
        self.assertEqual(intent.expression, "focused")
        self.assertEqual(intent.gesture, "review")

        serialized = json.dumps(reviewing)
        duplicate = serialized.replace(
            '"turn_id": "turn-review"',
            '"turn_id": "turn-review", "turn_id": "turn-review"',
            1,
        )
        for value in (duplicate, serialized.replace('"ttl_ms": 1000', '"ttl_ms": 1.0')):
            with self.subTest(value=value):
                with self.assertRaises(PrismSignalValidationError):
                    PrismAnimationSignalV2.from_json(value)

    def test_v2_requires_safe_bounded_turn_context(self):
        parsed = PrismAnimationSignalV2.from_mapping(envelope_v2())
        self.assertEqual(parsed.turn_id, "turn-a")
        self.assertIsNone(parsed.utterance_id)
        invalid = (
            {key: value for key, value in envelope_v2().items() if key != "turn_id"},
            envelope_v2(turn_id="turn with prose"),
            envelope_v2(turn_id="t" * 129),
            envelope_v2(utterance_id="utterance with prose"),
            envelope_v2(utterance_id="u" * 129),
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(PrismSignalValidationError):
                    PrismAnimationSignalV2.from_mapping(value)
        with self.assertRaisesRegex(PrismSignalValidationError, "contradicts"):
            PrismAnimationSignalV1.from_mapping(
                envelope(
                    kind="recall_summary",
                    payload={"selected_count_bucket": "0", "selected_count": 2},
                )
            )


class PrismSignalParserTests(unittest.TestCase):
    def test_sequence_is_strictly_monotonic_per_epoch(self):
        parser = PrismSignalParser()
        parser.parse(envelope(source_sequence=7), now_ms=NOW_MS)

        with self.assertRaisesRegex(PrismSignalValidationError, "monotonically"):
            parser.parse(envelope(source_sequence=7), now_ms=NOW_MS)
        with self.assertRaisesRegex(PrismSignalValidationError, "monotonically"):
            parser.parse(envelope(source_sequence=6), now_ms=NOW_MS)

        accepted = parser.parse(envelope(source_sequence=8), now_ms=NOW_MS)
        self.assertEqual(accepted.source_sequence, 8)
        self.assertEqual(parser.last_sequence(), 8)

    def test_new_epoch_resets_sequence_and_old_epoch_cannot_replay(self):
        parser = PrismSignalParser()
        parser.parse(envelope(source_epoch="epoch-a", source_sequence=9), now_ms=NOW_MS)
        parser.parse(envelope(source_epoch="epoch-b", source_sequence=0), now_ms=NOW_MS)

        self.assertEqual(parser.active_epoch, "epoch-b")
        with self.assertRaisesRegex(PrismSignalValidationError, "retired"):
            parser.parse(
                envelope(source_epoch="epoch-a", source_sequence=10), now_ms=NOW_MS
            )

    def test_duplicate_event_ids_are_rejected_even_with_new_sequence(self):
        parser = PrismSignalParser()
        event_id = str(uuid.uuid4())
        parser.parse(envelope(event_id=event_id, source_sequence=1), now_ms=NOW_MS)
        with self.assertRaisesRegex(PrismSignalValidationError, "duplicate"):
            parser.parse(
                envelope(event_id=event_id, source_sequence=2), now_ms=NOW_MS
            )

    def test_expired_and_far_future_events_do_not_advance_watermark(self):
        parser = PrismSignalParser(max_future_skew_ms=20)
        with self.assertRaisesRegex(PrismSignalValidationError, "expired"):
            parser.parse(
                envelope(source_sequence=4, emitted_at_ms=NOW_MS - 100, ttl_ms=100),
                now_ms=NOW_MS,
            )
        with self.assertRaisesRegex(PrismSignalValidationError, "future"):
            parser.parse(
                envelope(source_sequence=4, emitted_at_ms=NOW_MS + 21),
                now_ms=NOW_MS,
            )
        self.assertIsNone(parser.last_sequence())
        parser.parse(envelope(source_sequence=4), now_ms=NOW_MS)
        self.assertEqual(parser.last_sequence(), 4)

    def test_adapter_has_no_network_or_authority_surface(self):
        adapter = PrismSignalAdapter()
        public_names = {name for name in dir(adapter) if not name.startswith("_")}
        self.assertEqual(
            public_names, {"active_epoch", "last_sequence", "parse", "parse_json"}
        )

        source = inspect.getsource(__import__("wizard_avatar.prism_signals", fromlist=["*"]))
        for forbidden_import in ("socket", "urllib", "requests", "httpx", "websocket"):
            self.assertNotIn("import {}".format(forbidden_import), source)


class PrismAdvisoryStateMachineTests(unittest.TestCase):
    def test_expiry_and_matching_terminal_release_exactly_once(self):
        machine = PrismAdvisoryStateMachine()
        machine.accept(
            envelope_v2(emitted_at_ms=NOW_MS, ttl_ms=25), now_ms=NOW_MS
        )
        self.assertEqual(machine.advance(now_ms=NOW_MS + 24).disposition, "retained")
        expired = machine.advance(now_ms=NOW_MS + 25)
        self.assertTrue(expired.released)
        self.assertEqual(expired.release_reason, "expired")
        self.assertEqual(machine.advance(now_ms=NOW_MS + 26).disposition, "inactive")

        machine.accept(
            envelope_v2(
                source_sequence=2,
                turn_id="turn-b",
                utterance_id="utterance-b",
            ),
            now_ms=NOW_MS,
        )
        released = machine.accept(
            envelope_v2(
                source_sequence=3,
                turn_id="turn-b",
                utterance_id="utterance-b",
                payload={"stage": "ready", "status": "completed"},
            ),
            now_ms=NOW_MS,
        )
        self.assertTrue(released.released)
        self.assertEqual(released.release_reason, "completed")

    def test_stale_terminal_cannot_release_a_newer_turn(self):
        machine = PrismAdvisoryStateMachine()
        machine.accept(envelope_v2(source_sequence=1, turn_id="turn-old"), now_ms=NOW_MS)
        machine.accept(envelope_v2(source_sequence=2, turn_id="turn-new"), now_ms=NOW_MS)
        stale = machine.accept(
            envelope_v2(
                source_sequence=3,
                turn_id="turn-old",
                payload={"stage": "ready", "status": "cancelled"},
            ),
            now_ms=NOW_MS,
        )
        self.assertEqual(stale.disposition, "terminal_ignored")
        self.assertEqual(stale.release_reason, "turn_mismatch")
        self.assertEqual(machine.active_signal.turn_id, "turn-new")

    def test_terminal_requires_matching_utterance_and_schema_generation(self):
        machine = PrismAdvisoryStateMachine()
        machine.accept(
            envelope_v2(
                source_sequence=1,
                turn_id="turn-a",
                utterance_id="utterance-new",
            ),
            now_ms=NOW_MS,
        )
        wrong_utterance = machine.accept(
            envelope_v2(
                source_sequence=2,
                turn_id="turn-a",
                utterance_id="utterance-old",
                payload={"stage": "speaking", "status": "failed"},
            ),
            now_ms=NOW_MS,
        )
        self.assertEqual(wrong_utterance.disposition, "terminal_ignored")
        self.assertEqual(wrong_utterance.release_reason, "utterance_mismatch")

        legacy_terminal = machine.accept(
            envelope(
                source_sequence=3,
                payload={"stage": "speaking", "status": "cancelled"},
            ),
            now_ms=NOW_MS,
        )
        self.assertEqual(legacy_terminal.disposition, "terminal_ignored")
        self.assertEqual(legacy_terminal.release_reason, "turn_unbound")
        self.assertEqual(machine.active_signal.turn_id, "turn-a")


class PrismSignalSchemaTests(unittest.TestCase):
    def test_schema_matches_the_closed_python_contract(self):
        schema_path = (
            Path(__file__).parents[2]
            / "wizard_avatar"
            / "definitions"
            / "prism_animation_signal.schema.json"
        )
        with schema_path.open("r", encoding="utf-8") as handle:
            schema = json.load(handle)

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertEqual(
            schema["properties"]["classification"]["const"],
            "visual_advisory_only",
        )
        self.assertEqual(schema["properties"]["sanitization_version"]["const"], 1)
        self.assertEqual(schema["properties"]["ttl_ms"]["maximum"], 300000)
        serialized = json.dumps(schema).lower()
        for forbidden_field in (
            '"authority"',
            '"locomotion"',
            '"movement"',
            '"world_target"',
            '"command"',
            '"prompt"',
            '"reply"',
        ):
            self.assertNotIn(forbidden_field, serialized)

    def test_v2_schema_adds_required_turn_and_optional_utterance(self):
        schema_path = (
            Path(__file__).parents[2]
            / "wizard_avatar"
            / "definitions"
            / "prism_animation_signal_v2.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], 2)
        self.assertIn("turn_id", schema["required"])
        self.assertNotIn("utterance_id", schema["required"])
        self.assertEqual(schema["properties"]["turn_id"]["maxLength"], 128)


if __name__ == "__main__":
    unittest.main()
