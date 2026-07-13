import unittest
from math import ceil

from wizard_avatar.animation_graph import load_reference_animation_graph_v2
from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.gestures import ACTION_TO_CHANNELS
from wizard_avatar.models import ACTIONS, WizardCommand, WizardState
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
            "southwest": "front_idle",
            "southeast": "front_idle",
            "north": "back_idle",
            "northwest": "back_idle",
            "northeast": "back_idle",
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
        self.assertEqual(sample.contact, "left_foot")
        self.assertEqual(sample.clip_id, "walk_front")

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
        cases = (
            (state_for(action="dash"), "ground_run", "run_charge_front"),
            (
                state_for(action="explaining", upper_body_action="explain"),
                "explain",
                "explain_front",
            ),
            (
                state_for(action="idle", upper_body_action="cast", staff_state="cast"),
                "cast",
                "cast_front",
            ),
        )
        for state, expected_node, expected_clip in cases:
            with self.subTest(expected_node=expected_node):
                sample = select_reference_pose_sample(state, AVAILABLE_POSES)
                self.assertEqual(state.animation_node_id, expected_node)
                self.assertEqual(sample.clip_id, expected_clip)

    def test_all_authored_semantic_actions_reach_their_v2_clips(self):
        graph = load_reference_animation_graph_v2()
        action_nodes = {
            "dash": "ground_run",
            "magic_cast": "cast",
            "guard": "guard",
            "block": "block",
            "flourish": "flourish",
            "staff_spin": "flourish",
            "victory_cast": "victory_cast",
            "explaining": "explain",
            "speaking": "explain",
            "pointing": "point",
            "shush": "shush",
            "celebrate": "celebrate",
            "staff_forward": "air_staff",
            "reaction": "hit_reaction",
            "hit": "hit_reaction",
        }
        self.assertTrue(set(action_nodes).issubset(ACTIONS))
        for action, node_id in action_nodes.items():
            with self.subTest(action=action):
                node = graph.nodes[node_id]
                state = state_for(
                    action=action,
                    airborne=action == "staff_forward",
                    mobility_mode="hover" if action == "staff_forward" else "grounded_idle",
                    animation_node_id=node_id,
                    animation_clip_id=node.clip_id,
                )
                observed = set()
                clip = graph.clips[node.clip_id]
                ticks = ceil(clip.total_frames * graph.simulation_hz / graph.authored_fps)
                for tick in range(ticks + 1):
                    state.animation_clip_tick = tick
                    observed.add(select_reference_pose_sample(state).pose_id)
                expected = {sample.pose_id for sample in clip.samples}
                self.assertEqual(observed, expected)

    def test_controller_accepts_every_graph_declared_action(self):
        graph = load_reference_animation_graph_v2()
        declared_actions = {
            action
            for node in graph.nodes.values()
            for action in node.actions
        }
        self.assertTrue(declared_actions.issubset(ACTIONS))
        self.assertTrue(declared_actions.issubset(ACTION_TO_CHANNELS))
        for action in sorted(declared_actions):
            with self.subTest(action=action):
                controller = WizardAvatarController()
                result = controller.apply_command(
                    WizardCommand(
                        "action",
                        {"action": action, "duration_ms": 900},
                    )
                )
                self.assertTrue(result.ok, result.message)
                self.assertEqual(controller.current_state().action, action)

    def test_graph_transition_is_selected_when_ground_motion_changes(self):
        state = state_for(locomotion="walking", walk_phase=0.1)
        sample = select_reference_pose_sample(state)
        self.assertEqual(sample.clip_id, "walk_front")
        self.assertEqual(state.animation_node_id, "ground_walk")
        self.assertEqual(state.animation_transition_id, "idle_to_walk")

    def test_stale_walking_action_is_reconciled_from_locomotion(self):
        state = state_for(
            locomotion="idle",
            action="walking",
            upper_body_action="none",
            action_until=12.0,
        )
        select_reference_pose_sample(state, AVAILABLE_POSES)
        self.assertEqual(state.action, "idle")
        self.assertEqual(state.action_until, 0.0)

    def test_public_state_never_reports_idle_locomotion_as_walking_action(self):
        state = state_for(locomotion="idle", action="walking", action_until=12.0)
        public = state.as_public_dict()
        self.assertEqual(public["locomotion"], "idle")
        self.assertEqual(public["action"], "idle")

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
