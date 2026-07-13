use crate::error::{PoseToolError, Result};
use crate::model::{
    AnchorId, AttachmentEdge, CanonicalConfig, CellPayload, ContactKind, ContactMode, ContactPoint,
    ContactSet, FacingMetadata, FeaturePresence, MotionFamily, MotionMetadata, NamedAnchor, Point,
    RegionId, SemanticCellPayload,
};
use crate::spec::{Landmarks, PoseSpec};
use std::collections::{BTreeMap, BTreeSet};

const ANCHOR_NEAR_DISTANCE: i64 = 100;
const ROOT_NEAR_DISTANCE: i64 = 400;

pub(crate) struct SemanticParts {
    pub motion: MotionMetadata,
    pub facing: FacingMetadata,
    pub presence: FeaturePresence,
    pub anchors: Vec<NamedAnchor>,
    pub contact_sets: Vec<ContactSet>,
    pub attachment_edges: Vec<AttachmentEdge>,
    pub z_order: Vec<RegionId>,
    pub cells: Vec<SemanticCellPayload>,
}

#[derive(Clone, Debug)]
struct StaffPath {
    top: Point,
    hand: Point,
    authored_tail: Option<AuthoredStaffTail>,
    primary: BTreeSet<Point>,
    continuation: BTreeSet<Point>,
}

