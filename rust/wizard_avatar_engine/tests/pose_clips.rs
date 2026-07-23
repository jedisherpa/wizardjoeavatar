use serde_json::json;
use std::collections::BTreeSet;
use wizard_avatar_engine::controller::{WizardAvatarController, WizardCommand};
use wizard_avatar_engine::pose_clip::POSE_CLIPS;
use wizard_avatar_engine::pose_graph_runtime::runtime_pose_graph_catalog;

fn command(
    controller: &mut WizardAvatarController,
    command_type: &str,
    payload: serde_json::Value,
) {
    let result = controller.apply_command(WizardCommand::new(command_type, payload));
    assert!(result.ok, "{}", result.message);
}

#[test]
fn rust_clips_resolve_every_step_against_the_replacement_catalog() {
    let catalog = runtime_pose_graph_catalog().expect("replacement pose graph catalog");
    let clip_ids = POSE_CLIPS
        .iter()
        .map(|clip| clip.id)
        .collect::<BTreeSet<_>>();
    assert_eq!(clip_ids.len(), POSE_CLIPS.len());

    let covered = POSE_CLIPS
        .iter()
        .flat_map(|clip| clip.steps.iter().map(|step| step.pose_id))
        .collect::<BTreeSet<_>>();
    for pose_id in covered {
        assert!(
            catalog.for_runtime_pose_id(pose_id).is_some(),
            "{pose_id} does not resolve to a promoted replacement graph"
        );
    }
    assert_eq!(catalog.manifest().entries.len(), 260);
    assert!(catalog
        .manifest()
        .entries
        .iter()
        .all(|entry| entry.primary_for_semantic_id && entry.exact_rgba_equal));
}

#[test]
fn one_shot_clip_restores_and_replacement_cancels_the_old_generation() {
    let mut controller = WizardAvatarController::default();
    command(&mut controller, "pose_clip", json!({"clip_id":"point"}));
    assert_eq!(
        controller.current_state().pose_clip_id.as_deref(),
        Some("point")
    );
    let first_generation = controller.current_state().pose_clip_generation;

    for _ in 0..180 {
        controller.step_tick();
        if controller.current_state().pose_clip_id.is_none()
            && controller.current_state().pose_id.is_none()
        {
            break;
        }
    }
    assert_eq!(controller.current_state().pose_clip_id, None);
    assert_eq!(controller.current_state().pose_id, None);

    command(
        &mut controller,
        "pose_clip",
        json!({"clip_id":"hover_flap", "loop":true}),
    );
    for _ in 0..24 {
        controller.step_tick();
    }
    let interrupted_pose = controller.current_state().pose_id.clone();
    let interrupted_blend = controller.current_state().pose_blend;
    assert_eq!(
        interrupted_blend, 1.0,
        "authored flight frames are exact cuts"
    );
    command(
        &mut controller,
        "pose_clip",
        json!({"clip_id":"staff_combo"}),
    );
    assert_eq!(
        controller.current_state().pose_clip_id.as_deref(),
        Some("staff_combo")
    );
    assert_eq!(
        controller.current_state().pose_id.as_deref(),
        Some("staff_grip_default")
    );
    assert_eq!(
        controller.current_state().previous_pose_id,
        interrupted_pose,
        "replacement must enter from the exact flight frame that was visible"
    );
    assert!(controller.current_state().pose_blend < 1.0);
    assert!(controller.current_state().pose_clip_generation > first_generation);

    let mut replacement_started = false;
    for _ in 0..180 {
        controller.step_tick();
        if controller.current_state().pose_clip_step == Some(0)
            && controller.current_state().pose_blend < 1.0
        {
            replacement_started = true;
            break;
        }
    }
    assert!(replacement_started, "replacement clip never started");
    assert_eq!(
        controller.current_state().previous_pose_id,
        interrupted_pose,
        "replacement must enter from the pose that actually completed"
    );

    command(
        &mut controller,
        "pose",
        json!({"pose_id":"idle_warm_camera_ready", "transition_ms":120}),
    );
    assert_eq!(controller.current_state().pose_clip_id, None);
}

