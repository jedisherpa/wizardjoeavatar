use serde::{Deserialize, Serialize};
use std::str::FromStr;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Direction {
    South,
    #[serde(rename = "southwest")]
    SouthWest,
    West,
    #[serde(rename = "northwest")]
    NorthWest,
    North,
    #[serde(rename = "northeast")]
    NorthEast,
    East,
    #[serde(rename = "southeast")]
    SouthEast,
}

impl Direction {
    pub const ALL: [Self; 8] = [
        Self::South,
        Self::SouthWest,
        Self::West,
        Self::NorthWest,
        Self::North,
        Self::NorthEast,
        Self::East,
        Self::SouthEast,
    ];

    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::South => "south",
            Self::SouthWest => "southwest",
            Self::West => "west",
            Self::NorthWest => "northwest",
            Self::North => "north",
            Self::NorthEast => "northeast",
            Self::East => "east",
            Self::SouthEast => "southeast",
        }
    }

    #[must_use]
    pub fn rotate(self, steps: i32) -> Self {
        const ORDER: [Direction; 8] = [
            Direction::South,
            Direction::SouthWest,
            Direction::West,
            Direction::NorthWest,
            Direction::North,
            Direction::NorthEast,
            Direction::East,
            Direction::SouthEast,
        ];
        let idx = ORDER.iter().position(|item| *item == self).unwrap_or(0) as i32;
        ORDER[(idx + steps).rem_euclid(ORDER.len() as i32) as usize]
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContactMarker {
    #[default]
    LeftStance,
    LeftToeOff,
    LeftPassing,
    RightHeelStrike,
    RightStance,
    RightToeOff,
    RightPassing,
    LeftHeelStrike,
}

impl ContactMarker {
    #[must_use]
    pub fn from_phase(phase: f32) -> Self {
        match ((phase.rem_euclid(1.0) * 8.0).floor() as u8).min(7) {
            0 => Self::LeftStance,
            1 => Self::LeftToeOff,
            2 => Self::LeftPassing,
            3 => Self::RightHeelStrike,
            4 => Self::RightStance,
            5 => Self::RightToeOff,
            6 => Self::RightPassing,
            _ => Self::LeftHeelStrike,
        }
    }

    #[must_use]
    pub const fn planted_foot(self) -> PlantedFoot {
        match self {
            Self::LeftStance | Self::LeftToeOff | Self::LeftHeelStrike => PlantedFoot::Left,
            Self::RightStance | Self::RightToeOff | Self::RightHeelStrike => PlantedFoot::Right,
            Self::LeftPassing | Self::RightPassing => PlantedFoot::None,
        }
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PlantedFoot {
    #[default]
    None,
    Left,
    Right,
    Both,
}

impl FromStr for Direction {
    type Err = String;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "south" | "front" => Ok(Self::South),
            "southwest" | "front_left" | "front-left" => Ok(Self::SouthWest),
            "west" | "left" => Ok(Self::West),
            "northwest" | "back_left" | "back-left" => Ok(Self::NorthWest),
            "north" | "back" => Ok(Self::North),
            "northeast" | "back_right" | "back-right" => Ok(Self::NorthEast),
            "east" | "right" => Ok(Self::East),
            "southeast" | "front_right" | "front-right" => Ok(Self::SouthEast),
            other => Err(format!("unsupported direction: {other}")),
        }
    }
}

#[derive(Clone, Copy, Debug, Hash, Ord, PartialEq, Eq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Expression {
    Neutral,
    Happy,
    Thinking,
    Surprised,
    Worried,
    Amused,
    Confident,
    Focused,
    Skeptical,
    Explaining,
}

impl FromStr for Expression {
    type Err = String;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "neutral" => Ok(Self::Neutral),
            "happy" => Ok(Self::Happy),
            "thinking" => Ok(Self::Thinking),
            "surprised" => Ok(Self::Surprised),
            "worried" => Ok(Self::Worried),
            "amused" => Ok(Self::Amused),
            "confident" => Ok(Self::Confident),
            "focused" => Ok(Self::Focused),
            "skeptical" => Ok(Self::Skeptical),
            "explaining" => Ok(Self::Explaining),
            other => Err(format!("unsupported expression: {other}")),
        }
    }
}

