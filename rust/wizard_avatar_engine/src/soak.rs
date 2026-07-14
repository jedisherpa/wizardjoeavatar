use anyhow::{bail, Context};
use serde::Serialize;
use serde_json::json;
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Instant;
use tokio::sync::broadcast::error::TryRecvError;
use tokio::time::{sleep, Duration};
use wizard_avatar_engine::evidence::stable_hash64;
use wizard_avatar_engine::frame_source::ProceduralWizardFrameSource;
use wizard_avatar_engine::hub::AvatarFrameHub;
use wizard_avatar_engine::newsroom::{
    NewsCommand, NewsPerformanceCueV1, NewsProgram, NewsroomError, StorySensitivity, UnitInterval,
    NEWSROOM_CUE_SCHEMA_VERSION, NEWSROOM_POSE_COUNT,
};

const VIEWER_COUNTS: [usize; 5] = [0, 1, 2, 4, 8];
const MAX_RSS_GROWTH_KB: u64 = 64 * 1_024;
const MAX_ACTOR_SAMPLE_P99_SECONDS: f64 = 0.250;

#[derive(Clone, Debug, Serialize)]
struct SoakConfiguration {
    mode: &'static str,
    total_seconds: u64,
    seconds_per_viewer_count: f64,
    intended_use: &'static str,
}

#[derive(Clone, Debug, Serialize)]
struct ViewerScenario {
    viewers: usize,
    elapsed_seconds: f64,
    simulation_ticks: u64,
    measured_simulation_hz: f64,
    rendered_frames: u32,
    measured_render_fps: f64,
    simulation_deadline_misses: u64,
    render_deadline_misses: u32,
    viewer_received_frames: Vec<u64>,
    sequence_gaps: u64,
    lag_events: u64,
    canonical_hash_mismatches: u64,
    max_receiver_queue_depth: usize,
    rss_kb_start: Option<u64>,
    rss_kb_end: Option<u64>,
    rss_kb_peak: Option<u64>,
    rss_peak_growth_kb: Option<u64>,
    max_rss_growth_kb: u64,
    actor_sample_seconds: f64,
    passed: bool,
}

#[derive(Clone, Debug, Serialize)]
struct SoakEvidence {
    mode: String,
    source_git_sha: String,
    configured_total_seconds: u64,
    actual_elapsed_seconds: f64,
    broadcast_capacity: usize,
    scenarios: Vec<ViewerScenario>,
    newsroom: NewsroomSoakEvidence,
    passed: bool,
}

#[derive(Clone, Debug, Serialize)]
struct NewsroomSoakEvidence {
    cues_applied: u64,
    receipts_verified: u64,
    correction_receipts: u64,
    reduced_motion_receipts: u64,
    stale_cues_rejected: u64,
    actor_samples_validated: u64,
    actor_sample_initialization_seconds: f64,
    ticks_during_actor_sample_initialization: u64,
    actor_sample_p50_seconds: f64,
    actor_sample_p95_seconds: f64,
    actor_sample_p99_seconds: f64,
    max_actor_sample_p99_seconds: f64,
    reconnects: u64,
    expected_semantic_pose_count: usize,
    semantic_poses_seen: Vec<String>,
    semantic_coverage_passed: bool,
    generation_leaks: u64,
}

#[derive(Debug, Default)]
struct NewsroomSoakState {
    next_sequence: u64,
    cues_applied: u64,
    receipts_verified: u64,
    correction_receipts: u64,
    reduced_motion_receipts: u64,
    stale_cues_rejected: u64,
    actor_samples_validated: u64,
    actor_sample_seconds: Vec<f64>,
    reconnects: u64,
    semantic_poses_seen: std::collections::BTreeSet<String>,
    generation_leaks: u64,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let mode = std::env::var("WIZARD_SOAK_MODE").unwrap_or_else(|_| "short".to_string());
    let default_seconds = match mode.as_str() {
        "short" => 15,
        "ci" => 30 * 60,
        "newsroom" => 60 * 60,
        "nightly" => 2 * 60 * 60,
        other => bail!("unsupported soak mode {other}; use short, ci, newsroom, or nightly"),
    };
    let total_seconds = std::env::var("WIZARD_SOAK_SECONDS")
        .ok()
        .map(|value| value.parse::<u64>())
        .transpose()
        .context("WIZARD_SOAK_SECONDS must be an integer")?
        .unwrap_or(default_seconds)
        .max(5);
    let root = evidence_root();
    std::fs::create_dir_all(root.join("soak"))?;
    write_configurations(&root)?;

