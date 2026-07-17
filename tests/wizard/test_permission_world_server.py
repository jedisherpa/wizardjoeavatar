import json
import os
import unittest
from unittest import mock

from tests.wizard.test_media_session import snapshot_mapping
from tests.wizard.test_media_session_server import asgi_request
from wizard_avatar.permission_world import (
    PERMISSION_WORLD_MAX_BODY_BYTES,
    CapabilityPermissionV1,
    PermissionWorldCapabilityIndexV1,
    PermissionWorldStateV1,
)
from wizard_avatar.server import create_app


class PermissionWorldServerTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def bind_test_permission_surfaces(app):
        app.state.frame_hub.performance.permission_world_capabilities = (
            PermissionWorldCapabilityIndexV1(
                world_state_ids=(),
                effect_ids=("magic_effect",),
                prop_ids=(),
            )
        )

    def permission_state(self):
        return PermissionWorldStateV1.build(
            source_epoch="permission-source:server-1",
            observed_at_ms=5_000,
            permissions=(
                CapabilityPermissionV1(
                    capability_kind="effect:magic_effect",
                    posture="granted",
                    required_scope_class="current_surface",
                    granted_scope_class="current_surface",
                    purpose_code="calendar_coordination",
                    granted_at_ms=4_000,
                    affected_surfaces=("companion.calendar", "wizard.calendar"),
                    app_link_state="linked",
                    expires_at_ms=9_000_000_000_000,
                    revoked=False,
                ),
            ),
        )

    async def test_connector_writes_and_app_token_inspects_exact_facts(self):
        with mock.patch.dict(
            os.environ,
            {
                "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
                "WIZARD_MEDIA_CONNECTOR_TOKEN": "connector-secret",
            },
            clear=False,
        ):
            app = create_app(companion_mode=True, app_token="app-secret")
        self.bind_test_permission_surfaces(app)

        state = self.permission_state()
        status, payload = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/permission-world",
            state.canonical_json(),
            headers=(
                ("authorization", "Bearer connector-secret"),
                ("content-type", "application/json"),
            ),
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ready")

        unauthorized, _payload = await asgi_request(
            app,
            "GET",
            "/api/avatar/wizard/permission-world",
        )
        self.assertEqual(unauthorized, 401)

        status, payload = await asgi_request(
            app,
            "GET",
            "/api/avatar/wizard/permission-world",
            headers=(("authorization", "Bearer app-secret"),),
        )
        self.assertEqual(status, 200)
        permission = payload["state"]["permissions"][0]
        self.assertEqual(permission["purpose_code"], "calendar_coordination")
        self.assertEqual(
            permission["affected_surfaces"],
            ["companion.calendar", "wizard.calendar"],
        )
        self.assertEqual(
            payload["projection"]["affordances"][0]["availability"],
            "available",
        )
        self.assertEqual(payload["runtime"]["visible_surfaces"]["effects"], ["magic_effect"])
        self.assertNotIn("source_epoch", payload["runtime"])

        simulation = PermissionWorldStateV1.build(
            source_epoch="director-simulation:v1",
            observed_at_ms=6_000,
            permissions=(
                CapabilityPermissionV1(
                    capability_kind="director.simulation",
                    posture="denied",
                    required_scope_class="current_surface",
                    granted_scope_class=None,
                    purpose_code="director_preview",
                    granted_at_ms=None,
                    affected_surfaces=("companion.stage",),
                    app_link_state="not_required",
                    expires_at_ms=None,
                    revoked=False,
                ),
            ),
        )
        status, payload = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/director/permission-world",
            simulation.canonical_json(),
            headers=(
                ("authorization", "Bearer app-secret"),
                ("content-type", "application/json"),
            ),
        )
        self.assertEqual(status, 200)
        self.assertIsNotNone(payload["simulation_state"])
        self.assertEqual(
            payload["simulation_projection"]["affordances"][0]["reason_code"],
            "permission_denied",
        )

        status, payload = await asgi_request(
            app,
            "GET",
            "/api/avatar/wizard/permission-world",
            headers=(("authorization", "Bearer app-secret"),),
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["state"], state.to_dict())
        self.assertEqual(
            payload["simulation_state"]["source_epoch"],
            "director-simulation:{}".format(app.state.frame_hub.runtime_epoch),
        )
        await app.state.frame_hub.stop()

    async def test_permission_endpoint_enforces_auth_origin_content_type_and_body_limit(self):
        with mock.patch.dict(
            os.environ,
            {
                "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
                "WIZARD_MEDIA_CONNECTOR_TOKEN": "connector-secret",
            },
            clear=True,
        ):
            app = create_app()
        self.bind_test_permission_surfaces(app)
        body = self.permission_state().canonical_json()
        json_header = (("content-type", "application/json"),)
        connector = (("authorization", "Bearer connector-secret"),)

        status, _ = await asgi_request(
            app, "POST", "/api/avatar/wizard/permission-world", body, json_header
        )
        self.assertEqual(status, 401)

        status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/permission-world",
            body,
            json_header + connector + (("origin", "http://127.0.0.1:8765"),),
        )
        self.assertEqual(status, 403)

        status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/permission-world",
            body,
            connector + (("content-type", "text/plain"),),
        )
        self.assertEqual(status, 415)

        status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/permission-world",
            b" " * (PERMISSION_WORLD_MAX_BODY_BYTES + 1),
            json_header
            + connector
            + (("content-length", str(PERMISSION_WORLD_MAX_BODY_BYTES + 1)),),
        )
        self.assertEqual(status, 413)

        private = self.permission_state().to_dict()
        private["permissions"][0]["prompt"] = "private-canary"
        status, payload = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/permission-world",
            json.dumps(private).encode("utf-8"),
            json_header + connector,
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["detail"]["code"], "unknown_field")
        self.assertNotIn("private-canary", json.dumps(payload))
        await app.state.frame_hub.stop()

    async def test_duplicate_stale_epoch_and_current_motion_profile_are_runtime_visible(self):
        with mock.patch.dict(
            os.environ,
            {
                "WIZARD_MEDIA_CONNECTOR_ENABLED": "1",
                "WIZARD_MEDIA_CONNECTOR_TOKEN": "connector-secret",
            },
            clear=True,
        ):
            app = create_app()
        self.bind_test_permission_surfaces(app)
        headers = (
            ("authorization", "Bearer connector-secret"),
            ("content-type", "application/json"),
        )
        media = snapshot_mapping(with_hashes=False)
        media["performance"]["motion_profile"] = "reduced"
        status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/media-session",
            json.dumps(media).encode("utf-8"),
            headers,
        )
        self.assertEqual(status, 200)

        accepted = self.permission_state()
        status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/permission-world",
            accepted.canonical_json(),
            headers,
        )
        self.assertEqual(status, 200)

        status, payload = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/permission-world",
            accepted.canonical_json(),
            headers,
        )
        self.assertEqual(status, 409)
        self.assertEqual(payload["detail"]["code"], "replayed_state")

        next_epoch = PermissionWorldStateV1.build(
            source_epoch="permission-source:server-2",
            observed_at_ms=5_001,
            permissions=accepted.permissions,
        )
        status, _ = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/permission-world",
            next_epoch.canonical_json(),
            headers,
        )
        self.assertEqual(status, 200)

        status, payload = await asgi_request(
            app,
            "POST",
            "/api/avatar/wizard/permission-world",
            accepted.canonical_json(),
            headers,
        )
        self.assertEqual(status, 409)
        self.assertEqual(payload["detail"]["code"], "retired_source_epoch")

        status, payload = await asgi_request(app, "GET", "/api/avatar/wizard/state")
        self.assertEqual(status, 200)
        permission_runtime = payload["permission_world"]
        self.assertEqual(permission_runtime["motion_profile"], "reduced")
        self.assertEqual(permission_runtime["visible_surfaces"]["effects"], ["magic_effect"])
        self.assertNotIn("source_epoch", permission_runtime)
        await app.state.frame_hub.stop()


if __name__ == "__main__":
    unittest.main()
