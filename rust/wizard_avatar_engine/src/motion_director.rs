use crate::motion_graph::{
    ContactPoint, ContactPolicy, InterruptPolicy, LoopMode, MotionClip, MotionEdge, MotionGraphV1,
    MotionMarker, PerformanceRegion, PhaseSource, RecoveryPolicy, RegionPolicy, RootPolicy,
    SecondaryPolicy, SupportContact, SupportMode, TransitionRecipe,
};
use std::collections::{BTreeMap, BTreeSet, VecDeque};
use thiserror::Error;

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct SimulationTick(pub u64);

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct DistancePhaseTick(pub u64);

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct WingPhaseTick(pub u64);

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct SpeechPhaseTick(pub u64);

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub enum ClipPhaseInput {
    Time(SimulationTick),
    Distance(DistancePhaseTick),
    Wing(WingPhaseTick),
    Speech(SpeechPhaseTick),
}

impl ClipPhaseInput {
    #[must_use]
    pub const fn source(self) -> PhaseSource {
        match self {
            Self::Time(_) => PhaseSource::Time,
            Self::Distance(_) => PhaseSource::Distance,
            Self::Wing(_) => PhaseSource::Wing,
            Self::Speech(_) => PhaseSource::Speech,
        }
    }

    #[must_use]
    pub const fn tick(self) -> u64 {
        match self {
            Self::Time(tick) => tick.0,
            Self::Distance(tick) => tick.0,
            Self::Wing(tick) => tick.0,
            Self::Speech(tick) => tick.0,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExitRequest {
    pub requested_at_tick: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ClipCompletionState {
    Playing,
    Completed { completed_at_tick: u64 },
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ClipExitState {
    NotRequested,
    Pending {
        requested_at_tick: u64,
        safe_exit_tick: u64,
    },
    Satisfied {
        requested_at_tick: u64,
        safe_exit_tick: u64,
    },
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ClipEvaluation<'a> {
    pub clip_id: &'a str,
    pub pose_id: &'a str,
    pub phase_source: PhaseSource,
    pub phase_tick: u64,
    pub cycle: u64,
    pub sample_index: usize,
    pub sample_local_tick: u64,
    pub sample_started_at_tick: u64,
    pub active_markers: &'a [MotionMarker],
    pub completion: ClipCompletionState,
    pub exit: ClipExitState,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MarkerEventKind {
    LifecycleEntry,
    SampleEntry,
    LifecycleExit,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MarkerEvent {
    pub tick: u64,
    pub cycle: u64,
    pub sample_index: usize,
    pub marker: MotionMarker,
    pub kind: MarkerEventKind,
}

#[derive(Clone, Debug, Error, Eq, PartialEq)]
pub enum MotionDirectorError {
    #[error("motion clip {0} does not exist")]
    UnknownClip(String),
    #[error("motion graph contains duplicate clip ID {0}")]
    DuplicateClip(String),
    #[error("motion clip {clip_id} has no samples")]
    EmptyClip { clip_id: String },
    #[error("motion clip {clip_id} sample {sample_index} has zero hold ticks")]
    ZeroHoldTicks {
        clip_id: String,
        sample_index: usize,
    },
    #[error("motion clip {clip_id} duration overflowed integer ticks")]
    DurationOverflow { clip_id: String },
    #[error("motion clip {clip_id} has invalid marked loop bounds")]
    InvalidMarkedLoop { clip_id: String },
    #[error("motion clip {clip_id} expects {expected:?} phase ticks, but received {provided:?}")]
    PhaseSourceMismatch {
        clip_id: String,
        expected: PhaseSource,
        provided: PhaseSource,
    },
    #[error("{phase_source:?} phase evaluation is typed but not active in RCHAT-ANIM-040")]
    PhaseSourceNotEnabled { phase_source: PhaseSource },
    #[error("motion clip {clip_id} exit scheduling overflowed integer ticks")]
    ExitTickOverflow { clip_id: String },
    #[error(
        "motion clip {clip_id} cannot advance backward from tick {previous_tick} to {next_tick}"
    )]
    NonMonotonicAdvance {
        clip_id: String,
        previous_tick: u64,
        next_tick: u64,
    },
    #[error(
        "motion clip {clip_id} already has exit request tick {existing_tick}, not {requested_tick}"
    )]
    ConflictingExitRequest {
        clip_id: String,
        existing_tick: u64,
        requested_tick: u64,
    },
    #[error(
        "motion clip {clip_id} exit request tick {requested_tick} precedes playback tick {current_tick}"
    )]
    LateExitRequest {
        clip_id: String,
        current_tick: u64,
        requested_tick: u64,
    },
    #[error("motion graph contains duplicate transition recipe ID {0}")]
    DuplicateTransitionRecipe(String),
    #[error("motion graph contains duplicate edge ID {0}")]
    DuplicateMotionEdge(String),
    #[error("motion edge {0} does not exist")]
    UnknownMotionEdge(String),
    #[error("no motion edge exists from {source_clip_id} to {target_clip_id}")]
    MissingDirectedEdge {
        source_clip_id: String,
        target_clip_id: String,
    },
    #[error("multiple motion edges exist from {source_clip_id} to {target_clip_id}: {edge_ids:?}")]
    AmbiguousDirectedEdge {
        source_clip_id: String,
        target_clip_id: String,
        edge_ids: Vec<String>,
    },
    #[error("motion edge {edge_id} references missing {role} clip {clip_id}")]
    MissingEdgeClip {
        edge_id: String,
        role: &'static str,
        clip_id: String,
    },
    #[error("motion edge {edge_id} references missing transition recipe {recipe_id}")]
    MissingTransitionRecipe { edge_id: String, recipe_id: String },
    #[error("transition recipe {recipe_id} has invalid contract: {reason}")]
    MalformedTransitionRecipe { recipe_id: String, reason: String },
    #[error("transition recipe fallback cycle begins at {recipe_id}")]
    TransitionFallbackCycle { recipe_id: String },
    #[error(
        "transition recipe chain for edge {edge_id} does not admit {source_family:?} -> {target_family:?}"
    )]
    TransitionFamilyNotAdmitted {
        edge_id: String,
        source_family: crate::motion_graph::ClipFamily,
        target_family: crate::motion_graph::ClipFamily,
    },
    #[error("transition timeline has zero duration")]
    ZeroTransitionDuration,
    #[error("transition timeline completion overflows integer ticks")]
    TransitionTickOverflow,
    #[error("transition marker {marker:?} occurs more than once")]
    AmbiguousTransitionMarker { marker: MotionMarker },
    #[error("transition marker identity {marker:?}/{cycle}/{occurrence} occurs more than once")]
    DuplicateTransitionMarkerIdentity {
        marker: MotionMarker,
        cycle: u64,
        occurrence: u32,
    },
    #[error("transition marker {marker:?} at offset {tick} exceeds duration {duration}")]
    TransitionMarkerOutOfRange {
        marker: MotionMarker,
        tick: u64,
        duration: u64,
    },
    #[error("transition recipe {recipe_id} requires marker {marker:?}")]
    MissingTransitionMarker {
        recipe_id: String,
        marker: MotionMarker,
    },
    #[error("transition recipe {recipe_id} duration {duration} is outside [{minimum}, {maximum}]")]
    TransitionDurationOutOfRange {
        recipe_id: String,
        duration: u64,
        minimum: u16,
        maximum: u16,
    },
    #[error("transition recipe {recipe_id} has an invalid authored marker interval")]
    InvalidTransitionMarkerInterval { recipe_id: String },
    #[error("transition tick {current_tick} precedes start tick {start_tick}")]
    TransitionTickBeforeStart { current_tick: u64, start_tick: u64 },
    #[error("transition interrupt tick {requested_tick} precedes start tick {start_tick}")]
    TransitionInterruptBeforeStart {
        requested_tick: u64,
        start_tick: u64,
    },
    #[error("transition recipe {recipe_id} cannot preserve contact between its endpoint samples")]
    ContactCoherenceViolation { recipe_id: String },
    #[error(
        "transition recipe {recipe_id} cannot preserve root offset between its endpoint samples"
    )]
    RootCoherenceViolation { recipe_id: String },
    #[error("transition recipe {recipe_id} has incompatible endpoint contact modes")]
    ContactPolicyViolation { recipe_id: String },
    #[error(
        "transition recipe {recipe_id} expects {expected:?} phase ticks, but received {provided:?}"
    )]
    TransitionPhaseSourceMismatch {
        recipe_id: String,
        expected: PhaseSource,
        provided: PhaseSource,
    },
}

