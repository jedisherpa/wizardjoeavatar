import json
import os
import unittest
from unittest import mock

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

    async def test_all_companion_mutation_routes_require_app_bearer(self):
        app = self.create_companion_app()
        mutation_paths = sorted(
            route.path
            for route in app.routes
            if "POST" in getattr(route, "methods", set())
            and route.path != "/api/avatar/wizard/media-session"
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
        self.assertEqual(media_status, 401)
        self.assertEqual(command_status, 401)

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
                "connector_enabled",
            },
        )
        self.assertEqual(payload["status"], "ready")
        self.assertFalse(payload["frame_hub_running"])
        self.assertTrue(payload["connector_enabled"])
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

    async def test_compatibility_mode_keeps_mutations_unauthenticated(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            app = create_app(companion_mode=False)
        status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/stop",
            headers=(("host", "legacy.example"),),
            client="192.0.2.10",
        )
        self.assertEqual(status, 200)
        await app.state.frame_hub.stop()


if __name__ == "__main__":
    unittest.main()
