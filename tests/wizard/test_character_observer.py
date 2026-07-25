import unittest

from tools.run_character_observer import _observer_html


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


if __name__ == "__main__":
    unittest.main()
