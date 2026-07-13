use anyhow::{bail, Context};
use futures_util::{SinkExt, StreamExt};
use serde::Serialize;
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::path::PathBuf;
use std::time::Instant;
use tokio::net::TcpListener;
use tokio::time::{timeout, Duration};
use tokio_tungstenite::connect_async;
use tokio_tungstenite::tungstenite::Message;
use wizard_avatar_engine::codec::{decode_frame, CELL_BYTES};
use wizard_avatar_engine::frame_source::{ProceduralWizardFrameSource, DEFAULT_COLS, DEFAULT_ROWS};
use wizard_avatar_engine::server;

#[derive(Clone, Debug)]
struct DemoStep {
    id: &'static str,
    description: &'static str,
    command_type: Option<&'static str>,
    payload: Value,
    full_seconds: f32,
    fast_seconds: f32,
}

#[derive(Clone, Debug, Serialize)]
struct StepEvidence {
    id: &'static str,
    description: &'static str,
    command_type: Option<&'static str>,
    frames: usize,
    first_frame_index: Option<u32>,
    last_frame_index: Option<u32>,
    average_wire_bytes: f32,
    average_raw_bytes: f32,
}

#[derive(Debug, Serialize)]
struct DemoEvidence {
    mode: &'static str,
    websocket_url: String,
    init: String,
    steps: Vec<StepEvidence>,
    total_frames: usize,
    elapsed_seconds: f32,
    observed_fps: f32,
    average_wire_bytes: f32,
    average_raw_bytes: f32,
    compression_ratio: f32,
    codec_tag_counts: BTreeMap<u8, usize>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let fast = std::env::var("WIZARD_DEMO_FAST").is_ok_and(|value| value != "0");
    let evidence = run_demo(fast).await?;
    write_evidence(&evidence)?;
    println!(
        "demo complete: {} frames, {:.1} fps observed, {:.3} wire/raw ratio",
        evidence.total_frames, evidence.observed_fps, evidence.compression_ratio
    );
    Ok(())
}

async fn run_demo(fast: bool) -> anyhow::Result<DemoEvidence> {
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .context("failed to bind demo listener")?;
    let addr = listener.local_addr().context("failed to read demo addr")?;
    let app = server::app(ProceduralWizardFrameSource::default());
    let server_task = tokio::spawn(async move {
        if let Err(error) = axum::serve(listener, app).await {
            eprintln!("demo server failed: {error}");
        }
    });

    let websocket_url = format!("ws://{addr}/ws/avatar/wizard?codec=adaptive");
    let (mut socket, _) = connect_async(&websocket_url)
        .await
        .with_context(|| format!("failed to connect to {websocket_url}"))?;

    let init = match timeout(Duration::from_secs(3), socket.next())
        .await
        .context("timed out waiting for INIT")?
        .context("websocket closed before INIT")??
    {
        Message::Text(text) => text,
        other => bail!("expected INIT text, got {other:?}"),
    };
    if !init.starts_with("INIT:") {
        bail!("unexpected init message: {init}");
    }

    let mut previous_frame: Option<Vec<u8>> = None;
    let started = Instant::now();
    let mut total_frames = 0usize;
    let mut total_wire_bytes = 0usize;
    let mut total_raw_bytes = 0usize;
    let mut tag_counts: BTreeMap<u8, usize> = BTreeMap::new();
    let mut step_evidence = Vec::new();

    for step in demo_steps() {
        if let Some(command_type) = step.command_type {
            let command = json!({
                "type": command_type,
                "payload": step.payload,
            });
            socket
                .send(Message::Text(command.to_string()))
                .await
                .with_context(|| format!("failed to send step {}", step.id))?;
        }
        let duration = if fast {
            step.fast_seconds
        } else {
            step.full_seconds
        };
        let frame_target = (duration * 24.0).ceil().max(1.0) as usize;
        let mut frames = 0usize;
        let mut step_wire = 0usize;
        let mut step_raw = 0usize;
        let mut first_index = None;
        let mut last_index = None;

        while frames < frame_target {
            let message = timeout(Duration::from_secs(3), socket.next())
                .await
                .with_context(|| format!("timed out waiting for frame in {}", step.id))?
                .context("websocket closed during demo")??;
            let Message::Binary(bytes) = message else {
                continue;
            };
            let tag = bytes.get(4).copied().unwrap_or_default();
            let (frame_index, decoded, _tag) =
                decode_frame(&bytes, previous_frame.as_deref(), CELL_BYTES)
                    .with_context(|| format!("failed to decode frame in {}", step.id))?;
            if decoded.len() != DEFAULT_COLS * DEFAULT_ROWS * CELL_BYTES {
                bail!("decoded frame had wrong length: {}", decoded.len());
            }
            if !frame_has_reference_avatar(&decoded) {
                bail!(
                    "decoded frame in {} did not contain expected reference-avatar signals",
                    step.id
                );
            }
            previous_frame = Some(decoded);
            first_index.get_or_insert(frame_index);
            last_index = Some(frame_index);
            frames += 1;
            total_frames += 1;
            step_wire += bytes.len();
            step_raw += DEFAULT_COLS * DEFAULT_ROWS * CELL_BYTES;
            total_wire_bytes += bytes.len();
            total_raw_bytes += DEFAULT_COLS * DEFAULT_ROWS * CELL_BYTES;
            *tag_counts.entry(tag).or_insert(0) += 1;
        }

        step_evidence.push(StepEvidence {
            id: step.id,
            description: step.description,
            command_type: step.command_type,
            frames,
            first_frame_index: first_index,
            last_frame_index: last_index,
            average_wire_bytes: step_wire as f32 / frames.max(1) as f32,
            average_raw_bytes: step_raw as f32 / frames.max(1) as f32,
        });
    }

    let elapsed_seconds = started.elapsed().as_secs_f32();
    let observed_fps = total_frames as f32 / elapsed_seconds.max(0.001);
    let evidence = DemoEvidence {
        mode: if fast { "fast" } else { "full" },
        websocket_url,
        init,
        steps: step_evidence,
        total_frames,
        elapsed_seconds,
        observed_fps,
        average_wire_bytes: total_wire_bytes as f32 / total_frames.max(1) as f32,
        average_raw_bytes: total_raw_bytes as f32 / total_frames.max(1) as f32,
        compression_ratio: total_wire_bytes as f32 / total_raw_bytes.max(1) as f32,
        codec_tag_counts: tag_counts,
    };

    let _ = socket.close(None).await;
    server_task.abort();
    Ok(evidence)
}

