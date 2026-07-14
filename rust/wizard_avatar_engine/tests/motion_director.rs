mod motion_graph {
    pub use wizard_avatar_engine::motion_graph::*;
}

#[path = "../src/motion_director.rs"]
mod motion_director;

use motion_director::{
    select_transition_duration, ClipCompletionState, ClipEvaluator, ClipExitState, ClipPhaseInput,
    DistancePhaseTick, ExitRequest, MarkerEvent, MarkerEventKind, MotionDirector,
    MotionDirectorError, SimulationTick, SpeechPhaseTick, TransitionContactState,
    TransitionDirector, TransitionInterruptPosition, TransitionInterruptRequest,
    TransitionLifecycleState, TransitionMarkerTick, TransitionPhaseInput, TransitionRootState,
    TransitionSecondaryState, TransitionTimeline, WingPhaseTick,
};
use motion_graph::{
    ChannelMask, ClipFamily, ContactPoint, ContactPolicy, InterruptPolicy, InterruptWindow,
    LoopMode, MotionClip, MotionGraphV1, MotionMarker, MotionSample, PerformanceRegion,
    PhaseSource, RecoveryPolicy, RegionPolicy, RootPolicy, SecondaryPolicy, SupportContact,
    SupportMode, TickRange, TransitionTiming,
};
use sha2::{Digest, Sha256};

fn sample(index: usize, hold_ticks: u16, markers: Vec<MotionMarker>) -> MotionSample {
    MotionSample {
        pose_id: format!("pose_{index}"),
        hold_ticks,
        transition_recipe_id: "coherent_handoff".to_string(),
        markers,
        support: SupportContact {
            mode: SupportMode::Grounded,
            points: vec![ContactPoint::LeftFoot, ContactPoint::RightFoot],
        },
        root_offset: [0, 0],
        secondary_profile_id: "settled".to_string(),
    }
}

fn clip(
    clip_id: &str,
    loop_mode: LoopMode,
    phase_source: PhaseSource,
    samples: Vec<MotionSample>,
    loop_bounds: Option<(usize, usize)>,
) -> MotionClip {
    MotionClip {
        clip_id: clip_id.to_string(),
        family: ClipFamily::Idle,
        ground_locomotion_role: None,
        loop_mode,
        phase_source,
        entry_marker: MotionMarker::Entry,
        exit_markers: vec![MotionMarker::Exit],
        minimum_hold_ticks: 1,
        interrupt_policy: InterruptPolicy::AtSafeMarker,
        owned_channels: ChannelMask {
            regions: vec![PerformanceRegion::BaseBody],
        },
        samples,
        loop_start_sample: loop_bounds.map(|bounds| bounds.0),
        loop_end_sample: loop_bounds.map(|bounds| bounds.1),
        reduced_motion_clip_id: None,
    }
}

fn time(tick: u64) -> ClipPhaseInput {
    ClipPhaseInput::Time(SimulationTick(tick))
}

fn collect_events(
    events: impl Iterator<Item = Result<MarkerEvent, MotionDirectorError>>,
) -> Vec<MarkerEvent> {
    events
        .collect::<Result<Vec<_>, _>>()
        .expect("marker events")
}

fn event_trace(events: &[MarkerEvent]) -> Vec<(u64, u64, usize, MotionMarker, MarkerEventKind)> {
    events
        .iter()
        .map(|event| {
            (
                event.tick,
                event.cycle,
                event.sample_index,
                event.marker,
                event.kind,
            )
        })
        .collect()
}

#[test]
fn once_holds_are_half_open_and_marker_channels_are_distinct() {
    let clip = clip(
        "once",
        LoopMode::Once,
        PhaseSource::Time,
        vec![
            sample(0, 2, vec![MotionMarker::Entry, MotionMarker::Anticipation]),
            sample(1, 3, vec![MotionMarker::Impact, MotionMarker::Exit]),
        ],
        None,
    );
    let evaluator = ClipEvaluator::new(&clip).expect("once evaluator");

    let expected = [
        (0, 0, 0, 0, ClipCompletionState::Playing),
        (1, 0, 1, 0, ClipCompletionState::Playing),
        (2, 1, 0, 0, ClipCompletionState::Playing),
        (4, 1, 2, 0, ClipCompletionState::Playing),
        (
            5,
            1,
            3,
            0,
            ClipCompletionState::Completed {
                completed_at_tick: 5,
            },
        ),
    ];
    for (tick, sample_index, local_tick, cycle, completion) in expected {
        let actual = evaluator.evaluate(time(tick), None).expect("once sample");
        assert_eq!(
            (
                actual.sample_index,
                actual.sample_local_tick,
                actual.cycle,
                actual.completion,
            ),
            (sample_index, local_tick, cycle, completion),
            "tick {tick}"
        );
    }
    assert_eq!(
        evaluator
            .evaluate(time(1), None)
            .expect("active sample")
            .active_markers,
        [MotionMarker::Entry, MotionMarker::Anticipation]
    );
    assert!(evaluator
        .evaluate(time(5), None)
        .expect("completed sample")
        .active_markers
        .is_empty());

    let mut playback = evaluator.begin_playback();
    let first = playback.advance_to(time(0)).expect("tick zero");
    assert_eq!(
        event_trace(&collect_events(first.crossed_markers)),
        vec![
            (
                0,
                0,
                0,
                MotionMarker::Entry,
                MarkerEventKind::LifecycleEntry,
            ),
            (
                0,
                0,
                0,
                MotionMarker::Anticipation,
                MarkerEventKind::SampleEntry,
            ),
        ]
    );
    assert!(collect_events(
        playback
            .advance_to(time(1))
            .expect("inside hold")
            .crossed_markers
    )
    .is_empty());
    assert_eq!(
        event_trace(&collect_events(
            playback
                .advance_to(time(4))
                .expect("cross sample entry")
                .crossed_markers,
        )),
        vec![(2, 0, 1, MotionMarker::Impact, MarkerEventKind::SampleEntry,)]
    );
    assert_eq!(
        event_trace(&collect_events(
            playback
                .advance_to(time(5))
                .expect("complete")
                .crossed_markers,
        )),
        vec![(5, 0, 1, MotionMarker::Exit, MarkerEventKind::LifecycleExit,)]
    );
}

#[test]
fn once_exit_uses_natural_duration_for_shorter_or_longer_minimum_hold() {
    for minimum_hold_ticks in [1, 9] {
        let mut clip = clip(
            "once_exit",
            LoopMode::Once,
            PhaseSource::Time,
            vec![
                sample(0, 2, vec![MotionMarker::Entry, MotionMarker::Commit]),
                sample(1, 3, vec![MotionMarker::Recover, MotionMarker::Exit]),
            ],
            None,
        );
        clip.minimum_hold_ticks = minimum_hold_ticks;
        let evaluator = ClipEvaluator::new(&clip).expect("once exit evaluator");
        let request = Some(ExitRequest {
            requested_at_tick: 2,
        });

        assert_eq!(
            evaluator
                .evaluate(time(1), request)
                .expect("before request")
                .exit,
            ClipExitState::NotRequested
        );
        for tick in [2, 4] {
            assert_eq!(
                evaluator
                    .evaluate(time(tick), request)
                    .expect("pending once exit")
                    .exit,
                ClipExitState::Pending {
                    requested_at_tick: 2,
                    safe_exit_tick: 5,
                },
                "minimum hold {minimum_hold_ticks}, tick {tick}"
            );
        }
        let completed = evaluator
            .evaluate(time(5), request)
            .expect("exact half-open completion");
        assert_eq!(
            completed.completion,
            ClipCompletionState::Completed {
                completed_at_tick: 5,
            }
        );
        assert_eq!(
            completed.exit,
            ClipExitState::Satisfied {
                requested_at_tick: 2,
                safe_exit_tick: 5,
            }
        );

        let request_at_completion = Some(ExitRequest {
            requested_at_tick: 5,
        });
        assert_eq!(
            evaluator
                .evaluate(time(4), request_at_completion)
                .expect("before exact request")
                .exit,
            ClipExitState::NotRequested
        );
        assert_eq!(
            evaluator
                .evaluate(time(5), request_at_completion)
                .expect("request at completion")
                .exit,
            ClipExitState::Satisfied {
                requested_at_tick: 5,
                safe_exit_tick: 5,
            }
        );

        let request_after_completion = Some(ExitRequest {
            requested_at_tick: 6,
        });
        assert_eq!(
            evaluator
                .evaluate(time(5), request_after_completion)
                .expect("natural completion precedes request")
                .exit,
            ClipExitState::NotRequested
        );
    }
}

