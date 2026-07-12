from __future__ import annotations

import asyncio
import math
import struct
from typing import Optional, Tuple

from .compositor import CellCanvas, blit_scaled
from .controller import WizardAvatarController
from .diagnostics import FrameDiagnostics
from .floor import build_background
from .layers import ROOT_ANCHOR, render_wizard_local
from .models import Cell, CommandResult, WizardCellFrame, WizardCommand, WizardState
from .palette import ENV_RGB, RGB
from .projection import project_quantized
from .protocol import EncodedFrame, encode_frame
from .reference_avatar import (
    REFERENCE_SCALE_MULTIPLIER,
    reference_avatar_available,
    reference_root_anchor,
    render_reference_avatar_local,
)
from .shadow import draw_contact_shadow


class ProceduralWizardFrameSource:
    def __init__(self, cols: int = 240, rows: int = 135, fps: float = 24.0) -> None:
        self.cols = int(cols)
        self.rows = int(rows)
        self.fps = float(fps)
        self.controller = WizardAvatarController()
        self.frame_index = 0
        self._prev_encoded_frame: Optional[bytes] = None
        self.diagnostics = FrameDiagnostics(fps=self.fps)

    async def next_frame(self) -> WizardCellFrame:
        await asyncio.sleep(0)
        return self.render_next_frame()

    def render_next_frame(self) -> WizardCellFrame:
        self.controller.advance(1.0 / self.fps)
        return self._render_current_frame()

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
        render_scale = scale
        use_reference_avatar = reference_avatar_available() and state.facing == "south"
        if use_reference_avatar:
            stage = CellCanvas(self.cols, self.rows, Cell(" ", ENV_RGB["background"], "background"))
        else:
            stage = build_background(self.cols, self.rows).copy()
        lifted = state.locomotion == "walking" and 0.15 < state.walk_phase < 0.38
        root_screen = (sx, sy)
        if use_reference_avatar:
            render_scale = scale * REFERENCE_SCALE_MULTIPLIER
            bob = 0.0
            if state.locomotion == "walking":
                bob += math.sin(state.walk_phase * math.tau) * 1.8
            if state.action in {"speaking", "explaining"}:
                bob += math.sin(state.time_seconds * 12.0) * 0.7
            root_screen = (sx, min(self.rows - 8, sy + 18 * render_scale + bob))
            local = render_reference_avatar_local()
            root_anchor = reference_root_anchor()
        else:
            local = render_wizard_local(state)
            root_anchor = ROOT_ANCHOR
        state.display_scale = render_scale
        draw_contact_shadow(stage, root_screen[0], root_screen[1], render_scale, lifted=lifted)
        blit_scaled(stage, local, root_anchor, root_screen, render_scale)
        if use_reference_avatar:
            self._draw_reference_animation_overlays(stage, state, root_anchor, root_screen, render_scale)
        cells = stage.to_frame_bytes()
        frame = WizardCellFrame(
            cols=self.cols,
            rows=self.rows,
            frame_index=self.frame_index,
            cells=cells,
            raw_size=len(cells),
        )
        return frame

    def _draw_reference_animation_overlays(
        self,
        stage: CellCanvas,
        state: WizardState,
        root_anchor: Tuple[int, int],
        root_screen: Tuple[float, float],
        scale: float,
    ) -> None:
        origin_x = root_screen[0] - root_anchor[0] * scale
        origin_y = root_screen[1] - root_anchor[1] * scale

        def stage_point(local_x: float, local_y: float) -> Tuple[int, int]:
            return round(origin_x + local_x * scale), round(origin_y + local_y * scale)

        if state.action == "speaking" or state.speech_id is not None:
            open_mouth = int(state.time_seconds * 10) % 2 == 0
            mouth_color = (132, 30, 22) if open_mouth else (78, 39, 20)
            for lx in range(34, 41):
                for ly in range(35, 37 if open_mouth else 36):
                    x, y = stage_point(lx, ly)
                    stage.set(x, y, "#", mouth_color, "reference_speaking_mouth")
            if open_mouth:
                for lx in range(35, 40):
                    x, y = stage_point(lx, 34)
                    stage.set(x, y, "#", (250, 238, 209), "reference_teeth")

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

    async def next_encoded_frame(self, codec: str = "adaptive") -> Tuple[bytes, WizardCellFrame]:
        frame = await self.next_frame()
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
        }
