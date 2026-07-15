from __future__ import annotations

import asyncio
import math
import struct
from pathlib import Path
from typing import Optional, Tuple

from .character_package import WIZARD_JOE_PACKAGE_PATH, load_character_package
from .compositor import CellCanvas, blit_scaled
from .controller import WizardAvatarController
from .crystail import (
    CRYSTAIL_CHARACTER_ID,
    CRYSTAIL_SCALE_MULTIPLIER,
    resolve_crystail_pose_id,
)
from .diagnostics import FrameDiagnostics
from .direct_cell_character import (
    DirectCellRuntimeProfile,
    load_direct_cell_runtime_profile,
    resolve_direct_cell_blink_pose_id,
    resolve_direct_cell_pose_id,
    resolve_direct_cell_speech_pose_id,
    validate_direct_cell_runtime_profile,
)
from .floor import build_background
from .layers import ROOT_ANCHOR, render_wizard_local
from .models import Cell, CommandResult, WizardCellFrame, WizardCommand, WizardState
from .palette import ENV_RGB, RGB
from .pose_compositor import (
    blit_pose_scaled,
    copy_pose_canvas,
)
from .pose_selection import select_reference_pose_sample
from .projection import project_quantized
from .protocol import EncodedFrame, encode_frame
from .reference_avatar import (
    REFERENCE_SCALE_MULTIPLIER,
    reference_pose_anchor,
    reference_pose_ids,
    reference_pose_library_available,
    reference_pose_root_anchor,
    render_reference_pose_local,
)
from .shadow import draw_contact_shadow


REFERENCE_POSE_HORIZONTAL_SCALE = 1.18
REFERENCE_MOUTH_OPEN = (132, 30, 22)
REFERENCE_MOUTH_DARK = (78, 39, 20)
REFERENCE_TEETH = (250, 238, 209)


