import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.extract_joeville_authored_alpha import extract_alpha


class JoeVilleAuthoredAlphaExtractorTests(unittest.TestCase):
    def test_extracts_border_key_and_records_transform(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            destination = root / "destination.png"
            image = Image.new("RGB", (32, 32), (250, 2, 249))
            ImageDraw.Draw(image).rectangle(
                (8, 6, 23, 27),
                fill=(240, 170, 40),
            )
            image.save(source)

            receipt = extract_alpha(
                source_path=source,
                destination_path=destination,
                tolerance=20,
                edge_contract=0,
            )

            with Image.open(destination) as result:
                rgba = result.convert("RGBA")
                self.assertEqual(rgba.getpixel((0, 0)), (0, 0, 0, 0))
                self.assertEqual(
                    rgba.getchannel("A").getbbox(),
                    (8, 6, 24, 28),
                )
                self.assertEqual(
                    receipt["destination_rgba_sha256"],
                    hashlib.sha256(rgba.tobytes()).hexdigest(),
                )
            self.assertEqual(receipt["key_color"], [250, 2, 249])
            self.assertEqual(receipt["tolerance"], 20)
            self.assertEqual(receipt["edge_contract"], 0)

    def test_contracts_visible_edge_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            destination = root / "destination.png"
            image = Image.new("RGB", (32, 32), (255, 0, 255))
            ImageDraw.Draw(image).rectangle(
                (8, 6, 23, 27),
                fill=(40, 80, 120),
            )
            image.save(source)

            receipt = extract_alpha(
                source_path=source,
                destination_path=destination,
                edge_contract=1,
            )

            self.assertEqual(receipt["silhouette_bbox"], [9, 7, 23, 27])
            with Image.open(destination) as result:
                self.assertEqual(
                    result.convert("RGBA").getpixel((8, 8)),
                    (0, 0, 0, 0),
                )
            with self.assertRaisesRegex(ValueError, "destination exists"):
                extract_alpha(
                    source_path=source,
                    destination_path=destination,
                )

    def test_normalizes_non_square_source_before_keying(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            destination = root / "destination.png"
            image = Image.new("RGB", (20, 40), (255, 0, 255))
            ImageDraw.Draw(image).rectangle(
                (5, 5, 14, 34),
                fill=(40, 80, 120),
            )
            image.save(source)

            receipt = extract_alpha(
                source_path=source,
                destination_path=destination,
                tolerance=20,
                edge_contract=0,
                canvas_size=(64, 64),
            )

            with Image.open(destination) as result:
                self.assertEqual(result.size, (64, 64))
                self.assertEqual(
                    result.getchannel("A").getbbox(),
                    (23, 7, 41, 57),
                )
            self.assertTrue(receipt["canvas_normalized"])
            self.assertEqual(receipt["source_canvas_size"], [20, 40])
            self.assertEqual(receipt["normalization_scale"], 1.6)
            self.assertEqual(receipt["normalization_offset"], [16, 0])


if __name__ == "__main__":
    unittest.main()
