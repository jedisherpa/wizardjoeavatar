import copy
import hashlib
import json
import unittest
from dataclasses import FrozenInstanceError

from wizard_avatar.models import MOUTH_SHAPES
from wizard_avatar.voice_alignment import (
    VoiceAlignmentError,
    VoiceAlignmentV1,
    evaluate_voice_alignment,
)


APPROVED_TEXT = "Hello quiet world."


def sha256_ref(value):
    return "sha256:" + hashlib.sha256(value).hexdigest()


def alignment_mapping(with_phonemes=True):
    media_sha256 = sha256_ref(b"authoritative speech bytes")
    value = {
        "schema_version": 1,
        "alignment_id": "alignment:speech-0042-v1",
        "approved_content_sha256": sha256_ref(APPROVED_TEXT.encode("utf-8")),
        "approved_text_length": len(APPROVED_TEXT),
        "media_id": "media:" + media_sha256,
        "media_sha256": media_sha256,
        "speech_id": "speech:turn-0042",
        "voice_id": "voice-wizard-joe-v1",
        "duration_ms": 1400,
        "word_spans": [
            {"start_ms": 100, "end_ms": 400, "start_char": 0, "end_char": 5},
            {"start_ms": 600, "end_ms": 900, "start_char": 6, "end_char": 11},
            {"start_ms": 950, "end_ms": 1250, "start_char": 12, "end_char": 18},
        ],
        "character_spans": [],
        "phoneme_spans": [
            {"start_ms": 100, "end_ms": 180, "phoneme_class": "mbp"},
            {"start_ms": 180, "end_ms": 300, "phoneme_class": "e"},
            {"start_ms": 300, "end_ms": 400, "phoneme_class": "o"},
            {"start_ms": 600, "end_ms": 720, "phoneme_class": "rest"},
            {"start_ms": 720, "end_ms": 900, "phoneme_class": "a"},
            {"start_ms": 950, "end_ms": 1250, "phoneme_class": "kg"},
        ],
    }
    if not with_phonemes:
        value["phoneme_spans"] = []
    return value


