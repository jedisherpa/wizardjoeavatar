import asyncio
import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.protocol import KEYFRAME_INTERVAL, TAG_DELTA, decode_frame, encode_frame


class CodecTests(unittest.TestCase):
    def test_keyframe_round_trip(self):
        source = ProceduralWizardFrameSource()
        frame = source.render_next_frame()
        encoded = encode_frame(frame.cells, None, 0)
        index, decoded = decode_frame(encoded.message, None)
        self.assertEqual(index, 0)
        self.assertEqual(decoded, frame.cells)
        self.assertTrue(encoded.is_keyframe)

    def test_delta_round_trip(self):
        source = ProceduralWizardFrameSource()
        frame_a = source.render_next_frame()
        frame_b = source.render_next_frame()
        key = encode_frame(frame_a.cells, None, 0)
        delta = encode_frame(frame_b.cells, key.shown_frame, 1)
        index, decoded = decode_frame(delta.message, key.shown_frame)
        self.assertEqual(index, 1)
        self.assertEqual(decoded, frame_b.cells)
        self.assertIn(delta.tag, {TAG_DELTA, 1, 3, 0})

    def test_periodic_keyframe(self):
        source = ProceduralWizardFrameSource()
        frame = source.render_next_frame()
        prev = frame.cells
        encoded = encode_frame(frame.cells, prev, KEYFRAME_INTERVAL)
        self.assertTrue(encoded.is_keyframe)

    def test_source_encoded_frame_round_trip(self):
        async def run():
            source = ProceduralWizardFrameSource()
            message, frame = await source.next_encoded_frame()
            index, decoded = decode_frame(message, None)
            return index, decoded == frame.cells

        index, same = asyncio.run(run())
        self.assertEqual(index, 0)
        self.assertTrue(same)


if __name__ == "__main__":
    unittest.main()