    let hub = AvatarFrameHub::start(ProceduralWizardFrameSource::default());
    sleep(Duration::from_millis(150)).await;
    let actor_sample_tick_before = hub.snapshot().await.tick;
    let actor_sample_started = Instant::now();
    hub.newsroom_actor_sample()
        .await
        .context("initial actor sample build failed")?
        .decode_and_validate()
        .context("initial actor sample validation failed")?;
    let actor_sample_initialization_seconds = actor_sample_started.elapsed().as_secs_f64();
    let ticks_during_actor_sample_initialization = hub
        .snapshot()
        .await
        .tick
        .saturating_sub(actor_sample_tick_before);
    if ticks_during_actor_sample_initialization == 0 {
        bail!("actor sample initialization blocked runtime progress");
    }
    let started = Instant::now();
    let scenario_seconds = total_seconds as f64 / VIEWER_COUNTS.len() as f64;
    let mut scenarios = Vec::new();
    let mut newsroom = NewsroomSoakState {
        next_sequence: 1,
        actor_samples_validated: 1,
        ..NewsroomSoakState::default()
    };
    for viewers in VIEWER_COUNTS {
        scenarios.push(run_scenario(hub.clone(), viewers, scenario_seconds, &mut newsroom).await?);
    }
    let expected_semantic_pose_count = if mode == "newsroom" {
        NEWSROOM_POSE_COUNT
    } else {
        1
    };
    let semantic_coverage_passed =
        newsroom.semantic_poses_seen.len() >= expected_semantic_pose_count;
    let actor_sample_p50_seconds = percentile(&newsroom.actor_sample_seconds, 0.50);
    let actor_sample_p95_seconds = percentile(&newsroom.actor_sample_seconds, 0.95);
    let actor_sample_p99_seconds = percentile(&newsroom.actor_sample_seconds, 0.99);
    let newsroom = NewsroomSoakEvidence {
        cues_applied: newsroom.cues_applied,
        receipts_verified: newsroom.receipts_verified,
        correction_receipts: newsroom.correction_receipts,
        reduced_motion_receipts: newsroom.reduced_motion_receipts,
        stale_cues_rejected: newsroom.stale_cues_rejected,
        actor_samples_validated: newsroom.actor_samples_validated,
        actor_sample_initialization_seconds,
        ticks_during_actor_sample_initialization,
        actor_sample_p50_seconds,
        actor_sample_p95_seconds,
        actor_sample_p99_seconds,
        max_actor_sample_p99_seconds: MAX_ACTOR_SAMPLE_P99_SECONDS,
        reconnects: newsroom.reconnects,
        expected_semantic_pose_count,
        semantic_poses_seen: newsroom.semantic_poses_seen.into_iter().collect(),
        semantic_coverage_passed,
        generation_leaks: newsroom.generation_leaks,
    };
    let newsroom_passed = newsroom.cues_applied == newsroom.receipts_verified
        && newsroom.correction_receipts > 0
        && newsroom.reduced_motion_receipts > 0
        && newsroom.stale_cues_rejected == VIEWER_COUNTS.len() as u64
        && newsroom.actor_samples_validated > 1
        && newsroom.ticks_during_actor_sample_initialization > 0
        && newsroom.actor_sample_p99_seconds <= newsroom.max_actor_sample_p99_seconds
        && newsroom.reconnects > 0
        && newsroom.generation_leaks == 0
        && newsroom.semantic_coverage_passed;
    let passed = scenarios.iter().all(|scenario| scenario.passed) && newsroom_passed;
    let evidence = SoakEvidence {
        mode: mode.clone(),
        source_git_sha: source_git_sha()?,
        configured_total_seconds: total_seconds,
        actual_elapsed_seconds: started.elapsed().as_secs_f64(),
        broadcast_capacity: 16,
        scenarios,
        newsroom,
        passed,
    };
    write_json(&root.join(format!("soak/{mode}.json")), &evidence)?;
    write_json(&root.join("queue-and-pacing.json"), &evidence)?;
    write_json(
        &root.join("multiclient-fanout.json"),
        &json!({
            "scope": "single live hub with sequential viewer-count scenarios",
            "viewer_counts": VIEWER_COUNTS,
            "canonical_hash_mismatches": evidence.scenarios.iter().map(|scenario| scenario.canonical_hash_mismatches).sum::<u64>(),
            "sequence_gaps": evidence.scenarios.iter().map(|scenario| scenario.sequence_gaps).sum::<u64>(),
            "passed": passed,
        }),
    )?;
    println!(
        "{} soak complete in {:.1}s: {}",
        mode,
        evidence.actual_elapsed_seconds,
        if passed { "PASS" } else { "FAIL" }
    );
    if !passed {
        bail!("one or more soak scenarios failed");
    }
    Ok(())
}

