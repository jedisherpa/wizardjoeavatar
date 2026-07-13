#[allow(dead_code)]
#[path = "../../../tools/rchat/src/lib.rs"]
mod rchat_validator;

use std::path::PathBuf;

#[test]
fn release_registry_is_structurally_valid_rchat_v1() {
    let repository = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let registry = repository.join("docs/cartoon-animation-program/rust-chatbot/registry.json");
    let value = rchat_validator::read_json(&registry).unwrap();
    let report = rchat_validator::validate_registry(&value);

    assert!(
        report.is_valid(),
        "release registry validation failed:\n{}",
        report
            .violations
            .iter()
            .map(|violation| format!(
                "{} {}: {}",
                violation.code, violation.path, violation.message
            ))
            .collect::<Vec<_>>()
            .join("\n")
    );
}

#[test]
fn release_registry_material_audit_is_deterministic_and_actionable() {
    let repository = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let registry = repository.join("docs/cartoon-animation-program/rust-chatbot/registry.json");
    let first = rchat_validator::validate_registry_path(&registry).unwrap();
    let second = rchat_validator::validate_registry_path(&registry).unwrap();

    assert_eq!(
        first, second,
        "material registry audit must be deterministic"
    );
    assert!(
        first.is_valid(),
        "material release registry validation failed:\n{}",
        first
            .violations
            .iter()
            .map(|violation| format!(
                "{} {}: {}",
                violation.code, violation.path, violation.message
            ))
            .collect::<Vec<_>>()
            .join("\n")
    );
}

#[test]
fn release_registry_schemas_are_parseable() {
    let repository = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    for relative_path in [
        "schemas/rchat/registry-v1.schema.json",
        "schemas/rchat/gate-v1.schema.json",
    ] {
        let path = repository.join(relative_path);
        let value = rchat_validator::read_json(&path).unwrap();
        assert!(
            value.is_object(),
            "{} must contain a JSON object",
            path.display()
        );
    }
}
