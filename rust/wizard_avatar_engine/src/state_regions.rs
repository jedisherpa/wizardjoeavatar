use crate::chat_event::{
    AttentionTarget, ChatTurnState, Emotion, GestureKind, SessionId, SourceId, SourceKind, TurnId,
    UtteranceId, Viseme,
};
use crate::chat_performance::RenderedMouthPose;
use crate::state::{
    Action, ChannelGenerations, ContactMarker, Direction, EffectState, Expression, Locomotion,
    MouthShape, PlantedFoot, ScreenPoint, StaffState, UpperBodyAction, Velocity, WizardState,
    WorldPoint,
};
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use std::fmt;
use thiserror::Error;

pub const AVATAR_SEMANTIC_STATE_SCHEMA_VERSION: u16 = 1;
pub const MAX_STATE_ID_BYTES: usize = 128;
pub const MAX_EFFECT_INSTANCES: usize = 32;
pub const MAX_SOURCE_WATERMARKS: usize = 128;
pub const MAX_CONTACT_POINTS: usize = 5;

#[derive(
    Clone, Copy, Debug, Default, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize,
)]
#[serde(transparent)]
pub struct SemanticTick(pub u64);

#[derive(
    Clone, Copy, Debug, Default, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize,
)]
#[serde(transparent)]
pub struct RegionGeneration(pub u64);

#[derive(
    Clone, Copy, Debug, Default, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize,
)]
#[serde(transparent)]
pub struct RegionPriority(pub u8);

#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct StateIdV1(String);

