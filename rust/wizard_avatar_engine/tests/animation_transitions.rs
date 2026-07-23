use serde_json::json;
use wizard_avatar_engine::controller::{WizardAvatarController, WizardCommand};
use wizard_avatar_engine::pose::{analyze_pose_topology, sample_pose, AnchorId};
use wizard_avatar_engine::state::{
    Direction, EffectState, StaffState, UpperBodyAction, WizardState,
};

fn command(controller: &mut WizardAvatarController, kind: &str, payload: serde_json::Value) {
    let result = controller.apply_command(WizardCommand::new(kind, payload));
    assert!(result.ok, "{}", result.message);
}

fn advance_until(
    controller: &mut WizardAvatarController,
    maximum_ticks: u64,
    condition: impl Fn(&WizardState) -> bool,
) {
    for _ in 0..maximum_ticks {
        if condition(controller.current_state()) {
            return;
        }
        controller.step_tick();
    }
    assert!(
        condition(controller.current_state()),
        "condition was not reached within {maximum_ticks} simulation ticks"
    );
}

#[test]
fn wiz_anim_003_speech_and_gesture_overlay_locomotion_without_restarting_phase() {
    let mut controller = WizardAvatarController::default();
    command(&mut controller, "move", json!({"x": 2.0, "z": 5.0}));
    controller.advance(0.4);
    let phase_before = controller.current_state().walk_phase;
    command(
        &mut controller,
        "speak",
        json!({"text": "Still walking", "duration_ms": 2000}),
    );
    command(
        &mut controller,
        "action",
        json!({"action": "pointing", "duration_ms": 900}),
    );
    controller.advance(0.2);
    let state = controller.current_state();
    assert!(state.walk_phase > phase_before);
    assert!(state.speech_id.is_some());
    assert_eq!(state.upper_body_action, UpperBodyAction::Point);
    assert_eq!(state.staff_state, StaffState::Point);
}

#[test]
fn wiz_anim_004_stale_expiry_cannot_cancel_replacement_and_reaction_restores() {
    let mut controller = WizardAvatarController::default();
    command(
        &mut controller,
        "action",
        json!({"action": "pointing", "duration_ms": 900}),
    );
    controller.advance(0.1);
    command(
        &mut controller,
        "action",
        json!({"action": "magic_cast", "duration_ms": 1200}),
    );
    controller.advance(0.9);
    assert_eq!(
        controller.current_state().upper_body_action,
        UpperBodyAction::Cast
    );

    command(
        &mut controller,
        "action",
        json!({"action": "pointing", "duration_ms": 1800}),
    );
    controller.advance(0.2);
    command(
        &mut controller,
        "action",
        json!({"action": "reaction", "duration_ms": 200}),
    );
    controller.advance(0.3);
    assert_eq!(
        controller.current_state().upper_body_action,
        UpperBodyAction::Point
    );
    assert_eq!(controller.current_state().staff_state, StaffState::Point);
}

#[test]
fn wiz_anim_005_root_and_same_pose_anchors_remain_continuous_through_gait_and_turns() {
    let mut state = wizard_avatar_engine::state::WizardState::default();
    let mut previous = sample_pose(&state).expect("initial pose");
    for direction in Direction::ALL {
        state.previous_facing = state.facing;
        state.facing = direction;
        state.facing_blend = 0.0;
        for step in 0..32 {
            state.facing_blend = (state.facing_blend + 1.0 / 8.0).min(1.0);
            state.walk_phase = step as f32 / 32.0;
            state.speed_ratio = 1.0;
            let sample = sample_pose(&state).expect("pose sample");
            assert_eq!(sample.root, sample.anchors[&AnchorId::ContactRoot].round());
            let topology = analyze_pose_topology(&sample);
            assert_eq!(topology.staff_components, 1, "{direction:?} step {step}");
            assert_eq!(topology.staff_scanline_gaps, 0, "{direction:?} step {step}");
            let previous_staff = previous.anchors[&AnchorId::StaffHand];
            let staff = sample.anchors[&AnchorId::StaffHand];
            let previous_root = previous.anchors[&AnchorId::Root];
            let root = sample.anchors[&AnchorId::Root];
            let previous_staff = (
                previous_staff.x - previous_root.x,
                previous_staff.y - previous_root.y,
            );
            let staff = (staff.x - root.x, staff.y - root.y);
            if previous.pose_id == sample.pose_id {
                assert!(
                    (staff.0 - previous_staff.0).abs() <= 6.0,
                    "{direction:?} step {step}: staff x {} -> {}",
                    previous_staff.0,
                    staff.0
                );
                assert!(
                    (staff.1 - previous_staff.1).abs() <= 6.0,
                    "{direction:?} step {step}: staff y {} -> {}",
                    previous_staff.1,
                    staff.1
                );
            }
            previous = sample;
        }
    }
}

