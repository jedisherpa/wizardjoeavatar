import asyncio
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.character_package import (
    CharacterPackageValidationError,
    WIZARD_JOE_PACKAGE_PATH,
    load_character_package,
)
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.frame_hash import frame_hash
from wizard_avatar.server import create_app
from wizard_avatar.stream import WizardFrameHub, character_runtime_epoch_prefix


SERENA_PACKAGE_PATH = (
    Path(__file__).resolve().parents[2]
    / "wizard_avatar"
    / "definitions"
    / "characters"
    / "serena_quill"
    / "serena_quill_character_package_v2.json"
)
LOOPBACK_HEADERS = (("host", "127.0.0.1:43123"),)


async def asgi_request(app, method, path, headers=()):
    messages = []
    delivered = False

    async def receive():
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": b"", "more_body": False}

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
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 43123),
    }
    await app(scope, receive, send)
    status = next(
        message["status"]
        for message in messages
        if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return status, json.loads(body) if body else None


class SerenaRuntimeBootTests(unittest.IsolatedAsyncioTestCase):
    def create_source(self):
        return ProceduralWizardFrameSource(
            cols=96,
            rows=54,
            fps=24,
            character_package_path=SERENA_PACKAGE_PATH,
        )

    def test_serena_package_owns_initial_runtime_state_and_first_frame(self):
        first = self.create_source()
        second = self.create_source()

        state = first.current_state()
        self.assertEqual(state.character_id, "serena-quill-v1")
        self.assertEqual(state.pose_id, "neutral_front")
        self.assertEqual(state.animation_node_id, "node_neutral_front")
        self.assertEqual(state.animation_clip_id, "pose_neutral_front")
        first_cells = first.render_current_frame().cells
        self.assertEqual(first_cells, second.render_current_frame().cells)
        self.assertEqual(frame_hash(first_cells), "fnv1a32:4348c1bb")

    def test_epoch_namespaces_preserve_wizard_and_name_serena(self):
        self.assertEqual(
            character_runtime_epoch_prefix("wizard-joe-v1"),
            "wizard",
        )
        self.assertEqual(
            character_runtime_epoch_prefix("serena-quill-v1"),
            "serena_quill",
        )

    def test_v2_whole_pose_face_is_not_repainted_by_wizard_overlays(self):
        source = self.create_source()
        canvas, _, mouth_anchor = source._reference_pose_canvas_for_sample(
            "neutral_front"
        )
        before = canvas.to_frame_bytes()
        state = source.current_state()
        state.expression = "happy"
        state.mouth = "open_wide"
        state.blink_phase = 1.0

        source._apply_reference_face_channels(
            canvas,
            state,
            "neutral_front",
            mouth_anchor,
        )

        self.assertEqual(canvas.to_frame_bytes(), before)

    def test_v2_capability_profile_must_match_its_package_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            copied_root = Path(directory) / "serena_quill"
            shutil.copytree(SERENA_PACKAGE_PATH.parent, copied_root)
            package_path = copied_root / SERENA_PACKAGE_PATH.name
            capability_path = (
                copied_root / "serena_quill_capability_profile_v1.json"
            )
            capability = json.loads(capability_path.read_text(encoding="utf-8"))
            capability["renderer_adapter_id"] = "asciline.legacy_square_cells.v1"
            capability_bytes = (
                json.dumps(capability, indent=2, sort_keys=True).encode("utf-8")
                + b"\n"
            )
            capability_path.write_bytes(capability_bytes)
            package = json.loads(package_path.read_text(encoding="utf-8"))
            package["assets"]["capability_manifest"]["sha256"] = (
                "sha256:" + hashlib.sha256(capability_bytes).hexdigest()
            )
            package_path.write_text(
                json.dumps(package, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CharacterPackageValidationError,
                "renderer_adapter_id does not match",
            ):
                load_character_package(package_path)

    async def test_hd_review_assets_require_exact_wizard_runtime_hashes(self):
        canonical = load_character_package(WIZARD_JOE_PACKAGE_PATH)
        with tempfile.TemporaryDirectory() as directory:
            copied_root = Path(directory)
            package_path = copied_root / WIZARD_JOE_PACKAGE_PATH.name
            shutil.copy2(canonical.pose_library, copied_root / canonical.pose_library.name)
            shutil.copy2(
                canonical.animation_graph,
                copied_root / canonical.animation_graph.name,
            )
            copied_graph = copied_root / canonical.animation_graph.name
            copied_graph.write_text(
                copied_graph.read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
            )
            shutil.copy2(WIZARD_JOE_PACKAGE_PATH, package_path)
            app = create_app(
                ProceduralWizardFrameSource(
                    cols=96,
                    rows=54,
                    fps=24,
                    character_package_path=package_path,
                ),
                companion_mode=False,
            )
            status, health = await asgi_request(
                app,
                "GET",
                "/api/companion/health",
                headers=LOOPBACK_HEADERS,
            )
            self.assertEqual(status, 200)
            self.assertFalse(health["hd_review_projection"])
            await app.state.frame_hub.stop()

    async def test_existing_hub_binds_serena_hashes_and_character_epoch(self):
        source = self.create_source()
        hub = WizardFrameHub(source)
        package = source.character_package

        self.assertTrue(hub.runtime_epoch.startswith("serena_quill-"))
        self.assertEqual(hub.performance.character_id, package.character_id)
        self.assertEqual(hub.performance.package_digest, package.package_sha256)
        self.assertEqual(
            hub.performance.manifest_digest,
            package.assets["capability_manifest"].sha256,
        )
        self.assertEqual(
            hub.performance.permission_world_capabilities.prop_ids,
            (),
        )
        await hub.stop()

    async def test_existing_server_reports_serena_without_wizard_hd_claims(self):
        app = create_app(self.create_source(), companion_mode=False)
        status, health = await asgi_request(
            app,
            "GET",
            "/api/companion/health",
            headers=LOOPBACK_HEADERS,
        )
        self.assertEqual(status, 200)
        self.assertEqual(health["character_id"], "serena-quill-v1")
        self.assertTrue(health["runtime_epoch"].startswith("serena_quill-"))
        self.assertFalse(health["hd_review_projection"])
        self.assertFalse(health["hd_runtime_admitted"])
        identity_status, identity = await asgi_request(
            app,
            "GET",
            "/api/avatar/wizard/runtime-identity",
            headers=LOOPBACK_HEADERS,
        )
        self.assertEqual(identity_status, 200)
        self.assertEqual(
            identity["character"],
            {
                "character_id": "serena-quill-v1",
                "character_package_sha256": (
                    app.state.frame_hub.frame_source.character_package.package_sha256
                ),
            },
        )
        await app.state.frame_hub.stop()


if __name__ == "__main__":
    unittest.main()
