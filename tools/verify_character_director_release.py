#!/usr/bin/env python3
"""Verify a Character Director release from one immutable Git commit.

Fast mode performs commit and release-input closure checks only. Full mode
clones the selected commit, installs its frozen dependency lock, rebuilds the
declared review libraries, runs bounded verification shards, and smoke-tests
the real loopback HTTP/WebSocket server.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = 1
TAIL_LIMIT = 12_000
PATH_KEYS = {"path", "package"}
ROOT_PREFIXES = (
    "assets/",
    "companion/",
    "docs/",
    "tests/",
    "tools/",
    "wizard_avatar/",
)

DEFAULT_CONTRACT: dict[str, Any] = {
    "schema_version": 1,
    "contract_id": "character-director-python-release-v1",
    "required_files": [
        "pyproject.toml",
        "requirements.txt",
        "uv.lock",
        "docs/cartoon-animation-program/registry.json",
        "tools/verify_character_director_release.py",
        "wizard_avatar/definitions/character_registry.json",
        "wizard_avatar/definitions/wizard_joe_character_package.json",
        "assets/reference/characters/kingfisher/pair-review-compiled/library-index.json",
        "assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json",
    ],
    "required_trees": [
        "assets/reference/characters/dragon/interim-v001",
        "assets/reference/characters/dragon/source",
        "assets/reference/characters/dragon/source-repair",
        "assets/reference/characters/kingfisher/legacy-pairs-v1",
        "assets/reference/characters/kingfisher/pair-review-compiled",
        "assets/reference/characters/robin_speech/source",
        "tests",
        "tools",
        "wizard_avatar",
    ],
    "reference_manifests": [
        {
            "path": "wizard_avatar/definitions/character_registry.json",
            "kind": "character_registry",
        },
        {
            "path": "wizard_avatar/definitions/wizard_joe_character_package.json",
            "kind": "character_package",
        },
        {
            "path": "assets/reference/characters/kingfisher/pair-review-compiled/library-index.json",
            "kind": "hd_review_library",
        },
    ],
    "locked_distributions": ["numpy"],
    "remote_refs": ["codex/python-asciline-avatar"],
}


@dataclass(frozen=True)
class GateIssue:
    code: str
    message: str
    path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.path is not None:
            value["path"] = self.path
        return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _tail(value: str) -> str:
    return value[-TAIL_LIMIT:]


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: float = 120.0,
    check: bool = False,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        cwd=str(cwd),
        env=None if env is None else dict(env),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        rendered = " ".join(command)
        raise RuntimeError(
            f"command failed ({result.returncode}): {rendered}\n"
            f"{_tail(result.stdout)}\n{_tail(result.stderr)}"
        )
    return result


def _git(repo: Path, arguments: Sequence[str], *, check: bool = True) -> str:
    result = _run(["git", *arguments], cwd=repo, timeout=180.0)
    if check and result.returncode != 0:
        raise RuntimeError(_tail(result.stderr) or _tail(result.stdout))
    return result.stdout.strip()


def repository_root(path: Path) -> Path:
    candidate = path.resolve()
    root = _git(candidate, ["rev-parse", "--show-toplevel"])
    return Path(root).resolve()


def resolve_commit(repo: Path, revision: str) -> str:
    arguments = ["rev-parse", "--verify", f"{revision}^{{commit}}"]
    return _git(repo, arguments)


def commit_files(repo: Path, commit: str) -> set[str]:
    listing = _git(repo, ["ls-tree", "-r", "--name-only", commit])
    return {line for line in listing.splitlines() if line}


def commit_bytes(repo: Path, commit: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            result.stderr.decode("utf-8", errors="replace").strip()
            or f"cannot read {path} from {commit}"
        )
    return result.stdout


def _clean_relative_path(raw: object) -> str:
    if not isinstance(raw, str):
        raise ValueError(f"repository-relative path must be a string: {raw!r}")
    text = str(raw).replace("\\", "/").strip()
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe repository-relative path: {raw!r}")
    return path.as_posix()


def load_contract(path: Path | None) -> dict[str, Any]:
    if path is None:
        return json.loads(json.dumps(DEFAULT_CONTRACT))
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("release contract must be a schema_version 1 JSON object")
    return value


def _is_under(path: str, tree: str) -> bool:
    return path == tree or path.startswith(tree.rstrip("/") + "/")


def _declared(path: str, files: set[str], trees: set[str]) -> bool:
    return path in files or any(_is_under(path, tree) for tree in trees)


def _tracked_path(path: str, tracked: set[str]) -> bool:
    return path in tracked or any(item.startswith(path.rstrip("/") + "/") for item in tracked)


def _reference_path(manifest_path: str, raw: str) -> str:
    cleaned = _clean_relative_path(raw)
    if cleaned.startswith(ROOT_PREFIXES):
        return cleaned
    parent = PurePosixPath(manifest_path).parent
    return (parent / cleaned).as_posix()


def _iter_path_references(value: object) -> Iterable[tuple[str, str, str | None]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str) and (
                key in PATH_KEYS or key.endswith("_path")
            ):
                checksum_key = "sha256" if key == "path" else f"{key[:-5]}_sha256"
                checksum = value.get(checksum_key)
                yield key, child, checksum if isinstance(checksum, str) else None
            yield from _iter_path_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_path_references(child)


def _manifest_references(
    value: object,
    kind: str,
) -> Iterable[tuple[str, str, str | None]]:
    if not isinstance(value, dict) or kind == "generic":
        yield from _iter_path_references(value)
        return
    if kind == "character_registry":
        for record in value.get("characters", []):
            if isinstance(record, dict) and isinstance(record.get("package"), str):
                checksum = record.get("package_sha256")
                yield (
                    "package",
                    record["package"],
                    checksum if isinstance(checksum, str) else None,
                )
        return
    if kind == "character_package":
        for key in ("pose_library", "animation_graph"):
            if isinstance(value.get(key), str):
                yield key, value[key], None
        return
    if kind == "hd_review_library":
        dictionary = value.get("choreography_dictionary")
        if isinstance(dictionary, dict) and isinstance(dictionary.get("path"), str):
            checksum = dictionary.get("sha256")
            yield "path", dictionary["path"], checksum if isinstance(checksum, str) else None
        for shard in value.get("shards", []):
            if isinstance(shard, dict) and isinstance(shard.get("path"), str):
                checksum = shard.get("sha256")
                yield "path", shard["path"], checksum if isinstance(checksum, str) else None
        legacy = value.get("legacy_pair_review")
        if isinstance(legacy, dict):
            ledger_path = legacy.get("ledger_path")
            if isinstance(ledger_path, str):
                checksum = legacy.get("ledger_sha256")
                yield "ledger_path", ledger_path, checksum if isinstance(checksum, str) else None
            for pair in legacy.get("pairs", []):
                if not isinstance(pair, dict):
                    continue
                for key in ("audit_path", "receipt_path"):
                    raw = pair.get(key)
                    if isinstance(raw, str):
                        checksum = pair.get(f"{key[:-5]}_sha256")
                        yield key, raw, checksum if isinstance(checksum, str) else None
                visual = pair.get("pairwise_full_size_review")
                if isinstance(visual, dict) and isinstance(visual.get("evidence_path"), str):
                    yield "evidence_path", visual["evidence_path"], None
        return
    raise ValueError(f"unknown reference manifest kind: {kind}")


def _committed_sha256(repo: Path, commit: str, path: str) -> str:
    payload = commit_bytes(repo, commit, path)
    if payload.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
        match = re.search(rb"(?m)^oid sha256:([0-9a-f]{64})$", payload)
        if match is None:
            raise ValueError(f"invalid Git LFS pointer: {path}")
        return match.group(1).decode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _dependency_names_from_pyproject(payload: str) -> set[str]:
    match = re.search(
        r"(?ms)^dependencies\s*=\s*\[(.*?)^\]",
        payload,
    )
    if match is None:
        return set()
    names: set[str] = set()
    for requirement in re.findall(r"[\"']([^\"']+)[\"']", match.group(1)):
        package = re.match(r"[A-Za-z0-9_.-]+", requirement.strip())
        if package:
            names.add(package.group(0).lower().replace("_", "-"))
    return names


def _dependency_names_from_requirements(payload: str) -> set[str]:
    names: set[str] = set()
    for line in payload.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        package = re.match(r"[A-Za-z0-9_.-]+", stripped)
        if package:
            names.add(package.group(0).lower().replace("_", "-"))
    return names


def _dependency_names_from_uv_lock(payload: str) -> set[str]:
    return {
        name.lower().replace("_", "-")
        for name in re.findall(r'(?m)^name = "([A-Za-z0-9_.-]+)"$', payload)
    }


def validate_commit_closure(
    repo: Path,
    commit: str,
    contract: Mapping[str, Any],
) -> tuple[list[GateIssue], dict[str, Any]]:
    """Validate all declared and manifest-discovered inputs against a commit."""

    issues: list[GateIssue] = []
    tracked = commit_files(repo, commit)
    required_files: set[str] = set()
    required_trees: set[str] = set()

    for raw in contract.get("required_files", []):
        try:
            required_files.add(_clean_relative_path(raw))
        except ValueError as error:
            issues.append(GateIssue("contract.unsafe_path", str(error)))
    for raw in contract.get("required_trees", []):
        try:
            required_trees.add(_clean_relative_path(raw).rstrip("/"))
        except ValueError as error:
            issues.append(GateIssue("contract.unsafe_path", str(error)))

    for path in sorted(required_files):
        if path not in tracked:
            issues.append(
                GateIssue(
                    "input.untracked_or_missing",
                    "declared release file is absent from the selected commit",
                    path,
                )
            )
    for tree in sorted(required_trees):
        if not any(_is_under(path, tree) for path in tracked):
            issues.append(
                GateIssue(
                    "input.untracked_or_missing",
                    "declared release tree has no files in the selected commit",
                    tree,
                )
            )

    references: list[dict[str, Any]] = []
    for raw_manifest in contract.get("reference_manifests", []):
        if isinstance(raw_manifest, dict):
            raw_manifest_path = raw_manifest.get("path")
            manifest_kind = str(raw_manifest.get("kind", "generic"))
        else:
            raw_manifest_path = raw_manifest
            manifest_kind = "generic"
        try:
            manifest_path = _clean_relative_path(raw_manifest_path)
        except ValueError as error:
            issues.append(GateIssue("contract.unsafe_path", str(error)))
            continue
        if manifest_path not in tracked:
            issues.append(
                GateIssue(
                    "input.untracked_or_missing",
                    "reference manifest is absent from the selected commit",
                    manifest_path,
                )
            )
            continue
        try:
            manifest = json.loads(commit_bytes(repo, commit, manifest_path))
        except (ValueError, json.JSONDecodeError) as error:
            issues.append(GateIssue("manifest.invalid", str(error), manifest_path))
            continue
        try:
            discovered_references = list(_manifest_references(manifest, manifest_kind))
        except ValueError as error:
            issues.append(GateIssue("manifest.invalid_kind", str(error), manifest_path))
            continue
        for key, raw_reference, expected_sha256 in discovered_references:
            if "://" in raw_reference:
                continue
            try:
                referenced_path = _reference_path(manifest_path, raw_reference)
            except ValueError as error:
                issues.append(GateIssue("manifest.unsafe_reference", str(error), manifest_path))
                continue
            references.append(
                {
                    "manifest": manifest_path,
                    "key": key,
                    "path": referenced_path,
                    "expected_sha256": expected_sha256,
                }
            )
            if not _declared(referenced_path, required_files, required_trees):
                issues.append(
                    GateIssue(
                        "input.undeclared",
                        f"{manifest_path} references an input outside the release contract",
                        referenced_path,
                    )
                )
                continue
            if not _tracked_path(referenced_path, tracked):
                issues.append(
                    GateIssue(
                        "input.untracked_or_missing",
                        f"{manifest_path} references a path absent from the selected commit",
                        referenced_path,
                    )
                )
                continue
            if expected_sha256 and referenced_path in tracked:
                actual = _committed_sha256(repo, commit, referenced_path)
                normalized_expected = expected_sha256.removeprefix("sha256:")
                if actual != normalized_expected:
                    issues.append(
                        GateIssue(
                            "input.checksum_mismatch",
                            f"{manifest_path} checksum does not match the committed input",
                            referenced_path,
                        )
                    )

    dependency_files = ("pyproject.toml", "requirements.txt", "uv.lock")
    if all(path in tracked for path in dependency_files):
        dependency_sets = {
            "pyproject.toml": _dependency_names_from_pyproject(
                commit_bytes(repo, commit, "pyproject.toml").decode("utf-8")
            ),
            "requirements.txt": _dependency_names_from_requirements(
                commit_bytes(repo, commit, "requirements.txt").decode("utf-8")
            ),
            "uv.lock": _dependency_names_from_uv_lock(
                commit_bytes(repo, commit, "uv.lock").decode("utf-8")
            ),
        }
        for raw_name in contract.get("locked_distributions", []):
            name = str(raw_name).lower().replace("_", "-")
            for source, names in dependency_sets.items():
                if name not in names:
                    issues.append(
                        GateIssue(
                            "dependency.unlocked",
                            f"required verifier distribution {name!r} is absent from {source}",
                            source,
                        )
                    )

    details = {
        "tracked_file_count": len(tracked),
        "declared_file_count": len(required_files),
        "declared_tree_count": len(required_trees),
        "manifest_reference_count": len(references),
        "references": references,
    }
    return issues, details


def _source_status(repo: Path) -> dict[str, Any]:
    porcelain = _git(repo, ["status", "--porcelain=v1", "--untracked-files=all"])
    return {
        "dirty": bool(porcelain),
        "entry_count": len(porcelain.splitlines()) if porcelain else 0,
    }


def run_fast_gate(
    repo: Path,
    revision: str,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    root = repository_root(repo)
    commit = resolve_commit(root, revision)
    issues, closure = validate_commit_closure(root, commit, contract)
    return {
        "schema_version": SCHEMA_VERSION,
        "gate": "character-director-release",
        "mode": "fast",
        "contract_id": contract.get("contract_id", "custom-fixture-contract"),
        "repository": str(root),
        "revision": revision,
        "commit": commit,
        "source_worktree": _source_status(root),
        "closure": closure,
        "issues": [issue.as_dict() for issue in issues],
        "passed": not issues,
    }


def _command_receipt(
    name: str,
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: float,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = _run(command, cwd=cwd, timeout=timeout, env=env)
        return {
            "name": name,
            "command": list(command),
            "returncode": result.returncode,
            "duration_seconds": round(time.monotonic() - started, 3),
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
            "name": name,
            "command": list(command),
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
            "timed_out": True,
            "passed": False,
        }


def _sha256_tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _runtime_smoke(
    checkout: Path,
    python: Path,
    *,
    name: str,
    review_index: Path | None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    port = _free_port()
    command = [
        str(python),
        "tools/run_wizard_avatar_server.py",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--quiet",
    ]
    if review_index is not None:
        command.extend(["--review-library-index", str(review_index)])
    started = time.monotonic()
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=str(checkout),
            stdout=log,
            stderr=log,
            text=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        health: dict[str, Any] | None = None
        error = "server did not become healthy"
        try:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    error = f"server exited with {process.returncode}"
                    break
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/companion/health",
                        timeout=1.0,
                    ) as response:
                        health = json.loads(response.read())
                    if health.get("status") == "ready":
                        break
                except (OSError, urllib.error.URLError, json.JSONDecodeError):
                    time.sleep(0.1)
            if health is not None and health.get("status") == "ready":
                websocket_probe = _command_receipt(
                    f"{name}-websocket",
                    [
                        str(python),
                        "-c",
                        (
                            "from websockets.sync.client import connect; "
                            f"w=connect('ws://127.0.0.1:{port}/ws/avatar/wizard?codec=adaptive', "
                            "open_timeout=5); "
                            "i=w.recv(timeout=5); f=w.recv(timeout=10); "
                            "assert isinstance(i,str) and i.startswith('INIT:'); "
                            "assert isinstance(f,bytes) and len(f)>0; w.close()"
                        ),
                    ],
                    cwd=checkout,
                    timeout=20.0,
                )
                passed = bool(websocket_probe["passed"])
                if not passed:
                    error = "WebSocket did not emit INIT plus a binary frame"
            else:
                websocket_probe = None
                passed = False
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5.0)
            log.seek(0)
            logs = _tail(log.read())
    return {
        "name": name,
        "review_index": None if review_index is None else str(review_index),
        "duration_seconds": round(time.monotonic() - started, 3),
        "health": health,
        "websocket": websocket_probe,
        "server_log_tail": logs,
        "error": None if passed else error,
        "passed": passed,
    }


def _prepare_remote_refs(
    source: Path,
    checkout: Path,
    branches: Sequence[str],
    *,
    offline: bool,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    upstream = _git(source, ["remote", "get-url", "origin"], check=False)
    for branch in branches:
        target = f"refs/remotes/origin/{branch}"
        if offline:
            source_ref = f"refs/remotes/origin/{branch}"
            commit = _git(source, ["rev-parse", "--verify", source_ref], check=False)
            if not commit:
                records.append(
                    {"branch": branch, "passed": False, "error": "remote ref unavailable offline"}
                )
                continue
            result = _command_receipt(
                f"materialize-ref-{branch}",
                ["git", "update-ref", target, commit],
                cwd=checkout,
                timeout=30.0,
            )
        elif not upstream:
            result = {
                "name": f"fetch-ref-{branch}",
                "passed": False,
                "error": "source repository has no origin URL",
            }
        else:
            result = _command_receipt(
                f"fetch-ref-{branch}",
                [
                    "git",
                    "fetch",
                    "--no-tags",
                    upstream,
                    f"refs/heads/{branch}:{target}",
                ],
                cwd=checkout,
                timeout=180.0,
            )
        records.append({"branch": branch, **result})
    return records


def run_full_gate(
    repo: Path,
    revision: str,
    contract: Mapping[str, Any],
    *,
    offline: bool,
    full_test_timeout: float,
    keep_checkout: Path | None,
) -> dict[str, Any]:
    source = repository_root(repo)
    commit = resolve_commit(source, revision)
    started_at = _utc_now()
    fast = run_fast_gate(source, commit, contract)
    receipt: dict[str, Any] = {
        **fast,
        "mode": "full",
        "started_at": started_at,
        "commands": [],
        "generated_libraries": {},
        "runtime_smokes": [],
    }
    if not fast["passed"]:
        receipt["finished_at"] = _utc_now()
        return receipt

    temporary: tempfile.TemporaryDirectory[str] | None = None
    if keep_checkout is None:
        temporary = tempfile.TemporaryDirectory(prefix="character-director-release-")
        checkout = Path(temporary.name) / "checkout"
    else:
        checkout = keep_checkout.resolve()
        if checkout.exists():
            raise ValueError("--keep-checkout destination must not already exist")
        checkout.parent.mkdir(parents=True, exist_ok=True)
    try:
        clone = _command_receipt(
            "clone-selected-commit",
            ["git", "clone", "--no-hardlinks", "--no-checkout", str(source), str(checkout)],
            cwd=source,
            timeout=300.0,
        )
        receipt["commands"].append(clone)
        if not clone["passed"]:
            receipt["passed"] = False
            return receipt
        checkout_record = _command_receipt(
            "checkout-selected-commit",
            ["git", "checkout", "--detach", commit],
            cwd=checkout,
            timeout=120.0,
        )
        receipt["commands"].append(checkout_record)
        if not checkout_record["passed"]:
            receipt["passed"] = False
            return receipt
        initial_status = _git(checkout, ["status", "--porcelain=v1", "--untracked-files=all"])
        receipt["isolated_checkout"] = {
            "path": str(checkout),
            "commit": _git(checkout, ["rev-parse", "HEAD"]),
            "initially_clean": not initial_status,
        }
        if initial_status:
            receipt["issues"].append(
                GateIssue("checkout.dirty", "isolated checkout was not clean").as_dict()
            )
            receipt["passed"] = False
            return receipt

        ref_records = _prepare_remote_refs(
            source,
            checkout,
            [str(value) for value in contract.get("remote_refs", [])],
            offline=offline,
        )
        receipt["remote_refs"] = ref_records
        if not all(record.get("passed") for record in ref_records):
            receipt["passed"] = False
            return receipt

        uv = shutil.which("uv")
        if uv is None:
            receipt["issues"].append(
                GateIssue("tool.missing", "uv is required for full mode", "uv.lock").as_dict()
            )
            receipt["passed"] = False
            return receipt
        command_specs: list[tuple[str, list[str], float]] = [
            ("frozen-environment", [uv, "sync", "--frozen"], 900.0),
        ]
        for name, command, timeout in command_specs:
            record = _command_receipt(name, command, cwd=checkout, timeout=timeout)
            receipt["commands"].append(record)
            if not record["passed"]:
                receipt["passed"] = False
                return receipt

        python = checkout / ".venv" / "bin" / "python"
        import_probe = _command_receipt(
            "verifier-import-closure",
            [
                str(python),
                "-c",
                (
                    "import numpy; "
                    "import tools.analyze_user_capture_frames; "
                    "import tools.build_dragon_repair_review; "
                    "import tools.compose_kingfisher_pair_render; "
                    "import tools.import_robin_speech_alpha_library; "
                    "import tools.rebuild_kingfisher_legacy_pairs; "
                    "import tools.verify_kingfisher_pair_review"
                ),
            ],
            cwd=checkout,
            timeout=60.0,
        )
        receipt["commands"].append(import_probe)
        if not import_probe["passed"]:
            receipt["passed"] = False
            return receipt

        build_specs = [
            (
                "dragon-review-build",
                [str(python), "tools/build_dragon_repair_review.py"],
                checkout / "assets/reference/characters/dragon/compiled/repair-review",
            ),
            (
                "robin-speech-review-build",
                [str(python), "tools/import_robin_speech_alpha_library.py"],
                checkout / "assets/reference/characters/robin_speech/compiled",
            ),
            (
                "kingfisher-pair-review",
                [
                    str(python),
                    "tools/verify_kingfisher_pair_review.py",
                    "--index",
                    "assets/reference/characters/kingfisher/pair-review-compiled/library-index.json",
                    "--ledger",
                    "assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json",
                ],
                None,
            ),
        ]
        for name, command, output_root in build_specs:
            record = _command_receipt(name, command, cwd=checkout, timeout=1800.0)
            receipt["commands"].append(record)
            if output_root is not None and output_root.exists():
                receipt["generated_libraries"][name] = _sha256_tree(output_root)
            if not record["passed"]:
                receipt["passed"] = False
                return receipt

        test_specs = [
            (
                "release-gate-focused-tests",
                [str(python), "-m", "unittest", "tests.wizard.test_character_director_release_gate"],
                180.0,
            ),
            (
                "python-scope-boundary",
                [str(python), "tools/validate_python_scope.py", "."],
                180.0,
            ),
            (
                "complete-python-suite",
                [str(python), "-m", "unittest", "discover", "-s", "tests"],
                full_test_timeout,
            ),
        ]
        for name, command, timeout in test_specs:
            record = _command_receipt(name, command, cwd=checkout, timeout=timeout)
            receipt["commands"].append(record)
            if not record["passed"]:
                receipt["passed"] = False
                return receipt

        indexes: list[tuple[str, Path | None]] = [
            ("wizard-default", None),
            (
                "kingfisher-review",
                checkout / "assets/reference/characters/kingfisher/pair-review-compiled/library-index.json",
            ),
            (
                "dragon-review",
                checkout / "assets/reference/characters/dragon/compiled/repair-review/library-index.json",
            ),
            (
                "robin-review",
                checkout / "assets/reference/characters/robin_speech/compiled/robin/library-index.json",
            ),
            (
                "speech-review",
                checkout / "assets/reference/characters/robin_speech/compiled/speech/library-index.json",
            ),
        ]
        for name, index in indexes:
            smoke = _runtime_smoke(checkout, python, name=name, review_index=index)
            receipt["runtime_smokes"].append(smoke)
            if not smoke["passed"]:
                receipt["passed"] = False
                return receipt

        final_status = _git(checkout, ["status", "--porcelain=v1", "--untracked-files=all"])
        receipt["isolated_checkout"]["finally_clean"] = not final_status
        if final_status:
            receipt["issues"].append(
                GateIssue(
                    "checkout.generated_unignored_input",
                    "verification left unignored files in the isolated checkout",
                ).as_dict()
            )
            receipt["passed"] = False
        else:
            receipt["passed"] = True
        return receipt
    finally:
        receipt["finished_at"] = _utc_now()
        if temporary is not None:
            temporary.cleanup()


def _write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a Character Director release from an immutable Git commit."
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--mode", choices=("fast", "full"), default="full")
    parser.add_argument("--contract", type=Path, help="Schema-v1 fixture contract (fast mode is recommended).")
    parser.add_argument("--output", type=Path, help="Write the JSON receipt atomically to this path.")
    parser.add_argument("--offline", action="store_true", help="Do not fetch declared remote refs in full mode.")
    parser.add_argument("--full-test-timeout", type=float, default=3600.0)
    parser.add_argument(
        "--keep-checkout",
        type=Path,
        help="Keep the isolated full-mode checkout at a new path for diagnosis.",
    )
    args = parser.parse_args(argv)
    if args.mode == "fast" and args.keep_checkout is not None:
        parser.error("--keep-checkout is only valid in full mode")
    try:
        contract = load_contract(args.contract)
        if args.mode == "fast":
            receipt = run_fast_gate(args.repo, args.revision, contract)
        else:
            receipt = run_full_gate(
                args.repo,
                args.revision,
                contract,
                offline=args.offline,
                full_test_timeout=args.full_test_timeout,
                keep_checkout=args.keep_checkout,
            )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "gate": "character-director-release",
            "mode": args.mode,
            "passed": False,
            "issues": [GateIssue("gate.error", str(error)).as_dict()],
        }
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        _write_receipt(args.output, receipt)
    sys.stdout.write(payload)
    return 0 if receipt.get("passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