#[derive(Clone, Copy, Debug)]
struct AuthoredStaffTail {
    point: Point,
    corridor_radius_squared: i64,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct StaffTopologyMetrics {
    pub component_count: usize,
    pub off_axis_cells: usize,
    pub unexplained_axis_gaps: usize,
}

pub(crate) fn compile_semantics(
    spec: &PoseSpec,
    cells: &[CellPayload],
    canonical: CanonicalConfig,
) -> Result<SemanticParts> {
    let authored_anchors = derive_anchors(spec.landmarks, canonical);
    let raw_anchors = apply_staff_anchor_overrides(
        spec.semantic_id,
        refine_body_anchors(authored_anchors, cells, canonical),
    );
    let initial_cells = segment_cells(spec, cells, &raw_anchors);
    let staff_anchors = snap_staff_anchors(raw_anchors, &initial_cells, spec.effect);
    let mut semantic_cells = segment_cells(spec, cells, &staff_anchors);
    ensure_required_regions(spec, &mut semantic_cells, &staff_anchors)?;
    let anchors = snap_anchors(staff_anchors, &semantic_cells, spec.effect);
    bridge_staff_axis(&anchors, &mut semantic_cells);
    let contact_sets = contact_sets(spec.contact_mode, &anchors, &semantic_cells)?;
    let attachment_edges = attachment_edges(&anchors, spec.effect);
    let presence = FeaturePresence {
        staff: true,
        effect: spec.effect,
    };
    let parts = SemanticParts {
        motion: MotionMetadata {
            family: spec.family,
            contact_mode: spec.contact_mode,
            phase: spec.phase,
            authored_transition_neighbors: spec
                .neighbors
                .iter()
                .map(|neighbor| (*neighbor).to_string())
                .collect(),
        },
        facing: FacingMetadata {
            direction: spec.direction,
            view_family: spec.view_family.to_string(),
        },
        presence,
        anchors,
        contact_sets,
        attachment_edges,
        z_order: RegionId::Z_ORDER.to_vec(),
        cells: semantic_cells,
    };
    validate_semantics(spec.semantic_id, &parts, canonical)?;
    Ok(parts)
}

fn bridge_staff_axis(anchors: &[NamedAnchor], cells: &mut Vec<SemanticCellPayload>) {
    let map = anchor_map(anchors);
    let top = map[&AnchorId::StaffTop];
    let hand = map[&AnchorId::StaffHand];
    for point in discrete_line(top, hand) {
        let occupied = cells
            .iter()
            .any(|cell| cell.x == point.x && cell.y == point.y);
        if occupied {
            continue;
        }
        cells.push(SemanticCellPayload {
            x: point.x,
            y: point.y,
            rgb: [126, 73, 24],
            region: RegionId::Staff,
        });
    }
    cells.sort_by_key(|cell| (cell.y, cell.x, cell.rgb));
}

fn derive_anchors(landmarks: Landmarks, canonical: CanonicalConfig) -> Vec<NamedAnchor> {
    let root = canonical.root;
    let absolute = |offset: Point| clamp(add(root, offset), canonical);
    let mouth = absolute(landmarks.mouth);
    let left_eye = absolute(landmarks.left_eye);
    let right_eye = absolute(landmarks.right_eye);
    let left_foot = absolute(landmarks.left_foot);
    let right_foot = absolute(landmarks.right_foot);
    let left_wrist = absolute(landmarks.left_hand);
    let right_wrist = absolute(landmarks.right_hand);
    let staff_hand = absolute(landmarks.staff_hand);
    let staff_top = absolute(landmarks.staff_top);

    let eye_midpoint = midpoint(left_eye, right_eye);
    let head = clamp(
        Point {
            x: eye_midpoint.x,
            y: eye_midpoint.y + 3,
        },
        canonical,
    );
    let chest = clamp(
        Point {
            x: mouth.x,
            y: mouth.y + 13,
        },
        canonical,
    );
    let pelvis = clamp(
        Point {
            x: (left_foot.x + right_foot.x + mouth.x) / 3,
            y: ((mouth.y + left_foot.y.min(right_foot.y)) / 2 + 3).min(root.y - 8),
        },
        canonical,
    );
    let left_shoulder = clamp(
        Point {
            x: chest.x - 7,
            y: chest.y - 2,
        },
        canonical,
    );
    let right_shoulder = clamp(
        Point {
            x: chest.x + 7,
            y: chest.y - 2,
        },
        canonical,
    );
    let left_hip = clamp(
        Point {
            x: pelvis.x - 5,
            y: pelvis.y,
        },
        canonical,
    );
    let right_hip = clamp(
        Point {
            x: pelvis.x + 5,
            y: pelvis.y,
        },
        canonical,
    );
    let left_ankle = clamp(
        Point {
            x: left_foot.x,
            y: left_foot.y - 2,
        },
        canonical,
    );
    let right_ankle = clamp(
        Point {
            x: right_foot.x,
            y: right_foot.y - 2,
        },
        canonical,
    );

    let points = [
        (AnchorId::Root, root),
        (AnchorId::ContactRoot, root),
        (AnchorId::Pelvis, pelvis),
        (AnchorId::Chest, chest),
        (AnchorId::Head, head),
        (AnchorId::LeftShoulder, left_shoulder),
        (AnchorId::LeftElbow, midpoint(left_shoulder, left_wrist)),
        (AnchorId::LeftWrist, left_wrist),
        (AnchorId::RightShoulder, right_shoulder),
        (AnchorId::RightElbow, midpoint(right_shoulder, right_wrist)),
        (AnchorId::RightWrist, right_wrist),
        (AnchorId::LeftHip, left_hip),
        (AnchorId::LeftKnee, midpoint(left_hip, left_ankle)),
        (AnchorId::LeftAnkle, left_ankle),
        (AnchorId::LeftFoot, left_foot),
        (AnchorId::RightHip, right_hip),
        (AnchorId::RightKnee, midpoint(right_hip, right_ankle)),
        (AnchorId::RightAnkle, right_ankle),
        (AnchorId::RightFoot, right_foot),
        (AnchorId::LeftEye, left_eye),
        (AnchorId::RightEye, right_eye),
        (AnchorId::Mouth, mouth),
        (AnchorId::StaffHand, staff_hand),
        (AnchorId::StaffTop, staff_top),
        (AnchorId::EffectOrigin, staff_top),
    ];
    points
        .into_iter()
        .map(|(id, point)| NamedAnchor { id, point })
        .collect()
}

fn refine_body_anchors(
    anchors: Vec<NamedAnchor>,
    cells: &[CellPayload],
    canonical: CanonicalConfig,
) -> Vec<NamedAnchor> {
    let mut map = anchor_map(&anchors);
    let authored_head = map[&AnchorId::Head];
    let Some(face_center) = densest_face_cluster(cells, authored_head) else {
        return anchors;
    };
    let authored_left_eye = map[&AnchorId::LeftEye];
    let authored_right_eye = map[&AnchorId::RightEye];
    let eye_half_width = ((authored_right_eye.x - authored_left_eye.x).abs() / 2).clamp(3, 6);
    let left_eye = clamp(
        Point {
            x: face_center.x - eye_half_width,
            y: face_center.y - 2,
        },
        canonical,
    );
    let right_eye = clamp(
        Point {
            x: face_center.x + eye_half_width,
            y: face_center.y - 2,
        },
        canonical,
    );
    let mouth = clamp(
        Point {
            x: face_center.x,
            y: face_center.y + 4,
        },
        canonical,
    );
    let head = clamp(face_center, canonical);
    let foot_midpoint = midpoint(map[&AnchorId::LeftFoot], map[&AnchorId::RightFoot]);
    let pelvis = clamp(midpoint(mouth, foot_midpoint), canonical);
    let chest = clamp(midpoint(mouth, pelvis), canonical);
    let left_shoulder = clamp(toward(chest, map[&AnchorId::LeftWrist], 1, 3), canonical);
    let right_shoulder = clamp(toward(chest, map[&AnchorId::RightWrist], 1, 3), canonical);
    let left_hip = clamp(toward(pelvis, map[&AnchorId::LeftFoot], 1, 4), canonical);
    let right_hip = clamp(toward(pelvis, map[&AnchorId::RightFoot], 1, 4), canonical);
    let left_ankle = clamp(toward(map[&AnchorId::LeftFoot], left_hip, 1, 8), canonical);
    let right_ankle = clamp(
        toward(map[&AnchorId::RightFoot], right_hip, 1, 8),
        canonical,
    );

    for (id, point) in [
        (AnchorId::Head, head),
        (AnchorId::LeftEye, left_eye),
        (AnchorId::RightEye, right_eye),
        (AnchorId::Mouth, mouth),
        (AnchorId::Chest, chest),
        (AnchorId::Pelvis, pelvis),
        (AnchorId::LeftShoulder, left_shoulder),
        (
            AnchorId::LeftElbow,
            midpoint(left_shoulder, map[&AnchorId::LeftWrist]),
        ),
        (AnchorId::RightShoulder, right_shoulder),
        (
            AnchorId::RightElbow,
            midpoint(right_shoulder, map[&AnchorId::RightWrist]),
        ),
        (AnchorId::LeftHip, left_hip),
        (AnchorId::LeftKnee, midpoint(left_hip, left_ankle)),
        (AnchorId::LeftAnkle, left_ankle),
        (AnchorId::RightHip, right_hip),
        (AnchorId::RightKnee, midpoint(right_hip, right_ankle)),
        (AnchorId::RightAnkle, right_ankle),
    ] {
        map.insert(id, point);
    }
    AnchorId::REQUIRED
        .iter()
        .map(|id| NamedAnchor {
            id: *id,
            point: map[id],
        })
        .collect()
}

fn densest_face_cluster(cells: &[CellPayload], authored_head: Point) -> Option<Point> {
    let candidates = cells
        .iter()
        .filter(|cell| is_skin_color(cell.rgb) || is_brown(cell.rgb))
        .filter(|cell| cell.y < 84)
        .collect::<Vec<_>>();
    let center = candidates.iter().max_by_key(|candidate| {
        let point = Point {
            x: candidate.x,
            y: candidate.y,
        };
        let local_population = candidates
            .iter()
            .filter(|neighbor| {
                distance_squared(
                    point,
                    Point {
                        x: neighbor.x,
                        y: neighbor.y,
                    },
                ) <= 64
            })
            .count() as i64;
        let authored_penalty = i64::from((candidate.x - authored_head.x).abs()) * 2;
        (
            local_population * 100 - authored_penalty,
            -candidate.y,
            -candidate.x,
        )
    })?;
    let center_point = Point {
        x: center.x,
        y: center.y,
    };
    let cluster = candidates
        .iter()
        .filter(|cell| {
            distance_squared(
                center_point,
                Point {
                    x: cell.x,
                    y: cell.y,
                },
            ) <= 64
        })
        .collect::<Vec<_>>();
    let count = cluster.len() as i32;
    (count > 0).then(|| Point {
        x: cluster.iter().map(|cell| cell.x).sum::<i32>() / count,
        y: cluster.iter().map(|cell| cell.y).sum::<i32>() / count,
    })
}

fn segment_cells(
    spec: &PoseSpec,
    cells: &[CellPayload],
    anchors: &[NamedAnchor],
) -> Vec<SemanticCellPayload> {
    let map = anchor_map(anchors);
    let chest = map[&AnchorId::Chest];
    let pelvis = map[&AnchorId::Pelvis];
    let head = map[&AnchorId::Head];
    let mouth = map[&AnchorId::Mouth];
    let eyes_y = map[&AnchorId::LeftEye].y.min(map[&AnchorId::RightEye].y);
    let left_arm = [
        map[&AnchorId::LeftShoulder],
        map[&AnchorId::LeftElbow],
        map[&AnchorId::LeftWrist],
    ];
    let right_arm = [
        map[&AnchorId::RightShoulder],
        map[&AnchorId::RightElbow],
        map[&AnchorId::RightWrist],
    ];
    let left_leg = [
        map[&AnchorId::LeftHip],
        map[&AnchorId::LeftKnee],
        map[&AnchorId::LeftAnkle],
    ];
    let right_leg = [
        map[&AnchorId::RightHip],
        map[&AnchorId::RightKnee],
        map[&AnchorId::RightAnkle],
    ];
    let staff_top = map[&AnchorId::StaffTop];
    let staff_hand = map[&AnchorId::StaffHand];
    let staff_path = derive_staff_path(
        staff_top,
        staff_hand,
        authored_staff_tail(spec.semantic_id, map[&AnchorId::Root]),
        cells,
    );

    cells
        .iter()
        .map(|cell| {
            let point = Point {
                x: cell.x,
                y: cell.y,
            };
            let far_from_body = (point.x - chest.x).abs() >= 11;
            let in_wing_band = point.y >= eyes_y - 2 && point.y <= pelvis.y + 8;
            let near_staff = staff_path_contains(&staff_path, point, cell.rgb);
            let region = if spec.effect
                && distance_squared(point, staff_top) <= 225
                && is_effect_color(cell.rgb)
                && !near_staff
            {
                RegionId::Effect
            } else if near_staff {
                RegionId::Staff
            } else if point.y <= eyes_y - 3
                && (point.x - head.x).abs() <= 13
                && (is_blue(cell.rgb) || is_yellow(cell.rgb))
            {
                RegionId::Hat
            } else if distance_squared(point, mouth) <= 9 && is_mouth_color(cell.rgb) {
                RegionId::Mouth
            } else if point.y >= eyes_y - 4
                && point.y <= mouth.y + 2
                && (point.x - head.x).abs() <= 9
                && is_skin_color(cell.rgb)
            {
                RegionId::Face
            } else if point.y >= mouth.y - 3
                && point.y <= chest.y + 4
                && (point.x - head.x).abs() <= 11
                && is_brown(cell.rgb)
            {
                RegionId::Beard
            } else if distance_squared(point, head) <= 150
                && point.y <= mouth.y + 4
                && is_skin_color(cell.rgb)
            {
                RegionId::Head
            } else if distance_squared(point, map[&AnchorId::LeftFoot]) <= 72
                && point.y >= map[&AnchorId::LeftAnkle].y - 2
                && is_brown(cell.rgb)
            {
                RegionId::LeftBoot
            } else if distance_squared(point, map[&AnchorId::RightFoot]) <= 72
                && point.y >= map[&AnchorId::RightAnkle].y - 2
                && is_brown(cell.rgb)
            {
                RegionId::RightBoot
            } else if far_from_body && in_wing_band && is_adornment_color(cell.rgb) {
                if point.x < chest.x {
                    RegionId::AdornmentLeft
                } else {
                    RegionId::AdornmentRight
                }
            } else if polyline_distance_score(point, &left_arm) <= 45
                && polyline_distance_score(point, &left_arm)
                    <= polyline_distance_score(point, &right_arm)
                && point.y <= pelvis.y + 4
            {
                RegionId::LeftArm
            } else if polyline_distance_score(point, &right_arm) <= 45 && point.y <= pelvis.y + 4 {
                RegionId::RightArm
            } else if far_from_body && in_wing_band {
                if point.x < chest.x {
                    RegionId::AdornmentLeft
                } else {
                    RegionId::AdornmentRight
                }
            } else if polyline_distance_score(point, &left_leg)
                <= polyline_distance_score(point, &right_leg)
                && point.y >= pelvis.y - 2
                && (point.x - pelvis.x).abs() >= 3
            {
                RegionId::LeftLeg
            } else if point.y >= pelvis.y - 2 && (point.x - pelvis.x).abs() >= 3 {
                RegionId::RightLeg
            } else if is_inner_robe_color(cell.rgb) && point.y >= chest.y - 2 {
                RegionId::InnerRobe
            } else if point.y >= pelvis.y - 3 {
                RegionId::Robe
            } else {
                RegionId::Torso
            };
            SemanticCellPayload {
                x: cell.x,
                y: cell.y,
                rgb: cell.rgb,
                region,
            }
        })
        .collect()
}

fn ensure_required_regions(
    spec: &PoseSpec,
    cells: &mut [SemanticCellPayload],
    anchors: &[NamedAnchor],
) -> Result<()> {
    let mut required = RegionId::ALL.to_vec();
    if !spec.effect {
        required.retain(|region| *region != RegionId::Effect);
    }
    let mut reserved = BTreeSet::new();
    for region in required {
        if cells.iter().any(|cell| cell.region == region) {
            continue;
        }
        if region == RegionId::Staff {
            return Err(PoseToolError::Raster(format!(
                "{} has no coherent staff cells",
                spec.semantic_id
            )));
        }
        let seed = region_seed(region, anchors);
        let candidate = cells
            .iter()
            .enumerate()
            .filter(|(index, cell)| {
                !reserved.contains(index)
                    && cell.region != RegionId::Staff
                    && cell.region != RegionId::Effect
            })
            .min_by_key(|(_, cell)| {
                distance_squared(
                    Point {
                        x: cell.x,
                        y: cell.y,
                    },
                    seed,
                )
            })
            .map(|(index, _)| index)
            .ok_or_else(|| {
                PoseToolError::Raster(format!(
                    "{} has no cell available to seed {region:?}",
                    spec.semantic_id
                ))
            })?;
        cells[candidate].region = region;
        reserved.insert(candidate);
    }
    Ok(())
}

fn snap_anchors(
    anchors: Vec<NamedAnchor>,
    cells: &[SemanticCellPayload],
    effect_present: bool,
) -> Vec<NamedAnchor> {
    anchors
        .into_iter()
        .map(|mut anchor| {
            if matches!(
                anchor.id,
                AnchorId::Root | AnchorId::ContactRoot | AnchorId::StaffHand | AnchorId::StaffTop
            ) || anchor.id == AnchorId::EffectOrigin && !effect_present
            {
                return anchor;
            }
            let regions = anchor_regions(anchor.id, effect_present);
            if let Some(cell) = cells
                .iter()
                .filter(|cell| regions.contains(&cell.region))
                .min_by_key(|cell| {
                    distance_squared(
                        Point {
                            x: cell.x,
                            y: cell.y,
                        },
                        anchor.point,
                    )
                })
            {
                let candidate = Point {
                    x: cell.x,
                    y: cell.y,
                };
                if distance_squared(candidate, anchor.point) > 16 {
                    anchor.point = candidate;
                }
            }
            anchor
        })
        .collect()
}

fn snap_staff_anchors(
    mut anchors: Vec<NamedAnchor>,
    cells: &[SemanticCellPayload],
    effect_present: bool,
) -> Vec<NamedAnchor> {
    for anchor in &mut anchors {
        if !matches!(anchor.id, AnchorId::StaffHand | AnchorId::StaffTop) {
            continue;
        }
        if let Some(cell) = cells
            .iter()
            .filter(|cell| cell.region == RegionId::Staff)
            .min_by_key(|cell| {
                distance_squared(
                    Point {
                        x: cell.x,
                        y: cell.y,
                    },
                    anchor.point,
                )
            })
        {
            anchor.point = Point {
                x: cell.x,
                y: cell.y,
            };
        }
    }
    if !effect_present {
        let staff_top = anchors
            .iter()
            .find(|anchor| anchor.id == AnchorId::StaffTop)
            .map(|anchor| anchor.point);
        if let (Some(staff_top), Some(effect_origin)) = (
            staff_top,
            anchors
                .iter_mut()
                .find(|anchor| anchor.id == AnchorId::EffectOrigin),
        ) {
            effect_origin.point = staff_top;
        }
    }
    anchors
}

fn contact_sets(
    mode: ContactMode,
    anchors: &[NamedAnchor],
    cells: &[SemanticCellPayload],
) -> Result<Vec<ContactSet>> {
    if mode == ContactMode::Airborne {
        return Ok(Vec::new());
    }
    let map = anchor_map(anchors);
    let mut points = Vec::new();
    let mut add = |anchor: AnchorId, kind: ContactKind, point: Point| {
        points.push(ContactPoint {
            anchor,
            kind,
            point,
        });
    };
    match mode {
        ContactMode::Airborne => unreachable!("handled above"),
        ContactMode::LeftFoot => add(
            AnchorId::LeftFoot,
            ContactKind::Ground,
            map[&AnchorId::LeftFoot],
        ),
        ContactMode::RightFoot => add(
            AnchorId::RightFoot,
            ContactKind::Ground,
            map[&AnchorId::RightFoot],
        ),
        ContactMode::BothFeet => {
            add(
                AnchorId::LeftFoot,
                ContactKind::Ground,
                map[&AnchorId::LeftFoot],
            );
            add(
                AnchorId::RightFoot,
                ContactKind::Ground,
                map[&AnchorId::RightFoot],
            );
        }
        ContactMode::BothFeetAndStaff | ContactMode::KneelAndStaff => {
            add(
                AnchorId::LeftFoot,
                ContactKind::Ground,
                map[&AnchorId::LeftFoot],
            );
            add(
                AnchorId::RightFoot,
                ContactKind::Ground,
                map[&AnchorId::RightFoot],
            );
            add(
                AnchorId::StaffHand,
                ContactKind::Brace,
                staff_ground_point(cells)?,
            );
        }
        ContactMode::HandFootAndStaff => {
            add(
                AnchorId::LeftWrist,
                ContactKind::Brace,
                map[&AnchorId::LeftWrist],
            );
            add(
                AnchorId::LeftFoot,
                ContactKind::Ground,
                map[&AnchorId::LeftFoot],
            );
            add(
                AnchorId::RightFoot,
                ContactKind::Ground,
                map[&AnchorId::RightFoot],
            );
            add(
                AnchorId::StaffHand,
                ContactKind::Brace,
                staff_ground_point(cells)?,
            );
        }
    }
    Ok(vec![ContactSet {
        id: "primary".to_string(),
        points,
    }])
}

fn staff_ground_point(cells: &[SemanticCellPayload]) -> Result<Point> {
    cells
        .iter()
        .filter(|cell| cell.region == RegionId::Staff)
        .max_by_key(|cell| (cell.y, cell.x))
        .map(|cell| Point {
            x: cell.x,
            y: cell.y,
        })
        .ok_or_else(|| PoseToolError::Raster("staff contact requested without staff cells".into()))
}

fn attachment_edges(anchors: &[NamedAnchor], effect: bool) -> Vec<AttachmentEdge> {
    let map = anchor_map(anchors);
    let staff_parent = if distance_squared(map[&AnchorId::StaffHand], map[&AnchorId::LeftWrist])
        <= distance_squared(map[&AnchorId::StaffHand], map[&AnchorId::RightWrist])
    {
        RegionId::LeftArm
    } else {
        RegionId::RightArm
    };
    let mut edges = vec![
        edge(
            RegionId::Torso,
            RegionId::Head,
            AnchorId::Chest,
            AnchorId::Head,
        ),
        edge(
            RegionId::Head,
            RegionId::Hat,
            AnchorId::Head,
            AnchorId::Head,
        ),
        edge(
            RegionId::Head,
            RegionId::Beard,
            AnchorId::Head,
            AnchorId::Mouth,
        ),
        edge(
            RegionId::Head,
            RegionId::Face,
            AnchorId::Head,
            AnchorId::Mouth,
        ),
        edge(
            RegionId::Face,
            RegionId::Mouth,
            AnchorId::Mouth,
            AnchorId::Mouth,
        ),
        edge(
            RegionId::Torso,
            RegionId::Robe,
            AnchorId::Chest,
            AnchorId::Pelvis,
        ),
        edge(
            RegionId::Robe,
            RegionId::InnerRobe,
            AnchorId::Pelvis,
            AnchorId::Pelvis,
        ),
        edge(
            RegionId::Torso,
            RegionId::LeftArm,
            AnchorId::Chest,
            AnchorId::LeftShoulder,
        ),
        edge(
            RegionId::Torso,
            RegionId::RightArm,
            AnchorId::Chest,
            AnchorId::RightShoulder,
        ),
        edge(
            RegionId::Robe,
            RegionId::LeftLeg,
            AnchorId::Pelvis,
            AnchorId::LeftHip,
        ),
        edge(
            RegionId::Robe,
            RegionId::RightLeg,
            AnchorId::Pelvis,
            AnchorId::RightHip,
        ),
        edge(
            RegionId::LeftLeg,
            RegionId::LeftBoot,
            AnchorId::LeftAnkle,
            AnchorId::LeftFoot,
        ),
        edge(
            RegionId::RightLeg,
            RegionId::RightBoot,
            AnchorId::RightAnkle,
            AnchorId::RightFoot,
        ),
        edge(
            RegionId::Torso,
            RegionId::AdornmentLeft,
            AnchorId::Chest,
            AnchorId::LeftShoulder,
        ),
        edge(
            RegionId::Torso,
            RegionId::AdornmentRight,
            AnchorId::Chest,
            AnchorId::RightShoulder,
        ),
        edge(
            staff_parent,
            RegionId::Staff,
            AnchorId::StaffHand,
            AnchorId::StaffHand,
        ),
    ];
    if effect {
        edges.push(edge(
            RegionId::Staff,
            RegionId::Effect,
            AnchorId::StaffTop,
            AnchorId::EffectOrigin,
        ));
    }
    edges
}

const fn edge(
    parent_region: RegionId,
    child_region: RegionId,
    parent_anchor: AnchorId,
    child_anchor: AnchorId,
) -> AttachmentEdge {
    AttachmentEdge {
        parent_region,
        child_region,
        parent_anchor,
        child_anchor,
    }
}

pub(crate) fn validate_semantics(
    semantic_id: &str,
    parts: &SemanticParts,
    canonical: CanonicalConfig,
) -> Result<()> {
    if parts.anchors.len() != AnchorId::REQUIRED.len()
        || !AnchorId::REQUIRED.iter().all(|id| {
            parts
                .anchors
                .iter()
                .filter(|anchor| anchor.id == *id)
                .count()
                == 1
        })
    {
        return Err(PoseToolError::Raster(format!(
            "{semantic_id} does not define all 25 anchors exactly once"
        )));
    }
    for anchor in &parts.anchors {
        if anchor.point.x < 0
            || anchor.point.y < 0
            || anchor.point.x >= canonical.cols as i32
            || anchor.point.y >= canonical.rows as i32
        {
            return Err(PoseToolError::Raster(format!(
                "{semantic_id} {:?} is outside canonical bounds",
                anchor.id
            )));
        }
        let regions = anchor_regions(anchor.id, parts.presence.effect);
        let nearest = parts
            .cells
            .iter()
            .filter(|cell| regions.contains(&cell.region))
            .map(|cell| {
                distance_squared(
                    anchor.point,
                    Point {
                        x: cell.x,
                        y: cell.y,
                    },
                )
            })
            .min()
            .unwrap_or(i64::MAX);
        let limit = if matches!(anchor.id, AnchorId::Root | AnchorId::ContactRoot) {
            ROOT_NEAR_DISTANCE
        } else {
            ANCHOR_NEAR_DISTANCE
        };
        if nearest > limit {
            return Err(PoseToolError::Raster(format!(
                "{semantic_id} {:?} is not plausibly near {:?}: squared distance {nearest}",
                anchor.id, regions
            )));
        }
    }

    let occupied = parts
        .cells
        .iter()
        .map(|cell| (cell.x, cell.y))
        .collect::<BTreeSet<_>>();
    if occupied.len() != parts.cells.len() {
        return Err(PoseToolError::Raster(format!(
            "{semantic_id} contains duplicate occupied coordinates"
        )));
    }
    let mut required_regions = RegionId::ALL.to_vec();
    if !parts.presence.effect {
        required_regions.retain(|region| *region != RegionId::Effect);
    }
    for region in required_regions {
        if !parts.cells.iter().any(|cell| cell.region == region) {
            return Err(PoseToolError::Raster(format!(
                "{semantic_id} has no cells for {region:?}"
            )));
        }
    }
    if !parts.presence.effect
        && parts
            .cells
            .iter()
            .any(|cell| cell.region == RegionId::Effect)
    {
        return Err(PoseToolError::Raster(format!(
            "{semantic_id} marks effect cells while effect is absent"
        )));
    }
    if parts.presence.staff
        != parts
            .cells
            .iter()
            .any(|cell| cell.region == RegionId::Staff)
    {
        return Err(PoseToolError::Raster(format!(
            "{semantic_id} staff presence disagrees with its cells"
        )));
    }
    validate_staff_topology(semantic_id, &parts.anchors, &parts.cells)?;
    if parts.motion.contact_mode == ContactMode::Airborne {
        if !parts.contact_sets.is_empty() {
            return Err(PoseToolError::Raster(format!(
                "{semantic_id} airborne pose declares contacts"
            )));
        }
    } else if parts.contact_sets.len() != 1 || parts.contact_sets[0].points.is_empty() {
        return Err(PoseToolError::Raster(format!(
            "{semantic_id} grounded pose lacks a primary contact set"
        )));
    }
    let family_contact_valid = match parts.motion.family {
        MotionFamily::Flight | MotionFamily::Jump => {
            parts.motion.contact_mode == ContactMode::Airborne
        }
        MotionFamily::Walk => matches!(
            parts.motion.contact_mode,
            ContactMode::LeftFoot | ContactMode::RightFoot | ContactMode::BothFeet
        ),
        MotionFamily::Run => matches!(
            parts.motion.contact_mode,
            ContactMode::Airborne | ContactMode::LeftFoot | ContactMode::RightFoot
        ),
        MotionFamily::Landing => parts.motion.contact_mode == ContactMode::HandFootAndStaff,
        MotionFamily::Kneel => parts.motion.contact_mode == ContactMode::KneelAndStaff,
        MotionFamily::GroundAction => parts.motion.contact_mode != ContactMode::Airborne,
    };
    if !family_contact_valid {
        return Err(PoseToolError::Raster(format!(
            "{semantic_id} contact mode {:?} is invalid for {:?}",
            parts.motion.contact_mode, parts.motion.family
        )));
    }
    if let Some(phase) = parts.motion.phase {
        if phase.denominator == 0 || phase.numerator >= phase.denominator {
            return Err(PoseToolError::Raster(format!(
                "{semantic_id} has invalid authored phase {}/{}",
                phase.numerator, phase.denominator
            )));
        }
    }
    for set in &parts.contact_sets {
        for contact in &set.points {
            if contact.point.x < 0
                || contact.point.y < 0
                || contact.point.x >= canonical.cols as i32
                || contact.point.y >= canonical.rows as i32
            {
                return Err(PoseToolError::Raster(format!(
                    "{semantic_id} contact {:?} is out of bounds",
                    contact.anchor
                )));
            }
        }
    }
    if parts.z_order != RegionId::Z_ORDER {
        return Err(PoseToolError::Raster(format!(
            "{semantic_id} z-order does not match the engine RegionId contract"
        )));
    }
    for edge in &parts.attachment_edges {
        if !parts
            .cells
            .iter()
            .any(|cell| cell.region == edge.parent_region)
            || !parts
                .cells
                .iter()
                .any(|cell| cell.region == edge.child_region)
        {
            return Err(PoseToolError::Raster(format!(
                "{semantic_id} attachment {:?}->{:?} references an absent region",
                edge.parent_region, edge.child_region
            )));
        }
    }
    Ok(())
}

pub(crate) fn validate_staff_topology(
    semantic_id: &str,
    anchors: &[NamedAnchor],
    cells: &[SemanticCellPayload],
) -> Result<StaffTopologyMetrics> {
    let map = anchor_map(anchors);
    let source_cells = cells
        .iter()
        .map(|cell| CellPayload {
            x: cell.x,
            y: cell.y,
            rgb: cell.rgb,
        })
        .collect::<Vec<_>>();
    let path = derive_staff_path(
        map[&AnchorId::StaffTop],
        map[&AnchorId::StaffHand],
        map.get(&AnchorId::Root)
            .and_then(|root| authored_staff_tail(semantic_id, *root)),
        &source_cells,
    );
    let staff_points = cells
        .iter()
        .filter(|cell| cell.region == RegionId::Staff)
        .map(|cell| Point {
            x: cell.x,
            y: cell.y,
        })
        .collect::<BTreeSet<_>>();
    let off_axis_cells = staff_points
        .iter()
        .filter(|point| {
            let primary_distance = line_distance_score(**point, path.top, path.hand);
            primary_distance > 36
                && !path.primary.contains(point)
                && !path.continuation.contains(point)
        })
        .count();
    let primary_gaps =
        unexplained_segment_gaps(path.top, path.hand, 36, path.hand, &staff_points, cells);
    let continuation_gaps = if let Some(tail) = path.authored_tail {
        unexplained_segment_gaps(
            path.hand,
            tail.point,
            tail.corridor_radius_squared,
            path.hand,
            &staff_points,
            cells,
        )
    } else {
        path.continuation
            .iter()
            .min_by_key(|point| distance_squared(path.hand, **point))
            .map(|nearest| {
                unexplained_segment_gaps(path.hand, *nearest, 25, path.hand, &staff_points, cells)
            })
            .unwrap_or(0)
    };
    let unexplained_axis_gaps = primary_gaps + continuation_gaps;
    let metrics = StaffTopologyMetrics {
        component_count: staff_component_count(&staff_points),
        off_axis_cells,
        unexplained_axis_gaps,
    };
    if metrics.off_axis_cells != 0 {
        return Err(PoseToolError::Raster(format!(
            "{semantic_id} staff has {} off-axis semantic cells",
            metrics.off_axis_cells
        )));
    }
    if metrics.unexplained_axis_gaps != 0 {
        return Err(PoseToolError::Raster(format!(
            "{semantic_id} staff authored path has {} unexplained gaps ({primary_gaps} top-to-hand, {continuation_gaps} continuation)",
            metrics.unexplained_axis_gaps,
        )));
    }
    Ok(metrics)
}

fn unexplained_segment_gaps(
    start: Point,
    end: Point,
    staff_radius_squared: i64,
    hand: Point,
    staff_points: &BTreeSet<Point>,
    cells: &[SemanticCellPayload],
) -> usize {
    discrete_line(start, end)
        .into_iter()
        .filter(|axis_point| {
            let has_staff = staff_points
                .iter()
                .any(|point| distance_squared(*axis_point, *point) <= staff_radius_squared);
            if has_staff {
                return false;
            }
            let has_authored_occluder = cells.iter().any(|cell| {
                cell.region != RegionId::Staff
                    && distance_squared(
                        *axis_point,
                        Point {
                            x: cell.x,
                            y: cell.y,
                        },
                    ) <= 4
                    && (distance_squared(*axis_point, hand) <= 100
                        || matches!(
                            cell.region,
                            RegionId::Torso
                                | RegionId::Robe
                                | RegionId::InnerRobe
                                | RegionId::LeftArm
                                | RegionId::RightArm
                                | RegionId::Head
                                | RegionId::Hat
                                | RegionId::Beard
                                | RegionId::Face
                        ))
            });
            !has_authored_occluder
        })
        .count()
}

fn staff_component_count(points: &BTreeSet<Point>) -> usize {
    let mut unseen = points.clone();
    let mut components = 0;
    while let Some(start) = unseen.pop_first() {
        components += 1;
        let mut pending = vec![start];
        while let Some(point) = pending.pop() {
            for dy in -1..=1 {
                for dx in -1..=1 {
                    if dx == 0 && dy == 0 {
                        continue;
                    }
                    let neighbor = Point {
                        x: point.x + dx,
                        y: point.y + dy,
                    };
                    if unseen.remove(&neighbor) {
                        pending.push(neighbor);
                    }
                }
            }
        }
    }
    components
}

fn discrete_line(start: Point, end: Point) -> Vec<Point> {
    let mut points = Vec::new();
    let mut x = start.x;
    let mut y = start.y;
    let dx = (end.x - start.x).abs();
    let step_x = if start.x < end.x { 1 } else { -1 };
    let dy = -(end.y - start.y).abs();
    let step_y = if start.y < end.y { 1 } else { -1 };
    let mut error = dx + dy;
    loop {
        points.push(Point { x, y });
        if x == end.x && y == end.y {
            break;
        }
        let doubled = error * 2;
        if doubled >= dy {
            error += dy;
            x += step_x;
        }
        if doubled <= dx {
            error += dx;
            y += step_y;
        }
    }
    points
}

fn anchor_regions(anchor: AnchorId, effect_present: bool) -> &'static [RegionId] {
    match anchor {
        AnchorId::Root | AnchorId::ContactRoot => &[
            RegionId::Robe,
            RegionId::LeftLeg,
            RegionId::RightLeg,
            RegionId::LeftBoot,
            RegionId::RightBoot,
        ],
        AnchorId::Pelvis => &[RegionId::Torso, RegionId::Robe, RegionId::InnerRobe],
        AnchorId::Chest => &[RegionId::Torso],
        AnchorId::Head => &[RegionId::Head],
        AnchorId::LeftShoulder | AnchorId::LeftElbow | AnchorId::LeftWrist => &[RegionId::LeftArm],
        AnchorId::RightShoulder | AnchorId::RightElbow | AnchorId::RightWrist => {
            &[RegionId::RightArm]
        }
        AnchorId::LeftHip | AnchorId::LeftKnee | AnchorId::LeftAnkle => {
            &[RegionId::LeftLeg, RegionId::LeftBoot]
        }
        AnchorId::LeftFoot => &[RegionId::LeftBoot],
        AnchorId::RightHip | AnchorId::RightKnee | AnchorId::RightAnkle => {
            &[RegionId::RightLeg, RegionId::RightBoot]
        }
        AnchorId::RightFoot => &[RegionId::RightBoot],
        AnchorId::LeftEye | AnchorId::RightEye => &[RegionId::Face],
        AnchorId::Mouth => &[RegionId::Mouth],
        AnchorId::StaffHand | AnchorId::StaffTop => &[RegionId::Staff],
        AnchorId::EffectOrigin if effect_present => &[RegionId::Effect],
        AnchorId::EffectOrigin => &[RegionId::Staff],
    }
}

