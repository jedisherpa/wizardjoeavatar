import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.canonicalize_joeville_authored_alpha import canonicalize


class JoeVilleAuthoredAlphaCanonicalizerTests(unittest.TestCase):
    @staticmethod
    def _write_authority(root: Path) -> Path:
        authority = root / "authority.json"
        authority.write_text(
            json.dumps(
                {
                    "master_profile": {
                        "profile_id": "test",
                        "canvas_width": 64,
                        "canvas_height": 64,
                        "baseline_y": 58,
                        "minimum_margin": 4,
                    }
                }
            ),
            encoding="utf-8",
        )
        return authority

    def test_translates_without_resampling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = self._write_authority(root)
            source = root / "source.png"
            source_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            ImageDraw.Draw(source_image).rectangle(
                (11, 7, 30, 50), fill=(150, 70, 30, 255)
            )
            source_image.save(source)
            destination = root / "destination.png"

            receipt = canonicalize(
                source_path=source,
                destination_path=destination,
                authority_path=authority,
            )

            result = Image.open(destination).convert("RGBA")
            self.assertEqual(result.getchannel("A").getbbox(), (22, 14, 42, 58))
            self.assertEqual(receipt["translation"], {"x": 11, "y": 7})
            self.assertFalse(receipt["resampled"])
            visible_source = sorted(
                pixel
                for pixel in source_image.getdata()
                if pixel[3]
            )
            visible_result = sorted(
                pixel for pixel in result.getdata() if pixel[3]
            )
            self.assertEqual(visible_source, visible_result)
            self.assertEqual(
                receipt["destination_rgba_sha256"],
                hashlib.sha256(result.tobytes()).hexdigest(),
            )

    def test_rejects_oversize_source_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = self._write_authority(root)
            source = root / "source.png"
            source_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            ImageDraw.Draw(source_image).rectangle(
                (2, 1, 61, 60), fill=(150, 70, 30, 255)
            )
            source_image.save(source)

            with self.assertRaisesRegex(
                ValueError,
                "cannot fit canonical margins",
            ):
                canonicalize(
                    source_path=source,
                    destination_path=root / "destination.png",
                    authority_path=authority,
                )

    def test_ground_support_alignment_keeps_lopsided_actor_root_centered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = self._write_authority(root)
            source = root / "source.png"
            source_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(source_image)
            draw.rectangle((26, 10, 37, 44), fill=(150, 70, 30, 255))
            draw.rectangle((38, 18, 54, 25), fill=(150, 70, 30, 255))
            draw.rectangle((27, 45, 36, 50), fill=(90, 40, 20, 255))
            source_image.save(source)
            destination = root / "destination.png"

            receipt = canonicalize(
                source_path=source,
                destination_path=destination,
                authority_path=authority,
                ground_support_band_height=6,
            )

            result = Image.open(destination).convert("RGBA")
            self.assertEqual(receipt["alignment_mode"], "ground_support_center")
            self.assertEqual(receipt["alignment_source_center_x"], 32.0)
            self.assertEqual(receipt["alignment_target_center_x"], 32.0)
            self.assertEqual(receipt["ground_support_band_height"], 6)
            self.assertEqual(
                receipt["source_ground_support_bbox"],
                [27, 45, 37, 51],
            )
            self.assertEqual(
                receipt["destination_ground_support_bbox"],
                [27, 52, 37, 58],
            )
            self.assertEqual(result.getchannel("A").getbbox(), (26, 17, 55, 58))
            self.assertEqual(receipt["translation"], {"x": 0, "y": 7})
            self.assertFalse(receipt["resampled"])

    def test_rejects_nonpositive_ground_support_band(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = self._write_authority(root)
            source = root / "source.png"
            image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            ImageDraw.Draw(image).rectangle(
                (20, 10, 40, 50), fill=(150, 70, 30, 255)
            )
            image.save(source)

            with self.assertRaisesRegex(
                ValueError,
                "ground support band height must be positive",
            ):
                canonicalize(
                    source_path=source,
                    destination_path=root / "destination.png",
                    authority_path=authority,
                    ground_support_band_height=0,
                )

    def test_opt_in_fit_records_resampling_and_preserves_margins(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = self._write_authority(root)
            source = root / "source.png"
            source_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            ImageDraw.Draw(source_image).rectangle(
                (2, 1, 61, 60), fill=(150, 70, 30, 255)
            )
            source_image.save(source)
            destination = root / "destination.png"

            receipt = canonicalize(
                source_path=source,
                destination_path=destination,
                authority_path=authority,
                fit_oversize=True,
            )

            result = Image.open(destination).convert("RGBA")
            bbox = result.getchannel("A").getbbox()
            self.assertIsNotNone(bbox)
            assert bbox is not None
            self.assertGreaterEqual(bbox[0], 4)
            self.assertGreaterEqual(bbox[1], 4)
            self.assertGreaterEqual(64 - bbox[2], 4)
            self.assertEqual(bbox[3], 58)
            self.assertTrue(receipt["resampled"])
            self.assertLess(receipt["scale"], 1.0)
            self.assertEqual(receipt["resample_filter"], "lanczos")


if __name__ == "__main__":
    unittest.main()
