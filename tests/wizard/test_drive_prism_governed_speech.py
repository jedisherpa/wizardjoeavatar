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
    validate_disposable_loopback_url,
)


class FakeCdp:
    def __init__(self, target=None, activated=True, command_result=None):
        self.target = target
        self.activated = activated
        self.command_result = command_result
        self.commands = []
        self.evaluations = 0

    async def evaluate(self, _script):
        self.evaluations += 1
        return self.target if self.evaluations == 1 else self.activated

    async def command(self, method, params=None):
        self.commands.append((method, params))
        return self.command_result or {}


class GovernedSpeechDriverTests(unittest.TestCase):
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

    async def test_playback_recovery_invokes_native_play_with_user_gesture(self):
        cdp = FakeCdp(
            command_result={
                "result": {
                    "type": "object",
                    "value": {"attempted": True, "status": "pending"},
                }
            }
        )

        result = await resume_speech_playback_with_user_gesture(cdp)

        self.assertEqual(result, {"attempted": True, "status": "pending"})
        self.assertEqual(len(cdp.commands), 1)
        method, params = cdp.commands[0]
        self.assertEqual(method, "Runtime.evaluate")
        self.assertTrue(params["userGesture"])
        self.assertFalse(params["awaitPromise"])
        self.assertIn("audio.play()", params["expression"])

    async def test_playback_recovery_surfaces_browser_evaluation_error(self):
        cdp = FakeCdp(command_result={"result": {"subtype": "error"}})

        with self.assertRaises(BrowserCaptureFailure):
            await resume_speech_playback_with_user_gesture(cdp)

if __name__ == "__main__":
    unittest.main()
