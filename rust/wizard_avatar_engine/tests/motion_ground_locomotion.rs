use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use wizard_avatar_engine::motion_catalog::{runtime_geometry_authority, shadow_motion_catalog};

mod motion_graph {
    pub use wizard_avatar_engine::motion_graph::*;
}

#[path = "../src/motion_director.rs"]
#[allow(dead_code)]
mod motion_director;

use motion_director::{
    ClipCompletionState, ClipPhaseInput, DistancePhaseTick, ExitRequest, MarkerEventKind,
    MotionDirector, TransitionDirector, TransitionMarkerTick, TransitionPhaseInput,
    TransitionTimeline,
};
use motion_graph::{
    ContactPoint, GroundLocomotionRole, LoopMode, MotionClip, MotionGraphV1, MotionMarker,
    MotionSample, PhaseSource, SupportContact, GROUND_LOCOMOTION_CLIP_IDS,
    GROUND_LOCOMOTION_EDGE_ROUTES, GROUND_LOCOMOTION_ROLE_CLIPS, MAX_GROUND_FACING_DELTA_STEPS,
    REQUIRED_RUNTIME_GEOMETRY_COUNT, REQUIRED_WJFL_GEOMETRY_COUNT,
};
use wizard_avatar_engine::pose::{analyze_pose_topology, PoseLibrary};
use wizard_avatar_engine::state::{Direction, WizardState};

fn graph() -> &'static MotionGraphV1 {
    &shadow_motion_catalog()
        .expect("embedded shadow motion catalog")
        .graph
}

fn clip(clip_id: &str) -> &'static MotionClip {
    graph()
        .clips
        .iter()
        .find(|clip| clip.clip_id == clip_id)
        .expect("ground locomotion clip")
}

fn declared_contacts(support: &SupportContact) -> BTreeSet<ContactPoint> {
    support.points.iter().copied().collect()
}

fn support_marker(point: ContactPoint, planted: bool) -> MotionMarker {
    match (point, planted) {
        (ContactPoint::LeftFoot, true) => MotionMarker::LeftContact,
        (ContactPoint::LeftFoot, false) => MotionMarker::LeftRelease,
        (ContactPoint::RightFoot, true) => MotionMarker::RightContact,
        (ContactPoint::RightFoot, false) => MotionMarker::RightRelease,
        (ContactPoint::StaffTip, true) => MotionMarker::StaffPlant,
        (ContactPoint::StaffTip, false) => MotionMarker::StaffRelease,
        (ContactPoint::LeftHand | ContactPoint::RightHand, true) => MotionMarker::HandPlant,
        (ContactPoint::LeftHand | ContactPoint::RightHand, false) => MotionMarker::HandRelease,
    }
}

fn assert_support_transition_markers(
    context: &str,
    previous: &SupportContact,
    current: &MotionSample,
) -> bool {
    let previous = declared_contacts(previous);
    let current_contacts = declared_contacts(&current.support);
    for added in current_contacts.difference(&previous) {
        let marker = support_marker(*added, true);
        assert!(
            current.markers.contains(&marker),
            "{context} adds {added:?} without {marker:?}"
        );
    }
    for removed in previous.difference(&current_contacts) {
        let marker = support_marker(*removed, false);
        assert!(
            current.markers.contains(&marker),
            "{context} removes {removed:?} without {marker:?}"
        );
    }
    previous != current_contacts
}

fn authored_facing(pose_id: &str) -> Direction {
    let pose = graph()
        .pose_coverage
        .iter()
        .find(|pose| pose.pose_id == pose_id)
        .expect("pose coverage");
    let [facing] = pose.approved_facings.as_slice() else {
        panic!("ground pose {pose_id} must have one authored facing");
    };
    *facing
}

fn direction_index(direction: Direction) -> u8 {
    Direction::ALL
        .iter()
        .position(|candidate| *candidate == direction)
        .expect("canonical direction") as u8
}

fn facing_delta_steps(source_pose_id: &str, target_pose_id: &str) -> u8 {
    let direct = direction_index(authored_facing(source_pose_id))
        .abs_diff(direction_index(authored_facing(target_pose_id)));
    direct.min(Direction::ALL.len() as u8 - direct)
}

