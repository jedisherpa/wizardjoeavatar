use crate::controller::{CommandResult, WizardAvatarController, WizardCommand};
use crate::state::WizardState;
use std::collections::{BTreeMap, VecDeque};
use std::sync::Arc;

#[derive(Clone, Debug)]
pub struct RuntimeSnapshot {
    pub tick: u64,
    pub previous: Arc<WizardState>,
    pub current: Arc<WizardState>,
}

#[derive(Clone, Debug)]
struct ScheduledCommand {
    order: u64,
    command: WizardCommand,
}

#[derive(Clone, Debug)]
pub struct AvatarRuntime {
    controller: WizardAvatarController,
    previous: Arc<WizardState>,
    current: Arc<WizardState>,
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
        let current = Arc::new(controller.current_state().clone());
        Self {
            controller,
            previous: Arc::clone(&current),
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
        self.current.as_ref()
    }

    #[must_use]
    pub fn snapshot(&self) -> RuntimeSnapshot {
        RuntimeSnapshot {
            tick: self.tick,
            previous: Arc::clone(&self.previous),
            current: Arc::clone(&self.current),
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
        self.previous = Arc::clone(&self.current);
        self.controller.step_tick();
        self.tick += 1;
        self.current = Arc::new(self.controller.current_state().clone());
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
        self.current = Arc::new(self.controller.current_state().clone());
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
}
