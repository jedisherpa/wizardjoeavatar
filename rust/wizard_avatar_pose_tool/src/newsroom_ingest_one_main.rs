use std::path::PathBuf;
use wizard_avatar_pose_tool::{
    admit_one_newsroom_source, IsolationConfig, NewsroomAdmitOneConfig, VerificationConfig,
    MINIMUM_FIDELITY,
};

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-newsroom-ingest-one: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut arguments = std::env::args_os().skip(1);
    let source_id = arguments
        .next()
        .and_then(|argument| argument.into_string().ok())
        .ok_or(
            "usage: wizard-avatar-newsroom-ingest-one SOURCE_ID [repo-root] [matte-tolerance]",
        )?;
    let repo_root = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    let matte_tolerance = arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| value.parse::<u16>())
        .transpose()?
        .unwrap_or(32);
    if arguments.next().is_some() {
        return Err("too many arguments".into());
    }
    let report = admit_one_newsroom_source(&NewsroomAdmitOneConfig {
        repo_root,
        source_id,
        isolation: IsolationConfig {
            matte_tolerance,
            neutral_shadow_min_luma: 255,
            neutral_shadow_max_chroma: 0,
            ..IsolationConfig::default()
        },
        verification: VerificationConfig::default(),
        minimum_fidelity: MINIMUM_FIDELITY,
    })?;
    println!(
        "{} automated_pass={} visual_review=pending silhouette_iou={:.6} color_match={:.6} color_fidelity={:.6} graph_pixels={} overlay(matched={},missing={},extra={},mismatched={})",
        report.source_id,
        report.passed,
        report.metrics.silhouette_iou,
        report.metrics.foreground_color_match_ratio,
        report.metrics.foreground_color_fidelity,
        report.metrics.graph_foreground_pixels,
        report.overlay_counts.matched,
        report.overlay_counts.missing,
        report.overlay_counts.extra,
        report.overlay_counts.mismatched,
    );
    if !report.passed {
        return Err("newsroom source failed the 95% automated gate".into());
    }
    Ok(())
}
