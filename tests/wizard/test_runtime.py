import hashlib
import unittest

from wizard_avatar.commanding import CommandEnvelopeV1
from wizard_avatar.runtime import (
    ACCUMULATOR_TICK_UNITS,
    AvatarRuntime,
    ReplayLog,
    canonical_json_bytes,
    canonical_sha256,
)


def command(command_id, source_sequence, kind="action", priority_class="user"):
    source_kind = "system" if priority_class == "system" else "keyboard"
    return CommandEnvelopeV1(
        schema_version=1,
        command_id=command_id,
        source_id="source-{}".format(command_id),
        source_kind=source_kind,
        source_sequence=source_sequence,
        source_epoch="epoch-a",
        kind=kind,
        payload={},
        priority_class=priority_class,
    )


def counter_reducer(state, due, tick, dt):
    state["ticks"] += 1
    state["last_tick"] = tick
    state["dt_values"].append(dt)
    state["commands"].extend(item.envelope.command_id for item in due)
    return state


def make_runtime(replay_log=None):
    return AvatarRuntime(
        initial_state={"ticks": 0, "last_tick": 0, "dt_values": [], "commands": []},
        reducer=counter_reducer,
        runtime_epoch="runtime-a",
        presentation_factory=lambda state, tick: {"tick": tick, "ticks": state["ticks"]},
        replay_log=replay_log,
    )


class CanonicalHashTests(unittest.TestCase):
    def test_mapping_order_does_not_change_hash(self):
        left = {"b": [2, 3], "a": 1.25}
        right = {"a": 1.25, "b": [2, 3]}
        self.assertEqual(canonical_json_bytes(left), canonical_json_bytes(right))
        self.assertEqual(canonical_sha256(left), canonical_sha256(right))

    def test_float_identity_is_exact_and_nonfinite_is_rejected(self):
        self.assertNotEqual(canonical_sha256({"x": 0.0}), canonical_sha256({"x": -0.0}))
        with self.assertRaises(ValueError):
            canonical_sha256({"x": float("nan")})


class AvatarRuntimeTests(unittest.TestCase):
    def test_step_tick_uses_only_exact_sixtieth_delta(self):
        runtime = make_runtime()
        for _ in range(10_000):
            runtime.step_tick()
        snapshot = runtime.current_snapshot()
        self.assertEqual(snapshot.simulation_tick, 10_000)
        self.assertEqual(snapshot.state_revision, 10_000)
        self.assertEqual(set(snapshot.current["dt_values"]), {1.0 / 60.0})

    def test_integer_accumulator_preserves_half_tick_remainder(self):
        runtime = make_runtime()
        result = runtime.advance_elapsed_ns(41_666_667)
        self.assertEqual(result.steps, 2)
        self.assertEqual(result.dropped_ticks, 0)
        self.assertGreater(runtime.clock.accumulator_units, ACCUMULATOR_TICK_UNITS // 2)
        self.assertLess(runtime.clock.accumulator_units, ACCUMULATOR_TICK_UNITS // 2 + 100)

    def test_render_schedules_reach_identical_tick_hash(self):
        hashes = {}
        for fps in (15, 24, 30):
            runtime = make_runtime()
            for frame in range(fps * 2 + 1):
                runtime.advance_to(round(frame * 1_000_000_000 / fps))
            hashes[fps] = runtime.current_snapshot().state_hash
            self.assertEqual(runtime.current_snapshot().simulation_tick, 120)
            self.assertEqual(runtime.clock.dropped_simulation_seconds, 0.0)
        self.assertEqual(len(set(hashes.values())), 1)

    def test_two_second_stall_is_bounded_and_accounted(self):
        runtime = make_runtime()
        runtime.advance_to(0)
        result = runtime.advance_to(2_000_000_000)
        self.assertEqual(result.steps, 8)
        self.assertEqual(result.dropped_ticks, 112)
        self.assertEqual(result.snapshot.simulation_tick, 8)
        self.assertAlmostEqual(runtime.clock.dropped_simulation_seconds, 112 / 60.0)
        self.assertEqual(result.events[0].event_type, "runtime.catch_up_dropped")

    def test_runtime_events_retain_a_bounded_tail_without_losing_current_result(self):
        runtime = AvatarRuntime(
            initial_state={"ticks": 0, "last_tick": 0, "dt_values": [], "commands": []},
            reducer=counter_reducer,
            runtime_epoch="runtime-a",
            event_capacity=3,
        )
        for _ in range(10):
            result = runtime.advance_elapsed_ns(2_000_000_000)
            self.assertEqual(len(result.events), 1)
            self.assertEqual(result.events[0].event_type, "runtime.catch_up_dropped")

        self.assertEqual(len(runtime.drain_events()), 3)
        self.assertEqual(
            runtime.event_retention_diagnostics,
            {
                "event_capacity": 3,
                "retained_event_count": 0,
                "evicted_event_count": 7,
                "is_truncated": True,
            },
        )

    def test_runtime_event_capacity_must_be_positive(self):
        for invalid in (0, -1, True, 1.5):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "event_capacity"):
                    AvatarRuntime({}, lambda state, _due, _tick, _dt: state, "runtime-a", event_capacity=invalid)

    def test_clock_rejects_backwards_time(self):
        runtime = make_runtime()
        runtime.advance_to(100)
        with self.assertRaises(ValueError):
            runtime.advance_to(99)

    def test_snapshots_are_recursively_immutable_and_render_reads_do_not_step(self):
        runtime = make_runtime()
        before = runtime.current_snapshot()
        runtime.step_tick()
        snapshot = runtime.current_snapshot()
        self.assertEqual(before.current["ticks"], 0)
        self.assertEqual(snapshot.current["ticks"], 1)
        with self.assertRaises(TypeError):
            snapshot.current["ticks"] = 7
        with self.assertRaises(AttributeError):
            snapshot.current["dt_values"].append(2.0)
        with self.assertRaises(TypeError):
            snapshot.presentation["tick"] = 10
        self.assertIs(runtime.current_snapshot(), runtime.current_snapshot())
        self.assertEqual(runtime.current_snapshot().simulation_tick, 1)

    def test_commands_apply_on_tick_boundary_in_queue_order(self):
        runtime = make_runtime()
        runtime.enqueue(command("user", 1))
        runtime.enqueue(command("reset", 1, kind="reset", priority_class="system"))
        before = runtime.current_snapshot()
        self.assertEqual(before.current["commands"], ())
        after = runtime.step_tick()
        self.assertEqual(after.current["commands"], ("reset", "user"))
        self.assertEqual(runtime.inbox.ack_for("user").disposition, "applied")
        self.assertEqual(runtime.inbox.ack_for("reset").state_revision, 1)

    def test_reducer_failure_does_not_commit_tick_or_state(self):
        def fail(state, due, tick, dt):
            state["ticks"] = 999
            raise RuntimeError("boom")

        runtime = AvatarRuntime({"ticks": 0}, fail, "runtime-a")
        with self.assertRaises(RuntimeError):
            runtime.step_tick()
        self.assertEqual(runtime.current_snapshot().simulation_tick, 0)
        self.assertEqual(runtime.current_snapshot().current["ticks"], 0)

    def test_replay_is_byte_identical_for_same_commands(self):
        def run():
            replay = ReplayLog({"schema_version": 1, "seed": 7, "tick_rate": 60})
            runtime = make_runtime(replay)
            runtime.enqueue(command("first", 1))
            runtime.step_tick()
            runtime.enqueue(command("second", 1))
            runtime.step_tick()
            runtime.step_tick()
            return replay.to_ndjson_bytes(), replay.sha256()

        first_bytes, first_hash = run()
        second_bytes, second_hash = run()
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_hash, hashlib.sha256(first_bytes).hexdigest())
        self.assertIn(b'"record_type":"tick_state"', first_bytes)

    def test_idle_replay_uses_one_state_checkpoint_per_second(self):
        replay = ReplayLog({"schema_version": 1, "tick_rate": 60})
        runtime = make_runtime(replay)
        for _ in range(120):
            runtime.step_tick()

        tick_records = [
            record for record in replay.records if record["record_type"] == "tick_state"
        ]
        self.assertEqual([record["simulation_tick"] for record in tick_records], [60, 120])


