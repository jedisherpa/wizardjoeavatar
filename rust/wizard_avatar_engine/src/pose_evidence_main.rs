use anyhow::{bail, Context};
use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{create_dir_all, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use wizard_avatar_engine::codec::{decode_frame, CELL_BYTES};
use wizard_avatar_engine::controller::WizardCommand;
use wizard_avatar_engine::frame_source::ProceduralWizardFrameSource;
use wizard_avatar_engine::newsroom::{
    runtime_binding_for_pose, NewsCommand, NewsPerformanceCueV1, NewsProgram, NewsroomCatalogs,
    StorySensitivity, UnitInterval, NEWSROOM_CUE_SCHEMA_VERSION,
};
use wizard_avatar_engine::pose::{
    sample_pose, transition_ticks_for, AnchorId, PointF, PoseLibrary, PoseTopologyMetrics,
};
use wizard_avatar_engine::pose_clip::POSE_CLIPS;
use wizard_avatar_engine::pose_playback::DEFAULT_POSE_TRANSITION_TICKS;
use wizard_avatar_engine::quality::{
    FrameQualityReport, FrameQualitySnapshot, FrameQualityThresholds,
};
use wizard_avatar_engine::renderer::render_stage;
use wizard_avatar_engine::runtime::AvatarRuntime;
use wizard_avatar_engine::state::{ContactMarker, PlantedFoot, ScreenPoint, WizardState};

const WIDTH: usize = 480;
const HEIGHT: usize = 270;
const FPS: u32 = 24;

#[derive(Serialize)]
struct StaticPoseRecord {
    frame_index: usize,
    pose_id: String,
    resolved_pose_id: String,
    candidate_id: Option<String>,
    occupied_cells: usize,
    source_cells: usize,
    png: String,
}

#[derive(Serialize)]
struct StaticManifest {
    schema_version: u32,
    generator: &'static str,
    catalog_frames: usize,
    unique_geometry_count: usize,
    alias_count: usize,
    frame_width: usize,
    frame_height: usize,
    records: Vec<StaticPoseRecord>,
    quality: FrameQualityReport,
}

fn main() -> anyhow::Result<()> {
    let root = evidence_root().join("static-census");
    reset_dir(&root)?;
    let frames_dir = root.join("frames");
    create_dir_all(&frames_dir)?;
    let raw_path = root.join("frames.rgb");
    let mut raw = BufWriter::new(File::create(&raw_path)?);
    let library = PoseLibrary::reference().map_err(anyhow::Error::msg)?;
    let mut records = Vec::new();
    let mut snapshots = Vec::new();
    let ids = library
        .pose_ids()
        .filter_map(|pose_id| {
            let pose = library.for_id(pose_id)?;
            Some((pose.motion.candidate_id.clone(), pose.id.clone()))
        })
        .collect::<Vec<_>>();

    for (frame_index, (candidate_id, pose_id)) in ids.into_iter().enumerate() {
        let mut state = WizardState {
            pose_id: Some(pose_id.clone()),
            previous_pose_id: Some(pose_id.clone()),
            pose_handoff: true,
            pose_blend: 1.0,
            screen_position: ScreenPoint {
                x: WIDTH as f32 * 0.5,
                y: HEIGHT as f32 - 12.0,
            },
            display_scale: 2.0,
            ..WizardState::default()
        };
        state.simulation_tick = frame_index as u64 * 5;
        state.time_seconds = state.simulation_tick as f32 / 60.0;
        let sample = sample_pose(&state).map_err(anyhow::Error::msg)?;
        let frame = render_stage(&state, WIDTH, HEIGHT).to_frame_bytes();
        raw.write_all(&cell_rgb_bytes(&frame))?;
        let snapshot = FrameQualitySnapshot::from_pose(
            format!("static-{pose_id}"),
            sample.pose_id.clone(),
            frame_index as u64,
            &sample,
        )
        .map_err(anyhow::Error::msg)?;
        records.push(StaticPoseRecord {
            frame_index,
            pose_id,
            resolved_pose_id: sample.pose_id.clone(),
            candidate_id,
            occupied_cells: snapshot.topology.occupied_cells,
            source_cells: snapshot.source_cell_count,
            png: format!("frames/{frame_index:04}.png"),
        });
        snapshots.push(snapshot);
    }
    raw.flush()?;

    render_png_sequence(&raw_path, &frames_dir, records.len())?;
    verify_png_sequence(&frames_dir, records.len(), 4)?;
    render_contact_sheet(&raw_path, &root.join("contact-sheet.png"), records.len())?;
    let mut quality = FrameQualityReport::default();
    for snapshot in &snapshots {
        let report = FrameQualityReport::inspect_sequence(
            std::slice::from_ref(snapshot),
            FrameQualityThresholds::default(),
        );
        quality.frame_count += report.frame_count;
        quality.failures.extend(report.failures);
    }
    let manifest = StaticManifest {
        schema_version: 1,
        generator: "wizard-avatar-pose-evidence-rust-v4",
        catalog_frames: records.len(),
        unique_geometry_count: library.pose_ids().count(),
        alias_count: library.alias_count(),
        frame_width: WIDTH,
        frame_height: HEIGHT,
        records,
        quality,
    };
    write_json(&root.join("manifest.json"), &manifest)?;
    std::fs::remove_file(raw_path)?;
    println!(
        "rendered {} catalog frames; static quality failures: {}",
        manifest.catalog_frames,
        manifest.quality.failures.len()
    );
    render_animation_verification()?;
    Ok(())
}

#[derive(Clone, Serialize)]
struct AnimationContactRecord {
    contact_marker: ContactMarker,
    planted_foot: PlantedFoot,
    contact_root: PointF,
    left_foot: PointF,
    right_foot: PointF,
    staff_hand: PointF,
}

#[derive(Clone, Serialize)]
struct AnimationFrameRecord {
    frame_index: usize,
    scenario_id: String,
    transition_id: String,
    simulation_tick: u64,
    pose_id: String,
    requested_pose_id: Option<String>,
    clip_id: Option<String>,
    clip_step: Option<usize>,
    anchors: BTreeMap<AnchorId, PointF>,
    contacts: AnimationContactRecord,
    stream_sequence: u32,
    presented_sequence: usize,
    codec_tag: u8,
    source_frame_sha256: String,
    decoded_frame_sha256: String,
    presented_frame_sha256: String,
    presentation_accepted: bool,
    topology: PoseTopologyMetrics,
    source_cells: usize,
    png: String,
}

struct AnimationPass {
    records: Vec<AnimationFrameRecord>,
    frame_hashes: Vec<String>,
    quality: FrameQualityReport,
    authored_transitions: usize,
    newsroom_semantic_poses: usize,
}

struct AnimationRecorder {
    raw: Option<BufWriter<File>>,
    records: Vec<AnimationFrameRecord>,
    frame_hashes: Vec<String>,
    quality_groups: BTreeMap<String, Vec<FrameQualitySnapshot>>,
    decoded_previous: Option<Vec<u8>>,
    previous_presented_sequence: Option<usize>,
}

impl AnimationRecorder {
    fn new(raw_path: Option<&Path>) -> anyhow::Result<Self> {
        Ok(Self {
            raw: raw_path.map(File::create).transpose()?.map(BufWriter::new),
            records: Vec::new(),
            frame_hashes: Vec::new(),
            quality_groups: BTreeMap::new(),
            decoded_previous: None,
            previous_presented_sequence: None,
        })
    }

    fn capture(
        &mut self,
        scenario_id: &str,
        transition_id: &str,
        runtime: &AvatarRuntime,
        frame_source: &mut ProceduralWizardFrameSource,
    ) -> anyhow::Result<()> {
        let state = runtime.current_state();
        let sample = sample_pose(state).map_err(anyhow::Error::msg)?;
        let (message, frame) = frame_source
            .render_and_encode(state, "adaptive")
            .map_err(anyhow::Error::msg)?;
        if frame.frame_index == 0 {
            self.decoded_previous = None;
        }
        let (stream_sequence, decoded, decoded_tag) =
            decode_frame(&message, self.decoded_previous.as_deref(), CELL_BYTES)
                .map_err(anyhow::Error::msg)?;
        if stream_sequence != frame.frame_index {
            bail!(
                "adaptive sequence mismatch in {transition_id}: {stream_sequence} != {}",
                frame.frame_index
            );
        }
        if decoded != frame.cells {
            bail!("adaptive decode mismatch in {transition_id} at sequence {stream_sequence}");
        }
        if decoded_tag as u8 != frame.codec_tag {
            bail!(
                "adaptive codec-tag mismatch in {transition_id}: {} != {}",
                decoded_tag as u8,
                frame.codec_tag
            );
        }
        self.decoded_previous = Some(decoded.clone());

        let source_frame_sha256 = format!("{:x}", Sha256::digest(&frame.cells));
        let decoded_frame_sha256 = format!("{:x}", Sha256::digest(&decoded));
        let presented_frame_sha256 = decoded_frame_sha256.clone();
        if let Some(raw) = &mut self.raw {
            raw.write_all(&cell_rgb_bytes(&frame.cells))?;
        }
        let frame_index = self.records.len();
        let presented_sequence = frame_index;
        if self
            .previous_presented_sequence
            .is_some_and(|previous| presented_sequence != previous + 1)
        {
            bail!("presentation sequence is not strictly contiguous at frame {frame_index}");
        }
        self.previous_presented_sequence = Some(presented_sequence);
        let snapshot = FrameQualitySnapshot::from_pose(
            transition_id,
            sample.pose_id.clone(),
            frame_index as u64,
            &sample,
        )
        .map_err(anyhow::Error::msg)?;
        self.quality_groups
            .entry(transition_id.to_string())
            .or_default()
            .push(snapshot.clone());
        self.records.push(AnimationFrameRecord {
            frame_index,
            scenario_id: scenario_id.to_string(),
            transition_id: transition_id.to_string(),
            simulation_tick: state.simulation_tick,
            pose_id: sample.pose_id,
            requested_pose_id: state.pose_id.clone(),
            clip_id: state.pose_clip_id.clone(),
            clip_step: state.pose_clip_step,
            anchors: sample.anchors.clone(),
            contacts: AnimationContactRecord {
                contact_marker: state.contact_marker,
                planted_foot: state.planted_foot,
                contact_root: sample.anchors[&AnchorId::ContactRoot],
                left_foot: sample.anchors[&AnchorId::LeftFoot],
                right_foot: sample.anchors[&AnchorId::RightFoot],
                staff_hand: sample.anchors[&AnchorId::StaffHand],
            },
            stream_sequence,
            presented_sequence,
            codec_tag: frame.codec_tag,
            source_frame_sha256: source_frame_sha256.clone(),
            decoded_frame_sha256,
            presented_frame_sha256,
            presentation_accepted: true,
            topology: snapshot.topology,
            source_cells: snapshot.source_cell_count,
            png: format!("frames/{frame_index:06}.png"),
        });
        self.frame_hashes.push(source_frame_sha256);
        Ok(())
    }

    fn finish(
        mut self,
        authored_transitions: usize,
        newsroom_semantic_poses: usize,
    ) -> anyhow::Result<AnimationPass> {
        if let Some(raw) = &mut self.raw {
            raw.flush()?;
        }
        let thresholds = FrameQualityThresholds {
            maximum_face_anchor_step: 4.0,
            maximum_staff_anchor_step: 6.0,
            maximum_free_foot_step: 8.0,
            ..FrameQualityThresholds::default()
        };
        let mut quality = FrameQualityReport::default();
        for snapshots in self.quality_groups.values() {
            let report = FrameQualityReport::inspect_sequence(snapshots, thresholds);
            quality.frame_count += report.frame_count;
            quality.pair_count += report.pair_count;
            quality.failures.extend(report.failures);
        }
        Ok(AnimationPass {
            records: self.records,
            frame_hashes: self.frame_hashes,
            quality,
            authored_transitions,
            newsroom_semantic_poses,
        })
    }
}

#[derive(Serialize)]
struct AnimationManifest {
    schema_version: u32,
    generator: &'static str,
    source_git_sha: String,
    simulation_fps: u32,
    frame_width: usize,
    frame_height: usize,
    frame_count: usize,
    catalog_records: usize,
    unique_geometries: usize,
    aliases: usize,
    rust_clip_count: usize,
    authored_transition_count: usize,
    newsroom_semantic_pose_count: usize,
    deterministic_replay: bool,
    adaptive_decode_parity: bool,
    presentation_parity: bool,
    pass_one_stream_sha256: String,
    pass_two_stream_sha256: String,
    quality: FrameQualityReport,
    frame_ledger: &'static str,
    video: &'static str,
    timeline_contact_sheet: &'static str,
}

fn render_animation_verification() -> anyhow::Result<()> {
    let root = evidence_root().join("animation-verification");
    reset_dir(&root)?;
    let frames_dir = root.join("frames");
    create_dir_all(&frames_dir)?;
    let raw_path = root.join("frames.rgb");

    let first = run_animation_pass(Some(&raw_path))?;
    let second = run_animation_pass(None)?;
    let deterministic = first.frame_hashes == second.frame_hashes;
    let first_stream_sha256 = hash_stream(&first.frame_hashes);
    let second_stream_sha256 = hash_stream(&second.frame_hashes);

    write_ndjson(&root.join("frame-ledger.ndjson"), &first.records)?;
    render_animation_png_sequence(&raw_path, &frames_dir, first.records.len())?;
    verify_png_sequence(&frames_dir, first.records.len(), 6)?;
    render_animation_video(&raw_path, &root.join("animation.mp4"))?;
    render_timeline_contact_sheet(
        &raw_path,
        &root.join("timeline-contact-sheet.png"),
        first.records.len(),
    )?;

    let library = PoseLibrary::reference().map_err(anyhow::Error::msg)?;
    let manifest = AnimationManifest {
        schema_version: 2,
        generator: "wizard-avatar-pose-evidence-rust-v4",
        source_git_sha: source_git_sha()?,
        simulation_fps: 60,
        frame_width: WIDTH,
        frame_height: HEIGHT,
        frame_count: first.records.len(),
        catalog_records: 80,
        unique_geometries: library.pose_ids().count(),
        aliases: library.alias_count(),
        rust_clip_count: POSE_CLIPS.len(),
        authored_transition_count: first.authored_transitions,
        newsroom_semantic_pose_count: first.newsroom_semantic_poses,
        deterministic_replay: deterministic,
        adaptive_decode_parity: first
            .records
            .iter()
            .all(|record| record.source_frame_sha256 == record.decoded_frame_sha256),
        presentation_parity: first.records.iter().all(|record| {
            record.presentation_accepted
                && record.decoded_frame_sha256 == record.presented_frame_sha256
        }),
        pass_one_stream_sha256: first_stream_sha256,
        pass_two_stream_sha256: second_stream_sha256,
        quality: first.quality,
        frame_ledger: "frame-ledger.ndjson",
        video: "animation.mp4",
        timeline_contact_sheet: "timeline-contact-sheet.png",
    };
    write_json(&root.join("manifest.json"), &manifest)?;
    std::fs::remove_file(raw_path)?;

    if !deterministic {
        bail!("the two Rust animation passes produced different frame hashes");
    }
    if !manifest.adaptive_decode_parity || !manifest.presentation_parity {
        bail!("adaptive decode or presentation parity failed");
    }
    if !manifest.quality.passed() {
        bail!(
            "{} animation frame-quality failures remain",
            manifest.quality.failures.len()
        );
    }
    println!(
        "verified {} animation frames twice across {} authored transitions and {} Rust clips",
        manifest.frame_count, manifest.authored_transition_count, manifest.rust_clip_count
    );
    Ok(())
}

fn source_git_sha() -> anyhow::Result<String> {
    if let Ok(sha) = std::env::var("WIZARD_EVIDENCE_GIT_SHA") {
        return validate_git_sha(sha);
    }
    let output = Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .context("failed to resolve evidence source Git SHA")?;
    if !output.status.success() {
        bail!("git rev-parse HEAD failed with {}", output.status);
    }
    validate_git_sha(String::from_utf8(output.stdout)?.trim().to_string())
}

fn validate_git_sha(sha: String) -> anyhow::Result<String> {
    if sha.len() != 40 || !sha.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        bail!("evidence source Git SHA must be 40 hexadecimal characters");
    }
    Ok(sha.to_ascii_lowercase())
}

