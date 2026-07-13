use crate::animation::AnimationChannels;
use crate::geometry::distance;
use crate::pathing::PathCurve;
use crate::pose_clip::PoseClipPlayback;
use crate::pose_playback::{PosePlayback, DEFAULT_POSE_TRANSITION_TICKS};
use crate::pose_program::is_authored_pose_id;
use crate::state::{
    Action, Direction, Expression, Locomotion, MouthShape, PlantedFoot, Velocity, WizardState,
    WorldPoint,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::f32::consts::{FRAC_PI_4, PI, TAU};
use std::str::FromStr;

pub const WORLD_X_MIN: f32 = -5.0;
pub const WORLD_X_MAX: f32 = 5.0;
pub const WORLD_Z_NEAR: f32 = 1.5;
pub const WORLD_Z_FAR: f32 = 10.0;
pub const SIMULATION_HZ: f32 = 60.0;
pub const SIMULATION_DT: f32 = 1.0 / SIMULATION_HZ;
pub const STRIDE_LENGTH: f32 = 0.85;

#[derive(Clone, Debug, Deserialize)]
pub struct WizardCommand {
    #[serde(rename = "type")]
    pub command_type: String,
    #[serde(default)]
    pub payload: Value,
}

impl WizardCommand {
    #[must_use]
    pub fn new(command_type: impl Into<String>, payload: Value) -> Self {
        Self {
            command_type: command_type.into(),
            payload,
        }
    }
}

#[derive(Clone, Debug, Serialize)]
pub struct CommandResult {
    pub ok: bool,
    pub message: String,
    pub state: WizardState,
}

#[derive(Clone, Copy, Debug)]
struct MovementState {
    target: Option<WorldPoint>,
    max_speed: f32,
    current_speed: f32,
    acceleration: f32,
    deceleration: f32,
    arrival_tolerance: f32,
    stop_speed: f32,
    desired_velocity: Velocity,
    desired_heading: f32,
    presented_heading: f32,
    candidate_direction: Option<Direction>,
    candidate_ticks: u8,
    explicit_heading: Option<f32>,
}

impl Default for MovementState {
    fn default() -> Self {
        Self {
            target: None,
            max_speed: 1.25,
            current_speed: 0.0,
            acceleration: 4.0,
            deceleration: 5.0,
            arrival_tolerance: 0.04,
            stop_speed: 0.05,
            desired_velocity: Velocity { x: 0.0, z: 0.0 },
            desired_heading: 0.0,
            presented_heading: 0.0,
            candidate_direction: None,
            candidate_ticks: 0,
            explicit_heading: None,
        }
    }
}

#[derive(Clone, Debug, Default)]
struct PathState {
    generation: u64,
    curve: Option<PathCurve>,
    pending_curve: Option<PathCurve>,
    distance_along: f32,
    speed: f32,
    looped: bool,
}

#[derive(Clone, Debug, Default)]
pub struct WizardAvatarController {
    state: WizardState,
    movement: MovementState,
    path: PathState,
    channels: AnimationChannels,
    pose_playback: PosePlayback,
    pose_clip: PoseClipPlayback,
}

impl WizardAvatarController {
    #[must_use]
    pub fn current_state(&self) -> &WizardState {
        &self.state
    }

    #[must_use]
    pub fn state_mut(&mut self) -> &mut WizardState {
        &mut self.state
    }

    pub fn advance(&mut self, seconds: f32) {
        let steps = (seconds.max(0.0) / SIMULATION_DT).round() as u64;
        for _ in 0..steps {
            self.step_tick();
        }
    }

    pub fn step_tick(&mut self) {
        self.state.simulation_tick += 1;
        self.state.time_seconds = self.state.simulation_tick as f32 * SIMULATION_DT;
        self.state.facing_blend = (self.state.facing_blend + 1.0 / 8.0).min(1.0);
        self.step_locomotion();
        update_facing_handoff(&mut self.state);
        self.channels
            .step(self.state.simulation_tick, &mut self.state);
        self.pose_clip.step(
            self.state.simulation_tick,
            &mut self.pose_playback,
            &mut self.state,
        );
        self.pose_playback
            .step(self.state.simulation_tick, &mut self.state);
        if !self.channels.speech_active() && self.state.speech_id.is_some() {
            self.state.speech_id = None;
            self.state.mouth = expression_mouth(self.state.expression);
        }
        self.state.blink_phase = blink_phase(self.state.time_seconds);
    }

    pub fn apply_command(&mut self, command: WizardCommand) -> CommandResult {
        let result = self.apply_command_inner(command);
        self.channels
            .step(self.state.simulation_tick, &mut self.state);
        match result {
            Ok(()) => CommandResult {
                ok: true,
                message: "ok".to_string(),
                state: self.state.clone(),
            },
            Err(message) => CommandResult {
                ok: false,
                message,
                state: self.state.clone(),
            },
        }
    }

    fn apply_command_inner(&mut self, command: WizardCommand) -> Result<(), String> {
        match command.command_type.as_str() {
            "move" => self.cmd_move(&command.payload),
            "move_relative" => self.cmd_move_relative(&command.payload),
            "path" => self.cmd_path(&command.payload),
            "circle" => self.cmd_circle(&command.payload),
            "figure_eight" | "figure-eight" => self.cmd_figure_eight(&command.payload),
            "face" => self.cmd_face(&command.payload),
            "action" => self.cmd_action(&command.payload),
            "pose" => self.cmd_pose(&command.payload),
            "pose_clip" => self.cmd_pose_clip(&command.payload),
            "expression" => self.cmd_expression(&command.payload),
            "speak" => self.cmd_speak(&command.payload),
            "mouth" => self.cmd_mouth(&command.payload),
            "stop" => {
                self.stop_locomotion();
                Ok(())
            }
            "reset" => {
                let reconnect_count = self.state.reconnect_count;
                *self = Self::default();
                self.state.reconnect_count = reconnect_count + 1;
                Ok(())
            }
            "return_to_center" => {
                self.move_to(WorldPoint { x: 0.0, z: 5.0 }, self.movement.max_speed)
            }
            "walk_left" => self.move_relative(-number(&command.payload, "distance", 1.5)?, 0.0),
            "walk_right" => self.move_relative(number(&command.payload, "distance", 1.5)?, 0.0),
            "walk_forward" => self.move_relative(0.0, -number(&command.payload, "distance", 1.5)?),
            "walk_backward" => self.move_relative(0.0, number(&command.payload, "distance", 1.5)?),
            other => Err(format!("unsupported command: {other}")),
        }
    }

    fn cmd_move(&mut self, payload: &Value) -> Result<(), String> {
        self.move_to(
            WorldPoint {
                x: number(payload, "x", 0.0)?,
                z: number(payload, "z", 5.0)?,
            },
            number(payload, "speed", self.movement.max_speed)?,
        )
    }

    fn cmd_move_relative(&mut self, payload: &Value) -> Result<(), String> {
        self.move_relative(number(payload, "dx", 0.0)?, number(payload, "dz", 0.0)?)
    }

    fn cmd_path(&mut self, payload: &Value) -> Result<(), String> {
        let mut points = payload
            .get("points")
            .and_then(Value::as_array)
            .ok_or_else(|| "path command requires points".to_string())?
            .iter()
            .map(|point| {
                let point = WorldPoint {
                    x: number(point, "x", 0.0)?,
                    z: number(point, "z", 5.0)?,
                };
                validate_world_point(point)?;
                Ok(point)
            })
            .collect::<Result<Vec<_>, String>>()?;
        if points.is_empty() {
            return Err("path must contain at least one point".to_string());
        }
        if world_distance(self.state.world_position, points[0]) > self.movement.arrival_tolerance {
            points.insert(0, self.state.world_position);
        }
        let curve = PathCurve::spline(&points)?;
        self.activate_curve(
            curve,
            number(payload, "speed", self.movement.max_speed)?,
            bool_value(payload, "loop", false),
        )
    }

    fn cmd_circle(&mut self, payload: &Value) -> Result<(), String> {
        let center = WorldPoint {
            x: number(payload, "center_x", 0.0)?,
            z: number(payload, "center_z", 5.0)?,
        };
        let radius = number(payload, "radius", 2.0)?;
        if radius <= 0.0 {
            return Err("circle radius must be positive".to_string());
        }
        validate_world_point(WorldPoint {
            x: center.x - radius,
            z: center.z - radius,
        })?;
        validate_world_point(WorldPoint {
            x: center.x + radius,
            z: center.z + radius,
        })?;
        let dx = self.state.world_position.x - center.x;
        let dz = self.state.world_position.z - center.z;
        let start_angle = if dx.abs() + dz.abs() > f32::EPSILON {
            dz.atan2(dx)
        } else {
            0.0
        };
        let curve = PathCurve::circle(
            center,
            radius,
            start_angle,
            bool_value(payload, "clockwise", true),
        );
        let duration = number(payload, "duration_seconds", 10.0)?.max(0.1);
        let speed = curve.total_length() / duration;
        self.prepare_curve(curve, speed, false)
    }

    fn cmd_figure_eight(&mut self, payload: &Value) -> Result<(), String> {
        let center = WorldPoint {
            x: number(payload, "center_x", 0.0)?,
            z: number(payload, "center_z", 5.0)?,
        };
        let radius = number(payload, "radius", 1.4)?;
        if radius <= 0.0 {
            return Err("figure-eight radius must be positive".to_string());
        }
        validate_world_point(WorldPoint {
            x: center.x - radius,
            z: center.z - radius * 0.5,
        })?;
        validate_world_point(WorldPoint {
            x: center.x + radius,
            z: center.z + radius * 0.5,
        })?;
        self.prepare_curve(
            PathCurve::figure_eight(center, radius),
            number(payload, "speed", self.movement.max_speed)?,
            bool_value(payload, "loop", false),
        )
    }

    fn cmd_face(&mut self, payload: &Value) -> Result<(), String> {
        let value = string(payload, "direction", "south")?;
        let direction = match value.as_str() {
            "left" => self.state.facing.rotate(1),
            "right" => self.state.facing.rotate(-1),
            other => Direction::from_str(other)?,
        };
        self.movement.explicit_heading = Some(heading_for_direction(direction));
        Ok(())
    }

    fn cmd_action(&mut self, payload: &Value) -> Result<(), String> {
        let action = Action::from_str(&string(payload, "action", "idle")?)?;
        let duration_ms = number(payload, "duration_ms", 1600.0)?.max(0.0) as u64;
        self.state.action_until = self.state.time_seconds + duration_ms as f32 / 1000.0;
        self.channels.set_action(
            action,
            self.state.simulation_tick,
            millis_to_ticks(duration_ms),
        );
        match action {
            Action::Idle => {
                self.pose_clip.clear(&mut self.state);
                let presented = self
                    .pose_playback
                    .presented_pose()
                    .map(str::to_owned)
                    .or_else(|| self.state.pose_id.clone());
                if let Some(presented) = presented {
                    self.pose_playback.return_to_direction(
                        pose_id_for_direction(self.state.facing),
                        presented,
                        self.state.simulation_tick,
                        DEFAULT_POSE_TRANSITION_TICKS,
                    );
                    self.pose_playback
                        .step(self.state.simulation_tick, &mut self.state);
                } else {
                    self.pose_playback.clear(&mut self.state);
                }
            }
            Action::Explaining => self.start_pose_clip("explain", false, None)?,
            Action::Thinking => self.start_pose_clip("think", false, None)?,
            Action::Pointing => self.start_pose_clip("point", false, None)?,
            Action::MagicCast => self.start_pose_clip("staff_combo", false, None)?,
            Action::Reaction => self.start_pose_clip("reaction_recover", false, None)?,
            Action::Speaking | Action::Walking => {}
        }
        Ok(())
    }

    fn cmd_pose(&mut self, payload: &Value) -> Result<(), String> {
        if payload.get("pose_id").is_none_or(Value::is_null) {
            self.pose_clip.clear(&mut self.state);
            self.pose_playback.clear(&mut self.state);
            return Ok(());
        }
        let pose_id = string(payload, "pose_id", "front_idle")?;
        if !is_authored_pose_id(&pose_id) {
            return Err(format!("unsupported pose: {pose_id}"));
        }
        let transition_ms = number(payload, "transition_ms", 240.0)?.max(1.0) as u64;
        let duration_ms = number(payload, "duration_ms", 0.0)?.max(0.0) as u64;
        let transition_ticks = millis_to_ticks(transition_ms).min(u64::from(u16::MAX)) as u16;
        let presented = self
            .pose_playback
            .presented_pose()
            .map(str::to_owned)
            .or_else(|| self.state.pose_id.clone())
            .unwrap_or_else(|| pose_id_for_direction(self.state.facing).to_string());
        let restore_to = payload
            .get("restore_pose_id")
            .and_then(Value::as_str)
            .map(str::to_owned)
            .or_else(|| (duration_ms > 0).then_some(presented.clone()));
        if let Some(restore) = restore_to.as_deref() {
            if !is_authored_pose_id(restore) {
                return Err(format!("unsupported restore pose: {restore}"));
            }
        }
        let expires_at_tick =
            (duration_ms > 0).then_some(self.state.simulation_tick + millis_to_ticks(duration_ms));
        self.pose_clip.clear(&mut self.state);
        self.pose_playback.interrupt(
            pose_id,
            presented,
            self.state.simulation_tick,
            transition_ticks,
            expires_at_tick,
            restore_to,
        );
        self.pose_playback
            .step(self.state.simulation_tick, &mut self.state);
        Ok(())
    }

    fn cmd_pose_clip(&mut self, payload: &Value) -> Result<(), String> {
        let clip_id = string(payload, "clip_id", "ground_walk")?;
        let looped = bool_value(payload, "loop", false);
        let restore_to = payload
            .get("restore_pose_id")
            .and_then(Value::as_str)
            .map(str::to_owned);
        if let Some(restore) = restore_to.as_deref() {
            if !is_authored_pose_id(restore) {
                return Err(format!("unsupported restore pose: {restore}"));
            }
        }
        self.start_pose_clip(&clip_id, looped, restore_to)
    }

    fn start_pose_clip(
        &mut self,
        clip_id: &str,
        looped: bool,
        restore_to: Option<String>,
    ) -> Result<(), String> {
        let presented = self
            .pose_playback
            .presented_pose()
            .map(str::to_owned)
            .or_else(|| self.state.pose_id.clone())
            .unwrap_or_else(|| pose_id_for_direction(self.state.facing).to_string());
        let (restore_to, restore_to_direction) = if restore_to.is_some() {
            (restore_to, false)
        } else if let Some(restoration) = self.pose_clip.restoration() {
            restoration
        } else if self.state.pose_id.is_some() {
            (Some(presented.clone()), false)
        } else {
            (None, true)
        };
        self.pose_clip.start(
            clip_id,
            presented.clone(),
            self.state.simulation_tick,
            looped,
            restore_to,
            restore_to_direction,
        )?;
        self.pose_clip.step(
            self.state.simulation_tick,
            &mut self.pose_playback,
            &mut self.state,
        );
        self.pose_playback
            .step(self.state.simulation_tick, &mut self.state);
        Ok(())
    }

    fn cmd_expression(&mut self, payload: &Value) -> Result<(), String> {
        let expression = Expression::from_str(&string(payload, "expression", "neutral")?)?;
        self.channels
            .set_expression(expression, self.state.simulation_tick);
        if self.state.speech_id.is_none() {
            self.state.mouth = expression_mouth(expression);
        }
        Ok(())
    }

    fn cmd_speak(&mut self, payload: &Value) -> Result<(), String> {
        let text = string(payload, "text", "The stars prefer a tidy spellbook.")?;
        let default_duration = (text.len() as f32 * 70.0).max(1200.0);
        let duration_ms = number(payload, "duration_ms", default_duration)? as u64;
        self.state.speech_id = Some(string(
            payload,
            "speech_id",
            &format!("speech-{}", self.state.simulation_tick),
        )?);
        self.state.speech_until = self.state.time_seconds + duration_ms as f32 / 1000.0;
        self.state.mouth = MouthShape::OpenSmall;
        self.channels
            .start_speech(self.state.simulation_tick, millis_to_ticks(duration_ms));
        Ok(())
    }

    fn cmd_mouth(&mut self, payload: &Value) -> Result<(), String> {
        self.state.mouth = MouthShape::from_str(&string(payload, "mouth", "closed")?)?;
        Ok(())
    }

    fn move_to(&mut self, point: WorldPoint, speed: f32) -> Result<(), String> {
        validate_world_point(point)?;
        if speed <= 0.0 {
            return Err("speed must be positive".to_string());
        }
        self.cancel_path();
        self.movement.max_speed = speed;
        self.movement.target = Some(point);
        self.state.target_point = Some(point);
        self.channels.note_locomotion_change();
        Ok(())
    }

    fn move_relative(&mut self, dx: f32, dz: f32) -> Result<(), String> {
        self.move_to(
            WorldPoint {
                x: self.state.world_position.x + dx,
                z: self.state.world_position.z + dz,
            },
            self.movement.max_speed,
        )
    }

    fn prepare_curve(&mut self, curve: PathCurve, speed: f32, looped: bool) -> Result<(), String> {
        if speed <= 0.0 {
            return Err("path speed must be positive".to_string());
        }
        let start = curve.sample(0.0).position;
        if world_distance(self.state.world_position, start) > self.movement.arrival_tolerance {
            self.cancel_path();
            self.path.pending_curve = Some(curve);
            self.path.speed = speed;
            self.path.looped = looped;
            self.movement.target = Some(start);
            self.state.target_point = Some(start);
            self.channels.note_locomotion_change();
            Ok(())
        } else {
            self.activate_curve(curve, speed, looped)
        }
    }

    fn activate_curve(&mut self, curve: PathCurve, speed: f32, looped: bool) -> Result<(), String> {
        if speed <= 0.0 {
            return Err("path speed must be positive".to_string());
        }
        self.path.generation += 1;
        self.path.curve = Some(curve);
        self.path.pending_curve = None;
        self.path.distance_along = 0.0;
        self.path.speed = speed;
        self.path.looped = looped;
        self.movement.target = None;
        self.movement.max_speed = speed;
        self.state.target_point = None;
        self.channels.note_locomotion_change();
        Ok(())
    }

    fn cancel_path(&mut self) {
        self.path.generation += 1;
        self.path.curve = None;
        self.path.pending_curve = None;
        self.path.distance_along = 0.0;
    }

    fn stop_locomotion(&mut self) {
        self.cancel_path();
        self.movement.target = None;
        self.movement.desired_velocity = Velocity { x: 0.0, z: 0.0 };
        self.state.target_point = None;
        self.channels.note_locomotion_change();
    }

    fn step_locomotion(&mut self) {
        let before = self.state.world_position;
        if self.path.curve.is_some() {
            self.step_curve();
        } else if let Some(target) = self.movement.target {
            self.step_arrival(target);
        } else {
            self.step_deceleration();
        }

        self.state.world_position.x = self.state.world_position.x.clamp(WORLD_X_MIN, WORLD_X_MAX);
        self.state.world_position.z = self.state.world_position.z.clamp(WORLD_Z_NEAR, WORLD_Z_FAR);
        let travelled = world_distance(before, self.state.world_position);
        if travelled > 0.0 {
            self.state.walk_phase = (self.state.walk_phase + travelled / STRIDE_LENGTH).fract();
        }
        self.state.contact_marker = crate::state::ContactMarker::from_phase(self.state.walk_phase);
        let speed = velocity_length(self.state.velocity);
        self.state.speed_ratio = (speed / self.movement.max_speed.max(0.001)).clamp(0.0, 1.0);
        let previous_locomotion = self.state.locomotion;
        self.state.locomotion = if speed > 0.01 {
            Locomotion::Walking
        } else {
            Locomotion::Idle
        };
        self.state.planted_foot = if self.state.locomotion == Locomotion::Walking {
            self.state.contact_marker.planted_foot()
        } else {
            PlantedFoot::Both
        };
        if self.state.locomotion != previous_locomotion {
            self.channels.note_locomotion_change();
        }
        self.step_heading(speed);
    }

    fn step_curve(&mut self) {
        let curve = self.path.curve.as_ref().expect("curve checked by caller");
        let total = curve.total_length();
        let remaining = (total - self.path.distance_along).max(0.0);
        let desired_speed = if self.path.looped {
            self.path.speed
        } else {
            self.path
                .speed
                .min((2.0 * self.movement.deceleration * remaining).sqrt())
        };
        self.movement.current_speed = move_towards_scalar(
            self.movement.current_speed,
            desired_speed,
            if desired_speed < self.movement.current_speed {
                self.movement.deceleration
            } else {
                self.movement.acceleration
            } * SIMULATION_DT,
        );
        let mut next_distance =
            self.path.distance_along + self.movement.current_speed * SIMULATION_DT;
        let finished = !self.path.looped && next_distance >= total;
        if self.path.looped && next_distance >= total {
            next_distance = next_distance.rem_euclid(total.max(f32::EPSILON));
        } else {
            next_distance = next_distance.min(total);
        }
        let sample = curve.sample(next_distance);
        self.path.distance_along = next_distance;
        self.state.world_position = sample.position;
        self.state.velocity = Velocity {
            x: sample.tangent.x * self.movement.current_speed,
            z: sample.tangent.z * self.movement.current_speed,
        };
        self.movement.desired_velocity = self.state.velocity;
        if finished {
            self.path.curve = None;
            self.movement.current_speed = 0.0;
            self.state.velocity = Velocity { x: 0.0, z: 0.0 };
            self.channels.note_locomotion_change();
        }
    }

    fn step_arrival(&mut self, target: WorldPoint) {
        let to_target = Velocity {
            x: target.x - self.state.world_position.x,
            z: target.z - self.state.world_position.z,
        };
        let remaining = velocity_length(to_target);
        if remaining <= f32::EPSILON {
            self.finish_arrival(target);
            return;
        }
        let braking_speed = (2.0
            * self.movement.deceleration
            * (remaining - self.movement.arrival_tolerance).max(0.0))
        .sqrt();
        let desired_speed = self.movement.max_speed.min(braking_speed);
        self.movement.desired_velocity = Velocity {
            x: to_target.x / remaining * desired_speed,
            z: to_target.z / remaining * desired_speed,
        };
        let rate = if desired_speed < velocity_length(self.state.velocity) {
            self.movement.deceleration
        } else {
            self.movement.acceleration
        };
        self.state.velocity = move_velocity_towards(
            self.state.velocity,
            self.movement.desired_velocity,
            rate * SIMULATION_DT,
        );
        self.movement.current_speed = velocity_length(self.state.velocity);
        let step = Velocity {
            x: self.state.velocity.x * SIMULATION_DT,
            z: self.state.velocity.z * SIMULATION_DT,
        };
        if velocity_length(step) >= remaining
            || (remaining <= self.movement.arrival_tolerance
                && self.movement.current_speed <= self.movement.stop_speed)
        {
            self.finish_arrival(target);
        } else {
            self.state.world_position.x += step.x;
            self.state.world_position.z += step.z;
        }
    }

    fn finish_arrival(&mut self, target: WorldPoint) {
        self.state.world_position = target;
        self.state.velocity = Velocity { x: 0.0, z: 0.0 };
        self.movement.current_speed = 0.0;
        self.movement.target = None;
        self.state.target_point = None;
        if let Some(curve) = self.path.pending_curve.take() {
            let _ = self.activate_curve(curve, self.path.speed, self.path.looped);
        } else {
            self.channels.note_locomotion_change();
        }
    }

    fn step_deceleration(&mut self) {
        self.state.velocity = move_velocity_towards(
            self.state.velocity,
            Velocity { x: 0.0, z: 0.0 },
            self.movement.deceleration * SIMULATION_DT,
        );
        self.movement.current_speed = velocity_length(self.state.velocity);
        self.state.world_position.x += self.state.velocity.x * SIMULATION_DT;
        self.state.world_position.z += self.state.velocity.z * SIMULATION_DT;
    }

    fn step_heading(&mut self, speed: f32) {
        if speed >= 0.08 {
            self.movement.desired_heading = self.state.velocity.x.atan2(-self.state.velocity.z);
            self.movement.explicit_heading = None;
        } else if let Some(explicit) = self.movement.explicit_heading {
            self.movement.desired_heading = explicit;
        } else {
            return;
        }
        let error = wrap_pi(self.movement.desired_heading - self.movement.presented_heading);
        let turn_rate = if speed >= 0.08 { TAU } else { PI * 1.5 };
        self.movement.presented_heading = wrap_pi(
            self.movement.presented_heading
                + error.clamp(-turn_rate * SIMULATION_DT, turn_rate * SIMULATION_DT),
        );
        if error.abs() < 0.001 {
            self.movement.explicit_heading = None;
        }
        self.state.desired_heading = self.movement.desired_heading;
        self.state.presented_heading = self.movement.presented_heading;

        let current_center = heading_for_direction(self.state.facing);
        let hysteresis = PI / 8.0 + 8.0_f32.to_radians();
        if wrap_pi(self.movement.presented_heading - current_center).abs() <= hysteresis {
            self.movement.candidate_direction = None;
            self.movement.candidate_ticks = 0;
        } else {
            let candidate = direction_from_heading(self.movement.presented_heading);
            if self.movement.candidate_direction == Some(candidate) {
                self.movement.candidate_ticks = self.movement.candidate_ticks.saturating_add(1);
            } else {
                self.movement.candidate_direction = Some(candidate);
                self.movement.candidate_ticks = 1;
            }
            if self.movement.candidate_ticks >= 2 && candidate != self.state.facing {
                self.state.previous_facing = self.state.facing;
                self.state.facing = adjacent_towards(self.state.facing, candidate);
                self.state.facing_blend = 0.0;
                self.state.facing_pose_handoff = self.state.locomotion != Locomotion::Walking;
                self.channels.note_facing_change();
                self.movement.candidate_direction = None;
                self.movement.candidate_ticks = 0;
            }
        }
        self.state.pending_direction = self.movement.candidate_direction;
        self.state.direction_candidate_ticks = self.movement.candidate_ticks;
    }
}

fn pose_id_for_direction(direction: Direction) -> &'static str {
    match direction {
        Direction::South => "front_idle",
        Direction::SouthWest => "walk_front_left",
        Direction::West => "profile_left",
        Direction::NorthWest => "back_left",
        Direction::North => "back_idle",
        Direction::NorthEast => "back_right",
        Direction::East => "profile_right",
        Direction::SouthEast => "walk_front_right",
    }
}

