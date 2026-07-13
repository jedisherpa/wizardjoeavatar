use wizard_avatar_engine::pose::{sample_pose, PointF};
use wizard_avatar_engine::quality::{
    FrameQualityReport, FrameQualitySnapshot, FrameQualityThresholds,
};
use wizard_avatar_engine::state::{Direction, Locomotion, WizardState};

#[test]
fn existing_direction_and_gait_frames_pass_the_strict_breakup_gate() {
    let mut frame_index = 0u64;
    for direction in Direction::ALL {
        let mut snapshots = Vec::new();
        for phase_index in 0..24 {
            let mut state = WizardState {
                facing: direction,
                previous_facing: direction,
                facing_blend: 1.0,
                facing_pose_handoff: true,
                locomotion: Locomotion::Walking,
                speed_ratio: 1.0,
                walk_phase: phase_index as f32 / 24.0,
                ..WizardState::default()
            };
            state.planted_foot = if phase_index < 12 {
                wizard_avatar_engine::state::PlantedFoot::Left
            } else {
                wizard_avatar_engine::state::PlantedFoot::Right
            };
            let pose = sample_pose(&state).expect("pose sample");
            let snapshot = FrameQualitySnapshot::from_pose(
                format!("{direction:?}-gait"),
                format!("{direction:?}"),
                frame_index,
                &pose,
            )
            .expect("quality snapshot");
            snapshots.push(snapshot);
            frame_index += 1;
        }
        let report = FrameQualityReport::inspect_sequence(
            &snapshots,
            FrameQualityThresholds {
                maximum_face_anchor_step: 8.0,
                maximum_staff_anchor_step: 8.0,
                maximum_free_foot_step: 16.0,
                ..FrameQualityThresholds::default()
            },
        );
        report.require_pass().expect("strict breakup gate");
    }
}

#[test]
fn point_distance_type_remains_fractional_for_anchor_checks() {
    let point = PointF { x: 1.5, y: 2.5 };
    assert_eq!(point.x + point.y, 4.0);
}
