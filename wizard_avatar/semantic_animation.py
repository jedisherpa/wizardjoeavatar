from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple


SEMANTIC_ANIMATION_MAP_PATH = (
    Path(__file__).with_name("definitions") / "semantic_animation_map.json"
)
VISUAL_ADVISORY_CLASSIFICATION = "visual_advisory_only"
NEUTRAL_CUE = "none"


@dataclass(frozen=True)
class AnimationIntent:
    """Presentation-only guidance produced from a sanitized semantic signal.

    The type intentionally has no locomotion, world-target, approval, or execution
    field. Consumers may overlay it on animation channels, but cannot use it to
    replace user-owned movement or perform an operation.
    """

    cue: str = NEUTRAL_CUE
    expression: str = "neutral"
    gesture: str = "none"
    amplitude: float = 0.0
    tempo: float = 1.0
    mouth_activity: float = 0.0
    hold: bool = False
    allow_flourish: bool = False
    preserve_locomotion: bool = True
    priority: int = 0
    source_kind: str = "unknown"
    persona_style: Optional[str] = None
    amplitude_cap: Optional[float] = None
    clamps: Tuple[str, ...] = ()
    recognized: bool = False

    @property
    def is_noop(self) -> bool:
        return not self.recognized or self.cue == NEUTRAL_CUE

    def as_dict(self) -> Dict[str, Any]:
        return {
            "cue": self.cue,
            "expression": self.expression,
            "gesture": self.gesture,
            "amplitude": self.amplitude,
            "tempo": self.tempo,
            "mouth_activity": self.mouth_activity,
            "hold": self.hold,
            "allow_flourish": self.allow_flourish,
            "preserve_locomotion": self.preserve_locomotion,
            "priority": self.priority,
            "source_kind": self.source_kind,
            "persona_style": self.persona_style,
            "amplitude_cap": self.amplitude_cap,
            "clamps": list(self.clamps),
            "recognized": self.recognized,
        }


