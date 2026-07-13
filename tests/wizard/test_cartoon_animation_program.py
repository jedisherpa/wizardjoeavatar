import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_cartoon_animation_program import validate_program


ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = "08d8f3aaa181d97ef3d2a29cb5a8362d81a05f12"
LIBRARY_HASH = "1200e2891902cd1f3147d2c2d298dd2d99313708fbc8e90034376500e1843037"


class CartoonAnimationProgramTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.fixture_root = Path(self.temporary_directory.name)
        self._write_valid_fixture()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write(self, relative, text="fixture\n"):
        path = self.fixture_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _registry(self):
        return {
            "program_id": "wizardjoe-cartoon-animation-2026-07-12",
            "baseline": {
                "branch": "codex/build-repeatable-avatar-animation",
                "python_url": "http://127.0.0.1:8765/",
                "production_pose_count": 89,
                "generated_library_sha256": LIBRARY_HASH,
            },
            "production_architecture": "asciline_python",
            "rust_policy": "historical_side_track_not_a_production_dependency_or_gate",
            "phase": "implementation_wave_1",
            "planning_checkpoint": {"commit": CHECKPOINT, "pushed": True},
            "implementation_checkpoint": {"commit": None, "pushed": False},
            "roles": {
                "FPSE": {
                    "agent_id": "11111111-1111-4111-8111-111111111111",
                    "research_status": "complete",
                    "planning_status": "complete",
                    "research_file": "research/01-first-principles-software.md",
                    "planning_file": "planning/01-first-principles-plan.md",
                },
                "ANIM": {
                    "agent_id": "22222222-2222-4222-8222-222222222222",
                    "research_status": "complete",
                    "planning_status": "complete",
                    "research_file": "research/02-game-animation-motion.md",
                    "planning_file": "planning/02-animation-plan.md",
                },
                "RUST": {
                    "agent_id": "33333333-3333-4333-8333-333333333333",
                    "research_status": "complete",
                    "planning_status": "complete",
                    "research_file": "research/03-rust-runtime.md",
                    "planning_file": "planning/03-rust-plan.md",
                },
                "PLAN": {
                    "agent_id": "44444444-4444-4444-8444-444444444444",
                    "research_status": "complete",
                    "planning_status": "complete",
                    "research_file": "research/04-project-delivery.md",
                    "planning_file": "planning/04-workflow-plan.md",
                },
            },
        }

    def _write_registry(self, registry):
        self._write(
            "docs/cartoon-animation-program/registry.json",
            json.dumps(registry, indent=2) + "\n",
        )

    def _write_valid_fixture(self):
        registry = self._registry()
        self._write_registry(registry)
        for filename in (
            "README.md",
            "IMPLEMENTATION_PLAN.md",
            "PROGRAM_TRACKER.md",
            "WORKFLOW.md",
        ):
            self._write("docs/cartoon-animation-program/" + filename)
        tracker = (
            "| Phase | Status | Gate |\n"
            "|---|---|---|\n"
            "| Planning checkpoint | COMPLETE | pushed as `%s` |\n" % CHECKPOINT
        )
        self._write("docs/cartoon-animation-program/PROGRAM_TRACKER.md", tracker)
        workflow = "\n".join(
            (
                "# Workflow",
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
        )
        self._write("docs/cartoon-animation-program/WORKFLOW.md", workflow + "\n")
        for role in registry["roles"].values():
            self._write("docs/cartoon-animation-program/" + role["research_file"])
            self._write("docs/cartoon-animation-program/" + role["planning_file"])

        self._write("README.md", "Rainbow wings are required.\n")
        self._write("CODEX_GOAL.md", "Build the winged Python avatar.\n")
        self._write("docs/00-goal-and-visual-contract.md", "Keep the rainbow wings.\n")
        self._write("docs/30-visual-tests.md", "Test stable wing attachment.\n")
        self._write("docs/37-completion-gate.md", "Winged flight must pass.\n")
        self._write("pyproject.toml", "[project]\nname = \"fixture\"\n")
        self._write("wizard_avatar/runtime.py", "PORT = 8765\n")
        self._write(
            "wizard_avatar/definitions/cartoon_animation_evidence.schema.json",
            "{}\n",
        )

    def _codes(self, report):
        return {error["code"] for error in report["errors"]}

    def test_current_repository_program_contract_passes(self):
        report = validate_program(ROOT, verify_git=True)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["result"], "passed")
        self.assertTrue(report["planning_checkpoint"]["git_verified"])
        self.assertEqual(report["planning_checkpoint"]["commit"], CHECKPOINT)

    def test_valid_isolated_fixture_passes_without_git_checks(self):
        report = validate_program(self.fixture_root, verify_git=False)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["ownership"]["role_count"], 4)
        self.assertEqual(report["ownership"]["document_count"], 8)

    def test_missing_registered_report_fails(self):
        path = self.fixture_root / "docs/cartoon-animation-program/research/02-game-animation-motion.md"
        path.unlink()
        report = validate_program(self.fixture_root, verify_git=False)
        self.assertIn("program.role_output_missing", self._codes(report))

    def test_unpushed_planning_checkpoint_fails(self):
        registry = self._registry()
        registry["planning_checkpoint"] = {"commit": CHECKPOINT, "pushed": False}
        self._write_registry(registry)
        report = validate_program(self.fixture_root, verify_git=False)
        self.assertIn("checkpoint.not_pushed", self._codes(report))

    def test_active_no_wings_contract_fails_but_historical_files_are_not_scanned(self):
        self._write(
            "docs/cartoon-animation-program/research/history.md",
            "The old character has no wings.\n",
        )
        passing = validate_program(self.fixture_root, verify_git=False)
        self.assertNotIn("contract.no_wings", self._codes(passing))

        self._write("docs/37-completion-gate.md", "The character must have no wings.\n")
        failing = validate_program(self.fixture_root, verify_git=False)
        self.assertIn("contract.no_wings", self._codes(failing))

    def test_rust_production_dependency_path_fails_with_precise_rule(self):
        self._write(
            "wizard_avatar/runtime.py",
            "RUNTIME = \"rust/server/Cargo.toml\"\nPORT = 8787\n",
        )
        report = validate_program(self.fixture_root, verify_git=False)
        codes = self._codes(report)
        self.assertIn("scope.rust_path", codes)
        self.assertIn("scope.cargo_manifest", codes)
        self.assertIn("scope.rust_port", codes)

    def test_duplicate_document_ownership_fails(self):
        registry = self._registry()
        registry["roles"]["ANIM"]["planning_file"] = registry["roles"]["FPSE"][
            "planning_file"
        ]
        self._write_registry(registry)
        report = validate_program(self.fixture_root, verify_git=False)
        self.assertIn("ownership.document_overlap", self._codes(report))


if __name__ == "__main__":
    unittest.main()
