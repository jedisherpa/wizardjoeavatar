use crate::codec::{encode_frame, CodecError, CodecTag, EncodedFrame, CELL_BYTES};
use crate::controller::{CommandResult, WizardAvatarController, WizardCommand};
use crate::pose::sample_pose;
use crate::projection::ProjectionHistory;
use crate::renderer::render_stage;
use crate::state::{ScreenPoint, WizardState};
use serde::Serialize;

pub const DEFAULT_COLS: usize = 480;
pub const DEFAULT_ROWS: usize = 270;
pub const DEFAULT_FPS: f32 = 24.0;

#[derive(Clone, Debug, Serialize)]
pub struct WizardCellFrame {
    pub cols: usize,
    pub rows: usize,
    pub frame_index: u32,
    #[serde(skip)]
    pub cells: Vec<u8>,
    pub raw_size: usize,
    pub changed_cells: usize,
    pub codec_tag: u8,
    pub encoded_size: usize,
    pub is_keyframe: bool,
}

#[derive(Clone, Debug, Serialize)]
pub struct FrameDiagnostics {
    pub fps: f32,
    pub frame_sequence: u32,
    pub codec_tag: u8,
    pub raw_frame_size: usize,
    pub encoded_frame_size: usize,
    pub delta_cell_count: usize,
    pub keyframe_count: u64,
    pub reconnect_count: u64,
    pub bandwidth_ratio: f32,
}

impl Default for FrameDiagnostics {
    fn default() -> Self {
        Self {
            fps: 24.0,
            frame_sequence: 0,
            codec_tag: 0,
            raw_frame_size: 0,
            encoded_frame_size: 0,
            delta_cell_count: 0,
            keyframe_count: 0,
            reconnect_count: 0,
            bandwidth_ratio: 0.0,
        }
    }
}

#[derive(Clone, Debug)]
pub struct ProceduralWizardFrameSource {
    pub cols: usize,
    pub rows: usize,
    pub fps: f32,
    controller: WizardAvatarController,
    frame_index: u32,
    prev_encoded_frame: Option<Vec<u8>>,
    diagnostics: FrameDiagnostics,
    projection: ProjectionHistory,
}

impl Default for ProceduralWizardFrameSource {
    fn default() -> Self {
        Self::new(DEFAULT_COLS, DEFAULT_ROWS, DEFAULT_FPS)
    }
}

impl ProceduralWizardFrameSource {
    #[must_use]
    pub fn new(cols: usize, rows: usize, fps: f32) -> Self {
        Self {
            cols,
            rows,
            fps,
            controller: WizardAvatarController::default(),
            frame_index: 0,
            prev_encoded_frame: None,
            diagnostics: FrameDiagnostics {
                fps,
                ..FrameDiagnostics::default()
            },
            projection: ProjectionHistory::default(),
        }
    }

    #[must_use]
    pub fn current_state(&self) -> &WizardState {
        self.controller.current_state()
    }

    #[must_use]
    pub fn diagnostics(&self) -> FrameDiagnostics {
        let mut diagnostics = self.diagnostics.clone();
        diagnostics.reconnect_count = self.current_state().reconnect_count;
        diagnostics
    }

    pub fn apply_command(&mut self, command: WizardCommand) -> CommandResult {
        let resets_state = command.command_type == "reset";
        if resets_state {
            self.prev_encoded_frame = None;
        }
        self.controller.apply_command(command)
    }

    pub fn next_frame(&mut self) -> WizardCellFrame {
        let state = self.controller.current_state().clone();
        self.sample_state(&state)
    }

    pub fn sample_state(&mut self, state: &WizardState) -> WizardCellFrame {
        let mut sampled_state = state.clone();
        let cells = if let Ok(pose) = sample_pose(&sampled_state) {
            let context = self
                .projection
                .project(&sampled_state, &pose, self.cols, self.rows);
            sampled_state.screen_position = ScreenPoint {
                x: context.quantized_root.0 as f32,
                y: context.quantized_root.1 as f32,
            };
            sampled_state.display_scale = context.quantized_scale;
            render_stage(&sampled_state, self.cols, self.rows).to_frame_bytes()
        } else {
            render_state_to_cells(&mut sampled_state, self.cols, self.rows)
        };
        WizardCellFrame {
            cols: self.cols,
            rows: self.rows,
            frame_index: self.frame_index,
            raw_size: cells.len(),
            cells,
            changed_cells: 0,
            codec_tag: 0,
            encoded_size: 0,
            is_keyframe: false,
        }
    }

