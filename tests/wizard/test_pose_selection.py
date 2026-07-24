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
    presentation_pose_for_facing,
    select_reference_pose_id,
    select_reference_pose_sample,
)
from wizard_avatar.reference_avatar import get_reference_pose


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

    def test_idle_turn_presentation_uses_all_eight_authored_views(self):
        expected_by_facing = {
            "south": "front_idle",
            "southeast": "walk_front_right",
            "east": "profile_right",
            "northeast": "back_right",
            "north": "back_idle",
            "northwest": "back_left",
            "west": "profile_left",
            "southwest": "walk_front_left",
        }
        for facing, expected_pose in expected_by_facing.items():
            with self.subTest(facing=facing):
                self.assertEqual(
                    presentation_pose_for_facing(
                        "front_idle",
                        "idle_front",
                        facing,
                        AVAILABLE_POSES,
                    ),
                    expected_pose,
                )

    def test_turn_presentation_does_not_replace_action_pose(self):
        self.assertEqual(
            presentation_pose_for_facing(
                "magic_cast",
                "cast_front",
                "northeast",
                AVAILABLE_POSES,
            ),
            "magic_cast",
        )

    def test_turn_presentation_falls_back_when_authored_view_is_unavailable(self):
        self.assertEqual(
            presentation_pose_for_facing(
                "front_idle",
                "idle_front",
                "northeast",
                {"front_idle"},
            ),
            "front_idle",
        )

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

    def test_horizontal_stage_travel_uses_directional_profile_contacts(self):
        cases = {
            "east": (
                "ground_walk_right",
                "walk_right",
                1.0,
                (
                    (0.0, "walk_profile_right_contact_left", "left_foot"),
                    (
                        0.25,
                        "walk_profile_right_passing_left_to_right",
                        "none",
                    ),
                    (0.5, "walk_profile_right_contact_right", "right_foot"),
                    (
                        0.75,
                        "walk_profile_right_passing_right_to_left",
                        "none",
                    ),
                ),
            ),
            "west": (
                "ground_walk_left",
                "walk_left",
                -1.0,
                (
                    (0.0, "walk_profile_left_contact_left", "left_foot"),
                    (
                        0.25,
                        "walk_profile_left_passing_left_to_right",
                        "none",
                    ),
                    (0.5, "walk_profile_left_contact_right", "right_foot"),
                    (
                        0.75,
                        "walk_profile_left_passing_right_to_left",
                        "none",
                    ),
                ),
            ),
        }
        for facing, (
            expected_node,
            expected_clip,
            velocity_x,
            expected_samples,
        ) in cases.items():
            observed = []
            for phase, expected_pose, expected_contact in expected_samples:
                sample = select_reference_pose_sample(
                    state_for(
                        facing=facing,
                        locomotion="walking",
                        walk_phase=phase,
                        animation_node_id=expected_node,
                        animation_clip_id=expected_clip,
                        velocity={"x": velocity_x, "z": 0.0},
                    )
                )
                observed.append((sample.pose_id, sample.contact))
                self.assertEqual(sample.clip_id, expected_clip)
                self.assertEqual(sample.pose_id, expected_pose)
                self.assertEqual(sample.contact, expected_contact)
                self.assertEqual(
                    sample.planted_anchor,
                    None if expected_contact == "none" else expected_contact,
                )
                self.assertEqual(sample.root_policy, "contact_locked")
            self.assertEqual(
                {contact for _, contact in observed},
                {"left_foot", "right_foot", "none"},
            )

    def test_front_to_east_turn_presents_authored_quarter_views_before_profile_walk(self):
        graph = load_reference_animation_graph_v2()
        state = state_for(
            facing="southeast",
            locomotion="walking",
            walk_phase=0.5,
            velocity={"x": 1.0, "z": 0.0},
            animation_node_id="ground_walk",
            animation_clip_id="walk_front",
        )
        observed = []
        observed_contacts = set()
        for _ in range(70):
            sample = _select_graph_v2_sample(state, graph)
            if not observed or observed[-1] != sample.pose_id:
                observed.append(sample.pose_id)
            self.assertEqual(sample.root_policy, "contact_locked")
            self.assertIn(sample.contact, {"left_foot", "right_foot", "none"})
            observed_contacts.add(sample.contact)
            state.simulation_tick += 1
            state.animation_clip_tick += 1
            if state.animation_node_id == "ground_walk_right":
                break

        self.assertEqual(
            observed,
            [
                "walk_front_right",
                "turn_front_to_right_entry_250",
                "turn_front_to_right_entry_500",
                "turn_front_to_right_entry_750",
                "hd_turn_right_anticipation",
                "hd_turn_right_mid",
                "hd_turn_right_complete",
                "walk_profile_right_contact_left",
            ],
        )
        self.assertEqual(state.animation_node_id, "ground_walk_right")
        self.assertEqual(sample.clip_id, "walk_right")
        self.assertEqual(sample.contact, "left_foot")
        self.assertEqual(observed_contacts, {"right_foot", "left_foot", "none"})

    def test_front_body_turn_is_not_skipped_when_pathing_facing_already_reached_east(self):
        graph = load_reference_animation_graph_v2()
        state = state_for(
            facing="east",
            locomotion="walking",
            walk_phase=0.5,
            velocity={"x": 1.0, "z": 0.0},
            animation_node_id="ground_walk",
            animation_clip_id="walk_front",
        )

        sample = _select_graph_v2_sample(state, graph)

        self.assertEqual(state.animation_node_id, "ground_turn_front_to_east")
        self.assertEqual(sample.clip_id, "turn_front_to_east")
        self.assertEqual(sample.pose_id, "walk_front_right")

    def test_horizontal_reversals_use_authored_crossover_phrases(self):
        graph = load_reference_animation_graph_v2()
        reversals = (
            (
                "west_to_east",
                "west",
                "ground_walk_left",
                "walk_left",
                0.0,
                1.0,
                "ground_walk_right",
                (
                    "walk_profile_left_contact_left",
                    "hd_turn_left_complete",
                    "turn_left_mid_to_complete_833",
                    "turn_left_mid_to_complete_667",
                    "turn_left_mid_to_complete_500",
                    "turn_left_mid_to_complete_333",
                    "turn_left_mid_to_complete_166",
                    "hd_turn_left_mid",
                    "hd_turn_left_anticipation",
                    "hd_turn_front_neutral",
                    "hd_turn_right_anticipation",
                    "hd_turn_right_mid",
                    "hd_turn_right_complete",
                    "walk_profile_right_contact_right",
                ),
            ),
            (
                "east_to_west",
                "east",
                "ground_walk_right",
                "walk_right",
                0.5,
                -1.0,
                "ground_walk_left",
                (
                    "walk_profile_right_contact_right",
                    "hd_turn_right_complete",
                    "hd_turn_right_mid",
                    "hd_turn_right_anticipation",
                    "hd_turn_front_neutral",
                    "hd_turn_left_anticipation",
                    "hd_turn_left_mid",
                    "turn_left_mid_to_complete_166",
                    "turn_left_mid_to_complete_333",
                    "turn_left_mid_to_complete_500",
                    "turn_left_mid_to_complete_667",
                    "turn_left_mid_to_complete_833",
                    "hd_turn_left_complete",
                    "walk_profile_left_contact_left",
                ),
            ),
        )
        for (
            name,
            facing,
            source_node,
            source_clip,
            phase,
            velocity_x,
            target_node,
            expected_poses,
        ) in reversals:
            with self.subTest(reversal=name):
                state = state_for(
                    facing=facing,
                    locomotion="walking",
                    walk_phase=phase,
                    velocity={"x": velocity_x, "z": 0.0},
                    animation_node_id=source_node,
                    animation_clip_id=source_clip,
                )
                observed_poses = []
                observed_turn_clips = set()
                observed_contacts = set()
                for _ in range(100):
                    sample = _select_graph_v2_sample(state, graph)
                    if state.animation_node_id.startswith("ground_reverse_"):
                        observed_turn_clips.add(sample.clip_id)
                        self.assertEqual(sample.root_policy, "contact_locked")
                        self.assertIn(
                            sample.contact,
                            {"left_foot", "right_foot", "both_feet", "none"},
                        )
                        observed_contacts.add(sample.contact)
                        if not observed_poses or observed_poses[-1] != sample.pose_id:
                            observed_poses.append(sample.pose_id)
                    state.simulation_tick += 1
                    state.animation_clip_tick += 1
                    if state.animation_node_id == target_node:
                        break
                self.assertEqual(tuple(observed_poses), expected_poses)
                self.assertEqual(
                    observed_turn_clips,
                    {
                        "reverse_west_to_east"
                        if name == "west_to_east"
                        else "reverse_east_to_west"
                    },
                )
                self.assertEqual(state.animation_node_id, target_node)
                self.assertEqual(state.animation_transition_phase, "stable")
                self.assertEqual(state.animation_transition_generation, 2)
                self.assertIn("none", observed_contacts)

    def test_profile_stops_are_authored_from_either_support_foot(self):
        graph = load_reference_animation_graph_v2()
        cases = (
            (
                "west",
                0.0,
                "left_foot",
                "ground_stop_left",
                "profile_left",
                133,
                (
                    "walk_profile_left_passing_left_to_right",
                    "stop_profile_left_hd_settle_200",
                    "stop_profile_left_hd_settle_400",
                    "stop_profile_left_hd_settle_600",
                    "stop_profile_left_hd_settle_800",
                    "hd_turn_left_complete",
                    "profile_left",
                ),
            ),
            (
                "west",
                0.5,
                "right_foot",
                "ground_stop_left",
                "profile_left",
                153,
                (
                    "walk_profile_left_contact_right",
                    "walk_profile_left_contact_right_to_passing_250",
                    "walk_profile_left_contact_right_to_passing_500",
                    "walk_profile_left_contact_right_to_passing_750",
                    "walk_profile_left_passing_right_to_left",
                    "walk_profile_left_passing_to_contact_left_250",
                    "walk_profile_left_passing_to_contact_left_500",
                    "walk_profile_left_passing_to_contact_left_750",
                    "walk_profile_left_passing_left_to_right",
                    "stop_profile_left_hd_settle_200",
                    "stop_profile_left_hd_settle_400",
                    "stop_profile_left_hd_settle_600",
                    "stop_profile_left_hd_settle_800",
                    "hd_turn_left_complete",
                    "profile_left",
                ),
            ),
            (
                "east",
                0.0,
                "left_foot",
                "ground_stop_right",
                "profile_right",
                133,
                (
                    "walk_profile_right_passing_right_to_left",
                    "stop_profile_right_hd_settle_200",
                    "stop_profile_right_hd_settle_400",
                    "stop_profile_right_hd_settle_600",
                    "stop_profile_right_hd_settle_800",
                    "hd_turn_right_complete",
                    "profile_right",
                ),
            ),
            (
                "east",
                0.5,
                "right_foot",
                "ground_stop_right",
                "profile_right",
                123,
                (
                    "stop_profile_right_hd_settle_400",
                    "stop_profile_right_hd_settle_600",
                    "stop_profile_right_hd_settle_800",
                    "hd_turn_right_complete",
                    "profile_right",
                ),
            ),
        )
        for facing, phase, support, stop_node, idle_pose, settled_tick, pose_order in cases:
            with self.subTest(facing=facing, support=support):
                state = state_for(
                    facing=facing,
                    locomotion="idle",
                    walk_phase=phase,
                    animation_node_id=(
                        "ground_walk_left" if facing == "west" else "ground_walk_right"
                    ),
                    animation_clip_id=(
                        "walk_left" if facing == "west" else "walk_right"
                    ),
                    animation_clip_tick=100,
                    simulation_tick=100,
                )

                sample = _select_graph_v2_sample(state, graph)
                observed_poses = [sample.pose_id]
                stop_observed = state.animation_node_id == stop_node
                expected_idle_node = "left_idle" if facing == "west" else "right_idle"
                while state.animation_node_id != expected_idle_node:
                    state.simulation_tick += 1
                    state.animation_clip_tick += 1
                    sample = _select_graph_v2_sample(state, graph)
                    observed_poses.append(sample.pose_id)
                    stop_observed = stop_observed or state.animation_node_id == stop_node
                    self.assertLessEqual(state.simulation_tick, settled_tick)

                self.assertTrue(stop_observed)
                self.assertEqual(state.simulation_tick, settled_tick)
                self.assertEqual(state.animation_node_id, expected_idle_node)
                self.assertEqual(sample.pose_id, idle_pose)
                self.assertEqual(sample.contact, "both_feet")
                self.assertEqual(state.animation_transition_generation, 2)
                self.assertIsNone(state.animation_transition_id)
                observed_order = tuple(dict.fromkeys(observed_poses))
                self.assertEqual(observed_order, pose_order)
                entry_edge = graph.select_transition(
                    "ground_walk_left" if facing == "west" else "ground_walk_right",
                    stop_node,
                )
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

        self.assertEqual(release.pose_id, "walk_front_left_to_right")
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
        self.assertEqual(contacted.pose_id, "stop_profile_right_hd_settle_400")
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

    def test_front_walk_stops_through_phase_matched_authored_settle(self):
        graph = load_reference_animation_graph_v2()
        cases = (
            ("walk_front_left", "ground_stop_front_left", "stop_front_from_left"),
            ("walk_front_right", "ground_stop_front_right", "stop_front_from_right"),
            (
                "walk_front_left_to_right",
                "ground_stop_front_left_passing",
                "stop_front_from_left_passing",
            ),
            (
                "walk_front_right_to_left",
                "ground_stop_front_right_passing",
                "stop_front_from_right_passing",
            ),
        )
        for source_pose, stop_node, family in cases:
            with self.subTest(source_pose=source_pose):
                state = state_for(
                    locomotion="idle",
                    pose_id=source_pose,
                    animation_node_id="ground_walk",
                    animation_clip_id="walk_front",
                    animation_clip_tick=100,
                    simulation_tick=100,
                )

                sample = _select_graph_v2_sample(state, graph)
                self.assertEqual(state.animation_node_id, stop_node)
                self.assertEqual(sample.pose_id, source_pose)
                observed = [sample.pose_id]
                for _ in range(60):
                    state.simulation_tick += 1
                    state.animation_clip_tick += 1
                    sample = _select_graph_v2_sample(state, graph)
                    observed.append(sample.pose_id)
                    if state.animation_node_id == "ground_idle":
                        break

                self.assertEqual(state.animation_node_id, "ground_idle")
                self.assertEqual(sample.pose_id, "front_idle")
                compact = tuple(dict.fromkeys(observed))
                self.assertEqual(
                    compact,
                    (
                        source_pose,
                        f"{family}_25",
                        f"{family}_50",
                        f"{family}_625",
                        f"{family}_75",
                        f"{family}_875",
                        f"{family}_100",
                        "front_idle",
                    ),
                )

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

    def test_cast_clip_uses_frame_complete_rigged_staff_arc(self):
        graph = load_reference_animation_graph_v2()
        clip = graph.clips["cast_front"]

        self.assertEqual(
            [sample.pose_id for sample in clip.samples],
            [f"cast_front_{frame:02d}" for frame in range(32)],
        )
        self.assertNotIn("magic_cast", [sample.pose_id for sample in clip.samples])
        self.assertTrue(all(sample.duration_frames == 1 for sample in clip.samples))
        self.assertEqual(clip.total_frames, 32)
        self.assertTrue(
            graph.pose_catalog["cast_front_00"].source.startswith(
                "derived_cast_rig:front_idle:"
            )
        )

        staff_tip_offsets = []
        for sample in clip.samples:
            pose = get_reference_pose(sample.pose_id)
            density = Fraction(*pose.presentation_scale)
            staff_tip_offsets.append(
                Fraction(pose.anchors["staff_tip"][0] - pose.root_anchor[0])
                * density
            )
        self.assertLessEqual(
            max(
                abs(current - previous)
                for previous, current in zip(
                    staff_tip_offsets,
                    staff_tip_offsets[1:],
                )
            ),
            2,
        )

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
