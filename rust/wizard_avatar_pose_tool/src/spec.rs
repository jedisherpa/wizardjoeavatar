use crate::error::{PoseToolError, Result};
use crate::model::{ContactMode, Direction, MotionFamily, Phase, Point};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum SpecKind {
    Geometry,
    Alias { target_semantic_id: &'static str },
    FaceVariant { base_semantic_id: &'static str },
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct Landmarks {
    pub mouth: Point,
    pub left_eye: Point,
    pub right_eye: Point,
    pub left_foot: Point,
    pub right_foot: Point,
    pub left_hand: Point,
    pub right_hand: Point,
    pub staff_hand: Point,
    pub staff_top: Point,
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct PoseSpec {
    pub order: u32,
    pub candidate_id: &'static str,
    pub semantic_id: &'static str,
    pub kind: SpecKind,
    pub generation_rows: Option<u32>,
    pub family: MotionFamily,
    pub contact_mode: ContactMode,
    pub phase: Option<Phase>,
    pub direction: Direction,
    pub view_family: &'static str,
    pub effect: bool,
    pub landmarks: Landmarks,
    pub neighbors: &'static [&'static str],
}

const fn point(x: i32, y: i32) -> Point {
    Point { x, y }
}

const fn phase(numerator: u16, denominator: u16) -> Option<Phase> {
    Some(Phase {
        numerator,
        denominator,
    })
}

const RUN: &[&str] = &[
    "run_front_airborne_reach",
    "run_front_airborne_drive",
    "front_run_charge_right_plant",
    "walk_front_right_lift",
    "walk_front_left",
    "walk_front_right",
];
const CROUCH: &[&str] = &[
    "front_crouch_guard",
    "front_kneel_staff_brace",
    "front_crouch_reaction_staff_planted",
    "front_crouch_landing_staff_plant",
    "front_idle",
];
const JUMP: &[&str] = &[
    "front_reaction_jump_fist_staff",
    "front_celebrate_jump_staff_up",
    "front_airborne_fall_back_staff",
    "front_celebrate_wings_staff_up",
    "front_idle",
];
const GUARD: &[&str] = &[
    "front_staff_guard_windup",
    "front_staff_guard_low",
    "front_staff_block_horizontal",
    "front_magic_staff_thrust",
    "front_staff_spin_flourish",
    "magic_cast",
];
const SOCIAL: &[&str] = &[
    "front_victory_cast",
    "front_celebrate_wings_staff_up",
    "front_point_direct_staff_held",
    "front_shush_secret_staff_held",
    "front_staff_spin_flourish",
    "front_idle",
    "explaining",
    "magic_cast",
];
const FLY_FRONT: &[&str] = &[
    "fly_front_hover_neutral",
    "fly_front_knee_up",
    "fly_front_wings_up",
    "fly_front_wings_down",
    "fly_southwest_banked_staff",
    "fly_southeast_banked_staff",
];
const FLY_EAST: &[&str] = &[
    "fly_southeast_forward_glide",
    "fly_southeast_banked_staff",
    "fly_southeast_cheer",
    "fly_southeast_staff_forward",
    "fly_front_hover_neutral",
];
const FLY_WEST: &[&str] = &[
    "fly_southwest_banked_staff",
    "fly_front_hover_neutral",
    "fly_southeast_banked_staff",
];

pub(crate) const BASELINE_POSE_IDS: [&str; 10] = [
    "front_idle",
    "back_idle",
    "profile_left",
    "profile_right",
    "walk_front_left",
    "walk_front_right",
    "back_left",
    "back_right",
    "explaining",
    "magic_cast",
];

macro_rules! geometry {
    (
        $order:literal, $candidate:literal, $semantic:literal, $rows:literal,
        $family:ident, $contact:ident, $phase:expr, $direction:ident, $view:literal,
        $effect:expr, $neighbors:expr,
        [$mx:literal,$my:literal], [$lex:literal,$ley:literal], [$rex:literal,$rey:literal],
        [$lfx:literal,$lfy:literal], [$rfx:literal,$rfy:literal],
        [$lhx:literal,$lhy:literal], [$rhx:literal,$rhy:literal],
        [$shx:literal,$shy:literal], [$stx:literal,$sty:literal]
    ) => {
        PoseSpec {
            order: $order,
            candidate_id: $candidate,
            semantic_id: $semantic,
            kind: SpecKind::Geometry,
            generation_rows: Some($rows),
            family: MotionFamily::$family,
            contact_mode: ContactMode::$contact,
            phase: $phase,
            direction: Direction::$direction,
            view_family: $view,
            effect: $effect,
            landmarks: Landmarks {
                mouth: point($mx, $my),
                left_eye: point($lex, $ley),
                right_eye: point($rex, $rey),
                left_foot: point($lfx, $lfy),
                right_foot: point($rfx, $rfy),
                left_hand: point($lhx, $lhy),
                right_hand: point($rhx, $rhy),
                staff_hand: point($shx, $shy),
                staff_top: point($stx, $sty),
            },
            neighbors: $neighbors,
        }
    };
}

pub(crate) const POSE_SPECS: [PoseSpec; 30] = [
    geometry!(
        1,
        "WJP2-01",
        "run_front_airborne_reach",
        91,
        Run,
        Airborne,
        phase(0, 1),
        South,
        "front",
        false,
        RUN,
        [6, -64],
        [2, -73],
        [9, -73],
        [-10, -17],
        [10, -7],
        [-16, -42],
        [26, -46],
        [26, -46],
        [31, -86]
    ),
    geometry!(
        2,
        "WJP2-02",
        "run_front_airborne_drive",
        96,
        Run,
        Airborne,
        phase(1, 2),
        South,
        "front",
        false,
        RUN,
        [6, -65],
        [3, -72],
        [9, -72],
        [-11, -16],
        [11, -6],
        [-2, -51],
        [25, -52],
        [25, -52],
        [28, -87]
    ),
    geometry!(
        3,
        "WJP2-03",
        "front_crouch_guard",
        74,
        GroundAction,
        BothFeet,
        None,
        South,
        "front",
        false,
        CROUCH,
        [4, -38],
        [0, -45],
        [8, -45],
        [-12, -3],
        [11, -3],
        [-16, -22],
        [25, -32],
        [25, -32],
        [31, -71]
    ),
    geometry!(
        4,
        "WJP2-04",
        "front_reaction_jump_fist_staff",
        93,
        Jump,
        Airborne,
        None,
        South,
        "front",
        false,
        JUMP,
        [0, -56],
        [-5, -67],
        [5, -67],
        [-12, -7],
        [14, -8],
        [-24, -53],
        [23, -44],
        [23, -44],
        [28, -78]
    ),
    geometry!(
        5,
        "WJP2-05",
        "front_kneel_staff_brace",
        73,
        Kneel,
        KneelAndStaff,
        None,
        South,
        "front",
        false,
        CROUCH,
        [0, -44],
        [-4, -52],
        [4, -52],
        [-10, -2],
        [10, -1],
        [-14, -24],
        [17, -31],
        [17, -31],
        [23, -59]
    ),
    geometry!(
        6,
        "WJP2-06",
        "front_staff_guard_windup",
        78,
        GroundAction,
        BothFeet,
        phase(1, 4),
        South,
        "front",
        false,
        GUARD,
        [0, -47],
        [-4, -56],
        [4, -56],
        [-11, -1],
        [12, -1],
        [3, -37],
        [12, -35],
        [12, -35],
        [22, -64]
    ),
    geometry!(
        7,
        "WJP2-07",
        "front_staff_guard_low",
        94,
        GroundAction,
        BothFeet,
        phase(1, 2),
        South,
        "front",
        false,
        GUARD,
        [0, -57],
        [-5, -68],
        [5, -68],
        [-16, -1],
        [17, -1],
        [-6, -49],
        [13, -37],
        [-6, -49],
        [-21, -65]
    ),
    geometry!(
        8,
        "WJP2-08",
        "walk_front_right_lift",
        94,
        Walk,
        LeftFoot,
        phase(3, 4),
        SouthEast,
        "front_three_quarter",
        false,
        RUN,
        [0, -59],
        [-5, -64],
        [5, -64],
        [-7, -1],
        [15, -3],
        [-2, -43],
        [20, -44],
        [-2, -44],
        [13, -80]
    ),
    geometry!(
        9,
        "WJP2-09",
        "front_crouch_reaction_staff_planted",
        68,
        GroundAction,
        BothFeetAndStaff,
        None,
        South,
        "front",
        false,
        CROUCH,
        [2, -44],
        [-3, -51],
        [6, -51],
        [-14, -1],
        [9, -1],
        [-12, -32],
        [22, -30],
        [22, -30],
        [28, -66]
    ),
    geometry!(
        10,
        "WJP2-10",
        "front_victory_cast",
        96,
        GroundAction,
        BothFeet,
        None,
        South,
        "front",
        false,
        SOCIAL,
        [0, -59],
        [-5, -64],
        [5, -64],
        [-8, -1],
        [11, -1],
        [-18, -63],
        [19, -64],
        [19, -64],
        [19, -90]
    ),
    geometry!(
        11,
        "WJFA-01",
        "fly_front_hover_neutral",
        91,
        Flight,
        Airborne,
        None,
        South,
        "front",
        false,
        FLY_FRONT,
        [0, -60],
        [-5, -70],
        [5, -70],
        [-6, -9],
        [6, -9],
        [-15, -38],
        [19, -43],
        [19, -43],
        [26, -82]
    ),
    geometry!(
        12,
        "WJFA-02",
        "fly_front_knee_up",
        83,
        Flight,
        Airborne,
        phase(1, 4),
        South,
        "front",
        false,
        FLY_FRONT,
        [0, -60],
        [-5, -70],
        [5, -70],
        [-9, -7],
        [7, -15],
        [-12, -37],
        [19, -42],
        [19, -42],
        [27, -82]
    ),
    geometry!(
        13,
        "WJFA-03",
        "fly_front_wings_up",
        96,
        Flight,
        Airborne,
        phase(1, 2),
        South,
        "front",
        false,
        FLY_FRONT,
        [0, -60],
        [-5, -70],
        [5, -70],
        [-5, -9],
        [6, -8],
        [-13, -39],
        [21, -40],
        [21, -40],
        [29, -78]
    ),
    geometry!(
        14,
        "WJFA-04",
        "fly_front_wings_down",
        85,
        Flight,
        Airborne,
        phase(3, 4),
        South,
        "front",
        false,
        FLY_FRONT,
        [0, -60],
        [-5, -70],
        [5, -70],
        [-5, -11],
        [6, -11],
        [-16, -44],
        [20, -48],
        [20, -48],
        [26, -81]
    ),
    geometry!(
        15,
        "WJFA-05",
        "fly_southeast_forward_glide",
        60,
        Flight,
        Airborne,
        phase(7, 20),
        SouthEast,
        "front_three_quarter",
        false,
        FLY_EAST,
        [8, -64],
        [3, -70],
        [12, -70],
        [-16, -17],
        [-8, -15],
        [-22, -47],
        [22, -47],
        [-22, -47],
        [-32, -51]
    ),
    geometry!(
        16,
        "WJFA-06",
        "fly_southwest_banked_staff",
        85,
        Flight,
        Airborne,
        None,
        SouthWest,
        "front_three_quarter",
        false,
        FLY_WEST,
        [3, -62],
        [-2, -70],
        [8, -69],
        [-8, -11],
        [5, -6],
        [-21, -39],
        [21, -44],
        [-21, -39],
        [-32, -73]
    ),
    geometry!(
        17,
        "WJFA-07",
        "fly_southeast_banked_staff",
        82,
        Flight,
        Airborne,
        None,
        SouthEast,
        "front_three_quarter",
        false,
        FLY_EAST,
        [2, -61],
        [-3, -70],
        [7, -69],
        [-12, -12],
        [2, -5],
        [-13, -45],
        [19, -38],
        [19, -38],
        [25, -63]
    ),
    geometry!(
        18,
        "WJFA-08",
        "fly_southeast_cheer",
        96,
        Flight,
        Airborne,
        None,
        SouthEast,
        "front_three_quarter",
        false,
        FLY_EAST,
        [3, -61],
        [-2, -70],
        [8, -69],
        [-7, -10],
        [6, -6],
        [-14, -71],
        [20, -53],
        [20, -53],
        [26, -90]
    ),
    geometry!(
        19,
        "WJFA-09",
        "fly_southeast_staff_forward",
        71,
        Flight,
        Airborne,
        phase(13, 20),
        SouthEast,
        "front_three_quarter",
        false,
        FLY_EAST,
        [5, -59],
        [0, -67],
        [10, -66],
        [-21, -19],
        [-5, -14],
        [-14, -50],
        [20, -50],
        [20, -50],
        [28, -71]
    ),
    PoseSpec {
        order: 20,
        candidate_id: "WJFA-10",
        semantic_id: "fly_front_hover_ready",
        kind: SpecKind::Alias {
            target_semantic_id: "fly_front_hover_neutral",
        },
        generation_rows: None,
        family: MotionFamily::Flight,
        contact_mode: ContactMode::Airborne,
        phase: None,
        direction: Direction::South,
        view_family: "front",
        effect: false,
        landmarks: Landmarks {
            mouth: point(0, -60),
            left_eye: point(-5, -70),
            right_eye: point(5, -70),
            left_foot: point(-6, -9),
            right_foot: point(6, -9),
            left_hand: point(-15, -38),
            right_hand: point(19, -43),
            staff_hand: point(19, -43),
            staff_top: point(26, -82),
        },
        neighbors: FLY_FRONT,
    },
    geometry!(
        21,
        "WJFA-11",
        "front_run_charge_right_plant",
        77,
        Run,
        RightFoot,
        phase(1, 4),
        South,
        "front",
        false,
        RUN,
        [0, -47],
        [-4, -51],
        [6, -51],
        [-8, -7],
        [18, -1],
        [-12, -31],
        [21, -37],
        [21, -37],
        [32, -66]
    ),
    geometry!(
        22,
        "WJFA-12",
        "front_crouch_landing_staff_plant",
        74,
        Landing,
        HandFootAndStaff,
        None,
        South,
        "front",
        false,
        CROUCH,
        [0, -43],
        [-5, -47],
        [5, -47],
        [-21, -1],
        [14, -3],
        [-18, -2],
        [20, -43],
        [20, -43],
        [32, -68]
    ),
    geometry!(
        23,
        "WJFA-13",
        "front_magic_staff_thrust",
        73,
        GroundAction,
        BothFeet,
        None,
        South,
        "front",
        true,
        GUARD,
        [7, -45],
        [3, -48],
        [13, -48],
        [-13, -1],
        [21, -2],
        [-9, -39],
        [23, -31],
        [-9, -39],
        [-28, -53]
    ),
    geometry!(
        24,
        "WJFA-14",
        "front_airborne_fall_back_staff",
        80,
        Jump,
        Airborne,
        None,
        South,
        "front",
        false,
        JUMP,
        [0, -51],
        [-5, -55],
        [6, -55],
        [-5, -7],
        [25, -10],
        [-16, -40],
        [20, -45],
        [20, -45],
        [32, -67]
    ),
    geometry!(
        25,
        "WJFA-15",
        "front_celebrate_wings_staff_up",
        90,
        GroundAction,
        BothFeet,
        None,
        South,
        "front",
        false,
        SOCIAL,
        [0, -56],
        [-5, -61],
        [5, -61],
        [-9, -1],
        [16, -1],
        [18, -63],
        [-18, -65],
        [-18, -65],
        [-24, -86]
    ),
    geometry!(
        26,
        "WJFA-16",
        "front_staff_block_horizontal",
        75,
        GroundAction,
        BothFeet,
        None,
        South,
        "front",
        false,
        GUARD,
        [0, -47],
        [-5, -51],
        [6, -51],
        [-14, -1],
        [19, -1],
        [-19, -37],
        [8, -40],
        [-19, -37],
        [33, -42]
    ),
    geometry!(
        27,
        "WJFA-17",
        "front_point_direct_staff_held",
        94,
        GroundAction,
        BothFeet,
        None,
        South,
        "front",
        false,
        SOCIAL,
        [0, -58],
        [-5, -63],
        [5, -63],
        [-11, -1],
        [17, -1],
        [-23, -59],
        [21, -49],
        [21, -49],
        [27, -83]
    ),
    geometry!(
        28,
        "WJFA-18",
        "front_celebrate_jump_staff_up",
        92,
        Jump,
        Airborne,
        None,
        South,
        "front",
        false,
        JUMP,
        [0, -56],
        [-5, -60],
        [6, -60],
        [-9, -9],
        [13, -7],
        [-15, -68],
        [18, -69],
        [18, -69],
        [25, -86]
    ),
    geometry!(
        29,
        "WJFA-19",
        "front_shush_secret_staff_held",
        96,
        GroundAction,
        BothFeet,
        None,
        South,
        "front",
        false,
        SOCIAL,
        [0, -60],
        [-5, -65],
        [5, -65],
        [-9, -5],
        [14, -1],
        [-1, -51],
        [21, -50],
        [21, -50],
        [25, -84]
    ),
    geometry!(
        30,
        "WJFA-20",
        "front_staff_spin_flourish",
        75,
        GroundAction,
        BothFeet,
        None,
        South,
        "front",
        true,
        SOCIAL,
        [0, -47],
        [-5, -51],
        [6, -51],
        [-11, -1],
        [22, -1],
        [26, -44],
        [-13, -45],
        [-13, -45],
        [-26, -65]
    ),
];

pub(crate) fn pose_spec(candidate_id: &str) -> Result<&'static PoseSpec> {
    POSE_SPECS
        .iter()
        .chain(crate::feelings_spec::WJFL_SPECS.iter())
        .find(|spec| spec.candidate_id == candidate_id)
        .ok_or_else(|| PoseToolError::Archive(format!("no Rust semantic spec for {candidate_id}")))
}

pub(crate) fn all_pose_specs() -> impl Iterator<Item = &'static PoseSpec> {
    POSE_SPECS
        .iter()
        .chain(crate::feelings_spec::WJFL_SPECS.iter())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    #[test]
    fn table_has_thirty_ordered_records_and_one_alias() {
        assert_eq!(POSE_SPECS.len(), 30);
        assert_eq!(
            POSE_SPECS
                .iter()
                .map(|spec| spec.candidate_id)
                .collect::<BTreeSet<_>>()
                .len(),
            30
        );
        for (index, spec) in POSE_SPECS.iter().enumerate() {
            assert_eq!(spec.order, index as u32 + 1);
        }
        assert_eq!(
            POSE_SPECS
                .iter()
                .filter(|spec| matches!(spec.kind, SpecKind::Alias { .. }))
                .count(),
            1
        );
    }

    #[test]
    fn all_authored_neighbors_resolve_to_new_or_baseline_geometry() {
        let geometries = all_pose_specs()
            .filter(|spec| !matches!(spec.kind, SpecKind::Alias { .. }))
            .map(|spec| spec.semantic_id)
            .collect::<BTreeSet<_>>();
        let allowed = geometries
            .union(&BASELINE_POSE_IDS.into_iter().collect())
            .copied()
            .collect::<BTreeSet<_>>();
        for spec in all_pose_specs() {
            assert!(!spec.neighbors.is_empty(), "{}", spec.candidate_id);
            for neighbor in spec.neighbors {
                assert!(
                    allowed.contains(neighbor),
                    "{} unresolved neighbor {neighbor}",
                    spec.candidate_id
                );
            }
        }
    }

    #[test]
    fn combined_catalog_has_eighty_ordered_records() {
        let specs = all_pose_specs().collect::<Vec<_>>();
        assert_eq!(specs.len(), 80);
        for (index, spec) in specs.iter().enumerate() {
            assert_eq!(spec.order, index as u32 + 1);
        }
    }
}
