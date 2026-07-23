use crate::pose::{
    AnchorId, PoseLibrary, CANONICAL_POSE_COLS, CANONICAL_POSE_ROOT, CANONICAL_POSE_ROWS,
};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;

pub const LEGACY_CELL_POSE_COUNT: usize = 89;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PoseGraphAuditStatus {
    Complete,
    Incomplete,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct PoseGraphAuditRecord {
    pub pose_id: String,
    pub candidate_id: Option<String>,
    pub canonical_size: [usize; 2],
    pub root: [i32; 2],
    pub cell_count: usize,
    pub unique_coordinate_count: usize,
    pub required_anchor_count: usize,
    pub contact_point_count: usize,
    pub cell_graph_sha256: String,
    pub passed: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct PoseGraphAuditReport {
    pub schema_version: u32,
    pub expected_silhouette_count: usize,
    pub audited_geometry_count: usize,
    pub alias_count: usize,
    pub missing_geometry_count: usize,
    pub failed_geometry_count: usize,
    pub status: PoseGraphAuditStatus,
    pub records: Vec<PoseGraphAuditRecord>,
}

#[must_use]
pub fn audit_runtime_pose_graphs(
    library: &PoseLibrary,
    expected_silhouette_count: usize,
) -> PoseGraphAuditReport {
    let mut records = library
        .pose_ids()
        .filter_map(|pose_id| library.for_id(pose_id))
        .map(|pose| {
            let coordinates = pose
                .cells
                .iter()
                .map(|cell| (cell.x, cell.y))
                .collect::<BTreeSet<_>>();
            let required_anchor_count = AnchorId::REQUIRED
                .iter()
                .filter(|anchor| pose.anchors.contains_key(anchor))
                .count();
            let contact_point_count = pose
                .motion
                .contact_sets
                .iter()
                .map(|set| set.points.len())
                .sum();
            let passed = pose.cols == CANONICAL_POSE_COLS
                && pose.rows == CANONICAL_POSE_ROWS
                && pose.root == CANONICAL_POSE_ROOT
                && !pose.cells.is_empty()
                && coordinates.len() == pose.cells.len()
                && required_anchor_count == AnchorId::REQUIRED.len()
                && pose.cells.iter().all(|cell| {
                    (0..CANONICAL_POSE_COLS as i16).contains(&cell.x)
                        && (0..CANONICAL_POSE_ROWS as i16).contains(&cell.y)
                });
            PoseGraphAuditRecord {
                pose_id: pose.id.clone(),
                candidate_id: pose.motion.candidate_id.clone(),
                canonical_size: [pose.cols, pose.rows],
                root: [pose.root.0, pose.root.1],
                cell_count: pose.cells.len(),
                unique_coordinate_count: coordinates.len(),
                required_anchor_count,
                contact_point_count,
                cell_graph_sha256: pose_cell_graph_sha256(pose),
                passed,
            }
        })
        .collect::<Vec<_>>();
    records.sort_by(|left, right| left.pose_id.cmp(&right.pose_id));
    let audited_geometry_count = records.len();
    let failed_geometry_count = records.iter().filter(|record| !record.passed).count();
    let missing_geometry_count = expected_silhouette_count.saturating_sub(audited_geometry_count);
    let status =
        if audited_geometry_count == expected_silhouette_count && failed_geometry_count == 0 {
            PoseGraphAuditStatus::Complete
        } else {
            PoseGraphAuditStatus::Incomplete
        };
    PoseGraphAuditReport {
        schema_version: 1,
        expected_silhouette_count,
        audited_geometry_count,
        alias_count: library.alias_count(),
        missing_geometry_count,
        failed_geometry_count,
        status,
        records,
    }
}

fn pose_cell_graph_sha256(pose: &crate::pose::PoseDefinition) -> String {
    let mut cells = pose.cells.iter().collect::<Vec<_>>();
    cells.sort_by_key(|cell| (cell.y, cell.x, cell.stable_id));
    let mut hasher = Sha256::new();
    for cell in cells {
        hasher.update(cell.x.to_le_bytes());
        hasher.update(cell.y.to_le_bytes());
        hasher.update(cell.cell.to_bytes());
        hasher.update((cell.region as u8).to_le_bytes());
        hasher.update(cell.stable_id.to_le_bytes());
    }
    format!("{:x}", hasher.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn current_runtime_graphs_pass_their_actual_census() {
        let library = PoseLibrary::reference().expect("pose library");
        let report = audit_runtime_pose_graphs(library, library.pose_ids().count());
        assert_eq!(report.status, PoseGraphAuditStatus::Complete);
        assert_eq!(report.audited_geometry_count, 89);
        assert_eq!(report.failed_geometry_count, 0);
        assert!(report
            .records
            .iter()
            .all(|record| record.cell_graph_sha256.len() == 64));
    }

    #[test]
    fn replacement_pixelgraph_census_is_complete_and_exact() {
        let catalog = crate::pose_graph_runtime::runtime_pose_graph_catalog()
            .expect("runtime pixelgraph catalog");
        assert_eq!(
            catalog.manifest().verified_pose_count,
            crate::pose_graph_runtime::RUNTIME_POSE_GRAPH_COUNT
        );
        assert_eq!(catalog.manifest().verified_pose_count, 260);
        assert_eq!(catalog.manifest().base_pose_count, 250);
        assert_eq!(catalog.manifest().forward_flight_count, 10);
        assert_eq!(catalog.manifest().unique_semantic_pose_count, 260);
        catalog
            .verify_runtime_files()
            .expect("all promoted graph hashes");
    }
}
