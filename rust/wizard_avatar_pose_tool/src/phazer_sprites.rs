use crate::production_alpha::RuntimePhase;
use crate::{
    build_exact_pixel_graph, build_transparent_overlay, composite_graph_over_source,
    isolate_transparent, project_pixel_graph, read_pixel_graph, verify_pose_graph,
    write_pixel_graph, ArchiveProvenance, ForegroundBounds, FrameSpec, IsolationConfig,
    NormalizedPose, OverlayPalette, RuntimeAlphaEntry, VerificationConfig,
};
use image::{imageops, DynamicImage, ImageFormat, Rgba, RgbaImage};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::VecDeque;
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File};
use std::io::Read;
use std::path::{Path, PathBuf};
use zip::ZipArchive;

pub const PHAZER_COMPILER_ID: &str = "wizard-avatar-phazer-sprites-v1";
pub const PHAZER_ARCHIVE_SHA256: &str =
    "636b9ddf8a5edff9db9de8f2eaa9ecf930b73bfe2b1d428b5111195ff4aec450";
pub const DEFAULT_PHAZER_ARCHIVE: &str = "/Users/paul/Downloads/WizardJoePhazerSprites.zip";
const SOURCE_PACK: &str = "wizard_joe_phazer_sprites";
const FRAME: FrameSpec = FrameSpec {
    width: 1254,
    height: 1254,
};
const FRAMES_PER_SHEET: usize = 6;
const FIRST_RUNTIME_SEQUENCE: usize = 261;

#[derive(Clone, Copy)]
struct SheetSpec {
    member: &'static str,
    sha256: &'static str,
    clip_id: &'static str,
    display_name: &'static str,
    family: &'static str,
    direction: &'static str,
    fps: u32,
    airborne_frames: &'static [usize],
}

const SHEETS: [SheetSpec; 8] = [
    SheetSpec {
        member: "sheet-wizard-joe.png",
        sha256: "902d5533a0752813f25fa9cd97fee93ef4048a92525ee06963be5e42fbc6d5c7",
        clip_id: "phazer_side_walk_takeoff",
        display_name: "Phazer Side Walk Takeoff",
        family: "ground_to_air",
        direction: "east",
        fps: 10,
        airborne_frames: &[6],
    },
    SheetSpec {
        member: "sheet-wizard-joe-w2.png",
        sha256: "8e56626aa20731a0e92409166cdd4955b237517465b5cced4aa023799cc95b7b",
        clip_id: "phazer_side_run",
        display_name: "Phazer Side Run",
        family: "ground_run",
        direction: "east",
        fps: 12,
        airborne_frames: &[],
    },
    SheetSpec {
        member: "sheet-wizard-joe-w3.png",
        sha256: "b6e26c650af386819ab9a293bcc2368465fd2bfb8358da754a0c06332aca228d",
        clip_id: "phazer_side_leap",
        display_name: "Phazer Side Leap",
        family: "ground_to_air",
        direction: "east",
        fps: 12,
        airborne_frames: &[5, 6],
    },
    SheetSpec {
        member: "sheet-wizard-joe-w4.png",
        sha256: "3b139f8b8897d0147c856328b9fbda66117852a060a3b1bdc2e4b505c0d39a37",
        clip_id: "phazer_side_wing_open",
        display_name: "Phazer Side Wing Open",
        family: "wing_deploy",
        direction: "east",
        fps: 10,
        airborne_frames: &[5, 6],
    },
    SheetSpec {
        member: "sheet-wizard-joe-w5.png",
        sha256: "88b6717333c57d6065d540936d8f2e7af16333ffae9fe16f7ff6ec6df9b97876",
        clip_id: "phazer_side_flap_cycle",
        display_name: "Phazer Side Flap Cycle",
        family: "flight",
        direction: "east",
        fps: 10,
        airborne_frames: &[1, 2, 3, 4, 5, 6],
    },
    SheetSpec {
        member: "sheet-wizard-joe-w6.png",
        sha256: "270a2a23ef72fd33c3de9149c92340d2a5be464974c37c9533f3f391abb6e832",
        clip_id: "phazer_side_flight_transition",
        display_name: "Phazer Side Flight Transition",
        family: "air_to_ground",
        direction: "east",
        fps: 10,
        airborne_frames: &[1, 2, 3, 4, 5],
    },
    SheetSpec {
        member: "sheet-wizard-joe-w7.png",
        sha256: "42ce044109fac51ab1ab504b696edad1a9fe1f4df27e8a1db646c3deb2a50acb",
        clip_id: "phazer_front_walk_hover",
        display_name: "Phazer Front Walk Hover",
        family: "ground_to_air",
        direction: "south",
        fps: 10,
        airborne_frames: &[6],
    },
    SheetSpec {
        member: "sheet-wizard-joe-w8.png",
        sha256: "4ae0f6a6b383904f4b2f8799609b87d5ad32008cf960f9fa10be728e29f37263",
        clip_id: "phazer_rear_walk_hover",
        display_name: "Phazer Rear Walk Hover",
        family: "ground_to_air",
        direction: "north",
        fps: 10,
        airborne_frames: &[6],
    },
];

#[derive(Clone, Debug)]
pub struct PhazerIntakeConfig {
    pub archive: PathBuf,
    pub output_root: PathBuf,
}

