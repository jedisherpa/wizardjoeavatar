#![allow(dead_code)]

mod chat_event {
    pub use wizard_avatar_engine::chat_event::*;
}

mod chat_performance {
    pub use wizard_avatar_engine::chat_performance::RenderedMouthPose;
}

mod command {
    pub use wizard_avatar_engine::command::*;
}

mod state {
    pub use wizard_avatar_engine::state::*;
}

#[path = "../src/state_regions.rs"]
mod state_regions;

#[path = "../src/chat_policy.rs"]
mod chat_policy;

use chat_event::*;
use chat_policy::*;
use command::{
    ChatCommandCorrelationV1, CommandEnvelopeV1, CommandRequestV1, SemanticCommandV1,
    COMMAND_SCHEMA_VERSION,
};
use sha2::{Digest, Sha256};
use state::Direction;
use state_regions::*;

fn session_id() -> SessionId {
    SessionId::new("session-1").unwrap()
}

fn turn_id() -> TurnId {
    TurnId::new("turn-1").unwrap()
}

fn utterance_id() -> UtteranceId {
    UtteranceId::new("utterance-1").unwrap()
}

fn operation_id() -> OperationId {
    OperationId::new("operation-1").unwrap()
}

fn safety_clamp_id() -> SafetyClampId {
    SafetyClampId::new("clamp-1").unwrap()
}

fn speech_plan() -> SpeechPlanV1 {
    speech_plan_for("utterance-1")
}

fn speech_plan_for(id: &str) -> SpeechPlanV1 {
    SpeechPlanV1 {
        utterance_id: UtteranceId::new(id).unwrap(),
        text_hash: "0".repeat(64),
        text_length: 999_999,
        duration_ms: 1_000,
        timing_source: TimingSource::DurationOnly,
        cues: Vec::new(),
        markers: vec![SpeechMarkerV1 {
            at_ms: 500,
            kind: SpeechMarkerKindV1::Accent,
        }],
    }
}

fn input(sequence: u64, tick: u64, event: ChatEventV1) -> OrderedChatEventV1 {
    OrderedChatEventV1 {
        apply_tick: SemanticTick(tick),
        server_sequence: sequence,
        source_id: SourceId::new("source-1").unwrap(),
        session_id: session_id(),
        turn_id: Some(turn_id()),
        previous_turn_id: None,
        event,
    }
}

fn input_for(
    sequence: u64,
    tick: u64,
    session: &str,
    turn: &str,
    event: ChatEventV1,
) -> OrderedChatEventV1 {
    OrderedChatEventV1 {
        apply_tick: SemanticTick(tick),
        server_sequence: sequence,
        source_id: SourceId::new("source-1").unwrap(),
        session_id: SessionId::new(session).unwrap(),
        turn_id: Some(TurnId::new(turn).unwrap()),
        previous_turn_id: None,
        event,
    }
}

fn input_from_source(
    sequence: u64,
    tick: u64,
    source: &str,
    event: ChatEventV1,
) -> OrderedChatEventV1 {
    let mut input = input(sequence, tick, event);
    input.source_id = SourceId::new(source).unwrap();
    input
}

fn safety_event(id: &str, scope: SafetyScope, active: bool) -> ChatEventV1 {
    ChatEventV1::SafetyClamp(SafetyClampV1 {
        clamp_id: SafetyClampId::new(id).unwrap(),
        scope,
        active,
    })
}

fn reduce(
    reducer: &mut ChatPolicyReducerV1,
    sequence: &mut u64,
    tick: &mut u64,
    event: ChatEventV1,
) -> ChatPolicyOutcomeV1 {
    let result = reducer
        .reduce(input(*sequence, *tick, event))
        .expect("policy event");
    *sequence += 1;
    *tick += 1;
    result
}

fn active_reducer() -> ChatPolicyReducerV1 {
    let mut reducer = ChatPolicyReducerV1::new("wizard-joe");
    reducer
        .reduce(input(1, 1, ChatEventV1::SessionStarted { locale: None }))
        .unwrap();
    reducer
}

fn prepare_for(event: &ChatEventV1) -> ChatPolicyReducerV1 {
    let mut reducer = ChatPolicyReducerV1::new("wizard-joe");
    let mut sequence = 1;
    let mut tick = 1;
    if !matches!(event, ChatEventV1::SessionStarted { .. }) {
        reduce(
            &mut reducer,
            &mut sequence,
            &mut tick,
            ChatEventV1::SessionStarted { locale: None },
        );
    }
    match event {
        ChatEventV1::ToolWaitEnded(_) => {
            reduce(
                &mut reducer,
                &mut sequence,
                &mut tick,
                ChatEventV1::ToolWaitStarted(ToolWaitStartedV1 {
                    operation_id: operation_id(),
                    kind: ToolWaitKind::Retrieval,
                    expected_duration_ms: Some(2_000),
                }),
            );
        }
        ChatEventV1::SpeechStarted { .. } => {
            reduce(
                &mut reducer,
                &mut sequence,
                &mut tick,
                ChatEventV1::SpeechPrepared(speech_plan()),
            );
        }
        ChatEventV1::SpeechProgress { .. }
        | ChatEventV1::SpeechPaused { .. }
        | ChatEventV1::SpeechCancelled { .. }
        | ChatEventV1::SpeechCompleted { .. }
        | ChatEventV1::SpeechFailed { .. } => {
            reduce(
                &mut reducer,
                &mut sequence,
                &mut tick,
                ChatEventV1::SpeechPrepared(speech_plan()),
            );
            reduce(
                &mut reducer,
                &mut sequence,
                &mut tick,
                ChatEventV1::SpeechStarted {
                    utterance_id: utterance_id(),
                },
            );
        }
        ChatEventV1::SpeechResumed { .. } => {
            reduce(
                &mut reducer,
                &mut sequence,
                &mut tick,
                ChatEventV1::SpeechPrepared(speech_plan()),
            );
            reduce(
                &mut reducer,
                &mut sequence,
                &mut tick,
                ChatEventV1::SpeechStarted {
                    utterance_id: utterance_id(),
                },
            );
            reduce(
                &mut reducer,
                &mut sequence,
                &mut tick,
                ChatEventV1::SpeechPaused {
                    utterance_id: utterance_id(),
                },
            );
        }
        _ => {}
    }
    reducer
}

fn every_event_variant() -> Vec<(&'static str, ChatEventV1)> {
    vec![
        (
            "session_started",
            ChatEventV1::SessionStarted {
                locale: Some("en-US".into()),
            },
        ),
        (
            "session_ended",
            ChatEventV1::SessionEnded {
                reason: SessionEndReason::UserEnded,
            },
        ),
        ("user_turn_started", ChatEventV1::UserTurnStarted),
        ("user_turn_committed", ChatEventV1::UserTurnCommitted),
        ("user_turn_cancelled", ChatEventV1::UserTurnCancelled),
        ("thinking_started", ChatEventV1::AssistantThinkingStarted),
        ("thinking_ended", ChatEventV1::AssistantThinkingEnded),
        (
            "response_planned",
            ChatEventV1::AssistantResponsePlanned {
                speech_expected: true,
            },
        ),
        (
            "clarification",
            ChatEventV1::ClarificationRequested(ClarificationRequestV1 {
                reason: ClarificationReason::AmbiguousRequest,
                urgency: 70,
            }),
        ),
        (
            "tool_wait_started",
            ChatEventV1::ToolWaitStarted(ToolWaitStartedV1 {
                operation_id: operation_id(),
                kind: ToolWaitKind::Retrieval,
                expected_duration_ms: Some(2_000),
            }),
        ),
        (
            "tool_wait_ended",
            ChatEventV1::ToolWaitEnded(ToolWaitEndedV1 {
                operation_id: operation_id(),
                outcome: ToolWaitOutcome::Completed,
            }),
        ),
        (
            "assistant_error",
            ChatEventV1::AssistantError(AssistantErrorV1 {
                code: AssistantErrorCode::NetworkFailure,
                recoverable: true,
            }),
        ),
        (
            "celebration",
            ChatEventV1::CelebrationRequested(CelebrationRequestV1 {
                reason: CelebrationReason::TaskCompleted,
                intensity: 80,
            }),
        ),
        (
            "speech_prepared",
            ChatEventV1::SpeechPrepared(speech_plan()),
        ),
        (
            "speech_started",
            ChatEventV1::SpeechStarted {
                utterance_id: utterance_id(),
            },
        ),
        (
            "speech_progress",
            ChatEventV1::SpeechProgress {
                utterance_id: utterance_id(),
                elapsed_ms: 500,
            },
        ),
        (
            "speech_paused",
            ChatEventV1::SpeechPaused {
                utterance_id: utterance_id(),
            },
        ),
        (
            "speech_resumed",
            ChatEventV1::SpeechResumed {
                utterance_id: utterance_id(),
            },
        ),
        (
            "speech_cancelled",
            ChatEventV1::SpeechCancelled {
                utterance_id: utterance_id(),
                reason: CancelReason::UserInterrupted,
            },
        ),
        (
            "speech_completed",
            ChatEventV1::SpeechCompleted {
                utterance_id: utterance_id(),
            },
        ),
        (
            "speech_failed",
            ChatEventV1::SpeechFailed {
                utterance_id: utterance_id(),
                code: SpeechFailureCode::PlaybackFailed,
            },
        ),
        (
            "emotion_hint",
            ChatEventV1::EmotionHint(EmotionHintV1 {
                emotion: Emotion::Joy,
                intensity: 60,
                confidence: 90,
                duration_ms: Some(1_000),
            }),
        ),
        (
            "gesture_hint",
            ChatEventV1::GestureHint(GestureHintV1 {
                gesture: GestureKind::Explain,
                intensity: 55,
            }),
        ),
        (
            "attention_target",
            ChatEventV1::AttentionTarget(AttentionTargetV1 {
                target: AttentionTarget::Content,
                hold_ms: 1_000,
                return_to_user: true,
            }),
        ),
        (
            "safety_clamp",
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::Speech,
                active: true,
            }),
        ),
        ("connection_degraded", ChatEventV1::ConnectionDegraded),
        ("connection_recovered", ChatEventV1::ConnectionRecovered),
    ]
}

