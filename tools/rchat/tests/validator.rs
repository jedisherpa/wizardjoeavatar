use std::collections::HashSet;

use serde_json::{json, Value};
use wizardjoe_rchat_validator::{validate_gate, validate_registry};

fn registry() -> Value {
    serde_json::from_str(include_str!("fixtures/valid-registry.json")).unwrap()
}

fn gate() -> Value {
    serde_json::from_str(include_str!("fixtures/valid-gate.json")).unwrap()
}

fn codes(value: &Value) -> HashSet<&'static str> {
    validate_registry(value)
        .violations
        .into_iter()
        .map(|violation| violation.code)
        .collect()
}

#[test]
fn valid_registry_passes() {
    let report = validate_registry(&registry());
    assert!(report.is_valid(), "{:#?}", report.violations);
}

#[test]
fn valid_gate_passes() {
    let report = validate_gate(&gate(), None);
    assert!(report.is_valid(), "{:#?}", report.violations);
}

#[test]
fn gate_command_requires_artifact_fields() {
    let mut value = gate();
    value["commands"][0]
        .as_object_mut()
        .unwrap()
        .remove("stdout_artifact");

    let report = validate_gate(&value, None);
    assert!(report.violations.iter().any(|violation| {
        violation.code == "RCHAT-FIELD-MISSING" && violation.path == "$.commands[0].stdout_artifact"
    }));
}

#[test]
fn gate_command_artifacts_are_null_or_string() {
    let mut value = gate();
    value["commands"][0]["stdout_artifact"] = json!("evidence/stdout.txt");
    value["commands"][0]["stderr_artifact"] = json!(42);

    let report = validate_gate(&value, None);
    assert!(report.violations.iter().any(|violation| {
        violation.code == "RCHAT-TYPE" && violation.path == "$.commands[0].stderr_artifact"
    }));
    assert!(!report
        .violations
        .iter()
        .any(|violation| violation.path == "$.commands[0].stdout_artifact"));
}

#[test]
fn gate_command_rejects_unknown_fields() {
    let mut value = gate();
    value["commands"][0]["output"] = json!("uncontracted");

    let report = validate_gate(&value, None);
    assert!(report.violations.iter().any(|violation| {
        violation.code == "RCHAT-UNKNOWN-FIELD" && violation.path == "$.commands[0].output"
    }));
}

#[test]
fn schemas_are_valid_json_and_name_the_contracts() {
    let registry_schema: Value = serde_json::from_str(include_str!(
        "../../../schemas/rchat/registry-v1.schema.json"
    ))
    .unwrap();
    let gate_schema: Value =
        serde_json::from_str(include_str!("../../../schemas/rchat/gate-v1.schema.json")).unwrap();

    assert_eq!(registry_schema["title"], "wizardjoe-rchat-registry/v1");
    assert_eq!(gate_schema["title"], "wizardjoe-rchat-gate/v1");

    let expected: HashSet<&str> = [
        "command",
        "exit_code",
        "duration_ms",
        "stdout_artifact",
        "stderr_artifact",
    ]
    .into_iter()
    .collect();
    let command_schema = &gate_schema["$defs"]["command"];
    let required: HashSet<&str> = command_schema["required"]
        .as_array()
        .unwrap()
        .iter()
        .map(|field| field.as_str().unwrap())
        .collect();
    let properties: HashSet<&str> = command_schema["properties"]
        .as_object()
        .unwrap()
        .keys()
        .map(String::as_str)
        .collect();
    let gate_fixture = gate();
    let fixture_fields: HashSet<&str> = gate_fixture["commands"][0]
        .as_object()
        .unwrap()
        .keys()
        .map(String::as_str)
        .collect();

    assert_eq!(command_schema["additionalProperties"], false);
    assert_eq!(required, expected);
    assert_eq!(properties, expected);
    assert_eq!(fixture_fields, expected);
}

#[test]
fn rejects_duplicate_ids_and_missing_dependencies() {
    let mut value = registry();
    value["work_items"][1]["id"] = json!("RCHAT-FLOW-001");
    value["work_items"][1]["dependencies"] = json!(["RCHAT-MISSING-999"]);

    let found = codes(&value);
    assert!(found.contains("RCHAT-ID-DUPLICATE"));
    assert!(found.contains("RCHAT-DEPENDENCY-MISSING"));
}

#[test]
fn rejects_dependency_cycles() {
    let mut value = registry();
    value["work_items"][0]["dependencies"] = json!(["RCHAT-FLOW-020"]);

    assert!(codes(&value).contains("RCHAT-DEPENDENCY-CYCLE"));
}

#[test]
fn enforces_ready_base_sha_and_accepted_dependencies() {
    let mut value = registry();
    value["work_items"][0]["status"] = json!("REOPENED");
    value["work_items"][1]["status"] = json!("READY");

    let found = codes(&value);
    assert!(found.contains("RCHAT-DEPENDENCY-NOT-ACCEPTED"));
    assert!(found.contains("RCHAT-BASE-SHA"));
}

