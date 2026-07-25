import unittest

from tools.run_character_observer import _observer_health, _observer_html


class CharacterObserverTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
