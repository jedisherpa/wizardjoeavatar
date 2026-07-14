use crate::animation::reference_pose_id_for_state;
use crate::chat_event::{
    AttentionTarget, ChatTurnState, Emotion, GestureKind, MotionProfile, Viseme,
    CHAT_EVENT_SCHEMA_VERSION,
};
use crate::chat_performance::{
    RenderedMouthPose, CHAT_PERFORMANCE_SCHEMA_VERSION, DURATION_FALLBACK_VERSION,
};
use crate::command::COMMAND_SCHEMA_VERSION;
use crate::controller::RUNTIME_PROCEDURAL_BEHAVIOR_IDS;
use crate::motion_catalog::{shadow_motion_catalog, EMBEDDED_MOTION_GRAPH_SHA256};
use crate::motion_graph::{
    CapabilityTier, ClipFamily, InterruptPolicy, LoopMode, MotionClip, MotionGraphV1, PoseUseKind,
    MOTION_GRAPH_SCHEMA_VERSION, REQUIRED_RUNTIME_GEOMETRY_COUNT,
};
use crate::pose::{PoseDefinition, PoseLibrary, PoseMotionFamily};
use crate::pose_asset::{embedded_pose_archive_sha256, IMPORTED_POSE_SCHEMA_VERSION};
use crate::pose_clip::{PoseClipDefinition, POSE_CLIPS};
use crate::state::{Direction, Expression, WizardState};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::sync::OnceLock;

