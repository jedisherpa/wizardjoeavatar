from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping
from pathlib import Path

from .animation_trace import (
    ANIMATION_TRUTH_TRACE_SCHEMA,
    ANIMATION_TRUTH_TRACE_VERSION,
    AnimationTruthTraceV1,
    LocalPointV1,
    RasterSpanV1,
    StagePointV1,
)
from .frame_source import (
    PRESENTATION_MARKER_IDS,
    ProceduralWizardFrameSource,
    WizardPresentationSnapshot,
    WizardRenderSnapshot,
)
from .hd_pose_artifact import HDPoseLibrary
from .head_eye import HeadEyeState
from .models import WizardCellFrame, WizardPresentationState


class HDPoseFrameSource(ProceduralWizardFrameSource):
    """Render package-owned RGBA poses through the authoritative Python hub."""

    def __init__(
        self,
        *,
        fps: float,
        character_package_path: Path,
    ) -> None:
        package_path = Path(character_package_path).resolve()
        from .character_package import load_character_package

        package = load_character_package(package_path)
        if package.renderer_adapter_id != "asciline.hd_rgba_pose.v1":
            raise ValueError("HDPoseFrameSource requires the HD RGBA adapter")
        index_path = package.assets["hd_pose_library_index"].path
        library = HDPoseLibrary(index_path, cache_size_per_shard=3)
        width, height = library.canvas_size
        super().__init__(
            cols=width,
            rows=height,
            fps=fps,
            character_package_path=package_path,
        )
        self.render_mode = "rgba"
        self.hd_library = library
        self._hd_index = library.index
        self._pose_metadata = {
            str(item["pose_id"]): item
            for item in self._hd_index["poses"]
            if isinstance(item, Mapping) and isinstance(item.get("pose_id"), str)
        }
        profile = self._hd_index["profile"]
        split_x = int(profile.get("identity_split_x", width // 2))
        identity_side = str(self._hd_index.get("identity_side", ""))
        if (
            profile.get("coordinate_policy") == "preserve_shared_source_canvas"
            and 0 < split_x < width
            and identity_side == "left"
        ):
            self._presentation_offset_x = round(width / 2 - split_x / 2)
            self._source_root_x = split_x // 2
        elif (
            profile.get("coordinate_policy") == "preserve_shared_source_canvas"
            and 0 < split_x < width
            and identity_side == "right"
        ):
            self._presentation_offset_x = round(
                width / 2 - (split_x + width) / 2
            )
            self._source_root_x = (split_x + width) // 2
        else:
            self._presentation_offset_x = 0
            self._source_root_x = width // 2

    def _render_snapshot(
        self,
        snapshot: WizardRenderSnapshot,
    ) -> tuple[
        WizardCellFrame,
        WizardPresentationSnapshot,
        AnimationTruthTraceV1,
    ]:
        state = copy.deepcopy(snapshot.state)
        state.reconcile_compatibility_state()
        authored_pose_id = state.pose_id
        pose_id = (
            authored_pose_id
            if authored_pose_id in self.hd_library.pose_shards
            else self.character_package.default_pose_id
        )
        metadata = self._pose_metadata[pose_id]
        source_bbox = tuple(int(value) for value in metadata["source_bbox"])
        offset_x, offset_y = self._presentation_offset(state, source_bbox)
        rgba = _translate_rgba(
            self.hd_library.load_rgba(pose_id),
            self.cols,
            self.rows,
            offset_x,
            offset_y,
        )
        frame = WizardCellFrame(
            cols=self.cols,
            rows=self.rows,
            frame_index=snapshot.frame_index,
            cells=rgba,
            raw_size=len(rgba),
        )

        root_local = LocalPointV1(
            self._source_root_x,
            max(0, min(self.rows - 1, source_bbox[3] - 1)),
        )
        root_stage = StagePointV1(
            root_local.x + offset_x,
            root_local.y + offset_y,
        )
        silhouette = RasterSpanV1(
            min_x=max(0, source_bbox[0] + offset_x),
            max_x=min(self.cols - 1, source_bbox[2] - 1 + offset_x),
            min_y=max(0, source_bbox[1] + offset_y),
            max_y=min(self.rows - 1, source_bbox[3] - 1 + offset_y),
        )
        presented_facing = self.animation_graph.pose_catalog[pose_id].facing
        head_eye_state = HeadEyeState.steady(
            presented_facing,
            state.simulation_tick,
        )
        last_presentation_state = WizardPresentationState(
            screen_x=root_stage.x,
            screen_y=root_stage.y,
            display_scale=1.0,
            pose_id=pose_id,
            last_pose_id=snapshot.presentation.display_pose_id or pose_id,
            pose_transition_progress=state.pose_transition_progress,
            animation_clip_id=state.animation_clip_id,
            animation_node_id=state.animation_node_id,
            animation_transition_id=state.animation_transition_id,
            presented_facing=presented_facing,
            gaze_aim=state.gaze_aim,
            head_eye_phase="steady",
            rendered_mouth_shape=state.mouth,
            rendered_head_pose_id=pose_id,
            turn_progress_milli=1000,
            blink_source="none",
            head_offset_x=0,
            head_offset_y=0,
        )
        presentation = WizardPresentationSnapshot(
            generation=snapshot.presentation_generation + 1,
            display_pose_id=pose_id,
            last_presentation_state=last_presentation_state,
            head_eye_state=head_eye_state,
            contact_generation=state.animation_contact_generation,
            contact_anchor=None,
            contact_lock_stage=None,
            contact_root_offset=(0.0, 0.0),
            consumed_marker_events=snapshot.pending_marker_events,
            blink_input_active=False,
            blink_visible_frames_remaining=0,
            blink_source="none",
            pending_scheduler_blink=False,
        )
        digest = hashlib.sha256(rgba).hexdigest()
        truth = AnimationTruthTraceV1(
            schema=ANIMATION_TRUTH_TRACE_SCHEMA,
            schema_version=ANIMATION_TRUTH_TRACE_VERSION,
            simulation_tick=state.simulation_tick,
            state_revision=state.state_revision,
            frame_index=frame.frame_index,
            authoritative_state_sha256=snapshot.authoritative_state_sha256,
            authored_pose_id=authored_pose_id,
            rendered_pose_id=pose_id,
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
            active_markers=tuple(
                marker
                for marker in state.animation_active_markers
                if marker not in PRESENTATION_MARKER_IDS
            ),
            presentation_marker_events=snapshot.pending_marker_events,
            contact_generation=state.animation_contact_generation,
            contact_started_tick=state.animation_contact_started_tick,
            world_root_x=state.world_position["x"],
            world_root_z=state.world_position["z"],
            altitude=state.altitude,
            semantic_root_stage=root_stage,
            contact_root_offset_stage=StagePointV1(0.0, 0.0),
            presented_root_stage=root_stage,
            render_scale=1.0,
            render_scale_x=1.0,
            render_scale_y=1.0,
            root_anchor_local=root_local,
            planted_anchor_local=None,
            planted_anchor_stage=None,
            planted_anchor_raster_span=None,
            staff_tip_local=None,
            staff_tip_stage=None,
            staff_tip_raster_span=None,
            silhouette_raster_span=silhouette,
            effect_phase="inactive",
            effect_intensity=0.0,
            presented_facing=presented_facing,
            presentation_channels=None,
            performance_motion_profile=state.performance_motion_profile,
            performance_resolution_hash=state.performance_resolution_hash,
            performance_owned_channels=state.performance_owned_channels,
            performance_suppression_codes=state.performance_suppression_codes,
            frame_sha256=digest,
            # The dense RGBA path records its full SHA-256 above. Computing
            # the legacy byte-wise FNV value would consume the frame budget.
            frame_fnv1a32="unavailable:hd-rgba",
            codec_tag=0,
            encoded_size=0,
            changed_cells=0,
            is_keyframe=False,
        )
        return frame, presentation, truth

    def _presentation_offset(
        self,
        state,
        source_bbox: tuple[int, int, int, int],
    ) -> tuple[int, int]:
        world_x = round(float(state.world_position["x"]) * self.cols / 16.0)
        world_y = round(
            (5.0 - float(state.world_position["z"])) * self.rows / 24.0
            - float(state.altitude) * self.rows / 7.0
        )
        min_x = -source_bbox[0]
        max_x = self.cols - source_bbox[2]
        min_y = -source_bbox[1]
        max_y = self.rows - source_bbox[3]
        return (
            max(min_x, min(max_x, self._presentation_offset_x + world_x)),
            max(min_y, min(max_y, world_y)),
        )


def _translate_rgba(
    frame: bytes,
    width: int,
    height: int,
    offset_x: int,
    offset_y: int,
) -> bytes:
    expected = width * height * 4
    if len(frame) != expected:
        raise ValueError("HD RGBA source frame size mismatch")
    if offset_x == 0 and offset_y == 0:
        return frame
    translated = bytearray(expected)
    source_start_x = max(0, -offset_x)
    source_end_x = min(width, width - offset_x)
    source_start_y = max(0, -offset_y)
    source_end_y = min(height, height - offset_y)
    copy_width = source_end_x - source_start_x
    if copy_width <= 0 or source_end_y <= source_start_y:
        return bytes(translated)
    row_bytes = copy_width * 4
    destination_start_x = source_start_x + offset_x
    for source_y in range(source_start_y, source_end_y):
        destination_y = source_y + offset_y
        source_offset = (source_y * width + source_start_x) * 4
        destination_offset = (
            destination_y * width + destination_start_x
        ) * 4
        translated[destination_offset : destination_offset + row_bytes] = (
            frame[source_offset : source_offset + row_bytes]
        )
    return bytes(translated)


__all__ = ["HDPoseFrameSource"]