#[must_use]
pub fn expression_mouth(expression: Expression) -> MouthShape {
    match expression {
        Expression::Happy | Expression::Amused | Expression::Confident => MouthShape::Smile,
        Expression::Worried | Expression::Skeptical => MouthShape::Frown,
        Expression::Surprised => MouthShape::OpenWide,
        Expression::Thinking => MouthShape::Rounded,
        Expression::Explaining => MouthShape::OpenMedium,
        Expression::Neutral | Expression::Focused => MouthShape::Closed,
    }
}

#[must_use]
pub fn fallback_speech_shape(time_remaining: f32) -> MouthShape {
    match ((time_remaining.max(0.0) * 12.0).floor() as u32) % 4 {
        0 => MouthShape::OpenSmall,
        1 => MouthShape::OpenMedium,
        2 => MouthShape::Rounded,
        _ => MouthShape::OpenWide,
    }
}

#[must_use]
pub fn blink_state(time_seconds: f32) -> &'static str {
    let phase = time_seconds.rem_euclid(4.2);
    if phase < 0.07 {
        "closed"
    } else if phase < 0.14 {
        "half_closed"
    } else {
        "open"
    }
}

#[must_use]
pub fn blink_phase(time_seconds: f32) -> f32 {
    let phase = time_seconds.rem_euclid(4.2);
    if phase >= 0.14 {
        1.0
    } else {
        (phase / 0.14).clamp(0.0, 1.0)
    }
}

