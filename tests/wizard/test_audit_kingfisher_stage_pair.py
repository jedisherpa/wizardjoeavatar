import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.audit_kingfisher_stage_pair import audit_pair


class AuditKingfisherStagePairTests(unittest.TestCase):
    def test_accepts_stable_body_with_visible_mouth_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resting_path = root / "resting.png"
            speaking_path = root / "speaking.png"
            resting = Image.new("RGBA", (960, 540), (0, 0, 0, 0))
            draw = ImageDraw.Draw(resting)
            draw.rectangle((410, 100, 550, 528), fill=(20, 30, 40, 255))
            speaking = resting.copy()
            draw = ImageDraw.Draw(speaking)
            draw.rectangle((430, 220, 530, 300), fill=(170, 20, 30, 255))
            resting.save(resting_path)
            speaking.save(speaking_path)

            report = audit_pair(resting_path, speaking_path)

            self.assertTrue(report["passed"])
            self.assertEqual(report["silhouette_iou"], 1.0)
            self.assertEqual(report["outside_mouth_mean_abs"], 0.0)
            self.assertTrue(report["checks"]["visible_mouth_change"])
            self.assertTrue(report["checks"]["bounded_articulation_change"])
            self.assertEqual(report["schema_version"], 2)
            self.assertEqual(
                report["resting_sha256"],
                hashlib.sha256(resting_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                report["speaking_sha256"],
                hashlib.sha256(speaking_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(report["resting_path"], "external/resting.png")
            self.assertEqual(report["speaking_path"], "external/speaking.png")
            self.assertNotIn(root.as_posix(), str(report))

    def test_transparent_rgb_does_not_create_false_mouth_movement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resting_path = root / "resting.png"
            speaking_path = root / "speaking.png"
            resting = Image.new("RGBA", (960, 540), (0, 0, 0, 0))
            ImageDraw.Draw(resting).rectangle(
                (410, 100, 550, 528),
                fill=(20, 30, 40, 255),
            )
            speaking = resting.copy()
            ImageDraw.Draw(speaking).rectangle(
                (350, 140, 400, 190),
                fill=(255, 255, 255, 0),
            )
            resting.save(resting_path)
            speaking.save(speaking_path)

            report = audit_pair(resting_path, speaking_path)

            self.assertFalse(report["passed"])
            self.assertEqual(report["mouth_mean_abs"], 0.0)
            self.assertFalse(report["checks"]["visible_mouth_change"])
            self.assertNotEqual(
                report["resting_sha256"],
                report["speaking_sha256"],
            )

    def test_rejects_alpha_only_change_outside_articulation_region(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resting_path = root / "resting.png"
            speaking_path = root / "speaking.png"
            resting = Image.new("RGBA", (960, 540), (0, 0, 0, 0))
            ImageDraw.Draw(resting).rectangle(
                (410, 100, 550, 528),
                fill=(20, 30, 40, 255),
            )
            speaking = resting.copy()
            draw = ImageDraw.Draw(speaking)
            draw.rectangle(
                (430, 220, 530, 300),
                fill=(170, 20, 30, 255),
            )
            draw.rectangle(
                (420, 400, 540, 500),
                fill=(20, 30, 40, 254),
            )
            resting.save(resting_path)
            speaking.save(speaking_path)

            report = audit_pair(resting_path, speaking_path)

            self.assertFalse(report["passed"])
            self.assertGreater(report["outside_mouth_mean_abs"], 0.0)
            self.assertFalse(report["checks"]["outside_mouth_stability"])
            self.assertTrue(report["checks"]["visible_mouth_change"])
            self.assertEqual(
                report["resting_sha256"],
                hashlib.sha256(resting_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                report["speaking_sha256"],
                hashlib.sha256(speaking_path.read_bytes()).hexdigest(),
            )

    def test_rejects_head_change_outside_tight_articulation_region(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resting_path = root / "resting.png"
            speaking_path = root / "speaking.png"
            resting = Image.new("RGBA", (960, 540), (0, 0, 0, 0))
            ImageDraw.Draw(resting).rectangle(
                (410, 100, 550, 528),
                fill=(20, 30, 40, 255),
            )
            speaking = resting.copy()
            draw = ImageDraw.Draw(speaking)
            draw.rectangle(
                (430, 220, 530, 300),
                fill=(170, 20, 30, 255),
            )
            draw.rectangle(
                (450, 145, 500, 185),
                fill=(200, 210, 220, 255),
            )
            resting.save(resting_path)
            speaking.save(speaking_path)

            report = audit_pair(resting_path, speaking_path)

            self.assertFalse(report["passed"])
            self.assertFalse(report["checks"]["outside_mouth_stability"])
            self.assertGreater(report["outside_mouth_mean_abs"], 0.0)

    def test_rejects_pair_with_different_registration_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resting_path = root / "resting.png"
            speaking_path = root / "speaking.png"
            resting = Image.new("RGBA", (960, 540), (0, 0, 0, 0))
            speaking = Image.new("RGBA", (960, 540), (0, 0, 0, 0))
            ImageDraw.Draw(resting).rectangle(
                (410, 100, 550, 528),
                fill=(20, 30, 40, 255),
            )
            ImageDraw.Draw(speaking).rectangle(
                (415, 100, 555, 528),
                fill=(20, 30, 40, 255),
            )
            resting.save(resting_path)
            speaking.save(speaking_path)

            with self.assertRaisesRegex(
                ValueError,
                "registration bounds differ",
            ):
                audit_pair(resting_path, speaking_path)


if __name__ == "__main__":
    unittest.main()
