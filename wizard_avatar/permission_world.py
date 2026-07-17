"""Truthful, content-free permission-world projection primitives.

This module has no permission-granting behavior. It accepts a sanitized snapshot
of an external permission authority and projects semantic affordance descriptors
for later capability admission. The projection is pure: time and motion policy
are explicit inputs, and no device, application, or runtime state is observed.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple, Union

from .artifact_hashing import MAX_SAFE_INTEGER, canonical_json_v1, sha256_ref


PERMISSION_WORLD_SCHEMA_VERSION = 1
PERMISSION_WORLD_MAX_BODY_BYTES = 64 * 1024
PERMISSION_WORLD_MAX_PERMISSIONS = 256
PERMISSION_WORLD_MAX_SURFACES = 64
PERMISSION_WORLD_DEFAULT_RETIRED_EPOCH_CAPACITY = 64
PERMISSION_WORLD_MAX_RETIRED_EPOCH_CAPACITY = 1024

PERMISSION_POSTURES = frozenset(
    {"granted", "denied", "promptable", "unavailable", "unknown"}
)
APP_LINK_STATES = frozenset(
    {"not_required", "linked", "unlinked", "revoked", "unknown"}
)
MOTION_PROFILES = frozenset({"full", "reduced", "still"})
EXPIRY_CLASSES = frozenset({"current", "expired", "not_applicable", "unbounded"})
AVAILABILITIES = frozenset({"absent", "available", "requestable"})
VISIBILITIES = frozenset({"hidden", "visible"})
PROJECTED_POSTURES = frozenset({"denied", "granted", "promptable", "unavailable"})
SURFACE_CLASSES = frozenset({"effect", "prop", "unsupported", "unbound", "world_state"})
SUPPORT_STATUSES = frozenset({"supported", "unsupported", "unsupported_kind", "unbound"})
REVOCATION_BEHAVIORS = frozenset({"remove_immediately"})
REASON_CODES = frozenset(
    {
        "app_link_revoked",
        "app_link_unknown",
        "app_unlinked",
        "permission_denied",
        "permission_expired",
        "permission_granted",
        "permission_promptable",
        "permission_revoked",
        "permission_unavailable",
        "permission_unknown",
        "scope_mismatch",
        "scope_unproven",
        "character_capability_absent",
        "unsupported_capability_kind",
    }
)

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_PRIVATE_ID_FRAGMENTS = (
    "authority",
    "content",
    "credential",
    "document",
    "message",
    "path",
    "payload",
    "prompt",
    "query",
    "receipt",
    "reply",
    "response",
    "secret",
    "token",
    "transcript",
    "url",
)


class PermissionWorldError(ValueError):
    """A stable, path-addressed contract failure without caller content."""

    def __init__(self, code: str, message: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(message)


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PermissionWorldError("invalid_type", "expected an object", path)
    return value


def _exact(value: Mapping[str, object], fields: Sequence[str], path: str) -> None:
    expected = set(fields)
    if expected - set(value):
        raise PermissionWorldError("missing_field", "object is missing required fields", path)
    if set(value) - expected:
        raise PermissionWorldError("unknown_field", "object contains unknown fields", path)


def _integer(value: object, path: str) -> int:
    if type(value) is not int or not 0 <= value <= MAX_SAFE_INTEGER:
        raise PermissionWorldError("invalid_integer", "expected a non-negative safe integer", path)
    return value


def _optional_integer(value: object, path: str) -> Optional[int]:
    return None if value is None else _integer(value, path)


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        raise PermissionWorldError("invalid_type", "expected a boolean", path)
    return value


def _enum(value: object, allowed: frozenset[str], path: str) -> str:
    if type(value) is not str or value not in allowed:
        raise PermissionWorldError("invalid_enum", "value is not in the allowed set", path)
    return value


def _content_free_id(value: object, path: str) -> str:
    if type(value) is not str or _ID_PATTERN.fullmatch(value) is None:
        raise PermissionWorldError(
            "invalid_id", "expected a stable content-free identifier", path
        )
    normalized = value.lower().replace("-", "_")
    if any(fragment in normalized for fragment in _PRIVATE_ID_FRAGMENTS):
        raise PermissionWorldError(
            "private_content", "identifier contains a forbidden private concept", path
        )
    return value


def _optional_content_free_id(value: object, path: str) -> Optional[str]:
    return None if value is None else _content_free_id(value, path)


def _content_free_ids(value: object, path: str) -> Tuple[str, ...]:
    if type(value) not in (list, tuple):
        raise PermissionWorldError("invalid_type", "expected an array of identifiers", path)
    if len(value) > PERMISSION_WORLD_MAX_SURFACES:
        raise PermissionWorldError("too_many_items", "identifier array exceeds the limit", path)
    result = tuple(
        _content_free_id(item, "{}[{}]".format(path, index))
        for index, item in enumerate(value)
    )
    if result != tuple(sorted(result)) or len(result) != len(set(result)):
        raise PermissionWorldError(
            "invalid_order", "identifiers must be sorted and unique", path
        )
    return result


def _hash(value: object, path: str) -> str:
    if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
        raise PermissionWorldError("invalid_hash", "expected a SHA-256 reference", path)
    return value


def _parse_json(source: Union[str, bytes]) -> Mapping[str, object]:
    if type(source) is bytes:
        if len(source) > PERMISSION_WORLD_MAX_BODY_BYTES:
            raise PermissionWorldError("body_too_large", "permission state exceeds the limit")
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PermissionWorldError("invalid_json", "state is not UTF-8 JSON") from exc
    elif type(source) is str:
        if len(source.encode("utf-8")) > PERMISSION_WORLD_MAX_BODY_BYTES:
            raise PermissionWorldError("body_too_large", "permission state exceeds the limit")
        text = source
    else:
        raise PermissionWorldError("invalid_type", "source must be JSON text or bytes")

    def reject_duplicates(pairs: Sequence[Tuple[str, object]]) -> Dict[str, object]:
        result: Dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise PermissionWorldError("duplicate_json_key", "duplicate JSON object key")
            result[key] = item
        return result

    def reject_float(_value: str) -> object:
        raise PermissionWorldError("invalid_integer", "floating-point values are not allowed")

    try:
        parsed = json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except PermissionWorldError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise PermissionWorldError("invalid_json", "state is not valid JSON") from exc
    return _mapping(parsed, "$")


@dataclass(frozen=True)
class CapabilityPermissionV1:
    """One sanitized capability decision from the real permission authority."""

    capability_kind: str
    posture: str
    required_scope_class: str
    granted_scope_class: Optional[str]
    purpose_code: str
    granted_at_ms: Optional[int]
    affected_surfaces: Tuple[str, ...]
    app_link_state: str
    expires_at_ms: Optional[int]
    revoked: bool

    def __post_init__(self) -> None:
        _content_free_id(self.capability_kind, "$.capability_kind")
        _enum(self.posture, PERMISSION_POSTURES, "$.posture")
        _content_free_id(self.required_scope_class, "$.required_scope_class")
        _optional_content_free_id(self.granted_scope_class, "$.granted_scope_class")
        _content_free_id(self.purpose_code, "$.purpose_code")
        _optional_integer(self.granted_at_ms, "$.granted_at_ms")
        _content_free_ids(self.affected_surfaces, "$.affected_surfaces")
        _enum(self.app_link_state, APP_LINK_STATES, "$.app_link_state")
        _optional_integer(self.expires_at_ms, "$.expires_at_ms")
        _boolean(self.revoked, "$.revoked")
        if (self.granted_scope_class is None) != (self.granted_at_ms is None):
            raise PermissionWorldError(
                "incomplete_grant_facts",
                "granted scope and grant time must be present together",
            )
        if (
            self.granted_at_ms is not None
            and self.expires_at_ms is not None
            and self.expires_at_ms < self.granted_at_ms
        ):
            raise PermissionWorldError(
                "invalid_time_range", "expiry cannot precede grant time"
            )

    @classmethod
    def from_mapping(cls, raw: object, path: str = "$") -> "CapabilityPermissionV1":
        value = _mapping(raw, path)
        fields = (
            "capability_kind",
            "posture",
            "required_scope_class",
            "granted_scope_class",
            "purpose_code",
            "granted_at_ms",
            "affected_surfaces",
            "app_link_state",
            "expires_at_ms",
            "revoked",
        )
        _exact(value, fields, path)
        return cls(
            _content_free_id(value["capability_kind"], path + ".capability_kind"),
            _enum(value["posture"], PERMISSION_POSTURES, path + ".posture"),
            _content_free_id(
                value["required_scope_class"], path + ".required_scope_class"
            ),
            _optional_content_free_id(
                value["granted_scope_class"], path + ".granted_scope_class"
            ),
            _content_free_id(value["purpose_code"], path + ".purpose_code"),
            _optional_integer(value["granted_at_ms"], path + ".granted_at_ms"),
            _content_free_ids(value["affected_surfaces"], path + ".affected_surfaces"),
            _enum(value["app_link_state"], APP_LINK_STATES, path + ".app_link_state"),
            _optional_integer(value["expires_at_ms"], path + ".expires_at_ms"),
            _boolean(value["revoked"], path + ".revoked"),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "capability_kind": self.capability_kind,
            "posture": self.posture,
            "required_scope_class": self.required_scope_class,
            "granted_scope_class": self.granted_scope_class,
            "purpose_code": self.purpose_code,
            "granted_at_ms": self.granted_at_ms,
            "affected_surfaces": list(self.affected_surfaces),
            "app_link_state": self.app_link_state,
            "expires_at_ms": self.expires_at_ms,
            "revoked": self.revoked,
        }


@dataclass(frozen=True)
class PermissionWorldStateV1:
    """Frozen, hashed permission snapshot accepted by the projection boundary."""

    schema_version: int
    source_epoch: str
    observed_at_ms: int
    permissions: Tuple[CapabilityPermissionV1, ...]
    state_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != PERMISSION_WORLD_SCHEMA_VERSION:
            raise PermissionWorldError("unsupported_version", "unsupported schema version")
        _content_free_id(self.source_epoch, "$.source_epoch")
        _integer(self.observed_at_ms, "$.observed_at_ms")
        if type(self.permissions) is not tuple or any(
            type(item) is not CapabilityPermissionV1 for item in self.permissions
        ):
            raise PermissionWorldError(
                "invalid_type",
                "permissions must be a tuple of V1 permission records",
                "$.permissions",
            )
        if len(self.permissions) > PERMISSION_WORLD_MAX_PERMISSIONS:
            raise PermissionWorldError(
                "too_many_items", "permission array exceeds the limit", "$.permissions"
            )
        kinds = [item.capability_kind for item in self.permissions]
        if kinds != sorted(kinds) or len(kinds) != len(set(kinds)):
            raise PermissionWorldError(
                "invalid_order",
                "permissions must be sorted and unique by capability kind",
                "$.permissions",
            )
        for index, permission in enumerate(self.permissions):
            if (
                permission.granted_at_ms is not None
                and permission.granted_at_ms > self.observed_at_ms
            ):
                raise PermissionWorldError(
                    "grant_after_observation",
                    "grant time cannot follow its observation",
                    "$.permissions[{}].granted_at_ms".format(index),
                )
        _hash(self.state_sha256, "$.state_sha256")
        if self.state_sha256 != self._computed_hash():
            raise PermissionWorldError("hash_mismatch", "permission state hash does not match")

    @classmethod
    def build(
        cls,
        source_epoch: str,
        observed_at_ms: int,
        permissions: Sequence[Union[CapabilityPermissionV1, Mapping[str, object]]],
    ) -> "PermissionWorldStateV1":
        parsed = []
        if len(permissions) > PERMISSION_WORLD_MAX_PERMISSIONS:
            raise PermissionWorldError(
                "too_many_items", "permission array exceeds the limit", "$.permissions"
            )
        for index, permission in enumerate(permissions):
            if type(permission) is CapabilityPermissionV1:
                parsed.append(permission)
            else:
                parsed.append(
                    CapabilityPermissionV1.from_mapping(
                        permission, "$.permissions[{}]".format(index)
                    )
                )
        parsed.sort(key=lambda item: item.capability_kind)
        if len(parsed) != len({item.capability_kind for item in parsed}):
            raise PermissionWorldError(
                "duplicate_capability", "capability kinds must be unique", "$.permissions"
            )
        identity = {
            "schema_version": PERMISSION_WORLD_SCHEMA_VERSION,
            "source_epoch": _content_free_id(source_epoch, "$.source_epoch"),
            "observed_at_ms": _integer(observed_at_ms, "$.observed_at_ms"),
            "permissions": [item.to_dict() for item in parsed],
        }
        return cls(
            PERMISSION_WORLD_SCHEMA_VERSION,
            identity["source_epoch"],
            identity["observed_at_ms"],
            tuple(parsed),
            sha256_ref(canonical_json_v1(identity)),
        )

    @classmethod
    def from_mapping(cls, raw: object) -> "PermissionWorldStateV1":
        value = _mapping(raw, "$")
        fields = (
            "schema_version",
            "source_epoch",
            "observed_at_ms",
            "permissions",
            "state_sha256",
        )
        _exact(value, fields, "$")
        if type(value["permissions"]) not in (list, tuple):
            raise PermissionWorldError(
                "invalid_type", "permissions must be an array", "$.permissions"
            )
        if len(value["permissions"]) > PERMISSION_WORLD_MAX_PERMISSIONS:
            raise PermissionWorldError(
                "too_many_items", "permission array exceeds the limit", "$.permissions"
            )
        permissions = tuple(
            CapabilityPermissionV1.from_mapping(item, "$.permissions[{}]".format(index))
            for index, item in enumerate(value["permissions"])
        )
        return cls(
            _integer(value["schema_version"], "$.schema_version"),
            _content_free_id(value["source_epoch"], "$.source_epoch"),
            _integer(value["observed_at_ms"], "$.observed_at_ms"),
            permissions,
            _hash(value["state_sha256"], "$.state_sha256"),
        )

    @classmethod
    def from_json(cls, source: Union[str, bytes]) -> "PermissionWorldStateV1":
        return cls.from_mapping(_parse_json(source))

    def _identity_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_epoch": self.source_epoch,
            "observed_at_ms": self.observed_at_ms,
            "permissions": [item.to_dict() for item in self.permissions],
        }

    def _computed_hash(self) -> str:
        return sha256_ref(canonical_json_v1(self._identity_dict()))

    def to_dict(self) -> Dict[str, object]:
        result = self._identity_dict()
        result["state_sha256"] = self.state_sha256
        return result

    def canonical_json(self) -> bytes:
        return canonical_json_v1(self.to_dict())


@dataclass(frozen=True)
class PermissionWorldCapabilityIndexV1:
    """Surfaces explicitly authored as permission-managed by the character.

    Ordinary animation capability mappings describe what a character can do;
    they do not imply that the capability is controlled by user permission.
    Permission management is therefore opt-in through a manifest's optional
    ``permission_world`` mapping (or its explicit ``bindings`` child).
    """

    world_state_ids: Tuple[str, ...] = ()
    effect_ids: Tuple[str, ...] = ()
    prop_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _content_free_ids(self.world_state_ids, "$.world_state_ids")
        _content_free_ids(self.effect_ids, "$.effect_ids")
        _content_free_ids(self.prop_ids, "$.prop_ids")

    @classmethod
    def from_character_manifest(
        cls,
        manifest: Mapping[str, object],
    ) -> "PermissionWorldCapabilityIndexV1":
        """Index only surfaces explicitly bound to permission-world authority."""

        value = _mapping(manifest, "$.character_manifest")
        raw_permission_world = value.get("permission_world")
        if raw_permission_world is None:
            return cls()
        permission_world = _mapping(
            raw_permission_world,
            "$.character_manifest.permission_world",
        )
        raw_bindings = permission_world.get("bindings", permission_world)
        bindings = _mapping(
            raw_bindings,
            "$.character_manifest.permission_world.bindings",
        )

        def ids(field: str) -> Tuple[str, ...]:
            raw_ids = bindings.get(field, ())
            return _content_free_ids(
                raw_ids,
                "$.character_manifest.permission_world.bindings." + field,
            )

        admitted = {"effect_ids": set(), "prop_ids": set()}
        raw_capabilities = value.get("capabilities", ())
        if type(raw_capabilities) not in (list, tuple):
            raise PermissionWorldError(
                "invalid_type",
                "character manifest capabilities must be an array",
                "$.character_manifest.capabilities",
            )
        for index, raw_capability in enumerate(raw_capabilities):
            path = "$.character_manifest.capabilities[{}]".format(index)
            capability = _mapping(raw_capability, path)
            if capability.get("admission") == "unsupported":
                continue
            mapping = _mapping(capability.get("mapping"), path + ".mapping")
            for field in admitted:
                admitted[field].update(
                    _content_free_ids(mapping.get(field, ()), path + ".mapping." + field)
                )

        requested_effects = ids("effect_ids")
        requested_props = ids("prop_ids")

        return cls(
            ids("world_state_ids"),
            tuple(item for item in requested_effects if item in admitted["effect_ids"]),
            tuple(item for item in requested_props if item in admitted["prop_ids"]),
        )

    def resolve(self, capability_kind: str) -> Tuple[str, Optional[str], str]:
        if ":" not in capability_kind:
            return "unsupported", None, "unsupported_kind"
        surface_class, surface_id = capability_kind.split(":", 1)
        targets = {
            "world_state": self.world_state_ids,
            "effect": self.effect_ids,
            "prop": self.prop_ids,
        }.get(surface_class)
        if targets is None:
            return "unsupported", None, "unsupported_kind"
        _content_free_id(surface_id, "$.capability_kind")
        return (
            surface_class,
            surface_id,
            "supported" if surface_id in targets else "unsupported",
        )


@dataclass(frozen=True)
class PermissionAffordanceV1:
    """A content-free semantic descriptor with no execution authority."""

    capability_kind: str
    permission_posture: str
    scope_class: str
    purpose_class: str
    observed_at_ms: int
    granted_at_ms: Optional[int]
    expires_at_ms: Optional[int]
    affected_surface_classes: Tuple[str, ...]
    revocation_behavior: str
    surface_class: str
    surface_id: Optional[str]
    support_status: str
    expiry_class: str
    availability: str
    visibility: str
    reason_code: str
    motion_profile: str

    def __post_init__(self) -> None:
        _content_free_id(self.capability_kind, "$.capability_kind")
        _enum(self.permission_posture, PROJECTED_POSTURES, "$.permission_posture")
        _content_free_id(self.scope_class, "$.scope_class")
        _content_free_id(self.purpose_class, "$.purpose_class")
        _integer(self.observed_at_ms, "$.observed_at_ms")
        _optional_integer(self.granted_at_ms, "$.granted_at_ms")
        _optional_integer(self.expires_at_ms, "$.expires_at_ms")
        _content_free_ids(self.affected_surface_classes, "$.affected_surface_classes")
        _enum(self.revocation_behavior, REVOCATION_BEHAVIORS, "$.revocation_behavior")
        _enum(self.surface_class, SURFACE_CLASSES, "$.surface_class")
        _optional_content_free_id(self.surface_id, "$.surface_id")
        _enum(self.support_status, SUPPORT_STATUSES, "$.support_status")
        _enum(self.expiry_class, EXPIRY_CLASSES, "$.expiry_class")
        _enum(self.availability, AVAILABILITIES, "$.availability")
        _enum(self.visibility, VISIBILITIES, "$.visibility")
        _enum(self.reason_code, REASON_CODES, "$.reason_code")
        _enum(self.motion_profile, MOTION_PROFILES, "$.motion_profile")
        if self.availability in {"available", "requestable"} and self.visibility != "visible":
            raise PermissionWorldError(
                "invalid_affordance", "present affordances must be visible"
            )
        if self.availability == "absent" and self.visibility != "hidden":
            raise PermissionWorldError(
                "invalid_affordance", "absent affordances must be hidden"
            )
        if self.availability == "available" and self.permission_posture != "granted":
            raise PermissionWorldError(
                "invalid_affordance", "only a granted posture can be available"
            )
        if self.availability == "requestable" and self.permission_posture != "promptable":
            raise PermissionWorldError(
                "invalid_affordance", "only a promptable posture can be requestable"
            )
        if self.support_status == "supported" and self.surface_id is None:
            raise PermissionWorldError(
                "invalid_affordance", "supported affordances require a surface identity"
            )
        if self.availability == "available" and self.support_status in {
            "unsupported",
            "unsupported_kind",
        }:
            raise PermissionWorldError(
                "invalid_affordance", "unsupported affordances cannot be available"
            )

    def to_dict(self) -> Dict[str, object]:
        return {
            "capability_kind": self.capability_kind,
            "permission_posture": self.permission_posture,
            "scope_class": self.scope_class,
            "purpose_class": self.purpose_class,
            "observed_at_ms": self.observed_at_ms,
            "granted_at_ms": self.granted_at_ms,
            "expires_at_ms": self.expires_at_ms,
            "affected_surface_classes": list(self.affected_surface_classes),
            "revocation_behavior": self.revocation_behavior,
            "surface_class": self.surface_class,
            "surface_id": self.surface_id,
            "support_status": self.support_status,
            "expiry_class": self.expiry_class,
            "availability": self.availability,
            "visibility": self.visibility,
            "reason_code": self.reason_code,
            "motion_profile": self.motion_profile,
        }


@dataclass(frozen=True)
class PermissionWorldProjectionV1:
    """Deterministic semantic permission-world projection."""

    schema_version: int
    source_epoch: str
    source_state_sha256: str
    source_observed_at_ms: int
    evaluated_at_ms: int
    motion_profile: str
    affordances: Tuple[PermissionAffordanceV1, ...]
    managed_world_states: Tuple[str, ...]
    managed_effects: Tuple[str, ...]
    managed_props: Tuple[str, ...]
    visible_world_states: Tuple[str, ...]
    visible_effects: Tuple[str, ...]
    visible_props: Tuple[str, ...]
    projection_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != PERMISSION_WORLD_SCHEMA_VERSION:
            raise PermissionWorldError("unsupported_version", "unsupported schema version")
        _content_free_id(self.source_epoch, "$.source_epoch")
        _hash(self.source_state_sha256, "$.source_state_sha256")
        _integer(self.source_observed_at_ms, "$.source_observed_at_ms")
        _integer(self.evaluated_at_ms, "$.evaluated_at_ms")
        _enum(self.motion_profile, MOTION_PROFILES, "$.motion_profile")
        if type(self.affordances) is not tuple or any(
            type(item) is not PermissionAffordanceV1 for item in self.affordances
        ):
            raise PermissionWorldError(
                "invalid_type",
                "affordances must be a tuple of V1 descriptors",
                "$.affordances",
            )
        kinds = [item.capability_kind for item in self.affordances]
        if kinds != sorted(kinds) or len(kinds) != len(set(kinds)):
            raise PermissionWorldError(
                "invalid_order",
                "affordances must be sorted and unique by capability kind",
                "$.affordances",
            )
        _content_free_ids(self.managed_world_states, "$.managed_world_states")
        _content_free_ids(self.managed_effects, "$.managed_effects")
        _content_free_ids(self.managed_props, "$.managed_props")
        _content_free_ids(self.visible_world_states, "$.visible_world_states")
        _content_free_ids(self.visible_effects, "$.visible_effects")
        _content_free_ids(self.visible_props, "$.visible_props")
        if not set(self.visible_world_states).issubset(self.managed_world_states):
            raise PermissionWorldError(
                "unmanaged_surface", "visible world states must be managed"
            )
        if not set(self.visible_effects).issubset(self.managed_effects):
            raise PermissionWorldError(
                "unmanaged_surface", "visible effects must be managed"
            )
        if not set(self.visible_props).issubset(self.managed_props):
            raise PermissionWorldError(
                "unmanaged_surface", "visible props must be managed"
            )
        _hash(self.projection_sha256, "$.projection_sha256")
        if self.projection_sha256 != sha256_ref(canonical_json_v1(self._identity_dict())):
            raise PermissionWorldError("hash_mismatch", "projection hash does not match")

    def _identity_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_epoch": self.source_epoch,
            "source_state_sha256": self.source_state_sha256,
            "source_observed_at_ms": self.source_observed_at_ms,
            "evaluated_at_ms": self.evaluated_at_ms,
            "motion_profile": self.motion_profile,
            "affordances": [item.to_dict() for item in self.affordances],
            "managed_world_states": list(self.managed_world_states),
            "managed_effects": list(self.managed_effects),
            "managed_props": list(self.managed_props),
            "visible_world_states": list(self.visible_world_states),
            "visible_effects": list(self.visible_effects),
            "visible_props": list(self.visible_props),
        }

    def to_dict(self) -> Dict[str, object]:
        result = self._identity_dict()
        result["projection_sha256"] = self.projection_sha256
        return result

    def canonical_json(self) -> bytes:
        return canonical_json_v1(self.to_dict())

    def to_runtime_dict(self) -> Dict[str, object]:
        """Return an inspectable projection without the source's raw epoch identity."""

        return {
            "schema_version": self.schema_version,
            "status": "ready",
            "source_epoch_sha256": sha256_ref(self.source_epoch.encode("ascii")),
            "source_state_sha256": self.source_state_sha256,
            "observed_at_ms": self.source_observed_at_ms,
            "evaluated_at_ms": self.evaluated_at_ms,
            "motion_profile": self.motion_profile,
            "managed_surfaces": {
                "world_states": list(self.managed_world_states),
                "effects": list(self.managed_effects),
                "props": list(self.managed_props),
            },
            "visible_surfaces": {
                "world_states": list(self.visible_world_states),
                "effects": list(self.visible_effects),
                "props": list(self.visible_props),
            },
            "affordances": [item.to_dict() for item in self.affordances],
            "projection_sha256": self.projection_sha256,
        }


