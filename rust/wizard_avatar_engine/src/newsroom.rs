use crate::capability_manifest::wizard_capability_document;
use crate::motion_catalog::shadow_motion_catalog;
use crate::pose_graph_runtime::{project_runtime_pose_graph, resolved_runtime_pose_id};
use crate::state::WizardState;
use base64::engine::general_purpose::STANDARD as BASE64_STANDARD;
use base64::Engine;
use serde::de::{self, Visitor};
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::sync::OnceLock;

pub const NEWSROOM_CUE_SCHEMA_VERSION: &str = "newsroom_wizard_v1";
pub const NEWSROOM_POLICY_SCHEMA_VERSION: u16 = 1;
pub const ACTOR_RENDER_SAMPLE_SCHEMA_VERSION: &str = "wizardjoe.actor-render-sample.v1";
pub const SPEECH_TIMELINE_SCHEMA_VERSION: &str = "wizardjoe.speech-timeline.v1";
pub const NEWSROOM_POSE_COUNT: usize = 88;
pub const NEWSROOM_TRANSITION_COUNT: usize = 30;
pub const NEWSROOM_SECTION_COUNT: usize = 11;
pub const MAX_NEWSROOM_CUE_DURATION_MS: u32 = 30_000;
pub const NEWSROOM_POSE_CATALOG_JSON: &str =
    include_str!("../assets/newsroom/catalogs/pose-catalog.json");
pub const NEWSROOM_TRANSITION_MATRIX_JSON: &str =
    include_str!("../assets/newsroom/catalogs/transition-matrix.json");

#[derive(Clone, Copy, Debug, Default, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct UnitInterval(u16);

impl UnitInterval {
    pub const ZERO: Self = Self(0);
    pub const ONE: Self = Self(1_000);

    pub const fn from_permille(value: u16) -> Option<Self> {
        if value <= 1_000 {
            Some(Self(value))
        } else {
            None
        }
    }

    pub const fn permille(self) -> u16 {
        self.0
    }

    pub const fn min(self, other: Self) -> Self {
        if self.0 <= other.0 {
            self
        } else {
            other
        }
    }
}

impl Serialize for UnitInterval {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_f64(f64::from(self.0) / 1_000.0)
    }
}

impl<'de> Deserialize<'de> for UnitInterval {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        struct UnitIntervalVisitor;

        impl<'de> Visitor<'de> for UnitIntervalVisitor {
            type Value = UnitInterval;

            fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
                formatter.write_str("a finite number in 0..=1")
            }

            fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
            where
                E: de::Error,
            {
                match value {
                    0 => Ok(UnitInterval::ZERO),
                    1 => Ok(UnitInterval::ONE),
                    _ => Err(E::custom("unit interval must be in 0..=1")),
                }
            }

            fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E>
            where
                E: de::Error,
            {
                if value < 0 {
                    return Err(E::custom("unit interval must be in 0..=1"));
                }
                self.visit_u64(value as u64)
            }

