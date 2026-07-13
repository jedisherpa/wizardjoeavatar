use serde_json::json;
use std::collections::BTreeSet;
use wizard_avatar_engine::controller::{WizardAvatarController, WizardCommand};
use wizard_avatar_engine::pose::sample_pose;
use wizard_avatar_engine::pose_clip::pose_clip_definition;
use wizard_avatar_engine::quality::{
    FrameQualityReport, FrameQualitySnapshot, FrameQualityThresholds,
};

const WJFL_CLIPS: [&str; 5] = [
    "wjfl_run",
    "wjfl_guard",
    "wjfl_reaction",
    "wjfl_social",
    "wjfl_feelings",
];

#[test]
fn every_wjfl_clip_frame_and_loop_boundary_passes_the_breakup_gate() {
    let thresholds = FrameQualityThresholds {
        maximum_face_anchor_step: 4.0,
        maximum_staff_anchor_step: 6.0,
        maximum_free_foot_step: 8.0,
        ..FrameQualityThresholds::default()
    };
    let mut total_frames = 0usize;

    for clip_id in WJFL_CLIPS {
        let definition = pose_clip_definition(clip_id).expect("WJFL clip definition");
        assert!(
            definition.loopable,
            "{clip_id} must support repeat playback"
        );
        let cycle_ticks = definition
            .steps
            .iter()
            .map(|step| usize::from(step.hold_ticks.max(step.effective_transition_ticks())))
            .sum::<usize>();
        let mut controller = WizardAvatarController::default();
        let result = controller.apply_command(WizardCommand::new(
            "pose_clip",
            json!({"clip_id": clip_id, "loop": true}),
        ));
        assert!(result.ok, "{}", result.message);

        let mut snapshots = Vec::new();
        let mut visited_steps = BTreeSet::new();
        for frame_index in 0..cycle_ticks * 3 + 120 {
            controller.step_tick();
            if let Some(step) = controller.current_state().pose_clip_step {
                visited_steps.insert(step);
            }
            let sample = sample_pose(controller.current_state()).expect("sample WJFL clip");
            snapshots.push(
                FrameQualitySnapshot::from_pose(
                    clip_id,
                    sample.pose_id.clone(),
                    frame_index as u64,
                    &sample,
                )
                .expect("WJFL quality snapshot"),
            );
        }
        assert_eq!(
            visited_steps.len(),
            definition.steps.len(),
            "{clip_id} did not visit every authored step"
        );
        assert_eq!(
            controller.current_state().pose_clip_id.as_deref(),
            Some(clip_id)
        );
        let report = FrameQualityReport::inspect_sequence(&snapshots, thresholds);
        assert!(
            report.failures.is_empty(),
            "{clip_id} produced {} frame-quality failures: {:#?}",
            report.failures.len(),
            report.failures.iter().take(20).collect::<Vec<_>>()
        );
        total_frames += snapshots.len();
    }

    assert!(total_frames >= 900, "expected a substantial frame census");
}