@dataclass(frozen=True)
class PermissionWorldRenderPolicyV1:
    """Small immutable authority snapshot consumed by the pure compositor.

    Managed surfaces are distinct from visible surfaces. An absent authority
    snapshot preserves authored rendering, while a current authority snapshot
    can only hide surfaces explicitly listed as managed. Director simulations
    deliberately have no conversion into this type.
    """

    schema_version: int
    authority: str
    source_state_sha256: Optional[str]
    evaluated_at_ms: int
    motion_profile: str
    managed_world_states: Tuple[str, ...]
    managed_effects: Tuple[str, ...]
    managed_props: Tuple[str, ...]
    visible_world_states: Tuple[str, ...]
    visible_effects: Tuple[str, ...]
    visible_props: Tuple[str, ...]
    projection_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != PERMISSION_WORLD_SCHEMA_VERSION:
            raise PermissionWorldError("unsupported_version", "unsupported schema version")
        if self.authority != "authoritative":
            raise PermissionWorldError(
                "invalid_authority", "render policy must be authoritative"
            )
        if self.source_state_sha256 is not None:
            _hash(self.source_state_sha256, "$.source_state_sha256")
        _integer(self.evaluated_at_ms, "$.evaluated_at_ms")
        _enum(self.motion_profile, MOTION_PROFILES, "$.motion_profile")
        _content_free_ids(self.managed_world_states, "$.managed_world_states")
        _content_free_ids(self.managed_effects, "$.managed_effects")
        _content_free_ids(self.managed_props, "$.managed_props")
        _content_free_ids(self.visible_world_states, "$.visible_world_states")
        _content_free_ids(self.visible_effects, "$.visible_effects")
        _content_free_ids(self.visible_props, "$.visible_props")
        if not set(self.visible_world_states).issubset(self.managed_world_states):
            raise PermissionWorldError(
                "unmanaged_surface", "visible world states must be managed"
            )
        if not set(self.visible_effects).issubset(self.managed_effects):
            raise PermissionWorldError(
                "unmanaged_surface", "visible effects must be managed"
            )
        if not set(self.visible_props).issubset(self.managed_props):
            raise PermissionWorldError(
                "unmanaged_surface", "visible props must be managed"
            )
        _hash(self.projection_sha256, "$.projection_sha256")
        if self.projection_sha256 != sha256_ref(canonical_json_v1(self._identity_dict())):
            raise PermissionWorldError("hash_mismatch", "render policy hash does not match")

    def _identity_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "authority": self.authority,
            "source_state_sha256": self.source_state_sha256,
            "evaluated_at_ms": self.evaluated_at_ms,
            "motion_profile": self.motion_profile,
            "managed_world_states": list(self.managed_world_states),
            "managed_effects": list(self.managed_effects),
            "managed_props": list(self.managed_props),
            "visible_world_states": list(self.visible_world_states),
            "visible_effects": list(self.visible_effects),
            "visible_props": list(self.visible_props),
        }

    @classmethod
    def build(
        cls,
        *,
        source_state_sha256: Optional[str],
        evaluated_at_ms: int,
        motion_profile: str,
        managed_world_states: Sequence[str] = (),
        managed_effects: Sequence[str] = (),
        managed_props: Sequence[str] = (),
        visible_world_states: Sequence[str] = (),
        visible_effects: Sequence[str] = (),
        visible_props: Sequence[str] = (),
    ) -> "PermissionWorldRenderPolicyV1":
        identity = {
            "schema_version": PERMISSION_WORLD_SCHEMA_VERSION,
            "authority": "authoritative",
            "source_state_sha256": source_state_sha256,
            "evaluated_at_ms": evaluated_at_ms,
            "motion_profile": motion_profile,
            "managed_world_states": list(managed_world_states),
            "managed_effects": list(managed_effects),
            "managed_props": list(managed_props),
            "visible_world_states": list(visible_world_states),
            "visible_effects": list(visible_effects),
            "visible_props": list(visible_props),
        }
        return cls(
            PERMISSION_WORLD_SCHEMA_VERSION,
            "authoritative",
            source_state_sha256,
            evaluated_at_ms,
            motion_profile,
            tuple(managed_world_states),
            tuple(managed_effects),
            tuple(managed_props),
            tuple(visible_world_states),
            tuple(visible_effects),
            tuple(visible_props),
            sha256_ref(canonical_json_v1(identity)),
        )

    @classmethod
    def from_projection(
        cls,
        projection: PermissionWorldProjectionV1,
    ) -> "PermissionWorldRenderPolicyV1":
        if type(projection) is not PermissionWorldProjectionV1:
            raise PermissionWorldError(
                "invalid_type", "projection must be PermissionWorldProjectionV1"
            )
        return cls.build(
            source_state_sha256=projection.source_state_sha256,
            evaluated_at_ms=projection.evaluated_at_ms,
            motion_profile=projection.motion_profile,
            managed_world_states=projection.managed_world_states,
            managed_effects=projection.managed_effects,
            managed_props=projection.managed_props,
            visible_world_states=projection.visible_world_states,
            visible_effects=projection.visible_effects,
            visible_props=projection.visible_props,
        )

    def to_dict(self) -> Dict[str, object]:
        result = self._identity_dict()
        result["projection_sha256"] = self.projection_sha256
        return result


