from __future__ import annotations

import asyncio
import copy
import math
import struct
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from .character_package import WIZARD_JOE_PACKAGE_PATH, load_character_package
from .animation_graph import (
    AnimationGraph,
    AnimationGraphValidationError,
    load_animation_graph,
)
from .compositor import CellCanvas, blit_scaled
from .controller import WizardAvatarController
from .diagnostics import FrameDiagnostics
from .expressions import get_expression
from .floor import build_background
from .layers import ROOT_ANCHOR, render_wizard_local
from .models import (
    Cell,
    CommandResult,
    WizardCellFrame,
    WizardCommand,
    WizardPresentationState,
    WizardState,
)
from .palette import ENV_RGB, RGB
from .pose_compositor import (
    blit_pose_scaled,
    clear_authored_staff,
    copy_pose_canvas,
    touch_up_staff_occlusion,
)
from .pose_selection import select_reference_pose_sample
from .projection import project_quantized
from .permission_world import PermissionWorldRenderPolicyV1
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
REFERENCE_EYE_WHITE = (242, 242, 242)
REFERENCE_EYE_BLUE = (11, 76, 142)
REFERENCE_SKIN = (234, 167, 75)
REFERENCE_BROW = (108, 55, 26)


@dataclass(frozen=True)
class WizardRenderSnapshot:
    """Complete immutable-input presentation snapshot for the render worker."""

    state: WizardState
    permission_world: Optional[PermissionWorldRenderPolicyV1]


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
        self.character_package_path = Path(
            WIZARD_JOE_PACKAGE_PATH if character_package_path is None else character_package_path
        ).resolve()
        self.character_package = load_character_package(self.character_package_path)
        try:
            self.animation_graph: Optional[AnimationGraph] = load_animation_graph(
                self.character_package.animation_graph
            )
        except AnimationGraphValidationError:
            # Generic character packages may still carry the legacy/minimal
            # graph accepted by the package loader. Permission rendering must
            # not make Wizard Joe's v2 graph a cross-character requirement.
            self.animation_graph = None
        self.pose_library_path = self.character_package.pose_library
        self.pose_ids = reference_pose_ids(self.pose_library_path)
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
        self._last_presentation_state: Optional[WizardPresentationState] = None
        self._initialize_authoritative_animation_state()

    def _initialize_authoritative_animation_state(self) -> None:
        """Resolve the package's initial semantic animation before runtime hashing."""

        self.resolve_authoritative_animation_state()

    def resolve_authoritative_animation_state(self) -> None:
        """Update semantic pose selection outside the presentation renderer."""

        state = self.controller.current_state()
        derived = copy.deepcopy(state)
        sample = select_reference_pose_sample(
            derived,
            self.pose_ids,
            self.character_package.animation_graph,
        )
        if state.pose_id != sample.pose_id:
            state.last_pose_id = state.pose_id
        state.pose_id = sample.pose_id
        state.animation_clip_id = derived.animation_clip_id
        state.animation_clip_tick = derived.animation_clip_tick
        state.animation_node_id = derived.animation_node_id
        state.animation_transition_id = derived.animation_transition_id

    async def next_frame(self) -> WizardCellFrame:
        await asyncio.sleep(0)
        return self.render_next_frame()

    def advance_simulation(self, seconds: float) -> None:
        self.controller.advance(seconds)
        self.resolve_authoritative_animation_state()

    def render_current_frame(self) -> WizardCellFrame:
        return self._render_current_frame()

    def capture_render_state(self) -> WizardRenderSnapshot:
        """Capture the authoritative simulation state for off-thread rendering."""

        return WizardRenderSnapshot(
            state=copy.deepcopy(self.controller.current_state()),
            permission_world=self.controller.permission_world_render_policy,
        )

    def render_captured_frame(
        self,
        state: WizardRenderSnapshot | WizardState,
    ) -> WizardCellFrame:
        """Render a previously captured state without reading live simulation state."""

        return self._render_current_frame(state)

    def render_next_frame(self) -> WizardCellFrame:
        self.advance_simulation(1.0 / self.fps)
        return self.render_current_frame()

    def _render_current_frame(
        self,
        captured_state: Optional[WizardRenderSnapshot | WizardState] = None,
    ) -> WizardCellFrame:
        if captured_state is None:
            authoritative_state = self.controller.current_state()
            permission_world = self.controller.permission_world_render_policy
        elif type(captured_state) is WizardRenderSnapshot:
            authoritative_state = captured_state.state
            permission_world = captured_state.permission_world
        else:
            authoritative_state = captured_state
            permission_world = None
        state = copy.deepcopy(authoritative_state)
        state.reconcile_compatibility_state()
        sx, sy, scale = project_quantized(
            state.world_position["x"],
            state.world_position["z"],
            self.cols,
            self.rows,
        )
        state.screen_position = {"x": sx, "y": sy}
        previous_pose_id = self._display_pose_id or state.pose_id
        use_reference_pose_library = reference_pose_library_available(self.pose_library_path)
        if use_reference_pose_library:
            stage = self._permissioned_stage(permission_world)
            altitude_scale = max(0.76, 1.0 - state.altitude * 0.07)
            render_scale = scale * REFERENCE_SCALE_MULTIPLIER * altitude_scale
            pose_sample = select_reference_pose_sample(
                state,
                self.pose_ids,
                self.character_package.animation_graph,
            )
            pose_id = self._permissioned_pose_id(
                pose_sample.pose_id,
                state,
                permission_world,
            )
            local, root_anchor, mouth_anchor = self._reference_pose_canvas_for_sample(
                pose_id,
            )
            self._apply_reference_permission_surfaces(
                local,
                pose_id,
                permission_world,
            )
            self._apply_reference_face_channels(local, state, pose_id, mouth_anchor)
            root_screen = self._reference_root_screen(sx, sy, state, render_scale)
        else:
            stage = self._permissioned_stage(permission_world)
            render_scale = scale
            pose_id = None
            local = render_wizard_local(state)
            root_anchor = ROOT_ANCHOR
            mouth_anchor = None
            root_screen = (sx, sy)
        state.last_pose_id = previous_pose_id
        state.pose_id = pose_id or "procedural"
        lifted = state.airborne or (state.locomotion == "walking" and 0.15 < state.walk_phase < 0.38)
        state.display_scale = render_scale
        shadow_root = (
            root_screen[0],
            root_screen[1] + state.altitude * 8.0 * render_scale,
        )
        if self._permission_surface_visible(
            permission_world,
            "world_state",
            "default",
        ):
            draw_contact_shadow(
                stage,
                shadow_root[0],
                shadow_root[1],
                render_scale,
                lifted=lifted,
            )
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
                permission_world,
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
        self._last_presentation_state = WizardPresentationState(
            screen_x=sx,
            screen_y=sy,
            display_scale=render_scale,
            pose_id=state.pose_id,
            last_pose_id=state.last_pose_id,
            pose_transition_progress=state.pose_transition_progress,
            animation_clip_id=state.animation_clip_id,
            animation_node_id=state.animation_node_id,
            animation_transition_id=state.animation_transition_id,
        )
        return frame

    def _permissioned_stage(
        self,
        policy: Optional[PermissionWorldRenderPolicyV1],
    ) -> CellCanvas:
        if self._permission_surface_visible(policy, "world_state", "default"):
            return build_background(self.cols, self.rows).copy()
        return CellCanvas(self.cols, self.rows)

    @staticmethod
    def _permission_surface_visible(
        policy: Optional[PermissionWorldRenderPolicyV1],
        surface_class: str,
        surface_id: str,
    ) -> bool:
        """Preserve intrinsic pixels unless current authority manages the surface."""

        if policy is None or policy.source_state_sha256 is None:
            return True
        managed, visible = {
            "world_state": (
                policy.managed_world_states,
                policy.visible_world_states,
            ),
            "effect": (policy.managed_effects, policy.visible_effects),
            "prop": (policy.managed_props, policy.visible_props),
        }[surface_class]
        return surface_id not in managed or surface_id in visible

    def _permissioned_pose_id(
        self,
        pose_id: str,
        state: WizardState,
        policy: Optional[PermissionWorldRenderPolicyV1],
    ) -> str:
        if not self._permission_surface_visible(policy, "prop", "staff"):
            # Authored poses flatten the hand, wing, and staff into one graph.
            # Resolve to the neutral graph before the staffless reconstruction
            # so denied props never expose a damaged action silhouette.
            return "front_idle"
        if self._permission_surface_visible(policy, "effect", "magic_effect"):
            return pose_id
        if self.animation_graph is None:
            return pose_id
        clip = self.animation_graph.clips.get(state.animation_clip_id)
        if clip is None or "effect" not in clip.channel_ownership:
            return pose_id
        fallback_id = str(
            self.animation_graph.fallbacks[
                "airborne_clip_id" if state.airborne else "grounded_clip_id"
            ]
        )
        fallback = self.animation_graph.clips[fallback_id]
        return fallback.samples[0].pose_id

    def _apply_reference_permission_surfaces(
        self,
        canvas: CellCanvas,
        pose_id: str,
        policy: Optional[PermissionWorldRenderPolicyV1],
    ) -> None:
        if self._permission_surface_visible(policy, "prop", "staff"):
            return
        original = canvas.copy()
        staff_tip = reference_pose_anchor(
            pose_id, "staff_tip", self.pose_library_path
        )
        staff_hand = reference_pose_anchor(
            pose_id, "staff_hand", self.pose_library_path
        )
        root_anchor = reference_pose_root_anchor(pose_id, self.pose_library_path)
        clear_authored_staff(
            canvas,
            staff_tip,
            staff_hand,
            root_anchor,
        )
        touch_up_staff_occlusion(
            canvas,
            original,
            root_anchor,
            staff_tip,
            staff_hand,
        )

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
        self._transition_from_pose_id = None
        return target_canvas, target_root, target_mouth

    def _apply_reference_face_channels(
        self,
        canvas: CellCanvas,
        state: WizardState,
        pose_id: str,
        mouth_anchor: Tuple[int, int],
    ) -> None:
        eye_layouts = []
        for anchor_name in ("left_eye", "right_eye"):
            try:
                anchor = reference_pose_anchor(pose_id, anchor_name, self.pose_library_path)
            except KeyError:
                continue
            layout = self._reference_eye_layout(canvas, anchor)
            if layout is not None:
                eye_layouts.append((anchor_name, *layout))

        # Rear views and occluded action poses still carry approximate anchors.
        # Existing cool/white eye pixels are the authority for face visibility.
        if not eye_layouts:
            return

        blink = state.blink_phase >= 0.965
        eye_aim = self._reference_eye_aim(state)
        expression = get_expression(state.expression)
        for anchor_name, eye_left, eye_top in eye_layouts:
            eye_index = 0 if anchor_name == "left_eye" else 1
            skin = self._sample_reference_skin(canvas, eye_left + 2, eye_top)
            for y in range(eye_top, eye_top + 2):
                for x in range(eye_left, eye_left + 5):
                    color = skin if blink else REFERENCE_EYE_WHITE
                    layer = "reference_blink" if blink else "reference_eye_white"
                    canvas.set(x, y, "#", color, layer)

            if blink:
                for x in range(eye_left + 1, eye_left + 4):
                    canvas.set(x, eye_top + 1, "#", REFERENCE_BROW, "reference_blink")
            else:
                blue_x = eye_left + 2 + eye_aim
                vertical_aim = max(-1, min(1, int(state.gaze_vertical_aim)))
                blue_rows = (
                    (eye_top, eye_top + 1)
                    if vertical_aim < 0
                    else (eye_top + 1, eye_top + 2)
                    if vertical_aim > 0
                    else (eye_top, eye_top + 2)
                )
                for y in range(*blue_rows):
                    canvas.set(
                        x=blue_x,
                        y=y,
                        glyph="#",
                        rgb=REFERENCE_EYE_BLUE,
                        layer_id="reference_eye_blue",
                    )

            if state.expression != "neutral":
                self._draw_reference_brow(
                    canvas,
                    eye_left,
                    eye_top,
                    eye_index,
                    str(
                        expression.get(
                            "brow_left" if eye_index == 0 else "brow_right",
                            "level",
                        )
                    ),
                    skin,
                )

        mouth_shape = self._reference_mouth_shape(state, expression)
        if mouth_shape is not None:
            self._draw_reference_mouth(canvas, mouth_anchor, mouth_shape)

    @staticmethod
    def _is_reference_eye_pixel(cell: Optional[Cell]) -> bool:
        if cell is None:
            return False
        red, green, blue = cell.rgb
        near_white = min(cell.rgb) >= 185 and max(cell.rgb) - min(cell.rgb) <= 50
        cool_blue = blue >= 105 and blue >= red + 18 and blue >= green - 22
        cool_gray = max(cell.rgb) - min(cell.rgb) <= 42 and blue >= 90 and red < 165
        return near_white or cool_blue or cool_gray

    def _reference_eye_layout(
        self,
        canvas: CellCanvas,
        anchor: Tuple[int, int],
    ) -> Optional[Tuple[int, int]]:
        anchor_x, anchor_y = anchor
        candidates = []
        for y in range(anchor_y - 3, anchor_y + 3):
            for x in range(anchor_x - 4, anchor_x + 5):
                if self._is_reference_eye_pixel(canvas.get(x, y)):
                    candidates.append((x, y))
        if len(candidates) < 2:
            return None
        min_x = min(x for x, _ in candidates)
        max_x = max(x for x, _ in candidates)
        min_y = min(y for _, y in candidates)
        max_y = max(y for _, y in candidates)
        center_x = (min_x + max_x) // 2
        eye_top = (min_y + max_y) // 2
        return center_x - 2, eye_top

    @staticmethod
    def _reference_eye_aim(state: WizardState) -> int:
        if state.gaze_authoritative:
            return max(-1, min(1, int(state.gaze_aim)))
        if state.target_point is not None:
            delta_x = float(state.target_point.get("x", 0.0)) - float(
                state.world_position.get("x", 0.0)
            )
            if abs(delta_x) > 0.12:
                return 1 if delta_x > 0.0 else -1
        if state.expression == "thinking":
            return -1
        if state.expression == "skeptical":
            return 1
        if state.facing in {"west", "northwest", "southwest"}:
            return -1
        if state.facing in {"east", "northeast", "southeast"}:
            return 1
        return 0

    @staticmethod
    def _sample_reference_skin(
        canvas: CellCanvas,
        center_x: int,
        center_y: int,
    ) -> Tuple[int, int, int]:
        colors: Counter[Tuple[int, int, int]] = Counter()
        for y in range(center_y - 3, center_y + 4):
            for x in range(center_x - 4, center_x + 5):
                cell = canvas.get(x, y)
                if cell is None:
                    continue
                red, green, blue = cell.rgb
                if red >= 175 and 75 <= green <= 210 and blue <= 145:
                    colors[cell.rgb] += 1
        return colors.most_common(1)[0][0] if colors else REFERENCE_SKIN

    @staticmethod
    def _draw_reference_brow(
        canvas: CellCanvas,
        eye_left: int,
        eye_top: int,
        eye_index: int,
        style: str,
        skin: Tuple[int, int, int],
    ) -> None:
        brow_y = eye_top - 2
        for x in range(eye_left, eye_left + 5):
            canvas.set(x, brow_y, "#", skin, "reference_brow_clear")
        points = [
            (eye_left + 1, brow_y),
            (eye_left + 2, brow_y),
            (eye_left + 3, brow_y),
        ]
        if style in {"up", "soft_up"}:
            points[1] = (eye_left + 2, brow_y - 1)
        elif style in {"down", "pinched"}:
            inward = eye_left + (3 if eye_index == 0 else 1)
            points = [
                (eye_left + 1, brow_y - (eye_index == 1)),
                (eye_left + 2, brow_y),
                (inward, brow_y + 1),
            ]
        elif style == "tilt":
            points = [
                (eye_left + 1, brow_y + eye_index),
                (eye_left + 2, brow_y),
                (eye_left + 3, brow_y + (1 - eye_index)),
            ]
        for x, y in points:
            canvas.set(x, y, "#", REFERENCE_BROW, "reference_expression_brow")

    @staticmethod
    def _reference_mouth_shape(state: WizardState, expression: dict) -> Optional[str]:
        # Legacy local speech has no timing track, so it retains one explicit
        # deterministic fallback. Media performance never sets speech_id: its
        # scheduler-selected state.mouth is the sole rendered authority,
        # including intentionally closed phoneme/silence frames.
        if state.speech_id is not None:
            return ("open_medium", "open_small", "closed", "open_small")[
                int(state.time_seconds * 10) % 4
            ]
        if state.action == "speaking":
            return state.mouth
        expression_mouth = str(expression.get("mouth", "closed"))
        if state.mouth != "closed":
            return state.mouth
        if state.expression != "neutral":
            return expression_mouth
        return None

    @staticmethod
    def _sample_reference_beard(
        canvas: CellCanvas,
        anchor: Tuple[int, int],
    ) -> Tuple[int, int, int]:
        anchor_x, anchor_y = anchor
        colors: Counter[Tuple[int, int, int]] = Counter()
        for y in range(anchor_y - 4, anchor_y + 3):
            for x in range(anchor_x - 6, anchor_x + 7):
                if abs(x - anchor_x) < 5 and anchor_y - 3 <= y <= anchor_y + 1:
                    continue
                cell = canvas.get(x, y)
                if cell is None:
                    continue
                red, green, blue = cell.rgb
                if 65 <= red <= 175 and green < red and blue < green:
                    colors[cell.rgb] += 1
        return colors.most_common(1)[0][0] if colors else REFERENCE_BROW

    def _draw_reference_mouth(
        self,
        canvas: CellCanvas,
        anchor: Tuple[int, int],
        shape: str,
    ) -> None:
        anchor_x, anchor_y = anchor
        beard = self._sample_reference_beard(canvas, anchor)
        for y in range(anchor_y - 3, anchor_y + 2):
            for x in range(anchor_x - 5, anchor_x + 6):
                if canvas.get(x, y) is not None:
                    canvas.set(x, y, "#", beard, "reference_mouth_clear")

        if shape == "closed":
            for x in range(anchor_x - 3, anchor_x + 4):
                canvas.set(x, anchor_y - 1, "#", REFERENCE_MOUTH_DARK, "reference_mouth_closed")
            return
        if shape == "frown":
            for offset, y_offset in ((-2, 0), (-1, -1), (0, -1), (1, -1), (2, 0)):
                canvas.set(
                    anchor_x + offset,
                    anchor_y + y_offset,
                    "#",
                    REFERENCE_MOUTH_DARK,
                    "reference_mouth_frown",
                )
            return
        if shape == "smile":
            for x in range(anchor_x - 2, anchor_x + 3):
                canvas.set(x, anchor_y - 2, "#", REFERENCE_TEETH, "reference_teeth")
                canvas.set(x, anchor_y - 1, "#", REFERENCE_MOUTH_OPEN, "reference_mouth_smile")
            canvas.set(anchor_x - 3, anchor_y - 2, "#", REFERENCE_MOUTH_DARK, "reference_mouth_smile")
            canvas.set(anchor_x + 3, anchor_y - 2, "#", REFERENCE_MOUTH_DARK, "reference_mouth_smile")
            return
        if shape == "rounded":
            canvas.set(anchor_x, anchor_y - 2, "#", REFERENCE_MOUTH_DARK, "reference_mouth_rounded")
            canvas.set(anchor_x - 1, anchor_y - 1, "#", REFERENCE_MOUTH_DARK, "reference_mouth_rounded")
            canvas.set(anchor_x, anchor_y - 1, "#", REFERENCE_MOUTH_OPEN, "reference_mouth_rounded")
            canvas.set(anchor_x + 1, anchor_y - 1, "#", REFERENCE_MOUTH_DARK, "reference_mouth_rounded")
            canvas.set(anchor_x, anchor_y, "#", REFERENCE_MOUTH_DARK, "reference_mouth_rounded")
            return

        width = {"open_small": 2, "open_medium": 3, "open_wide": 3}.get(shape, 2)
        top = anchor_y - (3 if shape == "open_wide" else 2)
        for x in range(anchor_x - width + 1, anchor_x + width):
            canvas.set(x, top, "#", REFERENCE_TEETH, "reference_teeth")
        for y in range(top + 1, anchor_y + 1):
            for x in range(anchor_x - width + 1, anchor_x + width):
                canvas.set(x, y, "#", REFERENCE_MOUTH_OPEN, "reference_speaking_mouth")
        for x in range(anchor_x - width + 1, anchor_x + width):
            canvas.set(x, anchor_y + 1, "#", REFERENCE_MOUTH_DARK, "reference_mouth_bottom")

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
        permission_world: Optional[PermissionWorldRenderPolicyV1] = None,
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

        effect_visible = self._permission_surface_visible(
            permission_world,
            "effect",
            "magic_effect",
        )
        if effect_visible and state.action in {"magic_cast", "reaction"}:
            phase = (
                state.time_seconds * math.tau * 1.4
                if permission_world is None
                or permission_world.motion_profile == "full"
                else 0.0
            )
            cx, cy = stage_point(65, 12)
            for idx in range(14):
                angle = phase + idx * math.tau / 14.0
                radius = 4 + (idx % 3)
                x = round(cx + math.cos(angle) * radius)
                y = round(cy + math.sin(angle) * radius * 0.7)
                color = RGB["cyan_magic"] if idx % 2 else RGB["gold_light"]
                stage.set(x, y, "#", color, "reference_magic_spark")

        if state.action == "thinking":
            colors = ((38, 156, 210), (255, 210, 48), (38, 156, 210))
            for offset, color in enumerate(colors):
                x, y = stage_point(
                    47 + offset * 2,
                    18 - math.sin(state.time_seconds * 4 + offset) * 2,
                )
                stage.set(x, y, "#", color, "reference_thinking_bubble")

    async def next_encoded_frame(
        self,
        codec: str = "adaptive",
        advance: bool = True,
    ) -> Tuple[bytes, WizardCellFrame]:
        await asyncio.sleep(0)
        return self.next_encoded_frame_sync(codec=codec, advance=advance)

    def next_encoded_frame_sync(
        self,
        codec: str = "adaptive",
        advance: bool = True,
    ) -> Tuple[bytes, WizardCellFrame]:
        """Advance, render, and encode one frame without requiring an event loop."""

        if advance:
            frame = self.render_next_frame()
        else:
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

    def encode_captured_frame_sync(
        self,
        state: WizardRenderSnapshot | WizardState,
        codec: str = "adaptive",
    ) -> Tuple[bytes, WizardCellFrame]:
        """Render and encode a captured state on the presentation worker."""

        frame = self.render_captured_frame(state)
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
        presentation = self._last_presentation_state
        return {
            **self.diagnostics.as_dict(),
            "world_x": state["world_position"]["x"],
            "world_z": state["world_position"]["z"],
            "screen_x": presentation.screen_x if presentation else state["screen_position"]["x"],
            "screen_y": presentation.screen_y if presentation else state["screen_position"]["y"],
            "display_scale": presentation.display_scale if presentation else state["display_scale"],
            "facing": state["facing"],
            "velocity": state["velocity"],
            "target_point": state["target_point"],
            "walk_phase": state["walk_phase"],
            "current_action": state["action"],
            "current_expression": state["expression"],
            "mouth_state": state["mouth"],
            "pose_id": presentation.pose_id if presentation else state["pose_id"],
            "last_pose_id": presentation.last_pose_id if presentation else state["last_pose_id"],
            "pose_transition_progress": (
                presentation.pose_transition_progress
                if presentation
                else state["pose_transition_progress"]
            ),
            "simulation_tick": state["simulation_tick"],
            "animation_clip_id": (
                presentation.animation_clip_id if presentation else state["animation_clip_id"]
            ),
            "animation_node_id": (
                presentation.animation_node_id if presentation else state["animation_node_id"]
            ),
            "mobility_mode": state["mobility_mode"],
            "airborne": state["airborne"],
            "altitude": state["altitude"],
            "control_source": state["control_source"],
            "semantic_cue": state["semantic_cue"],
        }


def _smoothstep(progress: float) -> float:
    t = max(0.0, min(1.0, progress))
    return t * t * (3.0 - 2.0 * t)
