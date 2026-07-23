use std::path::PathBuf;
use wizard_avatar_pose_tool::{exclude_non_pose_source, NonPoseExclusionConfig};

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-pose-exclude-non-pose: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut arguments = std::env::args_os().skip(1);
    let candidate_id = next_string(&mut arguments, "candidate ID")?;
    let expected_source_sha256 = next_string(&mut arguments, "expected source SHA-256")?;
    let finding = next_string(&mut arguments, "non-pose finding")?;
    let repo_root = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    if arguments.next().is_some() {
        return Err("usage: wizard-avatar-pose-exclude-non-pose CANDIDATE_ID SOURCE_SHA256 FINDING [repo-root]".into());
    }
    let report = exclude_non_pose_source(&NonPoseExclusionConfig {
        repo_root,
        candidate_id,
        expected_source_sha256,
        reviewer: "codex-direct-frame-comparison".to_string(),
        finding,
    })?;
    println!(
        "{} disposition=excluded_non_pose evidence={} runtime_promotion=forbidden",
        report.source_record_id, report.visual_evidence.path
    );
    Ok(())
}

fn next_string(
    arguments: &mut impl Iterator<Item = std::ffi::OsString>,
    label: &str,
) -> Result<String, Box<dyn std::error::Error>> {
    arguments
        .next()
        .and_then(|argument| argument.into_string().ok())
        .ok_or_else(|| format!("missing {label}").into())
}
