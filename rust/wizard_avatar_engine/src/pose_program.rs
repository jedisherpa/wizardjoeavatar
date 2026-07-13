#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MotionFamily {
    GroundLocomotion,
    Flight,
    Reaction,
    StaffAction,
    Gesture,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ContactMode {
    BothFeet,
    LeftFoot,
    RightFoot,
    Airborne,
    Hover,
    Landing,
    Kneel,
    StaffPlant,
    HandAndFeet,
}

#[derive(Clone, Copy, Debug)]
pub struct FuturePoseMotionSpec {
    pub candidate_id: &'static str,
    pub semantic_id: &'static str,
    pub family: MotionFamily,
    pub contact: ContactMode,
    pub phase: Option<f32>,
    pub neighbors: &'static [&'static str],
    pub duplicate_of: Option<&'static str>,
}

const IDLE: &[&str] = &["front_idle"];
const WALK: &[&str] = &["front_idle", "walk_front_left", "walk_front_right"];
const RUN: &[&str] = &["front_run_charge_right_plant", "run_front_airborne_reach"];
const HOVER: &[&str] = &["front_idle", "fly_front_hover_neutral"];
const FLAP: &[&str] = &[
    "fly_front_hover_neutral",
    "fly_front_knee_up",
    "fly_front_wings_up",
    "fly_front_wings_down",
];
const BANK: &[&str] = &[
    "fly_front_hover_neutral",
    "fly_southwest_banked_staff",
    "fly_southeast_banked_staff",
];
const GLIDE: &[&str] = &[
    "fly_southeast_banked_staff",
    "fly_southeast_forward_glide",
    "fly_southeast_staff_forward",
];
const REACTION: &[&str] = &[
    "front_idle",
    "front_reaction_jump_fist_staff",
    "front_celebrate_jump_staff_up",
    "front_celebrate_wings_staff_up",
    "front_victory_cast",
    "front_crouch_reaction_staff_planted",
    "front_kneel_staff_brace",
];
const STAFF: &[&str] = &[
    "front_idle",
    "front_staff_guard_windup",
    "front_staff_guard_low",
    "front_staff_block_horizontal",
    "front_magic_staff_thrust",
    "magic_cast",
    "front_staff_spin_flourish",
];
const GESTURE: &[&str] = &[
    "front_idle",
    "explaining",
    "front_point_direct_staff_held",
    "front_shush_secret_staff_held",
];

pub const FUTURE_POSE_MOTION_SPECS: [FuturePoseMotionSpec; 30] = [
    spec(
        "WJP2-01",
        "run_front_airborne_reach",
        MotionFamily::GroundLocomotion,
        ContactMode::Airborne,
        Some(0.0),
        RUN,
    ),
    spec(
        "WJP2-02",
        "run_front_airborne_drive",
        MotionFamily::GroundLocomotion,
        ContactMode::Airborne,
        Some(0.5),
        RUN,
    ),
    spec(
        "WJP2-03",
        "front_crouch_guard",
        MotionFamily::Reaction,
        ContactMode::BothFeet,
        None,
        REACTION,
    ),
    spec(
        "WJP2-04",
        "front_reaction_jump_fist_staff",
        MotionFamily::Reaction,
        ContactMode::Airborne,
        None,
        REACTION,
    ),
    spec(
        "WJP2-05",
        "front_kneel_staff_brace",
        MotionFamily::Reaction,
        ContactMode::Kneel,
        None,
        REACTION,
    ),
    spec(
        "WJP2-06",
        "front_staff_guard_windup",
        MotionFamily::StaffAction,
        ContactMode::BothFeet,
        Some(0.25),
        STAFF,
    ),
    spec(
        "WJP2-07",
        "front_staff_guard_low",
        MotionFamily::StaffAction,
        ContactMode::BothFeet,
        Some(0.5),
        STAFF,
    ),
    spec(
        "WJP2-08",
        "walk_front_right_lift",
        MotionFamily::GroundLocomotion,
        ContactMode::LeftFoot,
        Some(0.75),
        WALK,
    ),
    spec(
        "WJP2-09",
        "front_crouch_reaction_staff_planted",
        MotionFamily::Reaction,
        ContactMode::StaffPlant,
        None,
        REACTION,
    ),
    spec(
        "WJP2-10",
        "front_victory_cast",
        MotionFamily::Reaction,
        ContactMode::BothFeet,
        None,
        REACTION,
    ),
    spec(
        "WJFA-01",
        "fly_front_hover_neutral",
        MotionFamily::Flight,
        ContactMode::Hover,
        Some(0.0),
        HOVER,
    ),
    spec(
        "WJFA-02",
        "fly_front_knee_up",
        MotionFamily::Flight,
        ContactMode::Hover,
        Some(0.25),
        FLAP,
    ),
    spec(
        "WJFA-03",
        "fly_front_wings_up",
        MotionFamily::Flight,
        ContactMode::Hover,
        Some(0.5),
        FLAP,
    ),
    spec(
        "WJFA-04",
        "fly_front_wings_down",
        MotionFamily::Flight,
        ContactMode::Hover,
        Some(0.75),
        FLAP,
    ),
    spec(
        "WJFA-05",
        "fly_southeast_forward_glide",
        MotionFamily::Flight,
        ContactMode::Airborne,
        Some(0.35),
        GLIDE,
    ),
    spec(
        "WJFA-06",
        "fly_southwest_banked_staff",
        MotionFamily::Flight,
        ContactMode::Airborne,
        None,
        BANK,
    ),
    spec(
        "WJFA-07",
        "fly_southeast_banked_staff",
        MotionFamily::Flight,
        ContactMode::Airborne,
        None,
        BANK,
    ),
    spec(
        "WJFA-08",
        "fly_southeast_cheer",
        MotionFamily::Flight,
        ContactMode::Airborne,
        None,
        REACTION,
    ),
    spec(
        "WJFA-09",
        "fly_southeast_staff_forward",
        MotionFamily::Flight,
        ContactMode::Airborne,
        Some(0.65),
        GLIDE,
    ),
    alias(
        "WJFA-10",
        "fly_front_hover_ready",
        "fly_front_hover_neutral",
    ),
    spec(
        "WJFA-11",
        "front_run_charge_right_plant",
        MotionFamily::GroundLocomotion,
        ContactMode::RightFoot,
        Some(0.25),
        RUN,
    ),
    spec(
        "WJFA-12",
        "front_crouch_landing_staff_plant",
        MotionFamily::GroundLocomotion,
        ContactMode::HandAndFeet,
        None,
        &["front_crouch_guard", "front_idle"],
    ),
    spec(
        "WJFA-13",
        "front_magic_staff_thrust",
        MotionFamily::StaffAction,
        ContactMode::BothFeet,
        None,
        STAFF,
    ),
    spec(
        "WJFA-14",
        "front_airborne_fall_back_staff",
        MotionFamily::Flight,
        ContactMode::Airborne,
        None,
        &[
            "fly_front_hover_neutral",
            "front_crouch_landing_staff_plant",
        ],
    ),
    spec(
        "WJFA-15",
        "front_celebrate_wings_staff_up",
        MotionFamily::Reaction,
        ContactMode::BothFeet,
        None,
        REACTION,
    ),
    spec(
        "WJFA-16",
        "front_staff_block_horizontal",
        MotionFamily::StaffAction,
        ContactMode::BothFeet,
        None,
        STAFF,
    ),
    spec(
        "WJFA-17",
        "front_point_direct_staff_held",
        MotionFamily::Gesture,
        ContactMode::BothFeet,
        None,
        GESTURE,
    ),
    spec(
        "WJFA-18",
        "front_celebrate_jump_staff_up",
        MotionFamily::Reaction,
        ContactMode::Airborne,
        None,
        REACTION,
    ),
    spec(
        "WJFA-19",
        "front_shush_secret_staff_held",
        MotionFamily::Gesture,
        ContactMode::BothFeet,
        None,
        GESTURE,
    ),
    spec(
        "WJFA-20",
        "front_staff_spin_flourish",
        MotionFamily::StaffAction,
        ContactMode::BothFeet,
        None,
        STAFF,
    ),
];

