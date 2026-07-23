use std::path::PathBuf;
use wizard_avatar_pose_tool::{
    admit_one_pose, AdmitOneConfig, ForegroundBounds, IsolationConfig, VerificationConfig,
    MINIMUM_FIDELITY,
};

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-pose-ingest-one: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut arguments = std::env::args_os().skip(1);
    let candidate_id = arguments
        .next()
        .and_then(|argument| argument.into_string().ok())
        .ok_or("usage: wizard-avatar-pose-ingest-one CANDIDATE_ID [repo-root] [downloads-dir] [matte-tolerance] [floor-shadow-start-y] [neutral-shadow-max-chroma] [floor-shadow-max-chroma] [enclosed-matte-min-pixels] [pale-effect-recovery-bounds] [floor-shadow-min-luma] [forced-matte-removal-bounds] [forced-transparent-bounds]")?;
    let repo_root = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    let downloads_dir = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(default_downloads_dir);
    let matte_tolerance = arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| value.parse::<u16>())
        .transpose()?
        .unwrap_or(96);
    let floor_shadow_start_y = arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| value.parse::<u32>())
        .transpose()?;
    let neutral_shadow_max_chroma = arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| value.parse::<u8>())
        .transpose()?
        .unwrap_or(IsolationConfig::default().neutral_shadow_max_chroma);
    let neutral_floor_shadow_max_chroma = arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| value.parse::<u8>())
        .transpose()?
        .unwrap_or(IsolationConfig::default().neutral_floor_shadow_max_chroma);
    let enclosed_matte_component_min_pixels = arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| value.parse::<u32>())
        .transpose()?
        .map(Some)
        .unwrap_or(IsolationConfig::default().enclosed_matte_component_min_pixels);
    let pale_effect_recovery_bounds = arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| parse_recovery_bounds(&value))
        .transpose()?
        .unwrap_or([None; 4]);
    let neutral_floor_shadow_min_luma = arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| value.parse::<u8>())
        .transpose()?
        .unwrap_or(IsolationConfig::default().neutral_floor_shadow_min_luma);
    let forced_matte_removal_bounds = arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| parse_bounds(&value, "forced matte-removal"))
        .transpose()?
        .unwrap_or([None; 4]);
    let forced_transparent_bounds = arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| parse_bounds(&value, "forced transparent"))
        .transpose()?
        .unwrap_or([None; 4]);
    if arguments.next().is_some() {
        return Err("too many arguments".into());
    }

    let report = admit_one_pose(&AdmitOneConfig {
        repo_root,
        downloads_dir,
        candidate_id,
        isolation: IsolationConfig {
            matte_tolerance,
            neutral_floor_shadow_start_y: floor_shadow_start_y,
            neutral_shadow_max_chroma,
            neutral_floor_shadow_max_chroma,
            neutral_floor_shadow_min_luma,
            enclosed_matte_component_min_pixels,
            pale_effect_recovery_bounds,
            forced_matte_removal_bounds,
            forced_transparent_bounds,
            ..IsolationConfig::default()
        },
        verification: VerificationConfig::default(),
        minimum_fidelity: MINIMUM_FIDELITY,
    })?;
    println!(
        "{} automated_pass={} visual_review=pending silhouette_iou={:.6} foreground_color_match_ratio={:.6} foreground_color_fidelity={:.6} graph_pixels={} overlay(matched={},missing={},extra={},mismatched={})",
        report.source_record_id,
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
        return Err("pose failed the 95% admission gate".into());
    }
    Ok(())
}

fn default_downloads_dir() -> PathBuf {
    std::env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("/Users/paul"))
        .join("Downloads")
}

fn parse_recovery_bounds(value: &str) -> Result<[Option<ForegroundBounds>; 4], String> {
    parse_bounds(value, "pale-effect recovery")
}

fn parse_bounds(value: &str, description: &str) -> Result<[Option<ForegroundBounds>; 4], String> {
    if value == "-" || value.trim().is_empty() {
        return Ok([None; 4]);
    }
    let mut parsed = [None; 4];
    for (index, region) in value.split(';').enumerate() {
        if index >= parsed.len() {
            return Err(format!("at most four {description} bounds are supported"));
        }
        let coordinates = region
            .split(',')
            .map(str::parse::<u32>)
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| format!("invalid {description} bounds: {error}"))?;
        if coordinates.len() != 4 {
            return Err(format!(
                "each {description} bound must be left,top,right,bottom"
            ));
        }
        let bounds = ForegroundBounds {
            left: coordinates[0],
            top: coordinates[1],
            right: coordinates[2],
            bottom: coordinates[3],
        };
        if bounds.left > bounds.right || bounds.top > bounds.bottom {
            return Err(format!("{description} bounds are inverted"));
        }
        parsed[index] = Some(bounds);
    }
    Ok(parsed)
}
