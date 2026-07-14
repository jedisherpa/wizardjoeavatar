import hashlib
import json
import unittest
from pathlib import Path

from tools.performance_authoring.narrative import (
    build_narrative_baseline,
    structured_planner_capability,
)
from wizard_avatar.performance_compiler import (
    PerformanceCompileError,
    build_speech_fallback_profile,
    canonical_artifact_bytes,
    compile_baseline_performance,
    evaluate_speech_fallback,
    select_performance_source,
    timing_spans_from_captions,
)
from wizard_avatar.schema_validation import SchemaRegistry
from wizard_avatar.transcript_ingest import ingest_transcript


FIXTURES = Path(__file__).parents[1] / "fixtures" / "audiobook_performance"
MEDIA_SHA256 = "sha256:" + hashlib.sha256(b"synthetic-audio").hexdigest()
MEDIA_ID = "media:sha256:" + MEDIA_SHA256.split(":", 1)[1]
ALIGNMENT_SHA256 = "sha256:" + hashlib.sha256(b"synthetic-alignment").hexdigest()


class PerformanceCompilerTests(unittest.TestCase):
    def setUp(self):
        imported = ingest_transcript(
            (FIXTURES / "synthetic_story.vtt").read_bytes(),
            media_id=MEDIA_ID,
            transcript_format="webvtt",
        )
        self.transcript = imported.transcript
        self.spans = timing_spans_from_captions(imported.caption_cues)

    def test_narrative_and_performance_artifacts_are_repeatable_and_content_free(self):
        first = compile_baseline_performance(
            self.transcript,
            duration_ms=6000,
            alignment_id="alignment:synthetic-v1",
            media_sha256=MEDIA_SHA256,
            timing_spans=self.spans,
        )
        second = compile_baseline_performance(
            self.transcript,
            duration_ms=6000,
            alignment_id="alignment:synthetic-v1",
            media_sha256=MEDIA_SHA256,
            timing_spans=self.spans,
        )

        self.assertEqual(
            canonical_artifact_bytes(first.narrative_score),
            canonical_artifact_bytes(second.narrative_score),
        )
        self.assertEqual(
            canonical_artifact_bytes(first.performance_score),
            canonical_artifact_bytes(second.performance_score),
        )
        serialized = canonical_artifact_bytes(first.narrative_score).decode("utf-8")
        for canary in ("observatory", "Mira", "blue dial", "chimed"):
            self.assertNotIn(canary, serialized)
        self.assertNotIn("display_text", serialized)
        self.assertNotIn("spoken_normalized_text", serialized)
        body_track = first.performance_score["tracks"][1]
        self.assertEqual(body_track["cues"][0]["intent"], "characterful_neutral")
        self.assertEqual(body_track["cues"][0]["start_ms"], 0)
        self.assertEqual(body_track["cues"][0]["end_ms"], 6000)
        registry = SchemaRegistry()
        registry.validate("TranscriptV1", self.transcript.to_mapping())
        registry.validate("NarrativeScoreV1", first.narrative_score)
        registry.validate("PerformanceScoreV1", first.performance_score)

    def test_local_narrative_authoring_has_stable_cache_and_explicit_planner_state(self):
        first = build_narrative_baseline(
            self.transcript,
            duration_ms=6000,
            alignment_id="alignment:synthetic-v1",
            alignment_sha256=ALIGNMENT_SHA256,
            media_sha256=MEDIA_SHA256,
            timing_spans=self.spans,
        )
        second = build_narrative_baseline(
            self.transcript,
            duration_ms=6000,
            alignment_id="alignment:synthetic-v1",
            alignment_sha256=ALIGNMENT_SHA256,
            media_sha256=MEDIA_SHA256,
            timing_spans=self.spans,
        )

        self.assertEqual(first.cache_key.digest, second.cache_key.digest)
        self.assertTrue(first.planner.available)
        optional = structured_planner_capability()
        self.assertFalse(optional.available)
        self.assertEqual(optional.reason_code, "optional_planner_not_configured")

    def test_duration_only_speech_fallback_needs_no_transcript_and_is_time_pure(self):
        profile = build_speech_fallback_profile(
            media_id=MEDIA_ID,
            media_sha256=MEDIA_SHA256,
            duration_ms=5000,
        )
        first = evaluate_speech_fallback(profile, 2375)
        cold = evaluate_speech_fallback(profile, 2375)
        ended = evaluate_speech_fallback(profile, 5000)

        self.assertEqual(first, cold)
        self.assertEqual(first.body_intent, "characterful_neutral")
        self.assertEqual(first.degraded_reason, "duration_only_speech")
        self.assertTrue(first.speaking)
        self.assertFalse(ended.speaking)
        self.assertEqual(ended.mouth_shape, "rest")
        serialized = json.dumps(profile.to_mapping(), sort_keys=True)
        self.assertNotIn("transcript", serialized)

    def test_accepted_aligned_score_wins_and_mismatch_never_silently_falls_back(self):
        compilation = compile_baseline_performance(
            self.transcript,
            duration_ms=6000,
            alignment_id="alignment:synthetic-v1",
            media_sha256=MEDIA_SHA256,
            timing_spans=self.spans,
        )
        aligned = select_performance_source(
            compilation.performance_score,
            media_id=MEDIA_ID,
            media_sha256=MEDIA_SHA256,
            duration_ms=6000,
        )
        fallback = select_performance_source(
            None,
            media_id=MEDIA_ID,
            media_sha256=MEDIA_SHA256,
            duration_ms=6000,
        )

        self.assertEqual(aligned.source, "aligned_score")
        self.assertIsNone(aligned.degraded_reason)
        self.assertEqual(fallback.source, "speech_fallback")
        self.assertEqual(fallback.degraded_reason, "duration_only_speech")

        mismatched = dict(compilation.performance_score)
        mismatched["media"] = dict(mismatched["media"], duration_ms=5999)
        with self.assertRaises(PerformanceCompileError) as caught:
            select_performance_source(
                mismatched,
                media_id=MEDIA_ID,
                media_sha256=MEDIA_SHA256,
                duration_ms=6000,
            )
        self.assertEqual(caught.exception.code, "score_mismatch")


if __name__ == "__main__":
    unittest.main()