#[test]
fn wiz_anim_007_direction_hysteresis_dwell_and_shortest_arc_are_deterministic() {
    let mut controller = WizardAvatarController::default();
    command(&mut controller, "face", json!({"direction": "southeast"}));
    for _ in 0..7 {
        controller.step_tick();
        assert_eq!(controller.current_state().facing, Direction::South);
    }
    assert_eq!(controller.current_state().direction_candidate_ticks, 1);
    controller.step_tick();
    assert_eq!(controller.current_state().facing, Direction::SouthEast);
    assert_eq!(controller.current_state().previous_facing, Direction::South);

    let mut shortest = WizardAvatarController::default();
    command(&mut shortest, "face", json!({"direction": "northwest"}));
    shortest.step_tick();
    assert!(shortest.current_state().presented_heading < 0.0);
    for _ in 0..120 {
        shortest.step_tick();
    }
    assert_eq!(shortest.current_state().facing, Direction::NorthWest);
}

#[test]
fn wiz_anim_008_action_transition_matrix_replaces_only_owned_generations() {
    let actions = [
        (
            "explaining",
            UpperBodyAction::Explain,
            StaffState::Held,
            EffectState::None,
        ),
        (
            "thinking",
            UpperBodyAction::Think,
            StaffState::Held,
            EffectState::None,
        ),
        (
            "pointing",
            UpperBodyAction::Point,
            StaffState::Point,
            EffectState::None,
        ),
        (
            "magic_cast",
            UpperBodyAction::Cast,
            StaffState::Cast,
            EffectState::Cast,
        ),
    ];
    for (source, _, _, _) in actions {
        for (target, upper, staff, effect) in actions {
            let mut controller = WizardAvatarController::default();
            command(
                &mut controller,
                "speak",
                json!({"text": "independent", "duration_ms": 3000}),
            );
            command(
                &mut controller,
                "action",
                json!({"action": source, "duration_ms": 1200}),
            );
            let before = controller.current_state().channel_generations;
            command(
                &mut controller,
                "action",
                json!({"action": target, "duration_ms": 1200}),
            );
            let state = controller.current_state();
            assert_eq!(state.upper_body_action, upper, "{source} -> {target}");
            assert_eq!(state.staff_state, staff, "{source} -> {target}");
            assert_eq!(state.effect_state, effect, "{source} -> {target}");
            assert!(state.channel_generations.upper_body > before.upper_body);
            assert!(state.channel_generations.staff > before.staff);
            assert!(state.channel_generations.effects > before.effects);
            assert_eq!(state.channel_generations.speech, before.speech);
            assert!(state.speech_id.is_some());
        }
    }
}

#[test]
fn authored_pose_channel_handoffs_replaces_and_restores_deterministically() {
    let mut controller = WizardAvatarController::default();
    command(
        &mut controller,
        "pose",
        json!({
            "pose_id": "staff_raise_vertical",
            "transition_ms": 200,
            "duration_ms": 1000,
            "restore_pose_id": "idle_warm_camera_ready"
        }),
    );
    let first_generation = controller.current_state().pose_generation;
    assert_eq!(
        controller.current_state().pose_id.as_deref(),
        Some("staff_raise_vertical")
    );
    assert!(!controller.current_state().pose_handoff);

    advance_until(&mut controller, 600, |state| state.pose_handoff);
    command(
        &mut controller,
        "pose",
        json!({
            "pose_id": "staff_aim_forward",
            "transition_ms": 200,
            "duration_ms": 300
        }),
    );
    advance_until(&mut controller, 600, |state| {
        state.pose_generation > first_generation
            && state.pose_id.as_deref() == Some("staff_aim_forward")
    });
    let replacement_generation = controller.current_state().pose_generation;
    advance_until(&mut controller, 600, |state| {
        state.pose_generation > replacement_generation
            && state.pose_id.as_deref() == Some("staff_raise_vertical")
    });
}
