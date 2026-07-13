use std::collections::VecDeque;
use std::sync::Arc;

pub const SIMULATION_HZ: u64 = 60;
pub const MAX_CATCH_UP_TICKS: u32 = 8;
pub const UNITS_PER_TICK: u128 = 1_000_000_000;

const UNITS_PER_NANOSECOND: u128 = SIMULATION_HZ as u128;

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct SimulationTime {
    ticks: u64,
}

impl SimulationTime {
    #[must_use]
    pub const fn from_ticks(ticks: u64) -> Self {
        Self { ticks }
    }

    #[must_use]
    pub const fn ticks(self) -> u64 {
        self.ticks
    }

    #[must_use]
    pub const fn whole_seconds(self) -> u64 {
        self.ticks / SIMULATION_HZ
    }

    #[must_use]
    pub const fn subsecond_ticks(self) -> u64 {
        self.ticks % SIMULATION_HZ
    }

    #[must_use]
    pub const fn accumulator_units(self) -> u128 {
        self.ticks as u128 * UNITS_PER_TICK
    }
}

pub trait FixedTickSemanticState: Clone + Send + Sync + 'static {
    fn step_tick(&mut self, tick: u64);

    fn semantic_hash(&self) -> [u8; 32];
}

#[derive(Clone, Debug)]
pub struct AvatarSnapshotV1<S> {
    simulation_time: SimulationTime,
    semantic_hash: [u8; 32],
    semantic_state: S,
}

impl<S> AvatarSnapshotV1<S> {
    #[must_use]
    pub const fn simulation_time(&self) -> SimulationTime {
        self.simulation_time
    }

    #[must_use]
    pub const fn tick(&self) -> u64 {
        self.simulation_time.ticks()
    }

    #[must_use]
    pub const fn semantic_hash(&self) -> &[u8; 32] {
        &self.semantic_hash
    }