#[test]
fn every_chat_event_variant_reduces_deterministically_and_repeats_remain_contract_valid() {
    let events = every_event_variant();
    assert_eq!(
        events.len(),
        27,
        "update exhaustive event fixtures when the enum changes"
    );
    for (name, event) in events {
        event.validate().unwrap();
        let mut first = prepare_for(&event);
        let mut second = prepare_for(&event);
        let first_sequence = first.next_test_sequence();
        let second_sequence = second.next_test_sequence();
        let first_tick = first.next_test_tick();
        let second_tick = second.next_test_tick();
        let first_outcome = first
            .reduce(input(first_sequence, first_tick, event.clone()))
            .unwrap();
        let second_outcome = second
            .reduce(input(second_sequence, second_tick, event.clone()))
            .unwrap();
        assert_eq!(first_outcome, second_outcome, "{name}");
        assert_eq!(
            serde_json::to_vec(&first).unwrap(),
            serde_json::to_vec(&second).unwrap(),
            "{name}"
        );
        assert_eq!(
            serde_json::from_value::<ChatPolicyReducerV1>(serde_json::to_value(&first).unwrap())
                .unwrap_or_else(|error| panic!("{name}: valid snapshot rejected: {error}")),
            first,
            "{name}: snapshot roundtrip drifted"
        );

        let before_repeat = serde_json::to_vec(first.semantic()).unwrap();
        let repeat = first.reduce(input(first_sequence + 1, first_tick + 1, event));
        if name == "session_ended" {
            assert_eq!(
                repeat.unwrap().disposition,
                ChatPolicyDispositionV1::Duplicate
            );
            assert_eq!(serde_json::to_vec(first.semantic()).unwrap(), before_repeat);
        } else {
            repeat.unwrap();
            first
                .semantic()
                .validate_at(SemanticTick(first_tick + 1))
                .unwrap();
        }
    }
}

fn enter_state(
    state: ChatTurnState,
    reducer: &mut ChatPolicyReducerV1,
    sequence: &mut u64,
    tick: &mut u64,
) {
    match state {
        ChatTurnState::Idle => {
            reduce(
                reducer,
                sequence,
                tick,
                ChatEventV1::SessionStarted { locale: None },
            );
        }
        ChatTurnState::Listening => {
            reduce(reducer, sequence, tick, ChatEventV1::UserTurnStarted);
        }
        ChatTurnState::Thinking => {
            reduce(
                reducer,
                sequence,
                tick,
                ChatEventV1::AssistantThinkingStarted,
            );
        }
        ChatTurnState::PreparingResponse => {
            reduce(
                reducer,
                sequence,
                tick,
                ChatEventV1::AssistantResponsePlanned {
                    speech_expected: true,
                },
            );
        }
        ChatTurnState::Speaking => {
            reduce(
                reducer,
                sequence,
                tick,
                ChatEventV1::SpeechPrepared(speech_plan()),
            );
            reduce(
                reducer,
                sequence,
                tick,
                ChatEventV1::SpeechStarted {
                    utterance_id: utterance_id(),
                },
            );
        }
        ChatTurnState::Clarifying => {
            reduce(
                reducer,
                sequence,
                tick,
                ChatEventV1::ClarificationRequested(ClarificationRequestV1 {
                    reason: ClarificationReason::ConfirmationRequired,
                    urgency: 50,
                }),
            );
        }
        ChatTurnState::ToolWait => {
            reduce(
                reducer,
                sequence,
                tick,
                ChatEventV1::ToolWaitStarted(ToolWaitStartedV1 {
                    operation_id: operation_id(),
                    kind: ToolWaitKind::Computation,
                    expected_duration_ms: Some(2_000),
                }),
            );
        }
        ChatTurnState::Error => {
            reduce(
                reducer,
                sequence,
                tick,
                ChatEventV1::AssistantError(AssistantErrorV1 {
                    code: AssistantErrorCode::Internal,
                    recoverable: true,
                }),
            );
        }
        ChatTurnState::Celebrating => {
            reduce(
                reducer,
                sequence,
                tick,
                ChatEventV1::CelebrationRequested(CelebrationRequestV1 {
                    reason: CelebrationReason::MilestoneReached,
                    intensity: 75,
                }),
            );
        }
        ChatTurnState::Interrupted => {
            reduce(reducer, sequence, tick, ChatEventV1::UserTurnCancelled);
        }
    }
}

#[test]
fn all_ten_canonical_states_have_explicit_enter_hold_interrupt_and_exit_paths() {
    assert_eq!(ChatTurnState::ALL.len(), 10);
    for expected in ChatTurnState::ALL {
        let mut reducer = active_reducer();
        let mut sequence = 2;
        let mut tick = 2;
        enter_state(expected, &mut reducer, &mut sequence, &mut tick);
        assert_eq!(reducer.semantic().conversation.state.turn_state, expected);

        let generation = reducer.semantic().conversation.header.generation;
        reduce(
            &mut reducer,
            &mut sequence,
            &mut tick,
            ChatEventV1::AttentionTarget(AttentionTargetV1 {
                target: AttentionTarget::User,
                hold_ms: 120,
                return_to_user: false,
            }),
        );
        assert_eq!(reducer.semantic().conversation.state.turn_state, expected);
        assert_eq!(
            reducer.semantic().conversation.header.generation,
            generation
        );

        let interrupt = if expected == ChatTurnState::Listening {
            ChatEventV1::AssistantThinkingStarted
        } else {
            ChatEventV1::UserTurnStarted
        };
        reduce(&mut reducer, &mut sequence, &mut tick, interrupt);
        assert_ne!(reducer.semantic().conversation.state.turn_state, expected);

        reduce(
            &mut reducer,
            &mut sequence,
            &mut tick,
            ChatEventV1::SessionEnded {
                reason: SessionEndReason::UserEnded,
            },
        );
        assert_eq!(
            reducer.semantic().conversation.state.turn_state,
            ChatTurnState::Idle
        );
    }
}

#[test]
fn exact_active_lifecycle_retries_preserve_canonical_regions_byte_for_byte() {
    for (name, event) in every_event_variant()
        .into_iter()
        .filter(|(name, _)| *name != "session_ended")
    {
        let mut reducer = prepare_for(&event);
        let sequence = reducer.next_test_sequence();
        let tick = reducer.next_test_tick();
        reducer
            .reduce(input(sequence, tick, event.clone()))
            .unwrap_or_else(|error| panic!("{name}: initial event failed: {error}"));
        let canonical_before = serde_json::to_vec(reducer.semantic()).unwrap();
        let clocks_before: Vec<_> = RegionKind::ALL
            .into_iter()
            .map(|region| (region, *reducer.semantic().region_header(region)))
            .collect();

        let outcome = reducer
            .reduce(input(sequence + 1, tick + 1, event))
            .unwrap_or_else(|error| panic!("{name}: exact retry failed: {error}"));

        assert_eq!(
            outcome.disposition,
            ChatPolicyDispositionV1::Duplicate,
            "{name}"
        );
        assert_eq!(
            serde_json::to_vec(reducer.semantic()).unwrap(),
            canonical_before,
            "{name}: canonical semantic state changed"
        );
        let clocks_after: Vec<_> = RegionKind::ALL
            .into_iter()
            .map(|region| (region, *reducer.semantic().region_header(region)))
            .collect();
        assert_eq!(clocks_after, clocks_before, "{name}: region clock changed");
    }
}

#[test]
fn materially_different_same_state_payloads_refresh_bounded_generations() {
    let cases = [
        (
            ChatEventV1::ClarificationRequested(ClarificationRequestV1 {
                reason: ClarificationReason::MissingInformation,
                urgency: 25,
            }),
            ChatEventV1::ClarificationRequested(ClarificationRequestV1 {
                reason: ClarificationReason::MissingInformation,
                urgency: 75,
            }),
            RegionKind::Conversation,
        ),
        (
            ChatEventV1::EmotionHint(EmotionHintV1 {
                emotion: Emotion::Joy,
                intensity: 25,
                confidence: 90,
                duration_ms: Some(1_000),
            }),
            ChatEventV1::EmotionHint(EmotionHintV1 {
                emotion: Emotion::Joy,
                intensity: 75,
                confidence: 90,
                duration_ms: Some(1_000),
            }),
            RegionKind::Face,
        ),
        (
            ChatEventV1::AssistantResponsePlanned {
                speech_expected: true,
            },
            ChatEventV1::AssistantResponsePlanned {
                speech_expected: false,
            },
            RegionKind::Conversation,
        ),
    ];

    for (first, second, region) in cases {
        let mut reducer = prepare_for(&first);
        let sequence = reducer.next_test_sequence();
        let tick = reducer.next_test_tick();
        reducer.reduce(input(sequence, tick, first)).unwrap();
        let generation = reducer.semantic().region_header(region).generation;
        let outcome = reducer
            .reduce(input(sequence + 1, tick + 1, second))
            .unwrap();
        assert_eq!(outcome.disposition, ChatPolicyDispositionV1::Applied);
        assert!(reducer.semantic().region_header(region).generation > generation);
    }
}