impl Expression {
    pub const ALL: [Self; 10] = [
        Self::Neutral,
        Self::Happy,
        Self::Thinking,
        Self::Surprised,
        Self::Worried,
        Self::Amused,
        Self::Confident,
        Self::Focused,
        Self::Skeptical,
        Self::Explaining,
    ];

    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Neutral => "neutral",
            Self::Happy => "happy",
            Self::Thinking => "thinking",
            Self::Surprised => "surprised",
            Self::Worried => "worried",
            Self::Amused => "amused",
            Self::Confident => "confident",
            Self::Focused => "focused",
            Self::Skeptical => "skeptical",
            Self::Explaining => "explaining",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Action {
    Idle,
    Speaking,
    Explaining,
    Walking,
    Thinking,
    Pointing,
    MagicCast,
    Reaction,
}

impl Action {
    pub const ALL: [Self; 8] = [
        Self::Idle,
        Self::Speaking,
        Self::Explaining,
        Self::Walking,
        Self::Thinking,
        Self::Pointing,
        Self::MagicCast,
        Self::Reaction,
    ];

    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Idle => "idle",
            Self::Speaking => "speaking",
            Self::Explaining => "explaining",
            Self::Walking => "walking",
            Self::Thinking => "thinking",
            Self::Pointing => "pointing",
            Self::MagicCast => "magic_cast",
            Self::Reaction => "reaction",
        }
    }
}

impl FromStr for Action {
    type Err = String;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "idle" => Ok(Self::Idle),
            "speaking" => Ok(Self::Speaking),
            "explaining" => Ok(Self::Explaining),
            "walking" => Ok(Self::Walking),
            "thinking" => Ok(Self::Thinking),
            "pointing" => Ok(Self::Pointing),
            "magic_cast" | "cast" => Ok(Self::MagicCast),
            "reaction" | "react" => Ok(Self::Reaction),
            other => Err(format!("unsupported action: {other}")),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MouthShape {
    Closed,
    OpenSmall,
    OpenMedium,
    OpenWide,
    Rounded,
    Smile,
    Frown,
}

impl FromStr for MouthShape {
    type Err = String;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "closed" => Ok(Self::Closed),
            "open_small" => Ok(Self::OpenSmall),
            "open_medium" => Ok(Self::OpenMedium),
            "open_wide" => Ok(Self::OpenWide),
            "rounded" => Ok(Self::Rounded),
            "smile" => Ok(Self::Smile),
            "frown" => Ok(Self::Frown),
            other => Err(format!("unsupported mouth shape: {other}")),
        }
    }
}

#[derive(Clone, Copy, Debug, Hash, Ord, PartialEq, Eq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Locomotion {
    Idle,
    Walking,
    Turn,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SceneMode {
    #[default]
    Studio,
    NewsroomMain,
    NewsroomExplainer,
    NewsroomInterview,
    NewsroomBreaking,
    NewsroomProps,
    NewsroomOverlays,
    NewsroomCameraA,
    NewsroomCameraB,
}

impl FromStr for SceneMode {
    type Err = String;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "studio" => Ok(Self::Studio),
            "newsroom" | "newsroom_main" => Ok(Self::NewsroomMain),
            "newsroom_explainer" => Ok(Self::NewsroomExplainer),
            "newsroom_interview" => Ok(Self::NewsroomInterview),
            "newsroom_breaking" => Ok(Self::NewsroomBreaking),
            "newsroom_props" => Ok(Self::NewsroomProps),
            "newsroom_overlays" => Ok(Self::NewsroomOverlays),
            "newsroom_camera_a" => Ok(Self::NewsroomCameraA),
            "newsroom_camera_b" => Ok(Self::NewsroomCameraB),
            other => Err(format!("unsupported scene: {other}")),
        }
    }
}

