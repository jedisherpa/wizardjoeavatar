use crate::codec::{encode_full_frame, CodecError, CELL_BYTES};
use crate::controller::WizardCommand;
use crate::frame_source::{FrameDiagnostics, ProceduralWizardFrameSource};
use crate::newsroom::{
    build_actor_render_sample, embedded_newsroom_catalogs, ActorRenderSampleEnvelopeV1,
    NewsPerformanceCueV1, NewsroomCueReceiptV1, NewsroomError,
};
use crate::runtime::{AvatarRuntime, RuntimeSnapshot};
use crate::runtime_clock::{CatchUpDropped, RuntimeClock};
use crate::state::WizardState;
use serde::Serialize;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tokio::sync::{broadcast, RwLock, Semaphore};
use tokio::time::{interval_at, sleep, Duration, Instant, MissedTickBehavior};

const BROADCAST_CAPACITY: usize = 16;
static NEXT_EPOCH: AtomicU64 = AtomicU64::new(1);

#[derive(Clone, Debug)]
pub struct FramePacket {
    pub epoch: u64,
    pub sequence: u32,
    pub simulation_tick: u64,
    pub presentation_micros: u64,
    pub encoded: Arc<[u8]>,
    pub full_cells: Arc<[u8]>,
    pub is_keyframe: bool,
    pub diagnostics: FrameDiagnostics,
}

#[derive(Clone, Debug)]
pub struct BootstrapFrame {
    pub epoch: u64,
    pub sequence: u32,
    pub simulation_tick: u64,
    pub encoded: Arc<[u8]>,
    pub full_cells: Arc<[u8]>,
}

#[derive(Clone, Debug, Serialize)]
pub struct HubDiagnostics {
    pub epoch: u64,
    pub simulation_tick: u64,
    pub frame_sequence: Option<u32>,
    pub subscriber_count: usize,
    pub latest_is_keyframe: bool,
    pub clock: HubClockDiagnostics,
    pub frame: Option<FrameDiagnostics>,
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct HubClockDiagnostics {
    pub catch_up_drop_count: u64,
    pub cumulative_dropped_monotonic_ns: u64,
    pub cumulative_dropped_sub_nanosecond_units: u8,
    pub last_drop: Option<HubClockDropDiagnostics>,
}

#[derive(Clone, Debug, Serialize)]
pub struct HubClockDropDiagnostics {
    pub at_monotonic_ns: u64,
    pub dropped_tick_count: u64,
    pub dropped_monotonic_ns: u64,
    pub dropped_sub_nanosecond_units: u8,
}

impl From<CatchUpDropped> for HubClockDropDiagnostics {
    fn from(drop: CatchUpDropped) -> Self {
        Self {
            at_monotonic_ns: drop.at_monotonic_ns,
            dropped_tick_count: drop.dropped_tick_count,
            dropped_monotonic_ns: drop.dropped_monotonic_ns,
            dropped_sub_nanosecond_units: drop.dropped_sub_nanosecond_units,
        }
    }
}

#[derive(Debug)]
pub struct AvatarFrameHub {
    sender: broadcast::Sender<Arc<FramePacket>>,
    latest: RwLock<Option<Arc<FramePacket>>>,
    runtime: Arc<RwLock<AvatarRuntime>>,
    actor_sample_slots: Semaphore,
    clock_diagnostics: RwLock<HubClockDiagnostics>,
    cols: usize,
    rows: usize,
    fps: f32,
    epoch: u64,
}

impl AvatarFrameHub {
    #[must_use]
    pub fn start(source: ProceduralWizardFrameSource) -> Arc<Self> {
        let runtime = Arc::new(RwLock::new(AvatarRuntime::new(source.controller_clone())));
        let (sender, _) = broadcast::channel(BROADCAST_CAPACITY);
        let hub = Arc::new(Self {
            sender,
            latest: RwLock::new(None),
            runtime,
            actor_sample_slots: Semaphore::new(2),
            clock_diagnostics: RwLock::new(HubClockDiagnostics::default()),
            cols: source.cols,
            rows: source.rows,
            fps: source.fps,
            epoch: NEXT_EPOCH.fetch_add(1, Ordering::Relaxed),
        });

        tokio::spawn(run_runtime(hub.clone()));
        tokio::spawn(run_render_producer(hub.clone(), source));
        hub
    }

    #[must_use]
    pub fn subscribe(&self) -> broadcast::Receiver<Arc<FramePacket>> {
        self.sender.subscribe()
    }

    #[must_use]
    pub const fn epoch(&self) -> u64 {
        self.epoch
    }

    #[must_use]
    pub const fn cols(&self) -> usize {
        self.cols
    }

    #[must_use]
    pub const fn rows(&self) -> usize {
        self.rows
    }

    #[must_use]
    pub const fn fps(&self) -> f32 {
        self.fps
    }

    pub async fn snapshot(&self) -> RuntimeSnapshot {
        self.runtime.read().await.snapshot()
    }

    pub async fn current_state(&self) -> WizardState {
        self.runtime.read().await.current_state().clone()
    }

