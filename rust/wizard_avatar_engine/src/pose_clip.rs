use crate::animation::reference_pose_id_for_state;
use crate::pose::transition_ticks_for;
use crate::pose_playback::{PosePlayback, DEFAULT_POSE_TRANSITION_TICKS};
use crate::state::WizardState;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PoseClipStep {
    pub pose_id: &'static str,
    pub hold_ticks: u16,
    pub transition_ticks: u16,
}

impl PoseClipStep {
    #[must_use]
    pub const fn effective_transition_ticks(self) -> u16 {
        if self.transition_ticks < DEFAULT_POSE_TRANSITION_TICKS {
            DEFAULT_POSE_TRANSITION_TICKS
        } else {
            self.transition_ticks
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub struct PoseClipDefinition {
    pub id: &'static str,
    pub steps: &'static [PoseClipStep],
    pub loopable: bool,
}

const fn step(pose_id: &'static str, hold_ticks: u16, transition_ticks: u16) -> PoseClipStep {
    PoseClipStep {
        pose_id,
        hold_ticks,
        transition_ticks,
    }
}

const GROUND_WALK: &[PoseClipStep] = &[
    step("walk_front_left", 12, 10),
    step("walk_front_right_lift", 12, 10),
    step("walk_front_right", 12, 10),
];
const GROUND_RUN: &[PoseClipStep] = &[
    step("walk_front_right", 10, 9),
    step("walk_front_right_lift", 9, 8),
    step("front_run_charge_right_plant", 9, 8),
    step("run_front_airborne_reach", 9, 8),
    step("run_front_airborne_drive", 9, 8),
    step("front_run_charge_right_plant", 10, 8),
    step("walk_front_left", 11, 9),
];
const HOVER_FLAP: &[PoseClipStep] = &[
    step("fly_front_hover_ready", 12, 10),
    step("fly_front_knee_up", 10, 9),
    step("fly_front_wings_up", 9, 8),
    step("fly_front_wings_down", 9, 8),
    step("fly_front_hover_neutral", 12, 9),
];
const BANK_GLIDE: &[PoseClipStep] = &[
    step("fly_front_hover_neutral", 12, 10),
    step("fly_southwest_banked_staff", 12, 10),
    step("fly_southeast_banked_staff", 12, 10),
    step("fly_southeast_forward_glide", 14, 10),
    step("fly_southeast_staff_forward", 12, 9),
    step("fly_southeast_cheer", 12, 9),
    step("fly_southeast_banked_staff", 12, 10),
    step("fly_front_hover_neutral", 14, 10),
];
const STAFF_COMBO: &[PoseClipStep] = &[
    step("front_staff_guard_windup", 14, 10),
    step("front_staff_guard_low", 12, 9),
    step("front_staff_block_horizontal", 12, 9),
    step("front_magic_staff_thrust", 12, 8),
    step("magic_cast", 14, 9),
    step("front_staff_spin_flourish", 16, 10),
];
const REACTION_RECOVER: &[PoseClipStep] = &[
    step("front_crouch_guard", 11, 9),
    step("front_reaction_jump_fist_staff", 12, 9),
    step("front_airborne_fall_back_staff", 11, 9),
    step("front_crouch_landing_staff_plant", 12, 9),
    step("front_crouch_reaction_staff_planted", 12, 9),
    step("front_kneel_staff_brace", 14, 10),
];
const CELEBRATE: &[PoseClipStep] = &[
    step("front_victory_cast", 14, 10),
    step("front_celebrate_jump_staff_up", 12, 9),
    step("front_celebrate_wings_staff_up", 16, 10),
    step("front_victory_cast", 12, 9),
];
const CONVERSATION: &[PoseClipStep] = &[
    step("explaining", 18, 10),
    step("front_point_direct_staff_held", 16, 10),
    step("front_shush_secret_staff_held", 16, 10),
    step("front_victory_cast", 14, 10),
];
const EXPLAIN: &[PoseClipStep] = &[step("explaining", 72, 10)];
const POINT: &[PoseClipStep] = &[step("front_point_direct_staff_held", 72, 10)];
const THINK: &[PoseClipStep] = &[step("front_shush_secret_staff_held", 72, 10)];
const WJFL_RUN: &[PoseClipStep] = &[
    step("run_front_cross_step_wings_staff", 10, 9),
    step("run_front_stride_wings_staff", 10, 9),
    step("front_run_charge_wings", 10, 9),
    step("run_front_stride_wings_staff", 10, 9),
];
const WJFL_GUARD: &[PoseClipStep] = &[
    step("front_idle_wings", 14, 10),
    step("front_crouch_guard_wings", 12, 10),
    step("front_kneel_staff_brace_wings", 12, 10),
    step("front_crouch_staff_planted_wings", 12, 10),
    step("front_crouch_hand_plant_wings", 12, 10),
    step("front_staff_guard_windup_wings", 12, 10),
    step("front_staff_guard_horizontal_wings", 12, 10),
    step("front_staff_guard_low_wings", 12, 10),
    step("front_staff_block_wings", 12, 10),
    step("front_magic_staff_thrust_wings", 12, 10),
    step("front_staff_spin_wings", 14, 10),
    step("front_idle_wings", 14, 10),
];
const WJFL_REACTION: &[PoseClipStep] = &[
    step("front_idle_wings", 14, 10),
    step("front_reaction_jump_wings_staff", 12, 10),
    step("front_airborne_fall_back_wings", 12, 10),
    step("front_celebrate_jump_wings", 12, 10),
    step("front_victory_cast_wings", 14, 10),
    step("front_celebrate_staff_up_wings", 14, 10),
    step("front_idle_wings", 14, 10),
];
const WJFL_SOCIAL: &[PoseClipStep] = &[
    step("front_idle_wings", 16, 10),
    step("front_greeting_wave_wings", 14, 10),
    step("front_explaining_open_hand_wings", 14, 10),
    step("front_explaining_both_hands_wings", 14, 10),
    step("front_point_direct_wings", 14, 10),
    step("front_point_side_wings", 14, 10),
    step("front_thinking_hand_chin_wings", 16, 10),
    step("front_shush_wings", 16, 10),
    step("front_sincere_hand_heart_wings", 16, 10),
    step("front_playful_kick_wings", 14, 10),
    step("front_magic_staff_raise_wings", 14, 10),
    step("front_magic_staff_spark_wings", 16, 10),
    step("front_idle_wings", 16, 10),
];
const WJFL_FEELINGS: &[PoseClipStep] = &[
    step("feeling_joy_full", 16, 10),
    step("feeling_joy_close", 14, 10),
    step("feeling_sadness_full", 16, 10),
    step("feeling_sadness_close", 14, 10),
    step("feeling_anger_full", 16, 10),
    step("feeling_anger_close", 14, 10),
    step("feeling_fear_full", 16, 10),
    step("feeling_fear_close", 14, 10),
    step("feeling_shame_full", 16, 10),
    step("feeling_shame_close", 14, 10),
    step("feeling_disgust_full", 16, 10),
    step("feeling_disgust_close", 14, 10),
    step("feeling_surprise_full", 16, 10),
    step("feeling_surprise_close", 14, 10),
    step("feeling_pride_full", 16, 10),
    step("feeling_pride_close", 14, 10),
    step("feeling_guilt_full", 16, 10),
    step("feeling_guilt_close", 14, 10),
    step("feeling_love_full", 16, 10),
    step("feeling_love_close", 14, 10),
];

pub const POSE_CLIPS: &[PoseClipDefinition] = &[
    PoseClipDefinition {
        id: "ground_walk",
        steps: GROUND_WALK,
        loopable: true,
    },
    PoseClipDefinition {
        id: "ground_run",
        steps: GROUND_RUN,
        loopable: true,
    },
    PoseClipDefinition {
        id: "hover_flap",
        steps: HOVER_FLAP,
        loopable: true,
    },
    PoseClipDefinition {
        id: "bank_glide",
        steps: BANK_GLIDE,
        loopable: true,
    },
    PoseClipDefinition {
        id: "staff_combo",
        steps: STAFF_COMBO,
        loopable: false,
    },
    PoseClipDefinition {
        id: "reaction_recover",
        steps: REACTION_RECOVER,
        loopable: false,
    },
    PoseClipDefinition {
        id: "celebrate",
        steps: CELEBRATE,
        loopable: false,
    },
    PoseClipDefinition {
        id: "conversation",
        steps: CONVERSATION,
        loopable: false,
    },
    PoseClipDefinition {
        id: "explain",
        steps: EXPLAIN,
        loopable: false,
    },
    PoseClipDefinition {
        id: "point",
        steps: POINT,
        loopable: false,
    },
    PoseClipDefinition {
        id: "think",
        steps: THINK,
        loopable: false,
    },
    PoseClipDefinition {
        id: "wjfl_run",
        steps: WJFL_RUN,
        loopable: true,
    },
    PoseClipDefinition {
        id: "wjfl_guard",
        steps: WJFL_GUARD,
        loopable: true,
    },
    PoseClipDefinition {
        id: "wjfl_reaction",
        steps: WJFL_REACTION,
        loopable: true,
    },
    PoseClipDefinition {
        id: "wjfl_social",
        steps: WJFL_SOCIAL,
        loopable: true,
    },
    PoseClipDefinition {
        id: "wjfl_feelings",
        steps: WJFL_FEELINGS,
        loopable: true,
    },
];

#[must_use]
pub fn pose_clip_definition(id: &str) -> Option<&'static PoseClipDefinition> {
    POSE_CLIPS.iter().find(|clip| clip.id == id)
}

#[derive(Clone, Debug, Default)]
pub struct PoseClipPlayback {
    clip_id: Option<&'static str>,
    entry_from: Option<String>,
    step_index: usize,
    next_step_tick: u64,
    looped: bool,
    restore_to: Option<String>,
    restore_to_direction: bool,
    generation: u64,
}

impl PoseClipPlayback {
    pub fn start(
        &mut self,
        clip_id: &str,
        entry_from: String,
        tick: u64,
        looped: bool,
        restore_to: Option<String>,
        restore_to_direction: bool,
    ) -> Result<(), String> {
        let definition = pose_clip_definition(clip_id)
            .ok_or_else(|| format!("unsupported pose clip: {clip_id}"))?;
        if looped && !definition.loopable {
            return Err(format!("pose clip {clip_id} is not loopable"));
        }
        self.generation = self.generation.wrapping_add(1);
        self.clip_id = Some(definition.id);
        self.entry_from = Some(entry_from);
        self.step_index = 0;
        self.next_step_tick = tick;
        self.looped = looped;
        self.restore_to = restore_to;
        self.restore_to_direction = restore_to_direction;
        Ok(())
    }

    #[must_use]
    pub fn restoration(&self) -> Option<(Option<String>, bool)> {
        self.clip_id
            .map(|_| (self.restore_to.clone(), self.restore_to_direction))
    }

    pub fn clear(&mut self, state: &mut WizardState) {
        self.clip_id = None;
        self.entry_from = None;
        self.step_index = 0;
        self.next_step_tick = 0;
        self.looped = false;
        self.restore_to = None;
        self.restore_to_direction = false;
        state.pose_clip_id = None;
        state.pose_clip_step = None;
        state.pose_clip_generation = self.generation;
    }

    pub fn step(&mut self, tick: u64, pose_playback: &mut PosePlayback, state: &mut WizardState) {
        let Some(clip_id) = self.clip_id else {
            state.pose_clip_id = None;
            state.pose_clip_step = None;
            state.pose_clip_generation = self.generation;
            return;
        };
        if self.step_index == 0 && state.pose_blend < 1.0 {
            // The pose that was presented when the replacement was requested can
            // become stale while the active handoff finishes. Resolve the stable
            // presented pose again before beginning the replacement clip.
            self.entry_from = None;
            self.write_state(state);
            return;
        }
        let definition = pose_clip_definition(clip_id).expect("active clip must resolve");
        if tick < self.next_step_tick {
            self.write_state(state);
            return;
        }

        if self.step_index >= definition.steps.len() {
            if self.looped {
                self.step_index = 0;
            } else {
                let presented = pose_playback
                    .presented_pose()
                    .map(str::to_owned)
                    .or_else(|| state.pose_id.clone());
                let restore_to = self.restore_to.take();
                let restore_to_direction = self.restore_to_direction;
                self.clear(state);
                if restore_to_direction {
                    if let Some(presented) = presented {
                        let direction_pose = reference_pose_id_for_state(state).to_string();
                        pose_playback.return_to_direction(
                            direction_pose,
                            presented,
                            tick,
                            DEFAULT_POSE_TRANSITION_TICKS,
                        );
                    }
                } else if let (Some(presented), Some(restore_to)) = (presented, restore_to) {
                    let transition_ticks = transition_ticks_for(
                        &presented,
                        &restore_to,
                        DEFAULT_POSE_TRANSITION_TICKS,
                    );
                    pose_playback.interrupt(
                        restore_to,
                        presented,
                        tick,
                        transition_ticks,
                        None,
                        None,
                    );
                }
                return;
            }
        }

        let step = definition.steps[self.step_index];
        let presented = self
            .entry_from
            .take()
            .or_else(|| pose_playback.presented_pose().map(str::to_owned))
            .or_else(|| state.pose_id.clone())
            .unwrap_or_else(|| step.pose_id.to_string());
        let transition_ticks =
            transition_ticks_for(&presented, step.pose_id, step.effective_transition_ticks());
        pose_playback.interrupt(step.pose_id, presented, tick, transition_ticks, None, None);
        self.next_step_tick = tick + u64::from(step.hold_ticks.max(transition_ticks));
        self.step_index += 1;
        self.write_state(state);
    }

    fn write_state(&self, state: &mut WizardState) {
        state.pose_clip_id = self.clip_id.map(str::to_string);
        state.pose_clip_step = self.step_index.checked_sub(1);
        state.pose_clip_generation = self.generation;
    }
}