class ReplayLogRetentionTests(unittest.TestCase):
    def test_retention_capacity_must_be_a_positive_integer(self):
        for invalid in (0, -1, True, 1.5):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    ReplayLog({"schema_version": 1}, max_records=invalid)

    def test_retains_header_and_bounded_tail_with_explicit_diagnostics(self):
        replay = ReplayLog({"schema_version": 1, "seed": 7}, max_records=3)
        for tick in range(1, 6):
            replay.append("tick_state", tick, {"tick": tick})

        self.assertEqual(replay.total_record_count, 6)
        self.assertEqual(replay.record_count, 6)
        self.assertEqual(replay.retained_record_count, 3)
        self.assertEqual(replay.evicted_record_count, 3)
        self.assertTrue(replay.is_truncated)
        self.assertEqual(
            [record["record_sequence"] for record in replay.records],
            [0, 4, 5],
        )
        self.assertEqual(replay.first_retained_sequence, 0)
        self.assertEqual(
            replay.retention_diagnostics,
            {
                "max_records": 3,
                "total_record_count": 6,
                "retained_record_count": 3,
                "evicted_record_count": 3,
                "is_truncated": True,
                "retained_sequence_ranges": ((0, 0), (4, 5)),
            },
        )

    def test_full_history_and_retained_window_hashes_are_deterministic(self):
        bounded = ReplayLog({"schema_version": 1}, max_records=3)
        complete = ReplayLog({"schema_version": 1}, max_records=10)
        for tick in range(1, 6):
            payload = {"tick": tick, "value": tick * 3}
            bounded.append("tick_state", tick, payload)
            complete.append("tick_state", tick, payload)

        retained_chunks = tuple(bounded.iter_ndjson_bytes())
        self.assertEqual(bounded.sha256(), complete.sha256())
        self.assertEqual(bounded.to_ndjson_bytes(), b"".join(retained_chunks))
        self.assertEqual(
            bounded.retained_sha256(),
            hashlib.sha256(bounded.to_ndjson_bytes()).hexdigest(),
        )

        repeated = ReplayLog({"schema_version": 1}, max_records=3)
        for tick in range(1, 6):
            repeated.append("tick_state", tick, {"tick": tick, "value": tick * 3})
        self.assertEqual(repeated.sha256(), bounded.sha256())
        self.assertEqual(repeated.retained_sha256(), bounded.retained_sha256())
        self.assertEqual(repeated.to_ndjson_bytes(), bounded.to_ndjson_bytes())


if __name__ == "__main__":
    unittest.main()