fn region_seed(region: RegionId, anchors: &[NamedAnchor]) -> Point {
    let map = anchor_map(anchors);
    match region {
        RegionId::Hat => add(map[&AnchorId::Head], Point { x: 0, y: -8 }),
        RegionId::Head => map[&AnchorId::Head],
        RegionId::Beard => add(map[&AnchorId::Mouth], Point { x: 0, y: 3 }),
        RegionId::Torso => map[&AnchorId::Chest],
        RegionId::Robe | RegionId::InnerRobe => map[&AnchorId::Pelvis],
        RegionId::LeftArm => map[&AnchorId::LeftElbow],
        RegionId::RightArm => map[&AnchorId::RightElbow],
        RegionId::LeftLeg => map[&AnchorId::LeftKnee],
        RegionId::RightLeg => map[&AnchorId::RightKnee],
        RegionId::LeftBoot => map[&AnchorId::LeftFoot],
        RegionId::RightBoot => map[&AnchorId::RightFoot],
        RegionId::Staff => map[&AnchorId::StaffHand],
        RegionId::AdornmentLeft => add(map[&AnchorId::LeftShoulder], Point { x: -8, y: 0 }),
        RegionId::AdornmentRight => add(map[&AnchorId::RightShoulder], Point { x: 8, y: 0 }),
        RegionId::Face => midpoint(map[&AnchorId::LeftEye], map[&AnchorId::RightEye]),
        RegionId::Mouth => map[&AnchorId::Mouth],
        RegionId::Effect => map[&AnchorId::EffectOrigin],
    }
}

