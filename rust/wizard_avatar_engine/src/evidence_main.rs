use anyhow::{bail, Context};
use base64::engine::general_purpose::STANDARD as BASE64;
use base64::Engine;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::fs::{File, OpenOptions};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use wizard_avatar_engine::codec::{decode_frame, encode_frame, CodecTag, CELL_BYTES};
use wizard_avatar_engine::controller::{WizardCommand, SIMULATION_HZ};
use wizard_avatar_engine::evidence::{
    cell_rgb_bytes, crc32, stable_hash64, ExactRenderClock, ReplayCommandSpec, ReplayManifest,
    ReplayTransition, EVIDENCE_RENDER_HZ, EVIDENCE_SCHEMA_VERSION, EVIDENCE_SIMULATION_HZ,
};
use wizard_avatar_engine::frame_source::{DEFAULT_COLS, DEFAULT_ROWS};
use wizard_avatar_engine::pose::{
    analyze_pose_topology, sample_pose, AnchorId, PoseLibrary, PoseSample, PoseTopologyMetrics,
};
use wizard_avatar_engine::projection::project_world_to_screen;
use wizard_avatar_engine::projection::{ProjectedPoseContext, ProjectionHistory};
use wizard_avatar_engine::quality::{
    FrameQualityFailure, FrameQualityReport, FrameQualitySnapshot, FrameQualityThresholds,
};
use wizard_avatar_engine::renderer::{build_background, render_stage};
use wizard_avatar_engine::runtime::AvatarRuntime;
use wizard_avatar_engine::state::{PlantedFoot, ScreenPoint, WizardState};

const PRE_TICKS: u32 = 30;
const POST_TICKS: u32 = 40;
const VECTOR_FRAMES_PER_CATEGORY: u32 = 12;

#[derive(Clone, Debug, Serialize)]
struct StageMetrics {
    contact_root: (i32, i32),
    visual_root: (i32, i32),
    left_foot: (i32, i32),
    right_foot: (i32, i32),
    left_wrist: (i32, i32),
    right_wrist: (i32, i32),
    staff_hand: (i32, i32),
    staff_top: (i32, i32),
    face: (i32, i32),
    scale: f32,
    scale_level: i16,
    contact_correction: (i32, i32),
}

#[derive(Clone, Debug, Serialize)]
struct FrameEvidence {
    category: String,
    transition_id: String,
    ledger_transition: String,
    boundary_side: &'static str,
    category_sequence: u32,
    runtime_tick: u64,
    presentation_micros: u64,
    state: WizardState,
    metrics: StageMetrics,
    topology: PoseTopologyMetrics,
    source_hash64: String,
    source_crc32: String,
    semantic_hash64: String,
    decoded_hash64: String,
    codec_tag: u8,
    encoded_bytes: usize,
    raw_bytes: usize,
}

#[derive(Clone, Debug, Serialize)]
struct BoundaryMetric {
    transition_id: String,
    ledger_transition: String,
    category: String,
    window_start_tick: u64,
    window_end_tick: u64,
    consecutive_frame_pairs: usize,
    root_jump_cells: f32,
    planted_foot_jump_cells: f32,
    staff_hand_error_cells: f32,
    face_anchor_jump_cells: f32,
    scale_jump: f32,
    mask_writes: u64,
    unexpected_mask_writes: u64,
    source_decoded_equal: bool,
    presented_sequence_strictly_increasing: bool,
    minimum_occupancy_ratio: f32,
    maximum_components: usize,
    maximum_component_step: usize,
    horizontal_seam_frames: usize,
    vertical_crack_frames: usize,
    staff_disconnected_frames: usize,
    semantic_quality_failures: Vec<FrameQualityFailure>,
    passed: bool,
}

#[derive(Clone, Debug)]
struct TemporalFrame {
    runtime_tick: u64,
    category_sequence: u32,
    state: WizardState,
    presented_pose_id: String,
    metrics: StageMetrics,
    topology: PoseTopologyMetrics,
    quality: FrameQualitySnapshot,
    cells: Vec<u8>,
    decoded_equal: bool,
}

#[derive(Clone, Debug, Serialize)]
struct CodecVector {
    group: String,
    sequence: u32,
    cols: usize,
    rows: usize,
    cell_bytes: usize,
    tag: u8,
    source_base64: String,
    encoded_base64: String,
    source_hash64: String,
    source_crc32: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct RunSummary {
    run_id: String,
    transitions: usize,
    frames: u64,
    semantic_stream_hash64: String,
    raw_frame_stream_hash64: String,
    category_frame_counts: BTreeMap<String, u32>,
    all_boundaries_passed: bool,
}

#[derive(Clone, Debug, Serialize)]
struct ReplayParity {
    deterministic: bool,
    manifest_hash64: String,
    run_1_semantic_hash64: String,
    run_2_semantic_hash64: String,
    run_1_raw_hash64: String,
    run_2_raw_hash64: String,
    frame_count_equal: bool,
}

#[derive(Default)]
struct StreamHasher(u64);

impl StreamHasher {
    fn new() -> Self {
        Self(0xcbf2_9ce4_8422_2325)
    }

    fn update(&mut self, bytes: &[u8]) {
        for byte in bytes {
            self.0 ^= u64::from(*byte);
            self.0 = self.0.wrapping_mul(0x0000_0100_0000_01b3);
        }
    }