#[test]
fn once_skipped_boundary_advance_emits_all_sample_and_lifecycle_markers() {
    let mut clip = clip(
        "once_skipped",
        LoopMode::Once,
        PhaseSource::Time,
        vec![
            sample(0, 2, vec![MotionMarker::Anticipation, MotionMarker::Commit]),
            sample(
                1,
                3,
                vec![
                    MotionMarker::Impact,
                    MotionMarker::Recover,
                    MotionMarker::Settled,
                ],
            ),
        ],
        None,
    );
    clip.entry_marker = MotionMarker::Anticipation;
    clip.exit_markers = vec![MotionMarker::Settled, MotionMarker::Recover];
    let evaluator = ClipEvaluator::new(&clip).expect("skipped once evaluator");
    let mut playback = evaluator.begin_playback();
    playback
        .request_exit(ExitRequest {
            requested_at_tick: 1,
        })
        .expect("once exit request");

    let completed = playback
        .advance_to(time(5))
        .expect("skip directly to completion");
    assert_eq!(
        completed.evaluation.exit,
        ClipExitState::Satisfied {
            requested_at_tick: 1,
            safe_exit_tick: 5,
        }
    );
    assert_eq!(
        event_trace(&collect_events(completed.crossed_markers)),
        vec![
            (
                0,
                0,
                0,
                MotionMarker::Anticipation,
                MarkerEventKind::LifecycleEntry,
            ),
            (0, 0, 0, MotionMarker::Commit, MarkerEventKind::SampleEntry,),
            (2, 0, 1, MotionMarker::Impact, MarkerEventKind::SampleEntry,),
            (
                5,
                0,
                1,
                MotionMarker::Settled,
                MarkerEventKind::LifecycleExit,
            ),
            (
                5,
                0,
                1,
                MotionMarker::Recover,
                MarkerEventKind::LifecycleExit,
            ),
        ]
    );
}

#[test]
fn lifecycle_events_follow_declared_marker_contract_and_exit_order() {
    let mut clip = clip(
        "custom_lifecycle",
        LoopMode::Once,
        PhaseSource::Time,
        vec![
            sample(
                0,
                1,
                vec![
                    MotionMarker::Entry,
                    MotionMarker::Anticipation,
                    MotionMarker::Commit,
                ],
            ),
            sample(
                1,
                1,
                vec![
                    MotionMarker::Recover,
                    MotionMarker::Impact,
                    MotionMarker::Settled,
                    MotionMarker::Exit,
                ],
            ),
        ],
        None,
    );
    clip.entry_marker = MotionMarker::Anticipation;
    clip.exit_markers = vec![MotionMarker::Settled, MotionMarker::Recover];
    let evaluator = ClipEvaluator::new(&clip).expect("custom lifecycle evaluator");
    let mut playback = evaluator.begin_playback();

    let active = playback.advance_to(time(0)).expect("custom entry");
    assert_eq!(
        event_trace(&collect_events(active.crossed_markers)),
        vec![
            (0, 0, 0, MotionMarker::Entry, MarkerEventKind::SampleEntry,),
            (
                0,
                0,
                0,
                MotionMarker::Anticipation,
                MarkerEventKind::LifecycleEntry,
            ),
            (0, 0, 0, MotionMarker::Commit, MarkerEventKind::SampleEntry,),
        ]
    );
    let second_sample = playback.advance_to(time(1)).expect("custom exit sample");
    assert_eq!(
        event_trace(&collect_events(second_sample.crossed_markers)),
        vec![
            (1, 0, 1, MotionMarker::Impact, MarkerEventKind::SampleEntry,),
            (1, 0, 1, MotionMarker::Exit, MarkerEventKind::SampleEntry,),
        ]
    );
    let completed = playback.advance_to(time(2)).expect("custom completion");
    assert_eq!(
        event_trace(&collect_events(completed.crossed_markers)),
        vec![
            (
                2,
                0,
                1,
                MotionMarker::Settled,
                MarkerEventKind::LifecycleExit,
            ),
            (
                2,
                0,
                1,
                MotionMarker::Recover,
                MarkerEventKind::LifecycleExit,
            ),
        ]
    );
}

#[test]
fn one_sample_clip_and_maximum_hold_obey_exact_boundaries() {
    let clip = clip(
        "max_hold",
        LoopMode::Once,
        PhaseSource::Time,
        vec![sample(
            0,
            u16::MAX,
            vec![MotionMarker::Entry, MotionMarker::Exit],
        )],
        None,
    );
    let evaluator = ClipEvaluator::new(&clip).expect("max hold evaluator");

    let start = evaluator.evaluate(time(0), None).expect("start");
    assert_eq!((start.sample_index, start.sample_local_tick), (0, 0));
    let final_active = evaluator
        .evaluate(time(u64::from(u16::MAX) - 1), None)
        .expect("final active tick");
    assert_eq!(
        (final_active.sample_index, final_active.sample_local_tick),
        (0, u64::from(u16::MAX) - 1)
    );
    let complete = evaluator
        .evaluate(time(u64::from(u16::MAX)), None)
        .expect("completion boundary");
    assert_eq!(
        complete.completion,
        ClipCompletionState::Completed {
            completed_at_tick: u64::from(u16::MAX),
        }
    );
}

#[test]
fn repeat_trace_crosses_three_loop_boundaries_without_lifecycle_reentry() {
    let clip = clip(
        "repeat",
        LoopMode::Repeat,
        PhaseSource::Time,
        vec![
            sample(0, 2, vec![MotionMarker::Entry, MotionMarker::LoopStart]),
            sample(1, 1, vec![MotionMarker::LoopEnd, MotionMarker::Exit]),
        ],
        None,
    );
    let evaluator = ClipEvaluator::new(&clip).expect("repeat evaluator");

    for (tick, sample_index, local_tick, cycle) in [
        (0, 0, 0, 0),
        (2, 1, 0, 0),
        (3, 0, 0, 1),
        (5, 1, 0, 1),
        (6, 0, 0, 2),
        (8, 1, 0, 2),
        (9, 0, 0, 3),
    ] {
        let actual = evaluator.evaluate(time(tick), None).expect("repeat tick");
        assert_eq!(
            (actual.sample_index, actual.sample_local_tick, actual.cycle),
            (sample_index, local_tick, cycle),
            "tick {tick}"
        );
    }

    let mut playback = evaluator.begin_playback();
    let events = collect_events(
        playback
            .advance_to(time(9))
            .expect("three repeat boundaries")
            .crossed_markers,
    );
    assert_eq!(
        event_trace(&events),
        vec![
            (
                0,
                0,
                0,
                MotionMarker::Entry,
                MarkerEventKind::LifecycleEntry
            ),
            (
                0,
                0,
                0,
                MotionMarker::LoopStart,
                MarkerEventKind::SampleEntry
            ),
            (2, 0, 1, MotionMarker::LoopEnd, MarkerEventKind::SampleEntry),
            (
                3,
                1,
                0,
                MotionMarker::LoopStart,
                MarkerEventKind::SampleEntry
            ),
            (5, 1, 1, MotionMarker::LoopEnd, MarkerEventKind::SampleEntry),
            (
                6,
                2,
                0,
                MotionMarker::LoopStart,
                MarkerEventKind::SampleEntry
            ),
            (8, 2, 1, MotionMarker::LoopEnd, MarkerEventKind::SampleEntry),
            (
                9,
                3,
                0,
                MotionMarker::LoopStart,
                MarkerEventKind::SampleEntry
            ),
        ]
    );
    assert_eq!(
        events
            .iter()
            .filter(|event| event.marker == MotionMarker::Entry)
            .count(),
        1
    );
    assert!(events
        .iter()
        .all(|event| event.kind != MarkerEventKind::LifecycleExit));
}