fn anchor_map(anchors: &[NamedAnchor]) -> BTreeMap<AnchorId, Point> {
    anchors
        .iter()
        .map(|anchor| (anchor.id, anchor.point))
        .collect()
}

const fn add(left: Point, right: Point) -> Point {
    Point {
        x: left.x + right.x,
        y: left.y + right.y,
    }
}

const fn midpoint(left: Point, right: Point) -> Point {
    Point {
        x: (left.x + right.x) / 2,
        y: (left.y + right.y) / 2,
    }
}

fn toward(start: Point, end: Point, numerator: i32, denominator: i32) -> Point {
    Point {
        x: start.x + (end.x - start.x) * numerator / denominator,
        y: start.y + (end.y - start.y) * numerator / denominator,
    }
}

fn clamp(point: Point, canonical: CanonicalConfig) -> Point {
    Point {
        x: point.x.clamp(0, canonical.cols as i32 - 1),
        y: point.y.clamp(0, canonical.rows as i32 - 1),
    }
}

fn distance_squared(left: Point, right: Point) -> i64 {
    let dx = i64::from(left.x - right.x);
    let dy = i64::from(left.y - right.y);
    dx * dx + dy * dy
}

fn polyline_distance_score(point: Point, points: &[Point; 3]) -> i64 {
    line_distance_score(point, points[0], points[1])
        .min(line_distance_score(point, points[1], points[2]))
}

