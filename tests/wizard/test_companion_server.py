import asyncio
import hashlib
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from wizard_avatar.hd_pose_artifact import HDPoseLibrary
from wizard_avatar.server import create_app


APP_TOKEN = "companion-app-token-for-focused-tests"
LOOPBACK_HEADERS = (("host", "127.0.0.1:43123"),)


async def asgi_request(app, method, path, body=b"", headers=(), client="127.0.0.1"):
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

    scope = {
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
            for key, value in headers
        ],
        "client": (client, 50000),
        "server": ("127.0.0.1", 43123),
    }
    await app(scope, receive, send)
    status = next(
        message["status"] for message in messages if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return status, json.loads(response_body) if response_body else None


async def asgi_raw_request(app, method, path, body=b"", headers=(), client="127.0.0.1"):
    messages = []
    delivered = False
    response_complete = asyncio.Event()

    async def receive():
        nonlocal delivered
        if delivered:
            await response_complete.wait()
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)
        if message["type"] == "http.response.body" and not message.get("more_body", False):
            response_complete.set()

    scope = {
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
            for key, value in headers
        ],
        "client": (client, 50000),
        "server": ("127.0.0.1", 43123),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_headers = {
        key.decode("ascii").lower(): value.decode("ascii")
        for key, value in start.get("headers", ())
    }
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start["status"], response_headers, response_body


async def asgi_websocket(app, headers=(), client="127.0.0.1"):
    messages = []
    connected = False

    async def receive():
        nonlocal connected
        if not connected:
            connected = True
            return {"type": "websocket.connect"}
        return {"type": "websocket.disconnect", "code": 1000}

    async def send(message):
        messages.append(message)
        if message["type"] == "websocket.send" and "bytes" in message:
            raise RuntimeError("test client disconnected")

    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "ws",
        "path": "/ws/avatar/wizard",
        "raw_path": b"/ws/avatar/wizard",
        "query_string": b"codec=adaptive",
        "root_path": "",
        "headers": [
            (key.lower().encode("ascii"), value.encode("ascii"))
            for key, value in headers
        ],
        "client": (client, 50000),
        "server": ("127.0.0.1", 43123),
        "subprotocols": [],
    }
    await app(scope, receive, send)
    return messages