#[test]
fn tool_wait_is_operation_correlated_and_same_tick_end_settles_idle_before_later_event() {
    let start = ChatEventV1::ToolWaitStarted(ToolWaitStartedV1 {
        operation_id: operation_id(),
        kind: ToolWaitKind::Retrieval,
        expected_duration_ms: Some(1_000),
    });
    let mut reducer = active_reducer();
    reducer.reduce(input(2, 10, start.clone())).unwrap();
    let generation = reducer.semantic().conversation.header.generation;
    let deadline = reducer.semantic().conversation.header.deadline_tick;
    assert_eq!(
        reducer.reduce(input(3, 10, start)).unwrap().disposition,
        ChatPolicyDispositionV1::Duplicate
    );
    assert_eq!(
        reducer.semantic().conversation.header.generation,
        generation
    );
    assert_eq!(
        reducer.semantic().conversation.header.deadline_tick,
        deadline
    );

    let conflict_before = serde_json::to_vec(&reducer).unwrap();
    assert!(matches!(
        reducer.reduce(input(
            4,
            10,
            ChatEventV1::ToolWaitStarted(ToolWaitStartedV1 {
                operation_id: operation_id(),
                kind: ToolWaitKind::Computation,
                expected_duration_ms: Some(1_000),
            }),
        )),
        Err(ChatPolicyError::OperationConflict(_))
    ));
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), conflict_before);

    assert!(matches!(
        reducer.reduce(input(
            4,
            10,
            ChatEventV1::ToolWaitStarted(ToolWaitStartedV1 {
                operation_id: OperationId::new("different-operation").unwrap(),
                kind: ToolWaitKind::Retrieval,
                expected_duration_ms: Some(1_000),
            }),
        )),
        Err(ChatPolicyError::OperationMismatch { .. })
    ));
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), conflict_before);

    let mismatch_before = serde_json::to_vec(reducer.semantic()).unwrap();
    let mismatch = reducer
        .reduce(input(
            4,
            10,
            ChatEventV1::ToolWaitEnded(ToolWaitEndedV1 {
                operation_id: OperationId::new("different-operation").unwrap(),
                outcome: ToolWaitOutcome::Completed,
            }),
        ))
        .unwrap_err();
    assert!(matches!(
        mismatch,
        ChatPolicyError::OperationMismatch { .. }
    ));
    assert_eq!(
        serde_json::to_vec(reducer.semantic()).unwrap(),
        mismatch_before
    );

    let ended = reducer
        .reduce(input(
            5,
            10,
            ChatEventV1::ToolWaitEnded(ToolWaitEndedV1 {
                operation_id: operation_id(),
                outcome: ToolWaitOutcome::Completed,
            }),
        ))
        .unwrap();
    assert_eq!(ended.conversation_after, ChatTurnState::Idle);
    assert_eq!(
        reducer.semantic().conversation.state.turn_state,
        ChatTurnState::Idle
    );

    reducer
        .reduce(input(
            6,
            10,
            ChatEventV1::CelebrationRequested(CelebrationRequestV1 {
                reason: CelebrationReason::TaskCompleted,
                intensity: 60,
            }),
        ))
        .unwrap();
    assert_eq!(
        reducer.semantic().conversation.state.turn_state,
        ChatTurnState::Celebrating
    );

    let duplicate_end_before = serde_json::to_vec(reducer.semantic()).unwrap();
    assert_eq!(
        reducer
            .reduce(input(
                7,
                10,
                ChatEventV1::ToolWaitEnded(ToolWaitEndedV1 {
                    operation_id: operation_id(),
                    outcome: ToolWaitOutcome::Completed,
                }),
            ))
            .unwrap()
            .disposition,
        ChatPolicyDispositionV1::Duplicate
    );
    assert_eq!(
        serde_json::to_vec(reducer.semantic()).unwrap(),
        duplicate_end_before
    );
}

#[test]
fn matching_tool_wait_end_owns_the_exact_deadline_before_expiry() {
    let mut reducer = active_reducer();
    reducer
        .reduce(input(
            2,
            10,
            ChatEventV1::ToolWaitStarted(ToolWaitStartedV1 {
                operation_id: operation_id(),
                kind: ToolWaitKind::Retrieval,
                expected_duration_ms: Some(1_000),
            }),
        ))
        .unwrap();
    assert_eq!(
        reducer.semantic().conversation.header.deadline_tick,
        Some(SemanticTick(70))
    );

    let before_fault = serde_json::to_vec(&reducer).unwrap();
    assert!(matches!(
        reducer.reduce_with_fault_for_test(
            input(
                3,
                70,
                ChatEventV1::ToolWaitEnded(ToolWaitEndedV1 {
                    operation_id: operation_id(),
                    outcome: ToolWaitOutcome::Completed,
                }),
            ),
            TransactionFaultV1::StaleGeneration,
        ),
        Err(ChatPolicyError::StateRegion(_))
    ));
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), before_fault);

    let ended = reducer
        .reduce(input(
            3,
            70,
            ChatEventV1::ToolWaitEnded(ToolWaitEndedV1 {
                operation_id: operation_id(),
                outcome: ToolWaitOutcome::Completed,
            }),
        ))
        .unwrap();
    assert_eq!(ended.disposition, ChatPolicyDispositionV1::Applied);
    assert_eq!(ended.conversation_after, ChatTurnState::Idle);
    assert_eq!(reducer.semantic().conversation.header.deadline_tick, None);
    reducer.semantic().validate_at(SemanticTick(70)).unwrap();

    let later = reducer
        .reduce(input(
            4,
            70,
            ChatEventV1::CelebrationRequested(CelebrationRequestV1 {
                reason: CelebrationReason::TaskCompleted,
                intensity: 60,
            }),
        ))
        .unwrap();
    assert_eq!(later.conversation_before, ChatTurnState::Idle);
    assert_eq!(later.conversation_after, ChatTurnState::Celebrating);
}

#[test]
fn compatible_conversation_and_speech_cancellation_preserve_user_mobility_byte_for_byte() {
    let mut reducer = active_reducer();
    reducer.semantic_mut_for_test().mobility.state = MobilityStateV1 {
        mode: MobilityModeV1::GroundWalk,
        position_millicells: Point2iV1 { x: 5_000, y: 2_000 },
        velocity_millicells_per_tick: Point2iV1 { x: 25, y: 0 },
        facing: Direction::East,
        altitude_millicells: 0,
        contacts: vec![ContactPointV1::LeftFoot],
        locomotion_phase_tick: 9,
        wing_phase_tick: 0,
    };
    let mobility = serde_json::to_vec(&reducer.semantic().mobility).unwrap();
    for (sequence, event) in [
        (2, ChatEventV1::UserTurnStarted),
        (3, ChatEventV1::AssistantThinkingStarted),
        (
            4,
            ChatEventV1::AssistantResponsePlanned {
                speech_expected: true,
            },
        ),
        (5, ChatEventV1::SpeechPrepared(speech_plan())),
        (
            6,
            ChatEventV1::SpeechStarted {
                utterance_id: utterance_id(),
            },
        ),
        (
            7,
            ChatEventV1::SpeechCancelled {
                utterance_id: utterance_id(),
                reason: CancelReason::UserInterrupted,
            },
        ),
    ] {
        reducer.reduce(input(sequence, sequence, event)).unwrap();
        assert_eq!(
            serde_json::to_vec(&reducer.semantic().mobility).unwrap(),
            mobility
        );
    }
}

#[test]
fn safety_clamp_neutralizes_only_requested_channels_until_owned_release() {
    let mut reducer = prepare_for(&ChatEventV1::SpeechPaused {
        utterance_id: utterance_id(),
    });
    let mobility_before = serde_json::to_vec(&reducer.semantic().mobility).unwrap();
    reducer
        .reduce(input(
            reducer.next_test_sequence(),
            reducer.next_test_tick(),
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::Speech,
                active: true,
            }),
        ))
        .unwrap();
    assert!(reducer.semantic().control.state.safety_clamp);
    assert_eq!(
        reducer.semantic().speech.state.mode,
        SpeechModeV1::Cancelling
    );
    assert_eq!(reducer.semantic().mouth.state.viseme, Viseme::Rest);
    assert_eq!(
        serde_json::to_vec(&reducer.semantic().mobility).unwrap(),
        mobility_before
    );

    let tick = reducer.next_test_tick();
    reducer
        .reduce(input(
            reducer.next_test_sequence(),
            tick,
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::All,
                active: true,
            }),
        ))
        .unwrap();
    assert_eq!(
        reducer.semantic().conversation.state.turn_state,
        ChatTurnState::Idle
    );
    assert_eq!(
        reducer.semantic().gesture.state.phase,
        GesturePhaseV1::Recovery
    );
    assert!(reducer.semantic().effects.state.instances.is_empty());
    assert_eq!(
        reducer.semantic().mobility.state.mode,
        MobilityModeV1::GroundedIdle
    );
    assert_eq!(reducer.semantic().conversation.header.deadline_tick, None);
}

#[test]
fn exact_active_safety_retries_are_deadline_free_and_byte_stable() {
    for (scope, region) in [
        (SafetyScope::All, RegionKind::Conversation),
        (SafetyScope::Speech, RegionKind::Speech),
        (SafetyScope::Gesture, RegionKind::Gesture),
        (SafetyScope::Mobility, RegionKind::Mobility),
        (SafetyScope::Effects, RegionKind::Effects),
    ] {
        let mut reducer = prepare_for(&ChatEventV1::SpeechPaused {
            utterance_id: utterance_id(),
        });
        reducer
            .reduce(input(
                reducer.next_test_sequence(),
                reducer.next_test_tick(),
                ChatEventV1::SafetyClamp(SafetyClampV1 {
                    clamp_id: safety_clamp_id(),
                    scope,
                    active: true,
                }),
            ))
            .unwrap();
        assert_eq!(
            reducer.semantic().region_header(region).deadline_tick,
            None,
            "{scope:?}"
        );
        let before_retry = serde_json::to_vec(reducer.semantic()).unwrap();

        let outcome = reducer
            .reduce(input(
                reducer.next_test_sequence(),
                reducer.next_test_tick() + 10_000,
                ChatEventV1::SafetyClamp(SafetyClampV1 {
                    clamp_id: safety_clamp_id(),
                    scope,
                    active: true,
                }),
            ))
            .unwrap();
        assert_eq!(outcome.disposition, ChatPolicyDispositionV1::Duplicate);
        assert_eq!(
            serde_json::to_vec(reducer.semantic()).unwrap(),
            before_retry
        );
        assert!(reducer.semantic().control.state.safety_clamp, "{scope:?}");
        reducer
            .semantic()
            .validate_at(SemanticTick(reducer.next_test_tick()))
            .unwrap();
    }
}

