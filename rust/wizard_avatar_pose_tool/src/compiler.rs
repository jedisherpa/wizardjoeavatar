use crate::archive::{sha256_hex, PoseArchive};
use crate::error::{read, PoseToolError, Result};
use crate::model::{
    CatalogRecord, CatalogRecordKind, CellPayload, CompiledArchive, CompiledPose, CompilerConfig,
    Point, PoseAlias,
};
use crate::quantize::median_cut_quantize;
use crate::raster::{
    box_resize_gray, box_resize_rgb, canonicalize_cells, crop_gray, crop_rgb, expand_bounds,
    fill_subject_holes, round_ratio_ties_even, subject_bounds, white_distance_mask,
};
use crate::semantics::{compile_semantics, validate_staff_topology};
use crate::spec::{pose_spec, SpecKind, BASELINE_POSE_IDS, POSE_SPECS};
use image::ImageFormat;
use std::collections::BTreeSet;
use std::path::{Component, Path, PathBuf};

const COMPILER_ID: &str = "wizard-avatar-pose-tool-rust-v3";

pub fn compile_archive(archive: &PoseArchive, config: CompilerConfig) -> Result<CompiledArchive> {
    validate_source_catalog(archive)?;
    let mut poses = Vec::with_capacity(29);
    let mut aliases = Vec::with_capacity(1);
    let mut catalog = Vec::with_capacity(30);
    let mut archive_palette = BTreeSet::new();

    for source in &archive.poses {
        let spec = pose_spec(&source.candidate_id)?;
        let (kind, geometry_id) = match spec.kind {
            SpecKind::Geometry => {
                let compiled = compile_pose(source, spec, config)?;
                archive_palette.extend(compiled.cells.iter().map(|cell| cell.rgb));
                poses.push(compiled);
                (CatalogRecordKind::Geometry, spec.semantic_id)
            }
            SpecKind::Alias { target_semantic_id } => {
                aliases.push(PoseAlias {
                    candidate_id: source.candidate_id.clone(),
                    semantic_id: source.semantic_id.clone(),
                    target_semantic_id: target_semantic_id.to_string(),
                });
                (CatalogRecordKind::Alias, target_semantic_id)
            }
        };
        catalog.push(CatalogRecord {
            order: source.order,
            candidate_id: source.candidate_id.clone(),
            semantic_id: source.semantic_id.clone(),
            source_sha256: source.source_sha256.clone(),
            kind,
            geometry_id: geometry_id.to_string(),
        });
    }

    let palette_bytes = archive_palette
        .iter()
        .flat_map(|rgb| rgb.iter().copied())
        .collect::<Vec<_>>();
    let mut compiled = CompiledArchive {
        schema_version: 3,
        compiler_id: COMPILER_ID.to_string(),
        source_manifest_sha256: archive.source_manifest_sha256.clone(),
        config,
        catalog_count: catalog.len(),
        unique_geometry_count: poses.len(),
        alias_count: aliases.len(),
        catalog,
        poses,
        aliases,
        palette_color_count: archive_palette.len(),
        palette_sha256: sha256_hex(&palette_bytes),
        archive_sha256: String::new(),
    };
    validate_compiled_archive(&compiled)?;
    compiled.archive_sha256 = content_hash(&compiled)?;
    Ok(compiled)
}

pub fn compile_archive_bytes(archive: &CompiledArchive) -> Result<Vec<u8>> {
    let mut bytes = serde_json::to_vec_pretty(archive).map_err(|source| PoseToolError::Json {
        path: PathBuf::from("<compiled-archive>"),
        source,
    })?;
    bytes.push(b'\n');
    Ok(bytes)
}

pub fn write_compiled_archive(
    archive: &CompiledArchive,
    output: impl AsRef<Path>,
) -> Result<PathBuf> {
    let crate_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let target = normalize_path(&crate_root.join("target"));
    let requested = if output.as_ref().is_absolute() {
        output.as_ref().to_path_buf()
    } else {
        crate_root.join(output)
    };
    let output = normalize_path(&requested);
    if !output.starts_with(&target) {
        return Err(PoseToolError::OutputOutsideTarget { target, output });
    }
    validate_compiled_archive(archive)?;
    if archive.archive_sha256 != content_hash(archive)? {
        return Err(PoseToolError::Archive(
            "compiled archive content hash does not match its payload".to_string(),
        ));
    }
    let parent = output.parent().ok_or_else(|| {
        PoseToolError::Raster("compiled output must have a parent directory".to_string())
    })?;
    std::fs::create_dir_all(parent).map_err(|source| PoseToolError::Io {
        path: parent.to_path_buf(),
        source,
    })?;
    std::fs::write(&output, compile_archive_bytes(archive)?).map_err(|source| {
        PoseToolError::Io {
            path: output.clone(),
            source,
        }
    })?;
    Ok(output)
}