#[derive(Clone, Debug)]
struct ClipLayout {
    sample_starts: Vec<u64>,
    total_duration: u64,
    loop_end_sample: Option<usize>,
    prefix_duration: u64,
    loop_duration: u64,
    tail_duration: u64,
}

impl ClipLayout {
    fn build(clip: &MotionClip) -> Result<Self, MotionDirectorError> {
        if clip.samples.is_empty() {
            return Err(MotionDirectorError::EmptyClip {
                clip_id: clip.clip_id.clone(),
            });
        }

        let mut sample_starts = Vec::with_capacity(clip.samples.len() + 1);
        sample_starts.push(0);
        let mut total_duration = 0_u64;
        for (sample_index, sample) in clip.samples.iter().enumerate() {
            if sample.hold_ticks == 0 {
                return Err(MotionDirectorError::ZeroHoldTicks {
                    clip_id: clip.clip_id.clone(),
                    sample_index,
                });
            }
            total_duration =
                checked_add_duration(total_duration, u64::from(sample.hold_ticks), &clip.clip_id)?;
            sample_starts.push(total_duration);
        }

        let (loop_end_sample, prefix_duration, loop_duration, tail_duration) = match clip.loop_mode
        {
            LoopMode::Once | LoopMode::Repeat => {
                if clip.loop_start_sample.is_some() || clip.loop_end_sample.is_some() {
                    return Err(MotionDirectorError::InvalidMarkedLoop {
                        clip_id: clip.clip_id.clone(),
                    });
                }
                (None, 0, total_duration, 0)
            }
            LoopMode::MarkedSegment => {
                let (Some(start), Some(end)) = (clip.loop_start_sample, clip.loop_end_sample)
                else {
                    return Err(MotionDirectorError::InvalidMarkedLoop {
                        clip_id: clip.clip_id.clone(),
                    });
                };
                if start >= end || end >= clip.samples.len() {
                    return Err(MotionDirectorError::InvalidMarkedLoop {
                        clip_id: clip.clip_id.clone(),
                    });
                }
                let prefix = sample_starts[start];
                let loop_end = sample_starts[end + 1];
                (
                    Some(end),
                    prefix,
                    loop_end - prefix,
                    total_duration - loop_end,
                )
            }
        };

        Ok(Self {
            sample_starts,
            total_duration,
            loop_end_sample,
            prefix_duration,
            loop_duration,
            tail_duration,
        })
    }

    fn sample_for_offset(&self, offset: u64) -> (usize, u64) {
        let sample_index = self
            .sample_starts
            .partition_point(|sample_start| *sample_start <= offset)
            .saturating_sub(1)
            .min(self.sample_starts.len() - 2);
        (sample_index, offset - self.sample_starts[sample_index])
    }
}

#[derive(Clone, Debug)]
pub struct ClipEvaluator<'a> {
    clip: &'a MotionClip,
    layout: ClipLayout,
}

impl<'a> ClipEvaluator<'a> {
    pub fn new(clip: &'a MotionClip) -> Result<Self, MotionDirectorError> {
        Ok(Self {
            clip,
            layout: ClipLayout::build(clip)?,
        })
    }

