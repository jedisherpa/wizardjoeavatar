from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace as dataclass_replace
from itertools import count
from collections import deque
from typing import Dict, Optional, Set

from .animation_trace import (
    ANIMATION_TRUTH_TRACE_CAPACITY,
    ANIMATION_TRUTH_TRACE_SCHEMA,
    ANIMATION_TRUTH_TRACE_VERSION,
)
from .character_capabilities import derive_character_capability_manifest
from .commanding import CommandAckV1, CommandEnvelopeV1, OrderedCommandInbox, QueuedCommand
from .frame_hash import frame_hash
from .frame_source import ProceduralWizardFrameSource
from .models import CommandResult, WizardCellFrame, WizardCommand, WizardState
from .protocol import encode_keyframe
from .performance_application import PerformanceApplication
from .performance_context import PerformanceContextV1
from .performance_release import (
    GovernedSpeechRegistrationV1,
    PerformanceContextRequestV1,
)
from .performance_score import CompiledScoreRepository
from .permission_world import CapabilityPermissionV1, PermissionWorldStateV1
from .media_session import MediaSessionAckV1, MediaSessionSnapshotV1
from .runtime import AvatarRuntime, ReplayLog, canonical_sha256


_subscriber_ids = count(1)
DEFAULT_MAX_SUBSCRIBERS = 64


class SubscriberLimitError(RuntimeError):
    pass


def _permission_render_signature(policy):
    if policy is None:
        return None
    return (
        policy.source_state_sha256,
        policy.motion_profile,
        policy.managed_world_states,
        policy.managed_effects,
        policy.managed_props,
        policy.visible_world_states,
        policy.visible_effects,
        policy.visible_props,
    )


@dataclass(eq=False)
class WizardSubscriber:
    queue: asyncio.Queue[bytes]
    subscriber_id: int = field(default_factory=lambda: next(_subscriber_ids))
    dropped_frame_count: int = 0
    resync_count: int = 0


