import unittest

from wizard_avatar.mouth import fallback_speech_shape


class MouthFallbackTests(unittest.TestCase):
    def test_utterance_timing_is_relative_to_its_start(self):
        text = "The stars prefer a tidy spellbook."
        first = [fallback_speech_shape(offset, 2.4, text) for offset in (0.0, 0.31, 0.82, 1.4)]
        second = [
            fallback_speech_shape(now - 87.0, 89.4 - 87.0, text)
            for now in (87.0, 87.31, 87.82, 88.4)
        ]
        self.assertEqual(first, second)

    def test_punctuation_creates_a_closed_rest(self):
        text = "Hello, world."
        self.assertNotEqual(fallback_speech_shape(0.30, 2.0, text), "closed")
        self.assertEqual(fallback_speech_shape(0.95, 2.0, text), "closed")

    def test_utterance_settles_closed_at_the_end(self):
        self.assertEqual(fallback_speech_shape(1.96, 2.0, "One final thought."), "closed")

    def test_speech_resumes_after_an_internal_sentence_stop(self):
        text = "First thought. Second thought."
        later_shapes = {
            fallback_speech_shape(offset, 2.4, text)
            for offset in (1.25, 1.40, 1.55, 1.70)
        }
        self.assertNotEqual(later_shapes, {"closed"})


if __name__ == "__main__":
    unittest.main()
