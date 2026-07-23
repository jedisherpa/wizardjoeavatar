use serde_json::json;
use std::collections::{BTreeMap, BTreeSet};
use wizard_avatar_engine::controller::{WizardAvatarController, WizardCommand};
use wizard_avatar_engine::pose_graph_runtime::{
    project_runtime_pose_graph, runtime_pose_graph_catalog, RuntimePoseGraphEntry,
    RUNTIME_POSE_GRAPH_COUNT,
};

fn command(controller: &mut WizardAvatarController, pose_id: &str, transition_ms: u64) {
    let result = controller.apply_command(WizardCommand::new(
        "pose",
        json!({"pose_id": pose_id, "transition_ms": transition_ms}),
    ));
    assert!(result.ok, "{}: {}", pose_id, result.message);
}

fn assert_exact_promoted_graph(entry: &RuntimePoseGraphEntry) {
    assert!(entry.primary_for_semantic_id);
    assert!(entry.exact_rgba_equal);
    assert_eq!(entry.silhouette_iou_millionths, 1_000_000);
    assert_eq!(entry.foreground_color_fidelity_millionths, 1_000_000);
    assert_eq!(entry.foreground_color_match_ratio_millionths, 1_000_000);
    assert_eq!(entry.rgba_mismatch_pixel_count, 0);
    assert_eq!(entry.rgba_mismatch_channel_count, 0);

    let raster = project_runtime_pose_graph(&entry.semantic_id)
        .unwrap_or_else(|error| panic!("project {}: {error}", entry.semantic_id));
    assert_eq!(raster.entry.source_record_id, entry.source_record_id);
    assert_eq!(
        [u32::from(raster.width), u32::from(raster.height)],
        entry.frame
    );
    assert_eq!(
        raster
            .coverage_mask
            .iter()
            .map(|value| u64::from(*value))
            .sum::<u64>(),
        entry.foreground_pixel_count
    );
    assert_eq!(
        raster.rgba.len(),
        usize::from(raster.width) * usize::from(raster.height) * 4
    );
}

#[test]
fn every_authored_production_alpha_neighbor_is_exact_and_controller_reachable() {
    let catalog = runtime_pose_graph_catalog().expect("runtime pose graph catalog");
    let entries = &catalog.manifest().entries;
    assert_eq!(entries.len(), RUNTIME_POSE_GRAPH_COUNT);

    let by_semantic = entries
        .iter()
        .map(|entry| (entry.semantic_id.as_str(), entry))
        .collect::<BTreeMap<_, _>>();
    assert_eq!(by_semantic.len(), RUNTIME_POSE_GRAPH_COUNT);

    for entry in entries {
        assert_exact_promoted_graph(entry);
    }

    let mut directed_edges = BTreeSet::new();
    for target in entries {
        for source_id in &target.authored_transition_neighbors {
            let source = by_semantic.get(source_id.as_str()).unwrap_or_else(|| {
                panic!(
                    "{} references missing transition neighbor {source_id}",
                    target.semantic_id
                )
            });
            assert!(directed_edges.insert((source.semantic_id.clone(), target.semantic_id.clone())));

            let mut controller = WizardAvatarController::default();
            command(&mut controller, &source.semantic_id, 1);
            controller.advance(0.1);
            command(&mut controller, &target.semantic_id, 240);

            let state = controller.current_state();
            assert_eq!(state.pose_id.as_deref(), Some(target.semantic_id.as_str()));
            assert_eq!(
                state.previous_pose_id.as_deref(),
                Some(source.semantic_id.as_str())
            );
            assert!(!state.pose_handoff);

            for _ in 0..20 {
                if controller.current_state().pose_handoff {
                    break;
                }
                controller.step_tick();
            }
            let state = controller.current_state();
            assert!(
                state.pose_handoff,
                "{} -> {}",
                source.semantic_id, target.semantic_id
            );
            assert_eq!(state.pose_id.as_deref(), Some(target.semantic_id.as_str()));
        }
    }

    assert_eq!(
        directed_edges.len(),
        480,
        "production-alpha authored transition census changed"
    );
}
