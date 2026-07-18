from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable, Tuple

from .animation_trace import AnimationTruthTraceV1


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
    maximum_root_residual_cells: float = 1e-6,
) -> ContactVerificationReportV1:
    """Verify contact locks from accepted atomic presentation records."""

    rows = tuple(records)
    issues = []
    stance_origins = {}
    stance_identity = {}
    contact_frames = 0
    max_drift = 0.0
    max_root_residual = 0.0
    previous_frame = None
    previous_generation = -1

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

    return ContactVerificationReportV1(
        schema="contact_verification_report_v1",
        schema_version=1,
        frame_count=len(rows),
        stance_count=len(stance_origins),
        contact_frame_count=contact_frames,
        maximum_planted_drift_cells=max_drift,
        maximum_root_residual_cells=max_root_residual,
        issues=tuple(issues),
    )


def _support_matches_anchor(support: str, anchor: str) -> bool:
    if support == "left_foot":
        return anchor == "left_foot"
    if support == "right_foot":
        return anchor == "right_foot"
    if support == "both_feet":
        return anchor in {"left_foot", "right_foot"}
    if support == "staff":
        return anchor == "staff_tip"
    return False


__all__ = [
    "ContactVerificationIssueV1",
    "ContactVerificationReportV1",
    "verify_contact_trace",
]
