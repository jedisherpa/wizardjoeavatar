"""Bounded, serialized execution for score-authoring transactions."""

from __future__ import annotations

import asyncio
import contextlib
import functools
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, Mapping, Optional, TypeVar


DEFAULT_SCORE_JOB_CAPACITY = 4


class ScoreJobError(RuntimeError):
    """A stable, content-free score-lane failure."""

    def __init__(self, code: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(code)


class ScoreJobQueueFull(ScoreJobError):
    def __init__(self) -> None:
        super().__init__("score_job_queue_full")


class ScoreJobLaneStopped(ScoreJobError):
    def __init__(self) -> None:
        super().__init__("score_job_lane_stopped")


T = TypeVar("T")


@dataclass(frozen=True)
class _ScoreJob(Generic[T]):
    operation: Callable[[], Awaitable[T]]
    future: "asyncio.Future[T]"


class ScoreJobLane:
    """Run bounded score transactions serially without using the hub lock."""

    def __init__(
        self,
        *,
        capacity: int = DEFAULT_SCORE_JOB_CAPACITY,
    ) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        self.capacity = capacity
        self._queue: Optional["asyncio.Queue[_ScoreJob[Any]]"] = None
        self._task: Optional[asyncio.Task] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._outstanding = 0
        self._active = False
        self._submitted = 0
        self._completed = 0
        self._rejected = 0
        self._failed = 0
        self._cancelled = 0
        self._max_queue_depth = 0
        self._last_duration_ms = 0
        self._last_error_code: Optional[str] = None

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._queue = asyncio.Queue(maxsize=self.capacity)
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="wizard-score-authoring",
        )
        self._task = asyncio.create_task(
            self._run(),
            name="wizard-score-authoring",
        )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        executor = self._executor
        self._executor = None
        if executor is not None:
            await asyncio.to_thread(
                executor.shutdown,
                wait=True,
                cancel_futures=True,
            )
        self._queue = None

    async def submit(
        self,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        await self.start()
        queue = self._queue
        task = self._task
        if queue is None or task is None or task.done():
            raise ScoreJobLaneStopped()
        if self._outstanding >= self.capacity:
            self._rejected += 1
            raise ScoreJobQueueFull()

        future: "asyncio.Future[T]" = asyncio.get_running_loop().create_future()
        job = _ScoreJob(operation=operation, future=future)
        self._outstanding += 1
        self._submitted += 1
        try:
            queue.put_nowait(job)
        except asyncio.QueueFull as exc:
            self._outstanding -= 1
            self._rejected += 1
            raise ScoreJobQueueFull() from exc
        self._max_queue_depth = max(self._max_queue_depth, queue.qsize())
        return await future

    async def run_sync(
        self,
        operation: Callable[..., T],
        *args: object,
        **kwargs: object,
    ) -> T:
        executor = self._executor
        if executor is None:
            raise ScoreJobLaneStopped()
        call = functools.partial(operation, *args, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(executor, call)

    def diagnostics(self) -> Mapping[str, object]:
        queue = self._queue
        return {
            "capacity": self.capacity,
            "outstanding": self._outstanding,
            "queued": 0 if queue is None else queue.qsize(),
            "active": self._active,
            "submitted": self._submitted,
            "completed": self._completed,
            "rejected": self._rejected,
            "failed": self._failed,
            "cancelled": self._cancelled,
            "max_queue_depth": self._max_queue_depth,
            "last_duration_ms": self._last_duration_ms,
            "last_error_code": self._last_error_code,
        }

    async def _run(self) -> None:
        queue = self._queue
        assert queue is not None
        try:
            while True:
                job = await queue.get()
                started = time.perf_counter()
                self._active = True
                try:
                    if job.future.cancelled():
                        self._cancelled += 1
                        continue
                    try:
                        result = await job.operation()
                    except asyncio.CancelledError:
                        self._cancelled += 1
                        if not job.future.done():
                            job.future.set_exception(ScoreJobLaneStopped())
                        raise
                    except Exception as exc:
                        self._failed += 1
                        self._last_error_code = "score_job_failed"
                        if not job.future.done():
                            job.future.set_exception(exc)
                    else:
                        self._completed += 1
                        self._last_error_code = None
                        if not job.future.done():
                            job.future.set_result(result)
                finally:
                    self._last_duration_ms = max(
                        0,
                        round((time.perf_counter() - started) * 1000),
                    )
                    self._active = False
                    self._outstanding -= 1
                    queue.task_done()
        finally:
            while True:
                try:
                    pending = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if not pending.future.done():
                    pending.future.set_exception(ScoreJobLaneStopped())
                self._cancelled += 1
                self._outstanding -= 1
                queue.task_done()


__all__ = [
    "DEFAULT_SCORE_JOB_CAPACITY",
    "ScoreJobError",
    "ScoreJobLane",
    "ScoreJobLaneStopped",
    "ScoreJobQueueFull",
]
