use crate::admission::{EvidenceFile, VisualReview, VisualReviewStatus, MINIMUM_FIDELITY};
use crate::isolation::{isolate_transparent, ForegroundBounds, IsolationConfig};
use crate::overlay::{
    build_transparent_overlay, composite_graph_over_source, OverlayCounts, OverlayPalette,
};
use crate::pixel_graph::{
    build_exact_pixel_graph, normalize_to_frame, project_pixel_graph, read_pixel_graph,
    write_pixel_graph, FrameSpec, PixelGraphError,
};
use crate::verification::{verify_pose_graph, PoseGraphMetrics, VerificationConfig};
use image::RgbaImage;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};

pub const NEWSROOM_ADMISSION_SCHEMA_VERSION: u32 = 1;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NewsroomAdmissionStatus {
    Queued,
    AwaitingVisualComparison,
    VisuallyVerified,
    FailedVerification,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomAdmissionEntry {
    pub sequence: usize,
    pub source_id: String,
    pub source_sha256: String,
    pub source_kind: String,
    pub status: NewsroomAdmissionStatus,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub graph_path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub graph_sha256: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub verification_report_path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub silhouette_iou: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub foreground_color_fidelity: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomAdmissionLedger {
    pub schema_version: u32,
    pub ledger_id: String,
    pub source_manifest_path: String,
    pub source_manifest_sha256: String,
    pub required_fidelity: f64,
    pub expected_source_count: usize,
    pub verified_source_count: usize,
    pub awaiting_visual_comparison_count: usize,
    pub failed_source_count: usize,
    pub queued_source_count: usize,
    pub entries: Vec<NewsroomAdmissionEntry>,
}

#[derive(Clone, Debug)]
pub struct NewsroomAdmitOneConfig {
    pub repo_root: PathBuf,
    pub source_id: String,
    pub isolation: IsolationConfig,
    pub verification: VerificationConfig,
    pub minimum_fidelity: f64,
}

#[derive(Clone, Debug)]
pub struct NewsroomVisualReviewConfig {
    pub repo_root: PathBuf,
    pub source_id: String,
    pub reviewer: String,
    pub expected_graph_sha256: String,
    pub finding: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomSourceVerificationReport {
    pub schema_version: u32,
    pub source_id: String,
    pub source_kind: String,
    pub source_path: String,
    pub source_sha256: String,
    pub source_width: u32,
    pub source_height: u32,
    pub isolated_bounds: Option<ForegroundBounds>,
    pub frame: FrameSpec,
    pub isolation: IsolationConfig,
    pub verification: VerificationConfig,
    pub minimum_fidelity: f64,
    pub metrics: PoseGraphMetrics,
    pub overlay_counts: OverlayCounts,
    pub source_original: EvidenceFile,
    pub source_isolated: EvidenceFile,
    pub isolation_decision: EvidenceFile,
    pub graph_render: EvidenceFile,
    pub transparent_overlay: EvidenceFile,
    pub graph_over_source_png: EvidenceFile,
    pub pixel_graph: EvidenceFile,
    pub graph_round_trip_exact: bool,
    pub passed: bool,
    pub visual_review: VisualReview,
    pub policy: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct NewsroomSourceManifest {
    schema_version: u32,
    status: String,
    style_authority: Vec<String>,
    runtime_raster_allowed: bool,
    visual_overlay_required: bool,
    minimum_visual_alignment: f64,
    sources: Vec<NewsroomSourceRecord>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct NewsroomSourceRecord {
    id: String,
    file: String,
    sha256: String,
    kind: String,
    #[serde(default)]
    targets: Vec<String>,
    #[serde(default)]
    character_pixels_canonical: Option<bool>,
}

impl NewsroomSourceRecord {
    fn is_admissible(&self) -> bool {
        self.kind != "composition_reference_only"
    }
}

#[derive(Debug, thiserror::Error)]
pub enum NewsroomAdmissionError {
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
    #[error("newsroom admission invariant failed: {0}")]
    Invariant(String),
}

pub fn admit_one_newsroom_source(
    config: &NewsroomAdmitOneConfig,
) -> Result<NewsroomSourceVerificationReport, NewsroomAdmissionError> {
    validate_minimum(config.minimum_fidelity)?;
    let manifest_path = manifest_path(&config.repo_root);
    let manifest: NewsroomSourceManifest = read_json(&manifest_path)?;
    validate_manifest(&manifest)?;
    let manifest_hash = sha256_file(&manifest_path)?;
    let ledger_path = ledger_path(&config.repo_root);
    let mut ledger = if ledger_path.exists() {
        let ledger: NewsroomAdmissionLedger = read_json(&ledger_path)?;
        validate_ledger(&ledger, &manifest, &manifest_hash)?;
        ledger
    } else {
        initialize_ledger(&manifest, &manifest_hash, config.minimum_fidelity)
    };

    let next = ledger
        .entries
        .iter()
        .find(|entry| entry.status == NewsroomAdmissionStatus::Queued)
        .ok_or_else(|| {
            NewsroomAdmissionError::Invariant("no queued newsroom source remains".into())
        })?;
    if next.source_id != config.source_id {
        return Err(NewsroomAdmissionError::Invariant(format!(
            "serial admission requires {} before {}",
            next.source_id, config.source_id
        )));
    }
    if ledger
        .entries
        .iter()
        .any(|entry| entry.status == NewsroomAdmissionStatus::AwaitingVisualComparison)
    {
        return Err(NewsroomAdmissionError::Invariant(
            "approve the current visual comparison before ingesting another source".into(),
        ));
    }

    let record = manifest
        .sources
        .iter()
        .find(|record| record.id == config.source_id)
        .ok_or_else(|| {
            NewsroomAdmissionError::Invariant("source is absent from manifest".into())
        })?;
    if !record.is_admissible() {
        return Err(NewsroomAdmissionError::Invariant(
            "composition boards are evidence only and cannot be admitted".into(),
        ));
    }
    let source_path = config
        .repo_root
        .join("evidence/newsroom-visual-development-v2")
        .join(&record.file);
    let source_hash = sha256_file(&source_path)?;
    if source_hash != record.sha256 {
        return Err(NewsroomAdmissionError::Invariant(format!(
            "source hash mismatch for {}",
            record.id
        )));
    }
    let source_bytes = read_bytes(&source_path)?;
    let source = image::load_from_memory(&source_bytes)
        .map_err(|source_error| NewsroomAdmissionError::Image {
            path: source_path.clone(),
            source: source_error,
        })?
        .to_rgba8();
    let isolated = isolate_transparent(&source, config.isolation);
    if isolated.foreground_pixels == 0 {
        return Err(NewsroomAdmissionError::Invariant(
            "background isolation produced an empty newsroom graph".into(),
        ));
    }
    let frame = FrameSpec {
        width: source.width(),
        height: source.height(),
    };
    let normalized = normalize_to_frame(&isolated.image, frame)?;
    let graph = build_exact_pixel_graph(
        format!("newsroom_{}", record.id),
        &record.id,
        &source_hash,
        source.dimensions(),
        &normalized,
    );
    let graph_render = project_pixel_graph(&graph)?;
    let metrics = verify_pose_graph(&normalized.image, &graph_render, config.verification)
        .map_err(|error| NewsroomAdmissionError::Invariant(error.to_string()))?;
    let transparent_overlay = build_transparent_overlay(
        &normalized.image,
        &graph_render,
        config.verification,
        OverlayPalette::default(),
    )
    .map_err(|error| NewsroomAdmissionError::Invariant(error.to_string()))?;
    let graph_over_source = composite_graph_over_source(&source, &graph_render, 128)
        .map_err(|error| NewsroomAdmissionError::Invariant(error.to_string()))?;
    let isolation_decision = build_isolation_decision(&source, &normalized.image)?;

    let evidence_dir = evidence_dir(&config.repo_root, &record.id);
    fs::create_dir_all(&evidence_dir).map_err(|source| NewsroomAdmissionError::Io {
        path: evidence_dir.clone(),
        source,
    })?;
    let source_original = save_png_evidence(&source, &evidence_dir.join("source-original.png"))?;
    let source_isolated =
        save_png_evidence(&normalized.image, &evidence_dir.join("source-isolated.png"))?;
    let isolation_decision_file = save_png_evidence(
        &isolation_decision,
        &evidence_dir.join("isolation-decision.png"),
    )?;
    let graph_render_file =
        save_png_evidence(&graph_render, &evidence_dir.join("graph-render.png"))?;
    let transparent_overlay_file = save_png_evidence(
        &transparent_overlay.image,
        &evidence_dir.join("transparent-overlay.png"),
    )?;
    let graph_over_source_png = save_png_evidence(
        &graph_over_source,
        &evidence_dir.join("graph-over-source-png.png"),
    )?;
    let graph_path = evidence_dir.join("pixelgraph.json.gz");
    let graph_hash = write_pixel_graph(&graph, &graph_path)?;
    let graph_file = EvidenceFile {
        path: repo_relative(&config.repo_root, &graph_path)?,
        sha256: graph_hash,
    };
    let graph_round_trip_exact = read_pixel_graph(&graph_path)? == graph;
    let passed = graph_round_trip_exact && metrics.passes(config.minimum_fidelity);
    let mut report = NewsroomSourceVerificationReport {
        schema_version: NEWSROOM_ADMISSION_SCHEMA_VERSION,
        source_id: record.id.clone(),
        source_kind: record.kind.clone(),
        source_path: repo_relative(&config.repo_root, &source_path)?,
        source_sha256: source_hash,
        source_width: source.width(),
        source_height: source.height(),
        isolated_bounds: isolated.bounds,
        frame,
        isolation: config.isolation,
        verification: config.verification,
        minimum_fidelity: config.minimum_fidelity,
        metrics,
        overlay_counts: transparent_overlay.counts,
        source_original,
        source_isolated,
        isolation_decision: isolation_decision_file,
        graph_render: graph_render_file,
        transparent_overlay: transparent_overlay_file,
        graph_over_source_png,
        pixel_graph: graph_file,
        graph_round_trip_exact,
        passed,
        visual_review: VisualReview {
            status: VisualReviewStatus::Pending,
            reviewer: String::new(),
            finding: String::new(),
        },
        policy: "Exact native-size source graph. Visual approval updates evidence state only. A separate future layer-classification and promotion command must rehash approved evidence before producing any runtime scene graph.".into(),
    };
    let report_path = evidence_dir.join("verification.json");
    write_json(&report_path, &report)?;

    let entry = ledger
        .entries
        .iter_mut()
        .find(|entry| entry.source_id == record.id)
        .expect("manifest and ledger source IDs were validated");
    entry.status = if passed {
        NewsroomAdmissionStatus::AwaitingVisualComparison
    } else {
        NewsroomAdmissionStatus::FailedVerification
    };
    entry.verification_report_path = Some(repo_relative(&config.repo_root, &report_path)?);
    entry.silhouette_iou = Some(metrics.silhouette_iou);
    entry.foreground_color_fidelity = Some(metrics.foreground_color_fidelity);
    update_ledger_counts(&mut ledger);
    write_json(&ledger_path, &ledger)?;

    // Ensure the report in memory exactly matches the persisted visual-review state.
    report.visual_review.status = VisualReviewStatus::Pending;
    Ok(report)
}

pub fn approve_newsroom_visual_comparison(
    config: &NewsroomVisualReviewConfig,
) -> Result<NewsroomSourceVerificationReport, NewsroomAdmissionError> {
    if config.reviewer.trim().is_empty() || config.finding.trim().is_empty() {
        return Err(NewsroomAdmissionError::Invariant(
            "visual approval requires a reviewer and a concrete finding".into(),
        ));
    }
    let manifest_path = manifest_path(&config.repo_root);
    let manifest: NewsroomSourceManifest = read_json(&manifest_path)?;
    validate_manifest(&manifest)?;
    let manifest_hash = sha256_file(&manifest_path)?;
    let ledger_path = ledger_path(&config.repo_root);
    let mut ledger: NewsroomAdmissionLedger = read_json(&ledger_path)?;
    validate_ledger(&ledger, &manifest, &manifest_hash)?;
    let entry = ledger
        .entries
        .iter()
        .find(|entry| entry.source_id == config.source_id)
        .ok_or_else(|| NewsroomAdmissionError::Invariant("source is absent from ledger".into()))?;
    if entry.status != NewsroomAdmissionStatus::AwaitingVisualComparison {
        return Err(NewsroomAdmissionError::Invariant(format!(
            "{} is not awaiting visual comparison",
            config.source_id
        )));
    }
    let report_path = config.repo_root.join(
        entry
            .verification_report_path
            .as_deref()
            .ok_or_else(|| NewsroomAdmissionError::Invariant("missing report path".into()))?,
    );
    let mut report: NewsroomSourceVerificationReport = read_json(&report_path)?;
    if !report.passed || report.visual_review.status != VisualReviewStatus::Pending {
        return Err(NewsroomAdmissionError::Invariant(
            "report is not eligible for visual approval".into(),
        ));
    }
    for evidence in [
        &report.source_original,
        &report.source_isolated,
        &report.isolation_decision,
        &report.graph_render,
        &report.transparent_overlay,
        &report.graph_over_source_png,
        &report.pixel_graph,
    ] {
        let path = config.repo_root.join(&evidence.path);
        if sha256_file(&path)? != evidence.sha256 {
            return Err(NewsroomAdmissionError::Invariant(format!(
                "visual evidence changed after generation: {}",
                evidence.path
            )));
        }
    }
    let graph_path = config.repo_root.join(&report.pixel_graph.path);
    if config.expected_graph_sha256 != report.pixel_graph.sha256 {
        return Err(NewsroomAdmissionError::Invariant(
            "reviewer-confirmed graph hash does not match the visual evidence".into(),
        ));
    }
    let graph = read_pixel_graph(&graph_path)?;
    if graph.source_record_id != report.source_id || graph.source_sha256 != report.source_sha256 {
        return Err(NewsroomAdmissionError::Invariant(
            "graph provenance no longer matches the reviewed source".into(),
        ));
    }
    let isolated_path = config.repo_root.join(&report.source_isolated.path);
    let isolated = load_rgba(&isolated_path)?;
    let projected = project_pixel_graph(&graph)?;
    let metrics = verify_pose_graph(&isolated, &projected, report.verification)
        .map_err(|error| NewsroomAdmissionError::Invariant(error.to_string()))?;
    if !metrics.passes(report.minimum_fidelity) || metrics != report.metrics {
        return Err(NewsroomAdmissionError::Invariant(
            "review-time projection no longer matches the recorded metrics".into(),
        ));
    }

    report.visual_review = VisualReview {
        status: VisualReviewStatus::Approved,
        reviewer: config.reviewer.clone(),
        finding: config.finding.clone(),
    };
    write_json(&report_path, &report)?;

    let entry = ledger
        .entries
        .iter_mut()
        .find(|entry| entry.source_id == config.source_id)
        .expect("source presence was checked above");
    entry.status = NewsroomAdmissionStatus::VisuallyVerified;
    entry.graph_path = Some(report.pixel_graph.path.clone());
    entry.graph_sha256 = Some(report.pixel_graph.sha256.clone());
    update_ledger_counts(&mut ledger);
    write_json(&ledger_path, &ledger)?;
    Ok(report)
}

fn validate_minimum(minimum: f64) -> Result<(), NewsroomAdmissionError> {
    if (MINIMUM_FIDELITY..=1.0).contains(&minimum) {
        Ok(())
    } else {
        Err(NewsroomAdmissionError::Invariant(format!(
            "minimum fidelity {minimum} is outside the enforced 0.95 to 1.0 range"
        )))
    }
}

fn build_isolation_decision(
    source: &RgbaImage,
    isolated: &RgbaImage,
) -> Result<RgbaImage, NewsroomAdmissionError> {
    if source.dimensions() != isolated.dimensions() {
        return Err(NewsroomAdmissionError::Invariant(
            "isolation decision images have different dimensions".into(),
        ));
    }
    let mut audit = RgbaImage::new(source.width(), source.height());
    for ((output, original), retained) in audit
        .pixels_mut()
        .zip(source.pixels())
        .zip(isolated.pixels())
    {
        *output = if retained[3] > 0 {
            *original
        } else {
            image::Rgba([255, 0, 255, 112])
        };
    }
    Ok(audit)
}

fn validate_manifest(manifest: &NewsroomSourceManifest) -> Result<(), NewsroomAdmissionError> {
    if manifest.schema_version != 2
        || manifest.status != "source_evidence_only"
        || manifest.runtime_raster_allowed
        || !manifest.visual_overlay_required
        || manifest.minimum_visual_alignment < MINIMUM_FIDELITY
        || manifest.style_authority.is_empty()
    {
        return Err(NewsroomAdmissionError::Invariant(
            "newsroom v2 manifest policy is not fail-closed".into(),
        ));
    }
    let admissible = manifest
        .sources
        .iter()
        .filter(|record| record.is_admissible())
        .count();
    if admissible == 0 {
        return Err(NewsroomAdmissionError::Invariant(
            "manifest has no admissible source plates".into(),
        ));
    }
    let mut ids = std::collections::BTreeSet::new();
    for source in &manifest.sources {
        if !ids.insert(source.id.as_str())
            || source.id.is_empty()
            || source.file.is_empty()
            || source.sha256.len() != 64
        {
            return Err(NewsroomAdmissionError::Invariant(
                "manifest source identities and hashes must be unique and complete".into(),
            ));
        }
        if source.is_admissible() && source.targets.is_empty() {
            return Err(NewsroomAdmissionError::Invariant(format!(
                "{} has no extraction targets",
                source.id
            )));
        }
        if source.kind == "composition_reference_only"
            && source.character_pixels_canonical != Some(false)
        {
            return Err(NewsroomAdmissionError::Invariant(format!(
                "{} must explicitly reject canonical character pixels",
                source.id
            )));
        }
    }
    Ok(())
}

fn initialize_ledger(
    manifest: &NewsroomSourceManifest,
    manifest_hash: &str,
    minimum_fidelity: f64,
) -> NewsroomAdmissionLedger {
    let entries = manifest
        .sources
        .iter()
        .filter(|source| source.is_admissible())
        .enumerate()
        .map(|(sequence, source)| NewsroomAdmissionEntry {
            sequence: sequence + 1,
            source_id: source.id.clone(),
            source_sha256: source.sha256.clone(),
            source_kind: source.kind.clone(),
            status: NewsroomAdmissionStatus::Queued,
            graph_path: None,
            graph_sha256: None,
            verification_report_path: None,
            silhouette_iou: None,
            foreground_color_fidelity: None,
        })
        .collect::<Vec<_>>();
    NewsroomAdmissionLedger {
        schema_version: NEWSROOM_ADMISSION_SCHEMA_VERSION,
        ledger_id: "wizard_joe_newsroom_v2_admission".into(),
        source_manifest_path: "evidence/newsroom-visual-development-v2/scene-manifest.json".into(),
        source_manifest_sha256: manifest_hash.into(),
        required_fidelity: minimum_fidelity,
        expected_source_count: entries.len(),
        verified_source_count: 0,
        awaiting_visual_comparison_count: 0,
        failed_source_count: 0,
        queued_source_count: entries.len(),
        entries,
    }
}

fn validate_ledger(
    ledger: &NewsroomAdmissionLedger,
    manifest: &NewsroomSourceManifest,
    manifest_hash: &str,
) -> Result<(), NewsroomAdmissionError> {
    if ledger.schema_version != NEWSROOM_ADMISSION_SCHEMA_VERSION
        || ledger.source_manifest_sha256 != manifest_hash
        || ledger.required_fidelity < MINIMUM_FIDELITY
    {
        return Err(NewsroomAdmissionError::Invariant(
            "newsroom admission ledger does not match its source manifest".into(),
        ));
    }
    let expected = manifest
        .sources
        .iter()
        .filter(|record| record.is_admissible())
        .collect::<Vec<_>>();
    if ledger.entries.len() != expected.len() || ledger.expected_source_count != expected.len() {
        return Err(NewsroomAdmissionError::Invariant(
            "newsroom admission ledger source count drifted".into(),
        ));
    }
    for (index, (entry, source)) in ledger.entries.iter().zip(expected).enumerate() {
        if entry.sequence != index + 1
            || entry.source_id != source.id
            || entry.source_sha256 != source.sha256
            || entry.source_kind != source.kind
        {
            return Err(NewsroomAdmissionError::Invariant(
                "newsroom admission ledger ordering or provenance drifted".into(),
            ));
        }
    }
    Ok(())
}

fn update_ledger_counts(ledger: &mut NewsroomAdmissionLedger) {
    ledger.verified_source_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == NewsroomAdmissionStatus::VisuallyVerified)
        .count();
    ledger.awaiting_visual_comparison_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == NewsroomAdmissionStatus::AwaitingVisualComparison)
        .count();
    ledger.failed_source_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == NewsroomAdmissionStatus::FailedVerification)
        .count();
    ledger.queued_source_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == NewsroomAdmissionStatus::Queued)
        .count();
}

fn manifest_path(repo_root: &Path) -> PathBuf {
    repo_root.join("evidence/newsroom-visual-development-v2/scene-manifest.json")
}

fn ledger_path(repo_root: &Path) -> PathBuf {
    repo_root.join("docs/newsroom-visual-development-v2/admission-ledger.json")
}

fn evidence_dir(repo_root: &Path, source_id: &str) -> PathBuf {
    repo_root
        .join("evidence/newsroom-visual-development-v2/pixelgraph-admission")
        .join(source_id)
}

fn read_bytes(path: &Path) -> Result<Vec<u8>, NewsroomAdmissionError> {
    fs::read(path).map_err(|source| NewsroomAdmissionError::Io {
        path: path.to_path_buf(),
        source,
    })
}

fn load_rgba(path: &Path) -> Result<RgbaImage, NewsroomAdmissionError> {
    let bytes = read_bytes(path)?;
    image::load_from_memory(&bytes)
        .map(|image| image.to_rgba8())
        .map_err(|source| NewsroomAdmissionError::Image {
            path: path.to_path_buf(),
            source,
        })
}

fn save_png_evidence(
    image: &RgbaImage,
    path: &Path,
) -> Result<EvidenceFile, NewsroomAdmissionError> {
    image
        .save_with_format(path, image::ImageFormat::Png)
        .map_err(|source| NewsroomAdmissionError::Image {
            path: path.to_path_buf(),
            source,
        })?;
    Ok(EvidenceFile {
        path: repo_relative(
            path.ancestors()
                .find(|ancestor| ancestor.join("rust").exists())
                .ok_or_else(|| {
                    NewsroomAdmissionError::Invariant(
                        "could not locate repository root for evidence path".into(),
                    )
                })?,
            path,
        )?,
        sha256: sha256_file(path)?,
    })
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, NewsroomAdmissionError> {
    let file = File::open(path).map_err(|source| NewsroomAdmissionError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    serde_json::from_reader(BufReader::new(file)).map_err(|source| NewsroomAdmissionError::Json {
        path: path.to_path_buf(),
        source,
    })
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), NewsroomAdmissionError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|source| NewsroomAdmissionError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    let bytes =
        serde_json::to_vec_pretty(value).map_err(|source| NewsroomAdmissionError::Json {
            path: path.to_path_buf(),
            source,
        })?;
    fs::write(path, bytes).map_err(|source| NewsroomAdmissionError::Io {
        path: path.to_path_buf(),
        source,
    })
}

fn sha256_file(path: &Path) -> Result<String, NewsroomAdmissionError> {
    let file = File::open(path).map_err(|source| NewsroomAdmissionError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let mut reader = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = reader
            .read(&mut buffer)
            .map_err(|source| NewsroomAdmissionError::Io {
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

fn repo_relative(repo_root: &Path, path: &Path) -> Result<String, NewsroomAdmissionError> {
    path.strip_prefix(repo_root)
        .map(|relative| relative.to_string_lossy().into_owned())
        .map_err(|_| {
            NewsroomAdmissionError::Invariant(format!(
                "{} is outside repository root {}",
                path.display(),
                repo_root.display()
            ))
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn manifest() -> NewsroomSourceManifest {
        NewsroomSourceManifest {
            schema_version: 2,
            status: "source_evidence_only".into(),
            style_authority: vec!["pose.png".into()],
            runtime_raster_allowed: false,
            visual_overlay_required: true,
            minimum_visual_alignment: 0.95,
            sources: vec![
                NewsroomSourceRecord {
                    id: "main_anchor_desk_v2".into(),
                    file: "source.png".into(),
                    sha256: "a".repeat(64),
                    kind: "character_free_set_plate".into(),
                    targets: vec!["desk".into()],
                    character_pixels_canonical: None,
                },
                NewsroomSourceRecord {
                    id: "camera_board".into(),
                    file: "board.png".into(),
                    sha256: "b".repeat(64),
                    kind: "composition_reference_only".into(),
                    targets: Vec::new(),
                    character_pixels_canonical: Some(false),
                },
            ],
        }
    }

    #[test]
    fn composition_boards_never_enter_the_admission_ledger() {
        let manifest = manifest();
        validate_manifest(&manifest).unwrap();
        let ledger = initialize_ledger(&manifest, &"c".repeat(64), 0.95);
        assert_eq!(ledger.expected_source_count, 1);
        assert_eq!(ledger.entries[0].source_id, "main_anchor_desk_v2");
    }

    #[test]
    fn manifest_rejects_runtime_rasters_and_missing_overlay_gate() {
        let mut bad = manifest();
        bad.runtime_raster_allowed = true;
        assert!(validate_manifest(&bad).is_err());
        let mut bad = manifest();
        bad.visual_overlay_required = false;
        assert!(validate_manifest(&bad).is_err());
    }

    #[test]
    fn ledger_order_is_manifest_order_and_hash_pinned() {
        let manifest = manifest();
        let ledger = initialize_ledger(&manifest, &"c".repeat(64), 0.95);
        validate_ledger(&ledger, &manifest, &"c".repeat(64)).unwrap();
        assert!(validate_ledger(&ledger, &manifest, &"d".repeat(64)).is_err());
    }
}
