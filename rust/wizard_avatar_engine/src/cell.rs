use crate::geometry::{bresenham_line, ellipse_points, point_in_polygon, polygon_bounds, Point};
use crate::palette::{env, Rgb};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Cell {
    pub glyph: u8,
    pub rgb: Rgb,
}

impl Cell {
    #[must_use]
    pub const fn new(glyph: u8, rgb: Rgb) -> Self {
        Self { glyph, rgb }
    }

    #[must_use]
    pub fn to_bytes(self) -> [u8; 4] {
        [self.glyph, self.rgb.0, self.rgb.1, self.rgb.2]
    }
}

#[derive(Clone, Debug)]
pub struct CellCanvas {
    pub width: usize,
    pub height: usize,
    cells: Vec<Option<Cell>>,
}

impl CellCanvas {
    #[must_use]
    pub fn new(width: usize, height: usize) -> Self {
        Self {
            width,
            height,
            cells: vec![None; width * height],
        }
    }

    #[must_use]
    pub fn filled(width: usize, height: usize, cell: Cell) -> Self {
        Self {
            width,
            height,
            cells: vec![Some(cell); width * height],
        }
    }

    #[must_use]
    pub fn in_bounds(&self, x: i32, y: i32) -> bool {
        x >= 0 && y >= 0 && (x as usize) < self.width && (y as usize) < self.height
    }

    #[must_use]
    pub fn get(&self, x: i32, y: i32) -> Option<Cell> {
        if !self.in_bounds(x, y) {
            return None;
        }
        self.cells[y as usize * self.width + x as usize]
    }

    pub fn set(&mut self, x: i32, y: i32, glyph: u8, rgb: Rgb) {
        if self.in_bounds(x, y) {
            self.cells[y as usize * self.width + x as usize] = Some(Cell::new(glyph, rgb));
        }
    }

    pub fn rect(&mut self, x0: i32, y0: i32, x1: i32, y1: i32, glyph: u8, rgb: Rgb) {
        for y in y0.min(y1)..=y0.max(y1) {
            for x in x0.min(x1)..=x0.max(x1) {
                self.set(x, y, glyph, rgb);
            }
        }
    }

    #[allow(clippy::too_many_arguments)]
    pub fn line(
        &mut self,
        x0: i32,
        y0: i32,
        x1: i32,
        y1: i32,
        glyph: u8,
        rgb: Rgb,
        thickness: i32,
    ) {
        let radius = (thickness - 1).max(0);
        for (x, y) in bresenham_line(x0, y0, x1, y1) {
            for oy in -radius..=radius {
                for ox in -radius..=radius {
                    if ox.abs() + oy.abs() <= radius {
                        self.set(x + ox, y + oy, glyph, rgb);
                    }
                }
            }
        }
    }

    pub fn polygon(&mut self, points: &[Point], glyph: u8, rgb: Rgb) {
        let Some((min_x, min_y, max_x, max_y)) = polygon_bounds(points) else {
            return;
        };
        for y in min_y..=max_y {
            for x in min_x..=max_x {
                if point_in_polygon(x as f32 + 0.5, y as f32 + 0.5, points) {
                    self.set(x, y, glyph, rgb);
                }
            }
        }
    }

    pub fn ellipse(&mut self, cx: i32, cy: i32, rx: i32, ry: i32, glyph: u8, rgb: Rgb) {
        for (x, y) in ellipse_points(cx, cy, rx, ry) {
            self.set(x, y, glyph, rgb);
        }
    }

    pub fn blit_scaled(
        &mut self,
        local: &CellCanvas,
        root_local: Point,
        root_screen: (f32, f32),
        scale: f32,
    ) {
        let dest_width = ((local.width as f32 * scale).round() as i32).max(1);
        let dest_height = ((local.height as f32 * scale).round() as i32).max(1);
        let origin_x = (root_screen.0 - root_local.0 as f32 * scale).round() as i32;
        let origin_y = (root_screen.1 - root_local.1 as f32 * scale).round() as i32;

        for dy in 0..dest_height {
            let sy = ((dy as f32 / scale.max(0.001)) as i32).min(local.height as i32 - 1);
            for dx in 0..dest_width {
                let sx = ((dx as f32 / scale.max(0.001)) as i32).min(local.width as i32 - 1);
                if let Some(cell) = local.get(sx, sy) {
                    let x = origin_x + dx;
                    let y = origin_y + dy;
                    if self.in_bounds(x, y) {
                        self.cells[y as usize * self.width + x as usize] = Some(cell);
                    }
                }
            }
        }
    }

    pub fn occupied_cells(&self) -> impl Iterator<Item = (i32, i32, Cell)> + '_ {
        self.cells.iter().enumerate().filter_map(|(index, cell)| {
            cell.map(|cell| {
                (
                    (index % self.width) as i32,
                    (index / self.width) as i32,
                    cell,
                )
            })
        })
    }

    #[must_use]
    pub fn occupied_count(&self) -> usize {
        self.cells.iter().filter(|cell| cell.is_some()).count()
    }

    #[must_use]
    pub fn to_frame_bytes(&self) -> Vec<u8> {
        let fallback = Cell::new(b' ', env::BACKGROUND);
        let mut out = Vec::with_capacity(self.width * self.height * 4);
        for cell in &self.cells {
            out.extend_from_slice(&cell.unwrap_or(fallback).to_bytes());
        }
        out
    }
}
