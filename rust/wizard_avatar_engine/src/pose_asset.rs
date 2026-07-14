use crate::cell::Cell;
use crate::palette::Rgb;
use crate::pose::{
    AnchorId, PointF, PoseAttachmentEdge, PoseCell, PoseContactKind, PoseContactMode,
    PoseContactPoint, PoseContactSet, PoseDefinition, PoseMotionFamily, PoseMotionMetadata,
    RegionId,
};
use crate::pose_program::BASELINE_POSE_IDS;
use crate::state::Direction;
use flate2::read::GzDecoder;
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::io::Read;
use std::sync::OnceLock;

pub const IMPORTED_POSE_SCHEMA_VERSION: u32 = 4;
pub const IMPORTED_POSE_COMPILER_ID: &str = "wizard-avatar-pose-tool-rust-v4";

const EMBEDDED_POSE_ARCHIVE_GZIP: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/assets/wizard_pose_library.v4.json.gz"
));

static EMBEDDED_POSE_ARCHIVE_SHA256: OnceLock<String> = OnceLock::new();

#[derive(Clone, Copy, Debug, Deserialize)]
pub struct AssetPoint {
    pub x: i32,
    pub y: i32,
}

#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
enum AssetDirection {
    North,
    NorthEast,
    East,
    SouthEast,
    South,
    SouthWest,
    West,
    NorthWest,
}

