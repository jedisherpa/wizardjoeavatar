from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Mapping, Optional, Tuple


ANIMATION_TRUTH_TRACE_SCHEMA = "animation_truth_trace_v1"
ANIMATION_TRUTH_TRACE_VERSION = 1
ANIMATION_TRUTH_TRACE_CAPACITY = 2048


@dataclass(frozen=True)
class StagePointV1:
    x: float
    y: float


@dataclass(frozen=True)
class LocalPointV1:
    x: int
    y: int


@dataclass(frozen=True)
class RasterSpanV1:
    min_x: int
    max_x: int
    min_y: int
    max_y: int


@dataclass(frozen=True)
class AnimationMarkerEventV1:
    """One authored marker crossing retained until an accepted presentation."""

    marker_id: str
    simulation_tick: int
    state_revision: int
    animation_node_id: str
    animation_clip_id: str
    animation_clip_tick: int
    animation_sample_index: int
    animation_sample_frame: int
    animation_authored_frame: int
    animation_phase_numerator: int
    animation_phase_denominator: int


@dataclass(frozen=True)
class PresentationChannelsV1:
    """Face and acting channels painted into the paired presentation frame."""

    head_eye_phase: str
    gaze_aim: int
    gaze_vertical_aim: int
    gaze_authoritative: bool
    blink_closed: bool
    expression: str
    rendered_mouth_shape: str
    speech_mouth_authority: str
    speech_id: Optional[str]
    locomotion: str
    action: str
    rendered_head_pose_id: str
    turn_progress_milli: int
    blink_source: str
    eye_apertures: Tuple[RasterSpanV1, ...]
    eye_blue_cells: Tuple[LocalPointV1, ...]
    blink_painted_cells: int
    body_pixel_sha256: str
    mouth_pixel_sha256: str
    mouth_painted_cells: int
    head_offset_x: int
    head_offset_y: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PresentationChannelsV1":
        expected = {item.name for item in fields(cls)}
        legacy_added = {
            "rendered_head_pose_id",
            "turn_progress_milli",
            "blink_source",
            "eye_apertures",
            "eye_blue_cells",
            "blink_painted_cells",
            "head_offset_x",
            "head_offset_y",
            "speech_id",
        }
        pixel_evidence_added = {
            "body_pixel_sha256",
            "mouth_pixel_sha256",
            "mouth_painted_cells",
        }
        supplied = set(value) if isinstance(value, Mapping) else set()
        compatible = {
            frozenset(expected),
            frozenset(expected.difference(pixel_evidence_added)),
            frozenset(expected.difference(legacy_added | pixel_evidence_added)),
        }
        if not isinstance(value, Mapping) or frozenset(supplied) not in compatible:
            raise ValueError(
                "invalid presentation channel fields: missing={} extra={}".format(
                    sorted(expected.difference(supplied)),
                    sorted(supplied.difference(expected)),
                )
            )
        payload = dict(value)
        payload.setdefault("rendered_head_pose_id", "legacy_unspecified")
        payload.setdefault("turn_progress_milli", 1000)
        payload.setdefault("blink_source", "legacy_unspecified")
        payload.setdefault("eye_apertures", ())
        payload.setdefault("eye_blue_cells", ())
        payload.setdefault("blink_painted_cells", 0)
        payload.setdefault("body_pixel_sha256", "legacy_unspecified")
        payload.setdefault("mouth_pixel_sha256", "legacy_unspecified")
        payload.setdefault("mouth_painted_cells", 0)
        payload.setdefault("head_offset_x", 0)
        payload.setdefault("head_offset_y", 0)
        payload.setdefault("speech_id", None)
        payload["eye_apertures"] = tuple(
            item if isinstance(item, RasterSpanV1) else RasterSpanV1(**item)
            for item in payload["eye_apertures"]
        )
        payload["eye_blue_cells"] = tuple(
            item if isinstance(item, LocalPointV1) else LocalPointV1(**item)
            for item in payload["eye_blue_cells"]
        )
        result = cls(**payload)
        if result.head_eye_phase not in {"steady", "leading", "turning", "settling"}:
            raise ValueError("unsupported head-eye phase")
        for name in ("gaze_aim", "gaze_vertical_aim"):
            aim = getattr(result, name)
            if isinstance(aim, bool) or aim not in {-1, 0, 1}:
                raise ValueError("{} must be -1, 0, or 1".format(name))
        if not isinstance(result.gaze_authoritative, bool):
            raise ValueError("gaze_authoritative must be boolean")
        if result.speech_id is not None and not isinstance(result.speech_id, str):
            raise ValueError("speech_id must be text or null")
        if not isinstance(result.blink_closed, bool):
            raise ValueError("blink_closed must be boolean")
        if (
            isinstance(result.turn_progress_milli, bool)
            or not isinstance(result.turn_progress_milli, int)
            or not 0 <= result.turn_progress_milli <= 1000
        ):
            raise ValueError("turn_progress_milli must be between 0 and 1000")
        if result.blink_source not in {
            "none",
            "scheduler",
            "turn",
            "scheduler+turn",
            "legacy_unspecified",
        }:
            raise ValueError("unsupported blink_source")
        if (
            isinstance(result.blink_painted_cells, bool)
            or not isinstance(result.blink_painted_cells, int)
            or result.blink_painted_cells < 0
        ):
            raise ValueError("blink_painted_cells must be nonnegative")
        if (
            isinstance(result.mouth_painted_cells, bool)
            or not isinstance(result.mouth_painted_cells, int)
            or result.mouth_painted_cells < 0
        ):
            raise ValueError("mouth_painted_cells must be nonnegative")
        for name in ("body_pixel_sha256", "mouth_pixel_sha256"):
            digest = getattr(result, name)
            if digest != "legacy_unspecified" and not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("{} must be a SHA-256 digest".format(name))
        for name in ("head_offset_x", "head_offset_y"):
            offset = getattr(result, name)
            if isinstance(offset, bool) or not isinstance(offset, int) or abs(offset) > 2:
                raise ValueError("{} must be an integer within two cells".format(name))
        for aperture in result.eye_apertures:
            if aperture.min_x > aperture.max_x or aperture.min_y > aperture.max_y:
                raise ValueError("eye aperture bounds are inverted")
        for point in result.eye_blue_cells:
            if not any(
                aperture.min_x <= point.x <= aperture.max_x
                and aperture.min_y <= point.y <= aperture.max_y
                for aperture in result.eye_apertures
            ):
                raise ValueError("blue eye cell escaped every aperture")
        for name in (
            "expression",
            "rendered_mouth_shape",
            "speech_mouth_authority",
            "locomotion",
            "action",
            "rendered_head_pose_id",
        ):
            item = getattr(result, name)
            if not isinstance(item, str) or not item or len(item) > 128:
                raise ValueError("{} must be bounded non-empty text".format(name))
        return result