fn run_animation_pass(raw_path: Option<&Path>) -> anyhow::Result<AnimationPass> {
    let mut recorder = AnimationRecorder::new(raw_path)?;
    run_clip_scenarios(&mut recorder)?;
    let authored_transitions = run_authored_transition_matrix(&mut recorder)?;
    let newsroom_semantic_poses = run_newsroom_semantic_matrix(&mut recorder)?;
    run_interruption_scenario(&mut recorder)?;
    recorder.finish(authored_transitions, newsroom_semantic_poses)
}

fn run_newsroom_semantic_matrix(recorder: &mut AnimationRecorder) -> anyhow::Result<usize> {
    let catalogs = NewsroomCatalogs::embedded().map_err(anyhow::Error::msg)?;
    for pose in &catalogs.poses.poses {
        let binding = runtime_binding_for_pose(pose).map_err(anyhow::Error::msg)?;
        let command = NewsCommand::from_wire_name(&pose.semantic_intent)
            .ok_or_else(|| anyhow::anyhow!("unknown semantic intent {}", pose.semantic_intent))?;
        let seed = catalogs
            .poses
            .poses
            .iter()
            .filter(|candidate| candidate.semantic_intent == pose.semantic_intent)
            .position(|candidate| candidate.pose_id == pose.pose_id)
            .ok_or_else(|| anyhow::anyhow!("missing variant index for {}", pose.pose_id))?
            as u64;
        let mut runtime = AvatarRuntime::default();
        let mut frame_source = ProceduralWizardFrameSource::new(WIDTH, HEIGHT, 60.0);
        let cue = NewsPerformanceCueV1 {
            schema_version: NEWSROOM_CUE_SCHEMA_VERSION.to_string(),
            cue_id: format!("evidence-{}", pose.pose_id),
            sequence: 1,
            program: NewsProgram::GeneralNews,
            command,
            target: None,
            count: (command == NewsCommand::Count).then_some(match pose.pose_id.as_str() {
                "count_one" => 1,
                "count_two" => 2,
                _ => 3,
            }),
            intensity: UnitInterval::from_permille(700).expect("constant"),
            sensitivity: StorySensitivity::Light,
            start_ms: 0,
            duration_ms: 320,
            generation: 1,
            reduced_motion: false,
            speech_line_id: None,
            graphic_id: (command == NewsCommand::RevealGraphic)
                .then(|| "evidence-graphic".to_string()),
            source_id: (command == NewsCommand::RevealSource)
                .then(|| "evidence-source".to_string()),
            seed: Some(seed),
        };
        let receipt = runtime
            .apply_newsroom_cue(cue)
            .map_err(anyhow::Error::msg)?;
        if receipt.performance.semantic_pose_id != pose.pose_id
            || receipt.performance.internal_pose_id != binding.internal_pose_id
        {
            bail!(
                "semantic evidence selection mismatch for {}: {:?}",
                pose.pose_id,
                receipt.performance
            );
        }
        let transition_ticks = (u64::from(receipt.performance.transition_ms) * 60).div_ceil(1_000);
        let restore_ticks = transition_ticks_for(
            &binding.internal_pose_id,
            "front_idle",
            DEFAULT_POSE_TRANSITION_TICKS,
        );
        let scenario_id = format!("newsroom-semantic-{}", pose.pose_id);
        for _ in 0..=transition_ticks + 20 + u64::from(restore_ticks) {
            runtime.step_tick();
            recorder.capture(&scenario_id, &scenario_id, &runtime, &mut frame_source)?;
        }
    }
    Ok(catalogs.poses.poses.len())
}

