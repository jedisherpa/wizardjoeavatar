from __future__ import annotations

import bisect
import contextlib
import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Dict, Iterable, Iterator, Mapping, Optional, Sequence, Tuple, Union


SCORE_SCHEMA_VERSION = 1
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
PHASE_ORDER = ("anticipation", "stroke", "hold", "release", "settle")


class ScoreValidationError(ValueError):
    """Stable, content-free failure raised by score runtime boundaries."""

    def __init__(self, code: str, message: str, path: str = "$") -> None:
        super().__init__(message)
        self.code = code
        self.path = path


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        frozen: Dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ScoreValidationError("invalid_type", "object keys must be strings")
            frozen[key] = _freeze(item)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, float):
        raise ScoreValidationError("non_integer_identity_value", "score artifacts cannot contain floats")
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) > 9007199254740991:
        raise ScoreValidationError("non_integer_identity_value", "score integer exceeds the canonical range")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ScoreValidationError("invalid_type", "unsupported score value type")


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        _thaw(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_ref(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _pairs_without_duplicates(pairs: Sequence[Tuple[str, object]]) -> Mapping[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ScoreValidationError("duplicate_json_key", "duplicate JSON object key")
        result[key] = value
    return result


def _require_mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ScoreValidationError("invalid_type", "expected an object", path)
    return value  # type: ignore[return-value]


def _require_id(value: object, path: str) -> str:
    if not isinstance(value, str) or ID_PATTERN.fullmatch(value) is None:
        raise ScoreValidationError("invalid_id", "expected a stable identifier", path)
    return value


def _require_sha256(value: object, path: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise ScoreValidationError("invalid_hash", "expected a sha256 reference", path)
    return value


def _require_int(value: object, path: str, minimum: int = 0) -> int:
    if not _is_int(value) or int(value) < minimum:
        raise ScoreValidationError("invalid_type", "expected a bounded integer", path)
    return int(value)


@dataclass(frozen=True)
class ScoreCue:
    cue_id: str
    start_ms: int
    end_ms: int
    intent: str
    priority: int
    owned_channels: Tuple[str, ...]
    phase_ranges: Mapping[str, Tuple[int, int]]
    data: Mapping[str, object] = field(repr=False, compare=False)

    @classmethod
    def from_mapping(cls, value: Mapping[str, object], path: str = "$.cue") -> "ScoreCue":
        cue_id = _require_id(value.get("cue_id"), path + ".cue_id")
        start_ms = _require_int(value.get("start_ms"), path + ".start_ms")
        end_ms = _require_int(value.get("end_ms"), path + ".end_ms")
        if end_ms <= start_ms:
            raise ScoreValidationError("range_invalid", "cue range must be non-empty", path)

        intent_value = value.get("intent", "")
        if not isinstance(intent_value, str):
            raise ScoreValidationError("invalid_type", "cue intent must be a string", path + ".intent")
        priority = _require_int(value.get("priority", 0), path + ".priority", minimum=0)

        channels_value = value.get("owned_channels", value.get("channel_ownership", ()))
        if not isinstance(channels_value, (list, tuple)):
            raise ScoreValidationError("invalid_type", "owned_channels must be an array", path)
        channels = []
        for index, channel in enumerate(channels_value):
            if not isinstance(channel, str) or not channel:
                raise ScoreValidationError("invalid_type", "channel names must be non-empty strings", path)
            if channel in channels:
                raise ScoreValidationError("invalid_type", "owned_channels must be unique", path)
            channels.append(channel)

        phase_value = value.get("phase_ranges", {})
        phase_mapping = _require_mapping(phase_value, path + ".phase_ranges")
        unknown_phases = set(phase_mapping) - set(PHASE_ORDER)
        if unknown_phases:
            raise ScoreValidationError("invalid_enum", "unsupported phrase phase", path + ".phase_ranges")
        phases: Dict[str, Tuple[int, int]] = {}
        last_end: Optional[int] = None
        for name in PHASE_ORDER:
            if name not in phase_mapping:
                continue
            raw_range = phase_mapping[name]
            if not isinstance(raw_range, (list, tuple)) or len(raw_range) != 2:
                raise ScoreValidationError("range_invalid", "phase range requires two integers", path)
            phase_start = _require_int(raw_range[0], path + ".phase_ranges." + name)
            phase_end = _require_int(raw_range[1], path + ".phase_ranges." + name)
            if phase_start < start_ms or phase_end > end_ms or phase_end <= phase_start:
                raise ScoreValidationError("range_invalid", "phase lies outside cue", path)
            if last_end is not None and phase_start != last_end:
                raise ScoreValidationError("range_invalid", "phrase phases must be contiguous", path)
            phases[name] = (phase_start, phase_end)
            last_end = phase_end
        if phases:
            first = next(iter(phases.values()))
            if first[0] != start_ms or last_end != end_ms:
                raise ScoreValidationError("range_invalid", "phrase phases must cover the cue", path)

        return cls(
            cue_id=cue_id,
            start_ms=start_ms,
            end_ms=end_ms,
            intent=intent_value,
            priority=priority,
            owned_channels=tuple(channels),
            phase_ranges=MappingProxyType(phases),
            data=_freeze(value),  # type: ignore[arg-type]
        )

    def active_at(self, media_time_ms: int) -> bool:
        return self.start_ms <= media_time_ms < self.end_ms

    def phase_at(self, media_time_ms: int) -> Optional[str]:
        if not self.active_at(media_time_ms):
            return None
        for name in PHASE_ORDER:
            phase_range = self.phase_ranges.get(name)
            if phase_range is not None and phase_range[0] <= media_time_ms < phase_range[1]:
                return name
        return "active"

    def get(self, key: str, default: object = None) -> object:
        return self.data.get(key, default)

    def to_dict(self) -> Mapping[str, object]:
        return _thaw(self.data)  # type: ignore[return-value]


@dataclass(frozen=True)
class _IntervalNode:
    center: int
    crossing_by_start: Tuple[ScoreCue, ...]
    crossing_by_end: Tuple[ScoreCue, ...]
    left: Optional["_IntervalNode"]
    right: Optional["_IntervalNode"]


def _build_interval_node(cues: Sequence[ScoreCue]) -> Optional[_IntervalNode]:
    if not cues:
        return None
    starts = sorted(cue.start_ms for cue in cues)
    center = starts[len(starts) // 2]
    left: list[ScoreCue] = []
    right: list[ScoreCue] = []
    crossing: list[ScoreCue] = []
    for cue in cues:
        if cue.end_ms <= center:
            left.append(cue)
        elif cue.start_ms > center:
            right.append(cue)
        else:
            crossing.append(cue)
    return _IntervalNode(
        center=center,
        crossing_by_start=tuple(sorted(crossing, key=lambda cue: (cue.start_ms, cue.end_ms, cue.cue_id))),
        crossing_by_end=tuple(sorted(crossing, key=lambda cue: (-cue.end_ms, cue.start_ms, cue.cue_id))),
        left=_build_interval_node(left),
        right=_build_interval_node(right),
    )


def _query_interval_node(node: Optional[_IntervalNode], media_time_ms: int, found: list[ScoreCue]) -> None:
    if node is None:
        return
    if media_time_ms < node.center:
        for cue in node.crossing_by_start:
            if cue.start_ms > media_time_ms:
                break
            if media_time_ms < cue.end_ms:
                found.append(cue)
        _query_interval_node(node.left, media_time_ms, found)
        return
    for cue in node.crossing_by_end:
        if cue.end_ms <= media_time_ms:
            break
        if cue.start_ms <= media_time_ms:
            found.append(cue)
    _query_interval_node(node.right, media_time_ms, found)


@dataclass(frozen=True)
class TrackIntervalIndex:
    """Immutable half-open interval index for one compiled score track."""

    cues: Tuple[ScoreCue, ...]
    exclusive: bool
    _starts: Tuple[int, ...] = field(repr=False)
    _overlay_root: Optional[_IntervalNode] = field(repr=False, default=None)

    def __init__(self, cues: Iterable[ScoreCue], exclusive: bool = False) -> None:
        ordered = tuple(sorted(cues, key=lambda cue: (cue.start_ms, cue.end_ms, cue.cue_id)))
        if len({cue.cue_id for cue in ordered}) != len(ordered):
            raise ScoreValidationError("invalid_id", "cue IDs must be unique within a track")
        if exclusive:
            for previous, current in zip(ordered, ordered[1:]):
                if current.start_ms < previous.end_ms:
                    raise ScoreValidationError("exclusive_overlap", "exclusive cues overlap")
        object.__setattr__(self, "cues", ordered)
        object.__setattr__(self, "exclusive", bool(exclusive))
        object.__setattr__(self, "_starts", tuple(cue.start_ms for cue in ordered))
        object.__setattr__(self, "_overlay_root", None if exclusive else _build_interval_node(ordered))

    def query(self, media_time_ms: int) -> Tuple[ScoreCue, ...]:
        if not _is_int(media_time_ms) or media_time_ms < 0:
            raise ScoreValidationError("time_out_of_bounds", "media time must be a non-negative integer")
        if self.exclusive:
            index = bisect.bisect_right(self._starts, media_time_ms) - 1
            if index < 0:
                return ()
            cue = self.cues[index]
            return (cue,) if cue.active_at(media_time_ms) else ()
        found: list[ScoreCue] = []
        _query_interval_node(self._overlay_root, media_time_ms, found)
        return tuple(sorted(found, key=lambda cue: (-cue.priority, cue.start_ms, cue.cue_id)))

    def previous(self, media_time_ms: int) -> Optional[ScoreCue]:
        index = bisect.bisect_right(self._starts, media_time_ms) - 1
        return self.cues[index] if index >= 0 else None


@dataclass(frozen=True)
class PerformanceTrack:
    track_id: str
    kind: str
    exclusive: bool
    max_active: int
    gap_policy: str
    index: TrackIntervalIndex
    data: Mapping[str, object] = field(repr=False, compare=False)

    @classmethod
    def from_mapping(cls, value: Mapping[str, object], path: str) -> "PerformanceTrack":
        track_id = _require_id(value.get("track_id"), path + ".track_id")
        kind = value.get("kind")
        if not isinstance(kind, str) or not kind:
            raise ScoreValidationError("invalid_type", "track kind must be a string", path + ".kind")
        exclusive = value.get("exclusive")
        if not isinstance(exclusive, bool):
            raise ScoreValidationError("invalid_type", "track exclusive must be a boolean", path)
        max_active = _require_int(value.get("max_active", 1), path + ".max_active", minimum=1)
        gap_policy = value.get("gap_policy", "clear")
        if gap_policy not in {"clear", "hold", "neutral", "characterful_neutral", "still", "none"}:
            raise ScoreValidationError("invalid_enum", "unsupported track gap policy", path)
        raw_cues = value.get("cues")
        if not isinstance(raw_cues, (list, tuple)):
            raise ScoreValidationError("invalid_type", "track cues must be an array", path + ".cues")
        cues = tuple(
            ScoreCue.from_mapping(_require_mapping(cue, path + ".cues[{}]".format(index)), path + ".cues[{}]".format(index))
            for index, cue in enumerate(raw_cues)
        )
        if exclusive and max_active != 1:
            raise ScoreValidationError("invalid_type", "exclusive tracks require max_active 1", path)
        interval_index = TrackIntervalIndex(cues, exclusive=exclusive)
        if not exclusive:
            for boundary in sorted({cue.start_ms for cue in cues} | {cue.end_ms for cue in cues}):
                active = interval_index.query(boundary)
                if len(active) > max_active:
                    raise ScoreValidationError("exclusive_overlap", "track exceeds max_active", path)
        return cls(
            track_id=track_id,
            kind=kind,
            exclusive=exclusive,
            max_active=max_active,
            gap_policy=gap_policy,
            index=interval_index,
            data=_freeze(value),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class PerformanceScore:
    schema_version: int
    score_id: str
    revision: int
    duration_ms: int
    media_id: Optional[str]
    media_sha256: Optional[str]
    tracks: Tuple[PerformanceTrack, ...]
    artifact_sha256: str
    document: Mapping[str, object] = field(repr=False, compare=False)

    def track(self, track_id: str) -> PerformanceTrack:
        for track in self.tracks:
            if track.track_id == track_id:
                return track
        raise KeyError(track_id)

    def to_dict(self) -> Mapping[str, object]:
        return _thaw(self.document)  # type: ignore[return-value]


@dataclass(frozen=True)
class CompiledPerformanceScore(PerformanceScore):
    compiled_score_id: str = ""
    performance_score_sha256: str = ""
    character_id: str = ""
    package_digest: str = ""
    runtime_api_version: int = 0


ContractValidator = Callable[[str, Mapping[str, object]], None]


class CompiledScoreLoader:
    """Loads frozen score values and builds indexes after contract validation."""

    def __init__(self, contract_validator: Optional[ContractValidator] = None) -> None:
        if contract_validator is None:
            from .schema_validation import SchemaRegistry

            registry = SchemaRegistry()
            self._contract_validator = registry.validate
        else:
            self._contract_validator = contract_validator

    def load(
        self,
        path: Union[str, os.PathLike[str]],
        expected_sha256: Optional[str] = None,
    ) -> CompiledPerformanceScore:
        try:
            data = Path(path).read_bytes()
        except OSError as exc:
            raise ScoreValidationError("artifact_missing", "score artifact could not be read") from exc
        return self.loads(data, expected_sha256=expected_sha256)

    def loads(
        self,
        data: Union[str, bytes, bytearray],
        expected_sha256: Optional[str] = None,
    ) -> CompiledPerformanceScore:
        raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        try:
            value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_without_duplicates)
        except ScoreValidationError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ScoreValidationError("schema_invalid", "score artifact is not valid UTF-8 JSON") from exc
        return self.from_mapping(_require_mapping(value, "$"), expected_sha256=expected_sha256)

    def from_mapping(
        self,
        value: Mapping[str, object],
        expected_sha256: Optional[str] = None,
    ) -> CompiledPerformanceScore:
        if self._contract_validator is not None:
            try:
                self._contract_validator("CompiledPerformanceScoreV1", value)
            except ScoreValidationError:
                raise
            except ValueError as exc:
                raise ScoreValidationError(
                    getattr(exc, "code", "schema_invalid"),
                    "compiled score does not satisfy its contract",
                    getattr(exc, "path", "$"),
                ) from exc
        frozen = _freeze(value)
        try:
            canonical = _canonical_bytes(frozen)
        except UnicodeEncodeError as exc:
            raise ScoreValidationError("invalid_type", "score contains invalid Unicode") from exc
        artifact_sha256 = _sha256_ref(canonical)
        if expected_sha256 is not None:
            _require_sha256(expected_sha256, "expected_sha256")
            if artifact_sha256 != expected_sha256:
                raise ScoreValidationError("hash_mismatch", "compiled score hash does not match")

        schema_version = value.get("schema_version")
        if schema_version != SCORE_SCHEMA_VERSION or isinstance(schema_version, bool):
            raise ScoreValidationError("schema_version_unsupported", "compiled score schema must be version 1")
        compiled_score_id = _require_id(value.get("compiled_score_id"), "$.compiled_score_id")
        performance_sha = _require_sha256(value.get("performance_score_sha256"), "$.performance_score_sha256")
        revision = _require_int(value.get("revision", 1), "$.revision", minimum=1)
        runtime_api = _require_int(value.get("runtime_api_version"), "$.runtime_api_version", minimum=1)

        validation = _require_mapping(value.get("validation"), "$.validation")
        if validation.get("decision") != "accepted":
            raise ScoreValidationError("artifact_not_accepted", "compiled score is not accepted")

        character = _require_mapping(value.get("character"), "$.character")
        character_id = _require_id(character.get("character_id"), "$.character.character_id")
        package_digest = _require_sha256(character.get("package_digest"), "$.character.package_digest")

        media_value = value.get("media", {})
        media = _require_mapping(media_value, "$.media")
        media_id_raw = media.get("media_id")
        media_sha_raw = media.get("media_sha256")
        media_id = _require_id(media_id_raw, "$.media.media_id") if media_id_raw is not None else None
        media_sha = _require_sha256(media_sha_raw, "$.media.media_sha256") if media_sha_raw is not None else None
        duration_raw = media.get("duration_ms", value.get("duration_ms", 0))
        duration_ms = _require_int(duration_raw, "$.media.duration_ms")

        tracks_raw = value.get("tracks")
        if not isinstance(tracks_raw, (list, tuple)):
            raise ScoreValidationError("invalid_type", "compiled score tracks must be an array", "$.tracks")
        tracks = tuple(
            PerformanceTrack.from_mapping(
                _require_mapping(track, "$.tracks[{}]".format(index)),
                "$.tracks[{}]".format(index),
            )
            for index, track in enumerate(tracks_raw)
        )
        if len({track.track_id for track in tracks}) != len(tracks):
            raise ScoreValidationError("invalid_id", "track IDs must be unique", "$.tracks")
        all_cues = [cue for track in tracks for cue in track.index.cues]
        if len({cue.cue_id for cue in all_cues}) != len(all_cues):
            raise ScoreValidationError("invalid_id", "cue IDs must be globally unique", "$.tracks")
        if duration_ms:
            for cue in all_cues:
                if cue.end_ms > duration_ms:
                    raise ScoreValidationError("time_out_of_bounds", "cue exceeds media duration", "$.tracks")

        return CompiledPerformanceScore(
            schema_version=SCORE_SCHEMA_VERSION,
            score_id=compiled_score_id,
            revision=revision,
            duration_ms=duration_ms,
            media_id=media_id,
            media_sha256=media_sha,
            tracks=tracks,
            artifact_sha256=artifact_sha256,
            document=frozen,  # type: ignore[arg-type]
            compiled_score_id=compiled_score_id,
            performance_score_sha256=performance_sha,
            character_id=character_id,
            package_digest=package_digest,
            runtime_api_version=runtime_api,
        )


@dataclass(frozen=True)
class ScorePublication:
    media_sha256: str
    score_id: str
    revision: int
    score_sha256: str
    compiled_score_id: str
    package_digest: str

    def to_dict(self) -> Mapping[str, object]:
        return {
            "schema_version": 1,
            "media_sha256": self.media_sha256,
            "score_id": self.score_id,
            "revision": self.revision,
            "score_sha256": self.score_sha256,
            "compiled_score_id": self.compiled_score_id,
            "package_digest": self.package_digest,
        }


class CompiledScoreRepository:
    """Content-bound immutable score generations with an atomic current pointer."""

    def __init__(self, root: Union[str, os.PathLike[str]], loader: Optional[CompiledScoreLoader] = None) -> None:
        self.root = Path(root)
        self.loader = loader or CompiledScoreLoader()
        self._thread_lock = threading.RLock()

    @staticmethod
    def _media_key(media_sha256: str) -> str:
        return _require_sha256(media_sha256, "media_sha256").split(":", 1)[1]

    def _media_root(self, media_sha256: str) -> Path:
        return self.root / "media" / self._media_key(media_sha256)

    def _generation_path(self, publication: ScorePublication) -> Path:
        return self._media_root(publication.media_sha256) / "scores" / publication.score_id / str(publication.revision)

    @contextlib.contextmanager
    def _publication_lock(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        with self._thread_lock:
            lock_file = (self.root / ".publication.lock").open("a+b")
            try:
                try:
                    import fcntl

                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                except ImportError:
                    pass
                yield
            finally:
                try:
                    import fcntl

                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                except ImportError:
                    pass
                lock_file.close()

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        descriptor = os.open(str(path), os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def _write_file(path: Path, data: bytes) -> None:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

    def _read_pointer(self, media_sha256: str) -> Optional[ScorePublication]:
        pointer_path = self._media_root(media_sha256) / "current.json"
        if not pointer_path.exists():
            return None
        try:
            value = json.loads(pointer_path.read_text("utf-8"), object_pairs_hook=_pairs_without_duplicates)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ScoreValidationError) as exc:
            raise ScoreValidationError("cache_corrupt", "current score pointer is corrupt") from exc
        mapping = _require_mapping(value, "$.current")
        expected = {
            "schema_version",
            "media_sha256",
            "score_id",
            "revision",
            "score_sha256",
            "compiled_score_id",
            "package_digest",
        }
        if set(mapping) != expected or mapping.get("schema_version") != 1:
            raise ScoreValidationError("cache_corrupt", "current score pointer shape is invalid")
        return ScorePublication(
            media_sha256=_require_sha256(mapping.get("media_sha256"), "$.current.media_sha256"),
            score_id=_require_id(mapping.get("score_id"), "$.current.score_id"),
            revision=_require_int(mapping.get("revision"), "$.current.revision", minimum=1),
            score_sha256=_require_sha256(mapping.get("score_sha256"), "$.current.score_sha256"),
            compiled_score_id=_require_id(mapping.get("compiled_score_id"), "$.current.compiled_score_id"),
            package_digest=_require_sha256(mapping.get("package_digest"), "$.current.package_digest"),
        )

    def _replace_pointer(self, publication: ScorePublication) -> None:
        media_root = self._media_root(publication.media_sha256)
        media_root.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".current-", suffix=".json", dir=str(media_root))
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(_canonical_bytes(publication.to_dict()))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(str(temporary), str(media_root / "current.json"))
            self._fsync_directory(media_root)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def publish(
        self,
        score: CompiledPerformanceScore,
        media_sha256: Optional[str] = None,
        score_id: Optional[str] = None,
        revision: Optional[int] = None,
    ) -> ScorePublication:
        if not isinstance(score, CompiledPerformanceScore):
            raise TypeError("score must be a CompiledPerformanceScore")
        bound_media = media_sha256 or score.media_sha256
        if bound_media is None:
            raise ScoreValidationError("media_mismatch", "publication requires a media digest")
        bound_media = _require_sha256(bound_media, "media_sha256")
        if score.media_sha256 is not None and score.media_sha256 != bound_media:
            raise ScoreValidationError("media_mismatch", "score media binding does not match publication")
        publication = ScorePublication(
            media_sha256=bound_media,
            score_id=_require_id(score_id or score.score_id, "score_id"),
            revision=_require_int(revision if revision is not None else score.revision, "revision", minimum=1),
            score_sha256=score.artifact_sha256,
            compiled_score_id=score.compiled_score_id,
            package_digest=score.package_digest,
        )
        generation = self._generation_path(publication)
        score_bytes = _canonical_bytes(score.document)
        manifest_bytes = _canonical_bytes(publication.to_dict())

        with self._publication_lock():
            current = self._read_pointer(bound_media)
            if current is not None and publication.revision < current.revision:
                raise ScoreValidationError("job_stale", "older score revision cannot replace current")
            if generation.exists():
                existing = self.loader.load(generation / "score.json")
                if existing.artifact_sha256 != score.artifact_sha256:
                    raise ScoreValidationError("immutable_revision_conflict", "score revision already has different bytes")
            else:
                generation.parent.mkdir(parents=True, exist_ok=True)
                staging = Path(tempfile.mkdtemp(prefix=".publish-", dir=str(generation.parent)))
                try:
                    self._write_file(staging / "score.json", score_bytes)
                    self._write_file(staging / "manifest.json", manifest_bytes)
                    self._fsync_directory(staging)
                    os.rename(str(staging), str(generation))
                    self._fsync_directory(generation.parent)
                except BaseException:
                    shutil.rmtree(staging, ignore_errors=True)
                    raise
            self._replace_pointer(publication)
        return publication

    def load_revision(self, publication: ScorePublication) -> CompiledPerformanceScore:
        score = self.loader.load(
            self._generation_path(publication) / "score.json",
            expected_sha256=publication.score_sha256,
        )
        if score.compiled_score_id != publication.compiled_score_id or score.package_digest != publication.package_digest:
            raise ScoreValidationError("cache_corrupt", "score generation does not match its manifest")
        return score

    def load_current(self, media_sha256: str) -> CompiledPerformanceScore:
        with self._publication_lock():
            publication = self._read_pointer(media_sha256)
            if publication is None:
                raise ScoreValidationError("score_not_ready", "no current score is published")
            if publication.media_sha256 != media_sha256:
                raise ScoreValidationError("cache_corrupt", "current pointer media binding is invalid")
            return self.load_revision(publication)

    def select_revision(self, publication: ScorePublication) -> None:
        """Atomically repoint current to an existing validated revision for rollback."""

        with self._publication_lock():
            self.load_revision(publication)
            self._replace_pointer(publication)


PerformanceScoreRepository = CompiledScoreRepository
