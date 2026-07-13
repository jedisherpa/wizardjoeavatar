use crate::state::{Velocity, WorldPoint};
use std::f32::consts::TAU;

#[derive(Clone, Copy, Debug)]
pub struct PathSample {
    pub position: WorldPoint,
    pub tangent: Velocity,
}

#[derive(Clone, Debug)]
pub enum PathCurve {
    Circle {
        center: WorldPoint,
        radius: f32,
        start_angle: f32,
        sign: f32,
    },
    Table(ArcLengthTable),
}

impl PathCurve {
    #[must_use]
    pub fn circle(center: WorldPoint, radius: f32, start_angle: f32, clockwise: bool) -> Self {
        Self::Circle {
            center,
            radius,
            start_angle,
            sign: if clockwise { -1.0 } else { 1.0 },
        }
    }

    #[must_use]
    pub fn figure_eight(center: WorldPoint, radius: f32) -> Self {
        let mut samples = Vec::with_capacity(513);
        for index in 0..=512 {
            let t = TAU * index as f32 / 512.0;
            let position = WorldPoint {
                x: center.x + radius * t.sin(),
                z: center.z + radius * t.sin() * t.cos(),
            };
            let derivative = Velocity {
                x: radius * t.cos(),
                z: radius * (2.0 * t).cos(),
            };
            samples.push((position, normalize(derivative)));
        }
        Self::Table(ArcLengthTable::new(samples))
    }

    pub fn spline(points: &[WorldPoint]) -> Result<Self, String> {
        if points.len() < 2 {
            return Err("spline requires at least two points".to_string());
        }
        let mut samples = Vec::new();
        for segment in 0..points.len() - 1 {
            let p0 = points[segment.saturating_sub(1)];
            let p1 = points[segment];
            let p2 = points[segment + 1];
            let p3 = points[(segment + 2).min(points.len() - 1)];
            for step in 0..32 {
                let t = step as f32 / 32.0;
                samples.push(catmull_rom(p0, p1, p2, p3, t));
            }
        }
        let last = *points.last().expect("validated non-empty points");
        let prior = points[points.len() - 2];
        samples.push((
            last,
            normalize(Velocity {
                x: last.x - prior.x,
                z: last.z - prior.z,
            }),
        ));
        Ok(Self::Table(ArcLengthTable::new(samples)))
    }

    #[must_use]
    pub fn total_length(&self) -> f32 {
        match self {
            Self::Circle { radius, .. } => TAU * radius,
            Self::Table(table) => table.total_length,
        }
    }

    #[must_use]
    pub fn sample(&self, distance: f32) -> PathSample {
        match self {
            Self::Circle {
                center,
                radius,
                start_angle,
                sign,
            } => {
                let distance = distance.clamp(0.0, self.total_length());
                let angle = start_angle + sign * distance / radius;
                PathSample {
                    position: WorldPoint {
                        x: center.x + radius * angle.cos(),
                        z: center.z + radius * angle.sin(),
                    },
                    tangent: Velocity {
                        x: -angle.sin() * sign,
                        z: angle.cos() * sign,
                    },
                }
            }
            Self::Table(table) => table.sample(distance),
        }
    }
}

#[derive(Clone, Debug)]
pub struct ArcLengthTable {
    samples: Vec<(f32, WorldPoint, Velocity)>,
    total_length: f32,
}

impl ArcLengthTable {
    fn new(points: Vec<(WorldPoint, Velocity)>) -> Self {
        let mut distance = 0.0;
        let mut samples = Vec::with_capacity(points.len());
        let mut previous = None;
        for (position, tangent) in points {
            if let Some(prior) = previous {
                distance += world_distance(prior, position);
            }
            samples.push((distance, position, tangent));
            previous = Some(position);
        }
        Self {
            samples,
            total_length: distance,
        }
    }

    fn sample(&self, distance: f32) -> PathSample {
        let distance = distance.clamp(0.0, self.total_length);
        let upper = self
            .samples
            .partition_point(|(sample_distance, _, _)| *sample_distance < distance)
            .min(self.samples.len() - 1);
        if upper == 0 {
            let (_, position, tangent) = self.samples[0];
            return PathSample { position, tangent };
        }
        let (d0, p0, t0) = self.samples[upper - 1];
        let (d1, p1, t1) = self.samples[upper];
        let alpha = if d1 > d0 {
            (distance - d0) / (d1 - d0)
        } else {
            0.0
        };
        PathSample {
            position: WorldPoint {
                x: p0.x + (p1.x - p0.x) * alpha,
                z: p0.z + (p1.z - p0.z) * alpha,
            },
            tangent: normalize(Velocity {
                x: t0.x + (t1.x - t0.x) * alpha,
                z: t0.z + (t1.z - t0.z) * alpha,
            }),
        }
    }
}

fn catmull_rom(
    p0: WorldPoint,
    p1: WorldPoint,
    p2: WorldPoint,
    p3: WorldPoint,
    t: f32,
) -> (WorldPoint, Velocity) {
    let t2 = t * t;
    let t3 = t2 * t;
    let position = |a: f32, b: f32, c: f32, d: f32| {
        0.5 * ((2.0 * b)
            + (-a + c) * t
            + (2.0 * a - 5.0 * b + 4.0 * c - d) * t2
            + (-a + 3.0 * b - 3.0 * c + d) * t3)
    };
    let derivative = |a: f32, b: f32, c: f32, d: f32| {
        0.5 * ((-a + c)
            + 2.0 * (2.0 * a - 5.0 * b + 4.0 * c - d) * t
            + 3.0 * (-a + 3.0 * b - 3.0 * c + d) * t2)
    };
    (
        WorldPoint {
            x: position(p0.x, p1.x, p2.x, p3.x),
            z: position(p0.z, p1.z, p2.z, p3.z),
        },
        normalize(Velocity {
            x: derivative(p0.x, p1.x, p2.x, p3.x),
            z: derivative(p0.z, p1.z, p2.z, p3.z),
        }),
    )
}

fn normalize(value: Velocity) -> Velocity {
    let length = (value.x * value.x + value.z * value.z).sqrt();
    if length <= f32::EPSILON {
        Velocity { x: 0.0, z: 0.0 }
    } else {
        Velocity {
            x: value.x / length,
            z: value.z / length,
        }
    }
}

fn world_distance(a: WorldPoint, b: WorldPoint) -> f32 {
    ((b.x - a.x).powi(2) + (b.z - a.z).powi(2)).sqrt()
}