#[test]
fn quiet_clock_expires_holds_at_equality_handles_skips_and_reasserts_safety() {
    let clarification = ChatEventV1::ClarificationRequested(ClarificationRequestV1 {
        reason: ClarificationReason::MissingInformation,
        urgency: 40,
    });
    let mut reducer = active_reducer();
    reducer.reduce(input(2, 2, clarification.clone())).unwrap();
    let deadline = reducer
        .semantic()
        .conversation
        .header
        .deadline_tick
        .unwrap();

    let before_deadline = reducer.advance_to(SemanticTick(deadline.0 - 1)).unwrap();
    assert!(!before_deadline
        .changed_regions
        .contains(&RegionKind::Conversation));
    assert_eq!(
        reducer.semantic().conversation.state.turn_state,
        ChatTurnState::Clarifying
    );
    let outcome = reducer.advance_to(deadline).unwrap();
    assert!(outcome.changed_regions.contains(&RegionKind::Conversation));
    assert_eq!(
        reducer.semantic().conversation.state.turn_state,
        ChatTurnState::Idle
    );
    reducer.semantic().validate_at(deadline).unwrap();

    let mut skipped = active_reducer();
    skipped.reduce(input(2, 2, clarification)).unwrap();
    let skipped_deadline = skipped
        .semantic()
        .conversation
        .header
        .deadline_tick
        .unwrap();
    skipped
        .advance_to(SemanticTick(skipped_deadline.0 + 17))
        .unwrap();
    assert_eq!(
        skipped.semantic().conversation.state.turn_state,
        ChatTurnState::Idle
    );
    assert!(matches!(
        skipped.advance_to(skipped_deadline),
        Err(ChatPolicyError::ClockRewind { .. })
    ));

    let mut safety = prepare_for(&ChatEventV1::SpeechPaused {
        utterance_id: utterance_id(),
    });
    safety
        .reduce(input(
            safety.next_test_sequence(),
            safety.next_test_tick(),
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::Speech,
                active: true,
            }),
        ))
        .unwrap();
    let safety_before = serde_json::to_vec(&safety).unwrap();
    let safety_tick = SemanticTick(safety.next_test_tick() + 1_000);
    safety.advance_to(safety_tick).unwrap();
    assert!(safety.semantic().speech.state.suppressed);
    assert_eq!(safety.semantic().speech.header.deadline_tick, None);
    let once = serde_json::to_vec(&safety).unwrap();
    assert!(safety
        .advance_to(safety_tick)
        .unwrap()
        .changed_regions
        .is_empty());
    assert_eq!(serde_json::to_vec(&safety).unwrap(), once);
    assert_ne!(safety_before, once);

    let mut attention = active_reducer();
    attention
        .reduce(input(
            2,
            2,
            ChatEventV1::AttentionTarget(AttentionTargetV1 {
                target: AttentionTarget::Content,
                hold_ms: 1_000,
                return_to_user: true,
            }),
        ))
        .unwrap();
    let attention_deadline = attention.semantic().face.header.deadline_tick.unwrap();
    attention.advance_to(attention_deadline).unwrap();
    assert_eq!(
        attention.semantic().session.state.attention_target,
        AttentionTarget::User
    );
    assert_eq!(attention.semantic().face.state.gaze, AttentionTarget::User);
}

#[test]
fn safety_release_is_owner_scoped_and_stale_release_is_atomic() {
    let mut reducer = active_reducer();
    reducer
        .reduce(input_from_source(
            2,
            2,
            "safety-source-a",
            safety_event("clamp-a", SafetyScope::Speech, true),
        ))
        .unwrap();
    reducer
        .reduce(input_from_source(
            3,
            3,
            "safety-source-b",
            safety_event("clamp-b", SafetyScope::Speech, true),
        ))
        .unwrap();

    reducer
        .reduce(input_from_source(
            4,
            4,
            "safety-source-a",
            safety_event("clamp-a", SafetyScope::Speech, false),
        ))
        .unwrap();
    assert!(reducer.semantic().control.state.safety_clamp);

    reducer
        .reduce(input_from_source(
            5,
            5,
            "safety-source-a",
            safety_event("clamp-c", SafetyScope::Speech, true),
        ))
        .unwrap();
    let before_delayed = serde_json::to_vec(reducer.semantic()).unwrap();
    let delayed = reducer
        .reduce(input_from_source(
            6,
            6,
            "safety-source-a",
            safety_event("clamp-a", SafetyScope::Speech, false),
        ))
        .unwrap();
    assert_eq!(delayed.disposition, ChatPolicyDispositionV1::Duplicate);
    assert_eq!(
        serde_json::to_vec(reducer.semantic()).unwrap(),
        before_delayed
    );
    assert!(reducer.semantic().control.state.safety_clamp);

    reducer
        .reduce(input_from_source(
            7,
            7,
            "safety-source-b",
            safety_event("clamp-b", SafetyScope::Speech, false),
        ))
        .unwrap();
    assert!(reducer.semantic().control.state.safety_clamp);

    let before = serde_json::to_vec(&reducer).unwrap();
    assert_eq!(
        reducer.reduce(input_from_source(
            8,
            8,
            "safety-source-b",
            safety_event("clamp-c", SafetyScope::Speech, false),
        )),
        Err(ChatPolicyError::SafetyClampOwnerMismatch)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), before);

    reducer
        .reduce(input_from_source(
            9,
            9,
            "safety-source-a",
            safety_event("clamp-c", SafetyScope::Speech, false),
        ))
        .unwrap();
    assert!(!reducer.semantic().control.state.safety_clamp);

    let retired = serde_json::to_vec(&reducer).unwrap();
    assert_eq!(
        reducer.reduce(input_from_source(
            10,
            10,
            "safety-source-a",
            safety_event("clamp-c", SafetyScope::Speech, true),
        )),
        Err(ChatPolicyError::SafetyClampIdRetired)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), retired);
}

#[test]
fn safety_history_never_evicts_or_reuses_a_retired_identity() {
    let mut reducer = active_reducer();
    for index in 0..MAX_COMPLETED_SAFETY_CLAMPS {
        let clamp_id = format!("clamp-history-{index}");
        reducer
            .reduce(input_from_source(
                reducer.next_test_sequence(),
                reducer.next_test_tick(),
                "safety-history-source",
                safety_event(&clamp_id, SafetyScope::Speech, true),
            ))
            .unwrap();
        reducer
            .reduce(input_from_source(
                reducer.next_test_sequence(),
                reducer.next_test_tick(),
                "safety-history-source",
                safety_event(&clamp_id, SafetyScope::Speech, false),
            ))
            .unwrap();
    }

    let full = serde_json::to_vec(&reducer).unwrap();
    assert_eq!(
        reducer.reduce(input_from_source(
            reducer.next_test_sequence(),
            reducer.next_test_tick(),
            "safety-history-source",
            safety_event("clamp-overflow", SafetyScope::Speech, true),
        )),
        Err(ChatPolicyError::SafetyClampHistoryCapacity)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), full);

    assert_eq!(
        reducer.reduce(input_from_source(
            reducer.next_test_sequence(),
            reducer.next_test_tick(),
            "safety-history-source",
            safety_event("clamp-history-0", SafetyScope::Speech, true),
        )),
        Err(ChatPolicyError::SafetyClampIdRetired)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), full);

    let delayed = reducer
        .reduce(input_from_source(
            reducer.next_test_sequence(),
            reducer.next_test_tick(),
            "safety-history-source",
            safety_event("clamp-history-0", SafetyScope::Speech, false),
        ))
        .unwrap();
    assert_eq!(delayed.disposition, ChatPolicyDispositionV1::Duplicate);
    assert!(!reducer.semantic().control.state.safety_clamp);
}

#[test]
fn finalized_ticks_reject_late_events_and_deadline_owner_runs_before_finalization() {
    let end = ChatEventV1::ToolWaitEnded(ToolWaitEndedV1 {
        operation_id: operation_id(),
        outcome: ToolWaitOutcome::Completed,
    });
    let mut late = prepare_for(&end);
    let deadline = late.semantic().conversation.header.deadline_tick.unwrap();
    late.advance_to(deadline).unwrap();
    let expired = serde_json::to_vec(&late).unwrap();
    assert_eq!(
        late.reduce(input(late.next_test_sequence(), deadline.0, end.clone(),)),
        Err(ChatPolicyError::TickAlreadyFinalized(deadline))
    );
    assert_eq!(serde_json::to_vec(&late).unwrap(), expired);

    let mut supported = prepare_for(&end);
    let outcome = supported
        .reduce(input(supported.next_test_sequence(), deadline.0, end))
        .unwrap();
    assert_eq!(outcome.disposition, ChatPolicyDispositionV1::Applied);
    assert_eq!(
        supported.semantic().conversation.state.turn_state,
        ChatTurnState::Idle
    );
    assert!(supported
        .advance_to(deadline)
        .unwrap()
        .changed_regions
        .is_empty());
}

#[test]
fn safety_advancement_is_partition_independent_for_every_scope_and_overlap() {
    let cases = vec![
        vec![SafetyScope::All],
        vec![SafetyScope::Speech],
        vec![SafetyScope::Gesture],
        vec![SafetyScope::Mobility],
        vec![SafetyScope::Effects],
        vec![SafetyScope::Speech, SafetyScope::Gesture],
        vec![SafetyScope::All, SafetyScope::Effects],
    ];
    for scopes in cases {
        let mut baseline = active_reducer();
        for (index, scope) in scopes.iter().copied().enumerate() {
            let sequence = index as u64 + 2;
            baseline
                .reduce(input_from_source(
                    sequence,
                    sequence,
                    &format!("safety-source-{index}"),
                    safety_event(&format!("clamp-{index}"), scope, true),
                ))
                .unwrap();
        }
        let target = SemanticTick(240);
        let mut per_tick = baseline.clone();
        for tick in per_tick.next_test_tick()..=target.0 {
            per_tick.advance_to(SemanticTick(tick)).unwrap();
        }
        let mut skipped = baseline;
        skipped.advance_to(target).unwrap();
        assert_eq!(
            serde_json::to_vec(&per_tick).unwrap(),
            serde_json::to_vec(&skipped).unwrap(),
            "{scopes:?}"
        );
        let canonical = serde_json::to_vec(&skipped).unwrap();
        assert!(skipped
            .advance_to(target)
            .unwrap()
            .changed_regions
            .is_empty());
        assert_eq!(serde_json::to_vec(&skipped).unwrap(), canonical);
    }
}