#[test]
fn repeat_exit_request_completes_at_next_whole_cycle() {
    let clip = clip(
        "repeat_exit",
        LoopMode::Repeat,
        PhaseSource::Time,
        vec![
            sample(0, 2, vec![MotionMarker::Entry]),
            sample(1, 1, vec![MotionMarker::Settled, MotionMarker::Exit]),
        ],
        None,
    );
    let evaluator = ClipEvaluator::new(&clip).expect("repeat evaluator");
    let mut playback = evaluator.begin_playback();
    collect_events(playback.advance_to(time(0)).expect("start").crossed_markers);
    playback
        .request_exit(ExitRequest {
            requested_at_tick: 4,
        })
        .expect("exit request");

    let pending = playback.advance_to(time(4)).expect("pending");
    assert_eq!(
        pending.evaluation.exit,
        ClipExitState::Pending {
            requested_at_tick: 4,
            safe_exit_tick: 6,
        }
    );
    collect_events(pending.crossed_markers);
    let complete = playback.advance_to(time(6)).expect("safe exit");
    assert_eq!(
        complete.evaluation.completion,
        ClipCompletionState::Completed {
            completed_at_tick: 6,
        }
    );
    assert_eq!(
        complete.evaluation.exit,
        ClipExitState::Satisfied {
            requested_at_tick: 4,
            safe_exit_tick: 6,
        }
    );
    assert_eq!(
        event_trace(&collect_events(complete.crossed_markers)),
        vec![
            (5, 1, 1, MotionMarker::Settled, MarkerEventKind::SampleEntry),
            (6, 1, 1, MotionMarker::Exit, MarkerEventKind::LifecycleExit),
        ]
    );
}

#[test]
fn repeat_exit_respects_minimum_hold_at_exact_boundaries() {
    for (minimum_hold_ticks, requested_at_tick, safe_exit_tick) in [(6, 1, 6), (7, 1, 9), (7, 9, 9)]
    {
        let mut clip = clip(
            "repeat_minimum",
            LoopMode::Repeat,
            PhaseSource::Time,
            vec![
                sample(0, 2, vec![MotionMarker::Entry]),
                sample(1, 1, vec![MotionMarker::Exit]),
            ],
            None,
        );
        clip.minimum_hold_ticks = minimum_hold_ticks;
        let evaluator = ClipEvaluator::new(&clip).expect("repeat minimum evaluator");
        let request = Some(ExitRequest { requested_at_tick });

        let expected_before = if safe_exit_tick - 1 < requested_at_tick {
            ClipExitState::NotRequested
        } else {
            ClipExitState::Pending {
                requested_at_tick,
                safe_exit_tick,
            }
        };
        assert_eq!(
            evaluator
                .evaluate(time(safe_exit_tick - 1), request)
                .expect("before safe boundary")
                .exit,
            expected_before
        );
        let safe = evaluator
            .evaluate(time(safe_exit_tick), request)
            .expect("exact safe boundary");
        assert_eq!(
            safe.completion,
            ClipCompletionState::Completed {
                completed_at_tick: safe_exit_tick,
            }
        );
        assert_eq!(
            safe.exit,
            ClipExitState::Satisfied {
                requested_at_tick,
                safe_exit_tick,
            }
        );
    }
}

fn marked_clip() -> MotionClip {
    clip(
        "marked",
        LoopMode::MarkedSegment,
        PhaseSource::Time,
        vec![
            sample(0, 2, vec![MotionMarker::Entry, MotionMarker::Anticipation]),
            sample(1, 2, vec![MotionMarker::LoopStart]),
            sample(2, 3, vec![MotionMarker::LoopEnd]),
            sample(3, 1, vec![MotionMarker::Settled, MotionMarker::Exit]),
        ],
        Some((1, 2)),
    )
}

#[test]
fn marked_segment_runs_prefix_once_and_repeats_inclusive_bounds() {
    let clip = marked_clip();
    let evaluator = ClipEvaluator::new(&clip).expect("marked evaluator");

    for (tick, sample_index, local_tick, cycle) in [
        (0, 0, 0, 0),
        (1, 0, 1, 0),
        (2, 1, 0, 0),
        (4, 2, 0, 0),
        (6, 2, 2, 0),
        (7, 1, 0, 1),
        (9, 2, 0, 1),
        (12, 1, 0, 2),
    ] {
        let actual = evaluator.evaluate(time(tick), None).expect("marked tick");
        assert_eq!(
            (actual.sample_index, actual.sample_local_tick, actual.cycle),
            (sample_index, local_tick, cycle),
            "tick {tick}"
        );
    }

    let mut playback = evaluator.begin_playback();
    let events = collect_events(
        playback
            .advance_to(time(12))
            .expect("multi-tick advance")
            .crossed_markers,
    );
    assert_eq!(
        event_trace(&events),
        vec![
            (
                0,
                0,
                0,
                MotionMarker::Entry,
                MarkerEventKind::LifecycleEntry
            ),
            (
                0,
                0,
                0,
                MotionMarker::Anticipation,
                MarkerEventKind::SampleEntry
            ),
            (
                2,
                0,
                1,
                MotionMarker::LoopStart,
                MarkerEventKind::SampleEntry
            ),
            (4, 0, 2, MotionMarker::LoopEnd, MarkerEventKind::SampleEntry),
            (
                7,
                1,
                1,
                MotionMarker::LoopStart,
                MarkerEventKind::SampleEntry
            ),
            (9, 1, 2, MotionMarker::LoopEnd, MarkerEventKind::SampleEntry),
            (
                12,
                2,
                1,
                MotionMarker::LoopStart,
                MarkerEventKind::SampleEntry
            ),
        ]
    );
}

#[test]
fn marked_exit_waits_for_loop_end_then_runs_tail_and_lifecycle_exit() {
    let clip = marked_clip();
    let evaluator = ClipEvaluator::new(&clip).expect("marked evaluator");
    let mut playback = evaluator.begin_playback();
    collect_events(
        playback
            .advance_to(time(7))
            .expect("second loop begins")
            .crossed_markers,
    );
    playback
        .request_exit(ExitRequest {
            requested_at_tick: 8,
        })
        .expect("exit request");

    let requested = playback.advance_to(time(8)).expect("request tick");
    assert_eq!(
        requested.evaluation.exit,
        ClipExitState::Pending {
            requested_at_tick: 8,
            safe_exit_tick: 12,
        }
    );
    assert!(collect_events(requested.crossed_markers).is_empty());
    let tail = playback.advance_to(time(12)).expect("safe loop end");
    assert_eq!(
        (
            tail.evaluation.sample_index,
            tail.evaluation.sample_local_tick,
            tail.evaluation.exit,
        ),
        (
            3,
            0,
            ClipExitState::Satisfied {
                requested_at_tick: 8,
                safe_exit_tick: 12,
            },
        )
    );
    assert_eq!(
        event_trace(&collect_events(tail.crossed_markers)),
        vec![
            (9, 1, 2, MotionMarker::LoopEnd, MarkerEventKind::SampleEntry),
            (
                12,
                1,
                3,
                MotionMarker::Settled,
                MarkerEventKind::SampleEntry
            ),
        ]
    );
    let complete = playback.advance_to(time(13)).expect("tail complete");
    assert_eq!(
        complete.evaluation.completion,
        ClipCompletionState::Completed {
            completed_at_tick: 13,
        }
    );
    assert_eq!(
        event_trace(&collect_events(complete.crossed_markers)),
        vec![(13, 1, 3, MotionMarker::Exit, MarkerEventKind::LifecycleExit,)]
    );
}