    pub async fn apply_command(&self, command: WizardCommand) -> crate::controller::CommandResult {
        self.runtime.write().await.apply_command(command)
    }

    pub async fn apply_newsroom_cue(
        &self,
        cue: NewsPerformanceCueV1,
    ) -> Result<NewsroomCueReceiptV1, NewsroomError> {
        embedded_newsroom_catalogs()?;
        self.runtime.write().await.apply_newsroom_cue(cue)
    }

    pub async fn latest_newsroom_receipt(&self) -> Option<NewsroomCueReceiptV1> {
        self.runtime.read().await.latest_newsroom_receipt().cloned()
    }

    pub async fn newsroom_actor_sample(
        &self,
    ) -> Result<ActorRenderSampleEnvelopeV1, NewsroomError> {
        let _permit = self
            .actor_sample_slots
            .try_acquire()
            .map_err(|_| NewsroomError::ActorSampleBusy)?;
        let (state, semantic_pose, generation) = {
            let runtime = self.runtime.read().await;
            runtime.newsroom_actor_sample_context()
        };
        let engine_commit = crate::BUILD_GIT_SHA.to_string();
        tokio::task::spawn_blocking(move || {
            let (metadata, buffers) =
                build_actor_render_sample(&state, &semantic_pose, generation, &engine_commit)?;
            Ok(ActorRenderSampleEnvelopeV1::new(metadata, &buffers))
        })
        .await
        .map_err(|error| NewsroomError::ActorSample(format!("actor sample task failed: {error}")))?
    }

    pub async fn bootstrap(&self) -> Result<Option<BootstrapFrame>, CodecError> {
        let latest = self.latest.read().await.clone();
        latest
            .map(|packet| {
                let encoded = encode_full_frame(&packet.full_cells, packet.sequence, CELL_BYTES)?;
                Ok(BootstrapFrame {
                    epoch: packet.epoch,
                    sequence: packet.sequence,
                    simulation_tick: packet.simulation_tick,
                    encoded: Arc::from(encoded.message),
                    full_cells: packet.full_cells.clone(),
                })
            })
            .transpose()
    }

    pub async fn diagnostics(&self) -> HubDiagnostics {
        let simulation_tick = self.runtime.read().await.tick();
        let latest = self.latest.read().await.clone();
        let clock = self.clock_diagnostics.read().await.clone();
        HubDiagnostics {
            epoch: self.epoch,
            simulation_tick,
            frame_sequence: latest.as_ref().map(|packet| packet.sequence),
            subscriber_count: self.sender.receiver_count(),
            latest_is_keyframe: latest.as_ref().is_some_and(|packet| packet.is_keyframe),
            clock,
            frame: latest.map(|packet| packet.diagnostics.clone()),
        }
    }
}

async fn run_runtime(hub: Arc<AvatarFrameHub>) {
    let origin = Instant::now();
    let mut clock = RuntimeClock::default();
    let _ = clock.advance_wall_clock(0);
    loop {
        sleep(Duration::from_millis(2)).await;
        let monotonic_ns = origin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64;
        let advance = clock.advance_wall_clock(monotonic_ns);
        if let Some(drop) = advance.dropped() {
            let mut diagnostics = hub.clock_diagnostics.write().await;
            diagnostics.catch_up_drop_count = drop.catch_up_drop_count;
            diagnostics.cumulative_dropped_monotonic_ns = drop.cumulative_dropped_monotonic_ns;
            diagnostics.cumulative_dropped_sub_nanosecond_units =
                drop.cumulative_dropped_sub_nanosecond_units;
            diagnostics.last_drop = Some(drop.into());
        }
        if advance.ticks_due() == 0 {
            continue;
        }
        let mut runtime = hub.runtime.write().await;
        for _ in 0..advance.ticks_due() {
            runtime.step_tick();
        }
    }
}

async fn run_render_producer(hub: Arc<AvatarFrameHub>, mut source: ProceduralWizardFrameSource) {
    let frame_duration = Duration::from_secs_f64(1.0 / f64::from(hub.fps));
    let mut deadline = interval_at(Instant::now(), frame_duration);
    deadline.set_missed_tick_behavior(MissedTickBehavior::Skip);

    loop {
        deadline.tick().await;
        let sample = hub.runtime.read().await.snapshot();
        let Ok((encoded, frame)) = source.render_and_encode(&sample.current, "adaptive") else {
            continue;
        };
        let packet = Arc::new(FramePacket {
            epoch: hub.epoch,
            sequence: frame.frame_index,
            simulation_tick: sample.tick,
            presentation_micros: u64::from(frame.frame_index)
                .saturating_mul((1_000_000.0 / f64::from(hub.fps)) as u64),
            encoded: Arc::from(encoded),
            full_cells: Arc::from(frame.cells),
            is_keyframe: frame.is_keyframe,
            diagnostics: source.diagnostics(),
        });
        *hub.latest.write().await = Some(packet.clone());
        let _ = hub.sender.send(packet);
    }
}
