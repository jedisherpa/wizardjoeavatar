import tempfile
import unittest
from pathlib import Path

from PIL import Image

from wizard_avatar.models import WizardCellFrame
from wizard_avatar.render_image import frame_to_png


class SquareRenderingTests(unittest.TestCase):
    def test_png_evidence_renders_cells_as_solid_square_tiles(self):
        red = (220, 20, 60)
        cells = bytes((ord("@"), *red, ord(" "), 255, 255, 255))
        frame = WizardCellFrame(cols=2, rows=1, frame_index=0, cells=cells, raw_size=len(cells))

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "square.png"
            frame_to_png(frame, path, cell_size=(4, 4))
            image = Image.open(path)

        self.assertEqual(image.size, (8, 4))
        self.assertEqual(image.getpixel((0, 0)), red)
        self.assertEqual(image.getpixel((2, 2)), red)
        self.assertEqual(image.getpixel((3, 3)), red)
        self.assertEqual(image.getpixel((4, 0)), (255, 255, 255))


if __name__ == "__main__":
    unittest.main()