#[test]
fn reducer_snapshot_deserialization_enforces_bounds_uniqueness_and_invariants() {
    let mut reducer = active_reducer();
    reducer
        .reduce(input_from_source(
            2,
            2,
            "safety-source-a",
            safety_event("clamp-a", SafetyScope::Speech, true),
        ))
        .unwrap();
    let valid = serde_json::to_value(&reducer).unwrap();
    assert_eq!(
        serde_json::from_value::<ChatPolicyReducerV1>(valid.clone()).unwrap(),
        reducer
    );

    let active = valid["active_safety_clamps"][0].clone();
    let mut oversized = valid.clone();
    oversized["active_safety_clamps"] = serde_json::Value::Array(vec![active.clone(); 33]);
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(oversized).is_err());

    let mut duplicate = valid.clone();
    duplicate["active_safety_clamps"] =
        serde_json::Value::Array(vec![active.clone(), active.clone()]);
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(duplicate).is_err());

    let mut inconsistent = valid.clone();
    inconsistent["completed_safety_clamps"] = serde_json::Value::Array(vec![active]);
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(inconsistent).is_err());

    let mut control = valid.clone();
    control["semantic"]["control"]["state"]["safety_clamp"] = false.into();
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(control).is_err());

    let mut clock = valid;
    clock["last_tick"] = serde_json::json!(0);
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(clock).is_err());

    let mut locale = serde_json::to_value(active_reducer()).unwrap();
    locale["last_session_locale"]["locale"] = "not a locale!".into();
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(locale).is_err());

    let wait_event = ChatEventV1::ToolWaitStarted(ToolWaitStartedV1 {
        operation_id: operation_id(),
        kind: ToolWaitKind::Retrieval,
        expected_duration_ms: Some(1_000),
    });
    let mut wait = prepare_for(&wait_event);
    wait.reduce(input(
        wait.next_test_sequence(),
        wait.next_test_tick(),
        wait_event,
    ))
    .unwrap();
    let mut malformed_wait = serde_json::to_value(&wait).unwrap();
    malformed_wait["active_tool_wait"]["expected_duration_ms"] = 1_800_001.into();
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(malformed_wait).is_err());
    let mut incoherent_wait = serde_json::to_value(wait).unwrap();
    incoherent_wait["semantic"]["conversation"]["state"]["turn_state"] = "idle".into();
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(incoherent_wait).is_err());

    let attention_event = ChatEventV1::AttentionTarget(AttentionTargetV1 {
        target: AttentionTarget::Content,
        hold_ms: 2_000,
        return_to_user: true,
    });
    let mut attention = prepare_for(&attention_event);
    attention
        .reduce(input(
            attention.next_test_sequence(),
            attention.next_test_tick(),
            attention_event,
        ))
        .unwrap();
    let mut expired_attention = serde_json::to_value(&attention).unwrap();
    expired_attention["active_attention_hold"]["deadline_tick"] =
        expired_attention["last_tick"].clone();
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(expired_attention).is_err());
    let mut mismatched_attention = serde_json::to_value(attention).unwrap();
    mismatched_attention["last_attention"]["target"] = "staff".into();
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(mismatched_attention).is_err());

    let progress_event = ChatEventV1::SpeechProgress {
        utterance_id: utterance_id(),
        elapsed_ms: 250,
    };
    let mut progress = prepare_for(&progress_event);
    progress
        .reduce(input(
            progress.next_test_sequence(),
            progress.next_test_tick(),
            progress_event,
        ))
        .unwrap();
    let mut oversized_progress = serde_json::to_value(progress).unwrap();
    oversized_progress["last_speech_retry"]["progress"]["elapsed_ms"] = 1_800_001.into();
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(oversized_progress).is_err());

    let emotion_event = ChatEventV1::EmotionHint(EmotionHintV1 {
        emotion: Emotion::Joy,
        intensity: 80,
        confidence: 90,
        duration_ms: Some(1_000),
    });
    let mut emotion = prepare_for(&emotion_event);
    emotion
        .reduce(input(
            emotion.next_test_sequence(),
            emotion.next_test_tick(),
            emotion_event,
        ))
        .unwrap();
    let mut malformed_emotion = serde_json::to_value(emotion).unwrap();
    malformed_emotion["last_emotion"]["intensity"] = 101.into();
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(malformed_emotion).is_err());

    let end = ChatEventV1::ToolWaitEnded(ToolWaitEndedV1 {
        operation_id: operation_id(),
        outcome: ToolWaitOutcome::Completed,
    });
    let mut completed = prepare_for(&end);
    completed
        .reduce(input(
            completed.next_test_sequence(),
            completed.next_test_tick(),
            end,
        ))
        .unwrap();
    let mut completed_json = serde_json::to_value(completed).unwrap();
    let operation = completed_json["completed_tool_waits"][0].clone();
    completed_json["completed_tool_waits"] =
        serde_json::Value::Array(vec![operation; MAX_COMPLETED_OPERATIONS + 1]);
    assert!(serde_json::from_value::<ChatPolicyReducerV1>(completed_json).is_err());
}

#[test]
fn accepted_cross_channel_transitions_keep_snapshot_lifecycle_coherent() {
    let roundtrip = |name: &str, reducer: &ChatPolicyReducerV1| {
        assert_eq!(
            serde_json::from_value::<ChatPolicyReducerV1>(serde_json::to_value(reducer).unwrap())
                .unwrap_or_else(|error| panic!("{name}: snapshot rejected: {error}")),
            *reducer,
            "{name}: snapshot drifted"
        );
    };

    let started = ChatEventV1::SpeechStarted {
        utterance_id: utterance_id(),
    };
    let mut speech = prepare_for(&started);
    speech
        .reduce(input(
            speech.next_test_sequence(),
            speech.next_test_tick(),
            started,
        ))
        .unwrap();
    speech
        .reduce(input(
            speech.next_test_sequence(),
            speech.next_test_tick(),
            ChatEventV1::UserTurnStarted,
        ))
        .unwrap();
    assert_eq!(
        speech.semantic().speech.state.mode,
        SpeechModeV1::Cancelling
    );
    roundtrip("speech_started_then_user_turn", &speech);

    let mut attention = active_reducer();
    attention
        .reduce(input(
            attention.next_test_sequence(),
            attention.next_test_tick(),
            ChatEventV1::AttentionTarget(AttentionTargetV1 {
                target: AttentionTarget::Content,
                hold_ms: 2_000,
                return_to_user: true,
            }),
        ))
        .unwrap();
    attention
        .reduce(input(
            attention.next_test_sequence(),
            attention.next_test_tick(),
            ChatEventV1::UserTurnStarted,
        ))
        .unwrap();
    assert_eq!(
        attention.semantic().session.state.attention_target,
        AttentionTarget::User
    );
    assert_eq!(attention.semantic().face.state.gaze, AttentionTarget::User);
    roundtrip("attention_then_user_turn", &attention);

    let mut tool_wait = active_reducer();
    tool_wait
        .reduce(input(
            tool_wait.next_test_sequence(),
            tool_wait.next_test_tick(),
            ChatEventV1::ToolWaitStarted(ToolWaitStartedV1 {
                operation_id: operation_id(),
                kind: ToolWaitKind::Retrieval,
                expected_duration_ms: Some(2_000),
            }),
        ))
        .unwrap();
    tool_wait
        .reduce(input(
            tool_wait.next_test_sequence(),
            tool_wait.next_test_tick(),
            ChatEventV1::AssistantThinkingStarted,
        ))
        .unwrap();
    assert_eq!(
        tool_wait.semantic().conversation.state.turn_state,
        ChatTurnState::Thinking
    );
    roundtrip("tool_wait_then_thinking", &tool_wait);
}

fn semantic_without_control(reducer: &ChatPolicyReducerV1) -> serde_json::Value {
    let mut value = serde_json::to_value(reducer.semantic()).unwrap();
    value.as_object_mut().unwrap().remove("control");
    value
}

#[test]
fn every_safety_scope_release_preserves_neutralization_without_replaying_stale_behavior() {
    for scope in [
        SafetyScope::All,
        SafetyScope::Speech,
        SafetyScope::Gesture,
        SafetyScope::Mobility,
        SafetyScope::Effects,
    ] {
        let mut reducer = prepare_for(&ChatEventV1::SpeechPaused {
            utterance_id: utterance_id(),
        });
        reducer.semantic_mut_for_test().gesture.state = GestureStateV1 {
            gesture: Some(GestureKind::Celebrate),
            phase: GesturePhaseV1::Commit,
            marker: GestureMarkerV1::Commit,
            interrupt_policy: GestureInterruptPolicyV1::AtSafeMarker,
            restoration_policy: GestureRestorationPolicyV1::RestorePrevious,
        };
        reducer.semantic_mut_for_test().mobility.state = MobilityStateV1 {
            mode: MobilityModeV1::GroundWalk,
            position_millicells: Point2iV1 { x: 1_000, y: 500 },
            velocity_millicells_per_tick: Point2iV1 { x: 20, y: 0 },
            facing: Direction::East,
            altitude_millicells: 0,
            contacts: vec![ContactPointV1::LeftFoot],
            locomotion_phase_tick: 4,
            wing_phase_tick: 0,
        };
        reducer.semantic_mut_for_test().effects.state.instances = vec![EffectInstanceV1 {
            effect_id: StateIdV1::new("stale-effect").unwrap(),
            kind: EffectKindV1::Magic,
            generation: RegionGeneration(1),
            started_tick: SemanticTick(1),
            deadline_tick: SemanticTick(100),
        }];

        let active_tick = reducer.next_test_tick();
        reducer
            .reduce(input(
                reducer.next_test_sequence(),
                active_tick,
                ChatEventV1::SafetyClamp(SafetyClampV1 {
                    clamp_id: safety_clamp_id(),
                    scope,
                    active: true,
                }),
            ))
            .unwrap();
        let neutralized = semantic_without_control(&reducer);
        reducer
            .reduce(input(
                reducer.next_test_sequence(),
                active_tick,
                ChatEventV1::SafetyClamp(SafetyClampV1 {
                    clamp_id: safety_clamp_id(),
                    scope,
                    active: false,
                }),
            ))
            .unwrap();
        assert!(!reducer.semantic().control.state.safety_clamp, "{scope:?}");
        assert_eq!(semantic_without_control(&reducer), neutralized, "{scope:?}");
    }
}

#[test]
fn overlapping_safety_scopes_keep_the_clamp_active_until_each_scope_releases() {
    let mut reducer = prepare_for(&ChatEventV1::SpeechPaused {
        utterance_id: utterance_id(),
    });
    for (sequence, scope, active) in [
        (4, SafetyScope::Speech, true),
        (5, SafetyScope::Gesture, true),
        (6, SafetyScope::Speech, false),
    ] {
        reducer
            .reduce(input(
                sequence,
                sequence,
                ChatEventV1::SafetyClamp(SafetyClampV1 {
                    clamp_id: safety_clamp_id(),
                    scope,
                    active,
                }),
            ))
            .unwrap();
    }
    assert!(reducer.semantic().control.state.safety_clamp);
    assert_eq!(
        reducer.semantic().gesture.state.phase,
        GesturePhaseV1::Recovery
    );

    reducer
        .reduce(input(
            7,
            7,
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::Gesture,
                active: false,
            }),
        ))
        .unwrap();
    assert!(!reducer.semantic().control.state.safety_clamp);

    let semantic = serde_json::to_vec(reducer.semantic()).unwrap();
    assert_eq!(
        reducer
            .reduce(input(
                8,
                8,
                ChatEventV1::SafetyClamp(SafetyClampV1 {
                    clamp_id: safety_clamp_id(),
                    scope: SafetyScope::Gesture,
                    active: false,
                }),
            ))
            .unwrap()
            .disposition,
        ChatPolicyDispositionV1::Duplicate
    );
    assert_eq!(serde_json::to_vec(reducer.semantic()).unwrap(), semantic);
}

