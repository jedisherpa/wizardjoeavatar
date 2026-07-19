import asyncio
import threading
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCellFrame, WizardCommand, WizardState
from wizard_avatar.protocol import TAG_DELTA, decode_frame, encode_frame
from wizard_avatar.permission_world import CapabilityPermissionV1, PermissionWorldStateV1
from wizard_avatar.stream import WizardFrameHub, WizardSubscriber


_REAL_ASYNCIO_SLEEP = asyncio.sleep


class _FrameLoopComplete(Exception):
    pass


class _FakeMonotonicClock:
    def __init__(self):
        self.now = 0.0
        self.sleep_delays = []

    def perf_counter(self):
        return self.now

    def perf_counter_ns(self):
        return round(self.now * 1_000_000_000)

    def advance(self, seconds):
        self.now += seconds

    async def sleep(self, delay):
        self.sleep_delays.append(delay)
        self.advance(delay)
        await _REAL_ASYNCIO_SLEEP(0)


class _CheapController:
    def __init__(self):
        self.state = WizardState(character_id="deadline-policy-test")

    def advance_tick(self):
        self.state.simulation_tick += 1
        self.state.state_revision += 1
        self.state.time_seconds = self.state.simulation_tick / 60.0

    def current_state(self):
        return self.state


class _CheapFrameSource:
    fps = 10
    cols = 1
    rows = 1

    def __init__(self, clock, render_durations):
        self.clock = clock
        self.render_durations = render_durations
        self.controller = _CheapController()
        self.character_package = SimpleNamespace(character_id="deadline-policy-test")
        self.diagnostics = SimpleNamespace(extra={})
        self.frame_started_at = []
        self.simulation_times = []

    def current_state(self):
        return self.controller.current_state()

    async def next_encoded_frame(self, *_args, **_kwargs):
        frame_index = len(self.frame_started_at)
        if frame_index == len(self.render_durations):
            raise _FrameLoopComplete
        self.frame_started_at.append(self.clock.now)
        self.simulation_times.append(self.current_state().time_seconds)
        self.clock.advance(self.render_durations[frame_index])
        frame = WizardCellFrame(
            cols=1,
            rows=1,
            frame_index=frame_index,
            cells=b"\x00\x00\x00\x00",
            raw_size=4,
        )
        return b"cheap-frame", frame


class _FailingFrameSource(_CheapFrameSource):
    def __init__(self):
        super().__init__(_FakeMonotonicClock(), ())

    async def next_encoded_frame(self, *_args, **_kwargs):
        raise RuntimeError("render failed")