fn derive_staff_path(
    top: Point,
    hand: Point,
    authored_tail: Option<AuthoredStaffTail>,
    cells: &[CellPayload],
) -> StaffPath {
    let primary_dx = hand.x - top.x;
    let primary_dy = hand.y - top.y;
    let primary_candidates = cells
        .iter()
        .filter(|cell| {
            line_distance_score(
                Point {
                    x: cell.x,
                    y: cell.y,
                },
                top,
                hand,
            ) <= 16
                && is_staff_color(cell.rgb)
                && !is_bright_skin(cell.rgb)
        })
        .map(|cell| Point {
            x: cell.x,
            y: cell.y,
        })
        .collect::<BTreeSet<_>>();
    let primary_components = eight_neighbor_components(&primary_candidates);
    let mut primary = primary_components
        .iter()
        .filter(|component| {
            component.len() >= 3
                || component
                    .iter()
                    .any(|point| distance_squared(*point, top) <= 16)
                || component
                    .iter()
                    .any(|point| distance_squared(*point, hand) <= 16)
        })
        .flatten()
        .copied()
        .collect::<BTreeSet<_>>();
    let primary_axis = discrete_line(top, hand);
    for component in &primary_components {
        if component.len() >= 3 || component.iter().any(|point| primary.contains(point)) {
            continue;
        }
        let uniquely_covers_axis = primary_axis.iter().any(|axis_point| {
            component
                .iter()
                .any(|point| distance_squared(*axis_point, *point) <= 36)
                && !primary
                    .iter()
                    .any(|point| distance_squared(*axis_point, *point) <= 36)
        });
        if uniquely_covers_axis {
            primary.extend(component);
        }
    }
    if let Some(tail) = authored_tail {
        let continuation = cells
            .iter()
            .filter(|cell| {
                let point = Point {
                    x: cell.x,
                    y: cell.y,
                };
                line_distance_score(point, hand, tail.point) <= tail.corridor_radius_squared
                    && is_staff_color(cell.rgb)
                    && !is_bright_skin(cell.rgb)
            })
            .map(|cell| Point {
                x: cell.x,
                y: cell.y,
            })
            .collect();
        return StaffPath {
            top,
            hand,
            authored_tail: Some(tail),
            primary,
            continuation,
        };
    }
    if primary_dy.abs() <= primary_dx.abs() {
        return StaffPath {
            top,
            hand,
            authored_tail: None,
            primary,
            continuation: BTreeSet::new(),
        };
    }

    let outward = Point {
        x: hand.x - top.x,
        y: hand.y - top.y,
    };
    let brown_points = cells
        .iter()
        .filter(|cell| is_staff_brown(cell.rgb))
        .map(|cell| Point {
            x: cell.x,
            y: cell.y,
        })
        .collect::<BTreeSet<_>>();
    let continuation = four_neighbor_components(&brown_points)
        .into_iter()
        .filter_map(|component| {
            let nearest_distance = component
                .iter()
                .map(|point| distance_squared(hand, *point))
                .min()
                .unwrap_or(i64::MAX);
            let maximum_projection = component
                .iter()
                .map(|point| (point.x - hand.x) * outward.x + (point.y - hand.y) * outward.y)
                .max()
                .unwrap_or(i32::MIN);
            let outward_cells = component
                .iter()
                .filter(|point| (point.x - hand.x) * outward.x + (point.y - hand.y) * outward.y > 0)
                .count();
            let min_x = component.iter().map(|point| point.x).min().unwrap_or(0);
            let max_x = component.iter().map(|point| point.x).max().unwrap_or(0);
            let min_y = component.iter().map(|point| point.y).min().unwrap_or(0);
            let max_y = component.iter().map(|point| point.y).max().unwrap_or(0);
            let major_span = (max_x - min_x).abs().max((max_y - min_y).abs());
            let (diameter_squared, thickness_squared) = component_stroke_metrics(&component);
            let cell_count = component.len() as i64;
            (component.len() >= 6
                && nearest_distance <= 100
                && maximum_projection > 0
                && major_span >= 6
                && outward_cells * 3 >= component.len()
                && thickness_squared <= 100
                && cell_count * cell_count <= diameter_squared * 25)
                .then_some((
                    (
                        -nearest_distance,
                        major_span,
                        -thickness_squared,
                        component.len(),
                        -min_y,
                        -min_x,
                    ),
                    component,
                ))
        })
        .max_by_key(|(score, _)| *score)
        .map(|(_, component)| component)
        .unwrap_or_default();
    StaffPath {
        top,
        hand,
        authored_tail: None,
        primary,
        continuation,
    }
}

