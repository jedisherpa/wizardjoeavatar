#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Rgb(pub u8, pub u8, pub u8);

pub mod rgb {
    use super::Rgb;

    pub const OUTLINE: Rgb = Rgb(0x17, 0x19, 0x1c);
    pub const SHADOW_GRAY: Rgb = Rgb(0x36, 0x3a, 0x3e);
    pub const BEARD_DARK: Rgb = Rgb(0x6e, 0x73, 0x77);
    pub const BEARD_MID: Rgb = Rgb(0xbf, 0xc3, 0xc7);
    pub const BEARD_LIGHT: Rgb = Rgb(0xf4, 0xf4, 0xf1);
    pub const SKIN_DARK: Rgb = Rgb(0x9b, 0x54, 0x28);
    pub const SKIN_MID: Rgb = Rgb(0xc7, 0x78, 0x3e);
    pub const SKIN_LIGHT: Rgb = Rgb(0xe9, 0xaa, 0x71);
    pub const BROWN_DARK: Rgb = Rgb(0x4c, 0x29, 0x12);
    pub const BROWN: Rgb = Rgb(0x87, 0x47, 0x19);
    pub const BLUE_DARK: Rgb = Rgb(0x08, 0x2d, 0x59);
    pub const BLUE_MID: Rgb = Rgb(0x0e, 0x4c, 0x89);
    pub const BLUE_LIGHT: Rgb = Rgb(0x17, 0x6d, 0xb5);
    pub const GOLD: Rgb = Rgb(0xef, 0xa0, 0x00);
    pub const GOLD_LIGHT: Rgb = Rgb(0xff, 0xd2, 0x47);
    pub const MAGENTA: Rgb = Rgb(0xc5, 0x1e, 0x72);
    pub const CYAN_MAGIC: Rgb = Rgb(0x26, 0xd7, 0xe8);
}

pub mod env {
    use super::Rgb;

    pub const BACKGROUND: Rgb = Rgb(0xff, 0xff, 0xff);
    pub const FLOOR_LIGHT: Rgb = Rgb(0xfc, 0xfc, 0xfb);
    pub const FLOOR_ALTERNATE: Rgb = Rgb(0xf5, 0xf5, 0xf3);
    pub const FLOOR_GRID: Rgb = Rgb(0xec, 0xec, 0xea);
    pub const CONTACT_SHADOW: Rgb = Rgb(0xe8, 0xe8, 0xe5);
}

#[must_use]
pub fn lerp_rgb(a: Rgb, b: Rgb, t: f32) -> Rgb {
    let t = t.clamp(0.0, 1.0);
    Rgb(
        (a.0 as f32 + (b.0 as f32 - a.0 as f32) * t).round() as u8,
        (a.1 as f32 + (b.1 as f32 - a.1 as f32) * t).round() as u8,
        (a.2 as f32 + (b.2 as f32 - a.2 as f32) * t).round() as u8,
    )
}
