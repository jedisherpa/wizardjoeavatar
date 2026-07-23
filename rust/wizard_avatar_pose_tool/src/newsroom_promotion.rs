use crate::{
    read_pixel_graph, EvidenceFile, NewsroomLayerAdmissionLedger, NewsroomLayerAdmissionStatus,
    NewsroomLayerVerificationReport, VisualReviewStatus, MINIMUM_FIDELITY,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::fs::{self, File};
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};

pub const NEWSROOM_PROMOTION_SCHEMA_VERSION: u32 = 1;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PromotedNewsroomTarget {
    pub id: String,
    pub semantic_layer: String,
    pub order: i32,
    pub anchor: [u32; 2],
    pub occlusion: String,
    pub foreground_pixel_count: u64,
    pub evidence_graph_path: String,
    pub evidence_graph_sha256: String,
    pub runtime_graph_path: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PromotedNewsroomScene {
    pub source_id: String,
    pub source_graph_sha256: String,
    pub source_target_spec_sha256: String,
    pub verification_report_path: String,
    pub verification_report_sha256: String,
    pub targets: Vec<PromotedNewsroomTarget>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomPromotionManifest {
    pub schema_version: u32,
    pub promotion_id: String,
    pub layer_admission_ledger_path: String,
    pub layer_admission_ledger_sha256: String,
    pub source_manifest_sha256: String,
    pub target_specs_sha256: String,
    pub minimum_visual_alignment: f64,
    pub runtime_raster_assets: bool,
    pub native_canvas: [u32; 2],
    pub source_count: usize,
    pub target_count: usize,
    pub foreground_pixel_count: u64,
    pub scenes: Vec<PromotedNewsroomScene>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewsroomPromotionReceipt {
    pub schema_version: u32,
    pub status: String,
    pub promotion_manifest_path: String,
    pub promotion_manifest_sha256: String,
    pub layer_admission_ledger_sha256: String,
    pub source_count: usize,
    pub target_count: usize,
    pub foreground_pixel_count: u64,
    pub policy: String,
}

#[derive(Debug, thiserror::Error)]
pub enum NewsroomPromotionError {
    #[error("I/O error at {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("JSON error at {path}: {source}")]
    Json {
        path: PathBuf,
        #[source]
        source: serde_json::Error,
    },
    #[error(transparent)]
    PixelGraph(#[from] crate::PixelGraphError),
    #[error("newsroom promotion invariant failed: {0}")]
    Invariant(String),
}

pub fn promote_verified_newsroom(
    repo_root: impl AsRef<Path>,
) -> Result<NewsroomPromotionManifest, NewsroomPromotionError> {
    let repo_root = repo_root.as_ref();
    let ledger_relative = "docs/newsroom-visual-development-v2/layer-admission-ledger.json";
    let ledger_path = repo_root.join(ledger_relative);
    let ledger: NewsroomLayerAdmissionLedger = read_json(&ledger_path)?;
    validate_complete_ledger(&ledger)?;
    let ledger_sha256 = sha256_file(&ledger_path)?;

    let output_root = repo_root.join("rust/wizard_avatar_engine/assets/newsroom/v2");
    let graph_root = output_root.join("graphs");
    fs::create_dir_all(&graph_root).map_err(|source| NewsroomPromotionError::Io {
        path: graph_root.clone(),
        source,
    })?;

    let mut scenes = Vec::with_capacity(ledger.entries.len());
    let mut expected_runtime_graphs = BTreeSet::new();
    let mut native_canvas = None;
    let mut foreground_pixel_count = 0_u64;

    for entry in &ledger.entries {
        let report_relative = entry.verification_report_path.as_deref().ok_or_else(|| {
            NewsroomPromotionError::Invariant(format!(
                "{} has no verification report",
                entry.source_id
            ))
        })?;
        let report_path = repo_root.join(report_relative);
        let report_sha256 = sha256_file(&report_path)?;
        let report: NewsroomLayerVerificationReport = read_json(&report_path)?;
        validate_report(entry, &report)?;
        verify_report_evidence(repo_root, &report)?;

        let frame = [report.frame.width, report.frame.height];
        if native_canvas
            .replace(frame)
            .is_some_and(|current| current != frame)
        {
            return Err(NewsroomPromotionError::Invariant(
                "approved source frames are not normalized to one native canvas".into(),
            ));
        }

        let mut targets = Vec::with_capacity(report.targets.len());
        for target in &report.targets {
            let evidence_path = repo_root.join(&target.pixel_graph.path);
            let graph = read_pixel_graph(&evidence_path)?;
            if graph.frame != report.frame
                || graph.foreground_pixel_count != target.foreground_pixel_count
                || graph.source_record_id != target.target_id
            {
                return Err(NewsroomPromotionError::Invariant(format!(
                    "{} graph metadata does not match its approved report",
                    target.target_id
                )));
            }

            let runtime_relative = format!(
                "rust/wizard_avatar_engine/assets/newsroom/v2/graphs/{}/{}.pixelgraph.json.gz",
                report.source_id, target.target_id
            );
            let runtime_path = repo_root.join(&runtime_relative);
            if let Some(parent) = runtime_path.parent() {
                fs::create_dir_all(parent).map_err(|source| NewsroomPromotionError::Io {
                    path: parent.to_path_buf(),
                    source,
                })?;
            }
            fs::copy(&evidence_path, &runtime_path).map_err(|source| {
                NewsroomPromotionError::Io {
                    path: runtime_path.clone(),
                    source,
                }
            })?;
            if sha256_file(&runtime_path)? != target.pixel_graph.sha256 {
                return Err(NewsroomPromotionError::Invariant(format!(
                    "runtime copy of {} is not byte-identical to approved evidence",
                    target.target_id
                )));
            }
            expected_runtime_graphs.insert(runtime_path);
            foreground_pixel_count += target.foreground_pixel_count;
            targets.push(PromotedNewsroomTarget {
                id: target.target_id.clone(),
                semantic_layer: target.semantic_layer.clone(),
                order: target.order,
                anchor: target.anchor,
                occlusion: target.occlusion.clone(),
                foreground_pixel_count: target.foreground_pixel_count,
                evidence_graph_path: target.pixel_graph.path.clone(),
                evidence_graph_sha256: target.pixel_graph.sha256.clone(),
                runtime_graph_path: runtime_relative,
            });
        }
        scenes.push(PromotedNewsroomScene {
            source_id: report.source_id,
            source_graph_sha256: report.source_graph_sha256,
            source_target_spec_sha256: report.source_target_spec_sha256,
            verification_report_path: report_relative.to_string(),
            verification_report_sha256: report_sha256,
            targets,
        });
    }
    reject_stale_runtime_graphs(&graph_root, &expected_runtime_graphs)?;

    let target_count = scenes.iter().map(|scene| scene.targets.len()).sum();
    let manifest = NewsroomPromotionManifest {
        schema_version: NEWSROOM_PROMOTION_SCHEMA_VERSION,
        promotion_id: "wizard_joe_newsroom_v2_native_pixelgraphs".into(),
        layer_admission_ledger_path: ledger_relative.into(),
        layer_admission_ledger_sha256: ledger_sha256.clone(),
        source_manifest_sha256: ledger.source_manifest_sha256,
        target_specs_sha256: ledger.target_specs_sha256,
        minimum_visual_alignment: MINIMUM_FIDELITY,
        runtime_raster_assets: false,
        native_canvas: native_canvas.ok_or_else(|| {
            NewsroomPromotionError::Invariant("promotion contains no approved sources".into())
        })?,
        source_count: scenes.len(),
        target_count,
        foreground_pixel_count,
        scenes,
    };
    let manifest_relative = "rust/wizard_avatar_engine/assets/newsroom/v2/promotion-manifest.json";
    let manifest_path = repo_root.join(manifest_relative);
    write_pretty_json(&manifest_path, &manifest)?;
    let manifest_sha256 = sha256_file(&manifest_path)?;

    let receipt = NewsroomPromotionReceipt {
        schema_version: NEWSROOM_PROMOTION_SCHEMA_VERSION,
        status: "promoted_from_visually_verified_native_graphs".into(),
        promotion_manifest_path: manifest_relative.into(),
        promotion_manifest_sha256: manifest_sha256,
        layer_admission_ledger_sha256: ledger_sha256,
        source_count: manifest.source_count,
        target_count: manifest.target_count,
        foreground_pixel_count: manifest.foreground_pixel_count,
        policy: "Runtime assets are byte-identical copies of approved transparent pixel graphs. No PNG, SVG, resampling, cropping, procedural reconstruction, or camera-board artwork is promoted.".into(),
    };
    write_pretty_json(
        &repo_root.join("docs/newsroom-visual-development-v2/runtime-promotion.json"),
        &receipt,
    )?;
    Ok(manifest)
}

fn validate_complete_ledger(
    ledger: &NewsroomLayerAdmissionLedger,
) -> Result<(), NewsroomPromotionError> {
    if ledger.schema_version != 1
        || ledger.ledger_id != "wizard_joe_newsroom_v2_layer_admission"
        || ledger.expected_source_count != 6
        || ledger.verified_source_count != ledger.expected_source_count
        || ledger.awaiting_visual_comparison_count != 0
        || ledger.failed_source_count != 0
        || ledger.queued_source_count != 0
        || ledger.entries.len() != ledger.expected_source_count
        || ledger
            .entries
            .iter()
            .any(|entry| entry.status != NewsroomLayerAdmissionStatus::VisuallyVerified)
    {
        return Err(NewsroomPromotionError::Invariant(
            "layer ledger is not a complete six-source visual approval".into(),
        ));
    }
    Ok(())
}

fn validate_report(
    entry: &crate::NewsroomLayerAdmissionEntry,
    report: &NewsroomLayerVerificationReport,
) -> Result<(), NewsroomPromotionError> {
    if report.schema_version != 1
        || report.source_id != entry.source_id
        || report.source_graph_sha256 != entry.source_graph_sha256
        || report.source_target_spec_sha256 != entry.source_target_spec_sha256
        || !report.passed
        || !report.recomposition_exact
        || report.visual_review.status != VisualReviewStatus::Approved
        || report.visual_review.reviewer.trim().is_empty()
        || report.visual_review.finding.trim().is_empty()
        || report.overlap_pixels != 0
        || report.unassigned_pixels != 0
        || report.assigned_source_pixels != report.source_foreground_pixels
        || report.recomposition_metrics.silhouette_iou < MINIMUM_FIDELITY
        || report.recomposition_metrics.foreground_color_fidelity < MINIMUM_FIDELITY
        || report.targets.is_empty()
    {
        return Err(NewsroomPromotionError::Invariant(format!(
            "{} does not satisfy the visual promotion gate",
            entry.source_id
        )));
    }
    Ok(())
}

fn verify_report_evidence(
    repo_root: &Path,
    report: &NewsroomLayerVerificationReport,
) -> Result<(), NewsroomPromotionError> {
    for target in &report.targets {
        verify_evidence(repo_root, &target.pixel_graph)?;
        verify_evidence(repo_root, &target.graph_render)?;
    }
    for evidence in [
        &report.layer_map,
        &report.recomposed_render,
        &report.transparent_overlay,
        &report.recomposed_over_source_png,
    ] {
        verify_evidence(repo_root, evidence)?;
    }
    Ok(())
}

fn verify_evidence(
    repo_root: &Path,
    evidence: &EvidenceFile,
) -> Result<(), NewsroomPromotionError> {
    let actual = sha256_file(&repo_root.join(&evidence.path))?;
    if actual != evidence.sha256 {
        return Err(NewsroomPromotionError::Invariant(format!(
            "evidence hash drifted at {}",
            evidence.path
        )));
    }
    Ok(())
}

fn reject_stale_runtime_graphs(
    graph_root: &Path,
    expected: &BTreeSet<PathBuf>,
) -> Result<(), NewsroomPromotionError> {
    let mut pending = vec![graph_root.to_path_buf()];
    while let Some(directory) = pending.pop() {
        for entry in fs::read_dir(&directory).map_err(|source| NewsroomPromotionError::Io {
            path: directory.clone(),
            source,
        })? {
            let path = entry
                .map_err(|source| NewsroomPromotionError::Io {
                    path: directory.clone(),
                    source,
                })?
                .path();
            if path.is_dir() {
                pending.push(path);
            } else if path.extension().is_some_and(|extension| extension == "gz")
                && !expected.contains(&path)
            {
                return Err(NewsroomPromotionError::Invariant(format!(
                    "stale unapproved runtime graph exists at {}",
                    path.display()
                )));
            }
        }
    }
    Ok(())
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, NewsroomPromotionError> {
    let file = File::open(path).map_err(|source| NewsroomPromotionError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    serde_json::from_reader(BufReader::new(file)).map_err(|source| NewsroomPromotionError::Json {
        path: path.to_path_buf(),
        source,
    })
}

fn write_pretty_json<T: Serialize>(path: &Path, value: &T) -> Result<(), NewsroomPromotionError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|source| NewsroomPromotionError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    let bytes =
        serde_json::to_vec_pretty(value).map_err(|source| NewsroomPromotionError::Json {
            path: path.to_path_buf(),
            source,
        })?;
    fs::write(path, bytes).map_err(|source| NewsroomPromotionError::Io {
        path: path.to_path_buf(),
        source,
    })
}

fn sha256_file(path: &Path) -> Result<String, NewsroomPromotionError> {
    let file = File::open(path).map_err(|source| NewsroomPromotionError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let mut reader = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = reader
            .read(&mut buffer)
            .map_err(|source| NewsroomPromotionError::Io {
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
