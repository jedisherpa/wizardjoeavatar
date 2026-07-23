use anyhow::{anyhow, bail, Context};
use flate2::read::GzDecoder;
use image::codecs::png::PngEncoder;
use image::imageops::FilterType;
use image::{GrayImage, ImageEncoder, Luma, Rgba, RgbaImage};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::{BTreeSet, HashMap, VecDeque};
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use wizard_avatar_engine::controller::{WizardAvatarController, WizardCommand};
use wizard_avatar_engine::pose_clip::POSE_CLIPS;
use wizard_avatar_engine::pose_graph_runtime::{
    implicit_runtime_pose_id, previous_runtime_pose_id, resolved_runtime_pose_id,
    runtime_actor_transform, runtime_pose_graph_catalog, verify_graph_bytes, RuntimeActorTransform,
    RuntimePoseGraphCatalog, RuntimePoseGraphEntry,
};
use wizard_avatar_engine::state::WorldPoint;

const SIMULATION_HZ: u32 = 60;
const PRESENTATION_FPS: u32 = 24;
const OUTPUT_WIDTH: u32 = 1_280;
const OUTPUT_HEIGHT: u32 = 720;
const LOGICAL_COLS: f32 = 480.0;
const LOGICAL_ROWS: f32 = 270.0;
const CANONICAL_ROOT_Y: f32 = 1_254.0;
const MAX_CLIP_TICKS: u64 = 12_000;
const MAX_SAME_GRAPH_DELTA_MILLIONTHS: u32 = 450_000;
const MAX_TRANSITION_DELTA_MILLIONTHS: u32 = 950_000;
const MAX_ROOT_STEP_MILLIPIXELS: u32 = 80_000;
const MAX_CONTACT_RESIDUAL_STEP_MILLIPIXELS: u32 = 36_000;
const MAX_TRANSITION_CONTACT_RESIDUAL_STEP_MILLIPIXELS: u32 = 100_000;
const MAX_COMPONENT_GROWTH: u32 = 12;
const MAX_LARGEST_COMPONENT_LOSS_MILLIONTHS: u32 = 75_000;
const MAX_WORLD_STEP_MILLIONTHS: u32 = 250_000;

#[derive(Clone, Debug, Deserialize)]
struct PixelGraph {
    schema_version: u32,
    graph_id: String,
    source_record_id: String,
    frame: PixelFrame,
    foreground_pixel_count: u64,
    palette: Vec<[u8; 4]>,
    runs: Vec<PixelRun>,
}

#[derive(Clone, Copy, Debug, Deserialize)]
struct PixelFrame {
    width: u32,
    height: u32,
}

#[derive(Clone, Debug, Deserialize)]
struct PixelRun {
    x: u32,
    y: u32,
    palette_indices: Vec<u32>,
}

#[derive(Clone, Debug)]
struct ProjectedGraph {
    image: RgbaImage,
    graph_sha256: String,
    canonical_alpha_sha256: String,
    canonical_silhouette: SilhouetteMetrics,
    foreground_pixel_count: u64,
    source_record_id: String,
    identity_integrity: bool,
}

#[derive(Clone, Debug)]
struct RenderedStage {
    png: Vec<u8>,
    actor_alpha: GrayImage,
    silhouette: SilhouetteMetrics,
    root: [f32; 2],
    contact_residual_y: f32,
    fully_visible: bool,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize)]
struct SilhouetteMetrics {
    alpha_pixel_count: u64,
    component_count: u32,
    largest_component_pixels: u64,
    largest_component_ratio_millionths: u32,
    bounds: Option<[u32; 4]>,
}

#[derive(Clone, Copy, Debug, Default, Serialize)]
struct FrameContinuity {
    silhouette_delta_millionths: Option<u32>,
    root_step_millipixels: Option<u32>,
    contact_residual_step_millipixels: Option<u32>,
    frame_delta_within_threshold: bool,
    root_contact_continuity: bool,
}

#[derive(Debug, Serialize)]
struct FrameEvidence {
    frame_index: usize,
    simulation_tick: u64,
    pose_clip_step: Option<usize>,
    requested_pose_id: String,
    previous_pose_id: String,
    pose_blend_millionths: u32,
    presented_pose_id: String,
    source_record_id: String,
    foreground_pixel_count: u64,
    graph_sha256: String,
    canonical_alpha_sha256: String,
    canonical_silhouette: SilhouetteMetrics,
    rendered_silhouette: SilhouetteMetrics,
    graph_identity_integrity: bool,
    silhouette_integrity: bool,
    fully_visible: bool,
    continuity: FrameContinuity,
    whole_pose_handoff: bool,
    png_path: String,
    png_sha256: String,
}

#[derive(Debug, Serialize)]
struct ClipEvidence {
    clip_id: String,
    contact_sheet_path: String,
    expected_step_count: usize,
    observed_step_indices: Vec<usize>,
    expected_pose_sequence: Vec<String>,
    observed_presented_pose_changes: Vec<String>,
    frame_count: usize,
    first_simulation_tick: u64,
    last_simulation_tick: u64,
    every_frame_has_complete_graph: bool,
    every_transition_is_continuous: bool,
    expected_pose_sequence_observed_in_order: bool,
    passed: bool,
    frames: Vec<FrameEvidence>,
}

#[derive(Debug, Serialize)]
struct EvidenceReport {
    schema_version: u32,
    report_id: String,
    simulation_hz: u32,
    presentation_fps: u32,
    output_size: [u32; 2],
    runtime_manifest_sha256: String,
    clip_count: usize,
    locomotion_scenario_count: usize,
    total_frame_count: usize,
    every_clip_passed: bool,
    every_locomotion_scenario_passed: bool,
    clips: Vec<ClipEvidence>,
    locomotion_scenarios: Vec<LocomotionEvidence>,
}

#[derive(Debug, Serialize)]
struct LocomotionFrameEvidence {
    frame_index: usize,
    simulation_tick: u64,
    presented_pose_id: String,
    expected_implicit_pose_id: String,
    source_record_id: String,
    foreground_pixel_count: u64,
    graph_sha256: String,
    canonical_alpha_sha256: String,
    canonical_silhouette: SilhouetteMetrics,
    rendered_silhouette: SilhouetteMetrics,
    graph_identity_integrity: bool,
    silhouette_integrity: bool,
    fully_visible: bool,
    continuity: FrameContinuity,
    walking: bool,
    world_position: WorldPoint,
    walk_phase_millionths: u32,
    actor_transform: RuntimeActorTransform,
    png_path: String,
    png_sha256: String,
}