#[test]
fn marked_exit_respects_minimum_hold_at_exact_loop_boundaries() {
    for (minimum_hold_ticks, requested_at_tick, safe_exit_tick) in
        [(7, 1, 7), (8, 1, 12), (8, 12, 12)]
    {
        let mut clip = marked_clip();
        clip.minimum_hold_ticks = minimum_hold_ticks;
        let evaluator = ClipEvaluator::new(&clip).expect("marked minimum evaluator");
        let request = Some(ExitRequest { requested_at_tick });

        let expected_before = if safe_exit_tick - 1 < requested_at_tick {
            ClipExitState::NotRequested
        } else {
            ClipExitState::Pending {
                requested_at_tick,
                safe_exit_tick,
            }
        };
        assert_eq!(
            evaluator
                .evaluate(time(safe_exit_tick - 1), request)
                .expect("before marked safe boundary")
                .exit,
            expected_before
        );
        let safe = evaluator
            .evaluate(time(safe_exit_tick), request)
            .expect("exact marked safe boundary");
        assert_eq!(
            (safe.sample_index, safe.sample_local_tick),
            (3, 0),
            "tail starts at safe boundary"
        );
        assert_eq!(
            safe.exit,
            ClipExitState::Satisfied {
                requested_at_tick,
                safe_exit_tick,
            }
        );
    }
}

#[test]
fn phase_sources_are_typed_and_shadow_distance_phase_is_enabled() {
    let time_clip = clip(
        "time",
        LoopMode::Once,
        PhaseSource::Time,
        vec![sample(0, 1, vec![MotionMarker::Entry])],
        None,
    );
    let time_evaluator = ClipEvaluator::new(&time_clip).expect("time evaluator");
    assert_eq!(
        time_evaluator.evaluate(ClipPhaseInput::Distance(DistancePhaseTick(0)), None),
        Err(MotionDirectorError::PhaseSourceMismatch {
            clip_id: "time".to_string(),
            expected: PhaseSource::Time,
            provided: PhaseSource::Distance,
        })
    );

    let distance_clip = clip(
        "distance",
        LoopMode::Repeat,
        PhaseSource::Distance,
        vec![sample(0, 2, vec![MotionMarker::Entry])],
        None,
    );
    let distance_evaluator = ClipEvaluator::new(&distance_clip).expect("distance evaluator");
    let distance = distance_evaluator
        .evaluate(ClipPhaseInput::Distance(DistancePhaseTick(3)), None)
        .expect("shadow distance phase");
    assert_eq!((distance.cycle, distance.sample_local_tick), (1, 1));

    for (source, input) in [
        (PhaseSource::Wing, ClipPhaseInput::Wing(WingPhaseTick(3))),
        (
            PhaseSource::Speech,
            ClipPhaseInput::Speech(SpeechPhaseTick(3)),
        ),
    ] {
        let typed_clip = clip(
            "typed",
            LoopMode::Repeat,
            source,
            vec![sample(0, 1, vec![MotionMarker::Entry])],
            None,
        );
        let evaluator = ClipEvaluator::new(&typed_clip).expect("typed evaluator");
        assert_eq!(
            evaluator.evaluate(input, None),
            Err(MotionDirectorError::PhaseSourceNotEnabled {
                phase_source: source,
            })
        );
    }
}

#[test]
fn huge_tick_sampling_is_constant_time_and_event_history_is_lazy() {
    let huge_clip = clip(
        "huge",
        LoopMode::Repeat,
        PhaseSource::Time,
        vec![
            sample(0, 2, vec![MotionMarker::Entry, MotionMarker::LoopStart]),
            sample(1, 3, vec![MotionMarker::LoopEnd]),
        ],
        None,
    );
    let evaluator = ClipEvaluator::new(&huge_clip).expect("huge evaluator");
    let tick = u64::MAX - 1;
    let evaluation = evaluator.evaluate(time(tick), None).expect("huge tick");
    let local_cycle_tick = tick % 5;
    let expected_sample = usize::from(local_cycle_tick >= 2);
    let expected_local = if expected_sample == 0 {
        local_cycle_tick
    } else {
        local_cycle_tick - 2
    };
    assert_eq!(
        (
            evaluation.cycle,
            evaluation.sample_index,
            evaluation.sample_local_tick,
        ),
        (tick / 5, expected_sample, expected_local)
    );

    let mut playback = evaluator.begin_playback();
    let advance = playback.advance_to(time(tick)).expect("lazy huge advance");
    let first_eight = collect_events(advance.crossed_markers.take(8));
    assert_eq!(first_eight.len(), 8);

    let overflow_clip = clip(
        "exit_overflow",
        LoopMode::Repeat,
        PhaseSource::Time,
        vec![sample(0, 2, vec![MotionMarker::Entry])],
        None,
    );
    assert_eq!(
        ClipEvaluator::new(&overflow_clip)
            .expect("overflow evaluator")
            .evaluate(
                time(u64::MAX),
                Some(ExitRequest {
                    requested_at_tick: u64::MAX,
                }),
            ),
        Err(MotionDirectorError::ExitTickOverflow {
            clip_id: "exit_overflow".to_string(),
        })
    );
}

#[test]
fn deterministic_replay_has_a_fixed_hash() {
    fn replay_hash(clip: &MotionClip) -> String {
        let evaluator = ClipEvaluator::new(clip).expect("replay evaluator");
        let mut playback = evaluator.begin_playback();
        let mut hasher = Sha256::new();
        for tick in [0, 1, 4, 7, 12, 17] {
            let advance = playback.advance_to(time(tick)).expect("replay advance");
            hasher.update(format!("{:?}", advance.evaluation).as_bytes());
            for event in collect_events(advance.crossed_markers) {
                hasher.update(format!("{:?}", event).as_bytes());
            }
        }
        format!("{:x}", hasher.finalize())
    }

    let clip = marked_clip();
    let first = replay_hash(&clip);
    let second = replay_hash(&clip);
    assert_eq!(first, second);
    assert_eq!(
        first, "55195065cec3e6607e23979cd719f6c0d02152af13a5a6f67f9e39cb0cef1444",
        "freeze this hash after reviewing the exact trace"
    );
}

#[test]
fn malformed_clips_unknown_ids_and_cursor_misuse_are_typed_errors() {
    let empty = clip("empty", LoopMode::Once, PhaseSource::Time, vec![], None);
    assert_eq!(
        ClipEvaluator::new(&empty).expect_err("empty rejected"),
        MotionDirectorError::EmptyClip {
            clip_id: "empty".to_string(),
        }
    );
    let zero = clip(
        "zero",
        LoopMode::Once,
        PhaseSource::Time,
        vec![sample(0, 0, vec![])],
        None,
    );
    assert_eq!(
        ClipEvaluator::new(&zero).expect_err("zero rejected"),
        MotionDirectorError::ZeroHoldTicks {
            clip_id: "zero".to_string(),
            sample_index: 0,
        }
    );
    for invalid in [
        clip(
            "missing_bounds",
            LoopMode::MarkedSegment,
            PhaseSource::Time,
            vec![sample(0, 1, vec![]), sample(1, 1, vec![])],
            None,
        ),
        clip(
            "reversed_bounds",
            LoopMode::MarkedSegment,
            PhaseSource::Time,
            vec![sample(0, 1, vec![]), sample(1, 1, vec![])],
            Some((1, 0)),
        ),
        clip(
            "once_with_bounds",
            LoopMode::Once,
            PhaseSource::Time,
            vec![sample(0, 1, vec![]), sample(1, 1, vec![])],
            Some((0, 1)),
        ),
    ] {
        assert!(matches!(
            ClipEvaluator::new(&invalid),
            Err(MotionDirectorError::InvalidMarkedLoop { .. })
        ));
    }

    let catalog = wizard_avatar_engine::motion_catalog::shadow_motion_catalog()
        .expect("embedded motion catalog");
    let director = MotionDirector::new(&catalog.graph).expect("motion director");
    assert_eq!(
        director.clip("unknown_clip").expect_err("unknown rejected"),
        MotionDirectorError::UnknownClip("unknown_clip".to_string())
    );

    let clip = clip(
        "cursor",
        LoopMode::Repeat,
        PhaseSource::Time,
        vec![sample(0, 2, vec![MotionMarker::Entry])],
        None,
    );
    let evaluator = ClipEvaluator::new(&clip).expect("cursor evaluator");
    let mut playback = evaluator.begin_playback();
    collect_events(
        playback
            .advance_to(time(5))
            .expect("advance")
            .crossed_markers,
    );
    assert_eq!(
        playback.advance_to(time(4)).expect_err("rewind rejected"),
        MotionDirectorError::NonMonotonicAdvance {
            clip_id: "cursor".to_string(),
            previous_tick: 5,
            next_tick: 4,
        }
    );
    assert_eq!(
        playback
            .request_exit(ExitRequest {
                requested_at_tick: 4,
            })
            .expect_err("late exit rejected"),
        MotionDirectorError::LateExitRequest {
            clip_id: "cursor".to_string(),
            current_tick: 5,
            requested_tick: 4,
        }
    );
}

