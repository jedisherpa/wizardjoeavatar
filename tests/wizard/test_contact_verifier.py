import unittest
from dataclasses import replace

from wizard_avatar.animation_trace import RasterSpanV1, StagePointV1
from wizard_avatar.contact_verifier import (
    DecodedRasterFrameV1,
    verify_contact_trace,
)
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.floor import build_background
from wizard_avatar.models import WizardCommand
from wizard_avatar.palette import RGB


class ContactVerifierTests(unittest.TestCase):
    def _walk_evidence(self):
        source = ProceduralWizardFrameSource()
        result = source.apply_command_sync(
            WizardCommand("move", {"x": 3.5, "z": 5.0})
        )
        self.assertTrue(result.ok, result.message)
        records = []
        frames = {}
        for _ in range(48):
            source.advance_simulation(1 / source.fps)
            candidate = source.render_captured_candidate_sync(
                source.capture_render_state()
            )
            source.commit_render_candidate(candidate)
            records.append(candidate.animation_truth)
            frames[candidate.frame.frame_index] = DecodedRasterFrameV1(
                cols=candidate.frame.cols,
                rows=candidate.frame.rows,
                cells=candidate.frame.cells,
            )
        return records, frames

    def _walk_trace(self):
        return self._walk_evidence()[0]

    @staticmethod
    def _issue_codes(report):
        return {issue.code for issue in report.issues}

    @staticmethod
    def _second_frame_in_stance(records):
        first_by_generation = {}
        for index, record in enumerate(records):
            if record.planted_anchor_stage is None:
                continue
            if record.contact_generation in first_by_generation:
                return index
            first_by_generation[record.contact_generation] = index
        return None

    @staticmethod
    def _blank_span(frame, span):
        cells = bytearray(frame.cells)
        background = build_background(frame.cols, frame.rows).to_frame_bytes()
        for y in range(span.min_y, span.max_y + 1):
            for x in range(span.min_x, span.max_x + 1):
                offset = (y * frame.cols + x) * 4
                cells[offset : offset + 4] = background[offset : offset + 4]
        return replace(frame, cells=bytes(cells))

    @staticmethod
    def _color_span(frame, span):
        cells = bytearray(frame.cells)
        offset = (span.min_y * frame.cols + span.min_x) * 4
        cells[offset : offset + 4] = bytes((35, *RGB["brown_dark"]))
        return replace(frame, cells=bytes(cells))

    def _add_visible_planted_cells(self, records, frames):
        for record in records:
            if record.animation_root_policy != "contact_locked":
                continue
            span = record.planted_anchor_raster_span
            if span is None or record.frame_index not in frames:
                continue
            frames[record.frame_index] = self._color_span(
                frames[record.frame_index],
                span,
            )

    def test_contact_locked_walk_has_zero_planted_drift(self):
        report = verify_contact_trace(self._walk_trace())

        self.assertTrue(report.passed, report.to_mapping())
        self.assertGreater(report.stance_count, 2)
        self.assertGreater(report.contact_frame_count, 8)
        self.assertLessEqual(report.maximum_planted_drift_cells, 1e-6)
        self.assertLessEqual(report.maximum_root_residual_cells, 1e-6)

    def test_strict_raster_evidence_accepts_visible_planted_cells(self):
        records, frames = self._walk_evidence()
        sample = next(iter(frames.values()))
        raw_frames = {
            frame_index: frame.cells
            for frame_index, frame in frames.items()
        }

        report = verify_contact_trace(
            records,
            decoded_frames=raw_frames,
            raster_size=(sample.cols, sample.rows),
            strict_raster_evidence=True,
        )

        self.assertTrue(report.passed, report.to_mapping())
        self.assertGreater(report.contact_frame_count, 8)
        self.assertLessEqual(
            report.maximum_planted_raster_span_drift_cells,
            1.0,
        )

    def test_both_foot_action_stance_does_not_break_locomotion_alternation(self):
        records = self._walk_trace()
        locomotion_stances = []
        seen = set()
        for record in records:
            if record.support_contact not in {"left_foot", "right_foot"}:
                continue
            if record.contact_generation in seen:
                continue
            seen.add(record.contact_generation)
            locomotion_stances.append(record)
        self.assertGreaterEqual(len(locomotion_stances), 2)
        first, second = locomotion_stances[:2]
        action = replace(
            first,
            frame_index=first.frame_index + 1,
            contact_generation=first.contact_generation + 1,
            animation_clip_id="cast_front",
            support_contact="both_feet",
            planted_anchor="staff_tip",
        )
        second = replace(
            second,
            frame_index=first.frame_index + 2,
            contact_generation=first.contact_generation + 2,
        )

        report = verify_contact_trace((first, action, second))

        self.assertTrue(report.passed, report.to_mapping())

    def test_verifier_rejects_synthetic_two_cell_drift(self):
        records = self._walk_trace()
        changed = self._second_frame_in_stance(records)
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
        self.assertIn("planted_anchor_drift", self._issue_codes(report))

    def test_fixed_root_support_does_not_claim_contact_lock(self):
        record = next(
            item
            for item in self._walk_trace()
            if item.planted_anchor_stage is not None
        )
        released = replace(
            record,
            frame_index=record.frame_index + 1,
            animation_root_policy="fixed",
            planted_anchor_stage=StagePointV1(
                record.planted_anchor_stage.x + 4.0,
                record.planted_anchor_stage.y,
            ),
        )

        report = verify_contact_trace((record, released))

        self.assertTrue(report.passed, report.to_mapping())

    def test_verifier_rejects_two_cell_raster_span_drift(self):
        records, frames = self._walk_evidence()
        self._add_visible_planted_cells(records, frames)
        changed = self._second_frame_in_stance(records)
        self.assertIsNotNone(changed)
        record = records[changed]
        span = record.planted_anchor_raster_span
        self.assertIsNotNone(span)
        records[changed] = replace(
            record,
            planted_anchor_raster_span=RasterSpanV1(
                min_x=span.min_x + 2,
                max_x=span.max_x + 2,
                min_y=span.min_y,
                max_y=span.max_y,
            ),
        )

        report = verify_contact_trace(records, decoded_frames=frames)

        self.assertFalse(report.passed)
        self.assertIn("planted_raster_span_drift", self._issue_codes(report))

    def test_strict_verifier_rejects_missing_planted_raster_span(self):
        records, frames = self._walk_evidence()
        self._add_visible_planted_cells(records, frames)
        changed = next(
            index
            for index, record in enumerate(records)
            if record.animation_root_policy == "contact_locked"
            and record.support_contact != "none"
        )
        records[changed] = replace(
            records[changed],
            planted_anchor_raster_span=None,
        )

        report = verify_contact_trace(
            records,
            decoded_frames=frames,
            strict_raster_evidence=True,
        )

        self.assertFalse(report.passed)
        self.assertIn("missing_planted_raster_span", self._issue_codes(report))

    def test_strict_verifier_rejects_missing_decoded_frame(self):
        records, frames = self._walk_evidence()
        self._add_visible_planted_cells(records, frames)
        missing = next(
            record.frame_index
            for record in records
            if record.animation_root_policy == "contact_locked"
            and record.support_contact != "none"
        )
        del frames[missing]

        report = verify_contact_trace(
            records,
            decoded_frames=frames,
            strict_raster_evidence=True,
        )

        self.assertFalse(report.passed)
        self.assertIn("missing_decoded_raster_frame", self._issue_codes(report))

    def test_verifier_rejects_blank_planted_raster_span(self):
        records, frames = self._walk_evidence()
        self._add_visible_planted_cells(records, frames)
        target = next(
            record
            for record in records
            if record.animation_root_policy == "contact_locked"
            and record.planted_anchor_raster_span is not None
        )
        frames[target.frame_index] = self._blank_span(
            frames[target.frame_index],
            target.planted_anchor_raster_span,
        )

        report = verify_contact_trace(records, decoded_frames=frames)

        self.assertFalse(report.passed)
        self.assertIn("blank_planted_raster_span", self._issue_codes(report))

    def test_verifier_rejects_repeated_single_foot_locomotion_stance(self):
        records = self._walk_trace()
        stance_supports = []
        for record in records:
            if record.support_contact not in {"left_foot", "right_foot"}:
                continue
            if any(record.contact_generation == item[0] for item in stance_supports):
                continue
            stance_supports.append(
                (record.contact_generation, record.support_contact)
            )
        self.assertGreaterEqual(len(stance_supports), 2)
        first_support = stance_supports[0][1]
        repeated_generation = stance_supports[1][0]
        for index, record in enumerate(records):
            if record.contact_generation != repeated_generation:
                continue
            records[index] = replace(
                record,
                support_contact=first_support,
                planted_anchor=first_support,
            )

        report = verify_contact_trace(records)

        self.assertFalse(report.passed)
        self.assertIn(
            "locomotion_support_not_alternating",
            self._issue_codes(report),
        )


if __name__ == "__main__":
    unittest.main()
