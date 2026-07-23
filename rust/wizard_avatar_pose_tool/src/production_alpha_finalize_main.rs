use flate2::read::GzDecoder;
use image::{ImageFormat, Rgba, RgbaImage};
use serde::{de::DeserializeOwned, Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File, OpenOptions};
use std::io::{Cursor, Write};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use wizard_avatar_pose_tool::{
    build_transparent_overlay, composite_graph_over_source, project_pixel_graph, verify_pose_graph,
    OverlayPalette, PixelGraph, ProductionAlphaAdmissionLedger, ProductionAlphaEvidenceArtifact,
    ProductionAlphaRuntimeManifest, ProductionAlphaSourceLedger, ProductionAlphaSummary,
    ProductionAlphaVerification, VerificationConfig, PRODUCTION_ALPHA_COMPILER_ID,
    PRODUCTION_ALPHA_SCHEMA_VERSION,
};

const EXPECTED_POSE_COUNT: usize = 260;
const EXPECTED_BATCH_COUNT: usize = 8;
const FRAME_SIZE: u32 = 1254;
const REQUIRED_SAFE_MARGIN: u32 = 69;
const PENDING_STATUS: &str = "pending_transparent_overlay_review";
const APPROVED_STATUS: &str = "approved_transparent_overlay_review";
const TECHNICAL_STATUS: &str = "exact_rgba_verified";
const REVIEW_REPORT_SCHEMA_VERSION: u32 = 1;
const AGGREGATE_SCHEMA_VERSION: u32 = 2;
const REVIEW_PROTOCOL: &str =
    "literal source/projected/50-percent-transparent-overlay visual comparison";

fn main() {
    match parse_root().and_then(|root| finalize(&root)) {
        Ok(receipt) => println!(
            "{}",
            serde_json::to_string_pretty(&receipt).expect("receipt must serialize")
        ),
        Err(error) => {
            eprintln!("wizard-avatar-production-alpha-finalize: {error}");
            std::process::exit(1);
        }
    }
}

fn parse_root() -> Result<PathBuf, String> {
    let mut root = None;
    let mut arguments = std::env::args().skip(1);
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--project-root" => {
                root = Some(PathBuf::from(
                    arguments.next().ok_or("--project-root requires a path")?,
                ));
            }
            "--help" | "-h" => {
                println!("Usage: wizard-avatar-production-alpha-finalize --project-root PATH");
                std::process::exit(0);
            }
            unknown => return Err(format!("unknown argument {unknown}")),
        }
    }
    root.ok_or("--project-root is required".to_string())
}

