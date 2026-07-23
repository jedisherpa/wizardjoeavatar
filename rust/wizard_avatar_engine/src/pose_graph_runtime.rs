use crate::state::{Direction, Locomotion, WizardState};
use flate2::read::GzDecoder;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, OnceLock};

pub const RUNTIME_POSE_GRAPH_SCHEMA_VERSION: u32 = 2;
pub const RUNTIME_POSE_GRAPH_COMPILER_ID: &str = "wizard-avatar-production-alpha-v1";
pub const RUNTIME_POSE_GRAPH_COUNT: usize = 260;
pub const RUNTIME_UNIQUE_SEMANTIC_COUNT: usize = 260;
pub const RUNTIME_SOURCE_RECORD_COUNT: usize = 260;
pub const RUNTIME_BASE_POSE_COUNT: usize = 250;
pub const RUNTIME_FORWARD_FLIGHT_COUNT: usize = 10;
const RUNTIME_RASTER_CACHE_LIMIT: usize = 16;

const EMBEDDED_RUNTIME_MANIFEST: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/assets/pose_graphs/v6/runtime-manifest.json"
));

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimePoseGraphEntry {
    pub sequence: usize,
    pub source_record_id: String,
    pub candidate_id: String,
    pub pose_id: String,
    pub semantic_id: String,
    pub display_name: String,
    pub source_archive: String,
    pub source_entry: String,
    pub source_sha256: String,
    pub graph_path: String,
    pub graph_sha256: String,
    pub graph_id: String,
    pub frame: [u32; 2],
    pub source_size: [u32; 2],
    pub offset: [u32; 2],
    pub foreground_pixel_count: u64,
    pub motion_family: String,
    pub contact_mode: String,
    pub phase: Option<RuntimePhase>,
    pub direction: String,
    pub authored_transition_neighbors: Vec<String>,
    pub control_groups: Vec<String>,
    pub primary_for_semantic_id: bool,
    pub duplicate_source_of: Option<String>,
    pub silhouette_iou_millionths: u32,
    pub foreground_color_fidelity_millionths: u32,
    pub foreground_color_match_ratio_millionths: u32,
    pub exact_rgba_equal: bool,
    pub rgba_mismatch_pixel_count: u64,
    pub rgba_mismatch_channel_count: u64,
    pub source_pack: String,
    pub category: String,
    pub anchor_kind: String,
    pub anchor_x: u32,
    pub anchor_y: u32,
    pub evidence_path: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimePhase {
    pub numerator: u16,
    pub denominator: u16,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimePoseGraphManifest {
    pub schema_version: u32,
    pub compiler_id: String,
    pub frame: [u32; 2],
    pub source_count: usize,
    pub base_pose_count: usize,
    pub forward_flight_count: usize,
    pub verified_pose_count: usize,
    pub primary_pose_count: usize,
    pub unique_semantic_pose_count: usize,
    pub archives: Vec<RuntimeArchiveProvenance>,
    pub entries: Vec<RuntimePoseGraphEntry>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeArchiveProvenance {
    pub source_pack: String,
    pub archive_filename: String,
    pub archive_sha256: String,
    pub manifest_member: String,
    pub manifest_status: String,
}

#[derive(Clone, Debug)]
pub struct RuntimePoseGraphCatalog {
    manifest: RuntimePoseGraphManifest,
    primary_by_semantic_id: BTreeMap<String, usize>,
    by_source_record_id: BTreeMap<String, usize>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RuntimePoseGraphRaster {
    pub entry: RuntimePoseGraphEntry,
    pub width: u16,
    pub height: u16,
    pub rgba: Vec<u8>,
    pub rgb_white_background: Vec<u8>,
    pub coverage_mask: Vec<u8>,
    pub rgb_sha256: String,
    pub coverage_mask_sha256: String,
    pub foreground_bounds: [u16; 4],
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StoredPoseGraph {
    schema_version: u32,
    graph_id: String,
    source_record_id: String,
    source_sha256: String,
    frame: StoredGraphFrame,
    source_width: u32,
    source_height: u32,
    offset_x: u32,
    offset_y: u32,
    foreground_pixel_count: u64,
    palette: Vec<[u8; 4]>,
    runs: Vec<StoredGraphRun>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StoredGraphFrame {
    width: u32,
    height: u32,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StoredGraphRun {
    y: u32,
    x: u32,
    palette_indices: Vec<usize>,
}

static RUNTIME_CATALOG: OnceLock<Result<RuntimePoseGraphCatalog, String>> = OnceLock::new();
static RUNTIME_RASTER_CACHE: OnceLock<Mutex<BTreeMap<String, Arc<RuntimePoseGraphRaster>>>> =
    OnceLock::new();

pub fn runtime_pose_graph_catalog() -> Result<&'static RuntimePoseGraphCatalog, String> {
    RUNTIME_CATALOG
        .get_or_init(|| RuntimePoseGraphCatalog::from_json(EMBEDDED_RUNTIME_MANIFEST))
        .as_ref()
        .map_err(Clone::clone)
}

#[must_use]
pub fn runtime_pose_graph_manifest_sha256() -> String {
    sha256_hex(EMBEDDED_RUNTIME_MANIFEST.as_bytes())
}

impl RuntimePoseGraphCatalog {
    pub fn from_json(json: &str) -> Result<Self, String> {
        let manifest: RuntimePoseGraphManifest = serde_json::from_str(json)
            .map_err(|error| format!("invalid runtime pose graph manifest: {error}"))?;
        validate_manifest(&manifest)?;
        let mut primary_by_semantic_id = BTreeMap::new();
        let mut by_source_record_id = BTreeMap::new();
        for (index, entry) in manifest.entries.iter().enumerate() {
            if by_source_record_id
                .insert(entry.source_record_id.clone(), index)
                .is_some()
            {
                return Err(format!(
                    "duplicate source record {}",
                    entry.source_record_id
                ));
            }
            if entry.primary_for_semantic_id
                && primary_by_semantic_id
                    .insert(entry.semantic_id.clone(), index)
                    .is_some()
            {
                return Err(format!(
                    "duplicate primary semantic pose {}",
                    entry.semantic_id
                ));
            }
        }
        if primary_by_semantic_id.len() != RUNTIME_UNIQUE_SEMANTIC_COUNT {
            return Err(format!(
                "runtime graph catalog has {} primary semantics instead of {}",
                primary_by_semantic_id.len(),
                RUNTIME_UNIQUE_SEMANTIC_COUNT
            ));
        }
        Ok(Self {
            manifest,
            primary_by_semantic_id,
            by_source_record_id,
        })
    }

    #[must_use]
    pub const fn manifest(&self) -> &RuntimePoseGraphManifest {
        &self.manifest
    }

    #[must_use]
    pub fn primary_for_semantic_id(&self, semantic_id: &str) -> Option<&RuntimePoseGraphEntry> {
        self.primary_by_semantic_id
            .get(semantic_id)
            .map(|index| &self.manifest.entries[*index])
    }

    #[must_use]
    pub fn for_source_record_id(&self, source_record_id: &str) -> Option<&RuntimePoseGraphEntry> {
        self.by_source_record_id
            .get(source_record_id)
            .map(|index| &self.manifest.entries[*index])
    }

    #[must_use]
    pub fn for_runtime_pose_id(&self, pose_id: &str) -> Option<&RuntimePoseGraphEntry> {
        self.for_source_record_id(pose_id)
            .or_else(|| self.primary_for_semantic_id(pose_id))
    }

    pub fn graph_path(&self, entry: &RuntimePoseGraphEntry) -> Result<PathBuf, String> {
        runtime_graph_directory().map(|directory| directory.join(&entry.graph_path))
    }

    pub fn verify_runtime_files(&self) -> Result<(), String> {
        for entry in &self.manifest.entries {
            let path = self.graph_path(entry)?;
            let bytes = std::fs::read(&path)
                .map_err(|error| format!("read runtime graph {}: {error}", path.display()))?;
            verify_graph_bytes(entry, &bytes)?;
        }
        Ok(())
    }
}

pub fn verify_graph_bytes(entry: &RuntimePoseGraphEntry, bytes: &[u8]) -> Result<(), String> {
    let actual = sha256_hex(bytes);
    if actual != entry.graph_sha256 {
        return Err(format!(
            "{} runtime graph hash mismatch: {} != {}",
            entry.source_record_id, actual, entry.graph_sha256
        ));
    }
    Ok(())
}

pub fn project_runtime_pose_graph(pose_id: &str) -> Result<Arc<RuntimePoseGraphRaster>, String> {
    let catalog = runtime_pose_graph_catalog()?;
    let source_record_id = catalog
        .for_runtime_pose_id(pose_id)
        .ok_or_else(|| format!("runtime pose graph {pose_id} is not in the promoted catalog"))?
        .source_record_id
        .clone();
    let cache = RUNTIME_RASTER_CACHE.get_or_init(|| Mutex::new(BTreeMap::new()));
    if let Some(raster) = cache
        .lock()
        .map_err(|_| "runtime pose graph raster cache is poisoned".to_string())?
        .get(&source_record_id)
        .cloned()
    {
        return Ok(raster);
    }
    let projected = Arc::new(project_runtime_pose_graph_uncached(pose_id)?);
    let mut cache = cache
        .lock()
        .map_err(|_| "runtime pose graph raster cache is poisoned".to_string())?;
    if cache.len() >= RUNTIME_RASTER_CACHE_LIMIT {
        if let Some(oldest_key) = cache.keys().next().cloned() {
            cache.remove(&oldest_key);
        }
    }
    Ok(cache
        .entry(source_record_id)
        .or_insert_with(|| projected.clone())
        .clone())
}

fn project_runtime_pose_graph_uncached(pose_id: &str) -> Result<RuntimePoseGraphRaster, String> {
    let catalog = runtime_pose_graph_catalog()?;
    let entry = catalog
        .for_runtime_pose_id(pose_id)
        .ok_or_else(|| format!("runtime pose graph {pose_id} is not in the promoted catalog"))?
        .clone();
    let path = catalog.graph_path(&entry)?;
    let compressed = std::fs::read(&path)
        .map_err(|error| format!("read runtime graph {}: {error}", path.display()))?;
    verify_graph_bytes(&entry, &compressed)?;

    let mut decoder = GzDecoder::new(compressed.as_slice());
    let mut json = Vec::new();
    decoder
        .read_to_end(&mut json)
        .map_err(|error| format!("decompress runtime graph {}: {error}", path.display()))?;
    let graph: StoredPoseGraph = serde_json::from_slice(&json)
        .map_err(|error| format!("parse runtime graph {}: {error}", path.display()))?;
    validate_stored_graph(&entry, &graph)?;

    let width = u16::try_from(graph.frame.width)
        .map_err(|_| format!("{} width exceeds u16", entry.source_record_id))?;
    let height = u16::try_from(graph.frame.height)
        .map_err(|_| format!("{} height exceeds u16", entry.source_record_id))?;
    let pixel_count = usize::from(width) * usize::from(height);
    let mut rgba = vec![0_u8; pixel_count * 4];
    let mut rgb_white_background = vec![255_u8; pixel_count * 3];
    let mut coverage_mask = vec![0_u8; pixel_count];
    let mut painted = 0_u64;
    let mut min_x = u16::MAX;
    let mut min_y = u16::MAX;
    let mut max_x = 0_u16;
    let mut max_y = 0_u16;

    for run in &graph.runs {
        let run_length = u32::try_from(run.palette_indices.len())
            .map_err(|_| format!("{} run length exceeds u32", entry.source_record_id))?;
        let run_end = run
            .x
            .checked_add(run_length)
            .ok_or_else(|| format!("{} run overflows x", entry.source_record_id))?;
        if run.y >= graph.frame.height || run.x >= graph.frame.width || run_end > graph.frame.width
        {
            return Err(format!(
                "{} contains an out-of-frame run at ({}, {})",
                entry.source_record_id, run.x, run.y
            ));
        }
        for (offset, palette_index) in run.palette_indices.iter().copied().enumerate() {
            let color = graph.palette.get(palette_index).ok_or_else(|| {
                format!(
                    "{} run references missing palette index {palette_index}",
                    entry.source_record_id
                )
            })?;
            if color[3] == 0 {
                return Err(format!(
                    "{} foreground run references a transparent palette entry",
                    entry.source_record_id
                ));
            }
            let x = usize::try_from(run.x)
                .map_err(|_| format!("{} x exceeds usize", entry.source_record_id))?
                + offset;
            let y = usize::try_from(run.y)
                .map_err(|_| format!("{} y exceeds usize", entry.source_record_id))?;
            let pixel_index = y * usize::from(width) + x;
            if coverage_mask[pixel_index] != 0 {
                return Err(format!(
                    "{} contains overlapping runs at ({x}, {y})",
                    entry.source_record_id
                ));
            }
            coverage_mask[pixel_index] = 1;
            rgba[pixel_index * 4..pixel_index * 4 + 4].copy_from_slice(color);
            rgb_white_background[pixel_index * 3..pixel_index * 3 + 3].copy_from_slice(&color[..3]);
            let x_u16 = u16::try_from(x)
                .map_err(|_| format!("{} x exceeds u16", entry.source_record_id))?;
            let y_u16 = u16::try_from(y)
                .map_err(|_| format!("{} y exceeds u16", entry.source_record_id))?;
            min_x = min_x.min(x_u16);
            min_y = min_y.min(y_u16);
            max_x = max_x.max(x_u16);
            max_y = max_y.max(y_u16);
            painted += 1;
        }
    }

    if painted != graph.foreground_pixel_count || painted != entry.foreground_pixel_count {
        return Err(format!(
            "{} painted {painted} pixels instead of {}",
            entry.source_record_id, entry.foreground_pixel_count
        ));
    }
    let bounds_width = max_x
        .checked_sub(min_x)
        .and_then(|value| value.checked_add(1))
        .ok_or_else(|| format!("{} has no foreground bounds", entry.source_record_id))?;
    let bounds_height = max_y
        .checked_sub(min_y)
        .and_then(|value| value.checked_add(1))
        .ok_or_else(|| format!("{} has no foreground bounds", entry.source_record_id))?;

    Ok(RuntimePoseGraphRaster {
        entry,
        width,
        height,
        rgba,
        rgb_sha256: sha256_hex(&rgb_white_background),
        coverage_mask_sha256: sha256_hex(&coverage_mask),
        rgb_white_background,
        coverage_mask,
        foreground_bounds: [min_x, min_y, bounds_width, bounds_height],
    })
}

fn validate_stored_graph(
    entry: &RuntimePoseGraphEntry,
    graph: &StoredPoseGraph,
) -> Result<(), String> {
    if graph.schema_version != 1
        || graph.graph_id != entry.graph_id
        || graph.source_record_id != entry.source_record_id
        || graph.source_sha256 != entry.source_sha256
        || [graph.frame.width, graph.frame.height] != entry.frame
        || graph.source_width != entry.source_size[0]
        || graph.source_height != entry.source_size[1]
        || [graph.offset_x, graph.offset_y] != entry.offset
        || graph.foreground_pixel_count != entry.foreground_pixel_count
        || graph.palette.is_empty()
        || graph.runs.is_empty()
    {
        return Err(format!(
            "{} stored graph metadata does not match the promoted manifest",
            entry.source_record_id
        ));
    }
    Ok(())
}

#[must_use]
pub fn resolved_runtime_pose_id(state: &WizardState) -> String {
    state
        .pose_id
        .clone()
        .unwrap_or_else(|| implicit_runtime_pose_id(state).to_string())
}

#[must_use]
pub fn implicit_runtime_pose_id(state: &WizardState) -> &'static str {
    if state.locomotion != Locomotion::Walking {
        return match state.facing {
            Direction::South => "idle_warm_camera_ready",
            Direction::SouthWest => "turn_front_3q_left",
            Direction::West => "turn_left_profile",
            Direction::NorthWest => "turn_back_3q_left",
            Direction::North => "turn_back_neutral",
            Direction::NorthEast => "turn_back_3q_right",
            Direction::East => "turn_right_profile",
            Direction::SouthEast => "turn_front_3q_right",
        };
    }

    match (state.walk_phase.rem_euclid(1.0) * 4.0).floor() as u8 {
        0 => "walk_contact_left",
        1 => "walk_passing_left",
        2 => "walk_up_left",
        _ => "walk_contact_right",
    }
}

#[must_use]
fn walk_mirror_for_state(state: &WizardState) -> f32 {
    if state.velocity.x > 0.01 {
        return -1.0;
    }
    1.0
}

#[must_use]
fn walking_direction_lean(state: &WizardState) -> f32 {
    if state.velocity.x > 0.01 {
        (state.velocity.x * 2.4).clamp(0.0, 3.0)
    } else if state.velocity.x < -0.01 {
        (state.velocity.x * 2.4).clamp(-3.0, 0.0)
    } else {
        0.0
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct RuntimeActorTransform {
    pub offset_x: f32,
    pub offset_y: f32,
    pub rotation_degrees: f32,
    pub scale_x: f32,
    pub scale_y: f32,
}

impl Default for RuntimeActorTransform {
    fn default() -> Self {
        Self {
            offset_x: 0.0,
            offset_y: 0.0,
            rotation_degrees: 0.0,
            scale_x: 1.0,
            scale_y: 1.0,
        }
    }
}

#[must_use]
pub fn runtime_actor_transform(state: &WizardState) -> RuntimeActorTransform {
    if state.locomotion != Locomotion::Walking {
        return RuntimeActorTransform::default();
    }
    let stride_angle = std::f32::consts::TAU * state.walk_phase.rem_euclid(1.0);
    let transfer = stride_angle.sin();
    let lift = transfer.abs();
    let contact_compression = 1.0 - lift;
    let lean = walking_direction_lean(state);
    let mirror = walk_mirror_for_state(state);
    RuntimeActorTransform {
        offset_x: transfer * 0.9,
        offset_y: -lift * 2.2,
        rotation_degrees: lean,
        scale_x: mirror * (1.0 + contact_compression * 0.012),
        scale_y: 1.0 - contact_compression * 0.012,
    }
}

#[must_use]
pub fn previous_runtime_pose_id(state: &WizardState) -> String {
    state
        .previous_pose_id
        .clone()
        .unwrap_or_else(|| resolved_runtime_pose_id(state))
}

pub fn runtime_graph_directory() -> Result<PathBuf, String> {
    if let Some(configured) = std::env::var_os("WIZARD_POSE_GRAPH_DIR") {
        let path = PathBuf::from(configured);
        if path.is_dir() {
            return Ok(path);
        }
        return Err(format!(
            "WIZARD_POSE_GRAPH_DIR is not a directory: {}",
            path.display()
        ));
    }
    if let Ok(executable) = std::env::current_exe() {
        if let Some(parent) = executable.parent() {
            let packaged = parent.join("assets/pose_graphs/v6");
            if packaged.is_dir() {
                return Ok(packaged);
            }
        }
    }
    let development = Path::new(env!("CARGO_MANIFEST_DIR")).join("assets/pose_graphs/v6");
    if development.is_dir() {
        return Ok(development);
    }
    Err("runtime pose graph directory is unavailable".to_string())
}

fn validate_manifest(manifest: &RuntimePoseGraphManifest) -> Result<(), String> {
    if manifest.schema_version != RUNTIME_POSE_GRAPH_SCHEMA_VERSION
        || manifest.compiler_id != RUNTIME_POSE_GRAPH_COMPILER_ID
    {
        return Err(format!(
            "unsupported runtime pose graph manifest {} from {}",
            manifest.schema_version, manifest.compiler_id
        ));
    }
    if manifest.source_count != RUNTIME_SOURCE_RECORD_COUNT
        || manifest.base_pose_count != RUNTIME_BASE_POSE_COUNT
        || manifest.forward_flight_count != RUNTIME_FORWARD_FLIGHT_COUNT
        || manifest.verified_pose_count != RUNTIME_POSE_GRAPH_COUNT
        || manifest.primary_pose_count != RUNTIME_POSE_GRAPH_COUNT
        || manifest.unique_semantic_pose_count != RUNTIME_UNIQUE_SEMANTIC_COUNT
        || manifest.entries.len() != RUNTIME_POSE_GRAPH_COUNT
        || manifest.frame != [1254, 1254]
    {
        return Err("runtime pose graph manifest counts/frame are not authoritative".to_string());
    }
    if manifest.archives.len() != 2
        || manifest
            .archives
            .iter()
            .any(|archive| !valid_sha256(&archive.archive_sha256))
    {
        return Err("runtime pose graph archive provenance is incomplete".to_string());
    }
    let mut source_ids = BTreeSet::new();
    let known_semantics = manifest
        .entries
        .iter()
        .map(|entry| entry.semantic_id.as_str())
        .collect::<BTreeSet<_>>();
    for entry in &manifest.entries {
        if !source_ids.insert(entry.source_record_id.as_str())
            || entry.frame != manifest.frame
            || entry.foreground_pixel_count == 0
            || entry.control_groups.is_empty()
            || entry.silhouette_iou_millionths != 1_000_000
            || entry.foreground_color_fidelity_millionths != 1_000_000
            || entry.foreground_color_match_ratio_millionths != 1_000_000
            || !entry.exact_rgba_equal
            || entry.rgba_mismatch_pixel_count != 0
            || entry.rgba_mismatch_channel_count != 0
            || !valid_sha256(&entry.source_sha256)
            || !valid_sha256(&entry.graph_sha256)
            || entry.anchor_x >= manifest.frame[0]
            || entry.anchor_y >= manifest.frame[1]
            || entry
                .authored_transition_neighbors
                .iter()
                .any(|neighbor| !known_semantics.contains(neighbor.as_str()))
        {
            return Err(format!(
                "invalid runtime pose graph entry {}",
                entry.source_record_id
            ));
        }
        let expected_path = format!("graphs/{}.pixelgraph.json.gz", entry.source_record_id);
        if entry.graph_path != expected_path {
            return Err(format!(
                "{} has a noncanonical graph path",
                entry.source_record_id
            ));
        }
    }
    Ok(())
}

fn valid_sha256(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|byte| byte.is_ascii_hexdigit())
}

fn sha256_hex(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embedded_catalog_has_every_verified_graph_and_control_identity() {
        let catalog = runtime_pose_graph_catalog().expect("runtime graph catalog");
        assert_eq!(catalog.manifest().entries.len(), 260);
        assert_eq!(catalog.primary_by_semantic_id.len(), 260);
        assert!(catalog
            .primary_for_semantic_id("idle_warm_camera_ready")
            .is_some());
        assert!(catalog
            .primary_for_semantic_id("walk_contact_left")
            .is_some());
        assert!(catalog
            .primary_for_semantic_id("fly_forward_camera_loop_close")
            .is_some());
        assert!(catalog.for_source_record_id("WJPA-0250").is_some());
        assert!(catalog.for_source_record_id("WJFF-0010").is_some());
        assert_eq!(
            catalog
                .for_runtime_pose_id("WJFF-0010")
                .map(|entry| entry.source_record_id.as_str()),
            Some("WJFF-0010")
        );
    }

    #[test]
    fn every_runtime_graph_hash_matches_the_promoted_file() {
        runtime_pose_graph_catalog()
            .expect("runtime graph catalog")
            .verify_runtime_files()
            .expect("all promoted runtime files");
    }

    #[test]
    fn graph_projection_reconstructs_base_and_flight_runtime_frames() {
        for pose_id in ["WJPA-0001", "idle_warm_camera_ready", "WJFF-0010"] {
            let raster = project_runtime_pose_graph(pose_id).expect("project runtime graph");
            assert_eq!([raster.width, raster.height], [1254, 1254]);
            assert_eq!(raster.rgba.len(), 1254 * 1254 * 4);
            assert_eq!(raster.coverage_mask.len(), 1254 * 1254);
            assert_eq!(
                raster
                    .coverage_mask
                    .iter()
                    .filter(|value| **value == 1)
                    .count() as u64,
                raster.entry.foreground_pixel_count
            );
            assert!(raster.foreground_bounds[2] > 0);
            assert!(raster.foreground_bounds[3] > 0);
        }
    }

    #[test]
    fn implicit_walk_uses_the_complete_authored_four_phase_cycle() {
        let mut state = WizardState {
            locomotion: Locomotion::Walking,
            facing: Direction::East,
            walk_phase: 0.1,
            ..WizardState::default()
        };
        assert_eq!(implicit_runtime_pose_id(&state), "walk_contact_left");
        state.walk_phase = 0.3;
        assert_eq!(implicit_runtime_pose_id(&state), "walk_passing_left");
        state.walk_phase = 0.6;
        assert_eq!(implicit_runtime_pose_id(&state), "walk_up_left");
        state.walk_phase = 0.9;
        assert_eq!(implicit_runtime_pose_id(&state), "walk_contact_right");

        state.locomotion = Locomotion::Idle;
        state.facing = Direction::North;
        assert_eq!(implicit_runtime_pose_id(&state), "turn_back_neutral");
    }

    #[test]
    fn explicit_performance_pose_owns_the_runtime_identity_while_moving() {
        let state = WizardState {
            locomotion: Locomotion::Walking,
            pose_id: Some("front_magic_staff_thrust".to_string()),
            ..WizardState::default()
        };
        assert_eq!(resolved_runtime_pose_id(&state), "front_magic_staff_thrust");
    }

    #[test]
    fn walking_transform_has_planted_contacts_and_airborne_weight_transfer() {
        let mut state = WizardState {
            locomotion: Locomotion::Walking,
            velocity: crate::state::Velocity { x: 1.0, z: 0.0 },
            walk_phase: 0.0,
            ..WizardState::default()
        };
        let contact = runtime_actor_transform(&state);
        assert!(contact.offset_y.abs() < f32::EPSILON);
        assert!(contact.scale_y < 1.0);
        assert!(contact.rotation_degrees > 0.0);
        assert!(contact.scale_x < 0.0);

        state.walk_phase = 0.25;
        let transfer = runtime_actor_transform(&state);
        assert!(transfer.offset_y < -2.0);
        assert!(transfer.offset_x > 0.8);
        assert!((transfer.scale_y - 1.0).abs() < f32::EPSILON);

        state.velocity.x = -1.0;
        let leftward = runtime_actor_transform(&state);
        assert!(leftward.rotation_degrees < 0.0);
        assert!(leftward.scale_x > 0.0);
    }
}
