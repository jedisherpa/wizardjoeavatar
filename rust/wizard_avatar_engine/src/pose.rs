use crate::cell::{Cell, CellCanvas};
use crate::geometry::{bresenham_line, Point};
use crate::pose_asset::load_embedded_pose_library;
use crate::reference_avatar::{reference_pose_ids, render_reference_avatar_pose_local};
use crate::state::{Direction, Locomotion, StaffState, UpperBodyAction, WizardState};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::f32::consts::{PI, TAU};
use std::sync::OnceLock;

pub const POSE_SCHEMA_VERSION: u16 = 2;
pub const CANONICAL_POSE_COLS: usize = 72;
pub const CANONICAL_POSE_ROWS: usize = 96;
pub const CANONICAL_POSE_ROOT: Point = (36, 95);

#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize)]
pub struct PointF {
    pub x: f32,
    pub y: f32,
}

impl PointF {
    #[must_use]
    pub fn round(self) -> Point {
        (self.x.round() as i32, self.y.round() as i32)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RegionId {
    Hat,
    Head,
    Beard,
    Torso,
    Robe,
    InnerRobe,
    LeftArm,
    RightArm,
    LeftLeg,
    RightLeg,
    LeftBoot,
    RightBoot,
    Staff,
    AdornmentLeft,
    AdornmentRight,
    Face,
    Mouth,
    Effect,
}

impl RegionId {
    pub const Z_ORDER: [Self; 18] = [
        Self::AdornmentLeft,
        Self::AdornmentRight,
        Self::Staff,
        Self::Robe,
        Self::InnerRobe,
        Self::LeftLeg,
        Self::RightLeg,
        Self::LeftBoot,
        Self::RightBoot,
        Self::Torso,
        Self::LeftArm,
        Self::RightArm,
        Self::Beard,
        Self::Head,
        Self::Hat,
        Self::Face,
        Self::Mouth,
        Self::Effect,
    ];
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AnchorId {
    Root,
    ContactRoot,
    Pelvis,
    Chest,
    Head,
    LeftShoulder,
    LeftElbow,
    LeftWrist,
    RightShoulder,
    RightElbow,
    RightWrist,
    LeftHip,
    LeftKnee,
    LeftAnkle,
    LeftFoot,
    RightHip,
    RightKnee,
    RightAnkle,
    RightFoot,
    LeftEye,
    RightEye,
    Mouth,
    StaffHand,
    StaffTop,
    EffectOrigin,
}

impl AnchorId {
    pub const REQUIRED: [Self; 25] = [
        Self::Root,
        Self::ContactRoot,
        Self::Pelvis,
        Self::Chest,
        Self::Head,
        Self::LeftShoulder,
        Self::LeftElbow,
        Self::LeftWrist,
        Self::RightShoulder,
        Self::RightElbow,
        Self::RightWrist,
        Self::LeftHip,
        Self::LeftKnee,
        Self::LeftAnkle,
        Self::LeftFoot,
        Self::RightHip,
        Self::RightKnee,
        Self::RightAnkle,
        Self::RightFoot,
        Self::LeftEye,
        Self::RightEye,
        Self::Mouth,
        Self::StaffHand,
        Self::StaffTop,
        Self::EffectOrigin,
    ];
}

#[derive(Clone, Copy, Debug)]
pub struct PoseCell {
    pub x: i16,
    pub y: i16,
    pub cell: Cell,
    pub region: RegionId,
    pub stable_id: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PoseMotionFamily {
    Run,
    Walk,
    Flight,
    Jump,
    Landing,
    GroundAction,
    Kneel,
    Baseline,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PoseContactMode {
    Airborne,
    LeftFoot,
    RightFoot,
    BothFeet,
    BothFeetAndStaff,
    KneelAndStaff,
    HandFootAndStaff,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PoseContactKind {
    Ground,
    Brace,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PoseContactPoint {
    pub anchor: AnchorId,
    pub kind: PoseContactKind,
    pub point: Point,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PoseContactSet {
    pub id: String,
    pub points: Vec<PoseContactPoint>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PoseAttachmentEdge {
    pub parent_region: RegionId,
    pub child_region: RegionId,
    pub parent_anchor: AnchorId,
    pub child_anchor: AnchorId,
}

#[derive(Clone, Debug)]
pub struct PoseMotionMetadata {
    pub candidate_id: Option<String>,
    pub family: PoseMotionFamily,
    pub contact_mode: PoseContactMode,
    pub phase: Option<f32>,
    pub authored_transition_neighbors: Vec<String>,
    pub contact_sets: Vec<PoseContactSet>,
    pub attachment_edges: Vec<PoseAttachmentEdge>,
    pub staff_present: bool,
    pub effect_present: bool,
}

#[derive(Clone, Debug)]
pub struct PoseDefinition {
    pub id: String,
    pub direction: Direction,
    pub root: Point,
    pub anchors: BTreeMap<AnchorId, PointF>,
    pub cells: Vec<PoseCell>,
    pub z_order: Vec<RegionId>,
    pub cols: usize,
    pub rows: usize,
    pub motion: PoseMotionMetadata,
}

#[derive(Clone, Debug)]
pub struct PoseSample {
    pub pose_id: String,
    pub direction: Direction,
    pub root: Point,
    pub anchors: BTreeMap<AnchorId, PointF>,
    pub region_bounds: BTreeMap<RegionId, RegionBounds>,
    pub region_points: BTreeMap<RegionId, Vec<Point>>,
    pub canvas: CellCanvas,
    pub source_cell_count: usize,
    pub source_region_components: BTreeMap<RegionId, usize>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RegionBounds {
    pub min_x: i32,
    pub min_y: i32,
    pub max_x: i32,
    pub max_y: i32,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize)]
pub struct PoseTopologyMetrics {
    pub occupied_cells: usize,
    pub semantic_retained_cells: usize,
    pub connected_components: usize,
    pub unexpected_fragment_components: usize,
    pub horizontal_seam_rows: usize,
    pub horizontal_seam_cells: usize,
    pub vertical_crack_cells: usize,
    pub staff_components: usize,
    pub staff_scanline_gaps: usize,
}

#[must_use]
pub fn analyze_pose_topology(sample: &PoseSample) -> PoseTopologyMetrics {
    let occupied = sample
        .canvas
        .occupied_cells()
        .map(|(x, y, _)| (x, y))
        .collect::<BTreeSet<_>>();
    let core_regions = [
        RegionId::Torso,
        RegionId::Robe,
        RegionId::InnerRobe,
        RegionId::LeftArm,
        RegionId::RightArm,
    ];
    let core = core_regions
        .iter()
        .flat_map(|region| sample.region_points.get(region).into_iter().flatten())
        .copied()
        .collect::<BTreeSet<_>>();
    let min_y = core.iter().map(|(_, y)| *y).min().unwrap_or(0);
    let max_y = core.iter().map(|(_, y)| *y).max().unwrap_or(0);
    let xs = core.iter().map(|(x, _)| *x).collect::<BTreeSet<_>>();
    let mut horizontal_seam_rows = 0;
    let mut horizontal_seam_cells = 0;
    for y in min_y + 1..max_y {
        let gaps = xs
            .iter()
            .filter(|x| {
                !occupied.contains(&(**x, y))
                    && occupied.contains(&(**x, y - 1))
                    && occupied.contains(&(**x, y + 1))
                    && core.contains(&(**x, y - 1))
                    && core.contains(&(**x, y + 1))
            })
            .count();
        if gaps >= 4 {
            horizontal_seam_rows += 1;
            horizontal_seam_cells += gaps;
        }
    }

    let hem_y = sample.root.1 - 10;
    let mut vertical_crack_cells = 0;
    for y in core.iter().map(|(_, y)| *y).collect::<BTreeSet<_>>() {
        if y >= hem_y {
            continue;
        }
        let row = core
            .iter()
            .filter_map(|(x, point_y)| (*point_y == y).then_some(*x))
            .collect::<BTreeSet<_>>();
        if let (Some(min_x), Some(max_x)) = (row.first(), row.last()) {
            vertical_crack_cells += (min_x + 1..*max_x)
                .filter(|x| {
                    !occupied.contains(&(*x, y))
                        && occupied.contains(&(x - 1, y))
                        && occupied.contains(&(x + 1, y))
                        && row.contains(&(x - 1))
                        && row.contains(&(x + 1))
                })
                .count();
        }
    }

    let staff = sample
        .region_points
        .get(&RegionId::Staff)
        .into_iter()
        .flatten()
        .copied()
        .collect::<BTreeSet<_>>();
    let rendered_staff_components = component_count(&staff);
    let source_staff_components = sample
        .source_region_components
        .get(&RegionId::Staff)
        .copied()
        .unwrap_or_default();
    let staff_fragment_excess = rendered_staff_components.saturating_sub(source_staff_components);
    let staff_components = if staff.is_empty() {
        0
    } else {
        1 + staff_fragment_excess
    };
    let staff_scanline_gaps = staff_fragment_excess;

    let unexpected_fragment_components = analyze_region_fragmentation(sample).values().sum();
    let semantic_retained_cells = sample
        .region_points
        .values()
        .map(|points| {
            points
                .iter()
                .copied()
                .filter(|(x, y)| sample.canvas.in_bounds(*x, *y))
                .collect::<BTreeSet<_>>()
                .len()
        })
        .sum();

    PoseTopologyMetrics {
        occupied_cells: occupied.len(),
        semantic_retained_cells,
        connected_components: component_count(&occupied),
        unexpected_fragment_components,
        horizontal_seam_rows,
        horizontal_seam_cells,
        vertical_crack_cells,
        staff_components,
        staff_scanline_gaps,
    }
}

#[must_use]
pub fn analyze_region_fragmentation(sample: &PoseSample) -> BTreeMap<RegionId, usize> {
    sample
        .region_points
        .iter()
        .filter_map(|(region, points)| {
            let excess = component_count(&points.iter().copied().collect()).saturating_sub(
                sample
                    .source_region_components
                    .get(region)
                    .copied()
                    .unwrap_or_default(),
            );
            (excess > 0).then_some((*region, excess))
        })
        .collect()
}

fn component_count(points: &BTreeSet<Point>) -> usize {
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

impl RegionBounds {
    fn include(&mut self, x: i32, y: i32) {
        self.min_x = self.min_x.min(x);
        self.min_y = self.min_y.min(y);
        self.max_x = self.max_x.max(x);
        self.max_y = self.max_y.max(y);
    }

    #[must_use]
    pub const fn width(self) -> i32 {
        self.max_x - self.min_x + 1
    }

    #[must_use]
    pub const fn height(self) -> i32 {
        self.max_y - self.min_y + 1
    }
}

#[derive(Clone, Debug)]
pub struct PoseLibrary {
    pub schema_version: u16,
    by_direction: BTreeMap<Direction, String>,
    by_id: BTreeMap<String, PoseDefinition>,
    aliases: BTreeMap<String, String>,
}

static POSE_LIBRARY: OnceLock<Result<PoseLibrary, String>> = OnceLock::new();

impl PoseLibrary {
    pub fn reference() -> Result<&'static Self, String> {
        POSE_LIBRARY
            .get_or_init(Self::load_reference)
            .as_ref()
            .map_err(Clone::clone)
    }

    fn load_reference() -> Result<Self, String> {
        let ids = reference_pose_ids().into_iter().collect::<BTreeSet<_>>();
        let directional = [
            (Direction::South, "front_idle"),
            (Direction::SouthWest, "walk_front_left"),
            (Direction::West, "profile_left"),
            (Direction::NorthWest, "back_left"),
            (Direction::North, "back_idle"),
            (Direction::NorthEast, "back_right"),
            (Direction::East, "profile_right"),
            (Direction::SouthEast, "walk_front_right"),
        ];
        let mut by_direction = BTreeMap::new();
        let mut by_id = BTreeMap::new();
        for (direction, id) in directional {
            if !ids.contains(id) {
                return Err(format!("pose library is missing {id}"));
            }
            let pose = render_reference_avatar_pose_local(id)
                .ok_or_else(|| format!("failed to load pose {id}"))?;
            by_id.insert(id.to_string(), build_definition(direction, pose)?);
            by_direction.insert(direction, id.to_string());
        }
        for id in ["explaining", "magic_cast"] {
            if !ids.contains(id) {
                return Err(format!("pose library is missing {id}"));
            }
            let pose = render_reference_avatar_pose_local(id)
                .ok_or_else(|| format!("failed to load pose {id}"))?;
            by_id.insert(id.to_string(), build_definition(Direction::South, pose)?);
        }
        let imported = load_embedded_pose_library()?;
        for definition in imported.definitions {
            if by_id.insert(definition.id.clone(), definition).is_some() {
                return Err("imported pose collides with a baseline pose ID".to_string());
            }
        }
        for definition in by_id.values_mut() {
            normalize_pose_canvas(definition)?;
        }
        let library = Self {
            schema_version: POSE_SCHEMA_VERSION,
            by_direction,
            by_id,
            aliases: imported.aliases,
        };
        library.validate()?;
        Ok(library)
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.schema_version != POSE_SCHEMA_VERSION {
            return Err(format!(
                "unsupported pose schema version {}",
                self.schema_version
            ));
        }
        for direction in Direction::ALL {
            let pose_id = self
                .by_direction
                .get(&direction)
                .ok_or_else(|| format!("missing pose for {direction:?}"))?;
            if !self.by_id.contains_key(pose_id) {
                return Err(format!(
                    "direction {direction:?} references missing pose {pose_id}"
                ));
            }
        }
        for pose in self.by_id.values() {
            if pose.cols != CANONICAL_POSE_COLS
                || pose.rows != CANONICAL_POSE_ROWS
                || pose.root != CANONICAL_POSE_ROOT
            {
                return Err(format!(
                    "{} is not normalized to {}x{} at root {:?}",
                    pose.id, CANONICAL_POSE_COLS, CANONICAL_POSE_ROWS, CANONICAL_POSE_ROOT
                ));
            }
            for anchor in AnchorId::REQUIRED {
                if !pose.anchors.contains_key(&anchor) {
                    return Err(format!("{} missing {anchor:?}", pose.id));
                }
            }
            if pose.anchors.values().any(|point| {
                !point.x.is_finite()
                    || !point.y.is_finite()
                    || !(0.0..CANONICAL_POSE_COLS as f32).contains(&point.x)
                    || !(0.0..CANONICAL_POSE_ROWS as f32).contains(&point.y)
            }) {
                return Err(format!(
                    "{} has anchors outside the canonical canvas",
                    pose.id
                ));
            }
            if pose.motion.contact_sets.iter().any(|set| {
                set.points.iter().any(|point| {
                    !(0..CANONICAL_POSE_COLS as i32).contains(&point.point.0)
                        || !(0..CANONICAL_POSE_ROWS as i32).contains(&point.point.1)
                })
            }) {
                return Err(format!(
                    "{} has contacts outside the canonical canvas",
                    pose.id
                ));
            }
            let ids = pose
                .cells
                .iter()
                .map(|cell| cell.stable_id)
                .collect::<BTreeSet<_>>();
            if ids.len() != pose.cells.len() {
                return Err(format!("{} has duplicate stable IDs", pose.id));
            }
            if pose.cells.is_empty() {
                return Err(format!("{} has invalid semantic cells", pose.id));
            }
            if pose.cells.iter().any(|cell| {
                cell.x < 0
                    || usize::try_from(cell.x).map_or(true, |x| x >= CANONICAL_POSE_COLS)
                    || cell.y < 0
                    || usize::try_from(cell.y).map_or(true, |y| y >= CANONICAL_POSE_ROWS)
            }) {
                return Err(format!(
                    "{} has cells outside the canonical canvas",
                    pose.id
                ));
            }
            let effect_cells = pose
                .cells
                .iter()
                .any(|cell| cell.region == RegionId::Effect);
            if effect_cells != pose.motion.effect_present {
                return Err(format!("{} has inconsistent effect presence", pose.id));
            }
            if pose.motion.staff_present
                != pose.cells.iter().any(|cell| cell.region == RegionId::Staff)
            {
                return Err(format!("{} has inconsistent staff presence", pose.id));
            }
        }
        for (alias, target) in &self.aliases {
            if alias == target || !self.by_id.contains_key(target) || self.by_id.contains_key(alias)
            {
                return Err(format!("invalid pose alias {alias} -> {target}"));
            }
        }
        if self.by_id.len() != 89 || self.aliases.len() != 1 {
            return Err(format!(
                "runtime pose library must contain 89 geometries and 1 alias, got {} and {}",
                self.by_id.len(),
                self.aliases.len()
            ));
        }
        let resolvable = self
            .by_id
            .keys()
            .chain(self.aliases.keys())
            .map(String::as_str)
            .collect::<BTreeSet<_>>();
        for pose in self.by_id.values() {
            if pose
                .motion
                .authored_transition_neighbors
                .iter()
                .any(|neighbor| !resolvable.contains(neighbor.as_str()))
            {
                return Err(format!("{} has an unresolved transition neighbor", pose.id));
            }
        }
        Ok(())
    }

    #[must_use]
    pub fn for_direction(&self, direction: Direction) -> Option<&PoseDefinition> {
        let id = self.by_direction.get(&direction)?;
        self.by_id.get(id)
    }

    #[must_use]
    pub fn for_id(&self, pose_id: &str) -> Option<&PoseDefinition> {
        let resolved = self
            .aliases
            .get(pose_id)
            .map(String::as_str)
            .unwrap_or(pose_id);
        self.by_id.get(resolved)
    }

    pub fn pose_ids(&self) -> impl Iterator<Item = &str> {
        self.by_id.keys().map(String::as_str)
    }

    #[must_use]
    pub fn alias_count(&self) -> usize {
        self.aliases.len()
    }

    pub fn sample(&self, state: &WizardState) -> Result<PoseSample, String> {
        let explicit_target = state.pose_id.as_deref();
        let target = match explicit_target {
            Some(id) => self
                .for_id(id)
                .ok_or_else(|| format!("missing pose {id}"))?,
            None => self
                .for_direction(state.facing)
                .ok_or_else(|| format!("missing pose for {:?}", state.facing))?,
        };
        let explicit_source = explicit_target
            .and(state.previous_pose_id.as_deref())
            .and_then(|id| self.for_id(id))
            .filter(|pose| pose.id != target.id && state.pose_blend < 1.0);
        let source = if explicit_target.is_some() && !state.pose_handoff {
            explicit_source
        } else if explicit_target.is_none()
            && state.previous_facing != state.facing
            && !state.facing_pose_handoff
        {
            self.for_direction(state.previous_facing)
        } else {
            None
        };

        // Direction poses have intentionally different topology. A transition therefore
        // presents one complete pose at a time; matching sorted cells across views tears
        // semantic regions into unrelated fragments. Gait and channel offsets remain
        // continuous, while the controller changes the coherent view once at a
        // contact-aware handoff.
        let presented = source.unwrap_or(target);
        let mut rig = semantic_gait_rig(state, presented.direction, presented);
        if let Some(source) = explicit_source {
            apply_pose_transition_rig(&mut rig, state, source, target, presented);
        }
        let mut anchors = presented.anchors.clone();
        apply_anchor_offsets(&mut anchors, &rig);
        let mut cells = presented.cells.clone();
        cells.sort_by_key(|cell| {
            (
                presented
                    .z_order
                    .iter()
                    .position(|region| *region == cell.region)
                    .unwrap_or(usize::MAX),
                cell.stable_id,
            )
        });
        let mut canvas = CellCanvas::new(presented.cols, presented.rows);
        let mut region_bounds = BTreeMap::<RegionId, RegionBounds>::new();
        let mut region_points = BTreeMap::<RegionId, Vec<Point>>::new();
        let transformed_cells = cells
            .iter()
            .map(|cell| {
                let transformed = transform_semantic_cell(
                    PointF {
                        x: f32::from(cell.x),
                        y: f32::from(cell.y),
                    },
                    cell.region,
                    presented,
                    &rig,
                );
                (
                    (i32::from(cell.x), i32::from(cell.y)),
                    (*cell, transformed.round()),
                )
            })
            .collect::<BTreeMap<_, _>>();
        let mut region_displacements = BTreeMap::<RegionId, BTreeSet<Point>>::new();
        for (source, (cell, destination)) in &transformed_cells {
            region_displacements
                .entry(cell.region)
                .or_default()
                .insert((destination.0 - source.0, destination.1 - source.1));
        }
        let mut actual_destinations = BTreeMap::<Point, Point>::new();
        for cell in &cells {
            let source = (i32::from(cell.x), i32::from(cell.y));
            let (_, intended_destination) = transformed_cells[&source];
            let destination = intended_destination;
            actual_destinations.insert(source, destination);
            record_raster_point(
                &mut canvas,
                &mut region_bounds,
                &mut region_points,
                cell.region,
                destination,
                cell.cell,
            );
        }
        for cell in &cells {
            let source = (i32::from(cell.x), i32::from(cell.y));
            let Some(&destination) = actual_destinations.get(&source) else {
                continue;
            };
            for neighbor_source in [
                (source.0 + 1, source.1),
                (source.0, source.1 + 1),
                (source.0 + 1, source.1 + 1),
                (source.0 - 1, source.1 + 1),
            ] {
                let Some((neighbor, neighbor_destination)) =
                    transformed_cells.get(&neighbor_source).copied()
                else {
                    continue;
                };
                let neighbor_destination = actual_destinations
                    .get(&neighbor_source)
                    .copied()
                    .unwrap_or(neighbor_destination);
                if !approved_attachment(cell.region, neighbor.region) {
                    continue;
                }
                let separation = (destination.0 - neighbor_destination.0)
                    .abs()
                    .max((destination.1 - neighbor_destination.1).abs());
                if !(2..=14).contains(&separation) {
                    continue;
                }
                let bridge = bresenham_line(
                    destination.0,
                    destination.1,
                    neighbor_destination.0,
                    neighbor_destination.1,
                );
                let bridge_len = bridge.len();
                for (index, point) in bridge.into_iter().enumerate().skip(1).take(bridge_len - 2) {
                    let (region, raster_cell) = if index * 2 < bridge_len {
                        (cell.region, cell.cell)
                    } else {
                        (neighbor.region, neighbor.cell)
                    };
                    record_raster_point(
                        &mut canvas,
                        &mut region_bounds,
                        &mut region_points,
                        region,
                        point,
                        raster_cell,
                    );
                }
            }
        }
        repair_one_cell_attachment_gaps(
            &mut canvas,
            &mut region_bounds,
            &mut region_points,
            presented,
            &region_displacements,
        );
        let source_region_components = cells.iter().fold(
            BTreeMap::<RegionId, BTreeSet<Point>>::new(),
            |mut regions, cell| {
                regions
                    .entry(cell.region)
                    .or_default()
                    .insert((i32::from(cell.x), i32::from(cell.y)));
                regions
            },
        );
        Ok(PoseSample {
            pose_id: presented.id.clone(),
            direction: presented.direction,
            root: presented.root,
            anchors,
            region_bounds,
            region_points,
            canvas,
            source_cell_count: presented.cells.len(),
            source_region_components: source_region_components
                .into_iter()
                .map(|(region, points)| (region, component_count(&points)))
                .collect(),
        })
    }
}

fn normalize_pose_canvas(pose: &mut PoseDefinition) -> Result<(), String> {
    if pose.cols > CANONICAL_POSE_COLS || pose.rows > CANONICAL_POSE_ROWS {
        return Err(format!(
            "{} canvas {}x{} exceeds canonical {}x{}",
            pose.id, pose.cols, pose.rows, CANONICAL_POSE_COLS, CANONICAL_POSE_ROWS
        ));
    }

    let dx = CANONICAL_POSE_ROOT.0 - pose.root.0;
    let dy = CANONICAL_POSE_ROOT.1 - pose.root.1;
    let translated_cells = pose
        .cells
        .iter()
        .map(|cell| (i32::from(cell.x) + dx, i32::from(cell.y) + dy))
        .collect::<Vec<_>>();
    if translated_cells.iter().any(|(x, y)| {
        *x < 0
            || usize::try_from(*x).map_or(true, |x| x >= CANONICAL_POSE_COLS)
            || *y < 0
            || usize::try_from(*y).map_or(true, |y| y >= CANONICAL_POSE_ROWS)
    }) {
        return Err(format!(
            "{} cannot be edge-padded to the canonical canvas without cropping",
            pose.id
        ));
    }

    for (cell, (x, y)) in pose.cells.iter_mut().zip(translated_cells) {
        cell.x = i16::try_from(x).map_err(|_| format!("{} cell x overflow", pose.id))?;
        cell.y = i16::try_from(y).map_err(|_| format!("{} cell y overflow", pose.id))?;
    }
    for point in pose.anchors.values_mut() {
        point.x += dx as f32;
        point.y += dy as f32;
    }
    for set in &mut pose.motion.contact_sets {
        for point in &mut set.points {
            point.point.0 += dx;
            point.point.1 += dy;
        }
    }
    pose.root = CANONICAL_POSE_ROOT;
    pose.cols = CANONICAL_POSE_COLS;
    pose.rows = CANONICAL_POSE_ROWS;
    Ok(())
}

fn repair_one_cell_attachment_gaps(
    canvas: &mut CellCanvas,
    region_bounds: &mut BTreeMap<RegionId, RegionBounds>,
    region_points: &mut BTreeMap<RegionId, Vec<Point>>,
    pose: &PoseDefinition,
    region_displacements: &BTreeMap<RegionId, BTreeSet<Point>>,
) {
    for _ in 0..6 {
        if repair_one_cell_attachment_gap_pass(
            canvas,
            region_bounds,
            region_points,
            pose,
            region_displacements,
        ) == 0
        {
            break;
        }
    }
    repair_staff_connectivity(canvas, region_bounds, region_points);
    repair_core_raster_gaps(canvas, region_bounds, region_points, pose.root.1 - 10);
}

fn repair_core_raster_gaps(
    canvas: &mut CellCanvas,
    region_bounds: &mut BTreeMap<RegionId, RegionBounds>,
    region_points: &mut BTreeMap<RegionId, Vec<Point>>,
    hem_y: i32,
) {
    let core_regions = [
        RegionId::Torso,
        RegionId::Robe,
        RegionId::InnerRobe,
        RegionId::LeftArm,
        RegionId::RightArm,
    ];
    for _ in 0..8 {
        let mut point_regions = BTreeMap::<Point, RegionId>::new();
        for region in core_regions {
            for point in region_points.get(&region).into_iter().flatten() {
                point_regions.insert(*point, region);
            }
        }
        let core = point_regions.keys().copied().collect::<BTreeSet<_>>();
        let occupied = canvas
            .occupied_cells()
            .map(|(x, y, _)| (x, y))
            .collect::<BTreeSet<_>>();
        let mut repairs = BTreeMap::<Point, (RegionId, Cell)>::new();

        for &(x, y) in &core {
            let right_gap = (x + 1, y);
            if y < hem_y && !occupied.contains(&right_gap) && core.contains(&(x + 2, y)) {
                if let Some(cell) = canvas.get(x, y).or_else(|| canvas.get(x + 2, y)) {
                    let region = point_regions
                        .get(&(x, y))
                        .or_else(|| point_regions.get(&(x + 2, y)))
                        .copied()
                        .unwrap_or(RegionId::Torso);
                    repairs.insert(right_gap, (region, cell));
                }
            }

            let below_gap = (x, y + 1);
            if !occupied.contains(&below_gap) && core.contains(&(x, y + 2)) {
                if let Some(cell) = canvas.get(x, y).or_else(|| canvas.get(x, y + 2)) {
                    let region = point_regions
                        .get(&(x, y))
                        .or_else(|| point_regions.get(&(x, y + 2)))
                        .copied()
                        .unwrap_or(RegionId::Torso);
                    repairs.insert(below_gap, (region, cell));
                }
            }
        }

        if repairs.is_empty() {
            break;
        }
        for (point, (region, cell)) in repairs {
            if canvas.get(point.0, point.1).is_none() {
                record_raster_point(canvas, region_bounds, region_points, region, point, cell);
            }
        }
    }
}

fn repair_one_cell_attachment_gap_pass(
    canvas: &mut CellCanvas,
    region_bounds: &mut BTreeMap<RegionId, RegionBounds>,
    region_points: &mut BTreeMap<RegionId, Vec<Point>>,
    pose: &PoseDefinition,
    region_displacements: &BTreeMap<RegionId, BTreeSet<Point>>,
) -> usize {
    let mut visible_regions = BTreeMap::<Point, RegionId>::new();
    for region in &pose.z_order {
        if let Some(points) = region_points.get(region) {
            for point in points {
                visible_regions.insert(*point, *region);
            }
        }
    }
    let occupied = canvas
        .occupied_cells()
        .map(|(x, y, _)| (x, y))
        .collect::<BTreeSet<_>>();
    let core_points = [
        RegionId::Torso,
        RegionId::Robe,
        RegionId::InnerRobe,
        RegionId::LeftArm,
        RegionId::RightArm,
    ]
    .iter()
    .flat_map(|region| region_points.get(region).into_iter().flatten())
    .copied()
    .collect::<BTreeSet<_>>();
    let Some(min_x) = occupied.iter().map(|(x, _)| *x).min() else {
        return 0;
    };
    let max_x = occupied.iter().map(|(x, _)| *x).max().unwrap_or(min_x);
    let min_y = occupied.iter().map(|(_, y)| *y).min().unwrap_or(0);
    let max_y = occupied.iter().map(|(_, y)| *y).max().unwrap_or(min_y);
    let hem_y = pose.root.1 - 10;
    let mut repairs = Vec::<(Point, RegionId, Cell)>::new();
    let collective_seam_rows = (min_y + 1..max_y)
        .filter(|y| {
            (min_x + 1..max_x)
                .filter(|x| {
                    !occupied.contains(&(*x, *y))
                        && occupied.contains(&(*x, *y - 1))
                        && occupied.contains(&(*x, *y + 1))
                })
                .count()
                >= 4
        })
        .collect::<BTreeSet<_>>();

    for y in min_y + 1..max_y {
        for x in min_x + 1..max_x {
            if occupied.contains(&(x, y)) {
                continue;
            }
            let above = (x, y - 1);
            let below = (x, y + 1);
            if let (Some(above_region), Some(below_region), Some(cell)) = (
                visible_regions.get(&above),
                visible_regions.get(&below),
                canvas.get(above.0, above.1),
            ) {
                if collective_seam_rows.contains(&y)
                    || approved_attachment(*above_region, *below_region)
                        && attachment_shifted(*above_region, *below_region, region_displacements)
                {
                    repairs.push(((x, y), *above_region, cell));
                    continue;
                }
            }

            let left = (x - 1, y);
            let right = (x + 1, y);
            if let (Some(left_region), Some(right_region), Some(cell)) = (
                visible_regions.get(&left),
                visible_regions.get(&right),
                canvas.get(left.0, left.1),
            ) {
                let lower_body_gap = y >= hem_y
                    && is_lower_body_or_robe(*left_region)
                    && is_lower_body_or_robe(*right_region);
                let core_crack =
                    y < hem_y && core_points.contains(&left) && core_points.contains(&right);
                if !lower_body_gap
                    && (core_crack
                        || approved_attachment(*left_region, *right_region)
                            && attachment_shifted(
                                *left_region,
                                *right_region,
                                region_displacements,
                            ))
                {
                    repairs.push(((x, y), *left_region, cell));
                }
            }
        }
    }

    let mut applied = 0;
    for (point, region, cell) in repairs {
        if canvas.get(point.0, point.1).is_none() {
            record_raster_point(canvas, region_bounds, region_points, region, point, cell);
            applied += 1;
        }
    }
    applied
}

fn repair_staff_connectivity(
    canvas: &mut CellCanvas,
    region_bounds: &mut BTreeMap<RegionId, RegionBounds>,
    region_points: &mut BTreeMap<RegionId, Vec<Point>>,
) {
    for _ in 0..32 {
        let staff = region_points
            .get(&RegionId::Staff)
            .into_iter()
            .flatten()
            .copied()
            .collect::<BTreeSet<_>>();
        let components = connected_components(&staff);
        if components.len() <= 1 {
            return;
        }
        let mut closest: Option<(i32, Point, Point)> = None;
        for first_index in 0..components.len() {
            for second_index in first_index + 1..components.len() {
                for &first in &components[first_index] {
                    for &second in &components[second_index] {
                        let distance = (first.0 - second.0).abs().max((first.1 - second.1).abs());
                        if closest.is_none_or(|current| distance < current.0) {
                            closest = Some((distance, first, second));
                        }
                    }
                }
            }
        }
        let Some((distance, first, second)) = closest else {
            return;
        };
        // Authored staffs can contain several short gaps around a hook or hand,
        // but a long join is more likely to be a misclassified body fragment.
        if distance > 16 {
            return;
        }
        let Some(cell) = canvas.get(first.0, first.1) else {
            return;
        };
        for point in bresenham_line(first.0, first.1, second.0, second.1) {
            if canvas.get(point.0, point.1).is_none() {
                record_raster_point(
                    canvas,
                    region_bounds,
                    region_points,
                    RegionId::Staff,
                    point,
                    cell,
                );
            } else {
                region_points
                    .entry(RegionId::Staff)
                    .or_default()
                    .push(point);
                region_bounds
                    .entry(RegionId::Staff)
                    .and_modify(|bounds| bounds.include(point.0, point.1));
            }
        }
    }
}

fn connected_components(points: &BTreeSet<Point>) -> Vec<BTreeSet<Point>> {
    let mut remaining = points.clone();
    let mut components = Vec::new();
    while let Some(start) = remaining.pop_first() {
        let mut component = BTreeSet::from([start]);
        let mut queue = VecDeque::from([start]);
        while let Some((x, y)) = queue.pop_front() {
            for dy in -1..=1 {
                for dx in -1..=1 {
                    let neighbor = (x + dx, y + dy);
                    if (dx != 0 || dy != 0) && remaining.remove(&neighbor) {
                        component.insert(neighbor);
                        queue.push_back(neighbor);
                    }
                }
            }
        }
        components.push(component);
    }
    components
}

fn attachment_shifted(
    a: RegionId,
    b: RegionId,
    region_displacements: &BTreeMap<RegionId, BTreeSet<Point>>,
) -> bool {
    let a_displacements = region_displacements.get(&a);
    let b_displacements = region_displacements.get(&b);
    if a == b {
        return matches!(a, RegionId::Torso | RegionId::Robe | RegionId::InnerRobe)
            || a == RegionId::Staff
                && a_displacements.is_some_and(|displacements| displacements.len() > 1);
    }
    a_displacements != b_displacements
}

fn is_lower_body_or_robe(region: RegionId) -> bool {
    matches!(
        region,
        RegionId::Robe
            | RegionId::InnerRobe
            | RegionId::LeftLeg
            | RegionId::RightLeg
            | RegionId::LeftBoot
            | RegionId::RightBoot
    )
}

fn record_raster_point(
    canvas: &mut CellCanvas,
    region_bounds: &mut BTreeMap<RegionId, RegionBounds>,
    region_points: &mut BTreeMap<RegionId, Vec<Point>>,
    region: RegionId,
    (x, y): Point,
    cell: Cell,
) {
    region_bounds
        .entry(region)
        .and_modify(|bounds| bounds.include(x, y))
        .or_insert(RegionBounds {
            min_x: x,
            min_y: y,
            max_x: x,
            max_y: y,
        });
    region_points.entry(region).or_default().push((x, y));
    canvas.set(x, y, cell.glyph, cell.rgb);
}

fn approved_attachment(a: RegionId, b: RegionId) -> bool {
    if a == b {
        return true;
    }
    let opposed_lower_limbs = matches!(a, RegionId::LeftLeg | RegionId::LeftBoot)
        && matches!(b, RegionId::RightLeg | RegionId::RightBoot)
        || matches!(b, RegionId::LeftLeg | RegionId::LeftBoot)
            && matches!(a, RegionId::RightLeg | RegionId::RightBoot);
    if opposed_lower_limbs {
        return false;
    }
    let pair = |left: RegionId, right: &[RegionId]| {
        a == left && right.contains(&b) || b == left && right.contains(&a)
    };
    pair(
        RegionId::Torso,
        &[
            RegionId::LeftArm,
            RegionId::RightArm,
            RegionId::Robe,
            RegionId::InnerRobe,
            RegionId::AdornmentLeft,
            RegionId::AdornmentRight,
            RegionId::Beard,
        ],
    ) || pair(
        RegionId::Robe,
        &[
            RegionId::InnerRobe,
            RegionId::LeftLeg,
            RegionId::RightLeg,
            RegionId::LeftArm,
            RegionId::RightArm,
            RegionId::AdornmentLeft,
            RegionId::AdornmentRight,
        ],
    ) || pair(
        RegionId::InnerRobe,
        &[RegionId::LeftLeg, RegionId::RightLeg],
    ) || pair(
        RegionId::Head,
        &[
            RegionId::Hat,
            RegionId::Beard,
            RegionId::Face,
            RegionId::Mouth,
        ],
    ) || pair(
        RegionId::Beard,
        &[
            RegionId::Face,
            RegionId::Mouth,
            RegionId::LeftArm,
            RegionId::RightArm,
        ],
    ) || pair(
        RegionId::AdornmentLeft,
        &[RegionId::LeftArm, RegionId::Robe],
    ) || pair(
        RegionId::AdornmentRight,
        &[RegionId::RightArm, RegionId::Robe],
    ) || pair(
        RegionId::Staff,
        &[RegionId::LeftArm, RegionId::RightArm, RegionId::Torso],
    ) || pair(RegionId::LeftLeg, &[RegionId::LeftBoot, RegionId::Robe])
        || pair(RegionId::RightLeg, &[RegionId::RightBoot, RegionId::Robe])
}

fn apply_anchor_offsets(anchors: &mut BTreeMap<AnchorId, PointF>, rig: &SemanticGaitRig) {
    for (anchor, region) in anchor_regions() {
        if let (Some(point), Some(offset)) = (anchors.get_mut(&anchor), rig.offsets.get(&region)) {
            point.x += offset.x;
            point.y += offset.y;
        }
    }
    offset_anchor(anchors, AnchorId::StaffHand, rig.staff_hand);
    offset_anchor(anchors, AnchorId::StaffTop, rig.staff_top);
    offset_anchor(anchors, AnchorId::EffectOrigin, rig.staff_top);
}

fn offset_anchor(anchors: &mut BTreeMap<AnchorId, PointF>, anchor: AnchorId, offset: PointF) {
    if let Some(point) = anchors.get_mut(&anchor) {
        point.x += offset.x;
        point.y += offset.y;
    }
}

fn smooth_step(value: f32) -> f32 {
    let value = value.clamp(0.0, 1.0);
    value * value * (3.0 - 2.0 * value)
}

pub fn sample_pose(state: &WizardState) -> Result<PoseSample, String> {
    PoseLibrary::reference()?.sample(state)
}

#[must_use]
pub fn transition_ticks_for(source_id: &str, target_id: &str, minimum: u16) -> u16 {
    let Ok(library) = PoseLibrary::reference() else {
        return minimum.max(1);
    };
    let (Some(source), Some(target)) = (library.for_id(source_id), library.for_id(target_id))
    else {
        return minimum.max(1);
    };
    if source.id == target.id {
        return minimum.max(1);
    }

    // At 24 Hz a presented pair can span three 60 Hz simulation ticks. The
    // derivative of smoothstep peaks at 1.5, so this bound chooses enough ticks
    // for the largest authored anchor displacement without relying on blur or
    // skipped frames to hide a jump.
    const PRESENTED_TICK_GAP: f32 = 3.0;
    const SMOOTHSTEP_MAX_SLOPE: f32 = 1.5;
    let mut required = f32::from(minimum.max(1));
    for anchor in [
        AnchorId::Pelvis,
        AnchorId::Chest,
        AnchorId::Head,
        AnchorId::LeftEye,
        AnchorId::RightEye,
        AnchorId::Mouth,
        AnchorId::LeftShoulder,
        AnchorId::LeftElbow,
        AnchorId::LeftWrist,
        AnchorId::RightShoulder,
        AnchorId::RightElbow,
        AnchorId::RightWrist,
        AnchorId::LeftHip,
        AnchorId::LeftKnee,
        AnchorId::LeftAnkle,
        AnchorId::LeftFoot,
        AnchorId::RightHip,
        AnchorId::RightKnee,
        AnchorId::RightAnkle,
        AnchorId::RightFoot,
        AnchorId::StaffHand,
        AnchorId::StaffTop,
        AnchorId::EffectOrigin,
    ] {
        let source_point = source.anchors[&anchor];
        let target_point = target.anchors[&anchor];
        let distance = ((target_point.x - source_point.x).powi(2)
            + (target_point.y - source_point.y).powi(2))
        .sqrt();
        let maximum_step = match anchor {
            AnchorId::Head | AnchorId::LeftEye | AnchorId::RightEye | AnchorId::Mouth => 4.0,
            AnchorId::LeftHip
            | AnchorId::LeftKnee
            | AnchorId::LeftAnkle
            | AnchorId::LeftFoot
            | AnchorId::RightHip
            | AnchorId::RightKnee
            | AnchorId::RightAnkle
            | AnchorId::RightFoot => 8.0,
            _ => 6.0,
        };
        required =
            required.max(distance * SMOOTHSTEP_MAX_SLOPE * PRESENTED_TICK_GAP / maximum_step);
    }
    required.ceil().min(f32::from(u16::MAX)) as u16
}

fn build_definition(
    direction: Direction,
    pose: crate::reference_avatar::ReferencePose,
) -> Result<PoseDefinition, String> {
    let anchors = enrich_anchors(&pose.metadata.anchors, pose.root_anchor)?;
    let motion = baseline_motion_metadata(&pose.pose_id, &anchors);
    let mut cells = pose
        .canvas
        .occupied_cells()
        .map(|(x, y, cell)| PoseCell {
            x: x as i16,
            y: y as i16,
            cell,
            region: classify_region(
                PointF {
                    x: x as f32,
                    y: y as f32,
                },
                &anchors,
            ),
            stable_id: 0,
        })
        .collect::<Vec<_>>();
    cells.sort_by_key(|cell| (cell.region, cell.y, cell.x));
    for (stable_id, cell) in cells.iter_mut().enumerate() {
        cell.stable_id = stable_id as u32;
    }
    Ok(PoseDefinition {
        id: pose.pose_id,
        direction,
        root: pose.root_anchor,
        anchors,
        cells,
        z_order: RegionId::Z_ORDER.to_vec(),
        cols: pose.canvas.width,
        rows: pose.canvas.height,
        motion,
    })
}

fn baseline_motion_metadata(
    pose_id: &str,
    anchors: &BTreeMap<AnchorId, PointF>,
) -> PoseMotionMetadata {
    let (contact_mode, contact_anchors) = match pose_id {
        "walk_front_left" | "back_left" => (PoseContactMode::LeftFoot, vec![AnchorId::LeftFoot]),
        "walk_front_right" | "back_right" => {
            (PoseContactMode::RightFoot, vec![AnchorId::RightFoot])
        }
        _ => (
            PoseContactMode::BothFeet,
            vec![AnchorId::LeftFoot, AnchorId::RightFoot],
        ),
    };
    let points = contact_anchors
        .into_iter()
        .filter_map(|anchor| {
            anchors.get(&anchor).map(|point| PoseContactPoint {
                anchor,
                kind: PoseContactKind::Ground,
                point: point.round(),
            })
        })
        .collect();
    PoseMotionMetadata {
        candidate_id: None,
        family: PoseMotionFamily::Baseline,
        contact_mode,
        phase: match pose_id {
            "walk_front_left" | "back_left" => Some(0.0),
            "walk_front_right" | "back_right" => Some(0.5),
            _ => None,
        },
        authored_transition_neighbors: vec!["front_idle".to_string()],
        contact_sets: vec![PoseContactSet {
            id: "primary".to_string(),
            points,
        }],
        attachment_edges: Vec::new(),
        staff_present: true,
        effect_present: false,
    }
}

fn enrich_anchors(
    source: &BTreeMap<String, Point>,
    root_point: Point,
) -> Result<BTreeMap<AnchorId, PointF>, String> {
    let point = |name: &str| {
        source
            .get(name)
            .copied()
            .map(|(x, y)| PointF {
                x: x as f32,
                y: y as f32,
            })
            .ok_or_else(|| format!("pose missing source anchor {name}"))
    };
    let root = PointF {
        x: root_point.0 as f32,
        y: root_point.1 as f32,
    };
    let left_eye = point("left_eye")?;
    let right_eye = point("right_eye")?;
    let mouth = point("mouth")?;
    let left_foot = point("left_foot")?;
    let right_foot = point("right_foot")?;
    let left_wrist = point("left_hand")?;
    let right_wrist = point("right_hand")?;
    let staff_hand = point("staff_hand")?;
    let staff_top = point("staff_tip")?;
    let pelvis = PointF {
        x: root.x,
        y: root.y - 24.0,
    };
    let chest = PointF {
        x: root.x,
        y: root.y - 48.0,
    };
    let head = PointF {
        x: (left_eye.x + right_eye.x) * 0.5,
        y: (left_eye.y + right_eye.y) * 0.5 - 5.0,
    };
    let left_shoulder = PointF {
        x: chest.x - 11.0,
        y: chest.y,
    };
    let right_shoulder = PointF {
        x: chest.x + 11.0,
        y: chest.y,
    };
    let left_hip = PointF {
        x: pelvis.x - 6.0,
        y: pelvis.y,
    };
    let right_hip = PointF {
        x: pelvis.x + 6.0,
        y: pelvis.y,
    };
    let midpoint = |a: PointF, b: PointF| PointF {
        x: (a.x + b.x) * 0.5,
        y: (a.y + b.y) * 0.5,
    };
    Ok(BTreeMap::from([
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
        (AnchorId::LeftKnee, midpoint(left_hip, left_foot)),
        (AnchorId::LeftAnkle, left_foot),
        (AnchorId::LeftFoot, left_foot),
        (AnchorId::RightHip, right_hip),
        (AnchorId::RightKnee, midpoint(right_hip, right_foot)),
        (AnchorId::RightAnkle, right_foot),
        (AnchorId::RightFoot, right_foot),
        (AnchorId::LeftEye, left_eye),
        (AnchorId::RightEye, right_eye),
        (AnchorId::Mouth, mouth),
        (AnchorId::StaffHand, staff_hand),
        (AnchorId::StaffTop, staff_top),
        (AnchorId::EffectOrigin, staff_top),
    ]))
}

fn classify_region(point: PointF, anchors: &BTreeMap<AnchorId, PointF>) -> RegionId {
    let anchor = |id| anchors[&id];
    let mouth = anchor(AnchorId::Mouth);
    if (point.x - mouth.x).abs() <= 4.0 && (point.y - mouth.y).abs() <= 3.0 {
        return RegionId::Mouth;
    }
    let left_eye = anchor(AnchorId::LeftEye);
    let right_eye = anchor(AnchorId::RightEye);
    if point.y >= left_eye.y - 4.0
        && point.y <= mouth.y + 4.0
        && point.x >= left_eye.x - 5.0
        && point.x <= right_eye.x + 5.0
    {
        return RegionId::Face;
    }
    let staff_hand = anchor(AnchorId::StaffHand);
    let staff_top = anchor(AnchorId::StaffTop);
    let staff_dy = staff_hand.y - staff_top.y;
    let staff_bottom = PointF {
        x: staff_hand.x
            + (staff_hand.x - staff_top.x) / staff_dy.max(1.0)
                * (anchor(AnchorId::Root).y - staff_hand.y),
        y: anchor(AnchorId::Root).y,
    };
    if segment_distance(point, staff_top, staff_bottom) <= 2.6 {
        return RegionId::Staff;
    }
    let head = anchor(AnchorId::Head);
    if point.y < head.y - 5.0 {
        return RegionId::Hat;
    }
    if point.y <= mouth.y + 12.0 {
        return if point.y > mouth.y + 3.0 {
            RegionId::Beard
        } else {
            RegionId::Head
        };
    }
    let left_foot = anchor(AnchorId::LeftFoot);
    let right_foot = anchor(AnchorId::RightFoot);
    if point.y >= left_foot.y - 5.0 {
        return if distance_sq(point, left_foot) <= distance_sq(point, right_foot) {
            RegionId::LeftBoot
        } else {
            RegionId::RightBoot
        };
    }
    if segment_distance(
        point,
        anchor(AnchorId::LeftShoulder),
        anchor(AnchorId::LeftWrist),
    ) <= 6.0
    {
        return RegionId::LeftArm;
    }
    if segment_distance(
        point,
        anchor(AnchorId::RightShoulder),
        anchor(AnchorId::RightWrist),
    ) <= 6.0
    {
        return RegionId::RightArm;
    }
    let pelvis = anchor(AnchorId::Pelvis);
    if point.y >= pelvis.y + 5.0 {
        let root = anchor(AnchorId::Root);
        if (point.x - root.x).abs() < 3.0 {
            return RegionId::InnerRobe;
        }
        let foot_lane = if point.x < root.x {
            RegionId::LeftLeg
        } else {
            RegionId::RightLeg
        };
        if (point.x - root.x).abs() < 8.0 {
            return foot_lane;
        }
        return RegionId::Robe;
    }
    let chest = anchor(AnchorId::Chest);
    if point.y >= chest.y - 5.0 {
        return RegionId::Torso;
    }
    if point.x < head.x {
        RegionId::AdornmentLeft
    } else {
        RegionId::AdornmentRight
    }
}

fn distance_sq(a: PointF, b: PointF) -> f32 {
    (a.x - b.x).powi(2) + (a.y - b.y).powi(2)
}

fn segment_distance(point: PointF, a: PointF, b: PointF) -> f32 {
    let dx = b.x - a.x;
    let dy = b.y - a.y;
    let length_sq = dx * dx + dy * dy;
    let t = if length_sq <= f32::EPSILON {
        0.0
    } else {
        ((point.x - a.x) * dx + (point.y - a.y) * dy) / length_sq
    }
    .clamp(0.0, 1.0);
    ((point.x - (a.x + dx * t)).powi(2) + (point.y - (a.y + dy * t)).powi(2)).sqrt()
}

#[derive(Clone, Copy, Debug, Default)]
struct FootPose {
    offset: PointF,
    swing: f32,
}

#[derive(Clone, Debug, Default)]
struct SemanticGaitRig {
    offsets: BTreeMap<RegionId, PointF>,
    left_foot: FootPose,
    right_foot: FootPose,
    staff_hand: PointF,
    staff_top: PointF,
    robe_open: f32,
    amplitude: f32,
}

fn apply_pose_transition_rig(
    rig: &mut SemanticGaitRig,
    state: &WizardState,
    source: &PoseDefinition,
    target: &PoseDefinition,
    presented: &PoseDefinition,
) {
    let weight = state.pose_blend.clamp(0.0, 1.0);
    let source_rig = semantic_gait_rig(state, source.direction, source);
    let target_rig = semantic_gait_rig(state, target.direction, target);
    let correction_between = |source_point: PointF,
                              target_point: PointF,
                              source_offset: PointF,
                              target_offset: PointF| {
        let source_total = add_points(source_point, source_offset);
        let target_total = add_points(target_point, target_offset);
        if presented.id == source.id {
            PointF {
                x: (target_total.x - source_total.x) * weight,
                y: (target_total.y - source_total.y) * weight,
            }
        } else {
            PointF {
                x: (source_total.x - target_total.x) * (1.0 - weight),
                y: (source_total.y - target_total.y) * (1.0 - weight),
            }
        }
    };
    let region_correction = |region: RegionId, anchor: AnchorId| {
        correction_between(
            source.anchors[&anchor],
            target.anchors[&anchor],
            source_rig.offsets.get(&region).copied().unwrap_or_default(),
            target_rig.offsets.get(&region).copied().unwrap_or_default(),
        )
    };
    for (region, anchor) in [
        (RegionId::Hat, AnchorId::Head),
        (RegionId::Head, AnchorId::Head),
        (RegionId::Beard, AnchorId::Head),
        (RegionId::Mouth, AnchorId::Mouth),
        (RegionId::Torso, AnchorId::Chest),
        (RegionId::Robe, AnchorId::Chest),
        (RegionId::InnerRobe, AnchorId::Chest),
        (RegionId::LeftArm, AnchorId::LeftShoulder),
        (RegionId::RightArm, AnchorId::RightShoulder),
        (RegionId::LeftLeg, AnchorId::LeftKnee),
        (RegionId::RightLeg, AnchorId::RightKnee),
        (RegionId::LeftBoot, AnchorId::LeftFoot),
        (RegionId::RightBoot, AnchorId::RightFoot),
        (RegionId::AdornmentLeft, AnchorId::Chest),
        (RegionId::AdornmentRight, AnchorId::Chest),
        (RegionId::Effect, AnchorId::EffectOrigin),
    ] {
        let current = rig.offsets.entry(region).or_default();
        *current = add_points(*current, region_correction(region, anchor));
    }
    let midpoint = |left: PointF, right: PointF| PointF {
        x: (left.x + right.x) * 0.5,
        y: (left.y + right.y) * 0.5,
    };
    let source_eyes = midpoint(
        source.anchors[&AnchorId::LeftEye],
        source.anchors[&AnchorId::RightEye],
    );
    let target_eyes = midpoint(
        target.anchors[&AnchorId::LeftEye],
        target.anchors[&AnchorId::RightEye],
    );
    let face = rig.offsets.entry(RegionId::Face).or_default();
    *face = add_points(
        *face,
        correction_between(
            source_eyes,
            target_eyes,
            source_rig
                .offsets
                .get(&RegionId::Face)
                .copied()
                .unwrap_or_default(),
            target_rig
                .offsets
                .get(&RegionId::Face)
                .copied()
                .unwrap_or_default(),
        ),
    );
    rig.staff_hand = add_points(
        rig.staff_hand,
        correction_between(
            source.anchors[&AnchorId::StaffHand],
            target.anchors[&AnchorId::StaffHand],
            source_rig.staff_hand,
            target_rig.staff_hand,
        ),
    );
    rig.staff_top = add_points(
        rig.staff_top,
        correction_between(
            source.anchors[&AnchorId::StaffTop],
            target.anchors[&AnchorId::StaffTop],
            source_rig.staff_top,
            target_rig.staff_top,
        ),
    );
}

fn semantic_gait_rig(
    state: &WizardState,
    presented_direction: Direction,
    pose: &PoseDefinition,
) -> SemanticGaitRig {
    let mut offsets = BTreeMap::new();
    let amplitude = if state.locomotion == Locomotion::Walking {
        smooth_step(state.speed_ratio.clamp(0.0, 1.0))
    } else {
        0.0
    };
    let phase = state.walk_phase.rem_euclid(1.0);
    let stride_axis = stride_axis(presented_direction);
    let lift = match presented_direction {
        Direction::West | Direction::East => 3.4,
        Direction::SouthWest
        | Direction::SouthEast
        | Direction::NorthWest
        | Direction::NorthEast => 3.8,
        Direction::South | Direction::North => 3.6,
    };
    let left = foot_pose(phase, stride_axis, lift, amplitude);
    let right = foot_pose((phase + 0.5).rem_euclid(1.0), stride_axis, lift, amplitude);

    let rise = (TAU * phase).sin().powi(2);
    let body = PointF {
        x: -(TAU * phase).cos() * 1.35 * amplitude,
        y: (1.25 - 3.75 * rise) * amplitude,
    };
    let delayed = (TAU * (phase - 0.08)).sin() * amplitude;
    let head = PointF {
        x: body.x * 0.45 - delayed * 0.35,
        y: body.y * 0.70 + delayed * 0.25,
    };

    for region in [
        RegionId::Torso,
        RegionId::Robe,
        RegionId::InnerRobe,
        RegionId::AdornmentLeft,
        RegionId::AdornmentRight,
    ] {
        offsets.insert(region, body);
    }
    for region in [
        RegionId::Hat,
        RegionId::Head,
        RegionId::Beard,
        RegionId::Face,
        RegionId::Mouth,
    ] {
        offsets.insert(region, head);
    }

    offsets.insert(RegionId::LeftBoot, left.offset);
    offsets.insert(RegionId::LeftLeg, lerp_point(body, left.offset, 0.58));
    offsets.insert(RegionId::RightBoot, right.offset);
    offsets.insert(RegionId::RightLeg, lerp_point(body, right.offset, 0.58));

    let arm_wave = (TAU * phase).sin() * amplitude;
    let base_left_arm = PointF {
        x: body.x - arm_wave * 0.55,
        y: body.y + arm_wave * 0.20,
    };
    let base_right_arm = PointF {
        x: body.x + arm_wave * 3.1,
        y: body.y - arm_wave * 1.25,
    };
    let blend = state.upper_body_blend.clamp(0.0, 1.0);
    let from_action = arm_action_offsets(state.previous_upper_body_action);
    let to_action = arm_action_offsets(state.upper_body_action);
    let left_arm = add_points(base_left_arm, lerp_point(from_action.0, to_action.0, blend));
    let right_arm = add_points(
        base_right_arm,
        lerp_point(from_action.1, to_action.1, blend),
    );
    offsets.insert(RegionId::LeftArm, left_arm);
    offsets.insert(RegionId::RightArm, right_arm);
    let staff_blend = state.staff_blend.clamp(0.0, 1.0);
    let from_hand = staff_hand_for(state.previous_staff_state, pose, left_arm, right_arm);
    let to_hand = staff_hand_for(state.staff_state, pose, left_arm, right_arm);
    let staff_hand = lerp_point(from_hand, to_hand, staff_blend);
    let from_top = staff_top_for(state.previous_staff_state, from_hand, body);
    let to_top = staff_top_for(state.staff_state, to_hand, body);
    let staff_top = lerp_point(from_top, to_top, staff_blend);
    offsets.insert(RegionId::Staff, staff_hand);
    let passing = (TAU * phase).sin().powi(2);
    let heel_strike = phase_pulse(phase, 0.375, 0.075).max(phase_pulse(phase, 0.875, 0.075));
    let robe_open = amplitude * (3.2 * passing + 1.1 * heel_strike);
    SemanticGaitRig {
        offsets,
        left_foot: left,
        right_foot: right,
        staff_hand,
        staff_top,
        robe_open,
        amplitude,
    }
}

fn stride_axis(direction: Direction) -> PointF {
    match direction {
        Direction::South => PointF { x: 1.6, y: 2.4 },
        Direction::SouthWest => PointF { x: -8.1, y: 1.7 },
        Direction::West => PointF { x: -11.5, y: 0.3 },
        Direction::NorthWest => PointF { x: -8.1, y: -1.7 },
        Direction::North => PointF { x: -1.6, y: -2.4 },
        Direction::NorthEast => PointF { x: 8.1, y: -1.7 },
        Direction::East => PointF { x: 11.5, y: 0.3 },
        Direction::SouthEast => PointF { x: 8.1, y: 1.7 },
    }
}

fn foot_pose(phase: f32, stride: PointF, lift: f32, amplitude: f32) -> FootPose {
    let phase = phase.rem_euclid(1.0);
    let stance = !(0.25..0.875).contains(&phase);
    if stance {
        let progress = if phase >= 0.875 {
            (phase - 0.875) / 0.375
        } else {
            (phase + 0.125) / 0.375
        };
        let travel = 0.5 - progress;
        FootPose {
            offset: PointF {
                x: stride.x * travel * amplitude,
                y: (stride.y * travel + (PI * progress).sin() * 0.55) * amplitude,
            },
            swing: 0.0,
        }
    } else {
        let progress = (phase - 0.25) / 0.625;
        let eased = progress * progress * (3.0 - 2.0 * progress);
        let clearance = (PI * progress).sin().max(0.0).powf(0.72);
        let toe_clearance = (PI * (progress * 1.35).min(1.0)).sin().max(0.0) * 0.35;
        let travel = eased - 0.5;
        FootPose {
            offset: PointF {
                x: stride.x * travel * amplitude,
                y: (stride.y * travel - lift * (clearance + toe_clearance)) * amplitude,
            },
            swing: clearance * amplitude,
        }
    }
}

fn lerp_point(from: PointF, to: PointF, amount: f32) -> PointF {
    PointF {
        x: from.x + (to.x - from.x) * amount,
        y: from.y + (to.y - from.y) * amount,
    }
}

fn add_points(a: PointF, b: PointF) -> PointF {
    PointF {
        x: a.x + b.x,
        y: a.y + b.y,
    }
}

fn arm_action_offsets(action: UpperBodyAction) -> (PointF, PointF) {
    match action {
        UpperBodyAction::Explain => (PointF { x: 0.0, y: -2.0 }, PointF::default()),
        UpperBodyAction::Point => (PointF::default(), PointF { x: 4.0, y: -1.0 }),
        UpperBodyAction::Think => (PointF { x: 2.0, y: -4.0 }, PointF::default()),
        UpperBodyAction::Cast => (PointF::default(), PointF { x: 3.0, y: -6.0 }),
        UpperBodyAction::React => (PointF { x: -2.0, y: -3.0 }, PointF { x: 2.0, y: -3.0 }),
        UpperBodyAction::None => (PointF::default(), PointF::default()),
    }
}

fn staff_hand_for(
    _state: StaffState,
    pose: &PoseDefinition,
    left_arm: PointF,
    _right_arm: PointF,
) -> PointF {
    let base_staff = pose.anchors[&AnchorId::StaffHand];
    let base_left = pose.anchors[&AnchorId::LeftWrist];
    let authored_grip = PointF {
        x: base_staff.x - base_left.x,
        y: base_staff.y - base_left.y,
    };
    PointF {
        x: base_left.x + left_arm.x + authored_grip.x - base_staff.x,
        y: base_left.y + left_arm.y + authored_grip.y - base_staff.y,
    }
}

fn staff_top_for(state: StaffState, hand: PointF, body: PointF) -> PointF {
    if matches!(state, StaffState::Held | StaffState::Rest) {
        lerp_point(
            hand,
            PointF {
                x: body.x * 0.25,
                y: body.y * 0.25,
            },
            0.72,
        )
    } else {
        hand
    }
}

fn phase_pulse(phase: f32, center: f32, half_width: f32) -> f32 {
    let distance = ((phase - center + 0.5).rem_euclid(1.0) - 0.5).abs();
    (1.0 - distance / half_width).clamp(0.0, 1.0)
}

fn transform_semantic_cell(
    mut point: PointF,
    region: RegionId,
    pose: &PoseDefinition,
    rig: &SemanticGaitRig,
) -> PointF {
    let offset = if region == RegionId::Staff {
        let hand = pose.anchors[&AnchorId::StaffHand];
        let top = pose.anchors[&AnchorId::StaffTop];
        let dx = top.x - hand.x;
        let dy = top.y - hand.y;
        let length_sq = dx * dx + dy * dy;
        let along = if length_sq <= f32::EPSILON {
            0.0
        } else {
            ((point.x - hand.x) * dx + (point.y - hand.y) * dy) / length_sq
        }
        .clamp(0.0, 1.0);
        lerp_point(rig.staff_hand, rig.staff_top, along)
    } else {
        rig.offsets.get(&region).copied().unwrap_or_default()
    };
    point.x += offset.x;
    point.y += offset.y;
    if matches!(region, RegionId::Robe | RegionId::InnerRobe) && rig.amplitude > 0.0 {
        let pelvis_y = pose.anchors[&AnchorId::Pelvis].y;
        let hem = ((point.y - offset.y - pelvis_y) / (pose.root.1 as f32 - pelvis_y - 2.0))
            .clamp(0.0, 1.0);
        let center_x = pose.root.0 as f32;
        let side = if point.x - offset.x < center_x {
            -1.0
        } else if point.x - offset.x > center_x {
            1.0
        } else {
            0.0
        };
        let foot = if side < 0.0 {
            rig.left_foot
        } else {
            rig.right_foot
        };
        let panel_scale = if region == RegionId::Robe { 1.0 } else { 0.45 };
        point.x += side * rig.robe_open * panel_scale * hem;
        point.x += foot.offset.x * 0.10 * hem;
        point.y -= foot.swing * 0.85 * hem;
    }
    point
}

fn anchor_regions() -> [(AnchorId, RegionId); 21] {
    [
        (AnchorId::Root, RegionId::Torso),
        (AnchorId::Pelvis, RegionId::Torso),
        (AnchorId::Chest, RegionId::Torso),
        (AnchorId::LeftShoulder, RegionId::Torso),
        (AnchorId::LeftElbow, RegionId::LeftArm),
        (AnchorId::LeftWrist, RegionId::LeftArm),
        (AnchorId::RightShoulder, RegionId::Torso),
        (AnchorId::RightElbow, RegionId::RightArm),
        (AnchorId::RightWrist, RegionId::RightArm),
        (AnchorId::LeftHip, RegionId::LeftLeg),
        (AnchorId::LeftKnee, RegionId::LeftLeg),
        (AnchorId::LeftAnkle, RegionId::LeftBoot),
        (AnchorId::LeftFoot, RegionId::LeftBoot),
        (AnchorId::RightHip, RegionId::RightLeg),
        (AnchorId::RightKnee, RegionId::RightLeg),
        (AnchorId::RightAnkle, RegionId::RightBoot),
        (AnchorId::RightFoot, RegionId::RightBoot),
        (AnchorId::Head, RegionId::Head),
        (AnchorId::LeftEye, RegionId::Face),
        (AnchorId::RightEye, RegionId::Face),
        (AnchorId::Mouth, RegionId::Mouth),
    ]
}

#[cfg(test)]
mod canvas_normalization_tests {
    use super::*;
    use crate::palette::Rgb;

    #[test]
    fn edge_padding_translates_cells_anchors_and_contacts_without_resampling() {
        let anchors = AnchorId::REQUIRED
            .into_iter()
            .map(|anchor| (anchor, PointF { x: 5.0, y: 9.0 }))
            .collect();
        let mut pose = PoseDefinition {
            id: "small-test-pose".to_string(),
            direction: Direction::South,
            root: (5, 9),
            anchors,
            cells: vec![PoseCell {
                x: 5,
                y: 0,
                cell: Cell::new(b'#', Rgb(1, 2, 3)),
                region: RegionId::Torso,
                stable_id: 0,
            }],
            z_order: RegionId::Z_ORDER.to_vec(),
            cols: 10,
            rows: 10,
            motion: PoseMotionMetadata {
                candidate_id: None,
                family: PoseMotionFamily::Baseline,
                contact_mode: PoseContactMode::BothFeet,
                phase: None,
                authored_transition_neighbors: Vec::new(),
                contact_sets: vec![PoseContactSet {
                    id: "floor".to_string(),
                    points: vec![PoseContactPoint {
                        anchor: AnchorId::LeftFoot,
                        kind: PoseContactKind::Ground,
                        point: (5, 9),
                    }],
                }],
                attachment_edges: Vec::new(),
                staff_present: false,
                effect_present: false,
            },
        };

        normalize_pose_canvas(&mut pose).expect("small pose should fit by edge padding");

        assert_eq!(
            (pose.cols, pose.rows),
            (CANONICAL_POSE_COLS, CANONICAL_POSE_ROWS)
        );
        assert_eq!(pose.root, CANONICAL_POSE_ROOT);
        assert_eq!((pose.cells[0].x, pose.cells[0].y), (36, 86));
        assert_eq!(pose.anchors[&AnchorId::Head], PointF { x: 36.0, y: 95.0 });
        assert_eq!(
            pose.motion.contact_sets[0].points[0].point,
            CANONICAL_POSE_ROOT
        );
        assert_eq!(pose.cells[0].cell.rgb, Rgb(1, 2, 3));
    }

    #[test]
    fn canonical_library_rejects_dimension_drift() {
        let library = PoseLibrary::reference().expect("embedded pose library");
        for pose_id in library.pose_ids() {
            let pose = library.for_id(pose_id).expect("known pose");
            assert_eq!(
                (pose.cols, pose.rows, pose.root),
                (
                    CANONICAL_POSE_COLS,
                    CANONICAL_POSE_ROWS,
                    CANONICAL_POSE_ROOT
                ),
                "{pose_id}"
            );
        }
    }
}
