use anyhow::Context;
use image::{Rgb, RgbImage};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use wizard_avatar_engine::frame_source::render_state_to_cells;
use wizard_avatar_engine::state::{SceneMode, WizardState};

const COLS: usize = 480;
const ROWS: usize = 270;
const BLOCK_SCALE: u32 = 3;

#[derive(Serialize)]
struct SnapshotRecord {
    scene: &'static str,
    path: String,
    sha256: String,
    width: u32,
    height: u32,
}

#[derive(Serialize)]
struct SnapshotManifest {
    schema_version: u32,
    renderer: &'static str,
    source_cells: [usize; 2],
    block_scale: u32,
    snapshots: Vec<SnapshotRecord>,
}

fn main() -> anyhow::Result<()> {
    let repo_root = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    let output = repo_root.join("evidence/newsroom-visual-development-v2/runtime-snapshots");
    std::fs::create_dir_all(&output).with_context(|| format!("create {}", output.display()))?;

    let mut snapshots = Vec::new();
    for (scene, mode) in [
        ("main", SceneMode::NewsroomMain),
        ("explainer", SceneMode::NewsroomExplainer),
        ("interview", SceneMode::NewsroomInterview),
        ("breaking", SceneMode::NewsroomBreaking),
        ("props", SceneMode::NewsroomProps),
        ("overlays", SceneMode::NewsroomOverlays),
    ] {
        let mut state = WizardState {
            scene_mode: mode,
            ..WizardState::default()
        };
        let cells = render_state_to_cells(&mut state, COLS, ROWS);
        let path = output.join(format!("{scene}.png"));
        write_block_snapshot(&path, &cells)?;
        snapshots.push(SnapshotRecord {
            scene,
            path: format!("{scene}.png"),
            sha256: sha256_file(&path)?,
            width: COLS as u32 * BLOCK_SCALE,
            height: ROWS as u32 * BLOCK_SCALE,
        });
    }

    let manifest = SnapshotManifest {
        schema_version: 1,
        renderer: "wizard_avatar_engine::frame_source::render_state_to_cells",
        source_cells: [COLS, ROWS],
        block_scale: BLOCK_SCALE,
        snapshots,
    };
    std::fs::write(
        output.join("manifest.json"),
        serde_json::to_vec_pretty(&manifest)?,
    )?;
    println!(
        "wrote six newsroom v2 runtime snapshots to {}",
        output.display()
    );
    Ok(())
}

fn write_block_snapshot(path: &Path, cells: &[u8]) -> anyhow::Result<()> {
    anyhow::ensure!(cells.len() == COLS * ROWS * 4, "invalid runtime frame");
    let mut image = RgbImage::new(COLS as u32 * BLOCK_SCALE, ROWS as u32 * BLOCK_SCALE);
    for y in 0..ROWS {
        for x in 0..COLS {
            let offset = (y * COLS + x) * 4;
            let rgb = [cells[offset + 1], cells[offset + 2], cells[offset + 3]];
            for block_y in 0..BLOCK_SCALE {
                for block_x in 0..BLOCK_SCALE {
                    image.put_pixel(
                        x as u32 * BLOCK_SCALE + block_x,
                        y as u32 * BLOCK_SCALE + block_y,
                        Rgb(rgb),
                    );
                }
            }
        }
    }
    image
        .save(path)
        .with_context(|| format!("write {}", path.display()))
}

fn sha256_file(path: &Path) -> anyhow::Result<String> {
    let bytes = std::fs::read(path).with_context(|| format!("read {}", path.display()))?;
    Ok(format!("{:x}", Sha256::digest(bytes)))
}
