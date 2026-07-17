use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::fs::{File, OpenOptions};
use std::io::{self, Read, Write};
use std::net::{Ipv4Addr, SocketAddr, SocketAddrV4, TcpListener, TcpStream};
#[cfg(unix)]
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{mpsc, Arc, Mutex, RwLock};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const HEALTH_SCHEMA_VERSION: u32 = 1;
const PROTOCOL_VERSION: u32 = 1;
const READY_TIMEOUT: Duration = Duration::from_secs(20);
const HEALTH_INTERVAL: Duration = Duration::from_secs(2);
const POLL_INTERVAL: Duration = Duration::from_millis(125);
const GRACEFUL_SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(3);
const CRASH_WINDOW: Duration = Duration::from_secs(60);
const MAX_CRASH_RESTARTS: usize = 4;
const STABLE_RUNTIME: Duration = Duration::from_secs(30);
const MAX_HTTP_BYTES: usize = 32 * 1024;
const MAX_REPLAY_HTTP_BYTES: usize = 8 * 1024 * 1024;
const MAX_COMMAND_BODY_BYTES: usize = 16 * 1024;
const DISCOVERY_SCHEMA_VERSION: u32 = 1;
const DISCOVERY_TTL: Duration = Duration::from_secs(120);
const DISCOVERY_REFRESH_INTERVAL: Duration = Duration::from_secs(45);
const ENGINE_LOG_MAX_BYTES: u64 = 5 * 1024 * 1024;
const ENGINE_LOG_HISTORY_COUNT: usize = 5;

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum EnginePhase {
    Starting,
    Ready,
    Reconnecting,
    Degraded,
    Stopped,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RuntimeStatus {
    pub phase: EnginePhase,
    pub pid: Option<u32>,
    pub port: u16,
    pub schema_version: Option<u32>,
    pub protocol_version: Option<u32>,
    pub character_id: Option<String>,
    pub runtime_epoch: Option<String>,
    pub frame_hub_running: bool,
    pub connector_enabled: bool,
    pub restart_attempt: usize,
    pub error_code: Option<String>,
}

impl RuntimeStatus {
    fn starting(port: u16) -> Self {
        Self {
            phase: EnginePhase::Starting,
            pid: None,
            port,
            schema_version: None,
            protocol_version: None,
            character_id: None,
            runtime_epoch: None,
            frame_hub_running: false,
            connector_enabled: false,
            restart_attempt: 0,
            error_code: None,
        }
    }
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RuntimeDescriptor {
    pub base_url: String,
    pub websocket_url: String,
    pub app_version: String,
    pub is_tauri: bool,
    pub http_transport: String,
    pub frame_transport: String,
    pub frame_event_name: String,
}

#[derive(Clone)]
pub(crate) struct ConnectionInfo {
    pub port: u16,
    pub token: String,
}

#[derive(Debug, Deserialize)]
struct HealthDocument {
    schema_version: u32,
    status: String,
    runtime_epoch: String,
    protocol_version: u32,
    character_id: String,
    pid: u32,
    started_at_monotonic_ms: u64,
    frame_hub_running: bool,
    connector_enabled: bool,
}

impl HealthDocument {
    fn validate(&self, expected_pid: u32) -> Result<(), &'static str> {
        if self.schema_version != HEALTH_SCHEMA_VERSION {
            return Err("health_schema_mismatch");
        }
        if self.protocol_version != PROTOCOL_VERSION {
            return Err("protocol_mismatch");
        }
        if self.status != "ready" {
            return Err("engine_not_ready");
        }
        if !self.connector_enabled {
            return Err("connector_disabled");
        }
        if self.pid != expected_pid {
            return Err("health_pid_mismatch");
        }
        if self.runtime_epoch.is_empty()
            || self.character_id.is_empty()
            || self.started_at_monotonic_ms == 0
        {
            return Err("health_identity_missing");
        }
        Ok(())
    }
}

#[derive(Debug)]
enum SupervisorCommand {
    Restart,
    Shutdown,
}

pub struct SupervisorHandle {
    tx: mpsc::Sender<SupervisorCommand>,
    status: Arc<RwLock<RuntimeStatus>>,
    descriptor: RuntimeDescriptor,
    secret: String,
    app_version: String,
    worker: Mutex<Option<thread::JoinHandle<()>>>,
}

impl SupervisorHandle {
    pub fn launch(
        executable: PathBuf,
        logs_dir: PathBuf,
        discovery_path: PathBuf,
        score_root: PathBuf,
        app_version: String,
    ) -> Result<Self, String> {
        let port =
            select_loopback_port().map_err(|error| format!("port selection failed: {error}"))?;
        let app_token =
            generate_launch_token().map_err(|error| format!("token generation failed: {error}"))?;
        let media_token =
            generate_launch_token().map_err(|error| format!("token generation failed: {error}"))?;
        if app_token == media_token {
            return Err("credential generation failed".to_string());
        }
        let descriptor = RuntimeDescriptor {
            base_url: format!("http://127.0.0.1:{port}"),
            websocket_url: format!("ws://127.0.0.1:{port}/ws/avatar/wizard"),
            app_version: app_version.clone(),
            is_tauri: true,
            http_transport: "invoke".to_string(),
            frame_transport: "tauri-event".to_string(),
            frame_event_name: "companion-frame".to_string(),
        };
        let handle_token = app_token.clone();
        let status = Arc::new(RwLock::new(RuntimeStatus::starting(port)));
        let (tx, rx) = mpsc::channel();
        let worker_status = Arc::clone(&status);
        let worker = thread::Builder::new()
            .name("wizard-sidecar-supervisor".to_string())
            .spawn(move || {
                run_supervisor(
                    WorkerConfig {
                        executable,
                        logs_dir,
                        discovery_path,
                        score_root,
                        port,
                        app_token,
                        media_token,
                    },
                    rx,
                    worker_status,
                )
            })
            .map_err(|error| format!("supervisor thread failed: {error}"))?;
        Ok(Self {
            tx,
            status,
            descriptor,
            secret: handle_token,
            app_version,
            worker: Mutex::new(Some(worker)),
        })
    }

    pub fn descriptor(&self) -> RuntimeDescriptor {
        self.descriptor.clone()
    }

    pub fn status(&self) -> RuntimeStatus {
        read_status(&self.status)
    }

    pub(crate) fn connection_info(&self) -> ConnectionInfo {
        ConnectionInfo {
            port: self.status().port,
            token: self.secret.clone(),
        }
    }

    pub fn authenticated_runtime_request(
        &self,
        method: &str,
        path: &str,
        body: Option<&serde_json::Value>,
        response_type: Option<&str>,
    ) -> Result<serde_json::Value, String> {
        validate_runtime_request(method, path).map_err(str::to_string)?;
        let response_type = response_type.unwrap_or("json");
        if response_type != "json"
            && !(response_type == "text" && path == "/api/avatar/wizard/replay")
        {
            return Err("runtime_response_type_not_allowed".to_string());
        }
        let encoded = body
            .map(serde_json::to_vec)
            .transpose()
            .map_err(|_| "request_json_invalid".to_string())?;
        if encoded
            .as_ref()
            .is_some_and(|body| body.len() > MAX_COMMAND_BODY_BYTES)
        {
            return Err("request_body_too_large".to_string());
        }
        let response = http_request_with_limit(
            self.status().port,
            method,
            path,
            Some(&self.secret),
            encoded.as_deref(),
            if response_type == "text" {
                MAX_REPLAY_HTTP_BYTES
            } else {
                MAX_HTTP_BYTES
            },
        )
        .map_err(str::to_string)?;
        if response_type == "text" {
            return String::from_utf8(response)
                .map(serde_json::Value::String)
                .map_err(|_| "response_text_invalid".to_string());
        }
        serde_json::from_slice(&response).map_err(|_| "response_json_invalid".to_string())
    }

    pub fn restart(&self) -> Result<(), String> {
        self.tx
            .send(SupervisorCommand::Restart)
            .map_err(|_| "engine supervisor is unavailable".to_string())
    }

    pub fn shutdown(&self) {
        let _ = self.tx.send(SupervisorCommand::Shutdown);
        let worker = match self.worker.lock() {
            Ok(mut guard) => guard.take(),
            Err(poisoned) => poisoned.into_inner().take(),
        };
        if let Some(worker) = worker {
            let _ = worker.join();
        }
    }

    pub fn safe_diagnostics(&self) -> String {
        let status = self.status();
        let payload = serde_json::json!({
            "app": "Wizard Joe Companion",
            "appVersion": self.app_version,
            "engine": status,
            "healthSchemaExpected": HEALTH_SCHEMA_VERSION,
            "protocolExpected": PROTOCOL_VERSION,
        });
        serde_json::to_string_pretty(&payload).unwrap_or_else(|_| "diagnostics unavailable".into())
    }
}

struct WorkerConfig {
    executable: PathBuf,
    logs_dir: PathBuf,
    discovery_path: PathBuf,
    score_root: PathBuf,
    port: u16,
    app_token: String,
    media_token: String,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct DiscoveryDocument {
    schema_version: u32,
    base_url: String,
    media_token: String,
    runtime_epoch: String,
    pid: u32,
    issued_at_unix_ms: u64,
    expires_at_unix_ms: u64,
}

fn run_supervisor(
    config: WorkerConfig,
    rx: mpsc::Receiver<SupervisorCommand>,
    status: Arc<RwLock<RuntimeStatus>>,
) {
    let mut policy = RestartPolicy::default();
    let mut restarting = false;
    let mut published_epoch: Option<String> = None;

    'launch: loop {
        if let Some(epoch) = published_epoch.take() {
            remove_owned_discovery(&config.discovery_path, &epoch);
        }
        let mut last_discovery_write: Option<Instant> = None;
        update_status(&status, |current| {
            current.phase = if restarting {
                EnginePhase::Reconnecting
            } else {
                EnginePhase::Starting
            };
            current.pid = None;
            current.error_code = None;
            current.restart_attempt = policy.recent_crashes();
        });

        let log = match open_log(&config.logs_dir) {
            Ok(log) => log,
            Err(_) => {
                set_degraded(&status, "log_open_failed");
                match wait_for_manual_command(&rx) {
                    SupervisorCommand::Restart => {
                        policy.reset();
                        restarting = true;
                        continue;
                    }
                    SupervisorCommand::Shutdown => {
                        set_stopped(&status);
                        return;
                    }
                }
            }
        };

        let mut child = match spawn_child(&config, log) {
            Ok(child) => child,
            Err(error_code) => {
                set_degraded(&status, error_code);
                match wait_for_manual_command(&rx) {
                    SupervisorCommand::Restart => {
                        policy.reset();
                        restarting = true;
                        continue;
                    }
                    SupervisorCommand::Shutdown => {
                        set_stopped(&status);
                        return;
                    }
                }
            }
        };

        let pid = child.id();
        let launched_at = Instant::now();
        update_status(&status, |current| current.pid = Some(pid));
        let ready_deadline = Instant::now() + READY_TIMEOUT;
        let mut last_health_check = Instant::now() - HEALTH_INTERVAL;
        let mut became_ready = false;

        loop {
            match rx.try_recv() {
                Ok(SupervisorCommand::Restart) => {
                    graceful_stop(&mut child, config.port, &config.app_token);
                    policy.reset();
                    restarting = true;
                    continue 'launch;
                }
                Ok(SupervisorCommand::Shutdown) | Err(mpsc::TryRecvError::Disconnected) => {
                    graceful_stop(&mut child, config.port, &config.app_token);
                    if let Some(epoch) = published_epoch.take() {
                        remove_owned_discovery(&config.discovery_path, &epoch);
                    }
                    set_stopped(&status);
                    return;
                }
                Err(mpsc::TryRecvError::Empty) => {}
            }

            match child.try_wait() {
                Ok(Some(_)) => break,
                Ok(None) => {}
                Err(_) => {
                    set_degraded(&status, "child_wait_failed");
                    break;
                }
            }

            if last_health_check.elapsed() >= HEALTH_INTERVAL || !became_ready {
                last_health_check = Instant::now();
                match fetch_health(config.port).and_then(|health| {
                    health.validate(pid)?;
                    Ok(health)
                }) {
                    Ok(health) => {
                        became_ready = true;
                        let publish_due = published_epoch.as_deref()
                            != Some(health.runtime_epoch.as_str())
                            || last_discovery_write.map_or(true, |written| {
                                written.elapsed() >= DISCOVERY_REFRESH_INTERVAL
                            });
                        let discovery_result = if publish_due {
                            publish_discovery(&config, &health).map(|()| {
                                published_epoch = Some(health.runtime_epoch.clone());
                                last_discovery_write = Some(Instant::now());
                            })
                        } else {
                            Ok(())
                        };
                        update_status(&status, |current| {
                            current.phase = if discovery_result.is_ok() {
                                EnginePhase::Ready
                            } else {
                                EnginePhase::Degraded
                            };
                            current.schema_version = Some(health.schema_version);
                            current.protocol_version = Some(health.protocol_version);
                            current.character_id = Some(health.character_id);
                            current.runtime_epoch = Some(health.runtime_epoch);
                            current.frame_hub_running = health.frame_hub_running;
                            current.connector_enabled = health.connector_enabled;
                            current.error_code = discovery_result
                                .err()
                                .map(|_| "discovery_publish_failed".to_string());
                        });
                    }
                    Err(error_code) if became_ready => {
                        update_status(&status, |current| {
                            current.phase = EnginePhase::Reconnecting;
                            current.error_code = Some(error_code.to_string());
                        });
                    }
                    Err(error_code) if Instant::now() >= ready_deadline => {
                        set_degraded(&status, error_code);
                    }
                    Err(_) => {}
                }
            }

            thread::sleep(POLL_INTERVAL);
        }

        update_status(&status, |current| current.pid = None);
        if let Some(epoch) = published_epoch.take() {
            remove_owned_discovery(&config.discovery_path, &epoch);
        }
        if launched_at.elapsed() >= STABLE_RUNTIME {
            policy.reset();
        }
        let Some(delay) = policy.record_crash(Instant::now()) else {
            set_degraded(&status, "crash_loop_limit");
            match wait_for_manual_command(&rx) {
                SupervisorCommand::Restart => {
                    policy.reset();
                    restarting = true;
                    continue;
                }
                SupervisorCommand::Shutdown => {
                    set_stopped(&status);
                    return;
                }
            }
        };
        update_status(&status, |current| {
            current.phase = EnginePhase::Reconnecting;
            current.error_code = Some("engine_exited".to_string());
            current.restart_attempt = policy.recent_crashes();
        });
        match rx.recv_timeout(delay) {
            Ok(SupervisorCommand::Shutdown) | Err(mpsc::RecvTimeoutError::Disconnected) => {
                set_stopped(&status);
                return;
            }
            Ok(SupervisorCommand::Restart) => policy.reset(),
            Err(mpsc::RecvTimeoutError::Timeout) => {}
        }
        restarting = true;
    }
}

fn open_log(logs_dir: &Path) -> io::Result<File> {
    std::fs::create_dir_all(logs_dir)?;
    if let Err(rotation_error) = rotate_engine_log(logs_dir) {
        return recover_bounded_engine_log(logs_dir, rotation_error);
    }
    open_append_log(logs_dir)
}

fn open_append_log(logs_dir: &Path) -> io::Result<File> {
    OpenOptions::new()
        .create(true)
        .append(true)
        .open(logs_dir.join("engine.log"))
}

fn recover_bounded_engine_log(logs_dir: &Path, rotation_error: io::Error) -> io::Result<File> {
    let active = logs_dir.join("engine.log");
    let metadata = std::fs::symlink_metadata(&active)?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(rotation_error);
    }

    let mut recovered = OpenOptions::new().write(true).truncate(true).open(active)?;
    writeln!(
        recovered,
        "[companion] engine log rotation failed ({:?}); active log reset to preserve size bound",
        rotation_error.kind()
    )?;
    Ok(recovered)
}

