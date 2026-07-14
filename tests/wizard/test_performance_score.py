import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wizard_avatar.performance_score import (
    CompiledScoreLoader,
    CompiledScoreRepository,
    ScoreValidationError,
    TrackIntervalIndex,
)


def digest(character):
    return "sha256:" + character * 64


def score_document(revision=1):
    return {
        "schema_version": 1,
        "compiled_score_id": "compiled:book",
        "revision": revision,
        "performance_score_sha256": digest("a"),
        "character": {
            "character_id": "wizard-joe",
            "package_version": "2.0.0",
            "package_digest": digest("b"),
            "pose_library_digest": digest("c"),
            "graph_digest": digest("d"),
        },
        "mapping_policy_sha256": digest("e"),
        "runtime_api_version": 2,
        "media": {
            "media_id": "media:book",
            "media_sha256": digest("f"),
            "duration_ms": 4000,
        },
        "tracks": [
            {
                "track_id": "body-base",
                "kind": "body_base",
                "exclusive": True,
                "max_active": 1,
                "gap_policy": "characterful_neutral",
                "cues": [
                    {
                        "cue_id": "body.neutral",
                        "start_ms": 0,
                        "end_ms": 1000,
                        "intent": "characterful_neutral",
                        "priority": 10,
                        "owned_channels": ["body"],
                        "phase_ranges": {},
                        "mapping_id": "neutral",
                    },
                    {
                        "cue_id": "body.explain",
                        "start_ms": 1000,
                        "end_ms": 3000,
                        "intent": "explain_light",
                        "priority": 20,
                        "owned_channels": ["body"],
                        "phase_ranges": {
                            "anticipation": [1000, 1200],
                            "stroke": [1200, 1500],
                            "hold": [1500, 2400],
                            "release": [2400, 2700],
                            "settle": [2700, 3000],
                        },
                        "mapping_id": "explain-open-hand",
                        "clip_id": "explain-clip",
                    },
                ],
            },
            {
                "track_id": "face",
                "kind": "face",
                "exclusive": False,
                "max_active": 2,
                "gap_policy": "neutral",
                "cues": [
                    {
                        "cue_id": "face.warm",
                        "start_ms": 900,
                        "end_ms": 2000,
                        "intent": "warm",
                        "priority": 10,
                        "owned_channels": ["face"],
                        "phase_ranges": {},
                    },
                    {
                        "cue_id": "face.emphasis",
                        "start_ms": 1200,
                        "end_ms": 1400,
                        "intent": "emphasis",
                        "priority": 30,
                        "owned_channels": ["face"],
                        "phase_ranges": {},
                    },
                ],
            },
        ],
        "checkpoints": [],
        "fallback_records": [],
        "validation": {"decision": "accepted", "report_sha256": digest("9")},
    }


