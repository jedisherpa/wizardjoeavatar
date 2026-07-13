pub type Point = (i32, i32);

#[must_use]
pub fn bresenham_line(x0: i32, y0: i32, x1: i32, y1: i32) -> Vec<Point> {
    let mut points = Vec::new();
    let dx = (x1 - x0).abs();
    let dy = -(y1 - y0).abs();
    let sx = if x0 < x1 { 1 } else { -1 };
    let sy = if y0 < y1 { 1 } else { -1 };
    let mut err = dx + dy;
    let (mut x, mut y) = (x0, y0);

    loop {
        points.push((x, y));
        if x == x1 && y == y1 {
            break;
        }
        let e2 = 2 * err;
        if e2 >= dy {
            err += dy;
            x += sx;
        }
        if e2 <= dx {
            err += dx;
            y += sy;
        }
    }
    points
}

#[must_use]
pub fn point_in_polygon(x: f32, y: f32, polygon: &[Point]) -> bool {
    if polygon.len() < 3 {
        return false;
    }
    let mut inside = false;
    let mut j = polygon.len() - 1;
    for (i, &(xi, yi)) in polygon.iter().enumerate() {
        let (xj, yj) = polygon[j];
        let yi_f = yi as f32;
        let yj_f = yj as f32;
        let denom = (yj - yi) as f32;
        let denom = if denom.abs() < 1e-9 { 1e-9 } else { denom };
        let intersects =
            (yi_f > y) != (yj_f > y) && x < (xj - xi) as f32 * (y - yi_f) / denom + xi as f32;
        if intersects {
            inside = !inside;
        }
        j = i;
    }
    inside
}

#[must_use]
pub fn polygon_bounds(points: &[Point]) -> Option<(i32, i32, i32, i32)> {
    let mut iter = points.iter();
    let first = iter.next()?;
    let (mut min_x, mut min_y, mut max_x, mut max_y) = (first.0, first.1, first.0, first.1);
    for &(x, y) in iter {
        min_x = min_x.min(x);
        min_y = min_y.min(y);
        max_x = max_x.max(x);
        max_y = max_y.max(y);
    }
    Some((min_x, min_y, max_x, max_y))
}

#[must_use]
pub fn ellipse_points(cx: i32, cy: i32, rx: i32, ry: i32) -> Vec<Point> {
    let rx = rx.max(1);
    let ry = ry.max(1);
    let mut points = Vec::new();
    for y in (cy - ry)..=(cy + ry) {
        for x in (cx - rx)..=(cx + rx) {
            let nx = (x - cx) as f32 / rx as f32;
            let ny = (y - cy) as f32 / ry as f32;
            if nx * nx + ny * ny <= 1.0 {
                points.push((x, y));
            }
        }
    }
    points
}

#[must_use]
pub fn quantize_scale(scale: f32) -> f32 {
    (scale * 8.0).round() / 8.0
}

#[must_use]
pub fn distance(a: (f32, f32), b: (f32, f32)) -> f32 {
    ((b.0 - a.0).powi(2) + (b.1 - a.1).powi(2)).sqrt()
}