fn run_clip_scenarios(recorder: &mut AnimationRecorder) -> anyhow::Result<()> {
    for (clip_index, clip) in POSE_CLIPS.iter().enumerate() {
        let mut runtime = AvatarRuntime::default();
        let mut frame_source = ProceduralWizardFrameSource::new(WIDTH, HEIGHT, 60.0);
        if matches!(clip.id, "ground_walk" | "ground_run") {
            apply_command(&mut runtime, "move", json!({"x":2.5,"z":5.0,"speed":1.1}))?;
        }
        apply_command(
            &mut runtime,
            "expression",
            json!({"expression": if clip_index % 2 == 0 { "focused" } else { "confident" }}),
        )?;
        apply_command(&mut runtime, "pose_clip", json!({"clip_id":clip.id}))?;
        let mut previous_pose = "front_idle";
        let mut clip_ticks = 0_u64;
        for step in clip.steps {
            let transition_ticks = transition_ticks_for(
                previous_pose,
                step.pose_id,
                step.effective_transition_ticks(),
            );
            clip_ticks += u64::from(step.hold_ticks.max(transition_ticks));
            previous_pose = step.pose_id;
        }
        if !clip.loopable {
            clip_ticks += u64::from(transition_ticks_for(
                previous_pose,
                "front_idle",
                DEFAULT_POSE_TRANSITION_TICKS,
            ));
        }
        clip_ticks += 24;
        for tick in 0..clip_ticks {
            if tick == clip_ticks / 3 && matches!(clip.id, "conversation" | "explain") {
                apply_command(
                    &mut runtime,
                    "speak",
                    json!({"text":"Every frame is checked.","duration_ms":900,"speech_id":format!("evidence-{clip_index}")}),
                )?;
            }
            runtime.step_tick();
            recorder.capture(
                &format!("clip-{}", clip.id),
                &format!("clip-{}", clip.id),
                &runtime,
                &mut frame_source,
            )?;
        }
    }
    Ok(())
}