    #[must_use]
    pub fn clip(&self) -> &'a MotionClip {
        self.clip
    }

    #[must_use]
    pub fn begin_playback(&self) -> ClipPlayback<'_, 'a> {
        ClipPlayback {
            evaluator: self,
            previous_tick: None,
            exit_request: None,
        }
    }

    pub fn evaluate(
        &self,
        phase: ClipPhaseInput,
        exit_request: Option<ExitRequest>,
    ) -> Result<ClipEvaluation<'a>, MotionDirectorError> {
        let provided = phase.source();
        if provided != self.clip.phase_source {
            return Err(MotionDirectorError::PhaseSourceMismatch {
                clip_id: self.clip.clip_id.clone(),
                expected: self.clip.phase_source,
                provided,
            });
        }
        if !matches!(provided, PhaseSource::Time | PhaseSource::Distance) {
            return Err(MotionDirectorError::PhaseSourceNotEnabled {
                phase_source: provided,
            });
        }

        let tick = phase.tick();
        match self.clip.loop_mode {
            LoopMode::Once => self.evaluate_once(tick, exit_request),
            LoopMode::Repeat => self.evaluate_repeat(tick, exit_request),
            LoopMode::MarkedSegment => self.evaluate_marked(tick, exit_request),
        }
    }

    fn evaluate_once(
        &self,
        tick: u64,
        exit_request: Option<ExitRequest>,
    ) -> Result<ClipEvaluation<'a>, MotionDirectorError> {
        let completed_at = self.layout.total_duration;
        let effective_exit =
            exit_request.filter(|request| request.requested_at_tick <= completed_at);
        let exit = exit_state(tick, effective_exit, completed_at);
        if tick >= completed_at {
            return Ok(self.completed_frame(tick, 0, completed_at, exit));
        }
        Ok(self.active_frame(tick, tick, 0, exit))
    }

    fn evaluate_repeat(
        &self,
        tick: u64,
        exit_request: Option<ExitRequest>,
    ) -> Result<ClipEvaluation<'a>, MotionDirectorError> {
        let scheduled_exit = exit_request
            .map(|request| {
                let minimum_exit_tick = request
                    .requested_at_tick
                    .max(u64::from(self.clip.minimum_hold_ticks));
                next_repeat_boundary(minimum_exit_tick, self.layout.total_duration)
                    .ok_or_else(|| MotionDirectorError::ExitTickOverflow {
                        clip_id: self.clip.clip_id.clone(),
                    })
                    .map(|safe_exit_tick| (request, safe_exit_tick))
            })
            .transpose()?;
        let exit = scheduled_exit.map_or(ClipExitState::NotRequested, |(request, safe)| {
            exit_state(tick, Some(request), safe)
        });
        if let Some((_, completed_at)) = scheduled_exit {
            if tick >= completed_at {
                let cycle = completed_at / self.layout.total_duration - 1;
                return Ok(self.completed_frame(tick, cycle, completed_at, exit));
            }
        }

        let cycle = tick / self.layout.total_duration;
        let local_tick = tick % self.layout.total_duration;
        Ok(self.active_frame(tick, local_tick, cycle, exit))
    }

    fn evaluate_marked(
        &self,
        tick: u64,
        exit_request: Option<ExitRequest>,
    ) -> Result<ClipEvaluation<'a>, MotionDirectorError> {
        if tick < self.layout.prefix_duration {
            let exit = match exit_request {
                Some(request) if tick >= request.requested_at_tick => {
                    let safe = self.marked_exit_boundary(request.requested_at_tick)?;
                    exit_state(tick, Some(request), safe)
                }
                _ => ClipExitState::NotRequested,
            };
            return Ok(self.active_frame(tick, tick, 0, exit));
        }

        let scheduled_exit = exit_request
            .map(|request| {
                self.marked_exit_boundary(request.requested_at_tick)
                    .map(|safe_exit_tick| (request, safe_exit_tick))
            })
            .transpose()?;
        let exit = scheduled_exit.map_or(ClipExitState::NotRequested, |(request, safe)| {
            exit_state(tick, Some(request), safe)
        });

        if let Some((_, safe_exit_tick)) = scheduled_exit {
            if tick >= safe_exit_tick {
                let loop_cycle =
                    (safe_exit_tick - self.layout.prefix_duration) / self.layout.loop_duration - 1;
                let tail_tick = tick - safe_exit_tick;
                let completed_at = safe_exit_tick
                    .checked_add(self.layout.tail_duration)
                    .ok_or_else(|| MotionDirectorError::ExitTickOverflow {
                        clip_id: self.clip.clip_id.clone(),
                    })?;
                if tail_tick >= self.layout.tail_duration {
                    return Ok(self.completed_frame(tick, loop_cycle, completed_at, exit));
                }
                let loop_end_sample = self.layout.loop_end_sample.ok_or_else(|| {
                    MotionDirectorError::InvalidMarkedLoop {
                        clip_id: self.clip.clip_id.clone(),
                    }
                })?;
                let tail_start = self.layout.sample_starts[loop_end_sample + 1];
                return Ok(self.active_frame(tick, tail_start + tail_tick, loop_cycle, exit));
            }
        }

        let loop_tick = tick - self.layout.prefix_duration;
        let cycle = loop_tick / self.layout.loop_duration;
        let loop_offset = loop_tick % self.layout.loop_duration;
        Ok(self.active_frame(tick, self.layout.prefix_duration + loop_offset, cycle, exit))
    }

    fn marked_exit_boundary(&self, requested_at_tick: u64) -> Result<u64, MotionDirectorError> {
        let minimum_exit_tick = requested_at_tick.max(u64::from(self.clip.minimum_hold_ticks));
        let first_loop_end = self
            .layout
            .prefix_duration
            .checked_add(self.layout.loop_duration)
            .ok_or_else(|| MotionDirectorError::ExitTickOverflow {
                clip_id: self.clip.clip_id.clone(),
            })?;
        if minimum_exit_tick <= first_loop_end {
            return Ok(first_loop_end);
        }
        let relative = minimum_exit_tick - self.layout.prefix_duration;
        let cycles = relative.div_ceil(self.layout.loop_duration);
        self.layout
            .loop_duration
            .checked_mul(cycles)
            .and_then(|duration| self.layout.prefix_duration.checked_add(duration))
            .ok_or_else(|| MotionDirectorError::ExitTickOverflow {
                clip_id: self.clip.clip_id.clone(),
            })
    }

    fn next_boundary_after(
        &self,
        tick: u64,
        exit_request: Option<ExitRequest>,
    ) -> Result<Option<u64>, MotionDirectorError> {
        let evaluation =
            self.evaluate(clip_phase_input(self.clip.phase_source, tick), exit_request)?;
        if matches!(evaluation.completion, ClipCompletionState::Completed { .. }) {
            return Ok(None);
        }
        let hold_ticks = u64::from(self.clip.samples[evaluation.sample_index].hold_ticks);
        Ok(evaluation.sample_started_at_tick.checked_add(hold_ticks))
    }

    fn active_frame(
        &self,
        tick: u64,
        clip_offset: u64,
        cycle: u64,
        exit: ClipExitState,
    ) -> ClipEvaluation<'a> {
        let (sample_index, sample_local_tick) = self.layout.sample_for_offset(clip_offset);
        let sample = &self.clip.samples[sample_index];
        ClipEvaluation {
            clip_id: &self.clip.clip_id,
            pose_id: &sample.pose_id,
            phase_source: self.clip.phase_source,
            phase_tick: tick,
            cycle,
            sample_index,
            sample_local_tick,
            sample_started_at_tick: tick - sample_local_tick,
            active_markers: &sample.markers,
            completion: ClipCompletionState::Playing,
            exit,
        }
    }

    fn completed_frame(
        &self,
        tick: u64,
        cycle: u64,
        completed_at_tick: u64,
        exit: ClipExitState,
    ) -> ClipEvaluation<'a> {
        let sample_index = self.clip.samples.len() - 1;
        let sample = &self.clip.samples[sample_index];
        let sample_local_tick = u64::from(sample.hold_ticks);
        ClipEvaluation {
            clip_id: &self.clip.clip_id,
            pose_id: &sample.pose_id,
            phase_source: self.clip.phase_source,
            phase_tick: tick,
            cycle,
            sample_index,
            sample_local_tick,
            sample_started_at_tick: completed_at_tick.saturating_sub(sample_local_tick),
            active_markers: &[],
            completion: ClipCompletionState::Completed { completed_at_tick },
            exit,
        }
    }
}

#[derive(Debug)]
pub struct ClipPlayback<'evaluator, 'graph> {
    evaluator: &'evaluator ClipEvaluator<'graph>,
    previous_tick: Option<u64>,
    exit_request: Option<ExitRequest>,
}

impl<'evaluator, 'graph> ClipPlayback<'evaluator, 'graph> {
    pub fn request_exit(&mut self, request: ExitRequest) -> Result<(), MotionDirectorError> {
        if let Some(previous_tick) = self.previous_tick {
            if request.requested_at_tick < previous_tick {
                return Err(MotionDirectorError::LateExitRequest {
                    clip_id: self.evaluator.clip.clip_id.clone(),
                    current_tick: previous_tick,
                    requested_tick: request.requested_at_tick,
                });
            }
        }
        if let Some(existing) = self.exit_request {
            if existing != request {
                return Err(MotionDirectorError::ConflictingExitRequest {
                    clip_id: self.evaluator.clip.clip_id.clone(),
                    existing_tick: existing.requested_at_tick,
                    requested_tick: request.requested_at_tick,
                });
            }
        } else {
            self.exit_request = Some(request);
        }
        Ok(())
    }