impl Locomotion {
    pub const ALL: [Self; 3] = [Self::Idle, Self::Walking, Self::Turn];
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum UpperBodyAction {
    None,
    Explain,
    Point,
    Think,
    Cast,
    React,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StaffState {
    Held,
    Point,
    Cast,
    Rest,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EffectState {
    #[default]
    None,
    Cast,
    Reaction,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChannelGenerations {
    pub locomotion: u64,
    pub facing: u64,
    pub upper_body: u64,
    pub staff: u64,
    pub expression: u64,
    pub blink: u64,
    pub speech: u64,
    pub effects: u64,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct WorldPoint {
    pub x: f32,
    pub z: f32,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct Velocity {
    pub x: f32,
    pub z: f32,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct ScreenPoint {
    pub x: f32,
    pub y: f32,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WizardState {
    pub character_id: String,
    pub world_position: WorldPoint,
    pub velocity: Velocity,
    pub facing: Direction,
    pub previous_facing: Direction,
    pub facing_blend: f32,
    pub facing_pose_handoff: bool,
    pub locomotion: Locomotion,
    #[serde(default)]
    pub scene_mode: SceneMode,
    pub action: Action,
    pub previous_upper_body_action: UpperBodyAction,
    pub upper_body_action: UpperBodyAction,
    pub expression: Expression,
    pub mouth: MouthShape,
    pub walk_phase: f32,
    pub speed_ratio: f32,
    pub contact_marker: ContactMarker,
    pub planted_foot: PlantedFoot,
    #[serde(default)]
    pub pose_id: Option<String>,
    #[serde(default)]
    pub previous_pose_id: Option<String>,
    #[serde(default = "default_pose_blend")]
    pub pose_blend: f32,
    #[serde(default = "default_pose_handoff")]
    pub pose_handoff: bool,
    #[serde(default)]
    pub pose_generation: u64,
    #[serde(default)]
    pub pose_expires_at_tick: Option<u64>,
    #[serde(default)]
    pub pose_clip_id: Option<String>,
    #[serde(default)]
    pub pose_clip_step: Option<usize>,
    #[serde(default)]
    pub pose_clip_generation: u64,
    pub blink_phase: f32,
    pub staff_state: StaffState,
    pub previous_staff_state: StaffState,
    pub effect_state: EffectState,
    pub upper_body_blend: f32,
    pub staff_blend: f32,
    pub speech_id: Option<String>,
    pub time_seconds: f32,
    pub action_until: f32,
    pub speech_until: f32,
    pub target_point: Option<WorldPoint>,
    pub screen_position: ScreenPoint,
    pub display_scale: f32,
    pub simulation_tick: u64,
    pub desired_heading: f32,
    pub presented_heading: f32,
    pub pending_direction: Option<Direction>,
    pub direction_candidate_ticks: u8,
    pub channel_generations: ChannelGenerations,
    pub reconnect_count: u64,
}

impl Default for WizardState {
    fn default() -> Self {
        Self {
            character_id: "asciline-wizard-v1-rust".to_string(),
            world_position: WorldPoint { x: 0.0, z: 5.0 },
            velocity: Velocity { x: 0.0, z: 0.0 },
            facing: Direction::South,
            previous_facing: Direction::South,
            facing_blend: 1.0,
            facing_pose_handoff: true,
            locomotion: Locomotion::Idle,
            scene_mode: SceneMode::Studio,
            action: Action::Idle,
            previous_upper_body_action: UpperBodyAction::None,
            upper_body_action: UpperBodyAction::None,
            expression: Expression::Neutral,
            mouth: MouthShape::Closed,
            walk_phase: 0.0,
            speed_ratio: 0.0,
            contact_marker: ContactMarker::LeftStance,
            planted_foot: PlantedFoot::Both,
            pose_id: None,
            previous_pose_id: None,
            pose_blend: 1.0,
            pose_handoff: true,
            pose_generation: 0,
            pose_expires_at_tick: None,
            pose_clip_id: None,
            pose_clip_step: None,
            pose_clip_generation: 0,
            blink_phase: 0.0,
            staff_state: StaffState::Held,
            previous_staff_state: StaffState::Held,
            effect_state: EffectState::None,
            upper_body_blend: 0.0,
            staff_blend: 1.0,
            speech_id: None,
            time_seconds: 0.0,
            action_until: 0.0,
            speech_until: 0.0,
            target_point: None,
            screen_position: ScreenPoint::default(),
            display_scale: 1.0,
            simulation_tick: 0,
            desired_heading: 0.0,
            presented_heading: 0.0,
            pending_direction: None,
            direction_candidate_ticks: 0,
            channel_generations: ChannelGenerations::default(),
            reconnect_count: 0,
        }
    }
}

const fn default_pose_blend() -> f32 {
    1.0
}

const fn default_pose_handoff() -> bool {
    true
}
