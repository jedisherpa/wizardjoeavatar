use std::f32::consts::TAU;
use wizard_avatar_engine::pathing::{PathCurve, PathSample};
use wizard_avatar_engine::state::WorldPoint;

fn distance(a: WorldPoint, b: WorldPoint) -> f32 {
    ((b.x - a.x).powi(2) + (b.z - a.z).powi(2)).sqrt()
}

#[test]
fn wiz_path_001_circle_is_arc_length_parameterized_and_closes_exactly() {
    let curve = PathCurve::circle(WorldPoint { x: 0.0, z: 5.0 }, 1.5, 0.0, false);
    assert!((curve.total_length() - TAU * 1.5).abs() < 1e-4);
    let start = curve.sample(0.0);
    let end = curve.sample(curve.total_length());
    assert!(distance(start.position, end.position) < 1e-5);
    let segment_lengths = (0..64)
        .map(|index| {
            let a = curve.sample(curve.total_length() * index as f32 / 64.0);
            let b = curve.sample(curve.total_length() * (index + 1) as f32 / 64.0);
            distance(a.position, b.position)
        })
        .collect::<Vec<_>>();
    let min = segment_lengths
        .iter()
        .copied()
        .fold(f32::INFINITY, f32::min);
    let max = segment_lengths.iter().copied().fold(0.0, f32::max);
    assert!(max - min < 1e-4);
}

#[test]
fn wiz_path_002_figure_eight_closes_with_continuous_tangent() {
    let curve = PathCurve::figure_eight(WorldPoint { x: 0.0, z: 5.0 }, 1.4);
    let start = curve.sample(0.0);
    let end = curve.sample(curve.total_length());
    assert!(distance(start.position, end.position) < 1e-4);
    assert!(tangent_delta(start, end) < 0.02);
    let before = curve.sample(curve.total_length() * 0.5 - 0.001);
    let after = curve.sample(curve.total_length() * 0.5 + 0.001);
    assert!(distance(before.position, after.position) < 0.02);
    assert!(tangent_delta(before, after) < 0.05);
}

fn tangent_delta(a: PathSample, b: PathSample) -> f32 {
    ((a.tangent.x - b.tangent.x).powi(2) + (a.tangent.z - b.tangent.z).powi(2)).sqrt()
}

#[test]
fn wiz_path_003_spline_starts_and_ends_without_root_teleport() {
    let points = [
        WorldPoint { x: -2.0, z: 4.0 },
        WorldPoint { x: -0.5, z: 6.0 },
        WorldPoint { x: 1.0, z: 4.5 },
        WorldPoint { x: 2.0, z: 6.0 },
    ];
    let curve = PathCurve::spline(&points).expect("spline");
    assert!(distance(curve.sample(0.0).position, points[0]) < 1e-6);
    assert!(distance(curve.sample(curve.total_length()).position, points[3]) < 1e-6);
}
