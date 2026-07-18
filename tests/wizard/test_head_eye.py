import unittest

from wizard_avatar.head_eye import (
    EYE_AIM_CENTER,
    EYE_AIM_LEFT,
    EYE_AIM_RIGHT,
    HeadEyeCoordinator,
    HeadEyeState,
    advance_head_eye,
)
from wizard_avatar.models import DIRECTIONS


class HeadEyeCoordinatorTests(unittest.TestCase):
    def test_all_canonical_directions_are_steady(self):
        for facing in DIRECTIONS:
            with self.subTest(facing=facing):
                output = HeadEyeCoordinator(facing, 12).advance(facing, 12)
                self.assertEqual(output.presented_facing, facing)
                self.assertEqual(output.gaze_aim, EYE_AIM_CENTER)
                self.assertEqual(output.phase, "steady")

    def test_opposite_turn_uses_eye_lead_adjacent_views_and_settle(self):
        coordinator = HeadEyeCoordinator("south")
        ticks = (0, 9, 10, 16, 22, 28, 29, 40)
        frames = [coordinator.advance("north", tick) for tick in ticks]

        self.assertEqual(
            [frame.presented_facing for frame in frames],
            [
                "south",
                "south",
                "southwest",
                "west",
                "northwest",
                "north",
                "north",
                "north",
            ],
        )
        self.assertEqual(
            [frame.phase for frame in frames],
            [
                "leading",
                "leading",
                "turning",
                "turning",
                "turning",
                "turning",
                "settling",
                "steady",
            ],
        )
        self.assertEqual(
            [frame.automatic_gaze_aim for frame in frames],
            [
                EYE_AIM_LEFT,
                EYE_AIM_LEFT,
                EYE_AIM_LEFT,
                EYE_AIM_LEFT,
                EYE_AIM_LEFT,
                EYE_AIM_CENTER,
                EYE_AIM_CENTER,
                EYE_AIM_CENTER,
            ],
        )

    def test_eyes_recenter_when_head_arrives_before_settle_completes(self):
        coordinator = HeadEyeCoordinator("south")

        leading = coordinator.advance("west", 0)
        arrived = coordinator.advance("west", 12)
        settling = coordinator.advance("west", 13)

        self.assertEqual(leading.phase, "leading")
        self.assertEqual(leading.automatic_gaze_aim, EYE_AIM_LEFT)
        self.assertEqual(arrived.presented_facing, "west")
        self.assertEqual(arrived.phase, "turning")
        self.assertEqual(arrived.automatic_gaze_aim, EYE_AIM_CENTER)
        self.assertEqual(settling.phase, "settling")
        self.assertEqual(settling.automatic_gaze_aim, EYE_AIM_CENTER)

    def test_turn_in_both_directions_uses_shortest_path(self):
        left = HeadEyeCoordinator("south").advance("west", 0)
        right = HeadEyeCoordinator("south").advance("east", 0)
        self.assertEqual(left.automatic_gaze_aim, EYE_AIM_LEFT)
        self.assertEqual(right.automatic_gaze_aim, EYE_AIM_RIGHT)

    def test_explicit_gaze_overrides_automatic_turn_gaze(self):
        frame = HeadEyeCoordinator("south").advance(
            "north", 0, gaze_authoritative=True, gaze_aim=EYE_AIM_RIGHT
        )
        self.assertEqual(frame.automatic_gaze_aim, EYE_AIM_LEFT)
        self.assertEqual(frame.gaze_aim, EYE_AIM_RIGHT)
        self.assertTrue(frame.gaze_authoritative)

    def test_repeated_sampling_same_tick_is_idempotent(self):
        initial = HeadEyeState.steady("south")
        first_state, first = advance_head_eye(initial, "north", 50)
        second_state, second = advance_head_eye(first_state, "north", 50)
        third_state, third = advance_head_eye(first_state, "north", 50)

        self.assertEqual(first, second)
        self.assertEqual(second, third)
        self.assertEqual(first_state, second_state)
        self.assertEqual(second_state, third_state)

    def test_tick_jump_catches_up_without_render_call_count(self):
        state, _ = advance_head_eye(HeadEyeState.steady("south"), "north", 0)
        state, output = advance_head_eye(state, "north", 28)
        self.assertEqual(output.presented_facing, "north")
        self.assertEqual(output.phase, "turning")
        state, output = advance_head_eye(state, "north", 40)
        self.assertEqual(output.phase, "steady")

    def test_discarded_first_candidate_does_not_delay_turn_timing(self):
        initial = HeadEyeState.steady("south")
        committed, _ = advance_head_eye(
            initial,
            "north",
            5,
            facing_changed_tick=5,
        )
        committed_later, committed_output = advance_head_eye(
            committed,
            "north",
            15,
            facing_changed_tick=5,
        )
        discarded_later, discarded_output = advance_head_eye(
            initial,
            "north",
            15,
            facing_changed_tick=5,
        )

        self.assertEqual(committed_output, discarded_output)
        self.assertEqual(committed_later, discarded_later)

    def test_retarget_starts_from_current_visible_facing(self):
        coordinator = HeadEyeCoordinator("south")
        coordinator.advance("north", 0)
        visible = coordinator.advance("north", 17)
        retargeted = coordinator.advance("southeast", 17)

        self.assertEqual(visible.presented_facing, "west")
        self.assertEqual(retargeted.presented_facing, "west")
        self.assertEqual(coordinator.state.origin_facing, "west")
        self.assertEqual(coordinator.state.target_facing, "southeast")

    def test_retarget_to_visible_facing_cancels_cleanly(self):
        coordinator = HeadEyeCoordinator("south")
        coordinator.advance("north", 0)
        coordinator.advance("north", 17)
        cancelled = coordinator.advance("west", 17)
        self.assertEqual(cancelled.presented_facing, "west")
        self.assertEqual(cancelled.phase, "steady")

    def test_reset_is_explicit_and_transport_reconnect_api_does_not_exist(self):
        coordinator = HeadEyeCoordinator("south")
        coordinator.advance("north", 0)
        reset = coordinator.reset("east", 90)
        self.assertEqual(reset.presented_facing, "east")
        self.assertEqual(coordinator.state, HeadEyeState.steady("east", 90))
        self.assertFalse(hasattr(coordinator, "reconnect"))

    def test_invalid_input_is_rejected_without_mutating_owner(self):
        coordinator = HeadEyeCoordinator("south")
        before = coordinator.state
        with self.assertRaises(ValueError):
            coordinator.advance("downstage", 0)
        with self.assertRaises(ValueError):
            coordinator.advance("north", -1)
        self.assertEqual(coordinator.state, before)


if __name__ == "__main__":
    unittest.main()
