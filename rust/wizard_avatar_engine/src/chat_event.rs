use serde::de::Error as DeError;
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use std::fmt;

pub const CHAT_EVENT_SCHEMA_VERSION: u16 = 1;
pub const MAX_INGRESS_BYTES: usize = 64 * 1024;
pub const MAX_ID_BYTES: usize = 128;
pub const MAX_TTL_MS: u32 = 5_000;
pub const MAX_DURATION_MS: u32 = 1_800_000;
pub const MAX_VISEME_CUES: usize = 4_096;
pub const MAX_TEXT_LENGTH: u32 = 1_000_000;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContractErrorCode {
    MalformedJson,
    PayloadTooLarge,
    UnsupportedSchemaVersion,
    InvalidIdentifier,
    InvalidTtl,
    InvalidRange,
    InvalidLocale,
    InvalidContentHash,
    InvalidSpeechPlan,
    TooManyVisemeCues,
    NonMonotonicVisemeCues,
    CueOutOfBounds,
    InvalidSpeechMarker,
    OperationMismatch,
}

impl ContractErrorCode {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::MalformedJson => "malformed_json",
            Self::PayloadTooLarge => "payload_too_large",
            Self::UnsupportedSchemaVersion => "unsupported_schema_version",
            Self::InvalidIdentifier => "invalid_identifier",
            Self::InvalidTtl => "invalid_ttl",
            Self::InvalidRange => "invalid_range",
            Self::InvalidLocale => "invalid_locale",
            Self::InvalidContentHash => "invalid_content_hash",
            Self::InvalidSpeechPlan => "invalid_speech_plan",
            Self::TooManyVisemeCues => "too_many_viseme_cues",
            Self::NonMonotonicVisemeCues => "non_monotonic_viseme_cues",
            Self::CueOutOfBounds => "cue_out_of_bounds",
            Self::InvalidSpeechMarker => "invalid_speech_marker",
            Self::OperationMismatch => "operation_mismatch",
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ContractError {
    pub code: ContractErrorCode,
    pub field: &'static str,
}

impl ContractError {
    pub const fn new(code: ContractErrorCode, field: &'static str) -> Self {
        Self { code, field }
    }
}

impl fmt::Display for ContractError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}:{}", self.code.as_str(), self.field)
    }
}

impl std::error::Error for ContractError {}

fn validate_identifier(value: &str) -> Result<(), ContractError> {
    if value.is_empty()
        || value.len() > MAX_ID_BYTES
        || !value.bytes().all(|byte| byte.is_ascii_graphic())
    {
        return Err(ContractError::new(
            ContractErrorCode::InvalidIdentifier,
            "identifier",
        ));
    }
    Ok(())
}

macro_rules! opaque_id {
    ($name:ident) => {
        #[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
        pub struct $name(String);

        impl $name {
            pub fn new(value: impl Into<String>) -> Result<Self, ContractError> {
                let value = value.into();
                validate_identifier(&value)?;
                Ok(Self(value))
            }

            pub fn as_str(&self) -> &str {
                &self.0
            }
        }

        impl fmt::Display for $name {
            fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
                formatter.write_str(&self.0)
            }
        }

        impl TryFrom<String> for $name {
            type Error = ContractError;

            fn try_from(value: String) -> Result<Self, Self::Error> {
                Self::new(value)
            }
        }

        impl TryFrom<&str> for $name {
            type Error = ContractError;

            fn try_from(value: &str) -> Result<Self, Self::Error> {
                Self::new(value)
            }
        }

        impl Serialize for $name {
            fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
            where
                S: Serializer,
            {
                serializer.serialize_str(&self.0)
            }
        }

        impl<'de> Deserialize<'de> for $name {
            fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
            where
                D: Deserializer<'de>,
            {
                let value = String::deserialize(deserializer)?;
                Self::new(value).map_err(D::Error::custom)
            }
        }
    };
}

