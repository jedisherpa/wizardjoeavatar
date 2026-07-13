//! Semantic validation for Wizard Joe RCHAT registries and gate records.

use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Component, Path, PathBuf};
use std::process::{Command, Output};

pub const REGISTRY_SCHEMA: &str = "wizardjoe-rchat-registry/v1";
pub const GATE_SCHEMA: &str = "wizardjoe-rchat-gate/v1";

const ROLES: [&str; 4] = ["RUNTIME", "MOTION", "FLOW", "INT"];
const WORK_STATUSES: [&str; 9] = [
    "PLANNED",
    "READY",
    "IN_PROGRESS",
    "HANDOFF_READY",
    "IN_REVIEW",
    "ACCEPTED",
    "BLOCKED",
    "FAILED",
    "REOPENED",
];

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Violation {
    pub code: &'static str,
    pub path: String,
    pub message: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ValidationReport {
    pub schema: &'static str,
    pub violations: Vec<Violation>,
}

impl ValidationReport {
    pub fn is_valid(&self) -> bool {
        self.violations.is_empty()
    }
}

#[derive(Clone, Debug)]
struct WorkItem {
    id: String,
    path: String,
    owner: String,
    status: String,
    weight: u64,
    dependencies: Vec<String>,
    required_children: Vec<String>,
    required_locks: Vec<String>,
    gate_id: String,
    parent: Option<String>,
    base_sha: Option<String>,
    raw: Map<String, Value>,
}

pub fn read_json(path: &Path) -> Result<Value, String> {
    let text = fs::read_to_string(path)
        .map_err(|error| format!("failed to read {}: {error}", path.display()))?;
    serde_json::from_str(&text)
        .map_err(|error| format!("failed to parse {} as JSON: {error}", path.display()))
}

pub fn validate_registry_path(path: &Path) -> Result<ValidationReport, String> {
    let value = read_json(path)?;
    let mut report = validate_registry(&value);
    let repository = repository_root(path)?;
    validate_material_registry(&value, &repository, &mut report.violations)?;
    report.violations.sort_by(|left, right| {
        (&left.path, left.code, &left.message).cmp(&(&right.path, right.code, &right.message))
    });
    Ok(report)
}

fn repository_root(registry_path: &Path) -> Result<PathBuf, String> {
    let start = registry_path.parent().unwrap_or_else(|| Path::new("."));
    let output = run_git(start, &["rev-parse", "--show-toplevel"])?;
    if !output.status.success() {
        return Err(format!(
            "cannot locate the Git repository containing {}: {}",
            registry_path.display(),
            git_stderr(&output)
        ));
    }
    let root = String::from_utf8(output.stdout)
        .map_err(|error| format!("git returned a non-UTF-8 repository path: {error}"))?;
    Ok(PathBuf::from(root.trim()))
}

fn validate_material_registry(
    value: &Value,
    repository: &Path,
    violations: &mut Vec<Violation>,
) -> Result<(), String> {
    let Some(root) = value.as_object() else {
        return Ok(());
    };
    for collection in ["work_items", "specialist_work_items"] {
        let Some(items) = root.get(collection).and_then(Value::as_array) else {
            continue;
        };
        for (index, value) in items.iter().enumerate() {
            let Some(item) = value.as_object() else {
                continue;
            };
            if item.get("status").and_then(Value::as_str) != Some("ACCEPTED") {
                continue;
            }
            let path = format!("$.{collection}[{index}]");
            validate_material_item(item, &path, repository, violations)?;
        }
    }
    Ok(())
}

fn validate_material_item(
    item: &Map<String, Value>,
    item_path: &str,
    repository: &Path,
    violations: &mut Vec<Violation>,
) -> Result<(), String> {
    let id = item
        .get("id")
        .and_then(Value::as_str)
        .unwrap_or("<unknown>");
    let base_sha = item.get("base_sha").and_then(Value::as_str);
    let result_sha = item.get("result_sha").and_then(Value::as_str);
    let base_resolves = commit_resolves(
        repository,
        base_sha,
        &format!("{item_path}.base_sha"),
        id,
        "RCHAT-GIT-BASE-COMMIT",
        violations,
    )?;
    let result_resolves = commit_resolves(
        repository,
        result_sha,
        &format!("{item_path}.result_sha"),
        id,
        "RCHAT-GIT-RESULT-COMMIT",
        violations,
    )?;

    if result_resolves {
        if let (Some(result_sha), Some(evidence)) =
            (result_sha, item.get("evidence").and_then(Value::as_array))
        {
            for (index, record) in evidence.iter().enumerate() {
                let Some(record) = record.as_object() else {
                    continue;
                };
                validate_material_evidence(
                    record,
                    &format!("{item_path}.evidence[{index}]"),
                    id,
                    result_sha,
                    repository,
                    violations,
                )?;
            }
        }
    }

    if base_resolves && result_resolves {
        if let (Some(base_sha), Some(result_sha)) = (base_sha, result_sha) {
            validate_changed_paths(
                item, item_path, id, base_sha, result_sha, repository, violations,
            )?;
        }
    }
    Ok(())
}

fn commit_resolves(
    repository: &Path,
    sha: Option<&str>,
    path: &str,
    id: &str,
    code: &'static str,
    violations: &mut Vec<Violation>,
) -> Result<bool, String> {
    let Some(sha) = sha else {
        return Ok(false);
    };
    let commit_object = format!("{sha}^{{commit}}");
    let output = run_git(repository, &["cat-file", "-e", &commit_object])?;
    if output.status.success() {
        return Ok(true);
    }
    push(
        violations,
        code,
        path,
        format!(
            "{id} references {sha}, which does not resolve to a commit; repair the receipt before acceptance ({})",
            git_stderr(&output)
        ),
    );
    Ok(false)
}

fn validate_material_evidence(
    evidence: &Map<String, Value>,
    evidence_path: &str,
    id: &str,
    result_sha: &str,
    repository: &Path,
    violations: &mut Vec<Violation>,
) -> Result<(), String> {
    let Some(path) = evidence.get("path").and_then(Value::as_str) else {
        return Ok(());
    };
    if !is_safe_repo_path(path) {
        push(
            violations,
            "RCHAT-EVIDENCE-PATH-UNSAFE",
            format!("{evidence_path}.path"),
            format!(
                "{id} evidence path {path:?} must be a safe repository-relative path without dot segments, backslashes, colons, or NUL bytes"
            ),
        );
        return Ok(());
    }

    let object = format!("{result_sha}:{path}");
    let output = run_git(repository, &["show", &object])?;
    if !output.status.success() {
        push(
            violations,
            "RCHAT-EVIDENCE-MISSING",
            format!("{evidence_path}.path"),
            format!(
                "{id} evidence {path} does not exist in result commit {result_sha}; commit the artifact or repair the receipt ({})",
                git_stderr(&output)
            ),
        );
        return Ok(());
    }

    let declared = evidence
        .get("sha256")
        .and_then(Value::as_str)
        .unwrap_or_default();
    let actual = format!("{:x}", Sha256::digest(&output.stdout));
    if declared != actual {
        push(
            violations,
            "RCHAT-EVIDENCE-HASH-MISMATCH",
            format!("{evidence_path}.sha256"),
            format!(
                "{id} evidence {path} hashes to {actual} at {result_sha}, not declared {declared}; regenerate the receipt from git-show bytes"
            ),
        );
    }
    Ok(())
}

fn validate_changed_paths(
    item: &Map<String, Value>,
    item_path: &str,
    id: &str,
    base_sha: &str,
    result_sha: &str,
    repository: &Path,
    violations: &mut Vec<Violation>,
) -> Result<(), String> {
    let output = run_git(
        repository,
        &[
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            base_sha,
            result_sha,
            "--",
        ],
    )?;
    if !output.status.success() {
        return Err(format!(
            "failed to inspect changed paths for {id} ({base_sha}..{result_sha}): {}",
            git_stderr(&output)
        ));
    }
    let allowlist: Vec<&str> = item
        .get("path_allowlist")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    for raw_path in output
        .stdout
        .split(|byte| *byte == 0)
        .filter(|p| !p.is_empty())
    {
        let changed_path = String::from_utf8(raw_path.to_vec())
            .map_err(|error| format!("git diff returned a non-UTF-8 path for {id}: {error}"))?;
        if !allowlist
            .iter()
            .any(|allowed| path_is_allowlisted(&changed_path, allowed))
        {
            push(
                violations,
                "RCHAT-PATH-OUT-OF-SCOPE",
                format!("{item_path}.path_allowlist"),
                format!(
                    "{id} changed {changed_path} between {base_sha} and {result_sha}, but no path_allowlist entry covers it"
                ),
            );
        }
    }
    Ok(())
}

fn is_safe_repo_path(value: &str) -> bool {
    if value.is_empty()
        || value.contains('\\')
        || value.contains(':')
        || value.contains('\0')
        || Path::new(value).is_absolute()
    {
        return false;
    }
    Path::new(value)
        .components()
        .all(|component| matches!(component, Component::Normal(_)))
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
    let message = stderr.trim();
    if message.is_empty() {
        format!("git exited with {}", output.status)
    } else {
        message.to_owned()
    }
}

pub fn validate_gate_path(
    path: &Path,
    registry_path: Option<&Path>,
) -> Result<ValidationReport, String> {
    let value = read_json(path)?;
    let registry = registry_path.map(read_json).transpose()?;
    Ok(validate_gate(&value, registry.as_ref()))
}

pub fn validate_registry(value: &Value) -> ValidationReport {
    let mut violations = Vec::new();
    let Some(root) = value.as_object() else {
        push(
            &mut violations,
            "RCHAT-TYPE",
            "$",
            "registry must be a JSON object",
        );
        return ValidationReport {
            schema: REGISTRY_SCHEMA,
            violations,
        };
    };

    require_fields(
        root,
        "$",
        &[
            "schema",
            "schema_version",
            "program_id",
            "branch",
            "production_authority",
            "integration_head",
            "planning_checkpoint",
            "status_vocabulary",
            "agents",
            "pose_baseline",
            "locks",
            "gates",
            "gate_aliases",
            "work_item_contract",
            "work_items",
            "specialist_work_items",
            "artifacts",
            "deployments",
            "progress",
        ],
        &mut violations,
    );

    expect_exact_string(root, "schema", REGISTRY_SCHEMA, "$", &mut violations);
    expect_u64(root, "schema_version", 1, "$", &mut violations);
    expect_exact_string(root, "program_id", "RCHAT", "$", &mut violations);
    expect_exact_string(
        root,
        "production_authority",
        "rust/wizard_avatar_engine",
        "$",
        &mut violations,
    );

    let integration_head =
        string_field(root, "integration_head", "$", &mut violations).unwrap_or_default();
    if !is_git_sha(&integration_head) {
        push(
            &mut violations,
            "RCHAT-SHA",
            "$.integration_head",
            "integration_head must be a lowercase 40-hex Git SHA",
        );
    }

    validate_status_vocabulary(root, &mut violations);
    validate_agents(root, &mut violations);
    validate_planning_checkpoint(root, &mut violations);

    let mut items = Vec::new();
    extract_items(root, "work_items", false, &mut items, &mut violations);
    extract_items(
        root,
        "specialist_work_items",
        true,
        &mut items,
        &mut violations,
    );

    let mut item_index = HashMap::new();
    for (index, item) in items.iter().enumerate() {
        if item_index.insert(item.id.clone(), index).is_some() {
            push(
                &mut violations,
                "RCHAT-ID-DUPLICATE",
                format!("{}.id", item.path),
                format!("duplicate work item ID {}", item.id),
            );
        }
    }

    validate_dependencies(&items, &item_index, &mut violations);
    validate_dependency_dag(&items, &item_index, &mut violations);

    let lock_ids = validate_locks(root, &items, &item_index, &mut violations);
    let gate_ids = validate_gates(root, &items, &item_index, &mut violations);
    validate_gate_aliases(root, &gate_ids, &mut violations);
    validate_item_references(&items, &lock_ids, &gate_ids, &mut violations);
    validate_status_rules(&items, &item_index, &integration_head, &mut violations);
    validate_parent_children(root, &items, &item_index, &mut violations);
    validate_progress(root, &items, &mut violations);
    validate_p0(root, &items, &mut violations);
    validate_deployments(root, &gate_ids, &mut violations);

    ValidationReport {
        schema: REGISTRY_SCHEMA,
        violations,
    }
}

pub fn validate_gate(value: &Value, registry: Option<&Value>) -> ValidationReport {
    let mut violations = Vec::new();
    let Some(root) = value.as_object() else {
        push(
            &mut violations,
            "RCHAT-TYPE",
            "$",
            "gate record must be a JSON object",
        );
        return ValidationReport {
            schema: GATE_SCHEMA,
            violations,
        };
    };

    require_fields(
        root,
        "$",
        &[
            "schema",
            "schema_version",
            "program_id",
            "gate_id",
            "status",
            "git",
            "environment",
            "inputs",
            "required_work_items",
            "commands",
            "metrics",
            "artifacts",
            "failures",
            "skips",
            "review",
            "rollback",
        ],
        &mut violations,
    );

    expect_exact_string(root, "schema", GATE_SCHEMA, "$", &mut violations);
    expect_u64(root, "schema_version", 1, "$", &mut violations);
    expect_exact_string(root, "program_id", "RCHAT", "$", &mut violations);

    let gate_id = string_field(root, "gate_id", "$", &mut violations).unwrap_or_default();
    let status = string_field(root, "status", "$", &mut violations).unwrap_or_default();
    if !["PASS", "FAIL", "BLOCKED"].contains(&status.as_str()) {
        push(
            &mut violations,
            "RCHAT-GATE-STATUS",
            "$.status",
            "gate status must be PASS, FAIL, or BLOCKED",
        );
    }

    let git_sha = validate_gate_git(root, &status, &mut violations);
    validate_gate_environment(root, &mut violations);
    validate_gate_inputs(root, &mut violations);
    let required_work = string_array_field(root, "required_work_items", "$", &mut violations);
    validate_gate_commands(root, &status, &mut violations);
    validate_gate_metrics(root, &status, &mut violations);
    validate_gate_artifacts(root, &mut violations);
    validate_gate_failures_and_skips(root, &status, &mut violations);
    validate_gate_review(root, &mut violations);
    validate_gate_rollback(root, &gate_id, &status, &mut violations);

    if let Some(registry_value) = registry {
        validate_gate_against_registry(
            &gate_id,
            &status,
            &required_work,
            git_sha.as_deref(),
            registry_value,
            &mut violations,
        );
    }

    ValidationReport {
        schema: GATE_SCHEMA,
        violations,
    }
}

fn validate_status_vocabulary(root: &Map<String, Value>, violations: &mut Vec<Violation>) {
    let values = string_array_field(root, "status_vocabulary", "$", violations);
    let actual: HashSet<_> = values.iter().map(String::as_str).collect();
    let expected: HashSet<_> = WORK_STATUSES.into_iter().collect();
    if actual != expected {
        push(
            violations,
            "RCHAT-STATUS-VOCABULARY",
            "$.status_vocabulary",
            "status vocabulary must contain exactly the nine canonical statuses",
        );
    }
}

fn validate_agents(root: &Map<String, Value>, violations: &mut Vec<Violation>) {
    let Some(agents) = array_field(root, "agents", "$", violations) else {
        return;
    };
    let mut roles = HashSet::new();
    for (index, value) in agents.iter().enumerate() {
        let path = format!("$.agents[{index}]");
        let Some(agent) = object_value(value, &path, violations) else {
            continue;
        };
        require_fields(agent, &path, &["role", "agent_id", "nickname"], violations);
        if let Some(role) = string_field(agent, "role", &path, violations) {
            if !ROLES.contains(&role.as_str()) {
                push(
                    violations,
                    "RCHAT-ROLE",
                    format!("{path}.role"),
                    format!("unknown role {role}"),
                );
            }
            if !roles.insert(role.clone()) {
                push(
                    violations,
                    "RCHAT-ROLE-DUPLICATE",
                    format!("{path}.role"),
                    format!("duplicate agent role {role}"),
                );
            }
        }
        non_empty_string_field(agent, "agent_id", &path, violations);
        non_empty_string_field(agent, "nickname", &path, violations);
    }
    for role in ROLES {
        if !roles.contains(role) {
            push(
                violations,
                "RCHAT-ROLE-MISSING",
                "$.agents",
                format!("missing agent role {role}"),
            );
        }
    }
}

fn validate_planning_checkpoint(root: &Map<String, Value>, violations: &mut Vec<Violation>) {
    let Some(value) = root.get("planning_checkpoint") else {
        return;
    };
    let Some(checkpoint) = object_value(value, "$.planning_checkpoint", violations) else {
        return;
    };
    require_fields(
        checkpoint,
        "$.planning_checkpoint",
        &["local_sha", "remote_sha", "pushed"],
        violations,
    );
    let local = nullable_sha_field(checkpoint, "local_sha", "$.planning_checkpoint", violations);
    let remote = nullable_sha_field(
        checkpoint,
        "remote_sha",
        "$.planning_checkpoint",
        violations,
    );
    let pushed =
        bool_field(checkpoint, "pushed", "$.planning_checkpoint", violations).unwrap_or(false);
    if pushed && (local.is_none() || local != remote) {
        push(
            violations,
            "RCHAT-CHECKPOINT-SHA",
            "$.planning_checkpoint",
            "a pushed planning checkpoint requires equal non-null local and remote SHAs",
        );
    }
}

fn extract_items(
    root: &Map<String, Value>,
    field: &str,
    specialist: bool,
    items: &mut Vec<WorkItem>,
    violations: &mut Vec<Violation>,
) {
    let Some(values) = array_field(root, field, "$", violations) else {
        return;
    };
    for (index, value) in values.iter().enumerate() {
        let path = format!("$.{field}[{index}]");
        let Some(raw) = object_value(value, &path, violations) else {
            continue;
        };
        let mut required = vec![
            "id",
            "title",
            "owner",
            "reviewers",
            "status",
            "weight",
            "dependencies",
            "gate_id",
            "path_allowlist",
            "required_locks",
            "base_sha",
            "result_sha",
            "started_at",
            "finished_at",
            "commands",
            "evidence",
            "metrics",
            "rollback",
            "blocker",
            "handoff_id",
        ];
        if specialist {
            required.extend(["parent", "detail_source"]);
        } else {
            required.push("required_children");
        }
        require_fields(raw, &path, &required, violations);

        let id = non_empty_string_field(raw, "id", &path, violations).unwrap_or_default();
        let owner = string_field(raw, "owner", &path, violations).unwrap_or_default();
        if !ROLES.contains(&owner.as_str()) {
            push(
                violations,
                "RCHAT-OWNER",
                format!("{path}.owner"),
                "owner must be one canonical role string",
            );
        }
        let reviewers = string_array_field(raw, "reviewers", &path, violations);
        for reviewer in &reviewers {
            if !ROLES.contains(&reviewer.as_str()) {
                push(
                    violations,
                    "RCHAT-REVIEWER",
                    format!("{path}.reviewers"),
                    format!("unknown reviewer role {reviewer}"),
                );
            }
            if reviewer == &owner {
                push(
                    violations,
                    "RCHAT-SELF-REVIEW",
                    format!("{path}.reviewers"),
                    "owner cannot be its own reviewer",
                );
            }
        }
        let status = string_field(raw, "status", &path, violations).unwrap_or_default();
        if !WORK_STATUSES.contains(&status.as_str()) {
            push(
                violations,
                "RCHAT-WORK-STATUS",
                format!("{path}.status"),
                format!("unknown work status {status}"),
            );
        }
        let weight = integer_field(raw, "weight", &path, violations).unwrap_or(0);
        let dependencies = string_array_field(raw, "dependencies", &path, violations);
        let required_children = if specialist {
            Vec::new()
        } else {
            string_array_field(raw, "required_children", &path, violations)
        };
        let required_locks = string_array_field(raw, "required_locks", &path, violations);
        let gate_id = non_empty_string_field(raw, "gate_id", &path, violations).unwrap_or_default();
        string_array_field(raw, "path_allowlist", &path, violations);
        nullable_sha_field(raw, "result_sha", &path, violations);
        nullable_string_field(raw, "started_at", &path, violations);
        nullable_string_field(raw, "finished_at", &path, violations);
        array_field(raw, "commands", &path, violations);
        array_field(raw, "evidence", &path, violations);
        object_field(raw, "metrics", &path, violations);
        object_field(raw, "rollback", &path, violations);
        nullable_string_field(raw, "handoff_id", &path, violations);
        let base_sha = nullable_sha_field(raw, "base_sha", &path, violations);
        let parent = if specialist {
            non_empty_string_field(raw, "parent", &path, violations)
        } else {
            None
        };
        if specialist {
            non_empty_string_field(raw, "detail_source", &path, violations);
            if weight != 0 {
                push(
                    violations,
                    "RCHAT-SPECIALIST-WEIGHT",
                    format!("{path}.weight"),
                    "specialist child weight must be zero when FLOW parents own progress",
                );
            }
        }
        items.push(WorkItem {
            id,
            path,
            owner,
            status,
            weight,
            dependencies,
            required_children,
            required_locks,
            gate_id,
            parent,
            base_sha,
            raw: raw.clone(),
        });
    }
}

fn validate_dependencies(
    items: &[WorkItem],
    item_index: &HashMap<String, usize>,
    violations: &mut Vec<Violation>,
) {
    for item in items {
        for dependency in &item.dependencies {
            if dependency == &item.id {
                push(
                    violations,
                    "RCHAT-SELF-DEPENDENCY",
                    format!("{}.dependencies", item.path),
                    format!("{} depends on itself", item.id),
                );
            } else if !item_index.contains_key(dependency) {
                push(
                    violations,
                    "RCHAT-DEPENDENCY-MISSING",
                    format!("{}.dependencies", item.path),
                    format!("{} references missing dependency {dependency}", item.id),
                );
            }
        }
    }
}

fn validate_dependency_dag(
    items: &[WorkItem],
    item_index: &HashMap<String, usize>,
    violations: &mut Vec<Violation>,
) {
    fn visit(
        id: &str,
        items: &[WorkItem],
        item_index: &HashMap<String, usize>,
        marks: &mut HashMap<String, u8>,
        stack: &mut Vec<String>,
        violations: &mut Vec<Violation>,
    ) {
        match marks.get(id).copied() {
            Some(2) => return,
            Some(1) => {
                stack.push(id.to_owned());
                push(
                    violations,
                    "RCHAT-DEPENDENCY-CYCLE",
                    "$.work_items",
                    format!("dependency cycle: {}", stack.join(" -> ")),
                );
                stack.pop();
                return;
            }
            _ => {}
        }
        marks.insert(id.to_owned(), 1);
        stack.push(id.to_owned());
        if let Some(index) = item_index.get(id) {
            for dependency in &items[*index].dependencies {
                if item_index.contains_key(dependency) {
                    visit(dependency, items, item_index, marks, stack, violations);
                }
            }
        }
        stack.pop();
        marks.insert(id.to_owned(), 2);
    }

    let mut marks = HashMap::new();
    let mut stack = Vec::new();
    for item in items {
        if !marks.contains_key(&item.id) {
            visit(
                &item.id, items, item_index, &mut marks, &mut stack, violations,
            );
        }
    }
}

fn validate_locks(
    root: &Map<String, Value>,
    items: &[WorkItem],
    item_index: &HashMap<String, usize>,
    violations: &mut Vec<Violation>,
) -> HashSet<String> {
    let mut ids = HashSet::new();
    let mut active_paths = HashMap::<String, String>::new();
    let mut active_work = HashMap::<String, String>::new();
    let Some(values) = array_field(root, "locks", "$", violations) else {
        return ids;
    };
    for (index, value) in values.iter().enumerate() {
        let path = format!("$.locks[{index}]");
        let Some(lock) = object_value(value, &path, violations) else {
            continue;
        };
        require_fields(
            lock,
            &path,
            &[
                "lock_id",
                "paths",
                "holder",
                "work_id",
                "acquired_at",
                "expires_at",
                "base_sha",
                "reason",
            ],
            violations,
        );
        let id = non_empty_string_field(lock, "lock_id", &path, violations).unwrap_or_default();
        if !ids.insert(id.clone()) {
            push(
                violations,
                "RCHAT-LOCK-DUPLICATE",
                format!("{path}.lock_id"),
                format!("duplicate lock ID {id}"),
            );
        }
        let paths = string_array_field(lock, "paths", &path, violations);
        let holder = nullable_string_field(lock, "holder", &path, violations);
        let work_id = nullable_string_field(lock, "work_id", &path, violations);
        nullable_string_field(lock, "acquired_at", &path, violations);
        nullable_string_field(lock, "expires_at", &path, violations);
        nullable_sha_field(lock, "base_sha", &path, violations);
        nullable_string_field(lock, "reason", &path, violations);
        if holder.is_some() != work_id.is_some() {
            push(
                violations,
                "RCHAT-LOCK-PARTIAL",
                &path,
                "holder and work_id must both be null or both be set",
            );
        }
        if let (Some(holder), Some(work_id)) = (holder, work_id) {
            let Some(item_position) = item_index.get(&work_id) else {
                push(
                    violations,
                    "RCHAT-LOCK-WORK-MISSING",
                    format!("{path}.work_id"),
                    format!("lock references missing work item {work_id}"),
                );
                continue;
            };
            let item = &items[*item_position];
            if item.owner != holder {
                push(
                    violations,
                    "RCHAT-LOCK-OWNER",
                    format!("{path}.holder"),
                    format!("lock holder {holder} does not own {work_id}"),
                );
            }
            if item.status != "IN_PROGRESS" {
                push(
                    violations,
                    "RCHAT-LOCK-STATUS",
                    format!("{path}.work_id"),
                    format!("active lock work item {work_id} is not IN_PROGRESS"),
                );
            }
            active_work.insert(id.clone(), work_id);
            for owned_path in paths {
                if let Some(other_lock) = active_paths.insert(owned_path.clone(), id.clone()) {
                    push(
                        violations,
                        "RCHAT-LOCK-PATH-CONFLICT",
                        format!("{path}.paths"),
                        format!("path {owned_path} is active under {other_lock} and {id}"),
                    );
                }
            }
        }
    }

    let mut in_progress_by_lock: HashMap<&str, Vec<&str>> = HashMap::new();
    for item in items.iter().filter(|item| item.status == "IN_PROGRESS") {
        for lock_id in &item.required_locks {
            in_progress_by_lock
                .entry(lock_id)
                .or_default()
                .push(&item.id);
            if active_work.get(lock_id) != Some(&item.id) {
                push(
                    violations,
                    "RCHAT-LOCK-NOT-HELD",
                    format!("{}.required_locks", item.path),
                    format!("{} is IN_PROGRESS without holding {lock_id}", item.id),
                );
            }
        }
    }
    for (lock_id, work_ids) in in_progress_by_lock {
        if work_ids.len() > 1 {
            push(
                violations,
                "RCHAT-LOCK-CONTENTION",
                "$.work_items",
                format!(
                    "lock {lock_id} is required by multiple IN_PROGRESS items: {}",
                    work_ids.join(", ")
                ),
            );
        }
    }
    for item in items.iter().filter(|item| item.status == "READY") {
        for lock_id in &item.required_locks {
            if let Some(holder) = active_work.get(lock_id) {
                push(
                    violations,
                    "RCHAT-READY-LOCK-BUSY",
                    format!("{}.required_locks", item.path),
                    format!("{} is READY while {lock_id} is held by {holder}", item.id),
                );
            }
        }
    }
    ids
}

fn validate_gates(
    root: &Map<String, Value>,
    items: &[WorkItem],
    item_index: &HashMap<String, usize>,
    violations: &mut Vec<Violation>,
) -> HashSet<String> {
    let mut ids = HashSet::new();
    let Some(values) = array_field(root, "gates", "$", violations) else {
        return ids;
    };
    for (index, value) in values.iter().enumerate() {
        let path = format!("$.gates[{index}]");
        let Some(gate) = object_value(value, &path, violations) else {
            continue;
        };
        require_fields(
            gate,
            &path,
            &[
                "gate_id",
                "status",
                "required_work",
                "structural_pass_required",
                "record",
            ],
            violations,
        );
        let gate_id =
            non_empty_string_field(gate, "gate_id", &path, violations).unwrap_or_default();
        if !ids.insert(gate_id.clone()) {
            push(
                violations,
                "RCHAT-GATE-DUPLICATE",
                format!("{path}.gate_id"),
                format!("duplicate gate ID {gate_id}"),
            );
        }
        let status = string_field(gate, "status", &path, violations).unwrap_or_default();
        if !["PASS", "FAIL", "BLOCKED", "IN_REVIEW"].contains(&status.as_str()) {
            push(
                violations,
                "RCHAT-GATE-STATUS",
                format!("{path}.status"),
                format!("invalid registry gate status {status}"),
            );
        }
        let required = string_array_field(gate, "required_work", &path, violations);
        bool_field(gate, "structural_pass_required", &path, violations);
        for work_id in &required {
            if !item_index.contains_key(work_id) {
                push(
                    violations,
                    "RCHAT-GATE-WORK-MISSING",
                    format!("{path}.required_work"),
                    format!("gate {gate_id} references missing work item {work_id}"),
                );
            }
        }
        if status == "PASS" {
            for work_id in required {
                if let Some(item_position) = item_index.get(&work_id) {
                    if items[*item_position].status != "ACCEPTED" {
                        push(
                            violations,
                            "RCHAT-GATE-PREMATURE-PASS",
                            format!("{path}.status"),
                            format!("gate {gate_id} passed before {work_id} was ACCEPTED"),
                        );
                    }
                }
            }
            if gate.get("record").is_none_or(Value::is_null) {
                push(
                    violations,
                    "RCHAT-GATE-RECORD",
                    format!("{path}.record"),
                    format!("passed gate {gate_id} requires a record"),
                );
            } else if let Some(record) = gate.get("record").and_then(Value::as_object) {
                require_fields(
                    record,
                    &format!("{path}.record"),
                    &["git_sha", "remote_sha", "result"],
                    violations,
                );
                let git_sha =
                    string_field(record, "git_sha", &format!("{path}.record"), violations)
                        .unwrap_or_default();
                let remote_sha =
                    string_field(record, "remote_sha", &format!("{path}.record"), violations)
                        .unwrap_or_default();
                if !is_git_sha(&git_sha) || git_sha != remote_sha {
                    push(
                        violations,
                        "RCHAT-GATE-RECORD-SHA",
                        format!("{path}.record"),
                        "passed gate record requires equal lowercase local and remote Git SHAs",
                    );
                }
                if record.contains_key("dirty")
                    && record.get("dirty").and_then(Value::as_bool) != Some(false)
                {
                    push(
                        violations,
                        "RCHAT-GATE-RECORD-DIRTY",
                        format!("{path}.record.dirty"),
                        "passed gate summary cannot report a dirty tree",
                    );
                }
                if record.get("result").and_then(Value::as_str) != Some("PASS") {
                    push(
                        violations,
                        "RCHAT-GATE-RECORD-RESULT",
                        format!("{path}.record"),
                        "passed gate record requires result=PASS",
                    );
                }
                for work_id in gate
                    .get("required_work")
                    .and_then(Value::as_array)
                    .into_iter()
                    .flatten()
                    .filter_map(Value::as_str)
                {
                    if let Some(item_position) = item_index.get(work_id) {
                        let result_sha = items[*item_position]
                            .raw
                            .get("result_sha")
                            .and_then(Value::as_str);
                        if result_sha != Some(git_sha.as_str()) {
                            push(
                                violations,
                                "RCHAT-GATE-WORK-SHA",
                                format!("{path}.record.git_sha"),
                                format!("gate {gate_id} SHA does not equal {work_id} result_sha"),
                            );
                        }
                    }
                }
            }
        }
    }
    ids
}

fn validate_gate_aliases(
    root: &Map<String, Value>,
    gate_ids: &HashSet<String>,
    violations: &mut Vec<Violation>,
) {
    let Some(aliases) = object_field(root, "gate_aliases", "$", violations) else {
        return;
    };
    let mut seen = HashMap::<String, String>::new();
    for (gate_id, value) in aliases {
        if !gate_ids.contains(gate_id) {
            push(
                violations,
                "RCHAT-GATE-ALIAS-KEY",
                format!("$.gate_aliases.{gate_id}"),
                format!("alias key {gate_id} is not a canonical gate"),
            );
        }
        let Some(values) = value.as_array() else {
            push(
                violations,
                "RCHAT-TYPE",
                format!("$.gate_aliases.{gate_id}"),
                "gate aliases must be an array",
            );
            continue;
        };
        for (index, alias) in values.iter().enumerate() {
            let Some(alias) = alias.as_str().filter(|alias| !alias.is_empty()) else {
                push(
                    violations,
                    "RCHAT-GATE-ALIAS",
                    format!("$.gate_aliases.{gate_id}[{index}]"),
                    "gate alias must be a non-empty string",
                );
                continue;
            };
            if let Some(other_gate) = seen.insert(alias.to_owned(), gate_id.clone()) {
                push(
                    violations,
                    "RCHAT-GATE-ALIAS-DUPLICATE",
                    format!("$.gate_aliases.{gate_id}[{index}]"),
                    format!("alias {alias} also maps to {other_gate}"),
                );
            }
        }
    }
    for gate_id in gate_ids {
        if !aliases.contains_key(gate_id) {
            push(
                violations,
                "RCHAT-GATE-ALIAS-MISSING",
                "$.gate_aliases",
                format!("canonical gate {gate_id} has no alias entry"),
            );
        }
    }
}

fn validate_item_references(
    items: &[WorkItem],
    lock_ids: &HashSet<String>,
    gate_ids: &HashSet<String>,
    violations: &mut Vec<Violation>,
) {
    for item in items {
        if !gate_ids.contains(&item.gate_id) {
            push(
                violations,
                "RCHAT-WORK-GATE-MISSING",
                format!("{}.gate_id", item.path),
                format!("{} references missing gate {}", item.id, item.gate_id),
            );
        }
        for lock_id in &item.required_locks {
            if !lock_ids.contains(lock_id) {
                push(
                    violations,
                    "RCHAT-WORK-LOCK-MISSING",
                    format!("{}.required_locks", item.path),
                    format!("{} references missing lock {lock_id}", item.id),
                );
            }
        }
    }
}

fn validate_status_rules(
    items: &[WorkItem],
    item_index: &HashMap<String, usize>,
    integration_head: &str,
    violations: &mut Vec<Violation>,
) {
    for item in items {
        if [
            "READY",
            "IN_PROGRESS",
            "HANDOFF_READY",
            "IN_REVIEW",
            "ACCEPTED",
        ]
        .contains(&item.status.as_str())
        {
            for dependency in &item.dependencies {
                if let Some(position) = item_index.get(dependency) {
                    if items[*position].status != "ACCEPTED" {
                        push(
                            violations,
                            "RCHAT-DEPENDENCY-NOT-ACCEPTED",
                            format!("{}.status", item.path),
                            format!(
                                "{} is {} while dependency {dependency} is {}",
                                item.id, item.status, items[*position].status
                            ),
                        );
                    }
                }
            }
        }

        if ["READY", "IN_PROGRESS"].contains(&item.status.as_str())
            && item.base_sha.as_deref() != Some(integration_head)
        {
            push(
                violations,
                "RCHAT-BASE-SHA",
                format!("{}.base_sha", item.path),
                format!(
                    "{} {} base SHA must equal integration_head",
                    item.id, item.status
                ),
            );
        }

        if item.status == "ACCEPTED" {
            validate_accepted_item(item, violations);
            for child in &item.required_children {
                if let Some(position) = item_index.get(child) {
                    if items[*position].status != "ACCEPTED" {
                        push(
                            violations,
                            "RCHAT-CHILD-NOT-ACCEPTED",
                            format!("{}.status", item.path),
                            format!("{} accepted before child {child}", item.id),
                        );
                    }
                }
            }
        }
    }
}

fn validate_accepted_item(item: &WorkItem, violations: &mut Vec<Violation>) {
    let result_sha = item.raw.get("result_sha").and_then(Value::as_str);
    if result_sha.is_none_or(|sha| !is_git_sha(sha)) {
        push(
            violations,
            "RCHAT-ACCEPTED-SHA",
            format!("{}.result_sha", item.path),
            "ACCEPTED work requires a lowercase 40-hex result SHA",
        );
    }
    for timestamp in ["started_at", "finished_at"] {
        if item
            .raw
            .get(timestamp)
            .and_then(Value::as_str)
            .is_none_or(str::is_empty)
        {
            push(
                violations,
                "RCHAT-ACCEPTED-TIME",
                format!("{}.{}", item.path, timestamp),
                format!("ACCEPTED work requires {timestamp}"),
            );
        }
    }

    let reviewers = item
        .raw
        .get("reviewers")
        .and_then(Value::as_array)
        .map(Vec::as_slice)
        .unwrap_or_default();
    if reviewers.is_empty() {
        push(
            violations,
            "RCHAT-ACCEPTED-REVIEWER",
            format!("{}.reviewers", item.path),
            "ACCEPTED work requires at least one independent reviewer",
        );
    }

    let commands = item
        .raw
        .get("commands")
        .and_then(Value::as_array)
        .map(Vec::as_slice)
        .unwrap_or_default();
    if commands.is_empty() {
        push(
            violations,
            "RCHAT-ACCEPTED-COMMANDS",
            format!("{}.commands", item.path),
            "ACCEPTED work requires at least one command record",
        );
    }
    for (index, value) in commands.iter().enumerate() {
        validate_command(
            value,
            &format!("{}.commands[{index}]", item.path),
            true,
            false,
            violations,
        );
    }

    let evidence = item
        .raw
        .get("evidence")
        .and_then(Value::as_array)
        .map(Vec::as_slice)
        .unwrap_or_default();
    if evidence.is_empty() {
        push(
            violations,
            "RCHAT-ACCEPTED-EVIDENCE",
            format!("{}.evidence", item.path),
            "ACCEPTED work requires at least one hashed evidence record",
        );
    }
    for (index, value) in evidence.iter().enumerate() {
        validate_evidence(
            value,
            &format!("{}.evidence[{index}]", item.path),
            violations,
        );
    }

    if item.raw.get("metrics").and_then(Value::as_object).is_none() {
        push(
            violations,
            "RCHAT-ACCEPTED-METRICS",
            format!("{}.metrics", item.path),
            "ACCEPTED work requires a metrics object",
        );
    }
    let rollback = item.raw.get("rollback").and_then(Value::as_object);
    let verified = rollback
        .and_then(|rollback| rollback.get("verified"))
        .and_then(Value::as_bool);
    let profile = rollback
        .and_then(|rollback| rollback.get("profile"))
        .and_then(Value::as_str);
    if verified != Some(true) || profile.is_none_or(str::is_empty) {
        push(
            violations,
            "RCHAT-ACCEPTED-ROLLBACK",
            format!("{}.rollback", item.path),
            "ACCEPTED work requires a non-empty profile and verified rollback",
        );
    }
}

fn validate_parent_children(
    root: &Map<String, Value>,
    items: &[WorkItem],
    item_index: &HashMap<String, usize>,
    violations: &mut Vec<Violation>,
) {
    let parent_ids: HashSet<_> = root
        .get("work_items")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(|value| value.get("id").and_then(Value::as_str))
        .collect();
    let mut actual: HashMap<&str, HashSet<&str>> = HashMap::new();
    for item in items.iter().filter(|item| item.parent.is_some()) {
        let parent = item.parent.as_deref().unwrap_or_default();
        if !parent_ids.contains(parent) {
            push(
                violations,
                "RCHAT-PARENT-MISSING",
                format!("{}.parent", item.path),
                format!("{} references missing FLOW parent {parent}", item.id),
            );
        }
        actual.entry(parent).or_default().insert(&item.id);
    }

    for parent_id in parent_ids {
        let Some(position) = item_index.get(parent_id) else {
            continue;
        };
        let declared: HashSet<_> = items[*position]
            .required_children
            .iter()
            .map(String::as_str)
            .collect();
        let observed = actual.remove(parent_id).unwrap_or_default();
        if declared != observed {
            let missing: Vec<_> = observed.difference(&declared).copied().collect();
            let extra: Vec<_> = declared.difference(&observed).copied().collect();
            push(
                violations,
                "RCHAT-PARENT-CHILDREN",
                format!("{}.required_children", items[*position].path),
                format!(
                    "parent {parent_id} child mismatch; undeclared={missing:?}, missing-record={extra:?}"
                ),
            );
        }
        for child in &items[*position].required_children {
            if !item_index.contains_key(child) {
                push(
                    violations,
                    "RCHAT-CHILD-MISSING",
                    format!("{}.required_children", items[*position].path),
                    format!("parent {parent_id} references missing child {child}"),
                );
            }
        }
    }
}

fn validate_progress(
    root: &Map<String, Value>,
    items: &[WorkItem],
    violations: &mut Vec<Violation>,
) {
    let Some(progress) = object_field(root, "progress", "$", violations) else {
        return;
    };
    let parent_count = root
        .get("work_items")
        .and_then(Value::as_array)
        .map_or(0, Vec::len);
    let parent_items = &items[..items.len().min(parent_count)];
    let accepted_weight: u64 = parent_items
        .iter()
        .filter(|item| item.status == "ACCEPTED")
        .map(|item| item.weight)
        .sum();
    let total_weight: u64 = parent_items.iter().map(|item| item.weight).sum();
    expect_computed_u64(
        progress,
        "accepted_weight",
        accepted_weight,
        "$.progress",
        violations,
    );
    expect_computed_u64(
        progress,
        "total_weight",
        total_weight,
        "$.progress",
        violations,
    );
    let program_percent = percent(accepted_weight, total_weight);
    expect_computed_f64(
        progress,
        "program_percent",
        program_percent,
        "$.progress",
        violations,
    );

    let gate_values = root
        .get("gates")
        .and_then(Value::as_array)
        .map(Vec::as_slice)
        .unwrap_or_default();
    let passed_gates = gate_values
        .iter()
        .filter(|gate| gate.get("status").and_then(Value::as_str) == Some("PASS"))
        .count() as u64;
    let total_gates = gate_values.len() as u64;
    expect_computed_u64(
        progress,
        "passed_blocking_gates",
        passed_gates,
        "$.progress",
        violations,
    );
    expect_computed_u64(
        progress,
        "total_blocking_gates",
        total_gates,
        "$.progress",
        violations,
    );
    expect_computed_f64(
        progress,
        "gate_percent",
        percent(passed_gates, total_gates),
        "$.progress",
        violations,
    );
    let critical =
        number_field(progress, "critical_path_percent", "$.progress", violations).unwrap_or(-1.0);
    if !(0.0..=100.0).contains(&critical) {
        push(
            violations,
            "RCHAT-PROGRESS-RANGE",
            "$.progress.critical_path_percent",
            "critical_path_percent must be between 0 and 100",
        );
    }
    if progress.get("weight_authority").and_then(Value::as_str) == Some("work_items")
        && (progress
            .get("specialist_weights_earning")
            .and_then(Value::as_bool)
            != Some(false)
            || progress
                .get("specialist_accepted_weight")
                .and_then(Value::as_u64)
                != Some(0)
            || progress
                .get("specialist_total_weight")
                .and_then(Value::as_u64)
                != Some(0))
    {
        push(
            violations,
            "RCHAT-PROGRESS-DOUBLE-COUNT",
            "$.progress",
            "parent-authoritative progress requires all specialist weights to be non-earning zero",
        );
    }
}

fn validate_p0(root: &Map<String, Value>, items: &[WorkItem], violations: &mut Vec<Violation>) {
    let p0_passed = root
        .get("gates")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .any(|gate| {
            gate.get("gate_id").and_then(Value::as_str) == Some("P0")
                && gate.get("status").and_then(Value::as_str) == Some("PASS")
        });
    if !p0_passed {
        return;
    }
    let Some(pose) = object_field(root, "pose_baseline", "$", violations) else {
        return;
    };
    let expected_counts = [
        ("runtime_geometries", 89),
        ("wjfl_geometries", 50),
        ("authored_transitions", 621),
        ("clips", 16),
        ("static_frames", 89),
        ("frames_per_pass", 20_065),
        ("passes", 2),
        ("quality_failures", 0),
    ];
    expect_exact_string(pose, "status", "PASS", "$.pose_baseline", violations);
    for (field, expected) in expected_counts {
        expect_u64(pose, field, expected, "$.pose_baseline", violations);
    }
    for field in ["decode_parity", "presentation_parity"] {
        if bool_field(pose, field, "$.pose_baseline", violations) != Some(true) {
            push(
                violations,
                "RCHAT-P0-PARITY",
                format!("$.pose_baseline.{field}"),
                format!("P0 requires {field}=true"),
            );
        }
    }
    for field in ["asset_sha256", "stream_sha256"] {
        let value = string_field(pose, field, "$.pose_baseline", violations).unwrap_or_default();
        if !is_sha256(&value) {
            push(
                violations,
                "RCHAT-EVIDENCE-HASH",
                format!("$.pose_baseline.{field}"),
                "P0 hashes must be lowercase 64-hex SHA-256 values",
            );
        }
    }
    let coverage = root
        .get("progress")
        .and_then(Value::as_object)
        .and_then(|progress| progress.get("pose_coverage_percent"))
        .and_then(Value::as_f64);
    if coverage != Some(100.0) {
        push(
            violations,
            "RCHAT-P0-COVERAGE",
            "$.progress.pose_coverage_percent",
            "passed P0 requires pose_coverage_percent=100",
        );
    }

    for item in items.iter().filter(|item| item.gate_id == "P0") {
        let rollback = item.raw.get("rollback").and_then(Value::as_object);
        let profile = rollback
            .and_then(|rollback| rollback.get("profile"))
            .and_then(Value::as_str);
        let sha = rollback.and_then(|rollback| rollback.get("sha"));
        let downgrade = rollback
            .and_then(|rollback| rollback.get("downgrade_allowed"))
            .and_then(Value::as_bool);
        let serialized = rollback
            .map(|rollback| Value::Object(rollback.clone()).to_string().to_lowercase())
            .unwrap_or_default();
        if profile != Some("repair-only")
            || sha.is_none_or(|sha| !sha.is_null())
            || downgrade != Some(false)
            || serialized.contains("pose-v3")
        {
            push(
                violations,
                "RCHAT-P0-DOWNGRADE",
                format!("{}.rollback", item.path),
                "P0 rollback must be repair-only, have no SHA, and explicitly forbid downgrade",
            );
        }
    }
}

fn validate_deployments(
    root: &Map<String, Value>,
    gate_ids: &HashSet<String>,
    violations: &mut Vec<Violation>,
) {
    let Some(values) = array_field(root, "deployments", "$", violations) else {
        return;
    };
    let f0_gate = root
        .get("gates")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .find(|gate| gate.get("gate_id").and_then(Value::as_str) == Some("F0"));
    let mut deployment_ids = HashSet::new();
    for (index, value) in values.iter().enumerate() {
        let path = format!("$.deployments[{index}]");
        let Some(deployment) = object_value(value, &path, violations) else {
            continue;
        };
        let fields = [
            "f0_approved_sha",
            "pushed_sha",
            "built_sha",
            "deployed_sha",
            "endpoint_sha",
        ];
        require_fields(
            deployment,
            &path,
            &[
                "deployment_id",
                "environment",
                "f0_approved_sha",
                "pushed_sha",
                "built_sha",
                "deployed_sha",
                "endpoint_sha",
                "status",
            ],
            violations,
        );
        let deployment_id = non_empty_string_field(deployment, "deployment_id", &path, violations)
            .unwrap_or_default();
        if !deployment_ids.insert(deployment_id.clone()) {
            push(
                violations,
                "RCHAT-DEPLOYMENT-DUPLICATE",
                format!("{path}.deployment_id"),
                format!("duplicate deployment ID {deployment_id}"),
            );
        }
        non_empty_string_field(deployment, "environment", &path, violations);
        let mut shas = Vec::new();
        for field in fields {
            let sha = string_field(deployment, field, &path, violations).unwrap_or_default();
            if !is_git_sha(&sha) {
                push(
                    violations,
                    "RCHAT-DEPLOYMENT-SHA",
                    format!("{path}.{field}"),
                    "deployment identity must be a lowercase 40-hex Git SHA",
                );
            }
            shas.push((field, sha));
        }
        if let Some((_, expected)) = shas.first() {
            for (field, actual) in shas.iter().skip(1) {
                if actual != expected {
                    push(
                        violations,
                        "RCHAT-DEPLOYMENT-SHA-MISMATCH",
                        format!("{path}.{field}"),
                        format!("deployment SHA {actual} does not equal F0 SHA {expected}"),
                    );
                }
            }
        }
        let status = string_field(deployment, "status", &path, violations).unwrap_or_default();
        if status == "ACTIVE" {
            let f0_passed = gate_ids.contains("F0")
                && f0_gate
                    .and_then(|gate| gate.get("status"))
                    .and_then(Value::as_str)
                    == Some("PASS");
            if !f0_passed {
                push(
                    violations,
                    "RCHAT-DEPLOYMENT-F0",
                    format!("{path}.status"),
                    "active deployment requires the canonical F0 gate to PASS",
                );
            }
            let recorded_f0_sha = f0_gate
                .and_then(|gate| gate.get("record"))
                .and_then(Value::as_object)
                .and_then(|record| record.get("git_sha"))
                .and_then(Value::as_str);
            let deployment_f0_sha = deployment.get("f0_approved_sha").and_then(Value::as_str);
            if recorded_f0_sha != deployment_f0_sha {
                push(
                    violations,
                    "RCHAT-DEPLOYMENT-F0-SHA",
                    format!("{path}.f0_approved_sha"),
                    "active deployment SHA must equal the canonical F0 gate record SHA",
                );
            }
        }
    }
}

fn validate_gate_git(
    root: &Map<String, Value>,
    status: &str,
    violations: &mut Vec<Violation>,
) -> Option<String> {
    let git = object_field(root, "git", "$", violations)?;
    require_fields(git, "$.git", &["branch", "sha", "dirty"], violations);
    non_empty_string_field(git, "branch", "$.git", violations);
    let sha = string_field(git, "sha", "$.git", violations);
    if sha.as_deref().is_none_or(|sha| !is_git_sha(sha)) {
        push(
            violations,
            "RCHAT-GATE-SHA",
            "$.git.sha",
            "gate Git SHA must be lowercase 40-hex",
        );
    }
    let dirty = bool_field(git, "dirty", "$.git", violations);
    if status == "PASS" && dirty != Some(false) {
        push(
            violations,
            "RCHAT-GATE-DIRTY",
            "$.git.dirty",
            "a PASS gate must be generated from a clean tree",
        );
    }
    sha
}

fn validate_gate_environment(root: &Map<String, Value>, violations: &mut Vec<Violation>) {
    let Some(environment) = object_field(root, "environment", "$", violations) else {
        return;
    };
    require_fields(
        environment,
        "$.environment",
        &["os", "arch", "rustc", "cargo", "node", "browser"],
        violations,
    );
    for field in ["os", "arch", "rustc", "cargo", "node"] {
        non_empty_string_field(environment, field, "$.environment", violations);
    }
    nullable_string_field(environment, "browser", "$.environment", violations);
}

fn validate_gate_inputs(root: &Map<String, Value>, violations: &mut Vec<Violation>) {
    let Some(inputs) = object_field(root, "inputs", "$", violations) else {
        return;
    };
    require_fields(
        inputs,
        "$.inputs",
        &[
            "pose_asset_sha256",
            "motion_graph_sha256",
            "policy_sha256",
            "browser_bundle_sha256",
        ],
        violations,
    );
    for field in [
        "pose_asset_sha256",
        "motion_graph_sha256",
        "policy_sha256",
        "browser_bundle_sha256",
    ] {
        match inputs.get(field) {
            Some(Value::String(value)) if is_sha256(value) => {}
            Some(Value::Null) if field != "pose_asset_sha256" => {}
            _ => push(
                violations,
                "RCHAT-GATE-INPUT-HASH",
                format!("$.inputs.{field}"),
                "input hash must be lowercase 64-hex, or null when optional",
            ),
        }
    }
}

fn validate_gate_commands(
    root: &Map<String, Value>,
    status: &str,
    violations: &mut Vec<Violation>,
) {
    let Some(commands) = array_field(root, "commands", "$", violations) else {
        return;
    };
    if status == "PASS" && commands.is_empty() {
        push(
            violations,
            "RCHAT-GATE-COMMANDS",
            "$.commands",
            "a PASS gate requires command evidence",
        );
    }
    for (index, command) in commands.iter().enumerate() {
        validate_command(
            command,
            &format!("$.commands[{index}]"),
            status == "PASS",
            true,
            violations,
        );
    }
}

fn validate_gate_metrics(root: &Map<String, Value>, status: &str, violations: &mut Vec<Violation>) {
    let Some(metrics) = array_field(root, "metrics", "$", violations) else {
        return;
    };
    for (index, value) in metrics.iter().enumerate() {
        let path = format!("$.metrics[{index}]");
        let Some(metric) = object_value(value, &path, violations) else {
            continue;
        };
        require_fields(
            metric,
            &path,
            &["name", "actual", "operator", "threshold", "unit", "status"],
            violations,
        );
        non_empty_string_field(metric, "name", &path, violations);
        non_empty_string_field(metric, "unit", &path, violations);
        let actual = number_field(metric, "actual", &path, violations).unwrap_or(f64::NAN);
        let threshold = number_field(metric, "threshold", &path, violations).unwrap_or(f64::NAN);
        let operator = string_field(metric, "operator", &path, violations).unwrap_or_default();
        let metric_status = string_field(metric, "status", &path, violations).unwrap_or_default();
        let comparison = match operator.as_str() {
            "eq" => (actual - threshold).abs() <= f64::EPSILON,
            "lte" => actual <= threshold,
            "gte" => actual >= threshold,
            _ => {
                push(
                    violations,
                    "RCHAT-GATE-METRIC-OPERATOR",
                    format!("{path}.operator"),
                    format!("unknown metric operator {operator}"),
                );
                false
            }
        };
        let expected_status = if comparison { "PASS" } else { "FAIL" };
        if metric_status != expected_status {
            push(
                violations,
                "RCHAT-GATE-METRIC-RESULT",
                format!("{path}.status"),
                format!("metric status must be {expected_status}"),
            );
        }
        if status == "PASS" && metric_status != "PASS" {
            push(
                violations,
                "RCHAT-GATE-METRIC-FAILURE",
                &path,
                "a PASS gate cannot contain a failed metric",
            );
        }
    }
}

fn validate_gate_artifacts(root: &Map<String, Value>, violations: &mut Vec<Violation>) {
    let Some(artifacts) = array_field(root, "artifacts", "$", violations) else {
        return;
    };
    for (index, value) in artifacts.iter().enumerate() {
        let path = format!("$.artifacts[{index}]");
        let Some(artifact) = object_value(value, &path, violations) else {
            continue;
        };
        require_fields(
            artifact,
            &path,
            &["kind", "path_or_url", "sha256", "bytes", "retention"],
            violations,
        );
        non_empty_string_field(artifact, "kind", &path, violations);
        non_empty_string_field(artifact, "path_or_url", &path, violations);
        let hash = string_field(artifact, "sha256", &path, violations).unwrap_or_default();
        if !is_sha256(&hash) {
            push(
                violations,
                "RCHAT-EVIDENCE-HASH",
                format!("{path}.sha256"),
                "artifact hash must be lowercase 64-hex SHA-256",
            );
        }
        integer_field(artifact, "bytes", &path, violations);
        let retention = string_field(artifact, "retention", &path, violations).unwrap_or_default();
        if !["pr", "candidate", "release", "permanent"].contains(&retention.as_str()) {
            push(
                violations,
                "RCHAT-RETENTION",
                format!("{path}.retention"),
                format!("unknown retention class {retention}"),
            );
        }
    }
}

fn validate_gate_failures_and_skips(
    root: &Map<String, Value>,
    status: &str,
    violations: &mut Vec<Violation>,
) {
    for field in ["failures", "skips"] {
        let values = array_field(root, field, "$", violations);
        if status == "PASS" && values.is_some_and(|values| !values.is_empty()) {
            push(
                violations,
                "RCHAT-GATE-UNRESOLVED",
                format!("$.{field}"),
                format!("a PASS gate requires empty {field}"),
            );
        }
    }
}

fn validate_gate_review(root: &Map<String, Value>, violations: &mut Vec<Violation>) {
    let Some(review) = object_field(root, "review", "$", violations) else {
        return;
    };
    require_fields(
        review,
        "$.review",
        &["primary", "independent", "reviewed_at"],
        violations,
    );
    let primary = string_field(review, "primary", "$.review", violations).unwrap_or_default();
    let independent =
        string_field(review, "independent", "$.review", violations).unwrap_or_default();
    for (field, role) in [("primary", &primary), ("independent", &independent)] {
        if !ROLES.contains(&role.as_str()) {
            push(
                violations,
                "RCHAT-ROLE",
                format!("$.review.{field}"),
                format!("unknown review role {role}"),
            );
        }
    }
    if primary == independent {
        push(
            violations,
            "RCHAT-REVIEW-INDEPENDENCE",
            "$.review",
            "primary and independent reviewers must differ",
        );
    }
    non_empty_string_field(review, "reviewed_at", "$.review", violations);
}

fn validate_gate_rollback(
    root: &Map<String, Value>,
    gate_id: &str,
    status: &str,
    violations: &mut Vec<Violation>,
) {
    let Some(rollback) = object_field(root, "rollback", "$", violations) else {
        return;
    };
    require_fields(
        rollback,
        "$.rollback",
        &["sha", "profile", "drill_passed"],
        violations,
    );
    let sha = nullable_sha_field(rollback, "sha", "$.rollback", violations);
    let profile = string_field(rollback, "profile", "$.rollback", violations).unwrap_or_default();
    let drill = bool_field(rollback, "drill_passed", "$.rollback", violations);
    if status == "PASS" && drill != Some(true) {
        push(
            violations,
            "RCHAT-GATE-ROLLBACK",
            "$.rollback.drill_passed",
            "a PASS gate requires a successful rollback drill",
        );
    }
    if gate_id == "P0" {
        let downgrade = rollback.get("downgrade_allowed").and_then(Value::as_bool);
        if profile != "repair-only" || sha.is_some() || downgrade != Some(false) {
            push(
                violations,
                "RCHAT-P0-DOWNGRADE",
                "$.rollback",
                "P0 gate rollback must be repair-only and forbid downgrade",
            );
        }
    } else if sha.is_none() {
        push(
            violations,
            "RCHAT-GATE-ROLLBACK-SHA",
            "$.rollback.sha",
            "non-P0 gate rollback requires a Git SHA",
        );
    }
}

fn validate_gate_against_registry(
    gate_id: &str,
    status: &str,
    required_work: &[String],
    git_sha: Option<&str>,
    registry: &Value,
    violations: &mut Vec<Violation>,
) {
    let registry_report = validate_registry(registry);
    if !registry_report.is_valid() {
        push(
            violations,
            "RCHAT-GATE-REGISTRY-INVALID",
            "$",
            format!(
                "cross-reference registry has {} violation(s)",
                registry_report.violations.len()
            ),
        );
        return;
    }
    let Some(root) = registry.as_object() else {
        return;
    };
    let gate = root
        .get("gates")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .find(|gate| gate.get("gate_id").and_then(Value::as_str) == Some(gate_id));
    let Some(gate) = gate else {
        push(
            violations,
            "RCHAT-GATE-NOT-REGISTERED",
            "$.gate_id",
            format!("gate {gate_id} is absent from registry"),
        );
        return;
    };
    let registered: HashSet<_> = gate
        .get("required_work")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
        .collect();
    let recorded: HashSet<_> = required_work.iter().map(String::as_str).collect();
    if registered != recorded {
        push(
            violations,
            "RCHAT-GATE-WORK-MISMATCH",
            "$.required_work_items",
            "gate required_work_items do not match the registry gate",
        );
    }
    if status == "PASS" {
        let mut item_status = HashMap::new();
        for field in ["work_items", "specialist_work_items"] {
            for item in root
                .get(field)
                .and_then(Value::as_array)
                .into_iter()
                .flatten()
            {
                if let (Some(id), Some(status)) = (
                    item.get("id").and_then(Value::as_str),
                    item.get("status").and_then(Value::as_str),
                ) {
                    item_status.insert(id, status);
                }
            }
        }
        for work_id in required_work {
            if item_status.get(work_id.as_str()) != Some(&"ACCEPTED") {
                push(
                    violations,
                    "RCHAT-GATE-WORK-NOT-ACCEPTED",
                    "$.required_work_items",
                    format!("PASS gate includes non-accepted work {work_id}"),
                );
            }
        }
        if let Some(registered_sha) = gate
            .get("record")
            .and_then(Value::as_object)
            .and_then(|record| record.get("git_sha"))
            .and_then(Value::as_str)
        {
            if git_sha != Some(registered_sha) {
                push(
                    violations,
                    "RCHAT-GATE-SHA-MISMATCH",
                    "$.git.sha",
                    format!("gate SHA does not match registry record {registered_sha}"),
                );
            }
        }
    }
}

fn validate_command(
    value: &Value,
    path: &str,
    require_success: bool,
    exact_gate_shape: bool,
    violations: &mut Vec<Violation>,
) {
    let Some(command) = object_value(value, path, violations) else {
        return;
    };
    let fields = if exact_gate_shape {
        &[
            "command",
            "exit_code",
            "duration_ms",
            "stdout_artifact",
            "stderr_artifact",
        ][..]
    } else {
        &["command", "exit_code", "duration_ms"][..]
    };
    require_fields(command, path, fields, violations);
    if exact_gate_shape {
        reject_unknown_fields(command, path, fields, violations);
    }
    non_empty_string_field(command, "command", path, violations);
    let exit_code = signed_integer_field(command, "exit_code", path, violations);
    integer_field(command, "duration_ms", path, violations);
    if exact_gate_shape {
        nullable_string_field(command, "stdout_artifact", path, violations);
        nullable_string_field(command, "stderr_artifact", path, violations);
    }
    if require_success && exit_code != Some(0) {
        push(
            violations,
            "RCHAT-COMMAND-FAILED",
            format!("{path}.exit_code"),
            "accepted work or PASS gate requires exit_code=0",
        );
    }
}

fn validate_evidence(value: &Value, path: &str, violations: &mut Vec<Violation>) {
    let Some(evidence) = object_value(value, path, violations) else {
        return;
    };
    require_fields(evidence, path, &["path", "sha256"], violations);
    non_empty_string_field(evidence, "path", path, violations);
    let hash = string_field(evidence, "sha256", path, violations).unwrap_or_default();
    if !is_sha256(&hash) {
        push(
            violations,
            "RCHAT-EVIDENCE-HASH",
            format!("{path}.sha256"),
            "evidence hash must be lowercase 64-hex SHA-256",
        );
    }
}

fn require_fields(
    object: &Map<String, Value>,
    path: &str,
    fields: &[&str],
    violations: &mut Vec<Violation>,
) {
    for field in fields {
        if !object.contains_key(*field) {
            push(
                violations,
                "RCHAT-FIELD-MISSING",
                format!("{path}.{field}"),
                format!("required field {field} is missing"),
            );
        }
    }
}

fn reject_unknown_fields(
    object: &Map<String, Value>,
    path: &str,
    allowed: &[&str],
    violations: &mut Vec<Violation>,
) {
    let allowed: HashSet<&str> = allowed.iter().copied().collect();
    let mut unknown: Vec<&str> = object
        .keys()
        .map(String::as_str)
        .filter(|field| !allowed.contains(field))
        .collect();
    unknown.sort_unstable();
    for field in unknown {
        push(
            violations,
            "RCHAT-UNKNOWN-FIELD",
            format!("{path}.{field}"),
            format!("field {field} is not permitted by the gate-v1 command contract"),
        );
    }
}

fn object_value<'a>(
    value: &'a Value,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Option<&'a Map<String, Value>> {
    if let Some(object) = value.as_object() {
        Some(object)
    } else {
        push(violations, "RCHAT-TYPE", path, "expected JSON object");
        None
    }
}

fn object_field<'a>(
    object: &'a Map<String, Value>,
    field: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Option<&'a Map<String, Value>> {
    object
        .get(field)
        .and_then(|value| object_value(value, &format!("{path}.{field}"), violations))
}

