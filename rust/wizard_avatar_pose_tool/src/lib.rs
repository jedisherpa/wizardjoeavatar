mod admission;
mod archive;
mod compiler;
mod error;
mod feelings_spec;
mod isolation;
mod model;
mod newsroom_admission;
mod newsroom_layers;
mod newsroom_promotion;
mod overlay;
mod pixel_graph;
mod pixelgraph_promotion;
mod production_alpha;
mod quantize;
mod raster;
mod semantics;
mod source_ledger;
mod spec;
mod verification;

pub use admission::{
    admit_one_pose, approve_visual_comparison, exclude_non_pose_source, reject_visual_comparison,
    reopen_visual_approval, AdmissionEntry, AdmissionLedger, AdmissionStatus, AdmitOneConfig,
    EvidenceFile, NonPoseExclusionConfig, NonPoseExclusionReport, PoseAdmissionError,
    PoseVerificationReport, VisualReview, VisualReviewConfig, VisualReviewStatus, MINIMUM_FIDELITY,
};
pub use archive::{load_archive, PoseArchive};
pub use compiler::{
    compile_archive, compile_archive_bytes, compile_archive_with_admission_trace,
    validate_compiled_archive, write_compiled_archive,
};
pub use error::{PoseToolError, Result};
pub use isolation::{isolate_transparent, ForegroundBounds, IsolatedPose, IsolationConfig};
pub use model::{
    AdmissionRecord, AnchorId, AttachmentEdge, CanonicalConfig, CatalogRecord, CatalogRecordKind,
    CellPayload, CompiledArchive, CompiledPose, CompilerConfig, ContactKind, ContactMode,
    ContactPoint, ContactSet, CropBounds, Direction, FacingMetadata, FeaturePresence, MotionFamily,
    MotionMetadata, NamedAnchor, Phase, Point, PoseAlias, RegionId, SemanticCellPayload,
};
pub use newsroom_admission::{
    admit_one_newsroom_source, approve_newsroom_visual_comparison, NewsroomAdmissionEntry,
    NewsroomAdmissionError, NewsroomAdmissionLedger, NewsroomAdmissionStatus,
    NewsroomAdmitOneConfig, NewsroomSourceVerificationReport, NewsroomVisualReviewConfig,
};
pub use newsroom_layers::{
    approve_newsroom_layer_comparison, compile_one_newsroom_layer_source,
    NewsroomLayerAdmissionEntry, NewsroomLayerAdmissionLedger, NewsroomLayerAdmissionStatus,
    NewsroomLayerCompileConfig, NewsroomLayerError, NewsroomLayerTargetReport,
    NewsroomLayerVerificationReport, NewsroomLayerVisualReviewConfig,
};
pub use newsroom_promotion::{
    promote_verified_newsroom, NewsroomPromotionError, NewsroomPromotionManifest,
    NewsroomPromotionReceipt, PromotedNewsroomScene, PromotedNewsroomTarget,
    NEWSROOM_PROMOTION_SCHEMA_VERSION,
};
pub use overlay::{
    build_transparent_overlay, composite_graph_over_source, OverlayCounts, OverlayPalette,
    TransparentOverlay,
};
pub use pixel_graph::{
    build_exact_pixel_graph, normalize_to_frame, project_pixel_graph, read_pixel_graph,
    write_pixel_graph, FrameSpec, NormalizedPose, PixelGraph, PixelGraphError, PixelRun,
};
pub use pixelgraph_promotion::{
    promote_verified_pose_graphs, PixelGraphPromotionError, PixelGraphPromotionManifest,
    PixelGraphPromotionReceipt, RuntimePoseGraphEntry, PIXELGRAPH_PROMOTION_SCHEMA_VERSION,
};
pub use production_alpha::{
    compile_production_alpha, AdmissionLedgerEntry as ProductionAlphaAdmissionEntry,
    AdmissionLedgerV2 as ProductionAlphaAdmissionLedger, AlphaBounds, ArchiveProvenance,
    EvidenceArtifact as ProductionAlphaEvidenceArtifact, EvidenceArtifacts,
    MotionMetadata as ProductionAlphaMotionMetadata, ProductionAlphaConfig, ProductionAlphaError,
    ProductionAlphaReceipt, ProductionAlphaSummary, ProductionAlphaVerification, RgbaMismatch,
    RuntimeAlphaEntry, RuntimeManifestV2 as ProductionAlphaRuntimeManifest,
    SourceLedgerEntry as ProductionAlphaSourceEntry, SourceLedgerV2 as ProductionAlphaSourceLedger,
    BASE_ARCHIVE_SHA256, DEFAULT_BASE_ARCHIVE, DEFAULT_FLIGHT_ARCHIVE, FLIGHT_ARCHIVE_SHA256,
    PRODUCTION_ALPHA_COMPILER_ID, PRODUCTION_ALPHA_SCHEMA_VERSION,
};
pub use quantize::median_cut_quantize;
pub use raster::{
    box_resize_gray, box_resize_rgb, canonicalize_cells, fill_subject_holes,
    retain_subject_components, white_distance_mask,
};
pub use source_ledger::{
    build_source_ledger, default_ledger_path, write_source_ledger, ArchiveLedger, ArchiveSpec,
    SourceLedger, SourceLedgerError, SourceRecord, SourceRecordKind, ARCHIVE_SPECS,
};
pub use verification::{
    verify_pose_graph, PoseGraphMetrics, VerificationConfig, VerificationError,
};
