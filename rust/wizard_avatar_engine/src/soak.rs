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

const VIEWER_COUNTS: [usize; 5] = [0, 1, 2, 4, 8];

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
    passed: bool,
}

#[derive(Clone, Debug, Serialize)]
struct SoakEvidence {
    mode: String,
    configured_total_seconds: u64,
    actual_elapsed_seconds: f64,
    broadcast_capacity: usize,
    scenarios: Vec<ViewerScenario>,
    passed: bool,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let mode = std::env::var("WIZARD_SOAK_MODE").unwrap_or_else(|_| "short".to_string());
    let default_seconds = match mode.as_str() {
        "short" => 15,
        "ci" => 30 * 60,
        "nightly" => 2 * 60 * 60,
        other => bail!("unsupported soak mode {other}; use short, ci, or nightly"),
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
    let started = Instant::now();
    let scenario_seconds = total_seconds as f64 / VIEWER_COUNTS.len() as f64;
    let mut scenarios = Vec::new();
    for viewers in VIEWER_COUNTS {
        scenarios.push(run_scenario(hub.clone(), viewers, scenario_seconds).await?);
    }
    let passed = scenarios.iter().all(|scenario| scenario.passed);
    let evidence = SoakEvidence {
        mode: mode.clone(),
        configured_total_seconds: total_seconds,
        actual_elapsed_seconds: started.elapsed().as_secs_f64(),
        broadcast_capacity: 16,
        scenarios,
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

async fn run_scenario(
    hub: std::sync::Arc<AvatarFrameHub>,
    viewers: usize,
    seconds: f64,
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
    while started.elapsed().as_secs_f64() < seconds {
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
    let passed = (58.0..=62.0).contains(&measured_simulation_hz)
        && (22.0..=26.0).contains(&measured_render_fps)
        && simulation_deadline_misses <= 2
        && render_deadline_misses <= 2
        && sequence_gaps == 0
        && lag_events == 0
        && canonical_hash_mismatches == 0
        && max_queue_depth <= 16;
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
        passed,
    })
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
