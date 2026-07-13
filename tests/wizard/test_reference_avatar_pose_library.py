import json
import unittest
from pathlib import Path

from wizard_avatar.compositor import CellCanvas
from wizard_avatar.reference_avatar import (
    REFERENCE_FRONT_IDLE_POSE_ID,
    get_reference_pose,
    reference_pose_anchor,
    reference_pose_ids,
    reference_pose_library_available,
    reference_pose_root_anchor,
    render_reference_avatar_local,
    render_reference_pose_local,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "assets" / "reference" / "motion_sources" / "manifest.json"


class ReferenceAvatarPoseLibraryTests(unittest.TestCase):
    def test_pose_library_loads_expected_pose_ids(self):
        self.assertTrue(reference_pose_library_available())
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        expected_pose_ids = {pose["id"] for pose in manifest["poses"]}
        self.assertEqual(set(reference_pose_ids()), expected_pose_ids)

    def test_all_reference_poses_share_canonical_canvas_and_root(self):
        for pose_id in reference_pose_ids():
            with self.subTest(pose_id=pose_id):
                pose = get_reference_pose(pose_id)
                self.assertEqual((pose.cols, pose.rows), (72, 96))
                self.assertEqual(pose.root_anchor, (36, 95))
                self.assertEqual(pose.anchors["root"], (36, 95))
                for anchor in pose.anchors.values():
                    self.assertGreaterEqual(anchor[0], 0)
                    self.assertLess(anchor[0], pose.cols)
                    self.assertGreaterEqual(anchor[1], 0)
                    self.assertLess(anchor[1], pose.rows)

    def test_airborne_dash_uses_explicit_fit_and_anchors(self):
        pose = get_reference_pose("run_front_airborne_reach")
        self.assertEqual(pose.root_anchor, (36, 95))
        self.assertEqual(pose.anchors["mouth"], (42, 31))
        self.assertEqual(pose.anchors["left_eye"], (38, 22))
        self.assertEqual(pose.anchors["right_eye"], (45, 22))

    def test_get_reference_pose_exposes_dimensions_and_root(self):
        pose = get_reference_pose("front_idle")
        self.assertEqual(pose.pose_id, "front_idle")
        self.assertEqual(pose.cols, 72)
        self.assertEqual(pose.rows, 96)
        self.assertEqual(reference_pose_root_anchor("front_idle"), pose.root_anchor)
        self.assertEqual(reference_pose_anchor("front_idle", "mouth"), pose.anchors["mouth"])
        self.assertEqual(len(pose.root_anchor), 2)
        self.assertIn("mouth", pose.anchors)
        self.assertIn("left_eye", pose.anchors)
        self.assertIn("right_eye", pose.anchors)
        self.assertGreater(len(pose.cells), 1000)

    def test_render_reference_pose_returns_canvas_copy(self):
        first = render_reference_pose_local("front_idle")
        second = render_reference_pose_local("front_idle")
        self.assertIsInstance(first, CellCanvas)
        self.assertIsInstance(second, CellCanvas)
        self.assertIsNot(first, second)
        self.assertEqual((first.width, first.height), (second.width, second.height))
        x, y = next(
            (x, y)
            for y, row in enumerate(second.cells)
            for x, cell in enumerate(row)
            if cell is not None
        )
        first.clear_cell(x, y)
        self.assertIsNotNone(second.get(x, y))

    def test_legacy_reference_avatar_uses_front_idle_pose(self):
        legacy = render_reference_avatar_local()
        front_idle = render_reference_pose_local(REFERENCE_FRONT_IDLE_POSE_ID)
        self.assertEqual((legacy.width, legacy.height), (front_idle.width, front_idle.height))


if __name__ == "__main__":
    unittest.main()
