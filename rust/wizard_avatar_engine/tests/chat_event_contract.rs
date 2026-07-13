#![allow(dead_code)]

#[path = "../src/chat_event.rs"]
mod chat_event;

use chat_event::{
    ChatEventEnvelopeV1, ChatEventV1, ChatTurnState, ContractErrorCode, EventId, MotionProfile,
    OperationId, SpeechMarkerKindV1, Viseme, MAX_ID_BYTES, MAX_INGRESS_BYTES,
};
use serde::Deserialize;
use serde_json::Value;
use std::collections::BTreeSet;

const GOOD_EVENTS: &str = include_str!("fixtures/chat/good_events.json");
const INVALID_EVENTS: &str = include_str!("fixtures/chat/invalid_events.json");

#[derive(Debug, Deserialize)]
struct InvalidFixture {
    name: String,
    expected_code: String,
    active_operation_id: Option<String>,
    value: Value,
}

#[test]
fn every_event_variant_round_trips_byte_stably() {
    let fixtures: Vec<Value> = serde_json::from_str(GOOD_EVENTS).expect("valid fixture JSON");
    let expected_tags: BTreeSet<String> = [
        "assistant_error",
        "assistant_response_planned",
        "assistant_thinking_ended",
        "assistant_thinking_started",
        "attention_target",
        "celebration_requested",
        "clarification_requested",
        "connection_degraded",
        "connection_recovered",
        "emotion_hint",
        "gesture_hint",
        "safety_clamp",
        "session_ended",
        "session_started",
        "speech_cancelled",
        "speech_completed",
        "speech_failed",
        "speech_paused",
        "speech_prepared",
        "speech_progress",
        "speech_resumed",
        "speech_started",
        "tool_wait_ended",
        "tool_wait_started",
        "user_turn_cancelled",
        "user_turn_committed",
        "user_turn_started",
    ]
    .into_iter()
    .map(str::to_owned)
    .collect();
    let mut actual_tags = BTreeSet::new();

    for fixture in fixtures {
        let input = serde_json::to_vec(&fixture).expect("fixture serialization");
        let envelope = ChatEventEnvelopeV1::from_json(&input).expect("good event fixture");
        let first = envelope
            .to_canonical_json()
            .expect("canonical serialization");
        let reparsed = ChatEventEnvelopeV1::from_json(&first).expect("canonical event parses");
        let second = reparsed
            .to_canonical_json()
            .expect("canonical reserialization");
        assert_eq!(first, second);
        actual_tags.insert(
            fixture["event"]["type"]
                .as_str()
                .expect("event type is a string")
                .to_owned(),
        );
    }

    assert_eq!(actual_tags, expected_tags);
}

#[test]
fn central_events_have_closed_payloads_and_canonical_states() {
    let fixtures: Vec<Value> = serde_json::from_str(GOOD_EVENTS).expect("valid fixture JSON");
    let expected = [
        (
            "clarification_requested",
            ChatTurnState::Clarifying,
            &["reason", "urgency"][..],
        ),
        (
            "tool_wait_started",
            ChatTurnState::ToolWait,
            &["expected_duration_ms", "kind", "operation_id"][..],
        ),
        (
            "tool_wait_ended",
            ChatTurnState::Idle,
            &["operation_id", "outcome"][..],
        ),
        (
            "assistant_error",
            ChatTurnState::Error,
            &["code", "recoverable"][..],
        ),
        (
            "celebration_requested",
            ChatTurnState::Celebrating,
            &["intensity", "reason"][..],
        ),
    ];

    for (tag, state, expected_keys) in expected {
        let fixture = fixtures
            .iter()
            .find(|value| value["event"]["type"] == tag)
            .expect("central event fixture");
        let envelope = ChatEventEnvelopeV1::from_json(
            &serde_json::to_vec(fixture).expect("fixture serialization"),
        )
        .expect("central event parses");
        assert_eq!(envelope.event.conversation_state(), Some(state));

        let payload = fixture["event"]["payload"]
            .as_object()
            .expect("central event payload object");
        let mut keys: Vec<_> = payload.keys().map(String::as_str).collect();
        keys.sort_unstable();
        assert_eq!(keys, expected_keys, "payload keys for {tag}");
    }
}

#[test]
fn canonical_ten_chat_states_have_exact_wire_names() {
    let states = [
        ChatTurnState::Idle,
        ChatTurnState::Listening,
        ChatTurnState::Thinking,
        ChatTurnState::PreparingResponse,
        ChatTurnState::Speaking,
        ChatTurnState::Clarifying,
        ChatTurnState::ToolWait,
        ChatTurnState::Error,
        ChatTurnState::Celebrating,
        ChatTurnState::Interrupted,
    ];
    let expected = [
        "idle",
        "listening",
        "thinking",
        "preparing_response",
        "speaking",
        "clarifying",
        "tool_wait",
        "error",
        "celebrating",
        "interrupted",
    ];
    let actual: Vec<String> = states
        .into_iter()
        .map(|state| {
            serde_json::to_value(state)
                .unwrap()
                .as_str()
                .unwrap()
                .to_owned()
        })
        .collect();
    assert_eq!(actual, expected);
}

