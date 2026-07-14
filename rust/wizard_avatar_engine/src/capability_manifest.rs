use crate::animation::reference_pose_id_for_state;
use crate::chat_event::{
    AttentionTarget, ChatTurnState, Emotion, GestureKind, MotionProfile, Viseme,
    CHAT_EVENT_SCHEMA_VERSION,
};
use crate::chat_performance::{
    RenderedMouthPose, CHAT_PERFORMANCE_SCHEMA_VERSION, DURATION_FALLBACK_VERSION,
};
use crate::command::COMMAND_SCHEMA_VERSION;
use crate::controller::{ControllerCommandKind, PROCEDURAL_CONTROLLER_COMMANDS};
use crate::motion_catalog::{shadow_motion_catalog, EMBEDDED_MOTION_GRAPH_SHA256};
use crate::motion_graph::{
    CapabilityTier, ClipFamily, InterruptPolicy, LoopMode, MotionClip, MotionGraphV1, PoseUseKind,
    MOTION_GRAPH_SCHEMA_VERSION, REQUIRED_RUNTIME_GEOMETRY_COUNT,
};
use crate::pose::{PoseDefinition, PoseLibrary, PoseMotionFamily};
use crate::pose_asset::{
    embedded_pose_archive_sha256, load_embedded_pose_library, IMPORTED_POSE_SCHEMA_VERSION,
};
use crate::pose_clip::{PoseClipDefinition, POSE_CLIPS};
use crate::state::{Direction, Expression, Locomotion, WizardState};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::sync::OnceLock;

pub const CAPABILITY_MANIFEST_SCHEMA_VERSION: u16 = 2;
pub const CAPABILITY_API_VERSION: u16 = 2;
pub const RUNTIME_PROFILE_VERSION: u16 = 1;
pub const RUNTIME_POLICY_VERSION: u16 = 1;
pub const RUNTIME_TRANSPORT_VERSION: u16 = 1;
pub const REQUIRED_POSE_ALIAS_COUNT: usize = 1;

const MAX_CAPABILITIES: usize = 512;
const MAX_ID_BYTES: usize = 128;
const MAX_TEXT_BYTES: usize = 256;
const MAX_TEXT_VALUES: usize = 16;
const MAX_TICK_DURATION: u32 = 60 * 60 * 30;

