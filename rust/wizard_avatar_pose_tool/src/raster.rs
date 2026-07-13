use crate::error::{PoseToolError, Result};
use crate::model::{CanonicalConfig, CellPayload, CropBounds, Point};
use std::collections::VecDeque;

#[derive(Clone, Copy, Debug)]
struct ComponentBounds {
    left: u32,
    top: u32,
    right: u32,
    bottom: u32,
}

#[derive(Debug)]
struct MaskComponent {
    pixels: Vec<usize>,
    bounds: ComponentBounds,
}

pub fn white_distance_mask(
    pixels: &[[u8; 3]],
    width: u32,
    height: u32,
    threshold: u16,
) -> Result<Vec<u8>> {
    validate_len(pixels.len(), width, height, "RGB image")?;
    let threshold_squared = u32::from(threshold).pow(2);
    Ok(pixels
        .iter()
        .map(|rgb| {
            let red = u32::from(255 - rgb[0]);
            let green = u32::from(255 - rgb[1]);
            let blue = u32::from(255 - rgb[2]);
            if red * red + green * green + blue * blue >= threshold_squared {
                255
            } else {
                0
            }
        })
        .collect())
}

pub fn fill_subject_holes(mask: &[u8], width: u32, height: u32) -> Result<Vec<u8>> {
    validate_len(mask.len(), width, height, "mask")?;
    if width == 0 || height == 0 {
        return Err(PoseToolError::Raster(
            "mask dimensions must be non-zero".to_string(),
        ));
    }
    let mut exterior = vec![false; mask.len()];
    let mut queue = VecDeque::new();
    let enqueue = |x: u32, y: u32, exterior: &mut [bool], queue: &mut VecDeque<(u32, u32)>| {
        let index = index(x, y, width);
        if mask[index] == 0 && !exterior[index] {
            exterior[index] = true;
            queue.push_back((x, y));
        }
    };

    for x in 0..width {
        enqueue(x, 0, &mut exterior, &mut queue);
        enqueue(x, height - 1, &mut exterior, &mut queue);
    }
    for y in 0..height {
        enqueue(0, y, &mut exterior, &mut queue);
        enqueue(width - 1, y, &mut exterior, &mut queue);
    }

    while let Some((x, y)) = queue.pop_front() {
        if x + 1 < width {
            enqueue(x + 1, y, &mut exterior, &mut queue);
        }
        if x > 0 {
            enqueue(x - 1, y, &mut exterior, &mut queue);
        }
        if y + 1 < height {
            enqueue(x, y + 1, &mut exterior, &mut queue);
        }
        if y > 0 {
            enqueue(x, y - 1, &mut exterior, &mut queue);
        }
    }

    Ok(mask
        .iter()
        .zip(exterior)
        .map(
            |(value, is_exterior)| {
                if *value != 0 || !is_exterior {
                    255
                } else {
                    0
                }
            },
        )
        .collect())
}

pub fn retain_subject_components(mask: &[u8], width: u32, height: u32) -> Result<Vec<u8>> {
    validate_len(mask.len(), width, height, "mask")?;
    let mut visited = vec![false; mask.len()];
    let mut components = Vec::new();
    for y in 0..height {
        for x in 0..width {
            let start = index(x, y, width);
            if mask[start] == 0 || visited[start] {
                continue;
            }
            visited[start] = true;
            let mut queue = VecDeque::from([(x, y)]);
            let mut pixels = Vec::new();
            let mut bounds = ComponentBounds {
                left: x,
                top: y,
                right: x,
                bottom: y,
            };
            while let Some((cx, cy)) = queue.pop_front() {
                pixels.push(index(cx, cy, width));
                bounds.left = bounds.left.min(cx);
                bounds.top = bounds.top.min(cy);
                bounds.right = bounds.right.max(cx);
                bounds.bottom = bounds.bottom.max(cy);
                for dy in -1_i32..=1 {
                    for dx in -1_i32..=1 {
                        if dx == 0 && dy == 0 {
                            continue;
                        }
                        let nx = cx as i32 + dx;
                        let ny = cy as i32 + dy;
                        if nx < 0 || ny < 0 || nx >= width as i32 || ny >= height as i32 {
                            continue;
                        }
                        let next = index(nx as u32, ny as u32, width);
                        if mask[next] != 0 && !visited[next] {
                            visited[next] = true;
                            queue.push_back((nx as u32, ny as u32));
                        }
                    }
                }
            }
            components.push(MaskComponent { pixels, bounds });
        }
    }
    let primary = components
        .iter()
        .max_by_key(|component| component.pixels.len())
        .ok_or_else(|| PoseToolError::Raster("image contains no detectable subject".to_string()))?;
    let proximity = width.max(height).div_ceil(9);
    let minimum_detail = (primary.pixels.len() / 600).max(4);
    let mut retained = vec![0_u8; mask.len()];
    for component in &components {
        let horizontal_gap = if component.bounds.right < primary.bounds.left {
            primary.bounds.left.saturating_sub(component.bounds.right)
        } else if component.bounds.left > primary.bounds.right {
            component.bounds.left.saturating_sub(primary.bounds.right)
        } else {
            0
        };
        let vertically_relevant = component.bounds.bottom <= primary.bounds.bottom;
        let is_primary = std::ptr::eq(component, primary);
        let is_near_detail = component.pixels.len() >= minimum_detail
            && horizontal_gap <= proximity
            && vertically_relevant;
        if is_primary || is_near_detail {
            for pixel in &component.pixels {
                retained[*pixel] = 255;
            }
        }
    }
    Ok(retained)
}

