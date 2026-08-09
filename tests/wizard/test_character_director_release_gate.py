from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.verify_character_director_release import main, run_fast_gate


class CharacterDirectorReleaseGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name) / "fixture"
        self.repo.mkdir()
        self._git("init", "-q")
        self._git("config", "user.email", "release-gate@example.invalid")
        self._git("config", "user.name", "Release Gate Fixture")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _git(self, *arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            self.fail(result.stderr)
        return result.stdout.strip()

    def _write(self, path: str, content: str | bytes) -> None:
        destination = self.repo / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            destination.write_bytes(content)
        else:
            destination.write_text(content, encoding="utf-8")

    def _commit_all(self) -> str:
        self._git("add", ".")
        self._git("commit", "-q", "-m", "fixture")
        return self._git("rev-parse", "HEAD")

    @staticmethod
    def _contract(**overrides: object) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_version": 1,
            "contract_id": "unit-fixture-v1",
            "required_files": [],
            "required_trees": [],
            "reference_manifests": [],
            "locked_distributions": [],
            "remote_refs": [],
        }
        value.update(overrides)
        return value

    def test_fast_mode_accepts_tracked_declared_manifest_input(self) -> None:
        self._write("release/asset.bin", b"approved")
        self._write("release/index.json", '{"asset_path": "asset.bin"}\n')
        commit = self._commit_all()
        contract = self._contract(
            required_files=["release/index.json", "release/asset.bin"],
            reference_manifests=["release/index.json"],
        )

        receipt = run_fast_gate(self.repo, "HEAD", contract)

        self.assertTrue(receipt["passed"])
        self.assertEqual(commit, receipt["commit"])
        self.assertEqual([], receipt["issues"])
        self.assertEqual(1, receipt["closure"]["manifest_reference_count"])

    def test_fast_mode_fails_closed_on_tracked_but_undeclared_input(self) -> None:
        self._write("release/asset.bin", b"not declared")
        self._write("release/index.json", '{"asset_path": "asset.bin"}\n')
        self._commit_all()
        contract = self._contract(
            required_files=["release/index.json"],
            reference_manifests=["release/index.json"],
        )

        receipt = run_fast_gate(self.repo, "HEAD", contract)

        self.assertFalse(receipt["passed"])
        self.assertIn("input.undeclared", {issue["code"] for issue in receipt["issues"]})
        self.assertIn(
            "release/asset.bin",
            {issue.get("path") for issue in receipt["issues"]},
        )

    def test_fast_mode_fails_closed_when_declared_input_is_only_untracked(self) -> None:
        self._write("release/index.json", "{}\n")
        self._commit_all()
        self._write("release/local-only.bin", b"working tree only")
        contract = self._contract(
            required_files=["release/index.json", "release/local-only.bin"],
        )

        receipt = run_fast_gate(self.repo, "HEAD", contract)

        self.assertFalse(receipt["passed"])
        self.assertIn(
            {
                "code": "input.untracked_or_missing",
                "message": "declared release file is absent from the selected commit",
                "path": "release/local-only.bin",
            },
            receipt["issues"],
        )

    def test_fast_mode_reads_selected_commit_not_dirty_worktree(self) -> None:
        self._write("release/asset.bin", b"committed")
        self._write("release/index.json", '{"asset_path": "asset.bin"}\n')
        commit = self._commit_all()
        self._write("release/index.json", '{"asset_path": "local-only.bin"}\n')
        self._write("release/local-only.bin", b"untracked")
        contract = self._contract(
            required_files=["release/index.json", "release/asset.bin"],
            reference_manifests=["release/index.json"],
        )

        receipt = run_fast_gate(self.repo, commit, contract)

        self.assertTrue(receipt["passed"])
        self.assertTrue(receipt["source_worktree"]["dirty"])
        self.assertEqual("release/asset.bin", receipt["closure"]["references"][0]["path"])

    def test_fast_mode_rejects_manifest_checksum_mismatch(self) -> None:
        self._write("release/asset.bin", b"actual")
        self._write(
            "release/index.json",
            json.dumps({"asset_path": "asset.bin", "asset_sha256": "0" * 64}),
        )
        self._commit_all()
        contract = self._contract(
            required_files=["release/index.json", "release/asset.bin"],
            reference_manifests=["release/index.json"],
        )

        receipt = run_fast_gate(self.repo, "HEAD", contract)

        self.assertFalse(receipt["passed"])
        self.assertIn(
            "input.checksum_mismatch",
            {issue["code"] for issue in receipt["issues"]},
        )

    def test_fast_mode_validates_git_lfs_object_identity(self) -> None:
        digest = "a" * 64
        self._write(
            "release/asset.wjpose",
            (
                "version https://git-lfs.github.com/spec/v1\n"
                f"oid sha256:{digest}\n"
                "size 1234\n"
            ),
        )
        self._write(
            "release/index.json",
            json.dumps({"asset_path": "asset.wjpose", "asset_sha256": digest}),
        )
        self._commit_all()
        contract = self._contract(
            required_files=["release/index.json", "release/asset.wjpose"],
            reference_manifests=["release/index.json"],
        )

        receipt = run_fast_gate(self.repo, "HEAD", contract)

        self.assertTrue(receipt["passed"])

    def test_fast_mode_ignores_absent_optional_pair_review_evidence(self) -> None:
        self._write(
            "release/library-index.json",
            json.dumps(
                {
                    "legacy_pair_review": {
                        "pairs": [
                            {
                                "pairwise_full_size_review": {
                                    "evidence_path": "",
                                }
                            }
                        ]
                    }
                }
            ),
        )
        self._commit_all()
        contract = self._contract(
            required_files=["release/library-index.json"],
            reference_manifests=[
                {
                    "path": "release/library-index.json",
                    "kind": "hd_review_library",
                }
            ],
        )

        receipt = run_fast_gate(self.repo, "HEAD", contract)

        self.assertTrue(receipt["passed"])
        self.assertEqual(0, receipt["closure"]["manifest_reference_count"])

    def test_fast_mode_requires_verifier_distribution_in_all_lock_surfaces(self) -> None:
        self._write(
            "pyproject.toml",
            '[project]\nname = "fixture"\nversion = "0"\ndependencies = []\n',
        )
        self._write("requirements.txt", "")
        self._write("uv.lock", "version = 1\n")
        self._commit_all()
        contract = self._contract(
            required_files=["pyproject.toml", "requirements.txt", "uv.lock"],
            locked_distributions=["numpy"],
        )

        receipt = run_fast_gate(self.repo, "HEAD", contract)

        self.assertFalse(receipt["passed"])
        unlocked = [
            issue for issue in receipt["issues"] if issue["code"] == "dependency.unlocked"
        ]
        self.assertEqual(3, len(unlocked))

    def test_cli_fast_fixture_mode_writes_machine_readable_receipt(self) -> None:
        self._write("release/asset.bin", b"approved")
        self._commit_all()
        contract_path = Path(self.temporary.name) / "contract.json"
        contract_path.write_text(
            json.dumps(
                self._contract(required_files=["release/asset.bin"]),
                indent=2,
            ),
            encoding="utf-8",
        )
        receipt_path = Path(self.temporary.name) / "receipt.json"

        with contextlib.redirect_stdout(io.StringIO()):
            returncode = main(
                [
                    "--mode",
                    "fast",
                    "--repo",
                    str(self.repo),
                    "--contract",
                    str(contract_path),
                    "--output",
                    str(receipt_path),
                ]
            )

        self.assertEqual(0, returncode)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertTrue(receipt["passed"])
        self.assertEqual("fast", receipt["mode"])


if __name__ == "__main__":
    unittest.main()