#[test]
fn duplicate_clip_ids_are_rejected() {
    let catalog = wizard_avatar_engine::motion_catalog::shadow_motion_catalog()
        .expect("embedded motion catalog");
    let mut graph = catalog.graph.clone();
    graph.clips.push(graph.clips[0].clone());
    assert_eq!(
        MotionDirector::new(&graph).expect_err("duplicate rejected"),
        MotionDirectorError::DuplicateClip(graph.clips[0].clip_id.clone())
    );
}

#[test]
fn reduced_motion_indirection_is_reported_but_never_silently_applied() {
    let catalog = wizard_avatar_engine::motion_catalog::shadow_motion_catalog()
        .expect("embedded motion catalog");
    let mut graph = catalog.graph.clone();
    let full_clip_id = graph.clips[0].clip_id.clone();
    let reduced_clip_id = graph.clips[1].clip_id.clone();
    graph.clips[0].reduced_motion_clip_id = Some(reduced_clip_id.clone());
    let director = MotionDirector::new(&graph).expect("motion director");

    assert_eq!(
        director
            .reduced_motion_target(&full_clip_id)
            .expect("reduced target"),
        Some(reduced_clip_id.as_str())
    );
    assert_eq!(
        director
            .evaluate(&full_clip_id, time(0), None)
            .expect("full clip remains selected")
            .clip_id,
        full_clip_id
    );
    assert_eq!(
        director
            .evaluate(&reduced_clip_id, time(0), None)
            .expect("explicit reduced clip")
            .clip_id,
        reduced_clip_id
    );
}

fn embedded_graph() -> MotionGraphV1 {
    wizard_avatar_engine::motion_catalog::shadow_motion_catalog()
        .expect("embedded motion catalog")
        .graph
        .clone()
}

fn transition_marker(marker: MotionMarker, offset_tick: u64) -> TransitionMarkerTick {
    TransitionMarkerTick {
        marker,
        cycle: 0,
        occurrence: 0,
        offset_tick,
    }
}

fn transition_timeline(start_tick: u64) -> TransitionTimeline {
    TransitionTimeline::new(
        start_tick,
        12,
        vec![
            transition_marker(MotionMarker::Entry, 0),
            transition_marker(MotionMarker::Anticipation, 2),
            transition_marker(MotionMarker::Commit, 4),
            transition_marker(MotionMarker::Impact, 6),
            transition_marker(MotionMarker::Recover, 8),
            transition_marker(MotionMarker::Exit, 10),
        ],
    )
    .expect("transition timeline")
}

fn transition_phase(timing: TransitionTiming, tick: u64) -> TransitionPhaseInput {
    match timing {
        TransitionTiming::Fixed | TransitionTiming::MarkerAligned => {
            TransitionPhaseInput::Time(SimulationTick(tick))
        }
        TransitionTiming::DistancePhase => TransitionPhaseInput::Distance(DistancePhaseTick(tick)),
        TransitionTiming::WingPhase => TransitionPhaseInput::Wing(WingPhaseTick(tick)),
        TransitionTiming::SpeechAligned => TransitionPhaseInput::Speech(SpeechPhaseTick(tick)),
    }
}

fn transition_endpoint_samples_mut(
    graph: &mut MotionGraphV1,
) -> (&mut MotionSample, &mut MotionSample) {
    let source_id = graph.edges[0].source_clip_id.clone();
    let target_id = graph.edges[0].target_clip_id.clone();
    let source_index = graph
        .clips
        .iter()
        .position(|clip| clip.clip_id == source_id)
        .expect("source clip");
    let target_index = graph
        .clips
        .iter()
        .position(|clip| clip.clip_id == target_id)
        .expect("target clip");
    assert_ne!(source_index, target_index);
    if source_index < target_index {
        let (source_side, target_side) = graph.clips.split_at_mut(target_index);
        (
            source_side[source_index]
                .samples
                .last_mut()
                .expect("source sample"),
            target_side[0].samples.first_mut().expect("target sample"),
        )
    } else {
        let (target_side, source_side) = graph.clips.split_at_mut(source_index);
        (
            source_side[0].samples.last_mut().expect("source sample"),
            target_side[target_index]
                .samples
                .first_mut()
                .expect("target sample"),
        )
    }
}

fn grounded(points: Vec<ContactPoint>) -> SupportContact {
    SupportContact {
        mode: SupportMode::Grounded,
        points,
    }
}

fn airborne() -> SupportContact {
    SupportContact {
        mode: SupportMode::Airborne,
        points: Vec::new(),
    }
}

fn graph_for_recipe(recipe_id: &str) -> MotionGraphV1 {
    let mut graph = embedded_graph();
    graph.edges[0].transition_recipe_id = recipe_id.to_string();
    let recipe = graph
        .transition_recipes
        .iter()
        .find(|recipe| recipe.recipe_id == recipe_id)
        .expect("named recipe")
        .clone();
    let (source, target) = transition_endpoint_samples_mut(&mut graph);
    source.support = grounded(vec![ContactPoint::LeftFoot]);
    target.support = grounded(vec![ContactPoint::LeftFoot]);
    source.root_offset = [0, 0];
    target.root_offset = [0, 0];
    source.secondary_profile_id = "source_secondary".to_string();
    target.secondary_profile_id = "target_secondary".to_string();
    match recipe.contact_policy {
        ContactPolicy::ReleaseThenAirborne => target.support = airborne(),
        ContactPolicy::AirborneThenLand => {
            source.support = airborne();
            target.support = grounded(vec![ContactPoint::RightFoot]);
        }
        ContactPolicy::BraceTransfer => {
            target.support = grounded(vec![ContactPoint::StaffTip]);
        }
        ContactPolicy::Preserve | ContactPolicy::TransferAtMarker | ContactPolicy::None => {}
    }
    graph
}

fn coherent_recipe_mut(graph: &mut MotionGraphV1) -> &mut motion_graph::TransitionRecipe {
    graph
        .transition_recipes
        .iter_mut()
        .find(|recipe| recipe.recipe_id == "coherent_handoff")
        .expect("coherent recipe")
}

#[test]
fn all_embedded_edges_resolve_exactly_one_authored_recipe() {
    let graph = embedded_graph();
    assert_eq!(graph.edges.len(), 43);
    let director = TransitionDirector::new(&graph).expect("transition director");
    let mut resolved_ids = Vec::new();
    for edge in &graph.edges {
        let resolved = director.resolve_edge(&edge.edge_id).expect("resolved edge");
        assert_eq!(resolved.edge.edge_id, edge.edge_id);
        assert_eq!(resolved.fallback_depth, 0);
        resolved_ids.push((
            resolved.edge.edge_id.as_str(),
            resolved.recipe.recipe_id.as_str(),
        ));
    }
    assert_eq!(resolved_ids.len(), 43);
    assert_eq!(
        resolved_ids
            .iter()
            .filter(|(_, recipe_id)| *recipe_id == "coherent_handoff")
            .count(),
        30
    );
    assert_eq!(
        resolved_ids
            .iter()
            .filter(|(_, recipe_id)| *recipe_id == "contact_sync")
            .count(),
        13
    );
}

