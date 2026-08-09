from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.run_python_test_shards import discover_test_files, main, partition_test_files


class PythonTestShardPlanTests(unittest.TestCase):
    def test_partition_is_complete_unique_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files: list[Path] = []
            for index, size in enumerate((80, 10, 50, 20, 40)):
                path = root / f"test_{index}.py"
                path.write_text("x" * size, encoding="utf-8")
                files.append(path)
            first = partition_test_files(files, 3)
            second = partition_test_files(list(reversed(files)), 3)
            self.assertEqual(first, second)
            flattened = [path for shard in first for path in shard]
            self.assertEqual(sorted(files), sorted(flattened))
            self.assertEqual(len(files), len(set(flattened)))

    def test_discovery_matches_unittest_pattern_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "nested").mkdir()
            expected = root / "nested" / "test_feature.py"
            expected.write_text("", encoding="utf-8")
            (root / "nested" / "helper.py").write_text("", encoding="utf-8")
            self.assertEqual([expected], discover_test_files(root))

    def test_jobs_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 1"):
            partition_test_files([], 0)

    def test_runner_executes_every_discovered_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("test_first.py", "test_second.py"):
                (root / name).write_text(
                    "import unittest\n"
                    "class ExampleTests(unittest.TestCase):\n"
                    "    def test_passes(self):\n"
                    "        self.assertTrue(True)\n",
                    encoding="utf-8",
                )
            output = io.StringIO()
            receipt_path = root / "receipt.json"
            with contextlib.redirect_stdout(output):
                returncode = main(
                    [
                        "--tests-root",
                        str(root),
                        "--jobs",
                        "2",
                        "--timeout-per-shard",
                        "30",
                        "--output",
                        str(receipt_path),
                    ]
                )
            summary = json.loads(output.getvalue())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(0, returncode, receipt)
            self.assertTrue(summary["passed"])
            self.assertTrue(receipt["passed"])
            self.assertEqual(2, receipt["test_file_count"])
            self.assertEqual(2, receipt["shard_count"])
