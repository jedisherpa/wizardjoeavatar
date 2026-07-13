from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Dict, Mapping, Tuple, Union


TRANSPORT_SCHEMA_VERSION = 1
MAX_TRANSPORT_BYTES = 1024 * 1024
MAX_RUNTIME_EPOCH_LENGTH = 128
MAX_JSON_DEPTH = 32
MAX_SAFE_SEQUENCE = (1 << 53) - 1
TRANSPORT_MESSAGE_TYPES = frozenset(
    {
        "ack",
        "command",
        "command_ack",
        "error",
        "event",
        "hello",
        "metrics",
        "resync",
        "resync_request",
        "resync_response",
        "snapshot",
        "state",
    }
)


class TransportValidationError(ValueError):
    """Raised when a transport message is not valid protocol JSON."""


def _strict_int(name: str, value: object, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TransportValidationError("{} must be an integer".format(name))
    if value < minimum:
        raise TransportValidationError("{} must be >= {}".format(name, minimum))
    if value > MAX_SAFE_SEQUENCE:
        raise TransportValidationError("{} exceeds the JSON safe integer range".format(name))
    return value


def _freeze_json(value: object, path: str = "payload", depth: int = 0) -> object:
    if depth > MAX_JSON_DEPTH:
        raise TransportValidationError("{} exceeds maximum nesting depth".format(path))
    if isinstance(value, Mapping):
        frozen: Dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TransportValidationError("{} keys must be strings".format(path))
            frozen[key] = _freeze_json(item, "{}.{}".format(path, key), depth + 1)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json(item, "{}[{}]".format(path, index), depth + 1)
            for index, item in enumerate(value)
        )
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        if value < -MAX_SAFE_SEQUENCE or value > MAX_SAFE_SEQUENCE:
            raise TransportValidationError("{} exceeds the JSON safe integer range".format(path))
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TransportValidationError("{} must be finite".format(path))
        return value
    raise TransportValidationError(
        "{} contains unsupported value type {}".format(path, type(value).__name__)
    )


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True)
class TransportMessageV1:
    schema_version: int
    message_type: str
    runtime_epoch: str
    sequence: int
    payload: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or self.schema_version != TRANSPORT_SCHEMA_VERSION
        ):
            raise TransportValidationError("schema_version must be exactly 1")
        if self.message_type not in TRANSPORT_MESSAGE_TYPES:
            raise TransportValidationError(
                "unsupported transport message type: {}".format(self.message_type)
            )
        if (
            not isinstance(self.runtime_epoch, str)
            or not self.runtime_epoch
            or len(self.runtime_epoch) > MAX_RUNTIME_EPOCH_LENGTH
        ):
            raise TransportValidationError(
                "runtime_epoch must be a non-empty string <= {} characters".format(
                    MAX_RUNTIME_EPOCH_LENGTH
                )
            )
        _strict_int("sequence", self.sequence)
        if not isinstance(self.payload, Mapping):
            raise TransportValidationError("payload must be an object")
        object.__setattr__(self, "payload", _freeze_json(self.payload))

    @property
    def type(self) -> str:
        return self.message_type

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "TransportMessageV1":
        if not isinstance(value, Mapping):
            raise TransportValidationError("transport message must be an object")
        keys = set(value.keys())
        if any(not isinstance(key, str) for key in keys):
            raise TransportValidationError("transport message keys must be strings")
        required = {"schema_version", "type", "runtime_epoch", "sequence", "payload"}
        unknown = sorted(keys - required)
        missing = sorted(required - keys)
        if unknown:
            raise TransportValidationError(
                "unknown transport fields: {}".format(", ".join(unknown))
            )
        if missing:
            raise TransportValidationError(
                "missing transport fields: {}".format(", ".join(missing))
            )
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            message_type=value["type"],  # type: ignore[arg-type]
            runtime_epoch=value["runtime_epoch"],  # type: ignore[arg-type]
            sequence=value["sequence"],  # type: ignore[arg-type]
            payload=value["payload"],  # type: ignore[arg-type]
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "type": self.message_type,
            "runtime_epoch": self.runtime_epoch,
            "sequence": self.sequence,
            "payload": _thaw_json(self.payload),
        }

    def to_json(self) -> str:
        return serialize_transport_message(self)

    def to_bytes(self) -> bytes:
        return self.to_json().encode("utf-8")


def _reject_duplicate_keys(pairs: Tuple[Tuple[str, object], ...]) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TransportValidationError("duplicate JSON object key: {}".format(key))
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    raise TransportValidationError("non-finite JSON number is not allowed: {}".format(value))


def parse_transport_message(raw: Union[str, bytes]) -> TransportMessageV1:
    if isinstance(raw, bytes):
        if len(raw) > MAX_TRANSPORT_BYTES:
            raise TransportValidationError("transport message exceeds maximum size")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TransportValidationError("transport message must be valid UTF-8") from exc
    elif isinstance(raw, str):
        text = raw
        if len(text.encode("utf-8")) > MAX_TRANSPORT_BYTES:
            raise TransportValidationError("transport message exceeds maximum size")
    else:
        raise TransportValidationError("transport message must be str or bytes")
    try:
        value = json.loads(
            text,
            object_pairs_hook=lambda pairs: _reject_duplicate_keys(tuple(pairs)),
            parse_constant=_reject_json_constant,
        )
    except TransportValidationError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise TransportValidationError("transport message is not valid JSON") from exc
    if not isinstance(value, Mapping):
        raise TransportValidationError("transport message must be a JSON object")
    return TransportMessageV1.from_mapping(value)


def serialize_transport_message(
    message: Union[TransportMessageV1, Mapping[str, object]],
) -> str:
    if isinstance(message, TransportMessageV1):
        validated = message
    elif isinstance(message, Mapping):
        validated = TransportMessageV1.from_mapping(message)
    else:
        raise TransportValidationError("transport message must be an envelope or mapping")
    try:
        encoded = json.dumps(
            validated.to_dict(),
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise TransportValidationError("transport message cannot be serialized") from exc
    if len(encoded.encode("utf-8")) > MAX_TRANSPORT_BYTES:
        raise TransportValidationError("transport message exceeds maximum size")
    return encoded


def serialize_transport_bytes(
    message: Union[TransportMessageV1, Mapping[str, object]],
) -> bytes:
    return serialize_transport_message(message).encode("utf-8")


parse_message = parse_transport_message
serialize_message = serialize_transport_message


__all__ = [
    "MAX_TRANSPORT_BYTES",
    "TRANSPORT_MESSAGE_TYPES",
    "TRANSPORT_SCHEMA_VERSION",
    "TransportMessageV1",
    "TransportValidationError",
    "parse_message",
    "parse_transport_message",
    "serialize_message",
    "serialize_transport_bytes",
    "serialize_transport_message",
]