#[test]
fn all_eight_recipes_and_five_timing_modes_have_exact_tick_lifecycle() {
    let recipe_ids = [
        "coherent_handoff",
        "contact_sync",
        "anticipation_action_recover",
        "airborne_arc",
        "brace_transfer",
        "face_coarticulation",
        "secondary_settle",
        "reduced_motion_handoff",
    ];
    let mut timings = Vec::new();
    for recipe_id in recipe_ids {
        let graph = graph_for_recipe(recipe_id);
        let director = TransitionDirector::new(&graph).expect("transition director");
        let resolved = director.resolve_edge("edge_001").expect("recipe edge");
        timings.push(resolved.recipe.timing);
        let timeline = transition_timeline(100);
        let trace = [
            (100, TransitionLifecycleState::Pending),
            (103, TransitionLifecycleState::Pending),
            (104, TransitionLifecycleState::Handoff),
            (
                105,
                TransitionLifecycleState::Recovery {
                    interrupted: false,
                    recovery_policy: None,
                },
            ),
            (
                112,
                TransitionLifecycleState::Completed {
                    completed_at_tick: 112,
                },
            ),
        ];
        for (tick, expected_state) in trace {
            let evaluation = director
                .evaluate(
                    "edge_001",
                    &timeline,
                    transition_phase(resolved.recipe.timing, tick),
                    None,
                )
                .expect("exact transition tick");
            assert_eq!(evaluation.recipe_id, recipe_id);
            assert_eq!(evaluation.state, expected_state, "{recipe_id} tick {tick}");
        }
        assert_eq!(
            director
                .evaluate(
                    "edge_001",
                    &timeline,
                    transition_phase(resolved.recipe.timing, 104),
                    None,
                )
                .expect("handoff marker")
                .active_markers,
            vec![transition_marker(MotionMarker::Commit, 4)]
        );
    }
    timings.sort_by_key(|timing| format!("{timing:?}"));
    timings.dedup();
    assert_eq!(timings.len(), 5);
}

#[test]
fn timing_sources_are_typed_and_never_silently_substituted() {
    for recipe_id in [
        "coherent_handoff",
        "contact_sync",
        "airborne_arc",
        "face_coarticulation",
    ] {
        let graph = graph_for_recipe(recipe_id);
        let director = TransitionDirector::new(&graph).expect("transition director");
        let recipe = director.resolve_edge("edge_001").expect("edge").recipe;
        let wrong = match recipe.timing {
            TransitionTiming::Fixed | TransitionTiming::MarkerAligned => {
                TransitionPhaseInput::Distance(DistancePhaseTick(100))
            }
            TransitionTiming::DistancePhase
            | TransitionTiming::WingPhase
            | TransitionTiming::SpeechAligned => TransitionPhaseInput::Time(SimulationTick(100)),
        };
        assert!(matches!(
            director.evaluate("edge_001", &transition_timeline(100), wrong, None),
            Err(MotionDirectorError::TransitionPhaseSourceMismatch { .. })
        ));
    }
}

#[test]
fn all_contact_and_root_policies_preserve_endpoint_coherence() {
    for policy in [
        ContactPolicy::Preserve,
        ContactPolicy::TransferAtMarker,
        ContactPolicy::ReleaseThenAirborne,
        ContactPolicy::AirborneThenLand,
        ContactPolicy::BraceTransfer,
        ContactPolicy::None,
    ] {
        let mut graph = graph_for_recipe("coherent_handoff");
        coherent_recipe_mut(&mut graph).contact_policy = policy;
        let (source, target) = transition_endpoint_samples_mut(&mut graph);
        source.support = grounded(vec![ContactPoint::LeftFoot]);
        target.support = grounded(vec![ContactPoint::LeftFoot]);
        match policy {
            ContactPolicy::TransferAtMarker => {
                target.support = grounded(vec![ContactPoint::RightFoot]);
            }
            ContactPolicy::ReleaseThenAirborne => target.support = airborne(),
            ContactPolicy::AirborneThenLand => {
                source.support = airborne();
                target.support = grounded(vec![ContactPoint::RightFoot]);
            }
            ContactPolicy::BraceTransfer => {
                target.support = grounded(vec![ContactPoint::StaffTip]);
            }
            ContactPolicy::Preserve | ContactPolicy::None => {}
        }
        let director = TransitionDirector::new(&graph).expect("contact director");
        let at_handoff = director
            .evaluate(
                "edge_001",
                &transition_timeline(100),
                TransitionPhaseInput::Time(SimulationTick(104)),
                None,
            )
            .expect("contact handoff");
        match policy {
            ContactPolicy::Preserve => assert!(matches!(
                at_handoff.contact,
                TransitionContactState::Source(_)
            )),
            ContactPolicy::TransferAtMarker | ContactPolicy::AirborneThenLand => {
                assert!(matches!(
                    at_handoff.contact,
                    TransitionContactState::Target(_)
                ));
            }
            ContactPolicy::ReleaseThenAirborne => {
                assert_eq!(at_handoff.contact, TransitionContactState::Airborne);
            }
            ContactPolicy::BraceTransfer => assert_eq!(
                at_handoff.contact,
                TransitionContactState::Braced(vec![
                    ContactPoint::LeftFoot,
                    ContactPoint::StaffTip
                ])
            ),
            ContactPolicy::None => assert_eq!(at_handoff.contact, TransitionContactState::None),
        }
        if policy == ContactPolicy::BraceTransfer {
            assert!(matches!(
                director
                    .evaluate(
                        "edge_001",
                        &transition_timeline(100),
                        TransitionPhaseInput::Time(SimulationTick(105)),
                        None,
                    )
                    .expect("brace completes transfer")
                    .contact,
                TransitionContactState::Target(_)
            ));
        }
    }

    for policy in [
        RootPolicy::Preserve,
        RootPolicy::FollowTarget,
        RootPolicy::AuthoredOffset,
        RootPolicy::ContactLocked,
    ] {
        let mut graph = graph_for_recipe("coherent_handoff");
        {
            let recipe = coherent_recipe_mut(&mut graph);
            recipe.contact_policy = ContactPolicy::None;
            recipe.root_policy = policy;
        }
        let (source, target) = transition_endpoint_samples_mut(&mut graph);
        source.root_offset = [1, 2];
        target.root_offset = if policy == RootPolicy::Preserve {
            [1, 2]
        } else {
            [3, 4]
        };
        source.support = grounded(vec![ContactPoint::LeftFoot]);
        let director = TransitionDirector::new(&graph).expect("root director");
        let handoff = director
            .evaluate(
                "edge_001",
                &transition_timeline(100),
                TransitionPhaseInput::Time(SimulationTick(104)),
                None,
            )
            .expect("root handoff")
            .root;
        match policy {
            RootPolicy::Preserve => assert_eq!(handoff, TransitionRootState::Source([1, 2])),
            RootPolicy::FollowTarget => assert_eq!(handoff, TransitionRootState::Target([3, 4])),
            RootPolicy::AuthoredOffset => {
                assert_eq!(handoff, TransitionRootState::Authored([3, 4]));
            }
            RootPolicy::ContactLocked => {
                assert_eq!(handoff, TransitionRootState::ContactLocked([1, 2]));
            }
        }
    }
}

