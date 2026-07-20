import unittest

from wizard_avatar.pose_compositor import authored_staff_cells, author_cast_staff_graph
from wizard_avatar.reference_avatar import (
    reference_pose_anchor,
    reference_pose_root_anchor,
    render_reference_pose_local,
)


class CastStaffGraphTests(unittest.TestCase):
    def test_authored_cast_staff_is_deterministic_and_preserves_grip(self):
        first = render_reference_pose_local("front_idle")
        second = render_reference_pose_local("front_idle")
        original = first.copy()

        kwargs = {
            "source_staff_tip": (58, 12),
            "source_staff_hand": (56, 50),
            "root_anchor": (36, 95),
            "target_staff_tip": (64, 19),
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
        source_staff = authored_staff_cells(original, (58, 12), (56, 50), (36, 95))
        target_staff = authored_staff_cells(first, (64, 19), (56, 50), (36, 95))
        self.assertTrue({cell.rgb for cell in target_staff.values()}.issubset(
            {cell.rgb for cell in source_staff.values()}
        ))
        self.assertGreaterEqual(len(target_staff), int(len(source_staff) * 0.85))
        self.assertLessEqual(len(target_staff), int(len(source_staff) * 1.20))

    def test_neutral_target_preserves_exact_staff_and_character_graph(self):
        canvas = render_reference_pose_local("front_idle")
        original = canvas.copy()

        author_cast_staff_graph(
            canvas,
            source_staff_tip=(58, 12),
            source_staff_hand=(56, 50),
            root_anchor=(36, 95),
            target_staff_tip=(58, 12),
            target_staff_hand=(56, 50),
        )

        self.assertEqual(
            [[None if cell is None else cell.to_bytes() for cell in row] for row in canvas.cells],
            [[None if cell is None else cell.to_bytes() for cell in row] for row in original.cells],
        )

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

    def test_stop_inbetweens_keep_staff_as_one_vertical_raster(self):
        for family in (
            "stop_front_from_left",
            "stop_front_from_right",
            "stop_front_from_left_passing",
            "stop_front_from_right_passing",
        ):
            for amount in (625, 75, 875):
                pose_id = f"{family}_{amount}"
                with self.subTest(pose_id=pose_id):
                    canvas = render_reference_pose_local(pose_id)
                    staff = authored_staff_cells(
                        canvas,
                        reference_pose_anchor(pose_id, "staff_tip"),
                        reference_pose_anchor(pose_id, "staff_hand"),
                        reference_pose_root_anchor(pose_id),
                    )
                    rows = sorted({y for _x, y in staff})
                    self.assertGreaterEqual(len(rows), 30)
                    self.assertLessEqual(
                        max(next_y - y for y, next_y in zip(rows, rows[1:])),
                        2,
                    )


if __name__ == "__main__":
    unittest.main()
