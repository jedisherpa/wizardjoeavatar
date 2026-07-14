use crate::state::{
    Action, ChannelGenerations, EffectState, Expression, Locomotion, StaffState, UpperBodyAction,
    WizardState,
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum InterruptPolicy {
    Immediate,
    HigherPriorityOnly,
    Finish,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EasingCurve {
    Linear,
    SmoothStep,
    CubicHermite,
    Inertialized,
}

#[derive(Clone, Debug)]
pub struct ChannelState<T>
where
    T: Copy + Eq,
{
    pub stable: T,
    pub target: T,
    pub generation: u64,
    pub expires_at_tick: Option<u64>,
    pub restore_to: Option<T>,
    pub blend: f32,
    started_tick: u64,
    duration_ticks: u16,
    expiry_generation: u64,
}

impl<T> ChannelState<T>
where
    T: Copy + Eq,
{
    #[must_use]
    pub fn new(value: T) -> Self {
        Self {
            stable: value,
            target: value,
            generation: 0,
            expires_at_tick: None,
            restore_to: None,
            blend: 1.0,
            started_tick: 0,
            duration_ticks: 0,
            expiry_generation: 0,
        }
    }

    pub fn interrupt(
        &mut self,
        target: T,
        tick: u64,
        duration_ticks: u16,
        expires_at_tick: Option<u64>,
        restore_to: Option<T>,
    ) {
        self.generation += 1;
        self.target = target;
        self.started_tick = tick;
        self.duration_ticks = duration_ticks;
        self.blend = if self.stable == target { 1.0 } else { 0.0 };
        self.expires_at_tick = expires_at_tick;
        self.restore_to = restore_to;
        self.expiry_generation = self.generation;
    }

    pub fn step(&mut self, tick: u64) {
        if self.stable != self.target {
            let elapsed = tick.saturating_sub(self.started_tick) as f32;
            let duration = f32::from(self.duration_ticks.max(1));
            let linear = (elapsed / duration).clamp(0.0, 1.0);
            self.blend = linear * linear * (3.0 - 2.0 * linear);
            if linear >= 1.0 {
                self.stable = self.target;
                self.blend = 1.0;
            }
        }

        let expires = self
            .expires_at_tick
            .is_some_and(|expiry| tick >= expiry && self.expiry_generation == self.generation);
        if expires {
            let restore = self.restore_to.unwrap_or(self.stable);
            self.interrupt(restore, tick, 6, None, None);
        }
    }
}

#[derive(Clone, Debug)]
pub struct AnimationChannels {
    pub upper_body: ChannelState<UpperBodyAction>,
    pub staff: ChannelState<StaffState>,
    pub expression: ChannelState<Expression>,
    pub speech: ChannelState<bool>,
    pub effects: ChannelState<EffectState>,
    locomotion_generation: u64,
    facing_generation: u64,
    blink_generation: u64,
}

impl Default for AnimationChannels {
    fn default() -> Self {
        Self {
            upper_body: ChannelState::new(UpperBodyAction::None),
            staff: ChannelState::new(StaffState::Held),
            expression: ChannelState::new(Expression::Neutral),
            speech: ChannelState::new(false),
            effects: ChannelState::new(EffectState::None),
            locomotion_generation: 0,
            facing_generation: 0,
            blink_generation: 0,
        }
    }
}

impl AnimationChannels {
    pub fn settle_safe_idle(&mut self, tick: u64) {
        self.upper_body
            .interrupt(UpperBodyAction::None, tick, 8, None, None);
        self.staff.interrupt(StaffState::Held, tick, 8, None, None);
        self.expression
            .interrupt(Expression::Neutral, tick, 4, None, None);
        self.speech.interrupt(false, tick, 1, None, None);
        self.effects
            .interrupt(EffectState::None, tick, 6, None, None);
        self.blink_generation = self.blink_generation.wrapping_add(1);
    }

    pub fn set_action(&mut self, action: Action, tick: u64, duration_ticks: u64) {
        let expiry = (duration_ticks > 0).then_some(tick + duration_ticks);
        let (upper, staff, effect) = channels_for_action(action);
        let (upper_restore, staff_restore) = if action == Action::Reaction {
            (Some(self.upper_body.target), Some(self.staff.target))
        } else {
            (Some(UpperBodyAction::None), Some(StaffState::Held))
        };
        self.upper_body
            .interrupt(upper, tick, 8, expiry, upper_restore);
        self.staff.interrupt(staff, tick, 8, expiry, staff_restore);
        self.effects
            .interrupt(effect, tick, 6, expiry, Some(EffectState::None));
    }

    pub fn start_speech(&mut self, tick: u64, duration_ticks: u64) {
        let expiry = Some(tick + duration_ticks.max(1));
        self.speech.interrupt(true, tick, 4, expiry, Some(false));
        if self.upper_body.target == UpperBodyAction::None {
            self.upper_body.interrupt(
                UpperBodyAction::Explain,
                tick,
                6,
                expiry,
                Some(UpperBodyAction::None),
            );
        }
    }

    pub fn set_expression(&mut self, expression: Expression, tick: u64) {
        self.expression.interrupt(expression, tick, 4, None, None);
    }

    pub fn note_locomotion_change(&mut self) {
        self.locomotion_generation += 1;
    }

    pub fn note_facing_change(&mut self) {
        self.facing_generation += 1;
    }

    pub fn step(&mut self, tick: u64, state: &mut WizardState) {
        self.upper_body.step(tick);
        self.staff.step(tick);
        self.expression.step(tick);
        self.speech.step(tick);
        self.effects.step(tick);

        state.previous_upper_body_action = self.upper_body.stable;
        state.upper_body_action = self.upper_body.target;
        state.previous_staff_state = self.staff.stable;
        state.staff_state = self.staff.target;
        state.expression = self.expression.target;
        state.effect_state = self.effects.target;
        state.upper_body_blend = self.upper_body.blend;
        state.staff_blend = self.staff.blend;
        state.action = action_from_channels(state, self.speech.target);
        state.channel_generations = ChannelGenerations {
            locomotion: self.locomotion_generation,
            facing: self.facing_generation,
            upper_body: self.upper_body.generation,
            staff: self.staff.generation,
            expression: self.expression.generation,
            blink: self.blink_generation,
            speech: self.speech.generation,
            effects: self.effects.generation,
        };
    }

    #[must_use]
    pub fn speech_active(&self) -> bool {
        self.speech.target
    }
}

fn action_from_channels(state: &WizardState, speech_active: bool) -> Action {
    match state.upper_body_action {
        UpperBodyAction::Explain => {
            if speech_active {
                Action::Speaking
            } else {
                Action::Explaining
            }
        }
        UpperBodyAction::Point => Action::Pointing,
        UpperBodyAction::Think => Action::Thinking,
        UpperBodyAction::Cast => Action::MagicCast,
        UpperBodyAction::React => Action::Reaction,
        UpperBodyAction::None if speech_active => Action::Speaking,
        UpperBodyAction::None if state.locomotion == Locomotion::Walking => Action::Walking,
        UpperBodyAction::None => Action::Idle,
    }
}

fn channels_for_action(action: Action) -> (UpperBodyAction, StaffState, EffectState) {
    match action {
        Action::Idle | Action::Walking => {
            (UpperBodyAction::None, StaffState::Held, EffectState::None)
        }
        Action::Speaking | Action::Explaining => (
            UpperBodyAction::Explain,
            StaffState::Held,
            EffectState::None,
        ),
        Action::Thinking => (UpperBodyAction::Think, StaffState::Held, EffectState::None),
        Action::Pointing => (UpperBodyAction::Point, StaffState::Point, EffectState::None),
        Action::MagicCast => (UpperBodyAction::Cast, StaffState::Cast, EffectState::Cast),
        Action::Reaction => (
            UpperBodyAction::React,
            StaffState::Held,
            EffectState::Reaction,
        ),
    }
}

#[must_use]
pub fn reference_pose_id_for_state(state: &WizardState) -> &'static str {
    match state.facing {
        crate::state::Direction::South => "front_idle",
        crate::state::Direction::SouthWest => "walk_front_left",
        crate::state::Direction::West => "profile_left",
        crate::state::Direction::NorthWest => "back_left",
        crate::state::Direction::North => "back_idle",
        crate::state::Direction::NorthEast => "back_right",
        crate::state::Direction::East => "profile_right",
        crate::state::Direction::SouthEast => "walk_front_right",
    }
}
