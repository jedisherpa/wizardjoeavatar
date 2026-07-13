use std::collections::{BTreeMap, BTreeSet, VecDeque};
use wizard_avatar_engine::pose::{
    analyze_pose_topology, sample_pose, AnchorId, PoseLibrary, RegionId, POSE_SCHEMA_VERSION,
};
use wizard_avatar_engine::state::{
    ContactMarker, Direction, Locomotion, StaffState, UpperBodyAction, WizardState,
};

type RegionNeighbor = (RegionId, i32);
type GapRegionTrace = ((i32, i32), Vec<RegionNeighbor>);

fn connected_component_sizes(points: &BTreeSet<(i32, i32)>) -> Vec<(usize, (i32, i32, i32, i32))> {
    let mut remaining = points.clone();
    let mut components = Vec::new();
    while let Some(start) = remaining.pop_first() {
        let mut component = BTreeSet::from([start]);
        let mut queue = VecDeque::from([start]);
        while let Some((x, y)) = queue.pop_front() {
            for dy in -1..=1 {
                for dx in -1..=1 {
                    let point = (x + dx, y + dy);
                    if (dx != 0 || dy != 0) && remaining.remove(&point) {
                        component.insert(point);
                        queue.push_back(point);
                    }
                }
            }
        }
        let bounds = (
            component.iter().map(|point| point.0).min().unwrap(),
            component.iter().map(|point| point.1).min().unwrap(),
            component.iter().map(|point| point.0).max().unwrap(),
            component.iter().map(|point| point.1).max().unwrap(),
        );
        components.push((component.len(), bounds));
    }
    components.sort_unstable_by(|left, right| right.0.cmp(&left.0));
    components
}

#[test]
fn all_pose_staff_anchors_do_not_create_phantom_repair_bridges() {
    let library = PoseLibrary::reference().expect("pose library");
    let mut failures = Vec::new();
    for pose_id in library.pose_ids() {
        let definition = library.for_id(pose_id).expect("baseline pose definition");
        let state = WizardState {
            pose_id: Some(pose_id.to_string()),
            previous_pose_id: Some(pose_id.to_string()),
            ..WizardState::default()
        };
        let sample = sample_pose(&state).expect("baseline pose sample");
        let staff = definition
            .cells
            .iter()
            .filter(|cell| cell.region == RegionId::Staff)
            .map(|cell| (i32::from(cell.x), i32::from(cell.y)))
            .collect::<BTreeSet<_>>();
        let sampled_staff = sample
            .region_points
            .get(&RegionId::Staff)
            .into_iter()
            .flatten()
            .copied()
            .collect::<BTreeSet<_>>();
        let staff_additions = sampled_staff
            .difference(&staff)
            .copied()
            .collect::<BTreeSet<_>>();
        let staff_components = connected_component_sizes(&staff);
        let addition_components = connected_component_sizes(&staff_additions);
        let final_staff_components = connected_component_sizes(&sampled_staff);
        if final_staff_components.len() != 1
            || addition_components
                .first()
                .is_some_and(|component| component.0 > 14)
        {
            failures.push(format!(
                "{pose_id}: staff={staff_components:?}, staff_additions={addition_components:?}, final={final_staff_components:?}"
            ));
        }
    }

    assert!(
        failures.is_empty(),
        "poses contain phantom staff repair bridges:\n{}",
        failures.join("\n")
    );
}

#[test]
fn wiz_anim_001_every_direction_has_validated_semantic_pose_metadata() {
    let library = PoseLibrary::reference().expect("load semantic pose library");
    library.validate().expect("validate semantic pose library");
    assert_eq!(library.schema_version, POSE_SCHEMA_VERSION);

    for direction in Direction::ALL {
        let pose = library.for_direction(direction).expect("direction pose");
        for anchor in AnchorId::REQUIRED {
            assert!(
                pose.anchors.contains_key(&anchor),
                "{direction:?} missing {anchor:?}"
            );
        }
        assert!(!pose.cells.is_empty());
        assert!(pose
            .cells
            .iter()
            .all(|cell| cell.region != RegionId::Effect));
        let ids = pose
            .cells
            .iter()
            .map(|cell| cell.stable_id)
            .collect::<BTreeSet<_>>();
        assert_eq!(
            ids.len(),
            pose.cells.len(),
            "stable IDs are unique for {direction:?}"
        );
        assert!(pose.z_order.contains(&RegionId::LeftBoot));
        assert!(pose.z_order.contains(&RegionId::RightBoot));
        assert!(pose.z_order.contains(&RegionId::Staff));
        assert!(pose.z_order.contains(&RegionId::Face));
        assert!(pose.z_order.contains(&RegionId::Mouth));
    }
}

