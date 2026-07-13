from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass, field
from itertools import count
from collections import deque
from typing import Optional, Set

from .frame_hash import frame_hash
from .frame_source import ProceduralWizardFrameSource
from .models import CommandResult, WizardCellFrame, WizardCommand
from .protocol import encode_keyframe


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
        async with self._current_lock():
            return await self.frame_source.apply_command(command)

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
        }

    def source_hash_history(self) -> list[dict]:
        return list(self._source_hash_history)

    async def _run(self) -> None:
        frame_interval = 1.0 / self.frame_source.fps
        next_tick = time.perf_counter()
        while True:
            async with self._current_lock():
                self.frame_source.advance_simulation(frame_interval)
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
