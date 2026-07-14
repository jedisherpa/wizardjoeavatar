use crate::chat_event::{
    AssistantErrorV1, AttentionTarget, AttentionTargetV1, CancelReason, CelebrationRequestV1,
    ChatEventV1, ChatTurnState, ClarificationRequestV1, ContractError, EmotionHintV1,
    GestureHintV1, GestureKind, OperationId, SafetyClampV1, SafetyScope, SessionEndReason,
    SessionId, SpeechFailureCode, SpeechMarkerKindV1, SpeechPlanV1, TimingSource, ToolWaitEndedV1,
    ToolWaitKind, ToolWaitOutcome, ToolWaitStartedV1, TurnId, UtteranceId, Viseme,
};
use crate::chat_performance::RenderedMouthPose;
use crate::command::{CommandEnvelopeV1, SemanticCommandV1};
use crate::state_regions::{
    AvatarSemanticStateV1, BlinkStateV1, ContactPointV1, ControlStateV1, ConversationStateV1,
    EffectsStateV1, FaceExpressionV1, FaceStateV1, GestureInterruptPolicyV1, GestureMarkerV1,
    GesturePhaseV1, GestureRestorationPolicyV1, GestureStateV1, MobilityModeV1, MobilityStateV1,
    MouthStateV1, Point2iV1, RegionGeneration, RegionHeader, RegionKind, RegionMutationContextV1,
    RegionMutationV1, RegionPriority, SemanticTick, SessionModeV1, SessionStateV1, SpeechModeV1,
    SpeechStateV1, StateRegionError,
};
use serde::{Deserialize, Serialize};
use thiserror::Error;

pub const CHAT_POLICY_SCHEMA_VERSION: u16 = 1;
pub const POLICY_PRIORITY: RegionPriority = RegionPriority(40);
pub const MAX_POLICY_HOLD_TICKS: u64 = 600;
pub const MAX_COMPLETED_OPERATIONS: usize = 64;