    pub fn advance_to<'step>(
        &'step mut self,
        phase: ClipPhaseInput,
    ) -> Result<ClipAdvance<'step, 'graph>, MotionDirectorError> {
        let next_tick = phase.tick();
        if let Some(previous_tick) = self.previous_tick {
            if next_tick < previous_tick {
                return Err(MotionDirectorError::NonMonotonicAdvance {
                    clip_id: self.evaluator.clip.clip_id.clone(),
                    previous_tick,
                    next_tick,
                });
            }
        }

        let evaluation = self.evaluator.evaluate(phase, self.exit_request)?;
        let crossed_markers = CrossedMarkerEvents::new(
            self.evaluator,
            self.previous_tick,
            next_tick,
            self.exit_request,
        )?;
        self.previous_tick = Some(next_tick);
        Ok(ClipAdvance {
            evaluation,
            crossed_markers,
        })
    }
}

#[derive(Debug)]
pub struct ClipAdvance<'evaluator, 'graph> {
    pub evaluation: ClipEvaluation<'graph>,
    pub crossed_markers: CrossedMarkerEvents<'evaluator, 'graph>,
}

#[derive(Debug)]
pub struct CrossedMarkerEvents<'evaluator, 'graph> {
    evaluator: &'evaluator ClipEvaluator<'graph>,
    upper_tick: u64,
    exit_request: Option<ExitRequest>,
    next_boundary_tick: Option<u64>,
    pending: VecDeque<MarkerEvent>,
}

impl<'evaluator, 'graph> CrossedMarkerEvents<'evaluator, 'graph> {
    fn new(
        evaluator: &'evaluator ClipEvaluator<'graph>,
        previous_tick: Option<u64>,
        upper_tick: u64,
        exit_request: Option<ExitRequest>,
    ) -> Result<Self, MotionDirectorError> {
        let next_boundary_tick = match previous_tick {
            None => Some(0),
            Some(previous_tick) => evaluator.next_boundary_after(previous_tick, exit_request)?,
        }
        .filter(|boundary| *boundary <= upper_tick);
        Ok(Self {
            evaluator,
            upper_tick,
            exit_request,
            next_boundary_tick,
            pending: VecDeque::new(),
        })
    }

    fn queue_boundary(&mut self, boundary_tick: u64) -> Result<(), MotionDirectorError> {
        let evaluation = self.evaluator.evaluate(
            clip_phase_input(self.evaluator.clip.phase_source, boundary_tick),
            self.exit_request,
        )?;
        match evaluation.completion {
            ClipCompletionState::Completed { .. } => {
                for marker in &self.evaluator.clip.exit_markers {
                    self.pending.push_back(MarkerEvent {
                        tick: boundary_tick,
                        cycle: evaluation.cycle,
                        sample_index: evaluation.sample_index,
                        marker: *marker,
                        kind: MarkerEventKind::LifecycleExit,
                    });
                }
            }
            ClipCompletionState::Playing => {
                let mut entry_emitted = false;
                for marker in evaluation.active_markers {
                    let kind = if *marker == self.evaluator.clip.entry_marker {
                        if boundary_tick != 0 || entry_emitted {
                            continue;
                        }
                        entry_emitted = true;
                        MarkerEventKind::LifecycleEntry
                    } else if self.evaluator.clip.exit_markers.contains(marker) {
                        continue;
                    } else {
                        MarkerEventKind::SampleEntry
                    };
                    self.pending.push_back(MarkerEvent {
                        tick: boundary_tick,
                        cycle: evaluation.cycle,
                        sample_index: evaluation.sample_index,
                        marker: *marker,
                        kind,
                    });
                }
            }
        }

        self.next_boundary_tick = self
            .evaluator
            .next_boundary_after(boundary_tick, self.exit_request)?
            .filter(|next| *next <= self.upper_tick);
        Ok(())
    }
}

fn clip_phase_input(source: PhaseSource, tick: u64) -> ClipPhaseInput {
    match source {
        PhaseSource::Time => ClipPhaseInput::Time(SimulationTick(tick)),
        PhaseSource::Distance => ClipPhaseInput::Distance(DistancePhaseTick(tick)),
        PhaseSource::Wing => ClipPhaseInput::Wing(WingPhaseTick(tick)),
        PhaseSource::Speech => ClipPhaseInput::Speech(SpeechPhaseTick(tick)),
    }
}

impl Iterator for CrossedMarkerEvents<'_, '_> {
    type Item = Result<MarkerEvent, MotionDirectorError>;

    fn next(&mut self) -> Option<Self::Item> {
        loop {
            if let Some(event) = self.pending.pop_front() {
                return Some(Ok(event));
            }
            let boundary_tick = self.next_boundary_tick?;
            if let Err(error) = self.queue_boundary(boundary_tick) {
                self.next_boundary_tick = None;
                return Some(Err(error));
            }
        }
    }
}

#[derive(Clone, Debug)]
pub struct MotionDirector<'a> {
    clips: BTreeMap<&'a str, ClipEvaluator<'a>>,
}

impl<'a> MotionDirector<'a> {
    pub fn new(graph: &'a MotionGraphV1) -> Result<Self, MotionDirectorError> {
        let mut clips = BTreeMap::new();
        for clip in &graph.clips {
            let evaluator = ClipEvaluator::new(clip)?;
            if clips.insert(clip.clip_id.as_str(), evaluator).is_some() {
                return Err(MotionDirectorError::DuplicateClip(clip.clip_id.clone()));
            }
        }
        Ok(Self { clips })
    }

    pub fn clip(&self, clip_id: &str) -> Result<&ClipEvaluator<'a>, MotionDirectorError> {
        self.clips
            .get(clip_id)
            .ok_or_else(|| MotionDirectorError::UnknownClip(clip_id.to_string()))
    }

    pub fn evaluate(
        &self,
        clip_id: &str,
        phase: ClipPhaseInput,
        exit_request: Option<ExitRequest>,
    ) -> Result<ClipEvaluation<'a>, MotionDirectorError> {
        self.clip(clip_id)?.evaluate(phase, exit_request)
    }

    pub fn reduced_motion_target(
        &self,
        clip_id: &str,
    ) -> Result<Option<&'a str>, MotionDirectorError> {
        Ok(self.clip(clip_id)?.clip().reduced_motion_clip_id.as_deref())
    }
}

/// An authored marker position within one transition generation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TransitionMarkerTick {
    pub marker: MotionMarker,
    pub cycle: u64,
    pub occurrence: u32,
    pub offset_tick: u64,
}

/// Integer-only timing authority supplied to the shadow transition evaluator.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TransitionTimeline {
    start_tick: u64,
    duration_ticks: u64,
    completion_tick: u64,
    markers: Vec<TransitionMarkerTick>,
}

