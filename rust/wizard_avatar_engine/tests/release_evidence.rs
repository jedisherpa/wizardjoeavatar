#[allow(dead_code)]
#[path = "../../../tools/rchat/src/evidence.rs"]
mod rchat_evidence;

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use rchat_evidence::{validate_evidence_paths, write_evidence, EvidenceRun, EvidenceStatus};

static NEXT_DIRECTORY: AtomicU64 = AtomicU64::new(0);

struct TestDirectory(PathBuf);

impl TestDirectory {
    fn new() -> Self {
        let unique = NEXT_DIRECTORY.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "wizard-avatar-release-evidence-{}-{unique}",
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

fn fixture() -> EvidenceRun {
    serde_json::from_str(include_str!(
        "../../../tools/rchat/tests/fixtures/evidence-run.json"
    ))
    .unwrap()
}

#[test]
fn release_evidence_is_deterministic_and_self_validating() {
    let first = TestDirectory::new();
    let second = TestDirectory::new();
    let first_ledger = first.path().join("frames.ndjson");
    let first_manifest = first.path().join("manifest.json");
    let second_ledger = second.path().join("frames.ndjson");
    let second_manifest = second.path().join("manifest.json");

    let receipt = write_evidence(&fixture(), &first_ledger, &first_manifest).unwrap();
    write_evidence(&fixture(), &second_ledger, &second_manifest).unwrap();

    assert_eq!(receipt.status, EvidenceStatus::Pass);
    assert_eq!(
        validate_evidence_paths(&first_ledger, &first_manifest).unwrap(),
        receipt
    );
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
fn release_evidence_schemas_are_parseable_and_versioned() {
    let repository = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let frame: serde_json::Value = serde_json::from_slice(
        &fs::read(repository.join("schemas/rchat/evidence-frame-v1.schema.json")).unwrap(),
    )
    .unwrap();
    let manifest: serde_json::Value = serde_json::from_slice(
        &fs::read(repository.join("schemas/rchat/evidence-manifest-v1.schema.json")).unwrap(),
    )
    .unwrap();

    assert_eq!(frame["title"], rchat_evidence::FRAME_SCHEMA);
    assert_eq!(manifest["title"], rchat_evidence::MANIFEST_SCHEMA);
    assert_eq!(frame["additionalProperties"], false);
    assert_eq!(manifest["additionalProperties"], false);
}

#[test]
fn release_evidence_cannot_pass_without_frames() {
    let directory = TestDirectory::new();
    let mut input = fixture();
    input.frames.clear();
    assert!(write_evidence(
        &input,
        &directory.path().join("frames.ndjson"),
        &directory.path().join("manifest.json")
    )
    .is_err());
}

#[test]
fn q0_ci_defines_accountable_required_checks() {
    let repository = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let workflow =
        fs::read_to_string(repository.join(".github/workflows/rust-chatbot-ci.yml")).unwrap();

    for check in [
        "rchat-contracts",
        "rchat-rust",
        "rchat-motion",
        "rchat-evidence",
        "rchat-browser",
    ] {
        assert!(
            workflow.contains(&format!("name: {check}")),
            "missing CI check {check}"
        );
    }
    assert!(workflow.contains("RCHAT-FLOW-060 --base"));
    assert!(workflow.contains("--head \"$result_sha\""));
    assert!(workflow.contains("--unavailable-policy fail"));
    assert!(!workflow.contains("continue-on-error"));
}