#[derive(Debug, Serialize)]
struct LocomotionEvidence {
    scenario_id: String,
    contact_sheet_path: String,
    command: String,
    distance: f32,
    expected_pose_ids: Vec<String>,
    observed_pose_ids: Vec<String>,
    target_position: WorldPoint,
    final_position: WorldPoint,
    frame_count: usize,
    reached_target: bool,
    every_frame_has_complete_graph: bool,
    every_transition_is_continuous: bool,
    gait_phase_coverage: bool,
    gait_pose_phase_consistent: bool,
    stride_motion_seen: bool,
    monotonic_target_progress: bool,
    passed: bool,
    frames: Vec<LocomotionFrameEvidence>,
}

fn main() -> anyhow::Result<()> {
    let output = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("evidence/runtime-pixelgraph-qa/animation-frames"));
    fs::create_dir_all(&output)
        .with_context(|| format!("create evidence directory {}", output.display()))?;

    let catalog = runtime_pose_graph_catalog().map_err(|error| anyhow!(error))?;
    catalog
        .verify_runtime_files()
        .map_err(|error| anyhow!(error))?;
    let mut graph_cache = HashMap::<String, ProjectedGraph>::new();
    let mut rendered_cache = HashMap::<String, RenderedStage>::new();
    let mut clips = Vec::with_capacity(POSE_CLIPS.len());

    for clip in POSE_CLIPS {
        let evidence = render_clip(
            clip,
            catalog,
            &output,
            &mut graph_cache,
            &mut rendered_cache,
        )?;
        println!(
            "verified clip {}: {} measured frames",
            evidence.clip_id, evidence.frame_count
        );
        clips.push(evidence);
    }

    let locomotion_specs = [
        (
            "walk_left",
            "walk_left",
            2.0_f32,
            [-2.0, 5.0],
            &[
                "walk_contact_left",
                "walk_passing_left",
                "walk_up_left",
                "walk_contact_right",
            ][..],
        ),
        (
            "walk_right",
            "walk_right",
            2.0,
            [2.0, 5.0],
            &[
                "walk_contact_left",
                "walk_passing_left",
                "walk_up_left",
                "walk_contact_right",
            ][..],
        ),
        (
            "walk_forward",
            "walk_forward",
            2.5,
            [0.0, 2.5],
            &[
                "walk_contact_left",
                "walk_passing_left",
                "walk_up_left",
                "walk_contact_right",
            ][..],
        ),
        (
            "walk_backward",
            "walk_backward",
            2.5,
            [0.0, 7.5],
            &[
                "walk_contact_left",
                "walk_passing_left",
                "walk_up_left",
                "walk_contact_right",
            ][..],
        ),
    ];
    let mut locomotion_scenarios = Vec::with_capacity(locomotion_specs.len());
    for (scenario_id, command, distance, target, expected) in locomotion_specs {
        let evidence = render_locomotion(
            scenario_id,
            command,
            distance,
            WorldPoint {
                x: target[0],
                z: target[1],
            },
            expected,
            catalog,
            &output,
            &mut graph_cache,
        )?;
        println!(
            "verified locomotion {}: {} measured frames",
            evidence.scenario_id, evidence.frame_count
        );
        locomotion_scenarios.push(evidence);
    }

    let clip_frame_count = clips.iter().map(|clip| clip.frame_count).sum::<usize>();
    let locomotion_frame_count = locomotion_scenarios
        .iter()
        .map(|scenario| scenario.frame_count)
        .sum::<usize>();
    let report = EvidenceReport {
        schema_version: 2,
        report_id: "wizard-joe-graph-native-animation-frame-audit-v2".to_string(),
        simulation_hz: SIMULATION_HZ,
        presentation_fps: PRESENTATION_FPS,
        output_size: [OUTPUT_WIDTH, OUTPUT_HEIGHT],
        runtime_manifest_sha256:
            wizard_avatar_engine::pose_graph_runtime::runtime_pose_graph_manifest_sha256(),
        clip_count: clips.len(),
        locomotion_scenario_count: locomotion_scenarios.len(),
        total_frame_count: clip_frame_count + locomotion_frame_count,
        every_clip_passed: clips.iter().all(|clip| clip.passed),
        every_locomotion_scenario_passed: locomotion_scenarios
            .iter()
            .all(|scenario| scenario.passed),
        clips,
        locomotion_scenarios,
    };
    if !report.every_clip_passed || !report.every_locomotion_scenario_passed {
        bail!("one or more graph-native clips failed frame evidence");
    }
    let report_path = output.join("animation-frame-audit.json");
    fs::write(&report_path, serde_json::to_vec_pretty(&report)?)
        .with_context(|| format!("write {}", report_path.display()))?;
    println!(
        "graph-native animation evidence: {} clips, {} locomotion scenarios, {} frames, report {}",
        report.clip_count,
        report.locomotion_scenario_count,
        report.total_frame_count,
        report_path.display()
    );
    Ok(())
}

