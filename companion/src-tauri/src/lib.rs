mod bridge;
mod lifecycle;

use bridge::FrameBridge;
use lifecycle::{resolve_sidecar_path, RuntimeDescriptor, RuntimeStatus, SupervisorHandle};
use serde::Deserialize;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use tauri::{Manager, RunEvent};
use tauri_plugin_autostart::ManagerExt;

const PRISM_BUNDLE_ID: &str = "com.jedisherpa.prismgeometrytalk";
const TARGET_TRIPLE: &str = env!("WIZARD_TARGET_TRIPLE");

#[tauri::command]
fn companion_runtime_descriptor(
    supervisor: tauri::State<'_, SupervisorHandle>,
) -> RuntimeDescriptor {
    supervisor.descriptor()
}

#[tauri::command]
fn runtime_status(supervisor: tauri::State<'_, SupervisorHandle>) -> RuntimeStatus {
    supervisor.status()
}

#[derive(Deserialize)]
struct CompanionRequest {
    path: String,
    method: String,
    body: Option<serde_json::Value>,
    #[serde(default, rename = "responseType")]
    response_type: Option<String>,
}

#[tauri::command]
fn companion_http_request(
    request: CompanionRequest,
    supervisor: tauri::State<'_, SupervisorHandle>,
) -> Result<serde_json::Value, String> {
    supervisor.authenticated_runtime_request(
        &request.method.to_ascii_uppercase(),
        &request.path,
        request.body.as_ref(),
        request.response_type.as_deref(),
    )
}

#[tauri::command]
fn start_companion_frame_stream(
    app: tauri::AppHandle,
    event_name: String,
    supervisor: tauri::State<'_, SupervisorHandle>,
    bridge: tauri::State<'_, FrameBridge>,
) -> Result<(), String> {
    bridge.start(app, &event_name, supervisor.connection_info())
}

#[tauri::command]
fn resync_companion_frame_stream(
    epoch: Option<u64>,
    reason: String,
    bridge: tauri::State<'_, FrameBridge>,
) -> Result<(), String> {
    bridge.resync(epoch, &reason)
}

#[tauri::command]
fn stop_companion_frame_stream(bridge: tauri::State<'_, FrameBridge>) {
    bridge.stop();
}

#[tauri::command]
fn restart_engine(supervisor: tauri::State<'_, SupervisorHandle>) -> Result<(), String> {
    supervisor.restart()
}

#[tauri::command]
fn set_launch_at_login(enabled: bool, app: tauri::AppHandle) -> Result<(), String> {
    let manager = app.autolaunch();
    if enabled {
        manager.enable()
    } else {
        manager.disable()
    }
    .map_err(|_| "Unable to update the login setting".to_string())
}

#[tauri::command]
fn launch_at_login_status(app: tauri::AppHandle) -> Result<bool, String> {
    app.autolaunch()
        .is_enabled()
        .map_err(|_| "Unable to read the login setting".to_string())
}

#[tauri::command]
fn open_prism_gt() -> Result<(), String> {
    let status = Command::new("/usr/bin/open")
        .args(["-b", PRISM_BUNDLE_ID])
        .status()
        .map_err(|_| "Unable to request Prism GT launch".to_string())?;
    if status.success() {
        Ok(())
    } else {
        Err("Prism GT is not installed".to_string())
    }
}

#[tauri::command]
fn open_logs(logs_dir: tauri::State<'_, LogsDirectory>) -> Result<(), String> {
    std::fs::create_dir_all(&logs_dir.0)
        .map_err(|_| "Unable to create logs directory".to_string())?;
    let status = Command::new("/usr/bin/open")
        .arg(&logs_dir.0)
        .status()
        .map_err(|_| "Unable to open logs".to_string())?;
    status
        .success()
        .then_some(())
        .ok_or_else(|| "Unable to open logs".to_string())
}

#[tauri::command]
fn copy_safe_diagnostics(supervisor: tauri::State<'_, SupervisorHandle>) -> Result<(), String> {
    let diagnostics = supervisor.safe_diagnostics();
    let mut child = Command::new("/usr/bin/pbcopy")
        .stdin(Stdio::piped())
        .spawn()
        .map_err(|_| "Unable to access the clipboard".to_string())?;
    child
        .stdin
        .take()
        .ok_or_else(|| "Unable to access the clipboard".to_string())?
        .write_all(diagnostics.as_bytes())
        .map_err(|_| "Unable to copy diagnostics".to_string())?;
    let status = child
        .wait()
        .map_err(|_| "Unable to copy diagnostics".to_string())?;
    status
        .success()
        .then_some(())
        .ok_or_else(|| "Unable to copy diagnostics".to_string())
}

struct LogsDirectory(PathBuf);

fn resource_sidecar_path(resource_dir: &Path) -> PathBuf {
    resolve_sidecar_path(resource_dir, TARGET_TRIPLE)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            None,
        ))
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .invoke_handler(tauri::generate_handler![
            companion_runtime_descriptor,
            runtime_status,
            companion_http_request,
            start_companion_frame_stream,
            resync_companion_frame_stream,
            stop_companion_frame_stream,
            restart_engine,
            set_launch_at_login,
            launch_at_login_status,
            open_prism_gt,
            open_logs,
            copy_safe_diagnostics
        ])
        .setup(|app| {
            let resource_dir = app.path().resource_dir()?;
            let app_data_dir = app.path().app_data_dir()?;
            let logs_dir = app_data_dir.join("logs");
            let score_root = app_data_dir.join("scores");
            let discovery_path = wizard_discovery_path()?;
            let supervisor = SupervisorHandle::launch(
                resource_sidecar_path(&resource_dir),
                logs_dir.clone(),
                discovery_path,
                score_root,
                app.package_info().version.to_string(),
            )
            .map_err(io_error)?;
            app.manage(LogsDirectory(logs_dir));
            app.manage(FrameBridge::default());
            app.manage(supervisor);
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build Wizard Joe Companion");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
            app_handle.state::<FrameBridge>().stop();
            app_handle.state::<SupervisorHandle>().shutdown();
        }
    });
}

fn wizard_discovery_path() -> Result<PathBuf, std::io::Error> {
    let home =
        std::env::var_os("HOME").ok_or_else(|| std::io::Error::other("HOME is unavailable"))?;
    Ok(wizard_discovery_path_from_home(Path::new(&home)))
}

fn wizard_discovery_path_from_home(home: &Path) -> PathBuf {
    home.join("Library")
        .join("Application Support")
        .join("Wizard Joe Companion")
        .join("connector-v1.json")
}

fn io_error(message: String) -> std::io::Error {
    std::io::Error::other(message)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn app_resource_resolution_uses_compiled_target() {
        let path = resource_sidecar_path(Path::new("/tmp/resources"));
        assert!(path.starts_with(Path::new("/tmp/resources/sidecar")));
        assert!(path.ends_with("wizard-joe-engine/wizard-joe-engine"));
        assert!(path.to_string_lossy().contains(TARGET_TRIPLE));
    }

    #[test]
    fn discovery_path_uses_the_locked_application_support_location() {
        assert_eq!(
            wizard_discovery_path_from_home(Path::new("/Users/wizard-test")),
            PathBuf::from(
                "/Users/wizard-test/Library/Application Support/Wizard Joe Companion/connector-v1.json"
            )
        );
    }
}