fn rotate_engine_log(logs_dir: &Path) -> io::Result<()> {
    prune_excess_engine_logs(logs_dir)?;

    let active = logs_dir.join("engine.log");
    let metadata = match std::fs::symlink_metadata(&active) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(()),
        Err(error) => return Err(error),
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(io::Error::other("engine log path is unsafe"));
    }
    if metadata.len() < ENGINE_LOG_MAX_BYTES {
        return Ok(());
    }

    let oldest = engine_log_history_path(logs_dir, ENGINE_LOG_HISTORY_COUNT);
    match std::fs::remove_file(&oldest) {
        Ok(()) => {}
        Err(error) if error.kind() == io::ErrorKind::NotFound => {}
        Err(error) => return Err(error),
    }

    for generation in (1..ENGINE_LOG_HISTORY_COUNT).rev() {
        let source = engine_log_history_path(logs_dir, generation);
        let destination = engine_log_history_path(logs_dir, generation + 1);
        match std::fs::rename(source, destination) {
            Ok(()) => {}
            Err(error) if error.kind() == io::ErrorKind::NotFound => {}
            Err(error) => return Err(error),
        }
    }
    std::fs::rename(active, engine_log_history_path(logs_dir, 1))
}

fn prune_excess_engine_logs(logs_dir: &Path) -> io::Result<()> {
    for entry in std::fs::read_dir(logs_dir)? {
        let entry = entry?;
        let Some(name) = entry.file_name().to_str().map(str::to_owned) else {
            continue;
        };
        let Some(generation) = name
            .strip_prefix("engine.log.")
            .and_then(|suffix| suffix.parse::<usize>().ok())
        else {
            continue;
        };
        if generation > ENGINE_LOG_HISTORY_COUNT {
            std::fs::remove_file(entry.path())?;
        }
    }
    Ok(())
}

