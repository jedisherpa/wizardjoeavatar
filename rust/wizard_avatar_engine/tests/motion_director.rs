mod motion_graph {
    pub use wizard_avatar_engine::motion_graph::*;
}

#[path = "../src/motion_director.rs"]
mod motion_director;

use motion_director::{
    ClipCompletionState, ClipEvaluator, ClipExitState, ClipPhaseInput, DistancePhaseTick,
    ExitRequest, MarkerEvent, MarkerEventKind, MotionDirector, MotionDirectorError, SimulationTick,
    SpeechPhaseTick, WingPhaseTick,
};
use motion_graph::{
    ChannelMask, ClipFamily, ContactPoint, InterruptPolicy, LoopMode, MotionClip, MotionMarker,
    MotionSample, PerformanceRegion, PhaseSource, SupportContact, SupportMode,
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
fn phase_sources_are_typed_but_only_time_is_enabled() {
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

    for (source, input) in [
        (
            PhaseSource::Distance,
            ClipPhaseInput::Distance(DistancePhaseTick(3)),
        ),
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
