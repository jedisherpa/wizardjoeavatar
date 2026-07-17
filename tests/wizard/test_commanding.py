import unittest

from wizard_avatar.commanding import (
    CommandEnvelopeV1,
    CommandValidationError,
    OrderedCommandInbox,
)


def envelope(
    command_id="command-1",
    source_id="keyboard-1",
    source_kind="keyboard",
    source_sequence=1,
    source_epoch="epoch-a",
    kind="action",
    payload=None,
    ttl_ms=None,
    lease_id=None,
    priority_class="user",
    issued_tick=None,
):
    return CommandEnvelopeV1(
        schema_version=1,
        command_id=command_id,
        source_id=source_id,
        source_kind=source_kind,
        source_sequence=source_sequence,
        source_epoch=source_epoch,
        kind=kind,
        payload={} if payload is None else payload,
        ttl_ms=ttl_ms,
        lease_id=lease_id,
        priority_class=priority_class,
        issued_tick=issued_tick,
    )


class CommandEnvelopeTests(unittest.TestCase):
    def test_structured_parser_accepts_frozen_contract_and_sequence_alias(self):
        command = CommandEnvelopeV1.from_mapping(
            {
                "schema_version": 1,
                "command_id": "move-7",
                "source_id": "controller-a",
                "source_kind": "gamepad",
                "sequence": 7,
                "source_epoch": "session-2",
                "kind": "control_intent",
                "payload": {"move_x": 1.0, "held_actions": ["cast"]},
                "ttl_ms": 250,
                "lease_id": "lease-a",
                "priority_class": "user",
            }
        )
        self.assertEqual(command.source_sequence, 7)
        self.assertEqual(command.sequence, 7)
        self.assertEqual(command.payload["held_actions"], ("cast",))
        with self.assertRaises(TypeError):
            command.payload["move_x"] = 0.0

    def test_parser_rejects_unknown_coerced_and_incomplete_fields(self):
        base = {
            "schema_version": 1,
            "command_id": "move-1",
            "source_id": "controller-a",
            "source_kind": "gamepad",
            "source_sequence": 1,
            "source_epoch": "session-1",
            "kind": "control_intent",
            "payload": {},
            "ttl_ms": 250,
            "lease_id": "lease-a",
        }
        for changed in (
            {**base, "unknown": True},
            {**base, "schema_version": True},
            {**base, "source_sequence": "1"},
            {key: value for key, value in base.items() if key != "source_epoch"},
            {**base, "ttl_ms": 49},
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(CommandValidationError):
                    CommandEnvelopeV1.from_mapping(changed)

    def test_to_dict_returns_mutable_transport_copy(self):
        command = envelope(payload={"nested": {"values": [1, 2]}})
        result = command.to_dict()
        result["payload"]["nested"]["values"].append(3)
        self.assertEqual(command.payload["nested"]["values"], (1, 2))


class OrderedCommandInboxTests(unittest.TestCase):
    def test_same_tick_order_is_priority_then_received_order(self):
        inbox = OrderedCommandInbox("runtime-a")
        commands = [
            envelope("demo", "demo", "demo", 1, kind="path", priority_class="demo"),
            envelope("user-1", "user-a", "keyboard", 1),
            envelope("system", "runtime", "system", 1, kind="reset", priority_class="system"),
            envelope("user-2", "user-b", "gamepad", 1),
        ]
        for command in commands:
            self.assertEqual(inbox.submit(command, 4, 9).disposition, "accepted")
        due = inbox.pop_due(5)
        self.assertEqual([item.envelope.command_id for item in due], ["system", "user-1", "user-2", "demo"])
        self.assertEqual([item.priority for item in due], [100, 80, 80, 40])

    def test_duplicate_id_never_queues_twice(self):
        inbox = OrderedCommandInbox("runtime-a")
        command = envelope()
        accepted = inbox.submit(command, 0, 0)
        duplicate = inbox.submit(command, 0, 0)
        self.assertEqual(accepted.disposition, "accepted")
        self.assertEqual(duplicate.disposition, "duplicate")
        self.assertEqual(inbox.pending_count, 1)
        inbox.pop_due(1)
        applied = inbox.mark_applied(command.command_id, 1)
        self.assertEqual(applied.disposition, "applied")
        self.assertEqual(inbox.submit(command, 1, 1).disposition, "duplicate")

    def test_sequence_is_strict_per_source_epoch(self):
        inbox = OrderedCommandInbox("runtime-a")
        self.assertEqual(inbox.submit(envelope(source_sequence=4), 0, 0).disposition, "accepted")
        stale = inbox.submit(envelope("other-id", source_sequence=4), 0, 0)
        self.assertEqual(stale.disposition, "stale")
        self.assertEqual(stale.error_code, "stale_sequence")
        new_epoch = inbox.submit(envelope("new-epoch", source_sequence=1, source_epoch="epoch-b"), 0, 0)
        self.assertEqual(new_epoch.disposition, "accepted")

    def test_expired_command_and_future_horizon_do_not_mutate_queue(self):
        inbox = OrderedCommandInbox("runtime-a")
        expired = envelope(
            "expired",
            kind="control_intent",
            ttl_ms=50,
            lease_id="lease-a",
            issued_tick=0,
        )
        self.assertEqual(inbox.submit(expired, 4, 0).disposition, "expired")
        future = inbox.submit(envelope("future"), 4, 0, apply_tick=125)
        self.assertEqual(future.error_code, "apply_tick_too_far")
        self.assertEqual(inbox.pending_count, 0)

    def test_bounded_queue_rejects_without_advancing_watermark(self):
        inbox = OrderedCommandInbox("runtime-a", capacity=1, dedup_capacity=2)
        self.assertEqual(inbox.submit(envelope("first", source_sequence=1), 0, 0).disposition, "accepted")
        rejected = inbox.submit(envelope("second", source_sequence=2), 0, 0)
        self.assertEqual(rejected.error_code, "queue_full")
        self.assertEqual(inbox.source_watermark("keyboard-1", "epoch-a"), 1)
        inbox.pop_due(1)
        retry = inbox.submit(envelope("retry", source_sequence=2), 1, 1)
        self.assertEqual(retry.disposition, "accepted")

    def test_permutation_replay_has_stable_order(self):
        def run(order):
            inbox = OrderedCommandInbox("runtime-a")
            for index in order:
                inbox.submit(
                    envelope(
                        command_id="source-{}".format(index),
                        source_id="source-{}".format(index),
                        source_sequence=1,
                    ),
                    10,
                    10,
                )
            return [(item.priority, item.received_order, item.envelope.command_id) for item in inbox.pop_due(11)]

        first = run([1, 2, 3, 4])
        second = run([1, 2, 3, 4])
        self.assertEqual(first, second)

    def test_source_watermark_capacity_must_be_positive(self):
        for invalid in (0, -1, True, 1.5):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    OrderedCommandInbox("runtime-a", source_watermark_capacity=invalid)
                with self.assertRaises(ValueError):
                    OrderedCommandInbox("runtime-a", retired_source_epoch_capacity=invalid)

    def test_old_source_epochs_are_evicted_deterministically_and_fail_closed(self):
        inbox = OrderedCommandInbox(
            "runtime-a",
            capacity=4,
            dedup_capacity=8,
            source_watermark_capacity=2,
        )
        for index, epoch in enumerate(("epoch-a", "epoch-b", "epoch-c"), start=1):
            ack = inbox.submit(
                envelope(
                    command_id="command-{}".format(index),
                    source_id="controller-a",
                    source_sequence=1,
                    source_epoch=epoch,
                ),
                current_tick=index - 1,
                state_revision=index - 1,
            )
            self.assertEqual(ack.disposition, "accepted")
            inbox.pop_due(index)
            inbox.mark_applied(ack.command_id, index)

        self.assertIsNone(inbox.source_watermark("controller-a", "epoch-a"))
        self.assertEqual(inbox.source_watermark("controller-a", "epoch-b"), 1)
        self.assertEqual(inbox.source_watermark("controller-a", "epoch-c"), 1)
        self.assertEqual(inbox.source_watermark_count, 2)
        self.assertEqual(inbox.total_source_epoch_count, 3)
        self.assertEqual(inbox.source_watermark_eviction_count, 1)

        replay = inbox.submit(
            envelope(
                command_id="replayed-old-epoch",
                source_id="controller-a",
                source_sequence=99,
                source_epoch="epoch-a",
            ),
            current_tick=3,
            state_revision=3,
        )
        self.assertEqual(replay.disposition, "stale")
        self.assertEqual(replay.error_code, "retired_source_epoch")
        self.assertEqual(inbox.pending_count, 0)

    def test_pending_and_active_source_epochs_are_never_evicted(self):
        inbox = OrderedCommandInbox(
            "runtime-a",
            capacity=4,
            dedup_capacity=8,
            source_watermark_capacity=2,
        )
        first = inbox.submit(
            envelope("first", "controller-a", source_sequence=1, source_epoch="epoch-a"),
            0,
            0,
            apply_tick=10,
        )
        second = inbox.submit(
            envelope("second", "controller-a", source_sequence=1, source_epoch="epoch-b"),
            0,
            0,
            apply_tick=11,
        )
        self.assertEqual(first.disposition, "accepted")
        self.assertEqual(second.disposition, "accepted")

        blocked = inbox.submit(
            envelope("third", "controller-a", source_sequence=1, source_epoch="epoch-c"),
            0,
            0,
            apply_tick=12,
        )
        self.assertEqual(blocked.disposition, "rejected")
        self.assertEqual(blocked.error_code, "source_watermark_capacity")
        self.assertEqual(inbox.source_watermark_count, 2)
        self.assertEqual(inbox.source_watermark_eviction_count, 0)
        self.assertEqual(inbox.source_watermark_capacity_rejection_count, 1)

        inbox.pop_due(10)
        inbox.mark_applied("first", 1)
        retry = inbox.submit(
            envelope("third-retry", "controller-a", source_sequence=1, source_epoch="epoch-c"),
            10,
            1,
            apply_tick=12,
        )
        self.assertEqual(retry.disposition, "accepted")
        self.assertIsNone(inbox.source_watermark("controller-a", "epoch-a"))

    def test_active_sources_fill_capacity_and_require_a_fresh_epoch(self):
        inbox = OrderedCommandInbox(
            "runtime-a",
            capacity=4,
            dedup_capacity=8,
            source_watermark_capacity=2,
        )
        for source_id in ("controller-a", "controller-b"):
            accepted = inbox.submit(
                envelope(
                    command_id="{}-1".format(source_id),
                    source_id=source_id,
                    source_sequence=1,
                    source_epoch="epoch-a",
                ),
                0,
                0,
            )
            self.assertEqual(accepted.disposition, "accepted")
        inbox.pop_due(1)

        rejected = inbox.submit(
            envelope(
                command_id="controller-c-1",
                source_id="controller-c",
                source_sequence=1,
                source_epoch="epoch-a",
            ),
            1,
            1,
        )
        self.assertEqual(rejected.error_code, "source_watermark_capacity")
        self.assertEqual(inbox.source_watermark_count, 2)

    def test_retired_epoch_history_is_bounded_and_exhaustion_fails_closed(self):
        inbox = OrderedCommandInbox(
            "runtime-a",
            capacity=4,
            dedup_capacity=8,
            source_watermark_capacity=1,
            retired_source_epoch_capacity=1,
        )
        for index, epoch in enumerate(("epoch-a", "epoch-b"), start=1):
            ack = inbox.submit(
                envelope(
                    command_id="command-{}".format(index),
                    source_id="controller-a",
                    source_sequence=1,
                    source_epoch=epoch,
                ),
                index - 1,
                index - 1,
            )
            self.assertEqual(ack.disposition, "accepted")
            inbox.pop_due(index)
            inbox.mark_applied(ack.command_id, index)

        blocked = inbox.submit(
            envelope(
                command_id="command-3",
                source_id="controller-a",
                source_sequence=1,
                source_epoch="epoch-c",
            ),
            2,
            2,
        )
        self.assertEqual(blocked.disposition, "rejected")
        self.assertEqual(blocked.error_code, "source_watermark_capacity")
        self.assertEqual(inbox.source_watermark("controller-a", "epoch-b"), 1)
        self.assertEqual(inbox.source_retention_diagnostics["retired_source_epoch_count"], 1)

        stale = inbox.submit(
            envelope(
                command_id="replayed-epoch-a",
                source_id="controller-a",
                source_sequence=99,
                source_epoch="epoch-a",
            ),
            2,
            2,
        )
        self.assertEqual(stale.error_code, "retired_source_epoch")

    def test_watermark_retention_is_repeatably_deterministic(self):
        def run():
            inbox = OrderedCommandInbox(
                "runtime-a",
                capacity=4,
                dedup_capacity=8,
                source_watermark_capacity=2,
            )
            results = []
            for index, epoch in enumerate(("epoch-a", "epoch-b", "epoch-c", "epoch-a"), start=1):
                ack = inbox.submit(
                    envelope(
                        command_id="command-{}".format(index),
                        source_id="controller-a",
                        source_sequence=index,
                        source_epoch=epoch,
                    ),
                    index - 1,
                    index - 1,
                )
                results.append((ack.disposition, ack.error_code))
                if ack.disposition == "accepted":
                    inbox.pop_due(index)
                    inbox.mark_applied(ack.command_id, index)
            return results, inbox.source_retention_diagnostics

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