fn source_git_sha() -> anyhow::Result<String> {
    if let Ok(sha) = std::env::var("WIZARD_EVIDENCE_GIT_SHA") {
        return validate_git_sha(sha);
    }
    let output = Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .context("failed to resolve soak source Git SHA")?;
    if !output.status.success() {
        bail!("git rev-parse HEAD failed with {}", output.status);
    }
    validate_git_sha(String::from_utf8(output.stdout)?.trim().to_string())
}

fn validate_git_sha(sha: String) -> anyhow::Result<String> {
    if sha.len() != 40 || !sha.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        bail!("soak source Git SHA must be 40 hexadecimal characters");
    }
    Ok(sha.to_ascii_lowercase())
}

async fn run_scenario(
    hub: std::sync::Arc<AvatarFrameHub>,
    viewers: usize,
    seconds: f64,
    newsroom: &mut NewsroomSoakState,
) -> anyhow::Result<ViewerScenario> {
    let mut receivers = (0..viewers).map(|_| hub.subscribe()).collect::<Vec<_>>();
    let start_snapshot = hub.snapshot().await;
    let start_diagnostics = hub.diagnostics().await;
    let start_sequence = start_diagnostics.frame_sequence.unwrap_or(0);
    let rss_start = rss_kb();
    let mut rss_peak = rss_start;
    let mut last_sequences = vec![None; viewers];
    let mut received = vec![0_u64; viewers];
    let mut sequence_gaps = 0_u64;
    let mut lag_events = 0_u64;
    let mut canonical_hash_mismatches = 0_u64;
    let mut canonical = BTreeMap::<u32, String>::new();
    let mut max_queue_depth = 0_usize;
    let started = Instant::now();
    let mut next_cue_at = 0.0_f64;
    let mut reconnected = false;
    while started.elapsed().as_secs_f64() < seconds {
        let elapsed = started.elapsed().as_secs_f64();
        if elapsed >= next_cue_at {
            apply_next_newsroom_cue(&hub, newsroom).await?;
            next_cue_at += 0.5;
        }
        if !reconnected && elapsed >= seconds / 2.0 {
            for (receiver, last_sequence) in receivers.iter_mut().zip(&mut last_sequences) {
                *receiver = hub.subscribe();
                *last_sequence = None;
                newsroom.reconnects += 1;
            }
            reconnected = true;
        }
        drain_receivers(
            &mut receivers,
            &mut last_sequences,
            &mut received,
            &mut sequence_gaps,
            &mut lag_events,
            &mut canonical_hash_mismatches,
            &mut canonical,
            &mut max_queue_depth,
        )?;
        rss_peak = max_option(rss_peak, rss_kb());
        sleep(Duration::from_millis(8)).await;
    }
    drain_receivers(
        &mut receivers,
        &mut last_sequences,
        &mut received,
        &mut sequence_gaps,
        &mut lag_events,
        &mut canonical_hash_mismatches,
        &mut canonical,
        &mut max_queue_depth,
    )?;
    let stale_sequence = newsroom.next_sequence.saturating_sub(1);
    let original_command =
        NewsCommand::ALL[((stale_sequence - 1) as usize) % NewsCommand::ALL.len()];
    let conflicting_command = if original_command == NewsCommand::Anchor {
        NewsCommand::Break
    } else {
        NewsCommand::Anchor
    };
    let stale_cue = newsroom_cue(stale_sequence, conflicting_command);
    match hub.apply_newsroom_cue(stale_cue).await {
        Err(NewsroomError::SequenceConflict | NewsroomError::StaleCue { .. }) => {
            newsroom.stale_cues_rejected += 1;
        }
        Err(error) => bail!("unexpected stale-cue error: {error}"),
        Ok(_) => bail!("stale newsroom cue was unexpectedly accepted"),
    }
    let actor_sample_started = Instant::now();
    hub.newsroom_actor_sample()
        .await
        .with_context(|| format!("actor sample build failed after {viewers}-viewer scenario"))?
        .decode_and_validate()
        .with_context(|| {
            format!("actor sample validation failed after {viewers}-viewer scenario")
        })?;
    let actor_sample_seconds = actor_sample_started.elapsed().as_secs_f64();
    newsroom.actor_samples_validated += 1;
    newsroom.actor_sample_seconds.push(actor_sample_seconds);
    let elapsed = started.elapsed().as_secs_f64();
    let end_snapshot = hub.snapshot().await;
    let end_diagnostics = hub.diagnostics().await;
    let end_sequence = end_diagnostics.frame_sequence.unwrap_or(start_sequence);
    let simulation_ticks = end_snapshot.tick.saturating_sub(start_snapshot.tick);
    let rendered_frames = end_sequence.saturating_sub(start_sequence);
    let expected_ticks = (elapsed * 60.0).floor() as u64;
    let expected_frames = (elapsed * 24.0).floor() as u32;
    let simulation_deadline_misses = expected_ticks.saturating_sub(simulation_ticks);
    let render_deadline_misses = expected_frames.saturating_sub(rendered_frames);
    let measured_simulation_hz = simulation_ticks as f64 / elapsed.max(0.001);
    let measured_render_fps = rendered_frames as f64 / elapsed.max(0.001);
    let rss_end = rss_kb();
    rss_peak = max_option(rss_peak, rss_end);
    let rss_peak_growth_kb = rss_start
        .zip(rss_peak)
        .map(|(start, peak)| peak.saturating_sub(start));
    let passed = (58.0..=62.0).contains(&measured_simulation_hz)
        && (22.0..=26.0).contains(&measured_render_fps)
        && simulation_deadline_misses <= 2
        && render_deadline_misses <= 2
        && sequence_gaps == 0
        && lag_events == 0
        && canonical_hash_mismatches == 0
        && max_queue_depth <= 16
        && rss_peak_growth_kb.is_some_and(|growth| growth <= MAX_RSS_GROWTH_KB);
    Ok(ViewerScenario {
        viewers,
        elapsed_seconds: elapsed,
        simulation_ticks,
        measured_simulation_hz,
        rendered_frames,
        measured_render_fps,
        simulation_deadline_misses,
        render_deadline_misses,
        viewer_received_frames: received,
        sequence_gaps,
        lag_events,
        canonical_hash_mismatches,
        max_receiver_queue_depth: max_queue_depth,
        rss_kb_start: rss_start,
        rss_kb_end: rss_end,
        rss_kb_peak: rss_peak,
        rss_peak_growth_kb,
        max_rss_growth_kb: MAX_RSS_GROWTH_KB,
        actor_sample_seconds,
        passed,
    })
}