class WizardFrameHub:
    def __init__(
        self,
        frame_source: ProceduralWizardFrameSource,
        codec: str = "adaptive",
        score_repository: Optional[CompiledScoreRepository] = None,
        max_subscribers: int = DEFAULT_MAX_SUBSCRIBERS,
    ) -> None:
        if (
            isinstance(max_subscribers, bool)
            or not isinstance(max_subscribers, int)
            or max_subscribers <= 0
        ):
            raise ValueError("max_subscribers must be a positive integer")
        self.frame_source = frame_source
        self.codec = codec
        self.max_subscribers = max_subscribers
        self.runtime_epoch = "wizard-{}".format(uuid.uuid4().hex)
        package_path = getattr(self.frame_source, "character_package_path", None)
        capability_manifest = (
            derive_character_capability_manifest(package_path)
            if package_path is not None
            else None
        )
        self.performance = PerformanceApplication(
            self.runtime_epoch,
            score_repository=score_repository,
            character_id=self.frame_source.character_package.character_id,
            package_digest=(
                "sha256:" + "0" * 64
                if capability_manifest is None
                else str(capability_manifest["sources"]["package_sha256"])
            ),
            manifest_digest=(
                "sha256:" + "0" * 64
                if capability_manifest is None
                else str(capability_manifest["manifest_sha256"])
            ),
            capability_manifest=capability_manifest,
        )
        self.command_inbox = OrderedCommandInbox(self.runtime_epoch)
        self.replay_log = ReplayLog(
            {
                "schema_version": 1,
                "runtime_epoch": self.runtime_epoch,
                "character_id": self.frame_source.character_package.character_id,
                "tick_rate": AvatarRuntime.TICK_RATE,
            }
        )
        self.runtime = AvatarRuntime(
            initial_state=self.frame_source.current_state(),
            reducer=self._reduce_runtime_tick,
            runtime_epoch=self.runtime_epoch,
            inbox=self.command_inbox,
            replay_log=self.replay_log,
        )
        self._legacy_source_sequence = 0
        self._command_types: Dict[str, str] = {}
        self._command_results: Dict[str, CommandResult] = {}
        self._command_waiters: Dict[str, asyncio.Event] = {}
        self._subscribers: Set[WizardSubscriber] = set()
        self._task: Optional[asyncio.Task] = None
        self._render_executor: Optional[ThreadPoolExecutor] = None
        self._task_error_code: Optional[str] = None
        self._task_failure_count = 0
        self._lock: Optional[asyncio.Lock] = None
        self._lock_loop: Optional[asyncio.AbstractEventLoop] = None
        self._latest_frame: Optional[WizardCellFrame] = None
        self._force_keyframe = False
        self._started_at = 0.0
        self._published_frames = 0
        self._queue_drops = 0
        self._resync_count = 0
        self._forced_keyframe_count = 0
        self._stale_render_discard_count = 0
        self._schedule_overruns = 0
        self._runtime_loop_observed_ns: Optional[int] = None
        self._presentation_clock_dropped_ns = 0
        self._source_hash_history = deque(maxlen=240)
        self._animation_truth_trace = deque(maxlen=ANIMATION_TRUTH_TRACE_CAPACITY)
        self._published_at = deque(maxlen=240)

    @property
    def task_error_code(self) -> Optional[str]:
        return self._task_error_code

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._started_at = time.perf_counter()
            now_ns = time.perf_counter_ns()
            if self._runtime_loop_observed_ns is None:
                self.runtime.advance_to(now_ns)
            # A stopped or overloaded projector does not create a simulation
            # debt that may be replayed as skipped authored poses.
            self._runtime_loop_observed_ns = now_ns
            self._task_error_code = None
            if self._render_executor is None:
                self._render_executor = ThreadPoolExecutor(
                    max_workers=1,
                    thread_name_prefix="wizard-frame-render",
                )
            self._task = asyncio.create_task(self._run(), name="wizard-frame-hub")
            self._task.add_done_callback(self._record_task_outcome)

    async def stop(self) -> None:
        task = self._task
        if task is not None:
            task.cancel()
            # The done callback records any non-cancellation failure. Shutdown
            # must remain idempotent when it is invoked after that failure.
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        self._task = None
        await self._settle_waiters_on_stop()
        executor = self._render_executor
        self._render_executor = None
        if executor is not None:
            await asyncio.to_thread(executor.shutdown, wait=True, cancel_futures=True)

    def _record_task_outcome(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        try:
            error = task.exception()
        except asyncio.CancelledError:
            return
        self._task_failure_count += 1
        self._task_error_code = (
            "frame_hub_failed" if error is not None else "frame_hub_stopped_unexpectedly"
        )
        self._update_diagnostics()

    async def _settle_waiters_on_stop(self) -> None:
        async with self._current_lock():
            self.command_inbox.discard_pending()
            state = self.frame_source.current_state().as_public_dict()
            for command_id, waiter in tuple(self._command_waiters.items()):
                ack = self.command_inbox.ack_for(command_id)
                if ack is not None and ack.disposition == "accepted":
                    self.command_inbox.mark_rejected(
                        command_id,
                        self.runtime.clock.state_revision,
                        "runtime_stopped",
                        "runtime stopped before command application",
                    )
                self._command_results[command_id] = CommandResult(
                    False,
                    "runtime stopped before command application",
                    state,
                )
                waiter.set()
            self._command_types.clear()

    async def subscribe(self, max_queue_size: int = 8) -> WizardSubscriber:
        await self.start()
        if len(self._subscribers) >= self.max_subscribers:
            raise SubscriberLimitError("avatar subscriber limit reached")
        subscriber = WizardSubscriber(asyncio.Queue(maxsize=max_queue_size))
        self._subscribers.add(subscriber)
        if self._latest_frame is not None:
            await self.enqueue_keyframe(subscriber)
        self._update_diagnostics()
        return subscriber

    def unsubscribe(self, subscriber: WizardSubscriber) -> None:
        self._subscribers.discard(subscriber)
        self._update_diagnostics()

    async def enqueue_keyframe(self, subscriber: WizardSubscriber) -> None:
        async with self._current_lock():
            if self._latest_frame is None:
                return
            # A resync must be a normal publication transaction. Re-encoding the
            # latest frame only for this subscriber creates a second transport
            # truth for one frame index, which cannot be paired atomically with
            # the accepted animation trace. Clear stale deltas and force the next
            # globally committed frame to be a keyframe instead.
            self._clear_queue(subscriber.queue)
            self._force_keyframe = True
            subscriber.resync_count += 1
            self._resync_count += 1
        self._update_diagnostics()

    def force_keyframe(self) -> None:
        self._force_keyframe = True

    async def apply_command(self, command: WizardCommand) -> CommandResult:
        await self.start()
        async with self._current_lock():
            self._legacy_source_sequence += 1
            envelope = self._legacy_envelope(command, self._legacy_source_sequence)
            ack, waiter = self._enqueue(envelope, command.type)
        return await self._await_command(envelope.command_id, ack, waiter)

    async def apply_envelope(self, envelope: CommandEnvelopeV1) -> tuple[CommandAckV1, CommandResult]:
        await self.start()
        async with self._current_lock():
            command_type = self._controller_command_type(envelope.kind)
            ack, waiter = self._enqueue(envelope, command_type)
        result = await self._await_command(envelope.command_id, ack, waiter)
        final_ack = self.command_inbox.ack_for(envelope.command_id) or ack
        return final_ack, result

    def diagnostics_extra(self, include_replay_digest: bool = True) -> dict:
        now = time.perf_counter()
        elapsed = max(0.001, now - self._started_at) if self._started_at else 0.001
        presentation_window = 0.0
        if len(self._published_at) >= 2:
            presentation_window = (len(self._published_at) - 1) / max(
                0.001,
                self._published_at[-1] - self._published_at[0],
            )
        diagnostics = {
            "subscriber_count": len(self._subscribers),
            "subscriber_capacity": self.max_subscribers,
            "hub_actual_fps": self._published_frames / elapsed,
            "hub_window_fps": presentation_window,
            "hub_queue_drops": self._queue_drops,
            "resync_count": self._resync_count,
            "slow_subscriber_count": sum(1 for subscriber in self._subscribers if subscriber.dropped_frame_count),
            "forced_keyframe_count": self._forced_keyframe_count,
            "stale_render_discard_count": self._stale_render_discard_count,
            "schedule_overruns": self._schedule_overruns,
            "presentation_clock_dropped_ns": self._presentation_clock_dropped_ns,
            "frame_hub_error_code": self._task_error_code,
            "frame_hub_failure_count": self._task_failure_count,
            "source_hash_history_count": len(self._source_hash_history),
            "animation_truth_trace_count": len(self._animation_truth_trace),
            "runtime_epoch": self.runtime_epoch,
            "simulation_tick": self.runtime.clock.simulation_tick,
            "state_revision": self.runtime.clock.state_revision,
            "runtime_state_hash": self.runtime.current_snapshot().state_hash,
            **self.runtime.event_retention_diagnostics,
            "ordered_command_pending": self.command_inbox.pending_count,
            **self.command_inbox.source_retention_diagnostics,
            "replay_record_count": self.replay_log.total_record_count,
            "replay_retained_record_count": self.replay_log.retained_record_count,
            "replay_evicted_record_count": self.replay_log.evicted_record_count,
            "replay_is_truncated": self.replay_log.is_truncated,
            "replay_sha256": self.replay_log.sha256(),
        }
        if include_replay_digest:
            diagnostics["replay_retained_sha256"] = self.replay_log.retained_sha256()
        diagnostics["media_performance"] = self.performance.diagnostics(time.perf_counter_ns() // 1000)
        return diagnostics

    async def accept_media_session(
        self,
        snapshot: MediaSessionSnapshotV1,
        receipt_monotonic_us: Optional[int] = None,
    ) -> MediaSessionAckV1:
        await self.start()
        # Score loading and validation may touch disk. Complete that work before
        # entering the single-writer hub lock; scheduler ticks only resolve the
        # resulting immutable score from memory.
        await asyncio.to_thread(self.performance.prepare_snapshot, snapshot)
        receipt = receipt_monotonic_us if receipt_monotonic_us is not None else time.perf_counter_ns() // 1000
        async with self._current_lock():
            return self.performance.accept_snapshot(snapshot, receipt)

    async def media_session_status(self) -> dict:
        async with self._current_lock():
            return dict(self.performance.diagnostics(time.perf_counter_ns() // 1000))

    async def performance_binding(self) -> dict:
        """Return the content-free runtime binding required before speech admission."""

        await self.start()
        async with self._current_lock():
            return {
                "schema_version": 1,
                "wizard_runtime_epoch": self.performance.runtime_epoch,
                "character_id": self.performance.character_id,
                "package_digest": self.performance.package_digest,
                "reconciliation_generation": (
                    self.performance.scheduler.coordinator.reconciliation_generation
                ),
                "revocation_generation": (
                    self.performance.governed_speech.revocation_generation
                ),
            }

    async def capture_performance_context(
        self,
        request: PerformanceContextRequestV1,
    ) -> PerformanceContextV1:
        await self.start()
        async with self._current_lock():
            return self.performance.capture_performance_context(
                request,
                self.frame_source.controller,
                time.perf_counter_ns() // 1000,
            )

    async def register_governed_speech(
        self,
        registration: GovernedSpeechRegistrationV1,
    ) -> dict:
        await self.start()
        async with self._current_lock():
            self.performance.register_governed_speech(
                registration,
                now_wall_ms=time.time_ns() // 1_000_000,
                now_monotonic_us=time.perf_counter_ns() // 1000,
            )
            return dict(self.performance.governed_speech.diagnostics())

    async def revoke_governed_speech(self, generation: int) -> dict:
        await self.start()
        async with self._current_lock():
            self.performance.revoke_governed_speech(
                generation,
                self.frame_source.controller,
            )
            return dict(self.performance.governed_speech.diagnostics())

    async def accept_permission_world(
        self,
        state: PermissionWorldStateV1,
    ) -> dict:
        await self.start()
        async with self._current_lock():
            now_wall_ms = time.time_ns() // 1_000_000
            now_monotonic_us = time.perf_counter_ns() // 1000
            diagnostics = self.performance.accept_permission_world(
                state,
                received_at_wall_ms=now_wall_ms,
            )
            self.performance._apply_authoritative_permission_world(
                self.frame_source.controller,
                now_monotonic_us,
            )
            return dict(diagnostics)

    async def permission_world_status(self) -> dict:
        await self.start()
        async with self._current_lock():
            return dict(
                self.performance.permission_world_snapshot(
                    time.time_ns() // 1_000_000
                )
            )

    async def simulate_permission_world(
        self,
        permission: CapabilityPermissionV1,
    ) -> dict:
        await self.start()
        async with self._current_lock():
            return dict(
                self.performance.simulate_permission_world(
                    permission,
                    time.time_ns() // 1_000_000,
                )
            )

    async def clear_permission_world_simulation(self) -> dict:
        await self.start()
        async with self._current_lock():
            return dict(self.performance.clear_permission_world_simulation())

    async def set_reactions_paused(self, paused: bool) -> dict:
        await self.start()
        async with self._current_lock():
            self.performance.set_paused(paused, self.frame_source.controller)
            return {"reactions_paused": self.performance.paused}

    def source_hash_history(self) -> list[dict]:
        return list(self._source_hash_history)

    async def animation_truth_trace_snapshot(self) -> dict:
        """Return an immutable in-memory snapshot without touching disk."""

        await self.start()
        async with self._current_lock():
            records = tuple(self._animation_truth_trace)
        return {
            "schema": ANIMATION_TRUTH_TRACE_SCHEMA,
            "schema_version": ANIMATION_TRUTH_TRACE_VERSION,
            "capacity": ANIMATION_TRUTH_TRACE_CAPACITY,
            "count": len(records),
            "records": [record.to_mapping() for record in records],
        }

    async def _run(self) -> None:
        frame_interval = 1.0 / self.frame_source.fps
        frame_interval_ns = round(frame_interval * 1_000_000_000)
        next_tick = time.perf_counter()
        while True:
            async with self._current_lock():
                now_ns = time.perf_counter_ns()
                if self._runtime_loop_observed_ns is None:
                    advance_result = self.runtime.advance_to(now_ns)
                else:
                    observed_elapsed_ns = max(
                        0,
                        now_ns - self._runtime_loop_observed_ns,
                    )
                    accepted_elapsed_ns = min(
                        observed_elapsed_ns,
                        frame_interval_ns,
                    )
                    self._presentation_clock_dropped_ns += (
                        observed_elapsed_ns - accepted_elapsed_ns
                    )
                    advance_result = self.runtime.advance_elapsed_ns(
                        accepted_elapsed_ns
                    )
                self._runtime_loop_observed_ns = now_ns
                if advance_result.steps == 0 and self.command_inbox.pending_count:
                    self.runtime.step_tick()
                capture_render_state = getattr(
                    self.frame_source,
                    "capture_render_state",
                    None,
                )
                render_state = (
                    None
                    if capture_render_state is None
                    else capture_render_state()
                )
                captured_permission_signature = _permission_render_signature(
                    getattr(
                        render_state,
                        "permission_world",
                        None,
                    )
                )
            # Let command waiters observe their authoritative ack before the
            # synchronous cell compositor begins the presentation frame.
            await asyncio.sleep(0)
            candidate_renderer = getattr(
                self.frame_source,
                "render_captured_candidate_sync",
                None,
            )
            captured_renderer = getattr(
                self.frame_source,
                "encode_captured_frame_sync",
                None,
            )
            render_candidate = None
            if candidate_renderer is not None and render_state is not None:
                if self._render_executor is None:
                    self._render_executor = ThreadPoolExecutor(
                        max_workers=1,
                        thread_name_prefix="wizard-frame-render",
                    )
                render_candidate = await asyncio.get_running_loop().run_in_executor(
                    self._render_executor,
                    candidate_renderer,
                    render_state,
                    self.codec,
                )
                message = None
                frame = None
            elif captured_renderer is not None and render_state is not None:
                if self._render_executor is None:
                    self._render_executor = ThreadPoolExecutor(
                        max_workers=1,
                        thread_name_prefix="wizard-frame-render",
                    )
                message, frame = await asyncio.get_running_loop().run_in_executor(
                    self._render_executor,
                    captured_renderer,
                    render_state,
                    self.codec,
                )
            else:
                message, frame = await self.frame_source.next_encoded_frame(
                    self.codec,
                    advance=False,
                )
            async with self._current_lock():
                self.performance._apply_authoritative_permission_world(
                    self.frame_source.controller,
                    time.perf_counter_ns() // 1000,
                )
                current_permission_policy = getattr(
                    self.frame_source.controller,
                    "permission_world_render_policy",
                    None,
                )
                stale_permission = (
                    captured_permission_signature
                    != _permission_render_signature(current_permission_policy)
                )
                stale_state = (
                    render_candidate is not None
                    and render_candidate.authoritative_state_sha256
                    != canonical_sha256(self.frame_source.controller.current_state())
                )
                if stale_permission or stale_state:
                    self._force_keyframe = True
                    self._stale_render_discard_count += 1
                    next_tick = time.perf_counter()
                    continue
                if render_candidate is not None:
                    try:
                        message, frame = self.frame_source.commit_render_candidate(
                            render_candidate
                        )
                    except ValueError:
                        # Another owner path committed against this generation.
                        # Reject the candidate as a whole; never partially
                        # advance the encoder or presentation transaction.
                        self._force_keyframe = True
                        self._stale_render_discard_count += 1
                        next_tick = time.perf_counter()
                        continue
                if message is None or frame is None:
                    raise RuntimeError("render candidate committed without a transport frame")
                if self._force_keyframe:
                    forced = encode_keyframe(frame.cells, frame.frame_index)
                    message = forced.message
                    self._force_keyframe = False
                    self._forced_keyframe_count += 1
                    frame = dataclass_replace(
                        frame,
                        changed_cells=forced.changed_cells,
                        codec_tag=forced.tag,
                        encoded_size=forced.encoded_size,
                        is_keyframe=forced.is_keyframe,
                    )
                    if render_candidate is not None:
                        render_candidate = dataclass_replace(
                            render_candidate,
                            animation_truth=render_candidate.animation_truth.with_transport(
                                codec_tag=forced.tag,
                                encoded_size=forced.encoded_size,
                                changed_cells=forced.changed_cells,
                                is_keyframe=forced.is_keyframe,
                            ),
                        )
                self._latest_frame = frame
                self._source_hash_history.append(
                    {
                        "frame_index": frame.frame_index,
                        "hash": (
                            render_candidate.animation_truth.frame_fnv1a32
                            if render_candidate is not None
                            else frame_hash(frame.cells)
                        ),
                        "codec_tag": frame.codec_tag,
                        "changed_cells": frame.changed_cells,
                        "raw_size": frame.raw_size,
                    }
                )
                if render_candidate is not None:
                    self._animation_truth_trace.append(render_candidate.animation_truth)
            self._published_frames += 1
            self._published_at.append(time.perf_counter())
            self._publish(message)
            self._update_diagnostics()
            next_tick += frame_interval
            now = time.perf_counter()
            if next_tick < now:
                # Drop missed presentation deadlines instead of advancing simulation in a burst.
                next_tick = now + frame_interval
                self._schedule_overruns += 1
            await asyncio.sleep(max(0.0, next_tick - now))

    def _enqueue(
        self,
        envelope: CommandEnvelopeV1,
        command_type: str,
    ) -> tuple[CommandAckV1, Optional[asyncio.Event]]:
        self._command_types[envelope.command_id] = command_type
        waiter = asyncio.Event()
        self._command_waiters[envelope.command_id] = waiter
        ack = self.runtime.enqueue(envelope)
        if ack.disposition != "accepted":
            self._command_types.pop(envelope.command_id, None)
            self._command_waiters.pop(envelope.command_id, None)
            return ack, None
        return ack, waiter

    async def _await_command(
        self,
        command_id: str,
        ack: CommandAckV1,
        waiter: Optional[asyncio.Event],
    ) -> CommandResult:
        if waiter is None:
            return CommandResult(
                False,
                ack.message,
                self.frame_source.current_state().as_public_dict(),
            )
        timeout = max(2.0, 3.0 / self.frame_source.fps)
        try:
            await asyncio.wait_for(waiter.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return CommandResult(
                False,
                "runtime command timed out",
                self.frame_source.current_state().as_public_dict(),
            )
        finally:
            self._command_waiters.pop(command_id, None)
        result = self._command_results.pop(command_id, None)
        if result is not None:
            return result
        final_ack = self.command_inbox.ack_for(command_id) or ack
        return CommandResult(
            final_ack.disposition == "applied",
            final_ack.message,
            self.frame_source.current_state().as_public_dict(),
        )

    def _reduce_runtime_tick(
        self,
        state: WizardState,
        due: tuple[QueuedCommand, ...],
        target_tick: int,
        _dt: float,
    ) -> WizardState:
        controller = self.frame_source.controller
        controller.state = state
        reduced_command_ids = []
        for queued in due:
            envelope = queued.envelope
            command_type = self._command_types.pop(
                envelope.command_id,
                self._controller_command_type(envelope.kind),
            )
            result = controller.apply_command(
                WizardCommand(command_type, dict(envelope.payload))
            )
            self._command_results[envelope.command_id] = result
            if not result.ok:
                self.command_inbox.mark_rejected(
                    envelope.command_id,
                    target_tick,
                    "command_validation_failed",
                    result.message,
                )
            reduced_command_ids.append(envelope.command_id)

        # Reset reinitializes the controller. Rebase it onto the authoritative
        # runtime tick before taking the single simulation step.
        controller.state.simulation_tick = target_tick - 1
        controller.state.state_revision = target_tick - 1
        controller.state.time_seconds = (target_tick - 1) / AvatarRuntime.TICK_RATE
        controller.advance_tick()
        self.performance.apply(controller, time.perf_counter_ns() // 1000)
        resolve_animation = getattr(
            self.frame_source,
            "resolve_authoritative_animation_state",
            None,
        )
        if resolve_animation is not None:
            resolve_animation()
        authoritative_state = controller.current_state().as_public_dict()
        for command_id in reduced_command_ids:
            result = self._command_results[command_id]
            self._command_results[command_id] = CommandResult(
                result.ok,
                result.message,
                authoritative_state,
            )
            waiter = self._command_waiters.get(command_id)
            if waiter is not None:
                waiter.set()
        return controller.current_state()

    def _legacy_envelope(self, command: WizardCommand, sequence: int) -> CommandEnvelopeV1:
        kind = self._runtime_kind(command.type)
        priority = "system" if command.type == "reset" else "user"
        source_kind = "legacy_adapter"
        ttl_ms = 250 if kind == "control_intent" else None
        lease_id = None
        if kind == "control_intent":
            source_kind = str(command.payload.get("source_kind", "legacy_adapter"))
            if source_kind not in {"keyboard", "gamepad", "remote", "demo", "api", "system", "visual_signal", "legacy_adapter"}:
                source_kind = "legacy_adapter"
            priority = "demo" if source_kind == "demo" else "user"
            lease_id = str(command.payload.get("lease_id", "legacy-control"))
            ttl_ms = int(command.payload.get("ttl_ms", 250))
        return CommandEnvelopeV1(
            schema_version=1,
            command_id="legacy-{}-{}".format(sequence, uuid.uuid4().hex),
            source_id="legacy-http-ws",
            source_kind=source_kind,
            source_sequence=sequence,
            source_epoch=self.runtime_epoch,
            kind=kind,
            payload=command.payload,
            issued_tick=self.runtime.clock.simulation_tick,
            ttl_ms=ttl_ms,
            lease_id=lease_id,
            priority_class=priority,
        )

    @staticmethod
    def _runtime_kind(command_type: str) -> str:
        aliases = {
            "control": "control_intent",
            "pose": "diagnostic_pose",
            "prism_signal": "visual_signal",
            "mouth": "expression",
            "move_relative": "move",
            "walk_left": "move",
            "walk_right": "move",
            "walk_forward": "move",
            "walk_backward": "move",
            "return_to_center": "move_to",
        }
        kind = aliases.get(command_type, command_type)
        if kind not in {
            "control_intent", "action", "path", "move", "move_to", "circle",
            "figure_eight", "face", "gaze", "expression", "speak", "speech_stop",
            "stop", "reset",
            "diagnostic_pose", "visual_signal",
        }:
            raise ValueError("Unsupported command: {}".format(command_type))
        return kind

    @staticmethod
    def _controller_command_type(kind: str) -> str:
        return {
            "control_intent": "control",
            "move_to": "move",
            "diagnostic_pose": "pose",
            "visual_signal": "prism_signal",
        }.get(kind, kind)

    def _publish(self, message: bytes) -> None:
        for subscriber in list(self._subscribers):
            try:
                subscriber.queue.put_nowait(message)
            except asyncio.QueueFull:
                self._queue_drops += 1
                subscriber.dropped_frame_count += 1
                self._clear_queue(subscriber.queue)
                subscriber.resync_count += 1
                self._resync_count += 1
                # Recovery rejoins the one global publication stream. Do not
                # synthesize a subscriber-only encoding of the latest frame:
                # the next accepted frame is committed as a keyframe, traced
                # once, and offered unchanged to every recipient.
                self._force_keyframe = True

    def _current_lock(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock = asyncio.Lock()
            self._lock_loop = loop
        return self._lock

    def _update_diagnostics(self) -> None:
        # Exact retained replay hashing serializes the bounded evidence window.
        # Keep that operator-requested work entirely off the presentation loop.
        self.frame_source.diagnostics.extra.update(
            self.diagnostics_extra(include_replay_digest=False)
        )

    @staticmethod
    def _clear_queue(queue: asyncio.Queue[bytes]) -> None:
        while True:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                return