fn millis_to_ticks(milliseconds: u64) -> u64 {
    (milliseconds * 60).div_ceil(1000).max(1)
}

fn update_facing_handoff(state: &mut WizardState) {
    if !state.facing_pose_handoff
        && (state.locomotion != Locomotion::Walking
            || state.facing_blend >= 0.25
                && matches!(
                    state.contact_marker,
                    crate::state::ContactMarker::LeftHeelStrike
                        | crate::state::ContactMarker::RightHeelStrike
                ))
    {
        state.facing_pose_handoff = true;
    }
}

fn validate_world_point(point: WorldPoint) -> Result<(), String> {
    if !(WORLD_X_MIN..=WORLD_X_MAX).contains(&point.x) {
        return Err(format!("x must be between {WORLD_X_MIN} and {WORLD_X_MAX}"));
    }
    if !(WORLD_Z_NEAR..=WORLD_Z_FAR).contains(&point.z) {
        return Err(format!(
            "z must be between {WORLD_Z_NEAR} and {WORLD_Z_FAR}"
        ));
    }
    Ok(())
}

fn move_velocity_towards(current: Velocity, target: Velocity, max_delta: f32) -> Velocity {
    let delta = Velocity {
        x: target.x - current.x,
        z: target.z - current.z,
    };
    let length = velocity_length(delta);
    if length <= max_delta || length <= f32::EPSILON {
        target
    } else {
        Velocity {
            x: current.x + delta.x / length * max_delta,
            z: current.z + delta.z / length * max_delta,
        }
    }
}

