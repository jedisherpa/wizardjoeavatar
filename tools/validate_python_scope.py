#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parent.parent
PYTHON_ROOT = "wizard_avatar"
WEB_ROOT = "web"
WEB_SUFFIXES = frozenset({".html", ".js", ".jsx", ".mjs", ".ts", ".tsx"})
RUST_MODULES = frozenset({"maturin", "pyo3", "rust", "rustext", "setuptools_rust"})
RUST_COMMANDS = frozenset({"cargo", "cbindgen", "maturin", "rustc", "rustup", "wasm-bindgen"})
PROCESS_CALLS = frozenset(
    {
        "asyncio.create_subprocess_exec",
        "asyncio.create_subprocess_shell",
        "os.popen",
        "os.spawnl",
        "os.spawnlp",
        "os.spawnv",
        "os.spawnvp",
        "os.system",
        "subprocess.Popen",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.run",
    }
)

WEB_IMPORT_RE = re.compile(
    r"(?m)^\s*(?:import(?:[\s\S]*?\sfrom\s*)?|export[\s\S]*?\sfrom\s*)"
    r"[\"']([^\"']+)[\"']|\b(?:import|require)\s*\(\s*[\"']([^\"']+)[\"']\s*\)"
)
WEB_COMMAND_RE = re.compile(
    r"\b(?:Deno\.Command|Bun\.spawn(?:Sync)?|child_process\."
    r"(?:exec|execFile|spawn)(?:Sync)?)\s*\(\s*[\"']([^\"']+)[\"']"
)


@dataclass(frozen=True)
class ScopeViolation:
    code: str
    path: str
    line: int
    column: int
    message: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _is_rust_module(module: str) -> bool:
    normalized = module.lower().replace("-", "_")
    components = tuple(part for part in normalized.split(".") if part)
    return any(
        component in RUST_MODULES
        or component.startswith("rust_")
        or component.endswith("_rust")
        for component in components
    )


def _command_name(value: str) -> str:
    token = value.strip().split()[0] if value.strip() else ""
    return Path(token).name.lower()


def _contains_rust_command(values: Iterable[str]) -> bool:
    return any(_command_name(value) in RUST_COMMANDS for value in values)


def _literal_command(node: ast.AST) -> Tuple[str, ...]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (node.value,)
    if isinstance(node, (ast.List, ast.Tuple)):
        values = []
        for item in node.elts:
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                values.append(item.value)
            else:
                break
        return tuple(values)
    return ()


def _qualified_name(node: ast.AST) -> Optional[str]:
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


class _PythonRustVisitor(ast.NodeVisitor):
    def __init__(self, relative_path: str) -> None:
        self.relative_path = relative_path
        self.aliases: Dict[str, str] = {}
        self.violations: List[ScopeViolation] = []

    def _add(self, node: ast.AST, code: str, message: str) -> None:
        self.violations.append(
            ScopeViolation(
                code=code,
                path=self.relative_path,
                line=getattr(node, "lineno", 1),
                column=getattr(node, "col_offset", 0) + 1,
                message=message,
            )
        )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".")[0]
            self.aliases[local_name] = alias.name
            if _is_rust_module(alias.name):
                self._add(node, "python.rust_import", "production Python imports a Rust module")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        rust_import = _is_rust_module(module)
        for alias in node.names:
            local_name = alias.asname or alias.name
            qualified = "{}.{}".format(module, alias.name) if module else alias.name
            self.aliases[local_name] = qualified
            rust_import = rust_import or _is_rust_module(qualified)
        if rust_import:
            self._add(node, "python.rust_import", "production Python imports a Rust module")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        qualified = _qualified_name(node.func)
        if qualified:
            first, separator, remainder = qualified.partition(".")
            resolved = self.aliases.get(first, first)
            if separator:
                resolved = "{}.{}".format(resolved, remainder)
            if resolved in PROCESS_CALLS:
                command_node = node.args[0] if node.args else None
                if command_node is None:
                    for keyword in node.keywords:
                        if keyword.arg in {"args", "cmd", "command"}:
                            command_node = keyword.value
                            break
                if command_node is not None and _contains_rust_command(
                    _literal_command(command_node)
                ):
                    self._add(
                        node,
                        "python.rust_invocation",
                        "production Python invokes a Rust toolchain command",
                    )
        self.generic_visit(node)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _scan_python(path: Path, root: Path) -> Tuple[ScopeViolation, ...]:
    relative = _relative(path, root)
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return (
            ScopeViolation(
                "python.read_error", relative, 1, 1, "cannot read production Python: {}".format(exc)
            ),
        )
    try:
        tree = ast.parse(source, filename=relative)
    except SyntaxError as exc:
        return (
            ScopeViolation(
                "python.syntax_error",
                relative,
                exc.lineno or 1,
                exc.offset or 1,
                "cannot prove Python scope because the file does not parse",
            ),
        )
    visitor = _PythonRustVisitor(relative)
    visitor.visit(tree)
    return tuple(visitor.violations)


