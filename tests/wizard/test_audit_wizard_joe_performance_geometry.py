from __future__ import annotations

import unittest

from tools.audit_wizard_joe_performance_geometry import (
    projected_pose_sequence,
    transition_geometry,
)


class WizardJoePerformanceGeometryAuditTests(unittest.TestCase):
    def test_projected_sequence_ignores_beats_hidden_by_full_clip_approach(self) -> None:
        performance = {
            "_duration_ms": 10_000,
            "approach": {
                "end_ms": 10_000,
                "pose_ids": ["flight_down", "flight_up"],
                "arrival_pose_ids": ["flight_hover"],
            },
            "motion_beats": [
                {"time_ms": 0, "pose_id": "hidden_one"},
                {"time_ms": 4_000, "pose_id": "hidden_two"},
            ],
        }

        self.assertEqual(
            projected_pose_sequence(performance),
            ["flight_down", "flight_up", "flight_hover"],
        )

    def test_projected_sequence_starts_at_beat_active_after_approach(self) -> None:
        performance = {
            "_duration_ms": 10_000,
            "approach": {
                "end_ms": 4_200,
                "pose_ids": ["camera_approach"],
                "arrival_pose_ids": ["camera_hold"],
            },
            "motion_beats": [
                {"time_ms": 0, "pose_id": "hidden_one"},
                {"time_ms": 3_000, "pose_id": "active_at_arrival"},
                {"time_ms": 6_000, "pose_id": "later"},
            ],
        }

        self.assertEqual(
            projected_pose_sequence(performance),
            ["camera_approach", "camera_hold", "active_at_arrival", "later"],
        )

    def test_transition_geometry_flags_large_discontinuities(self) -> None:
        source = {
            "width": 100,
            "height": 200,
            "center_x": 100,
            "center_y": 100,
            "baseline_y": 200,
        }
        target = {
            "width": 200,
            "height": 100,
            "center_x": 250,
            "center_y": 250,
            "baseline_y": 300,
        }

        result = transition_geometry("source", "target", source, target)

        self.assertEqual(
            result["issues"],
            [
                "center_shift_outlier",
                "dimension_change_outlier",
            ],
        )

    def test_authored_flight_transition_allows_deliberate_shape_change(self) -> None:
        source = {
            "width": 100,
            "height": 200,
            "center_x": 100,
            "center_y": 100,
            "baseline_y": 200,
        }
        target = {
            "width": 160,
            "height": 200,
            "center_x": 105,
            "center_y": 100,
            "baseline_y": 200,
        }

        result = transition_geometry(
            "175_flight_recoverystroke_up",
            "184_flight_accelerate",
            source,
            target,
        )

        self.assertEqual(result["issues"], [])
        self.assertTrue(result["intentional_dynamic_transition"])


if __name__ == "__main__":
    unittest.main()