class StreamHubTests(unittest.IsolatedAsyncioTestCase):
    async def test_retained_replay_digest_stays_off_the_frame_diagnostics_path(self):
        hub = WizardFrameHub(_CheapFrameSource(_FakeMonotonicClock(), ()))
        with mock.patch.object(
            hub.replay_log,
            "retained_sha256",
            wraps=hub.replay_log.retained_sha256,
        ) as retained_sha256:
            frame_diagnostics = hub.diagnostics_extra(include_replay_digest=False)
            requested_diagnostics = hub.diagnostics_extra(include_replay_digest=True)

        self.assertNotIn("replay_retained_sha256", frame_diagnostics)
        self.assertIn("replay_retained_sha256", requested_diagnostics)
        self.assertEqual(retained_sha256.call_count, 1)

    async def test_media_score_preparation_runs_off_the_event_loop(self):
        hub = WizardFrameHub(ProceduralWizardFrameSource(fps=1))
        event_loop_thread = threading.get_ident()
        preparation_threads = []

        def prepare(_snapshot):
            preparation_threads.append(threading.get_ident())

        with (
            mock.patch.object(hub.performance, "prepare_snapshot", side_effect=prepare),
            mock.patch.object(hub.performance, "accept_snapshot", return_value="ack"),
        ):
            result = await hub.accept_media_session(object(), receipt_monotonic_us=1)

        try:
            self.assertEqual(result, "ack")
            self.assertEqual(len(preparation_threads), 1)
            self.assertNotEqual(preparation_threads[0], event_loop_thread)
        finally:
            await hub.stop()

    async def test_background_failure_is_observed_and_reported(self):
        hub = WizardFrameHub(_FailingFrameSource())
        await hub.start()
        task = hub._task
        self.assertIsNotNone(task)
        with self.assertRaisesRegex(RuntimeError, "render failed"):
            await task
        await asyncio.sleep(0)
        self.assertEqual(hub.task_error_code, "frame_hub_failed")
        self.assertEqual(hub.diagnostics_extra()["frame_hub_failure_count"], 1)
        await hub.stop()

    async def test_commands_can_contend_with_frame_loop(self):
        hub = WizardFrameHub(ProceduralWizardFrameSource(fps=60))
        subscriber = await hub.subscribe()
        try:
            poses = ("front_idle", "back_idle", "profile_left", "profile_right")
            for _ in range(4):
                for pose_id in poses:
                    result = await asyncio.wait_for(
                        hub.apply_command(
                            WizardCommand("pose", {"pose_id": pose_id, "duration_ms": 300})
                        ),
                        timeout=1.0,
                    )
                    self.assertTrue(result.ok, result.message)
            self.assertIs(hub._lock_loop, asyncio.get_running_loop())
        finally:
            hub.unsubscribe(subscriber)
            await hub.stop()

    async def test_slow_render_does_not_hold_runtime_lock(self):
        source = ProceduralWizardFrameSource(fps=24)
        hub = WizardFrameHub(source)
        render_started = threading.Event()
        release_render = threading.Event()
        original_render = source.render_captured_candidate_sync

        def slow_render(state, codec):
            render_started.set()
            release_render.wait(timeout=2.0)
            return original_render(state, codec)

        with mock.patch.object(
            source,
            "render_captured_candidate_sync",
            side_effect=slow_render,
        ):
            await hub.start()
            self.assertTrue(await asyncio.to_thread(render_started.wait, 1.0))
            try:
                binding = await asyncio.wait_for(
                    hub.performance_binding(),
                    timeout=0.2,
                )
                self.assertEqual(binding["wizard_runtime_epoch"], hub.runtime_epoch)
            finally:
                release_render.set()
                await hub.stop()

    async def test_permission_change_discards_in_flight_granted_frame(self):
        source = ProceduralWizardFrameSource(fps=24)
        source.controller.state.pose_override_id = "front_idle"
        source.controller.state.pose_override_until = 100.0
        hub = WizardFrameHub(source)
        observed_at_ms = 2_000_000_000_000

        def permission(posture, *, revoked=False):
            granted = posture == "granted"
            has_grant = granted or revoked
            return CapabilityPermissionV1(
                capability_kind="prop:memory_notebook",
                posture=posture,
                required_scope_class="current_character",
                granted_scope_class="current_character" if has_grant else None,
                purpose_code="conversation_continuity",
                granted_at_ms=observed_at_ms - 1 if has_grant else None,
                affected_surfaces=("wizard.stage",),
                app_link_state="not_required",
                expires_at_ms=observed_at_ms + 60_000 if has_grant else None,
                revoked=revoked,
            )

        grant = PermissionWorldStateV1.build(
            source_epoch="permission-source:stream-race",
            observed_at_ms=observed_at_ms,
            permissions=(permission("granted"),),
        )
        revoke = PermissionWorldStateV1.build(
            source_epoch="permission-source:stream-race",
            observed_at_ms=observed_at_ms + 1,
            permissions=(permission("denied", revoked=True),),
        )

        await hub.accept_permission_world(grant)
        render_started = threading.Event()
        release_render = threading.Event()
        rendered_policies = []
        original_render = source.render_captured_candidate_sync

        def blocked_render(state, codec):
            rendered_policies.append(state.permission_world.visible_props)
            if not render_started.is_set():
                render_started.set()
                release_render.wait(timeout=2.0)
            return original_render(state, codec)

        with mock.patch.object(
            source,
            "render_captured_candidate_sync",
            side_effect=blocked_render,
        ):
            self.assertTrue(await asyncio.to_thread(render_started.wait, 1.0))
            published_before = hub._published_frames
            await hub.accept_permission_world(revoke)
            release_render.set()
            deadline = asyncio.get_running_loop().time() + 1.0
            while hub._published_frames == published_before:
                self.assertLess(asyncio.get_running_loop().time(), deadline)
                await asyncio.sleep(0.01)

        try:
            self.assertEqual(rendered_policies[0], ("memory_notebook",))
            self.assertIn((), rendered_policies[1:])
            self.assertGreaterEqual(hub._stale_render_discard_count, 1)
            self.assertEqual(
                source.controller.permission_world_render_policy.visible_props,
                (),
            )
        finally:
            release_render.set()
            await hub.stop()

    async def test_permission_expiry_discards_in_flight_granted_frame(self):
        source = ProceduralWizardFrameSource(fps=24)
        hub = WizardFrameHub(source)
        observed_at_ms = time.time_ns() // 1_000_000
        state = PermissionWorldStateV1.build(
            source_epoch="permission-source:stream-expiry",
            observed_at_ms=observed_at_ms,
            permissions=(
                CapabilityPermissionV1(
                    capability_kind="prop:memory_notebook",
                    posture="granted",
                    required_scope_class="current_character",
                    granted_scope_class="current_character",
                    purpose_code="conversation_continuity",
                    granted_at_ms=observed_at_ms - 1,
                    affected_surfaces=("wizard.stage",),
                    app_link_state="not_required",
                    expires_at_ms=observed_at_ms + 200,
                    revoked=False,
                ),
            ),
        )
        await hub.accept_permission_world(state)
        render_started = threading.Event()
        release_render = threading.Event()
        rendered_policies = []
        original_render = source.render_captured_candidate_sync

        def blocked_render(render_state, codec):
            rendered_policies.append(render_state.permission_world.visible_props)
            if not render_started.is_set():
                render_started.set()
                release_render.wait(timeout=2.0)
            return original_render(render_state, codec)

        with mock.patch.object(
            source,
            "render_captured_candidate_sync",
            side_effect=blocked_render,
        ):
            self.assertTrue(await asyncio.to_thread(render_started.wait, 1.0))
            published_before = hub._published_frames
            await asyncio.sleep(0.25)
            release_render.set()
            deadline = asyncio.get_running_loop().time() + 1.0
            while hub._published_frames == published_before:
                self.assertLess(asyncio.get_running_loop().time(), deadline)
                await asyncio.sleep(0.01)

        try:
            self.assertEqual(rendered_policies[0], ("memory_notebook",))
            self.assertIn((), rendered_policies[1:])
            self.assertGreaterEqual(hub._stale_render_discard_count, 1)
            self.assertEqual(
                source.controller.permission_world_render_policy.visible_props,
                (),
            )
        finally:
            release_render.set()
            await hub.stop()

    async def test_authoritative_state_change_discards_candidate_without_advancing_commit(self):
        source = ProceduralWizardFrameSource(fps=24)
        hub = WizardFrameHub(source)
        render_started = threading.Event()
        release_render = threading.Event()
        original_render = source.render_captured_candidate_sync
        render_count = 0

        def blocked_first_render(render_state, codec):
            nonlocal render_count
            render_count += 1
            if render_count == 1:
                render_started.set()
                release_render.wait(timeout=2.0)
            return original_render(render_state, codec)

        with mock.patch.object(
            source,
            "render_captured_candidate_sync",
            side_effect=blocked_first_render,
        ):
            await hub.start()
            self.assertTrue(await asyncio.to_thread(render_started.wait, 1.0))
            async with hub._current_lock():
                # Exercise the legacy immediate-mutation hazard explicitly:
                # the state revision is unchanged, so only the canonical state
                # hash can prevent the obsolete raster from committing.
                source.controller.state.expression = "happy"
            release_render.set()
            deadline = asyncio.get_running_loop().time() + 2.0
            while hub._published_frames < 1:
                self.assertLess(asyncio.get_running_loop().time(), deadline)
                await asyncio.sleep(0.01)

        try:
            self.assertGreaterEqual(hub._stale_render_discard_count, 1)
            self.assertEqual(hub._latest_frame.frame_index, 0)
            self.assertEqual(source.frame_index, 1)
            self.assertEqual(source.presentation_generation, 1)
            self.assertEqual(source._last_presentation_state.pose_id, "front_idle")
        finally:
            release_render.set()
            await hub.stop()

    async def test_subscribers_receive_decodable_contiguous_frames(self):
        hub = WizardFrameHub(ProceduralWizardFrameSource(fps=24))
        first = await hub.subscribe()
        second = await hub.subscribe()
        try:
            messages_a = [await asyncio.wait_for(first.queue.get(), timeout=1.0) for _ in range(4)]
            messages_b = [await asyncio.wait_for(second.queue.get(), timeout=1.0) for _ in range(4)]
            prev_a = None
            prev_b = None
            frames_a = []
            frames_b = []
            for message_a, message_b in zip(messages_a, messages_b):
                index_a, prev_a = decode_frame(message_a, prev_a)
                index_b, prev_b = decode_frame(message_b, prev_b)
                frames_a.append(index_a)
                frames_b.append(index_b)
                self.assertEqual(prev_a, prev_b)
            self.assertEqual(frames_a, frames_b)
            self.assertEqual(frames_a, list(range(frames_a[0], frames_a[0] + 4)))
        finally:
            hub.unsubscribe(first)
            hub.unsubscribe(second)
            await hub.stop()

    async def test_resync_requests_one_global_keyframe_publication(self):
        hub = WizardFrameHub(ProceduralWizardFrameSource(fps=24))
        recovering = await hub.subscribe()
        current = await hub.subscribe()
        try:
            await asyncio.wait_for(recovering.queue.get(), timeout=1.0)
            await asyncio.wait_for(current.queue.get(), timeout=1.0)
            await hub.enqueue_keyframe(recovering)
            recovered_message = await asyncio.wait_for(
                recovering.queue.get(),
                timeout=1.0,
            )
            recovered_index, decoded = decode_frame(recovered_message, None)
            while True:
                current_message = await asyncio.wait_for(
                    current.queue.get(),
                    timeout=1.0,
                )
                current_index = int.from_bytes(current_message[:4], "big")
                if current_index >= recovered_index:
                    break

            self.assertEqual(current_index, recovered_index)
            self.assertEqual(current_message, recovered_message)
            self.assertNotEqual(recovered_message[4], TAG_DELTA)
            self.assertEqual(len(decoded), 240 * 135 * 4)
        finally:
            hub.unsubscribe(recovering)
            hub.unsubscribe(current)
            await hub.stop()

    async def test_queue_overflow_clears_stale_delta_without_private_reencode(self):
        hub = WizardFrameHub(_CheapFrameSource(_FakeMonotonicClock(), ()))
        subscriber = WizardSubscriber(asyncio.Queue(maxsize=1))
        hub._subscribers.add(subscriber)
        base = bytes(40)
        first = bytearray(base)
        first[0:4] = b"\x01\x01\x01\x01"
        second = bytearray(first)
        second[4:8] = b"\x02\x02\x02\x02"
        stale_delta = encode_frame(bytes(first), base, 1).message
        overflowing_delta = encode_frame(bytes(second), bytes(first), 2).message
        self.assertEqual(stale_delta[4], TAG_DELTA)
        self.assertEqual(overflowing_delta[4], TAG_DELTA)
        subscriber.queue.put_nowait(stale_delta)

        with mock.patch("wizard_avatar.stream.encode_keyframe") as encode_keyframe:
            hub._publish(overflowing_delta)

        self.assertTrue(subscriber.queue.empty())
        self.assertTrue(hub._force_keyframe)
        self.assertEqual(subscriber.dropped_frame_count, 1)
        self.assertEqual(subscriber.resync_count, 1)
        self.assertEqual(hub._queue_drops, 1)
        self.assertEqual(hub._resync_count, 1)
        encode_keyframe.assert_not_called()

    async def test_overflow_rejoins_atomic_global_keyframe_and_trace_truth(self):
        clock = _FakeMonotonicClock()
        source = ProceduralWizardFrameSource(cols=80, rows=45, fps=10)
        hub = WizardFrameHub(source)
        slow = WizardSubscriber(asyncio.Queue(maxsize=1))
        current = WizardSubscriber(asyncio.Queue(maxsize=8))
        hub._subscribers.update((slow, current))
        original_render = source.render_captured_candidate_sync

        def render_three_frames(render_state, codec):
            if source.frame_index == 3:
                raise _FrameLoopComplete
            return original_render(render_state, codec)

        try:
            with (
                mock.patch("wizard_avatar.stream.time.perf_counter", clock.perf_counter),
                mock.patch(
                    "wizard_avatar.stream.time.perf_counter_ns",
                    clock.perf_counter_ns,
                ),
                mock.patch("wizard_avatar.stream.asyncio.sleep", clock.sleep),
                mock.patch.object(
                    source,
                    "render_captured_candidate_sync",
                    side_effect=render_three_frames,
                ),
            ):
                with self.assertRaises(_FrameLoopComplete):
                    await hub._run()

            current_messages = [current.queue.get_nowait() for _ in range(3)]
            recovered_message = slow.queue.get_nowait()
            self.assertEqual(recovered_message, current_messages[-1])
            self.assertNotEqual(recovered_message[4], TAG_DELTA)

            recovered_index, recovered_cells = decode_frame(recovered_message, None)
            current_cells = None
            current_index = -1
            for message in current_messages:
                current_index, current_cells = decode_frame(message, current_cells)
            self.assertEqual(recovered_index, current_index)
            self.assertEqual(recovered_cells, current_cells)

            trace = hub._animation_truth_trace[-1]
            self.assertEqual(trace.frame_index, recovered_index)
            self.assertEqual(trace.codec_tag, recovered_message[4])
            self.assertEqual(trace.encoded_size, len(recovered_message))
            self.assertTrue(trace.is_keyframe)
            self.assertEqual(hub._latest_frame.frame_index, recovered_index)
            self.assertEqual(hub._latest_frame.codec_tag, trace.codec_tag)
            self.assertEqual(hub._latest_frame.encoded_size, trace.encoded_size)
            self.assertTrue(hub._latest_frame.is_keyframe)
            self.assertEqual(hub._source_hash_history[-1]["codec_tag"], trace.codec_tag)
            self.assertGreaterEqual(hub._forced_keyframe_count, 1)
            self.assertEqual(hub._queue_drops, 1)
            self.assertEqual(slow.resync_count, 1)
        finally:
            hub._subscribers.clear()
            await hub.stop()

    async def test_frame_loop_does_not_replay_missed_deadlines(self):
        for iteration in range(100):
            with self.subTest(iteration=iteration):
                await self._assert_deadline_policy()

    async def _assert_deadline_policy(self):
        clock = _FakeMonotonicClock()
        render_durations = (0.02, 0.12, 0.02, 0.02)
        source = _CheapFrameSource(clock, render_durations)
        hub = WizardFrameHub(source)
        with (
            mock.patch("wizard_avatar.stream.time.perf_counter", clock.perf_counter),
            mock.patch(
                "wizard_avatar.stream.time.perf_counter_ns",
                clock.perf_counter_ns,
            ),
            mock.patch("wizard_avatar.stream.asyncio.sleep", clock.sleep),
        ):
            with self.assertRaises(_FrameLoopComplete):
                await hub._run()

        frame_interval = 1.0 / source.fps
        frame_gaps = [
            later - earlier
            for earlier, later in zip(source.frame_started_at, source.frame_started_at[1:])
        ]
        scheduled_sleeps = [delay for delay in clock.sleep_delays if delay > 0.001]

        self.assertEqual(hub._published_frames, len(render_durations))
        self.assertEqual(hub._schedule_overruns, 1, "exactly one deadline was missed")
        self.assertTrue(
            all(gap >= frame_interval - 1e-9 for gap in frame_gaps),
            "a missed deadline caused a replay burst",
        )
        self.assertTrue(
            all(
                simulation <= started + 1e-9
                for simulation, started in zip(
                    source.simulation_times,
                    source.frame_started_at,
                )
            ),
            "simulation advanced beyond the fake monotonic clock",
        )
        simulation_gaps = [
            later - earlier
            for earlier, later in zip(
                source.simulation_times,
                source.simulation_times[1:],
            )
        ]
        self.assertTrue(
            all(gap <= frame_interval + 1e-9 for gap in simulation_gaps),
            "a missed deadline skipped presentation-rate simulation states",
        )
        self.assertGreater(
            hub._presentation_clock_dropped_ns,
            0,
            "the dropped presentation-clock debt was not measured",
        )
        self.assertAlmostEqual(
            scheduled_sleeps[1],
            frame_interval,
            places=9,
            msg="the post-overrun deadline was not aligned into the future",
        )


if __name__ == "__main__":
    unittest.main()