    fn finish(&self) -> String {
        format!("{:016x}", self.0)
    }
}

struct RunOutputs {
    summary: RunSummary,
    boundaries: Vec<BoundaryMetric>,
    vectors: Vec<CodecVector>,
}

struct CategoryOutput {
    raw: BufWriter<File>,
    frame_count: u32,
    vector_count: u32,
}

fn main() -> anyhow::Result<()> {
    if SIMULATION_HZ as u32 != EVIDENCE_SIMULATION_HZ {
        bail!("runtime simulation rate no longer matches evidence contract");
    }
    let root = evidence_root();
    create_layout(&root)?;
    if std::env::args().any(|argument| argument == "--check-integrity") {
        check_integrity_manifest(&root)?;
        println!(
            "verified {}",
            root.join("evidence-integrity.json").display()
        );
        return Ok(());
    }
    if std::env::args().any(|argument| argument == "--integrity-only") {
        write_integrity_manifest(&root)?;
        println!(
            "refreshed {}",
            root.join("evidence-integrity.json").display()
        );
        return Ok(());
    }
    reset_frame_sequences(&root)?;
    let manifest = replay_manifest();
    let manifest_bytes = serde_json::to_vec_pretty(&manifest)?;
    write_json_bytes(&root.join("replay/replay-manifest.json"), &manifest_bytes)?;

    let run_1 = run_replay(&manifest, &root, "run-1", true)?;
    let serialized: ReplayManifest = serde_json::from_slice(&manifest_bytes)?;
    let run_2 = run_replay(&serialized, &root, "run-2", false)?;
    let deterministic = run_1.summary.semantic_stream_hash64
        == run_2.summary.semantic_stream_hash64
        && run_1.summary.raw_frame_stream_hash64 == run_2.summary.raw_frame_stream_hash64
        && run_1.summary.frames == run_2.summary.frames;
    let parity = ReplayParity {
        deterministic,
        manifest_hash64: stable_hash64(&manifest_bytes),
        run_1_semantic_hash64: run_1.summary.semantic_stream_hash64.clone(),
        run_2_semantic_hash64: run_2.summary.semantic_stream_hash64.clone(),
        run_1_raw_hash64: run_1.summary.raw_frame_stream_hash64.clone(),
        run_2_raw_hash64: run_2.summary.raw_frame_stream_hash64.clone(),
        frame_count_equal: run_1.summary.frames == run_2.summary.frames,
    };
    if !deterministic {
        bail!("offline replay hashes diverged");
    }

    write_json(&root.join("replay/run-1-summary.json"), &run_1.summary)?;
    write_json(&root.join("replay/run-2-summary.json"), &run_2.summary)?;
    write_json(&root.join("replay/deterministic-parity.json"), &parity)?;
    write_json(&root.join("transition-metrics.json"), &run_1.boundaries)?;
    write_json(
        &root.join("hashes/codec-vectors.json"),
        &json!({
            "schema_version": 1,
            "vectors": run_1.vectors,
        }),
    )?;
    write_json(
        &root.join("browser-console.json"),
        &json!({
            "scope": "module-level only",
            "real_browser_control_available": false,
            "console_errors": Value::Null,
            "claim": "No real-browser console capture was performed in this pass."
        }),
    )?;
    run_browser_parity(&root)?;
    write_integrity_manifest(&root)?;
    println!(
        "evidence complete: {} transitions, {} frames, deterministic hash {}",
        run_1.summary.transitions, run_1.summary.frames, run_1.summary.raw_frame_stream_hash64
    );
    Ok(())
}

fn run_replay(
    manifest: &ReplayManifest,
    root: &Path,
    run_id: &str,
    emit: bool,
) -> anyhow::Result<RunOutputs> {
    let mut semantic_stream = StreamHasher::new();
    let mut raw_stream = StreamHasher::new();
    let mut boundaries = Vec::new();
    let mut vectors = Vec::new();
    let mut categories = BTreeMap::<String, CategoryOutput>::new();
    let mut category_frame_counts = BTreeMap::<String, u32>::new();
    let mut state_log = emit
        .then(|| create_writer(&root.join("logs/state-frames.ndjson")))
        .transpose()?;
    let mut event_log = emit
        .then(|| create_writer(&root.join("logs/semantic-events.ndjson")))
        .transpose()?;

    for transition in &manifest.transitions {
        let mut runtime = AvatarRuntime::default();
        let mut projection = ProjectionHistory::default();
        let mut temporal_frames = Vec::with_capacity(28);
        let mut previous_cells: Option<Vec<u8>> = None;
        let mut previous_decoded: Option<Vec<u8>> = None;
        let category_sequence = category_frame_counts
            .entry(transition.category.clone())
            .or_default();
        if emit && !categories.contains_key(&transition.category) {
            let raw_path = root.join(format!("tmp/{}.rgb", transition.category));
            categories.insert(
                transition.category.clone(),
                CategoryOutput {
                    raw: create_writer(&raw_path)?,
                    frame_count: 0,
                    vector_count: 0,
                },
            );
        }
        apply_commands(&mut runtime, &transition.setup)?;
        if let Some(log) = event_log.as_mut() {
            write_ndjson(
                log,
                &json!({
                    "run_id": run_id,
                    "transition_id": transition.id,
                    "category": transition.category,
                    "phase": "setup",
                    "runtime_tick": runtime.tick(),
                    "commands": transition.setup,
                }),
            )?;
        }
        run_ticks(
            PRE_TICKS,
            "before",
            transition,
            &mut runtime,
            &mut projection,
            &mut previous_cells,
            &mut previous_decoded,
            category_sequence,
            categories.get_mut(&transition.category),
            state_log.as_mut(),
            &mut semantic_stream,
            &mut raw_stream,
            &mut vectors,
            &mut temporal_frames,
        )?;
        apply_commands(&mut runtime, &transition.boundary)?;
        if transition.force_full_at_boundary {
            previous_cells = None;
            previous_decoded = None;
        }
        if let Some(log) = event_log.as_mut() {
            write_ndjson(
                log,
                &json!({
                    "run_id": run_id,
                    "transition_id": transition.id,
                    "ledger_transition": transition.ledger_transition,
                    "category": transition.category,
                    "phase": "boundary",
                    "runtime_tick": runtime.tick(),
                    "commands": transition.boundary,
                    "force_full": transition.force_full_at_boundary,
                }),
            )?;
        }
        run_ticks(
            POST_TICKS,
            "after",
            transition,
            &mut runtime,
            &mut projection,
            &mut previous_cells,
            &mut previous_decoded,
            category_sequence,
            categories.get_mut(&transition.category),
            state_log.as_mut(),
            &mut semantic_stream,
            &mut raw_stream,
            &mut vectors,
            &mut temporal_frames,
        )?;
        boundaries.push(transition_metric(transition, &temporal_frames));
    }

    if let Some(mut log) = state_log {
        log.flush()?;
    }
    if let Some(mut log) = event_log {
        log.flush()?;
    }
    if emit {
        for (category, mut output) in categories {
            output.raw.flush()?;
            category_frame_counts.insert(category, output.frame_count);
        }
        render_media(root, &category_frame_counts)?;
        add_synthetic_codec_vectors(&mut vectors)?;
        write_rust_hash_log(root, &vectors)?;
    }

    let summary = RunSummary {
        run_id: run_id.to_string(),
        transitions: manifest.transitions.len(),
        frames: u64::from(category_frame_counts.values().sum::<u32>()),
        semantic_stream_hash64: semantic_stream.finish(),
        raw_frame_stream_hash64: raw_stream.finish(),
        category_frame_counts,
        all_boundaries_passed: boundaries.iter().all(|metric| metric.passed),
    };
    if !summary.all_boundaries_passed {
        if emit {
            write_json(&root.join("transition-metrics.json"), &boundaries)?;
        }
        let failed = boundaries
            .iter()
            .filter(|metric| !metric.passed)
            .collect::<Vec<_>>();
        bail!("transition metrics failed: {failed:#?}");
    }
    Ok(RunOutputs {
        summary,
        boundaries,
        vectors,
    })
}

#[allow(clippy::too_many_arguments)]
fn run_ticks(
    ticks: u32,
    boundary_side: &'static str,
    transition: &ReplayTransition,
    runtime: &mut AvatarRuntime,
    projection: &mut ProjectionHistory,
    previous_cells: &mut Option<Vec<u8>>,
    previous_decoded: &mut Option<Vec<u8>>,
    category_sequence: &mut u32,
    mut category_output: Option<&mut CategoryOutput>,
    mut state_log: Option<&mut BufWriter<File>>,
    semantic_stream: &mut StreamHasher,
    raw_stream: &mut StreamHasher,
    vectors: &mut Vec<CodecVector>,
    temporal_frames: &mut Vec<TemporalFrame>,
) -> anyhow::Result<()> {
    let mut clock = ExactRenderClock::new(EVIDENCE_SIMULATION_HZ, EVIDENCE_RENDER_HZ);
    for _ in 0..ticks {
        runtime.step_tick();
        if !clock.simulation_tick() {
            continue;
        }
        let state = runtime.current_state().clone();
        let (cells, metrics, topology, pose) = render_cells(&state, projection)?;
        let quality = FrameQualitySnapshot::from_pose(
            transition.id.clone(),
            pose.pose_id.clone(),
            u64::from(*category_sequence),
            &pose,
        )
        .map_err(anyhow::Error::msg)?;
        let encoded = encode_frame(
            &cells,
            previous_cells.as_deref(),
            *category_sequence,
            CELL_BYTES,
        )?;
        let (_, decoded, tag) =
            decode_frame(&encoded.message, previous_decoded.as_deref(), CELL_BYTES)?;
        if decoded != cells {
            bail!("Rust adaptive decode diverged at sequence {category_sequence}");
        }
        let state_bytes = serde_json::to_vec(&state)?;
        let source_hash = stable_hash64(&cells);
        let semantic_hash = stable_hash64(&state_bytes);
        semantic_stream.update(semantic_hash.as_bytes());
        raw_stream.update(&cells);
        let evidence = FrameEvidence {
            category: transition.category.clone(),
            transition_id: transition.id.clone(),
            ledger_transition: transition.ledger_transition.clone(),
            boundary_side,
            category_sequence: *category_sequence,
            runtime_tick: runtime.tick(),
            presentation_micros: u64::from(*category_sequence) * 1_000_000
                / u64::from(EVIDENCE_RENDER_HZ),
            state,
            metrics: metrics.clone(),
            topology,
            source_hash64: source_hash.clone(),
            source_crc32: crc32(&cells),
            semantic_hash64: semantic_hash,
            decoded_hash64: stable_hash64(&decoded),
            codec_tag: tag as u8,
            encoded_bytes: encoded.message.len(),
            raw_bytes: cells.len(),
        };
        temporal_frames.push(TemporalFrame {
            runtime_tick: evidence.runtime_tick,
            category_sequence: evidence.category_sequence,
            state: evidence.state.clone(),
            presented_pose_id: pose.pose_id,
            metrics,
            topology,
            quality,
            cells: cells.clone(),
            decoded_equal: decoded == cells,
        });
        if let Some(log) = state_log.as_deref_mut() {
            write_ndjson(log, &evidence)?;
        }
        if let Some(output) = category_output.as_deref_mut() {
            output.raw.write_all(&cell_rgb_bytes(&cells))?;
            output.frame_count += 1;
            if output.vector_count < VECTOR_FRAMES_PER_CATEGORY {
                vectors.push(codec_vector(
                    transition.category.clone(),
                    *category_sequence,
                    DEFAULT_COLS,
                    DEFAULT_ROWS,
                    tag,
                    &cells,
                    &encoded.message,
                ));
                output.vector_count += 1;
            }
        }
        *previous_cells = Some(encoded.shown_frame);
        *previous_decoded = Some(decoded);
        *category_sequence += 1;
    }
    Ok(())
}

fn render_cells(
    state: &WizardState,
    projection: &mut ProjectionHistory,
) -> anyhow::Result<(Vec<u8>, StageMetrics, PoseTopologyMetrics, PoseSample)> {
    let mut sampled = state.clone();
    let library = PoseLibrary::reference().map_err(anyhow::Error::msg)?;
    if sampled
        .pose_id
        .as_deref()
        .is_some_and(|pose_id| library.for_id(pose_id).is_none())
    {
        // This binary preserves the retired cell-renderer evidence contract. New
        // production-alpha poses are verified by pixelgraph_runtime_evidence;
        // use the directional cell fallback here instead of asking the old
        // procedural library to interpret a graph-only semantic ID.
        sampled.pose_id = None;
        sampled.previous_pose_id = None;
        sampled.pose_blend = 1.0;
        sampled.pose_handoff = true;
        sampled.pose_clip_id = None;
        sampled.pose_clip_step = None;
    }
    let pose = sample_pose(&sampled).map_err(anyhow::Error::msg)?;
    let context = projection.project(state, &pose, DEFAULT_COLS, DEFAULT_ROWS);
    sampled.screen_position = ScreenPoint {
        x: context.quantized_root.0 as f32,
        y: context.quantized_root.1 as f32,
    };
    sampled.display_scale = context.quantized_scale;
    let cells = render_stage(&sampled, DEFAULT_COLS, DEFAULT_ROWS).to_frame_bytes();
    let topology = analyze_pose_topology(&pose);
    Ok((cells, stage_metrics(&pose, context), topology, pose))
}

fn stage_metrics(pose: &PoseSample, context: ProjectedPoseContext) -> StageMetrics {
    StageMetrics {
        contact_root: context.quantized_root,
        visual_root: projected_anchor(pose, context, AnchorId::Root),
        left_foot: projected_anchor(pose, context, AnchorId::LeftFoot),
        right_foot: projected_anchor(pose, context, AnchorId::RightFoot),
        left_wrist: projected_anchor(pose, context, AnchorId::LeftWrist),
        right_wrist: projected_anchor(pose, context, AnchorId::RightWrist),
        staff_hand: projected_anchor(pose, context, AnchorId::StaffHand),
        staff_top: projected_anchor(pose, context, AnchorId::StaffTop),
        face: projected_anchor(pose, context, AnchorId::Head),
        scale: context.quantized_scale,
        scale_level: context.scale_level,
        contact_correction: context.foot_correction,
    }
}

fn projected_anchor(
    pose: &PoseSample,
    context: ProjectedPoseContext,
    anchor: AnchorId,
) -> (i32, i32) {
    let point = pose.anchors[&anchor];
    (
        (context.quantized_root.0 as f32 + (point.x - pose.root.0 as f32) * context.quantized_scale)
            .round() as i32,
        (context.quantized_root.1 as f32 + (point.y - pose.root.1 as f32) * context.quantized_scale)
            .round() as i32,
    )
}

fn transition_metric(transition: &ReplayTransition, frames: &[TemporalFrame]) -> BoundaryMetric {
    let background = build_background(DEFAULT_COLS, DEFAULT_ROWS).to_frame_bytes();
    let mut root_jump = 0.0_f32;
    let mut planted_jump = 0.0_f32;
    let mut staff_error = 0.0_f32;
    let mut face_jump = 0.0_f32;
    let mut scale_jump = 0.0_f32;
    let mut mask_writes = 0_u64;
    let mut unexpected_mask_writes = 0_u64;
    let mut source_decoded_equal = frames.iter().all(|frame| frame.decoded_equal);
    let mut presented_sequence_strictly_increasing = true;
    let mut minimum_occupancy_ratio = 1.0_f32;
    let mut maximum_component_step = 0_usize;

    for pair in frames.windows(2) {
        let before = &pair[0];
        let after = &pair[1];
        let actual_root_step =
            point_difference(after.metrics.contact_root, before.metrics.contact_root);
        let expected_root_step = point_difference(
            uncorrected_root(&after.state),
            uncorrected_root(&before.state),
        );
        root_jump = root_jump.max(chebyshev_distance(actual_root_step, expected_root_step));
        let same_presented_pose = before.presented_pose_id == after.presented_pose_id;
        if same_presented_pose && before.state.planted_foot == after.state.planted_foot {
            let foot_jump = match after.state.planted_foot {
                PlantedFoot::Left => {
                    chebyshev_distance(before.metrics.left_foot, after.metrics.left_foot)
                }
                PlantedFoot::Right => {
                    chebyshev_distance(before.metrics.right_foot, after.metrics.right_foot)
                }
                PlantedFoot::Both => {
                    chebyshev_distance(before.metrics.left_foot, after.metrics.left_foot).max(
                        chebyshev_distance(before.metrics.right_foot, after.metrics.right_foot),
                    )
                }
                PlantedFoot::None => 0.0,
            };
            planted_jump = planted_jump.max(foot_jump);
        }
        if same_presented_pose {
            staff_error = staff_error.max(chebyshev_distance(
                staff_grip_offset(&before.metrics),
                staff_grip_offset(&after.metrics),
            ));
            face_jump = face_jump.max(chebyshev_distance(
                point_difference(before.metrics.face, before.metrics.contact_root),
                point_difference(after.metrics.face, after.metrics.contact_root),
            ));
        }
        scale_jump = scale_jump.max((after.metrics.scale - before.metrics.scale).abs());
        presented_sequence_strictly_increasing &=
            after.category_sequence > before.category_sequence;
        source_decoded_equal &= before.decoded_equal && after.decoded_equal;
        if same_presented_pose {
            let minimum = after
                .topology
                .occupied_cells
                .min(before.topology.occupied_cells) as f32;
            let maximum = after
                .topology
                .occupied_cells
                .max(before.topology.occupied_cells)
                .max(1) as f32;
            minimum_occupancy_ratio = minimum_occupancy_ratio.min(minimum / maximum);
            maximum_component_step = maximum_component_step.max(
                after
                    .topology
                    .unexpected_fragment_components
                    .abs_diff(before.topology.unexpected_fragment_components),
            );
        }

        for ((before_cell, after_cell), background_cell) in before
            .cells
            .chunks_exact(CELL_BYTES)
            .zip(after.cells.chunks_exact(CELL_BYTES))
            .zip(background.chunks_exact(CELL_BYTES))
        {
            if before_cell == after_cell {
                continue;
            }
            let dynamic = before_cell != background_cell || after_cell != background_cell;
            if dynamic {
                mask_writes += 1;
            } else {
                unexpected_mask_writes += 1;
            }
        }
    }

    let horizontal_seam_frames = frames
        .iter()
        .filter(|frame| frame.topology.horizontal_seam_rows > 0)
        .count();
    let vertical_crack_frames = frames
        .iter()
        .filter(|frame| frame.topology.vertical_crack_cells > 0)
        .count();
    let staff_disconnected_frames = frames
        .iter()
        .filter(|frame| {
            frame.topology.staff_components != 1 || frame.topology.staff_scanline_gaps > 0
        })
        .count();
    let maximum_components = frames
        .iter()
        .map(|frame| frame.topology.connected_components)
        .max()
        .unwrap_or(0);
    let semantic_quality = FrameQualityReport::inspect_sequence(
        &frames
            .iter()
            .map(|frame| frame.quality.clone())
            .collect::<Vec<_>>(),
        FrameQualityThresholds {
            maximum_face_anchor_step: 4.0,
            maximum_staff_anchor_step: 6.0,
            maximum_free_foot_step: 8.0,
            ..FrameQualityThresholds::default()
        },
    );
    let passed = frames.len() == 28
        && root_jump <= 1.0
        && planted_jump <= 4.0
        && scale_jump <= 0.125
        && unexpected_mask_writes == 0
        && source_decoded_equal
        && presented_sequence_strictly_increasing
        && minimum_occupancy_ratio >= 0.75
        && maximum_component_step <= 2
        && horizontal_seam_frames == 0
        && vertical_crack_frames == 0
        && staff_disconnected_frames == 0
        && semantic_quality.passed();
    BoundaryMetric {
        transition_id: transition.id.clone(),
        ledger_transition: transition.ledger_transition.clone(),
        category: transition.category.clone(),
        window_start_tick: frames.first().map(|frame| frame.runtime_tick).unwrap_or(0),
        window_end_tick: frames.last().map(|frame| frame.runtime_tick).unwrap_or(0),
        consecutive_frame_pairs: frames.len().saturating_sub(1),
        root_jump_cells: root_jump,
        planted_foot_jump_cells: planted_jump,
        staff_hand_error_cells: staff_error,
        face_anchor_jump_cells: face_jump,
        scale_jump,
        mask_writes,
        unexpected_mask_writes,
        source_decoded_equal,
        presented_sequence_strictly_increasing,
        minimum_occupancy_ratio,
        maximum_components,
        maximum_component_step,
        horizontal_seam_frames,
        vertical_crack_frames,
        staff_disconnected_frames,
        semantic_quality_failures: semantic_quality.failures,
        passed,
    }
}

fn point_difference(a: (i32, i32), b: (i32, i32)) -> (i32, i32) {
    (a.0 - b.0, a.1 - b.1)
}

fn uncorrected_root(state: &WizardState) -> (i32, i32) {
    let (x, y, _) = project_world_to_screen(
        state.world_position.x,
        state.world_position.z,
        DEFAULT_COLS,
        DEFAULT_ROWS,
    );
    (x.round() as i32, y.round() as i32)
}

fn staff_grip_offset(metrics: &StageMetrics) -> (i32, i32) {
    let left = point_difference(metrics.staff_hand, metrics.left_wrist);
    let right = point_difference(metrics.staff_hand, metrics.right_wrist);
    if chebyshev_distance(left, (0, 0)) <= chebyshev_distance(right, (0, 0)) {
        left
    } else {
        right
    }
}

fn chebyshev_distance(a: (i32, i32), b: (i32, i32)) -> f32 {
    (a.0 - b.0).abs().max((a.1 - b.1).abs()) as f32
}

fn apply_commands(
    runtime: &mut AvatarRuntime,
    commands: &[ReplayCommandSpec],
) -> anyhow::Result<()> {
    for command in commands {
        let result = runtime.apply_command(WizardCommand::new(
            command.command_type.clone(),
            command.payload.clone(),
        ));
        if !result.ok {
            bail!(
                "command {} failed in replay: {}",
                command.command_type,
                result.message
            );
        }
    }
    Ok(())
}

fn codec_vector(
    group: String,
    sequence: u32,
    cols: usize,
    rows: usize,
    tag: CodecTag,
    source: &[u8],
    encoded: &[u8],
) -> CodecVector {
    CodecVector {
        group,
        sequence,
        cols,
        rows,
        cell_bytes: CELL_BYTES,
        tag: tag as u8,
        source_base64: BASE64.encode(source),
        encoded_base64: BASE64.encode(encoded),
        source_hash64: stable_hash64(source),
        source_crc32: crc32(source),
    }
}

fn add_synthetic_codec_vectors(vectors: &mut Vec<CodecVector>) -> anyhow::Result<()> {
    let raw = vec![b'@', 7, 11, 13];
    let raw_encoded = encode_frame(&raw, None, 0, CELL_BYTES)?;
    vectors.push(codec_vector(
        "codec-raw".to_string(),
        0,
        1,
        1,
        raw_encoded.tag,
        &raw,
        &raw_encoded.message,
    ));

    let rle = [b' ', 255, 255, 255].repeat(64);
    let rle_encoded = encode_frame(&rle, None, 0, CELL_BYTES)?;
    vectors.push(codec_vector(
        "codec-rle-delta".to_string(),
        0,
        8,
        8,
        rle_encoded.tag,
        &rle,
        &rle_encoded.message,
    ));
    let mut delta = rle.clone();
    delta[7 * CELL_BYTES..8 * CELL_BYTES].copy_from_slice(&[b'*', 10, 20, 30]);
    let delta_encoded = encode_frame(&delta, Some(&rle), 1, CELL_BYTES)?;
    vectors.push(codec_vector(
        "codec-rle-delta".to_string(),
        1,
        8,
        8,
        delta_encoded.tag,
        &delta,
        &delta_encoded.message,
    ));

    let mut zlib = Vec::new();
    for index in 0..256_u16 {
        zlib.extend_from_slice(&[
            b'#',
            (index % 251) as u8,
            ((index * 3) % 251) as u8,
            ((index * 7) % 251) as u8,
        ]);
    }
    let zlib_encoded = encode_frame(&zlib, None, 0, CELL_BYTES)?;
    vectors.push(codec_vector(
        "codec-zlib".to_string(),
        0,
        16,
        16,
        zlib_encoded.tag,
        &zlib,
        &zlib_encoded.message,
    ));
    let tags = vectors.iter().map(|vector| vector.tag).collect::<Vec<_>>();
    for required in [0_u8, 1, 2, 3] {
        if !tags.contains(&required) {
            bail!("production codec vectors did not produce tag {required}");
        }
    }
    Ok(())
}

fn render_media(root: &Path, categories: &BTreeMap<String, u32>) -> anyhow::Result<()> {
    for (category, frame_count) in categories {
        let raw = root.join(format!("tmp/{category}.rgb"));
        let sequence_dir = root.join(format!("frame-sequences/{category}"));
        std::fs::create_dir_all(&sequence_dir)?;
        for entry in std::fs::read_dir(&sequence_dir)? {
            let path = entry?.path();
            if path.extension().is_some_and(|extension| extension == "png") {
                std::fs::remove_file(path)?;
            }
        }
        let pattern = sequence_dir.join("%04d.png");
        run_ffmpeg(&[
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            "480x270",
            "-framerate",
            "24",
            "-i",
            path_text(&raw)?,
            "-frames:v",
            &frame_count.to_string(),
            "-start_number",
            "0",
            path_text(&pattern)?,
        ])?;
        let recording = root.join(format!("recordings/{category}.mp4"));
        run_ffmpeg(&[
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            "480x270",
            "-framerate",
            "24",
            "-i",
            path_text(&raw)?,
            "-vf",
            "scale=1920:1080:flags=neighbor",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            path_text(&recording)?,
        ])?;
        let stride = (*frame_count / 12).max(1);
        let contact_sheet = root.join(format!("screenshots/{category}-contact-sheet.png"));
        let filter = format!("select=not(mod(n\\,{stride})),scale=960:540:flags=neighbor,tile=4x3");
        run_ffmpeg(&[
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            "480x270",
            "-framerate",
            "24",
            "-i",
            path_text(&raw)?,
            "-vf",
            &filter,
            "-frames:v",
            "1",
            path_text(&contact_sheet)?,
        ])?;
        std::fs::remove_file(raw)?;
    }
    Ok(())
}

fn run_ffmpeg(arguments: &[&str]) -> anyhow::Result<()> {
    let status = Command::new("ffmpeg")
        .arg("-y")
        .arg("-loglevel")
        .arg("error")
        .args(arguments)
        .status()
        .context("failed to start ffmpeg")?;
    if !status.success() {
        bail!("ffmpeg failed with status {status}");
    }
    Ok(())
}

fn run_browser_parity(root: &Path) -> anyhow::Result<()> {
    let script =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("web/tools/verify_animation_evidence.mjs");
    let status = Command::new("node")
        .arg(script)
        .arg(root)
        .status()
        .context("failed to start browser parity verifier")?;
    if !status.success() {
        bail!("browser parity verifier failed with status {status}");
    }
    Ok(())
}

fn write_rust_hash_log(root: &Path, vectors: &[CodecVector]) -> anyhow::Result<()> {
    let mut writer = create_writer(&root.join("hashes/source-rust.ndjson"))?;
    for vector in vectors {
        write_ndjson(
            &mut writer,
            &json!({
                "group": vector.group,
                "sequence": vector.sequence,
                "tag": vector.tag,
                "source_hash64": vector.source_hash64,
                "source_crc32": vector.source_crc32,
            }),
        )?;
    }
    writer.flush()?;
    Ok(())
}

fn replay_manifest() -> ReplayManifest {
    ReplayManifest {
        schema_version: EVIDENCE_SCHEMA_VERSION,
        simulation_hz: EVIDENCE_SIMULATION_HZ,
        render_hz: EVIDENCE_RENDER_HZ,
        pre_boundary_frames: 12,
        post_boundary_frames: 16,
        transitions: transition_recipes(),
    }
}

fn transition_recipes() -> Vec<ReplayTransition> {
    let locomotion = "01-locomotion-directions";
    let actions = "02-speech-actions-expressions";
    let paths = "03-circles-figure-eight";
    let replay = "04-reconnect-replay";
    vec![
        recipe(
            "idle-to-walk",
            "idle -> walk",
            locomotion,
            vec![],
            vec![cmd("move", json!({"x": 2.0, "z": 5.0, "speed": 1.2}))],
            false,
        ),
        recipe(
            "walk-to-idle",
            "walk -> idle",
            locomotion,
            vec![cmd("move", json!({"x": 2.0, "z": 5.0, "speed": 1.2}))],
            vec![cmd("stop", json!({}))],
            false,
        ),
        recipe(
            "walk-to-turn",
            "walk -> turn",
            locomotion,
            vec![cmd("move", json!({"x": 2.0, "z": 5.0}))],
            vec![cmd("move", json!({"x": 1.75, "z": 3.0}))],
            false,
        ),
        recipe(
            "turn-to-walk",
            "turn -> walk",
            locomotion,
            vec![cmd("face", json!({"direction": "southeast"}))],
            vec![cmd("move", json!({"x": 1.75, "z": 3.0}))],
            false,
        ),
        recipe(
            "front-to-diagonal",
            "front -> diagonal",
            locomotion,
            vec![cmd("face", json!({"direction": "south"}))],
            vec![cmd("face", json!({"direction": "southeast"}))],
            false,
        ),
        recipe(
            "diagonal-to-side",
            "diagonal -> side",
            locomotion,
            vec![cmd("face", json!({"direction": "southeast"}))],
            vec![cmd("face", json!({"direction": "east"}))],
            false,
        ),
        recipe(
            "side-to-back",
            "side -> back",
            locomotion,
            vec![cmd("face", json!({"direction": "east"}))],
            vec![cmd("face", json!({"direction": "north"}))],
            false,
        ),
        recipe(
            "forward-to-backward",
            "forward -> backward",
            locomotion,
            vec![cmd("move", json!({"x": 0.0, "z": 3.0}))],
            vec![cmd("move", json!({"x": 0.0, "z": 7.0}))],
            false,
        ),
        recipe(
            "clockwise-circle",
            "clockwise circle changes",
            paths,
            vec![cmd(
                "circle",
                json!({"center_x": 0.0, "center_z": 5.0, "radius": 0.4, "duration_seconds": 1.4, "clockwise": true}),
            )],
            vec![],
            false,
        ),
        recipe(
            "counterclockwise-circle",
            "counterclockwise circle changes",
            paths,
            vec![cmd(
                "circle",
                json!({"center_x": 0.0, "center_z": 5.0, "radius": 0.4, "duration_seconds": 1.4, "clockwise": false}),
            )],
            vec![],
            false,
        ),
        recipe(
            "figure-eight-crossover",
            "figure-eight crossover",
            paths,
            vec![cmd(
                "figure_eight",
                json!({"center_x": 0.0, "center_z": 5.0, "radius": 0.4, "speed": 1.5}),
            )],
            vec![],
            false,
        ),
        recipe(
            "walk-to-speak",
            "walk -> speak",
            actions,
            vec![cmd("move", json!({"x": 2.0, "z": 5.0}))],
            vec![cmd(
                "speak",
                json!({"text": "Still walking", "duration_ms": 1200}),
            )],
            false,
        ),
        recipe(
            "speak-to-walk",
            "speak -> walk",
            actions,
            vec![
                cmd("move", json!({"x": 2.0, "z": 5.0})),
                cmd("speak", json!({"text": "Ending soon", "duration_ms": 700})),
            ],
            vec![],
            false,
        ),
        recipe(
            "idle-to-explain",
            "idle -> explain",
            actions,
            vec![],
            vec![cmd(
                "action",
                json!({"action": "explaining", "duration_ms": 1200}),
            )],
            false,
        ),
        recipe(
            "explain-to-walk",
            "explain -> walk",
            actions,
            vec![cmd(
                "action",
                json!({"action": "explaining", "duration_ms": 1800}),
            )],
            vec![cmd("move", json!({"x": 2.0, "z": 5.0}))],
            false,
        ),
        recipe(
            "walk-to-point",
            "walk -> point",
            actions,
            vec![cmd("move", json!({"x": 2.0, "z": 5.0}))],
            vec![cmd(
                "action",
                json!({"action": "pointing", "duration_ms": 1200}),
            )],
            false,
        ),
        recipe(
            "point-to-idle",
            "point -> idle",
            actions,
            vec![cmd(
                "action",
                json!({"action": "pointing", "duration_ms": 1800}),
            )],
            vec![cmd("action", json!({"action": "idle", "duration_ms": 1}))],
            false,
        ),
        recipe(
            "idle-to-think",
            "idle -> think",
            actions,
            vec![],
            vec![cmd(
                "action",
                json!({"action": "thinking", "duration_ms": 1200}),
            )],
            false,
        ),
        recipe(
            "think-to-speak",
            "think -> speak",
            actions,
            vec![cmd(
                "action",
                json!({"action": "thinking", "duration_ms": 1800}),
            )],
            vec![cmd(
                "speak",
                json!({"text": "Thinking aloud", "duration_ms": 1200}),
            )],
            false,
        ),
        recipe(
            "idle-to-cast",
            "idle -> cast",
            actions,
            vec![],
            vec![cmd(
                "action",
                json!({"action": "magic_cast", "duration_ms": 1200}),
            )],
            false,
        ),
        recipe(
            "cast-to-idle",
            "cast -> idle",
            actions,
            vec![cmd(
                "action",
                json!({"action": "magic_cast", "duration_ms": 1800}),
            )],
            vec![cmd("action", json!({"action": "idle", "duration_ms": 1}))],
            false,
        ),
        recipe(
            "reaction-to-previous",
            "reaction -> previous",
            actions,
            vec![cmd(
                "action",
                json!({"action": "pointing", "duration_ms": 1800}),
            )],
            vec![cmd(
                "action",
                json!({"action": "reaction", "duration_ms": 200}),
            )],
            false,
        ),
        recipe(
            "expression-during-locomotion",
            "expression during locomotion",
            actions,
            vec![cmd("move", json!({"x": 2.0, "z": 5.0}))],
            vec![cmd("expression", json!({"expression": "skeptical"}))],
            false,
        ),
        recipe(
            "blink-during-speech",
            "blink during speech",
            actions,
            vec![cmd(
                "speak",
                json!({"text": "Blink window", "duration_ms": 1600}),
            )],
            vec![],
            false,
        ),
        recipe(
            "mouth-closure",
            "mouth closure after speech",
            actions,
            vec![cmd("speak", json!({"text": "Close", "duration_ms": 650}))],
            vec![],
            false,
        ),
        recipe(
            "staff-during-turning",
            "staff during turning",
            actions,
            vec![cmd("move", json!({"x": 2.0, "z": 5.0}))],
            vec![cmd("move", json!({"x": 1.75, "z": 3.0}))],
            false,
        ),
        recipe(
            "staff-during-gesture",
            "staff during arm gestures",
            actions,
            vec![cmd("move", json!({"x": 2.0, "z": 5.0}))],
            vec![cmd(
                "action",
                json!({"action": "pointing", "duration_ms": 1200}),
            )],
            false,
        ),
        recipe(
            "depth-scaling",
            "depth scaling",
            locomotion,
            vec![],
            vec![cmd("move", json!({"x": 0.0, "z": 2.0}))],
            false,
        ),
        recipe(
            "root-view-change",
            "root during view changes",
            locomotion,
            vec![cmd("face", json!({"direction": "south"}))],
            vec![cmd("face", json!({"direction": "southwest"}))],
            false,
        ),
        recipe(
            "contact-shadow",
            "contact shadow during locomotion",
            locomotion,
            vec![cmd("move", json!({"x": 2.0, "z": 5.0}))],
            vec![cmd("expression", json!({"expression": "happy"}))],
            false,
        ),
        recipe(
            "interruption-cancellation",
            "interruption and cancellation",
            actions,
            vec![cmd(
                "action",
                json!({"action": "pointing", "duration_ms": 1800}),
            )],
            vec![cmd(
                "action",
                json!({"action": "magic_cast", "duration_ms": 1200}),
            )],
            false,
        ),
        recipe(
            "reconnect-replay",
            "reconnect and replay",
            replay,
            vec![cmd("move", json!({"x": 2.0, "z": 5.0}))],
            vec![],
            true,
        ),
        recipe(
            "canonical-fanout",
            "viewer-count canonical fanout",
            replay,
            vec![cmd(
                "action",
                json!({"action": "explaining", "duration_ms": 1200}),
            )],
            vec![],
            false,
        ),
        recipe(
            "missing-delta-resync",
            "missing delta recovery",
            replay,
            vec![cmd("move", json!({"x": -2.0, "z": 5.0}))],
            vec![],
            true,
        ),
        recipe(
            "hidden-resume",
            "hidden resume",
            replay,
            vec![cmd("speak", json!({"text": "Resume", "duration_ms": 1200}))],
            vec![],
            true,
        ),
        recipe(
            "context-restore",
            "context restore",
            replay,
            vec![cmd(
                "action",
                json!({"action": "magic_cast", "duration_ms": 1200}),
            )],
            vec![],
            true,
        ),
    ]
}

fn recipe(
    id: &str,
    ledger_transition: &str,
    category: &str,
    setup: Vec<ReplayCommandSpec>,
    boundary: Vec<ReplayCommandSpec>,
    force_full_at_boundary: bool,
) -> ReplayTransition {
    ReplayTransition {
        id: id.to_string(),
        ledger_transition: ledger_transition.to_string(),
        category: category.to_string(),
        setup,
        boundary,
        force_full_at_boundary,
    }
}

fn cmd(command_type: &str, payload: Value) -> ReplayCommandSpec {
    ReplayCommandSpec::new(command_type, payload)
}

fn evidence_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../evidence/animation-quality/final")
}