fn authored_staff_tail(semantic_id: &str, root: Point) -> Option<AuthoredStaffTail> {
    let (offset, corridor_radius_squared) = match semantic_id {
        "front_staff_guard_low" => (Point { x: 32, y: -19 }, 16),
        "walk_front_right_lift" => (Point { x: 4, y: -10 }, 36),
        "front_crouch_reaction_staff_planted" => (Point { x: 22, y: -3 }, 16),
        "fly_front_wings_down" => (Point { x: 13, y: -22 }, 16),
        "fly_southeast_staff_forward" => (Point { x: 7, y: -6 }, 25),
        "front_crouch_landing_staff_plant" => (Point { x: 17, y: -3 }, 16),
        "front_celebrate_wings_staff_up" => (Point { x: -28, y: -25 }, 16),
        "front_point_direct_staff_held" => (Point { x: 20, y: -5 }, 16),
        "front_staff_spin_flourish" => (Point { x: -33, y: -25 }, 9),
        _ => return None,
    };
    Some(AuthoredStaffTail {
        point: add(root, offset),
        corridor_radius_squared,
    })
}

fn apply_staff_anchor_overrides(
    semantic_id: &str,
    mut anchors: Vec<NamedAnchor>,
) -> Vec<NamedAnchor> {
    let Some(root) = anchors
        .iter()
        .find(|anchor| anchor.id == AnchorId::Root)
        .map(|anchor| anchor.point)
    else {
        return anchors;
    };
    let override_points = match semantic_id {
        "fly_southeast_forward_glide" => Some((
            add(root, Point { x: -33, y: -32 }),
            add(root, Point { x: -19, y: -30 }),
        )),
        _ => None,
    };
    if let Some((staff_top, staff_hand)) = override_points {
        for anchor in &mut anchors {
            match anchor.id {
                AnchorId::StaffTop | AnchorId::EffectOrigin => anchor.point = staff_top,
                AnchorId::StaffHand => anchor.point = staff_hand,
                _ => {}
            }
        }
    }
    anchors
}

