import unittest
from dataclasses import replace

from wizard_avatar.animation_trace import StagePointV1
from wizard_avatar.contact_verifier import verify_contact_trace
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand


class ContactVerifierTests(unittest.TestCase):
    def _walk_trace(self):
        source = ProceduralWizardFrameSource()
        result = source.apply_command_sync(
            WizardCommand("move", {"x": 3.5, "z": 5.0})
        )
        self.assertTrue(result.ok, result.message)
        records = []
        for _ in range(48):
            source.advance_simulation(1 / source.fps)
            candidate = source.render_captured_candidate_sync(
                source.capture_render_state()
            )
            source.commit_render_candidate(candidate)
            records.append(candidate.animation_truth)
        return records

    def test_contact_locked_walk_has_zero_planted_drift(self):
        report = verify_contact_trace(self._walk_trace())

        self.assertTrue(report.passed, report.to_mapping())
        self.assertGreater(report.stance_count, 2)
        self.assertGreater(report.contact_frame_count, 8)
        self.assertLessEqual(report.maximum_planted_drift_cells, 1e-6)
        self.assertLessEqual(report.maximum_root_residual_cells, 1e-6)

    def test_verifier_rejects_synthetic_two_cell_drift(self):
        records = self._walk_trace()
        first_by_generation = {}
        changed = None
        for index, record in enumerate(records):
            if record.planted_anchor_stage is None:
                continue
            if record.contact_generation in first_by_generation:
                changed = index
                break
            first_by_generation[record.contact_generation] = index
        self.assertIsNotNone(changed)
        record = records[changed]
        records[changed] = replace(
            record,
            planted_anchor_stage=StagePointV1(
                record.planted_anchor_stage.x + 2.0,
                record.planted_anchor_stage.y,
            ),
        )

        report = verify_contact_trace(records)

        self.assertFalse(report.passed)
        self.assertIn("planted_anchor_drift", {issue.code for issue in report.issues})


if __name__ == "__main__":
    unittest.main()