fn engine_log_history_path(logs_dir: &Path, generation: usize) -> PathBuf {
    logs_dir.join(format!("engine.log.{generation}"))
}

fn spawn_child(config: &WorkerConfig, log: File) -> Result<Child, &'static str> {
    if !config.executable.is_file() {
        return Err("sidecar_missing");
    }
    let stderr = log.try_clone().map_err(|_| "log_clone_failed")?;
    Command::new(&config.executable)
        .args([
            "--host",
            "127.0.0.1",
            "--port",
            &config.port.to_string(),
            "--companion",
        ])
        .env("WIZARD_COMPANION_MODE", "1")
        .env("WIZARD_COMPANION_APP_TOKEN", &config.app_token)
        .env("WIZARD_MEDIA_CONNECTOR_ENABLED", "1")
        .env("WIZARD_MEDIA_CONNECTOR_TOKEN", &config.media_token)
        .env("WIZARD_SCORE_ROOT", &config.score_root)
        .stdin(Stdio::null())
        .stdout(Stdio::from(log))
        .stderr(Stdio::from(stderr))
        .spawn()
        .map_err(|_| "sidecar_spawn_failed")
}

fn publish_discovery(config: &WorkerConfig, health: &HealthDocument) -> io::Result<()> {
    let parent = config
        .discovery_path
        .parent()
        .ok_or_else(|| io::Error::other("discovery parent missing"))?;
    std::fs::create_dir_all(parent)?;
    #[cfg(unix)]
    {
        let metadata = std::fs::symlink_metadata(parent)?;
        if metadata.file_type().is_symlink() || !metadata.is_dir() {
            return Err(io::Error::other("discovery parent is unsafe"));
        }
        std::fs::set_permissions(parent, std::fs::Permissions::from_mode(0o700))?;
    }

    let issued_at_unix_ms = unix_time_ms()?;
    let document = DiscoveryDocument {
        schema_version: DISCOVERY_SCHEMA_VERSION,
        base_url: format!("http://127.0.0.1:{}", config.port),
        media_token: config.media_token.clone(),
        runtime_epoch: health.runtime_epoch.clone(),
        pid: health.pid,
        issued_at_unix_ms,
        expires_at_unix_ms: issued_at_unix_ms.saturating_add(DISCOVERY_TTL.as_millis() as u64),
    };
    let bytes = serde_json::to_vec(&document).map_err(io::Error::other)?;
    let temporary = parent.join(format!(".connector-v1.{}.tmp", std::process::id()));
    let mut options = OpenOptions::new();
    options.create(true).write(true).truncate(true);
    #[cfg(unix)]
    options.mode(0o600);
    let mut file = options.open(&temporary)?;
    file.write_all(&bytes)?;
    file.sync_all()?;
    #[cfg(unix)]
    std::fs::set_permissions(&temporary, std::fs::Permissions::from_mode(0o600))?;
    std::fs::rename(&temporary, &config.discovery_path)?;
    Ok(())
}

