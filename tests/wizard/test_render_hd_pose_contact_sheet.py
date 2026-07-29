from __future__ import annotations

import unittest

from tools.render_hd_pose_contact_sheet import pose_number, select_pose_ids


class RenderHDPoseContactSheetTests(unittest.TestCase):
    def test_pose_number_supports_legacy_and_structured_ids(self) -> None:
        self.assertEqual(pose_number("067_pose-name"), 67)
        self.assertEqual(pose_number("kingfisher.act.110.warm-resolution"), 110)
        self.assertEqual(pose_number("dragon-act-086-hover"), 86)
        self.assertIsNone(pose_number("kingfisher-neutral"))

    def test_numeric_range_selects_structured_pose_ids(self) -> None:
        pose_ids = [
            "kingfisher.act.066.select-a-control",
            "kingfisher.act.067.center-mark-resting-beak",
            "kingfisher.act.110.warm-resolution-speaking-beak",
            "kingfisher.act.111.future-pose",
        ]

        self.assertEqual(
            select_pose_ids(pose_ids, prefixes=[], start=67, end=110),
            pose_ids[1:3],
        )


if __name__ == "__main__":
    unittest.main()
