import json
import os
import time
import unittest
from unittest import mock

from wizard_avatar.governed_performance import GovernedPerformanceApprovalV1
from wizard_avatar.media_session import MEDIA_SESSION_MAX_BODY_BYTES
from wizard_avatar.performance_release import GOVERNED_SPEECH_MAX_BODY_BYTES
from wizard_avatar.server import create_app

from tests.wizard.test_media_session import snapshot_mapping
from tests.wizard.test_media_session_server import asgi_request
from tests.wizard.test_performance_release import (
    MEDIA_ID,
    PACKAGE_DIGEST,
    TEXT,
    alignment_mapping,
    context_request_mapping,
)


TOKEN_HEADERS = (
    ("content-type", "application/json"),
    ("authorization", "Bearer governed-test-token"),
)


def connector_app():
    env = {
        "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
        "WIZARD_MEDIA_CONNECTOR_TOKEN": "governed-test-token",
    }
    with mock.patch.dict(os.environ, env, clear=True):
        return create_app()


class GovernedSpeechServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_performance_binding_is_connector_only_and_content_free(self):
        app = connector_app()
        try:
            unauthorized, _ = await asgi_request(
                app,
                "GET",
                "/api/avatar/wizard/performance-binding",
            )
            self.assertEqual(unauthorized, 401)

            status, binding = await asgi_request(
                app,
                "GET",
                "/api/avatar/wizard/performance-binding",
                headers=(("authorization", "Bearer governed-test-token"),),
            )
            self.assertEqual(status, 200, binding)
            self.assertEqual(
                set(binding),
                {
                    "schema_version",
                    "wizard_runtime_epoch",
                    "character_id",
                    "package_digest",
                    "reconciliation_generation",
                    "revocation_generation",
                },
            )
            self.assertEqual(binding["schema_version"], 1)
            self.assertEqual(
                binding["character_id"], app.state.frame_hub.performance.character_id
            )
            self.assertEqual(
                binding["package_digest"], app.state.frame_hub.performance.package_digest
            )
            serialized = json.dumps(binding)
            for private_value in (TEXT, "approved_text", "prompt", "transcript"):
                self.assertNotIn(private_value, serialized)
        finally:
            await app.state.frame_hub.stop()

    async def test_connector_ingress_requires_exact_auth_and_server_to_server_origin(self):
        app = connector_app()
        paths = (
            "/api/avatar/wizard/performance-context",
            "/api/avatar/wizard/governed-speech",
            "/api/avatar/wizard/governed-speech/revoke",
        )
        try:
            for path in paths:
                for authorization in (
                    None,
                    "Bearer governed-test-token ",
                    "bearer governed-test-token",
                    "Basic governed-test-token",
                    "Bearer wrong-token",
                ):
                    headers = [("content-type", "application/json")]
                    if authorization is not None:
                        headers.append(("authorization", authorization))
                    with self.subTest(path=path, authorization=authorization):
                        status, _ = await asgi_request(
                            app, "POST", path, b"{}", tuple(headers)
                        )
                        self.assertEqual(status, 401)

                for origin in (
                    "http://127.0.0.1:8765",
                    "https://[::1]:8765",
                    "https://example.test",
                ):
                    with self.subTest(path=path, origin=origin):
                        status, _ = await asgi_request(
                            app,
                            "POST",
                            path,
                            b"{}",
                            TOKEN_HEADERS + (("origin", origin),),
                        )
                        self.assertEqual(status, 403)

                with self.subTest(path=path, content_type="with-charset"):
                    status, _ = await asgi_request(
                        app,
                        "POST",
                        path,
                        b"{}",
                        (
                            ("content-type", "application/json; charset=utf-8"),
                            ("authorization", "Bearer governed-test-token"),
                        ),
                    )
                    self.assertEqual(status, 415)

                with self.subTest(path=path, host="localhost"):
                    status, _ = await asgi_request(
                        app,
                        "POST",
                        path,
                        b"{}",
                        TOKEN_HEADERS + (("host", "localhost:8765"),),
                    )
                    self.assertEqual(status, 403)
        finally:
            await app.state.frame_hub.stop()

        with mock.patch.dict(os.environ, {}, clear=True):
            disabled = create_app()
        try:
            status, _ = await asgi_request(
                disabled,
                "POST",
                "/api/avatar/wizard/performance-context",
                b"{}",
                TOKEN_HEADERS,
            )
            self.assertEqual(status, 503)
        finally:
            await disabled.state.frame_hub.stop()

    async def test_connector_routes_enforce_their_exact_content_limits(self):
        app = connector_app()
        limits = (
            (
                "/api/avatar/wizard/performance-context",
                MEDIA_SESSION_MAX_BODY_BYTES,
                400,
            ),
            (
                "/api/avatar/wizard/governed-speech",
                GOVERNED_SPEECH_MAX_BODY_BYTES,
                400,
            ),
            ("/api/avatar/wizard/governed-speech/revoke", 4 * 1024, 409),
        )
        try:
            for path, limit, parse_status in limits:
                with self.subTest(path=path, boundary="exact-stream"):
                    status, _ = await asgi_request(
                        app, "POST", path, b" " * limit, TOKEN_HEADERS
                    )
                    self.assertEqual(status, parse_status)

                with self.subTest(path=path, boundary="stream-plus-one"):
                    status, _ = await asgi_request(
                        app, "POST", path, b" " * (limit + 1), TOKEN_HEADERS
                    )
                    self.assertEqual(status, 413)

                with self.subTest(path=path, boundary="declared-plus-one"):
                    status, _ = await asgi_request(
                        app,
                        "POST",
                        path,
                        b"{}",
                        TOKEN_HEADERS + (("content-length", str(limit + 1)),),
                    )
                    self.assertEqual(status, 413)

                for content_length in ("not-an-integer", "-1"):
                    with self.subTest(path=path, content_length=content_length):
                        status, _ = await asgi_request(
                            app,
                            "POST",
                            path,
                            b"{}",
                            TOKEN_HEADERS + (("content-length", content_length),),
                        )
                        self.assertEqual(status, 400)
        finally:
            await app.state.frame_hub.stop()

    async def test_connector_context_register_and_revoke_contract(self):
        app = connector_app()
        package_digest = app.state.frame_hub.performance.package_digest
        character_id = app.state.frame_hub.performance.character_id
        self.assertNotEqual(package_digest, PACKAGE_DIGEST)
        pending = snapshot_mapping(
            sequence=0,
            media_epoch=4,
            state="paused",
            position_ms=0,
            source_slot="speech",
            kind="tts",
            media_id=MEDIA_ID,
            mode="speech",
            with_hashes=True,
        )
        pending["performance"]["score_id"] = None
        pending["performance"]["score_revision"] = None
        pending["performance"]["score_sha256"] = None
        pending["performance"]["character_id"] = character_id
        pending["performance"]["character_package_sha256"] = package_digest
        try:
            status, _ = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/media-session",
                json.dumps(pending).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(status, 200)

            unauthorized, _ = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/performance-context",
                json.dumps(context_request_mapping()).encode("utf-8"),
                (("content-type", "application/json"),),
            )
            self.assertEqual(unauthorized, 401)

            context_status, context = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/performance-context",
                json.dumps(context_request_mapping()).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(context_status, 200, context)
            self.assertEqual(context["character"]["package_digest"], package_digest)
            self.assertNotIn(TEXT, json.dumps(context))

            now_ms = time.time_ns() // 1_000_000
            approval = GovernedPerformanceApprovalV1.build(
                {
                    "schema_version": 1,
                    "approval_id": "approval:server-turn-0042",
                    "turn_id": "turn:0042",
                    "reply_sha256": alignment_mapping()["approved_content_sha256"],
                    "speech_media": {
                        "kind": "speech",
                        "identity": "speech:turn-0042",
                        "sha256": alignment_mapping()["media_sha256"],
                    },
                    "performance_context_sha256": context["context_sha256"],
                    "character_id": character_id,
                    "package_digest": package_digest,
                    "allowed_sinks": ["animation", "speech", "text"],
                    "issued_at_ms": now_ms - 100,
                    "expires_at_ms": now_ms + 60_000,
                    "revocation_generation": 0,
                    "reconciliation_generation": context["runtime"][
                        "reconciliation_generation"
                    ],
                }
            )
            registration = {
                "schema_version": 1,
                "approved_text": TEXT,
                "approval": approval.to_dict(),
                "performance_context": context,
                "alignment": alignment_mapping(),
            }

            package_mismatch = json.loads(json.dumps(registration))
            package_mismatch["approval"] = GovernedPerformanceApprovalV1.build(
                {
                    **approval.content_dict(),
                    "package_digest": "sha256:" + "c" * 64,
                }
            ).to_dict()
            mismatch_status, mismatch = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/governed-speech",
                json.dumps(package_mismatch).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(mismatch_status, 409)
            self.assertEqual(mismatch["detail"]["code"], "package_mismatch")

            hash_tampered = json.loads(json.dumps(registration))
            hash_tampered["approval"]["turn_id"] = "turn:forged"
            hash_status, hash_error = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/governed-speech",
                json.dumps(hash_tampered).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(hash_status, 409)
            self.assertEqual(hash_error["detail"]["code"], "hash_mismatch")

            register_status, registered = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/governed-speech",
                json.dumps(registration).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(register_status, 200)
            self.assertTrue(registered["active"])
            self.assertNotIn(TEXT, json.dumps(registered))

            replay_status, replay = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/governed-speech",
                json.dumps(registration).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(replay_status, 400)
            self.assertEqual(replay["detail"]["code"], "replay_detected")

            revoke_status, revoked = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/governed-speech/revoke",
                json.dumps(
                    {
                        "schema_version": 1,
                        "approval_id": approval.approval_id,
                        "revocation_generation": 1,
                    }
                ).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(revoke_status, 200)
            self.assertFalse(revoked["active"])
            self.assertEqual(revoked["status"], "approval_revoked")

            stale_status, stale = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/governed-speech/revoke",
                json.dumps(
                    {
                        "schema_version": 1,
                        "approval_id": approval.approval_id,
                        "revocation_generation": 1,
                    }
                ).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(stale_status, 409)
            self.assertEqual(
                stale["detail"]["code"], "revocation_generation_stale"
            )
        finally:
            await app.state.frame_hub.stop()


if __name__ == "__main__":
    unittest.main()