fn create_layout(root: &Path) -> anyhow::Result<()> {
    for directory in [
        "frame-sequences",
        "hashes",
        "logs",
        "recordings",
        "replay",
        "screenshots",
        "soak",
        "tmp",
    ] {
        std::fs::create_dir_all(root.join(directory))?;
    }
    Ok(())
}

fn create_writer(path: &Path) -> anyhow::Result<BufWriter<File>> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let file = OpenOptions::new()
        .create(true)
        .write(true)
        .truncate(true)
        .open(path)
        .with_context(|| format!("failed to open {}", path.display()))?;
    Ok(BufWriter::new(file))
}

fn write_ndjson(writer: &mut BufWriter<File>, value: &impl Serialize) -> anyhow::Result<()> {
    serde_json::to_writer(&mut *writer, value)?;
    writer.write_all(b"\n")?;
    Ok(())
}

fn write_json(path: &Path, value: &impl Serialize) -> anyhow::Result<()> {
    write_json_bytes(path, &serde_json::to_vec_pretty(value)?)
}

fn write_json_bytes(path: &Path, bytes: &[u8]) -> anyhow::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(path, bytes).with_context(|| format!("failed to write {}", path.display()))
}

fn path_text(path: &Path) -> anyhow::Result<&str> {
    path.to_str()
        .ok_or_else(|| anyhow::anyhow!("non-UTF-8 evidence path: {}", path.display()))
}