fn move_towards_scalar(current: f32, target: f32, max_delta: f32) -> f32 {
    current + (target - current).clamp(-max_delta, max_delta)
}

fn velocity_length(value: Velocity) -> f32 {
    (value.x * value.x + value.z * value.z).sqrt()
}

fn world_distance(a: WorldPoint, b: WorldPoint) -> f32 {
    distance((a.x, a.z), (b.x, b.z))
}

fn wrap_pi(angle: f32) -> f32 {
    (angle + PI).rem_euclid(TAU) - PI
}

fn heading_for_direction(direction: Direction) -> f32 {
    match direction {
        Direction::South => 0.0,
        Direction::SouthEast => FRAC_PI_4,
        Direction::East => FRAC_PI_4 * 2.0,
        Direction::NorthEast => FRAC_PI_4 * 3.0,
        Direction::North => PI,
        Direction::NorthWest => -FRAC_PI_4 * 3.0,
        Direction::West => -FRAC_PI_4 * 2.0,
        Direction::SouthWest => -FRAC_PI_4,
    }
}

fn direction_from_heading(heading: f32) -> Direction {
    let sector = (wrap_pi(heading) / FRAC_PI_4).round() as i32;
    match sector.rem_euclid(8) {
        0 => Direction::South,
        1 => Direction::SouthEast,
        2 => Direction::East,
        3 => Direction::NorthEast,
        4 => Direction::North,
        5 => Direction::NorthWest,
        6 => Direction::West,
        _ => Direction::SouthWest,
    }
}