#[test]
fn family_has_six_distinct_roles_and_preserves_89_geometry_50_wjfl_authority() {
    graph()
        .validate_ground_locomotion_family()
        .expect("complete ground locomotion family");
    let authority = runtime_geometry_authority().expect("Rust geometry authority");
    assert_eq!(authority.len(), REQUIRED_RUNTIME_GEOMETRY_COUNT);
    assert_eq!(
        authority
            .iter()
            .filter_map(|row| row.source_candidate_id.as_deref())
            .filter(|candidate| candidate.starts_with("WJFL-"))
            .count(),
        REQUIRED_WJFL_GEOMETRY_COUNT
    );

    let clips = GROUND_LOCOMOTION_CLIP_IDS.map(clip);
    let roles = GROUND_LOCOMOTION_ROLE_CLIPS
        .into_iter()
        .map(|(role, clip_id)| {
            assert_eq!(clip(clip_id).ground_locomotion_role, Some(role));
            role
        })
        .collect::<BTreeSet<_>>();
    assert_eq!(
        roles,
        BTreeSet::from([
            GroundLocomotionRole::Start,
            GroundLocomotionRole::Walk,
            GroundLocomotionRole::Run,
            GroundLocomotionRole::Stop,
            GroundLocomotionRole::TurnLeft,
            GroundLocomotionRole::TurnRight,
        ])
    );
    assert_eq!(
        clips.iter().map(|clip| clip.samples.len()).sum::<usize>(),
        29
    );
    assert_eq!(
        clips
            .iter()
            .flat_map(|clip| &clip.samples)
            .map(|sample| sample.markers.len())
            .sum::<usize>(),
        76
    );
    assert_eq!(
        clips
            .iter()
            .flat_map(|clip| &clip.samples)
            .flat_map(|sample| &sample.markers)
            .filter(|marker| {
                matches!(
                    marker,
                    MotionMarker::LeftContact
                        | MotionMarker::LeftRelease
                        | MotionMarker::RightContact
                        | MotionMarker::RightRelease
                )
            })
            .count(),
        26
    );
    assert_eq!(
        clips
            .iter()
            .flat_map(|clip| &clip.samples)
            .flat_map(|sample| &sample.markers)
            .filter(|marker| {
                matches!(
                    marker,
                    MotionMarker::StaffPlant | MotionMarker::StaffRelease
                )
            })
            .count(),
        12
    );
    assert_eq!(clip("ground_walk_front").loop_mode, LoopMode::MarkedSegment);
    assert_eq!(clip("ground_run_front").loop_mode, LoopMode::MarkedSegment);
    assert_eq!(
        clip("ground_walk_front").phase_source,
        PhaseSource::Distance
    );
    assert_eq!(clip("ground_run_front").phase_source, PhaseSource::Distance);
    for clip_id in [
        "ground_start_front",
        "ground_stop_front",
        "ground_turn_left",
        "ground_turn_right",
    ] {
        let finite = clip(clip_id);
        assert_eq!(finite.loop_mode, LoopMode::Once);
        assert_eq!(finite.phase_source, PhaseSource::Time);
        assert!(finite.loop_start_sample.is_none());
        assert!(finite.loop_end_sample.is_none());
        assert!(!finite.samples.iter().any(|sample| {
            sample.markers.contains(&MotionMarker::LoopStart)
                || sample.markers.contains(&MotionMarker::LoopEnd)
        }));
    }
}

#[test]
fn every_declared_support_change_is_marker_complete_and_foot_phase_stays_alternating() {
    let mut support_transition_count = 0usize;
    let mut loop_support_transition_count = 0usize;
    for clip_id in GROUND_LOCOMOTION_CLIP_IDS {
        let clip = clip(clip_id);
        for (index, pair) in clip.samples.windows(2).enumerate() {
            if assert_support_transition_markers(
                &format!("{clip_id} sample {}", index + 1),
                &pair[0].support,
                &pair[1],
            ) {
                support_transition_count += 1;
            }
        }
        if let (Some(start), Some(end)) = (clip.loop_start_sample, clip.loop_end_sample) {
            if assert_support_transition_markers(
                &format!("{clip_id} loop closure"),
                &clip.samples[end].support,
                &clip.samples[start],
            ) {
                loop_support_transition_count += 1;
            }
        }
    }
    assert_eq!(support_transition_count, 16);
    assert_eq!(loop_support_transition_count, 2);

    let normalized = |clip: &MotionClip| {
        let start = clip.loop_start_sample.expect("loop start");
        let end = clip.loop_end_sample.expect("loop end");
        clip.samples[start..=end]
            .iter()
            .flat_map(|sample| sample.markers.iter().copied())
            .filter(|marker| {
                matches!(
                    marker,
                    MotionMarker::LeftContact
                        | MotionMarker::LeftRelease
                        | MotionMarker::RightContact
                        | MotionMarker::RightRelease
                )
            })
            .collect::<Vec<_>>()
    };
    let expected = vec![
        MotionMarker::RightRelease,
        MotionMarker::LeftContact,
        MotionMarker::LeftRelease,
        MotionMarker::RightContact,
    ];
    assert_eq!(normalized(clip("ground_walk_front")), expected);
    assert_eq!(normalized(clip("ground_run_front")), expected);
}

