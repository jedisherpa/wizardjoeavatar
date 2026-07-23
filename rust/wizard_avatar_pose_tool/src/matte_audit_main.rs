use image::ImageReader;
use serde::Serialize;
use std::collections::VecDeque;
use std::path::PathBuf;

#[derive(Debug, Serialize)]
struct Component {
    pixels: u64,
    left: u32,
    top: u32,
    right: u32,
    bottom: u32,
    source_left: i64,
    source_top: i64,
    source_right: i64,
    source_bottom: i64,
}

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-matte-audit: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut arguments = std::env::args_os().skip(1);
    let image_path = arguments
        .next()
        .map(PathBuf::from)
        .ok_or("usage: wizard-avatar-matte-audit IMAGE [offset-x] [offset-y] [min-luma] [max-chroma] [min-pixels]")?;
    let offset_x = parse_argument::<i64>(&mut arguments)?.unwrap_or(0);
    let offset_y = parse_argument::<i64>(&mut arguments)?.unwrap_or(0);
    let min_luma = parse_argument::<u16>(&mut arguments)?.unwrap_or(96);
    let max_chroma = parse_argument::<u8>(&mut arguments)?.unwrap_or(24);
    let min_pixels = parse_argument::<u64>(&mut arguments)?.unwrap_or(4);
    if arguments.next().is_some() {
        return Err("too many arguments".into());
    }

    let image = ImageReader::open(image_path)?.decode()?.to_rgba8();
    let width = image.width();
    let height = image.height();
    let mut visited = vec![false; (width as usize).saturating_mul(height as usize)];
    let mut components = Vec::new();

    for y in 0..height {
        for x in 0..width {
            let start = index(x, y, width);
            if visited[start] || !is_neutral_light(image.get_pixel(x, y), min_luma, max_chroma) {
                continue;
            }

            visited[start] = true;
            let mut queue = VecDeque::from([(x, y)]);
            let mut pixels = 0_u64;
            let mut left = x;
            let mut top = y;
            let mut right = x;
            let mut bottom = y;
            while let Some((component_x, component_y)) = queue.pop_front() {
                pixels += 1;
                left = left.min(component_x);
                top = top.min(component_y);
                right = right.max(component_x);
                bottom = bottom.max(component_y);
                for (next_x, next_y) in neighbors(component_x, component_y, width, height) {
                    let next = index(next_x, next_y, width);
                    if visited[next]
                        || !is_neutral_light(image.get_pixel(next_x, next_y), min_luma, max_chroma)
                    {
                        continue;
                    }
                    visited[next] = true;
                    queue.push_back((next_x, next_y));
                }
            }
            if pixels >= min_pixels {
                components.push(Component {
                    pixels,
                    left,
                    top,
                    right,
                    bottom,
                    source_left: i64::from(left) - offset_x,
                    source_top: i64::from(top) - offset_y,
                    source_right: i64::from(right) - offset_x,
                    source_bottom: i64::from(bottom) - offset_y,
                });
            }
        }
    }

    components.sort_by_key(|component| std::cmp::Reverse(component.pixels));
    println!("{}", serde_json::to_string_pretty(&components)?);
    Ok(())
}

fn parse_argument<T>(
    arguments: &mut impl Iterator<Item = std::ffi::OsString>,
) -> Result<Option<T>, Box<dyn std::error::Error>>
where
    T: std::str::FromStr,
    T::Err: std::error::Error + 'static,
{
    arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| value.parse::<T>())
        .transpose()
        .map_err(Into::into)
}

fn is_neutral_light(pixel: &image::Rgba<u8>, min_luma: u16, max_chroma: u8) -> bool {
    if pixel[3] == 0 {
        return false;
    }
    let minimum = *pixel.0[..3].iter().min().unwrap_or(&0);
    let maximum = *pixel.0[..3].iter().max().unwrap_or(&0);
    let luma = pixel.0[..3]
        .iter()
        .map(|channel| u16::from(*channel))
        .sum::<u16>()
        / 3;
    maximum.saturating_sub(minimum) <= max_chroma && luma >= min_luma
}

fn neighbors(x: u32, y: u32, width: u32, height: u32) -> impl Iterator<Item = (u32, u32)> {
    let left = (x > 0).then_some((x.saturating_sub(1), y));
    let right = (x + 1 < width).then_some((x + 1, y));
    let up = (y > 0).then_some((x, y.saturating_sub(1)));
    let down = (y + 1 < height).then_some((x, y + 1));
    [left, right, up, down].into_iter().flatten()
}

fn index(x: u32, y: u32, width: u32) -> usize {
    (y as usize)
        .saturating_mul(width as usize)
        .saturating_add(x as usize)
}