impl StateIdV1 {
    pub fn new(value: impl Into<String>) -> Result<Self, StateRegionError> {
        let value = value.into();
        if value.is_empty()
            || value.len() > MAX_STATE_ID_BYTES
            || !value.bytes().all(|byte| byte.is_ascii_graphic())
        {
            return Err(StateRegionError::InvalidIdentifier);
        }
        Ok(Self(value))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for StateIdV1 {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl Serialize for StateIdV1 {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&self.0)
    }
}

impl<'de> Deserialize<'de> for StateIdV1 {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        Self::new(value).map_err(serde::de::Error::custom)
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RegionOwner {
    SessionLifecycle,
    ConversationRuntime,
    SpeechRuntime,
    FaceRuntime,
    GestureRuntime,
    MotionRuntime,
    PropsRuntime,
    EffectsRuntime,
    MobilityRuntime,
    ControlRuntime,
    SafetyOverride,
    LegacyAdapter,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RegionKind {
    Session,
    Conversation,
    Speech,
    Mouth,
    Face,
    Gesture,
    Pose,
    Staff,
    Wings,
    Effects,
    Mobility,
    Control,
}

impl RegionKind {
    pub const ALL: [Self; 12] = [
        Self::Session,
        Self::Conversation,
        Self::Speech,
        Self::Mouth,
        Self::Face,
        Self::Gesture,
        Self::Pose,
        Self::Staff,
        Self::Wings,
        Self::Effects,
        Self::Mobility,
        Self::Control,
    ];
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RegionHeader {
    pub generation: RegionGeneration,
    pub entered_tick: SemanticTick,
    pub owner: RegionOwner,
    pub priority: RegionPriority,
    pub deadline_tick: Option<SemanticTick>,
}

impl RegionHeader {
    const fn initial(owner: RegionOwner) -> Self {
        Self {
            generation: RegionGeneration(0),
            entered_tick: SemanticTick(0),
            owner,
            priority: RegionPriority(0),
            deadline_tick: None,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RegionMutationContextV1 {
    pub owner: RegionOwner,
    pub expected_generation: RegionGeneration,
    pub priority: RegionPriority,
    pub entered_tick: SemanticTick,
    pub deadline_tick: Option<SemanticTick>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RegionMutationReceiptV1 {
    pub region: RegionKind,
    pub owner: RegionOwner,
    pub generation: RegionGeneration,
}

#[derive(Clone, Debug, Error, Eq, PartialEq)]
pub enum StateRegionError {
    #[error("unsupported semantic state schema {0}")]
    UnsupportedSchema(u16),
    #[error("state identifier is empty, oversized, or non-graphic ASCII")]
    InvalidIdentifier,
    #[error(
        "{region:?} owner {requested_owner:?} at {requested_priority:?} cannot acquire from {current_owner:?} at {current_priority:?}"
    )]
    ConflictingOwner {
        region: RegionKind,
        current_owner: RegionOwner,
        current_priority: RegionPriority,
        requested_owner: RegionOwner,
        requested_priority: RegionPriority,
    },
    #[error("{region:?} expected generation {expected:?}, actual {actual:?}")]
    StaleGeneration {
        region: RegionKind,
        expected: RegionGeneration,
        actual: RegionGeneration,
    },
    #[error("{region:?} priority {requested_priority:?} is below {current_priority:?}")]
    PriorityConflict {
        region: RegionKind,
        current_priority: RegionPriority,
        requested_priority: RegionPriority,
    },
    #[error("{region:?} generation cannot advance without wrapping")]
    GenerationOverflow { region: RegionKind },
    #[error("{region:?} expired at {deadline_tick:?}; current tick is {current_tick:?}")]
    ExpiredRegion {
        region: RegionKind,
        deadline_tick: SemanticTick,
        current_tick: SemanticTick,
    },
    #[error("{region:?} deadline {deadline_tick:?} is not after {current_tick:?}")]
    ExpiredDeadline {
        region: RegionKind,
        deadline_tick: SemanticTick,
        current_tick: SemanticTick,
    },
    #[error("{region:?} entered tick moved backward from {current_tick:?} to {requested_tick:?}")]
    NonMonotonicTick {
        region: RegionKind,
        current_tick: SemanticTick,
        requested_tick: SemanticTick,
    },
    #[error("{region:?} exceeds bounded capacity {maximum}")]
    CapacityExceeded { region: RegionKind, maximum: usize },
    #[error("{region:?}.{field} must be in 0..=100, got {value}")]
    InvalidPercent {
        region: RegionKind,
        field: &'static str,
        value: u8,
    },
    #[error("{region:?} effect {index} deadline is not after its start")]
    InvalidEffectDeadline { region: RegionKind, index: usize },
    #[error("{region:?} contains duplicate effect ID at index {index}")]
    DuplicateEffectId { region: RegionKind, index: usize },
    #[error(
        "{region:?} effect {index} expired at {deadline_tick:?}; current tick is {current_tick:?}"
    )]
    ExpiredEffect {
        region: RegionKind,
        index: usize,
        deadline_tick: SemanticTick,
        current_tick: SemanticTick,
    },
    #[error(
        "{region:?} mobility lease expired at {deadline_tick:?}; current tick is {current_tick:?}"
    )]
    ExpiredLease {
        region: RegionKind,
        deadline_tick: SemanticTick,
        current_tick: SemanticTick,
    },
    #[error("{region:?} contains duplicate contact at index {index}")]
    DuplicateContact { region: RegionKind, index: usize },
    #[error("control contains duplicate source-watermark identity at index {index}")]
    DuplicateSourceWatermark { index: usize },
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SessionModeV1 {
    Disconnected,
    Ready,
    Degraded,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SessionStateV1 {
    pub mode: SessionModeV1,
    pub session_id: Option<SessionId>,
    pub turn_id: Option<TurnId>,
    pub attention_target: AttentionTarget,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ConversationStateV1 {
    pub turn_state: ChatTurnState,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SpeechModeV1 {
    Idle,
    Prepared,
    Active,
    Paused,
    Cancelling,
    Completed,
    Failed,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SpeechStateV1 {
    pub mode: SpeechModeV1,
    pub utterance_id: Option<UtteranceId>,
    pub plan_hash64: Option<u64>,
    pub start_tick: Option<SemanticTick>,
    pub cursor_tick: u32,
    pub suppressed: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MouthStateV1 {
    pub viseme: Viseme,
    pub rendered_pose: RenderedMouthPose,
    pub previous_pose: RenderedMouthPose,
    pub blend_percent: u8,
    pub cue_index: Option<u32>,
    pub confidence: u8,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FaceExpressionV1 {
    Neutral,
    Happy,
    Thinking,
    Surprised,
    Worried,
    Amused,
    Confident,
    Focused,
    Skeptical,
    Explaining,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BlinkStateV1 {
    Open,
    Closing,
    Closed,
    Opening,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FaceStateV1 {
    pub emotion: Emotion,
    pub transient_expression: Option<FaceExpressionV1>,
    pub intensity: u8,
    pub confidence: u8,
    pub blink: BlinkStateV1,
    pub gaze: AttentionTarget,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GesturePhaseV1 {
    Idle,
    Anticipation,
    Commit,
    Hold,
    Recovery,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GestureMarkerV1 {
    None,
    Entry,
    Anticipation,
    Commit,
    Hold,
    Recover,
    Exit,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GestureInterruptPolicyV1 {
    Immediate,
    AtSafeMarker,
    AfterCommit,
    Uninterruptible,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GestureRestorationPolicyV1 {
    RestorePrevious,
    SettleToIdle,
    ContinueTarget,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GestureStateV1 {
    pub gesture: Option<GestureKind>,
    pub phase: GesturePhaseV1,
    pub marker: GestureMarkerV1,
    pub interrupt_policy: GestureInterruptPolicyV1,
    pub restoration_policy: GestureRestorationPolicyV1,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Point2iV1 {
    pub x: i32,
    pub y: i32,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContactPointV1 {
    LeftFoot,
    RightFoot,
    StaffTip,
    LeftHand,
    RightHand,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PoseStateV1 {
    pub clip_id: Option<StateIdV1>,
    pub sample_index: Option<u32>,
    pub pose_id: Option<StateIdV1>,
    pub transition_id: Option<StateIdV1>,
    pub transition_progress_percent: u8,
    pub visual_root_millicells: Point2iV1,
    pub contacts: Vec<ContactPointV1>,
    pub presented_state_hash64: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StaffModeV1 {
    Held,
    Planted,
    Guard,
    Thrust,
    Block,
    Spin,
    Raised,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HandV1 {
    None,
    Left,
    Right,
    Both,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContactStateV1 {
    Free,
    Held,
    Planted,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StaffStateV1 {
    pub mode: StaffModeV1,
    pub hand: HandV1,
    pub contact: ContactStateV1,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WingModeV1 {
    Folded,
    Neutral,
    Upstroke,
    Downstroke,
    Glide,
    BankLeft,
    BankRight,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WingStateV1 {
    pub mode: WingModeV1,
    pub phase_percent: u8,
    pub visible: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EffectKindV1 {
    Magic,
    Reaction,
    Emphasis,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EffectInstanceV1 {
    pub effect_id: StateIdV1,
    pub kind: EffectKindV1,
    pub generation: RegionGeneration,
    pub started_tick: SemanticTick,
    pub deadline_tick: SemanticTick,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EffectsStateV1 {
    pub instances: Vec<EffectInstanceV1>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MobilityModeV1 {
    GroundedIdle,
    GroundStart,
    GroundWalk,
    GroundRun,
    GroundStop,
    Takeoff,
    Hover,
    Travel,
    Bank,
    Fall,
    Land,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MobilityStateV1 {
    pub mode: MobilityModeV1,
    pub position_millicells: Point2iV1,
    pub velocity_millicells_per_tick: Point2iV1,
    pub facing: Direction,
    pub altitude_millicells: i32,
    pub contacts: Vec<ContactPointV1>,
    pub locomotion_phase_tick: u32,
    pub wing_phase_tick: u32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceWatermarkStateV1 {
    pub source_kind: SourceKind,
    pub source_id: SourceId,
    pub source_sequence: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RegionLeaseV1 {
    pub owner: RegionOwner,
    pub generation: RegionGeneration,
    pub deadline_tick: SemanticTick,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ControlStateV1 {
    pub source_watermarks: Vec<SourceWatermarkStateV1>,
    pub active_mobility_lease: Option<RegionLeaseV1>,
    pub safety_clamp: bool,
    pub queue_watermark: u64,
    pub reconnect_count: u64,
}

macro_rules! region {
    ($name:ident, $body:ty) => {
        #[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
        #[serde(deny_unknown_fields)]
        pub struct $name {
            pub header: RegionHeader,
            pub state: $body,
        }
    };
}

region!(SessionRegionV1, SessionStateV1);
region!(ConversationRegionV1, ConversationStateV1);
region!(SpeechRegionV1, SpeechStateV1);
region!(MouthRegionV1, MouthStateV1);
region!(FaceRegionV1, FaceStateV1);
region!(GestureRegionV1, GestureStateV1);
region!(PoseRegionV1, PoseStateV1);
region!(StaffRegionV1, StaffStateV1);
region!(WingRegionV1, WingStateV1);
region!(EffectsRegionV1, EffectsStateV1);
region!(MobilityRegionV1, MobilityStateV1);
region!(ControlRegionV1, ControlStateV1);

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AvatarSemanticStateV1 {
    pub schema_version: u16,
    pub character_id: String,
    pub session: SessionRegionV1,
    pub conversation: ConversationRegionV1,
    pub speech: SpeechRegionV1,
    pub mouth: MouthRegionV1,
    pub face: FaceRegionV1,
    pub gesture: GestureRegionV1,
    pub pose: PoseRegionV1,
    pub staff: StaffRegionV1,
    pub wings: WingRegionV1,
    pub effects: EffectsRegionV1,
    pub mobility: MobilityRegionV1,
    pub control: ControlRegionV1,
}

impl AvatarSemanticStateV1 {
    #[must_use]
    pub fn new(character_id: impl Into<String>) -> Self {
        Self {
            schema_version: AVATAR_SEMANTIC_STATE_SCHEMA_VERSION,
            character_id: character_id.into(),
            session: SessionRegionV1 {
                header: RegionHeader::initial(RegionOwner::SessionLifecycle),
                state: SessionStateV1 {
                    mode: SessionModeV1::Disconnected,
                    session_id: None,
                    turn_id: None,
                    attention_target: AttentionTarget::Neutral,
                },
            },
            conversation: ConversationRegionV1 {
                header: RegionHeader::initial(RegionOwner::ConversationRuntime),
                state: ConversationStateV1 {
                    turn_state: ChatTurnState::Idle,
                },
            },
            speech: SpeechRegionV1 {
                header: RegionHeader::initial(RegionOwner::SpeechRuntime),
                state: SpeechStateV1 {
                    mode: SpeechModeV1::Idle,
                    utterance_id: None,
                    plan_hash64: None,
                    start_tick: None,
                    cursor_tick: 0,
                    suppressed: false,
                },
            },
            mouth: MouthRegionV1 {
                header: RegionHeader::initial(RegionOwner::SpeechRuntime),
                state: MouthStateV1 {
                    viseme: Viseme::Rest,
                    rendered_pose: RenderedMouthPose::Closed,
                    previous_pose: RenderedMouthPose::Closed,
                    blend_percent: 100,
                    cue_index: None,
                    confidence: 100,
                },
            },
            face: FaceRegionV1 {
                header: RegionHeader::initial(RegionOwner::FaceRuntime),
                state: FaceStateV1 {
                    emotion: Emotion::Neutral,
                    transient_expression: None,
                    intensity: 0,
                    confidence: 100,
                    blink: BlinkStateV1::Open,
                    gaze: AttentionTarget::Neutral,
                },
            },
            gesture: GestureRegionV1 {
                header: RegionHeader::initial(RegionOwner::GestureRuntime),
                state: GestureStateV1 {
                    gesture: None,
                    phase: GesturePhaseV1::Idle,
                    marker: GestureMarkerV1::None,
                    interrupt_policy: GestureInterruptPolicyV1::AtSafeMarker,
                    restoration_policy: GestureRestorationPolicyV1::SettleToIdle,
                },
            },
            pose: PoseRegionV1 {
                header: RegionHeader::initial(RegionOwner::MotionRuntime),
                state: PoseStateV1 {
                    clip_id: None,
                    sample_index: None,
                    pose_id: None,
                    transition_id: None,
                    transition_progress_percent: 100,
                    visual_root_millicells: Point2iV1::default(),
                    contacts: Vec::new(),
                    presented_state_hash64: 0,
                },
            },
            staff: StaffRegionV1 {
                header: RegionHeader::initial(RegionOwner::PropsRuntime),
                state: StaffStateV1 {
                    mode: StaffModeV1::Held,
                    hand: HandV1::Right,
                    contact: ContactStateV1::Held,
                },
            },
            wings: WingRegionV1 {
                header: RegionHeader::initial(RegionOwner::PropsRuntime),
                state: WingStateV1 {
                    mode: WingModeV1::Folded,
                    phase_percent: 0,
                    visible: false,
                },
            },
            effects: EffectsRegionV1 {
                header: RegionHeader::initial(RegionOwner::EffectsRuntime),
                state: EffectsStateV1 {
                    instances: Vec::new(),
                },
            },
            mobility: MobilityRegionV1 {
                header: RegionHeader::initial(RegionOwner::MobilityRuntime),
                state: MobilityStateV1 {
                    mode: MobilityModeV1::GroundedIdle,
                    position_millicells: Point2iV1::default(),
                    velocity_millicells_per_tick: Point2iV1::default(),
                    facing: Direction::South,
                    altitude_millicells: 0,
                    contacts: vec![ContactPointV1::LeftFoot, ContactPointV1::RightFoot],
                    locomotion_phase_tick: 0,
                    wing_phase_tick: 0,
                },
            },
            control: ControlRegionV1 {
                header: RegionHeader::initial(RegionOwner::ControlRuntime),
                state: ControlStateV1 {
                    source_watermarks: Vec::new(),
                    active_mobility_lease: None,
                    safety_clamp: false,
                    queue_watermark: 0,
                    reconnect_count: 0,
                },
            },
        }
    }

    #[must_use]
    pub const fn region_header(&self, region: RegionKind) -> &RegionHeader {
        match region {
            RegionKind::Session => &self.session.header,
            RegionKind::Conversation => &self.conversation.header,
            RegionKind::Speech => &self.speech.header,
            RegionKind::Mouth => &self.mouth.header,
            RegionKind::Face => &self.face.header,
            RegionKind::Gesture => &self.gesture.header,
            RegionKind::Pose => &self.pose.header,
            RegionKind::Staff => &self.staff.header,
            RegionKind::Wings => &self.wings.header,
            RegionKind::Effects => &self.effects.header,
            RegionKind::Mobility => &self.mobility.header,
            RegionKind::Control => &self.control.header,
        }
    }

    pub fn apply_mutation(
        &mut self,
        context: RegionMutationContextV1,
        mutation: RegionMutationV1,
    ) -> Result<RegionMutationReceiptV1, StateRegionError> {
        let region = mutation.kind();
        let next_header = validate_header_transition(region, *self.region_header(region), context)?;
        mutation.validate(context.entered_tick)?;
        match mutation {
            RegionMutationV1::Session(state) => {
                self.session = SessionRegionV1 {
                    header: next_header,
                    state,
                }
            }
            RegionMutationV1::Conversation(state) => {
                self.conversation = ConversationRegionV1 {
                    header: next_header,
                    state,
                }
            }
            RegionMutationV1::Speech(state) => {
                self.speech = SpeechRegionV1 {
                    header: next_header,
                    state,
                }
            }
            RegionMutationV1::Mouth(state) => {
                self.mouth = MouthRegionV1 {
                    header: next_header,
                    state,
                }
            }
            RegionMutationV1::Face(state) => {
                self.face = FaceRegionV1 {
                    header: next_header,
                    state,
                }
            }
            RegionMutationV1::Gesture(state) => {
                self.gesture = GestureRegionV1 {
                    header: next_header,
                    state,
                }
            }
            RegionMutationV1::Pose(state) => {
                self.pose = PoseRegionV1 {
                    header: next_header,
                    state,
                }
            }
            RegionMutationV1::Staff(state) => {
                self.staff = StaffRegionV1 {
                    header: next_header,
                    state,
                }
            }
            RegionMutationV1::Wings(state) => {
                self.wings = WingRegionV1 {
                    header: next_header,
                    state,
                }
            }
            RegionMutationV1::Effects(state) => {
                self.effects = EffectsRegionV1 {
                    header: next_header,
                    state,
                }
            }
            RegionMutationV1::Mobility(state) => {
                self.mobility = MobilityRegionV1 {
                    header: next_header,
                    state,
                }
            }
            RegionMutationV1::Control(state) => {
                self.control = ControlRegionV1 {
                    header: next_header,
                    state,
                }
            }
        }
        Ok(RegionMutationReceiptV1 {
            region,
            owner: context.owner,
            generation: next_header.generation,
        })
    }

    pub fn validate_at(&self, current_tick: SemanticTick) -> Result<(), StateRegionError> {
        if self.schema_version != AVATAR_SEMANTIC_STATE_SCHEMA_VERSION {
            return Err(StateRegionError::UnsupportedSchema(self.schema_version));
        }
        validate_identifier(&self.character_id)?;
        for region in RegionKind::ALL {
            validate_live_header(region, *self.region_header(region), current_tick)?;
        }
        validate_percent(
            RegionKind::Mouth,
            "blend_percent",
            self.mouth.state.blend_percent,
        )?;
        validate_percent(RegionKind::Mouth, "confidence", self.mouth.state.confidence)?;
        validate_percent(RegionKind::Face, "intensity", self.face.state.intensity)?;
        validate_percent(RegionKind::Face, "confidence", self.face.state.confidence)?;
        validate_percent(
            RegionKind::Pose,
            "transition_progress_percent",
            self.pose.state.transition_progress_percent,
        )?;
        validate_percent(
            RegionKind::Wings,
            "phase_percent",
            self.wings.state.phase_percent,
        )?;
        validate_contacts(RegionKind::Pose, &self.pose.state.contacts)?;
        validate_contacts(RegionKind::Mobility, &self.mobility.state.contacts)?;
        validate_effects(&self.effects.state)?;
        for (index, effect) in self.effects.state.instances.iter().enumerate() {
            if current_tick >= effect.deadline_tick {
                return Err(StateRegionError::ExpiredEffect {
                    region: RegionKind::Effects,
                    index,
                    deadline_tick: effect.deadline_tick,
                    current_tick,
                });
            }
        }
        validate_control(&self.control.state, Some(current_tick))?;
        Ok(())
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegionMutationV1 {
    Session(SessionStateV1),
    Conversation(ConversationStateV1),
    Speech(SpeechStateV1),
    Mouth(MouthStateV1),
    Face(FaceStateV1),
    Gesture(GestureStateV1),
    Pose(PoseStateV1),
    Staff(StaffStateV1),
    Wings(WingStateV1),
    Effects(EffectsStateV1),
    Mobility(MobilityStateV1),
    Control(ControlStateV1),
}

impl RegionMutationV1 {
    const fn kind(&self) -> RegionKind {
        match self {
            Self::Session(_) => RegionKind::Session,
            Self::Conversation(_) => RegionKind::Conversation,
            Self::Speech(_) => RegionKind::Speech,
            Self::Mouth(_) => RegionKind::Mouth,
            Self::Face(_) => RegionKind::Face,
            Self::Gesture(_) => RegionKind::Gesture,
            Self::Pose(_) => RegionKind::Pose,
            Self::Staff(_) => RegionKind::Staff,
            Self::Wings(_) => RegionKind::Wings,
            Self::Effects(_) => RegionKind::Effects,
            Self::Mobility(_) => RegionKind::Mobility,
            Self::Control(_) => RegionKind::Control,
        }
    }

    fn validate(&self, current_tick: SemanticTick) -> Result<(), StateRegionError> {
        match self {
            Self::Mouth(value) => {
                validate_percent(RegionKind::Mouth, "blend_percent", value.blend_percent)?;
                validate_percent(RegionKind::Mouth, "confidence", value.confidence)
            }
            Self::Face(value) => {
                validate_percent(RegionKind::Face, "intensity", value.intensity)?;
                validate_percent(RegionKind::Face, "confidence", value.confidence)
            }
            Self::Pose(value) => validate_percent(
                RegionKind::Pose,
                "transition_progress_percent",
                value.transition_progress_percent,
            )
            .and_then(|()| validate_contacts(RegionKind::Pose, &value.contacts)),
            Self::Wings(value) => {
                validate_percent(RegionKind::Wings, "phase_percent", value.phase_percent)
            }
            Self::Effects(value) => {
                validate_effects(value)?;
                for (index, effect) in value.instances.iter().enumerate() {
                    if current_tick >= effect.deadline_tick {
                        return Err(StateRegionError::ExpiredDeadline {
                            region: RegionKind::Effects,
                            deadline_tick: effect.deadline_tick,
                            current_tick,
                        });
                    }
                    if effect.started_tick >= effect.deadline_tick {
                        return Err(StateRegionError::InvalidEffectDeadline {
                            region: RegionKind::Effects,
                            index,
                        });
                    }
                }
                Ok(())
            }
            Self::Mobility(value) => validate_contacts(RegionKind::Mobility, &value.contacts),
            Self::Control(value) => validate_control(value, Some(current_tick)),
            Self::Session(_)
            | Self::Conversation(_)
            | Self::Speech(_)
            | Self::Gesture(_)
            | Self::Staff(_) => Ok(()),
        }
    }
}

fn validate_percent(
    region: RegionKind,
    field: &'static str,
    value: u8,
) -> Result<(), StateRegionError> {
    if value > 100 {
        return Err(StateRegionError::InvalidPercent {
            region,
            field,
            value,
        });
    }
    Ok(())
}

fn validate_effects(value: &EffectsStateV1) -> Result<(), StateRegionError> {
    if value.instances.len() > MAX_EFFECT_INSTANCES {
        return Err(StateRegionError::CapacityExceeded {
            region: RegionKind::Effects,
            maximum: MAX_EFFECT_INSTANCES,
        });
    }
    for (index, effect) in value.instances.iter().enumerate() {
        if effect.started_tick >= effect.deadline_tick {
            return Err(StateRegionError::InvalidEffectDeadline {
                region: RegionKind::Effects,
                index,
            });
        }
        if value.instances[..index]
            .iter()
            .any(|prior| prior.effect_id == effect.effect_id)
        {
            return Err(StateRegionError::DuplicateEffectId {
                region: RegionKind::Effects,
                index,
            });
        }
    }
    Ok(())
}

fn validate_control(
    value: &ControlStateV1,
    current_tick: Option<SemanticTick>,
) -> Result<(), StateRegionError> {
    if value.source_watermarks.len() > MAX_SOURCE_WATERMARKS {
        return Err(StateRegionError::CapacityExceeded {
            region: RegionKind::Control,
            maximum: MAX_SOURCE_WATERMARKS,
        });
    }
    for (index, watermark) in value.source_watermarks.iter().enumerate() {
        if value.source_watermarks[..index].iter().any(|prior| {
            prior.source_kind == watermark.source_kind && prior.source_id == watermark.source_id
        }) {
            return Err(StateRegionError::DuplicateSourceWatermark { index });
        }
    }
    if let (Some(current_tick), Some(lease)) = (current_tick, value.active_mobility_lease) {
        if current_tick >= lease.deadline_tick {
            return Err(StateRegionError::ExpiredLease {
                region: RegionKind::Control,
                deadline_tick: lease.deadline_tick,
                current_tick,
            });
        }
    }
    Ok(())
}

fn validate_contacts(
    region: RegionKind,
    contacts: &[ContactPointV1],
) -> Result<(), StateRegionError> {
    if contacts.len() > MAX_CONTACT_POINTS {
        return Err(StateRegionError::CapacityExceeded {
            region,
            maximum: MAX_CONTACT_POINTS,
        });
    }
    for (index, contact) in contacts.iter().enumerate() {
        if contacts[..index].contains(contact) {
            return Err(StateRegionError::DuplicateContact { region, index });
        }
    }
    Ok(())
}

fn validate_identifier(value: &str) -> Result<(), StateRegionError> {
    if value.is_empty()
        || value.len() > MAX_STATE_ID_BYTES
        || !value.bytes().all(|byte| byte.is_ascii_graphic())
    {
        return Err(StateRegionError::InvalidIdentifier);
    }
    Ok(())
}

fn validate_live_header(
    region: RegionKind,
    header: RegionHeader,
    current_tick: SemanticTick,
) -> Result<(), StateRegionError> {
    if let Some(deadline_tick) = header.deadline_tick {
        if current_tick >= deadline_tick {
            return Err(StateRegionError::ExpiredRegion {
                region,
                deadline_tick,
                current_tick,
            });
        }
    }
    Ok(())
}

fn validate_header_transition(
    region: RegionKind,
    current: RegionHeader,
    requested: RegionMutationContextV1,
) -> Result<RegionHeader, StateRegionError> {
    if let Some(deadline_tick) = requested.deadline_tick {
        if requested.entered_tick >= deadline_tick {
            return Err(StateRegionError::ExpiredDeadline {
                region,
                deadline_tick,
                current_tick: requested.entered_tick,
            });
        }
    }
    if requested.expected_generation != current.generation {
        return Err(StateRegionError::StaleGeneration {
            region,
            expected: requested.expected_generation,
            actual: current.generation,
        });
    }
    if requested.owner == current.owner && requested.priority < current.priority {
        return Err(StateRegionError::PriorityConflict {
            region,
            current_priority: current.priority,
            requested_priority: requested.priority,
        });
    }
    if requested.owner != current.owner && requested.priority <= current.priority {
        return Err(StateRegionError::ConflictingOwner {
            region,
            current_owner: current.owner,
            current_priority: current.priority,
            requested_owner: requested.owner,
            requested_priority: requested.priority,
        });
    }
    if requested.entered_tick < current.entered_tick {
        return Err(StateRegionError::NonMonotonicTick {
            region,
            current_tick: current.entered_tick,
            requested_tick: requested.entered_tick,
        });
    }
    let generation = current
        .generation
        .0
        .checked_add(1)
        .map(RegionGeneration)
        .ok_or(StateRegionError::GenerationOverflow { region })?;
    Ok(RegionHeader {
        generation,
        entered_tick: requested.entered_tick,
        owner: requested.owner,
        priority: requested.priority,
        deadline_tick: requested.deadline_tick,
    })
}

impl From<&AvatarSemanticStateV1> for WizardState {
    fn from(value: &AvatarSemanticStateV1) -> Self {
        let simulation_tick = RegionKind::ALL
            .into_iter()
            .map(|region| value.region_header(region).entered_tick.0)
            .max()
            .unwrap_or(0);
        let action = legacy_action(value);
        let upper_body_action = legacy_upper_body(value.gesture.state.gesture);
        let staff_state = legacy_staff(value.staff.state.mode);
        let effect_state = legacy_effect(value);
        let heading = legacy_heading(value.mobility.state.facing);
        let locomotion = legacy_locomotion(value.mobility.state.mode);
        let contact_marker = legacy_contact_marker(value.mobility.state.locomotion_phase_tick);
        let planted_foot = legacy_planted_foot(&value.mobility.state.contacts);

        Self {
            character_id: value.character_id.clone(),
            world_position: WorldPoint {
                x: millicells_to_cells(value.mobility.state.position_millicells.x),
                z: millicells_to_cells(value.mobility.state.position_millicells.y),
            },
            velocity: Velocity {
                x: millicells_to_cells(value.mobility.state.velocity_millicells_per_tick.x),
                z: millicells_to_cells(value.mobility.state.velocity_millicells_per_tick.y),
            },
            facing: value.mobility.state.facing,
            previous_facing: value.mobility.state.facing,
            facing_blend: 1.0,
            facing_pose_handoff: true,
            locomotion,
            scene_mode: crate::state::SceneMode::Studio,
            action,
            previous_upper_body_action: upper_body_action,
            upper_body_action,
            expression: legacy_expression(&value.face.state),
            mouth: legacy_mouth(value.mouth.state.rendered_pose),
            walk_phase: phase_fraction(value.mobility.state.locomotion_phase_tick, 60),
            speed_ratio: legacy_speed_ratio(value.mobility.state.velocity_millicells_per_tick),
            contact_marker,
            planted_foot,
            pose_id: value.pose.state.pose_id.as_ref().map(ToString::to_string),
            previous_pose_id: None,
            pose_blend: percent_fraction(value.pose.state.transition_progress_percent),
            pose_handoff: value.pose.state.transition_progress_percent == 100,
            pose_generation: value.pose.header.generation.0,
            pose_expires_at_tick: value.pose.header.deadline_tick.map(|tick| tick.0),
            pose_clip_id: value.pose.state.clip_id.as_ref().map(ToString::to_string),
            pose_clip_step: value.pose.state.sample_index.map(|step| step as usize),
            pose_clip_generation: value.pose.header.generation.0,
            blink_phase: legacy_blink(value.face.state.blink),
            staff_state,
            previous_staff_state: staff_state,
            effect_state,
            upper_body_blend: percent_fraction(value.pose.state.transition_progress_percent),
            staff_blend: 1.0,
            speech_id: value
                .speech
                .state
                .utterance_id
                .as_ref()
                .map(ToString::to_string),
            time_seconds: ticks_to_seconds(simulation_tick),
            action_until: value
                .gesture
                .header
                .deadline_tick
                .map_or(0.0, |tick| ticks_to_seconds(tick.0)),
            speech_until: value
                .speech
                .header
                .deadline_tick
                .map_or(0.0, |tick| ticks_to_seconds(tick.0)),
            target_point: None,
            screen_position: ScreenPoint {
                x: millicells_to_cells(value.pose.state.visual_root_millicells.x),
                y: millicells_to_cells(value.pose.state.visual_root_millicells.y),
            },
            display_scale: 1.0,
            simulation_tick,
            desired_heading: heading,
            presented_heading: heading,
            pending_direction: None,
            direction_candidate_ticks: 0,
            channel_generations: ChannelGenerations {
                locomotion: value.mobility.header.generation.0,
                facing: value.mobility.header.generation.0,
                upper_body: value.gesture.header.generation.0,
                staff: value.staff.header.generation.0,
                expression: value.face.header.generation.0,
                blink: value.face.header.generation.0,
                speech: value.speech.header.generation.0,
                effects: value.effects.header.generation.0,
            },
            reconnect_count: value.control.state.reconnect_count,
        }
    }
}

fn legacy_action(value: &AvatarSemanticStateV1) -> Action {
    if let Some(gesture) = value.gesture.state.gesture {
        return match gesture {
            GestureKind::Acknowledge | GestureKind::Reassure | GestureKind::Yield => {
                Action::Reaction
            }
            GestureKind::Explain => Action::Explaining,
            GestureKind::Point => Action::Pointing,
            GestureKind::Think => Action::Thinking,
            GestureKind::Celebrate => Action::MagicCast,
        };
    }
    match value.conversation.state.turn_state {
        ChatTurnState::Speaking | ChatTurnState::PreparingResponse => Action::Speaking,
        ChatTurnState::Thinking | ChatTurnState::ToolWait => Action::Thinking,
        ChatTurnState::Celebrating => Action::MagicCast,
        ChatTurnState::Clarifying => Action::Explaining,
        ChatTurnState::Error | ChatTurnState::Interrupted => Action::Reaction,
        ChatTurnState::Idle | ChatTurnState::Listening => match value.mobility.state.mode {
            MobilityModeV1::GroundStart
            | MobilityModeV1::GroundWalk
            | MobilityModeV1::GroundRun
            | MobilityModeV1::GroundStop => Action::Walking,
            MobilityModeV1::GroundedIdle
            | MobilityModeV1::Takeoff
            | MobilityModeV1::Hover
            | MobilityModeV1::Travel
            | MobilityModeV1::Bank
            | MobilityModeV1::Fall
            | MobilityModeV1::Land => Action::Idle,
        },
    }
}

const fn legacy_upper_body(gesture: Option<GestureKind>) -> UpperBodyAction {
    match gesture {
        None => UpperBodyAction::None,
        Some(GestureKind::Explain | GestureKind::Reassure | GestureKind::Yield) => {
            UpperBodyAction::Explain
        }
        Some(GestureKind::Point) => UpperBodyAction::Point,
        Some(GestureKind::Think) => UpperBodyAction::Think,
        Some(GestureKind::Celebrate) => UpperBodyAction::Cast,
        Some(GestureKind::Acknowledge) => UpperBodyAction::React,
    }
}

const fn legacy_expression(face: &FaceStateV1) -> Expression {
    if let Some(expression) = face.transient_expression {
        return match expression {
            FaceExpressionV1::Neutral => Expression::Neutral,
            FaceExpressionV1::Happy => Expression::Happy,
            FaceExpressionV1::Thinking => Expression::Thinking,
            FaceExpressionV1::Surprised => Expression::Surprised,
            FaceExpressionV1::Worried => Expression::Worried,
            FaceExpressionV1::Amused => Expression::Amused,
            FaceExpressionV1::Confident => Expression::Confident,
            FaceExpressionV1::Focused => Expression::Focused,
            FaceExpressionV1::Skeptical => Expression::Skeptical,
            FaceExpressionV1::Explaining => Expression::Explaining,
        };
    }
    match face.emotion {
        Emotion::Neutral => Expression::Neutral,
        Emotion::Joy | Emotion::Love => Expression::Happy,
        Emotion::Sadness | Emotion::Fear | Emotion::Guilt | Emotion::Shame => Expression::Worried,
        Emotion::Surprise => Expression::Surprised,
        Emotion::Pride => Expression::Confident,
        Emotion::Anger | Emotion::Disgust => Expression::Skeptical,
    }
}

const fn legacy_mouth(value: RenderedMouthPose) -> MouthShape {
    match value {
        RenderedMouthPose::Closed => MouthShape::Closed,
        RenderedMouthPose::OpenSmall => MouthShape::OpenSmall,
        RenderedMouthPose::OpenMedium => MouthShape::OpenMedium,
        RenderedMouthPose::OpenWide => MouthShape::OpenWide,
        RenderedMouthPose::Rounded => MouthShape::Rounded,
        RenderedMouthPose::Smile => MouthShape::Smile,
        RenderedMouthPose::Frown => MouthShape::Frown,
    }
}

const fn legacy_staff(value: StaffModeV1) -> StaffState {
    match value {
        StaffModeV1::Held | StaffModeV1::Guard | StaffModeV1::Block => StaffState::Held,
        StaffModeV1::Planted => StaffState::Rest,
        StaffModeV1::Thrust => StaffState::Point,
        StaffModeV1::Spin | StaffModeV1::Raised => StaffState::Cast,
    }
}

fn legacy_effect(value: &AvatarSemanticStateV1) -> EffectState {
    value
        .effects
        .state
        .instances
        .iter()
        .fold(EffectState::None, |state, effect| {
            match (state, effect.kind) {
                (_, EffectKindV1::Magic) => EffectState::Cast,
                (EffectState::None, EffectKindV1::Reaction | EffectKindV1::Emphasis) => {
                    EffectState::Reaction
                }
                (current, EffectKindV1::Reaction | EffectKindV1::Emphasis) => current,
            }
        })
}

const fn legacy_locomotion(value: MobilityModeV1) -> Locomotion {
    match value {
        MobilityModeV1::GroundStart
        | MobilityModeV1::GroundWalk
        | MobilityModeV1::GroundRun
        | MobilityModeV1::GroundStop => Locomotion::Walking,
        MobilityModeV1::Bank => Locomotion::Turn,
        MobilityModeV1::GroundedIdle
        | MobilityModeV1::Takeoff
        | MobilityModeV1::Hover
        | MobilityModeV1::Travel
        | MobilityModeV1::Fall
        | MobilityModeV1::Land => Locomotion::Idle,
    }
}

const fn legacy_contact_marker(phase_tick: u32) -> ContactMarker {
    match phase_tick % 8 {
        0 => ContactMarker::LeftStance,
        1 => ContactMarker::LeftToeOff,
        2 => ContactMarker::LeftPassing,
        3 => ContactMarker::RightHeelStrike,
        4 => ContactMarker::RightStance,
        5 => ContactMarker::RightToeOff,
        6 => ContactMarker::RightPassing,
        _ => ContactMarker::LeftHeelStrike,
    }
}

fn legacy_planted_foot(contacts: &[ContactPointV1]) -> PlantedFoot {
    let left = contacts.contains(&ContactPointV1::LeftFoot);
    let right = contacts.contains(&ContactPointV1::RightFoot);
    match (left, right) {
        (true, true) => PlantedFoot::Both,
        (true, false) => PlantedFoot::Left,
        (false, true) => PlantedFoot::Right,
        (false, false) => PlantedFoot::None,
    }
}

const fn legacy_blink(value: BlinkStateV1) -> f32 {
    match value {
        BlinkStateV1::Open => 0.0,
        BlinkStateV1::Closing => 0.5,
        BlinkStateV1::Closed => 1.0,
        BlinkStateV1::Opening => 0.5,
    }
}

const fn legacy_heading(value: Direction) -> f32 {
    match value {
        Direction::South => 0.0,
        Direction::SouthWest => 45.0,
        Direction::West => 90.0,
        Direction::NorthWest => 135.0,
        Direction::North => 180.0,
        Direction::NorthEast => 225.0,
        Direction::East => 270.0,
        Direction::SouthEast => 315.0,
    }
}

fn legacy_speed_ratio(velocity: Point2iV1) -> f32 {
    let magnitude = velocity
        .x
        .unsigned_abs()
        .saturating_add(velocity.y.unsigned_abs());
    (magnitude.min(1_000) as f32) / 1_000.0
}

fn millicells_to_cells(value: i32) -> f32 {
    value as f32 / 1_000.0
}

fn percent_fraction(value: u8) -> f32 {
    f32::from(value) / 100.0
}

fn phase_fraction(value: u32, cycle: u32) -> f32 {
    (value % cycle) as f32 / cycle as f32
}

fn ticks_to_seconds(value: u64) -> f32 {
    value as f32 / 60.0
}
