import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand


def run_seconds(source, seconds):
    source.advance_simulation(seconds)
    source.render_current_frame()


def run_ticks(source, ticks):
    for _ in range(ticks):
        source.advance_simulation(1 / 60)
    source.render_current_frame()


class AnimationChannelTests(unittest.TestCase):
    def test_speech_does_not_cancel_locomotion(self):
        source = ProceduralWizardFrameSource()
        self.assertTrue(
            source.apply_command_sync(WizardCommand("move", {"x": 1.5, "z": 5.0})).ok
        )
        run_seconds(source, 0.5)
        self.assertEqual(source.current_state().locomotion, "walking")

        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("speak", {"text": "Still walking.", "duration_ms": 300})
            ).ok
        )
        state = source.current_state()
        self.assertEqual(state.locomotion, "walking")
        self.assertIsNotNone(state.speech_id)

        run_seconds(source, 0.5)
        state = source.current_state()
        self.assertIsNone(state.speech_id)
        self.assertEqual(state.locomotion, "walking")
        self.assertNotEqual(state.mouth, "open_small")

    def test_speech_before_cast_commit_cancels_cast_without_replay(self):
        source = ProceduralWizardFrameSource()
        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("action", {"action": "magic_cast", "duration_ms": 5000})
            ).ok
        )
        run_ticks(source, 1)
        before = source.current_state()
        self.assertEqual(before.action, "magic_cast")
        self.assertEqual(before.staff_state, "cast")
        self.assertEqual(before.animation_clip_id, "cast_front")

        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("speak", {"text": "A spell within a spell.", "duration_ms": 300})
            ).ok
        )
        during = source.current_state()
        self.assertEqual(during.action, "speaking")
        self.assertEqual(during.staff_state, "held")
        self.assertEqual(during.animation_clip_id, "idle_front")
        self.assertIsNotNone(during.speech_id)

        run_seconds(source, 0.4)
        after_speech = source.current_state()
        self.assertIsNone(after_speech.speech_id)
        self.assertEqual(after_speech.action, "idle")
        self.assertEqual(after_speech.staff_state, "held")
        self.assertEqual(after_speech.animation_clip_id, "idle_front")

    def test_speech_at_commit_waits_for_cast_recovery(self):
        source = ProceduralWizardFrameSource()
        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("action", {"action": "magic_cast", "duration_ms": 5000})
            ).ok
        )
        run_ticks(source, 16)
        self.assertEqual(source.current_state().animation_clip_tick, 15)

        self.assertTrue(
            source.apply_command_sync(
                WizardCommand(
                    "speak",
                    {
                        "text": "The committed spell resolves first.",
                        "duration_ms": 300,
                        "speech_id": "queued-after-commit",
                    },
                )
            ).ok
        )
        committed = source.current_state()
        self.assertEqual(committed.action, "magic_cast")
        self.assertIsNone(committed.speech_id)

        run_ticks(source, 28)
        recovering = source.current_state()
        self.assertEqual(recovering.action, "magic_cast")
        self.assertIsNone(recovering.speech_id)
        self.assertIn("action_settled", recovering.animation_active_markers)

        run_ticks(source, 7)
        speaking = source.current_state()
        self.assertEqual(speaking.action, "speaking")
        self.assertEqual(speaking.staff_state, "held")
        self.assertEqual(speaking.speech_id, "queued-after-commit")

        run_seconds(source, 0.4)
        settled = source.current_state()
        self.assertIsNone(settled.speech_id)
        self.assertEqual(settled.action, "idle")
        self.assertNotEqual(settled.animation_clip_id, "cast_front")

    def test_long_cast_lease_ends_at_authored_recovery(self):
        source = ProceduralWizardFrameSource()
        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("action", {"action": "magic_cast", "duration_ms": 5000})
            ).ok
        )
        run_ticks(source, 51)

        state = source.current_state()
        self.assertEqual(state.action, "idle")
        self.assertEqual(state.staff_state, "held")
        self.assertLess(state.time_seconds, 5.0)

    def test_short_cast_lease_cancels_before_commit(self):
        source = ProceduralWizardFrameSource()
        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("action", {"action": "magic_cast", "duration_ms": 100})
            ).ok
        )
        run_ticks(source, 7)

        state = source.current_state()
        self.assertEqual(state.action, "idle")
        self.assertEqual(state.animation_clip_id, "idle_front")
        self.assertEqual(state.staff_state, "held")

    def test_cast_lease_expiring_after_commit_still_reaches_settle(self):
        source = ProceduralWizardFrameSource()
        self.assertTrue(
            source.apply_command_sync(
                WizardCommand("action", {"action": "magic_cast", "duration_ms": 300})
            ).ok
        )

        run_ticks(source, 20)
        committed = source.current_state()
        self.assertEqual(committed.action, "magic_cast")
        self.assertGreater(committed.time_seconds, committed.action_until)

        run_ticks(source, 31)
        settled = source.current_state()
        self.assertEqual(settled.action, "idle")
        self.assertEqual(settled.animation_clip_id, "idle_front")

    def test_reaction_never_restores_preempted_cast(self):
        for phase, ticks in (("precommit", 7), ("committed", 16)):
            with self.subTest(phase=phase):
                source = ProceduralWizardFrameSource()
                self.assertTrue(
                    source.apply_command_sync(
                        WizardCommand(
                            "action",
                            {"action": "magic_cast", "duration_ms": 5000},
                        )
                    ).ok
                )
                run_ticks(source, ticks)
                self.assertTrue(
                    source.apply_command_sync(
                        WizardCommand(
                            "action",
                            {"action": "reaction", "duration_ms": 300},
                        )
                    ).ok
                )
                reacting = source.current_state()
                self.assertEqual(reacting.action, "reaction")
                self.assertIsNone(reacting.action_restore)

                run_seconds(source, 0.5)
                settled = source.current_state()
                self.assertEqual(settled.action, "idle")
                self.assertEqual(settled.upper_body_action, "none")
                self.assertEqual(settled.staff_state, "held")
                self.assertIsNone(settled.action_restore)


if __name__ == "__main__":
    unittest.main()
