import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from tools.census_joeville_sprite_archives import (
    _category,
    _character_id,
    _sequence_id,
    census,
)


def _png_payload(mode: str = "RGBA") -> bytes:
    image = Image.new(mode, (12, 8), (10, 20, 30, 0) if mode == "RGBA" else "white")
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    return payload.getvalue()


class JoeVilleSpriteArchiveCensusTests(unittest.TestCase):
    def test_member_classification_is_explicit(self):
        self.assertEqual(_character_id("sheet-serena-quill-w7a.png"), "serena-quill")
        self.assertEqual(_category("sheet-serena-quill-w7a.png"), "sprite_sheet")
        self.assertEqual(_sequence_id("sheet-serena-quill-w7a.png"), "w7a")
        self.assertEqual(_character_id("char-crystail-hires.png"), "crystail")
        self.assertEqual(_character_id("vehicle-4runner-side.png"), None)

    def test_census_reports_conflicting_and_identical_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "one.zip"
            second = root / "two.zip"
            alpha_payload = _png_payload("RGBA")
            changed_payload = _png_payload("RGB")
            with zipfile.ZipFile(first, "w") as archive:
                archive.writestr("sheet-serena-quill-w1.png", alpha_payload)
                archive.writestr("sheet-thorne-vale-g1.png", alpha_payload)
            with zipfile.ZipFile(second, "w") as archive:
                archive.writestr("sheet-serena-quill-w1.png", alpha_payload)
                archive.writestr("sheet-thorne-vale-g1.png", changed_payload)

            result = census([first, second])

        duplicates = {
            record["member_name"]: record
            for record in result["duplicate_member_names"]
        }
        self.assertTrue(duplicates["sheet-serena-quill-w1.png"]["byte_identical"])
        self.assertFalse(duplicates["sheet-thorne-vale-g1.png"]["byte_identical"])
        serena = next(
            record
            for record in result["characters"]
            if record["character_id"] == "serena-quill"
        )
        self.assertEqual(serena["source_member_count"], 2)
        self.assertTrue(serena["members"][0]["has_alpha"])


if __name__ == "__main__":
    unittest.main()