pub(crate) fn subject_bounds(mask: &[u8], width: u32, height: u32) -> Result<CropBounds> {
    validate_len(mask.len(), width, height, "mask")?;
    let mut bounds: Option<CropBounds> = None;
    for y in 0..height {
        for x in 0..width {
            if mask[index(x, y, width)] == 0 {
                continue;
            }
            bounds = Some(match bounds {
                Some(current) => CropBounds {
                    left: current.left.min(x),
                    top: current.top.min(y),
                    right: current.right.max(x),
                    bottom: current.bottom.max(y),
                },
                None => CropBounds {
                    left: x,
                    top: y,
                    right: x,
                    bottom: y,
                },
            });
        }
    }
    bounds.ok_or_else(|| PoseToolError::Raster("image contains no detectable subject".to_string()))
}

pub(crate) fn expand_bounds(
    bounds: CropBounds,
    width: u32,
    height: u32,
    margin: u32,
) -> CropBounds {
    CropBounds {
        left: bounds.left.saturating_sub(margin),
        top: bounds.top.saturating_sub(margin),
        right: bounds.right.saturating_add(margin).min(width - 1),
        bottom: bounds.bottom.saturating_add(margin).min(height - 1),
    }
}

pub(crate) fn crop_rgb(
    pixels: &[[u8; 3]],
    width: u32,
    height: u32,
    bounds: CropBounds,
) -> Result<Vec<[u8; 3]>> {
    validate_len(pixels.len(), width, height, "RGB image")?;
    validate_bounds(bounds, width, height)?;
    let mut cropped = Vec::with_capacity((bounds.width() * bounds.height()) as usize);
    for y in bounds.top..=bounds.bottom {
        for x in bounds.left..=bounds.right {
            cropped.push(pixels[index(x, y, width)]);
        }
    }
    Ok(cropped)
}

pub(crate) fn crop_gray(
    pixels: &[u8],
    width: u32,
    height: u32,
    bounds: CropBounds,
) -> Result<Vec<u8>> {
    validate_len(pixels.len(), width, height, "gray image")?;
    validate_bounds(bounds, width, height)?;
    let mut cropped = Vec::with_capacity((bounds.width() * bounds.height()) as usize);
    for y in bounds.top..=bounds.bottom {
        for x in bounds.left..=bounds.right {
            cropped.push(pixels[index(x, y, width)]);
        }
    }
    Ok(cropped)
}

pub fn box_resize_rgb(
    source: &[[u8; 3]],
    source_width: u32,
    source_height: u32,
    target_width: u32,
    target_height: u32,
) -> Result<Vec<[u8; 3]>> {
    validate_resize(
        source.len(),
        source_width,
        source_height,
        target_width,
        target_height,
    )?;
    let mut output = Vec::with_capacity((target_width * target_height) as usize);
    for target_y in 0..target_height {
        for target_x in 0..target_width {
            let mut sums = [0_u64; 3];
            let mut total_weight = 0_u64;
            for_each_box_sample(
                source_width,
                source_height,
                target_width,
                target_height,
                target_x,
                target_y,
                |source_x, source_y, weight| {
                    let rgb = source[index(source_x, source_y, source_width)];
                    for channel in 0..3 {
                        sums[channel] += u64::from(rgb[channel]) * weight;
                    }
                    total_weight += weight;
                },
            );
            output.push([
                rounded_average(sums[0], total_weight),
                rounded_average(sums[1], total_weight),
                rounded_average(sums[2], total_weight),
            ]);
        }
    }
    Ok(output)
}

