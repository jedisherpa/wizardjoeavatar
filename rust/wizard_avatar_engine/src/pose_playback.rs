use crate::pose::transition_ticks_for;
use crate::state::WizardState;

pub const DEFAULT_POSE_TRANSITION_TICKS: u16 = 14;

#[derive(Clone, Debug)]
struct PendingPose {
    target: String,
    transition_ticks: u16,
    expires_after_ticks: Option<u64>,
    restore_to: Option<String>,
    clear_after: bool,
}

#[derive(Clone, Debug, Default)]
pub struct PosePlayback {
    current: Option<String>,
    previous: Option<String>,
    restore_to: Option<String>,
    started_tick: u64,
    duration_ticks: u16,
    handoff: bool,
    expires_at_tick: Option<u64>,
    generation: u64,
    pending: Option<PendingPose>,
    clear_after_tick: Option<u64>,
}

impl PosePlayback {
    /// Presents an authored whole-frame key immediately.
    ///
    /// This is reserved for exact raster animation cycles whose source cadence
    /// must not be lengthened or visually blended by the general transition
    /// scheduler.
    pub fn cut(&mut self, target: impl Into<String>, tick: u64) {
        let target = target.into();
        self.generation = self.generation.wrapping_add(1);
        self.current = Some(target.clone());
        self.previous = Some(target);
        self.restore_to = None;
        self.started_tick = tick;
        self.duration_ticks = 1;
        self.handoff = true;
        self.expires_at_tick = None;
        self.pending = None;
        self.clear_after_tick = None;
    }

    pub fn interrupt(
        &mut self,
        target: impl Into<String>,
        presented: impl Into<String>,
        tick: u64,
        transition_ticks: u16,
        expires_at_tick: Option<u64>,
        restore_to: Option<String>,
    ) {
        self.queue_or_begin(
            target.into(),
            presented.into(),
            tick,
            transition_ticks,
            expires_at_tick,
            restore_to,
            false,
        );
    }

    pub fn return_to_direction(
        &mut self,
        target: impl Into<String>,
        presented: impl Into<String>,
        tick: u64,
        transition_ticks: u16,
    ) {
        self.queue_or_begin(
            target.into(),
            presented.into(),
            tick,
            transition_ticks,
            None,
            None,
            true,
        );
    }

    #[allow(clippy::too_many_arguments)]
    fn queue_or_begin(
        &mut self,
        target: String,
        presented: String,
        tick: u64,
        transition_ticks: u16,
        expires_at_tick: Option<u64>,
        restore_to: Option<String>,
        clear_after: bool,
    ) {
        let transition_ticks = transition_ticks_for(&presented, &target, transition_ticks);
        let pending = PendingPose {
            target,
            transition_ticks,
            expires_after_ticks: expires_at_tick.map(|expiry| expiry.saturating_sub(tick)),
            restore_to,
            clear_after,
        };
        if self.transition_active_at(tick) {
            self.pending = Some(pending);
            return;
        }
        self.begin_interrupt(pending, presented, tick, expires_at_tick);
    }

    fn begin_interrupt(
        &mut self,
        pending: PendingPose,
        presented: String,
        tick: u64,
        expires_at_tick: Option<u64>,
    ) {
        let PendingPose {
            target,
            transition_ticks,
            restore_to,
            clear_after,
            ..
        } = pending;
        self.generation = self.generation.wrapping_add(1);
        self.previous = Some(presented);
        self.current = Some(target);
        self.restore_to = restore_to;
        self.started_tick = tick;
        self.duration_ticks = transition_ticks.max(1);
        self.handoff = false;
        self.expires_at_tick = expires_at_tick;
        self.clear_after_tick = clear_after.then_some(tick + u64::from(self.duration_ticks));
    }

    fn transition_active_at(&self, tick: u64) -> bool {
        self.current != self.previous
            && self.current.is_some()
            && tick.saturating_sub(self.started_tick) < u64::from(self.duration_ticks.max(1))
    }

    pub fn clear(&mut self, state: &mut WizardState) {
        *self = Self::default();
        state.pose_id = None;
        state.previous_pose_id = None;
        state.pose_blend = 1.0;
        state.pose_handoff = true;
        state.pose_generation = 0;
        state.pose_expires_at_tick = None;
    }