fn finalize(root: &Path) -> Result<Value, String> {
    let root = fs::canonicalize(root)
        .map_err(|error| format!("cannot resolve project root {}: {error}", root.display()))?;
    let report_root = root.join("evidence/pose-admission-v2/visual-review-batches");
    let lock_path = report_root.join(".production-alpha-finalize.lock");
    let _lock = ExclusiveLock::acquire(&lock_path)?;

    let plan = build_finalization_plan(&root)?;
    stage_and_publish(&report_root, &plan.bindings, &plan.outputs, None)?;
    Ok(plan.receipt)
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct EntriesReviewReportV1 {
    #[serde(default)]
    schema_version: Option<u32>,
    batch_id: String,
    reviewer: String,
    range: EntriesRangeV1,
    reviewed_count: usize,
    approved_count: usize,
    rejected_count: usize,
    overall_status: String,
    entries: Vec<EntriesReviewResultV1>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct EntriesRangeV1 {
    #[serde(default)]
    start: Option<String>,
    #[serde(default)]
    end: Option<String>,
    #[serde(default)]
    first_pose_id: Option<String>,
    #[serde(default)]
    last_pose_id: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct EntriesReviewResultV1 {
    pose_id: String,
    status: String,
    visual_note: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ResultsReviewReportV1 {
    #[serde(default)]
    schema_version: Option<u32>,
    batch_id: String,
    reviewer: String,
    #[serde(default)]
    range: Option<ResultsRangeV1>,
    #[serde(default)]
    ranges: Option<Vec<ResultsRangeV1>>,
    reviewed_count: usize,
    approved_count: usize,
    rejected_count: usize,
    status: String,
    results: Vec<ResultsReviewResultV1>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ResultsRangeV1 {
    start: String,
    end: String,
    inclusive: bool,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ResultsReviewResultV1 {
    id: String,
    decision: String,
    notes: String,
    comparison_path: String,
}

#[derive(Debug)]
enum ReviewReport {
    Entries(EntriesReviewReportV1),
    Results(ResultsReviewReportV1),
}

#[derive(Clone, Debug)]
struct NormalizedReview {
    pose_id: String,
}

#[derive(Debug)]
struct NormalizedReport {
    batch_id: String,
    schema_variant: &'static str,
    reviews: Vec<NormalizedReview>,
}

fn parse_review_report(
    path: &Path,
    bytes: &[u8],
    batch: usize,
) -> Result<NormalizedReport, String> {
    let envelope: Value = serde_json::from_slice(bytes)
        .map_err(|error| format!("invalid review report {}: {error}", path.display()))?;
    let object = envelope
        .as_object()
        .ok_or_else(|| format!("review report {} is not an object", path.display()))?;
    let has_entries = object.contains_key("entries");
    let has_results = object.contains_key("results");
    let report = match (has_entries, has_results) {
        (true, false) => {
            ReviewReport::Entries(serde_json::from_slice(bytes).map_err(|error| {
                format!("invalid entries-v1 report {}: {error}", path.display())
            })?)
        }
        (false, true) => {
            ReviewReport::Results(serde_json::from_slice(bytes).map_err(|error| {
                format!("invalid results-v1 report {}: {error}", path.display())
            })?)
        }
        _ => {
            return Err(format!(
                "{} must contain exactly one controlled entries/results report shape",
                path.display()
            ));
        }
    };
    normalize_review_report(path, report, batch)
}

fn normalize_review_report(
    path: &Path,
    report: ReviewReport,
    batch: usize,
) -> Result<NormalizedReport, String> {
    let expected_batch_id = format!("batch-{batch:02}");
    let expected_ids = expected_batch_pose_ids(batch);
    let expected_set = expected_ids.iter().cloned().collect::<BTreeSet<_>>();
    let (batch_id, reviewer, status, counts, schema_variant, reviews) = match report {
        ReviewReport::Entries(report) => {
            validate_review_schema(path, report.schema_version)?;
            if batch > 6 {
                return Err(format!(
                    "{} uses entries-v1 outside its controlled batch-01..06 scope",
                    path.display()
                ));
            }
            validate_entries_range(path, &report.range, &expected_ids)?;
            let reviews = report
                .entries
                .into_iter()
                .map(|entry| {
                    require_nonempty(path, "visual_note", &entry.visual_note)?;
                    if entry.status != "approved" {
                        return Err(format!(
                            "{} rejects {} with status {}",
                            path.display(),
                            entry.pose_id,
                            entry.status
                        ));
                    }
                    Ok(NormalizedReview {
                        pose_id: entry.pose_id,
                    })
                })
                .collect::<Result<Vec<_>, String>>()?;
            (
                report.batch_id,
                report.reviewer,
                report.overall_status,
                (
                    report.reviewed_count,
                    report.approved_count,
                    report.rejected_count,
                ),
                "entries-v1",
                reviews,
            )
        }
        ReviewReport::Results(report) => {
            validate_review_schema(path, report.schema_version)?;
            if batch < 7 {
                return Err(format!(
                    "{} uses results-v1 outside its controlled batch-07..08 scope",
                    path.display()
                ));
            }
            validate_results_ranges(path, report.range.as_ref(), report.ranges.as_deref(), batch)?;
            let reviews = report
                .results
                .into_iter()
                .map(|entry| {
                    require_nonempty(path, "notes", &entry.notes)?;
                    if entry.decision != "approved" {
                        return Err(format!(
                            "{} rejects {} with decision {}",
                            path.display(),
                            entry.id,
                            entry.decision
                        ));
                    }
                    let expected_path =
                        format!("evidence/pose-admission-v2/{}/comparison.png", entry.id);
                    if entry.comparison_path != expected_path {
                        return Err(format!(
                            "{} result {} declares comparison_path {}, expected {}",
                            path.display(),
                            entry.id,
                            entry.comparison_path,
                            expected_path
                        ));
                    }
                    Ok(NormalizedReview { pose_id: entry.id })
                })
                .collect::<Result<Vec<_>, String>>()?;
            (
                report.batch_id,
                report.reviewer,
                report.status,
                (
                    report.reviewed_count,
                    report.approved_count,
                    report.rejected_count,
                ),
                "results-v1",
                reviews,
            )
        }
    };

    require_nonempty(path, "reviewer", &reviewer)?;
    if batch_id != expected_batch_id {
        return Err(format!(
            "{} declares batch_id {batch_id}, expected {expected_batch_id}",
            path.display()
        ));
    }
    if status != "approved" {
        return Err(format!(
            "{} declares non-approved status {status}",
            path.display()
        ));
    }
    if counts != (reviews.len(), reviews.len(), 0) {
        return Err(format!(
            "{} count fields {:?} do not match {} approved reviews",
            path.display(),
            counts,
            reviews.len()
        ));
    }
    let actual_set = reviews
        .iter()
        .map(|review| review.pose_id.clone())
        .collect::<BTreeSet<_>>();
    if actual_set.len() != reviews.len() {
        return Err(format!("{} contains duplicate pose IDs", path.display()));
    }
    if actual_set != expected_set {
        return Err(census_error(
            &format!("{} review", path.display()),
            &expected_set,
            &actual_set,
        ));
    }
    Ok(NormalizedReport {
        batch_id,
        schema_variant,
        reviews,
    })
}

fn validate_review_schema(path: &Path, schema_version: Option<u32>) -> Result<(), String> {
    match schema_version {
        None | Some(REVIEW_REPORT_SCHEMA_VERSION) => Ok(()),
        Some(version) => Err(format!(
            "{} uses unsupported review schema {version}",
            path.display()
        )),
    }
}

fn validate_entries_range(
    path: &Path,
    range: &EntriesRangeV1,
    expected_ids: &[String],
) -> Result<(), String> {
    let expected_start = expected_ids
        .first()
        .ok_or_else(|| format!("{} has an empty expected range", path.display()))?;
    let expected_end = expected_ids
        .last()
        .ok_or_else(|| format!("{} has an empty expected range", path.display()))?;
    let declared = match (
        range.start.as_ref(),
        range.end.as_ref(),
        range.first_pose_id.as_ref(),
        range.last_pose_id.as_ref(),
    ) {
        (Some(start), Some(end), None, None) => (start, end),
        (None, None, Some(start), Some(end)) => (start, end),
        _ => {
            return Err(format!(
                "{} has a malformed entries-v1 range",
                path.display()
            ));
        }
    };
    if declared != (expected_start, expected_end) {
        return Err(format!(
            "{} declares range {}..{}, expected {}..{}",
            path.display(),
            declared.0,
            declared.1,
            expected_start,
            expected_end
        ));
    }
    Ok(())
}

fn validate_results_ranges(
    path: &Path,
    range: Option<&ResultsRangeV1>,
    ranges: Option<&[ResultsRangeV1]>,
    batch: usize,
) -> Result<(), String> {
    let expected = if batch == 7 {
        vec![ResultsRangeV1 {
            start: "WJPA-0193".to_string(),
            end: "WJPA-0224".to_string(),
            inclusive: true,
        }]
    } else {
        vec![
            ResultsRangeV1 {
                start: "WJPA-0225".to_string(),
                end: "WJPA-0250".to_string(),
                inclusive: true,
            },
            ResultsRangeV1 {
                start: "WJFF-0001".to_string(),
                end: "WJFF-0010".to_string(),
                inclusive: true,
            },
        ]
    };
    let declared = match (range, ranges) {
        (Some(range), None) => vec![range.clone()],
        (None, Some(ranges)) => ranges.to_vec(),
        _ => {
            return Err(format!(
                "{} must declare exactly one controlled range/ranges field",
                path.display()
            ));
        }
    };
    if declared != expected {
        return Err(format!(
            "{} declares ranges {declared:?}, expected {expected:?}",
            path.display()
        ));
    }
    Ok(())
}

fn require_nonempty(path: &Path, field: &str, value: &str) -> Result<(), String> {
    if value.trim().is_empty() {
        return Err(format!("{} has an empty {field}", path.display()));
    }
    Ok(())
}

#[derive(Clone, Debug, Default)]
struct InputBindings {
    hashes: BTreeMap<PathBuf, String>,
}

impl InputBindings {
    fn read(&mut self, path: &Path) -> Result<Vec<u8>, String> {
        let bytes =
            fs::read(path).map_err(|error| format!("cannot read {}: {error}", path.display()))?;
        self.bind(path, &bytes)?;
        Ok(bytes)
    }

    fn bind(&mut self, path: &Path, bytes: &[u8]) -> Result<String, String> {
        let hash = sha256_bytes(bytes);
        if let Some(previous) = self.hashes.insert(path.to_path_buf(), hash.clone()) {
            if previous != hash {
                return Err(format!(
                    "{} changed while preflight was reading it",
                    path.display()
                ));
            }
        }
        Ok(hash)
    }

    fn expected_hash(&self, path: &Path) -> Option<&str> {
        self.hashes.get(path).map(String::as_str)
    }

    fn recheck(&self) -> Result<(), String> {
        for (path, expected) in &self.hashes {
            let bytes = fs::read(path)
                .map_err(|error| format!("cannot recheck {}: {error}", path.display()))?;
            let actual = sha256_bytes(&bytes);
            if &actual != expected {
                return Err(format!(
                    "{} changed after preflight: expected {expected}, found {actual}",
                    path.display()
                ));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug)]
struct PlannedOutput {
    target: PathBuf,
    bytes: Vec<u8>,
}

#[derive(Debug)]
struct FinalizationPlan {
    bindings: InputBindings,
    outputs: Vec<PlannedOutput>,
    receipt: Value,
}

#[derive(Clone, Debug)]
struct ReviewAssignment {
    batch_id: String,
    report_path: String,
}

fn build_finalization_plan(root: &Path) -> Result<FinalizationPlan, String> {
    let v6_root = root.join("rust/wizard_avatar_engine/assets/pose_graphs/v6");
    let manifest_path = v6_root.join("runtime-manifest.json");
    let graph_root = v6_root.join("graphs");
    let evidence_root = root.join("evidence/pose-admission-v2");
    let report_root = evidence_root.join("visual-review-batches");
    let source_ledger_path =
        root.join("docs/pose-admission-v2/wizard-joe-alpha-source-ledger.json");
    let admission_path = root.join("docs/pose-admission-v2/wizard-joe-alpha-admission-ledger.json");
    let summary_path = root.join("docs/pose-admission-v2/summary.json");
    let aggregate_path = report_root.join("visual-review-summary.json");
    if aggregate_path.exists() {
        return Err(format!(
            "{} already exists; refusing to overwrite a prior admission receipt",
            aggregate_path.display()
        ));
    }

    let expected_ids = expected_pose_ids();
    let expected_set = expected_ids.iter().cloned().collect::<BTreeSet<_>>();
    validate_file_census(
        &graph_root,
        &expected_ids
            .iter()
            .map(|pose_id| format!("{pose_id}.pixelgraph.json.gz"))
            .collect::<BTreeSet<_>>(),
        "graph directory",
    )?;
    validate_file_census(
        &report_root,
        &(1..=EXPECTED_BATCH_COUNT)
            .map(|batch| format!("batch-{batch:02}.json"))
            .collect::<BTreeSet<_>>(),
        "review report directory",
    )?;

    let mut bindings = InputBindings::default();
    let (manifest, manifest_bytes): (ProductionAlphaRuntimeManifest, Vec<u8>) =
        read_bound_json(&mut bindings, &manifest_path)?;
    let (source_ledger, source_ledger_bytes): (ProductionAlphaSourceLedger, Vec<u8>) =
        read_bound_json(&mut bindings, &source_ledger_path)?;
    let (admission, admission_bytes): (ProductionAlphaAdmissionLedger, Vec<u8>) =
        read_bound_json(&mut bindings, &admission_path)?;
    let (summary, summary_bytes): (ProductionAlphaSummary, Vec<u8>) =
        read_bound_json(&mut bindings, &summary_path)?;

    validate_documents(
        &manifest,
        &source_ledger,
        &admission,
        &summary,
        &expected_ids,
        &expected_set,
    )?;

    let manifest_sha256 = sha256_bytes(&manifest_bytes);
    let source_ledger_sha256 = sha256_bytes(&source_ledger_bytes);
    let admission_input_sha256 = sha256_bytes(&admission_bytes);
    let summary_input_sha256 = sha256_bytes(&summary_bytes);

    let mut reviews = BTreeMap::<String, ReviewAssignment>::new();
    let mut report_receipts = Vec::with_capacity(EXPECTED_BATCH_COUNT);
    for batch in 1..=EXPECTED_BATCH_COUNT {
        let batch_id = format!("batch-{batch:02}");
        let report_path = report_root.join(format!("{batch_id}.json"));
        let bytes = bindings.read(&report_path)?;
        let report = parse_review_report(&report_path, &bytes, batch)?;
        let report_relative = relative_path(root, &report_path)?;
        for review in report.reviews {
            if reviews
                .insert(
                    review.pose_id.clone(),
                    ReviewAssignment {
                        batch_id: report.batch_id.clone(),
                        report_path: report_relative.clone(),
                    },
                )
                .is_some()
            {
                return Err(format!("duplicate visual review for {}", review.pose_id));
            }
        }
        report_receipts.push(json!({
            "batch_id": report.batch_id,
            "schema_version": REVIEW_REPORT_SCHEMA_VERSION,
            "schema_variant": report.schema_variant,
            "path": report_relative,
            "sha256": sha256_bytes(&bytes),
            "reviewed_count": expected_batch_pose_ids(batch).len()
        }));
    }
    let reviewed = reviews.keys().cloned().collect::<BTreeSet<_>>();
    if reviewed != expected_set {
        return Err(census_error("visual review", &expected_set, &reviewed));
    }

    let mut outputs = Vec::with_capacity(EXPECTED_POSE_COUNT + 3);
    let mut pose_receipts = Vec::with_capacity(EXPECTED_POSE_COUNT);
    for (index, pose_id) in expected_ids.iter().enumerate() {
        let runtime = &manifest.entries[index];
        let source = &source_ledger.entries[index];
        let admission_entry = &admission.entries[index];
        let graph_path = v6_root.join(&runtime.graph_path);
        let graph_bytes = bindings.read(&graph_path)?;
        let graph_sha256 = sha256_bytes(&graph_bytes);
        if graph_sha256 != runtime.graph_sha256 {
            return Err(format!(
                "{pose_id} graph hash {graph_sha256} does not match manifest {}",
                runtime.graph_sha256
            ));
        }
        let graph = read_graph_bytes(pose_id, &graph_bytes)?;
        validate_graph_binding(pose_id, runtime, &graph)?;
        let graph_projection = project_pixel_graph(&graph)
            .map_err(|error| format!("{pose_id} graph projection failed: {error}"))?;

        let evidence_dir = evidence_root.join(pose_id);
        validate_file_census(
            &evidence_dir,
            &[
                "source.png",
                "projected.png",
                "transparent-overlay.png",
                "composite.png",
                "comparison.png",
                "verification.json",
            ]
            .into_iter()
            .map(str::to_string)
            .collect(),
            &format!("{pose_id} evidence directory"),
        )?;
        let verification_path = evidence_dir.join("verification.json");
        let (mut verification, verification_bytes): (ProductionAlphaVerification, Vec<u8>) =
            read_bound_json(&mut bindings, &verification_path)?;
        validate_verification_binding(
            pose_id,
            index + 1,
            runtime,
            source,
            admission_entry,
            &verification,
        )?;

        let source_image = read_evidence_image(
            &mut bindings,
            &evidence_dir,
            pose_id,
            "source.png",
            &verification.artifacts.source_png,
            (FRAME_SIZE, FRAME_SIZE),
        )?;
        let projected_image = read_evidence_image(
            &mut bindings,
            &evidence_dir,
            pose_id,
            "projected.png",
            &verification.artifacts.projected_png,
            (FRAME_SIZE, FRAME_SIZE),
        )?;
        let overlay_image = read_evidence_image(
            &mut bindings,
            &evidence_dir,
            pose_id,
            "transparent-overlay.png",
            &verification.artifacts.transparent_overlay_png,
            (FRAME_SIZE, FRAME_SIZE),
        )?;
        let composite_image = read_evidence_image(
            &mut bindings,
            &evidence_dir,
            pose_id,
            "composite.png",
            &verification.artifacts.composite_png,
            (FRAME_SIZE, FRAME_SIZE),
        )?;
        let comparison_image = read_evidence_image(
            &mut bindings,
            &evidence_dir,
            pose_id,
            "comparison.png",
            &verification.artifacts.comparison_png,
            (FRAME_SIZE * 2, FRAME_SIZE * 2),
        )?;

        if sha256_file_binding(&bindings, &evidence_dir.join("source.png"))?
            != runtime.source_sha256
        {
            return Err(format!(
                "{pose_id} source artifact hash does not match runtime manifest"
            ));
        }
        if source_image != graph_projection || projected_image != graph_projection {
            return Err(format!(
                "{pose_id} source/projected evidence does not equal graph projection"
            ));
        }
        let verification_config = VerificationConfig {
            foreground_alpha_threshold: 1,
            color_match_tolerance: 0,
        };
        let recomputed_metrics =
            verify_pose_graph(&source_image, &graph_projection, verification_config)
                .map_err(|error| format!("{pose_id} metric verification failed: {error}"))?;
        if recomputed_metrics != verification.metrics {
            return Err(format!(
                "{pose_id} recomputed metrics do not match verification"
            ));
        }
        let recomputed_overlay = build_transparent_overlay(
            &source_image,
            &graph_projection,
            verification_config,
            OverlayPalette::default(),
        )
        .map_err(|error| format!("{pose_id} overlay reconstruction failed: {error}"))?;
        if recomputed_overlay.counts != verification.overlay_counts
            || recomputed_overlay.image != overlay_image
        {
            return Err(format!(
                "{pose_id} overlay evidence does not match reconstruction"
            ));
        }
        let recomputed_composite =
            composite_graph_over_source(&source_image, &graph_projection, 128)
                .map_err(|error| format!("{pose_id} composite reconstruction failed: {error}"))?;
        if recomputed_composite != composite_image {
            return Err(format!(
                "{pose_id} composite evidence does not match reconstruction"
            ));
        }
        let recomputed_comparison = build_comparison(
            &source_image,
            &graph_projection,
            &recomputed_overlay.image,
            &recomputed_composite,
        );
        if recomputed_comparison != comparison_image {
            return Err(format!(
                "{pose_id} comparison evidence does not match reconstruction"
            ));
        }

        let verification_input_sha256 = sha256_bytes(&verification_bytes);
        verification.visual_review_status = APPROVED_STATUS.to_string();
        let updated_verification_bytes = serialize_json(&verification_path, &verification)?;
        let updated_verification_sha256 = sha256_bytes(&updated_verification_bytes);
        outputs.push(PlannedOutput {
            target: verification_path.clone(),
            bytes: updated_verification_bytes,
        });

        let assignment = reviews
            .get(pose_id)
            .ok_or_else(|| format!("missing review assignment for {pose_id}"))?;
        pose_receipts.push(json!({
            "sequence": index + 1,
            "pose_id": pose_id,
            "semantic_id": runtime.semantic_id,
            "decision": "approved",
            "batch_id": assignment.batch_id,
            "batch_report_path": assignment.report_path,
            "source_png_sha256": runtime.source_sha256,
            "graph": {
                "path": relative_path(root, &graph_path)?,
                "sha256": graph_sha256
            },
            "verification": {
                "path": relative_path(root, &verification_path)?,
                "preflight_sha256": verification_input_sha256,
                "sha256": updated_verification_sha256
            },
            "evidence_artifacts": {
                "source": bound_artifact_receipt(root, &bindings, &evidence_dir.join("source.png"))?,
                "projected": bound_artifact_receipt(root, &bindings, &evidence_dir.join("projected.png"))?,
                "transparent_overlay": bound_artifact_receipt(root, &bindings, &evidence_dir.join("transparent-overlay.png"))?,
                "composite": bound_artifact_receipt(root, &bindings, &evidence_dir.join("composite.png"))?,
                "comparison": bound_artifact_receipt(root, &bindings, &evidence_dir.join("comparison.png"))?
            }
        }));
    }

    let mut updated_admission = admission;
    for entry in &mut updated_admission.entries {
        entry.visual_review_status = APPROVED_STATUS.to_string();
    }
    updated_admission.visual_review_pending_count = 0;
    let updated_admission_bytes = serialize_json(&admission_path, &updated_admission)?;
    let updated_admission_sha256 = sha256_bytes(&updated_admission_bytes);
    outputs.push(PlannedOutput {
        target: admission_path.clone(),
        bytes: updated_admission_bytes,
    });

    let mut updated_summary = summary;
    updated_summary.visual_review_pending_count = 0;
    let updated_summary_bytes = serialize_json(&summary_path, &updated_summary)?;
    let updated_summary_sha256 = sha256_bytes(&updated_summary_bytes);
    outputs.push(PlannedOutput {
        target: summary_path.clone(),
        bytes: updated_summary_bytes,
    });

    let aggregate = json!({
        "schema_version": AGGREGATE_SCHEMA_VERSION,
        "compiler_id": PRODUCTION_ALPHA_COMPILER_ID,
        "review_protocol": REVIEW_PROTOCOL,
        "expected_pose_count": EXPECTED_POSE_COUNT,
        "reviewed_pose_count": EXPECTED_POSE_COUNT,
        "approved_pose_count": EXPECTED_POSE_COUNT,
        "rejected_pose_count": 0,
        "status": "approved",
        "runtime_manifest": {
            "path": relative_path(root, &manifest_path)?,
            "sha256": manifest_sha256
        },
        "source_ledger": {
            "path": relative_path(root, &source_ledger_path)?,
            "sha256": source_ledger_sha256
        },
        "admission_ledger": {
            "path": relative_path(root, &admission_path)?,
            "preflight_sha256": admission_input_sha256,
            "sha256": updated_admission_sha256
        },
        "summary": {
            "path": relative_path(root, &summary_path)?,
            "preflight_sha256": summary_input_sha256,
            "sha256": updated_summary_sha256
        },
        "batch_reports": report_receipts,
        "poses": pose_receipts
    });
    let aggregate_bytes = serialize_json(&aggregate_path, &aggregate)?;
    let aggregate_sha256 = sha256_bytes(&aggregate_bytes);
    outputs.push(PlannedOutput {
        target: aggregate_path.clone(),
        bytes: aggregate_bytes,
    });

    let receipt = json!({
        "schema_version": AGGREGATE_SCHEMA_VERSION,
        "status": "approved",
        "reviewed_pose_count": EXPECTED_POSE_COUNT,
        "approved_pose_count": EXPECTED_POSE_COUNT,
        "rejected_pose_count": 0,
        "runtime_manifest_sha256": manifest_sha256,
        "admission_ledger_sha256": updated_admission_sha256,
        "summary_sha256": updated_summary_sha256,
        "aggregate_report_path": relative_path(root, &aggregate_path)?,
        "aggregate_report_sha256": aggregate_sha256
    });

    Ok(FinalizationPlan {
        bindings,
        outputs,
        receipt,
    })
}

fn validate_documents(
    manifest: &ProductionAlphaRuntimeManifest,
    source_ledger: &ProductionAlphaSourceLedger,
    admission: &ProductionAlphaAdmissionLedger,
    summary: &ProductionAlphaSummary,
    expected_ids: &[String],
    expected_set: &BTreeSet<String>,
) -> Result<(), String> {
    if manifest.schema_version != PRODUCTION_ALPHA_SCHEMA_VERSION
        || manifest.compiler_id != PRODUCTION_ALPHA_COMPILER_ID
        || manifest.frame != [FRAME_SIZE, FRAME_SIZE]
        || manifest.source_count != EXPECTED_POSE_COUNT
        || manifest.base_pose_count != 250
        || manifest.forward_flight_count != 10
        || manifest.verified_pose_count != EXPECTED_POSE_COUNT
        || manifest.primary_pose_count != EXPECTED_POSE_COUNT
        || manifest.unique_semantic_pose_count != EXPECTED_POSE_COUNT
        || manifest.entries.len() != EXPECTED_POSE_COUNT
        || manifest.archives.len() != 2
    {
        return Err("runtime manifest census/schema fields are not canonical".to_string());
    }
    if source_ledger.schema_version != PRODUCTION_ALPHA_SCHEMA_VERSION
        || source_ledger.compiler_id != PRODUCTION_ALPHA_COMPILER_ID
        || source_ledger.expected_source_count != EXPECTED_POSE_COUNT
        || source_ledger.entries.len() != EXPECTED_POSE_COUNT
        || source_ledger.archives != manifest.archives
    {
        return Err("source ledger census/schema/archive fields are not canonical".to_string());
    }
    if admission.schema_version != PRODUCTION_ALPHA_SCHEMA_VERSION
        || admission.compiler_id != PRODUCTION_ALPHA_COMPILER_ID
        || admission.expected_pose_count != EXPECTED_POSE_COUNT
        || admission.exact_rgba_verified_count != EXPECTED_POSE_COUNT
        || admission.visual_review_pending_count != EXPECTED_POSE_COUNT
        || admission.failed_count != 0
        || admission.entries.len() != EXPECTED_POSE_COUNT
    {
        return Err("admission ledger is malformed or not fully pending".to_string());
    }
    if summary.schema_version != PRODUCTION_ALPHA_SCHEMA_VERSION
        || summary.compiler_id != PRODUCTION_ALPHA_COMPILER_ID
        || summary.source_count != EXPECTED_POSE_COUNT
        || summary.base_pose_count != 250
        || summary.forward_flight_count != 10
        || summary.exact_rgba_verified_count != EXPECTED_POSE_COUNT
        || summary.graph_count != EXPECTED_POSE_COUNT
        || summary.visual_review_pending_count != EXPECTED_POSE_COUNT
        || summary.failed_count != 0
        || summary.frame.width != FRAME_SIZE
        || summary.frame.height != FRAME_SIZE
        || summary.policy.trim().is_empty()
    {
        return Err("summary is malformed or not fully pending".to_string());
    }

    let mut semantic_ids = BTreeSet::new();
    for (index, expected_id) in expected_ids.iter().enumerate() {
        let sequence = index + 1;
        let runtime = &manifest.entries[index];
        let source = &source_ledger.entries[index];
        let admission_entry = &admission.entries[index];
        if runtime.sequence != sequence
            || runtime.pose_id != *expected_id
            || runtime.source_record_id != *expected_id
            || runtime.candidate_id != *expected_id
            || source.sequence != sequence
            || source.pose_id != *expected_id
            || admission_entry.sequence != sequence
            || admission_entry.pose_id != *expected_id
        {
            return Err(format!("{expected_id} document sequence/identity mismatch"));
        }
        if !semantic_ids.insert(runtime.semantic_id.clone()) {
            return Err(format!("duplicate semantic_id {}", runtime.semantic_id));
        }
        if runtime.semantic_id != source.semantic_id
            || runtime.source_pack != source.source_pack
            || runtime.source_entry != source.source_member
            || runtime.source_sha256 != source.source_png_sha256
            || runtime.category != source.category
            || runtime.graph_path != format!("graphs/{expected_id}.pixelgraph.json.gz")
            || runtime.graph_id != format!("{}-pixelgraph-v1", expected_id.to_ascii_lowercase())
            || runtime.evidence_path != format!("evidence/{expected_id}")
            || runtime.frame != [FRAME_SIZE, FRAME_SIZE]
            || runtime.source_size != [FRAME_SIZE, FRAME_SIZE]
            || runtime.offset != [0, 0]
            || !runtime.primary_for_semantic_id
            || !runtime.exact_rgba_equal
            || runtime.rgba_mismatch_pixel_count != 0
            || runtime.rgba_mismatch_channel_count != 0
            || runtime.silhouette_iou_millionths != 1_000_000
            || runtime.foreground_color_fidelity_millionths != 1_000_000
            || runtime.foreground_color_match_ratio_millionths != 1_000_000
        {
            return Err(format!("{expected_id} runtime/source binding mismatch"));
        }
        let archive = manifest
            .archives
            .iter()
            .find(|archive| archive.source_pack == source.source_pack)
            .ok_or_else(|| format!("{expected_id} references an unknown source pack"))?;
        if archive.archive_filename != runtime.source_archive
            || archive.archive_sha256 != source.archive_sha256
        {
            return Err(format!("{expected_id} archive provenance mismatch"));
        }
        if admission_entry.technical_status != TECHNICAL_STATUS
            || admission_entry.visual_review_status != PENDING_STATUS
            || admission_entry.source_png_sha256 != runtime.source_sha256
            || admission_entry.graph_sha256 != runtime.graph_sha256
            || admission_entry.graph_path != runtime.graph_path
            || admission_entry.evidence_path != runtime.evidence_path
            || admission_entry.verification_report_path
                != format!("evidence/{expected_id}/verification.json")
        {
            return Err(format!("{expected_id} admission ledger binding mismatch"));
        }
    }
    if semantic_ids.len() != EXPECTED_POSE_COUNT {
        return Err("semantic census is not unique".to_string());
    }
    for entry in &manifest.entries {
        for neighbor in &entry.authored_transition_neighbors {
            if !semantic_ids.contains(neighbor) {
                return Err(format!(
                    "{} references unknown transition neighbor {neighbor}",
                    entry.pose_id
                ));
            }
        }
    }
    let actual_ids = manifest
        .entries
        .iter()
        .map(|entry| entry.pose_id.clone())
        .collect::<BTreeSet<_>>();
    if actual_ids != *expected_set {
        return Err(census_error("runtime manifest", expected_set, &actual_ids));
    }
    Ok(())
}

fn validate_graph_binding(
    pose_id: &str,
    runtime: &wizard_avatar_pose_tool::RuntimeAlphaEntry,
    graph: &PixelGraph,
) -> Result<(), String> {
    if graph.schema_version != 1
        || graph.graph_id != runtime.graph_id
        || graph.source_record_id != pose_id
        || graph.source_sha256 != runtime.source_sha256
        || graph.frame.width != FRAME_SIZE
        || graph.frame.height != FRAME_SIZE
        || graph.source_width != FRAME_SIZE
        || graph.source_height != FRAME_SIZE
        || graph.offset_x != 0
        || graph.offset_y != 0
        || graph.foreground_pixel_count != runtime.foreground_pixel_count
    {
        return Err(format!("{pose_id} graph binding mismatch"));
    }
    Ok(())
}

fn validate_verification_binding(
    pose_id: &str,
    sequence: usize,
    runtime: &wizard_avatar_pose_tool::RuntimeAlphaEntry,
    source: &wizard_avatar_pose_tool::ProductionAlphaSourceEntry,
    admission: &wizard_avatar_pose_tool::ProductionAlphaAdmissionEntry,
    verification: &ProductionAlphaVerification,
) -> Result<(), String> {
    let bounds = verification.foreground_bounds;
    let bounds_right = bounds
        .x
        .checked_add(bounds.width)
        .ok_or_else(|| format!("{pose_id} foreground bounds overflow"))?;
    let bounds_bottom = bounds
        .y
        .checked_add(bounds.height)
        .ok_or_else(|| format!("{pose_id} foreground bounds overflow"))?;
    if verification.schema_version != PRODUCTION_ALPHA_SCHEMA_VERSION
        || verification.compiler_id != PRODUCTION_ALPHA_COMPILER_ID
        || verification.sequence != sequence
        || verification.pose_id != pose_id
        || verification.semantic_id != runtime.semantic_id
        || verification.source_pack != runtime.source_pack
        || verification.source_archive_sha256 != source.archive_sha256
        || verification.source_member != runtime.source_entry
        || verification.source_png_sha256 != runtime.source_sha256
        || verification.frame.width != FRAME_SIZE
        || verification.frame.height != FRAME_SIZE
        || bounds.width == 0
        || bounds.height == 0
        || bounds.x < REQUIRED_SAFE_MARGIN
        || bounds.y < REQUIRED_SAFE_MARGIN
        || bounds_right > FRAME_SIZE - REQUIRED_SAFE_MARGIN
        || bounds_bottom > FRAME_SIZE - REQUIRED_SAFE_MARGIN
        || verification.safe_margin_px != REQUIRED_SAFE_MARGIN
        || !verification.transparent_corners
        || verification.foreground_pixel_count != runtime.foreground_pixel_count
        || !verification.exact_rgba_equal
        || verification.rgba_mismatch.pixel_count != 0
        || verification.rgba_mismatch.channel_count != 0
        || verification.rgba_mismatch.first_x.is_some()
        || verification.rgba_mismatch.first_y.is_some()
        || verification.metrics.silhouette_precision != 1.0
        || verification.metrics.silhouette_recall != 1.0
        || verification.metrics.silhouette_iou != 1.0
        || verification.metrics.foreground_color_match_ratio != 1.0
        || verification.metrics.foreground_color_fidelity != 1.0
        || verification.metrics.source_foreground_pixels != runtime.foreground_pixel_count
        || verification.metrics.graph_foreground_pixels != runtime.foreground_pixel_count
        || verification.metrics.intersection_pixels != runtime.foreground_pixel_count
        || verification.metrics.union_pixels != runtime.foreground_pixel_count
        || verification.metrics.missing_pixels != 0
        || verification.metrics.extra_pixels != 0
        || verification.metrics.color_matched_pixels != runtime.foreground_pixel_count
        || verification.metrics.color_mismatched_pixels != 0
        || verification.overlay_counts.matched != runtime.foreground_pixel_count
        || verification.overlay_counts.missing != 0
        || verification.overlay_counts.extra != 0
        || verification.overlay_counts.mismatched != 0
        || verification.graph_path != runtime.graph_path
        || verification.graph_sha256 != runtime.graph_sha256
        || verification.technical_status != TECHNICAL_STATUS
        || verification.visual_review_status != PENDING_STATUS
        || admission.technical_status != TECHNICAL_STATUS
        || admission.visual_review_status != PENDING_STATUS
    {
        return Err(format!(
            "{pose_id} verification is malformed, failed, stale, or not pending"
        ));
    }
    Ok(())
}

fn read_evidence_image(
    bindings: &mut InputBindings,
    evidence_dir: &Path,
    pose_id: &str,
    filename: &str,
    declaration: &ProductionAlphaEvidenceArtifact,
    dimensions: (u32, u32),
) -> Result<RgbaImage, String> {
    let expected_declaration = format!("evidence/{pose_id}/{filename}");
    if declaration.path != expected_declaration {
        return Err(format!(
            "{pose_id} {filename} declares path {}, expected {expected_declaration}",
            declaration.path
        ));
    }
    let path = evidence_dir.join(filename);
    let bytes = bindings.read(&path)?;
    let actual_sha256 = sha256_bytes(&bytes);
    if actual_sha256 != declaration.sha256 {
        return Err(format!(
            "{} hash {actual_sha256} does not match declaration {}",
            path.display(),
            declaration.sha256
        ));
    }
    let image = image::load_from_memory_with_format(&bytes, ImageFormat::Png)
        .map_err(|error| format!("cannot decode {}: {error}", path.display()))?
        .into_rgba8();
    if image.dimensions() != dimensions {
        return Err(format!(
            "{} dimensions {:?} do not match {dimensions:?}",
            path.display(),
            image.dimensions()
        ));
    }
    Ok(image)
}

fn build_comparison(
    source: &RgbaImage,
    projected: &RgbaImage,
    overlay: &RgbaImage,
    composite: &RgbaImage,
) -> RgbaImage {
    let mut comparison =
        RgbaImage::from_pixel(FRAME_SIZE * 2, FRAME_SIZE * 2, Rgba([255, 255, 255, 255]));
    place_on_checkerboard(&mut comparison, source, 0, 0);
    place_on_checkerboard(&mut comparison, projected, FRAME_SIZE, 0);
    place_on_checkerboard(&mut comparison, overlay, 0, FRAME_SIZE);
    place_on_checkerboard(&mut comparison, composite, FRAME_SIZE, FRAME_SIZE);
    comparison
}

fn place_on_checkerboard(canvas: &mut RgbaImage, image: &RgbaImage, offset_x: u32, offset_y: u32) {
    for y in 0..image.height() {
        for x in 0..image.width() {
            let checker = if ((x / 16) + (y / 16)) % 2 == 0 {
                238
            } else {
                214
            };
            let base = Rgba([checker, checker, checker, 255]);
            canvas.put_pixel(
                offset_x + x,
                offset_y + y,
                alpha_over_opaque(base, *image.get_pixel(x, y)),
            );
        }
    }
}

fn alpha_over_opaque(base: Rgba<u8>, foreground: Rgba<u8>) -> Rgba<u8> {
    let alpha = u32::from(foreground[3]);
    let inverse = 255 - alpha;
    Rgba([
        ((u32::from(foreground[0]) * alpha + u32::from(base[0]) * inverse + 127) / 255) as u8,
        ((u32::from(foreground[1]) * alpha + u32::from(base[1]) * inverse + 127) / 255) as u8,
        ((u32::from(foreground[2]) * alpha + u32::from(base[2]) * inverse + 127) / 255) as u8,
        255,
    ])
}

fn read_graph_bytes(pose_id: &str, bytes: &[u8]) -> Result<PixelGraph, String> {
    serde_json::from_reader(GzDecoder::new(Cursor::new(bytes)))
        .map_err(|error| format!("{pose_id} graph gzip/JSON decode failed: {error}"))
}

fn read_bound_json<T: DeserializeOwned>(
    bindings: &mut InputBindings,
    path: &Path,
) -> Result<(T, Vec<u8>), String> {
    let bytes = bindings.read(path)?;
    let value = serde_json::from_slice(&bytes)
        .map_err(|error| format!("invalid JSON {}: {error}", path.display()))?;
    Ok((value, bytes))
}

fn serialize_json<T: Serialize>(path: &Path, value: &T) -> Result<Vec<u8>, String> {
    let mut bytes = serde_json::to_vec_pretty(value)
        .map_err(|error| format!("cannot serialize {}: {error}", path.display()))?;
    bytes.push(b'\n');
    Ok(bytes)
}

fn validate_file_census(
    directory: &Path,
    expected: &BTreeSet<String>,
    label: &str,
) -> Result<(), String> {
    let mut actual = BTreeSet::new();
    let entries = fs::read_dir(directory)
        .map_err(|error| format!("cannot read {label} {}: {error}", directory.display()))?;
    for entry in entries {
        let entry = entry
            .map_err(|error| format!("cannot read {label} {}: {error}", directory.display()))?;
        let file_type = entry
            .file_type()
            .map_err(|error| format!("cannot stat {}: {error}", entry.path().display()))?;
        if file_type.is_file() {
            let name = entry
                .file_name()
                .into_string()
                .map_err(|_| format!("{} contains a non-UTF-8 filename", directory.display()))?;
            if !name.starts_with(".production-alpha-finalize") {
                actual.insert(name);
            }
        }
    }
    if &actual != expected {
        return Err(census_error(label, expected, &actual));
    }
    Ok(())
}

fn bound_artifact_receipt(
    root: &Path,
    bindings: &InputBindings,
    path: &Path,
) -> Result<Value, String> {
    Ok(json!({
        "path": relative_path(root, path)?,
        "sha256": sha256_file_binding(bindings, path)?
    }))
}

fn sha256_file_binding<'a>(bindings: &'a InputBindings, path: &Path) -> Result<&'a str, String> {
    bindings
        .expected_hash(path)
        .ok_or_else(|| format!("{} was not bound during preflight", path.display()))
}

fn stage_and_publish(
    report_root: &Path,
    bindings: &InputBindings,
    outputs: &[PlannedOutput],
    fail_before_output: Option<usize>,
) -> Result<(), String> {
    let stage_root = report_root.join(format!(
        ".production-alpha-finalize-stage-{}-{}",
        std::process::id(),
        unique_timestamp()
    ));
    let new_root = stage_root.join("new");
    let backup_root = stage_root.join("backup");
    if let Err(error) = fs::create_dir_all(&new_root) {
        let _ = fs::remove_dir_all(&stage_root);
        return Err(format!(
            "cannot create stage {}: {error}",
            new_root.display()
        ));
    }

    let result = (|| {
        let mut staged = Vec::with_capacity(outputs.len());
        for (index, output) in outputs.iter().enumerate() {
            let staged_path = new_root.join(format!("{index:04}.json"));
            write_synced(&staged_path, &output.bytes)?;
            let staged_bytes = fs::read(&staged_path)
                .map_err(|error| format!("cannot verify {}: {error}", staged_path.display()))?;
            if sha256_bytes(&staged_bytes) != sha256_bytes(&output.bytes) {
                return Err(format!(
                    "{} does not match its planned output bytes",
                    staged_path.display()
                ));
            }
            staged.push(staged_path);
        }
        sync_directory(&new_root)?;

        bindings.recheck()?;

        let mut backups = Vec::with_capacity(outputs.len());
        for (index, output) in outputs.iter().enumerate() {
            if output.target.exists() {
                let original = fs::read(&output.target).map_err(|error| {
                    format!(
                        "cannot read output backup source {}: {error}",
                        output.target.display()
                    )
                })?;
                let expected = bindings.expected_hash(&output.target).ok_or_else(|| {
                    format!(
                        "{} existed but was not bound during preflight",
                        output.target.display()
                    )
                })?;
                let actual = sha256_bytes(&original);
                if actual != expected {
                    return Err(format!(
                        "{} changed before backup: expected {expected}, found {actual}",
                        output.target.display()
                    ));
                }
                let backup_path = backup_root.join(format!("{index:04}.json"));
                write_synced(&backup_path, &original)?;
                backups.push(Some(backup_path));
            } else {
                backups.push(None);
            }
        }
        if backup_root.exists() {
            sync_directory(&backup_root)?;
        }

        let mut published = Vec::new();
        let publish_result = (|| {
            for (index, output) in outputs.iter().enumerate() {
                if fail_before_output == Some(index) {
                    return Err(format!("injected publish failure before output {index}"));
                }
                fs::rename(&staged[index], &output.target).map_err(|error| {
                    format!(
                        "cannot atomically publish {}: {error}",
                        output.target.display()
                    )
                })?;
                sync_parent(&output.target)?;
                published.push(index);
            }
            Ok(())
        })();
        if let Err(error) = publish_result {
            let rollback_errors = rollback_outputs(outputs, &backups, &published);
            if rollback_errors.is_empty() {
                return Err(error);
            }
            return Err(format!(
                "{error}; rollback also failed: {}",
                rollback_errors.join("; ")
            ));
        }
        Ok(())
    })();

    let cleanup_result = if stage_root.exists() {
        fs::remove_dir_all(&stage_root)
            .map_err(|error| format!("cannot clean stage {}: {error}", stage_root.display()))
    } else {
        Ok(())
    };
    match (result, cleanup_result) {
        (Ok(()), Ok(())) => Ok(()),
        (Err(error), Ok(())) => Err(error),
        (Ok(()), Err(cleanup)) => Err(cleanup),
        (Err(error), Err(cleanup)) => Err(format!("{error}; {cleanup}")),
    }
}

fn rollback_outputs(
    outputs: &[PlannedOutput],
    backups: &[Option<PathBuf>],
    published: &[usize],
) -> Vec<String> {
    let mut errors = Vec::new();
    for index in published.iter().rev().copied() {
        let output = &outputs[index];
        let result = if let Some(backup) = &backups[index] {
            if output.target.exists() {
                fs::remove_file(&output.target)
                    .map_err(|error| {
                        format!(
                            "cannot remove published {}: {error}",
                            output.target.display()
                        )
                    })
                    .and_then(|_| {
                        fs::rename(backup, &output.target).map_err(|error| {
                            format!(
                                "cannot restore backup for {}: {error}",
                                output.target.display()
                            )
                        })
                    })
            } else {
                fs::rename(backup, &output.target).map_err(|error| {
                    format!(
                        "cannot restore missing {}: {error}",
                        output.target.display()
                    )
                })
            }
        } else if output.target.exists() {
            fs::remove_file(&output.target).map_err(|error| {
                format!(
                    "cannot remove newly published {}: {error}",
                    output.target.display()
                )
            })
        } else {
            Ok(())
        };
        if let Err(error) = result {
            errors.push(error);
        } else if let Err(error) = sync_parent(&output.target) {
            errors.push(error);
        }
    }
    errors
}

fn write_synced(path: &Path, bytes: &[u8]) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|error| format!("cannot create {}: {error}", parent.display()))?;
    }
    let mut file =
        File::create(path).map_err(|error| format!("cannot create {}: {error}", path.display()))?;
    file.write_all(bytes)
        .map_err(|error| format!("cannot write {}: {error}", path.display()))?;
    file.sync_all()
        .map_err(|error| format!("cannot sync {}: {error}", path.display()))
}

fn sync_parent(path: &Path) -> Result<(), String> {
    let parent = path
        .parent()
        .ok_or_else(|| format!("{} has no parent directory", path.display()))?;
    sync_directory(parent)
}

fn sync_directory(path: &Path) -> Result<(), String> {
    let directory =
        File::open(path).map_err(|error| format!("cannot open {}: {error}", path.display()))?;
    directory
        .sync_all()
        .map_err(|error| format!("cannot sync {}: {error}", path.display()))
}

struct ExclusiveLock {
    path: PathBuf,
    _file: File,
}

impl ExclusiveLock {
    fn acquire(path: &Path) -> Result<Self, String> {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .map_err(|error| {
                format!(
                    "cannot acquire exclusive finalizer lock {}: {error}",
                    path.display()
                )
            })?;
        let initialize = (|| {
            writeln!(file, "pid={}", std::process::id())
                .map_err(|error| format!("cannot write lock {}: {error}", path.display()))?;
            file.sync_all()
                .map_err(|error| format!("cannot sync lock {}: {error}", path.display()))?;
            sync_parent(path)
        })();
        if let Err(error) = initialize {
            drop(file);
            let _ = fs::remove_file(path);
            let _ = sync_parent(path);
            return Err(error);
        }
        Ok(Self {
            path: path.to_path_buf(),
            _file: file,
        })
    }
}

impl Drop for ExclusiveLock {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.path);
        let _ = sync_parent(&self.path);
    }
}

fn expected_pose_ids() -> Vec<String> {
    let mut ids = (1..=250)
        .map(|index| format!("WJPA-{index:04}"))
        .collect::<Vec<_>>();
    ids.extend((1..=10).map(|index| format!("WJFF-{index:04}")));
    ids
}

fn expected_batch_pose_ids(batch: usize) -> Vec<String> {
    match batch {
        1..=7 => {
            let start = (batch - 1) * 32 + 1;
            let end = batch * 32;
            (start..=end)
                .map(|index| format!("WJPA-{index:04}"))
                .collect()
        }
        8 => {
            let mut ids = (225..=250)
                .map(|index| format!("WJPA-{index:04}"))
                .collect::<Vec<_>>();
            ids.extend((1..=10).map(|index| format!("WJFF-{index:04}")));
            ids
        }
        _ => Vec::new(),
    }
}

fn census_error(label: &str, expected: &BTreeSet<String>, actual: &BTreeSet<String>) -> String {
    let missing = expected.difference(actual).cloned().collect::<Vec<_>>();
    let unknown = actual.difference(expected).cloned().collect::<Vec<_>>();
    format!("{label} census mismatch: missing={missing:?}, unknown={unknown:?}")
}

fn relative_path(root: &Path, path: &Path) -> Result<String, String> {
    path.strip_prefix(root)
        .map(|value| value.to_string_lossy().into_owned())
        .map_err(|_| format!("{} is outside {}", path.display(), root.display()))
}

fn unique_timestamp() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos()
}

