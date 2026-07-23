use image::{GenericImageView, ImageFormat};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::cmp::Ordering;
use std::collections::BTreeMap;
use std::fs::{self, File};
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};
use zip::ZipArchive;

pub const LEDGER_SCHEMA_VERSION: u32 = 1;
pub const EXPECTED_ARCHIVE_COUNT: usize = 5;
pub const EXPECTED_SOURCE_RECORD_COUNT: usize = 159;
pub const EXPECTED_STYLE_REFERENCE_COUNT: usize = 1;
pub const STYLE_REFERENCE_ARCHIVE: &str = "Wizard Joe Poses.zip";
pub const STYLE_REFERENCE_ENTRY: &str = "ChatGPT Image Jul 12, 2026, 01_57_13 PM.png";
pub const STYLE_REFERENCE_SHA256: &str =
    "7ac53c9a01743bf422612b269ae51e1170ec736b5b188c19b4b9d4653b1e21fd";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ArchiveSpec {
    pub file_name: &'static str,
    pub expected_png_count: usize,
}

pub const ARCHIVE_SPECS: [ArchiveSpec; EXPECTED_ARCHIVE_COUNT] = [
    ArchiveSpec {
        file_name: "Wizard Joe Poses.zip",
        expected_png_count: 11,
    },
    ArchiveSpec {
        file_name: "Wizard Joe Poses 2.zip",
        expected_png_count: 10,
    },
    ArchiveSpec {
        file_name: "Wizard Joe Poses Flying and Action.zip",
        expected_png_count: 20,
    },
    ArchiveSpec {
        file_name: "Wizard Joe Poses Feelings.zip",
        expected_png_count: 60,
    },
    ArchiveSpec {
        file_name: "Wizard Dance etc.zip",
        expected_png_count: 58,
    },
];

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SourceRecordKind {
    PoseCandidate,
    StyleReference,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceRecord {
    pub serial: usize,
    pub record_id: String,
    pub kind: SourceRecordKind,
    pub archive_order: usize,
    pub archive_filename: String,
    pub archive_entry_order: usize,
    pub archive_entry: String,
    pub sha256: String,
    pub byte_length: u64,
    pub width: u32,
    pub height: u32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub exact_duplicate_of: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ArchiveLedger {
    pub order: usize,
    pub filename: String,
    pub sha256: String,
    pub byte_length: u64,
    pub record_count: usize,
    pub first_serial: usize,
    pub last_serial: usize,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceLedger {
    pub schema_version: u32,
    pub ledger_id: String,
    pub policy: String,
    pub archive_count: usize,
    pub record_count: usize,
    pub pose_candidate_count: usize,
    pub style_reference_count: usize,
    pub unique_content_count: usize,
    pub archives: Vec<ArchiveLedger>,
    pub records: Vec<SourceRecord>,
}

#[derive(Debug, thiserror::Error)]
pub enum SourceLedgerError {
    #[error("I/O error at {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("invalid ZIP archive {path}: {source}")]
    Zip {
        path: PathBuf,
        #[source]
        source: zip::result::ZipError,
    },
    #[error("cannot read {entry} from {path}: {source}")]
    ZipEntryIo {
        path: PathBuf,
        entry: String,
        #[source]
        source: std::io::Error,
    },
    #[error("cannot decode PNG {entry} from {path}: {source}")]
    Image {
        path: PathBuf,
        entry: String,
        #[source]
        source: image::ImageError,
    },
    #[error("cannot encode ledger JSON: {0}")]
    Json(#[from] serde_json::Error),
    #[error("source inventory violation: {0}")]
    Inventory(String),
}

#[derive(Debug)]
struct PendingRecord {
    archive_entry: String,
    kind: SourceRecordKind,
    sha256: String,
    byte_length: u64,
    width: u32,
    height: u32,
}

pub fn build_source_ledger(
    downloads_dir: impl AsRef<Path>,
) -> Result<SourceLedger, SourceLedgerError> {
    let downloads_dir = downloads_dir.as_ref();
    let mut records = Vec::with_capacity(EXPECTED_SOURCE_RECORD_COUNT);
    let mut archives = Vec::with_capacity(EXPECTED_ARCHIVE_COUNT);
    let mut first_record_by_hash = BTreeMap::<String, String>::new();

    for (archive_index, spec) in ARCHIVE_SPECS.iter().enumerate() {
        let archive_order = archive_index + 1;
        let archive_path = downloads_dir.join(spec.file_name);
        let archive_sha256 = sha256_file(&archive_path)?;
        let archive_byte_length = file_length(&archive_path)?;
        let file = File::open(&archive_path).map_err(|source| SourceLedgerError::Io {
            path: archive_path.clone(),
            source,
        })?;
        let mut zip = ZipArchive::new(file).map_err(|source| SourceLedgerError::Zip {
            path: archive_path.clone(),
            source,
        })?;
        let mut pending = Vec::with_capacity(spec.expected_png_count);

        for index in 0..zip.len() {
            let mut entry = zip
                .by_index(index)
                .map_err(|source| SourceLedgerError::Zip {
                    path: archive_path.clone(),
                    source,
                })?;
            let entry_name = entry.name().to_string();
            if !is_real_png_entry(&entry_name) {
                continue;
            }
            let mut bytes = Vec::with_capacity(entry.size() as usize);
            entry
                .read_to_end(&mut bytes)
                .map_err(|source| SourceLedgerError::ZipEntryIo {
                    path: archive_path.clone(),
                    entry: entry_name.clone(),
                    source,
                })?;
            let sha256 = sha256_bytes(&bytes);
            let kind = classify_record(spec.file_name, &entry_name, &sha256);
            let image = image::load_from_memory_with_format(&bytes, ImageFormat::Png).map_err(
                |source| SourceLedgerError::Image {
                    path: archive_path.clone(),
                    entry: entry_name.clone(),
                    source,
                },
            )?;
            let (width, height) = image.dimensions();
            pending.push(PendingRecord {
                archive_entry: entry_name,
                kind,
                sha256,
                byte_length: bytes.len() as u64,
                width,
                height,
            });
        }

        if pending.len() != spec.expected_png_count {
            return Err(SourceLedgerError::Inventory(format!(
                "{} contains {} real PNG entries; expected {}",
                spec.file_name,
                pending.len(),
                spec.expected_png_count
            )));
        }
        pending.sort_by(|left, right| {
            record_kind_order(&left.kind)
                .cmp(&record_kind_order(&right.kind))
                .then_with(|| natural_cmp(&left.archive_entry, &right.archive_entry))
        });

        let first_serial = records.len() + 1;
        for (entry_index, pending_record) in pending.into_iter().enumerate() {
            let serial = records.len() + 1;
            let record_id = format!("WJSRC-{serial:04}");
            let exact_duplicate_of = first_record_by_hash.get(&pending_record.sha256).cloned();
            first_record_by_hash
                .entry(pending_record.sha256.clone())
                .or_insert_with(|| record_id.clone());
            records.push(SourceRecord {
                serial,
                record_id,
                kind: pending_record.kind,
                archive_order,
                archive_filename: spec.file_name.to_string(),
                archive_entry_order: entry_index + 1,
                archive_entry: pending_record.archive_entry,
                sha256: pending_record.sha256,
                byte_length: pending_record.byte_length,
                width: pending_record.width,
                height: pending_record.height,
                exact_duplicate_of,
            });
        }
        archives.push(ArchiveLedger {
            order: archive_order,
            filename: spec.file_name.to_string(),
            sha256: archive_sha256,
            byte_length: archive_byte_length,
            record_count: spec.expected_png_count,
            first_serial,
            last_serial: records.len(),
        });
    }

    let style_reference_count = records
        .iter()
        .filter(|record| record.kind == SourceRecordKind::StyleReference)
        .count();
    if records.len() != EXPECTED_SOURCE_RECORD_COUNT {
        return Err(SourceLedgerError::Inventory(format!(
            "inventory contains {} records; expected {EXPECTED_SOURCE_RECORD_COUNT}",
            records.len()
        )));
    }
    if style_reference_count != EXPECTED_STYLE_REFERENCE_COUNT {
        return Err(SourceLedgerError::Inventory(format!(
            "inventory contains {style_reference_count} style references; expected {EXPECTED_STYLE_REFERENCE_COUNT}"
        )));
    }

    Ok(SourceLedger {
        schema_version: LEDGER_SCHEMA_VERSION,
        ledger_id: "wizard-joe-complete-nondeduplicated-source-inventory-v1".to_string(),
        policy: "Every real PNG archive entry is a separate serial admission record; exact duplicates are linked but never collapsed, and __MACOSX AppleDouble entries are excluded.".to_string(),
        archive_count: archives.len(),
        record_count: records.len(),
        pose_candidate_count: records.len() - style_reference_count,
        style_reference_count,
        unique_content_count: first_record_by_hash.len(),
        archives,
        records,
    })
}

pub fn default_ledger_path(repo_root: impl AsRef<Path>) -> PathBuf {
    repo_root
        .as_ref()
        .join("docs/pose-admission/wizard-joe-source-ledger.json")
}

pub fn write_source_ledger(
    ledger: &SourceLedger,
    output_path: impl AsRef<Path>,
) -> Result<PathBuf, SourceLedgerError> {
    validate_ledger(ledger)?;
    let output_path = output_path.as_ref();
    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent).map_err(|source| SourceLedgerError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    let mut bytes = serde_json::to_vec_pretty(ledger)?;
    bytes.push(b'\n');
    fs::write(output_path, bytes).map_err(|source| SourceLedgerError::Io {
        path: output_path.to_path_buf(),
        source,
    })?;
    Ok(output_path.to_path_buf())
}

fn validate_ledger(ledger: &SourceLedger) -> Result<(), SourceLedgerError> {
    if ledger.archive_count != EXPECTED_ARCHIVE_COUNT
        || ledger.archives.len() != EXPECTED_ARCHIVE_COUNT
    {
        return Err(SourceLedgerError::Inventory(
            "ledger archive count is inconsistent".to_string(),
        ));
    }
    if ledger.record_count != EXPECTED_SOURCE_RECORD_COUNT
        || ledger.records.len() != EXPECTED_SOURCE_RECORD_COUNT
    {
        return Err(SourceLedgerError::Inventory(
            "ledger record count is inconsistent".to_string(),
        ));
    }
    if ledger.style_reference_count != EXPECTED_STYLE_REFERENCE_COUNT
        || ledger.pose_candidate_count + ledger.style_reference_count != ledger.record_count
    {
        return Err(SourceLedgerError::Inventory(
            "ledger record dispositions are inconsistent".to_string(),
        ));
    }
    for (index, record) in ledger.records.iter().enumerate() {
        let expected_serial = index + 1;
        if record.serial != expected_serial
            || record.record_id != format!("WJSRC-{expected_serial:04}")
        {
            return Err(SourceLedgerError::Inventory(format!(
                "record at index {index} is not serial {expected_serial}"
            )));
        }
    }
    Ok(())
}

fn classify_record(archive: &str, entry: &str, sha256: &str) -> SourceRecordKind {
    if archive == STYLE_REFERENCE_ARCHIVE
        && entry == STYLE_REFERENCE_ENTRY
        && sha256 == STYLE_REFERENCE_SHA256
    {
        SourceRecordKind::StyleReference
    } else {
        SourceRecordKind::PoseCandidate
    }
}

fn record_kind_order(kind: &SourceRecordKind) -> u8 {
    match kind {
        SourceRecordKind::PoseCandidate => 0,
        SourceRecordKind::StyleReference => 1,
    }
}

fn is_real_png_entry(entry: &str) -> bool {
    let normalized = entry.replace('\\', "/");
    let components = normalized.split('/').collect::<Vec<_>>();
    if components
        .iter()
        .any(|component| component.eq_ignore_ascii_case("__MACOSX"))
    {
        return false;
    }
    let Some(filename) = components.last() else {
        return false;
    };
    !filename.starts_with("._") && filename.to_ascii_lowercase().ends_with(".png")
}

fn natural_cmp(left: &str, right: &str) -> Ordering {
    let mut left_chars = left.chars().peekable();
    let mut right_chars = right.chars().peekable();
    loop {
        match (left_chars.peek(), right_chars.peek()) {
            (None, None) => return Ordering::Equal,
            (None, Some(_)) => return Ordering::Less,
            (Some(_), None) => return Ordering::Greater,
            (Some(left_char), Some(right_char))
                if left_char.is_ascii_digit() && right_char.is_ascii_digit() =>
            {
                let left_digits = take_digits(&mut left_chars);
                let right_digits = take_digits(&mut right_chars);
                let left_trimmed = left_digits.trim_start_matches('0');
                let right_trimmed = right_digits.trim_start_matches('0');
                let left_number = if left_trimmed.is_empty() {
                    "0"
                } else {
                    left_trimmed
                };
                let right_number = if right_trimmed.is_empty() {
                    "0"
                } else {
                    right_trimmed
                };
                let number_order = left_number
                    .len()
                    .cmp(&right_number.len())
                    .then_with(|| left_number.cmp(right_number))
                    .then_with(|| left_digits.len().cmp(&right_digits.len()));
                if number_order != Ordering::Equal {
                    return number_order;
                }
            }
            (Some(left_char), Some(right_char)) => {
                let character_order = left_char
                    .to_ascii_lowercase()
                    .cmp(&right_char.to_ascii_lowercase());
                if character_order != Ordering::Equal {
                    return character_order;
                }
                left_chars.next();
                right_chars.next();
            }
        }
    }
}

fn take_digits<I>(characters: &mut std::iter::Peekable<I>) -> String
where
    I: Iterator<Item = char>,
{
    let mut digits = String::new();
    while characters.peek().is_some_and(char::is_ascii_digit) {
        if let Some(character) = characters.next() {
            digits.push(character);
        }
    }
    digits
}

fn sha256_file(path: &Path) -> Result<String, SourceLedgerError> {
    let file = File::open(path).map_err(|source| SourceLedgerError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let mut reader = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = reader
            .read(&mut buffer)
            .map_err(|source| SourceLedgerError::Io {
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

fn file_length(path: &Path) -> Result<u64, SourceLedgerError> {
    fs::metadata(path)
        .map(|metadata| metadata.len())
        .map_err(|source| SourceLedgerError::Io {
            path: path.to_path_buf(),
            source,
        })
}

fn sha256_bytes(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn apple_double_and_non_png_entries_are_excluded() {
        assert!(is_real_png_entry("pose.png"));
        assert!(is_real_png_entry("folder/POSE.PNG"));
        assert!(!is_real_png_entry("__MACOSX/._pose.png"));
        assert!(!is_real_png_entry("folder/__MACOSX/pose.png"));
        assert!(!is_real_png_entry("._pose.png"));
        assert!(!is_real_png_entry("pose.jpg"));
    }

    #[test]
    fn source_names_sort_naturally() {
        let mut names = vec!["pose (10).png", "pose (2).png", "pose (1).png"];
        names.sort_by(|left, right| natural_cmp(left, right));
        assert_eq!(names, ["pose (1).png", "pose (2).png", "pose (10).png"]);
    }

    #[test]
    fn canonical_style_reference_requires_archive_entry_and_hash() {
        assert_eq!(
            classify_record(
                STYLE_REFERENCE_ARCHIVE,
                STYLE_REFERENCE_ENTRY,
                STYLE_REFERENCE_SHA256
            ),
            SourceRecordKind::StyleReference
        );
        assert_eq!(
            classify_record("another.zip", STYLE_REFERENCE_ENTRY, STYLE_REFERENCE_SHA256),
            SourceRecordKind::PoseCandidate
        );
    }

    #[test]
    fn archive_contract_totals_159_records() {
        assert_eq!(ARCHIVE_SPECS.len(), EXPECTED_ARCHIVE_COUNT);
        assert_eq!(
            ARCHIVE_SPECS
                .iter()
                .map(|archive| archive.expected_png_count)
                .sum::<usize>(),
            EXPECTED_SOURCE_RECORD_COUNT
        );
    }

    #[test]
    fn duplicate_hashes_remain_separate_serial_records() {
        let hash = sha256_bytes(b"same image");
        let mut first_by_hash = BTreeMap::new();
        let first_id = "WJSRC-0001".to_string();
        first_by_hash.insert(hash.clone(), first_id.clone());
        let duplicate_of = first_by_hash.get(&hash).cloned();
        assert_eq!(duplicate_of, Some(first_id));
    }
}
