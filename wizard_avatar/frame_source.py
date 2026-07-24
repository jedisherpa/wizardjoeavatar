from __future__ import annotations

import asyncio
import copy
import hashlib
import math
import struct
import threading
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

from .character_package import WIZARD_JOE_PACKAGE_PATH, load_character_package
from .animation_trace import (
    ANIMATION_TRUTH_TRACE_SCHEMA,
    ANIMATION_TRUTH_TRACE_VERSION,
    AnimationMarkerEventV1,
    AnimationTruthTraceV1,
    LocalPointV1,
    PresentationChannelsV1,
    RasterSpanV1,
    StagePointV1,
    transformed_anchor,
)
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
from .frame_hash import frame_hash
from .head_eye import HeadEyeState, advance_head_eye
from .layers import ROOT_ANCHOR, render_wizard_local
from .models import (
    Cell,
    CommandResult,
    WizardCellFrame,
    WizardCommand,
    WizardPresentationState,
    WizardState,
)
from .mouth import fallback_speech_shape
from .palette import ENV_RGB, RGB
from .pose_compositor import (
    blit_pose_scaled,
    clear_authored_staff,
    copy_pose_canvas,
    touch_up_staff_occlusion,
)
from .pose_selection import (
    PoseSample,
    presentation_pose_for_facing,
    select_reference_pose_sample,
)
from .projection import project_quantized
from .permission_world import PermissionWorldRenderPolicyV1
from .protocol import EncodedFrame, encode_frame
from .reference_avatar import (
    REFERENCE_SCALE_MULTIPLIER,
    reference_pose_anchor,
    reference_pose_ids,
    reference_pose_library_available,
    reference_pose_presentation_scale,
    reference_pose_root_anchor,
    render_reference_pose_local,
)
from .runtime import canonical_sha256
from .shadow import draw_contact_shadow


REFERENCE_POSE_HORIZONTAL_SCALE = 1.18
REFERENCE_TOP_MARGIN_CELLS = 4
REFERENCE_SIDE_MARGIN_CELLS = 4
REFERENCE_BOTTOM_MARGIN_CELLS = 6
REFERENCE_HEAD_MOTION_RESERVE_CELLS = 1
REFERENCE_RASTER_SAFETY_CELLS = 1
REFERENCE_MOUTH_OPEN = (132, 30, 22)
REFERENCE_MOUTH_DARK = (78, 39, 20)
REFERENCE_TEETH = (250, 238, 209)
REFERENCE_EYE_WHITE = (242, 242, 242)
REFERENCE_EYE_BLUE = (11, 76, 142)
REFERENCE_SKIN = (234, 167, 75)
REFERENCE_BROW = (108, 55, 26)
MEMORY_NOTEBOOK_COVER = (31, 101, 112)
MEMORY_NOTEBOOK_EDGE = (22, 45, 52)
MEMORY_NOTEBOOK_PAPER = (241, 230, 190)
MEMORY_NOTEBOOK_ARCHIVE = (218, 166, 54)
PRESENTATION_MARKER_IDS = frozenset(
    {
        "action_commit",
        "action_effect",
        "action_recoverable",
        "action_settled",
        "speech_open",
        "speech_close",
    }
)
PRESENTATION_MARKER_DEDUP_CAPACITY = 256
IDLE_BODY_FACING_BY_CLIP = {
    "idle_front": "south",
    "idle_back": "north",
    "idle_left": "west",
    "idle_right": "east",
}


@dataclass(frozen=True)
class ReferenceEyeAperture:
    left: int
    top: int
    width: int
    height: int = 2

    def span(self) -> RasterSpanV1:
        return RasterSpanV1(
            min_x=self.left,
            max_x=self.left + self.width - 1,
            min_y=self.top,
            max_y=self.top + self.height - 1,
        )


@dataclass(frozen=True)
class ReferenceFaceEvidence:
    eye_apertures: Tuple[RasterSpanV1, ...] = ()
    eye_blue_cells: Tuple[LocalPointV1, ...] = ()
    blink_painted_cells: int = 0
    body_pixel_sha256: str = "legacy_unspecified"
    mouth_pixel_sha256: str = "legacy_unspecified"
    mouth_painted_cells: int = 0


@dataclass(frozen=True)
class WizardPresentationSnapshot:
    """Committed presentation state that a pure render candidate extends."""

    generation: int
    display_pose_id: Optional[str]
    last_presentation_state: Optional[WizardPresentationState]
    head_eye_state: HeadEyeState
    contact_generation: int = -1
    contact_anchor: Optional[str] = None
    contact_lock_stage: Optional[Tuple[float, float]] = None
    contact_root_offset: Tuple[float, float] = (0.0, 0.0)
    consumed_marker_events: Tuple[AnimationMarkerEventV1, ...] = ()
    blink_input_active: bool = False
    blink_visible_frames_remaining: int = 0
    blink_source: str = "none"


@dataclass(frozen=True)
class WizardRenderSnapshot:
    """Complete immutable-input transaction for the render worker."""

    state: WizardState
    permission_world: Optional[PermissionWorldRenderPolicyV1]
    authoritative_state_sha256: str = ""
    frame_index: int = 0
    previous_encoded_frame: Optional[bytes] = None
    encoder_generation: int = 0
    pending_marker_events: Tuple[AnimationMarkerEventV1, ...] = ()
    presentation: WizardPresentationSnapshot = field(
        default_factory=lambda: WizardPresentationSnapshot(
            0,
            None,
            None,
            HeadEyeState.steady(),
        )
    )

    @property
    def presentation_generation(self) -> int:
        return self.presentation.generation


