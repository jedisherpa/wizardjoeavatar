#[allow(dead_code)]
#[path = "../src/chat_event.rs"]
mod chat_event;
#[allow(dead_code)]
#[path = "../src/chat_inbox.rs"]
mod chat_inbox;
#[allow(dead_code)]
#[path = "../src/command.rs"]
mod command;

use chat_event::{CommandId, DiagnosticGeometryId, SourceId, SourceKind};
use chat_inbox::{
    ChatInbox, InboxConfig, InboxEventKind, SourceSequencePolicy, DEFAULT_ACK_RETENTION_TICKS,
    MAX_INBOX_EVENTS, MAX_PENDING_COMMANDS, MAX_SOURCE_WATERMARKS, MAX_TERMINAL_ACKS,
};
use command::{
    AckStatus, CommandEnvelopeV1, CommandErrorCode, CommandRequestV1, DiagnosticPoseRequest,
    LegacyCommandKind, LegacyCommandV1, RuntimeEpoch, SemanticCommandV1, StopScope,
    COMMAND_SCHEMA_VERSION,
};

const REVISION: u64 = 41;
const EPOCH: RuntimeEpoch = RuntimeEpoch(7);

fn config(pending: usize, terminal_acks: usize, events: usize) -> InboxConfig {
    InboxConfig::new(
        pending,
        terminal_acks,
        2_048,
        events,
        DEFAULT_ACK_RETENTION_TICKS,
        1,
    )
    .expect("valid test inbox bounds")
}

fn request(
    command_id: impl Into<String>,
    source_id: impl Into<String>,
    source_sequence: u64,
    requested_apply_tick: Option<u64>,
    ttl_ms: u32,
) -> CommandRequestV1 {
    CommandRequestV1 {
        schema_version: COMMAND_SCHEMA_VERSION,
        command_id: CommandId::new(command_id).expect("command id"),
        source_id: SourceId::new(source_id).expect("source id"),
        source_kind: SourceKind::Chatbot,
        source_sequence,
        requested_apply_tick,
        ttl_ms,
        command: SemanticCommandV1::Legacy(LegacyCommandV1 {
            command: LegacyCommandKind::Idle,
        }),
    }
}

fn emergency_request(command_id: &str, source_sequence: u64) -> CommandRequestV1 {
    let mut request = request(command_id, "runtime", source_sequence, None, 1_000);
    request.source_kind = SourceKind::System;
    request.command = SemanticCommandV1::Stop(StopScope::All);
    request
}

fn diagnostic_request(command_id: &str) -> CommandRequestV1 {
    let mut request = request(command_id, "browser", 1, None, 1_000);
    request.source_kind = SourceKind::Browser;
    request.command = SemanticCommandV1::DiagnosticPose(DiagnosticPoseRequest {
        geometry_id: DiagnosticGeometryId::new("front_idle").unwrap(),
    });
    request
}

#[test]
fn one_hundred_retries_return_the_original_ack_and_apply_once() {
    let mut inbox = ChatInbox::new(InboxConfig::default(), EPOCH);
    let request = request("retry-1", "chatbot-a", 1, None, 1_000);
    let original = inbox.accept(request.clone(), 0, REVISION);
    let original_json = serde_json::to_vec(&original).expect("ack JSON");

    for _ in 0..100 {
        let retry = inbox.accept(request.clone(), 0, REVISION + 99);
        assert_eq!(serde_json::to_vec(&retry).unwrap(), original_json);
        assert_eq!(retry.status, AckStatus::Accepted);
        assert_ne!(retry.status, AckStatus::Duplicate);
    }

    assert_eq!(inbox.pending_len(), 1);
    assert_eq!(inbox.drain_for_tick(1).len(), 1);
    assert!(inbox.drain_for_tick(1).is_empty());
    let metrics = inbox.metrics();
    assert_eq!(metrics.accepted_count, 1);
    assert_eq!(metrics.duplicate_retry_count, 100);
    assert_eq!(metrics.dispatched_count, 1);
}