fn render_clip(
    clip: &wizard_avatar_engine::pose_clip::PoseClipDefinition,
    catalog: &RuntimePoseGraphCatalog,
    output: &Path,
    graph_cache: &mut HashMap<String, ProjectedGraph>,
    rendered_cache: &mut HashMap<String, RenderedStage>,
) -> anyhow::Result<ClipEvidence> {
    let clip_dir = output.join(clip.id);
    fs::create_dir_all(&clip_dir)
        .with_context(|| format!("create clip directory {}", clip_dir.display()))?;
    let mut controller = WizardAvatarController::default();
    let result = controller.apply_command(WizardCommand::new(
        "pose_clip",
        json!({"clip_id": clip.id, "loop": false}),
    ));
    if !result.ok {
        bail!("start clip {}: {}", clip.id, result.message);
    }

    let mut active_seen = false;
    let mut completion_tick = None;
    let mut presentation_accumulator = 0_u32;
    let mut observed_steps = BTreeSet::new();
    let mut observed_pose_changes = Vec::new();
    let mut frames = Vec::new();
    let mut previous_rendered: Option<(String, RenderedStage)> = None;

    for _ in 0..MAX_CLIP_TICKS {
        let state = controller.current_state();
        if state.pose_clip_id.as_deref() == Some(clip.id) {
            active_seen = true;
            if let Some(step) = state.pose_clip_step {
                observed_steps.insert(step);
            }
        } else if active_seen && completion_tick.is_none() {
            completion_tick = Some(state.simulation_tick);
        }

        let should_capture = frames.is_empty() || {
            presentation_accumulator += PRESENTATION_FPS;
            if presentation_accumulator >= SIMULATION_HZ {
                presentation_accumulator -= SIMULATION_HZ;
                true
            } else {
                false
            }
        };
        if should_capture {
            let requested_pose_id = resolved_runtime_pose_id(state);
            let previous_pose_id = previous_runtime_pose_id(state);
            let presented_pose_id = if state.pose_blend < 0.5 {
                previous_pose_id.clone()
            } else {
                requested_pose_id.clone()
            };
            if observed_pose_changes.last() != Some(&presented_pose_id) {
                observed_pose_changes.push(presented_pose_id.clone());
            }
            let entry = catalog
                .for_runtime_pose_id(&presented_pose_id)
                .ok_or_else(|| anyhow!("clip {} has unknown pose {presented_pose_id}", clip.id))?;
            let projected = load_graph(entry, catalog, graph_cache)?;
            let rendered = if let Some(cached) = rendered_cache.get(&presented_pose_id) {
                cached.clone()
            } else {
                let rendered = render_stage(
                    projected,
                    WorldPoint { x: 0.0, z: 5.0 },
                    RuntimeActorTransform::default(),
                )?;
                rendered_cache.insert(presented_pose_id.clone(), rendered.clone());
                rendered
            };
            let whole_pose_handoff =
                presented_pose_id == requested_pose_id || presented_pose_id == previous_pose_id;
            let continuity = frame_continuity(
                previous_rendered
                    .as_ref()
                    .map(|(source_record_id, previous)| (source_record_id.as_str(), previous)),
                projected.source_record_id.as_str(),
                &rendered,
            );
            let silhouette_integrity = silhouette_integrity(projected, &rendered);
            let frame_index = frames.len();
            let filename = format!("frame-{frame_index:04}.png");
            let path = clip_dir.join(&filename);
            fs::write(&path, &rendered.png).with_context(|| format!("write {}", path.display()))?;
            frames.push(FrameEvidence {
                frame_index,
                simulation_tick: state.simulation_tick,
                pose_clip_step: state.pose_clip_step,
                requested_pose_id,
                previous_pose_id,
                pose_blend_millionths: (state.pose_blend.clamp(0.0, 1.0) * 1_000_000.0).round()
                    as u32,
                presented_pose_id,
                source_record_id: projected.source_record_id.clone(),
                foreground_pixel_count: projected.foreground_pixel_count,
                graph_sha256: projected.graph_sha256.clone(),
                canonical_alpha_sha256: projected.canonical_alpha_sha256.clone(),
                canonical_silhouette: projected.canonical_silhouette,
                rendered_silhouette: rendered.silhouette,
                graph_identity_integrity: projected.identity_integrity,
                silhouette_integrity,
                fully_visible: rendered.fully_visible,
                continuity,
                whole_pose_handoff,
                png_path: format!("{}/{filename}", clip.id),
                png_sha256: sha256_hex(&rendered.png),
            });
            previous_rendered = Some((projected.source_record_id.clone(), rendered));
        }

        if completion_tick
            .is_some_and(|tick| state.simulation_tick >= tick + 12 && state.pose_blend >= 1.0)
        {
            break;
        }
        controller.step_tick();
    }

    let observed_step_indices = observed_steps.into_iter().collect::<Vec<_>>();
    let expected_steps = (0..clip.steps.len()).collect::<Vec<_>>();
    let every_frame_has_complete_graph = frames.iter().all(frame_is_complete);
    let every_transition_is_continuous = frames.iter().all(|frame| {
        frame.continuity.frame_delta_within_threshold && frame.continuity.root_contact_continuity
    });
    let expected_pose_sequence = clip
        .steps
        .iter()
        .map(|step| step.pose_id.to_string())
        .collect::<Vec<_>>();
    let expected_pose_sequence_observed_in_order =
        expected_pose_sequence
            .iter()
            .enumerate()
            .all(|(step_index, pose_id)| {
                frames.iter().any(|frame| {
                    frame.pose_clip_step == Some(step_index)
                        && (&frame.presented_pose_id == pose_id
                            || &frame.requested_pose_id == pose_id)
                })
            });
    let contact_sheet_path = format!("{}/contact-sheet.png", clip.id);
    write_contact_sheet(
        output,
        frames.iter().map(|frame| frame.png_path.as_str()),
        &contact_sheet_path,
    )?;
    let passed = active_seen
        && completion_tick.is_some()
        && observed_step_indices == expected_steps
        && every_frame_has_complete_graph
        && every_transition_is_continuous
        && expected_pose_sequence_observed_in_order
        && !frames.is_empty();
    let evidence = ClipEvidence {
        clip_id: clip.id.to_string(),
        contact_sheet_path,
        expected_step_count: clip.steps.len(),
        observed_step_indices,
        expected_pose_sequence,
        observed_presented_pose_changes: observed_pose_changes,
        frame_count: frames.len(),
        first_simulation_tick: frames.first().map_or(0, |frame| frame.simulation_tick),
        last_simulation_tick: frames.last().map_or(0, |frame| frame.simulation_tick),
        every_frame_has_complete_graph,
        every_transition_is_continuous,
        expected_pose_sequence_observed_in_order,
        passed,
        frames,
    };
    if !evidence.passed {
        let incomplete_frames = evidence
            .frames
            .iter()
            .filter(|frame| !frame_is_complete(frame))
            .map(|frame| frame.frame_index)
            .collect::<Vec<_>>();
        let discontinuous_frames = evidence
            .frames
            .iter()
            .filter(|frame| {
                !frame.continuity.frame_delta_within_threshold
                    || !frame.continuity.root_contact_continuity
            })
            .map(|frame| {
                (
                    frame.frame_index,
                    frame.continuity.silhouette_delta_millionths,
                    frame.continuity.root_step_millipixels,
                    frame.continuity.contact_residual_step_millipixels,
                )
            })
            .collect::<Vec<_>>();
        bail!(
            "clip {} failed: steps {:?}/{:?}, completion {:?}, {} frames, complete {}, continuous {}, sequence {}, incomplete {:?}, discontinuous {:?}",
            clip.id,
            evidence.observed_step_indices,
            expected_steps,
            completion_tick,
            evidence.frame_count,
            evidence.every_frame_has_complete_graph,
            evidence.every_transition_is_continuous,
            evidence.expected_pose_sequence_observed_in_order,
            incomplete_frames,
            discontinuous_frames,
        );
    }
    Ok(evidence)
}