class VoiceAlignmentTests(unittest.TestCase):
    def assert_code(self, code, value):
        with self.assertRaises(VoiceAlignmentError) as caught:
            VoiceAlignmentV1.from_mapping(value)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_v1_is_frozen_content_free_and_identity_bound(self):
        value = alignment_mapping()
        alignment = VoiceAlignmentV1.from_mapping(value)

        self.assertEqual(alignment.to_dict(), value)
        self.assertEqual(alignment.approved_content_sha256, sha256_ref(APPROVED_TEXT.encode("utf-8")))
        self.assertEqual(alignment.alignment_sha256, sha256_ref(alignment.canonical_json()))
        self.assertNotIn(APPROVED_TEXT, alignment.canonical_json().decode("utf-8"))
        with self.assertRaises(FrozenInstanceError):
            alignment.duration_ms = 10
        with self.assertRaises(TypeError):
            alignment.word_spans[0] = alignment.word_spans[1]

        mismatch = alignment_mapping()
        mismatch["media_sha256"] = "sha256:" + "f" * 64
        self.assert_code("media_hash_mismatch", mismatch)

    def test_rejects_floats_bools_unknowns_and_duplicate_json_keys(self):
        value = alignment_mapping()
        value["duration_ms"] = 1400.0
        self.assert_code("invalid_type", value)

        value = alignment_mapping()
        value["word_spans"][0]["start_ms"] = False
        self.assert_code("invalid_type", value)

        value = alignment_mapping()
        value["raw_text"] = "private-canary"
        caught = self.assert_code("unknown_field", value)
        self.assertNotIn("private-canary", str(caught))

        payload = b'{"schema_version":1,"schema_version":1}'
        with self.assertRaises(VoiceAlignmentError) as caught:
            VoiceAlignmentV1.from_json(payload)
        self.assertEqual(caught.exception.code, "duplicate_json_key")

    def test_rejects_overlap_out_of_range_unknown_phonemes_and_ambiguous_reveal(self):
        value = alignment_mapping()
        value["word_spans"][1]["start_ms"] = 399
        self.assert_code("timing_overlap", value)

        value = alignment_mapping()
        value["phoneme_spans"][1]["start_ms"] = 179
        self.assert_code("timing_overlap", value)

        value = alignment_mapping()
        value["word_spans"][-1]["end_ms"] = 1401
        self.assert_code("timing_out_of_range", value)

        value = alignment_mapping()
        value["word_spans"][-1]["end_char"] = len(APPROVED_TEXT) + 1
        self.assert_code("text_out_of_range", value)

        value = alignment_mapping()
        value["word_spans"][1]["start_char"] = 4
        self.assert_code("text_overlap", value)

        value = alignment_mapping()
        value["phoneme_spans"][0]["phoneme_class"] = "unknown"
        self.assert_code("phoneme_unknown", value)

        value = alignment_mapping()
        value["character_spans"] = [
            {"start_ms": 0, "end_ms": 10, "start_char": 0, "end_char": 1}
        ]
        self.assert_code("reveal_track_ambiguous", value)

    def test_exact_boundaries_reveal_at_start_and_close_in_gaps(self):
        alignment = VoiceAlignmentV1.from_mapping(alignment_mapping())
        expected = {
            0: (0, "closed", False, False),
            99: (0, "closed", False, False),
            100: (5, "closed", True, False),
            179: (5, "closed", True, False),
            180: (5, "smile", True, False),
            399: (5, "rounded", True, False),
            400: (5, "closed", False, False),
            599: (5, "closed", False, False),
            600: (11, "closed", False, False),
            720: (11, "open_wide", True, False),
            900: (11, "closed", False, False),
            950: (18, "open_medium", True, False),
            1250: (18, "closed", False, False),
        }
        for media_time_ms, result in expected.items():
            with self.subTest(media_time_ms=media_time_ms):
                state = alignment.evaluate(media_time_ms)
                self.assertEqual(
                    (state.reveal_boundary, state.mouth_shape, state.speaking, state.terminal),
                    result,
                )
                self.assertIn(state.mouth_shape, MOUTH_SHAPES)

    def test_character_spans_are_an_alternative_progressive_reveal_track(self):
        value = alignment_mapping(with_phonemes=False)
        value["approved_text_length"] = 3
        value["approved_content_sha256"] = sha256_ref(b"abc")
        value["word_spans"] = []
        value["character_spans"] = [
            {"start_ms": 100, "end_ms": 200, "start_char": 0, "end_char": 1},
            {"start_ms": 200, "end_ms": 300, "start_char": 1, "end_char": 2},
            {"start_ms": 300, "end_ms": 400, "start_char": 2, "end_char": 3},
        ]
        alignment = VoiceAlignmentV1.from_mapping(value)
        self.assertEqual([alignment.evaluate(t).reveal_boundary for t in (99, 100, 200, 300)], [0, 1, 2, 3])

    def test_fallback_is_absolute_deterministic_and_silent_outside_text_spans(self):
        value = alignment_mapping(with_phonemes=False)
        first = VoiceAlignmentV1.from_mapping(value)
        second = VoiceAlignmentV1.from_mapping(copy.deepcopy(value))

        for media_time_ms in range(0, first.duration_ms + 250, 17):
            self.assertEqual(first.evaluate(media_time_ms), second.evaluate(media_time_ms))
        for media_time_ms in (0, 99, 400, 500, 599, 900, 925, 1250, 1399):
            state = first.evaluate(media_time_ms)
            self.assertEqual(state.mouth_shape, "closed")
            self.assertFalse(state.speaking)
            self.assertEqual(state.mouth_policy, "silence")
        for media_time_ms in (100, 250, 600, 800, 950, 1200):
            state = first.evaluate(media_time_ms)
            self.assertTrue(state.speaking)
            self.assertNotEqual(state.mouth_shape, "closed")
            self.assertEqual(state.mouth_policy, "absolute_duration_fallback_v1")

    def test_cold_seek_and_linear_evaluation_match_exactly(self):
        value = alignment_mapping(with_phonemes=False)
        alignment = VoiceAlignmentV1.from_mapping(value)
        times = list(range(0, 1601, 13)) + [100, 180, 400, 600, 900, 1400, 5000]
        linear = {time: alignment.evaluate(time).to_dict() for time in sorted(times)}

        for time in reversed(times):
            cold = VoiceAlignmentV1.from_mapping(copy.deepcopy(value))
            self.assertEqual(evaluate_voice_alignment(cold, time).to_dict(), linear[time])

    def test_end_and_expiry_reveal_all_text_and_hold_closed(self):
        alignment = VoiceAlignmentV1.from_mapping(alignment_mapping())
        for media_time_ms in (1400, 1401, 10_000_000):
            state = alignment.evaluate(media_time_ms)
            self.assertEqual(state.media_time_ms, alignment.duration_ms)
            self.assertEqual(state.reveal_boundary, len(APPROVED_TEXT))
            self.assertEqual(state.mouth_shape, "closed")
            self.assertFalse(state.speaking)
            self.assertTrue(state.terminal)
            self.assertEqual(state.mouth_policy, "ended")

    def test_diagnostics_expose_hashes_counts_and_timing_without_text(self):
        alignment = VoiceAlignmentV1.from_mapping(alignment_mapping())
        diagnostics = alignment.diagnostics().to_dict()
        encoded = json.dumps(diagnostics, sort_keys=True)

        self.assertEqual(diagnostics["alignment_sha256"], alignment.alignment_sha256)
        self.assertEqual(diagnostics["approved_content_sha256"], alignment.approved_content_sha256)
        self.assertRegex(diagnostics["speech_identity_sha256"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(diagnostics["word_span_count"], 3)
        self.assertEqual(diagnostics["character_span_count"], 0)
        self.assertEqual(diagnostics["phoneme_span_count"], 6)
        self.assertEqual(diagnostics["first_timed_ms"], 100)
        self.assertEqual(diagnostics["last_timed_ms"], 1250)
        self.assertEqual(diagnostics["duration_ms"], 1400)
        self.assertNotIn(APPROVED_TEXT, encoded)
        self.assertNotIn("Hello", encoded)
        self.assertNotIn("quiet", encoded)
        self.assertNotIn(alignment.speech_id, encoded)
        self.assertNotIn(alignment.voice_id, encoded)


if __name__ == "__main__":
    unittest.main()