#[test]
fn same_command_id_with_different_canonical_request_is_conflict() {
    let mut inbox = ChatInbox::new(InboxConfig::default(), EPOCH);
    let original = request("identity-1", "chatbot-a", 1, None, 1_000);
    let accepted = inbox.accept(original.clone(), 0, REVISION);
    let mut conflicting = original;
    conflicting.ttl_ms = 2_000;

    let conflict = inbox.accept(conflicting.clone(), 0, REVISION + 100);
    let conflict_retry = inbox.accept(conflicting, 0, REVISION + 200);
    assert_eq!(conflict.status, AckStatus::RejectedConflict);
    assert_eq!(conflict.error_code, Some(CommandErrorCode::Conflict));
    assert_eq!(conflict.state_revision, accepted.state_revision);
    assert_eq!(conflict, conflict_retry);
    assert_eq!(inbox.pending_len(), 1);
}

#[test]
fn trusted_diagnostic_then_public_reuse_is_conflict_not_cached_acceptance() {
    let mut inbox = ChatInbox::new(InboxConfig::default(), EPOCH);
    let diagnostic = diagnostic_request("trusted-diagnostic");
    let accepted = inbox.accept(diagnostic.clone(), 0, REVISION);
    assert_eq!(accepted.status, AckStatus::Accepted);

    let public_conflict = inbox.accept_public(diagnostic.clone(), 0, REVISION + 100);
    let public_retry = inbox.accept_public(diagnostic.clone(), 0, REVISION + 200);
    assert_eq!(public_conflict.status, AckStatus::RejectedConflict);
    assert_eq!(public_conflict.error_code, Some(CommandErrorCode::Conflict));
    assert_eq!(public_conflict.state_revision, accepted.state_revision);
    assert_eq!(public_conflict, public_retry);
    assert_eq!(
        serde_json::to_vec(&public_conflict).unwrap(),
        serde_json::to_vec(&public_retry).unwrap()
    );
    assert_eq!(inbox.cached_ack(&diagnostic.command_id), Some(&accepted));
    assert_eq!(inbox.pending_len(), 1);
    assert_eq!(inbox.metrics().accepted_count, 1);
    assert_eq!(inbox.metrics().duplicate_retry_count, 0);
}

#[test]
fn public_unauthorized_then_trusted_reuse_conflicts_and_preserves_public_ack() {
    let mut inbox = ChatInbox::new(InboxConfig::default(), EPOCH);
    let diagnostic = diagnostic_request("public-diagnostic");
    let unauthorized = inbox.accept_public(diagnostic.clone(), 0, REVISION);
    let unauthorized_retry = inbox.accept_public(diagnostic.clone(), 0, REVISION + 100);
    assert_eq!(unauthorized.status, AckStatus::RejectedUnauthorized);
    assert_eq!(unauthorized, unauthorized_retry);
    assert_eq!(
        serde_json::to_vec(&unauthorized).unwrap(),
        serde_json::to_vec(&unauthorized_retry).unwrap()
    );

    let trusted_conflict = inbox.accept(diagnostic.clone(), 0, REVISION + 200);
    let trusted_retry = inbox.accept(diagnostic.clone(), 0, REVISION + 300);
    assert_eq!(trusted_conflict.status, AckStatus::RejectedConflict);
    assert_eq!(
        trusted_conflict.error_code,
        Some(CommandErrorCode::Conflict)
    );
    assert_eq!(trusted_conflict.state_revision, unauthorized.state_revision);
    assert_eq!(trusted_conflict, trusted_retry);
    assert_eq!(
        inbox.cached_ack(&diagnostic.command_id),
        Some(&unauthorized)
    );
    assert_eq!(inbox.pending_len(), 0);
    assert!(inbox
        .source_watermark(diagnostic.source_kind, &diagnostic.source_id)
        .is_none());
}