#[allow(clippy::too_many_arguments)]
fn render_locomotion(
    scenario_id: &str,
    command: &str,
    distance: f32,
    target_position: WorldPoint,
    expected_pose_ids: &[&str],
    catalog: &RuntimePoseGraphCatalog,
    output: &Path,
    graph_cache: &mut HashMap<String, ProjectedGraph>,
) -> anyhow::Result<LocomotionEvidence> {
    let scenario_dir = output.join(scenario_id);
    fs::create_dir_all(&scenario_dir)
        .with_context(|| format!("create locomotion directory {}", scenario_dir.display()))?;
    let mut controller = WizardAvatarController::default();
    let result =
        controller.apply_command(WizardCommand::new(command, json!({"distance": distance})));
    if !result.ok {
        bail!("start locomotion {scenario_id}: {}", result.message);
    }
    let mut walking_seen = false;
    let mut idle_ticks = 0_u32;
    let mut presentation_accumulator = 0_u32;
    let mut observed_pose_ids = Vec::new();
    let mut frames = Vec::new();
    let mut previous_rendered: Option<(String, RenderedStage)> = None;

    for _ in 0..MAX_CLIP_TICKS {
        let state = controller.current_state();
        if state.locomotion == wizard_avatar_engine::state::Locomotion::Walking {
            walking_seen = true;
            idle_ticks = 0;
        } else if walking_seen {
            idle_ticks += 1;
        }
        let should_capture = frames.is_empty() || {
            presentation_accumulator += PRESENTATION_FPS;
            if presentation_accumulator >= SIMULATION_HZ {
                presentation_accumulator -= SIMULATION_HZ;
                true
            } else {
                false
            }
        };
        if should_capture {
            let pose_id = resolved_runtime_pose_id(state);
            let expected_implicit_pose_id = implicit_runtime_pose_id(state).to_string();
            if observed_pose_ids.last() != Some(&pose_id) {
                observed_pose_ids.push(pose_id.clone());
            }
            let entry = catalog
                .for_runtime_pose_id(&pose_id)
                .ok_or_else(|| anyhow!("locomotion {scenario_id} has unknown pose {pose_id}"))?;
            let graph = load_graph(entry, catalog, graph_cache)?;
            let actor_transform = runtime_actor_transform(state);
            let rendered = render_stage(graph, state.world_position, actor_transform)?;
            let continuity = frame_continuity(
                previous_rendered
                    .as_ref()
                    .map(|(source_record_id, previous)| (source_record_id.as_str(), previous)),
                graph.source_record_id.as_str(),
                &rendered,
            );
            let silhouette_integrity = silhouette_integrity(graph, &rendered);
            let frame_index = frames.len();
            let filename = format!("frame-{frame_index:04}.png");
            let path = scenario_dir.join(&filename);
            fs::write(&path, &rendered.png).with_context(|| format!("write {}", path.display()))?;
            frames.push(LocomotionFrameEvidence {
                frame_index,
                simulation_tick: state.simulation_tick,
                presented_pose_id: pose_id,
                expected_implicit_pose_id,
                source_record_id: graph.source_record_id.clone(),
                foreground_pixel_count: graph.foreground_pixel_count,
                graph_sha256: graph.graph_sha256.clone(),
                canonical_alpha_sha256: graph.canonical_alpha_sha256.clone(),
                canonical_silhouette: graph.canonical_silhouette,
                rendered_silhouette: rendered.silhouette,
                graph_identity_integrity: graph.identity_integrity,
                silhouette_integrity,
                fully_visible: rendered.fully_visible,
                continuity,
                walking: state.locomotion == wizard_avatar_engine::state::Locomotion::Walking,
                world_position: state.world_position,
                walk_phase_millionths: (state.walk_phase.rem_euclid(1.0) * 1_000_000.0).round()
                    as u32,
                actor_transform,
                png_path: format!("{scenario_id}/{filename}"),
                png_sha256: sha256_hex(&rendered.png),
            });
            previous_rendered = Some((graph.source_record_id.clone(), rendered));
        }
        if walking_seen && idle_ticks >= 12 {
            break;
        }
        controller.step_tick();
    }

    let final_position = controller.current_state().world_position;
    let reached_target = (final_position.x - target_position.x).abs() <= 0.05
        && (final_position.z - target_position.z).abs() <= 0.05;
    let observed = observed_pose_ids
        .iter()
        .map(String::as_str)
        .collect::<BTreeSet<_>>();
    let expected_seen = expected_pose_ids
        .iter()
        .all(|pose_id| observed.contains(pose_id));
    let every_frame_has_complete_graph = frames.iter().all(locomotion_frame_is_complete);
    let every_transition_is_continuous = frames.iter().all(|frame| {
        frame.continuity.frame_delta_within_threshold && frame.continuity.root_contact_continuity
    });
    let walking_frames = frames
        .iter()
        .filter(|frame| frame.walking)
        .collect::<Vec<_>>();
    let gait_phase_coverage = walking_frames
        .iter()
        .any(|frame| frame.walk_phase_millionths < 500_000)
        && walking_frames
            .iter()
            .any(|frame| frame.walk_phase_millionths >= 500_000);
    let gait_pose_phase_consistent = walking_frames
        .iter()
        .all(|frame| frame.presented_pose_id == frame.expected_implicit_pose_id);
    let stride_motion_seen = stride_motion_is_visible(&walking_frames);
    let monotonic_target_progress =
        progresses_monotonically_to_target(&walking_frames, target_position);
    let contact_sheet_path = format!("{scenario_id}/contact-sheet.png");
    write_contact_sheet(
        output,
        frames.iter().map(|frame| frame.png_path.as_str()),
        &contact_sheet_path,
    )?;
    let passed = walking_seen
        && reached_target
        && expected_seen
        && every_frame_has_complete_graph
        && every_transition_is_continuous
        && gait_phase_coverage
        && gait_pose_phase_consistent
        && stride_motion_seen
        && monotonic_target_progress;
    if !passed {
        let incomplete_frames = frames
            .iter()
            .filter(|frame| !locomotion_frame_is_complete(frame))
            .map(|frame| frame.frame_index)
            .collect::<Vec<_>>();
        let discontinuous_frames = frames
            .iter()
            .filter(|frame| {
                !frame.continuity.frame_delta_within_threshold
                    || !frame.continuity.root_contact_continuity
            })
            .map(|frame| {
                (
                    frame.frame_index,
                    frame.presented_pose_id.as_str(),
                    frame.continuity.silhouette_delta_millionths,
                    frame.continuity.root_step_millipixels,
                    frame.continuity.contact_residual_step_millipixels,
                )
            })
            .collect::<Vec<_>>();
        bail!(
            "locomotion {scenario_id} failed: walking {walking_seen}, target {reached_target}, expected poses {expected_seen}, complete {every_frame_has_complete_graph}, continuous {every_transition_is_continuous}, phase coverage {gait_phase_coverage}, phase consistent {gait_pose_phase_consistent}, stride {stride_motion_seen}, monotonic {monotonic_target_progress}, poses {:?}, incomplete {:?}, discontinuous {:?}",
            observed_pose_ids,
            incomplete_frames,
            discontinuous_frames,
        );
    }
    Ok(LocomotionEvidence {
        scenario_id: scenario_id.to_string(),
        contact_sheet_path,
        command: command.to_string(),
        distance,
        expected_pose_ids: expected_pose_ids
            .iter()
            .map(|pose_id| (*pose_id).to_string())
            .collect(),
        observed_pose_ids,
        target_position,
        final_position,
        frame_count: frames.len(),
        reached_target,
        every_frame_has_complete_graph,
        every_transition_is_continuous,
        gait_phase_coverage,
        gait_pose_phase_consistent,
        stride_motion_seen,
        monotonic_target_progress,
        passed,
        frames,
    })
}

