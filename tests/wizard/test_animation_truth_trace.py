import asyncio
import hashlib
import threading
import unittest
from unittest import mock

from wizard_avatar.animation_trace import (
    ANIMATION_TRUTH_TRACE_CAPACITY,
    AnimationTruthTraceV1,
    transformed_anchor,
)
from wizard_avatar.compositor import CellCanvas
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.pose_compositor import blit_pose_scaled
from wizard_avatar.server import create_app
from wizard_avatar.stream import WizardFrameHub

from tests.wizard.test_media_session_server import asgi_request


class AnimationTruthGeometryTests(unittest.TestCase):
    def test_cast_markers_are_presented_once_in_order_at_24_fps(self):
        source = ProceduralWizardFrameSource(cols=96, rows=54, fps=24)
        result = source.apply_command_sync(
            WizardCommand("action", {"action": "magic_cast", "duration_ms": 5000})
        )
        self.assertTrue(result.ok, result.message)

        traces = []
        presentation_accumulator = 0
        for _ in range(60):
            source.advance_simulation(1 / 60)
            presentation_accumulator += 24
            if presentation_accumulator < 60:
                continue
            presentation_accumulator -= 60
            candidate = source.render_captured_candidate_sync(
                source.capture_render_state()
            )
            source.commit_render_candidate(candidate)
            traces.append(candidate.animation_truth)

        expected = [
            ("action_commit", 6),
            ("action_effect", 7),
            ("action_recoverable", 14),
            ("action_settled", 17),
        ]
        events = [
            (trace, event)
            for trace in traces
            for event in trace.presentation_marker_events
        ]
        self.assertEqual(
            [(event.marker_id, event.animation_authored_frame) for _, event in events],
            expected,
        )
        self.assertEqual(
            [
                marker
                for trace in traces
                for marker in trace.active_markers
                if marker.startswith("action_")
            ],
            [],
        )
        self.assertEqual(
            [event.simulation_tick for _, event in events],
            sorted(event.simulation_tick for _, event in events),
        )
        effect_trace = next(
            trace
            for trace, event in events
            if event.marker_id == "action_effect"
        )
        settled_trace = next(
            trace
            for trace, event in events
            if event.marker_id == "action_settled"
        )
        self.assertEqual(effect_trace.effect_phase, "stroke")
        self.assertEqual(effect_trace.effect_intensity, 1.0)
        self.assertEqual(settled_trace.effect_phase, "inactive")
        self.assertEqual(settled_trace.effect_intensity, 0.0)
        self.assertEqual(
            AnimationTruthTraceV1.from_mapping(effect_trace.to_mapping()),
            effect_trace,
        )

    def test_stale_candidate_does_not_consume_latched_marker(self):
        source = ProceduralWizardFrameSource(cols=96, rows=54, fps=24)
        result = source.apply_command_sync(
            WizardCommand("action", {"action": "magic_cast", "duration_ms": 5000})
        )
        self.assertTrue(result.ok, result.message)

        while "action_commit" not in source.current_state().animation_active_markers:
            source.advance_simulation(1 / 60)
        stale = source.render_captured_candidate_sync(source.capture_render_state())
        self.assertEqual(
            [event.marker_id for event in stale.animation_truth.presentation_marker_events],
            ["action_commit"],
        )

        source.advance_simulation(1 / 60)
        with self.assertRaisesRegex(ValueError, "stale render candidate authoritative state"):
            source.commit_render_candidate(stale)

        accepted = source.render_captured_candidate_sync(source.capture_render_state())
        source.commit_render_candidate(accepted)
        self.assertEqual(
            [event.marker_id for event in accepted.animation_truth.presentation_marker_events],
            ["action_commit"],
        )

        following = source.render_captured_candidate_sync(source.capture_render_state())
        source.commit_render_candidate(following)
        self.assertEqual(following.animation_truth.presentation_marker_events, ())

    def test_v1_trace_without_presentation_events_remains_readable(self):
        source = ProceduralWizardFrameSource(cols=96, rows=54, fps=24)
        candidate = source.render_captured_candidate_sync(source.capture_render_state())
        mapping = candidate.animation_truth.to_mapping()
        del mapping["presentation_marker_events"]

        decoded = AnimationTruthTraceV1.from_mapping(mapping)

        self.assertEqual(decoded.presentation_marker_events, ())

    def test_raster_anchor_span_matches_nearest_neighbor_blit(self):
        local = CellCanvas(5, 5)
        local.set(3, 2, "#", (1, 2, 3), "anchor")
        stage = CellCanvas(40, 30)
        root_local = (2, 4)
        root_stage = (17.4, 22.2)
        scale = 1.25
        horizontal_scale = 1.18

        blit_pose_scaled(
            stage,
            local,
            root_local,
            root_stage,
            scale,
            horizontal_scale,
        )
        _, span = transformed_anchor(
            root_local=root_local,
            root_stage=root_stage,
            anchor_local=(3, 2),
            local_size=(local.width, local.height),
            scale=scale,
            horizontal_scale=horizontal_scale,
        )

        self.assertIsNotNone(span)
        rendered = {
            (x, y)
            for y in range(stage.height)
            for x in range(stage.width)
            if stage.get(x, y) is not None
        }
        expected = {
            (x, y)
            for y in range(span.min_y, span.max_y + 1)
            for x in range(span.min_x, span.max_x + 1)
        }
        self.assertEqual(rendered, expected)

    def test_candidate_preserves_exact_authoritative_sample_and_frame_hash(self):
        source = ProceduralWizardFrameSource(cols=96, rows=54, fps=24)
        state = source.current_state()
        state.locomotion = "walking"
        state.animation_node_id = "ground_walk"
        state.animation_clip_id = "walk_front"
        state.animation_transition_phase = "stable"
        state.walk_phase = 0.56
        source.resolve_authoritative_animation_state()

        snapshot = source.capture_render_state()
        candidate = source.render_captured_candidate_sync(snapshot, "adaptive")
        trace = candidate.animation_truth
        evaluation = source.animation_graph.evaluate_clip_phase(
            state.animation_clip_id,
            state.walk_phase + state.animation_phase_offset,
        )

        self.assertEqual(trace.simulation_tick, state.simulation_tick)
        self.assertEqual(trace.state_revision, state.state_revision)
        self.assertEqual(trace.frame_index, candidate.frame_index)
        self.assertEqual(trace.authoritative_state_sha256, snapshot.authoritative_state_sha256)
        self.assertEqual(trace.authored_pose_id, state.pose_id)
        self.assertEqual(trace.animation_sample_index, evaluation.sample_index)
        self.assertEqual(trace.animation_sample_frame, evaluation.sample_frame)
        self.assertEqual(trace.animation_authored_frame, evaluation.authored_frame)
        self.assertEqual(trace.animation_phase_numerator, evaluation.clip_phase_numerator)
        self.assertEqual(trace.animation_phase_denominator, evaluation.clip_phase_denominator)
        self.assertEqual(trace.support_contact, evaluation.support_contact)
        self.assertEqual(trace.planted_anchor, evaluation.planted_anchor)
        self.assertEqual(trace.active_markers, evaluation.active_markers)
        self.assertEqual(trace.frame_sha256, hashlib.sha256(candidate.cells).hexdigest())
        self.assertEqual(trace.codec_tag, candidate.codec_tag)
        self.assertEqual(trace.encoded_size, candidate.encoded_size)
        self.assertEqual(trace.changed_cells, candidate.changed_cells)
        self.assertEqual(trace.is_keyframe, candidate.is_keyframe)
        self.assertIsNotNone(trace.planted_anchor_local)
        self.assertIsNotNone(trace.planted_anchor_stage)
        self.assertIsNotNone(trace.planted_anchor_raster_span)