fn run_authored_transition_matrix(recorder: &mut AnimationRecorder) -> anyhow::Result<usize> {
    let library = PoseLibrary::reference().map_err(anyhow::Error::msg)?;
    let imported = library
        .pose_ids()
        .filter_map(|pose_id| {
            let pose = library.for_id(pose_id)?;
            pose.motion.candidate_id.as_ref().map(|_| {
                (
                    pose.id.clone(),
                    pose.motion.authored_transition_neighbors.clone(),
                )
            })
        })
        .collect::<Vec<_>>();
    let mut transitions = 0;
    for (target, neighbors) in imported {
        for source in neighbors {
            let mut runtime = AvatarRuntime::default();
            let mut frame_source = ProceduralWizardFrameSource::new(WIDTH, HEIGHT, 60.0);
            apply_command(
                &mut runtime,
                "pose",
                json!({"pose_id":source,"transition_ms":1}),
            )?;
            let source_entry_ticks = transition_ticks_for("front_idle", &source, 1);
            for _ in 0..=source_entry_ticks {
                runtime.step_tick();
            }
            apply_command(
                &mut runtime,
                "pose",
                json!({"pose_id":target,"transition_ms":240}),
            )?;
            let transition_id = format!("matrix-{source}-to-{target}");
            let transition_ticks = transition_ticks_for(&source, &target, 15);
            for _ in 0..=transition_ticks + 3 {
                runtime.step_tick();
                recorder.capture(
                    "authored-transition-matrix",
                    &transition_id,
                    &runtime,
                    &mut frame_source,
                )?;
            }
            transitions += 1;
        }
    }
    if transitions < 100 {
        bail!("authored transition matrix is unexpectedly small: {transitions}");
    }
    Ok(transitions)
}

