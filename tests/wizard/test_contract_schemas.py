import copy
import json
import unittest
from pathlib import Path

from wizard_avatar.artifact_hashing import canonical_json_v1
from wizard_avatar.schema_validation import (
    DRAFT_2020_12,
    SCHEMA_FILES,
    ContractValidationError,
    SchemaRegistry,
    load_and_validate_json,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "audiobook_contracts"
SCHEMA_DIR = ROOT / "wizard_avatar" / "definitions"


class ContractSchemaTests(unittest.TestCase):
    def setUp(self):
        self.registry = SchemaRegistry()

    def fixture(self, contract_name):
        filename = SCHEMA_FILES[contract_name].replace(".schema", "")
        return json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))

    def assert_code(self, code, contract_name, value, **kwargs):
        with self.assertRaises(ContractValidationError) as caught:
            self.registry.validate(contract_name, value, **kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_all_golden_fixtures_validate_and_round_trip_without_loss(self):
        for contract_name, schema_filename in SCHEMA_FILES.items():
            fixture_path = FIXTURE_DIR / schema_filename.replace(".schema", "")
            with self.subTest(contract=contract_name):
                original = json.loads(fixture_path.read_text(encoding="utf-8"))
                validated = load_and_validate_json(
                    fixture_path,
                    contract_name,
                    registry=self.registry,
                )
                reparsed = json.loads(canonical_json_v1(validated).decode("utf-8"))
                self.assertEqual(reparsed, original)

    def test_schemas_are_draft_2020_12_and_close_every_object_boundary(self):
        def inspect(node, path):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIs(
                        node.get("additionalProperties"),
                        False,
                        "open object schema at {}".format(path),
                    )
                for key, value in node.items():
                    inspect(value, "{}.{}".format(path, key))
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    inspect(value, "{}[{}]".format(path, index))

        for contract_name, filename in SCHEMA_FILES.items():
            with self.subTest(contract=contract_name):
                schema = json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))
                self.assertEqual(schema["$schema"], DRAFT_2020_12)
                self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
                inspect(schema, "$schema")

    def test_unknown_fields_and_versions_fail_at_root_and_nested_boundaries(self):
        fixture = self.fixture("MediaAssetV1")
        root_extra = copy.deepcopy(fixture)
        root_extra["url"] = "https://forbidden.invalid"
        self.assert_code("unknown_field", "MediaAssetV1", root_extra)

        nested_extra = copy.deepcopy(fixture)
        nested_extra["identity"]["path"] = "/private/media.mp3"
        self.assert_code("unknown_field", "MediaAssetV1", nested_extra)

        wrong_version = copy.deepcopy(fixture)
        wrong_version["schema_version"] = 2
        self.assert_code("schema_version_unsupported", "MediaAssetV1", wrong_version)

        bool_version = copy.deepcopy(fixture)
        bool_version["schema_version"] = True
        self.assert_code("invalid_type", "MediaAssetV1", bool_version)

    def test_float_duplicate_key_and_invalid_utf8_inputs_fail_closed(self):
        raw_float = (FIXTURE_DIR / "media_asset_v1.json").read_text(encoding="utf-8").replace(
            '"duration_ms": 10000',
            '"duration_ms": 10000.0',
        )
        with self.assertRaises(ContractValidationError) as caught:
            load_and_validate_json(raw_float, "MediaAssetV1")
        self.assertEqual(caught.exception.code, "non_integer_identity_value")

        duplicate = '{"schema_version":1,"schema_version":1}'
        with self.assertRaises(ContractValidationError) as caught:
            load_and_validate_json(duplicate, "MediaAssetV1")
        self.assertEqual(caught.exception.code, "duplicate_json_key")

        with self.assertRaises(ContractValidationError) as caught:
            load_and_validate_json(b"\xff", "MediaAssetV1")
        self.assertEqual(caught.exception.code, "invalid_json")

    def test_hash_id_and_media_identity_binding_are_strict(self):
        fixture = self.fixture("MediaAssetV1")
        invalid_hash = copy.deepcopy(fixture)
        invalid_hash["identity"]["source_sha256"] = "a" * 64
        self.assert_code("invalid_hash", "MediaAssetV1", invalid_hash)

        invalid_id = copy.deepcopy(fixture)
        invalid_id["storage_ref"] = "UPPER CASE"
        self.assert_code("invalid_id", "MediaAssetV1", invalid_id)

        mismatch = copy.deepcopy(fixture)
        mismatch["identity"]["source_sha256"] = "sha256:" + "f" * 64
        self.assert_code("hash_mismatch", "MediaAssetV1", mismatch)

    def test_transcript_references_and_alignment_ranges_are_semantic(self):
        transcript = self.fixture("TranscriptV1")
        transcript["chapters"][0]["block_ids"] = ["missing-block"]
        self.assert_code("dangling_reference", "TranscriptV1", transcript)

        alignment = self.fixture("AlignmentV1")
        alignment["units"][1]["start_ms"] = 400
        self.assert_code("exclusive_overlap", "AlignmentV1", alignment)

        alignment = self.fixture("AlignmentV1")
        alignment["units"][0]["end_ms"] = alignment["units"][0]["start_ms"]
        self.assert_code("range_invalid", "AlignmentV1", alignment)

    def test_score_cue_phases_and_exclusive_tracks_are_strict(self):
        score = self.fixture("PerformanceScoreV1")
        score["tracks"][0]["cues"][0]["phase_ranges"]["stroke"][0] = 1150
        self.assert_code("range_invalid", "PerformanceScoreV1", score)

        score = self.fixture("PerformanceScoreV1")
        second = copy.deepcopy(score["tracks"][0]["cues"][0])
        second["cue_id"] = "ch-001.beat-002.gesture-001"
        second["start_ms"] = 1500
        second["end_ms"] = 2500
        second.pop("phase_ranges")
        score["tracks"][0]["cues"].append(second)
        self.assert_code("exclusive_overlap", "PerformanceScoreV1", score)

    def test_music_positions_and_snapshot_position_are_bounded(self):
        music = self.fixture("MusicScoreV1")
        music["beats"][0]["sample"] = music["duration_samples"] + 1
        self.assert_code("time_out_of_bounds", "MusicScoreV1", music)

        snapshot = self.fixture("MediaSessionSnapshotV1")
        snapshot["playback"]["position_ms"] = snapshot["media"]["duration_ms"] + 1
        self.assert_code("position_out_of_bounds", "MediaSessionSnapshotV1", snapshot)

    def test_connector_contract_rejects_private_fields_and_unsorted_sets(self):
        snapshot = self.fixture("MediaSessionSnapshotV1")
        snapshot["media"]["canonical_url"] = "https://forbidden.invalid"
        self.assert_code("unknown_field", "MediaSessionSnapshotV1", snapshot)

        snapshot = self.fixture("MediaSessionSnapshotV1")
        snapshot["performance"]["disabled_channels"] = ["mouth", "body"]
        self.assert_code("invalid_enum", "MediaSessionSnapshotV1", snapshot)

        ack = self.fixture("MediaSessionAckV1")
        ack["capabilities"]["supported_rate_milli"] = [1000, 500]
        self.assert_code("invalid_enum", "MediaSessionAckV1", ack)

    def test_expected_bindings_reject_stale_package_and_score_digests(self):
        compiled_score = self.fixture("CompiledPerformanceScoreV1")
        self.registry.validate(
            "CompiledPerformanceScoreV1",
            compiled_score,
            expected_bindings={
                "character.package_digest": compiled_score["character"]["package_digest"]
            },
        )
        self.assert_code(
            "stale_binding",
            "CompiledPerformanceScoreV1",
            compiled_score,
            expected_bindings={"character.package_digest": "sha256:" + "f" * 64},
        )

        snapshot = self.fixture("MediaSessionSnapshotV1")
        self.assert_code(
            "stale_binding",
            "MediaSessionSnapshotV1",
            snapshot,
            expected_bindings={"performance.score_sha256": "sha256:" + "e" * 64},
        )

    def test_duplicate_ids_and_ack_error_contract_fail(self):
        edits = self.fixture("ScoreEditsV1")
        edits["operations"].append(copy.deepcopy(edits["operations"][0]))
        self.assert_code("duplicate_id", "ScoreEditsV1", edits)

        ack = self.fixture("MediaSessionAckV1")
        ack.pop("error")
        self.assert_code("missing_field", "MediaSessionAckV1", ack)

    def test_add_cue_edit_accepts_a_complete_strict_cue(self):
        edits = self.fixture("ScoreEditsV1")
        cue = copy.deepcopy(self.fixture("PerformanceScoreV1")["tracks"][0]["cues"][0])
        cue["execution"] = {
            "trajectory": {
                "source_position_milli": [100, 200],
                "destination_position_milli": [500, 600],
                "easing_id": "smoothstep_v1",
            },
            "facing": "south",
        }
        edits["operations"] = [
            {
                "operation_id": "op-add-0001",
                "op": "add_cue",
                "cue_id": cue["cue_id"],
                "field": None,
                "old_value_sha256": None,
                "value": cue,
                "reason_code": "director_choice",
                "locked": False,
            }
        ]
        self.registry.validate("ScoreEditsV1", edits)

        edits["operations"][0]["value"]["runtime_clip_id"] = "forbidden"
        self.assert_code("unknown_field", "ScoreEditsV1", edits)


if __name__ == "__main__":
    unittest.main()