fn remove_owned_discovery(path: &Path, runtime_epoch: &str) {
    let Ok(metadata) = std::fs::symlink_metadata(path) else {
        return;
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() || metadata.len() > 16 * 1024 {
        return;
    }
    let Ok(bytes) = std::fs::read(path) else {
        return;
    };
    let Ok(document) = serde_json::from_slice::<DiscoveryDocument>(&bytes) else {
        return;
    };
    if document.schema_version == DISCOVERY_SCHEMA_VERSION
        && document.runtime_epoch == runtime_epoch
    {
        let _ = std::fs::remove_file(path);
    }
}

fn unix_time_ms() -> io::Result<u64> {
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(io::Error::other)?;
    u64::try_from(duration.as_millis()).map_err(io::Error::other)
}

fn graceful_stop(child: &mut Child, port: u16, token: &str) {
    let _ = request_shutdown(port, token);
    let deadline = Instant::now() + GRACEFUL_SHUTDOWN_TIMEOUT;
    while Instant::now() < deadline {
        match child.try_wait() {
            Ok(Some(_)) => return,
            Ok(None) => thread::sleep(Duration::from_millis(50)),
            Err(_) => break,
        }
    }
    let _ = child.kill();
    let _ = child.wait();
}

fn wait_for_manual_command(rx: &mpsc::Receiver<SupervisorCommand>) -> SupervisorCommand {
    rx.recv().unwrap_or(SupervisorCommand::Shutdown)
}

fn set_degraded(status: &Arc<RwLock<RuntimeStatus>>, error_code: &str) {
    update_status(status, |current| {
        current.phase = EnginePhase::Degraded;
        current.error_code = Some(error_code.to_string());
    });
}

fn set_stopped(status: &Arc<RwLock<RuntimeStatus>>) {
    update_status(status, |current| {
        current.phase = EnginePhase::Stopped;
        current.pid = None;
        current.error_code = None;
    });
}

fn update_status(status: &Arc<RwLock<RuntimeStatus>>, update: impl FnOnce(&mut RuntimeStatus)) {
    match status.write() {
        Ok(mut guard) => update(&mut guard),
        Err(poisoned) => update(&mut poisoned.into_inner()),
    }
}

fn read_status(status: &Arc<RwLock<RuntimeStatus>>) -> RuntimeStatus {
    match status.read() {
        Ok(guard) => guard.clone(),
        Err(poisoned) => poisoned.into_inner().clone(),
    }
}

pub fn select_loopback_port() -> io::Result<u16> {
    let listener = TcpListener::bind(SocketAddrV4::new(Ipv4Addr::LOCALHOST, 0))?;
    listener.local_addr().map(|address| address.port())
}

pub fn generate_launch_token() -> io::Result<String> {
    let mut bytes = [0_u8; 32];
    getrandom::fill(&mut bytes)
        .map_err(|error| io::Error::other(format!("secure randomness unavailable: {error:?}")))?;
    let mut token = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        use std::fmt::Write as _;
        write!(&mut token, "{byte:02x}").expect("writing to String cannot fail");
    }
    Ok(token)
}

