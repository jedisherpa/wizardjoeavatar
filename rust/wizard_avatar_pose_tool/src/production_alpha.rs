use crate::{
    build_exact_pixel_graph, build_transparent_overlay, composite_graph_over_source,
    normalize_to_frame, project_pixel_graph, read_pixel_graph, verify_pose_graph,
    write_pixel_graph, FrameSpec, OverlayCounts, OverlayPalette, PixelGraphError, PoseGraphMetrics,
    VerificationConfig, VerificationError,
};
use image::{codecs::png::PngDecoder, ColorType, ImageDecoder, ImageFormat, Rgba, RgbaImage};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File};
use std::io::{BufReader, Cursor, Read, Write};
use std::path::{Path, PathBuf};
use zip::ZipArchive;

pub const PRODUCTION_ALPHA_SCHEMA_VERSION: u32 = 2;
pub const PRODUCTION_ALPHA_COMPILER_ID: &str = "wizard-avatar-production-alpha-v1";
pub const BASE_ARCHIVE_SHA256: &str =
    "dc367a89f5f592dad1db8d0d16dcf12ff5600659e4ee2f87b32b25e8227f4b80";
pub const FLIGHT_ARCHIVE_SHA256: &str =
    "7d2a7d7390d1fb95147bf834cc45849dbfee50a9f42ba05abe99c50e37cf9e49";
pub const DEFAULT_BASE_ARCHIVE: &str =
    "/Users/paul/Downloads/Wizard_Joe_Production_Alpha_Set_001_250_v001.zip";
pub const DEFAULT_FLIGHT_ARCHIVE: &str =
    "/Users/paul/Downloads/Wizard_Joe_Forward_Camera_Flight_Alpha_Cycle_v001 (1).zip";

const BASE_MANIFEST_MEMBER: &str =
    "Wizard_Joe_Production_Alpha_Set_001_250_v001/manifests/alpha_asset_manifest_v001.json";
const BASE_ALPHA_PREFIX: &str = "Wizard_Joe_Production_Alpha_Set_001_250_v001/alphas_srgb_v001/";
const FLIGHT_MANIFEST_MEMBER: &str =
    "Wizard_Joe_Forward_Camera_Flight_Alpha_Cycle_v001/flight_cycle_manifest_v001.json";
const FLIGHT_ALPHA_PREFIX: &str = "Wizard_Joe_Forward_Camera_Flight_Alpha_Cycle_v001/alphas/";
const FRAME: FrameSpec = FrameSpec {
    width: 1254,
    height: 1254,
};
const REQUIRED_SAFE_MARGIN: u32 = 69;