pub const CAPABILITY_MANIFEST_SCHEMA_VERSION: u16 = 1;
pub const CAPABILITY_API_VERSION: u16 = 1;
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
pub struct CapabilityEntryV1 {
    pub id: String,
    pub kind: CapabilityKind,
    pub status: CapabilityStatus,
    pub category: CapabilityCategoryV1,
    pub emotional_uses: Vec<Emotion>,
    pub energy: u8,
    pub directions: Vec<Direction>,
    pub duration: Option<TickDurationV1>,
    pub loop_behavior: LoopBehaviorV1,
    pub interruptibility: InterruptibilityV1,
    pub valid_entry_states: Vec<ChatTurnState>,
    pub valid_exit_states: Vec<ChatTurnState>,
    pub face_policy: FacePolicyV1,
    pub compatible_motion_profiles: Vec<MotionProfile>,
    pub runtime_surfaces: Vec<RuntimeSurfaceV1>,
    pub prop_requirements: Vec<PropRequirementV1>,
    pub runtime_cost: RuntimeCostV1,
    pub quality_status: QualityStatusV1,
    pub pose_coverage: Option<PoseCoverageV1>,
    pub transition_limitations: Vec<String>,
    pub narrative_uses: Vec<String>,
    pub inappropriate_uses: Vec<String>,
    pub fallback_ids: Vec<String>,
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
    pub state_facing_fallbacks: Vec<StateFacingFallbackV1>,
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
        validate_fallback_topology(&ids)?;
        validate_state_facing_fallbacks(&ids, &self.state_facing_fallbacks)?;
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

pub fn build_wizard_capability_manifest() -> Result<CapabilityManifestV1, String> {
    let library = PoseLibrary::reference()?;
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
        state_facing_fallbacks,
        support: RuntimeSupportFlagsV1 {
            deterministic_media_scores: false,
            authored_dance: false,
            rendered_gaze: false,
            timed_visemes: false,
        },
        capabilities,
    };
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
    let mut props = Vec::new();
    if pose.motion.staff_present {
        props.push(PropRequirementV1::StaffAllSamples);
    }
    if pose.motion.effect_present {
        props.push(PropRequirementV1::EffectAllSamples);
    }
    let fallback_ids = showcase_approval
        .as_ref()
        .map(|approval| vec![approval.fallback_pose_id.clone()])
        .unwrap_or_default();
    CapabilityEntryV1 {
        id: pose.id.clone(),
        kind: CapabilityKind::Pose,
        status,
        category: CapabilityCategoryV1::PoseFamily(pose_family(pose.motion.family)),
        emotional_uses: Vec::new(),
        energy: pose_family_energy(pose.motion.family),
        directions: vec![pose.direction],
        duration: None,
        loop_behavior: LoopBehaviorV1::NotApplicable,
        interruptibility: InterruptibilityV1::RawPoseReplace,
        valid_entry_states: Vec::new(),
        valid_exit_states: Vec::new(),
        face_policy: FacePolicyV1::LegacyOverlay,
        compatible_motion_profiles: Vec::new(),
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
        transition_limitations: vec![
            "raw pose selection bypasses semantic performance policy".to_string()
        ],
        narrative_uses: pose_family_narrative_uses(pose.motion.family),
        inappropriate_uses: vec!["direct selection by an unconstrained model".to_string()],
        fallback_ids,
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
    let category = legacy_clip_category(clip.id)?;
    Ok(CapabilityEntryV1 {
        id: clip.id.to_string(),
        kind: CapabilityKind::LegacyClip,
        status: CapabilityStatus::ActiveLegacy,
        category: CapabilityCategoryV1::LegacyClip(category),
        emotional_uses: legacy_clip_emotions(clip.id),
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
        valid_entry_states: Vec::new(),
        valid_exit_states: Vec::new(),
        face_policy: FacePolicyV1::LegacyOverlay,
        compatible_motion_profiles: Vec::new(),
        runtime_surfaces: vec![
            RuntimeSurfaceV1::LegacyPoseClip,
            RuntimeSurfaceV1::LegacyController,
        ],
        prop_requirements: prop_coverage(
            PropRequirementV1::StaffAllSamples,
            PropRequirementV1::StaffSomeSamples,
            staff_count,
            clip.steps.len(),
        )
        .into_iter()
        .collect(),
        runtime_cost: RuntimeCostV1::BoundedPoseSequence,
        quality_status: RuntimeCostV1::BoundedPoseSequence.into_quality(),
        pose_coverage: None,
        transition_limitations: vec!["not executed by the marker-aware motion director".to_string()],
        narrative_uses: legacy_clip_narrative_uses(category),
        inappropriate_uses: vec!["media-time choreography without a score".to_string()],
        fallback_ids: Vec::new(),
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
    let fallback_ids = clip
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
        emotional_uses: clip_family_emotions(clip.family),
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
        valid_entry_states,
        valid_exit_states,
        face_policy: if clip
            .owned_channels
            .regions
            .contains(&crate::motion_graph::PerformanceRegion::FaceEmotion)
        {
            FacePolicyV1::OwnedByClip
        } else {
            FacePolicyV1::PreserveFaceRegion
        },
        compatible_motion_profiles: sorted_unique(
            graph
                .edges
                .iter()
                .filter(|edge| {
                    edge.source_clip_id == clip.clip_id || edge.target_clip_id == clip.clip_id
                })
                .flat_map(|edge| edge.allowed_motion_profiles.iter().copied()),
        ),
        runtime_surfaces: vec![RuntimeSurfaceV1::ShadowMotionGraph],
        prop_requirements: props,
        runtime_cost: RuntimeCostV1::BoundedMarkerTimeline,
        quality_status: QualityStatusV1::ShadowValidatedNotRuntimeWired,
        pose_coverage: None,
        transition_limitations: vec!["not yet consumed by the production controller".to_string()],
        narrative_uses: clip_family_narrative_uses(clip.family),
        inappropriate_uses: vec!["advertising as runtime active before wiring".to_string()],
        fallback_ids,
    })
}

fn expression_entries() -> Vec<CapabilityEntryV1> {
    Expression::ALL
        .into_iter()
        .map(|expression| {
            simple_entry(
                format!("expression.{}", expression.as_str()),
                CapabilityKind::Expression,
                CapabilityStatus::ActiveLegacy,
                CapabilityCategoryV1::FaceExpression,
                20,
                RuntimeSurfaceV1::LegacyController,
                QualityStatusV1::RuntimeRendered,
            )
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
                RuntimeSurfaceV1::LegacyController,
                QualityStatusV1::RuntimeRenderedDurationDriven,
            ))
        })
        .collect()
}