def _is_rust_web_specifier(specifier: str) -> bool:
    normalized = specifier.lower().replace("\\", "/")
    components = tuple(part for part in normalized.split("/") if part not in {"", ".", ".."})
    return any(
        part in {"maturin", "pyo3", "rust", "rustext", "setuptools-rust"}
        or part.startswith("rust-")
        or part.startswith("rust_")
        for part in components
    )


def _line_column(source: str, index: int) -> Tuple[int, int]:
    line = source.count("\n", 0, index) + 1
    prior_newline = source.rfind("\n", 0, index)
    column = index + 1 if prior_newline < 0 else index - prior_newline
    return line, column


def _scan_web(path: Path, root: Path) -> Tuple[ScopeViolation, ...]:
    relative = _relative(path, root)
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return (
            ScopeViolation("web.read_error", relative, 1, 1, "cannot read web source: {}".format(exc)),
        )
    violations = []
    for match in WEB_IMPORT_RE.finditer(source):
        specifier = match.group(1) or match.group(2) or ""
        if _is_rust_web_specifier(specifier):
            line, column = _line_column(source, match.start())
            violations.append(
                ScopeViolation(
                    "web.rust_import",
                    relative,
                    line,
                    column,
                    "production web source imports a Rust artifact",
                )
            )
    for match in WEB_COMMAND_RE.finditer(source):
        if _contains_rust_command((match.group(1),)):
            line, column = _line_column(source, match.start())
            violations.append(
                ScopeViolation(
                    "web.rust_invocation",
                    relative,
                    line,
                    column,
                    "production web source invokes a Rust toolchain command",
                )
            )
    return tuple(violations)


def _production_files(root: Path) -> Tuple[Path, ...]:
    files = []
    python_root = root / PYTHON_ROOT
    if python_root.is_dir():
        files.extend(path for path in python_root.rglob("*.py") if "__pycache__" not in path.parts)
    web_root = root / WEB_ROOT
    if web_root.is_dir():
        files.extend(
            path
            for path in web_root.rglob("*")
            if path.is_file() and path.suffix.lower() in WEB_SUFFIXES
        )
    return tuple(sorted(files, key=lambda path: _relative(path, root)))


def find_rust_violations(root: Path = ROOT) -> Tuple[ScopeViolation, ...]:
    repository_root = Path(root).resolve()
    violations = []
    for path in _production_files(repository_root):
        if path.suffix.lower() == ".py":
            violations.extend(_scan_python(path, repository_root))
        else:
            violations.extend(_scan_web(path, repository_root))
    return tuple(
        sorted(
            violations,
            key=lambda item: (item.path, item.line, item.column, item.code),
        )
    )


def validate_python_scope(root: Path = ROOT) -> Dict[str, object]:
    repository_root = Path(root).resolve()
    files = _production_files(repository_root)
    violations = find_rust_violations(repository_root)
    return {
        "ok": not violations,
        "root": str(repository_root),
        "scanned_file_count": len(files),
        "violation_count": len(violations),
        "violations": [item.to_dict() for item in violations],
    }


validate = validate_python_scope


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prove production Python and web sources do not import or invoke Rust."
    )
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    arguments = parser.parse_args(argv)
    result = validate_python_scope(arguments.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