class PerformanceScoreTests(unittest.TestCase):
    def setUp(self):
        self.loader = CompiledScoreLoader(contract_validator=lambda _name, _value: None)

    def test_loader_freezes_document_and_uses_half_open_boundaries(self):
        score = self.loader.from_mapping(score_document())
        body = score.track("body-base").index
        self.assertEqual(body.query(999)[0].cue_id, "body.neutral")
        self.assertEqual(body.query(1000)[0].cue_id, "body.explain")
        self.assertEqual(body.query(3000), ())
        with self.assertRaises(TypeError):
            score.document["runtime_api_version"] = 99
        with self.assertRaises(TypeError):
            score.tracks[0].index.cues[0].data["intent"] = "changed"

    def test_default_loader_uses_the_contract_foundation(self):
        fixture = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "audiobook_contracts"
            / "compiled_performance_score_v1.json"
        )
        score = CompiledScoreLoader().load(fixture)
        self.assertEqual(score.compiled_score_id, "compiled:fixture-001")
        invalid = score_document()
        with self.assertRaises(ScoreValidationError) as error:
            CompiledScoreLoader().from_mapping(invalid)
        self.assertEqual(error.exception.code, "unknown_field")

    def test_overlay_index_returns_deterministic_precedence(self):
        score = self.loader.from_mapping(score_document())
        index = score.track("face").index
        self.assertIsInstance(index, TrackIntervalIndex)
        self.assertEqual([cue.cue_id for cue in index.query(1250)], ["face.emphasis", "face.warm"])
        self.assertEqual([cue.cue_id for cue in index.query(1400)], ["face.warm"])

    def test_duplicate_keys_floats_overlap_and_hash_mismatch_fail_closed(self):
        with self.assertRaisesRegex(ScoreValidationError, "duplicate") as duplicate:
            self.loader.loads('{"schema_version":1,"schema_version":1}')
        self.assertEqual(duplicate.exception.code, "duplicate_json_key")

        floating = score_document()
        floating["tracks"][0]["cues"][0]["amplitude"] = 0.5
        with self.assertRaises(ScoreValidationError) as float_error:
            self.loader.from_mapping(floating)
        self.assertEqual(float_error.exception.code, "non_integer_identity_value")

        overlap = score_document()
        overlap["tracks"][0]["cues"][1]["start_ms"] = 999
        overlap["tracks"][0]["cues"][1]["phase_ranges"] = {}
        with self.assertRaises(ScoreValidationError) as overlap_error:
            self.loader.from_mapping(overlap)
        self.assertEqual(overlap_error.exception.code, "exclusive_overlap")

        with self.assertRaises(ScoreValidationError) as hash_error:
            self.loader.from_mapping(score_document(), expected_sha256=digest("0"))
        self.assertEqual(hash_error.exception.code, "hash_mismatch")

    def test_atomic_publication_preserves_current_pointer_on_failure(self):
        first = self.loader.from_mapping(score_document(1))
        second = self.loader.from_mapping(score_document(2))
        with tempfile.TemporaryDirectory() as temporary:
            repository = CompiledScoreRepository(temporary, self.loader)
            first_publication = repository.publish(first)
            self.assertEqual(repository.load_current(digest("f")).revision, 1)

            with mock.patch.object(repository, "_replace_pointer", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    repository.publish(second)

            self.assertEqual(repository.load_current(digest("f")).revision, 1)
            second_generation = (
                Path(temporary)
                / "media"
                / ("f" * 64)
                / "scores"
                / "compiled:book"
                / "2"
                / "score.json"
            )
            self.assertTrue(second_generation.is_file())
            repository.select_revision(first_publication)
            self.assertEqual(repository.load_current(digest("f")).artifact_sha256, first.artifact_sha256)

    def test_publication_is_immutable_and_rejects_stale_revision(self):
        first = self.loader.from_mapping(score_document(1))
        second = self.loader.from_mapping(score_document(2))
        with tempfile.TemporaryDirectory() as temporary:
            repository = CompiledScoreRepository(temporary, self.loader)
            repository.publish(second)
            with self.assertRaises(ScoreValidationError) as stale:
                repository.publish(first)
            self.assertEqual(stale.exception.code, "job_stale")

            changed = score_document(2)
            changed["tracks"][0]["cues"][0]["mapping_id"] = "different"
            with self.assertRaises(ScoreValidationError) as conflict:
                repository.publish(self.loader.from_mapping(changed))
            self.assertEqual(conflict.exception.code, "immutable_revision_conflict")

    def test_corrupt_pointer_is_not_silently_ignored(self):
        score = self.loader.from_mapping(score_document())
        with tempfile.TemporaryDirectory() as temporary:
            repository = CompiledScoreRepository(temporary, self.loader)
            repository.publish(score)
            pointer = Path(temporary) / "media" / ("f" * 64) / "current.json"
            pointer.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            with self.assertRaises(ScoreValidationError) as corrupt:
                repository.load_current(digest("f"))
            self.assertEqual(corrupt.exception.code, "cache_corrupt")


if __name__ == "__main__":
    unittest.main()