#[test]
fn start_stop_and_turn_roles_have_required_authored_progression() {
    let marker_index = |clip: &MotionClip, marker| {
        clip.samples
            .iter()
            .position(|sample| sample.markers.contains(&marker))
            .expect("required marker")
    };
    let start = clip("ground_start_front");
    assert!(
        marker_index(start, MotionMarker::Settled)
            < marker_index(start, MotionMarker::Anticipation)
    );
    assert!(
        marker_index(start, MotionMarker::Anticipation)
            < marker_index(start, MotionMarker::Release)
    );
    assert_eq!(
        start.samples.last().expect("start exit").pose_id,
        "front_run_charge_right_plant"
    );

    let stop = clip("ground_stop_front");
    assert_eq!(marker_index(stop, MotionMarker::RightContact), 0);
    assert!(marker_index(stop, MotionMarker::Impact) < marker_index(stop, MotionMarker::Recover));
    assert!(marker_index(stop, MotionMarker::Recover) < marker_index(stop, MotionMarker::Settled));
    assert_eq!(
        stop.samples
            .iter()
            .filter(|sample| sample.markers.contains(&MotionMarker::Exit))
            .count(),
        1
    );

    for (clip_id, profile_pose, front_return_profile) in [
        (
            "ground_turn_left",
            "profile_left",
            "ground_turn_left_front_return",
        ),
        (
            "ground_turn_right",
            "profile_right",
            "ground_turn_right_front_return",
        ),
    ] {
        let turn = clip(clip_id);
        let profile = turn
            .samples
            .iter()
            .position(|sample| sample.pose_id == profile_pose)
            .expect("profile pose");
        assert!(profile > marker_index(turn, MotionMarker::Anticipation));
        assert!(profile < marker_index(turn, MotionMarker::Recover));
        assert!(turn.samples[0]
            .markers
            .contains(&MotionMarker::RightContact));
        assert_eq!(turn.samples.last().expect("restart").pose_id, "front_idle");
        assert_eq!(
            turn.samples
                .last()
                .expect("front return")
                .secondary_profile_id,
            front_return_profile
        );
        assert_eq!(
            authored_facing(&turn.samples.last().expect("exit").pose_id),
            Direction::South
        );
    }
}