fn run_interruption_scenario(recorder: &mut AnimationRecorder) -> anyhow::Result<()> {
    let mut runtime = AvatarRuntime::default();
    let mut frame_source = ProceduralWizardFrameSource::new(WIDTH, HEIGHT, 60.0);
    apply_command(
        &mut runtime,
        "pose_clip",
        json!({"clip_id":"hover_flap","loop":true}),
    )?;
    let mut started_clips = BTreeSet::new();
    for tick in 0..420 {
        match tick {
            24 => apply_command(&mut runtime, "pose_clip", json!({"clip_id":"staff_combo"}))?,
            100 => apply_command(
                &mut runtime,
                "pose_clip",
                json!({"clip_id":"reaction_recover"}),
            )?,
            180 => apply_command(&mut runtime, "pose_clip", json!({"clip_id":"conversation"}))?,
            205 => apply_command(
                &mut runtime,
                "speak",
                json!({"text":"Interruptions stay coherent.","duration_ms":1100,"speech_id":"interrupt-evidence"}),
            )?,
            250 => apply_command(
                &mut runtime,
                "pose",
                json!({"pose_id":"front_point_direct_staff_held","transition_ms":180,"duration_ms":500,"restore_pose_id":"front_idle"}),
            )?,
            320 => apply_command(
                &mut runtime,
                "expression",
                json!({"expression":"surprised"}),
            )?,
            _ => {}
        }
        runtime.step_tick();
        if runtime.current_state().pose_clip_step.is_some() {
            if let Some(clip_id) = &runtime.current_state().pose_clip_id {
                started_clips.insert(clip_id.clone());
            }
        }
        recorder.capture(
            "interrupt-replace-restore",
            "interrupt-replace-restore",
            &runtime,
            &mut frame_source,
        )?;
    }
    for expected in [
        "hover_flap",
        "staff_combo",
        "reaction_recover",
        "conversation",
    ] {
        if !started_clips.contains(expected) {
            bail!("interruption scenario never started {expected}");
        }
    }
    Ok(())
}

