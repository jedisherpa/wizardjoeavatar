use image::ImageReader;
use serde::Serialize;
use std::collections::BTreeMap;
use std::path::PathBuf;

#[derive(Debug, Serialize)]
struct ColorCount {
    rgba: [u8; 4],
    pixels: u64,
    chroma: u8,
    luma: u16,
    left: u32,
    top: u32,
    right: u32,
    bottom: u32,
}

#[derive(Debug)]
struct ColorStats {
    pixels: u64,
    left: u32,
    top: u32,
    right: u32,
    bottom: u32,
}

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-pixel-sample: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut arguments = std::env::args_os().skip(1);
    let path = arguments
        .next()
        .map(PathBuf::from)
        .ok_or("usage: wizard-avatar-pixel-sample IMAGE LEFT TOP RIGHT BOTTOM [minimum-count] [crop-output]")?;
    let left = next_u32(&mut arguments, "left")?;
    let top = next_u32(&mut arguments, "top")?;
    let right = next_u32(&mut arguments, "right")?;
    let bottom = next_u32(&mut arguments, "bottom")?;
    let minimum_count = arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .map(|value| value.parse::<u64>())
        .transpose()?
        .unwrap_or(1);
    let crop_output = arguments.next().map(PathBuf::from);
    if arguments.next().is_some() {
        return Err("too many arguments".into());
    }

    let image = ImageReader::open(path)?.decode()?.to_rgba8();
    if left > right || top > bottom || right >= image.width() || bottom >= image.height() {
        return Err("sample bounds are outside the image".into());
    }
    if let Some(crop_output) = crop_output {
        image::imageops::crop_imm(&image, left, top, right - left + 1, bottom - top + 1)
            .to_image()
            .save(crop_output)?;
    }

    let mut counts = BTreeMap::<[u8; 4], ColorStats>::new();
    for y in top..=bottom {
        for x in left..=right {
            let rgba = image.get_pixel(x, y).0;
            if rgba[3] > 0 {
                counts
                    .entry(rgba)
                    .and_modify(|stats| {
                        stats.pixels += 1;
                        stats.left = stats.left.min(x);
                        stats.top = stats.top.min(y);
                        stats.right = stats.right.max(x);
                        stats.bottom = stats.bottom.max(y);
                    })
                    .or_insert(ColorStats {
                        pixels: 1,
                        left: x,
                        top: y,
                        right: x,
                        bottom: y,
                    });
            }
        }
    }
    let mut colors = counts
        .into_iter()
        .filter(|(_, stats)| stats.pixels >= minimum_count)
        .map(|(rgba, stats)| {
            let minimum = *rgba[..3].iter().min().unwrap_or(&0);
            let maximum = *rgba[..3].iter().max().unwrap_or(&0);
            let luma = rgba[..3]
                .iter()
                .map(|channel| u16::from(*channel))
                .sum::<u16>()
                / 3;
            ColorCount {
                rgba,
                pixels: stats.pixels,
                chroma: maximum.saturating_sub(minimum),
                luma,
                left: stats.left,
                top: stats.top,
                right: stats.right,
                bottom: stats.bottom,
            }
        })
        .collect::<Vec<_>>();
    colors.sort_by_key(|color| std::cmp::Reverse(color.pixels));
    println!("{}", serde_json::to_string_pretty(&colors)?);
    Ok(())
}

fn next_u32(
    arguments: &mut impl Iterator<Item = std::ffi::OsString>,
    label: &str,
) -> Result<u32, Box<dyn std::error::Error>> {
    arguments
        .next()
        .and_then(|value| value.into_string().ok())
        .ok_or_else(|| format!("missing {label}").into())
        .and_then(|value| value.parse::<u32>().map_err(Into::into))
}
