#![allow(dead_code)]

#[path = "../src/chat_event.rs"]
mod chat_event;
#[path = "../src/command.rs"]
mod command;

use chat_event::MAX_INGRESS_BYTES;
use command::{
    AckStatus, CommandAckV1, CommandEnvelopeV1, CommandErrorCode, CommandRequestV1, RuntimeEpoch,
};
use serde::Deserialize;
use serde_json::Value;
use std::collections::BTreeSet;

const GOOD_COMMANDS: &str = include_str!("fixtures/chat/good_commands.json");
const INVALID_COMMANDS: &str = include_str!("fixtures/chat/invalid_commands.json");
const CURRENT_TICK: u64 = 100;

#[derive(Debug, Deserialize)]
struct InvalidFixture {
    name: String,
    expected_code: String,
    #[serde(default)]
    public: bool,
    value: Value,
}

#[test]
fn contract_every_command_variant_round_trips_byte_stably() {
    let fixtures: Vec<Value> = serde_json::from_str(GOOD_COMMANDS).expect("valid fixture JSON");
    let expected_tags: BTreeSet<String> = [
        "apply_chat_event",
        "cancel_speech",
        "complete_speech",
        "diagnostic_pose",
        "legacy",
        "pause_speech",
        "prepare_speech",
        "reset",
        "resume_speech",
        "set_emotion",
        "set_motion_intent",
        "start_gesture",
        "start_speech",
        "stop",
        "update_speech_progress",
    ]
    .into_iter()
    .map(str::to_owned)
    .collect();
    let mut actual_tags = BTreeSet::new();

    for fixture in fixtures {
        let input = serde_json::to_vec(&fixture).expect("fixture serialization");
        let request = CommandRequestV1::from_json(&input, CURRENT_TICK).expect("good command");
        let first = request
            .to_canonical_json()
            .expect("canonical serialization");
        let reparsed =
            CommandRequestV1::from_json(&first, CURRENT_TICK).expect("canonical command parses");
        let second = reparsed
            .to_canonical_json()
            .expect("canonical reserialization");
        assert_eq!(first, second);
        actual_tags.insert(
            fixture["command"]["type"]
                .as_str()
                .expect("command type is a string")
                .to_owned(),
        );
    }

    assert_eq!(actual_tags, expected_tags);
}

#[test]
fn contract_invalid_commands_fail_with_stable_codes() {
    let fixtures: Vec<InvalidFixture> =
        serde_json::from_str(INVALID_COMMANDS).expect("valid invalid-fixture JSON");

    for fixture in fixtures {
        let input = serde_json::to_vec(&fixture.value).expect("fixture serialization");
        let result = if fixture.public {
            CommandRequestV1::from_public_json(&input, CURRENT_TICK)
        } else {
            CommandRequestV1::from_json(&input, CURRENT_TICK)
        };
        assert_eq!(
            result.expect_err(&fixture.name).code,
            error_code(&fixture.expected_code),
            "{}",
            fixture.name
        );
    }
}

#[test]
fn contract_server_assignment_is_stable_and_client_cannot_set_it() {
    let fixtures: Vec<Value> = serde_json::from_str(GOOD_COMMANDS).expect("valid fixture JSON");
    let default_request = CommandRequestV1::from_json(
        &serde_json::to_vec(&fixtures[0]).expect("fixture serialization"),
        CURRENT_TICK,
    )
    .expect("default-tick request");
    let explicit_request = CommandRequestV1::from_json(
        &serde_json::to_vec(&fixtures[1]).expect("fixture serialization"),
        CURRENT_TICK,
    )
    .expect("explicit-tick request");

    let default = CommandEnvelopeV1::assign(default_request, 2, CURRENT_TICK).unwrap();
    let explicit = CommandEnvelopeV1::assign(explicit_request, 1, CURRENT_TICK).unwrap();
    assert_eq!(default.apply_tick, CURRENT_TICK + 1);
    assert_eq!(explicit.apply_tick, CURRENT_TICK + 1);
    assert!(explicit.ordering_key() < default.ordering_key());
    assert_eq!(default.expires_tick, 161);
    assert!(!default.is_expired_at(160));
    assert!(default.is_expired_at(161));

    let mut zero_ttl_fixture = fixtures[0].clone();
    zero_ttl_fixture["ttl_ms"] = Value::from(0);
    let zero_ttl_request = CommandRequestV1::from_json(
        &serde_json::to_vec(&zero_ttl_fixture).expect("fixture serialization"),
        CURRENT_TICK,
    )
    .expect("zero TTL request");
    let zero_ttl = CommandEnvelopeV1::assign(zero_ttl_request, 3, CURRENT_TICK).unwrap();
    assert_eq!(zero_ttl.apply_tick, 101);
    assert_eq!(zero_ttl.expires_tick, 102);
    assert!(!zero_ttl.is_expired_at(101));
    assert!(zero_ttl.is_expired_at(102));

    for (ttl_ms, ttl_ticks) in [(1, 1), (16, 1), (17, 2), (1_000, 60), (1_001, 61)] {
        let mut fixture = fixtures[0].clone();
        fixture["ttl_ms"] = Value::from(ttl_ms);
        let request = CommandRequestV1::from_json(
            &serde_json::to_vec(&fixture).expect("fixture serialization"),
            CURRENT_TICK,
        )
        .expect("bounded TTL request");
        let envelope = CommandEnvelopeV1::assign(request, 4, CURRENT_TICK).unwrap();
        assert_eq!(envelope.expires_tick, envelope.apply_tick + ttl_ticks);
    }
}

