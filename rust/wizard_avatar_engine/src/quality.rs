use crate::pose::{analyze_pose_topology, AnchorId, PointF, PoseSample, PoseTopologyMetrics};
use serde::Serialize;

#[derive(Clone, Copy, Debug)]
pub struct FrameQualityThresholds {
    pub maximum_component_step: usize,
    pub minimum_occupancy_ratio: f32,
    pub minimum_visible_source_ratio: f32,
    pub minimum_source_retention_ratio: f32,
    pub maximum_face_anchor_step: f32,
    pub maximum_staff_anchor_step: f32,
    pub maximum_free_foot_step: f32,
}

impl Default for FrameQualityThresholds {
    fn default() -> Self {
        Self {
            maximum_component_step: 2,
            minimum_occupancy_ratio: 0.88,
            minimum_visible_source_ratio: 0.75,
            minimum_source_retention_ratio: 0.94,
            maximum_face_anchor_step: 1.5,
            maximum_staff_anchor_step: 1.5,
            maximum_free_foot_step: 5.0,
        }
    }
}

#[derive(Clone, Debug, Serialize)]
pub struct FrameQualitySnapshot {
    pub transition_id: String,
    pub pose_id: String,
    pub frame_index: u64,
    pub topology: PoseTopologyMetrics,
    pub source_cell_count: usize,
    pub root: PointF,
    pub left_foot: PointF,
    pub right_foot: PointF,
    pub face: PointF,
    pub staff_hand: PointF,
}

impl FrameQualitySnapshot {
    pub fn from_pose(
        transition_id: impl Into<String>,
        pose_id: impl Into<String>,
        frame_index: u64,
        sample: &PoseSample,
    ) -> Result<Self, String> {
        let anchor = |id| {
            sample
                .anchors
                .get(&id)
                .copied()
                .ok_or_else(|| format!("pose is missing {id:?}"))
        };
        let left_eye = anchor(AnchorId::LeftEye)?;
        let right_eye = anchor(AnchorId::RightEye)?;
        Ok(Self {
            transition_id: transition_id.into(),
            pose_id: pose_id.into(),
            frame_index,
            topology: analyze_pose_topology(sample),
            source_cell_count: sample.source_cell_count,
            root: PointF {
                x: sample.root.0 as f32,
                y: sample.root.1 as f32,
            },
            left_foot: anchor(AnchorId::LeftFoot)?,
            right_foot: anchor(AnchorId::RightFoot)?,
            face: PointF {
                x: (left_eye.x + right_eye.x) * 0.5,
                y: (left_eye.y + right_eye.y) * 0.5,
            },
            staff_hand: anchor(AnchorId::StaffHand)?,
        })
    }
}

#[derive(Clone, Debug, Serialize)]
pub struct FrameQualityFailure {
    pub transition_id: String,
    pub pose_id: String,
    pub frame_index: u64,
    pub rule: String,
    pub actual: f32,
    pub limit: f32,
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct FrameQualityReport {
    pub frame_count: usize,
    pub pair_count: usize,
    pub failures: Vec<FrameQualityFailure>,
}

impl FrameQualityReport {
    pub fn inspect_sequence(
        snapshots: &[FrameQualitySnapshot],
        thresholds: FrameQualityThresholds,
    ) -> Self {
        let mut report = Self {
            frame_count: snapshots.len(),
            pair_count: snapshots.len().saturating_sub(1),
            failures: Vec::new(),
        };
        for snapshot in snapshots {
            report.inspect_frame(snapshot, thresholds);
        }
        for pair in snapshots.windows(2) {
            report.inspect_pair(&pair[0], &pair[1], thresholds);
        }
        report
    }

    #[must_use]
    pub fn passed(&self) -> bool {
        self.failures.is_empty()
    }

    pub fn require_pass(&self) -> Result<(), String> {
        if self.passed() {
            Ok(())
        } else {
            Err(format!(
                "{} frame-quality failures: {:#?}",
                self.failures.len(),
                self.failures
            ))
        }
    }