class CompanionServerTests(unittest.IsolatedAsyncioTestCase):
    def create_companion_app(self, **kwargs):
        with mock.patch.dict(os.environ, {}, clear=True):
            return create_app(companion_mode=True, app_token=APP_TOKEN, **kwargs)

    def test_companion_configuration_fails_closed(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "APP_TOKEN"):
                create_app(companion_mode=True)

        with mock.patch.dict(
            os.environ,
            {"WIZARD_MEDIA_CONNECTOR_TOKEN": APP_TOKEN},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "separate"):
                create_app(companion_mode=True, app_token=APP_TOKEN)

    def test_score_repository_is_configured_from_explicit_runtime_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                os.environ,
                {"WIZARD_SCORE_ROOT": temporary},
                clear=True,
            ):
                app = create_app(companion_mode=False)

            repository = app.state.frame_hub.performance.score_repository
            self.assertIsNotNone(repository)
            self.assertEqual(repository.root, Path(temporary))

    async def test_all_companion_mutation_routes_require_app_bearer(self):
        app = self.create_companion_app()
        mutation_paths = sorted(
            route.path
            for route in app.routes
            if "POST" in getattr(route, "methods", set())
            and route.path
            not in {
                "/api/avatar/wizard/media-session",
                "/api/avatar/wizard/performance-context",
                "/api/avatar/wizard/governed-speech",
                "/api/avatar/wizard/governed-speech/revoke",
                "/api/avatar/wizard/permission-world",
                "/api/avatar/wizard/prism-signal",
            }
        )
        self.assertIn("/api/companion/shutdown", mutation_paths)
        self.assertIn("/api/companion/reactions", mutation_paths)
        self.assertIn("/api/avatar/wizard/command", mutation_paths)

        for path in mutation_paths:
            with self.subTest(path=path):
                status, _ = await asgi_request(app, "POST", path, headers=LOOPBACK_HEADERS)
                self.assertEqual(status, 401)

        wrong_status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/stop",
            headers=LOOPBACK_HEADERS + (("authorization", "Bearer wrong-token"),),
        )
        self.assertEqual(wrong_status, 401)

        accepted_status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/stop",
            headers=LOOPBACK_HEADERS + (("authorization", "Bearer " + APP_TOKEN),),
        )
        self.assertEqual(accepted_status, 200)
        await app.state.frame_hub.stop()

    async def test_companion_reads_are_authenticated_except_versioned_health(self):
        app = self.create_companion_app()
        missing, _ = await asgi_request(
            app, "GET", "/api/avatar/wizard/state", headers=LOOPBACK_HEADERS
        )
        accepted, payload = await asgi_request(
            app,
            "GET",
            "/api/avatar/wizard/state",
            headers=LOOPBACK_HEADERS + (("authorization", "Bearer " + APP_TOKEN),),
        )
        self.assertEqual(missing, 401)
        self.assertEqual(accepted, 200)
        self.assertIn("state", payload)
        await app.state.frame_hub.stop()

    async def test_replay_export_hashes_the_retained_response_bytes(self):
        app = self.create_companion_app()
        status, headers, body = await asgi_raw_request(
            app,
            "GET",
            "/api/avatar/wizard/replay",
            headers=LOOPBACK_HEADERS + (("authorization", "Bearer " + APP_TOKEN),),
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers["x-replay-sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(headers["x-replay-cumulative-sha256"], headers["x-replay-sha256"])
        self.assertEqual(headers["x-replay-total-records"], "1")
        self.assertEqual(headers["x-replay-retained-records"], "1")
        self.assertEqual(headers["x-replay-evicted-records"], "0")
        self.assertEqual(headers["x-replay-truncated"], "false")
        await app.state.frame_hub.stop()

    async def test_reaction_preference_is_strict_and_authenticated(self):
        app = self.create_companion_app()
        headers = LOOPBACK_HEADERS + (
            ("authorization", "Bearer " + APP_TOKEN),
            ("content-type", "application/json"),
        )
        invalid, _ = await asgi_request(
            app, "POST", "/api/companion/reactions", b'{"paused":"yes"}', headers
        )
        accepted, payload = await asgi_request(
            app, "POST", "/api/companion/reactions", b'{"paused":true}', headers
        )
        self.assertEqual(invalid, 400)
        self.assertEqual(accepted, 200)
        self.assertEqual(payload, {"reactions_paused": True})
        await app.state.frame_hub.stop()

    async def test_app_and_media_bearers_are_not_interchangeable(self):
        media_token = "distinct-media-token-for-focused-tests"
        with mock.patch.dict(
            os.environ,
            {
                "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
                "WIZARD_MEDIA_CONNECTOR_TOKEN": media_token,
            },
            clear=True,
        ):
            app = create_app(companion_mode=True, app_token=APP_TOKEN)

        media_status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/media-session",
            headers=LOOPBACK_HEADERS + (("authorization", "Bearer " + APP_TOKEN),),
        )
        command_status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/stop",
            headers=LOOPBACK_HEADERS + (("authorization", "Bearer " + media_token),),
        )
        prism_status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/prism-signal",
            headers=LOOPBACK_HEADERS + (("authorization", "Bearer " + APP_TOKEN),),
        )
        self.assertEqual(media_status, 401)
        self.assertEqual(command_status, 401)
        self.assertEqual(prism_status, 401)

    async def test_prism_advisory_uses_connector_credential_and_strict_bounded_json(self):
        media_token = "distinct-media-token-for-advisory-tests"
        with mock.patch.dict(
            os.environ,
            {
                "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
                "WIZARD_MEDIA_CONNECTOR_TOKEN": media_token,
            },
            clear=True,
        ):
            app = create_app(companion_mode=True, app_token=APP_TOKEN)

        payload = {
            "schema_version": 1,
            "event_id": "00000000-0000-4000-8000-000000000031",
            "source_epoch": "prism-turn-stream-1",
            "source_sequence": 1,
            "emitted_at_ms": int(time.time() * 1000),
            "ttl_ms": 5_000,
            "kind": "stage",
            "classification": "visual_advisory_only",
            "provenance_class": "runtime_lifecycle",
            "sanitization_version": 1,
            "payload": {"stage": "drafting", "status": "active"},
        }
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = LOOPBACK_HEADERS + (
            ("authorization", "Bearer " + media_token),
            ("content-type", "application/json"),
            ("content-length", str(len(body))),
        )
        accepted, state = await asgi_request(
            app, "POST", "/api/avatar/wizard/prism-signal", body, headers
        )
        self.assertEqual(accepted, 200)
        self.assertEqual(state["semantic_signal_sequence"], 1)

        duplicate_body = body.replace(
            b'"schema_version":1',
            b'"schema_version":1,"schema_version":1',
        )
        duplicate, error = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/prism-signal",
            duplicate_body,
            LOOPBACK_HEADERS
            + (
                ("authorization", "Bearer " + media_token),
                ("content-type", "application/json"),
            ),
        )
        browser, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/prism-signal",
            body,
            headers + (("origin", "http://127.0.0.1:43123"),),
        )
        self.assertEqual(duplicate, 400)
        self.assertEqual(error, {"detail": {"code": "visual_advisory_invalid"}})
        self.assertEqual(browser, 403)
        await app.state.frame_hub.stop()

    async def test_prism_v2_ingress_preserves_public_errors_and_turn_context(self):
        media_token = "distinct-media-token-for-v2-advisory-tests"
        with mock.patch.dict(
            os.environ,
            {
                "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
                "WIZARD_MEDIA_CONNECTOR_TOKEN": media_token,
            },
            clear=True,
        ):
            app = create_app(companion_mode=True, app_token=APP_TOKEN)

        payload = {
            "schema_version": 2,
            "event_id": "00000000-0000-4000-8000-000000000032",
            "turn_id": "turn-server-v2",
            "utterance_id": "utterance-server-v2",
            "source_epoch": "prism-turn-stream-2",
            "source_sequence": 1,
            "emitted_at_ms": int(time.time() * 1000),
            "ttl_ms": 5_000,
            "kind": "stage",
            "classification": "visual_advisory_only",
            "provenance_class": "runtime_lifecycle",
            "sanitization_version": 1,
            "payload": {"stage": "reviewing", "status": "active"},
        }
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = LOOPBACK_HEADERS + (
            ("authorization", "Bearer " + media_token),
            ("content-type", "application/json"),
            ("content-length", str(len(body))),
        )
        accepted, state = await asgi_request(
            app, "POST", "/api/avatar/wizard/prism-signal", body, headers
        )
        self.assertEqual(accepted, 200)
        self.assertEqual(state["semantic_turn_id"], "turn-server-v2")
        self.assertEqual(state["semantic_cue"], "review")
        self.assertEqual(state["expression"], "focused")
        self.assertEqual(state["action"], "thinking")

        duplicate_body = body.replace(
            b'"turn_id":"turn-server-v2"',
            b'"turn_id":"turn-server-v2","turn_id":"turn-server-v2"',
        )
        status, error = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/prism-signal",
            duplicate_body,
            LOOPBACK_HEADERS
            + (
                ("authorization", "Bearer " + media_token),
                ("content-type", "application/json"),
            ),
        )
        self.assertEqual(status, 400)
        self.assertEqual(error, {"detail": {"code": "visual_advisory_invalid"}})
        await app.state.frame_hub.stop()

    async def test_health_is_public_private_and_literal_loopback_only(self):
        with mock.patch.dict(
            os.environ,
            {
                "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
                "WIZARD_MEDIA_CONNECTOR_TOKEN": "distinct-media-token",
            },
            clear=True,
        ):
            app = create_app(companion_mode=True, app_token=APP_TOKEN)

        status, payload = await asgi_request(
            app, "GET", "/api/companion/health", headers=LOOPBACK_HEADERS
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            set(payload),
            {
                "schema_version",
                "status",
                "runtime_epoch",
                "protocol_version",
                "character_id",
                "pid",
                "started_at_monotonic_ms",
                "frame_hub_running",
                "frame_hub_error_code",
                "connector_enabled",
                "hd_review_projection",
                "hd_runtime_admitted",
            },
        )
        self.assertEqual(payload["status"], "ready")
        self.assertFalse(payload["frame_hub_running"])
        self.assertIsNone(payload["frame_hub_error_code"])
        self.assertTrue(payload["connector_enabled"])
        self.assertTrue(payload["hd_review_projection"])
        self.assertFalse(payload["hd_runtime_admitted"])
        serialized = json.dumps(payload)
        self.assertNotIn(APP_TOKEN, serialized)
        self.assertNotIn("distinct-media-token", serialized)

        hostname_status, _ = await asgi_request(
            app,
            "GET",
            "/api/companion/health",
            headers=(("host", "localhost:43123"),),
        )
        self.assertEqual(hostname_status, 403)
        remote_status, _ = await asgi_request(
            app,
            "GET",
            "/api/companion/health",
            headers=LOOPBACK_HEADERS,
            client="192.0.2.10",
        )
        self.assertEqual(remote_status, 403)

    async def test_hd_review_projection_serves_decoded_pixel_graph(self):
        app = self.create_companion_app()
        authenticated = LOOPBACK_HEADERS + (
            ("authorization", "Bearer " + APP_TOKEN),
        )
        status, profile = await asgi_request(
            app, "GET", "/api/avatar/wizard/hd-profile", headers=authenticated
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(profile["pose_ids"]), 260)
        self.assertIn("001_turn_front_neutral", profile["pose_ids"])
        self.assertIn("wjff_001_top_recovery", profile["pose_ids"])
        self.assertEqual(profile["profile"]["canvas_width"], 1254)
        self.assertEqual(profile["profile"]["canvas_height"], 1254)
        self.assertTrue(profile["review_projection"])
        self.assertFalse(profile["runtime_admitted"])
        self.assertEqual(
            profile["pose_metadata"]["001_turn_front_neutral"]["approval_state"],
            "approved_production_alpha",
        )
        self.assertEqual(
            profile["pose_metadata"]["wjff_001_top_recovery"]["approval_state"],
            "candidate_review",
        )
        self.assertEqual(len(profile["sequences"]["all_hd_frames"]["pose_ids"]), 260)
        self.assertEqual(profile["sequences"]["all_hd_frames"]["fps"], 6)

        status, headers, body = await asgi_raw_request(
            app,
            "GET",
            "/api/avatar/wizard/hd-pose/001_turn_front_neutral",
            headers=authenticated,
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers["x-pixel-format"], "rgba8")
        self.assertEqual(headers["x-approval-state"], "approved_production_alpha")
        self.assertEqual(headers["x-runtime-admitted"], "false")
        self.assertEqual(len(body), 1254 * 1254 * 4)
        self.assertEqual(headers["x-pose-sha256"], hashlib.sha256(body).hexdigest())

        missing_status, _ = await asgi_request(
            app, "GET", "/api/avatar/wizard/hd-pose/missing", headers=authenticated
        )
        self.assertEqual(missing_status, 404)
        await app.state.frame_hub.stop()

    async def test_hd_review_projection_decodes_off_the_event_loop(self):
        app = self.create_companion_app()
        authenticated = LOOPBACK_HEADERS + (
            ("authorization", "Bearer " + APP_TOKEN),
        )
        loop_thread = threading.get_ident()
        worker_threads = []
        original = HDPoseLibrary.load_rgba

        def instrumented(library, pose_id):
            worker_threads.append(threading.get_ident())
            return original(library, pose_id)

        with mock.patch.object(HDPoseLibrary, "load_rgba", instrumented):
            status, _, _ = await asgi_raw_request(
                app,
                "GET",
                "/api/avatar/wizard/hd-pose/001_turn_front_neutral",
                headers=authenticated,
            )

        self.assertEqual(status, 200)
        self.assertTrue(worker_threads)
        self.assertNotEqual(worker_threads[0], loop_thread)
        await app.state.frame_hub.stop()

    async def test_side_by_side_player_is_served_with_live_and_review_views(self):
        app = self.create_companion_app()
        authenticated = LOOPBACK_HEADERS + (
            ("authorization", "Bearer " + APP_TOKEN),
        )
        status, headers, body = await asgi_raw_request(
            app, "GET", "/side-by-side", headers=authenticated
        )
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["content-type"])
        self.assertIn(b"Current live animation", body)
        self.assertIn(b"All 260 HD alpha frames", body)
        self.assertIn(b"hd-sequence=all_hd_frames", body)
        await app.state.frame_hub.stop()

    async def test_browser_origin_cannot_request_shutdown(self):
        signal = mock.Mock()
        app = self.create_companion_app(shutdown_signal=signal)
        status, _ = await asgi_request(
            app,
            "POST",
            "/api/companion/shutdown",
            headers=LOOPBACK_HEADERS
            + (
                ("authorization", "Bearer " + APP_TOKEN),
                ("origin", "http://127.0.0.1:43123"),
            ),
        )
        self.assertEqual(status, 403)
        signal.assert_not_called()

    async def test_shutdown_stops_hub_and_requests_clean_server_exit(self):
        signal = mock.Mock()
        app = self.create_companion_app(shutdown_signal=signal)
        await app.state.frame_hub.start()
        self.assertIsNotNone(app.state.frame_hub._task)

        status, payload = await asgi_request(
            app,
            "POST",
            "/api/companion/shutdown",
            headers=LOOPBACK_HEADERS + (("authorization", "Bearer " + APP_TOKEN),),
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "shutting_down"})
        self.assertIsNone(app.state.frame_hub._task)
        self.assertTrue(app.state.shutdown_requested)
        signal.assert_called_once_with()

    async def test_lifespan_always_stops_frame_hub(self):
        app = self.create_companion_app()
        app.state.frame_hub.stop = mock.AsyncMock()
        async with app.router.lifespan_context(app):
            pass
        app.state.frame_hub.stop.assert_awaited_once_with()

    async def test_websocket_rejects_missing_wrong_and_browser_credentials(self):
        app = self.create_companion_app()
        missing = await asgi_websocket(app, headers=LOOPBACK_HEADERS)
        wrong = await asgi_websocket(
            app,
            headers=LOOPBACK_HEADERS + (("authorization", "Bearer wrong-token"),),
        )
        browser = await asgi_websocket(
            app,
            headers=LOOPBACK_HEADERS
            + (
                ("authorization", "Bearer " + APP_TOKEN),
                ("origin", "https://example.com"),
            ),
        )
        hostname = await asgi_websocket(
            app,
            headers=(
                ("host", "localhost:43123"),
                ("authorization", "Bearer " + APP_TOKEN),
            ),
        )
        for messages in (missing, wrong, browser, hostname):
            self.assertEqual(messages, [{"type": "websocket.close", "code": 1008, "reason": ""}])

    async def test_websocket_accepts_app_bearer_on_literal_loopback(self):
        app = self.create_companion_app()
        messages = await asgi_websocket(
            app,
            headers=LOOPBACK_HEADERS + (("authorization", "Bearer " + APP_TOKEN),),
        )
        self.assertEqual(messages[0]["type"], "websocket.accept")
        self.assertEqual(messages[1]["type"], "websocket.send")
        self.assertTrue(messages[1]["text"].startswith("INIT:"))
        await app.state.frame_hub.stop()

    async def test_compatibility_mode_is_local_only_but_keeps_local_mutations_unauthenticated(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            app = create_app(companion_mode=False)
        remote_status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/stop",
            headers=(("host", "legacy.example"),),
            client="192.0.2.10",
        )
        local_status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/stop",
            headers=LOOPBACK_HEADERS,
        )
        self.assertEqual(remote_status, 403)
        self.assertEqual(local_status, 200)
        await app.state.frame_hub.stop()

    async def test_all_modes_reject_oversized_mutation_bodies_before_parsing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            app = create_app(companion_mode=False)
        status, payload = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/stop",
            headers=LOOPBACK_HEADERS + (("content-length", str(64 * 1024 + 1)),),
        )
        self.assertEqual(status, 413)
        self.assertEqual(payload, {"detail": "Request body too large"})

    async def test_health_reports_background_hub_failure_truthfully(self):
        app = self.create_companion_app()
        app.state.frame_hub._task_error_code = "frame_hub_failed"
        status, payload = await asgi_request(
            app,
            "GET",
            "/api/companion/health",
            headers=LOOPBACK_HEADERS,
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["frame_hub_error_code"], "frame_hub_failed")


if __name__ == "__main__":
    unittest.main()