fn component_stroke_metrics(component: &BTreeSet<Point>) -> (i64, i64) {
    let mut diameter = None;
    for start in component {
        for end in component.range(*start..) {
            let distance = distance_squared(*start, *end);
            if diameter.is_none_or(|(best, _, _)| distance > best) {
                diameter = Some((distance, *start, *end));
            }
        }
    }
    let Some((diameter_squared, start, end)) = diameter else {
        return (0, 0);
    };
    let thickness_squared = component
        .iter()
        .map(|point| line_distance_score(*point, start, end))
        .max()
        .unwrap_or(0);
    (diameter_squared, thickness_squared)
}

fn four_neighbor_components(points: &BTreeSet<Point>) -> Vec<BTreeSet<Point>> {
    neighbor_components(points, false)
}

fn eight_neighbor_components(points: &BTreeSet<Point>) -> Vec<BTreeSet<Point>> {
    neighbor_components(points, true)
}

fn neighbor_components(points: &BTreeSet<Point>, include_diagonals: bool) -> Vec<BTreeSet<Point>> {
    let mut unseen = points.clone();
    let mut components = Vec::new();
    while let Some(start) = unseen.pop_first() {
        let mut component = BTreeSet::from([start]);
        let mut pending = vec![start];
        while let Some(point) = pending.pop() {
            for dy in -1..=1 {
                for dx in -1..=1 {
                    if (dx == 0 && dy == 0) || (!include_diagonals && dx != 0 && dy != 0) {
                        continue;
                    }
                    let neighbor = Point {
                        x: point.x + dx,
                        y: point.y + dy,
                    };
                    if unseen.remove(&neighbor) {
                        component.insert(neighbor);
                        pending.push(neighbor);
                    }
                }
            }
        }
        components.push(component);
    }
    components
}

fn staff_path_contains(path: &StaffPath, point: Point, rgb: [u8; 3]) -> bool {
    let on_primary = path.primary.contains(&point) && !is_bright_skin(rgb);
    let on_continuation = path.continuation.contains(&point) && is_staff_brown(rgb);
    on_primary || on_continuation
}

fn line_distance_score(point: Point, start: Point, end: Point) -> i64 {
    let dx = i64::from(end.x - start.x);
    let dy = i64::from(end.y - start.y);
    let length_squared = dx * dx + dy * dy;
    if length_squared == 0 {
        return distance_squared(point, start);
    }
    let px = i64::from(point.x - start.x);
    let py = i64::from(point.y - start.y);
    let projection = (px * dx + py * dy).clamp(0, length_squared);
    let nearest_x = i64::from(start.x) + (dx * projection + length_squared / 2) / length_squared;
    let nearest_y = i64::from(start.y) + (dy * projection + length_squared / 2) / length_squared;
    let offset_x = i64::from(point.x) - nearest_x;
    let offset_y = i64::from(point.y) - nearest_y;
    offset_x * offset_x + offset_y * offset_y
}

fn is_blue(rgb: [u8; 3]) -> bool {
    rgb[2] > 70 && rgb[2] > rgb[0].saturating_add(12)
}

fn is_yellow(rgb: [u8; 3]) -> bool {
    rgb[0] > 150 && rgb[1] > 120 && rgb[2] < 120
}

fn is_brown(rgb: [u8; 3]) -> bool {
    rgb[0] > 60 && rgb[0] > rgb[2].saturating_add(15) && rgb[1] >= rgb[2]
}

fn is_skin_color(rgb: [u8; 3]) -> bool {
    rgb[0] > 100 && rgb[0] > rgb[1] && rgb[1] > rgb[2].saturating_add(5)
}

