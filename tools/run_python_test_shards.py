#!/usr/bin/env python3
"""Run every unittest file in deterministic parallel process shards."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence


TAIL_LIMIT = 12_000


def discover_test_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("test_*.py") if path.is_file())


def partition_test_files(files: Sequence[Path], jobs: int) -> list[list[Path]]:
    if jobs < 1:
        raise ValueError("jobs must be at least 1")
    shard_count = min(jobs, max(1, len(files)))
    shards: list[list[Path]] = [[] for _ in range(shard_count)]
    weights = [0] * shard_count
    for path in sorted(files, key=lambda item: (-item.stat().st_size, item.as_posix())):
        index = min(range(shard_count), key=lambda candidate: (weights[candidate], candidate))
        shards[index].append(path)
        weights[index] += path.stat().st_size
    for shard in shards:
        shard.sort()
    return shards


def _tail(value: str) -> str:
    return value[-TAIL_LIMIT:]


def _run_shard(
    index: int,
    files: Sequence[Path],
    *,
    cwd: Path,
    timeout: float,
) -> dict[str, Any]:
    arguments = [path.resolve().relative_to(cwd.resolve()).as_posix() for path in files]
    command = [sys.executable, "-m", "unittest", *arguments]
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "shard": index,
            "file_count": len(files),
            "files": arguments,
            "duration_seconds": round(time.monotonic() - started, 3),
            "returncode": result.returncode,
            "timed_out": False,
            "stdout_tail": _tail(result.stdout),
            "stderr_tail": _tail(result.stderr),
            "passed": result.returncode == 0,
        }
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "shard": index,
            "file_count": len(files),
            "files": arguments,
            "duration_seconds": round(time.monotonic() - started, 3),
            "returncode": None,
            "timed_out": True,
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
            "passed": False,
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests-root", type=Path, default=Path("tests"))
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout-per-shard", type=float, default=3300.0)
    parser.add_argument("--only-shard", type=int)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args(argv)
    root = arguments.tests_root
    cwd = root.resolve().parent if root.is_absolute() else Path.cwd()
    files = discover_test_files(root)
    if not files:
        parser.error(f"no unittest files found beneath {root}")
    shards = partition_test_files(files, arguments.jobs)
    indexed_shards = list(enumerate(shards, start=1))
    if arguments.only_shard is not None:
        if not 1 <= arguments.only_shard <= len(shards):
            parser.error(f"--only-shard must be between 1 and {len(shards)}")
        indexed_shards = [indexed_shards[arguments.only_shard - 1]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(indexed_shards)) as executor:
        futures = [
            executor.submit(
                _run_shard,
                index,
                shard,
                cwd=cwd,
                timeout=arguments.timeout_per_shard,
            )
            for index, shard in indexed_shards
        ]
        results = [future.result() for future in futures]
    results.sort(key=lambda result: result["shard"])
    passed = all(result["passed"] for result in results)
    receipt = {
        "schema_version": 1,
        "gate": "complete-python-suite-sharded",
        "test_file_count": len(files),
        "executed_file_count": sum(len(result["files"]) for result in results),
        "shard_count": len(shards),
        "executed_shards": [result["shard"] for result in results],
        "passed": passed,
        "shards": results,
    }
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if arguments.output is not None:
        output = arguments.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(
            json.dumps(
                {
                    "gate": receipt["gate"],
                    "passed": passed,
                    "test_file_count": receipt["test_file_count"],
                    "executed_file_count": receipt["executed_file_count"],
                    "executed_shards": receipt["executed_shards"],
                    "output": str(output),
                },
                sort_keys=True,
            )
        )
    else:
        print(rendered, end="")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