def _expiry_class(permission: CapabilityPermissionV1, evaluated_at_ms: int) -> str:
    if permission.expires_at_ms is None:
        return "unbounded"
    if permission.expires_at_ms <= evaluated_at_ms:
        return "expired"
    return "current"


def _absent(
    permission: CapabilityPermissionV1,
    observed_at_ms: int,
    posture: str,
    expiry_class: str,
    reason_code: str,
    motion_profile: str,
    surface_class: str,
    surface_id: Optional[str],
    support_status: str,
) -> PermissionAffordanceV1:
    return PermissionAffordanceV1(
        capability_kind=permission.capability_kind,
        permission_posture=posture,
        scope_class=permission.required_scope_class,
        purpose_class=permission.purpose_code,
        observed_at_ms=observed_at_ms,
        granted_at_ms=permission.granted_at_ms,
        expires_at_ms=permission.expires_at_ms,
        affected_surface_classes=permission.affected_surfaces,
        revocation_behavior="remove_immediately",
        surface_class=surface_class,
        surface_id=surface_id,
        support_status=support_status,
        expiry_class=expiry_class,
        availability="absent",
        visibility="hidden",
        reason_code=reason_code,
        motion_profile=motion_profile,
    )


def _project_permission(
    permission: CapabilityPermissionV1,
    observed_at_ms: int,
    evaluated_at_ms: int,
    motion_profile: str,
    capability_index: Optional[PermissionWorldCapabilityIndexV1],
) -> PermissionAffordanceV1:
    expiry_class = _expiry_class(permission, evaluated_at_ms)
    if capability_index is None:
        surface_class, surface_id, support_status = "unbound", None, "unbound"
    else:
        surface_class, surface_id, support_status = capability_index.resolve(
            permission.capability_kind
        )

    def absent(posture: str, expiry: str, reason: str) -> PermissionAffordanceV1:
        return _absent(
            permission,
            observed_at_ms,
            posture,
            expiry,
            reason,
            motion_profile,
            surface_class,
            surface_id,
            support_status,
        )

    if permission.revoked:
        return absent("unavailable", expiry_class, "permission_revoked")
    if permission.posture == "unknown":
        return absent("unavailable", "not_applicable", "permission_unknown")
    if permission.posture == "denied":
        return absent("denied", "not_applicable", "permission_denied")
    if permission.posture == "unavailable":
        return absent("unavailable", "not_applicable", "permission_unavailable")
    if permission.app_link_state == "unlinked":
        return absent("unavailable", expiry_class, "app_unlinked")
    if permission.app_link_state == "revoked":
        return absent("unavailable", expiry_class, "app_link_revoked")
    if permission.app_link_state == "unknown":
        return absent("unavailable", expiry_class, "app_link_unknown")
    if expiry_class == "expired":
        return absent("unavailable", expiry_class, "permission_expired")
    if support_status == "unsupported_kind":
        return absent("unavailable", expiry_class, "unsupported_capability_kind")
    if support_status == "unsupported":
        return absent("unavailable", expiry_class, "character_capability_absent")

    if permission.posture == "promptable":
        return PermissionAffordanceV1(
            capability_kind=permission.capability_kind,
            permission_posture="promptable",
            scope_class=permission.required_scope_class,
            purpose_class=permission.purpose_code,
            observed_at_ms=observed_at_ms,
            granted_at_ms=permission.granted_at_ms,
            expires_at_ms=permission.expires_at_ms,
            affected_surface_classes=permission.affected_surfaces,
            revocation_behavior="remove_immediately",
            surface_class=surface_class,
            surface_id=surface_id,
            support_status=support_status,
            expiry_class=expiry_class,
            availability="requestable",
            visibility="visible",
            reason_code="permission_promptable",
            motion_profile=motion_profile,
        )

    if permission.granted_scope_class is None:
        return absent("unavailable", expiry_class, "scope_unproven")
    if permission.granted_scope_class != permission.required_scope_class:
        return absent("unavailable", expiry_class, "scope_mismatch")
    return PermissionAffordanceV1(
        capability_kind=permission.capability_kind,
        permission_posture="granted",
        scope_class=permission.required_scope_class,
        purpose_class=permission.purpose_code,
        observed_at_ms=observed_at_ms,
        granted_at_ms=permission.granted_at_ms,
        expires_at_ms=permission.expires_at_ms,
        affected_surface_classes=permission.affected_surfaces,
        revocation_behavior="remove_immediately",
        surface_class=surface_class,
        surface_id=surface_id,
        support_status=support_status,
        expiry_class=expiry_class,
        availability="available",
        visibility="visible",
        reason_code="permission_granted",
        motion_profile=motion_profile,
    )


