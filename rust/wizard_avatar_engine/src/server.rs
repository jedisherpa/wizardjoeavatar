use crate::capability_manifest::wizard_capability_document;
use crate::controller::WizardCommand;
use crate::frame_source::ProceduralWizardFrameSource;
use crate::hub::AvatarFrameHub;
use anyhow::Context;
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{Query, State};
use axum::http::StatusCode;
use axum::response::{Html, IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use futures_util::{SinkExt, StreamExt};
use serde::Deserialize;
use serde_json::{json, Value};
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::TcpListener;

#[derive(Clone)]
pub struct AppState {
    hub: Arc<AvatarFrameHub>,
}

impl AppState {
    #[must_use]
    pub fn new(source: ProceduralWizardFrameSource) -> Self {
        Self {
            hub: AvatarFrameHub::start(source),
        }
    }
}

#[derive(Debug, Deserialize)]
struct WsQuery {
    #[serde(default = "default_codec")]
    codec: String,
}

fn default_codec() -> String {
    "adaptive".to_string()
}

pub fn app(source: ProceduralWizardFrameSource) -> Router {
    Router::new()
        .route("/", get(root))
        .route("/avatar/wizard.js", get(wizard_js))
        .route("/avatar/motion_tour.js", get(motion_tour_js))
        .route("/avatar/asciline_codec.js", get(asciline_codec_js))
        .route("/avatar/asciline_client.js", get(asciline_client_js))
        .route("/avatar/canvas_renderer.js", get(canvas_renderer_js))
        .route(
            "/avatar/reference-avatar-cells.json",
            get(reference_avatar_cells_json),
        )
        .route(
            "/avatar/reference-avatar-pose-cells.json",
            get(reference_avatar_pose_cells_json),
        )
        .route("/api/avatar/wizard/state", get(state))
        .route("/api/avatar/wizard/v1/capabilities", get(capabilities))
        .route("/api/avatar/wizard/capabilities", get(capabilities))
        .route("/api/avatar/wizard/move", post(command_move))
        .route("/api/avatar/wizard/walk-left", post(command_walk_left))
        .route("/api/avatar/wizard/walk-right", post(command_walk_right))
        .route(
            "/api/avatar/wizard/walk-forward",
            post(command_walk_forward),
        )
        .route(
            "/api/avatar/wizard/walk-backward",
            post(command_walk_backward),
        )
        .route(
            "/api/avatar/wizard/return-to-center",
            post(command_return_to_center),
        )
        .route("/api/avatar/wizard/path", post(command_path))
        .route("/api/avatar/wizard/circle", post(command_circle))
        .route(
            "/api/avatar/wizard/figure-eight",
            post(command_figure_eight),
        )
        .route("/api/avatar/wizard/face", post(command_face))
        .route("/api/avatar/wizard/action", post(command_action))
        .route("/api/avatar/wizard/expression", post(command_expression))
        .route("/api/avatar/wizard/speak", post(command_speak))
        .route("/api/avatar/wizard/stop", post(command_stop))
        .route("/api/avatar/wizard/reset", post(command_reset))
        .route("/ws/avatar/wizard", get(wizard_ws))
        .with_state(AppState::new(source))
}

pub async fn serve(addr: SocketAddr, source: ProceduralWizardFrameSource) -> anyhow::Result<()> {
    let listener = TcpListener::bind(addr)
        .await
        .with_context(|| format!("failed to bind {addr}"))?;
    axum::serve(listener, app(source))
        .await
        .context("wizard avatar server failed")
}

async fn root() -> Html<&'static str> {
    Html(include_str!("../web/index.html"))
}

async fn wizard_js() -> impl IntoResponse {
    (
        [("content-type", "application/javascript; charset=utf-8")],
        include_str!("../web/wizard.js"),
    )
}

async fn motion_tour_js() -> impl IntoResponse {
    (
        [("content-type", "application/javascript; charset=utf-8")],
        include_str!("../web/motion_tour.js"),
    )
}

async fn asciline_codec_js() -> impl IntoResponse {
    (
        [("content-type", "application/javascript; charset=utf-8")],
        include_str!("../web/asciline_codec.js"),
    )
}

async fn asciline_client_js() -> impl IntoResponse {
    (
        [("content-type", "application/javascript; charset=utf-8")],
        include_str!("../web/asciline_client.js"),
    )
}

async fn canvas_renderer_js() -> impl IntoResponse {
    (
        [("content-type", "application/javascript; charset=utf-8")],
        include_str!("../web/canvas_renderer.js"),
    )
}

async fn reference_avatar_cells_json() -> impl IntoResponse {
    (
        [("content-type", "application/json; charset=utf-8")],
        include_str!("../../../wizard_avatar/definitions/reference_avatar_cells.json"),
    )
}

async fn reference_avatar_pose_cells_json() -> impl IntoResponse {
    (
        [("content-type", "application/json; charset=utf-8")],
        include_str!("../../../wizard_avatar/definitions/reference_avatar_pose_cells.json"),
    )
}

async fn state(State(app): State<AppState>) -> Json<Value> {
    let state = app.hub.current_state().await;
    let diagnostics = app.hub.diagnostics().await;
    Json(json!({
        "state": state,
        "diagnostics": diagnostics,
    }))
}

