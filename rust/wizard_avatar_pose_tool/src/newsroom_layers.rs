use crate::admission::{EvidenceFile, VisualReview, VisualReviewStatus};
use crate::newsroom_admission::{
    NewsroomAdmissionLedger, NewsroomAdmissionStatus, NewsroomSourceVerificationReport,
};
use crate::overlay::{
    build_transparent_overlay, composite_graph_over_source, OverlayCounts, OverlayPalette,
};
use crate::pixel_graph::{
    build_exact_pixel_graph, project_pixel_graph, read_pixel_graph, write_pixel_graph, FrameSpec,
    NormalizedPose, PixelGraphError,
};
use crate::verification::{verify_pose_graph, PoseGraphMetrics, VerificationConfig};
use image::{Rgba, RgbaImage};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::fs::{self, File};
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};

pub const NEWSROOM_LAYER_SCHEMA_VERSION: u32 = 1;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NewsroomLayerAdmissionStatus {
    Queued,
    AwaitingVisualComparison,
    VisuallyVerified,
    FailedVerification,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomLayerAdmissionEntry {
    pub sequence: usize,
    pub source_id: String,
    pub source_graph_sha256: String,
    pub source_target_spec_sha256: String,
    pub status: NewsroomLayerAdmissionStatus,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub verification_report_path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub recomposition_iou: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub recomposition_color_fidelity: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomLayerAdmissionLedger {
    pub schema_version: u32,
    pub ledger_id: String,
    pub source_admission_ledger_path: String,
    pub source_admission_ledger_sha256: String,
    pub source_manifest_sha256: String,
    pub target_specs_path: String,
    pub target_specs_sha256: String,
    pub expected_source_count: usize,
    pub verified_source_count: usize,
    pub awaiting_visual_comparison_count: usize,
    pub failed_source_count: usize,
    pub queued_source_count: usize,
    pub entries: Vec<NewsroomLayerAdmissionEntry>,
}

#[derive(Clone, Debug)]
pub struct NewsroomLayerCompileConfig {
    pub repo_root: PathBuf,
    pub source_id: String,
}

#[derive(Clone, Debug)]
pub struct NewsroomLayerVisualReviewConfig {
    pub repo_root: PathBuf,
    pub source_id: String,
    pub reviewer: String,
    pub expected_source_graph_sha256: String,
    pub expected_target_specs_sha256: String,
    pub finding: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomLayerTargetReport {
    pub target_id: String,
    pub semantic_layer: String,
    pub order: i32,
    pub anchor: [u32; 2],
    pub occlusion: String,
    pub covers_manifest_targets: Vec<String>,
    pub foreground_pixel_count: u64,
    pub pixel_graph: EvidenceFile,
    pub graph_render: EvidenceFile,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomLayerVerificationReport {
    pub schema_version: u32,
    pub source_id: String,
    pub source_manifest_sha256: String,
    pub source_admission_ledger_sha256: String,
    pub target_specs_sha256: String,
    pub source_target_spec_sha256: String,
    pub source_graph_sha256: String,
    pub frame: FrameSpec,
    pub source_foreground_pixels: u64,
    pub assigned_source_pixels: u64,
    pub overlap_pixels: u64,
    pub unassigned_pixels: u64,
    pub targets: Vec<NewsroomLayerTargetReport>,
    pub recomposition_metrics: PoseGraphMetrics,
    pub overlay_counts: OverlayCounts,
    pub recomposition_exact: bool,
    pub layer_map: EvidenceFile,
    pub recomposed_render: EvidenceFile,
    pub transparent_overlay: EvidenceFile,
    pub recomposed_over_source_png: EvidenceFile,
    pub passed: bool,
    pub visual_review: VisualReview,
    pub policy: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct NewsroomTargetSpecs {
    schema_version: u32,
    source_manifest_sha256: String,
    canvas: FrameSpec,
    selection_policy: String,
    sources: Vec<NewsroomTargetSource>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct NewsroomTargetSource {
    source_id: String,
    source_graph_sha256: String,
    targets: Vec<NewsroomTarget>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct NewsroomTarget {
    id: String,
    layer: String,
    order: i32,
    selection: TargetSelection,
    anchor: [u32; 2],
    occlusion: String,
    covers_manifest_targets: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
enum TargetSelection {
    Rect {
        x: u32,
        y: u32,
        width: u32,
        height: u32,
    },
    Polygon {
        points: Vec<[u32; 2]>,
        #[serde(default)]
        exclude_neutral: Option<NeutralExclusion>,
    },
    Remainder,
}

impl TargetSelection {
    fn selects(&self, x: u32, y: u32, pixel: &Rgba<u8>) -> bool {
        let coordinate_match = match self {
            Self::Rect {
                x: left,
                y: top,
                width,
                height,
            } => x >= *left && x < *left + *width && y >= *top && y < *top + *height,
            Self::Polygon { points, .. } => point_in_polygon(x, y, points),
            Self::Remainder => false,
        };
        if !coordinate_match {
            return false;
        }
        match self {
            Self::Polygon {
                exclude_neutral: Some(exclusion),
                ..
            } => !exclusion.matches(pixel),
            _ => true,
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct NeutralExclusion {
    min_luma: u8,
    max_chroma: u8,
}

impl NeutralExclusion {
    fn matches(self, pixel: &Rgba<u8>) -> bool {
        let minimum = pixel[0].min(pixel[1]).min(pixel[2]);
        let maximum = pixel[0].max(pixel[1]).max(pixel[2]);
        minimum >= self.min_luma && maximum - minimum <= self.max_chroma
    }
}

fn point_in_polygon(x: u32, y: u32, points: &[[u32; 2]]) -> bool {
    let sample_x = f64::from(x) + 0.5;
    let sample_y = f64::from(y) + 0.5;
    let mut inside = false;
    let mut previous = points[points.len() - 1];
    for &current in points {
        let previous_x = f64::from(previous[0]);
        let previous_y = f64::from(previous[1]);
        let current_x = f64::from(current[0]);
        let current_y = f64::from(current[1]);
        if (current_y > sample_y) != (previous_y > sample_y) {
            let intersection_x = (previous_x - current_x) * (sample_y - current_y)
                / (previous_y - current_y)
                + current_x;
            if sample_x < intersection_x {
                inside = !inside;
            }
        }
        previous = current;
    }
    inside
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceManifest {
    schema_version: u32,
    status: String,
    style_authority: Vec<String>,
    runtime_raster_allowed: bool,
    visual_overlay_required: bool,
    minimum_visual_alignment: f64,
    sources: Vec<SourceManifestRecord>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceManifestRecord {
    id: String,
    file: String,
    sha256: String,
    kind: String,
    #[serde(default)]
    targets: Vec<String>,
    #[serde(default)]
    character_pixels_canonical: Option<bool>,
}

impl SourceManifestRecord {
    fn is_admissible(&self) -> bool {
        self.kind != "composition_reference_only"
    }
}

#[derive(Debug, thiserror::Error)]
pub enum NewsroomLayerError {
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
    #[error("JSON error at {path}: {source}")]
    Json {
        path: PathBuf,
        #[source]
        source: serde_json::Error,
    },
    #[error(transparent)]
    PixelGraph(#[from] PixelGraphError),
    #[error("newsroom layer invariant failed: {0}")]
    Invariant(String),
}

pub fn compile_one_newsroom_layer_source(
    config: &NewsroomLayerCompileConfig,
) -> Result<NewsroomLayerVerificationReport, NewsroomLayerError> {
    let bindings = load_bindings(&config.repo_root)?;
    let mut ledger = load_or_initialize_layer_ledger(&config.repo_root, &bindings)?;
    if ledger.failed_source_count > 0 {
        return Err(NewsroomLayerError::Invariant(
            "a failed layer split must be corrected before serial compilation continues".into(),
        ));
    }
    if ledger.awaiting_visual_comparison_count > 0 {
        return Err(NewsroomLayerError::Invariant(
            "approve the pending layer comparison before compiling another source".into(),
        ));
    }
    let next = ledger
        .entries
        .iter()
        .find(|entry| entry.status == NewsroomLayerAdmissionStatus::Queued)
        .ok_or_else(|| NewsroomLayerError::Invariant("no queued layer source remains".into()))?;
    if next.source_id != config.source_id {
        return Err(NewsroomLayerError::Invariant(format!(
            "serial layer compilation requires {} before {}",
            next.source_id, config.source_id
        )));
    }

    let source_spec = bindings
        .specs
        .sources
        .iter()
        .find(|source| source.source_id == config.source_id)
        .ok_or_else(|| {
            NewsroomLayerError::Invariant("source is absent from target specs".into())
        })?;
    let source_target_spec_sha256 = source_spec_sha256(source_spec)?;
    let admission_entry = bindings
        .source_admission
        .entries
        .iter()
        .find(|entry| entry.source_id == config.source_id)
        .ok_or_else(|| {
            NewsroomLayerError::Invariant("source is absent from admission ledger".into())
        })?;
    let graph_path = config
        .repo_root
        .join(admission_entry.graph_path.as_deref().ok_or_else(|| {
            NewsroomLayerError::Invariant("approved source graph path is missing".into())
        })?);
    if sha256_file(&graph_path)? != source_spec.source_graph_sha256 {
        return Err(NewsroomLayerError::Invariant(
            "approved source graph changed after target specification".into(),
        ));
    }
    let source_graph = read_pixel_graph(&graph_path)?;
    let source_render = project_pixel_graph(&source_graph)?;
    if source_render.dimensions() != (bindings.specs.canvas.width, bindings.specs.canvas.height) {
        return Err(NewsroomLayerError::Invariant(
            "approved source graph does not use the target-spec canvas".into(),
        ));
    }

    let split = split_source_pixels(&source_render, &source_spec.targets)?;
    let evidence_dir = layer_evidence_dir(&config.repo_root, &config.source_id);
    fs::create_dir_all(&evidence_dir).map_err(|source| NewsroomLayerError::Io {
        path: evidence_dir.clone(),
        source,
    })?;

    let mut target_reports = Vec::with_capacity(source_spec.targets.len());
    for (target, image) in source_spec.targets.iter().zip(&split.target_images) {
        let normalized = NormalizedPose {
            image: image.clone(),
            offset_x: 0,
            offset_y: 0,
        };
        let graph = build_exact_pixel_graph(
            format!("newsroom_layer_{}", target.id),
            &target.id,
            &source_graph.source_sha256,
            source_render.dimensions(),
            &normalized,
        );
        if graph.foreground_pixel_count == 0 {
            return Err(NewsroomLayerError::Invariant(format!(
                "target {} selected no source pixels",
                target.id
            )));
        }
        let projected = project_pixel_graph(&graph)?;
        if projected != *image {
            return Err(NewsroomLayerError::Invariant(format!(
                "target {} graph did not round-trip exactly",
                target.id
            )));
        }
        let graph_path = evidence_dir.join(format!("{}.pixelgraph.json.gz", target.id));
        let graph_sha256 = write_pixel_graph(&graph, &graph_path)?;
        let render_path = evidence_dir.join(format!("{}.graph-render.png", target.id));
        let graph_render = save_png_evidence(&config.repo_root, &projected, &render_path)?;
        target_reports.push(NewsroomLayerTargetReport {
            target_id: target.id.clone(),
            semantic_layer: target.layer.clone(),
            order: target.order,
            anchor: target.anchor,
            occlusion: target.occlusion.clone(),
            covers_manifest_targets: target.covers_manifest_targets.clone(),
            foreground_pixel_count: graph.foreground_pixel_count,
            pixel_graph: EvidenceFile {
                path: repo_relative(&config.repo_root, &graph_path)?,
                sha256: graph_sha256,
            },
            graph_render,
        });
    }

    let exact_config = exact_verification_config();
    let metrics = verify_pose_graph(&source_render, &split.recomposed, exact_config)
        .map_err(|error| NewsroomLayerError::Invariant(error.to_string()))?;
    let transparent_overlay = build_transparent_overlay(
        &source_render,
        &split.recomposed,
        exact_config,
        OverlayPalette::default(),
    )
    .map_err(|error| NewsroomLayerError::Invariant(error.to_string()))?;
    let source_report_path = config.repo_root.join(
        admission_entry
            .verification_report_path
            .as_deref()
            .ok_or_else(|| {
                NewsroomLayerError::Invariant("approved source verification path is missing".into())
            })?,
    );
    let source_report: NewsroomSourceVerificationReport = read_json(&source_report_path)?;
    let source_original = load_rgba(&config.repo_root.join(&source_report.source_original.path))?;
    let recomposed_over_source =
        composite_graph_over_source(&source_original, &split.recomposed, 128)
            .map_err(|error| NewsroomLayerError::Invariant(error.to_string()))?;

    let layer_map = save_png_evidence(
        &config.repo_root,
        &split.layer_map,
        &evidence_dir.join("layer-map.png"),
    )?;
    let recomposed_render = save_png_evidence(
        &config.repo_root,
        &split.recomposed,
        &evidence_dir.join("recomposed-render.png"),
    )?;
    let transparent_overlay_file = save_png_evidence(
        &config.repo_root,
        &transparent_overlay.image,
        &evidence_dir.join("transparent-overlay.png"),
    )?;
    let recomposed_over_source_png = save_png_evidence(
        &config.repo_root,
        &recomposed_over_source,
        &evidence_dir.join("recomposed-over-source-png.png"),
    )?;
    let recomposition_exact = split.recomposed == source_render;
    let passed = recomposition_exact
        && split.overlap_pixels == 0
        && split.unassigned_pixels == 0
        && split.assigned_source_pixels == source_graph.foreground_pixel_count
        && metrics.silhouette_iou == 1.0
        && metrics.foreground_color_match_ratio == 1.0
        && metrics.foreground_color_fidelity == 1.0;
    let report = NewsroomLayerVerificationReport {
        schema_version: NEWSROOM_LAYER_SCHEMA_VERSION,
        source_id: config.source_id.clone(),
        source_manifest_sha256: bindings.manifest_sha256.clone(),
        source_admission_ledger_sha256: bindings.source_admission_sha256.clone(),
        target_specs_sha256: bindings.specs_sha256.clone(),
        source_target_spec_sha256,
        source_graph_sha256: source_spec.source_graph_sha256.clone(),
        frame: bindings.specs.canvas,
        source_foreground_pixels: source_graph.foreground_pixel_count,
        assigned_source_pixels: split.assigned_source_pixels,
        overlap_pixels: split.overlap_pixels,
        unassigned_pixels: split.unassigned_pixels,
        targets: target_reports,
        recomposition_metrics: metrics,
        overlay_counts: transparent_overlay.counts,
        recomposition_exact,
        layer_map,
        recomposed_render,
        transparent_overlay: transparent_overlay_file,
        recomposed_over_source_png,
        passed,
        visual_review: VisualReview {
            status: VisualReviewStatus::Pending,
            reviewer: String::new(),
            finding: String::new(),
        },
        policy: "Evidence-only native pixel-graph classification. Every occupied source pixel is owned exactly once and recomposes byte-for-byte. Visual approval does not create or update runtime assets; promotion requires a separate command.".into(),
    };
    let report_path = evidence_dir.join("verification.json");
    write_json(&report_path, &report)?;

    let ledger_entry = ledger
        .entries
        .iter_mut()
        .find(|entry| entry.source_id == config.source_id)
        .expect("ledger and target specs were validated");
    ledger_entry.status = if passed {
        NewsroomLayerAdmissionStatus::AwaitingVisualComparison
    } else {
        NewsroomLayerAdmissionStatus::FailedVerification
    };
    ledger_entry.verification_report_path = Some(repo_relative(&config.repo_root, &report_path)?);
    ledger_entry.recomposition_iou = Some(metrics.silhouette_iou);
    ledger_entry.recomposition_color_fidelity = Some(metrics.foreground_color_fidelity);
    update_layer_ledger_counts(&mut ledger);
    write_json(&layer_ledger_path(&config.repo_root), &ledger)?;
    Ok(report)
}

pub fn approve_newsroom_layer_comparison(
    config: &NewsroomLayerVisualReviewConfig,
) -> Result<NewsroomLayerVerificationReport, NewsroomLayerError> {
    if config.reviewer.trim().is_empty() || config.finding.trim().is_empty() {
        return Err(NewsroomLayerError::Invariant(
            "layer approval requires a reviewer and concrete visual finding".into(),
        ));
    }
    let bindings = load_bindings(&config.repo_root)?;
    let mut ledger = load_or_initialize_layer_ledger(&config.repo_root, &bindings)?;
    let source_spec = bindings
        .specs
        .sources
        .iter()
        .find(|source| source.source_id == config.source_id)
        .ok_or_else(|| {
            NewsroomLayerError::Invariant("source is absent from target specs".into())
        })?;
    if config.expected_target_specs_sha256 != source_spec_sha256(source_spec)? {
        return Err(NewsroomLayerError::Invariant(
            "reviewed source target-spec hash does not match current target specs".into(),
        ));
    }
    let entry = ledger
        .entries
        .iter()
        .find(|entry| entry.source_id == config.source_id)
        .ok_or_else(|| {
            NewsroomLayerError::Invariant("source is absent from layer ledger".into())
        })?;
    if entry.status != NewsroomLayerAdmissionStatus::AwaitingVisualComparison {
        return Err(NewsroomLayerError::Invariant(format!(
            "{} is not awaiting layer visual comparison",
            config.source_id
        )));
    }
    if config.expected_source_graph_sha256 != entry.source_graph_sha256 {
        return Err(NewsroomLayerError::Invariant(
            "reviewed source graph hash does not match the layer evidence".into(),
        ));
    }
    let report_path = config.repo_root.join(
        entry
            .verification_report_path
            .as_deref()
            .ok_or_else(|| NewsroomLayerError::Invariant("layer report path is missing".into()))?,
    );
    let mut report: NewsroomLayerVerificationReport = read_json(&report_path)?;
    if !report.passed
        || !report.recomposition_exact
        || report.visual_review.status != VisualReviewStatus::Pending
        || report.source_graph_sha256 != config.expected_source_graph_sha256
        || report.source_target_spec_sha256 != config.expected_target_specs_sha256
    {
        return Err(NewsroomLayerError::Invariant(
            "layer report is not eligible for visual approval".into(),
        ));
    }
    let mut evidence = vec![
        &report.layer_map,
        &report.recomposed_render,
        &report.transparent_overlay,
        &report.recomposed_over_source_png,
    ];
    for target in &report.targets {
        evidence.push(&target.pixel_graph);
        evidence.push(&target.graph_render);
    }
    for file in evidence {
        if sha256_file(&config.repo_root.join(&file.path))? != file.sha256 {
            return Err(NewsroomLayerError::Invariant(format!(
                "layer evidence changed after generation: {}",
                file.path
            )));
        }
    }

    let source_entry = bindings
        .source_admission
        .entries
        .iter()
        .find(|entry| entry.source_id == config.source_id)
        .ok_or_else(|| NewsroomLayerError::Invariant("approved source entry disappeared".into()))?;
    let source_graph = read_pixel_graph(config.repo_root.join(
        source_entry.graph_path.as_deref().ok_or_else(|| {
            NewsroomLayerError::Invariant("approved graph path disappeared".into())
        })?,
    ))?;
    let source_render = project_pixel_graph(&source_graph)?;
    let mut recomposed = RgbaImage::new(report.frame.width, report.frame.height);
    let mut assigned = 0_u64;
    for target in &report.targets {
        let graph = read_pixel_graph(config.repo_root.join(&target.pixel_graph.path))?;
        let rendered = project_pixel_graph(&graph)?;
        for (output, pixel) in recomposed.pixels_mut().zip(rendered.pixels()) {
            if pixel[3] == 0 {
                continue;
            }
            if output[3] > 0 {
                return Err(NewsroomLayerError::Invariant(
                    "review-time target graphs overlap".into(),
                ));
            }
            *output = *pixel;
            assigned += 1;
        }
    }
    if assigned != report.assigned_source_pixels || recomposed != source_render {
        return Err(NewsroomLayerError::Invariant(
            "review-time layer recomposition is no longer exact".into(),
        ));
    }
    let metrics = verify_pose_graph(&source_render, &recomposed, exact_verification_config())
        .map_err(|error| NewsroomLayerError::Invariant(error.to_string()))?;
    if metrics != report.recomposition_metrics || metrics.silhouette_iou != 1.0 {
        return Err(NewsroomLayerError::Invariant(
            "review-time recomposition metrics changed".into(),
        ));
    }

    report.visual_review = VisualReview {
        status: VisualReviewStatus::Approved,
        reviewer: config.reviewer.clone(),
        finding: config.finding.clone(),
    };
    write_json(&report_path, &report)?;
    let ledger_entry = ledger
        .entries
        .iter_mut()
        .find(|entry| entry.source_id == config.source_id)
        .expect("source presence checked above");
    ledger_entry.status = NewsroomLayerAdmissionStatus::VisuallyVerified;
    update_layer_ledger_counts(&mut ledger);
    write_json(&layer_ledger_path(&config.repo_root), &ledger)?;
    Ok(report)
}

struct Bindings {
    specs: NewsroomTargetSpecs,
    specs_sha256: String,
    manifest_sha256: String,
    source_admission: NewsroomAdmissionLedger,
    source_admission_sha256: String,
}

fn load_bindings(repo_root: &Path) -> Result<Bindings, NewsroomLayerError> {
    let specs_path = target_specs_path(repo_root);
    let specs: NewsroomTargetSpecs = read_json(&specs_path)?;
    let specs_sha256 = sha256_file(&specs_path)?;
    let manifest_path = source_manifest_path(repo_root);
    let manifest: SourceManifest = read_json(&manifest_path)?;
    let manifest_sha256 = sha256_file(&manifest_path)?;
    let source_admission_path = source_admission_ledger_path(repo_root);
    let source_admission: NewsroomAdmissionLedger = read_json(&source_admission_path)?;
    let source_admission_sha256 = sha256_file(&source_admission_path)?;
    validate_bindings(&specs, &manifest, &manifest_sha256, &source_admission)?;
    Ok(Bindings {
        specs,
        specs_sha256,
        manifest_sha256,
        source_admission,
        source_admission_sha256,
    })
}

fn validate_bindings(
    specs: &NewsroomTargetSpecs,
    manifest: &SourceManifest,
    manifest_sha256: &str,
    source_admission: &NewsroomAdmissionLedger,
) -> Result<(), NewsroomLayerError> {
    if specs.schema_version != NEWSROOM_LAYER_SCHEMA_VERSION
        || specs.canvas.width == 0
        || specs.canvas.height == 0
        || specs.selection_policy.trim().is_empty()
        || specs.source_manifest_sha256 != manifest_sha256
    {
        return Err(NewsroomLayerError::Invariant(
            "target specs are invalid or not bound to the source manifest".into(),
        ));
    }
    if manifest.schema_version != 2
        || manifest.status != "source_evidence_only"
        || manifest.runtime_raster_allowed
        || !manifest.visual_overlay_required
        || manifest.minimum_visual_alignment < 0.95
        || manifest.style_authority.is_empty()
    {
        return Err(NewsroomLayerError::Invariant(
            "source manifest policy is not fail-closed".into(),
        ));
    }
    if source_admission.source_manifest_sha256 != manifest_sha256
        || source_admission.verified_source_count != source_admission.expected_source_count
        || source_admission.awaiting_visual_comparison_count != 0
        || source_admission.failed_source_count != 0
        || source_admission.queued_source_count != 0
    {
        return Err(NewsroomLayerError::Invariant(
            "all source graphs must be visually verified against the bound manifest first".into(),
        ));
    }
    let admissible = manifest
        .sources
        .iter()
        .filter(|record| record.is_admissible())
        .collect::<Vec<_>>();
    if admissible.len() != specs.sources.len() || admissible.len() != source_admission.entries.len()
    {
        return Err(NewsroomLayerError::Invariant(
            "manifest, source admission, and target specs have different source counts".into(),
        ));
    }
    let mut source_ids = BTreeSet::new();
    let mut target_ids = BTreeSet::new();
    for ((record, spec), admission) in admissible
        .iter()
        .zip(&specs.sources)
        .zip(&source_admission.entries)
    {
        if record.id != spec.source_id
            || record.id != admission.source_id
            || admission.status != NewsroomAdmissionStatus::VisuallyVerified
            || admission.graph_sha256.as_deref() != Some(spec.source_graph_sha256.as_str())
            || !source_ids.insert(spec.source_id.as_str())
        {
            return Err(NewsroomLayerError::Invariant(format!(
                "source binding mismatch for {}",
                record.id
            )));
        }
        if record.file.trim().is_empty()
            || record.sha256.len() != 64
            || record.character_pixels_canonical == Some(true)
            || spec.targets.is_empty()
        {
            return Err(NewsroomLayerError::Invariant(format!(
                "invalid source or target metadata for {}",
                record.id
            )));
        }
        validate_target_source(spec, record, specs.canvas, &mut target_ids)?;
    }
    Ok(())
}

fn validate_target_source<'a>(
    source: &'a NewsroomTargetSource,
    manifest: &SourceManifestRecord,
    frame: FrameSpec,
    global_target_ids: &mut BTreeSet<&'a str>,
) -> Result<(), NewsroomLayerError> {
    let remainder_count = source
        .targets
        .iter()
        .filter(|target| matches!(&target.selection, TargetSelection::Remainder))
        .count();
    if remainder_count > 1 {
        return Err(NewsroomLayerError::Invariant(format!(
            "{} has more than one remainder target",
            source.source_id
        )));
    }
    let mut covered = Vec::new();
    for target in &source.targets {
        if target.id.trim().is_empty()
            || target.layer.trim().is_empty()
            || target.occlusion.trim().is_empty()
            || target.covers_manifest_targets.is_empty()
            || !global_target_ids.insert(&target.id)
            || target.anchor[0] >= frame.width
            || target.anchor[1] >= frame.height
        {
            return Err(NewsroomLayerError::Invariant(format!(
                "invalid target metadata for {}",
                target.id
            )));
        }
        if let TargetSelection::Rect {
            x,
            y,
            width,
            height,
        } = &target.selection
        {
            let right = x.checked_add(*width);
            let bottom = y.checked_add(*height);
            if *width == 0
                || *height == 0
                || right.is_none()
                || bottom.is_none()
                || right.unwrap_or(u32::MAX) > frame.width
                || bottom.unwrap_or(u32::MAX) > frame.height
            {
                return Err(NewsroomLayerError::Invariant(format!(
                    "target rectangle exceeds canvas for {}",
                    target.id
                )));
            }
        }
        if let TargetSelection::Polygon { points, .. } = &target.selection {
            if points.len() < 3
                || points
                    .iter()
                    .any(|point| point[0] > frame.width || point[1] > frame.height)
            {
                return Err(NewsroomLayerError::Invariant(format!(
                    "target polygon is invalid for {}",
                    target.id
                )));
            }
        }
        covered.extend(target.covers_manifest_targets.iter().cloned());
    }
    covered.sort();
    let mut expected = manifest.targets.clone();
    expected.sort();
    if covered != expected {
        return Err(NewsroomLayerError::Invariant(format!(
            "target coverage for {} does not exactly match its manifest targets",
            source.source_id
        )));
    }
    Ok(())
}

struct SplitResult {
    target_images: Vec<RgbaImage>,
    recomposed: RgbaImage,
    layer_map: RgbaImage,
    assigned_source_pixels: u64,
    overlap_pixels: u64,
    unassigned_pixels: u64,
}

fn split_source_pixels(
    source: &RgbaImage,
    targets: &[NewsroomTarget],
) -> Result<SplitResult, NewsroomLayerError> {
    let remainder = targets
        .iter()
        .position(|target| matches!(&target.selection, TargetSelection::Remainder));
    let mut target_images = (0..targets.len())
        .map(|_| RgbaImage::new(source.width(), source.height()))
        .collect::<Vec<_>>();
    let mut recomposed = RgbaImage::new(source.width(), source.height());
    let mut layer_map = RgbaImage::new(source.width(), source.height());
    let mut assigned_source_pixels = 0_u64;
    let mut overlap_pixels = 0_u64;
    let mut unassigned_pixels = 0_u64;
    let mut first_conflict = None;

    for (x, y, pixel) in source.enumerate_pixels() {
        if pixel[3] == 0 {
            continue;
        }
        let matches = targets
            .iter()
            .enumerate()
            .filter(|(_, target)| target.selection.selects(x, y, pixel))
            .map(|(index, _)| index)
            .collect::<Vec<_>>();
        let owner = match matches.as_slice() {
            [index] => Some(*index),
            [] => remainder,
            _ => {
                overlap_pixels += 1;
                first_conflict.get_or_insert((x, y));
                None
            }
        };
        let Some(owner) = owner else {
            if matches.is_empty() {
                unassigned_pixels += 1;
                first_conflict.get_or_insert((x, y));
            }
            continue;
        };
        target_images[owner].put_pixel(x, y, *pixel);
        recomposed.put_pixel(x, y, *pixel);
        let color = ownership_color(owner);
        layer_map.put_pixel(x, y, Rgba([color[0], color[1], color[2], pixel[3]]));
        assigned_source_pixels += 1;
    }
    if overlap_pixels > 0 || unassigned_pixels > 0 {
        let location = first_conflict
            .map(|(x, y)| format!("; first conflict at ({x},{y})"))
            .unwrap_or_default();
        return Err(NewsroomLayerError::Invariant(format!(
            "target ownership is ambiguous: {overlap_pixels} overlap pixels, {unassigned_pixels} unassigned pixels{location}"
        )));
    }
    Ok(SplitResult {
        target_images,
        recomposed,
        layer_map,
        assigned_source_pixels,
        overlap_pixels,
        unassigned_pixels,
    })
}

fn ownership_color(index: usize) -> [u8; 3] {
    const COLORS: [[u8; 3]; 12] = [
        [0, 168, 232],
        [255, 190, 0],
        [229, 27, 125],
        [24, 173, 98],
        [107, 78, 255],
        [255, 100, 60],
        [0, 190, 190],
        [180, 80, 210],
        [75, 110, 145],
        [150, 200, 45],
        [245, 75, 95],
        [140, 95, 45],
    ];
    COLORS[index % COLORS.len()]
}

fn exact_verification_config() -> VerificationConfig {
    VerificationConfig {
        foreground_alpha_threshold: 1,
        color_match_tolerance: 0,
    }
}

fn load_or_initialize_layer_ledger(
    repo_root: &Path,
    bindings: &Bindings,
) -> Result<NewsroomLayerAdmissionLedger, NewsroomLayerError> {
    let path = layer_ledger_path(repo_root);
    if path.exists() {
        let mut ledger: NewsroomLayerAdmissionLedger = read_json(&path)?;
        rebind_queued_layer_specs(&mut ledger, bindings)?;
        validate_layer_ledger(&ledger, bindings)?;
        write_json(&path, &ledger)?;
        return Ok(ledger);
    }
    Ok(NewsroomLayerAdmissionLedger {
        schema_version: NEWSROOM_LAYER_SCHEMA_VERSION,
        ledger_id: "wizard_joe_newsroom_v2_layer_admission".into(),
        source_admission_ledger_path: repo_relative(
            repo_root,
            &source_admission_ledger_path(repo_root),
        )?,
        source_admission_ledger_sha256: bindings.source_admission_sha256.clone(),
        source_manifest_sha256: bindings.manifest_sha256.clone(),
        target_specs_path: repo_relative(repo_root, &target_specs_path(repo_root))?,
        target_specs_sha256: bindings.specs_sha256.clone(),
        expected_source_count: bindings.specs.sources.len(),
        verified_source_count: 0,
        awaiting_visual_comparison_count: 0,
        failed_source_count: 0,
        queued_source_count: bindings.specs.sources.len(),
        entries: bindings
            .specs
            .sources
            .iter()
            .enumerate()
            .map(|(index, source)| NewsroomLayerAdmissionEntry {
                sequence: index + 1,
                source_id: source.source_id.clone(),
                source_graph_sha256: source.source_graph_sha256.clone(),
                source_target_spec_sha256: source_spec_sha256(source)
                    .expect("validated target specs serialize"),
                status: NewsroomLayerAdmissionStatus::Queued,
                verification_report_path: None,
                recomposition_iou: None,
                recomposition_color_fidelity: None,
            })
            .collect(),
    })
}

fn validate_layer_ledger(
    ledger: &NewsroomLayerAdmissionLedger,
    bindings: &Bindings,
) -> Result<(), NewsroomLayerError> {
    if ledger.schema_version != NEWSROOM_LAYER_SCHEMA_VERSION
        || ledger.ledger_id != "wizard_joe_newsroom_v2_layer_admission"
        || ledger.source_admission_ledger_sha256 != bindings.source_admission_sha256
        || ledger.source_manifest_sha256 != bindings.manifest_sha256
        || ledger.expected_source_count != bindings.specs.sources.len()
        || ledger.entries.len() != bindings.specs.sources.len()
    {
        return Err(NewsroomLayerError::Invariant(
            "layer ledger is stale or not bound to current evidence".into(),
        ));
    }
    for (index, (entry, source)) in ledger
        .entries
        .iter()
        .zip(&bindings.specs.sources)
        .enumerate()
    {
        if entry.sequence != index + 1
            || entry.source_id != source.source_id
            || entry.source_graph_sha256 != source.source_graph_sha256
            || entry.source_target_spec_sha256 != source_spec_sha256(source)?
        {
            return Err(NewsroomLayerError::Invariant(
                "layer ledger order or source hash changed".into(),
            ));
        }
    }
    let mut copy = ledger.clone();
    update_layer_ledger_counts(&mut copy);
    if &copy != ledger {
        return Err(NewsroomLayerError::Invariant(
            "layer ledger counters do not match entries".into(),
        ));
    }
    Ok(())
}

fn rebind_queued_layer_specs(
    ledger: &mut NewsroomLayerAdmissionLedger,
    bindings: &Bindings,
) -> Result<(), NewsroomLayerError> {
    if ledger.schema_version != NEWSROOM_LAYER_SCHEMA_VERSION
        || ledger.ledger_id != "wizard_joe_newsroom_v2_layer_admission"
        || ledger.source_admission_ledger_sha256 != bindings.source_admission_sha256
        || ledger.source_manifest_sha256 != bindings.manifest_sha256
        || ledger.entries.len() != bindings.specs.sources.len()
    {
        return Err(NewsroomLayerError::Invariant(
            "layer ledger cannot be rebound because immutable evidence changed".into(),
        ));
    }
    for (entry, source) in ledger.entries.iter_mut().zip(&bindings.specs.sources) {
        let current_hash = source_spec_sha256(source)?;
        if entry.status == NewsroomLayerAdmissionStatus::Queued {
            entry.source_target_spec_sha256 = current_hash;
        } else if entry.source_target_spec_sha256 != current_hash {
            return Err(NewsroomLayerError::Invariant(format!(
                "reviewed target spec changed for {}; regenerate its evidence before continuing",
                entry.source_id
            )));
        }
    }
    ledger.target_specs_sha256 = bindings.specs_sha256.clone();
    Ok(())
}

fn source_spec_sha256(source: &NewsroomTargetSource) -> Result<String, NewsroomLayerError> {
    let bytes = serde_json::to_vec(source).map_err(|error| {
        NewsroomLayerError::Invariant(format!(
            "could not serialize source target spec for hashing: {error}"
        ))
    })?;
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    Ok(format!("{:x}", hasher.finalize()))
}

fn update_layer_ledger_counts(ledger: &mut NewsroomLayerAdmissionLedger) {
    ledger.verified_source_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == NewsroomLayerAdmissionStatus::VisuallyVerified)
        .count();
    ledger.awaiting_visual_comparison_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == NewsroomLayerAdmissionStatus::AwaitingVisualComparison)
        .count();
    ledger.failed_source_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == NewsroomLayerAdmissionStatus::FailedVerification)
        .count();
    ledger.queued_source_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == NewsroomLayerAdmissionStatus::Queued)
        .count();
}

fn target_specs_path(repo_root: &Path) -> PathBuf {
    repo_root.join("evidence/newsroom-visual-development-v2/target-specs.json")
}

fn source_manifest_path(repo_root: &Path) -> PathBuf {
    repo_root.join("evidence/newsroom-visual-development-v2/scene-manifest.json")
}

fn source_admission_ledger_path(repo_root: &Path) -> PathBuf {
    repo_root.join("docs/newsroom-visual-development-v2/admission-ledger.json")
}

fn layer_ledger_path(repo_root: &Path) -> PathBuf {
    repo_root.join("docs/newsroom-visual-development-v2/layer-admission-ledger.json")
}

fn layer_evidence_dir(repo_root: &Path, source_id: &str) -> PathBuf {
    repo_root
        .join("evidence/newsroom-visual-development-v2/layer-admission")
        .join(source_id)
}

fn load_rgba(path: &Path) -> Result<RgbaImage, NewsroomLayerError> {
    image::open(path)
        .map(|image| image.to_rgba8())
        .map_err(|source| NewsroomLayerError::Image {
            path: path.to_path_buf(),
            source,
        })
}

fn save_png_evidence(
    repo_root: &Path,
    image: &RgbaImage,
    path: &Path,
) -> Result<EvidenceFile, NewsroomLayerError> {
    image
        .save_with_format(path, image::ImageFormat::Png)
        .map_err(|source| NewsroomLayerError::Image {
            path: path.to_path_buf(),
            source,
        })?;
    Ok(EvidenceFile {
        path: repo_relative(repo_root, path)?,
        sha256: sha256_file(path)?,
    })
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, NewsroomLayerError> {
    let file = File::open(path).map_err(|source| NewsroomLayerError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    serde_json::from_reader(BufReader::new(file)).map_err(|source| NewsroomLayerError::Json {
        path: path.to_path_buf(),
        source,
    })
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), NewsroomLayerError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|source| NewsroomLayerError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    let bytes = serde_json::to_vec_pretty(value).map_err(|source| NewsroomLayerError::Json {
        path: path.to_path_buf(),
        source,
    })?;
    fs::write(path, bytes).map_err(|source| NewsroomLayerError::Io {
        path: path.to_path_buf(),
        source,
    })
}

fn sha256_file(path: &Path) -> Result<String, NewsroomLayerError> {
    let file = File::open(path).map_err(|source| NewsroomLayerError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let mut reader = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = reader
            .read(&mut buffer)
            .map_err(|source| NewsroomLayerError::Io {
                path: path.to_path_buf(),
                source,
            })?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    Ok(format!("{:x}", hasher.finalize()))
}

fn repo_relative(repo_root: &Path, path: &Path) -> Result<String, NewsroomLayerError> {
    path.strip_prefix(repo_root)
        .map(|relative| relative.to_string_lossy().into_owned())
        .map_err(|_| {
            NewsroomLayerError::Invariant(format!(
                "{} is outside repository root {}",
                path.display(),
                repo_root.display()
            ))
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn target(id: &str, selection: TargetSelection) -> NewsroomTarget {
        NewsroomTarget {
            id: id.into(),
            layer: "set_piece".into(),
            order: 0,
            selection,
            anchor: [0, 0],
            occlusion: "behind".into(),
            covers_manifest_targets: vec![id.into()],
        }
    }

    #[test]
    fn rectangles_and_remainder_recompose_exactly() {
        let mut source = RgbaImage::new(4, 2);
        source.put_pixel(0, 0, Rgba([10, 20, 30, 255]));
        source.put_pixel(3, 1, Rgba([40, 50, 60, 255]));
        let targets = vec![
            target(
                "left",
                TargetSelection::Rect {
                    x: 0,
                    y: 0,
                    width: 2,
                    height: 2,
                },
            ),
            target("rest", TargetSelection::Remainder),
        ];
        let split = split_source_pixels(&source, &targets).unwrap();
        assert_eq!(split.assigned_source_pixels, 2);
        assert_eq!(split.recomposed, source);
        assert_eq!(split.target_images[0].get_pixel(0, 0)[3], 255);
        assert_eq!(split.target_images[1].get_pixel(3, 1)[3], 255);
    }

    #[test]
    fn occupied_rectangle_overlap_fails_closed() {
        let mut source = RgbaImage::new(3, 1);
        source.put_pixel(1, 0, Rgba([10, 20, 30, 255]));
        let targets = vec![
            target(
                "one",
                TargetSelection::Rect {
                    x: 0,
                    y: 0,
                    width: 2,
                    height: 1,
                },
            ),
            target(
                "two",
                TargetSelection::Rect {
                    x: 1,
                    y: 0,
                    width: 2,
                    height: 1,
                },
            ),
        ];
        assert!(split_source_pixels(&source, &targets).is_err());
    }

    #[test]
    fn uncovered_occupied_pixel_without_remainder_fails_closed() {
        let mut source = RgbaImage::new(3, 1);
        source.put_pixel(2, 0, Rgba([10, 20, 30, 255]));
        let targets = vec![target(
            "left",
            TargetSelection::Rect {
                x: 0,
                y: 0,
                width: 1,
                height: 1,
            },
        )];
        assert!(split_source_pixels(&source, &targets).is_err());
    }

    #[test]
    fn polygon_selects_pixel_centers_inside_its_boundary() {
        let mut source = RgbaImage::new(4, 4);
        source.put_pixel(1, 1, Rgba([10, 20, 30, 255]));
        source.put_pixel(3, 3, Rgba([40, 50, 60, 255]));
        let targets = vec![
            target(
                "inside",
                TargetSelection::Polygon {
                    points: vec![[0, 0], [3, 0], [3, 3], [0, 3]],
                    exclude_neutral: None,
                },
            ),
            target("rest", TargetSelection::Remainder),
        ];
        let split = split_source_pixels(&source, &targets).unwrap();
        assert_eq!(split.target_images[0].get_pixel(1, 1)[3], 255);
        assert_eq!(split.target_images[1].get_pixel(3, 3)[3], 255);
        assert_eq!(split.recomposed, source);
    }
}
