use crate::chat_event::{
    CancelReason, ChatEventV1, ChatTurnState, CommandId, ContractErrorCode, DiagnosticGeometryId,
    Emotion, GestureKind, MotionProfile, SessionId, SourceId, SourceKind, SpeechPlanV1, TurnId,
    UtteranceId, CHAT_EVENT_SCHEMA_VERSION, MAX_DURATION_MS, MAX_INGRESS_BYTES, MAX_TTL_MS,
};
use serde::{Deserialize, Serialize};
use std::fmt;

pub const COMMAND_SCHEMA_VERSION: u16 = CHAT_EVENT_SCHEMA_VERSION;
pub const MAX_FUTURE_APPLY_TICKS: u64 = 120;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CommandErrorCode {
    MalformedJson,
    PayloadTooLarge,
    UnsupportedSchemaVersion,
    InvalidIdentifier,
    InvalidTtl,
    InvalidApplyTick,
    InvalidCommand,
    OperationMismatch,
    StaleSourceSequence,
    Expired,
    Unauthorized,
    QueueFull,
    Conflict,
}

impl CommandErrorCode {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::MalformedJson => "malformed_json",
            Self::PayloadTooLarge => "payload_too_large",
            Self::UnsupportedSchemaVersion => "unsupported_schema_version",
            Self::InvalidIdentifier => "invalid_identifier",
            Self::InvalidTtl => "invalid_ttl",
            Self::InvalidApplyTick => "invalid_apply_tick",
            Self::InvalidCommand => "invalid_command",
            Self::OperationMismatch => "operation_mismatch",
            Self::StaleSourceSequence => "stale_source_sequence",
            Self::Expired => "expired",
            Self::Unauthorized => "unauthorized",
            Self::QueueFull => "queue_full",
            Self::Conflict => "conflict",
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CommandContractError {
    pub code: CommandErrorCode,
    pub field: &'static str,
}

impl CommandContractError {
    pub const fn new(code: CommandErrorCode, field: &'static str) -> Self {
        Self { code, field }
    }
}

impl fmt::Display for CommandContractError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}:{}", self.code.as_str(), self.field)
    }
}

impl std::error::Error for CommandContractError {}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CommandRequestV1 {
    pub schema_version: u16,
    pub command_id: CommandId,
    pub source_id: SourceId,
    pub source_kind: SourceKind,
    pub source_sequence: u64,
    pub requested_apply_tick: Option<u64>,
    pub ttl_ms: u32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub chat_correlation: Option<ChatCommandCorrelationV1>,
    pub command: SemanticCommandV1,
}

impl CommandRequestV1 {
    pub fn from_json(input: &[u8], current_tick: u64) -> Result<Self, CommandContractError> {
        if input.len() > MAX_INGRESS_BYTES {
            return Err(CommandContractError::new(
                CommandErrorCode::PayloadTooLarge,
                "command_request",
            ));
        }
        let request: Self = serde_json::from_slice(input)
            .map_err(|error| classify_serde_error(&error, "command_request"))?;
        request.validate(current_tick)?;
        Ok(request)
    }

    pub fn from_public_json(input: &[u8], current_tick: u64) -> Result<Self, CommandContractError> {
        let request = Self::from_json(input, current_tick)?;
        request.validate_public()?;
        Ok(request)
    }

    pub fn validate(&self, current_tick: u64) -> Result<(), CommandContractError> {
        if self.schema_version != COMMAND_SCHEMA_VERSION {
            return Err(CommandContractError::new(
                CommandErrorCode::UnsupportedSchemaVersion,
                "schema_version",
            ));
        }
        if self.ttl_ms > MAX_TTL_MS {
            return Err(CommandContractError::new(
                CommandErrorCode::InvalidTtl,
                "ttl_ms",
            ));
        }
        validate_apply_tick(self.requested_apply_tick, current_tick)?;
        let chat_command = matches!(self.command, SemanticCommandV1::ApplyChatEvent(_));
        if chat_command != self.chat_correlation.is_some() {
            return Err(CommandContractError::new(
                CommandErrorCode::InvalidCommand,
                "chat_correlation",
            ));
        }
        self.command.validate()
    }

    pub fn validate_public(&self) -> Result<(), CommandContractError> {
        if matches!(self.command, SemanticCommandV1::DiagnosticPose(_)) {
            return Err(CommandContractError::new(
                CommandErrorCode::Unauthorized,
                "command",
            ));
        }
        Ok(())
    }

