use crate::chat_event::{
    AttentionTarget, ChatTurnState, CommandId, ContractError, Emotion, GestureKind, MotionProfile,
    SpeechMarkerKindV1, SpeechPlanV1, TimingSource, UtteranceId, Viseme, MAX_VISEME_CUES,
};
use crate::command::{CommandEnvelopeV1, RuntimeEpoch};
use crate::state::MouthShape;
use serde::{Deserialize, Serialize};
use thiserror::Error;

pub const CHAT_PERFORMANCE_SCHEMA_VERSION: u16 = 1;
pub const SIMULATION_HZ: u64 = 60;
pub const MILLIS_PER_SECOND: u64 = 1_000;
pub const MAX_SPEECH_TICKS: u32 = 60 * 60 * 30;
pub const DURATION_FALLBACK_VERSION: u16 = 1;

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RenderedMouthPose {
    Closed,
    OpenSmall,
    OpenMedium,
    OpenWide,
    Rounded,
    Smile,
    Frown,
}

impl RenderedMouthPose {
    pub const ALL: [Self; 7] = [
        Self::Closed,
        Self::OpenSmall,
        Self::OpenMedium,
        Self::OpenWide,
        Self::Rounded,
        Self::Smile,
        Self::Frown,
    ];
}

impl From<Viseme> for RenderedMouthPose {
    fn from(value: Viseme) -> Self {
        match value {
            Viseme::Rest | Viseme::MBP => Self::Closed,
            Viseme::FV | Viseme::TH | Viseme::DTLN | Viseme::SZ => Self::OpenSmall,
            Viseme::KG | Viseme::CHSH => Self::OpenMedium,
            Viseme::A => Self::OpenWide,
            Viseme::R | Viseme::O | Viseme::U => Self::Rounded,
            Viseme::E | Viseme::I => Self::Smile,
        }
    }
}

