use image::{Rgba, RgbaImage};
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct VerificationConfig {
    /// Alpha values at or above this threshold count as occupied foreground.
    pub foreground_alpha_threshold: u8,
    /// Maximum Manhattan RGB distance for a foreground pixel to count as a color match.
    pub color_match_tolerance: u16,
}

impl Default for VerificationConfig {
    fn default() -> Self {
        Self {
            foreground_alpha_threshold: 1,
            color_match_tolerance: 24,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
pub struct PoseGraphMetrics {
    pub source_foreground_pixels: u64,
    pub graph_foreground_pixels: u64,
    pub intersection_pixels: u64,
    pub union_pixels: u64,
    pub missing_pixels: u64,
    pub extra_pixels: u64,
    pub color_matched_pixels: u64,
    pub color_mismatched_pixels: u64,
    pub silhouette_precision: f64,
    pub silhouette_recall: f64,
    pub silhouette_iou: f64,
    /// Fraction of the foreground union whose RGB value is within the configured tolerance.
    pub foreground_color_match_ratio: f64,
    /// Mean RGB similarity over the foreground union. Missing and extra pixels contribute zero.
    pub foreground_color_fidelity: f64,
}

impl PoseGraphMetrics {
    pub fn passes(self, minimum: f64) -> bool {
        self.source_foreground_pixels > 0
            && self.graph_foreground_pixels > 0
            && self.silhouette_iou >= minimum
            && self.foreground_color_match_ratio >= minimum
            && self.foreground_color_fidelity >= minimum
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, thiserror::Error)]
pub enum VerificationError {
    #[error(
        "source dimensions {source_width}x{source_height} do not match graph dimensions {graph_width}x{graph_height}"
    )]
    DimensionMismatch {
        source_width: u32,
        source_height: u32,
        graph_width: u32,
        graph_height: u32,
    },
}

/// Compares an isolated source and an independently projected pose graph.
///
/// All silhouette metrics use alpha occupancy only. Color fidelity is averaged over the union of
/// occupied source and graph pixels; a missing or extra pixel scores zero. Transparent background
/// is never included, so a large white canvas cannot inflate the result.
pub fn verify_pose_graph(
    isolated_source: &RgbaImage,
    projected_graph: &RgbaImage,
    config: VerificationConfig,
) -> Result<PoseGraphMetrics, VerificationError> {
    validate_matching_dimensions(isolated_source, projected_graph)?;

    let mut source_foreground_pixels = 0_u64;
    let mut graph_foreground_pixels = 0_u64;
    let mut intersection_pixels = 0_u64;
    let mut union_pixels = 0_u64;
    let mut missing_pixels = 0_u64;
    let mut extra_pixels = 0_u64;
    let mut color_matched_pixels = 0_u64;
    let mut color_mismatched_pixels = 0_u64;
    let mut color_similarity_sum = 0.0_f64;

    for (source, graph) in isolated_source.pixels().zip(projected_graph.pixels()) {
        let source_present = is_foreground(source, config.foreground_alpha_threshold);
        let graph_present = is_foreground(graph, config.foreground_alpha_threshold);

        source_foreground_pixels += u64::from(source_present);
        graph_foreground_pixels += u64::from(graph_present);

        match (source_present, graph_present) {
            (true, true) => {
                intersection_pixels += 1;
                union_pixels += 1;
                let distance = rgb_manhattan_distance(source, graph);
                if distance <= config.color_match_tolerance {
                    color_matched_pixels += 1;
                } else {
                    color_mismatched_pixels += 1;
                }
                color_similarity_sum += rgb_similarity(source, graph);
            }
            (true, false) => {
                union_pixels += 1;
                missing_pixels += 1;
            }
            (false, true) => {
                union_pixels += 1;
                extra_pixels += 1;
            }
            (false, false) => {}
        }
    }

    Ok(PoseGraphMetrics {
        source_foreground_pixels,
        graph_foreground_pixels,
        intersection_pixels,
        union_pixels,
        missing_pixels,
        extra_pixels,
        color_matched_pixels,
        color_mismatched_pixels,
        silhouette_precision: ratio_or_identity(intersection_pixels, graph_foreground_pixels),
        silhouette_recall: ratio_or_identity(intersection_pixels, source_foreground_pixels),
        silhouette_iou: ratio_or_identity(intersection_pixels, union_pixels),
        foreground_color_match_ratio: ratio_or_identity(color_matched_pixels, union_pixels),
        foreground_color_fidelity: if union_pixels == 0 {
            1.0
        } else {
            color_similarity_sum / union_pixels as f64
        },
    })
}

pub(crate) fn validate_matching_dimensions(
    source: &RgbaImage,
    graph: &RgbaImage,
) -> Result<(), VerificationError> {
    if source.dimensions() == graph.dimensions() {
        return Ok(());
    }
    Err(VerificationError::DimensionMismatch {
        source_width: source.width(),
        source_height: source.height(),
        graph_width: graph.width(),
        graph_height: graph.height(),
    })
}

pub(crate) fn is_foreground(pixel: &Rgba<u8>, alpha_threshold: u8) -> bool {
    pixel[3] >= alpha_threshold
}

pub(crate) fn rgb_manhattan_distance(left: &Rgba<u8>, right: &Rgba<u8>) -> u16 {
    left.0[..3]
        .iter()
        .zip(&right.0[..3])
        .map(|(left, right)| u16::from(left.abs_diff(*right)))
        .sum()
}

fn rgb_similarity(left: &Rgba<u8>, right: &Rgba<u8>) -> f64 {
    1.0 - f64::from(rgb_manhattan_distance(left, right)) / (3.0 * 255.0)
}

fn ratio_or_identity(numerator: u64, denominator: u64) -> f64 {
    if denominator == 0 {
        1.0
    } else {
        numerator as f64 / denominator as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn perfect_foreground_scores_one() {
        let mut source = RgbaImage::new(4, 4);
        source.put_pixel(1, 1, Rgba([10, 20, 30, 255]));
        source.put_pixel(2, 2, Rgba([80, 90, 100, 255]));
        let graph = source.clone();

        let metrics = verify_pose_graph(&source, &graph, VerificationConfig::default()).unwrap();

        assert_eq!(metrics.source_foreground_pixels, 2);
        assert_eq!(metrics.graph_foreground_pixels, 2);
        assert_eq!(metrics.silhouette_precision, 1.0);
        assert_eq!(metrics.silhouette_recall, 1.0);
        assert_eq!(metrics.silhouette_iou, 1.0);
        assert_eq!(metrics.foreground_color_match_ratio, 1.0);
        assert_eq!(metrics.foreground_color_fidelity, 1.0);
        assert!(metrics.passes(0.95));
    }

    #[test]
    fn white_background_cannot_inflate_color_fidelity() {
        use crate::isolation::{isolate_transparent, IsolationConfig};

        let mut source = RgbaImage::from_pixel(100, 100, Rgba([255, 255, 255, 255]));
        let mut graph = RgbaImage::new(100, 100);
        source.put_pixel(50, 50, Rgba([255, 0, 0, 255]));
        graph.put_pixel(50, 50, Rgba([0, 0, 255, 255]));
        let isolated = isolate_transparent(&source, IsolationConfig::default());

        let metrics =
            verify_pose_graph(&isolated.image, &graph, VerificationConfig::default()).unwrap();

        assert_eq!(metrics.union_pixels, 1);
        assert_eq!(metrics.color_mismatched_pixels, 1);
        assert_eq!(metrics.foreground_color_match_ratio, 0.0);
        assert!((metrics.foreground_color_fidelity - (1.0 / 3.0)).abs() < 1.0e-12);
        assert!(!metrics.passes(0.95));
    }

    #[test]
    fn missing_and_extra_pixels_score_zero_in_color_union() {
        let mut source = RgbaImage::new(3, 1);
        let mut graph = RgbaImage::new(3, 1);
        source.put_pixel(0, 0, Rgba([40, 80, 120, 255]));
        source.put_pixel(1, 0, Rgba([40, 80, 120, 255]));
        graph.put_pixel(0, 0, Rgba([40, 80, 120, 255]));
        graph.put_pixel(2, 0, Rgba([40, 80, 120, 255]));

        let metrics = verify_pose_graph(&source, &graph, VerificationConfig::default()).unwrap();

        assert_eq!(metrics.intersection_pixels, 1);
        assert_eq!(metrics.union_pixels, 3);
        assert_eq!(metrics.missing_pixels, 1);
        assert_eq!(metrics.extra_pixels, 1);
        assert_eq!(metrics.silhouette_precision, 0.5);
        assert_eq!(metrics.silhouette_recall, 0.5);
        assert_eq!(metrics.silhouette_iou, 1.0 / 3.0);
        assert_eq!(metrics.foreground_color_match_ratio, 1.0 / 3.0);
        assert_eq!(metrics.foreground_color_fidelity, 1.0 / 3.0);
    }

    #[test]
    fn empty_transparent_images_are_identical_without_background_credit() {
        let source = RgbaImage::new(8, 8);
        let graph = RgbaImage::new(8, 8);

        let metrics = verify_pose_graph(&source, &graph, VerificationConfig::default()).unwrap();

        assert_eq!(metrics.union_pixels, 0);
        assert_eq!(metrics.silhouette_precision, 1.0);
        assert_eq!(metrics.silhouette_recall, 1.0);
        assert_eq!(metrics.silhouette_iou, 1.0);
        assert_eq!(metrics.foreground_color_match_ratio, 1.0);
        assert_eq!(metrics.foreground_color_fidelity, 1.0);
        assert!(!metrics.passes(0.95), "an empty pose cannot be admitted");
    }

    #[test]
    fn rejects_dimension_mismatch() {
        let source = RgbaImage::new(8, 8);
        let graph = RgbaImage::new(7, 8);

        let error = verify_pose_graph(&source, &graph, VerificationConfig::default()).unwrap_err();

        assert_eq!(
            error,
            VerificationError::DimensionMismatch {
                source_width: 8,
                source_height: 8,
                graph_width: 7,
                graph_height: 8,
            }
        );
    }

    #[test]
    fn alpha_threshold_controls_foreground_occupancy() {
        let source = RgbaImage::from_pixel(1, 1, Rgba([10, 20, 30, 127]));
        let graph = RgbaImage::new(1, 1);

        let metrics = verify_pose_graph(
            &source,
            &graph,
            VerificationConfig {
                foreground_alpha_threshold: 128,
                ..VerificationConfig::default()
            },
        )
        .unwrap();

        assert_eq!(metrics.source_foreground_pixels, 0);
        assert_eq!(metrics.union_pixels, 0);
    }
}
