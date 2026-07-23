use anyhow::{bail, Context};
use flate2::write::GzEncoder;
use flate2::Compression;
use image::imageops::FilterType;
use image::{RgbImage, Rgba, RgbaImage};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use wizard_avatar_engine::scene::{
    SceneCellRun, SceneDefinition, SceneElement, SceneLayerKind, ScenePixel, SCENE_SCHEMA_VERSION,
};

const OUTPUT_WIDTH: usize = 480;
const OUTPUT_HEIGHT: usize = 270;

#[derive(Clone, Copy)]
struct SourceSpec {
    id: &'static str,
    file: &'static str,
    foreground_from_y: Option<usize>,
}

const SOURCES: [SourceSpec; 8] = [
    SourceSpec {
        id: "main_anchor_desk",
        file: "set-main-anchor-desk.png",
        foreground_from_y: Some(166),
    },
    SourceSpec {
        id: "standing_explainer_wall",
        file: "set-standing-explainer-wall.png",
        foreground_from_y: None,
    },
    SourceSpec {
        id: "cohost_interview",
        file: "set-cohost-interview.png",
        foreground_from_y: None,
    },
    SourceSpec {
        id: "magical_breaking_field",
        file: "set-magical-breaking-field.png",
        foreground_from_y: None,
    },
    SourceSpec {
        id: "props_studio_furniture_displays",
        file: "props-studio-furniture-displays.png",
        foreground_from_y: None,
    },
    SourceSpec {
        id: "props_broadcast_magic_overlays",
        file: "props-broadcast-magic-overlays.png",
        foreground_from_y: None,
    },
    SourceSpec {
        id: "camera_board_a_core_coverage",
        file: "camera-board-a-core-coverage.png",
        foreground_from_y: None,
    },
    SourceSpec {
        id: "camera_board_b_dynamic_inserts",
        file: "camera-board-b-dynamic-inserts.png",
        foreground_from_y: None,
    },
];

#[derive(Serialize)]
struct CompiledRecord {
    id: String,
    source: String,
    source_sha256: String,
    graph_file: String,
    graph_sha256: String,
    width: usize,
    height: usize,
    opaque_cell_count: usize,
    run_count: usize,
    color_fidelity: f64,
    silhouette_iou: f64,
    verification_passed: bool,
    transparent_overlay: String,
}

fn main() -> anyhow::Result<()> {
    let mut arguments = std::env::args_os().skip(1);
    if arguments.next().as_deref() != Some(std::ffi::OsStr::new("--legacy-v1")) {
        bail!(
            "legacy v1 compiler is disabled by default; pass --legacy-v1 explicitly. It cannot compile or promote newsroom v2 evidence"
        );
    }
    let repo = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("../.."));
    if arguments.next().is_some() {
        bail!("usage: newsroom_graph_compile --legacy-v1 [repo-root]");
    }
    let source_dir = repo.join("evidence/newsroom-visual-development/images");
    let output_dir = repo.join("rust/wizard_avatar_engine/assets/newsroom/scenes");
    let verification_dir =
        repo.join("evidence/newsroom-visual-development/pixelgraph-verification");
    fs::create_dir_all(&output_dir).context("create newsroom graph output directory")?;
    fs::create_dir_all(&verification_dir)
        .context("create newsroom pixel-graph verification directory")?;

    let mut records = Vec::with_capacity(SOURCES.len());
    for spec in SOURCES {
        let source = source_dir.join(spec.file);
        let output = output_dir.join(format!("{}.scene.json.gz", spec.id));
        records.push(compile_one(spec, &source, &output, &verification_dir)?);
    }
    if records.iter().any(|record| !record.verification_passed) {
        bail!("one or more image-derived graphs failed the 95 percent admission gate");
    }

    let manifest = serde_json::to_vec_pretty(&records)?;
    fs::write(output_dir.join("compiled-manifest.json"), manifest)
        .context("write compiled newsroom manifest")?;
    println!("compiled {} image-derived newsroom graphs", records.len());
    Ok(())
}

