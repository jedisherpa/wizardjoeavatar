import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.generate_reference_avatar_cells import generate


class ReferenceAvatarCellGeneratorTests(unittest.TestCase):
    def test_authored_alpha_preserves_holes_and_rejects_small_matte_islands(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "pose.png"
            output_path = root / "pose.json"
            source = Image.new("RGBA", (64, 64), (255, 255, 255, 0))
            draw = ImageDraw.Draw(source)
            draw.rectangle((20, 10, 40, 50), fill=(20, 110, 220, 255))
            draw.rectangle((27, 22, 33, 34), fill=(255, 255, 255, 0))
            draw.point((2, 62), fill=(70, 170, 150, 80))
            source.save(source_path)

            payload = generate(
                source_path,
                output_path,
                rows=41,
                margin=0,
                threshold=30.0,
                coverage_threshold=24,
                colors=8,
            )

        self.assertEqual(payload["source_crop"], [20, 10, 40, 50])
        self.assertEqual((payload["cols"], payload["rows"]), (21, 41))
        occupied = {(cell["x"], cell["y"]) for cell in payload["cells"]}
        self.assertNotIn((10, 18), occupied)
        self.assertLess(len(occupied), payload["cols"] * payload["rows"])
        self.assertTrue(all(cell["rgb"][2] > cell["rgb"][0] for cell in payload["cells"]))


if __name__ == "__main__":
    unittest.main()
