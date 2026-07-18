import hashlib
import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import DIRECTIONS, WizardCommand
from wizard_avatar.views import all_views


class ViewTests(unittest.TestCase):
    def test_all_eight_views_have_definitions(self):
        self.assertEqual(set(all_views().keys()), set(DIRECTIONS))

    def test_views_render_distinct_frames(self):
        source = ProceduralWizardFrameSource()
        hashes = set()
        for direction in DIRECTIONS:
            source.apply_command_sync(WizardCommand("face", {"direction": direction}))
            # Facing is a timed performance channel. Advance far enough for
            # the longest four-sector head turn and settle before comparing
            # the canonical authored view.
            for _ in range(24):
                source.advance_simulation(1.0 / 60.0)
                frame = source.render_current_frame()
            hashes.add(hashlib.sha256(frame.cells).hexdigest())
        self.assertGreaterEqual(len(hashes), 6)

    def test_turning_preserves_world_root(self):
        source = ProceduralWizardFrameSource()
        before = dict(source.current_state().world_position)
        source.apply_command_sync(WizardCommand("face", {"direction": "north"}))
        after = dict(source.current_state().world_position)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
