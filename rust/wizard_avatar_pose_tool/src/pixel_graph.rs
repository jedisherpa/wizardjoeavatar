use flate2::{read::GzDecoder, write::GzEncoder, Compression};
use image::{Rgba, RgbaImage};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File};
use std::io::{BufReader, BufWriter};
use std::path::{Path, PathBuf};

pub const PIXEL_GRAPH_SCHEMA_VERSION: u32 = 1;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FrameSpec {
    pub width: u32,
    pub height: u32,
}

impl FrameSpec {
    pub fn from_source_dimensions(
        dimensions: impl IntoIterator<Item = (u32, u32)>,
    ) -> Option<Self> {
        dimensions
            .into_iter()
            .fold(None, |frame, (width, height)| match frame {
                Some(current) => Some(Self {
                    width: current.width.max(width),
                    height: current.height.max(height),
                }),
                None => Some(Self { width, height }),
            })
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NormalizedPose {
    pub image: RgbaImage,
    pub offset_x: u32,
    pub offset_y: u32,
}

/// One occupied scanline span. Transparency is represented by absence.
///
/// Every palette index corresponds to one source pixel, making this a lossless colored pixel
/// graph rather than a reference to a raster render asset.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PixelRun {
    pub y: u32,
    pub x: u32,
    pub palette_indices: Vec<u32>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PixelGraph {
    pub schema_version: u32,
    pub graph_id: String,
    pub source_record_id: String,
    pub source_sha256: String,
    pub frame: FrameSpec,
    pub source_width: u32,
    pub source_height: u32,
    pub offset_x: u32,
    pub offset_y: u32,
    pub foreground_pixel_count: u64,
    pub palette: Vec<[u8; 4]>,
    pub runs: Vec<PixelRun>,
}

#[derive(Debug, thiserror::Error)]
pub enum PixelGraphError {
    #[error(
        "source {source_width}x{source_height} does not fit frame {frame_width}x{frame_height}"
    )]
    SourceExceedsFrame {
        source_width: u32,
        source_height: u32,
        frame_width: u32,
        frame_height: u32,
    },
    #[error("invalid pixel graph: {0}")]
    Invalid(String),
    #[error("I/O error at {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

pub fn normalize_to_frame(
    source: &RgbaImage,
    frame: FrameSpec,
) -> Result<NormalizedPose, PixelGraphError> {
    if source.width() > frame.width || source.height() > frame.height {
        return Err(PixelGraphError::SourceExceedsFrame {
            source_width: source.width(),
            source_height: source.height(),
            frame_width: frame.width,
            frame_height: frame.height,
        });
    }
    let offset_x = (frame.width - source.width()) / 2;
    let offset_y = (frame.height - source.height()) / 2;
    let mut image = RgbaImage::new(frame.width, frame.height);
    for (x, y, pixel) in source.enumerate_pixels() {
        if pixel[3] > 0 {
            image.put_pixel(x + offset_x, y + offset_y, *pixel);
        }
    }
    Ok(NormalizedPose {
        image,
        offset_x,
        offset_y,
    })
}

pub fn build_exact_pixel_graph(
    graph_id: impl Into<String>,
    source_record_id: impl Into<String>,
    source_sha256: impl Into<String>,
    source_dimensions: (u32, u32),
    normalized: &NormalizedPose,
) -> PixelGraph {
    let palette_set = normalized
        .image
        .pixels()
        .filter(|pixel| pixel[3] > 0)
        .map(|pixel| pixel.0)
        .collect::<BTreeSet<_>>();
    let palette = palette_set.into_iter().collect::<Vec<_>>();
    let palette_lookup = palette
        .iter()
        .enumerate()
        .map(|(index, rgba)| (*rgba, index as u32))
        .collect::<BTreeMap<_, _>>();

    let mut foreground_pixel_count = 0_u64;
    let mut runs = Vec::new();
    for y in 0..normalized.image.height() {
        let mut x = 0_u32;
        while x < normalized.image.width() {
            while x < normalized.image.width() && normalized.image.get_pixel(x, y)[3] == 0 {
                x += 1;
            }
            if x == normalized.image.width() {
                break;
            }
            let start_x = x;
            let mut palette_indices = Vec::new();
            while x < normalized.image.width() {
                let pixel = normalized.image.get_pixel(x, y);
                if pixel[3] == 0 {
                    break;
                }
                palette_indices.push(palette_lookup[&pixel.0]);
                foreground_pixel_count += 1;
                x += 1;
            }
            runs.push(PixelRun {
                y,
                x: start_x,
                palette_indices,
            });
        }
    }

    PixelGraph {
        schema_version: PIXEL_GRAPH_SCHEMA_VERSION,
        graph_id: graph_id.into(),
        source_record_id: source_record_id.into(),
        source_sha256: source_sha256.into(),
        frame: FrameSpec {
            width: normalized.image.width(),
            height: normalized.image.height(),
        },
        source_width: source_dimensions.0,
        source_height: source_dimensions.1,
        offset_x: normalized.offset_x,
        offset_y: normalized.offset_y,
        foreground_pixel_count,
        palette,
        runs,
    }
}

pub fn project_pixel_graph(graph: &PixelGraph) -> Result<RgbaImage, PixelGraphError> {
    validate_pixel_graph(graph)?;
    let mut image = RgbaImage::new(graph.frame.width, graph.frame.height);
    for run in &graph.runs {
        for (offset, palette_index) in run.palette_indices.iter().enumerate() {
            image.put_pixel(
                run.x + offset as u32,
                run.y,
                Rgba(graph.palette[*palette_index as usize]),
            );
        }
    }
    Ok(image)
}

pub fn write_pixel_graph(
    graph: &PixelGraph,
    path: impl AsRef<Path>,
) -> Result<String, PixelGraphError> {
    validate_pixel_graph(graph)?;
    let path = path.as_ref();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|source| PixelGraphError::Io {
            path: parent.to_path_buf(),
            source,
        })?;
    }
    let file = File::create(path).map_err(|source| PixelGraphError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let mut encoder = GzEncoder::new(BufWriter::new(file), Compression::best());
    serde_json::to_writer(&mut encoder, graph)?;
    let mut writer = encoder.finish().map_err(|source| PixelGraphError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    use std::io::Write;
    writer.flush().map_err(|source| PixelGraphError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    sha256_file(path)
}

pub fn read_pixel_graph(path: impl AsRef<Path>) -> Result<PixelGraph, PixelGraphError> {
    let path = path.as_ref();
    let file = File::open(path).map_err(|source| PixelGraphError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let graph = serde_json::from_reader(GzDecoder::new(BufReader::new(file)))?;
    validate_pixel_graph(&graph)?;
    Ok(graph)
}

fn validate_pixel_graph(graph: &PixelGraph) -> Result<(), PixelGraphError> {
    if graph.schema_version != PIXEL_GRAPH_SCHEMA_VERSION {
        return Err(PixelGraphError::Invalid(format!(
            "schema {} is not {}",
            graph.schema_version, PIXEL_GRAPH_SCHEMA_VERSION
        )));
    }
    if graph.palette.is_empty() || graph.foreground_pixel_count == 0 {
        return Err(PixelGraphError::Invalid(
            "pixel graph must contain foreground colors".to_string(),
        ));
    }
    if graph.graph_id.is_empty()
        || graph.source_record_id.is_empty()
        || graph.source_sha256.is_empty()
    {
        return Err(PixelGraphError::Invalid(
            "graph and source provenance must be non-empty".to_string(),
        ));
    }
    let source_right = graph
        .offset_x
        .checked_add(graph.source_width)
        .ok_or_else(|| PixelGraphError::Invalid("source x extent overflow".to_string()))?;
    let source_bottom = graph
        .offset_y
        .checked_add(graph.source_height)
        .ok_or_else(|| PixelGraphError::Invalid("source y extent overflow".to_string()))?;
    if graph.source_width == 0
        || graph.source_height == 0
        || source_right > graph.frame.width
        || source_bottom > graph.frame.height
    {
        return Err(PixelGraphError::Invalid(
            "source dimensions and offsets do not fit the frame".to_string(),
        ));
    }
    if graph.palette.iter().any(|rgba| rgba[3] == 0) {
        return Err(PixelGraphError::Invalid(
            "transparent colors must be represented by graph absence".to_string(),
        ));
    }
    let mut previous_end = None;
    let mut actual_pixels = 0_u64;
    for run in &graph.runs {
        if run.palette_indices.is_empty() {
            return Err(PixelGraphError::Invalid("empty run".to_string()));
        }
        let end = run
            .x
            .checked_add(run.palette_indices.len() as u32)
            .ok_or_else(|| PixelGraphError::Invalid("run coordinate overflow".to_string()))?;
        if run.y >= graph.frame.height || end > graph.frame.width {
            return Err(PixelGraphError::Invalid(format!(
                "run at ({},{}) exceeds frame",
                run.x, run.y
            )));
        }
        if run.y < graph.offset_y
            || run.y >= source_bottom
            || run.x < graph.offset_x
            || end > source_right
        {
            return Err(PixelGraphError::Invalid(
                "run falls outside the padded source rectangle".to_string(),
            ));
        }
        if previous_end.is_some_and(|(y, x)| run.y < y || (run.y == y && run.x < x)) {
            return Err(PixelGraphError::Invalid(
                "runs are not sorted or overlap".to_string(),
            ));
        }
        if run
            .palette_indices
            .iter()
            .any(|index| *index as usize >= graph.palette.len())
        {
            return Err(PixelGraphError::Invalid(
                "run contains an out-of-range palette index".to_string(),
            ));
        }
        previous_end = Some((run.y, end));
        actual_pixels += run.palette_indices.len() as u64;
    }
    if actual_pixels != graph.foreground_pixel_count {
        return Err(PixelGraphError::Invalid(format!(
            "graph declares {} foreground pixels but stores {actual_pixels}",
            graph.foreground_pixel_count
        )));
    }
    Ok(())
}

fn sha256_file(path: &Path) -> Result<String, PixelGraphError> {
    use std::io::Read;
    let file = File::open(path).map_err(|source| PixelGraphError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    let mut reader = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = reader
            .read(&mut buffer)
            .map_err(|source| PixelGraphError::Io {
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
    fn normalization_only_adds_transparent_edges() {
        let source = RgbaImage::from_pixel(2, 2, Rgba([10, 20, 30, 255]));
        let normalized = normalize_to_frame(
            &source,
            FrameSpec {
                width: 6,
                height: 4,
            },
        )
        .unwrap();
        assert_eq!((normalized.offset_x, normalized.offset_y), (2, 1));
        assert_eq!(normalized.image.get_pixel(2, 1), &Rgba([10, 20, 30, 255]));
        assert_eq!(normalized.image.get_pixel(0, 0), &Rgba([0, 0, 0, 0]));
    }

    #[test]
    fn exact_graph_round_trip_preserves_every_rgba_pixel() {
        let mut source = RgbaImage::new(5, 3);
        source.put_pixel(1, 1, Rgba([1, 2, 3, 255]));
        source.put_pixel(2, 1, Rgba([4, 5, 6, 127]));
        source.put_pixel(4, 1, Rgba([1, 2, 3, 255]));
        let normalized = NormalizedPose {
            image: source.clone(),
            offset_x: 0,
            offset_y: 0,
        };
        let graph = build_exact_pixel_graph("graph", "source", "hash", (5, 3), &normalized);
        assert_eq!(graph.foreground_pixel_count, 3);
        assert_eq!(graph.runs.len(), 2);
        assert_eq!(project_pixel_graph(&graph).unwrap(), source);
    }
}