pub fn validate_compiled_archive(archive: &CompiledArchive) -> Result<()> {
    if archive.schema_version != 3 || archive.compiler_id != COMPILER_ID {
        return Err(PoseToolError::Archive(
            "compiled artifact is not wizard-avatar schema v3".to_string(),
        ));
    }
    if archive.catalog_count != 30
        || archive.unique_geometry_count != 29
        || archive.alias_count != 1
        || archive.catalog.len() != archive.catalog_count
        || archive.poses.len() != archive.unique_geometry_count
        || archive.aliases.len() != archive.alias_count
    {
        return Err(PoseToolError::Archive(format!(
            "schema v3 requires 30 catalog records, 29 geometries, and 1 alias; got {}/{}/{}",
            archive.catalog_count, archive.unique_geometry_count, archive.alias_count
        )));
    }
    for (index, record) in archive.catalog.iter().enumerate() {
        if record.order != index as u32 + 1 {
            return Err(PoseToolError::Archive(format!(
                "catalog record {} has noncanonical order {}",
                record.candidate_id, record.order
            )));
        }
    }
    let geometry_ids = archive
        .poses
        .iter()
        .map(|pose| pose.semantic_id.as_str())
        .collect::<BTreeSet<_>>();
    if geometry_ids.len() != 29 {
        return Err(PoseToolError::Archive(
            "geometry semantic IDs are not unique".to_string(),
        ));
    }
    let allowed_neighbor_ids = geometry_ids
        .iter()
        .copied()
        .chain(BASELINE_POSE_IDS)
        .collect::<BTreeSet<_>>();
    let candidate_ids = archive
        .catalog
        .iter()
        .map(|record| record.candidate_id.as_str())
        .collect::<BTreeSet<_>>();
    if candidate_ids.len() != 30 {
        return Err(PoseToolError::Archive(
            "catalog candidate IDs are not unique".to_string(),
        ));
    }
    for pose in &archive.poses {
        if pose.anchors.len() != 25
            || pose.cells.len() != pose.cell_count
            || pose.cells.is_empty()
            || pose.z_order.len() != 18
        {
            return Err(PoseToolError::Archive(format!(
                "{} has incomplete animation geometry",
                pose.semantic_id
            )));
        }
        for neighbor in &pose.motion.authored_transition_neighbors {
            if !allowed_neighbor_ids.contains(neighbor.as_str()) {
                return Err(PoseToolError::Archive(format!(
                    "{} has unresolved transition neighbor {neighbor}",
                    pose.semantic_id
                )));
            }
        }
        validate_staff_topology(&pose.semantic_id, &pose.anchors, &pose.cells)?;
    }
    let alias = &archive.aliases[0];
    if alias.candidate_id != "WJFA-10"
        || alias.semantic_id != "fly_front_hover_ready"
        || alias.target_semantic_id != "fly_front_hover_neutral"
        || !geometry_ids.contains(alias.target_semantic_id.as_str())
        || geometry_ids.contains(alias.semantic_id.as_str())
    {
        return Err(PoseToolError::Archive(
            "WJFA-10 must be the sole cell-free alias to fly_front_hover_neutral".to_string(),
        ));
    }
    let alias_record = archive
        .catalog
        .iter()
        .find(|record| record.candidate_id == alias.candidate_id)
        .ok_or_else(|| PoseToolError::Archive("alias lacks catalog record".to_string()))?;
    if alias_record.kind != CatalogRecordKind::Alias
        || alias_record.geometry_id != alias.target_semantic_id
    {
        return Err(PoseToolError::Archive(
            "alias catalog record does not resolve to its target geometry".to_string(),
        ));
    }
    Ok(())
}