#[test]
fn ten_thousand_randomized_envelopes_replay_identically_in_bounded_same_tick_batches() {
    fn replay(seed: u64) -> Vec<(u64, u64, String)> {
        let mut inbox = ChatInbox::new(InboxConfig::default(), EPOCH);
        let mut random_state = seed;
        let mut replay = Vec::with_capacity(10_000);

        for batch in 0..10_u64 {
            let mut order = (0..1_000_usize).collect::<Vec<_>>();
            deterministic_shuffle(&mut order, &mut random_state);
            let current_tick = batch;
            for source_index in order {
                let request = request(
                    format!("batch-{batch:02}-{source_index:04}"),
                    format!("source-{source_index:04}"),
                    batch,
                    Some(current_tick + 1),
                    1_000,
                );
                assert_eq!(
                    inbox.accept(request, current_tick, REVISION).status,
                    AckStatus::Accepted
                );
            }
            for envelope in inbox.drain_for_tick(current_tick + 1) {
                replay.push((
                    envelope.apply_tick,
                    envelope.server_sequence,
                    envelope.command_id.as_str().to_string(),
                ));
            }
        }
        assert_eq!(replay.len(), 10_000);
        assert!(inbox.pending_len() <= MAX_PENDING_COMMANDS);
        assert!(inbox.terminal_ack_len() <= MAX_TERMINAL_ACKS);
        assert!(inbox.source_watermark_len() <= MAX_SOURCE_WATERMARKS);
        assert!(inbox.metrics().retained_events <= MAX_INBOX_EVENTS);
        replay
    }

    assert_eq!(replay(0x0c0d_e030), replay(0x0c0d_e030));
}

#[test]
fn ten_thousand_envelopes_share_one_apply_tick_and_sort_identically_twice() {
    const CURRENT_TICK: u64 = 100;
    const APPLY_TICK: u64 = 120;
    const ENVELOPE_COUNT: usize = 10_000;

    fn ordered_replay(seed: u64) -> Vec<(u64, u64, String)> {
        let mut envelopes = (0..ENVELOPE_COUNT)
            .map(|index| {
                CommandEnvelopeV1::assign(
                    request(
                        format!("literal-{index:05}"),
                        format!("literal-source-{index:05}"),
                        1,
                        Some(APPLY_TICK),
                        1_000,
                    ),
                    index as u64,
                    CURRENT_TICK,
                )
                .expect("valid same-tick envelope")
            })
            .collect::<Vec<_>>();

        let mut random_state = seed;
        deterministic_shuffle(&mut envelopes, &mut random_state);
        assert!(envelopes
            .iter()
            .all(|envelope| envelope.apply_tick == APPLY_TICK));

        envelopes.sort_by_key(|envelope| envelope.ordering_key());
        assert!(envelopes
            .windows(2)
            .all(|pair| pair[0].ordering_key() < pair[1].ordering_key()));

        envelopes
            .into_iter()
            .map(|envelope| {
                (
                    envelope.apply_tick,
                    envelope.server_sequence,
                    envelope.command_id.as_str().to_string(),
                )
            })
            .collect()
    }

    let first = ordered_replay(0x0c0d_e030);
    let second = ordered_replay(0x0c0d_e030);

    assert_eq!(first.len(), ENVELOPE_COUNT);
    assert_eq!(first, second);
    assert!(first
        .iter()
        .all(|(apply_tick, _, _)| *apply_tick == APPLY_TICK));
    assert_eq!(first.first().map(|entry| entry.1), Some(0));
    assert_eq!(
        first.last().map(|entry| entry.1),
        Some((ENVELOPE_COUNT - 1) as u64)
    );
}

#[test]
fn future_tick_and_exclusive_ttl_boundary_are_exact() {
    for (ttl_ms, ttl_ticks) in [(0, 1), (1, 1), (16, 1), (17, 2), (1_000, 60)] {
        let mut inbox = ChatInbox::new(InboxConfig::default(), EPOCH);
        let ack = inbox.accept(
            request(format!("ttl-{ttl_ms}"), "ttl-source", 1, Some(5), ttl_ms),
            0,
            REVISION,
        );
        let queued = inbox.queue_snapshot();
        assert_eq!(ack.apply_tick, Some(5));
        assert_eq!(queued[0].expires_tick, 5 + ttl_ticks);
    }

    let mut on_time = ChatInbox::new(InboxConfig::default(), EPOCH);
    let ack = on_time.accept(request("future", "chatbot-a", 1, Some(5), 0), 0, REVISION);
    assert_eq!(ack.apply_tick, Some(5));
    let queued = on_time.queue_snapshot();
    assert_eq!(queued[0].expires_tick, 6);
    assert!(on_time.drain_for_tick(4).is_empty());
    assert_eq!(on_time.drain_for_tick(5).len(), 1);

    let mut late = ChatInbox::new(InboxConfig::default(), EPOCH);
    let revision = REVISION;
    let ack = late.accept(request("late", "chatbot-a", 1, Some(5), 0), 0, revision);
    assert_eq!(ack.status, AckStatus::Accepted);
    assert!(late.drain_for_tick(6).is_empty());
    assert_eq!(revision, REVISION);
    assert_eq!(late.metrics().expired_count, 1);
    assert!(late.events().any(|event| {
        event.kind == InboxEventKind::ExpiredBeforeApply
            && event.observed_tick == 6
            && event.ack_status == Some(AckStatus::RejectedExpired)
            && event.error_code == Some(CommandErrorCode::Expired)
    }));
}