pub const BASELINE_POSE_IDS: [&str; 10] = [
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

#[must_use]
pub fn is_authored_pose_id(pose_id: &str) -> bool {
    BASELINE_POSE_IDS.contains(&pose_id)
        || FUTURE_POSE_MOTION_SPECS.iter().any(|spec| {
            spec.semantic_id == pose_id || spec.duplicate_of.is_some_and(|alias| alias == pose_id)
        })
        || crate::pose::PoseLibrary::reference()
            .is_ok_and(|library| library.for_id(pose_id).is_some())
}

const fn spec(
    candidate_id: &'static str,
    semantic_id: &'static str,
    family: MotionFamily,
    contact: ContactMode,
    phase: Option<f32>,
    neighbors: &'static [&'static str],
) -> FuturePoseMotionSpec {
    FuturePoseMotionSpec {
        candidate_id,
        semantic_id,
        family,
        contact,
        phase,
        neighbors,
        duplicate_of: None,
    }
}

const fn alias(
    candidate_id: &'static str,
    semantic_id: &'static str,
    duplicate_of: &'static str,
) -> FuturePoseMotionSpec {
    FuturePoseMotionSpec {
        candidate_id,
        semantic_id,
        family: MotionFamily::Flight,
        contact: ContactMode::Hover,
        phase: None,
        neighbors: IDLE,
        duplicate_of: Some(duplicate_of),
    }
}

#[must_use]
pub fn future_pose_motion_spec(semantic_id: &str) -> Option<&'static FuturePoseMotionSpec> {
    FUTURE_POSE_MOTION_SPECS
        .iter()
        .find(|spec| spec.semantic_id == semantic_id)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pose_archive::future_pose_catalog;
    use std::collections::BTreeSet;

    #[test]
    fn every_archived_pose_has_one_rust_motion_spec() {
        let catalog = future_pose_catalog().expect("catalog");
        let catalog_ids = catalog
            .references()
            .map(|reference| reference.semantic_id.as_str())
            .collect::<BTreeSet<_>>();
        let spec_ids = FUTURE_POSE_MOTION_SPECS
            .iter()
            .map(|spec| spec.semantic_id)
            .collect::<BTreeSet<_>>();
        assert_eq!(catalog_ids, spec_ids);
        assert_eq!(spec_ids.len(), 30);
        assert_eq!(
            FUTURE_POSE_MOTION_SPECS
                .iter()
                .filter(|spec| spec.duplicate_of.is_some())
                .count(),
            1
        );
    }

    #[test]
    fn flight_specs_never_claim_ground_contact() {
        for spec in FUTURE_POSE_MOTION_SPECS
            .iter()
            .filter(|spec| spec.family == MotionFamily::Flight)
        {
            assert!(
                matches!(spec.contact, ContactMode::Airborne | ContactMode::Hover),
                "{} has invalid flight contact {:?}",
                spec.semantic_id,
                spec.contact
            );
        }
    }
}