impl TransitionTimeline {
    pub fn new(
        start_tick: u64,
        duration_ticks: u64,
        markers: Vec<TransitionMarkerTick>,
    ) -> Result<Self, MotionDirectorError> {
        if duration_ticks == 0 {
            return Err(MotionDirectorError::ZeroTransitionDuration);
        }
        let completion_tick = start_tick
            .checked_add(duration_ticks)
            .ok_or(MotionDirectorError::TransitionTickOverflow)?;
        let mut seen = BTreeSet::new();
        for marker in &markers {
            if marker.offset_tick > duration_ticks {
                return Err(MotionDirectorError::TransitionMarkerOutOfRange {
                    marker: marker.marker,
                    tick: marker.offset_tick,
                    duration: duration_ticks,
                });
            }
            if !seen.insert((marker.marker, marker.cycle, marker.occurrence)) {
                return Err(MotionDirectorError::DuplicateTransitionMarkerIdentity {
                    marker: marker.marker,
                    cycle: marker.cycle,
                    occurrence: marker.occurrence,
                });
            }
        }
        Ok(Self {
            start_tick,
            duration_ticks,
            completion_tick,
            markers,
        })
    }

    #[must_use]
    pub const fn start_tick(&self) -> u64 {
        self.start_tick
    }

    #[must_use]
    pub const fn duration_ticks(&self) -> u64 {
        self.duration_ticks
    }

    #[must_use]
    pub const fn completion_tick(&self) -> u64 {
        self.completion_tick
    }

    #[must_use]
    pub fn markers(&self) -> &[TransitionMarkerTick] {
        &self.markers
    }

