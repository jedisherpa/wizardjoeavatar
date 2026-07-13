use serde_json::json;
use std::collections::{BTreeMap, BTreeSet};
use wizard_avatar_engine::chat_event::ChatTurnState;
use wizard_avatar_engine::motion_catalog::{
    embedded_motion_graph_json, runtime_geometry_authority, sha256_hex, shadow_motion_catalog,
    EMBEDDED_MOTION_GRAPH_SHA256,
};
use wizard_avatar_engine::motion_graph::{
    CapabilityTier, MotionGraphV1, MotionMarker, PoseUseKind, REQUIRED_RECIPE_IDS,
    REQUIRED_RUNTIME_GEOMETRY_COUNT, REQUIRED_WJFL_GEOMETRY_COUNT,
};
use wizard_avatar_engine::state::Direction;

#[test]
fn embedded_shadow_catalog_is_hash_pinned_and_matches_runtime_authority() {
    let catalog = shadow_motion_catalog().expect("embedded shadow catalog");
    let authority = runtime_geometry_authority().expect("Rust runtime geometry authority");

    assert_eq!(catalog.sha256, EMBEDDED_MOTION_GRAPH_SHA256);
    assert_eq!(
        sha256_hex(embedded_motion_graph_json().as_bytes()),
        EMBEDDED_MOTION_GRAPH_SHA256
    );
    assert_eq!(authority.len(), REQUIRED_RUNTIME_GEOMETRY_COUNT);
    assert_eq!(
        catalog.graph.pose_coverage.len(),
        REQUIRED_RUNTIME_GEOMETRY_COUNT
    );
    catalog
        .graph
        .validate_against_runtime_authority(&authority)
        .expect("catalog matches production Rust pose authority");
}

#[test]
fn every_runtime_geometry_and_wjfl_candidate_is_classified_exactly_once() {
    let catalog = shadow_motion_catalog().expect("embedded shadow catalog");
    let authority = runtime_geometry_authority().expect("Rust runtime geometry authority");
    let runtime_ids = authority
        .iter()
        .map(|row| row.pose_id.as_str())
        .collect::<BTreeSet<_>>();
    let coverage_ids = catalog
        .graph
        .pose_coverage
        .iter()
        .map(|row| row.pose_id.as_str())
        .collect::<BTreeSet<_>>();
    assert_eq!(runtime_ids, coverage_ids);
    assert_eq!(coverage_ids.len(), REQUIRED_RUNTIME_GEOMETRY_COUNT);

    let expected_wjfl = (1..=40)
        .chain(51..=60)
        .map(|number| format!("WJFL-{number:02}"))
        .collect::<BTreeSet<_>>();
    let actual_wjfl = catalog
        .graph
        .pose_coverage
        .iter()
        .filter_map(|row| row.source_candidate_id.as_ref())
        .filter(|candidate_id| candidate_id.starts_with("WJFL-"))
        .cloned()
        .collect::<BTreeSet<_>>();
    assert_eq!(actual_wjfl, expected_wjfl);
    assert_eq!(actual_wjfl.len(), REQUIRED_WJFL_GEOMETRY_COUNT);
}

#[test]
fn capability_tiers_showcases_and_authored_uses_are_accountable() {
    let catalog = shadow_motion_catalog().expect("embedded shadow catalog");
    let referenced = catalog
        .graph
        .clips
        .iter()
        .flat_map(|clip| clip.samples.iter().map(|sample| sample.pose_id.as_str()))
        .collect::<BTreeSet<_>>();
    let mut tier_counts = BTreeMap::new();

    for row in &catalog.graph.pose_coverage {
        *tier_counts.entry(row.capability_tier).or_insert(0usize) += 1;
        assert!(!row.use_kinds.is_empty(), "{} has a use", row.pose_id);
        assert!(
            !row.approved_facings.is_empty(),
            "{} has an approved facing",
            row.pose_id
        );
        if row.capability_tier == CapabilityTier::ShowcaseOnly {
            let approval = row.showcase_approval.as_ref().expect("showcase approval");
            assert_eq!(approval.owner, "MOTION");
            assert!(!approval.rationale.trim().is_empty());
            assert_ne!(approval.fallback_pose_id, row.pose_id);
            assert_eq!(row.use_kinds, [PoseUseKind::Showcase]);
        } else {
            assert!(referenced.contains(row.pose_id.as_str()));
            assert!(row.showcase_approval.is_none());
        }
    }

    assert_eq!(tier_counts[&CapabilityTier::ShowcaseOnly], 10);
    assert_eq!(tier_counts.values().sum::<usize>(), 89);
}

