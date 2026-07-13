import unittest

from wizard_avatar.runtime_metrics import RuntimeMetrics


class RuntimeMetricsTests(unittest.TestCase):
    def test_outgoing_sequences_are_monotonic_per_epoch(self):
        metrics = RuntimeMetrics("runtime-a")

        self.assertEqual([metrics.next_sequence(), metrics.next_sequence()], [0, 1])
        snapshot = metrics.snapshot()
        self.assertEqual(snapshot.runtime_epoch, "runtime-a")
        self.assertEqual(snapshot.next_outgoing_sequence, 2)
        self.assertEqual(snapshot.messages_sent, 2)

    def test_observation_classifies_gap_and_stale_sequence(self):
        metrics = RuntimeMetrics("runtime-a")

        first = metrics.observe_sequence("runtime-a", 0)
        second = metrics.observe_sequence("runtime-a", 1)
        gap = metrics.observe_sequence("runtime-a", 4)
        stale = metrics.observe_sequence("runtime-a", 4)

        self.assertEqual(first.disposition, "accepted")
        self.assertEqual(second.disposition, "accepted")
        self.assertEqual(gap.disposition, "gap")
        self.assertTrue(gap.resync_required)
        self.assertEqual(gap.expected_sequence, 2)
        self.assertEqual(gap.missing_count, 2)
        self.assertEqual(stale.disposition, "stale")
        self.assertFalse(stale.resync_required)
        snapshot = metrics.snapshot()
        self.assertEqual(snapshot.sequence_gaps, 1)
        self.assertEqual(snapshot.missing_messages, 2)
        self.assertEqual(snapshot.stale_messages, 1)

    def test_runtime_epoch_change_resets_expected_sequence_and_requests_resync(self):
        metrics = RuntimeMetrics("runtime-a")
        metrics.observe_sequence("runtime-a", 0)

        changed = metrics.observe_sequence("runtime-b", 9)
        following = metrics.observe_sequence("runtime-b", 10)

        self.assertEqual(changed.disposition, "epoch_changed")
        self.assertTrue(changed.resync_required)
        self.assertEqual(changed.previous_runtime_epoch, "runtime-a")
        self.assertEqual(following.disposition, "accepted")
        self.assertEqual(metrics.runtime_epoch, "runtime-b")
        self.assertEqual(metrics.snapshot().epoch_changes, 1)

    def test_resync_metrics_are_reasoned_and_serializable(self):
        metrics = RuntimeMetrics("runtime-a")
        metrics.record_resync("explicit")
        metrics.record_resync("sequence_gap")
        metrics.record_resync("sequence_gap")

        result = metrics.snapshot().to_dict()

        self.assertEqual(result["resync_count"], 3)
        self.assertEqual(result["resync_reasons"], {"explicit": 1, "sequence_gap": 2})
        result["resync_reasons"]["explicit"] = 99
        self.assertEqual(metrics.snapshot().resync_reasons["explicit"], 1)

    def test_metrics_reject_bool_negative_and_blank_values(self):
        with self.assertRaises(ValueError):
            RuntimeMetrics("")
        metrics = RuntimeMetrics("runtime-a")
        for epoch, sequence in (("", 0), ("runtime-a", -1), ("runtime-a", True)):
            with self.subTest(epoch=epoch, sequence=sequence):
                with self.assertRaises(ValueError):
                    metrics.observe_sequence(epoch, sequence)
        with self.assertRaises(ValueError):
            metrics.record_resync("")


if __name__ == "__main__":
    unittest.main()
