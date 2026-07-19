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
    manifest_artifact_path,
    validate_disposable_loopback_url,
)


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


if __name__ == "__main__":
    unittest.main()