fn demo_steps() -> Vec<DemoStep> {
    vec![
        DemoStep {
            id: "01-load-environment",
            description: "Load fixed white environment and receive initial stream",
            command_type: None,
            payload: json!({}),
            full_seconds: 0.5,
            fast_seconds: 0.1,
        },
        DemoStep {
            id: "02-spawn-center",
            description: "Spawn wizard in the center",
            command_type: Some("reset"),
            payload: json!({}),
            full_seconds: 0.5,
            fast_seconds: 0.1,
        },
        DemoStep {
            id: "03-idle",
            description: "Idle for three seconds",
            command_type: Some("stop"),
            payload: json!({}),
            full_seconds: 3.0,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "04-blink-window",
            description: "Observe deterministic blink window",
            command_type: None,
            payload: json!({}),
            full_seconds: 0.25,
            fast_seconds: 0.1,
        },
        DemoStep {
            id: "05-happy",
            description: "Change to happy expression",
            command_type: Some("expression"),
            payload: json!({"expression": "happy"}),
            full_seconds: 0.5,
            fast_seconds: 0.1,
        },
        DemoStep {
            id: "06-speak",
            description: "Speak one test line",
            command_type: Some("speak"),
            payload: json!({"text": "A well tuned spell is mostly timing.", "duration_ms": 1600}),
            full_seconds: 1.6,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "07-walk-left",
            description: "Walk left",
            command_type: Some("walk_left"),
            payload: json!({"distance": 1.5}),
            full_seconds: 1.4,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "08-walk-right",
            description: "Turn and walk right",
            command_type: Some("walk_right"),
            payload: json!({"distance": 3.0}),
            full_seconds: 2.2,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "09-walk-away",
            description: "Walk away from camera",
            command_type: Some("walk_backward"),
            payload: json!({"distance": 1.4}),
            full_seconds: 1.4,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "10-walk-toward",
            description: "Walk toward camera",
            command_type: Some("walk_forward"),
            payload: json!({"distance": 1.4}),
            full_seconds: 1.4,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "11-walk-front-left",
            description: "Walk front-left",
            command_type: Some("move_relative"),
            payload: json!({"dx": -1.0, "dz": -0.9}),
            full_seconds: 1.4,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "12-walk-back-right",
            description: "Walk back-right",
            command_type: Some("move_relative"),
            payload: json!({"dx": 1.0, "dz": 0.9}),
            full_seconds: 1.4,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "13-clockwise-circle",
            description: "Walk one clockwise circle",
            command_type: Some("circle"),
            payload: json!({"center_x": 0.0, "center_z": 5.0, "radius": 1.2, "clockwise": true, "duration_seconds": 3.0}),
            full_seconds: 3.0,
            fast_seconds: 0.4,
        },
        DemoStep {
            id: "14-counterclockwise-circle",
            description: "Walk one counterclockwise circle",
            command_type: Some("circle"),
            payload: json!({"center_x": 0.0, "center_z": 5.0, "radius": 1.2, "clockwise": false, "duration_seconds": 3.0}),
            full_seconds: 3.0,
            fast_seconds: 0.4,
        },
        DemoStep {
            id: "15-figure-eight",
            description: "Walk a figure-eight",
            command_type: Some("figure_eight"),
            payload: json!({"center_x": 0.0, "center_z": 5.0, "radius": 1.1, "speed": 1.5}),
            full_seconds: 3.0,
            fast_seconds: 0.4,
        },
        DemoStep {
            id: "16-stop-center",
            description: "Stop in the center",
            command_type: Some("return_to_center"),
            payload: json!({"speed": 1.5}),
            full_seconds: 1.4,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "17-think",
            description: "Think",
            command_type: Some("action"),
            payload: json!({"action": "thinking", "duration_ms": 1200}),
            full_seconds: 1.2,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "18-point",
            description: "Point",
            command_type: Some("action"),
            payload: json!({"action": "pointing", "duration_ms": 1200}),
            full_seconds: 1.2,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "19-explain",
            description: "Explain",
            command_type: Some("action"),
            payload: json!({"action": "explaining", "duration_ms": 1200}),
            full_seconds: 1.2,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "20-cast-magic",
            description: "Cast magic",
            command_type: Some("action"),
            payload: json!({"action": "magic_cast", "duration_ms": 1400}),
            full_seconds: 1.4,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "21-react",
            description: "React",
            command_type: Some("action"),
            payload: json!({"action": "reaction", "duration_ms": 1000}),
            full_seconds: 1.0,
            fast_seconds: 0.2,
        },
        DemoStep {
            id: "22-neutral-idle",
            description: "Return to neutral idle",
            command_type: Some("expression"),
            payload: json!({"expression": "neutral"}),
            full_seconds: 0.5,
            fast_seconds: 0.1,
        },
        DemoStep {
            id: "23-final-idle",
            description: "Continue idling for ten seconds",
            command_type: Some("stop"),
            payload: json!({}),
            full_seconds: 10.0,
            fast_seconds: 0.3,
        },
    ]
}