#[test]
fn contract_command_payload_and_tick_overflow_are_rejected() {
    assert_eq!(
        CommandRequestV1::from_json(&vec![b' '; MAX_INGRESS_BYTES + 1], CURRENT_TICK)
            .expect_err("oversized command payload")
            .code,
        CommandErrorCode::PayloadTooLarge
    );

    let fixtures: Vec<Value> = serde_json::from_str(GOOD_COMMANDS).expect("valid fixture JSON");
    let input = serde_json::to_vec(&fixtures[0]).expect("fixture serialization");
    assert_eq!(
        CommandRequestV1::from_json(&input, u64::MAX)
            .expect_err("default apply tick overflow")
            .code,
        CommandErrorCode::InvalidApplyTick
    );

    let current_tick = u64::MAX - 120;
    let mut overflow_fixture = fixtures[0].clone();
    overflow_fixture["requested_apply_tick"] = Value::from(u64::MAX);
    overflow_fixture["ttl_ms"] = Value::from(0);
    let overflow_request = CommandRequestV1::from_json(
        &serde_json::to_vec(&overflow_fixture).expect("fixture serialization"),
        current_tick,
    )
    .expect("latest representable apply tick is structurally valid");
    assert_eq!(
        CommandEnvelopeV1::assign(overflow_request, 1, current_tick)
            .expect_err("exclusive expiry overflows")
            .code,
        CommandErrorCode::InvalidApplyTick
    );
}

#[test]
fn contract_terminal_ack_has_exact_status_and_error_shape() {
    let fixture: Vec<Value> = serde_json::from_str(GOOD_COMMANDS).expect("valid fixture JSON");
    let request = CommandRequestV1::from_json(
        &serde_json::to_vec(&fixture[0]).expect("fixture serialization"),
        CURRENT_TICK,
    )
    .expect("good request");
    let envelope = CommandEnvelopeV1::assign(request.clone(), 44, CURRENT_TICK).unwrap();
    let accepted = CommandAckV1::accepted(&envelope, 9, RuntimeEpoch(3));
    assert!(accepted.is_terminal());
    assert_eq!(accepted.status, AckStatus::Accepted);
    assert_eq!(accepted.server_sequence, Some(44));
    assert_eq!(accepted.error_code, None);

    let rejected = CommandAckV1::rejected(
        &request,
        AckStatus::RejectedStale,
        9,
        RuntimeEpoch(3),
        CommandErrorCode::StaleSourceSequence,
    )
    .expect("valid rejected ack");
    assert!(rejected.is_terminal());
    assert_eq!(rejected.server_sequence, None);
    assert_eq!(rejected.apply_tick, None);
    assert_eq!(
        serde_json::to_value(&rejected).unwrap()["status"],
        "rejected_stale"
    );
    assert_eq!(
        serde_json::to_value(&rejected).unwrap()["error_code"],
        "stale_source_sequence"
    );
}

#[test]
fn contract_every_ack_status_has_a_frozen_wire_name() {
    let statuses = [
        AckStatus::Accepted,
        AckStatus::Duplicate,
        AckStatus::RejectedInvalid,
        AckStatus::RejectedStale,
        AckStatus::RejectedExpired,
        AckStatus::RejectedUnauthorized,
        AckStatus::RejectedQueueFull,
        AckStatus::RejectedConflict,
    ];
    let expected = [
        "accepted",
        "duplicate",
        "rejected_invalid",
        "rejected_stale",
        "rejected_expired",
        "rejected_unauthorized",
        "rejected_queue_full",
        "rejected_conflict",
    ];
    let actual: Vec<String> = statuses
        .into_iter()
        .map(|status| {
            serde_json::to_value(status)
                .unwrap()
                .as_str()
                .unwrap()
                .to_owned()
        })
        .collect();
    assert_eq!(actual, expected);
}

fn error_code(value: &str) -> CommandErrorCode {
    match value {
        "malformed_json" => CommandErrorCode::MalformedJson,
        "payload_too_large" => CommandErrorCode::PayloadTooLarge,
        "unsupported_schema_version" => CommandErrorCode::UnsupportedSchemaVersion,
        "invalid_identifier" => CommandErrorCode::InvalidIdentifier,
        "invalid_ttl" => CommandErrorCode::InvalidTtl,
        "invalid_apply_tick" => CommandErrorCode::InvalidApplyTick,
        "invalid_command" => CommandErrorCode::InvalidCommand,
        "operation_mismatch" => CommandErrorCode::OperationMismatch,
        "stale_source_sequence" => CommandErrorCode::StaleSourceSequence,
        "expired" => CommandErrorCode::Expired,
        "unauthorized" => CommandErrorCode::Unauthorized,
        "queue_full" => CommandErrorCode::QueueFull,
        "conflict" => CommandErrorCode::Conflict,
        other => panic!("unknown expected command error code: {other}"),
    }
}
