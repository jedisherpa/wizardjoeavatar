import tempfile
import unittest
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.compose_kingfisher_pair_render import (
    CANVAS_SIZE,
    compose_pair,
    extract_light_background_alpha,
)


class ComposeKingfisherPairRenderTests(unittest.TestCase):
    def test_background_extraction_preserves_enclosed_white_detail(self):
        source = Image.new("RGB", (20, 20), (250, 250, 250))
        draw = ImageDraw.Draw(source)
        draw.rectangle((5, 5, 14, 14), fill=(20, 30, 40))
        draw.rectangle((8, 8, 11, 11), fill=(250, 250, 250))

        result = extract_light_background_alpha(source)

        self.assertEqual(result.getpixel((0, 0))[3], 0)
        self.assertEqual(result.getpixel((9, 9))[3], 255)

    def test_chroma_extraction_preserves_boundary_white_detail(self):
        source = Image.new("RGB", (20, 20), (0, 255, 0))
        draw = ImageDraw.Draw(source)
        draw.rectangle((0, 5, 12, 15), fill=(20, 30, 40))
        draw.rectangle((0, 8, 4, 12), fill=(250, 250, 250))
        draw.line((13, 5, 13, 15), fill=(45, 220, 45), width=1)

        result = extract_light_background_alpha(source)

        self.assertEqual(result.getpixel((19, 0))[3], 0)
        self.assertEqual(result.getpixel((0, 10))[3], 255)
        self.assertEqual(result.getpixel((13, 10))[3], 0)

    def test_chroma_extraction_removes_enclosed_green_spill(self):
        source = Image.new("RGB", (20, 20), (0, 255, 0))
        draw = ImageDraw.Draw(source)
        draw.rectangle((4, 4, 15, 15), fill=(20, 30, 40))
        draw.point((10, 10), fill=(75, 239, 94))
        draw.point((11, 10), fill=(250, 250, 250))

        result = extract_light_background_alpha(source)

        self.assertEqual(result.getpixel((10, 10))[3], 0)
        self.assertEqual(result.getpixel((11, 10))[3], 255)
        self.assertEqual(result.getpixel((5, 5))[3], 255)

    def test_composite_changes_only_the_declared_polygon(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path = root / "resting.png"
            generated_path = root / "generated.png"
            output_path = root / "speaking.png"
            receipt_path = root / "receipt.json"
            resting = Image.new(
                "RGBA",
                CANVAS_SIZE,
                (0, 0, 0, 0),
            )
            ImageDraw.Draw(resting).rectangle(
                (400, 200, 560, 500),
                fill=(20, 30, 40, 255),
            )
            resting.save(resting_path)
            generated = Image.new("RGB", CANVAS_SIZE, (250, 250, 250))
            ImageDraw.Draw(generated).rectangle(
                (400, 200, 560, 500),
                fill=(20, 30, 40),
            )
            ImageDraw.Draw(generated).rectangle(
                (430, 230, 530, 280),
                fill=(180, 20, 20),
            )
            generated.save(generated_path)

            receipt = compose_pair(
                resting_path,
                generated_path,
                output_path,
                receipt_path,
                scale=1.0,
                translate_x=0,
                translate_y=0,
                articulation_polygon=[
                    (425, 225),
                    (535, 225),
                    (535, 285),
                    (425, 285),
                ],
            )

            self.assertFalse(receipt["outside_articulation_change"])
            self.assertEqual(receipt["alignment"]["scale_x"], 1.0)
            self.assertEqual(receipt["alignment"]["scale_y"], 1.0)
            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(
                output.getpixel((410, 210)),
                resting.getpixel((410, 210)),
            )
            self.assertNotEqual(
                output.getpixel((450, 250)),
                resting.getpixel((450, 250)),
            )

    def test_independent_alignment_scales_are_recorded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path = root / "resting.png"
            generated_path = root / "generated.png"
            resting = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
            ImageDraw.Draw(resting).rectangle(
                (440, 230, 520, 280),
                fill=(20, 30, 40, 255),
            )
            resting.save(resting_path)
            generated = Image.new("RGB", CANVAS_SIZE, (250, 250, 250))
            ImageDraw.Draw(generated).rectangle(
                (440, 230, 520, 280),
                fill=(180, 20, 20),
            )
            generated.save(generated_path)

            receipt = compose_pair(
                resting_path,
                generated_path,
                root / "speaking.png",
                root / "receipt.json",
                scale=1.0,
                scale_x=1.01,
                scale_y=0.99,
                translate_x=-5,
                translate_y=3,
                articulation_polygon=[
                    (435, 225),
                    (525, 225),
                    (525, 285),
                    (435, 285),
                ],
            )

            self.assertEqual(receipt["alignment"]["scale_x"], 1.01)
            self.assertEqual(receipt["alignment"]["scale_y"], 0.99)

    def test_resting_repair_receipt_uses_distinct_output_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path = root / "source.png"
            generated_path = root / "generated.png"
            output_path = root / "repaired.png"
            receipt_path = root / "receipt.json"
            resting = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
            ImageDraw.Draw(resting).rectangle(
                (450, 230, 510, 270),
                fill=(20, 30, 40, 255),
            )
            resting.save(resting_path)
            generated = Image.new("RGB", CANVAS_SIZE, (250, 250, 250))
            ImageDraw.Draw(generated).rectangle(
                (450, 230, 510, 270),
                fill=(180, 20, 20),
            )
            generated.save(generated_path)

            compose_pair(
                resting_path,
                generated_path,
                output_path,
                receipt_path,
                scale=1.0,
                translate_x=0,
                translate_y=0,
                articulation_polygon=[
                    (445, 225),
                    (515, 225),
                    (515, 275),
                    (445, 275),
                ],
                output_role="resting_repair",
            )

            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["output_role"], "resting_repair")
            self.assertEqual(
                receipt["repaired_resting_path"],
                output_path.as_posix(),
            )
            self.assertNotIn("speaking_path", receipt)

    def test_cavity_polygon_overrides_generated_interior(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path = root / "resting.png"
            generated_path = root / "generated.png"
            output_path = root / "speaking.png"
            receipt_path = root / "receipt.json"
            resting = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
            ImageDraw.Draw(resting).rectangle(
                (400, 200, 560, 500),
                fill=(20, 30, 40, 255),
            )
            resting.save(resting_path)
            generated = Image.new("RGB", CANVAS_SIZE, (250, 250, 250))
            ImageDraw.Draw(generated).rectangle(
                (400, 200, 560, 500),
                fill=(20, 30, 40),
            )
            ImageDraw.Draw(generated).rectangle(
                (430, 230, 530, 280),
                fill=(220, 120, 30),
            )
            generated.save(generated_path)

            receipt = compose_pair(
                resting_path,
                generated_path,
                output_path,
                receipt_path,
                scale=1.0,
                translate_x=0,
                translate_y=0,
                articulation_polygon=[
                    (425, 225),
                    (535, 225),
                    (535, 285),
                    (425, 285),
                ],
                cavity_polygon=[
                    (450, 245),
                    (510, 245),
                    (500, 270),
                    (460, 270),
                ],
            )

            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(output.getpixel((480, 255)), (10, 13, 16, 255))
            self.assertEqual(
                output.getpixel((410, 210)),
                resting.getpixel((410, 210)),
            )
            self.assertEqual(
                receipt["cavity_polygon"],
                [[450, 245], [510, 245], [500, 270], [460, 270]],
            )
            self.assertEqual(receipt["cavity_fill_rgba"], [10, 13, 16, 255])
            self.assertEqual(
                receipt["cavity_fill_mode"],
                "generated_alpha",
            )

    def test_cavity_polygon_must_stay_inside_articulation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path = root / "resting.png"
            generated_path = root / "generated.png"
            resting = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
            ImageDraw.Draw(resting).rectangle(
                (400, 200, 560, 500),
                fill=(20, 30, 40, 255),
            )
            resting.save(resting_path)
            Image.new("RGB", CANVAS_SIZE, (20, 30, 40)).save(
                generated_path
            )

            with self.assertRaisesRegex(
                ValueError,
                "cavity polygon must remain inside",
            ):
                compose_pair(
                    resting_path,
                    generated_path,
                    root / "speaking.png",
                    root / "receipt.json",
                    scale=1.0,
                    translate_x=0,
                    translate_y=0,
                    articulation_polygon=[
                        (425, 225),
                        (535, 225),
                        (535, 285),
                        (425, 285),
                    ],
                    cavity_polygon=[
                        (410, 240),
                        (450, 240),
                        (450, 260),
                        (410, 260),
                    ],
                )

    def test_cavity_polygon_is_clipped_to_generated_alpha(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path = root / "resting.png"
            generated_path = root / "generated.png"
            output_path = root / "speaking.png"
            resting = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
            ImageDraw.Draw(resting).rectangle(
                (450, 240, 500, 260),
                fill=(20, 30, 40, 255),
            )
            resting.save(resting_path)
            generated = Image.new("RGB", CANVAS_SIZE, (250, 250, 250))
            ImageDraw.Draw(generated).rectangle(
                (450, 240, 500, 260),
                fill=(220, 120, 30),
            )
            generated.save(generated_path)

            compose_pair(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1.0,
                translate_x=0,
                translate_y=0,
                articulation_polygon=[
                    (440, 225),
                    (510, 225),
                    (510, 275),
                    (440, 275),
                ],
                cavity_polygon=[
                    (440, 230),
                    (510, 230),
                    (510, 250),
                    (440, 250),
                ],
            )

            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(output.getpixel((475, 245)), (10, 13, 16, 255))
            self.assertEqual(output.getpixel((445, 235)), (0, 0, 0, 0))

    def test_opaque_cavity_fills_open_space_inside_articulation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path = root / "resting.png"
            generated_path = root / "generated.png"
            output_path = root / "speaking.png"
            resting = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
            ImageDraw.Draw(resting).rectangle(
                (450, 240, 500, 260),
                fill=(20, 30, 40, 255),
            )
            resting.save(resting_path)
            generated = Image.new("RGB", CANVAS_SIZE, (250, 250, 250))
            ImageDraw.Draw(generated).rectangle(
                (450, 240, 470, 260),
                fill=(220, 120, 30),
            )
            ImageDraw.Draw(generated).rectangle(
                (480, 240, 500, 260),
                fill=(220, 120, 30),
            )
            generated.save(generated_path)

            receipt = compose_pair(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1.0,
                translate_x=0,
                translate_y=0,
                articulation_polygon=[
                    (440, 225),
                    (510, 225),
                    (510, 275),
                    (440, 275),
                ],
                cavity_polygon=[
                    (468, 240),
                    (482, 240),
                    (482, 260),
                    (468, 260),
                ],
                cavity_fill_mode="opaque_polygon",
            )

            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(output.getpixel((475, 250)), (10, 13, 16, 255))
            self.assertEqual(
                receipt["cavity_fill_mode"],
                "opaque_polygon",
            )


if __name__ == "__main__":
    unittest.main()
