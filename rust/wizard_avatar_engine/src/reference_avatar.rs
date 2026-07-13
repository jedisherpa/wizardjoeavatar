use crate::cell::CellCanvas;
use crate::geometry::Point;
use crate::palette::Rgb;
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet};
use std::sync::OnceLock;

const REFERENCE_CELLS_JSON: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../wizard_avatar/definitions/reference_avatar_cells.json"
));
const REFERENCE_POSE_CELLS_JSON: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../wizard_avatar/definitions/reference_avatar_pose_cells.json"
));
const REFERENCE_ANIMATION_GRAPH_JSON: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../wizard_avatar/definitions/reference_avatar_animation_graph.json"
));

pub const REFERENCE_SCALE_MULTIPLIER: f32 = 0.90;

#[derive(Debug, Deserialize)]
struct ReferencePayload {
    cols: usize,
    rows: usize,
    root_anchor: [i32; 2],
    cells: Vec<ReferenceCell>,
}

#[derive(Debug, Deserialize)]
struct ReferencePoseLibrary {
    #[serde(default)]
    schema_version: Option<u32>,
    #[serde(default)]
    version: Option<u32>,
    #[serde(default)]
    asset_set_id: Option<String>,
    poses: Vec<ReferencePosePayload>,
}

#[derive(Debug, Deserialize)]
struct ReferencePosePayload {
    #[serde(alias = "pose_id")]
    id: String,
    #[serde(default)]
    description: String,
    cols: usize,
    rows: usize,
    root_anchor: [i32; 2],
    #[serde(default)]
    facing: Option<String>,
    #[serde(default)]
    locomotion: Option<String>,
    #[serde(default)]
    actions: Vec<String>,
    #[serde(default)]
    phase: Option<f32>,
    #[serde(default)]
    tags: Vec<String>,
    #[serde(default)]
    anchors: BTreeMap<String, [i32; 2]>,
    cells: Vec<ReferenceCell>,
}

#[derive(Debug, Deserialize)]
struct ReferenceCell {
    x: i32,
    y: i32,
    rgb: [u8; 3],
}

#[derive(Debug, Deserialize)]
pub struct ReferenceAnimationGraph {
    pub schema_version: u32,
    #[serde(default)]
    pub version: Option<u32>,
    pub asset_set_id: String,
    pub pose_library: String,
    pub default_pose_id: String,
    pub idle_by_facing: BTreeMap<String, String>,
    #[serde(default)]
    pub action_pose_overrides: BTreeMap<String, String>,
    #[serde(default)]
    pub walking_clips: BTreeMap<String, ReferenceAnimationClip>,
}

impl ReferenceAnimationGraph {
    #[must_use]
    pub fn idle_pose_for_facing(&self, facing: &str) -> Option<&str> {
        self.idle_by_facing.get(facing).map(String::as_str)
    }

    #[must_use]
    pub fn action_pose_for_action(&self, action: &str) -> Option<&str> {
        self.action_pose_overrides.get(action).map(String::as_str)
    }

    #[must_use]
    pub fn walking_pose_for_facing_phase(&self, facing: &str, phase: f32) -> Option<&str> {
        let clip = self
            .walking_clips
            .get(facing)
            .or_else(|| self.walking_clips.get("south"))?;
        clip.pose_at_phase(phase)
    }
}

#[derive(Debug, Deserialize)]
pub struct ReferenceAnimationClip {
    pub clip_id: String,
    #[serde(rename = "loop")]
    pub is_looping: bool,
    pub samples: Vec<ReferenceAnimationSample>,
}

impl ReferenceAnimationClip {
    #[must_use]
    pub fn pose_at_phase(&self, phase: f32) -> Option<&str> {
        let first = self.samples.first()?;
        let normalized = phase.rem_euclid(1.0);
        let mut selected = first;
        for sample in &self.samples {
            if sample.phase <= normalized + f32::EPSILON {
                selected = sample;
            }
        }
        Some(selected.pose_id.as_str())
    }
}

#[derive(Debug, Deserialize)]
pub struct ReferenceAnimationSample {
    pub phase: f32,
    pub pose_id: String,
    #[serde(default)]
    pub contact: Option<String>,
}