    pub fn step(&mut self, tick: u64, state: &mut WizardState) {
        if self
            .clear_after_tick
            .is_some_and(|clear_tick| tick > clear_tick)
        {
            self.clear(state);
            return;
        }
        let Some(current) = self.current.clone() else {
            state.pose_id = None;
            state.previous_pose_id = None;
            state.pose_blend = 1.0;
            state.pose_handoff = true;
            state.pose_generation = self.generation;
            state.pose_expires_at_tick = None;
            return;
        };

        if self.expires_at_tick.is_some_and(|expiry| tick >= expiry) {
            self.expires_at_tick = None;
            if let Some(restore) = self.restore_to.take() {
                let presented = self
                    .presented_pose()
                    .unwrap_or(current.as_str())
                    .to_string();
                self.interrupt(
                    restore,
                    presented,
                    tick,
                    DEFAULT_POSE_TRANSITION_TICKS,
                    None,
                    None,
                );
            }
        }

        let elapsed = tick.saturating_sub(self.started_tick) as f32;
        let linear = if self.current == self.previous {
            1.0
        } else {
            (elapsed / f32::from(self.duration_ticks.max(1))).clamp(0.0, 1.0)
        };
        let blend = linear * linear * (3.0 - 2.0 * linear);
        let handoff = linear >= 0.5;
        self.handoff = handoff;
        if linear >= 1.0 {
            self.previous = self.current.clone();
            if let Some(pending) = self.pending.take() {
                let expires_at_tick = pending.expires_after_ticks.map(|duration| tick + duration);
                self.begin_interrupt(pending, current, tick, expires_at_tick);
                self.step(tick, state);
                return;
            }
        }

        state.pose_id = self.current.clone();
        state.previous_pose_id = self.previous.clone();
        state.pose_blend = blend;
        state.pose_handoff = handoff;
        state.pose_generation = self.generation;
        state.pose_expires_at_tick = self.expires_at_tick;
    }

    #[must_use]
    pub fn presented_pose(&self) -> Option<&str> {
        if self.handoff || self.current == self.previous {
            self.current.as_deref()
        } else {
            self.previous.as_deref().or(self.current.as_deref())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn transition_keeps_whole_source_until_the_handoff() {
        let mut playback = PosePlayback::default();
        let mut state = WizardState::default();
        playback.interrupt("target", "source", 10, 10, None, None);
        playback.step(14, &mut state);
        assert_eq!(state.previous_pose_id.as_deref(), Some("source"));
        assert_eq!(state.pose_id.as_deref(), Some("target"));
        assert!(!state.pose_handoff);
        playback.step(15, &mut state);
        assert!(state.pose_handoff);
    }

    #[test]
    fn expiry_restores_without_allowing_a_stale_target_to_reappear() {
        let mut playback = PosePlayback::default();
        let mut state = WizardState::default();
        playback.interrupt("reaction", "idle", 0, 4, Some(8), Some("idle".to_string()));
        playback.step(8, &mut state);
        assert_eq!(state.pose_id.as_deref(), Some("idle"));
        assert_eq!(state.pose_generation, 2);
        playback.interrupt("cast", "idle", 9, 4, Some(20), Some("idle".to_string()));
        playback.step(12, &mut state);
        assert_eq!(state.pose_id.as_deref(), Some("cast"));
    }

    #[test]
    fn replacement_waits_for_the_in_progress_handoff_without_resetting_it() {
        let mut playback = PosePlayback::default();
        let mut state = WizardState::default();
        playback.interrupt("first", "idle", 0, 10, None, None);
        playback.step(6, &mut state);
        let blend = state.pose_blend;
        playback.interrupt("replacement", "first", 6, 10, None, None);
        playback.step(6, &mut state);
        assert_eq!(state.pose_id.as_deref(), Some("first"));
        assert_eq!(state.pose_blend, blend);
        playback.step(10, &mut state);
        assert_eq!(state.pose_id.as_deref(), Some("replacement"));
        assert_eq!(state.previous_pose_id.as_deref(), Some("first"));
        assert_eq!(state.pose_blend, 0.0);
    }

    #[test]
    fn authored_frame_cut_is_presented_on_the_same_tick() {
        let mut playback = PosePlayback::default();
        let mut state = WizardState::default();
        playback.interrupt("old", "idle", 0, 10, None, None);
        playback.cut("authored-key", 3);
        playback.step(3, &mut state);

        assert_eq!(state.pose_id.as_deref(), Some("authored-key"));
        assert_eq!(state.previous_pose_id.as_deref(), Some("authored-key"));
        assert!(state.pose_handoff);
        assert_eq!(state.pose_blend, 1.0);
    }
}