async fn apply_next_newsroom_cue(
    hub: &std::sync::Arc<AvatarFrameHub>,
    newsroom: &mut NewsroomSoakState,
) -> anyhow::Result<()> {
    let sequence = newsroom.next_sequence;
    let command = NewsCommand::ALL[((sequence - 1) as usize) % NewsCommand::ALL.len()];
    let cue = newsroom_cue(sequence, command);
    let receipt = hub.apply_newsroom_cue(cue).await?;
    if receipt.sequence != sequence
        || receipt.generation != 1
        || receipt.performance.sequence != sequence
        || receipt.performance.generation != 1
        || receipt.duplicate
    {
        bail!("newsroom receipt identity mismatch at sequence {sequence}");
    }
    newsroom.next_sequence += 1;
    newsroom.cues_applied += 1;
    newsroom.receipts_verified += 1;
    newsroom.generation_leaks += u64::from(receipt.generation != 1);
    newsroom
        .semantic_poses_seen
        .insert(receipt.performance.semantic_pose_id);
    if command == NewsCommand::Correct {
        newsroom.correction_receipts += 1;
    }
    if receipt.performance.reduced_motion {
        newsroom.reduced_motion_receipts += 1;
    }
    Ok(())
}

fn newsroom_cue(sequence: u64, command: NewsCommand) -> NewsPerformanceCueV1 {
    let reduced_motion = sequence.is_multiple_of(7);
    let sensitivity = match command {
        NewsCommand::Correct => StorySensitivity::Correction,
        NewsCommand::Break | NewsCommand::Warn => StorySensitivity::Serious,
        _ => StorySensitivity::Normal,
    };
    NewsPerformanceCueV1 {
        schema_version: NEWSROOM_CUE_SCHEMA_VERSION.to_string(),
        cue_id: format!("soak-{sequence}-{}", command.wire_name()),
        sequence,
        program: NewsProgram::GeneralNews,
        command,
        target: None,
        count: (command == NewsCommand::Count).then_some((sequence % 3 + 1) as u8),
        intensity: UnitInterval::from_permille(300 + ((sequence * 53) % 701) as u16)
            .expect("bounded deterministic soak intensity"),
        sensitivity,
        start_ms: sequence.saturating_sub(1) * 500,
        duration_ms: 400,
        generation: 1,
        reduced_motion,
        speech_line_id: Some(format!("soak-line-{sequence}")),
        graphic_id: (command == NewsCommand::RevealGraphic)
            .then(|| format!("soak-graphic-{sequence}")),
        source_id: (command == NewsCommand::RevealSource)
            .then(|| format!("soak-source-{sequence}")),
        seed: Some(sequence),
    }
}

