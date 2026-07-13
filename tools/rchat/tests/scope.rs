use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};

use serde_json::Value;
use wizardjoe_rchat_validator::scope::{validate_scope_path, ScopeOptions};

static NEXT_REPOSITORY: AtomicU64 = AtomicU64::new(0);
const BRANCH: &str = "codex/rust-chatbot-animation-engine";

struct TestRepository {
    root: PathBuf,
    registry: PathBuf,
    base_sha: String,
    result_sha: String,
}

impl TestRepository {
    fn new(include_outside_commit: bool) -> Self {
        let unique = NEXT_REPOSITORY.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "wizardjoe-rchat-scope-{}-{unique}",
            std::process::id()
        ));
        fs::create_dir_all(&root).unwrap();
        git(&root, &["init", "--quiet", "--initial-branch", BRANCH]);
        git(&root, &["config", "user.name", "RCHAT Scope"]);
        git(&root, &["config", "user.email", "rchat@example.invalid"]);
        fs::write(root.join("README.md"), "base\n").unwrap();
        git(&root, &["add", "--all"]);
        git(&root, &["commit", "--quiet", "-m", "base"]);
        let base_sha = git_text(&root, &["rev-parse", "HEAD"]);

        fs::create_dir_all(root.join("tools/rchat")).unwrap();
        fs::write(root.join("tools/rchat/foundation.txt"), "allowed\n").unwrap();
        if include_outside_commit {
            fs::write(root.join("outside.txt"), "not owned\n").unwrap();
        }
        git(&root, &["add", "--all"]);
        git(&root, &["commit", "--quiet", "-m", "result"]);
        let result_sha = git_text(&root, &["rev-parse", "HEAD"]);

        let registry = root.join("registry.json");
        let mut value: Value =
            serde_json::from_str(include_str!("fixtures/valid-registry.json")).unwrap();
        value["branch"] = Value::String(BRANCH.to_owned());
        fs::write(&registry, serde_json::to_vec_pretty(&value).unwrap()).unwrap();
        Self {
            root,
            registry,
            base_sha,
            result_sha,
        }
    }

    fn validate(&self, include_worktree: bool) -> wizardjoe_rchat_validator::scope::ScopeReport {
        validate_scope_path(
            &self.registry,
            "RCHAT-FLOW-020",
            ScopeOptions {
                base_ref: &self.base_sha,
                head_ref: &self.result_sha,
                include_worktree,
            },
        )
        .unwrap()
    }
}

impl Drop for TestRepository {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
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
fn allowed_committed_paths_pass_on_registry_branch() {
    let repository = TestRepository::new(false);
    let report = repository.validate(false);
    assert!(report.is_valid(), "{:#?}", report.violations);
    assert_eq!(report.changed_paths, ["tools/rchat/foundation.txt"]);
}

#[test]
fn committed_path_outside_allowlist_fails() {
    let repository = TestRepository::new(true);
    let report = repository.validate(false);
    assert!(report
        .violations
        .iter()
        .any(|violation| violation.code == "RCHAT-SCOPE-PATH"));
}

#[test]
fn untracked_path_is_checked_when_worktree_is_included() {
    let repository = TestRepository::new(false);
    fs::write(repository.root.join("untracked.txt"), "not owned\n").unwrap();
    let report = repository.validate(true);
    assert!(report.violations.iter().any(|violation| {
        violation.code == "RCHAT-SCOPE-PATH" && violation.message.contains("untracked.txt")
    }));
}

#[test]
fn branch_mismatch_fails_accountability() {
    let repository = TestRepository::new(false);
    git(&repository.root, &["switch", "-c", "wrong-branch"]);
    let report = repository.validate(false);
    assert!(report
        .violations
        .iter()
        .any(|violation| violation.code == "RCHAT-SCOPE-BRANCH"));
}
