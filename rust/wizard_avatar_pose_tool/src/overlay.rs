use crate::verification::{
    is_foreground, rgb_manhattan_distance, validate_matching_dimensions, VerificationConfig,
    VerificationError,
};
use image::{Rgba, RgbaImage};
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct OverlayPalette {
    /// Source foreground absent from the graph.
    pub missing: Rgba<u8>,
    /// Graph foreground absent from the source.
    pub extra: Rgba<u8>,
    /// Occupied in both images but outside the configured color tolerance.
    pub mismatched: Rgba<u8>,
    /// Alpha used to show correctly aligned source color without obscuring the reference.
    pub matched_alpha: u8,
}

impl Default for OverlayPalette {
    fn default() -> Self {
        Self {
            missing: Rgba([255, 0, 255, 216]),
            extra: Rgba([0, 224, 255, 216]),
            mismatched: Rgba([255, 144, 0, 216]),
            matched_alpha: 88,
        }
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct OverlayCounts {
    pub matched: u64,
    pub missing: u64,
    pub extra: u64,
    pub mismatched: u64,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TransparentOverlay {
    pub image: RgbaImage,
    pub counts: OverlayCounts,
}

/// Places the projected pixel graph directly over the source PNG at a fixed opacity.
///
/// This is the visual admission artifact: a displaced graph produces doubled edges, while an
/// aligned graph settles directly into the original source pixels.
pub fn composite_graph_over_source(
    normalized_source_png: &RgbaImage,
    projected_graph: &RgbaImage,
    graph_opacity: u8,
) -> Result<RgbaImage, VerificationError> {
    validate_matching_dimensions(normalized_source_png, projected_graph)?;
    let mut composite = normalized_source_png.clone();
    for (output, graph) in composite.pixels_mut().zip(projected_graph.pixels()) {
        if graph[3] == 0 {
            continue;
        }
        let layer_alpha = (u32::from(graph[3]) * u32::from(graph_opacity) / 255) as u8;
        *output = alpha_over(*output, *graph, layer_alpha);
    }
    Ok(composite)
}

fn alpha_over(base: Rgba<u8>, layer: Rgba<u8>, layer_alpha: u8) -> Rgba<u8> {
    let alpha = u32::from(layer_alpha);
    let inverse = 255 - alpha;
    Rgba([
        ((u32::from(layer[0]) * alpha + u32::from(base[0]) * inverse + 127) / 255) as u8,
        ((u32::from(layer[1]) * alpha + u32::from(base[1]) * inverse + 127) / 255) as u8,
        ((u32::from(layer[2]) * alpha + u32::from(base[2]) * inverse + 127) / 255) as u8,
        base[3].max(layer_alpha),
    ])
}

/// Creates a source-sized transparent verification overlay.
///
/// Correct cells retain their source RGB at low alpha. Missing, extra, and color-mismatched cells
/// use distinct high-visibility colors. Background remains fully transparent.
pub fn build_transparent_overlay(
    isolated_source: &RgbaImage,
    projected_graph: &RgbaImage,
    verification: VerificationConfig,
    palette: OverlayPalette,
) -> Result<TransparentOverlay, VerificationError> {
    validate_matching_dimensions(isolated_source, projected_graph)?;
    let mut image = RgbaImage::new(isolated_source.width(), isolated_source.height());
    let mut counts = OverlayCounts::default();

    for y in 0..isolated_source.height() {
        for x in 0..isolated_source.width() {
            let source = isolated_source.get_pixel(x, y);
            let graph = projected_graph.get_pixel(x, y);
            let source_present = is_foreground(source, verification.foreground_alpha_threshold);
            let graph_present = is_foreground(graph, verification.foreground_alpha_threshold);

            let output = match (source_present, graph_present) {
                (false, false) => Rgba([0, 0, 0, 0]),
                (true, false) => {
                    counts.missing += 1;
                    palette.missing
                }
                (false, true) => {
                    counts.extra += 1;
                    palette.extra
                }
                (true, true)
                    if rgb_manhattan_distance(source, graph)
                        <= verification.color_match_tolerance =>
                {
                    counts.matched += 1;
                    Rgba([
                        source[0],
                        source[1],
                        source[2],
                        source[3].min(palette.matched_alpha),
                    ])
                }
                (true, true) => {
                    counts.mismatched += 1;
                    palette.mismatched
                }
            };
            image.put_pixel(x, y, output);
        }
    }

    Ok(TransparentOverlay { image, counts })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn classifies_every_foreground_relationship_with_distinct_rgba() {
        let mut source = RgbaImage::new(5, 1);
        let mut graph = RgbaImage::new(5, 1);
        source.put_pixel(0, 0, Rgba([20, 40, 60, 255]));
        graph.put_pixel(0, 0, Rgba([20, 40, 60, 255]));
        source.put_pixel(1, 0, Rgba([200, 10, 10, 255]));
        graph.put_pixel(1, 0, Rgba([10, 10, 200, 255]));
        source.put_pixel(2, 0, Rgba([20, 200, 20, 255]));
        graph.put_pixel(3, 0, Rgba([200, 200, 20, 255]));

        let palette = OverlayPalette::default();
        let overlay =
            build_transparent_overlay(&source, &graph, VerificationConfig::default(), palette)
                .unwrap();

        assert_eq!(
            overlay.image.get_pixel(0, 0),
            &Rgba([20, 40, 60, palette.matched_alpha])
        );
        assert_eq!(overlay.image.get_pixel(1, 0), &palette.mismatched);
        assert_eq!(overlay.image.get_pixel(2, 0), &palette.missing);
        assert_eq!(overlay.image.get_pixel(3, 0), &palette.extra);
        assert_eq!(overlay.image.get_pixel(4, 0), &Rgba([0, 0, 0, 0]));
        assert_eq!(
            overlay.counts,
            OverlayCounts {
                matched: 1,
                missing: 1,
                extra: 1,
                mismatched: 1,
            }
        );
        assert_ne!(palette.missing, palette.extra);
        assert_ne!(palette.missing, palette.mismatched);
        assert_ne!(palette.extra, palette.mismatched);
    }

    #[test]
    fn matched_cells_are_translucent_and_background_is_clear() {
        let mut source = RgbaImage::new(2, 1);
        let mut graph = RgbaImage::new(2, 1);
        source.put_pixel(0, 0, Rgba([1, 2, 3, 255]));
        graph.put_pixel(0, 0, Rgba([1, 2, 3, 255]));

        let overlay = build_transparent_overlay(
            &source,
            &graph,
            VerificationConfig::default(),
            OverlayPalette::default(),
        )
        .unwrap();

        assert!(overlay.image.get_pixel(0, 0)[3] > 0);
        assert!(overlay.image.get_pixel(0, 0)[3] < 255);
        assert_eq!(overlay.image.get_pixel(1, 0), &Rgba([0, 0, 0, 0]));
    }

    #[test]
    fn color_tolerance_controls_match_classification() {
        let source = RgbaImage::from_pixel(1, 1, Rgba([100, 100, 100, 255]));
        let graph = RgbaImage::from_pixel(1, 1, Rgba([104, 103, 102, 255]));

        let accepted = build_transparent_overlay(
            &source,
            &graph,
            VerificationConfig {
                color_match_tolerance: 9,
                ..VerificationConfig::default()
            },
            OverlayPalette::default(),
        )
        .unwrap();
        let rejected = build_transparent_overlay(
            &source,
            &graph,
            VerificationConfig {
                color_match_tolerance: 8,
                ..VerificationConfig::default()
            },
            OverlayPalette::default(),
        )
        .unwrap();

        assert_eq!(accepted.counts.matched, 1);
        assert_eq!(rejected.counts.mismatched, 1);
    }

    #[test]
    fn rejects_dimension_mismatch() {
        let source = RgbaImage::new(4, 4);
        let graph = RgbaImage::new(4, 3);

        let result = build_transparent_overlay(
            &source,
            &graph,
            VerificationConfig::default(),
            OverlayPalette::default(),
        );

        assert!(matches!(
            result,
            Err(VerificationError::DimensionMismatch { .. })
        ));
    }

    #[test]
    fn direct_composite_keeps_identical_pixels_visually_stable() {
        let source = RgbaImage::from_pixel(1, 1, Rgba([20, 80, 160, 255]));
        let graph = source.clone();
        let composite = composite_graph_over_source(&source, &graph, 128).unwrap();
        assert_eq!(composite, source);
    }
}
