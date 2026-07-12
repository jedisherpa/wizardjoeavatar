import asyncio
import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand


class FrameSourceTests(unittest.TestCase):
    def test_direct_procedural_frame_source_shape(self):
        source = ProceduralWizardFrameSource(240, 135, 24)
        frame = source.render_next_frame()
        self.assertEqual(frame.raw_size, 240 * 135 * 4)
        self.assertNotEqual(frame.cells.count(b"\x00"), len(frame.cells))

    def test_async_command_and_frame(self):
        async def run():
            source = ProceduralWizardFrameSource()
            result = await source.apply_command(WizardCommand("expression", {"expression": "focused"}))
            frame = await source.next_frame()
            return result.ok, frame.raw_size

        ok, raw_size = asyncio.run(run())
        self.assertTrue(ok)
        self.assertEqual(raw_size, 240 * 135 * 4)

    def test_invalid_command_is_rejected(self):
        source = ProceduralWizardFrameSource()
        result = source.apply_command_sync(WizardCommand("expression", {"expression": "laser"}))
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
