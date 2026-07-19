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
    reference_pose_presentation_scale,
    reference_pose_root_anchor,
    render_reference_avatar_local,
    render_reference_pose_local,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "assets" / "reference" / "motion_sources" / "manifest.json"
GRAPH_PATH = (
    ROOT
    / "wizard_avatar"
    / "definitions"
    / "reference_avatar_animation_graph_v2.json"
)


class ReferenceAvatarPoseLibraryTests(unittest.TestCase):
    def test_pose_library_loads_expected_pose_ids(self):
        self.assertTrue(reference_pose_library_available())
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        expected_pose_ids = {pose["id"] for pose in manifest["poses"]}
        self.assertEqual(set(reference_pose_ids()), expected_pose_ids)
        self.assertEqual(len(expected_pose_ids), 123)
        self.assertTrue(
            {
                "front_greeting_wave_wings",
                "front_magic_staff_spark_wings",
                "feeling_joy_full",
                "feeling_love_close",
                "cast_front_00",
                "cast_front_31",
            }.issubset(expected_pose_ids)
        )

    def test_cast_frames_are_baked_atomic_pixel_graphs_with_continuous_anchors(self):
        poses = [get_reference_pose(f"cast_front_{frame:02d}") for frame in range(32)]
        front_idle = get_reference_pose("front_idle")

        self.assertTrue(
            all(pose.description.startswith("authored cast frame") for pose in poses)
        )
        self.assertEqual({pose.root_anchor for pose in poses}, {(36, 95)})
        self.assertEqual({pose.anchors["staff_hand"] for pose in poses}, {(56, 50)})
        self.assertEqual(front_idle.anchors["staff_hand"], poses[0].anchors["staff_hand"])
        self.assertEqual(front_idle.anchors["staff_tip"], poses[0].anchors["staff_tip"])
        self.assertEqual(front_idle.anchors["staff_tip"], poses[-1].anchors["staff_tip"])
        front_cells = {(cell.x, cell.y, cell.rgb) for cell in front_idle.cells}
        self.assertEqual(
            {(cell.x, cell.y, cell.rgb) for cell in poses[0].cells},
            front_cells,
        )
        self.assertEqual(
            {(cell.x, cell.y, cell.rgb) for cell in poses[-1].cells},
            front_cells,
        )
        for previous, current in zip(poses, poses[1:]):
            tip_a = previous.anchors["staff_tip"]
            tip_b = current.anchors["staff_tip"]
            self.assertLessEqual(abs(tip_b[0] - tip_a[0]), 2)
            self.assertLessEqual(abs(tip_b[1] - tip_a[1]), 2)

        library = json.loads(
            (
                ROOT
                / "wizard_avatar"
                / "definitions"
                / "reference_avatar_pose_cells.json"
            ).read_text(encoding="utf-8")
        )
        cast_payloads = {
            pose["id"]: pose
            for pose in library["poses"]
            if pose["id"].startswith("cast_front_")
        }
        stable_body = None
        for frame in range(32):
            payload = cast_payloads[f"cast_front_{frame:02d}"]
            self.assertTrue(payload["source"].startswith("derived_cast_rig:"))
            body = {
                (cell["x"], cell["y"], tuple(cell["rgb"]), cell.get("region", ""))
                for cell in payload["cells"]
                if cell["x"] < 35
            }
            if stable_body is None:
                stable_body = body
            else:
                self.assertEqual(body, stable_body)

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

    def test_wide_cast_poses_preserve_authored_subject_density(self):
        self.assertEqual(
            get_reference_pose("front_staff_guard_windup").presentation_scale,
            (96, 78),
        )
        self.assertAlmostEqual(
            reference_pose_presentation_scale("front_staff_block_horizontal"),
            96 / 75,
        )
        self.assertAlmostEqual(
            reference_pose_presentation_scale("front_magic_staff_thrust"),
            96 / 73,
        )
        self.assertEqual(reference_pose_presentation_scale("front_idle"), 1.0)

    def test_walk_transition_poses_are_crisp_endpoint_pixel_graphs(self):
        library = json.loads(
            (
                ROOT
                / "wizard_avatar"
                / "definitions"
                / "reference_avatar_pose_cells.json"
            ).read_text(encoding="utf-8")
        )
        poses = {pose["id"]: pose for pose in library["poses"]}
        endpoints = {
            pose_id: poses[pose_id]
            for pose_id in ("walk_front_left", "walk_front_right")
        }
        endpoint_cells = {
            pose_id: {
                (cell["x"], cell["y"]): (
                    tuple(cell["rgb"]),
                    cell.get("region", ""),
                )
                for cell in pose["cells"]
            }
            for pose_id, pose in endpoints.items()
        }
        for pose_id in ("walk_front_left_to_right", "walk_front_right_to_left"):
            with self.subTest(pose_id=pose_id):
                pose = poses[pose_id]
                self.assertTrue(pose["source"].startswith("derived:"))
                self.assertEqual(pose["root_anchor"], [36, 95])
                for cell in pose["cells"]:
                    pixel = (tuple(cell["rgb"]), cell.get("region", ""))
                    coordinate = (cell["x"], cell["y"])
                    self.assertIn(
                        pixel,
                        {
                            cells.get(coordinate)
                            for cells in endpoint_cells.values()
                        },
                    )
                target_pose_id = (
                    "walk_front_right"
                    if pose_id == "walk_front_left_to_right"
                    else "walk_front_left"
                )
                target = {
                    (cell["x"], cell["y"]): tuple(cell["rgb"])
                    for cell in poses[target_pose_id]["cells"]
                    if cell["x"] >= 56
                }
                derived = {
                    (cell["x"], cell["y"]): tuple(cell["rgb"])
                    for cell in pose["cells"]
                    if cell["x"] >= 56
                }
                self.assertEqual(derived, target)

    def test_front_walk_clip_contains_no_idle_reset(self):
        graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
        samples = graph["clips"]["walk_front"]["samples"]
        self.assertEqual(
            [sample["pose_id"] for sample in samples],
            [
                "walk_front_left",
                "walk_front_left_to_right",
                "walk_front_right",
                "walk_front_right_to_left",
            ],
        )
        self.assertNotIn("front_idle", {sample["pose_id"] for sample in samples})

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
