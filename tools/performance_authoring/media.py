from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple, Union

from .cache import CacheKey, pcm_cache_key


CANONICAL_SAMPLE_RATE_HZ = 16_000
CANONICAL_CHANNELS = 1
CANONICAL_SAMPLE_FORMAT = "s16le"

_URI_PREFIX = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


class AuthoringToolError(RuntimeError):
    def __init__(self, code: str, message: str, capability: Optional["ToolCapability"] = None) -> None:
        super().__init__(message)
        self.code = code
        self.capability = capability


@dataclass(frozen=True)
class ToolCapability:
    tool: str
    available: bool
    executable: Optional[str]
    version_line: Optional[str]
    binary_sha256: Optional[str]
    version_sha256: Optional[str]
    reason_code: Optional[str]

    def to_mapping(self) -> Dict[str, object]:
        return {
            "tool": self.tool,
            "available": self.available,
            "executable": self.executable,
            "version_line": self.version_line,
            "binary_sha256": self.binary_sha256,
            "version_sha256": self.version_sha256,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class MediaProbe:
    source_sha256: str
    byte_length: int
    format_name: str
    mime_type: str
    duration_ms: int
    audio_stream_index: int
    codec_name: str
    sample_rate_hz: Optional[int]
    channels: Optional[int]
    ffprobe: ToolCapability

    def to_mapping(self) -> Dict[str, object]:
        return {
            "source_sha256": self.source_sha256,
            "byte_length": self.byte_length,
            "format_name": self.format_name,
            "mime_type": self.mime_type,
            "duration_ms": self.duration_ms,
            "audio_stream_index": self.audio_stream_index,
            "codec_name": self.codec_name,
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "ffprobe": self.ffprobe.to_mapping(),
        }


@dataclass(frozen=True)
class CanonicalPcmResult:
    source_sha256: str
    pcm_sha256: str
    byte_length: int
    sample_rate_hz: int
    channels: int
    sample_format: str
    duration_samples: int
    decoder_build_sha256: str
    decoder_arguments_sha256: str
    cache_key: CacheKey
    output_path: Path

    def portable_mapping(self) -> Dict[str, object]:
        return {
            "pcm_sha256": self.pcm_sha256,
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "sample_format": self.sample_format,
            "duration_samples": self.duration_samples,
            "decoder_build_sha256": self.decoder_build_sha256,
            "decoder_arguments_sha256": self.decoder_arguments_sha256,
        }


def inspect_tool(tool: str, executable: Optional[Union[str, Path]] = None) -> ToolCapability:
    candidate = str(executable) if executable is not None else shutil.which(tool)
    if not candidate:
        return ToolCapability(
            tool=tool,
            available=False,
            executable=None,
            version_line=None,
            binary_sha256=None,
            version_sha256=None,
            reason_code="tool_unavailable",
        )
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        located = shutil.which(str(path))
        if not located:
            return ToolCapability(
                tool=tool,
                available=False,
                executable=None,
                version_line=None,
                binary_sha256=None,
                version_sha256=None,
                reason_code="tool_unavailable",
            )
        path = Path(located)
    path = path.resolve()
    if not path.is_file() or not os.access(str(path), os.X_OK):
        return ToolCapability(
            tool=tool,
            available=False,
            executable=str(path),
            version_line=None,
            binary_sha256=None,
            version_sha256=None,
            reason_code="tool_not_executable",
        )
    try:
        completed = subprocess.run(
            [str(path), "-version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ToolCapability(
            tool=tool,
            available=False,
            executable=str(path),
            version_line=None,
            binary_sha256=None,
            version_sha256=None,
            reason_code="tool_version_failed",
        )
    version_bytes = completed.stdout
    if completed.returncode != 0 or not version_bytes:
        return ToolCapability(
            tool=tool,
            available=False,
            executable=str(path),
            version_line=None,
            binary_sha256=None,
            version_sha256=None,
            reason_code="tool_version_failed",
        )
    version_line = version_bytes.decode("utf-8", errors="replace").splitlines()[0]
    return ToolCapability(
        tool=tool,
        available=True,
        executable=str(path),
        version_line=version_line,
        binary_sha256=_sha256_file(path),
        version_sha256=_sha256_ref(version_bytes),
        reason_code=None,
    )


def authoring_capabilities(
    *,
    ffmpeg_executable: Optional[Union[str, Path]] = None,
    ffprobe_executable: Optional[Union[str, Path]] = None,
) -> Tuple[ToolCapability, ToolCapability]:
    return (
        inspect_tool("ffmpeg", ffmpeg_executable),
        inspect_tool("ffprobe", ffprobe_executable),
    )


def probe_media(
    source: Union[str, Path],
    *,
    ffprobe_executable: Optional[Union[str, Path]] = None,
) -> MediaProbe:
    source_path = require_local_input(source)
    capability = inspect_tool("ffprobe", ffprobe_executable)
    _require_capability(capability)
    command = [
        str(capability.executable),
        "-v",
        "error",
        "-show_entries",
        "format=duration,format_name,size:stream=index,codec_type,codec_name,sample_rate,channels",
        "-of",
        "json",
        str(source_path),
    ]
    completed = _run(command, "media_probe_failed")
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
        streams = payload["streams"]
        format_data = payload["format"]
        audio = next(stream for stream in streams if stream.get("codec_type") == "audio")
        duration_ms = _seconds_to_ms(format_data["duration"])
        format_name = str(format_data["format_name"]).split(",", 1)[0]
        codec_name = str(audio["codec_name"])
        stream_index = _strict_int(audio["index"], "audio stream index")
        sample_rate = _optional_positive_int(audio.get("sample_rate"))
        channels = _optional_positive_int(audio.get("channels"))
    except (KeyError, StopIteration, TypeError, ValueError, InvalidOperation) as exc:
        raise AuthoringToolError(
            "media_probe_invalid", "ffprobe returned incomplete audio metadata"
        ) from exc
    mime_type = mimetypes.guess_type(source_path.name)[0] or _mime_for_format(format_name)
    return MediaProbe(
        source_sha256=_sha256_file(source_path),
        byte_length=source_path.stat().st_size,
        format_name=format_name,
        mime_type=mime_type,
        duration_ms=duration_ms,
        audio_stream_index=stream_index,
        codec_name=codec_name,
        sample_rate_hz=sample_rate,
        channels=channels,
        ffprobe=capability,
    )


def canonicalize_pcm(
    source: Union[str, Path],
    output: Union[str, Path],
    *,
    sample_rate_hz: int = CANONICAL_SAMPLE_RATE_HZ,
    channels: int = CANONICAL_CHANNELS,
    ffmpeg_executable: Optional[Union[str, Path]] = None,
) -> CanonicalPcmResult:
    source_path = require_local_input(source)
    output_path = require_local_output(output)
    if source_path == output_path:
        raise AuthoringToolError("output_conflict", "PCM output must differ from source")
    if not isinstance(sample_rate_hz, int) or isinstance(sample_rate_hz, bool) or sample_rate_hz <= 0:
        raise AuthoringToolError("invalid_sample_rate", "sample rate must be positive")
    if not isinstance(channels, int) or isinstance(channels, bool) or channels not in {1, 2}:
        raise AuthoringToolError("invalid_channels", "canonical channels must be 1 or 2")
    capability = inspect_tool("ffmpeg", ffmpeg_executable)
    _require_capability(capability)
    assert capability.binary_sha256 is not None
    assert capability.version_sha256 is not None

    decode_arguments = (
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-map",
        "0:a:0",
        "-vn",
        "-map_metadata",
        "-1",
        "-fflags",
        "+bitexact",
        "-flags:a",
        "+bitexact",
        "-ar",
        str(sample_rate_hz),
        "-ac",
        str(channels),
        "-c:a",
        "pcm_s16le",
        "-f",
        "wav",
    )
    source_sha256 = _sha256_file(source_path)
    cache_key = pcm_cache_key(
        source_sha256=source_sha256,
        ffmpeg_binary_sha256=capability.binary_sha256,
        ffmpeg_version_sha256=capability.version_sha256,
        arguments=decode_arguments,
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        sample_format=CANONICAL_SAMPLE_FORMAT,
        resampler_config="ffmpeg-default-bitexact-v1",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix=".canonical-pcm-", suffix=".wav", dir=str(output_path.parent), delete=False
    )
    temporary_path = Path(handle.name)
    handle.close()
    command = [
        str(capability.executable),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source_path),
        *decode_arguments[4:],
        "-y",
        str(temporary_path),
    ]
    try:
        _run(command, "decode_failed")
        with wave.open(str(temporary_path), "rb") as pcm:
            actual_rate = pcm.getframerate()
            actual_channels = pcm.getnchannels()
            sample_width = pcm.getsampwidth()
            duration_samples = pcm.getnframes()
        if (actual_rate, actual_channels, sample_width) != (sample_rate_hz, channels, 2):
            raise AuthoringToolError(
                "pcm_mismatch", "decoded WAV does not match canonical PCM policy"
            )
        os.replace(str(temporary_path), str(output_path))
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass

    return CanonicalPcmResult(
        source_sha256=source_sha256,
        pcm_sha256=_sha256_file(output_path),
        byte_length=output_path.stat().st_size,
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        sample_format=CANONICAL_SAMPLE_FORMAT,
        duration_samples=duration_samples,
        decoder_build_sha256=capability.binary_sha256,
        decoder_arguments_sha256=_sha256_ref(
            json.dumps(list(decode_arguments), separators=(",", ":")).encode("utf-8")
        ),
        cache_key=cache_key,
        output_path=output_path,
    )


def build_media_asset(
    probe: MediaProbe,
    *,
    storage_ref: str,
    title: str,
    media_kind: str,
    canonical_pcm: Optional[CanonicalPcmResult] = None,
) -> Dict[str, object]:
    if not isinstance(storage_ref, str) or not storage_ref or "/" in storage_ref or "\\" in storage_ref:
        raise AuthoringToolError("storage_ref_invalid", "storage_ref must be opaque")
    if media_kind not in {"audiobook", "music", "video", "speech", "unknown"}:
        raise AuthoringToolError("media_kind_invalid", "media_kind is unsupported")
    source_hex = probe.source_sha256.split(":", 1)[1]
    return {
        "schema_version": 1,
        "media_id": "media:sha256:{}".format(source_hex),
        "identity": {
            "source_sha256": probe.source_sha256,
            "byte_length": probe.byte_length,
            "mime_type": probe.mime_type,
            "duration_ms": probe.duration_ms,
            "media_kind": media_kind,
        },
        "storage_ref": storage_ref,
        "display": {
            "title": title,
            "creator": None,
            "collection": None,
            "chapter_id": None,
        },
        "canonical_pcm": canonical_pcm.portable_mapping() if canonical_pcm else None,
        "external": {"canonical_url": None, "url_source": None},
        "status": {
            "transcript": "missing",
            "analysis": "missing",
            "performance": "missing",
        },
    }


def require_local_input(value: Union[str, Path]) -> Path:
    path = _local_path(value, "source")
    if not path.is_file():
        raise AuthoringToolError("source_missing", "local source file is missing")
    return path


def require_local_output(value: Union[str, Path]) -> Path:
    return _local_path(value, "output")


def _local_path(value: Union[str, Path], name: str) -> Path:
    raw = str(value)
    if not raw or raw == "-" or "://" in raw or _URI_PREFIX.match(raw):
        raise AuthoringToolError(
            "network_forbidden", "{} must be a local filesystem path".format(name)
        )
    return Path(raw).expanduser().resolve()


def _require_capability(capability: ToolCapability) -> None:
    if not capability.available:
        raise AuthoringToolError(
            "tool_unavailable",
            "{} is unavailable: {}".format(capability.tool, capability.reason_code),
            capability,
        )


def _run(command: Sequence[str], error_code: str) -> subprocess.CompletedProcess:
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise AuthoringToolError(error_code, "local authoring subprocess failed") from exc
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise AuthoringToolError(error_code, message[-1000:] or "local tool failed")
    return completed


def _seconds_to_ms(value: object) -> int:
    milliseconds = (Decimal(str(value)) * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    result = int(milliseconds)
    if result <= 0:
        raise ValueError("duration must be positive")
    return result


def _strict_int(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(name)
    return int(str(value))


def _optional_positive_int(value: object) -> Optional[int]:
    if value in (None, ""):
        return None
    result = _strict_int(value, "positive integer")
    return result if result > 0 else None


def _mime_for_format(format_name: str) -> str:
    return {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "flac": "audio/flac",
        "ogg": "audio/ogg",
        "mov": "video/quicktime",
        "matroska": "video/x-matroska",
    }.get(format_name, "application/octet-stream")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _sha256_ref(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


__all__ = [
    "AuthoringToolError",
    "CANONICAL_CHANNELS",
    "CANONICAL_SAMPLE_FORMAT",
    "CANONICAL_SAMPLE_RATE_HZ",
    "CanonicalPcmResult",
    "MediaProbe",
    "ToolCapability",
    "authoring_capabilities",
    "build_media_asset",
    "canonicalize_pcm",
    "inspect_tool",
    "probe_media",
    "require_local_input",
    "require_local_output",
]