static REFERENCE_PAYLOAD: OnceLock<Option<ReferencePayload>> = OnceLock::new();
static REFERENCE_POSE_LIBRARY: OnceLock<Option<ReferencePoseLibrary>> = OnceLock::new();
static REFERENCE_POSE_CACHE: OnceLock<Option<BTreeMap<String, ReferencePose>>> = OnceLock::new();
static REFERENCE_ANIMATION_GRAPH: OnceLock<Option<ReferenceAnimationGraph>> = OnceLock::new();

#[derive(Clone, Debug, PartialEq)]
pub struct ReferencePoseMetadata {
    pub id: String,
    pub description: String,
    pub cols: usize,
    pub rows: usize,
    pub root_anchor: Point,
    pub facing: Option<String>,
    pub locomotion: Option<String>,
    pub actions: Vec<String>,
    pub phase: Option<f32>,
    pub tags: Vec<String>,
    pub anchors: BTreeMap<String, Point>,
}

#[derive(Clone, Debug)]
pub struct ReferencePose {
    pub pose_id: String,
    pub canvas: CellCanvas,
    pub root_anchor: Point,
    pub metadata: ReferencePoseMetadata,
}

fn payload() -> Option<&'static ReferencePayload> {
    REFERENCE_PAYLOAD
        .get_or_init(|| serde_json::from_str(REFERENCE_CELLS_JSON).ok())
        .as_ref()
}

fn pose_library() -> Option<&'static ReferencePoseLibrary> {
    REFERENCE_POSE_LIBRARY
        .get_or_init(|| serde_json::from_str(REFERENCE_POSE_CELLS_JSON).ok())
        .as_ref()
}

pub fn reference_animation_graph() -> Option<&'static ReferenceAnimationGraph> {
    REFERENCE_ANIMATION_GRAPH
        .get_or_init(|| serde_json::from_str(REFERENCE_ANIMATION_GRAPH_JSON).ok())
        .as_ref()
}

fn render_cells(cols: usize, rows: usize, cells: &[ReferenceCell]) -> CellCanvas {
    let mut canvas = CellCanvas::new(cols, rows);
    for cell in cells {
        canvas.set(
            cell.x,
            cell.y,
            b'#',
            Rgb(cell.rgb[0], cell.rgb[1], cell.rgb[2]),
        );
    }
    canvas
}

fn metadata_from_pose(pose: &ReferencePosePayload) -> ReferencePoseMetadata {
    let root_anchor = (pose.root_anchor[0], pose.root_anchor[1]);
    let mut anchors = pose
        .anchors
        .iter()
        .map(|(name, point)| (name.clone(), (point[0], point[1])))
        .collect::<BTreeMap<_, _>>();
    anchors.entry("root".to_string()).or_insert(root_anchor);

    ReferencePoseMetadata {
        id: pose.id.clone(),
        description: pose.description.clone(),
        cols: pose.cols,
        rows: pose.rows,
        root_anchor,
        facing: pose.facing.clone(),
        locomotion: pose.locomotion.clone(),
        actions: pose.actions.clone(),
        phase: pose.phase,
        tags: pose.tags.clone(),
        anchors,
    }
}

fn pose_cache() -> Option<&'static BTreeMap<String, ReferencePose>> {
    REFERENCE_POSE_CACHE
        .get_or_init(|| {
            let library = pose_library()?;
            Some(
                library
                    .poses
                    .iter()
                    .map(|pose| {
                        let metadata = metadata_from_pose(pose);
                        (
                            pose.id.clone(),
                            ReferencePose {
                                pose_id: pose.id.clone(),
                                canvas: render_cells(pose.cols, pose.rows, &pose.cells),
                                root_anchor: (pose.root_anchor[0], pose.root_anchor[1]),
                                metadata,
                            },
                        )
                    })
                    .collect(),
            )
        })
        .as_ref()
}

#[must_use]
pub fn reference_avatar_available() -> bool {
    payload().is_some()
}

#[must_use]
pub fn reference_pose_library_available() -> bool {
    pose_library()
        .map(|library| !library.poses.is_empty())
        .unwrap_or(false)
}

#[must_use]
pub fn reference_animation_graph_available() -> bool {
    reference_animation_graph().is_some()
}

