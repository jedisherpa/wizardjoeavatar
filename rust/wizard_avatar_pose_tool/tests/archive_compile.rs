use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;
use wizard_avatar_pose_tool::{
    compile_archive, compile_archive_bytes, compile_archive_with_admission_trace, load_archive,
    validate_compiled_archive, write_compiled_archive, AnchorId, CatalogRecordKind, CompilerConfig,
    ContactMode, Point, RegionId,
};

const BASELINE_POSE_IDS: [&str; 10] = [
    "front_idle",
    "back_idle",
    "profile_left",
    "profile_right",
    "walk_front_left",
    "walk_front_right",
    "back_left",
    "back_right",
    "explaining",
    "magic_cast",
];

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

#[test]
fn all_eighty_archived_records_compile_twice_to_identical_schema_v4() {
    let archive = load_archive(repo_root()).expect("validate 80-record archive");
    assert_eq!(archive.poses.len(), 80);
    assert_eq!(archive.poses.first().unwrap().candidate_id, "WJP2-01");
    assert_eq!(archive.poses.last().unwrap().candidate_id, "WJFL-60");

    let (first, admissions) =
        compile_archive_with_admission_trace(&archive, CompilerConfig::default())
            .expect("first serial compile");
    let second = compile_archive(&archive, CompilerConfig::default()).expect("second compile");
    validate_compiled_archive(&first).expect("validate schema v4 artifact");
    let first_bytes = compile_archive_bytes(&first).expect("first serialization");
    let second_bytes = compile_archive_bytes(&second).expect("second serialization");
    assert_eq!(first, second);
    assert_eq!(first_bytes, second_bytes);

    assert_eq!(first.schema_version, 4);
    assert_eq!(first.catalog_count, 80);
    assert_eq!(first.unique_geometry_count, 79);
    assert_eq!(first.alias_count, 1);
    assert_eq!(first.catalog.len(), 80);
    assert_eq!(first.poses.len(), 79);
    assert_eq!(first.aliases.len(), 1);
    assert_eq!(first.archive_sha256.len(), 64);

    assert_eq!(admissions.len(), 80);
    for (index, admission) in admissions.iter().enumerate() {
        assert_eq!(admission.order, index as u32 + 1);
        assert_eq!(admission.cumulative_catalog_count, index + 1);
        assert_eq!(
            admission.cumulative_geometry_count + admission.cumulative_alias_count,
            index + 1
        );
    }
    assert_eq!(admissions[30].candidate_id, "WJFL-01");
    assert_eq!(admissions[79].candidate_id, "WJFL-60");
    assert!(admissions[30..]
        .iter()
        .all(|admission| admission.geometry_sha256.len() == 64));

    let alias = &first.aliases[0];
    assert_eq!(alias.candidate_id, "WJFA-10");
    assert_eq!(alias.semantic_id, "fly_front_hover_ready");
    assert_eq!(alias.target_semantic_id, "fly_front_hover_neutral");
    assert!(!first
        .poses
        .iter()
        .any(|pose| pose.semantic_id == alias.semantic_id));
    let alias_record = first
        .catalog
        .iter()
        .find(|record| record.candidate_id == "WJFA-10")
        .expect("alias catalog record");
    assert_eq!(alias_record.kind, CatalogRecordKind::Alias);
    assert_eq!(alias_record.geometry_id, alias.target_semantic_id);

    let geometry_ids = first
        .poses
        .iter()
        .map(|pose| pose.semantic_id.as_str())
        .collect::<BTreeSet<_>>();
    assert_eq!(geometry_ids.len(), 79);
    let allowed_neighbor_ids = geometry_ids
        .iter()
        .copied()
        .chain(BASELINE_POSE_IDS)
        .collect::<BTreeSet<_>>();
    for pose in &first.poses {
        assert_eq!(pose.canonical_size, [72, 96], "{}", pose.candidate_id);
        assert_eq!(
            pose.root_anchor,
            Point { x: 36, y: 95 },
            "{}",
            pose.candidate_id
        );
        assert!(!pose.cells.is_empty(), "{}", pose.candidate_id);
        assert_eq!(pose.cell_count, pose.cells.len(), "{}", pose.candidate_id);
        assert_eq!(pose.source_sha256.len(), 64, "{}", pose.candidate_id);
        assert_eq!(pose.cell_sha256.len(), 64, "{}", pose.candidate_id);
        assert_eq!(pose.semantic_sha256.len(), 64, "{}", pose.candidate_id);
        assert_eq!(pose.anchors.len(), 25, "{}", pose.candidate_id);
        assert_eq!(pose.z_order, RegionId::Z_ORDER, "{}", pose.candidate_id);
        assert_eq!(
            pose.anchors
                .iter()
                .map(|anchor| anchor.id)
                .collect::<BTreeSet<_>>(),
            AnchorId::REQUIRED.into_iter().collect(),
            "{}",
            pose.candidate_id
        );
        assert!(
            pose.cells
                .iter()
                .all(|cell| (0..72).contains(&cell.x) && (0..96).contains(&cell.y)),
            "{}",
            pose.candidate_id
        );
        assert_eq!(
            pose.cells
                .iter()
                .map(|cell| (cell.x, cell.y))
                .collect::<BTreeSet<_>>()
                .len(),
            pose.cells.len(),
            "{}",
            pose.candidate_id
        );
        let region_counts = pose.cells.iter().fold(BTreeMap::new(), |mut counts, cell| {
            *counts.entry(cell.region).or_insert(0usize) += 1;
            counts
        });
        for region in RegionId::ALL {
            if region != RegionId::Effect || pose.presence.effect {
                assert!(
                    region_counts.contains_key(&region),
                    "{} {region:?}",
                    pose.candidate_id
                );
            }
        }
        assert_eq!(
            pose.presence.effect,
            region_counts.contains_key(&RegionId::Effect),
            "{}",
            pose.candidate_id
        );
        assert_eq!(
            pose.motion.contact_mode == ContactMode::Airborne,
            pose.contact_sets.is_empty(),
            "{}",
            pose.candidate_id
        );
        assert!(
            pose.motion
                .authored_transition_neighbors
                .iter()
                .all(|neighbor| allowed_neighbor_ids.contains(neighbor.as_str())),
            "{}",
            pose.candidate_id
        );
        let anchor_ids = pose
            .anchors
            .iter()
            .map(|anchor| anchor.id)
            .collect::<BTreeSet<_>>();
        for edge in &pose.attachment_edges {
            assert!(region_counts.contains_key(&edge.parent_region));
            assert!(region_counts.contains_key(&edge.child_region));
            assert!(anchor_ids.contains(&edge.parent_anchor));
            assert!(anchor_ids.contains(&edge.child_anchor));
        }
    }

    for record in &first.catalog {
        assert!(geometry_ids.contains(record.geometry_id.as_str()));
        assert_eq!(record.source_sha256.len(), 64);
    }

    for (full, close) in [
        ("feeling_joy_full", "feeling_joy_close"),
        ("feeling_sadness_full", "feeling_sadness_close"),
        ("feeling_anger_full", "feeling_anger_close"),
        ("feeling_fear_full", "feeling_fear_close"),
        ("feeling_shame_full", "feeling_shame_close"),
        ("feeling_disgust_full", "feeling_disgust_close"),
        ("feeling_surprise_full", "feeling_surprise_close"),
        ("feeling_pride_full", "feeling_pride_close"),
        ("feeling_guilt_full", "feeling_guilt_close"),
        ("feeling_love_full", "feeling_love_close"),
    ] {
        let full = first
            .poses
            .iter()
            .find(|pose| pose.semantic_id == full)
            .unwrap();
        let close = first
            .poses
            .iter()
            .find(|pose| pose.semantic_id == close)
            .unwrap();
        assert_ne!(full.cell_sha256, close.cell_sha256);
        assert_eq!(full.root_anchor, close.root_anchor);
        assert_eq!(full.contact_sets, close.contact_sets);
    }

    let authored_neighbors = first
        .poses
        .iter()
        .flat_map(|pose| &pose.motion.authored_transition_neighbors)
        .map(String::as_str)
        .collect::<BTreeSet<_>>();
    for baseline in [
        "front_idle",
        "walk_front_left",
        "walk_front_right",
        "explaining",
        "magic_cast",
    ] {
        assert!(authored_neighbors.contains(baseline), "missing {baseline}");
    }

    let mut invalid = first.clone();
    invalid.poses[0]
        .motion
        .authored_transition_neighbors
        .push("not_a_pose".to_string());
    assert!(validate_compiled_archive(&invalid).is_err());

    let text = String::from_utf8_lossy(&first_bytes).to_ascii_lowercase();
    assert!(!text.contains(".png"));
    assert!(!text.contains("source_path"));

    let output = PathBuf::from(format!(
        "target/test-temp/schema-v4-all-80-{}/compiled.json",
        std::process::id()
    ));
    let written = write_compiled_archive(&first, &output).expect("write test artifact");
    assert_eq!(
        std::fs::read(written).expect("read test artifact"),
        first_bytes
    );
}