fn write_integrity_manifest(root: &Path) -> anyhow::Result<()> {
    validate_frame_sequence_layout(root)?;
    let mut files = Vec::new();
    collect_files(root, root, &mut files)?;
    files.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    write_json(
        &root.join("evidence-integrity.json"),
        &json!({
            "schema_version": 1,
            "file_count": files.len(),
            "files": files,
        }),
    )
}

fn check_integrity_manifest(root: &Path) -> anyhow::Result<()> {
    validate_frame_sequence_layout(root)?;
    let manifest_path = root.join("evidence-integrity.json");
    let manifest: Value = serde_json::from_slice(
        &std::fs::read(&manifest_path)
            .with_context(|| format!("failed to read {}", manifest_path.display()))?,
    )?;
    let mut actual = Vec::new();
    collect_files(root, root, &mut actual)?;
    actual.sort_by(|a, b| a["path"].as_str().cmp(&b["path"].as_str()));
    let expected = manifest["files"]
        .as_array()
        .ok_or_else(|| anyhow::anyhow!("integrity manifest has no files array"))?;
    if expected != &actual {
        bail!("evidence integrity mismatch");
    }
    if manifest["file_count"].as_u64() != Some(actual.len() as u64) {
        bail!("evidence integrity file count mismatch");
    }
    Ok(())
}

