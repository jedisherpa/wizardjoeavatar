import json
import tempfile
import unittest
from pathlib import Path

from tools.run_character_observer import (
    _mouth_pair_states,
    _observer_health,
    _observer_html,
    _performance_review_html,
    _record_review_decision,
)


class CharacterObserverTests(unittest.TestCase):
    def test_mouth_pair_states_include_only_complete_open_closed_pairs(self):
        states = _mouth_pair_states(
            {
                "pairs": [
                    {
                        "base_pose_id": "pose-a",
                        "states": {
                            "closed": {"pose_id": "pose-a"},
                            "open": {"pose_id": "pose-a__mouth_open"},
                        },
                    },
                    {
                        "base_pose_id": "pose-b",
                        "states": {"closed": {"pose_id": "pose-b"}},
                    },
                ]
            }
        )

        self.assertEqual(
            states,
            {
                "pose-a": {
                    "closed": "pose-a",
                    "open": "pose-a__mouth_open",
                }
            },
        )

    def test_wizard_review_mode_renders_distinct_sequences(self):
        body = _observer_html(
            joe_port=8666,
            current_port=8666,
            joe_path="/?hd-sequence=approved_hd_frames",
            current_path="/?hd-sequence=phazer_all",
            current_label="Wizard Joe Phazer motion",
            current_meta="48 reconstructed alpha candidates",
        )

        self.assertIn(b"250 approved source frames", body)
        self.assertIn(b"hd-sequence=approved_hd_frames", body)
        self.assertIn(b"Wizard Joe Phazer motion", body)
        self.assertIn(b"48 reconstructed alpha candidates", body)
        self.assertIn(b"hd-sequence=phazer_all", body)

    def test_observer_escapes_review_labels_and_paths(self):
        body = _observer_html(
            joe_port=8666,
            current_port=8666,
            joe_path='/?hd-sequence="approved"',
            current_path='/?hd-sequence=<candidate>',
            current_label="<Wizard>",
            current_meta='"candidate"',
        )

        self.assertNotIn(b"<Wizard>", body)
        self.assertIn(b"&lt;Wizard&gt;", body)
        self.assertIn(b"&quot;candidate&quot;", body)
        self.assertIn(b"hd-sequence=&lt;candidate&gt;", body)
        self.assertIn(b"hd-sequence=&quot;approved&quot;", body)

    def test_observer_health_names_review_character_without_claiming_admission(self):
        payload = _observer_health(
            joe={"status": "ready", "character_id": "wizard-joe-v1"},
            current={"status": "ready", "character_id": "wizard-joe-v1"},
            current_label="Orion Vale",
            current_meta="36 supplied motions",
            review_character_id="orion-vale",
            review_projection=True,
            runtime_admitted=False,
        )

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["baseline"]["display_name"], "HD Wizard Joe")
        self.assertEqual(payload["review"]["character_id"], "orion-vale")
        self.assertEqual(payload["review"]["display_name"], "Orion Vale")
        self.assertTrue(payload["review"]["review_projection"])
        self.assertFalse(payload["review"]["runtime_admitted"])
        self.assertEqual(
            payload["review"]["runtime"]["character_id"],
            "wizard-joe-v1",
        )

    def test_isolated_review_path_can_request_centered_projection(self):
        body = _observer_html(
            joe_port=8666,
            current_port=8667,
            joe_path="/?hd-sequence=approved_local_frames",
            current_path="/?hd-sequence=robin-all&hd-center-isolated=1",
            current_label="Robin",
            current_meta="200 corrected HD poses",
        )

        self.assertIn(
            b"hd-sequence=robin-all&amp;hd-center-isolated=1",
            body,
        )

    def test_audio_performance_review_renders_transport_and_projector(self):
        body = _performance_review_html(
            joe_port=8666,
            observer_port=8665,
            joe_path="/?hd-sequence=approved_hd_frames",
            joe_meta="250 approved source frames",
        )

        self.assertIn(b"Wizard Joe Audio Performance Review", body)
        self.assertIn(b'id="clip"', body)
        self.assertIn(b'id="play"', body)
        self.assertIn(b'id="seek"', body)
        self.assertIn(b"Approve choreography", body)
        self.assertIn(b"hd-performance=1", body)
        self.assertIn(b"controller-origin=http://127.0.0.1:8665", body)
        self.assertIn(b"audio.currentTime", body)
        self.assertIn(b"mouthStateAt", body)
        self.assertIn(b"poseForMouthState", body)

    def test_review_decision_is_persisted_without_runtime_admission(self):
        manifest = {
            "clips": [
                {
                    "clip_id": "WJ_INTRO_001",
                }
            ]
        }
        state = {
            "schema_version": 1,
            "program_id": "review",
            "decisions": {
                "WJ_INTRO_001": {
                    "status": "unreviewed",
                    "notes": "",
                }
            },
        }
        with tempfile.TemporaryDirectory() as temp_name:
            state_path = Path(temp_name) / "review-state.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            updated = _record_review_decision(
                state_path,
                manifest,
                {
                    "clip_id": "WJ_INTRO_001",
                    "status": "approved_choreography",
                    "notes": "Walk timing feels right.",
                },
            )

            decision = updated["decisions"]["WJ_INTRO_001"]
            self.assertEqual(decision["status"], "approved_choreography")
            self.assertEqual(decision["notes"], "Walk timing feels right.")
            self.assertNotIn("runtime_admitted", decision)
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8")),
                updated,
            )


if __name__ == "__main__":
    unittest.main()