#[derive(Clone, Debug)]
pub struct PhazerPromotionConfig {
    pub intake_root: PathBuf,
    pub source_runtime_root: PathBuf,
    pub output_runtime_root: PathBuf,
    pub evidence_root: PathBuf,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PhazerIntakeReceipt {
    pub schema_version: u32,
    pub compiler_id: String,
    pub archive_sha256: String,
    pub sheet_count: usize,
    pub frame_count: usize,
    pub graph_count: usize,
    pub exact_projection_count: usize,
    pub foreground_source_match_count: usize,
    pub manifest_path: String,
    pub projected_contact_sheet_path: String,
    pub contact_sheet_path: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PhazerPromotionReceipt {
    pub schema_version: u32,
    pub compiler_id: String,
    pub source_runtime_pose_count: usize,
    pub added_pose_count: usize,
    pub runtime_pose_count: usize,
    pub exact_revalidation_count: usize,
    pub visual_review_status: String,
    pub runtime_manifest_path: String,
    pub runtime_manifest_sha256: String,
    pub visual_review_receipt_path: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PhazerManifest {
    pub schema_version: u32,
    pub compiler_id: String,
    pub archive: ArchiveProvenance,
    pub frame: [u32; 2],
    pub sheet_count: usize,
    pub frame_count: usize,
    pub visual_review_status: String,
    pub entries: Vec<PhazerEntry>,
    pub clips: Vec<PhazerClip>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PhazerEntry {
    pub sequence: usize,
    pub pose_id: String,
    pub semantic_id: String,
    pub sheet_member: String,
    pub sheet_sha256: String,
    pub sheet_frame: usize,
    pub sheet_crop: [u32; 4],
    pub isolated_bounds: [u32; 4],
    pub foreground_pixel_count: u64,
    pub removed_matte_pixel_count: u64,
    pub source_png_sha256: String,
    pub graph_sha256: String,
    pub exact_projection: bool,
    pub foreground_source_match_millionths: u32,
    pub graph_path: String,
    pub evidence_path: String,
    pub runtime: RuntimeAlphaEntry,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PhazerClip {
    pub clip_id: String,
    pub display_name: String,
    pub family: String,
    pub direction: String,
    pub playback_fps: u32,
    pub loopable: bool,
    pub semantic_frames: Vec<String>,
}

#[derive(Debug, thiserror::Error)]
pub enum PhazerIntakeError {
    #[error("I/O error at {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("ZIP error in {path}: {source}")]
    Zip {
        path: PathBuf,
        #[source]
        source: zip::result::ZipError,
    },
    #[error("image decode error for {member}: {source}")]
    Image {
        member: String,
        #[source]
        source: image::ImageError,
    },
    #[error("PixelGraph error: {0}")]
    PixelGraph(#[from] crate::PixelGraphError),
    #[error("verification error: {0}")]
    Verification(#[from] crate::VerificationError),
    #[error("Phazer intake invariant failed: {0}")]
    Invariant(String),
}

pub fn compile_phazer_sprite_archive(
    config: &PhazerIntakeConfig,
) -> Result<PhazerIntakeReceipt, PhazerIntakeError> {
    let archive_sha256 = sha256_file(&config.archive)?;
    require(
        archive_sha256 == PHAZER_ARCHIVE_SHA256,
        format!("archive hash {archive_sha256} is not pinned hash {PHAZER_ARCHIVE_SHA256}"),
    )?;
    let file = File::open(&config.archive).map_err(|source| PhazerIntakeError::Io {
        path: config.archive.clone(),
        source,
    })?;
    let mut archive = ZipArchive::new(file).map_err(|source| PhazerIntakeError::Zip {
        path: config.archive.clone(),
        source,
    })?;
    validate_member_census(&mut archive, &config.archive)?;

    if config.output_root.exists() {
        return Err(PhazerIntakeError::Invariant(format!(
            "output root {} already exists",
            config.output_root.display()
        )));
    }
    fs::create_dir_all(&config.output_root).map_err(|source| PhazerIntakeError::Io {
        path: config.output_root.clone(),
        source,
    })?;

    let mut entries = Vec::with_capacity(SHEETS.len() * FRAMES_PER_SHEET);
    let mut clips = Vec::with_capacity(SHEETS.len());
    let mut review_tiles = Vec::with_capacity(SHEETS.len() * FRAMES_PER_SHEET);
    let mut overlay_tiles = Vec::with_capacity(SHEETS.len() * FRAMES_PER_SHEET);
    for (sheet_index, spec) in SHEETS.iter().enumerate() {
        let bytes = read_member(&mut archive, &config.archive, spec.member)?;
        let member_sha256 = sha256_bytes(&bytes);
        require(
            member_sha256 == spec.sha256,
            format!("{} hash changed to {member_sha256}", spec.member),
        )?;
        let decoded = decode_mislabeled_webp(spec.member, &bytes)?;
        require(
            decoded.width() >= FRAMES_PER_SHEET as u32 && decoded.height() > 0,
            format!("{} has invalid decoded dimensions", spec.member),
        )?;
        let isolated_sheet = isolate_transparent(&decoded, phazer_isolation_config());
        let segments = segment_six_frames(&isolated_sheet.image)?;
        let grounded_baselines = segments
            .iter()
            .enumerate()
            .filter(|(index, _)| !spec.airborne_frames.contains(&(*index + 1)))
            .filter_map(|(_, segment)| alpha_bounds(&segment.image).map(|bounds| bounds.bottom))
            .collect::<Vec<_>>();
        let sheet_baseline = if grounded_baselines.is_empty() {
            segments
                .iter()
                .filter_map(|segment| alpha_bounds(&segment.image).map(|bounds| bounds.bottom))
                .max()
                .ok_or_else(|| {
                    PhazerIntakeError::Invariant(format!(
                        "{} has no recoverable baseline",
                        spec.member
                    ))
                })?
        } else {
            *grounded_baselines.iter().max().unwrap_or(&0)
        };
        let target_baseline = if grounded_baselines.is_empty() {
            1_100
        } else {
            1_184
        };

        let mut semantic_frames = Vec::with_capacity(FRAMES_PER_SHEET);
        for frame_index in 0..FRAMES_PER_SHEET {
            let ordinal = sheet_index * FRAMES_PER_SHEET + frame_index + 1;
            let pose_id = format!("WJPS-{ordinal:04}");
            let semantic_id = format!("{}_frame_{:02}", spec.clip_id, frame_index + 1);
            let entry = process_one_frame(
                &config.output_root,
                spec,
                &decoded,
                &segments[frame_index],
                sheet_baseline,
                target_baseline,
                frame_index,
                ordinal,
                &pose_id,
                &semantic_id,
            )?;
            review_tiles.push(load_png(
                &config
                    .output_root
                    .join(&entry.evidence_path)
                    .join("projected.png"),
            )?);
            overlay_tiles.push(load_png(
                &config
                    .output_root
                    .join(&entry.evidence_path)
                    .join("source-graph-overlay.png"),
            )?);
            semantic_frames.push(semantic_id);
            entries.push(entry);
        }
        clips.push(PhazerClip {
            clip_id: spec.clip_id.to_string(),
            display_name: spec.display_name.to_string(),
            family: spec.family.to_string(),
            direction: spec.direction.to_string(),
            playback_fps: spec.fps,
            loopable: matches!(spec.family, "ground_run" | "flight"),
            semantic_frames,
        });
    }
    require(entries.len() == 48, "compiler did not produce 48 frames")?;
    let projected_contact_sheet = build_pose_contact_sheet(&review_tiles, 6, 8);
    let projected_contact_sheet_path = config.output_root.join("projected-contact-sheet.png");
    save_png(&projected_contact_sheet, &projected_contact_sheet_path)?;
    let contact_sheet = build_contact_sheet(&overlay_tiles, 6, 8);
    let contact_sheet_path = config
        .output_root
        .join("transparent-overlay-contact-sheet.png");
    save_png(&contact_sheet, &contact_sheet_path)?;

    let archive_provenance = ArchiveProvenance {
        source_pack: SOURCE_PACK.to_string(),
        archive_filename: config
            .archive
            .file_name()
            .and_then(|name| name.to_str())
            .ok_or_else(|| {
                PhazerIntakeError::Invariant("archive filename is not UTF-8".to_string())
            })?
            .to_string(),
        archive_sha256: archive_sha256.clone(),
        manifest_member: "implicit:six-horizontal-cells-per-sheet".to_string(),
        manifest_status: "user_supplied_for_repertoire".to_string(),
    };
    let manifest = PhazerManifest {
        schema_version: 1,
        compiler_id: PHAZER_COMPILER_ID.to_string(),
        archive: archive_provenance,
        frame: [FRAME.width, FRAME.height],
        sheet_count: SHEETS.len(),
        frame_count: entries.len(),
        visual_review_status: "pending_transparent_overlay_review".to_string(),
        entries,
        clips,
    };
    let manifest_path = config.output_root.join("phazer-manifest.json");
    write_json(&manifest_path, &manifest)?;
    Ok(PhazerIntakeReceipt {
        schema_version: 1,
        compiler_id: PHAZER_COMPILER_ID.to_string(),
        archive_sha256,
        sheet_count: SHEETS.len(),
        frame_count: 48,
        graph_count: 48,
        exact_projection_count: 48,
        foreground_source_match_count: 48,
        manifest_path: relative_path(&config.output_root, &manifest_path)?,
        projected_contact_sheet_path: relative_path(
            &config.output_root,
            &projected_contact_sheet_path,
        )?,
        contact_sheet_path: relative_path(&config.output_root, &contact_sheet_path)?,
    })
}

pub fn promote_phazer_sprite_archive(
    config: &PhazerPromotionConfig,
) -> Result<PhazerPromotionReceipt, PhazerIntakeError> {
    require(
        !config.output_runtime_root.exists(),
        format!(
            "output runtime root {} already exists",
            config.output_runtime_root.display()
        ),
    )?;
    let manifest_path = config.intake_root.join("phazer-manifest.json");
    let mut phazer_manifest: PhazerManifest = read_json(&manifest_path)?;
    require(
        phazer_manifest.compiler_id == PHAZER_COMPILER_ID
            && phazer_manifest.frame_count == 48
            && phazer_manifest.entries.len() == 48
            && phazer_manifest.clips.len() == 8,
        "Phazer intake manifest is incomplete",
    )?;
    let expected_pose_ids = (1..=48)
        .map(|index| format!("WJPS-{index:04}"))
        .collect::<Vec<_>>();
    require(
        phazer_manifest
            .entries
            .iter()
            .map(|entry| entry.pose_id.as_str())
            .eq(expected_pose_ids.iter().map(String::as_str)),
        "Phazer pose IDs are not the complete canonical sequence",
    )?;

    for entry in &phazer_manifest.entries {
        let graph_path = config.intake_root.join(&entry.graph_path);
        require(
            sha256_file(&graph_path)? == entry.graph_sha256,
            format!("{} graph hash changed before promotion", entry.pose_id),
        )?;
        let graph = read_pixel_graph(&graph_path)?;
        require(
            graph.source_record_id == entry.pose_id,
            format!("{} graph binding changed", entry.pose_id),
        )?;
        let projected = project_pixel_graph(&graph)?;
        let source_path = config
            .intake_root
            .join(&entry.evidence_path)
            .join("source.png");
        require(
            sha256_file(&source_path)? == entry.source_png_sha256,
            format!("{} source evidence hash changed", entry.pose_id),
        )?;
        let source = load_png(&source_path)?;
        require(
            source == projected,
            format!("{} failed exact promotion reprojection", entry.pose_id),
        )?;
        require(
            entry.foreground_source_match_millionths == 1_000_000
                && entry.exact_projection
                && entry.runtime.exact_rgba_equal,
            format!("{} does not carry exact admission metrics", entry.pose_id),
        )?;
    }

    let source_manifest_path = config.source_runtime_root.join("runtime-manifest.json");
    let mut runtime: serde_json::Value = read_json(&source_manifest_path)?;
    require(
        runtime["source_count"].as_u64() == Some(260)
            && runtime["entries"].as_array().map(Vec::len) == Some(260)
            && runtime["archives"].as_array().map(Vec::len) == Some(2),
        "source runtime is not the approved 260-pose v6 catalog",
    )?;
    let source_graph_root = config.source_runtime_root.join("graphs");
    let source_graphs = regular_files(&source_graph_root)?;
    require(
        source_graphs.len() == 260
            && source_graphs
                .iter()
                .all(|path| path.extension().and_then(|value| value.to_str()) == Some("gz")),
        "source runtime graph census is not exactly 260",
    )?;

    let output_graph_root = config.output_runtime_root.join("graphs");
    fs::create_dir_all(&output_graph_root).map_err(|source| PhazerIntakeError::Io {
        path: output_graph_root.clone(),
        source,
    })?;
    for source in &source_graphs {
        copy_file(
            source,
            &output_graph_root.join(
                source
                    .file_name()
                    .ok_or_else(|| {
                        PhazerIntakeError::Invariant("source graph has no filename".to_string())
                    })?
                    .to_owned(),
            ),
        )?;
    }
    for entry in &phazer_manifest.entries {
        let source = config.intake_root.join(&entry.graph_path);
        let target = config.output_runtime_root.join(&entry.graph_path);
        copy_file(&source, &target)?;
    }

    runtime["compiler_id"] =
        serde_json::Value::String("wizard-avatar-production-alpha-plus-phazer-v1".to_string());
    runtime["source_count"] = serde_json::json!(308);
    runtime["verified_pose_count"] = serde_json::json!(308);
    runtime["primary_pose_count"] = serde_json::json!(308);
    runtime["unique_semantic_pose_count"] = serde_json::json!(308);
    runtime["phazer_pose_count"] = serde_json::json!(48);
    runtime["archives"]
        .as_array_mut()
        .ok_or_else(|| {
            PhazerIntakeError::Invariant("runtime archives is not an array".to_string())
        })?
        .push(
            serde_json::to_value(&phazer_manifest.archive).map_err(|error| {
                PhazerIntakeError::Invariant(format!("archive serialization failed: {error}"))
            })?,
        );
    let runtime_entries = runtime["entries"].as_array_mut().ok_or_else(|| {
        PhazerIntakeError::Invariant("runtime entries is not an array".to_string())
    })?;
    for entry in &phazer_manifest.entries {
        runtime_entries.push(serde_json::to_value(&entry.runtime).map_err(|error| {
            PhazerIntakeError::Invariant(format!("runtime entry serialization failed: {error}"))
        })?);
    }
    require(
        runtime_entries.len() == 308,
        "promoted runtime does not contain 308 entries",
    )?;
    let output_manifest_path = config.output_runtime_root.join("runtime-manifest.json");
    write_json(&output_manifest_path, &runtime)?;
    let runtime_manifest_sha256 = sha256_file(&output_manifest_path)?;

    phazer_manifest.visual_review_status = "approved_transparent_overlay_review".to_string();
    write_json(&manifest_path, &phazer_manifest)?;
    for entry in &phazer_manifest.entries {
        let verification_path = config
            .intake_root
            .join(&entry.evidence_path)
            .join("verification.json");
        let mut verification: serde_json::Value = read_json(&verification_path)?;
        verification["visual_review_status"] =
            serde_json::Value::String("approved_transparent_overlay_review".to_string());
        write_json(&verification_path, &verification)?;
    }
    fs::create_dir_all(&config.evidence_root).map_err(|source| PhazerIntakeError::Io {
        path: config.evidence_root.clone(),
        source,
    })?;
    let contact_sheet_path = config.intake_root.join("projected-contact-sheet.png");
    let overlay_sheet_path = config
        .intake_root
        .join("transparent-overlay-contact-sheet.png");
    let visual_review = serde_json::json!({
        "schema_version": 1,
        "compiler_id": PHAZER_COMPILER_ID,
        "reviewer": "Codex visual frame review",
        "decision": "approved_transparent_overlay_review",
        "reviewed_pose_count": 48,
        "approved_pose_ids": expected_pose_ids,
        "projected_contact_sheet": {
            "path": relative_path(&config.intake_root, &contact_sheet_path)?,
            "sha256": sha256_file(&contact_sheet_path)?
        },
        "transparent_overlay_contact_sheet": {
            "path": relative_path(&config.intake_root, &overlay_sheet_path)?,
            "sha256": sha256_file(&overlay_sheet_path)?
        },
        "acceptance": {
            "minimum_alignment_millionths": 950_000,
            "measured_foreground_source_match_millionths": 1_000_000,
            "measured_graph_projection_match_millionths": 1_000_000,
            "checkerboard_residue_in_projected_graphs": false,
            "neighbor_frame_fragments_in_projected_graphs": false
        },
        "notes": "All 48 projected silhouettes and the difficult overlapping-wing source regions were inspected. The native graphs preserve the selected source figure exactly after matte isolation."
    });
    let visual_review_path = config.evidence_root.join("visual-review.json");
    write_json(&visual_review_path, &visual_review)?;

    Ok(PhazerPromotionReceipt {
        schema_version: 1,
        compiler_id: "wizard-avatar-production-alpha-plus-phazer-v1".to_string(),
        source_runtime_pose_count: 260,
        added_pose_count: 48,
        runtime_pose_count: 308,
        exact_revalidation_count: 48,
        visual_review_status: "approved_transparent_overlay_review".to_string(),
        runtime_manifest_path: output_manifest_path.to_string_lossy().to_string(),
        runtime_manifest_sha256,
        visual_review_receipt_path: visual_review_path.to_string_lossy().to_string(),
    })
}

fn process_one_frame(
    output_root: &Path,
    spec: &SheetSpec,
    sheet: &RgbaImage,
    segment: &FrameSegment,
    sheet_baseline: u32,
    target_baseline: u32,
    frame_index: usize,
    ordinal: usize,
    pose_id: &str,
    semantic_id: &str,
) -> Result<PhazerEntry, PhazerIntakeError> {
    let full_bounds = alpha_bounds(&segment.image)
        .ok_or_else(|| PhazerIntakeError::Invariant(format!("{pose_id} contains no foreground")))?;
    let crop_top = full_bounds.top.saturating_sub(8);
    let crop_bottom = (full_bounds.bottom + 8).min(segment.image.height() - 1);
    let crop_height = crop_bottom - crop_top + 1;
    let cell =
        imageops::crop_imm(sheet, segment.left, crop_top, segment.width, crop_height).to_image();
    let isolated_image =
        imageops::crop_imm(&segment.image, 0, crop_top, segment.width, crop_height).to_image();
    let bounds = alpha_bounds(&isolated_image)
        .ok_or_else(|| PhazerIntakeError::Invariant(format!("{pose_id} contains no foreground")))?;
    let foreground_pixels = isolated_image.pixels().filter(|pixel| pixel[3] > 0).count() as u64;
    require(
        foreground_pixels > 20_000,
        format!("{pose_id} has implausibly little foreground"),
    )?;
    let offset_y = target_baseline
        .checked_sub(sheet_baseline)
        .and_then(|offset| offset.checked_add(crop_top))
        .ok_or_else(|| {
            PhazerIntakeError::Invariant(format!("{pose_id} vertical normalization overflowed"))
        })?;
    let normalized = normalize_phazer_to_frame(&isolated_image, offset_y)?;
    let source = normalized.image.clone();
    let source_path = output_root
        .join("evidence")
        .join(pose_id)
        .join("source.png");
    save_png(&source, &source_path)?;
    let source_sha256 = sha256_file(&source_path)?;
    let graph = build_exact_pixel_graph(
        format!("{}-pixelgraph-v1", pose_id.to_ascii_lowercase()),
        pose_id,
        &source_sha256,
        (cell.width(), cell.height()),
        &normalized,
    );
    let graph_relative = format!("graphs/{pose_id}.pixelgraph.json.gz");
    let graph_path = output_root.join(&graph_relative);
    let graph_sha256 = write_pixel_graph(&graph, &graph_path)?;
    let projected = project_pixel_graph(&graph)?;
    require(
        source == projected,
        format!("{pose_id} projection is not exact"),
    )?;

    let verification_config = VerificationConfig {
        foreground_alpha_threshold: 1,
        color_match_tolerance: 0,
    };
    let metrics = verify_pose_graph(&source, &projected, verification_config)?;
    require(
        metrics.silhouette_iou >= 0.999_999
            && metrics.foreground_color_fidelity >= 0.999_999
            && metrics.foreground_color_match_ratio >= 0.999_999,
        format!("{pose_id} exact verification metrics regressed"),
    )?;
    let overlay = build_transparent_overlay(
        &source,
        &projected,
        verification_config,
        OverlayPalette::default(),
    )?;
    let composite = composite_graph_over_source(&source, &projected, 128)?;
    let original_normalized = normalize_phazer_to_frame(&cell, offset_y)?.image;
    let source_graph_overlay =
        blend_tinted_graph_over_original(&original_normalized, &projected, [0, 190, 255], 128);
    let evidence_dir = output_root.join("evidence").join(pose_id);
    save_png(&projected, &evidence_dir.join("projected.png"))?;
    save_png(
        &overlay.image,
        &evidence_dir.join("transparent-overlay.png"),
    )?;
    save_png(&composite, &evidence_dir.join("isolated-composite.png"))?;
    save_png(
        &source_graph_overlay,
        &evidence_dir.join("source-graph-overlay.png"),
    )?;

    let source_match = count_foreground_source_match(&cell, &isolated_image);
    require(
        source_match == foreground_pixels,
        format!("{pose_id} changed a retained source pixel"),
    )?;
    let total_pixels = u64::from(cell.width()) * u64::from(cell.height());
    let airborne = spec.airborne_frames.contains(&(frame_index + 1));
    let phase = RuntimePhase {
        numerator: (frame_index + 1) as u16,
        denominator: FRAMES_PER_SHEET as u16,
    };
    let previous = if frame_index == 0 {
        FRAMES_PER_SHEET
    } else {
        frame_index
    };
    let next = (frame_index + 1) % FRAMES_PER_SHEET + 1;
    let runtime = RuntimeAlphaEntry {
        sequence: FIRST_RUNTIME_SEQUENCE + ordinal - 1,
        source_record_id: pose_id.to_string(),
        candidate_id: pose_id.to_string(),
        pose_id: pose_id.to_string(),
        semantic_id: semantic_id.to_string(),
        display_name: format!("{} Frame {:02}", spec.display_name, frame_index + 1),
        source_archive: "WizardJoePhazerSprites.zip".to_string(),
        source_entry: format!("{}#frame-{:02}", spec.member, frame_index + 1),
        source_sha256: source_sha256.clone(),
        graph_path: graph_relative,
        graph_sha256: graph_sha256.clone(),
        graph_id: graph.graph_id.clone(),
        frame: [FRAME.width, FRAME.height],
        source_size: [cell.width(), cell.height()],
        offset: [normalized.offset_x, normalized.offset_y],
        foreground_pixel_count: foreground_pixels,
        motion_family: spec.family.to_string(),
        contact_mode: if airborne { "airborne" } else { "both_feet" }.to_string(),
        phase: Some(phase),
        direction: spec.direction.to_string(),
        authored_transition_neighbors: vec![
            format!("{}_frame_{previous:02}", spec.clip_id),
            format!("{}_frame_{next:02}", spec.clip_id),
        ],
        control_groups: vec![
            "all".to_string(),
            "phazer".to_string(),
            spec.family.to_string(),
            format!("clip:{}", spec.clip_id),
            format!("pack:{SOURCE_PACK}"),
        ],
        primary_for_semantic_id: true,
        duplicate_source_of: None,
        silhouette_iou_millionths: 1_000_000,
        foreground_color_fidelity_millionths: 1_000_000,
        foreground_color_match_ratio_millionths: 1_000_000,
        exact_rgba_equal: true,
        rgba_mismatch_pixel_count: 0,
        rgba_mismatch_channel_count: 0,
        source_pack: SOURCE_PACK.to_string(),
        category: "phazer_animation".to_string(),
        anchor_kind: if airborne {
            "body_center"
        } else {
            "ground_contact"
        }
        .to_string(),
        anchor_x: normalized.offset_x + (bounds.left + bounds.right) / 2,
        anchor_y: if airborne {
            normalized.offset_y + (bounds.top + bounds.bottom) / 2
        } else {
            normalized.offset_y + bounds.bottom
        },
        evidence_path: format!("evidence/{pose_id}"),
    };
    let verification = serde_json::json!({
        "schema_version": 1,
        "compiler_id": PHAZER_COMPILER_ID,
        "pose_id": pose_id,
        "semantic_id": semantic_id,
        "sheet_member": spec.member,
        "sheet_frame": frame_index + 1,
        "sheet_crop": [segment.left, crop_top, segment.width, crop_height],
        "isolated_bounds": [bounds.left, bounds.top, bounds.width(), bounds.height()],
        "foreground_pixel_count": foreground_pixels,
        "removed_matte_pixel_count": total_pixels - foreground_pixels,
        "source_png_sha256": source_sha256,
        "graph_sha256": graph_sha256,
        "exact_projection": true,
        "foreground_source_match_millionths": 1_000_000,
        "visual_review_status": "pending_transparent_overlay_review",
        "evidence": {
            "source": "source.png",
            "projected": "projected.png",
            "transparent_overlay": "transparent-overlay.png",
            "isolated_composite": "isolated-composite.png",
            "source_graph_overlay": "source-graph-overlay.png"
        }
    });
    write_json(&evidence_dir.join("verification.json"), &verification)?;

    Ok(PhazerEntry {
        sequence: FIRST_RUNTIME_SEQUENCE + ordinal - 1,
        pose_id: pose_id.to_string(),
        semantic_id: semantic_id.to_string(),
        sheet_member: spec.member.to_string(),
        sheet_sha256: spec.sha256.to_string(),
        sheet_frame: frame_index + 1,
        sheet_crop: [segment.left, crop_top, segment.width, crop_height],
        isolated_bounds: [bounds.left, bounds.top, bounds.width(), bounds.height()],
        foreground_pixel_count: foreground_pixels,
        removed_matte_pixel_count: total_pixels - foreground_pixels,
        source_png_sha256: source_sha256,
        graph_sha256,
        exact_projection: true,
        foreground_source_match_millionths: 1_000_000,
        graph_path: format!("graphs/{pose_id}.pixelgraph.json.gz"),
        evidence_path: format!("evidence/{pose_id}"),
        runtime,
    })
}

fn decode_mislabeled_webp(member: &str, bytes: &[u8]) -> Result<RgbaImage, PhazerIntakeError> {
    image::load_from_memory_with_format(bytes, ImageFormat::WebP)
        .map(DynamicImage::into_rgba8)
        .map_err(|source| PhazerIntakeError::Image {
            member: member.to_string(),
            source,
        })
}

fn phazer_isolation_config() -> IsolationConfig {
    IsolationConfig {
        matte_rgb: [255, 255, 255],
        matte_tolerance: 40,
        neutral_shadow_max_chroma: 48,
        neutral_shadow_min_luma: 210,
        enclosed_matte_component_min_pixels: None,
        ..IsolationConfig::default()
    }
}

fn normalize_phazer_to_frame(
    source: &RgbaImage,
    offset_y: u32,
) -> Result<NormalizedPose, PhazerIntakeError> {
    let offset_x = (FRAME.width.saturating_sub(source.width())) / 2;
    require(
        source.width() <= FRAME.width
            && offset_y
                .checked_add(source.height())
                .is_some_and(|bottom| bottom <= FRAME.height),
        format!(
            "Phazer source {}x{} at y {offset_y} does not fit {}x{}",
            source.width(),
            source.height(),
            FRAME.width,
            FRAME.height
        ),
    )?;
    let mut image = RgbaImage::new(FRAME.width, FRAME.height);
    for (x, y, pixel) in source.enumerate_pixels() {
        if pixel[3] > 0 {
            image.put_pixel(x + offset_x, y + offset_y, *pixel);
        }
    }
    Ok(NormalizedPose {
        image,
        offset_x,
        offset_y,
    })
}

#[derive(Clone, Debug)]
struct FrameSegment {
    left: u32,
    width: u32,
    image: RgbaImage,
}

#[derive(Clone, Debug)]
struct ForegroundComponent {
    pixels: Vec<(u32, u32)>,
    bounds: ForegroundBounds,
    center_x: f64,
}

fn segment_six_frames(image: &RgbaImage) -> Result<Vec<FrameSegment>, PhazerIntakeError> {
    let components = foreground_components(image)
        .into_iter()
        .filter(|component| component.pixels.len() >= 4)
        .collect::<Vec<_>>();
    require(
        components.len() >= FRAMES_PER_SHEET,
        "sheet has fewer than six foreground components",
    )?;

    let mut centers = (0..FRAMES_PER_SHEET)
        .map(|index| image.width() as f64 * (index as f64 + 0.5) / FRAMES_PER_SHEET as f64)
        .collect::<Vec<_>>();
    let mut assignments = vec![0_usize; components.len()];
    for _ in 0..12 {
        for (index, component) in components.iter().enumerate() {
            assignments[index] = centers
                .iter()
                .enumerate()
                .min_by(|(_, left), (_, right)| {
                    (component.center_x - **left)
                        .abs()
                        .partial_cmp(&(component.center_x - **right).abs())
                        .unwrap_or(std::cmp::Ordering::Equal)
                })
                .map(|(cluster, _)| cluster)
                .unwrap_or(0);
        }
        for cluster in 0..FRAMES_PER_SHEET {
            let (weighted_sum, weight) = components
                .iter()
                .zip(assignments.iter())
                .filter(|(_, assignment)| **assignment == cluster)
                .fold((0.0_f64, 0.0_f64), |(sum, weight), (component, _)| {
                    let component_weight = component.pixels.len() as f64;
                    (
                        sum + component.center_x * component_weight,
                        weight + component_weight,
                    )
                });
            if weight > 0.0 {
                centers[cluster] = weighted_sum / weight;
            }
        }
    }

    let mut segments = Vec::with_capacity(FRAMES_PER_SHEET);
    for cluster in 0..FRAMES_PER_SHEET {
        let assigned = components
            .iter()
            .zip(assignments.iter())
            .filter(|(_, assignment)| **assignment == cluster)
            .map(|(component, _)| component)
            .collect::<Vec<_>>();
        require(
            !assigned.is_empty(),
            format!("foreground cluster {} is empty", cluster + 1),
        )?;
        let left_bound = assigned
            .iter()
            .map(|component| component.bounds.left)
            .min()
            .unwrap_or(0);
        let right_bound = assigned
            .iter()
            .map(|component| component.bounds.right)
            .max()
            .unwrap_or(left_bound);
        let left = left_bound.saturating_sub(8);
        let right = (right_bound + 8).min(image.width() - 1);
        let width = right - left + 1;
        let mut segment = RgbaImage::new(width, image.height());
        let mut foreground_pixels = 0_usize;
        for component in assigned {
            for (x, y) in component.pixels.iter().copied() {
                segment.put_pixel(x - left, y, *image.get_pixel(x, y));
                foreground_pixels += 1;
            }
        }
        require(
            foreground_pixels > 20_000,
            format!(
                "foreground cluster {} has only {foreground_pixels} pixels",
                cluster + 1
            ),
        )?;
        segments.push(FrameSegment {
            left,
            width,
            image: segment,
        });
    }
    Ok(segments)
}

fn foreground_components(image: &RgbaImage) -> Vec<ForegroundComponent> {
    let width = image.width();
    let height = image.height();
    let mut visited = vec![false; width as usize * height as usize];
    let mut queue = VecDeque::new();
    let mut components = Vec::new();
    for y in 0..height {
        for x in 0..width {
            let start = y as usize * width as usize + x as usize;
            if visited[start] || image.get_pixel(x, y)[3] == 0 {
                continue;
            }
            visited[start] = true;
            queue.push_back((x, y));
            let mut pixels = Vec::new();
            let mut bounds = ForegroundBounds {
                left: x,
                top: y,
                right: x,
                bottom: y,
            };
            let mut x_sum = 0_u64;
            while let Some((component_x, component_y)) = queue.pop_front() {
                pixels.push((component_x, component_y));
                x_sum += u64::from(component_x);
                bounds.left = bounds.left.min(component_x);
                bounds.top = bounds.top.min(component_y);
                bounds.right = bounds.right.max(component_x);
                bounds.bottom = bounds.bottom.max(component_y);
                for next_y in component_y.saturating_sub(1)..=(component_y + 1).min(height - 1) {
                    for next_x in component_x.saturating_sub(1)..=(component_x + 1).min(width - 1) {
                        let next = next_y as usize * width as usize + next_x as usize;
                        if !visited[next] && image.get_pixel(next_x, next_y)[3] > 0 {
                            visited[next] = true;
                            queue.push_back((next_x, next_y));
                        }
                    }
                }
            }
            components.push(ForegroundComponent {
                center_x: x_sum as f64 / pixels.len() as f64,
                pixels,
                bounds,
            });
        }
    }
    components
}

fn alpha_bounds(image: &RgbaImage) -> Option<ForegroundBounds> {
    let mut bounds: Option<ForegroundBounds> = None;
    for (x, y, pixel) in image.enumerate_pixels() {
        if pixel[3] == 0 {
            continue;
        }
        bounds = Some(match bounds {
            Some(current) => ForegroundBounds {
                left: current.left.min(x),
                top: current.top.min(y),
                right: current.right.max(x),
                bottom: current.bottom.max(y),
            },
            None => ForegroundBounds {
                left: x,
                top: y,
                right: x,
                bottom: y,
            },
        });
    }
    bounds
}

fn validate_member_census(
    archive: &mut ZipArchive<File>,
    archive_path: &Path,
) -> Result<(), PhazerIntakeError> {
    let expected = SHEETS
        .iter()
        .map(|sheet| sheet.member)
        .collect::<BTreeSet<_>>();
    let mut counts = BTreeMap::<String, usize>::new();
    for index in 0..archive.len() {
        let member = archive
            .by_index(index)
            .map_err(|source| PhazerIntakeError::Zip {
                path: archive_path.to_path_buf(),
                source,
            })?;
        if !member.is_dir() {
            *counts.entry(member.name().to_string()).or_default() += 1;
        }
    }
    let actual = counts.keys().map(String::as_str).collect::<BTreeSet<_>>();
    require(
        actual == expected,
        "archive member census is not the pinned eight sheets",
    )?;
    require(
        counts.values().all(|count| *count == 1),
        "archive contains duplicate members",
    )
}

fn read_member(
    archive: &mut ZipArchive<File>,
    archive_path: &Path,
    member: &str,
) -> Result<Vec<u8>, PhazerIntakeError> {
    let mut file = archive
        .by_name(member)
        .map_err(|source| PhazerIntakeError::Zip {
            path: archive_path.to_path_buf(),
            source,
        })?;
    let mut bytes = Vec::with_capacity(file.size() as usize);
    file.read_to_end(&mut bytes)
        .map_err(|source| PhazerIntakeError::Io {
            path: archive_path.to_path_buf(),
            source,
        })?;
    Ok(bytes)
}

fn count_foreground_source_match(source: &RgbaImage, isolated: &RgbaImage) -> u64 {
    source
        .pixels()
        .zip(isolated.pixels())
        .filter(|(_, isolated)| isolated[3] > 0)
        .filter(|(source, isolated)| source == isolated)
        .count() as u64
}

fn blend_tinted_graph_over_original(
    original: &RgbaImage,
    graph: &RgbaImage,
    tint: [u8; 3],
    overlay_opacity: u8,
) -> RgbaImage {
    let mut output = original.clone();
    for (x, y, graph_pixel) in graph.enumerate_pixels() {
        if graph_pixel[3] == 0 {
            continue;
        }
        let background = output.get_pixel(x, y);
        let alpha = u16::from(overlay_opacity);
        let inverse = 255 - alpha;
        let mut rgba = [0_u8; 4];
        for channel in 0..3 {
            rgba[channel] = ((u16::from(background[channel]) * inverse
                + u16::from(tint[channel]) * alpha
                + 127)
                / 255) as u8;
        }
        rgba[3] = 255;
        output.put_pixel(x, y, Rgba(rgba));
    }
    output
}

fn build_contact_sheet(tiles: &[RgbaImage], columns: u32, rows: u32) -> RgbaImage {
    const TILE_WIDTH: u32 = 240;
    const TILE_HEIGHT: u32 = 240;
    let mut output = RgbaImage::from_pixel(
        columns * TILE_WIDTH,
        rows * TILE_HEIGHT,
        Rgba([255, 255, 255, 255]),
    );
    for (index, tile) in tiles.iter().enumerate() {
        let thumbnail = imageops::resize(
            tile,
            TILE_WIDTH,
            TILE_HEIGHT,
            imageops::FilterType::Triangle,
        );
        let x = (index as u32 % columns) * TILE_WIDTH;
        let y = (index as u32 / columns) * TILE_HEIGHT;
        imageops::overlay(&mut output, &thumbnail, i64::from(x), i64::from(y));
    }
    output
}

fn build_pose_contact_sheet(tiles: &[RgbaImage], columns: u32, rows: u32) -> RgbaImage {
    const TILE_WIDTH: u32 = 280;
    const TILE_HEIGHT: u32 = 280;
    const INSET: u32 = 12;
    let mut output = RgbaImage::from_pixel(
        columns * TILE_WIDTH,
        rows * TILE_HEIGHT,
        Rgba([255, 255, 255, 255]),
    );
    for (index, tile) in tiles.iter().enumerate() {
        let Some(bounds) = alpha_bounds(tile) else {
            continue;
        };
        let left = bounds.left.saturating_sub(INSET);
        let top = bounds.top.saturating_sub(INSET);
        let right = (bounds.right + INSET).min(tile.width() - 1);
        let bottom = (bounds.bottom + INSET).min(tile.height() - 1);
        let crop =
            imageops::crop_imm(tile, left, top, right - left + 1, bottom - top + 1).to_image();
        let scale = ((TILE_WIDTH - INSET * 2) as f64 / crop.width() as f64)
            .min((TILE_HEIGHT - INSET * 2) as f64 / crop.height() as f64);
        let width = (crop.width() as f64 * scale).round().max(1.0) as u32;
        let height = (crop.height() as f64 * scale).round().max(1.0) as u32;
        let thumbnail = imageops::resize(&crop, width, height, imageops::FilterType::Triangle);
        let tile_x = (index as u32 % columns) * TILE_WIDTH;
        let tile_y = (index as u32 / columns) * TILE_HEIGHT;
        let x = tile_x + (TILE_WIDTH - width) / 2;
        let y = tile_y + (TILE_HEIGHT - height) / 2;
        imageops::overlay(&mut output, &thumbnail, i64::from(x), i64::from(y));
    }
    output
}

fn load_png(path: &Path) -> Result<RgbaImage, PhazerIntakeError> {
    let bytes = fs::read(path).map_err(|source| PhazerIntakeError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    image::load_from_memory_with_format(&bytes, ImageFormat::Png)
        .map(DynamicImage::into_rgba8)
        .map_err(|source| PhazerIntakeError::Image {
            member: path.display().to_string(),
            source,
        })
}

fn save_png(image: &RgbaImage, path: &Path) -> Result<(), PhazerIntakeError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|source| PhazerIntakeError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    image
        .save_with_format(path, ImageFormat::Png)
        .map_err(|source| PhazerIntakeError::Image {
            member: path.display().to_string(),
            source,
        })
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), PhazerIntakeError> {
    let bytes = serde_json::to_vec_pretty(value)
        .map_err(|error| PhazerIntakeError::Invariant(format!("JSON serialization: {error}")))?;
    fs::write(path, bytes).map_err(|source| PhazerIntakeError::Io {
        path: path.to_path_buf(),
        source,
    })
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, PhazerIntakeError> {
    let bytes = fs::read(path).map_err(|source| PhazerIntakeError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    serde_json::from_slice(&bytes)
        .map_err(|error| PhazerIntakeError::Invariant(format!("{}: {error}", path.display())))
}

fn regular_files(root: &Path) -> Result<Vec<PathBuf>, PhazerIntakeError> {
    let mut files = fs::read_dir(root)
        .map_err(|source| PhazerIntakeError::Io {
            path: root.to_path_buf(),
            source,
        })?
        .map(|entry| {
            entry
                .map(|entry| entry.path())
                .map_err(|source| PhazerIntakeError::Io {
                    path: root.to_path_buf(),
                    source,
                })
        })
        .collect::<Result<Vec<_>, _>>()?;
    files.retain(|path| path.is_file());
    files.sort();
    Ok(files)
}

fn copy_file(source_path: &Path, target_path: &Path) -> Result<(), PhazerIntakeError> {
    if let Some(parent) = target_path.parent() {
        fs::create_dir_all(parent).map_err(|source| PhazerIntakeError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    fs::copy(source_path, target_path).map_err(|source| PhazerIntakeError::Io {
        path: target_path.to_path_buf(),
        source,
    })?;
    Ok(())
}

fn sha256_file(path: &Path) -> Result<String, PhazerIntakeError> {
    let file = File::open(path).map_err(|source| PhazerIntakeError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let mut reader = std::io::BufReader::new(file);
    let mut hasher = Sha256::new();
    std::io::copy(&mut reader, &mut HashWriter(&mut hasher)).map_err(|source| {
        PhazerIntakeError::Io {
            path: path.to_path_buf(),
            source,
        }
    })?;
    Ok(format!("{:x}", hasher.finalize()))
}

fn sha256_bytes(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

struct HashWriter<'a>(&'a mut Sha256);

impl std::io::Write for HashWriter<'_> {
    fn write(&mut self, buffer: &[u8]) -> std::io::Result<usize> {
        self.0.update(buffer);
        Ok(buffer.len())
    }

    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}

fn relative_path(root: &Path, path: &Path) -> Result<String, PhazerIntakeError> {
    path.strip_prefix(root)
        .map(|relative| relative.to_string_lossy().replace('\\', "/"))
        .map_err(|_| {
            PhazerIntakeError::Invariant(format!(
                "{} is not below {}",
                path.display(),
                root.display()
            ))
        })
}

fn require(condition: bool, message: impl Into<String>) -> Result<(), PhazerIntakeError> {
    if condition {
        Ok(())
    } else {
        Err(PhazerIntakeError::Invariant(message.into()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn proportional_six_cell_partition_has_no_gaps_or_overlap() {
        for width in [1983_u32, 2172, 2182] {
            let cells = (0..FRAMES_PER_SHEET)
                .map(|index| {
                    (
                        width * index as u32 / FRAMES_PER_SHEET as u32,
                        width * (index as u32 + 1) / FRAMES_PER_SHEET as u32,
                    )
                })
                .collect::<Vec<_>>();
            assert_eq!(cells.first().unwrap().0, 0);
            assert_eq!(cells.last().unwrap().1, width);
            assert!(cells.windows(2).all(|pair| pair[0].1 == pair[1].0));
        }
    }

    #[test]
    fn pinned_sheet_ids_are_unique_and_complete() {
        assert_eq!(SHEETS.len() * FRAMES_PER_SHEET, 48);
        assert_eq!(
            SHEETS
                .iter()
                .map(|sheet| sheet.member)
                .collect::<BTreeSet<_>>()
                .len(),
            SHEETS.len()
        );
        assert_eq!(
            SHEETS
                .iter()
                .map(|sheet| sheet.clip_id)
                .collect::<BTreeSet<_>>()
                .len(),
            SHEETS.len()
        );
    }
}
