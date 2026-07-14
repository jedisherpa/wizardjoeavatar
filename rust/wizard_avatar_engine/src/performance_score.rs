use crate::capability_manifest::{
    CapabilityCategoryV1, CapabilityEntryV1, CapabilityKind, CapabilityManifestV1,
    CapabilityStatus, LegacyClipCategoryV1, PropRequirementV1, QualityStatusV1,
};
use crate::motion_graph::ClipFamily;
use serde::de::Error as DeError;
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::cmp::Reverse;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

pub const PERFORMANCE_SCORE_SCHEMA_VERSION: u16 = 1;
pub const PERFORMANCE_SCORE_TIMEBASE_HZ: u32 = 1_000_000;
pub const MAX_SCORE_BYTES: usize = 64 * 1024 * 1024;
pub const MAX_SCORE_ID_BYTES: usize = 128;
pub const MAX_SCORE_DURATION_US: i64 = 604_800_000_000;
pub const MAX_SCORE_TRACKS: usize = 32;
pub const MAX_SCORE_CUES: usize = 100_000;
pub const MAX_SCORE_CHECKPOINTS: usize = 20_160;
pub const MAX_ACTIVE_CUES: usize = 4_096;
pub const MAX_FALLBACK_CAPABILITIES: usize = 4;
pub const MAX_LOCKED_LAYERS: usize = 8;
pub const MAX_TRANSITION_DURATION_US: i64 = 10_000_000;
pub const MAX_CHECKPOINT_GAP_US: i64 = 30_000_000;
pub const MAX_STAGE_MILLICELLS: i32 = 1_000_000;

pub type MediaTimestamp = i64;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ScoreErrorCode {
    MalformedJson,
    PayloadTooLarge,
    UnsupportedSchemaVersion,
    InvalidIdentifier,
    InvalidSha256,
    InvalidRange,
    InvalidScoreHash,
    InvalidOrder,
    DuplicateId,
    InvalidLayer,
    InvalidPayload,
    InvalidOverlap,
    InvalidFallback,
    InvalidCheckpoint,
    ManifestMismatch,
    UnknownCapability,
    InactiveCapability,
    UnderQualityCapability,
    IncompatibleCapability,
}

impl ScoreErrorCode {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::MalformedJson => "malformed_json",
            Self::PayloadTooLarge => "payload_too_large",
            Self::UnsupportedSchemaVersion => "unsupported_schema_version",
            Self::InvalidIdentifier => "invalid_identifier",
            Self::InvalidSha256 => "invalid_sha256",
            Self::InvalidRange => "invalid_range",
            Self::InvalidScoreHash => "invalid_score_hash",
            Self::InvalidOrder => "invalid_order",
            Self::DuplicateId => "duplicate_id",
            Self::InvalidLayer => "invalid_layer",
            Self::InvalidPayload => "invalid_payload",
            Self::InvalidOverlap => "invalid_overlap",
            Self::InvalidFallback => "invalid_fallback",
            Self::InvalidCheckpoint => "invalid_checkpoint",
            Self::ManifestMismatch => "manifest_mismatch",
            Self::UnknownCapability => "unknown_capability",
            Self::InactiveCapability => "inactive_capability",
            Self::UnderQualityCapability => "under_quality_capability",
            Self::IncompatibleCapability => "incompatible_capability",
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ScoreError {
    pub code: ScoreErrorCode,
    pub field: &'static str,
}

impl ScoreError {
    const fn new(code: ScoreErrorCode, field: &'static str) -> Self {
        Self { code, field }
    }
}

impl fmt::Display for ScoreError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}:{}", self.code.as_str(), self.field)
    }
}

impl std::error::Error for ScoreError {}

fn validate_bounded_text(value: &str) -> Result<(), ScoreError> {
    if value.is_empty() || value.len() > MAX_SCORE_ID_BYTES {
        return Err(ScoreError::new(
            ScoreErrorCode::InvalidIdentifier,
            "identifier",
        ));
    }
    Ok(())
}

macro_rules! bounded_string_type {
    ($name:ident) => {
        #[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
        pub struct $name(String);

        impl $name {
            pub fn new(value: impl Into<String>) -> Result<Self, ScoreError> {
                let value = value.into();
                validate_bounded_text(&value)?;
                Ok(Self(value))
            }

            pub fn as_str(&self) -> &str {
                &self.0
            }
        }

        impl Serialize for $name {
            fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
            where
                S: Serializer,
            {
                serializer.serialize_str(&self.0)
            }
        }

        impl<'de> Deserialize<'de> for $name {
            fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
            where
                D: Deserializer<'de>,
            {
                let value = String::deserialize(deserializer)?;
                Self::new(value).map_err(D::Error::custom)
            }
        }
    };
}

bounded_string_type!(MediaId);
bounded_string_type!(CharacterId);
bounded_string_type!(ArtifactVersion);
bounded_string_type!(CueId);
bounded_string_type!(TrackId);
bounded_string_type!(CapabilityId);

