#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import math
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from wizard_avatar.frame_hash import frame_hash
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import PROFILES
from wizard_avatar.protocol import encode_frame


PHASES = (
    "simulation",
    "cell_render",
    "frame_encode",
    "frame_hash",
    "queue_wait",
    "renderer_pipeline",
    "end_to_end",
)


def _percentile(values: list[float], percentile: int) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(len(ordered) * percentile / 100))
    return ordered[rank - 1]


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "count": len(values),
        "mean": round(statistics.fmean(values), 6),
        "p50": round(_percentile(values, 50), 6),
        "p95": round(_percentile(values, 95), 6),
        "p99": round(_percentile(values, 99), 6),
        "max": round(max(values), 6),
    }


async def _measure(args: argparse.Namespace) -> dict[str, object]:
    profile = PROFILES[args.profile]
    source = ProceduralWizardFrameSource(
        cols=profile.cols,
        rows=profile.rows,
        fps=args.fps,
    )
    samples = {phase: [] for phase in PHASES}
    previous = None
    hashes = []

    for index in range(args.warmup + args.frames):
        started = time.perf_counter_ns()
        source.advance_simulation(1.0 / source.fps)
        simulated = time.perf_counter_ns()

        frame = source.render_current_frame()
        rendered = time.perf_counter_ns()

        encoded = encode_frame(frame.cells, previous, frame.frame_index)
        previous = encoded.shown_frame
        encoded_at = time.perf_counter_ns()

        digest = frame_hash(frame.cells)
        hashed = time.perf_counter_ns()

        queue = asyncio.Queue(maxsize=1)
        queue.put_nowait(encoded.message)
        await asyncio.sleep(0)
        queue.get_nowait()
        queued = time.perf_counter_ns()
        source.frame_index += 1

        if index < args.warmup:
            continue

        hashes.append(digest)
        durations = {
            "simulation": simulated - started,
            "cell_render": rendered - simulated,
            "frame_encode": encoded_at - rendered,
            "frame_hash": hashed - encoded_at,
            "queue_wait": queued - hashed,
            "renderer_pipeline": hashed - started,
            "end_to_end": queued - started,
        }
        for phase, duration_ns in durations.items():
            samples[phase].append(duration_ns / 1_000_000)

    summaries = {phase: _summary(samples[phase]) for phase in PHASES}
    reference_profile = source.fps == 24 and source.cols == 240 and source.rows == 135
    minimum_frames = 30
    gate = {
        "profile": "reference_24fps_240x135",
        "p95_limit_ms": 33.3,
        "p99_limit_ms": 41.7,
        "minimum_frames": minimum_frames,
        "applicable": reference_profile and args.frames >= minimum_frames,
    }
    gate["passed"] = (
        summaries["renderer_pipeline"]["p95"] <= gate["p95_limit_ms"]
        and summaries["renderer_pipeline"]["p99"] <= gate["p99_limit_ms"]
        if gate["applicable"]
        else None
    )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": " ".join(sys.argv),
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "os": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or None,
        },
        "render_profile": {
            "name": args.profile,
            "cols": source.cols,
            "rows": source.rows,
            "fps": source.fps,
            "codec": "adaptive",
            "warmup_frames": args.warmup,
            "measured_frames": args.frames,
        },
        "phase_ms": summaries,
        "renderer_gate": gate,
        "sampled_frame_hashes": hashes,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure real Wizard stream render phases without asserting scheduler correctness."
    )
    parser.add_argument("--profile", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--fps", type=float, default=24.0)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.fps <= 0 or args.warmup < 0 or args.frames <= 0:
        raise SystemExit("fps and frames must be positive; warmup must be non-negative")
    report = asyncio.run(_measure(args))
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