fn adjacent_towards(current: Direction, target: Direction) -> Direction {
    let current_index = Direction::ALL
        .iter()
        .position(|direction| *direction == current)
        .unwrap_or(0) as i32;
    let target_index = Direction::ALL
        .iter()
        .position(|direction| *direction == target)
        .unwrap_or(0) as i32;
    let clockwise = (target_index - current_index).rem_euclid(8);
    current.rotate(if clockwise <= 4 { 1 } else { -1 })
}

fn number(payload: &Value, key: &str, default: f32) -> Result<f32, String> {
    Ok(match payload.get(key) {
        Some(value) => value
            .as_f64()
            .ok_or_else(|| format!("{key} must be numeric"))? as f32,
        None => default,
    })
}

fn bool_value(payload: &Value, key: &str, default: bool) -> bool {
    payload.get(key).and_then(Value::as_bool).unwrap_or(default)
}

fn string(payload: &Value, key: &str, default: &str) -> Result<String, String> {
    Ok(match payload.get(key) {
        Some(value) => value
            .as_str()
            .ok_or_else(|| format!("{key} must be a string"))?
            .to_string(),
        None => default.to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn walking_updates_position_without_overshoot() {
        let mut controller = WizardAvatarController::default();
        let result =
            controller.apply_command(WizardCommand::new("move", json!({"x": 1.0, "z": 5.0})));
        assert!(result.ok);
        controller.advance(3.0);
        assert!((controller.current_state().world_position.x - 1.0).abs() < 0.001);
        assert_eq!(controller.current_state().locomotion, Locomotion::Idle);
    }

    #[test]
    fn speaking_does_not_cancel_walking() {
        let mut controller = WizardAvatarController::default();
        assert!(
            controller
                .apply_command(WizardCommand::new("move", json!({"x": 3.0, "z": 5.0})))
                .ok
        );
        assert!(
            controller
                .apply_command(WizardCommand::new(
                    "speak",
                    json!({"text": "hello", "duration_ms": 1000})
                ))
                .ok
        );
        controller.advance(0.25);
        assert_eq!(controller.current_state().locomotion, Locomotion::Walking);
        assert!(controller.current_state().speech_id.is_some());
    }

    #[test]
    fn facing_pose_handoff_waits_for_contact_and_never_reverts() {
        let mut state = WizardState {
            facing: Direction::East,
            previous_facing: Direction::SouthEast,
            facing_blend: 0.75,
            facing_pose_handoff: false,
            locomotion: Locomotion::Walking,
            contact_marker: crate::state::ContactMarker::RightPassing,
            ..WizardState::default()
        };
        update_facing_handoff(&mut state);
        assert!(!state.facing_pose_handoff);

        state.contact_marker = crate::state::ContactMarker::LeftHeelStrike;
        update_facing_handoff(&mut state);
        assert!(state.facing_pose_handoff);

        state.contact_marker = crate::state::ContactMarker::LeftPassing;
        update_facing_handoff(&mut state);
        assert!(state.facing_pose_handoff);
    }
}
