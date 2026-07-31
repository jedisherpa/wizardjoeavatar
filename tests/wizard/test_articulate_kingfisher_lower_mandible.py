import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.articulate_kingfisher_lower_mandible import (
    articulate_lower_mandible,
)


class ArticulateKingfisherLowerMandibleTests(unittest.TestCase):
    def test_rotates_only_declared_mandible_and_keeps_binary_alpha(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resting_path = root / "resting.png"
            output_path = root / "open.png"
            receipt_path = root / "receipt.json"
            resting = Image.new("RGBA", (80, 60), (0, 0, 0, 0))
            draw = ImageDraw.Draw(resting)
            draw.rectangle((10, 10, 70, 55), fill=(30, 40, 50, 255))
            draw.polygon(
                [(30, 25), (65, 24), (32, 32)],
                fill=(70, 80, 90, 255),
            )
            resting.save(resting_path)

            receipt = articulate_lower_mandible(
                resting_path,
                output_path,
                receipt_path,
                mandible_polygon=[(30, 25), (65, 24), (32, 32)],
                cavity_polygon=[(30, 25), (65, 24), (33, 38)],
                hinge=(30, 25),
                rotation_degrees=12,
                tongue_polygon=[(34, 29), (52, 27), (35, 33)],
            )

            with Image.open(output_path) as loaded:
                output = loaded.convert("RGBA")
            self.assertEqual(
                output.getpixel((15, 15)),
                resting.getpixel((15, 15)),
            )
            self.assertTrue(
                set(output.getchannel("A").getdata()).issubset({0, 255})
            )
            self.assertGreater(receipt["changed_pixels"], 0)
            self.assertFalse(receipt["runtime_admitted"])
            self.assertEqual(
                receipt["upper_beak_policy"],
                "immutable_source_pixels",
            )

    def test_rejects_empty_articulation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resting_path = root / "resting.png"
            Image.new("RGBA", (40, 30), (0, 0, 0, 0)).save(resting_path)
            with self.assertRaisesRegex(ValueError, "no visible change"):
                articulate_lower_mandible(
                    resting_path,
                    root / "open.png",
                    root / "receipt.json",
                    mandible_polygon=[(10, 10), (20, 10), (12, 15)],
                    cavity_polygon=[(10, 10), (20, 10), (12, 15)],
                    hinge=(10, 10),
                    rotation_degrees=10,
                    cavity_fill=(0, 0, 0, 0),
                )


if __name__ == "__main__":
    unittest.main()