fn load_graph<'a>(
    entry: &RuntimePoseGraphEntry,
    catalog: &RuntimePoseGraphCatalog,
    cache: &'a mut HashMap<String, ProjectedGraph>,
) -> anyhow::Result<&'a ProjectedGraph> {
    if !cache.contains_key(&entry.source_record_id) {
        let path = catalog.graph_path(entry).map_err(|error| anyhow!(error))?;
        let compressed = fs::read(&path).with_context(|| format!("read {}", path.display()))?;
        verify_graph_bytes(entry, &compressed).map_err(|error| anyhow!(error))?;
        let mut decoder = GzDecoder::new(compressed.as_slice());
        let mut json = Vec::new();
        decoder
            .read_to_end(&mut json)
            .with_context(|| format!("decode {}", path.display()))?;
        let graph: PixelGraph =
            serde_json::from_slice(&json).with_context(|| format!("parse {}", path.display()))?;
        let projected = project_graph(&graph, entry)?;
        cache.insert(entry.source_record_id.clone(), projected);
    }
    cache
        .get(&entry.source_record_id)
        .ok_or_else(|| anyhow!("graph cache lost {}", entry.source_record_id))
}

fn project_graph(
    graph: &PixelGraph,
    entry: &RuntimePoseGraphEntry,
) -> anyhow::Result<ProjectedGraph> {
    if graph.schema_version != 1
        || graph.graph_id != entry.graph_id
        || graph.source_record_id != entry.source_record_id
        || graph.frame.width != entry.frame[0]
        || graph.frame.height != entry.frame[1]
        || graph.foreground_pixel_count != entry.foreground_pixel_count
    {
        bail!("graph metadata mismatch for {}", entry.source_record_id);
    }
    let mut image = RgbaImage::new(graph.frame.width, graph.frame.height);
    let mut painted = 0_u64;
    for run in &graph.runs {
        let end = run
            .x
            .checked_add(run.palette_indices.len() as u32)
            .ok_or_else(|| anyhow!("run overflow in {}", entry.source_record_id))?;
        if run.y >= graph.frame.height || end > graph.frame.width {
            bail!("run leaves frame in {}", entry.source_record_id);
        }
        for (offset, palette_index) in run.palette_indices.iter().copied().enumerate() {
            let color = graph
                .palette
                .get(palette_index as usize)
                .ok_or_else(|| anyhow!("palette index overflow in {}", entry.source_record_id))?;
            if color[3] == 0 {
                bail!("transparent palette entry in {}", entry.source_record_id);
            }
            image.put_pixel(run.x + offset as u32, run.y, Rgba(*color));
            painted += 1;
        }
    }
    if painted != graph.foreground_pixel_count {
        bail!(
            "{} painted {painted} pixels instead of {}",
            entry.source_record_id,
            graph.foreground_pixel_count
        );
    }
    let canonical_silhouette = silhouette_metrics_rgba(&image);
    let canonical_alpha_sha256 = alpha_sha256_rgba(&image);
    let identity_integrity = painted == entry.foreground_pixel_count
        && canonical_silhouette.alpha_pixel_count == entry.foreground_pixel_count
        && graph.graph_id == entry.graph_id
        && graph.source_record_id == entry.source_record_id;
    Ok(ProjectedGraph {
        image,
        graph_sha256: entry.graph_sha256.clone(),
        canonical_alpha_sha256,
        canonical_silhouette,
        foreground_pixel_count: painted,
        source_record_id: entry.source_record_id.clone(),
        identity_integrity,
    })
}

fn render_stage(
    graph: &ProjectedGraph,
    world_position: WorldPoint,
    transform: RuntimeActorTransform,
) -> anyhow::Result<RenderedStage> {
    let mut stage = RgbaImage::from_pixel(OUTPUT_WIDTH, OUTPUT_HEIGHT, Rgba([255, 255, 255, 255]));
    let mut actor_layer = RgbaImage::new(OUTPUT_WIDTH, OUTPUT_HEIGHT);
    let depth = ((10.0_f32 - world_position.z) / (10.0 - 1.5)).clamp(0.0, 1.0);
    let scale = 1.4 + depth * 0.8;
    let projected_x = LOGICAL_COLS * 0.5 + world_position.x * LOGICAL_COLS * 0.075 * scale;
    let projected_y = LOGICAL_ROWS * 0.48 + depth * (LOGICAL_ROWS * 0.88 - LOGICAL_ROWS * 0.48);
    let logical_height = 96.0 * scale;
    let logical_width = logical_height * graph.image.width() as f32 / graph.image.height() as f32;
    let scale_x = OUTPUT_WIDTH as f32 / LOGICAL_COLS;
    let scale_y = OUTPUT_HEIGHT as f32 / LOGICAL_ROWS;
    let draw_width = (logical_width * scale_x).round().max(1.0) as u32;
    let draw_height = (logical_height * scale_y).round().max(1.0) as u32;
    let canonical_root = CANONICAL_ROOT_Y / graph.image.height() as f32;
    let resized =
        image::imageops::resize(&graph.image, draw_width, draw_height, FilterType::Nearest);
    let root = [
        (projected_x + transform.offset_x) * scale_x,
        (projected_y + transform.offset_y) * scale_y,
    ];
    composite_actor(
        &mut actor_layer,
        &resized,
        root[0],
        root[1],
        draw_width as f32 * 0.5,
        draw_height as f32 * canonical_root,
        transform,
    );
    let actor_alpha = rgba_alpha(&actor_layer);
    let silhouette = silhouette_metrics_alpha(&actor_alpha);
    let fully_visible = silhouette
        .bounds
        .is_some_and(|[min_x, min_y, max_x, max_y]| {
            min_x > 0 && min_y > 0 && max_x + 1 < OUTPUT_WIDTH && max_y + 1 < OUTPUT_HEIGHT
        });
    let contact_residual_y = silhouette
        .bounds
        .map_or(0.0, |bounds| bounds[3] as f32 - root[1]);
    image::imageops::overlay(&mut stage, &actor_layer, 0, 0);
    let mut png = Vec::new();
    PngEncoder::new(&mut png).write_image(
        stage.as_raw(),
        stage.width(),
        stage.height(),
        image::ExtendedColorType::Rgba8,
    )?;
    Ok(RenderedStage {
        png,
        actor_alpha,
        silhouette,
        root,
        contact_residual_y,
        fully_visible,
    })
}