#[test]
fn exact_deadline_expiry_restores_regions_before_same_or_unrelated_dispatch() {
    let clarification = ChatEventV1::ClarificationRequested(ClarificationRequestV1 {
        reason: ClarificationReason::MissingInformation,
        urgency: 40,
    });
    let mut same = active_reducer();
    same.reduce(input(2, 2, clarification.clone())).unwrap();
    let deadline = same.semantic().conversation.header.deadline_tick.unwrap();
    let generation = same.semantic().conversation.header.generation;
    same.reduce(input(3, deadline.0, clarification)).unwrap();
    assert_eq!(
        same.semantic().conversation.state.turn_state,
        ChatTurnState::Clarifying
    );
    assert!(same.semantic().conversation.header.generation.0 > generation.0);
    assert!(same.semantic().conversation.header.deadline_tick.unwrap() > deadline);

    let mut unrelated = active_reducer();
    unrelated
        .reduce(input(2, 2, ChatEventV1::AssistantThinkingStarted))
        .unwrap();
    let deadline = unrelated
        .semantic()
        .conversation
        .header
        .deadline_tick
        .unwrap();
    unrelated
        .reduce(input(
            3,
            deadline.0,
            ChatEventV1::EmotionHint(EmotionHintV1 {
                emotion: Emotion::Joy,
                intensity: 60,
                confidence: 90,
                duration_ms: None,
            }),
        ))
        .unwrap();
    assert_eq!(
        unrelated.semantic().conversation.state.turn_state,
        ChatTurnState::Idle
    );
    assert_eq!(unrelated.semantic().conversation.header.deadline_tick, None);
    unrelated.semantic().validate_at(deadline).unwrap();
}

#[test]
fn expiry_sweeps_every_bounded_header_and_internal_deadline_at_equality() {
    let mut reducer = active_reducer();
    let deadline = SemanticTick(10);
    let semantic = reducer.semantic_mut_for_test();
    semantic.session.header.deadline_tick = Some(deadline);
    semantic.conversation.header.deadline_tick = Some(deadline);
    semantic.speech.header.deadline_tick = Some(deadline);
    semantic.mouth.header.deadline_tick = Some(deadline);
    semantic.face.header.deadline_tick = Some(deadline);
    semantic.gesture.header.deadline_tick = Some(deadline);
    semantic.pose.header.deadline_tick = Some(deadline);
    semantic.staff.header.deadline_tick = Some(deadline);
    semantic.wings.header.deadline_tick = Some(deadline);
    semantic.effects.header.deadline_tick = Some(deadline);
    semantic.mobility.header.deadline_tick = Some(deadline);
    semantic.control.header.deadline_tick = Some(deadline);
    semantic.effects.state.instances = vec![EffectInstanceV1 {
        effect_id: StateIdV1::new("expiring-effect").unwrap(),
        kind: EffectKindV1::Emphasis,
        generation: RegionGeneration(1),
        started_tick: SemanticTick(2),
        deadline_tick: deadline,
    }];
    semantic.control.state.active_mobility_lease = Some(RegionLeaseV1 {
        owner: semantic.mobility.header.owner,
        generation: semantic.mobility.header.generation,
        deadline_tick: deadline,
    });

    reducer.advance_to(deadline).unwrap();
    for region in RegionKind::ALL {
        assert_eq!(reducer.semantic().region_header(region).deadline_tick, None);
    }
    assert!(reducer.semantic().effects.state.instances.is_empty());
    assert!(reducer
        .semantic()
        .control
        .state
        .active_mobility_lease
        .is_none());
    reducer.semantic().validate_at(deadline).unwrap();
}

#[test]
fn attention_expiry_honors_return_to_user_without_erasing_new_face_input() {
    let mut reducer = active_reducer();
    reducer
        .reduce(input(
            2,
            2,
            ChatEventV1::AttentionTarget(AttentionTargetV1 {
                target: AttentionTarget::Content,
                hold_ms: 1_000,
                return_to_user: true,
            }),
        ))
        .unwrap();
    let deadline = reducer.semantic().face.header.deadline_tick.unwrap();
    reducer
        .reduce(input(
            3,
            deadline.0,
            ChatEventV1::EmotionHint(EmotionHintV1 {
                emotion: Emotion::Joy,
                intensity: 75,
                confidence: 95,
                duration_ms: Some(500),
            }),
        ))
        .unwrap();
    assert_eq!(
        reducer.semantic().session.state.attention_target,
        AttentionTarget::User
    );
    assert_eq!(reducer.semantic().face.state.gaze, AttentionTarget::User);
    assert_eq!(reducer.semantic().face.state.emotion, Emotion::Joy);

    let mut retained = active_reducer();
    retained
        .reduce(input(
            2,
            2,
            ChatEventV1::AttentionTarget(AttentionTargetV1 {
                target: AttentionTarget::Staff,
                hold_ms: 1_000,
                return_to_user: false,
            }),
        ))
        .unwrap();
    let deadline = retained.semantic().face.header.deadline_tick.unwrap();
    retained
        .reduce(input(
            3,
            deadline.0,
            ChatEventV1::EmotionHint(EmotionHintV1 {
                emotion: Emotion::Neutral,
                intensity: 0,
                confidence: 100,
                duration_ms: None,
            }),
        ))
        .unwrap();
    assert_eq!(retained.semantic().face.state.gaze, AttentionTarget::Staff);
}

#[test]
fn active_and_overlapping_safety_scopes_block_repopulation_until_final_release() {
    let mut reducer = active_reducer();
    reducer
        .reduce(input(
            2,
            2,
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::All,
                active: true,
            }),
        ))
        .unwrap();
    reducer
        .reduce(input(
            3,
            3,
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::Speech,
                active: true,
            }),
        ))
        .unwrap();
    reducer
        .reduce(input(4, 4, ChatEventV1::SpeechPrepared(speech_plan())))
        .unwrap();
    reducer
        .reduce(input(
            5,
            5,
            ChatEventV1::SpeechStarted {
                utterance_id: utterance_id(),
            },
        ))
        .unwrap();
    reducer
        .reduce(input(
            6,
            6,
            ChatEventV1::GestureHint(GestureHintV1 {
                gesture: GestureKind::Explain,
                intensity: 70,
            }),
        ))
        .unwrap();
    reducer
        .reduce(input(7, 7, ChatEventV1::AssistantThinkingStarted))
        .unwrap();
    assert_eq!(
        reducer.semantic().conversation.state.turn_state,
        ChatTurnState::Idle
    );
    assert_ne!(reducer.semantic().speech.state.mode, SpeechModeV1::Prepared);
    assert_ne!(reducer.semantic().speech.state.mode, SpeechModeV1::Active);
    assert_eq!(
        reducer.semantic().gesture.state.phase,
        GesturePhaseV1::Recovery
    );

    reducer
        .reduce(input(
            8,
            8,
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::All,
                active: false,
            }),
        ))
        .unwrap();
    reducer
        .reduce(input(9, 9, ChatEventV1::SpeechPrepared(speech_plan())))
        .unwrap();
    assert_ne!(reducer.semantic().speech.state.mode, SpeechModeV1::Prepared);

    reducer
        .reduce(input(
            10,
            10,
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::Speech,
                active: false,
            }),
        ))
        .unwrap();
    reducer
        .reduce(input(11, 11, ChatEventV1::SpeechPrepared(speech_plan())))
        .unwrap();
    assert_eq!(reducer.semantic().speech.state.mode, SpeechModeV1::Prepared);
    reducer
        .reduce(input(
            12,
            12,
            ChatEventV1::SpeechStarted {
                utterance_id: utterance_id(),
            },
        ))
        .unwrap();
    assert_eq!(reducer.semantic().speech.state.mode, SpeechModeV1::Active);
}

#[test]
fn non_global_events_require_live_exact_session_and_turn_correlation() {
    let mut disconnected = ChatPolicyReducerV1::new("wizard-joe");
    let before = serde_json::to_vec(&disconnected).unwrap();
    assert_eq!(
        disconnected.reduce(input(1, 1, ChatEventV1::AssistantThinkingStarted)),
        Err(ChatPolicyError::SessionMismatch)
    );
    assert_eq!(serde_json::to_vec(&disconnected).unwrap(), before);
    disconnected
        .reduce(input(
            1,
            1,
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::Gesture,
                active: true,
            }),
        ))
        .unwrap();

    let mut ended = active_reducer();
    ended
        .reduce(input(
            2,
            2,
            ChatEventV1::SessionEnded {
                reason: SessionEndReason::UserEnded,
            },
        ))
        .unwrap();
    let before = serde_json::to_vec(&ended).unwrap();
    assert_eq!(
        ended.reduce(input(3, 3, ChatEventV1::UserTurnCommitted)),
        Err(ChatPolicyError::SessionMismatch)
    );
    assert_eq!(serde_json::to_vec(&ended).unwrap(), before);

    let mut wrong_turn = active_reducer();
    let mut event = input(2, 2, ChatEventV1::ConnectionDegraded);
    event.turn_id = Some(TurnId::new("wrong-turn").unwrap());
    assert_eq!(wrong_turn.reduce(event), Err(ChatPolicyError::TurnMismatch));
}

#[test]
fn null_turn_session_adopts_new_turns_and_rejects_retired_turn_events() {
    let mut reducer = ChatPolicyReducerV1::new("wizard-joe");
    let mut started = input(1, 1, ChatEventV1::SessionStarted { locale: None });
    started.turn_id = None;
    reducer.reduce(started).unwrap();
    assert_eq!(reducer.semantic().session.state.turn_id, None);

    reducer
        .reduce(input(2, 2, ChatEventV1::UserTurnStarted))
        .unwrap();
    assert_eq!(
        reducer.semantic().session.state.turn_id.as_ref(),
        Some(&turn_id())
    );

    let second_turn = TurnId::new("turn-2").unwrap();
    let mut next = input(3, 3, ChatEventV1::UserTurnStarted);
    next.turn_id = Some(second_turn.clone());
    next.previous_turn_id = Some(turn_id());
    reducer.reduce(next).unwrap();
    assert_eq!(
        reducer.semantic().session.state.turn_id.as_ref(),
        Some(&second_turn)
    );

    let before_stale = serde_json::to_vec(&reducer).unwrap();
    assert_eq!(
        reducer.reduce(input(4, 4, ChatEventV1::UserTurnCommitted)),
        Err(ChatPolicyError::TurnMismatch)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), before_stale);
    assert_eq!(
        reducer.reduce(input(5, 5, ChatEventV1::UserTurnStarted)),
        Err(ChatPolicyError::TurnMismatch)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), before_stale);

    let mut stale_start = input(6, 6, ChatEventV1::SessionStarted { locale: None });
    stale_start.turn_id = None;
    assert_eq!(
        reducer.reduce(stale_start),
        Err(ChatPolicyError::TurnMismatch)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), before_stale);

    let mut current = input(7, 7, ChatEventV1::UserTurnCommitted);
    current.turn_id = Some(second_turn);
    reducer.reduce(current).unwrap();
    assert_eq!(
        reducer.semantic().conversation.state.turn_state,
        ChatTurnState::Thinking
    );
}