fn array_field<'a>(
    object: &'a Map<String, Value>,
    field: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Option<&'a Vec<Value>> {
    let value = object.get(field)?;
    if let Some(array) = value.as_array() {
        Some(array)
    } else {
        push(
            violations,
            "RCHAT-TYPE",
            format!("{path}.{field}"),
            "expected JSON array",
        );
        None
    }
}

fn string_field(
    object: &Map<String, Value>,
    field: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Option<String> {
    let value = object.get(field)?;
    if let Some(text) = value.as_str() {
        Some(text.to_owned())
    } else {
        push(
            violations,
            "RCHAT-TYPE",
            format!("{path}.{field}"),
            "expected string",
        );
        None
    }
}

fn non_empty_string_field(
    object: &Map<String, Value>,
    field: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Option<String> {
    let value = string_field(object, field, path, violations)?;
    if value.is_empty() {
        push(
            violations,
            "RCHAT-EMPTY",
            format!("{path}.{field}"),
            "string cannot be empty",
        );
    }
    Some(value)
}

fn nullable_string_field(
    object: &Map<String, Value>,
    field: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Option<String> {
    match object.get(field) {
        Some(Value::String(value)) => Some(value.clone()),
        Some(Value::Null) | None => None,
        Some(_) => {
            push(
                violations,
                "RCHAT-TYPE",
                format!("{path}.{field}"),
                "expected string or null",
            );
            None
        }
    }
}

fn nullable_sha_field(
    object: &Map<String, Value>,
    field: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Option<String> {
    let value = nullable_string_field(object, field, path, violations);
    if value.as_deref().is_some_and(|sha| !is_git_sha(sha)) {
        push(
            violations,
            "RCHAT-SHA",
            format!("{path}.{field}"),
            "expected lowercase 40-hex Git SHA or null",
        );
    }
    value
}

fn string_array_field(
    object: &Map<String, Value>,
    field: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Vec<String> {
    let Some(values) = array_field(object, field, path, violations) else {
        return Vec::new();
    };
    let mut result = Vec::new();
    let mut seen = HashSet::new();
    for (index, value) in values.iter().enumerate() {
        let Some(text) = value.as_str().filter(|text| !text.is_empty()) else {
            push(
                violations,
                "RCHAT-TYPE",
                format!("{path}.{field}[{index}]"),
                "expected non-empty string",
            );
            continue;
        };
        if !seen.insert(text) {
            push(
                violations,
                "RCHAT-ARRAY-DUPLICATE",
                format!("{path}.{field}[{index}]"),
                format!("duplicate value {text}"),
            );
        }
        result.push(text.to_owned());
    }
    result
}

fn bool_field(
    object: &Map<String, Value>,
    field: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Option<bool> {
    let value = object.get(field)?;
    if let Some(boolean) = value.as_bool() {
        Some(boolean)
    } else {
        push(
            violations,
            "RCHAT-TYPE",
            format!("{path}.{field}"),
            "expected boolean",
        );
        None
    }
}

fn integer_field(
    object: &Map<String, Value>,
    field: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Option<u64> {
    let value = object.get(field)?;
    if let Some(integer) = value.as_u64() {
        Some(integer)
    } else {
        push(
            violations,
            "RCHAT-TYPE",
            format!("{path}.{field}"),
            "expected non-negative integer",
        );
        None
    }
}

fn signed_integer_field(
    object: &Map<String, Value>,
    field: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Option<i64> {
    let value = object.get(field)?;
    if let Some(integer) = value.as_i64() {
        Some(integer)
    } else {
        push(
            violations,
            "RCHAT-TYPE",
            format!("{path}.{field}"),
            "expected integer",
        );
        None
    }
}

fn number_field(
    object: &Map<String, Value>,
    field: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) -> Option<f64> {
    let value = object.get(field)?;
    if let Some(number) = value.as_f64() {
        Some(number)
    } else {
        push(
            violations,
            "RCHAT-TYPE",
            format!("{path}.{field}"),
            "expected finite JSON number",
        );
        None
    }
}

fn expect_exact_string(
    object: &Map<String, Value>,
    field: &str,
    expected: &str,
    path: &str,
    violations: &mut Vec<Violation>,
) {
    if string_field(object, field, path, violations).as_deref() != Some(expected) {
        push(
            violations,
            "RCHAT-CONST",
            format!("{path}.{field}"),
            format!("expected {expected}"),
        );
    }
}

fn expect_u64(
    object: &Map<String, Value>,
    field: &str,
    expected: u64,
    path: &str,
    violations: &mut Vec<Violation>,
) {
    if integer_field(object, field, path, violations) != Some(expected) {
        push(
            violations,
            "RCHAT-CONST",
            format!("{path}.{field}"),
            format!("expected {expected}"),
        );
    }
}

fn expect_computed_u64(
    object: &Map<String, Value>,
    field: &str,
    expected: u64,
    path: &str,
    violations: &mut Vec<Violation>,
) {
    if integer_field(object, field, path, violations) != Some(expected) {
        push(
            violations,
            "RCHAT-PROGRESS",
            format!("{path}.{field}"),
            format!("computed value is {expected}"),
        );
    }
}

fn expect_computed_f64(
    object: &Map<String, Value>,
    field: &str,
    expected: f64,
    path: &str,
    violations: &mut Vec<Violation>,
) {
    let actual = number_field(object, field, path, violations);
    if actual.is_none_or(|actual| (actual - expected).abs() > 0.0001) {
        push(
            violations,
            "RCHAT-PROGRESS",
            format!("{path}.{field}"),
            format!("computed value is {expected:.4}"),
        );
    }
}

fn percent(numerator: u64, denominator: u64) -> f64 {
    if denominator == 0 {
        0.0
    } else {
        numerator as f64 * 100.0 / denominator as f64
    }
}

fn is_git_sha(value: &str) -> bool {
    value.len() == 40
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn push(
    violations: &mut Vec<Violation>,
    code: &'static str,
    path: impl Into<String>,
    message: impl Into<String>,
) {
    violations.push(Violation {
        code,
        path: path.into(),
        message: message.into(),
    });
}