@dataclass(frozen=True)
class AnimationTruthTraceV1:
    """Atomic provenance for one accepted ASCILINE presentation frame."""

    schema: str
    schema_version: int
    simulation_tick: int
    state_revision: int
    frame_index: int
    authoritative_state_sha256: str
    authored_pose_id: str
    rendered_pose_id: str
    animation_node_id: str
    animation_clip_id: str
    animation_clip_tick: int
    animation_sample_index: int
    animation_sample_frame: int
    animation_authored_frame: int
    animation_phase_numerator: int
    animation_phase_denominator: int
    animation_root_policy: str
    support_contact: str
    planted_anchor: Optional[str]
    active_markers: Tuple[str, ...]
    presentation_marker_events: Tuple[AnimationMarkerEventV1, ...]
    contact_generation: int
    contact_started_tick: int
    world_root_x: float
    world_root_z: float
    altitude: float
    semantic_root_stage: StagePointV1
    contact_root_offset_stage: StagePointV1
    presented_root_stage: StagePointV1
    render_scale: float
    render_scale_x: float
    render_scale_y: float
    root_anchor_local: LocalPointV1
    planted_anchor_local: Optional[LocalPointV1]
    planted_anchor_stage: Optional[StagePointV1]
    planted_anchor_raster_span: Optional[RasterSpanV1]
    staff_tip_local: Optional[LocalPointV1]
    staff_tip_stage: Optional[StagePointV1]
    staff_tip_raster_span: Optional[RasterSpanV1]
    silhouette_raster_span: Optional[RasterSpanV1]
    effect_phase: str
    effect_intensity: float
    presented_facing: str
    presentation_channels: Optional[PresentationChannelsV1]
    performance_motion_profile: str
    performance_resolution_hash: Optional[str]
    performance_owned_channels: Tuple[str, ...]
    performance_suppression_codes: Tuple[str, ...]
    frame_sha256: str
    frame_fnv1a32: str
    codec_tag: int
    encoded_size: int
    changed_cells: int
    is_keyframe: bool

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AnimationTruthTraceV1":
        expected = {item.name for item in fields(cls)}
        supplied = set(value)
        optional_compatibility_fields = (
            "presentation_marker_events",
            "presentation_channels",
            "silhouette_raster_span",
            "performance_motion_profile",
            "performance_resolution_hash",
            "performance_owned_channels",
            "performance_suppression_codes",
        )
        compatible_field_sets = {
            frozenset(
                expected.difference(
                    field
                    for index, field in enumerate(optional_compatibility_fields)
                    if mask & (1 << index)
                )
            )
            for mask in range(1 << len(optional_compatibility_fields))
        }
        if frozenset(supplied) not in compatible_field_sets:
            missing = sorted(expected.difference(supplied))
            extra = sorted(set(value).difference(expected))
            raise ValueError(
                "invalid animation truth fields: missing={} extra={}".format(
                    missing,
                    extra,
                )
            )
        payload = dict(value)
        payload["active_markers"] = tuple(payload["active_markers"])
        payload.setdefault("presentation_marker_events", ())
        payload.setdefault("presentation_channels", None)
        payload.setdefault("silhouette_raster_span", None)
        payload.setdefault("performance_motion_profile", "none")
        payload.setdefault("performance_resolution_hash", None)
        payload.setdefault("performance_owned_channels", ())
        payload.setdefault("performance_suppression_codes", ())
        payload["performance_owned_channels"] = tuple(
            payload["performance_owned_channels"]
        )
        payload["performance_suppression_codes"] = tuple(
            payload["performance_suppression_codes"]
        )
        payload["presentation_marker_events"] = tuple(
            AnimationMarkerEventV1(**event)
            for event in payload["presentation_marker_events"]
        )
        if payload["presentation_channels"] is not None:
            payload["presentation_channels"] = PresentationChannelsV1.from_mapping(
                payload["presentation_channels"]
            )
        for name in (
            "semantic_root_stage",
            "contact_root_offset_stage",
            "presented_root_stage",
            "planted_anchor_stage",
            "staff_tip_stage",
        ):
            point = payload[name]
            payload[name] = None if point is None else StagePointV1(**point)
        for name in (
            "root_anchor_local",
            "planted_anchor_local",
            "staff_tip_local",
        ):
            point = payload[name]
            payload[name] = None if point is None else LocalPointV1(**point)
        for name in (
            "planted_anchor_raster_span",
            "staff_tip_raster_span",
            "silhouette_raster_span",
        ):
            span = payload[name]
            payload[name] = None if span is None else RasterSpanV1(**span)
        result = cls(**payload)
        if result.schema != ANIMATION_TRUTH_TRACE_SCHEMA:
            raise ValueError("unsupported animation truth schema")
        if result.schema_version != ANIMATION_TRUTH_TRACE_VERSION:
            raise ValueError("unsupported animation truth schema version")
        if result.performance_motion_profile not in {
            "none",
            "full",
            "reduced",
            "still",
        }:
            raise ValueError("unsupported performance motion profile")
        if (
            result.performance_resolution_hash is not None
            and not re.fullmatch(
                r"sha256:[0-9a-f]{64}",
                result.performance_resolution_hash,
            )
        ):
            raise ValueError("performance resolution hash must be qualified SHA-256")
        for name in (
            "performance_owned_channels",
            "performance_suppression_codes",
        ):
            values = getattr(result, name)
            if tuple(sorted(set(values))) != values:
                raise ValueError("{} must be sorted and unique".format(name))
            if any(
                not isinstance(item, str) or not item or len(item) > 128
                for item in values
            ):
                raise ValueError("{} must contain bounded text".format(name))
        return result

    def with_transport(
        self,
        *,
        codec_tag: int,
        encoded_size: int,
        changed_cells: int,
        is_keyframe: bool,
    ) -> "AnimationTruthTraceV1":
        return replace(
            self,
            codec_tag=codec_tag,
            encoded_size=encoded_size,
            changed_cells=changed_cells,
            is_keyframe=is_keyframe,
        )


