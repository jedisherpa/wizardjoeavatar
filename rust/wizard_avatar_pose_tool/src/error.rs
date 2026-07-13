use std::path::PathBuf;

pub type Result<T> = std::result::Result<T, PoseToolError>;

#[derive(Debug, thiserror::Error)]
pub enum PoseToolError {
    #[error("I/O error at {path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("JSON error at {path}: {source}")]
    Json {
        path: PathBuf,
        #[source]
        source: serde_json::Error,
    },
    #[error("image error at {path}: {source}")]
    Image {
        path: PathBuf,
        #[source]
        source: image::ImageError,
    },
    #[error("invalid pose archive: {0}")]
    Archive(String),
    #[error("invalid raster input: {0}")]
    Raster(String),
    #[error("pose {pose_id} overflows the canonical canvas at ({x}, {y})")]
    CanonicalOverflow { pose_id: String, x: i32, y: i32 },
    #[error("output path must remain below {target}: {output}")]
    OutputOutsideTarget { target: PathBuf, output: PathBuf },
}

pub(crate) fn read(path: &std::path::Path) -> Result<Vec<u8>> {
    std::fs::read(path).map_err(|source| PoseToolError::Io {
        path: path.to_path_buf(),
        source,
    })
}

pub(crate) fn read_json<T: serde::de::DeserializeOwned>(path: &std::path::Path) -> Result<T> {
    serde_json::from_slice(&read(path)?).map_err(|source| PoseToolError::Json {
        path: path.to_path_buf(),
        source,
    })
}
