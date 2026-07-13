import hashlib
import unittest

from wizard_avatar.compositor import CellCanvas
from wizard_avatar.models import Cell
from wizard_avatar.pose_compositor import composite_anchor_transition


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


if __name__ == "__main__":
    unittest.main()
