from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


DIRECTIONS = (
    "south",
    "southwest",
    "west",
    "northwest",
    "north",
    "northeast",
    "east",
    "southeast",
)

EXPRESSIONS = (
    "neutral",
    "happy",
    "thinking",
    "surprised",
    "worried",
    "amused",
    "confident",
    "focused",
    "skeptical",
    "explaining",
)

ACTIONS = (
    "idle",
    "speaking",
    "explaining",
    "walking",
    "dash",
    "thinking",
    "pointing",
    "magic_cast",
    "reaction",
    "guard",
    "block",
    "flourish",
    "staff_spin",
    "victory_cast",
    "shush",
    "celebrate",
    "staff_forward",
    "hit",
)

MOUTH_SHAPES = (
    "closed",
    "open_small",
    "open_medium",
    "open_wide",
    "rounded",
    "smile",
    "frown",
)

UPPER_BODY_ACTIONS = (
    "none",
    "explain",
    "point",
    "think",
    "cast",
    "react",
    "guard",
    "block",
    "flourish",
    "shush",
    "celebrate",
    "staff_forward",
)
STAFF_STATES = ("held", "point", "cast", "rest", "guard", "spin")


@dataclass(frozen=True)
class Cell:
    glyph: str
    rgb: Tuple[int, int, int]
    layer_id: str = ""

    def to_bytes(self) -> bytes:
        return bytes((ord(self.glyph[0]), self.rgb[0], self.rgb[1], self.rgb[2]))


@dataclass
class MovementState:
    position_x: float = 0.0
    position_z: float = 5.0
    velocity_x: float = 0.0
    velocity_z: float = 0.0
    target_x: Optional[float] = None
    target_z: Optional[float] = None
    speed: float = 1.25
    acceleration: float = 4.0
    deceleration: float = 5.0
    turn_speed_degrees: float = 360.0
    arrival_tolerance: float = 0.05


@dataclass
class PathState:
    points: List[Tuple[float, float]] = field(default_factory=list)
    index: int = 0
    loop: bool = False
    active: bool = False


@dataclass
class CircleState:
    center_x: float = 0.0
    center_z: float = 5.0
    radius: float = 2.0
    clockwise: bool = True
    duration_seconds: float = 10.0
    elapsed_seconds: float = 0.0
    active: bool = False


@dataclass
class WizardState:
    character_id: str = "asciline-wizard-v1"
    world_position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "z": 5.0})
    velocity: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "z": 0.0})
    facing: str = "south"
    facing_changed_tick: int = 0
    locomotion: str = "idle"
    action: str = "idle"
    upper_body_action: str = "none"
    expression: str = "neutral"
    mouth: str = "closed"
    walk_phase: float = 0.0
    blink_phase: float = 0.0
    staff_state: str = "held"
    speech_id: Optional[str] = None
    speech_text: Optional[str] = None
    time_seconds: float = 0.0
    action_until: float = 0.0
    action_restore: Optional[Dict[str, Any]] = None
    speech_until: float = 0.0
    target_point: Optional[Dict[str, float]] = None
    gaze_aim: int = 0
    gaze_vertical_aim: int = 0
    gaze_authoritative: bool = False
    screen_position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    display_scale: float = 1.0
    pose_id: str = "front_idle"
    last_pose_id: str = "front_idle"
    pose_transition_progress: float = 1.0
    pose_override_id: Optional[str] = None
    pose_override_until: float = 0.0
    reconnect_count: int = 0
    simulation_tick: int = 0
    state_revision: int = 0
    animation_clip_id: str = "idle_front"
    animation_clip_tick: int = 0
    animation_node_id: str = "ground_idle"
    animation_transition_id: Optional[str] = None
    mobility_mode: str = "grounded_idle"
    airborne: bool = False
    altitude: float = 0.0
    vertical_velocity: float = 0.0
    flight_target_altitude: float = 0.0
    control_source: Optional[str] = None
    control_lease_id: Optional[str] = None
    control_lease_generation: int = 0
    semantic_cue: str = "none"
    semantic_gesture: str = "none"
    semantic_amplitude: float = 0.0
    semantic_signal_sequence: int = 0
    semantic_advisory_active: bool = False
    semantic_turn_id: Optional[str] = None
    semantic_utterance_id: Optional[str] = None
    semantic_expires_at_ms: Optional[int] = None
    semantic_transition: str = "inactive"
    semantic_release_reason: Optional[str] = None

    def set_facing(self, facing: str) -> None:
        """Record facing changes on the authoritative simulation timeline."""

        if facing not in DIRECTIONS:
            raise ValueError("facing must be one of DIRECTIONS")
        if facing != self.facing:
            self.facing = facing
            self.facing_changed_tick = self.simulation_tick

    def reconcile_compatibility_state(self) -> None:
        """Keep legacy action fields consistent with authoritative locomotion."""

        if self.action == "walking" and self.locomotion != "walking":
            self.action = "idle"
            self.upper_body_action = "none"
            self.staff_state = "held"
            self.action_until = 0.0
            self.action_restore = None

    def as_public_dict(self) -> Dict[str, Any]:
        public = asdict(self)
        if public["action"] == "walking" and public["locomotion"] != "walking":
            public["action"] = "idle"
            public["upper_body_action"] = "none"
            public["staff_state"] = "held"
            public["action_until"] = 0.0
            public["action_restore"] = None
        return public


@dataclass(frozen=True)
class WizardPresentationState:
    screen_x: float
    screen_y: float
    display_scale: float
    pose_id: str
    last_pose_id: str
    pose_transition_progress: float
    animation_clip_id: str
    animation_node_id: str
    animation_transition_id: Optional[str]
    presented_facing: str
    gaze_aim: int
    head_eye_phase: str


@dataclass
class WizardCommand:
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    issued_at: Optional[float] = None


@dataclass
class CommandResult:
    ok: bool
    message: str = "ok"
    state: Optional[Dict[str, Any]] = None


@dataclass
class WizardCellFrame:
    cols: int
    rows: int
    frame_index: int
    cells: bytes
    raw_size: int
    changed_cells: int = 0
    codec_tag: int = 0
    encoded_size: int = 0
    is_keyframe: bool = False


@dataclass(frozen=True)
class StageProfile:
    name: str
    cols: int
    rows: int
    fps: float


PROFILES = {
    "low": StageProfile("low", 180, 101, 15.0),
    "medium": StageProfile("medium", 240, 135, 24.0),
    "high": StageProfile("high", 320, 180, 30.0),
}
