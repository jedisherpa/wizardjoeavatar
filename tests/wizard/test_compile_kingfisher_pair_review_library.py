import json
import tempfile
import unittest
from collections import OrderedDict
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import tools.compile_kingfisher_pair_review_library as compiler
from tools.compile_kingfisher_pair_review_library import (
    compile_pair_review_library,
)
from tools.verify_kingfisher_pair_review import (
    blocked_pair_review_report,
    verify_pair_review,
)
from wizard_avatar.hd_pose_artifact import (
    HDPoseLibrary,
    sha256_path,
    write_pose_artifact,
)


class CompileKingfisherPairReviewLibraryTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path]:
        base_root = root / "base"
        pair_root = root / "pairs"
        base_root.mkdir()
        pair_root.mkdir()
        profile = {
            "profile_id": "test",
            "canvas_width": 32,
            "canvas_height": 24,
            "color_space": "sRGB",
            "alpha_mode": "binary_straight",
        }
        poses = OrderedDict()
        pairs = []
        for ordinal in range(1, 67):
            pose_id = f"kingfisher.act.{ordinal:03d}.pose-{ordinal:03d}"
            resting = Image.new("RGBA", (32, 24), (0, 0, 0, 0))
            resting.paste((20, 40, 60, 255), (8, 4, 24, 23))
            poses[pose_id] = resting
        artifact_path = base_root / "base.wjpose"
        receipt = write_pose_artifact(
            artifact_path,
            poses,
            profile=profile,
            provenance={"source": "test"},
        )
        base_index = {
            "schema_version": 1,
            "asset_set_id": "test-base",
            "character_id": "kingfisher",
            "profile": profile,
            "pose_count": 66,
            "pose_ids": list(poses),
            "shards": [
                {
                    "shard_id": "base",
                    "path": artifact_path.name,
                    "sha256": receipt["sha256"],
                    "bytes": receipt["bytes"],
                    "pose_count": 66,
                    "pose_ids": list(poses),
                    "approval_state": "candidate_visual_review",
                    "review_projection": True,
                    "runtime_admitted": False,
                    "source": "test",
                }
            ],
            "sequences": {},
            "review_projection": True,
            "runtime_admitted": False,
        }
        base_index_path = base_root / "library-index.json"
        base_index_path.write_text(json.dumps(base_index), encoding="utf-8")

        for ordinal, resting_pose_id in enumerate(poses, start=1):
            work = pair_root / f"{ordinal:03d}"
            work.mkdir()
            speaking_ordinal = ordinal + 110
            speaking_pose_id = (
                f"kingfisher.act.{speaking_ordinal:03d}.pose-{ordinal:03d}-speaking-beak"
            )
            resting_path = work / "resting.png"
            speaking_path = work / "speaking.png"
            poses[resting_pose_id].save(resting_path)
            speaking = poses[resting_pose_id].copy()
            speaking.paste((5, 8, 12, 255), (13, 9, 19, 12))
            speaking.save(speaking_path)
            pair_receipt = {
                "approval_state": "candidate_visual_review",
                "runtime_admitted": False,
                "resting_path": resting_path.as_posix(),
                "speaking_path": speaking_path.as_posix(),
                "resting_sha256": sha256_path(resting_path),
                "speaking_sha256": sha256_path(speaking_path),
            }
            pair_audit = {
                "passed": True,
                "resting_sha256": sha256_path(resting_path),
                "speaking_sha256": sha256_path(speaking_path),
            }
            receipt_path = work / "receipt.json"
            audit_path = work / "audit.json"
            receipt_path.write_text(json.dumps(pair_receipt), encoding="utf-8")
            audit_path.write_text(json.dumps(pair_audit), encoding="utf-8")
            pairs.append(
                {
                    "ordinal": ordinal,
                    "speaking_ordinal": speaking_ordinal,
                    "resting_pose_id": resting_pose_id,
                    "speaking_pose_id": speaking_pose_id,
                    "status": "candidate_visual_review",
                    "automated_audit_passed": True,
                    "user_approved": False,
                    "runtime_admitted": False,
                    "pairwise_full_size_review": {
                        "protocol_id": "kingfisher-full-size-pairwise-v1",
                        "state": "pending",
                        "evidence_path": "",
                        "user_approval_implied": False,
                        "runtime_admission_implied": False,
                    },
                    "receipt_path": receipt_path.as_posix(),
                    "audit_path": audit_path.as_posix(),
                }
            )
        ledger_path = pair_root / "ledger.json"
        ledger_path.write_text(
            json.dumps(
                {
                    "character_id": "kingfisher",
                    "pair_count": 66,
                    "runtime_admitted_count": 0,
                    "pairs": pairs,
                }
            ),
            encoding="utf-8",
        )
        return base_index_path, ledger_path

    def test_compiles_alternating_review_sequence_without_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base_index, ledger = self._fixture(root)
            output = root / "review"

            result = compile_pair_review_library(base_index, ledger, output)

            library = HDPoseLibrary(output / "library-index.json")
            sequence = library.index["sequences"]["kingfisher-paired-beaks-review"]
            self.assertEqual(result["pose_count"], 132)
            self.assertEqual(result["pair_count"], 66)
            self.assertEqual(len(sequence["pose_ids"]), 132)
            self.assertEqual(sequence["pair_review_states"], ["pending"] * 66)
            self.assertEqual(
                sequence["pose_ids"][:4],
                [
                    "kingfisher.act.001.pose-001",
                    "kingfisher.act.111.pose-001-speaking-beak",
                    "kingfisher.act.002.pose-002",
                    "kingfisher.act.112.pose-002-speaking-beak",
                ],
            )
            self.assertFalse(library.index["runtime_admitted"])
            self.assertEqual(
                library.index["legacy_pair_review"]["user_approved_count"],
                0,
            )
            shard = next(
                shard for shard in library.index["shards"]
                if shard["shard_id"] == compiler.PAIR_REVIEW_SHARD_ID
            )
            self.assertIn(shard["sha256"][:16], shard["path"])

    def test_rejects_user_approved_or_runtime_admitted_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base_index, ledger = self._fixture(root)
            original = json.loads(ledger.read_text(encoding="utf-8"))
            for field in ("user_approved", "runtime_admitted"):
                with self.subTest(field=field):
                    changed = json.loads(json.dumps(original))
                    changed["pairs"][0][field] = True
                    ledger.write_text(json.dumps(changed), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "cannot"):
                        compile_pair_review_library(base_index, ledger, root / field)
            ledger.write_text(json.dumps(original), encoding="utf-8")

    def test_rejects_unknown_pairwise_review_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base_index, ledger = self._fixture(root)
            data = json.loads(ledger.read_text(encoding="utf-8"))
            data["pairs"][0]["pairwise_full_size_review"]["protocol_id"] = (
                "unknown-protocol"
            )
            ledger.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "protocol"):
                compile_pair_review_library(base_index, ledger, root / "review")

    def test_rejects_modified_speaking_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base_index, ledger = self._fixture(root)
            data = json.loads(ledger.read_text(encoding="utf-8"))
            receipt_path = Path(data["pairs"][0]["receipt_path"])
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            speaking_path = Path(receipt["speaking_path"])
            with Image.open(speaking_path) as loaded:
                changed = loaded.convert("RGBA")
            changed.putpixel((16, 10), (255, 0, 0, 255))
            changed.save(speaking_path)

            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                compile_pair_review_library(base_index, ledger, root / "review")

    def test_failed_artifact_write_preserves_previous_review_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base_index, ledger = self._fixture(root)
            output = root / "review"
            output.mkdir()
            artifact = output / (
                f"{compiler.PAIR_REVIEW_SHARD_ID}-previous.wjpose"
            )
            artifact.write_bytes(b"previous-complete-artifact")

            def fail_after_partial_write(destination, *args, **kwargs):
                Path(destination).write_bytes(b"partial")
                raise RuntimeError("simulated interrupted artifact write")

            with patch.object(
                compiler,
                "write_pose_artifact",
                side_effect=fail_after_partial_write,
            ):
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    compile_pair_review_library(base_index, ledger, output)

            self.assertEqual(artifact.read_bytes(), b"previous-complete-artifact")
            self.assertEqual(list(output.glob(".*.tmp")), [])

    def test_verifier_requires_internal_review_and_checks_every_pose(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base_index, ledger = self._fixture(root)
            ledger_data = json.loads(ledger.read_text(encoding="utf-8"))
            for pair in ledger_data["pairs"]:
                pair["internal_visual_review"] = {
                    "state": "pass",
                    "user_approval_implied": False,
                    "runtime_admission_implied": False,
                }
                pair["pairwise_full_size_review"]["state"] = "pass"
            ledger.write_text(json.dumps(ledger_data), encoding="utf-8")
            output = root / "review"
            compile_pair_review_library(base_index, ledger, output)

            report = verify_pair_review(output / "library-index.json", ledger)

            self.assertTrue(report["passed"])
            self.assertEqual(report["pair_count"], 66)
            self.assertEqual(report["paired_sequence_frame_count"], 132)
            self.assertEqual(report["binary_alpha_pose_count"], 132)
            self.assertEqual(report["pairwise_full_size_pass_count"], 66)
            self.assertEqual(report["runtime_admitted_count"], 0)

            ledger_data["pairs"][0]["pairwise_full_size_review"]["state"] = (
                "needs_rebuild"
            )
            ledger.write_text(json.dumps(ledger_data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pairwise disposition"):
                verify_pair_review(output / "library-index.json", ledger)

            ledger_data["pairwise_full_size_review_summary"] = {
                "pair_count": 66,
                "pending_count": 0,
                "pass_count": 65,
                "needs_rebuild_count": 1,
                "not_observable_count": 0,
            }
            ledger.write_text(json.dumps(ledger_data), encoding="utf-8")
            report = blocked_pair_review_report(
                output / "library-index.json",
                ledger,
                ValueError(
                    "pair 1 lacks a passing full-size pairwise disposition"
                ),
            )
            self.assertFalse(report["passed"])
            self.assertEqual(report["pairwise_full_size_pass_count"], 65)
            self.assertEqual(report["needs_rebuild_count"], 1)
            self.assertEqual(
                report["verification_state"],
                "blocked_by_pairwise_full_size_review",
            )


if __name__ == "__main__":
    unittest.main()
