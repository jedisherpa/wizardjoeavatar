import unittest

from wizard_avatar.models import WizardState
from wizard_avatar.pose_selection import select_reference_pose_id, select_reference_pose_sample


AVAILABLE_POSES = {
    "front_idle",
    "back_idle",
    "profile_left",
    "profile_right",
    "walk_front_left",
    "walk_front_right",
    "back_left",
    "back_right",
    "explaining",
    "magic_cast",
    "run_front_airborne_reach",
}


def state_for(**overrides):
    state = WizardState()
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


class PoseSelectionTests(unittest.TestCase):
    def test_pose_override_selects_requested_pose_above_locomotion(self):
        state = state_for(
            locomotion="walking",
            walk_phase=0.75,
            pose_override_id="magic_cast",
        )
        sample = select_reference_pose_sample(state, AVAILABLE_POSES)
        self.assertEqual(sample.pose_id, "magic_cast")
        self.assertEqual(sample.clip_id, "pose_showcase")

    def test_idle_facing_pose_map(self):
        cases = {
            "south": "front_idle",
            "southwest": "walk_front_left",
            "southeast": "walk_front_right",
            "north": "back_idle",
            "northwest": "back_left",
            "northeast": "back_right",
            "west": "profile_left",
            "east": "profile_right",
        }
        for facing, expected_pose in cases.items():
            with self.subTest(facing=facing):
                pose_id = select_reference_pose_id(state_for(facing=facing), AVAILABLE_POSES)
                self.assertEqual(pose_id, expected_pose)

    def test_front_walk_uses_animation_graph_samples(self):
        self.assertEqual(
            select_reference_pose_id(
                state_for(facing="south", locomotion="walking", walk_phase=0.25),
                AVAILABLE_POSES,
            ),
            "front_idle",
        )
        self.assertEqual(
            select_reference_pose_id(
                state_for(facing="south", locomotion="walking", walk_phase=0.50),
                AVAILABLE_POSES,
            ),
            "walk_front_right",
        )
        sample = select_reference_pose_sample(
            state_for(facing="south", locomotion="walking", walk_phase=0.75),
            AVAILABLE_POSES,
        )
        self.assertEqual(sample.pose_id, "front_idle")
        self.assertEqual(sample.contact, "both")

    def test_back_walk_uses_animation_graph_samples(self):
        cases = (
            (0.10, "back_left"),
            (0.40, "back_idle"),
            (0.80, "back_idle"),
        )
        for phase, expected_pose in cases:
            with self.subTest(phase=phase):
                pose_id = select_reference_pose_id(
                    state_for(facing="north", locomotion="walking", walk_phase=phase),
                    AVAILABLE_POSES,
                )
                self.assertEqual(pose_id, expected_pose)

    def test_action_channels_select_available_action_poses(self):
        self.assertEqual(
            select_reference_pose_id(
                state_for(action="dash"),
                AVAILABLE_POSES,
            ),
            "run_front_airborne_reach",
        )
        self.assertEqual(
            select_reference_pose_id(
                state_for(action="explaining", upper_body_action="explain"),
                AVAILABLE_POSES,
            ),
            "explaining",
        )
        self.assertEqual(
            select_reference_pose_id(
                state_for(action="idle", upper_body_action="cast", staff_state="cast"),
                AVAILABLE_POSES,
            ),
            "magic_cast",
        )

    def test_speech_does_not_replace_body_pose(self):
        speaking_profile = state_for(
            facing="east",
            action="speaking",
            upper_body_action="explain",
            speech_id="speech-1",
        )
        self.assertEqual(
            select_reference_pose_id(speaking_profile, AVAILABLE_POSES),
            "profile_right",
        )

        speaking_walk = state_for(
            facing="south",
            locomotion="walking",
            action="speaking",
            upper_body_action="explain",
            speech_id="speech-2",
            walk_phase=0.75,
        )
        self.assertEqual(
            select_reference_pose_id(speaking_walk, AVAILABLE_POSES),
            "front_idle",
        )


if __name__ == "__main__":
    unittest.main()
