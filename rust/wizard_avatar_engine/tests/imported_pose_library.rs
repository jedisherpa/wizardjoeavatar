use std::collections::BTreeSet;
use wizard_avatar_engine::pose::{sample_pose, AnchorId, PoseLibrary, RegionId};
use wizard_avatar_engine::pose_program::FUTURE_POSE_MOTION_SPECS;
use wizard_avatar_engine::state::WizardState;

#[test]
fn rust_runtime_loads_eighty_catalog_entries_as_seventy_nine_geometries_and_one_alias() {
    let library = PoseLibrary::reference().expect("Rust pose library");
    let ids = library.pose_ids().collect::<BTreeSet<_>>();
    assert_eq!(ids.len(), 89);
    assert_eq!(library.alias_count(), 1);

    for spec in FUTURE_POSE_MOTION_SPECS {
        let pose = library
            .for_id(spec.semantic_id)
            .unwrap_or_else(|| panic!("missing {}", spec.semantic_id));
        assert!(!pose.cells.is_empty(), "{} has no cells", spec.semantic_id);
        assert_eq!(pose.anchors.len(), AnchorId::REQUIRED.len());
        assert!(AnchorId::REQUIRED
            .iter()
            .all(|anchor| pose.anchors.contains_key(anchor)));
        assert!(pose
            .cells
            .iter()
            .all(|cell| RegionId::Z_ORDER.contains(&cell.region)));
    }
    assert_eq!(
        library.for_id("fly_front_hover_ready").expect("alias").id,
        "fly_front_hover_neutral"
    );
}

#[test]
fn all_fifty_wjfl_geometries_are_runtime_resolvable() {
    let library = PoseLibrary::reference().expect("Rust pose library");
    let imported = library
        .pose_ids()
        .filter_map(|id| library.for_id(id))
        .filter_map(|pose| pose.motion.candidate_id.as_deref())
        .filter(|candidate| candidate.starts_with("WJFL-"))
        .collect::<BTreeSet<_>>();
    assert_eq!(imported.len(), 50);
    assert!(imported.contains("WJFL-01"));
    assert!(imported.contains("WJFL-40"));
    assert!(imported.contains("WJFL-51"));
    assert!(imported.contains("WJFL-60"));
}

#[test]
fn every_imported_pose_renders_as_a_complete_semantic_sample() {
    let mut state = WizardState::default();
    for spec in FUTURE_POSE_MOTION_SPECS {
        state.pose_id = Some(spec.semantic_id.to_string());
        state.previous_pose_id = state.pose_id.clone();
        state.pose_handoff = true;
        state.pose_blend = 1.0;
        let sample = sample_pose(&state)
            .unwrap_or_else(|error| panic!("{} failed: {error}", spec.semantic_id));
        assert!(sample.canvas.occupied_cells().next().is_some());
        assert_eq!(sample.anchors.len(), AnchorId::REQUIRED.len());
        assert!(sample.source_cell_count > 0);
    }
}