    fn inspect_frame(
        &mut self,
        snapshot: &FrameQualitySnapshot,
        thresholds: FrameQualityThresholds,
    ) {
        self.fail_if_nonzero(
            snapshot,
            "horizontal_seam_rows",
            snapshot.topology.horizontal_seam_rows,
        );
        self.fail_if_nonzero(
            snapshot,
            "horizontal_seam_cells",
            snapshot.topology.horizontal_seam_cells,
        );
        self.fail_if_nonzero(
            snapshot,
            "vertical_crack_cells",
            snapshot.topology.vertical_crack_cells,
        );
        self.fail_if_nonzero(
            snapshot,
            "unexpected_fragment_components",
            snapshot.topology.unexpected_fragment_components,
        );
        if snapshot.topology.staff_components > 1 {
            self.push(
                snapshot,
                "staff_components",
                snapshot.topology.staff_components as f32,
                1.0,
            );
        }
        self.fail_if_nonzero(
            snapshot,
            "staff_scanline_gaps",
            snapshot.topology.staff_scanline_gaps,
        );
        if snapshot.topology.occupied_cells == 0 {
            self.push(snapshot, "occupied_cells", 0.0, 1.0);
        }
        let visible_source_ratio =
            snapshot.topology.occupied_cells as f32 / snapshot.source_cell_count.max(1) as f32;
        if visible_source_ratio < thresholds.minimum_visible_source_ratio {
            self.push(
                snapshot,
                "visible_source_ratio",
                visible_source_ratio,
                thresholds.minimum_visible_source_ratio,
            );
        }
        let source_retention = snapshot.topology.semantic_retained_cells as f32
            / snapshot.source_cell_count.max(1) as f32;
        if source_retention < thresholds.minimum_source_retention_ratio {
            self.push(
                snapshot,
                "source_retention_ratio",
                source_retention,
                thresholds.minimum_source_retention_ratio,
            );
        }
    }

    fn inspect_pair(
        &mut self,
        previous: &FrameQualitySnapshot,
        current: &FrameQualitySnapshot,
        thresholds: FrameQualityThresholds,
    ) {
        if previous.pose_id == current.pose_id {
            let minimum = previous
                .topology
                .occupied_cells
                .min(current.topology.occupied_cells) as f32;
            let maximum = previous
                .topology
                .occupied_cells
                .max(current.topology.occupied_cells) as f32;
            let occupancy_ratio = if maximum <= f32::EPSILON {
                0.0
            } else {
                minimum / maximum
            };
            if occupancy_ratio < thresholds.minimum_occupancy_ratio {
                self.push(
                    current,
                    "occupancy_ratio",
                    occupancy_ratio,
                    thresholds.minimum_occupancy_ratio,
                );
            }

            let component_step = previous
                .topology
                .unexpected_fragment_components
                .abs_diff(current.topology.unexpected_fragment_components);
            if component_step > thresholds.maximum_component_step {
                self.push(
                    current,
                    "component_step",
                    component_step as f32,
                    thresholds.maximum_component_step as f32,
                );
            }
        }
        self.maximum_step(current, "root_step", previous.root, current.root, 0.0);
        self.maximum_step(
            current,
            "face_anchor_step",
            previous.face,
            current.face,
            thresholds.maximum_face_anchor_step,
        );
        if previous.pose_id == current.pose_id {
            self.maximum_step(
                current,
                "staff_anchor_step",
                previous.staff_hand,
                current.staff_hand,
                thresholds.maximum_staff_anchor_step,
            );
        }
        self.maximum_step(
            current,
            "left_foot_step",
            previous.left_foot,
            current.left_foot,
            thresholds.maximum_free_foot_step,
        );
        self.maximum_step(
            current,
            "right_foot_step",
            previous.right_foot,
            current.right_foot,
            thresholds.maximum_free_foot_step,
        );
    }

