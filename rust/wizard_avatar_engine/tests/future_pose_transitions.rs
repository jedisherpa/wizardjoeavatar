use serde_json::json;
use std::collections::BTreeMap;
use wizard_avatar_engine::controller::{WizardAvatarController, WizardCommand};
use wizard_avatar_engine::pose::{
    analyze_region_fragmentation, sample_pose, PoseLibrary, RegionId,
};
use wizard_avatar_engine::quality::{
    FrameQualityFailure, FrameQualityReport, FrameQualitySnapshot, FrameQualityThresholds,
};

fn command(controller: &mut WizardAvatarController, pose_id: &str, transition_ms: u64) {
    let result = controller.apply_command(WizardCommand::new(
        "pose",
        json!({"pose_id": pose_id, "transition_ms": transition_ms}),
    ));
    assert!(result.ok, "{}", result.message);
}

#[test]
fn every_authored_new_pose_neighbor_transition_passes_the_frame_breakup_gate() {
    let library = PoseLibrary::reference().expect("pose library");
    let imported = library
        .pose_ids()
        .filter_map(|pose_id| {
            let pose = library.for_id(pose_id)?;
            pose.motion.candidate_id.as_ref().map(|_| {
                (
                    pose.id.clone(),
                    pose.motion.authored_transition_neighbors.clone(),
                )
            })
        })
        .collect::<Vec<_>>();
    assert_eq!(imported.len(), 29);

    let thresholds = FrameQualityThresholds {
        maximum_face_anchor_step: 4.0,
        maximum_staff_anchor_step: 6.0,
        maximum_free_foot_step: 8.0,
        ..FrameQualityThresholds::default()
    };
    let mut failures = Vec::<FrameQualityFailure>::new();
    let mut fragmented_regions = BTreeMap::<RegionId, usize>::new();
    let mut transitions = 0usize;
    let mut frame_index = 0u64;

    for (target, neighbors) in imported {
        for source in neighbors {
            let mut controller = WizardAvatarController::default();
            command(&mut controller, &source, 1);
            controller.advance(0.1);
            command(&mut controller, &target, 240);
            let transition_id = format!("{source}-to-{target}");
            let mut snapshots = Vec::new();
            for _ in 0..18 {
                controller.step_tick();
                let sample = sample_pose(controller.current_state()).expect("sample transition");
                for (region, excess) in analyze_region_fragmentation(&sample) {
                    *fragmented_regions.entry(region).or_default() += excess;
                }
                snapshots.push(
                    FrameQualitySnapshot::from_pose(
                        transition_id.clone(),
                        sample.pose_id.clone(),
                        frame_index,
                        &sample,
                    )
                    .expect("quality snapshot"),
                );
                frame_index += 1;
            }
            let report = FrameQualityReport::inspect_sequence(&snapshots, thresholds);
            failures.extend(report.failures);
            transitions += 1;
        }
    }

    assert!(
        transitions >= 100,
        "transition matrix is unexpectedly small"
    );
    let mut by_rule = BTreeMap::<String, usize>::new();
    for failure in &failures {
        *by_rule.entry(failure.rule.clone()).or_default() += 1;
    }
    let examples = failures.iter().take(24).collect::<Vec<_>>();
    assert!(failures.is_empty(), "{} of {transitions} authored transitions failed; by rule {by_rule:?}; fragmented regions {fragmented_regions:?}; examples {examples:#?}", failures.len());
}
