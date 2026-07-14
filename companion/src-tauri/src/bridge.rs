use crate::lifecycle::ConnectionInfo;
use base64::Engine as _;
use serde::Serialize;
use serde_json::json;
use std::io;
use std::net::{Ipv4Addr, SocketAddr, SocketAddrV4, TcpStream};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    mpsc, Arc, Mutex,
};
use std::thread::{self, JoinHandle};
use std::time::Duration;
use tauri::{AppHandle, Emitter};
use tungstenite::{
    client::client_with_config, protocol::WebSocketConfig, ClientRequestBuilder, Message,
};

const FRAME_EVENT_NAME: &str = "companion-frame";
const MAX_FRAME_MESSAGE_BYTES: usize = 2 * 1024 * 1024;

#[derive(Default)]
pub struct FrameBridge {
    worker: Mutex<Option<FrameWorker>>,
}

struct FrameWorker {
    stop: Arc<AtomicBool>,
    control: mpsc::Sender<String>,
    join: JoinHandle<()>,
}

#[derive(Clone, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum FrameEvent {
    Text { data: String },
    Binary { base64: String },
}

impl FrameBridge {
    pub fn start(
        &self,
        app: AppHandle,
        event_name: &str,
        connection: ConnectionInfo,
    ) -> Result<(), String> {
        if event_name != FRAME_EVENT_NAME {
            return Err("frame_event_not_allowed".to_string());
        }
        self.stop();
        let stop = Arc::new(AtomicBool::new(false));
        let worker_stop = Arc::clone(&stop);
        let (control, controls) = mpsc::channel();
        let join = thread::Builder::new()
            .name("wizard-frame-bridge".to_string())
            .spawn(move || run_frame_bridge(app, connection, worker_stop, controls))
            .map_err(|_| "frame_bridge_start_failed".to_string())?;
        let worker = FrameWorker {
            stop,
            control,
            join,
        };
        match self.worker.lock() {
            Ok(mut guard) => *guard = Some(worker),
            Err(poisoned) => *poisoned.into_inner() = Some(worker),
        }
        Ok(())
    }

    pub fn resync(&self, epoch: Option<u64>, reason: &str) -> Result<(), String> {
        let message = json!({
            "type": "resync",
            "payload": { "epoch": epoch, "reason": reason }
        })
        .to_string();
        let guard = self
            .worker
            .lock()
            .map_err(|_| "frame_bridge_unavailable".to_string())?;
        guard
            .as_ref()
            .ok_or_else(|| "frame_bridge_not_started".to_string())?
            .control
            .send(message)
            .map_err(|_| "frame_bridge_unavailable".to_string())
    }

    pub fn stop(&self) {
        let worker = match self.worker.lock() {
            Ok(mut guard) => guard.take(),
            Err(poisoned) => poisoned.into_inner().take(),
        };
        if let Some(worker) = worker {
            worker.stop.store(true, Ordering::Release);
            let _ = worker.join.join();
        }
    }
}

impl Drop for FrameBridge {
    fn drop(&mut self) {
        self.stop();
    }
}

fn run_frame_bridge(
    app: AppHandle,
    connection: ConnectionInfo,
    stop: Arc<AtomicBool>,
    controls: mpsc::Receiver<String>,
) {
    let mut retry = 0_u32;
    while !stop.load(Ordering::Acquire) {
        if let Ok(mut socket) = connect(&connection) {
            retry = 0;
            loop {
                if stop.load(Ordering::Acquire) {
                    let _ = socket.close(None);
                    return;
                }
                while let Ok(control) = controls.try_recv() {
                    if socket.send(Message::Text(control.into())).is_err() {
                        break;
                    }
                }
                match socket.read() {
                    Ok(Message::Text(text)) => {
                        let _ = app.emit(
                            FRAME_EVENT_NAME,
                            FrameEvent::Text {
                                data: text.to_string(),
                            },
                        );
                    }
                    Ok(Message::Binary(bytes)) => {
                        let encoded = base64::engine::general_purpose::STANDARD.encode(bytes);
                        let _ = app.emit(FRAME_EVENT_NAME, FrameEvent::Binary { base64: encoded });
                    }
                    Ok(Message::Close(_)) => break,
                    Ok(_) => {}
                    Err(tungstenite::Error::Io(error))
                        if matches!(
                            error.kind(),
                            io::ErrorKind::WouldBlock | io::ErrorKind::TimedOut
                        ) => {}
                    Err(_) => break,
                }
            }
        }
        let delay_ms = (300_u64 * 2_u64.pow(retry.min(4))).min(4_000);
        retry = retry.saturating_add(1);
        sleep_interruptibly(&stop, Duration::from_millis(delay_ms));
    }
}

fn connect(connection: &ConnectionInfo) -> Result<tungstenite::WebSocket<TcpStream>, &'static str> {
    let address = SocketAddr::V4(SocketAddrV4::new(Ipv4Addr::LOCALHOST, connection.port));
    let timeout = Duration::from_millis(750);
    let stream = TcpStream::connect_timeout(&address, timeout).map_err(|_| "frame_unreachable")?;
    stream
        .set_read_timeout(Some(Duration::from_millis(200)))
        .map_err(|_| "frame_io_failed")?;
    stream
        .set_write_timeout(Some(timeout))
        .map_err(|_| "frame_io_failed")?;
    let uri = format!(
        "ws://127.0.0.1:{}/ws/avatar/wizard?codec=adaptive",
        connection.port
    )
    .parse()
    .map_err(|_| "frame_uri_invalid")?;
    let request = ClientRequestBuilder::new(uri)
        .with_header("Authorization", format!("Bearer {}", connection.token));
    let config = WebSocketConfig::default()
        .max_message_size(Some(MAX_FRAME_MESSAGE_BYTES))
        .max_frame_size(Some(MAX_FRAME_MESSAGE_BYTES));
    client_with_config(request, stream, Some(config))
        .map(|(socket, _response)| socket)
        .map_err(|_| "frame_handshake_failed")
}

fn sleep_interruptibly(stop: &AtomicBool, duration: Duration) {
    let slices = (duration.as_millis() / 50).max(1);
    for _ in 0..slices {
        if stop.load(Ordering::Acquire) {
            break;
        }
        thread::sleep(Duration::from_millis(50));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn frame_event_payload_never_contains_connection_credentials() {
        let payload = serde_json::to_value(FrameEvent::Binary {
            base64: "AQID".to_string(),
        })
        .unwrap();
        assert_eq!(payload["type"], "binary");
        assert_eq!(payload["base64"], "AQID");
        assert!(payload.get("token").is_none());
    }
}
