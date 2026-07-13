use std::time::Duration;
use wizard_avatar_engine::controller::{SIMULATION_DT, SIMULATION_HZ};
use wizard_avatar_engine::runtime::{AvatarRuntime, SimulationAccumulator, MAX_CATCH_UP_STEPS};

#[test]
fn wiz_pace_001_runtime_uses_exact_sixty_hertz_steps() {
    let mut runtime = AvatarRuntime::default();
    let mut observed_times = Vec::new();

    for _ in 0..120 {
        let before = runtime.current_state().time_seconds;
        runtime.step_tick();
        let after = runtime.current_state().time_seconds;
        observed_times.push(after - before);
    }

    assert_eq!(runtime.tick(), 120);
    assert_eq!(SIMULATION_HZ, 60.0);
    assert!(observed_times
        .iter()
        .all(|step| (*step - SIMULATION_DT).abs() <= f32::EPSILON * 8.0));
}

#[test]
fn wiz_pace_005_wall_accumulator_has_no_drift_for_irregular_elapsed_chunks() {
    let mut accumulator = SimulationAccumulator::default();
    let mut ticks = 0;
    for milliseconds in [7_u64, 11, 19, 3, 26, 14, 20].into_iter().cycle().take(700) {
        ticks += accumulator
            .advance(Duration::from_millis(milliseconds))
            .steps as u64;
    }
    let total_milliseconds = [7_u64, 11, 19, 3, 26, 14, 20]
        .into_iter()
        .cycle()
        .take(700)
        .sum::<u64>();
    let expected = (total_milliseconds as f64 / 1000.0 * 60.0).floor() as u64;
    assert_eq!(ticks, expected);
}

#[test]
fn wiz_pace_006_wall_accumulator_bounds_catch_up() {
    let mut accumulator = SimulationAccumulator::default();
    let advance = accumulator.advance(Duration::from_secs(5));
    assert_eq!(advance.steps, MAX_CATCH_UP_STEPS);
    assert!(advance.dropped_seconds > 4.8);
}

#[test]
fn wiz_pace_007_same_tick_commands_apply_in_deterministic_arrival_order() {
    let mut runtime = AvatarRuntime::default();
    runtime.schedule_command(
        3,
        wizard_avatar_engine::controller::WizardCommand::new(
            "expression",
            serde_json::json!({"expression": "happy"}),
        ),
    );
    runtime.schedule_command(
        3,
        wizard_avatar_engine::controller::WizardCommand::new(
            "expression",
            serde_json::json!({"expression": "focused"}),
        ),
    );
    for _ in 0..4 {
        runtime.step_tick();
    }
    assert_eq!(runtime.current_state().expression.as_str(), "focused");
}

#[test]
fn wiz_pace_001_viewer_count_and_render_sampling_never_advance_simulation() {
    let mut outcomes = Vec::new();
    for viewer_count in [0, 1, 2, 4, 8] {
        let mut runtime = AvatarRuntime::default();
        for _ in 0..120 {
            for _ in 0..viewer_count {
                let sample = runtime.snapshot();
                assert_eq!(sample.tick, runtime.tick());
                assert_eq!(
                    sample.current.time_seconds,
                    runtime.current_state().time_seconds
                );
            }
            runtime.step_tick();
        }
        outcomes.push((runtime.tick(), runtime.current_state().time_seconds));
    }
    assert!(outcomes.windows(2).all(|pair| pair[0] == pair[1]));
}