#[test]
fn wiz_anim_002_pose_cells_use_semantic_regions_not_palette_classification() {
    let library = PoseLibrary::reference().expect("load semantic pose library");
    let regions = Direction::ALL
        .into_iter()
        .flat_map(|direction| library.for_direction(direction).unwrap().cells.iter())
        .map(|cell| cell.region)
        .collect::<BTreeSet<_>>();
    for required in [
        RegionId::Hat,
        RegionId::Head,
        RegionId::Torso,
        RegionId::Robe,
        RegionId::InnerRobe,
        RegionId::LeftArm,
        RegionId::RightArm,
        RegionId::LeftLeg,
        RegionId::RightLeg,
        RegionId::LeftBoot,
        RegionId::RightBoot,
        RegionId::Staff,
        RegionId::Face,
        RegionId::Mouth,
    ] {
        assert!(
            regions.contains(&required),
            "missing semantic region {required:?}"
        );
    }
}

#[test]
fn wiz_anim_006_all_eight_directions_produce_distinct_complete_cell_samples() {
    let samples = Direction::ALL
        .into_iter()
        .map(|facing| {
            let state = WizardState {
                facing,
                previous_facing: facing,
                ..WizardState::default()
            };
            let sample = sample_pose(&state).expect("sample semantic pose");
            let occupied = sample.canvas.occupied_count();
            assert!(occupied >= sample.source_cell_count * 95 / 100);
            assert!(occupied <= sample.source_cell_count * 102 / 100);
            sample.canvas.to_frame_bytes()
        })
        .collect::<BTreeSet<_>>();
    assert_eq!(samples.len(), Direction::ALL.len());
}

fn occupied_points(sample: &wizard_avatar_engine::pose::PoseSample) -> BTreeSet<(i32, i32)> {
    sample
        .canvas
        .occupied_cells()
        .map(|(x, y, _)| (x, y))
        .collect()
}

fn component_count(points: &BTreeSet<(i32, i32)>) -> usize {
    let mut remaining = points.clone();
    let mut components = 0;
    while let Some(start) = remaining.pop_first() {
        components += 1;
        let mut queue = VecDeque::from([start]);
        while let Some((x, y)) = queue.pop_front() {
            for dy in -1..=1 {
                for dx in -1..=1 {
                    if (dx != 0 || dy != 0) && remaining.remove(&(x + dx, y + dy)) {
                        queue.push_back((x + dx, y + dy));
                    }
                }
            }
        }
    }
    components
}

fn fragmentation_score(points: &BTreeSet<(i32, i32)>) -> f32 {
    let mut rows = BTreeMap::<i32, Vec<i32>>::new();
    let mut columns = BTreeMap::<i32, Vec<i32>>::new();
    for &(x, y) in points {
        rows.entry(y).or_default().push(x);
        columns.entry(x).or_default().push(y);
    }
    let runs = |lines: BTreeMap<i32, Vec<i32>>| {
        lines
            .into_values()
            .map(|mut values| {
                values.sort_unstable();
                1 + values
                    .windows(2)
                    .filter(|pair| pair[1] > pair[0] + 1)
                    .count()
            })
            .sum::<usize>()
    };
    (runs(rows) + runs(columns)) as f32 / points.len().max(1) as f32
}

fn nearest_region_distance(
    sample: &wizard_avatar_engine::pose::PoseSample,
    anchor: AnchorId,
    regions: &[RegionId],
) -> f32 {
    let point = sample.anchors[&anchor];
    regions
        .iter()
        .flat_map(|region| sample.region_points.get(region).into_iter().flatten())
        .map(|&(x, y)| ((point.x - x as f32).powi(2) + (point.y - y as f32).powi(2)).sqrt())
        .fold(f32::INFINITY, f32::min)
}