def transformed_anchor(
    *,
    root_local: tuple[int, int],
    root_stage: tuple[float, float],
    anchor_local: tuple[int, int],
    local_size: tuple[int, int],
    scale: float,
    horizontal_scale: float,
) -> tuple[StagePointV1, Optional[RasterSpanV1]]:
    """Return continuous and exact nearest-neighbor raster anchor geometry."""

    scale_x = max(0.001, scale * horizontal_scale)
    scale_y = max(0.001, scale)
    origin_x = round(root_stage[0] - root_local[0] * scale_x)
    origin_y = round(root_stage[1] - root_local[1] * scale_y)
    stage_point = StagePointV1(
        x=root_stage[0] + (anchor_local[0] - root_local[0]) * scale_x,
        y=root_stage[1] + (anchor_local[1] - root_local[1]) * scale_y,
    )

    dest_width = max(1, round(local_size[0] * scale_x))
    dest_height = max(1, round(local_size[1] * scale_y))
    x_span = _source_cell_destination_span(anchor_local[0], scale_x, dest_width)
    y_span = _source_cell_destination_span(anchor_local[1], scale_y, dest_height)
    if x_span is None or y_span is None:
        return stage_point, None
    return stage_point, RasterSpanV1(
        min_x=origin_x + x_span[0],
        max_x=origin_x + x_span[1],
        min_y=origin_y + y_span[0],
        max_y=origin_y + y_span[1],
    )


def _source_cell_destination_span(
    source_coordinate: int,
    scale: float,
    destination_size: int,
) -> Optional[tuple[int, int]]:
    first = max(0, math.ceil(source_coordinate * scale))
    last = min(destination_size - 1, math.ceil((source_coordinate + 1) * scale) - 1)
    while first <= last and int(first / scale) != source_coordinate:
        first += 1
    while last >= first and int(last / scale) != source_coordinate:
        last -= 1
    return None if first > last else (first, last)
