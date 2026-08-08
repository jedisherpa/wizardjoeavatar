import asyncio
import json
import os
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

from tests.wizard.test_directed_performance import (
    main_snapshot,
    preparation_mapping,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.directed_performance import (
    DirectedPerformanceError,
    DirectedPerformancePreparationV1,
)
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.performance_score import CompiledScoreRepository
from wizard_avatar.score_jobs import (
    ScoreJobLane,
    ScoreJobLaneStopped,
    ScoreJobQueueFull,
)
from wizard_avatar.server import create_app
from wizard_avatar.stream import WizardFrameHub


async def asgi_request(app, method, path, body=b"", headers=()):
    messages = []
    delivered = False

    async def receive():
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    request_headers = list(headers)
    if not any(key.lower() == "host" for key, _value in request_headers):
        request_headers.append(("host", "127.0.0.1:8765"))
    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "root_path": "",
            "headers": [
                (key.lower().encode("ascii"), value.encode("ascii"))
                for key, value in request_headers
            ],
            "client": ("127.0.0.1", 50000),
            "server": ("127.0.0.1", 8765),
        },
        receive,
        send,
    )
    start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode("ascii").lower(): value.decode("ascii")
        for key, value in start.get("headers", ())
    }
    return (
        start["status"],
        json.loads(response_body) if response_body else None,
        response_headers,
    )


class ScoreJobLaneTests(unittest.IsolatedAsyncioTestCase):
    async def test_lane_serializes_work_and_rejects_beyond_total_capacity(self):
        lane = ScoreJobLane(capacity=2)
        first_started = asyncio.Event()
        release_first = asyncio.Event()
        second_started = asyncio.Event()

        async def first():
            first_started.set()
            await release_first.wait()
            return "first"

        async def second():
            second_started.set()
            return "second"

        first_task = asyncio.create_task(lane.submit(first))
        await first_started.wait()
        second_task = asyncio.create_task(lane.submit(second))
        await asyncio.sleep(0)

        try:
            self.assertFalse(second_started.is_set())
            with self.assertRaises(ScoreJobQueueFull) as caught:
                await lane.submit(second)
            self.assertEqual(caught.exception.code, "score_job_queue_full")
            diagnostics = lane.diagnostics()
            self.assertEqual(diagnostics["capacity"], 2)
            self.assertEqual(diagnostics["outstanding"], 2)
            self.assertEqual(diagnostics["rejected"], 1)
            self.assertNotIn("operation", diagnostics)
            self.assertNotIn("exception", diagnostics)

            release_first.set()
            self.assertEqual(await first_task, "first")
            self.assertEqual(await second_task, "second")
            self.assertTrue(second_started.is_set())
            self.assertEqual(lane.diagnostics()["completed"], 2)
        finally:
            release_first.set()
            for task in (first_task, second_task):
                if not task.done():
                    task.cancel()
            await lane.stop()

    async def test_stop_settles_active_and_queued_jobs(self):
        lane = ScoreJobLane(capacity=2)
        active_started = asyncio.Event()
        never_release = asyncio.Event()

        async def active():
            active_started.set()
            await never_release.wait()

        active_task = asyncio.create_task(lane.submit(active))
        await active_started.wait()
        queued_task = asyncio.create_task(lane.submit(active))
        await asyncio.sleep(0)

        await lane.stop()

        for task in (active_task, queued_task):
            with self.assertRaises(ScoreJobLaneStopped):
                await task
        diagnostics = lane.diagnostics()
        self.assertEqual(diagnostics["outstanding"], 0)
        self.assertEqual(diagnostics["cancelled"], 2)


class ScoreJobHubTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.registry = load_character_registry()
        self.hub = WizardFrameHub(
            ProceduralWizardFrameSource(fps=24),
            score_repository=CompiledScoreRepository(self.temporary.name),
        )
        await self.hub.accept_media_session(
            main_snapshot(self.registry),
            receipt_monotonic_us=1_000_000,
        )
        self.preparation = DirectedPerformancePreparationV1.from_mapping(
            preparation_mapping()
        )

    async def asyncTearDown(self):
        await self.hub.stop()
        self.temporary.cleanup()

    @staticmethod
    def prepared_result():
        return SimpleNamespace(
            to_dict=lambda: {
                "schema_version": 1,
                "score_binding": {"score_id": "compiled:test"},
            }
        )

    async def test_blocked_publication_does_not_hold_hub_lock_or_stop_clock(self):
        publication_started = threading.Event()
        release_publication = threading.Event()

        def publish(_compiled):
            publication_started.set()
            release_publication.wait(timeout=2.0)
            return self.prepared_result()

        with (
            mock.patch.object(
                self.hub.performance,
                "compile_directed_performance",
                return_value=object(),
            ),
            mock.patch.object(
                self.hub.performance,
                "publish_directed_performance",
                side_effect=publish,
            ),
        ):
            preparation_task = asyncio.create_task(
                self.hub.prepare_directed_performance(self.preparation)
            )
            self.assertTrue(
                await asyncio.to_thread(publication_started.wait, 1.0)
            )
            tick_before = self.hub.runtime.clock.simulation_tick
            try:
                binding = await asyncio.wait_for(
                    self.hub.performance_binding(),
                    timeout=0.2,
                )
                await asyncio.sleep(0.1)
                tick_after = self.hub.runtime.clock.simulation_tick
                self.assertEqual(
                    binding["wizard_runtime_epoch"],
                    self.hub.runtime_epoch,
                )
                self.assertGreater(tick_after, tick_before)
                self.assertTrue(self.hub.diagnostics_extra()["score_jobs"]["active"])
            finally:
                release_publication.set()
            result = await preparation_task

        self.assertEqual(
            result["score_binding"]["score_id"],
            "compiled:test",
        )

    async def test_authority_change_during_publication_returns_no_binding(self):
        def publish_after_authority_change(_compiled):
            self.hub.performance.scheduler.coordinator.rotate_runtime_epoch(
                "wizard-runtime-score-job-revoked"
            )
            return self.prepared_result()

        with (
            mock.patch.object(
                self.hub.performance,
                "compile_directed_performance",
                return_value=object(),
            ),
            mock.patch.object(
                self.hub.performance,
                "publish_directed_performance",
                side_effect=publish_after_authority_change,
            ),
        ):
            with self.assertRaises(DirectedPerformanceError) as caught:
                await self.hub.prepare_directed_performance(self.preparation)

        self.assertEqual(caught.exception.code, "media_session_changed")
        diagnostics = self.hub.diagnostics_extra()["score_jobs"]
        self.assertEqual(diagnostics["completed"], 0)
        self.assertEqual(diagnostics["failed"], 1)
        self.assertEqual(diagnostics["last_error_code"], "score_job_failed")


class ScoreJobServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_queue_full_is_a_sanitized_retryable_response(self):
        env = {
            "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
            "WIZARD_MEDIA_CONNECTOR_TOKEN": "director-test-token",
        }
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(os.environ, env, clear=True):
                app = create_app(
                    score_repository=CompiledScoreRepository(temporary)
                )
            with mock.patch.object(
                app.state.frame_hub,
                "prepare_directed_performance",
                new=mock.AsyncMock(side_effect=ScoreJobQueueFull()),
            ):
                status, payload, headers = await asgi_request(
                    app,
                    "POST",
                    "/api/avatar/wizard/director/v1/performances/prepare",
                    json.dumps(
                        preparation_mapping(),
                        separators=(",", ":"),
                    ).encode("utf-8"),
                    (
                        ("content-type", "application/json"),
                        ("authorization", "Bearer director-test-token"),
                    ),
                )
            await app.state.frame_hub.stop()

        self.assertEqual(status, 503)
        self.assertEqual(
            payload,
            {
                "detail": {
                    "code": "score_job_queue_full",
                    "path": "$",
                }
            },
        )
        self.assertEqual(headers["retry-after"], "1")


if __name__ == "__main__":
    unittest.main()