fn frame_has_reference_avatar(cells: &[u8]) -> bool {
    let reference_fill_count = cells
        .chunks_exact(CELL_BYTES)
        .filter(|cell| cell[0] == b'#')
        .count();
    let has_blue = cells
        .chunks_exact(CELL_BYTES)
        .any(|cell| cell[1] < 40 && cell[2] > 90 && cell[3] > 140);
    let has_warm_or_rainbow = cells
        .chunks_exact(CELL_BYTES)
        .any(|cell| cell[1] > 180 && cell[2] > 80 && cell[3] < 80);
    reference_fill_count > 8_000 && has_blue && has_warm_or_rainbow
}

fn write_evidence(evidence: &DemoEvidence) -> anyhow::Result<()> {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../evidence/wizard/rust-demo");
    std::fs::create_dir_all(&root)
        .with_context(|| format!("failed to create {}", root.display()))?;
    let json_path = root.join("demo-summary.json");
    let md_path = root.join("README.md");
    let mode_json_path = root.join(format!("demo-summary-{}.json", evidence.mode));
    let mode_md_path = root.join(format!("README-{}.md", evidence.mode));
    let json = serde_json::to_vec_pretty(evidence)?;
    let markdown = render_markdown(evidence);
    std::fs::write(&json_path, &json)
        .with_context(|| format!("failed to write {}", json_path.display()))?;
    std::fs::write(&md_path, &markdown)
        .with_context(|| format!("failed to write {}", md_path.display()))?;
    std::fs::write(&mode_json_path, &json)
        .with_context(|| format!("failed to write {}", mode_json_path.display()))?;
    std::fs::write(&mode_md_path, &markdown)
        .with_context(|| format!("failed to write {}", mode_md_path.display()))?;
    println!("wrote {}", json_path.display());
    println!("wrote {}", md_path.display());
    println!("wrote {}", mode_json_path.display());
    println!("wrote {}", mode_md_path.display());
    Ok(())
}

fn render_markdown(evidence: &DemoEvidence) -> String {
    let mut out = String::new();
    out.push_str("# Rust Wizard Avatar Demo Evidence\n\n");
    out.push_str(&format!("- mode: `{}`\n", evidence.mode));
    out.push_str(&format!("- websocket: `{}`\n", evidence.websocket_url));
    out.push_str(&format!("- init: `{}`\n", evidence.init));
    out.push_str(&format!("- total frames: `{}`\n", evidence.total_frames));
    out.push_str(&format!("- observed fps: `{:.2}`\n", evidence.observed_fps));
    out.push_str(&format!(
        "- average wire/raw ratio: `{:.4}`\n\n",
        evidence.compression_ratio
    ));
    out.push_str("## Codec Tags\n\n");
    for (tag, count) in &evidence.codec_tag_counts {
        out.push_str(&format!("- tag `{tag}`: `{count}` frames\n"));
    }
    out.push_str("\n## Steps\n\n");
    for step in &evidence.steps {
        out.push_str(&format!(
            "- `{}`: {} frames, sequence `{:?}` to `{:?}` - {}\n",
            step.id, step.frames, step.first_frame_index, step.last_frame_index, step.description
        ));
    }
    out
}