#[test]
fn terminal_ack_retention_uses_an_exclusive_tick_boundary() {
    let retention_ticks = 121;
    let config = InboxConfig::new(2, 4, 8, 32, retention_ticks, 1).unwrap();
    let mut inbox = ChatInbox::new(config, EPOCH);
    let first_id = CommandId::new("retained-first").unwrap();

    let first = inbox.accept(
        request("retained-first", "retention-source", 1, None, 1_000),
        0,
        REVISION,
    );
    assert_eq!(first.status, AckStatus::Accepted);
    assert_eq!(inbox.drain_for_tick(1).len(), 1);

    let second = inbox.accept(
        request("retained-second", "retention-source", 2, None, 1_000),
        retention_ticks - 1,
        REVISION,
    );
    assert_eq!(second.status, AckStatus::Accepted);
    assert!(inbox.cached_ack(&first_id).is_some());
    assert_eq!(inbox.drain_for_tick(retention_ticks).len(), 1);

    let third = inbox.accept(
        request("retained-third", "retention-source", 3, None, 1_000),
        retention_ticks,
        REVISION,
    );
    assert_eq!(third.status, AckStatus::Accepted);
    assert!(inbox.cached_ack(&first_id).is_none());
}

#[test]
fn queue_overflow_preserves_reserved_emergency_capacity_and_order() {
    let mut inbox = ChatInbox::new(config(4, 16, 64), EPOCH);
    for sequence in 1..=3_u64 {
        let ack = inbox.accept(
            request(
                format!("ordinary-{sequence}"),
                "chatbot-a",
                sequence,
                None,
                1_000,
            ),
            0,
            REVISION,
        );
        assert_eq!(ack.status, AckStatus::Accepted);
    }
    let sequence_before_reject = inbox.next_server_sequence();
    let rejected = inbox.accept(
        request("overflow", "chatbot-a", 4, None, 1_000),
        0,
        REVISION,
    );
    assert_eq!(rejected.status, AckStatus::RejectedQueueFull);
    assert_eq!(rejected.state_revision, REVISION);
    assert_eq!(inbox.next_server_sequence(), sequence_before_reject);
    assert_eq!(
        inbox
            .source_watermark(SourceKind::Chatbot, &SourceId::new("chatbot-a").unwrap())
            .unwrap()
            .source_sequence,
        3
    );

    let emergency = inbox.accept(emergency_request("emergency", 1), 0, REVISION);
    assert_eq!(emergency.status, AckStatus::Accepted);
    assert_eq!(inbox.pending_len(), 4);
    let dispatched = inbox.drain_for_tick(1);
    assert_eq!(dispatched.len(), 4);
    assert!(dispatched
        .windows(2)
        .all(|pair| pair[0].ordering_key() < pair[1].ordering_key()));
    assert!(matches!(
        dispatched.last().map(|envelope| &envelope.command),
        Some(SemanticCommandV1::Stop(StopScope::All))
    ));
}

#[test]
fn terminal_ack_eviction_is_bounded_and_replay_becomes_stale() {
    let mut inbox = ChatInbox::new(config(2, 3, 64), EPOCH);
    for sequence in 1..=4_u64 {
        let tick = sequence - 1;
        let ack = inbox.accept(
            request(
                format!("evict-{sequence}"),
                "chatbot-a",
                sequence,
                None,
                1_000,
            ),
            tick,
            REVISION,
        );
        assert_eq!(ack.status, AckStatus::Accepted);
        assert_eq!(inbox.drain_for_tick(tick + 1).len(), 1);
        assert!(inbox.terminal_ack_len() <= 3);
    }
    assert!(inbox
        .cached_ack(&CommandId::new("evict-1").unwrap())
        .is_none());
    let pending_before = inbox.pending_len();
    let retry = inbox.accept(request("evict-1", "chatbot-a", 1, None, 1_000), 4, REVISION);
    assert_eq!(retry.status, AckStatus::RejectedStale);
    assert_eq!(retry.state_revision, REVISION);
    assert_eq!(inbox.pending_len(), pending_before);
    assert!(inbox.terminal_ack_len() <= 3);
    assert!(inbox.metrics().terminal_ack_eviction_count > 0);
}

