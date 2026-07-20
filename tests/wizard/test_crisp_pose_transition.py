import hashlib
import unittest

from wizard_avatar.compositor import CellCanvas
from wizard_avatar.models import Cell
from wizard_avatar.pose_compositor import (
    composite_anchor_transition,
    composite_landmark_splat_transition,
    composite_landmark_warp_transition,
    composite_localized_landmark_transition,
)


def cell_signature(canvas):
    payload = bytearray()
    for row in canvas.cells:
        for cell in row:
            if cell is None:
                payload.extend(b"\0\0\0\0")
            else:
                payload.extend(cell.to_bytes())
    return hashlib.sha256(payload).hexdigest()


class CrispPoseTransitionTests(unittest.TestCase):
    def test_anchor_transition_endpoints_are_exact_and_crisp(self):
        source = CellCanvas(4, 4)
        target = CellCanvas(5, 4)
        source.set(1, 2, "#", (10, 20, 30), "source")
        source.set(2, 2, "#", (40, 50, 60), "source")
        target.set(2, 2, "#", (200, 120, 20), "target")
        target.set(3, 2, "#", (250, 210, 80), "target")

        first, first_root = composite_anchor_transition(source, target, (1, 3), (2, 3), 0.0)
        last, last_root = composite_anchor_transition(source, target, (1, 3), (2, 3), 1.0)

        self.assertEqual(first_root, last_root)
        self.assertEqual(first.get(first_root[0], first_root[1] - 1), source.get(1, 2))
        self.assertEqual(last.get(last_root[0], last_root[1] - 1), target.get(2, 2))

        mid, _ = composite_anchor_transition(source, target, (1, 3), (2, 3), 0.5)
        allowed = {source.get(1, 2), source.get(2, 2), target.get(2, 2), target.get(3, 2), None}
        for row in mid.cells:
            for cell in row:
                self.assertIn(cell, allowed)

    def test_anchor_transition_is_deterministic(self):
        source = CellCanvas(3, 3)
        target = CellCanvas(3, 3)
        for x in range(3):
            source.set(x, 1, "#", (10 + x, 20, 30), "source")
            target.set(x, 1, "#", (200 + x, 120, 20), "target")

        first, _ = composite_anchor_transition(source, target, (1, 2), (1, 2), 0.375)
        second, _ = composite_anchor_transition(source, target, (1, 2), (1, 2), 0.375)
        self.assertEqual(cell_signature(first), cell_signature(second))

    def test_landmark_warp_endpoints_are_exact_and_intermediate_is_deterministic(self):
        source = CellCanvas(7, 5)
        target = CellCanvas(7, 5)
        for x in range(1, 4):
            source.set(x, 2, "#", (10 + x, 20, 30), "source")
            target.set(x + 2, 2, "#", (200 + x, 120, 20), "target")
        controls = (((1, 2), (3, 2)), ((3, 2), (5, 2)))

        first = composite_landmark_warp_transition(source, target, controls, 0.0)
        last = composite_landmark_warp_transition(source, target, controls, 1.0)
        middle_a = composite_landmark_warp_transition(source, target, controls, 0.5)
        middle_b = composite_landmark_warp_transition(source, target, controls, 0.5)

        self.assertEqual(cell_signature(first), cell_signature(source))
        self.assertEqual(cell_signature(last), cell_signature(target))
        self.assertEqual(cell_signature(middle_a), cell_signature(middle_b))
        self.assertNotEqual(cell_signature(middle_a), cell_signature(source))
        self.assertNotEqual(cell_signature(middle_a), cell_signature(target))

    def test_landmark_warp_rejects_missing_controls(self):
        source = CellCanvas(3, 3)
        target = CellCanvas(3, 3)
        with self.assertRaisesRegex(ValueError, "at least one control"):
            composite_landmark_warp_transition(source, target, (), 0.5)

    def test_landmark_splat_preserves_cells_and_repairs_enclosed_gaps(self):
        source = CellCanvas(9, 7)
        target = CellCanvas(9, 7)
        for y in range(2, 5):
            for x in range(1, 4):
                source.set(x, y, "#", (20 + x, 80 + y, 170), "source")
                target.set(x + 3, y, "#", (120 + x, 60 + y, 40), "target")
        controls = (((1, 3), (4, 3)), ((3, 3), (6, 3)))

        first = composite_landmark_splat_transition(source, target, controls, 0.0)
        middle_a = composite_landmark_splat_transition(source, target, controls, 0.5)
        middle_b = composite_landmark_splat_transition(source, target, controls, 0.5)
        late = composite_landmark_splat_transition(source, target, controls, 0.875)
        last = composite_landmark_splat_transition(source, target, controls, 1.0)

        self.assertEqual(cell_signature(first), cell_signature(source))
        self.assertEqual(cell_signature(last), cell_signature(target))
        self.assertEqual(cell_signature(middle_a), cell_signature(middle_b))
        self.assertEqual(
            {cell.layer_id for row in middle_a.cells for cell in row if cell is not None},
            {"source", "target"},
        )
        self.assertIn(
            "target",
            {cell.layer_id for row in late.cells for cell in row if cell is not None},
        )
        middle_source_count = sum(
            cell is not None and cell.layer_id == "source"
            for row in middle_a.cells
            for cell in row
        )
        late_source_count = sum(
            cell is not None and cell.layer_id == "source"
            for row in late.cells
            for cell in row
        )
        self.assertLess(late_source_count, middle_source_count)
        self.assertGreaterEqual(
            sum(cell is not None for row in middle_a.cells for cell in row),
            8,
        )

    def test_landmark_splat_rejects_missing_controls(self):
        source = CellCanvas(3, 3)
        target = CellCanvas(3, 3)
        with self.assertRaisesRegex(ValueError, "at least one control"):
            composite_landmark_splat_transition(source, target, (), 0.5)

    def test_localized_warp_keeps_unrelated_body_cells_stable(self):
        source = CellCanvas(12, 10)
        target = CellCanvas(12, 10)
        body = Cell("#", (20, 80, 180), "body")
        skin = Cell("#", (220, 150, 90), "hand")
        for y in range(3, 9):
            source.cells[y][7] = body
            target.cells[y][7] = body
        source.cells[6][4] = skin
        source.cells[6][5] = body
        target.cells[2][2] = skin
        target.cells[3][3] = body

        middle = composite_localized_landmark_transition(
            source,
            target,
            ((4, 6), (7, 5)),
            ((2, 2), (7, 5)),
            0.6,
            radius=2.0,
            hand_radius=3.0,
            repair_axis_x=6,
        )

        self.assertEqual(middle.get(7, 8), body)
        self.assertTrue(
            any(
                middle.get(x, y) == skin
                for y in range(2, 7)
                for x in range(1, 6)
            )
        )

    def test_localized_warp_is_deterministic_and_source_exact_at_zero(self):
        source = CellCanvas(8, 8)
        target = CellCanvas(8, 8)
        source.set(2, 5, "#", (210, 140, 80), "hand")
        target.set(1, 2, "#", (210, 140, 80), "hand")
        args = (source, target, ((2, 5), (5, 4)), ((1, 2), (5, 4)), 0.4)

        first = composite_localized_landmark_transition(
            *args, radius=2.5, hand_radius=3.0, repair_axis_x=4
        )
        second = composite_localized_landmark_transition(
            *args, radius=2.5, hand_radius=3.0, repair_axis_x=4
        )
        exact = composite_localized_landmark_transition(
            source,
            target,
            ((2, 5), (5, 4)),
            ((1, 2), (5, 4)),
            0.0,
            radius=2.5,
            hand_radius=3.0,
            repair_axis_x=4,
        )

        self.assertEqual(cell_signature(first), cell_signature(second))
        self.assertEqual(cell_signature(exact), cell_signature(source))


if __name__ == "__main__":
    unittest.main()
