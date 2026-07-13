from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Optional, Tuple

from .commanding import CommandEnvelopeV1
from .control import ControlArbiter, ControlIntentV1
from .expressions import expression_mouth
from .gestures import channels_for_action, validate_action
from .locomotion import LocomotionController, SIMULATION_DT
from .models import CommandResult, DIRECTIONS, EXPRESSIONS, WizardCommand, WizardState
from .mouth import validate_mouth_shape
from .pathing import circle_points, figure_eight_points, validate_path, validate_world_point
from .reference_avatar import reference_pose_ids
from .prism_signals import PrismSignalParser
from .semantic_animation import map_prism_signal
from .views import rotate_direction


class WizardAvatarController:
    def __init__(
        self,
        available_pose_ids: Optional[Iterable[str]] = None,
        character_id: str = "asciline-wizard-v1",
    ) -> None:
        self.available_pose_ids = tuple(
            available_pose_ids if available_pose_ids is not None else reference_pose_ids()
        )
        if not self.available_pose_ids:
            raise ValueError("available_pose_ids must not be empty")
        self.character_id = character_id
        self.state = WizardState(character_id=character_id)
        self.locomotion = LocomotionController()
        self.control_arbiter = ControlArbiter()
        self.prism_signals = PrismSignalParser()
        self._time_accumulator = 0.0

    def current_state(self) -> WizardState:
        return self.state

    def advance(self, seconds: float) -> None:
        self._time_accumulator += max(0.0, seconds)
        while self._time_accumulator + 1e-12 >= SIMULATION_DT:
            self.advance_tick()
            self._time_accumulator -= SIMULATION_DT

    def advance_tick(self) -> None:
        self.state.simulation_tick += 1
        self.state.state_revision += 1
        self.state.animation_clip_tick += 1
        self.state.time_seconds = self.state.simulation_tick * SIMULATION_DT
        self.state.blink_phase = (self.state.blink_phase + SIMULATION_DT / 4.2) % 1.0
        self._update_timers()
        self.control_arbiter.expire(self.state.simulation_tick)
        lease = self.control_arbiter.active_lease
        if lease is None:
            self.state.control_source = None
            self.state.control_lease_id = None
            self.locomotion.step(self.state, SIMULATION_DT)
            self._step_flight(0.0, "keep")
            return
        intent = lease.intent
        self.state.control_source = lease.source_kind
        self.state.control_lease_id = lease.lease_id
        self.state.control_lease_generation = lease.generation
        self.locomotion.step_control(
            self.state,
            intent.move_x,
            intent.move_z,
            run=intent.run,
            dt=SIMULATION_DT,
        )
        if intent.face_x is not None and intent.face_z is not None:
            from .views import resolve_direction_from_velocity

            self.state.facing = resolve_direction_from_velocity(
                intent.face_x,
                intent.face_z,
                self.state.facing,
            )
        self._step_flight(intent.ascend, intent.mobility_request)

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
            self.state.speech_text = None
            self.state.mouth = expression_mouth(self.state.expression)
            if self.state.action == "speaking":
                self._set_action("idle", 0)

    def _set_action(self, action: str, duration_ms: int) -> None:
        validate_action(action)
        if action == "containment":
            self.state.speech_id = None
            self.state.speech_text = None
            self.state.speech_until = 0.0
            self.state.mouth = expression_mouth(self.state.expression)
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
        if pose_id not in self.available_pose_ids:
            raise ValueError(f"Unsupported pose: {pose_id}")
        duration_ms = max(0, int(payload.get("duration_ms", 900)))
        self.state.pose_override_id = pose_id
        self.state.pose_override_until = (
            self.state.time_seconds + duration_ms / 1000.0 if duration_ms else 0.0
        )

    def _cmd_control(self, payload: Dict[str, Any]) -> None:
        intent_payload = payload.get("intent", {})
        if not isinstance(intent_payload, dict):
            raise ValueError("control intent must be an object")
        source_kind = str(payload.get("source_kind", "keyboard"))
        priority_class = "demo" if source_kind == "demo" else "user"
        envelope = CommandEnvelopeV1(
            schema_version=1,
            command_id=str(payload.get("command_id", "control-{}".format(time.time_ns()))),
            source_id=str(payload.get("source_id", "browser-controller")),
            source_kind=source_kind,
            source_sequence=int(payload.get("source_sequence", 0)),
            source_epoch=str(payload.get("source_epoch", "browser-session")),
            kind="control_intent",
            payload=intent_payload,
            ttl_ms=int(payload.get("ttl_ms", 250)),
            lease_id=str(payload.get("lease_id", "browser-control")),
            priority_class=priority_class,
        )
        intent = ControlIntentV1.from_mapping(intent_payload)
        decision = self.control_arbiter.submit(
            envelope,
            intent,
            accepted_tick=self.state.simulation_tick,
        )
        if not decision.accepted:
            raise ValueError(decision.reason)
        if decision.active_lease is not None:
            self.state.control_source = decision.active_lease.source_kind
            self.state.control_lease_id = decision.active_lease.lease_id
            self.state.control_lease_generation = decision.active_lease.generation
        elif decision.released:
            self.state.control_source = None
            self.state.control_lease_id = None
        if intent.mobility_request == "takeoff" and not self.state.airborne:
            self.state.airborne = True
            self.state.flight_target_altitude = 1.8
            self.state.mobility_mode = "takeoff"
        elif intent.mobility_request == "land" and self.state.airborne:
            self.state.flight_target_altitude = 0.0
            self.state.mobility_mode = "landing"

    def _cmd_prism_signal(self, payload: Dict[str, Any]) -> None:
        signal = self.prism_signals.parse(payload, now_ms=int(time.time() * 1000))
        semantic_input = {
            "schema_version": 1,
            "classification": signal.classification,
            "kind": signal.kind,
            "emitted_at_ms": signal.emitted_at_ms,
            "ttl_ms": signal.ttl_ms,
            **dict(signal.payload),
        }
        intent = map_prism_signal(
            semantic_input,
            now_ms=int(time.time() * 1000),
            user_locomotion_active=self.control_arbiter.active_lease is not None,
        )
        self.state.semantic_signal_sequence = signal.source_sequence
        self.state.semantic_cue = intent.cue
        self.state.semantic_gesture = intent.gesture
        self.state.semantic_amplitude = intent.amplitude
        if intent.recognized:
            expression_map = {
                "attentive": "focused",
                "friendly": "happy",
                "curious": "surprised",
                "thoughtful": "thinking",
            }
            expression = expression_map.get(intent.expression, intent.expression)
            if expression in EXPRESSIONS:
                self.state.expression = expression
            advisory_actions = {
                "explain": "explaining",
                "point": "pointing",
                "think": "thinking",
                "cast": "magic_cast",
                "react": "reaction",
                "review": "thinking",
                "recall": "thinking",
                "question": "explaining",
                "reference": "pointing",
                "reorient": "explaining",
            }
            action = advisory_actions.get(intent.gesture)
            if action is not None and self.state.speech_id is None:
                self._set_action(action, min(1800, max(400, int(900 / max(0.5, intent.tempo)))))
            stage = signal.payload.get("stage") if signal.kind == "stage" else None
            if stage == "speaking" and self.state.speech_id is None:
                self.state.mouth = "open_small"
            elif intent.mouth_activity <= 0.05 and self.state.speech_id is None:
                self.state.mouth = expression_mouth(self.state.expression)

    def _cmd_speech_stop(self, payload: Dict[str, Any]) -> None:
        self.state.speech_id = None
        self.state.speech_text = None
        self.state.speech_until = 0.0
        self.state.mouth = expression_mouth(self.state.expression)
        if self.state.action == "speaking":
            self._set_action("idle", 0)

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
        self.state.speech_text = text
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
        self.__init__(self.available_pose_ids, self.character_id)

    def _step_flight(self, ascend: float, mobility_request: str) -> None:
        if mobility_request == "takeoff" and not self.state.airborne:
            self.state.airborne = True
            self.state.flight_target_altitude = max(1.8, self.state.altitude)
            self.state.mobility_mode = "takeoff"
        elif mobility_request == "land" and self.state.airborne:
            self.state.flight_target_altitude = 0.0
            self.state.mobility_mode = "landing"

        if self.state.airborne and abs(ascend) > 0.01:
            self.state.flight_target_altitude = max(
                0.6,
                min(3.8, self.state.flight_target_altitude + ascend * SIMULATION_DT * 2.2),
            )

        target = self.state.flight_target_altitude if self.state.airborne else 0.0
        error = target - self.state.altitude
        desired_velocity = max(-2.4, min(2.4, error * 3.0))
        velocity_delta = desired_velocity - self.state.vertical_velocity
        velocity_limit = 7.0 * SIMULATION_DT
        velocity_delta = max(-velocity_limit, min(velocity_limit, velocity_delta))
        self.state.vertical_velocity += velocity_delta
        self.state.altitude = max(0.0, self.state.altitude + self.state.vertical_velocity * SIMULATION_DT)

        if self.state.airborne and self.state.flight_target_altitude <= 0.0 and self.state.altitude <= 0.025:
            self.state.airborne = False
            self.state.altitude = 0.0
            self.state.vertical_velocity = 0.0
            self.state.mobility_mode = "grounded_idle"
        elif self.state.airborne and self.state.mobility_mode not in {"takeoff", "landing"}:
            speed = (self.state.velocity["x"] ** 2 + self.state.velocity["z"] ** 2) ** 0.5
            self.state.mobility_mode = "flight_travel" if speed > 0.08 else "hover"
        elif self.state.airborne and self.state.mobility_mode == "takeoff":
            if self.state.altitude >= self.state.flight_target_altitude * 0.82:
                self.state.mobility_mode = "hover"

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
