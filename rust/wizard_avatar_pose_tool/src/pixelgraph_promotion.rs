use crate::{
    read_pixel_graph, AdmissionLedger, AdmissionStatus, CompiledArchive, ContactMode, Direction,
    MotionFamily, Phase, SourceLedger, SourceRecordKind, MINIMUM_FIDELITY,
};
use flate2::read::GzDecoder;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File};
use std::io::{BufReader, Read, Write};
use std::path::{Path, PathBuf};

pub const PIXELGRAPH_PROMOTION_SCHEMA_VERSION: u32 = 1;
const COMPILER_ID: &str = "wizard-avatar-pose-tool-rust-pixelgraph-v5";
const EXPECTED_SOURCE_RECORDS: usize = 158;
const EXPECTED_VERIFIED_GRAPHS: usize = 120;
const EXPECTED_EXCLUSIONS: usize = 38;
const EXPECTED_UNIQUE_SEMANTICS: usize = 110;
const ADMISSION_LEDGER: &str = "docs/pose-admission/wizard-joe-admission-ledger.json";
const SOURCE_LEDGER: &str = "docs/pose-admission/wizard-joe-source-ledger.json";
const V4_ARCHIVE: &str = "rust/wizard_avatar_engine/assets/wizard_pose_library.v4.json.gz";
const ACTION_MANIFEST: &str = "evidence/pose-library-expansion/intake/manifest.json";
const FEELINGS_QUEUE: &str = "docs/pose-library-expansion/feelings-queue.json";
const OUTPUT_MANIFEST: &str =
    "rust/wizard_avatar_engine/assets/pose_graphs/v5/runtime-manifest.json";

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimePoseGraphEntry {
    pub sequence: usize,
    pub source_record_id: String,
    pub candidate_id: String,
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
    pub motion_family: MotionFamily,
    pub contact_mode: ContactMode,
    pub phase: Option<Phase>,
    pub direction: Direction,
    pub authored_transition_neighbors: Vec<String>,
    pub control_groups: Vec<String>,
    pub primary_for_semantic_id: bool,
    pub duplicate_source_of: Option<String>,
    pub silhouette_iou_millionths: u32,
    pub foreground_color_fidelity_millionths: u32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PixelGraphPromotionManifest {
    pub schema_version: u32,
    pub compiler_id: String,
    pub admission_ledger_path: String,
    pub admission_ledger_sha256: String,
    pub source_ledger_path: String,
    pub source_ledger_sha256: String,
    pub expected_source_record_count: usize,
    pub verified_pose_count: usize,
    pub excluded_non_pose_count: usize,
    pub unique_semantic_pose_count: usize,
    pub frame: [u32; 2],
    pub entries: Vec<RuntimePoseGraphEntry>,
    pub manifest_sha256: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PixelGraphPromotionReceipt {
    pub manifest_path: String,
    pub manifest_sha256: String,
    pub verified_pose_count: usize,
    pub excluded_non_pose_count: usize,
    pub unique_semantic_pose_count: usize,
}

#[derive(Debug, thiserror::Error)]
pub enum PixelGraphPromotionError {
    #[error("I/O error at {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("JSON error at {path}: {source}")]
    Json {
        path: PathBuf,
        #[source]
        source: serde_json::Error,
    },
    #[error("pixel graph promotion invariant failed: {0}")]
    Invariant(String),
    #[error(transparent)]
    PixelGraph(#[from] crate::PixelGraphError),
}

#[derive(Clone, Debug)]
struct SemanticSpec {
    candidate_id: String,
    semantic_id: String,
    display_name: String,
    motion_family: MotionFamily,
    contact_mode: ContactMode,
    phase: Option<Phase>,
    direction: Direction,
    neighbors: Vec<String>,
    control_groups: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct ActionManifest {
    packs: Vec<ActionPack>,
}

#[derive(Debug, Deserialize)]
struct ActionPack {
    images: Vec<ActionImage>,
}

#[derive(Debug, Deserialize)]
struct ActionImage {
    candidate_id: String,
    semantic_id: String,
    source_filename: String,
}

#[derive(Debug, Deserialize)]
struct FeelingsQueue {
    candidates: Vec<FeelingCandidate>,
}

#[derive(Debug, Deserialize)]
struct FeelingCandidate {
    archive_entry: String,
    id: String,
    semantic_id: String,
}

pub fn promote_verified_pose_graphs(
    repo_root: impl AsRef<Path>,
) -> Result<PixelGraphPromotionReceipt, PixelGraphPromotionError> {
    let repo_root = repo_root.as_ref();
    let admission_path = repo_root.join(ADMISSION_LEDGER);
    let source_path = repo_root.join(SOURCE_LEDGER);
    let admission: AdmissionLedger = read_json(&admission_path)?;
    let source: SourceLedger = read_json(&source_path)?;
    validate_terminal_ledgers(&admission, &source)?;

    let v4 = read_gzip_json::<CompiledArchive>(&repo_root.join(V4_ARCHIVE))?;
    let action: ActionManifest = read_json(&repo_root.join(ACTION_MANIFEST))?;
    let feelings: FeelingsQueue = read_json(&repo_root.join(FEELINGS_QUEUE))?;
    let specs = semantic_specs(&v4, &action, &feelings)?;
    let source_by_id = source
        .records
        .iter()
        .map(|record| (record.record_id.as_str(), record))
        .collect::<BTreeMap<_, _>>();

    let mut entries = Vec::with_capacity(EXPECTED_VERIFIED_GRAPHS);
    let mut primary_by_semantic = BTreeMap::<String, String>::new();
    let mut primary_by_source_hash = BTreeMap::<String, String>::new();
    for admission_entry in admission
        .entries
        .iter()
        .filter(|entry| entry.status == AdmissionStatus::VisuallyVerified)
    {
        let source_record = source_by_id
            .get(admission_entry.source_record_id.as_str())
            .ok_or_else(|| {
                invariant(format!(
                    "{} is absent from the source ledger",
                    admission_entry.source_record_id
                ))
            })?;
        if source_record.kind != SourceRecordKind::PoseCandidate {
            return Err(invariant(format!(
                "{} is not a pose candidate",
                source_record.record_id
            )));
        }
        let spec = specs.get(source_record.record_id.as_str()).ok_or_else(|| {
            invariant(format!(
                "{} has no semantic/control specification",
                source_record.record_id
            ))
        })?;
        let graph_path = admission_entry
            .graph_path
            .as_ref()
            .ok_or_else(|| invariant(format!("{} has no graph path", source_record.record_id)))?;
        let expected_graph_sha = admission_entry
            .graph_sha256
            .as_ref()
            .ok_or_else(|| invariant(format!("{} has no graph hash", source_record.record_id)))?;
        let absolute_graph_path = repo_root.join(graph_path);
        let actual_graph_sha = sha256_file(&absolute_graph_path)?;
        if actual_graph_sha != *expected_graph_sha {
            return Err(invariant(format!(
                "{} graph hash mismatch: {} != {}",
                source_record.record_id, actual_graph_sha, expected_graph_sha
            )));
        }
        let graph = read_pixel_graph(&absolute_graph_path)?;
        if graph.source_record_id != source_record.record_id
            || graph.source_sha256 != source_record.sha256
            || graph.frame != admission.frame
        {
            return Err(invariant(format!(
                "{} graph provenance/frame mismatch",
                source_record.record_id
            )));
        }
        let silhouette = admission_entry.silhouette_iou.ok_or_else(|| {
            invariant(format!("{} lacks silhouette IoU", source_record.record_id))
        })?;
        let color = admission_entry.foreground_color_fidelity.ok_or_else(|| {
            invariant(format!(
                "{} lacks foreground color fidelity",
                source_record.record_id
            ))
        })?;
        if silhouette < MINIMUM_FIDELITY || color < MINIMUM_FIDELITY {
            return Err(invariant(format!(
                "{} fell below the 95% admission gate",
                source_record.record_id
            )));
        }

        let primary_for_semantic_id = !primary_by_semantic.contains_key(&spec.semantic_id);
        if primary_for_semantic_id {
            primary_by_semantic.insert(spec.semantic_id.clone(), source_record.record_id.clone());
        }
        let duplicate_source_of = primary_by_source_hash.get(&source_record.sha256).cloned();
        primary_by_source_hash
            .entry(source_record.sha256.clone())
            .or_insert_with(|| source_record.record_id.clone());
        entries.push(RuntimePoseGraphEntry {
            sequence: admission_entry.sequence,
            source_record_id: source_record.record_id.clone(),
            candidate_id: spec.candidate_id.clone(),
            semantic_id: spec.semantic_id.clone(),
            display_name: spec.display_name.clone(),
            source_archive: source_record.archive_filename.clone(),
            source_entry: source_record.archive_entry.clone(),
            source_sha256: source_record.sha256.clone(),
            graph_path: graph_path.clone(),
            graph_sha256: actual_graph_sha,
            graph_id: graph.graph_id,
            frame: [graph.frame.width, graph.frame.height],
            source_size: [graph.source_width, graph.source_height],
            offset: [graph.offset_x, graph.offset_y],
            foreground_pixel_count: graph.foreground_pixel_count,
            motion_family: spec.motion_family,
            contact_mode: spec.contact_mode,
            phase: spec.phase,
            direction: spec.direction,
            authored_transition_neighbors: spec.neighbors.clone(),
            control_groups: spec.control_groups.clone(),
            primary_for_semantic_id,
            duplicate_source_of,
            silhouette_iou_millionths: fidelity_millionths(silhouette),
            foreground_color_fidelity_millionths: fidelity_millionths(color),
        });
    }
    entries.sort_by_key(|entry| entry.sequence);
    validate_promoted_entries(&entries, &primary_by_semantic)?;

    let output_path = repo_root.join(OUTPUT_MANIFEST);
    let mut manifest = PixelGraphPromotionManifest {
        schema_version: PIXELGRAPH_PROMOTION_SCHEMA_VERSION,
        compiler_id: COMPILER_ID.to_string(),
        admission_ledger_path: ADMISSION_LEDGER.to_string(),
        admission_ledger_sha256: sha256_file(&admission_path)?,
        source_ledger_path: SOURCE_LEDGER.to_string(),
        source_ledger_sha256: sha256_file(&source_path)?,
        expected_source_record_count: EXPECTED_SOURCE_RECORDS,
        verified_pose_count: EXPECTED_VERIFIED_GRAPHS,
        excluded_non_pose_count: EXPECTED_EXCLUSIONS,
        unique_semantic_pose_count: EXPECTED_UNIQUE_SEMANTICS,
        frame: [admission.frame.width, admission.frame.height],
        entries,
        manifest_sha256: String::new(),
    };
    manifest.manifest_sha256 = manifest_content_sha256(&manifest)?;
    write_json(&output_path, &manifest)?;
    let manifest_sha256 = sha256_file(&output_path)?;
    Ok(PixelGraphPromotionReceipt {
        manifest_path: OUTPUT_MANIFEST.to_string(),
        manifest_sha256,
        verified_pose_count: manifest.verified_pose_count,
        excluded_non_pose_count: manifest.excluded_non_pose_count,
        unique_semantic_pose_count: manifest.unique_semantic_pose_count,
    })
}

fn validate_terminal_ledgers(
    admission: &AdmissionLedger,
    source: &SourceLedger,
) -> Result<(), PixelGraphPromotionError> {
    if admission.expected_pose_count != EXPECTED_SOURCE_RECORDS
        || admission.entries.len() != EXPECTED_SOURCE_RECORDS
        || admission.verified_pose_count != EXPECTED_VERIFIED_GRAPHS
        || admission.excluded_non_pose_count != EXPECTED_EXCLUSIONS
        || admission.awaiting_visual_comparison_count != 0
        || admission.failed_pose_count != 0
        || admission.queued_pose_count != 0
    {
        return Err(invariant(
            "admission ledger is not at the required 120 verified / 38 excluded terminal state",
        ));
    }
    let candidate_count = source
        .records
        .iter()
        .filter(|record| record.kind == SourceRecordKind::PoseCandidate)
        .count();
    if candidate_count != EXPECTED_SOURCE_RECORDS {
        return Err(invariant(format!(
            "source ledger contains {candidate_count} pose candidates, expected {EXPECTED_SOURCE_RECORDS}"
        )));
    }
    Ok(())
}

fn validate_promoted_entries(
    entries: &[RuntimePoseGraphEntry],
    primary_by_semantic: &BTreeMap<String, String>,
) -> Result<(), PixelGraphPromotionError> {
    if entries.len() != EXPECTED_VERIFIED_GRAPHS
        || primary_by_semantic.len() != EXPECTED_UNIQUE_SEMANTICS
    {
        return Err(invariant(format!(
            "promotion produced {} entries and {} unique semantics",
            entries.len(),
            primary_by_semantic.len()
        )));
    }
    let source_ids = entries
        .iter()
        .map(|entry| entry.source_record_id.as_str())
        .collect::<BTreeSet<_>>();
    if source_ids.len() != entries.len() {
        return Err(invariant("promoted source IDs are not unique"));
    }
    for entry in entries {
        if entry.control_groups.is_empty()
            || entry.silhouette_iou_millionths < 950_000
            || entry.foreground_color_fidelity_millionths < 950_000
        {
            return Err(invariant(format!(
                "{} lacks control metadata or verified fidelity",
                entry.source_record_id
            )));
        }
    }
    Ok(())
}

fn semantic_specs(
    archive: &CompiledArchive,
    action: &ActionManifest,
    feelings: &FeelingsQueue,
) -> Result<BTreeMap<String, SemanticSpec>, PixelGraphPromotionError> {
    let mut metadata = archive
        .poses
        .iter()
        .map(|pose| (pose.semantic_id.as_str(), pose))
        .collect::<BTreeMap<_, _>>();
    for alias in &archive.aliases {
        let target = metadata
            .get(alias.target_semantic_id.as_str())
            .copied()
            .ok_or_else(|| invariant(format!("alias {} lost target", alias.semantic_id)))?;
        metadata.insert(alias.semantic_id.as_str(), target);
    }

    let mut specs = BTreeMap::new();
    let baseline = [
        (
            "WJSRC-0001",
            "WJBASE-01",
            "front_idle",
            "Front Idle",
            Direction::South,
            MotionFamily::GroundAction,
            ContactMode::BothFeet,
            "idle",
        ),
        (
            "WJSRC-0002",
            "WJBASE-02",
            "back_idle",
            "Back Idle",
            Direction::North,
            MotionFamily::GroundAction,
            ContactMode::BothFeet,
            "idle",
        ),
        (
            "WJSRC-0003",
            "WJBASE-03",
            "profile_right",
            "Profile Right",
            Direction::East,
            MotionFamily::GroundAction,
            ContactMode::BothFeet,
            "idle",
        ),
        (
            "WJSRC-0004",
            "WJBASE-04",
            "profile_left",
            "Profile Left",
            Direction::West,
            MotionFamily::GroundAction,
            ContactMode::BothFeet,
            "idle",
        ),
        (
            "WJSRC-0005",
            "WJBASE-05",
            "walk_front_left",
            "Walk Front Left",
            Direction::South,
            MotionFamily::Walk,
            ContactMode::RightFoot,
            "walk",
        ),
        (
            "WJSRC-0006",
            "WJBASE-06",
            "walk_front_right",
            "Walk Front Right",
            Direction::South,
            MotionFamily::Walk,
            ContactMode::LeftFoot,
            "walk",
        ),
        (
            "WJSRC-0007",
            "WJBASE-07",
            "back_left",
            "Walk Back Left",
            Direction::North,
            MotionFamily::Walk,
            ContactMode::RightFoot,
            "walk",
        ),
        (
            "WJSRC-0008",
            "WJBASE-08",
            "back_right",
            "Walk Back Right",
            Direction::North,
            MotionFamily::Walk,
            ContactMode::LeftFoot,
            "walk",
        ),
        (
            "WJSRC-0009",
            "WJBASE-09",
            "explaining",
            "Explaining",
            Direction::South,
            MotionFamily::GroundAction,
            ContactMode::BothFeet,
            "conversation",
        ),
        (
            "WJSRC-0010",
            "WJBASE-10",
            "magic_cast",
            "Magic Cast",
            Direction::South,
            MotionFamily::GroundAction,
            ContactMode::BothFeetAndStaff,
            "magic",
        ),
    ];
    for (record, candidate, semantic, name, direction, family, contact, group) in baseline {
        specs.insert(
            record.to_string(),
            SemanticSpec {
                candidate_id: candidate.to_string(),
                semantic_id: semantic.to_string(),
                display_name: name.to_string(),
                motion_family: family,
                contact_mode: contact,
                phase: None,
                direction,
                neighbors: baseline_neighbors(semantic),
                control_groups: vec![group.to_string(), "baseline".to_string()],
            },
        );
    }

    let actions = action
        .packs
        .iter()
        .flat_map(|pack| pack.images.iter())
        .map(|image| (image.source_filename.as_str(), image))
        .collect::<BTreeMap<_, _>>();
    for sequence in 12..=41 {
        let record_id = format!("WJSRC-{sequence:04}");
        let action_image = actions
            .values()
            .find(|image| source_sequence_for_action(&image.candidate_id) == Some(sequence))
            .ok_or_else(|| invariant(format!("{record_id} has no action mapping")))?;
        let pose = metadata
            .get(action_image.semantic_id.as_str())
            .copied()
            .ok_or_else(|| {
                invariant(format!(
                    "{} has no v4 motion metadata",
                    action_image.semantic_id
                ))
            })?;
        specs.insert(
            record_id,
            SemanticSpec {
                candidate_id: action_image.candidate_id.clone(),
                semantic_id: action_image.semantic_id.clone(),
                display_name: title_case(&action_image.semantic_id),
                motion_family: pose.motion.family,
                contact_mode: pose.motion.contact_mode,
                phase: pose.motion.phase,
                direction: pose.facing.direction,
                neighbors: pose.motion.authored_transition_neighbors.clone(),
                control_groups: control_groups_for(&action_image.semantic_id, pose.motion.family),
            },
        );
    }

    let feelings_by_entry = feelings
        .candidates
        .iter()
        .map(|candidate| (candidate.archive_entry.as_str(), candidate))
        .collect::<BTreeMap<_, _>>();
    for (offset, candidate) in feelings.candidates.iter().enumerate() {
        let record_id = format!("WJSRC-{:04}", 42 + offset);
        let matched = feelings_by_entry
            .get(candidate.archive_entry.as_str())
            .copied()
            .ok_or_else(|| invariant(format!("{} lost feelings mapping", candidate.id)))?;
        let pose = metadata
            .get(matched.semantic_id.as_str())
            .copied()
            .ok_or_else(|| {
                invariant(format!("{} has no v4 motion metadata", matched.semantic_id))
            })?;
        specs.insert(
            record_id,
            SemanticSpec {
                candidate_id: matched.id.clone(),
                semantic_id: matched.semantic_id.clone(),
                display_name: title_case(&matched.semantic_id),
                motion_family: pose.motion.family,
                contact_mode: pose.motion.contact_mode,
                phase: pose.motion.phase,
                direction: pose.facing.direction,
                neighbors: pose.motion.authored_transition_neighbors.clone(),
                control_groups: control_groups_for(&matched.semantic_id, pose.motion.family),
            },
        );
    }

    for (index, (semantic, name, family, contact, groups)) in dance_specs().into_iter().enumerate()
    {
        let sequence = 140 + index;
        specs.insert(
            format!("WJSRC-{sequence:04}"),
            SemanticSpec {
                candidate_id: format!("WJDANCE-{:02}", index + 1),
                semantic_id: semantic.to_string(),
                display_name: name.to_string(),
                motion_family: family,
                contact_mode: contact,
                phase: None,
                direction: Direction::South,
                neighbors: dance_neighbors(index),
                control_groups: groups.iter().map(|value| (*value).to_string()).collect(),
            },
        );
    }
    Ok(specs)
}

fn source_sequence_for_action(candidate_id: &str) -> Option<usize> {
    let number = candidate_id.rsplit('-').next()?.parse::<usize>().ok()?;
    match candidate_id.split('-').next()? {
        "WJP2" => Some(11 + number),
        "WJFA" if number <= 10 => Some(21 + number),
        "WJFA" => Some(21 + number),
        _ => None,
    }
}

fn baseline_neighbors(semantic_id: &str) -> Vec<String> {
    match semantic_id {
        "walk_front_left" => vec!["front_idle", "walk_front_right"],
        "walk_front_right" => vec!["walk_front_left", "front_idle"],
        "back_left" => vec!["back_idle", "back_right"],
        "back_right" => vec!["back_left", "back_idle"],
        "explaining" | "magic_cast" => vec!["front_idle"],
        _ => vec![semantic_id],
    }
    .into_iter()
    .map(str::to_string)
    .collect()
}

fn control_groups_for(semantic_id: &str, family: MotionFamily) -> Vec<String> {
    let mut groups = vec![match family {
        MotionFamily::Run => "run",
        MotionFamily::Walk => "walk",
        MotionFamily::Flight => "flight",
        MotionFamily::Jump => "jump",
        MotionFamily::Landing => "landing",
        MotionFamily::GroundAction => "action",
        MotionFamily::Kneel => "kneel",
    }
    .to_string()];
    if semantic_id.starts_with("feeling_") {
        groups.push("emotion".to_string());
    }
    if semantic_id.contains("staff") || semantic_id.contains("magic") {
        groups.push("staff".to_string());
    }
    if semantic_id.contains("explain")
        || semantic_id.contains("point")
        || semantic_id.contains("greeting")
        || semantic_id.contains("sincere")
        || semantic_id.contains("shush")
    {
        groups.push("conversation".to_string());
    }
    groups.sort();
    groups.dedup();
    groups
}

type DanceSpec = (
    &'static str,
    &'static str,
    MotionFamily,
    ContactMode,
    &'static [&'static str],
);

fn dance_specs() -> [DanceSpec; 20] {
    [
        (
            "dance_groove_step",
            "Groove Step",
            MotionFamily::Walk,
            ContactMode::LeftFoot,
            &["dance", "groove"],
        ),
        (
            "dance_side_rock",
            "Side Rock",
            MotionFamily::Walk,
            ContactMode::RightFoot,
            &["dance", "groove"],
        ),
        (
            "dance_bounce_groove",
            "Bounce Groove",
            MotionFamily::GroundAction,
            ContactMode::BothFeet,
            &["dance", "groove"],
        ),
        (
            "dance_kick_step",
            "Kick Step",
            MotionFamily::Jump,
            ContactMode::LeftFoot,
            &["dance", "groove"],
        ),
        (
            "dance_shoulder_pop",
            "Shoulder Pop",
            MotionFamily::GroundAction,
            ContactMode::BothFeet,
            &["dance", "groove"],
        ),
        (
            "dance_heel_toe",
            "Heel-Toe",
            MotionFamily::Walk,
            ContactMode::RightFoot,
            &["dance", "groove"],
        ),
        (
            "dance_knee_drop_prep",
            "Knee Drop Prep",
            MotionFamily::Kneel,
            ContactMode::LeftFoot,
            &["dance", "groove"],
        ),
        (
            "dance_arm_wave",
            "Arm Wave",
            MotionFamily::GroundAction,
            ContactMode::BothFeet,
            &["dance", "groove"],
        ),
        (
            "dance_spin_entry",
            "Spin Entry",
            MotionFamily::GroundAction,
            ContactMode::BothFeet,
            &["dance", "groove"],
        ),
        (
            "dance_groove_finish",
            "Groove Finish",
            MotionFamily::GroundAction,
            ContactMode::BothFeet,
            &["dance", "groove"],
        ),
        (
            "breakdance_top_rock_1",
            "Top Rock 1",
            MotionFamily::Walk,
            ContactMode::LeftFoot,
            &["dance", "breakdance"],
        ),
        (
            "breakdance_top_rock_2",
            "Top Rock 2",
            MotionFamily::Walk,
            ContactMode::RightFoot,
            &["dance", "breakdance"],
        ),
        (
            "breakdance_drop",
            "Drop",
            MotionFamily::Landing,
            ContactMode::BothFeet,
            &["dance", "breakdance"],
        ),
        (
            "breakdance_six_step",
            "Six Step",
            MotionFamily::GroundAction,
            ContactMode::HandFootAndStaff,
            &["dance", "breakdance"],
        ),
        (
            "breakdance_baby_freeze",
            "Baby Freeze",
            MotionFamily::GroundAction,
            ContactMode::HandFootAndStaff,
            &["dance", "breakdance"],
        ),
        (
            "breakdance_chair_freeze",
            "Chair Freeze",
            MotionFamily::GroundAction,
            ContactMode::HandFootAndStaff,
            &["dance", "breakdance"],
        ),
        (
            "breakdance_handstand",
            "Handstand",
            MotionFamily::GroundAction,
            ContactMode::HandFootAndStaff,
            &["dance", "breakdance"],
        ),
        (
            "breakdance_windmill",
            "Windmill",
            MotionFamily::GroundAction,
            ContactMode::HandFootAndStaff,
            &["dance", "breakdance"],
        ),
        (
            "breakdance_backspin",
            "Backspin",
            MotionFamily::GroundAction,
            ContactMode::HandFootAndStaff,
            &["dance", "breakdance"],
        ),
        (
            "breakdance_finish",
            "Finish",
            MotionFamily::GroundAction,
            ContactMode::BothFeet,
            &["dance", "breakdance"],
        ),
    ]
}

fn dance_neighbors(index: usize) -> Vec<String> {
    let specs = dance_specs();
    let mut neighbors = Vec::new();
    if index > 0 {
        neighbors.push(specs[index - 1].0.to_string());
    }
    if index + 1 < specs.len() {
        neighbors.push(specs[index + 1].0.to_string());
    }
    neighbors
}

fn title_case(value: &str) -> String {
    value
        .split('_')
        .map(|word| {
            let mut chars = word.chars();
            chars.next().map_or_else(String::new, |first| {
                first.to_uppercase().chain(chars).collect::<String>()
            })
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn fidelity_millionths(value: f64) -> u32 {
    (value.clamp(0.0, 1.0) * 1_000_000.0).round() as u32
}

fn manifest_content_sha256(
    manifest: &PixelGraphPromotionManifest,
) -> Result<String, PixelGraphPromotionError> {
    let mut content = manifest.clone();
    content.manifest_sha256.clear();
    let bytes = serde_json::to_vec(&content).map_err(|source| PixelGraphPromotionError::Json {
        path: PathBuf::from(OUTPUT_MANIFEST),
        source,
    })?;
    Ok(format!("{:x}", Sha256::digest(bytes)))
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, PixelGraphPromotionError> {
    let file = File::open(path).map_err(|source| PixelGraphPromotionError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    serde_json::from_reader(BufReader::new(file)).map_err(|source| PixelGraphPromotionError::Json {
        path: path.to_path_buf(),
        source,
    })
}

fn read_gzip_json<T: for<'de> Deserialize<'de>>(
    path: &Path,
) -> Result<T, PixelGraphPromotionError> {
    let file = File::open(path).map_err(|source| PixelGraphPromotionError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    serde_json::from_reader(GzDecoder::new(BufReader::new(file))).map_err(|source| {
        PixelGraphPromotionError::Json {
            path: path.to_path_buf(),
            source,
        }
    })
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), PixelGraphPromotionError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|source| PixelGraphPromotionError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    let mut file = File::create(path).map_err(|source| PixelGraphPromotionError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let bytes =
        serde_json::to_vec_pretty(value).map_err(|source| PixelGraphPromotionError::Json {
            path: path.to_path_buf(),
            source,
        })?;
    file.write_all(&bytes)
        .and_then(|_| file.write_all(b"\n"))
        .map_err(|source| PixelGraphPromotionError::Io {
            path: path.to_path_buf(),
            source,
        })
}

fn sha256_file(path: &Path) -> Result<String, PixelGraphPromotionError> {
    let mut file = File::open(path).map_err(|source| PixelGraphPromotionError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let mut digest = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = file
            .read(&mut buffer)
            .map_err(|source| PixelGraphPromotionError::Io {
                path: path.to_path_buf(),
                source,
            })?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn invariant(message: impl Into<String>) -> PixelGraphPromotionError {
    PixelGraphPromotionError::Invariant(message.into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dance_catalog_is_complete_and_named() {
        let specs = dance_specs();
        assert_eq!(specs.len(), 20);
        assert_eq!(specs[0].0, "dance_groove_step");
        assert_eq!(specs[19].0, "breakdance_finish");
        assert!(specs
            .iter()
            .all(|spec| !spec.1.is_empty() && !spec.4.is_empty()));
    }
}