#[test]
fn invalid_event_fixtures_fail_with_stable_codes() {
    let fixtures: Vec<InvalidFixture> =
        serde_json::from_str(INVALID_EVENTS).expect("valid invalid-fixture JSON");

    for fixture in fixtures {
        let input = serde_json::to_vec(&fixture.value).expect("fixture serialization");
        let envelope = ChatEventEnvelopeV1::from_json(&input);
        let actual = if let Some(active_operation_id) = fixture.active_operation_id {
            let envelope = envelope.expect("correlation fixture parses structurally");
            let ChatEventV1::ToolWaitEnded(payload) = envelope.event else {
                panic!("correlation fixture must be tool_wait_ended");
            };
            let active = OperationId::new(active_operation_id).expect("valid active operation ID");
            payload
                .validate_against(Some(&active))
                .expect_err("correlation must fail")
                .code
        } else {
            envelope.expect_err(&fixture.name).code
        };
        assert_eq!(
            actual,
            error_code(&fixture.expected_code),
            "{}",
            fixture.name
        );
    }
}

#[test]
fn identifier_and_payload_bounds_are_enforced() {
    assert!(EventId::new("x".repeat(MAX_ID_BYTES)).is_ok());
    assert_eq!(
        EventId::new("x".repeat(MAX_ID_BYTES + 1))
            .expect_err("oversized ID")
            .code,
        ContractErrorCode::InvalidIdentifier
    );
    assert_eq!(
        EventId::new("has space").expect_err("whitespace ID").code,
        ContractErrorCode::InvalidIdentifier
    );
    assert_eq!(
        ChatEventEnvelopeV1::from_json(&vec![b' '; MAX_INGRESS_BYTES + 1])
            .expect_err("oversized payload")
            .code,
        ContractErrorCode::PayloadTooLarge
    );
}

#[test]
fn semantic_visemes_and_motion_profiles_have_frozen_wire_names() {
    let visemes = [
        (Viseme::Rest, "rest"),
        (Viseme::MBP, "mbp"),
        (Viseme::FV, "fv"),
        (Viseme::TH, "th"),
        (Viseme::DTLN, "dtln"),
        (Viseme::KG, "kg"),
        (Viseme::CHSH, "chsh"),
        (Viseme::SZ, "sz"),
        (Viseme::R, "r"),
        (Viseme::A, "a"),
        (Viseme::E, "e"),
        (Viseme::I, "i"),
        (Viseme::O, "o"),
        (Viseme::U, "u"),
    ];
    assert_eq!(visemes.len(), Viseme::ALL.len());
    for (viseme, wire_name) in visemes {
        assert_eq!(serde_json::to_value(viseme).unwrap(), wire_name);
    }
    assert_eq!(
        MotionProfile::ALL.map(|profile| serde_json::to_value(profile).unwrap()),
        [
            Value::String("full".into()),
            Value::String("reduced".into())
        ]
    );
}

#[test]
fn speech_markers_have_frozen_names_default_empty_and_reject_content() {
    let expected = ["phrase_start", "accent", "clause_end", "turn_end"];
    let actual = SpeechMarkerKindV1::ALL.map(|kind| {
        serde_json::to_value(kind)
            .unwrap()
            .as_str()
            .unwrap()
            .to_owned()
    });
    assert_eq!(actual, expected);

    let mut fixtures: Vec<Value> = serde_json::from_str(GOOD_EVENTS).expect("valid fixture JSON");
    let speech = fixtures
        .iter_mut()
        .find(|value| value["event"]["type"] == "speech_prepared")
        .expect("speech fixture");
    speech["event"]["payload"]
        .as_object_mut()
        .expect("speech payload")
        .remove("markers");
    let envelope = ChatEventEnvelopeV1::from_json(&serde_json::to_vec(speech).unwrap())
        .expect("markers default");
    let ChatEventV1::SpeechPrepared(plan) = envelope.event else {
        panic!("speech fixture must remain speech_prepared");
    };
    assert!(plan.markers.is_empty());

    let mut content_fixture: Vec<Value> =
        serde_json::from_str(GOOD_EVENTS).expect("valid fixture JSON");
    let speech = content_fixture
        .iter_mut()
        .find(|value| value["event"]["type"] == "speech_prepared")
        .expect("speech fixture");
    speech["event"]["payload"]["markers"][0]["text"] = Value::String("forbidden".into());
    assert_eq!(
        ChatEventEnvelopeV1::from_json(&serde_json::to_vec(speech).unwrap())
            .expect_err("marker content is forbidden")
            .code,
        ContractErrorCode::MalformedJson
    );
}

fn error_code(value: &str) -> ContractErrorCode {
    match value {
        "malformed_json" => ContractErrorCode::MalformedJson,
        "payload_too_large" => ContractErrorCode::PayloadTooLarge,
        "unsupported_schema_version" => ContractErrorCode::UnsupportedSchemaVersion,
        "invalid_identifier" => ContractErrorCode::InvalidIdentifier,
        "invalid_ttl" => ContractErrorCode::InvalidTtl,
        "invalid_range" => ContractErrorCode::InvalidRange,
        "invalid_locale" => ContractErrorCode::InvalidLocale,
        "invalid_content_hash" => ContractErrorCode::InvalidContentHash,
        "invalid_speech_plan" => ContractErrorCode::InvalidSpeechPlan,
        "too_many_viseme_cues" => ContractErrorCode::TooManyVisemeCues,
        "non_monotonic_viseme_cues" => ContractErrorCode::NonMonotonicVisemeCues,
        "cue_out_of_bounds" => ContractErrorCode::CueOutOfBounds,
        "invalid_speech_marker" => ContractErrorCode::InvalidSpeechMarker,
        "operation_mismatch" => ContractErrorCode::OperationMismatch,
        other => panic!("unknown expected event error code: {other}"),
    }
}