fn sha256_bytes(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temporary_directory(label: &str) -> PathBuf {
        let path = std::env::temp_dir().join(format!(
            "wizard-avatar-production-alpha-finalizer-{label}-{}-{}",
            std::process::id(),
            unique_timestamp()
        ));
        fs::create_dir_all(&path).unwrap();
        path
    }

    fn entries_report(batch: usize) -> Vec<u8> {
        let ids = expected_batch_pose_ids(batch);
        serde_json::to_vec(&json!({
            "batch_id": format!("batch-{batch:02}"),
            "reviewer": "reviewer",
            "range": {
                "start": ids.first().unwrap(),
                "end": ids.last().unwrap()
            },
            "reviewed_count": ids.len(),
            "approved_count": ids.len(),
            "rejected_count": 0,
            "overall_status": "approved",
            "entries": ids.into_iter().map(|pose_id| json!({
                "pose_id": pose_id,
                "status": "approved",
                "visual_note": "literal comparison passed"
            })).collect::<Vec<_>>()
        }))
        .unwrap()
    }

    fn results_report(batch: usize) -> Vec<u8> {
        let ids = expected_batch_pose_ids(batch);
        let ranges = if batch == 7 {
            json!({"range": {
                "start": "WJPA-0193",
                "end": "WJPA-0224",
                "inclusive": true
            }})
        } else {
            json!({"ranges": [
                {"start": "WJPA-0225", "end": "WJPA-0250", "inclusive": true},
                {"start": "WJFF-0001", "end": "WJFF-0010", "inclusive": true}
            ]})
        };
        let mut value = json!({
            "schema_version": 1,
            "batch_id": format!("batch-{batch:02}"),
            "reviewer": "reviewer",
            "reviewed_count": ids.len(),
            "approved_count": ids.len(),
            "rejected_count": 0,
            "status": "approved",
            "results": ids.into_iter().map(|pose_id| json!({
                "id": pose_id,
                "decision": "approved",
                "notes": "literal comparison passed",
                "comparison_path": format!("evidence/pose-admission-v2/{pose_id}/comparison.png")
            })).collect::<Vec<_>>()
        });
        value
            .as_object_mut()
            .unwrap()
            .extend(ranges.as_object().unwrap().clone());
        serde_json::to_vec(&value).unwrap()
    }

    #[test]
    fn accepts_both_controlled_review_report_shapes() {
        let entries = parse_review_report(Path::new("batch-01.json"), &entries_report(1), 1)
            .expect("entries-v1 should parse");
        assert_eq!(entries.schema_variant, "entries-v1");
        assert_eq!(entries.reviews.len(), 32);

        let results = parse_review_report(Path::new("batch-08.json"), &results_report(8), 8)
            .expect("results-v1 should parse");
        assert_eq!(results.schema_variant, "results-v1");
        assert_eq!(results.reviews.len(), 36);
    }

    #[test]
    fn rejects_unknown_or_unsupported_review_schema() {
        let mut unknown: Value = serde_json::from_slice(&entries_report(1)).unwrap();
        unknown["unexpected"] = Value::Bool(true);
        assert!(parse_review_report(
            Path::new("batch-01.json"),
            &serde_json::to_vec(&unknown).unwrap(),
            1
        )
        .unwrap_err()
        .contains("invalid entries-v1"));

        let mut unsupported: Value = serde_json::from_slice(&results_report(7)).unwrap();
        unsupported["schema_version"] = Value::from(2);
        assert!(parse_review_report(
            Path::new("batch-07.json"),
            &serde_json::to_vec(&unsupported).unwrap(),
            7
        )
        .unwrap_err()
        .contains("unsupported review schema"));
    }

    #[test]
    fn exclusive_lock_rejects_concurrent_owner_and_cleans_up() {
        let root = temporary_directory("lock");
        let path = root.join("finalize.lock");
        let first = ExclusiveLock::acquire(&path).unwrap();
        assert!(ExclusiveLock::acquire(&path).is_err());
        drop(first);
        assert!(!path.exists());
        ExclusiveLock::acquire(&path).unwrap();
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn publish_failure_rolls_back_every_published_output() {
        let root = temporary_directory("rollback");
        let report_root = root.join("reports");
        fs::create_dir_all(&report_root).unwrap();
        let first = root.join("first.json");
        let second = root.join("second.json");
        fs::write(&first, b"old-first\n").unwrap();
        fs::write(&second, b"old-second\n").unwrap();
        let mut bindings = InputBindings::default();
        bindings.bind(&first, b"old-first\n").unwrap();
        bindings.bind(&second, b"old-second\n").unwrap();
        let outputs = vec![
            PlannedOutput {
                target: first.clone(),
                bytes: b"new-first\n".to_vec(),
            },
            PlannedOutput {
                target: second.clone(),
                bytes: b"new-second\n".to_vec(),
            },
        ];

        let error = stage_and_publish(&report_root, &bindings, &outputs, Some(1)).unwrap_err();
        assert!(error.contains("injected publish failure"));
        assert_eq!(fs::read(&first).unwrap(), b"old-first\n");
        assert_eq!(fs::read(&second).unwrap(), b"old-second\n");
        assert!(fs::read_dir(&report_root).unwrap().all(|entry| !entry
            .unwrap()
            .file_name()
            .to_string_lossy()
            .starts_with(".production-alpha-finalize-stage")));
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn publish_success_replaces_every_output_and_cleans_stage() {
        let root = temporary_directory("publish-success");
        let report_root = root.join("reports");
        fs::create_dir_all(&report_root).unwrap();
        let existing = root.join("existing.json");
        let created = root.join("created.json");
        fs::write(&existing, b"old\n").unwrap();
        let mut bindings = InputBindings::default();
        bindings.bind(&existing, b"old\n").unwrap();
        let outputs = vec![
            PlannedOutput {
                target: existing.clone(),
                bytes: b"new-existing\n".to_vec(),
            },
            PlannedOutput {
                target: created.clone(),
                bytes: b"new-created\n".to_vec(),
            },
        ];

        stage_and_publish(&report_root, &bindings, &outputs, None).unwrap();

        assert_eq!(fs::read(&existing).unwrap(), b"new-existing\n");
        assert_eq!(fs::read(&created).unwrap(), b"new-created\n");
        assert!(fs::read_dir(&report_root).unwrap().all(|entry| !entry
            .unwrap()
            .file_name()
            .to_string_lossy()
            .starts_with(".production-alpha-finalize-stage")));
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn changed_input_aborts_before_any_output_is_published() {
        let root = temporary_directory("input-change");
        let report_root = root.join("reports");
        fs::create_dir_all(&report_root).unwrap();
        let first = root.join("first.json");
        let second = root.join("second.json");
        fs::write(&first, b"old-first\n").unwrap();
        fs::write(&second, b"old-second\n").unwrap();
        let mut bindings = InputBindings::default();
        bindings.bind(&first, b"old-first\n").unwrap();
        bindings.bind(&second, b"old-second\n").unwrap();
        fs::write(&second, b"concurrent-change\n").unwrap();
        let outputs = vec![
            PlannedOutput {
                target: first.clone(),
                bytes: b"new-first\n".to_vec(),
            },
            PlannedOutput {
                target: second.clone(),
                bytes: b"new-second\n".to_vec(),
            },
        ];

        let error = stage_and_publish(&report_root, &bindings, &outputs, None).unwrap_err();

        assert!(error.contains("changed after preflight"));
        assert_eq!(fs::read(&first).unwrap(), b"old-first\n");
        assert_eq!(fs::read(&second).unwrap(), b"concurrent-change\n");
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    #[ignore = "requires the complete production-alpha corpus"]
    fn current_corpus_passes_complete_preflight() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .and_then(Path::parent)
            .unwrap();
        let plan = build_finalization_plan(root).expect("current corpus should pass preflight");
        assert_eq!(plan.outputs.len(), EXPECTED_POSE_COUNT + 3);
        assert_eq!(plan.receipt["status"], "approved");
    }
}