fn compile_one(
    spec: SourceSpec,
    source: &Path,
    output: &Path,
    verification_dir: &Path,
) -> anyhow::Result<CompiledRecord> {
    let source_bytes =
        fs::read(source).with_context(|| format!("read source image {}", source.display()))?;
    let image = image::load_from_memory(&source_bytes)
        .with_context(|| format!("decode source image {}", source.display()))?
        .resize_exact(
            OUTPUT_WIDTH as u32,
            OUTPUT_HEIGHT as u32,
            FilterType::Triangle,
        )
        .to_rgb8();

    let mut rear_rows = vec![Vec::<Option<ScenePixel>>::new(); OUTPUT_HEIGHT];
    let mut foreground_rows = vec![Vec::<Option<ScenePixel>>::new(); OUTPUT_HEIGHT];
    for y in 0..OUTPUT_HEIGHT {
        rear_rows[y].reserve(OUTPUT_WIDTH);
        foreground_rows[y].reserve(OUTPUT_WIDTH);
        for x in 0..OUTPUT_WIDTH {
            let [r, g, b] = image.get_pixel(x as u32, y as u32).0;
            let pixel = (!is_sheet_background(r, g, b)).then_some(ScenePixel {
                glyph: b' ',
                rgb: [r, g, b],
            });
            if spec
                .foreground_from_y
                .is_some_and(|threshold| y >= threshold)
            {
                rear_rows[y].push(None);
                foreground_rows[y].push(pixel);
            } else {
                rear_rows[y].push(pixel);
                foreground_rows[y].push(None);
            }
        }
    }

    let rear_runs = rows_to_runs(&rear_rows);
    let foreground_runs = rows_to_runs(&foreground_rows);
    if rear_runs.is_empty() {
        bail!("{} produced an empty pixel graph", spec.id);
    }
    let mut elements = vec![graph_element(
        &format!("{}_image_graph", spec.id),
        SceneLayerKind::SetPiece,
        rear_runs,
    )];
    if !foreground_runs.is_empty() {
        elements.push(graph_element(
            &format!("{}_foreground_graph", spec.id),
            SceneLayerKind::Foreground,
            foreground_runs,
        ));
    }
    let scene = SceneDefinition {
        schema_version: SCENE_SCHEMA_VERSION,
        id: spec.id.to_string(),
        width: OUTPUT_WIDTH,
        height: OUTPUT_HEIGHT,
        clear_rgb: [255, 255, 255],
        elements,
    };
    scene
        .validate()
        .with_context(|| format!("validate {} graph", spec.id))?;

    let (color_fidelity, silhouette_iou, overlay) = verify_graph(&image, &scene)?;
    let verification_passed = color_fidelity >= 0.95 && silhouette_iou >= 0.95;
    let overlay_name = format!("{}.transparent-overlay.png", spec.id);
    overlay
        .save(verification_dir.join(&overlay_name))
        .with_context(|| format!("write {} transparent overlay", spec.id))?;

    let json = serde_json::to_vec(&scene)?;
    let mut encoder = GzEncoder::new(Vec::new(), Compression::best());
    encoder.write_all(&json)?;
    let compressed = encoder.finish()?;
    fs::write(output, &compressed)
        .with_context(|| format!("write compiled graph {}", output.display()))?;

    let opaque_cell_count = scene
        .elements
        .iter()
        .flat_map(|element| &element.runs)
        .map(|run| run.pixels.len())
        .sum();
    let run_count = scene
        .elements
        .iter()
        .map(|element| element.runs.len())
        .sum();
    Ok(CompiledRecord {
        id: spec.id.to_string(),
        source: format!("evidence/newsroom-visual-development/images/{}", spec.file),
        source_sha256: sha256(&source_bytes),
        graph_file: output
            .file_name()
            .expect("graph filename")
            .to_string_lossy()
            .into_owned(),
        graph_sha256: sha256(&compressed),
        width: OUTPUT_WIDTH,
        height: OUTPUT_HEIGHT,
        opaque_cell_count,
        run_count,
        color_fidelity,
        silhouette_iou,
        verification_passed,
        transparent_overlay: format!(
            "evidence/newsroom-visual-development/pixelgraph-verification/{overlay_name}"
        ),
    })
}

