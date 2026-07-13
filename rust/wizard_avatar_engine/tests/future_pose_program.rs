use std::collections::BTreeSet;
use wizard_avatar_engine::pose_program::{future_pose_motion_spec, FUTURE_POSE_MOTION_SPECS};

#[test]
fn future_pose_program_has_twenty_nine_geometries_and_one_alias() {
    let unique = FUTURE_POSE_MOTION_SPECS
        .iter()
        .filter(|spec| spec.duplicate_of.is_none())
        .map(|spec| spec.semantic_id)
        .collect::<BTreeSet<_>>();
    assert_eq!(unique.len(), 29);
    assert_eq!(
        future_pose_motion_spec("fly_front_hover_ready").and_then(|spec| spec.duplicate_of),
        Some("fly_front_hover_neutral")
    );
}

#[test]
fn every_unique_pose_has_authored_transition_neighbors() {
    for spec in FUTURE_POSE_MOTION_SPECS
        .iter()
        .filter(|spec| spec.duplicate_of.is_none())
    {
        assert!(
            !spec.neighbors.is_empty(),
            "{} has no transition neighbors",
            spec.semantic_id
        );
    }
}
