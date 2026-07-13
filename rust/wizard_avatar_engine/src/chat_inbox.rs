use crate::chat_event::{CommandId, SourceId, SourceKind};
use crate::command::{
    AckStatus, CommandAckV1, CommandContractError, CommandEnvelopeV1, CommandErrorCode,
    CommandRequestV1, RuntimeEpoch, SemanticCommandV1, StopScope, COMMAND_SCHEMA_VERSION,
    MAX_FUTURE_APPLY_TICKS,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::error::Error;
use std::fmt;

pub const MAX_PENDING_COMMANDS: usize = 1_024;
pub const MAX_TERMINAL_ACKS: usize = 8_192;
pub const MAX_SOURCE_WATERMARKS: usize = 8_192;
pub const MAX_INBOX_EVENTS: usize = 8_192;
pub const DEFAULT_ACK_RETENTION_TICKS: u64 = 15 * 60 * 60;
pub const DEFAULT_EMERGENCY_RESERVE: usize = 1;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct InboxConfig {
    pending_capacity: usize,
    terminal_ack_capacity: usize,
    source_watermark_capacity: usize,
    event_capacity: usize,
    ack_retention_ticks: u64,
    emergency_reserve: usize,
}

impl InboxConfig {
    pub fn new(
        pending_capacity: usize,
        terminal_ack_capacity: usize,
        source_watermark_capacity: usize,
        event_capacity: usize,
        ack_retention_ticks: u64,
        emergency_reserve: usize,
    ) -> Result<Self, InboxConfigError> {
        validate_capacity("pending_capacity", pending_capacity, MAX_PENDING_COMMANDS)?;
        validate_capacity(
            "terminal_ack_capacity",
            terminal_ack_capacity,
            MAX_TERMINAL_ACKS,
        )?;
        validate_capacity(
            "source_watermark_capacity",
            source_watermark_capacity,
            MAX_SOURCE_WATERMARKS,
        )?;
        validate_capacity("event_capacity", event_capacity, MAX_INBOX_EVENTS)?;
        if terminal_ack_capacity <= pending_capacity {
            return Err(InboxConfigError::AckCapacityMustExceedPending);
        }
        if ack_retention_ticks <= MAX_FUTURE_APPLY_TICKS {
            return Err(InboxConfigError::AckRetentionTooShort);
        }
        if emergency_reserve == 0 || emergency_reserve >= pending_capacity {
            return Err(InboxConfigError::InvalidEmergencyReserve);
        }
        Ok(Self {
            pending_capacity,
            terminal_ack_capacity,
            source_watermark_capacity,
            event_capacity,
            ack_retention_ticks,
            emergency_reserve,
        })
    }

    #[must_use]
    pub const fn pending_capacity(self) -> usize {
        self.pending_capacity
    }

    #[must_use]
    pub const fn terminal_ack_capacity(self) -> usize {
        self.terminal_ack_capacity
    }

    #[must_use]
    pub const fn source_watermark_capacity(self) -> usize {
        self.source_watermark_capacity
    }

    #[must_use]
    pub const fn event_capacity(self) -> usize {
        self.event_capacity
    }

    #[must_use]
    pub const fn ack_retention_ticks(self) -> u64 {
        self.ack_retention_ticks
    }

    #[must_use]
    pub const fn emergency_reserve(self) -> usize {
        self.emergency_reserve
    }
}

impl Default for InboxConfig {
    fn default() -> Self {
        Self {
            pending_capacity: MAX_PENDING_COMMANDS,
            terminal_ack_capacity: MAX_TERMINAL_ACKS,
            source_watermark_capacity: MAX_SOURCE_WATERMARKS,
            event_capacity: MAX_INBOX_EVENTS,
            ack_retention_ticks: DEFAULT_ACK_RETENTION_TICKS,
            emergency_reserve: DEFAULT_EMERGENCY_RESERVE,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InboxConfigError {
    CapacityOutOfRange { field: &'static str, maximum: usize },
    AckCapacityMustExceedPending,
    AckRetentionTooShort,
    InvalidEmergencyReserve,
}

impl fmt::Display for InboxConfigError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::CapacityOutOfRange { field, maximum } => {
                write!(formatter, "{field} must be in 1..={maximum}")
            }
            Self::AckCapacityMustExceedPending => {
                formatter.write_str("terminal ack capacity must exceed pending capacity")
            }
            Self::AckRetentionTooShort => write!(
                formatter,
                "terminal ack retention must exceed {MAX_FUTURE_APPLY_TICKS} ticks"
            ),
            Self::InvalidEmergencyReserve => formatter
                .write_str("emergency reserve must be non-zero and smaller than pending capacity"),
        }
    }
}

impl Error for InboxConfigError {}

fn validate_capacity(
    field: &'static str,
    value: usize,
    maximum: usize,
) -> Result<(), InboxConfigError> {
    if value == 0 || value > maximum {
        return Err(InboxConfigError::CapacityOutOfRange { field, maximum });
    }
    Ok(())
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IngressAuthority {
    Trusted,
    Public,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SourceSequencePolicy {
    StrictMonotonicNewSourceOrEpochAfterMaximum,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct SourceNamespace {
    runtime_epoch: RuntimeEpoch,
    source_kind: SourceKind,
    source_id: SourceId,
}

impl Ord for SourceNamespace {
    fn cmp(&self, other: &Self) -> Ordering {
        (
            self.runtime_epoch.0,
            source_kind_rank(self.source_kind),
            &self.source_id,
        )
            .cmp(&(
                other.runtime_epoch.0,
                source_kind_rank(other.source_kind),
                &other.source_id,
            ))
    }
}

impl PartialOrd for SourceNamespace {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

const fn source_kind_rank(source_kind: SourceKind) -> u8 {
    match source_kind {
        SourceKind::Browser => 0,
        SourceKind::Chatbot => 1,
        SourceKind::Tts => 2,
        SourceKind::Automation => 3,
        SourceKind::Demo => 4,
        SourceKind::System => 5,
        SourceKind::LegacyAdapter => 6,
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceWatermarkV1 {
    pub runtime_epoch: RuntimeEpoch,
    pub source_kind: SourceKind,
    pub source_id: SourceId,
    pub source_sequence: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InboxEventKind {
    Accepted,
    DuplicateRetry,
    Rejected,
    SourceRestartRequired,
    Dispatched,
    ExpiredBeforeApply,
    TerminalAckEvicted,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct InboxEventV1 {
    pub event_sequence: u64,
    pub observed_tick: u64,
    pub kind: InboxEventKind,
    pub runtime_epoch: RuntimeEpoch,
    pub source_kind: SourceKind,
    pub source_id: SourceId,
    pub command_id: CommandId,
    pub source_sequence: u64,
    pub server_sequence: Option<u64>,
    pub apply_tick: Option<u64>,
    pub ack_status: Option<AckStatus>,
    pub error_code: Option<CommandErrorCode>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct QueuedCommandV1 {
    pub runtime_epoch: RuntimeEpoch,
    pub source_kind: SourceKind,
    pub source_id: SourceId,
    pub command_id: CommandId,
    pub source_sequence: u64,
    pub server_sequence: u64,
    pub apply_tick: u64,
    pub expires_tick: u64,
    pub emergency_stop: bool,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct InboxMetricsSnapshotV1 {
    pub pending_commands: usize,
    pub terminal_acks: usize,
    pub source_watermarks: usize,
    pub retained_events: usize,
    pub ingress_count: u64,
    pub accepted_count: u64,
    pub duplicate_retry_count: u64,
    pub rejected_count: u64,
    pub dispatched_count: u64,
    pub expired_count: u64,
    pub terminal_ack_eviction_count: u64,
    pub dropped_event_count: u64,
}

#[derive(Clone, Debug)]
struct CachedTerminalAck {
    request_fingerprint: [u8; 32],
    ack: CommandAckV1,
    terminal_tick: u64,
    namespace: SourceNamespace,
}

#[derive(Clone, Copy, Debug, Default)]
struct InboxCounters {
    ingress_count: u64,
    accepted_count: u64,
    duplicate_retry_count: u64,
    rejected_count: u64,
    dispatched_count: u64,
    expired_count: u64,
    terminal_ack_eviction_count: u64,
    dropped_event_count: u64,
}

#[derive(Clone, Debug)]
pub struct ChatInbox {
    config: InboxConfig,
    runtime_epoch: RuntimeEpoch,
    next_server_sequence: Option<u64>,
    next_event_sequence: u64,
    last_ack_prune_tick: Option<u64>,
    pending: BTreeMap<(u64, u64), CommandEnvelopeV1>,
    pending_ids: BTreeSet<CommandId>,
    terminal_acks: BTreeMap<CommandId, CachedTerminalAck>,
    terminal_order: VecDeque<CommandId>,
    source_watermarks: BTreeMap<SourceNamespace, u64>,
    events: VecDeque<InboxEventV1>,
    counters: InboxCounters,
}

impl ChatInbox {
    #[must_use]
    pub fn new(config: InboxConfig, runtime_epoch: RuntimeEpoch) -> Self {
        Self::with_next_server_sequence(config, runtime_epoch, 0)
    }

    #[must_use]
    pub fn with_next_server_sequence(
        config: InboxConfig,
        runtime_epoch: RuntimeEpoch,
        next_server_sequence: u64,
    ) -> Self {
        Self {
            config,
            runtime_epoch,
            next_server_sequence: Some(next_server_sequence),
            next_event_sequence: 0,
            last_ack_prune_tick: None,
            pending: BTreeMap::new(),
            pending_ids: BTreeSet::new(),
            terminal_acks: BTreeMap::new(),
            terminal_order: VecDeque::new(),
            source_watermarks: BTreeMap::new(),
            events: VecDeque::new(),
            counters: InboxCounters::default(),
        }
    }

    /// Duplicate retries return the cached original ack unchanged. The frozen
    /// `AckStatus::Duplicate` value is reserved and is not emitted by this inbox.
    #[must_use]
    pub fn accept(
        &mut self,
        request: CommandRequestV1,
        current_tick: u64,
        state_revision: u64,
    ) -> CommandAckV1 {
        self.accept_with_authority(
            request,
            current_tick,
            state_revision,
            IngressAuthority::Trusted,
        )
    }

    #[must_use]
    pub fn accept_public(
        &mut self,
        request: CommandRequestV1,
        current_tick: u64,
        state_revision: u64,
    ) -> CommandAckV1 {
        self.accept_with_authority(
            request,
            current_tick,
            state_revision,
            IngressAuthority::Public,
        )
    }

    #[must_use]
    pub fn accept_with_authority(
        &mut self,
        request: CommandRequestV1,
        current_tick: u64,
        state_revision: u64,
        authority: IngressAuthority,
    ) -> CommandAckV1 {
        increment(&mut self.counters.ingress_count);
        self.prune_terminal_acks(current_tick);

        let request_fingerprint = match canonical_request_fingerprint(&request) {
            Ok(fingerprint) => fingerprint,
            Err(error) => {
                return self.reject_uncached(
                    &request,
                    current_tick,
                    state_revision,
                    AckStatus::RejectedInvalid,
                    error.code,
                    InboxEventKind::Rejected,
                );
            }
        };

        if let Some(cached) = self.terminal_acks.get(&request.command_id).cloned() {
            if cached.request_fingerprint == request_fingerprint {
                increment(&mut self.counters.duplicate_retry_count);
                self.record_request_event(
                    InboxEventKind::DuplicateRetry,
                    current_tick,
                    &request,
                    &cached.ack,
                );
                return cached.ack;
            }
            return self.reject_uncached(
                &request,
                current_tick,
                cached.ack.state_revision,
                AckStatus::RejectedConflict,
                CommandErrorCode::Conflict,
                InboxEventKind::Rejected,
            );
        }

        let validation = request
            .validate(current_tick)
            .and_then(|()| match authority {
                IngressAuthority::Trusted => Ok(()),
                IngressAuthority::Public => request.validate_public(),
            });
        if let Err(error) = validation {
            let (status, code) = rejection_for_contract_error(&error);
            return self.reject_and_cache(
                request,
                request_fingerprint,
                current_tick,
                state_revision,
                status,
                code,
                InboxEventKind::Rejected,
            );
        }

        let namespace = self.namespace_for(&request);
        if let Some(watermark) = self.source_watermarks.get(&namespace).copied() {
            if request.source_sequence <= watermark {
                let event_kind = if watermark == u64::MAX {
                    InboxEventKind::SourceRestartRequired
                } else {
                    InboxEventKind::Rejected
                };
                return self.reject_and_cache(
                    request,
                    request_fingerprint,
                    current_tick,
                    state_revision,
                    AckStatus::RejectedStale,
                    CommandErrorCode::StaleSourceSequence,
                    event_kind,
                );
            }
        } else if self.source_watermarks.len() >= self.config.source_watermark_capacity {
            return self.reject_and_cache(
                request,
                request_fingerprint,
                current_tick,
                state_revision,
                AckStatus::RejectedQueueFull,
                CommandErrorCode::QueueFull,
                InboxEventKind::Rejected,
            );
        }

        let emergency_stop = is_emergency_stop(&request.command);
        if !self.has_queue_capacity(emergency_stop) {
            return self.reject_and_cache(
                request,
                request_fingerprint,
                current_tick,
                state_revision,
                AckStatus::RejectedQueueFull,
                CommandErrorCode::QueueFull,
                InboxEventKind::Rejected,
            );
        }

        let Some(server_sequence) = self.next_server_sequence else {
            return self.reject_and_cache(
                request,
                request_fingerprint,
                current_tick,
                state_revision,
                AckStatus::RejectedConflict,
                CommandErrorCode::Conflict,
                InboxEventKind::Rejected,
            );
        };
        let envelope =
            match CommandEnvelopeV1::assign(request.clone(), server_sequence, current_tick) {
                Ok(envelope) => envelope,
                Err(error) => {
                    let (status, code) = rejection_for_contract_error(&error);
                    return self.reject_and_cache(
                        request,
                        request_fingerprint,
                        current_tick,
                        state_revision,
                        status,
                        code,
                        InboxEventKind::Rejected,
                    );
                }
            };

        self.next_server_sequence = server_sequence.checked_add(1);
        self.pending
            .insert(envelope.ordering_key(), envelope.clone());
        self.pending_ids.insert(envelope.command_id.clone());
        self.source_watermarks
            .insert(namespace.clone(), envelope.source_sequence);

        let ack = CommandAckV1::accepted(&envelope, state_revision, self.runtime_epoch);
        self.cache_terminal(
            request,
            request_fingerprint,
            ack.clone(),
            current_tick,
            namespace,
        );
        increment(&mut self.counters.accepted_count);
        self.record_envelope_event(
            InboxEventKind::Accepted,
            current_tick,
            &envelope,
            Some(&ack),
        );
        ack
    }

    #[must_use]
    pub fn drain_for_tick(&mut self, tick: u64) -> Vec<CommandEnvelopeV1> {
        let due_keys = self
            .pending
            .range(..=(tick, u64::MAX))
            .map(|(key, _)| *key)
            .collect::<Vec<_>>();
        let mut dispatched = Vec::with_capacity(due_keys.len());
        for key in due_keys {
            let Some(envelope) = self.pending.remove(&key) else {
                continue;
            };
            self.pending_ids.remove(&envelope.command_id);
            if envelope.is_expired_at(tick) || envelope.apply_tick != tick {
                increment(&mut self.counters.expired_count);
                self.record_envelope_event(
                    InboxEventKind::ExpiredBeforeApply,
                    tick,
                    &envelope,
                    None,
                );
                continue;
            }
            increment(&mut self.counters.dispatched_count);
            self.record_envelope_event(InboxEventKind::Dispatched, tick, &envelope, None);
            dispatched.push(envelope);
        }
        dispatched
    }

    #[must_use]
    pub fn pending_len(&self) -> usize {
        self.pending.len()
    }

    #[must_use]
    pub fn terminal_ack_len(&self) -> usize {
        self.terminal_acks.len()
    }

    #[must_use]
    pub fn source_watermark_len(&self) -> usize {
        self.source_watermarks.len()
    }

    #[must_use]
    pub fn next_server_sequence(&self) -> Option<u64> {
        self.next_server_sequence
    }

    #[must_use]
    pub const fn runtime_epoch(&self) -> RuntimeEpoch {
        self.runtime_epoch
    }

    #[must_use]
    pub const fn source_sequence_policy(&self) -> SourceSequencePolicy {
        SourceSequencePolicy::StrictMonotonicNewSourceOrEpochAfterMaximum
    }

    #[must_use]
    pub fn cached_ack(&self, command_id: &CommandId) -> Option<&CommandAckV1> {
        self.terminal_acks.get(command_id).map(|entry| &entry.ack)
    }

    #[must_use]
    pub fn source_watermark(
        &self,
        source_kind: SourceKind,
        source_id: &SourceId,
    ) -> Option<SourceWatermarkV1> {
        let namespace = SourceNamespace {
            runtime_epoch: self.runtime_epoch,
            source_kind,
            source_id: source_id.clone(),
        };
        self.source_watermarks
            .get(&namespace)
            .copied()
            .map(|source_sequence| SourceWatermarkV1 {
                runtime_epoch: self.runtime_epoch,
                source_kind,
                source_id: source_id.clone(),
                source_sequence,
            })
    }

    #[must_use]
    pub fn queue_snapshot(&self) -> Vec<QueuedCommandV1> {
        self.pending
            .values()
            .map(|envelope| QueuedCommandV1 {
                runtime_epoch: self.runtime_epoch,
                source_kind: envelope.source_kind,
                source_id: envelope.source_id.clone(),
                command_id: envelope.command_id.clone(),
                source_sequence: envelope.source_sequence,
                server_sequence: envelope.server_sequence,
                apply_tick: envelope.apply_tick,
                expires_tick: envelope.expires_tick,
                emergency_stop: is_emergency_stop(&envelope.command),
            })
            .collect()
    }

    pub fn events(&self) -> impl ExactSizeIterator<Item = &InboxEventV1> {
        self.events.iter()
    }

    pub fn drain_events(&mut self) -> Vec<InboxEventV1> {
        self.events.drain(..).collect()
    }

    #[must_use]
    pub fn metrics(&self) -> InboxMetricsSnapshotV1 {
        InboxMetricsSnapshotV1 {
            pending_commands: self.pending.len(),
            terminal_acks: self.terminal_acks.len(),
            source_watermarks: self.source_watermarks.len(),
            retained_events: self.events.len(),
            ingress_count: self.counters.ingress_count,
            accepted_count: self.counters.accepted_count,
            duplicate_retry_count: self.counters.duplicate_retry_count,
            rejected_count: self.counters.rejected_count,
            dispatched_count: self.counters.dispatched_count,
            expired_count: self.counters.expired_count,
            terminal_ack_eviction_count: self.counters.terminal_ack_eviction_count,
            dropped_event_count: self.counters.dropped_event_count,
        }
    }

    fn namespace_for(&self, request: &CommandRequestV1) -> SourceNamespace {
        SourceNamespace {
            runtime_epoch: self.runtime_epoch,
            source_kind: request.source_kind,
            source_id: request.source_id.clone(),
        }
    }

    fn has_queue_capacity(&self, emergency_stop: bool) -> bool {
        if self.pending.len() >= self.config.pending_capacity {
            return false;
        }
        if emergency_stop {
            return true;
        }
        let ordinary_count = self
            .pending
            .values()
            .filter(|envelope| !is_emergency_stop(&envelope.command))
            .count();
        ordinary_count < self.config.pending_capacity - self.config.emergency_reserve
    }

    #[allow(clippy::too_many_arguments)]
    fn reject_and_cache(
        &mut self,
        request: CommandRequestV1,
        request_fingerprint: [u8; 32],
        current_tick: u64,
        state_revision: u64,
        status: AckStatus,
        error_code: CommandErrorCode,
        event_kind: InboxEventKind,
    ) -> CommandAckV1 {
        let namespace = self.namespace_for(&request);
        let ack = rejected_ack(
            &request,
            status,
            state_revision,
            self.runtime_epoch,
            error_code,
        );
        self.cache_terminal(
            request.clone(),
            request_fingerprint,
            ack.clone(),
            current_tick,
            namespace,
        );
        increment(&mut self.counters.rejected_count);
        self.record_request_event(event_kind, current_tick, &request, &ack);
        ack
    }

    #[allow(clippy::too_many_arguments)]
    fn reject_uncached(
        &mut self,
        request: &CommandRequestV1,
        current_tick: u64,
        state_revision: u64,
        status: AckStatus,
        error_code: CommandErrorCode,
        event_kind: InboxEventKind,
    ) -> CommandAckV1 {
        let ack = rejected_ack(
            request,
            status,
            state_revision,
            self.runtime_epoch,
            error_code,
        );
        increment(&mut self.counters.rejected_count);
        self.record_request_event(event_kind, current_tick, request, &ack);
        ack
    }

    fn cache_terminal(
        &mut self,
        request: CommandRequestV1,
        request_fingerprint: [u8; 32],
        ack: CommandAckV1,
        current_tick: u64,
        namespace: SourceNamespace,
    ) {
        while self.terminal_acks.len() >= self.config.terminal_ack_capacity {
            if !self.evict_oldest_non_pending(current_tick) {
                return;
            }
        }
        self.terminal_order.push_back(request.command_id.clone());
        self.terminal_acks.insert(
            request.command_id,
            CachedTerminalAck {
                request_fingerprint,
                ack,
                terminal_tick: current_tick,
                namespace,
            },
        );
    }

    fn prune_terminal_acks(&mut self, current_tick: u64) {
        if self
            .last_ack_prune_tick
            .is_some_and(|last_tick| current_tick <= last_tick)
        {
            return;
        }
        self.last_ack_prune_tick = Some(current_tick);
        let entries_to_scan = self.terminal_order.len();
        for _ in 0..entries_to_scan {
            let Some(command_id) = self.terminal_order.pop_front() else {
                break;
            };
            let expired = self.terminal_acks.get(&command_id).is_some_and(|entry| {
                !self.pending_ids.contains(&command_id)
                    && entry
                        .terminal_tick
                        .checked_add(self.config.ack_retention_ticks)
                        .is_some_and(|expires_tick| current_tick >= expires_tick)
            });
            if expired {
                if let Some(entry) = self.terminal_acks.remove(&command_id) {
                    self.record_terminal_eviction(entry, current_tick);
                }
            } else if self.terminal_acks.contains_key(&command_id) {
                self.terminal_order.push_back(command_id);
            }
        }
    }

    fn evict_oldest_non_pending(&mut self, current_tick: u64) -> bool {
        let entries_to_scan = self.terminal_order.len();
        for _ in 0..entries_to_scan {
            let Some(command_id) = self.terminal_order.pop_front() else {
                break;
            };
            if self.pending_ids.contains(&command_id) {
                self.terminal_order.push_back(command_id);
                continue;
            }
            if let Some(entry) = self.terminal_acks.remove(&command_id) {
                self.record_terminal_eviction(entry, current_tick);
                return true;
            }
        }
        false
    }

    fn record_terminal_eviction(&mut self, entry: CachedTerminalAck, current_tick: u64) {
        increment(&mut self.counters.terminal_ack_eviction_count);
        self.record_event(InboxEventV1 {
            event_sequence: 0,
            observed_tick: current_tick,
            kind: InboxEventKind::TerminalAckEvicted,
            runtime_epoch: entry.namespace.runtime_epoch,
            source_kind: entry.namespace.source_kind,
            source_id: entry.namespace.source_id,
            command_id: entry.ack.command_id,
            source_sequence: entry.ack.source_sequence,
            server_sequence: entry.ack.server_sequence,
            apply_tick: entry.ack.apply_tick,
            ack_status: Some(entry.ack.status),
            error_code: entry.ack.error_code,
        });
    }

    fn record_request_event(
        &mut self,
        kind: InboxEventKind,
        tick: u64,
        request: &CommandRequestV1,
        ack: &CommandAckV1,
    ) {
        self.record_event(InboxEventV1 {
            event_sequence: 0,
            observed_tick: tick,
            kind,
            runtime_epoch: self.runtime_epoch,
            source_kind: request.source_kind,
            source_id: request.source_id.clone(),
            command_id: request.command_id.clone(),
            source_sequence: request.source_sequence,
            server_sequence: ack.server_sequence,
            apply_tick: ack.apply_tick,
            ack_status: Some(ack.status),
            error_code: ack.error_code,
        });
    }

    fn record_envelope_event(
        &mut self,
        kind: InboxEventKind,
        tick: u64,
        envelope: &CommandEnvelopeV1,
        ack: Option<&CommandAckV1>,
    ) {
        let (ack_status, error_code) = match ack {
            Some(ack) => (Some(ack.status), ack.error_code),
            None if kind == InboxEventKind::ExpiredBeforeApply => (
                Some(AckStatus::RejectedExpired),
                Some(CommandErrorCode::Expired),
            ),
            None => (None, None),
        };
        self.record_event(InboxEventV1 {
            event_sequence: 0,
            observed_tick: tick,
            kind,
            runtime_epoch: self.runtime_epoch,
            source_kind: envelope.source_kind,
            source_id: envelope.source_id.clone(),
            command_id: envelope.command_id.clone(),
            source_sequence: envelope.source_sequence,
            server_sequence: Some(envelope.server_sequence),
            apply_tick: Some(envelope.apply_tick),
            ack_status,
            error_code,
        });
    }

    fn record_event(&mut self, mut event: InboxEventV1) {
        event.event_sequence = self.next_event_sequence;
        self.next_event_sequence = self.next_event_sequence.saturating_add(1);
        if self.events.len() == self.config.event_capacity {
            self.events.pop_front();
            increment(&mut self.counters.dropped_event_count);
        }
        self.events.push_back(event);
    }
}

fn canonical_request_fingerprint(
    request: &CommandRequestV1,
) -> Result<[u8; 32], CommandContractError> {
    let canonical = request.to_canonical_json().map_err(|_| {
        CommandContractError::new(CommandErrorCode::InvalidCommand, "command_request")
    })?;
    Ok(Sha256::digest(canonical).into())
}

fn rejection_for_contract_error(error: &CommandContractError) -> (AckStatus, CommandErrorCode) {
    match error.code {
        CommandErrorCode::Unauthorized => (AckStatus::RejectedUnauthorized, error.code),
        CommandErrorCode::Expired => (AckStatus::RejectedExpired, error.code),
        CommandErrorCode::StaleSourceSequence => (AckStatus::RejectedStale, error.code),
        CommandErrorCode::QueueFull => (AckStatus::RejectedQueueFull, error.code),
        CommandErrorCode::Conflict => (AckStatus::RejectedConflict, error.code),
        CommandErrorCode::MalformedJson
        | CommandErrorCode::PayloadTooLarge
        | CommandErrorCode::UnsupportedSchemaVersion
        | CommandErrorCode::InvalidIdentifier
        | CommandErrorCode::InvalidTtl
        | CommandErrorCode::InvalidApplyTick
        | CommandErrorCode::InvalidCommand
        | CommandErrorCode::OperationMismatch => (AckStatus::RejectedInvalid, error.code),
    }
}

fn rejected_ack(
    request: &CommandRequestV1,
    status: AckStatus,
    state_revision: u64,
    runtime_epoch: RuntimeEpoch,
    error_code: CommandErrorCode,
) -> CommandAckV1 {
    CommandAckV1 {
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
    }
}

fn is_emergency_stop(command: &SemanticCommandV1) -> bool {
    matches!(command, SemanticCommandV1::Stop(StopScope::All))
}

fn increment(value: &mut u64) {
    *value = value.saturating_add(1);
}
