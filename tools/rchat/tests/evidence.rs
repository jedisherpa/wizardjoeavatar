use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use wizardjoe_rchat_validator::evidence::{
    validate_evidence_paths, write_evidence, EvidenceRun, EvidenceStatus, FRAME_SCHEMA,
    MANIFEST_SCHEMA,
};

static NEXT_DIRECTORY: AtomicU64 = AtomicU64::new(0);

struct TestDirectory(PathBuf);

impl TestDirectory {
    fn new() -> Self {
        let unique = NEXT_DIRECTORY.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "wizardjoe-rchat-evidence-{}-{unique}",
            std::process::id()
        ));
        fs::create_dir_all(&path).unwrap();
        Self(path)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TestDirectory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn run() -> EvidenceRun {
    serde_json::from_str(include_str!("fixtures/evidence-run.json")).unwrap()
}

#[test]
fn evidence_output_is_deterministic_and_round_trips() {
    let first = TestDirectory::new();
    let second = TestDirectory::new();
    let first_ledger = first.path().join("frames.ndjson");
    let first_manifest = first.path().join("manifest.json");
    let second_ledger = second.path().join("frames.ndjson");
    let second_manifest = second.path().join("manifest.json");

    let written = write_evidence(&run(), &first_ledger, &first_manifest).unwrap();
    write_evidence(&run(), &second_ledger, &second_manifest).unwrap();
    let validated = validate_evidence_paths(&first_ledger, &first_manifest).unwrap();

    assert_eq!(written.status, EvidenceStatus::Pass);
    assert_eq!(written, validated);
    assert_eq!(
        fs::read(first_ledger).unwrap(),
        fs::read(second_ledger).unwrap()
    );
    assert_eq!(
        fs::read(first_manifest).unwrap(),
        fs::read(second_manifest).unwrap()
    );
}

#[test]
fn empty_run_requires_explicit_skip_and_never_passes() {
    let directory = TestDirectory::new();
    let mut input = run();
    input.frames.clear();
    assert!(write_evidence(
        &input,
        &directory.path().join("empty.ndjson"),
        &directory.path().join("empty.json")
    )
    .is_err());

    input.skips.push("browser tooling unavailable".to_owned());
    let manifest = write_evidence(
        &input,
        &directory.path().join("skip.ndjson"),
        &directory.path().join("skip.json"),
    )
    .unwrap();
    assert_eq!(manifest.status, EvidenceStatus::Skip);
}

#[test]
fn quality_failure_forces_fail_receipt() {
    let directory = TestDirectory::new();
    let mut input = run();
    input.frames[1]
        .quality_failures
        .push("detached component".to_owned());
    let manifest = write_evidence(
        &input,
        &directory.path().join("frames.ndjson"),
        &directory.path().join("manifest.json"),
    )
    .unwrap();
    assert_eq!(manifest.status, EvidenceStatus::Fail);
    assert_eq!(manifest.quality_failure_count, 1);
}

#[test]
fn ledger_mutation_is_detected() {
    let directory = TestDirectory::new();
    let ledger = directory.path().join("frames.ndjson");
    let manifest = directory.path().join("manifest.json");
    write_evidence(&run(), &ledger, &manifest).unwrap();
    fs::write(&ledger, b"{}\n").unwrap();

    assert!(validate_evidence_paths(&ledger, &manifest)
        .unwrap_err()
        .contains("SHA-256"));
}

#[test]
fn evidence_schemas_and_fixture_name_the_same_contract() {
    let frame_schema: serde_json::Value = serde_json::from_str(include_str!(
        "../../../schemas/rchat/evidence-frame-v1.schema.json"
    ))
    .unwrap();
    let manifest_schema: serde_json::Value = serde_json::from_str(include_str!(
        "../../../schemas/rchat/evidence-manifest-v1.schema.json"
    ))
    .unwrap();
    let fixture = run();

    assert_eq!(frame_schema["title"], FRAME_SCHEMA);
    assert_eq!(manifest_schema["title"], MANIFEST_SCHEMA);
    assert_eq!(fixture.frames[0].schema, FRAME_SCHEMA);
    assert_eq!(frame_schema["additionalProperties"], false);
    assert_eq!(manifest_schema["additionalProperties"], false);
}