@dataclass(frozen=True)
class WizardRenderCandidate:
    """Pure worker output that changes no committed source state until accepted."""

    authoritative_state_sha256: str
    base_presentation_generation: int
    base_encoder_generation: int
    cols: int
    rows: int
    frame_index: int
    cells: bytes
    raw_size: int
    changed_cells: int
    codec_tag: int
    encoded_size: int
    is_keyframe: bool
    message: bytes
    shown_frame: bytes
    presentation: WizardPresentationSnapshot
    animation_truth: AnimationTruthTraceV1

    @property
    def frame(self) -> WizardCellFrame:
        """Materialize a mutable transport DTO without exposing candidate state."""

        return WizardCellFrame(
            cols=self.cols,
            rows=self.rows,
            frame_index=self.frame_index,
            cells=self.cells,
            raw_size=self.raw_size,
            changed_cells=self.changed_cells,
            codec_tag=self.codec_tag,
            encoded_size=self.encoded_size,
            is_keyframe=self.is_keyframe,
        )


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
        self._encoder_generation = 0
        self._presentation_lock = threading.RLock()
        self._presentation_generation = 0
        self._head_eye_state = HeadEyeState.steady(
            self.controller.current_state().facing,
            self.controller.current_state().simulation_tick,
        )
        self.diagnostics = FrameDiagnostics(fps=self.fps)
        self._display_pose_id: Optional[str] = None
        self._transition_from_pose_id: Optional[str] = None
        self._transition_started_at_frame = 0
        self._transition_frames = max(2, round(self.fps * 0.12))
        self._last_presentation_state: Optional[WizardPresentationState] = None
        self._contact_generation = -1
        self._contact_anchor: Optional[str] = None
        self._contact_lock_stage: Optional[Tuple[float, float]] = None
        self._contact_root_offset = (0.0, 0.0)
        self._pending_presentation_marker_events: list[AnimationMarkerEventV1] = []
        self._observed_presentation_marker_keys: deque[tuple[object, ...]] = deque()
        self._observed_presentation_marker_key_set: set[tuple[object, ...]] = set()
        self._last_marker_observation_tick = -1
        self._reference_body_hash_cache: dict[tuple[object, ...], str] = {}
        self._blink_input_active = False
        self._blink_visible_frames_remaining = 0
        self._blink_source = "none"
        self._initialize_authoritative_animation_state()

    def _initialize_authoritative_animation_state(self) -> None:
        """Resolve the package's initial semantic animation before runtime hashing."""

        self.resolve_authoritative_animation_state()

    def resolve_authoritative_animation_state(self) -> None:
        """Update semantic pose selection outside the presentation renderer."""

        state = self.controller.current_state()
        derived = copy.deepcopy(state)
        if (
            state.locomotion == "idle"
            and state.animation_clip_id in IDLE_BODY_FACING_BY_CLIP
        ):
            # Facing commands animate the head and eyes over the planted idle
            # body. Resolve semantic body selection from its current authored
            # orientation while the presentation layer turns toward the target.
            derived.facing = IDLE_BODY_FACING_BY_CLIP[state.animation_clip_id]
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
        state.animation_phase_offset = derived.animation_phase_offset
        state.animation_node_id = derived.animation_node_id
        state.animation_transition_id = derived.animation_transition_id
        state.animation_transition_phase = derived.animation_transition_phase
        state.animation_transition_target_node_id = derived.animation_transition_target_node_id
        state.animation_transition_target_clip_id = derived.animation_transition_target_clip_id
        state.animation_transition_entry_tick = derived.animation_transition_entry_tick
        state.animation_transition_started_tick = derived.animation_transition_started_tick
        state.animation_transition_commit_tick = derived.animation_transition_commit_tick
        state.animation_transition_source_pose_id = derived.animation_transition_source_pose_id
        state.animation_transition_source_contact = derived.animation_transition_source_contact
        state.animation_transition_generation = derived.animation_transition_generation
        state.pose_transition_progress = derived.pose_transition_progress
        self._record_authoritative_pose_sample(state, sample)

    def _record_authoritative_pose_sample(
        self,
        state: WizardState,
        sample: PoseSample,
    ) -> None:
        """Persist the exact selected graph sample on the authoritative state."""

        previous_contact = (
            state.animation_support_contact,
            state.animation_planted_anchor,
            state.animation_root_policy,
        )
        state.animation_support_contact = sample.contact
        state.animation_planted_anchor = sample.planted_anchor
        state.animation_active_markers = tuple(sample.active_markers)

        state.animation_sample_index = sample.sample_index
        state.animation_sample_frame = sample.sample_frame
        state.animation_authored_frame = sample.authored_frame
        state.animation_phase_numerator = sample.phase_numerator
        state.animation_phase_denominator = sample.phase_denominator
        state.animation_root_policy = sample.root_policy

        current_contact = (
            state.animation_support_contact,
            state.animation_planted_anchor,
            state.animation_root_policy,
        )
        if current_contact != previous_contact:
            state.animation_contact_generation += 1
            state.animation_contact_started_tick = state.simulation_tick
        self._latch_presentation_markers(state)

    def _latch_presentation_markers(self, state: WizardState) -> None:
        """Retain transient authored events until one frame accepts them."""

        markers = tuple(
            marker
            for marker in state.animation_active_markers
            if marker in PRESENTATION_MARKER_IDS
        )
        with self._presentation_lock:
            if state.simulation_tick < self._last_marker_observation_tick:
                self._pending_presentation_marker_events.clear()
                self._observed_presentation_marker_keys.clear()
                self._observed_presentation_marker_key_set.clear()
            self._last_marker_observation_tick = state.simulation_tick
            for marker_id in markers:
                key = (
                    marker_id,
                    state.simulation_tick,
                    state.state_revision,
                    state.animation_clip_id,
                    state.animation_clip_tick,
                    state.animation_authored_frame,
                )
                if key in self._observed_presentation_marker_key_set:
                    continue
                event = AnimationMarkerEventV1(
                    marker_id=marker_id,
                    simulation_tick=state.simulation_tick,
                    state_revision=state.state_revision,
                    animation_node_id=state.animation_node_id,
                    animation_clip_id=state.animation_clip_id,
                    animation_clip_tick=state.animation_clip_tick,
                    animation_sample_index=state.animation_sample_index,
                    animation_sample_frame=state.animation_sample_frame,
                    animation_authored_frame=state.animation_authored_frame,
                    animation_phase_numerator=state.animation_phase_numerator,
                    animation_phase_denominator=state.animation_phase_denominator,
                )
                self._pending_presentation_marker_events.append(event)
                self._observed_presentation_marker_keys.append(key)
                self._observed_presentation_marker_key_set.add(key)
                while (
                    len(self._observed_presentation_marker_keys)
                    > PRESENTATION_MARKER_DEDUP_CAPACITY
                ):
                    expired = self._observed_presentation_marker_keys.popleft()
                    self._observed_presentation_marker_key_set.discard(expired)

    async def next_frame(self) -> WizardCellFrame:
        await asyncio.sleep(0)
        return self.render_next_frame()

    def advance_simulation(self, seconds: float) -> None:
        self.controller.advance(seconds)
        self.resolve_authoritative_animation_state()

    def render_current_frame(self) -> WizardCellFrame:
        # Direct rendering is a synchronous owner path. Production rendering
        # uses the pure candidate/commit API below so stale worker output can be
        # discarded without advancing presentation state.
        with self._presentation_lock:
            snapshot = self._capture_render_state_unlocked()
            frame, presentation, _ = self._render_snapshot(snapshot)
            self._commit_presentation_unlocked(
                presentation,
                snapshot.presentation_generation,
            )
            return frame

    def capture_render_state(self) -> WizardRenderSnapshot:
        """Capture the authoritative simulation state for off-thread rendering."""

        with self._presentation_lock:
            return self._capture_render_state_unlocked()

    def _capture_render_state_unlocked(
        self,
        state: Optional[WizardState] = None,
        permission_world: Optional[PermissionWorldRenderPolicyV1] = None,
    ) -> WizardRenderSnapshot:
        captured_state = copy.deepcopy(
            self.controller.current_state() if state is None else state
        )
        captured_permission = (
            self.controller.permission_world_render_policy
            if state is None and permission_world is None
            else permission_world
        )
        return WizardRenderSnapshot(
            state=captured_state,
            permission_world=captured_permission,
            authoritative_state_sha256=canonical_sha256(captured_state),
            frame_index=self.frame_index,
            previous_encoded_frame=self._prev_encoded_frame,
            encoder_generation=self._encoder_generation,
            pending_marker_events=tuple(self._pending_presentation_marker_events),
            presentation=WizardPresentationSnapshot(
                generation=self._presentation_generation,
                display_pose_id=self._display_pose_id,
                last_presentation_state=self._last_presentation_state,
                head_eye_state=self._head_eye_state,
                contact_generation=self._contact_generation,
                contact_anchor=self._contact_anchor,
                contact_lock_stage=self._contact_lock_stage,
                contact_root_offset=self._contact_root_offset,
                blink_input_active=self._blink_input_active,
                blink_visible_frames_remaining=self._blink_visible_frames_remaining,
                blink_source=self._blink_source,
            ),
        )

    def render_captured_frame(
        self,
        state: WizardRenderSnapshot | WizardState,
    ) -> WizardCellFrame:
        """Purely rasterize a captured state without committing presentation."""

        if type(state) is WizardRenderSnapshot:
            snapshot = state
        else:
            with self._presentation_lock:
                snapshot = self._capture_render_state_unlocked(state=state)
        frame, _, _ = self._render_snapshot(snapshot)
        return frame

    def render_next_frame(self) -> WizardCellFrame:
        self.advance_simulation(1.0 / self.fps)
        return self.render_current_frame()

    def _render_snapshot(
        self,
        snapshot: WizardRenderSnapshot,
    ) -> tuple[WizardCellFrame, WizardPresentationSnapshot, AnimationTruthTraceV1]:
        state = copy.deepcopy(snapshot.state)
        permission_world = snapshot.permission_world
        state.reconcile_compatibility_state()
        authored_pose_id = state.pose_id
        authored_body_facing = self._authored_body_facing(state)
        head_eye_state, head_eye = advance_head_eye(
            snapshot.presentation.head_eye_state,
            authored_body_facing or state.facing,
            state.simulation_tick,
            state.gaze_authoritative,
            state.gaze_aim,
            facing_changed_tick=state.facing_changed_tick,
        )
        if (
            authored_body_facing is not None
            and head_eye.presented_facing != authored_body_facing
        ):
            # Whole-pose transition graphs already author the head, torso,
            # wings, hand, and staff as one physical turn. Present their
            # declared sector atomically so pathing cannot lead the body.
            head_eye_state = HeadEyeState.steady(
                authored_body_facing,
                state.simulation_tick,
            )
            head_eye_state, head_eye = advance_head_eye(
                head_eye_state,
                authored_body_facing,
                state.simulation_tick,
                state.gaze_authoritative,
                state.gaze_aim,
                facing_changed_tick=state.simulation_tick,
            )
        scheduler_blink_closed = state.blink_phase >= 0.965
        scheduler_blink_suppressed = (
            scheduler_blink_closed
            and not head_eye.turn_blink_closed
            and state.facing_changed_tick > 0
            and 0
            <= state.simulation_tick - state.facing_changed_tick
            < 150
        )
        if scheduler_blink_suppressed:
            scheduler_blink_closed = False
            state.blink_phase = 0.0
        if head_eye.turn_blink_closed:
            state.blink_phase = 1.0
        blink_source = (
            "scheduler+turn"
            if scheduler_blink_closed and head_eye.turn_blink_closed
            else "scheduler"
            if scheduler_blink_closed
            else "turn"
            if head_eye.turn_blink_closed
            else "none"
        )
        blink_input_active = scheduler_blink_closed or head_eye.turn_blink_closed
        (
            presentation_blink_closed,
            blink_visible_frames_remaining,
            blink_source,
        ) = self._resolve_presentation_blink(
            input_active=blink_input_active,
            previous_input_active=snapshot.presentation.blink_input_active,
            previous_frames_remaining=(
                snapshot.presentation.blink_visible_frames_remaining
            ),
            input_source=blink_source,
            previous_source=snapshot.presentation.blink_source,
        )
        state.blink_phase = 1.0 if presentation_blink_closed else 0.0
        head_offset_y = self._idle_head_breath_offset(
            state,
            head_eye.phase,
            head_eye.presented_facing,
        )
        state.facing = head_eye.presented_facing
        if state.gaze_authoritative or head_eye.phase != "steady":
            state.gaze_authoritative = True
            state.gaze_aim = head_eye.gaze_aim
        sx, sy, scale = project_quantized(
            state.world_position["x"],
            state.world_position["z"],
            self.cols,
            self.rows,
        )
        state.screen_position = {"x": sx, "y": sy}
        previous_pose_id = snapshot.presentation.display_pose_id or state.pose_id
        use_reference_pose_library = reference_pose_library_available(self.pose_library_path)
        rendered_head_pose_id = state.pose_id
        face_evidence = ReferenceFaceEvidence()
        if use_reference_pose_library:
            stage = self._permissioned_stage(permission_world)
            altitude_scale = max(0.76, 1.0 - state.altitude * 0.07)
            render_scale = scale * REFERENCE_SCALE_MULTIPLIER * altitude_scale
            requested_head_pose_id = presentation_pose_for_facing(
                state.pose_id,
                state.animation_clip_id,
                head_eye.presented_facing,
                self.pose_ids,
            )
            # Candidate freshness already binds this render to the authoritative
            # state hash. A previous presentation pose is evidence, not an
            # alternate pose authority; retaining it here freezes the final
            # action frame forever after the controller settles into idle.
            committed_pose_id = state.pose_id
            pose_id = self._permissioned_pose_id(
                committed_pose_id,
                state,
                permission_world,
            )
            render_scale *= reference_pose_presentation_scale(
                pose_id,
                self.pose_library_path,
            )
            local, root_anchor, mouth_anchor = self._reference_pose_canvas_for_sample(
                pose_id,
            )
            provisional_root_screen = self._reference_root_screen(
                sx,
                sy,
                state,
                render_scale,
            )
            render_scale = self._fit_reference_scale_to_stage(
                local,
                root_anchor,
                provisional_root_screen,
                render_scale,
            )
            if (
                state.animation_clip_id
                in {"idle_front", "idle_back", "idle_left", "idle_right"}
                and (
                    requested_head_pose_id != pose_id
                    or head_eye.head_offset_x != 0
                    or head_offset_y != 0
                )
                and requested_head_pose_id in self.pose_ids
            ):
                self._project_reference_head(
                    local,
                    pose_id,
                    requested_head_pose_id,
                    head_eye.head_offset_x,
                    head_offset_y,
                )
                rendered_head_pose_id = requested_head_pose_id
                mouth_anchor = reference_pose_anchor(
                    requested_head_pose_id,
                    "mouth",
                    self.pose_library_path,
                )
                mouth_anchor = (
                    mouth_anchor[0] + head_eye.head_offset_x,
                    mouth_anchor[1] + head_offset_y,
                )
            else:
                rendered_head_pose_id = pose_id
            self._apply_reference_permission_surfaces(
                local,
                pose_id,
                permission_world,
            )
            body_pixel_sha256 = self._reference_body_pixel_sha256(
                local,
                pose_id=pose_id,
                rendered_head_pose_id=rendered_head_pose_id,
                head_offset_x=(
                    head_eye.head_offset_x
                    if rendered_head_pose_id != pose_id
                    or head_eye.head_offset_x != 0
                    or head_offset_y != 0
                    else 0
                ),
                head_offset_y=head_offset_y,
                staff_visible=self._permission_surface_visible(
                    permission_world,
                    "prop",
                    "staff",
                ),
            )
            face_evidence = self._apply_reference_face_channels(
                local,
                state,
                rendered_head_pose_id,
                mouth_anchor,
                head_eye.head_offset_x
                if rendered_head_pose_id != pose_id
                or head_eye.head_offset_x != 0
                or head_offset_y != 0
                else 0,
                head_offset_y,
                body_pixel_sha256,
            )
            base_root_screen = self._reference_root_screen(sx, sy, state, render_scale)
            (
                root_screen,
                contact_generation,
                contact_anchor,
                contact_lock_stage,
                contact_root_offset,
            ) = self._resolve_contact_locked_root(
                snapshot.presentation,
                state,
                pose_id,
                root_anchor,
                base_root_screen,
                render_scale,
            )
        else:
            stage = self._permissioned_stage(permission_world)
            render_scale = scale
            pose_id = None
            local = render_wizard_local(state)
            root_anchor = ROOT_ANCHOR
            mouth_anchor = None
            base_root_screen = (sx, sy)
            root_screen = base_root_screen
            contact_generation = state.animation_contact_generation
            contact_anchor = None
            contact_lock_stage = None
            contact_root_offset = (0.0, 0.0)
        state.last_pose_id = previous_pose_id
        state.pose_id = pose_id or "procedural"
        lifted = state.airborne or (state.locomotion == "walking" and 0.15 < state.walk_phase < 0.38)
        state.display_scale = render_scale
        rendered_mouth_shape = self._reference_mouth_shape(
            state,
            get_expression(state.expression),
        ) or state.mouth
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
        silhouette_raster_span = None
        if pose_id is not None:
            occupied = blit_pose_scaled(
                stage,
                local,
                root_anchor,
                root_screen,
                render_scale,
                REFERENCE_POSE_HORIZONTAL_SCALE,
            )
            if occupied is not None:
                silhouette_raster_span = RasterSpanV1(
                    min_x=occupied[0],
                    max_x=occupied[1],
                    min_y=occupied[2],
                    max_y=occupied[3],
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
        self._draw_memory_notebook_overlay(
            stage,
            root_screen,
            render_scale,
            permission_world,
        )
        cells = stage.to_frame_bytes()
        frame = WizardCellFrame(
            cols=self.cols,
            rows=self.rows,
            frame_index=snapshot.frame_index,
            cells=cells,
            raw_size=len(cells),
        )
        last_presentation_state = WizardPresentationState(
            screen_x=sx,
            screen_y=sy,
            display_scale=render_scale,
            pose_id=state.pose_id,
            last_pose_id=state.last_pose_id,
            pose_transition_progress=state.pose_transition_progress,
            animation_clip_id=state.animation_clip_id,
            animation_node_id=state.animation_node_id,
            animation_transition_id=state.animation_transition_id,
            presented_facing=head_eye.presented_facing,
            gaze_aim=head_eye.gaze_aim,
            head_eye_phase=head_eye.phase,
            rendered_mouth_shape=rendered_mouth_shape,
            rendered_head_pose_id=rendered_head_pose_id,
            turn_progress_milli=head_eye.turn_progress_milli,
            blink_source=blink_source,
            head_offset_x=head_eye.head_offset_x,
            head_offset_y=head_offset_y,
        )
        presentation = WizardPresentationSnapshot(
            generation=snapshot.presentation_generation + 1,
            display_pose_id=pose_id,
            last_presentation_state=last_presentation_state,
            head_eye_state=head_eye_state,
            contact_generation=contact_generation,
            contact_anchor=contact_anchor,
            contact_lock_stage=contact_lock_stage,
            contact_root_offset=contact_root_offset,
            consumed_marker_events=snapshot.pending_marker_events,
            blink_input_active=blink_input_active,
            blink_visible_frames_remaining=blink_visible_frames_remaining,
            blink_source=(
                blink_source
                if presentation_blink_closed
                else "none"
            ),
        )
        planted_anchor_local = None
        planted_anchor_stage = None
        planted_anchor_raster_span = None
        staff_tip_local = None
        staff_tip_stage = None
        staff_tip_raster_span = None
        if pose_id is not None and state.animation_planted_anchor is not None:
            try:
                planted_anchor_local = reference_pose_anchor(
                    pose_id,
                    state.animation_planted_anchor,
                    self.pose_library_path,
                )
            except KeyError:
                planted_anchor_local = None
            if planted_anchor_local is not None:
                planted_anchor_stage, planted_anchor_raster_span = transformed_anchor(
                    root_local=root_anchor,
                    root_stage=root_screen,
                    anchor_local=planted_anchor_local,
                    local_size=(local.width, local.height),
                    scale=render_scale,
                    horizontal_scale=REFERENCE_POSE_HORIZONTAL_SCALE,
                )
        if pose_id is not None:
            try:
                staff_tip_local = reference_pose_anchor(
                    pose_id,
                    "staff_tip",
                    self.pose_library_path,
                )
            except KeyError:
                staff_tip_local = None
            if staff_tip_local is not None:
                staff_tip_stage, staff_tip_raster_span = transformed_anchor(
                    root_local=root_anchor,
                    root_stage=root_screen,
                    anchor_local=staff_tip_local,
                    local_size=(local.width, local.height),
                    scale=render_scale,
                    horizontal_scale=REFERENCE_POSE_HORIZONTAL_SCALE,
                )
        effect_phase, effect_intensity = self._reference_magic_effect_state(state)
        if not self._permission_surface_visible(
            permission_world,
            "effect",
            "magic_effect",
        ) or (
            permission_world is not None
            and permission_world.motion_profile != "full"
        ):
            effect_intensity = 0.0
        animation_truth = AnimationTruthTraceV1(
            schema=ANIMATION_TRUTH_TRACE_SCHEMA,
            schema_version=ANIMATION_TRUTH_TRACE_VERSION,
            simulation_tick=state.simulation_tick,
            state_revision=state.state_revision,
            frame_index=frame.frame_index,
            authoritative_state_sha256=snapshot.authoritative_state_sha256,
            authored_pose_id=authored_pose_id,
            rendered_pose_id=state.pose_id,
            animation_node_id=state.animation_node_id,
            animation_clip_id=state.animation_clip_id,
            animation_clip_tick=state.animation_clip_tick,
            animation_sample_index=state.animation_sample_index,
            animation_sample_frame=state.animation_sample_frame,
            animation_authored_frame=state.animation_authored_frame,
            animation_phase_numerator=state.animation_phase_numerator,
            animation_phase_denominator=state.animation_phase_denominator,
            animation_root_policy=state.animation_root_policy,
            support_contact=state.animation_support_contact,
            planted_anchor=state.animation_planted_anchor,
            active_markers=tuple(state.animation_active_markers),
            presentation_marker_events=snapshot.pending_marker_events,
            contact_generation=state.animation_contact_generation,
            contact_started_tick=state.animation_contact_started_tick,
            world_root_x=state.world_position["x"],
            world_root_z=state.world_position["z"],
            altitude=state.altitude,
            semantic_root_stage=StagePointV1(*base_root_screen),
            contact_root_offset_stage=StagePointV1(*contact_root_offset),
            presented_root_stage=StagePointV1(*root_screen),
            render_scale=render_scale,
            render_scale_x=(
                render_scale * REFERENCE_POSE_HORIZONTAL_SCALE
                if pose_id is not None
                else render_scale
            ),
            render_scale_y=render_scale,
            root_anchor_local=LocalPointV1(*root_anchor),
            planted_anchor_local=(
                None
                if planted_anchor_local is None
                else LocalPointV1(*planted_anchor_local)
            ),
            planted_anchor_stage=planted_anchor_stage,
            planted_anchor_raster_span=planted_anchor_raster_span,
            staff_tip_local=(
                None if staff_tip_local is None else LocalPointV1(*staff_tip_local)
            ),
            staff_tip_stage=staff_tip_stage,
            staff_tip_raster_span=staff_tip_raster_span,
            silhouette_raster_span=silhouette_raster_span,
            effect_phase=effect_phase,
            effect_intensity=effect_intensity,
            presented_facing=head_eye.presented_facing,
            presentation_channels=PresentationChannelsV1(
                head_eye_phase=head_eye.phase,
                gaze_aim=head_eye.gaze_aim,
                gaze_vertical_aim=max(-1, min(1, int(state.gaze_vertical_aim))),
                gaze_authoritative=bool(state.gaze_authoritative),
                blink_closed=state.blink_phase >= 0.965,
                expression=state.expression,
                rendered_mouth_shape=rendered_mouth_shape,
                speech_mouth_authority=state.speech_mouth_authority,
                speech_id=state.speech_id,
                locomotion=state.locomotion,
                action=state.action,
                rendered_head_pose_id=rendered_head_pose_id,
                turn_progress_milli=head_eye.turn_progress_milli,
                blink_source=blink_source,
                eye_apertures=face_evidence.eye_apertures,
                eye_blue_cells=face_evidence.eye_blue_cells,
                blink_painted_cells=face_evidence.blink_painted_cells,
                body_pixel_sha256=face_evidence.body_pixel_sha256,
                mouth_pixel_sha256=face_evidence.mouth_pixel_sha256,
                mouth_painted_cells=face_evidence.mouth_painted_cells,
                head_offset_x=head_eye.head_offset_x,
                head_offset_y=head_offset_y,
            ),
            frame_sha256=hashlib.sha256(cells).hexdigest(),
            frame_fnv1a32=frame_hash(cells),
            codec_tag=0,
            encoded_size=0,
            changed_cells=0,
            is_keyframe=False,
        )
        return frame, presentation, animation_truth

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

    @staticmethod
    def _draw_memory_notebook_overlay(
        stage: CellCanvas,
        root_screen: Tuple[float, float],
        scale: float,
        policy: Optional[PermissionWorldRenderPolicyV1],
    ) -> None:
        if (
            policy is None
            or policy.source_state_sha256 is None
            or "memory_notebook" not in policy.managed_props
            or "memory_notebook" not in policy.visible_props
        ):
            return

        cell_size = max(1, round(scale))
        left = round(root_screen[0] + 36 * scale)
        top = round(root_screen[1] - 42 * scale)
        layer_id = "permission_world_memory_notebook"

        def square(x: int, y: int, color: Tuple[int, int, int]) -> None:
            x0 = left + x * cell_size
            y0 = top + y * cell_size
            stage.rect(
                x0,
                y0,
                x0 + cell_size - 1,
                y0 + cell_size - 1,
                "#",
                color,
                layer_id,
            )

        for y in range(7):
            for x in range(7):
                border = x in {0, 6} or y in {0, 6}
                square(x, y, MEMORY_NOTEBOOK_EDGE if border else MEMORY_NOTEBOOK_PAPER)
        for y in range(1, 6):
            square(1, y, MEMORY_NOTEBOOK_COVER)
        for x in range(2, 6):
            square(x, 1, MEMORY_NOTEBOOK_ARCHIVE)
        for y in (3, 5):
            for x in range(3, 6):
                square(x, y, MEMORY_NOTEBOOK_COVER)

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

        # Authored square-cell sprites are atomic presentation snapshots. A
        # partial per-cell dissolve creates false limbs and facial artifacts;
        # root anchoring and fixed-tick motion carry continuity between them.
        return target_canvas, target_root, target_mouth

    def _project_reference_head(
        self,
        target: CellCanvas,
        target_pose_id: str,
        head_pose_id: str,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        """Project a head view onto a stable authored body pixel graph.

        Listening turns own the head and eyes, not locomotion. Keeping the
        target body's feet, hands, wings, and staff intact prevents a face cue
        from silently substituting a walk or profile-body silhouette.
        """

        source = render_reference_pose_local(head_pose_id, self.pose_library_path)
        target_root = reference_pose_root_anchor(target_pose_id, self.pose_library_path)
        source_root = reference_pose_root_anchor(head_pose_id, self.pose_library_path)
        target_mouth = reference_pose_anchor(
            target_pose_id,
            "mouth",
            self.pose_library_path,
        )

        def in_head_mask(x: int, y: int, root_x: int, mouth_y: int) -> bool:
            if y < mouth_y - 14:
                return abs(x - root_x) <= 15
            return y <= mouth_y + 8 and abs(x - root_x) <= 15

        clear_bottom = target_mouth[1] + 8 + min(0, int(offset_y))
        for y in range(target.height):
            for x in range(target.width):
                if (
                    y <= clear_bottom
                    and in_head_mask(x, y, target_root[0], target_mouth[1])
                ):
                    target.clear_cell(x, y)

        dx = target_root[0] - source_root[0] + int(offset_x)
        dy = target_root[1] - source_root[1] + int(offset_y)
        source_mouth = reference_pose_anchor(
            head_pose_id,
            "mouth",
            self.pose_library_path,
        )
        for y in range(source.height):
            for x in range(source.width):
                if not in_head_mask(x, y, source_root[0], source_mouth[1]):
                    continue
                cell = source.get(x, y)
                target_x = x + dx
                target_y = y + dy
                if cell is not None and target.in_bounds(target_x, target_y):
                    target.cells[target_y][target_x] = cell

    def _authored_body_facing(self, state: WizardState) -> Optional[str]:
        """Return the facing owned by a whole-pose locomotion transition."""

        if self.animation_graph is None:
            return None
        clip = self.animation_graph.clips.get(state.animation_clip_id)
        if clip is None:
            return None
        transition_target = state.animation_transition_target_node_id or ""
        transition_owns_body = state.animation_clip_id in {
            "walk_front",
            "walk_left",
            "walk_right",
            "turn_front_to_east",
            "turn_front_to_west",
            "reverse_east_to_west",
            "reverse_west_to_east",
            "stop_left",
            "stop_right",
        } or transition_target.startswith(("ground_turn_", "ground_reverse_"))
        if not transition_owns_body:
            return None
        pose = self.animation_graph.pose_catalog.get(state.pose_id)
        return pose.facing if pose is not None else None

    @staticmethod
    def _idle_head_breath_offset(
        state: WizardState,
        head_eye_phase: str,
        presented_facing: str,
    ) -> int:
        """Return one restrained pixel-art inhale without moving the body root."""

        if (
            head_eye_phase != "steady"
            or presented_facing not in {"south", "west", "east"}
            or state.locomotion != "idle"
            or state.action != "idle"
            or state.speech_mouth_authority != "none"
        ):
            return 0
        # Two unevenly spaced inhales in a six-second phrase avoid the
        # metronomic three-second bob. Profile holds retain the same restrained
        # head-only life without disturbing the planted body graph.
        phase = state.simulation_tick % 360
        return -1 if 36 <= phase < 48 or 228 <= phase < 240 else 0

    def _apply_reference_face_channels(
        self,
        canvas: CellCanvas,
        state: WizardState,
        pose_id: str,
        mouth_anchor: Tuple[int, int],
        head_offset_x: int = 0,
        head_offset_y: int = 0,
        body_pixel_sha256: str = "legacy_unspecified",
    ) -> ReferenceFaceEvidence:
        eye_layouts = []
        seen_apertures = set()
        for anchor_name in ("left_eye", "right_eye"):
            try:
                anchor = reference_pose_anchor(pose_id, anchor_name, self.pose_library_path)
            except KeyError:
                continue
            shifted_anchor = (
                anchor[0] + int(head_offset_x),
                anchor[1] + int(head_offset_y),
            )
            if pose_id == "profile_left" and anchor_name == "left_eye":
                aperture = ReferenceEyeAperture(
                    shifted_anchor[0] - 3,
                    shifted_anchor[1] - 1,
                    3,
                )
            elif pose_id == "profile_right" and anchor_name == "right_eye":
                aperture = ReferenceEyeAperture(
                    shifted_anchor[0] + 1,
                    shifted_anchor[1] - 1,
                    3,
                )
            elif pose_id in {"profile_left", "profile_right"}:
                aperture = None
            else:
                aperture = self._reference_eye_aperture(canvas, shifted_anchor)
            if aperture is not None:
                key = (aperture.left, aperture.top, aperture.width, aperture.height)
                if key not in seen_apertures:
                    seen_apertures.add(key)
                    eye_layouts.append((anchor_name, aperture))

        # Rear views and occluded action poses still carry approximate anchors.
        # Existing cool/white eye pixels are the authority for face visibility.
        if not eye_layouts:
            mouth_hash, mouth_count = self._reference_mouth_pixel_evidence(
                canvas,
                mouth_anchor,
            )
            return ReferenceFaceEvidence(
                body_pixel_sha256=body_pixel_sha256,
                mouth_pixel_sha256=mouth_hash,
                mouth_painted_cells=mouth_count,
            )

        blink = state.blink_phase >= 0.965
        eye_aim = self._reference_eye_aim(state)
        expression = get_expression(state.expression)
        blue_cells = []
        blink_painted_cells = 0
        for anchor_name, aperture in eye_layouts:
            eye_left = aperture.left
            eye_top = aperture.top
            eye_right = eye_left + aperture.width
            eye_index = 0 if anchor_name == "left_eye" else 1
            skin = self._sample_reference_skin(
                canvas,
                eye_left + aperture.width // 2,
                eye_top,
            )
            for y in range(eye_top, eye_top + aperture.height):
                for x in range(eye_left, eye_right):
                    color = skin if blink else REFERENCE_EYE_WHITE
                    layer = "reference_blink" if blink else "reference_eye_white"
                    canvas.set(x, y, "#", color, layer)
                    if blink:
                        blink_painted_cells += 1

            if blink:
                line_start = eye_left + 1 if aperture.width > 2 else eye_left
                line_end = eye_right - 1 if aperture.width > 2 else eye_right
                for x in range(line_start, line_end):
                    canvas.set(
                        x,
                        eye_top + aperture.height - 1,
                        "#",
                        REFERENCE_BROW,
                        "reference_blink",
                    )
            else:
                blue_x = max(
                    eye_left,
                    min(eye_right - 1, eye_left + aperture.width // 2 + eye_aim),
                )
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
                    blue_cells.append(LocalPointV1(blue_x, y))

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
        mouth_hash, mouth_count = self._reference_mouth_pixel_evidence(
            canvas,
            mouth_anchor,
        )
        return ReferenceFaceEvidence(
            eye_apertures=tuple(aperture.span() for _, aperture in eye_layouts),
            eye_blue_cells=tuple(blue_cells),
            blink_painted_cells=blink_painted_cells,
            body_pixel_sha256=body_pixel_sha256,
            mouth_pixel_sha256=mouth_hash,
            mouth_painted_cells=mouth_count,
        )

    @staticmethod
    def _reference_mouth_pixel_evidence(
        canvas: CellCanvas,
        mouth_anchor: Tuple[int, int],
    ) -> Tuple[str, int]:
        """Hash the fixed visible mouth region without a full-canvas Python scan."""

        mouth = hashlib.sha256()
        mouth_count = 0
        anchor_x, anchor_y = mouth_anchor
        for y in range(anchor_y - 3, anchor_y + 2):
            for x in range(anchor_x - 5, anchor_x + 6):
                cell = canvas.get(x, y)
                # Generic character packages can place a small mouth region
                # partly outside their local canvas. Preserve those signed
                # coordinates in the evidence hash instead of rejecting an
                # otherwise valid package.
                mouth.update(struct.pack(">ii", x, y))
                mouth.update(cell.to_bytes() if cell is not None else b"\x00\x00\x00\x00")
                if cell is not None and (
                    cell.layer_id.startswith("reference_mouth")
                    or cell.layer_id == "reference_teeth"
                ):
                    mouth_count += 1
        return mouth.hexdigest(), mouth_count

    def _reference_body_pixel_sha256(
        self,
        canvas: CellCanvas,
        *,
        pose_id: str,
        rendered_head_pose_id: str,
        head_offset_x: int,
        head_offset_y: int,
        staff_visible: bool,
    ) -> str:
        """Hash one deterministic pre-face body graph per visual composition."""

        key = (
            pose_id,
            rendered_head_pose_id,
            int(head_offset_x),
            int(head_offset_y),
            bool(staff_visible),
        )
        digest = self._reference_body_hash_cache.get(key)
        if digest is None:
            digest = hashlib.sha256(canvas.to_frame_bytes()).hexdigest()
            if len(self._reference_body_hash_cache) >= 256:
                self._reference_body_hash_cache.clear()
            self._reference_body_hash_cache[key] = digest
        return digest

    @staticmethod
    def _resolve_presentation_blink(
        *,
        input_active: bool,
        previous_input_active: bool,
        previous_frames_remaining: int,
        input_source: str,
        previous_source: str,
    ) -> Tuple[bool, int, str]:
        """Latch each blink onset for four committed presentation frames."""

        remaining = max(0, int(previous_frames_remaining))
        if input_active and not previous_input_active:
            remaining = max(remaining, 4)
        visible = bool(input_active or remaining > 0)
        next_remaining = max(0, remaining - 1) if visible else 0
        if input_active:
            source = input_source
        elif visible:
            # The hold preserves the originating semantic source. It is a
            # projector timing guarantee, not a new protocol-level blink kind.
            source = previous_source if previous_source != "none" else "scheduler"
        else:
            source = "none"
        return visible, next_remaining, source

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
        aperture = self._reference_eye_aperture(canvas, anchor)
        if aperture is None:
            return None
        return aperture.left, aperture.top

    def _reference_eye_aperture(
        self,
        canvas: CellCanvas,
        anchor: Tuple[int, int],
        allow_sparse: bool = False,
    ) -> Optional[ReferenceEyeAperture]:
        anchor_x, anchor_y = anchor
        candidates = []
        for y in range(anchor_y - 3, anchor_y + 3):
            for x in range(anchor_x - 4, anchor_x + 5):
                if self._is_reference_eye_pixel(canvas.get(x, y)):
                    candidates.append((x, y))
        if not candidates:
            return None
        if len(candidates) == 1:
            if not allow_sparse:
                return None
            center_x, center_y = candidates[0]
            return ReferenceEyeAperture(
                left=center_x - 1,
                top=min(center_y, anchor_y) - 1,
                width=3,
            )
        min_x = min(x for x, _ in candidates)
        max_x = max(x for x, _ in candidates)
        min_y = min(y for _, y in candidates)
        max_y = max(y for _, y in candidates)
        center_x = (min_x + max_x) // 2
        eye_top = (min_y + max_y) // 2
        return ReferenceEyeAperture(left=center_x - 2, top=eye_top, width=5)

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
        # Only the local command path needs a degraded timing fallback. Media
        # and governed speech own state.mouth, including intentional silence.
        if state.speech_mouth_authority == "local_fallback":
            return fallback_speech_shape(
                state.time_seconds - state.speech_started_at,
                state.speech_until - state.speech_started_at,
                state.speech_text or "",
            )
        if state.speech_id is not None:
            return state.mouth
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

    def _fit_reference_scale_to_stage(
        self,
        canvas: CellCanvas,
        root_anchor: Tuple[int, int],
        root_screen: Tuple[float, float],
        requested_scale: float,
    ) -> float:
        """Cap scale so the complete authored silhouette remains reviewable."""

        occupied = [
            (x, y)
            for y, row in enumerate(canvas.cells)
            for x, cell in enumerate(row)
            if cell is not None
        ]
        if not occupied:
            return requested_scale
        min_x = min(point[0] for point in occupied) - REFERENCE_HEAD_MOTION_RESERVE_CELLS
        max_x = max(point[0] for point in occupied) + REFERENCE_HEAD_MOTION_RESERVE_CELLS
        min_y = min(point[1] for point in occupied) - REFERENCE_HEAD_MOTION_RESERVE_CELLS
        max_y = max(point[1] for point in occupied)
        root_x, root_y = root_anchor
        stage_x, stage_y = root_screen
        limits = [requested_scale]

        left_extent = (root_x - min_x) * REFERENCE_POSE_HORIZONTAL_SCALE
        right_extent = (max_x - root_x) * REFERENCE_POSE_HORIZONTAL_SCALE
        top_extent = root_y - min_y
        bottom_extent = max_y - root_y
        if left_extent > 0:
            limits.append(
                (stage_x - REFERENCE_SIDE_MARGIN_CELLS - REFERENCE_RASTER_SAFETY_CELLS)
                / left_extent
            )
        if right_extent > 0:
            limits.append(
                (
                    self.cols
                    - 1
                    - REFERENCE_SIDE_MARGIN_CELLS
                    - REFERENCE_RASTER_SAFETY_CELLS
                    - stage_x
                )
                / right_extent
            )
        if top_extent > 0:
            limits.append(
                (stage_y - REFERENCE_TOP_MARGIN_CELLS - REFERENCE_RASTER_SAFETY_CELLS)
                / top_extent
            )
        if bottom_extent > 0:
            limits.append(
                (
                    self.rows
                    - 1
                    - REFERENCE_BOTTOM_MARGIN_CELLS
                    - REFERENCE_RASTER_SAFETY_CELLS
                    - stage_y
                )
                / bottom_extent
            )
        return max(0.001, min(limits))

    def _resolve_contact_locked_root(
        self,
        presentation: WizardPresentationSnapshot,
        state: WizardState,
        pose_id: str,
        root_anchor: Tuple[int, int],
        base_root_screen: Tuple[float, float],
        render_scale: float,
    ) -> tuple[
        Tuple[float, float],
        int,
        Optional[str],
        Optional[Tuple[float, float]],
        Tuple[float, float],
    ]:
        active_anchor = (
            state.animation_planted_anchor
            if state.animation_root_policy == "contact_locked"
            and state.animation_support_contact != "none"
            and not state.airborne
            else None
        )
        if active_anchor is None:
            offset = tuple(
                self._approach_zero(value, 2.5)
                for value in presentation.contact_root_offset
            )
            return (
                (base_root_screen[0] + offset[0], base_root_screen[1] + offset[1]),
                state.animation_contact_generation,
                None,
                None,
                offset,
            )

        try:
            anchor_local = reference_pose_anchor(
                pose_id,
                active_anchor,
                self.pose_library_path,
            )
        except KeyError:
            return (
                base_root_screen,
                state.animation_contact_generation,
                None,
                None,
                (0.0, 0.0),
            )

        scale_x = render_scale * REFERENCE_POSE_HORIZONTAL_SCALE
        base_anchor = (
            base_root_screen[0] + (anchor_local[0] - root_anchor[0]) * scale_x,
            base_root_screen[1] + (anchor_local[1] - root_anchor[1]) * render_scale,
        )
        same_contact = (
            presentation.contact_generation == state.animation_contact_generation
            and presentation.contact_anchor == active_anchor
            and presentation.contact_lock_stage is not None
        )
        if same_contact:
            lock_stage = presentation.contact_lock_stage
            offset = (
                lock_stage[0] - base_anchor[0],
                lock_stage[1] - base_anchor[1],
            )
        else:
            # Each authored stance establishes a fresh world-space plant.
            # Carrying the previous foot's correction forward double-counts
            # locomotion and eventually walks the silhouette off the stage.
            offset = (0.0, 0.0)
            lock_stage = base_anchor
        return (
            (base_root_screen[0] + offset[0], base_root_screen[1] + offset[1]),
            state.animation_contact_generation,
            active_anchor,
            lock_stage,
            offset,
        )

    @staticmethod
    def _approach_zero(value: float, maximum_step: float) -> float:
        if value > maximum_step:
            return value - maximum_step
        if value < -maximum_step:
            return value + maximum_step
        return 0.0

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
        _effect_phase, effect_intensity = self._reference_magic_effect_state(state)
        full_motion = (
            permission_world is None or permission_world.motion_profile == "full"
        )
        if effect_visible and full_motion and effect_intensity > 0.0 and pose_id is not None:
            try:
                staff_tip = reference_pose_anchor(
                    pose_id,
                    "staff_tip",
                    self.pose_library_path,
                )
            except KeyError:
                staff_tip = None
            if staff_tip is not None:
                phase = state.animation_authored_frame * math.tau / 7.0
                cx, cy = stage_point(*staff_tip)
                stage.set(cx, cy, "#", RGB["gold_light"], "reference_magic_spark")
                spark_count = max(1, round(14 * effect_intensity))
                for idx in range(spark_count):
                    angle = phase + idx * math.tau / 14.0
                    radius = 2 + round((2 + idx % 3) * effect_intensity)
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

    @staticmethod
    def _reference_magic_effect_state(state: WizardState) -> Tuple[str, float]:
        if state.animation_clip_id != "cast_front":
            return "inactive", 0.0
        frame = int(state.animation_authored_frame)
        if 14 <= frame <= 17:
            return "stroke", 1.0
        if 18 <= frame <= 22:
            return "hold", 1.0
        if 23 <= frame <= 27:
            return "recovery", (28 - frame) / 5.0
        return "inactive", 0.0

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
            self.advance_simulation(1.0 / self.fps)
        with self._presentation_lock:
            snapshot = self._capture_render_state_unlocked()
            candidate = self.render_captured_candidate_sync(snapshot, codec)
            return self._commit_render_candidate_unlocked(candidate)

    def render_captured_candidate_sync(
        self,
        state: WizardRenderSnapshot,
        codec: str = "adaptive",
    ) -> WizardRenderCandidate:
        """Rasterize and encode a transaction without mutating committed state."""

        if type(state) is not WizardRenderSnapshot:
            raise TypeError("state must be a WizardRenderSnapshot")
        captured_state = copy.deepcopy(state.state)
        captured_hash = canonical_sha256(captured_state)
        if (
            state.authoritative_state_sha256
            and captured_hash != state.authoritative_state_sha256
        ):
            raise ValueError("render snapshot state does not match its authoritative hash")
        worker_snapshot = WizardRenderSnapshot(
            state=captured_state,
            permission_world=state.permission_world,
            authoritative_state_sha256=captured_hash,
            frame_index=state.frame_index,
            previous_encoded_frame=state.previous_encoded_frame,
            encoder_generation=state.encoder_generation,
            pending_marker_events=state.pending_marker_events,
            presentation=state.presentation,
        )
        frame, presentation, animation_truth = self._render_snapshot(worker_snapshot)
        if codec == "adaptive":
            encoded = encode_frame(
                frame.cells,
                state.previous_encoded_frame,
                state.frame_index,
            )
            frame.codec_tag = encoded.tag
            frame.changed_cells = encoded.changed_cells
            frame.encoded_size = encoded.encoded_size
            frame.is_keyframe = encoded.is_keyframe
            message = encoded.message
            shown_frame = encoded.shown_frame
        else:
            message = struct.pack(">I", frame.frame_index) + frame.cells
            frame.codec_tag = 0
            frame.encoded_size = len(message)
            shown_frame = frame.cells
        return WizardRenderCandidate(
            authoritative_state_sha256=captured_hash,
            base_presentation_generation=worker_snapshot.presentation_generation,
            base_encoder_generation=worker_snapshot.encoder_generation,
            cols=frame.cols,
            rows=frame.rows,
            frame_index=frame.frame_index,
            cells=frame.cells,
            raw_size=frame.raw_size,
            changed_cells=frame.changed_cells,
            codec_tag=frame.codec_tag,
            encoded_size=frame.encoded_size,
            is_keyframe=frame.is_keyframe,
            message=message,
            shown_frame=shown_frame,
            presentation=presentation,
            animation_truth=animation_truth.with_transport(
                codec_tag=frame.codec_tag,
                encoded_size=frame.encoded_size,
                changed_cells=frame.changed_cells,
                is_keyframe=frame.is_keyframe,
            ),
        )

    def commit_render_candidate(
        self,
        candidate: WizardRenderCandidate,
    ) -> Tuple[bytes, WizardCellFrame]:
        """Atomically accept one worker candidate into the presentation stream."""

        with self._presentation_lock:
            return self._commit_render_candidate_unlocked(candidate)

    def _commit_render_candidate_unlocked(
        self,
        candidate: WizardRenderCandidate,
    ) -> Tuple[bytes, WizardCellFrame]:
        if type(candidate) is not WizardRenderCandidate:
            raise TypeError("candidate must be a WizardRenderCandidate")
        if candidate.base_encoder_generation != self._encoder_generation:
            raise ValueError("stale render candidate encoder generation")
        if candidate.authoritative_state_sha256 != canonical_sha256(
            self.controller.current_state()
        ):
            raise ValueError("stale render candidate authoritative state")
        if candidate.frame_index != self.frame_index:
            raise ValueError("stale render candidate frame index")
        self._commit_presentation_unlocked(
            candidate.presentation,
            candidate.base_presentation_generation,
        )
        self._prev_encoded_frame = candidate.shown_frame
        self._encoder_generation += 1
        frame = candidate.frame
        self._update_diagnostics(
            frame,
            None,
        )
        self.frame_index += 1
        return candidate.message, frame

    def _commit_presentation_unlocked(
        self,
        presentation: WizardPresentationSnapshot,
        expected_generation: int,
    ) -> None:
        if expected_generation != self._presentation_generation:
            raise ValueError("stale render candidate presentation generation")
        if presentation.generation != expected_generation + 1:
            raise ValueError("invalid render candidate presentation generation")
        self._display_pose_id = presentation.display_pose_id
        self._last_presentation_state = presentation.last_presentation_state
        self._head_eye_state = presentation.head_eye_state
        self._contact_generation = presentation.contact_generation
        self._contact_anchor = presentation.contact_anchor
        self._contact_lock_stage = presentation.contact_lock_stage
        self._contact_root_offset = presentation.contact_root_offset
        self._blink_input_active = presentation.blink_input_active
        self._blink_visible_frames_remaining = (
            presentation.blink_visible_frames_remaining
        )
        self._blink_source = presentation.blink_source
        consumed = set(presentation.consumed_marker_events)
        if consumed:
            self._pending_presentation_marker_events = [
                event
                for event in self._pending_presentation_marker_events
                if event not in consumed
            ]
        self._presentation_generation = presentation.generation

    @property
    def presentation_generation(self) -> int:
        with self._presentation_lock:
            return self._presentation_generation

    def encode_captured_frame_sync(
        self,
        state: WizardRenderSnapshot | WizardState,
        codec: str = "adaptive",
    ) -> Tuple[bytes, WizardCellFrame]:
        """Compatibility owner path; production workers use pure candidates."""

        with self._presentation_lock:
            snapshot = (
                state
                if type(state) is WizardRenderSnapshot
                else self._capture_render_state_unlocked(state=state)
            )
            candidate = self.render_captured_candidate_sync(snapshot, codec)
            return self._commit_render_candidate_unlocked(candidate)

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
        result = self.controller.apply_command(command)
        if result.ok and command.type == "reset":
            self.reset_presentation_for_authoritative_reset()
        return result

    def apply_command_sync(self, command: WizardCommand) -> CommandResult:
        result = self.controller.apply_command(command)
        if result.ok and command.type == "reset":
            self.reset_presentation_for_authoritative_reset()
        return result

    def reset_presentation_for_authoritative_reset(self) -> None:
        """Discard presentation state that belongs to the pre-reset timeline."""

        with self._presentation_lock:
            state = self.controller.current_state()
            self._prev_encoded_frame = None
            self._encoder_generation += 1
            self._presentation_generation += 1
            self._display_pose_id = None
            self._transition_from_pose_id = None
            self._transition_started_at_frame = self.frame_index
            self._last_presentation_state = None
            self._head_eye_state = HeadEyeState.steady(
                state.facing,
                state.simulation_tick,
            )
            self._contact_generation = -1
            self._contact_anchor = None
            self._contact_lock_stage = None
            self._contact_root_offset = (0.0, 0.0)
            self._pending_presentation_marker_events.clear()
            self._observed_presentation_marker_keys.clear()
            self._observed_presentation_marker_key_set.clear()
            self._last_marker_observation_tick = state.simulation_tick
            self._blink_input_active = False
            self._blink_visible_frames_remaining = 0
            self._blink_source = "none"

    def reset_encoder(self) -> None:
        with self._presentation_lock:
            self._prev_encoded_frame = None
            self._encoder_generation += 1
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
            "presented_facing": (
                presentation.presented_facing if presentation else state["facing"]
            ),
            "head_eye_phase": (
                presentation.head_eye_phase if presentation else "steady"
            ),
            "velocity": state["velocity"],
            "target_point": state["target_point"],
            "walk_phase": state["walk_phase"],
            "current_action": state["action"],
            "current_expression": state["expression"],
            "mouth_state": (
                presentation.rendered_mouth_shape
                if presentation
                else state["mouth"]
            ),
            "mouth_command_state": state["mouth"],
            "speech_mouth_authority": state["speech_mouth_authority"],
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
