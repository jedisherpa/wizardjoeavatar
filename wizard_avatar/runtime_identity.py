from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence


RUNTIME_IDENTITY_SCHEMA = "wizard_runtime_identity_v1"
RUNTIME_IDENTITY_SCHEMA_VERSION = 1


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_argv(argv: Sequence[str]) -> list[str]:
    safe: list[str] = []
    redact_next = False
    for raw in argv:
        value = str(raw)
        lowered = value.lower()
        if redact_next:
            safe.append("[REDACTED]")
            redact_next = False
            continue
        if any(word in lowered for word in ("token", "secret", "password", "api-key", "apikey")):
            if "=" in value:
                safe.append(value.split("=", 1)[0] + "=[REDACTED]")
            else:
                safe.append(value)
                redact_next = True
            continue
        safe.append(value)
    return safe


def _git_identity(root: Path) -> Dict[str, Any]:
    def run(*args: str) -> bytes:
        completed = subprocess.run(
            ("git", *args),
            cwd=str(root),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return completed.stdout

    try:
        head = run("rev-parse", "HEAD").decode("ascii").strip()
        tree = run("rev-parse", "{}^{{tree}}".format(head)).decode("ascii").strip()
        branch = run("branch", "--show-current").decode("utf-8").strip()
        status = run("status", "--porcelain=v1", "--untracked-files=all")
        tracked_diff = run("diff", "--binary", "HEAD")
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
        return {
            "available": False,
            "head": None,
            "head_tree": None,
            "branch": None,
            "worktree_clean": False,
            "status_sha256": None,
            "tracked_diff_sha256": None,
            "status_lines": [],
        }
    return {
        "available": True,
        "head": head,
        "head_tree": tree,
        "branch": branch,
        "worktree_clean": not status,
        "status_sha256": hashlib.sha256(status).hexdigest(),
        "tracked_diff_sha256": hashlib.sha256(tracked_diff).hexdigest(),
        "status_lines": status.decode("utf-8", errors="replace").splitlines(),
    }


@lru_cache(maxsize=8)
def _static_runtime_facts(root_text: str) -> Dict[str, Any]:
    executable = Path(sys.executable).resolve()
    return {
        "python_executable": str(executable),
        "python_executable_sha256": (
            _sha256_file(executable) if executable.is_file() else None
        ),
    }


def build_runtime_identity(
    root: Path,
    *,
    render_config: Mapping[str, Any],
    server_config: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build immutable, non-secret startup identity for evidence binding."""

    root = root.resolve()
    static = _static_runtime_facts(str(root))
    launcher = Path(sys.argv[0]).expanduser()
    if not launcher.is_absolute():
        launcher = (Path.cwd() / launcher).resolve()
    safe_argv = _safe_argv(sys.argv)
    launcher_sha256 = _sha256_file(launcher) if launcher.is_file() else None
    started_at_utc = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )
    return {
        "schema": RUNTIME_IDENTITY_SCHEMA,
        "schema_version": RUNTIME_IDENTITY_SCHEMA_VERSION,
        "runtime_epoch": "wizard-runtime-{}".format(uuid.uuid4().hex),
        "pid": os.getpid(),
        "started_at_utc": started_at_utc,
        "started_at_monotonic_ns": time.monotonic_ns(),
        "working_directory": str(Path.cwd().resolve()),
        "repository_root": str(root),
        "git": _git_identity(root),
        "python": {
            "executable": static["python_executable"],
            "executable_sha256": static["python_executable_sha256"],
            "version": sys.version.splitlines()[0],
        },
        "launch": {
            "argv": safe_argv,
            "argv_sha256": hashlib.sha256(
                "\0".join(safe_argv).encode("utf-8")
            ).hexdigest(),
            "launcher": str(launcher),
            "launcher_sha256": launcher_sha256,
        },
        "server": dict(server_config or {}),
        "render": dict(render_config),
    }


def refresh_runtime_identity(
    identity: Mapping[str, Any],
    root: Path,
) -> Dict[str, Any]:
    """Refresh mutable source provenance while preserving process identity."""

    refreshed = dict(identity)
    refreshed["git"] = _git_identity(root.resolve())
    return refreshed
