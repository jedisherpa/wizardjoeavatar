use std::path::PathBuf;
use wizard_avatar_pose_tool::{approve_newsroom_layer_comparison, NewsroomLayerVisualReviewConfig};

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-newsroom-layer-review-one: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut arguments = std::env::args_os().skip(1);
    let source_id = next_string(&mut arguments, "source ID")?;
    let reviewer = next_string(&mut arguments, "reviewer identity")?;
    let expected_source_graph_sha256 =
        next_string(&mut arguments, "reviewed source graph SHA-256")?;
    let expected_target_specs_sha256 = next_string(&mut arguments, "source target-spec SHA-256")?;
    let finding = next_string(&mut arguments, "visual comparison finding")?;
    let repo_root = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    if arguments.next().is_some() {
        return Err("usage: wizard-avatar-newsroom-layer-review-one SOURCE_ID REVIEWER SOURCE_GRAPH_SHA256 SOURCE_TARGET_SPEC_SHA256 FINDING [repo-root]".into());
    }

    let report = approve_newsroom_layer_comparison(&NewsroomLayerVisualReviewConfig {
        repo_root,
        source_id,
        reviewer,
        expected_source_graph_sha256,
        expected_target_specs_sha256,
        finding,
    })?;
    println!(
        "{} visual_review=approved targets={} ownership_map={} overlay={} exact_recomposition={}",
        report.source_id,
        report.targets.len(),
        report.layer_map.path,
        report.recomposed_over_source_png.path,
        report.recomposition_exact,
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
