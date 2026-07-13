from __future__ import annotations

import math
from typing import Optional, Tuple

from .geometry import clamp
from .models import MovementState, PathState, WizardState
from .pathing import validate_path, validate_world_point
from .projection import WORLD_X_MAX, WORLD_X_MIN, WORLD_Z_FAR, WORLD_Z_NEAR
from .views import resolve_direction_from_velocity, step_direction_towards


SIMULATION_HZ = 60.0
SIMULATION_DT = 1.0 / SIMULATION_HZ
STRIDE_LENGTH = 0.85


class LocomotionController:
    def __init__(self, movement: Optional[MovementState] = None) -> None:
        self.movement = movement or MovementState()
        self.path = PathState()

    def sync_from_state(self, state: WizardState) -> None:
        self.movement.position_x = state.world_position["x"]
        self.movement.position_z = state.world_position["z"]
        self.movement.velocity_x = state.velocity["x"]
        self.movement.velocity_z = state.velocity["z"]

    def sync_to_state(self, state: WizardState) -> None:
        state.world_position["x"] = self.movement.position_x
        state.world_position["z"] = self.movement.position_z
        state.velocity["x"] = self.movement.velocity_x
        state.velocity["z"] = self.movement.velocity_z
        moving = math.hypot(self.movement.velocity_x, self.movement.velocity_z) > 0.01
        state.locomotion = "walking" if moving else "idle"
        if moving:
            target_facing = resolve_direction_from_velocity(
                self.movement.velocity_x,
                self.movement.velocity_z,
                state.facing,
            )
            state.facing = step_direction_towards(state.facing, target_facing)

    def move_to(self, x: float, z: float, speed: Optional[float] = None) -> None:
        validate_world_point(x, z)
        if speed is not None:
            if speed <= 0:
                raise ValueError("Speed must be positive")
            self.movement.speed = float(speed)
        self.movement.target_x = float(x)
        self.movement.target_z = float(z)
        self.path.active = False

    def move_relative(self, dx: float, dz: float, speed: Optional[float] = None) -> None:
        self.move_to(self.movement.position_x + dx, self.movement.position_z + dz, speed)

    def follow_path(self, points, loop: bool = False, speed: Optional[float] = None) -> None:
        valid = validate_path(points)
        if speed is not None:
            if speed <= 0:
                raise ValueError("Speed must be positive")
            self.movement.speed = float(speed)
        self.path.points = valid
        self.path.index = 0
        self.path.loop = bool(loop)
        self.path.active = True
        self.movement.target_x, self.movement.target_z = valid[0]

    def stop(self) -> None:
        self.movement.target_x = None
        self.movement.target_z = None
        self.path.active = False
        self.movement.velocity_x = 0.0
        self.movement.velocity_z = 0.0

    def step_control(
        self,
        state: WizardState,
        move_x: float,
        move_z: float,
        run: bool = False,
        dt: float = SIMULATION_DT,
    ) -> None:
        """Advance one fixed tick from direct controller input.

        Direct input owns planar motion for this tick, so any scripted target or
        path is released. Acceleration and deceleration remain identical to the
        point-to-point controller, which keeps keyboard and gamepad motion from
        snapping when a lease starts or expires.
        """

        self.sync_from_state(state)
        self.movement.target_x = None
        self.movement.target_z = None
        self.path.active = False
        before = (self.movement.position_x, self.movement.position_z)
        magnitude = math.hypot(move_x, move_z)
        if magnitude > 1.0:
            move_x /= magnitude
            move_z /= magnitude
            magnitude = 1.0
        if magnitude <= 1e-6:
            self._decelerate(dt)
        else:
            speed = (2.2 if run else 1.35) * magnitude
            desired_vx = move_x / magnitude * speed
            desired_vz = move_z / magnitude * speed
            delta_x = desired_vx - self.movement.velocity_x
            delta_z = desired_vz - self.movement.velocity_z
            delta = math.hypot(delta_x, delta_z)
            limit = self.movement.acceleration * (1.35 if run else 1.0) * dt
            if delta > limit:
                delta_x = delta_x / delta * limit
                delta_z = delta_z / delta * limit
            self.movement.velocity_x += delta_x
            self.movement.velocity_z += delta_z
            self.movement.position_x += self.movement.velocity_x * dt
            self.movement.position_z += self.movement.velocity_z * dt

        self.movement.position_x = clamp(self.movement.position_x, WORLD_X_MIN, WORLD_X_MAX)
        self.movement.position_z = clamp(self.movement.position_z, WORLD_Z_NEAR, WORLD_Z_FAR)
        after = (self.movement.position_x, self.movement.position_z)
        travelled = math.hypot(after[0] - before[0], after[1] - before[1])
        if travelled > 0:
            state.walk_phase = (state.walk_phase + travelled / STRIDE_LENGTH) % 1.0
        self.sync_to_state(state)
        if state.airborne:
            state.locomotion = "flying" if magnitude > 0.05 else "hovering"

    def step(self, state: WizardState, dt: float = SIMULATION_DT) -> None:
        self.sync_from_state(state)
        before = (self.movement.position_x, self.movement.position_z)
        target = None
        if self.movement.target_x is not None and self.movement.target_z is not None:
            target = (self.movement.target_x, self.movement.target_z)

        if target is None:
            self._decelerate(dt)
        else:
            self._move_toward_target(target, dt)
            if self._arrived(target):
                self.movement.position_x, self.movement.position_z = target
                self._advance_path_or_stop()

        self.movement.position_x = clamp(self.movement.position_x, WORLD_X_MIN, WORLD_X_MAX)
        self.movement.position_z = clamp(self.movement.position_z, WORLD_Z_NEAR, WORLD_Z_FAR)
        after = (self.movement.position_x, self.movement.position_z)
        travelled = math.hypot(after[0] - before[0], after[1] - before[1])
        if travelled > 0:
            state.walk_phase = (state.walk_phase + travelled / STRIDE_LENGTH) % 1.0
        self.sync_to_state(state)

    def _move_toward_target(self, target: Tuple[float, float], dt: float) -> None:
        dx = target[0] - self.movement.position_x
        dz = target[1] - self.movement.position_z
        dist = math.hypot(dx, dz)
        if dist < 1e-9:
            self.movement.velocity_x = 0.0
            self.movement.velocity_z = 0.0
            return
        desired_speed = self.movement.speed
        if dist < 0.45:
            desired_speed *= max(0.25, dist / 0.45)
        desired_vx = dx / dist * desired_speed
        desired_vz = dz / dist * desired_speed
        ax = desired_vx - self.movement.velocity_x
        az = desired_vz - self.movement.velocity_z
        accel_limit = self.movement.acceleration * dt
        delta = math.hypot(ax, az)
        if delta > accel_limit:
            ax = ax / delta * accel_limit
            az = az / delta * accel_limit
        self.movement.velocity_x += ax
        self.movement.velocity_z += az
        step_x = self.movement.velocity_x * dt
        step_z = self.movement.velocity_z * dt
        if math.hypot(step_x, step_z) > dist:
            self.movement.position_x, self.movement.position_z = target
        else:
            self.movement.position_x += step_x
            self.movement.position_z += step_z

    def _decelerate(self, dt: float) -> None:
        speed = math.hypot(self.movement.velocity_x, self.movement.velocity_z)
        if speed <= 1e-9:
            self.movement.velocity_x = 0.0
            self.movement.velocity_z = 0.0
            return
        new_speed = max(0.0, speed - self.movement.deceleration * dt)
        ratio = new_speed / speed if speed else 0.0
        self.movement.velocity_x *= ratio
        self.movement.velocity_z *= ratio
        self.movement.position_x += self.movement.velocity_x * dt
        self.movement.position_z += self.movement.velocity_z * dt

    def _arrived(self, target: Tuple[float, float]) -> bool:
        return math.hypot(target[0] - self.movement.position_x, target[1] - self.movement.position_z) <= self.movement.arrival_tolerance

    def _advance_path_or_stop(self) -> None:
        if not self.path.active:
            self.stop()
            return
        self.path.index += 1
        if self.path.index >= len(self.path.points):
            if self.path.loop:
                self.path.index = 0
            else:
                self.stop()
                return
        self.movement.target_x, self.movement.target_z = self.path.points[self.path.index]
