import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from drive_prism_governed_speech import (
    BrowserCaptureFailure,
    establish_audio_user_gesture,
    manifest_artifact_path,
    parse_args,
    resume_speech_playback_with_user_gesture,
    start_main_playback_with_user_gesture,
    summarize_governed_registration_request,
    summarize_media_session_request,
    validate_disposable_loopback_url,
)
from prism_connector_lifecycle_receipt import (
    LIFECYCLE_RECEIPT_SCHEMA,
    evaluate_connector_lifecycle_receipt,
)


def lifecycle_receipt():
    session_sha256 = "sha256:" + "a" * 64

    def phase(slot, observed_ms, position_ms, media_id, media_sha256, mouth="closed"):
        return {
            "observed_at_utc": "2026-08-08T00:00:00Z",
            "observed_monotonic_ms": observed_ms,
            "source_slot": slot,
            "browser": {
                "playing": True,
                "position_ms": position_ms,
                "duration_ms": 60_000,
                "playback_rate_milli": 1000,
            },
            "wizard": {
                "active": True,
                "source_slot": slot,
                "media_time_ms": position_ms - 10,
                "mouth": mouth,
                "speech_mouth_authority": (
                    "media_alignment" if slot == "speech" else None
                ),
            },
            "media": {
                "connector_session_sha256": session_sha256,
                "sequence": observed_ms,
                "media_epoch": 1 if slot == "main" else 2,
                "cause": "playing",
                "media_id": media_id,
                "media_sha256": media_sha256,
            },
            "visible_character_count": 12 if slot == "speech" else 0,
            "absolute_clock_offset_ms": 10,
        }

    main_id = "media:sha256:" + "b" * 64
    main_sha256 = "sha256:" + "b" * 64
    return {
        "schema": LIFECYCLE_RECEIPT_SCHEMA,
        "schema_version": 1,
        "content_free": True,
        "started_at_utc": "2026-08-08T00:00:00Z",
        "completed_at_utc": "2026-08-08T00:00:04Z",
        "thresholds": {
            "maximum_clock_offset_ms": 100,
            "reconnect_recovery_limit_ms": 3000,
        },
        "phases": {
            "main_before": phase("main", 100, 1_000, main_id, main_sha256),
            "speech": phase(
                "speech",
                200,
                100,
                "media:sha256:" + "c" * 64,
                "sha256:" + "c" * 64,
                mouth="open_small",
            ),
            "main_after": phase("main", 300, 2_500, main_id, main_sha256),
        },
        "reconnect": {
            "before_runtime_epoch": "wizard-runtime-before",
            "after_runtime_epoch": "wizard-runtime-after",
            "recovery_ms": 900,
            "reconnect_cause_observed": True,
            "main_restored": True,
            "obsolete_speech_inactive": True,
            "restart_command_sha256": "sha256:" + "d" * 64,
            "restart_command_duration_ms": 100,
        },
        "stale_replay": {
            "disposition": "stale",
            "error_code": "stale_sequence",
            "main_remained_active": True,
            "obsolete_speech_inactive": True,
        },
    }


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
    def test_can_defer_v2_specific_review_products(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scenario = root / "scenario.json"
            scenario.write_text("{}", encoding="utf-8")
            args = parse_args(
                [
                    "--receipt",
                    str(root / "receipt.json"),
                    "--scenarios-file",
                    str(scenario),
                    "--defer-review-products",
                ]
            )

        self.assertTrue(args.defer_review_products)
        self.assertFalse(args.lifecycle_proof)

    def test_lifecycle_proof_is_explicit_and_preserves_restart_argv(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scenario = root / "scenario.json"
            scenario.write_text("{}", encoding="utf-8")
            args = parse_args(
                [
                    "--receipt",
                    str(root / "receipt.json"),
                    "--scenarios-file",
                    str(scenario),
                    "--lifecycle-proof",
                    "--lifecycle-restart-command",
                    "/usr/bin/true",
                    "--opaque-restart-argument",
                ]
            )

        self.assertTrue(args.lifecycle_proof)
        self.assertEqual(
            args.lifecycle_restart_command,
            ["/usr/bin/true", "--opaque-restart-argument"],
        )

    def test_lifecycle_proof_requires_disposable_restart_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scenario = root / "scenario.json"
            scenario.write_text("{}", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    parse_args(
                        [
                            "--receipt",
                            str(root / "receipt.json"),
                            "--scenarios-file",
                            str(scenario),
                            "--lifecycle-proof",
                        ]
                    )

    def test_accepts_complete_content_free_lifecycle_receipt(self):
        result = evaluate_connector_lifecycle_receipt(lifecycle_receipt())

        self.assertTrue(result["passed"])
        self.assertEqual(result["metrics"]["main_advance_ms"], 1500)
        self.assertEqual(result["metrics"]["privacy_violation_count"], 0)

    def test_lifecycle_receipt_rejects_private_text_keys(self):
        receipt = lifecycle_receipt()
        receipt["phases"]["speech"]["approved_text"] = "must never be retained"

        result = evaluate_connector_lifecycle_receipt(receipt)

        self.assertFalse(result["passed"])
        self.assertIn("$.phases.speech.approved_text", result["privacy_violation_paths"])

    def test_lifecycle_receipt_rejects_rewound_or_substituted_main(self):
        receipt = lifecycle_receipt()
        receipt["phases"]["main_after"]["browser"]["position_ms"] = 500
        receipt["phases"]["main_after"]["media"]["media_id"] = (
            "media:sha256:" + "e" * 64
        )

        result = evaluate_connector_lifecycle_receipt(receipt)

        checks = {check["name"]: check["passed"] for check in result["checks"]}
        self.assertFalse(checks["main_identity_continued_and_advanced"])

    def test_lifecycle_receipt_rejects_missing_reconnect_and_accepted_stale_turn(self):
        receipt = lifecycle_receipt()
        receipt["reconnect"]["after_runtime_epoch"] = "wizard-runtime-before"
        receipt["stale_replay"]["disposition"] = "accepted"
        receipt["stale_replay"]["obsolete_speech_inactive"] = False

        result = evaluate_connector_lifecycle_receipt(receipt)

        checks = {check["name"]: check["passed"] for check in result["checks"]}
        self.assertFalse(checks["runtime_reconnected_within_budget"])
        self.assertFalse(checks["stale_speech_replay_rejected"])

    def test_lifecycle_validator_does_not_mutate_input(self):
        receipt = lifecycle_receipt()
        original = deepcopy(receipt)

        evaluate_connector_lifecycle_receipt(receipt)

        self.assertEqual(receipt, original)

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
    async def test_lifecycle_main_play_uses_real_pointer_gesture(self):
        cdp = FakeCdp({"alreadyPlaying": False, "x": 640.0, "y": 680.0})

        result = await start_main_playback_with_user_gesture(cdp)

        self.assertEqual(result, {"already_playing": False, "pointer_dispatched": True})
        self.assertEqual(
            [params["type"] for _, params in cdp.commands],
            ["mousePressed", "mouseReleased"],
        )

    async def test_lifecycle_main_play_preserves_already_playing_media(self):
        cdp = FakeCdp({"alreadyPlaying": True})

        result = await start_main_playback_with_user_gesture(cdp)

        self.assertEqual(result, {"already_playing": True, "pointer_dispatched": False})
        self.assertEqual(cdp.commands, [])

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
