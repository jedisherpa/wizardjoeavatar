import copy
import json
import unittest
from pathlib import Path

from tools.validate_cartoon_animation_program import validate_evidence_record


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "wizard_avatar/definitions/cartoon_animation_evidence.schema.json"
CHECKPOINT = "08d8f3aaa181d97ef3d2a29cb5a8362d81a05f12"


class CartoonAnimationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "schema_version": 1,
            "program_id": "wizardjoe-cartoon-animation-2026-07-12",
            "gate_id": "Q0",
            "work_item_id": "CAP-520",
            "result": "passed",
            "production": {"architecture": "asciline_python", "port": 8765},
            "planning_checkpoint": {"commit": CHECKPOINT, "pushed": True},
            "tested_commit": "a" * 40,
            "generated_at": "2026-07-13T08:15:30Z",
            "commands": [
                {
                    "command": "python3 -m unittest tests.wizard.test_cartoon_animation_program",
                    "exit_code": 0,
                    "duration_ms": 125.5,
                    "result": "passed",
                    "output_summary": "7 tests passed",
                    "output_sha256": "b" * 64,
                }
            ],
            "artifacts": [
                {
                    "path": "evidence/cartoon-animation-program/checkpoints/Q0.json",
                    "media_type": "application/json",
                    "sha256": "c" * 64,
                    "bytes": 2048,
                    "storage": "git",
                    "retention_days": 90,
                }
            ],
            "changed_paths": [
                "tools/validate_cartoon_animation_program.py",
                "wizard_avatar/definitions/cartoon_animation_evidence.schema.json",
            ],
            "metrics": {"error_count": 0, "duration_ms": 125.5},
            "risks": [],
            "review": {
                "role": "PLAN",
                "reviewer_id": "darwin",
                "decision": "accepted",
                "notes": "Program gate passes.",
            },
        }

    def _codes(self, record):
        return {error["code"] for error in validate_evidence_record(record)}

    def test_schema_is_strict_draft_2020_12_and_matches_runtime_contract(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertEqual(
            schema["properties"]["production"]["properties"]["architecture"]["const"],
            "asciline_python",
        )
        self.assertEqual(
            schema["properties"]["production"]["properties"]["port"]["const"],
            8765,
        )
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "program_id",
                "gate_id",
                "work_item_id",
                "result",
                "production",
                "planning_checkpoint",
                "tested_commit",
                "generated_at",
                "commands",
                "artifacts",
                "changed_paths",
                "risks",
            },
        )

    def test_valid_compact_evidence_record_passes(self):
        self.assertEqual(validate_evidence_record(self.record), [])

    def test_missing_required_fields_and_wrong_runtime_fail(self):
        record = copy.deepcopy(self.record)
        del record["commands"]
        record["production"] = {"architecture": "other", "port": 8787}
        codes = self._codes(record)
        self.assertIn("evidence.required", codes)
        self.assertIn("evidence.architecture", codes)
        self.assertIn("evidence.port", codes)

    def test_passed_record_cannot_contain_failed_command(self):
        record = copy.deepcopy(self.record)
        record["commands"][0]["exit_code"] = 1
        record["commands"][0]["result"] = "failed"
        codes = self._codes(record)
        self.assertIn("evidence.pass_with_failure", codes)

    def test_command_exit_code_and_result_must_agree(self):
        record = copy.deepcopy(self.record)
        record["commands"][0]["result"] = "failed"
        self.assertIn("evidence.command_exit_mismatch", self._codes(record))

    def test_git_evidence_is_compact_and_raw_files_use_artifact_storage(self):
        record = copy.deepcopy(self.record)
        artifact = record["artifacts"][0]
        artifact["path"] = "evidence/cartoon-animation-program/raw/session.ndjson"
        artifact["bytes"] = 5 * 1024 * 1024 + 1
        codes = self._codes(record)
        self.assertIn("evidence.git_artifact_size", codes)
        self.assertIn("evidence.raw_in_git", codes)

    def test_evidence_rejects_rust_changed_paths_and_path_traversal(self):
        record = copy.deepcopy(self.record)
        record["changed_paths"] = ["rust/src/main.rs", "../outside.json"]
        codes = self._codes(record)
        self.assertIn("evidence.rust_path", codes)
        self.assertIn("evidence.changed_path", codes)

    def test_checkpoint_must_be_full_and_pushed(self):
        record = copy.deepcopy(self.record)
        record["planning_checkpoint"] = {"commit": "08d8f3a", "pushed": False}
        codes = self._codes(record)
        self.assertIn("evidence.checkpoint_commit", codes)
        self.assertIn("evidence.checkpoint_pushed", codes)


if __name__ == "__main__":
    unittest.main()