#[test]
fn stale_source_watermark_is_scoped_by_epoch_kind_and_source() {
    let mut inbox = ChatInbox::new(InboxConfig::default(), EPOCH);
    assert_eq!(
        inbox
            .accept(request("fresh", "shared", 5, None, 1_000), 0, REVISION)
            .status,
        AckStatus::Accepted
    );
    let stale = inbox.accept(request("stale", "shared", 4, None, 1_000), 0, REVISION);
    assert_eq!(stale.status, AckStatus::RejectedStale);
    assert_eq!(stale.state_revision, REVISION);

    let mut other_kind = request("other-kind", "shared", 0, None, 1_000);
    other_kind.source_kind = SourceKind::Tts;
    assert_eq!(
        inbox.accept(other_kind, 0, REVISION).status,
        AckStatus::Accepted
    );

    let mut next_epoch = ChatInbox::new(InboxConfig::default(), RuntimeEpoch(EPOCH.0 + 1));
    assert_eq!(
        next_epoch
            .accept(request("next-epoch", "shared", 0, None, 1_000), 0, REVISION)
            .status,
        AckStatus::Accepted
    );
}

#[test]
fn source_and_server_sequences_never_wrap() {
    let mut source_inbox = ChatInbox::new(InboxConfig::default(), EPOCH);
    assert_eq!(
        source_inbox
            .accept(
                request("source-max", "max-source", u64::MAX, None, 1_000),
                0,
                REVISION
            )
            .status,
        AckStatus::Accepted
    );
    let wrapped = source_inbox.accept(
        request("source-wrap", "max-source", 0, None, 1_000),
        0,
        REVISION,
    );
    assert_eq!(wrapped.status, AckStatus::RejectedStale);
    assert_eq!(
        source_inbox.source_sequence_policy(),
        SourceSequencePolicy::StrictMonotonicNewSourceOrEpochAfterMaximum
    );
    assert!(source_inbox.events().any(|event| {
        event.kind == InboxEventKind::SourceRestartRequired
            && event.source_sequence == 0
            && event.error_code == Some(CommandErrorCode::StaleSourceSequence)
    }));
    assert_eq!(
        source_inbox
            .accept(
                request("new-source", "replacement", 0, None, 1_000),
                0,
                REVISION
            )
            .status,
        AckStatus::Accepted
    );

    let mut server_inbox =
        ChatInbox::with_next_server_sequence(InboxConfig::default(), EPOCH, u64::MAX);
    let maximum = server_inbox.accept(request("server-max", "a", 1, None, 1_000), 0, REVISION);
    assert_eq!(maximum.server_sequence, Some(u64::MAX));
    assert_eq!(server_inbox.next_server_sequence(), None);
    let exhausted =
        server_inbox.accept(request("server-overflow", "b", 1, None, 1_000), 0, REVISION);
    assert_eq!(exhausted.status, AckStatus::RejectedConflict);
    assert_eq!(exhausted.state_revision, REVISION);
    assert_eq!(server_inbox.next_server_sequence(), None);
}