const THINKING_HOLD_TICKS: u64 = 180;
const RESPONSE_HOLD_TICKS: u64 = 120;
const CLARIFICATION_HOLD_TICKS: u64 = 120;
const ERROR_HOLD_TICKS: u64 = 90;
const CELEBRATION_BASE_TICKS: u64 = 30;
const INTERRUPTED_HOLD_TICKS: u64 = 30;
const SAFETY_HOLD_TICKS: u64 = 30;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ChatPolicyOrderKeyV1 {
    pub apply_tick: SemanticTick,
    pub server_sequence: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OrderedChatEventV1 {
    pub apply_tick: SemanticTick,
    pub server_sequence: u64,
    pub session_id: SessionId,
    pub turn_id: Option<TurnId>,
    pub previous_turn_id: Option<TurnId>,
    pub event: ChatEventV1,
}

impl OrderedChatEventV1 {
    const fn order_key(&self) -> ChatPolicyOrderKeyV1 {
        ChatPolicyOrderKeyV1 {
            apply_tick: self.apply_tick,
            server_sequence: self.server_sequence,
        }
    }

    pub fn from_command_envelope(
        envelope: &CommandEnvelopeV1,
    ) -> Result<Option<Self>, ChatPolicyError> {
        let SemanticCommandV1::ApplyChatEvent(event) = &envelope.command else {
            return Ok(None);
        };
        let correlation = envelope
            .chat_correlation
            .as_ref()
            .ok_or(ChatPolicyError::MissingCommandCorrelation)?;
        Ok(Some(Self {
            apply_tick: SemanticTick(envelope.apply_tick),
            server_sequence: envelope.server_sequence,
            session_id: correlation.session_id.clone(),
            turn_id: correlation.turn_id.clone(),
            previous_turn_id: correlation.previous_turn_id.clone(),
            event: event.clone(),
        }))
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ChatPolicyDispositionV1 {
    Applied,
    Duplicate,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ChatPolicyOutcomeV1 {
    pub disposition: ChatPolicyDispositionV1,
    pub order: ChatPolicyOrderKeyV1,
    pub conversation_before: ChatTurnState,
    pub conversation_after: ChatTurnState,
    pub changed_regions: Vec<RegionKind>,
}

#[derive(Clone, Debug, Error, Eq, PartialEq)]
pub enum ChatPolicyError {
    #[error(transparent)]
    InvalidEvent(#[from] ContractError),
    #[error(transparent)]
    StateRegion(#[from] StateRegionError),
    #[error("event order {received:?} does not follow {previous:?}")]
    OutOfOrder {
        previous: ChatPolicyOrderKeyV1,
        received: ChatPolicyOrderKeyV1,
    },
    #[error("session correlation mismatch")]
    SessionMismatch,
    #[error("turn correlation mismatch")]
    TurnMismatch,
    #[error("chat command is missing session/turn correlation")]
    MissingCommandCorrelation,
    #[error("operation {received} does not match active operation {active:?}")]
    OperationMismatch {
        active: Option<OperationId>,
        received: OperationId,
    },
    #[error("operation {0} reused with a conflicting lifecycle payload")]
    OperationConflict(OperationId),
    #[error("operation {0} already completed")]
    OperationAlreadyCompleted(OperationId),
    #[error("utterance {received} does not match active utterance {active:?}")]
    UtteranceMismatch {
        active: Option<UtteranceId>,
        received: UtteranceId,
    },
    #[error("utterance {0} reused with a conflicting speech plan")]
    SpeechPlanConflict(UtteranceId),
    #[error("speech progress moved backward from {current_tick} to {received_tick}")]
    StaleSpeechProgress {
        current_tick: u32,
        received_tick: u32,
    },
    #[error("policy tick arithmetic overflow")]
    TickOverflow,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ActiveToolWaitV1 {
    operation_id: OperationId,
    kind: ToolWaitKind,
    expected_duration_ms: Option<u32>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct CompletedToolWaitV1 {
    operation_id: OperationId,
    outcome: ToolWaitOutcome,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct CompletedSessionEndV1 {
    session_id: SessionId,
    turn_id: Option<TurnId>,
    reason: SessionEndReason,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct SpeechPlanIdentityV1 {
    utterance_id: UtteranceId,
    content_free_hash64: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct ActiveAttentionHoldV1 {
    deadline_tick: SemanticTick,
    return_to_user: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
enum ConversationRetryV1 {
    UserTurnStarted,
    UserTurnCommitted,
    UserTurnCancelled,
    AssistantThinkingStarted,
    AssistantThinkingEnded,
    AssistantResponsePlanned { speech_expected: bool },
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
enum SpeechRetryV1 {
    Started {
        utterance_id: UtteranceId,
    },
    Progress {
        utterance_id: UtteranceId,
        elapsed_ms: u32,
    },
    Paused {
        utterance_id: UtteranceId,
    },
    Resumed {
        utterance_id: UtteranceId,
    },
    Cancelled {
        utterance_id: UtteranceId,
        reason: CancelReason,
    },
    Completed {
        utterance_id: UtteranceId,
    },
    Failed {
        utterance_id: UtteranceId,
        code: SpeechFailureCode,
    },
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ChatPolicyReducerV1 {
    pub schema_version: u16,
    semantic: AvatarSemanticStateV1,
    active_tool_wait: Option<ActiveToolWaitV1>,
    completed_tool_waits: Vec<CompletedToolWaitV1>,
    active_speech_plan: Option<SpeechPlanIdentityV1>,
    active_attention_hold: Option<ActiveAttentionHoldV1>,
    active_safety_scope_mask: u8,
    last_session_end: Option<CompletedSessionEndV1>,
    last_session_locale: Option<Option<String>>,
    last_conversation_retry: Option<ConversationRetryV1>,
    last_speech_retry: Option<SpeechRetryV1>,
    last_emotion: Option<EmotionHintV1>,
    last_gesture: Option<GestureHintV1>,
    last_attention: Option<AttentionTargetV1>,
    last_clarification: Option<ClarificationRequestV1>,
    last_error: Option<AssistantErrorV1>,
    last_celebration: Option<CelebrationRequestV1>,
    last_order: Option<ChatPolicyOrderKeyV1>,
}

impl ChatPolicyReducerV1 {
    #[must_use]
    pub fn new(character_id: impl Into<String>) -> Self {
        Self {
            schema_version: CHAT_POLICY_SCHEMA_VERSION,
            semantic: AvatarSemanticStateV1::new(character_id),
            active_tool_wait: None,
            completed_tool_waits: Vec::new(),
            active_speech_plan: None,
            active_attention_hold: None,
            active_safety_scope_mask: 0,
            last_session_end: None,
            last_session_locale: None,
            last_conversation_retry: None,
            last_speech_retry: None,
            last_emotion: None,
            last_gesture: None,
            last_attention: None,
            last_clarification: None,
            last_error: None,
            last_celebration: None,
            last_order: None,
        }
    }

    #[must_use]
    pub const fn semantic(&self) -> &AvatarSemanticStateV1 {
        &self.semantic
    }

    pub fn reduce(
        &mut self,
        input: OrderedChatEventV1,
    ) -> Result<ChatPolicyOutcomeV1, ChatPolicyError> {
        self.reduce_internal(input, None)
    }

    fn reduce_internal(
        &mut self,
        input: OrderedChatEventV1,
        fault: Option<TransactionFaultV1>,
    ) -> Result<ChatPolicyOutcomeV1, ChatPolicyError> {
        input.event.validate()?;
        let order = input.order_key();
        if let Some(previous) = self.last_order {
            if order <= previous {
                return Err(ChatPolicyError::OutOfOrder {
                    previous,
                    received: order,
                });
            }
        }
        let before = self.semantic.conversation.state.turn_state;
        let mut draft = self.clone();
        let mut transaction = PolicyTransactionV1::new(input.apply_tick, fault);

        if draft.is_exact_completed_session_end(&input) {
            draft.semantic.validate_at(input.apply_tick)?;
            draft.last_order = Some(order);
            let outcome = ChatPolicyOutcomeV1 {
                disposition: ChatPolicyDispositionV1::Duplicate,
                order,
                conversation_before: before,
                conversation_after: before,
                changed_regions: Vec::new(),
            };
            *self = draft;
            return Ok(outcome);
        }

        if draft.matching_tool_end_precedes_expiry(&input) {
            // A matching completion owns the equality boundary. It settles the active
            // operation first; every unrelated bounded region is swept immediately after.
            draft.validate_correlation(&input)?;
            draft.dispatch(&input, &mut transaction)?;
            draft.record_retry_identity(&input.event);
            draft.expire_at(input.apply_tick, &mut transaction)?;
            draft.enforce_active_safety_scopes(&mut transaction)?;
        } else {
            draft.expire_at(input.apply_tick, &mut transaction)?;
            draft.validate_correlation(&input)?;
            let exact_retry = draft.is_exact_active_retry(&input);
            if !exact_retry {
                let blocked_by_safety = draft.event_is_blocked_by_safety(&input.event);
                draft.dispatch(&input, &mut transaction)?;
                if !blocked_by_safety {
                    draft.record_retry_identity(&input.event);
                }
                draft.enforce_active_safety_scopes(&mut transaction)?;
            }
        }
        draft.semantic.validate_at(input.apply_tick)?;
        draft.last_order = Some(order);
        let after = draft.semantic.conversation.state.turn_state;
        let disposition = if transaction.changed_regions.is_empty() {
            ChatPolicyDispositionV1::Duplicate
        } else {
            ChatPolicyDispositionV1::Applied
        };
        let outcome = ChatPolicyOutcomeV1 {
            disposition,
            order,
            conversation_before: before,
            conversation_after: after,
            changed_regions: transaction.changed_regions,
        };
        *self = draft;
        Ok(outcome)
    }

    fn is_exact_completed_session_end(&self, input: &OrderedChatEventV1) -> bool {
        let ChatEventV1::SessionEnded { reason } = &input.event else {
            return false;
        };
        self.semantic.session.state.mode == SessionModeV1::Disconnected
            && self.last_session_end.as_ref()
                == Some(&CompletedSessionEndV1 {
                    session_id: input.session_id.clone(),
                    turn_id: input.turn_id.clone(),
                    reason: *reason,
                })
    }

    fn matching_tool_end_precedes_expiry(&self, input: &OrderedChatEventV1) -> bool {
        let ChatEventV1::ToolWaitEnded(payload) = &input.event else {
            return false;
        };
        !self.event_is_blocked_by_safety(&input.event)
            && self.semantic.conversation.state.turn_state == ChatTurnState::ToolWait
            && self.semantic.conversation.header.deadline_tick == Some(input.apply_tick)
            && self
                .active_tool_wait
                .as_ref()
                .is_some_and(|active| active.operation_id == payload.operation_id)
    }

    fn is_exact_active_retry(&self, input: &OrderedChatEventV1) -> bool {
        let event = &input.event;
        match event {
            ChatEventV1::SessionStarted { locale } => {
                self.last_session_locale.as_ref() == Some(locale)
                    && self.semantic.session.state.mode != SessionModeV1::Disconnected
                    && self.semantic.session.state.session_id.as_ref() == Some(&input.session_id)
                    && self.semantic.session.state.turn_id == input.turn_id
            }
            ChatEventV1::SessionEnded { .. } => false,
            ChatEventV1::UserTurnStarted => {
                self.last_conversation_retry == Some(ConversationRetryV1::UserTurnStarted)
                    && self.semantic.conversation.state.turn_state == ChatTurnState::Listening
                    && self.semantic.session.state.turn_id == input.turn_id
            }
            ChatEventV1::UserTurnCommitted => {
                self.last_conversation_retry == Some(ConversationRetryV1::UserTurnCommitted)
                    && self.semantic.conversation.state.turn_state == ChatTurnState::Thinking
            }
            ChatEventV1::UserTurnCancelled => {
                self.last_conversation_retry == Some(ConversationRetryV1::UserTurnCancelled)
                    && self.semantic.conversation.state.turn_state == ChatTurnState::Interrupted
            }
            ChatEventV1::AssistantThinkingStarted => {
                self.last_conversation_retry == Some(ConversationRetryV1::AssistantThinkingStarted)
                    && self.semantic.conversation.state.turn_state == ChatTurnState::Thinking
            }
            ChatEventV1::AssistantThinkingEnded => {
                self.last_conversation_retry == Some(ConversationRetryV1::AssistantThinkingEnded)
                    && self.semantic.conversation.state.turn_state == ChatTurnState::Idle
            }
            ChatEventV1::AssistantResponsePlanned { speech_expected } => {
                self.last_conversation_retry
                    == Some(ConversationRetryV1::AssistantResponsePlanned {
                        speech_expected: *speech_expected,
                    })
                    && self.semantic.conversation.state.turn_state
                        == ChatTurnState::PreparingResponse
            }
            ChatEventV1::ClarificationRequested(payload) => {
                self.last_clarification.as_ref() == Some(payload)
                    && self.semantic.conversation.state.turn_state == ChatTurnState::Clarifying
            }
            ChatEventV1::ToolWaitStarted(payload) => {
                self.active_tool_wait.as_ref()
                    == Some(&ActiveToolWaitV1 {
                        operation_id: payload.operation_id.clone(),
                        kind: payload.kind,
                        expected_duration_ms: payload.expected_duration_ms,
                    })
                    && self.semantic.conversation.state.turn_state == ChatTurnState::ToolWait
            }
            ChatEventV1::ToolWaitEnded(payload) => {
                self.completed_tool_waits.iter().any(|completed| {
                    completed.operation_id == payload.operation_id
                        && completed.outcome == payload.outcome
                })
            }
            ChatEventV1::AssistantError(payload) => {
                self.last_error.as_ref() == Some(payload)
                    && self.semantic.conversation.state.turn_state == ChatTurnState::Error
            }
            ChatEventV1::CelebrationRequested(payload) => {
                self.last_celebration.as_ref() == Some(payload)
                    && self.semantic.conversation.state.turn_state == ChatTurnState::Celebrating
            }
            ChatEventV1::SpeechPrepared(plan) => {
                self.active_speech_plan.as_ref()
                    == Some(&SpeechPlanIdentityV1 {
                        utterance_id: plan.utterance_id.clone(),
                        content_free_hash64: content_free_speech_hash(plan),
                    })
                    && self.semantic.speech.state.mode == SpeechModeV1::Prepared
            }
            ChatEventV1::SpeechStarted { utterance_id } => {
                self.last_speech_retry
                    == Some(SpeechRetryV1::Started {
                        utterance_id: utterance_id.clone(),
                    })
                    && self.semantic.speech.state.mode == SpeechModeV1::Active
            }
            ChatEventV1::SpeechProgress {
                utterance_id,
                elapsed_ms,
            } => {
                self.last_speech_retry
                    == Some(SpeechRetryV1::Progress {
                        utterance_id: utterance_id.clone(),
                        elapsed_ms: *elapsed_ms,
                    })
                    && self.semantic.speech.state.mode == SpeechModeV1::Active
            }
            ChatEventV1::SpeechPaused { utterance_id } => {
                self.last_speech_retry
                    == Some(SpeechRetryV1::Paused {
                        utterance_id: utterance_id.clone(),
                    })
                    && self.semantic.speech.state.mode == SpeechModeV1::Paused
            }
            ChatEventV1::SpeechResumed { utterance_id } => {
                self.last_speech_retry
                    == Some(SpeechRetryV1::Resumed {
                        utterance_id: utterance_id.clone(),
                    })
                    && self.semantic.speech.state.mode == SpeechModeV1::Active
            }
            ChatEventV1::SpeechCancelled {
                utterance_id,
                reason,
            } => {
                self.last_speech_retry
                    == Some(SpeechRetryV1::Cancelled {
                        utterance_id: utterance_id.clone(),
                        reason: *reason,
                    })
                    && self.semantic.speech.state.mode == SpeechModeV1::Cancelling
            }
            ChatEventV1::SpeechCompleted { utterance_id } => {
                self.last_speech_retry
                    == Some(SpeechRetryV1::Completed {
                        utterance_id: utterance_id.clone(),
                    })
                    && self.semantic.speech.state.mode == SpeechModeV1::Completed
            }
            ChatEventV1::SpeechFailed { utterance_id, code } => {
                self.last_speech_retry
                    == Some(SpeechRetryV1::Failed {
                        utterance_id: utterance_id.clone(),
                        code: *code,
                    })
                    && self.semantic.speech.state.mode == SpeechModeV1::Failed
            }
            ChatEventV1::EmotionHint(payload) => {
                self.last_emotion.as_ref() == Some(payload)
                    && self.semantic.face.state.emotion == payload.emotion
                    && self.semantic.face.state.intensity == payload.intensity
                    && self.semantic.face.state.confidence == payload.confidence
            }
            ChatEventV1::GestureHint(payload) => {
                self.last_gesture.as_ref() == Some(payload)
                    && self.semantic.gesture.state.gesture == Some(payload.gesture)
                    && self.semantic.gesture.state.phase == GesturePhaseV1::Commit
            }
            ChatEventV1::AttentionTarget(payload) => {
                self.last_attention.as_ref() == Some(payload)
                    && self.active_attention_hold.is_some()
                    && self.semantic.session.state.attention_target == payload.target
                    && self.semantic.face.state.gaze == payload.target
            }
            ChatEventV1::SafetyClamp(payload) => {
                let active = self.active_safety_scope_mask & safety_scope_bit(payload.scope) != 0;
                active == payload.active
            }
            ChatEventV1::ConnectionDegraded => {
                self.semantic.session.state.mode == SessionModeV1::Degraded
            }
            ChatEventV1::ConnectionRecovered => {
                self.semantic.session.state.mode == SessionModeV1::Ready
                    && self.semantic.conversation.state.turn_state == ChatTurnState::Idle
            }
        }
    }

    fn record_retry_identity(&mut self, event: &ChatEventV1) {
        match event {
            ChatEventV1::SessionStarted { locale } => {
                self.last_session_locale = Some(locale.clone());
                self.last_conversation_retry = None;
            }
            ChatEventV1::SessionEnded { .. } => {}
            ChatEventV1::UserTurnStarted => {
                self.last_conversation_retry = Some(ConversationRetryV1::UserTurnStarted);
            }
            ChatEventV1::UserTurnCommitted => {
                self.last_conversation_retry = Some(ConversationRetryV1::UserTurnCommitted);
            }
            ChatEventV1::UserTurnCancelled => {
                self.last_conversation_retry = Some(ConversationRetryV1::UserTurnCancelled);
            }
            ChatEventV1::AssistantThinkingStarted => {
                self.last_conversation_retry = Some(ConversationRetryV1::AssistantThinkingStarted);
            }
            ChatEventV1::AssistantThinkingEnded => {
                self.last_conversation_retry = Some(ConversationRetryV1::AssistantThinkingEnded);
            }
            ChatEventV1::AssistantResponsePlanned { speech_expected } => {
                self.last_conversation_retry =
                    Some(ConversationRetryV1::AssistantResponsePlanned {
                        speech_expected: *speech_expected,
                    });
            }
            ChatEventV1::ClarificationRequested(_)
            | ChatEventV1::ToolWaitStarted(_)
            | ChatEventV1::ToolWaitEnded(_)
            | ChatEventV1::AssistantError(_)
            | ChatEventV1::CelebrationRequested(_) => {
                self.last_conversation_retry = None;
            }
            ChatEventV1::SpeechPrepared(_) => {
                self.last_conversation_retry = None;
                self.last_speech_retry = None;
            }
            ChatEventV1::SpeechStarted { utterance_id } => {
                self.last_conversation_retry = None;
                self.last_speech_retry = Some(SpeechRetryV1::Started {
                    utterance_id: utterance_id.clone(),
                });
            }
            ChatEventV1::SpeechProgress {
                utterance_id,
                elapsed_ms,
            } => {
                self.last_conversation_retry = None;
                self.last_speech_retry = Some(SpeechRetryV1::Progress {
                    utterance_id: utterance_id.clone(),
                    elapsed_ms: *elapsed_ms,
                });
            }
            ChatEventV1::SpeechPaused { utterance_id } => {
                self.last_conversation_retry = None;
                self.last_speech_retry = Some(SpeechRetryV1::Paused {
                    utterance_id: utterance_id.clone(),
                });
            }
            ChatEventV1::SpeechResumed { utterance_id } => {
                self.last_conversation_retry = None;
                self.last_speech_retry = Some(SpeechRetryV1::Resumed {
                    utterance_id: utterance_id.clone(),
                });
            }
            ChatEventV1::SpeechCancelled {
                utterance_id,
                reason,
            } => {
                self.last_conversation_retry = None;
                self.last_speech_retry = Some(SpeechRetryV1::Cancelled {
                    utterance_id: utterance_id.clone(),
                    reason: *reason,
                });
            }
            ChatEventV1::SpeechCompleted { utterance_id } => {
                self.last_conversation_retry = None;
                self.last_speech_retry = Some(SpeechRetryV1::Completed {
                    utterance_id: utterance_id.clone(),
                });
            }
            ChatEventV1::SpeechFailed { utterance_id, code } => {
                self.last_conversation_retry = None;
                self.last_speech_retry = Some(SpeechRetryV1::Failed {
                    utterance_id: utterance_id.clone(),
                    code: *code,
                });
            }
            ChatEventV1::EmotionHint(payload) => self.last_emotion = Some(payload.clone()),
            ChatEventV1::GestureHint(payload) => self.last_gesture = Some(payload.clone()),
            ChatEventV1::AttentionTarget(payload) => {
                self.last_attention = Some(payload.clone());
            }
            ChatEventV1::SafetyClamp(payload) => {
                if payload.scope == SafetyScope::All {
                    self.last_conversation_retry = None;
                }
            }
            ChatEventV1::ConnectionDegraded | ChatEventV1::ConnectionRecovered => {
                self.last_conversation_retry = None;
            }
        }
    }

    fn validate_correlation(&self, input: &OrderedChatEventV1) -> Result<(), ChatPolicyError> {
        if matches!(input.event, ChatEventV1::SafetyClamp(_)) {
            return Ok(());
        }

        if matches!(input.event, ChatEventV1::SessionStarted { .. }) {
            if let Some(active_session) = self.semantic.session.state.session_id.as_ref() {
                if active_session != &input.session_id {
                    return Err(ChatPolicyError::SessionMismatch);
                }
                if self.semantic.session.state.turn_id != input.turn_id {
                    return Err(ChatPolicyError::TurnMismatch);
                }
            }
            return Ok(());
        }

        let Some(active_session) = self.semantic.session.state.session_id.as_ref() else {
            return Err(ChatPolicyError::SessionMismatch);
        };
        if active_session != &input.session_id {
            return Err(ChatPolicyError::SessionMismatch);
        }
        if matches!(input.event, ChatEventV1::UserTurnStarted) {
            let Some(next_turn) = input.turn_id.as_ref() else {
                return Err(ChatPolicyError::TurnMismatch);
            };
            if self.semantic.session.state.turn_id.as_ref() == Some(next_turn) {
                return Ok(());
            }
            if self.semantic.session.state.turn_id != input.previous_turn_id {
                return Err(ChatPolicyError::TurnMismatch);
            }
            return Ok(());
        }
        let Some(active_turn) = self.semantic.session.state.turn_id.as_ref() else {
            return Err(ChatPolicyError::TurnMismatch);
        };
        if input.turn_id.as_ref() != Some(active_turn) {
            return Err(ChatPolicyError::TurnMismatch);
        }
        Ok(())
    }

    fn expire_at(
        &mut self,
        tick: SemanticTick,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let defaults = AvatarSemanticStateV1::new(self.semantic.character_id.clone());
        let expired_regions: Vec<_> = RegionKind::ALL
            .into_iter()
            .filter(|region| {
                self.semantic
                    .region_header(*region)
                    .deadline_tick
                    .is_some_and(|deadline| tick >= deadline)
            })
            .collect();

        for region in expired_regions {
            let mutation = match region {
                RegionKind::Session => {
                    self.active_tool_wait = None;
                    self.active_speech_plan = None;
                    self.active_attention_hold = None;
                    self.last_session_locale = None;
                    self.last_attention = None;
                    RegionMutationV1::Session(defaults.session.state.clone())
                }
                RegionKind::Conversation => {
                    if self.semantic.conversation.state.turn_state == ChatTurnState::ToolWait {
                        self.active_tool_wait = None;
                    }
                    self.last_conversation_retry = None;
                    RegionMutationV1::Conversation(defaults.conversation.state.clone())
                }
                RegionKind::Speech => {
                    self.active_speech_plan = None;
                    self.last_speech_retry = None;
                    RegionMutationV1::Speech(defaults.speech.state.clone())
                }
                RegionKind::Mouth => RegionMutationV1::Mouth(defaults.mouth.state.clone()),
                RegionKind::Face => {
                    self.last_emotion = None;
                    let mut face = defaults.face.state.clone();
                    face.gaze = self.semantic.face.state.gaze;
                    RegionMutationV1::Face(face)
                }
                RegionKind::Gesture => {
                    self.last_gesture = None;
                    RegionMutationV1::Gesture(defaults.gesture.state.clone())
                }
                RegionKind::Pose => RegionMutationV1::Pose(defaults.pose.state.clone()),
                RegionKind::Staff => RegionMutationV1::Staff(defaults.staff.state.clone()),
                RegionKind::Wings => RegionMutationV1::Wings(defaults.wings.state.clone()),
                RegionKind::Effects => RegionMutationV1::Effects(defaults.effects.state.clone()),
                RegionKind::Mobility => {
                    let current = &self.semantic.mobility.state;
                    let mut mobility = defaults.mobility.state.clone();
                    mobility.position_millicells = current.position_millicells;
                    mobility.facing = current.facing;
                    mobility.locomotion_phase_tick = current.locomotion_phase_tick;
                    mobility.wing_phase_tick = current.wing_phase_tick;
                    RegionMutationV1::Mobility(mobility)
                }
                RegionKind::Control => RegionMutationV1::Control(defaults.control.state.clone()),
            };
            self.apply_region(transaction, region, mutation, None)?;
        }

        let mut effects = self.semantic.effects.state.clone();
        effects
            .instances
            .retain(|effect| tick < effect.deadline_tick);
        if effects != self.semantic.effects.state {
            self.apply_region(
                transaction,
                RegionKind::Effects,
                RegionMutationV1::Effects(effects),
                None,
            )?;
        }

        if self
            .semantic
            .control
            .state
            .active_mobility_lease
            .is_some_and(|lease| tick >= lease.deadline_tick)
        {
            let mut control = self.semantic.control.state.clone();
            control.active_mobility_lease = None;
            self.apply_region(
                transaction,
                RegionKind::Control,
                RegionMutationV1::Control(control),
                None,
            )?;
        }

        if self
            .active_attention_hold
            .as_ref()
            .is_some_and(|hold| tick >= hold.deadline_tick)
        {
            let return_to_user = self
                .active_attention_hold
                .take()
                .is_some_and(|hold| hold.return_to_user);
            self.last_attention = None;
            if return_to_user {
                let mut session = self.semantic.session.state.clone();
                session.attention_target = AttentionTarget::User;
                self.set_session(transaction, session)?;
                let mut face = self.semantic.face.state.clone();
                face.gaze = AttentionTarget::User;
                self.set_face(transaction, face, None)?;
            }
        }
        Ok(())
    }

    fn event_is_blocked_by_safety(&self, event: &ChatEventV1) -> bool {
        if self.safety_scope_is_active(SafetyScope::Speech)
            && matches!(
                event,
                ChatEventV1::SpeechPrepared(_)
                    | ChatEventV1::SpeechStarted { .. }
                    | ChatEventV1::SpeechProgress { .. }
                    | ChatEventV1::SpeechPaused { .. }
                    | ChatEventV1::SpeechResumed { .. }
                    | ChatEventV1::SpeechCancelled { .. }
                    | ChatEventV1::SpeechCompleted { .. }
                    | ChatEventV1::SpeechFailed { .. }
            )
        {
            return true;
        }
        if self.safety_scope_is_active(SafetyScope::Gesture)
            && matches!(event, ChatEventV1::GestureHint(_))
        {
            return true;
        }
        self.safety_scope_is_active(SafetyScope::All)
            && matches!(
                event,
                ChatEventV1::UserTurnCommitted
                    | ChatEventV1::UserTurnCancelled
                    | ChatEventV1::AssistantThinkingStarted
                    | ChatEventV1::AssistantThinkingEnded
                    | ChatEventV1::AssistantResponsePlanned { .. }
                    | ChatEventV1::ClarificationRequested(_)
                    | ChatEventV1::ToolWaitStarted(_)
                    | ChatEventV1::ToolWaitEnded(_)
                    | ChatEventV1::AssistantError(_)
                    | ChatEventV1::CelebrationRequested(_)
            )
    }

    fn dispatch(
        &mut self,
        input: &OrderedChatEventV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        if self.event_is_blocked_by_safety(&input.event) {
            return Ok(());
        }
        match &input.event {
            ChatEventV1::SessionStarted { .. } => self.session_started(input, transaction),
            ChatEventV1::SessionEnded { .. } => self.session_ended(input, transaction),
            ChatEventV1::UserTurnStarted => self.user_turn_started(input, transaction),
            ChatEventV1::UserTurnCommitted | ChatEventV1::AssistantThinkingStarted => self
                .set_conversation(
                    transaction,
                    ChatTurnState::Thinking,
                    Some(THINKING_HOLD_TICKS),
                    false,
                ),
            ChatEventV1::UserTurnCancelled => self.interrupt_conversation(transaction),
            ChatEventV1::AssistantThinkingEnded => {
                self.set_conversation(transaction, ChatTurnState::Idle, None, false)
            }
            ChatEventV1::AssistantResponsePlanned { .. } => {
                self.set_conversation(
                    transaction,
                    ChatTurnState::PreparingResponse,
                    Some(RESPONSE_HOLD_TICKS),
                    false,
                )?;
                self.set_mouth_rest(transaction)
            }
            ChatEventV1::ClarificationRequested(payload) => {
                self.clarification_requested(payload, transaction)
            }
            ChatEventV1::ToolWaitStarted(payload) => self.tool_wait_started(payload, transaction),
            ChatEventV1::ToolWaitEnded(payload) => self.tool_wait_ended(payload, transaction),
            ChatEventV1::AssistantError(payload) => self.assistant_error(payload, transaction),
            ChatEventV1::CelebrationRequested(payload) => {
                self.celebration_requested(payload, transaction)
            }
            ChatEventV1::SpeechPrepared(plan) => self.speech_prepared(plan, transaction),
            ChatEventV1::SpeechStarted { utterance_id } => {
                self.speech_started(utterance_id, transaction)
            }
            ChatEventV1::SpeechProgress {
                utterance_id,
                elapsed_ms,
            } => self.speech_progress(utterance_id, *elapsed_ms, transaction),
            ChatEventV1::SpeechPaused { utterance_id } => {
                self.speech_paused(utterance_id, transaction)
            }
            ChatEventV1::SpeechResumed { utterance_id } => {
                self.speech_resumed(utterance_id, transaction)
            }
            ChatEventV1::SpeechCancelled { utterance_id, .. } => {
                self.speech_cancelled(utterance_id, transaction)
            }
            ChatEventV1::SpeechCompleted { utterance_id } => {
                self.speech_completed(utterance_id, transaction)
            }
            ChatEventV1::SpeechFailed { utterance_id, .. } => {
                self.speech_failed(utterance_id, transaction)
            }
            ChatEventV1::EmotionHint(payload) => self.emotion_hint(payload, transaction),
            ChatEventV1::GestureHint(payload) => self.gesture_hint(payload, transaction),
            ChatEventV1::AttentionTarget(payload) => self.attention_target(payload, transaction),
            ChatEventV1::SafetyClamp(payload) => self.safety_clamp(payload, transaction),
            ChatEventV1::ConnectionDegraded => self.connection_degraded(transaction),
            ChatEventV1::ConnectionRecovered => self.connection_recovered(transaction),
        }
    }

    fn session_started(
        &mut self,
        input: &OrderedChatEventV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let starts_new_session =
            self.semantic.session.state.session_id.as_ref() != Some(&input.session_id);
        if starts_new_session {
            self.last_session_end = None;
        }
        let state = SessionStateV1 {
            mode: SessionModeV1::Ready,
            session_id: Some(input.session_id.clone()),
            turn_id: input.turn_id.clone(),
            attention_target: AttentionTarget::User,
        };
        self.set_session(transaction, state)?;
        self.set_conversation(transaction, ChatTurnState::Idle, None, false)
    }

    fn session_ended(
        &mut self,
        input: &OrderedChatEventV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let ChatEventV1::SessionEnded { reason } = &input.event else {
            unreachable!("session_ended is dispatched only for SessionEnded");
        };
        let completed_end = CompletedSessionEndV1 {
            session_id: input.session_id.clone(),
            turn_id: input.turn_id.clone(),
            reason: *reason,
        };
        let defaults = AvatarSemanticStateV1::new(self.semantic.character_id.clone());
        let mobility = self.semantic.mobility.state.clone();
        let mut control = self.semantic.control.state.clone();
        control.active_mobility_lease = None;
        control.safety_clamp = false;

        self.apply_region(
            transaction,
            RegionKind::Session,
            RegionMutationV1::Session(defaults.session.state),
            None,
        )?;
        self.apply_region(
            transaction,
            RegionKind::Conversation,
            RegionMutationV1::Conversation(defaults.conversation.state),
            None,
        )?;
        self.apply_region(
            transaction,
            RegionKind::Speech,
            RegionMutationV1::Speech(defaults.speech.state),
            None,
        )?;
        self.apply_region(
            transaction,
            RegionKind::Mouth,
            RegionMutationV1::Mouth(defaults.mouth.state),
            None,
        )?;
        self.apply_region(
            transaction,
            RegionKind::Face,
            RegionMutationV1::Face(defaults.face.state),
            None,
        )?;
        self.apply_region(
            transaction,
            RegionKind::Gesture,
            RegionMutationV1::Gesture(defaults.gesture.state),
            None,
        )?;
        self.apply_region(
            transaction,
            RegionKind::Pose,
            RegionMutationV1::Pose(defaults.pose.state),
            None,
        )?;
        self.apply_region(
            transaction,
            RegionKind::Staff,
            RegionMutationV1::Staff(defaults.staff.state),
            None,
        )?;
        self.apply_region(
            transaction,
            RegionKind::Wings,
            RegionMutationV1::Wings(defaults.wings.state),
            None,
        )?;
        self.apply_region(
            transaction,
            RegionKind::Effects,
            RegionMutationV1::Effects(defaults.effects.state),
            None,
        )?;
        self.apply_region(
            transaction,
            RegionKind::Mobility,
            RegionMutationV1::Mobility(mobility),
            None,
        )?;
        self.apply_region(
            transaction,
            RegionKind::Control,
            RegionMutationV1::Control(control),
            None,
        )?;
        self.active_tool_wait = None;
        self.active_speech_plan = None;
        self.active_attention_hold = None;
        self.active_safety_scope_mask = 0;
        self.last_session_locale = None;
        self.last_conversation_retry = None;
        self.last_speech_retry = None;
        self.last_emotion = None;
        self.last_gesture = None;
        self.last_attention = None;
        self.last_clarification = None;
        self.last_error = None;
        self.last_celebration = None;
        self.last_session_end = Some(completed_end);
        Ok(())
    }

    fn user_turn_started(
        &mut self,
        input: &OrderedChatEventV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let Some(next_turn) = input.turn_id.as_ref() else {
            return Err(ChatPolicyError::TurnMismatch);
        };
        if self.semantic.session.state.turn_id.as_ref() != Some(next_turn) {
            self.active_tool_wait = None;
        }
        let mut session = self.semantic.session.state.clone();
        session.mode = SessionModeV1::Ready;
        session.session_id = Some(input.session_id.clone());
        session.turn_id = input.turn_id.clone();
        session.attention_target = AttentionTarget::User;
        self.set_session(transaction, session)?;
        self.set_conversation(transaction, ChatTurnState::Listening, None, false)?;
        self.cancel_speech(transaction)?;
        self.set_mouth_rest(transaction)?;
        self.set_gesture_recovery(transaction)
    }

    fn interrupt_conversation(
        &mut self,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        self.set_conversation(
            transaction,
            ChatTurnState::Interrupted,
            Some(INTERRUPTED_HOLD_TICKS),
            false,
        )?;
        self.cancel_speech(transaction)?;
        self.set_mouth_rest(transaction)?;
        self.set_gesture_recovery(transaction)
    }

    fn clarification_requested(
        &mut self,
        payload: &ClarificationRequestV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let force = self.semantic.conversation.state.turn_state == ChatTurnState::Clarifying;
        self.set_conversation(
            transaction,
            ChatTurnState::Clarifying,
            Some(CLARIFICATION_HOLD_TICKS),
            force,
        )?;
        self.cancel_speech(transaction)?;
        self.set_mouth_rest(transaction)?;
        self.set_gesture_recovery(transaction)?;
        self.last_clarification = Some(payload.clone());
        Ok(())
    }

    fn tool_wait_started(
        &mut self,
        payload: &ToolWaitStartedV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let requested = ActiveToolWaitV1 {
            operation_id: payload.operation_id.clone(),
            kind: payload.kind,
            expected_duration_ms: payload.expected_duration_ms,
        };
        let hold = payload
            .expected_duration_ms
            .map(milliseconds_to_ticks)
            .transpose()?
            .unwrap_or(THINKING_HOLD_TICKS)
            .clamp(1, MAX_POLICY_HOLD_TICKS);
        if let Some(active) = self.active_tool_wait.as_ref() {
            if active == &requested {
                self.set_conversation(transaction, ChatTurnState::ToolWait, Some(hold), true)?;
                return self.set_gesture(
                    transaction,
                    GestureStateV1 {
                        gesture: Some(GestureKind::Think),
                        phase: GesturePhaseV1::Hold,
                        marker: GestureMarkerV1::Hold,
                        interrupt_policy: GestureInterruptPolicyV1::AtSafeMarker,
                        restoration_policy: GestureRestorationPolicyV1::SettleToIdle,
                    },
                    Some(hold),
                    true,
                );
            }
            if active.operation_id == requested.operation_id {
                return Err(ChatPolicyError::OperationConflict(requested.operation_id));
            }
            return Err(ChatPolicyError::OperationMismatch {
                active: Some(active.operation_id.clone()),
                received: requested.operation_id,
            });
        }
        if self
            .completed_tool_waits
            .iter()
            .any(|completed| completed.operation_id == requested.operation_id)
        {
            return Err(ChatPolicyError::OperationAlreadyCompleted(
                requested.operation_id,
            ));
        }
        self.set_conversation(transaction, ChatTurnState::ToolWait, Some(hold), false)?;
        self.set_gesture(
            transaction,
            GestureStateV1 {
                gesture: Some(GestureKind::Think),
                phase: GesturePhaseV1::Hold,
                marker: GestureMarkerV1::Hold,
                interrupt_policy: GestureInterruptPolicyV1::AtSafeMarker,
                restoration_policy: GestureRestorationPolicyV1::SettleToIdle,
            },
            Some(hold),
            false,
        )?;
        self.active_tool_wait = Some(requested);
        Ok(())
    }

    fn tool_wait_ended(
        &mut self,
        payload: &ToolWaitEndedV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        if let Some(completed) = self
            .completed_tool_waits
            .iter()
            .find(|completed| completed.operation_id == payload.operation_id)
        {
            if completed.outcome == payload.outcome {
                return Ok(());
            }
            return Err(ChatPolicyError::OperationConflict(
                payload.operation_id.clone(),
            ));
        }
        let Some(active) = self.active_tool_wait.as_ref() else {
            return Err(ChatPolicyError::OperationMismatch {
                active: None,
                received: payload.operation_id.clone(),
            });
        };
        if active.operation_id != payload.operation_id {
            return Err(ChatPolicyError::OperationMismatch {
                active: Some(active.operation_id.clone()),
                received: payload.operation_id.clone(),
            });
        }
        self.set_conversation(transaction, ChatTurnState::Idle, None, false)?;
        self.set_gesture_recovery(transaction)?;
        self.active_tool_wait = None;
        if self.completed_tool_waits.len() == MAX_COMPLETED_OPERATIONS {
            self.completed_tool_waits.remove(0);
        }
        self.completed_tool_waits.push(CompletedToolWaitV1 {
            operation_id: payload.operation_id.clone(),
            outcome: payload.outcome,
        });
        Ok(())
    }

    fn assistant_error(
        &mut self,
        payload: &AssistantErrorV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let force = self.semantic.conversation.state.turn_state == ChatTurnState::Error;
        self.set_conversation(
            transaction,
            ChatTurnState::Error,
            Some(ERROR_HOLD_TICKS),
            force,
        )?;
        self.cancel_speech(transaction)?;
        self.set_mouth_rest(transaction)?;
        self.set_gesture(
            transaction,
            GestureStateV1 {
                gesture: Some(GestureKind::Acknowledge),
                phase: GesturePhaseV1::Commit,
                marker: GestureMarkerV1::Commit,
                interrupt_policy: GestureInterruptPolicyV1::AtSafeMarker,
                restoration_policy: GestureRestorationPolicyV1::SettleToIdle,
            },
            Some(ERROR_HOLD_TICKS),
            force,
        )?;
        self.last_error = Some(payload.clone());
        Ok(())
    }

    fn celebration_requested(
        &mut self,
        payload: &CelebrationRequestV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let hold = CELEBRATION_BASE_TICKS + u64::from(payload.intensity).min(90);
        let force = self.semantic.conversation.state.turn_state == ChatTurnState::Celebrating;
        self.set_conversation(transaction, ChatTurnState::Celebrating, Some(hold), force)?;
        self.set_gesture(
            transaction,
            GestureStateV1 {
                gesture: Some(GestureKind::Celebrate),
                phase: GesturePhaseV1::Commit,
                marker: GestureMarkerV1::Commit,
                interrupt_policy: GestureInterruptPolicyV1::AtSafeMarker,
                restoration_policy: GestureRestorationPolicyV1::SettleToIdle,
            },
            Some(hold),
            force,
        )?;
        self.last_celebration = Some(payload.clone());
        Ok(())
    }

    fn speech_prepared(
        &mut self,
        plan: &SpeechPlanV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let identity = SpeechPlanIdentityV1 {
            utterance_id: plan.utterance_id.clone(),
            content_free_hash64: content_free_speech_hash(plan),
        };
        if let Some(active) = self.active_speech_plan.as_ref() {
            if active == &identity && self.semantic.speech.state.mode == SpeechModeV1::Prepared {
                return self.set_conversation(
                    transaction,
                    ChatTurnState::PreparingResponse,
                    Some(RESPONSE_HOLD_TICKS),
                    true,
                );
            }
            if active.utterance_id == identity.utterance_id && active != &identity {
                return Err(ChatPolicyError::SpeechPlanConflict(identity.utterance_id));
            }
        }
        self.set_conversation(
            transaction,
            ChatTurnState::PreparingResponse,
            Some(RESPONSE_HOLD_TICKS),
            false,
        )?;
        self.set_speech(
            transaction,
            SpeechStateV1 {
                mode: SpeechModeV1::Prepared,
                utterance_id: Some(plan.utterance_id.clone()),
                plan_hash64: Some(identity.content_free_hash64),
                start_tick: None,
                cursor_tick: 0,
                suppressed: false,
            },
            None,
        )?;
        self.set_mouth_rest(transaction)?;
        self.active_speech_plan = Some(identity);
        Ok(())
    }

    fn speech_started(
        &mut self,
        utterance_id: &UtteranceId,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        self.require_utterance(utterance_id)?;
        if self.semantic.speech.state.mode == SpeechModeV1::Active
            && self.semantic.speech.state.utterance_id.as_ref() == Some(utterance_id)
        {
            return Ok(());
        }
        if self.semantic.speech.state.mode != SpeechModeV1::Prepared
            && self.semantic.speech.state.mode != SpeechModeV1::Paused
        {
            return Err(ChatPolicyError::UtteranceMismatch {
                active: self.semantic.speech.state.utterance_id.clone(),
                received: utterance_id.clone(),
            });
        }
        self.set_conversation(transaction, ChatTurnState::Speaking, None, false)?;
        let mut speech = self.semantic.speech.state.clone();
        speech.mode = SpeechModeV1::Active;
        speech.start_tick.get_or_insert(transaction.tick);
        speech.suppressed = false;
        self.set_speech(transaction, speech, None)
    }

    fn speech_progress(
        &mut self,
        utterance_id: &UtteranceId,
        elapsed_ms: u32,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        self.require_utterance(utterance_id)?;
        if self.semantic.speech.state.mode != SpeechModeV1::Active {
            return Err(ChatPolicyError::UtteranceMismatch {
                active: self.semantic.speech.state.utterance_id.clone(),
                received: utterance_id.clone(),
            });
        }
        let cursor_tick = u32::try_from(milliseconds_to_ticks(elapsed_ms)?)
            .map_err(|_| ChatPolicyError::TickOverflow)?;
        if cursor_tick < self.semantic.speech.state.cursor_tick {
            return Err(ChatPolicyError::StaleSpeechProgress {
                current_tick: self.semantic.speech.state.cursor_tick,
                received_tick: cursor_tick,
            });
        }
        let mut speech = self.semantic.speech.state.clone();
        speech.cursor_tick = cursor_tick;
        self.set_speech(transaction, speech, None)?;
        self.set_conversation(transaction, ChatTurnState::Speaking, None, false)
    }

    fn speech_paused(
        &mut self,
        utterance_id: &UtteranceId,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        self.require_utterance(utterance_id)?;
        if self.semantic.speech.state.mode == SpeechModeV1::Paused {
            return Ok(());
        }
        if self.semantic.speech.state.mode != SpeechModeV1::Active {
            return Err(ChatPolicyError::UtteranceMismatch {
                active: self.semantic.speech.state.utterance_id.clone(),
                received: utterance_id.clone(),
            });
        }
        let mut speech = self.semantic.speech.state.clone();
        speech.mode = SpeechModeV1::Paused;
        self.set_speech(transaction, speech, None)?;
        self.set_mouth_rest(transaction)?;
        self.set_conversation(transaction, ChatTurnState::Speaking, None, false)
    }

    fn speech_resumed(
        &mut self,
        utterance_id: &UtteranceId,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        self.require_utterance(utterance_id)?;
        if self.semantic.speech.state.mode == SpeechModeV1::Active {
            return Ok(());
        }
        if self.semantic.speech.state.mode != SpeechModeV1::Paused {
            return Err(ChatPolicyError::UtteranceMismatch {
                active: self.semantic.speech.state.utterance_id.clone(),
                received: utterance_id.clone(),
            });
        }
        let mut speech = self.semantic.speech.state.clone();
        speech.mode = SpeechModeV1::Active;
        speech.suppressed = false;
        self.set_speech(transaction, speech, None)?;
        self.set_conversation(transaction, ChatTurnState::Speaking, None, false)
    }

    fn speech_cancelled(
        &mut self,
        utterance_id: &UtteranceId,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        self.require_utterance(utterance_id)?;
        if self.semantic.speech.state.mode == SpeechModeV1::Cancelling {
            return Ok(());
        }
        self.cancel_speech(transaction)?;
        self.set_mouth_rest(transaction)?;
        self.set_conversation(
            transaction,
            ChatTurnState::Interrupted,
            Some(INTERRUPTED_HOLD_TICKS),
            false,
        )
    }

    fn speech_completed(
        &mut self,
        utterance_id: &UtteranceId,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        self.require_utterance(utterance_id)?;
        if self.semantic.speech.state.mode == SpeechModeV1::Completed {
            return Ok(());
        }
        let mut speech = self.semantic.speech.state.clone();
        speech.mode = SpeechModeV1::Completed;
        speech.suppressed = false;
        self.set_speech(transaction, speech, None)?;
        self.set_mouth_rest(transaction)?;
        self.set_conversation(transaction, ChatTurnState::Idle, None, false)
    }

    fn speech_failed(
        &mut self,
        utterance_id: &UtteranceId,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        self.require_utterance(utterance_id)?;
        if self.semantic.speech.state.mode == SpeechModeV1::Failed {
            return Ok(());
        }
        let mut speech = self.semantic.speech.state.clone();
        speech.mode = SpeechModeV1::Failed;
        speech.suppressed = true;
        self.set_speech(transaction, speech, None)?;
        self.set_mouth_rest(transaction)?;
        self.set_conversation(
            transaction,
            ChatTurnState::Error,
            Some(ERROR_HOLD_TICKS),
            false,
        )
    }

    fn emotion_hint(
        &mut self,
        payload: &EmotionHintV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let hold = payload.duration_ms.map(bounded_visual_ticks).transpose()?;
        let face = FaceStateV1 {
            emotion: payload.emotion,
            transient_expression: None,
            intensity: payload.intensity,
            confidence: payload.confidence,
            blink: self.semantic.face.state.blink,
            gaze: self.semantic.face.state.gaze,
        };
        self.set_face(transaction, face, hold)
    }

    fn gesture_hint(
        &mut self,
        payload: &GestureHintV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let hold = CELEBRATION_BASE_TICKS + u64::from(payload.intensity).min(90);
        self.set_gesture(
            transaction,
            GestureStateV1 {
                gesture: Some(payload.gesture),
                phase: GesturePhaseV1::Commit,
                marker: GestureMarkerV1::Commit,
                interrupt_policy: GestureInterruptPolicyV1::AtSafeMarker,
                restoration_policy: GestureRestorationPolicyV1::RestorePrevious,
            },
            Some(hold),
            false,
        )
    }

    fn attention_target(
        &mut self,
        payload: &AttentionTargetV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let hold_ticks = bounded_visual_ticks(payload.hold_ms)?;
        let deadline_tick = checked_deadline(transaction.tick, hold_ticks)?;
        let mut session = self.semantic.session.state.clone();
        session.attention_target = payload.target;
        self.set_session(transaction, session)?;
        let mut face = self.semantic.face.state.clone();
        face.gaze = payload.target;
        self.set_face(transaction, face, Some(hold_ticks))?;
        self.active_attention_hold = Some(ActiveAttentionHoldV1 {
            deadline_tick,
            return_to_user: payload.return_to_user,
        });
        Ok(())
    }

    fn safety_clamp(
        &mut self,
        payload: &SafetyClampV1,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let scope_bit = safety_scope_bit(payload.scope);
        if payload.active {
            self.active_safety_scope_mask |= scope_bit;
        } else {
            self.active_safety_scope_mask &= !scope_bit;
        }
        let mut control = self.semantic.control.state.clone();
        control.safety_clamp = self.active_safety_scope_mask != 0;
        self.set_control(transaction, control)?;
        if !payload.active {
            return Ok(());
        }
        match payload.scope {
            SafetyScope::All => {
                self.set_conversation(
                    transaction,
                    ChatTurnState::Idle,
                    Some(SAFETY_HOLD_TICKS),
                    false,
                )?;
                self.cancel_speech(transaction)?;
                self.set_mouth_rest(transaction)?;
                self.set_gesture_recovery(transaction)?;
                self.set_effects(
                    transaction,
                    EffectsStateV1 {
                        instances: Vec::new(),
                    },
                )?;
                self.neutralize_mobility(transaction)
            }
            SafetyScope::Speech => {
                self.cancel_speech(transaction)?;
                self.set_mouth_rest(transaction)
            }
            SafetyScope::Gesture => self.set_gesture_recovery(transaction),
            SafetyScope::Mobility => self.neutralize_mobility(transaction),
            SafetyScope::Effects => self.set_effects(
                transaction,
                EffectsStateV1 {
                    instances: Vec::new(),
                },
            ),
        }
    }

    fn safety_scope_is_active(&self, scope: SafetyScope) -> bool {
        let all_active = self.active_safety_scope_mask & safety_scope_bit(SafetyScope::All) != 0;
        all_active || self.active_safety_scope_mask & safety_scope_bit(scope) != 0
    }

    fn enforce_active_safety_scopes(
        &mut self,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let mut control = self.semantic.control.state.clone();
        control.safety_clamp = self.active_safety_scope_mask != 0;
        self.set_control(transaction, control)?;
        if self.safety_scope_is_active(SafetyScope::All) {
            self.set_conversation(
                transaction,
                ChatTurnState::Idle,
                Some(SAFETY_HOLD_TICKS),
                true,
            )?;
            self.cancel_speech(transaction)?;
            self.set_mouth_rest(transaction)?;
            self.set_gesture_recovery(transaction)?;
            self.set_effects(
                transaction,
                EffectsStateV1 {
                    instances: Vec::new(),
                },
            )?;
            return self.neutralize_mobility(transaction);
        }
        if self.safety_scope_is_active(SafetyScope::Speech) {
            self.cancel_speech(transaction)?;
            self.set_mouth_rest(transaction)?;
        }
        if self.safety_scope_is_active(SafetyScope::Gesture) {
            self.set_gesture_recovery(transaction)?;
        }
        if self.safety_scope_is_active(SafetyScope::Effects) {
            self.set_effects(
                transaction,
                EffectsStateV1 {
                    instances: Vec::new(),
                },
            )?;
        }
        if self.safety_scope_is_active(SafetyScope::Mobility) {
            self.neutralize_mobility(transaction)?;
        }
        Ok(())
    }

    fn connection_degraded(
        &mut self,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let mut session = self.semantic.session.state.clone();
        session.mode = SessionModeV1::Degraded;
        self.set_session(transaction, session)?;
        self.set_face(
            transaction,
            FaceStateV1 {
                emotion: crate::chat_event::Emotion::Neutral,
                transient_expression: Some(FaceExpressionV1::Neutral),
                intensity: 10,
                confidence: 100,
                blink: BlinkStateV1::Open,
                gaze: AttentionTarget::User,
            },
            None,
        )?;
        self.set_gesture_recovery(transaction)
    }

    fn connection_recovered(
        &mut self,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let mut session = self.semantic.session.state.clone();
        session.mode = SessionModeV1::Ready;
        self.set_session(transaction, session)?;
        self.set_conversation(transaction, ChatTurnState::Idle, None, false)
    }

    fn require_utterance(&self, received: &UtteranceId) -> Result<(), ChatPolicyError> {
        let plan_matches = self
            .active_speech_plan
            .as_ref()
            .is_some_and(|plan| &plan.utterance_id == received);
        if self.semantic.speech.state.utterance_id.as_ref() != Some(received) || !plan_matches {
            return Err(ChatPolicyError::UtteranceMismatch {
                active: self.semantic.speech.state.utterance_id.clone(),
                received: received.clone(),
            });
        }
        Ok(())
    }

    fn cancel_speech(
        &mut self,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let mut speech = self.semantic.speech.state.clone();
        speech.mode = if speech.utterance_id.is_some() {
            SpeechModeV1::Cancelling
        } else {
            SpeechModeV1::Idle
        };
        speech.suppressed = true;
        self.set_speech(transaction, speech, Some(SAFETY_HOLD_TICKS))
    }

    fn set_mouth_rest(
        &mut self,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        if !self.safety_scope_is_active(SafetyScope::Speech)
            && self.semantic.mouth.state.viseme == Viseme::Rest
            && self.semantic.mouth.state.rendered_pose == RenderedMouthPose::Closed
            && self.semantic.mouth.state.cue_index.is_none()
        {
            return Ok(());
        }
        let mouth = MouthStateV1 {
            viseme: Viseme::Rest,
            rendered_pose: RenderedMouthPose::Closed,
            previous_pose: self.semantic.mouth.state.rendered_pose,
            blend_percent: 100,
            cue_index: None,
            confidence: 100,
        };
        self.apply_region(
            transaction,
            RegionKind::Mouth,
            RegionMutationV1::Mouth(mouth),
            Some(SAFETY_HOLD_TICKS),
        )
    }

    fn set_gesture_recovery(
        &mut self,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        self.set_gesture(
            transaction,
            GestureStateV1 {
                gesture: None,
                phase: GesturePhaseV1::Recovery,
                marker: GestureMarkerV1::Recover,
                interrupt_policy: GestureInterruptPolicyV1::Immediate,
                restoration_policy: GestureRestorationPolicyV1::SettleToIdle,
            },
            Some(SAFETY_HOLD_TICKS),
            false,
        )
    }

    fn neutralize_mobility(
        &mut self,
        transaction: &mut PolicyTransactionV1,
    ) -> Result<(), ChatPolicyError> {
        let current = &self.semantic.mobility.state;
        let state = MobilityStateV1 {
            mode: MobilityModeV1::GroundedIdle,
            position_millicells: current.position_millicells,
            velocity_millicells_per_tick: Point2iV1::default(),
            facing: current.facing,
            altitude_millicells: 0,
            contacts: vec![ContactPointV1::LeftFoot, ContactPointV1::RightFoot],
            locomotion_phase_tick: current.locomotion_phase_tick,
            wing_phase_tick: current.wing_phase_tick,
        };
        self.set_mobility(transaction, state, Some(SAFETY_HOLD_TICKS))
    }

    fn set_session(
        &mut self,
        transaction: &mut PolicyTransactionV1,
        state: SessionStateV1,
    ) -> Result<(), ChatPolicyError> {
        if self.semantic.session.state == state {
            return Ok(());
        }
        self.apply_region(
            transaction,
            RegionKind::Session,
            RegionMutationV1::Session(state),
            None,
        )
    }

    fn set_conversation(
        &mut self,
        transaction: &mut PolicyTransactionV1,
        turn_state: ChatTurnState,
        hold_ticks: Option<u64>,
        force: bool,
    ) -> Result<(), ChatPolicyError> {
        let safety_active = self.safety_scope_is_active(SafetyScope::All);
        let state = ConversationStateV1 {
            turn_state: if safety_active {
                ChatTurnState::Idle
            } else {
                turn_state
            },
        };
        let hold_ticks = if safety_active {
            Some(SAFETY_HOLD_TICKS)
        } else {
            hold_ticks
        };
        if !force && hold_ticks.is_none() && self.semantic.conversation.state == state {
            return Ok(());
        }
        self.apply_region(
            transaction,
            RegionKind::Conversation,
            RegionMutationV1::Conversation(state),
            hold_ticks,
        )
    }

    fn set_speech(
        &mut self,
        transaction: &mut PolicyTransactionV1,
        state: SpeechStateV1,
        hold_ticks: Option<u64>,
    ) -> Result<(), ChatPolicyError> {
        let safety_active = self.safety_scope_is_active(SafetyScope::Speech);
        let state = if safety_active {
            let mut neutral = self.semantic.speech.state.clone();
            neutral.mode = if neutral.utterance_id.is_some() {
                SpeechModeV1::Cancelling
            } else {
                SpeechModeV1::Idle
            };
            neutral.suppressed = true;
            neutral
        } else {
            state
        };
        let hold_ticks = if safety_active {
            Some(SAFETY_HOLD_TICKS)
        } else {
            hold_ticks
        };
        if hold_ticks.is_none() && self.semantic.speech.state == state {
            return Ok(());
        }
        self.apply_region(
            transaction,
            RegionKind::Speech,
            RegionMutationV1::Speech(state),
            hold_ticks,
        )
    }

    fn set_face(
        &mut self,
        transaction: &mut PolicyTransactionV1,
        state: FaceStateV1,
        hold_ticks: Option<u64>,
    ) -> Result<(), ChatPolicyError> {
        if hold_ticks.is_none() && self.semantic.face.state == state {
            return Ok(());
        }
        self.apply_region(
            transaction,
            RegionKind::Face,
            RegionMutationV1::Face(state),
            hold_ticks,
        )
    }

    fn set_gesture(
        &mut self,
        transaction: &mut PolicyTransactionV1,
        state: GestureStateV1,
        hold_ticks: Option<u64>,
        force: bool,
    ) -> Result<(), ChatPolicyError> {
        let safety_active = self.safety_scope_is_active(SafetyScope::Gesture);
        let state = if safety_active {
            GestureStateV1 {
                gesture: None,
                phase: GesturePhaseV1::Recovery,
                marker: GestureMarkerV1::Recover,
                interrupt_policy: GestureInterruptPolicyV1::Immediate,
                restoration_policy: GestureRestorationPolicyV1::SettleToIdle,
            }
        } else {
            state
        };
        let hold_ticks = if safety_active {
            Some(SAFETY_HOLD_TICKS)
        } else {
            hold_ticks
        };
        if !force && hold_ticks.is_none() && self.semantic.gesture.state == state {
            return Ok(());
        }
        self.apply_region(
            transaction,
            RegionKind::Gesture,
            RegionMutationV1::Gesture(state),
            hold_ticks,
        )
    }

    fn set_effects(
        &mut self,
        transaction: &mut PolicyTransactionV1,
        state: EffectsStateV1,
    ) -> Result<(), ChatPolicyError> {
        let state = if self.safety_scope_is_active(SafetyScope::Effects) {
            EffectsStateV1 {
                instances: Vec::new(),
            }
        } else {
            state
        };
        if !self.safety_scope_is_active(SafetyScope::Effects)
            && self.semantic.effects.state == state
        {
            return Ok(());
        }
        self.apply_region(
            transaction,
            RegionKind::Effects,
            RegionMutationV1::Effects(state),
            Some(SAFETY_HOLD_TICKS),
        )
    }

    fn set_mobility(
        &mut self,
        transaction: &mut PolicyTransactionV1,
        state: MobilityStateV1,
        hold_ticks: Option<u64>,
    ) -> Result<(), ChatPolicyError> {
        let safety_active = self.safety_scope_is_active(SafetyScope::Mobility);
        let state = if safety_active {
            let current = &self.semantic.mobility.state;
            MobilityStateV1 {
                mode: MobilityModeV1::GroundedIdle,
                position_millicells: current.position_millicells,
                velocity_millicells_per_tick: Point2iV1::default(),
                facing: current.facing,
                altitude_millicells: 0,
                contacts: vec![ContactPointV1::LeftFoot, ContactPointV1::RightFoot],
                locomotion_phase_tick: current.locomotion_phase_tick,
                wing_phase_tick: current.wing_phase_tick,
            }
        } else {
            state
        };
        let hold_ticks = if safety_active {
            Some(SAFETY_HOLD_TICKS)
        } else {
            hold_ticks
        };
        if hold_ticks.is_none() && self.semantic.mobility.state == state {
            return Ok(());
        }
        self.apply_region(
            transaction,
            RegionKind::Mobility,
            RegionMutationV1::Mobility(state),
            hold_ticks,
        )
    }

    fn set_control(
        &mut self,
        transaction: &mut PolicyTransactionV1,
        state: ControlStateV1,
    ) -> Result<(), ChatPolicyError> {
        if self.semantic.control.state == state {
            return Ok(());
        }
        self.apply_region(
            transaction,
            RegionKind::Control,
            RegionMutationV1::Control(state),
            None,
        )
    }

    fn apply_region(
        &mut self,
        transaction: &mut PolicyTransactionV1,
        region: RegionKind,
        mutation: RegionMutationV1,
        hold_ticks: Option<u64>,
    ) -> Result<(), ChatPolicyError> {
        transaction.attempted_mutations += 1;
        let mut header = *self.semantic.region_header(region);
        let mut deadline_tick = hold_ticks
            .map(|hold| checked_deadline(transaction.tick, hold))
            .transpose()?;
        let mut expected_generation = header.generation;
        let mut requested_priority = header.priority.max(POLICY_PRIORITY);

        #[cfg(test)]
        if transaction.attempted_mutations == 2 {
            if let Some(fault) = transaction.fault {
                match fault {
                    TransactionFaultV1::StaleGeneration => {
                        expected_generation =
                            RegionGeneration(if header.generation.0 == u64::MAX {
                                u64::MAX - 1
                            } else {
                                header.generation.0 + 1
                            });
                    }
                    TransactionFaultV1::PriorityConflict => {
                        header.priority = RegionPriority(requested_priority.0.saturating_add(1));
                        *region_header_mut(&mut self.semantic, region) = header;
                        requested_priority = RegionPriority(header.priority.0.saturating_sub(1));
                    }
                    TransactionFaultV1::ExpiredDeadline => {
                        deadline_tick = Some(transaction.tick);
                    }
                    TransactionFaultV1::GenerationOverflow => {
                        header.generation = RegionGeneration(u64::MAX);
                        *region_header_mut(&mut self.semantic, region) = header;
                        expected_generation = RegionGeneration(u64::MAX);
                    }
                }
            }
        }

        self.semantic.apply_mutation(
            RegionMutationContextV1 {
                owner: header.owner,
                expected_generation,
                priority: requested_priority,
                entered_tick: transaction.tick,
                deadline_tick,
            },
            mutation,
        )?;
        if !transaction.changed_regions.contains(&region) {
            transaction.changed_regions.push(region);
        }
        Ok(())
    }

    #[cfg(test)]
    pub fn reduce_with_fault_for_test(
        &mut self,
        input: OrderedChatEventV1,
        fault: TransactionFaultV1,
    ) -> Result<ChatPolicyOutcomeV1, ChatPolicyError> {
        self.reduce_internal(input, Some(fault))
    }

    #[cfg(test)]
    pub fn semantic_mut_for_test(&mut self) -> &mut AvatarSemanticStateV1 {
        &mut self.semantic
    }

    #[cfg(test)]
    pub fn next_test_sequence(&self) -> u64 {
        self.last_order
            .map_or(1, |order| order.server_sequence.saturating_add(1))
    }

    #[cfg(test)]
    pub fn next_test_tick(&self) -> u64 {
        self.last_order
            .map_or(1, |order| order.apply_tick.0.saturating_add(1))
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[cfg_attr(not(test), allow(dead_code))]
pub(crate) enum TransactionFaultV1 {
    StaleGeneration,
    PriorityConflict,
    ExpiredDeadline,
    GenerationOverflow,
}

#[derive(Debug)]
struct PolicyTransactionV1 {
    tick: SemanticTick,
    attempted_mutations: usize,
    changed_regions: Vec<RegionKind>,
    fault: Option<TransactionFaultV1>,
}

impl PolicyTransactionV1 {
    const fn new(tick: SemanticTick, fault: Option<TransactionFaultV1>) -> Self {
        Self {
            tick,
            attempted_mutations: 0,
            changed_regions: Vec::new(),
            fault,
        }
    }
}

fn checked_deadline(tick: SemanticTick, hold_ticks: u64) -> Result<SemanticTick, ChatPolicyError> {
    if hold_ticks == 0 || hold_ticks > MAX_POLICY_HOLD_TICKS {
        return Err(ChatPolicyError::TickOverflow);
    }
    tick.0
        .checked_add(hold_ticks)
        .map(SemanticTick)
        .ok_or(ChatPolicyError::TickOverflow)
}

fn milliseconds_to_ticks(milliseconds: u32) -> Result<u64, ChatPolicyError> {
    u64::from(milliseconds)
        .checked_mul(60)
        .and_then(|scaled| scaled.checked_add(999))
        .map(|scaled| scaled / 1_000)
        .ok_or(ChatPolicyError::TickOverflow)
}

fn bounded_visual_ticks(milliseconds: u32) -> Result<u64, ChatPolicyError> {
    Ok(milliseconds_to_ticks(milliseconds)?.clamp(1, MAX_POLICY_HOLD_TICKS))
}

const fn safety_scope_bit(scope: SafetyScope) -> u8 {
    match scope {
        SafetyScope::All => 1 << 0,
        SafetyScope::Speech => 1 << 1,
        SafetyScope::Gesture => 1 << 2,
        SafetyScope::Mobility => 1 << 3,
        SafetyScope::Effects => 1 << 4,
    }
}

fn content_free_speech_hash(plan: &SpeechPlanV1) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    hash_bytes(&mut hash, plan.utterance_id.as_str().as_bytes());
    hash_u64(&mut hash, u64::from(plan.duration_ms));
    hash_u64(
        &mut hash,
        match plan.timing_source {
            TimingSource::TimedVisemes => 1,
            TimingSource::DurationOnly => 2,
        },
    );
    for cue in &plan.cues {
        hash_u64(&mut hash, u64::from(cue.start_ms));
        hash_u64(&mut hash, u64::from(cue.end_ms));
        hash_u64(&mut hash, viseme_code(cue.viseme));
        hash_u64(&mut hash, u64::from(cue.weight));
    }
    for marker in &plan.markers {
        hash_u64(&mut hash, u64::from(marker.at_ms));
        hash_u64(
            &mut hash,
            match marker.kind {
                SpeechMarkerKindV1::PhraseStart => 1,
                SpeechMarkerKindV1::Accent => 2,
                SpeechMarkerKindV1::ClauseEnd => 3,
                SpeechMarkerKindV1::TurnEnd => 4,
            },
        );
    }
    hash
}

fn hash_bytes(hash: &mut u64, bytes: &[u8]) {
    for byte in bytes {
        *hash ^= u64::from(*byte);
        *hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
    }
}

fn hash_u64(hash: &mut u64, value: u64) {
    hash_bytes(hash, &value.to_le_bytes());
}

const fn viseme_code(viseme: Viseme) -> u64 {
    match viseme {
        Viseme::Rest => 0,
        Viseme::MBP => 1,
        Viseme::FV => 2,
        Viseme::TH => 3,
        Viseme::DTLN => 4,
        Viseme::KG => 5,
        Viseme::CHSH => 6,
        Viseme::SZ => 7,
        Viseme::R => 8,
        Viseme::A => 9,
        Viseme::E => 10,
        Viseme::I => 11,
        Viseme::O => 12,
        Viseme::U => 13,
    }
}

#[cfg(test)]
fn region_header_mut(state: &mut AvatarSemanticStateV1, region: RegionKind) -> &mut RegionHeader {
    match region {
        RegionKind::Session => &mut state.session.header,
        RegionKind::Conversation => &mut state.conversation.header,
        RegionKind::Speech => &mut state.speech.header,
        RegionKind::Mouth => &mut state.mouth.header,
        RegionKind::Face => &mut state.face.header,
        RegionKind::Gesture => &mut state.gesture.header,
        RegionKind::Pose => &mut state.pose.header,
        RegionKind::Staff => &mut state.staff.header,
        RegionKind::Wings => &mut state.wings.header,
        RegionKind::Effects => &mut state.effects.header,
        RegionKind::Mobility => &mut state.mobility.header,
        RegionKind::Control => &mut state.control.header,
    }
}
