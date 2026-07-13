#!/usr/bin/env python3
"""Validate the cartoon-animation program contract and compact evidence records."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
PROGRAM_RELATIVE = Path("docs/cartoon-animation-program")
REGISTRY_RELATIVE = PROGRAM_RELATIVE / "registry.json"
TRACKER_RELATIVE = PROGRAM_RELATIVE / "PROGRAM_TRACKER.md"
WORKFLOW_RELATIVE = PROGRAM_RELATIVE / "WORKFLOW.md"
EVIDENCE_SCHEMA_RELATIVE = (
    Path("wizard_avatar/definitions/cartoon_animation_evidence.schema.json")
)

CORE_ROLE_FILES = {
    "FPSE": (
        "research/01-first-principles-software.md",
        "planning/01-first-principles-plan.md",
    ),
    "ANIM": (
        "research/02-game-animation-motion.md",
        "planning/02-animation-plan.md",
    ),
    "RUST": (
        "research/03-rust-runtime.md",
        "planning/03-rust-plan.md",
    ),
    "PLAN": (
        "research/04-project-delivery.md",
        "planning/04-workflow-plan.md",
    ),
}

REQUIRED_PROGRAM_FILES = (
    "README.md",
    "IMPLEMENTATION_PLAN.md",
    "WORKFLOW.md",
    "PROGRAM_TRACKER.md",
    "registry.json",
)

LOCKED_HOTSPOTS = (
    "wizard_avatar/models.py",
    "wizard_avatar/controller.py",
    "wizard_avatar/frame_source.py",
    "wizard_avatar/server.py",
    "wizard_avatar/stream.py",
    "web/avatar/wizardClient.ts",
    "web/avatar/wizardControls.ts",
    "docs/cartoon-animation-program/PROGRAM_TRACKER.md",
    "docs/cartoon-animation-program/registry.json",
)

ACTIVE_CONTRACT_PATHS = (
    Path("README.md"),
    Path("CODEX_GOAL.md"),
    Path("docs/00-goal-and-visual-contract.md"),
    Path("docs/30-visual-tests.md"),
    Path("docs/37-completion-gate.md"),
)

NO_WINGS_PATTERNS = (
    re.compile(
        r"\b(?:character|wizard|avatar)\s+(?:has|must have|should have)\s+no\s+wings\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:must|should)\s+not\s+(?:have|include|render|show|use)\s+(?:visible\s+)?wings\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bwingless\b", re.IGNORECASE),
    re.compile(
        r"\bwings?\s+(?:are|is)\s+(?:forbidden|prohibited|not allowed)\b",
        re.IGNORECASE,
    ),
)

RUST_RULES = (
    (
        "scope.rust_path",
        re.compile(r"(?<![A-Za-z0-9_.-])rust/(?![A-Za-z0-9_.-]*ical)", re.IGNORECASE),
        "production file references the historical rust/ tree",
    ),
    (
        "scope.cargo_manifest",
        re.compile(r"\bCargo\.(?:toml|lock)\b", re.IGNORECASE),
        "production file references a Cargo manifest",
    ),
    (
        "scope.cargo_command",
        re.compile(
            r"\bcargo\s+(?:build|check|clippy|fmt|install|run|test)\b",
            re.IGNORECASE,
        ),
        "production file invokes Cargo",
    ),
    (
        "scope.rust_toolchain",
        re.compile(r"\b(?:rustc|rustup)\b", re.IGNORECASE),
        "production file invokes a Rust toolchain command",
    ),
    (
        "scope.rust_source",
        re.compile(r"(?:^|[\s\"'=(])[^\s\"']+\.rs\b", re.IGNORECASE),
        "production file references a Rust source file",
    ),
    (
        "scope.rust_port",
        re.compile(r"(?<![A-Fa-f0-9])878[78](?![A-Fa-f0-9])"),
        "production file references a retired Rust service port",
    ),
    (
        "scope.rust_binding",
        re.compile(
            r"\b(?:from|import)\s+(?:maturin|pyo3|rust(?:_extension|ext|lib))\b",
            re.IGNORECASE,
        ),
        "production Python imports a Rust binding",
    ),
)

SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
COMMIT_PATTERN = re.compile(r"^[a-f0-9]{40}$")
WORK_ITEM_PATTERN = re.compile(r"^CAP-[0-9]{3}$")
GATE_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]{0,15}$")
ROLE_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]{1,15}$")
AGENT_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
UTC_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


def _issue(code: str, path: str, message: str, **details: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {"code": code, "path": path, "message": message}
    if details:
        result["details"] = details
    return result


def _load_json(path: Path, errors: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(_issue("file.missing", _relative(path), "required JSON file is missing"))
        return None
    except (OSError, UnicodeError) as exc:
        errors.append(_issue("file.unreadable", _relative(path), str(exc)))
        return None
    except json.JSONDecodeError as exc:
        errors.append(
            _issue(
                "json.invalid",
                _relative(path),
                "invalid JSON",
                line=exc.lineno,
                column=exc.colno,
            )
        )
        return None
    if not isinstance(value, dict):
        errors.append(_issue("json.root_type", _relative(path), "JSON root must be an object"))
        return None
    return value


def _relative(path: Path, root: Optional[Path] = None) -> str:
    base = root or ROOT
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path)


def _safe_program_path(program_dir: Path, value: Any) -> Optional[Path]:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved_program = program_dir.resolve()
    resolved_candidate = (program_dir / candidate).resolve()
    try:
        resolved_candidate.relative_to(resolved_program)
    except ValueError:
        return None
    return resolved_candidate


def _read_text(path: Path, errors: List[Dict[str, Any]], root: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(_issue("file.missing", _relative(path, root), "required file is missing"))
    except (OSError, UnicodeError) as exc:
        errors.append(_issue("file.unreadable", _relative(path, root), str(exc)))
    return None


def _run_git(root: Path, arguments: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root)] + list(arguments),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _validate_program_identity(
    registry: Mapping[str, Any], errors: List[Dict[str, Any]]
) -> None:
    if registry.get("program_id") != "wizardjoe-cartoon-animation-2026-07-12":
        errors.append(
            _issue(
                "program.id",
                REGISTRY_RELATIVE.as_posix(),
                "unexpected or missing program_id",
            )
        )
    if registry.get("production_architecture") != "asciline_python":
        errors.append(
            _issue(
                "program.architecture",
                REGISTRY_RELATIVE.as_posix(),
                "production_architecture must be asciline_python",
            )
        )
    rust_policy = registry.get("rust_policy")
    if not isinstance(rust_policy, str) or "not_a_production_dependency" not in rust_policy:
        errors.append(
            _issue(
                "program.rust_policy",
                REGISTRY_RELATIVE.as_posix(),
                "rust_policy must explicitly exclude Rust from production",
            )
        )

    baseline = registry.get("baseline")
    if not isinstance(baseline, dict):
        errors.append(_issue("program.baseline", REGISTRY_RELATIVE.as_posix(), "baseline must be an object"))
        return
    url_value = baseline.get("python_url")
    parsed = urlparse(url_value) if isinstance(url_value, str) else None
    if (
        parsed is None
        or parsed.scheme not in {"http", "https"}
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.port != 8765
    ):
        errors.append(
            _issue(
                "program.python_url",
                REGISTRY_RELATIVE.as_posix(),
                "baseline.python_url must target the ASCILINE Python service on port 8765",
            )
        )
    if baseline.get("production_pose_count") != 39:
        errors.append(
            _issue(
                "program.pose_count",
                REGISTRY_RELATIVE.as_posix(),
                "baseline.production_pose_count must be 39",
            )
        )
    library_hash = baseline.get("generated_library_sha256")
    if not isinstance(library_hash, str) or not SHA256_PATTERN.fullmatch(library_hash):
        errors.append(
            _issue(
                "program.pose_hash",
                REGISTRY_RELATIVE.as_posix(),
                "baseline.generated_library_sha256 must be a lowercase SHA-256",
            )
        )


def _validate_outputs_and_ownership(
    root: Path,
    registry: Mapping[str, Any],
    errors: List[Dict[str, Any]],
) -> Dict[str, Any]:
    program_dir = root / PROGRAM_RELATIVE
    for filename in REQUIRED_PROGRAM_FILES:
        path = program_dir / filename
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(
                _issue(
                    "program.output_missing",
                    _relative(path, root),
                    "required integrated program file is missing or empty",
                )
            )

    roles = registry.get("roles")
    if not isinstance(roles, dict):
        errors.append(_issue("ownership.roles", REGISTRY_RELATIVE.as_posix(), "roles must be an object"))
        return {"role_count": 0, "document_count": 0, "document_owners": {}}

    document_owners: Dict[str, str] = {}
    agent_owners: Dict[str, str] = {}
    for role_id, role in sorted(roles.items()):
        role_path = "%s#/roles/%s" % (REGISTRY_RELATIVE.as_posix(), role_id)
        if not isinstance(role_id, str) or not ROLE_ID_PATTERN.fullmatch(role_id):
            errors.append(_issue("ownership.role_id", role_path, "invalid role ID"))
            continue
        if not isinstance(role, dict):
            errors.append(_issue("ownership.role_type", role_path, "role entry must be an object"))
            continue
        agent_id = role.get("agent_id")
        if not isinstance(agent_id, str) or not AGENT_ID_PATTERN.fullmatch(agent_id):
            errors.append(_issue("ownership.agent_id", role_path, "agent_id must be a UUID"))
        elif agent_id in agent_owners:
            errors.append(
                _issue(
                    "ownership.agent_overlap",
                    role_path,
                    "agent_id is assigned to multiple roles",
                    other_role=agent_owners[agent_id],
                )
            )
        else:
            agent_owners[agent_id] = role_id

        research_status = role.get("research_status")
        planning_status = role.get("planning_status")
        fields: List[Tuple[str, bool]] = [
            ("research_file", research_status == "complete"),
            ("planning_file", planning_status == "complete"),
        ]
        for field_name, required in fields:
            value = role.get(field_name)
            if not required and value is None:
                continue
            path = _safe_program_path(program_dir, value)
            if path is None:
                errors.append(
                    _issue(
                        "ownership.path",
                        role_path,
                        "%s must be a safe path inside the program directory" % field_name,
                    )
                )
                continue
            relative = path.relative_to(program_dir.resolve()).as_posix()
            expected_prefix = "research/" if field_name == "research_file" else "planning/"
            if not relative.startswith(expected_prefix):
                errors.append(
                    _issue(
                        "ownership.path_kind",
                        role_path,
                        "%s must be under %s" % (field_name, expected_prefix),
                    )
                )
            if relative in document_owners:
                errors.append(
                    _issue(
                        "ownership.document_overlap",
                        role_path,
                        "program output is assigned to multiple roles",
                        document=relative,
                        other_role=document_owners[relative],
                    )
                )
            else:
                document_owners[relative] = role_id
            if required and (not path.is_file() or path.stat().st_size == 0):
                errors.append(
                    _issue(
                        "program.role_output_missing",
                        _relative(path, root),
                        "registered %s output is missing or empty" % field_name,
                        role=role_id,
                    )
                )

    for role_id, expected_paths in CORE_ROLE_FILES.items():
        role = roles.get(role_id)
        if not isinstance(role, dict):
            errors.append(
                _issue(
                    "program.core_role_missing",
                    REGISTRY_RELATIVE.as_posix(),
                    "required core role is missing",
                    role=role_id,
                )
            )
            continue
        for field_name, expected in zip(("research_file", "planning_file"), expected_paths):
            if role.get(field_name) != expected:
                errors.append(
                    _issue(
                        "program.core_output_registration",
                        "%s#/roles/%s" % (REGISTRY_RELATIVE.as_posix(), role_id),
                        "%s must register %s" % (field_name, expected),
                    )
                )

    workflow_path = root / WORKFLOW_RELATIVE
    workflow = _read_text(workflow_path, errors, root)
    locked_present: List[str] = []
    if workflow is not None:
        for hotspot in LOCKED_HOTSPOTS:
            if hotspot not in workflow:
                errors.append(
                    _issue(
                        "ownership.hotspot_missing",
                        WORKFLOW_RELATIVE.as_posix(),
                        "coordinator-locked hotspot is not declared",
                        hotspot=hotspot,
                    )
                )
            else:
                locked_present.append(hotspot)

    return {
        "role_count": len(roles),
        "document_count": len(document_owners),
        "document_owners": document_owners,
        "locked_hotspots": locked_present,
    }


def _validate_checkpoint(
    root: Path,
    registry: Mapping[str, Any],
    tracker: Optional[str],
    errors: List[Dict[str, Any]],
    verify_git: bool,
) -> Dict[str, Any]:
    checkpoint = registry.get("planning_checkpoint")
    if not isinstance(checkpoint, dict):
        errors.append(
            _issue(
                "checkpoint.metadata",
                REGISTRY_RELATIVE.as_posix(),
                "planning_checkpoint must be an object",
            )
        )
        return {"commit": None, "pushed": False, "git_verified": False}

    commit = checkpoint.get("commit")
    pushed = checkpoint.get("pushed")
    if pushed is not True:
        errors.append(
            _issue(
                "checkpoint.not_pushed",
                REGISTRY_RELATIVE.as_posix(),
                "planning_checkpoint.pushed must be true before implementation",
            )
        )
    if not isinstance(commit, str) or not COMMIT_PATTERN.fullmatch(commit):
        errors.append(
            _issue(
                "checkpoint.commit",
                REGISTRY_RELATIVE.as_posix(),
                "planning_checkpoint.commit must be a full lowercase 40-character Git SHA",
            )
        )
        commit = None

    if tracker is not None and commit is not None:
        if "| Planning checkpoint | COMPLETE |" not in tracker or commit not in tracker:
            errors.append(
                _issue(
                    "checkpoint.tracker_mismatch",
                    TRACKER_RELATIVE.as_posix(),
                    "tracker must mark the same planning checkpoint COMPLETE",
                )
            )

    git_verified = False
    remote_ref: Optional[str] = None
    if verify_git and commit is not None:
        if _run_git(root, ["rev-parse", "--is-inside-work-tree"]).returncode != 0:
            errors.append(_issue("checkpoint.git_repository", ".", "root is not a Git worktree"))
        elif _run_git(root, ["cat-file", "-e", "%s^{commit}" % commit]).returncode != 0:
            errors.append(
                _issue(
                    "checkpoint.commit_missing",
                    REGISTRY_RELATIVE.as_posix(),
                    "recorded planning checkpoint is not available locally",
                    commit=commit,
                )
            )
        elif _run_git(root, ["merge-base", "--is-ancestor", commit, "HEAD"]).returncode != 0:
            errors.append(
                _issue(
                    "checkpoint.not_ancestor",
                    REGISTRY_RELATIVE.as_posix(),
                    "recorded planning checkpoint is not an ancestor of HEAD",
                    commit=commit,
                )
            )
        else:
            baseline = registry.get("baseline")
            branch = baseline.get("branch") if isinstance(baseline, dict) else None
            if not isinstance(branch, str) or not branch:
                errors.append(
                    _issue(
                        "checkpoint.branch",
                        REGISTRY_RELATIVE.as_posix(),
                        "baseline.branch is required for remote checkpoint verification",
                    )
                )
            else:
                remote_ref = "refs/remotes/origin/%s" % branch
                ref_exists = _run_git(root, ["show-ref", "--verify", "--quiet", remote_ref])
                if ref_exists.returncode != 0:
                    errors.append(
                        _issue(
                            "checkpoint.remote_ref_missing",
                            REGISTRY_RELATIVE.as_posix(),
                            "remote-tracking branch is unavailable; fetch origin before validation",
                            remote_ref=remote_ref,
                        )
                    )
                elif _run_git(root, ["merge-base", "--is-ancestor", commit, remote_ref]).returncode != 0:
                    errors.append(
                        _issue(
                            "checkpoint.remote_missing_commit",
                            REGISTRY_RELATIVE.as_posix(),
                            "remote-tracking branch does not contain the planning checkpoint",
                            commit=commit,
                            remote_ref=remote_ref,
                        )
                    )
                else:
                    git_verified = True

    return {
        "commit": commit,
        "pushed": pushed is True,
        "git_verified": git_verified,
        "remote_ref": remote_ref,
    }


def _validate_wing_contract(root: Path, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    checked: List[str] = []
    for relative in ACTIVE_CONTRACT_PATHS:
        path = root / relative
        text = _read_text(path, errors, root)
        if text is None:
            continue
        checked.append(relative.as_posix())
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in NO_WINGS_PATTERNS:
                if pattern.search(line):
                    errors.append(
                        _issue(
                            "contract.no_wings",
                            relative.as_posix(),
                            "active contract contradicts the accepted winged/flying design",
                            line=line_number,
                            excerpt=line.strip()[:240],
                        )
                    )
                    break
    return {"checked_paths": checked, "contract": "winged_flying_required"}


def _production_scan_paths(root: Path) -> Iterable[Path]:
    exact = (
        Path("pyproject.toml"),
        Path("requirements.txt"),
        Path("uv.lock"),
        Path("README.md"),
        Path("CODEX_GOAL.md"),
    )
    seen: Set[Path] = set()
    for relative in exact:
        path = root / relative
        if path.is_file():
            seen.add(path.resolve())
            yield path

    roots_and_suffixes = (
        (Path(".github"), {".json", ".yaml", ".yml"}),
        (Path("wizard_avatar"), {".json", ".py"}),
        (Path("web/avatar"), {".html", ".js", ".json", ".mjs", ".ts"}),
        (Path("tools"), {".py"}),
    )
    this_script = Path(__file__).resolve()
    for relative_root, suffixes in roots_and_suffixes:
        directory = root / relative_root
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            resolved = path.resolve()
            if (
                path.is_file()
                and path.suffix.lower() in suffixes
                and resolved not in seen
                and resolved != this_script
                and path.name != "validate_python_scope.py"
                and "__pycache__" not in path.parts
            ):
                seen.add(resolved)
                yield path


def _validate_python_scope(root: Path, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    checked: List[str] = []
    violation_count = 0
    for path in _production_scan_paths(root):
        relative = _relative(path, root)
        checked.append(relative)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(_issue("scope.unreadable", relative, str(exc)))
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for code, pattern, message in RUST_RULES:
                if pattern.search(line):
                    violation_count += 1
                    errors.append(
                        _issue(
                            code,
                            relative,
                            message,
                            line=line_number,
                            excerpt=line.strip()[:240],
                        )
                    )
    return {
        "checked_paths": checked,
        "checked_path_count": len(checked),
        "violation_count": violation_count,
        "excluded_historical_paths": [
            "rust/",
            "evidence/wizard/rust-*/",
            "docs/cartoon-animation-program/research/",
            "docs/cartoon-animation-program/planning/",
        ],
    }


def validate_evidence_record(record: Any) -> List[Dict[str, Any]]:
    """Validate semantic constraints for one compact evidence record.

    JSON Schema remains the interchange contract. These checks cover relational
    constraints that JSON Schema cannot express clearly without a runtime
    dependency, including command/result agreement and Git retention policy.
    """

    errors: List[Dict[str, Any]] = []
    if not isinstance(record, dict):
        return [_issue("evidence.root_type", "$", "evidence root must be an object")]

    required = (
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
    )
    for field in required:
        if field not in record:
            errors.append(_issue("evidence.required", "$/%s" % field, "required field is missing"))

    if record.get("schema_version") != 1:
        errors.append(_issue("evidence.schema_version", "$/schema_version", "must equal 1"))
    if record.get("program_id") != "wizardjoe-cartoon-animation-2026-07-12":
        errors.append(_issue("evidence.program_id", "$/program_id", "unexpected program ID"))
    if not isinstance(record.get("gate_id"), str) or not GATE_PATTERN.fullmatch(record["gate_id"]):
        errors.append(_issue("evidence.gate_id", "$/gate_id", "invalid gate ID"))
    if not isinstance(record.get("work_item_id"), str) or not WORK_ITEM_PATTERN.fullmatch(
        record["work_item_id"]
    ):
        errors.append(_issue("evidence.work_item_id", "$/work_item_id", "invalid work item ID"))
    if record.get("result") not in {"passed", "failed", "blocked"}:
        errors.append(_issue("evidence.result", "$/result", "invalid result"))
    if not isinstance(record.get("generated_at"), str) or not UTC_TIMESTAMP_PATTERN.fullmatch(
        record["generated_at"]
    ):
        errors.append(_issue("evidence.generated_at", "$/generated_at", "must be a UTC timestamp ending in Z"))
    tested_commit = record.get("tested_commit")
    if not isinstance(tested_commit, str) or not COMMIT_PATTERN.fullmatch(tested_commit):
        errors.append(_issue("evidence.tested_commit", "$/tested_commit", "must be a full Git SHA"))

    production = record.get("production")
    if not isinstance(production, dict):
        errors.append(_issue("evidence.production", "$/production", "must be an object"))
    else:
        if production.get("architecture") != "asciline_python":
            errors.append(_issue("evidence.architecture", "$/production/architecture", "must be asciline_python"))
        if production.get("port") != 8765:
            errors.append(_issue("evidence.port", "$/production/port", "must equal 8765"))

    checkpoint = record.get("planning_checkpoint")
    if not isinstance(checkpoint, dict):
        errors.append(_issue("evidence.checkpoint", "$/planning_checkpoint", "must be an object"))
    else:
        checkpoint_commit = checkpoint.get("commit")
        if not isinstance(checkpoint_commit, str) or not COMMIT_PATTERN.fullmatch(checkpoint_commit):
            errors.append(_issue("evidence.checkpoint_commit", "$/planning_checkpoint/commit", "must be a full Git SHA"))
        if checkpoint.get("pushed") is not True:
            errors.append(_issue("evidence.checkpoint_pushed", "$/planning_checkpoint/pushed", "must be true"))

    commands = record.get("commands")
    if not isinstance(commands, list) or not commands:
        errors.append(_issue("evidence.commands", "$/commands", "must contain at least one command result"))
    else:
        for index, command in enumerate(commands):
            path = "$/commands/%d" % index
            if not isinstance(command, dict):
                errors.append(_issue("evidence.command_type", path, "command result must be an object"))
                continue
            if not isinstance(command.get("command"), str) or not command["command"].strip():
                errors.append(_issue("evidence.command", path + "/command", "command must not be empty"))
            exit_code = command.get("exit_code")
            if isinstance(exit_code, bool) or not isinstance(exit_code, int):
                errors.append(_issue("evidence.exit_code", path + "/exit_code", "exit_code must be an integer"))
            outcome = command.get("result")
            if outcome not in {"passed", "failed"}:
                errors.append(_issue("evidence.command_result", path + "/result", "must be passed or failed"))
            elif isinstance(exit_code, int) and not isinstance(exit_code, bool):
                if (exit_code == 0) != (outcome == "passed"):
                    errors.append(_issue("evidence.command_exit_mismatch", path, "exit_code and result disagree"))
            duration_ms = command.get("duration_ms")
            if (
                isinstance(duration_ms, bool)
                or not isinstance(duration_ms, (int, float))
                or duration_ms < 0
            ):
                errors.append(_issue("evidence.duration", path + "/duration_ms", "duration_ms must be non-negative"))

    artifacts = record.get("artifacts")
    seen_artifacts: Set[str] = set()
    if not isinstance(artifacts, list):
        errors.append(_issue("evidence.artifacts", "$/artifacts", "must be an array"))
    else:
        for index, artifact in enumerate(artifacts):
            path = "$/artifacts/%d" % index
            if not isinstance(artifact, dict):
                errors.append(_issue("evidence.artifact_type", path, "artifact must be an object"))
                continue
            artifact_path = artifact.get("path")
            if not _is_safe_relative_path(artifact_path):
                errors.append(_issue("evidence.artifact_path", path + "/path", "path must be repository-relative and traversal-free"))
            elif artifact_path in seen_artifacts:
                errors.append(_issue("evidence.artifact_duplicate", path + "/path", "artifact path is duplicated"))
            else:
                seen_artifacts.add(artifact_path)
            digest = artifact.get("sha256")
            if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
                errors.append(_issue("evidence.artifact_hash", path + "/sha256", "invalid SHA-256"))
            size = artifact.get("bytes")
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                errors.append(_issue("evidence.artifact_bytes", path + "/bytes", "bytes must be a non-negative integer"))
            storage = artifact.get("storage")
            if storage not in {"git", "workflow_artifact"}:
                errors.append(_issue("evidence.artifact_storage", path + "/storage", "invalid storage tier"))
            if storage == "git" and isinstance(size, int) and size > 5 * 1024 * 1024:
                errors.append(_issue("evidence.git_artifact_size", path, "Git evidence must not exceed 5 MiB"))
            retention = artifact.get("retention_days")
            if isinstance(retention, bool) or not isinstance(retention, int) or retention < 1:
                errors.append(_issue("evidence.retention", path + "/retention_days", "retention_days must be a positive integer"))
            if storage == "git" and isinstance(artifact_path, str) and Path(artifact_path).suffix.lower() in {
                ".mp4",
                ".ndjson",
                ".rgb",
            }:
                errors.append(_issue("evidence.raw_in_git", path, "raw evidence must use workflow_artifact storage"))

    changed_paths = record.get("changed_paths")
    if not isinstance(changed_paths, list):
        errors.append(_issue("evidence.changed_paths", "$/changed_paths", "must be an array"))
    else:
        for index, value in enumerate(changed_paths):
            if not _is_safe_relative_path(value):
                errors.append(_issue("evidence.changed_path", "$/changed_paths/%d" % index, "invalid repository-relative path"))
            elif value == "rust" or value.startswith("rust/"):
                errors.append(_issue("evidence.rust_path", "$/changed_paths/%d" % index, "Rust paths cannot be production evidence"))

    risks = record.get("risks")
    if not isinstance(risks, list) or any(not isinstance(value, str) for value in risks):
        errors.append(_issue("evidence.risks", "$/risks", "risks must be an array of strings"))

    if record.get("result") == "passed" and isinstance(commands, list):
        if any(isinstance(command, dict) and command.get("result") != "passed" for command in commands):
            errors.append(_issue("evidence.pass_with_failure", "$/result", "passed evidence cannot contain a failed command"))
    return errors


def _is_safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def validate_program(root: Path = ROOT, verify_git: bool = True) -> Dict[str, Any]:
    root = Path(root).resolve()
    errors: List[Dict[str, Any]] = []
    registry_path = root / REGISTRY_RELATIVE
    registry = _load_json(registry_path, errors)
    tracker = _read_text(root / TRACKER_RELATIVE, errors, root)

    ownership: Dict[str, Any] = {
        "role_count": 0,
        "document_count": 0,
        "document_owners": {},
        "locked_hotspots": [],
    }
    checkpoint: Dict[str, Any] = {
        "commit": None,
        "pushed": False,
        "git_verified": False,
        "remote_ref": None,
    }
    if registry is not None:
        _validate_program_identity(registry, errors)
        ownership = _validate_outputs_and_ownership(root, registry, errors)
        checkpoint = _validate_checkpoint(root, registry, tracker, errors, verify_git)

    wing_contract = _validate_wing_contract(root, errors)
    python_scope = _validate_python_scope(root, errors)
    if not (root / EVIDENCE_SCHEMA_RELATIVE).is_file():
        errors.append(
            _issue(
                "evidence.schema_missing",
                EVIDENCE_SCHEMA_RELATIVE.as_posix(),
                "compact evidence schema is missing",
            )
        )

    return {
        "schema_version": 1,
        "program_id": registry.get("program_id") if registry is not None else None,
        "result": "passed" if not errors else "failed",
        "root": str(root),
        "planning_checkpoint": checkpoint,
        "ownership": ownership,
        "wing_contract": wing_contract,
        "python_production_scope": python_scope,
        "errors": errors,
        "summary": {
            "error_count": len(errors),
            "role_count": ownership["role_count"],
            "checked_production_path_count": python_scope["checked_path_count"],
        },
    }


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            target.write(payload)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--json", type=Path, dest="json_path", help="write the report atomically")
    parser.add_argument(
        "--evidence",
        action="append",
        default=[],
        type=Path,
        help="also validate a compact evidence JSON record; may be repeated",
    )
    parser.add_argument(
        "--skip-git-checks",
        action="store_true",
        help="skip local/remote Git ancestry checks (intended for isolated fixtures only)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    report = validate_program(args.root, verify_git=not args.skip_git_checks)
    evidence_reports: List[Dict[str, Any]] = []
    for evidence_path in args.evidence:
        try:
            record = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence_errors = validate_evidence_record(record)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            evidence_errors = [_issue("evidence.unreadable", str(evidence_path), str(exc))]
        evidence_reports.append(
            {
                "path": str(evidence_path),
                "result": "passed" if not evidence_errors else "failed",
                "errors": evidence_errors,
            }
        )
        report["errors"].extend(evidence_errors)
    if evidence_reports:
        report["evidence_records"] = evidence_reports
        report["result"] = "passed" if not report["errors"] else "failed"
        report["summary"]["error_count"] = len(report["errors"])

    if args.json_path is not None:
        output_path = args.json_path
        if not output_path.is_absolute():
            output_path = args.root / output_path
        _atomic_write_json(output_path, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
