use image::{imageops, Rgba, RgbaImage};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Serialize)]
struct CaptureEntry {
    pose_id: String,
    path: String,
    sha256: String,
    dimensions: [u32; 2],
}

#[derive(Serialize)]
struct CaptureManifest {
    schema_version: u32,
    compiler_id: &'static str,
    captured_pose_count: usize,
    expected_pose_count: usize,
    missing_pose_ids: Vec<String>,
    duplicate_pose_ids: Vec<String>,
    common_dimensions: [u32; 2],
    contact_sheet_path: String,
    contact_sheet_sha256: String,
    entries: Vec<CaptureEntry>,
}

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-phazer-live-capture-finalize: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let capture_root = parse_path("--capture-root")?;
    let output_path = parse_path("--output")?;
    let mut captures = Vec::with_capacity(48);
    let mut entries = Vec::with_capacity(48);
    for ordinal in 1..=48 {
        let pose_id = format!("WJPS-{ordinal:04}");
        let path = capture_root.join(format!("{pose_id}.png"));
        let encoded = fs::read(&path)
            .map_err(|error| format!("failed to read {}: {error}", path.display()))?;
        let image = image::load_from_memory(&encoded)
            .map_err(|error| format!("failed to decode {}: {error}", path.display()))?
            .into_rgba8();
        entries.push(CaptureEntry {
            pose_id,
            path: path.to_string_lossy().to_string(),
            sha256: sha256_file(&path)?,
            dimensions: [image.width(), image.height()],
        });
        captures.push(image);
    }
    let common_dimensions = entries[0].dimensions;
    if entries
        .iter()
        .any(|entry| entry.dimensions != common_dimensions)
    {
        return Err("live screenshots do not share one viewport".to_string());
    }
    let sheet = contact_sheet(&captures);
    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent)
            .map_err(|error| format!("failed to create {}: {error}", parent.display()))?;
    }
    sheet
        .save_with_format(&output_path, image::ImageFormat::Png)
        .map_err(|error| format!("failed to save {}: {error}", output_path.display()))?;
    let manifest = CaptureManifest {
        schema_version: 1,
        compiler_id: "wizard-avatar-phazer-live-capture-v1",
        captured_pose_count: entries.len(),
        expected_pose_count: 48,
        missing_pose_ids: Vec::new(),
        duplicate_pose_ids: Vec::new(),
        common_dimensions,
        contact_sheet_path: output_path.to_string_lossy().to_string(),
        contact_sheet_sha256: sha256_file(&output_path)?,
        entries,
    };
    let manifest_path = capture_root.join("live-capture-manifest.json");
    let bytes = serde_json::to_vec_pretty(&manifest)
        .map_err(|error| format!("failed to serialize manifest: {error}"))?;
    fs::write(&manifest_path, bytes)
        .map_err(|error| format!("failed to write {}: {error}", manifest_path.display()))?;
    println!(
        "{}",
        serde_json::to_string_pretty(&manifest)
            .map_err(|error| format!("failed to print manifest: {error}"))?
    );
    Ok(())
}

fn parse_path(flag: &str) -> Result<PathBuf, String> {
    let mut arguments = std::env::args().skip(1);
    while let Some(argument) = arguments.next() {
        if argument == flag {
            return arguments
                .next()
                .map(PathBuf::from)
                .ok_or_else(|| format!("{flag} requires a path"));
        }
    }
    Err(format!("{flag} is required"))
}

fn contact_sheet(images: &[RgbaImage]) -> RgbaImage {
    const COLUMNS: u32 = 6;
    const ROWS: u32 = 8;
    const TILE_WIDTH: u32 = 320;
    const TILE_HEIGHT: u32 = 180;
    let mut sheet = RgbaImage::from_pixel(
        COLUMNS * TILE_WIDTH,
        ROWS * TILE_HEIGHT,
        Rgba([255, 255, 255, 255]),
    );
    for (index, image) in images.iter().enumerate() {
        let tile = imageops::resize(
            image,
            TILE_WIDTH,
            TILE_HEIGHT,
            imageops::FilterType::Lanczos3,
        );
        let x = index as u32 % COLUMNS * TILE_WIDTH;
        let y = index as u32 / COLUMNS * TILE_HEIGHT;
        imageops::overlay(&mut sheet, &tile, i64::from(x), i64::from(y));
    }
    sheet
}

fn sha256_file(path: &Path) -> Result<String, String> {
    let bytes =
        fs::read(path).map_err(|error| format!("failed to read {}: {error}", path.display()))?;
    Ok(format!("{:x}", Sha256::digest(bytes)))
}
