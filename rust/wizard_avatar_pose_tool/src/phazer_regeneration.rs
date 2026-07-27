use crate::{
    build_exact_pixel_graph, build_transparent_overlay, project_pixel_graph, verify_pose_graph,
    write_pixel_graph, NormalizedPose, OverlayPalette, VerificationConfig,
};
use flate2::{write::GzEncoder, Compression};
use image::{imageops, Rgba, RgbaImage};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, VecDeque};
use std::fs;
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

pub const PHAZER_REGENERATION_COMPILER_ID: &str = "wizard-avatar-phazer-native-detail-v1";
const CANDIDATE_ALPHA_THRESHOLD: u8 = 220;
const MIN_GENERATED_PIXEL_RETENTION: f64 = 0.75;
const MIN_LOCKED_MASK_IOU: f64 = 0.95;
const SOURCE_CANONICAL_FRAME: u32 = 1254;
const NORMALIZED_CANONICAL_FRAME: u32 = 1536;
const NORMALIZATION_PADDING: u32 = (NORMALIZED_CANONICAL_FRAME - SOURCE_CANONICAL_FRAME) / 2;
const MIN_NORMALIZATION_SCALE: f64 = 0.80;
const MAX_NORMALIZATION_SCALE: f64 = 1.50;
const PHAZER_CATALOG_SCALE: f64 = 1.08;

#[derive(Clone, Debug)]
pub struct PhazerRegenerationConfig {
    pub pose_id: String,
    pub authored_source: PathBuf,
    pub generated_candidate: PathBuf,
    pub output_root: PathBuf,
}

#[derive(Clone, Debug)]
pub struct PhazerRegenerationCorpusConfig {
    pub output_root: PathBuf,
    pub approve_visual_review: bool,
}

#[derive(Clone, Debug)]
pub struct PhazerSizeNormalizationConfig {
    pub source_root: PathBuf,
    pub runtime_manifest: PathBuf,
    pub output_root: PathBuf,
}