#[test]
fn every_authored_facing_and_contact_sync_edge_is_explicit_and_reachable() {
    let coverage = graph()
        .pose_coverage
        .iter()
        .map(|pose| (pose.pose_id.as_str(), pose))
        .collect::<BTreeMap<_, _>>();
    let phase_matrix = [
        (
            "ground_start_front",
            vec![Direction::South, Direction::South, Direction::South],
        ),
        (
            "ground_walk_front",
            vec![
                Direction::SouthWest,
                Direction::South,
                Direction::SouthEast,
                Direction::SouthEast,
                Direction::South,
                Direction::South,
            ],
        ),
        (
            "ground_run_front",
            vec![
                Direction::SouthWest,
                Direction::South,
                Direction::South,
                Direction::South,
            ],
        ),
        (
            "ground_stop_front",
            vec![
                Direction::SouthEast,
                Direction::SouthEast,
                Direction::South,
                Direction::South,
            ],
        ),
        (
            "ground_turn_left",
            vec![
                Direction::SouthEast,
                Direction::South,
                Direction::SouthWest,
                Direction::West,
                Direction::SouthWest,
                Direction::South,
            ],
        ),
        (
            "ground_turn_right",
            vec![
                Direction::SouthEast,
                Direction::South,
                Direction::SouthEast,
                Direction::East,
                Direction::SouthEast,
                Direction::South,
            ],
        ),
    ];
    for (clip_id, facings) in phase_matrix {
        assert_eq!(clip(clip_id).samples.len(), facings.len());
        for (sample, facing) in clip(clip_id).samples.iter().zip(facings) {
            assert!(coverage[sample.pose_id.as_str()]
                .approved_facings
                .contains(&facing));
        }
    }

    let director = TransitionDirector::new(graph()).expect("transition director");
    let mut support_handoffs = 0usize;
    for (source, target) in GROUND_LOCOMOTION_EDGE_ROUTES {
        let resolved = director
            .resolve_between(source, target)
            .expect("one directed ground edge");
        assert_eq!(resolved.recipe.recipe_id, "contact_sync");
        assert_eq!(resolved.fallback_depth, 0);
        let source_clip = clip_or_graph(source);
        let target_clip = clip_or_graph(target);
        if assert_support_transition_markers(
            &format!("{source}->{target}"),
            &source_clip.samples.last().expect("source sample").support,
            target_clip.samples.first().expect("target sample"),
        ) {
            support_handoffs += 1;
        }
        let timeline = TransitionTimeline::new(
            100,
            12,
            vec![
                TransitionMarkerTick {
                    marker: MotionMarker::Entry,
                    cycle: 0,
                    occurrence: 0,
                    offset_tick: 0,
                },
                TransitionMarkerTick {
                    marker: MotionMarker::Commit,
                    cycle: 0,
                    occurrence: 0,
                    offset_tick: 4,
                },
                TransitionMarkerTick {
                    marker: MotionMarker::Exit,
                    cycle: 0,
                    occurrence: 0,
                    offset_tick: 10,
                },
            ],
        )
        .expect("contact timeline");
        for tick in [100, 104, 112] {
            director
                .evaluate(
                    &resolved.edge.edge_id,
                    &timeline,
                    TransitionPhaseInput::Distance(DistancePhaseTick(tick)),
                    None,
                )
                .expect("contact-aware exact tick");
        }
    }
    assert_eq!(support_handoffs, 6);
}

#[test]
fn authored_frame_facing_delta_is_at_most_one_step_within_clips_loops_and_edges() {
    let mut boundary_count = 0usize;
    let mut maximum_delta = 0u8;
    let mut assert_pair = |context: &str, source: &str, target: &str| {
        let delta = facing_delta_steps(source, target);
        assert!(
            delta <= MAX_GROUND_FACING_DELTA_STEPS,
            "{context} snaps {source}->{target} by {delta} facing steps"
        );
        maximum_delta = maximum_delta.max(delta);
        boundary_count += 1;
    };

    for clip_id in GROUND_LOCOMOTION_CLIP_IDS {
        let clip = clip(clip_id);
        for pair in clip.samples.windows(2) {
            assert_pair(clip_id, &pair[0].pose_id, &pair[1].pose_id);
        }
        if let (Some(start), Some(end)) = (clip.loop_start_sample, clip.loop_end_sample) {
            assert_pair(
                &format!("{clip_id} loop closure"),
                &clip.samples[end].pose_id,
                &clip.samples[start].pose_id,
            );
        }
    }
    for (source, target) in GROUND_LOCOMOTION_EDGE_ROUTES {
        let source = clip_or_graph(source);
        let target = clip_or_graph(target);
        assert_pair(
            &format!("{}->{}", source.clip_id, target.clip_id),
            &source.samples.last().expect("source sample").pose_id,
            &target.samples.first().expect("target sample").pose_id,
        );
    }

    assert_eq!(boundary_count, 38);
    assert_eq!(maximum_delta, MAX_GROUND_FACING_DELTA_STEPS);
}

fn replay_hash() -> String {
    let director = MotionDirector::new(graph()).expect("motion director");
    let mut hasher = Sha256::new();
    for clip_id in ["ground_walk_front", "ground_run_front"] {
        let evaluator = director.clip(clip_id).expect("distance clip");
        let loop_ticks = if clip_id == "ground_walk_front" {
            20
        } else {
            10
        };
        let mut playback = evaluator.begin_playback();
        for tick in [0, loop_ticks - 1, loop_ticks * 2 - 1, loop_ticks * 3 - 1] {
            let advance = playback
                .advance_to(ClipPhaseInput::Distance(DistancePhaseTick(tick)))
                .expect("skipped distance phase");
            hasher.update(format!("{:?}", advance.evaluation).as_bytes());
            for event in advance.crossed_markers {
                hasher.update(format!("{:?}", event.expect("marker event")).as_bytes());
            }
        }
        playback
            .request_exit(ExitRequest {
                requested_at_tick: loop_ticks * 3 - 1,
            })
            .expect("exit request");
        for tick in [loop_ticks * 3, loop_ticks * 3 + 2] {
            let advance = playback
                .advance_to(ClipPhaseInput::Distance(DistancePhaseTick(tick)))
                .expect("distance exit boundary");
            hasher.update(format!("{:?}", advance.evaluation).as_bytes());
            for event in advance.crossed_markers {
                hasher.update(format!("{:?}", event.expect("exit event")).as_bytes());
            }
        }
    }
    format!("{:x}", hasher.finalize())
}