static CAPABILITY_DOCUMENT: OnceLock<Result<CapabilityDocumentV1, String>> = OnceLock::new();

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CapabilityKind {
    Pose,
    PoseAlias,
    LegacyClip,
    MotionClip,
    Expression,
    MouthPose,
    ChatState,
    Emotion,
    GestureIntent,
    GazeIntent,
    VisemeIntent,
    ProceduralBehavior,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CapabilityStatus {
    ActiveLegacy,
    ShadowValidated,
    ShowcaseOnly,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimeProfileV1 {
    Legacy,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimePolicyV1 {
    LegacyController,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimeTransportV1 {
    AxumHttpWebSocketAdaptiveCodec,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeVersionsV1 {
    pub capability_api_version: u16,
    pub runtime_profile: RuntimeProfileV1,
    pub runtime_profile_version: u16,
    pub runtime_policy: RuntimePolicyV1,
    pub runtime_policy_version: u16,
    pub runtime_transport: RuntimeTransportV1,
    pub runtime_transport_version: u16,
    pub command_schema_version: u16,
    pub chat_event_schema_version: u16,
    pub chat_performance_schema_version: u16,
    pub duration_fallback_policy_version: u16,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PoseFamilyV1 {
    Run,
    Walk,
    Flight,
    Jump,
    Landing,
    GroundAction,
    Kneel,
    Baseline,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LegacyClipCategoryV1 {
    GroundLocomotion,
    FlightPoseSequence,
    Action,
    Celebration,
    Conversation,
    EmotionShowcase,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(tag = "domain", content = "value", rename_all = "snake_case")]
pub enum CapabilityCategoryV1 {
    PoseFamily(PoseFamilyV1),
    PoseAlias,
    LegacyClip(LegacyClipCategoryV1),
    MotionClip(ClipFamily),
    FaceExpression,
    MouthPose,
    ChatState,
    EmotionIntent,
    GestureIntent,
    GazeIntent,
    VisemeIntent,
    RootMotion,
    FacingControl,
    ControllerControl,
    PathMotion,
    SpeechFallback,
    BlinkFallback,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LoopBehaviorV1 {
    NotApplicable,
    Once,
    Repeat,
    MarkedSegment,
    StateDriven,
    EventDriven,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InterruptibilityV1 {
    Immediate,
    RawPoseReplace,
    LegacyGenerationReplace,
    AtSafeMarker,
    AfterCommit,
    AfterImpact,
    UninterruptibleUntilRecovery,
    ContractDefined,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FacePolicyV1 {
    LegacyOverlay,
    PreserveFaceRegion,
    OwnedByClip,
    ContractOnlyNotRendered,
    NotApplicable,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimeSurfaceV1 {
    DirectPoseCommand,
    DirectionalController,
    LegacyPoseClip,
    LegacyController,
    ShadowMotionGraph,
    TypedChatContract,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PropRequirementV1 {
    StaffAllSamples,
    StaffSomeSamples,
    EffectAllSamples,
    EffectSomeSamples,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimeCostV1 {
    ConstantTimeStateUpdate,
    BoundedCellProjection,
    BoundedPoseSequence,
    BoundedMarkerTimeline,
    NotMeasuredUntilRuntimeWiring,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum QualityStatusV1 {
    RuntimeGeometryValidated,
    RuntimeActiveUnscored,
    RuntimeRendered,
    RuntimeRenderedDurationDriven,
    RuntimeActiveLegacy,
    ShadowValidatedNotRuntimeWired,
    ContractValidatedNotRuntimeRendered,
    ShowcaseApprovedNotGeneralPurpose,
    RuntimeAliasValidated,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(tag = "applicability", content = "values", rename_all = "snake_case")]
pub enum ApplicabilityV1<T> {
    NotApplicable,
    Applicable(Vec<T>),
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(tag = "topology", content = "ids", rename_all = "snake_case")]
pub enum FallbackTopologyV1 {
    NotApplicable,
    Terminal,
    Fallbacks(Vec<String>),
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TransitionLimitationV1 {
    RawPoseBypassesSemanticPolicy,
    NotMarkerAwareMotionDirector,
    NotProductionControllerWired,
    NotConsumedByProductionRenderer,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NarrativeUseV1 {
    UrgentTravelOrAction,
    DeliberateStageTravel,
    AirborneStaging,
    AuthoredActionAccent,
    AuthoredRecoveryOrArrival,
    GroundedPerformanceAccent,
    LowOrBracedStaging,
    NeutralStagingAndDirectionalFallback,
    StageTravel,
    FlightShowcaseOnly,
    AuthoredActionBeat,
    PositiveClimax,
    SpokenExplanationOrSocialBeat,
    EmotionReferenceOrShowcase,
    AuthoredStillness,
    ReceptiveAttention,
    InternalThoughtBeat,
    PreSpeechAnticipation,
    SpokenPhrasePerformance,
    ClarificationEmphasis,
    BoundedWaitingState,
    ErrorAcknowledgment,
    InterruptionAndRecovery,
    StaffLedActionBeat,
    ReactionAccent,
    EmotionAccent,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InappropriateUseV1 {
    UnconstrainedModelDirectSelection,
    MediaTimeChoreographyWithoutScore,
    AdvertisingAsRuntimeBeforeWiring,
    AdvertisingAsVisiblyImplemented,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TickDurationV1 {
    pub nominal_ticks: u32,
    pub repeats: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ShowcaseApprovalV1 {
    pub owner: String,
    pub rationale: String,
    pub fallback_pose_id: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PoseCoverageV1 {
    pub use_kinds: Vec<PoseUseKind>,
    pub capability_tier: CapabilityTier,
    pub approved_facings: Vec<Direction>,
    pub showcase_approval: Option<ShowcaseApprovalV1>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PoseAliasV1 {
    pub target_pose_id: String,
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StateFacingFallbackV1 {
    pub turn_state: ChatTurnState,
    pub requested_facing: Direction,
    pub fallback_pose_id: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeSupportFlagsV1 {
    pub deterministic_media_scores: bool,
    pub authored_dance: bool,
    pub rendered_gaze: bool,
    pub timed_visemes: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeSafeIdleProfileV1 {
    pub idle_turn_state: ChatTurnState,
    pub stop_behavior_id: String,
    pub neutral_expression_id: String,
    pub rest_mouth_pose_id: String,
    pub preserve_mode: bool,
    pub preserve_root_position: bool,
    pub preserve_facing: bool,
    pub clear_gesture: bool,
    pub clear_gaze_override: bool,
    pub clear_viseme_override: bool,
    pub clear_blink_override: bool,
    pub clear_prop_effects: bool,
    pub settle_secondary_motion: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CapabilityEntryV1 {
    pub id: String,
    pub kind: CapabilityKind,
    pub status: CapabilityStatus,
    pub category: CapabilityCategoryV1,
    pub emotional_uses: ApplicabilityV1<Emotion>,
    pub energy: u8,
    pub directions: Vec<Direction>,
    pub duration: Option<TickDurationV1>,
    pub loop_behavior: LoopBehaviorV1,
    pub interruptibility: InterruptibilityV1,
    pub valid_entry_states: ApplicabilityV1<ChatTurnState>,
    pub valid_exit_states: ApplicabilityV1<ChatTurnState>,
    pub face_policy: FacePolicyV1,
    pub compatible_face_states: ApplicabilityV1<Expression>,
    pub compatible_locomotion_states: ApplicabilityV1<Locomotion>,
    pub compatible_motion_profiles: Vec<MotionProfile>,
    pub controller_commands: ApplicabilityV1<ControllerCommandKind>,
    pub runtime_surfaces: Vec<RuntimeSurfaceV1>,
    pub prop_requirements: Vec<PropRequirementV1>,
    pub runtime_cost: RuntimeCostV1,
    pub quality_status: QualityStatusV1,
    pub pose_coverage: Option<PoseCoverageV1>,
    pub pose_alias: Option<PoseAliasV1>,
    pub transition_limitations: ApplicabilityV1<TransitionLimitationV1>,
    pub narrative_uses: ApplicabilityV1<NarrativeUseV1>,
    pub inappropriate_uses: ApplicabilityV1<InappropriateUseV1>,
    pub fallback: FallbackTopologyV1,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CapabilityManifestV1 {
    pub schema_version: u16,
    pub character_id: String,
    pub versions: RuntimeVersionsV1,
    pub imported_pose_asset_schema_version: u32,
    pub imported_pose_archive_sha256: String,
    pub runtime_geometry_authority_sha256: String,
    pub pose_geometry_count: usize,
    pub pose_alias_count: usize,
    pub motion_graph_schema_version: u16,
    pub motion_graph_sha256: String,
    pub feelings: Vec<Emotion>,
    pub controller_command_surface: Vec<ControllerCommandKind>,
    pub state_facing_fallbacks: Vec<StateFacingFallbackV1>,
    pub safe_idle: RuntimeSafeIdleProfileV1,
    pub support: RuntimeSupportFlagsV1,
    pub capabilities: Vec<CapabilityEntryV1>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CapabilityDocumentV1 {
    pub manifest_sha256: String,
    pub manifest: CapabilityManifestV1,
}

impl CapabilityDocumentV1 {
    pub fn validate(&self) -> Result<(), String> {
        self.manifest.validate()?;
        validate_sha256(&self.manifest_sha256, "manifest_sha256")?;
        let actual = self.manifest.sha256()?;
        if self.manifest_sha256 != actual {
            return Err(format!(
                "capability document hash mismatch: expected {}, got {actual}",
                self.manifest_sha256
            ));
        }
        Ok(())
    }
}

impl CapabilityManifestV1 {
    pub fn validate(&self) -> Result<(), String> {
        self.validate_header()?;
        validate_sorted_unique(&self.feelings, "feelings")?;
        if self.feelings != non_neutral_emotions() {
            return Err("feelings must be the exact ten non-neutral emotions".to_string());
        }
        validate_sorted_unique(
            &self.controller_command_surface,
            "controller_command_surface",
        )?;
        if self.controller_command_surface != sorted_unique(ControllerCommandKind::ALL) {
            return Err("controller command surface is not the exact runtime registry".to_string());
        }
        validate_sorted_unique(&self.state_facing_fallbacks, "state_facing_fallbacks")?;
        if self.capabilities.is_empty() || self.capabilities.len() > MAX_CAPABILITIES {
            return Err("capability count is outside the bounded manifest range".to_string());
        }

        let mut ids = BTreeMap::new();
        let mut previous_id: Option<&str> = None;
        for entry in &self.capabilities {
            validate_id(&entry.id)?;
            if previous_id.is_some_and(|previous| previous >= entry.id.as_str()) {
                return Err("capability entries must be strictly ID-sorted".to_string());
            }
            previous_id = Some(&entry.id);
            if ids.insert(entry.id.as_str(), entry).is_some() {
                return Err("capability IDs must be globally unique".to_string());
            }
            validate_entry(entry)?;
        }

        validate_feeling_entries(&ids, &self.feelings)?;
        validate_controller_command_coverage(&self.capabilities, &self.controller_command_surface)?;
        validate_fallback_topology(&ids)?;
        validate_pose_alias_target_consistency(&ids)?;
        validate_state_facing_fallbacks(&ids, &self.state_facing_fallbacks)?;
        validate_safe_idle_profile(&self.safe_idle, &ids, &self.state_facing_fallbacks)?;
        let expected = build_unvalidated_wizard_capability_manifest()?;
        if self != &expected {
            return Err(
                "capability manifest differs from the exact loaded runtime registries".to_string(),
            );
        }
        Ok(())
    }

    fn validate_header(&self) -> Result<(), String> {
        if self.schema_version != CAPABILITY_MANIFEST_SCHEMA_VERSION {
            return Err(format!(
                "unsupported capability manifest schema {}",
                self.schema_version
            ));
        }
        let runtime_character_id = WizardState::default().character_id;
        if self.character_id != runtime_character_id {
            return Err(format!(
                "character_id must match WizardState::default ({runtime_character_id})"
            ));
        }
        validate_id(&self.character_id)?;
        self.versions.validate()?;
        if self.imported_pose_asset_schema_version != IMPORTED_POSE_SCHEMA_VERSION {
            return Err("imported pose schema version drift".to_string());
        }
        if self.motion_graph_schema_version != MOTION_GRAPH_SCHEMA_VERSION {
            return Err("motion graph schema version drift".to_string());
        }
        validate_sha256(
            &self.imported_pose_archive_sha256,
            "imported_pose_archive_sha256",
        )?;
        validate_sha256(
            &self.runtime_geometry_authority_sha256,
            "runtime_geometry_authority_sha256",
        )?;
        validate_sha256(&self.motion_graph_sha256, "motion_graph_sha256")?;
        if self.pose_geometry_count != REQUIRED_RUNTIME_GEOMETRY_COUNT
            || self.pose_alias_count != REQUIRED_POSE_ALIAS_COUNT
        {
            return Err(format!(
                "runtime pose authority must contain {REQUIRED_RUNTIME_GEOMETRY_COUNT} geometries and {REQUIRED_POSE_ALIAS_COUNT} alias"
            ));
        }
        if self.support.deterministic_media_scores
            || self.support.authored_dance
            || self.support.rendered_gaze
            || self.support.timed_visemes
        {
            return Err("unsupported runtime support flag was promoted".to_string());
        }
        Ok(())
    }

    pub fn canonical_json(&self) -> Result<Vec<u8>, String> {
        self.validate()?;
        serde_json::to_vec(self)
            .map_err(|error| format!("failed to serialize capability manifest: {error}"))
    }

    pub fn sha256(&self) -> Result<String, String> {
        Ok(format!("{:x}", Sha256::digest(self.canonical_json()?)))
    }
}

impl RuntimeVersionsV1 {
    fn validate(&self) -> Result<(), String> {
        let expected = Self::current();
        if self != &expected {
            return Err("runtime profile/policy/transport/event versions drifted".to_string());
        }
        Ok(())
    }

    fn current() -> Self {
        Self {
            capability_api_version: CAPABILITY_API_VERSION,
            runtime_profile: RuntimeProfileV1::Legacy,
            runtime_profile_version: RUNTIME_PROFILE_VERSION,
            runtime_policy: RuntimePolicyV1::LegacyController,
            runtime_policy_version: RUNTIME_POLICY_VERSION,
            runtime_transport: RuntimeTransportV1::AxumHttpWebSocketAdaptiveCodec,
            runtime_transport_version: RUNTIME_TRANSPORT_VERSION,
            command_schema_version: COMMAND_SCHEMA_VERSION,
            chat_event_schema_version: CHAT_EVENT_SCHEMA_VERSION,
            chat_performance_schema_version: CHAT_PERFORMANCE_SCHEMA_VERSION,
            duration_fallback_policy_version: DURATION_FALLBACK_VERSION,
        }
    }
}

fn build_unvalidated_wizard_capability_manifest() -> Result<CapabilityManifestV1, String> {
    let library = PoseLibrary::reference()?;
    let imported = load_embedded_pose_library()?;
    let catalog = shadow_motion_catalog()?;
    let graph = &catalog.graph;
    let coverage = graph
        .pose_coverage
        .iter()
        .map(|row| (row.pose_id.as_str(), row))
        .collect::<BTreeMap<_, _>>();
    if coverage.len() != library.pose_ids().count() {
        return Err("motion graph pose coverage is not a one-to-one runtime join".to_string());
    }

    let legacy_pose_ids = POSE_CLIPS
        .iter()
        .flat_map(|clip| clip.steps.iter().map(|step| step.pose_id))
        .collect::<BTreeSet<_>>();
    let directional_pose_ids = Direction::ALL
        .into_iter()
        .map(|facing| {
            let state = WizardState {
                facing,
                ..WizardState::default()
            };
            reference_pose_id_for_state(&state)
        })
        .collect::<BTreeSet<_>>();

    let mut capabilities = Vec::new();
    for pose_id in library.pose_ids() {
        let pose = library
            .for_id(pose_id)
            .ok_or_else(|| format!("runtime pose authority lost {pose_id}"))?;
        let graph_coverage = coverage
            .get(pose_id)
            .copied()
            .ok_or_else(|| format!("motion graph has no coverage row for {pose_id}"))?;
        capabilities.push(pose_entry(
            pose,
            graph_coverage,
            legacy_pose_ids.contains(pose_id),
            directional_pose_ids.contains(pose_id),
        ));
    }
    for (alias_id, target_pose_id) in &imported.aliases {
        let target = library
            .for_id(target_pose_id)
            .ok_or_else(|| format!("runtime alias {alias_id} lost target {target_pose_id}"))?;
        capabilities.push(pose_alias_entry(alias_id, target_pose_id, target));
    }
    capabilities.extend(
        POSE_CLIPS
            .iter()
            .map(|clip| legacy_clip_entry(clip, library))
            .collect::<Result<Vec<_>, _>>()?,
    );
    for clip in &graph.clips {
        capabilities.push(motion_clip_entry(clip, graph, library)?);
    }
    capabilities.extend(expression_entries());
    capabilities.extend(mouth_entries()?);
    capabilities.extend(shadow_semantic_entries()?);
    capabilities.extend(procedural_entries()?);
    capabilities.sort_by(|left, right| left.id.cmp(&right.id));

    let mut state_facing_fallbacks = graph
        .state_facing_fallbacks
        .iter()
        .map(|fallback| StateFacingFallbackV1 {
            turn_state: fallback.turn_state,
            requested_facing: fallback.requested_facing,
            fallback_pose_id: fallback.fallback_pose_id.clone(),
        })
        .collect::<Vec<_>>();
    state_facing_fallbacks.sort();

    let manifest = CapabilityManifestV1 {
        schema_version: CAPABILITY_MANIFEST_SCHEMA_VERSION,
        character_id: WizardState::default().character_id,
        versions: RuntimeVersionsV1::current(),
        imported_pose_asset_schema_version: IMPORTED_POSE_SCHEMA_VERSION,
        imported_pose_archive_sha256: embedded_pose_archive_sha256().to_string(),
        runtime_geometry_authority_sha256: runtime_geometry_authority_sha256(library)?,
        pose_geometry_count: library.pose_ids().count(),
        pose_alias_count: library.alias_count(),
        motion_graph_schema_version: graph.schema_version,
        motion_graph_sha256: EMBEDDED_MOTION_GRAPH_SHA256.to_string(),
        feelings: non_neutral_emotions(),
        controller_command_surface: sorted_unique(ControllerCommandKind::ALL),
        state_facing_fallbacks,
        safe_idle: RuntimeSafeIdleProfileV1 {
            idle_turn_state: ChatTurnState::Idle,
            stop_behavior_id: "behavior.stop".to_string(),
            neutral_expression_id: "expression.neutral".to_string(),
            rest_mouth_pose_id: "mouth.closed".to_string(),
            preserve_mode: true,
            preserve_root_position: true,
            preserve_facing: true,
            clear_gesture: true,
            clear_gaze_override: true,
            clear_viseme_override: true,
            clear_blink_override: true,
            clear_prop_effects: true,
            settle_secondary_motion: true,
        },
        support: RuntimeSupportFlagsV1 {
            deterministic_media_scores: false,
            authored_dance: false,
            rendered_gaze: false,
            timed_visemes: false,
        },
        capabilities,
    };
    Ok(manifest)
}

pub fn build_wizard_capability_manifest() -> Result<CapabilityManifestV1, String> {
    let manifest = build_unvalidated_wizard_capability_manifest()?;
    manifest.validate()?;
    Ok(manifest)
}

pub fn build_wizard_capability_document() -> Result<CapabilityDocumentV1, String> {
    let manifest = build_wizard_capability_manifest()?;
    let document = CapabilityDocumentV1 {
        manifest_sha256: manifest.sha256()?,
        manifest,
    };
    document.validate()?;
    Ok(document)
}

pub fn wizard_capability_document() -> Result<&'static CapabilityDocumentV1, String> {
    CAPABILITY_DOCUMENT
        .get_or_init(build_wizard_capability_document)
        .as_ref()
        .map_err(Clone::clone)
}

fn pose_entry(
    pose: &PoseDefinition,
    coverage: &crate::motion_graph::PoseCoverage,
    legacy_clip: bool,
    directional_controller: bool,
) -> CapabilityEntryV1 {
    let showcase_approval =
        coverage
            .showcase_approval
            .as_ref()
            .map(|approval| ShowcaseApprovalV1 {
                owner: approval.owner.clone(),
                rationale: approval.rationale.clone(),
                fallback_pose_id: approval.fallback_pose_id.clone(),
            });
    let status = match coverage.capability_tier {
        CapabilityTier::DirectionalBase => CapabilityStatus::ActiveLegacy,
        CapabilityTier::ShowcaseOnly => CapabilityStatus::ShowcaseOnly,
        CapabilityTier::FrontPerformance
        | CapabilityTier::DiagonalFlight
        | CapabilityTier::FaceAccent => CapabilityStatus::ShadowValidated,
    };
    let mut runtime_surfaces = vec![
        RuntimeSurfaceV1::DirectPoseCommand,
        RuntimeSurfaceV1::ShadowMotionGraph,
    ];
    if legacy_clip {
        runtime_surfaces.push(RuntimeSurfaceV1::LegacyPoseClip);
    }
    if directional_controller {
        runtime_surfaces.push(RuntimeSurfaceV1::DirectionalController);
    }
    runtime_surfaces.sort();
    let props = pose_prop_requirements(pose);
    let fallback = showcase_approval
        .as_ref()
        .map_or(FallbackTopologyV1::Terminal, |approval| {
            FallbackTopologyV1::Fallbacks(vec![approval.fallback_pose_id.clone()])
        });
    CapabilityEntryV1 {
        id: pose.id.clone(),
        kind: CapabilityKind::Pose,
        status,
        category: CapabilityCategoryV1::PoseFamily(pose_family(pose.motion.family)),
        emotional_uses: ApplicabilityV1::NotApplicable,
        energy: pose_family_energy(pose.motion.family),
        directions: vec![pose.direction],
        duration: None,
        loop_behavior: LoopBehaviorV1::NotApplicable,
        interruptibility: InterruptibilityV1::RawPoseReplace,
        valid_entry_states: ApplicabilityV1::NotApplicable,
        valid_exit_states: ApplicabilityV1::NotApplicable,
        face_policy: FacePolicyV1::LegacyOverlay,
        compatible_face_states: applicable(Expression::ALL),
        compatible_locomotion_states: applicable(Locomotion::ALL),
        compatible_motion_profiles: Vec::new(),
        controller_commands: applicable([ControllerCommandKind::Pose]),
        runtime_surfaces,
        prop_requirements: props,
        runtime_cost: RuntimeCostV1::BoundedCellProjection,
        quality_status: if coverage.capability_tier == CapabilityTier::ShowcaseOnly {
            QualityStatusV1::ShowcaseApprovedNotGeneralPurpose
        } else {
            QualityStatusV1::RuntimeGeometryValidated
        },
        pose_coverage: Some(PoseCoverageV1 {
            use_kinds: sorted_unique(coverage.use_kinds.iter().copied()),
            capability_tier: coverage.capability_tier,
            approved_facings: sorted_unique(coverage.approved_facings.iter().copied()),
            showcase_approval,
        }),
        pose_alias: None,
        transition_limitations: applicable([TransitionLimitationV1::RawPoseBypassesSemanticPolicy]),
        narrative_uses: applicable(pose_family_narrative_uses(pose.motion.family)),
        inappropriate_uses: applicable([InappropriateUseV1::UnconstrainedModelDirectSelection]),
        fallback,
    }
}

fn pose_alias_entry(
    alias_id: &str,
    target_pose_id: &str,
    target: &PoseDefinition,
) -> CapabilityEntryV1 {
    CapabilityEntryV1 {
        id: alias_id.to_string(),
        kind: CapabilityKind::PoseAlias,
        status: CapabilityStatus::ActiveLegacy,
        category: CapabilityCategoryV1::PoseAlias,
        emotional_uses: ApplicabilityV1::NotApplicable,
        energy: pose_family_energy(target.motion.family),
        directions: vec![target.direction],
        duration: None,
        loop_behavior: LoopBehaviorV1::NotApplicable,
        interruptibility: InterruptibilityV1::RawPoseReplace,
        valid_entry_states: ApplicabilityV1::NotApplicable,
        valid_exit_states: ApplicabilityV1::NotApplicable,
        face_policy: FacePolicyV1::LegacyOverlay,
        compatible_face_states: applicable(Expression::ALL),
        compatible_locomotion_states: applicable(Locomotion::ALL),
        compatible_motion_profiles: Vec::new(),
        controller_commands: applicable([ControllerCommandKind::Pose]),
        runtime_surfaces: vec![RuntimeSurfaceV1::DirectPoseCommand],
        prop_requirements: pose_prop_requirements(target),
        runtime_cost: RuntimeCostV1::BoundedCellProjection,
        quality_status: QualityStatusV1::RuntimeAliasValidated,
        pose_coverage: None,
        pose_alias: Some(PoseAliasV1 {
            target_pose_id: target_pose_id.to_string(),
        }),
        transition_limitations: applicable([TransitionLimitationV1::RawPoseBypassesSemanticPolicy]),
        narrative_uses: applicable(pose_family_narrative_uses(target.motion.family)),
        inappropriate_uses: applicable([InappropriateUseV1::UnconstrainedModelDirectSelection]),
        fallback: FallbackTopologyV1::Fallbacks(vec![target_pose_id.to_string()]),
    }
}

fn legacy_clip_entry(
    clip: &PoseClipDefinition,
    library: &PoseLibrary,
) -> Result<CapabilityEntryV1, String> {
    let directions = sorted_unique(
        clip.steps
            .iter()
            .filter_map(|step| library.for_id(step.pose_id).map(|pose| pose.direction)),
    );
    let staff_count = clip
        .steps
        .iter()
        .filter(|step| {
            library
                .for_id(step.pose_id)
                .is_some_and(|pose| pose.motion.staff_present)
        })
        .count();
    let effect_count = clip
        .steps
        .iter()
        .filter(|step| {
            library
                .for_id(step.pose_id)
                .is_some_and(|pose| pose.motion.effect_present)
        })
        .count();
    let mut props = Vec::new();
    props.extend(prop_coverage(
        PropRequirementV1::StaffAllSamples,
        PropRequirementV1::StaffSomeSamples,
        staff_count,
        clip.steps.len(),
    ));
    props.extend(prop_coverage(
        PropRequirementV1::EffectAllSamples,
        PropRequirementV1::EffectSomeSamples,
        effect_count,
        clip.steps.len(),
    ));
    props.sort();
    let category = legacy_clip_category(clip.id)?;
    Ok(CapabilityEntryV1 {
        id: clip.id.to_string(),
        kind: CapabilityKind::LegacyClip,
        status: CapabilityStatus::ActiveLegacy,
        category: CapabilityCategoryV1::LegacyClip(category),
        emotional_uses: applicability(legacy_clip_emotions(clip.id)),
        energy: legacy_clip_energy(category),
        directions,
        duration: Some(TickDurationV1 {
            nominal_ticks: clip
                .steps
                .iter()
                .map(|step| u32::from(step.hold_ticks))
                .sum(),
            repeats: clip.loopable,
        }),
        loop_behavior: if clip.loopable {
            LoopBehaviorV1::Repeat
        } else {
            LoopBehaviorV1::Once
        },
        interruptibility: InterruptibilityV1::LegacyGenerationReplace,
        valid_entry_states: ApplicabilityV1::NotApplicable,
        valid_exit_states: ApplicabilityV1::NotApplicable,
        face_policy: FacePolicyV1::LegacyOverlay,
        compatible_face_states: applicable(Expression::ALL),
        compatible_locomotion_states: applicable(Locomotion::ALL),
        compatible_motion_profiles: Vec::new(),
        controller_commands: applicable([ControllerCommandKind::PoseClip]),
        runtime_surfaces: vec![
            RuntimeSurfaceV1::LegacyPoseClip,
            RuntimeSurfaceV1::LegacyController,
        ],
        prop_requirements: props,
        runtime_cost: RuntimeCostV1::BoundedPoseSequence,
        quality_status: RuntimeCostV1::BoundedPoseSequence.into_quality(),
        pose_coverage: None,
        pose_alias: None,
        transition_limitations: applicable([TransitionLimitationV1::NotMarkerAwareMotionDirector]),
        narrative_uses: applicable(legacy_clip_narrative_uses(category)),
        inappropriate_uses: applicable([InappropriateUseV1::MediaTimeChoreographyWithoutScore]),
        fallback: FallbackTopologyV1::NotApplicable,
    })
}

fn motion_clip_entry(
    clip: &MotionClip,
    graph: &MotionGraphV1,
    library: &PoseLibrary,
) -> Result<CapabilityEntryV1, String> {
    let mut directions = BTreeSet::new();
    let mut staff_count = 0usize;
    let mut effect_count = 0usize;
    for sample in &clip.samples {
        let pose = library
            .for_id(&sample.pose_id)
            .ok_or_else(|| format!("motion clip {} lost pose {}", clip.clip_id, sample.pose_id))?;
        directions.insert(pose.direction);
        staff_count += usize::from(pose.motion.staff_present);
        effect_count += usize::from(pose.motion.effect_present);
    }
    let mut props = Vec::new();
    props.extend(prop_coverage(
        PropRequirementV1::StaffAllSamples,
        PropRequirementV1::StaffSomeSamples,
        staff_count,
        clip.samples.len(),
    ));
    props.extend(prop_coverage(
        PropRequirementV1::EffectAllSamples,
        PropRequirementV1::EffectSomeSamples,
        effect_count,
        clip.samples.len(),
    ));
    props.sort();
    let valid_entry_states = sorted_unique(
        graph
            .edges
            .iter()
            .filter(|edge| edge.target_clip_id == clip.clip_id)
            .flat_map(|edge| edge.allowed_turn_states.iter().copied())
            .chain(
                graph
                    .turn_state_profiles
                    .iter()
                    .filter(|profile| {
                        profile.entry_clip_id == clip.clip_id
                            || profile.stable_clip_id == clip.clip_id
                    })
                    .map(|profile| profile.turn_state),
            ),
    );
    let valid_exit_states = sorted_unique(
        graph
            .edges
            .iter()
            .filter(|edge| edge.source_clip_id == clip.clip_id)
            .flat_map(|edge| edge.allowed_turn_states.iter().copied()),
    );
    let fallback_ids: Vec<String> = clip
        .reduced_motion_clip_id
        .iter()
        .filter(|fallback| fallback.as_str() != clip.clip_id)
        .cloned()
        .collect();
    Ok(CapabilityEntryV1 {
        id: clip.clip_id.clone(),
        kind: CapabilityKind::MotionClip,
        status: CapabilityStatus::ShadowValidated,
        category: CapabilityCategoryV1::MotionClip(clip.family),
        emotional_uses: applicability(clip_family_emotions(clip.family)),
        energy: clip_family_energy(clip.family),
        directions: directions.into_iter().collect(),
        duration: Some(TickDurationV1 {
            nominal_ticks: clip
                .samples
                .iter()
                .map(|sample| u32::from(sample.hold_ticks))
                .sum(),
            repeats: clip.loop_mode != LoopMode::Once,
        }),
        loop_behavior: match clip.loop_mode {
            LoopMode::Once => LoopBehaviorV1::Once,
            LoopMode::Repeat => LoopBehaviorV1::Repeat,
            LoopMode::MarkedSegment => LoopBehaviorV1::MarkedSegment,
        },
        interruptibility: interruptibility(clip.interrupt_policy),
        valid_entry_states: applicability(valid_entry_states),
        valid_exit_states: applicability(valid_exit_states),
        face_policy: if clip
            .owned_channels
            .regions
            .contains(&crate::motion_graph::PerformanceRegion::FaceEmotion)
        {
            FacePolicyV1::OwnedByClip
        } else {
            FacePolicyV1::PreserveFaceRegion
        },
        compatible_face_states: if clip
            .owned_channels
            .regions
            .contains(&crate::motion_graph::PerformanceRegion::FaceEmotion)
        {
            ApplicabilityV1::NotApplicable
        } else {
            applicable(Expression::ALL)
        },
        compatible_locomotion_states: clip_family_locomotion_states(clip.family),
        compatible_motion_profiles: sorted_unique(
            graph
                .edges
                .iter()
                .filter(|edge| {
                    edge.source_clip_id == clip.clip_id || edge.target_clip_id == clip.clip_id
                })
                .flat_map(|edge| edge.allowed_motion_profiles.iter().copied()),
        ),
        controller_commands: ApplicabilityV1::NotApplicable,
        runtime_surfaces: vec![RuntimeSurfaceV1::ShadowMotionGraph],
        prop_requirements: props,
        runtime_cost: RuntimeCostV1::BoundedMarkerTimeline,
        quality_status: QualityStatusV1::ShadowValidatedNotRuntimeWired,
        pose_coverage: None,
        pose_alias: None,
        transition_limitations: applicable([TransitionLimitationV1::NotProductionControllerWired]),
        narrative_uses: applicable(clip_family_narrative_uses(clip.family)),
        inappropriate_uses: applicable([InappropriateUseV1::AdvertisingAsRuntimeBeforeWiring]),
        fallback: if fallback_ids.is_empty() {
            FallbackTopologyV1::Terminal
        } else {
            FallbackTopologyV1::Fallbacks(fallback_ids)
        },
    })
}

fn expression_entries() -> Vec<CapabilityEntryV1> {
    Expression::ALL
        .into_iter()
        .map(|expression| {
            let mut entry = simple_entry(
                format!("expression.{}", expression.as_str()),
                CapabilityKind::Expression,
                CapabilityStatus::ActiveLegacy,
                CapabilityCategoryV1::FaceExpression,
                20,
                simple_runtime(
                    RuntimeSurfaceV1::LegacyController,
                    QualityStatusV1::RuntimeRendered,
                    Some(ControllerCommandKind::Expression),
                ),
            );
            entry.compatible_face_states = applicable([expression]);
            entry
        })
        .collect()
}

fn mouth_entries() -> Result<Vec<CapabilityEntryV1>, String> {
    RenderedMouthPose::ALL
        .into_iter()
        .map(|mouth| {
            Ok(simple_entry(
                format!("mouth.{}", enum_wire_name(mouth, "mouth pose")?),
                CapabilityKind::MouthPose,
                CapabilityStatus::ActiveLegacy,
                CapabilityCategoryV1::MouthPose,
                15,
                simple_runtime(
                    RuntimeSurfaceV1::LegacyController,
                    QualityStatusV1::RuntimeRenderedDurationDriven,
                    Some(ControllerCommandKind::Mouth),
                ),
            ))
        })
        .collect()
}

fn shadow_semantic_entries() -> Result<Vec<CapabilityEntryV1>, String> {
    let mut entries = Vec::new();
    for state in ChatTurnState::ALL {
        let mut entry = simple_shadow_entry(
            format!("chat_state.{}", enum_wire_name(state, "chat state")?),
            CapabilityKind::ChatState,
            CapabilityCategoryV1::ChatState,
        );
        entry.valid_entry_states = applicable([state]);
        entry.valid_exit_states = applicable([state]);
        entries.push(entry);
    }
    for emotion in non_neutral_emotions() {
        let mut entry = simple_shadow_entry(
            format!("emotion.{}", enum_wire_name(emotion, "emotion")?),
            CapabilityKind::Emotion,
            CapabilityCategoryV1::EmotionIntent,
        );
        entry.emotional_uses = applicable([emotion]);
        entries.push(entry);
    }
    for gesture in GestureKind::ALL {
        entries.push(simple_shadow_entry(
            format!("gesture.{}", enum_wire_name(gesture, "gesture")?),
            CapabilityKind::GestureIntent,
            CapabilityCategoryV1::GestureIntent,
        ));
    }
    for target in AttentionTarget::ALL {
        entries.push(simple_shadow_entry(
            format!("gaze.{}", enum_wire_name(target, "attention target")?),
            CapabilityKind::GazeIntent,
            CapabilityCategoryV1::GazeIntent,
        ));
    }
    for viseme in Viseme::ALL {
        entries.push(simple_shadow_entry(
            format!("viseme.{}", enum_wire_name(viseme, "viseme")?),
            CapabilityKind::VisemeIntent,
            CapabilityCategoryV1::VisemeIntent,
        ));
    }
    Ok(entries)
}

fn procedural_entries() -> Result<Vec<CapabilityEntryV1>, String> {
    let mut entries = PROCEDURAL_CONTROLLER_COMMANDS
        .into_iter()
        .map(procedural_command_entry)
        .collect::<Result<Vec<_>, _>>()?;
    entries.push(simple_entry(
        "behavior.action".to_string(),
        CapabilityKind::ProceduralBehavior,
        CapabilityStatus::ActiveLegacy,
        CapabilityCategoryV1::ControllerControl,
        60,
        simple_runtime(
            RuntimeSurfaceV1::LegacyController,
            QualityStatusV1::RuntimeActiveLegacy,
            Some(ControllerCommandKind::Action),
        ),
    ));
    entries.push(simple_entry(
        "behavior.speaking_duration".to_string(),
        CapabilityKind::ProceduralBehavior,
        CapabilityStatus::ActiveLegacy,
        CapabilityCategoryV1::SpeechFallback,
        25,
        simple_runtime(
            RuntimeSurfaceV1::LegacyController,
            QualityStatusV1::RuntimeActiveLegacy,
            Some(ControllerCommandKind::Speak),
        ),
    ));
    entries.push(simple_entry(
        "behavior.periodic_blink".to_string(),
        CapabilityKind::ProceduralBehavior,
        CapabilityStatus::ActiveLegacy,
        CapabilityCategoryV1::BlinkFallback,
        5,
        simple_runtime(
            RuntimeSurfaceV1::LegacyController,
            QualityStatusV1::RuntimeActiveLegacy,
            None,
        ),
    ));
    Ok(entries)
}

fn procedural_command_entry(command: ControllerCommandKind) -> Result<CapabilityEntryV1, String> {
    let (id, category, energy) = match command {
        ControllerCommandKind::Move => ("behavior.move", CapabilityCategoryV1::RootMotion, 35),
        ControllerCommandKind::MoveRelative => (
            "behavior.move_relative",
            CapabilityCategoryV1::RootMotion,
            35,
        ),
        ControllerCommandKind::Path => ("behavior.path", CapabilityCategoryV1::PathMotion, 45),
        ControllerCommandKind::Circle => ("behavior.circle", CapabilityCategoryV1::PathMotion, 45),
        ControllerCommandKind::FigureEight => (
            "behavior.figure_eight",
            CapabilityCategoryV1::PathMotion,
            50,
        ),
        ControllerCommandKind::Face => ("behavior.face", CapabilityCategoryV1::FacingControl, 10),
        ControllerCommandKind::Stop => {
            ("behavior.stop", CapabilityCategoryV1::ControllerControl, 5)
        }
        ControllerCommandKind::Reset => {
            ("behavior.reset", CapabilityCategoryV1::ControllerControl, 5)
        }
        ControllerCommandKind::ReturnToCenter => (
            "behavior.return_to_center",
            CapabilityCategoryV1::RootMotion,
            35,
        ),
        ControllerCommandKind::WalkLeft => {
            ("behavior.walk_left", CapabilityCategoryV1::RootMotion, 40)
        }
        ControllerCommandKind::WalkRight => {
            ("behavior.walk_right", CapabilityCategoryV1::RootMotion, 40)
        }
        ControllerCommandKind::WalkForward => (
            "behavior.walk_forward",
            CapabilityCategoryV1::RootMotion,
            40,
        ),
        ControllerCommandKind::WalkBackward => (
            "behavior.walk_backward",
            CapabilityCategoryV1::RootMotion,
            40,
        ),
        _ => {
            return Err(format!(
                "unclassified procedural controller command {command:?}"
            ))
        }
    };
    Ok(simple_entry(
        id.to_string(),
        CapabilityKind::ProceduralBehavior,
        CapabilityStatus::ActiveLegacy,
        category,
        energy,
        simple_runtime(
            RuntimeSurfaceV1::LegacyController,
            QualityStatusV1::RuntimeActiveLegacy,
            Some(command),
        ),
    ))
}

struct SimpleRuntimeMetadata {
    surface: RuntimeSurfaceV1,
    quality_status: QualityStatusV1,
    controller_command: Option<ControllerCommandKind>,
}

fn simple_runtime(
    surface: RuntimeSurfaceV1,
    quality_status: QualityStatusV1,
    controller_command: Option<ControllerCommandKind>,
) -> SimpleRuntimeMetadata {
    SimpleRuntimeMetadata {
        surface,
        quality_status,
        controller_command,
    }
}

fn simple_entry(
    id: String,
    kind: CapabilityKind,
    status: CapabilityStatus,
    category: CapabilityCategoryV1,
    energy: u8,
    runtime: SimpleRuntimeMetadata,
) -> CapabilityEntryV1 {
    CapabilityEntryV1 {
        id,
        kind,
        status,
        category,
        emotional_uses: ApplicabilityV1::NotApplicable,
        energy,
        directions: Vec::new(),
        duration: None,
        loop_behavior: LoopBehaviorV1::StateDriven,
        interruptibility: InterruptibilityV1::Immediate,
        valid_entry_states: ApplicabilityV1::NotApplicable,
        valid_exit_states: ApplicabilityV1::NotApplicable,
        face_policy: FacePolicyV1::LegacyOverlay,
        compatible_face_states: applicable(Expression::ALL),
        compatible_locomotion_states: applicable(Locomotion::ALL),
        compatible_motion_profiles: Vec::new(),
        controller_commands: runtime
            .controller_command
            .map(|command| applicable([command]))
            .unwrap_or(ApplicabilityV1::NotApplicable),
        runtime_surfaces: vec![runtime.surface],
        prop_requirements: Vec::new(),
        runtime_cost: RuntimeCostV1::ConstantTimeStateUpdate,
        quality_status: runtime.quality_status,
        pose_coverage: None,
        pose_alias: None,
        transition_limitations: ApplicabilityV1::NotApplicable,
        narrative_uses: ApplicabilityV1::NotApplicable,
        inappropriate_uses: ApplicabilityV1::NotApplicable,
        fallback: FallbackTopologyV1::NotApplicable,
    }
}

fn simple_shadow_entry(
    id: String,
    kind: CapabilityKind,
    category: CapabilityCategoryV1,
) -> CapabilityEntryV1 {
    CapabilityEntryV1 {
        id,
        kind,
        status: CapabilityStatus::ShadowValidated,
        category,
        emotional_uses: ApplicabilityV1::NotApplicable,
        energy: 25,
        directions: Vec::new(),
        duration: None,
        loop_behavior: LoopBehaviorV1::EventDriven,
        interruptibility: InterruptibilityV1::ContractDefined,
        valid_entry_states: ApplicabilityV1::NotApplicable,
        valid_exit_states: ApplicabilityV1::NotApplicable,
        face_policy: FacePolicyV1::ContractOnlyNotRendered,
        compatible_face_states: ApplicabilityV1::NotApplicable,
        compatible_locomotion_states: ApplicabilityV1::NotApplicable,
        compatible_motion_profiles: Vec::new(),
        controller_commands: ApplicabilityV1::NotApplicable,
        runtime_surfaces: vec![RuntimeSurfaceV1::TypedChatContract],
        prop_requirements: Vec::new(),
        runtime_cost: RuntimeCostV1::NotMeasuredUntilRuntimeWiring,
        quality_status: QualityStatusV1::ContractValidatedNotRuntimeRendered,
        pose_coverage: None,
        pose_alias: None,
        transition_limitations: applicable([
            TransitionLimitationV1::NotConsumedByProductionRenderer,
        ]),
        narrative_uses: ApplicabilityV1::NotApplicable,
        inappropriate_uses: applicable([InappropriateUseV1::AdvertisingAsVisiblyImplemented]),
        fallback: FallbackTopologyV1::NotApplicable,
    }
}

fn validate_entry(entry: &CapabilityEntryV1) -> Result<(), String> {
    if entry.energy > 100 {
        return Err(format!("{} energy exceeds 100", entry.id));
    }
    validate_applicability(&entry.emotional_uses, "emotional_uses")?;
    validate_sorted_unique(&entry.directions, "directions")?;
    validate_applicability(&entry.valid_entry_states, "valid_entry_states")?;
    validate_applicability(&entry.valid_exit_states, "valid_exit_states")?;
    validate_applicability(&entry.compatible_face_states, "compatible_face_states")?;
    validate_applicability(
        &entry.compatible_locomotion_states,
        "compatible_locomotion_states",
    )?;
    validate_sorted_unique(
        &entry.compatible_motion_profiles,
        "compatible_motion_profiles",
    )?;
    validate_applicability(&entry.controller_commands, "controller_commands")?;
    validate_sorted_unique(&entry.runtime_surfaces, "runtime_surfaces")?;
    validate_sorted_unique(&entry.prop_requirements, "prop_requirements")?;
    validate_applicability(&entry.transition_limitations, "transition_limitations")?;
    validate_applicability(&entry.narrative_uses, "narrative_uses")?;
    validate_applicability(&entry.inappropriate_uses, "inappropriate_uses")?;
    if let FallbackTopologyV1::Fallbacks(ids) = &entry.fallback {
        if ids.is_empty() {
            return Err(format!("{} has an empty applicable fallback", entry.id));
        }
        validate_ids(ids, "fallback")?;
    }
    if let Some(duration) = &entry.duration {
        if duration.nominal_ticks == 0 || duration.nominal_ticks > MAX_TICK_DURATION {
            return Err(format!("{} has invalid nominal duration", entry.id));
        }
        if duration.repeats
            != matches!(
                entry.loop_behavior,
                LoopBehaviorV1::Repeat | LoopBehaviorV1::MarkedSegment
            )
        {
            return Err(format!(
                "{} repeat duration disagrees with loop behavior",
                entry.id
            ));
        }
    } else if matches!(
        entry.kind,
        CapabilityKind::LegacyClip | CapabilityKind::MotionClip
    ) {
        return Err(format!("{} clip is missing a duration", entry.id));
    }

    match entry.kind {
        CapabilityKind::Pose => validate_pose_entry(entry),
        CapabilityKind::PoseAlias => validate_pose_alias_entry(entry),
        CapabilityKind::LegacyClip
        | CapabilityKind::Expression
        | CapabilityKind::MouthPose
        | CapabilityKind::ProceduralBehavior => {
            if entry.status != CapabilityStatus::ActiveLegacy
                || entry.pose_coverage.is_some()
                || entry.pose_alias.is_some()
            {
                return Err(format!("{} has an invalid active legacy status", entry.id));
            }
            Ok(())
        }
        CapabilityKind::MotionClip
        | CapabilityKind::ChatState
        | CapabilityKind::Emotion
        | CapabilityKind::GestureIntent
        | CapabilityKind::GazeIntent
        | CapabilityKind::VisemeIntent => {
            if entry.status != CapabilityStatus::ShadowValidated
                || entry.pose_coverage.is_some()
                || entry.pose_alias.is_some()
            {
                return Err(format!("{} has an invalid shadow status", entry.id));
            }
            Ok(())
        }
    }
}

fn validate_pose_alias_entry(entry: &CapabilityEntryV1) -> Result<(), String> {
    if entry.status != CapabilityStatus::ActiveLegacy || entry.pose_coverage.is_some() {
        return Err(format!("{} has invalid alias status/coverage", entry.id));
    }
    let alias = entry
        .pose_alias
        .as_ref()
        .ok_or_else(|| format!("{} alias is missing its target", entry.id))?;
    validate_id(&alias.target_pose_id)?;
    if fallback_ids(entry) != [alias.target_pose_id.as_str()] {
        return Err(format!(
            "{} alias fallback does not match its target",
            entry.id
        ));
    }
    Ok(())
}

fn validate_pose_entry(entry: &CapabilityEntryV1) -> Result<(), String> {
    if entry.pose_alias.is_some() {
        return Err(format!("{} pose cannot also be an alias", entry.id));
    }
    let coverage = entry
        .pose_coverage
        .as_ref()
        .ok_or_else(|| format!("{} pose is missing graph coverage", entry.id))?;
    validate_sorted_unique(&coverage.use_kinds, "pose use_kinds")?;
    validate_sorted_unique(&coverage.approved_facings, "approved_facings")?;
    if coverage.approved_facings.is_empty() {
        return Err(format!("{} has no approved facing", entry.id));
    }
    if !entry
        .directions
        .iter()
        .all(|facing| coverage.approved_facings.contains(facing))
    {
        return Err(format!("{} authored facing is not approved", entry.id));
    }
    let expected_status = match coverage.capability_tier {
        CapabilityTier::DirectionalBase => CapabilityStatus::ActiveLegacy,
        CapabilityTier::ShowcaseOnly => CapabilityStatus::ShowcaseOnly,
        CapabilityTier::FrontPerformance
        | CapabilityTier::DiagonalFlight
        | CapabilityTier::FaceAccent => CapabilityStatus::ShadowValidated,
    };
    if entry.status != expected_status {
        return Err(format!(
            "{} status disagrees with runtime surfaces/tier",
            entry.id
        ));
    }
    if !entry
        .runtime_surfaces
        .contains(&RuntimeSurfaceV1::DirectPoseCommand)
        || !entry
            .runtime_surfaces
            .contains(&RuntimeSurfaceV1::ShadowMotionGraph)
    {
        return Err(format!("{} omits a factual pose runtime surface", entry.id));
    }
    match (&coverage.capability_tier, &coverage.showcase_approval) {
        (CapabilityTier::ShowcaseOnly, Some(approval)) => {
            validate_text(&approval.owner, "showcase owner")?;
            validate_text(&approval.rationale, "showcase rationale")?;
            validate_id(&approval.fallback_pose_id)?;
            if fallback_ids(entry) != [approval.fallback_pose_id.as_str()] {
                return Err(format!("{} lost its showcase fallback", entry.id));
            }
        }
        (CapabilityTier::ShowcaseOnly, None) => {
            return Err(format!("{} showcase pose lacks approval", entry.id));
        }
        (_, Some(_)) => {
            return Err(format!(
                "{} non-showcase pose has showcase approval",
                entry.id
            ))
        }
        (_, None) => {
            if entry.fallback != FallbackTopologyV1::Terminal {
                return Err(format!("{} non-showcase pose must be terminal", entry.id));
            }
        }
    }
    Ok(())
}

fn validate_feeling_entries(
    ids: &BTreeMap<&str, &CapabilityEntryV1>,
    feelings: &[Emotion],
) -> Result<(), String> {
    let expected = feelings
        .iter()
        .map(|emotion| enum_wire_name(*emotion, "emotion").map(|name| format!("emotion.{name}")))
        .collect::<Result<BTreeSet<_>, _>>()?;
    let actual = ids
        .values()
        .filter(|entry| entry.kind == CapabilityKind::Emotion)
        .map(|entry| entry.id.clone())
        .collect::<BTreeSet<_>>();
    if actual != expected {
        return Err("emotion capabilities do not match the ten feelings".to_string());
    }
    Ok(())
}

fn validate_controller_command_coverage(
    capabilities: &[CapabilityEntryV1],
    command_surface: &[ControllerCommandKind],
) -> Result<(), String> {
    let advertised = sorted_unique(capabilities.iter().flat_map(|entry| {
        match &entry.controller_commands {
            ApplicabilityV1::Applicable(commands) => commands.as_slice(),
            ApplicabilityV1::NotApplicable => &[],
        }
        .iter()
        .copied()
    }));
    if advertised != command_surface {
        return Err(
            "capability entry commands do not cover the exact runtime command surface".to_string(),
        );
    }
    Ok(())
}

fn validate_pose_alias_target_consistency(
    ids: &BTreeMap<&str, &CapabilityEntryV1>,
) -> Result<(), String> {
    for alias in ids
        .values()
        .filter(|entry| entry.kind == CapabilityKind::PoseAlias)
    {
        let target_id = &alias
            .pose_alias
            .as_ref()
            .ok_or_else(|| format!("{} alias is missing its target", alias.id))?
            .target_pose_id;
        let target = ids
            .get(target_id.as_str())
            .ok_or_else(|| format!("{} alias lost target {target_id}", alias.id))?;
        if alias.emotional_uses != target.emotional_uses
            || alias.energy != target.energy
            || alias.directions != target.directions
            || alias.duration != target.duration
            || alias.loop_behavior != target.loop_behavior
            || alias.interruptibility != target.interruptibility
            || alias.valid_entry_states != target.valid_entry_states
            || alias.valid_exit_states != target.valid_exit_states
            || alias.face_policy != target.face_policy
            || alias.compatible_face_states != target.compatible_face_states
            || alias.compatible_locomotion_states != target.compatible_locomotion_states
            || alias.compatible_motion_profiles != target.compatible_motion_profiles
            || alias.controller_commands != target.controller_commands
            || alias.prop_requirements != target.prop_requirements
            || alias.runtime_cost != target.runtime_cost
            || alias.transition_limitations != target.transition_limitations
            || alias.narrative_uses != target.narrative_uses
            || alias.inappropriate_uses != target.inappropriate_uses
        {
            return Err(format!(
                "{} alias metadata differs from target {target_id}",
                alias.id
            ));
        }
    }
    Ok(())
}

fn validate_fallback_topology(ids: &BTreeMap<&str, &CapabilityEntryV1>) -> Result<(), String> {
    for entry in ids.values() {
        for fallback in fallback_ids(entry) {
            let target = ids
                .get(fallback)
                .ok_or_else(|| format!("{} has unresolved fallback {fallback}", entry.id))?;
            if fallback == entry.id {
                return Err(format!("{} has a self fallback", entry.id));
            }
            let valid_kind = if entry.kind == CapabilityKind::PoseAlias {
                target.kind == CapabilityKind::Pose
            } else {
                target.kind == entry.kind
            };
            if !valid_kind {
                return Err(format!(
                    "{} fallback {fallback} changes capability kind",
                    entry.id
                ));
            }
        }
    }
    let mut visited = BTreeSet::new();
    let mut visiting = BTreeSet::new();
    for id in ids.keys().copied() {
        validate_fallback_acyclic(id, ids, &mut visiting, &mut visited)?;
    }
    Ok(())
}

fn validate_fallback_acyclic<'a>(
    id: &'a str,
    ids: &BTreeMap<&'a str, &CapabilityEntryV1>,
    visiting: &mut BTreeSet<&'a str>,
    visited: &mut BTreeSet<&'a str>,
) -> Result<(), String> {
    if visited.contains(id) {
        return Ok(());
    }
    if !visiting.insert(id) {
        return Err(format!("{id} participates in a fallback cycle"));
    }
    let entry = ids
        .get(id)
        .ok_or_else(|| format!("fallback traversal lost {id}"))?;
    for fallback in fallback_ids(entry) {
        let (target_id, _) = ids
            .get_key_value(fallback)
            .ok_or_else(|| format!("{id} has unresolved fallback {fallback}"))?;
        validate_fallback_acyclic(target_id, ids, visiting, visited)?;
    }
    visiting.remove(id);
    visited.insert(id);
    Ok(())
}

fn fallback_ids(entry: &CapabilityEntryV1) -> Vec<&str> {
    match &entry.fallback {
        FallbackTopologyV1::Fallbacks(ids) => ids.iter().map(String::as_str).collect(),
        FallbackTopologyV1::NotApplicable | FallbackTopologyV1::Terminal => Vec::new(),
    }
}

fn pose_prop_requirements(pose: &PoseDefinition) -> Vec<PropRequirementV1> {
    let mut requirements = Vec::new();
    if pose.motion.staff_present {
        requirements.push(PropRequirementV1::StaffAllSamples);
    }
    if pose.motion.effect_present {
        requirements.push(PropRequirementV1::EffectAllSamples);
    }
    requirements
}

fn validate_state_facing_fallbacks(
    ids: &BTreeMap<&str, &CapabilityEntryV1>,
    fallbacks: &[StateFacingFallbackV1],
) -> Result<(), String> {
    let expected_pairs = ChatTurnState::ALL
        .into_iter()
        .flat_map(|state| {
            Direction::ALL
                .into_iter()
                .map(move |facing| (state, facing))
        })
        .collect::<BTreeSet<_>>();
    let actual_pairs = fallbacks
        .iter()
        .map(|fallback| (fallback.turn_state, fallback.requested_facing))
        .collect::<BTreeSet<_>>();
    if fallbacks.len() != expected_pairs.len() || actual_pairs != expected_pairs {
        return Err("state/facing fallbacks must cover the exact 10x8 topology".to_string());
    }
    for fallback in fallbacks {
        validate_id(&fallback.fallback_pose_id)?;
        let target = ids
            .get(fallback.fallback_pose_id.as_str())
            .ok_or_else(|| format!("state/facing fallback lost {}", fallback.fallback_pose_id))?;
        if target.kind != CapabilityKind::Pose {
            return Err("state/facing fallback target must be a pose".to_string());
        }
        let coverage = target
            .pose_coverage
            .as_ref()
            .ok_or_else(|| "state/facing fallback pose lacks coverage".to_string())?;
        if !coverage
            .approved_facings
            .contains(&fallback.requested_facing)
        {
            return Err(format!(
                "{} is not approved for {:?}",
                fallback.fallback_pose_id, fallback.requested_facing
            ));
        }
        if coverage.capability_tier == CapabilityTier::ShowcaseOnly {
            return Err("state/facing fallback cannot target showcase-only geometry".to_string());
        }
    }
    Ok(())
}

fn validate_safe_idle_profile(
    profile: &RuntimeSafeIdleProfileV1,
    ids: &BTreeMap<&str, &CapabilityEntryV1>,
    fallbacks: &[StateFacingFallbackV1],
) -> Result<(), String> {
    if profile.idle_turn_state != ChatTurnState::Idle {
        return Err("safe idle turn state must be idle".to_string());
    }
    if profile.stop_behavior_id != "behavior.stop"
        || profile.neutral_expression_id != "expression.neutral"
        || profile.rest_mouth_pose_id != "mouth.closed"
    {
        return Err("safe idle capability IDs must match the exact runtime policy".to_string());
    }
    if !profile.preserve_mode
        || !profile.preserve_root_position
        || !profile.preserve_facing
        || !profile.clear_gesture
        || !profile.clear_gaze_override
        || !profile.clear_viseme_override
        || !profile.clear_blink_override
        || !profile.clear_prop_effects
        || !profile.settle_secondary_motion
    {
        return Err("safe idle policy flags must match the exact runtime policy".to_string());
    }

    validate_safe_idle_reference(
        ids,
        &profile.stop_behavior_id,
        CapabilityKind::ProceduralBehavior,
        CapabilityCategoryV1::ControllerControl,
        ControllerCommandKind::Stop,
        "stop behavior",
    )?;
    validate_safe_idle_reference(
        ids,
        &profile.neutral_expression_id,
        CapabilityKind::Expression,
        CapabilityCategoryV1::FaceExpression,
        ControllerCommandKind::Expression,
        "neutral expression",
    )?;
    validate_safe_idle_reference(
        ids,
        &profile.rest_mouth_pose_id,
        CapabilityKind::MouthPose,
        CapabilityCategoryV1::MouthPose,
        ControllerCommandKind::Mouth,
        "rest mouth pose",
    )?;

    let expected_facings = Direction::ALL.into_iter().collect::<BTreeSet<_>>();
    let idle_rows = fallbacks
        .iter()
        .filter(|fallback| fallback.turn_state == profile.idle_turn_state)
        .collect::<Vec<_>>();
    let idle_facings = idle_rows
        .iter()
        .map(|fallback| fallback.requested_facing)
        .collect::<BTreeSet<_>>();
    if idle_rows.len() != Direction::ALL.len() || idle_facings != expected_facings {
        return Err("safe idle must resolve all eight facing fallbacks exactly once".to_string());
    }
    for fallback in idle_rows {
        let target = ids.get(fallback.fallback_pose_id.as_str()).ok_or_else(|| {
            format!(
                "safe idle fallback lost target {}",
                fallback.fallback_pose_id
            )
        })?;
        if target.kind != CapabilityKind::Pose || target.status != CapabilityStatus::ActiveLegacy {
            return Err(format!(
                "safe idle fallback {} is not an active pose",
                fallback.fallback_pose_id
            ));
        }
    }
    Ok(())
}

fn validate_safe_idle_reference(
    ids: &BTreeMap<&str, &CapabilityEntryV1>,
    id: &str,
    kind: CapabilityKind,
    category: CapabilityCategoryV1,
    command: ControllerCommandKind,
    label: &str,
) -> Result<(), String> {
    validate_id(id)?;
    let entry = ids
        .get(id)
        .ok_or_else(|| format!("safe idle {label} lost capability {id}"))?;
    if entry.kind != kind
        || entry.status != CapabilityStatus::ActiveLegacy
        || entry.category != category
        || entry.controller_commands != applicable([command])
    {
        return Err(format!(
            "safe idle {label} {id} has the wrong runtime contract"
        ));
    }
    Ok(())
}

fn runtime_geometry_authority_sha256(library: &PoseLibrary) -> Result<String, String> {
    let mut digest = Sha256::new();
    for pose_id in library.pose_ids() {
        let pose = library
            .for_id(pose_id)
            .ok_or_else(|| format!("runtime pose authority lost {pose_id}"))?;
        hash_text(&mut digest, &pose.id);
        hash_text(&mut digest, pose.direction.as_str());
        digest.update(pose.root.0.to_le_bytes());
        digest.update(pose.root.1.to_le_bytes());
        digest.update((pose.cols as u64).to_le_bytes());
        digest.update((pose.rows as u64).to_le_bytes());
        hash_text(&mut digest, pose_family_name(pose.motion.family));
        hash_text(&mut digest, contact_mode_name(pose.motion.contact_mode));
        match pose.motion.phase {
            Some(phase) => {
                digest.update([1]);
                digest.update(phase.to_bits().to_le_bytes());
            }
            None => digest.update([0]),
        }
        hash_text(
            &mut digest,
            pose.motion.candidate_id.as_deref().unwrap_or(""),
        );
        digest.update([u8::from(pose.motion.staff_present)]);
        digest.update([u8::from(pose.motion.effect_present)]);
        let mut neighbors = pose.motion.authored_transition_neighbors.clone();
        neighbors.sort();
        for neighbor in neighbors {
            hash_text(&mut digest, &neighbor);
        }
        for (anchor, point) in &pose.anchors {
            hash_serialized(&mut digest, anchor, "anchor")?;
            digest.update(point.x.to_bits().to_le_bytes());
            digest.update(point.y.to_bits().to_le_bytes());
        }
        for contact_set in &pose.motion.contact_sets {
            hash_text(&mut digest, &contact_set.id);
            for point in &contact_set.points {
                hash_serialized(&mut digest, &point.anchor, "contact anchor")?;
                hash_text(&mut digest, contact_kind_name(point.kind));
                digest.update(point.point.0.to_le_bytes());
                digest.update(point.point.1.to_le_bytes());
            }
        }
        for edge in &pose.motion.attachment_edges {
            hash_serialized(&mut digest, &edge.parent_region, "parent region")?;
            hash_serialized(&mut digest, &edge.child_region, "child region")?;
            hash_serialized(&mut digest, &edge.parent_anchor, "parent anchor")?;
            hash_serialized(&mut digest, &edge.child_anchor, "child anchor")?;
        }
        for region in &pose.z_order {
            hash_serialized(&mut digest, region, "z-order region")?;
        }
        let mut cells = pose.cells.iter().collect::<Vec<_>>();
        cells.sort_by_key(|cell| cell.stable_id);
        for cell in cells {
            digest.update(cell.stable_id.to_le_bytes());
            digest.update(cell.x.to_le_bytes());
            digest.update(cell.y.to_le_bytes());
            digest.update(cell.cell.to_bytes());
            hash_serialized(&mut digest, &cell.region, "cell region")?;
        }
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn validate_id(value: &str) -> Result<(), String> {
    if value.is_empty()
        || value.len() > MAX_ID_BYTES
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-' | b'.'))
    {
        return Err(format!("invalid capability identifier {value:?}"));
    }
    Ok(())
}

fn validate_ids(values: &[String], field: &str) -> Result<(), String> {
    if values.len() > MAX_TEXT_VALUES {
        return Err(format!("{field} exceeds {MAX_TEXT_VALUES} values"));
    }
    validate_sorted_unique(values, field)?;
    for value in values {
        validate_id(value)?;
    }
    Ok(())
}

fn validate_sha256(value: &str, field: &str) -> Result<(), String> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(format!("{field} must be a lowercase SHA-256"));
    }
    Ok(())
}

fn validate_text(value: &str, field: &str) -> Result<(), String> {
    if value.is_empty() || value.len() > MAX_TEXT_BYTES || value.chars().any(char::is_control) {
        return Err(format!("invalid {field} value"));
    }
    Ok(())
}

fn validate_sorted_unique<T: Ord>(values: &[T], field: &str) -> Result<(), String> {
    if values.windows(2).any(|pair| pair[0] >= pair[1]) {
        return Err(format!("{field} must be canonically sorted and unique"));
    }
    Ok(())
}

fn validate_applicability<T: Ord>(
    applicability: &ApplicabilityV1<T>,
    field: &str,
) -> Result<(), String> {
    match applicability {
        ApplicabilityV1::NotApplicable => Ok(()),
        ApplicabilityV1::Applicable(values) => {
            if values.is_empty() {
                return Err(format!("{field} is applicable but has no values"));
            }
            validate_sorted_unique(values, field)
        }
    }
}

fn sorted_unique<T: Ord>(values: impl IntoIterator<Item = T>) -> Vec<T> {
    values
        .into_iter()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}

fn applicable<T: Ord>(values: impl IntoIterator<Item = T>) -> ApplicabilityV1<T> {
    ApplicabilityV1::Applicable(sorted_unique(values))
}

fn applicability<T: Ord>(values: impl IntoIterator<Item = T>) -> ApplicabilityV1<T> {
    let values = sorted_unique(values);
    if values.is_empty() {
        ApplicabilityV1::NotApplicable
    } else {
        ApplicabilityV1::Applicable(values)
    }
}

fn non_neutral_emotions() -> Vec<Emotion> {
    Emotion::ALL
        .into_iter()
        .filter(|emotion| *emotion != Emotion::Neutral)
        .collect()
}

fn enum_wire_name<T: Serialize>(value: T, label: &str) -> Result<String, String> {
    let value = serde_json::to_value(value)
        .map_err(|error| format!("failed to serialize {label}: {error}"))?;
    value
        .as_str()
        .map(str::to_string)
        .ok_or_else(|| format!("{label} did not serialize as a string"))
}

fn hash_text(digest: &mut Sha256, value: &str) {
    digest.update((value.len() as u64).to_le_bytes());
    digest.update(value.as_bytes());
}

fn hash_serialized<T: Serialize>(
    digest: &mut Sha256,
    value: &T,
    label: &str,
) -> Result<(), String> {
    let bytes = serde_json::to_vec(value)
        .map_err(|error| format!("failed to serialize {label} for authority hash: {error}"))?;
    digest.update((bytes.len() as u64).to_le_bytes());
    digest.update(bytes);
    Ok(())
}

fn prop_coverage(
    all: PropRequirementV1,
    some: PropRequirementV1,
    count: usize,
    total: usize,
) -> Option<PropRequirementV1> {
    match count {
        0 => None,
        count if count == total => Some(all),
        _ => Some(some),
    }
}

impl RuntimeCostV1 {
    fn into_quality(self) -> QualityStatusV1 {
        match self {
            Self::BoundedPoseSequence => QualityStatusV1::RuntimeActiveUnscored,
            _ => QualityStatusV1::RuntimeActiveLegacy,
        }
    }
}

fn pose_family(family: PoseMotionFamily) -> PoseFamilyV1 {
    match family {
        PoseMotionFamily::Run => PoseFamilyV1::Run,
        PoseMotionFamily::Walk => PoseFamilyV1::Walk,
        PoseMotionFamily::Flight => PoseFamilyV1::Flight,
        PoseMotionFamily::Jump => PoseFamilyV1::Jump,
        PoseMotionFamily::Landing => PoseFamilyV1::Landing,
        PoseMotionFamily::GroundAction => PoseFamilyV1::GroundAction,
        PoseMotionFamily::Kneel => PoseFamilyV1::Kneel,
        PoseMotionFamily::Baseline => PoseFamilyV1::Baseline,
    }
}

fn pose_family_name(family: PoseMotionFamily) -> &'static str {
    match pose_family(family) {
        PoseFamilyV1::Run => "run",
        PoseFamilyV1::Walk => "walk",
        PoseFamilyV1::Flight => "flight",
        PoseFamilyV1::Jump => "jump",
        PoseFamilyV1::Landing => "landing",
        PoseFamilyV1::GroundAction => "ground_action",
        PoseFamilyV1::Kneel => "kneel",
        PoseFamilyV1::Baseline => "baseline",
    }
}

fn contact_mode_name(mode: crate::pose::PoseContactMode) -> &'static str {
    match mode {
        crate::pose::PoseContactMode::Airborne => "airborne",
        crate::pose::PoseContactMode::LeftFoot => "left_foot",
        crate::pose::PoseContactMode::RightFoot => "right_foot",
        crate::pose::PoseContactMode::BothFeet => "both_feet",
        crate::pose::PoseContactMode::BothFeetAndStaff => "both_feet_and_staff",
        crate::pose::PoseContactMode::KneelAndStaff => "kneel_and_staff",
        crate::pose::PoseContactMode::HandFootAndStaff => "hand_foot_and_staff",
    }
}

fn contact_kind_name(kind: crate::pose::PoseContactKind) -> &'static str {
    match kind {
        crate::pose::PoseContactKind::Ground => "ground",
        crate::pose::PoseContactKind::Brace => "brace",
    }
}

fn pose_family_energy(family: PoseMotionFamily) -> u8 {
    match family {
        PoseMotionFamily::Run => 80,
        PoseMotionFamily::Walk => 45,
        PoseMotionFamily::Flight => 70,
        PoseMotionFamily::Jump => 75,
        PoseMotionFamily::Landing => 60,
        PoseMotionFamily::GroundAction => 55,
        PoseMotionFamily::Kneel => 25,
        PoseMotionFamily::Baseline => 15,
    }
}

fn pose_family_narrative_uses(family: PoseMotionFamily) -> Vec<NarrativeUseV1> {
    let value = match family {
        PoseMotionFamily::Run => NarrativeUseV1::UrgentTravelOrAction,
        PoseMotionFamily::Walk => NarrativeUseV1::DeliberateStageTravel,
        PoseMotionFamily::Flight => NarrativeUseV1::AirborneStaging,
        PoseMotionFamily::Jump => NarrativeUseV1::AuthoredActionAccent,
        PoseMotionFamily::Landing => NarrativeUseV1::AuthoredRecoveryOrArrival,
        PoseMotionFamily::GroundAction => NarrativeUseV1::GroundedPerformanceAccent,
        PoseMotionFamily::Kneel => NarrativeUseV1::LowOrBracedStaging,
        PoseMotionFamily::Baseline => NarrativeUseV1::NeutralStagingAndDirectionalFallback,
    };
    vec![value]
}

fn legacy_clip_category(id: &str) -> Result<LegacyClipCategoryV1, String> {
    let category = match id {
        "ground_walk" | "ground_run" | "wjfl_run" => LegacyClipCategoryV1::GroundLocomotion,
        "hover_flap" | "bank_glide" => LegacyClipCategoryV1::FlightPoseSequence,
        "staff_combo" | "reaction_recover" | "wjfl_guard" | "wjfl_reaction" => {
            LegacyClipCategoryV1::Action
        }
        "celebrate" => LegacyClipCategoryV1::Celebration,
        "wjfl_feelings" => LegacyClipCategoryV1::EmotionShowcase,
        "conversation" | "explain" | "point" | "think" | "wjfl_social" => {
            LegacyClipCategoryV1::Conversation
        }
        _ => return Err(format!("unclassified legacy pose clip {id}")),
    };
    Ok(category)
}

fn legacy_clip_energy(category: LegacyClipCategoryV1) -> u8 {
    match category {
        LegacyClipCategoryV1::GroundLocomotion => 65,
        LegacyClipCategoryV1::FlightPoseSequence => 70,
        LegacyClipCategoryV1::Action => 75,
        LegacyClipCategoryV1::Celebration => 85,
        LegacyClipCategoryV1::Conversation => 40,
        LegacyClipCategoryV1::EmotionShowcase => 55,
    }
}

fn legacy_clip_emotions(id: &str) -> Vec<Emotion> {
    match id {
        "celebrate" => vec![Emotion::Joy, Emotion::Pride],
        "reaction_recover" | "wjfl_reaction" => vec![Emotion::Surprise],
        "wjfl_feelings" => non_neutral_emotions(),
        _ => Vec::new(),
    }
}

fn legacy_clip_narrative_uses(category: LegacyClipCategoryV1) -> Vec<NarrativeUseV1> {
    let use_case = match category {
        LegacyClipCategoryV1::GroundLocomotion => NarrativeUseV1::StageTravel,
        LegacyClipCategoryV1::FlightPoseSequence => NarrativeUseV1::FlightShowcaseOnly,
        LegacyClipCategoryV1::Action => NarrativeUseV1::AuthoredActionBeat,
        LegacyClipCategoryV1::Celebration => NarrativeUseV1::PositiveClimax,
        LegacyClipCategoryV1::Conversation => NarrativeUseV1::SpokenExplanationOrSocialBeat,
        LegacyClipCategoryV1::EmotionShowcase => NarrativeUseV1::EmotionReferenceOrShowcase,
    };
    vec![use_case]
}

fn clip_family_energy(family: ClipFamily) -> u8 {
    match family {
        ClipFamily::Idle => 5,
        ClipFamily::Listening => 15,
        ClipFamily::Thinking => 20,
        ClipFamily::PreparingResponse => 30,
        ClipFamily::Speaking => 45,
        ClipFamily::Clarifying => 40,
        ClipFamily::ToolWait => 10,
        ClipFamily::Error => 30,
        ClipFamily::Celebrating => 85,
        ClipFamily::Interrupted => 55,
        ClipFamily::GroundLocomotion => 60,
        ClipFamily::Flight => 70,
        ClipFamily::StaffAction => 75,
        ClipFamily::Reaction => 70,
        ClipFamily::FeelingAccent => 50,
    }
}

fn clip_family_emotions(family: ClipFamily) -> Vec<Emotion> {
    match family {
        ClipFamily::Celebrating => vec![Emotion::Joy, Emotion::Pride],
        ClipFamily::Error => vec![Emotion::Fear],
        ClipFamily::Reaction | ClipFamily::Interrupted => vec![Emotion::Surprise],
        _ => Vec::new(),
    }
}

fn clip_family_locomotion_states(family: ClipFamily) -> ApplicabilityV1<Locomotion> {
    match family {
        ClipFamily::Flight => ApplicabilityV1::NotApplicable,
        ClipFamily::GroundLocomotion => applicable([Locomotion::Walking, Locomotion::Turn]),
        _ => applicable(Locomotion::ALL),
    }
}

fn clip_family_narrative_uses(family: ClipFamily) -> Vec<NarrativeUseV1> {
    let value = match family {
        ClipFamily::Idle => NarrativeUseV1::AuthoredStillness,
        ClipFamily::Listening => NarrativeUseV1::ReceptiveAttention,
        ClipFamily::Thinking => NarrativeUseV1::InternalThoughtBeat,
        ClipFamily::PreparingResponse => NarrativeUseV1::PreSpeechAnticipation,
        ClipFamily::Speaking => NarrativeUseV1::SpokenPhrasePerformance,
        ClipFamily::Clarifying => NarrativeUseV1::ClarificationEmphasis,
        ClipFamily::ToolWait => NarrativeUseV1::BoundedWaitingState,
        ClipFamily::Error => NarrativeUseV1::ErrorAcknowledgment,
        ClipFamily::Celebrating => NarrativeUseV1::PositiveClimax,
        ClipFamily::Interrupted => NarrativeUseV1::InterruptionAndRecovery,
        ClipFamily::GroundLocomotion => NarrativeUseV1::StageTravel,
        ClipFamily::Flight => NarrativeUseV1::AirborneStaging,
        ClipFamily::StaffAction => NarrativeUseV1::StaffLedActionBeat,
        ClipFamily::Reaction => NarrativeUseV1::ReactionAccent,
        ClipFamily::FeelingAccent => NarrativeUseV1::EmotionAccent,
    };
    vec![value]
}

fn interruptibility(policy: InterruptPolicy) -> InterruptibilityV1 {
    match policy {
        InterruptPolicy::Immediate => InterruptibilityV1::Immediate,
        InterruptPolicy::AtSafeMarker => InterruptibilityV1::AtSafeMarker,
        InterruptPolicy::AfterCommit => InterruptibilityV1::AfterCommit,
        InterruptPolicy::AfterImpact => InterruptibilityV1::AfterImpact,
        InterruptPolicy::UninterruptibleUntilRecovery => {
            InterruptibilityV1::UninterruptibleUntilRecovery
        }
    }
}