fn validate_source_catalog(archive: &PoseArchive) -> Result<()> {
    if archive.poses.len() != POSE_SPECS.len() {
        return Err(PoseToolError::Archive(format!(
            "Rust semantic table expects {} records but archive has {}",
            POSE_SPECS.len(),
            archive.poses.len()
        )));
    }
    for (source, spec) in archive.poses.iter().zip(POSE_SPECS.iter()) {
        if source.order != spec.order
            || source.candidate_id != spec.candidate_id
            || source.semantic_id != spec.semantic_id
        {
            return Err(PoseToolError::Archive(format!(
                "archive record {} does not match Rust semantic spec {} at order {}",
                source.candidate_id, spec.candidate_id, spec.order
            )));
        }
        if matches!(spec.kind, SpecKind::Geometry) && source.generation_rows != spec.generation_rows
        {
            return Err(PoseToolError::Archive(format!(
                "{} generation rows {:?} disagree with Rust authority {:?}",
                source.candidate_id, source.generation_rows, spec.generation_rows
            )));
        }
    }
    Ok(())
}

fn compile_pose(
    pose: &crate::model::ArchivePose,
    spec: &crate::spec::PoseSpec,
    config: CompilerConfig,
) -> Result<CompiledPose> {
    let source_bytes = read(&pose.source_path)?;
    let image =
        image::load_from_memory_with_format(&source_bytes, ImageFormat::Png).map_err(|source| {
            PoseToolError::Image {
                path: pose.source_path.clone(),
                source,
            }
        })?;
    let rgb_image = image.to_rgb8();
    let width = rgb_image.width();
    let height = rgb_image.height();
    if width != pose.expected_width || height != pose.expected_height {
        return Err(PoseToolError::Archive(format!(
            "{} decoded as {}x{} instead of {}x{}",
            pose.candidate_id, width, height, pose.expected_width, pose.expected_height
        )));
    }
    let pixels = rgb_image
        .as_raw()
        .chunks_exact(3)
        .map(|rgb| [rgb[0], rgb[1], rgb[2]])
        .collect::<Vec<_>>();
    let rough_mask = white_distance_mask(&pixels, width, height, config.white_distance_threshold)?;
    let crop = expand_bounds(
        subject_bounds(&rough_mask, width, height)?,
        width,
        height,
        config.margin,
    );
    let cropped_pixels = crop_rgb(&pixels, width, height, crop)?;
    let cropped_mask = crop_gray(&rough_mask, width, height, crop)?;
    let solid_mask = fill_subject_holes(&cropped_mask, crop.width(), crop.height())?;
    let generation_rows = spec.generation_rows.ok_or_else(|| {
        PoseToolError::Archive(format!(
            "{} geometry lacks generation rows",
            spec.candidate_id
        ))
    })?;
    if generation_rows == 0 || generation_rows > config.canonical.rows {
        return Err(PoseToolError::Archive(format!(
            "{} generation_rows {} is outside canonical height {}",
            pose.candidate_id, generation_rows, config.canonical.rows
        )));
    }
    let generation_cols = round_ratio_ties_even(
        u64::from(generation_rows) * u64::from(crop.width()),
        u64::from(crop.height()),
    )
    .max(1);
    let resized_pixels = box_resize_rgb(
        &cropped_pixels,
        crop.width(),
        crop.height(),
        generation_cols,
        generation_rows,
    )?;
    let resized_mask = box_resize_gray(
        &solid_mask,
        crop.width(),
        crop.height(),
        generation_cols,
        generation_rows,
    )?;
    let (quantized_pixels, palette) =
        median_cut_quantize(&resized_pixels, config.quantized_colors)?;
    let mut local_cells = Vec::new();
    for y in 0..generation_rows {
        for x in 0..generation_cols {
            let index = (y as usize) * (generation_cols as usize) + (x as usize);
            if resized_mask[index] >= config.coverage_threshold {
                local_cells.push(CellPayload {
                    x: x as i32,
                    y: y as i32,
                    rgb: quantized_pixels[index],
                });
            }
        }
    }
    if local_cells.is_empty() {
        return Err(PoseToolError::Raster(format!(
            "{} produced no occupied cells",
            pose.candidate_id
        )));
    }
    let local_root = Point {
        x: (generation_cols / 2) as i32,
        y: generation_rows as i32 - 1,
    };
    let (canonical_shift, cells) = canonicalize_cells(
        &pose.semantic_id,
        &local_cells,
        local_root,
        config.canonical,
    )?;
    let cell_bytes = cells
        .iter()
        .flat_map(|cell| {
            let mut bytes = Vec::with_capacity(11);
            bytes.extend_from_slice(&cell.x.to_le_bytes());
            bytes.extend_from_slice(&cell.y.to_le_bytes());
            bytes.extend_from_slice(&cell.rgb);
            bytes
        })
        .collect::<Vec<_>>();
    let palette_bytes = palette
        .iter()
        .flat_map(|rgb| rgb.iter().copied())
        .collect::<Vec<_>>();
    let semantic = compile_semantics(spec, &cells, config.canonical)?;
    let semantic_bytes = serde_json::to_vec(&(
        &semantic.motion,
        &semantic.facing,
        &semantic.presence,
        &semantic.anchors,
        &semantic.contact_sets,
        &semantic.attachment_edges,
        &semantic.z_order,
        &semantic.cells,
    ))
    .map_err(|source| PoseToolError::Json {
        path: PathBuf::from("<semantic-hash>"),
        source,
    })?;
    Ok(CompiledPose {
        candidate_id: pose.candidate_id.clone(),
        semantic_id: pose.semantic_id.clone(),
        source_sha256: pose.source_sha256.clone(),
        source_size: [width, height],
        source_crop: crop,
        generation_rows,
        generated_size: [generation_cols, generation_rows],
        canonical_size: [config.canonical.cols, config.canonical.rows],
        root_anchor: config.canonical.root,
        canonical_shift,
        quantized_colors: config.quantized_colors,
        palette_color_count: palette.len(),
        palette_sha256: sha256_hex(&palette_bytes),
        cell_count: semantic.cells.len(),
        cell_sha256: sha256_hex(&cell_bytes),
        semantic_sha256: sha256_hex(&semantic_bytes),
        motion: semantic.motion,
        facing: semantic.facing,
        presence: semantic.presence,
        anchors: semantic.anchors,
        contact_sets: semantic.contact_sets,
        attachment_edges: semantic.attachment_edges,
        z_order: semantic.z_order,
        cells: semantic.cells,
    })
}