class ProceduralWizardFrameSource:
    def __init__(
        self,
        cols: int = 240,
        rows: int = 135,
        fps: float = 24.0,
        character_package_path: Optional[Path] = None,
    ) -> None:
        self.cols = int(cols)
        self.rows = int(rows)
        self.fps = float(fps)
        self.character_package = load_character_package(
            WIZARD_JOE_PACKAGE_PATH if character_package_path is None else character_package_path
        )
        self.pose_library_path = self.character_package.pose_library
        all_pose_ids = reference_pose_ids(self.pose_library_path)
        self.direct_cell_runtime_profile: Optional[DirectCellRuntimeProfile] = None
        if self.character_package.runtime_profile is not None:
            self.direct_cell_runtime_profile = load_direct_cell_runtime_profile(
                self.character_package.runtime_profile
            )
            validate_direct_cell_runtime_profile(
                self.direct_cell_runtime_profile,
                all_pose_ids,
            )
        self.pose_ids = reference_pose_ids(
            self.pose_library_path,
            pose_capable_only=self.direct_cell_runtime_profile is not None,
        )
        self.controller = WizardAvatarController(
            self.pose_ids,
            self.character_package.character_id,
        )
        self.frame_index = 0
        self._prev_encoded_frame: Optional[bytes] = None
        self.diagnostics = FrameDiagnostics(fps=self.fps)
        self._display_pose_id: Optional[str] = None
        self._transition_from_pose_id: Optional[str] = None
        self._transition_started_at_frame = 0
        self._transition_frames = max(2, round(self.fps * 0.12))

    async def next_frame(self) -> WizardCellFrame:
        await asyncio.sleep(0)
        return self.render_next_frame()

    def advance_simulation(self, seconds: float) -> None:
        self.controller.advance(seconds)

    def render_current_frame(self) -> WizardCellFrame:
        return self._render_current_frame()

    def render_next_frame(self) -> WizardCellFrame:
        self.advance_simulation(1.0 / self.fps)
        return self.render_current_frame()

    def _render_current_frame(self) -> WizardCellFrame:
        state = self.controller.current_state()
        sx, sy, scale = project_quantized(
            state.world_position["x"],
            state.world_position["z"],
            self.cols,
            self.rows,
        )
        state.screen_position["x"] = sx
        state.screen_position["y"] = sy
        if self.character_package.character_id == CRYSTAIL_CHARACTER_ID:
            return self._render_crystail_frame(state, sx, sy, scale)
        if self.direct_cell_runtime_profile is not None:
            return self._render_direct_cell_character_frame(state, sx, sy, scale)
        use_reference_pose_library = reference_pose_library_available(self.pose_library_path)
        if use_reference_pose_library:
            stage = build_background(self.cols, self.rows).copy()
            altitude_scale = max(0.76, 1.0 - state.altitude * 0.07)
            render_scale = scale * REFERENCE_SCALE_MULTIPLIER * altitude_scale
            pose_sample = select_reference_pose_sample(state, self.pose_ids)
            pose_id = pose_sample.pose_id
            local, root_anchor, mouth_anchor = self._reference_pose_canvas_for_sample(
                pose_id,
            )
            root_screen = self._reference_root_screen(sx, sy, state, render_scale)
        else:
            stage = build_background(self.cols, self.rows).copy()
            render_scale = scale
            pose_id = None
            local = render_wizard_local(state)
            root_anchor = ROOT_ANCHOR
            mouth_anchor = None
            root_screen = (sx, sy)
        state.last_pose_id = state.pose_id
        state.pose_id = pose_id or "procedural"
        lifted = state.airborne or (state.locomotion == "walking" and 0.15 < state.walk_phase < 0.38)
        state.display_scale = render_scale
        shadow_root = (
            root_screen[0],
            root_screen[1] + state.altitude * 8.0 * render_scale,
        )
        draw_contact_shadow(stage, shadow_root[0], shadow_root[1], render_scale, lifted=lifted)
        if pose_id is not None:
            blit_pose_scaled(
                stage,
                local,
                root_anchor,
                root_screen,
                render_scale,
                REFERENCE_POSE_HORIZONTAL_SCALE,
            )
            self._draw_reference_animation_overlays(
                stage,
                state,
                root_anchor,
                mouth_anchor,
                root_screen,
                render_scale,
                REFERENCE_POSE_HORIZONTAL_SCALE,
                pose_id,
            )
        else:
            blit_scaled(stage, local, root_anchor, root_screen, render_scale)
        cells = stage.to_frame_bytes()
        frame = WizardCellFrame(
            cols=self.cols,
            rows=self.rows,
            frame_index=self.frame_index,
            cells=cells,
            raw_size=len(cells),
        )
        return frame

    def _render_crystail_frame(
        self,
        state: WizardState,
        sx: float,
        sy: float,
        projected_scale: float,
    ) -> WizardCellFrame:
        stage = build_background(self.cols, self.rows).copy()
        altitude_scale = max(0.78, 1.0 - state.altitude * 0.055)
        render_scale = projected_scale * CRYSTAIL_SCALE_MULTIPLIER * altitude_scale
        pose_id = resolve_crystail_pose_id(state)
        local = render_reference_pose_local(pose_id, self.pose_library_path)
        root_anchor = reference_pose_root_anchor(pose_id, self.pose_library_path)
        root_screen = self._reference_root_screen(sx, sy, state, render_scale)
        state.last_pose_id = state.pose_id
        state.pose_id = pose_id
        state.pose_transition_progress = 1.0
        state.display_scale = render_scale
        lifted = state.airborne or pose_id in {"jump_airborne", "fall", "hover_up", "hover_down", "glide", "takeoff"}
        shadow_root = (root_screen[0], root_screen[1] + state.altitude * 8.0 * render_scale)
        draw_contact_shadow(stage, shadow_root[0], shadow_root[1], render_scale, lifted=lifted)
        blit_scaled(stage, local, root_anchor, root_screen, render_scale)
        if state.action == "magic_cast":
            try:
                mouth_anchor = reference_pose_anchor(pose_id, "mouth", self.pose_library_path)
            except KeyError:
                mouth_anchor = root_anchor
            self._draw_reference_animation_overlays(
                stage,
                state,
                root_anchor,
                mouth_anchor,
                root_screen,
                render_scale,
                1.0,
                pose_id,
            )
        cells = stage.to_frame_bytes()
        return WizardCellFrame(
            cols=self.cols,
            rows=self.rows,
            frame_index=self.frame_index,
            cells=cells,
            raw_size=len(cells),
        )

    def _render_direct_cell_character_frame(
        self,
        state: WizardState,
        sx: float,
        sy: float,
        projected_scale: float,
    ) -> WizardCellFrame:
        profile = self.direct_cell_runtime_profile
        if profile is None:  # pragma: no cover - guarded by caller.
            raise RuntimeError("direct-cell runtime profile is not loaded")
        stage = build_background(self.cols, self.rows).copy()
        altitude_scale = max(0.78, 1.0 - state.altitude * 0.055)
        render_scale = projected_scale * profile.scale_multiplier * altitude_scale
        pose_id = resolve_direct_cell_pose_id(state, profile, self.pose_ids)
        local = render_reference_pose_local(pose_id, self.pose_library_path)
        root_anchor = reference_pose_root_anchor(pose_id, self.pose_library_path)
        self._apply_direct_cell_face_channels(local, pose_id, state, profile)
        root_screen = self._reference_root_screen(sx, sy, state, render_scale)
        state.last_pose_id = state.pose_id
        state.pose_id = pose_id
        state.pose_transition_progress = 1.0
        state.display_scale = render_scale
        lifted = state.airborne or pose_id in {
            "jump_airborne", "fall", "hover_up", "hover_down", "glide", "takeoff"
        }
        shadow_root = (
            root_screen[0],
            root_screen[1] + state.altitude * 8.0 * render_scale,
        )
        draw_contact_shadow(stage, shadow_root[0], shadow_root[1], render_scale, lifted=lifted)
        blit_scaled(stage, local, root_anchor, root_screen, render_scale)
        cells = stage.to_frame_bytes()
        return WizardCellFrame(
            cols=self.cols,
            rows=self.rows,
            frame_index=self.frame_index,
            cells=cells,
            raw_size=len(cells),
        )

    def _apply_direct_cell_face_channels(
        self,
        target: CellCanvas,
        target_pose_id: str,
        state: WizardState,
        profile: DirectCellRuntimeProfile,
    ) -> None:
        """Compose authored speech and blink regions over the current body.

        Face channels use pose-local anchors, so speaking never replaces a
        walking, action, expression, or journal body pose. Back-facing views
        intentionally retain their authored hidden face rather than receiving
        a front-view patch.
        """
        if state.facing in {"north", "northeast", "northwest"}:
            return
        speech_pose_id = resolve_direct_cell_speech_pose_id(state, profile, self.pose_ids)
        if speech_pose_id is not None:
            self._copy_direct_cell_feature(
                target,
                target_pose_id,
                speech_pose_id,
                "mouth",
                left=6,
                right=6,
                above=4,
                below=3,
            )
        blink_pose_id = resolve_direct_cell_blink_pose_id(state, profile, self.pose_ids)
        if blink_pose_id is not None and blink_pose_id != profile.blink_poses.get("open"):
            open_pose_id = profile.blink_poses.get("open")
            if open_pose_id is None:
                return
            for eye_anchor in ("left_eye", "right_eye"):
                self._copy_direct_cell_feature_delta(
                    target,
                    target_pose_id,
                    blink_pose_id,
                    open_pose_id,
                    eye_anchor,
                    left=3,
                    right=3,
                    above=2,
                    below=2,
                )

    def _copy_direct_cell_feature(
        self,
        target: CellCanvas,
        target_pose_id: str,
        donor_pose_id: str,
        anchor_name: str,
        *,
        left: int,
        right: int,
        above: int,
        below: int,
    ) -> None:
        target_anchor = reference_pose_anchor(
            target_pose_id, anchor_name, self.pose_library_path
        )
        donor_anchor = reference_pose_anchor(
            donor_pose_id, anchor_name, self.pose_library_path
        )
        donor = render_reference_pose_local(donor_pose_id, self.pose_library_path)
        for dy in range(-above, below + 1):
            for dx in range(-left, right + 1):
                target_x, target_y = target_anchor[0] + dx, target_anchor[1] + dy
                donor_cell = donor.get(donor_anchor[0] + dx, donor_anchor[1] + dy)
                target.clear_cell(target_x, target_y)
                if donor_cell is not None:
                    target.set(
                        target_x,
                        target_y,
                        donor_cell.glyph,
                        donor_cell.rgb,
                        "direct_cell_face:{}".format(donor_pose_id),
                    )

    def _copy_direct_cell_feature_delta(
        self,
        target: CellCanvas,
        target_pose_id: str,
        donor_pose_id: str,
        reference_pose_id: str,
        anchor_name: str,
        *,
        left: int,
        right: int,
        above: int,
        below: int,
    ) -> None:
        """Apply only authored differences, preserving the target face/view."""
        target_anchor = reference_pose_anchor(
            target_pose_id, anchor_name, self.pose_library_path
        )
        donor_anchor = reference_pose_anchor(
            donor_pose_id, anchor_name, self.pose_library_path
        )
        reference_anchor = reference_pose_anchor(
            reference_pose_id, anchor_name, self.pose_library_path
        )
        donor = render_reference_pose_local(donor_pose_id, self.pose_library_path)
        reference = render_reference_pose_local(reference_pose_id, self.pose_library_path)
        for dy in range(-above, below + 1):
            for dx in range(-left, right + 1):
                donor_cell = donor.get(donor_anchor[0] + dx, donor_anchor[1] + dy)
                reference_cell = reference.get(
                    reference_anchor[0] + dx,
                    reference_anchor[1] + dy,
                )
                if not self._direct_cell_feature_changed(donor_cell, reference_cell):
                    continue
                target_x, target_y = target_anchor[0] + dx, target_anchor[1] + dy
                if donor_cell is None:
                    target.clear_cell(target_x, target_y)
                else:
                    target.set(
                        target_x,
                        target_y,
                        donor_cell.glyph,
                        donor_cell.rgb,
                        "direct_cell_blink:{}".format(donor_pose_id),
                    )

    @staticmethod
    def _direct_cell_feature_changed(
        donor_cell: Optional[Cell],
        reference_cell: Optional[Cell],
    ) -> bool:
        if donor_cell is None or reference_cell is None:
            return donor_cell is not reference_cell
        return max(
            abs(donor - reference)
            for donor, reference in zip(donor_cell.rgb, reference_cell.rgb)
        ) >= 18

    def _reference_pose_canvas_for_sample(
        self,
        pose_id: str,
    ) -> tuple[CellCanvas, Tuple[int, int], Tuple[int, int]]:
        target_canvas = copy_pose_canvas(
            render_reference_pose_local(pose_id, self.pose_library_path)
        )
        target_root = reference_pose_root_anchor(pose_id, self.pose_library_path)
        try:
            target_mouth = reference_pose_anchor(pose_id, "mouth", self.pose_library_path)
        except KeyError:
            target_mouth = target_root

        if pose_id != self._display_pose_id:
            self._transition_from_pose_id = self._display_pose_id
            self._transition_started_at_frame = self.frame_index
            self._display_pose_id = pose_id
        # Authored square-cell sprites are atomic presentation snapshots. A
        # partial per-cell dissolve creates false limbs and facial artifacts;
        # root anchoring and fixed-tick motion carry continuity between them.
        self.current_state().pose_transition_progress = 1.0
        self._transition_from_pose_id = None
        return target_canvas, target_root, target_mouth

    def _reference_root_screen(
        self,
        sx: float,
        sy: float,
        state: WizardState,
        render_scale: float,
    ) -> Tuple[float, float]:
        ground_y = min(self.rows - 8, sy + 18 * render_scale)
        return sx, ground_y - state.altitude * 8.0 * render_scale

    def _draw_reference_animation_overlays(
        self,
        stage: CellCanvas,
        state: WizardState,
        root_anchor: Tuple[int, int],
        mouth_anchor: Optional[Tuple[int, int]],
        root_screen: Tuple[float, float],
        scale: float,
        horizontal_scale: float = 1.0,
        pose_id: Optional[str] = None,
    ) -> None:
        scale_x = scale * horizontal_scale
        origin_x = root_screen[0] - root_anchor[0] * scale_x
        origin_y = root_screen[1] - root_anchor[1] * scale

        def stage_point(local_x: float, local_y: float) -> Tuple[int, int]:
            return round(origin_x + local_x * scale_x), round(origin_y + local_y * scale)

        def stage_cell(local_x: int, local_y: int, color: Tuple[int, int, int], layer_id: str) -> None:
            start_x = round(origin_x + local_x * scale_x)
            end_x = max(start_x, round(origin_x + (local_x + 1) * scale_x) - 1)
            start_y = round(origin_y + local_y * scale)
            end_y = max(start_y, round(origin_y + (local_y + 1) * scale) - 1)
            for y in range(start_y, end_y + 1):
                for x in range(start_x, end_x + 1):
                    stage.set(x, y, "#", color, layer_id)

        if state.action == "speaking" or state.speech_id is not None:
            open_mouth = int(state.time_seconds * 10) % 2 == 0
            mouth_color = REFERENCE_MOUTH_OPEN if open_mouth else REFERENCE_MOUTH_DARK
            anchor_x, anchor_y = mouth_anchor or (root_anchor[0], 36)
            mouth_left = anchor_x - 3
            mouth_right = anchor_x + 3
            mouth_top = anchor_y - 2
            mouth_bottom = anchor_y if open_mouth else mouth_top
            if open_mouth:
                for lx in range(anchor_x - 5, anchor_x + 6):
                    for ly in range(anchor_y - 3, anchor_y + 2):
                        stage_cell(lx, ly, REFERENCE_MOUTH_DARK, "reference_mouth_clear")
            for lx in range(mouth_left, mouth_right + 1):
                for ly in range(mouth_top, mouth_bottom + 1):
                    stage_cell(lx, ly, mouth_color, "reference_speaking_mouth")
            if open_mouth:
                for lx in range(anchor_x - 2, anchor_x + 3):
                    stage_cell(lx, anchor_y - 3, REFERENCE_TEETH, "reference_teeth")

        if state.action in {"magic_cast", "reaction"}:
            phase = state.time_seconds * math.tau * 1.4
            cx, cy = stage_point(65, 12)
            for idx in range(14):
                angle = phase + idx * math.tau / 14.0
                radius = 4 + (idx % 3)
                x = round(cx + math.cos(angle) * radius)
                y = round(cy + math.sin(angle) * radius * 0.7)
                color = RGB["cyan_magic"] if idx % 2 else RGB["gold_light"]
                stage.set(x, y, "#", color, "reference_magic_spark")

        if state.action == "thinking":
            for offset, color in enumerate([(38, 156, 210), (255, 210, 48), (38, 156, 210)]):
                x, y = stage_point(47 + offset * 2, 18 - math.sin(state.time_seconds * 4 + offset) * 2)
                stage.set(x, y, "#", color, "reference_thinking_bubble")

    async def next_encoded_frame(
        self,
        codec: str = "adaptive",
        advance: bool = True,
    ) -> Tuple[bytes, WizardCellFrame]:
        if advance:
            frame = await self.next_frame()
        else:
            await asyncio.sleep(0)
            frame = self.render_current_frame()
        if codec == "adaptive":
            encoded = encode_frame(frame.cells, self._prev_encoded_frame, frame.frame_index)
            self._prev_encoded_frame = encoded.shown_frame
            frame.codec_tag = encoded.tag
            frame.changed_cells = encoded.changed_cells
            frame.encoded_size = encoded.encoded_size
            frame.is_keyframe = encoded.is_keyframe
            self._update_diagnostics(frame, encoded)
            self.frame_index += 1
            return encoded.message, frame
        message = struct.pack(">I", frame.frame_index) + frame.cells
        frame.codec_tag = 0
        frame.encoded_size = len(message)
        self._prev_encoded_frame = frame.cells
        self._update_diagnostics(frame, None)
        self.frame_index += 1
        return message, frame

    def _update_diagnostics(self, frame: WizardCellFrame, encoded: Optional[EncodedFrame]) -> None:
        self.diagnostics.frame_sequence = frame.frame_index
        self.diagnostics.codec_tag = frame.codec_tag
        self.diagnostics.raw_frame_size = frame.raw_size
        self.diagnostics.encoded_frame_size = frame.encoded_size
        self.diagnostics.delta_cell_count = frame.changed_cells
        self.diagnostics.fps = self.fps
        if frame.is_keyframe:
            self.diagnostics.keyframe_count += 1
        if frame.raw_size:
            self.diagnostics.bandwidth_ratio = frame.encoded_size / frame.raw_size

    def current_state(self) -> WizardState:
        return self.controller.current_state()

    async def apply_command(self, command: WizardCommand) -> CommandResult:
        await asyncio.sleep(0)
        return self.controller.apply_command(command)

    def apply_command_sync(self, command: WizardCommand) -> CommandResult:
        return self.controller.apply_command(command)

    def reset_encoder(self) -> None:
        self._prev_encoded_frame = None
        self.current_state().reconnect_count += 1
        self.diagnostics.reconnect_count += 1

    def diagnostics_dict(self):
        state = self.current_state().as_public_dict()
        return {
            **self.diagnostics.as_dict(),
            "world_x": state["world_position"]["x"],
            "world_z": state["world_position"]["z"],
            "screen_x": state["screen_position"]["x"],
            "screen_y": state["screen_position"]["y"],
            "display_scale": state["display_scale"],
            "facing": state["facing"],
            "velocity": state["velocity"],
            "target_point": state["target_point"],
            "walk_phase": state["walk_phase"],
            "current_action": state["action"],
            "current_expression": state["expression"],
            "mouth_state": state["mouth"],
            "pose_id": state["pose_id"],
            "last_pose_id": state["last_pose_id"],
            "pose_transition_progress": state["pose_transition_progress"],
            "simulation_tick": state["simulation_tick"],
            "animation_clip_id": state["animation_clip_id"],
            "animation_node_id": state["animation_node_id"],
            "mobility_mode": state["mobility_mode"],
            "airborne": state["airborne"],
            "altitude": state["altitude"],
            "control_source": state["control_source"],
            "semantic_cue": state["semantic_cue"],
        }


def _smoothstep(progress: float) -> float:
    t = max(0.0, min(1.0, progress))
    return t * t * (3.0 - 2.0 * t)