opaque_id!(EventId);
opaque_id!(CommandId);
opaque_id!(SessionId);
opaque_id!(TurnId);
opaque_id!(UtteranceId);
opaque_id!(OperationId);
opaque_id!(SourceId);
opaque_id!(DiagnosticGeometryId);

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SourceKind {
    Browser,
    Chatbot,
    Tts,
    Automation,
    Demo,
    System,
    LegacyAdapter,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ChatTurnState {
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
}

impl ChatTurnState {
    pub const ALL: [Self; 10] = [
        Self::Idle,
        Self::Listening,
        Self::Thinking,
        Self::PreparingResponse,
        Self::Speaking,
        Self::Clarifying,
        Self::ToolWait,
        Self::Error,
        Self::Celebrating,
        Self::Interrupted,
    ];
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MotionProfile {
    Full,
    Reduced,
}

impl MotionProfile {
    pub const ALL: [Self; 2] = [Self::Full, Self::Reduced];
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ChatEventEnvelopeV1 {
    pub schema_version: u16,
    pub event_id: EventId,
    pub session_id: SessionId,
    pub turn_id: Option<TurnId>,
    pub source_id: SourceId,
    pub source_kind: SourceKind,
    pub source_sequence: u64,
    pub requested_apply_tick: Option<u64>,
    pub ttl_ms: u32,
    pub event: ChatEventV1,
}

impl ChatEventEnvelopeV1 {
    pub fn from_json(input: &[u8]) -> Result<Self, ContractError> {
        if input.len() > MAX_INGRESS_BYTES {
            return Err(ContractError::new(
                ContractErrorCode::PayloadTooLarge,
                "chat_event_envelope",
            ));
        }
        let envelope: Self = serde_json::from_slice(input)
            .map_err(|error| classify_serde_error(&error, "chat_event_envelope"))?;
        envelope.validate()?;
        Ok(envelope)
    }

    pub fn validate(&self) -> Result<(), ContractError> {
        if self.schema_version != CHAT_EVENT_SCHEMA_VERSION {
            return Err(ContractError::new(
                ContractErrorCode::UnsupportedSchemaVersion,
                "schema_version",
            ));
        }
        if self.ttl_ms > MAX_TTL_MS {
            return Err(ContractError::new(ContractErrorCode::InvalidTtl, "ttl_ms"));
        }
        self.event.validate()
    }

    pub fn to_canonical_json(&self) -> Result<Vec<u8>, serde_json::Error> {
        serde_json::to_vec(self)
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(
    tag = "type",
    content = "payload",
    rename_all = "snake_case",
    deny_unknown_fields
)]
pub enum ChatEventV1 {
    SessionStarted {
        locale: Option<String>,
    },
    SessionEnded {
        reason: SessionEndReason,
    },
    UserTurnStarted,
    UserTurnCommitted,
    UserTurnCancelled,
    AssistantThinkingStarted,
    AssistantThinkingEnded,
    AssistantResponsePlanned {
        speech_expected: bool,
    },
    ClarificationRequested(ClarificationRequestV1),
    ToolWaitStarted(ToolWaitStartedV1),
    ToolWaitEnded(ToolWaitEndedV1),
    AssistantError(AssistantErrorV1),
    CelebrationRequested(CelebrationRequestV1),
    SpeechPrepared(SpeechPlanV1),
    SpeechStarted {
        utterance_id: UtteranceId,
    },
    SpeechProgress {
        utterance_id: UtteranceId,
        elapsed_ms: u32,
    },
    SpeechPaused {
        utterance_id: UtteranceId,
    },
    SpeechResumed {
        utterance_id: UtteranceId,
    },
    SpeechCancelled {
        utterance_id: UtteranceId,
        reason: CancelReason,
    },
    SpeechCompleted {
        utterance_id: UtteranceId,
    },
    SpeechFailed {
        utterance_id: UtteranceId,
        code: SpeechFailureCode,
    },
    EmotionHint(EmotionHintV1),
    GestureHint(GestureHintV1),
    AttentionTarget(AttentionTargetV1),
    SafetyClamp(SafetyClampV1),
    ConnectionDegraded,
    ConnectionRecovered,
}

impl ChatEventV1 {
    pub fn validate(&self) -> Result<(), ContractError> {
        match self {
            Self::SessionStarted { locale } => validate_locale(locale.as_deref()),
            Self::ClarificationRequested(payload) => payload.validate(),
            Self::ToolWaitStarted(payload) => payload.validate(),
            Self::ToolWaitEnded(_) => Ok(()),
            Self::AssistantError(_) => Ok(()),
            Self::CelebrationRequested(payload) => payload.validate(),
            Self::SpeechPrepared(plan) => plan.validate(),
            Self::SpeechProgress { elapsed_ms, .. } if *elapsed_ms > MAX_DURATION_MS => Err(
                ContractError::new(ContractErrorCode::InvalidRange, "elapsed_ms"),
            ),
            Self::EmotionHint(payload) => payload.validate(),
            Self::GestureHint(payload) => payload.validate(),
            Self::AttentionTarget(payload) => payload.validate(),
            Self::SessionEnded { .. }
            | Self::UserTurnStarted
            | Self::UserTurnCommitted
            | Self::UserTurnCancelled
            | Self::AssistantThinkingStarted
            | Self::AssistantThinkingEnded
            | Self::AssistantResponsePlanned { .. }
            | Self::SpeechStarted { .. }
            | Self::SpeechProgress { .. }
            | Self::SpeechPaused { .. }
            | Self::SpeechResumed { .. }
            | Self::SpeechCancelled { .. }
            | Self::SpeechCompleted { .. }
            | Self::SpeechFailed { .. }
            | Self::SafetyClamp(_)
            | Self::ConnectionDegraded
            | Self::ConnectionRecovered => Ok(()),
        }
    }

    pub const fn conversation_state(&self) -> Option<ChatTurnState> {
        match self {
            Self::SessionStarted { .. } | Self::SessionEnded { .. } => Some(ChatTurnState::Idle),
            Self::UserTurnStarted => Some(ChatTurnState::Listening),
            Self::UserTurnCommitted | Self::AssistantThinkingStarted => {
                Some(ChatTurnState::Thinking)
            }
            Self::AssistantThinkingEnded
            | Self::ToolWaitEnded(_)
            | Self::SpeechCompleted { .. }
            | Self::ConnectionRecovered => Some(ChatTurnState::Idle),
            Self::AssistantResponsePlanned { .. } | Self::SpeechPrepared(_) => {
                Some(ChatTurnState::PreparingResponse)
            }
            Self::SpeechStarted { .. }
            | Self::SpeechProgress { .. }
            | Self::SpeechPaused { .. }
            | Self::SpeechResumed { .. } => Some(ChatTurnState::Speaking),
            Self::ClarificationRequested(_) => Some(ChatTurnState::Clarifying),
            Self::ToolWaitStarted(_) => Some(ChatTurnState::ToolWait),
            Self::AssistantError(_) | Self::SpeechFailed { .. } => Some(ChatTurnState::Error),
            Self::CelebrationRequested(_) => Some(ChatTurnState::Celebrating),
            Self::UserTurnCancelled | Self::SpeechCancelled { .. } => {
                Some(ChatTurnState::Interrupted)
            }
            Self::EmotionHint(_)
            | Self::GestureHint(_)
            | Self::AttentionTarget(_)
            | Self::SafetyClamp(_)
            | Self::ConnectionDegraded => None,
        }
    }
}

fn validate_locale(locale: Option<&str>) -> Result<(), ContractError> {
    let Some(locale) = locale else {
        return Ok(());
    };
    if locale.is_empty()
        || locale.len() > 35
        || !locale
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'-')
    {
        return Err(ContractError::new(
            ContractErrorCode::InvalidLocale,
            "locale",
        ));
    }
    Ok(())
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ClarificationRequestV1 {
    pub reason: ClarificationReason,
    pub urgency: u8,
}

impl ClarificationRequestV1 {
    pub fn validate(&self) -> Result<(), ContractError> {
        validate_percent(self.urgency, "urgency")
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ToolWaitStartedV1 {
    pub operation_id: OperationId,
    pub kind: ToolWaitKind,
    pub expected_duration_ms: Option<u32>,
}

impl ToolWaitStartedV1 {
    pub fn validate(&self) -> Result<(), ContractError> {
        validate_optional_duration(self.expected_duration_ms, "expected_duration_ms")
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ToolWaitEndedV1 {
    pub operation_id: OperationId,
    pub outcome: ToolWaitOutcome,
}

impl ToolWaitEndedV1 {
    pub fn validate_against(
        &self,
        active_operation: Option<&OperationId>,
    ) -> Result<(), ContractError> {
        if active_operation != Some(&self.operation_id) {
            return Err(ContractError::new(
                ContractErrorCode::OperationMismatch,
                "operation_id",
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AssistantErrorV1 {
    pub code: AssistantErrorCode,
    pub recoverable: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CelebrationRequestV1 {
    pub reason: CelebrationReason,
    pub intensity: u8,
}

impl CelebrationRequestV1 {
    pub fn validate(&self) -> Result<(), ContractError> {
        validate_percent(self.intensity, "intensity")
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ClarificationReason {
    MissingInformation,
    AmbiguousRequest,
    ConfirmationRequired,
    UnsupportedRequest,
    Other,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ToolWaitKind {
    Retrieval,
    Computation,
    ExternalAction,
    FileOperation,
    Other,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ToolWaitOutcome {
    Completed,
    Failed,
    Cancelled,
    TimedOut,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AssistantErrorCode {
    InvalidRequest,
    UpstreamUnavailable,
    ToolFailure,
    NetworkFailure,
    RateLimited,
    SafetyBlocked,
    Internal,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CelebrationReason {
    TaskCompleted,
    MilestoneReached,
    UserSuccess,
    PositiveFeedback,
    Other,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SessionEndReason {
    UserEnded,
    AssistantEnded,
    Timeout,
    ConnectionLost,
    Shutdown,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CancelReason {
    UserInterrupted,
    Superseded,
    StopRequested,
    SessionEnded,
    SafetyClamp,
    UpstreamCancelled,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SpeechFailureCode {
    UpstreamUnavailable,
    InvalidTiming,
    PlaybackFailed,
    Cancelled,
    Internal,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Emotion {
    Neutral,
    Joy,
    Sadness,
    Anger,
    Fear,
    Shame,
    Disgust,
    Surprise,
    Pride,
    Guilt,
    Love,
}

impl Emotion {
    pub const ALL: [Self; 11] = [
        Self::Neutral,
        Self::Joy,
        Self::Sadness,
        Self::Anger,
        Self::Fear,
        Self::Shame,
        Self::Disgust,
        Self::Surprise,
        Self::Pride,
        Self::Guilt,
        Self::Love,
    ];
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EmotionHintV1 {
    pub emotion: Emotion,
    pub intensity: u8,
    pub confidence: u8,
    pub duration_ms: Option<u32>,
}

impl EmotionHintV1 {
    pub fn validate(&self) -> Result<(), ContractError> {
        validate_percent(self.intensity, "intensity")?;
        validate_percent(self.confidence, "confidence")?;
        validate_optional_duration(self.duration_ms, "duration_ms")
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GestureKind {
    Acknowledge,
    Explain,
    Point,
    Think,
    Reassure,
    Celebrate,
    Yield,
}

impl GestureKind {
    pub const ALL: [Self; 7] = [
        Self::Acknowledge,
        Self::Explain,
        Self::Point,
        Self::Think,
        Self::Reassure,
        Self::Celebrate,
        Self::Yield,
    ];
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GestureHintV1 {
    pub gesture: GestureKind,
    pub intensity: u8,
}

impl GestureHintV1 {
    pub fn validate(&self) -> Result<(), ContractError> {
        validate_percent(self.intensity, "intensity")
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AttentionTarget {
    User,
    Content,
    Staff,
    Down,
    AwayLeft,
    AwayRight,
    Neutral,
}

impl AttentionTarget {
    pub const ALL: [Self; 7] = [
        Self::User,
        Self::Content,
        Self::Staff,
        Self::Down,
        Self::AwayLeft,
        Self::AwayRight,
        Self::Neutral,
    ];
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AttentionTargetV1 {
    pub target: AttentionTarget,
    pub hold_ms: u32,
    pub return_to_user: bool,
}

impl AttentionTargetV1 {
    pub fn validate(&self) -> Result<(), ContractError> {
        if self.hold_ms > MAX_DURATION_MS {
            return Err(ContractError::new(
                ContractErrorCode::InvalidRange,
                "hold_ms",
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SafetyScope {
    All,
    Speech,
    Gesture,
    Mobility,
    Effects,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SafetyClampV1 {
    pub scope: SafetyScope,
    pub active: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TimingSource {
    TimedVisemes,
    DurationOnly,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
#[allow(clippy::upper_case_acronyms)]
pub enum Viseme {
    Rest,
    #[serde(rename = "mbp")]
    MBP,
    #[serde(rename = "fv")]
    FV,
    #[serde(rename = "th")]
    TH,
    #[serde(rename = "dtln")]
    DTLN,
    #[serde(rename = "kg")]
    KG,
    #[serde(rename = "chsh")]
    CHSH,
    #[serde(rename = "sz")]
    SZ,
    #[serde(rename = "r")]
    R,
    #[serde(rename = "a")]
    A,
    #[serde(rename = "e")]
    E,
    #[serde(rename = "i")]
    I,
    #[serde(rename = "o")]
    O,
    #[serde(rename = "u")]
    U,
}

impl Viseme {
    pub const ALL: [Self; 14] = [
        Self::Rest,
        Self::MBP,
        Self::FV,
        Self::TH,
        Self::DTLN,
        Self::KG,
        Self::CHSH,
        Self::SZ,
        Self::R,
        Self::A,
        Self::E,
        Self::I,
        Self::O,
        Self::U,
    ];
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct VisemeCueV1 {
    pub start_ms: u32,
    pub end_ms: u32,
    pub viseme: Viseme,
    pub weight: u8,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SpeechMarkerKindV1 {
    PhraseStart,
    Accent,
    ClauseEnd,
    TurnEnd,
}

impl SpeechMarkerKindV1 {
    pub const ALL: [Self; 4] = [
        Self::PhraseStart,
        Self::Accent,
        Self::ClauseEnd,
        Self::TurnEnd,
    ];
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SpeechMarkerV1 {
    pub at_ms: u32,
    pub kind: SpeechMarkerKindV1,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SpeechPlanV1 {
    pub utterance_id: UtteranceId,
    pub text_hash: String,
    pub text_length: u32,
    pub duration_ms: u32,
    pub timing_source: TimingSource,
    pub cues: Vec<VisemeCueV1>,
    #[serde(default)]
    pub markers: Vec<SpeechMarkerV1>,
}

impl SpeechPlanV1 {
    pub fn validate(&self) -> Result<(), ContractError> {
        if self.duration_ms == 0 || self.duration_ms > MAX_DURATION_MS {
            return Err(ContractError::new(
                ContractErrorCode::InvalidSpeechPlan,
                "duration_ms",
            ));
        }
        if self.text_length > MAX_TEXT_LENGTH {
            return Err(ContractError::new(
                ContractErrorCode::InvalidRange,
                "text_length",
            ));
        }
        if self.text_hash.len() != 64
            || !self
                .text_hash
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
        {
            return Err(ContractError::new(
                ContractErrorCode::InvalidContentHash,
                "text_hash",
            ));
        }
        if self.cues.len() > MAX_VISEME_CUES {
            return Err(ContractError::new(
                ContractErrorCode::TooManyVisemeCues,
                "cues",
            ));
        }
        match self.timing_source {
            TimingSource::DurationOnly if !self.cues.is_empty() => {
                return Err(ContractError::new(
                    ContractErrorCode::InvalidSpeechPlan,
                    "timing_source",
                ));
            }
            TimingSource::TimedVisemes if self.cues.is_empty() => {
                return Err(ContractError::new(
                    ContractErrorCode::InvalidSpeechPlan,
                    "timing_source",
                ));
            }
            TimingSource::TimedVisemes | TimingSource::DurationOnly => {}
        }

        let mut previous_end = 0;
        for cue in &self.cues {
            if cue.weight > 100 {
                return Err(ContractError::new(
                    ContractErrorCode::InvalidRange,
                    "cues.weight",
                ));
            }
            if cue.start_ms >= cue.end_ms || cue.end_ms > self.duration_ms {
                return Err(ContractError::new(
                    ContractErrorCode::CueOutOfBounds,
                    "cues",
                ));
            }
            if cue.start_ms < previous_end {
                return Err(ContractError::new(
                    ContractErrorCode::NonMonotonicVisemeCues,
                    "cues",
                ));
            }
            previous_end = cue.end_ms;
        }

        let mut previous_marker_ms = 0;
        for (index, marker) in self.markers.iter().enumerate() {
            if marker.at_ms > self.duration_ms || (index > 0 && marker.at_ms < previous_marker_ms) {
                return Err(ContractError::new(
                    ContractErrorCode::InvalidSpeechMarker,
                    "markers",
                ));
            }
            previous_marker_ms = marker.at_ms;
        }
        Ok(())
    }
}

fn validate_percent(value: u8, field: &'static str) -> Result<(), ContractError> {
    if value > 100 {
        return Err(ContractError::new(ContractErrorCode::InvalidRange, field));
    }
    Ok(())
}

fn validate_optional_duration(
    value: Option<u32>,
    field: &'static str,
) -> Result<(), ContractError> {
    if let Some(value) = value {
        if value == 0 || value > MAX_DURATION_MS {
            return Err(ContractError::new(ContractErrorCode::InvalidRange, field));
        }
    }
    Ok(())
}

fn classify_serde_error(error: &serde_json::Error, field: &'static str) -> ContractError {
    let message = error.to_string();
    if message.contains(ContractErrorCode::InvalidIdentifier.as_str()) {
        return ContractError::new(ContractErrorCode::InvalidIdentifier, "identifier");
    }
    ContractError::new(ContractErrorCode::MalformedJson, field)
}