#[derive(Clone, Debug)]
pub struct PhazerNormalizedRuntimeConfig {
    pub source_runtime_root: PathBuf,
    pub normalized_phazer_root: PathBuf,
    pub output_runtime_root: PathBuf,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PhazerRegenerationReceipt {
    pub schema_version: u32,
    pub compiler_id: String,
    pub pose_id: String,
    pub authored_source_sha256: String,
    pub generated_candidate_sha256: String,
    pub native_source_sha256: String,
    pub graph_sha256: String,
    pub authored_bounds: [u32; 4],
    pub generated_bounds: [u32; 4],
    pub aligned_candidate_silhouette_iou: f64,
    pub authored_mask_coverage: f64,
    pub generated_pixel_retention: f64,
    pub locked_mask_silhouette_iou: f64,
    pub exact_graph_projection: bool,
    pub foreground_pixel_count: u64,
    pub palette_color_count: usize,
    pub graph_run_count: usize,
    pub visual_review_status: String,
    pub evidence_path: String,
    pub graph_path: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PhazerRegenerationCorpusReceipt {
    pub schema_version: u32,
    pub compiler_id: String,
    pub pose_count: usize,
    pub exact_graph_projection_count: usize,
    pub minimum_locked_mask_silhouette_iou: f64,
    pub minimum_generated_pixel_retention: f64,
    pub median_foreground_pixel_count: u64,
    pub median_palette_color_count: usize,
    pub median_graph_run_count: usize,
    pub visual_review_status: String,
    pub native_contact_sheet_path: String,
    pub authored_mask_overlay_contact_sheet_path: String,
    pub corpus_manifest_path: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PhazerSizeNormalizationEntry {
    pub pose_id: String,
    pub direction: String,
    pub anchor_kind: String,
    pub anchor_x: u32,
    pub anchor_y: u32,
    pub measured_hat_brim_width: u32,
    pub target_hat_brim_width: u32,
    pub applied_scale: f64,
    pub frame_fit_translation_x: i32,
    pub frame_fit_translation_y: i32,
    pub normalized_hat_brim_width: u32,
    pub normalized_source_sha256: String,
    pub graph_sha256: String,
    pub exact_graph_projection: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PhazerSizeNormalizationReceipt {
    pub schema_version: u32,
    pub compiler_id: String,
    pub pose_count: usize,
    pub direction_target_hat_brim_widths: BTreeMap<String, u32>,
    pub maximum_scale_delta: f64,
    pub maximum_frame_fit_translation_pixels: u32,
    pub maximum_hat_brim_target_error_pixels: u32,
    pub exact_graph_projection_count: usize,
    pub fixed_canvas_before_contact_sheet_path: String,
    pub fixed_canvas_after_contact_sheet_path: String,
    pub corpus_manifest_path: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PhazerNormalizedRuntimeReceipt {
    pub schema_version: u32,
    pub compiler_id: String,
    pub runtime_pose_count: usize,
    pub padded_existing_pose_count: usize,
    pub normalized_phazer_pose_count: usize,
    pub frame: [u32; 2],
    pub runtime_manifest_path: String,
    pub runtime_manifest_sha256: String,
}

#[derive(Debug, thiserror::Error)]
pub enum PhazerRegenerationError {
    #[error("I/O error at {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("image error at {path}: {source}")]
    Image {
        path: PathBuf,
        #[source]
        source: image::ImageError,
    },
    #[error("PixelGraph error: {0}")]
    PixelGraph(#[from] crate::PixelGraphError),
    #[error("verification error: {0}")]
    Verification(#[from] crate::VerificationError),
    #[error("regeneration invariant failed: {0}")]
    Invariant(String),
}

#[derive(Clone, Copy, Debug)]
struct Bounds {
    left: u32,
    top: u32,
    right: u32,
    bottom: u32,
}

#[derive(Clone, Copy, Debug)]
struct HatBrim {
    bounds: Bounds,
}

#[derive(Clone, Debug, Deserialize)]
struct RuntimeNormalizationManifest {
    entries: Vec<RuntimeNormalizationEntry>,
}

#[derive(Clone, Debug, Deserialize)]
struct RuntimeNormalizationEntry {
    source_record_id: String,
    direction: String,
    anchor_kind: String,
    anchor_x: u32,
    anchor_y: u32,
}

impl Bounds {
    fn width(self) -> u32 {
        self.right - self.left + 1
    }

    fn height(self) -> u32 {
        self.bottom - self.top + 1
    }

    fn array(self) -> [u32; 4] {
        [self.left, self.top, self.width(), self.height()]
    }
}

pub fn admit_regenerated_phazer_pose(
    config: &PhazerRegenerationConfig,
) -> Result<PhazerRegenerationReceipt, PhazerRegenerationError> {
    require(
        valid_pose_id(&config.pose_id),
        format!("{} is not a WJPS pose id", config.pose_id),
    )?;
    let authored = load_rgba(&config.authored_source)?;
    let generated = load_rgba(&config.generated_candidate)?;
    let authored_bounds = alpha_bounds(&authored).ok_or_else(|| {
        PhazerRegenerationError::Invariant(format!(
            "{} authored source has no foreground",
            config.pose_id
        ))
    })?;
    let generated_matted = remove_magenta_matte(&generated);
    let generated_bounds = alpha_bounds(&generated_matted).ok_or_else(|| {
        PhazerRegenerationError::Invariant(format!(
            "{} generated candidate has no foreground after matte removal",
            config.pose_id
        ))
    })?;
    let aligned = align_candidate(
        &generated_matted,
        generated_bounds,
        authored.dimensions(),
        authored_bounds,
    );
    let aligned_candidate_silhouette_iou = silhouette_iou(&authored, &aligned);
    let authored_mask_coverage = source_coverage(&authored, &aligned);
    let (native_source, retained_pixels) = lock_authored_mask(&authored, &aligned);
    let foreground_pixel_count = foreground_count(&native_source);
    let generated_pixel_retention = retained_pixels as f64 / foreground_pixel_count as f64;
    require(
        generated_pixel_retention >= MIN_GENERATED_PIXEL_RETENTION,
        format!(
            "{} only retained {:.2}% generated pixels inside the authored mask",
            config.pose_id,
            generated_pixel_retention * 100.0
        ),
    )?;

    let pose_root = config.output_root.join(&config.pose_id);
    let evidence_root = pose_root.join("evidence");
    fs::create_dir_all(&evidence_root).map_err(|source| PhazerRegenerationError::Io {
        path: evidence_root.clone(),
        source,
    })?;
    let authored_path = evidence_root.join("authored-source.png");
    let candidate_path = evidence_root.join("generated-candidate-matted.png");
    let aligned_path = evidence_root.join("generated-candidate-aligned.png");
    let native_path = evidence_root.join("native-source.png");
    save_png(&authored, &authored_path)?;
    save_png(&generated_matted, &candidate_path)?;
    save_png(&aligned, &aligned_path)?;
    save_png(&native_source, &native_path)?;

    let native_source_sha256 = sha256_file(&native_path)?;
    let normalized = NormalizedPose {
        image: native_source.clone(),
        offset_x: 0,
        offset_y: 0,
    };
    let graph = build_exact_pixel_graph(
        format!(
            "{}-native-detail-pixelgraph-v1",
            config.pose_id.to_ascii_lowercase()
        ),
        &config.pose_id,
        &native_source_sha256,
        native_source.dimensions(),
        &normalized,
    );
    let graph_path = pose_root
        .join("graphs")
        .join(format!("{}.pixelgraph.json.gz", config.pose_id));
    let graph_sha256 = write_pixel_graph(&graph, &graph_path)?;
    let projected = project_pixel_graph(&graph)?;
    let exact_graph_projection = projected == native_source;
    require(
        exact_graph_projection,
        format!(
            "{} graph projection changed regenerated pixels",
            config.pose_id
        ),
    )?;

    let verification_config = VerificationConfig {
        foreground_alpha_threshold: 1,
        color_match_tolerance: 0,
    };
    let graph_metrics = verify_pose_graph(&native_source, &projected, verification_config)?;
    let locked_mask_metrics = verify_pose_graph(&authored, &native_source, verification_config)?;
    require(
        graph_metrics.silhouette_iou >= 0.999_999
            && graph_metrics.foreground_color_fidelity >= 0.999_999,
        format!("{} graph is not lossless", config.pose_id),
    )?;
    require(
        locked_mask_metrics.silhouette_iou >= MIN_LOCKED_MASK_IOU,
        format!("{} changed the authored silhouette", config.pose_id),
    )?;

    let graph_overlay = build_transparent_overlay(
        &native_source,
        &projected,
        verification_config,
        OverlayPalette::default(),
    )?;
    let authored_mask_overlay = build_mask_overlay(&authored, &native_source);
    save_png(&projected, &evidence_root.join("projected.png"))?;
    save_png(
        &graph_overlay.image,
        &evidence_root.join("native-source-graph-overlay.png"),
    )?;
    save_png(
        &authored_mask_overlay,
        &evidence_root.join("authored-mask-overlay.png"),
    )?;

    let receipt = PhazerRegenerationReceipt {
        schema_version: 1,
        compiler_id: PHAZER_REGENERATION_COMPILER_ID.to_string(),
        pose_id: config.pose_id.clone(),
        authored_source_sha256: sha256_file(&config.authored_source)?,
        generated_candidate_sha256: sha256_file(&config.generated_candidate)?,
        native_source_sha256,
        graph_sha256,
        authored_bounds: authored_bounds.array(),
        generated_bounds: generated_bounds.array(),
        aligned_candidate_silhouette_iou,
        authored_mask_coverage,
        generated_pixel_retention,
        locked_mask_silhouette_iou: locked_mask_metrics.silhouette_iou,
        exact_graph_projection,
        foreground_pixel_count,
        palette_color_count: graph.palette.len(),
        graph_run_count: graph.runs.len(),
        visual_review_status: "pending_transparent_overlay_review".to_string(),
        evidence_path: relative_path(&config.output_root, &evidence_root)?,
        graph_path: relative_path(&config.output_root, &graph_path)?,
    };
    write_json(&pose_root.join("verification.json"), &receipt)?;
    Ok(receipt)
}

pub fn finalize_regenerated_phazer_corpus(
    config: &PhazerRegenerationCorpusConfig,
) -> Result<PhazerRegenerationCorpusReceipt, PhazerRegenerationError> {
    let expected_pose_ids = (1..=48)
        .map(|ordinal| format!("WJPS-{ordinal:04}"))
        .collect::<Vec<_>>();
    let mut receipts = Vec::with_capacity(expected_pose_ids.len());
    let mut native_tiles = Vec::with_capacity(expected_pose_ids.len());
    let mut overlay_tiles = Vec::with_capacity(expected_pose_ids.len());
    for pose_id in &expected_pose_ids {
        let pose_root = config.output_root.join(pose_id);
        let verification_path = pose_root.join("verification.json");
        let mut receipt: PhazerRegenerationReceipt = read_json(&verification_path)?;
        require(
            receipt.pose_id == *pose_id
                && receipt.compiler_id == PHAZER_REGENERATION_COMPILER_ID
                && receipt.exact_graph_projection
                && receipt.locked_mask_silhouette_iou >= MIN_LOCKED_MASK_IOU,
            format!("{pose_id} does not carry complete regeneration admission"),
        )?;
        let evidence_root = pose_root.join("evidence");
        let native = load_rgba(&evidence_root.join("native-source.png"))?;
        let projected = load_rgba(&evidence_root.join("projected.png"))?;
        require(
            native == projected,
            format!("{pose_id} projection changed after admission"),
        )?;
        require(
            sha256_file(&evidence_root.join("native-source.png"))? == receipt.native_source_sha256,
            format!("{pose_id} native-source hash changed"),
        )?;
        let graph_path = config.output_root.join(&receipt.graph_path);
        require(
            sha256_file(&graph_path)? == receipt.graph_sha256,
            format!("{pose_id} graph hash changed"),
        )?;
        let graph = crate::read_pixel_graph(&graph_path)?;
        require(
            project_pixel_graph(&graph)? == native,
            format!("{pose_id} graph failed corpus reprojection"),
        )?;
        let overlay = load_rgba(&evidence_root.join("authored-mask-overlay.png"))?;
        require(
            mask_overlay_is_all_matched(&overlay),
            format!("{pose_id} authored mask overlay contains missing or extra pixels"),
        )?;
        if config.approve_visual_review {
            receipt.visual_review_status = "approved_closeup_and_mask_overlay_review".to_string();
            write_json(&verification_path, &receipt)?;
        }
        native_tiles.push(native);
        overlay_tiles.push(overlay);
        receipts.push(receipt);
    }

    let review_root = config.output_root.join("review");
    fs::create_dir_all(&review_root).map_err(|source| PhazerRegenerationError::Io {
        path: review_root.clone(),
        source,
    })?;
    let native_contact_sheet = build_contact_sheet(&native_tiles, 6, 8);
    let native_contact_sheet_path = review_root.join("native-detail-contact-sheet.png");
    save_png(&native_contact_sheet, &native_contact_sheet_path)?;
    let overlay_contact_sheet = build_contact_sheet(&overlay_tiles, 6, 8);
    let overlay_contact_sheet_path = review_root.join("authored-mask-overlay-contact-sheet.png");
    save_png(&overlay_contact_sheet, &overlay_contact_sheet_path)?;

    let minimum_locked_mask_silhouette_iou = receipts
        .iter()
        .map(|receipt| receipt.locked_mask_silhouette_iou)
        .fold(1.0_f64, f64::min);
    let minimum_generated_pixel_retention = receipts
        .iter()
        .map(|receipt| receipt.generated_pixel_retention)
        .fold(1.0_f64, f64::min);
    let median_foreground_pixel_count = median(
        receipts
            .iter()
            .map(|receipt| receipt.foreground_pixel_count)
            .collect(),
    );
    let median_palette_color_count = median(
        receipts
            .iter()
            .map(|receipt| receipt.palette_color_count)
            .collect(),
    );
    let median_graph_run_count = median(
        receipts
            .iter()
            .map(|receipt| receipt.graph_run_count)
            .collect(),
    );
    let visual_review_status = if config.approve_visual_review {
        "approved_closeup_and_mask_overlay_review"
    } else {
        "pending_closeup_and_mask_overlay_review"
    }
    .to_string();
    let manifest = serde_json::json!({
        "schema_version": 1,
        "compiler_id": PHAZER_REGENERATION_COMPILER_ID,
        "pose_count": receipts.len(),
        "visual_review_status": visual_review_status,
        "acceptance": {
            "minimum_required_locked_mask_silhouette_iou": MIN_LOCKED_MASK_IOU,
            "measured_minimum_locked_mask_silhouette_iou": minimum_locked_mask_silhouette_iou,
            "exact_graph_projection_count": receipts.iter().filter(|receipt| receipt.exact_graph_projection).count(),
            "minimum_generated_pixel_retention_diagnostic": minimum_generated_pixel_retention,
            "wrong_facing_or_action_candidates_rejected_before_admission": 4
        },
        "detail_parity": {
            "median_foreground_pixel_count": median_foreground_pixel_count,
            "median_palette_color_count": median_palette_color_count,
            "median_graph_run_count": median_graph_run_count
        },
        "review_artifacts": {
            "native_detail_contact_sheet": {
                "path": relative_path(&config.output_root, &native_contact_sheet_path)?,
                "sha256": sha256_file(&native_contact_sheet_path)?
            },
            "authored_mask_overlay_contact_sheet": {
                "path": relative_path(&config.output_root, &overlay_contact_sheet_path)?,
                "sha256": sha256_file(&overlay_contact_sheet_path)?
            }
        },
        "entries": receipts
    });
    let corpus_manifest_path = config.output_root.join("corpus-manifest.json");
    write_json(&corpus_manifest_path, &manifest)?;

    Ok(PhazerRegenerationCorpusReceipt {
        schema_version: 1,
        compiler_id: PHAZER_REGENERATION_COMPILER_ID.to_string(),
        pose_count: 48,
        exact_graph_projection_count: 48,
        minimum_locked_mask_silhouette_iou,
        minimum_generated_pixel_retention,
        median_foreground_pixel_count,
        median_palette_color_count,
        median_graph_run_count,
        visual_review_status,
        native_contact_sheet_path: relative_path(&config.output_root, &native_contact_sheet_path)?,
        authored_mask_overlay_contact_sheet_path: relative_path(
            &config.output_root,
            &overlay_contact_sheet_path,
        )?,
        corpus_manifest_path: relative_path(&config.output_root, &corpus_manifest_path)?,
    })
}

pub fn normalize_regenerated_phazer_corpus(
    config: &PhazerSizeNormalizationConfig,
) -> Result<PhazerSizeNormalizationReceipt, PhazerRegenerationError> {
    let runtime: RuntimeNormalizationManifest = read_json(&config.runtime_manifest)?;
    let runtime_entries = runtime
        .entries
        .into_iter()
        .filter(|entry| entry.source_record_id.starts_with("WJPS-"))
        .map(|entry| (entry.source_record_id.clone(), entry))
        .collect::<BTreeMap<_, _>>();
    require(
        runtime_entries.len() == 48,
        "runtime manifest does not contain exactly 48 WJPS entries",
    )?;

    let expected_pose_ids = (1..=48)
        .map(|ordinal| format!("WJPS-{ordinal:04}"))
        .collect::<Vec<_>>();
    let mut sources = BTreeMap::new();
    let mut measured_brims = BTreeMap::new();
    let mut widths_by_direction = BTreeMap::<String, Vec<u32>>::new();
    for pose_id in &expected_pose_ids {
        let source_path = config
            .source_root
            .join(pose_id)
            .join("evidence/native-source.png");
        let source = load_rgba(&source_path)?;
        require(
            source.dimensions() == (SOURCE_CANONICAL_FRAME, SOURCE_CANONICAL_FRAME),
            format!(
                "{pose_id} is not on the canonical {SOURCE_CANONICAL_FRAME}x{SOURCE_CANONICAL_FRAME} source frame"
            ),
        )?;
        let padded_source = pad_for_size_normalization(&source);
        let brim = detect_hat_brim(&padded_source).ok_or_else(|| {
            PhazerRegenerationError::Invariant(format!(
                "{pose_id} does not have a measurable central hat brim"
            ))
        })?;
        let runtime_entry = runtime_entries.get(pose_id).ok_or_else(|| {
            PhazerRegenerationError::Invariant(format!("{pose_id} is missing runtime metadata"))
        })?;
        widths_by_direction
            .entry(runtime_entry.direction.clone())
            .or_default()
            .push(brim.bounds.width());
        sources.insert(pose_id.clone(), padded_source);
        measured_brims.insert(pose_id.clone(), brim);
    }
    let direction_targets = widths_by_direction
        .into_iter()
        .map(|(direction, widths)| {
            (
                direction,
                (f64::from(median(widths)) * PHAZER_CATALOG_SCALE).round() as u32,
            )
        })
        .collect::<BTreeMap<_, _>>();
    for pose_id in &expected_pose_ids {
        let brim = measured_brims
            .get(pose_id)
            .expect("all expected brim metrics were collected");
        let runtime_entry = runtime_entries
            .get(pose_id)
            .expect("all expected runtime entries were collected");
        let target_width = direction_targets[&runtime_entry.direction];
        let scale = target_width as f64 / brim.bounds.width() as f64;
        require(
            (MIN_NORMALIZATION_SCALE..=MAX_NORMALIZATION_SCALE).contains(&scale),
            format!(
                "{pose_id} requires unsafe {:.3} scale from {}px to {}px",
                scale,
                brim.bounds.width(),
                target_width
            ),
        )?;
    }

    let mut entries = Vec::with_capacity(48);
    let mut before_tiles = Vec::with_capacity(48);
    let mut after_tiles = Vec::with_capacity(48);
    for pose_id in &expected_pose_ids {
        let source = sources
            .get(pose_id)
            .expect("all expected sources were collected");
        let brim = measured_brims
            .get(pose_id)
            .expect("all expected brim metrics were collected");
        let runtime_entry = runtime_entries
            .get(pose_id)
            .expect("all expected runtime entries were collected");
        let target_width = direction_targets[&runtime_entry.direction];
        let scale = target_width as f64 / brim.bounds.width() as f64;
        let normalized_anchor_x = runtime_entry.anchor_x + NORMALIZATION_PADDING;
        let normalized_anchor_y = runtime_entry.anchor_y + NORMALIZATION_PADDING;
        require(
            (MIN_NORMALIZATION_SCALE..=MAX_NORMALIZATION_SCALE).contains(&scale),
            format!(
                "{pose_id} requires unsafe {:.3} scale from {}px to {}px",
                scale,
                brim.bounds.width(),
                target_width
            ),
        )?;
        let (normalized, frame_fit_translation_x, frame_fit_translation_y) =
            scale_about_anchor(source, scale, normalized_anchor_x, normalized_anchor_y)?;
        let normalized_hat_brim_width =
            (brim.bounds.width() as f64 * scale).round().max(1.0) as u32;

        let pose_root = config.output_root.join(pose_id);
        let evidence_root = pose_root.join("evidence");
        let normalized_path = evidence_root.join("native-source.png");
        let graph_path = pose_root
            .join("graphs")
            .join(format!("{pose_id}.pixelgraph.json.gz"));
        let (normalized_source_sha256, graph_sha256) =
            if normalized_path.exists() && graph_path.exists() {
                require(
                    load_rgba(&normalized_path)? == normalized,
                    format!("{pose_id} resume source differs from deterministic normalization"),
                )?;
                let graph = crate::read_pixel_graph(&graph_path)?;
                require(
                    project_pixel_graph(&graph)? == normalized,
                    format!("{pose_id} resumed graph is not lossless"),
                )?;
                (sha256_file(&normalized_path)?, sha256_file(&graph_path)?)
            } else {
                save_png(&normalized, &normalized_path)?;
                let normalized_source_sha256 = sha256_file(&normalized_path)?;
                let graph = build_exact_pixel_graph(
                    format!(
                        "{}-normalized-native-detail-pixelgraph-v1",
                        pose_id.to_ascii_lowercase()
                    ),
                    pose_id,
                    &normalized_source_sha256,
                    normalized.dimensions(),
                    &NormalizedPose {
                        image: normalized.clone(),
                        offset_x: 0,
                        offset_y: 0,
                    },
                );
                let graph_sha256 = write_pixel_graph(&graph, &graph_path)?;
                let projected = project_pixel_graph(&graph)?;
                require(
                    projected == normalized,
                    format!("{pose_id} normalized graph is not lossless"),
                )?;
                save_png(&projected, &evidence_root.join("projected.png"))?;
                (normalized_source_sha256, graph_sha256)
            };
        let comparison = build_normalization_comparison(source, &normalized);
        save_png(
            &comparison,
            &evidence_root.join("size-normalization-comparison.png"),
        )?;

        let entry = PhazerSizeNormalizationEntry {
            pose_id: pose_id.clone(),
            direction: runtime_entry.direction.clone(),
            anchor_kind: runtime_entry.anchor_kind.clone(),
            anchor_x: normalized_anchor_x,
            anchor_y: normalized_anchor_y,
            measured_hat_brim_width: brim.bounds.width(),
            target_hat_brim_width: target_width,
            applied_scale: scale,
            frame_fit_translation_x,
            frame_fit_translation_y,
            normalized_hat_brim_width,
            normalized_source_sha256,
            graph_sha256,
            exact_graph_projection: true,
        };
        write_json(&pose_root.join("normalization.json"), &entry)?;
        before_tiles.push(source.clone());
        after_tiles.push(normalized);
        entries.push(entry);
    }

    let review_root = config.output_root.join("review");
    fs::create_dir_all(&review_root).map_err(|source| PhazerRegenerationError::Io {
        path: review_root.clone(),
        source,
    })?;
    let before_sheet = build_fixed_canvas_contact_sheet(&before_tiles, 6, 8);
    let before_sheet_path = review_root.join("fixed-canvas-before.png");
    save_png(&before_sheet, &before_sheet_path)?;
    let after_sheet = build_fixed_canvas_contact_sheet(&after_tiles, 6, 8);
    let after_sheet_path = review_root.join("fixed-canvas-after.png");
    save_png(&after_sheet, &after_sheet_path)?;

    let maximum_scale_delta = entries
        .iter()
        .map(|entry| (entry.applied_scale - 1.0).abs())
        .fold(0.0_f64, f64::max);
    let maximum_frame_fit_translation_pixels = entries
        .iter()
        .flat_map(|entry| {
            [
                entry.frame_fit_translation_x.unsigned_abs(),
                entry.frame_fit_translation_y.unsigned_abs(),
            ]
        })
        .max()
        .unwrap_or(0);
    let maximum_hat_brim_target_error_pixels = entries
        .iter()
        .map(|entry| {
            entry
                .normalized_hat_brim_width
                .abs_diff(entry.target_hat_brim_width)
        })
        .max()
        .unwrap_or(0);
    require(
        maximum_hat_brim_target_error_pixels <= 3,
        format!("normalized brim measurements deviate by {maximum_hat_brim_target_error_pixels}px"),
    )?;
    let exact_graph_projection_count = entries
        .iter()
        .filter(|entry| entry.exact_graph_projection)
        .count();
    require(
        exact_graph_projection_count == 48,
        "not every normalized graph reprojects exactly",
    )?;

    let manifest = serde_json::json!({
        "schema_version": 1,
        "compiler_id": "wizard-avatar-phazer-size-normalization-v2",
        "pose_count": entries.len(),
        "method": {
            "scale_feature": "central_hat_brim",
            "target": "median_width_per_camera_facing_with_catalog_scale",
            "catalog_scale": PHAZER_CATALOG_SCALE,
            "pivot": "runtime_ground_contact_or_body_center_anchor",
            "minimum_allowed_scale": MIN_NORMALIZATION_SCALE,
            "maximum_allowed_scale": MAX_NORMALIZATION_SCALE,
            "source_canonical_frame": [SOURCE_CANONICAL_FRAME, SOURCE_CANONICAL_FRAME],
            "normalized_canonical_frame": [NORMALIZED_CANONICAL_FRAME, NORMALIZED_CANONICAL_FRAME],
            "symmetric_transparent_padding_pixels": NORMALIZATION_PADDING
        },
        "direction_target_hat_brim_widths": direction_targets,
        "maximum_scale_delta": maximum_scale_delta,
        "maximum_frame_fit_translation_pixels": maximum_frame_fit_translation_pixels,
        "maximum_hat_brim_target_error_pixels": maximum_hat_brim_target_error_pixels,
        "exact_graph_projection_count": exact_graph_projection_count,
        "visual_review_status": "pending_fixed_canvas_transition_review",
        "review_artifacts": {
            "fixed_canvas_before": {
                "path": relative_path(&config.output_root, &before_sheet_path)?,
                "sha256": sha256_file(&before_sheet_path)?
            },
            "fixed_canvas_after": {
                "path": relative_path(&config.output_root, &after_sheet_path)?,
                "sha256": sha256_file(&after_sheet_path)?
            }
        },
        "entries": entries
    });
    let manifest_path = config.output_root.join("normalization-manifest.json");
    write_json(&manifest_path, &manifest)?;

    Ok(PhazerSizeNormalizationReceipt {
        schema_version: 1,
        compiler_id: "wizard-avatar-phazer-size-normalization-v2".to_string(),
        pose_count: 48,
        direction_target_hat_brim_widths: direction_targets,
        maximum_scale_delta,
        maximum_frame_fit_translation_pixels,
        maximum_hat_brim_target_error_pixels,
        exact_graph_projection_count,
        fixed_canvas_before_contact_sheet_path: relative_path(
            &config.output_root,
            &before_sheet_path,
        )?,
        fixed_canvas_after_contact_sheet_path: relative_path(
            &config.output_root,
            &after_sheet_path,
        )?,
        corpus_manifest_path: relative_path(&config.output_root, &manifest_path)?,
    })
}

pub fn build_normalized_phazer_runtime(
    config: &PhazerNormalizedRuntimeConfig,
) -> Result<PhazerNormalizedRuntimeReceipt, PhazerRegenerationError> {
    require(
        !config.output_runtime_root.exists(),
        format!(
            "runtime output already exists at {}",
            config.output_runtime_root.display()
        ),
    )?;
    let source_manifest_path = config.source_runtime_root.join("runtime-manifest.json");
    let mut runtime: serde_json::Value = read_json(&source_manifest_path)?;
    require(
        runtime["source_count"].as_u64() == Some(308)
            && runtime["entries"].as_array().map(Vec::len) == Some(308)
            && runtime["frame"]
                == serde_json::json!([SOURCE_CANONICAL_FRAME, SOURCE_CANONICAL_FRAME]),
        "source runtime is not the authoritative 308-pose v7 catalog",
    )?;
    let output_graph_root = config.output_runtime_root.join("graphs");
    fs::create_dir_all(&output_graph_root).map_err(|source| PhazerRegenerationError::Io {
        path: output_graph_root.clone(),
        source,
    })?;

    let entries = runtime["entries"].as_array_mut().ok_or_else(|| {
        PhazerRegenerationError::Invariant("runtime entries is not an array".to_string())
    })?;
    let (padded_existing_pose_count, normalized_phazer_pose_count) = std::thread::scope(|scope| {
        let chunk_size = entries.len().div_ceil(8);
        let mut handles = Vec::new();
        for chunk in entries.chunks_mut(chunk_size) {
            let output_graph_root = output_graph_root.clone();
            handles.push(scope.spawn(move || {
                let mut padded = 0_usize;
                let mut normalized = 0_usize;
                for entry in chunk {
                    if migrate_runtime_entry(config, &output_graph_root, entry)? {
                        normalized += 1;
                    } else {
                        padded += 1;
                    }
                }
                Ok::<_, PhazerRegenerationError>((padded, normalized))
            }));
        }
        let mut padded = 0_usize;
        let mut normalized = 0_usize;
        for handle in handles {
            let (chunk_padded, chunk_normalized) = handle.join().map_err(|_| {
                PhazerRegenerationError::Invariant(
                    "runtime graph migration worker panicked".to_string(),
                )
            })??;
            padded += chunk_padded;
            normalized += chunk_normalized;
        }
        Ok::<_, PhazerRegenerationError>((padded, normalized))
    })?;
    require(
        padded_existing_pose_count == 260 && normalized_phazer_pose_count == 48,
        "runtime did not preserve the 260 plus 48 corpus partition",
    )?;
    runtime["compiler_id"] = serde_json::Value::String(
        "wizard-avatar-production-alpha-plus-normalized-phazer-v4".to_string(),
    );
    runtime["frame"] = serde_json::json!([NORMALIZED_CANONICAL_FRAME, NORMALIZED_CANONICAL_FRAME]);
    let output_manifest_path = config.output_runtime_root.join("runtime-manifest.json");
    write_json(&output_manifest_path, &runtime)?;
    let runtime_manifest_sha256 = sha256_file(&output_manifest_path)?;
    Ok(PhazerNormalizedRuntimeReceipt {
        schema_version: 1,
        compiler_id: "wizard-avatar-production-alpha-plus-normalized-phazer-v4".to_string(),
        runtime_pose_count: 308,
        padded_existing_pose_count,
        normalized_phazer_pose_count,
        frame: [NORMALIZED_CANONICAL_FRAME, NORMALIZED_CANONICAL_FRAME],
        runtime_manifest_path: output_manifest_path.to_string_lossy().to_string(),
        runtime_manifest_sha256,
    })
}

fn migrate_runtime_entry(
    config: &PhazerNormalizedRuntimeConfig,
    output_graph_root: &Path,
    entry: &mut serde_json::Value,
) -> Result<bool, PhazerRegenerationError> {
    let source_record_id = entry["source_record_id"]
        .as_str()
        .ok_or_else(|| {
            PhazerRegenerationError::Invariant("runtime entry has no source_record_id".to_string())
        })?
        .to_string();
    let output_graph_path =
        output_graph_root.join(format!("{source_record_id}.pixelgraph.json.gz"));
    if source_record_id.starts_with("WJPS-") {
        let normalization_path = config
            .normalized_phazer_root
            .join(&source_record_id)
            .join("normalization.json");
        let normalization: PhazerSizeNormalizationEntry = read_json(&normalization_path)?;
        let source_graph_path = config
            .normalized_phazer_root
            .join(&source_record_id)
            .join("graphs")
            .join(format!("{source_record_id}.pixelgraph.json.gz"));
        let graph = crate::read_pixel_graph(&source_graph_path)?;
        require(
            graph.source_record_id == source_record_id
                && graph.frame.width == NORMALIZED_CANONICAL_FRAME
                && graph.frame.height == NORMALIZED_CANONICAL_FRAME
                && project_pixel_graph(&graph)?
                    == load_rgba(
                        &config
                            .normalized_phazer_root
                            .join(&source_record_id)
                            .join("evidence/native-source.png"),
                    )?,
            format!("{source_record_id} normalized graph is not authoritative"),
        )?;
        let graph_sha256 = write_runtime_graph_fast(&graph, &output_graph_path)?;
        entry["frame"] =
            serde_json::json!([NORMALIZED_CANONICAL_FRAME, NORMALIZED_CANONICAL_FRAME]);
        entry["source_size"] =
            serde_json::json!([NORMALIZED_CANONICAL_FRAME, NORMALIZED_CANONICAL_FRAME]);
        entry["offset"] = serde_json::json!([0, 0]);
        entry["source_sha256"] = serde_json::Value::String(normalization.normalized_source_sha256);
        entry["graph_sha256"] = serde_json::Value::String(graph_sha256);
        entry["graph_id"] = serde_json::Value::String(graph.graph_id);
        entry["foreground_pixel_count"] = serde_json::json!(graph.foreground_pixel_count);
        entry["anchor_x"] = serde_json::json!(normalization.anchor_x);
        entry["anchor_y"] = serde_json::json!(normalization.anchor_y);
        entry["evidence_path"] = serde_json::Value::String(format!(
            "evidence/phazer-native-regeneration/normalized-v2/{source_record_id}/evidence"
        ));
        Ok(true)
    } else {
        let graph_path = entry["graph_path"].as_str().ok_or_else(|| {
            PhazerRegenerationError::Invariant(format!("{source_record_id} has no graph path"))
        })?;
        let mut graph = crate::read_pixel_graph(&config.source_runtime_root.join(graph_path))?;
        require(
            graph.frame.width == SOURCE_CANONICAL_FRAME
                && graph.frame.height == SOURCE_CANONICAL_FRAME,
            format!("{source_record_id} does not use the v7 canonical frame"),
        )?;
        graph.frame.width = NORMALIZED_CANONICAL_FRAME;
        graph.frame.height = NORMALIZED_CANONICAL_FRAME;
        graph.offset_x += NORMALIZATION_PADDING;
        graph.offset_y += NORMALIZATION_PADDING;
        for run in &mut graph.runs {
            run.x += NORMALIZATION_PADDING;
            run.y += NORMALIZATION_PADDING;
        }
        let graph_sha256 = write_runtime_graph_fast(&graph, &output_graph_path)?;
        let old_offset = entry["offset"].as_array().ok_or_else(|| {
            PhazerRegenerationError::Invariant(format!("{source_record_id} has no offset"))
        })?;
        let offset_x = old_offset[0].as_u64().unwrap_or(0) as u32 + NORMALIZATION_PADDING;
        let offset_y = old_offset[1].as_u64().unwrap_or(0) as u32 + NORMALIZATION_PADDING;
        let anchor_x = entry["anchor_x"].as_u64().ok_or_else(|| {
            PhazerRegenerationError::Invariant(format!("{source_record_id} has no anchor_x"))
        })? as u32
            + NORMALIZATION_PADDING;
        let anchor_y = entry["anchor_y"].as_u64().ok_or_else(|| {
            PhazerRegenerationError::Invariant(format!("{source_record_id} has no anchor_y"))
        })? as u32
            + NORMALIZATION_PADDING;
        entry["frame"] =
            serde_json::json!([NORMALIZED_CANONICAL_FRAME, NORMALIZED_CANONICAL_FRAME]);
        entry["offset"] = serde_json::json!([offset_x, offset_y]);
        entry["graph_sha256"] = serde_json::Value::String(graph_sha256);
        entry["anchor_x"] = serde_json::json!(anchor_x);
        entry["anchor_y"] = serde_json::json!(anchor_y);
        Ok(false)
    }
}

fn remove_magenta_matte(source: &RgbaImage) -> RgbaImage {
    let mut output = source.clone();
    for pixel in output.pixels_mut() {
        let red = i32::from(pixel[0]);
        let green = i32::from(pixel[1]);
        let blue = i32::from(pixel[2]);
        let magenta_dominance = ((red + blue) / 2) - green;
        let magenta_family = red >= 70
            && blue >= 145
            && green <= 145
            && red - green >= 45
            && blue - green >= 70
            && magenta_dominance >= 65;
        if magenta_family {
            *pixel = Rgba([0, 0, 0, 0]);
        } else {
            pixel[3] = 255;
        }
    }
    output
}

fn align_candidate(
    source: &RgbaImage,
    source_bounds: Bounds,
    frame: (u32, u32),
    target_bounds: Bounds,
) -> RgbaImage {
    let crop = imageops::crop_imm(
        source,
        source_bounds.left,
        source_bounds.top,
        source_bounds.width(),
        source_bounds.height(),
    )
    .to_image();
    let resized = imageops::resize(
        &crop,
        target_bounds.width(),
        target_bounds.height(),
        imageops::FilterType::Lanczos3,
    );
    let mut aligned = RgbaImage::new(frame.0, frame.1);
    imageops::overlay(
        &mut aligned,
        &resized,
        i64::from(target_bounds.left),
        i64::from(target_bounds.top),
    );
    aligned
}

fn lock_authored_mask(authored: &RgbaImage, aligned: &RgbaImage) -> (RgbaImage, u64) {
    let mut output = RgbaImage::new(authored.width(), authored.height());
    let mut retained = 0_u64;
    for (x, y, authored_pixel) in authored.enumerate_pixels() {
        if authored_pixel[3] == 0 {
            continue;
        }
        let generated_pixel = aligned.get_pixel(x, y);
        let mut selected = if generated_pixel[3] >= CANDIDATE_ALPHA_THRESHOLD {
            retained += 1;
            *generated_pixel
        } else {
            *authored_pixel
        };
        selected[3] = authored_pixel[3];
        output.put_pixel(x, y, selected);
    }
    (output, retained)
}

fn build_mask_overlay(authored: &RgbaImage, regenerated: &RgbaImage) -> RgbaImage {
    let mut output = RgbaImage::new(authored.width(), authored.height());
    for (x, y, authored_pixel) in authored.enumerate_pixels() {
        let regenerated_pixel = regenerated.get_pixel(x, y);
        let authored_foreground = authored_pixel[3] > 0;
        let regenerated_foreground = regenerated_pixel[3] > 0;
        let pixel = match (authored_foreground, regenerated_foreground) {
            (true, true) => {
                let alpha = authored_pixel[3];
                Rgba([0, 185, 115, alpha.max(160)])
            }
            (true, false) => Rgba([255, 56, 74, 230]),
            (false, true) => Rgba([0, 158, 255, 230]),
            (false, false) => Rgba([0, 0, 0, 0]),
        };
        output.put_pixel(x, y, pixel);
    }
    output
}

fn mask_overlay_is_all_matched(image: &RgbaImage) -> bool {
    image
        .pixels()
        .all(|pixel| pixel[3] == 0 || (pixel[0] == 0 && pixel[1] == 185 && pixel[2] == 115))
}

fn detect_hat_brim(image: &RgbaImage) -> Option<HatBrim> {
    let width = image.width() as usize;
    let height = image.height() as usize;
    let mut visited = vec![false; width * height];
    let mut best: Option<(u64, HatBrim)> = None;
    for y in 0..image.height() {
        for x in 0..image.width() {
            let index = y as usize * width + x as usize;
            if visited[index] || !is_hat_yellow(image.get_pixel(x, y)) {
                continue;
            }
            visited[index] = true;
            let mut queue = VecDeque::from([(x, y)]);
            let mut bounds = Bounds {
                left: x,
                top: y,
                right: x,
                bottom: y,
            };
            let mut area = 0_u64;
            while let Some((current_x, current_y)) = queue.pop_front() {
                area += 1;
                bounds.left = bounds.left.min(current_x);
                bounds.top = bounds.top.min(current_y);
                bounds.right = bounds.right.max(current_x);
                bounds.bottom = bounds.bottom.max(current_y);
                for (next_x, next_y) in
                    orthogonal_neighbors(current_x, current_y, image.dimensions())
                {
                    let next_index = next_y as usize * width + next_x as usize;
                    if !visited[next_index] && is_hat_yellow(image.get_pixel(next_x, next_y)) {
                        visited[next_index] = true;
                        queue.push_back((next_x, next_y));
                    }
                }
            }
            let center_x = (bounds.left + bounds.right) / 2;
            if area < 100
                || bounds.width() < 35
                || bounds.width() < bounds.height().saturating_mul(2)
                || bounds.height() > 110
                || bounds.top > image.height() * 2 / 3
                || !(image.width() / 8..=image.width() * 7 / 8).contains(&center_x)
            {
                continue;
            }
            let blue_top = bounds.top.saturating_sub(260);
            let blue_pixels = count_pixels_in_rect(
                image,
                Bounds {
                    left: bounds.left.saturating_sub(24),
                    top: blue_top,
                    right: (bounds.right + 24).min(image.width() - 1),
                    bottom: bounds.top.saturating_sub(1),
                },
                is_hat_blue,
            );
            if blue_pixels < 150 {
                continue;
            }
            let center_distance = center_x.abs_diff(image.width() / 2) as u64;
            let score = blue_pixels
                .saturating_mul(8)
                .saturating_add(area.saturating_mul(2))
                .saturating_add(u64::from(bounds.width()).saturating_mul(20))
                .saturating_sub(center_distance);
            if best
                .as_ref()
                .is_none_or(|(best_score, _)| score > *best_score)
            {
                best = Some((score, HatBrim { bounds }));
            }
        }
    }
    best.map(|(_, brim)| HatBrim {
        bounds: expand_hat_brim_band(image, brim.bounds),
    })
}

fn expand_hat_brim_band(image: &RgbaImage, seed: Bounds) -> Bounds {
    let center_x = (seed.left + seed.right) / 2;
    let mut expanded = seed;
    let search_left = center_x.saturating_sub(220);
    let search_right = (center_x + 220).min(image.width() - 1);
    for y in seed.top..=seed.bottom {
        let mut runs = Vec::<(u32, u32)>::new();
        let mut run_start = None;
        let mut previous_gold = None;
        for x in search_left..=search_right {
            if !is_relaxed_hat_gold(image.get_pixel(x, y)) {
                continue;
            }
            match previous_gold {
                Some(previous) if x - previous <= 20 => {}
                Some(previous) => {
                    runs.push((run_start.expect("gold run has a start"), previous));
                    run_start = Some(x);
                }
                None => run_start = Some(x),
            }
            previous_gold = Some(x);
        }
        if let (Some(start), Some(end)) = (run_start, previous_gold) {
            runs.push((start, end));
        }
        if let Some((left, right)) = runs
            .into_iter()
            .filter(|(left, right)| {
                *right >= seed.left.saturating_sub(12) && *left <= seed.right + 12
            })
            .max_by_key(|(left, right)| right - left)
        {
            expanded.left = expanded.left.min(left);
            expanded.right = expanded.right.max(right);
        }
    }
    expanded
}

fn orthogonal_neighbors(x: u32, y: u32, frame: (u32, u32)) -> Vec<(u32, u32)> {
    let mut neighbors = Vec::with_capacity(4);
    if x > 0 {
        neighbors.push((x - 1, y));
    }
    if x + 1 < frame.0 {
        neighbors.push((x + 1, y));
    }
    if y > 0 {
        neighbors.push((x, y - 1));
    }
    if y + 1 < frame.1 {
        neighbors.push((x, y + 1));
    }
    neighbors
}

fn is_hat_yellow(pixel: &Rgba<u8>) -> bool {
    pixel[3] > 0
        && pixel[0] >= 145
        && pixel[1] >= 90
        && pixel[2] <= 120
        && pixel[0] >= pixel[1]
        && pixel[1] >= pixel[2].saturating_add(25)
}

fn is_relaxed_hat_gold(pixel: &Rgba<u8>) -> bool {
    pixel[3] > 0
        && pixel[0] >= 120
        && pixel[1] >= 65
        && pixel[2] <= 145
        && pixel[0] >= pixel[2].saturating_add(30)
        && pixel[1] >= pixel[2].saturating_add(8)
}

fn is_hat_blue(pixel: &Rgba<u8>) -> bool {
    pixel[3] > 0
        && pixel[2] >= 95
        && pixel[2] >= pixel[0].saturating_add(20)
        && pixel[2] >= pixel[1].saturating_add(5)
}

fn count_pixels_in_rect(
    image: &RgbaImage,
    bounds: Bounds,
    predicate: fn(&Rgba<u8>) -> bool,
) -> u64 {
    if bounds.top > bounds.bottom || bounds.left > bounds.right {
        return 0;
    }
    let mut count = 0_u64;
    for y in bounds.top..=bounds.bottom {
        for x in bounds.left..=bounds.right {
            if predicate(image.get_pixel(x, y)) {
                count += 1;
            }
        }
    }
    count
}

fn pad_for_size_normalization(source: &RgbaImage) -> RgbaImage {
    let mut output = RgbaImage::new(NORMALIZED_CANONICAL_FRAME, NORMALIZED_CANONICAL_FRAME);
    imageops::overlay(
        &mut output,
        source,
        i64::from(NORMALIZATION_PADDING),
        i64::from(NORMALIZATION_PADDING),
    );
    output
}

fn scale_about_anchor(
    source: &RgbaImage,
    scale: f64,
    anchor_x: u32,
    anchor_y: u32,
) -> Result<(RgbaImage, i32, i32), PhazerRegenerationError> {
    let bounds = alpha_bounds(source).ok_or_else(|| {
        PhazerRegenerationError::Invariant("source has no foreground".to_string())
    })?;
    let crop = imageops::crop_imm(
        source,
        bounds.left,
        bounds.top,
        bounds.width(),
        bounds.height(),
    )
    .to_image();
    let resized_width = (crop.width() as f64 * scale).round().max(1.0) as u32;
    let resized_height = (crop.height() as f64 * scale).round().max(1.0) as u32;
    let resized = imageops::resize(
        &crop,
        resized_width,
        resized_height,
        imageops::FilterType::Lanczos3,
    );
    let local_anchor_x = i64::from(anchor_x) - i64::from(bounds.left);
    let local_anchor_y = i64::from(anchor_y) - i64::from(bounds.top);
    let desired_left = i64::from(anchor_x) - (local_anchor_x as f64 * scale).round() as i64;
    let desired_top = i64::from(anchor_y) - (local_anchor_y as f64 * scale).round() as i64;
    require(
        resized.width() <= source.width() && resized.height() <= source.height(),
        format!(
            "scale {:.3} produces an oversized {}x{} silhouette",
            scale,
            resized.width(),
            resized.height()
        ),
    )?;
    let maximum_left = i64::from(source.width() - resized.width());
    let maximum_top = i64::from(source.height() - resized.height());
    let destination_left = desired_left.clamp(0, maximum_left);
    let destination_top = desired_top.clamp(0, maximum_top);
    let frame_fit_translation_x = destination_left - desired_left;
    let frame_fit_translation_y = destination_top - desired_top;
    require(
        frame_fit_translation_x.unsigned_abs() <= 48
            && frame_fit_translation_y.unsigned_abs() <= 48,
        format!(
            "scale {:.3} needs excessive frame-fit translation ({frame_fit_translation_x}, {frame_fit_translation_y})",
            scale
        ),
    )?;
    let mut output = RgbaImage::new(source.width(), source.height());
    imageops::overlay(&mut output, &resized, destination_left, destination_top);
    Ok((
        output,
        frame_fit_translation_x as i32,
        frame_fit_translation_y as i32,
    ))
}

fn build_normalization_comparison(before: &RgbaImage, after: &RgbaImage) -> RgbaImage {
    let mut output = RgbaImage::from_pixel(
        before.width() * 2,
        before.height(),
        Rgba([255, 255, 255, 255]),
    );
    imageops::overlay(&mut output, before, 0, 0);
    imageops::overlay(&mut output, after, i64::from(before.width()), 0);
    output
}

fn build_fixed_canvas_contact_sheet(images: &[RgbaImage], columns: u32, rows: u32) -> RgbaImage {
    const TILE: u32 = 250;
    const MARGIN: u32 = 5;
    let content_size = TILE - MARGIN * 2;
    let mut sheet = RgbaImage::from_pixel(columns * TILE, rows * TILE, Rgba([255, 255, 255, 255]));
    for (index, image) in images.iter().enumerate() {
        let tile = imageops::resize(
            image,
            content_size,
            content_size,
            imageops::FilterType::Lanczos3,
        );
        let column = index as u32 % columns;
        let row = index as u32 / columns;
        let left = column * TILE + MARGIN;
        let top = row * TILE + MARGIN;
        imageops::overlay(&mut sheet, &tile, i64::from(left), i64::from(top));
    }
    sheet
}

fn build_contact_sheet(images: &[RgbaImage], columns: u32, rows: u32) -> RgbaImage {
    const TILE: u32 = 320;
    const MARGIN: u32 = 12;
    let mut sheet = RgbaImage::from_pixel(columns * TILE, rows * TILE, Rgba([255, 255, 255, 255]));
    for (index, image) in images.iter().enumerate() {
        let Some(bounds) = alpha_bounds(image) else {
            continue;
        };
        let crop = imageops::crop_imm(
            image,
            bounds.left,
            bounds.top,
            bounds.width(),
            bounds.height(),
        )
        .to_image();
        let scale = ((TILE - MARGIN * 2) as f64 / crop.width() as f64)
            .min((TILE - MARGIN * 2) as f64 / crop.height() as f64);
        let width = (crop.width() as f64 * scale).round().max(1.0) as u32;
        let height = (crop.height() as f64 * scale).round().max(1.0) as u32;
        let tile = imageops::resize(&crop, width, height, imageops::FilterType::Lanczos3);
        let column = index as u32 % columns;
        let row = index as u32 / columns;
        let left = column * TILE + (TILE - width) / 2;
        let top = row * TILE + (TILE - height) / 2;
        imageops::overlay(&mut sheet, &tile, i64::from(left), i64::from(top));
    }
    sheet
}

fn silhouette_iou(left: &RgbaImage, right: &RgbaImage) -> f64 {
    let mut intersection = 0_u64;
    let mut union = 0_u64;
    for (left_pixel, right_pixel) in left.pixels().zip(right.pixels()) {
        let left_foreground = left_pixel[3] > 0;
        let right_foreground = right_pixel[3] >= CANDIDATE_ALPHA_THRESHOLD;
        if left_foreground || right_foreground {
            union += 1;
        }
        if left_foreground && right_foreground {
            intersection += 1;
        }
    }
    if union == 0 {
        1.0
    } else {
        intersection as f64 / union as f64
    }
}

fn source_coverage(source: &RgbaImage, candidate: &RgbaImage) -> f64 {
    let mut source_pixels = 0_u64;
    let mut covered_pixels = 0_u64;
    for (source_pixel, candidate_pixel) in source.pixels().zip(candidate.pixels()) {
        if source_pixel[3] > 0 {
            source_pixels += 1;
            if candidate_pixel[3] >= CANDIDATE_ALPHA_THRESHOLD {
                covered_pixels += 1;
            }
        }
    }
    covered_pixels as f64 / source_pixels as f64
}

fn foreground_count(image: &RgbaImage) -> u64 {
    image.pixels().filter(|pixel| pixel[3] > 0).count() as u64
}

fn alpha_bounds(image: &RgbaImage) -> Option<Bounds> {
    let mut left = image.width();
    let mut top = image.height();
    let mut right = 0;
    let mut bottom = 0;
    let mut found = false;
    for (x, y, pixel) in image.enumerate_pixels() {
        if pixel[3] == 0 {
            continue;
        }
        found = true;
        left = left.min(x);
        top = top.min(y);
        right = right.max(x);
        bottom = bottom.max(y);
    }
    found.then_some(Bounds {
        left,
        top,
        right,
        bottom,
    })
}

fn valid_pose_id(pose_id: &str) -> bool {
    pose_id
        .strip_prefix("WJPS-")
        .is_some_and(|ordinal| ordinal.len() == 4 && ordinal.chars().all(|c| c.is_ascii_digit()))
}

fn load_rgba(path: &Path) -> Result<RgbaImage, PhazerRegenerationError> {
    image::open(path)
        .map(|image| image.into_rgba8())
        .map_err(|source| PhazerRegenerationError::Image {
            path: path.to_path_buf(),
            source,
        })
}

fn save_png(image: &RgbaImage, path: &Path) -> Result<(), PhazerRegenerationError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|source| PhazerRegenerationError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    image
        .save_with_format(path, image::ImageFormat::Png)
        .map_err(|source| PhazerRegenerationError::Image {
            path: path.to_path_buf(),
            source,
        })
}

fn write_runtime_graph_fast(
    graph: &crate::PixelGraph,
    path: &Path,
) -> Result<String, PhazerRegenerationError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|source| PhazerRegenerationError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    let file = fs::File::create(path).map_err(|source| PhazerRegenerationError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let mut encoder = GzEncoder::new(BufWriter::new(file), Compression::fast());
    serde_json::to_writer(&mut encoder, graph).map_err(|source| {
        PhazerRegenerationError::Invariant(format!(
            "failed to serialize runtime graph {}: {source}",
            graph.source_record_id
        ))
    })?;
    let mut writer = encoder
        .finish()
        .map_err(|source| PhazerRegenerationError::Io {
            path: path.to_path_buf(),
            source,
        })?;
    writer
        .flush()
        .map_err(|source| PhazerRegenerationError::Io {
            path: path.to_path_buf(),
            source,
        })?;
    sha256_file(path)
}

fn sha256_file(path: &Path) -> Result<String, PhazerRegenerationError> {
    let bytes = fs::read(path).map_err(|source| PhazerRegenerationError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    Ok(format!("{:x}", Sha256::digest(bytes)))
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), PhazerRegenerationError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|source| PhazerRegenerationError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    let bytes = serde_json::to_vec_pretty(value).map_err(|source| {
        PhazerRegenerationError::Invariant(format!("failed to serialize JSON: {source}"))
    })?;
    fs::write(path, bytes).map_err(|source| PhazerRegenerationError::Io {
        path: path.to_path_buf(),
        source,
    })
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, PhazerRegenerationError> {
    let bytes = fs::read(path).map_err(|source| PhazerRegenerationError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    serde_json::from_slice(&bytes).map_err(|source| {
        PhazerRegenerationError::Invariant(format!(
            "failed to parse JSON at {}: {source}",
            path.display()
        ))
    })
}

fn median<T: Ord + Copy>(mut values: Vec<T>) -> T {
    values.sort_unstable();
    values[values.len() / 2]
}

fn relative_path(root: &Path, path: &Path) -> Result<String, PhazerRegenerationError> {
    path.strip_prefix(root)
        .map(|relative| relative.to_string_lossy().replace('\\', "/"))
        .map_err(|_| {
            PhazerRegenerationError::Invariant(format!(
                "{} is not under {}",
                path.display(),
                root.display()
            ))
        })
}

fn require(condition: bool, message: impl Into<String>) -> Result<(), PhazerRegenerationError> {
    if condition {
        Ok(())
    } else {
        Err(PhazerRegenerationError::Invariant(message.into()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matte_removal_keeps_character_colors() {
        let mut image = RgbaImage::new(2, 1);
        image.put_pixel(0, 0, Rgba([255, 0, 255, 255]));
        image.put_pixel(1, 0, Rgba([12, 130, 220, 255]));
        let matted = remove_magenta_matte(&image);
        assert_eq!(matted.get_pixel(0, 0)[3], 0);
        assert_eq!(*matted.get_pixel(1, 0), Rgba([12, 130, 220, 255]));
    }

    #[test]
    fn mask_lock_preserves_authored_alpha() {
        let mut authored = RgbaImage::new(2, 1);
        authored.put_pixel(0, 0, Rgba([10, 20, 30, 128]));
        let mut candidate = RgbaImage::new(2, 1);
        candidate.put_pixel(0, 0, Rgba([40, 50, 60, 255]));
        candidate.put_pixel(1, 0, Rgba([70, 80, 90, 255]));
        let (locked, retained) = lock_authored_mask(&authored, &candidate);
        assert_eq!(retained, 1);
        assert_eq!(*locked.get_pixel(0, 0), Rgba([40, 50, 60, 128]));
        assert_eq!(locked.get_pixel(1, 0)[3], 0);
    }
}
