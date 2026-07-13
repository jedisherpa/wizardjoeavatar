use crate::motion_graph::{LoopMode, MotionClip, MotionGraphV1, MotionMarker, PhaseSource};
use std::collections::{BTreeMap, VecDeque};
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
        if provided != PhaseSource::Time {
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
        let evaluation = self.evaluate(ClipPhaseInput::Time(SimulationTick(tick)), exit_request)?;
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
            ClipPhaseInput::Time(SimulationTick(boundary_tick)),
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