#[test]
fn all_ten_states_resolve_all_eight_facings_to_approved_geometry() {
    let graph = &shadow_motion_catalog()
        .expect("embedded shadow catalog")
        .graph;
    let coverage = graph
        .pose_coverage
        .iter()
        .map(|row| (row.pose_id.as_str(), row))
        .collect::<BTreeMap<_, _>>();
    let actual = graph
        .state_facing_fallbacks
        .iter()
        .map(|row| (row.turn_state, row.requested_facing))
        .collect::<BTreeSet<_>>();
    let expected = ChatTurnState::ALL
        .into_iter()
        .flat_map(|state| {
            Direction::ALL
                .into_iter()
                .map(move |facing| (state, facing))
        })
        .collect::<BTreeSet<_>>();

    assert_eq!(graph.state_facing_fallbacks.len(), 80);
    assert_eq!(actual, expected);
    for fallback in &graph.state_facing_fallbacks {
        let target = coverage[&fallback.fallback_pose_id.as_str()];
        assert!(target.approved_facings.contains(&fallback.requested_facing));
    }
}

#[test]
fn graph_recipes_edges_loops_and_markers_are_closed_and_resolved() {
    let graph = &shadow_motion_catalog()
        .expect("embedded shadow catalog")
        .graph;
    let recipe_ids = graph
        .transition_recipes
        .iter()
        .map(|recipe| recipe.recipe_id.as_str())
        .collect::<BTreeSet<_>>();
    assert_eq!(
        recipe_ids,
        REQUIRED_RECIPE_IDS.into_iter().collect::<BTreeSet<_>>()
    );
    assert_eq!(graph.turn_state_profiles.len(), ChatTurnState::ALL.len());
    assert!(graph
        .clips
        .iter()
        .flat_map(|clip| &clip.samples)
        .all(|sample| recipe_ids.contains(sample.transition_recipe_id.as_str())));
    assert!(graph.clips.iter().all(|clip| {
        clip.samples[0].markers.contains(&clip.entry_marker)
            && clip.exit_markers.iter().all(|marker| {
                clip.samples
                    .iter()
                    .any(|sample| sample.markers.contains(marker))
            })
    }));
}

#[test]
fn catalog_contains_no_runtime_image_or_python_authority() {
    let source = embedded_motion_graph_json().to_ascii_lowercase();
    for forbidden in [".png", ".py", "python", "png_path", "image_path"] {
        assert!(!source.contains(forbidden), "forbidden token {forbidden}");
    }
}

#[test]
fn strict_runtime_validation_rejects_unknown_duplicate_and_missing_ids() {
    let authority = runtime_geometry_authority().expect("Rust runtime geometry authority");
    let graph = &shadow_motion_catalog()
        .expect("embedded shadow catalog")
        .graph;

    let mut unknown = graph.clone();
    unknown.pose_coverage[0].pose_id = "unknown_runtime_geometry".into();
    let unknown_error = unknown
        .validate_against_runtime_authority(&authority)
        .expect_err("unknown pose must fail");
    assert!(unknown_error
        .issues
        .iter()
        .any(|issue| issue.contains("unknown runtime pose")));

    let mut duplicate = graph.clone();
    duplicate.pose_coverage[1].pose_id = duplicate.pose_coverage[0].pose_id.clone();
    let duplicate_error = duplicate
        .validate_against_runtime_authority(&authority)
        .expect_err("duplicate pose must fail");
    assert!(duplicate_error
        .issues
        .iter()
        .any(|issue| issue.contains("duplicate id")));

    let mut missing = graph.clone();
    let removed = missing.pose_coverage.pop().expect("coverage row");
    let missing_error = missing
        .validate_against_runtime_authority(&authority)
        .expect_err("missing pose must fail");
    assert!(missing_error
        .issues
        .iter()
        .any(|issue| issue.contains(&format!("missing runtime pose {}", removed.pose_id))));
}

