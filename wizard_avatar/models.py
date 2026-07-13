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

    def reconcile_compatibility_state(self) -> None:
        """Keep legacy action fields consistent with authoritative locomotion."""

        if self.action == "walking" and self.locomotion != "walking":
            self.action = "idle"
            self.upper_body_action = "none"
            self.staff_state = "held"
            self.action_until = 0.0
            self.action_restore = None

    def as_public_dict(self) -> Dict[str, Any]:
        self.reconcile_compatibility_state()
        return asdict(self)


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