fn reset_frame_sequences(root: &Path) -> anyhow::Result<()> {
    let frame_root = root.join("frame-sequences");
    if frame_root.exists() {
        std::fs::remove_dir_all(&frame_root)
            .with_context(|| format!("failed to reset {}", frame_root.display()))?;
    }
    std::fs::create_dir_all(&frame_root)?;
    Ok(())
}

fn validate_frame_sequence_layout(root: &Path) -> anyhow::Result<()> {
    let summary_path = root.join("replay/run-1-summary.json");
    let summary: RunSummary = serde_json::from_slice(
        &std::fs::read(&summary_path)
            .with_context(|| format!("failed to read {}", summary_path.display()))?,
    )?;
    for (category, expected_count) in summary.category_frame_counts {
        let directory = root.join("frame-sequences").join(&category);
        let mut count = 0_u32;
        for entry in std::fs::read_dir(&directory)
            .with_context(|| format!("failed to read {}", directory.display()))?
        {
            let path = entry?.path();
            let valid_name = path.extension().is_some_and(|extension| extension == "png")
                && path.file_stem().is_some_and(|stem| {
                    let stem = stem.to_string_lossy();
                    stem.len() == 4 && stem.bytes().all(|byte| byte.is_ascii_digit())
                });
            if !path.is_file() || !valid_name {
                bail!("noncanonical frame-sequence artifact: {}", path.display());
            }
            count += 1;
        }
        if count != expected_count {
            bail!("frame-sequence count mismatch for {category}: {count} != {expected_count}");
        }
    }
    Ok(())
}

