import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.audit_wizard_joe_hd_mouth_states import audit_pose


class WizardJoeMouthStateAuditTests(unittest.TestCase):
    def _face(self, *, open_mouth: bool) -> Image.Image:
        image = Image.new("RGBA", (320, 320), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 45, 240, 255), fill=(235, 160, 95, 255))
        draw.rectangle((100, 105, 145, 135), fill=(245, 240, 225, 255))
        draw.rectangle((175, 105, 220, 135), fill=(245, 240, 225, 255))
        draw.rectangle((140, 155, 180, 190), fill=(215, 125, 65, 255))
        draw.rectangle((110, 190, 210, 255), fill=(115, 65, 30, 255))
        if open_mouth:
            draw.rectangle((130, 210, 190, 244), fill=(40, 20, 18, 255))
            draw.rectangle((134, 212, 186, 222), fill=(230, 220, 205, 255))
            draw.rectangle((145, 232, 175, 241), fill=(155, 38, 45, 255))
        else:
            draw.rectangle((130, 218, 190, 226), fill=(40, 20, 18, 255))
        return image

    def test_detects_open_and_closed_front_mouths(self):
        self.assertEqual(audit_pose("open", self._face(open_mouth=True))["mouth_state"], "open")
        self.assertEqual(
            audit_pose("closed", self._face(open_mouth=False))["mouth_state"],
            "closed",
        )

    def test_records_nonvisible_when_no_eye_geometry_exists(self):
        image = Image.new("RGBA", (320, 320), (80, 45, 25, 255))
        result = audit_pose("005_turn_back_neutral", image)
        self.assertEqual(result["mouth_state"], "not_visible")
        self.assertIsNone(result["mouth_region"])


if __name__ == "__main__":
    unittest.main()
