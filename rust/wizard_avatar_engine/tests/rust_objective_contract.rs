use serde_json::json;
use std::collections::BTreeSet;
use std::hash::{Hash, Hasher};
use wizard_avatar_engine::codec::{decode_frame, CodecTag, CELL_BYTES};
use wizard_avatar_engine::controller::{WizardAvatarController, WizardCommand};
use wizard_avatar_engine::frame_source::{
    render_state_to_cells, ProceduralWizardFrameSource, DEFAULT_COLS, DEFAULT_ROWS,
};
use wizard_avatar_engine::palette::rgb;
use wizard_avatar_engine::state::{
    Action, Direction, Expression, Locomotion, MouthShape, StaffState, UpperBodyAction, WizardState,
};

const COLS: usize = DEFAULT_COLS;
const ROWS: usize = DEFAULT_ROWS;

fn render(mut state: WizardState) -> Vec<u8> {
    render_state_to_cells(&mut state, COLS, ROWS)
}

fn base_state() -> WizardState {
    WizardState {
        facing: Direction::South,
        time_seconds: 1.0,
        ..WizardState::default()
    }
}

fn signature(bytes: &[u8]) -> u64 {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    bytes.hash(&mut hasher);
    hasher.finish()
}

fn count_rgb(bytes: &[u8], rgb: wizard_avatar_engine::palette::Rgb) -> usize {
    bytes
        .chunks_exact(CELL_BYTES)
        .filter(|cell| cell[1] == rgb.0 && cell[2] == rgb.1 && cell[3] == rgb.2)
        .count()
}

#[test]
fn rendered_frames_are_asciline_char_rgb_cells() {
    let frame = render(base_state());

    assert_eq!(frame.len(), COLS * ROWS * CELL_BYTES);
    assert_eq!(frame.len() % CELL_BYTES, 0);
    assert!(frame
        .chunks_exact(CELL_BYTES)
        .all(|cell| cell[0].is_ascii()));
    assert!(
        frame
            .chunks_exact(CELL_BYTES)
            .any(|cell| matches!(cell[0], b'@' | b'%' | b'#' | b'+')),
        "frame should contain visible wizard glyphs, not only environment cells"
    );
}

#[test]
fn all_expressions_and_mouth_shapes_affect_rendered_frames() {
    let expressions = [
        Expression::Neutral,
        Expression::Happy,
        Expression::Thinking,
        Expression::Surprised,
        Expression::Worried,
        Expression::Amused,
        Expression::Confident,
        Expression::Focused,
        Expression::Skeptical,
        Expression::Explaining,
    ];
    let expression_signatures = expressions
        .into_iter()
        .map(|expression| {
            let mut state = base_state();
            state.expression = expression;
            state.mouth = MouthShape::Closed;
            signature(&render(state))
        })
        .collect::<BTreeSet<_>>();
    assert_eq!(
        expression_signatures.len(),
        expressions.len(),
        "each public expression should produce a distinct visible frame"
    );

    let mouth_shapes = [
        MouthShape::Closed,
        MouthShape::OpenSmall,
        MouthShape::OpenMedium,
        MouthShape::OpenWide,
        MouthShape::Rounded,
        MouthShape::Smile,
        MouthShape::Frown,
    ];
    let mouth_signatures = mouth_shapes
        .into_iter()
        .map(|mouth| {
            let mut state = base_state();
            state.expression = Expression::Neutral;
            state.mouth = mouth;
            signature(&render(state))
        })
        .collect::<BTreeSet<_>>();
    assert_eq!(
        mouth_signatures.len(),
        mouth_shapes.len(),
        "each mouth shape should have a distinct rendered pose"
    );
}

