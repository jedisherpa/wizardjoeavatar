use anyhow::{bail, Context};
use serde::Serialize;
use std::collections::BTreeMap;
use std::path::PathBuf;
use std::time::Instant;
use wizard_avatar_engine::codec::CodecTag;
use wizard_avatar_engine::controller::WizardCommand;
use wizard_avatar_engine::frame_source::{ProceduralWizardFrameSource, DEFAULT_COLS, DEFAULT_ROWS};

#[derive(Clone, Copy, Debug)]
struct Profile {
    name: &'static str,
    cols: usize,
    rows: usize,
    target_fps: f32,
    frames: usize,
}

#[derive(Debug, Serialize)]
struct ProfileEvidence {
    name: &'static str,
    cols: usize,
    rows: usize,
    target_fps: f32,
    frames: usize,
    elapsed_seconds: f32,
    measured_fps: f32,
    target_met: bool,
    average_raw_bytes: f32,
    average_wire_bytes: f32,
    compression_ratio: f32,
    keyframes: usize,
    codec_tag_counts: BTreeMap<u8, usize>,
}

#[derive(Debug, Serialize)]
struct PerformanceEvidence {
    profiles: Vec<ProfileEvidence>,
}

fn main() -> anyhow::Result<()> {
    let evidence = run_profiles()?;
    write_evidence(&evidence)?;
    for profile in &evidence.profiles {
        println!(
            "{}: {:.1} fps measured vs {:.1} target, ratio {:.4}",
            profile.name, profile.measured_fps, profile.target_fps, profile.compression_ratio
        );
    }
    if let Some(profile) = evidence.profiles.iter().find(|profile| !profile.target_met) {
        bail!(
            "{} profile did not meet target fps: measured {:.1}, target {:.1}",
            profile.name,
            profile.measured_fps,
            profile.target_fps
        );
    }
    Ok(())
}

fn run_profiles() -> anyhow::Result<PerformanceEvidence> {
    let profiles = [
        Profile {
            name: "low",
            cols: 180,
            rows: 101,
            target_fps: 15.0,
            frames: 90,
        },
        Profile {
            name: "medium",
            cols: 240,
            rows: 135,
            target_fps: 24.0,
            frames: 144,
        },
        Profile {
            name: "high",
            cols: DEFAULT_COLS,
            rows: DEFAULT_ROWS,
            target_fps: 30.0,
            frames: 144,
        },
    ];
    let mut results = Vec::new();
    for profile in profiles {
        results.push(run_profile(profile)?);
    }
    Ok(PerformanceEvidence { profiles: results })
}

fn run_profile(profile: Profile) -> anyhow::Result<ProfileEvidence> {
    let mut source =
        ProceduralWizardFrameSource::new(profile.cols, profile.rows, profile.target_fps);
    let move_result = source.apply_command(WizardCommand::new(
        "path",
        serde_json::json!({
            "points": [
                {"x": -2.0, "z": 4.2},
                {"x": 2.0, "z": 4.8},
                {"x": 1.5, "z": 6.4},
                {"x": -1.5, "z": 5.6}
            ],
            "loop": true,
            "speed": 1.4
        }),
    ));
    if !move_result.ok {
        bail!(
            "failed to configure performance path: {}",
            move_result.message
        );
    }

    let started = Instant::now();
    let mut raw_bytes = 0usize;
    let mut wire_bytes = 0usize;
    let mut keyframes = 0usize;
    let mut tag_counts: BTreeMap<u8, usize> = BTreeMap::new();
    for _ in 0..profile.frames {
        let (message, frame) = source
            .next_encoded_frame("adaptive")
            .with_context(|| format!("failed to encode {} frame", profile.name))?;
        raw_bytes += frame.raw_size;
        wire_bytes += message.len();
        keyframes += usize::from(frame.is_keyframe);
        *tag_counts.entry(frame.codec_tag).or_insert(0) += 1;
    }
    let elapsed_seconds = started.elapsed().as_secs_f32();
    let measured_fps = profile.frames as f32 / elapsed_seconds.max(0.001);
    let target_met = measured_fps >= profile.target_fps;
    let average_raw_bytes = raw_bytes as f32 / profile.frames as f32;
    let average_wire_bytes = wire_bytes as f32 / profile.frames as f32;
    let compression_ratio = wire_bytes as f32 / raw_bytes.max(1) as f32;

    if !tag_counts.contains_key(&(CodecTag::Delta as u8)) {
        bail!("{} profile never emitted delta frames", profile.name);
    }
    if keyframes == 0 {
        bail!("{} profile did not emit keyframes", profile.name);
    }

    Ok(ProfileEvidence {
        name: profile.name,
        cols: profile.cols,
        rows: profile.rows,
        target_fps: profile.target_fps,
        frames: profile.frames,
        elapsed_seconds,
        measured_fps,
        target_met,
        average_raw_bytes,
        average_wire_bytes,
        compression_ratio,
        keyframes,
        codec_tag_counts: tag_counts,
    })
}

fn write_evidence(evidence: &PerformanceEvidence) -> anyhow::Result<()> {
    let root =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../evidence/wizard/rust-performance");
    std::fs::create_dir_all(&root)
        .with_context(|| format!("failed to create {}", root.display()))?;
    let json_path = root.join("performance-summary.json");
    let md_path = root.join("README.md");
    std::fs::write(&json_path, serde_json::to_vec_pretty(evidence)?)
        .with_context(|| format!("failed to write {}", json_path.display()))?;
    std::fs::write(&md_path, render_markdown(evidence))
        .with_context(|| format!("failed to write {}", md_path.display()))?;
    println!("wrote {}", json_path.display());
    println!("wrote {}", md_path.display());
    Ok(())
}

fn render_markdown(evidence: &PerformanceEvidence) -> String {
    let mut out = String::from("# Rust Wizard Avatar Performance Evidence\n\n");
    out.push_str(
        "| profile | grid | frames | measured fps | target fps | target met | wire/raw |\n",
    );
    out.push_str("|---|---:|---:|---:|---:|---|---:|\n");
    for profile in &evidence.profiles {
        out.push_str(&format!(
            "| {} | {} x {} | {} | {:.1} | {:.1} | {} | {:.4} |\n",
            profile.name,
            profile.cols,
            profile.rows,
            profile.frames,
            profile.measured_fps,
            profile.target_fps,
            if profile.target_met { "yes" } else { "no" },
            profile.compression_ratio
        ));
    }
    out.push_str("\n## Codec Tags\n\n");
    for profile in &evidence.profiles {
        out.push_str(&format!("- `{}`:", profile.name));
        for (tag, count) in &profile.codec_tag_counts {
            out.push_str(&format!(" tag `{tag}` = `{count}`;"));
        }
        out.push('\n');
    }
    out
}