#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct Sha256Hex(String);

impl Sha256Hex {
    pub fn new(value: impl Into<String>) -> Result<Self, ScoreError> {
        let value = value.into();
        if value.len() != 64
            || !value
                .bytes()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        {
            return Err(ScoreError::new(ScoreErrorCode::InvalidSha256, "sha256"));
        }
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl Serialize for Sha256Hex {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&self.0)
    }
}

impl<'de> Deserialize<'de> for Sha256Hex {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        Self::new(value).map_err(D::Error::custom)
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ReducedMotionProfileV1 {
    Full,
    Reduced,
    Minimal,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DirectionV1 {
    South,
    Southwest,
    West,
    Northwest,
    North,
    Northeast,
    East,
    Southeast,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GazeTargetV1 {
    User,
    Content,
    Staff,
    Down,
    AwayLeft,
    AwayRight,
    Neutral,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ScoreEmotionV1 {
    Neutral,
    Joy,
    Sadness,
    Anger,
    Fear,
    Shame,
    Disgust,
    Surprise,
    Pride,
    Guilt,
    Love,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
#[allow(clippy::upper_case_acronyms)]
pub enum ScoreVisemeV1 {
    Rest,
    #[serde(rename = "mbp")]
    MBP,
    #[serde(rename = "fv")]
    FV,
    #[serde(rename = "th")]
    TH,
    #[serde(rename = "dtln")]
    DTLN,
    #[serde(rename = "kg")]
    KG,
    #[serde(rename = "chsh")]
    CHSH,
    #[serde(rename = "sz")]
    SZ,
    #[serde(rename = "r")]
    R,
    #[serde(rename = "a")]
    A,
    #[serde(rename = "e")]
    E,
    #[serde(rename = "i")]
    I,
    #[serde(rename = "o")]
    O,
    #[serde(rename = "u")]
    U,
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RegionLayerV1 {
    Mode,
    Root,
    Body,
    Gesture,
    Gaze,
    Face,
    Speech,
    Blink,
    PropEffect,
    SecondaryMotion,
    Stillness,
}

impl RegionLayerV1 {
    pub const ALL: [Self; 11] = [
        Self::Mode,
        Self::Root,
        Self::Body,
        Self::Gesture,
        Self::Gaze,
        Self::Face,
        Self::Speech,
        Self::Blink,
        Self::PropEffect,
        Self::SecondaryMotion,
        Self::Stillness,
    ];
}

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CueTypeV1 {
    Mode,
    Locomotion,
    BodyPose,
    Gesture,
    Gaze,
    Expression,
    Viseme,
    Blink,
    PropEffect,
    DancePhrase,
    Stillness,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PerformanceModeV1 {
    Audiobook,
    Music,
    MediaCompanion,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GesturePhaseV1 {
    Prepare,
    Stroke,
    Hold,
    Recover,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BlinkStateV1 {
    Open,
    Closing,
    Closed,
    Opening,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TransitionKindV1 {
    Cut,
    Linear,
    Authored,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ScoreProvenanceKindV1 {
    Manual,
    DeterministicCompiler,
    Imported,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScoreProvenanceV1 {
    pub kind: ScoreProvenanceKindV1,
    pub source_artifact_sha256: Sha256Hex,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScoreHeaderV1 {
    pub schema_version: u16,
    pub score_id: Sha256Hex,
    pub media_id: MediaId,
    pub media_sha256: Sha256Hex,
    pub character_id: CharacterId,
    pub capability_manifest_sha256: Sha256Hex,
    pub animation_library_sha256: Sha256Hex,
    pub motion_graph_sha256: Sha256Hex,
    pub transcript_version: ArtifactVersion,
    pub alignment_version: ArtifactVersion,
    pub analysis_version: ArtifactVersion,
    pub compiler_version: ArtifactVersion,
    pub validator_version: ArtifactVersion,
    pub duration_us: MediaTimestamp,
    pub timebase_hz: u32,
    pub seed: u64,
    pub reduced_motion_profile: ReducedMotionProfileV1,
    pub provenance: ScoreProvenanceV1,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TransitionSpecV1 {
    pub kind: TransitionKindV1,
    pub duration_us: MediaTimestamp,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum CuePayloadV1 {
    Mode {
        mode: PerformanceModeV1,
    },
    Locomotion {
        target_x_millicells: i32,
        target_y_millicells: i32,
        facing: DirectionV1,
        speed_percent: u8,
    },
    BodyPose {
        weight_shift_percent: u8,
    },
    Gesture {
        phase: GesturePhaseV1,
        intensity_percent: u8,
    },
    Gaze {
        target: GazeTargetV1,
        head_weight_percent: u8,
        eye_weight_percent: u8,
    },
    Expression {
        emotion: ScoreEmotionV1,
        intensity_percent: u8,
    },
    Viseme {
        viseme: ScoreVisemeV1,
        weight_percent: u8,
    },
    Blink {
        state: BlinkStateV1,
    },
    PropEffect {
        intensity_percent: u8,
    },
    DancePhrase {
        beat_phase_q32: u32,
        energy_percent: u8,
    },
    Stillness {
        locked_layers: Vec<RegionLayerV1>,
    },
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScoreCueV1 {
    pub cue_id: CueId,
    pub cue_type: CueTypeV1,
    pub start_us: MediaTimestamp,
    pub end_us: MediaTimestamp,
    pub layer: RegionLayerV1,
    pub priority: u16,
    pub capability_id: CapabilityId,
    pub fallback_capability_ids: Vec<CapabilityId>,
    pub transition_in: TransitionSpecV1,
    pub transition_out: TransitionSpecV1,
    pub payload: CuePayloadV1,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScoreTrackV1 {
    pub track_id: TrackId,
    pub layer: RegionLayerV1,
    pub cues: Vec<ScoreCueV1>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ActiveCueCheckpointV1 {
    pub cue_id: CueId,
    pub resolved_capability_id: CapabilityId,
    pub cue_local_time_us: MediaTimestamp,
    pub fallback_index: u8,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RegionCheckpointV1 {
    pub layer: RegionLayerV1,
    pub active_cues: Vec<ActiveCueCheckpointV1>,
    pub owner_generation: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScoreCheckpointV1 {
    pub at_us: MediaTimestamp,
    pub next_cue_indices: Vec<u32>,
    pub regions: Vec<RegionCheckpointV1>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PerformanceScoreV1 {
    pub header: ScoreHeaderV1,
    pub checkpoints: Vec<ScoreCheckpointV1>,
    pub tracks: Vec<ScoreTrackV1>,
}

impl PerformanceScoreV1 {
    pub fn from_json(input: &[u8]) -> Result<Self, ScoreError> {
        if input.len() > MAX_SCORE_BYTES {
            return Err(ScoreError::new(
                ScoreErrorCode::PayloadTooLarge,
                "performance_score",
            ));
        }
        let value: Value = serde_json::from_slice(input)
            .map_err(|_| ScoreError::new(ScoreErrorCode::MalformedJson, "performance_score"))?;
        reject_floating_point(&value)?;
        let score: Self = serde_json::from_value(value)
            .map_err(|_| ScoreError::new(ScoreErrorCode::MalformedJson, "performance_score"))?;
        score.validate()?;
        Ok(score)
    }

    pub fn from_json_with_manifest(
        input: &[u8],
        manifest: &CapabilityManifestV1,
    ) -> Result<Self, ScoreError> {
        let score = Self::from_json(input)?;
        score.validate_against_manifest(manifest)?;
        Ok(score)
    }

    pub fn validate(&self) -> Result<(), ScoreError> {
        self.validate_structure()?;
        if self.header.score_id != self.computed_score_id()? {
            return Err(ScoreError::new(
                ScoreErrorCode::InvalidScoreHash,
                "header.score_id",
            ));
        }
        Ok(())
    }

    pub fn validate_against_manifest(
        &self,
        manifest: &CapabilityManifestV1,
    ) -> Result<(), ScoreError> {
        self.validate_capabilities_against_manifest(manifest)?;
        if self.header.animation_library_sha256.as_str()
            != manifest.runtime_geometry_authority_sha256
            || self.header.motion_graph_sha256.as_str() != manifest.motion_graph_sha256
        {
            return Err(ScoreError::new(
                ScoreErrorCode::ManifestMismatch,
                "header.runtime_asset_binding",
            ));
        }
        Ok(())
    }

    pub fn validate_capabilities_against_manifest(
        &self,
        manifest: &CapabilityManifestV1,
    ) -> Result<(), ScoreError> {
        self.validate()?;
        manifest.validate().map_err(|_| {
            ScoreError::new(ScoreErrorCode::ManifestMismatch, "capability_manifest")
        })?;
        let manifest_sha = manifest.sha256().map_err(|_| {
            ScoreError::new(ScoreErrorCode::ManifestMismatch, "capability_manifest")
        })?;
        if self.header.character_id.as_str() != manifest.character_id
            || self.header.capability_manifest_sha256.as_str() != manifest_sha
        {
            return Err(ScoreError::new(
                ScoreErrorCode::ManifestMismatch,
                "header.capability_manifest_binding",
            ));
        }

        let capabilities = manifest
            .capabilities
            .iter()
            .map(|entry| (entry.id.as_str(), entry))
            .collect::<BTreeMap<_, _>>();
        for track in &self.tracks {
            for cue in &track.cues {
                validate_capability_for_cue(
                    cue,
                    &cue.capability_id,
                    &capabilities,
                    "cue.capability_id",
                )?;
                for fallback in &cue.fallback_capability_ids {
                    validate_capability_for_cue(
                        cue,
                        fallback,
                        &capabilities,
                        "cue.fallback_capability_ids",
                    )?;
                }
            }
        }
        Ok(())
    }

    pub fn canonical_json(&self) -> Result<Vec<u8>, ScoreError> {
        self.validate()?;
        canonical_json_value(
            serde_json::to_value(self)
                .map_err(|_| ScoreError::new(ScoreErrorCode::MalformedJson, "performance_score"))?,
        )
    }

    pub fn canonical_body_json(&self) -> Result<Vec<u8>, ScoreError> {
        self.validate_structure()?;
        let mut value = serde_json::to_value(self)
            .map_err(|_| ScoreError::new(ScoreErrorCode::MalformedJson, "performance_score"))?;
        value
            .get_mut("header")
            .and_then(Value::as_object_mut)
            .and_then(|header| header.remove("score_id"))
            .ok_or_else(|| ScoreError::new(ScoreErrorCode::MalformedJson, "header.score_id"))?;
        canonical_json_value(value)
    }

    pub fn computed_score_id(&self) -> Result<Sha256Hex, ScoreError> {
        Sha256Hex::new(format!("{:x}", Sha256::digest(self.canonical_body_json()?)))
    }

    pub fn recompute_score_id(&mut self) -> Result<(), ScoreError> {
        self.header.score_id = self.computed_score_id()?;
        Ok(())
    }

    pub fn checkpoint_at_or_before(
        &self,
        target_us: MediaTimestamp,
    ) -> Result<(usize, &ScoreCheckpointV1), ScoreError> {
        self.validate()?;
        if !(0..=self.header.duration_us).contains(&target_us) {
            return Err(ScoreError::new(
                ScoreErrorCode::InvalidRange,
                "seek.target_us",
            ));
        }
        let index = self
            .checkpoints
            .partition_point(|checkpoint| checkpoint.at_us <= target_us)
            .checked_sub(1)
            .ok_or_else(|| ScoreError::new(ScoreErrorCode::InvalidCheckpoint, "seek.checkpoint"))?;
        Ok((index, &self.checkpoints[index]))
    }

    fn validate_structure(&self) -> Result<(), ScoreError> {
        self.validate_header()?;
        if !(1..=MAX_SCORE_TRACKS).contains(&self.tracks.len()) {
            return Err(ScoreError::new(ScoreErrorCode::InvalidRange, "tracks"));
        }
        if !(1..=MAX_SCORE_CHECKPOINTS).contains(&self.checkpoints.len()) {
            return Err(ScoreError::new(ScoreErrorCode::InvalidRange, "checkpoints"));
        }
        self.validate_tracks_and_cues()?;
        self.validate_checkpoints()?;
        let canonical =
            canonical_json_value(serde_json::to_value(self).map_err(|_| {
                ScoreError::new(ScoreErrorCode::MalformedJson, "performance_score")
            })?)?;
        if canonical.len() > MAX_SCORE_BYTES {
            return Err(ScoreError::new(
                ScoreErrorCode::PayloadTooLarge,
                "performance_score",
            ));
        }
        Ok(())
    }

    fn validate_header(&self) -> Result<(), ScoreError> {
        if self.header.schema_version != PERFORMANCE_SCORE_SCHEMA_VERSION {
            return Err(ScoreError::new(
                ScoreErrorCode::UnsupportedSchemaVersion,
                "header.schema_version",
            ));
        }
        if self.header.timebase_hz != PERFORMANCE_SCORE_TIMEBASE_HZ {
            return Err(ScoreError::new(
                ScoreErrorCode::InvalidRange,
                "header.timebase_hz",
            ));
        }
        if !(1..=MAX_SCORE_DURATION_US).contains(&self.header.duration_us) {
            return Err(ScoreError::new(
                ScoreErrorCode::InvalidRange,
                "header.duration_us",
            ));
        }
        Ok(())
    }

    fn validate_tracks_and_cues(&self) -> Result<(), ScoreError> {
        let mut track_ids = BTreeSet::new();
        let mut cue_ids = BTreeSet::new();
        let mut total_cues = 0usize;
        let mut previous_track: Option<(RegionLayerV1, i64, Reverse<u16>, &str, &str)> = None;
        let mut overlap_groups: BTreeMap<(RegionLayerV1, u16), Vec<&ScoreCueV1>> = BTreeMap::new();
        let mut boundaries = Vec::new();

        for track in &self.tracks {
            if !track_ids.insert(track.track_id.as_str()) {
                return Err(ScoreError::new(
                    ScoreErrorCode::DuplicateId,
                    "track.track_id",
                ));
            }
            let first_cue = track
                .cues
                .first()
                .ok_or_else(|| ScoreError::new(ScoreErrorCode::InvalidRange, "track.cues"))?;
            let track_key = (
                track.layer,
                first_cue.start_us,
                Reverse(first_cue.priority),
                first_cue.cue_id.as_str(),
                track.track_id.as_str(),
            );
            if previous_track.is_some_and(|previous| previous >= track_key) {
                return Err(ScoreError::new(ScoreErrorCode::InvalidOrder, "tracks"));
            }
            previous_track = Some(track_key);
            let mut previous_cue: Option<(i64, Reverse<u16>, &str)> = None;
            for cue in &track.cues {
                total_cues = total_cues
                    .checked_add(1)
                    .ok_or_else(|| ScoreError::new(ScoreErrorCode::InvalidRange, "cues"))?;
                if total_cues > MAX_SCORE_CUES {
                    return Err(ScoreError::new(ScoreErrorCode::InvalidRange, "cues"));
                }
                if cue.layer != track.layer || cue.layer == RegionLayerV1::SecondaryMotion {
                    return Err(ScoreError::new(ScoreErrorCode::InvalidLayer, "cue.layer"));
                }
                if !cue_ids.insert(cue.cue_id.as_str()) {
                    return Err(ScoreError::new(ScoreErrorCode::DuplicateId, "cue.cue_id"));
                }
                let cue_key = (cue.start_us, Reverse(cue.priority), cue.cue_id.as_str());
                if previous_cue.is_some_and(|previous| previous >= cue_key) {
                    return Err(ScoreError::new(ScoreErrorCode::InvalidOrder, "track.cues"));
                }
                previous_cue = Some(cue_key);
                validate_cue(cue, self.header.duration_us)?;
                overlap_groups
                    .entry((cue.layer, cue.priority))
                    .or_default()
                    .push(cue);
                boundaries.push((cue.start_us, 1_i32));
                boundaries.push((cue.end_us, -1_i32));
            }
        }
        if total_cues == 0 {
            return Err(ScoreError::new(ScoreErrorCode::InvalidRange, "cues"));
        }

        for ((layer, _), cues) in overlap_groups {
            if layer == RegionLayerV1::PropEffect {
                continue;
            }
            let mut latest_end = -1;
            for cue in cues {
                if cue.start_us < latest_end {
                    return Err(ScoreError::new(
                        ScoreErrorCode::InvalidOverlap,
                        "cue.interval",
                    ));
                }
                latest_end = latest_end.max(cue.end_us);
            }
        }
        boundaries.sort_by_key(|(at_us, delta)| (*at_us, *delta));
        let mut active = 0_i32;
        for (_, delta) in boundaries {
            active = active
                .checked_add(delta)
                .ok_or_else(|| ScoreError::new(ScoreErrorCode::InvalidRange, "active_cues"))?;
            if active < 0 || active as usize > MAX_ACTIVE_CUES {
                return Err(ScoreError::new(ScoreErrorCode::InvalidRange, "active_cues"));
            }
        }
        self.validate_global_stillness_locks()
    }

    fn validate_global_stillness_locks(&self) -> Result<(), ScoreError> {
        let all_cues = self
            .tracks
            .iter()
            .flat_map(|track| &track.cues)
            .collect::<Vec<_>>();
        for cue in &all_cues {
            let CuePayloadV1::Stillness { locked_layers } = &cue.payload else {
                continue;
            };
            if cue.layer != RegionLayerV1::Stillness {
                continue;
            }
            let required = all_cues
                .iter()
                .filter(|other| {
                    other.cue_id != cue.cue_id
                        && other.start_us < cue.end_us
                        && cue.start_us < other.end_us
                        && !matches!(
                            other.layer,
                            RegionLayerV1::Mode
                                | RegionLayerV1::SecondaryMotion
                                | RegionLayerV1::Stillness
                        )
                })
                .map(|other| other.layer)
                .collect::<BTreeSet<_>>();
            if !required.iter().all(|layer| locked_layers.contains(layer)) {
                return Err(ScoreError::new(
                    ScoreErrorCode::InvalidPayload,
                    "payload.locked_layers",
                ));
            }
        }
        Ok(())
    }

    fn validate_checkpoints(&self) -> Result<(), ScoreError> {
        if self.checkpoints[0].at_us != 0 {
            return Err(ScoreError::new(
                ScoreErrorCode::InvalidCheckpoint,
                "checkpoints.first",
            ));
        }
        let cue_map = self
            .tracks
            .iter()
            .flat_map(|track| &track.cues)
            .map(|cue| (cue.cue_id.as_str(), cue))
            .collect::<BTreeMap<_, _>>();
        let mut previous_at = None;
        for checkpoint in &self.checkpoints {
            if checkpoint.at_us < 0 || checkpoint.at_us > self.header.duration_us {
                return Err(ScoreError::new(
                    ScoreErrorCode::InvalidCheckpoint,
                    "checkpoint.at_us",
                ));
            }
            if let Some(previous) = previous_at {
                if checkpoint.at_us <= previous
                    || checkpoint.at_us - previous > MAX_CHECKPOINT_GAP_US
                {
                    return Err(ScoreError::new(
                        ScoreErrorCode::InvalidCheckpoint,
                        "checkpoints.order",
                    ));
                }
            }
            previous_at = Some(checkpoint.at_us);
            self.validate_checkpoint(checkpoint, &cue_map)?;
        }
        let tail = self.header.duration_us - self.checkpoints.last().expect("non-empty").at_us;
        if tail > MAX_CHECKPOINT_GAP_US {
            return Err(ScoreError::new(
                ScoreErrorCode::InvalidCheckpoint,
                "checkpoints.coverage",
            ));
        }
        Ok(())
    }

    fn validate_checkpoint(
        &self,
        checkpoint: &ScoreCheckpointV1,
        cue_map: &BTreeMap<&str, &ScoreCueV1>,
    ) -> Result<(), ScoreError> {
        if checkpoint.next_cue_indices.len() != self.tracks.len()
            || checkpoint.regions.len() != RegionLayerV1::ALL.len()
        {
            return Err(ScoreError::new(
                ScoreErrorCode::InvalidCheckpoint,
                "checkpoint.shape",
            ));
        }
        for (track_index, track) in self.tracks.iter().enumerate() {
            let expected = track
                .cues
                .partition_point(|cue| cue.start_us <= checkpoint.at_us);
            if checkpoint.next_cue_indices[track_index] as usize != expected {
                return Err(ScoreError::new(
                    ScoreErrorCode::InvalidCheckpoint,
                    "checkpoint.next_cue_indices",
                ));
            }
        }

        let mut total_active = 0usize;
        for (index, region) in checkpoint.regions.iter().enumerate() {
            let layer = RegionLayerV1::ALL[index];
            if region.layer != layer {
                return Err(ScoreError::new(
                    ScoreErrorCode::InvalidCheckpoint,
                    "checkpoint.regions",
                ));
            }
            let expected = self.effective_active_cues(layer, checkpoint.at_us);
            if region.active_cues.len() != expected.len() {
                return Err(ScoreError::new(
                    ScoreErrorCode::InvalidCheckpoint,
                    "checkpoint.active_cues",
                ));
            }
            total_active = total_active
                .checked_add(region.active_cues.len())
                .ok_or_else(|| {
                    ScoreError::new(ScoreErrorCode::InvalidCheckpoint, "checkpoint.active_cues")
                })?;
            if total_active > MAX_ACTIVE_CUES {
                return Err(ScoreError::new(
                    ScoreErrorCode::InvalidCheckpoint,
                    "checkpoint.active_cues",
                ));
            }
            if region.active_cues.is_empty() {
                if region.owner_generation != 0 {
                    return Err(ScoreError::new(
                        ScoreErrorCode::InvalidCheckpoint,
                        "checkpoint.owner_generation",
                    ));
                }
                continue;
            }
            if region.owner_generation == 0 {
                return Err(ScoreError::new(
                    ScoreErrorCode::InvalidCheckpoint,
                    "checkpoint.owner_generation",
                ));
            }
            for (active, expected_cue) in region.active_cues.iter().zip(expected) {
                if active.cue_id.as_str() != expected_cue.cue_id.as_str()
                    || cue_map.get(active.cue_id.as_str()).copied() != Some(expected_cue)
                    || active.cue_local_time_us != checkpoint.at_us - expected_cue.start_us
                {
                    return Err(ScoreError::new(
                        ScoreErrorCode::InvalidCheckpoint,
                        "checkpoint.active_cues",
                    ));
                }
                let resolved = if active.fallback_index == 0 {
                    Some(&expected_cue.capability_id)
                } else {
                    expected_cue
                        .fallback_capability_ids
                        .get(usize::from(active.fallback_index) - 1)
                };
                if resolved != Some(&active.resolved_capability_id) {
                    return Err(ScoreError::new(
                        ScoreErrorCode::InvalidCheckpoint,
                        "checkpoint.fallback_index",
                    ));
                }
            }
        }
        Ok(())
    }

    fn effective_active_cues(
        &self,
        layer: RegionLayerV1,
        at_us: MediaTimestamp,
    ) -> Vec<&ScoreCueV1> {
        let mut active = self
            .tracks
            .iter()
            .filter(|track| track.layer == layer)
            .flat_map(|track| &track.cues)
            .filter(|cue| cue.start_us <= at_us && at_us < cue.end_us)
            .collect::<Vec<_>>();
        if layer == RegionLayerV1::PropEffect {
            active.sort_by(|left, right| left.cue_id.cmp(&right.cue_id));
            return active;
        }
        active
            .into_iter()
            .max_by(|left, right| {
                left.priority
                    .cmp(&right.priority)
                    .then_with(|| right.cue_id.cmp(&left.cue_id))
            })
            .into_iter()
            .collect()
    }
}

fn validate_cue(cue: &ScoreCueV1, duration_us: i64) -> Result<(), ScoreError> {
    if cue.start_us < 0 || cue.start_us >= cue.end_us || cue.end_us > duration_us {
        return Err(ScoreError::new(
            ScoreErrorCode::InvalidRange,
            "cue.interval",
        ));
    }
    validate_transition(&cue.transition_in)?;
    validate_transition(&cue.transition_out)?;
    if !(1..=MAX_FALLBACK_CAPABILITIES).contains(&cue.fallback_capability_ids.len()) {
        return Err(ScoreError::new(
            ScoreErrorCode::InvalidFallback,
            "cue.fallback_capability_ids",
        ));
    }
    let mut fallbacks = BTreeSet::new();
    for fallback in &cue.fallback_capability_ids {
        if fallback == &cue.capability_id || !fallbacks.insert(fallback.as_str()) {
            return Err(ScoreError::new(
                ScoreErrorCode::InvalidFallback,
                "cue.fallback_capability_ids",
            ));
        }
    }
    validate_payload(cue)
}

fn validate_transition(transition: &TransitionSpecV1) -> Result<(), ScoreError> {
    if !(0..=MAX_TRANSITION_DURATION_US).contains(&transition.duration_us)
        || (transition.kind == TransitionKindV1::Cut && transition.duration_us != 0)
    {
        return Err(ScoreError::new(
            ScoreErrorCode::InvalidRange,
            "cue.transition",
        ));
    }
    Ok(())
}

fn validate_percent(value: u8, field: &'static str) -> Result<(), ScoreError> {
    if value > 100 {
        return Err(ScoreError::new(ScoreErrorCode::InvalidRange, field));
    }
    Ok(())
}

fn validate_payload(cue: &ScoreCueV1) -> Result<(), ScoreError> {
    let matches = match &cue.payload {
        CuePayloadV1::Mode { .. } => {
            cue.cue_type == CueTypeV1::Mode && cue.layer == RegionLayerV1::Mode
        }
        CuePayloadV1::Locomotion {
            target_x_millicells,
            target_y_millicells,
            speed_percent,
            ..
        } => {
            validate_percent(*speed_percent, "payload.speed_percent")?;
            if !(-MAX_STAGE_MILLICELLS..=MAX_STAGE_MILLICELLS).contains(target_x_millicells)
                || !(-MAX_STAGE_MILLICELLS..=MAX_STAGE_MILLICELLS).contains(target_y_millicells)
            {
                return Err(ScoreError::new(
                    ScoreErrorCode::InvalidRange,
                    "payload.target_millicells",
                ));
            }
            cue.cue_type == CueTypeV1::Locomotion && cue.layer == RegionLayerV1::Root
        }
        CuePayloadV1::BodyPose {
            weight_shift_percent,
        } => {
            validate_percent(*weight_shift_percent, "payload.weight_shift_percent")?;
            cue.cue_type == CueTypeV1::BodyPose && cue.layer == RegionLayerV1::Body
        }
        CuePayloadV1::Gesture {
            intensity_percent, ..
        } => {
            validate_percent(*intensity_percent, "payload.intensity_percent")?;
            cue.cue_type == CueTypeV1::Gesture && cue.layer == RegionLayerV1::Gesture
        }
        CuePayloadV1::Gaze {
            head_weight_percent,
            eye_weight_percent,
            ..
        } => {
            validate_percent(*head_weight_percent, "payload.head_weight_percent")?;
            validate_percent(*eye_weight_percent, "payload.eye_weight_percent")?;
            cue.cue_type == CueTypeV1::Gaze && cue.layer == RegionLayerV1::Gaze
        }
        CuePayloadV1::Expression {
            intensity_percent, ..
        } => {
            validate_percent(*intensity_percent, "payload.intensity_percent")?;
            cue.cue_type == CueTypeV1::Expression && cue.layer == RegionLayerV1::Face
        }
        CuePayloadV1::Viseme { weight_percent, .. } => {
            validate_percent(*weight_percent, "payload.weight_percent")?;
            cue.cue_type == CueTypeV1::Viseme && cue.layer == RegionLayerV1::Speech
        }
        CuePayloadV1::Blink { .. } => {
            cue.cue_type == CueTypeV1::Blink && cue.layer == RegionLayerV1::Blink
        }
        CuePayloadV1::PropEffect { intensity_percent } => {
            validate_percent(*intensity_percent, "payload.intensity_percent")?;
            cue.cue_type == CueTypeV1::PropEffect && cue.layer == RegionLayerV1::PropEffect
        }
        CuePayloadV1::DancePhrase { energy_percent, .. } => {
            validate_percent(*energy_percent, "payload.energy_percent")?;
            cue.cue_type == CueTypeV1::DancePhrase && cue.layer == RegionLayerV1::Body
        }
        CuePayloadV1::Stillness { locked_layers } => {
            if locked_layers.len() > MAX_LOCKED_LAYERS
                || locked_layers.windows(2).any(|pair| pair[0] >= pair[1])
                || locked_layers.contains(&RegionLayerV1::Mode)
            {
                return Err(ScoreError::new(
                    ScoreErrorCode::InvalidPayload,
                    "payload.locked_layers",
                ));
            }
            cue.cue_type == CueTypeV1::Stillness
                && (cue.layer == RegionLayerV1::Stillness || locked_layers.contains(&cue.layer))
        }
    };
    if !matches {
        return Err(ScoreError::new(
            ScoreErrorCode::InvalidPayload,
            "cue.payload",
        ));
    }
    Ok(())
}

fn reject_floating_point(value: &Value) -> Result<(), ScoreError> {
    match value {
        Value::Number(number) if !(number.is_i64() || number.is_u64()) => Err(ScoreError::new(
            ScoreErrorCode::MalformedJson,
            "floating_point",
        )),
        Value::Array(values) => values.iter().try_for_each(reject_floating_point),
        Value::Object(values) => values.values().try_for_each(reject_floating_point),
        _ => Ok(()),
    }
}

fn canonical_json_value(value: Value) -> Result<Vec<u8>, ScoreError> {
    let value = canonicalize_value(value);
    let bytes = serde_json::to_vec(&value)
        .map_err(|_| ScoreError::new(ScoreErrorCode::MalformedJson, "performance_score"))?;
    if bytes.len() > MAX_SCORE_BYTES {
        return Err(ScoreError::new(
            ScoreErrorCode::PayloadTooLarge,
            "performance_score",
        ));
    }
    Ok(bytes)
}

fn canonicalize_value(value: Value) -> Value {
    match value {
        Value::Array(values) => Value::Array(values.into_iter().map(canonicalize_value).collect()),
        Value::Object(values) => {
            let mut entries = values.into_iter().collect::<Vec<_>>();
            entries.sort_by(|left, right| left.0.cmp(&right.0));
            Value::Object(
                entries
                    .into_iter()
                    .map(|(key, value)| (key, canonicalize_value(value)))
                    .collect(),
            )
        }
        other => other,
    }
}

fn validate_capability_for_cue(
    cue: &ScoreCueV1,
    capability_id: &CapabilityId,
    capabilities: &BTreeMap<&str, &CapabilityEntryV1>,
    field: &'static str,
) -> Result<(), ScoreError> {
    let capability = capabilities
        .get(capability_id.as_str())
        .copied()
        .ok_or_else(|| ScoreError::new(ScoreErrorCode::UnknownCapability, field))?;
    if capability.status != CapabilityStatus::ActiveLegacy {
        return Err(ScoreError::new(ScoreErrorCode::InactiveCapability, field));
    }
    if matches!(
        capability.quality_status,
        QualityStatusV1::RuntimeActiveUnscored
            | QualityStatusV1::ShadowValidatedNotRuntimeWired
            | QualityStatusV1::ContractValidatedNotRuntimeRendered
            | QualityStatusV1::ShowcaseApprovedNotGeneralPurpose
    ) {
        return Err(ScoreError::new(
            ScoreErrorCode::UnderQualityCapability,
            field,
        ));
    }
    if !capability_matches_cue(capability, cue.cue_type) {
        return Err(ScoreError::new(
            ScoreErrorCode::IncompatibleCapability,
            field,
        ));
    }
    Ok(())
}

fn capability_matches_cue(capability: &CapabilityEntryV1, cue_type: CueTypeV1) -> bool {
    match cue_type {
        CueTypeV1::Mode => capability.kind == CapabilityKind::ChatState,
        CueTypeV1::Locomotion => matches!(
            capability.category,
            CapabilityCategoryV1::RootMotion
                | CapabilityCategoryV1::PathMotion
                | CapabilityCategoryV1::LegacyClip(LegacyClipCategoryV1::GroundLocomotion)
                | CapabilityCategoryV1::MotionClip(ClipFamily::GroundLocomotion)
        ),
        CueTypeV1::BodyPose => matches!(
            capability.kind,
            CapabilityKind::Pose
                | CapabilityKind::PoseAlias
                | CapabilityKind::LegacyClip
                | CapabilityKind::MotionClip
        ),
        CueTypeV1::Gesture => matches!(
            capability.kind,
            CapabilityKind::GestureIntent | CapabilityKind::LegacyClip | CapabilityKind::MotionClip
        ),
        CueTypeV1::Gaze => capability.kind == CapabilityKind::GazeIntent,
        CueTypeV1::Expression => matches!(
            capability.kind,
            CapabilityKind::Expression | CapabilityKind::Emotion
        ),
        CueTypeV1::Viseme => matches!(
            capability.kind,
            CapabilityKind::MouthPose | CapabilityKind::VisemeIntent
        ),
        CueTypeV1::Blink => capability.category == CapabilityCategoryV1::BlinkFallback,
        CueTypeV1::PropEffect => capability.prop_requirements.iter().any(|requirement| {
            matches!(
                requirement,
                PropRequirementV1::EffectAllSamples | PropRequirementV1::EffectSomeSamples
            )
        }),
        CueTypeV1::DancePhrase => matches!(
            capability.kind,
            CapabilityKind::LegacyClip | CapabilityKind::MotionClip
        ),
        CueTypeV1::Stillness => matches!(
            capability.kind,
            CapabilityKind::Pose | CapabilityKind::PoseAlias
        ),
    }
}
