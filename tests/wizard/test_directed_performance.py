import json
import os
import tempfile
import unittest
from copy import deepcopy
from unittest import mock

from wizard_avatar.character_capabilities import derive_character_capability_manifest
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.directed_performance import (
    DirectedPerformanceError,
    DirectedPerformancePreparationV1,
)
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.media_session import MediaSessionSnapshotV1
from wizard_avatar.performance_application import PerformanceApplication
from wizard_avatar.performance_release import PerformanceContextRequestV1
from wizard_avatar.performance_score import CompiledScoreRepository
from wizard_avatar.server import create_app
from wizard_avatar.score_edits import ScoreEditsV1
from wizard_avatar.stream import WizardFrameHub

from tests.wizard.test_media_session import snapshot_mapping
from tests.wizard.test_media_session_server import asgi_request


MEDIA_DIGEST = "sha256:" + "1" * 64
MEDIA_ID = "media:sha256:" + "1" * 64
REPLY_DIGEST = "sha256:" + "d" * 64
DURATION_MS = 9_000


def preparation_mapping(*, source_slot="main", direction_text=None):
    return {
        "schema_version": 1,
        "source_slot": source_slot,
        "context_request": {
            "schema_version": 1,
            "turn_id": "turn:directed:0001",
            "utterance_id": "utterance:directed:0001",
            "media_id": MEDIA_ID,
            "reply_sha256": REPLY_DIGEST,
            "intent": "explain",
            "tone": "warm",
            "sensitivity": "ordinary",
            "urgency": "normal",
            "relational_stance": "collaborative",
            "pending_action_posture": "none",
            "display_profile": "desktop",
        },
        "direction": {
            "schema_version": 1,
            "direction_id": "direction:directed:0001",
            "direction_text": direction_text
            or (
                "Wizard Joe enters toward center stage, transitions to warm "
                "seriousness, raises the right hand, then speaks."
            ),
            "intent": "explain",
            "duration_ms": DURATION_MS,
            "media_id": MEDIA_ID,
            "media_sha256": MEDIA_DIGEST,
            "seed": 27,
        },
    }


def main_snapshot(
    registry,
    *,
    sequence=0,
    state="paused",
    position_ms=0,
    score_binding=None,
):
    value = snapshot_mapping(
        sequence=sequence,
        media_epoch=7 if score_binding is None else 8,
        cause=(
            "initial"
            if sequence == 0
            else "seeked"
            if score_binding is not None
            else {"playing": "play", "paused": "pause"}.get(state, state)
        ),
        state=state,
        position_ms=position_ms,
        source_slot="main",
        kind="audiobook",
        media_id=MEDIA_ID,
        mode="narrative",
        with_hashes=True,
    )
    package = registry.get(registry.default_character_id)
    value["media"]["duration_ms"] = DURATION_MS
    value["performance"].update(
        {
            "character_id": registry.default_character_id,
            "character_package_sha256": package.package_sha256,
            "score_id": None,
            "score_revision": None,
            "score_sha256": None,
        }
    )
    if score_binding is not None:
        value["performance"].update(
            {
                "score_id": score_binding["score_id"],
                "score_revision": score_binding["score_revision"],
                "score_sha256": score_binding["score_sha256"],
            }
        )
    return MediaSessionSnapshotV1.from_mapping(value)


