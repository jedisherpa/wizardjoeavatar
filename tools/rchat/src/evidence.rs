//! Deterministic per-frame evidence ledger and manifest receipts.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Component, Path};

pub const FRAME_SCHEMA: &str = "wizardjoe-rchat-frame-evidence/v1";
pub const MANIFEST_SCHEMA: &str = "wizardjoe-rchat-evidence-manifest/v1";

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CellPoint {
    pub x: i32,
    pub y: i32,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FrameEvidence {
    pub schema: String,
    pub schema_version: u32,
    pub run_id: String,
    pub scenario_id: String,
    pub transition_id: Option<String>,
    pub clip_id: Option<String>,
    pub frame_index: u64,
    pub simulation_tick: u64,
    pub source_event_id: Option<String>,
    pub command_id: Option<String>,
    pub state_revision: u64,
    pub pose_id: String,
    pub previous_pose_id: Option<String>,
    pub transition_progress: f64,
    pub contacts: Vec<String>,
    pub root: CellPoint,
    pub anchors: BTreeMap<String, CellPoint>,
    pub channel_generations: BTreeMap<String, u64>,
    pub source_frame_sha256: String,
    pub encoded_frame_sha256: String,
    pub decoded_frame_sha256: String,
    pub presented_frame_sha256: String,
    pub png_path: Option<String>,
    pub quality_failures: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EvidenceRun {
    pub run_id: String,
    pub branch: String,
    pub git_sha: String,
    pub frames: Vec<FrameEvidence>,
    pub failures: Vec<String>,
    pub skips: Vec<String>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum EvidenceStatus {
    Pass,
    Fail,
    Skip,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EvidenceArtifact {
    pub path: String,
    pub sha256: String,
    pub bytes: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EvidenceManifest {
    pub schema: String,
    pub schema_version: u32,
    pub run_id: String,
    pub branch: String,
    pub git_sha: String,
    pub status: EvidenceStatus,
    pub frame_count: u64,
    pub scenario_count: u64,
    pub screenshot_count: u64,
    pub first_frame_index: Option<u64>,
    pub last_frame_index: Option<u64>,
    pub ledger: EvidenceArtifact,
    pub presented_stream_sha256: String,
    pub quality_failure_count: u64,
    pub failures: Vec<String>,
    pub skips: Vec<String>,
}

#[derive(Clone, Debug)]
pub struct EvidenceWriter {
    run: EvidenceRun,
}

impl EvidenceWriter {
    pub fn new(
        run_id: impl Into<String>,
        branch: impl Into<String>,
        git_sha: impl Into<String>,
    ) -> Self {
        Self {
            run: EvidenceRun {
                run_id: run_id.into(),
                branch: branch.into(),
                git_sha: git_sha.into(),
                frames: Vec::new(),
                failures: Vec::new(),
                skips: Vec::new(),
            },
        }
    }

    pub fn push_frame(&mut self, frame: FrameEvidence) {
        self.run.frames.push(frame);
    }

    pub fn add_failure(&mut self, failure: impl Into<String>) {
        self.run.failures.push(failure.into());
    }

    pub fn add_skip(&mut self, skip: impl Into<String>) {
        self.run.skips.push(skip.into());
    }

    pub fn finish(
        self,
        ledger_path: &Path,
        manifest_path: &Path,
    ) -> Result<EvidenceManifest, String> {
        write_evidence(&self.run, ledger_path, manifest_path)
    }
}

pub fn write_evidence(
    run: &EvidenceRun,
    ledger_path: &Path,
    manifest_path: &Path,
) -> Result<EvidenceManifest, String> {
    validate_run(run)?;
    ensure_parent(ledger_path)?;
    ensure_parent(manifest_path)?;

    let ledger_bytes = ledger_bytes(&run.frames)?;
    let ledger_sha256 = sha256(&ledger_bytes);
    let stream_sha256 = presented_stream_sha256(&run.frames);
    fs::write(ledger_path, &ledger_bytes)
        .map_err(|error| format!("failed to write {}: {error}", ledger_path.display()))?;

    let quality_failure_count = run
        .frames
        .iter()
        .map(|frame| frame.quality_failures.len() as u64)
        .sum();
    let scenarios: BTreeSet<&str> = run
        .frames
        .iter()
        .map(|frame| frame.scenario_id.as_str())
        .collect();
    let screenshot_count = run
        .frames
        .iter()
        .filter(|frame| frame.png_path.is_some())
        .count() as u64;
    let status = evidence_status(
        run.frames.len() as u64,
        quality_failure_count,
        &run.failures,
        &run.skips,
    );
    let ledger_name = ledger_path
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| "ledger path requires a UTF-8 file name".to_owned())?;
    let manifest = EvidenceManifest {
        schema: MANIFEST_SCHEMA.to_owned(),
        schema_version: 1,
        run_id: run.run_id.clone(),
        branch: run.branch.clone(),
        git_sha: run.git_sha.clone(),
        status,
        frame_count: run.frames.len() as u64,
        scenario_count: scenarios.len() as u64,
        screenshot_count,
        first_frame_index: run.frames.first().map(|frame| frame.frame_index),
        last_frame_index: run.frames.last().map(|frame| frame.frame_index),
        ledger: EvidenceArtifact {
            path: ledger_name.to_owned(),
            sha256: ledger_sha256,
            bytes: ledger_bytes.len() as u64,
        },
        presented_stream_sha256: stream_sha256,
        quality_failure_count,
        failures: run.failures.clone(),
        skips: run.skips.clone(),
    };
    let mut manifest_bytes = serde_json::to_vec_pretty(&manifest)
        .map_err(|error| format!("failed to serialize evidence manifest: {error}"))?;
    manifest_bytes.push(b'\n');
    fs::write(manifest_path, manifest_bytes)
        .map_err(|error| format!("failed to write {}: {error}", manifest_path.display()))?;
    Ok(manifest)
}

pub fn validate_evidence_paths(
    ledger_path: &Path,
    manifest_path: &Path,
) -> Result<EvidenceManifest, String> {
    let manifest_bytes = fs::read(manifest_path)
        .map_err(|error| format!("failed to read {}: {error}", manifest_path.display()))?;
    let manifest: EvidenceManifest = serde_json::from_slice(&manifest_bytes)
        .map_err(|error| format!("invalid manifest {}: {error}", manifest_path.display()))?;
    if manifest.schema != MANIFEST_SCHEMA || manifest.schema_version != 1 {
        return Err("manifest schema must be wizardjoe-rchat-evidence-manifest/v1".to_owned());
    }

    let ledger_bytes = fs::read(ledger_path)
        .map_err(|error| format!("failed to read {}: {error}", ledger_path.display()))?;
    if manifest.ledger.sha256 != sha256(&ledger_bytes) {
        return Err("ledger SHA-256 does not match the manifest receipt".to_owned());
    }
    if manifest.ledger.bytes != ledger_bytes.len() as u64 {
        return Err("ledger byte count does not match the manifest receipt".to_owned());
    }
    let frames = parse_ledger(&ledger_bytes)?;
    let run = EvidenceRun {
        run_id: manifest.run_id.clone(),
        branch: manifest.branch.clone(),
        git_sha: manifest.git_sha.clone(),
        frames,
        failures: manifest.failures.clone(),
        skips: manifest.skips.clone(),
    };
    validate_run(&run)?;
    let quality_failure_count = run
        .frames
        .iter()
        .map(|frame| frame.quality_failures.len() as u64)
        .sum();
    if manifest.frame_count != run.frames.len() as u64
        || manifest.first_frame_index != run.frames.first().map(|frame| frame.frame_index)
        || manifest.last_frame_index != run.frames.last().map(|frame| frame.frame_index)
        || manifest.screenshot_count
            != run
                .frames
                .iter()
                .filter(|frame| frame.png_path.is_some())
                .count() as u64
        || manifest.quality_failure_count != quality_failure_count
        || manifest.presented_stream_sha256 != presented_stream_sha256(&run.frames)
        || manifest.status
            != evidence_status(
                run.frames.len() as u64,
                quality_failure_count,
                &run.failures,
                &run.skips,
            )
    {
        return Err("manifest summary does not match its per-frame ledger".to_owned());
    }
    let scenarios: BTreeSet<&str> = run
        .frames
        .iter()
        .map(|frame| frame.scenario_id.as_str())
        .collect();
    if manifest.scenario_count != scenarios.len() as u64 {
        return Err("manifest scenario count does not match the ledger".to_owned());
    }
    Ok(manifest)
}

fn validate_run(run: &EvidenceRun) -> Result<(), String> {
    if run.run_id.is_empty() || run.branch.is_empty() {
        return Err("run_id and branch must be non-empty".to_owned());
    }
    if !is_git_sha(&run.git_sha) {
        return Err("git_sha must be lowercase 40-hex".to_owned());
    }
    if !run.skips.is_empty() && !run.frames.is_empty() {
        return Err("a skipped evidence run cannot contain captured frames".to_owned());
    }
    if run.frames.is_empty() && run.skips.is_empty() {
        return Err("an evidence run without frames must record an explicit skip".to_owned());
    }
    let mut previous_tick = None;
    for (expected_index, frame) in run.frames.iter().enumerate() {
        validate_frame(frame, &run.run_id, expected_index as u64, previous_tick)?;
        previous_tick = Some(frame.simulation_tick);
    }
    Ok(())
}

fn validate_frame(
    frame: &FrameEvidence,
    run_id: &str,
    expected_index: u64,
    previous_tick: Option<u64>,
) -> Result<(), String> {
    if frame.schema != FRAME_SCHEMA || frame.schema_version != 1 {
        return Err(format!("frame {expected_index} has the wrong schema"));
    }
    if frame.run_id != run_id || frame.frame_index != expected_index {
        return Err(format!(
            "frame {expected_index} must have the run ID and contiguous index declared by the run"
        ));
    }
    if frame.scenario_id.is_empty() || frame.pose_id.is_empty() {
        return Err(format!(
            "frame {expected_index} requires scenario_id and pose_id"
        ));
    }
    if previous_tick.is_some_and(|tick| frame.simulation_tick < tick) {
        return Err(format!(
            "frame {expected_index} simulation_tick moved backwards"
        ));
    }
    if !frame.transition_progress.is_finite() || !(0.0..=1.0).contains(&frame.transition_progress) {
        return Err(format!(
            "frame {expected_index} transition_progress must be finite and between 0 and 1"
        ));
    }
    for (name, hash) in [
        ("source_frame_sha256", &frame.source_frame_sha256),
        ("encoded_frame_sha256", &frame.encoded_frame_sha256),
        ("decoded_frame_sha256", &frame.decoded_frame_sha256),
        ("presented_frame_sha256", &frame.presented_frame_sha256),
    ] {
        if !is_sha256(hash) {
            return Err(format!(
                "frame {expected_index} {name} must be lowercase 64-hex"
            ));
        }
    }
    if frame
        .png_path
        .as_deref()
        .is_some_and(|path| !is_safe_relative_path(path))
    {
        return Err(format!(
            "frame {expected_index} png_path must be a safe relative path"
        ));
    }
    Ok(())
}

fn ledger_bytes(frames: &[FrameEvidence]) -> Result<Vec<u8>, String> {
    let mut bytes = Vec::new();
    for frame in frames {
        serde_json::to_writer(&mut bytes, frame)
            .map_err(|error| format!("failed to serialize frame ledger: {error}"))?;
        bytes.push(b'\n');
    }
    Ok(bytes)
}

fn parse_ledger(bytes: &[u8]) -> Result<Vec<FrameEvidence>, String> {
    let text = std::str::from_utf8(bytes)
        .map_err(|error| format!("frame ledger must be UTF-8 NDJSON: {error}"))?;
    let mut frames = Vec::new();
    for (line_index, line) in text.lines().enumerate() {
        if line.is_empty() {
            return Err(format!("frame ledger line {} is empty", line_index + 1));
        }
        let frame = serde_json::from_str(line)
            .map_err(|error| format!("invalid frame ledger line {}: {error}", line_index + 1))?;
        frames.push(frame);
    }
    Ok(frames)
}

fn presented_stream_sha256(frames: &[FrameEvidence]) -> String {
    let mut digest = Sha256::new();
    for frame in frames {
        digest.update(frame.presented_frame_sha256.as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

fn evidence_status(
    frame_count: u64,
    quality_failure_count: u64,
    failures: &[String],
    skips: &[String],
) -> EvidenceStatus {
    if !failures.is_empty() || quality_failure_count > 0 {
        EvidenceStatus::Fail
    } else if !skips.is_empty() || frame_count == 0 {
        EvidenceStatus::Skip
    } else {
        EvidenceStatus::Pass
    }
}

fn ensure_parent(path: &Path) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|error| format!("failed to create {}: {error}", parent.display()))?;
    }
    Ok(())
}

fn is_git_sha(value: &str) -> bool {
    value.len() == 40
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn is_safe_relative_path(value: &str) -> bool {
    !value.is_empty()
        && !value.contains('\\')
        && !value.contains(':')
        && !value.contains('\0')
        && !Path::new(value).is_absolute()
        && Path::new(value)
            .components()
            .all(|component| matches!(component, Component::Normal(_)))
}

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