#[test]
fn wiz_anim_009_adjacent_facing_blends_preserve_coherent_complete_silhouettes() {
    let required_regions = [
        RegionId::Hat,
        RegionId::Head,
        RegionId::Torso,
        RegionId::Robe,
        RegionId::LeftBoot,
        RegionId::RightBoot,
        RegionId::Staff,
    ];
    let anchored_regions = [
        (
            AnchorId::Head,
            &[RegionId::Hat, RegionId::Head, RegionId::Face][..],
        ),
        (AnchorId::StaffHand, &[RegionId::Staff][..]),
        (AnchorId::StaffTop, &[RegionId::Staff][..]),
        (
            AnchorId::Root,
            &[
                RegionId::Robe,
                RegionId::LeftLeg,
                RegionId::RightLeg,
                RegionId::LeftBoot,
                RegionId::RightBoot,
            ][..],
        ),
    ];

    for source_direction in Direction::ALL {
        let target_direction = source_direction.rotate(1);
        for step in 0..=16 {
            let blend = step as f32 / 16.0;
            let phase = blend.rem_euclid(1.0);
            let make_state = |facing, previous_facing, facing_blend| WizardState {
                facing,
                previous_facing,
                facing_blend,
                facing_pose_handoff: facing_blend >= 0.5,
                locomotion: Locomotion::Walking,
                walk_phase: phase,
                speed_ratio: 1.0,
                contact_marker: ContactMarker::from_phase(phase),
                ..WizardState::default()
            };
            let sample = sample_pose(&make_state(target_direction, source_direction, blend))
                .expect("sample adjacent facing transition");
            let source = sample_pose(&make_state(source_direction, source_direction, 1.0))
                .expect("sample source facing");
            let target = sample_pose(&make_state(target_direction, target_direction, 1.0))
                .expect("sample target facing");
            assert_eq!(
                sample.direction,
                if blend < 0.5 {
                    source_direction
                } else {
                    target_direction
                },
                "direction handoff must present one coherent pose"
            );

            for region in required_regions {
                assert!(
                    sample
                        .region_points
                        .get(&region)
                        .is_some_and(|points| !points.is_empty()),
                    "{source_direction:?}->{target_direction:?} blend {blend} lost {region:?}"
                );
            }

            let points = occupied_points(&sample);
            let source_points = occupied_points(&source);
            let target_points = occupied_points(&target);
            let minimum_expected = source_points.len().min(target_points.len()) * 9 / 10;
            assert!(
                points.len() >= minimum_expected,
                "{source_direction:?}->{target_direction:?} blend {blend} cell count collapsed: {} < {minimum_expected}",
                points.len()
            );
            let baseline_components =
                component_count(&source_points).max(component_count(&target_points));
            assert!(
                component_count(&points) <= baseline_components + 2,
                "{source_direction:?}->{target_direction:?} blend {blend} component explosion"
            );
            let baseline_fragmentation =
                fragmentation_score(&source_points).max(fragmentation_score(&target_points));
            assert!(
                fragmentation_score(&points) <= baseline_fragmentation * 1.1 + 0.02,
                "{source_direction:?}->{target_direction:?} blend {blend} excessive bounds fragmentation"
            );

            for (anchor, regions) in anchored_regions {
                let baseline_distance = nearest_region_distance(&source, anchor, regions)
                    .max(nearest_region_distance(&target, anchor, regions));
                let distance = nearest_region_distance(&sample, anchor, regions);
                assert!(
                    distance <= baseline_distance + 1.0,
                    "{source_direction:?}->{target_direction:?} blend {blend} detached {anchor:?}: {distance} > {baseline_distance}"
                );
            }
        }
    }
}

fn empty_internal_rows(sample: &wizard_avatar_engine::pose::PoseSample) -> Vec<i32> {
    let occupied = occupied_points(sample);
    let min_y = occupied.iter().map(|(_, y)| *y).min().unwrap_or(0);
    let max_y = occupied.iter().map(|(_, y)| *y).max().unwrap_or(0);
    (min_y + 1..max_y)
        .filter(|y| !occupied.iter().any(|(_, occupied_y)| occupied_y == y))
        .collect()
}