#[test]
fn command_envelope_preserves_chat_correlation_and_bridge_rejects_legacy_absence() {
    let previous_turn = TurnId::new("turn-previous").unwrap();
    let request = CommandRequestV1 {
        schema_version: COMMAND_SCHEMA_VERSION,
        command_id: CommandId::new("correlated-command").unwrap(),
        source_id: SourceId::new("chatbot-source").unwrap(),
        source_kind: SourceKind::Chatbot,
        source_sequence: 7,
        requested_apply_tick: Some(42),
        ttl_ms: 1_000,
        chat_correlation: Some(ChatCommandCorrelationV1 {
            session_id: session_id(),
            turn_id: Some(turn_id()),
            previous_turn_id: Some(previous_turn.clone()),
        }),
        command: SemanticCommandV1::ApplyChatEvent(ChatEventV1::UserTurnStarted),
    };
    let envelope = CommandEnvelopeV1::assign(request, 99, 40).unwrap();
    let canonical = serde_json::to_vec(&envelope).unwrap();
    let reparsed: CommandEnvelopeV1 = serde_json::from_slice(&canonical).unwrap();
    assert_eq!(reparsed, envelope);
    let ordered = OrderedChatEventV1::from_command_envelope(&reparsed)
        .unwrap()
        .expect("chat event command");
    assert_eq!(ordered.session_id, session_id());
    assert_eq!(ordered.turn_id, Some(turn_id()));
    assert_eq!(ordered.previous_turn_id, Some(previous_turn));
    assert_eq!(ordered.server_sequence, 99);
    assert_eq!(ordered.apply_tick, SemanticTick(42));
    assert_eq!(ordered.event, ChatEventV1::UserTurnStarted);

    let legacy = CommandRequestV1 {
        schema_version: COMMAND_SCHEMA_VERSION,
        command_id: CommandId::new("legacy-chat-command").unwrap(),
        source_id: SourceId::new("chatbot-source").unwrap(),
        source_kind: SourceKind::Chatbot,
        source_sequence: 8,
        requested_apply_tick: Some(43),
        ttl_ms: 1_000,
        chat_correlation: None,
        command: SemanticCommandV1::ApplyChatEvent(ChatEventV1::UserTurnStarted),
    };
    assert_eq!(
        CommandEnvelopeV1::assign(legacy, 100, 40).unwrap_err().code,
        command::CommandErrorCode::InvalidCommand
    );
    let mut legacy = envelope;
    legacy.chat_correlation = None;
    assert_eq!(
        OrderedChatEventV1::from_command_envelope(&legacy),
        Err(ChatPolicyError::MissingCommandCorrelation)
    );
}

#[test]
fn exact_session_end_is_idempotent_but_changed_and_stale_ends_reject() {
    let mut reducer = active_reducer();
    let end = ChatEventV1::SessionEnded {
        reason: SessionEndReason::UserEnded,
    };
    reducer.reduce(input(2, 10, end.clone())).unwrap();
    let canonical = serde_json::to_vec(reducer.semantic()).unwrap();
    let clocks: Vec<_> = RegionKind::ALL
        .into_iter()
        .map(|region| *reducer.semantic().region_header(region))
        .collect();

    assert_eq!(
        reducer
            .reduce(input(3, 11, end.clone()))
            .unwrap()
            .disposition,
        ChatPolicyDispositionV1::Duplicate
    );
    assert_eq!(serde_json::to_vec(reducer.semantic()).unwrap(), canonical);
    assert_eq!(
        RegionKind::ALL
            .into_iter()
            .map(|region| *reducer.semantic().region_header(region))
            .collect::<Vec<_>>(),
        clocks
    );

    let retained = serde_json::to_vec(&reducer).unwrap();
    assert_eq!(
        reducer.reduce(input(
            4,
            12,
            ChatEventV1::SessionEnded {
                reason: SessionEndReason::Timeout,
            },
        )),
        Err(ChatPolicyError::SessionMismatch)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), retained);

    let new_session = SessionId::new("session-2").unwrap();
    let mut restart = input(4, 13, ChatEventV1::SessionStarted { locale: None });
    restart.session_id = new_session;
    restart.turn_id = None;
    reducer.reduce(restart).unwrap();
    let active = serde_json::to_vec(&reducer).unwrap();
    assert_eq!(
        reducer.reduce(input(5, 14, end)),
        Err(ChatPolicyError::SessionMismatch)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), active);
}

#[test]
fn session_end_commits_an_indefinitely_valid_deadline_free_disconnected_state() {
    let mut reducer = active_reducer();
    reducer
        .reduce(input(
            2,
            2,
            ChatEventV1::EmotionHint(EmotionHintV1 {
                emotion: Emotion::Joy,
                intensity: 80,
                confidence: 90,
                duration_ms: Some(1_000),
            }),
        ))
        .unwrap();
    reducer
        .reduce(input(
            3,
            3,
            ChatEventV1::GestureHint(GestureHintV1 {
                gesture: GestureKind::Explain,
                intensity: 70,
            }),
        ))
        .unwrap();
    reducer
        .reduce(input(
            4,
            4,
            ChatEventV1::AttentionTarget(AttentionTargetV1 {
                target: AttentionTarget::Content,
                hold_ms: 1_000,
                return_to_user: true,
            }),
        ))
        .unwrap();
    reducer
        .reduce(input(5, 5, ChatEventV1::SpeechPrepared(speech_plan())))
        .unwrap();
    reducer
        .reduce(input(
            6,
            6,
            ChatEventV1::SpeechStarted {
                utterance_id: utterance_id(),
            },
        ))
        .unwrap();

    reducer
        .reduce(input(
            7,
            10,
            ChatEventV1::SessionEnded {
                reason: SessionEndReason::UserEnded,
            },
        ))
        .unwrap();

    assert_eq!(
        reducer.semantic().session.state.mode,
        SessionModeV1::Disconnected
    );
    assert_eq!(reducer.semantic().session.state.session_id, None);
    assert_eq!(reducer.semantic().session.state.turn_id, None);
    assert_eq!(reducer.semantic().speech.state.mode, SpeechModeV1::Idle);
    assert_eq!(reducer.semantic().gesture.state.phase, GesturePhaseV1::Idle);
    for region in RegionKind::ALL {
        assert_eq!(
            reducer.semantic().region_header(region).deadline_tick,
            None,
            "{region:?} retained a bounded hold"
        );
    }
    reducer.semantic().validate_at(SemanticTick(10)).unwrap();
    reducer.semantic().validate_at(SemanticTick(40)).unwrap();
    reducer
        .semantic()
        .validate_at(SemanticTick(10_000))
        .unwrap();

    let retained = serde_json::to_vec(&reducer).unwrap();
    assert_eq!(
        reducer.reduce(input(8, 40, ChatEventV1::UserTurnCommitted)),
        Err(ChatPolicyError::SessionMismatch)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), retained);
    reducer.semantic().validate_at(SemanticTick(40)).unwrap();
    reducer
        .semantic()
        .validate_at(SemanticTick(10_000))
        .unwrap();
}

#[test]
fn long_contract_valid_visual_holds_clamp_to_policy_maximum() {
    let mut emotion = active_reducer();
    emotion
        .reduce(input(
            2,
            20,
            ChatEventV1::EmotionHint(EmotionHintV1 {
                emotion: Emotion::Joy,
                intensity: 80,
                confidence: 100,
                duration_ms: Some(MAX_DURATION_MS),
            }),
        ))
        .unwrap();
    assert_eq!(
        emotion.semantic().face.header.deadline_tick,
        Some(SemanticTick(20 + MAX_POLICY_HOLD_TICKS))
    );

    let mut attention = active_reducer();
    attention
        .reduce(input(
            2,
            20,
            ChatEventV1::AttentionTarget(AttentionTargetV1 {
                target: AttentionTarget::Content,
                hold_ms: MAX_DURATION_MS,
                return_to_user: true,
            }),
        ))
        .unwrap();
    assert_eq!(
        attention.semantic().face.header.deadline_tick,
        Some(SemanticTick(20 + MAX_POLICY_HOLD_TICKS))
    );
}

#[test]
fn session_turn_operation_and_utterance_correlation_fail_without_mutation() {
    let mut reducer = ChatPolicyReducerV1::new("wizard-joe");
    reducer
        .reduce(input(1, 1, ChatEventV1::SessionStarted { locale: None }))
        .unwrap();
    reducer
        .reduce(input(2, 2, ChatEventV1::UserTurnStarted))
        .unwrap();

    let before_session = serde_json::to_vec(&reducer).unwrap();
    let mut stale_session = input(3, 3, ChatEventV1::UserTurnCommitted);
    stale_session.session_id = SessionId::new("stale-session").unwrap();
    assert_eq!(
        reducer.reduce(stale_session),
        Err(ChatPolicyError::SessionMismatch)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), before_session);

    let mut stale_turn = input(3, 3, ChatEventV1::UserTurnCommitted);
    stale_turn.turn_id = Some(TurnId::new("stale-turn").unwrap());
    assert_eq!(
        reducer.reduce(stale_turn),
        Err(ChatPolicyError::TurnMismatch)
    );
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), before_session);

    let mut operation = active_reducer();
    operation
        .reduce(input(
            2,
            2,
            ChatEventV1::ToolWaitStarted(ToolWaitStartedV1 {
                operation_id: operation_id(),
                kind: ToolWaitKind::Retrieval,
                expected_duration_ms: None,
            }),
        ))
        .unwrap();
    let before_operation = serde_json::to_vec(&operation).unwrap();
    assert!(matches!(
        operation.reduce(input(
            3,
            3,
            ChatEventV1::ToolWaitEnded(ToolWaitEndedV1 {
                operation_id: OperationId::new("stale-operation").unwrap(),
                outcome: ToolWaitOutcome::Completed,
            }),
        )),
        Err(ChatPolicyError::OperationMismatch { .. })
    ));
    assert_eq!(serde_json::to_vec(&operation).unwrap(), before_operation);

    let mut speech = prepare_for(&ChatEventV1::SpeechProgress {
        utterance_id: utterance_id(),
        elapsed_ms: 100,
    });
    let before_utterance = serde_json::to_vec(&speech).unwrap();
    assert!(matches!(
        speech.reduce(input(
            speech.next_test_sequence(),
            speech.next_test_tick(),
            ChatEventV1::SpeechProgress {
                utterance_id: UtteranceId::new("stale-utterance").unwrap(),
                elapsed_ms: 100,
            },
        )),
        Err(ChatPolicyError::UtteranceMismatch { .. })
    ));
    assert_eq!(serde_json::to_vec(&speech).unwrap(), before_utterance);
}