async fn capabilities() -> Response {
    match wizard_capability_document() {
        Ok(document) => Json(document).into_response(),
        Err(error) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({
                "error": "capability_manifest_unavailable",
                "message": error,
            })),
        )
            .into_response(),
    }
}

async fn command_move(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "move", payload).await
}

async fn command_path(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "path", payload).await
}

async fn command_walk_left(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "walk_left", payload).await
}

async fn command_walk_right(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "walk_right", payload).await
}

async fn command_walk_forward(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "walk_forward", payload).await
}

async fn command_walk_backward(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "walk_backward", payload).await
}

async fn command_return_to_center(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "return_to_center", payload).await
}

async fn command_circle(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "circle", payload).await
}

async fn command_figure_eight(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "figure_eight", payload).await
}

async fn command_face(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "face", payload).await
}

async fn command_action(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "action", payload).await
}

async fn command_expression(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "expression", payload).await
}

async fn command_speak(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "speak", payload).await
}

async fn command_stop(
    State(app): State<AppState>,
    payload: Option<Json<Value>>,
) -> impl IntoResponse {
    apply_command(
        app,
        "stop",
        payload
            .map(|Json(value)| value)
            .unwrap_or_else(|| json!({})),
    )
    .await
}

async fn command_reset(
    State(app): State<AppState>,
    payload: Option<Json<Value>>,
) -> impl IntoResponse {
    apply_command(
        app,
        "reset",
        payload
            .map(|Json(value)| value)
            .unwrap_or_else(|| json!({})),
    )
    .await
}

async fn apply_command(app: AppState, command_type: &str, payload: Value) -> impl IntoResponse {
    let result = app
        .hub
        .apply_command(WizardCommand::new(command_type, payload))
        .await;
    let status = if result.ok {
        StatusCode::OK
    } else {
        StatusCode::BAD_REQUEST
    };
    (status, Json(result))
}

async fn wizard_ws(
    State(app): State<AppState>,
    Query(query): Query<WsQuery>,
    ws: WebSocketUpgrade,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, app, query.codec))
}

async fn handle_socket(socket: WebSocket, app: AppState, codec: String) {
    let (mut sender, mut receiver) = socket.split();
    if codec != "adaptive" {
        let _ = sender
            .send(Message::Text(
                "Error: only adaptive codec is supported".to_string(),
            ))
            .await;
        return;
    }

    let init = format!(
        "INIT:{}:5:{}:{}:0:0:0.000:EPOCH:{}:CELL_BYTES:4:CODEC:1",
        app.hub.fps(),
        app.hub.cols(),
        app.hub.rows(),
        app.hub.epoch()
    );
    if sender.send(Message::Text(init)).await.is_err() {
        return;
    }

    let mut frames = app.hub.subscribe();
    let mut last_sent = match send_bootstrap(&mut sender, &app.hub).await {
        Ok(sequence) => sequence,
        Err(()) => return,
    };

    loop {
        tokio::select! {
            maybe_message = receiver.next() => {
                let Some(Ok(message)) = maybe_message else {
                    break;
                };
                if let Message::Text(text) = message {
                    let is_resync = serde_json::from_str::<Value>(&text)
                        .ok()
                        .and_then(|value| value.get("type").and_then(Value::as_str).map(str::to_owned))
                        .is_some_and(|message_type| message_type == "resync");
                    if is_resync {
                        match send_bootstrap(&mut sender, &app.hub).await {
                            Ok(sequence) => last_sent = sequence,
                            Err(()) => break,
                        }
                    } else if let Ok(command) = serde_json::from_str::<WizardCommand>(&text) {
                        let _ = app.hub.apply_command(command).await;
                    }
                }
            }
            frame = frames.recv() => {
                match frame {
                    Ok(packet) => {
                        if last_sent.is_some_and(|sequence| packet.sequence <= sequence) {
                            continue;
                        }
                        let contiguous = last_sent
                            .is_none_or(|sequence| packet.sequence == sequence.wrapping_add(1));
                        if packet.epoch != app.hub.epoch() || !contiguous {
                            match send_bootstrap(&mut sender, &app.hub).await {
                                Ok(sequence) => last_sent = sequence,
                                Err(()) => break,
                            }
                            continue;
                        }
                        if sender.send(Message::Binary(packet.encoded.to_vec())).await.is_err() {
                            break;
                        }
                        last_sent = Some(packet.sequence);
                    }
                    Err(tokio::sync::broadcast::error::RecvError::Lagged(_)) => {
                        match send_bootstrap(&mut sender, &app.hub).await {
                            Ok(sequence) => last_sent = sequence,
                            Err(()) => break,
                        }
                    }
                    Err(tokio::sync::broadcast::error::RecvError::Closed) => break,
                }
            }
        }
    }
}

async fn send_bootstrap(
    sender: &mut futures_util::stream::SplitSink<WebSocket, Message>,
    hub: &AvatarFrameHub,
) -> Result<Option<u32>, ()> {
    let bootstrap = hub.bootstrap().await.map_err(|_| ())?;
    let Some(bootstrap) = bootstrap else {
        return Ok(None);
    };
    sender
        .send(Message::Binary(bootstrap.encoded.to_vec()))
        .await
        .map_err(|_| ())?;
    Ok(Some(bootstrap.sequence))
}
