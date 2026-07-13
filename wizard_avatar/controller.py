from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Tuple

from .expressions import expression_mouth
from .gestures import channels_for_action, validate_action
from .locomotion import LocomotionController, SIMULATION_DT
from .models import CommandResult, DIRECTIONS, EXPRESSIONS, WizardCommand, WizardState
from .mouth import validate_mouth_shape
from .pathing import circle_points, figure_eight_points, validate_path, validate_world_point
from .reference_avatar import reference_pose_ids
from .views import rotate_direction


class WizardAvatarController:
    def __init__(self) -> None:
        self.state = WizardState()
        self.locomotion = LocomotionController()

    def current_state(self) -> WizardState:
        return self.state

    def advance(self, seconds: float) -> None:
        remaining = max(0.0, seconds)
        while remaining > 1e-9:
            dt = min(SIMULATION_DT, remaining)
            self.state.time_seconds += dt
            self._update_timers()
            self.locomotion.step(self.state, dt)
            remaining -= dt

    def apply_command(self, command: WizardCommand) -> CommandResult:
        try:
            handler = getattr(self, f"_cmd_{command.type}", None)
            if handler is None:
                raise ValueError(f"Unsupported command: {command.type}")
            handler(command.payload)
            return CommandResult(True, "ok", self.state.as_public_dict())
        except ValueError as exc:
            return CommandResult(False, str(exc), self.state.as_public_dict())

    def _update_timers(self) -> None:
        if self.state.pose_override_id is not None and self.state.pose_override_until:
            if self.state.time_seconds >= self.state.pose_override_until:
                self.state.pose_override_id = None
                self.state.pose_override_until = 0.0
        if self.state.action != "idle" and self.state.action_until and self.state.time_seconds >= self.state.action_until:
            if self.state.action == "reaction" and self.state.action_restore:
                self._restore_action_after_reaction()
            else:
                self._set_action("idle", 0)
        if self.state.speech_id is not None and self.state.time_seconds >= self.state.speech_until:
            self.state.speech_id = None
            self.state.mouth = expression_mouth(self.state.expression)
            if self.state.action == "speaking":
                self._set_action("idle", 0)

    def _set_action(self, action: str, duration_ms: int) -> None:
        validate_action(action)
        if action == "reaction" and self.state.action not in {"idle", "reaction"}:
            self.state.action_restore = {
                "action": self.state.action,
                "upper_body_action": self.state.upper_body_action,
                "staff_state": self.state.staff_state,
                "action_until": self.state.action_until,
            }
        elif action != "reaction":
            self.state.action_restore = None
        upper, staff = channels_for_action(action)
        self.state.action = action
        self.state.upper_body_action = upper
        self.state.staff_state = staff
        self.state.action_until = (
            self.state.time_seconds + max(0, duration_ms) / 1000.0 if duration_ms else 0.0
        )
        if action == "walking":
            self.state.locomotion = "walking"

    def _restore_action_after_reaction(self) -> None:
        restore = self.state.action_restore or {}
        restore_until = float(restore.get("action_until") or 0.0)
        if restore_until and self.state.time_seconds >= restore_until:
            self._set_action("idle", 0)
            return
        self.state.action = str(restore.get("action", "idle"))
        self.state.upper_body_action = str(restore.get("upper_body_action", "none"))
        self.state.staff_state = str(restore.get("staff_state", "held"))
        self.state.action_until = restore_until
        self.state.action_restore = None

    def _cmd_move(self, payload: Dict[str, Any]) -> None:
        x = float(payload["x"])
        z = float(payload["z"])
        speed = float(payload.get("speed", self.locomotion.movement.speed))
        self.locomotion.move_to(x, z, speed)
        self._set_action("walking", 0)
        self.state.target_point = {"x": x, "z": z}

    def _cmd_move_relative(self, payload: Dict[str, Any]) -> None:
        dx = float(payload.get("dx", 0.0))
        dz = float(payload.get("dz", 0.0))
        speed = float(payload.get("speed", self.locomotion.movement.speed))
        self.locomotion.move_relative(dx, dz, speed)
        self._set_action("walking", 0)

    def _cmd_path(self, payload: Dict[str, Any]) -> None:
        points = [
            (float(point["x"]), float(point["z"]))
            for point in payload.get("points", [])
        ]
        speed = float(payload.get("speed", self.locomotion.movement.speed))
        loop = bool(payload.get("loop", False))
        self.locomotion.follow_path(validate_path(points), loop=loop, speed=speed)
        self._set_action("walking", 0)

    def _cmd_circle(self, payload: Dict[str, Any]) -> None:
        center_x = float(payload.get("center_x", 0.0))
        center_z = float(payload.get("center_z", 5.0))
        radius = float(payload.get("radius", 2.0))
        clockwise = bool(payload.get("clockwise", True))
        duration = float(payload.get("duration_seconds", 10.0))
        points = circle_points(center_x, center_z, radius, clockwise)
        speed = max(0.1, (6.283185307179586 * radius) / max(duration, 0.1))
        self.locomotion.follow_path(points, loop=False, speed=speed)
        self._set_action("walking", 0)

    def _cmd_figure_eight(self, payload: Dict[str, Any]) -> None:
        points = figure_eight_points(
            float(payload.get("center_x", 0.0)),
            float(payload.get("center_z", 5.0)),
            float(payload.get("radius", 1.4)),
        )
        self.locomotion.follow_path(points, loop=False, speed=float(payload.get("speed", 1.25)))
        self._set_action("walking", 0)

    def _cmd_face(self, payload: Dict[str, Any]) -> None:
        direction = str(payload["direction"])
        if direction == "left":
            direction = rotate_direction(self.state.facing, 1)
        elif direction == "right":
            direction = rotate_direction(self.state.facing, -1)
        if direction not in DIRECTIONS:
            raise ValueError(f"Unsupported direction: {direction}")
        self.state.facing = direction

    def _cmd_action(self, payload: Dict[str, Any]) -> None:
        action = str(payload["action"])
        duration_ms = int(payload.get("duration_ms", 1600))
        self._set_action(action, duration_ms)

    def _cmd_pose(self, payload: Dict[str, Any]) -> None:
        pose_id = payload.get("pose_id")
        if pose_id is None:
            self.state.pose_override_id = None
            self.state.pose_override_until = 0.0
            return
        pose_id = str(pose_id)
        if pose_id not in reference_pose_ids():
            raise ValueError(f"Unsupported pose: {pose_id}")
        duration_ms = max(0, int(payload.get("duration_ms", 900)))
        self.state.pose_override_id = pose_id
        self.state.pose_override_until = (
            self.state.time_seconds + duration_ms / 1000.0 if duration_ms else 0.0
        )

    def _cmd_expression(self, payload: Dict[str, Any]) -> None:
        expression = str(payload["expression"])
        if expression not in EXPRESSIONS:
            raise ValueError(f"Unsupported expression: {expression}")
        self.state.expression = expression
        if self.state.speech_id is None:
            self.state.mouth = expression_mouth(expression)

    def _cmd_speak(self, payload: Dict[str, Any]) -> None:
        text = str(payload.get("text", "The stars prefer a tidy spellbook."))
        duration_ms = int(payload.get("duration_ms", max(1200, len(text) * 70)))
        self.state.speech_id = str(payload.get("speech_id", f"speech-{int(time.time() * 1000)}"))
        self.state.speech_until = self.state.time_seconds + duration_ms / 1000.0
        self.state.mouth = "open_small"
        if self.state.action in {"idle", "speaking"}:
            self.state.action = "speaking"
            self.state.upper_body_action = "explain"
            self.state.staff_state = "held"
            self.state.action_until = 0.0

    def _cmd_mouth(self, payload: Dict[str, Any]) -> None:
        shape = str(payload["mouth"])
        validate_mouth_shape(shape)
        self.state.mouth = shape

    def _cmd_stop(self, payload: Dict[str, Any]) -> None:
        self.locomotion.stop()
        self.state.target_point = None
        self.state.velocity["x"] = 0.0
        self.state.velocity["z"] = 0.0
        self.state.locomotion = "idle"
        self._set_action("idle", 0)

    def _cmd_reset(self, payload: Dict[str, Any]) -> None:
        self.__init__()

    def _cmd_return_to_center(self, payload: Dict[str, Any]) -> None:
        self.locomotion.move_to(0.0, 5.0, float(payload.get("speed", 1.25)))
        self._set_action("walking", 0)

    def _cmd_walk_left(self, payload: Dict[str, Any]) -> None:
        self._cmd_move_relative({"dx": -float(payload.get("distance", 1.5)), "dz": 0.0, **payload})

    def _cmd_walk_right(self, payload: Dict[str, Any]) -> None:
        self._cmd_move_relative({"dx": float(payload.get("distance", 1.5)), "dz": 0.0, **payload})

    def _cmd_walk_forward(self, payload: Dict[str, Any]) -> None:
        self._cmd_move_relative({"dx": 0.0, "dz": -float(payload.get("distance", 1.5)), **payload})

    def _cmd_walk_backward(self, payload: Dict[str, Any]) -> None:
        self._cmd_move_relative({"dx": 0.0, "dz": float(payload.get("distance", 1.5)), **payload})
