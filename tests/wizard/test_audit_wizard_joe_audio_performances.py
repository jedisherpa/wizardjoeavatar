import unittest

from tools.audit_wizard_joe_audio_performances import _motion_quality


def _performance(pose_ids, *, spacing_ms=1600):
    return {
        "approach": {
            "mode": "walk_toward_camera",
            "pose_ids": ["246_camera_approach"],
            "arrival_pose_ids": ["247_camera_intimate_hold"],
        },
        "body_transition_ms": 160,
        "body_cues": [
            {
                "crossfade_ms": 160,
            }
        ],
        "motion_beats": [
            {
                "time_ms": index * spacing_ms,
                "pose_id": pose_id,
            }
            for index, pose_id in enumerate(pose_ids)
        ],
    }


class WizardJoeAudioPerformanceAuditTests(unittest.TestCase):
    def test_quality_gate_accepts_spaced_nonrepeating_motion(self):
        report = _motion_quality(
            _performance(["one", "two", "three", "four", "five"]),
            9000,
        )

        self.assertEqual(report["issues"], [])

    def test_quality_gate_rejects_short_window_return_and_false_walk_loop(self):
        performance = _performance(
            ["one", "two", "three", "one"],
            spacing_ms=1000,
        )
        performance["approach"]["pose_ids"] = [
            "246_camera_approach",
            "248_camera_retreat",
        ]

        report = _motion_quality(performance, 5000)

        self.assertIn("motion_beats_too_close", report["issues"])
        self.assertIn("short_window_pose_repetition", report["issues"])
        self.assertIn("incoherent_camera_approach", report["issues"])

    def test_quality_gate_rejects_hold_hidden_by_long_approach(self):
        performance = _performance(
            ["one", "two"],
            spacing_ms=5000,
        )
        performance["approach"]["end_ms"] = 4200

        report = _motion_quality(performance, 14_000)

        self.assertIn("projected_pose_hold_too_long", report["issues"])


if __name__ == "__main__":
    unittest.main()