#[derive(Clone, Debug)]
pub struct ProductionAlphaConfig {
    pub base_archive: PathBuf,
    pub flight_archive: PathBuf,
    pub output_root: PathBuf,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProductionAlphaReceipt {
    pub schema_version: u32,
    pub compiler_id: String,
    pub source_count: usize,
    pub exact_rgba_verified_count: usize,
    pub graph_count: usize,
    pub runtime_manifest_path: String,
    pub source_ledger_path: String,
    pub admission_ledger_path: String,
    pub summary_path: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeManifestV2 {
    pub schema_version: u32,
    pub compiler_id: String,
    pub frame: [u32; 2],
    pub source_count: usize,
    pub base_pose_count: usize,
    pub forward_flight_count: usize,
    pub verified_pose_count: usize,
    pub primary_pose_count: usize,
    pub unique_semantic_pose_count: usize,
    pub archives: Vec<ArchiveProvenance>,
    pub entries: Vec<RuntimeAlphaEntry>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ArchiveProvenance {
    pub source_pack: String,
    pub archive_filename: String,
    pub archive_sha256: String,
    pub manifest_member: String,
    pub manifest_status: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeAlphaEntry {
    pub sequence: usize,
    pub source_record_id: String,
    pub candidate_id: String,
    pub pose_id: String,
    pub semantic_id: String,
    pub display_name: String,
    pub source_archive: String,
    pub source_entry: String,
    pub source_sha256: String,
    pub graph_path: String,
    pub graph_sha256: String,
    pub graph_id: String,
    pub frame: [u32; 2],
    pub source_size: [u32; 2],
    pub offset: [u32; 2],
    pub foreground_pixel_count: u64,
    pub motion_family: String,
    pub contact_mode: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub phase: Option<RuntimePhase>,
    pub direction: String,
    pub authored_transition_neighbors: Vec<String>,
    pub control_groups: Vec<String>,
    pub primary_for_semantic_id: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub duplicate_source_of: Option<String>,
    pub silhouette_iou_millionths: u32,
    pub foreground_color_fidelity_millionths: u32,
    pub foreground_color_match_ratio_millionths: u32,
    pub exact_rgba_equal: bool,
    pub rgba_mismatch_pixel_count: u64,
    pub rgba_mismatch_channel_count: u64,
    pub source_pack: String,
    pub category: String,
    pub anchor_kind: String,
    pub anchor_x: u32,
    pub anchor_y: u32,
    pub evidence_path: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimePhase {
    pub numerator: u16,
    pub denominator: u16,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MotionMetadata {
    pub family: String,
    pub phase: String,
    pub direction: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub loop_group: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub playback_fps: Option<u32>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceLedgerV2 {
    pub schema_version: u32,
    pub compiler_id: String,
    pub expected_source_count: usize,
    pub archives: Vec<ArchiveProvenance>,
    pub entries: Vec<SourceLedgerEntry>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceLedgerEntry {
    pub sequence: usize,
    pub pose_id: String,
    pub semantic_id: String,
    pub source_pack: String,
    pub archive_sha256: String,
    pub source_member: String,
    pub source_png_sha256: String,
    pub manifest_status: String,
    pub category: String,
    pub motion: MotionMetadata,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AdmissionLedgerV2 {
    pub schema_version: u32,
    pub compiler_id: String,
    pub expected_pose_count: usize,
    pub exact_rgba_verified_count: usize,
    pub visual_review_pending_count: usize,
    pub failed_count: usize,
    pub entries: Vec<AdmissionLedgerEntry>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AdmissionLedgerEntry {
    pub sequence: usize,
    pub pose_id: String,
    pub technical_status: String,
    pub visual_review_status: String,
    pub source_png_sha256: String,
    pub graph_sha256: String,
    pub graph_path: String,
    pub evidence_path: String,
    pub verification_report_path: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProductionAlphaVerification {
    pub schema_version: u32,
    pub compiler_id: String,
    pub sequence: usize,
    pub pose_id: String,
    pub semantic_id: String,
    pub source_pack: String,
    pub source_archive_sha256: String,
    pub source_member: String,
    pub source_png_sha256: String,
    pub frame: FrameSpec,
    pub foreground_bounds: AlphaBounds,
    pub safe_margin_px: u32,
    pub transparent_corners: bool,
    pub foreground_pixel_count: u64,
    pub exact_rgba_equal: bool,
    pub rgba_mismatch: RgbaMismatch,
    pub metrics: PoseGraphMetrics,
    pub overlay_counts: OverlayCounts,
    pub graph_path: String,
    pub graph_sha256: String,
    pub artifacts: EvidenceArtifacts,
    pub technical_status: String,
    pub visual_review_status: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AlphaBounds {
    pub x: u32,
    pub y: u32,
    pub width: u32,
    pub height: u32,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RgbaMismatch {
    pub pixel_count: u64,
    pub channel_count: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub first_x: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub first_y: Option<u32>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EvidenceArtifacts {
    pub source_png: EvidenceArtifact,
    pub projected_png: EvidenceArtifact,
    pub transparent_overlay_png: EvidenceArtifact,
    pub composite_png: EvidenceArtifact,
    pub comparison_png: EvidenceArtifact,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EvidenceArtifact {
    pub path: String,
    pub sha256: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProductionAlphaSummary {
    pub schema_version: u32,
    pub compiler_id: String,
    pub source_count: usize,
    pub base_pose_count: usize,
    pub forward_flight_count: usize,
    pub exact_rgba_verified_count: usize,
    pub graph_count: usize,
    pub visual_review_pending_count: usize,
    pub failed_count: usize,
    pub frame: FrameSpec,
    pub policy: String,
}

#[derive(Debug, thiserror::Error)]
pub enum ProductionAlphaError {
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
    #[error("JSON error in {source_name}: {source}")]
    Json {
        source_name: String,
        #[source]
        source: serde_json::Error,
    },
    #[error("PNG decode error for {pose_id}: {source}")]
    Image {
        pose_id: String,
        #[source]
        source: image::ImageError,
    },
    #[error(transparent)]
    PixelGraph(#[from] PixelGraphError),
    #[error(transparent)]
    Verification(#[from] VerificationError),
    #[error(
        "exact RGBA mismatch for {pose_id}: {pixel_count} pixels and {channel_count} channels differ"
    )]
    ExactRgbaMismatch {
        pose_id: String,
        pixel_count: u64,
        channel_count: u64,
    },
    #[error("production alpha invariant failed: {0}")]
    Invariant(String),
}

#[derive(Clone, Debug)]
struct SourceAsset {
    sequence: usize,
    pose_id: String,
    semantic_id: String,
    source_pack: String,
    archive_sha256: String,
    source_member: String,
    source_png_sha256: String,
    manifest_status: String,
    expected_bounds: AlphaBounds,
    safe_margin_px: u32,
    category: String,
    motion: MotionMetadata,
}

#[derive(Clone, Debug)]
struct ProcessedAsset {
    runtime: RuntimeAlphaEntry,
    source: SourceLedgerEntry,
    admission: AdmissionLedgerEntry,
}

#[derive(Clone, Debug, Deserialize)]
struct ManifestCanvas {
    width: u32,
    height: u32,
    color_space: String,
    alpha: bool,
    #[serde(default)]
    safe_margin_px: Option<u32>,
}

#[derive(Clone, Debug, Deserialize)]
struct ManifestDimensions {
    width: u32,
    height: u32,
}

#[derive(Clone, Debug, Deserialize)]
struct ManifestBounds {
    x: u32,
    y: u32,
    width: u32,
    height: u32,
}

impl From<ManifestBounds> for AlphaBounds {
    fn from(value: ManifestBounds) -> Self {
        Self {
            x: value.x,
            y: value.y,
            width: value.width,
            height: value.height,
        }
    }
}

#[derive(Clone, Debug, Deserialize)]
struct BaseQaCounts {
    expected: usize,
    present: usize,
    pass: usize,
    fail: usize,
    unique_hashes: usize,
}

#[derive(Clone, Debug, Deserialize)]
struct BaseQaSummary {
    verdict: String,
    counts: BaseQaCounts,
    missing_ids: Vec<String>,
    duplicate_ids: Vec<String>,
}

#[derive(Clone, Debug, Deserialize)]
struct BaseManifest {
    pack_id: String,
    version: String,
    status: String,
    canvas: ManifestCanvas,
    qa_summary: BaseQaSummary,
    assets: Vec<BaseManifestAsset>,
}

#[derive(Clone, Debug, Deserialize)]
struct BaseManifestAsset {
    asset_id: String,
    filename: String,
    status: String,
    output_sha256: String,
    dimensions: ManifestDimensions,
    color_space: String,
    alpha: bool,
    normalized_bbox: ManifestBounds,
    minimum_margin_px: u32,
    qa_status: String,
    qa_failures: Vec<String>,
}

#[derive(Clone, Debug, Deserialize)]
struct FlightNormalization {
    safe_margin_px: u32,
}

#[derive(Clone, Debug, Deserialize)]
struct FlightPlayback {
    fps: u32,
    order: Vec<String>,
    loop_transition: String,
}

#[derive(Clone, Debug, Deserialize)]
struct FlightManifest {
    pack_id: String,
    version: String,
    status: String,
    frame_count: usize,
    canvas: ManifestCanvas,
    normalization: FlightNormalization,
    playback: FlightPlayback,
    assets: Vec<FlightManifestAsset>,
}

#[derive(Clone, Debug, Deserialize)]
struct FlightManifestAsset {
    frame: usize,
    filename: String,
    dimensions: ManifestDimensions,
    color_space: String,
    alpha: bool,
    output_sha256: String,
    normalized_bbox: ManifestBounds,
    qa_status: String,
}

pub fn compile_production_alpha(
    config: &ProductionAlphaConfig,
) -> Result<ProductionAlphaReceipt, ProductionAlphaError> {
    let base_archive_sha256 = verify_archive_hash(&config.base_archive, BASE_ARCHIVE_SHA256)?;
    let flight_archive_sha256 = verify_archive_hash(&config.flight_archive, FLIGHT_ARCHIVE_SHA256)?;

    let mut base_zip = open_zip(&config.base_archive)?;
    let base_names = zip_member_counts(&mut base_zip, &config.base_archive)?;
    let base_manifest: BaseManifest = read_zip_json(
        &mut base_zip,
        &config.base_archive,
        &base_names,
        BASE_MANIFEST_MEMBER,
    )?;
    let base_assets = validate_base_manifest(&base_manifest, &base_names, &base_archive_sha256)?;

    let mut flight_zip = open_zip(&config.flight_archive)?;
    let flight_names = zip_member_counts(&mut flight_zip, &config.flight_archive)?;
    let flight_manifest: FlightManifest = read_zip_json(
        &mut flight_zip,
        &config.flight_archive,
        &flight_names,
        FLIGHT_MANIFEST_MEMBER,
    )?;
    let flight_assets =
        validate_flight_manifest(&flight_manifest, &flight_names, &flight_archive_sha256)?;
    validate_global_uniqueness(&base_assets, &flight_assets)?;

    let archives = vec![
        ArchiveProvenance {
            source_pack: base_manifest.pack_id.clone(),
            archive_filename: archive_filename(&config.base_archive)?,
            archive_sha256: base_archive_sha256,
            manifest_member: BASE_MANIFEST_MEMBER.to_string(),
            manifest_status: base_manifest.status.clone(),
        },
        ArchiveProvenance {
            source_pack: flight_manifest.pack_id.clone(),
            archive_filename: archive_filename(&config.flight_archive)?,
            archive_sha256: flight_archive_sha256,
            manifest_member: FLIGHT_MANIFEST_MEMBER.to_string(),
            manifest_status: flight_manifest.status.clone(),
        },
    ];

    fs::create_dir_all(&config.output_root).map_err(|source| ProductionAlphaError::Io {
        path: config.output_root.clone(),
        source,
    })?;
    write_incomplete_marker(&config.output_root)?;

    let mut processed = Vec::with_capacity(260);
    for asset in &base_assets {
        processed.push(process_one_asset(
            &config.output_root,
            &config.base_archive,
            &mut base_zip,
            &base_names,
            asset,
        )?);
    }
    for asset in &flight_assets {
        processed.push(process_one_asset(
            &config.output_root,
            &config.flight_archive,
            &mut flight_zip,
            &flight_names,
            asset,
        )?);
    }
    populate_transition_neighbors(&mut processed);
    if processed.len() != 260 {
        return Err(ProductionAlphaError::Invariant(format!(
            "compiler processed {} assets instead of 260",
            processed.len()
        )));
    }

    let runtime_manifest = RuntimeManifestV2 {
        schema_version: PRODUCTION_ALPHA_SCHEMA_VERSION,
        compiler_id: PRODUCTION_ALPHA_COMPILER_ID.to_string(),
        frame: [FRAME.width, FRAME.height],
        source_count: processed.len(),
        base_pose_count: base_assets.len(),
        forward_flight_count: flight_assets.len(),
        verified_pose_count: processed.len(),
        primary_pose_count: processed.len(),
        unique_semantic_pose_count: processed.len(),
        archives: archives.clone(),
        entries: processed.iter().map(|item| item.runtime.clone()).collect(),
    };
    let source_ledger = SourceLedgerV2 {
        schema_version: PRODUCTION_ALPHA_SCHEMA_VERSION,
        compiler_id: PRODUCTION_ALPHA_COMPILER_ID.to_string(),
        expected_source_count: processed.len(),
        archives,
        entries: processed.iter().map(|item| item.source.clone()).collect(),
    };
    let admission_ledger = AdmissionLedgerV2 {
        schema_version: PRODUCTION_ALPHA_SCHEMA_VERSION,
        compiler_id: PRODUCTION_ALPHA_COMPILER_ID.to_string(),
        expected_pose_count: processed.len(),
        exact_rgba_verified_count: processed.len(),
        visual_review_pending_count: processed.len(),
        failed_count: 0,
        entries: processed
            .iter()
            .map(|item| item.admission.clone())
            .collect(),
    };
    let summary = ProductionAlphaSummary {
        schema_version: PRODUCTION_ALPHA_SCHEMA_VERSION,
        compiler_id: PRODUCTION_ALPHA_COMPILER_ID.to_string(),
        source_count: processed.len(),
        base_pose_count: base_assets.len(),
        forward_flight_count: flight_assets.len(),
        exact_rgba_verified_count: processed.len(),
        graph_count: processed.len(),
        visual_review_pending_count: processed.len(),
        failed_count: 0,
        frame: FRAME,
        policy: "Every source PNG is hash-verified from its pinned ZIP, decoded as RGBA8 at 1254x1254, checked against its declared safe bounds, converted sequentially into a native colored-run PixelGraph, serialized, read back, projected, and required to match every RGBA byte including alpha. PNG evidence is never a runtime dependency.".to_string(),
    };

    let runtime_manifest_path = config.output_root.join("runtime-manifest.json");
    let source_ledger_path = config
        .output_root
        .join("wizard-joe-alpha-source-ledger.json");
    let admission_ledger_path = config
        .output_root
        .join("wizard-joe-alpha-admission-ledger.json");
    let summary_path = config.output_root.join("summary.json");
    write_json(&runtime_manifest_path, &runtime_manifest)?;
    write_json(&source_ledger_path, &source_ledger)?;
    write_json(&admission_ledger_path, &admission_ledger)?;
    write_json(&summary_path, &summary)?;
    remove_incomplete_marker(&config.output_root)?;

    Ok(ProductionAlphaReceipt {
        schema_version: PRODUCTION_ALPHA_SCHEMA_VERSION,
        compiler_id: PRODUCTION_ALPHA_COMPILER_ID.to_string(),
        source_count: processed.len(),
        exact_rgba_verified_count: processed.len(),
        graph_count: processed.len(),
        runtime_manifest_path: relative_path(&config.output_root, &runtime_manifest_path)?,
        source_ledger_path: relative_path(&config.output_root, &source_ledger_path)?,
        admission_ledger_path: relative_path(&config.output_root, &admission_ledger_path)?,
        summary_path: relative_path(&config.output_root, &summary_path)?,
    })
}

fn validate_base_manifest(
    manifest: &BaseManifest,
    member_counts: &BTreeMap<String, usize>,
    archive_sha256: &str,
) -> Result<Vec<SourceAsset>, ProductionAlphaError> {
    require(
        manifest.pack_id == "wizard_joe_base_250_alpha",
        "unexpected Base-250 pack_id",
    )?;
    require(manifest.version == "v001", "unexpected Base-250 version")?;
    require(
        manifest.status == "approved_production_alpha_set",
        "Base-250 manifest is not approved",
    )?;
    validate_canvas(&manifest.canvas, Some(REQUIRED_SAFE_MARGIN))?;
    require(
        manifest.qa_summary.verdict == "technical_alpha_qa_pass",
        "Base-250 QA verdict is not a pass",
    )?;
    let counts = &manifest.qa_summary.counts;
    require(
        (
            counts.expected,
            counts.present,
            counts.pass,
            counts.fail,
            counts.unique_hashes,
        ) == (250, 250, 250, 0, 250),
        "Base-250 QA counts are not 250/250/250/0/250",
    )?;
    require(
        manifest.qa_summary.missing_ids.is_empty() && manifest.qa_summary.duplicate_ids.is_empty(),
        "Base-250 QA reports missing or duplicate IDs",
    )?;
    require(
        manifest.assets.len() == 250,
        "Base-250 manifest must contain 250 assets",
    )?;

    let mut assets = manifest.assets.clone();
    assets.sort_by_key(|asset| asset.asset_id.parse::<usize>().unwrap_or(usize::MAX));
    let mut sources = Vec::with_capacity(250);
    let mut expected_members = BTreeSet::new();
    let mut hashes = BTreeSet::new();
    for (index, asset) in assets.into_iter().enumerate() {
        let ordinal = index + 1;
        require(
            asset.asset_id == format!("{ordinal:03}"),
            format!(
                "Base-250 asset {} is out of canonical order",
                asset.asset_id
            ),
        )?;
        require(
            asset.filename.starts_with(&format!("{ordinal:03}_"))
                && asset.filename.ends_with(".png"),
            format!("Base-250 filename {} does not match its ID", asset.filename),
        )?;
        require(
            asset.status == "approved_production_alpha"
                && asset.qa_status == "pass"
                && asset.qa_failures.is_empty(),
            format!("Base-250 asset {} did not pass manifest QA", asset.asset_id),
        )?;
        validate_asset_contract(
            &asset.dimensions,
            &asset.color_space,
            asset.alpha,
            asset.minimum_margin_px,
        )?;
        require_sha256(&asset.output_sha256, "Base-250 output_sha256")?;
        require(
            hashes.insert(asset.output_sha256.clone()),
            format!("duplicate Base-250 output hash for {}", asset.filename),
        )?;
        let source_member = format!("{BASE_ALPHA_PREFIX}{}", asset.filename);
        require_single_member(member_counts, &source_member)?;
        expected_members.insert(source_member.clone());
        let semantic_id = base_semantic_id_from_filename(&asset.filename)?;
        let category = infer_category(&semantic_id, false).to_string();
        let motion = infer_motion(&semantic_id, false);
        sources.push(SourceAsset {
            sequence: ordinal,
            pose_id: format!("WJPA-{ordinal:04}"),
            semantic_id,
            source_pack: manifest.pack_id.clone(),
            archive_sha256: archive_sha256.to_string(),
            source_member,
            source_png_sha256: asset.output_sha256,
            manifest_status: asset.qa_status,
            expected_bounds: asset.normalized_bbox.into(),
            safe_margin_px: REQUIRED_SAFE_MARGIN,
            category,
            motion,
        });
    }
    validate_exact_alpha_member_set(member_counts, BASE_ALPHA_PREFIX, &expected_members)?;
    Ok(sources)
}

fn validate_flight_manifest(
    manifest: &FlightManifest,
    member_counts: &BTreeMap<String, usize>,
    archive_sha256: &str,
) -> Result<Vec<SourceAsset>, ProductionAlphaError> {
    require(
        manifest.pack_id == "wizard_joe_forward_camera_flight_cycle",
        "unexpected WJFF pack_id",
    )?;
    require(manifest.version == "v001", "unexpected WJFF version")?;
    require(
        manifest.status == "candidate_review",
        "unexpected WJFF manifest status",
    )?;
    require(manifest.frame_count == 10, "WJFF frame_count is not 10")?;
    validate_canvas(&manifest.canvas, None)?;
    require(
        manifest.normalization.safe_margin_px == REQUIRED_SAFE_MARGIN,
        "WJFF safe margin is not 69",
    )?;
    require(manifest.playback.fps == 10, "WJFF playback is not 10 fps")?;
    require(
        manifest.playback.order.len() == 10,
        "WJFF playback order must contain 10 frames",
    )?;
    require(
        manifest.playback.loop_transition == "WJFF_010_loop_close.png -> WJFF_001_top_recovery.png",
        "WJFF loop transition is unexpected",
    )?;
    require(
        manifest.assets.len() == 10,
        "WJFF manifest must contain 10 assets",
    )?;

    let mut assets = manifest.assets.clone();
    assets.sort_by_key(|asset| asset.frame);
    let mut sources = Vec::with_capacity(10);
    let mut expected_members = BTreeSet::new();
    let mut hashes = BTreeSet::new();
    for (index, asset) in assets.into_iter().enumerate() {
        let frame = index + 1;
        require(
            asset.frame == frame,
            format!("WJFF frame {} is out of canonical order", asset.frame),
        )?;
        require(
            asset.filename.starts_with(&format!("WJFF_{frame:03}_"))
                && asset.filename.ends_with(".png"),
            format!("WJFF filename {} does not match its frame", asset.filename),
        )?;
        require(
            manifest.playback.order[index] == asset.filename,
            format!("WJFF playback order disagrees at frame {frame}"),
        )?;
        require(
            asset.qa_status == "candidate_review",
            format!("WJFF frame {frame} has unexpected QA status"),
        )?;
        validate_asset_contract(
            &asset.dimensions,
            &asset.color_space,
            asset.alpha,
            REQUIRED_SAFE_MARGIN,
        )?;
        require_sha256(&asset.output_sha256, "WJFF output_sha256")?;
        require(
            hashes.insert(asset.output_sha256.clone()),
            format!("duplicate WJFF output hash for {}", asset.filename),
        )?;
        let source_member = format!("{FLIGHT_ALPHA_PREFIX}{}", asset.filename);
        require_single_member(member_counts, &source_member)?;
        expected_members.insert(source_member.clone());
        let semantic_id = flight_semantic_id_from_filename(&asset.filename)?;
        sources.push(SourceAsset {
            sequence: 250 + frame,
            pose_id: format!("WJFF-{frame:04}"),
            semantic_id: semantic_id.clone(),
            source_pack: manifest.pack_id.clone(),
            archive_sha256: archive_sha256.to_string(),
            source_member,
            source_png_sha256: asset.output_sha256,
            manifest_status: asset.qa_status,
            expected_bounds: asset.normalized_bbox.into(),
            safe_margin_px: REQUIRED_SAFE_MARGIN,
            category: infer_category(&semantic_id, true).to_string(),
            motion: infer_motion(&semantic_id, true),
        });
    }
    validate_exact_alpha_member_set(member_counts, FLIGHT_ALPHA_PREFIX, &expected_members)?;
    Ok(sources)
}

fn validate_global_uniqueness(
    base_assets: &[SourceAsset],
    flight_assets: &[SourceAsset],
) -> Result<(), ProductionAlphaError> {
    let mut pose_ids = BTreeSet::new();
    let mut semantic_ids = BTreeSet::new();
    let mut source_hashes = BTreeSet::new();
    for asset in base_assets.iter().chain(flight_assets) {
        require(
            pose_ids.insert(asset.pose_id.clone()),
            format!("duplicate primary pose ID {}", asset.pose_id),
        )?;
        require(
            semantic_ids.insert(asset.semantic_id.clone()),
            format!("duplicate semantic ID {}", asset.semantic_id),
        )?;
        require(
            source_hashes.insert(asset.source_png_sha256.clone()),
            format!("duplicate source PNG hash for {}", asset.pose_id),
        )?;
    }
    require(
        pose_ids.len() == 260 && semantic_ids.len() == 260 && source_hashes.len() == 260,
        "the replacement set is not 260 primary, semantically unique, source-unique poses",
    )
}

fn populate_transition_neighbors(processed: &mut [ProcessedAsset]) {
    let identities = processed
        .iter()
        .map(|item| {
            (
                item.runtime.source_pack.clone(),
                item.runtime.category.clone(),
                item.runtime.semantic_id.clone(),
            )
        })
        .collect::<Vec<_>>();
    for index in 0..processed.len() {
        let (source_pack, category, _) = &identities[index];
        let mut neighbors = Vec::new();
        if source_pack == "wizard_joe_forward_camera_flight_cycle" {
            let flight_indices = identities
                .iter()
                .enumerate()
                .filter(|(_, (pack, _, _))| pack == source_pack)
                .map(|(index, _)| index)
                .collect::<Vec<_>>();
            if let Some(position) = flight_indices
                .iter()
                .position(|candidate| *candidate == index)
            {
                let previous =
                    flight_indices[(position + flight_indices.len() - 1) % flight_indices.len()];
                let next = flight_indices[(position + 1) % flight_indices.len()];
                neighbors.push(identities[previous].2.clone());
                neighbors.push(identities[next].2.clone());
            }
        } else {
            if index > 0
                && identities[index - 1].0 == *source_pack
                && identities[index - 1].1 == *category
            {
                neighbors.push(identities[index - 1].2.clone());
            }
            if index + 1 < identities.len()
                && identities[index + 1].0 == *source_pack
                && identities[index + 1].1 == *category
            {
                neighbors.push(identities[index + 1].2.clone());
            }
        }
        neighbors.dedup();
        processed[index].runtime.authored_transition_neighbors = neighbors;
    }
}

fn process_one_asset(
    output_root: &Path,
    archive_path: &Path,
    archive: &mut ZipArchive<File>,
    member_counts: &BTreeMap<String, usize>,
    asset: &SourceAsset,
) -> Result<ProcessedAsset, ProductionAlphaError> {
    let png_bytes = read_zip_member(archive, archive_path, member_counts, &asset.source_member)?;
    let actual_png_sha256 = sha256_bytes(&png_bytes);
    require(
        actual_png_sha256 == asset.source_png_sha256,
        format!(
            "{} member hash {} does not match manifest {}",
            asset.pose_id, actual_png_sha256, asset.source_png_sha256
        ),
    )?;
    let source = decode_required_rgba_png(&asset.pose_id, &png_bytes)?;
    let bounds = validate_source_image(asset, &source)?;
    let normalized = normalize_to_frame(&source, FRAME)?;
    require(
        normalized.offset_x == 0 && normalized.offset_y == 0,
        format!("{} was unexpectedly padded or translated", asset.pose_id),
    )?;

    let graph = build_exact_pixel_graph(
        format!("{}-pixelgraph-v1", asset.pose_id.to_ascii_lowercase()),
        &asset.pose_id,
        &asset.source_png_sha256,
        source.dimensions(),
        &normalized,
    );
    let graph_path = output_root
        .join("graphs")
        .join(format!("{}.pixelgraph.json.gz", asset.pose_id));
    let graph_sha256 = write_pixel_graph(&graph, &graph_path)?;
    let serialized_graph = read_pixel_graph(&graph_path)?;
    require(
        serialized_graph == graph,
        format!("{} graph did not serialize losslessly", asset.pose_id),
    )?;
    let projected = project_pixel_graph(&serialized_graph)?;
    let rgba_mismatch = require_exact_rgba_match(&asset.pose_id, &source, &projected)?;

    let verification = VerificationConfig {
        foreground_alpha_threshold: 1,
        color_match_tolerance: 0,
    };
    let metrics = verify_pose_graph(&source, &projected, verification)?;
    require_perfect_metrics(&asset.pose_id, metrics)?;
    let overlay =
        build_transparent_overlay(&source, &projected, verification, OverlayPalette::default())?;
    require(
        overlay.counts.missing == 0 && overlay.counts.extra == 0 && overlay.counts.mismatched == 0,
        format!("{} transparent overlay contains differences", asset.pose_id),
    )?;
    let composite = composite_graph_over_source(&source, &projected, 128)?;
    let comparison = build_comparison(&source, &projected, &overlay.image, &composite);

    let evidence_dir = output_root.join("evidence").join(&asset.pose_id);
    fs::create_dir_all(&evidence_dir).map_err(|source| ProductionAlphaError::Io {
        path: evidence_dir.clone(),
        source,
    })?;
    let source_path = evidence_dir.join("source.png");
    write_bytes(&source_path, &png_bytes)?;
    let projected_path = evidence_dir.join("projected.png");
    let overlay_path = evidence_dir.join("transparent-overlay.png");
    let composite_path = evidence_dir.join("composite.png");
    let comparison_path = evidence_dir.join("comparison.png");
    save_png(&projected, &projected_path)?;
    save_png(&overlay.image, &overlay_path)?;
    save_png(&composite, &composite_path)?;
    save_png(&comparison, &comparison_path)?;

    let artifacts = EvidenceArtifacts {
        source_png: evidence_artifact(output_root, &source_path)?,
        projected_png: evidence_artifact(output_root, &projected_path)?,
        transparent_overlay_png: evidence_artifact(output_root, &overlay_path)?,
        composite_png: evidence_artifact(output_root, &composite_path)?,
        comparison_png: evidence_artifact(output_root, &comparison_path)?,
    };
    require(
        artifacts.source_png.sha256 == asset.source_png_sha256,
        format!(
            "{} evidence source was not copied byte-for-byte",
            asset.pose_id
        ),
    )?;

    let graph_relative = relative_path(output_root, &graph_path)?;
    let evidence_relative = relative_path(output_root, &evidence_dir)?;
    let verification_path = evidence_dir.join("verification.json");
    let report = ProductionAlphaVerification {
        schema_version: PRODUCTION_ALPHA_SCHEMA_VERSION,
        compiler_id: PRODUCTION_ALPHA_COMPILER_ID.to_string(),
        sequence: asset.sequence,
        pose_id: asset.pose_id.clone(),
        semantic_id: asset.semantic_id.clone(),
        source_pack: asset.source_pack.clone(),
        source_archive_sha256: asset.archive_sha256.clone(),
        source_member: asset.source_member.clone(),
        source_png_sha256: asset.source_png_sha256.clone(),
        frame: FRAME,
        foreground_bounds: bounds,
        safe_margin_px: asset.safe_margin_px,
        transparent_corners: true,
        foreground_pixel_count: metrics.source_foreground_pixels,
        exact_rgba_equal: true,
        rgba_mismatch,
        metrics,
        overlay_counts: overlay.counts,
        graph_path: graph_relative.clone(),
        graph_sha256: graph_sha256.clone(),
        artifacts,
        technical_status: "exact_rgba_verified".to_string(),
        visual_review_status: "pending_transparent_overlay_review".to_string(),
    };
    write_json(&verification_path, &report)?;
    let verification_relative = relative_path(output_root, &verification_path)?;
    let (anchor_kind, anchor_x, anchor_y) = infer_anchor(&asset.category, bounds);
    let motion_family = runtime_motion_family(&asset.motion.family);
    let contact_mode = infer_contact_mode(&asset.semantic_id, &asset.category);
    let direction = runtime_direction(&asset.motion.direction);
    let phase = runtime_phase(&asset.motion.phase);
    let source_archive = archive_filename(archive_path)?;
    let display_name = display_name(&asset.semantic_id);
    let control_groups = vec![
        "all".to_string(),
        asset.category.clone(),
        motion_family.clone(),
        format!("pack:{}", asset.source_pack),
    ];

    Ok(ProcessedAsset {
        runtime: RuntimeAlphaEntry {
            sequence: asset.sequence,
            source_record_id: asset.pose_id.clone(),
            candidate_id: asset.pose_id.clone(),
            pose_id: asset.pose_id.clone(),
            semantic_id: asset.semantic_id.clone(),
            display_name,
            source_archive,
            source_entry: asset.source_member.clone(),
            source_sha256: asset.source_png_sha256.clone(),
            graph_path: graph_relative.clone(),
            graph_sha256: graph_sha256.clone(),
            graph_id: graph.graph_id,
            frame: [FRAME.width, FRAME.height],
            source_size: [source.width(), source.height()],
            offset: [0, 0],
            foreground_pixel_count: metrics.source_foreground_pixels,
            motion_family,
            contact_mode,
            phase,
            direction,
            authored_transition_neighbors: Vec::new(),
            control_groups,
            primary_for_semantic_id: true,
            duplicate_source_of: None,
            silhouette_iou_millionths: 1_000_000,
            foreground_color_fidelity_millionths: 1_000_000,
            foreground_color_match_ratio_millionths: 1_000_000,
            exact_rgba_equal: true,
            rgba_mismatch_pixel_count: rgba_mismatch.pixel_count,
            rgba_mismatch_channel_count: rgba_mismatch.channel_count,
            source_pack: asset.source_pack.clone(),
            category: asset.category.clone(),
            anchor_kind,
            anchor_x,
            anchor_y,
            evidence_path: evidence_relative.clone(),
        },
        source: SourceLedgerEntry {
            sequence: asset.sequence,
            pose_id: asset.pose_id.clone(),
            semantic_id: asset.semantic_id.clone(),
            source_pack: asset.source_pack.clone(),
            archive_sha256: asset.archive_sha256.clone(),
            source_member: asset.source_member.clone(),
            source_png_sha256: asset.source_png_sha256.clone(),
            manifest_status: asset.manifest_status.clone(),
            category: asset.category.clone(),
            motion: asset.motion.clone(),
        },
        admission: AdmissionLedgerEntry {
            sequence: asset.sequence,
            pose_id: asset.pose_id.clone(),
            technical_status: "exact_rgba_verified".to_string(),
            visual_review_status: "pending_transparent_overlay_review".to_string(),
            source_png_sha256: asset.source_png_sha256.clone(),
            graph_sha256,
            graph_path: graph_relative,
            evidence_path: evidence_relative,
            verification_report_path: verification_relative,
        },
    })
}

fn validate_canvas(
    canvas: &ManifestCanvas,
    expected_safe_margin: Option<u32>,
) -> Result<(), ProductionAlphaError> {
    require(
        canvas.width == FRAME.width && canvas.height == FRAME.height,
        "manifest canvas is not 1254x1254",
    )?;
    require(
        canvas.color_space == "sRGB",
        "manifest color space is not sRGB",
    )?;
    require(canvas.alpha, "manifest canvas does not declare alpha")?;
    if let Some(expected) = expected_safe_margin {
        require(
            canvas.safe_margin_px == Some(expected),
            "manifest safe margin is not 69",
        )?;
    }
    Ok(())
}

fn validate_asset_contract(
    dimensions: &ManifestDimensions,
    color_space: &str,
    alpha: bool,
    safe_margin: u32,
) -> Result<(), ProductionAlphaError> {
    require(
        dimensions.width == FRAME.width && dimensions.height == FRAME.height,
        "asset dimensions are not 1254x1254",
    )?;
    require(color_space == "sRGB", "asset color space is not sRGB")?;
    require(alpha, "asset does not declare alpha")?;
    require(
        safe_margin >= REQUIRED_SAFE_MARGIN,
        "asset safe margin is below 69",
    )
}

fn validate_source_image(
    asset: &SourceAsset,
    image: &RgbaImage,
) -> Result<AlphaBounds, ProductionAlphaError> {
    require(
        image.dimensions() == (FRAME.width, FRAME.height),
        format!("{} decoded dimensions are not 1254x1254", asset.pose_id),
    )?;
    let corners = [
        image.get_pixel(0, 0)[3],
        image.get_pixel(FRAME.width - 1, 0)[3],
        image.get_pixel(0, FRAME.height - 1)[3],
        image.get_pixel(FRAME.width - 1, FRAME.height - 1)[3],
    ];
    require(
        corners == [0, 0, 0, 0],
        format!("{} has a nontransparent corner", asset.pose_id),
    )?;
    let bounds = alpha_bounds(image).ok_or_else(|| {
        ProductionAlphaError::Invariant(format!("{} has no alpha foreground", asset.pose_id))
    })?;
    require(
        bounds == asset.expected_bounds,
        format!(
            "{} alpha bounds {:?} do not match manifest {:?}",
            asset.pose_id, bounds, asset.expected_bounds
        ),
    )?;
    let right_margin = FRAME
        .width
        .checked_sub(bounds.x + bounds.width)
        .ok_or_else(|| ProductionAlphaError::Invariant("alpha x extent overflow".to_string()))?;
    let bottom_margin = FRAME
        .height
        .checked_sub(bounds.y + bounds.height)
        .ok_or_else(|| ProductionAlphaError::Invariant("alpha y extent overflow".to_string()))?;
    let minimum_margin = bounds.x.min(bounds.y).min(right_margin).min(bottom_margin);
    require(
        minimum_margin >= asset.safe_margin_px,
        format!(
            "{} minimum alpha margin {minimum_margin} is below {}",
            asset.pose_id, asset.safe_margin_px
        ),
    )?;
    Ok(bounds)
}

fn alpha_bounds(image: &RgbaImage) -> Option<AlphaBounds> {
    let mut min_x = image.width();
    let mut min_y = image.height();
    let mut max_x = 0;
    let mut max_y = 0;
    let mut found = false;
    for (x, y, pixel) in image.enumerate_pixels() {
        if pixel[3] == 0 {
            continue;
        }
        found = true;
        min_x = min_x.min(x);
        min_y = min_y.min(y);
        max_x = max_x.max(x);
        max_y = max_y.max(y);
    }
    found.then_some(AlphaBounds {
        x: min_x,
        y: min_y,
        width: max_x - min_x + 1,
        height: max_y - min_y + 1,
    })
}

fn require_exact_rgba_match(
    pose_id: &str,
    source: &RgbaImage,
    projected: &RgbaImage,
) -> Result<RgbaMismatch, ProductionAlphaError> {
    if source.dimensions() != projected.dimensions() {
        return Err(ProductionAlphaError::Invariant(format!(
            "{pose_id} exact comparison dimensions differ"
        )));
    }
    let mut mismatch = RgbaMismatch::default();
    for (index, (left, right)) in source.pixels().zip(projected.pixels()).enumerate() {
        if left == right {
            continue;
        }
        mismatch.pixel_count += 1;
        mismatch.channel_count += left
            .0
            .iter()
            .zip(right.0.iter())
            .filter(|(left, right)| left != right)
            .count() as u64;
        if mismatch.first_x.is_none() {
            mismatch.first_x = Some(index as u32 % source.width());
            mismatch.first_y = Some(index as u32 / source.width());
        }
    }
    if source.as_raw() != projected.as_raw() || mismatch.pixel_count != 0 {
        return Err(ProductionAlphaError::ExactRgbaMismatch {
            pose_id: pose_id.to_string(),
            pixel_count: mismatch.pixel_count,
            channel_count: mismatch.channel_count,
        });
    }
    Ok(mismatch)
}

fn require_perfect_metrics(
    pose_id: &str,
    metrics: PoseGraphMetrics,
) -> Result<(), ProductionAlphaError> {
    require(
        metrics.source_foreground_pixels > 0
            && metrics.source_foreground_pixels == metrics.graph_foreground_pixels
            && metrics.missing_pixels == 0
            && metrics.extra_pixels == 0
            && metrics.color_mismatched_pixels == 0
            && metrics.silhouette_precision == 1.0
            && metrics.silhouette_recall == 1.0
            && metrics.silhouette_iou == 1.0
            && metrics.foreground_color_match_ratio == 1.0
            && metrics.foreground_color_fidelity == 1.0,
        format!("{pose_id} did not receive perfect zero-tolerance verification"),
    )
}

fn base_semantic_id_from_filename(filename: &str) -> Result<String, ProductionAlphaError> {
    let stem = filename
        .strip_suffix(".png")
        .ok_or_else(|| ProductionAlphaError::Invariant(format!("{filename} is not a PNG")))?;
    let (prefix, semantic) = stem.split_once('_').ok_or_else(|| {
        ProductionAlphaError::Invariant(format!("{filename} has no semantic filename component"))
    })?;
    require(
        prefix.len() == 3 && prefix.chars().all(|character| character.is_ascii_digit()),
        format!("{filename} does not begin with a three-digit prefix"),
    )?;
    validate_semantic_component(filename, semantic)?;
    Ok(semantic.to_string())
}

fn flight_semantic_id_from_filename(filename: &str) -> Result<String, ProductionAlphaError> {
    let stem = filename
        .strip_suffix(".png")
        .ok_or_else(|| ProductionAlphaError::Invariant(format!("{filename} is not a PNG")))?;
    let rest = stem.strip_prefix("WJFF_").ok_or_else(|| {
        ProductionAlphaError::Invariant(format!("{filename} does not begin with WJFF_"))
    })?;
    let (frame, suffix) = rest.split_once('_').ok_or_else(|| {
        ProductionAlphaError::Invariant(format!("{filename} has no flight semantic suffix"))
    })?;
    require(
        frame.len() == 3 && frame.chars().all(|character| character.is_ascii_digit()),
        format!("{filename} has an invalid WJFF frame prefix"),
    )?;
    validate_semantic_component(filename, suffix)?;
    Ok(format!("fly_forward_camera_{suffix}"))
}

fn validate_semantic_component(filename: &str, semantic: &str) -> Result<(), ProductionAlphaError> {
    require(
        !semantic.is_empty()
            && semantic.chars().all(|character| {
                character.is_ascii_lowercase() || character.is_ascii_digit() || character == '_'
            }),
        format!("{filename} has an invalid semantic component"),
    )
}

fn infer_category(semantic_id: &str, forward_flight: bool) -> &'static str {
    if forward_flight || semantic_id.starts_with("flight_") {
        "flight"
    } else if semantic_id.starts_with("idle_") {
        "idle"
    } else if semantic_id.starts_with("listen_") {
        "listening"
    } else if semantic_id.starts_with("think_")
        || semantic_id.starts_with("realization_")
        || semantic_id.starts_with("acknowledge_")
        || semantic_id.starts_with("wait_")
        || semantic_id.starts_with("shift_")
        || semantic_id == "settle_to_neutral"
    {
        "cognition_transition"
    } else if semantic_id.starts_with("news_") {
        "newsroom_performance"
    } else if semantic_id.starts_with("story_") {
        "storytelling"
    } else if semantic_id.starts_with("speak_") || semantic_id.starts_with("speech_") {
        "speech"
    } else if semantic_id.starts_with("emotion_") {
        "emotion"
    } else if semantic_id.starts_with("hand_") {
        "hand_gesture"
    } else if semantic_id.starts_with("staff_")
        || semantic_id.starts_with("hold_")
        || semantic_id.starts_with("write_")
        || semantic_id.starts_with("receive_")
        || semantic_id.starts_with("offer_")
        || semantic_id.starts_with("touch_")
        || semantic_id.starts_with("drag_")
        || semantic_id.starts_with("lean_")
    {
        "prop_interaction"
    } else if semantic_id.starts_with("magic_") {
        "magic"
    } else if semantic_id.starts_with("dance_") {
        "dance"
    } else if semantic_id.starts_with("comedy_") {
        "comedy"
    } else if semantic_id.starts_with("hero_")
        || semantic_id.starts_with("camera_")
        || semantic_id.starts_with("final_")
    {
        "hero_camera"
    } else if semantic_id.starts_with("walk_")
        || semantic_id.starts_with("run_")
        || semantic_id.starts_with("crouch_")
        || semantic_id.starts_with("jump_")
        || semantic_id.starts_with("fall_")
        || semantic_id.starts_with("kneel_")
        || semantic_id.starts_with("sit_")
        || semantic_id.starts_with("rise_")
        || semantic_id.starts_with("sidestep_")
        || semantic_id.starts_with("locomotion_")
    {
        "ground_locomotion"
    } else if semantic_id.starts_with("turn_") || semantic_id.starts_with("neutral_") {
        "orientation"
    } else {
        "performance"
    }
}

fn infer_motion(semantic_id: &str, forward_flight: bool) -> MotionMetadata {
    let tokens = semantic_id.split('_').collect::<Vec<_>>();
    let family = if forward_flight {
        "forward_camera_flight"
    } else {
        tokens.first().copied().unwrap_or("performance")
    };
    let direction = if semantic_id.contains("toward_camera") {
        "toward_camera"
    } else if semantic_id.contains("away_camera") {
        "away_camera"
    } else if semantic_id.contains("screen_left") {
        "screen_left"
    } else if semantic_id.contains("screen_right") {
        "screen_right"
    } else {
        ["left", "right", "front", "back", "up", "down"]
            .into_iter()
            .find(|direction| tokens.contains(direction))
            .unwrap_or("neutral")
    };
    let phase = if has_any(
        &tokens,
        &[
            "anticipation",
            "prepare",
            "ready",
            "start",
            "begin",
            "crouch",
        ],
    ) {
        "anticipation"
    } else if has_any(
        &tokens,
        &["early", "open", "launch", "push", "raise", "gather"],
    ) {
        "initiation"
    } else if has_any(
        &tokens,
        &["mid", "passing", "apex", "hold", "sequence", "build"],
    ) {
        "action"
    } else if has_any(
        &tokens,
        &[
            "contact", "plant", "release", "recoil", "finish", "complete", "bottom", "late",
        ],
    ) {
        "impact"
    } else if has_any(
        &tokens,
        &["recover", "recovery", "settle", "stop", "close", "home"],
    ) {
        "recovery"
    } else {
        "hold"
    };
    let loop_group = if forward_flight {
        Some("forward_camera_flight_cycle")
    } else if semantic_id.starts_with("walk_") {
        Some("walk_cycle")
    } else if semantic_id.starts_with("run_") {
        Some("run_cycle")
    } else if semantic_id.starts_with("flight_") {
        Some("flight_cycle")
    } else if semantic_id.starts_with("dance_") {
        Some("dance_sequence")
    } else {
        None
    };
    MotionMetadata {
        family: family.to_string(),
        phase: phase.to_string(),
        direction: direction.to_string(),
        loop_group: loop_group.map(str::to_string),
        playback_fps: forward_flight.then_some(10),
    }
}

fn runtime_motion_family(inferred_family: &str) -> String {
    match inferred_family {
        "run" => "run",
        "walk" => "walk",
        "flight" | "forward_camera_flight" => "flight",
        "jump" => "jump",
        "kneel" => "kneel",
        "landing" => "landing",
        _ => "ground_action",
    }
    .to_string()
}

fn runtime_direction(inferred_direction: &str) -> String {
    match inferred_direction {
        "left" | "screen_left" => "west",
        "right" | "screen_right" => "east",
        "back" | "up" | "away_camera" => "north",
        "front" | "down" | "toward_camera" => "south",
        _ => "south",
    }
    .to_string()
}

fn runtime_phase(inferred_phase: &str) -> Option<RuntimePhase> {
    let numerator = match inferred_phase {
        "anticipation" => 0,
        "initiation" => 1,
        "action" => 2,
        "impact" => 3,
        "recovery" => 4,
        _ => return None,
    };
    Some(RuntimePhase {
        numerator,
        denominator: 4,
    })
}

fn infer_contact_mode(semantic_id: &str, category: &str) -> String {
    if category == "flight" || semantic_id.starts_with("jump_") || semantic_id.starts_with("fall_")
    {
        "airborne"
    } else if semantic_id.contains("contact_left") {
        "left_foot"
    } else if semantic_id.contains("contact_right") {
        "right_foot"
    } else if semantic_id.starts_with("kneel_") {
        "kneel_and_staff"
    } else if semantic_id.contains("staff_planted") || semantic_id == "staff_plant" {
        "both_feet_and_staff"
    } else {
        "both_feet"
    }
    .to_string()
}

fn infer_anchor(category: &str, bounds: AlphaBounds) -> (String, u32, u32) {
    if category == "flight" {
        (
            "body_center".to_string(),
            bounds.x + bounds.width / 2,
            bounds.y + bounds.height / 2,
        )
    } else {
        (
            "ground_contact".to_string(),
            bounds.x + bounds.width / 2,
            bounds.y + bounds.height - 1,
        )
    }
}

fn display_name(semantic_id: &str) -> String {
    semantic_id
        .split('_')
        .map(|word| {
            let mut characters = word.chars();
            match characters.next() {
                Some(first) => format!("{}{}", first.to_ascii_uppercase(), characters.as_str()),
                None => String::new(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn has_any(tokens: &[&str], candidates: &[&str]) -> bool {
    candidates
        .iter()
        .any(|candidate| tokens.contains(candidate))
}

fn decode_required_rgba_png(
    pose_id: &str,
    bytes: &[u8],
) -> Result<RgbaImage, ProductionAlphaError> {
    let decoder =
        PngDecoder::new(Cursor::new(bytes)).map_err(|source| ProductionAlphaError::Image {
            pose_id: pose_id.to_string(),
            source,
        })?;
    require(
        decoder.dimensions() == (FRAME.width, FRAME.height),
        format!("{pose_id} PNG header dimensions are not 1254x1254"),
    )?;
    require(
        decoder.color_type() == ColorType::Rgba8,
        format!(
            "{pose_id} PNG color type is {:?}, not RGBA8",
            decoder.color_type()
        ),
    )?;
    let mut rgba = vec![0_u8; decoder.total_bytes() as usize];
    decoder
        .read_image(&mut rgba)
        .map_err(|source| ProductionAlphaError::Image {
            pose_id: pose_id.to_string(),
            source,
        })?;
    RgbaImage::from_raw(FRAME.width, FRAME.height, rgba).ok_or_else(|| {
        ProductionAlphaError::Invariant(format!("{pose_id} RGBA buffer has an invalid length"))
    })
}

fn build_comparison(
    source: &RgbaImage,
    projected: &RgbaImage,
    overlay: &RgbaImage,
    composite: &RgbaImage,
) -> RgbaImage {
    let mut comparison = RgbaImage::from_pixel(
        FRAME.width * 2,
        FRAME.height * 2,
        Rgba([255, 255, 255, 255]),
    );
    place_on_checkerboard(&mut comparison, source, 0, 0);
    place_on_checkerboard(&mut comparison, projected, FRAME.width, 0);
    place_on_checkerboard(&mut comparison, overlay, 0, FRAME.height);
    place_on_checkerboard(&mut comparison, composite, FRAME.width, FRAME.height);
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
            let foreground = *image.get_pixel(x, y);
            canvas.put_pixel(
                offset_x + x,
                offset_y + y,
                alpha_over_opaque(base, foreground),
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

fn open_zip(path: &Path) -> Result<ZipArchive<File>, ProductionAlphaError> {
    let file = File::open(path).map_err(|source| ProductionAlphaError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    ZipArchive::new(file).map_err(|source| ProductionAlphaError::Zip {
        path: path.to_path_buf(),
        source,
    })
}

fn zip_member_counts(
    archive: &mut ZipArchive<File>,
    archive_path: &Path,
) -> Result<BTreeMap<String, usize>, ProductionAlphaError> {
    let mut counts = BTreeMap::new();
    for index in 0..archive.len() {
        let member = archive
            .by_index(index)
            .map_err(|source| ProductionAlphaError::Zip {
                path: archive_path.to_path_buf(),
                source,
            })?;
        *counts.entry(member.name().to_string()).or_insert(0) += 1;
    }
    Ok(counts)
}

fn read_zip_json<T: for<'de> Deserialize<'de>>(
    archive: &mut ZipArchive<File>,
    archive_path: &Path,
    member_counts: &BTreeMap<String, usize>,
    member_name: &str,
) -> Result<T, ProductionAlphaError> {
    let bytes = read_zip_member(archive, archive_path, member_counts, member_name)?;
    serde_json::from_slice(&bytes).map_err(|source| ProductionAlphaError::Json {
        source_name: member_name.to_string(),
        source,
    })
}

fn read_zip_member(
    archive: &mut ZipArchive<File>,
    archive_path: &Path,
    member_counts: &BTreeMap<String, usize>,
    member_name: &str,
) -> Result<Vec<u8>, ProductionAlphaError> {
    require_single_member(member_counts, member_name)?;
    let mut member = archive
        .by_name(member_name)
        .map_err(|source| ProductionAlphaError::Zip {
            path: archive_path.to_path_buf(),
            source,
        })?;
    let mut bytes = Vec::with_capacity(member.size() as usize);
    member
        .read_to_end(&mut bytes)
        .map_err(|source| ProductionAlphaError::Io {
            path: archive_path.to_path_buf(),
            source,
        })?;
    Ok(bytes)
}

fn require_single_member(
    member_counts: &BTreeMap<String, usize>,
    member_name: &str,
) -> Result<(), ProductionAlphaError> {
    require(
        member_counts.get(member_name) == Some(&1),
        format!("ZIP member {member_name} is missing or duplicated"),
    )
}

fn validate_exact_alpha_member_set(
    member_counts: &BTreeMap<String, usize>,
    prefix: &str,
    expected: &BTreeSet<String>,
) -> Result<(), ProductionAlphaError> {
    let actual = member_counts
        .keys()
        .filter(|name| name.starts_with(prefix) && name.ends_with(".png"))
        .cloned()
        .collect::<BTreeSet<_>>();
    require(
        &actual == expected,
        format!(
            "ZIP alpha member set under {prefix} differs from the manifest ({} actual, {} expected)",
            actual.len(),
            expected.len()
        ),
    )
}

fn verify_archive_hash(path: &Path, expected: &str) -> Result<String, ProductionAlphaError> {
    let actual = sha256_file(path)?;
    require(
        actual == expected,
        format!(
            "archive {} has SHA-256 {actual}, expected {expected}",
            path.display()
        ),
    )?;
    Ok(actual)
}

fn require_sha256(value: &str, label: &str) -> Result<(), ProductionAlphaError> {
    require(
        value.len() == 64
            && value
                .chars()
                .all(|character| character.is_ascii_hexdigit() && !character.is_ascii_uppercase()),
        format!("{label} is not a lowercase SHA-256"),
    )
}

fn require(condition: bool, message: impl Into<String>) -> Result<(), ProductionAlphaError> {
    if condition {
        Ok(())
    } else {
        Err(ProductionAlphaError::Invariant(message.into()))
    }
}

fn write_incomplete_marker(output_root: &Path) -> Result<(), ProductionAlphaError> {
    write_bytes(
        &output_root.join(".production-alpha-incomplete"),
        b"Runtime manifests are valid only after this marker is removed.\n",
    )
}

fn remove_incomplete_marker(output_root: &Path) -> Result<(), ProductionAlphaError> {
    let path = output_root.join(".production-alpha-incomplete");
    fs::remove_file(&path).map_err(|source| ProductionAlphaError::Io { path, source })
}

fn save_png(image: &RgbaImage, path: &Path) -> Result<(), ProductionAlphaError> {
    image
        .save_with_format(path, ImageFormat::Png)
        .map_err(|source| ProductionAlphaError::Image {
            pose_id: path.display().to_string(),
            source,
        })
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), ProductionAlphaError> {
    let bytes = serde_json::to_vec_pretty(value).map_err(|source| ProductionAlphaError::Json {
        source_name: path.display().to_string(),
        source,
    })?;
    write_bytes(path, &bytes)
}

fn write_bytes(path: &Path, bytes: &[u8]) -> Result<(), ProductionAlphaError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|source| ProductionAlphaError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    let mut file = File::create(path).map_err(|source| ProductionAlphaError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    file.write_all(bytes)
        .map_err(|source| ProductionAlphaError::Io {
            path: path.to_path_buf(),
            source,
        })
}

fn evidence_artifact(
    output_root: &Path,
    path: &Path,
) -> Result<EvidenceArtifact, ProductionAlphaError> {
    Ok(EvidenceArtifact {
        path: relative_path(output_root, path)?,
        sha256: sha256_file(path)?,
    })
}

fn relative_path(root: &Path, path: &Path) -> Result<String, ProductionAlphaError> {
    path.strip_prefix(root)
        .map(|relative| relative.to_string_lossy().replace('\\', "/"))
        .map_err(|_| {
            ProductionAlphaError::Invariant(format!(
                "{} is outside output root {}",
                path.display(),
                root.display()
            ))
        })
}

fn archive_filename(path: &Path) -> Result<String, ProductionAlphaError> {
    path.file_name()
        .and_then(|name| name.to_str())
        .map(str::to_string)
        .ok_or_else(|| {
            ProductionAlphaError::Invariant(format!("{} has no UTF-8 filename", path.display()))
        })
}

fn sha256_bytes(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn sha256_file(path: &Path) -> Result<String, ProductionAlphaError> {
    let file = File::open(path).map_err(|source| ProductionAlphaError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let mut reader = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = reader
            .read(&mut buffer)
            .map_err(|source| ProductionAlphaError::Io {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_base_and_flight_semantic_ids() {
        assert_eq!(
            base_semantic_id_from_filename("001_turn_front_neutral.png").unwrap(),
            "turn_front_neutral"
        );
        assert_eq!(
            base_semantic_id_from_filename("002_turn_front_3q_left.png").unwrap(),
            "turn_front_3q_left"
        );
        assert_eq!(
            flight_semantic_id_from_filename("WJFF_001_top_recovery.png").unwrap(),
            "fly_forward_camera_top_recovery"
        );
        assert_eq!(
            flight_semantic_id_from_filename("WJFF_010_loop_close.png").unwrap(),
            "fly_forward_camera_loop_close"
        );
        assert!(base_semantic_id_from_filename("missing-prefix.png").is_err());
    }

    #[test]
    fn infers_categories_and_motion_from_semantic_names() {
        assert_eq!(
            infer_category("news_presenter_open", false),
            "newsroom_performance"
        );
        assert_eq!(
            infer_category("walk_contact_left", false),
            "ground_locomotion"
        );
        assert_eq!(infer_category("top_recovery", true), "flight");

        let walk = infer_motion("walk_contact_left", false);
        assert_eq!(walk.family, "walk");
        assert_eq!(walk.phase, "impact");
        assert_eq!(walk.direction, "left");
        assert_eq!(walk.loop_group.as_deref(), Some("walk_cycle"));
        assert_eq!(walk.playback_fps, None);

        let flight = infer_motion("early_powerstroke", true);
        assert_eq!(flight.family, "forward_camera_flight");
        assert_eq!(flight.phase, "initiation");
        assert_eq!(
            flight.loop_group.as_deref(),
            Some("forward_camera_flight_cycle")
        );
        assert_eq!(flight.playback_fps, Some(10));
    }

    #[test]
    fn exact_rgba_gate_rejects_alpha_only_mismatch() {
        let source = RgbaImage::from_pixel(1, 1, Rgba([10, 20, 30, 127]));
        let projected = RgbaImage::from_pixel(1, 1, Rgba([10, 20, 30, 128]));

        let error = require_exact_rgba_match("WJPA-TEST", &source, &projected).unwrap_err();

        assert!(matches!(
            error,
            ProductionAlphaError::ExactRgbaMismatch {
                pixel_count: 1,
                channel_count: 1,
                ..
            }
        ));
    }

    #[test]
    fn exact_rgba_gate_accepts_identical_partial_alpha() {
        let source = RgbaImage::from_pixel(1, 1, Rgba([10, 20, 30, 127]));
        assert_eq!(
            require_exact_rgba_match("WJPA-TEST", &source, &source).unwrap(),
            RgbaMismatch::default()
        );
    }
}
