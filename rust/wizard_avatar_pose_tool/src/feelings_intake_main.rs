use image::{imageops, DynamicImage, GenericImageView, Rgba, RgbaImage};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::env;
use std::error::Error;
use std::fs::{self, File};
use std::io::{BufWriter, Read, Write};
use std::path::{Path, PathBuf};

const SOURCE_DIR: &str = "evidence/pose-library-expansion/intake/feelings";
const MANIFEST_PATH: &str = "evidence/pose-library-expansion/intake/feelings-manifest.json";
const CONTACT_SHEET_PATH: &str =
    "evidence/pose-library-expansion/intake/contact-sheets/wizard-joe-poses-feelings.png";
const QUEUE_PATH: &str = "docs/pose-library-expansion/feelings-queue.json";
const ARCHIVE_NAME: &str = "Wizard Joe Poses Feelings.zip";
const ID_PREFIX: &str = "WJFL";
const FIRST_GLOBAL_ORDER: usize = 31;
const EXPECTED_IMAGE_COUNT: usize = 60;

#[derive(Serialize)]
struct IntakeManifest {
    schema_version: u32,
    generated_on: &'static str,
    purpose: &'static str,
    runtime_policy: &'static str,
    queue_status: &'static str,
    archive_name: &'static str,
    archive_sha256: String,
    image_count: usize,
    unique_source_count: usize,
    source_directory: &'static str,
    contact_sheet: &'static str,
    images: Vec<IntakeImage>,
}

#[derive(Clone, Serialize)]
struct IntakeImage {
    candidate_id: String,
    global_order: usize,
    status: &'static str,
    semantic_id: Option<String>,
    source_filename: String,
    source_order: usize,
    repository_path: String,
    sha256: String,
    width: u32,
    height: u32,
    mode: &'static str,
    runtime_disposition: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    exact_duplicate_of: Option<String>,
}

#[derive(Serialize)]
struct QueueRegistry {
    schema_version: u32,
    queue_id: &'static str,
    updated_at: &'static str,
    source_manifest: &'static str,
    integration_policy: &'static str,
    candidate_count: usize,
    queued_count: usize,
    candidates: Vec<QueueCandidate>,
}

#[derive(Serialize)]
struct QueueCandidate {
    id: String,
    order: usize,
    owner: Option<String>,
    status: &'static str,
    semantic_id: Option<String>,
    archive_entry: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    exact_duplicate_of: Option<String>,
}

fn main() -> Result<(), Box<dyn Error>> {
    let repo_root = env::args()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or(env::current_dir()?);
    let archive_path = env::args()
        .nth(2)
        .map(PathBuf::from)
        .ok_or("usage: wizard-avatar-feelings-intake <repo-root> <archive-path>")?;

    let source_dir = repo_root.join(SOURCE_DIR);
    let mut sources = fs::read_dir(&source_dir)?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.extension()
                .and_then(|value| value.to_str())
                .is_some_and(|value| value.eq_ignore_ascii_case("png"))
        })
        .collect::<Vec<_>>();
    sources.sort_by_key(|path| source_sort_key(path));
    if sources.len() != EXPECTED_IMAGE_COUNT {
        return Err(format!(
            "expected {EXPECTED_IMAGE_COUNT} feelings sources, found {}",
            sources.len()
        )
        .into());
    }

    let archive_sha256 = sha256_file(&archive_path)?;
    let mut first_by_hash = BTreeMap::new();
    let mut images = Vec::with_capacity(sources.len());
    let mut decoded = Vec::with_capacity(sources.len());

    for (index, source_path) in sources.iter().enumerate() {
        let source_filename = source_path
            .file_name()
            .and_then(|value| value.to_str())
            .ok_or("source filename is not UTF-8")?
            .to_string();
        let candidate_id = format!("{ID_PREFIX}-{:02}", index + 1);
        let source_sha256 = sha256_file(source_path)?;
        let exact_duplicate_of = first_by_hash.get(&source_sha256).cloned();
        first_by_hash
            .entry(source_sha256.clone())
            .or_insert_with(|| candidate_id.clone());

        let image = image::open(source_path)?;
        let (width, height) = image.dimensions();
        let mode = if image.color().has_alpha() {
            "RGBA"
        } else {
            "RGB"
        };
        if mode != "RGB" {
            return Err(format!("{candidate_id} must be an RGB source").into());
        }
        decoded.push(image);
        images.push(IntakeImage {
            candidate_id,
            global_order: FIRST_GLOBAL_ORDER + index,
            status: "QUEUED",
            semantic_id: None,
            source_filename: source_filename.clone(),
            source_order: index + 1,
            repository_path: format!("{SOURCE_DIR}/{source_filename}"),
            sha256: source_sha256,
            width,
            height,
            mode,
            runtime_disposition: "reference_only",
            exact_duplicate_of,
        });
    }

    write_contact_sheet(&repo_root.join(CONTACT_SHEET_PATH), &decoded)?;
    write_json(
        &repo_root.join(MANIFEST_PATH),
        &IntakeManifest {
            schema_version: 1,
            generated_on: "2026-07-13",
            purpose: "Deferred visual references for Rust procedural WizardJoe feelings and pose integration",
            runtime_policy: "Never load these PNGs at runtime; translate approved references into canonical Rust cell geometry, anchors, regions, and transition rules.",
            queue_status: "QUEUED",
            archive_name: ARCHIVE_NAME,
            archive_sha256,
            image_count: images.len(),
            unique_source_count: first_by_hash.len(),
            source_directory: SOURCE_DIR,
            contact_sheet: CONTACT_SHEET_PATH,
            images: images.clone(),
        },
    )?;
    write_json(
        &repo_root.join(QUEUE_PATH),
        &QueueRegistry {
            schema_version: 1,
            queue_id: "wizardjoe-feelings-2026-07-13",
            updated_at: "2026-07-13",
            source_manifest: MANIFEST_PATH,
            integration_policy: "Rust-only procedural translation; sources remain reference-only and are integrated serially after semantic intake and transition planning.",
            candidate_count: images.len(),
            queued_count: images.len(),
            candidates: images
                .into_iter()
                .map(|image| QueueCandidate {
                    id: image.candidate_id,
                    order: image.global_order,
                    owner: None,
                    status: image.status,
                    semantic_id: image.semantic_id,
                    archive_entry: image.source_filename,
                    exact_duplicate_of: image.exact_duplicate_of,
                })
                .collect(),
        },
    )?;

    println!(
        "queued {EXPECTED_IMAGE_COUNT} references ({} unique sources) in {QUEUE_PATH}",
        first_by_hash.len()
    );
    Ok(())
}

