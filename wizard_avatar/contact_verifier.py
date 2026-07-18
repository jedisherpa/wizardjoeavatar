from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import (
    FrozenSet,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from .animation_trace import AnimationTruthTraceV1, RasterSpanV1
from .floor import build_background
from .palette import ENV_RGB


DEFAULT_LOCOMOTION_CLIP_IDS = frozenset(
    {
        "walk_front",
        "walk_back",
        "run_charge_front",
        "run_land_front",
    }
)
DEFAULT_BACKGROUND_RGB_VALUES = frozenset(ENV_RGB.values())


@dataclass(frozen=True)
class DecodedRasterFrameV1:
    """One decoded ASCILINE cell raster used as visible contact evidence."""

    cols: int
    rows: int
    cells: bytes


@dataclass(frozen=True)
class ContactVerificationIssueV1:
    frame_index: int
    code: str
    detail: str


@dataclass(frozen=True)
class ContactVerificationReportV1:
    schema: str
    schema_version: int
    frame_count: int
    stance_count: int
    contact_frame_count: int
    maximum_planted_drift_cells: float
    maximum_planted_raster_span_drift_cells: float
    maximum_root_residual_cells: float
    issues: Tuple[ContactVerificationIssueV1, ...]

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_mapping(self) -> dict:
        result = asdict(self)
        result["passed"] = self.passed
        return result


def verify_contact_trace(
    records: Iterable[AnimationTruthTraceV1],
    *,
    maximum_drift_cells: float = 1.0,
    maximum_raster_span_drift_cells: float = 1.0,
    maximum_root_residual_cells: float = 1e-6,
    decoded_frames: Optional[
        Mapping[int, Union[DecodedRasterFrameV1, bytes]]
    ] = None,
    raster_size: Optional[Tuple[int, int]] = None,
    strict_raster_evidence: bool = False,
    background_rgb_values: Optional[Sequence[Tuple[int, int, int]]] = None,
    locomotion_clip_ids: Iterable[str] = DEFAULT_LOCOMOTION_CLIP_IDS,
) -> ContactVerificationReportV1:
    """Verify contact locks from accepted atomic presentation records.

    Existing trace-only callers remain valid. Supplying ``decoded_frames`` enables
    visible raster checks; ``strict_raster_evidence`` additionally makes absent
    decoded frames, dimensions, and planted spans explicit failures.
    """

    rows = tuple(records)
    issues = []
    stance_origins = {}
    stance_raster_origins = {}
    stance_identity = {}
    contact_frames = 0
    max_drift = 0.0
    max_raster_span_drift = 0.0
    max_root_residual = 0.0
    previous_frame = None
    previous_generation = -1
    seen_locomotion_stances = set()
    previous_locomotion_support = None
    raster_checks_enabled = strict_raster_evidence or decoded_frames is not None
    background_rgbs: FrozenSet[Tuple[int, int, int]] = frozenset(
        DEFAULT_BACKGROUND_RGB_VALUES
        if background_rgb_values is None
        else background_rgb_values
    )
    locomotion_clips = frozenset(locomotion_clip_ids)

    for record in rows:
        if previous_frame is not None and record.frame_index <= previous_frame:
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "frame_order",
                    "frame indexes must increase strictly",
                )
            )
        previous_frame = record.frame_index
        if record.contact_generation < previous_generation:
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "contact_generation_order",
                    "contact generation moved backward",
                )
            )
        previous_generation = max(previous_generation, record.contact_generation)

        expected_x = (
            record.semantic_root_stage.x + record.contact_root_offset_stage.x
        )
        expected_y = (
            record.semantic_root_stage.y + record.contact_root_offset_stage.y
        )
        root_residual = math.hypot(
            record.presented_root_stage.x - expected_x,
            record.presented_root_stage.y - expected_y,
        )
        max_root_residual = max(max_root_residual, root_residual)
        if root_residual > maximum_root_residual_cells:
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "unexplained_root_residual",
                    "presented root differs from semantic root plus contact correction",
                )
            )

        if record.support_contact == "none":
            if record.planted_anchor is not None or record.planted_anchor_stage is not None:
                issues.append(
                    ContactVerificationIssueV1(
                        record.frame_index,
                        "released_contact_has_anchor",
                        "released contact must not claim a planted anchor",
                    )
                )
            continue

        contact_frames += 1
        if record.altitude > 1e-6:
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "airborne_contact",
                    "airborne frames cannot claim planted support",
                )
            )
        if record.planted_anchor is None or record.planted_anchor_stage is None:
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "missing_planted_anchor",
                    "contact frame is missing planted-anchor geometry",
                )
            )
            continue
        if not _support_matches_anchor(record.support_contact, record.planted_anchor):
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "support_anchor_mismatch",
                    "support contact does not match the planted anchor",
                )
            )

        identity = (record.support_contact, record.planted_anchor)
        previous_identity = stance_identity.setdefault(record.contact_generation, identity)
        if previous_identity != identity:
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "contact_changed_without_generation",
                    "support identity changed without a new contact generation",
                )
            )
        # Root policy controls correction, not the truth of an explicit planted claim.
        point = record.planted_anchor_stage
        origin = stance_origins.setdefault(
            record.contact_generation,
            (point.x, point.y),
        )
        drift = math.hypot(point.x - origin[0], point.y - origin[1])
        max_drift = max(max_drift, drift)
        if drift > maximum_drift_cells:
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "planted_anchor_drift",
                    "planted anchor drifted {:.6f} output cells".format(drift),
                )
            )

        if (
            record.animation_clip_id in locomotion_clips
            and record.support_contact in {"left_foot", "right_foot"}
            and record.contact_generation not in seen_locomotion_stances
        ):
            seen_locomotion_stances.add(record.contact_generation)
            if previous_locomotion_support == record.support_contact:
                issues.append(
                    ContactVerificationIssueV1(
                        record.frame_index,
                        "locomotion_support_not_alternating",
                        "successive single-foot locomotion stances must alternate",
                    )
                )
            previous_locomotion_support = record.support_contact

        if not raster_checks_enabled or record.animation_root_policy != "contact_locked":
            continue

        span = record.planted_anchor_raster_span
        if span is None:
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "missing_planted_raster_span",
                    "contact-locked frame is missing a planted-anchor raster span",
                )
            )
            continue

        raster_origin = stance_raster_origins.setdefault(
            record.contact_generation,
            span,
        )
        raster_drift = _raster_span_drift(span, raster_origin)
        max_raster_span_drift = max(max_raster_span_drift, raster_drift)
        if raster_drift > maximum_raster_span_drift_cells:
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "planted_raster_span_drift",
                    "planted raster span drifted {:.6f} output cells".format(
                        raster_drift
                    ),
                )
            )

        decoded = None if decoded_frames is None else decoded_frames.get(record.frame_index)
        if decoded is None:
            if strict_raster_evidence:
                issues.append(
                    ContactVerificationIssueV1(
                        record.frame_index,
                        "missing_decoded_raster_frame",
                        "contact-locked frame has no supplied decoded raster evidence",
                    )
                )
            continue

        raster = _coerce_decoded_raster(decoded, raster_size)
        if raster is None:
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "missing_decoded_raster_size",
                    "raw decoded frame bytes require an explicit raster_size",
                )
            )
            continue
        expected_size = raster.cols * raster.rows * 4
        if raster.cols <= 0 or raster.rows <= 0 or len(raster.cells) != expected_size:
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "invalid_decoded_raster_frame_size",
                    "decoded raster size does not match cols * rows * 4 bytes",
                )
            )
            continue
        if not _raster_span_in_bounds(span, raster.cols, raster.rows):
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "planted_raster_span_out_of_bounds",
                    "planted raster span falls outside the decoded frame",
                )
            )
            continue
        if not _span_has_foreground_color(raster, span, background_rgbs):
            issues.append(
                ContactVerificationIssueV1(
                    record.frame_index,
                    "blank_planted_raster_span",
                    "planted raster span contains only background-colored cells",
                )
            )

    return ContactVerificationReportV1(
        schema="contact_verification_report_v1",
        schema_version=1,
        frame_count=len(rows),
        stance_count=len(stance_origins),
        contact_frame_count=contact_frames,
        maximum_planted_drift_cells=max_drift,
        maximum_planted_raster_span_drift_cells=max_raster_span_drift,
        maximum_root_residual_cells=max_root_residual,
        issues=tuple(issues),
    )