#[test]
fn distance_loops_cross_three_cycles_skipped_ticks_and_exact_exit_boundaries() {
    let director = MotionDirector::new(graph()).expect("motion director");
    for (clip_id, loop_ticks) in [("ground_walk_front", 20), ("ground_run_front", 10)] {
        let evaluator = director.clip(clip_id).expect("distance clip");
        let mut playback = evaluator.begin_playback();
        let mut events = Vec::new();
        for tick in [0, loop_ticks - 1, loop_ticks * 2 - 1, loop_ticks * 3 - 1] {
            let advance = playback
                .advance_to(ClipPhaseInput::Distance(DistancePhaseTick(tick)))
                .expect("three-cycle advance");
            events.extend(
                advance
                    .crossed_markers
                    .collect::<Result<Vec<_>, _>>()
                    .expect("crossed markers"),
            );
        }
        assert_eq!(
            events
                .iter()
                .filter(|event| event.kind == MarkerEventKind::LifecycleEntry)
                .count(),
            1
        );
        assert_eq!(
            events
                .iter()
                .filter(|event| event.marker == MotionMarker::LoopStart)
                .count(),
            3
        );
        playback
            .request_exit(ExitRequest {
                requested_at_tick: loop_ticks * 3 - 1,
            })
            .expect("exit request");
        let boundary = playback
            .advance_to(ClipPhaseInput::Distance(DistancePhaseTick(loop_ticks * 3)))
            .expect("safe exit boundary");
        assert_eq!(
            boundary.evaluation.sample_index,
            evaluator.clip().samples.len() - 1
        );
        assert_eq!(boundary.evaluation.sample_local_tick, 0);
        let completed = playback
            .advance_to(ClipPhaseInput::Distance(DistancePhaseTick(
                loop_ticks * 3 + 2,
            )))
            .expect("half-open completion");
        assert!(matches!(
            completed.evaluation.completion,
            ClipCompletionState::Completed { .. }
        ));
        assert_eq!(
            completed
                .crossed_markers
                .collect::<Result<Vec<_>, _>>()
                .expect("lifecycle exit")
                .iter()
                .filter(|event| event.kind == MarkerEventKind::LifecycleExit)
                .count(),
            1
        );
    }

    let first = replay_hash();
    assert_eq!(first, replay_hash());
    assert_eq!(
        first,
        "efe07f95ee0e5c07edbcb87c3956405fc7573e04412fc019d356990aea81de3b"
    );
}

#[test]
fn sampled_semantic_pose_transitions_keep_body_and_staff_topology_coherent() {
    let library = PoseLibrary::reference().expect("Rust pose library");
    let mut transitions = Vec::new();
    for clip_id in GROUND_LOCOMOTION_CLIP_IDS {
        let clip = clip(clip_id);
        transitions.extend(
            clip.samples
                .windows(2)
                .map(|pair| (pair[0].pose_id.as_str(), pair[1].pose_id.as_str())),
        );
        if let (Some(start), Some(end)) = (clip.loop_start_sample, clip.loop_end_sample) {
            transitions.push((
                clip.samples[end].pose_id.as_str(),
                clip.samples[start].pose_id.as_str(),
            ));
        }
    }
    for (source_id, target_id) in GROUND_LOCOMOTION_EDGE_ROUTES {
        let source = clip_or_graph(source_id);
        let target = clip_or_graph(target_id);
        transitions.push((
            source
                .samples
                .last()
                .expect("source sample")
                .pose_id
                .as_str(),
            target
                .samples
                .first()
                .expect("target sample")
                .pose_id
                .as_str(),
        ));
    }

    let mut semantic_sample_count = 0usize;
    for (source, target) in transitions {
        assert!(
            facing_delta_steps(source, target) <= MAX_GROUND_FACING_DELTA_STEPS,
            "semantic transition {source}->{target} exceeds the authored facing bound"
        );
        for blend_percent in [0, 25, 50, 75, 100] {
            let mut state = WizardState {
                pose_id: Some(target.to_string()),
                previous_pose_id: Some(source.to_string()),
                pose_blend: blend_percent as f32 / 100.0,
                pose_handoff: false,
                ..WizardState::default()
            };
            if blend_percent == 100 {
                state.previous_pose_id = None;
            }
            let sample = library.sample(&state).expect("complete Rust pose sample");
            let topology = analyze_pose_topology(&sample);
            assert_eq!(
                topology.unexpected_fragment_components, 0,
                "{source}->{target}"
            );
            assert_eq!(topology.horizontal_seam_rows, 0, "{source}->{target}");
            assert_eq!(topology.vertical_crack_cells, 0, "{source}->{target}");
            assert!(topology.staff_components <= 1, "{source}->{target}");
            assert_eq!(topology.staff_scanline_gaps, 0, "{source}->{target}");
            semantic_sample_count += 1;
        }
    }
    assert_eq!(semantic_sample_count, 190);
}