#[test]
fn accepted_work_requires_commands_evidence_and_rollback() {
    let mut value = registry();
    let work = &mut value["work_items"][1];
    work["status"] = json!("ACCEPTED");
    work["base_sha"] = json!("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    work["result_sha"] = json!("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    work["started_at"] = json!("2026-07-13T00:00:00Z");
    work["finished_at"] = json!("2026-07-13T00:01:00Z");
    work["rollback"]["profile"] = json!("");

    let found = codes(&value);
    assert!(found.contains("RCHAT-ACCEPTED-COMMANDS"));
    assert!(found.contains("RCHAT-ACCEPTED-EVIDENCE"));
    assert!(found.contains("RCHAT-ACCEPTED-ROLLBACK"));
}

#[test]
fn rejects_non_scalar_owner_and_self_review() {
    let mut value = registry();
    value["work_items"][1]["owner"] = json!(["FLOW", "MOTION"]);
    value["specialist_work_items"][0]["reviewers"] = json!(["RUNTIME"]);

    let found = codes(&value);
    assert!(found.contains("RCHAT-TYPE"));
    assert!(found.contains("RCHAT-SELF-REVIEW"));
}

#[test]
fn rejects_lock_path_conflicts() {
    let mut value = registry();
    value["work_items"][1]["status"] = json!("IN_PROGRESS");
    value["work_items"][1]["base_sha"] = json!("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    value["work_items"][1]["required_locks"] = json!(["LOCK-RCHAT-REGISTRY", "LOCK-RCHAT-SECOND"]);
    value["locks"][0]["holder"] = json!("FLOW");
    value["locks"][0]["work_id"] = json!("RCHAT-FLOW-020");
    value["locks"][0]["base_sha"] = json!("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    value["locks"][0]["acquired_at"] = json!("2026-07-13T00:00:00Z");
    value["locks"].as_array_mut().unwrap().push(json!({
        "lock_id": "LOCK-RCHAT-SECOND",
        "paths": ["docs/cartoon-animation-program/rust-chatbot/registry.json"],
        "holder": "FLOW",
        "work_id": "RCHAT-FLOW-020",
        "acquired_at": "2026-07-13T00:00:00Z",
        "expires_at": null,
        "base_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "reason": "test"
    }));

    assert!(codes(&value).contains("RCHAT-LOCK-PATH-CONFLICT"));
}

#[test]
fn ready_work_requires_free_locks() {
    let mut value = registry();
    value["work_items"][1]["status"] = json!("READY");
    value["work_items"][1]["base_sha"] = json!("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    value["work_items"][1]["required_locks"] = json!(["LOCK-RCHAT-REGISTRY"]);
    value["locks"][0]["holder"] = json!("INT");
    value["locks"][0]["work_id"] = json!("RCHAT-FLOW-001");
    value["locks"][0]["base_sha"] = json!("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    value["locks"][0]["acquired_at"] = json!("2026-07-13T00:00:00Z");
    value["work_items"][0]["status"] = json!("IN_PROGRESS");
    value["work_items"][0]["required_locks"] = json!(["LOCK-RCHAT-REGISTRY"]);

    assert!(codes(&value).contains("RCHAT-READY-LOCK-BUSY"));
}

#[test]
fn rejects_parent_child_and_gate_reference_drift() {
    let mut value = registry();
    value["work_items"][0]["required_children"] = json!([]);
    value["work_items"][1]["gate_id"] = json!("MISSING");

    let found = codes(&value);
    assert!(found.contains("RCHAT-PARENT-CHILDREN"));
    assert!(found.contains("RCHAT-WORK-GATE-MISSING"));
}

#[test]
fn rejects_progress_arithmetic_drift() {
    let mut value = registry();
    value["progress"]["accepted_weight"] = json!(2);
    value["progress"]["program_percent"] = json!(100.0);

    assert!(codes(&value).contains("RCHAT-PROGRESS"));
}

#[test]
fn passed_registry_gate_sha_matches_required_work() {
    let mut value = registry();
    value["work_items"][0]["result_sha"] = json!("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");

    assert!(codes(&value).contains("RCHAT-GATE-WORK-SHA"));
}

#[test]
fn p0_forbids_downgrade() {
    let mut value = registry();
    value["work_items"][0]["rollback"]["profile"] = json!("pose-v3");
    value["work_items"][0]["rollback"]["sha"] = json!("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    value["work_items"][0]["rollback"]["downgrade_allowed"] = json!(true);

    assert!(codes(&value).contains("RCHAT-P0-DOWNGRADE"));
}

#[test]
fn deployment_identity_requires_one_sha() {
    let mut value = registry();
    value["deployments"] = json!([{
        "deployment_id": "production-1",
        "environment": "production",
        "f0_approved_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "pushed_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "built_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "deployed_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "endpoint_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "status": "PLANNED"
    }]);

    assert!(codes(&value).contains("RCHAT-DEPLOYMENT-SHA-MISMATCH"));
}

#[test]
fn deployment_ids_are_unique() {
    let mut value = registry();
    let deployment = json!({
        "deployment_id": "production-1",
        "environment": "production",
        "f0_approved_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "pushed_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "built_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "deployed_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "endpoint_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "status": "PLANNED"
    });
    value["deployments"] = json!([deployment.clone(), deployment]);

    assert!(codes(&value).contains("RCHAT-DEPLOYMENT-DUPLICATE"));
}

#[test]
fn pass_gate_rejects_failed_commands_metrics_and_skips() {
    let mut value = gate();
    value["commands"][0]["exit_code"] = json!(1);
    value["metrics"][0]["status"] = json!("FAIL");
    value["skips"] = json!(["browser QA"]);

    let found: HashSet<_> = validate_gate(&value, None)
        .violations
        .into_iter()
        .map(|violation| violation.code)
        .collect();
    assert!(found.contains("RCHAT-COMMAND-FAILED"));
    assert!(found.contains("RCHAT-GATE-METRIC-FAILURE"));
    assert!(found.contains("RCHAT-GATE-UNRESOLVED"));
}
