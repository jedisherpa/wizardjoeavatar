from __future__ import annotations

import unittest

from wizard_avatar.semantic_animation import (
    AnimationIntent,
    arbitrate_animation_intents,
    load_semantic_animation_map,
    map_signal_to_animation_intent,
)


class SemanticAnimationMappingTests(unittest.TestCase):
    def signal(self, kind, **values):
        signal = {
            "schema_version": 1,
            "classification": "visual_advisory_only",
            "kind": kind,
        }
        signal.update(values)
        return signal

    def test_configuration_has_every_bounded_public_cue(self):
        config = load_semantic_animation_map()
        expected = {
            "none",
            "listen",
            "think",
            "speak",
            "review",
            "clarify",
            "wait",
            "recall",
            "reference",
            "topic_reset",
            "degraded",
            "persona_style",
        }
        self.assertEqual(expected, set(config["profiles"]))
        for profile in config["profiles"].values():
            self.assertGreaterEqual(profile["amplitude"], 0.0)
            self.assertLessEqual(profile["amplitude"], 1.0)
            self.assertGreaterEqual(profile["mouth_activity"], 0.0)
            self.assertLessEqual(profile["mouth_activity"], 1.0)

    def test_stage_lifecycle_maps_to_expected_cues(self):
        expected = {
            "queued": "listen",
            "understanding": "listen",
            "drafting": "think",
            "checking_safety": "review",
            "auditing": "review",
            "reviewing": "review",
            "ready": "speak",
            "needs_clarification": "clarify",
            "waiting_approval": "wait",
        }
        for stage, cue in expected.items():
            with self.subTest(stage=stage):
                intent = map_signal_to_animation_intent(
                    self.signal("stage", stage=stage)
                )
                self.assertTrue(intent.recognized)
                self.assertEqual(cue, intent.cue)
                self.assertTrue(intent.preserve_locomotion)

    def test_direct_safe_signal_kinds_map_without_content(self):
        expected = {
            "listen": "listen",
            "think": "think",
            "speak": "speak",
            "review": "review",
            "clarify": "clarify",
            "wait": "wait",
            "recall_summary": "recall",
            "retrieval_summary": "reference",
            "topic_shift": "topic_reset",
            "degraded": "degraded",
        }
        for kind, cue in expected.items():
            with self.subTest(kind=kind):
                self.assertEqual(
                    cue, map_signal_to_animation_intent(self.signal(kind)).cue
                )

    def test_terminal_continuity_health_and_approval_enums_are_structural(self):
        cases = (
            (self.signal("terminal_posture", posture="needs_clarification"), "clarify"),
            (self.signal("continuity", continuity="restored"), "recall"),
            (self.signal("health", status="degraded"), "degraded"),
            (self.signal("approval_posture", posture="pending"), "wait"),
        )
        for signal, cue in cases:
            with self.subTest(kind=signal["kind"]):
                intent = map_signal_to_animation_intent(signal)
                self.assertEqual(cue, intent.cue)
                if signal["kind"] == "approval_posture":
                    self.assertIn("approval", intent.clamps)
                    self.assertEqual(100, intent.priority)

    def test_unknown_malformed_and_stale_inputs_are_neutral_noops(self):
        cases = (
            self.signal("unknown"),
            self.signal("stage", stage="invented"),
            self.signal("stage", stage="queued", stale=True),
            self.signal("stage", stage="queued", emitted_at_ms=100, ttl_ms=20),
            self.signal("stage", stage="queued", ttl_ms=0, emitted_at_ms=100),
            {"kind": "stage", "stage": "queued", "classification": "command"},
            {"schema_version": 2, "kind": "stage", "stage": "queued"},
        )
        for signal in cases:
            with self.subTest(signal=signal):
                intent = map_signal_to_animation_intent(signal, now_ms=121)
                self.assertTrue(intent.is_noop)
                self.assertEqual("none", intent.cue)
                self.assertEqual(0.0, intent.amplitude)
                self.assertEqual("unknown", intent.source_kind)

    def test_private_or_nested_content_fails_closed(self):
        forbidden = (
            {"prompt": "private"},
            {"memory_body": "private"},
            {"embedding": [0.1, 0.2]},
            {"authority_claim": "expert"},
            {"provider_name": "private"},
            {"extra": {"text": "private"}},
        )
        for extra in forbidden:
            signal = self.signal("speak", **extra)
            with self.subTest(extra=extra):
                self.assertTrue(map_signal_to_animation_intent(signal).is_noop)

    def test_safety_seriousness_and_degraded_health_only_reduce_motion(self):
        base = map_signal_to_animation_intent(self.signal("speak"))
        safety = map_signal_to_animation_intent(
            self.signal("speak", safety_posture="review")
        )
        serious = map_signal_to_animation_intent(
            self.signal("speak", risk_level="high")
        )
        degraded = map_signal_to_animation_intent(
            self.signal("speak", health_status="degraded")
        )
        self.assertLess(safety.amplitude, base.amplitude)
        self.assertLess(serious.amplitude, base.amplitude)
        self.assertLess(degraded.amplitude, base.amplitude)
        self.assertFalse(safety.allow_flourish)
        self.assertFalse(serious.allow_flourish)
        self.assertFalse(degraded.allow_flourish)
        self.assertEqual("degraded", degraded.cue)
        self.assertEqual(0.0, degraded.mouth_activity)

    def test_approval_and_blocked_safety_can_only_produce_waiting(self):
        for clamp in (
            {"approval_state": "pending"},
            {"approval_state": "denied"},
            {"safety_posture": "blocked"},
            {"safety_posture": "invariant_hit"},
        ):
            intent = map_signal_to_animation_intent(self.signal("speak", **clamp))
            with self.subTest(clamp=clamp):
                self.assertEqual("wait", intent.cue)
                self.assertTrue(intent.hold)
                self.assertFalse(intent.allow_flourish)
                self.assertLessEqual(intent.amplitude, 0.18)
                self.assertNotIn("execute", intent.as_dict())
                self.assertNotIn("approval", intent.as_dict())

    def test_authority_is_not_part_of_the_intent_protocol(self):
        fields = set(AnimationIntent.__dataclass_fields__)
        self.assertNotIn("authority", fields)
        self.assertNotIn("confidence", fields)
        self.assertNotIn("execute", fields)
        self.assertNotIn("locomotion", fields)

    def test_user_locomotion_is_never_displaced(self):
        moving = map_signal_to_animation_intent(
            self.signal("stage", stage="drafting"),
            user_locomotion_active=True,
        )
        stationary = map_signal_to_animation_intent(
            self.signal("stage", stage="drafting"),
            user_locomotion_active=False,
        )
        self.assertEqual(moving, stationary)
        self.assertTrue(moving.preserve_locomotion)

    def test_persona_style_is_allowlisted_and_bounded(self):
        playful = map_signal_to_animation_intent(
            self.signal("persona_style", style="playful")
        )
        unknown = map_signal_to_animation_intent(
            self.signal("persona_style", style="all_powerful")
        )
        self.assertTrue(playful.recognized)
        self.assertEqual("playful", playful.persona_style)
        self.assertEqual("none", playful.gesture)
        self.assertLessEqual(playful.amplitude, 1.0)
        self.assertTrue(unknown.is_noop)

    def test_arbitration_obeys_priority_and_composes_restrictive_clamps(self):
        speak = map_signal_to_animation_intent(self.signal("speak"))
        listen = map_signal_to_animation_intent(self.signal("listen"))
        safety = map_signal_to_animation_intent(
            self.signal("review", safety_posture="review")
        )
        result = arbitrate_animation_intents(
            [listen, speak, safety], user_locomotion_active=True
        )
        self.assertEqual("review", result.cue)
        self.assertLessEqual(result.amplitude, 0.18)
        self.assertFalse(result.allow_flourish)
        self.assertTrue(result.preserve_locomotion)

    def test_arbitration_applies_style_without_changing_the_selected_cue(self):
        speak = map_signal_to_animation_intent(self.signal("speak"))
        style = map_signal_to_animation_intent(
            self.signal("persona_style", style="measured")
        )
        result = arbitrate_animation_intents([style, speak])
        self.assertEqual("speak", result.cue)
        self.assertEqual("measured", result.persona_style)
        self.assertLess(result.amplitude, speak.amplitude)
        self.assertLess(result.tempo, speak.tempo)


if __name__ == "__main__":
    unittest.main()