class DirectedPerformanceContractTests(unittest.TestCase):
    def test_contract_is_closed_duplicate_safe_and_identity_bound(self):
        raw = preparation_mapping()
        raw["unexpected"] = True
        with self.assertRaises(DirectedPerformanceError) as unknown:
            DirectedPerformancePreparationV1.from_mapping(raw)
        self.assertEqual(unknown.exception.code, "unknown_field")

        duplicate = (
            b'{"schema_version":1,"schema_version":1,"source_slot":"main",'
            b'"context_request":{},"direction":{}}'
        )
        with self.assertRaises(DirectedPerformanceError) as repeated:
            DirectedPerformancePreparationV1.from_json(duplicate)
        self.assertEqual(repeated.exception.code, "duplicate_json_key")

        mismatch = preparation_mapping()
        mismatch["direction"]["media_id"] = "media:sha256:" + "2" * 64
        mismatch["direction"]["media_sha256"] = "sha256:" + "2" * 64
        with self.assertRaises(DirectedPerformanceError) as stale:
            DirectedPerformancePreparationV1.from_mapping(mismatch)
        self.assertEqual(stale.exception.code, "media_mismatch")

    def test_private_direction_fails_closed_without_echoing_content(self):
        preparation = DirectedPerformancePreparationV1.from_mapping(
            preparation_mapping(direction_text="Bearer sk-privatecanary")
        )
        registry = load_character_registry()
        manifest = derive_character_capability_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            application = PerformanceApplication(
                "wizard-runtime-directed-private",
                score_repository=CompiledScoreRepository(temporary),
                character_id=registry.default_character_id,
                package_digest=registry.get(
                    registry.default_character_id
                ).package_sha256,
                manifest_digest=manifest["manifest_sha256"],
                capability_manifest=manifest,
                character_registry=registry,
            )
            controller = WizardAvatarController(
                ("front_idle",),
                registry.default_character_id,
            )
            application.accept_snapshot(main_snapshot(registry), 1_000_000)
            context = application.capture_performance_context(
                preparation.context_request,
                controller,
                1_010_000,
                source_slot="main",
            )
            with self.assertRaises(DirectedPerformanceError) as caught:
                application.compile_directed_performance(preparation, context)
        self.assertEqual(caught.exception.code, "private_content")
        self.assertNotIn("privatecanary", str(caught.exception))

    def test_prepare_publish_and_activate_use_the_existing_scheduler(self):
        preparation = DirectedPerformancePreparationV1.from_mapping(
            preparation_mapping()
        )
        registry = load_character_registry()
        manifest = derive_character_capability_manifest()
        package = registry.get(registry.default_character_id)
        with tempfile.TemporaryDirectory() as temporary:
            repository = CompiledScoreRepository(temporary)
            application = PerformanceApplication(
                "wizard-runtime-directed-activation",
                score_repository=repository,
                character_id=registry.default_character_id,
                package_digest=package.package_sha256,
                manifest_digest=manifest["manifest_sha256"],
                capability_manifest=manifest,
                character_registry=registry,
            )
            controller = WizardAvatarController(
                ("front_idle",),
                registry.default_character_id,
            )
            application.accept_snapshot(main_snapshot(registry), 1_000_000)
            context = application.capture_performance_context(
                preparation.context_request,
                controller,
                1_010_000,
                source_slot="main",
            )

            first = application.compile_directed_performance(
                preparation,
                context,
            )
            second = application.compile_directed_performance(
                preparation,
                context,
            )
            self.assertEqual(
                first.score.artifact_sha256,
                second.score.artifact_sha256,
            )

            prepared = application.publish_directed_performance(first)
            binding = prepared.score_binding.to_dict()
            loaded = repository.load_current(MEDIA_DIGEST)
            self.assertEqual(
                binding["score_sha256"],
                loaded.artifact_sha256,
            )
            self.assertEqual(
                binding["prepared_from_context_sha256"],
                context.context_sha256,
            )

            playing = main_snapshot(
                registry,
                sequence=1,
                state="playing",
                position_ms=4_500,
                score_binding=binding,
            )
            score_ready = application.prepare_snapshot(playing)
            ack = application.accept_snapshot(playing, 2_000_000)
            projected = application.apply(controller, 2_000_000)

        self.assertTrue(score_ready.ready)
        self.assertEqual(ack.scheduler_state, "playing")
        self.assertTrue(projected.active)
        self.assertIsNotNone(projected.resolution_hash)
        self.assertEqual(
            prepared.preliminary_context.source.source_slot,
            "main",
        )
        self.assertEqual(
            prepared.preliminary_context.pipeline.tts_readiness,
            "not_requested",
        )
        self.assertEqual(prepared.preliminary_context.pipeline.observed_stage, "none")
        self.assertEqual(prepared.preliminary_context.pipeline.mapped_status, "none")
        self.assertEqual(prepared.preliminary_context.character.gaze, "automatic")
        self.assertEqual(prepared.preliminary_context.governance.memory_scope, "none")
        self.assertEqual(prepared.preliminary_context.governance.notification_scope, "none")


