use crate::controller::{CommandResult, WizardAvatarController, WizardCommand};
use crate::state::WizardState;
use std::collections::{BTreeMap, VecDeque};
use std::time::Duration;

pub const MAX_CATCH_UP_STEPS: u32 = 8;
const STEP_SECONDS: f64 = 1.0 / 60.0;

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct AccumulatorAdvance {
    pub steps: u32,
    pub alpha: f32,
    pub dropped_seconds: f64,
}

#[derive(Clone, Debug, Default)]
pub struct SimulationAccumulator {
    accumulated_seconds: f64,
    dropped_seconds: f64,
}

impl SimulationAccumulator {
    #[must_use]
    pub fn advance(&mut self, elapsed: Duration) -> AccumulatorAdvance {
        self.accumulated_seconds += elapsed.as_secs_f64();
        let maximum = STEP_SECONDS * f64::from(MAX_CATCH_UP_STEPS);
        let dropped = (self.accumulated_seconds - maximum).max(0.0);
        if dropped > 0.0 {
            self.accumulated_seconds = maximum;
            self.dropped_seconds += dropped;
        }
        let steps = ((self.accumulated_seconds / STEP_SECONDS) + 1e-9).floor() as u32;
        let steps = steps.min(MAX_CATCH_UP_STEPS);
        self.accumulated_seconds -= f64::from(steps) * STEP_SECONDS;
        AccumulatorAdvance {
            steps,
            alpha: (self.accumulated_seconds / STEP_SECONDS).clamp(0.0, 1.0) as f32,
            dropped_seconds: self.dropped_seconds,
        }
    }
}

#[derive(Clone, Debug)]
pub struct RuntimeSnapshot {
    pub tick: u64,
    pub previous: WizardState,
    pub current: WizardState,
}

#[derive(Clone, Debug)]
struct ScheduledCommand {
    order: u64,
    command: WizardCommand,
}

#[derive(Clone, Debug)]
pub struct AvatarRuntime {
    controller: WizardAvatarController,
    previous: WizardState,
    current: WizardState,
    tick: u64,
    next_command_order: u64,
    scheduled: BTreeMap<u64, VecDeque<ScheduledCommand>>,
}

impl Default for AvatarRuntime {
    fn default() -> Self {
        Self::new(WizardAvatarController::default())
    }
}

impl AvatarRuntime {
    #[must_use]
    pub fn new(controller: WizardAvatarController) -> Self {
        let current = controller.current_state().clone();
        Self {
            controller,
            previous: current.clone(),
            current,
            tick: 0,
            next_command_order: 0,
            scheduled: BTreeMap::new(),
        }
    }

    #[must_use]
    pub const fn tick(&self) -> u64 {
        self.tick
    }

    #[must_use]
    pub fn current_state(&self) -> &WizardState {
        &self.current
    }

    #[must_use]
    pub fn snapshot(&self) -> RuntimeSnapshot {
        RuntimeSnapshot {
            tick: self.tick,
            previous: self.previous.clone(),
            current: self.current.clone(),
        }
    }

    pub fn schedule_command(&mut self, tick: u64, command: WizardCommand) {
        let scheduled = ScheduledCommand {
            order: self.next_command_order,
            command,
        };
        self.next_command_order += 1;
        self.scheduled.entry(tick).or_default().push_back(scheduled);
    }

    pub fn apply_command(&mut self, command: WizardCommand) -> CommandResult {
        self.schedule_command(self.tick, command);
        self.apply_commands_through(self.tick)
            .pop()
            .expect("the just-scheduled command must be applied")
    }

    pub fn step_tick(&mut self) {
        self.apply_commands_through(self.tick);
        self.previous = self.current.clone();
        self.controller.step_tick();
        self.tick += 1;
        self.current = self.controller.current_state().clone();
    }

    fn apply_commands_through(&mut self, tick: u64) -> Vec<CommandResult> {
        let due_ticks = self
            .scheduled
            .range(..=tick)
            .map(|(scheduled_tick, _)| *scheduled_tick)
            .collect::<Vec<_>>();
        let mut due = Vec::new();
        for due_tick in due_ticks {
            if let Some(mut commands) = self.scheduled.remove(&due_tick) {
                due.extend(commands.drain(..));
            }
        }
        due.sort_by_key(|scheduled| scheduled.order);

        let results = due
            .into_iter()
            .map(|scheduled| self.controller.apply_command(scheduled.command))
            .collect::<Vec<_>>();
        self.current = self.controller.current_state().clone();
        results
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn scheduled_commands_apply_on_their_exact_tick_in_order() {
        let mut runtime = AvatarRuntime::default();
        runtime.schedule_command(
            2,
            WizardCommand::new("expression", json!({"expression": "happy"})),
        );
        runtime.step_tick();
        runtime.step_tick();
        assert_eq!(runtime.current_state().expression.as_str(), "neutral");
        runtime.step_tick();
        assert_eq!(runtime.current_state().expression.as_str(), "happy");
    }

    #[test]
    fn accumulator_caps_catch_up_without_fractional_simulation_steps() {
        let mut accumulator = SimulationAccumulator::default();
        let advance = accumulator.advance(Duration::from_secs(2));
        assert_eq!(advance.steps, MAX_CATCH_UP_STEPS);
        assert!(advance.dropped_seconds > 1.8);
        assert!((0.0..=1.0).contains(&advance.alpha));
    }
}