def _bounded_float(value: Any, lower: float, upper: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric" % name)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % name)
    return max(lower, min(upper, number))


def _normalized_token(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    token = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not token or len(token) > 64:
        return None
    if not all(character.isalnum() or character == "_" for character in token):
        return None
    return token


def _validate_map(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Semantic animation map must be a JSON object")
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported semantic animation map schema version")
    if payload.get("classification") != VISUAL_ADVISORY_CLASSIFICATION:
        raise ValueError("Semantic animation map must remain visual-advisory-only")

    profiles = payload.get("profiles")
    if not isinstance(profiles, dict) or NEUTRAL_CUE not in profiles:
        raise ValueError("Semantic animation map must define a neutral profile")
    required_profile_fields = {
        "expression",
        "gesture",
        "amplitude",
        "tempo",
        "mouth_activity",
        "hold",
        "allow_flourish",
        "priority",
    }
    for cue, profile in profiles.items():
        if _normalized_token(cue) != cue or not isinstance(profile, dict):
            raise ValueError("Invalid semantic animation profile")
        if not required_profile_fields.issubset(profile):
            raise ValueError("Profile %s is incomplete" % cue)
        _bounded_float(profile["amplitude"], 0.0, 1.0, "%s.amplitude" % cue)
        _bounded_float(profile["tempo"], 0.25, 2.0, "%s.tempo" % cue)
        _bounded_float(
            profile["mouth_activity"], 0.0, 1.0, "%s.mouth_activity" % cue
        )
        if not isinstance(profile["hold"], bool) or not isinstance(
            profile["allow_flourish"], bool
        ):
            raise ValueError("Profile %s boolean fields are invalid" % cue)
        if isinstance(profile["priority"], bool) or not isinstance(
            profile["priority"], int
        ):
            raise ValueError("Profile %s priority must be an integer" % cue)

    for table_name in (
        "stage_map",
        "kind_map",
        "terminal_posture_map",
        "continuity_map",
        "approval_map",
        "health_map",
    ):
        table = payload.get(table_name)
        if not isinstance(table, dict):
            raise ValueError("%s must be an object" % table_name)
        for token, rule in table.items():
            if _normalized_token(token) != token or not isinstance(rule, dict):
                raise ValueError("Invalid rule in %s" % table_name)
            if rule.get("cue") not in profiles:
                raise ValueError("Unknown cue in %s" % table_name)

    if not isinstance(payload.get("governance"), dict):
        raise ValueError("Semantic animation map is missing governance rules")
    if not isinstance(payload.get("persona_styles"), dict):
        raise ValueError("Semantic animation map is missing persona styles")
    if not isinstance(payload.get("forbidden_key_fragments"), list):
        raise ValueError("Semantic animation map is missing privacy boundaries")
    return payload


@lru_cache(maxsize=1)
def load_semantic_animation_map() -> Dict[str, Any]:
    with open(SEMANTIC_ANIMATION_MAP_PATH, "r", encoding="utf-8") as handle:
        return _validate_map(json.load(handle))


def _neutral(source_kind: str = "unknown") -> AnimationIntent:
    return AnimationIntent(source_kind=source_kind)


def _profile_intent(
    cue: str,
    source_kind: str,
    rule: Optional[Mapping[str, Any]] = None,
) -> AnimationIntent:
    config = load_semantic_animation_map()
    profile = config["profiles"][cue]
    amplitude = _bounded_float(profile["amplitude"], 0.0, 1.0, "amplitude")
    allow_flourish = bool(profile["allow_flourish"])
    amplitude_cap: Optional[float] = None
    if rule is not None:
        if "amplitude_cap" in rule:
            amplitude_cap = _bounded_float(
                rule["amplitude_cap"], 0.0, 1.0, "amplitude_cap"
            )
            amplitude = min(amplitude, amplitude_cap)
        if "allow_flourish" in rule:
            allow_flourish = bool(rule["allow_flourish"])
    return AnimationIntent(
        cue=cue,
        expression=str(profile["expression"]),
        gesture=str(profile["gesture"]),
        amplitude=amplitude,
        tempo=_bounded_float(profile["tempo"], 0.25, 2.0, "tempo"),
        mouth_activity=_bounded_float(
            profile["mouth_activity"], 0.0, 1.0, "mouth_activity"
        ),
        hold=bool(profile["hold"]),
        allow_flourish=allow_flourish,
        priority=int(profile["priority"]),
        source_kind=source_kind,
        amplitude_cap=amplitude_cap,
        recognized=True,
    )


def _forbidden_content(signal: Mapping[str, Any]) -> bool:
    fragments = tuple(load_semantic_animation_map()["forbidden_key_fragments"])
    for key, value in signal.items():
        normalized_key = str(key).strip().lower().replace("-", "_")
        if any(fragment in normalized_key for fragment in fragments):
            return True
        if normalized_key == "payload" and isinstance(value, Mapping):
            if _forbidden_content(value):
                return True
        elif isinstance(value, (Mapping, list, tuple, set)):
            return True
    return False


def _flatten_signal_payload(signal: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = signal.get("payload")
    if payload is None:
        return signal
    if not isinstance(payload, Mapping):
        return {}
    flattened = {key: value for key, value in signal.items() if key != "payload"}
    for key, value in payload.items():
        if key in flattened:
            return {}
        flattened[key] = value
    return flattened


def _is_stale(signal: Mapping[str, Any], now_ms: Optional[int]) -> bool:
    if signal.get("stale") is True or signal.get("expired") is True:
        return True
    ttl = signal.get("ttl_ms")
    emitted = signal.get("emitted_at_ms")
    if ttl is None and emitted is None:
        return False
    if isinstance(ttl, bool) or not isinstance(ttl, int) or ttl <= 0:
        return True
    if isinstance(emitted, bool) or not isinstance(emitted, int) or emitted < 0:
        return True
    return now_ms is not None and emitted + ttl <= now_ms


def _rule_for_signal(
    signal: Mapping[str, Any], kind: str
) -> Optional[Mapping[str, Any]]:
    config = load_semantic_animation_map()
    if kind == "stage":
        stage = _normalized_token(signal.get("stage"))
        return config["stage_map"].get(stage)
    if kind == "terminal_posture":
        posture = _normalized_token(signal.get("posture") or signal.get("terminal_posture"))
        return config["terminal_posture_map"].get(posture)
    if kind == "approval_posture":
        posture = _normalized_token(
            signal.get("posture") or signal.get("approval_state")
        )
        return config["approval_map"].get(posture)
    if kind == "continuity":
        continuity = _normalized_token(
            signal.get("continuity") or signal.get("posture")
        )
        return config["continuity_map"].get(continuity)
    if kind == "health":
        health = _normalized_token(
            signal.get("health") or signal.get("status") or signal.get("health_status")
        )
        return config["health_map"].get(health)
    return config["kind_map"].get(kind)


def _enum_value(signal: Mapping[str, Any], *names: str) -> Optional[str]:
    for name in names:
        value = _normalized_token(signal.get(name))
        if value is not None:
            return value
    return None


def _apply_governance(
    intent: AnimationIntent, signal: Mapping[str, Any]
) -> AnimationIntent:
    config = load_semantic_animation_map()
    rules = config["governance"]
    approval_names = ["approval_state", "approval_posture"]
    if intent.source_kind == "approval_posture":
        approval_names.append("posture")
    approval = _enum_value(signal, *approval_names)
    safety = _enum_value(signal, "safety", "safety_posture", "governance_posture")
    seriousness = _enum_value(signal, "seriousness", "risk_level")
    health = _enum_value(signal, "health", "health_status", "status")

    clamps = list(intent.clamps)
    caps = [intent.amplitude_cap] if intent.amplitude_cap is not None else []
    replacement: Optional[AnimationIntent] = None

    if approval in rules["approval_states"]:
        replacement = _profile_intent("wait", intent.source_kind)
        replacement = replace(replacement, priority=int(rules["approval_priority"]))
        caps.append(float(rules["approval_cap"]))
        clamps.append("approval")
    if safety in rules["safety_states"]:
        caps.append(float(rules["safety_cap"]))
        clamps.append("safety")
        if safety in rules["safety_hold_states"]:
            replacement = _profile_intent("wait", intent.source_kind)
            replacement = replace(replacement, priority=int(rules["safety_priority"]))
    if seriousness in rules["serious_states"]:
        caps.append(float(rules["serious_cap"]))
        clamps.append("serious")
    if health in rules["degraded_states"]:
        caps.append(float(rules["degraded_cap"]))
        clamps.append("degraded")
        if replacement is None:
            replacement = _profile_intent("degraded", intent.source_kind)
            replacement = replace(replacement, priority=int(rules["degraded_priority"]))

    governed = replacement if replacement is not None else intent
    amplitude_cap = min(caps) if caps else governed.amplitude_cap
    amplitude = governed.amplitude
    if amplitude_cap is not None:
        amplitude = min(amplitude, amplitude_cap)
    if clamps:
        return replace(
            governed,
            amplitude=amplitude,
            mouth_activity=0.0 if "degraded" in clamps else governed.mouth_activity,
            allow_flourish=False,
            amplitude_cap=amplitude_cap,
            clamps=tuple(dict.fromkeys(clamps)),
        )
    return governed


def _apply_persona_style(intent: AnimationIntent, style: str) -> AnimationIntent:
    style_rules = load_semantic_animation_map()["persona_styles"].get(style)
    if style_rules is None:
        return _neutral(intent.source_kind)
    amplitude_scale = _bounded_float(
        style_rules["amplitude_scale"], 0.5, 1.25, "amplitude_scale"
    )
    tempo_scale = _bounded_float(
        style_rules["tempo_scale"], 0.5, 1.25, "tempo_scale"
    )
    amplitude = min(1.0, intent.amplitude * amplitude_scale)
    if intent.amplitude_cap is not None:
        amplitude = min(amplitude, intent.amplitude_cap)
    return replace(
        intent,
        amplitude=amplitude,
        tempo=max(0.25, min(2.0, intent.tempo * tempo_scale)),
        persona_style=style,
    )


def map_signal_to_animation_intent(
    signal: Mapping[str, Any],
    *,
    now_ms: Optional[int] = None,
    user_locomotion_active: bool = False,
) -> AnimationIntent:
    """Map one sanitized Prism-shaped mapping to bounded presentation intent.

    ``user_locomotion_active`` is accepted at the ownership boundary so callers
    can be explicit. It never changes the result: semantic intent is always an
    overlay and always preserves user locomotion.
    """

    del user_locomotion_active
    if not isinstance(signal, Mapping):
        return _neutral()
    if _forbidden_content(signal) or _is_stale(signal, now_ms):
        return _neutral()
    raw_schema_version = signal.get("schema_version")
    if raw_schema_version in (2, "2", "2.0") and not isinstance(
        signal.get("payload"), Mapping
    ):
        return _neutral()
    signal = _flatten_signal_payload(signal)
    if not signal:
        return _neutral()
    kind = _normalized_token(signal.get("kind")) or "unknown"
    classification = signal.get("classification")
    if classification is not None and classification != VISUAL_ADVISORY_CLASSIFICATION:
        return _neutral()
    schema_version = signal.get("schema_version")
    if schema_version is not None and schema_version not in (
        1,
        2,
        "1",
        "1.0",
        "2",
        "2.0",
    ):
        return _neutral()

    rule = _rule_for_signal(signal, kind)
    if rule is None:
        return _neutral()
    intent = _profile_intent(str(rule["cue"]), kind, rule)

    if kind == "persona_style":
        style = _enum_value(signal, "style", "persona_style")
        if style is None:
            return _neutral()
        intent = _apply_persona_style(intent, style)

    return _apply_governance(intent, signal)


def arbitrate_animation_intents(
    intents: Iterable[AnimationIntent],
    *,
    user_locomotion_active: bool = False,
) -> AnimationIntent:
    """Choose one advisory cue and compose only restrictive/shared modifiers."""

    del user_locomotion_active
    candidates = [intent for intent in intents if intent.recognized]
    if not candidates:
        return _neutral()

    substantive = [intent for intent in candidates if intent.cue != "persona_style"]
    pool = substantive or candidates
    winner = max(enumerate(pool), key=lambda item: (item[1].priority, -item[0]))[1]

    caps = [
        intent.amplitude_cap
        for intent in candidates
        if intent.amplitude_cap is not None
    ]
    clamps = tuple(
        dict.fromkeys(clamp for intent in candidates for clamp in intent.clamps)
    )
    amplitude_cap = min(caps) if caps else winner.amplitude_cap
    amplitude = winner.amplitude
    if amplitude_cap is not None:
        amplitude = min(amplitude, amplitude_cap)
    result = replace(
        winner,
        amplitude=amplitude,
        allow_flourish=winner.allow_flourish and not clamps,
        amplitude_cap=amplitude_cap,
        clamps=clamps,
        preserve_locomotion=True,
    )

    style_intents = [
        intent for intent in candidates if intent.persona_style is not None
    ]
    if style_intents:
        result = _apply_persona_style(result, style_intents[-1].persona_style or "")
    return result


# A concise alias for adapters that already identify their source as Prism.
map_prism_signal = map_signal_to_animation_intent