class PerformanceContextObservationTests(unittest.TestCase):
    def setUp(self):
        self.request = PerformanceContextRequestV1.from_mapping(
            preparation_mapping()["context_request"]
        )
        self.clock = {"now": 1_700_000_000_000}
        self.controller = WizardAvatarController(
            ("front_idle",),
            clock_ms=lambda: self.clock["now"],
        )

    def prism_stage(self, *, turn_id=None, utterance_id=None, stage="reviewing"):
        return {
            "schema_version": 2,
            "event_id": "00000000-0000-4000-8000-000000000123",
            "source_epoch": "prism-context-observation",
            "source_sequence": 1,
            "emitted_at_ms": self.clock["now"],
            "ttl_ms": 5_000,
            "kind": "stage",
            "classification": "visual_advisory_only",
            "provenance_class": "runtime_lifecycle",
            "sanitization_version": 1,
            "turn_id": turn_id or self.request.turn_id,
            "utterance_id": utterance_id or self.request.utterance_id,
            "payload": {"stage": stage, "status": "active"},
        }

    def test_pipeline_uses_only_turn_correlated_prism_stage(self):
        self.controller.prism_advisories.accept(
            self.prism_stage(),
            now_ms=self.clock["now"],
        )
        observed = PerformanceApplication._observed_pipeline_context(
            self.request,
            self.controller,
            source_slot="main",
            playback_state="paused",
            now_monotonic_ms=42,
        )
        self.assertEqual(observed["observed_stage"], "reviewing")
        self.assertEqual(observed["mapped_status"], "active")
        self.assertEqual(observed["expected_next_event"], "stage_changed")

    def test_pipeline_ignores_a_different_turn(self):
        self.controller.prism_advisories.accept(
            self.prism_stage(turn_id="turn:other"),
            now_ms=self.clock["now"],
        )
        observed = PerformanceApplication._observed_pipeline_context(
            self.request,
            self.controller,
            source_slot="main",
            playback_state="paused",
            now_monotonic_ms=42,
        )
        self.assertEqual(observed["observed_stage"], "none")
        self.assertEqual(observed["mapped_status"], "none")

    def test_pipeline_ignores_an_expired_stage_before_the_next_tick(self):
        self.controller.prism_advisories.accept(
            self.prism_stage(),
            now_ms=self.clock["now"],
        )
        self.clock["now"] += 5_000
        observed = PerformanceApplication._observed_pipeline_context(
            self.request,
            self.controller,
            source_slot="main",
            playback_state="paused",
            now_monotonic_ms=42,
        )
        self.assertEqual(observed["observed_stage"], "none")
        self.assertEqual(observed["mapped_status"], "none")

    def test_gaze_reports_actual_controller_authority(self):
        self.assertEqual(
            PerformanceApplication._observed_gaze(self.controller.state),
            "automatic",
        )
        self.controller.state.gaze_authoritative = True
        self.controller.state.gaze_aim = -1
        self.assertEqual(
            PerformanceApplication._observed_gaze(self.controller.state),
            "left",
        )


class DirectedPerformanceServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_director_source_slot_inspection_is_authenticated_and_content_free(self):
        registry = load_character_registry()
        env = {
            "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
            "WIZARD_MEDIA_CONNECTOR_TOKEN": "director-test-token",
        }
        headers = (("authorization", "Bearer director-test-token"),)
        media_headers = (
            ("content-type", "application/json"),
            ("authorization", "Bearer director-test-token"),
        )
        media_body = json.dumps(
            main_snapshot(registry).to_dict(),
            separators=(",", ":"),
        ).encode("utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(os.environ, env, clear=True):
                app = create_app(
                    score_repository=CompiledScoreRepository(temporary)
                )
            path = "/api/avatar/wizard/director/v1/source-slots/main"
            unauthorized, _ = await asgi_request(app, "GET", path)
            missing_status, missing = await asgi_request(
                app, "GET", path, headers=headers
            )
            invalid_status, invalid = await asgi_request(
                app,
                "GET",
                "/api/avatar/wizard/director/v1/source-slots/private",
                headers=headers,
            )
            await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/media-session",
                media_body,
                media_headers,
            )
            ready_status, ready = await asgi_request(
                app, "GET", path, headers=headers
            )
            await app.state.frame_hub.stop()

        self.assertEqual(unauthorized, 401)
        self.assertEqual(missing_status, 200)
        self.assertEqual(missing["status"], "unavailable")
        self.assertEqual(invalid_status, 400)
        self.assertEqual(invalid["detail"]["code"], "source_slot_invalid")
        self.assertEqual(ready_status, 200)
        self.assertEqual(ready["status"], "ready")
        self.assertEqual(ready["source_slot"], "main")
        self.assertEqual(ready["media"]["media_id"], MEDIA_ID)
        self.assertEqual(ready["media"]["media_sha256"], MEDIA_DIGEST)
        self.assertEqual(ready["media"]["duration_ms"], DURATION_MS)
        self.assertEqual(
            ready["performance"]["character_id"],
            registry.default_character_id,
        )
        encoded = json.dumps(ready, separators=(",", ":"))
        self.assertNotIn("connector", encoded)
        self.assertNotIn("message", encoded)
        self.assertNotIn("title", encoded)

    async def test_companion_director_uses_app_token_not_connector_token(self):
        env = {
            "WIZARD_COMPANION_MODE": "1",
            "WIZARD_COMPANION_APP_TOKEN": "private-app-token",
            "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
            "WIZARD_MEDIA_CONNECTOR_TOKEN": "separate-connector-token",
        }
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(os.environ, env, clear=True):
                app = create_app(
                    score_repository=CompiledScoreRepository(temporary)
                )
            path = "/api/avatar/wizard/director/v1/performances/prepare-editable"
            connector_status, _ = await asgi_request(
                app,
                "POST",
                path,
                b"",
                (("authorization", "Bearer separate-connector-token"),),
            )
            app_status, _ = await asgi_request(
                app,
                "POST",
                path,
                b"",
                (("authorization", "Bearer private-app-token"),),
            )
            origin_status, _ = await asgi_request(
                app,
                "POST",
                path,
                b"",
                (
                    ("authorization", "Bearer private-app-token"),
                    ("origin", "http://127.0.0.1:8765"),
                ),
            )
            await app.state.frame_hub.stop()

        self.assertEqual(connector_status, 401)
        self.assertEqual(app_status, 415)
        self.assertEqual(origin_status, 403)

    async def test_authenticated_edit_session_applies_and_publishes_content_free_edit(self):
        registry = load_character_registry()
        direction = preparation_mapping()["direction"]["direction_text"]
        media_body = json.dumps(
            main_snapshot(registry).to_dict(),
            separators=(",", ":"),
        ).encode("utf-8")
        preparation_body = json.dumps(
            preparation_mapping(),
            separators=(",", ":"),
        ).encode("utf-8")
        env = {
            "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
            "WIZARD_MEDIA_CONNECTOR_TOKEN": "director-test-token",
        }
        with tempfile.TemporaryDirectory() as temporary:
            repository = CompiledScoreRepository(temporary)
            with mock.patch.dict(os.environ, env, clear=True):
                app = create_app(score_repository=repository)
            headers = (
                ("content-type", "application/json"),
                ("authorization", "Bearer director-test-token"),
            )
            await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/media-session",
                media_body,
                headers,
            )
            unauthorized, _ = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/director/v1/performances/prepare-editable",
                preparation_body,
                (("content-type", "application/json"),),
            )
            prepared_status, prepared = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/director/v1/performances/prepare-editable",
                preparation_body,
                headers,
            )
            inspection = prepared["edit_session"]
            cue = inspection["cues"][0]
            edits = ScoreEditsV1.build(
                {
                    "schema_version": 1,
                    "edit_set_id": "edits:http-director-0001",
                    "revision": 1,
                    "character_id": inspection["character_id"],
                    "package_digest": inspection["package_digest"],
                    "base_score_sha256": inspection["base_score_sha256"],
                    "parent_edit_set_sha256": None,
                    "actor": {
                        "kind": "human",
                        "actor_id": "local:director-test",
                    },
                    "operations": [
                        {
                            "operation_id": "op:http-disable-0001",
                            "cue_id": cue["cue_id"],
                            "edit_type": "disabled",
                            "expected_value_sha256": cue["edit_preconditions"][
                                "disabled"
                            ],
                            "value": True,
                            "reason_code": "director_choice",
                        }
                    ],
                }
            )
            apply_status, applied = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/director/v1/edit-sessions/{}/apply".format(
                    inspection["edit_session_id"]
                ),
                json.dumps(edits.to_dict(), separators=(",", ":")).encode(
                    "utf-8"
                ),
                headers,
            )
            loaded = repository.load_current(MEDIA_DIGEST)
            replay_status, replay = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/director/v1/edit-sessions/{}/apply".format(
                    inspection["edit_session_id"]
                ),
                json.dumps(edits.to_dict(), separators=(",", ":")).encode(
                    "utf-8"
                ),
                headers,
            )
            await app.state.frame_hub.stop()

        self.assertEqual(unauthorized, 401)
        self.assertEqual(prepared_status, 200)
        self.assertEqual(apply_status, 200)
        self.assertEqual(applied["publication"]["revision"], 2)
        self.assertEqual(applied["edit_session"]["score_revision"], 2)
        self.assertEqual(loaded.revision, 2)
        self.assertEqual(replay_status, 409)
        self.assertEqual(replay["detail"]["code"], "stale_binding")
        self.assertTrue(applied["edit_session"]["cues"][0]["disabled"])
        encoded = json.dumps(
            {"prepared": prepared, "applied": applied},
            separators=(",", ":"),
        )
        self.assertNotIn(direction, encoded)
        self.assertNotIn("capability_requirements", encoded)

    async def test_authenticated_route_prepares_content_free_binding(self):
        registry = load_character_registry()
        body = json.dumps(
            preparation_mapping(),
            separators=(",", ":"),
        ).encode("utf-8")
        media_body = json.dumps(
            main_snapshot(registry).to_dict(),
            separators=(",", ":"),
        ).encode("utf-8")
        env = {
            "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
            "WIZARD_MEDIA_CONNECTOR_TOKEN": "director-test-token",
        }
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(os.environ, env, clear=True):
                app = create_app(
                    score_repository=CompiledScoreRepository(temporary)
                )
            headers = (
                ("content-type", "application/json"),
                ("authorization", "Bearer director-test-token"),
            )
            media_status, _ = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/media-session",
                media_body,
                headers,
            )
            unauthorized, _ = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/director/v1/performances/prepare",
                body,
                (("content-type", "application/json"),),
            )
            status, payload = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/director/v1/performances/prepare",
                body,
                headers,
            )
            await app.state.frame_hub.stop()

        self.assertEqual(media_status, 200)
        self.assertEqual(unauthorized, 401)
        self.assertEqual(status, 200)
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("score_binding", payload)
        encoded = json.dumps(payload, separators=(",", ":"))
        self.assertNotIn(
            preparation_mapping()["direction"]["direction_text"],
            encoded,
        )

    async def test_route_rejects_media_duration_mismatch(self):
        registry = load_character_registry()
        media_value = main_snapshot(registry).to_dict()
        media_value = deepcopy(media_value)
        media_value["media"]["duration_ms"] = DURATION_MS + 1
        env = {
            "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
            "WIZARD_MEDIA_CONNECTOR_TOKEN": "director-test-token",
        }
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(os.environ, env, clear=True):
                app = create_app(
                    score_repository=CompiledScoreRepository(temporary)
                )
            headers = (
                ("content-type", "application/json"),
                ("authorization", "Bearer director-test-token"),
            )
            await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/media-session",
                json.dumps(media_value, separators=(",", ":")).encode("utf-8"),
                headers,
            )
            status, payload = await asgi_request(
                app,
                "POST",
                "/api/avatar/wizard/director/v1/performances/prepare",
                json.dumps(
                    preparation_mapping(),
                    separators=(",", ":"),
                ).encode("utf-8"),
                headers,
            )
            await app.state.frame_hub.stop()

        self.assertEqual(status, 409)
        self.assertEqual(payload["detail"]["code"], "media_session_mismatch")

    async def test_context_change_during_compile_revokes_publication(self):
        registry = load_character_registry()
        preparation = DirectedPerformancePreparationV1.from_mapping(
            preparation_mapping()
        )
        with tempfile.TemporaryDirectory() as temporary:
            repository = CompiledScoreRepository(temporary)
            hub = WizardFrameHub(
                ProceduralWizardFrameSource(),
                score_repository=repository,
            )
            await hub.accept_media_session(
                main_snapshot(registry),
                1_000_000,
            )
            original = hub.performance.compile_directed_performance

            def compile_after_cancellation(preparation_value, context):
                compiled = original(preparation_value, context)
                hub.performance.scheduler.coordinator.rotate_runtime_epoch(
                    "wizard-runtime-directed-cancelled"
                )
                return compiled

            with mock.patch.object(
                hub.performance,
                "compile_directed_performance",
                side_effect=compile_after_cancellation,
            ):
                with self.assertRaises(DirectedPerformanceError) as caught:
                    await hub.prepare_directed_performance(preparation)
            await hub.stop()

            self.assertEqual(caught.exception.code, "media_session_changed")
            self.assertFalse((repository.root / "media").exists())


if __name__ == "__main__":
    unittest.main()
