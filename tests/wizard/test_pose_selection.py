import unittest
from fractions import Fraction
from math import ceil

from wizard_avatar.animation_graph import load_reference_animation_graph_v2
from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.gestures import ACTION_TO_CHANNELS
from wizard_avatar.models import ACTIONS, WizardCommand, WizardState
from wizard_avatar.pose_selection import (
    _nearest_contact_entry_frame,
    _select_graph_v2_sample,
    select_reference_pose_id,
    select_reference_pose_sample,
)


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
                state_for(
                    facing="south",
                    locomotion="walking",
                    walk_phase=0.25,
                    animation_node_id="ground_walk",
                    animation_clip_id="walk_front",
                ),
                AVAILABLE_POSES,
            ),
            "front_idle",
        )
        self.assertEqual(
            select_reference_pose_id(
                state_for(
                    facing="south",
                    locomotion="walking",
                    walk_phase=0.50,
                    animation_node_id="ground_walk",
                    animation_clip_id="walk_front",
                ),
                AVAILABLE_POSES,
            ),
            "walk_front_right",
        )
        sample = select_reference_pose_sample(
            state_for(
                facing="south",
                locomotion="walking",
                walk_phase=0.75,
                animation_node_id="ground_walk",
                animation_clip_id="walk_front",
            ),
            AVAILABLE_POSES,
        )
        self.assertEqual(sample.pose_id, "front_idle")
        self.assertEqual(sample.contact, "none")
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
                    state_for(
                        facing="north",
                        locomotion="walking",
                        walk_phase=phase,
                        animation_node_id="back_walk",
                        animation_clip_id="walk_back",
                    ),
                    AVAILABLE_POSES,
                )
                self.assertEqual(pose_id, expected_pose)

    def test_horizontal_stage_travel_uses_authored_front_walk_contacts(self):
        for facing in ("east", "west"):
            observed = []
            for phase in (0.0, 0.5):
                sample = select_reference_pose_sample(
                    state_for(
                        facing=facing,
                        locomotion="walking",
                        walk_phase=phase,
                        animation_node_id="ground_walk",
                        animation_clip_id="walk_front",
                    )
                )
                observed.append((sample.pose_id, sample.contact))
                self.assertEqual(sample.clip_id, "walk_front")
                self.assertNotIn(sample.pose_id, {"profile_left", "profile_right"})
            self.assertEqual(
                {contact for _, contact in observed},
                {"left_foot", "right_foot"},
            )

    def test_horizontal_reversals_never_enter_back_walk_during_stepped_turn(self):
        graph = load_reference_animation_graph_v2()
        reversals = (
            (
                "west_to_east",
                (
                    (381, "west", -0.013372),
                    (382, "northwest", 0.053295),
                    (383, "north", 0.119962),
                    (384, "northeast", 0.186629),
                    (385, "east", 0.253296),
                ),
            ),
            (
                "east_to_west",
                (
                    (481, "east", 0.013372),
                    (482, "southeast", -0.053295),
                    (483, "south", -0.119962),
                    (484, "southwest", -0.186629),
                    (485, "west", -0.253296),
                ),
            ),
        )
        for name, ticks in reversals:
            with self.subTest(reversal=name):
                state = state_for(
                    locomotion="walking",
                    walk_phase=0.5,
                    animation_node_id="ground_walk",
                    animation_clip_id="walk_front",
                )
                observed_contacts = []
                for simulation_tick, facing, velocity_x in ticks:
                    state.simulation_tick = simulation_tick
                    state.animation_clip_tick += 1
                    state.facing = facing
                    state.velocity = {"x": velocity_x, "z": 0.0}
                    sample = _select_graph_v2_sample(state, graph)
                    observed_contacts.append(sample.contact)
                    self.assertEqual(state.animation_node_id, "ground_walk")
                    self.assertEqual(sample.clip_id, "walk_front")
                    self.assertNotIn(sample.pose_id, {"back_left", "back_idle", "back_right"})
                    self.assertIsNone(state.animation_transition_id)
                    self.assertEqual(state.animation_transition_generation, 0)
                self.assertEqual(set(observed_contacts), {"right_foot"})

    def test_profile_stops_are_authored_from_either_support_foot(self):
        graph = load_reference_animation_graph_v2()
        cases = (
            (
                "west",
                0.0,
                "left_foot",
                "ground_stop_left",
                "profile_left",
                128,
                ("walk_front_left", "walk_front_right", "front_idle", "profile_left"),
            ),
            (
                "west",
                0.5,
                "right_foot",
                "ground_stop_left",
                "profile_left",
                120,
                ("walk_front_right", "front_idle", "profile_left"),
            ),
            (
                "east",
                0.0,
                "left_foot",
                "ground_stop_right",
                "profile_right",
                128,
                ("walk_front_left", "walk_front_right", "front_idle", "profile_right"),
            ),
            (
                "east",
                0.5,
                "right_foot",
                "ground_stop_right",
                "profile_right",
                120,
                ("walk_front_right", "front_idle", "profile_right"),
            ),
        )
        for facing, phase, support, stop_node, idle_pose, settled_tick, pose_order in cases:
            with self.subTest(facing=facing, support=support):
                state = state_for(
                    facing=facing,
                    locomotion="idle",
                    walk_phase=phase,
                    animation_node_id="ground_walk",
                    animation_clip_id="walk_front",
                    animation_clip_tick=100,
                    simulation_tick=100,
                )

                entered = _select_graph_v2_sample(state, graph)
                self.assertEqual(state.animation_node_id, stop_node)
                self.assertEqual(entered.contact, support)
                self.assertEqual(state.animation_transition_generation, 1)
                self.assertIsNone(state.animation_transition_id)

                observed_poses = [entered.pose_id]
                while state.animation_node_id == stop_node:
                    state.simulation_tick += 1
                    state.animation_clip_tick += 1
                    sample = _select_graph_v2_sample(state, graph)
                    observed_poses.append(sample.pose_id)
                    self.assertLessEqual(state.simulation_tick, settled_tick)

                expected_idle_node = "left_idle" if facing == "west" else "right_idle"
                self.assertEqual(state.simulation_tick, settled_tick)
                self.assertEqual(state.animation_node_id, expected_idle_node)
                self.assertEqual(sample.pose_id, idle_pose)
                self.assertEqual(sample.contact, "both_feet")
                self.assertEqual(state.animation_transition_generation, 2)
                self.assertIsNone(state.animation_transition_id)
                observed_order = tuple(dict.fromkeys(observed_poses))
                self.assertEqual(observed_order, pose_order)
                entry_edge = graph.select_transition("ground_walk", stop_node)
                exit_edge = graph.select_transition(stop_node, expected_idle_node)
                self.assertIsNotNone(entry_edge)
                self.assertIsNotNone(exit_edge)
                self.assertEqual(entry_edge.contact_policy, "match")
                self.assertEqual(exit_edge.interrupt_window, "action_recoverable")

    def test_stop_waits_for_authored_contact_instead_of_release_sample(self):
        graph = load_reference_animation_graph_v2()
        state = state_for(
            facing="east",
            locomotion="idle",
            walk_phase=0.25,
            animation_node_id="ground_walk",
            animation_clip_id="walk_front",
            animation_clip_tick=20,
            simulation_tick=20,
        )

        release = _select_graph_v2_sample(state, graph)

        self.assertEqual(release.pose_id, "front_idle")
        self.assertEqual(release.active_markers, ("left_release",))
        self.assertEqual(state.animation_transition_id, "walk_to_stop_right")
        self.assertEqual(state.animation_transition_phase, "wait_gate")

        for _ in range(20):
            state.simulation_tick += 1
            state.animation_clip_tick += 1
            contacted = _select_graph_v2_sample(state, graph)
            if state.animation_node_id == "ground_stop_right":
                break

        self.assertEqual(state.animation_node_id, "ground_stop_right")
        self.assertEqual(contacted.contact, "right_foot")
        self.assertEqual(contacted.pose_id, "walk_front_right")
        self.assertEqual(state.animation_transition_generation, 1)

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
                if state.animation_node_id != expected_node:
                    state.simulation_tick += 1
                    state.animation_clip_tick += 1
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
        self.assertEqual(sample.clip_id, "idle_front")
        self.assertEqual(state.animation_node_id, "ground_idle")
        self.assertEqual(state.animation_transition_id, "idle_to_walk")
        self.assertEqual(state.animation_transition_phase, "wait_gate")

    def test_idle_to_walk_waits_for_minimum_hold_then_commits_atomically(self):
        graph = load_reference_animation_graph_v2()
        state = state_for(
            locomotion="walking",
            walk_phase=0.75,
        )

        source = _select_graph_v2_sample(state, graph)
        self.assertEqual(source.pose_id, "front_idle")
        self.assertEqual(state.animation_transition_phase, "wait_gate")
        self.assertEqual(state.animation_transition_id, "idle_to_walk")

        state.simulation_tick += 1
        state.animation_clip_tick += 1
        sample = _select_graph_v2_sample(state, graph)

        self.assertEqual(sample.pose_id, "walk_front_left")
        self.assertEqual(sample.contact, "left_foot")
        self.assertEqual(sample.phase, 0.0)
        self.assertEqual(state.animation_node_id, "ground_walk")
        self.assertEqual(state.animation_clip_id, "walk_front")
        self.assertIsNone(state.animation_transition_id)
        self.assertEqual(state.animation_transition_phase, "stable")
        self.assertEqual(state.animation_transition_generation, 1)

    def test_walk_to_idle_retains_walk_until_contact_boundary(self):
        graph = load_reference_animation_graph_v2()
        state = state_for(
            locomotion="idle",
            walk_phase=0.625,
            animation_node_id="ground_walk",
            animation_clip_id="walk_front",
            animation_clip_tick=12,
            simulation_tick=12,
        )

        walking = _select_graph_v2_sample(state, graph)
        self.assertEqual(walking.clip_id, "walk_front")
        self.assertEqual(state.animation_transition_phase, "wait_gate")
        self.assertEqual(state.animation_transition_id, "walk_to_idle")

        settle_ticks = 0
        while state.animation_transition_phase != "stable":
            state.simulation_tick += 1
            state.animation_clip_tick += 1
            settled = _select_graph_v2_sample(state, graph)
            settle_ticks += 1
            self.assertLess(settle_ticks, 17)

        self.assertEqual(settled.clip_id, "idle_front")
        self.assertEqual(settled.contact, "both_feet")
        self.assertEqual(state.animation_transition_phase, "stable")
        self.assertEqual(settle_ticks, 15)

    def test_run_charge_progresses_through_recovery_before_idle(self):
        graph = load_reference_animation_graph_v2()
        state = state_for(
            action="idle",
            animation_node_id="ground_run",
            animation_clip_id="run_charge_front",
            animation_clip_tick=30,
            simulation_tick=30,
        )

        recovery = _select_graph_v2_sample(state, graph)

        self.assertEqual(state.animation_node_id, "run_recovery")
        self.assertEqual(recovery.clip_id, "run_land_front")
        self.assertEqual(state.animation_transition_phase, "stable")

        observed_recovery = {recovery.pose_id}
        for _ in range(40):
            state.simulation_tick += 1
            state.animation_clip_tick += 1
            sample = _select_graph_v2_sample(state, graph)
            if state.animation_node_id == "run_recovery":
                observed_recovery.add(sample.pose_id)
            if state.animation_node_id == "ground_idle":
                break

        self.assertEqual(state.animation_node_id, "ground_idle")
        self.assertIn("front_kneel_staff_brace", observed_recovery)
        self.assertGreater(len(observed_recovery), 1)
        self.assertIsNone(state.animation_transition_id)

    def test_front_to_back_reversal_waits_for_contact_and_matches_support(self):
        graph = load_reference_animation_graph_v2()
        state = state_for(
            facing="north",
            locomotion="walking",
            walk_phase=0.625,
            animation_node_id="ground_walk",
            animation_clip_id="walk_front",
            animation_clip_tick=12,
            simulation_tick=12,
        )

        source = _select_graph_v2_sample(state, graph)
        self.assertEqual(source.clip_id, "walk_front")
        self.assertEqual(state.animation_transition_id, "walk_to_back_walk")
        self.assertEqual(state.animation_transition_phase, "wait_gate")

        state.walk_phase = 0.75
        state.simulation_tick += 1
        state.animation_clip_tick += 1
        release = _select_graph_v2_sample(state, graph)

        self.assertEqual(release.clip_id, "walk_front")
        self.assertEqual(release.active_markers, ("right_release",))
        self.assertEqual(state.animation_transition_phase, "wait_gate")

        state.walk_phase = 0.0
        state.simulation_tick += 1
        state.animation_clip_tick += 1
        target = _select_graph_v2_sample(state, graph)

        self.assertEqual(target.clip_id, "walk_back")
        self.assertEqual(target.contact, "left_foot")
        self.assertEqual(state.animation_node_id, "back_walk")
        self.assertEqual(state.animation_transition_phase, "stable")

    def test_preserve_transition_retains_normalized_source_phase(self):
        graph = load_reference_animation_graph_v2()
        state = state_for(
            airborne=True,
            mobility_mode="flight_travel",
            velocity={"x": 0.0, "z": 1.0},
            animation_node_id="hover",
            animation_clip_id="hover_front",
            animation_clip_tick=20,
        )

        source = _select_graph_v2_sample(state, graph)

        self.assertEqual(source.clip_id, "hover_front")
        self.assertEqual(state.animation_node_id, "hover")
        self.assertEqual(state.animation_transition_phase, "handoff")
        self.assertEqual(state.animation_transition_id, "hover_to_glide")
        self.assertEqual(state.animation_transition_entry_tick, 23)

        while state.simulation_tick < state.animation_transition_commit_tick:
            state.simulation_tick += 1
            state.animation_clip_tick += 1
            sample = _select_graph_v2_sample(state, graph)

        self.assertEqual(state.animation_node_id, "glide")
        self.assertIsNone(state.animation_transition_id)
        self.assertEqual(state.animation_clip_tick, 23)
        self.assertEqual(sample.phase, 0.5)

    def test_restart_transition_starts_target_clip_at_zero(self):
        graph = load_reference_animation_graph_v2()
        state = state_for(action="magic_cast", animation_clip_tick=20)

        sample = _select_graph_v2_sample(state, graph)

        self.assertEqual(sample.clip_id, "cast_front")
        self.assertEqual(sample.phase, 0.0)
        self.assertIsNone(state.animation_transition_id)
        self.assertEqual(state.animation_clip_tick, 0)

    def test_nearest_contact_fallback_breaks_phase_ties_by_earliest_frame(self):
        graph = load_reference_animation_graph_v2()

        frame = _nearest_contact_entry_frame(
            graph.clips["walk_front"],
            "both_feet",
            Fraction(1, 8),
        )

        self.assertEqual(frame, 0)

    def test_node_change_without_transition_restarts_and_clears_transition_id(self):
        graph = load_reference_animation_graph_v2()
        state = state_for(
            facing="north",
            animation_clip_tick=20,
            animation_transition_id="stale_transition",
        )

        sample = _select_graph_v2_sample(state, graph)

        self.assertEqual(sample.clip_id, "idle_back")
        self.assertEqual(sample.phase, 0.0)
        self.assertEqual(state.animation_node_id, "back_idle")
        self.assertIsNone(state.animation_transition_id)
        self.assertEqual(state.animation_clip_tick, 0)

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
            animation_node_id="ground_walk",
            animation_clip_id="walk_front",
        )
        self.assertEqual(
            select_reference_pose_id(speaking_walk, AVAILABLE_POSES),
            "front_idle",
        )


if __name__ == "__main__":
    unittest.main()
