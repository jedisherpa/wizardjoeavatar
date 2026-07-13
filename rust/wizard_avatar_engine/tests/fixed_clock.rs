use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::sync::Arc;
use wizard_avatar_engine::runtime_clock::{
    CatchUpDropped, FixedTickRuntime, FixedTickSemanticState, PresentationInterpolation,
    RuntimeClockEvent, MAX_CATCH_UP_TICKS, SIMULATION_HZ, UNITS_PER_TICK,
};

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct ScriptedState {
    ticks: u64,
    phase: u64,
    position: i64,
    energy: u64,
}

impl FixedTickSemanticState for ScriptedState {
    fn step_tick(&mut self, tick: u64) {
        self.ticks = tick;
        self.phase = (self.phase + tick * 17 + 3) % 4_093;
        self.position += (tick % 7) as i64 - 3;
        self.energy = self.energy.wrapping_mul(33).wrapping_add(tick ^ 0x5a5a);
    }

    fn semantic_hash(&self) -> [u8; 32] {
        let mut digest = Sha256::new();
        digest.update(self.ticks.to_le_bytes());
        digest.update(self.phase.to_le_bytes());
        digest.update(self.position.to_le_bytes());
        digest.update(self.energy.to_le_bytes());
        digest.finalize().into()
    }
}

fn run_wall_partitions(
    partitions_ns: &[u64],
) -> (FixedTickRuntime<ScriptedState>, BTreeMap<u64, [u8; 32]>) {
    let mut runtime = FixedTickRuntime::new(ScriptedState::default());
    let baseline = runtime.advance_wall_clock(0);
    assert_eq!(baseline.ticks_executed(), 0);

    let mut monotonic_ns = 0_u64;
    let mut hashes = BTreeMap::new();
    for elapsed_ns in partitions_ns {
        monotonic_ns += elapsed_ns;
        let advance = runtime.advance_wall_clock(monotonic_ns);
        assert!(advance.clock().dropped().is_none());
        for snapshot in advance.executed_snapshots() {
            hashes.insert(snapshot.tick(), *snapshot.semantic_hash());
        }
    }
    (runtime, hashes)
}

fn sampling_partitions(fps: u64, seconds: u64) -> Vec<u64> {
    let frame_count = fps * seconds;
    let mut previous_ns = 0_u64;
    (1..=frame_count)
        .map(|frame| {
            let monotonic_ns = frame * seconds * 1_000_000_000 / frame_count;
            let elapsed_ns = monotonic_ns - previous_ns;
            previous_ns = monotonic_ns;
            elapsed_ns
        })
        .collect()
}

#[test]
fn sixty_thousand_ticks_are_exactly_one_thousand_simulated_seconds() {
    let mut runtime = FixedTickRuntime::new(ScriptedState::default());
    for _ in 0..60_000 {
        let _ = runtime.step_tick();
    }

    let snapshot = runtime.snapshot();
    assert_eq!(snapshot.tick(), 60_000);
    assert_eq!(snapshot.simulation_time().whole_seconds(), 1_000);
    assert_eq!(snapshot.simulation_time().subsecond_ticks(), 0);
    assert_eq!(
        snapshot.simulation_time().accumulator_units(),
        60_000 * UNITS_PER_TICK
    );
    assert_eq!(snapshot.semantic_state().ticks, 60_000);
    assert_eq!(SIMULATION_HZ, 60);
}

#[test]
fn equal_elapsed_nanosecond_partitions_produce_equal_semantics_and_hashes() {
    let uniform = vec![10_000_000; 100];
    let irregular = [7_u64, 11, 19, 3, 26, 14, 20]
        .into_iter()
        .cycle()
        .take(70)
        .map(|milliseconds| milliseconds * 1_000_000)
        .collect::<Vec<_>>();
    assert_eq!(uniform.iter().sum::<u64>(), irregular.iter().sum::<u64>());

    let (uniform_runtime, uniform_hashes) = run_wall_partitions(&uniform);
    let (irregular_runtime, irregular_hashes) = run_wall_partitions(&irregular);

    assert_eq!(uniform_hashes, irregular_hashes);
    assert_eq!(uniform_hashes.len(), 60);
    assert_eq!(
        uniform_runtime.snapshot().semantic_state(),
        irregular_runtime.snapshot().semantic_state()
    );
    assert_eq!(
        uniform_runtime.snapshot().semantic_hash(),
        irregular_runtime.snapshot().semantic_hash()
    );
}

#[test]
fn presentation_sampling_rates_do_not_change_common_tick_hashes() {
    let (_, expected_hashes) = run_wall_partitions(&sampling_partitions(60, 3));
    assert_eq!(expected_hashes.len(), 180);

    for fps in [15_u64, 24, 30, 60] {
        let (runtime, hashes) = run_wall_partitions(&sampling_partitions(fps, 3));
        assert_eq!(hashes, expected_hashes, "semantic drift at {fps} FPS");
        assert_eq!(runtime.snapshot().tick(), 180);
    }
}

#[test]
fn two_second_stall_caps_ticks_and_records_exact_dropped_time() {
    fn stalled_run() -> (CatchUpDropped, Vec<RuntimeClockEvent>, [u8; 32]) {
        let mut runtime = FixedTickRuntime::new(ScriptedState::default());
        let _ = runtime.advance_wall_clock(1_000_000);
        let advance = runtime.advance_wall_clock(2_001_000_000);

        assert_eq!(advance.ticks_executed(), MAX_CATCH_UP_TICKS);
        assert_eq!(advance.executed_snapshots().len(), 8);
        assert_eq!(advance.snapshot().tick(), 8);
        assert_eq!(advance.clock().interpolation().numerator_units(), 0);
        assert_eq!(runtime.clock().catch_up_drop_count(), 1);
        assert_eq!(runtime.clock().dropped_monotonic_ns(), 1_866_666_666);
        assert_eq!(runtime.clock().dropped_sub_nanosecond_units(), 40);

        (
            advance.clock().dropped().expect("stall must drop time"),
            runtime.drain_runtime_events(),
            *advance.snapshot().semantic_hash(),
        )
    }

    let first = stalled_run();
    let second = stalled_run();
    assert_eq!(first, second);

    assert_eq!(first.0.dropped_tick_count, 112);
    assert_eq!(first.0.dropped_units, 112 * UNITS_PER_TICK);
    assert_eq!(first.0.dropped_monotonic_ns, 1_866_666_666);
    assert_eq!(first.0.dropped_sub_nanosecond_units, 40);
    assert_eq!(first.1, vec![RuntimeClockEvent::CatchUpDropped(first.0)]);
}

#[test]
fn presentation_interpolation_only_reads_immutable_arc_snapshots() {
    let mut runtime = FixedTickRuntime::new(ScriptedState::default());
    let initial = runtime.snapshot();
    let current = runtime.step_tick();
    let hash_before_sampling = *current.semantic_hash();
    let interpolation =
        PresentationInterpolation::from_accumulator_units(UNITS_PER_TICK / 2).unwrap();

    let sample = runtime.presentation(interpolation);
    assert!(Arc::ptr_eq(sample.previous(), &initial));
    assert!(Arc::ptr_eq(sample.current(), &current));
    assert_eq!(sample.interpolation().numerator_units(), UNITS_PER_TICK / 2);
    assert_eq!(sample.interpolation().denominator_units(), UNITS_PER_TICK);
    assert_eq!(sample.interpolation().as_f64(), 0.5);
    assert_eq!(runtime.snapshot().semantic_hash(), &hash_before_sampling);
}
