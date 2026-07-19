import unittest

from wizard_avatar.pose_compositor import author_cast_staff_graph
from wizard_avatar.reference_avatar import render_reference_pose_local


class CastStaffGraphTests(unittest.TestCase):
    def test_authored_cast_staff_is_deterministic_and_preserves_grip(self):
        first = render_reference_pose_local("front_idle")
        second = render_reference_pose_local("front_idle")
        original = first.copy()

        kwargs = {
            "source_staff_tip": (58, 12),
            "source_staff_hand": (56, 50),
            "root_anchor": (36, 95),
            "target_staff_tip": (52, 17),
            "target_staff_hand": (56, 50),
        }
        author_cast_staff_graph(first, **kwargs)
        author_cast_staff_graph(second, **kwargs)

        self.assertEqual(first.cells, second.cells)
        self.assertNotEqual(first.cells, original.cells)
        preserved_skin = 0
        for y in range(45, 56):
            for x in range(51, 62):
                if first.get(x, y) == original.get(x, y) and first.get(x, y) is not None:
                    red, green, blue = first.get(x, y).rgb
                    if red >= 145 and red > green * 1.08 and green > blue * 1.05:
                        preserved_skin += 1
        self.assertGreater(preserved_skin, 0)

    def test_cast_staff_rejects_collapsed_geometry(self):
        canvas = render_reference_pose_local("front_idle")

        with self.assertRaisesRegex(ValueError, "must be distinct"):
            author_cast_staff_graph(
                canvas,
                source_staff_tip=(58, 12),
                source_staff_hand=(56, 50),
                root_anchor=(36, 95),
                target_staff_tip=(56, 50),
                target_staff_hand=(56, 50),
            )


if __name__ == "__main__":
    unittest.main()
