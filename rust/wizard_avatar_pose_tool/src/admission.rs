use crate::isolation::{isolate_transparent, ForegroundBounds, IsolationConfig};
use crate::overlay::{
    build_transparent_overlay, composite_graph_over_source, OverlayCounts, OverlayPalette,
};
use crate::pixel_graph::{
    build_exact_pixel_graph, normalize_to_frame, project_pixel_graph, read_pixel_graph,
    write_pixel_graph, FrameSpec, PixelGraphError,
};
use crate::source_ledger::{SourceLedger, SourceRecord, SourceRecordKind};
use crate::verification::{verify_pose_graph, PoseGraphMetrics, VerificationConfig};
use image::{ImageFormat, RgbaImage};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};
use zip::ZipArchive;

pub const ADMISSION_SCHEMA_VERSION: u32 = 1;
pub const MINIMUM_FIDELITY: f64 = 0.95;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AdmissionStatus {
    Queued,
    AwaitingVisualComparison,
    VisuallyVerified,
    ExcludedNonPose,
    FailedVerification,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum VisualReviewStatus {
    Pending,
    Approved,
    Rejected,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct VisualReview {
    pub status: VisualReviewStatus,
    pub reviewer: String,
    pub finding: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AdmissionEntry {
    pub sequence: usize,
    pub source_record_id: String,
    pub source_sha256: String,
    pub status: AdmissionStatus,
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
    #[serde(skip_serializing_if = "Option::is_none")]
    pub exclusion_reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub exclusion_evidence_path: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AdmissionLedger {
    pub schema_version: u32,
    pub ledger_id: String,
    pub source_ledger_path: String,
    pub source_ledger_sha256: String,
    pub frame: FrameSpec,
    pub required_silhouette_iou: f64,
    pub required_foreground_color_fidelity: f64,
    pub expected_pose_count: usize,
    pub verified_pose_count: usize,
    #[serde(default)]
    pub excluded_non_pose_count: usize,
    pub awaiting_visual_comparison_count: usize,
    pub failed_pose_count: usize,
    pub queued_pose_count: usize,
    pub entries: Vec<AdmissionEntry>,
}

#[derive(Clone, Debug)]
pub struct AdmitOneConfig {
    pub repo_root: PathBuf,
    pub downloads_dir: PathBuf,
    pub candidate_id: String,
    pub isolation: IsolationConfig,
    pub verification: VerificationConfig,
    pub minimum_fidelity: f64,
}

#[derive(Clone, Debug)]
pub struct VisualReviewConfig {
    pub repo_root: PathBuf,
    pub candidate_id: String,
    pub expected_graph_sha256: String,
    pub reviewer: String,
    pub finding: String,
}

#[derive(Clone, Debug)]
pub struct NonPoseExclusionConfig {
    pub repo_root: PathBuf,
    pub candidate_id: String,
    pub expected_source_sha256: String,
    pub reviewer: String,
    pub finding: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EvidenceFile {
    pub path: String,
    pub sha256: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PoseVerificationReport {
    pub schema_version: u32,
    pub source_record_id: String,
    pub source_archive: String,
    pub source_entry: String,
    pub source_sha256: String,
    pub source_width: u32,
    pub source_height: u32,
    pub isolated_bounds: Option<ForegroundBounds>,
    pub frame: FrameSpec,
    pub offset_x: u32,
    pub offset_y: u32,
    pub isolation: IsolationConfig,
    pub verification: VerificationConfig,
    pub minimum_fidelity: f64,
    pub metrics: PoseGraphMetrics,
    pub overlay_counts: OverlayCounts,
    pub source_isolated: EvidenceFile,
    pub graph_render: EvidenceFile,
    pub transparent_overlay: EvidenceFile,
    pub graph_over_source_png: EvidenceFile,
    pub pixel_graph: EvidenceFile,
    pub graph_round_trip_exact: bool,
    pub passed: bool,
    pub visual_review: VisualReview,
    pub policy: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NonPoseExclusionReport {
    pub schema_version: u32,
    pub source_record_id: String,
    pub source_archive: String,
    pub source_entry: String,
    pub source_sha256: String,
    pub source_width: u32,
    pub source_height: u32,
    pub reviewer: String,
    pub finding: String,
    pub visual_evidence: EvidenceFile,
    pub policy: String,
}

#[derive(Debug, thiserror::Error)]
pub enum PoseAdmissionError {
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
    #[error("ZIP error at {path}: {source}")]
    Zip {
        path: PathBuf,
        #[source]
        source: zip::result::ZipError,
    },
    #[error("JSON error at {path}: {source}")]
    Json {
        path: PathBuf,
        #[source]
        source: serde_json::Error,
    },
    #[error(transparent)]
    PixelGraph(#[from] PixelGraphError),
    #[error("admission invariant failed: {0}")]
    Invariant(String),
}

fn ensure_local_admission_owner(repo_root: &Path) -> Result<(), PoseAdmissionError> {
    const OWNER: &str = "isolated-primary-019f6d";
    let owner_path = repo_root.join(format!(".pose-admission-owner-{OWNER}"));
    if !owner_path.exists() {
        return Ok(());
    }
    let actual = std::env::var("WIZARD_POSE_ADMISSION_OWNER").unwrap_or_default();
    if OWNER != actual {
        return Err(PoseAdmissionError::Invariant(
            "pose admission is temporarily owned by another serial reviewer".to_string(),
        ));
    }
    Ok(())
}

pub fn admit_one_pose(
    config: &AdmitOneConfig,
) -> Result<PoseVerificationReport, PoseAdmissionError> {
    ensure_local_admission_owner(&config.repo_root)?;
    if !(MINIMUM_FIDELITY..=1.0).contains(&config.minimum_fidelity) {
        return Err(PoseAdmissionError::Invariant(format!(
            "minimum fidelity {} is below the enforced 0.95 gate or above 1.0",
            config.minimum_fidelity
        )));
    }
    let source_ledger_path = config
        .repo_root
        .join("docs/pose-admission/wizard-joe-source-ledger.json");
    let source_ledger: SourceLedger = read_json(&source_ledger_path)?;
    let source_ledger_sha256 = sha256_file(&source_ledger_path)?;
    let frame = frame_from_source_ledger(&source_ledger)?;
    let admission_ledger_path = config
        .repo_root
        .join("docs/pose-admission/wizard-joe-admission-ledger.json");
    let mut admission_ledger = if admission_ledger_path.exists() {
        let ledger: AdmissionLedger = read_json(&admission_ledger_path)?;
        validate_admission_ledger(&ledger, &source_ledger, &source_ledger_sha256, frame)?;
        ledger
    } else {
        initialize_admission_ledger(
            &source_ledger,
            &source_ledger_sha256,
            frame,
            config.minimum_fidelity,
        )
    };

    let expected = admission_ledger
        .entries
        .iter()
        .find(|entry| !is_terminal(entry.status))
        .map(|entry| entry.source_record_id.as_str())
        .ok_or_else(|| {
            PoseAdmissionError::Invariant("all pose candidates are admitted".to_string())
        })?;
    if expected != config.candidate_id {
        return Err(PoseAdmissionError::Invariant(format!(
            "serial admission requires {expected}; requested {}",
            config.candidate_id
        )));
    }
    let pending_entry = admission_ledger
        .entries
        .iter()
        .find(|entry| entry.source_record_id == config.candidate_id)
        .ok_or_else(|| PoseAdmissionError::Invariant("admission entry disappeared".to_string()))?;
    if pending_entry.status == AdmissionStatus::AwaitingVisualComparison {
        return Err(PoseAdmissionError::Invariant(format!(
            "{} is waiting for direct graph-over-PNG visual comparison",
            config.candidate_id
        )));
    }

    let source_record = source_ledger
        .records
        .iter()
        .find(|record| record.record_id == config.candidate_id)
        .ok_or_else(|| {
            PoseAdmissionError::Invariant(format!(
                "{} is absent from the source ledger",
                config.candidate_id
            ))
        })?;
    if source_record.kind != SourceRecordKind::PoseCandidate {
        return Err(PoseAdmissionError::Invariant(format!(
            "{} is not a pose candidate",
            config.candidate_id
        )));
    }

    let source = load_source_image(&config.downloads_dir, source_record)?;
    let isolated = isolate_transparent(&source, config.isolation);
    if isolated.foreground_pixels == 0 {
        return Err(PoseAdmissionError::Invariant(format!(
            "{} became empty after background isolation",
            config.candidate_id
        )));
    }
    let normalized = normalize_to_frame(&isolated.image, frame)?;
    let normalized_source_png = normalize_to_frame(&source, frame)?;
    let graph = build_exact_pixel_graph(
        format!("{}-pixelgraph-v1", config.candidate_id.to_ascii_lowercase()),
        &config.candidate_id,
        &source_record.sha256,
        source.dimensions(),
        &normalized,
    );

    let evidence_dir = config
        .repo_root
        .join("evidence/pose-admission")
        .join(&config.candidate_id);
    fs::create_dir_all(&evidence_dir).map_err(|source| PoseAdmissionError::Io {
        path: evidence_dir.clone(),
        source,
    })?;
    let evidence_graph_path = evidence_dir.join("pixelgraph.json.gz");
    let graph_sha256 = write_pixel_graph(&graph, &evidence_graph_path)?;
    let round_trip_graph = read_pixel_graph(&evidence_graph_path)?;
    let graph_round_trip_exact = round_trip_graph == graph;
    if !graph_round_trip_exact {
        return Err(PoseAdmissionError::Invariant(
            "serialized graph did not round-trip exactly".to_string(),
        ));
    }
    let graph_render = project_pixel_graph(&round_trip_graph)?;
    let metrics = verify_pose_graph(&normalized.image, &graph_render, config.verification)
        .map_err(|error| PoseAdmissionError::Invariant(error.to_string()))?;
    let overlay = build_transparent_overlay(
        &normalized.image,
        &graph_render,
        config.verification,
        OverlayPalette::default(),
    )
    .map_err(|error| PoseAdmissionError::Invariant(error.to_string()))?;
    let graph_over_source =
        composite_graph_over_source(&normalized_source_png.image, &graph_render, 128)
            .map_err(|error| PoseAdmissionError::Invariant(error.to_string()))?;

    let source_isolated_path = evidence_dir.join("source-isolated-normalized.png");
    let graph_render_path = evidence_dir.join("graph-render.png");
    let overlay_path = evidence_dir.join("transparent-overlay.png");
    let graph_over_source_path = evidence_dir.join("graph-over-source-png.png");
    save_png(&normalized.image, &source_isolated_path)?;
    save_png(&graph_render, &graph_render_path)?;
    save_png(&overlay.image, &overlay_path)?;
    save_png(&graph_over_source, &graph_over_source_path)?;

    let passed = graph_round_trip_exact && metrics.passes(config.minimum_fidelity);
    let report_path = evidence_dir.join("verification.json");
    let report = PoseVerificationReport {
        schema_version: ADMISSION_SCHEMA_VERSION,
        source_record_id: config.candidate_id.clone(),
        source_archive: source_record.archive_filename.clone(),
        source_entry: source_record.archive_entry.clone(),
        source_sha256: source_record.sha256.clone(),
        source_width: source.width(),
        source_height: source.height(),
        isolated_bounds: isolated.bounds,
        frame,
        offset_x: normalized.offset_x,
        offset_y: normalized.offset_y,
        isolation: config.isolation,
        verification: config.verification,
        minimum_fidelity: config.minimum_fidelity,
        metrics,
        overlay_counts: overlay.counts,
        source_isolated: evidence_file(&config.repo_root, &source_isolated_path)?,
        graph_render: evidence_file(&config.repo_root, &graph_render_path)?,
        transparent_overlay: evidence_file(&config.repo_root, &overlay_path)?,
        graph_over_source_png: evidence_file(&config.repo_root, &graph_over_source_path)?,
        pixel_graph: evidence_file(&config.repo_root, &evidence_graph_path)?,
        graph_round_trip_exact,
        passed,
        visual_review: VisualReview {
            status: VisualReviewStatus::Pending,
            reviewer: "pending".to_string(),
            finding: "Direct transparent pixel-graph-over-PNG comparison has not yet been visually approved.".to_string(),
        },
        policy: "One source record maps to one lossless colored-pixel run graph. The source is background-isolated, centered by transparent edge padding only, projected from serialized graph data, and admitted only when both foreground silhouette IoU and foreground-only color fidelity are at least 95%. No PNG or SVG path is stored in the runtime graph.".to_string(),
    };
    write_json(&report_path, &report)?;

    let entry = admission_ledger
        .entries
        .iter_mut()
        .find(|entry| entry.source_record_id == config.candidate_id)
        .ok_or_else(|| PoseAdmissionError::Invariant("admission entry disappeared".to_string()))?;
    entry.status = if passed {
        AdmissionStatus::AwaitingVisualComparison
    } else {
        AdmissionStatus::FailedVerification
    };
    entry.graph_path = None;
    entry.graph_sha256 = passed.then_some(graph_sha256);
    entry.verification_report_path = Some(relative_path(&config.repo_root, &report_path));
    entry.silhouette_iou = Some(metrics.silhouette_iou);
    entry.foreground_color_fidelity = Some(metrics.foreground_color_fidelity);
    refresh_counts(&mut admission_ledger);
    write_json(&admission_ledger_path, &admission_ledger)?;

    Ok(report)
}

pub fn approve_visual_comparison(
    config: &VisualReviewConfig,
) -> Result<PoseVerificationReport, PoseAdmissionError> {
    ensure_local_admission_owner(&config.repo_root)?;
    if config.reviewer.trim().is_empty() || config.finding.trim().is_empty() {
        return Err(PoseAdmissionError::Invariant(
            "visual approval requires a reviewer and a concrete finding".to_string(),
        ));
    }
    let ledger_path = config
        .repo_root
        .join("docs/pose-admission/wizard-joe-admission-ledger.json");
    let mut ledger: AdmissionLedger = read_json(&ledger_path)?;
    let expected = ledger
        .entries
        .iter()
        .find(|entry| !is_terminal(entry.status))
        .ok_or_else(|| {
            PoseAdmissionError::Invariant("all pose candidates are admitted".to_string())
        })?;
    if expected.source_record_id != config.candidate_id
        || expected.status != AdmissionStatus::AwaitingVisualComparison
    {
        return Err(PoseAdmissionError::Invariant(format!(
            "{} is not the next graph awaiting visual comparison",
            config.candidate_id
        )));
    }

    let report_path = config
        .repo_root
        .join("evidence/pose-admission")
        .join(&config.candidate_id)
        .join("verification.json");
    let mut report: PoseVerificationReport = read_json(&report_path)?;
    if !report.passed
        || report.visual_review.status != VisualReviewStatus::Pending
        || report.source_record_id != config.candidate_id
        || report.pixel_graph.sha256 != config.expected_graph_sha256
        || expected.graph_sha256.as_deref() != Some(config.expected_graph_sha256.as_str())
    {
        return Err(PoseAdmissionError::Invariant(
            "automated evidence is not eligible for visual approval or its graph hash changed"
                .to_string(),
        ));
    }
    for evidence in [
        &report.source_isolated,
        &report.graph_render,
        &report.transparent_overlay,
        &report.graph_over_source_png,
        &report.pixel_graph,
    ] {
        let path = config.repo_root.join(&evidence.path);
        if sha256_file(&path)? != evidence.sha256 {
            return Err(PoseAdmissionError::Invariant(format!(
                "visual evidence changed after generation: {}",
                evidence.path
            )));
        }
    }

    let evidence_graph_path = config.repo_root.join(&report.pixel_graph.path);
    let runtime_graph_path = config
        .repo_root
        .join("rust/wizard_avatar_engine/assets/pose_graphs/v5")
        .join(format!("{}.pixelgraph.json.gz", config.candidate_id));
    if let Some(parent) = runtime_graph_path.parent() {
        fs::create_dir_all(parent).map_err(|source| PoseAdmissionError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    fs::copy(&evidence_graph_path, &runtime_graph_path).map_err(|source| {
        PoseAdmissionError::Io {
            path: runtime_graph_path.clone(),
            source,
        }
    })?;
    let runtime_hash = sha256_file(&runtime_graph_path)?;
    if runtime_hash != report.pixel_graph.sha256 {
        return Err(PoseAdmissionError::Invariant(
            "promoted graph differs from visually reviewed graph".to_string(),
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
        .find(|entry| entry.source_record_id == config.candidate_id)
        .ok_or_else(|| PoseAdmissionError::Invariant("admission entry disappeared".to_string()))?;
    entry.status = AdmissionStatus::VisuallyVerified;
    entry.graph_path = Some(relative_path(&config.repo_root, &runtime_graph_path));
    entry.graph_sha256 = Some(runtime_hash);
    refresh_counts(&mut ledger);
    write_json(&ledger_path, &ledger)?;
    Ok(report)
}

pub fn reject_visual_comparison(
    config: &VisualReviewConfig,
) -> Result<PoseVerificationReport, PoseAdmissionError> {
    ensure_local_admission_owner(&config.repo_root)?;
    if config.reviewer.trim().is_empty() || config.finding.trim().is_empty() {
        return Err(PoseAdmissionError::Invariant(
            "visual rejection requires a reviewer and a concrete finding".to_string(),
        ));
    }
    let ledger_path = config
        .repo_root
        .join("docs/pose-admission/wizard-joe-admission-ledger.json");
    let mut ledger: AdmissionLedger = read_json(&ledger_path)?;
    let expected = ledger
        .entries
        .iter()
        .find(|entry| !is_terminal(entry.status))
        .ok_or_else(|| {
            PoseAdmissionError::Invariant("all pose candidates are admitted".to_string())
        })?;
    if expected.source_record_id != config.candidate_id
        || expected.status != AdmissionStatus::AwaitingVisualComparison
    {
        return Err(PoseAdmissionError::Invariant(format!(
            "{} is not the next graph awaiting visual comparison",
            config.candidate_id
        )));
    }

    let report_path = config
        .repo_root
        .join("evidence/pose-admission")
        .join(&config.candidate_id)
        .join("verification.json");
    let mut report: PoseVerificationReport = read_json(&report_path)?;
    if !report.passed
        || report.visual_review.status != VisualReviewStatus::Pending
        || report.source_record_id != config.candidate_id
        || report.pixel_graph.sha256 != config.expected_graph_sha256
        || expected.graph_sha256.as_deref() != Some(config.expected_graph_sha256.as_str())
    {
        return Err(PoseAdmissionError::Invariant(
            "automated evidence is not eligible for visual rejection or its graph hash changed"
                .to_string(),
        ));
    }
    for evidence in [
        &report.source_isolated,
        &report.graph_render,
        &report.transparent_overlay,
        &report.graph_over_source_png,
        &report.pixel_graph,
    ] {
        let path = config.repo_root.join(&evidence.path);
        if sha256_file(&path)? != evidence.sha256 {
            return Err(PoseAdmissionError::Invariant(format!(
                "visual evidence changed after generation: {}",
                evidence.path
            )));
        }
    }

    report.visual_review = VisualReview {
        status: VisualReviewStatus::Rejected,
        reviewer: config.reviewer.clone(),
        finding: config.finding.clone(),
    };
    write_json(&report_path, &report)?;
    let entry = ledger
        .entries
        .iter_mut()
        .find(|entry| entry.source_record_id == config.candidate_id)
        .ok_or_else(|| PoseAdmissionError::Invariant("admission entry disappeared".to_string()))?;
    entry.status = AdmissionStatus::FailedVerification;
    entry.graph_path = None;
    refresh_counts(&mut ledger);
    write_json(&ledger_path, &ledger)?;
    Ok(report)
}

/// Revokes the most recent visual approval when direct frame review finds a defect afterward.
///
/// The exact graph hash is mandatory so a correction can never reopen a different revision.
pub fn reopen_visual_approval(
    config: &VisualReviewConfig,
) -> Result<PoseVerificationReport, PoseAdmissionError> {
    ensure_local_admission_owner(&config.repo_root)?;
    if config.reviewer.trim().is_empty() || config.finding.trim().is_empty() {
        return Err(PoseAdmissionError::Invariant(
            "reopening visual approval requires a reviewer and a concrete finding".to_string(),
        ));
    }
    let ledger_path = config
        .repo_root
        .join("docs/pose-admission/wizard-joe-admission-ledger.json");
    let mut ledger: AdmissionLedger = read_json(&ledger_path)?;
    let entry_index = ledger
        .entries
        .iter()
        .position(|entry| entry.source_record_id == config.candidate_id)
        .ok_or_else(|| PoseAdmissionError::Invariant("admission entry disappeared".to_string()))?;
    let entry = &ledger.entries[entry_index];
    if entry.status != AdmissionStatus::VisuallyVerified
        || entry.graph_sha256.as_deref() != Some(config.expected_graph_sha256.as_str())
        || ledger.entries[entry_index + 1..]
            .iter()
            .any(|later| later.status == AdmissionStatus::VisuallyVerified)
    {
        return Err(PoseAdmissionError::Invariant(format!(
            "{} is not the latest exact visually verified graph",
            config.candidate_id
        )));
    }

    let report_path = config
        .repo_root
        .join("evidence/pose-admission")
        .join(&config.candidate_id)
        .join("verification.json");
    let mut report: PoseVerificationReport = read_json(&report_path)?;
    if !report.passed
        || report.visual_review.status != VisualReviewStatus::Approved
        || report.source_record_id != config.candidate_id
        || report.pixel_graph.sha256 != config.expected_graph_sha256
    {
        return Err(PoseAdmissionError::Invariant(
            "approved evidence is not eligible for exact-hash reopening".to_string(),
        ));
    }
    for evidence in [
        &report.source_isolated,
        &report.graph_render,
        &report.transparent_overlay,
        &report.graph_over_source_png,
        &report.pixel_graph,
    ] {
        let path = config.repo_root.join(&evidence.path);
        if sha256_file(&path)? != evidence.sha256 {
            return Err(PoseAdmissionError::Invariant(format!(
                "visual evidence changed after approval: {}",
                evidence.path
            )));
        }
    }

    let runtime_graph_path = entry
        .graph_path
        .as_ref()
        .map(|path| config.repo_root.join(path))
        .ok_or_else(|| {
            PoseAdmissionError::Invariant("approved graph has no runtime path".to_string())
        })?;
    if sha256_file(&runtime_graph_path)? != config.expected_graph_sha256 {
        return Err(PoseAdmissionError::Invariant(
            "runtime graph changed after visual approval".to_string(),
        ));
    }
    fs::remove_file(&runtime_graph_path).map_err(|source| PoseAdmissionError::Io {
        path: runtime_graph_path,
        source,
    })?;

    report.visual_review = VisualReview {
        status: VisualReviewStatus::Rejected,
        reviewer: config.reviewer.clone(),
        finding: config.finding.clone(),
    };
    write_json(&report_path, &report)?;
    let entry = &mut ledger.entries[entry_index];
    entry.status = AdmissionStatus::FailedVerification;
    entry.graph_path = None;
    refresh_counts(&mut ledger);
    write_json(&ledger_path, &ledger)?;
    Ok(report)
}

pub fn exclude_non_pose_source(
    config: &NonPoseExclusionConfig,
) -> Result<NonPoseExclusionReport, PoseAdmissionError> {
    ensure_local_admission_owner(&config.repo_root)?;
    if config.reviewer.trim().is_empty() || config.finding.trim().is_empty() {
        return Err(PoseAdmissionError::Invariant(
            "non-pose exclusion requires a reviewer and a concrete finding".to_string(),
        ));
    }

    let ledger_path = config
        .repo_root
        .join("docs/pose-admission/wizard-joe-admission-ledger.json");
    let mut ledger: AdmissionLedger = read_json(&ledger_path)?;
    let expected = ledger
        .entries
        .iter()
        .find(|entry| !is_terminal(entry.status))
        .ok_or_else(|| {
            PoseAdmissionError::Invariant("all source records are disposed".to_string())
        })?;
    if expected.source_record_id != config.candidate_id
        || expected.source_sha256 != config.expected_source_sha256
    {
        return Err(PoseAdmissionError::Invariant(format!(
            "{} is not the next exact source record awaiting disposition",
            config.candidate_id
        )));
    }

    let verification_path = config
        .repo_root
        .join("evidence/pose-admission")
        .join(&config.candidate_id)
        .join("verification.json");
    let verification: PoseVerificationReport = read_json(&verification_path)?;
    if verification.source_record_id != config.candidate_id
        || verification.source_sha256 != config.expected_source_sha256
    {
        return Err(PoseAdmissionError::Invariant(
            "non-pose visual evidence does not match the exact source record".to_string(),
        ));
    }
    let visual_evidence_path = config.repo_root.join(&verification.source_isolated.path);
    if sha256_file(&visual_evidence_path)? != verification.source_isolated.sha256 {
        return Err(PoseAdmissionError::Invariant(
            "non-pose visual evidence changed after generation".to_string(),
        ));
    }

    let report = NonPoseExclusionReport {
        schema_version: ADMISSION_SCHEMA_VERSION,
        source_record_id: verification.source_record_id.clone(),
        source_archive: verification.source_archive.clone(),
        source_entry: verification.source_entry.clone(),
        source_sha256: verification.source_sha256.clone(),
        source_width: verification.source_width,
        source_height: verification.source_height,
        reviewer: config.reviewer.clone(),
        finding: config.finding.clone(),
        visual_evidence: verification.source_isolated.clone(),
        policy: "A serial source may be excluded only after direct visual inspection proves it contains no Wizard Joe character pose. Excluded records remain auditable but are never copied into runtime pose assets.".to_string(),
    };
    let report_path = config
        .repo_root
        .join("evidence/pose-admission")
        .join(&config.candidate_id)
        .join("non-pose-exclusion.json");
    write_json(&report_path, &report)?;

    let entry = ledger
        .entries
        .iter_mut()
        .find(|entry| entry.source_record_id == config.candidate_id)
        .ok_or_else(|| PoseAdmissionError::Invariant("admission entry disappeared".to_string()))?;
    entry.status = AdmissionStatus::ExcludedNonPose;
    entry.graph_path = None;
    entry.graph_sha256 = None;
    entry.verification_report_path = None;
    entry.silhouette_iou = None;
    entry.foreground_color_fidelity = None;
    entry.exclusion_reason = Some(config.finding.clone());
    entry.exclusion_evidence_path = Some(relative_path(&config.repo_root, &report_path));
    refresh_counts(&mut ledger);
    write_json(&ledger_path, &ledger)?;
    Ok(report)
}

fn initialize_admission_ledger(
    source_ledger: &SourceLedger,
    source_ledger_sha256: &str,
    frame: FrameSpec,
    minimum_fidelity: f64,
) -> AdmissionLedger {
    let entries = source_ledger
        .records
        .iter()
        .filter(|record| record.kind == SourceRecordKind::PoseCandidate)
        .enumerate()
        .map(|(index, record)| AdmissionEntry {
            sequence: index + 1,
            source_record_id: record.record_id.clone(),
            source_sha256: record.sha256.clone(),
            status: AdmissionStatus::Queued,
            graph_path: None,
            graph_sha256: None,
            verification_report_path: None,
            silhouette_iou: None,
            foreground_color_fidelity: None,
            exclusion_reason: None,
            exclusion_evidence_path: None,
        })
        .collect::<Vec<_>>();
    AdmissionLedger {
        schema_version: ADMISSION_SCHEMA_VERSION,
        ledger_id: "wizard-joe-serial-pixelgraph-admission-v1".to_string(),
        source_ledger_path: "docs/pose-admission/wizard-joe-source-ledger.json".to_string(),
        source_ledger_sha256: source_ledger_sha256.to_string(),
        frame,
        required_silhouette_iou: minimum_fidelity,
        required_foreground_color_fidelity: minimum_fidelity,
        expected_pose_count: entries.len(),
        verified_pose_count: 0,
        excluded_non_pose_count: 0,
        awaiting_visual_comparison_count: 0,
        failed_pose_count: 0,
        queued_pose_count: entries.len(),
        entries,
    }
}

fn validate_admission_ledger(
    ledger: &AdmissionLedger,
    source: &SourceLedger,
    source_sha256: &str,
    frame: FrameSpec,
) -> Result<(), PoseAdmissionError> {
    let candidates = source
        .records
        .iter()
        .filter(|record| record.kind == SourceRecordKind::PoseCandidate)
        .collect::<Vec<_>>();
    if ledger.schema_version != ADMISSION_SCHEMA_VERSION
        || ledger.source_ledger_sha256 != source_sha256
        || ledger.frame != frame
        || ledger.entries.len() != candidates.len()
        || ledger.expected_pose_count != candidates.len()
        || ledger.required_silhouette_iou < MINIMUM_FIDELITY
        || ledger.required_foreground_color_fidelity < MINIMUM_FIDELITY
    {
        return Err(PoseAdmissionError::Invariant(
            "admission ledger does not match the complete source ledger".to_string(),
        ));
    }
    for (index, (entry, source_record)) in ledger.entries.iter().zip(candidates).enumerate() {
        if entry.sequence != index + 1
            || entry.source_record_id != source_record.record_id
            || entry.source_sha256 != source_record.sha256
        {
            return Err(PoseAdmissionError::Invariant(format!(
                "admission entry {} does not match its source record",
                index + 1
            )));
        }
    }
    Ok(())
}

fn refresh_counts(ledger: &mut AdmissionLedger) {
    ledger.verified_pose_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == AdmissionStatus::VisuallyVerified)
        .count();
    ledger.excluded_non_pose_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == AdmissionStatus::ExcludedNonPose)
        .count();
    ledger.awaiting_visual_comparison_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == AdmissionStatus::AwaitingVisualComparison)
        .count();
    ledger.failed_pose_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == AdmissionStatus::FailedVerification)
        .count();
    ledger.queued_pose_count = ledger
        .entries
        .iter()
        .filter(|entry| entry.status == AdmissionStatus::Queued)
        .count();
}

fn is_terminal(status: AdmissionStatus) -> bool {
    matches!(
        status,
        AdmissionStatus::VisuallyVerified | AdmissionStatus::ExcludedNonPose
    )
}

fn frame_from_source_ledger(ledger: &SourceLedger) -> Result<FrameSpec, PoseAdmissionError> {
    FrameSpec::from_source_dimensions(
        ledger
            .records
            .iter()
            .map(|record| (record.width, record.height)),
    )
    .ok_or_else(|| PoseAdmissionError::Invariant("source ledger is empty".to_string()))
}

fn load_source_image(
    downloads_dir: &Path,
    record: &SourceRecord,
) -> Result<RgbaImage, PoseAdmissionError> {
    let archive_path = downloads_dir.join(&record.archive_filename);
    let file = File::open(&archive_path).map_err(|source| PoseAdmissionError::Io {
        path: archive_path.clone(),
        source,
    })?;
    let mut archive = ZipArchive::new(file).map_err(|source| PoseAdmissionError::Zip {
        path: archive_path.clone(),
        source,
    })?;
    let mut entry =
        archive
            .by_name(&record.archive_entry)
            .map_err(|source| PoseAdmissionError::Zip {
                path: archive_path.clone(),
                source,
            })?;
    let mut bytes = Vec::with_capacity(entry.size() as usize);
    entry
        .read_to_end(&mut bytes)
        .map_err(|source| PoseAdmissionError::Io {
            path: archive_path.clone(),
            source,
        })?;
    let actual_sha256 = format!("{:x}", Sha256::digest(&bytes));
    if actual_sha256 != record.sha256 {
        return Err(PoseAdmissionError::Invariant(format!(
            "{} source hash changed: expected {}, got {actual_sha256}",
            record.record_id, record.sha256
        )));
    }
    let image = image::load_from_memory_with_format(&bytes, ImageFormat::Png)
        .map_err(|source| PoseAdmissionError::Image {
            path: archive_path,
            source,
        })?
        .to_rgba8();
    if image.dimensions() != (record.width, record.height) {
        return Err(PoseAdmissionError::Invariant(format!(
            "{} dimensions changed: expected {}x{}, got {}x{}",
            record.record_id,
            record.width,
            record.height,
            image.width(),
            image.height()
        )));
    }
    Ok(image)
}

fn save_png(image: &RgbaImage, path: &Path) -> Result<(), PoseAdmissionError> {
    image
        .save(path)
        .map_err(|source| PoseAdmissionError::Image {
            path: path.to_path_buf(),
            source,
        })
}

fn evidence_file(repo_root: &Path, path: &Path) -> Result<EvidenceFile, PoseAdmissionError> {
    Ok(EvidenceFile {
        path: relative_path(repo_root, path),
        sha256: sha256_file(path)?,
    })
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, PoseAdmissionError> {
    let file = File::open(path).map_err(|source| PoseAdmissionError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    serde_json::from_reader(BufReader::new(file)).map_err(|source| PoseAdmissionError::Json {
        path: path.to_path_buf(),
        source,
    })
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), PoseAdmissionError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|source| PoseAdmissionError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    let mut bytes =
        serde_json::to_vec_pretty(value).map_err(|source| PoseAdmissionError::Json {
            path: path.to_path_buf(),
            source,
        })?;
    bytes.push(b'\n');
    fs::write(path, bytes).map_err(|source| PoseAdmissionError::Io {
        path: path.to_path_buf(),
        source,
    })
}

fn sha256_file(path: &Path) -> Result<String, PoseAdmissionError> {
    let file = File::open(path).map_err(|source| PoseAdmissionError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let mut reader = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = reader
            .read(&mut buffer)
            .map_err(|source| PoseAdmissionError::Io {
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

fn relative_path(repo_root: &Path, path: &Path) -> String {
    path.strip_prefix(repo_root)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn admission_ledger_keeps_duplicate_sources_as_independent_entries() {
        let source = SourceLedger {
            schema_version: 1,
            ledger_id: "source".to_string(),
            policy: "no collapse".to_string(),
            archive_count: 1,
            record_count: 2,
            pose_candidate_count: 2,
            style_reference_count: 0,
            unique_content_count: 1,
            archives: Vec::new(),
            records: vec![source_record(1, "same"), source_record(2, "same")],
        };
        let ledger = initialize_admission_ledger(
            &source,
            "ledger-hash",
            FrameSpec {
                width: 10,
                height: 10,
            },
            0.95,
        );
        assert_eq!(ledger.entries.len(), 2);
        assert_ne!(
            ledger.entries[0].source_record_id,
            ledger.entries[1].source_record_id
        );
    }

    #[test]
    fn excluded_non_pose_sources_are_terminal_and_counted() {
        let source = SourceLedger {
            schema_version: 1,
            ledger_id: "source".to_string(),
            policy: "serial review".to_string(),
            archive_count: 1,
            record_count: 1,
            pose_candidate_count: 1,
            style_reference_count: 0,
            unique_content_count: 1,
            archives: Vec::new(),
            records: vec![source_record(1, "not-a-pose")],
        };
        let mut ledger = initialize_admission_ledger(
            &source,
            "ledger-hash",
            FrameSpec {
                width: 10,
                height: 10,
            },
            0.95,
        );
        ledger.entries[0].status = AdmissionStatus::ExcludedNonPose;
        refresh_counts(&mut ledger);
        assert!(is_terminal(ledger.entries[0].status));
        assert_eq!(ledger.excluded_non_pose_count, 1);
        assert_eq!(ledger.queued_pose_count, 0);
    }

    fn source_record(serial: usize, hash: &str) -> SourceRecord {
        SourceRecord {
            serial,
            record_id: format!("WJSRC-{serial:04}"),
            kind: SourceRecordKind::PoseCandidate,
            archive_order: 1,
            archive_filename: "poses.zip".to_string(),
            archive_entry_order: serial,
            archive_entry: format!("pose-{serial}.png"),
            sha256: hash.to_string(),
            byte_length: 1,
            width: 10,
            height: 10,
            exact_duplicate_of: None,
        }
    }
}