pub fn box_resize_gray(
    source: &[u8],
    source_width: u32,
    source_height: u32,
    target_width: u32,
    target_height: u32,
) -> Result<Vec<u8>> {
    validate_resize(
        source.len(),
        source_width,
        source_height,
        target_width,
        target_height,
    )?;
    let mut output = Vec::with_capacity((target_width * target_height) as usize);
    for target_y in 0..target_height {
        for target_x in 0..target_width {
            let mut sum = 0_u64;
            let mut total_weight = 0_u64;
            for_each_box_sample(
                source_width,
                source_height,
                target_width,
                target_height,
                target_x,
                target_y,
                |source_x, source_y, weight| {
                    sum += u64::from(source[index(source_x, source_y, source_width)]) * weight;
                    total_weight += weight;
                },
            );
            output.push(rounded_average(sum, total_weight));
        }
    }
    Ok(output)
}

pub fn canonicalize_cells(
    pose_id: &str,
    cells: &[CellPayload],
    local_root: Point,
    canonical: CanonicalConfig,
) -> Result<(Point, Vec<CellPayload>)> {
    let shift = Point {
        x: canonical.root.x - local_root.x,
        y: canonical.root.y - local_root.y,
    };
    let mut normalized = Vec::with_capacity(cells.len());
    for cell in cells {
        let x = cell.x + shift.x;
        let y = cell.y + shift.y;
        if x < 0 || y < 0 || x >= canonical.cols as i32 || y >= canonical.rows as i32 {
            return Err(PoseToolError::CanonicalOverflow {
                pose_id: pose_id.to_string(),
                x,
                y,
            });
        }
        normalized.push(CellPayload {
            x,
            y,
            rgb: cell.rgb,
        });
    }
    normalized.sort_by_key(|cell| (cell.y, cell.x, cell.rgb));
    Ok((shift, normalized))
}

pub(crate) fn round_ratio_ties_even(numerator: u64, denominator: u64) -> u32 {
    let quotient = numerator / denominator;
    let remainder = numerator % denominator;
    let doubled = remainder * 2;
    let rounded = if doubled > denominator || doubled == denominator && quotient % 2 == 1 {
        quotient + 1
    } else {
        quotient
    };
    rounded as u32
}

fn for_each_box_sample(
    source_width: u32,
    source_height: u32,
    target_width: u32,
    target_height: u32,
    target_x: u32,
    target_y: u32,
    mut visit: impl FnMut(u32, u32, u64),
) {
    let x0 = u64::from(target_x) * u64::from(source_width);
    let x1 = u64::from(target_x + 1) * u64::from(source_width);
    let y0 = u64::from(target_y) * u64::from(source_height);
    let y1 = u64::from(target_y + 1) * u64::from(source_height);
    let source_x_start = (x0 / u64::from(target_width)) as u32;
    let source_x_end = x1.div_ceil(u64::from(target_width)) as u32;
    let source_y_start = (y0 / u64::from(target_height)) as u32;
    let source_y_end = y1.div_ceil(u64::from(target_height)) as u32;

    for source_y in source_y_start..source_y_end.min(source_height) {
        let source_y0 = u64::from(source_y) * u64::from(target_height);
        let source_y1 = u64::from(source_y + 1) * u64::from(target_height);
        let overlap_y = source_y1.min(y1).saturating_sub(source_y0.max(y0));
        for source_x in source_x_start..source_x_end.min(source_width) {
            let source_x0 = u64::from(source_x) * u64::from(target_width);
            let source_x1 = u64::from(source_x + 1) * u64::from(target_width);
            let overlap_x = source_x1.min(x1).saturating_sub(source_x0.max(x0));
            let weight = overlap_x * overlap_y;
            if weight > 0 {
                visit(source_x, source_y, weight);
            }
        }
    }
}