    pub fn next_encoded_frame(
        &mut self,
        codec: &str,
    ) -> Result<(Vec<u8>, WizardCellFrame), CodecError> {
        let state = self.controller.current_state().clone();
        self.render_and_encode(&state, codec)
    }

    pub fn render_and_encode(
        &mut self,
        state: &WizardState,
        codec: &str,
    ) -> Result<(Vec<u8>, WizardCellFrame), CodecError> {
        let mut frame = self.sample_state(state);
        if codec == "adaptive" {
            let encoded = encode_frame(
                &frame.cells,
                self.prev_encoded_frame.as_deref(),
                frame.frame_index,
                CELL_BYTES,
            )?;
            self.prev_encoded_frame = Some(encoded.shown_frame.clone());
            apply_encoded_stats(&mut frame, &encoded);
            self.update_diagnostics(&frame);
            self.frame_index += 1;
            Ok((encoded.message, frame))
        } else {
            let mut message = Vec::with_capacity(4 + frame.cells.len());
            message.extend_from_slice(&frame.frame_index.to_be_bytes());
            message.extend_from_slice(&frame.cells);
            frame.codec_tag = CodecTag::Raw as u8;
            frame.encoded_size = message.len();
            frame.changed_cells = frame.raw_size / CELL_BYTES;
            self.prev_encoded_frame = Some(frame.cells.clone());
            self.update_diagnostics(&frame);
            self.frame_index += 1;
            Ok((message, frame))
        }
    }

    #[must_use]
    pub(crate) fn controller_clone(&self) -> WizardAvatarController {
        self.controller.clone()
    }

    fn update_diagnostics(&mut self, frame: &WizardCellFrame) {
        self.diagnostics.frame_sequence = frame.frame_index;
        self.diagnostics.codec_tag = frame.codec_tag;
        self.diagnostics.raw_frame_size = frame.raw_size;
        self.diagnostics.encoded_frame_size = frame.encoded_size;
        self.diagnostics.delta_cell_count = frame.changed_cells;
        self.diagnostics.fps = self.fps;
        if frame.is_keyframe {
            self.diagnostics.keyframe_count += 1;
        }
        self.diagnostics.bandwidth_ratio = if frame.raw_size > 0 {
            frame.encoded_size as f32 / frame.raw_size as f32
        } else {
            0.0
        };
    }
}

#[must_use]
pub fn render_state_to_cells(state: &mut WizardState, cols: usize, rows: usize) -> Vec<u8> {
    if let Ok(pose) = sample_pose(state) {
        let mut history = ProjectionHistory::default();
        let context = history.project(state, &pose, cols, rows);
        state.screen_position = ScreenPoint {
            x: context.quantized_root.0 as f32,
            y: context.quantized_root.1 as f32,
        };
        state.display_scale = context.quantized_scale;
    }
    render_stage(state, cols, rows).to_frame_bytes()
}

fn apply_encoded_stats(frame: &mut WizardCellFrame, encoded: &EncodedFrame) {
    frame.codec_tag = encoded.tag as u8;
    frame.changed_cells = encoded.changed_cells;
    frame.encoded_size = encoded.encoded_size;
    frame.is_keyframe = encoded.is_keyframe;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::codec::decode_frame;

    #[test]
    fn source_emits_direct_procedural_frame() {
        let mut source = ProceduralWizardFrameSource::default();
        let frame = source.next_frame();
        assert_eq!(frame.cells.len(), DEFAULT_COLS * DEFAULT_ROWS * CELL_BYTES);
        assert_eq!(frame.frame_index, 0);
        assert!(frame.cells.chunks_exact(4).any(|cell| cell[0] == b'#'));
    }

    #[test]
    fn encoded_frame_round_trips() {
        let mut source = ProceduralWizardFrameSource::default();
        let (message, frame) = source.next_encoded_frame("adaptive").expect("encode");
        let (index, decoded, _) = decode_frame(&message, None, CELL_BYTES).expect("decode");
        assert_eq!(index, frame.frame_index);
        assert_eq!(decoded, frame.cells);
    }

    #[test]
    fn reset_command_forces_fresh_keyframe() {
        let mut source = ProceduralWizardFrameSource::default();
        let _ = source.next_encoded_frame("adaptive").expect("first");
        let result = source.apply_command(WizardCommand::new("reset", serde_json::json!({})));
        assert!(result.ok, "{}", result.message);
        let (_message, frame) = source
            .next_encoded_frame("adaptive")
            .expect("after reset command");
        assert!(frame.is_keyframe);
    }
}