fn horizontal_seam_rows(sample: &wizard_avatar_engine::pose::PoseSample) -> Vec<(i32, usize)> {
    let occupied = occupied_points(sample);
    let min_y = occupied.iter().map(|(_, y)| *y).min().unwrap_or(0);
    let max_y = occupied.iter().map(|(_, y)| *y).max().unwrap_or(0);
    (min_y + 1..max_y)
        .filter_map(|y| {
            let gap_count = occupied
                .iter()
                .map(|(x, _)| *x)
                .collect::<BTreeSet<_>>()
                .into_iter()
                .filter(|x| {
                    !occupied.contains(&(*x, y))
                        && occupied.contains(&(*x, y - 1))
                        && occupied.contains(&(*x, y + 1))
                })
                .count();
            (gap_count >= 4).then_some((y, gap_count))
        })
        .collect()
}

fn horizontal_seam_points(sample: &wizard_avatar_engine::pose::PoseSample) -> Vec<(i32, i32)> {
    let occupied = occupied_points(sample);
    let xs = occupied.iter().map(|(x, _)| *x).collect::<BTreeSet<_>>();
    let mut points = Vec::new();
    for (y, _) in horizontal_seam_rows(sample) {
        for x in &xs {
            if !occupied.contains(&(*x, y))
                && occupied.contains(&(*x, y - 1))
                && occupied.contains(&(*x, y + 1))
            {
                points.push((*x, y));
            }
        }
    }
    points
}

fn seam_neighbor_regions(sample: &wizard_avatar_engine::pose::PoseSample) -> Vec<GapRegionTrace> {
    horizontal_seam_points(sample)
        .into_iter()
        .map(|point @ (x, y)| {
            let regions = sample
                .region_points
                .iter()
                .flat_map(|(region, points)| {
                    [-1, 1]
                        .into_iter()
                        .filter(move |dy| points.contains(&(x, y + dy)))
                        .map(move |dy| (*region, dy))
                })
                .collect();
            (point, regions)
        })
        .collect()
}

fn core_vertical_cracks(sample: &wizard_avatar_engine::pose::PoseSample) -> Vec<(i32, i32)> {
    let core_regions = [
        RegionId::Torso,
        RegionId::Robe,
        RegionId::InnerRobe,
        RegionId::LeftArm,
        RegionId::RightArm,
    ];
    let points = core_regions
        .iter()
        .flat_map(|region| sample.region_points.get(region).into_iter().flatten())
        .copied()
        .collect::<BTreeSet<_>>();
    let hem_y = sample.root.1 - 10;
    let mut cracks = Vec::new();
    for y in points.iter().map(|(_, y)| *y).collect::<BTreeSet<_>>() {
        if y >= hem_y {
            continue;
        }
        let row = points
            .iter()
            .filter_map(|(x, point_y)| (*point_y == y).then_some(*x))
            .collect::<BTreeSet<_>>();
        if let (Some(min_x), Some(max_x)) = (row.first(), row.last()) {
            for x in min_x + 1..*max_x {
                if !row.contains(&x) && row.contains(&(x - 1)) && row.contains(&(x + 1)) {
                    cracks.push((x, y));
                }
            }
        }
    }
    cracks
}

fn core_crack_neighbor_regions(
    sample: &wizard_avatar_engine::pose::PoseSample,
) -> Vec<GapRegionTrace> {
    core_vertical_cracks(sample)
        .into_iter()
        .map(|point @ (x, y)| {
            let regions = sample
                .region_points
                .iter()
                .flat_map(|(region, points)| {
                    [-1, 1]
                        .into_iter()
                        .filter(move |dx| points.contains(&(x + dx, y)))
                        .map(move |dx| (*region, dx))
                })
                .collect();
            (point, regions)
        })
        .collect()
}