#[test]
fn prepared_response_keeps_mouth_at_rest_and_content_metadata_cannot_branch_behavior() {
    let mut reducer = active_reducer();
    let mouth_generation = reducer.semantic().mouth.header.generation;
    reducer
        .reduce(input(
            2,
            2,
            ChatEventV1::AssistantResponsePlanned {
                speech_expected: true,
            },
        ))
        .unwrap();
    assert_eq!(reducer.semantic().mouth.state.viseme, Viseme::Rest);
    assert_eq!(
        reducer.semantic().mouth.state.rendered_pose,
        chat_performance::RenderedMouthPose::Closed
    );
    assert_eq!(reducer.semantic().mouth.header.generation, mouth_generation);

    let first = speech_plan();
    reducer
        .reduce(input(3, 3, ChatEventV1::SpeechPrepared(first.clone())))
        .unwrap();
    let mut control = reducer.clone();
    let mut metadata_only = first;
    metadata_only.text_hash = "1".repeat(64);
    metadata_only.text_length = 1;
    assert_eq!(
        reducer
            .reduce(input(4, 4, ChatEventV1::SpeechPrepared(metadata_only)))
            .unwrap()
            .disposition,
        ChatPolicyDispositionV1::Duplicate
    );
    control
        .reduce(input(4, 4, ChatEventV1::SpeechPrepared(speech_plan())))
        .unwrap();
    assert_eq!(
        serde_json::to_vec(&reducer).unwrap(),
        serde_json::to_vec(&control).unwrap()
    );
}

#[test]
fn speech_lifecycle_transitions_require_a_correlated_active_utterance() {
    let events = vec![
        ChatEventV1::SpeechStarted {
            utterance_id: utterance_id(),
        },
        ChatEventV1::SpeechProgress {
            utterance_id: utterance_id(),
            elapsed_ms: 100,
        },
        ChatEventV1::SpeechPaused {
            utterance_id: utterance_id(),
        },
        ChatEventV1::SpeechResumed {
            utterance_id: utterance_id(),
        },
        ChatEventV1::SpeechCancelled {
            utterance_id: utterance_id(),
            reason: CancelReason::UserInterrupted,
        },
        ChatEventV1::SpeechCompleted {
            utterance_id: utterance_id(),
        },
        ChatEventV1::SpeechFailed {
            utterance_id: utterance_id(),
            code: SpeechFailureCode::Internal,
        },
    ];
    assert_eq!(events.len(), 7);
    for event in events {
        let mut reducer = active_reducer();
        let before = serde_json::to_vec(&reducer).unwrap();
        assert!(matches!(
            reducer.reduce(input(2, 2, event)),
            Err(ChatPolicyError::UtteranceMismatch { .. })
        ));
        assert_eq!(serde_json::to_vec(&reducer).unwrap(), before);
    }
}

#[test]
fn second_region_faults_roll_back_the_entire_multi_region_decision() {
    let cases = [
        TransactionFaultV1::StaleGeneration,
        TransactionFaultV1::PriorityConflict,
        TransactionFaultV1::ExpiredDeadline,
        TransactionFaultV1::GenerationOverflow,
    ];
    for fault in cases {
        let mut reducer = prepare_for(&ChatEventV1::SpeechPaused {
            utterance_id: utterance_id(),
        });
        let before = serde_json::to_vec(&reducer).unwrap();
        let result = reducer.reduce_with_fault_for_test(
            input(
                reducer.next_test_sequence(),
                reducer.next_test_tick(),
                ChatEventV1::UserTurnStarted,
            ),
            fault,
        );
        match fault {
            TransactionFaultV1::StaleGeneration => assert!(matches!(
                result,
                Err(ChatPolicyError::StateRegion(
                    StateRegionError::StaleGeneration { .. }
                ))
            )),
            TransactionFaultV1::PriorityConflict => assert!(matches!(
                result,
                Err(ChatPolicyError::StateRegion(
                    StateRegionError::PriorityConflict { .. }
                ))
            )),
            TransactionFaultV1::ExpiredDeadline => assert!(matches!(
                result,
                Err(ChatPolicyError::StateRegion(
                    StateRegionError::ExpiredDeadline { .. }
                ))
            )),
            TransactionFaultV1::GenerationOverflow => assert!(matches!(
                result,
                Err(ChatPolicyError::StateRegion(
                    StateRegionError::GenerationOverflow { .. }
                ))
            )),
        }
        assert_eq!(serde_json::to_vec(&reducer).unwrap(), before, "{fault:?}");
    }
}

#[test]
fn out_of_order_and_failed_events_are_atomic_and_replay_hash_is_stable() {
    fn replay_hash() -> String {
        let mut reducer = ChatPolicyReducerV1::new("wizard-joe");
        let second_utterance = UtteranceId::new("utterance-2").unwrap();
        let third_utterance = UtteranceId::new("utterance-3").unwrap();
        let trace = vec![
            ChatEventV1::SessionStarted {
                locale: Some("en-US".into()),
            },
            ChatEventV1::UserTurnStarted,
            ChatEventV1::UserTurnCommitted,
            ChatEventV1::AssistantThinkingStarted,
            ChatEventV1::AssistantThinkingEnded,
            ChatEventV1::AssistantResponsePlanned {
                speech_expected: true,
            },
            ChatEventV1::ClarificationRequested(ClarificationRequestV1 {
                reason: ClarificationReason::AmbiguousRequest,
                urgency: 70,
            }),
            ChatEventV1::ToolWaitStarted(ToolWaitStartedV1 {
                operation_id: operation_id(),
                kind: ToolWaitKind::Retrieval,
                expected_duration_ms: Some(2_000),
            }),
            ChatEventV1::ToolWaitEnded(ToolWaitEndedV1 {
                operation_id: operation_id(),
                outcome: ToolWaitOutcome::Completed,
            }),
            ChatEventV1::AssistantError(AssistantErrorV1 {
                code: AssistantErrorCode::NetworkFailure,
                recoverable: true,
            }),
            ChatEventV1::CelebrationRequested(CelebrationRequestV1 {
                reason: CelebrationReason::TaskCompleted,
                intensity: 80,
            }),
            ChatEventV1::SpeechPrepared(speech_plan()),
            ChatEventV1::SpeechStarted {
                utterance_id: utterance_id(),
            },
            ChatEventV1::SpeechProgress {
                utterance_id: utterance_id(),
                elapsed_ms: 500,
            },
            ChatEventV1::SpeechPaused {
                utterance_id: utterance_id(),
            },
            ChatEventV1::SpeechResumed {
                utterance_id: utterance_id(),
            },
            ChatEventV1::EmotionHint(EmotionHintV1 {
                emotion: Emotion::Joy,
                intensity: 60,
                confidence: 90,
                duration_ms: Some(1_000),
            }),
            ChatEventV1::GestureHint(GestureHintV1 {
                gesture: GestureKind::Explain,
                intensity: 55,
            }),
            ChatEventV1::AttentionTarget(AttentionTargetV1 {
                target: AttentionTarget::Content,
                hold_ms: 1_000,
                return_to_user: true,
            }),
            ChatEventV1::SpeechCompleted {
                utterance_id: utterance_id(),
            },
            ChatEventV1::SpeechPrepared(speech_plan_for("utterance-2")),
            ChatEventV1::SpeechStarted {
                utterance_id: second_utterance.clone(),
            },
            ChatEventV1::SpeechCancelled {
                utterance_id: second_utterance,
                reason: CancelReason::UserInterrupted,
            },
            ChatEventV1::SpeechPrepared(speech_plan_for("utterance-3")),
            ChatEventV1::SpeechStarted {
                utterance_id: third_utterance.clone(),
            },
            ChatEventV1::SpeechFailed {
                utterance_id: third_utterance,
                code: SpeechFailureCode::PlaybackFailed,
            },
            ChatEventV1::UserTurnCancelled,
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::Speech,
                active: true,
            }),
            ChatEventV1::SafetyClamp(SafetyClampV1 {
                clamp_id: safety_clamp_id(),
                scope: SafetyScope::Speech,
                active: false,
            }),
            ChatEventV1::ConnectionDegraded,
            ChatEventV1::ConnectionRecovered,
            ChatEventV1::SessionEnded {
                reason: SessionEndReason::UserEnded,
            },
        ];
        assert_eq!(
            trace.len(),
            32,
            "update the frozen replay receipt deliberately"
        );
        let mut outcomes = Vec::with_capacity(trace.len());
        for (sequence, event) in trace.into_iter().enumerate() {
            outcomes.push(
                reducer
                    .reduce(input(sequence as u64 + 1, sequence as u64 + 1, event))
                    .expect("every frozen replay event must reduce successfully"),
            );
        }
        format!(
            "{:x}",
            Sha256::digest(serde_json::to_vec(&(outcomes, reducer)).unwrap())
        )
    }

    let mut reducer = active_reducer();
    reducer
        .reduce(input(2, 2, ChatEventV1::UserTurnStarted))
        .unwrap();
    let before = serde_json::to_vec(&reducer).unwrap();
    assert!(matches!(
        reducer.reduce(input(1, 1, ChatEventV1::AssistantThinkingStarted)),
        Err(ChatPolicyError::OutOfOrder { .. })
    ));
    assert_eq!(serde_json::to_vec(&reducer).unwrap(), before);

    let first = replay_hash();
    assert_eq!(first, replay_hash());
    assert_eq!(first, EXPECTED_REPLAY_HASH, "freeze reviewed policy replay");

    let source = include_str!("../src/chat_policy.rs");
    for forbidden in [
        "SystemTime",
        "Instant",
        "thread_rng",
        "random",
        "response_text",
        "private_text",
        ".png",
        "python",
        "text_hash",
        "text_length",
    ] {
        assert!(
            !source.contains(forbidden),
            "forbidden policy token {forbidden}"
        );
    }
}

const EXPECTED_REPLAY_HASH: &str =
    "12baaa7658baf911104010f23a7553a529b1ec41473512dbad0a635490ad4b6c";