fn apply_command(
    runtime: &mut AvatarRuntime,
    command_type: &str,
    payload: Value,
) -> anyhow::Result<()> {
    let result = runtime.apply_command(WizardCommand::new(command_type, payload));
    if result.ok {
        Ok(())
    } else {
        bail!("{command_type} command failed: {}", result.message)
    }
}

fn hash_stream(hashes: &[String]) -> String {
    let mut digest = Sha256::new();
    for hash in hashes {
        digest.update(hash.as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

fn write_ndjson(path: &Path, records: &[AnimationFrameRecord]) -> anyhow::Result<()> {
    let mut writer = BufWriter::new(File::create(path)?);
    for record in records {
        serde_json::to_writer(&mut writer, record)?;
        writer.write_all(b"\n")?;
    }
    writer.flush()?;
    Ok(())
}

fn render_animation_png_sequence(raw: &Path, frames: &Path, count: usize) -> anyhow::Result<()> {
    let pattern = frames.join("%06d.png");
    run_ffmpeg(&[
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        "480x270",
        "-framerate",
        "60",
        "-i",
        path_text(raw)?,
        "-frames:v",
        &count.to_string(),
        "-start_number",
        "0",
        path_text(&pattern)?,
    ])
}

fn render_animation_video(raw: &Path, output: &Path) -> anyhow::Result<()> {
    run_ffmpeg(&[
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        "480x270",
        "-framerate",
        "60",
        "-i",
        path_text(raw)?,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        path_text(output)?,
    ])
}

fn render_timeline_contact_sheet(raw: &Path, output: &Path, count: usize) -> anyhow::Result<()> {
    let sampled = count.div_ceil(60);
    let rows = sampled.div_ceil(5).max(1);
    let filter = format!("fps=1,scale=240:135:flags=neighbor,tile=5x{rows}");
    run_ffmpeg(&[
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        "480x270",
        "-framerate",
        "60",
        "-i",
        path_text(raw)?,
        "-vf",
        &filter,
        "-frames:v",
        "1",
        path_text(output)?,
    ])
}

fn cell_rgb_bytes(cells: &[u8]) -> Vec<u8> {
    cells
        .chunks_exact(4)
        .flat_map(|cell| [cell[1], cell[2], cell[3]])
        .collect()
}

fn render_png_sequence(raw: &Path, frames: &Path, count: usize) -> anyhow::Result<()> {
    let pattern = frames.join("%04d.png");
    run_ffmpeg(&[
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        "480x270",
        "-framerate",
        &FPS.to_string(),
        "-i",
        path_text(raw)?,
        "-frames:v",
        &count.to_string(),
        "-start_number",
        "0",
        path_text(&pattern)?,
    ])
}

fn verify_png_sequence(frames: &Path, count: usize, digits: usize) -> anyhow::Result<()> {
    let actual_count = std::fs::read_dir(frames)?
        .filter_map(Result::ok)
        .filter(|entry| {
            entry
                .path()
                .extension()
                .is_some_and(|extension| extension == "png")
        })
        .count();
    if actual_count != count {
        bail!(
            "PNG sequence count mismatch in {}: {actual_count} != {count}",
            frames.display()
        );
    }
    for frame_index in 0..count {
        let path = frames.join(format!("{:0width$}.png", frame_index, width = digits));
        if !path.is_file() {
            bail!("missing rendered PNG {}", path.display());
        }
    }
    Ok(())
}

fn render_contact_sheet(raw: &Path, output: &Path, count: usize) -> anyhow::Result<()> {
    let rows = count.div_ceil(5);
    let filter = format!("scale=480:270:flags=neighbor,tile=5x{rows}");
    run_ffmpeg(&[
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        "480x270",
        "-framerate",
        &FPS.to_string(),
        "-i",
        path_text(raw)?,
        "-vf",
        &filter,
        "-frames:v",
        "1",
        path_text(output)?,
    ])
}

fn run_ffmpeg(arguments: &[&str]) -> anyhow::Result<()> {
    let status = Command::new("ffmpeg")
        .arg("-y")
        .arg("-loglevel")
        .arg("error")
        .args(arguments)
        .status()
        .context("failed to launch ffmpeg")?;
    if !status.success() {
        bail!("ffmpeg failed with {status}");
    }
    Ok(())
}

fn write_json(path: &Path, value: &impl Serialize) -> anyhow::Result<()> {
    let mut bytes = serde_json::to_vec_pretty(value)?;
    bytes.push(b'\n');
    std::fs::write(path, bytes).with_context(|| format!("failed to write {}", path.display()))
}

fn reset_dir(path: &Path) -> anyhow::Result<()> {
    if path.exists() {
        std::fs::remove_dir_all(path)?;
    }
    create_dir_all(path)?;
    Ok(())
}

fn path_text(path: &Path) -> anyhow::Result<&str> {
    path.to_str()
        .ok_or_else(|| anyhow::anyhow!("path is not UTF-8: {}", path.display()))
}

fn evidence_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../evidence/pose-library-expansion/rust-v4")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ledger_record_proves_decode_presentation_anchor_and_contact_parity() {
        let mut recorder = AnimationRecorder::new(None).expect("recorder");
        let mut runtime = AvatarRuntime::default();
        let mut source = ProceduralWizardFrameSource::new(WIDTH, HEIGHT, 60.0);
        runtime.step_tick();
        recorder
            .capture("test", "test", &runtime, &mut source)
            .expect("capture");
        let record = recorder.records.first().expect("record");
        assert_eq!(record.anchors.len(), AnchorId::REQUIRED.len());
        assert_eq!(record.source_frame_sha256, record.decoded_frame_sha256);
        assert_eq!(record.decoded_frame_sha256, record.presented_frame_sha256);
        assert!(record.presentation_accepted);
        assert_eq!(record.presented_sequence, 0);
        assert_eq!(record.stream_sequence, 0);
        assert_eq!(
            record.contacts.planted_foot,
            runtime.current_state().planted_foot
        );
    }
}
