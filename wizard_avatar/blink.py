from __future__ import annotations


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
