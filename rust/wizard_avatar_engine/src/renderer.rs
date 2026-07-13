use crate::cell::{Cell, CellCanvas};
use crate::controller::{blink_state, fallback_speech_shape};
use crate::geometry::quantize_scale;
use crate::palette::{env, lerp_rgb, rgb, Rgb};
use crate::pose::{sample_pose, AnchorId, PointF, PoseSample};
use crate::projection::{project_world_to_screen, FLOOR_RATIO, HORIZON_RATIO};
use crate::state::{
    Action, EffectState, Expression, MouthShape, PlantedFoot, UpperBodyAction, WizardState,
};
use std::collections::BTreeMap;
use std::sync::{Mutex, OnceLock};

static BACKGROUND_CACHE: OnceLock<Mutex<BTreeMap<(usize, usize), CellCanvas>>> = OnceLock::new();

#[must_use]
pub fn project_quantized(x: f32, z: f32, width: usize, height: usize) -> (f32, f32, f32) {
    let (sx, sy, scale) = project_world_to_screen(x, z, width, height);
    (sx, sy, quantize_scale(scale))
}

#[must_use]
pub fn build_background(cols: usize, rows: usize) -> CellCanvas {
    let cache = BACKGROUND_CACHE.get_or_init(|| Mutex::new(BTreeMap::new()));
    if let Some(background) = cache
        .lock()
        .expect("background cache lock")
        .get(&(cols, rows))
        .cloned()
    {
        return background;
    }

    let mut canvas = CellCanvas::filled(cols, rows, Cell::new(b' ', env::BACKGROUND));
    let horizon = (rows as f32 * HORIZON_RATIO).round() as i32;
    let near = (rows as f32 * FLOOR_RATIO).round() as i32;
    for y in horizon..=near.min(rows as i32 - 1) {
        let depth = (y - horizon) as f32 / (near - horizon).max(1) as f32;
        let fade = 1.0 - depth.clamp(0.0, 1.0);
        let tile_h = (1.0 + depth * 5.0).round().max(1.0) as i32;
        let tile_w = (8.0 + depth * 16.0).round().max(5.0) as i32;
        let shift = ((0.5 - depth) * 4.0).round() as i32;
        for x in 0..cols as i32 {
            let relative_x = x - cols as i32 / 2 + shift;
            let tile_x = relative_x.div_euclid(tile_w);
            let tile_z = (y - horizon).div_euclid(tile_h);
            let grid = relative_x.rem_euclid(tile_w) == 0 || (y - horizon).rem_euclid(tile_h) == 0;
            let base = if grid {
                env::FLOOR_GRID
            } else if (tile_x + tile_z) % 2 == 0 {
                env::FLOOR_LIGHT
            } else {
                env::FLOOR_ALTERNATE
            };
            canvas.set(
                x,
                y,
                if grid || depth > 0.45 && (x + y) % 9 == 0 {
                    b'.'
                } else {
                    b' '
                },
                lerp_rgb(base, env::BACKGROUND, fade * 0.96),
            );
        }
    }
    cache
        .lock()
        .expect("background cache lock")
        .insert((cols, rows), canvas.clone());
    canvas
}

#[must_use]
pub fn render_stage(state: &WizardState, cols: usize, rows: usize) -> CellCanvas {
    let Ok(sample) = sample_pose(state) else {
        return build_background(cols, rows);
    };
    let mut stage = build_background(cols, rows);
    draw_contact_shadow(
        &mut stage,
        state.screen_position.x,
        state.screen_position.y,
        state.display_scale,
        state.planted_foot,
    );
    stage.blit_scaled(
        &sample.canvas,
        sample.root,
        (state.screen_position.x, state.screen_position.y),
        state.display_scale,
    );
    draw_pose_anchored_layers(&mut stage, state, &sample);
    stage
}

#[must_use]
pub fn render_wizard_local(state: &WizardState) -> CellCanvas {
    sample_pose(state)
        .map(|sample| sample.canvas)
        .unwrap_or_else(|_| CellCanvas::new(1, 1))
}

