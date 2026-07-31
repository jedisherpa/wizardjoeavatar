import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.remove_isolated_alpha_components import (
    remove_isolated_components,
)


class RemoveIsolatedAlphaComponentsTests(unittest.TestCase):
    def test_removes_only_components_at_or_below_the_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source.png"
            output_path = root / "output.png"
            receipt_path = root / "receipt.json"
            source = Image.new("RGBA", (40, 30), (0, 0, 0, 0))
            draw = ImageDraw.Draw(source)
            draw.rectangle((5, 5, 25, 25), fill=(20, 30, 40, 255))
            draw.rectangle((32, 3, 33, 4), fill=(200, 30, 40, 255))
            source.save(source_path)
            source_sha256 = hashlib.sha256(
                source_path.read_bytes()
            ).hexdigest()

            receipt = remove_isolated_components(
                source_path,
                source_path,
                receipt_path,
                maximum_area=4,
            )

            output = Image.open(source_path).convert("RGBA")
            self.assertEqual(output.getpixel((10, 10))[3], 255)
            self.assertEqual(output.getpixel((32, 3))[3], 0)
            self.assertEqual(receipt["removed_pixel_count"], 4)
            self.assertEqual(receipt["input_sha256"], source_sha256)
            self.assertNotEqual(
                receipt["output_sha256"],
                source_sha256,
            )
            stored = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["removed_components"][0]["area"], 4)

    def test_rejects_a_noop_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source.png"
            source = Image.new("RGBA", (20, 20), (20, 30, 40, 255))
            source.save(source_path)

            with self.assertRaisesRegex(ValueError, "no isolated"):
                remove_isolated_components(
                    source_path,
                    root / "output.png",
                    root / "receipt.json",
                    maximum_area=3,
                )


if __name__ == "__main__":
    unittest.main()
