use serde_json::Value;
use std::collections::BTreeSet;
use std::path::PathBuf;

#[test]
fn generated_performance_manifest_covers_required_profiles() {
    let evidence_dir =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../evidence/wizard/rust-performance");
    let manifest_path = evidence_dir.join("performance-summary.json");
    let manifest: Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).expect("read performance manifest"))
            .expect("parse performance manifest");
    let profiles = manifest["profiles"].as_array().expect("profiles array");
    let names = profiles
        .iter()
        .map(|profile| profile["name"].as_str().expect("profile name").to_string())
        .collect::<BTreeSet<_>>();
    assert_eq!(
        names,
        BTreeSet::from(["high".to_string(), "low".to_string(), "medium".to_string()])
    );

    for profile in profiles {
        assert!(profile["target_met"].as_bool().expect("target_met"));
        assert!(
            profile["compression_ratio"]
                .as_f64()
                .expect("compression ratio")
                < 0.25
        );
        assert!(
            profile["keyframes"].as_u64().expect("keyframes") >= 1,
            "profile should include keyframe evidence"
        );
        assert!(
            profile["codec_tag_counts"]
                .as_object()
                .expect("tag counts")
                .contains_key("2"),
            "profile should include delta frames"
        );
    }
}
