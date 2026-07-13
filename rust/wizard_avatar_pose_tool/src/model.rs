use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct Point {
    pub x: i32,
    pub y: i32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CropBounds {
    pub left: u32,
    pub top: u32,
    pub right: u32,
    pub bottom: u32,
}

impl CropBounds {
    #[must_use]
    pub const fn width(self) -> u32 {
        self.right - self.left + 1
    }

    #[must_use]
    pub const fn height(self) -> u32 {
        self.bottom - self.top + 1
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CanonicalConfig {
    pub cols: u32,
    pub rows: u32,
    pub root: Point,
}

impl Default for CanonicalConfig {
    fn default() -> Self {
        Self {
            cols: 72,
            rows: 96,
            root: Point { x: 36, y: 95 },
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompilerConfig {
    pub margin: u32,
    pub white_distance_threshold: u16,
    pub coverage_threshold: u8,
    pub quantized_colors: usize,
    pub canonical: CanonicalConfig,
}

impl Default for CompilerConfig {
    fn default() -> Self {
        Self {
            margin: 18,
            white_distance_threshold: 30,
            coverage_threshold: 24,
            quantized_colors: 64,
            canonical: CanonicalConfig::default(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ArchivePose {
    pub candidate_id: String,
    pub semantic_id: String,
    pub status: String,
    pub order: u32,
    pub source_path: PathBuf,
    pub source_sha256: String,
    pub expected_width: u32,
    pub expected_height: u32,
    pub generation_rows: Option<u32>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RegionId {
    Hat,
    Head,
    Beard,
    Torso,
    Robe,
    InnerRobe,
    LeftArm,
    RightArm,
    LeftLeg,
    RightLeg,
    LeftBoot,
    RightBoot,
    Staff,
    AdornmentLeft,
    AdornmentRight,
    Face,
    Mouth,
    Effect,
}

impl RegionId {
    pub const ALL: [Self; 18] = [
        Self::Hat,
        Self::Head,
        Self::Beard,
        Self::Torso,
        Self::Robe,
        Self::InnerRobe,
        Self::LeftArm,
        Self::RightArm,
        Self::LeftLeg,
        Self::RightLeg,
        Self::LeftBoot,
        Self::RightBoot,
        Self::Staff,
        Self::AdornmentLeft,
        Self::AdornmentRight,
        Self::Face,
        Self::Mouth,
        Self::Effect,
    ];

    pub const Z_ORDER: [Self; 18] = [
        Self::AdornmentLeft,
        Self::AdornmentRight,
        Self::Staff,
        Self::Robe,
        Self::InnerRobe,
        Self::LeftLeg,
        Self::RightLeg,
        Self::LeftBoot,
        Self::RightBoot,
        Self::Torso,
        Self::LeftArm,
        Self::RightArm,
        Self::Beard,
        Self::Head,
        Self::Hat,
        Self::Face,
        Self::Mouth,
        Self::Effect,
    ];
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AnchorId {
    Root,
    ContactRoot,
    Pelvis,
    Chest,
    Head,
    LeftShoulder,
    LeftElbow,
    LeftWrist,
    RightShoulder,
    RightElbow,
    RightWrist,
    LeftHip,
    LeftKnee,
    LeftAnkle,
    LeftFoot,
    RightHip,
    RightKnee,
    RightAnkle,
    RightFoot,
    LeftEye,
    RightEye,
    Mouth,
    StaffHand,
    StaffTop,
    EffectOrigin,
}

impl AnchorId {
    pub const REQUIRED: [Self; 25] = [
        Self::Root,
        Self::ContactRoot,
        Self::Pelvis,
        Self::Chest,
        Self::Head,
        Self::LeftShoulder,
        Self::LeftElbow,
        Self::LeftWrist,
        Self::RightShoulder,
        Self::RightElbow,
        Self::RightWrist,
        Self::LeftHip,
        Self::LeftKnee,
        Self::LeftAnkle,
        Self::LeftFoot,
        Self::RightHip,
        Self::RightKnee,
        Self::RightAnkle,
        Self::RightFoot,
        Self::LeftEye,
        Self::RightEye,
        Self::Mouth,
        Self::StaffHand,
        Self::StaffTop,
        Self::EffectOrigin,
    ];
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Direction {
    North,
    NorthEast,
    East,
    SouthEast,
    South,
    SouthWest,
    West,
    NorthWest,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MotionFamily {
    Run,
    Walk,
    Flight,
    Jump,
    Landing,
    GroundAction,
    Kneel,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContactMode {
    Airborne,
    LeftFoot,
    RightFoot,
    BothFeet,
    BothFeetAndStaff,
    KneelAndStaff,
    HandFootAndStaff,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Phase {
    pub numerator: u16,
    pub denominator: u16,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContactKind {
    Ground,
    Brace,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ContactPoint {
    pub anchor: AnchorId,
    pub kind: ContactKind,
    pub point: Point,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ContactSet {
    pub id: String,
    pub points: Vec<ContactPoint>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct MotionMetadata {
    pub family: MotionFamily,
    pub contact_mode: ContactMode,
    pub phase: Option<Phase>,
    pub authored_transition_neighbors: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct FacingMetadata {
    pub direction: Direction,
    pub view_family: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct FeaturePresence {
    pub staff: bool,
    pub effect: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct NamedAnchor {
    pub id: AnchorId,
    pub point: Point,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AttachmentEdge {
    pub parent_region: RegionId,
    pub child_region: RegionId,
    pub parent_anchor: AnchorId,
    pub child_anchor: AnchorId,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CellPayload {
    pub x: i32,
    pub y: i32,
    pub rgb: [u8; 3],
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct SemanticCellPayload {
    pub x: i32,
    pub y: i32,
    pub rgb: [u8; 3],
    pub region: RegionId,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompiledPose {
    pub candidate_id: String,
    pub semantic_id: String,
    pub source_sha256: String,
    pub source_size: [u32; 2],
    pub source_crop: CropBounds,
    pub generation_rows: u32,
    pub generated_size: [u32; 2],
    pub canonical_size: [u32; 2],
    pub root_anchor: Point,
    pub canonical_shift: Point,
    pub quantized_colors: usize,
    pub palette_color_count: usize,
    pub palette_sha256: String,
    pub cell_count: usize,
    pub cell_sha256: String,
    pub semantic_sha256: String,
    pub motion: MotionMetadata,
    pub facing: FacingMetadata,
    pub presence: FeaturePresence,
    pub anchors: Vec<NamedAnchor>,
    pub contact_sets: Vec<ContactSet>,
    pub attachment_edges: Vec<AttachmentEdge>,
    pub z_order: Vec<RegionId>,
    pub cells: Vec<SemanticCellPayload>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CatalogRecordKind {
    Geometry,
    Alias,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CatalogRecord {
    pub order: u32,
    pub candidate_id: String,
    pub semantic_id: String,
    pub source_sha256: String,
    pub kind: CatalogRecordKind,
    pub geometry_id: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct PoseAlias {
    pub candidate_id: String,
    pub semantic_id: String,
    pub target_semantic_id: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompiledArchive {
    pub schema_version: u32,
    pub compiler_id: String,
    pub source_manifest_sha256: String,
    pub config: CompilerConfig,
    pub catalog_count: usize,
    pub unique_geometry_count: usize,
    pub alias_count: usize,
    pub catalog: Vec<CatalogRecord>,
    pub poses: Vec<CompiledPose>,
    pub aliases: Vec<PoseAlias>,
    pub palette_color_count: usize,
    pub palette_sha256: String,
    pub archive_sha256: String,
}