#[test]
fn wiz_anim_010_known_browser_source_states_have_no_internal_raster_seams() {
    let diagonal_crack = sample_pose(&WizardState {
        facing: Direction::South,
        previous_facing: Direction::South,
        facing_blend: 1.0,
        locomotion: Locomotion::Walking,
        walk_phase: 0.272_550_02,
        speed_ratio: 1.0,
        contact_marker: ContactMarker::LeftPassing,
        ..WizardState::default()
    })
    .expect("reproduce source frame 0203");
    let horizontal_seam = sample_pose(&WizardState {
        facing: Direction::East,
        previous_facing: Direction::SouthEast,
        facing_blend: 1.0,
        locomotion: Locomotion::Walking,
        walk_phase: 0.885_294,
        speed_ratio: 1.0,
        contact_marker: ContactMarker::LeftHeelStrike,
        ..WizardState::default()
    })
    .expect("reproduce source frame 0297");
    let diagonal_topology = analyze_pose_topology(&diagonal_crack);
    let horizontal_topology = analyze_pose_topology(&horizontal_seam);
    assert!(
        core_vertical_cracks(&diagonal_crack).is_empty(),
        "source frame 0203 state contains core cracks: {:?}, regions {:?}; frame 0297 empty scanlines: {:?}; horizontal seams: {:?} at {:?}, regions {:?}",
        core_vertical_cracks(&diagonal_crack),
        core_crack_neighbor_regions(&diagonal_crack),
        empty_internal_rows(&horizontal_seam),
        horizontal_seam_rows(&horizontal_seam),
        horizontal_seam_points(&horizontal_seam),
        seam_neighbor_regions(&horizontal_seam)
    );
    assert!(
        empty_internal_rows(&horizontal_seam).is_empty(),
        "source frame 0297 state contains empty scanlines: {:?}",
        empty_internal_rows(&horizontal_seam)
    );
    assert!(
        horizontal_seam_rows(&horizontal_seam).is_empty(),
        "source frame 0297 state contains horizontal seams: {:?}",
        horizontal_seam_rows(&horizontal_seam)
    );
    for topology in [diagonal_topology, horizontal_topology] {
        assert_eq!(topology.horizontal_seam_rows, 0);
        assert_eq!(topology.vertical_crack_cells, 0);
        assert_eq!(topology.staff_components, 1, "{topology:?}");
        assert_eq!(topology.staff_scanline_gaps, 0, "{topology:?}");
    }
}

#[test]
fn wiz_anim_011_action_blends_preserve_core_and_staff_connectivity() {
    for step in 0..=16 {
        let blend = step as f32 / 16.0;
        for (previous_action, action, previous_staff, staff) in [
            (
                UpperBodyAction::None,
                UpperBodyAction::Cast,
                StaffState::Held,
                StaffState::Cast,
            ),
            (
                UpperBodyAction::Cast,
                UpperBodyAction::None,
                StaffState::Cast,
                StaffState::Held,
            ),
        ] {
            let sample = sample_pose(&WizardState {
                previous_upper_body_action: previous_action,
                upper_body_action: action,
                upper_body_blend: blend,
                previous_staff_state: previous_staff,
                staff_state: staff,
                staff_blend: blend,
                ..WizardState::default()
            })
            .expect("sample cast transition");
            let topology = analyze_pose_topology(&sample);
            assert_eq!(topology.horizontal_seam_rows, 0, "{blend}: {topology:?}");
            assert_eq!(topology.vertical_crack_cells, 0, "{blend}: {topology:?}");
            assert_eq!(topology.staff_components, 1, "{blend}: {topology:?}");
            assert_eq!(topology.staff_scanline_gaps, 0, "{blend}: {topology:?}");
        }
    }
}

fn walking_sample(
    direction: Direction,
    phase: f32,
    speed_ratio: f32,
) -> wizard_avatar_engine::pose::PoseSample {
    sample_pose(&WizardState {
        facing: direction,
        previous_facing: direction,
        locomotion: Locomotion::Walking,
        walk_phase: phase,
        speed_ratio,
        contact_marker: ContactMarker::from_phase(phase),
        ..WizardState::default()
    })
    .expect("walking pose")
}