#[test]
fn all_region_and_secondary_policies_are_explicit() {
    for policy in [
        RegionPolicy::PreserveUnowned,
        RegionPolicy::ReplaceOwned,
        RegionPolicy::FaceOnly,
        RegionPolicy::ReducedMotion,
    ] {
        let mut graph = graph_for_recipe("coherent_handoff");
        coherent_recipe_mut(&mut graph).region_policy = policy;
        let director = TransitionDirector::new(&graph).expect("region director");
        let evaluation = director
            .evaluate(
                "edge_001",
                &transition_timeline(100),
                TransitionPhaseInput::Time(SimulationTick(104)),
                None,
            )
            .expect("region policy");
        assert_eq!(evaluation.regions.policy, policy);
        assert!(!evaluation.regions.target_owned_regions.is_empty());
    }

    for policy in [
        SecondaryPolicy::Preserve,
        SecondaryPolicy::Settle,
        SecondaryPolicy::ResetAtMarker,
        SecondaryPolicy::Suppress,
    ] {
        let mut graph = graph_for_recipe("coherent_handoff");
        coherent_recipe_mut(&mut graph).secondary_policy = policy;
        let director = TransitionDirector::new(&graph).expect("secondary director");
        let handoff = director
            .evaluate(
                "edge_001",
                &transition_timeline(100),
                TransitionPhaseInput::Time(SimulationTick(104)),
                None,
            )
            .expect("secondary handoff")
            .secondary;
        match policy {
            SecondaryPolicy::Preserve => assert_eq!(
                handoff,
                TransitionSecondaryState::Source("source_secondary".to_string())
            ),
            SecondaryPolicy::Settle => {
                assert!(matches!(handoff, TransitionSecondaryState::Settling { .. }))
            }
            SecondaryPolicy::ResetAtMarker => assert_eq!(
                handoff,
                TransitionSecondaryState::Target("target_secondary".to_string())
            ),
            SecondaryPolicy::Suppress => {
                assert_eq!(handoff, TransitionSecondaryState::Suppressed);
            }
        }
    }
}

#[test]
fn interrupt_windows_are_half_open_with_authored_overlap_precedence() {
    let policies = [
        (InterruptPolicy::Immediate, 102),
        (InterruptPolicy::AtSafeMarker, 110),
        (InterruptPolicy::AfterCommit, 104),
        (InterruptPolicy::AfterImpact, 106),
        (InterruptPolicy::UninterruptibleUntilRecovery, 110),
    ];
    let recoveries = [
        RecoveryPolicy::RestorePrevious,
        RecoveryPolicy::SettleToIdle,
        RecoveryPolicy::SettleToListening,
        RecoveryPolicy::ContinueTarget,
        RecoveryPolicy::EmergencyHome,
    ];
    for ((policy, expected_before), recovery) in policies.into_iter().zip(recoveries) {
        let mut graph = graph_for_recipe("coherent_handoff");
        coherent_recipe_mut(&mut graph).interrupt_windows = vec![InterruptWindow {
            start_marker: MotionMarker::Anticipation,
            end_marker: MotionMarker::Exit,
            interrupt_policy: policy,
            recovery_policy: recovery,
        }];
        let director = TransitionDirector::new(&graph).expect("interrupt director");
        let timeline = transition_timeline(100);
        let before = director
            .evaluate(
                "edge_001",
                &timeline,
                TransitionPhaseInput::Time(SimulationTick(101)),
                Some(TransitionInterruptRequest {
                    requested_at_tick: 101,
                }),
            )
            .expect("before window")
            .interrupt
            .expect("interrupt decision");
        assert_eq!(
            before.position,
            TransitionInterruptPosition::BeforeWindow { window_index: 0 }
        );
        assert_eq!(before.recovery_at_tick, expected_before);
        assert_eq!(before.recovery_policy, recovery);

        for request_tick in [102, 109] {
            assert_eq!(
                director
                    .evaluate(
                        "edge_001",
                        &timeline,
                        TransitionPhaseInput::Time(SimulationTick(request_tick)),
                        Some(TransitionInterruptRequest {
                            requested_at_tick: request_tick,
                        }),
                    )
                    .expect("inside half-open window")
                    .interrupt
                    .expect("inside decision")
                    .position,
                TransitionInterruptPosition::InsideWindow { window_index: 0 }
            );
        }
        let exact_end = director
            .evaluate(
                "edge_001",
                &timeline,
                TransitionPhaseInput::Time(SimulationTick(110)),
                Some(TransitionInterruptRequest {
                    requested_at_tick: 110,
                }),
            )
            .expect("exclusive end")
            .interrupt
            .expect("after decision");
        assert_eq!(
            exact_end.position,
            TransitionInterruptPosition::AfterWindows
        );
        assert_eq!(exact_end.recovery_at_tick, 110);
    }

    let mut graph = graph_for_recipe("coherent_handoff");
    coherent_recipe_mut(&mut graph).interrupt_windows = vec![
        InterruptWindow {
            start_marker: MotionMarker::Entry,
            end_marker: MotionMarker::Recover,
            interrupt_policy: InterruptPolicy::AfterCommit,
            recovery_policy: RecoveryPolicy::RestorePrevious,
        },
        InterruptWindow {
            start_marker: MotionMarker::Anticipation,
            end_marker: MotionMarker::Exit,
            interrupt_policy: InterruptPolicy::Immediate,
            recovery_policy: RecoveryPolicy::EmergencyHome,
        },
    ];
    let director = TransitionDirector::new(&graph).expect("overlap director");
    let overlap = director
        .evaluate(
            "edge_001",
            &transition_timeline(100),
            TransitionPhaseInput::Time(SimulationTick(105)),
            Some(TransitionInterruptRequest {
                requested_at_tick: 105,
            }),
        )
        .expect("overlap")
        .interrupt
        .expect("overlap decision");
    assert_eq!(
        overlap.position,
        TransitionInterruptPosition::InsideWindow { window_index: 0 }
    );
    assert_eq!(overlap.recovery_policy, RecoveryPolicy::RestorePrevious);
}

#[test]
fn fallback_activation_is_explicit_and_bad_chains_fail_closed() {
    let mut graph = graph_for_recipe("contact_sync");
    graph
        .transition_recipes
        .iter_mut()
        .find(|recipe| recipe.recipe_id == "contact_sync")
        .expect("contact recipe")
        .source_families = vec![ClipFamily::Flight];
    let director = TransitionDirector::new(&graph).expect("fallback director");
    let resolved = director.resolve_edge("edge_001").expect("fallback edge");
    assert_eq!(resolved.recipe.recipe_id, "coherent_handoff");
    assert_eq!(resolved.fallback_depth, 1);

    for failure in ["unknown", "self", "cycle"] {
        let mut graph = graph_for_recipe("contact_sync");
        match failure {
            "unknown" => {
                graph
                    .transition_recipes
                    .iter_mut()
                    .find(|recipe| recipe.recipe_id == "contact_sync")
                    .expect("recipe")
                    .fallback_recipe_id = Some("not_a_recipe".to_string());
            }
            "self" => {
                graph
                    .transition_recipes
                    .iter_mut()
                    .find(|recipe| recipe.recipe_id == "contact_sync")
                    .expect("recipe")
                    .fallback_recipe_id = Some("contact_sync".to_string());
            }
            "cycle" => {
                graph
                    .transition_recipes
                    .iter_mut()
                    .find(|recipe| recipe.recipe_id == "coherent_handoff")
                    .expect("recipe")
                    .fallback_recipe_id = Some("contact_sync".to_string());
            }
            _ => unreachable!(),
        }
        assert!(TransitionDirector::new(&graph).is_err(), "{failure}");
    }
}

