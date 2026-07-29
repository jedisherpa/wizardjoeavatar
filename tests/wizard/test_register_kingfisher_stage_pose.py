import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.register_kingfisher_stage_pose import (
    CANVAS_SIZE,
    ROOT,
    TARGET_BASELINE_Y,
    portable_receipt_path,
    register_pose,
)


class RegisterKingfisherStagePoseTests(unittest.TestCase):
    def test_registers_binary_alpha_at_stable_center_and_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "inputs" / "source.png"
            output = root / "generated" / "output.png"
            source.parent.mkdir()
            image = Image.new("RGBA", (1200, 800), (0, 0, 0, 0))
            image.paste((20, 40, 60, 160), (300, 100, 900, 750))
            image.save(source)

            previous_directory = Path.cwd()
            try:
                os.chdir(root)
                audit = register_pose(
                    Path("inputs/./source.png"),
                    Path("generated/staging/../output.png"),
                    ordinal=67,
                    slug="center_mark_resting_beak",
                )
            finally:
                os.chdir(previous_directory)

            registered = Image.open(output).convert("RGBA")
            alpha = registered.getchannel("A")
            bbox = alpha.getbbox()
            self.assertEqual(registered.size, CANVAS_SIZE)
            self.assertEqual(set(alpha.getdata()), {0, 255})
            self.assertEqual(bbox[3], TARGET_BASELINE_Y)
            self.assertLessEqual(abs((bbox[0] + bbox[2]) - 960), 1)
            self.assertEqual(
                audit["pose_id"],
                "kingfisher.act.067.center-mark-resting-beak",
            )
            self.assertEqual(
                audit["approval_state"],
                "candidate_visual_review",
            )
            self.assertFalse(audit["runtime_admitted"])
            self.assertEqual(audit["source"]["path"], "inputs/source.png")
            self.assertEqual(audit["output"]["path"], "generated/output.png")
            serialized_audit = str(audit)
            self.assertNotIn(root.as_posix(), serialized_audit)
            self.assertNotIn(
                Path(__file__).resolve().parents[2].as_posix(),
                serialized_audit,
            )

    def test_redacts_absolute_paths_from_receipts(self):
        self.assertEqual(
            portable_receipt_path(ROOT / "assets" / "example.png"),
            "assets/example.png",
        )
        with tempfile.TemporaryDirectory() as directory:
            external = Path(directory) / "private-source.png"
            self.assertEqual(
                portable_receipt_path(external),
                "external/private-source.png",
            )
            self.assertNotIn(directory, portable_receipt_path(external))


if __name__ == "__main__":
    unittest.main()
