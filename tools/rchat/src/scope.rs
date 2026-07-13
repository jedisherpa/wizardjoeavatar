//! Branch-aware work-item path scope validation.

use serde_json::Value;
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;
use std::process::{Command, Output};

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ScopeOptions<'a> {
    pub base_ref: &'a str,
    pub head_ref: &'a str,
    pub include_worktree: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ScopeViolation {
    pub code: &'static str,
    pub path: String,
    pub message: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ScopeReport {
    pub work_id: String,
    pub branch: String,
    pub changed_paths: Vec<String>,
    pub violations: Vec<ScopeViolation>,
}

impl ScopeReport {
    pub fn is_valid(&self) -> bool {
        self.violations.is_empty()
    }
}

pub fn validate_scope_path(
    registry_path: &Path,
    work_id: &str,
    options: ScopeOptions<'_>,
) -> Result<ScopeReport, String> {
    let registry_bytes = fs::read(registry_path)
        .map_err(|error| format!("failed to read {}: {error}", registry_path.display()))?;
    let registry: Value = serde_json::from_slice(&registry_bytes)
        .map_err(|error| format!("failed to parse {}: {error}", registry_path.display()))?;
    let root = repository_root(registry_path)?;
    let expected_branch = registry
        .get("branch")
        .and_then(Value::as_str)
        .ok_or_else(|| "registry branch must be a string".to_owned())?;
    let current_branch =
        git_text(&root, &["symbolic-ref", "--quiet", "--short", "HEAD"]).unwrap_or_default();
    let mut violations = Vec::new();
    if current_branch != expected_branch {
        violations.push(ScopeViolation {
            code: "RCHAT-SCOPE-BRANCH",
            path: "$.branch".to_owned(),
            message: format!(
                "registry branch {expected_branch} does not match current branch {}; check out the accountable branch before scope validation",
                if current_branch.is_empty() {
                    "<detached>"
                } else {
                    &current_branch
                }
            ),
        });
    }

    let (item_path, item) = find_item(&registry, work_id)
        .ok_or_else(|| format!("work item {work_id} does not exist in the registry"))?;
    let allowlist: Vec<&str> = item
        .get("path_allowlist")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    resolve_commit(&root, options.base_ref, "base")?;
    resolve_commit(&root, options.head_ref, "head")?;

    let mut changed_paths = BTreeSet::new();
    extend_diff_paths(
        &root,
        &[
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            options.base_ref,
            options.head_ref,
            "--",
        ],
        &mut changed_paths,
    )?;
    if options.include_worktree {
        extend_diff_paths(
            &root,
            &[
                "diff",
                "--name-only",
                "--no-renames",
                "-z",
                options.head_ref,
                "--",
            ],
            &mut changed_paths,
        )?;
        extend_diff_paths(
            &root,
            &[
                "diff",
                "--cached",
                "--name-only",
                "--no-renames",
                "-z",
                "--",
            ],
            &mut changed_paths,
        )?;
        let untracked = run_git(&root, &["ls-files", "--others", "--exclude-standard", "-z"])?;
        if !untracked.status.success() {
            return Err(format!(
                "failed to enumerate untracked paths: {}",
                git_stderr(&untracked)
            ));
        }
        extend_nul_paths(&untracked.stdout, &mut changed_paths)?;
    }

    for changed_path in &changed_paths {
        if !allowlist
            .iter()
            .any(|allowed| path_is_allowlisted(changed_path, allowed))
        {
            violations.push(ScopeViolation {
                code: "RCHAT-SCOPE-PATH",
                path: format!("{item_path}.path_allowlist"),
                message: format!(
                    "{work_id} does not allow changed path {changed_path}; move the change to its owner or update the registry under coordinator lock"
                ),
            });
        }
    }
    violations.sort_by(|left, right| {
        (&left.path, left.code, &left.message).cmp(&(&right.path, right.code, &right.message))
    });
    Ok(ScopeReport {
        work_id: work_id.to_owned(),
        branch: current_branch,
        changed_paths: changed_paths.into_iter().collect(),
        violations,
    })
}

fn find_item<'a>(registry: &'a Value, work_id: &str) -> Option<(String, &'a Value)> {
    for collection in ["work_items", "specialist_work_items"] {
        for (index, item) in registry.get(collection)?.as_array()?.iter().enumerate() {
            if item.get("id").and_then(Value::as_str) == Some(work_id) {
                return Some((format!("$.{collection}[{index}]"), item));
            }
        }
    }
    None
}

