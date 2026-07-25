import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.canonicalize_joeville_authored_alpha import canonicalize


class JoeVilleAuthoredAlphaCanonicalizerTests(unittest.TestCase):
    def test_translates_without_resampling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
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


if __name__ == "__main__":
    unittest.main()
