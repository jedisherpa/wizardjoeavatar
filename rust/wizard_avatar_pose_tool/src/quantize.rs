use crate::error::{PoseToolError, Result};
use std::collections::BTreeMap;

pub type QuantizationResult = (Vec<[u8; 3]>, Vec<[u8; 3]>);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct ColorCount {
    rgb: [u8; 3],
    count: u64,
}

#[derive(Clone, Debug)]
struct ColorBox {
    colors: Vec<ColorCount>,
}

impl ColorBox {
    fn population(&self) -> u64 {
        self.colors.iter().map(|color| color.count).sum()
    }

    fn channel_ranges(&self) -> [u8; 3] {
        let mut minimum = [u8::MAX; 3];
        let mut maximum = [u8::MIN; 3];
        for color in &self.colors {
            for channel in 0..3 {
                minimum[channel] = minimum[channel].min(color.rgb[channel]);
                maximum[channel] = maximum[channel].max(color.rgb[channel]);
            }
        }
        [
            maximum[0] - minimum[0],
            maximum[1] - minimum[1],
            maximum[2] - minimum[2],
        ]
    }

    fn split_score(&self) -> (u8, u64, usize) {
        let ranges = self.channel_ranges();
        (
            ranges[0].max(ranges[1]).max(ranges[2]),
            self.population(),
            self.colors.len(),
        )
    }

    fn split(mut self) -> Option<(Self, Self)> {
        if self.colors.len() < 2 {
            return None;
        }
        let ranges = self.channel_ranges();
        let channel = (0..3)
            .max_by_key(|channel| (ranges[*channel], 2_usize - *channel))
            .unwrap_or(0);
        self.colors.sort_by_key(|color| {
            (
                color.rgb[channel],
                color.rgb[(channel + 1) % 3],
                color.rgb[(channel + 2) % 3],
                color.rgb,
            )
        });
        let total = self.population();
        let mut cumulative = 0_u64;
        let mut split_at = 1_usize;
        for (index, color) in self.colors.iter().enumerate().take(self.colors.len() - 1) {
            cumulative += color.count;
            split_at = index + 1;
            if cumulative * 2 >= total {
                break;
            }
        }
        let right = self
            .colors
            .split_off(split_at.clamp(1, self.colors.len() - 1));
        Some((self, Self { colors: right }))
    }

    fn representative(&self) -> [u8; 3] {
        let population = self.population();
        let mut sums = [0_u64; 3];
        for color in &self.colors {
            for (channel, sum) in sums.iter_mut().enumerate() {
                *sum += u64::from(color.rgb[channel]) * color.count;
            }
        }
        [
            ((sums[0] + population / 2) / population) as u8,
            ((sums[1] + population / 2) / population) as u8,
            ((sums[2] + population / 2) / population) as u8,
        ]
    }
}

pub fn median_cut_quantize(
    pixels: &[[u8; 3]],
    maximum_colors: usize,
) -> Result<QuantizationResult> {
    if pixels.is_empty() {
        return Err(PoseToolError::Raster(
            "cannot quantize an empty image".to_string(),
        ));
    }
    if maximum_colors == 0 {
        return Err(PoseToolError::Raster(
            "quantizer color count must be positive".to_string(),
        ));
    }

    let mut histogram = BTreeMap::<[u8; 3], u64>::new();
    for &pixel in pixels {
        *histogram.entry(pixel).or_default() += 1;
    }
    let initial = ColorBox {
        colors: histogram
            .into_iter()
            .map(|(rgb, count)| ColorCount { rgb, count })
            .collect(),
    };
    let mut boxes = vec![initial];
    while boxes.len() < maximum_colors {
        let selected = boxes
            .iter()
            .enumerate()
            .filter(|(_, color_box)| color_box.colors.len() > 1)
            .max_by_key(|(index, color_box)| (color_box.split_score(), usize::MAX - *index))
            .map(|(index, _)| index);
        let Some(index) = selected else {
            break;
        };
        let color_box = boxes.remove(index);
        let Some((left, right)) = color_box.split() else {
            break;
        };
        boxes.push(left);
        boxes.push(right);
    }

    let mut palette = boxes
        .iter()
        .map(ColorBox::representative)
        .collect::<Vec<_>>();
    palette.sort_unstable();
    palette.dedup();
    let quantized = pixels
        .iter()
        .map(|pixel| nearest_palette_color(*pixel, &palette))
        .collect();
    Ok((quantized, palette))
}

fn nearest_palette_color(pixel: [u8; 3], palette: &[[u8; 3]]) -> [u8; 3] {
    palette
        .iter()
        .copied()
        .min_by_key(|candidate| (color_distance_squared(pixel, *candidate), *candidate))
        .expect("quantizer always produces a palette")
}

fn color_distance_squared(left: [u8; 3], right: [u8; 3]) -> u32 {
    (0..3)
        .map(|channel| {
            let difference = i32::from(left[channel]) - i32::from(right[channel]);
            (difference * difference) as u32
        })
        .sum()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn median_cut_is_deterministic_and_population_weighted() {
        let pixels = vec![
            [0, 0, 0],
            [0, 0, 0],
            [10, 0, 0],
            [240, 250, 255],
            [255, 255, 255],
        ];
        let first = median_cut_quantize(&pixels, 2).expect("first quantization");
        let second = median_cut_quantize(&pixels, 2).expect("second quantization");
        assert_eq!(first, second);
        assert_eq!(first.1.len(), 2);
        assert_eq!(first.0[0], first.0[1]);
        assert_ne!(first.0[0], first.0[4]);
    }

    #[test]
    fn palette_ties_choose_lexicographically_first_color() {
        assert_eq!(
            nearest_palette_color([10, 10, 10], &[[0, 10, 10], [20, 10, 10]]),
            [0, 10, 10]
        );
    }
}
