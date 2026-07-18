import copy
import json
import threading
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from wizard_avatar.artifact_hashing import canonical_json_v1, sha256_ref
from wizard_avatar.permission_world import (
    CapabilityPermissionV1,
    PermissionWorldCapabilityIndexV1,
    PermissionWorldCapabilityRequirementV1,
    PermissionWorldError,
    PermissionWorldRuntime,
    PermissionWorldStateV1,
    project_permission_world,
)


NOW_MS = 5_000
ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    ROOT / "wizard_avatar" / "definitions" / "permission_world_state_v1.schema.json"
)


def permission(
    capability_kind="calendar.read",
    posture="granted",
    required_scope_class="current_surface",
    granted_scope_class="current_surface",
    purpose_code="calendar_coordination",
    granted_at_ms=NOW_MS - 1_000,
    affected_surfaces=("companion.calendar", "wizard.calendar"),
    app_link_state="linked",
    expires_at_ms=NOW_MS + 1_000,
    revoked=False,
):
    return CapabilityPermissionV1(
        capability_kind=capability_kind,
        posture=posture,
        required_scope_class=required_scope_class,
        granted_scope_class=granted_scope_class,
        purpose_code=purpose_code,
        granted_at_ms=granted_at_ms,
        affected_surfaces=affected_surfaces,
        app_link_state=app_link_state,
        expires_at_ms=expires_at_ms,
        revoked=revoked,
    )


def state(
    *permissions,
    source_epoch="permission-source:7",
    observed_at_ms=NOW_MS - 100,
):
    return PermissionWorldStateV1.build(
        source_epoch=source_epoch,
        observed_at_ms=observed_at_ms,
        permissions=permissions,
    )


def projected(permission_value, motion_profile="full"):
    result = project_permission_world(
        state(permission_value),
        evaluated_at_ms=NOW_MS,
        motion_profile=motion_profile,
    )
    return result, result.affordances[0]


def capability_index():
    return PermissionWorldCapabilityIndexV1(
        world_state_ids=("default",),
        effect_ids=("magic_effect",),
        prop_ids=("staff",),
        requirements=(
            PermissionWorldCapabilityRequirementV1(
                "effect:magic_effect",
                "current_surface",
                "calendar_coordination",
            ),
            PermissionWorldCapabilityRequirementV1(
                "prop:staff",
                "current_surface",
                "calendar_coordination",
            ),
            PermissionWorldCapabilityRequirementV1(
                "world_state:default",
                "current_surface",
                "calendar_coordination",
            ),
        ),
    )


