use crate::error::{read, read_json, PoseToolError, Result};
use crate::model::ArchivePose;
use crate::spec::pose_spec;
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

const INTAKE_MANIFEST: &str = "evidence/pose-library-expansion/intake/manifest.json";
const REGISTRY: &str = "docs/pose-library-expansion/registry.json";

#[derive(Clone, Debug)]
pub struct PoseArchive {
    pub repo_root: PathBuf,
    pub source_manifest_sha256: String,
    pub poses: Vec<ArchivePose>,
}

#[derive(Debug, Deserialize)]
struct IntakeManifest {
    image_count: usize,
    packs: Vec<IntakePack>,
}

#[derive(Debug, Deserialize)]
struct IntakePack {
    images: Vec<IntakeImage>,
}

#[derive(Debug, Deserialize)]
struct IntakeImage {
    candidate_id: String,
    semantic_id: String,
    repository_path: String,
    sha256: String,
    width: u32,
    height: u32,
    mode: String,
    runtime_disposition: String,
}

#[derive(Debug, Deserialize)]
struct Registry {
    candidates: Vec<RegistryCandidate>,
}

#[derive(Debug, Deserialize)]
struct RegistryCandidate {
    id: String,
    order: u32,
    status: String,
    semantic_id: String,
}

pub fn load_archive(repo_root: impl AsRef<Path>) -> Result<PoseArchive> {
    let repo_root = repo_root.as_ref().to_path_buf();
    let intake_path = repo_root.join(INTAKE_MANIFEST);
    let intake_bytes = read(&intake_path)?;
    let intake: IntakeManifest =
        serde_json::from_slice(&intake_bytes).map_err(|source| PoseToolError::Json {
            path: intake_path.clone(),
            source,
        })?;
    let registry: Registry = read_json(&repo_root.join(REGISTRY))?;

    if intake.image_count != 30 {
        return Err(PoseToolError::Archive(format!(
            "intake manifest declares {} images instead of 30",
            intake.image_count
        )));
    }
    if registry.candidates.len() != 30 {
        return Err(PoseToolError::Archive(format!(
            "registry contains {} candidates instead of 30",
            registry.candidates.len()
        )));
    }

    let mut images = BTreeMap::new();
    for image in intake.packs.into_iter().flat_map(|pack| pack.images) {
        if image.mode != "RGB" || image.runtime_disposition != "reference_only" {
            return Err(PoseToolError::Archive(format!(
                "{} must be an RGB reference_only source",
                image.candidate_id
            )));
        }
        let candidate_id = image.candidate_id.clone();
        if images.insert(candidate_id.clone(), image).is_some() {
            return Err(PoseToolError::Archive(format!(
                "duplicate intake candidate {candidate_id}"
            )));
        }
    }
    if images.len() != 30 {
        return Err(PoseToolError::Archive(format!(
            "intake manifest resolves to {} unique candidates",
            images.len()
        )));
    }

    let mut orders = BTreeSet::new();
    let mut poses = Vec::with_capacity(30);
    let mut candidates = registry.candidates;
    candidates.sort_by_key(|candidate| candidate.order);
    for candidate in candidates {
        if !orders.insert(candidate.order) {
            return Err(PoseToolError::Archive(format!(
                "duplicate registry order {}",
                candidate.order
            )));
        }
        let image = images.remove(&candidate.id).ok_or_else(|| {
            PoseToolError::Archive(format!("registry candidate {} has no source", candidate.id))
        })?;
        if image.semantic_id != candidate.semantic_id {
            return Err(PoseToolError::Archive(format!(
                "{} semantic id mismatch: {} != {}",
                candidate.id, image.semantic_id, candidate.semantic_id
            )));
        }
        let source_path = repo_root.join(&image.repository_path);
        let source_bytes = read(&source_path)?;
        let actual_sha256 = sha256_hex(&source_bytes);
        if actual_sha256 != image.sha256 {
            return Err(PoseToolError::Archive(format!(
                "{} source hash mismatch: {} != {}",
                candidate.id, actual_sha256, image.sha256
            )));
        }
        let spec = pose_spec(&candidate.id)?;
        if spec.order != candidate.order || spec.semantic_id != candidate.semantic_id {
            return Err(PoseToolError::Archive(format!(
                "{} disagrees with the Rust semantic catalog",
                candidate.id
            )));
        }
        poses.push(ArchivePose {
            candidate_id: candidate.id,
            semantic_id: candidate.semantic_id,
            status: candidate.status,
            order: candidate.order,
            source_path,
            source_sha256: image.sha256,
            expected_width: image.width,
            expected_height: image.height,
            generation_rows: spec.generation_rows,
        });
    }
    if !images.is_empty() {
        return Err(PoseToolError::Archive(format!(
            "unregistered intake candidates: {:?}",
            images.keys().collect::<Vec<_>>()
        )));
    }

    Ok(PoseArchive {
        repo_root,
        source_manifest_sha256: sha256_hex(&intake_bytes),
        poses,
    })
}

pub(crate) fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    digest.iter().map(|byte| format!("{byte:02x}")).collect()
}