fn repository_root(registry_path: &Path) -> Result<std::path::PathBuf, String> {
    let start = registry_path.parent().unwrap_or_else(|| Path::new("."));
    let output = run_git(start, &["rev-parse", "--show-toplevel"])?;
    if !output.status.success() {
        return Err(format!(
            "cannot locate repository for {}: {}",
            registry_path.display(),
            git_stderr(&output)
        ));
    }
    let root = String::from_utf8(output.stdout)
        .map_err(|error| format!("repository root is not UTF-8: {error}"))?;
    Ok(root.trim().into())
}

fn resolve_commit(repository: &Path, reference: &str, label: &str) -> Result<(), String> {
    let object = format!("{reference}^{{commit}}");
    let output = run_git(repository, &["cat-file", "-e", &object])?;
    if output.status.success() {
        Ok(())
    } else {
        Err(format!(
            "scope {label} ref {reference} does not resolve to a commit: {}",
            git_stderr(&output)
        ))
    }
}

fn extend_diff_paths(
    repository: &Path,
    args: &[&str],
    paths: &mut BTreeSet<String>,
) -> Result<(), String> {
    let output = run_git(repository, args)?;
    if !output.status.success() {
        return Err(format!(
            "git {} failed: {}",
            args.join(" "),
            git_stderr(&output)
        ));
    }
    extend_nul_paths(&output.stdout, paths)
}

fn extend_nul_paths(bytes: &[u8], paths: &mut BTreeSet<String>) -> Result<(), String> {
    for path in bytes
        .split(|byte| *byte == 0)
        .filter(|path| !path.is_empty())
    {
        paths.insert(
            String::from_utf8(path.to_vec())
                .map_err(|error| format!("Git returned a non-UTF-8 path: {error}"))?,
        );
    }
    Ok(())
}

fn path_is_allowlisted(path: &str, allowed: &str) -> bool {
    if !allowed.contains('*') {
        return path == allowed
            || path
                .strip_prefix(allowed)
                .is_some_and(|suffix| suffix.starts_with('/'));
    }
    wildcard_matches(path.as_bytes(), allowed.as_bytes())
}

fn wildcard_matches(value: &[u8], pattern: &[u8]) -> bool {
    let mut previous = vec![false; value.len() + 1];
    previous[0] = true;
    for token in pattern {
        let mut current = vec![false; value.len() + 1];
        if *token == b'*' {
            current[0] = previous[0];
            for index in 1..=value.len() {
                current[index] = previous[index] || current[index - 1];
            }
        } else {
            for index in 1..=value.len() {
                current[index] = previous[index - 1] && value[index - 1] == *token;
            }
        }
        previous = current;
    }
    previous[value.len()]
}

fn git_text(repository: &Path, args: &[&str]) -> Result<String, String> {
    let output = run_git(repository, args)?;
    if !output.status.success() {
        return Err(git_stderr(&output));
    }
    String::from_utf8(output.stdout)
        .map(|value| value.trim().to_owned())
        .map_err(|error| format!("Git returned non-UTF-8 output: {error}"))
}

fn run_git(repository: &Path, args: &[&str]) -> Result<Output, String> {
    Command::new("git")
        .arg("-C")
        .arg(repository)
        .args(args)
        .env("LC_ALL", "C")
        .env("LANG", "C")
        .output()
        .map_err(|error| {
            format!(
                "failed to execute git -C {} {}: {error}",
                repository.display(),
                args.join(" ")
            )
        })
}

fn git_stderr(output: &Output) -> String {
    let stderr = String::from_utf8_lossy(&output.stderr);
    if stderr.trim().is_empty() {
        format!("git exited with {}", output.status)
    } else {
        stderr.trim().to_owned()
    }
}
