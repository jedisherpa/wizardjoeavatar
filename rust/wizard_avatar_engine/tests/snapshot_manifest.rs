use serde_json::Value;
use std::collections::BTreeSet;
use std::path::PathBuf;
use wizard_avatar_engine::frame_source::{DEFAULT_COLS, DEFAULT_ROWS};

#[test]
fn generated_snapshot_manifest_covers_required_rust_surfaces() {
    let evidence_dir =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../evidence/wizard/rust-snapshots");
    let manifest_path = evidence_dir.join("manifest.json");
    let manifest: Value =
        serde_json::from_slice(&std::fs::read(&manifest_path).expect("read snapshot manifest"))
            .expect("parse snapshot manifest");
    let snapshots = manifest["snapshots"]
        .as_array()
        .expect("snapshots array exists");

    assert_eq!(manifest["cols"], DEFAULT_COLS);
    assert_eq!(manifest["rows"], DEFAULT_ROWS);
    assert_eq!(snapshots.len(), 30);

    let ids = snapshots
        .iter()
        .map(|snapshot| snapshot["id"].as_str().expect("snapshot id").to_string())
        .collect::<BTreeSet<_>>();
    assert_eq!(
        ids.iter().filter(|id| id.starts_with("direction-")).count(),
        8
    );
    assert_eq!(
        ids.iter()
            .filter(|id| id.starts_with("expression-"))
            .count(),
        10
    );
    assert_eq!(ids.iter().filter(|id| id.starts_with("action-")).count(), 8);
    assert_eq!(
        ids.iter()
            .filter(|id| id.starts_with("walk-phase-"))
            .count(),
        4
    );

    for snapshot in snapshots {
        assert_eq!(snapshot["frame_bytes"], DEFAULT_COLS * DEFAULT_ROWS * 4);
        assert!(
            snapshot["non_background_cells"]
                .as_u64()
                .expect("non-background count")
                > 10_000
        );
        let ppm_path = evidence_dir.join(snapshot["ppm_path"].as_str().expect("ppm path"));
        let header = std::fs::read(&ppm_path).expect("read ppm");
        assert!(header.starts_with(b"P6\n"));
    }
}
