use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::fs::File;
use std::io::Read;
use std::path::Path;
use std::sync::OnceLock;

const FUTURE_POSE_CATALOG_JSON: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../evidence/pose-library-expansion/intake/manifest.json"
));

#[derive(Clone, Debug, Deserialize)]
pub struct FuturePoseCatalog {
    pub schema_version: u32,
    pub purpose: String,
    pub runtime_policy: String,
    pub image_count: usize,
    pub packs: Vec<FuturePosePack>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct FuturePosePack {
    pub id: String,
    pub archive_name: String,
    pub archive_sha256: String,
    pub image_count: usize,
    pub contact_sheet: String,
    pub images: Vec<FuturePoseReference>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct FuturePoseReference {
    pub candidate_id: String,
    pub semantic_id: String,
    pub source_filename: String,
    pub source_order: usize,
    pub repository_path: String,
    pub sha256: String,
    pub width: u32,
    pub height: u32,
    pub mode: String,
    pub runtime_disposition: String,
}

static FUTURE_POSE_CATALOG: OnceLock<Result<FuturePoseCatalog, String>> = OnceLock::new();

pub fn future_pose_catalog() -> Result<&'static FuturePoseCatalog, String> {
    FUTURE_POSE_CATALOG
        .get_or_init(|| {
            serde_json::from_str::<FuturePoseCatalog>(FUTURE_POSE_CATALOG_JSON)
                .map_err(|error| format!("invalid future pose catalog: {error}"))
        })
        .as_ref()
        .map_err(Clone::clone)
}

impl FuturePoseCatalog {
    pub fn validate(&self, repository_root: &Path) -> Result<(), String> {
        if self.schema_version != 1 {
            return Err(format!(
                "unsupported future pose catalog schema {}",
                self.schema_version
            ));
        }
        if self.runtime_policy.is_empty() || !self.runtime_policy.contains("Never load") {
            return Err("future pose catalog must preserve the reference-only policy".to_string());
        }

        let mut candidate_ids = BTreeSet::new();
        let mut semantic_ids = BTreeSet::new();
        let mut total = 0usize;
        for pack in &self.packs {
            if pack.images.len() != pack.image_count {
                return Err(format!(
                    "{} declares {} images but contains {}",
                    pack.id,
                    pack.image_count,
                    pack.images.len()
                ));
            }
            validate_sha256(&pack.archive_sha256, &format!("{} archive", pack.id))?;
            let contact_sheet = repository_root.join(&pack.contact_sheet);
            if !contact_sheet.is_file() {
                return Err(format!(
                    "{} contact sheet is missing: {}",
                    pack.id,
                    contact_sheet.display()
                ));
            }
            for reference in &pack.images {
                total += 1;
                if !candidate_ids.insert(reference.candidate_id.clone()) {
                    return Err(format!("duplicate candidate id {}", reference.candidate_id));
                }
                if !semantic_ids.insert(reference.semantic_id.clone()) {
                    return Err(format!("duplicate semantic id {}", reference.semantic_id));
                }
                if reference.runtime_disposition != "reference_only" {
                    return Err(format!("{} is not reference_only", reference.candidate_id));
                }
                if reference.width == 0 || reference.height == 0 || reference.mode != "RGB" {
                    return Err(format!(
                        "{} has invalid source metadata",
                        reference.candidate_id
                    ));
                }
                validate_sha256(&reference.sha256, &reference.candidate_id)?;
                let path = repository_root.join(&reference.repository_path);
                if !path.is_file() {
                    return Err(format!(
                        "{} source is missing: {}",
                        reference.candidate_id,
                        path.display()
                    ));
                }
                let actual = sha256_file(&path)?;
                if actual != reference.sha256 {
                    return Err(format!(
                        "{} source hash mismatch: {} != {}",
                        reference.candidate_id, actual, reference.sha256
                    ));
                }
            }
        }
        if total != self.image_count {
            return Err(format!(
                "catalog declares {} images but contains {total}",
                self.image_count
            ));
        }
        Ok(())
    }

    pub fn references(&self) -> impl Iterator<Item = &FuturePoseReference> {
        self.packs.iter().flat_map(|pack| pack.images.iter())
    }
}

fn validate_sha256(value: &str, label: &str) -> Result<(), String> {
    if value.len() != 64 || !value.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(format!("{label} has an invalid SHA-256 value"));
    }
    Ok(())
}

fn sha256_file(path: &Path) -> Result<String, String> {
    let mut source =
        File::open(path).map_err(|error| format!("open {}: {error}", path.display()))?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 1024 * 64];
    loop {
        let read = source
            .read(&mut buffer)
            .map_err(|error| format!("read {}: {error}", path.display()))?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn catalog_has_all_thirty_reference_only_poses() {
        let catalog = future_pose_catalog().expect("catalog");
        assert_eq!(catalog.image_count, 30);
        assert_eq!(catalog.references().count(), 30);
        assert!(catalog
            .references()
            .all(|reference| reference.runtime_disposition == "reference_only"));
    }
}
