from __future__ import annotations


class BlinkScheduler:
    SIMULATION_HZ = 60
    MIN_OPEN_TICKS = 150
    MAX_OPEN_TICKS = 390
    # Eight to ten simulation ticks keeps closures inside the 100-200 ms
    # acting contract while guaranteeing three to four visible samples at the
    # 24 FPS presentation cadence. Six ticks could alias down to two frames.
    MIN_CLOSED_TICKS = 8
    MAX_CLOSED_TICKS = 10

    def __init__(self, seed: int = 17) -> None:
        self.seed = seed & 0xFFFFFFFF
        self.reset()

    def reset(self) -> None:
        self._random_state = self.seed
        self._closed = False
        self._last_open_ticks = 0
        self._ticks_remaining = self._next_open_ticks()

    @property
    def phase(self) -> float:
        return 1.0 if self._closed else 0.0

    def advance_tick(self) -> float:
        self._ticks_remaining -= 1
        if self._ticks_remaining == 0:
            if self._closed:
                self._closed = False
                self._ticks_remaining = self._next_open_ticks()
            else:
                self._closed = True
                self._ticks_remaining = self._next_closed_ticks()
        return self.phase

    def _next_random(self) -> int:
        self._random_state = (
            1664525 * self._random_state + 1013904223
        ) & 0xFFFFFFFF
        return self._random_state

    def _next_open_ticks(self) -> int:
        span = self.MAX_OPEN_TICKS - self.MIN_OPEN_TICKS + 1
        ticks = self.MIN_OPEN_TICKS + self._next_random() % span
        if ticks == self._last_open_ticks:
            ticks = self.MIN_OPEN_TICKS + (ticks - self.MIN_OPEN_TICKS + 1) % span
        self._last_open_ticks = ticks
        return ticks

    def _next_closed_ticks(self) -> int:
        span = self.MAX_CLOSED_TICKS - self.MIN_CLOSED_TICKS + 1
        return self.MIN_CLOSED_TICKS + self._next_random() % span


def blink_state(time_seconds: float, seed: int = 17) -> str:
    interval = 3.0 + (seed % 5) * 0.67
    phase = time_seconds % interval
    duration = 0.16
    if phase > duration:
        return "open"
    section = phase / duration
    if section < 0.2:
        return "open"
    if section < 0.4:
        return "half_closed"
    if section < 0.7:
        return "closed"
    if section < 0.9:
        return "half_closed"
    return "open"


def blink_phase(time_seconds: float, seed: int = 17) -> float:
    interval = 3.0 + (seed % 5) * 0.67
    phase = time_seconds % interval
    return min(1.0, phase / 0.16)