class AnimationTruthHubTests(unittest.IsolatedAsyncioTestCase):
    async def test_server_exposes_in_memory_trace_contract(self):
        app = create_app(
            source=ProceduralWizardFrameSource(cols=96, rows=54, fps=24),
            companion_mode=False,
        )
        try:
            status, payload = await asgi_request(
                app,
                "GET",
                "/api/avatar/wizard/animation-trace",
            )
            self.assertEqual(status, 200)
            self.assertEqual(payload["schema"], "animation_truth_trace_v1")
            self.assertEqual(payload["capacity"], ANIMATION_TRUTH_TRACE_CAPACITY)
            self.assertEqual(payload["count"], len(payload["records"]))
        finally:
            await app.state.frame_hub.stop()

    async def test_hub_exposes_one_atomic_record_per_accepted_candidate(self):
        source = ProceduralWizardFrameSource(cols=96, rows=54, fps=24)
        hub = WizardFrameHub(source)
        subscriber = await hub.subscribe()
        try:
            for _ in range(3):
                await asyncio.wait_for(subscriber.queue.get(), timeout=2.0)
            snapshot = await hub.animation_truth_trace_snapshot()

            self.assertEqual(snapshot["schema"], "animation_truth_trace_v1")
            self.assertEqual(snapshot["capacity"], ANIMATION_TRUTH_TRACE_CAPACITY)
            self.assertEqual(snapshot["count"], hub._published_frames)
            indexes = [record["frame_index"] for record in snapshot["records"]]
            self.assertEqual(indexes, list(range(indexes[0], indexes[0] + len(indexes))))
            self.assertEqual(
                snapshot["records"][-1]["frame_sha256"],
                hashlib.sha256(hub._latest_frame.cells).hexdigest(),
            )
        finally:
            hub.unsubscribe(subscriber)
            await hub.stop()

    async def test_stale_worker_candidate_is_not_emitted(self):
        source = ProceduralWizardFrameSource(cols=96, rows=54, fps=24)
        hub = WizardFrameHub(source)
        render_started = threading.Event()
        release_render = threading.Event()
        first_candidate_hash = None
        original_render = source.render_captured_candidate_sync

        def blocked_first_render(render_state, codec):
            nonlocal first_candidate_hash
            candidate = original_render(render_state, codec)
            if first_candidate_hash is None:
                first_candidate_hash = candidate.authoritative_state_sha256
                render_started.set()
                release_render.wait(timeout=2.0)
            return candidate

        with mock.patch.object(
            source,
            "render_captured_candidate_sync",
            side_effect=blocked_first_render,
        ):
            await hub.start()
            self.assertTrue(await asyncio.to_thread(render_started.wait, 1.0))
            async with hub._current_lock():
                source.current_state().expression = "happy"
            release_render.set()
            deadline = asyncio.get_running_loop().time() + 2.0
            while hub._published_frames < 1:
                self.assertLess(asyncio.get_running_loop().time(), deadline)
                await asyncio.sleep(0.01)

        try:
            snapshot = await hub.animation_truth_trace_snapshot()
            self.assertGreaterEqual(hub._stale_render_discard_count, 1)
            self.assertEqual(snapshot["count"], hub._published_frames)
            self.assertNotIn(
                first_candidate_hash,
                {
                    record["authoritative_state_sha256"]
                    for record in snapshot["records"]
                },
            )
        finally:
            release_render.set()
            await hub.stop()


if __name__ == "__main__":
    unittest.main()
