use std::path::PathBuf;
use wizard_avatar_pose_tool::{compile_one_newsroom_layer_source, NewsroomLayerCompileConfig};

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-newsroom-layer-compile-one: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut arguments = std::env::args_os().skip(1);
    let source_id = arguments
        .next()
        .and_then(|argument| argument.into_string().ok())
        .ok_or("usage: wizard-avatar-newsroom-layer-compile-one SOURCE_ID [repo-root]")?;
    let repo_root = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    if arguments.next().is_some() {
        return Err("too many arguments".into());
    }

    let report = compile_one_newsroom_layer_source(&NewsroomLayerCompileConfig {
        repo_root,
        source_id,
    })?;
    println!(
        "{} automated_pass={} visual_review=pending targets={} assigned={} overlap={} unassigned={} recomposition_iou={:.6} color_fidelity={:.6} source_spec_sha256={}",
        report.source_id,
        report.passed,
        report.targets.len(),
        report.assigned_source_pixels,
        report.overlap_pixels,
        report.unassigned_pixels,
        report.recomposition_metrics.silhouette_iou,
        report.recomposition_metrics.foreground_color_fidelity,
        report.source_target_spec_sha256,
    );
    if !report.passed {
        return Err("newsroom layer split failed exact recomposition".into());
    }
    Ok(())
}