impl From<AssetDirection> for Direction {
    fn from(value: AssetDirection) -> Self {
        match value {
            AssetDirection::North => Self::North,
            AssetDirection::NorthEast => Self::NorthEast,
            AssetDirection::East => Self::East,
            AssetDirection::SouthEast => Self::SouthEast,
            AssetDirection::South => Self::South,
            AssetDirection::SouthWest => Self::SouthWest,
            AssetDirection::West => Self::West,
            AssetDirection::NorthWest => Self::NorthWest,
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
enum AssetMotionFamily {
    Run,
    Walk,
    Flight,
    Jump,
    Landing,
    GroundAction,
    Kneel,
}

impl From<AssetMotionFamily> for PoseMotionFamily {
    fn from(value: AssetMotionFamily) -> Self {
        match value {
            AssetMotionFamily::Run => Self::Run,
            AssetMotionFamily::Walk => Self::Walk,
            AssetMotionFamily::Flight => Self::Flight,
            AssetMotionFamily::Jump => Self::Jump,
            AssetMotionFamily::Landing => Self::Landing,
            AssetMotionFamily::GroundAction => Self::GroundAction,
            AssetMotionFamily::Kneel => Self::Kneel,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
enum AssetContactMode {
    Airborne,
    LeftFoot,
    RightFoot,
    BothFeet,
    BothFeetAndStaff,
    KneelAndStaff,
    HandFootAndStaff,
}

impl From<AssetContactMode> for PoseContactMode {
    fn from(value: AssetContactMode) -> Self {
        match value {
            AssetContactMode::Airborne => Self::Airborne,
            AssetContactMode::LeftFoot => Self::LeftFoot,
            AssetContactMode::RightFoot => Self::RightFoot,
            AssetContactMode::BothFeet => Self::BothFeet,
            AssetContactMode::BothFeetAndStaff => Self::BothFeetAndStaff,
            AssetContactMode::KneelAndStaff => Self::KneelAndStaff,
            AssetContactMode::HandFootAndStaff => Self::HandFootAndStaff,
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
enum AssetContactKind {
    Ground,
    Brace,
}

impl From<AssetContactKind> for PoseContactKind {
    fn from(value: AssetContactKind) -> Self {
        match value {
            AssetContactKind::Ground => Self::Ground,
            AssetContactKind::Brace => Self::Brace,
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize)]
struct AssetPhase {
    numerator: u16,
    denominator: u16,
}

#[derive(Clone, Debug, Deserialize)]
struct AssetMotion {
    family: AssetMotionFamily,
    contact_mode: AssetContactMode,
    phase: Option<AssetPhase>,
    authored_transition_neighbors: Vec<String>,
}

#[derive(Clone, Copy, Debug, Deserialize)]
struct AssetFacing {
    direction: AssetDirection,
}

#[derive(Clone, Copy, Debug, Deserialize)]
struct AssetPresence {
    staff: bool,
    effect: bool,
}

#[derive(Clone, Copy, Debug, Deserialize)]
struct AssetAnchor {
    id: AnchorId,
    point: AssetPoint,
}

#[derive(Clone, Copy, Debug, Deserialize)]
struct AssetContactPoint {
    anchor: AnchorId,
    kind: AssetContactKind,
    point: AssetPoint,
}

#[derive(Clone, Debug, Deserialize)]
struct AssetContactSet {
    id: String,
    points: Vec<AssetContactPoint>,
}

#[derive(Clone, Copy, Debug, Deserialize)]
struct AssetAttachmentEdge {
    parent_region: RegionId,
    child_region: RegionId,
    parent_anchor: AnchorId,
    child_anchor: AnchorId,
}

#[derive(Clone, Copy, Debug, Deserialize)]
struct AssetCell {
    x: i32,
    y: i32,
    rgb: [u8; 3],
    region: RegionId,
}

#[derive(Clone, Debug, Deserialize)]
struct AssetPose {
    candidate_id: String,
    semantic_id: String,
    canonical_size: [u32; 2],
    root_anchor: AssetPoint,
    cell_count: usize,
    cell_sha256: String,
    motion: AssetMotion,
    facing: AssetFacing,
    presence: AssetPresence,
    anchors: Vec<AssetAnchor>,
    contact_sets: Vec<AssetContactSet>,
    attachment_edges: Vec<AssetAttachmentEdge>,
    z_order: Vec<RegionId>,
    cells: Vec<AssetCell>,
}

#[derive(Clone, Debug, Deserialize)]
struct AssetAlias {
    candidate_id: String,
    semantic_id: String,
    target_semantic_id: String,
}

#[derive(Clone, Debug, Deserialize)]
struct AssetArchive {
    schema_version: u32,
    compiler_id: String,
    catalog_count: usize,
    unique_geometry_count: usize,
    alias_count: usize,
    poses: Vec<AssetPose>,
    aliases: Vec<AssetAlias>,
}

pub struct ImportedPoseLibrary {
    pub definitions: Vec<PoseDefinition>,
    pub aliases: BTreeMap<String, String>,
}

pub fn load_embedded_pose_library() -> Result<ImportedPoseLibrary, String> {
    let mut decoder = GzDecoder::new(EMBEDDED_POSE_ARCHIVE_GZIP);
    let mut json = String::new();
    decoder
        .read_to_string(&mut json)
        .map_err(|error| format!("failed to decompress embedded pose archive: {error}"))?;
    parse_imported_pose_library(&json)
}

#[must_use]
pub fn embedded_pose_archive_sha256() -> &'static str {
    EMBEDDED_POSE_ARCHIVE_SHA256
        .get_or_init(|| format!("{:x}", Sha256::digest(EMBEDDED_POSE_ARCHIVE_GZIP)))
}

pub fn parse_imported_pose_library(json: &str) -> Result<ImportedPoseLibrary, String> {
    let archive: AssetArchive =
        serde_json::from_str(json).map_err(|error| format!("invalid pose archive: {error}"))?;
    if archive.schema_version != IMPORTED_POSE_SCHEMA_VERSION
        || archive.compiler_id != IMPORTED_POSE_COMPILER_ID
    {
        return Err(format!(
            "unsupported imported pose artifact {} from {}",
            archive.schema_version, archive.compiler_id
        ));
    }
    if archive.catalog_count != 80
        || archive.unique_geometry_count != 79
        || archive.alias_count != 1
        || archive.poses.len() != 79
        || archive.aliases.len() != 1
    {
        return Err("pose archive must contain 80 records, 79 geometries, and 1 alias".to_string());
    }

    let geometry_ids = archive
        .poses
        .iter()
        .map(|pose| pose.semantic_id.clone())
        .collect::<BTreeSet<_>>();
    if geometry_ids.len() != 79 {
        return Err("imported pose IDs are not unique".to_string());
    }
    let mut known_ids = geometry_ids;
    known_ids.extend(BASELINE_POSE_IDS.into_iter().map(str::to_string));

    let mut definitions = Vec::with_capacity(79);
    for pose in archive.poses {
        validate_pose(&pose, &known_ids)?;
        definitions.push(convert_pose(pose)?);
    }
    let alias = &archive.aliases[0];
    if alias.candidate_id != "WJFA-10"
        || alias.semantic_id != "fly_front_hover_ready"
        || alias.target_semantic_id != "fly_front_hover_neutral"
        || !known_ids.contains(alias.target_semantic_id.as_str())
    {
        return Err("invalid WJFA-10 pose alias".to_string());
    }
    Ok(ImportedPoseLibrary {
        definitions,
        aliases: BTreeMap::from([(alias.semantic_id.clone(), alias.target_semantic_id.clone())]),
    })
}

fn validate_pose(pose: &AssetPose, known_ids: &BTreeSet<String>) -> Result<(), String> {
    let fail = |message: &str| format!("{}: {message}", pose.semantic_id);
    if pose.canonical_size != [72, 96] || pose.root_anchor.x != 36 || pose.root_anchor.y != 95 {
        return Err(fail("canonical geometry is not 72x96 at root 36,95"));
    }
    if pose.cells.len() != pose.cell_count || pose.cells.is_empty() {
        return Err(fail("cell count is invalid"));
    }
    let coordinates = pose
        .cells
        .iter()
        .map(|cell| (cell.x, cell.y))
        .collect::<BTreeSet<_>>();
    if coordinates.len() != pose.cells.len()
        || pose
            .cells
            .iter()
            .any(|cell| !(0..72).contains(&cell.x) || !(0..96).contains(&cell.y))
    {
        return Err(fail("cells are duplicated or out of bounds"));
    }
    if cell_hash(&pose.cells) != pose.cell_sha256 {
        return Err(fail("cell SHA-256 does not match geometry"));
    }
    let anchor_ids = pose
        .anchors
        .iter()
        .map(|anchor| anchor.id)
        .collect::<BTreeSet<_>>();
    if anchor_ids.len() != AnchorId::REQUIRED.len()
        || !AnchorId::REQUIRED
            .iter()
            .all(|anchor| anchor_ids.contains(anchor))
        || pose
            .anchors
            .iter()
            .any(|anchor| !(0..72).contains(&anchor.point.x) || !(0..96).contains(&anchor.point.y))
    {
        return Err(fail(
            "required anchors are missing, duplicated, or out of bounds",
        ));
    }
    if pose.z_order != RegionId::Z_ORDER {
        return Err(fail("z-order does not match the engine region contract"));
    }
    if pose
        .motion
        .authored_transition_neighbors
        .iter()
        .any(|neighbor| !known_ids.contains(neighbor.as_str()))
    {
        return Err(fail("an authored transition neighbor does not resolve"));
    }
    let airborne = pose.motion.contact_mode == AssetContactMode::Airborne;
    if airborne && !pose.contact_sets.is_empty()
        || !airborne && (pose.contact_sets.len() != 1 || pose.contact_sets[0].points.is_empty())
    {
        return Err(fail("contact sets disagree with the authored contact mode"));
    }
    let occupied_regions = pose
        .cells
        .iter()
        .map(|cell| cell.region)
        .collect::<BTreeSet<_>>();
    if pose.presence.staff != occupied_regions.contains(&RegionId::Staff)
        || pose.presence.effect != occupied_regions.contains(&RegionId::Effect)
    {
        return Err(fail("feature presence disagrees with semantic regions"));
    }
    if pose.attachment_edges.iter().any(|edge| {
        !occupied_regions.contains(&edge.parent_region)
            || !occupied_regions.contains(&edge.child_region)
            || !anchor_ids.contains(&edge.parent_anchor)
            || !anchor_ids.contains(&edge.child_anchor)
    }) {
        return Err(fail("an attachment edge references absent semantics"));
    }
    Ok(())
}

fn convert_pose(pose: AssetPose) -> Result<PoseDefinition, String> {
    let phase = pose
        .motion
        .phase
        .map(|phase| {
            if phase.denominator == 0 || phase.numerator >= phase.denominator {
                Err(format!("{} has invalid phase", pose.semantic_id))
            } else {
                Ok(f32::from(phase.numerator) / f32::from(phase.denominator))
            }
        })
        .transpose()?;
    let anchors = pose
        .anchors
        .into_iter()
        .map(|anchor| {
            (
                anchor.id,
                PointF {
                    x: anchor.point.x as f32,
                    y: anchor.point.y as f32,
                },
            )
        })
        .collect();
    let cells = pose
        .cells
        .into_iter()
        .enumerate()
        .map(|(stable_id, cell)| PoseCell {
            x: cell.x as i16,
            y: cell.y as i16,
            cell: Cell::new(b'#', Rgb(cell.rgb[0], cell.rgb[1], cell.rgb[2])),
            region: cell.region,
            stable_id: stable_id as u32,
        })
        .collect();
    let contact_sets = pose
        .contact_sets
        .into_iter()
        .map(|set| PoseContactSet {
            id: set.id,
            points: set
                .points
                .into_iter()
                .map(|point| PoseContactPoint {
                    anchor: point.anchor,
                    kind: point.kind.into(),
                    point: (point.point.x, point.point.y),
                })
                .collect(),
        })
        .collect();
    let attachment_edges = pose
        .attachment_edges
        .into_iter()
        .map(|edge| PoseAttachmentEdge {
            parent_region: edge.parent_region,
            child_region: edge.child_region,
            parent_anchor: edge.parent_anchor,
            child_anchor: edge.child_anchor,
        })
        .collect();
    Ok(PoseDefinition {
        id: pose.semantic_id,
        direction: pose.facing.direction.into(),
        root: (pose.root_anchor.x, pose.root_anchor.y),
        anchors,
        cells,
        z_order: pose.z_order,
        cols: pose.canonical_size[0] as usize,
        rows: pose.canonical_size[1] as usize,
        motion: PoseMotionMetadata {
            candidate_id: Some(pose.candidate_id),
            family: pose.motion.family.into(),
            contact_mode: pose.motion.contact_mode.into(),
            phase,
            authored_transition_neighbors: pose.motion.authored_transition_neighbors,
            contact_sets,
            attachment_edges,
            staff_present: pose.presence.staff,
            effect_present: pose.presence.effect,
        },
    })
}

fn cell_hash(cells: &[AssetCell]) -> String {
    let bytes = cells
        .iter()
        .flat_map(|cell| {
            let mut bytes = Vec::with_capacity(11);
            bytes.extend_from_slice(&cell.x.to_le_bytes());
            bytes.extend_from_slice(&cell.y.to_le_bytes());
            bytes.extend_from_slice(&cell.rgb);
            bytes
        })
        .collect::<Vec<_>>();
    format!("{:x}", Sha256::digest(bytes))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_a_non_v4_payload() {
        let error = parse_imported_pose_library(r#"{"schema_version":2}"#)
            .err()
            .expect("invalid payload");
        assert!(error.contains("invalid pose archive") || error.contains("unsupported"));
    }
}
