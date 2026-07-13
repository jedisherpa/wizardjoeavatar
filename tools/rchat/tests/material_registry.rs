use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};

use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use wizardjoe_rchat_validator::{validate_registry_path, ValidationReport};

static NEXT_REPOSITORY: AtomicU64 = AtomicU64::new(0);
const EVIDENCE_BYTES: &[u8] = b"material receipt\n";

struct TestRepository {
    root: PathBuf,
    registry: PathBuf,
    base_sha: String,
    result_sha: String,
}

impl TestRepository {
    fn new() -> Self {
        let unique = NEXT_REPOSITORY.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "wizardjoe-rchat-validator-{}-{unique}",
            std::process::id()
        ));
        fs::create_dir_all(&root).unwrap();
        git(&root, &["init", "--quiet"]);
        git(&root, &["config", "user.name", "RCHAT Validator"]);
        git(&root, &["config", "user.email", "rchat@example.invalid"]);

        fs::write(root.join("README.md"), "base\n").unwrap();
        git(&root, &["add", "--all"]);
        git(&root, &["commit", "--quiet", "-m", "base"]);
        let base_sha = git_text(&root, &["rev-parse", "HEAD"]);

        fs::create_dir_all(root.join("evidence")).unwrap();
        fs::write(root.join("evidence/report.txt"), EVIDENCE_BYTES).unwrap();
        git(&root, &["add", "--all"]);
        git(&root, &["commit", "--quiet", "-m", "result"]);
        let result_sha = git_text(&root, &["rev-parse", "HEAD"]);

        let registry = root.join("registry.json");
        let repository = Self {
            root,
            registry,
            base_sha,
            result_sha,
        };
        repository.write_registry(repository.valid_registry());
        repository
    }

    fn valid_registry(&self) -> Value {
        let mut value: Value =
            serde_json::from_str(include_str!("fixtures/valid-registry.json")).unwrap();
        let hash = format!("{:x}", Sha256::digest(EVIDENCE_BYTES));
        for collection in ["work_items", "specialist_work_items"] {
            for item in value[collection].as_array_mut().unwrap() {
                if item["status"] != "ACCEPTED" {
                    continue;
                }
                item["base_sha"] = json!(self.base_sha);
                item["result_sha"] = json!(self.result_sha);
                item["path_allowlist"] = json!(["evidence"]);
                item["evidence"] = json!([{
                    "path": "evidence/report.txt",
                    "sha256": hash.clone()
                }]);
            }
        }
        value["integration_head"] = json!(self.result_sha);
        value["planning_checkpoint"]["local_sha"] = json!(self.result_sha);
        value["planning_checkpoint"]["remote_sha"] = json!(self.result_sha);
        value["gates"][0]["record"]["git_sha"] = json!(self.result_sha);
        value["gates"][0]["record"]["remote_sha"] = json!(self.result_sha);
        value
    }

    fn write_registry(&self, value: Value) {
        fs::write(&self.registry, serde_json::to_vec_pretty(&value).unwrap()).unwrap();
    }

    fn validate(&self) -> ValidationReport {
        validate_registry_path(&self.registry).unwrap()
    }
}

impl Drop for TestRepository {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

fn parent_item_mut(value: &mut Value) -> &mut Value {
    &mut value["work_items"][0]
}

fn codes(report: &ValidationReport) -> HashSet<&'static str> {
    report
        .violations
        .iter()
        .map(|violation| violation.code)
        .collect()
}

fn git(repository: &Path, args: &[&str]) -> Output {
    let output = Command::new("git")
        .arg("-C")
        .arg(repository)
        .args(args)
        .env("LC_ALL", "C")
        .env("LANG", "C")
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "git {} failed: {}",
        args.join(" "),
        String::from_utf8_lossy(&output.stderr)
    );
    output
}

fn git_text(repository: &Path, args: &[&str]) -> String {
    String::from_utf8(git(repository, args).stdout)
        .unwrap()
        .trim()
        .to_owned()
}

#[test]
fn accepted_material_receipt_passes_and_is_deterministic() {
    let repository = TestRepository::new();
    let first = repository.validate();
    let second = repository.validate();

    assert!(first.is_valid(), "{:#?}", first.violations);
    assert_eq!(first, second);
}

#[test]
fn rejects_nonexistent_base_and_result_commits() {
    let repository = TestRepository::new();
    let mut value = repository.valid_registry();
    let missing_base = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee";
    let missing = "ffffffffffffffffffffffffffffffffffffffff";
    parent_item_mut(&mut value)["base_sha"] = json!(missing_base);
    parent_item_mut(&mut value)["result_sha"] = json!(missing);
    value["gates"][0]["record"]["git_sha"] = json!(missing);
    value["gates"][0]["record"]["remote_sha"] = json!(missing);
    repository.write_registry(value);

    let found = codes(&repository.validate());
    assert!(found.contains("RCHAT-GIT-BASE-COMMIT"));
    assert!(found.contains("RCHAT-GIT-RESULT-COMMIT"));
}

#[test]
fn rejects_mismatched_evidence_hash() {
    let repository = TestRepository::new();
    let mut value = repository.valid_registry();
    parent_item_mut(&mut value)["evidence"][0]["sha256"] =
        json!("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    repository.write_registry(value);

    assert!(codes(&repository.validate()).contains("RCHAT-EVIDENCE-HASH-MISMATCH"));
}

#[test]
fn rejects_unsafe_evidence_path() {
    let repository = TestRepository::new();
    let mut value = repository.valid_registry();
    parent_item_mut(&mut value)["evidence"][0]["path"] = json!("../outside.txt");
    repository.write_registry(value);

    assert!(codes(&repository.validate()).contains("RCHAT-EVIDENCE-PATH-UNSAFE"));
}

#[test]
fn rejects_missing_evidence_path() {
    let repository = TestRepository::new();
    let mut value = repository.valid_registry();
    parent_item_mut(&mut value)["evidence"][0]["path"] = json!("evidence/missing.txt");
    repository.write_registry(value);

    assert!(codes(&repository.validate()).contains("RCHAT-EVIDENCE-MISSING"));
}

#[test]
fn rejects_out_of_scope_diff() {
    let repository = TestRepository::new();
    let mut value = repository.valid_registry();
    parent_item_mut(&mut value)["path_allowlist"] = json!(["allowed"]);
    repository.write_registry(value);

    assert!(codes(&repository.validate()).contains("RCHAT-PATH-OUT-OF-SCOPE"));
}
