"""Pure validation for content-free Prism connector lifecycle receipts."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


LIFECYCLE_RECEIPT_SCHEMA = "character_director_prism_connector_lifecycle_v1"
LIFECYCLE_ACCEPTANCE_SCHEMA = (
    "character_director_prism_connector_lifecycle_acceptance_v1"
)

_FORBIDDEN_PRIVATE_KEYS = frozenset(
    {
        "approved_text",
        "argv",
        "command",
        "messages",
        "private_text",
        "prompt",
        "speech_text",
        "stderr",
        "stdout",
        "text",
        "transcript",
    }
)
_NON_OPEN_MOUTHS = frozenset({"", "closed", "idle", "neutral", "none"})
_REJECTED_STALE_DISPOSITIONS = frozenset(
    {"duplicate", "rejected", "resync_required", "stale"}
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _integer(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _private_paths(value: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = "{}.{}".format(path, key)
            if str(key).lower() in _FORBIDDEN_PRIVATE_KEYS:
                violations.append(child_path)
            violations.extend(_private_paths(child, child_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            violations.extend(_private_paths(child, "{}[{}]".format(path, index)))
    return violations


def _phase_ready(phase: Mapping[str, Any], slot: str) -> bool:
    browser = _mapping(phase.get("browser"))
    wizard = _mapping(phase.get("wizard"))
    media = _mapping(phase.get("media"))
    return bool(
        phase.get("source_slot") == slot
        and browser.get("playing") is True
        and wizard.get("active") is True
        and wizard.get("source_slot") == slot
        and isinstance(media.get("media_id"), str)
        and isinstance(media.get("media_sha256"), str)
        and isinstance(media.get("connector_session_sha256"), str)
    )


def evaluate_connector_lifecycle_receipt(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a deterministic acceptance report without reading external state."""

    phases = _mapping(receipt.get("phases"))
    main_before = _mapping(phases.get("main_before"))
    speech = _mapping(phases.get("speech"))
    main_after = _mapping(phases.get("main_after"))
    reconnect = _mapping(receipt.get("reconnect"))
    stale_replay = _mapping(receipt.get("stale_replay"))
    thresholds = _mapping(receipt.get("thresholds"))

    maximum_clock_offset_ms = _integer(thresholds.get("maximum_clock_offset_ms"))
    reconnect_limit_ms = _integer(thresholds.get("reconnect_recovery_limit_ms"))
    private_paths = _private_paths(receipt)

    ordered_times = [
        _integer(phase.get("observed_monotonic_ms"))
        for phase in (main_before, speech, main_after)
    ]
    phase_ordered = all(value is not None for value in ordered_times) and bool(
        ordered_times[0] < ordered_times[1] < ordered_times[2]  # type: ignore[operator]
    )

    before_media = _mapping(main_before.get("media"))
    after_media = _mapping(main_after.get("media"))
    before_browser = _mapping(main_before.get("browser"))
    after_browser = _mapping(main_after.get("browser"))
    before_position = _integer(before_browser.get("position_ms"))
    after_position = _integer(after_browser.get("position_ms"))
    main_continued = bool(
        before_media.get("media_id") == after_media.get("media_id")
        and before_media.get("media_sha256") == after_media.get("media_sha256")
        and before_media.get("connector_session_sha256")
        == after_media.get("connector_session_sha256")
        and before_position is not None
        and after_position is not None
        and after_position > before_position
    )

    speech_wizard = _mapping(speech.get("wizard"))
    speech_media = _mapping(speech.get("media"))
    speech_mouth = str(speech_wizard.get("mouth") or "").lower()
    speech_authorized = bool(
        _phase_ready(speech, "speech")
        and speech_wizard.get("speech_mouth_authority") == "media_alignment"
        and speech_mouth not in _NON_OPEN_MOUTHS
        and _integer(speech.get("visible_character_count")) is not None
        and speech_media.get("connector_session_sha256")
        == before_media.get("connector_session_sha256")
    )

    offsets = []
    for phase in (main_before, speech, main_after):
        value = _integer(phase.get("absolute_clock_offset_ms"))
        if value is not None:
            offsets.append(value)
    clocks_within_budget = bool(
        maximum_clock_offset_ms is not None
        and maximum_clock_offset_ms >= 0
        and len(offsets) == 3
        and max(offsets) <= maximum_clock_offset_ms
    )

    before_epoch = reconnect.get("before_runtime_epoch")
    after_epoch = reconnect.get("after_runtime_epoch")
    recovery_ms = _integer(reconnect.get("recovery_ms"))
    reconnect_proved = bool(
        isinstance(before_epoch, str)
        and isinstance(after_epoch, str)
        and before_epoch != after_epoch
        and recovery_ms is not None
        and reconnect_limit_ms is not None
        and 0 <= recovery_ms <= reconnect_limit_ms
        and reconnect.get("reconnect_cause_observed") is True
        and reconnect.get("main_restored") is True
        and reconnect.get("obsolete_speech_inactive") is True
    )

    stale_rejected = bool(
        stale_replay.get("disposition") in _REJECTED_STALE_DISPOSITIONS
        and stale_replay.get("main_remained_active") is True
        and stale_replay.get("obsolete_speech_inactive") is True
    )

    checks = (
        (
            "schema_identity",
            receipt.get("schema") == LIFECYCLE_RECEIPT_SCHEMA
            and receipt.get("schema_version") == 1,
        ),
        ("content_free", receipt.get("content_free") is True and not private_paths),
        ("ordered_main_speech_main", phase_ordered),
        ("main_before_active", _phase_ready(main_before, "main")),
        ("speech_authorized_with_open_mouth", speech_authorized),
        ("main_after_active", _phase_ready(main_after, "main")),
        ("main_identity_continued_and_advanced", main_continued),
        ("clock_offsets_within_budget", clocks_within_budget),
        ("runtime_reconnected_within_budget", reconnect_proved),
        ("stale_speech_replay_rejected", stale_rejected),
    )
    check_records = [
        {"name": name, "passed": passed} for name, passed in checks
    ]
    return {
        "schema": LIFECYCLE_ACCEPTANCE_SCHEMA,
        "schema_version": 1,
        "passed": all(record["passed"] for record in check_records),
        "checks": check_records,
        "metrics": {
            "maximum_observed_clock_offset_ms": max(offsets) if offsets else None,
            "main_advance_ms": (
                after_position - before_position
                if before_position is not None and after_position is not None
                else None
            ),
            "reconnect_recovery_ms": recovery_ms,
            "privacy_violation_count": len(private_paths),
        },
        "privacy_violation_paths": private_paths,
    }