fn write_json(path: &Path, value: &impl Serialize) -> Result<(), Box<dyn Error>> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut writer = BufWriter::new(File::create(path)?);
    serde_json::to_writer_pretty(&mut writer, value)?;
    writer.write_all(b"\n")?;
    Ok(())
}

fn sha256_file(path: &Path) -> Result<String, Box<dyn Error>> {
    let mut source = File::open(path)?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 64 * 1024];
    loop {
        let read = source.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn source_sort_key(path: &Path) -> (u8, u8, u8, u8, usize) {
    let name = path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    let day = if name.contains("Jul 12") { 12 } else { 13 };
    let time_start = name.rfind(", ").map(|index| index + 2).unwrap_or_default();
    let time = name.get(time_start..time_start + 8).unwrap_or("00_00_00");
    let mut parts = time.split('_').filter_map(|part| part.parse::<u8>().ok());
    let mut hour = parts.next().unwrap_or_default();
    let minute = parts.next().unwrap_or_default();
    let second = parts.next().unwrap_or_default();
    let is_pm = name.contains(" PM ");
    if is_pm && hour != 12 {
        hour += 12;
    } else if !is_pm && hour == 12 {
        hour = 0;
    }
    let source_order = name
        .rsplit_once('(')
        .and_then(|(_, suffix)| suffix.strip_suffix(").png"))
        .and_then(|value| value.parse::<usize>().ok())
        .unwrap_or_default();
    (day, hour, minute, second, source_order)
}

fn write_contact_sheet(path: &Path, images: &[DynamicImage]) -> Result<(), Box<dyn Error>> {
    const COLUMNS: u32 = 10;
    const CELL_WIDTH: u32 = 170;
    const CELL_HEIGHT: u32 = 190;
    const THUMB_SIZE: u32 = 156;
    let rows = images.len().div_ceil(COLUMNS as usize) as u32;
    let mut sheet = RgbaImage::from_pixel(
        COLUMNS * CELL_WIDTH,
        rows * CELL_HEIGHT,
        Rgba([255, 255, 255, 255]),
    );

    for (index, source) in images.iter().enumerate() {
        let column = index as u32 % COLUMNS;
        let row = index as u32 / COLUMNS;
        let thumbnail = source.thumbnail(THUMB_SIZE, THUMB_SIZE).to_rgba8();
        let x = column * CELL_WIDTH + (CELL_WIDTH - thumbnail.width()) / 2;
        let y = row * CELL_HEIGHT + 4 + (THUMB_SIZE - thumbnail.height()) / 2;
        imageops::overlay(&mut sheet, &thumbnail, x.into(), y.into());
        draw_text(
            &mut sheet,
            column * CELL_WIDTH + 41,
            row * CELL_HEIGHT + 166,
            &format!("{ID_PREFIX}-{:02}", index + 1),
            2,
        );
    }

    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    sheet.save(path)?;
    Ok(())
}

fn draw_text(image: &mut RgbaImage, x: u32, y: u32, text: &str, scale: u32) {
    let ink = Rgba([22, 25, 28, 255]);
    let mut cursor = x;
    for character in text.chars() {
        if let Some(rows) = glyph(character) {
            for (row, bits) in rows.iter().enumerate() {
                for column in 0..5 {
                    if bits & (1 << (4 - column)) != 0 {
                        for dy in 0..scale {
                            for dx in 0..scale {
                                let px = cursor + column * scale + dx;
                                let py = y + row as u32 * scale + dy;
                                if px < image.width() && py < image.height() {
                                    image.put_pixel(px, py, ink);
                                }
                            }
                        }
                    }
                }
            }
        }
        cursor += 6 * scale;
    }
}

fn glyph(character: char) -> Option<[u8; 7]> {
    match character {
        'W' => Some([
            0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001,
        ]),
        'J' => Some([
            0b00111, 0b00010, 0b00010, 0b00010, 0b10010, 0b10010, 0b01100,
        ]),
        'F' => Some([
            0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000,
        ]),
        'L' => Some([
            0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111,
        ]),
        '-' => Some([0, 0, 0, 0b11111, 0, 0, 0]),
        '0' => Some([
            0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110,
        ]),
        '1' => Some([
            0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110,
        ]),
        '2' => Some([
            0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111,
        ]),
        '3' => Some([
            0b11110, 0b00001, 0b00001, 0b01110, 0b00001, 0b00001, 0b11110,
        ]),
        '4' => Some([
            0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010,
        ]),
        '5' => Some([
            0b11111, 0b10000, 0b10000, 0b11110, 0b00001, 0b00001, 0b11110,
        ]),
        '6' => Some([
            0b01110, 0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110,
        ]),
        '7' => Some([
            0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000,
        ]),
        '8' => Some([
            0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110,
        ]),
        '9' => Some([
            0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b01110,
        ]),
        _ => None,
    }
}