#[test]
fn edge_resolution_and_malformed_graph_failures_are_typed() {
    let graph = graph_for_recipe("coherent_handoff");
    let director = TransitionDirector::new(&graph).expect("transition director");
    assert_eq!(
        director
            .resolve_edge("missing_edge")
            .expect_err("unknown edge"),
        MotionDirectorError::UnknownMotionEdge("missing_edge".to_string())
    );
    assert!(matches!(
        director.resolve_between("state_idle", "not_a_target"),
        Err(MotionDirectorError::MissingDirectedEdge { .. })
    ));
    let timeline = transition_timeline(100);
    assert_eq!(timeline.start_tick(), 100);
    assert_eq!(timeline.duration_ticks(), 12);
    assert_eq!(timeline.completion_tick(), 112);

    let mut ambiguous = graph.clone();
    let mut duplicate_direction = ambiguous.edges[0].clone();
    duplicate_direction.edge_id = "edge_ambiguous".to_string();
    ambiguous.edges.push(duplicate_direction);
    let ambiguous_director =
        TransitionDirector::new(&ambiguous).expect("individual edge IDs remain resolvable");
    assert!(matches!(
        ambiguous_director.resolve_between("state_idle", "state_listening"),
        Err(MotionDirectorError::AmbiguousDirectedEdge { edge_ids, .. }) if edge_ids.len() == 2
    ));

    let mut duplicate_edge = graph.clone();
    duplicate_edge.edges.push(duplicate_edge.edges[0].clone());
    assert!(matches!(
        TransitionDirector::new(&duplicate_edge),
        Err(MotionDirectorError::DuplicateMotionEdge(_))
    ));

    let mut duplicate_recipe = graph.clone();
    duplicate_recipe
        .transition_recipes
        .push(duplicate_recipe.transition_recipes[0].clone());
    assert!(matches!(
        TransitionDirector::new(&duplicate_recipe),
        Err(MotionDirectorError::DuplicateTransitionRecipe(_))
    ));

    let mut missing_clip = graph.clone();
    missing_clip.edges[0].source_clip_id = "missing_clip".to_string();
    assert!(matches!(
        TransitionDirector::new(&missing_clip),
        Err(MotionDirectorError::MissingEdgeClip { role: "source", .. })
    ));

    let mut missing_recipe = graph.clone();
    missing_recipe.edges[0].transition_recipe_id = "missing_recipe".to_string();
    assert!(matches!(
        TransitionDirector::new(&missing_recipe),
        Err(MotionDirectorError::MissingTransitionRecipe { .. })
    ));

    let mut no_admission = graph;
    let source_family = no_admission
        .clips
        .iter()
        .find(|clip| clip.clip_id == no_admission.edges[0].source_clip_id)
        .expect("source clip")
        .family;
    let target_family = no_admission
        .clips
        .iter()
        .find(|clip| clip.clip_id == no_admission.edges[0].target_clip_id)
        .expect("target clip")
        .family;
    let recipe = coherent_recipe_mut(&mut no_admission);
    recipe.source_families = vec![ClipFamily::Flight];
    recipe.fallback_recipe_id = None;
    assert!(matches!(
        TransitionDirector::new(&no_admission),
        Err(MotionDirectorError::TransitionFamilyNotAdmitted {
            source_family: actual_source,
            target_family: actual_target,
            ..
        }) if actual_source == source_family && actual_target == target_family
    ));
}

#[test]
fn missing_repeated_and_duplicate_marker_occurrences_are_typed_errors() {
    let graph = graph_for_recipe("coherent_handoff");
    let director = TransitionDirector::new(&graph).expect("transition director");
    let missing = TransitionTimeline::new(
        100,
        12,
        vec![
            transition_marker(MotionMarker::Entry, 0),
            transition_marker(MotionMarker::Exit, 10),
        ],
    )
    .expect("missing timeline builds");
    assert!(matches!(
        director.evaluate(
            "edge_001",
            &missing,
            TransitionPhaseInput::Time(SimulationTick(100)),
            None
        ),
        Err(MotionDirectorError::MissingTransitionMarker {
            marker: MotionMarker::Commit,
            ..
        })
    ));

    let mut repeated_markers = transition_timeline(100).markers().to_vec();
    repeated_markers.push(TransitionMarkerTick {
        marker: MotionMarker::Commit,
        cycle: 1,
        occurrence: 1,
        offset_tick: 7,
    });
    let repeated = TransitionTimeline::new(100, 12, repeated_markers)
        .expect("occurrence identities are distinct");
    assert!(matches!(
        director.evaluate(
            "edge_001",
            &repeated,
            TransitionPhaseInput::Time(SimulationTick(100)),
            None
        ),
        Err(MotionDirectorError::AmbiguousTransitionMarker {
            marker: MotionMarker::Commit
        })
    ));

    let duplicate = vec![
        transition_marker(MotionMarker::Entry, 0),
        transition_marker(MotionMarker::Entry, 1),
    ];
    assert!(matches!(
        TransitionTimeline::new(100, 12, duplicate),
        Err(MotionDirectorError::DuplicateTransitionMarkerIdentity {
            marker: MotionMarker::Entry,
            cycle: 0,
            occurrence: 0
        })
    ));
}

#[test]
fn deterministic_duration_integer_extremes_and_huge_ticks_are_checked() {
    let graph = graph_for_recipe("coherent_handoff");
    let recipe = graph
        .transition_recipes
        .iter()
        .find(|recipe| recipe.recipe_id == "coherent_handoff")
        .expect("recipe");
    assert_eq!(select_transition_duration(recipe, 0).expect("minimum"), 1);
    assert_eq!(select_transition_duration(recipe, 17).expect("maximum"), 18);
    assert_eq!(select_transition_duration(recipe, 18).expect("wrap"), 1);
    let mut maximum = recipe.clone();
    maximum.duration_ticks = TickRange {
        min: u16::MAX,
        max: u16::MAX,
    };
    assert_eq!(
        select_transition_duration(&maximum, u64::MAX).expect("u16 maximum"),
        u16::MAX
    );
    maximum.duration_ticks = TickRange {
        min: u16::MAX,
        max: u16::MAX - 1,
    };
    assert!(matches!(
        select_transition_duration(&maximum, 0),
        Err(MotionDirectorError::MalformedTransitionRecipe { .. })
    ));

    assert_eq!(
        TransitionTimeline::new(u64::MAX, 1, Vec::new()),
        Err(MotionDirectorError::TransitionTickOverflow)
    );
    assert!(matches!(
        TransitionTimeline::new(0, 12, vec![transition_marker(MotionMarker::Commit, 13)]),
        Err(MotionDirectorError::TransitionMarkerOutOfRange { .. })
    ));

    let director = TransitionDirector::new(&graph).expect("transition director");
    let huge = director
        .evaluate(
            "edge_001",
            &transition_timeline(0),
            TransitionPhaseInput::Time(SimulationTick(u64::MAX)),
            None,
        )
        .expect("constant-time huge tick");
    assert_eq!(
        huge.state,
        TransitionLifecycleState::Completed {
            completed_at_tick: 12
        }
    );
}

#[test]
fn transition_replay_hash_is_repeatable_and_shadow_only() {
    fn replay_hash() -> String {
        let graph = graph_for_recipe("anticipation_action_recover");
        let director = TransitionDirector::new(&graph).expect("transition director");
        let timeline = transition_timeline(100);
        let mut hasher = Sha256::new();
        for tick in [100, 102, 104, 105, 109, 110, 112, u64::MAX] {
            let evaluation = director
                .evaluate(
                    "edge_001",
                    &timeline,
                    TransitionPhaseInput::Time(SimulationTick(tick)),
                    Some(TransitionInterruptRequest {
                        requested_at_tick: 103,
                    }),
                )
                .expect("replay transition");
            hasher.update(format!("{evaluation:?}").as_bytes());
        }
        format!("{:x}", hasher.finalize())
    }

    let first = replay_hash();
    assert_eq!(first, replay_hash());
    assert_eq!(
        first, "58d1834517ccc6a86463fee5e660797e34e387db82c43bb5a99273d3e82d7591",
        "freeze after reviewing the exact transition trace"
    );

    let source = include_str!("../src/motion_director.rs");
    for forbidden in [
        "crate::controller",
        "crate::renderer",
        ".png",
        "python",
        "cell_dissolve",
    ] {
        assert!(!source.contains(forbidden), "forbidden wiring {forbidden}");
    }
}