def project_permission_world(
    state: PermissionWorldStateV1,
    *,
    evaluated_at_ms: int,
    motion_profile: str,
    capability_index: Optional[PermissionWorldCapabilityIndexV1] = None,
) -> PermissionWorldProjectionV1:
    """Purely project current permission truth into semantic affordances."""

    if type(state) is not PermissionWorldStateV1:
        raise PermissionWorldError("invalid_type", "state must be PermissionWorldStateV1")
    evaluated = _integer(evaluated_at_ms, "$.evaluated_at_ms")
    motion = _enum(motion_profile, MOTION_PROFILES, "$.motion_profile")
    if (
        capability_index is not None
        and type(capability_index) is not PermissionWorldCapabilityIndexV1
    ):
        raise PermissionWorldError(
            "invalid_type", "capability index must be PermissionWorldCapabilityIndexV1"
        )
    if evaluated < state.observed_at_ms:
        raise PermissionWorldError(
            "evaluation_before_observation",
            "evaluation time cannot precede the permission observation",
            "$.evaluated_at_ms",
        )

    affordances = tuple(
        _project_permission(
            permission,
            state.observed_at_ms,
            evaluated,
            motion,
            capability_index,
        )
        for permission in state.permissions
    )
    visible_world_states = tuple(
        sorted(
            item.surface_id
            for item in affordances
            if item.availability == "available"
            and item.surface_class == "world_state"
            and item.surface_id is not None
        )
    )
    visible_effects = tuple(
        sorted(
            item.surface_id
            for item in affordances
            if item.availability == "available"
            and item.surface_class == "effect"
            and item.surface_id is not None
        )
    )
    visible_props = tuple(
        sorted(
            item.surface_id
            for item in affordances
            if item.availability == "available"
            and item.surface_class == "prop"
            and item.surface_id is not None
        )
    )
    managed_world_states = (
        () if capability_index is None else capability_index.world_state_ids
    )
    managed_effects = () if capability_index is None else capability_index.effect_ids
    managed_props = () if capability_index is None else capability_index.prop_ids
    identity = {
        "schema_version": PERMISSION_WORLD_SCHEMA_VERSION,
        "source_epoch": state.source_epoch,
        "source_state_sha256": state.state_sha256,
        "source_observed_at_ms": state.observed_at_ms,
        "evaluated_at_ms": evaluated,
        "motion_profile": motion,
        "affordances": [item.to_dict() for item in affordances],
        "managed_world_states": list(managed_world_states),
        "managed_effects": list(managed_effects),
        "managed_props": list(managed_props),
        "visible_world_states": list(visible_world_states),
        "visible_effects": list(visible_effects),
        "visible_props": list(visible_props),
    }
    return PermissionWorldProjectionV1(
        PERMISSION_WORLD_SCHEMA_VERSION,
        state.source_epoch,
        state.state_sha256,
        state.observed_at_ms,
        evaluated,
        motion,
        affordances,
        managed_world_states,
        managed_effects,
        managed_props,
        visible_world_states,
        visible_effects,
        visible_props,
        sha256_ref(canonical_json_v1(identity)),
    )