def _support_matches_anchor(support: str, anchor: str) -> bool:
    if support == "left_foot":
        return anchor == "left_foot"
    if support == "right_foot":
        return anchor == "right_foot"
    if support == "both_feet":
        return anchor in {"left_foot", "right_foot", "staff_tip"}
    if support == "staff":
        return anchor == "staff_tip"
    return False


def _coerce_decoded_raster(
    value: Union[DecodedRasterFrameV1, bytes],
    raster_size: Optional[Tuple[int, int]],
) -> Optional[DecodedRasterFrameV1]:
    if isinstance(value, DecodedRasterFrameV1):
        return value
    if raster_size is None:
        return None
    return DecodedRasterFrameV1(
        cols=raster_size[0],
        rows=raster_size[1],
        cells=value,
    )


def _raster_span_drift(current: RasterSpanV1, origin: RasterSpanV1) -> float:
    return float(
        max(
            abs(current.min_x - origin.min_x),
            abs(current.max_x - origin.max_x),
            abs(current.min_y - origin.min_y),
            abs(current.max_y - origin.max_y),
        )
    )


def _raster_span_in_bounds(span: RasterSpanV1, cols: int, rows: int) -> bool:
    return (
        0 <= span.min_x <= span.max_x < cols
        and 0 <= span.min_y <= span.max_y < rows
    )


def _span_has_foreground_color(
    raster: DecodedRasterFrameV1,
    span: RasterSpanV1,
    background_rgbs: FrozenSet[Tuple[int, int, int]],
) -> bool:
    authored_background = build_background(raster.cols, raster.rows).to_frame_bytes()
    for y in range(span.min_y, span.max_y + 1):
        for x in range(span.min_x, span.max_x + 1):
            offset = (y * raster.cols + x) * 4
            rgb = tuple(raster.cells[offset + 1 : offset + 4])
            cell = raster.cells[offset : offset + 4]
            background_cell = authored_background[offset : offset + 4]
            if cell != background_cell and rgb not in background_rgbs:
                return True
    return False


__all__ = [
    "ContactVerificationIssueV1",
    "ContactVerificationReportV1",
    "DecodedRasterFrameV1",
    "verify_contact_trace",
]