    fn maximum_step(
        &mut self,
        snapshot: &FrameQualitySnapshot,
        rule: &str,
        previous: PointF,
        current: PointF,
        maximum: f32,
    ) {
        let actual = distance(previous, current);
        if actual > maximum + f32::EPSILON {
            self.push(snapshot, rule, actual, maximum);
        }
    }

    fn fail_if_nonzero(&mut self, snapshot: &FrameQualitySnapshot, rule: &str, actual: usize) {
        if actual != 0 {
            self.push(snapshot, rule, actual as f32, 0.0);
        }
    }

    fn push(&mut self, snapshot: &FrameQualitySnapshot, rule: &str, actual: f32, limit: f32) {
        self.failures.push(FrameQualityFailure {
            transition_id: snapshot.transition_id.clone(),
            pose_id: snapshot.pose_id.clone(),
            frame_index: snapshot.frame_index,
            rule: rule.to_string(),
            actual,
            limit,
        });
    }
}

fn distance(a: PointF, b: PointF) -> f32 {
    ((a.x - b.x).powi(2) + (a.y - b.y).powi(2)).sqrt()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn snapshot(frame_index: u64) -> FrameQualitySnapshot {
        FrameQualitySnapshot {
            transition_id: "idle-to-walk".to_string(),
            pose_id: "front-idle".to_string(),
            frame_index,
            topology: PoseTopologyMetrics {
                occupied_cells: 100,
                semantic_retained_cells: 100,
                connected_components: 1,
                unexpected_fragment_components: 0,
                horizontal_seam_rows: 0,
                horizontal_seam_cells: 0,
                vertical_crack_cells: 0,
                staff_components: 1,
                staff_scanline_gaps: 0,
            },
            source_cell_count: 100,
            root: PointF { x: 36.0, y: 95.0 },
            left_foot: PointF { x: 28.0, y: 94.0 },
            right_foot: PointF { x: 44.0, y: 94.0 },
            face: PointF { x: 36.0, y: 25.0 },
            staff_hand: PointF { x: 20.0, y: 50.0 },
        }
    }

    #[test]
    fn a_clean_sequence_passes() {
        let report = FrameQualityReport::inspect_sequence(
            &[snapshot(0), snapshot(1)],
            FrameQualityThresholds::default(),
        );
        assert!(report.passed(), "{:#?}", report.failures);
    }

    #[test]
    fn one_bad_frame_fails_with_its_exact_index() {
        let clean = snapshot(0);
        let mut broken = snapshot(1);
        broken.topology.horizontal_seam_rows = 1;
        broken.topology.horizontal_seam_cells = 8;
        broken.topology.staff_components = 2;
        let report = FrameQualityReport::inspect_sequence(
            &[clean, broken],
            FrameQualityThresholds::default(),
        );
        assert!(!report.passed());
        assert!(report
            .failures
            .iter()
            .all(|failure| failure.frame_index == 1));
        assert!(report
            .failures
            .iter()
            .any(|failure| failure.rule == "horizontal_seam_rows"));
        assert!(report
            .failures
            .iter()
            .any(|failure| failure.rule == "staff_components"));
    }

    #[test]
    fn coherent_pose_handoff_does_not_compare_view_space_staff_anchors() {
        let previous = snapshot(0);
        let mut current = snapshot(1);
        current.pose_id = "profile-right".to_string();
        current.staff_hand = PointF { x: 60.0, y: 52.0 };
        let report = FrameQualityReport::inspect_sequence(
            &[previous, current],
            FrameQualityThresholds::default(),
        );
        assert!(report.passed(), "{:#?}", report.failures);
    }

    #[test]
    fn same_pose_still_rejects_a_large_staff_anchor_step() {
        let previous = snapshot(0);
        let mut current = snapshot(1);
        current.staff_hand = PointF { x: 60.0, y: 52.0 };
        let report = FrameQualityReport::inspect_sequence(
            &[previous, current],
            FrameQualityThresholds::default(),
        );
        assert!(report
            .failures
            .iter()
            .any(|failure| failure.rule == "staff_anchor_step"));
    }
}
