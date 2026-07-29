import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from tools.stabilize_kingfisher_stage_pair import (
    DEFAULT_ARTICULATION_REGION,
    stabilize_pair,
)


class StabilizeKingfisherStagePairTests(unittest.TestCase):
    def test_preserves_resting_frame_outside_articulation_region(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resting_path = root / "resting.png"
            candidate_path = root / "candidate.png"
            output_path = root / "output.png"
            resting = Image.new("RGBA", (960, 540), (20, 30, 40, 255))
            candidate = Image.new("RGBA", (960, 540), (80, 90, 100, 255))
            ImageDraw.Draw(candidate).rectangle(
                (420, 180, 540, 305),
                fill=(170, 20, 30, 255),
            )
            resting.save(resting_path)
            candidate.save(candidate_path)

            stabilize_pair(resting_path, candidate_path, output_path)

            output = Image.open(output_path).convert("RGBA")
            difference = ImageChops.difference(resting, output)
            difference.paste(
                (0, 0, 0, 0),
                DEFAULT_ARTICULATION_REGION,
            )
            self.assertIsNone(difference.getbbox())
            self.assertEqual(
                output.getpixel((480, 220)),
                (170, 20, 30, 255),
            )

    def test_rejects_region_large_enough_to_replace_the_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resting_path = root / "resting.png"
            candidate_path = root / "candidate.png"
            output_path = root / "output.png"
            Image.new("RGBA", (960, 540), (20, 30, 40, 255)).save(
                resting_path
            )
            Image.new("RGBA", (960, 540), (80, 90, 100, 255)).save(
                candidate_path
            )

            with self.assertRaisesRegex(ValueError, "too wide"):
                stabilize_pair(
                    resting_path,
                    candidate_path,
                    output_path,
                    articulation_region=(280, 120, 680, 350),
                )


if __name__ == "__main__":
    unittest.main()
