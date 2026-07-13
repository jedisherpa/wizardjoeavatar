from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from dataclasses import dataclass, field
from itertools import count
from collections import deque
from typing import Dict, Optional, Set

from .commanding import CommandAckV1, CommandEnvelopeV1, OrderedCommandInbox, QueuedCommand
from .frame_hash import frame_hash
from .frame_source import ProceduralWizardFrameSource
from .models import CommandResult, WizardCellFrame, WizardCommand, WizardState
from .protocol import encode_keyframe
from .runtime import AvatarRuntime, ReplayLog


_subscriber_ids = count(1)


@dataclass(eq=False)
class WizardSubscriber:
    queue: asyncio.Queue[bytes]
    subscriber_id: int = field(default_factory=lambda: next(_subscriber_ids))
    dropped_frame_count: int = 0
    resync_count: int = 0


class WizardFrameHub:
    def __init__(self, frame_source: ProceduralWizardFrameSource, codec: str = "adaptive") -> None:
        self.frame_source = frame_source
        self.codec = codec
        self.runtime_epoch = "wizard-{}".format(uuid.uuid4().hex)
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
        self._lock: Optional[asyncio.Lock] = None
        self._lock_loop: Optional[asyncio.AbstractEventLoop] = None
        self._latest_frame: Optional[WizardCellFrame] = None
        self._force_keyframe = False
        self._started_at = 0.0
        self._published_frames = 0
        self._queue_drops = 0
        self._resync_count = 0
        self._forced_keyframe_count = 0
        self._schedule_overruns = 0
        self._source_hash_history = deque(maxlen=240)

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._started_at = time.perf_counter()
            self.runtime.advance_to(time.perf_counter_ns())
            self._task = asyncio.create_task(self._run(), name="wizard-frame-hub")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def subscribe(self, max_queue_size: int = 8) -> WizardSubscriber:
        await self.start()
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
            frame = self._latest_frame
        if frame is None:
            return
        self._clear_queue(subscriber.queue)
        subscriber.resync_count += 1
        self._resync_count += 1
        subscriber.queue.put_nowait(encode_keyframe(frame.cells, frame.frame_index).message)
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

    def diagnostics_extra(self) -> dict:
        elapsed = max(0.001, time.perf_counter() - self._started_at) if self._started_at else 0.001
        return {
            "subscriber_count": len(self._subscribers),
            "hub_actual_fps": self._published_frames / elapsed,
            "hub_queue_drops": self._queue_drops,
            "resync_count": self._resync_count,
            "slow_subscriber_count": sum(1 for subscriber in self._subscribers if subscriber.dropped_frame_count),
            "forced_keyframe_count": self._forced_keyframe_count,
            "schedule_overruns": self._schedule_overruns,
            "source_hash_history_count": len(self._source_hash_history),
            "runtime_epoch": self.runtime_epoch,
            "simulation_tick": self.runtime.clock.simulation_tick,
            "state_revision": self.runtime.clock.state_revision,
            "runtime_state_hash": self.runtime.current_snapshot().state_hash,
            "ordered_command_pending": self.command_inbox.pending_count,
            "replay_record_count": self.replay_log.record_count,
            "replay_sha256": self.replay_log.sha256(),
        }

    def source_hash_history(self) -> list[dict]:
        return list(self._source_hash_history)

    async def _run(self) -> None:
        frame_interval = 1.0 / self.frame_source.fps
        next_tick = time.perf_counter()
        while True:
            async with self._current_lock():
                advance_result = self.runtime.advance_to(time.perf_counter_ns())
                if advance_result.steps == 0 and self.command_inbox.pending_count:
                    self.runtime.step_tick()
            # Let command waiters observe their authoritative ack before the
            # synchronous cell compositor begins the presentation frame.
            await asyncio.sleep(0.001)
            async with self._current_lock():
                message, frame = await self.frame_source.next_encoded_frame(
                    self.codec,
                    advance=False,
                )
                self._latest_frame = frame
                self._source_hash_history.append(
                    {
                        "frame_index": frame.frame_index,
                        "hash": frame_hash(frame.cells),
                        "codec_tag": frame.codec_tag,
                        "changed_cells": frame.changed_cells,
                        "raw_size": frame.raw_size,
                    }
                )
                if self._force_keyframe:
                    message = encode_keyframe(frame.cells, frame.frame_index).message
                    self._force_keyframe = False
                    self._forced_keyframe_count += 1
            self._published_frames += 1
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
            return CommandResult(
                result.ok,
                result.message,
                self.frame_source.current_state().as_public_dict(),
            )
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
            waiter = self._command_waiters.get(envelope.command_id)
            if waiter is not None:
                waiter.set()

        # Reset reinitializes the controller. Rebase it onto the authoritative
        # runtime tick before taking the single simulation step.
        controller.state.simulation_tick = target_tick - 1
        controller.state.state_revision = target_tick - 1
        controller.state.time_seconds = (target_tick - 1) / AvatarRuntime.TICK_RATE
        controller.advance_tick()
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
            "speech_stop": "stop",
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
            "figure_eight", "face", "expression", "speak", "stop", "reset",
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
                if self._latest_frame is not None:
                    subscriber.queue.put_nowait(
                        encode_keyframe(self._latest_frame.cells, self._latest_frame.frame_index).message
                    )

    def _current_lock(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock = asyncio.Lock()
            self._lock_loop = loop
        return self._lock

    def _update_diagnostics(self) -> None:
        self.frame_source.diagnostics.extra.update(self.diagnostics_extra())

    @staticmethod
    def _clear_queue(queue: asyncio.Queue[bytes]) -> None:
        while True:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                return