fn draw_pose_anchored_layers(stage: &mut CellCanvas, state: &WizardState, sample: &PoseSample) {
    draw_expression(stage, state, sample);
    draw_mouth(stage, state, sample);
    draw_action_and_effects(stage, state, sample);
}

fn draw_expression(stage: &mut CellCanvas, state: &WizardState, sample: &PoseSample) {
    let definition = expression_definition(state.expression);
    let blink = blink_state(state.time_seconds);
    let eye_glyph = match blink {
        "closed" => b'-',
        "half_closed" => b':',
        _ if definition.squint => b'-',
        _ => b'O',
    };
    for anchor in [AnchorId::LeftEye, AnchorId::RightEye] {
        set_at_anchor(
            stage,
            sample,
            state,
            anchor,
            (0.0, 0.0),
            eye_glyph,
            rgb::BLUE_MID,
        );
    }
    draw_brow(
        stage,
        sample,
        state,
        AnchorId::LeftEye,
        definition.left_brow,
        false,
    );
    draw_brow(
        stage,
        sample,
        state,
        AnchorId::RightEye,
        definition.right_brow,
        true,
    );
}

fn draw_brow(
    stage: &mut CellCanvas,
    sample: &PoseSample,
    state: &WizardState,
    anchor: AnchorId,
    kind: Brow,
    mirrored: bool,
) {
    let cells: &[(f32, f32, u8)] = match kind {
        Brow::Flat => &[(-1.0, -2.0, b'-'), (0.0, -2.0, b'-'), (1.0, -2.0, b'-')],
        Brow::Up => &[(-1.0, -1.0, b'/'), (0.0, -2.0, b'-'), (1.0, -2.0, b'-')],
        Brow::Down => &[(-1.0, -2.0, b'-'), (0.0, -1.0, b'-'), (1.0, -1.0, b'\\')],
        Brow::Pinched => &[(-1.0, -2.0, b'\\'), (0.0, -1.0, b'-'), (1.0, -1.0, b'/')],
        Brow::Tilt => &[(-1.0, -1.0, b'-'), (0.0, -2.0, b'-'), (1.0, -3.0, b'-')],
    };
    for &(dx, dy, glyph) in cells {
        set_at_anchor(
            stage,
            sample,
            state,
            anchor,
            (if mirrored { -dx } else { dx }, dy),
            glyph,
            rgb::BROWN_DARK,
        );
    }
}

fn draw_mouth(stage: &mut CellCanvas, state: &WizardState, sample: &PoseSample) {
    let definition = expression_definition(state.expression);
    let mouth = if state.speech_id.is_some() {
        fallback_speech_shape((state.speech_until - state.time_seconds).max(0.0))
    } else if state.mouth == MouthShape::Closed {
        definition.mouth
    } else {
        state.mouth
    };
    for &(dx, dy, glyph) in mouth_pattern(mouth) {
        set_at_anchor(
            stage,
            sample,
            state,
            AnchorId::Mouth,
            (dx, dy),
            glyph,
            if matches!(
                mouth,
                MouthShape::OpenSmall
                    | MouthShape::OpenMedium
                    | MouthShape::OpenWide
                    | MouthShape::Rounded
            ) {
                rgb::MAGENTA
            } else {
                rgb::BROWN_DARK
            },
        );
    }
}