fn content_hash(archive: &CompiledArchive) -> Result<String> {
    let mut unhashed = archive.clone();
    unhashed.archive_sha256.clear();
    let bytes = serde_json::to_vec(&unhashed).map_err(|source| PoseToolError::Json {
        path: PathBuf::from("<archive-hash>"),
        source,
    })?;
    Ok(sha256_hex(&bytes))
}

fn normalize_path(path: &Path) -> PathBuf {
    let mut normalized = PathBuf::new();
    for component in path.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir => {
                normalized.pop();
            }
            other => normalized.push(other.as_os_str()),
        }
    }
    normalized
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn output_is_restricted_to_crate_target() {
        let archive = CompiledArchive {
            schema_version: 3,
            compiler_id: COMPILER_ID.to_string(),
            source_manifest_sha256: "test".to_string(),
            config: CompilerConfig::default(),
            catalog_count: 0,
            unique_geometry_count: 0,
            alias_count: 0,
            catalog: Vec::new(),
            poses: Vec::new(),
            aliases: Vec::new(),
            palette_color_count: 0,
            palette_sha256: "test".to_string(),
            archive_sha256: "test".to_string(),
        };
        let error = write_compiled_archive(&archive, "../outside.json").expect_err("restricted");
        assert!(matches!(error, PoseToolError::OutputOutsideTarget { .. }));
    }

    #[test]
    fn content_hash_ignores_only_its_own_field() {
        let mut archive = CompiledArchive {
            schema_version: 3,
            compiler_id: COMPILER_ID.to_string(),
            source_manifest_sha256: "test".to_string(),
            config: CompilerConfig::default(),
            catalog_count: 0,
            unique_geometry_count: 0,
            alias_count: 0,
            catalog: Vec::new(),
            poses: Vec::new(),
            aliases: Vec::new(),
            palette_color_count: 0,
            palette_sha256: "test".to_string(),
            archive_sha256: String::new(),
        };
        let first = content_hash(&archive).unwrap();
        archive.archive_sha256 = "different".to_string();
        assert_eq!(content_hash(&archive).unwrap(), first);
        archive.palette_sha256 = "changed".to_string();
        assert_ne!(content_hash(&archive).unwrap(), first);
    }
}