pub fn resolve_sidecar_path(resource_root: &Path, target_triple: &str) -> PathBuf {
    resource_root
        .join("sidecar")
        .join(target_triple)
        .join("wizard-joe-engine")
        .join("wizard-joe-engine")
}

#[derive(Default)]
pub struct RestartPolicy {
    crashes: VecDeque<Instant>,
}

impl RestartPolicy {
    pub fn record_crash(&mut self, now: Instant) -> Option<Duration> {
        while self
            .crashes
            .front()
            .is_some_and(|time| now.duration_since(*time) > CRASH_WINDOW)
        {
            self.crashes.pop_front();
        }
        if self.crashes.len() >= MAX_CRASH_RESTARTS {
            return None;
        }
        self.crashes.push_back(now);
        let exponent = (self.crashes.len() - 1).min(3) as u32;
        Some(Duration::from_millis(250 * 2_u64.pow(exponent)))
    }

    pub fn reset(&mut self) {
        self.crashes.clear();
    }

    pub fn recent_crashes(&self) -> usize {
        self.crashes.len()
    }
}

fn fetch_health(port: u16) -> Result<HealthDocument, &'static str> {
    let body = http_request(port, "GET", "/api/companion/health", None, None)?;
    serde_json::from_slice(&body).map_err(|_| "health_json_invalid")
}

fn request_shutdown(port: u16, token: &str) -> Result<(), &'static str> {
    http_request(port, "POST", "/api/companion/shutdown", Some(token), None).map(|_| ())
}