fn verify_graph(
    reference: &RgbImage,
    scene: &SceneDefinition,
) -> anyhow::Result<(f64, f64, RgbaImage)> {
    let composed = scene.compose()?;
    let mut absolute_error = 0_u64;
    let mut intersection = 0_u64;
    let mut union = 0_u64;
    let mut overlay = RgbaImage::from_pixel(
        OUTPUT_WIDTH as u32,
        OUTPUT_HEIGHT as u32,
        Rgba([0, 0, 0, 0]),
    );

    for y in 0..OUTPUT_HEIGHT {
        for x in 0..OUTPUT_WIDTH {
            let reference_rgb = reference.get_pixel(x as u32, y as u32).0;
            let graph_rgb = composed
                .get(x as i32, y as i32)
                .map(|cell| [cell.rgb.0, cell.rgb.1, cell.rgb.2])
                .unwrap_or([255, 255, 255]);
            absolute_error += reference_rgb
                .iter()
                .zip(graph_rgb)
                .map(|(left, right)| u64::from(left.abs_diff(right)))
                .sum::<u64>();

            let reference_opaque =
                !is_sheet_background(reference_rgb[0], reference_rgb[1], reference_rgb[2]);
            let graph_opaque = graph_rgb != [255, 255, 255];
            if reference_opaque || graph_opaque {
                union += 1;
            }
            if reference_opaque && graph_opaque {
                intersection += 1;
            }

            let overlay_pixel = match (reference_opaque, graph_opaque) {
                (false, false) => Rgba([0, 0, 0, 0]),
                (true, false) => Rgba([255, 32, 48, 240]),
                (false, true) => Rgba([0, 220, 255, 240]),
                (true, true) => {
                    let error = reference_rgb
                        .iter()
                        .zip(graph_rgb)
                        .map(|(left, right)| left.abs_diff(right))
                        .max()
                        .unwrap_or(0);
                    if error > 24 {
                        Rgba([255, 196, 0, 220])
                    } else {
                        Rgba([
                            ((u16::from(reference_rgb[0]) + u16::from(graph_rgb[0])) / 2) as u8,
                            ((u16::from(reference_rgb[1]) + u16::from(graph_rgb[1])) / 2) as u8,
                            ((u16::from(reference_rgb[2]) + u16::from(graph_rgb[2])) / 2) as u8,
                            190,
                        ])
                    }
                }
            };
            overlay.put_pixel(x as u32, y as u32, overlay_pixel);
        }
    }

    let channel_count = (OUTPUT_WIDTH * OUTPUT_HEIGHT * 3) as f64;
    let color_fidelity = 1.0 - absolute_error as f64 / (channel_count * 255.0);
    let silhouette_iou = if union == 0 {
        1.0
    } else {
        intersection as f64 / union as f64
    };
    Ok((color_fidelity, silhouette_iou, overlay))
}

fn graph_element(id: &str, layer: SceneLayerKind, runs: Vec<SceneCellRun>) -> SceneElement {
    SceneElement {
        id: id.to_string(),
        layer,
        order: 0,
        origin: [0, 0],
        width: OUTPUT_WIDTH,
        height: OUTPUT_HEIGHT,
        visible: true,
        runs,
    }
}

fn rows_to_runs(rows: &[Vec<Option<ScenePixel>>]) -> Vec<SceneCellRun> {
    let mut runs = Vec::new();
    for (y, row) in rows.iter().enumerate() {
        let mut x = 0;
        while x < row.len() {
            while x < row.len() && row[x].is_none() {
                x += 1;
            }
            if x == row.len() {
                break;
            }
            let x_start = x;
            let mut pixels = Vec::new();
            while x < row.len() {
                let Some(pixel) = row[x] else {
                    break;
                };
                pixels.push(pixel);
                x += 1;
            }
            runs.push(SceneCellRun { y, x_start, pixels });
        }
    }
    runs
}

fn is_sheet_background(r: u8, g: u8, b: u8) -> bool {
    let min = r.min(g).min(b);
    let max = r.max(g).max(b);
    min >= 245 || (min >= 232 && max - min <= 8)
}

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