fn composite_actor(
    stage: &mut RgbaImage,
    actor: &RgbaImage,
    root_x: f32,
    root_y: f32,
    anchor_x: f32,
    anchor_y: f32,
    transform: RuntimeActorTransform,
) {
    let radians = transform.rotation_degrees.to_radians();
    let cosine = radians.cos();
    let sine = radians.sin();
    let corners = [
        (-anchor_x, -anchor_y),
        (actor.width() as f32 - anchor_x, -anchor_y),
        (-anchor_x, actor.height() as f32 - anchor_y),
        (
            actor.width() as f32 - anchor_x,
            actor.height() as f32 - anchor_y,
        ),
    ]
    .map(|(x, y)| {
        let x = x * transform.scale_x;
        let y = y * transform.scale_y;
        (
            root_x + x * cosine - y * sine,
            root_y + x * sine + y * cosine,
        )
    });
    let min_x = corners
        .iter()
        .map(|corner| corner.0)
        .fold(f32::INFINITY, f32::min)
        .floor()
        .max(0.0) as u32;
    let max_x = corners
        .iter()
        .map(|corner| corner.0)
        .fold(f32::NEG_INFINITY, f32::max)
        .ceil()
        .min(stage.width() as f32 - 1.0) as u32;
    let min_y = corners
        .iter()
        .map(|corner| corner.1)
        .fold(f32::INFINITY, f32::min)
        .floor()
        .max(0.0) as u32;
    let max_y = corners
        .iter()
        .map(|corner| corner.1)
        .fold(f32::NEG_INFINITY, f32::max)
        .ceil()
        .min(stage.height() as f32 - 1.0) as u32;
    for y in min_y..=max_y {
        for x in min_x..=max_x {
            let dx = x as f32 + 0.5 - root_x;
            let dy = y as f32 + 0.5 - root_y;
            let local_x = (dx * cosine + dy * sine) / transform.scale_x + anchor_x;
            let local_y = (-dx * sine + dy * cosine) / transform.scale_y + anchor_y;
            if local_x < 0.0
                || local_y < 0.0
                || local_x >= actor.width() as f32
                || local_y >= actor.height() as f32
            {
                continue;
            }
            let source = *actor.get_pixel(local_x.floor() as u32, local_y.floor() as u32);
            if source[3] == 0 {
                continue;
            }
            let destination = stage.get_pixel_mut(x, y);
            *destination = source;
        }
    }
}

fn write_contact_sheet<'a>(
    output: &Path,
    frame_paths: impl IntoIterator<Item = &'a str>,
    contact_sheet_path: &str,
) -> anyhow::Result<()> {
    const TILE_WIDTH: u32 = 160;
    const TILE_HEIGHT: u32 = 90;
    const MAX_COLUMNS: usize = 12;

    let frame_paths = frame_paths.into_iter().collect::<Vec<_>>();
    if frame_paths.is_empty() {
        bail!("cannot make an empty contact sheet {contact_sheet_path}");
    }
    let columns = frame_paths.len().min(MAX_COLUMNS);
    let rows = frame_paths.len().div_ceil(columns);
    let mut sheet = RgbaImage::from_pixel(
        TILE_WIDTH * columns as u32,
        TILE_HEIGHT * rows as u32,
        Rgba([255, 255, 255, 255]),
    );
    for (index, frame_path) in frame_paths.iter().enumerate() {
        let absolute = output.join(frame_path);
        let frame = image::open(&absolute)
            .with_context(|| format!("read contact-sheet frame {}", absolute.display()))?
            .to_rgba8();
        let tile = image::imageops::resize(&frame, TILE_WIDTH, TILE_HEIGHT, FilterType::Nearest);
        image::imageops::overlay(
            &mut sheet,
            &tile,
            ((index % columns) as u32 * TILE_WIDTH).into(),
            ((index / columns) as u32 * TILE_HEIGHT).into(),
        );
    }
    let absolute = output.join(contact_sheet_path);
    let mut png = Vec::new();
    PngEncoder::new(&mut png).write_image(
        sheet.as_raw(),
        sheet.width(),
        sheet.height(),
        image::ExtendedColorType::Rgba8,
    )?;
    fs::write(&absolute, png)
        .with_context(|| format!("write contact sheet {}", absolute.display()))?;
    Ok(())
}

fn rgba_alpha(image: &RgbaImage) -> GrayImage {
    GrayImage::from_fn(image.width(), image.height(), |x, y| {
        Luma([image.get_pixel(x, y)[3]])
    })
}

fn alpha_sha256_rgba(image: &RgbaImage) -> String {
    let mut digest = Sha256::new();
    digest.update(image.width().to_le_bytes());
    digest.update(image.height().to_le_bytes());
    for pixel in image.pixels() {
        digest.update([pixel[3]]);
    }
    format!("{:x}", digest.finalize())
}

fn silhouette_metrics_rgba(image: &RgbaImage) -> SilhouetteMetrics {
    silhouette_metrics_alpha(&rgba_alpha(image))
}

