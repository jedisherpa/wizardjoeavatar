import json
import os
import unittest
from unittest import mock

from wizard_avatar.server import create_app

from tests.wizard.test_media_session import snapshot_mapping


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
            for key, value in request_headers
        ],
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8765),
    }
    await app(scope, receive, send)
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"") for message in messages if message["type"] == "http.response.body"
    )
    return status, json.loads(response_body) if response_body else None


class MediaSessionServerTests(unittest.IsolatedAsyncioTestCase):
    def live_body(self):
        return json.dumps(
            snapshot_mapping(kind="music", mode="music", with_hashes=False),
            separators=(",", ":"),
        ).encode("utf-8")

    async def test_connector_is_disabled_without_explicit_configuration(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            app = create_app()
        status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/media-session",
            self.live_body(),
            (("content-type", "application/json"),),
        )
        self.assertEqual(status, 503)
        state_status, payload = await asgi_request(
            app, "GET", "/api/avatar/wizard/state"
        )
        self.assertEqual(state_status, 200)
        self.assertEqual(payload["media"]["status"], "disabled")
        self.assertNotIn("active_session_suffix", payload["media"])

    async def test_auth_origin_size_and_valid_snapshot_boundaries(self):
        env = {
            "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
            "WIZARD_MEDIA_CONNECTOR_TOKEN": "server-test-token",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            app = create_app()
        body = self.live_body()
        common = (("content-type", "application/json"),)

        unauthorized, _ = await asgi_request(
            app, "POST", "/api/avatar/wizard/media-session", body, common
        )
        self.assertEqual(unauthorized, 401)

        forbidden, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/media-session",
            body,
            common
            + (("authorization", "Bearer server-test-token"), ("origin", "http://127.0.0.1:8765")),
        )
        self.assertEqual(forbidden, 403)

        oversized, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/media-session",
            b" " * (16 * 1024 + 1),
            common
            + (
                ("authorization", "Bearer server-test-token"),
                ("content-length", str(16 * 1024 + 1)),
            ),
        )
        self.assertEqual(oversized, 413)

        accepted, payload = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/media-session",
            body,
            common + (("authorization", "Bearer server-test-token"),),
        )
        self.assertEqual(accepted, 200)
        self.assertEqual(payload["disposition"], "accepted")
        self.assertEqual(payload["scheduler_state"], "scoreless")

        state_status, state_payload = await asgi_request(
            app, "GET", "/api/avatar/wizard/state"
        )
        self.assertEqual(state_status, 200)
        self.assertIn(state_payload["media"]["status"], {"ready", "animating"})
        self.assertEqual(state_payload["media"]["source"], "main")
        self.assertNotIn("active_session_suffix", state_payload["media"])
        await app.state.frame_hub.stop()


if __name__ == "__main__":
    unittest.main()
