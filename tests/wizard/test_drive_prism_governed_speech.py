import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from drive_prism_governed_speech import (
    BrowserCaptureFailure,
    establish_audio_user_gesture,
    manifest_artifact_path,
    resume_speech_playback_with_user_gesture,
    summarize_governed_registration_request,
    summarize_media_session_request,
    validate_disposable_loopback_url,
)


class FakeCdp:
    def __init__(
        self,
        target=None,
        activated=True,
        command_result=None,
        evaluation_results=None,
    ):
        self.target = target
        self.activated = activated
        self.command_result = command_result
        self.commands = []
        self.evaluations = 0
        self.evaluation_results = list(evaluation_results or [])

    async def evaluate(self, _script):
        self.evaluations += 1
        if self.evaluation_results:
            return self.evaluation_results.pop(0)
        return self.target if self.evaluations == 1 else self.activated

    async def command(self, method, params=None):
        self.commands.append((method, params))
        return self.command_result or {}


class GovernedSpeechDriverTests(unittest.TestCase):
    def test_summarizes_only_media_binding_and_playback_fields(self):
        event = {
            "requestId": "42.1",
            "request": {
                "postData": __import__("json").dumps(
                    {
                        "sequence": 7,
                        "media_epoch": 3,
                        "cause": "playing",
                        "media": {
                            "source_slot": "speech",
                            "media_id": "media:sha256:abc",
                            "media_sha256": "sha256:abc",
                        },
                        "playback": {"state": "playing", "position_ms": 25},
                        "performance": {
                            "character_id": "wizard-joe-v1",
                            "character_package_sha256": "sha256:def",
                        },
                        "private_text": "must not be copied",
                    }
                )
            },
        }

        summary = summarize_media_session_request(event)

        self.assertEqual(summary["sequence"], 7)
        self.assertEqual(summary["source_slot"], "speech")
        self.assertNotIn("private_text", summary)

    def test_summarizes_governed_registration_source_binding(self):
        event = {
            "requestId": "42.2",
            "request": {
                "postData": __import__("json").dumps(
                    {
                        "performance_context": {
                            "source": {
                                "connector_session_id": "session",
                                "accepted_sequence": 6,
                                "media_epoch": 3,
                                "source_slot": "speech",
                                "media_id": "media:sha256:abc",
                                "media_sha256": "sha256:abc",
                            }
                        },
                        "approved_text": "must not be copied",
                    }
                )
            },
        }

        summary = summarize_governed_registration_request(event)

        self.assertEqual(summary["accepted_sequence"], 6)
        self.assertEqual(summary["media_epoch"], 3)
        self.assertNotIn("approved_text", summary)

    def test_resolves_contact_sheet_from_validated_artifact_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            contact_sheet = output / "capture-contact-sheet.png"
            contact_sheet.write_bytes(b"png")
            manifest = {
                "artifacts": [
                    {
                        "path": contact_sheet.name,
                        "media_type": "image/png",
                    }
                ]
            }
            self.assertEqual(
                manifest_artifact_path(
                    manifest,
                    output,
                    path_suffix="-contact-sheet.png",
                    media_type="image/png",
                ),
                contact_sheet.resolve(),
            )

    def test_rejects_missing_or_escaping_review_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for artifact_path in ("missing-contact-sheet.png", "../escape-contact-sheet.png"):
                manifest = {
                    "artifacts": [
                        {"path": artifact_path, "media_type": "image/png"}
                    ]
                }
                with self.subTest(path=artifact_path), self.assertRaises(
                    BrowserCaptureFailure
                ):
                    manifest_artifact_path(
                        manifest,
                        output,
                        path_suffix="-contact-sheet.png",
                        media_type="image/png",
                    )

    def test_accepts_explicit_disposable_loopback_endpoint(self):
        self.assertEqual(
            validate_disposable_loopback_url("http://127.0.0.1:8896/", "wizard"),
            "http://127.0.0.1:8896",
        )

    def test_rejects_protected_ports(self):
        for port in (8765, 8875):
            with self.subTest(port=port), self.assertRaises(ValueError):
                validate_disposable_loopback_url(
                    "http://127.0.0.1:{}".format(port),
                    "wizard",
                )

    def test_rejects_remote_credentials_and_paths(self):
        invalid = (
            "https://127.0.0.1:8896",
            "http://example.com:8896",
            "http://user:secret@127.0.0.1:8896",
            "http://127.0.0.1:8896/private",
            "http://127.0.0.1:8896/?token=secret",
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_disposable_loopback_url(value, "wizard")


class GovernedSpeechDriverAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_audio_activation_uses_real_cdp_pointer_gesture(self):
        cdp = FakeCdp({"x": 120.5, "y": 640.25})

        await establish_audio_user_gesture(cdp)

        self.assertEqual(
            [params["type"] for _, params in cdp.commands],
            ["mousePressed", "mouseReleased"],
        )
        self.assertTrue(
            all(method == "Input.dispatchMouseEvent" for method, _ in cdp.commands)
        )

    async def test_audio_activation_fails_without_prompt_or_user_activation(self):
        with self.assertRaises(BrowserCaptureFailure):
            await establish_audio_user_gesture(FakeCdp(None))
        with self.assertRaises(BrowserCaptureFailure):
            await establish_audio_user_gesture(FakeCdp({"x": 10, "y": 10}, False))

    async def test_playback_recovery_dispatches_gesture_through_application(self):
        cdp = FakeCdp(
            evaluation_results=[
                {"x": 120.5, "y": 640.25},
                {"attempted": True, "status": "playing"},
            ]
        )

        result = await resume_speech_playback_with_user_gesture(cdp)

        self.assertEqual(result, {"attempted": True, "status": "playing"})
        self.assertEqual(
            [params["type"] for _, params in cdp.commands],
            ["mousePressed", "mouseReleased"],
        )
        self.assertTrue(
            all(method == "Input.dispatchMouseEvent" for method, _ in cdp.commands)
        )

    async def test_playback_recovery_skips_missing_gesture_target(self):
        cdp = FakeCdp(evaluation_results=[None])

        result = await resume_speech_playback_with_user_gesture(cdp)

        self.assertEqual(
            result, {"attempted": False, "reason": "missing_gesture_target"}
        )
        self.assertEqual(cdp.commands, [])

if __name__ == "__main__":
    unittest.main()