#[test]
fn strict_runtime_validation_rejects_bad_fallbacks_and_showcase_approvals() {
    let authority = runtime_geometry_authority().expect("Rust runtime geometry authority");
    let graph = &shadow_motion_catalog()
        .expect("embedded shadow catalog")
        .graph;

    let mut missing_cell = graph.clone();
    missing_cell.state_facing_fallbacks.pop();
    assert!(missing_cell
        .validate_against_runtime_authority(&authority)
        .expect_err("missing fallback cell")
        .issues
        .iter()
        .any(|issue| issue.contains("every canonical state/facing pair")));

    let mut wrong_facing = graph.clone();
    wrong_facing.state_facing_fallbacks[0].fallback_pose_id = "back_idle".into();
    assert!(wrong_facing
        .validate_against_runtime_authority(&authority)
        .expect_err("wrong-facing fallback")
        .issues
        .iter()
        .any(|issue| issue.contains("without that facing")));

    let mut duplicate_cell = graph.clone();
    duplicate_cell.state_facing_fallbacks[1] = duplicate_cell.state_facing_fallbacks[0].clone();
    assert!(duplicate_cell
        .validate_against_runtime_authority(&authority)
        .expect_err("duplicate fallback cell")
        .issues
        .iter()
        .any(|issue| issue.contains("repeats")));

    let mut unknown_target = graph.clone();
    unknown_target.state_facing_fallbacks[0].fallback_pose_id = "unknown_pose".into();
    assert!(unknown_target
        .validate_against_runtime_authority(&authority)
        .expect_err("unknown fallback target")
        .issues
        .iter()
        .any(|issue| issue.contains("missing pose unknown_pose")));

    let mut invalid_showcase = graph.clone();
    let showcase = invalid_showcase
        .pose_coverage
        .iter_mut()
        .find(|row| row.capability_tier == CapabilityTier::ShowcaseOnly)
        .expect("showcase row");
    showcase.showcase_approval.as_mut().expect("approval").owner = "".into();
    assert!(invalid_showcase
        .validate_against_runtime_authority(&authority)
        .expect_err("empty showcase owner")
        .issues
        .iter()
        .any(|issue| issue.contains("non-empty owner and rationale")));
}

#[test]
fn malformed_recipe_loop_and_marker_contracts_are_rejected() {
    let graph = &shadow_motion_catalog()
        .expect("embedded shadow catalog")
        .graph;

    let mut bad_recipe = graph.clone();
    bad_recipe.transition_recipes[1].fallback_recipe_id = Some("missing_recipe".into());
    assert!(bad_recipe
        .validate()
        .expect_err("missing recipe fallback")
        .issues
        .iter()
        .any(|issue| issue.contains("invalid fallback recipe")));

    let mut bad_loop = graph.clone();
    let marked = bad_loop
        .clips
        .iter_mut()
        .find(|clip| clip.loop_start_sample.is_some())
        .expect("marked clip");
    marked.loop_end_sample = marked.loop_start_sample;
    assert!(bad_loop
        .validate()
        .expect_err("invalid loop bounds")
        .issues
        .iter()
        .any(|issue| issue.contains("invalid marked_segment")));

    let mut duplicate_entry = graph.clone();
    duplicate_entry.clips[0].samples[1]
        .markers
        .push(MotionMarker::Entry);
    assert!(duplicate_entry
        .validate()
        .expect_err("duplicate entry marker")
        .issues
        .iter()
        .any(|issue| issue.contains("entry_marker must occur exactly once")));

    let mut unknown_marker: serde_json::Value =
        serde_json::from_str(embedded_motion_graph_json()).expect("graph JSON");
    unknown_marker["clips"][0]["samples"][0]["markers"][0] = json!("teleport");
    assert!(serde_json::from_value::<MotionGraphV1>(unknown_marker).is_err());

    let mut unknown_state: serde_json::Value =
        serde_json::from_str(embedded_motion_graph_json()).expect("graph JSON");
    unknown_state["state_facing_fallbacks"][0]["turn_state"] = json!("listen");
    assert!(serde_json::from_value::<MotionGraphV1>(unknown_state).is_err());

    let mut unknown_facing: serde_json::Value =
        serde_json::from_str(embedded_motion_graph_json()).expect("graph JSON");
    unknown_facing["state_facing_fallbacks"][0]["requested_facing"] = json!("front");
    assert!(serde_json::from_value::<MotionGraphV1>(unknown_facing).is_err());
}