#[test]
fn implicit_direction_restoration_survives_clip_replacement() {
    let mut controller = WizardAvatarController::default();
    command(&mut controller, "face", json!({"direction":"west"}));
    for _ in 0..90 {
        controller.step_tick();
        if controller.current_state().facing == wizard_avatar_engine::state::Direction::West {
            break;
        }
    }
    assert_eq!(
        controller.current_state().facing,
        wizard_avatar_engine::state::Direction::West
    );

    command(&mut controller, "pose_clip", json!({"clip_id":"point"}));
    for _ in 0..24 {
        controller.step_tick();
    }
    command(
        &mut controller,
        "pose_clip",
        json!({"clip_id":"reaction_recover"}),
    );
    for _ in 0..900 {
        controller.step_tick();
        if controller.current_state().pose_clip_id.is_none()
            && controller.current_state().pose_id.is_none()
        {
            break;
        }
    }

    assert_eq!(controller.current_state().pose_clip_id, None);
    assert_eq!(controller.current_state().pose_id, None);
    assert_eq!(
        controller.current_state().facing,
        wizard_avatar_engine::state::Direction::West
    );
}

#[test]
fn action_commands_use_the_same_rust_clip_scheduler() {
    let mut controller = WizardAvatarController::default();
    command(
        &mut controller,
        "action",
        json!({"action":"magic_cast", "duration_ms":1800}),
    );
    assert_eq!(
        controller.current_state().pose_clip_id.as_deref(),
        Some("staff_combo")
    );
    command(
        &mut controller,
        "action",
        json!({"action":"reaction", "duration_ms":1800}),
    );
    assert_eq!(
        controller.current_state().pose_clip_id.as_deref(),
        Some("reaction_recover")
    );
}

#[test]
fn raw_pose_commands_reject_retired_graph_ids() {
    let mut controller = WizardAvatarController::default();
    let retired = controller.apply_command(WizardCommand::new(
        "pose",
        json!({"pose_id":"front_idle_wings", "transition_ms":120}),
    ));
    assert!(!retired.ok);
    assert!(retired.message.contains("unsupported pose"));

    let retired_restore = controller.apply_command(WizardCommand::new(
        "pose_clip",
        json!({"clip_id":"point", "restore_pose_id":"front_idle_wings"}),
    ));
    assert!(!retired_restore.ok);
    assert!(retired_restore.message.contains("unsupported restore pose"));
}

#[test]
fn a_clip_enters_from_the_current_direction_pose() {
    let mut controller = WizardAvatarController::default();
    command(&mut controller, "pose_clip", json!({"clip_id":"point"}));

    controller.step_tick();
    let state = controller.current_state();
    assert_eq!(state.pose_id.as_deref(), Some("hand_point_screen_left"));
    assert_eq!(
        state.previous_pose_id.as_deref(),
        Some("idle_warm_camera_ready")
    );
    assert!(state.pose_blend < 1.0);
    assert!(!state.pose_handoff);
}

#[test]
fn idle_returns_through_the_direction_pose_before_clearing_the_override() {
    let mut controller = WizardAvatarController::default();
    command(&mut controller, "pose_clip", json!({"clip_id":"point"}));
    for _ in 0..180 {
        controller.step_tick();
        if controller.current_state().pose_blend >= 1.0 {
            break;
        }
    }
    assert_eq!(
        controller.current_state().pose_id.as_deref(),
        Some("hand_point_screen_left")
    );

    command(
        &mut controller,
        "action",
        json!({"action":"idle", "duration_ms":0}),
    );
    assert_eq!(
        controller.current_state().previous_pose_id.as_deref(),
        Some("hand_point_screen_left")
    );
    for _ in 0..180 {
        controller.step_tick();
        if controller.current_state().pose_id.is_none() {
            break;
        }
    }
    assert_eq!(controller.current_state().pose_id, None);
}
