from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import wave
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from .cache import CacheKey, canonical_identity_bytes, music_cache_key
from .media import AuthoringToolError, ToolCapability, inspect_tool, require_local_input


MUSIC_PIPELINE_VERSION = "deterministic-wav-music-v1"
DEFAULT_HOP_SAMPLES = 441
_SHA256_REF = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class FixedHopFeatures:
    sample_rate_hz: int
    channels: int
    sample_width_bytes: int
    duration_samples: int
    hop_samples: int
    rms_dbfs_centi: Tuple[int, ...]
    onset_strength_milli: Tuple[int, ...]
    onset_samples: Tuple[int, ...]
    tempo_bpm_milli: Optional[int]
    tempo_confidence_milli: int


@dataclass(frozen=True)
class LoudnessMeasurement:
    integrated_lufs_centi: int
    lra_lu_centi: int
    true_peak_dbtp_centi: int
    capability: ToolCapability


@dataclass(frozen=True)
class MusicAuthoringResult:
    music_score: Dict[str, object]
    cache_key: CacheKey
    ffmpeg: ToolCapability


def extract_fixed_hop_features(
    source: Union[str, Path],
    *,
    hop_samples: int = DEFAULT_HOP_SAMPLES,
) -> FixedHopFeatures:
    source_path = require_local_input(source)
    if not isinstance(hop_samples, int) or isinstance(hop_samples, bool) or hop_samples <= 0:
        raise AuthoringToolError("music_config_invalid", "hop_samples must be positive")
    try:
        audio = wave.open(str(source_path), "rb")
    except (wave.Error, OSError) as exc:
        raise AuthoringToolError("wav_invalid", "music baseline requires PCM WAV") from exc
    with audio:
        if audio.getcomptype() != "NONE":
            raise AuthoringToolError("wav_compression_unsupported", "WAV must contain PCM")
        sample_rate_hz = audio.getframerate()
        channels = audio.getnchannels()
        sample_width = audio.getsampwidth()
        duration_samples = audio.getnframes()
        if channels not in {1, 2} or sample_width not in {1, 2, 3, 4}:
            raise AuthoringToolError(
                "wav_format_unsupported", "WAV channel/sample width is unsupported"
            )
        if sample_rate_hz <= 0 or duration_samples <= 0:
            raise AuthoringToolError("wav_invalid", "WAV duration is invalid")
        peak = (1 << (sample_width * 8 - 1)) - 1
        rms_values = []  # type: List[int]
        rms_dbfs = []  # type: List[int]
        while True:
            frames = audio.readframes(hop_samples)
            if not frames:
                break
            mono = _decode_mono(frames, channels, sample_width)
            rms = math.isqrt(sum(sample * sample for sample in mono) // max(1, len(mono)))
            rms_values.append(rms)
            rms_dbfs.append(_dbfs_centi(rms, peak))

    onset_strength = []  # type: List[int]
    previous = 0
    for rms in rms_values:
        onset_strength.append(min(1000, max(0, rms - previous) * 1000 // max(1, peak)))
        previous = rms
    onset_indexes = _onset_indexes(onset_strength)
    onset_samples = tuple(index * hop_samples for index in onset_indexes)
    tempo_bpm_milli, confidence = _tempo_from_onsets(onset_samples, sample_rate_hz)
    return FixedHopFeatures(
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        sample_width_bytes=sample_width,
        duration_samples=duration_samples,
        hop_samples=hop_samples,
        rms_dbfs_centi=tuple(rms_dbfs),
        onset_strength_milli=tuple(onset_strength),
        onset_samples=onset_samples,
        tempo_bpm_milli=tempo_bpm_milli,
        tempo_confidence_milli=confidence,
    )


def measure_loudness(
    source: Union[str, Path],
    *,
    ffmpeg_executable: Optional[Union[str, Path]] = None,
) -> LoudnessMeasurement:
    source_path = require_local_input(source)
    capability = inspect_tool("ffmpeg", ffmpeg_executable)
    if not capability.available:
        raise AuthoringToolError(
            "tool_unavailable",
            "ffmpeg EBU R128 capability is unavailable",
            capability,
        )
    command = [
        str(capability.executable),
        "-nostdin",
        "-hide_banner",
        "-nostats",
        "-i",
        str(source_path),
        "-filter_complex",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise AuthoringToolError("loudness_failed", "FFmpeg loudness analysis failed") from exc
    if completed.returncode != 0:
        raise AuthoringToolError("loudness_failed", "FFmpeg loudness analysis failed")
    output = completed.stderr.decode("utf-8", errors="replace")
    integrated = re.findall(r"^\s*I:\s*(-?(?:\d+(?:\.\d+)?|inf))\s+LUFS", output, re.MULTILINE)
    ranges = re.findall(r"^\s*LRA:\s*(-?(?:\d+(?:\.\d+)?|inf))\s+LU", output, re.MULTILINE)
    peaks = re.findall(r"^\s*Peak:\s*(-?(?:\d+(?:\.\d+)?|inf))\s+dBFS", output, re.MULTILINE)
    if not integrated or not ranges or not peaks:
        raise AuthoringToolError("loudness_parse_failed", "FFmpeg EBU R128 summary is missing")
    return LoudnessMeasurement(
        integrated_lufs_centi=_decimal_centi(integrated[-1]),
        lra_lu_centi=_decimal_centi(ranges[-1]),
        true_peak_dbtp_centi=_decimal_centi(peaks[-1]),
        capability=capability,
    )


def build_music_score(
    source: Union[str, Path],
    *,
    media_id: str,
    media_sha256: str,
    hop_samples: int = DEFAULT_HOP_SAMPLES,
    ffmpeg_executable: Optional[Union[str, Path]] = None,
) -> MusicAuthoringResult:
    _require_sha256("media_sha256", media_sha256)
    if not isinstance(media_id, str) or not media_id.startswith("media:sha256:"):
        raise AuthoringToolError("media_id_invalid", "media_id is invalid")
    source_path = require_local_input(source)
    pcm_sha256 = _sha256_file(source_path)
    features = extract_fixed_hop_features(source_path, hop_samples=hop_samples)
    loudness = measure_loudness(source_path, ffmpeg_executable=ffmpeg_executable)
    assert loudness.capability.binary_sha256 is not None
    assert loudness.capability.version_sha256 is not None
    numerical_lock = {
        "python_integer_rms": True,
        "decimal_db_precision": 40,
        "onset_threshold_milli": 80,
        "tempo_max_deviation_milli": 100,
    }
    numerical_lock_sha256 = _sha256_ref(canonical_identity_bytes(numerical_lock))
    config = {
        "hop_samples": features.hop_samples,
        "sample_rate_hz": features.sample_rate_hz,
        "channels": features.channels,
        "sample_width_bytes": features.sample_width_bytes,
    }
    config_sha256 = _sha256_ref(canonical_identity_bytes(config))
    algorithm_sha256 = _sha256_ref(
        canonical_identity_bytes(
            {
                "pipeline": MUSIC_PIPELINE_VERSION,
                "feature_algorithm": "integer-rms-positive-delta-v1",
                "loudness_algorithm": "ffmpeg-ebur128-peak-v1",
            }
        )
    )
    key = music_cache_key(
        pcm_sha256=pcm_sha256,
        pipeline_version=MUSIC_PIPELINE_VERSION,
        numerical_lock_sha256=numerical_lock_sha256,
        fixed_hop_config=config,
        algorithm_sha256=algorithm_sha256,
        model_sha256=None,
        execution_policy="single-process-cpu-integer-v1",
    )
    beats = (
        [
            {"sample": sample, "confidence_milli": features.tempo_confidence_milli}
            for sample in features.onset_samples
        ]
        if features.tempo_bpm_milli is not None
        else []
    )
    tempo_regions = (
        [
            {
                "start_sample": 0,
                "end_sample": features.duration_samples,
                "bpm_milli": features.tempo_bpm_milli,
                "confidence_milli": features.tempo_confidence_milli,
            }
        ]
        if features.tempo_bpm_milli is not None
        else []
    )
    score = {
        "schema_version": 1,
        "media_id": media_id,
        "media_sha256": media_sha256,
        "pcm_sha256": pcm_sha256,
        "sample_rate_hz": features.sample_rate_hz,
        "duration_samples": features.duration_samples,
        "analysis": {
            "pipeline_version": MUSIC_PIPELINE_VERSION,
            "decoder_build_sha256": loudness.capability.binary_sha256,
            "config_sha256": config_sha256,
            "packages_sha256": algorithm_sha256,
            "model_sha256": None,
        },
        "beats": beats,
        "downbeats": [],
        "tempo_regions": tempo_regions,
        "meter_regions": [],
        "sections": [
            {
                "section_id": "sec-001",
                "start_sample": 0,
                "end_sample": features.duration_samples,
                "label": "unknown",
                "confidence_milli": 0,
            }
        ],
        "onsets": [
            {
                "sample": sample,
                "strength_milli": features.onset_strength_milli[
                    min(len(features.onset_strength_milli) - 1, sample // features.hop_samples)
                ],
            }
            for sample in features.onset_samples
        ],
        "loudness": {
            "integrated_lufs_centi": loudness.integrated_lufs_centi,
            "lra_lu_centi": loudness.lra_lu_centi,
            "true_peak_dbtp_centi": loudness.true_peak_dbtp_centi,
        },
        "envelopes": {
            "hop_samples": features.hop_samples,
            "rms_dbfs_centi": list(features.rms_dbfs_centi),
            "onset_strength_milli": list(features.onset_strength_milli),
            "bands_db_centi": [],
        },
    }
    score["music_score_id"] = "music:{}".format(
        _sha256_ref(_canonical_score_bytes(score)).split(":", 1)[1][:24]
    )
    score = {"schema_version": 1, "music_score_id": score.pop("music_score_id"), **score}
    return MusicAuthoringResult(music_score=score, cache_key=key, ffmpeg=loudness.capability)


def _decode_mono(data: bytes, channels: int, width: int) -> List[int]:
    frame_width = channels * width
    if len(data) % frame_width:
        raise AuthoringToolError("wav_invalid", "WAV frame data is truncated")
    result = []  # type: List[int]
    for frame_start in range(0, len(data), frame_width):
        total = 0
        for channel in range(channels):
            start = frame_start + channel * width
            raw = data[start : start + width]
            if width == 1:
                sample = raw[0] - 128
            else:
                sample = int.from_bytes(raw, "little", signed=True)
            total += sample
        result.append(total // channels)
    return result


def _dbfs_centi(rms: int, peak: int) -> int:
    if rms <= 0:
        return -12000
    with localcontext() as context:
        context.prec = 40
        value = Decimal(2000) * (Decimal(rms).log10() - Decimal(peak).log10())
        return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _onset_indexes(strengths: Sequence[int]) -> Tuple[int, ...]:
    indexes = []  # type: List[int]
    for index, strength in enumerate(strengths):
        previous = strengths[index - 1] if index else -1
        following = strengths[index + 1] if index + 1 < len(strengths) else -1
        if strength >= 80 and strength > previous and strength >= following:
            if not indexes or index - indexes[-1] >= 2:
                indexes.append(index)
    return tuple(indexes)


def _tempo_from_onsets(
    onset_samples: Sequence[int], sample_rate_hz: int
) -> Tuple[Optional[int], int]:
    if len(onset_samples) < 4:
        return None, 0
    intervals = sorted(
        onset_samples[index] - onset_samples[index - 1]
        for index in range(1, len(onset_samples))
    )
    median = intervals[len(intervals) // 2]
    if median <= 0:
        return None, 0
    maximum_deviation = max(abs(interval - median) for interval in intervals)
    deviation_milli = maximum_deviation * 1000 // median
    bpm_milli = (60_000 * sample_rate_hz) // median
    if not 30_000 <= bpm_milli <= 240_000 or deviation_milli > 100:
        return None, 0
    return bpm_milli, max(500, 1000 - deviation_milli * 5)


def _decimal_centi(value: str) -> int:
    if value in {"-inf", "inf", "+inf"}:
        raise AuthoringToolError("loudness_silence", "loudness is undefined for silence")
    return int((Decimal(value) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _require_sha256(name: str, value: object) -> None:
    if not isinstance(value, str) or _SHA256_REF.fullmatch(value) is None:
        raise AuthoringToolError("invalid_hash", "{} must be a SHA-256 reference".format(name))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _sha256_ref(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _canonical_score_bytes(value: Dict[str, object]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


__all__ = [
    "DEFAULT_HOP_SAMPLES",
    "FixedHopFeatures",
    "LoudnessMeasurement",
    "MUSIC_PIPELINE_VERSION",
    "MusicAuthoringResult",
    "build_music_score",
    "extract_fixed_hop_features",
    "measure_loudness",
]
