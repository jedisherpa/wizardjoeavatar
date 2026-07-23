use serde_json::json;
use std::collections::BTreeSet;
use wizard_avatar_engine::controller::{WizardAvatarController, WizardCommand};
use wizard_avatar_engine::pose_clip::pose_clip_definition;
use wizard_avatar_engine::pose_graph_runtime::{
    project_runtime_pose_graph, runtime_pose_graph_catalog,
};

const REPLACEMENT_CLIPS: [&str; 5] = [
    "wjfl_run",
    "wjfl_guard",
    "wjfl_reaction",
    "wjfl_social",
    "wjfl_feelings",
];

#[test]
fn every_replacement_clip_frame_and_loop_boundary_uses_an_exact_promoted_graph() {
    let catalog = runtime_pose_graph_catalog().expect("replacement graph catalog");
    let mut total_frames = 0usize;
    let mut projected = BTreeSet::new();

    for clip_id in REPLACEMENT_CLIPS {
        let definition = pose_clip_definition(clip_id).expect("replacement clip definition");
        assert!(
            definition.loopable,
            "{clip_id} must support repeat playback"
        );
        for step in definition.steps {
            let entry = catalog
                .for_runtime_pose_id(step.pose_id)
                .unwrap_or_else(|| panic!("{} has no promoted graph", step.pose_id));
            assert!(entry.exact_rgba_equal);
            assert_eq!(entry.silhouette_iou_millionths, 1_000_000);
            assert_eq!(entry.foreground_color_fidelity_millionths, 1_000_000);
            if projected.insert(entry.source_record_id.clone()) {
                let raster = project_runtime_pose_graph(step.pose_id)
                    .unwrap_or_else(|error| panic!("project {}: {error}", step.pose_id));
                assert_eq!(
                    raster
                        .coverage_mask
                        .iter()
                        .filter(|value| **value == 1)
                        .count() as u64,
                    entry.foreground_pixel_count
                );
            }
        }

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

        let mut visited_steps = BTreeSet::new();
        for _ in 0..cycle_ticks * 3 + 120 {
            controller.step_tick();
            let state = controller.current_state();
            if let Some(step) = state.pose_clip_step {
                visited_steps.insert(step);
            }
            let pose_id = state
                .pose_id
                .as_deref()
                .expect("looping replacement clip must own a pose");
            assert!(
                catalog.for_runtime_pose_id(pose_id).is_some(),
                "{clip_id} emitted non-promoted pose {pose_id}"
            );
            total_frames += 1;
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
    }

    assert!(total_frames >= 900, "expected a substantial frame census");
}
