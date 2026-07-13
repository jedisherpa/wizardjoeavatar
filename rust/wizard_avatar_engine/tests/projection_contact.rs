use wizard_avatar_engine::pose::{sample_pose, AnchorId, PoseSample};
use wizard_avatar_engine::projection::{
    ProjectedPoseContext, ProjectionHistory, MAX_CONTACT_CORRECTION,
};
use wizard_avatar_engine::state::{ContactMarker, Direction, Locomotion, PlantedFoot, WizardState};

#[test]
fn wiz_proj_001_depth_quantization_is_hysteretic_and_bounded_per_frame() {
    let mut history = ProjectionHistory::default();
    let mut state = WizardState::default();
    let mut previous_level: Option<i16> = None;
    for z in [5.00, 5.01, 4.99, 5.02, 4.98, 4.7, 4.4, 4.1] {
        state.world_position.z = z;
        let pose = sample_pose(&state).expect("pose");
        let context = history.project(&state, &pose, 480, 270);
        if let Some(previous) = previous_level {
            assert!((context.scale_level - previous).abs() <= 1);
        }
        previous_level = Some(context.scale_level);
    }
}

#[test]
fn wiz_contact_001_planted_foot_correction_is_continuous_across_contact_markers() {
    let mut history = ProjectionHistory::default();
    let mut state = WizardState {
        speed_ratio: 1.0,
        ..WizardState::default()
    };
    let mut previous = (0, 0);
    for step in 0..64 {
        state.walk_phase = step as f32 / 64.0;
        state.contact_marker = ContactMarker::from_phase(state.walk_phase);
        state.world_position.x += 0.012;
        let pose = sample_pose(&state).expect("pose");
        let context = history.project(&state, &pose, 480, 270);
        assert!((context.foot_correction.0 - previous.0).abs() <= 1);
        assert!((context.foot_correction.1 - previous.1).abs() <= 1);
        previous = context.foot_correction;
    }
}

fn projected_anchor(
    pose: &PoseSample,
    context: ProjectedPoseContext,
    anchor: AnchorId,
) -> (i32, i32) {
    let point = pose.anchors[&anchor];
    (
        (context.quantized_root.0 as f32 + (point.x - pose.root.0 as f32) * context.quantized_scale)
            .round() as i32,
        (context.quantized_root.1 as f32 + (point.y - pose.root.1 as f32) * context.quantized_scale)
            .round() as i32,
    )
}

#[test]
fn wiz_contact_002_root_progresses_across_three_cycles_while_stance_feet_stay_bounded() {
    let mut history = ProjectionHistory::default();
    let mut state = WizardState {
        facing: Direction::East,
        previous_facing: Direction::East,
        locomotion: Locomotion::Walking,
        speed_ratio: 1.0,
        ..WizardState::default()
    };
    let steps_per_cycle = 240;
    let mut first_root = None;
    let mut last_root = (0, 0);
    let mut previous_root = None;
    let mut progressing_samples = 0;
    let mut active_contact = PlantedFoot::None;
    let mut locked_foot = None;

    for step in 0..=steps_per_cycle * 3 {
        state.walk_phase = (step as f32 / steps_per_cycle as f32).fract();
        state.contact_marker = ContactMarker::from_phase(state.walk_phase);
        state.planted_foot = state.contact_marker.planted_foot();
        state.world_position.x = -1.0 + step as f32 * 0.85 / steps_per_cycle as f32;
        let pose = sample_pose(&state).expect("multi-cycle pose");
        let context = history.project(&state, &pose, 480, 270);
        first_root.get_or_insert(context.quantized_root);
        if previous_root.is_some_and(|previous: (i32, i32)| context.quantized_root.0 > previous.0) {
            progressing_samples += 1;
        }
        previous_root = Some(context.quantized_root);
        last_root = context.quantized_root;
        assert!(context.foot_correction.0.abs() <= MAX_CONTACT_CORRECTION);
        assert!(context.foot_correction.1.abs() <= MAX_CONTACT_CORRECTION);

        let planted = state.contact_marker.planted_foot();
        if planted != active_contact {
            active_contact = planted;
            locked_foot = match planted {
                PlantedFoot::Left => Some(projected_anchor(&pose, context, AnchorId::LeftFoot)),
                PlantedFoot::Right => Some(projected_anchor(&pose, context, AnchorId::RightFoot)),
                PlantedFoot::None | PlantedFoot::Both => None,
            };
        }
        if let Some(locked) = locked_foot {
            let anchor = if planted == PlantedFoot::Left {
                AnchorId::LeftFoot
            } else {
                AnchorId::RightFoot
            };
            let foot = projected_anchor(&pose, context, anchor);
            assert!(
                (foot.0 - locked.0).abs() <= 3 && (foot.1 - locked.1).abs() <= 2,
                "{planted:?} stance foot slid from {locked:?} to {foot:?}"
            );
        }
    }

    let first_root = first_root.expect("first projected root");
    assert!(
        last_root.0 - first_root.0 >= 150,
        "root did not visibly progress"
    );
    assert!(
        progressing_samples >= 140,
        "root was pinned for too many samples"
    );
}