fn is_staff_color(rgb: [u8; 3]) -> bool {
    is_staff_brown(rgb)
        || (rgb[0].abs_diff(rgb[1]) < 18 && rgb[1].abs_diff(rgb[2]) < 18 && rgb[0] < 225)
}

fn is_staff_brown(rgb: [u8; 3]) -> bool {
    is_brown(rgb) && u16::from(rgb[1]) * 5 >= u16::from(rgb[0]) * 2 && !is_bright_skin(rgb)
}

fn is_bright_skin(rgb: [u8; 3]) -> bool {
    rgb[0] >= 190 && rgb[1] >= 115 && rgb[1] > rgb[2]
}

fn is_mouth_color(rgb: [u8; 3]) -> bool {
    (rgb[0] > rgb[1].saturating_add(25) && rgb[0] > rgb[2].saturating_add(15))
        || rgb.iter().copied().max().unwrap_or(255) < 85
}

fn is_inner_robe_color(rgb: [u8; 3]) -> bool {
    rgb[0] > 120 && rgb[2] > 50 && rgb[0] > rgb[1].saturating_add(30)
}

fn is_adornment_color(rgb: [u8; 3]) -> bool {
    let maximum = rgb.iter().copied().max().unwrap_or(0);
    let minimum = rgb.iter().copied().min().unwrap_or(0);
    maximum.saturating_sub(minimum) > 45 && !is_skin_color(rgb)
}

fn is_effect_color(rgb: [u8; 3]) -> bool {
    let maximum = rgb.iter().copied().max().unwrap_or(0);
    let minimum = rgb.iter().copied().min().unwrap_or(0);
    maximum > 150 && maximum.saturating_sub(minimum) > 35
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn line_distance_is_integer_and_clamped_to_segment() {
        assert_eq!(
            line_distance_score(
                Point { x: 5, y: 2 },
                Point { x: 0, y: 0 },
                Point { x: 10, y: 0 }
            ),
            4
        );
        assert_eq!(
            line_distance_score(
                Point { x: -2, y: 0 },
                Point { x: 0, y: 0 },
                Point { x: 10, y: 0 }
            ),
            4
        );
    }

    #[test]
    fn engine_contract_has_eighteen_regions_and_twenty_five_anchors() {
        assert_eq!(RegionId::ALL.len(), 18);
        assert_eq!(RegionId::Z_ORDER.len(), 18);
        assert_eq!(AnchorId::REQUIRED.len(), 25);
        assert_eq!(RegionId::ALL.into_iter().collect::<BTreeSet<_>>().len(), 18);
        assert_eq!(
            AnchorId::REQUIRED
                .into_iter()
                .collect::<BTreeSet<_>>()
                .len(),
            25
        );
    }

    #[test]
    fn horizontal_staff_topology_uses_the_authored_axis() {
        let anchors = vec![
            NamedAnchor {
                id: AnchorId::StaffTop,
                point: Point { x: 10, y: 5 },
            },
            NamedAnchor {
                id: AnchorId::StaffHand,
                point: Point { x: 0, y: 5 },
            },
        ];
        let cells = (0..=10)
            .map(|x| SemanticCellPayload {
                x,
                y: 5,
                rgb: [120, 70, 20],
                region: RegionId::Staff,
            })
            .collect::<Vec<_>>();
        let metrics = validate_staff_topology("horizontal", &anchors, &cells).unwrap();
        assert_eq!(metrics.component_count, 1);
        assert_eq!(metrics.off_axis_cells, 0);
        assert_eq!(metrics.unexplained_axis_gaps, 0);
    }

    #[test]
    fn staff_topology_rejects_unexplained_axis_gaps() {
        let anchors = vec![
            NamedAnchor {
                id: AnchorId::StaffTop,
                point: Point { x: 0, y: 5 },
            },
            NamedAnchor {
                id: AnchorId::StaffHand,
                point: Point { x: 20, y: 5 },
            },
        ];
        let cells = [0, 1, 19, 20]
            .into_iter()
            .map(|x| SemanticCellPayload {
                x,
                y: 5,
                rgb: [120, 70, 20],
                region: RegionId::Staff,
            })
            .collect::<Vec<_>>();
        let error = validate_staff_topology("gapped", &anchors, &cells).unwrap_err();
        assert!(error.to_string().contains("unexplained gaps"));
    }

    #[test]
    fn staff_topology_allows_authored_hand_occlusion() {
        let anchors = vec![
            NamedAnchor {
                id: AnchorId::StaffTop,
                point: Point { x: 0, y: 5 },
            },
            NamedAnchor {
                id: AnchorId::StaffHand,
                point: Point { x: 20, y: 5 },
            },
        ];
        let mut cells = (0..=5)
            .chain(15..=20)
            .map(|x| SemanticCellPayload {
                x,
                y: 5,
                rgb: [120, 70, 20],
                region: RegionId::Staff,
            })
            .collect::<Vec<_>>();
        cells.extend((6..15).map(|x| SemanticCellPayload {
            x,
            y: 5,
            rgb: [220, 150, 90],
            region: RegionId::RightArm,
        }));
        let metrics = validate_staff_topology("occluded", &anchors, &cells).unwrap();
        assert_eq!(metrics.off_axis_cells, 0);
        assert_eq!(metrics.unexplained_axis_gaps, 0);
    }

    #[test]
    fn staff_topology_rejects_disconnected_off_axis_outlier() {
        let anchors = vec![
            NamedAnchor {
                id: AnchorId::StaffTop,
                point: Point { x: 0, y: 5 },
            },
            NamedAnchor {
                id: AnchorId::StaffHand,
                point: Point { x: 20, y: 5 },
            },
        ];
        let mut cells = (0..=20)
            .map(|x| SemanticCellPayload {
                x,
                y: 5,
                rgb: [120, 70, 20],
                region: RegionId::Staff,
            })
            .collect::<Vec<_>>();
        cells.push(SemanticCellPayload {
            x: 10,
            y: 15,
            rgb: [120, 70, 20],
            region: RegionId::Staff,
        });
        let error = validate_staff_topology("outlier", &anchors, &cells).unwrap_err();
        assert!(error.to_string().contains("off-axis"));
    }

    #[test]
    fn staff_continuation_prefers_a_curved_stroke_over_a_brown_body_mass() {
        let top = Point { x: 12, y: 2 };
        let hand = Point { x: 12, y: 15 };
        let mut cells = (2..=15)
            .map(|y| CellPayload {
                x: 12,
                y,
                rgb: [120, 70, 20],
            })
            .collect::<Vec<_>>();
        let shaft = (16..=40)
            .flat_map(|y| {
                let center = 12 + (y - 16) / 8;
                (center - 1..=center + 1).map(move |x| CellPayload {
                    x,
                    y,
                    rgb: [120, 70, 20],
                })
            })
            .collect::<Vec<_>>();
        let body_mass = (14..=35)
            .flat_map(|y| {
                (0..=7).map(move |x| CellPayload {
                    x,
                    y,
                    rgb: [120, 70, 20],
                })
            })
            .collect::<Vec<_>>();
        cells.extend(shaft.iter().cloned());
        cells.extend(body_mass.iter().cloned());

        let path = derive_staff_path(top, hand, None, &cells);

        assert!(shaft.iter().all(|cell| path.continuation.contains(&Point {
            x: cell.x,
            y: cell.y,
        })));
        assert!(body_mass.iter().all(|cell| !path.primary.contains(&Point {
            x: cell.x,
            y: cell.y,
        }) && !path.continuation.contains(&Point {
            x: cell.x,
            y: cell.y,
        })));
    }
}