#[allow(clippy::too_many_arguments)]
fn drain_receivers(
    receivers: &mut [tokio::sync::broadcast::Receiver<
        std::sync::Arc<wizard_avatar_engine::hub::FramePacket>,
    >],
    last_sequences: &mut [Option<u32>],
    received: &mut [u64],
    sequence_gaps: &mut u64,
    lag_events: &mut u64,
    canonical_hash_mismatches: &mut u64,
    canonical: &mut BTreeMap<u32, String>,
    max_queue_depth: &mut usize,
) -> anyhow::Result<()> {
    for (viewer, receiver) in receivers.iter_mut().enumerate() {
        *max_queue_depth = (*max_queue_depth).max(receiver.len());
        loop {
            match receiver.try_recv() {
                Ok(packet) => {
                    if let Some(last) = last_sequences[viewer] {
                        if packet.sequence != last.wrapping_add(1) {
                            *sequence_gaps += 1;
                        }
                    }
                    last_sequences[viewer] = Some(packet.sequence);
                    received[viewer] += 1;
                    let hash = stable_hash64(&packet.encoded);
                    if canonical
                        .insert(packet.sequence, hash.clone())
                        .is_some_and(|expected| expected != hash)
                    {
                        *canonical_hash_mismatches += 1;
                    }
                }
                Err(TryRecvError::Empty) => break,
                Err(TryRecvError::Lagged(count)) => {
                    *lag_events += 1;
                    *sequence_gaps += count;
                }
                Err(TryRecvError::Closed) => bail!("hub broadcast closed during soak"),
            }
        }
    }
    Ok(())
}

fn rss_kb() -> Option<u64> {
    let output = Command::new("ps")
        .args(["-o", "rss=", "-p", &std::process::id().to_string()])
        .output()
        .ok()?;
    String::from_utf8(output.stdout).ok()?.trim().parse().ok()
}

fn max_option(a: Option<u64>, b: Option<u64>) -> Option<u64> {
    match (a, b) {
        (Some(a), Some(b)) => Some(a.max(b)),
        (Some(value), None) | (None, Some(value)) => Some(value),
        (None, None) => None,
    }
}

fn percentile(values: &[f64], quantile: f64) -> f64 {
    if values.is_empty() {
        return f64::INFINITY;
    }
    let mut sorted = values.to_vec();
    sorted.sort_by(f64::total_cmp);
    let rank = (quantile.clamp(0.0, 1.0) * sorted.len() as f64).ceil() as usize;
    sorted[rank.saturating_sub(1).min(sorted.len() - 1)]
}

fn write_configurations(root: &Path) -> anyhow::Result<()> {
    let configs = [
        SoakConfiguration {
            mode: "short",
            total_seconds: 15,
            seconds_per_viewer_count: 3.0,
            intended_use: "interactive verification",
        },
        SoakConfiguration {
            mode: "ci",
            total_seconds: 30 * 60,
            seconds_per_viewer_count: 6.0 * 60.0,
            intended_use: "30-minute CI soak",
        },
        SoakConfiguration {
            mode: "newsroom",
            total_seconds: 60 * 60,
            seconds_per_viewer_count: 12.0 * 60.0,
            intended_use: "60-minute newsroom release gate",
        },
        SoakConfiguration {
            mode: "nightly",
            total_seconds: 2 * 60 * 60,
            seconds_per_viewer_count: 24.0 * 60.0,
            intended_use: "two-hour nightly soak",
        },
    ];
    write_json(&root.join("soak/configurations.json"), &configs)
}

fn evidence_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../evidence/animation-quality/final")
}

fn write_json(path: &Path, value: &impl Serialize) -> anyhow::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(path, serde_json::to_vec_pretty(value)?)
        .with_context(|| format!("failed to write {}", path.display()))
}
