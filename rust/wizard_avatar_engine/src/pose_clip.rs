use crate::pose::transition_ticks_for;
use crate::pose_graph_runtime::implicit_runtime_pose_id;
use crate::pose_playback::{PosePlayback, DEFAULT_POSE_TRANSITION_TICKS};
use crate::state::WizardState;
use serde::Serialize;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
pub struct PoseClipStep {
    pub pose_id: &'static str,
    pub hold_ticks: u16,
    pub transition_ticks: u16,
}

impl PoseClipStep {
    #[must_use]
    pub const fn effective_transition_ticks(self) -> u16 {
        if self.transition_ticks == 0 {
            0
        } else if self.transition_ticks < DEFAULT_POSE_TRANSITION_TICKS {
            DEFAULT_POSE_TRANSITION_TICKS
        } else {
            self.transition_ticks
        }
    }
}

#[derive(Clone, Copy, Debug, Serialize)]
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
    step("walk_contact_left", 8, 0),
    step("walk_passing_left", 8, 0),
    step("walk_up_left", 8, 0),
    step("walk_contact_right", 8, 0),
];
const GROUND_RUN: &[PoseClipStep] = &[
    step("run_passing", 5, 0),
    step("run_contact_left", 5, 0),
    step("run_flight_phase", 5, 0),
    step("run_contact_right", 5, 0),
];
const HOVER_FLAP: &[PoseClipStep] = &[
    step("fly_forward_camera_top_recovery", 6, 0),
    step("fly_forward_camera_early_powerstroke", 6, 0),
    step("fly_forward_camera_mid_powerstroke", 6, 0),
    step("fly_forward_camera_late_powerstroke", 6, 0),
    step("fly_forward_camera_bottom_powerstroke", 6, 0),
    step("fly_forward_camera_early_recovery", 6, 0),
    step("fly_forward_camera_mid_recovery", 6, 0),
    step("fly_forward_camera_late_recovery", 6, 0),
    step("fly_forward_camera_near_top_recovery", 6, 0),
    step("fly_forward_camera_loop_close", 6, 0),
];
const BANK_GLIDE: &[PoseClipStep] = &[
    step("flight_hover_neutral", 12, 0),
    step("flight_bank_left", 12, 0),
    step("flight_glide_forward", 14, 0),
    step("flight_bank_right", 12, 0),
    step("flight_staff_forward", 12, 0),
    step("flight_hover_neutral", 14, 0),
];
const STAFF_COMBO: &[PoseClipStep] = &[
    step("staff_grip_default", 12, 10),
    step("staff_two_hand_grip", 12, 10),
    step("staff_raise_vertical", 12, 8),
    step("staff_aim_forward", 12, 8),
    step("staff_sweep_horizontal", 12, 8),
    step("magic_cast_begin", 10, 8),
    step("magic_cast_hold", 14, 8),
    step("magic_cast_release", 10, 8),
    step("magic_cast_recover", 14, 10),
];
const REACTION_RECOVER: &[PoseClipStep] = &[
    step("crouch_prepare", 10, 0),
    step("jump_launch", 8, 0),
    step("jump_apex", 8, 0),
    step("jump_descent", 8, 0),
    step("jump_land_contact", 8, 0),
    step("jump_land_recovery", 12, 0),
    step("locomotion_return_home", 14, 10),
];
const CELEBRATE: &[PoseClipStep] = &[
    step("emotion_excited", 14, 10),
    step("emotion_triumphant", 16, 10),
    step("magic_mastery_hero", 16, 10),
    step("hero_declaration", 18, 10),
];
const CONVERSATION: &[PoseClipStep] = &[
    step("listen_user_warm", 16, 10),
    step("speak_explain_open", 14, 10),
    step("speak_explain_sequence", 14, 10),
    step("speak_clarify", 14, 10),
    step("speech_yield_floor", 16, 10),
];
const EXPLAIN: &[PoseClipStep] = &[
    step("speak_explain_open", 18, 10),
    step("speak_explain_precise", 18, 10),
    step("speak_explain_sequence", 18, 10),
    step("speak_summarize", 18, 10),
];
const POINT: &[PoseClipStep] = &[
    step("hand_point_screen_left", 18, 10),
    step("hand_point_screen_right", 18, 10),
    step("hand_point_up", 18, 10),
    step("hand_point_down", 18, 10),
];
const THINK: &[PoseClipStep] = &[
    step("think_consider", 20, 10),
    step("think_upward_recall", 20, 10),
    step("realization_small", 16, 10),
    step("realization_clear", 16, 10),
];
const WJFL_RUN: &[PoseClipStep] = &[
    step("run_start", 7, 0),
    step("run_passing", 5, 0),
    step("run_contact_left", 5, 0),
    step("run_flight_phase", 5, 0),
    step("run_contact_right", 5, 0),
];
const WJFL_GUARD: &[PoseClipStep] = &[
    step("idle_wings_displayed", 14, 10),
    step("staff_grip_default", 12, 10),
    step("staff_two_hand_grip", 12, 10),
    step("staff_plant", 12, 10),
    step("staff_raise_vertical", 12, 10),
    step("staff_aim_forward", 12, 10),
    step("staff_sweep_horizontal", 12, 10),
    step("idle_staff_two_hand_rest", 14, 10),
];
const WJFL_REACTION: &[PoseClipStep] = &[
    step("emotion_surprise", 14, 10),
    step("emotion_shock", 14, 10),
    step("magic_mishap_start", 12, 10),
    step("magic_mishap_blast", 12, 10),
    step("magic_mishap_smoke_reveal", 14, 10),
    step("comedy_recover_dignity", 16, 10),
    step("emotion_recover_composure", 16, 10),
];
const WJFL_SOCIAL: &[PoseClipStep] = &[
    step("hand_open_relaxed", 16, 10),
    step("hand_present_screen_right", 14, 10),
    step("hand_present_screen_left", 14, 10),
    step("hand_invite", 14, 10),
    step("speak_reassure", 14, 10),
    step("speak_persuade", 14, 10),
    step("speak_confide", 16, 10),
    step("emotion_gratitude", 16, 10),
    step("idle_warm_camera_ready", 16, 10),
];
const WJFL_FEELINGS: &[PoseClipStep] = &[
    step("emotion_neutral", 14, 10),
    step("emotion_joy", 14, 10),
    step("emotion_amused", 14, 10),
    step("emotion_excited", 14, 10),
    step("emotion_curious", 14, 10),
    step("emotion_confident", 14, 10),
    step("emotion_compassion", 14, 10),
    step("emotion_proud", 14, 10),
    step("emotion_playful", 14, 10),
    step("emotion_relief", 14, 10),
    step("emotion_gratitude", 14, 10),
    step("emotion_surprise", 14, 10),
    step("emotion_shock", 14, 10),
    step("emotion_confusion", 14, 10),
    step("emotion_skepticism", 14, 10),
    step("emotion_concern", 14, 10),
    step("emotion_sadness", 14, 10),
    step("emotion_grief_restrained", 14, 10),
    step("emotion_shame", 14, 10),
    step("emotion_embarrassed", 14, 10),
    step("emotion_fear", 14, 10),
    step("emotion_anxiety", 14, 10),
    step("emotion_anger", 14, 10),
    step("emotion_frustration", 14, 10),
    step("emotion_determined", 14, 10),
    step("emotion_defiant", 14, 10),
    step("emotion_disappointed", 14, 10),
    step("emotion_exhausted", 14, 10),
    step("emotion_fatigued_speaking", 14, 10),
    step("emotion_contemplative", 14, 10),
    step("emotion_serene", 14, 10),
    step("emotion_solemn", 14, 10),
    step("emotion_hopeful", 14, 10),
    step("emotion_triumphant", 14, 10),
    step("emotion_recover_composure", 14, 10),
];
const DANCE_GROOVE: &[PoseClipStep] = &[
    step("dance_ready", 12, 0),
    step("dance_step_left", 12, 0),
    step("dance_step_right", 12, 0),
    step("dance_bounce_down", 12, 0),
    step("dance_bounce_up", 12, 0),
    step("dance_turn_prepare", 12, 0),
    step("dance_turn_mid", 12, 0),
    step("dance_turn_finish", 12, 0),
    step("dance_wing_flourish", 12, 0),
    step("dance_kick", 12, 0),
    step("dance_slide", 12, 0),
    step("dance_finale", 16, 0),
];
const BREAKDANCE: &[PoseClipStep] = &[
    step("dance_staff_twirl_start", 12, 0),
    step("dance_staff_twirl_mid", 12, 0),
    step("dance_staff_twirl_catch", 12, 0),
    step("dance_low_freeze", 14, 0),
    step("dance_high_freeze", 14, 0),
    step("hero_dance_freeze", 18, 0),
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
        id: "forward_camera_flight",
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
    PoseClipDefinition {
        id: "dance_groove",
        steps: DANCE_GROOVE,
        loopable: true,
    },
    PoseClipDefinition {
        id: "breakdance",
        steps: BREAKDANCE,
        loopable: true,
    },
];

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pose_graph_runtime::runtime_pose_graph_catalog;
    use std::collections::BTreeSet;

    #[test]
    fn every_clip_step_resolves_to_an_exact_replacement_graph() {
        let catalog = runtime_pose_graph_catalog().expect("runtime graph catalog");
        let clip_poses = POSE_CLIPS
            .iter()
            .flat_map(|clip| clip.steps.iter().map(|step| step.pose_id))
            .collect::<BTreeSet<_>>();
        let manifest = catalog.manifest();
        let missing = clip_poses
            .iter()
            .filter(|pose_id| catalog.primary_for_semantic_id(pose_id).is_none())
            .collect::<Vec<_>>();
        assert!(missing.is_empty(), "clip poses missing graphs: {missing:?}");
        assert!(manifest.entries.iter().all(|entry| {
            entry.primary_for_semantic_id
                && entry.exact_rgba_equal
                && entry.control_groups.iter().any(|group| group == "all")
        }));
    }

    #[test]
    fn ground_walk_contains_the_four_authored_stride_phases() {
        assert_eq!(
            GROUND_WALK
                .iter()
                .map(|step| step.pose_id)
                .collect::<Vec<_>>(),
            [
                "walk_contact_left",
                "walk_passing_left",
                "walk_up_left",
                "walk_contact_right"
            ]
        );
    }

    #[test]
    fn forward_camera_flight_is_the_exact_ten_frame_sixty_tick_cycle() {
        assert_eq!(HOVER_FLAP.len(), 10);
        assert_eq!(
            HOVER_FLAP
                .iter()
                .map(|step| step.pose_id)
                .collect::<Vec<_>>(),
            [
                "fly_forward_camera_top_recovery",
                "fly_forward_camera_early_powerstroke",
                "fly_forward_camera_mid_powerstroke",
                "fly_forward_camera_late_powerstroke",
                "fly_forward_camera_bottom_powerstroke",
                "fly_forward_camera_early_recovery",
                "fly_forward_camera_mid_recovery",
                "fly_forward_camera_late_recovery",
                "fly_forward_camera_near_top_recovery",
                "fly_forward_camera_loop_close",
            ]
        );
        assert!(HOVER_FLAP
            .iter()
            .all(|step| step.hold_ticks == 6 && step.transition_ticks == 0));
        assert_eq!(
            HOVER_FLAP
                .iter()
                .map(|step| u32::from(step.hold_ticks))
                .sum::<u32>(),
            60
        );
        assert_eq!(
            pose_clip_definition("forward_camera_flight")
                .expect("forward camera flight alias")
                .steps,
            HOVER_FLAP
        );
    }
}

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
                        let direction_pose = implicit_runtime_pose_id(state).to_string();
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
        let requested_transition_ticks = step.effective_transition_ticks();
        let transition_ticks = if requested_transition_ticks == 0 {
            pose_playback.cut(step.pose_id, tick);
            0
        } else {
            let transition_ticks =
                transition_ticks_for(&presented, step.pose_id, requested_transition_ticks);
            pose_playback.interrupt(step.pose_id, presented, tick, transition_ticks, None, None);
            transition_ticks
        };
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
