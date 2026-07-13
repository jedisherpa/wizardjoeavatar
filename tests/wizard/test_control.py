import itertools
import math
import unittest

from wizard_avatar.commanding import CommandEnvelopeV1
from wizard_avatar.control import (
    ControlArbiter,
    ControlIntentV1,
    ControlValidationError,
    intent_from_envelope,
)


def control_envelope(
    command_id="control-1",
    source_id="keyboard-a",
    source_kind="keyboard",
    source_sequence=1,
    source_epoch="epoch-a",
    lease_id="lease-a",
    ttl_ms=250,
    priority_class="user",
    payload=None,
):
    return CommandEnvelopeV1(
        schema_version=1,
        command_id=command_id,
        source_id=source_id,
        source_kind=source_kind,
        source_sequence=source_sequence,
        source_epoch=source_epoch,
        kind="control_intent",
        payload={} if payload is None else payload,
        ttl_ms=ttl_ms,
        lease_id=lease_id,
        priority_class=priority_class,
    )


class ControlIntentTests(unittest.TestCase):
    def test_diagonal_input_is_normalized_without_losing_direction(self):
        intent = ControlIntentV1(move_x=1.0, move_z=1.0, speed_mode="run")
        self.assertAlmostEqual(intent.planar_magnitude, 1.0)
        self.assertAlmostEqual(intent.move_x, 1.0 / math.sqrt(2.0))
        self.assertTrue(intent.run)
        self.assertFalse(intent.is_neutral)

    def test_parser_is_strict_and_facing_vector_is_coherent(self):
        intent = ControlIntentV1.from_mapping(
            {"face_x": 0.5, "face_z": 0.5, "mobility_request": "takeoff"}
        )
        self.assertFalse(intent.is_neutral)
        with self.assertRaises(ControlValidationError):
            ControlIntentV1.from_mapping({"face_x": 1.0})
        with self.assertRaises(ControlValidationError):
            ControlIntentV1.from_mapping({"move_x": "1.0"})
        with self.assertRaises(ControlValidationError):
            ControlIntentV1.from_mapping({"unknown": 1})

    def test_intent_from_envelope_uses_structured_payload(self):
        command = control_envelope(payload={"move_x": 0.5, "held_actions": ["cast"]})
        intent = intent_from_envelope(command)
        self.assertEqual(intent.move_x, 0.5)
        self.assertEqual(intent.held_actions, ("cast",))