fn shadow_semantic_entries() -> Result<Vec<CapabilityEntryV1>, String> {
    let mut entries = Vec::new();
    for state in ChatTurnState::ALL {
        entries.push(simple_shadow_entry(
            format!("chat_state.{}", enum_wire_name(state, "chat state")?),
            CapabilityKind::ChatState,
            CapabilityCategoryV1::ChatState,
        ));
    }
    for emotion in non_neutral_emotions() {
        entries.push(simple_shadow_entry(
            format!("emotion.{}", enum_wire_name(emotion, "emotion")?),
            CapabilityKind::Emotion,
            CapabilityCategoryV1::EmotionIntent,
        ));
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
    RUNTIME_PROCEDURAL_BEHAVIOR_IDS
        .into_iter()
        .map(|id| {
            let (category, energy) = match id {
                "behavior.move" | "behavior.return_to_center" => {
                    (CapabilityCategoryV1::RootMotion, 35)
                }
                "behavior.walk_left"
                | "behavior.walk_right"
                | "behavior.walk_forward"
                | "behavior.walk_backward" => (CapabilityCategoryV1::RootMotion, 40),
                "behavior.path" | "behavior.circle" => (CapabilityCategoryV1::PathMotion, 45),
                "behavior.figure_eight" => (CapabilityCategoryV1::PathMotion, 50),
                "behavior.speaking_duration" => (CapabilityCategoryV1::SpeechFallback, 25),
                "behavior.periodic_blink" => (CapabilityCategoryV1::BlinkFallback, 5),
                _ => return Err(format!("unclassified controller procedural behavior {id}")),
            };
            Ok(simple_entry(
                id.to_string(),
                CapabilityKind::ProceduralBehavior,
                CapabilityStatus::ActiveLegacy,
                category,
                energy,
                RuntimeSurfaceV1::LegacyController,
                QualityStatusV1::RuntimeActiveLegacy,
            ))
        })
        .collect()
}

fn simple_entry(
    id: String,
    kind: CapabilityKind,
    status: CapabilityStatus,
    category: CapabilityCategoryV1,
    energy: u8,
    surface: RuntimeSurfaceV1,
    quality_status: QualityStatusV1,
) -> CapabilityEntryV1 {
    CapabilityEntryV1 {
        id,
        kind,
        status,
        category,
        emotional_uses: Vec::new(),
        energy,
        directions: Vec::new(),
        duration: None,
        loop_behavior: LoopBehaviorV1::StateDriven,
        interruptibility: InterruptibilityV1::Immediate,
        valid_entry_states: Vec::new(),
        valid_exit_states: Vec::new(),
        face_policy: FacePolicyV1::LegacyOverlay,
        compatible_motion_profiles: Vec::new(),
        runtime_surfaces: vec![surface],
        prop_requirements: Vec::new(),
        runtime_cost: RuntimeCostV1::ConstantTimeStateUpdate,
        quality_status,
        pose_coverage: None,
        transition_limitations: Vec::new(),
        narrative_uses: Vec::new(),
        inappropriate_uses: Vec::new(),
        fallback_ids: Vec::new(),
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
        emotional_uses: Vec::new(),
        energy: 25,
        directions: Vec::new(),
        duration: None,
        loop_behavior: LoopBehaviorV1::EventDriven,
        interruptibility: InterruptibilityV1::ContractDefined,
        valid_entry_states: Vec::new(),
        valid_exit_states: Vec::new(),
        face_policy: FacePolicyV1::ContractOnlyNotRendered,
        compatible_motion_profiles: Vec::new(),
        runtime_surfaces: vec![RuntimeSurfaceV1::TypedChatContract],
        prop_requirements: Vec::new(),
        runtime_cost: RuntimeCostV1::NotMeasuredUntilRuntimeWiring,
        quality_status: QualityStatusV1::ContractValidatedNotRuntimeRendered,
        pose_coverage: None,
        transition_limitations: vec!["not consumed by the production renderer".to_string()],
        narrative_uses: Vec::new(),
        inappropriate_uses: vec!["advertising as visibly implemented".to_string()],
        fallback_ids: Vec::new(),
    }
}

fn validate_entry(entry: &CapabilityEntryV1) -> Result<(), String> {
    if entry.energy > 100 {
        return Err(format!("{} energy exceeds 100", entry.id));
    }
    validate_sorted_unique(&entry.emotional_uses, "emotional_uses")?;
    validate_sorted_unique(&entry.directions, "directions")?;
    validate_sorted_unique(&entry.valid_entry_states, "valid_entry_states")?;
    validate_sorted_unique(&entry.valid_exit_states, "valid_exit_states")?;
    validate_sorted_unique(
        &entry.compatible_motion_profiles,
        "compatible_motion_profiles",
    )?;
    validate_sorted_unique(&entry.runtime_surfaces, "runtime_surfaces")?;
    validate_sorted_unique(&entry.prop_requirements, "prop_requirements")?;
    validate_text_values(&entry.transition_limitations, "transition_limitations")?;
    validate_text_values(&entry.narrative_uses, "narrative_uses")?;
    validate_text_values(&entry.inappropriate_uses, "inappropriate_uses")?;
    validate_ids(&entry.fallback_ids, "fallback_ids")?;
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
        CapabilityKind::LegacyClip
        | CapabilityKind::Expression
        | CapabilityKind::MouthPose
        | CapabilityKind::ProceduralBehavior => {
            if entry.status != CapabilityStatus::ActiveLegacy || entry.pose_coverage.is_some() {
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
            if entry.status != CapabilityStatus::ShadowValidated || entry.pose_coverage.is_some() {
                return Err(format!("{} has an invalid shadow status", entry.id));
            }
            Ok(())
        }
    }
}

fn validate_pose_entry(entry: &CapabilityEntryV1) -> Result<(), String> {
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
            if entry.fallback_ids != [approval.fallback_pose_id.clone()] {
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
        (_, None) => {}
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

fn validate_fallback_topology(ids: &BTreeMap<&str, &CapabilityEntryV1>) -> Result<(), String> {
    for entry in ids.values() {
        for fallback in &entry.fallback_ids {
            let target = ids
                .get(fallback.as_str())
                .ok_or_else(|| format!("{} has unresolved fallback {fallback}", entry.id))?;
            if fallback == &entry.id {
                return Err(format!("{} has a self fallback", entry.id));
            }
            if target.kind != entry.kind {
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
    for fallback in &entry.fallback_ids {
        let (target_id, _) = ids
            .get_key_value(fallback.as_str())
            .ok_or_else(|| format!("{id} has unresolved fallback {fallback}"))?;
        validate_fallback_acyclic(target_id, ids, visiting, visited)?;
    }
    visiting.remove(id);
    visited.insert(id);
    Ok(())
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

fn validate_text_values(values: &[String], field: &str) -> Result<(), String> {
    if values.len() > MAX_TEXT_VALUES {
        return Err(format!("{field} exceeds {MAX_TEXT_VALUES} values"));
    }
    validate_sorted_unique(values, field)?;
    for value in values {
        validate_text(value, field)?;
    }
    Ok(())
}

fn validate_sorted_unique<T: Ord>(values: &[T], field: &str) -> Result<(), String> {
    if values.windows(2).any(|pair| pair[0] >= pair[1]) {
        return Err(format!("{field} must be canonically sorted and unique"));
    }
    Ok(())
}

fn sorted_unique<T: Ord>(values: impl IntoIterator<Item = T>) -> Vec<T> {
    values
        .into_iter()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
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

fn pose_family_narrative_uses(family: PoseMotionFamily) -> Vec<String> {
    let value = match family {
        PoseMotionFamily::Run => "urgent travel or action",
        PoseMotionFamily::Walk => "deliberate stage travel",
        PoseMotionFamily::Flight => "airborne staging after flight activation",
        PoseMotionFamily::Jump => "authored action accent",
        PoseMotionFamily::Landing => "authored recovery or arrival",
        PoseMotionFamily::GroundAction => "grounded performance accent",
        PoseMotionFamily::Kneel => "low or braced staging",
        PoseMotionFamily::Baseline => "neutral staging and directional fallback",
    };
    vec![value.to_string()]
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

fn legacy_clip_narrative_uses(category: LegacyClipCategoryV1) -> Vec<String> {
    let use_case = match category {
        LegacyClipCategoryV1::GroundLocomotion => "stage travel",
        LegacyClipCategoryV1::FlightPoseSequence => "flight showcase only",
        LegacyClipCategoryV1::Action => "authored action beat",
        LegacyClipCategoryV1::Celebration => "positive climax",
        LegacyClipCategoryV1::Conversation => "spoken explanation or social beat",
        LegacyClipCategoryV1::EmotionShowcase => "emotion reference or showcase",
    };
    vec![use_case.to_string()]
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

fn clip_family_narrative_uses(family: ClipFamily) -> Vec<String> {
    let value = match family {
        ClipFamily::Idle => "authored stillness",
        ClipFamily::Listening => "receptive attention",
        ClipFamily::Thinking => "internal thought beat",
        ClipFamily::PreparingResponse => "pre-speech anticipation",
        ClipFamily::Speaking => "spoken phrase performance",
        ClipFamily::Clarifying => "clarification emphasis",
        ClipFamily::ToolWait => "bounded waiting state",
        ClipFamily::Error => "error acknowledgment",
        ClipFamily::Celebrating => "positive climax",
        ClipFamily::Interrupted => "interruption and recovery",
        ClipFamily::GroundLocomotion => "stage travel",
        ClipFamily::Flight => "airborne staging after flight activation",
        ClipFamily::StaffAction => "staff-led action beat",
        ClipFamily::Reaction => "reaction accent",
        ClipFamily::FeelingAccent => "emotion accent",
    };
    vec![value.to_string()]
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
