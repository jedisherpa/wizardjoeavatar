import asyncio
import unittest

from wizard_avatar.frame_source import (
    REFERENCE_EYE_BLUE,
    REFERENCE_EYE_WHITE,
    REFERENCE_MOUTH_DARK,
    ProceduralWizardFrameSource,
)
from wizard_avatar.models import WizardCommand, WizardState
from wizard_avatar.reference_avatar import (
    reference_pose_anchor,
    reference_pose_ids,
    render_reference_pose_local,
)


def changed_points(before, after):
    return {
        (x, y)
        for y in range(before.height)
        for x in range(before.width)
        if before.get(x, y) != after.get(x, y)
    }


class FrameSourceTests(unittest.TestCase):
    def test_authored_turn_pose_owns_presented_facing(self):
        source = ProceduralWizardFrameSource()
        cases = (
            ("walk_front_right", "turn_front_to_east", "south"),
            ("turn_front_to_east_entry_50", "turn_front_to_east", "southeast"),
            ("walk_profile_right_contact_left", "turn_front_to_east", "east"),
            ("turn_front_crossover_plant", "reverse_east_to_west", "south"),
            ("turn_crossover_to_west_50", "reverse_east_to_west", "southwest"),
            ("stop_profile_left_from_left_75", "stop_left", "west"),
        )
        for pose_id, clip_id, expected in cases:
            with self.subTest(pose_id=pose_id):
                state = WizardState(pose_id=pose_id, animation_clip_id=clip_id)
                self.assertEqual(source._authored_body_facing(state), expected)

        walking = WizardState(
            pose_id="walk_profile_right_contact_left",
            animation_clip_id="walk_right",
        )
        self.assertIsNone(source._authored_body_facing(walking))

    def test_presentation_blink_latches_short_input_for_four_frames(self):
        source = ProceduralWizardFrameSource()
        previous_input = False
        remaining = 0
        source_name = "none"
        visible_frames = []
        source_names = []
        for input_active in (True, True, False, False, False):
            visible, remaining, source_name = source._resolve_presentation_blink(
                input_active=input_active,
                previous_input_active=previous_input,
                previous_frames_remaining=remaining,
                input_source="scheduler" if input_active else "none",
                previous_source=source_name,
            )
            visible_frames.append(visible)
            source_names.append(source_name)
            previous_input = input_active

        self.assertEqual(visible_frames, [True, True, True, True, False])
        self.assertEqual(source_names, ["scheduler"] * 4 + ["none"])
        self.assertEqual(remaining, 0)

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

    def test_reference_face_channels_stay_bounded_and_expression_is_visible(self):
        source = ProceduralWizardFrameSource()
        pose_id = "front_idle"
        neutral = render_reference_pose_local(pose_id)
        happy = render_reference_pose_local(pose_id)
        mouth_anchor = reference_pose_anchor("front_idle", "mouth")
        source._apply_reference_face_channels(
            neutral,
            WizardState(expression="neutral"),
            pose_id,
            mouth_anchor,
        )
        source._apply_reference_face_channels(
            happy,
            WizardState(expression="happy"),
            pose_id,
            mouth_anchor,
        )

        changed = changed_points(neutral, happy)
        eye_anchors = [
            reference_pose_anchor(pose_id, "left_eye"),
            reference_pose_anchor(pose_id, "right_eye"),
        ]
        self.assertTrue(changed)
        for x, y in changed:
            near_eye = any(
                abs(x - eye_x) <= 6 and abs(y - eye_y) <= 6
                for eye_x, eye_y in eye_anchors
            )
            near_mouth = abs(x - mouth_anchor[0]) <= 6 and abs(y - mouth_anchor[1]) <= 4
            self.assertTrue(near_eye or near_mouth, (x, y))

    def test_reference_eyes_are_short_blue_centers_with_white_sides(self):
        source = ProceduralWizardFrameSource()
        pose_id = "front_idle"
        canvas = render_reference_pose_local(pose_id)
        layouts = [
            source._reference_eye_layout(canvas, reference_pose_anchor(pose_id, anchor_name))
            for anchor_name in ("left_eye", "right_eye")
        ]
        source._apply_reference_face_channels(
            canvas,
            WizardState(expression="neutral"),
            pose_id,
            reference_pose_anchor(pose_id, "mouth"),
        )

        self.assertNotIn(None, layouts)
        for eye_left, eye_top in layouts:
            eye_cells = [
                canvas.get(x, y)
                for y in range(eye_top, eye_top + 2)
                for x in range(eye_left, eye_left + 5)
            ]
            blue = [
                cell
                for cell in eye_cells
                if cell is not None and cell.rgb == REFERENCE_EYE_BLUE
            ]
            white = [
                cell
                for cell in eye_cells
                if cell is not None and cell.rgb == REFERENCE_EYE_WHITE
            ]
            self.assertEqual(len(blue), 2)
            self.assertEqual(len(white), 8)
            self.assertTrue(
                all(cell.rgb != (0, 0, 0) for cell in eye_cells if cell is not None)
            )

    def test_reference_blink_stays_inside_two_row_eye_boxes(self):
        source = ProceduralWizardFrameSource()
        pose_id = "front_idle"
        open_canvas = render_reference_pose_local(pose_id)
        blink_canvas = render_reference_pose_local(pose_id)
        layouts = [
            source._reference_eye_layout(open_canvas, reference_pose_anchor(pose_id, anchor_name))
            for anchor_name in ("left_eye", "right_eye")
        ]
        mouth_anchor = reference_pose_anchor(pose_id, "mouth")
        source._apply_reference_face_channels(
            open_canvas,
            WizardState(blink_phase=0.5),
            pose_id,
            mouth_anchor,
        )
        source._apply_reference_face_channels(
            blink_canvas,
            WizardState(blink_phase=0.99),
            pose_id,
            mouth_anchor,
        )

        allowed = {
            (x, y)
            for eye_left, eye_top in layouts
            for y in range(eye_top, eye_top + 2)
            for x in range(eye_left, eye_left + 5)
        }
        self.assertEqual(changed_points(open_canvas, blink_canvas), allowed)
        for x, y in allowed:
            cell = blink_canvas.get(x, y)
            self.assertIsNotNone(cell)
            self.assertNotIn(cell.rgb, {REFERENCE_EYE_WHITE, REFERENCE_EYE_BLUE})

    def test_head_breath_preserves_the_authored_neck_seam(self):
        source = ProceduralWizardFrameSource()
        pose_id = "front_idle"
        original = render_reference_pose_local(pose_id)
        breathed = render_reference_pose_local(pose_id)
        root_x, _ = reference_pose_anchor(pose_id, "root")
        _, mouth_y = reference_pose_anchor(pose_id, "mouth")

        source._project_reference_head(
            breathed,
            pose_id,
            pose_id,
            offset_y=-1,
        )

        seam_y = mouth_y + 8
        self.assertEqual(
            [original.get(x, seam_y) for x in range(root_x - 15, root_x + 16)],
            [breathed.get(x, seam_y) for x in range(root_x - 15, root_x + 16)],
        )

    def test_profile_blink_uses_one_bounded_visible_aperture(self):
        source = ProceduralWizardFrameSource()
        pose_id = "profile_left"
        open_canvas = render_reference_pose_local(pose_id)
        blink_canvas = render_reference_pose_local(pose_id)
        mouth_anchor = reference_pose_anchor(pose_id, "mouth")

        open_evidence = source._apply_reference_face_channels(
            open_canvas,
            WizardState(blink_phase=0.0),
            pose_id,
            mouth_anchor,
        )
        blink_evidence = source._apply_reference_face_channels(
            blink_canvas,
            WizardState(blink_phase=1.0),
            pose_id,
            mouth_anchor,
        )

        self.assertEqual(len(open_evidence.eye_apertures), 1)
        self.assertEqual(len(open_evidence.eye_blue_cells), 2)
        self.assertEqual(blink_evidence.blink_painted_cells, 6)
        self.assertTrue(changed_points(open_canvas, blink_canvas))
        aperture = open_evidence.eye_apertures[0]
        for point in open_evidence.eye_blue_cells:
            self.assertLessEqual(aperture.min_x, point.x)
            self.assertLessEqual(point.x, aperture.max_x)
            self.assertLessEqual(aperture.min_y, point.y)
            self.assertLessEqual(point.y, aperture.max_y)

    def test_reference_eye_aim_moves_only_the_blue_centers(self):
        source = ProceduralWizardFrameSource()
        pose_id = "front_idle"
        left = render_reference_pose_local(pose_id)
        right = render_reference_pose_local(pose_id)
        mouth_anchor = reference_pose_anchor(pose_id, "mouth")
        source._apply_reference_face_channels(
            left,
            WizardState(target_point={"x": -2.0, "z": 5.0}),
            pose_id,
            mouth_anchor,
        )
        source._apply_reference_face_channels(
            right,
            WizardState(target_point={"x": 2.0, "z": 5.0}),
            pose_id,
            mouth_anchor,
        )

        changed = changed_points(left, right)
        self.assertEqual(len(changed), 8)
        self.assertTrue(
            all(
                left.get(x, y).rgb in {REFERENCE_EYE_WHITE, REFERENCE_EYE_BLUE}
                for x, y in changed
            )
        )
        self.assertTrue(
            all(
                right.get(x, y).rgb in {REFERENCE_EYE_WHITE, REFERENCE_EYE_BLUE}
                for x, y in changed
            )
        )

    def test_vertical_gaze_stays_inside_the_existing_eye_aperture(self):
        source = ProceduralWizardFrameSource()
        pose_id = "front_idle"
        canvas = render_reference_pose_local(pose_id)
        layouts = [
            source._reference_eye_layout(
                canvas,
                reference_pose_anchor(pose_id, anchor_name),
            )
            for anchor_name in ("left_eye", "right_eye")
        ]
        source._apply_reference_face_channels(
            canvas,
            WizardState(gaze_authoritative=True, gaze_vertical_aim=-1),
            pose_id,
            reference_pose_anchor(pose_id, "mouth"),
        )

        for eye_left, eye_top in layouts:
            top = [canvas.get(x, eye_top) for x in range(eye_left, eye_left + 5)]
            bottom = [
                canvas.get(x, eye_top + 1) for x in range(eye_left, eye_left + 5)
            ]
            self.assertEqual(
                sum(cell.rgb == REFERENCE_EYE_BLUE for cell in top),
                1,
            )
            self.assertEqual(
                sum(cell.rgb == REFERENCE_EYE_BLUE for cell in bottom),
                0,
            )
            self.assertTrue(
                all(cell.rgb != (0, 0, 0) for cell in top + bottom)
            )

    def test_open_mouth_has_no_dark_vertical_side_columns(self):
        source = ProceduralWizardFrameSource()
        pose_id = "front_idle"
        canvas = render_reference_pose_local(pose_id)
        mouth_anchor = reference_pose_anchor(pose_id, "mouth")
        source._apply_reference_face_channels(
            canvas,
            WizardState(action="speaking", mouth="open_medium", time_seconds=0.0),
            pose_id,
            mouth_anchor,
        )

        dark_by_x = {}
        for x in range(mouth_anchor[0] - 5, mouth_anchor[0] + 6):
            dark_by_x[x] = sum(
                canvas.get(x, y) is not None and canvas.get(x, y).rgb == REFERENCE_MOUTH_DARK
                for y in range(mouth_anchor[1] - 3, mouth_anchor[1] + 2)
            )
        self.assertLessEqual(max(dark_by_x.values()), 1)
        self.assertTrue(
            any(
                canvas.get(x, y) is not None
                and canvas.get(x, y).layer_id == "reference_speaking_mouth"
                for y in range(mouth_anchor[1] - 3, mouth_anchor[1] + 2)
                for x in range(mouth_anchor[0] - 4, mouth_anchor[0] + 5)
            )
        )

    def test_media_speaking_action_uses_scheduler_mouth_without_time_override(self):
        source = ProceduralWizardFrameSource()
        expression = {"mouth": "smile"}

        for time_seconds in (0.0, 0.1, 1.7, 99.0):
            with self.subTest(time_seconds=time_seconds):
                state = WizardState(
                    action="speaking",
                    mouth="closed",
                    expression="explaining",
                    time_seconds=time_seconds,
                )
                self.assertEqual(
                    source._reference_mouth_shape(state, expression),
                    "closed",
                )

        state = WizardState(action="speaking", mouth="rounded", time_seconds=4.2)
        self.assertEqual(source._reference_mouth_shape(state, expression), "rounded")

    def test_legacy_speech_keeps_explicit_fallback_without_alignment(self):
        source = ProceduralWizardFrameSource()
        state = WizardState(
            action="speaking",
            speech_id="legacy-speech",
            speech_text="Hello, wizard.",
            speech_started_at=8.0,
            speech_until=10.0,
            speech_mouth_authority="local_fallback",
            mouth="closed",
            time_seconds=8.0,
        )
        self.assertEqual(
            source._reference_mouth_shape(state, {"mouth": "closed"}),
            "open_small",
        )

    def test_aligned_speech_mouth_is_not_replaced_by_local_fallback(self):
        source = ProceduralWizardFrameSource()
        state = WizardState(
            action="speaking",
            speech_id="speech:approved",
            speech_mouth_authority="media_alignment",
            mouth="rounded",
            time_seconds=41.0,
        )
        self.assertEqual(
            source._reference_mouth_shape(state, {"mouth": "closed"}),
            "rounded",
        )

    def test_diagnostics_report_the_projected_fallback_mouth(self):
        source = ProceduralWizardFrameSource()
        self.assertTrue(
            source.apply_command_sync(
                WizardCommand(
                    "speak",
                    {
                        "text": "Hello, world.",
                        "duration_ms": 2000,
                        "speech_id": "diagnostic-speech",
                    },
                )
            ).ok
        )
        source.advance_simulation(0.95)
        source.render_current_frame()

        diagnostics = source.diagnostics_dict()
        self.assertEqual(diagnostics["mouth_state"], "closed")
        self.assertEqual(diagnostics["mouth_command_state"], "open_small")
        self.assertEqual(diagnostics["speech_mouth_authority"], "local_fallback")

    def test_all_pose_face_edits_remain_inside_anchor_bounds(self):
        source = ProceduralWizardFrameSource()
        state = WizardState(expression="happy", blink_phase=0.5)
        for pose_id in reference_pose_ids():
            with self.subTest(pose_id=pose_id):
                before = render_reference_pose_local(pose_id)
                after = render_reference_pose_local(pose_id)
                mouth_anchor = reference_pose_anchor(pose_id, "mouth")
                eye_anchors = [
                    reference_pose_anchor(pose_id, "left_eye"),
                    reference_pose_anchor(pose_id, "right_eye"),
                ]
                source._apply_reference_face_channels(
                    after,
                    state,
                    pose_id,
                    mouth_anchor,
                )

                for x, y in changed_points(before, after):
                    near_eye = any(
                        abs(x - eye_x) <= 6 and abs(y - eye_y) <= 6
                        for eye_x, eye_y in eye_anchors
                    )
                    near_mouth = (
                        abs(x - mouth_anchor[0]) <= 6
                        and abs(y - mouth_anchor[1]) <= 4
                    )
                    self.assertTrue(near_eye or near_mouth, (pose_id, x, y))

    def test_back_pose_does_not_receive_front_face_pixels(self):
        source = ProceduralWizardFrameSource()
        pose_id = "back_idle"
        before = render_reference_pose_local(pose_id)
        after = render_reference_pose_local(pose_id)
        source._apply_reference_face_channels(
            after,
            WizardState(expression="happy", blink_phase=0.99),
            pose_id,
            reference_pose_anchor(pose_id, "mouth"),
        )
        self.assertEqual(changed_points(before, after), set())

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