class PermissionWorldRuntime:
    """Bounded single-writer holder for one verified permission-world state."""

    def __init__(
        self,
        *,
        retired_epoch_capacity: int = PERMISSION_WORLD_DEFAULT_RETIRED_EPOCH_CAPACITY,
    ) -> None:
        if (
            type(retired_epoch_capacity) is not int
            or not 1 <= retired_epoch_capacity <= PERMISSION_WORLD_MAX_RETIRED_EPOCH_CAPACITY
        ):
            raise PermissionWorldError(
                "invalid_capacity",
                "retired epoch capacity must be a bounded positive integer",
            )
        self._retired_epoch_capacity = retired_epoch_capacity
        self._lock = threading.RLock()
        self._writer_thread_id: Optional[int] = None
        self._current_state: Optional[PermissionWorldStateV1] = None
        self._retired_epochs: set[str] = set()
        self._accepted_count = 0
        self._rejected_count = 0
        self._replay_rejection_count = 0
        self._stale_rejection_count = 0
        self._tamper_rejection_count = 0
        self._last_rejection_code: Optional[str] = None

    @staticmethod
    def _verified_state(
        source: Union[
            PermissionWorldStateV1,
            Mapping[str, object],
            str,
            bytes,
        ]
    ) -> PermissionWorldStateV1:
        if type(source) is PermissionWorldStateV1:
            return PermissionWorldStateV1.from_mapping(source.to_dict())
        if isinstance(source, Mapping):
            return PermissionWorldStateV1.from_mapping(source)
        if type(source) in (str, bytes):
            return PermissionWorldStateV1.from_json(source)
        raise PermissionWorldError(
            "invalid_type", "state must be a V1 state, mapping, or JSON"
        )

    @staticmethod
    def _increment(value: int) -> int:
        return min(value + 1, MAX_SAFE_INTEGER)

    def _record_rejection(self, code: str) -> None:
        self._rejected_count = self._increment(self._rejected_count)
        self._last_rejection_code = code
        if code == "replayed_state":
            self._replay_rejection_count = self._increment(
                self._replay_rejection_count
            )
        if code in {
            "observation_conflict",
            "retired_source_epoch",
            "stale_observation",
        }:
            self._stale_rejection_count = self._increment(
                self._stale_rejection_count
            )
        if code in {"hash_mismatch", "invalid_hash"}:
            self._tamper_rejection_count = self._increment(
                self._tamper_rejection_count
            )

    def _claim_writer(self) -> None:
        writer = threading.get_ident()
        if self._writer_thread_id is None:
            self._writer_thread_id = writer
        elif self._writer_thread_id != writer:
            raise PermissionWorldError(
                "single_writer_violation",
                "permission state updates must use the owning writer",
            )

    def accept(
        self,
        source: Union[
            PermissionWorldStateV1,
            Mapping[str, object],
            str,
            bytes,
        ],
    ) -> PermissionWorldStateV1:
        """Verify and atomically accept a strictly newer authority observation."""

        with self._lock:
            try:
                self._claim_writer()
                state = self._verified_state(source)
                current = self._current_state
                if state.source_epoch in self._retired_epochs:
                    raise PermissionWorldError(
                        "retired_source_epoch",
                        "source epoch has been retired",
                        "$.source_epoch",
                    )
                if current is not None and state.source_epoch == current.source_epoch:
                    if state.observed_at_ms < current.observed_at_ms:
                        raise PermissionWorldError(
                            "stale_observation",
                            "observation predates the accepted state",
                            "$.observed_at_ms",
                        )
                    if state.observed_at_ms == current.observed_at_ms:
                        if state.state_sha256 == current.state_sha256:
                            raise PermissionWorldError(
                                "replayed_state",
                                "state observation has already been accepted",
                            )
                        raise PermissionWorldError(
                            "observation_conflict",
                            "one observation cannot identify multiple states",
                            "$.observed_at_ms",
                        )
                elif current is not None:
                    if state.observed_at_ms <= current.observed_at_ms:
                        raise PermissionWorldError(
                            "stale_observation",
                            "a new epoch must advance the observation time",
                            "$.observed_at_ms",
                        )
                    if len(self._retired_epochs) >= self._retired_epoch_capacity:
                        raise PermissionWorldError(
                            "retired_epoch_capacity",
                            "retired epoch capacity is exhausted",
                        )
                    self._retired_epochs.add(current.source_epoch)

                self._current_state = state
                self._accepted_count = self._increment(self._accepted_count)
                return PermissionWorldStateV1.from_mapping(state.to_dict())
            except PermissionWorldError as exc:
                self._record_rejection(exc.code)
                raise

    def accept_mapping(self, source: Mapping[str, object]) -> PermissionWorldStateV1:
        return self.accept(source)

    def accept_json(self, source: Union[str, bytes]) -> PermissionWorldStateV1:
        return self.accept(source)

    @property
    def current_state(self) -> Optional[PermissionWorldStateV1]:
        with self._lock:
            if self._current_state is None:
                return None
            return PermissionWorldStateV1.from_mapping(self._current_state.to_dict())

    def project(
        self,
        *,
        evaluated_at_ms: int,
        motion_profile: str,
        capability_index: Optional[PermissionWorldCapabilityIndexV1] = None,
    ) -> PermissionWorldProjectionV1:
        """Evaluate the accepted state using only the caller's explicit inputs."""

        with self._lock:
            state = self._current_state
        if state is None:
            raise PermissionWorldError(
                "state_unavailable", "no permission state has been accepted"
            )
        return project_permission_world(
            state,
            evaluated_at_ms=evaluated_at_ms,
            motion_profile=motion_profile,
            capability_index=capability_index,
        )

    def diagnostics(self) -> Mapping[str, object]:
        """Return bounded counters and opaque identities, never permission details."""

        with self._lock:
            state = self._current_state
            return {
                "status": "ready" if state is not None else "empty",
                "active_source_epoch_sha256": (
                    None
                    if state is None
                    else sha256_ref(state.source_epoch.encode("ascii"))
                ),
                "active_observed_at_ms": (
                    None if state is None else state.observed_at_ms
                ),
                "active_state_sha256": (
                    None if state is None else state.state_sha256
                ),
                "permission_count": (
                    0 if state is None else len(state.permissions)
                ),
                "accepted_count": self._accepted_count,
                "rejected_count": self._rejected_count,
                "replay_rejection_count": self._replay_rejection_count,
                "stale_rejection_count": self._stale_rejection_count,
                "tamper_rejection_count": self._tamper_rejection_count,
                "retired_epoch_count": len(self._retired_epochs),
                "retired_epoch_capacity": self._retired_epoch_capacity,
                "last_rejection_code": self._last_rejection_code,
            }


project_permission_world_v1 = project_permission_world


__all__ = [
    "APP_LINK_STATES",
    "AVAILABILITIES",
    "EXPIRY_CLASSES",
    "MOTION_PROFILES",
    "PERMISSION_POSTURES",
    "PERMISSION_WORLD_DEFAULT_RETIRED_EPOCH_CAPACITY",
    "PERMISSION_WORLD_MAX_PERMISSIONS",
    "PERMISSION_WORLD_MAX_RETIRED_EPOCH_CAPACITY",
    "PERMISSION_WORLD_MAX_SURFACES",
    "PERMISSION_WORLD_SCHEMA_VERSION",
    "PROJECTED_POSTURES",
    "REVOCATION_BEHAVIORS",
    "REASON_CODES",
    "SUPPORT_STATUSES",
    "SURFACE_CLASSES",
    "VISIBILITIES",
    "CapabilityPermissionV1",
    "PermissionAffordanceV1",
    "PermissionWorldCapabilityIndexV1",
    "PermissionWorldError",
    "PermissionWorldProjectionV1",
    "PermissionWorldRenderPolicyV1",
    "PermissionWorldRuntime",
    "PermissionWorldStateV1",
    "project_permission_world",
    "project_permission_world_v1",
]