fn draw_action_and_effects(stage: &mut CellCanvas, state: &WizardState, sample: &PoseSample) {
    let upper = if state.upper_body_action == UpperBodyAction::None {
        match state.action {
            Action::Explaining => UpperBodyAction::Explain,
            Action::Pointing => UpperBodyAction::Point,
            Action::Thinking => UpperBodyAction::Think,
            Action::MagicCast => UpperBodyAction::Cast,
            Action::Reaction => UpperBodyAction::React,
            Action::Idle | Action::Speaking | Action::Walking => UpperBodyAction::None,
        }
    } else {
        state.upper_body_action
    };
    match upper {
        UpperBodyAction::Explain => {
            for offset in [(-2.0, -2.0), (-3.0, 0.0), (-1.0, 2.0)] {
                set_at_anchor(
                    stage,
                    sample,
                    state,
                    AnchorId::LeftWrist,
                    offset,
                    b'+',
                    rgb::GOLD,
                );
            }
        }
        UpperBodyAction::Point => {
            for offset in [(1.0, 0.0), (2.0, 0.0), (3.0, -1.0)] {
                set_at_anchor(
                    stage,
                    sample,
                    state,
                    AnchorId::RightWrist,
                    offset,
                    b'>',
                    rgb::GOLD,
                );
            }
        }
        UpperBodyAction::Think => {
            for offset in [(0.0, -3.0), (2.0, -5.0), (4.0, -6.0)] {
                set_at_anchor(
                    stage,
                    sample,
                    state,
                    AnchorId::Head,
                    offset,
                    b'?',
                    rgb::BLUE_LIGHT,
                );
            }
        }
        UpperBodyAction::Cast => draw_magic(stage, state, sample),
        UpperBodyAction::React => {
            for offset in [(-3.0, -3.0), (0.0, -5.0), (3.0, -3.0)] {
                set_at_anchor(
                    stage,
                    sample,
                    state,
                    AnchorId::Head,
                    offset,
                    b'!',
                    rgb::MAGENTA,
                );
            }
        }
        UpperBodyAction::None => {}
    }
    if matches!(state.effect_state, EffectState::Cast) && upper != UpperBodyAction::Cast {
        draw_magic(stage, state, sample);
    }
}

fn draw_magic(stage: &mut CellCanvas, state: &WizardState, sample: &PoseSample) {
    let phase = (state.simulation_tick % 8) as usize;
    let pattern = [
        (-4.0, 0.0),
        (-3.0, -3.0),
        (0.0, -4.0),
        (3.0, -3.0),
        (4.0, 0.0),
        (3.0, 3.0),
        (0.0, 4.0),
        (-3.0, 3.0),
    ];
    for index in 0..8 {
        let offset = pattern[(index + phase) % pattern.len()];
        set_at_anchor(
            stage,
            sample,
            state,
            AnchorId::EffectOrigin,
            offset,
            b'*',
            if index % 3 != 0 {
                rgb::CYAN_MAGIC
            } else {
                rgb::GOLD
            },
        );
    }
}

fn set_at_anchor(
    stage: &mut CellCanvas,
    sample: &PoseSample,
    state: &WizardState,
    anchor: AnchorId,
    offset: (f32, f32),
    glyph: u8,
    color: Rgb,
) {
    let point = sample.anchors[&anchor];
    set_local(
        stage,
        sample,
        state,
        PointF {
            x: point.x + offset.0,
            y: point.y + offset.1,
        },
        glyph,
        color,
    );
}

fn set_local(
    stage: &mut CellCanvas,
    sample: &PoseSample,
    state: &WizardState,
    point: PointF,
    glyph: u8,
    color: Rgb,
) {
    let scale = state.display_scale;
    let origin_x = state.screen_position.x - sample.root.0 as f32 * scale;
    let origin_y = state.screen_position.y - sample.root.1 as f32 * scale;
    stage.set(
        (origin_x + point.x * scale).round() as i32,
        (origin_y + point.y * scale).round() as i32,
        glyph,
        color,
    );
}

fn draw_contact_shadow(
    stage: &mut CellCanvas,
    root_x: f32,
    root_y: f32,
    scale: f32,
    contact: PlantedFoot,
) {
    let width_factor = match contact {
        PlantedFoot::Both => 1.0,
        PlantedFoot::Left | PlantedFoot::Right => 0.82,
        PlantedFoot::None => 0.68,
    };
    let radius_x = (10.0 * scale * width_factor).round().max(2.0) as i32;
    let radius_y = (1.5 * scale).round().max(1.0) as i32;
    stage.ellipse(
        root_x.round() as i32,
        (root_y + scale.max(1.0)).round() as i32,
        radius_x,
        radius_y,
        b'.',
        env::CONTACT_SHADOW,
    );
}

#[derive(Clone, Copy)]
enum Brow {
    Flat,
    Up,
    Down,
    Pinched,
    Tilt,
}