            fn visit_f64<E>(self, value: f64) -> Result<Self::Value, E>
            where
                E: de::Error,
            {
                if !value.is_finite() || !(0.0..=1.0).contains(&value) {
                    return Err(E::custom("unit interval must be finite and in 0..=1"));
                }
                Ok(UnitInterval((value * 1_000.0).round() as u16))
            }
        }

        deserializer.deserialize_any(UnitIntervalVisitor)
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NewsProgram {
    GeneralNews,
    AiInnovation,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NewsCommand {
    Anchor,
    Break,
    Clarify,
    Compare,
    Correct,
    Count,
    Emphasize,
    Explain,
    Handoff,
    Listen,
    Nod,
    Point,
    React,
    RevealGraphic,
    RevealSource,
    SignOff,
    Think,
    Warn,
    Welcome,
}

impl NewsCommand {
    pub const ALL: [Self; 19] = [
        Self::Anchor,
        Self::Break,
        Self::Clarify,
        Self::Compare,
        Self::Correct,
        Self::Count,
        Self::Emphasize,
        Self::Explain,
        Self::Handoff,
        Self::Listen,
        Self::Nod,
        Self::Point,
        Self::React,
        Self::RevealGraphic,
        Self::RevealSource,
        Self::SignOff,
        Self::Think,
        Self::Warn,
        Self::Welcome,
    ];

    pub const fn wire_name(self) -> &'static str {
        match self {
            Self::Anchor => "anchor",
            Self::Break => "break",
            Self::Clarify => "clarify",
            Self::Compare => "compare",
            Self::Correct => "correct",
            Self::Count => "count",
            Self::Emphasize => "emphasize",
            Self::Explain => "explain",
            Self::Handoff => "handoff",
            Self::Listen => "listen",
            Self::Nod => "nod",
            Self::Point => "point",
            Self::React => "react",
            Self::RevealGraphic => "reveal_graphic",
            Self::RevealSource => "reveal_source",
            Self::SignOff => "sign_off",
            Self::Think => "think",
            Self::Warn => "warn",
            Self::Welcome => "welcome",
        }
    }

    pub fn from_wire_name(value: &str) -> Option<Self> {
        Self::ALL
            .into_iter()
            .find(|command| command.wire_name() == value)
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StorySensitivity {
    Light,
    Normal,
    Serious,
    Critical,
    Correction,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsPerformanceCueV1 {
    pub schema_version: String,
    pub cue_id: String,
    pub sequence: u64,
    pub program: NewsProgram,
    pub command: NewsCommand,
    #[serde(default)]
    pub target: Option<String>,
    #[serde(default)]
    pub count: Option<u8>,
    pub intensity: UnitInterval,
    pub sensitivity: StorySensitivity,
    pub start_ms: u64,
    pub duration_ms: u32,
    pub generation: u64,
    pub reduced_motion: bool,
    #[serde(default)]
    pub speech_line_id: Option<String>,
    #[serde(default)]
    pub graphic_id: Option<String>,
    #[serde(default)]
    pub source_id: Option<String>,
    #[serde(default)]
    pub seed: Option<u64>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum ImplementationWorkItemStatusV1 {
    #[serde(rename = "PLANNED_NOT_STARTED")]
    PlannedNotStarted,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ImplementationWorkItemV1 {
    pub work_item_id: String,
    pub phase: u8,
    pub lane: String,
    pub title: String,
    pub dependencies: Vec<String>,
    pub files: Vec<String>,
    pub acceptance: String,
    pub human_approval_required: bool,
    pub status: ImplementationWorkItemStatusV1,
}

#[derive(Clone, Debug, Eq, PartialEq, thiserror::Error)]
pub enum NewsroomError {
    #[error("unsupported newsroom cue schema {0}")]
    UnsupportedCueSchema(String),
    #[error("{field} is not a valid bounded ASCII identifier")]
    InvalidIdentifier { field: &'static str },
    #[error("sequence and generation must be positive")]
    InvalidSequenceOrGeneration,
    #[error("duration_ms exceeds {MAX_NEWSROOM_CUE_DURATION_MS}")]
    InvalidDuration,
    #[error("count is required only for count and must be in 1..=3")]
    InvalidCount,
    #[error("graphic_id is required only for reveal_graphic")]
    InvalidGraphic,
    #[error("source_id is required only for reveal_source")]
    InvalidSource,
    #[error("unsupported newsroom policy")]
    InvalidPolicy,
    #[error("invalid implementation work item: {0}")]
    InvalidWorkItem(String),
    #[error("invalid newsroom catalog: {0}")]
    InvalidCatalog(String),
    #[error("semantic pose {0} is absent from the locked catalog")]
    UnknownSemanticPose(String),
    #[error("cannot sample actor pose: {0}")]
    ActorSample(String),
    #[error("actor sample capacity is currently exhausted")]
    ActorSampleBusy,
    #[error("invalid actor sample: {0}")]
    InvalidActorSample(String),
    #[error("invalid speech timeline: {0}")]
    InvalidSpeechTimeline(String),
    #[error(
        "stale newsroom cue generation/sequence {incoming_generation}/{incoming_sequence}; current is {current_generation}/{current_sequence}"
    )]
    StaleCue {
        incoming_generation: u64,
        incoming_sequence: u64,
        current_generation: u64,
        current_sequence: u64,
    },
    #[error("newsroom cue sequence was replayed with different content")]
    SequenceConflict,
    #[error("semantic cue resolved to unavailable authored pose {0}")]
    UnsupportedInternalPose(String),
}

impl NewsPerformanceCueV1 {
    pub fn validate(&self) -> Result<(), NewsroomError> {
        if self.schema_version != NEWSROOM_CUE_SCHEMA_VERSION {
            return Err(NewsroomError::UnsupportedCueSchema(
                self.schema_version.clone(),
            ));
        }
        for (field, value) in [
            ("cue_id", Some(self.cue_id.as_str())),
            ("target", self.target.as_deref()),
            ("speech_line_id", self.speech_line_id.as_deref()),
            ("graphic_id", self.graphic_id.as_deref()),
            ("source_id", self.source_id.as_deref()),
        ] {
            if value.is_some_and(|value| !valid_identifier(value)) {
                return Err(NewsroomError::InvalidIdentifier { field });
            }
        }
        if self.sequence == 0 || self.generation == 0 {
            return Err(NewsroomError::InvalidSequenceOrGeneration);
        }
        if self.duration_ms > MAX_NEWSROOM_CUE_DURATION_MS {
            return Err(NewsroomError::InvalidDuration);
        }
        let count_is_valid = match self.command {
            NewsCommand::Count => matches!(self.count, Some(1..=3)),
            _ => self.count.is_none(),
        };
        if !count_is_valid {
            return Err(NewsroomError::InvalidCount);
        }
        if (self.command == NewsCommand::RevealGraphic) != self.graphic_id.is_some() {
            return Err(NewsroomError::InvalidGraphic);
        }
        if (self.command == NewsCommand::RevealSource) != self.source_id.is_some() {
            return Err(NewsroomError::InvalidSource);
        }
        Ok(())
    }
}

impl ImplementationWorkItemV1 {
    pub fn validate(&self) -> Result<(), NewsroomError> {
        if !valid_work_item_id(&self.work_item_id)
            || self.phase > 9
            || self.lane.is_empty()
            || self.title.chars().count() < 10
            || self.dependencies.iter().any(|id| !valid_work_item_id(id))
            || self.files.is_empty()
            || self.files.iter().any(String::is_empty)
            || self.acceptance.chars().count() < 20
        {
            return Err(NewsroomError::InvalidWorkItem(self.work_item_id.clone()));
        }
        Ok(())
    }
}

fn valid_work_item_id(value: &str) -> bool {
    value.len() == 6
        && value.starts_with("WJ-")
        && value[3..].bytes().all(|byte| byte.is_ascii_digit())
}

fn valid_identifier(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 96
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b':' | b'-'))
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SensitivityCapsV1 {
    pub light: UnitInterval,
    pub normal: UnitInterval,
    pub serious: UnitInterval,
    pub critical: UnitInterval,
    pub correction: UnitInterval,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ForbiddenPairV1 {
    pub scene: String,
    pub family: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ReducedMotionPolicyV1 {
    pub suppress_root_motion: bool,
    pub suppress_repeated_secondary_motion: bool,
    pub maximum_transition_ms: u16,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomMotionPolicyV1 {
    pub schema_version: u16,
    pub policy_id: String,
    pub sensitivity_caps: SensitivityCapsV1,
    pub forbidden_pairs: Vec<ForbiddenPairV1>,
    pub reduced_motion: ReducedMotionPolicyV1,
    pub raw_control_allowed: bool,
}

impl Default for NewsroomMotionPolicyV1 {
    fn default() -> Self {
        Self {
            schema_version: NEWSROOM_POLICY_SCHEMA_VERSION,
            policy_id: NEWSROOM_CUE_SCHEMA_VERSION.to_string(),
            sensitivity_caps: SensitivityCapsV1 {
                light: UnitInterval(550),
                normal: UnitInterval(400),
                serious: UnitInterval(250),
                critical: UnitInterval(150),
                correction: UnitInterval(150),
            },
            forbidden_pairs: vec![
                ForbiddenPairV1 {
                    scene: "critical".to_string(),
                    family: "zany".to_string(),
                },
                ForbiddenPairV1 {
                    scene: "correction".to_string(),
                    family: "magic".to_string(),
                },
            ],
            reduced_motion: ReducedMotionPolicyV1 {
                suppress_root_motion: true,
                suppress_repeated_secondary_motion: true,
                maximum_transition_ms: 160,
            },
            raw_control_allowed: false,
        }
    }
}

impl NewsroomMotionPolicyV1 {
    pub fn validate(&self) -> Result<(), NewsroomError> {
        if self.schema_version != NEWSROOM_POLICY_SCHEMA_VERSION
            || self.policy_id != NEWSROOM_CUE_SCHEMA_VERSION
            || self.raw_control_allowed
            || self.reduced_motion.maximum_transition_ms > 500
        {
            return Err(NewsroomError::InvalidPolicy);
        }
        Ok(())
    }

    pub const fn cap_for(&self, sensitivity: StorySensitivity) -> UnitInterval {
        match sensitivity {
            StorySensitivity::Light => self.sensitivity_caps.light,
            StorySensitivity::Normal => self.sensitivity_caps.normal,
            StorySensitivity::Serious => self.sensitivity_caps.serious,
            StorySensitivity::Critical => self.sensitivity_caps.critical,
            StorySensitivity::Correction => self.sensitivity_caps.correction,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PoseClassification {
    ApproximateExisting,
    ChannelComposition,
    Deferred,
    ExactExisting,
    NewClip,
    NewGeometry,
    NewGeometryAndClip,
    PolicyOnly,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PoseSectionV1 {
    pub number: u8,
    pub name: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomPoseDefinitionV1 {
    pub ordinal: u8,
    pub pose_id: String,
    pub display_name: String,
    pub section: PoseSectionV1,
    pub family: String,
    pub semantic_intent: String,
    pub newsroom_purpose: String,
    pub python_classification: PoseClassification,
    pub python_current_equivalent: String,
    pub rust_classification: PoseClassification,
    pub rust_current_equivalent: String,
    pub joe_semantic_cue: String,
    pub geometry_requirement: String,
    pub clip_requirement: String,
    pub silhouette: String,
    pub root_anchor: String,
    pub contact_mode: String,
    pub planted_foot: String,
    pub staff_contact: String,
    pub head_direction: String,
    pub gaze_target: String,
    pub expression: String,
    pub mouth_compatibility: String,
    pub staff_mode: String,
    pub wing_mode: String,
    pub robe_behavior: String,
    pub hat_behavior: String,
    pub beard_behavior: String,
    pub effect_behavior: String,
    pub allowed_scenes: Vec<String>,
    pub disallowed_scenes: Vec<String>,
    pub story_sensitivity_limit: String,
    pub emotional_amplitude: UnitInterval,
    pub recommended_duration: String,
    pub entry_transitions: Vec<String>,
    pub exit_transitions: Vec<String>,
    pub interruption: String,
    pub restoration: String,
    pub desktop_safe_bounds: String,
    pub mobile_safe_bounds: String,
    pub closeup_compatibility: String,
    pub reduced_motion_fallback: String,
    pub python_files_likely_affected: Vec<String>,
    pub rust_files_likely_affected: Vec<String>,
    pub joe_files_likely_affected: Vec<String>,
    pub unit_tests: Vec<String>,
    pub integration_tests: Vec<String>,
    pub visual_tests: Vec<String>,
    pub runtime_tests: Vec<String>,
    pub evidence: Vec<String>,
    pub dependencies: Vec<String>,
    pub risks: Vec<String>,
    pub acceptance_state: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomPoseCatalogV1 {
    pub schema_version: String,
    pub generated_at: String,
    pub authority: String,
    pub poses: Vec<NewsroomPoseDefinitionV1>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomTransitionDefinitionV1 {
    pub transition_id: String,
    pub source_family: String,
    pub target_family: String,
    pub legal_source_poses: Vec<String>,
    pub legal_target_poses: Vec<String>,
    pub minimum_duration_ms: u32,
    pub maximum_duration_ms: u32,
    pub root_rule: String,
    pub contact_rule: String,
    pub staff_rule: String,
    pub wing_rule: String,
    pub mouth_rule: String,
    pub gaze_rule: String,
    pub expression_rule: String,
    pub effect_rule: String,
    pub interrupt_points: Vec<String>,
    pub restoration: String,
    pub python_strategy: String,
    pub rust_strategy: String,
    pub joe_timing_relationship: String,
    pub reduced_motion_fallback: String,
    pub structural_failure_conditions: Vec<String>,
    pub tests: Vec<String>,
    pub evidence: Vec<String>,
    pub acceptance_state: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomTransitionMatrixV1 {
    pub schema_version: String,
    pub generated_at: String,
    pub transitions: Vec<NewsroomTransitionDefinitionV1>,
}

#[derive(Clone, Debug)]
pub struct NewsroomCatalogs {
    pub poses: NewsroomPoseCatalogV1,
    pub transitions: NewsroomTransitionMatrixV1,
    pose_index: BTreeMap<String, usize>,
    transition_index: BTreeMap<String, usize>,
}

static EMBEDDED_NEWSROOM_CATALOGS: OnceLock<Result<NewsroomCatalogs, NewsroomError>> =
    OnceLock::new();
static CHARACTER_PACKAGE_SHA256: OnceLock<Result<String, NewsroomError>> = OnceLock::new();

pub fn embedded_newsroom_catalogs() -> Result<&'static NewsroomCatalogs, NewsroomError> {
    EMBEDDED_NEWSROOM_CATALOGS
        .get_or_init(NewsroomCatalogs::embedded)
        .as_ref()
        .map_err(Clone::clone)
}

fn character_package_sha256() -> Result<&'static str, NewsroomError> {
    match CHARACTER_PACKAGE_SHA256.get_or_init(|| {
        wizard_capability_document()
            .map(|document| document.manifest.runtime_geometry_authority_sha256.clone())
            .map_err(NewsroomError::ActorSample)
    }) {
        Ok(hash) => Ok(hash),
        Err(error) => Err(error.clone()),
    }
}

impl NewsroomCatalogs {
    pub fn embedded() -> Result<Self, NewsroomError> {
        let poses: NewsroomPoseCatalogV1 = serde_json::from_str(NEWSROOM_POSE_CATALOG_JSON)
            .map_err(|error| NewsroomError::InvalidCatalog(error.to_string()))?;
        let transitions: NewsroomTransitionMatrixV1 =
            serde_json::from_str(NEWSROOM_TRANSITION_MATRIX_JSON)
                .map_err(|error| NewsroomError::InvalidCatalog(error.to_string()))?;
        let catalogs = Self::new(poses, transitions)?;
        catalogs.validate_motion_graph()?;
        Ok(catalogs)
    }

    pub fn new(
        poses: NewsroomPoseCatalogV1,
        transitions: NewsroomTransitionMatrixV1,
    ) -> Result<Self, NewsroomError> {
        if poses.schema_version != "wizardjoe.pose-catalog.v1"
            || transitions.schema_version != "wizardjoe.transition-matrix.v1"
            || poses.poses.len() != NEWSROOM_POSE_COUNT
            || transitions.transitions.len() != NEWSROOM_TRANSITION_COUNT
        {
            return Err(NewsroomError::InvalidCatalog(
                "schema versions or exact catalog counts do not match v1".to_string(),
            ));
        }

        let mut pose_index = BTreeMap::new();
        let mut sections = BTreeSet::new();
        for (index, pose) in poses.poses.iter().enumerate() {
            if pose.ordinal as usize != index + 1
                || !valid_identifier(&pose.pose_id)
                || NewsCommand::from_wire_name(&pose.semantic_intent).is_none()
                || pose.joe_semantic_cue != pose.semantic_intent
                || pose.allowed_scenes.is_empty()
                || pose.disallowed_scenes.is_empty()
                || pose.evidence.is_empty()
            {
                return Err(NewsroomError::InvalidCatalog(format!(
                    "pose {} violates its locked identity or required fields",
                    pose.pose_id
                )));
            }
            if pose_index.insert(pose.pose_id.clone(), index).is_some() {
                return Err(NewsroomError::InvalidCatalog(format!(
                    "duplicate pose {}",
                    pose.pose_id
                )));
            }
            sections.insert(pose.section.number);
        }
        if sections.len() != NEWSROOM_SECTION_COUNT
            || sections
                .iter()
                .copied()
                .ne(1..=NEWSROOM_SECTION_COUNT as u8)
        {
            return Err(NewsroomError::InvalidCatalog(
                "pose sections must be exactly 1 through 11".to_string(),
            ));
        }

        let mut transition_index = BTreeMap::new();
        for (index, transition) in transitions.transitions.iter().enumerate() {
            if transition.minimum_duration_ms > transition.maximum_duration_ms
                || transition.legal_source_poses.is_empty()
                || transition.legal_target_poses.is_empty()
                || transition.interrupt_points.is_empty()
                || transition.evidence.is_empty()
            {
                return Err(NewsroomError::InvalidCatalog(format!(
                    "transition {} violates required bounds",
                    transition.transition_id
                )));
            }
            for pose_id in transition
                .legal_source_poses
                .iter()
                .chain(&transition.legal_target_poses)
            {
                if !pose_index.contains_key(pose_id) {
                    return Err(NewsroomError::InvalidCatalog(format!(
                        "transition {} references unknown pose {pose_id}",
                        transition.transition_id
                    )));
                }
            }
            if transition_index
                .insert(transition.transition_id.clone(), index)
                .is_some()
            {
                return Err(NewsroomError::InvalidCatalog(format!(
                    "duplicate transition {}",
                    transition.transition_id
                )));
            }
        }
        for pose in &poses.poses {
            for transition_id in pose.entry_transitions.iter().chain(&pose.exit_transitions) {
                let resolved_transition_id =
                    newsroom_transition_alias(transition_id).unwrap_or(transition_id.as_str());
                if !transition_index.contains_key(resolved_transition_id) {
                    return Err(NewsroomError::InvalidCatalog(format!(
                        "pose {} references unknown transition {transition_id}",
                        pose.pose_id
                    )));
                }
            }
        }

        Ok(Self {
            poses,
            transitions,
            pose_index,
            transition_index,
        })
    }

    pub fn pose(&self, pose_id: &str) -> Option<&NewsroomPoseDefinitionV1> {
        self.pose_index
            .get(pose_id)
            .map(|index| &self.poses.poses[*index])
    }

    pub fn transition(&self, transition_id: &str) -> Option<&NewsroomTransitionDefinitionV1> {
        let transition_id = newsroom_transition_alias(transition_id).unwrap_or(transition_id);
        self.transition_index
            .get(transition_id)
            .map(|index| &self.transitions.transitions[*index])
    }

    pub fn validate_motion_graph(&self) -> Result<(), NewsroomError> {
        let graph = &shadow_motion_catalog()
            .map_err(NewsroomError::InvalidCatalog)?
            .graph;
        let recipe_ids = graph
            .transition_recipes
            .iter()
            .map(|recipe| recipe.recipe_id.as_str())
            .collect::<BTreeSet<_>>();
        for transition in &self.transitions.transitions {
            let recipe_id = motion_recipe_for_transition(transition)?;
            if !recipe_ids.contains(recipe_id) {
                return Err(NewsroomError::InvalidCatalog(format!(
                    "transition {} references missing MotionGraphV1 recipe {recipe_id}",
                    transition.transition_id
                )));
            }
        }
        Ok(())
    }
}

// The planning packet's pose catalog uses 23 semantic edge names that are not
// present in its locked 30-edge matrix. Keep both artifacts byte-exact and map
// those names onto the matrix's authored recipes at the Rust ingestion boundary.
fn newsroom_transition_alias(transition_id: &str) -> Option<&'static str> {
    match transition_id {
        "tr_break_to_home" => Some("tr_breaking_to_composed"),
        "tr_clarify_to_home" | "tr_compare_to_home" | "tr_count_to_home" | "tr_home_to_react"
        | "tr_home_to_think" | "tr_react_to_home" | "tr_think_to_home" => {
            Some("tr_semantic_settle")
        }
        "tr_closeup_to_home" => Some("tr_closeup_to_body"),
        "tr_correct_to_home" => Some("tr_correction_restore"),
        "tr_handoff_to_home" | "tr_nod_to_home" => Some("tr_listen_to_home"),
        "tr_home_to_break" => Some("tr_any_to_breaking"),
        "tr_home_to_closeup" => Some("tr_body_to_closeup"),
        "tr_home_to_correct" => Some("tr_any_to_correction"),
        "tr_home_to_handoff" => Some("tr_listen_to_handoff"),
        "tr_home_to_nod" => Some("tr_home_to_listen"),
        "tr_home_to_reveal_graphic" => Some("tr_home_to_magic"),
        "tr_home_to_reveal_source" => Some("tr_home_to_point"),
        "tr_home_to_warn" => Some("tr_interrupt_to_breaking"),
        "tr_reveal_graphic_to_home" => Some("tr_magic_to_home"),
        "tr_reveal_source_to_home" => Some("tr_point_to_home"),
        "tr_warn_to_home" => Some("tr_breaking_to_composed"),
        _ => None,
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NewsroomLifecycleState {
    Scheduled,
    Applied,
    Interrupted,
    Restoring,
    Completed,
    Rejected,
    Degraded,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimeBindingFidelityV1 {
    Exact,
    Composed,
    ApprovedComposition,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomPoseRuntimeBindingV1 {
    pub semantic_pose_id: String,
    pub internal_pose_id: String,
    pub fidelity: RuntimeBindingFidelityV1,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ResolvedNewsroomPerformanceV1 {
    pub cue_id: String,
    pub sequence: u64,
    pub generation: u64,
    pub semantic_pose_id: String,
    pub internal_pose_id: String,
    pub binding_fidelity: RuntimeBindingFidelityV1,
    pub transition_id: String,
    pub motion_recipe_id: String,
    pub applied_intensity: UnitInterval,
    pub transition_ms: u16,
    pub lifecycle: NewsroomLifecycleState,
    pub reduced_motion: bool,
    pub policy_clamps: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomCueReceiptV1 {
    pub cue_id: String,
    pub sequence: u64,
    pub generation: u64,
    pub accepted_tick: u64,
    pub duplicate: bool,
    #[serde(default)]
    pub interrupted_cue_id: Option<String>,
    pub performance: ResolvedNewsroomPerformanceV1,
}

pub fn resolve_newsroom_cue(
    cue: &NewsPerformanceCueV1,
    policy: &NewsroomMotionPolicyV1,
    catalogs: &NewsroomCatalogs,
) -> Result<ResolvedNewsroomPerformanceV1, NewsroomError> {
    cue.validate()?;
    policy.validate()?;
    let cap = policy.cap_for(cue.sensitivity);
    let applied_intensity = cue.intensity.min(cap);
    let mut policy_clamps = Vec::new();
    if applied_intensity != cue.intensity {
        policy_clamps.push("sensitivity_amplitude_cap".to_string());
    }
    if cue.reduced_motion {
        policy_clamps.push("reduced_motion".to_string());
    }

    let pose = semantic_pose_for(cue, applied_intensity, catalogs)?;
    let (transition, used_compatibility_fallback) = legal_entry_transition(catalogs, pose)?;
    if used_compatibility_fallback {
        policy_clamps.push("transition_compatibility_fallback".to_string());
    }
    let motion_recipe_id = if cue.reduced_motion {
        "reduced_motion_handoff"
    } else {
        motion_recipe_for_transition(transition)?
    };
    let transition_ms = if cue.reduced_motion {
        u32::from(policy.reduced_motion.maximum_transition_ms).min(transition.maximum_duration_ms)
    } else {
        transition.minimum_duration_ms.max(120)
    }
    .min(u32::from(u16::MAX)) as u16;

    let binding = runtime_binding_for_pose(pose)?;
    Ok(ResolvedNewsroomPerformanceV1 {
        cue_id: cue.cue_id.clone(),
        sequence: cue.sequence,
        generation: cue.generation,
        semantic_pose_id: pose.pose_id.clone(),
        internal_pose_id: binding.internal_pose_id,
        binding_fidelity: binding.fidelity,
        transition_id: transition.transition_id.clone(),
        motion_recipe_id: motion_recipe_id.to_string(),
        applied_intensity,
        transition_ms,
        lifecycle: NewsroomLifecycleState::Scheduled,
        reduced_motion: cue.reduced_motion,
        policy_clamps,
    })
}

fn legal_entry_transition<'a>(
    catalogs: &'a NewsroomCatalogs,
    pose: &NewsroomPoseDefinitionV1,
) -> Result<(&'a NewsroomTransitionDefinitionV1, bool), NewsroomError> {
    if let Some(transition) = pose
        .entry_transitions
        .iter()
        .filter_map(|transition_id| catalogs.transition(transition_id))
        .find(|transition| transition.legal_target_poses.contains(&pose.pose_id))
    {
        return Ok((transition, false));
    }
    catalogs
        .transitions
        .transitions
        .iter()
        .find(|transition| transition.legal_target_poses.contains(&pose.pose_id))
        .map(|transition| (transition, true))
        .ok_or_else(|| {
            NewsroomError::InvalidCatalog(format!(
                "no canonical transition can target pose {}",
                pose.pose_id
            ))
        })
}

fn motion_recipe_for_transition(
    transition: &NewsroomTransitionDefinitionV1,
) -> Result<&str, NewsroomError> {
    transition
        .rust_strategy
        .strip_prefix("map to MotionGraphV1 recipe ")
        .and_then(|strategy| strategy.split_whitespace().next())
        .filter(|recipe_id| !recipe_id.is_empty())
        .ok_or_else(|| {
            NewsroomError::InvalidCatalog(format!(
                "transition {} has an invalid Rust motion strategy",
                transition.transition_id
            ))
        })
}

fn semantic_pose_for<'a>(
    cue: &NewsPerformanceCueV1,
    intensity: UnitInterval,
    catalogs: &'a NewsroomCatalogs,
) -> Result<&'a NewsroomPoseDefinitionV1, NewsroomError> {
    if cue.command == NewsCommand::Count {
        let pose_id = match cue.count.unwrap_or(1) {
            1 => "count_one",
            2 => "count_two",
            _ => "count_three",
        };
        return catalogs
            .pose(pose_id)
            .ok_or_else(|| NewsroomError::UnknownSemanticPose(pose_id.to_string()));
    }

    if let Some(seed) = cue.seed {
        let candidate_count = catalogs
            .poses
            .poses
            .iter()
            .filter(|pose| pose_is_eligible_variant(pose, cue))
            .count();
        if candidate_count == 0 {
            return Err(NewsroomError::UnknownSemanticPose(
                cue.command.wire_name().to_string(),
            ));
        }
        let selected_index = (seed % candidate_count as u64) as usize;
        return catalogs
            .poses
            .poses
            .iter()
            .filter(|pose| pose_is_eligible_variant(pose, cue))
            .nth(selected_index)
            .ok_or_else(|| {
                NewsroomError::UnknownSemanticPose(cue.command.wire_name().to_string())
            });
    }

    let pose_id = default_semantic_pose(cue, intensity);
    catalogs
        .pose(pose_id)
        .ok_or_else(|| NewsroomError::UnknownSemanticPose(pose_id.to_string()))
}

fn pose_is_eligible_variant(pose: &NewsroomPoseDefinitionV1, cue: &NewsPerformanceCueV1) -> bool {
    pose.semantic_intent == cue.command.wire_name()
        && (!matches!(
            cue.sensitivity,
            StorySensitivity::Serious | StorySensitivity::Critical | StorySensitivity::Correction
        ) || !pose.story_sensitivity_limit.starts_with("light/"))
}

fn default_semantic_pose(cue: &NewsPerformanceCueV1, intensity: UnitInterval) -> &'static str {
    match cue.command {
        NewsCommand::Anchor => "anchor_neutral_front",
        NewsCommand::Break => {
            if matches!(
                cue.sensitivity,
                StorySensitivity::Critical | StorySensitivity::Correction
            ) {
                "breaking_composed"
            } else {
                "breaking_alert_initial"
            }
        }
        NewsCommand::Clarify => "clarify_uncertainty",
        NewsCommand::Compare => "compare_left_right",
        NewsCommand::Correct => "correction_sober",
        NewsCommand::Count => "count_one",
        NewsCommand::Emphasize if intensity.permille() > 450 => "emphasis_large",
        NewsCommand::Emphasize => "emphasis_small",
        NewsCommand::Explain => "explain_one_hand",
        NewsCommand::Handoff => "handoff_receive",
        NewsCommand::Listen => "listen_camera",
        NewsCommand::Nod => "nod_single",
        NewsCommand::Point => "point_source_card",
        NewsCommand::React if cue.sensitivity == StorySensitivity::Light => "amused_light",
        NewsCommand::React => "surprised_bounded",
        NewsCommand::RevealGraphic => {
            if matches!(
                cue.sensitivity,
                StorySensitivity::Serious
                    | StorySensitivity::Critical
                    | StorySensitivity::Correction
            ) {
                "trace_timeline"
            } else {
                "magic_reveal_headline"
            }
        }
        NewsCommand::RevealSource => "source_emphasis",
        NewsCommand::SignOff => "exit_stage",
        NewsCommand::Think => "think_hand_chin",
        NewsCommand::Warn => "urgent_warning",
        NewsCommand::Welcome => "enter_from_left",
    }
}

pub fn runtime_binding_for_pose(
    pose: &NewsroomPoseDefinitionV1,
) -> Result<NewsroomPoseRuntimeBindingV1, NewsroomError> {
    let internal_pose_id = runtime_pose_for_semantic(&pose.pose_id)
        .ok_or_else(|| NewsroomError::UnknownSemanticPose(pose.pose_id.clone()))?;
    let fidelity = match pose.rust_classification {
        PoseClassification::ExactExisting => RuntimeBindingFidelityV1::Exact,
        PoseClassification::NewGeometry | PoseClassification::NewGeometryAndClip => {
            RuntimeBindingFidelityV1::ApprovedComposition
        }
        PoseClassification::ApproximateExisting
        | PoseClassification::ChannelComposition
        | PoseClassification::NewClip => RuntimeBindingFidelityV1::Composed,
        PoseClassification::Deferred | PoseClassification::PolicyOnly => {
            RuntimeBindingFidelityV1::ApprovedComposition
        }
    };
    Ok(NewsroomPoseRuntimeBindingV1 {
        semantic_pose_id: pose.pose_id.clone(),
        internal_pose_id: internal_pose_id.to_string(),
        fidelity,
    })
}

fn runtime_pose_for_semantic(semantic_pose: &str) -> Option<&'static str> {
    Some(match semantic_pose {
        "anchor_neutral_front"
        | "anchor_neutral_three_quarter_left"
        | "anchor_neutral_three_quarter_right"
        | "anchor_hands_composed"
        | "anchor_confident"
        | "anchor_soft_smile"
        | "conclusion_resolve"
        | "listen_camera"
        | "listen_cohost_left"
        | "listen_cohost_right"
        | "nod_single"
        | "nod_agree"
        | "skeptical_head_tilt"
        | "handoff_receive"
        | "breaking_composed"
        | "developing_story"
        | "desk_seated_neutral"
        | "desk_seated_listening"
        | "desk_microphone_ready"
        | "turn_to_camera"
        | "wings_resting" => "idle_warm_camera_ready",
        "closeup_skeptical" => "emotion_skepticism",
        "anchor_open_ready" | "wings_welcome_open" => "hand_open_relaxed",
        "anchor_staff_planted" | "stand_from_desk" | "sit_at_desk" => "staff_plant",
        "explain_one_hand"
        | "explain_precise"
        | "emphasis_small"
        | "count_one"
        | "count_two"
        | "count_three"
        | "define_term"
        | "zoom_out_context"
        | "zoom_in_detail"
        | "desk_seated_speaking" => "speak_explain_precise",
        "explain_two_hands" | "compare_left_right" | "weighing_options" => "speak_explain_sequence",
        "emphasis_large" | "wings_emphasis" => "speak_emphasize_high",
        "clarify_uncertainty" | "think_hand_chin" | "fact_check_focus" | "desk_review_notes" => {
            "emotion_contemplative"
        }
        "curious" => "emotion_curious",
        "important_context" | "point_source_card" | "urgent_warning" | "source_emphasis" => {
            "hand_point_screen_right"
        }
        "point_headline_left"
        | "point_headline_right"
        | "point_chart_high"
        | "point_chart_low"
        | "point_city_window"
        | "trace_timeline"
        | "desk_seated_pointing"
        | "turn_to_graphic" => "hand_point_screen_left",
        "staff_point_graphic" => "staff_aim_forward",
        "breaking_alert_initial" | "teleport_puff_arrival" => "emotion_shock",
        "correction_sober" => "emotion_shame",
        "correction_apology" | "empathetic" => "emotion_compassion",
        "warm_good_news" => "emotion_joy",
        "amused_light" | "closeup_signoff" => "emotion_amused",
        "surprised_bounded" => "emotion_surprise",
        "concerned" => "emotion_concern",
        "confident_resolve" | "proud_bounded" => "emotion_confident",
        "enter_from_left" | "walk_to_anchor_mark" | "walk_to_explainer_wall" | "exit_stage" => {
            "walk_contact_right"
        }
        "enter_from_right" | "walk_to_correspondent_window" => "walk_contact_left",
        "orb_low_glow" | "orb_breaking_pulse" | "orb_correction_dim" | "magic_reveal_headline" => {
            "magic_cast_hold"
        }
        "conjure_chart" | "summon_source_scroll" => "magic_raise_staff",
        "staff_misfire_recover" => "magic_mishap_smoke_reveal",
        "wings_folded_serious" => "emotion_solemn",
        "closeup_warm" => "emotion_compassion",
        "closeup_concerned" => "emotion_concern",
        _ => return None,
    })
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ActorPointV1 {
    pub x: i32,
    pub y: i32,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ActorRectV1 {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ActorEngineV1 {
    Python,
    Rust,
    SafeFallback,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ActorRenderSampleV1 {
    pub schema_version: String,
    pub width: u16,
    pub height: u16,
    pub channels: u8,
    pub rgb_sha256: String,
    pub coverage_mask_sha256: String,
    #[serde(default)]
    pub shadow_mask_sha256: Option<String>,
    #[serde(default)]
    pub depth_sha256: Option<String>,
    pub bounds: ActorRectV1,
    pub root: ActorPointV1,
    pub contact_points: Vec<ActorPointV1>,
    #[serde(default)]
    pub staff_bounds: Option<ActorRectV1>,
    #[serde(default)]
    pub wing_bounds: Option<ActorRectV1>,
    pub semantic_pose: String,
    pub expression: String,
    pub mouth: String,
    pub engine: ActorEngineV1,
    pub engine_commit: String,
    pub character_package: String,
    pub simulation_tick: u64,
    pub generation: u64,
    pub state_hash: String,
    pub actor_layer_hash: String,
    pub diagnostics: BTreeMap<String, serde_json::Value>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ActorLayerBuffersV1 {
    pub rgb: Vec<u8>,
    pub coverage_mask: Vec<u8>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ActorRenderSampleEnvelopeV1 {
    pub metadata: ActorRenderSampleV1,
    pub rgb_base64: String,
    pub coverage_mask_base64: String,
}

impl ActorRenderSampleEnvelopeV1 {
    pub fn new(metadata: ActorRenderSampleV1, buffers: &ActorLayerBuffersV1) -> Self {
        Self {
            metadata,
            rgb_base64: BASE64_STANDARD.encode(&buffers.rgb),
            coverage_mask_base64: BASE64_STANDARD.encode(&buffers.coverage_mask),
        }
    }

    pub fn decode_and_validate(&self) -> Result<ActorLayerBuffersV1, NewsroomError> {
        let buffers = ActorLayerBuffersV1 {
            rgb: BASE64_STANDARD.decode(&self.rgb_base64).map_err(|error| {
                NewsroomError::InvalidActorSample(format!("invalid RGB base64: {error}"))
            })?,
            coverage_mask: BASE64_STANDARD
                .decode(&self.coverage_mask_base64)
                .map_err(|error| {
                    NewsroomError::InvalidActorSample(format!(
                        "invalid coverage-mask base64: {error}"
                    ))
                })?,
        };
        self.metadata.validate_with_buffers(&buffers)?;
        Ok(buffers)
    }
}

impl ActorRenderSampleV1 {
    pub fn validate_with_buffers(
        &self,
        buffers: &ActorLayerBuffersV1,
    ) -> Result<(), NewsroomError> {
        let pixels = usize::from(self.width) * usize::from(self.height);
        let bounds_are_valid = self.bounds.width > 0
            && self.bounds.height > 0
            && self.bounds.x >= 0
            && self.bounds.y >= 0
            && self.bounds.x + self.bounds.width as i32 <= i32::from(self.width)
            && self.bounds.y + self.bounds.height as i32 <= i32::from(self.height);
        let region_bounds_are_valid = [self.staff_bounds, self.wing_bounds]
            .into_iter()
            .flatten()
            .all(|bounds| {
                bounds.width > 0
                    && bounds.height > 0
                    && bounds.x >= 0
                    && bounds.y >= 0
                    && bounds.x + bounds.width as i32 <= i32::from(self.width)
                    && bounds.y + bounds.height as i32 <= i32::from(self.height)
            });
        // Anchors are edge coordinates, so the stage-floor root may equal a canvas dimension.
        let points_are_valid = std::iter::once(self.root)
            .chain(self.contact_points.iter().copied())
            .all(|point| {
                point.x >= 0
                    && point.y >= 0
                    && point.x <= i32::from(self.width)
                    && point.y <= i32::from(self.height)
            });
        let expected_layer_hash = actor_layer_hash(
            &self.rgb_sha256,
            &self.coverage_mask_sha256,
            &self.state_hash,
            &self.semantic_pose,
            self.generation,
            &self.character_package,
        );
        let mut failures = Vec::new();
        if self.schema_version != ACTOR_RENDER_SAMPLE_SCHEMA_VERSION {
            failures.push("schema_version");
        }
        if self.width == 0 || self.height == 0 {
            failures.push("dimensions");
        }
        if self.channels != 3 {
            failures.push("channels");
        }
        if self.generation == 0 {
            failures.push("generation");
        }
        if self.engine_commit.len() < 7 || self.semantic_pose.is_empty() {
            failures.push("identity");
        }
        if buffers.rgb.len() != pixels * 3 {
            failures.push("rgb_length");
        }
        if buffers.coverage_mask.len() != pixels {
            failures.push("coverage_mask_length");
        }
        if !buffers.coverage_mask.iter().all(|value| *value <= 1)
            || !buffers.coverage_mask.contains(&1)
        {
            failures.push("coverage_mask_values");
        }
        if self.rgb_sha256 != sha256_hex(&buffers.rgb) {
            failures.push("rgb_sha256");
        }
        if self.coverage_mask_sha256 != sha256_hex(&buffers.coverage_mask) {
            failures.push("coverage_mask_sha256");
        }
        if !valid_sha256(&self.state_hash) || !valid_sha256(&self.character_package) {
            failures.push("authority_hash");
        }
        if self.actor_layer_hash != expected_layer_hash {
            failures.push("actor_layer_hash");
        }
        if !bounds_are_valid {
            failures.push("bounds");
        }
        if !region_bounds_are_valid {
            failures.push("region_bounds");
        }
        if !points_are_valid {
            failures.push("anchors");
        }
        if !failures.is_empty() {
            let anchor_details = if points_are_valid {
                String::new()
            } else {
                format!(
                    "; root={:?}, contacts={:?}, canvas={}x{}",
                    self.root, self.contact_points, self.width, self.height
                )
            };
            return Err(NewsroomError::InvalidActorSample(format!(
                "failed invariants: {}{anchor_details}",
                failures.join(", "),
            )));
        }
        Ok(())
    }
}

pub fn build_actor_render_sample(
    state: &WizardState,
    semantic_pose: &str,
    generation: u64,
    engine_commit: &str,
) -> Result<(ActorRenderSampleV1, ActorLayerBuffersV1), NewsroomError> {
    if generation == 0 || engine_commit.len() < 7 || !valid_identifier(semantic_pose) {
        return Err(NewsroomError::InvalidActorSample(
            "invalid generation, engine commit, or semantic pose".to_string(),
        ));
    }
    let runtime_pose_id = resolved_runtime_pose_id(state);
    let raster =
        project_runtime_pose_graph(&runtime_pose_id).map_err(NewsroomError::ActorSample)?;
    let width = raster.width;
    let height = raster.height;
    if width == 0 || height == 0 || width > 2_048 || height > 2_048 {
        return Err(NewsroomError::ActorSample(
            "actor dimensions are outside 1..=2048".to_string(),
        ));
    }

    let rgb = raster.rgb_white_background.clone();
    let coverage_mask = raster.coverage_mask.clone();
    let bounds = ActorRectV1 {
        x: i32::from(raster.foreground_bounds[0]),
        y: i32::from(raster.foreground_bounds[1]),
        width: u32::from(raster.foreground_bounds[2]),
        height: u32::from(raster.foreground_bounds[3]),
    };
    let root = ActorPointV1 {
        x: i32::try_from(raster.entry.anchor_x)
            .unwrap_or(i32::from(width))
            .clamp(0, i32::from(width)),
        y: i32::try_from(raster.entry.anchor_y)
            .unwrap_or(i32::from(height))
            .clamp(0, i32::from(height)),
    };
    let contact_points = if raster.entry.contact_mode == "airborne" {
        Vec::new()
    } else {
        vec![root]
    };
    let state_bytes =
        serde_json::to_vec(state).map_err(|error| NewsroomError::ActorSample(error.to_string()))?;
    let state_hash = sha256_hex(&state_bytes);
    let rgb_sha256 = raster.rgb_sha256.clone();
    let coverage_mask_sha256 = raster.coverage_mask_sha256.clone();
    let character_package = character_package_sha256()?.to_string();
    let actor_layer_hash = actor_layer_hash(
        &rgb_sha256,
        &coverage_mask_sha256,
        &state_hash,
        semantic_pose,
        generation,
        &character_package,
    );
    let expression = serde_json::to_value(state.expression)
        .ok()
        .and_then(|value| value.as_str().map(str::to_owned))
        .unwrap_or_else(|| "neutral".to_string());
    let mouth = serde_json::to_value(state.mouth)
        .ok()
        .and_then(|value| value.as_str().map(str::to_owned))
        .unwrap_or_else(|| "closed".to_string());
    let mut diagnostics = BTreeMap::new();
    diagnostics.insert(
        "source_pose_id".to_string(),
        raster.entry.semantic_id.clone().into(),
    );
    diagnostics.insert(
        "source_record_id".to_string(),
        raster.entry.source_record_id.clone().into(),
    );
    diagnostics.insert(
        "graph_sha256".to_string(),
        raster.entry.graph_sha256.clone().into(),
    );
    diagnostics.insert(
        "occupied_pixels".to_string(),
        raster.entry.foreground_pixel_count.into(),
    );
    diagnostics.insert(
        "pixel_format".to_string(),
        "rgb8_plus_binary_coverage_from_rgba_pixelgraph".into(),
    );
    diagnostics.insert(
        "coordinate_space".to_string(),
        "production_alpha_1254_pixelgraph".into(),
    );
    diagnostics.insert("origin".to_string(), "top_left".into());

    let buffers = ActorLayerBuffersV1 { rgb, coverage_mask };
    let metadata = ActorRenderSampleV1 {
        schema_version: ACTOR_RENDER_SAMPLE_SCHEMA_VERSION.to_string(),
        width,
        height,
        channels: 3,
        rgb_sha256,
        coverage_mask_sha256,
        shadow_mask_sha256: None,
        depth_sha256: None,
        bounds,
        root,
        contact_points,
        staff_bounds: None,
        wing_bounds: None,
        semantic_pose: semantic_pose.to_string(),
        expression,
        mouth,
        engine: ActorEngineV1::Rust,
        engine_commit: engine_commit.to_string(),
        character_package,
        simulation_tick: state.simulation_tick,
        generation,
        state_hash,
        actor_layer_hash,
        diagnostics,
    };
    metadata.validate_with_buffers(&buffers)?;
    Ok((metadata, buffers))
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SpeechTimingSourceV1 {
    ProviderViseme,
    ProviderPhoneme,
    Word,
    Amplitude,
    TextFallback,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SpeechMouthCueV1 {
    pub start_ms: u32,
    pub end_ms: u32,
    pub mouth: String,
    #[serde(default)]
    pub weight: Option<u8>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CaptionCueV1 {
    pub start_ms: u32,
    pub end_ms: u32,
    pub text: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SpeechTimelineV1 {
    pub schema_version: String,
    pub utterance_id: String,
    pub generation: u64,
    pub start_ms: u64,
    pub duration_ms: u32,
    pub timing_source: SpeechTimingSourceV1,
    pub cues: Vec<SpeechMouthCueV1>,
    pub caption_cues: Vec<CaptionCueV1>,
}

impl SpeechTimelineV1 {
    pub fn validate(&self) -> Result<(), NewsroomError> {
        if self.schema_version != SPEECH_TIMELINE_SCHEMA_VERSION
            || !valid_identifier(&self.utterance_id)
            || self.generation == 0
            || self.duration_ms == 0
        {
            return Err(NewsroomError::InvalidSpeechTimeline(
                "invalid schema, utterance, generation, or duration".to_string(),
            ));
        }
        validate_intervals(
            self.cues
                .iter()
                .map(|cue| (cue.start_ms, cue.end_ms, cue.weight.unwrap_or(100) <= 100)),
            self.duration_ms,
        )?;
        validate_intervals(
            self.caption_cues.iter().map(|cue| {
                (
                    cue.start_ms,
                    cue.end_ms,
                    !cue.text.is_empty() && cue.text.len() <= 500,
                )
            }),
            self.duration_ms,
        )?;
        Ok(())
    }

    pub fn mouth_at_ms(&self, elapsed_ms: u32) -> &str {
        self.cues
            .iter()
            .find(|cue| cue.start_ms <= elapsed_ms && elapsed_ms < cue.end_ms)
            .map_or("closed", |cue| cue.mouth.as_str())
    }
}

fn validate_intervals(
    intervals: impl IntoIterator<Item = (u32, u32, bool)>,
    duration_ms: u32,
) -> Result<(), NewsroomError> {
    let mut previous_end = 0;
    for (index, (start, end, content_valid)) in intervals.into_iter().enumerate() {
        if start >= end || end > duration_ms || start < previous_end || !content_valid {
            return Err(NewsroomError::InvalidSpeechTimeline(format!(
                "invalid or overlapping interval at index {index}"
            )));
        }
        previous_end = end;
    }
    Ok(())
}

fn sha256_hex(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn actor_layer_hash(
    rgb_sha256: &str,
    coverage_mask_sha256: &str,
    state_hash: &str,
    semantic_pose: &str,
    generation: u64,
    character_package: &str,
) -> String {
    sha256_hex(
        format!(
            "wizardjoe.actor-layer.v1\0{rgb_sha256}\0{coverage_mask_sha256}\0{state_hash}\0{semantic_pose}\0{generation}\0{character_package}"
        )
        .as_bytes(),
    )
}

fn valid_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}