#[test]
fn invalid_unauthorized_conflict_stale_and_overflow_rejects_preserve_revision() {
    let mut inbox = ChatInbox::new(config(3, 16, 64), EPOCH);

    let mut invalid = request("invalid", "invalid-source", 1, None, 1_000);
    invalid.schema_version = 0;
    let invalid_ack = inbox.accept(invalid, 0, REVISION);
    assert_eq!(invalid_ack.status, AckStatus::RejectedInvalid);

    let mut diagnostic = request("diagnostic", "browser", 1, None, 1_000);
    diagnostic.source_kind = SourceKind::Browser;
    diagnostic.command = SemanticCommandV1::DiagnosticPose(DiagnosticPoseRequest {
        geometry_id: DiagnosticGeometryId::new("front_idle").unwrap(),
    });
    let unauthorized = inbox.accept_public(diagnostic, 0, REVISION);
    assert_eq!(unauthorized.status, AckStatus::RejectedUnauthorized);

    let accepted_request = request("accepted", "chatbot-a", 10, None, 1_000);
    let accepted = inbox.accept(accepted_request.clone(), 0, REVISION);
    assert_eq!(accepted.status, AckStatus::Accepted);
    let mut conflict_request = accepted_request;
    conflict_request.ttl_ms = 2_000;
    let conflict = inbox.accept(conflict_request, 0, REVISION + 1);
    assert_eq!(conflict.status, AckStatus::RejectedConflict);

    let stale = inbox.accept(request("stale", "chatbot-a", 9, None, 1_000), 0, REVISION);
    assert_eq!(stale.status, AckStatus::RejectedStale);

    assert_eq!(
        inbox
            .accept(request("fill", "chatbot-b", 1, None, 1_000), 0, REVISION)
            .status,
        AckStatus::Accepted
    );
    let overflow = inbox.accept(
        request("overflow", "chatbot-c", 1, None, 1_000),
        0,
        REVISION,
    );
    assert_eq!(overflow.status, AckStatus::RejectedQueueFull);

    for ack in [invalid_ack, unauthorized, conflict, stale, overflow] {
        assert_eq!(ack.state_revision, REVISION);
        assert!(ack.server_sequence.is_none());
        assert!(ack.is_terminal());
    }
}

#[test]
fn replay_and_telemetry_event_storage_is_content_free_and_bounded() {
    let mut inbox = ChatInbox::new(config(2, 8, 3), EPOCH);
    let first = request("event-1", "chatbot-a", 1, None, 1_000);
    let second = request("event-2", "chatbot-b", 1, None, 1_000);
    let _ = inbox.accept(first, 0, REVISION);
    let _ = inbox.accept(second, 0, REVISION);
    let _ = inbox.drain_for_tick(1);
    let _ = inbox.accept(request("event-1", "chatbot-a", 1, None, 1_000), 1, REVISION);

    let events = inbox.events().cloned().collect::<Vec<_>>();
    assert_eq!(events.len(), 3);
    assert!(inbox.metrics().dropped_event_count > 0);
    let encoded = serde_json::to_string(&events).unwrap();
    for forbidden in [
        "payload",
        "text",
        "legacy\":",
        "command\":",
        "event-1",
        "event-2",
        "chatbot-a",
        "chatbot-b",
    ] {
        assert!(
            !encoded.contains(forbidden),
            "logged forbidden field {forbidden}"
        );
    }
    let value = serde_json::to_value(&events).unwrap();
    for event in value.as_array().unwrap() {
        let object = event.as_object().unwrap();
        assert!(!object.contains_key("source_id"));
        assert!(!object.contains_key("command_id"));
        assert!(object.contains_key("source_id_hash64"));
        assert!(object.contains_key("command_id_hash64"));
    }
}

#[test]
fn event_identifier_hashes_are_domain_separated_stable_and_epoch_scoped() {
    fn accepted_event(epoch: RuntimeEpoch) -> chat_inbox::InboxEventV1 {
        let mut inbox = ChatInbox::new(InboxConfig::default(), epoch);
        assert_eq!(
            inbox
                .accept(
                    request("same-identifier", "same-identifier", 1, None, 1_000),
                    0,
                    REVISION
                )
                .status,
            AckStatus::Accepted
        );
        let event = inbox
            .events()
            .find(|event| event.kind == InboxEventKind::Accepted)
            .cloned()
            .expect("accepted event");
        event
    }

    let first = accepted_event(EPOCH);
    let same_epoch = accepted_event(EPOCH);
    let next_epoch = accepted_event(RuntimeEpoch(EPOCH.0 + 1));

    assert_eq!(first.source_id_hash64, same_epoch.source_id_hash64);
    assert_eq!(first.command_id_hash64, same_epoch.command_id_hash64);
    assert_ne!(first.source_id_hash64, first.command_id_hash64);
    assert_ne!(first.source_id_hash64, next_epoch.source_id_hash64);
    assert_ne!(first.command_id_hash64, next_epoch.command_id_hash64);
}

fn deterministic_shuffle<T>(values: &mut [T], state: &mut u64) {
    for index in (1..values.len()).rev() {
        *state = state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        let other = (*state % (index as u64 + 1)) as usize;
        values.swap(index, other);
    }
}