#[derive(Clone, Copy)]
struct ExpressionDefinition {
    left_brow: Brow,
    right_brow: Brow,
    mouth: MouthShape,
    squint: bool,
}

fn expression_definition(expression: Expression) -> ExpressionDefinition {
    match expression {
        Expression::Neutral => ExpressionDefinition {
            left_brow: Brow::Flat,
            right_brow: Brow::Flat,
            mouth: MouthShape::Closed,
            squint: false,
        },
        Expression::Happy => ExpressionDefinition {
            left_brow: Brow::Up,
            right_brow: Brow::Up,
            mouth: MouthShape::Smile,
            squint: false,
        },
        Expression::Thinking => ExpressionDefinition {
            left_brow: Brow::Tilt,
            right_brow: Brow::Flat,
            mouth: MouthShape::Rounded,
            squint: true,
        },
        Expression::Surprised => ExpressionDefinition {
            left_brow: Brow::Up,
            right_brow: Brow::Up,
            mouth: MouthShape::OpenWide,
            squint: false,
        },
        Expression::Worried => ExpressionDefinition {
            left_brow: Brow::Up,
            right_brow: Brow::Down,
            mouth: MouthShape::Frown,
            squint: false,
        },
        Expression::Amused => ExpressionDefinition {
            left_brow: Brow::Tilt,
            right_brow: Brow::Up,
            mouth: MouthShape::Smile,
            squint: true,
        },
        Expression::Confident => ExpressionDefinition {
            left_brow: Brow::Flat,
            right_brow: Brow::Tilt,
            mouth: MouthShape::Smile,
            squint: true,
        },
        Expression::Focused => ExpressionDefinition {
            left_brow: Brow::Down,
            right_brow: Brow::Down,
            mouth: MouthShape::Closed,
            squint: true,
        },
        Expression::Skeptical => ExpressionDefinition {
            left_brow: Brow::Up,
            right_brow: Brow::Pinched,
            mouth: MouthShape::Frown,
            squint: true,
        },
        Expression::Explaining => ExpressionDefinition {
            left_brow: Brow::Up,
            right_brow: Brow::Flat,
            mouth: MouthShape::OpenMedium,
            squint: false,
        },
    }
}

fn mouth_pattern(shape: MouthShape) -> &'static [(f32, f32, u8)] {
    match shape {
        MouthShape::Closed => &[(0.0, 0.0, b'-')],
        MouthShape::OpenSmall => &[(0.0, 0.0, b'o')],
        MouthShape::OpenMedium => &[(-1.0, 0.0, b'('), (0.0, 1.0, b'_'), (1.0, 0.0, b')')],
        MouthShape::OpenWide => &[
            (-1.0, -1.0, b'('),
            (1.0, -1.0, b')'),
            (-1.0, 1.0, b'('),
            (1.0, 1.0, b')'),
        ],
        MouthShape::Rounded => &[(0.0, -1.0, b'O'), (0.0, 0.0, b'o')],
        MouthShape::Smile => &[(-1.0, 0.0, b'\\'), (0.0, 1.0, b'_'), (1.0, 0.0, b'/')],
        MouthShape::Frown => &[(-1.0, 1.0, b'/'), (0.0, 0.0, b'-'), (1.0, 1.0, b'\\')],
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn projection_depth_changes_scale() {
        let (_, _, near) = project_world_to_screen(0.0, 1.5, 480, 270);
        let (_, _, far) = project_world_to_screen(0.0, 10.0, 480, 270);
        assert!(near > far);
    }

    #[test]
    fn reference_stage_keeps_floor_and_direct_cells() {
        let mut state = WizardState::default();
        let (x, y, scale) = project_quantized(0.0, 5.0, 480, 270);
        state.screen_position.x = x;
        state.screen_position.y = y;
        state.display_scale = scale;
        let stage = render_stage(&state, 480, 270);
        assert_eq!(stage.width, 480);
        assert!(stage
            .to_frame_bytes()
            .chunks_exact(4)
            .any(|cell| cell[0] == b'#'));
        assert!(stage
            .to_frame_bytes()
            .chunks_exact(4)
            .any(|cell| cell[0] == b'.'));
    }
}