impl From<RenderedMouthPose> for MouthShape {
    fn from(value: RenderedMouthPose) -> Self {
        match value {
            RenderedMouthPose::Closed => Self::Closed,
            RenderedMouthPose::OpenSmall => Self::OpenSmall,
            RenderedMouthPose::OpenMedium => Self::OpenMedium,
            RenderedMouthPose::OpenWide => Self::OpenWide,
            RenderedMouthPose::Rounded => Self::Rounded,
            RenderedMouthPose::Smile => Self::Smile,
            RenderedMouthPose::Frown => Self::Frown,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct QuantizedVisemeCueV1 {
    pub start_tick: u32,
    pub peak_tick: u32,
    pub end_tick: u32,
    pub viseme: Viseme,
    pub strength: u8,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct QuantizedSpeechMarkerV1 {
    pub tick: u32,
    pub kind: SpeechMarkerKindV1,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct QuantizedSpeechTrackV1 {
    pub utterance_id: UtteranceId,
    pub duration_ticks: u32,
    pub cues: Vec<QuantizedVisemeCueV1>,
    pub markers: Vec<QuantizedSpeechMarkerV1>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GazeIntentV1 {
    pub target: AttentionTarget,
    pub hold_ticks: u16,
    pub return_to_user: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ChatPerformanceContentV1 {
    pub turn_state: ChatTurnState,
    pub emotion: Emotion,
    pub intensity: u8,
    pub confidence: u8,
    pub urgency: u8,
    pub speech: Option<QuantizedSpeechTrackV1>,
    pub gaze: GazeIntentV1,
    pub gesture_hint: Option<GestureKind>,
    pub motion_profile: MotionProfile,
    pub deterministic_seed: u64,
    pub minimum_hold_ticks: u16,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ChatPerformanceIntent {
    pub schema_version: u16,
    pub command_id: CommandId,
    pub server_sequence: u64,
    pub apply_tick: u64,
    pub runtime_epoch: RuntimeEpoch,
    pub expires_tick: u64,
    pub turn_state: ChatTurnState,
    pub emotion: Emotion,
    pub intensity: u8,
    pub confidence: u8,
    pub urgency: u8,
    pub speech: Option<QuantizedSpeechTrackV1>,
    pub gaze: GazeIntentV1,
    pub gesture_hint: Option<GestureKind>,
    pub motion_profile: MotionProfile,
    pub deterministic_seed: u64,
    pub minimum_hold_ticks: u16,
}

#[derive(Clone, Debug, Error, Eq, PartialEq)]
pub enum PerformanceIntentError {
    #[error("unsupported performance intent schema {0}")]
    UnsupportedSchema(u16),
    #[error("{field} must be in 0..=100, got {value}")]
    OutOfRange { field: &'static str, value: u8 },
    #[error("expires_tick is exclusive and must cover apply_tick plus minimum_hold_ticks")]
    InvalidExpiry,
    #[error("performance intent expired at tick {expires_tick}; current tick is {current_tick}")]
    Expired {
        expires_tick: u64,
        current_tick: u64,
    },
    #[error("speech duration must be in 1..={MAX_SPEECH_TICKS} ticks")]
    InvalidSpeechDuration,
    #[error("speech contains {0} cues; maximum is {MAX_VISEME_CUES}")]
    TooManyVisemeCues(usize),
    #[error("viseme cue {index} has invalid bounds or strength")]
    InvalidVisemeCue { index: usize },
    #[error("viseme cue {index} overlaps or precedes the previous cue")]
    UnorderedVisemeCue { index: usize },
    #[error("speech marker {index} is out of order or outside the speech duration")]
    InvalidSpeechMarker { index: usize },
    #[error("invalid ingress speech plan: {0}")]
    InvalidIngressSpeech(#[from] ContractError),
}

impl ChatPerformanceIntent {
    #[must_use]
    pub fn from_command_envelope(
        envelope: &CommandEnvelopeV1,
        runtime_epoch: RuntimeEpoch,
        content: ChatPerformanceContentV1,
    ) -> Self {
        Self {
            schema_version: CHAT_PERFORMANCE_SCHEMA_VERSION,
            command_id: envelope.command_id.clone(),
            server_sequence: envelope.server_sequence,
            apply_tick: envelope.apply_tick,
            runtime_epoch,
            expires_tick: envelope.expires_tick,
            turn_state: content.turn_state,
            emotion: content.emotion,
            intensity: content.intensity,
            confidence: content.confidence,
            urgency: content.urgency,
            speech: content.speech,
            gaze: content.gaze,
            gesture_hint: content.gesture_hint,
            motion_profile: content.motion_profile,
            deterministic_seed: content.deterministic_seed,
            minimum_hold_ticks: content.minimum_hold_ticks,
        }
    }

    pub fn validate(&self) -> Result<(), PerformanceIntentError> {
        if self.schema_version != CHAT_PERFORMANCE_SCHEMA_VERSION {
            return Err(PerformanceIntentError::UnsupportedSchema(
                self.schema_version,
            ));
        }
        for (field, value) in [
            ("intensity", self.intensity),
            ("confidence", self.confidence),
            ("urgency", self.urgency),
        ] {
            if value > 100 {
                return Err(PerformanceIntentError::OutOfRange { field, value });
            }
        }
        if self.expires_tick
            < self
                .apply_tick
                .saturating_add(u64::from(self.minimum_hold_ticks))
        {
            return Err(PerformanceIntentError::InvalidExpiry);
        }
        if let Some(speech) = &self.speech {
            speech.validate()?;
        }
        Ok(())
    }

    pub fn validate_at(&self, current_tick: u64) -> Result<(), PerformanceIntentError> {
        self.validate()?;
        if current_tick >= self.expires_tick {
            return Err(PerformanceIntentError::Expired {
                expires_tick: self.expires_tick,
                current_tick,
            });
        }
        Ok(())
    }
}

impl QuantizedSpeechTrackV1 {
    pub fn validate(&self) -> Result<(), PerformanceIntentError> {
        if !(1..=MAX_SPEECH_TICKS).contains(&self.duration_ticks) {
            return Err(PerformanceIntentError::InvalidSpeechDuration);
        }
        if self.cues.len() > MAX_VISEME_CUES {
            return Err(PerformanceIntentError::TooManyVisemeCues(self.cues.len()));
        }

        let mut previous_end = 0;
        for (index, cue) in self.cues.iter().enumerate() {
            if cue.start_tick > cue.peak_tick
                || cue.peak_tick > cue.end_tick
                || cue.end_tick > self.duration_ticks
                || cue.strength > 100
                || cue.start_tick == cue.end_tick
            {
                return Err(PerformanceIntentError::InvalidVisemeCue { index });
            }
            if index > 0 && cue.start_tick < previous_end {
                return Err(PerformanceIntentError::UnorderedVisemeCue { index });
            }
            previous_end = cue.end_tick;
        }

        let mut previous_tick = 0;
        for (index, marker) in self.markers.iter().enumerate() {
            if marker.tick > self.duration_ticks || (index > 0 && marker.tick < previous_tick) {
                return Err(PerformanceIntentError::InvalidSpeechMarker { index });
            }
            previous_tick = marker.tick;
        }
        Ok(())
    }
}

pub fn quantize_speech_plan_v1(
    plan: &SpeechPlanV1,
) -> Result<QuantizedSpeechTrackV1, PerformanceIntentError> {
    plan.validate()?;
    let duration_ticks = milliseconds_to_ticks_half_up(plan.duration_ms).max(1);
    let cues = match plan.timing_source {
        TimingSource::TimedVisemes => quantize_timed_cues(plan, duration_ticks),
        TimingSource::DurationOnly => duration_fallback_cues(&plan.utterance_id, duration_ticks),
    };
    let markers = plan
        .markers
        .iter()
        .map(|marker| QuantizedSpeechMarkerV1 {
            tick: milliseconds_to_ticks_half_up(marker.at_ms).min(duration_ticks),
            kind: marker.kind,
        })
        .collect();
    let track = QuantizedSpeechTrackV1 {
        utterance_id: plan.utterance_id.clone(),
        duration_ticks,
        cues,
        markers,
    };
    track.validate()?;
    Ok(track)
}

#[must_use]
pub fn milliseconds_to_ticks_half_up(milliseconds: u32) -> u32 {
    let scaled = u64::from(milliseconds).saturating_mul(SIMULATION_HZ);
    let rounded = scaled.saturating_add(MILLIS_PER_SECOND / 2) / MILLIS_PER_SECOND;
    u32::try_from(rounded).unwrap_or(u32::MAX)
}

fn quantize_timed_cues(plan: &SpeechPlanV1, duration_ticks: u32) -> Vec<QuantizedVisemeCueV1> {
    let mut cues: Vec<QuantizedVisemeCueV1> = Vec::with_capacity(plan.cues.len());
    for source in &plan.cues {
        let mut start_tick =
            milliseconds_to_ticks_half_up(source.start_ms).min(duration_ticks.saturating_sub(1));
        let mut end_tick = milliseconds_to_ticks_half_up(source.end_ms).min(duration_ticks);
        if end_tick <= start_tick {
            end_tick = start_tick.saturating_add(1).min(duration_ticks);
        }

        if let Some(previous) = cues.last_mut() {
            if start_tick < previous.end_tick {
                if end_tick <= previous.end_tick {
                    if source.weight > previous.strength {
                        previous.viseme = source.viseme;
                        previous.strength = source.weight;
                    }
                    continue;
                }
                start_tick = previous.end_tick;
            }
        }
        if start_tick >= duration_ticks {
            if let Some(previous) = cues.last_mut() {
                if source.weight > previous.strength {
                    previous.viseme = source.viseme;
                    previous.strength = source.weight;
                }
            }
            continue;
        }
        end_tick = end_tick.max(start_tick + 1).min(duration_ticks);
        cues.push(QuantizedVisemeCueV1 {
            start_tick,
            peak_tick: midpoint_half_up(start_tick, end_tick),
            end_tick,
            viseme: source.viseme,
            strength: source.weight,
        });
    }
    cues
}

#[must_use]
pub fn duration_fallback_cues(
    utterance_id: &UtteranceId,
    duration_ticks: u32,
) -> Vec<QuantizedVisemeCueV1> {
    if duration_ticks == 0 {
        return Vec::new();
    }

    let seed = stable_seed(utterance_id.as_str().as_bytes());
    let base_span = 6 + u32::try_from(seed % 4).unwrap_or(0);
    let bounded_span = duration_ticks
        .div_ceil(MAX_VISEME_CUES as u32)
        .max(base_span);
    let open_visemes = [Viseme::A, Viseme::E, Viseme::O];
    let open_viseme = open_visemes[(seed as usize) % open_visemes.len()];
    let mut cues = Vec::new();
    let mut cursor = 0;
    let mut open = false;
    while cursor < duration_ticks {
        let end_tick = cursor.saturating_add(bounded_span).min(duration_ticks);
        cues.push(QuantizedVisemeCueV1 {
            start_tick: cursor,
            peak_tick: midpoint_half_up(cursor, end_tick),
            end_tick,
            viseme: if open { open_viseme } else { Viseme::Rest },
            strength: if open { 55 } else { 0 },
        });
        cursor = end_tick;
        open = !open;
    }
    cues
}

const fn midpoint_half_up(start: u32, end: u32) -> u32 {
    start + (end - start).div_ceil(2)
}

fn stable_seed(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
    }
    hash
}
