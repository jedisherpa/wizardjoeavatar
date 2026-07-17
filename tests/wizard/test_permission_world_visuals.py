import copy
import unittest

from wizard_avatar.character_capabilities import derive_character_capability_manifest
from wizard_avatar.frame_source import (
    ProceduralWizardFrameSource,
    WizardRenderSnapshot,
)
from wizard_avatar.performance_application import PerformanceApplication
from wizard_avatar.permission_world import (
    CapabilityPermissionV1,
    PermissionWorldCapabilityIndexV1,
    PermissionWorldStateV1,
)
from wizard_avatar.projection import project_quantized
from wizard_avatar.reference_avatar import (
    reference_pose_anchor,
    reference_pose_root_anchor,
)
from wizard_avatar.pose_compositor import clear_authored_staff


OBSERVED_MS = 10_000


def capability_manifest():
    return {
        "permission_world": {
            "bindings": {
                "world_state_ids": ["default"],
                "effect_ids": ["magic_effect", "unsupported_calendar_glow"],
                "prop_ids": ["staff", "unsupported_book"],
            }
        },
        "capabilities": [
            {
                "admission": "graph_admitted",
                "mapping": {
                    "effect_ids": ["magic_effect"],
                    "prop_ids": ["staff"],
                },
            }
        ]
    }


def permission(
    capability_kind,
    *,
    posture="granted",
    revoked=False,
    expires_at_ms=OBSERVED_MS + 1_000,
):
    granted = posture == "granted"
    return CapabilityPermissionV1(
        capability_kind=capability_kind,
        posture=posture,
        required_scope_class="current_surface",
        granted_scope_class="current_surface" if granted else None,
        purpose_code="stage_projection",
        granted_at_ms=OBSERVED_MS - 1 if granted else None,
        affected_surfaces=("companion.stage",),
        app_link_state="linked",
        expires_at_ms=expires_at_ms,
        revoked=revoked,
    )


def authority_state(*permissions):
    return PermissionWorldStateV1.build(
        source_epoch="permission-source:visual-test",
        observed_at_ms=OBSERVED_MS,
        permissions=permissions,
    )


def application_and_source():
    source = ProceduralWizardFrameSource(180, 101, 24)
    application = PerformanceApplication(
        "permission-visual-runtime",
        character_id=source.character_package.character_id,
        capability_manifest=capability_manifest(),
    )
    return application, source


def frame_rgb(frame, x, y):
    offset = (y * frame.cols + x) * 4
    return tuple(frame.cells[offset + 1 : offset + 4])