fn collect_files(root: &Path, directory: &Path, files: &mut Vec<Value>) -> anyhow::Result<()> {
    for entry in std::fs::read_dir(directory)? {
        let path = entry?.path();
        if path.is_dir() {
            collect_files(root, &path, files)?;
        } else if path
            .file_name()
            .is_some_and(|name| name != "evidence-integrity.json")
        {
            let bytes = std::fs::read(&path)?;
            files.push(json!({
                "path": path.strip_prefix(root)?.to_string_lossy(),
                "bytes": bytes.len(),
                "hash64": stable_hash64(&bytes),
                "crc32": crc32(&bytes),
            }));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn full_replay_rejects_seams_fragmentation_and_temporal_collapse() {
        let manifest = replay_manifest();
        let result = run_replay(&manifest, Path::new("."), "seam-regression", false)
            .expect("all 36 transitions must satisfy temporal topology gates");
        assert_eq!(result.summary.transitions, 36);
        assert_eq!(result.summary.frames, 1_008);
        assert!(result.summary.all_boundaries_passed);
        let failed = result
            .boundaries
            .iter()
            .filter(|metric| {
                metric.horizontal_seam_frames != 0
                    || metric.vertical_crack_frames != 0
                    || metric.staff_disconnected_frames != 0
                    || !metric.semantic_quality_failures.is_empty()
                    || metric.minimum_occupancy_ratio < 0.75
                    || metric.maximum_component_step > 2
                    || !metric.source_decoded_equal
                    || !metric.presented_sequence_strictly_increasing
            })
            .collect::<Vec<_>>();
        assert!(failed.is_empty(), "failed topology metrics: {failed:#?}");
    }

    #[test]
    fn walk_to_point_preserves_semantic_continuity() {
        let mut manifest = replay_manifest();
        manifest
            .transitions
            .retain(|transition| transition.id == "walk-to-point");
        let result = run_replay(&manifest, Path::new("."), "walk-to-point-regression", false)
            .expect("walk-to-point must satisfy the semantic continuity gates");
        assert_eq!(result.summary.transitions, 1);
        assert!(result.summary.all_boundaries_passed);
    }
}