#[test]
fn wiz_gait_001_quarters_separate_body_robe_arms_and_boots() {
    let support_left = walking_sample(Direction::South, 0.0, 1.0);
    let passing_left = walking_sample(Direction::South, 0.25, 1.0);
    let support_right = walking_sample(Direction::South, 0.5, 1.0);
    let passing_right = walking_sample(Direction::South, 0.75, 1.0);

    assert_eq!(
        support_left.anchors[&AnchorId::ContactRoot].round(),
        support_left.root
    );
    assert_eq!(
        passing_left.anchors[&AnchorId::ContactRoot].round(),
        passing_left.root
    );
    assert!(
        support_left.anchors[&AnchorId::Root].y - passing_left.anchors[&AnchorId::Root].y >= 3.0,
        "visual root should compress in support and rise in passing"
    );
    assert!(
        (support_left.anchors[&AnchorId::Pelvis].x - support_right.anchors[&AnchorId::Pelvis].x)
            .abs()
            >= 2.0,
        "pelvis should transfer weight between stance sides"
    );

    let support_robe = support_left.region_bounds[&RegionId::Robe];
    let passing_robe = passing_left.region_bounds[&RegionId::Robe];
    assert!(passing_robe.width() >= support_robe.width() + 4);
    assert_ne!(passing_robe, support_robe);

    let free_forward = passing_left.anchors[&AnchorId::RightWrist];
    let free_back = passing_right.anchors[&AnchorId::RightWrist];
    assert!((free_forward.x - free_back.x).abs() >= 5.0);
    assert!((free_forward.y - free_back.y).abs() >= 2.0);

    let grip_delta = |sample: &wizard_avatar_engine::pose::PoseSample| {
        let grip = sample.anchors[&AnchorId::StaffHand];
        let wrist = sample.anchors[&AnchorId::LeftWrist];
        (grip.x - wrist.x, grip.y - wrist.y)
    };
    let grip_forward = grip_delta(&passing_left);
    let grip_back = grip_delta(&passing_right);
    assert!((grip_forward.0 - grip_back.0).abs() < 0.001);
    assert!((grip_forward.1 - grip_back.1).abs() < 0.001);
    let hand_travel = (passing_left.anchors[&AnchorId::StaffHand].x
        - passing_right.anchors[&AnchorId::StaffHand].x)
        .abs();
    let tip_travel = (passing_left.anchors[&AnchorId::StaffTop].x
        - passing_right.anchors[&AnchorId::StaffTop].x)
        .abs();
    assert!(tip_travel < hand_travel);

    let left_swing = passing_right.region_bounds[&RegionId::LeftBoot];
    let left_support = support_left.region_bounds[&RegionId::LeftBoot];
    assert!(left_swing.min_y <= left_support.min_y - 2);
    assert_ne!(
        support_left.region_bounds[&RegionId::LeftBoot],
        support_right.region_bounds[&RegionId::LeftBoot]
    );

    let silhouettes = [support_left, passing_left, support_right, passing_right]
        .into_iter()
        .map(|sample| sample.canvas.to_frame_bytes())
        .collect::<BTreeSet<_>>();
    assert_eq!(silhouettes.len(), 4);
}

#[test]
fn wiz_gait_002_stride_axis_changes_for_front_side_and_diagonal_views() {
    let displacement = |direction| {
        let heel = walking_sample(direction, 0.875, 1.0).anchors[&AnchorId::LeftFoot];
        let toe = walking_sample(direction, 0.249, 1.0).anchors[&AnchorId::LeftFoot];
        (heel.x - toe.x, heel.y - toe.y)
    };
    let south = displacement(Direction::South);
    let east = displacement(Direction::East);
    let southeast = displacement(Direction::SouthEast);
    assert!(south.1.abs() > south.0.abs());
    assert!(east.0.abs() > east.1.abs() * 8.0);
    assert!(southeast.0.abs() >= 6.0 && southeast.1.abs() >= 1.0);
}

#[test]
fn wiz_gait_003_speed_ratio_ramps_from_idle_without_a_pose_jump() {
    let idle = walking_sample(Direction::South, 0.25, 0.0);
    let low = walking_sample(Direction::South, 0.25, 0.1);
    let medium = walking_sample(Direction::South, 0.25, 0.5);
    let full = walking_sample(Direction::South, 0.25, 1.0);
    let displacement = |sample: &wizard_avatar_engine::pose::PoseSample| {
        (sample.anchors[&AnchorId::Root].y - sample.anchors[&AnchorId::ContactRoot].y).abs()
    };
    assert_eq!(displacement(&idle), 0.0);
    assert!(displacement(&low) < displacement(&medium));
    assert!(displacement(&medium) < displacement(&full));
    let resting = sample_pose(&WizardState::default()).expect("idle pose");
    assert_eq!(
        idle.canvas.to_frame_bytes(),
        resting.canvas.to_frame_bytes()
    );
}