fn silhouette_metrics_alpha(alpha: &GrayImage) -> SilhouetteMetrics {
    let mut bounds: Option<[u32; 4]> = None;
    let mut alpha_pixel_count = 0_u64;
    for (x, y, pixel) in alpha.enumerate_pixels() {
        if pixel[0] == 0 {
            continue;
        }
        alpha_pixel_count += 1;
        bounds = Some(match bounds {
            Some([min_x, min_y, max_x, max_y]) => {
                [min_x.min(x), min_y.min(y), max_x.max(x), max_y.max(y)]
            }
            None => [x, y, x, y],
        });
    }
    let Some([min_x, min_y, max_x, max_y]) = bounds else {
        return SilhouetteMetrics::default();
    };

    let local_width = (max_x - min_x + 1) as usize;
    let local_height = (max_y - min_y + 1) as usize;
    let mut visited = vec![false; local_width * local_height];
    let mut component_count = 0_u32;
    let mut largest_component_pixels = 0_u64;
    let mut queue = VecDeque::new();
    for local_y in 0..local_height {
        for local_x in 0..local_width {
            let index = local_y * local_width + local_x;
            if visited[index]
                || alpha.get_pixel(min_x + local_x as u32, min_y + local_y as u32)[0] == 0
            {
                continue;
            }
            component_count += 1;
            visited[index] = true;
            queue.push_back((local_x, local_y));
            let mut component_pixels = 0_u64;
            while let Some((x, y)) = queue.pop_front() {
                component_pixels += 1;
                for (next_x, next_y) in orthogonal_neighbors(x, y, local_width, local_height) {
                    let next_index = next_y * local_width + next_x;
                    if visited[next_index]
                        || alpha.get_pixel(min_x + next_x as u32, min_y + next_y as u32)[0] == 0
                    {
                        continue;
                    }
                    visited[next_index] = true;
                    queue.push_back((next_x, next_y));
                }
            }
            largest_component_pixels = largest_component_pixels.max(component_pixels);
        }
    }

    SilhouetteMetrics {
        alpha_pixel_count,
        component_count,
        largest_component_pixels,
        largest_component_ratio_millionths: ratio_millionths(
            largest_component_pixels,
            alpha_pixel_count,
        ),
        bounds,
    }
}

fn orthogonal_neighbors(
    x: usize,
    y: usize,
    width: usize,
    height: usize,
) -> impl Iterator<Item = (usize, usize)> {
    let mut neighbors = [(0_usize, 0_usize); 4];
    let mut count = 0;
    if x > 0 {
        neighbors[count] = (x - 1, y);
        count += 1;
    }
    if x + 1 < width {
        neighbors[count] = (x + 1, y);
        count += 1;
    }
    if y > 0 {
        neighbors[count] = (x, y - 1);
        count += 1;
    }
    if y + 1 < height {
        neighbors[count] = (x, y + 1);
        count += 1;
    }
    neighbors.into_iter().take(count)
}

fn ratio_millionths(numerator: u64, denominator: u64) -> u32 {
    if denominator == 0 {
        return 0;
    }
    ((u128::from(numerator) * 1_000_000) / u128::from(denominator)).min(u128::from(u32::MAX)) as u32
}

fn silhouette_integrity(graph: &ProjectedGraph, rendered: &RenderedStage) -> bool {
    let canonical = graph.canonical_silhouette;
    let projected = rendered.silhouette;
    graph.identity_integrity
        && rendered.fully_visible
        && projected.alpha_pixel_count > 0
        && projected.component_count
            <= canonical
                .component_count
                .saturating_add(MAX_COMPONENT_GROWTH)
        && projected
            .largest_component_ratio_millionths
            .saturating_add(MAX_LARGEST_COMPONENT_LOSS_MILLIONTHS)
            >= canonical.largest_component_ratio_millionths
}

fn frame_continuity(
    previous: Option<(&str, &RenderedStage)>,
    current_source_record_id: &str,
    current: &RenderedStage,
) -> FrameContinuity {
    let Some((previous_source_record_id, previous)) = previous else {
        return FrameContinuity {
            frame_delta_within_threshold: true,
            root_contact_continuity: true,
            ..FrameContinuity::default()
        };
    };
    let silhouette_delta_millionths =
        silhouette_delta_millionths(&previous.actor_alpha, &current.actor_alpha);
    let root_step_millipixels = point_step_millipixels(previous.root, current.root);
    let contact_residual_step_millipixels =
        ((previous.contact_residual_y - current.contact_residual_y).abs() * 1_000.0).round() as u32;
    let delta_limit = if previous_source_record_id == current_source_record_id {
        MAX_SAME_GRAPH_DELTA_MILLIONTHS
    } else {
        MAX_TRANSITION_DELTA_MILLIONTHS
    };
    let contact_limit = if previous_source_record_id == current_source_record_id {
        MAX_CONTACT_RESIDUAL_STEP_MILLIPIXELS
    } else {
        MAX_TRANSITION_CONTACT_RESIDUAL_STEP_MILLIPIXELS
    };
    FrameContinuity {
        silhouette_delta_millionths: Some(silhouette_delta_millionths),
        root_step_millipixels: Some(root_step_millipixels),
        contact_residual_step_millipixels: Some(contact_residual_step_millipixels),
        frame_delta_within_threshold: silhouette_delta_millionths <= delta_limit,
        root_contact_continuity: root_step_millipixels <= MAX_ROOT_STEP_MILLIPIXELS
            && contact_residual_step_millipixels <= contact_limit,
    }
}

fn silhouette_delta_millionths(left: &GrayImage, right: &GrayImage) -> u32 {
    if left.dimensions() != right.dimensions() {
        return 1_000_000;
    }
    let mut union = 0_u64;
    let mut difference = 0_u64;
    for (left, right) in left.pixels().zip(right.pixels()) {
        let left_opaque = left[0] > 0;
        let right_opaque = right[0] > 0;
        if left_opaque || right_opaque {
            union += 1;
            if left_opaque != right_opaque {
                difference += 1;
            }
        }
    }
    ratio_millionths(difference, union)
}

fn point_step_millipixels(left: [f32; 2], right: [f32; 2]) -> u32 {
    (((right[0] - left[0]).hypot(right[1] - left[1])) * 1_000.0).round() as u32
}

fn frame_is_complete(frame: &FrameEvidence) -> bool {
    frame.whole_pose_handoff
        && frame.graph_identity_integrity
        && frame.silhouette_integrity
        && frame.fully_visible
        && frame.foreground_pixel_count == frame.canonical_silhouette.alpha_pixel_count
        && valid_sha256(&frame.graph_sha256)
        && valid_sha256(&frame.canonical_alpha_sha256)
        && valid_sha256(&frame.png_sha256)
}

fn locomotion_frame_is_complete(frame: &LocomotionFrameEvidence) -> bool {
    frame.graph_identity_integrity
        && frame.silhouette_integrity
        && frame.fully_visible
        && frame.foreground_pixel_count == frame.canonical_silhouette.alpha_pixel_count
        && frame.rendered_silhouette.alpha_pixel_count > 0
        && frame.actor_transform.scale_x.abs() > f32::EPSILON
        && frame.actor_transform.scale_y > 0.0
        && valid_sha256(&frame.graph_sha256)
        && valid_sha256(&frame.canonical_alpha_sha256)
        && valid_sha256(&frame.png_sha256)
}

