import asyncio
import unittest

from wizard_avatar.compositor import CellCanvas
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.pose_compositor import blit_pose_scaled
from wizard_avatar.reference_avatar import (
    reference_pose_anchor,
    reference_pose_root_anchor,
    render_reference_pose_local,
)


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

    def test_reference_speaking_mouth_tracks_authored_anchor(self):
        source = ProceduralWizardFrameSource()
        state = source.current_state()
        state.action = "speaking"
        state.time_seconds = 0.0
        stage = CellCanvas(120, 130)
        root_anchor = reference_pose_root_anchor("front_idle")
        mouth_anchor = reference_pose_anchor("front_idle", "mouth")
        root_screen = (60.0, 105.0)

        source._draw_reference_animation_overlays(
            stage,
            state,
            root_anchor,
            mouth_anchor,
            root_screen,
            1.0,
            1.0,
        )

        origin_x = round(root_screen[0] - root_anchor[0])
        origin_y = round(root_screen[1] - root_anchor[1])
        mouth_stage_x = origin_x + mouth_anchor[0]
        mouth_stage_y = origin_y + mouth_anchor[1]
        mouth_cells = [
            (x, y)
            for y, row in enumerate(stage.cells)
            for x, cell in enumerate(row)
            if cell is not None and cell.layer_id == "reference_speaking_mouth"
        ]

        self.assertGreater(len(mouth_cells), 0)
        self.assertLessEqual(max(abs(x - mouth_stage_x) for x, _ in mouth_cells), 3)
        self.assertLessEqual(max(y for _, y in mouth_cells), mouth_stage_y)
        self.assertGreaterEqual(min(y for _, y in mouth_cells), mouth_stage_y - 3)

    def test_open_speaking_mouth_covers_reference_brown_corner_blocks(self):
        source = ProceduralWizardFrameSource()
        state = source.current_state()
        state.action = "speaking"
        state.time_seconds = 0.0
        stage = CellCanvas(120, 130)
        root_anchor = reference_pose_root_anchor("front_idle")
        mouth_anchor = reference_pose_anchor("front_idle", "mouth")
        root_screen = (60.0, 105.0)

        blit_pose_scaled(
            stage,
            render_reference_pose_local("front_idle"),
            root_anchor,
            root_screen,
            1.0,
            1.0,
        )
        source._draw_reference_animation_overlays(
            stage,
            state,
            root_anchor,
            mouth_anchor,
            root_screen,
            1.0,
            1.0,
        )

        origin_x = round(root_screen[0] - root_anchor[0])
        origin_y = round(root_screen[1] - root_anchor[1])
        mouth_stage_x = origin_x + mouth_anchor[0]
        upper_mouth_y = origin_y + mouth_anchor[1] - 3

        allowed_layers = {"reference_mouth_clear", "reference_speaking_mouth", "reference_teeth"}
        for y in range(upper_mouth_y, origin_y + mouth_anchor[1] + 2):
            for x in range(mouth_stage_x - 5, mouth_stage_x + 6):
                cell = stage.get(x, y)
                self.assertIsNotNone(cell)
                self.assertIn(cell.layer_id, allowed_layers)

        for x in range(mouth_stage_x - 2, mouth_stage_x + 3):
            cell = stage.get(x, upper_mouth_y)
            self.assertIsNotNone(cell)
            self.assertEqual(cell.layer_id, "reference_teeth")

    def test_scaled_open_speaking_mouth_covers_reference_brown_columns(self):
        source = ProceduralWizardFrameSource()
        state = source.current_state()
        state.action = "speaking"
        state.time_seconds = 0.0
        stage = CellCanvas(240, 230)
        root_anchor = reference_pose_root_anchor("front_idle")
        mouth_anchor = reference_pose_anchor("front_idle", "mouth")
        root_screen = (120.0, 205.0)
        scale = 2.0
        horizontal_scale = 1.18

        blit_pose_scaled(
            stage,
            render_reference_pose_local("front_idle"),
            root_anchor,
            root_screen,
            scale,
            horizontal_scale,
        )
        source._draw_reference_animation_overlays(
            stage,
            state,
            root_anchor,
            mouth_anchor,
            root_screen,
            scale,
            horizontal_scale,
        )

        scale_x = scale * horizontal_scale
        origin_x = root_screen[0] - root_anchor[0] * scale_x
        origin_y = root_screen[1] - root_anchor[1] * scale
        allowed_layers = {"reference_mouth_clear", "reference_speaking_mouth", "reference_teeth"}
        for lx in range(mouth_anchor[0] - 5, mouth_anchor[0] + 6):
            for ly in range(mouth_anchor[1] - 3, mouth_anchor[1] + 2):
                start_x = round(origin_x + lx * scale_x)
                end_x = max(start_x, round(origin_x + (lx + 1) * scale_x) - 1)
                start_y = round(origin_y + ly * scale)
                end_y = max(start_y, round(origin_y + (ly + 1) * scale) - 1)
                for y in range(start_y, end_y + 1):
                    for x in range(start_x, end_x + 1):
                        cell = stage.get(x, y)
                        self.assertIsNotNone(cell)
                        self.assertIn(cell.layer_id, allowed_layers)

    def test_reference_pose_preserves_authored_eye_pixels(self):
        for pose_id in ("front_idle", "walk_front_left", "walk_front_right", "explaining", "magic_cast"):
            source = ProceduralWizardFrameSource()
            authored = render_reference_pose_local(pose_id)
            sampled, _, _ = source._reference_pose_canvas_for_sample(pose_id)

            for anchor_name in ("left_eye", "right_eye"):
                eye_x, eye_y = reference_pose_anchor(pose_id, anchor_name)
                for y in range(eye_y - 3, eye_y + 4):
                    for x in range(eye_x - 4, eye_x + 5):
                        self.assertEqual(sampled.get(x, y), authored.get(x, y))


if __name__ == "__main__":
    unittest.main()