    fn active_markers(&self, current_tick: u64) -> Vec<TransitionMarkerTick> {
        let Some(offset) = current_tick.checked_sub(self.start_tick) else {
            return Vec::new();
        };
        self.markers
            .iter()
            .filter(|authored| authored.offset_tick == offset)
            .copied()
            .collect()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TransitionPhaseInput {
    Time(SimulationTick),
    Distance(DistancePhaseTick),
    Wing(WingPhaseTick),
    Speech(SpeechPhaseTick),
}

impl TransitionPhaseInput {
    #[must_use]
    pub const fn source(self) -> PhaseSource {
        match self {
            Self::Time(_) => PhaseSource::Time,
            Self::Distance(_) => PhaseSource::Distance,
            Self::Wing(_) => PhaseSource::Wing,
            Self::Speech(_) => PhaseSource::Speech,
        }
    }

    #[must_use]
    pub const fn tick(self) -> u64 {
        match self {
            Self::Time(tick) => tick.0,
            Self::Distance(tick) => tick.0,
            Self::Wing(tick) => tick.0,
            Self::Speech(tick) => tick.0,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TransitionInterruptRequest {
    pub requested_at_tick: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TransitionInterruptPosition {
    BeforeWindow { window_index: usize },
    InsideWindow { window_index: usize },
    AfterWindows,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TransitionInterruptDecision {
    pub requested_at_tick: u64,
    pub recovery_at_tick: u64,
    pub position: TransitionInterruptPosition,
    pub interrupt_policy: InterruptPolicy,
    pub recovery_policy: RecoveryPolicy,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TransitionLifecycleState {
    Pending,
    Handoff,
    Recovery {
        interrupted: bool,
        recovery_policy: Option<RecoveryPolicy>,
    },
    Completed {
        completed_at_tick: u64,
    },
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum TransitionContactState {
    Source(SupportContact),
    Target(SupportContact),
    Braced(Vec<ContactPoint>),
    Airborne,
    None,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TransitionRootState {
    Source([i8; 2]),
    Target([i8; 2]),
    Authored([i8; 2]),
    ContactLocked([i8; 2]),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TransitionRegionState {
    pub policy: RegionPolicy,
    pub target_owned_regions: Vec<PerformanceRegion>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum TransitionSecondaryState {
    Source(String),
    Target(String),
    Settling { source: String, target: String },
    Suppressed,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TransitionEvaluation<'a> {
    pub edge_id: &'a str,
    pub recipe_id: &'a str,
    pub fallback_depth: usize,
    pub current_tick: u64,
    pub handoff_tick: u64,
    pub completion_tick: u64,
    pub state: TransitionLifecycleState,
    pub active_markers: Vec<TransitionMarkerTick>,
    pub interrupt: Option<TransitionInterruptDecision>,
    pub contact: TransitionContactState,
    pub root: TransitionRootState,
    pub regions: TransitionRegionState,
    pub secondary: TransitionSecondaryState,
}

#[derive(Clone, Copy, Debug)]
pub struct ResolvedTransition<'a> {
    pub edge: &'a MotionEdge,
    pub recipe: &'a TransitionRecipe,
    pub source_clip: &'a MotionClip,
    pub target_clip: &'a MotionClip,
    pub fallback_depth: usize,
}

/// Read-only graph evaluator for ANIM-041. It does not select or activate runtime behavior.
#[derive(Clone, Debug)]
pub struct TransitionDirector<'a> {
    clips: BTreeMap<&'a str, &'a MotionClip>,
    recipes: BTreeMap<&'a str, &'a TransitionRecipe>,
    edges: BTreeMap<&'a str, &'a MotionEdge>,
    directed_edges: BTreeMap<(&'a str, &'a str), Vec<&'a MotionEdge>>,
}

impl<'a> TransitionDirector<'a> {
    pub fn new(graph: &'a MotionGraphV1) -> Result<Self, MotionDirectorError> {
        let mut clips = BTreeMap::new();
        for clip in &graph.clips {
            if clips.insert(clip.clip_id.as_str(), clip).is_some() {
                return Err(MotionDirectorError::DuplicateClip(clip.clip_id.clone()));
            }
            ClipLayout::build(clip)?;
        }

        let mut recipes = BTreeMap::new();
        for recipe in &graph.transition_recipes {
            if recipes.insert(recipe.recipe_id.as_str(), recipe).is_some() {
                return Err(MotionDirectorError::DuplicateTransitionRecipe(
                    recipe.recipe_id.clone(),
                ));
            }
            validate_transition_recipe(recipe)?;
        }
        validate_fallback_chains(&recipes)?;

        let mut edges = BTreeMap::new();
        let mut directed_edges: BTreeMap<(&str, &str), Vec<&MotionEdge>> = BTreeMap::new();
        for edge in &graph.edges {
            if edges.insert(edge.edge_id.as_str(), edge).is_some() {
                return Err(MotionDirectorError::DuplicateMotionEdge(
                    edge.edge_id.clone(),
                ));
            }
            directed_edges
                .entry((edge.source_clip_id.as_str(), edge.target_clip_id.as_str()))
                .or_default()
                .push(edge);
        }

        let director = Self {
            clips,
            recipes,
            edges,
            directed_edges,
        };
        for edge_id in director.edges.keys() {
            director.resolve_edge(edge_id)?;
        }
        Ok(director)
    }

    pub fn resolve_edge(
        &self,
        edge_id: &str,
    ) -> Result<ResolvedTransition<'a>, MotionDirectorError> {
        let edge = self
            .edges
            .get(edge_id)
            .copied()
            .ok_or_else(|| MotionDirectorError::UnknownMotionEdge(edge_id.to_string()))?;
        let source_clip = self
            .clips
            .get(edge.source_clip_id.as_str())
            .copied()
            .ok_or_else(|| MotionDirectorError::MissingEdgeClip {
                edge_id: edge.edge_id.clone(),
                role: "source",
                clip_id: edge.source_clip_id.clone(),
            })?;
        let target_clip = self
            .clips
            .get(edge.target_clip_id.as_str())
            .copied()
            .ok_or_else(|| MotionDirectorError::MissingEdgeClip {
                edge_id: edge.edge_id.clone(),
                role: "target",
                clip_id: edge.target_clip_id.clone(),
            })?;

        let mut recipe_id = edge.transition_recipe_id.as_str();
        let mut seen = BTreeSet::new();
        let mut fallback_depth = 0;
        loop {
            if !seen.insert(recipe_id) {
                return Err(MotionDirectorError::TransitionFallbackCycle {
                    recipe_id: recipe_id.to_string(),
                });
            }
            let recipe = self.recipes.get(recipe_id).copied().ok_or_else(|| {
                MotionDirectorError::MissingTransitionRecipe {
                    edge_id: edge.edge_id.clone(),
                    recipe_id: recipe_id.to_string(),
                }
            })?;
            if recipe.source_families.contains(&source_clip.family)
                && recipe.target_families.contains(&target_clip.family)
            {
                return Ok(ResolvedTransition {
                    edge,
                    recipe,
                    source_clip,
                    target_clip,
                    fallback_depth,
                });
            }
            let Some(fallback) = recipe.fallback_recipe_id.as_deref() else {
                return Err(MotionDirectorError::TransitionFamilyNotAdmitted {
                    edge_id: edge.edge_id.clone(),
                    source_family: source_clip.family,
                    target_family: target_clip.family,
                });
            };
            recipe_id = fallback;
            fallback_depth += 1;
        }
    }

    pub fn resolve_between(
        &self,
        source_clip_id: &str,
        target_clip_id: &str,
    ) -> Result<ResolvedTransition<'a>, MotionDirectorError> {
        let edges = self
            .directed_edges
            .get(&(source_clip_id, target_clip_id))
            .ok_or_else(|| MotionDirectorError::MissingDirectedEdge {
                source_clip_id: source_clip_id.to_string(),
                target_clip_id: target_clip_id.to_string(),
            })?;
        if edges.len() != 1 {
            return Err(MotionDirectorError::AmbiguousDirectedEdge {
                source_clip_id: source_clip_id.to_string(),
                target_clip_id: target_clip_id.to_string(),
                edge_ids: edges.iter().map(|edge| edge.edge_id.clone()).collect(),
            });
        }
        self.resolve_edge(&edges[0].edge_id)
    }

    pub fn evaluate(
        &self,
        edge_id: &str,
        timeline: &TransitionTimeline,
        phase: TransitionPhaseInput,
        interrupt: Option<TransitionInterruptRequest>,
    ) -> Result<TransitionEvaluation<'a>, MotionDirectorError> {
        let resolved = self.resolve_edge(edge_id)?;
        evaluate_transition(resolved, timeline, phase, interrupt)
    }
}

pub fn select_transition_duration(
    recipe: &TransitionRecipe,
    deterministic_seed: u64,
) -> Result<u16, MotionDirectorError> {
    validate_transition_recipe(recipe)?;
    let minimum = u64::from(recipe.duration_ticks.min);
    let span = u64::from(recipe.duration_ticks.max) - minimum + 1;
    u16::try_from(minimum + deterministic_seed % span).map_err(|_| {
        MotionDirectorError::MalformedTransitionRecipe {
            recipe_id: recipe.recipe_id.clone(),
            reason: "duration selection exceeded u16 TickRange".to_string(),
        }
    })
}

fn validate_transition_recipe(recipe: &TransitionRecipe) -> Result<(), MotionDirectorError> {
    let malformed = |reason: &str| MotionDirectorError::MalformedTransitionRecipe {
        recipe_id: recipe.recipe_id.clone(),
        reason: reason.to_string(),
    };
    if recipe.source_families.is_empty() || recipe.target_families.is_empty() {
        return Err(malformed(
            "source and target family admission must be non-empty",
        ));
    }
    if recipe.duration_ticks.min == 0 || recipe.duration_ticks.min > recipe.duration_ticks.max {
        return Err(malformed("duration range must be non-zero and ordered"));
    }
    if recipe.interrupt_windows.is_empty() {
        return Err(malformed("at least one interrupt window is required"));
    }
    if recipe
        .interrupt_windows
        .iter()
        .any(|window| window.start_marker == window.end_marker)
    {
        return Err(malformed("interrupt window markers must differ"));
    }
    Ok(())
}

fn validate_fallback_chains(
    recipes: &BTreeMap<&str, &TransitionRecipe>,
) -> Result<(), MotionDirectorError> {
    for recipe_id in recipes.keys() {
        let mut seen = BTreeSet::new();
        let mut current = Some(*recipe_id);
        while let Some(id) = current {
            if !seen.insert(id) {
                return Err(MotionDirectorError::TransitionFallbackCycle {
                    recipe_id: (*recipe_id).to_string(),
                });
            }
            let recipe = recipes.get(id).copied().ok_or_else(|| {
                MotionDirectorError::MalformedTransitionRecipe {
                    recipe_id: (*recipe_id).to_string(),
                    reason: format!("fallback recipe {id} does not exist"),
                }
            })?;
            current = recipe.fallback_recipe_id.as_deref();
        }
    }
    Ok(())
}

fn evaluate_transition<'a>(
    resolved: ResolvedTransition<'a>,
    timeline: &TransitionTimeline,
    phase: TransitionPhaseInput,
    interrupt: Option<TransitionInterruptRequest>,
) -> Result<TransitionEvaluation<'a>, MotionDirectorError> {
    let recipe = resolved.recipe;
    let expected_phase = match recipe.timing {
        crate::motion_graph::TransitionTiming::Fixed
        | crate::motion_graph::TransitionTiming::MarkerAligned => PhaseSource::Time,
        crate::motion_graph::TransitionTiming::DistancePhase => PhaseSource::Distance,
        crate::motion_graph::TransitionTiming::WingPhase => PhaseSource::Wing,
        crate::motion_graph::TransitionTiming::SpeechAligned => PhaseSource::Speech,
    };
    if phase.source() != expected_phase {
        return Err(MotionDirectorError::TransitionPhaseSourceMismatch {
            recipe_id: recipe.recipe_id.clone(),
            expected: expected_phase,
            provided: phase.source(),
        });
    }
    let current_tick = phase.tick();
    if timeline.duration_ticks < u64::from(recipe.duration_ticks.min)
        || timeline.duration_ticks > u64::from(recipe.duration_ticks.max)
    {
        return Err(MotionDirectorError::TransitionDurationOutOfRange {
            recipe_id: recipe.recipe_id.clone(),
            duration: timeline.duration_ticks,
            minimum: recipe.duration_ticks.min,
            maximum: recipe.duration_ticks.max,
        });
    }
    if current_tick < timeline.start_tick {
        return Err(MotionDirectorError::TransitionTickBeforeStart {
            current_tick,
            start_tick: timeline.start_tick,
        });
    }
    let handoff_offset = required_marker_offset(recipe, timeline, recipe.handoff_marker)?;
    if handoff_offset >= timeline.duration_ticks {
        return Err(MotionDirectorError::InvalidTransitionMarkerInterval {
            recipe_id: recipe.recipe_id.clone(),
        });
    }
    let handoff_tick = timeline
        .start_tick
        .checked_add(handoff_offset)
        .ok_or(MotionDirectorError::TransitionTickOverflow)?;
    validate_interrupt_timeline(recipe, timeline)?;
    let interrupt = interrupt
        .map(|request| evaluate_interrupt(recipe, timeline, request))
        .transpose()?;

    let state = if current_tick >= timeline.completion_tick {
        TransitionLifecycleState::Completed {
            completed_at_tick: timeline.completion_tick,
        }
    } else if let Some(decision) = interrupt.filter(|decision| {
        current_tick >= decision.requested_at_tick && current_tick >= decision.recovery_at_tick
    }) {
        TransitionLifecycleState::Recovery {
            interrupted: true,
            recovery_policy: Some(decision.recovery_policy),
        }
    } else if current_tick < handoff_tick {
        TransitionLifecycleState::Pending
    } else if current_tick == handoff_tick {
        TransitionLifecycleState::Handoff
    } else {
        TransitionLifecycleState::Recovery {
            interrupted: false,
            recovery_policy: None,
        }
    };
    let handed_off = current_tick >= handoff_tick;
    let completed = current_tick >= timeline.completion_tick;
    let (source_sample, target_sample) = endpoint_samples(resolved)?;

    Ok(TransitionEvaluation {
        edge_id: &resolved.edge.edge_id,
        recipe_id: &recipe.recipe_id,
        fallback_depth: resolved.fallback_depth,
        current_tick,
        handoff_tick,
        completion_tick: timeline.completion_tick,
        state,
        active_markers: timeline.active_markers(current_tick),
        interrupt,
        contact: evaluate_contact(
            recipe,
            source_sample,
            target_sample,
            handed_off,
            current_tick == handoff_tick,
        )?,
        root: evaluate_root(recipe, source_sample, target_sample, handed_off, completed)?,
        regions: TransitionRegionState {
            policy: recipe.region_policy,
            target_owned_regions: resolved.target_clip.owned_channels.regions.clone(),
        },
        secondary: evaluate_secondary(recipe, source_sample, target_sample, handed_off, completed),
    })
}

fn endpoint_samples<'a>(
    resolved: ResolvedTransition<'a>,
) -> Result<
    (
        &'a crate::motion_graph::MotionSample,
        &'a crate::motion_graph::MotionSample,
    ),
    MotionDirectorError,
> {
    let source =
        resolved
            .source_clip
            .samples
            .last()
            .ok_or_else(|| MotionDirectorError::EmptyClip {
                clip_id: resolved.source_clip.clip_id.clone(),
            })?;
    let target =
        resolved
            .target_clip
            .samples
            .first()
            .ok_or_else(|| MotionDirectorError::EmptyClip {
                clip_id: resolved.target_clip.clip_id.clone(),
            })?;
    Ok((source, target))
}

fn required_marker_offset(
    recipe: &TransitionRecipe,
    timeline: &TransitionTimeline,
    marker: MotionMarker,
) -> Result<u64, MotionDirectorError> {
    let mut matches = timeline
        .markers
        .iter()
        .filter(|authored| authored.marker == marker);
    let first = matches
        .next()
        .ok_or_else(|| MotionDirectorError::MissingTransitionMarker {
            recipe_id: recipe.recipe_id.clone(),
            marker,
        })?;
    if matches.next().is_some() {
        return Err(MotionDirectorError::AmbiguousTransitionMarker { marker });
    }
    Ok(first.offset_tick)
}

fn required_marker_tick(
    recipe: &TransitionRecipe,
    timeline: &TransitionTimeline,
    marker: MotionMarker,
) -> Result<u64, MotionDirectorError> {
    timeline
        .start_tick
        .checked_add(required_marker_offset(recipe, timeline, marker)?)
        .ok_or(MotionDirectorError::TransitionTickOverflow)
}

fn validate_interrupt_timeline(
    recipe: &TransitionRecipe,
    timeline: &TransitionTimeline,
) -> Result<(), MotionDirectorError> {
    for window in &recipe.interrupt_windows {
        let start = required_marker_offset(recipe, timeline, window.start_marker)?;
        let end = required_marker_offset(recipe, timeline, window.end_marker)?;
        if start >= end {
            return Err(MotionDirectorError::InvalidTransitionMarkerInterval {
                recipe_id: recipe.recipe_id.clone(),
            });
        }
    }
    Ok(())
}

fn evaluate_interrupt(
    recipe: &TransitionRecipe,
    timeline: &TransitionTimeline,
    request: TransitionInterruptRequest,
) -> Result<TransitionInterruptDecision, MotionDirectorError> {
    if request.requested_at_tick < timeline.start_tick {
        return Err(MotionDirectorError::TransitionInterruptBeforeStart {
            requested_tick: request.requested_at_tick,
            start_tick: timeline.start_tick,
        });
    }

    let mut selected = None;
    for (index, window) in recipe.interrupt_windows.iter().enumerate() {
        let start = required_marker_tick(recipe, timeline, window.start_marker)?;
        let end = required_marker_tick(recipe, timeline, window.end_marker)?;
        if request.requested_at_tick >= start && request.requested_at_tick < end {
            selected = Some((
                TransitionInterruptPosition::InsideWindow {
                    window_index: index,
                },
                window,
                request.requested_at_tick,
                end,
            ));
            break;
        }
    }

    if selected.is_none() {
        let mut future = None;
        for (index, window) in recipe.interrupt_windows.iter().enumerate() {
            let start = required_marker_tick(recipe, timeline, window.start_marker)?;
            let end = required_marker_tick(recipe, timeline, window.end_marker)?;
            if request.requested_at_tick < start
                && future
                    .as_ref()
                    .is_none_or(|(best_start, _, _, _)| start < *best_start)
            {
                future = Some((start, index, window, end));
            }
        }
        if let Some((start, index, window, end)) = future {
            selected = Some((
                TransitionInterruptPosition::BeforeWindow {
                    window_index: index,
                },
                window,
                start,
                end,
            ));
        }
    }

    let Some((position, window, base_tick, end_tick)) = selected else {
        let window = recipe.interrupt_windows.last().ok_or_else(|| {
            MotionDirectorError::MalformedTransitionRecipe {
                recipe_id: recipe.recipe_id.clone(),
                reason: "at least one interrupt window is required".to_string(),
            }
        })?;
        return Ok(TransitionInterruptDecision {
            requested_at_tick: request.requested_at_tick,
            recovery_at_tick: request.requested_at_tick,
            position: TransitionInterruptPosition::AfterWindows,
            interrupt_policy: InterruptPolicy::Immediate,
            recovery_policy: window.recovery_policy,
        });
    };

    let recovery_at_tick = match window.interrupt_policy {
        InterruptPolicy::Immediate => base_tick,
        InterruptPolicy::AtSafeMarker | InterruptPolicy::UninterruptibleUntilRecovery => end_tick,
        InterruptPolicy::AfterCommit => base_tick.max(required_marker_tick(
            recipe,
            timeline,
            MotionMarker::Commit,
        )?),
        InterruptPolicy::AfterImpact => base_tick.max(required_marker_tick(
            recipe,
            timeline,
            MotionMarker::Impact,
        )?),
    };
    Ok(TransitionInterruptDecision {
        requested_at_tick: request.requested_at_tick,
        recovery_at_tick,
        position,
        interrupt_policy: window.interrupt_policy,
        recovery_policy: window.recovery_policy,
    })
}

fn evaluate_contact(
    recipe: &TransitionRecipe,
    source: &crate::motion_graph::MotionSample,
    target: &crate::motion_graph::MotionSample,
    handed_off: bool,
    at_handoff: bool,
) -> Result<TransitionContactState, MotionDirectorError> {
    let state = match recipe.contact_policy {
        ContactPolicy::Preserve => {
            if source.support != target.support {
                return Err(MotionDirectorError::ContactCoherenceViolation {
                    recipe_id: recipe.recipe_id.clone(),
                });
            }
            TransitionContactState::Source(source.support.clone())
        }
        ContactPolicy::TransferAtMarker => {
            if handed_off {
                TransitionContactState::Target(target.support.clone())
            } else {
                TransitionContactState::Source(source.support.clone())
            }
        }
        ContactPolicy::ReleaseThenAirborne => {
            if target.support.mode != SupportMode::Airborne || !target.support.points.is_empty() {
                return Err(MotionDirectorError::ContactPolicyViolation {
                    recipe_id: recipe.recipe_id.clone(),
                });
            }
            if handed_off {
                TransitionContactState::Airborne
            } else {
                TransitionContactState::Source(source.support.clone())
            }
        }
        ContactPolicy::AirborneThenLand => {
            if source.support.mode != SupportMode::Airborne
                || target.support.mode != SupportMode::Grounded
            {
                return Err(MotionDirectorError::ContactPolicyViolation {
                    recipe_id: recipe.recipe_id.clone(),
                });
            }
            if handed_off {
                TransitionContactState::Target(target.support.clone())
            } else {
                TransitionContactState::Airborne
            }
        }
        ContactPolicy::BraceTransfer => {
            if source.support.mode != SupportMode::Grounded
                || target.support.mode != SupportMode::Grounded
            {
                return Err(MotionDirectorError::ContactPolicyViolation {
                    recipe_id: recipe.recipe_id.clone(),
                });
            }
            if at_handoff {
                let mut points = source.support.points.clone();
                for point in &target.support.points {
                    if !points.contains(point) {
                        points.push(*point);
                    }
                }
                TransitionContactState::Braced(points)
            } else if handed_off {
                TransitionContactState::Target(target.support.clone())
            } else {
                TransitionContactState::Source(source.support.clone())
            }
        }
        ContactPolicy::None => TransitionContactState::None,
    };
    Ok(state)
}

fn evaluate_root(
    recipe: &TransitionRecipe,
    source: &crate::motion_graph::MotionSample,
    target: &crate::motion_graph::MotionSample,
    handed_off: bool,
    completed: bool,
) -> Result<TransitionRootState, MotionDirectorError> {
    let state = match recipe.root_policy {
        RootPolicy::Preserve => {
            if source.root_offset != target.root_offset {
                return Err(MotionDirectorError::RootCoherenceViolation {
                    recipe_id: recipe.recipe_id.clone(),
                });
            }
            TransitionRootState::Source(source.root_offset)
        }
        RootPolicy::FollowTarget => {
            if handed_off {
                TransitionRootState::Target(target.root_offset)
            } else {
                TransitionRootState::Source(source.root_offset)
            }
        }
        RootPolicy::AuthoredOffset => {
            if handed_off {
                TransitionRootState::Authored(target.root_offset)
            } else {
                TransitionRootState::Authored(source.root_offset)
            }
        }
        RootPolicy::ContactLocked => {
            if source.support.mode != SupportMode::Grounded
                || target.support.mode != SupportMode::Grounded
            {
                return Err(MotionDirectorError::ContactPolicyViolation {
                    recipe_id: recipe.recipe_id.clone(),
                });
            }
            if completed {
                TransitionRootState::Target(target.root_offset)
            } else {
                TransitionRootState::ContactLocked(source.root_offset)
            }
        }
    };
    Ok(state)
}

fn evaluate_secondary(
    recipe: &TransitionRecipe,
    source: &crate::motion_graph::MotionSample,
    target: &crate::motion_graph::MotionSample,
    handed_off: bool,
    completed: bool,
) -> TransitionSecondaryState {
    match recipe.secondary_policy {
        SecondaryPolicy::Preserve => {
            TransitionSecondaryState::Source(source.secondary_profile_id.clone())
        }
        SecondaryPolicy::Settle if completed => {
            TransitionSecondaryState::Target(target.secondary_profile_id.clone())
        }
        SecondaryPolicy::Settle => TransitionSecondaryState::Settling {
            source: source.secondary_profile_id.clone(),
            target: target.secondary_profile_id.clone(),
        },
        SecondaryPolicy::ResetAtMarker if handed_off => {
            TransitionSecondaryState::Target(target.secondary_profile_id.clone())
        }
        SecondaryPolicy::ResetAtMarker => {
            TransitionSecondaryState::Source(source.secondary_profile_id.clone())
        }
        SecondaryPolicy::Suppress => TransitionSecondaryState::Suppressed,
    }
}

fn next_repeat_boundary(requested_at_tick: u64, duration: u64) -> Option<u64> {
    let cycles = requested_at_tick.div_ceil(duration).max(1);
    cycles.checked_mul(duration)
}

fn exit_state(tick: u64, request: Option<ExitRequest>, safe_exit_tick: u64) -> ClipExitState {
    let Some(request) = request else {
        return ClipExitState::NotRequested;
    };
    if tick < request.requested_at_tick {
        ClipExitState::NotRequested
    } else if tick < safe_exit_tick {
        ClipExitState::Pending {
            requested_at_tick: request.requested_at_tick,
            safe_exit_tick,
        }
    } else {
        ClipExitState::Satisfied {
            requested_at_tick: request.requested_at_tick,
            safe_exit_tick,
        }
    }
}

fn checked_add_duration(
    accumulated: u64,
    hold_ticks: u64,
    clip_id: &str,
) -> Result<u64, MotionDirectorError> {
    accumulated
        .checked_add(hold_ticks)
        .ok_or_else(|| MotionDirectorError::DurationOverflow {
            clip_id: clip_id.to_string(),
        })
}

#[cfg(test)]
mod internal_tests {
    use super::{checked_add_duration, MotionDirectorError};

    #[test]
    fn duration_sum_overflow_is_checked() {
        assert_eq!(
            checked_add_duration(u64::MAX, 1, "overflow"),
            Err(MotionDirectorError::DurationOverflow {
                clip_id: "overflow".to_string(),
            })
        );
    }
}