    #[must_use]
    pub const fn semantic_state(&self) -> &S {
        &self.semantic_state
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct PresentationInterpolation {
    numerator_units: u128,
}

impl PresentationInterpolation {
    #[must_use]
    pub const fn from_accumulator_units(numerator_units: u128) -> Option<Self> {
        if numerator_units < UNITS_PER_TICK {
            Some(Self { numerator_units })
        } else {
            None
        }
    }

    #[must_use]
    pub const fn numerator_units(self) -> u128 {
        self.numerator_units
    }

    #[must_use]
    pub const fn denominator_units(self) -> u128 {
        UNITS_PER_TICK
    }

    #[must_use]
    pub fn as_f64(self) -> f64 {
        self.numerator_units as f64 / UNITS_PER_TICK as f64
    }
}

#[derive(Clone, Debug)]
pub struct PresentationSample<S> {
    previous: Arc<AvatarSnapshotV1<S>>,
    current: Arc<AvatarSnapshotV1<S>>,
    interpolation: PresentationInterpolation,
}

impl<S> PresentationSample<S> {
    #[must_use]
    pub fn previous(&self) -> &Arc<AvatarSnapshotV1<S>> {
        &self.previous
    }

    #[must_use]
    pub fn current(&self) -> &Arc<AvatarSnapshotV1<S>> {
        &self.current
    }

    #[must_use]
    pub const fn interpolation(&self) -> PresentationInterpolation {
        self.interpolation
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CatchUpDropped {
    pub at_monotonic_ns: u64,
    pub dropped_tick_count: u64,
    pub dropped_units: u128,
    pub dropped_monotonic_ns: u64,
    pub dropped_sub_nanosecond_units: u8,
    pub cumulative_dropped_monotonic_ns: u64,
    pub cumulative_dropped_sub_nanosecond_units: u8,
    pub catch_up_drop_count: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RuntimeClockEvent {
    CatchUpDropped(CatchUpDropped),
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct ClockAdvance {
    ticks_due: u32,
    interpolation: PresentationInterpolation,
    dropped: Option<CatchUpDropped>,
}

impl ClockAdvance {
    #[must_use]
    pub const fn ticks_due(self) -> u32 {
        self.ticks_due
    }

    #[must_use]
    pub const fn interpolation(self) -> PresentationInterpolation {
        self.interpolation
    }

    #[must_use]
    pub const fn dropped(self) -> Option<CatchUpDropped> {
        self.dropped
    }
}

#[derive(Clone, Debug, Default)]
pub struct RuntimeClock {
    last_monotonic_ns: Option<u64>,
    accumulator_units: u128,
    dropped_monotonic_ns: u64,
    catch_up_drop_count: u64,
    dropped_units: u128,
    events: VecDeque<RuntimeClockEvent>,
}

impl RuntimeClock {
    #[must_use]
    pub fn advance_wall_clock(&mut self, monotonic_ns: u64) -> ClockAdvance {
        let Some(previous_ns) = self.last_monotonic_ns else {
            self.last_monotonic_ns = Some(monotonic_ns);
            return ClockAdvance::default();
        };

        let effective_ns = monotonic_ns.max(previous_ns);
        self.last_monotonic_ns = Some(effective_ns);
        let elapsed_ns = effective_ns - previous_ns;
        let elapsed_units = u128::from(elapsed_ns) * UNITS_PER_NANOSECOND;
        let available_units = self.accumulator_units + elapsed_units;
        let available_ticks = available_units / UNITS_PER_TICK;
        let ticks_due = available_ticks.min(u128::from(MAX_CATCH_UP_TICKS)) as u32;
        let dropped_ticks = available_ticks - u128::from(ticks_due);
        let dropped_units = dropped_ticks * UNITS_PER_TICK;

        self.accumulator_units =
            available_units - dropped_units - u128::from(ticks_due) * UNITS_PER_TICK;

        let dropped = if dropped_units == 0 {
            None
        } else {
            self.dropped_units += dropped_units;
            self.dropped_monotonic_ns = (self.dropped_units / UNITS_PER_NANOSECOND) as u64;
            self.catch_up_drop_count += 1;

            let event = CatchUpDropped {
                at_monotonic_ns: effective_ns,
                dropped_tick_count: dropped_ticks as u64,
                dropped_units,
                dropped_monotonic_ns: (dropped_units / UNITS_PER_NANOSECOND) as u64,
                dropped_sub_nanosecond_units: (dropped_units % UNITS_PER_NANOSECOND) as u8,
                cumulative_dropped_monotonic_ns: self.dropped_monotonic_ns,
                cumulative_dropped_sub_nanosecond_units: (self.dropped_units % UNITS_PER_NANOSECOND)
                    as u8,
                catch_up_drop_count: self.catch_up_drop_count,
            };
            self.events
                .push_back(RuntimeClockEvent::CatchUpDropped(event));
            Some(event)
        };

        ClockAdvance {
            ticks_due,
            interpolation: PresentationInterpolation {
                numerator_units: self.accumulator_units,
            },
            dropped,
        }
    }

    #[must_use]
    pub const fn accumulator_units(&self) -> u128 {
        self.accumulator_units
    }

    #[must_use]
    pub const fn dropped_monotonic_ns(&self) -> u64 {
        self.dropped_monotonic_ns
    }

    #[must_use]
    pub const fn dropped_sub_nanosecond_units(&self) -> u8 {
        (self.dropped_units % UNITS_PER_NANOSECOND) as u8
    }

    #[must_use]
    pub const fn catch_up_drop_count(&self) -> u64 {
        self.catch_up_drop_count
    }

    pub fn drain_events(&mut self) -> Vec<RuntimeClockEvent> {
        self.events.drain(..).collect()
    }
}

#[derive(Clone, Debug)]
pub struct RuntimeAdvance<S> {
    clock: ClockAdvance,
    executed_snapshots: Vec<Arc<AvatarSnapshotV1<S>>>,
    snapshot: Arc<AvatarSnapshotV1<S>>,
    presentation: PresentationSample<S>,
}

impl<S> RuntimeAdvance<S> {
    #[must_use]
    pub const fn ticks_executed(&self) -> u32 {
        self.clock.ticks_due()
    }

    #[must_use]
    pub const fn clock(&self) -> ClockAdvance {
        self.clock
    }

    #[must_use]
    pub fn executed_snapshots(&self) -> &[Arc<AvatarSnapshotV1<S>>] {
        &self.executed_snapshots
    }

    #[must_use]
    pub fn snapshot(&self) -> &Arc<AvatarSnapshotV1<S>> {
        &self.snapshot
    }

    #[must_use]
    pub const fn presentation(&self) -> &PresentationSample<S> {
        &self.presentation
    }
}

#[derive(Clone, Debug)]
pub struct FixedTickRuntime<S> {
    clock: RuntimeClock,
    semantic_state: S,
    previous_snapshot: Arc<AvatarSnapshotV1<S>>,
    current_snapshot: Arc<AvatarSnapshotV1<S>>,
}

impl<S: FixedTickSemanticState> FixedTickRuntime<S> {
    #[must_use]
    pub fn new(semantic_state: S) -> Self {
        let initial = Arc::new(AvatarSnapshotV1 {
            simulation_time: SimulationTime::default(),
            semantic_hash: semantic_state.semantic_hash(),
            semantic_state: semantic_state.clone(),
        });
        Self {
            clock: RuntimeClock::default(),
            semantic_state,
            previous_snapshot: Arc::clone(&initial),
            current_snapshot: initial,
        }
    }

    #[must_use]
    pub fn step_tick(&mut self) -> Arc<AvatarSnapshotV1<S>> {
        let tick = self
            .current_snapshot
            .tick()
            .checked_add(1)
            .expect("simulation tick overflow");
        self.semantic_state.step_tick(tick);

        let snapshot = Arc::new(AvatarSnapshotV1 {
            simulation_time: SimulationTime::from_ticks(tick),
            semantic_hash: self.semantic_state.semantic_hash(),
            semantic_state: self.semantic_state.clone(),
        });
        self.previous_snapshot = Arc::clone(&self.current_snapshot);
        self.current_snapshot = Arc::clone(&snapshot);
        snapshot
    }

    #[must_use]
    pub fn advance_wall_clock(&mut self, monotonic_ns: u64) -> RuntimeAdvance<S> {
        let clock = self.clock.advance_wall_clock(monotonic_ns);
        let mut executed_snapshots = Vec::with_capacity(clock.ticks_due() as usize);
        for _ in 0..clock.ticks_due() {
            executed_snapshots.push(self.step_tick());
        }

        RuntimeAdvance {
            clock,
            executed_snapshots,
            snapshot: Arc::clone(&self.current_snapshot),
            presentation: self.presentation(clock.interpolation()),
        }
    }

    #[must_use]
    pub fn snapshot(&self) -> Arc<AvatarSnapshotV1<S>> {
        Arc::clone(&self.current_snapshot)
    }

    #[must_use]
    pub fn presentation(&self, interpolation: PresentationInterpolation) -> PresentationSample<S> {
        PresentationSample {
            previous: Arc::clone(&self.previous_snapshot),
            current: Arc::clone(&self.current_snapshot),
            interpolation,
        }
    }

    #[must_use]
    pub const fn clock(&self) -> &RuntimeClock {
        &self.clock
    }

    pub fn drain_runtime_events(&mut self) -> Vec<RuntimeClockEvent> {
        self.clock.drain_events()
    }
}