fn validate_runtime_request(method: &str, path: &str) -> Result<(), &'static str> {
    let allowed = matches!(
        (method, path),
        ("GET", "/api/companion/health")
            | ("GET", "/api/avatar/wizard/state")
            | ("GET", "/api/avatar/wizard/poses")
            | ("GET", "/api/avatar/wizard/character")
            | ("GET", "/api/avatar/wizard/permission-world")
            | ("GET", "/api/avatar/wizard/replay")
            | ("POST", "/api/companion/reactions")
            | ("POST", "/api/avatar/wizard/action")
            | ("POST", "/api/avatar/wizard/gaze")
            | ("POST", "/api/avatar/wizard/move")
            | ("POST", "/api/avatar/wizard/path")
            | ("POST", "/api/avatar/wizard/expression")
            | ("POST", "/api/avatar/wizard/speak")
            | ("POST", "/api/avatar/wizard/speech-stop")
            | ("POST", "/api/avatar/wizard/pose")
            | ("POST", "/api/avatar/wizard/control")
            | ("POST", "/api/avatar/wizard/stop")
            | ("POST", "/api/avatar/wizard/reset")
            | ("POST", "/api/avatar/wizard/director/permission-world")
    );
    allowed.then_some(()).ok_or("runtime_route_not_allowed")
}

fn http_request(
    port: u16,
    method: &str,
    path: &str,
    bearer: Option<&str>,
    body: Option<&[u8]>,
) -> Result<Vec<u8>, &'static str> {
    http_request_with_limit(port, method, path, bearer, body, MAX_HTTP_BYTES)
}