class PermissionWorldTests(unittest.TestCase):
    def test_bound_capability_without_scope_and_purpose_rule_is_rejected(self):
        with self.assertRaises(PermissionWorldError) as caught:
            PermissionWorldCapabilityIndexV1(prop_ids=("staff",))

        self.assertEqual(caught.exception.code, "permission_requirement_mismatch")

    def test_record_exposes_exact_content_free_permission_facts(self):
        record = permission()

        self.assertEqual(
            record.to_dict(),
            {
                "capability_kind": "calendar.read",
                "posture": "granted",
                "required_scope_class": "current_surface",
                "granted_scope_class": "current_surface",
                "purpose_code": "calendar_coordination",
                "granted_at_ms": 4_000,
                "affected_surfaces": ["companion.calendar", "wizard.calendar"],
                "app_link_state": "linked",
                "expires_at_ms": 6_000,
                "revoked": False,
            },
        )
        restored = CapabilityPermissionV1.from_mapping(record.to_dict())
        self.assertEqual(restored, record)
        self.assertIsInstance(restored.affected_surfaces, tuple)

    def test_permission_facts_are_canonical_and_temporally_consistent(self):
        with self.assertRaises(PermissionWorldError) as caught:
            permission(affected_surfaces=("wizard.calendar", "companion.calendar"))
        self.assertEqual(caught.exception.code, "invalid_order")

        with self.assertRaises(PermissionWorldError) as caught:
            permission(affected_surfaces=("wizard.calendar", "wizard.calendar"))
        self.assertEqual(caught.exception.code, "invalid_order")

        with self.assertRaises(PermissionWorldError) as caught:
            permission(affected_surfaces=("private_message",))
        self.assertEqual(caught.exception.code, "private_content")

        with self.assertRaises(PermissionWorldError) as caught:
            permission(granted_at_ms=None)
        self.assertEqual(caught.exception.code, "incomplete_grant_facts")

        with self.assertRaises(PermissionWorldError) as caught:
            permission(expires_at_ms=NOW_MS - 2_000)
        self.assertEqual(caught.exception.code, "invalid_time_range")

        with self.assertRaises(PermissionWorldError) as caught:
            state(permission(granted_at_ms=NOW_MS), observed_at_ms=NOW_MS - 1)
        self.assertEqual(caught.exception.code, "grant_after_observation")

    def test_valid_grant_is_the_only_available_affordance(self):
        result, affordance = projected(permission())

        self.assertEqual(affordance.permission_posture, "granted")
        self.assertEqual(affordance.availability, "available")
        self.assertEqual(affordance.visibility, "visible")
        self.assertEqual(affordance.reason_code, "permission_granted")
        self.assertEqual(affordance.expiry_class, "current")
        self.assertEqual(result.source_epoch, "permission-source:7")

    def test_revoke_and_expiry_fail_closed(self):
        _, revoked = projected(permission(revoked=True))
        self.assertEqual(
            (revoked.permission_posture, revoked.availability, revoked.reason_code),
            ("unavailable", "absent", "permission_revoked"),
        )

        _, expired = projected(permission(expires_at_ms=NOW_MS))
        self.assertEqual(expired.availability, "absent")
        self.assertEqual(expired.visibility, "hidden")
        self.assertEqual(expired.expiry_class, "expired")
        self.assertEqual(expired.reason_code, "permission_expired")

    def test_scope_and_link_boundaries_fail_closed(self):
        _, mismatched = projected(permission(granted_scope_class="linked_surface"))
        self.assertEqual(mismatched.availability, "absent")
        self.assertEqual(mismatched.reason_code, "scope_mismatch")

        _, unproven = projected(
            permission(granted_scope_class=None, granted_at_ms=None)
        )
        self.assertEqual(unproven.reason_code, "scope_unproven")

        link_reasons = {
            "unlinked": "app_unlinked",
            "revoked": "app_link_revoked",
            "unknown": "app_link_unknown",
        }
        for link_state, reason in link_reasons.items():
            with self.subTest(link_state=link_state):
                _, affordance = projected(permission(app_link_state=link_state))
                self.assertEqual(affordance.availability, "absent")
                self.assertEqual(affordance.reason_code, reason)

    def test_decision_postures_project_without_fabricating_a_grant(self):
        expected = {
            "denied": ("absent", "hidden", "permission_denied"),
            "unavailable": ("absent", "hidden", "permission_unavailable"),
            "unknown": ("absent", "hidden", "permission_unknown"),
            "promptable": ("requestable", "visible", "permission_promptable"),
        }
        for posture, outcome in expected.items():
            with self.subTest(posture=posture):
                _, affordance = projected(
                    permission(
                        posture=posture,
                        granted_scope_class=None,
                        granted_at_ms=None,
                    )
                )
                self.assertEqual(
                    (affordance.availability, affordance.visibility, affordance.reason_code),
                    outcome,
                )
                self.assertNotEqual(affordance.permission_posture, "granted")

    def test_motion_profile_is_validated_and_remains_semantic(self):
        for profile in ("full", "reduced", "still"):
            with self.subTest(profile=profile):
                result, affordance = projected(permission(), profile)
                self.assertEqual(result.motion_profile, profile)
                self.assertEqual(affordance.motion_profile, profile)

        with self.assertRaises(PermissionWorldError) as caught:
            projected(permission(), "cinematic")
        self.assertEqual(caught.exception.code, "invalid_enum")

    def test_character_projection_binds_only_real_world_effect_and_prop_semantics(self):
        permission_state = state(
            permission("world_state:default"),
            permission("effect:magic_effect"),
            permission("prop:staff"),
            permission("effect:calendar_badge"),
            permission("calendar.read"),
        )
        result = project_permission_world(
            permission_state,
            evaluated_at_ms=NOW_MS,
            motion_profile="reduced",
            capability_index=capability_index(),
        )
        affordances = {item.capability_kind: item for item in result.affordances}

        self.assertEqual(result.visible_world_states, ("default",))
        self.assertEqual(result.visible_effects, ("magic_effect",))
        self.assertEqual(result.visible_props, ("staff",))
        self.assertEqual(
            affordances["effect:magic_effect"].to_dict(),
            {
                "capability_kind": "effect:magic_effect",
                "permission_posture": "granted",
                "scope_class": "current_surface",
                "purpose_class": "calendar_coordination",
                "observed_at_ms": 4_900,
                "granted_at_ms": 4_000,
                "expires_at_ms": 6_000,
                "affected_surface_classes": [
                    "companion.calendar",
                    "wizard.calendar",
                ],
                "revocation_behavior": "remove_immediately",
                "surface_class": "effect",
                "surface_id": "magic_effect",
                "support_status": "supported",
                "expiry_class": "current",
                "availability": "available",
                "visibility": "visible",
                "reason_code": "permission_granted",
                "motion_profile": "reduced",
            },
        )
        self.assertEqual(
            affordances["effect:calendar_badge"].reason_code,
            "character_capability_absent",
        )
        self.assertEqual(affordances["effect:calendar_badge"].visibility, "hidden")
        self.assertEqual(affordances["calendar.read"].reason_code, "unsupported_capability_kind")
        self.assertEqual(affordances["calendar.read"].support_status, "unsupported_kind")

    def test_runtime_projection_is_redacted_and_removes_revoked_affordance(self):
        runtime = PermissionWorldRuntime()
        granted = state(permission("effect:magic_effect"), observed_at_ms=NOW_MS)
        runtime.accept(granted)
        visible = runtime.project(
            evaluated_at_ms=NOW_MS,
            motion_profile="full",
            capability_index=capability_index(),
        ).to_runtime_dict()

        self.assertEqual(visible["visible_surfaces"]["effects"], ["magic_effect"])
        self.assertNotIn("source_epoch", visible)
        self.assertRegex(visible["source_epoch_sha256"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(visible["affordances"][0]["purpose_class"], "calendar_coordination")

        revoked = state(
            permission("effect:magic_effect", revoked=True),
            observed_at_ms=NOW_MS + 1,
        )
        runtime.accept(revoked)
        removed = runtime.project(
            evaluated_at_ms=NOW_MS + 1,
            motion_profile="still",
            capability_index=capability_index(),
        ).to_runtime_dict()

        self.assertEqual(removed["visible_surfaces"]["effects"], [])
        self.assertEqual(removed["affordances"][0]["reason_code"], "permission_revoked")
        self.assertEqual(removed["affordances"][0]["motion_profile"], "still")

    def test_state_and_projection_are_frozen_and_deterministically_hashed(self):
        first_state = state(
            permission("files.write"),
            permission("calendar.read"),
        )
        second_state = state(
            permission("calendar.read"),
            permission("files.write"),
        )
        self.assertEqual(first_state.to_dict(), second_state.to_dict())
        self.assertEqual(first_state.state_sha256, second_state.state_sha256)
        self.assertEqual(
            first_state.state_sha256,
            sha256_ref(
                canonical_json_v1(
                    {
                        key: value
                        for key, value in first_state.to_dict().items()
                        if key != "state_sha256"
                    }
                )
            ),
        )

        first = project_permission_world(
            first_state, evaluated_at_ms=NOW_MS, motion_profile="reduced"
        )
        second = project_permission_world(
            second_state, evaluated_at_ms=NOW_MS, motion_profile="reduced"
        )
        self.assertEqual(first.canonical_json(), second.canonical_json())
        identity = copy.deepcopy(first.to_dict())
        identity.pop("projection_sha256")
        self.assertEqual(
            first.projection_sha256, sha256_ref(canonical_json_v1(identity))
        )

        with self.assertRaises(FrozenInstanceError):
            first.motion_profile = "full"
        with self.assertRaises(FrozenInstanceError):
            first.affordances[0].availability = "absent"

    def test_exact_boundary_rejects_private_or_unknown_fields(self):
        value = state(permission()).to_dict()
        value["permissions"][0]["prompt"] = "private-canary"
        with self.assertRaises(PermissionWorldError) as caught:
            PermissionWorldStateV1.from_mapping(value)
        self.assertEqual(caught.exception.code, "unknown_field")
        self.assertNotIn("private-canary", str(caught.exception))

        with self.assertRaises(PermissionWorldError) as caught:
            permission(capability_kind="secret_token")
        self.assertEqual(caught.exception.code, "private_content")

        raw = json.dumps(state(permission()).to_dict())
        restored = PermissionWorldStateV1.from_json(raw)
        self.assertEqual(restored.to_dict(), state(permission()).to_dict())

        tampered = state(permission()).to_dict()
        tampered["permissions"][0]["purpose_code"] = "different_purpose"
        with self.assertRaises(PermissionWorldError) as caught:
            PermissionWorldStateV1.from_mapping(tampered)
        self.assertEqual(caught.exception.code, "hash_mismatch")

    def test_json_and_collection_bounds_fail_closed(self):
        with self.assertRaises(PermissionWorldError) as caught:
            PermissionWorldStateV1.from_json(
                '{"schema_version":1,"schema_version":1}'
            )
        self.assertEqual(caught.exception.code, "duplicate_json_key")

        with self.assertRaises(PermissionWorldError) as caught:
            PermissionWorldStateV1.from_json("{" + (" " * (64 * 1024)))
        self.assertEqual(caught.exception.code, "body_too_large")

        with self.assertRaises(PermissionWorldError) as caught:
            permission(
                affected_surfaces=tuple(
                    "surface:{:03d}".format(index) for index in range(65)
                )
            )
        self.assertEqual(caught.exception.code, "too_many_items")

        with self.assertRaises(PermissionWorldError) as caught:
            PermissionWorldStateV1.build(
                source_epoch="permission-source:7",
                observed_at_ms=NOW_MS,
                permissions=[permission()] * 257,
            )
        self.assertEqual(caught.exception.code, "too_many_items")

    def test_projection_contains_no_private_or_executable_fields(self):
        result, _ = projected(permission())
        encoded = result.to_dict()
        forbidden = {
            "animation",
            "app_id",
            "command",
            "content",
            "device_id",
            "granted_scope_class",
            "path",
            "prompt",
            "receipt",
            "secret",
            "token",
        }

        def keys(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield key
                    yield from keys(item)
            elif isinstance(value, list):
                for item in value:
                    yield from keys(item)

        self.assertTrue(forbidden.isdisjoint(set(keys(encoded))))
        self.assertIn("expires_at_ms", set(keys(encoded)))


class PermissionWorldRuntimeTests(unittest.TestCase):
    def test_runtime_capacity_configuration_is_strictly_bounded(self):
        for invalid in (True, 0, 1025):
            with self.subTest(invalid=invalid):
                with self.assertRaises(PermissionWorldError) as caught:
                    PermissionWorldRuntime(retired_epoch_capacity=invalid)
                self.assertEqual(caught.exception.code, "invalid_capacity")

    def test_accepts_only_strictly_newer_observations_in_one_epoch(self):
        runtime = PermissionWorldRuntime()
        first = state(permission(), observed_at_ms=NOW_MS - 100)
        second = state(
            permission(expires_at_ms=NOW_MS + 2_000),
            observed_at_ms=NOW_MS,
        )

        self.assertEqual(runtime.accept(first), first)
        self.assertEqual(runtime.accept_json(second.canonical_json()), second)
        self.assertEqual(runtime.current_state, second)

        with self.assertRaises(PermissionWorldError) as caught:
            runtime.accept(second)
        self.assertEqual(caught.exception.code, "replayed_state")

        with self.assertRaises(PermissionWorldError) as caught:
            runtime.accept(first)
        self.assertEqual(caught.exception.code, "stale_observation")

        conflict = state(
            permission(posture="denied", granted_scope_class=None, granted_at_ms=None),
            observed_at_ms=NOW_MS,
        )
        with self.assertRaises(PermissionWorldError) as caught:
            runtime.accept_mapping(conflict.to_dict())
        self.assertEqual(caught.exception.code, "observation_conflict")

    def test_epoch_rollover_retires_old_epochs_and_is_globally_monotonic(self):
        runtime = PermissionWorldRuntime()
        old = state(permission(), source_epoch="permission-source:7")
        runtime.accept(old)

        stale_new_epoch = state(
            permission(),
            source_epoch="permission-source:8",
            observed_at_ms=old.observed_at_ms,
        )
        with self.assertRaises(PermissionWorldError) as caught:
            runtime.accept(stale_new_epoch)
        self.assertEqual(caught.exception.code, "stale_observation")

        current = state(
            permission(),
            source_epoch="permission-source:8",
            observed_at_ms=old.observed_at_ms + 1,
        )
        runtime.accept(current)

        retired_replay = state(
            permission(),
            source_epoch="permission-source:7",
            observed_at_ms=current.observed_at_ms + 1,
        )
        with self.assertRaises(PermissionWorldError) as caught:
            runtime.accept(retired_replay)
        self.assertEqual(caught.exception.code, "retired_source_epoch")
        self.assertEqual(runtime.current_state, current)

    def test_epoch_retention_is_bounded_and_fails_closed_at_capacity(self):
        runtime = PermissionWorldRuntime(retired_epoch_capacity=1)
        runtime.accept(
            state(permission(), source_epoch="permission-source:1", observed_at_ms=4_900)
        )
        second = state(
            permission(), source_epoch="permission-source:2", observed_at_ms=5_000
        )
        runtime.accept(second)

        with self.assertRaises(PermissionWorldError) as caught:
            runtime.accept(
                state(
                    permission(),
                    source_epoch="permission-source:3",
                    observed_at_ms=5_001,
                )
            )
        self.assertEqual(caught.exception.code, "retired_epoch_capacity")
        self.assertEqual(runtime.current_state, second)
        self.assertEqual(runtime.diagnostics()["retired_epoch_count"], 1)

    def test_tampered_state_is_rejected_before_it_can_replace_current_truth(self):
        runtime = PermissionWorldRuntime()
        accepted = state(permission())
        runtime.accept(accepted)
        tampered = accepted.to_dict()
        tampered["permissions"][0]["revoked"] = True

        with self.assertRaises(PermissionWorldError) as caught:
            runtime.accept(tampered)
        self.assertEqual(caught.exception.code, "hash_mismatch")
        self.assertEqual(runtime.current_state, accepted)
        self.assertEqual(runtime.diagnostics()["tamper_rejection_count"], 1)

    def test_update_writer_is_owned_by_one_thread(self):
        runtime = PermissionWorldRuntime()
        runtime.accept(state(permission()))
        rejection_codes = []

        def update_from_other_writer():
            try:
                runtime.accept(
                    state(permission(), observed_at_ms=NOW_MS + 1)
                )
            except PermissionWorldError as exc:
                rejection_codes.append(exc.code)

        writer = threading.Thread(target=update_from_other_writer)
        writer.start()
        writer.join()

        self.assertEqual(rejection_codes, ["single_writer_violation"])
        self.assertEqual(runtime.diagnostics()["accepted_count"], 1)

    def test_projection_uses_current_state_and_only_explicit_evaluation_inputs(self):
        runtime = PermissionWorldRuntime()
        with self.assertRaises(PermissionWorldError) as caught:
            runtime.project(evaluated_at_ms=NOW_MS, motion_profile="full")
        self.assertEqual(caught.exception.code, "state_unavailable")

        accepted = state(permission())
        runtime.accept(accepted)
        first = runtime.project(evaluated_at_ms=NOW_MS, motion_profile="still")
        second = runtime.project(evaluated_at_ms=NOW_MS, motion_profile="still")
        self.assertEqual(first.canonical_json(), second.canonical_json())
        self.assertEqual(first.source_state_sha256, accepted.state_sha256)

    def test_diagnostics_are_bounded_content_free_and_do_not_expose_facts(self):
        runtime = PermissionWorldRuntime(retired_epoch_capacity=2)
        accepted = state(permission())
        runtime.accept(accepted)
        with self.assertRaises(PermissionWorldError):
            runtime.accept(accepted)
        diagnostics = runtime.diagnostics()
        encoded = json.dumps(diagnostics, sort_keys=True)

        self.assertEqual(diagnostics["status"], "ready")
        self.assertEqual(diagnostics["permission_count"], 1)
        self.assertEqual(diagnostics["accepted_count"], 1)
        self.assertEqual(diagnostics["replay_rejection_count"], 1)
        self.assertEqual(diagnostics["retired_epoch_capacity"], 2)
        self.assertRegex(
            diagnostics["active_source_epoch_sha256"], r"^sha256:[0-9a-f]{64}$"
        )
        for private_fact in (
            "permission-source:7",
            "calendar.read",
            "calendar_coordination",
            "companion.calendar",
            "wizard.calendar",
        ):
            self.assertNotIn(private_fact, encoded)
        for forbidden_key in ("command", "payload", "prompt", "token"):
            self.assertNotIn(forbidden_key, diagnostics)


class PermissionWorldSchemaTests(unittest.TestCase):
    def test_schema_is_closed_bounded_and_matches_the_state_record(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        permission_schema = schema["$defs"]["permission"]
        permission_fields = {
            "capability_kind",
            "posture",
            "required_scope_class",
            "granted_scope_class",
            "purpose_code",
            "granted_at_ms",
            "affected_surfaces",
            "app_link_state",
            "expires_at_ms",
            "revoked",
        }

        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(permission_schema["additionalProperties"])
        self.assertEqual(set(permission_schema["required"]), permission_fields)
        self.assertEqual(set(permission_schema["properties"]), permission_fields)
        self.assertEqual(schema["properties"]["permissions"]["maxItems"], 256)
        self.assertTrue(schema["properties"]["permissions"]["uniqueItems"])
        surfaces = permission_schema["properties"]["affected_surfaces"]
        self.assertTrue(surfaces["uniqueItems"])
        self.assertEqual(surfaces["maxItems"], 64)
        self.assertEqual(schema["$defs"]["time"]["maximum"], 9007199254740991)

    def test_schema_has_no_private_or_executable_payload_surface(self):
        serialized = SCHEMA_PATH.read_text(encoding="utf-8").lower()
        for forbidden_field in (
            '"app_id"',
            '"command"',
            '"credential"',
            '"payload"',
            '"prompt"',
            '"receipt"',
            '"secret"',
            '"token"',
        ):
            self.assertNotIn(forbidden_field, serialized)


if __name__ == "__main__":
    unittest.main()