fn stride_motion_is_visible(frames: &[&LocomotionFrameEvidence]) -> bool {
    if frames.is_empty() {
        return false;
    }
    let min_x = frames
        .iter()
        .map(|frame| frame.actor_transform.offset_x)
        .fold(f32::INFINITY, f32::min);
    let max_x = frames
        .iter()
        .map(|frame| frame.actor_transform.offset_x)
        .fold(f32::NEG_INFINITY, f32::max);
    let min_y = frames
        .iter()
        .map(|frame| frame.actor_transform.offset_y)
        .fold(f32::INFINITY, f32::min);
    let max_y = frames
        .iter()
        .map(|frame| frame.actor_transform.offset_y)
        .fold(f32::NEG_INFINITY, f32::max);
    min_x <= -0.5 && max_x >= 0.5 && min_y <= -1.5 && max_y >= -0.25
}

fn progresses_monotonically_to_target(
    frames: &[&LocomotionFrameEvidence],
    target: WorldPoint,
) -> bool {
    let points = frames
        .iter()
        .map(|frame| frame.world_position)
        .collect::<Vec<_>>();
    progresses_monotonically(&points, target)
}

fn progresses_monotonically(points: &[WorldPoint], target: WorldPoint) -> bool {
    if points.len() < 2 {
        return false;
    }
    points.windows(2).all(|pair| {
        let previous_distance = world_distance(pair[0], target);
        let current_distance = world_distance(pair[1], target);
        let world_step_millionths = (world_distance(pair[0], pair[1]) * 1_000_000.0).round() as u32;
        current_distance <= previous_distance + 0.01
            && world_step_millionths <= MAX_WORLD_STEP_MILLIONTHS
    })
}

fn world_distance(left: WorldPoint, right: WorldPoint) -> f32 {
    (right.x - left.x).hypot(right.z - left.z)
}

fn valid_sha256(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|byte| byte.is_ascii_hexdigit())
}

fn sha256_hex(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rendered_stage(alpha: GrayImage, root: [f32; 2]) -> RenderedStage {
        let silhouette = silhouette_metrics_alpha(&alpha);
        RenderedStage {
            png: Vec::new(),
            actor_alpha: alpha,
            silhouette,
            root,
            contact_residual_y: silhouette
                .bounds
                .map_or(0.0, |bounds| bounds[3] as f32 - root[1]),
            fully_visible: true,
        }
    }

    #[test]
    fn silhouette_metrics_measure_real_components_and_largest_ratio() {
        let mut alpha = GrayImage::new(8, 6);
        for y in 1..=3 {
            for x in 1..=3 {
                alpha.put_pixel(x, y, Luma([255]));
            }
        }
        alpha.put_pixel(6, 4, Luma([255]));

        let metrics = silhouette_metrics_alpha(&alpha);
        assert_eq!(metrics.alpha_pixel_count, 10);
        assert_eq!(metrics.component_count, 2);
        assert_eq!(metrics.largest_component_pixels, 9);
        assert_eq!(metrics.largest_component_ratio_millionths, 900_000);
        assert_eq!(metrics.bounds, Some([1, 1, 6, 4]));
    }

    #[test]
    fn silhouette_delta_detects_disappearance_instead_of_trusting_a_hash() {
        let mut intact = GrayImage::new(4, 4);
        intact.put_pixel(1, 1, Luma([255]));
        intact.put_pixel(2, 1, Luma([255]));
        let empty = GrayImage::new(4, 4);

        assert_eq!(silhouette_delta_millionths(&intact, &intact), 0);
        assert_eq!(silhouette_delta_millionths(&intact, &empty), 1_000_000);
    }

    #[test]
    fn measured_integrity_rejects_a_broken_apart_projection() {
        let mut canonical_image = RgbaImage::new(8, 8);
        for y in 2..=5 {
            for x in 2..=5 {
                canonical_image.put_pixel(x, y, Rgba([0, 120, 255, 255]));
            }
        }
        let canonical_silhouette = silhouette_metrics_rgba(&canonical_image);
        let graph = ProjectedGraph {
            image: canonical_image.clone(),
            graph_sha256: "a".repeat(64),
            canonical_alpha_sha256: alpha_sha256_rgba(&canonical_image),
            canonical_silhouette,
            foreground_pixel_count: canonical_silhouette.alpha_pixel_count,
            source_record_id: "WJSRC-TEST".to_string(),
            identity_integrity: true,
        };
        let intact = rendered_stage(rgba_alpha(&canonical_image), [4.0, 6.0]);
        assert!(silhouette_integrity(&graph, &intact));

        let mut fragmented = GrayImage::new(8, 8);
        fragmented.put_pixel(2, 2, Luma([255]));
        fragmented.put_pixel(5, 5, Luma([255]));
        let fragmented = rendered_stage(fragmented, [4.0, 6.0]);
        assert!(!silhouette_integrity(&graph, &fragmented));
    }

    #[test]
    fn continuity_gate_rejects_disappearance_and_root_teleport() {
        let mut alpha = GrayImage::new(16, 16);
        for y in 4..=10 {
            for x in 5..=9 {
                alpha.put_pixel(x, y, Luma([255]));
            }
        }
        let previous = rendered_stage(alpha.clone(), [7.0, 11.0]);
        let disappeared = rendered_stage(GrayImage::new(16, 16), [7.0, 11.0]);
        let breakup = frame_continuity(Some(("same", &previous)), "same", &disappeared);
        assert!(!breakup.frame_delta_within_threshold);

        let teleported = rendered_stage(alpha, [100.0, 11.0]);
        let jump = frame_continuity(Some(("same", &previous)), "same", &teleported);
        assert!(!jump.root_contact_continuity);
    }

    #[test]
    fn target_progress_rejects_reverse_motion_and_teleports() {
        let target = WorldPoint { x: 3.0, z: 5.0 };
        assert!(progresses_monotonically(
            &[
                WorldPoint { x: 0.0, z: 5.0 },
                WorldPoint { x: 0.1, z: 5.0 },
                WorldPoint { x: 0.2, z: 5.0 },
            ],
            target,
        ));
        assert!(!progresses_monotonically(
            &[
                WorldPoint { x: 0.0, z: 5.0 },
                WorldPoint { x: -0.1, z: 5.0 },
            ],
            target,
        ));
        assert!(!progresses_monotonically(
            &[WorldPoint { x: 0.0, z: 5.0 }, WorldPoint { x: 1.0, z: 5.0 },],
            target,
        ));
    }
}
