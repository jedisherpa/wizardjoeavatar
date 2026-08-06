import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.compose_kingfisher_pair_mandible_patch import (
    beak_anatomy_metrics,
    compose_mandible_patch,
)
from tools.compose_kingfisher_pair_render import CANVAS_SIZE


class ComposeKingfisherPairMandiblePatchTests(unittest.TestCase):
    def test_beak_anatomy_rejects_reversed_profile_mandible(self):
        report = beak_anatomy_metrics(
            hinge=(100, 100),
            hinge_radius=6,
            upper_beak_polygon=[
                (98, 96),
                (160, 98),
                (158, 106),
                (100, 104),
            ],
            mandible_polygon=[
                (100, 102),
                (72, 112),
                (68, 124),
                (98, 110),
            ],
            cavity_polygon=[
                (100, 101),
                (82, 108),
                (80, 114),
                (99, 106),
            ],
        )

        self.assertFalse(report["passed"])
        self.assertEqual(report["mode"], "directional")
        self.assertFalse(report["checks"]["same_longitudinal_direction"])

    def _sources(self, root: Path, *, detached: bool = False) -> tuple[Path, Path]:
        resting_path = root / "resting.png"
        generated_path = root / "generated.png"
        resting = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(resting)
        draw.rectangle((400, 200, 560, 500), fill=(20, 30, 40, 255))
        draw.polygon(
            [(470, 240), (550, 230), (480, 250)],
            fill=(40, 45, 50, 255),
        )
        resting.save(resting_path)

        generated = Image.new("RGB", CANVAS_SIZE, (0, 255, 0))
        draw = ImageDraw.Draw(generated)
        draw.rectangle((400, 200, 560, 500), fill=(20, 30, 40))
        draw.polygon(
            [(470, 252), (548, 254), (480, 268)],
            fill=(60, 65, 70),
        )
        if detached:
            draw.rectangle((520, 264, 530, 270), fill=(60, 65, 70))
        generated.save(generated_path)
        return resting_path, generated_path

    def test_composites_connected_mandible_and_preserves_upper_beak(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            output_path = root / "output.png"
            receipt = compose_mandible_patch(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1,
                translate_x=0,
                translate_y=0,
                mandible_polygon=[
                    (468, 248),
                    (552, 248),
                    (552, 272),
                    (468, 272),
                ],
                cavity_polygon=[
                    (468, 238),
                    (552, 230),
                    (548, 258),
                    (470, 258),
                ],
                upper_beak_polygon=[
                    (468, 228),
                    (552, 225),
                    (552, 250),
                    (468, 250),
                ],
                hinge=(473, 255),
                minimum_mandible_height=10,
            )

            resting = Image.open(resting_path).convert("RGBA")
            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(output.getpixel((500, 240)), resting.getpixel((500, 240)))
            self.assertNotEqual(output.getpixel((500, 260)), resting.getpixel((500, 260)))
            self.assertFalse(receipt["outside_articulation_change"])
            self.assertEqual(receipt["upper_beak_policy"], "immutable_source_pixels")
            self.assertGreaterEqual(receipt["mandible_connected_ratio"], 0.9)

    def test_uses_separate_upper_beak_outline_for_anatomy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            output_path = root / "output.png"
            anatomy_polygon = [
                (468, 228),
                (552, 225),
                (552, 250),
                (468, 250),
            ]
            receipt = compose_mandible_patch(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1,
                translate_x=0,
                translate_y=0,
                mandible_polygon=[
                    (468, 248),
                    (552, 248),
                    (552, 272),
                    (468, 272),
                ],
                cavity_polygon=[
                    (468, 238),
                    (552, 230),
                    (548, 258),
                    (470, 258),
                ],
                upper_beak_polygon=[
                    (400, 180),
                    (552, 225),
                    (552, 250),
                    (468, 250),
                ],
                anatomy_upper_beak_polygon=anatomy_polygon,
                hinge=(473, 255),
                minimum_mandible_height=10,
            )

            self.assertEqual(
                receipt["anatomy_upper_beak_polygon"],
                [list(point) for point in anatomy_polygon],
            )
            self.assertTrue(receipt["beak_anatomy"]["passed"])

    def test_clears_declared_residual_edge_before_compositing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            resting = Image.open(resting_path).convert("RGBA")
            ImageDraw.Draw(resting).line(
                (548, 260, 570, 270),
                fill=(245, 245, 245, 255),
                width=2,
            )
            resting.save(resting_path)
            output_path = root / "output.png"
            receipt = compose_mandible_patch(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1,
                translate_x=0,
                translate_y=0,
                mandible_polygon=[
                    (468, 248),
                    (552, 248),
                    (552, 272),
                    (468, 272),
                ],
                cavity_polygon=[
                    (468, 238),
                    (552, 230),
                    (548, 258),
                    (470, 258),
                ],
                upper_beak_polygon=[
                    (468, 228),
                    (552, 225),
                    (552, 250),
                    (468, 250),
                ],
                residual_clear_polygon=[
                    (548, 258),
                    (574, 268),
                    (572, 275),
                    (548, 266),
                ],
                hinge=(473, 255),
                minimum_mandible_height=10,
            )

            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(output.getpixel((565, 269))[3], 0)
            self.assertEqual(
                receipt["residual_clear_polygon"],
                [[548, 258], [574, 268], [572, 275], [548, 266]],
            )

    def test_neutral_cavity_overwrites_generated_mouth_pixels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            generated = Image.open(generated_path).convert("RGB")
            ImageDraw.Draw(generated).polygon(
                [(478, 252), (540, 252), (520, 262), (485, 260)],
                fill=(220, 35, 55),
            )
            generated.save(generated_path)
            output_path = root / "output.png"
            receipt = compose_mandible_patch(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1,
                translate_x=0,
                translate_y=0,
                mandible_polygon=[
                    (468, 248),
                    (552, 248),
                    (552, 272),
                    (468, 272),
                ],
                cavity_polygon=[
                    (478, 251),
                    (542, 251),
                    (520, 263),
                    (484, 261),
                ],
                upper_beak_polygon=[
                    (468, 228),
                    (552, 225),
                    (552, 250),
                    (468, 250),
                ],
                hinge=(473, 255),
                minimum_mandible_height=10,
                cavity_fill=(64, 24, 20, 255),
            )

            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(output.getpixel((500, 257)), (64, 24, 20, 255))
            self.assertEqual(receipt["cavity_fill_rgba"], [64, 24, 20, 255])
            self.assertEqual(receipt["cavity_source"], "solid")

    def test_preserves_reviewed_generated_cavity_when_requested(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            generated = Image.open(generated_path).convert("RGB")
            ImageDraw.Draw(generated).polygon(
                [(478, 252), (540, 252), (520, 262), (485, 260)],
                fill=(112, 31, 38),
            )
            generated.save(generated_path)
            output_path = root / "output.png"
            receipt = compose_mandible_patch(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1,
                translate_x=0,
                translate_y=0,
                mandible_polygon=[
                    (468, 248),
                    (552, 248),
                    (552, 272),
                    (468, 272),
                ],
                cavity_polygon=[
                    (478, 251),
                    (542, 251),
                    (520, 263),
                    (484, 261),
                ],
                upper_beak_polygon=[
                    (468, 228),
                    (552, 225),
                    (552, 250),
                    (468, 250),
                ],
                hinge=(473, 255),
                minimum_mandible_height=10,
                cavity_source="generated",
            )

            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(output.getpixel((500, 257)), (112, 31, 38, 255))
            self.assertEqual(receipt["cavity_source"], "generated")
            self.assertIsNone(receipt["cavity_fill_rgba"])

    def test_neutralizes_warm_pixels_only_inside_explicit_oral_region(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            generated = Image.open(generated_path).convert("RGB")
            draw = ImageDraw.Draw(generated)
            draw.rectangle((490, 252, 515, 260), fill=(180, 85, 24))
            draw.rectangle((530, 252, 542, 260), fill=(180, 85, 24))
            generated.save(generated_path)
            output_path = root / "output.png"
            receipt = compose_mandible_patch(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1,
                translate_x=0,
                translate_y=0,
                mandible_polygon=[
                    (468, 248),
                    (552, 248),
                    (552, 272),
                    (468, 272),
                ],
                cavity_polygon=[
                    (478, 251),
                    (542, 251),
                    (542, 263),
                    (478, 263),
                ],
                upper_beak_polygon=[
                    (468, 228),
                    (552, 225),
                    (552, 250),
                    (468, 250),
                ],
                hinge=(473, 255),
                minimum_mandible_height=10,
                cavity_source="generated_overlay",
                oral_warm_replacement=(18, 23, 31, 255),
                oral_warm_replacement_polygon=[
                    (488, 250),
                    (518, 250),
                    (518, 264),
                    (488, 264),
                ],
            )

            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(output.getpixel((500, 257)), (18, 23, 31, 255))
            self.assertEqual(output.getpixel((536, 257)), (180, 85, 24, 255))
            self.assertEqual(
                receipt["oral_warm_replacement_rgba"],
                [18, 23, 31, 255],
            )
            self.assertEqual(
                receipt["oral_warm_replacement_polygon"],
                [[488, 250], [518, 250], [518, 264], [488, 264]],
            )

    def test_overlays_generated_cavity_after_restoring_upper_beak(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            generated = Image.open(generated_path).convert("RGB")
            ImageDraw.Draw(generated).rectangle(
                (490, 246, 530, 260),
                fill=(112, 31, 38),
            )
            generated.save(generated_path)
            output_path = root / "output.png"
            receipt = compose_mandible_patch(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1,
                translate_x=0,
                translate_y=0,
                mandible_polygon=[
                    (468, 248),
                    (552, 248),
                    (552, 272),
                    (468, 272),
                ],
                cavity_polygon=[
                    (490, 246),
                    (530, 246),
                    (530, 260),
                    (490, 260),
                ],
                upper_beak_polygon=[
                    (468, 228),
                    (552, 225),
                    (552, 250),
                    (468, 250),
                ],
                hinge=(473, 255),
                minimum_mandible_height=10,
                cavity_source="generated_overlay",
            )

            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(output.getpixel((500, 248)), (112, 31, 38, 255))
            self.assertEqual(receipt["cavity_source"], "generated_overlay")
            self.assertIsNone(receipt["cavity_fill_rgba"])

    def test_overlays_solid_cavity_after_restoring_upper_beak(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            output_path = root / "output.png"
            receipt = compose_mandible_patch(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1,
                translate_x=0,
                translate_y=0,
                mandible_polygon=[
                    (468, 248),
                    (552, 248),
                    (552, 272),
                    (468, 272),
                ],
                cavity_polygon=[
                    (490, 246),
                    (530, 246),
                    (530, 260),
                    (490, 260),
                ],
                upper_beak_polygon=[
                    (468, 228),
                    (552, 225),
                    (552, 250),
                    (468, 250),
                ],
                hinge=(473, 255),
                minimum_mandible_height=10,
                cavity_fill=(23, 17, 19, 255),
                cavity_source="solid_overlay",
            )

            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(output.getpixel((500, 248)), (23, 17, 19, 255))
            self.assertEqual(receipt["cavity_source"], "solid_overlay")
            self.assertEqual(receipt["cavity_fill_rgba"], [23, 17, 19, 255])

    def test_overlays_generated_detail_over_solid_cavity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            generated = Image.open(generated_path).convert("RGB")
            draw = ImageDraw.Draw(generated)
            draw.rectangle((490, 246, 519, 260), fill=(112, 31, 38))
            draw.rectangle((520, 246, 530, 260), fill=(0, 255, 0))
            generated.save(generated_path)
            output_path = root / "output.png"
            receipt = compose_mandible_patch(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1,
                translate_x=0,
                translate_y=0,
                mandible_polygon=[
                    (468, 248),
                    (552, 248),
                    (552, 272),
                    (468, 272),
                ],
                cavity_polygon=[
                    (490, 246),
                    (530, 246),
                    (530, 260),
                    (490, 260),
                ],
                upper_beak_polygon=[
                    (468, 228),
                    (552, 225),
                    (552, 250),
                    (468, 250),
                ],
                hinge=(473, 255),
                minimum_mandible_height=10,
                cavity_fill=(23, 17, 19, 255),
                cavity_source="solid_generated_overlay",
            )

            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(output.getpixel((500, 248)), (112, 31, 38, 255))
            self.assertEqual(output.getpixel((525, 248)), (23, 17, 19, 255))
            self.assertEqual(
                receipt["cavity_source"], "solid_generated_overlay"
            )
            self.assertEqual(receipt["cavity_fill_rgba"], [23, 17, 19, 255])

    def test_rejects_underweight_mandible(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            with self.assertRaisesRegex(ValueError, "too thin"):
                compose_mandible_patch(
                    resting_path,
                    generated_path,
                    root / "output.png",
                    root / "receipt.json",
                    scale=1,
                    translate_x=0,
                    translate_y=0,
                    mandible_polygon=[
                        (468, 252),
                        (552, 252),
                        (552, 257),
                        (468, 257),
                    ],
                    cavity_polygon=[(468, 240), (552, 235), (480, 260)],
                    upper_beak_polygon=[(468, 228), (552, 225), (480, 250)],
                    hinge=(473, 254),
                    minimum_mandible_height=10,
                )

    def test_can_exclude_light_neutral_throat_pixels_from_donor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            generated = Image.open(generated_path).convert("RGB")
            draw = ImageDraw.Draw(generated)
            draw.rectangle((468, 248, 552, 272), fill=(230, 222, 216))
            draw.polygon(
                [(478, 251), (542, 251), (520, 266), (484, 264)],
                fill=(112, 31, 38),
            )
            generated.save(generated_path)
            output_path = root / "output.png"
            receipt = compose_mandible_patch(
                resting_path,
                generated_path,
                output_path,
                root / "receipt.json",
                scale=1,
                translate_x=0,
                translate_y=0,
                mandible_polygon=[
                    (468, 248),
                    (552, 248),
                    (552, 272),
                    (468, 272),
                ],
                cavity_polygon=[
                    (478, 251),
                    (542, 251),
                    (520, 266),
                    (484, 264),
                ],
                upper_beak_polygon=[
                    (468, 228),
                    (552, 225),
                    (552, 248),
                    (468, 248),
                ],
                hinge=(480, 255),
                minimum_mandible_height=10,
                cavity_source="generated_overlay",
                source_mask_mode="exclude_light_neutral",
                source_light_threshold=180,
                source_neutral_chroma_threshold=36,
            )

            resting = Image.open(resting_path).convert("RGBA")
            output = Image.open(output_path).convert("RGBA")
            self.assertEqual(
                output.getpixel((470, 260)),
                resting.getpixel((470, 260)),
            )
            self.assertEqual(output.getpixel((500, 258)), (112, 31, 38, 255))
            self.assertEqual(
                receipt["source_mask"]["mode"],
                "exclude_light_neutral",
            )

    def test_rejects_mandible_that_misses_hinge(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resting_path, generated_path = self._sources(root)
            with self.assertRaisesRegex(ValueError, "connect to the hinge"):
                compose_mandible_patch(
                    resting_path,
                    generated_path,
                    root / "output.png",
                    root / "receipt.json",
                    scale=1,
                    translate_x=0,
                    translate_y=0,
                    mandible_polygon=[
                        (500, 248),
                        (552, 248),
                        (552, 272),
                        (500, 272),
                    ],
                    cavity_polygon=[(468, 240), (552, 235), (480, 260)],
                    upper_beak_polygon=[(468, 228), (552, 225), (480, 250)],
                    hinge=(473, 254),
                    hinge_radius=4,
                    minimum_mandible_height=10,
                )


if __name__ == "__main__":
    unittest.main()