#[test]
fn semantic_actions_drive_gesture_channels_and_visible_pose_changes() {
    let expected_channels = [
        (
            "explaining",
            Action::Explaining,
            UpperBodyAction::Explain,
            StaffState::Held,
        ),
        (
            "pointing",
            Action::Pointing,
            UpperBodyAction::Point,
            StaffState::Point,
        ),
        (
            "thinking",
            Action::Thinking,
            UpperBodyAction::Think,
            StaffState::Held,
        ),
        (
            "magic_cast",
            Action::MagicCast,
            UpperBodyAction::Cast,
            StaffState::Cast,
        ),
        (
            "reaction",
            Action::Reaction,
            UpperBodyAction::React,
            StaffState::Held,
        ),
    ];

    let mut controller = WizardAvatarController::default();
    for (name, action, upper, staff) in expected_channels {
        let result = controller.apply_command(WizardCommand::new(
            "action",
            json!({"action": name, "duration_ms": 1200}),
        ));
        assert!(result.ok, "{}", result.message);
        let state = controller.current_state();
        assert_eq!(state.action, action);
        assert_eq!(state.upper_body_action, upper);
        assert_eq!(state.staff_state, staff);
    }

    let idle = render(base_state());
    for action in [
        Action::Explaining,
        Action::Thinking,
        Action::Pointing,
        Action::MagicCast,
        Action::Reaction,
    ] {
        let mut state = base_state();
        state.action = action;
        assert_ne!(
            signature(&idle),
            signature(&render(state)),
            "{action:?} should visibly differ from idle"
        );
    }

    let mut walking = base_state();
    walking.action = Action::Walking;
    walking.locomotion = Locomotion::Walking;
    walking.walk_phase = 0.25;
    walking.speed_ratio = 1.0;
    walking.contact_marker = wizard_avatar_engine::state::ContactMarker::from_phase(0.25);
    assert_ne!(
        signature(&idle),
        signature(&render(walking)),
        "walking phase should visibly differ from idle"
    );

    let mut magic = base_state();
    magic.action = Action::MagicCast;
    magic.time_seconds = 1.17;
    assert!(
        count_rgb(&render(magic), rgb::CYAN_MAGIC) > count_rgb(&idle, rgb::CYAN_MAGIC) + 4,
        "magic cast should add visible cyan magic beyond the idle staff orb"
    );
}

#[test]
fn speaking_can_overlay_mouth_state_while_locomotion_continues() {
    let mut controller = WizardAvatarController::default();
    let move_result =
        controller.apply_command(WizardCommand::new("move", json!({"x": 2.0, "z": 5.0})));
    assert!(move_result.ok, "{}", move_result.message);

    let speak_result = controller.apply_command(WizardCommand::new(
        "speak",
        json!({"text": "The spell keeps walking while it talks.", "duration_ms": 1000}),
    ));
    assert!(speak_result.ok, "{}", speak_result.message);

    controller.advance(0.25);
    let state = controller.current_state();
    assert_eq!(state.locomotion, Locomotion::Walking);
    assert_eq!(state.action, Action::Speaking);
    assert_eq!(state.upper_body_action, UpperBodyAction::Explain);
    assert!(state.speech_id.is_some());
    assert_ne!(state.mouth, MouthShape::Closed);
}

#[test]
fn adaptive_stream_uses_keyframes_deltas_and_reset_resync() {
    let mut source = ProceduralWizardFrameSource::new(COLS, ROWS, 24.0);

    let (first_message, first_frame) = source.next_encoded_frame("adaptive").expect("first frame");
    assert!(first_frame.is_keyframe);
    let (first_index, decoded_first, first_tag) =
        decode_frame(&first_message, None, CELL_BYTES).expect("decode first");
    assert_eq!(first_index, 0);
    assert_eq!(decoded_first, first_frame.cells);
    assert!(matches!(
        first_tag,
        CodecTag::Raw | CodecTag::Zlib | CodecTag::RleFull
    ));

    let (second_message, second_frame) =
        source.next_encoded_frame("adaptive").expect("second frame");
    assert!(!second_frame.is_keyframe);
    let (second_index, decoded_second, second_tag) =
        decode_frame(&second_message, Some(&decoded_first), CELL_BYTES).expect("decode second");
    assert_eq!(second_index, 1);
    assert_eq!(decoded_second, second_frame.cells);
    assert_eq!(second_tag, CodecTag::Delta);

    let reset_result = source.apply_command(WizardCommand::new("reset", json!({})));
    assert!(reset_result.ok, "{}", reset_result.message);
    let (reset_message, reset_frame) = source.next_encoded_frame("adaptive").expect("reset frame");
    assert!(reset_frame.is_keyframe);
    let (_reset_index, decoded_reset, _reset_tag) =
        decode_frame(&reset_message, None, CELL_BYTES).expect("decode reset keyframe");
    assert_eq!(decoded_reset, reset_frame.cells);
}