fn rounded_average(sum: u64, total_weight: u64) -> u8 {
    ((sum + total_weight / 2) / total_weight) as u8
}

fn validate_resize(
    len: usize,
    source_width: u32,
    source_height: u32,
    target_width: u32,
    target_height: u32,
) -> Result<()> {
    validate_len(len, source_width, source_height, "resize source")?;
    if target_width == 0 || target_height == 0 {
        return Err(PoseToolError::Raster(
            "resize target dimensions must be non-zero".to_string(),
        ));
    }
    Ok(())
}

fn validate_len(len: usize, width: u32, height: u32, label: &str) -> Result<()> {
    if width == 0 || height == 0 || len != (width as usize) * (height as usize) {
        return Err(PoseToolError::Raster(format!(
            "{label} length {len} does not match {width}x{height}"
        )));
    }
    Ok(())
}

fn validate_bounds(bounds: CropBounds, width: u32, height: u32) -> Result<()> {
    if bounds.left > bounds.right
        || bounds.top > bounds.bottom
        || bounds.right >= width
        || bounds.bottom >= height
    {
        return Err(PoseToolError::Raster(format!(
            "crop {bounds:?} is outside {width}x{height}"
        )));
    }
    Ok(())
}

fn index(x: u32, y: u32, width: u32) -> usize {
    (y as usize) * (width as usize) + (x as usize)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn white_mask_uses_inclusive_euclidean_threshold() {
        let pixels = [[255, 255, 255], [225, 255, 255], [226, 255, 255]];
        let mask = white_distance_mask(&pixels, 3, 1, 30).expect("mask");
        assert_eq!(mask, vec![0, 255, 0]);
    }

    #[test]
    fn four_neighbor_fill_closes_internal_holes_only() {
        let mask = vec![
            0, 0, 0, 0, 0, //
            0, 255, 255, 255, 0, //
            0, 255, 0, 255, 0, //
            0, 255, 255, 255, 0, //
            0, 0, 0, 0, 0,
        ];
        let filled = fill_subject_holes(&mask, 5, 5).expect("filled mask");
        assert_eq!(filled[index(2, 2, 5)], 255);
        assert_eq!(filled[index(0, 0, 5)], 0);
    }

    #[test]
    fn foreground_components_keep_near_effects_but_remove_shadow_and_caption() {
        let mut mask = vec![0_u8; 12 * 12];
        for y in 2..=8 {
            for x in 4..=7 {
                mask[index(x, y, 12)] = 255;
            }
        }
        mask[index(9, 3, 12)] = 255;
        mask[index(9, 4, 12)] = 255;
        mask[index(10, 3, 12)] = 255;
        mask[index(10, 4, 12)] = 255;
        for x in 3..=8 {
            mask[index(x, 10, 12)] = 255;
        }
        for x in 4..=7 {
            mask[index(x, 11, 12)] = 255;
        }

        let retained = retain_subject_components(&mask, 12, 12).expect("retained mask");
        assert_eq!(retained[index(5, 5, 12)], 255);
        assert_eq!(retained[index(9, 3, 12)], 255);
        assert_eq!(retained[index(5, 10, 12)], 0);
        assert_eq!(retained[index(5, 11, 12)], 0);
    }

    #[test]
    fn box_average_uses_exact_area_weights() {
        let source = [[0, 0, 0], [100, 100, 100], [200, 200, 200]];
        let resized = box_resize_rgb(&source, 3, 1, 2, 1).expect("resize");
        assert_eq!(resized, vec![[33, 33, 33], [167, 167, 167]]);
    }

    #[test]
    fn canonical_alignment_rejects_overflow() {
        let cells = vec![CellPayload {
            x: 80,
            y: 0,
            rgb: [1, 2, 3],
        }];
        let error = canonicalize_cells(
            "too-wide",
            &cells,
            Point { x: 0, y: 0 },
            CanonicalConfig::default(),
        )
        .expect_err("overflow");
        assert!(matches!(error, PoseToolError::CanonicalOverflow { .. }));
    }

    #[test]
    fn rational_rounding_matches_python_ties_to_even() {
        assert_eq!(round_ratio_ties_even(5, 2), 2);
        assert_eq!(round_ratio_ties_even(7, 2), 4);
        assert_eq!(round_ratio_ties_even(8, 3), 3);
    }
}
