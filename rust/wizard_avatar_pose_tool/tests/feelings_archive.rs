use std::collections::BTreeSet;
use std::path::PathBuf;
use wizard_avatar_pose_tool::load_archive;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

#[test]
fn archive_admits_exactly_fifty_unique_wjfl_sources_after_the_original_thirty() {
    let archive = load_archive(repo_root()).expect("load combined Rust pose archive");

    assert_eq!(archive.poses.len(), 80);
    assert_eq!(archive.poses[29].candidate_id, "WJFA-20");
    assert_eq!(archive.poses[30].candidate_id, "WJFL-01");
    assert_eq!(archive.poses[69].candidate_id, "WJFL-40");
    assert_eq!(archive.poses[70].candidate_id, "WJFL-51");
    assert_eq!(archive.poses[79].candidate_id, "WJFL-60");

    let feelings = &archive.poses[30..];
    assert_eq!(feelings.len(), 50);
    assert_eq!(
        feelings
            .iter()
            .map(|pose| pose.source_sha256.as_str())
            .collect::<BTreeSet<_>>()
            .len(),
        50
    );
    assert!(feelings.iter().all(|pose| pose.status == "INTEGRATED_RUST"));
    assert!(!feelings
        .iter()
        .any(|pose| ("WJFL-41"..="WJFL-50").contains(&pose.candidate_id.as_str())));

    for (index, pose) in archive.poses.iter().enumerate() {
        assert_eq!(pose.order, index as u32 + 1, "{}", pose.candidate_id);
        assert!(!pose.semantic_id.is_empty(), "{}", pose.candidate_id);
    }
}
