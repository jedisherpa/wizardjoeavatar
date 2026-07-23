pub mod animation;
pub mod capability_manifest;
pub mod cell;
pub mod chat_event;
pub mod chat_performance;
pub mod codec;
pub mod command;
pub mod controller;
pub mod evidence;
pub mod frame_source;
pub mod geometry;
pub mod hub;
pub mod motion_catalog;
pub mod motion_graph;
pub mod newsroom;
pub mod newsroom_scene;
pub mod palette;
pub mod pathing;
pub mod performance_score;
pub mod pose;
pub mod pose_archive;
pub mod pose_asset;
pub mod pose_clip;
pub mod pose_graph_audit;
pub mod pose_graph_runtime;
pub mod pose_playback;
pub mod pose_program;
pub mod projection;
pub mod quality;
pub mod reference_avatar;
pub mod renderer;
pub mod runtime;
pub mod runtime_clock;
pub mod scene;
pub mod server;
pub mod state;

pub use codec::{
    decode_frame, encode_frame, encode_full_frame, CodecTag, EncodedFrame, KEYFRAME_INTERVAL,
};
pub use controller::{CommandResult, WizardAvatarController, WizardCommand};
pub use frame_source::{ProceduralWizardFrameSource, WizardCellFrame};
pub use state::{Action, Direction, Expression, MouthShape, WizardState};

pub const BUILD_GIT_SHA: &str = match option_env!("WIZARD_AVATAR_GIT_SHA") {
    Some(sha) => sha,
    None => "development",
};