    pub fn to_canonical_json(&self) -> Result<Vec<u8>, serde_json::Error> {
        serde_json::to_vec(self)
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ChatCommandCorrelationV1 {
    pub session_id: SessionId,
    pub turn_id: Option<TurnId>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub previous_turn_id: Option<TurnId>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(
    tag = "type",
    content = "payload",
    rename_all = "snake_case",
    deny_unknown_fields
)]
pub enum SemanticCommandV1 {
    ApplyChatEvent(ChatEventV1),
    SetMotionIntent(MotionIntentV1),
    StartGesture(GestureRequestV1),
    SetEmotion(EmotionRequestV1),
    PrepareSpeech(SpeechPlanV1),
    StartSpeech(UtteranceId),
    UpdateSpeechProgress {
        utterance_id: UtteranceId,
        elapsed_ms: u32,
    },
    PauseSpeech(UtteranceId),
    ResumeSpeech(UtteranceId),
    CancelSpeech {
        utterance_id: UtteranceId,
        reason: CancelReason,
    },
    CompleteSpeech(UtteranceId),
    Stop(StopScope),
    Reset(ResetScope),
    Legacy(LegacyCommandV1),
    DiagnosticPose(DiagnosticPoseRequest),
}

impl SemanticCommandV1 {
    pub fn validate(&self) -> Result<(), CommandContractError> {
        match self {
            Self::ApplyChatEvent(event) => event.validate().map_err(map_chat_error),
            Self::SetMotionIntent(request) => request.validate(),
            Self::StartGesture(request) => request.validate(),
            Self::SetEmotion(request) => request.validate(),
            Self::PrepareSpeech(plan) => plan.validate().map_err(map_chat_error),
            Self::UpdateSpeechProgress { elapsed_ms, .. } if *elapsed_ms > MAX_DURATION_MS => Err(
                CommandContractError::new(CommandErrorCode::InvalidCommand, "command.elapsed_ms"),
            ),
            Self::StartSpeech(_)
            | Self::UpdateSpeechProgress { .. }
            | Self::PauseSpeech(_)
            | Self::ResumeSpeech(_)
            | Self::CancelSpeech { .. }
            | Self::CompleteSpeech(_)
            | Self::Stop(_)
            | Self::Reset(_)
            | Self::Legacy(_)
            | Self::DiagnosticPose(_) => Ok(()),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MotionIntentV1 {
    pub state: ChatTurnState,
    pub intensity: u8,
    pub profile: MotionProfile,
}

impl MotionIntentV1 {
    fn validate(&self) -> Result<(), CommandContractError> {
        validate_percent(self.intensity, "command.intensity")
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GestureRequestV1 {
    pub gesture: GestureKind,
    pub intensity: u8,
    pub duration_ms: Option<u32>,
}

impl GestureRequestV1 {
    fn validate(&self) -> Result<(), CommandContractError> {
        validate_percent(self.intensity, "command.intensity")?;
        validate_optional_duration(self.duration_ms, "command.duration_ms")
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EmotionRequestV1 {
    pub emotion: Emotion,
    pub intensity: u8,
    pub duration_ms: Option<u32>,
}

impl EmotionRequestV1 {
    fn validate(&self) -> Result<(), CommandContractError> {
        validate_percent(self.intensity, "command.intensity")?;
        validate_optional_duration(self.duration_ms, "command.duration_ms")
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StopScope {
    All,
    Speech,
    Gesture,
    Mobility,
    Effects,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ResetScope {
    Session,
    Turn,
    Performance,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LegacyCommandKind {
    Idle,
    Walk,
    Talk,
    Think,
    Celebrate,
    Stop,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LegacyCommandV1 {
    pub command: LegacyCommandKind,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DiagnosticPoseRequest {
    pub geometry_id: DiagnosticGeometryId,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CommandEnvelopeV1 {
    pub schema_version: u16,
    pub command_id: CommandId,
    pub source_id: SourceId,
    pub source_kind: SourceKind,
    pub source_sequence: u64,
    pub requested_apply_tick: Option<u64>,
    pub ttl_ms: u32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub chat_correlation: Option<ChatCommandCorrelationV1>,
    pub command: SemanticCommandV1,
    pub server_sequence: u64,
    pub accepted_tick: u64,
    pub apply_tick: u64,
    pub expires_tick: u64,
}

impl CommandEnvelopeV1 {
    pub fn assign(
        request: CommandRequestV1,
        server_sequence: u64,
        current_tick: u64,
    ) -> Result<Self, CommandContractError> {
        request.validate(current_tick)?;
        let apply_tick = request.requested_apply_tick.unwrap_or(current_tick + 1);
        let ttl_ticks = u64::from(request.ttl_ms)
            .checked_mul(60)
            .and_then(|scaled| scaled.checked_add(999))
            .map(|rounded| rounded / 1_000)
            .ok_or_else(|| CommandContractError::new(CommandErrorCode::InvalidTtl, "ttl_ms"))?
            .max(1);
        // Expiry is exclusive: the command is live only while tick < expires_tick.
        let expires_tick = apply_tick.checked_add(ttl_ticks).ok_or_else(|| {
            CommandContractError::new(CommandErrorCode::InvalidApplyTick, "expires_tick")
        })?;
        Ok(Self {
            schema_version: request.schema_version,
            command_id: request.command_id,
            source_id: request.source_id,
            source_kind: request.source_kind,
            source_sequence: request.source_sequence,
            requested_apply_tick: request.requested_apply_tick,
            ttl_ms: request.ttl_ms,
            chat_correlation: request.chat_correlation,
            command: request.command,
            server_sequence,
            accepted_tick: current_tick,
            apply_tick,
            expires_tick,
        })
    }

    pub const fn ordering_key(&self) -> (u64, u64) {
        (self.apply_tick, self.server_sequence)
    }

    pub const fn is_expired_at(&self, tick: u64) -> bool {
        tick >= self.expires_tick
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AckStatus {
    Accepted,
    Duplicate,
    RejectedInvalid,
    RejectedStale,
    RejectedExpired,
    RejectedUnauthorized,
    RejectedQueueFull,
    RejectedConflict,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(transparent)]
pub struct RuntimeEpoch(pub u64);

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CommandAckV1 {
    pub schema_version: u16,
    pub command_id: CommandId,
    pub status: AckStatus,
    pub source_sequence: u64,
    pub server_sequence: Option<u64>,
    pub accepted_tick: Option<u64>,
    pub apply_tick: Option<u64>,
    pub state_revision: u64,
    pub runtime_epoch: RuntimeEpoch,
    pub error_code: Option<CommandErrorCode>,
}

impl CommandAckV1 {
    pub fn accepted(
        envelope: &CommandEnvelopeV1,
        state_revision: u64,
        runtime_epoch: RuntimeEpoch,
    ) -> Self {
        Self {
            schema_version: COMMAND_SCHEMA_VERSION,
            command_id: envelope.command_id.clone(),
            status: AckStatus::Accepted,
            source_sequence: envelope.source_sequence,
            server_sequence: Some(envelope.server_sequence),
            accepted_tick: Some(envelope.accepted_tick),
            apply_tick: Some(envelope.apply_tick),
            state_revision,
            runtime_epoch,
            error_code: None,
        }
    }

    pub fn rejected(
        request: &CommandRequestV1,
        status: AckStatus,
        state_revision: u64,
        runtime_epoch: RuntimeEpoch,
        error_code: CommandErrorCode,
    ) -> Result<Self, CommandContractError> {
        if matches!(status, AckStatus::Accepted | AckStatus::Duplicate) {
            return Err(CommandContractError::new(
                CommandErrorCode::InvalidCommand,
                "ack.status",
            ));
        }
        Ok(Self {
            schema_version: COMMAND_SCHEMA_VERSION,
            command_id: request.command_id.clone(),
            status,
            source_sequence: request.source_sequence,
            server_sequence: None,
            accepted_tick: None,
            apply_tick: None,
            state_revision,
            runtime_epoch,
            error_code: Some(error_code),
        })
    }

    pub const fn is_terminal(&self) -> bool {
        true
    }
}

fn validate_apply_tick(
    requested_apply_tick: Option<u64>,
    current_tick: u64,
) -> Result<(), CommandContractError> {
    let earliest = current_tick.checked_add(1).ok_or_else(|| {
        CommandContractError::new(CommandErrorCode::InvalidApplyTick, "requested_apply_tick")
    })?;
    let latest = current_tick
        .checked_add(MAX_FUTURE_APPLY_TICKS)
        .ok_or_else(|| {
            CommandContractError::new(CommandErrorCode::InvalidApplyTick, "requested_apply_tick")
        })?;
    let Some(requested_apply_tick) = requested_apply_tick else {
        return Ok(());
    };
    if !(earliest..=latest).contains(&requested_apply_tick) {
        return Err(CommandContractError::new(
            CommandErrorCode::InvalidApplyTick,
            "requested_apply_tick",
        ));
    }
    Ok(())
}

fn validate_percent(value: u8, field: &'static str) -> Result<(), CommandContractError> {
    if value > 100 {
        return Err(CommandContractError::new(
            CommandErrorCode::InvalidCommand,
            field,
        ));
    }
    Ok(())
}

fn validate_optional_duration(
    value: Option<u32>,
    field: &'static str,
) -> Result<(), CommandContractError> {
    if let Some(value) = value {
        if value == 0 || value > MAX_DURATION_MS {
            return Err(CommandContractError::new(
                CommandErrorCode::InvalidCommand,
                field,
            ));
        }
    }
    Ok(())
}

fn map_chat_error(error: crate::chat_event::ContractError) -> CommandContractError {
    let code = match error.code {
        ContractErrorCode::OperationMismatch => CommandErrorCode::OperationMismatch,
        ContractErrorCode::InvalidIdentifier => CommandErrorCode::InvalidIdentifier,
        _ => CommandErrorCode::InvalidCommand,
    };
    CommandContractError::new(code, error.field)
}

fn classify_serde_error(error: &serde_json::Error, field: &'static str) -> CommandContractError {
    let message = error.to_string();
    if message.contains(ContractErrorCode::InvalidIdentifier.as_str()) {
        return CommandContractError::new(CommandErrorCode::InvalidIdentifier, "identifier");
    }
    CommandContractError::new(CommandErrorCode::MalformedJson, field)
}