class PermissionWorldVisualApplicationTests(unittest.TestCase):
    def apply_state(self, *permissions, now_monotonic_us=1_000_000):
        application, source = application_and_source()
        application.accept_permission_world(authority_state(*permissions))
        application.apply(source.controller, now_monotonic_us)
        return application, source

    def test_authoritative_grants_change_the_visible_projected_frame(self):
        _, source = self.apply_state(
            permission("world_state:default"),
            permission("effect:magic_effect"),
            permission("prop:staff"),
        )
        policy = source.controller.permission_world_render_policy
        self.assertEqual(policy.managed_world_states, ("default",))
        self.assertEqual(policy.managed_effects, ("magic_effect",))
        self.assertEqual(policy.managed_props, ("staff",))
        self.assertEqual(policy.visible_world_states, ("default",))
        self.assertEqual(policy.visible_effects, ("magic_effect",))
        self.assertEqual(policy.visible_props, ("staff",))

        source.controller.state.pose_override_id = "front_idle"
        source.controller.state.pose_override_until = 100.0
        frame = source.render_current_frame()
        state = source.current_state()
        sx, sy, scale = project_quantized(
            state.world_position["x"], state.world_position["z"], 180, 101
        )
        render_scale = scale * 0.90
        root = reference_pose_root_anchor("front_idle", source.pose_library_path)
        tip = reference_pose_anchor("front_idle", "staff_tip", source.pose_library_path)
        hand = reference_pose_anchor("front_idle", "staff_hand", source.pose_library_path)
        shaft = (
            round(tip[0] + (hand[0] - tip[0]) * 0.45),
            round(tip[1] + (hand[1] - tip[1]) * 0.45),
        )
        root_screen = source._reference_root_screen(sx, sy, state, render_scale)
        tip_x = round(
            root_screen[0]
            - root[0] * render_scale * 1.18
            + shaft[0] * render_scale * 1.18
        )
        tip_y = round(root_screen[1] - root[1] * render_scale + shaft[1] * render_scale)
        self.assertTrue(
            any(
                frame_rgb(frame, x, y) != (255, 255, 255)
                for y in range(max(0, tip_y - 4), min(frame.rows, tip_y + 5))
                for x in range(max(0, tip_x - 5), min(frame.cols, tip_x + 6))
            )
        )
        self.assertNotEqual(frame_rgb(frame, 10, 90), (255, 255, 255))

    def test_effect_grant_keeps_authored_pose_and_deny_uses_neutral_fallback(self):
        _, granted = self.apply_state(
            permission("effect:magic_effect"),
            permission("prop:staff"),
        )
        _, denied = self.apply_state(
            permission("effect:magic_effect", posture="denied"),
            permission("prop:staff"),
        )
        for source in (granted, denied):
            state = source.controller.state
            state.action = "magic_cast"
            state.animation_clip_id = "cast_front"
            state.pose_override_id = "magic_cast"
            state.pose_override_until = 100.0

        granted_frame = granted.render_current_frame()
        denied_frame = denied.render_current_frame()
        self.assertEqual(granted._last_presentation_state.pose_id, "magic_cast")
        self.assertEqual(denied._last_presentation_state.pose_id, "front_idle")
        self.assertNotEqual(granted_frame.cells, denied_frame.cells)

    def test_deny_revoke_and_expire_remove_projected_surfaces(self):
        cases = (
            permission("prop:staff", posture="denied"),
            permission("prop:staff", revoked=True),
            permission("prop:staff", expires_at_ms=OBSERVED_MS + 20),
        )
        for item in cases:
            with self.subTest(posture=item.posture, revoked=item.revoked):
                application, source = application_and_source()
                application.accept_permission_world(authority_state(item))
                application.apply(source.controller, 1_000_000)
                if item.expires_at_ms == OBSERVED_MS + 20:
                    application.apply(source.controller, 1_021_000)
                self.assertEqual(
                    source.controller.permission_world_render_policy.visible_props,
                    (),
                )

    def test_denied_staff_is_removed_from_authored_pixel_graph_and_frame(self):
        _, granted = self.apply_state(permission("prop:staff"))
        _, denied = self.apply_state(permission("prop:staff", posture="denied"))
        for source in (granted, denied):
            source.controller.state.pose_override_id = "front_idle"
            source.controller.state.pose_override_until = 100.0

        granted_local, _, _ = granted._reference_pose_canvas_for_sample("front_idle")
        denied_local, _, _ = denied._reference_pose_canvas_for_sample("front_idle")
        denied._apply_reference_permission_surfaces(
            denied_local,
            "front_idle",
            denied.controller.permission_world_render_policy,
        )
        root = reference_pose_root_anchor("front_idle", denied.pose_library_path)
        for y in range(25, denied_local.height):
            for distance in range(8, denied_local.width):
                right = root[0] + distance
                left = root[0] - distance
                if denied_local.in_bounds(right, y) and denied_local.in_bounds(left, y):
                    self.assertEqual(
                        denied_local.get(right, y),
                        granted_local.get(left, y),
                    )
        left_eye = reference_pose_anchor(
            "front_idle", "left_eye", denied.pose_library_path
        )
        self.assertEqual(
            granted_local.get(*left_eye),
            denied_local.get(*left_eye),
        )
        self.assertNotEqual(
            granted.render_current_frame().cells,
            denied.render_current_frame().cells,
        )

    def test_denied_staff_action_resolves_to_complete_neutral_fallback(self):
        _, denied = self.apply_state(
            permission("effect:magic_effect"),
            permission("prop:staff", posture="denied"),
        )
        denied.controller.state.action = "magic_cast"
        denied.controller.state.animation_clip_id = "cast_front"
        denied.controller.state.pose_override_id = "magic_cast"
        denied.controller.state.pose_override_until = 100.0
        denied.render_current_frame()
        self.assertEqual(denied._last_presentation_state.pose_id, "front_idle")

    def test_every_authored_pose_has_a_deterministic_staff_mask(self):
        _, source = application_and_source()
        first_counts = {}
        second_counts = {}
        for pose_id in source.pose_ids:
            tip = reference_pose_anchor(
                pose_id, "staff_tip", source.pose_library_path
            )
            hand = reference_pose_anchor(
                pose_id, "staff_hand", source.pose_library_path
            )
            root = reference_pose_root_anchor(pose_id, source.pose_library_path)
            first, _, _ = source._reference_pose_canvas_for_sample(pose_id)
            second, _, _ = source._reference_pose_canvas_for_sample(pose_id)
            first_counts[pose_id] = clear_authored_staff(first, tip, hand, root)
            second_counts[pose_id] = clear_authored_staff(second, tip, hand, root)
        self.assertEqual(first_counts, second_counts)
        self.assertTrue(all(count > 0 for count in first_counts.values()))

    def test_unsupported_surface_never_reaches_render_policy(self):
        _, baseline = self.apply_state(
            permission("world_state:default"),
            permission("prop:staff"),
        )
        _, source = self.apply_state(
            permission("world_state:default"),
            permission("prop:staff"),
            permission("effect:unsupported_calendar_glow"),
            permission("prop:unsupported_book"),
            permission("world_state:unsupported_room"),
        )
        policy = source.controller.permission_world_render_policy
        self.assertEqual(policy.visible_world_states, ("default",))
        self.assertEqual(policy.visible_effects, ())
        self.assertEqual(policy.visible_props, ("staff",))
        self.assertEqual(
            source.render_current_frame().cells,
            baseline.render_current_frame().cells,
        )

    def test_capability_mappings_do_not_implicitly_manage_intrinsic_surfaces(self):
        index = PermissionWorldCapabilityIndexV1.from_character_manifest(
            {
                "capabilities": [
                    {
                        "admission": "graph_admitted",
                        "mapping": {
                            "effect_ids": ["magic_effect"],
                            "prop_ids": ["staff"],
                        },
                    }
                ]
            }
        )
        self.assertEqual(index.world_state_ids, ())
        self.assertEqual(index.effect_ids, ())
        self.assertEqual(index.prop_ids, ())

    def test_no_authority_state_preserves_explicitly_managed_intrinsic_rendering(self):
        application, source = application_and_source()
        source.controller.state.pose_override_id = "front_idle"
        source.controller.state.pose_override_until = 100.0
        baseline = source.render_current_frame()

        application.apply(source.controller, 1_000_000)
        policy = source.controller.permission_world_render_policy
        self.assertIsNone(policy.source_state_sha256)
        self.assertEqual(policy.managed_props, ("staff",))
        self.assertEqual(source.render_current_frame().cells, baseline.cells)

    def test_production_manifest_empty_authority_preserves_staff_and_base_frame(self):
        source = ProceduralWizardFrameSource(180, 101, 24)
        source.controller.state.pose_override_id = "front_idle"
        source.controller.state.pose_override_until = 100.0
        baseline = source.render_current_frame()
        application = PerformanceApplication(
            "permission-production-regression",
            character_id=source.character_package.character_id,
            capability_manifest=derive_character_capability_manifest(
                source.character_package_path
            ),
        )
        application.accept_permission_world(authority_state())
        application.apply(source.controller, 1_000_000)

        policy = source.controller.permission_world_render_policy
        self.assertEqual(policy.managed_world_states, ())
        self.assertEqual(policy.managed_effects, ())
        self.assertEqual(policy.managed_props, ())
        self.assertIsNotNone(policy.source_state_sha256)
        self.assertEqual(source.render_current_frame().cells, baseline.cells)

    def test_simulation_is_labeled_and_cannot_control_production_projection(self):
        application, source = application_and_source()
        application.simulate_permission_world(
            permission("effect:magic_effect"),
            OBSERVED_MS,
        )
        application.apply(source.controller, 1_000_000)
        policy = source.controller.permission_world_render_policy
        self.assertEqual(policy.visible_effects, ())

        status = application.permission_world_snapshot(OBSERVED_MS)
        self.assertEqual(status["render_authority"]["source"], "authoritative")
        self.assertFalse(
            status["render_authority"]["simulation_can_control_projection"]
        )
        self.assertEqual(status["simulation_boundary"]["label"], "SIMULATION")
        self.assertFalse(
            status["simulation_boundary"]["applied_to_projected_frames"]
        )

    def test_captured_projection_render_is_deterministic_and_isolated(self):
        _, source = self.apply_state(
            permission("world_state:default"),
            permission("effect:magic_effect"),
            permission("prop:staff"),
        )
        source.controller.state.action = "magic_cast"
        source.controller.state.animation_clip_id = "cast_front"
        source.controller.state.pose_override_id = "magic_cast"
        source.controller.state.pose_override_until = 100.0
        snapshot = source.capture_render_state()
        self.assertIsInstance(snapshot, WizardRenderSnapshot)

        first = source.render_captured_frame(snapshot)
        source.controller.state.action = "idle"
        source.controller.set_permission_world_render_policy(
            copy.deepcopy(source.controller.permission_world_render_policy)
        )
        second = source.render_captured_frame(snapshot)
        self.assertEqual(first.cells, second.cells)

    def test_reduced_motion_keeps_effect_overlay_static(self):
        application, source = application_and_source()
        application.accept_permission_world(
            authority_state(permission("effect:magic_effect"))
        )
        policy = source.controller.permission_world_render_policy
        self.assertIsNone(policy)
        reduced = application.permission_world.project(
            evaluated_at_ms=OBSERVED_MS,
            motion_profile="reduced",
            capability_index=application.permission_world_capabilities,
        )
        from wizard_avatar.permission_world import PermissionWorldRenderPolicyV1

        policy = PermissionWorldRenderPolicyV1.from_projection(reduced)
        state = copy.deepcopy(source.current_state())
        state.action = "magic_cast"
        state.pose_override_id = "front_idle"
        state.pose_override_until = 100.0
        first_state = copy.deepcopy(state)
        second_state = copy.deepcopy(state)
        first_state.time_seconds = 1.0
        second_state.time_seconds = 9.0
        first = source.render_captured_frame(WizardRenderSnapshot(first_state, policy))
        second = source.render_captured_frame(WizardRenderSnapshot(second_state, policy))
        self.assertEqual(first.cells, second.cells)


if __name__ == "__main__":
    unittest.main()
