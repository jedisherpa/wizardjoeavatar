mod archive;
mod compiler;
mod error;
mod feelings_spec;
mod model;
mod quantize;
mod raster;
mod semantics;
mod spec;

pub use archive::{load_archive, PoseArchive};
pub use compiler::{
    compile_archive, compile_archive_bytes, compile_archive_with_admission_trace,
    validate_compiled_archive, write_compiled_archive,
};
pub use error::{PoseToolError, Result};
pub use model::{
    AdmissionRecord, AnchorId, AttachmentEdge, CanonicalConfig, CatalogRecord, CatalogRecordKind,
    CellPayload, CompiledArchive, CompiledPose, CompilerConfig, ContactKind, ContactMode,
    ContactPoint, ContactSet, CropBounds, Direction, FacingMetadata, FeaturePresence, MotionFamily,
    MotionMetadata, NamedAnchor, Phase, Point, PoseAlias, RegionId, SemanticCellPayload,
};
pub use quantize::median_cut_quantize;
pub use raster::{
    box_resize_gray, box_resize_rgb, canonicalize_cells, fill_subject_holes,
    retain_subject_components, white_distance_mask,
};
