import tempfile
import unittest
from pathlib import Path

from tools.validate_python_scope import find_rust_violations, validate_python_scope


class PythonScopeValidationTests(unittest.TestCase):
    def make_root(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / "wizard_avatar").mkdir()
        (root / "web" / "avatar").mkdir(parents=True)
        return temporary, root

    def test_clean_production_scope_passes_and_rust_side_track_is_ignored(self):
        temporary, root = self.make_root()
        self.addCleanup(temporary.cleanup)
        (root / "wizard_avatar" / "clean.py").write_text(
            "import json\nsubsystem = 'rust is not a production dependency'\n",
            encoding="utf-8",
        )
        (root / "web" / "avatar" / "clean.ts").write_text(
            "// Rust is historical only.\nexport const runtime = 'python';\n",
            encoding="utf-8",
        )
        (root / "rust").mkdir()
        (root / "rust" / "main.py").write_text("import rust_extension\n", encoding="utf-8")

        self.assertEqual(find_rust_violations(root), ())
        self.assertTrue(validate_python_scope(root)["ok"])

    def test_python_rust_imports_and_process_invocations_are_reported(self):
        temporary, root = self.make_root()
        self.addCleanup(temporary.cleanup)
        (root / "wizard_avatar" / "binding.py").write_text(
            "import rust_renderer\nfrom pyo3 import bridge\nfrom . import rust_extension\n",
            encoding="utf-8",
        )
        (root / "wizard_avatar" / "runner.py").write_text(
            "import subprocess as sp\nsp.run(['cargo', 'run'])\nsp.run(['python', '-m', 'maturin'])\n",
            encoding="utf-8",
        )

        violations = find_rust_violations(root)
        codes = [item.code for item in violations]

        self.assertEqual(codes.count("python.rust_import"), 3)
        self.assertEqual(codes.count("python.rust_invocation"), 2)
        self.assertTrue(all(not Path(item.path).is_absolute() for item in violations))

    def test_web_rust_import_and_command_invocation_are_reported(self):
        temporary, root = self.make_root()
        self.addCleanup(temporary.cleanup)
        (root / "web" / "avatar" / "binding.ts").write_text(
            'import init from "../../rust/pkg/avatar.js";\n'
            'const command = new Deno.Command("rustc", {args: ["--version"]});\n',
            encoding="utf-8",
        )

        codes = [item.code for item in find_rust_violations(root)]

        self.assertIn("web.rust_import", codes)
        self.assertIn("web.rust_invocation", codes)

    def test_python_syntax_error_prevents_a_false_proof(self):
        temporary, root = self.make_root()
        self.addCleanup(temporary.cleanup)
        (root / "wizard_avatar" / "broken.py").write_text("def broken(:\n", encoding="utf-8")

        violations = find_rust_violations(root)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "python.syntax_error")
        result = validate_python_scope(root)
        self.assertFalse(result["ok"])
        self.assertEqual(result["violation_count"], 1)


if __name__ == "__main__":
    unittest.main()
