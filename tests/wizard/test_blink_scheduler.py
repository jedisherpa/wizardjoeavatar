import copy
import unittest

from wizard_avatar.blink import BlinkScheduler, blink_seed_for_character
from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.models import WizardCommand


SIMULATION_HZ = 60
OPEN_PHASE_LIMIT = 0.965


def phase_runs(scheduler, ticks):
    runs = []
    closed = scheduler.phase >= OPEN_PHASE_LIMIT
    run_start = 0
    for tick in range(1, ticks + 1):
        next_closed = scheduler.advance_tick() >= OPEN_PHASE_LIMIT
        if next_closed != closed:
            runs.append((closed, tick - run_start))
            closed = next_closed
            run_start = tick
    return runs


def presented_phase_runs(scheduler, ticks, presentation_hz=24):
    phases = []
    accumulator = 0
    for _ in range(ticks):
        phase = scheduler.advance_tick()
        accumulator += presentation_hz
        if accumulator >= SIMULATION_HZ:
            accumulator -= SIMULATION_HZ
            phases.append(phase)
    runs = []
    closed = phases[0] >= OPEN_PHASE_LIMIT
    run_start = 0
    for index, phase in enumerate(phases[1:], start=1):
        next_closed = phase >= OPEN_PHASE_LIMIT
        if next_closed != closed:
            runs.append((closed, index - run_start))
            closed = next_closed
            run_start = index
    return runs


class BlinkSchedulerTests(unittest.TestCase):
    def test_character_seed_is_stable_and_character_specific(self):
        self.assertEqual(blink_seed_for_character("asciline-wizard-v1"), 5)
        self.assertEqual(
            blink_seed_for_character("asciline-wizard-v1"),
            blink_seed_for_character("asciline-wizard-v1"),
        )
        self.assertNotEqual(
            blink_seed_for_character("asciline-wizard-v1"),
            blink_seed_for_character("another-character"),
        )

    def test_character_seed_rejects_an_empty_identity(self):
        with self.assertRaises(ValueError):
            blink_seed_for_character("")

    def test_sequence_is_reproducible(self):
        first = BlinkScheduler()
        second = BlinkScheduler()

        first_sequence = [first.advance_tick() for _ in range(60 * SIMULATION_HZ)]
        second_sequence = [second.advance_tick() for _ in range(60 * SIMULATION_HZ)]

        self.assertEqual(first_sequence, second_sequence)
        self.assertTrue(all(phase in {0.0, 1.0} for phase in first_sequence))

    def test_open_intervals_are_bounded_and_varied(self):
        runs = phase_runs(BlinkScheduler(), 60 * SIMULATION_HZ)
        open_intervals = [length for closed, length in runs if not closed]

        self.assertGreaterEqual(len(set(open_intervals)), 3)
        self.assertTrue(
            all(2.5 * SIMULATION_HZ <= length <= 6.5 * SIMULATION_HZ for length in open_intervals)
        )

    def test_closures_last_between_100_and_200_milliseconds(self):
        runs = phase_runs(BlinkScheduler(), 60 * SIMULATION_HZ)
        closure_ticks = [length for closed, length in runs if closed]

        self.assertGreater(len(closure_ticks), 0)
        self.assertTrue(
            all(0.1 * SIMULATION_HZ <= length <= 0.2 * SIMULATION_HZ for length in closure_ticks)
        )

    def test_closures_present_for_three_to_four_frames_at_24_fps(self):
        runs = presented_phase_runs(BlinkScheduler(), 60 * SIMULATION_HZ)
        closure_frames = [length for closed, length in runs if closed]

        self.assertGreater(len(closure_frames), 0)
        self.assertTrue(all(3 <= length <= 4 for length in closure_frames))

    def test_closures_remain_visible_across_accepted_delivery_band(self):
        for presentation_hz in range(20, 25):
            runs = presented_phase_runs(
                BlinkScheduler(),
                60 * SIMULATION_HZ,
                presentation_hz=presentation_hz,
            )
            closure_frames = [length for closed, length in runs if closed]
            self.assertGreater(len(closure_frames), 0)
            self.assertTrue(
                all(3 <= length <= 4 for length in closure_frames),
                (presentation_hz, closure_frames),
            )

    def test_reset_restarts_the_same_sequence(self):
        scheduler = BlinkScheduler()
        expected = [scheduler.advance_tick() for _ in range(20 * SIMULATION_HZ)]

        scheduler.reset()

        self.assertEqual(
            [scheduler.advance_tick() for _ in range(20 * SIMULATION_HZ)],
            expected,
        )

    def test_controller_reset_restarts_blinks(self):
        controller = WizardAvatarController()
        expected = []
        for _ in range(20 * SIMULATION_HZ):
            controller.advance_tick()
            expected.append(controller.state.blink_phase)

        result = controller.apply_command(WizardCommand("reset"))
        actual = []
        for _ in range(20 * SIMULATION_HZ):
            controller.advance_tick()
            actual.append(controller.state.blink_phase)

        self.assertTrue(result.ok, result.message)
        self.assertEqual(actual, expected)

    def test_blinks_do_not_mutate_world_or_body_state(self):
        controller = WizardAvatarController()
        body_fields = (
            "world_position",
            "velocity",
            "facing",
            "locomotion",
            "action",
            "upper_body_action",
            "expression",
            "mouth",
            "staff_state",
            "airborne",
            "altitude",
            "vertical_velocity",
        )
        before = {
            field: copy.deepcopy(getattr(controller.state, field))
            for field in body_fields
        }

        for _ in range(60 * SIMULATION_HZ):
            controller.advance_tick()

        after = {
            field: copy.deepcopy(getattr(controller.state, field))
            for field in body_fields
        }
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
