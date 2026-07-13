use crate::chat_event::{ChatTurnState, Emotion, MotionProfile};
use crate::chat_performance::RenderedMouthPose;
use crate::state::Direction;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;
use thiserror::Error;

pub const MOTION_GRAPH_SCHEMA_VERSION: u16 = 1;
pub const REQUIRED_ASSET_SCHEMA_VERSION: u16 = 4;
pub const REQUIRED_RUNTIME_GEOMETRY_COUNT: usize = 89;
pub const REQUIRED_WJFL_GEOMETRY_COUNT: usize = 50;
pub const REQUIRED_RECIPE_IDS: [&str; 8] = [
    "coherent_handoff",
    "contact_sync",
    "anticipation_action_recover",
    "airborne_arc",
    "brace_transfer",
    "face_coarticulation",
    "secondary_settle",
    "reduced_motion_handoff",
];

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MotionGraphV1 {
    pub schema_version: u16,
    pub graph_id: String,
    pub asset_schema_version: u16,
    pub required_runtime_geometry_count: usize,
    pub required_wjfl_geometry_count: usize,
    pub default_clip_id: String,
    pub pose_coverage: Vec<PoseCoverage>,
    pub clips: Vec<MotionClip>,
    pub transition_recipes: Vec<TransitionRecipe>,
    pub edges: Vec<MotionEdge>,
    pub turn_state_profiles: Vec<TurnStateProfile>,
    pub emotion_profiles: Vec<EmotionProfile>,
    pub variant_sets: Vec<VariantSet>,
    pub reduced_motion_overrides: Vec<ReducedMotionOverride>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub state_facing_fallbacks: Vec<StateFacingFallback>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PoseCoverage {
    pub pose_id: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source_candidate_id: Option<String>,
    pub use_kinds: Vec<PoseUseKind>,
    pub capability_tier: CapabilityTier,
    pub approved_facings: Vec<Direction>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub showcase_approval: Option<ShowcaseApproval>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ShowcaseApproval {
    pub owner: String,
    pub rationale: String,
    pub fallback_pose_id: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StateFacingFallback {
    pub turn_state: ChatTurnState,
    pub requested_facing: Direction,
    pub fallback_pose_id: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RuntimeGeometryAuthority {
    pub pose_id: String,
    pub source_candidate_id: Option<String>,
    pub authored_facing: Direction,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PoseUseKind {
    Clip,
    Transition,
    FaceAccent,
    Showcase,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CapabilityTier {
    DirectionalBase,
    FrontPerformance,
    DiagonalFlight,
    FaceAccent,
    ShowcaseOnly,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ClipFamily {
    Idle,
    Listening,
    Thinking,
    PreparingResponse,
    Speaking,
    Clarifying,
    ToolWait,
    Error,
    Celebrating,
    Interrupted,
    GroundLocomotion,
    Flight,
    StaffAction,
    Reaction,
    FeelingAccent,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LoopMode {
    Once,
    Repeat,
    MarkedSegment,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PhaseSource {
    Time,
    Distance,
    Wing,
    Speech,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MotionMarker {
    Entry,
    Anticipation,
    Commit,
    Release,
    Impact,
    Apex,
    AccentHold,
    LeftContact,
    LeftRelease,
    RightContact,
    RightRelease,
    StaffPlant,
    StaffRelease,
    HandPlant,
    HandRelease,
    WingUp,
    WingDown,
    Glide,
    PhraseStart,
    SpeechAccent,
    ClauseEnd,
    Recover,
    Settled,
    LoopStart,
    LoopEnd,
    Exit,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PerformanceRegion {
    BaseBody,
    UpperBody,
    FaceEmotion,
    Speech,
    Gaze,
    Blink,
    StaffEffect,
    Secondary,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RegionMask {
    pub regions: Vec<PerformanceRegion>,
}

pub type ChannelMask = RegionMask;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InterruptPolicy {
    Immediate,
    AtSafeMarker,
    AfterCommit,
    AfterImpact,
    UninterruptibleUntilRecovery,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RecoveryPolicy {
    RestorePrevious,
    SettleToIdle,
    SettleToListening,
    ContinueTarget,
    EmergencyHome,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MotionClip {
    pub clip_id: String,
    pub family: ClipFamily,
    pub loop_mode: LoopMode,
    pub phase_source: PhaseSource,
    pub entry_marker: MotionMarker,
    pub exit_markers: Vec<MotionMarker>,
    pub minimum_hold_ticks: u16,
    pub interrupt_policy: InterruptPolicy,
    pub owned_channels: ChannelMask,
    pub samples: Vec<MotionSample>,
    pub loop_start_sample: Option<usize>,
    pub loop_end_sample: Option<usize>,
    pub reduced_motion_clip_id: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MotionSample {
    pub pose_id: String,
    pub hold_ticks: u16,
    pub transition_recipe_id: String,
    pub markers: Vec<MotionMarker>,
    pub support: SupportContact,
    pub root_offset: [i8; 2],
    pub secondary_profile_id: String,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SupportMode {
    Grounded,
    Airborne,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContactPoint {
    LeftFoot,
    RightFoot,
    StaffTip,
    LeftHand,
    RightHand,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SupportContact {
    pub mode: SupportMode,
    pub points: Vec<ContactPoint>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TransitionTiming {
    Fixed,
    MarkerAligned,
    DistancePhase,
    WingPhase,
    SpeechAligned,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TickRange {
    pub min: u16,
    pub max: u16,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContactPolicy {
    Preserve,
    TransferAtMarker,
    ReleaseThenAirborne,
    AirborneThenLand,
    BraceTransfer,
    None,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RootPolicy {
    Preserve,
    FollowTarget,
    AuthoredOffset,
    ContactLocked,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RegionPolicy {
    PreserveUnowned,
    ReplaceOwned,
    FaceOnly,
    ReducedMotion,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SecondaryPolicy {
    Preserve,
    Settle,
    ResetAtMarker,
    Suppress,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct InterruptWindow {
    pub start_marker: MotionMarker,
    pub end_marker: MotionMarker,
    pub interrupt_policy: InterruptPolicy,
    pub recovery_policy: RecoveryPolicy,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TransitionRecipe {
    pub recipe_id: String,
    pub source_families: Vec<ClipFamily>,
    pub target_families: Vec<ClipFamily>,
    pub timing: TransitionTiming,
    pub duration_ticks: TickRange,
    pub handoff_marker: MotionMarker,
    pub contact_policy: ContactPolicy,
    pub root_policy: RootPolicy,
    pub region_policy: RegionPolicy,
    pub secondary_policy: SecondaryPolicy,
    pub interrupt_windows: Vec<InterruptWindow>,
    pub fallback_recipe_id: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MotionEdge {
    pub edge_id: String,
    pub source_clip_id: String,
    pub target_clip_id: String,
    pub transition_recipe_id: String,
    pub allowed_turn_states: Vec<ChatTurnState>,
    pub allowed_motion_profiles: Vec<MotionProfile>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TurnStateProfile {
    pub turn_state: ChatTurnState,
    pub entry_clip_id: String,
    pub stable_clip_id: String,
    pub variant_set_id: Option<String>,
    pub recovery_policy: RecoveryPolicy,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EmotionProfile {
    pub emotion: Emotion,
    pub accent_variant_set_id: Option<String>,
    pub rest_mouth_pose: RenderedMouthPose,
    pub negative_pose_may_loop: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct VariantSet {
    pub variant_set_id: String,
    pub choices: Vec<VariantChoice>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct VariantChoice {
    pub clip_id: String,
    pub weight: u16,
    pub cooldown_generations: u16,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ReducedMotionOverride {
    pub source_clip_id: String,
    pub reduced_clip_id: String,
    pub suppress_root_motion: bool,
    pub suppress_secondary_motion: bool,
    pub suppress_repeated_gestures: bool,
    pub maximum_mouth_steps_per_second: u8,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MotionGraphValidationError {
    pub issues: Vec<String>,
}

impl fmt::Display for MotionGraphValidationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "motion graph validation failed: {}",
            self.issues.join("; ")
        )
    }
}

impl Error for MotionGraphValidationError {}

#[derive(Debug, Error)]
pub enum MotionGraphLoadError {
    #[error("motion graph JSON is invalid: {0}")]
    Decode(#[from] serde_json::Error),
    #[error(transparent)]
    Validation(#[from] MotionGraphValidationError),
}

impl MotionGraphV1 {
    pub fn from_json(json: &str) -> Result<Self, MotionGraphLoadError> {
        let graph: Self = serde_json::from_str(json)?;
        graph.validate()?;
        Ok(graph)
    }

    pub fn validate(&self) -> Result<(), MotionGraphValidationError> {
        let mut issues = BTreeSet::new();
        if self.schema_version != MOTION_GRAPH_SCHEMA_VERSION {
            issues.insert(format!(
                "schema_version must be {MOTION_GRAPH_SCHEMA_VERSION}, got {}",
                self.schema_version
            ));
        }
        if self.asset_schema_version != REQUIRED_ASSET_SCHEMA_VERSION {
            issues.insert(format!(
                "asset_schema_version must be {REQUIRED_ASSET_SCHEMA_VERSION}, got {}",
                self.asset_schema_version
            ));
        }
        if self.required_runtime_geometry_count != REQUIRED_RUNTIME_GEOMETRY_COUNT {
            issues.insert(format!(
                "required_runtime_geometry_count must be {REQUIRED_RUNTIME_GEOMETRY_COUNT}, got {}",
                self.required_runtime_geometry_count
            ));
        }
        if self.required_wjfl_geometry_count != REQUIRED_WJFL_GEOMETRY_COUNT {
            issues.insert(format!(
                "required_wjfl_geometry_count must be {REQUIRED_WJFL_GEOMETRY_COUNT}, got {}",
                self.required_wjfl_geometry_count
            ));
        }
        validate_id("graph_id", &self.graph_id, &mut issues);

        let pose_ids = collect_ids(
            self.pose_coverage.iter().map(|pose| pose.pose_id.as_str()),
            "pose_coverage.pose_id",
            &mut issues,
        );
        if self.pose_coverage.len() != self.required_runtime_geometry_count {
            issues.insert(format!(
                "pose_coverage must contain {} rows, got {}",
                self.required_runtime_geometry_count,
                self.pose_coverage.len()
            ));
        }
        for pose in &self.pose_coverage {
            validate_pose_id(&pose.pose_id, &mut issues);
            if let Some(candidate_id) = &pose.source_candidate_id {
                validate_id(
                    &format!("pose {} source_candidate_id", pose.pose_id),
                    candidate_id,
                    &mut issues,
                );
            }
            if pose.use_kinds.is_empty() {
                issues.insert(format!("pose {} has no use_kinds", pose.pose_id));
            }
            ensure_unique(
                &pose.use_kinds,
                &format!("pose {} use_kinds", pose.pose_id),
                &mut issues,
            );
            if pose.approved_facings.is_empty() {
                issues.insert(format!("pose {} has no approved_facings", pose.pose_id));
            }
            ensure_unique(
                &pose.approved_facings,
                &format!("pose {} approved_facings", pose.pose_id),
                &mut issues,
            );
            validate_showcase_approval(pose, &pose_ids, &mut issues);
        }
        validate_state_facing_fallback_references(
            &self.state_facing_fallbacks,
            &self.pose_coverage,
            &mut issues,
        );

        let clip_ids = collect_ids(
            self.clips.iter().map(|clip| clip.clip_id.as_str()),
            "clips.clip_id",
            &mut issues,
        );
        let recipe_ids = collect_ids(
            self.transition_recipes
                .iter()
                .map(|recipe| recipe.recipe_id.as_str()),
            "transition_recipes.recipe_id",
            &mut issues,
        );
        for required_recipe_id in REQUIRED_RECIPE_IDS {
            if !recipe_ids.contains(required_recipe_id) {
                issues.insert(format!(
                    "transition_recipes is missing required v1 recipe {required_recipe_id}"
                ));
            }
        }
        let variant_ids = collect_ids(
            self.variant_sets
                .iter()
                .map(|set| set.variant_set_id.as_str()),
            "variant_sets.variant_set_id",
            &mut issues,
        );
        let _edge_ids = collect_ids(
            self.edges.iter().map(|edge| edge.edge_id.as_str()),
            "edges.edge_id",
            &mut issues,
        );

        if !clip_ids.contains(&self.default_clip_id) {
            issues.insert(format!(
                "default_clip_id {} does not reference a clip",
                self.default_clip_id
            ));
        }

        let clip_families = self
            .clips
            .iter()
            .map(|clip| (clip.clip_id.as_str(), clip.family))
            .collect::<BTreeMap<_, _>>();
        let recipes = self
            .transition_recipes
            .iter()
            .map(|recipe| (recipe.recipe_id.as_str(), recipe))
            .collect::<BTreeMap<_, _>>();

        for clip in &self.clips {
            validate_clip(clip, &pose_ids, &recipe_ids, &clip_ids, &mut issues);
        }
        for recipe in &self.transition_recipes {
            validate_recipe(recipe, &recipe_ids, &mut issues);
        }
        validate_recipe_fallback_cycles(&recipes, &mut issues);
        validate_edges(&self.edges, &clip_families, &recipes, &mut issues);
        validate_turn_state_profiles(
            &self.turn_state_profiles,
            &clip_ids,
            &variant_ids,
            &mut issues,
        );
        validate_emotion_profiles(&self.emotion_profiles, &variant_ids, &mut issues);
        validate_variant_sets(&self.variant_sets, &clip_ids, &mut issues);
        validate_reduced_motion(
            &self.reduced_motion_overrides,
            &self.clips,
            &clip_ids,
            &mut issues,
        );

        if issues.is_empty() {
            Ok(())
        } else {
            Err(MotionGraphValidationError {
                issues: issues.into_iter().collect(),
            })
        }
    }

    pub fn validate_against_runtime_authority(
        &self,
        authority: &[RuntimeGeometryAuthority],
    ) -> Result<(), MotionGraphValidationError> {
        let mut issues = self
            .validate()
            .err()
            .map(|error| error.issues.into_iter().collect::<BTreeSet<_>>())
            .unwrap_or_default();

        let mut authority_by_pose = BTreeMap::new();
        let mut authority_candidates = BTreeSet::new();
        for row in authority {
            validate_pose_id(&row.pose_id, &mut issues);
            if authority_by_pose
                .insert(row.pose_id.as_str(), row)
                .is_some()
            {
                issues.insert(format!(
                    "runtime authority contains duplicate pose ID {}",
                    row.pose_id
                ));
            }
            if let Some(candidate_id) = &row.source_candidate_id {
                if !authority_candidates.insert(candidate_id.as_str()) {
                    issues.insert(format!(
                        "runtime authority contains duplicate candidate ID {candidate_id}"
                    ));
                }
            }
        }

        if authority_by_pose.len() != REQUIRED_RUNTIME_GEOMETRY_COUNT {
            issues.insert(format!(
                "runtime authority must contain {REQUIRED_RUNTIME_GEOMETRY_COUNT} unique geometries, got {}",
                authority_by_pose.len()
            ));
        }

        let coverage_by_pose = self
            .pose_coverage
            .iter()
            .map(|row| (row.pose_id.as_str(), row))
            .collect::<BTreeMap<_, _>>();
        for pose_id in authority_by_pose.keys() {
            if !coverage_by_pose.contains_key(pose_id) {
                issues.insert(format!("pose_coverage is missing runtime pose {pose_id}"));
            }
        }
        for pose_id in coverage_by_pose.keys() {
            if !authority_by_pose.contains_key(pose_id) {
                issues.insert(format!(
                    "pose_coverage contains unknown runtime pose {pose_id}"
                ));
            }
        }

        let referenced_poses = self
            .clips
            .iter()
            .flat_map(|clip| clip.samples.iter().map(|sample| sample.pose_id.as_str()))
            .collect::<BTreeSet<_>>();
        for (pose_id, coverage) in &coverage_by_pose {
            let Some(authority_row) = authority_by_pose.get(pose_id) else {
                continue;
            };
            if coverage.source_candidate_id != authority_row.source_candidate_id {
                issues.insert(format!(
                    "pose {pose_id} source_candidate_id does not match runtime authority"
                ));
            }
            if !coverage
                .approved_facings
                .contains(&authority_row.authored_facing)
            {
                issues.insert(format!(
                    "pose {pose_id} does not approve its authored facing {:?}",
                    authority_row.authored_facing
                ));
            }
            validate_capability_tier(coverage, &mut issues);
            if coverage.capability_tier == CapabilityTier::ShowcaseOnly
                && coverage.showcase_approval.is_none()
            {
                issues.insert(format!(
                    "showcase-only pose {pose_id} requires approval metadata"
                ));
            }
            if coverage.capability_tier != CapabilityTier::ShowcaseOnly
                && !referenced_poses.contains(pose_id)
            {
                issues.insert(format!(
                    "non-showcase pose {pose_id} is absent from every authored clip"
                ));
            }
        }

        let expected_wjfl = authority_candidates
            .iter()
            .filter(|candidate_id| candidate_id.starts_with("WJFL-"))
            .copied()
            .collect::<BTreeSet<_>>();
        let catalog_wjfl = self
            .pose_coverage
            .iter()
            .filter_map(|row| row.source_candidate_id.as_deref())
            .filter(|candidate_id| candidate_id.starts_with("WJFL-"))
            .collect::<BTreeSet<_>>();
        if expected_wjfl.len() != REQUIRED_WJFL_GEOMETRY_COUNT {
            issues.insert(format!(
                "runtime authority must contain {REQUIRED_WJFL_GEOMETRY_COUNT} WJFL geometries, got {}",
                expected_wjfl.len()
            ));
        }
        if catalog_wjfl != expected_wjfl {
            issues.insert("pose_coverage WJFL candidate IDs do not match runtime authority".into());
        }

        validate_complete_state_facing_fallbacks(
            &self.state_facing_fallbacks,
            &coverage_by_pose,
            &mut issues,
        );

        if issues.is_empty() {
            Ok(())
        } else {
            Err(MotionGraphValidationError {
                issues: issues.into_iter().collect(),
            })
        }
    }
}

fn validate_showcase_approval(
    pose: &PoseCoverage,
    pose_ids: &BTreeSet<String>,
    issues: &mut BTreeSet<String>,
) {
    match (pose.capability_tier, &pose.showcase_approval) {
        (CapabilityTier::ShowcaseOnly, Some(approval)) => {
            if approval.owner.trim().is_empty() || approval.rationale.trim().is_empty() {
                issues.insert(format!(
                    "showcase-only pose {} requires non-empty owner and rationale",
                    pose.pose_id
                ));
            }
            if approval.fallback_pose_id == pose.pose_id
                || !pose_ids.contains(&approval.fallback_pose_id)
            {
                issues.insert(format!(
                    "showcase-only pose {} has invalid fallback pose {}",
                    pose.pose_id, approval.fallback_pose_id
                ));
            }
            if !pose.use_kinds.contains(&PoseUseKind::Showcase) {
                issues.insert(format!(
                    "showcase-only pose {} must declare showcase use",
                    pose.pose_id
                ));
            }
        }
        (CapabilityTier::ShowcaseOnly, None) => {}
        (_, Some(_)) => {
            issues.insert(format!(
                "non-showcase pose {} may not carry showcase approval",
                pose.pose_id
            ));
        }
        (_, None) => {}
    }
}

fn validate_state_facing_fallback_references(
    fallbacks: &[StateFacingFallback],
    coverage: &[PoseCoverage],
    issues: &mut BTreeSet<String>,
) {
    let coverage_by_pose = coverage
        .iter()
        .map(|row| (row.pose_id.as_str(), row))
        .collect::<BTreeMap<_, _>>();
    let mut keys = BTreeSet::new();
    for fallback in fallbacks {
        if !keys.insert((fallback.turn_state, fallback.requested_facing)) {
            issues.insert(format!(
                "state_facing_fallbacks repeats {:?}/{:?}",
                fallback.turn_state, fallback.requested_facing
            ));
        }
        match coverage_by_pose.get(fallback.fallback_pose_id.as_str()) {
            None => {
                issues.insert(format!(
                    "state/facing fallback {:?}/{:?} references missing pose {}",
                    fallback.turn_state, fallback.requested_facing, fallback.fallback_pose_id
                ));
            }
            Some(target) if !target.approved_facings.contains(&fallback.requested_facing) => {
                issues.insert(format!(
                    "state/facing fallback {:?}/{:?} targets pose {} without that facing",
                    fallback.turn_state, fallback.requested_facing, fallback.fallback_pose_id
                ));
            }
            Some(_) => {}
        }
    }
}

fn validate_complete_state_facing_fallbacks(
    fallbacks: &[StateFacingFallback],
    coverage_by_pose: &BTreeMap<&str, &PoseCoverage>,
    issues: &mut BTreeSet<String>,
) {
    let actual = fallbacks
        .iter()
        .map(|fallback| (fallback.turn_state, fallback.requested_facing))
        .collect::<BTreeSet<_>>();
    let expected = ChatTurnState::ALL
        .into_iter()
        .flat_map(|state| {
            Direction::ALL
                .into_iter()
                .map(move |facing| (state, facing))
        })
        .collect::<BTreeSet<_>>();
    if fallbacks.len() != expected.len() || actual != expected {
        issues.insert(
            "state_facing_fallbacks must contain every canonical state/facing pair exactly once"
                .into(),
        );
    }
    for fallback in fallbacks {
        if !coverage_by_pose.contains_key(fallback.fallback_pose_id.as_str()) {
            issues.insert(format!(
                "state/facing fallback references unknown runtime pose {}",
                fallback.fallback_pose_id
            ));
        }
    }
}

fn validate_capability_tier(pose: &PoseCoverage, issues: &mut BTreeSet<String>) {
    let facings = pose
        .approved_facings
        .iter()
        .copied()
        .collect::<BTreeSet<_>>();
    let allowed = match pose.capability_tier {
        CapabilityTier::DirectionalBase => Direction::ALL.into_iter().collect(),
        CapabilityTier::DiagonalFlight => [Direction::SouthWest, Direction::SouthEast]
            .into_iter()
            .collect(),
        CapabilityTier::FrontPerformance
        | CapabilityTier::FaceAccent
        | CapabilityTier::ShowcaseOnly => [Direction::South].into_iter().collect(),
    };
    if !facings.is_subset(&allowed) {
        issues.insert(format!(
            "pose {} claims facings outside capability tier {:?}",
            pose.pose_id, pose.capability_tier
        ));
    }
    if pose.capability_tier != CapabilityTier::ShowcaseOnly
        && pose.use_kinds == [PoseUseKind::Showcase]
    {
        issues.insert(format!(
            "non-showcase pose {} cannot be classified only as showcase",
            pose.pose_id
        ));
    }
}

fn validate_clip(
    clip: &MotionClip,
    pose_ids: &BTreeSet<String>,
    recipe_ids: &BTreeSet<String>,
    clip_ids: &BTreeSet<String>,
    issues: &mut BTreeSet<String>,
) {
    if clip.samples.is_empty() {
        issues.insert(format!("clip {} has no samples", clip.clip_id));
        return;
    }
    if clip.exit_markers.is_empty() {
        issues.insert(format!("clip {} has no exit_markers", clip.clip_id));
    }
    ensure_unique(
        &clip.exit_markers,
        &format!("clip {} exit_markers", clip.clip_id),
        issues,
    );
    validate_region_mask(&clip.clip_id, &clip.owned_channels, issues);
    if clip.minimum_hold_ticks == 0 {
        issues.insert(format!(
            "clip {} minimum_hold_ticks must be positive",
            clip.clip_id
        ));
    }

    let mut marker_positions = BTreeMap::<MotionMarker, Vec<usize>>::new();
    for (sample_index, sample) in clip.samples.iter().enumerate() {
        for marker in &sample.markers {
            marker_positions
                .entry(*marker)
                .or_default()
                .push(sample_index);
        }
    }
    if !clip.samples[0].markers.contains(&clip.entry_marker) {
        issues.insert(format!(
            "clip {} entry_marker is absent from its first sample",
            clip.clip_id
        ));
    }
    if marker_positions
        .get(&clip.entry_marker)
        .is_none_or(|positions| positions.len() != 1)
    {
        issues.insert(format!(
            "clip {} entry_marker must occur exactly once",
            clip.clip_id
        ));
    }
    for marker in &clip.exit_markers {
        if marker_positions
            .get(marker)
            .is_none_or(|positions| positions.len() != 1)
        {
            issues.insert(format!(
                "clip {} exit marker {marker:?} must occur exactly once",
                clip.clip_id
            ));
        }
    }

    for (index, sample) in clip.samples.iter().enumerate() {
        if !pose_ids.contains(&sample.pose_id) {
            issues.insert(format!(
                "clip {} sample {index} references missing pose {}",
                clip.clip_id, sample.pose_id
            ));
        }
        if !recipe_ids.contains(&sample.transition_recipe_id) {
            issues.insert(format!(
                "clip {} sample {index} references missing recipe {}",
                clip.clip_id, sample.transition_recipe_id
            ));
        }
        if sample.hold_ticks == 0 {
            issues.insert(format!(
                "clip {} sample {index} hold_ticks must be positive",
                clip.clip_id
            ));
        }
        validate_id(
            &format!("clip {} sample {index} secondary_profile_id", clip.clip_id),
            &sample.secondary_profile_id,
            issues,
        );
        ensure_unique(
            &sample.markers,
            &format!("clip {} sample {index} markers", clip.clip_id),
            issues,
        );
        validate_support(&clip.clip_id, index, &sample.support, issues);
    }

    match clip.loop_mode {
        LoopMode::Once | LoopMode::Repeat => {
            if clip.loop_start_sample.is_some() || clip.loop_end_sample.is_some() {
                issues.insert(format!(
                    "clip {} may set loop indexes only for marked_segment",
                    clip.clip_id
                ));
            }
            if clip.loop_mode == LoopMode::Once
                && (marker_positions.contains_key(&MotionMarker::LoopStart)
                    || marker_positions.contains_key(&MotionMarker::LoopEnd))
            {
                issues.insert(format!(
                    "clip {} once loop may not declare loop boundary markers",
                    clip.clip_id
                ));
            }
        }
        LoopMode::MarkedSegment => match (clip.loop_start_sample, clip.loop_end_sample) {
            (Some(start), Some(end))
                if start < end
                    && end < clip.samples.len()
                    && marker_positions
                        .get(&MotionMarker::LoopStart)
                        .is_some_and(|positions| positions.as_slice() == [start])
                    && marker_positions
                        .get(&MotionMarker::LoopEnd)
                        .is_some_and(|positions| positions.as_slice() == [end])
                    && clip.samples[start]
                        .markers
                        .contains(&MotionMarker::LoopStart)
                    && clip.samples[end].markers.contains(&MotionMarker::LoopEnd) => {}
            _ => {
                issues.insert(format!(
                    "clip {} has invalid marked_segment indexes or markers",
                    clip.clip_id
                ));
            }
        },
    }

    if clip
        .reduced_motion_clip_id
        .as_ref()
        .is_some_and(|clip_id| !clip_ids.contains(clip_id))
    {
        issues.insert(format!(
            "clip {} references missing reduced motion clip",
            clip.clip_id
        ));
    }
}

fn validate_region_mask(clip_id: &str, mask: &RegionMask, issues: &mut BTreeSet<String>) {
    if mask.regions.is_empty() {
        issues.insert(format!("clip {clip_id} owns no performance regions"));
    }
    ensure_unique(
        &mask.regions,
        &format!("clip {clip_id} owned regions"),
        issues,
    );
}

fn validate_support(
    clip_id: &str,
    sample_index: usize,
    support: &SupportContact,
    issues: &mut BTreeSet<String>,
) {
    ensure_unique(
        &support.points,
        &format!("clip {clip_id} sample {sample_index} support points"),
        issues,
    );
    match support.mode {
        SupportMode::Airborne if !support.points.is_empty() => {
            issues.insert(format!(
                "clip {clip_id} sample {sample_index} is airborne but claims contacts"
            ));
        }
        SupportMode::Grounded if support.points.is_empty() => {
            issues.insert(format!(
                "clip {clip_id} sample {sample_index} is grounded without contacts"
            ));
        }
        SupportMode::Grounded | SupportMode::Airborne => {}
    }
}

fn validate_recipe(
    recipe: &TransitionRecipe,
    recipe_ids: &BTreeSet<String>,
    issues: &mut BTreeSet<String>,
) {
    if recipe.source_families.is_empty() || recipe.target_families.is_empty() {
        issues.insert(format!(
            "recipe {} must declare source and target families",
            recipe.recipe_id
        ));
    }
    ensure_unique(
        &recipe.source_families,
        &format!("recipe {} source_families", recipe.recipe_id),
        issues,
    );
    ensure_unique(
        &recipe.target_families,
        &format!("recipe {} target_families", recipe.recipe_id),
        issues,
    );
    if recipe.duration_ticks.min == 0 || recipe.duration_ticks.min > recipe.duration_ticks.max {
        issues.insert(format!(
            "recipe {} has invalid duration range",
            recipe.recipe_id
        ));
    }
    if recipe.interrupt_windows.is_empty() {
        issues.insert(format!(
            "recipe {} must declare at least one interrupt window",
            recipe.recipe_id
        ));
    }
    if recipe
        .fallback_recipe_id
        .as_ref()
        .is_some_and(|fallback| fallback == &recipe.recipe_id || !recipe_ids.contains(fallback))
    {
        issues.insert(format!(
            "recipe {} has an invalid fallback recipe",
            recipe.recipe_id
        ));
    }
    for (index, window) in recipe.interrupt_windows.iter().enumerate() {
        if window.start_marker == window.end_marker {
            issues.insert(format!(
                "recipe {} interrupt window {index} has identical markers",
                recipe.recipe_id
            ));
        }
    }
}

fn validate_recipe_fallback_cycles(
    recipes: &BTreeMap<&str, &TransitionRecipe>,
    issues: &mut BTreeSet<String>,
) {
    for recipe_id in recipes.keys() {
        let mut seen = BTreeSet::new();
        let mut current = Some(*recipe_id);
        while let Some(id) = current {
            if !seen.insert(id) {
                issues.insert(format!(
                    "recipe {recipe_id} participates in a fallback cycle at {id}"
                ));
                break;
            }
            current = recipes
                .get(id)
                .and_then(|recipe| recipe.fallback_recipe_id.as_deref());
        }
    }
}

fn validate_edges(
    edges: &[MotionEdge],
    clip_families: &BTreeMap<&str, ClipFamily>,
    recipes: &BTreeMap<&str, &TransitionRecipe>,
    issues: &mut BTreeSet<String>,
) {
    let mut triples = BTreeSet::new();
    for edge in edges {
        let source = clip_families.get(edge.source_clip_id.as_str());
        let target = clip_families.get(edge.target_clip_id.as_str());
        if source.is_none() {
            issues.insert(format!(
                "edge {} references missing source clip {}",
                edge.edge_id, edge.source_clip_id
            ));
        }
        if target.is_none() {
            issues.insert(format!(
                "edge {} references missing target clip {}",
                edge.edge_id, edge.target_clip_id
            ));
        }
        match recipes.get(edge.transition_recipe_id.as_str()) {
            None => {
                issues.insert(format!(
                    "edge {} references missing recipe {}",
                    edge.edge_id, edge.transition_recipe_id
                ));
            }
            Some(recipe) => {
                if source.is_some_and(|family| !recipe.source_families.contains(family)) {
                    issues.insert(format!(
                        "edge {} source family is not admitted by recipe {}",
                        edge.edge_id, edge.transition_recipe_id
                    ));
                }
                if target.is_some_and(|family| !recipe.target_families.contains(family)) {
                    issues.insert(format!(
                        "edge {} target family is not admitted by recipe {}",
                        edge.edge_id, edge.transition_recipe_id
                    ));
                }
            }
        }
        if edge.allowed_turn_states.is_empty() || edge.allowed_motion_profiles.is_empty() {
            issues.insert(format!(
                "edge {} must declare turn states and motion profiles",
                edge.edge_id
            ));
        }
        ensure_unique(
            &edge.allowed_turn_states,
            &format!("edge {} allowed_turn_states", edge.edge_id),
            issues,
        );
        ensure_unique(
            &edge.allowed_motion_profiles,
            &format!("edge {} allowed_motion_profiles", edge.edge_id),
            issues,
        );
        if !triples.insert((
            edge.source_clip_id.as_str(),
            edge.target_clip_id.as_str(),
            edge.transition_recipe_id.as_str(),
        )) {
            issues.insert(format!("edge {} duplicates a directed edge", edge.edge_id));
        }
    }
}

fn validate_turn_state_profiles(
    profiles: &[TurnStateProfile],
    clip_ids: &BTreeSet<String>,
    variant_ids: &BTreeSet<String>,
    issues: &mut BTreeSet<String>,
) {
    let states = profiles
        .iter()
        .map(|profile| profile.turn_state)
        .collect::<BTreeSet<_>>();
    let required = ChatTurnState::ALL.into_iter().collect::<BTreeSet<_>>();
    if profiles.len() != required.len() || states != required {
        issues.insert("turn_state_profiles must contain each canonical state exactly once".into());
    }
    for profile in profiles {
        for (field, clip_id) in [
            ("entry_clip_id", &profile.entry_clip_id),
            ("stable_clip_id", &profile.stable_clip_id),
        ] {
            if !clip_ids.contains(clip_id) {
                issues.insert(format!(
                    "turn state {:?} {field} references missing clip {clip_id}",
                    profile.turn_state
                ));
            }
        }
        if profile
            .variant_set_id
            .as_ref()
            .is_some_and(|id| !variant_ids.contains(id))
        {
            issues.insert(format!(
                "turn state {:?} references missing variant set",
                profile.turn_state
            ));
        }
    }
}

fn validate_emotion_profiles(
    profiles: &[EmotionProfile],
    variant_ids: &BTreeSet<String>,
    issues: &mut BTreeSet<String>,
) {
    let emotions = profiles
        .iter()
        .map(|profile| profile.emotion)
        .collect::<BTreeSet<_>>();
    let required = Emotion::ALL.into_iter().collect::<BTreeSet<_>>();
    if profiles.len() != required.len() || emotions != required {
        issues.insert("emotion_profiles must contain each canonical emotion exactly once".into());
    }
    for profile in profiles {
        if profile
            .accent_variant_set_id
            .as_ref()
            .is_some_and(|id| !variant_ids.contains(id))
        {
            issues.insert(format!(
                "emotion {:?} references missing variant set",
                profile.emotion
            ));
        }
        if profile.negative_pose_may_loop
            && matches!(
                profile.emotion,
                Emotion::Sadness
                    | Emotion::Anger
                    | Emotion::Fear
                    | Emotion::Shame
                    | Emotion::Disgust
                    | Emotion::Guilt
            )
        {
            issues.insert(format!(
                "negative emotion {:?} may not loop",
                profile.emotion
            ));
        }
    }
}

fn validate_variant_sets(
    sets: &[VariantSet],
    clip_ids: &BTreeSet<String>,
    issues: &mut BTreeSet<String>,
) {
    for set in sets {
        if set.choices.is_empty() {
            issues.insert(format!("variant set {} has no choices", set.variant_set_id));
        }
        let mut choices = BTreeSet::new();
        for choice in &set.choices {
            if !clip_ids.contains(&choice.clip_id) {
                issues.insert(format!(
                    "variant set {} references missing clip {}",
                    set.variant_set_id, choice.clip_id
                ));
            }
            if choice.weight == 0 {
                issues.insert(format!(
                    "variant set {} contains a zero-weight choice",
                    set.variant_set_id
                ));
            }
            if !choices.insert(choice.clip_id.as_str()) {
                issues.insert(format!(
                    "variant set {} repeats clip {}",
                    set.variant_set_id, choice.clip_id
                ));
            }
        }
    }
}

fn validate_reduced_motion(
    overrides: &[ReducedMotionOverride],
    clips: &[MotionClip],
    clip_ids: &BTreeSet<String>,
    issues: &mut BTreeSet<String>,
) {
    let declared = clips
        .iter()
        .filter_map(|clip| {
            clip.reduced_motion_clip_id
                .as_deref()
                .map(|reduced| (clip.clip_id.as_str(), reduced))
        })
        .collect::<BTreeMap<_, _>>();
    let mut sources = BTreeSet::new();
    for item in overrides {
        if !sources.insert(item.source_clip_id.as_str()) {
            issues.insert(format!(
                "reduced motion repeats source clip {}",
                item.source_clip_id
            ));
        }
        if !clip_ids.contains(&item.source_clip_id) || !clip_ids.contains(&item.reduced_clip_id) {
            issues.insert(format!(
                "reduced motion override {} -> {} references a missing clip",
                item.source_clip_id, item.reduced_clip_id
            ));
        }
        if item.source_clip_id == item.reduced_clip_id {
            issues.insert(format!(
                "reduced motion override {} must select a distinct clip",
                item.source_clip_id
            ));
        }
        if declared.get(item.source_clip_id.as_str()).copied()
            != Some(item.reduced_clip_id.as_str())
        {
            issues.insert(format!(
                "reduced motion override {} -> {} disagrees with its source clip",
                item.source_clip_id, item.reduced_clip_id
            ));
        }
        if item.maximum_mouth_steps_per_second == 0 {
            issues.insert(format!(
                "reduced motion override {} must retain readable mouth motion",
                item.source_clip_id
            ));
        }
    }
    for (source, reduced) in declared {
        if !overrides
            .iter()
            .any(|item| item.source_clip_id == source && item.reduced_clip_id == reduced)
        {
            issues.insert(format!(
                "clip {source} declares reduced motion clip {reduced} without an override"
            ));
        }
    }
}

fn collect_ids<'a>(
    values: impl Iterator<Item = &'a str>,
    field: &str,
    issues: &mut BTreeSet<String>,
) -> BTreeSet<String> {
    let mut ids = BTreeSet::new();
    for value in values {
        validate_id(field, value, issues);
        if !ids.insert(value.to_string()) {
            issues.insert(format!("{field} contains duplicate id {value}"));
        }
    }
    ids
}

fn validate_id(field: &str, value: &str, issues: &mut BTreeSet<String>) {
    if value.is_empty() || value.len() > 128 || !value.bytes().all(|byte| byte.is_ascii_graphic()) {
        issues.insert(format!("{field} must be 1..=128 printable ASCII bytes"));
    }
}

fn validate_pose_id(value: &str, issues: &mut BTreeSet<String>) {
    let lowercase = value.to_ascii_lowercase();
    if value.contains('/') || value.contains('\\') || lowercase.ends_with(".png") {
        issues.insert(format!(
            "pose_id {value} must name authored geometry, not a runtime image path"
        ));
    }
}

fn ensure_unique<T>(values: &[T], field: &str, issues: &mut BTreeSet<String>)
where
    T: Copy + Ord,
{
    if values.iter().copied().collect::<BTreeSet<_>>().len() != values.len() {
        issues.insert(format!("{field} contains duplicate values"));
    }
}