class ControlArbiterTests(unittest.TestCase):
    def test_acquire_refresh_and_tick_expiry(self):
        arbiter = ControlArbiter()
        intent = ControlIntentV1(move_x=1.0)
        first = arbiter.submit(control_envelope(), intent, accepted_tick=10)
        self.assertTrue(first.accepted)
        self.assertEqual(first.active_lease.expires_tick, 25)
        refreshed = arbiter.submit(
            control_envelope(command_id="control-2", source_sequence=2),
            ControlIntentV1(move_z=1.0),
            accepted_tick=12,
        )
        self.assertTrue(refreshed.accepted)
        self.assertEqual(refreshed.reason, "lease refreshed")
        self.assertGreater(refreshed.active_lease.generation, first.active_lease.generation)
        self.assertFalse(arbiter.expire(26).accepted)
        expired = arbiter.expire(27)
        self.assertTrue(expired.accepted)
        self.assertTrue(expired.released)
        self.assertIsNone(arbiter.active_lease)

    def test_live_monotonic_deadline_expires_after_scheduler_stall(self):
        arbiter = ControlArbiter()
        arbiter.submit(
            control_envelope(ttl_ms=1000),
            ControlIntentV1(move_x=1.0),
            accepted_tick=0,
            accepted_monotonic_ns=1_000_000_000,
        )
        self.assertEqual(arbiter.active_lease.expires_tick, 15)
        decision = arbiter.expire(current_tick=1, monotonic_ns=1_250_000_000)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.disposition, "expired")

    def test_stale_sequence_does_not_change_active_lease(self):
        arbiter = ControlArbiter()
        arbiter.submit(control_envelope(source_sequence=4), ControlIntentV1(move_x=1.0), 0)
        active = arbiter.active_lease
        stale = arbiter.submit(
            control_envelope(command_id="stale", source_sequence=4),
            ControlIntentV1(move_z=1.0),
            1,
        )
        self.assertFalse(stale.accepted)
        self.assertEqual(stale.disposition, "stale")
        self.assertIs(arbiter.active_lease, active)

    def test_equal_priority_controller_cannot_steal_lease(self):
        arbiter = ControlArbiter()
        arbiter.submit(control_envelope(), ControlIntentV1(move_x=1.0), 0)
        rejected = arbiter.submit(
            control_envelope(
                command_id="other",
                source_id="gamepad-b",
                source_kind="gamepad",
                source_epoch="epoch-b",
                lease_id="lease-b",
            ),
            ControlIntentV1(move_z=1.0),
            1,
        )
        self.assertFalse(rejected.accepted)
        self.assertEqual(rejected.disposition, "unauthorized")
        self.assertEqual(arbiter.active_lease.source_id, "keyboard-a")

    def test_higher_priority_preempts_and_priority_claims_are_validated(self):
        arbiter = ControlArbiter()
        demo = control_envelope(
            command_id="demo",
            source_id="demo-a",
            source_kind="demo",
            source_epoch="demo-epoch",
            lease_id="demo-lease",
            priority_class="demo",
        )
        arbiter.submit(demo, ControlIntentV1(move_x=1.0), 0)
        user = arbiter.submit(control_envelope(), ControlIntentV1(move_z=1.0), 1)
        self.assertTrue(user.preempted)
        self.assertEqual(user.active_lease.priority, 60)

        forged = control_envelope(
            command_id="forged",
            source_id="forged",
            source_kind="remote",
            source_epoch="forged-epoch",
            lease_id="forged-lease",
            priority_class="system",
        )
        decision = arbiter.submit(forged, ControlIntentV1(move_x=-1.0), 2)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.disposition, "unauthorized")

    def test_reconnect_epoch_retires_old_epoch(self):
        arbiter = ControlArbiter()
        arbiter.submit(control_envelope(), ControlIntentV1(move_x=1.0), 0)
        reconnect = arbiter.submit(
            control_envelope(
                command_id="new-session",
                source_sequence=1,
                source_epoch="epoch-b",
                lease_id="lease-b",
            ),
            ControlIntentV1(move_z=1.0),
            1,
        )
        self.assertTrue(reconnect.accepted)
        self.assertEqual(arbiter.active_lease.source_epoch, "epoch-b")
        stale_epoch = arbiter.submit(
            control_envelope(command_id="old-session", source_sequence=2),
            ControlIntentV1(move_x=-1.0),
            2,
        )
        self.assertFalse(stale_epoch.accepted)
        self.assertEqual(stale_epoch.disposition, "stale")

    def test_zero_intent_disconnect_and_clear_release_only_owner(self):
        arbiter = ControlArbiter()
        arbiter.submit(control_envelope(), ControlIntentV1(move_x=1.0), 0)
        ignored = arbiter.disconnect("someone-else", "epoch-x")
        self.assertFalse(ignored.accepted)
        release = arbiter.submit(
            control_envelope(command_id="release", source_sequence=2),
            ControlIntentV1.neutral(),
            1,
        )
        self.assertTrue(release.released)
        self.assertIsNone(arbiter.active_lease)

        arbiter.submit(
            control_envelope(command_id="again", source_sequence=3),
            ControlIntentV1(move_x=1.0),
            2,
        )
        disconnected = arbiter.disconnect("keyboard-a", "epoch-a")
        self.assertTrue(disconnected.released)
        self.assertFalse(arbiter.clear().accepted)

    def test_priority_permutations_always_finish_with_system_owner(self):
        contenders = [
            (
                control_envelope(
                    "demo",
                    "demo",
                    "demo",
                    1,
                    "demo-epoch",
                    "demo-lease",
                    priority_class="demo",
                ),
                ControlIntentV1(move_x=1.0),
            ),
            (control_envelope(), ControlIntentV1(move_z=1.0)),
            (
                control_envelope(
                    "system",
                    "system",
                    "system",
                    1,
                    "system-epoch",
                    "system-lease",
                    priority_class="system",
                ),
                ControlIntentV1(move_x=-1.0),
            ),
        ]
        for order in itertools.permutations(contenders):
            arbiter = ControlArbiter()
            for index, (command, intent) in enumerate(order):
                arbiter.submit(command, intent, index)
            self.assertEqual(arbiter.active_lease.source_id, "system")
            self.assertEqual(arbiter.active_lease.priority, 100)


if __name__ == "__main__":
    unittest.main()
