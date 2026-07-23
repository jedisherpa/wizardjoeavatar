use crate::scene::{SceneCellRun, SceneElement, SceneLayerKind, ScenePixel};
use crate::state::SceneMode;
use flate2::read::GzDecoder;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::io::Read;
use std::sync::{Mutex, OnceLock};

const PROMOTION_MANIFEST: &str = include_str!("../assets/newsroom/v2/promotion-manifest.json");
const EXPECTED_PROMOTION_ID: &str = "wizard_joe_newsroom_v2_native_pixelgraphs";
const EXPECTED_SOURCE_COUNT: usize = 6;
const EXPECTED_TARGET_COUNT: usize = 27;
const EXPECTED_FOREGROUND_PIXELS: u64 = 4_233_630;

static MANIFEST: OnceLock<PromotionManifest> = OnceLock::new();
type ProjectionCacheKey = (u8, usize, usize);
type ProjectionCache = BTreeMap<ProjectionCacheKey, Vec<SceneElement>>;
static PROJECTED_CACHE: OnceLock<Mutex<ProjectionCache>> = OnceLock::new();

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PromotionManifest {
    schema_version: u32,
    promotion_id: String,
    layer_admission_ledger_path: String,
    layer_admission_ledger_sha256: String,
    source_manifest_sha256: String,
    target_specs_sha256: String,
    minimum_visual_alignment: f64,
    runtime_raster_assets: bool,
    native_canvas: [u32; 2],
    source_count: usize,
    target_count: usize,
    foreground_pixel_count: u64,
    scenes: Vec<PromotionScene>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PromotionScene {
    source_id: String,
    source_graph_sha256: String,
    source_target_spec_sha256: String,
    verification_report_path: String,
    verification_report_sha256: String,
    targets: Vec<PromotionTarget>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PromotionTarget {
    id: String,
    semantic_layer: String,
    order: i32,
    anchor: [u32; 2],
    occlusion: String,
    foreground_pixel_count: u64,
    evidence_graph_path: String,
    evidence_graph_sha256: String,
    runtime_graph_path: String,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FrameSpec {
    width: u32,
    height: u32,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PixelRun {
    y: u32,
    x: u32,
    palette_indices: Vec<u32>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PixelGraph {
    schema_version: u32,
    graph_id: String,
    source_record_id: String,
    source_sha256: String,
    frame: FrameSpec,
    source_width: u32,
    source_height: u32,
    offset_x: u32,
    offset_y: u32,
    foreground_pixel_count: u64,
    palette: Vec<[u8; 4]>,
    runs: Vec<PixelRun>,
}

#[derive(Clone, Debug, Serialize)]
pub struct NewsroomForegroundCatalog {
    pub schema_version: u32,
    pub native_canvas: [u32; 2],
    pub scenes: Vec<NewsroomForegroundScene>,
}

#[derive(Clone, Debug, Serialize)]
pub struct NewsroomForegroundScene {
    pub scene_mode: &'static str,
    pub targets: Vec<NewsroomForegroundTarget>,
}

#[derive(Clone, Debug, Serialize)]
pub struct NewsroomForegroundTarget {
    pub id: String,
    pub semantic_layer: String,
    pub order: i32,
    pub foreground_pixel_count: u64,
    pub graph_sha256: String,
}

#[must_use]
pub fn newsroom_foreground_catalog() -> NewsroomForegroundCatalog {
    newsroom_graph_catalog(false)
}

#[must_use]
pub fn newsroom_post_character_catalog() -> NewsroomForegroundCatalog {
    newsroom_graph_catalog(true)
}

fn newsroom_graph_catalog(post_character: bool) -> NewsroomForegroundCatalog {
    let modes = [
        SceneMode::NewsroomMain,
        SceneMode::NewsroomExplainer,
        SceneMode::NewsroomInterview,
        SceneMode::NewsroomBreaking,
        SceneMode::NewsroomProps,
        SceneMode::NewsroomOverlays,
        SceneMode::NewsroomCameraA,
        SceneMode::NewsroomCameraB,
    ];
    let scenes = modes
        .into_iter()
        .filter(|mode| post_character || *mode != SceneMode::NewsroomOverlays)
        .map(|mode| {
            let source_id = source_for_mode(mode);
            let mut targets = manifest()
                .scenes
                .iter()
                .find(|scene| scene.source_id == source_id)
                .expect("promoted newsroom mode must have an approved scene")
                .targets
                .iter()
                .filter(|target| {
                    if post_character {
                        is_post_character_layer(&target.semantic_layer)
                    } else {
                        target.semantic_layer == "foreground"
                    }
                })
                .map(|target| NewsroomForegroundTarget {
                    id: target.id.clone(),
                    semantic_layer: target.semantic_layer.clone(),
                    order: target.order,
                    foreground_pixel_count: target.foreground_pixel_count,
                    graph_sha256: target.evidence_graph_sha256.clone(),
                })
                .collect::<Vec<_>>();
            targets.sort_by_key(|target| target.order);
            NewsroomForegroundScene {
                scene_mode: scene_mode_id(mode),
                targets,
            }
        })
        .collect();
    NewsroomForegroundCatalog {
        schema_version: 1,
        native_canvas: manifest().native_canvas,
        scenes,
    }
}

#[must_use]
pub fn newsroom_foreground_graph_asset(
    mode: SceneMode,
    target_id: &str,
) -> Option<(&'static str, &'static [u8])> {
    newsroom_graph_asset(mode, target_id, false)
}

#[must_use]
pub fn newsroom_post_character_graph_asset(
    mode: SceneMode,
    target_id: &str,
) -> Option<(&'static str, &'static [u8])> {
    newsroom_graph_asset(mode, target_id, true)
}

fn newsroom_graph_asset(
    mode: SceneMode,
    target_id: &str,
    post_character: bool,
) -> Option<(&'static str, &'static [u8])> {
    if mode == SceneMode::Studio {
        return None;
    }
    let source_id = source_for_mode(mode);
    let target = manifest()
        .scenes
        .iter()
        .find(|scene| scene.source_id == source_id)?
        .targets
        .iter()
        .find(|target| {
            target.id == target_id
                && if post_character {
                    is_post_character_layer(&target.semantic_layer)
                } else {
                    target.semantic_layer == "foreground"
                }
        })?;
    let bytes = graph_asset(&target.runtime_graph_path);
    assert_eq!(sha256(bytes), target.evidence_graph_sha256);
    Some((target.evidence_graph_sha256.as_str(), bytes))
}

fn is_post_character_layer(layer: &str) -> bool {
    matches!(layer, "foreground" | "effect" | "broadcast_overlay")
}

fn scene_mode_id(mode: SceneMode) -> &'static str {
    match mode {
        SceneMode::Studio => "studio",
        SceneMode::NewsroomMain => "newsroom_main",
        SceneMode::NewsroomExplainer => "newsroom_explainer",
        SceneMode::NewsroomInterview => "newsroom_interview",
        SceneMode::NewsroomBreaking => "newsroom_breaking",
        SceneMode::NewsroomProps => "newsroom_props",
        SceneMode::NewsroomOverlays => "newsroom_overlays",
        SceneMode::NewsroomCameraA => "newsroom_camera_a",
        SceneMode::NewsroomCameraB => "newsroom_camera_b",
    }
}

#[must_use]
pub fn newsroom_scene_elements(mode: SceneMode, cols: usize, rows: usize) -> Vec<SceneElement> {
    if mode == SceneMode::Studio || cols == 0 || rows == 0 {
        return Vec::new();
    }
    let cache = PROJECTED_CACHE.get_or_init(|| Mutex::new(BTreeMap::new()));
    let key = (mode_cache_key(mode), cols, rows);
    if let Some(elements) = cache
        .lock()
        .expect("newsroom projection cache lock")
        .get(&key)
        .cloned()
    {
        return elements;
    }

    let source_id = source_for_mode(mode);
    let scene = manifest()
        .scenes
        .iter()
        .find(|scene| scene.source_id == source_id)
        .expect("promoted newsroom mode must have an approved scene");
    let elements = scene
        .targets
        .iter()
        .map(|target| project_target(target, cols, rows, manifest().native_canvas))
        .collect::<Vec<_>>();
    cache
        .lock()
        .expect("newsroom projection cache lock")
        .insert(key, elements.clone());
    elements
}

fn mode_cache_key(mode: SceneMode) -> u8 {
    match mode {
        SceneMode::Studio => 0,
        SceneMode::NewsroomMain => 1,
        SceneMode::NewsroomExplainer => 2,
        SceneMode::NewsroomInterview => 3,
        SceneMode::NewsroomBreaking => 4,
        SceneMode::NewsroomProps => 5,
        SceneMode::NewsroomOverlays => 6,
        SceneMode::NewsroomCameraA => 7,
        SceneMode::NewsroomCameraB => 8,
    }
}

fn source_for_mode(mode: SceneMode) -> &'static str {
    match mode {
        SceneMode::Studio => unreachable!("studio has no newsroom source"),
        SceneMode::NewsroomMain | SceneMode::NewsroomCameraA | SceneMode::NewsroomCameraB => {
            "main_anchor_desk_v2"
        }
        SceneMode::NewsroomExplainer => "standing_explainer_wall_v2",
        SceneMode::NewsroomInterview => "cohost_interview_v2",
        SceneMode::NewsroomBreaking => "magical_breaking_field_v2",
        SceneMode::NewsroomProps => "studio_furniture_displays_v2",
        SceneMode::NewsroomOverlays => "broadcast_magic_overlays_v2",
    }
}

fn manifest() -> &'static PromotionManifest {
    MANIFEST.get_or_init(|| {
        let manifest: PromotionManifest = serde_json::from_str(PROMOTION_MANIFEST)
            .expect("promoted newsroom manifest must parse");
        validate_manifest(&manifest);
        manifest
    })
}

fn validate_manifest(manifest: &PromotionManifest) {
    assert_eq!(manifest.schema_version, 1, "unsupported promotion schema");
    assert_eq!(manifest.promotion_id, EXPECTED_PROMOTION_ID);
    assert_eq!(manifest.source_count, EXPECTED_SOURCE_COUNT);
    assert_eq!(manifest.target_count, EXPECTED_TARGET_COUNT);
    assert_eq!(manifest.foreground_pixel_count, EXPECTED_FOREGROUND_PIXELS);
    assert!(!manifest.runtime_raster_assets);
    assert!(manifest.minimum_visual_alignment >= 0.95);
    assert_eq!(manifest.native_canvas, [1672, 941]);
    assert!(!manifest.layer_admission_ledger_path.is_empty());
    assert_hash(&manifest.layer_admission_ledger_sha256);
    assert_hash(&manifest.source_manifest_sha256);
    assert_hash(&manifest.target_specs_sha256);
    assert_eq!(manifest.scenes.len(), manifest.source_count);

    let mut source_ids = BTreeSet::new();
    let mut target_ids = BTreeSet::new();
    let mut target_count = 0;
    let mut pixel_count = 0;
    for scene in &manifest.scenes {
        assert!(source_ids.insert(scene.source_id.as_str()));
        assert_hash(&scene.source_graph_sha256);
        assert_hash(&scene.source_target_spec_sha256);
        assert!(!scene.verification_report_path.is_empty());
        assert_hash(&scene.verification_report_sha256);
        for target in &scene.targets {
            assert!(target_ids.insert(target.id.as_str()));
            assert!(!target.occlusion.is_empty());
            assert!(target.anchor[0] < manifest.native_canvas[0]);
            assert!(target.anchor[1] <= manifest.native_canvas[1]);
            assert!(!target.evidence_graph_path.is_empty());
            assert_hash(&target.evidence_graph_sha256);
            assert!(!target.runtime_graph_path.is_empty());
            target_count += 1;
            pixel_count += target.foreground_pixel_count;
        }
    }
    assert_eq!(target_count, manifest.target_count);
    assert_eq!(pixel_count, manifest.foreground_pixel_count);
}

fn project_target(
    target: &PromotionTarget,
    cols: usize,
    rows: usize,
    native_canvas: [u32; 2],
) -> SceneElement {
    let bytes = graph_asset(&target.runtime_graph_path);
    assert_eq!(sha256(bytes), target.evidence_graph_sha256);
    let mut decoder = GzDecoder::new(bytes);
    let mut json = Vec::new();
    decoder
        .read_to_end(&mut json)
        .expect("embedded pixel graph must decompress");
    let graph: PixelGraph = serde_json::from_slice(&json).expect("embedded pixel graph must parse");
    validate_graph(&graph, target, native_canvas);

    let native_width = native_canvas[0] as usize;
    let native_height = native_canvas[1] as usize;
    let mut native = vec![None; native_width * native_height];
    for run in &graph.runs {
        for (offset, palette_index) in run.palette_indices.iter().copied().enumerate() {
            let rgba = graph.palette[palette_index as usize];
            native[run.y as usize * native_width + run.x as usize + offset] =
                Some([rgba[0], rgba[1], rgba[2]]);
        }
    }

    let mut runs = Vec::new();
    for y in 0..rows {
        let source_y = sample_coordinate(y, rows, native_height);
        let mut x = 0;
        while x < cols {
            let source_x = sample_coordinate(x, cols, native_width);
            let Some(rgb) = native[source_y * native_width + source_x] else {
                x += 1;
                continue;
            };
            let x_start = x;
            let mut pixels = vec![ScenePixel { glyph: b'#', rgb }];
            x += 1;
            while x < cols {
                let source_x = sample_coordinate(x, cols, native_width);
                let Some(rgb) = native[source_y * native_width + source_x] else {
                    break;
                };
                pixels.push(ScenePixel { glyph: b'#', rgb });
                x += 1;
            }
            runs.push(SceneCellRun { y, x_start, pixels });
        }
    }
    let element = SceneElement {
        id: target.id.clone(),
        layer: semantic_layer(&target.semantic_layer),
        order: target.order,
        origin: [0, 0],
        width: cols,
        height: rows,
        visible: true,
        runs,
    };
    element
        .validate()
        .expect("projected native newsroom graph must be a valid scene element");
    element
}

fn validate_graph(graph: &PixelGraph, target: &PromotionTarget, native_canvas: [u32; 2]) {
    assert_eq!(graph.schema_version, 1);
    assert!(!graph.graph_id.is_empty());
    assert_eq!(graph.source_record_id, target.id);
    assert_hash(&graph.source_sha256);
    assert_eq!(graph.frame.width, native_canvas[0]);
    assert_eq!(graph.frame.height, native_canvas[1]);
    assert_eq!(graph.source_width, native_canvas[0]);
    assert_eq!(graph.source_height, native_canvas[1]);
    assert_eq!(graph.offset_x, 0);
    assert_eq!(graph.offset_y, 0);
    assert_eq!(graph.foreground_pixel_count, target.foreground_pixel_count);
    assert!(!graph.palette.is_empty());
    assert!(graph.palette.iter().all(|rgba| rgba[3] == 255));

    let mut previous_end = None;
    let mut actual_pixels = 0_u64;
    for run in &graph.runs {
        assert!(!run.palette_indices.is_empty());
        let end = run.x + run.palette_indices.len() as u32;
        assert!(run.y < graph.frame.height && end <= graph.frame.width);
        assert!(previous_end.is_none_or(|(y, x)| run.y > y || run.y == y && run.x >= x));
        assert!(run
            .palette_indices
            .iter()
            .all(|index| (*index as usize) < graph.palette.len()));
        previous_end = Some((run.y, end));
        actual_pixels += run.palette_indices.len() as u64;
    }
    assert_eq!(actual_pixels, graph.foreground_pixel_count);
}

fn semantic_layer(value: &str) -> SceneLayerKind {
    match value {
        "background" => SceneLayerKind::Background,
        "set_piece" => SceneLayerKind::SetPiece,
        "prop" => SceneLayerKind::Prop,
        "character" => SceneLayerKind::Character,
        "effect" => SceneLayerKind::Effect,
        "foreground" => SceneLayerKind::Foreground,
        "broadcast_overlay" => SceneLayerKind::BroadcastOverlay,
        other => panic!("unsupported promoted semantic layer {other}"),
    }
}

fn sample_coordinate(destination: usize, destination_size: usize, source_size: usize) -> usize {
    (((destination * 2 + 1) as u64 * source_size as u64) / (destination_size as u64 * 2))
        .min(source_size as u64 - 1) as usize
}

fn assert_hash(value: &str) {
    assert_eq!(value.len(), 64);
    assert!(value.bytes().all(|byte| byte.is_ascii_hexdigit()));
}

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn graph_asset(path: &str) -> &'static [u8] {
    match path {
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/main_anchor_desk_v2/main_anchor_desk_foreground.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/main_anchor_desk_v2/main_anchor_desk_foreground.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/main_anchor_desk_v2/main_anchor_rear_set.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/main_anchor_desk_v2/main_anchor_rear_set.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/standing_explainer_wall_v2/explainer_lectern_foreground.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/standing_explainer_wall_v2/explainer_lectern_foreground.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/standing_explainer_wall_v2/explainer_rear_set.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/standing_explainer_wall_v2/explainer_rear_set.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/cohost_interview_v2/interview_left_chair_foreground.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/cohost_interview_v2/interview_left_chair_foreground.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/cohost_interview_v2/interview_table_foreground.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/cohost_interview_v2/interview_table_foreground.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/cohost_interview_v2/interview_right_chair_foreground.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/cohost_interview_v2/interview_right_chair_foreground.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/cohost_interview_v2/interview_rear_set.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/cohost_interview_v2/interview_rear_set.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/magical_breaking_field_v2/breaking_lectern_foreground.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/magical_breaking_field_v2/breaking_lectern_foreground.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/magical_breaking_field_v2/breaking_platform_foreground.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/magical_breaking_field_v2/breaking_platform_foreground.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/magical_breaking_field_v2/breaking_rear_set.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/magical_breaking_field_v2/breaking_rear_set.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_desk.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_desk.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_chair_front.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_chair_front.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_chair_side.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_chair_side.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_lectern.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_lectern.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_display_large.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_display_large.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_display_small.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_display_small.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_light_tower.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_light_tower.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_side_table.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/studio_furniture_displays_v2/prop_side_table.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/magic_portal_console.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/magic_portal_console.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/magic_breaking_beacon.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/magic_breaking_beacon.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/magic_crystal_light.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/magic_crystal_light.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/magic_ring.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/magic_ring.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/overlay_lower_third_blank.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/overlay_lower_third_blank.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/overlay_source_card_blank.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/overlay_source_card_blank.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/overlay_two_box_blank.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/overlay_two_box_blank.pixelgraph.json.gz"),
        "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/effect_sparkle_cluster.pixelgraph.json.gz" => include_bytes!("../assets/newsroom/v2/graphs/broadcast_magic_overlays_v2/effect_sparkle_cluster.pixelgraph.json.gz"),
        other => panic!("promotion manifest references an unembedded graph: {other}"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn manifest_contains_only_exact_native_graph_assets() {
        let manifest = manifest();
        assert_eq!(manifest.source_count, 6);
        assert_eq!(manifest.target_count, 27);
        assert_eq!(manifest.foreground_pixel_count, 4_233_630);
        assert!(!manifest.runtime_raster_assets);
        for scene in &manifest.scenes {
            for target in &scene.targets {
                let bytes = graph_asset(&target.runtime_graph_path);
                assert_eq!(sha256(bytes), target.evidence_graph_sha256);
                assert!(!target.runtime_graph_path.ends_with(".png"));
                assert!(!target.runtime_graph_path.ends_with(".svg"));
            }
        }
    }

    #[test]
    fn all_approved_scene_modes_project_into_valid_layered_blocks() {
        for mode in [
            SceneMode::NewsroomMain,
            SceneMode::NewsroomExplainer,
            SceneMode::NewsroomInterview,
            SceneMode::NewsroomBreaking,
            SceneMode::NewsroomProps,
            SceneMode::NewsroomOverlays,
        ] {
            let elements = newsroom_scene_elements(mode, 480, 270);
            assert!(!elements.is_empty());
            assert!(elements.iter().all(|element| element.validate().is_ok()));
            assert!(elements.iter().all(|element| !element.runs.is_empty()));
        }
    }

    #[test]
    fn camera_modes_use_approved_set_art_not_reference_boards() {
        let main = newsroom_scene_elements(SceneMode::NewsroomMain, 320, 180);
        assert_eq!(
            newsroom_scene_elements(SceneMode::NewsroomCameraA, 320, 180),
            main
        );
        assert_eq!(
            newsroom_scene_elements(SceneMode::NewsroomCameraB, 320, 180),
            main
        );
        assert!(manifest()
            .scenes
            .iter()
            .all(|scene| !scene.source_id.contains("camera_board")));
    }

    #[test]
    fn foreground_catalog_exposes_only_verified_occluder_graphs() {
        let catalog = newsroom_foreground_catalog();
        assert_eq!(catalog.schema_version, 1);
        assert_eq!(catalog.native_canvas, [1672, 941]);
        assert_eq!(catalog.scenes.len(), 7);
        let expected_counts = [1, 1, 3, 2, 3, 1, 1];
        for (scene, expected_count) in catalog.scenes.iter().zip(expected_counts) {
            assert_eq!(scene.targets.len(), expected_count, "{}", scene.scene_mode);
            assert!(scene
                .targets
                .windows(2)
                .all(|pair| pair[0].order < pair[1].order));
            let mode = scene
                .scene_mode
                .parse::<SceneMode>()
                .expect("catalog scene mode");
            for target in &scene.targets {
                assert_eq!(target.semantic_layer, "foreground");
                let (sha256, bytes) = newsroom_foreground_graph_asset(mode, &target.id)
                    .expect("catalog target graph");
                assert_eq!(sha256, target.graph_sha256);
                let mut decoder = GzDecoder::new(bytes);
                let mut json = Vec::new();
                decoder.read_to_end(&mut json).expect("decompress graph");
                let graph: PixelGraph = serde_json::from_slice(&json).expect("parse graph");
                assert_eq!(graph.source_record_id, target.id);
                assert_eq!(graph.foreground_pixel_count, target.foreground_pixel_count);
            }
        }
    }

    #[test]
    fn post_character_catalog_preserves_every_approved_top_layer_in_order() {
        let catalog = newsroom_post_character_catalog();
        assert_eq!(catalog.scenes.len(), 8);
        let expected_counts = [1, 1, 3, 2, 3, 5, 1, 1];
        for (scene, expected_count) in catalog.scenes.iter().zip(expected_counts) {
            assert_eq!(scene.targets.len(), expected_count, "{}", scene.scene_mode);
            assert!(scene
                .targets
                .windows(2)
                .all(|pair| pair[0].order < pair[1].order));
            let mode = scene
                .scene_mode
                .parse::<SceneMode>()
                .expect("catalog scene mode");
            for target in &scene.targets {
                assert!(is_post_character_layer(&target.semantic_layer));
                let (sha256, bytes) = newsroom_post_character_graph_asset(mode, &target.id)
                    .expect("post-character target graph");
                assert_eq!(sha256, target.graph_sha256);
                assert!(!bytes.is_empty());
            }
        }
        let overlays = catalog
            .scenes
            .iter()
            .find(|scene| scene.scene_mode == "newsroom_overlays")
            .expect("overlay scene");
        assert!(overlays
            .targets
            .iter()
            .any(|target| target.semantic_layer == "effect"));
        assert!(overlays
            .targets
            .iter()
            .any(|target| target.semantic_layer == "broadcast_overlay"));
    }

    #[test]
    fn center_sampling_is_stable_at_edges() {
        assert_eq!(sample_coordinate(0, 480, 1672), 1);
        assert_eq!(sample_coordinate(479, 480, 1672), 1670);
        assert_eq!(sample_coordinate(0, 1, 1672), 836);
    }
}