fn clip_or_graph(clip_id: &str) -> &'static MotionClip {
    graph()
        .clips
        .iter()
        .find(|clip| clip.clip_id == clip_id)
        .expect("edge clip")
}

#[test]
fn locomotion_validator_rejects_phase_contact_root_and_edge_regressions() {
    let mut wrong_phase = graph().clone();
    wrong_phase
        .clips
        .iter_mut()
        .find(|clip| clip.clip_id == "ground_walk_front")
        .expect("walk")
        .phase_source = PhaseSource::Time;
    assert!(wrong_phase.validate_ground_locomotion_family().is_err());

    let mut missing_contact = graph().clone();
    missing_contact
        .clips
        .iter_mut()
        .find(|clip| clip.clip_id == "ground_run_front")
        .expect("run")
        .samples[1]
        .markers
        .retain(|marker| *marker != MotionMarker::LeftRelease);
    assert!(missing_contact.validate_ground_locomotion_family().is_err());

    let mut missing_staff_marker = graph().clone();
    missing_staff_marker
        .clips
        .iter_mut()
        .find(|clip| clip.clip_id == "ground_start_front")
        .expect("start")
        .samples[2]
        .markers
        .retain(|marker| *marker != MotionMarker::StaffRelease);
    assert!(missing_staff_marker
        .validate_ground_locomotion_family()
        .is_err());

    let mut facing_snap = graph().clone();
    facing_snap
        .clips
        .iter_mut()
        .find(|clip| clip.clip_id == "ground_turn_left")
        .expect("left turn")
        .samples
        .last_mut()
        .expect("turn exit")
        .pose_id = "walk_front_right".into();
    assert!(facing_snap.validate_ground_locomotion_family().is_err());

    let mut root_teleport = graph().clone();
    root_teleport
        .clips
        .iter_mut()
        .find(|clip| clip.clip_id == "ground_turn_left")
        .expect("turn")
        .samples[2]
        .root_offset = [3, 0];
    assert!(root_teleport.validate_ground_locomotion_family().is_err());

    let mut duplicate_route = graph().clone();
    let duplicate = duplicate_route
        .edges
        .iter()
        .find(|edge| edge.edge_id == "ground_edge_003_walk_to_run")
        .expect("ground edge")
        .clone();
    duplicate_route.edges.push(duplicate);
    assert!(duplicate_route.validate_ground_locomotion_family().is_err());

    let mut unregistered_route = graph().clone();
    let mut extra = unregistered_route
        .edges
        .iter()
        .find(|edge| edge.edge_id == "ground_edge_002_start_to_walk")
        .expect("ground edge")
        .clone();
    extra.edge_id = "ground_edge_014_unregistered_shortcut".into();
    extra.target_clip_id = "ground_stop_front".into();
    unregistered_route.edges.push(extra);
    assert!(unregistered_route
        .validate_ground_locomotion_family()
        .is_err());

    let mut duplicate_role = graph().clone();
    duplicate_role
        .clips
        .iter_mut()
        .find(|clip| clip.clip_id == "ground_turn_right")
        .expect("right turn")
        .ground_locomotion_role = Some(GroundLocomotionRole::TurnLeft);
    assert!(duplicate_role.validate_ground_locomotion_family().is_err());
}
