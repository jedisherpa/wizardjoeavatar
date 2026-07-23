use image::{Rgba, RgbaImage};
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

/// Parameters for removing a flat sheet background from a pose source.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct IsolationConfig {
    /// RGB color of the source sheet/cell background.
    pub matte_rgb: [u8; 3],
    /// Maximum Euclidean RGB distance from `matte_rgb` that is considered matte.
    pub matte_tolerance: u16,
    /// Maximum channel spread for neutral sheet shadows connected to the canvas edge.
    pub neutral_shadow_max_chroma: u8,
    /// Minimum average channel value for a neutral sheet shadow.
    pub neutral_shadow_min_luma: u8,
    /// Optional source row below which neutral floor-shadow residue is removed.
    pub neutral_floor_shadow_start_y: Option<u32>,
    /// Maximum channel spread for floor shadows, independent of edge-matte cleanup.
    #[serde(default = "default_neutral_floor_shadow_max_chroma")]
    pub neutral_floor_shadow_max_chroma: u8,
    /// Minimum average channel value for the optional floor-shadow cleanup.
    pub neutral_floor_shadow_min_luma: u8,
    /// Large enclosed matte regions are sheet background trapped behind pale motion effects.
    #[serde(default = "default_enclosed_matte_component_min_pixels")]
    pub enclosed_matte_component_min_pixels: Option<u32>,
    /// Source-space regions where pale authored effects are recovered after base isolation.
    #[serde(default = "default_pale_effect_recovery_bounds")]
    pub pale_effect_recovery_bounds: [Option<ForegroundBounds>; 4],
    /// Source-space regions where matte-colored residue is removed even when enclosed.
    #[serde(default = "default_forced_matte_removal_bounds")]
    pub forced_matte_removal_bounds: [Option<ForegroundBounds>; 4],
    /// Source-space regions known to contain only blended sheet residue.
    #[serde(default = "default_forced_transparent_bounds")]
    pub forced_transparent_bounds: [Option<ForegroundBounds>; 4],
    /// Matte tolerance used only inside pale-effect recovery regions.
    #[serde(default = "default_pale_effect_matte_tolerance")]
    pub pale_effect_matte_tolerance: u16,
    /// Neutral-shadow chroma used only inside pale-effect recovery regions.
    #[serde(default = "default_pale_effect_neutral_shadow_max_chroma")]
    pub pale_effect_neutral_shadow_max_chroma: u8,
    /// Pixels at or below this alpha are treated as already transparent.
    pub transparent_alpha_max: u8,
}

impl Default for IsolationConfig {
    fn default() -> Self {
        Self {
            matte_rgb: [255, 255, 255],
            matte_tolerance: 18,
            neutral_shadow_max_chroma: 24,
            neutral_shadow_min_luma: 96,
            neutral_floor_shadow_start_y: None,
            neutral_floor_shadow_max_chroma: default_neutral_floor_shadow_max_chroma(),
            neutral_floor_shadow_min_luma: 48,
            enclosed_matte_component_min_pixels: default_enclosed_matte_component_min_pixels(),
            pale_effect_recovery_bounds: default_pale_effect_recovery_bounds(),
            forced_matte_removal_bounds: default_forced_matte_removal_bounds(),
            forced_transparent_bounds: default_forced_transparent_bounds(),
            pale_effect_matte_tolerance: default_pale_effect_matte_tolerance(),
            pale_effect_neutral_shadow_max_chroma: default_pale_effect_neutral_shadow_max_chroma(),
            transparent_alpha_max: 0,
        }
    }
}

const fn default_neutral_floor_shadow_max_chroma() -> u8 {
    48
}

const fn default_enclosed_matte_component_min_pixels() -> Option<u32> {
    Some(20_000)
}

const fn default_pale_effect_recovery_bounds() -> [Option<ForegroundBounds>; 4] {
    [None; 4]
}

const fn default_forced_matte_removal_bounds() -> [Option<ForegroundBounds>; 4] {
    [None; 4]
}

const fn default_forced_transparent_bounds() -> [Option<ForegroundBounds>; 4] {
    [None; 4]
}

