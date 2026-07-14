import hashlib
import unittest
from pathlib import Path

from tools.performance_authoring.transcript import (
    import_transcript as import_transcript_file,
    optional_speech_capabilities,
)
from wizard_avatar.transcript_ingest import (
    TranscriptIngestError,
    ingest_transcript,
    normalize_spoken_text,
    revise_transcript,
)


FIXTURES = Path(__file__).parents[1] / "fixtures" / "audiobook_performance"
MEDIA_ID = "media:sha256:" + hashlib.sha256(b"synthetic-audio").hexdigest()


class TranscriptIngestTests(unittest.TestCase):
    def test_webvtt_ingest_is_repeatable_and_separates_caption_timing(self):
        source = (FIXTURES / "synthetic_story.vtt").read_bytes()
        first = ingest_transcript(
            source,
            media_id=MEDIA_ID,
            transcript_format="webvtt",
        )
        second = ingest_transcript(
            source,
            media_id=MEDIA_ID,
            transcript_format="webvtt",
        )

        self.assertEqual(first, second)
        self.assertEqual(first.transcript.to_mapping(), second.transcript.to_mapping())
        self.assertEqual([cue.start_ms for cue in first.caption_cues], [0, 2000, 4000])
        self.assertEqual([cue.end_ms for cue in first.caption_cues], [2000, 4000, 6000])
        self.assertNotIn("<i>", first.transcript.blocks[0].display_text)
        self.assertNotIn("<v", first.transcript.blocks[1].display_text)
        self.assertNotIn("start_ms", first.transcript.to_mapping()["blocks"][0])

    def test_plain_text_and_srt_have_stable_spoken_normalization(self):
        plain = import_transcript_file(
            FIXTURES / "synthetic_story.txt",
            media_id=MEDIA_ID,
        ).transcript
        srt = import_transcript_file(
            FIXTURES / "synthetic_story.srt",
            media_id=MEDIA_ID,
        ).transcript

        self.assertEqual(len(plain.blocks), 3)
        self.assertEqual(len(srt.blocks), 3)
        self.assertEqual(
            normalize_spoken_text('  "Is the blue dial awake?"  '),
            "is the blue dial awake",
        )
        self.assertEqual(plain.spoken_normalized_sha256, srt.spoken_normalized_sha256)
        self.assertNotEqual(plain.source_sha256, srt.source_sha256)

    def test_revision_preserves_ids_and_invalidates_only_changed_forms(self):
        parent = import_transcript_file(
            FIXTURES / "synthetic_story.txt",
            media_id=MEDIA_ID,
        ).transcript
        revised = revise_transcript(
            parent,
            {"b-0002": '"Is the blue dial ready?" asked Mira.'},
        )

        self.assertEqual(revised.revision, 2)
        self.assertEqual(revised.parent_transcript_id, parent.transcript_id)
        self.assertEqual(
            [block.block_id for block in revised.blocks],
            [block.block_id for block in parent.blocks],
        )
        self.assertNotEqual(revised.transcript_id, parent.transcript_id)
        self.assertNotEqual(revised.spoken_normalized_sha256, parent.spoken_normalized_sha256)
        self.assertEqual(revised.blocks[0], parent.blocks[0])

    def test_invalid_caption_order_and_non_utf8_fail_with_stable_codes(self):
        invalid_order = """WEBVTT

00:00:02.000 --> 00:00:03.000
Later

00:00:01.000 --> 00:00:02.000
Earlier
"""
        with self.assertRaises(TranscriptIngestError) as order_error:
            ingest_transcript(
                invalid_order,
                media_id=MEDIA_ID,
                transcript_format="webvtt",
            )
        self.assertEqual(order_error.exception.code, "caption_order_invalid")

        with self.assertRaises(TranscriptIngestError) as encoding_error:
            ingest_transcript(
                b"\xff\xfe",
                media_id=MEDIA_ID,
                transcript_format="text",
            )
        self.assertEqual(encoding_error.exception.code, "transcript_encoding_invalid")

    def test_provider_tts_ssml_is_removed_from_display_but_bound_to_source_hash(self):
        source = b'<speak>Hello <prosody rate="slow">local listener</prosody>.<break time="1s"/></speak>'
        imported = ingest_transcript(
            source,
            media_id=MEDIA_ID,
            transcript_format="text",
            source_kind="provider_tts",
        ).transcript

        self.assertEqual(imported.blocks[0].display_text, "Hello local listener.")
        self.assertNotIn("<", imported.blocks[0].display_text)
        self.assertEqual(
            imported.source_sha256,
            "sha256:" + hashlib.sha256(source).hexdigest(),
        )

    def test_optional_speech_tools_are_never_reported_ready_without_models(self):
        capabilities = optional_speech_capabilities()

        self.assertEqual(
            {capability.capability for capability in capabilities},
            {"local_asr", "forced_alignment"},
        )
        self.assertTrue(all(not capability.available for capability in capabilities))
        self.assertTrue(all(capability.reason_code for capability in capabilities))


if __name__ == "__main__":
    unittest.main()