#[must_use]
pub fn reference_pose_library_schema_version() -> Option<u32> {
    pose_library()?.schema_version
}

#[must_use]
pub fn reference_pose_library_version() -> Option<u32> {
    pose_library()?.version
}

#[must_use]
pub fn reference_pose_library_asset_set_id() -> Option<&'static str> {
    pose_library()?.asset_set_id.as_deref()
}

#[must_use]
pub fn reference_pose_ids() -> Vec<String> {
    pose_library()
        .map(|library| library.poses.iter().map(|pose| pose.id.clone()).collect())
        .unwrap_or_default()
}

#[must_use]
pub fn reference_pose_metadata(pose_id: &str) -> Option<ReferencePoseMetadata> {
    let pose = pose_library()?
        .poses
        .iter()
        .find(|pose| pose.id == pose_id)?;
    Some(metadata_from_pose(pose))
}

#[must_use]
pub fn reference_animation_graph_pose_ids() -> BTreeSet<String> {
    let mut pose_ids = BTreeSet::new();
    let Some(graph) = reference_animation_graph() else {
        return pose_ids;
    };
    pose_ids.insert(graph.default_pose_id.clone());
    pose_ids.extend(graph.idle_by_facing.values().cloned());
    pose_ids.extend(graph.action_pose_overrides.values().cloned());
    for clip in graph.walking_clips.values() {
        pose_ids.extend(clip.samples.iter().map(|sample| sample.pose_id.clone()));
    }
    pose_ids
}

#[must_use]
pub fn reference_root_anchor() -> Option<Point> {
    payload().map(|payload| (payload.root_anchor[0], payload.root_anchor[1]))
}

#[must_use]
pub fn render_reference_avatar_local() -> Option<CellCanvas> {
    let payload = payload()?;
    Some(render_cells(payload.cols, payload.rows, &payload.cells))
}

#[must_use]
pub fn render_reference_avatar_pose_local(pose_id: &str) -> Option<ReferencePose> {
    pose_cache()?.get(pose_id).cloned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reference_avatar_loads_generated_cell_mask() {
        let local = render_reference_avatar_local().expect("reference cells");
        assert_eq!(local.width, 74);
        assert_eq!(local.height, 96);
        assert_eq!(reference_root_anchor(), Some((37, 95)));
        assert!(reference_avatar_available());
    }

    #[test]
    fn reference_pose_library_loads_motion_copies() {
        assert!(reference_pose_library_available());
        assert_eq!(reference_pose_library_schema_version(), Some(2));
        assert_eq!(
            reference_pose_library_asset_set_id(),
            Some("wizardjoe-reference-motion-v1")
        );
        let front = render_reference_avatar_pose_local("front_idle").expect("front pose");
        let back = render_reference_avatar_pose_local("back_idle").expect("back pose");
        let magic = render_reference_avatar_pose_local("magic_cast").expect("magic pose");
        assert_eq!(front.pose_id, "front_idle");
        assert_eq!(front.metadata.facing.as_deref(), Some("south"));
        assert_eq!(
            magic.metadata.actions,
            vec!["magic_cast".to_string(), "reaction".to_string()]
        );
        assert!(front.metadata.anchors.contains_key("mouth"));
        assert_eq!(front.canvas.height, 96);
        assert_eq!(back.canvas.height, 96);
        assert_eq!(magic.canvas.height, 96);
        assert_eq!(front.canvas.width, back.canvas.width);
        assert!(front.canvas.width <= 74);
    }

    #[test]
    fn reference_animation_graph_loads_and_samples_walk_phase() {
        let graph = reference_animation_graph().expect("animation graph");
        assert!(reference_animation_graph_available());
        assert_eq!(graph.schema_version, 1);
        assert_eq!(graph.idle_pose_for_facing("south"), Some("front_idle"));
        assert_eq!(
            graph.action_pose_for_action("magic_cast"),
            Some("magic_cast")
        );
        assert_eq!(
            graph.walking_pose_for_facing_phase("south", 0.0),
            Some("walk_front_left")
        );
        assert_eq!(
            graph.walking_pose_for_facing_phase("south", 0.5),
            Some("walk_front_right")
        );
    }
}
