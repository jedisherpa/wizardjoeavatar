import json
import os
import tempfile
import time
import unittest
from copy import deepcopy
from unittest import mock

from wizard_avatar.governed_performance import GovernedPerformanceApprovalV1
from wizard_avatar.media_session import MEDIA_SESSION_MAX_BODY_BYTES
from wizard_avatar.performance_context import PerformanceContextV1
from wizard_avatar.performance_release import GOVERNED_SPEECH_MAX_BODY_BYTES
from wizard_avatar.server import create_app
from wizard_avatar.voice_alignment import VoiceAlignmentV1

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


def connector_app(*, allow_scoreless=True):
    score_root = tempfile.TemporaryDirectory()
    env = {
        "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
        "WIZARD_MEDIA_CONNECTOR_TOKEN": "governed-test-token",
        "WIZARD_SCORE_ROOT": score_root.name,
    }
    if allow_scoreless:
        env["WIZARD_ALLOW_SCORELESS_GOVERNED_SPEECH"] = "1"
    with mock.patch.dict(os.environ, env, clear=True):
        app = create_app()
    app.state.test_score_root = score_root
    return app


async def stop_connector_app(app):
    await app.state.frame_hub.stop()
    app.state.test_score_root.cleanup()


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
            await stop_connector_app(app)

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
            await stop_connector_app(app)

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
            await stop_connector_app(app)

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
                    "persona_id": "persona:wizard-joe",
                    "voice_id": alignment_mapping()["voice_id"],
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
            self.assertEqual(registered["status"], "release_active")
            self.assertEqual(registered["approval_id"], approval.approval_id)
            self.assertEqual(
                registered["approval_sha256"],
                approval.approval_sha256,
            )
            self.assertEqual(
                registered["alignment_sha256"],
                VoiceAlignmentV1.from_mapping(
                    registration["alignment"]
                ).alignment_sha256,
            )
            self.assertEqual(registered["turn_id"], approval.turn_id)
            self.assertEqual(registered["speech_id"], "speech:turn-0042")
            self.assertEqual(registered["character_id"], character_id)
            self.assertEqual(registered["package_digest"], package_digest)
            self.assertEqual(registered["media_id"], MEDIA_ID)
            self.assertEqual(
                registered["media_sha256"],
                registration["alignment"]["media_sha256"],
            )
            self.assertEqual(
                registered["reconciliation_generation"],
                context["runtime"]["reconciliation_generation"],
            )
            self.assertEqual(
                registered["revocation_generation"],
                approval.revocation_generation,
            )
            self.assertEqual(
                registered["mouth_presentation_policy"],
                "presentation_stabilized_v1",
            )
            self.assertIsNone(registered["score_id"])
            self.assertIsNone(registered["score_revision"])
            self.assertIsNone(registered["score_sha256"])
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

            stop_status, stopped = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/speech-stop",
                json.dumps({"speech_id": "speech:turn-0042"}).encode("utf-8"),
                (("content-type", "application/json"),),
            )
            self.assertEqual(stop_status, 200, stopped)
            governed = app.state.frame_hub.performance.governed_speech.diagnostics()
            self.assertFalse(governed["active"])
            self.assertEqual(governed["status"], "speech_interrupted")

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
            await stop_connector_app(app)

    async def test_live_score_two_pass_context_binds_final_approval_and_receipt(self):
        app = connector_app(allow_scoreless=False)
        performance = app.state.frame_hub.performance
        character_id = performance.character_id
        package_digest = performance.package_digest
        scoreless = snapshot_mapping(
            sequence=0,
            media_epoch=4,
            cause="trackchange",
            state="loading",
            position_ms=0,
            source_slot="speech",
            kind="tts",
            media_id=MEDIA_ID,
            mode="speech",
            with_hashes=True,
        )
        scoreless["performance"].update(
            {
                "score_id": None,
                "score_revision": None,
                "score_sha256": None,
                "character_id": character_id,
                "character_package_sha256": package_digest,
            }
        )
        context_request = context_request_mapping()
        context_request["intent"] = "speak"
        try:
            status, loading_ack = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/media-session",
                json.dumps(scoreless).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(status, 200, loading_ack)
            self.assertEqual(loading_ack["disposition"], "accepted")

            prepare_status, prepared = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/performance-context/prepare-score",
                json.dumps(context_request).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(prepare_status, 200, prepared)
            self.assertEqual(
                set(prepared),
                {"schema_version", "preliminary_context", "score_binding"},
            )
            preliminary = prepared["preliminary_context"]
            binding = prepared["score_binding"]
            self.assertEqual(
                binding["prepared_from_context_sha256"],
                preliminary["context_sha256"],
            )
            self.assertNotEqual(
                binding["compiled_from_context_sha256"],
                preliminary["context_sha256"],
            )
            self.assertEqual(binding["media_id"], MEDIA_ID)
            self.assertEqual(binding["character_id"], character_id)
            self.assertEqual(binding["package_digest"], package_digest)
            self.assertIsNone(
                preliminary["evidence"]["score_binding"]["score_id"]
            )

            bound = snapshot_mapping(
                sequence=1,
                media_epoch=5,
                cause="trackchange",
                state="loading",
                position_ms=0,
                source_slot="speech",
                kind="tts",
                media_id=MEDIA_ID,
                score_id=binding["score_id"],
                mode="speech",
                with_hashes=True,
            )
            bound["performance"].update(
                {
                    "score_id": binding["score_id"],
                    "score_revision": binding["score_revision"],
                    "score_sha256": binding["score_sha256"],
                    "character_id": character_id,
                    "character_package_sha256": package_digest,
                }
            )
            status, bound_ack = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/media-session",
                json.dumps(bound).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(status, 200, bound_ack)
            self.assertEqual(bound_ack["disposition"], "accepted")

            context_status, final_context = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/performance-context",
                json.dumps(context_request).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(context_status, 200, final_context)
            self.assertNotEqual(
                final_context["context_sha256"],
                preliminary["context_sha256"],
            )
            self.assertEqual(
                final_context["evidence"]["score_binding"],
                {
                    "score_id": binding["score_id"],
                    "score_revision": binding["score_revision"],
                    "score_sha256": binding["score_sha256"],
                },
            )

            now_ms = time.time_ns() // 1_000_000
            def approval_for(context, approval_id, turn_id="turn:0042"):
                return GovernedPerformanceApprovalV1.build({
                    "schema_version": 1,
                    "approval_id": approval_id,
                    "turn_id": turn_id,
                    "reply_sha256": alignment_mapping()[
                        "approved_content_sha256"
                    ],
                    "persona_id": "persona:wizard-joe",
                    "voice_id": alignment_mapping()["voice_id"],
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
                })

            mismatched_context_value = deepcopy(final_context)
            mismatched_context_value.pop("context_sha256")
            mismatched_context_value["evidence"]["score_binding"] = {
                "score_id": "compiled:speech:substituted",
                "score_revision": binding["score_revision"],
                "score_sha256": binding["score_sha256"],
            }
            mismatched_context = PerformanceContextV1.build(
                mismatched_context_value
            ).to_dict()
            mismatched_approval = approval_for(
                mismatched_context,
                "approval:server-score-mismatch-turn-0042",
            )
            mismatched_registration = {
                "schema_version": 1,
                "approved_text": TEXT,
                "approval": mismatched_approval.to_dict(),
                "performance_context": mismatched_context,
                "alignment": alignment_mapping(),
            }
            mismatch_status, mismatch_response = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/governed-speech",
                json.dumps(mismatched_registration).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(mismatch_status, 409, mismatch_response)
            self.assertEqual(
                mismatch_response["detail"]["code"],
                "score_binding_mismatch",
            )

            late_context_value = deepcopy(final_context)
            late_context_value.pop("context_sha256")
            late_context_value["source"]["accepted_sequence"] += 1
            late_context_value["source"]["media_epoch"] += 1
            late_context = PerformanceContextV1.build(
                late_context_value
            ).to_dict()
            late_approval = approval_for(
                late_context,
                "approval:server-score-late-cursor",
            )
            late_registration = {
                "schema_version": 1,
                "approved_text": TEXT,
                "approval": late_approval.to_dict(),
                "performance_context": late_context,
                "alignment": alignment_mapping(),
            }
            late_status, late_response = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/governed-speech",
                json.dumps(late_registration).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(late_status, 409, late_response)
            self.assertEqual(
                late_response["detail"]["code"],
                "score_preparation_mismatch",
            )

            replay_context_value = deepcopy(final_context)
            replay_context_value.pop("context_sha256")
            replay_context_value["source"]["turn_id"] = "turn:replayed"
            replay_context_value["source"]["utterance_id"] = "utterance:replayed"
            replay_context = PerformanceContextV1.build(
                replay_context_value
            ).to_dict()
            replay_approval = approval_for(
                replay_context,
                "approval:server-score-replayed",
                turn_id="turn:replayed",
            )
            replay_registration = {
                "schema_version": 1,
                "approved_text": TEXT,
                "approval": replay_approval.to_dict(),
                "performance_context": replay_context,
                "alignment": alignment_mapping(),
            }
            replay_status, replay_response = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/governed-speech",
                json.dumps(replay_registration).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(replay_status, 409, replay_response)
            self.assertEqual(
                replay_response["detail"]["code"],
                "score_preparation_mismatch",
            )

            approval = approval_for(
                final_context,
                "approval:server-score-turn-0042",
            )
            registration = {
                "schema_version": 1,
                "approved_text": TEXT,
                "approval": approval.to_dict(),
                "performance_context": final_context,
                "alignment": alignment_mapping(),
            }
            register_status, receipt = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/governed-speech",
                json.dumps(registration).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(register_status, 200, receipt)
            self.assertTrue(receipt["active"])
            self.assertEqual(receipt["score_id"], binding["score_id"])
            self.assertEqual(
                receipt["score_revision"], binding["score_revision"]
            )
            self.assertEqual(receipt["score_sha256"], binding["score_sha256"])
            self.assertNotIn(TEXT, json.dumps(receipt))

            replay_status, replay_response = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/governed-speech",
                json.dumps(registration).encode("utf-8"),
                TOKEN_HEADERS,
            )
            self.assertEqual(replay_status, 409, replay_response)
            self.assertEqual(
                replay_response["detail"]["code"],
                "score_preparation_required",
            )
        finally:
            await stop_connector_app(app)


if __name__ == "__main__":
    unittest.main()
