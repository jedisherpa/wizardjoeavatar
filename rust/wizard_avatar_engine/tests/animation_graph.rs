use std::collections::BTreeSet;
use wizard_avatar_engine::animation::reference_pose_id_for_state;
use wizard_avatar_engine::reference_avatar::{
    reference_animation_graph, reference_animation_graph_available,
    reference_animation_graph_pose_ids, reference_pose_ids,
};
use wizard_avatar_engine::state::{Direction, WizardState};

#[test]
fn animation_graph_references_only_existing_pose_ids() {
    assert!(reference_animation_graph_available());

    let library_ids = reference_pose_ids().into_iter().collect::<BTreeSet<_>>();
    let graph_ids = reference_animation_graph_pose_ids();
    assert!(!graph_ids.is_empty());

    for pose_id in graph_ids {
        assert!(
            library_ids.contains(&pose_id),
            "graph references missing pose {pose_id}"
        );
    }
}

#[test]
fn animation_graph_covers_facings_while_runtime_keeps_one_base_pose_per_view() {
    let graph = reference_animation_graph().expect("animation graph");
    let facings = [
        Direction::South,
        Direction::SouthWest,
        Direction::West,
        Direction::NorthWest,
        Direction::North,
        Direction::NorthEast,
        Direction::East,
        Direction::SouthEast,
    ];

    for facing in facings {
        assert!(
            graph.idle_pose_for_facing(facing.as_str()).is_some(),
            "idle facing {facing:?} has graph pose"
        );
        assert!(
            graph
                .walking_pose_for_facing_phase(facing.as_str(), 0.0)
                .is_some(),
            "walking facing {facing:?} has graph clip"
        );
    }

    for facing in Direction::ALL {
        let state = WizardState {
            facing,
            ..WizardState::default()
        };
        let base = reference_pose_id_for_state(&state);
        let mut animated = state.clone();
        animated.walk_phase = 0.5;
        assert_eq!(reference_pose_id_for_state(&animated), base);
    }
}