const fn default_pale_effect_matte_tolerance() -> u16 {
    32
}

const fn default_pale_effect_neutral_shadow_max_chroma() -> u8 {
    0
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ForegroundBounds {
    pub left: u32,
    pub top: u32,
    pub right: u32,
    pub bottom: u32,
}

impl ForegroundBounds {
    pub fn width(self) -> u32 {
        self.right - self.left + 1
    }

    pub fn height(self) -> u32 {
        self.bottom - self.top + 1
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct IsolatedPose {
    /// Source-sized RGBA image. Background is represented only by `[0, 0, 0, 0]`.
    pub image: RgbaImage,
    pub foreground_pixels: u64,
    pub bounds: Option<ForegroundBounds>,
}

/// Removes only matte-colored pixels connected to the canvas edge.
///
/// Border connectivity is intentional. A global white-key operation would erase valid white
/// blocks inside the character, including eyes and beard highlights. Existing transparent pixels
/// are normalized to transparent black so evidence hashes do not depend on hidden RGB channels.
pub fn isolate_transparent(source: &RgbaImage, config: IsolationConfig) -> IsolatedPose {
    let width = source.width();
    let height = source.height();
    let mut removable = build_matte_removal_mask(source, config);
    recover_pale_effect_regions(source, config, &mut removable);
    force_remove_matte_regions(source, config, &mut removable);
    force_remove_regions(source, config, &mut removable);

    let mut image = RgbaImage::new(width, height);
    let mut foreground_pixels = 0_u64;
    let mut bounds = None;
    for y in 0..height {
        for x in 0..width {
            let source_pixel = *source.get_pixel(x, y);
            let remove = removable[index(x, y, width)]
                || source_pixel[3] <= config.transparent_alpha_max
                || is_floor_shadow(&source_pixel, y, config);
            if remove {
                image.put_pixel(x, y, Rgba([0, 0, 0, 0]));
                continue;
            }

            image.put_pixel(x, y, source_pixel);
            foreground_pixels += 1;
            bounds = Some(expand_foreground_bounds(bounds, x, y));
        }
    }

    IsolatedPose {
        image,
        foreground_pixels,
        bounds,
    }
}

fn build_matte_removal_mask(source: &RgbaImage, config: IsolationConfig) -> Vec<bool> {
    let width = source.width();
    let height = source.height();
    let pixel_count = (width as usize).saturating_mul(height as usize);
    let mut removable = vec![false; pixel_count];
    let mut queue = VecDeque::new();

    if width > 0 && height > 0 {
        for x in 0..width {
            enqueue_edge_candidate(source, x, 0, config, &mut removable, &mut queue);
            if height > 1 {
                enqueue_edge_candidate(source, x, height - 1, config, &mut removable, &mut queue);
            }
        }
        for y in 0..height {
            enqueue_edge_candidate(source, 0, y, config, &mut removable, &mut queue);
            if width > 1 {
                enqueue_edge_candidate(source, width - 1, y, config, &mut removable, &mut queue);
            }
        }
    }

    while let Some((x, y)) = queue.pop_front() {
        for (next_x, next_y) in neighbors(x, y, width, height) {
            let next_index = index(next_x, next_y, width);
            if !removable[next_index]
                && is_matte_candidate(source.get_pixel(next_x, next_y), config)
            {
                removable[next_index] = true;
                queue.push_back((next_x, next_y));
            }
        }
    }

    remove_large_enclosed_matte_components(source, config, &mut removable);
    removable
}

fn recover_pale_effect_regions(
    source: &RgbaImage,
    config: IsolationConfig,
    removable: &mut [bool],
) {
    if config
        .pale_effect_recovery_bounds
        .iter()
        .all(Option::is_none)
    {
        return;
    }
    let mut recovery_config = config;
    recovery_config.matte_tolerance = config.pale_effect_matte_tolerance;
    recovery_config.neutral_shadow_max_chroma = config.pale_effect_neutral_shadow_max_chroma;
    recovery_config.neutral_floor_shadow_start_y = None;
    recovery_config.pale_effect_recovery_bounds = [None; 4];
    recovery_config.forced_matte_removal_bounds = [None; 4];
    recovery_config.forced_transparent_bounds = [None; 4];
    let recovery_removable = build_matte_removal_mask(source, recovery_config);

    for bounds in config.pale_effect_recovery_bounds.into_iter().flatten() {
        if bounds.left > bounds.right
            || bounds.top > bounds.bottom
            || bounds.right >= source.width()
            || bounds.bottom >= source.height()
        {
            continue;
        }
        for y in bounds.top..=bounds.bottom {
            for x in bounds.left..=bounds.right {
                let pixel_index = index(x, y, source.width());
                removable[pixel_index] = recovery_removable[pixel_index];
            }
        }
    }
}

fn force_remove_matte_regions(source: &RgbaImage, config: IsolationConfig, removable: &mut [bool]) {
    for bounds in config.forced_matte_removal_bounds.into_iter().flatten() {
        if bounds.left > bounds.right
            || bounds.top > bounds.bottom
            || bounds.right >= source.width()
            || bounds.bottom >= source.height()
        {
            continue;
        }
        for y in bounds.top..=bounds.bottom {
            for x in bounds.left..=bounds.right {
                let pixel = source.get_pixel(x, y);
                if is_matte_candidate(pixel, config) {
                    removable[index(x, y, source.width())] = true;
                }
            }
        }
    }
}

fn force_remove_regions(source: &RgbaImage, config: IsolationConfig, removable: &mut [bool]) {
    for bounds in config.forced_transparent_bounds.into_iter().flatten() {
        if bounds.left > bounds.right
            || bounds.top > bounds.bottom
            || bounds.right >= source.width()
            || bounds.bottom >= source.height()
        {
            continue;
        }
        for y in bounds.top..=bounds.bottom {
            for x in bounds.left..=bounds.right {
                removable[index(x, y, source.width())] = true;
            }
        }
    }
}

fn is_floor_shadow(pixel: &Rgba<u8>, y: u32, config: IsolationConfig) -> bool {
    let Some(start_y) = config.neutral_floor_shadow_start_y else {
        return false;
    };
    if y < start_y {
        return false;
    }
    let minimum = *pixel.0[..3].iter().min().unwrap_or(&0);
    let maximum = *pixel.0[..3].iter().max().unwrap_or(&0);
    let luma = pixel.0[..3]
        .iter()
        .map(|channel| u16::from(*channel))
        .sum::<u16>()
        / 3;
    maximum.saturating_sub(minimum) <= config.neutral_floor_shadow_max_chroma
        && luma >= u16::from(config.neutral_floor_shadow_min_luma)
}

fn remove_large_enclosed_matte_components(
    source: &RgbaImage,
    config: IsolationConfig,
    removable: &mut [bool],
) {
    let Some(minimum_pixels) = config.enclosed_matte_component_min_pixels else {
        return;
    };
    if minimum_pixels == 0 {
        return;
    }

    let width = source.width();
    let height = source.height();
    let mut visited = vec![false; removable.len()];
    let mut queue = VecDeque::new();
    let mut component = Vec::new();

    for y in 0..height {
        for x in 0..width {
            let start = index(x, y, width);
            if removable[start]
                || visited[start]
                || !is_matte_candidate(source.get_pixel(x, y), config)
            {
                continue;
            }

            visited[start] = true;
            queue.push_back((x, y));
            component.clear();
            while let Some((component_x, component_y)) = queue.pop_front() {
                let component_index = index(component_x, component_y, width);
                component.push(component_index);
                for (next_x, next_y) in neighbors(component_x, component_y, width, height) {
                    let next_index = index(next_x, next_y, width);
                    if removable[next_index]
                        || visited[next_index]
                        || !is_matte_candidate(source.get_pixel(next_x, next_y), config)
                    {
                        continue;
                    }
                    visited[next_index] = true;
                    queue.push_back((next_x, next_y));
                }
            }

            if component.len() >= minimum_pixels as usize {
                for component_index in component.iter().copied() {
                    removable[component_index] = true;
                }
            }
        }
    }
}

fn enqueue_edge_candidate(
    source: &RgbaImage,
    x: u32,
    y: u32,
    config: IsolationConfig,
    removable: &mut [bool],
    queue: &mut VecDeque<(u32, u32)>,
) {
    let candidate_index = index(x, y, source.width());
    if !removable[candidate_index] && is_matte_candidate(source.get_pixel(x, y), config) {
        removable[candidate_index] = true;
        queue.push_back((x, y));
    }
}

fn is_matte_candidate(pixel: &Rgba<u8>, config: IsolationConfig) -> bool {
    if pixel[3] <= config.transparent_alpha_max {
        return true;
    }
    if is_within_matte_distance(pixel, config) {
        return true;
    }
    let minimum = *pixel.0[..3].iter().min().unwrap_or(&0);
    let maximum = *pixel.0[..3].iter().max().unwrap_or(&0);
    let luma = pixel.0[..3]
        .iter()
        .map(|channel| u16::from(*channel))
        .sum::<u16>()
        / 3;
    maximum.saturating_sub(minimum) <= config.neutral_shadow_max_chroma
        && luma >= u16::from(config.neutral_shadow_min_luma)
}

fn is_within_matte_distance(pixel: &Rgba<u8>, config: IsolationConfig) -> bool {
    let distance_squared = pixel.0[..3]
        .iter()
        .zip(config.matte_rgb)
        .map(|(actual, matte)| i32::from(*actual) - i32::from(matte))
        .map(|delta| (delta * delta) as u32)
        .sum::<u32>();
    distance_squared <= u32::from(config.matte_tolerance).pow(2)
}

fn neighbors(x: u32, y: u32, width: u32, height: u32) -> impl Iterator<Item = (u32, u32)> {
    let left = (x > 0).then_some((x.saturating_sub(1), y));
    let right = (x + 1 < width).then_some((x + 1, y));
    let up = (y > 0).then_some((x, y.saturating_sub(1)));
    let down = (y + 1 < height).then_some((x, y + 1));
    [left, right, up, down].into_iter().flatten()
}

fn expand_foreground_bounds(current: Option<ForegroundBounds>, x: u32, y: u32) -> ForegroundBounds {
    match current {
        Some(bounds) => ForegroundBounds {
            left: bounds.left.min(x),
            top: bounds.top.min(y),
            right: bounds.right.max(x),
            bottom: bounds.bottom.max(y),
        },
        None => ForegroundBounds {
            left: x,
            top: y,
            right: x,
            bottom: y,
        },
    }
}

fn index(x: u32, y: u32, width: u32) -> usize {
    (y as usize) * (width as usize) + (x as usize)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn removes_only_border_connected_white_matte() {
        let mut source = RgbaImage::from_pixel(5, 5, Rgba([255, 255, 255, 255]));
        for x in 1..=3 {
            source.put_pixel(x, 1, Rgba([0, 0, 0, 255]));
            source.put_pixel(x, 3, Rgba([0, 0, 0, 255]));
        }
        source.put_pixel(1, 2, Rgba([0, 0, 0, 255]));
        source.put_pixel(3, 2, Rgba([0, 0, 0, 255]));

        let isolated = isolate_transparent(&source, IsolationConfig::default());

        assert_eq!(isolated.image.get_pixel(0, 0), &Rgba([0, 0, 0, 0]));
        assert_eq!(
            isolated.image.get_pixel(2, 2),
            &Rgba([255, 255, 255, 255]),
            "an enclosed white character cell must not be keyed out"
        );
        assert_eq!(isolated.foreground_pixels, 9);
        assert_eq!(
            isolated.bounds,
            Some(ForegroundBounds {
                left: 1,
                top: 1,
                right: 3,
                bottom: 3,
            })
        );
    }

    #[test]
    fn tolerance_removes_near_white_sheet_pixels() {
        let mut source = RgbaImage::from_pixel(3, 1, Rgba([250, 252, 249, 255]));
        source.put_pixel(1, 0, Rgba([20, 40, 80, 255]));

        let isolated = isolate_transparent(
            &source,
            IsolationConfig {
                matte_tolerance: 12,
                ..IsolationConfig::default()
            },
        );

        assert_eq!(isolated.image.get_pixel(0, 0), &Rgba([0, 0, 0, 0]));
        assert_eq!(isolated.image.get_pixel(1, 0), &Rgba([20, 40, 80, 255]));
        assert_eq!(isolated.image.get_pixel(2, 0), &Rgba([0, 0, 0, 0]));
    }

    #[test]
    fn normalizes_hidden_rgb_of_existing_transparency() {
        let source = RgbaImage::from_pixel(1, 1, Rgba([91, 72, 53, 0]));

        let isolated = isolate_transparent(&source, IsolationConfig::default());

        assert_eq!(isolated.image.get_pixel(0, 0), &Rgba([0, 0, 0, 0]));
        assert_eq!(isolated.foreground_pixels, 0);
        assert_eq!(isolated.bounds, None);
    }

    #[test]
    fn removes_border_connected_neutral_sheet_shadow() {
        let mut source = RgbaImage::from_pixel(5, 3, Rgba([255, 255, 255, 255]));
        source.put_pixel(1, 2, Rgba([210, 208, 207, 255]));
        source.put_pixel(2, 2, Rgba([170, 168, 166, 255]));
        source.put_pixel(3, 2, Rgba([120, 119, 118, 255]));
        source.put_pixel(2, 1, Rgba([20, 80, 180, 255]));

        let isolated = isolate_transparent(&source, IsolationConfig::default());

        assert_eq!(isolated.foreground_pixels, 1);
        assert_eq!(isolated.image.get_pixel(2, 1), &Rgba([20, 80, 180, 255]));
    }

    #[test]
    fn optional_floor_cleanup_removes_detached_gray_without_erasing_colored_boot() {
        let mut source = RgbaImage::new(2, 2);
        source.put_pixel(0, 1, Rgba([90, 89, 88, 255]));
        source.put_pixel(1, 1, Rgba([90, 45, 10, 255]));
        let isolated = isolate_transparent(
            &source,
            IsolationConfig {
                neutral_floor_shadow_start_y: Some(1),
                ..IsolationConfig::default()
            },
        );
        assert_eq!(isolated.image.get_pixel(0, 1), &Rgba([0, 0, 0, 0]));
        assert_eq!(isolated.image.get_pixel(1, 1), &Rgba([90, 45, 10, 255]));
    }

    #[test]
    fn removes_large_enclosed_matte_without_erasing_small_white_detail() {
        let mut source = RgbaImage::from_pixel(11, 7, Rgba([255, 255, 255, 255]));
        for x in 1..=9 {
            source.put_pixel(x, 1, Rgba([20, 40, 80, 255]));
            source.put_pixel(x, 5, Rgba([20, 40, 80, 255]));
        }
        for y in 1..=5 {
            source.put_pixel(1, y, Rgba([20, 40, 80, 255]));
            source.put_pixel(9, y, Rgba([20, 40, 80, 255]));
        }
        for x in 6..=8 {
            source.put_pixel(x, 2, Rgba([20, 40, 80, 255]));
            source.put_pixel(x, 4, Rgba([20, 40, 80, 255]));
        }
        source.put_pixel(6, 3, Rgba([20, 40, 80, 255]));
        source.put_pixel(8, 3, Rgba([20, 40, 80, 255]));

        let isolated = isolate_transparent(
            &source,
            IsolationConfig {
                enclosed_matte_component_min_pixels: Some(10),
                ..IsolationConfig::default()
            },
        );

        assert_eq!(isolated.image.get_pixel(3, 3), &Rgba([0, 0, 0, 0]));
        assert_eq!(isolated.image.get_pixel(7, 3), &Rgba([255, 255, 255, 255]));
        assert_eq!(isolated.image.get_pixel(6, 3), &Rgba([20, 40, 80, 255]));
    }

    #[test]
    fn floor_chroma_is_independent_from_edge_shadow_chroma() {
        let mut source = RgbaImage::new(1, 2);
        source.put_pixel(0, 0, Rgba([200, 180, 170, 255]));
        source.put_pixel(0, 1, Rgba([100, 70, 60, 255]));

        let isolated = isolate_transparent(
            &source,
            IsolationConfig {
                neutral_shadow_max_chroma: 0,
                neutral_floor_shadow_start_y: Some(1),
                neutral_floor_shadow_max_chroma: 48,
                ..IsolationConfig::default()
            },
        );

        assert_eq!(isolated.image.get_pixel(0, 0), &Rgba([200, 180, 170, 255]));
        assert_eq!(isolated.image.get_pixel(0, 1), &Rgba([0, 0, 0, 0]));
    }

    #[test]
    fn recovers_pale_authored_effect_only_inside_declared_region() {
        let mut source = RgbaImage::from_pixel(5, 3, Rgba([255, 255, 255, 255]));
        source.put_pixel(1, 1, Rgba([230, 220, 210, 255]));
        source.put_pixel(3, 1, Rgba([230, 220, 210, 255]));

        let isolated = isolate_transparent(
            &source,
            IsolationConfig {
                matte_tolerance: 96,
                neutral_shadow_max_chroma: 24,
                pale_effect_recovery_bounds: [
                    Some(ForegroundBounds {
                        left: 1,
                        top: 1,
                        right: 1,
                        bottom: 1,
                    }),
                    None,
                    None,
                    None,
                ],
                pale_effect_matte_tolerance: 10,
                pale_effect_neutral_shadow_max_chroma: 0,
                ..IsolationConfig::default()
            },
        );

        assert_eq!(isolated.image.get_pixel(1, 1), &Rgba([230, 220, 210, 255]));
        assert_eq!(isolated.image.get_pixel(3, 1), &Rgba([0, 0, 0, 0]));
    }

    #[test]
    fn forced_matte_region_removes_only_declared_enclosed_pixels() {
        let mut source = RgbaImage::from_pixel(7, 5, Rgba([255, 255, 255, 255]));
        for x in 1..=5 {
            source.put_pixel(x, 1, Rgba([20, 40, 80, 255]));
            source.put_pixel(x, 3, Rgba([20, 40, 80, 255]));
        }
        for y in 1..=3 {
            source.put_pixel(1, y, Rgba([20, 40, 80, 255]));
            source.put_pixel(5, y, Rgba([20, 40, 80, 255]));
        }
        source.put_pixel(2, 2, Rgba([190, 188, 187, 255]));

        let isolated = isolate_transparent(
            &source,
            IsolationConfig {
                enclosed_matte_component_min_pixels: None,
                forced_matte_removal_bounds: [
                    Some(ForegroundBounds {
                        left: 2,
                        top: 2,
                        right: 2,
                        bottom: 2,
                    }),
                    None,
                    None,
                    None,
                ],
                ..IsolationConfig::default()
            },
        );

        assert_eq!(isolated.image.get_pixel(2, 2), &Rgba([0, 0, 0, 0]));
        assert_eq!(isolated.image.get_pixel(3, 2), &Rgba([255, 255, 255, 255]));
        assert_eq!(isolated.image.get_pixel(4, 2), &Rgba([255, 255, 255, 255]));
    }

    #[test]
    fn forced_transparent_region_removes_blended_residue_regardless_of_color() {
        let mut source = RgbaImage::new(4, 2);
        source.put_pixel(0, 0, Rgba([80, 65, 50, 255]));
        source.put_pixel(1, 0, Rgba([20, 90, 180, 255]));

        let isolated = isolate_transparent(
            &source,
            IsolationConfig {
                forced_transparent_bounds: [
                    Some(ForegroundBounds {
                        left: 0,
                        top: 0,
                        right: 0,
                        bottom: 0,
                    }),
                    None,
                    None,
                    None,
                ],
                ..IsolationConfig::default()
            },
        );

        assert_eq!(isolated.image.get_pixel(0, 0), &Rgba([0, 0, 0, 0]));
        assert_eq!(isolated.image.get_pixel(1, 0), &Rgba([20, 90, 180, 255]));
    }

    #[test]
    fn supports_empty_images() {
        let source = RgbaImage::new(0, 0);

        let isolated = isolate_transparent(&source, IsolationConfig::default());

        assert_eq!(isolated.image.dimensions(), (0, 0));
        assert_eq!(isolated.foreground_pixels, 0);
        assert_eq!(isolated.bounds, None);
    }
}