fn http_request_with_limit(
    port: u16,
    method: &str,
    path: &str,
    bearer: Option<&str>,
    body: Option<&[u8]>,
    max_response_bytes: usize,
) -> Result<Vec<u8>, &'static str> {
    let address = SocketAddr::V4(SocketAddrV4::new(Ipv4Addr::LOCALHOST, port));
    let timeout = Duration::from_millis(600);
    let mut stream =
        TcpStream::connect_timeout(&address, timeout).map_err(|_| "health_unreachable")?;
    stream
        .set_read_timeout(Some(timeout))
        .map_err(|_| "health_io_failed")?;
    stream
        .set_write_timeout(Some(timeout))
        .map_err(|_| "health_io_failed")?;
    let authorization = bearer
        .map(|token| format!("Authorization: Bearer {token}\r\n"))
        .unwrap_or_default();
    let body = body.unwrap_or_default();
    let content_type = if body.is_empty() {
        ""
    } else {
        "Content-Type: application/json\r\n"
    };
    let request = format!(
        "{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n{authorization}{content_type}Content-Length: {}\r\nConnection: close\r\n\r\n",
        body.len()
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|_| "health_io_failed")?;
    stream.write_all(body).map_err(|_| "health_io_failed")?;

    let mut response = Vec::new();
    let mut chunk = [0_u8; 4096];
    loop {
        match stream.read(&mut chunk) {
            Ok(0) => break,
            Ok(count) => {
                if response.len() + count > max_response_bytes {
                    return Err("health_response_too_large");
                }
                response.extend_from_slice(&chunk[..count]);
            }
            Err(error)
                if matches!(
                    error.kind(),
                    io::ErrorKind::WouldBlock | io::ErrorKind::TimedOut
                ) && !response.is_empty() =>
            {
                break
            }
            Err(_) => return Err("health_io_failed"),
        }
    }
    let header_end = response
        .windows(4)
        .position(|window| window == b"\r\n\r\n")
        .ok_or("health_http_invalid")?;
    let headers =
        std::str::from_utf8(&response[..header_end]).map_err(|_| "health_http_invalid")?;
    let status_line = headers.lines().next().ok_or("health_http_invalid")?;
    if !status_line.starts_with("HTTP/1.1 200 ") && !status_line.starts_with("HTTP/1.0 200 ") {
        return Err("health_http_rejected");
    }
    Ok(response[header_end + 4..].to_vec())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;
    use std::sync::atomic::{AtomicU64, Ordering};

    static TEMP_PATH_SEQUENCE: AtomicU64 = AtomicU64::new(0);

    struct TestDirectory(PathBuf);

    impl TestDirectory {
        fn new(label: &str) -> Self {
            let sequence = TEMP_PATH_SEQUENCE.fetch_add(1, Ordering::Relaxed);
            let path = std::env::temp_dir().join(format!(
                "wizard-companion-{label}-{}-{sequence}",
                std::process::id()
            ));
            std::fs::create_dir_all(&path).expect("create test directory");
            Self(path)
        }

        fn path(&self) -> &Path {
            &self.0
        }
    }

    impl Drop for TestDirectory {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn selected_ports_are_dynamic_literal_loopback_ports() {
        let mut ports = HashSet::new();
        for _ in 0..8 {
            let port = select_loopback_port().expect("loopback port");
            assert_ne!(port, 0);
            ports.insert(port);
        }
        assert!(ports.len() > 1);
    }

    #[test]
    fn launch_tokens_have_256_bits_of_hex_entropy_input() {
        let first = generate_launch_token().expect("first token");
        let second = generate_launch_token().expect("second token");
        assert_eq!(first.len(), 64);
        assert!(first.bytes().all(|byte| byte.is_ascii_hexdigit()));
        assert_ne!(first, second);
    }

    #[test]
    fn health_validation_checks_version_identity_and_pid() {
        let health = HealthDocument {
            schema_version: HEALTH_SCHEMA_VERSION,
            status: "ready".into(),
            runtime_epoch: "epoch-1".into(),
            protocol_version: PROTOCOL_VERSION,
            character_id: "asciline-wizard-v1".into(),
            pid: 42,
            started_at_monotonic_ms: 1,
            frame_hub_running: false,
            connector_enabled: true,
        };
        assert_eq!(health.validate(42), Ok(()));
        assert_eq!(health.validate(41), Err("health_pid_mismatch"));
        let disabled = HealthDocument {
            connector_enabled: false,
            ..health
        };
        assert_eq!(disabled.validate(42), Err("connector_disabled"));
    }

    #[test]
    fn restart_policy_is_exponential_bounded_and_resettable() {
        let start = Instant::now();
        let mut policy = RestartPolicy::default();
        assert_eq!(policy.record_crash(start), Some(Duration::from_millis(250)));
        assert_eq!(policy.record_crash(start), Some(Duration::from_millis(500)));
        assert_eq!(
            policy.record_crash(start),
            Some(Duration::from_millis(1000))
        );
        assert_eq!(
            policy.record_crash(start),
            Some(Duration::from_millis(2000))
        );
        assert_eq!(policy.record_crash(start), None);
        policy.reset();
        assert_eq!(policy.record_crash(start), Some(Duration::from_millis(250)));
    }

    #[test]
    fn restart_policy_forgets_crashes_outside_window() {
        let start = Instant::now();
        let mut policy = RestartPolicy::default();
        assert!(policy.record_crash(start).is_some());
        assert_eq!(
            policy.record_crash(start + CRASH_WINDOW + Duration::from_millis(1)),
            Some(Duration::from_millis(250))
        );
    }

    #[test]
    fn resource_resolution_keeps_target_and_onedir_payload_together() {
        let path = resolve_sidecar_path(
            Path::new("/Applications/Wizard Joe Companion.app/Contents/Resources"),
            "aarch64-apple-darwin",
        );
        assert_eq!(
            path,
            Path::new("/Applications/Wizard Joe Companion.app/Contents/Resources")
                .join("sidecar/aarch64-apple-darwin/wizard-joe-engine/wizard-joe-engine")
        );
        assert_eq!(
            path.parent().unwrap().file_name().unwrap(),
            "wizard-joe-engine"
        );
    }

    #[test]
    fn runtime_status_serialization_uses_safe_public_fields() {
        let serialized = serde_json::to_value(RuntimeStatus::starting(43123)).unwrap();
        assert_eq!(serialized["phase"], "starting");
        assert_eq!(serialized["port"], 43123);
        assert!(serialized.get("token").is_none());
        assert!(serialized.get("executable").is_none());
        assert!(serialized.get("logsDir").is_none());
    }

    #[test]
    fn runtime_bridge_allows_only_expected_methods_and_routes() {
        assert_eq!(
            validate_runtime_request("GET", "/api/avatar/wizard/state"),
            Ok(())
        );
        assert_eq!(
            validate_runtime_request("GET", "/api/avatar/wizard/poses"),
            Ok(())
        );
        assert_eq!(
            validate_runtime_request("POST", "/api/avatar/wizard/action"),
            Ok(())
        );
        for path in [
            "/api/avatar/wizard/character",
            "/api/avatar/wizard/permission-world",
            "/api/avatar/wizard/replay",
        ] {
            assert_eq!(validate_runtime_request("GET", path), Ok(()));
        }
        for path in [
            "/api/avatar/wizard/gaze",
            "/api/avatar/wizard/move",
            "/api/avatar/wizard/path",
            "/api/avatar/wizard/expression",
            "/api/avatar/wizard/speak",
            "/api/avatar/wizard/speech-stop",
            "/api/avatar/wizard/director/permission-world",
        ] {
            assert_eq!(validate_runtime_request("POST", path), Ok(()));
            assert_eq!(
                validate_runtime_request("GET", path),
                Err("runtime_route_not_allowed")
            );
        }
        assert_eq!(
            validate_runtime_request("POST", "/api/companion/shutdown"),
            Err("runtime_route_not_allowed")
        );
        assert_eq!(
            validate_runtime_request("GET", "http://example.com"),
            Err("runtime_route_not_allowed")
        );
    }

    #[test]
    fn discovery_publication_is_private_separate_and_ownership_checked() {
        let directory = std::env::temp_dir().join(format!(
            "wizard-companion-discovery-{}-{}",
            std::process::id(),
            unix_time_ms().unwrap()
        ));
        let path = directory.join("connector-v1.json");
        let config = WorkerConfig {
            executable: PathBuf::from("/unused"),
            logs_dir: PathBuf::from("/unused"),
            discovery_path: path.clone(),
            score_root: PathBuf::from("/unused/scores"),
            port: 51_234,
            app_token: "a".repeat(64),
            media_token: "b".repeat(64),
        };
        let health = HealthDocument {
            schema_version: HEALTH_SCHEMA_VERSION,
            status: "ready".into(),
            runtime_epoch: "epoch-owned".into(),
            protocol_version: PROTOCOL_VERSION,
            character_id: "asciline-wizard-v1".into(),
            pid: 42,
            started_at_monotonic_ms: 1,
            frame_hub_running: true,
            connector_enabled: true,
        };

        publish_discovery(&config, &health).unwrap();
        let document: DiscoveryDocument =
            serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
        assert_eq!(document.schema_version, DISCOVERY_SCHEMA_VERSION);
        assert_eq!(document.base_url, "http://127.0.0.1:51234");
        assert_eq!(document.media_token, config.media_token);
        assert_ne!(document.media_token, config.app_token);
        assert_eq!(document.runtime_epoch, "epoch-owned");
        assert!(document.expires_at_unix_ms > document.issued_at_unix_ms);
        #[cfg(unix)]
        assert_eq!(
            std::fs::metadata(&path).unwrap().permissions().mode() & 0o777,
            0o600
        );

        remove_owned_discovery(&path, "different-epoch");
        assert!(path.exists());
        remove_owned_discovery(&path, "epoch-owned");
        assert!(!path.exists());
        let _ = std::fs::remove_dir_all(directory);
    }

    #[test]
    fn engine_log_below_limit_is_reopened_without_rotation() {
        let directory = TestDirectory::new("log-below-limit");
        let active = directory.path().join("engine.log");
        std::fs::write(&active, b"existing\n").unwrap();

        let mut log = open_log(directory.path()).unwrap();
        log.write_all(b"next\n").unwrap();
        drop(log);

        assert_eq!(std::fs::read(&active).unwrap(), b"existing\nnext\n");
        assert!(!engine_log_history_path(directory.path(), 1).exists());
    }

    #[test]
    fn engine_log_at_limit_rotates_before_the_new_file_is_opened() {
        let directory = TestDirectory::new("log-at-limit");
        let active = directory.path().join("engine.log");
        let oversized = File::create(&active).unwrap();
        oversized.set_len(ENGINE_LOG_MAX_BYTES).unwrap();
        drop(oversized);

        let mut log = open_log(directory.path()).unwrap();
        log.write_all(b"fresh\n").unwrap();
        drop(log);

        assert_eq!(std::fs::metadata(&active).unwrap().len(), 6);
        assert_eq!(
            std::fs::metadata(engine_log_history_path(directory.path(), 1))
                .unwrap()
                .len(),
            ENGINE_LOG_MAX_BYTES
        );
    }

    #[test]
    fn engine_log_rotation_retains_only_five_deterministic_generations() {
        let directory = TestDirectory::new("log-history");
        let active = directory.path().join("engine.log");
        let oversized = File::create(&active).unwrap();
        oversized.set_len(ENGINE_LOG_MAX_BYTES + 1).unwrap();
        drop(oversized);
        for generation in 1..=7 {
            std::fs::write(
                engine_log_history_path(directory.path(), generation),
                generation.to_string(),
            )
            .unwrap();
        }
        std::fs::write(directory.path().join("engine.log.notes"), b"leave me").unwrap();

        drop(open_log(directory.path()).unwrap());

        assert_eq!(
            std::fs::metadata(engine_log_history_path(directory.path(), 1))
                .unwrap()
                .len(),
            ENGINE_LOG_MAX_BYTES + 1
        );
        for generation in 2..=ENGINE_LOG_HISTORY_COUNT {
            assert_eq!(
                std::fs::read_to_string(engine_log_history_path(directory.path(), generation))
                    .unwrap(),
                (generation - 1).to_string()
            );
        }
        assert!(!engine_log_history_path(directory.path(), 6).exists());
        assert!(!engine_log_history_path(directory.path(), 7).exists());
        assert!(directory.path().join("engine.log.notes").exists());
    }

    #[test]
    fn unrotatable_history_recovers_with_a_bounded_observable_active_log() {
        let directory = TestDirectory::new("log-rotation-failure");
        let active = directory.path().join("engine.log");
        let oversized = File::create(&active).unwrap();
        oversized.set_len(ENGINE_LOG_MAX_BYTES).unwrap();
        drop(oversized);
        std::fs::create_dir(engine_log_history_path(
            directory.path(),
            ENGINE_LOG_HISTORY_COUNT,
        ))
        .unwrap();

        drop(open_log(directory.path()).unwrap());
        let recovered = std::fs::read_to_string(active).unwrap();
        assert!(recovered.contains("engine log rotation failed"));
        assert!(recovered.len() < ENGINE_LOG_MAX_BYTES as usize);
    }

    #[cfg(unix)]
    #[test]
    fn unsafe_active_log_symlink_fails_closed() {
        use std::os::unix::fs::symlink;

        let directory = TestDirectory::new("log-symlink");
        let target = directory.path().join("target.log");
        let active = directory.path().join("engine.log");
        std::fs::write(&target, b"do not overwrite").unwrap();
        symlink(&target, &active).unwrap();

        assert!(open_log(directory.path()).is_err());
        assert_eq!(std::fs::read_to_string(target).unwrap(), "do not overwrite");
    }
}
