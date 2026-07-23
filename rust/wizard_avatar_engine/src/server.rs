use crate::capability_manifest::wizard_capability_document;
use crate::controller::WizardCommand;
use crate::frame_source::ProceduralWizardFrameSource;
use crate::hub::AvatarFrameHub;
use crate::newsroom::{NewsPerformanceCueV1, NewsroomError};
use crate::newsroom_scene::{
    newsroom_foreground_catalog, newsroom_foreground_graph_asset, newsroom_post_character_catalog,
    newsroom_post_character_graph_asset,
};
use crate::pose_graph_runtime::{
    previous_runtime_pose_id, resolved_runtime_pose_id, runtime_actor_transform,
    runtime_pose_graph_catalog, verify_graph_bytes, RuntimePoseGraphEntry,
};
use anyhow::Context;
use axum::body::Body;
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{DefaultBodyLimit, Path, Query, State};
use axum::http::header::{CACHE_CONTROL, CONTENT_ENCODING, CONTENT_TYPE, ETAG};
use axum::http::{HeaderValue, StatusCode};
use axum::response::{Html, IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use futures_util::{SinkExt, StreamExt};
use serde::Deserialize;
use serde_json::{json, Value};
use std::net::SocketAddr;
use std::str::FromStr;
use std::sync::Arc;
use tokio::net::TcpListener;

const MAX_COMMAND_BODY_BYTES: usize = 16 * 1_024;

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
        .route("/avatar/newsroom_controls.js", get(newsroom_controls_js))
        .route("/avatar/asciline_codec.js", get(asciline_codec_js))
        .route("/avatar/asciline_client.js", get(asciline_client_js))
        .route("/avatar/canvas_renderer.js", get(canvas_renderer_js))
        .route(
            "/avatar/pixel_graph_renderer.js",
            get(pixel_graph_renderer_js),
        )
        .route("/avatar/pixel_graph_worker.js", get(pixel_graph_worker_js))
        .route(
            "/api/avatar/wizard/v2/pose-graphs/catalog",
            get(pose_graph_catalog),
        )
        .route(
            "/api/avatar/wizard/v2/pose-graphs/semantic/:semantic_id",
            get(pose_graph_by_semantic),
        )
        .route(
            "/api/avatar/wizard/v2/pose-graphs/source/:source_record_id",
            get(pose_graph_by_source),
        )
        .route(
            "/api/avatar/wizard/v2/pose-clips/catalog",
            get(pose_clip_catalog),
        )
        .route(
            "/api/avatar/wizard/v2/newsroom-graphs/foreground/catalog",
            get(newsroom_foreground_graph_catalog),
        )
        .route(
            "/api/avatar/wizard/v2/newsroom-graphs/foreground/:scene/:target_id",
            get(newsroom_foreground_graph),
        )
        .route(
            "/api/avatar/wizard/v2/newsroom-graphs/post-character/catalog",
            get(newsroom_post_character_graph_catalog),
        )
        .route(
            "/api/avatar/wizard/v2/newsroom-graphs/post-character/:scene/:target_id",
            get(newsroom_post_character_graph),
        )
        .route(
            "/avatar/reference-avatar-cells.json",
            get(reference_avatar_cells_json),
        )
        .route(
            "/avatar/reference-avatar-pose-cells.json",
            get(reference_avatar_pose_cells_json),
        )
        .route("/api/avatar/wizard/state", get(state))
        .route("/api/avatar/wizard/v2/capabilities", get(capabilities))
        .route(
            "/api/avatar/wizard/v2/newsroom/cue",
            post(command_newsroom_cue),
        )
        .route(
            "/api/avatar/wizard/v2/newsroom/receipt",
            get(latest_newsroom_receipt),
        )
        .route(
            "/api/avatar/wizard/v2/newsroom/actor-sample",
            get(newsroom_actor_sample),
        )
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
        .route("/api/avatar/wizard/pose", post(command_pose))
        .route("/api/avatar/wizard/pose-clip", post(command_pose_clip))
        .route("/api/avatar/wizard/scene", post(command_scene))
        .route("/api/avatar/wizard/expression", post(command_expression))
        .route("/api/avatar/wizard/speak", post(command_speak))
        .route("/api/avatar/wizard/stop", post(command_stop))
        .route("/api/avatar/wizard/reset", post(command_reset))
        .route("/ws/avatar/wizard", get(wizard_ws))
        .layer(DefaultBodyLimit::max(MAX_COMMAND_BODY_BYTES))
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

async fn newsroom_controls_js() -> impl IntoResponse {
    (
        [("content-type", "application/javascript; charset=utf-8")],
        include_str!("../web/newsroom_controls.js"),
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

async fn pixel_graph_renderer_js() -> impl IntoResponse {
    (
        [("content-type", "application/javascript; charset=utf-8")],
        include_str!("../web/pixel_graph_renderer.js"),
    )
}

async fn pixel_graph_worker_js() -> impl IntoResponse {
    (
        [("content-type", "application/javascript; charset=utf-8")],
        include_str!("../web/pixel_graph_worker.js"),
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
        "build": {
            "git_sha": crate::BUILD_GIT_SHA,
        },
        "runtime_pose_id": resolved_runtime_pose_id(&state),
        "state": state,
        "diagnostics": diagnostics,
    }))
}

async fn pose_graph_catalog() -> Response {
    match runtime_pose_graph_catalog() {
        Ok(catalog) => Json(catalog.manifest().clone()).into_response(),
        Err(error) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({
                "error": "runtime_pose_graph_catalog_unavailable",
                "message": error,
            })),
        )
            .into_response(),
    }
}

async fn pose_clip_catalog() -> Json<Value> {
    Json(json!({
        "schema_version": 1,
        "clip_count": crate::pose_clip::POSE_CLIPS.len(),
        "clips": crate::pose_clip::POSE_CLIPS,
    }))
}

async fn newsroom_foreground_graph_catalog(
) -> Json<crate::newsroom_scene::NewsroomForegroundCatalog> {
    Json(newsroom_foreground_catalog())
}

async fn newsroom_post_character_graph_catalog(
) -> Json<crate::newsroom_scene::NewsroomForegroundCatalog> {
    Json(newsroom_post_character_catalog())
}

async fn newsroom_foreground_graph(Path((scene, target_id)): Path<(String, String)>) -> Response {
    let Ok(mode) = crate::state::SceneMode::from_str(&scene) else {
        return (
            StatusCode::NOT_FOUND,
            Json(json!({"error": "newsroom_foreground_scene_not_found", "scene": scene})),
        )
            .into_response();
    };
    let Some((sha256, bytes)) = newsroom_foreground_graph_asset(mode, &target_id) else {
        return (
            StatusCode::NOT_FOUND,
            Json(json!({
                "error": "newsroom_foreground_graph_not_found",
                "scene": scene,
                "target_id": target_id,
            })),
        )
            .into_response();
    };
    newsroom_graph_response(sha256, bytes)
}

async fn newsroom_post_character_graph(
    Path((scene, target_id)): Path<(String, String)>,
) -> Response {
    let Ok(mode) = crate::state::SceneMode::from_str(&scene) else {
        return (
            StatusCode::NOT_FOUND,
            Json(json!({"error": "newsroom_post_character_scene_not_found", "scene": scene})),
        )
            .into_response();
    };
    let Some((sha256, bytes)) = newsroom_post_character_graph_asset(mode, &target_id) else {
        return (
            StatusCode::NOT_FOUND,
            Json(json!({
                "error": "newsroom_post_character_graph_not_found",
                "scene": scene,
                "target_id": target_id,
            })),
        )
            .into_response();
    };
    newsroom_graph_response(sha256, bytes)
}

fn newsroom_graph_response(sha256: &str, bytes: &'static [u8]) -> Response {
    let etag = HeaderValue::from_str(&format!("\"{sha256}\""))
        .expect("promoted newsroom graph hash is a valid header value");
    Response::builder()
        .status(StatusCode::OK)
        .header(CONTENT_TYPE, "application/json; charset=utf-8")
        .header(CONTENT_ENCODING, "gzip")
        .header(CACHE_CONTROL, "public, max-age=31536000, immutable")
        .header(ETAG, etag)
        .body(Body::from(bytes))
        .expect("newsroom foreground response headers are valid")
}

async fn pose_graph_by_semantic(Path(semantic_id): Path<String>) -> Response {
    let Ok(catalog) = runtime_pose_graph_catalog() else {
        return pose_graph_catalog_unavailable();
    };
    let Some(entry) = catalog.primary_for_semantic_id(&semantic_id) else {
        return pose_graph_not_found("semantic_id", &semantic_id);
    };
    serve_pose_graph(catalog, entry).await
}

async fn pose_graph_by_source(Path(source_record_id): Path<String>) -> Response {
    let Ok(catalog) = runtime_pose_graph_catalog() else {
        return pose_graph_catalog_unavailable();
    };
    let Some(entry) = catalog.for_source_record_id(&source_record_id) else {
        return pose_graph_not_found("source_record_id", &source_record_id);
    };
    serve_pose_graph(catalog, entry).await
}

async fn serve_pose_graph(
    catalog: &crate::pose_graph_runtime::RuntimePoseGraphCatalog,
    entry: &RuntimePoseGraphEntry,
) -> Response {
    let path = match catalog.graph_path(entry) {
        Ok(path) => path,
        Err(error) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"error": "pose_graph_storage_unavailable", "message": error})),
            )
                .into_response();
        }
    };
    let bytes = match tokio::fs::read(&path).await {
        Ok(bytes) => bytes,
        Err(error) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({
                    "error": "pose_graph_read_failed",
                    "message": format!("read {}: {error}", path.display()),
                })),
            )
                .into_response();
        }
    };
    if let Err(error) = verify_graph_bytes(entry, &bytes) {
        return (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": "pose_graph_integrity_failed", "message": error})),
        )
            .into_response();
    }
    let etag = match HeaderValue::from_str(&format!("\"{}\"", entry.graph_sha256)) {
        Ok(value) => value,
        Err(error) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"error": "pose_graph_etag_failed", "message": error.to_string()})),
            )
                .into_response();
        }
    };
    Response::builder()
        .status(StatusCode::OK)
        .header(CONTENT_TYPE, "application/json; charset=utf-8")
        .header(CONTENT_ENCODING, "gzip")
        .header(CACHE_CONTROL, "public, max-age=31536000, immutable")
        .header(ETAG, etag)
        .body(Body::from(bytes))
        .expect("pose graph response headers are valid")
}

fn pose_graph_catalog_unavailable() -> Response {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(json!({"error": "runtime_pose_graph_catalog_unavailable"})),
    )
        .into_response()
}

fn pose_graph_not_found(field: &str, value: &str) -> Response {
    (
        StatusCode::NOT_FOUND,
        Json(json!({"error": "pose_graph_not_found", field: value})),
    )
        .into_response()
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

async fn command_newsroom_cue(
    State(app): State<AppState>,
    Json(cue): Json<NewsPerformanceCueV1>,
) -> Response {
    match app.hub.apply_newsroom_cue(cue).await {
        Ok(receipt) => (StatusCode::OK, Json(receipt)).into_response(),
        Err(error) => newsroom_error_response(error),
    }
}

async fn latest_newsroom_receipt(State(app): State<AppState>) -> Response {
    match app.hub.latest_newsroom_receipt().await {
        Some(receipt) => (StatusCode::OK, Json(receipt)).into_response(),
        None => (
            StatusCode::NOT_FOUND,
            Json(json!({"error": "newsroom_receipt_not_found"})),
        )
            .into_response(),
    }
}

async fn newsroom_actor_sample(State(app): State<AppState>) -> Response {
    match app.hub.newsroom_actor_sample().await {
        Ok(sample) => (StatusCode::OK, Json(sample)).into_response(),
        Err(error) => newsroom_error_response(error),
    }
}

fn newsroom_error_response(error: NewsroomError) -> Response {
    let (status, code) = match error {
        NewsroomError::StaleCue { .. } | NewsroomError::SequenceConflict => {
            (StatusCode::CONFLICT, "newsroom_cue_conflict")
        }
        NewsroomError::ActorSampleBusy => {
            (StatusCode::TOO_MANY_REQUESTS, "newsroom_actor_sample_busy")
        }
        NewsroomError::ActorSample(_)
        | NewsroomError::InvalidActorSample(_)
        | NewsroomError::InvalidCatalog(_)
        | NewsroomError::UnknownSemanticPose(_)
        | NewsroomError::UnsupportedInternalPose(_) => {
            (StatusCode::INTERNAL_SERVER_ERROR, "newsroom_runtime_error")
        }
        _ => (StatusCode::UNPROCESSABLE_ENTITY, "invalid_newsroom_cue"),
    };
    (
        status,
        Json(json!({"error": code, "message": error.to_string()})),
    )
        .into_response()
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

async fn command_pose(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "pose", payload).await
}

async fn command_pose_clip(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    apply_command(app, "pose_clip", payload).await
}

async fn command_scene(
    State(app): State<AppState>,
    Json(payload): Json<Value>,
) -> impl IntoResponse {
    let Some(scene) = payload.get("scene").and_then(Value::as_str) else {
        return (
            StatusCode::BAD_REQUEST,
            Json(json!({"ok": false, "message": "scene is required"})),
        );
    };
    let Ok(mode) = crate::state::SceneMode::from_str(scene) else {
        return (
            StatusCode::BAD_REQUEST,
            Json(json!({"ok": false, "message": format!("unsupported scene: {scene}")})),
        );
    };
    let state = app.hub.set_scene_mode(mode).await;
    (
        StatusCode::OK,
        Json(json!({"ok": true, "message": "ok", "state": state})),
    )
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
                        if send_frame_state(&mut sender, packet.sequence, packet.simulation_tick, &packet.state).await.is_err() {
                            break;
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
    send_frame_state(
        sender,
        bootstrap.sequence,
        bootstrap.simulation_tick,
        &bootstrap.state,
    )
    .await?;
    sender
        .send(Message::Binary(bootstrap.encoded.to_vec()))
        .await
        .map_err(|_| ())?;
    Ok(Some(bootstrap.sequence))
}

async fn send_frame_state(
    sender: &mut futures_util::stream::SplitSink<WebSocket, Message>,
    sequence: u32,
    simulation_tick: u64,
    state: &crate::state::WizardState,
) -> Result<(), ()> {
    sender
        .send(Message::Text(
            pixelgraph_state_payload(sequence, simulation_tick, state).to_string(),
        ))
        .await
        .map_err(|_| ())
}

fn pixelgraph_state_payload(
    sequence: u32,
    simulation_tick: u64,
    state: &crate::state::WizardState,
) -> Value {
    json!({
        "type": "pixelgraph_state",
        "sequence": sequence,
        "simulation_tick": simulation_tick,
        "pose_id": resolved_runtime_pose_id(state),
        "previous_pose_id": previous_runtime_pose_id(state),
        "presentation_pose_id": presentation_pose_id(state),
        "presentation_override_active": presentation_override_active(state),
        "pose_blend": state.pose_blend,
        "world_position": state.world_position,
        "actor_transform": runtime_actor_transform(state),
        "velocity": state.velocity,
        "facing": state.facing,
        "locomotion": state.locomotion,
        "action": state.action,
        "effect_state": state.effect_state,
        "scene_mode": state.scene_mode,
        "walk_phase": state.walk_phase,
        "contact_marker": state.contact_marker,
        "pose_clip_id": state.pose_clip_id,
        "pose_clip_step": state.pose_clip_step,
        "pose_clip_generation": state.pose_clip_generation,
        "speech_active": state.speech_id.is_some(),
        "speech_id": state.speech_id,
        "expression": state.expression,
        "mouth": state.mouth,
    })
}

fn presentation_pose_id(state: &crate::state::WizardState) -> String {
    if !presentation_override_active(state) {
        return resolved_runtime_pose_id(state);
    }
    if state.speech_id.is_some() {
        return mouth_graph_pose_id(state.mouth).to_string();
    }
    expression_graph_pose_id(state.expression).to_string()
}

fn presentation_override_active(state: &crate::state::WizardState) -> bool {
    use crate::state::{Direction, Expression, Locomotion, MouthShape};

    state.pose_id.is_none()
        && state.pose_clip_id.is_none()
        && state.locomotion == Locomotion::Idle
        && state.facing == Direction::South
        && (state.speech_id.is_some()
            || state.expression != Expression::Neutral
            || state.mouth != MouthShape::Closed)
}

fn expression_graph_pose_id(expression: crate::state::Expression) -> &'static str {
    use crate::state::Expression;

    match expression {
        Expression::Neutral => "emotion_neutral",
        Expression::Happy => "emotion_joy",
        Expression::Amused => "emotion_amused",
        Expression::Thinking => "emotion_contemplative",
        Expression::Surprised => "emotion_surprise",
        Expression::Worried => "emotion_concern",
        Expression::Confident => "emotion_confident",
        Expression::Focused => "emotion_determined",
        Expression::Skeptical => "emotion_skepticism",
        Expression::Explaining => "speak_explain_open",
    }
}

fn mouth_graph_pose_id(mouth: crate::state::MouthShape) -> &'static str {
    use crate::state::MouthShape;

    match mouth {
        MouthShape::Closed => "idle_speaking_ready",
        MouthShape::OpenSmall => "speak_explain_precise",
        MouthShape::OpenMedium => "speak_explain_sequence",
        MouthShape::OpenWide => "speak_emphasize_high",
        MouthShape::Rounded => "speak_question",
        MouthShape::Smile => "speak_reassure",
        MouthShape::Frown => "emotion_sadness",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::{Direction, Expression, Locomotion, MouthShape, WizardState};

    #[test]
    fn authored_expression_and_mouth_presentations_resolve_to_verified_graphs() {
        let catalog = runtime_pose_graph_catalog().expect("runtime graph catalog");
        for expression in Expression::ALL {
            assert!(
                catalog
                    .primary_for_semantic_id(expression_graph_pose_id(expression))
                    .is_some(),
                "missing expression graph for {expression:?}"
            );
        }
        for mouth in [
            MouthShape::Closed,
            MouthShape::OpenSmall,
            MouthShape::OpenMedium,
            MouthShape::OpenWide,
            MouthShape::Rounded,
            MouthShape::Smile,
            MouthShape::Frown,
        ] {
            assert!(
                catalog
                    .primary_for_semantic_id(mouth_graph_pose_id(mouth))
                    .is_some(),
                "missing mouth graph for {mouth:?}"
            );
        }
    }

    #[test]
    fn pixelgraph_state_transmits_the_actual_mouth_and_authored_presentation_pose() {
        let mut state = WizardState {
            speech_id: Some("speech-test".to_string()),
            mouth: MouthShape::OpenWide,
            expression: Expression::Happy,
            ..WizardState::default()
        };
        let payload = pixelgraph_state_payload(17, 29, &state);
        assert_eq!(payload["sequence"], 17);
        assert_eq!(payload["simulation_tick"], 29);
        assert_eq!(payload["speech_active"], true);
        assert_eq!(payload["speech_id"], "speech-test");
        assert_eq!(payload["mouth"], "open_wide");
        assert_eq!(payload["expression"], "happy");
        assert_eq!(payload["presentation_override_active"], true);
        assert_eq!(payload["presentation_pose_id"], "speak_emphasize_high");

        state.speech_id = None;
        state.mouth = MouthShape::Smile;
        let expression_payload = pixelgraph_state_payload(18, 30, &state);
        assert_eq!(expression_payload["presentation_pose_id"], "emotion_joy");
    }

    #[test]
    fn facial_presentation_never_replaces_explicit_choreography_or_locomotion() {
        let mut explicit = WizardState {
            pose_id: Some("magic_cast_begin".to_string()),
            expression: Expression::Surprised,
            mouth: MouthShape::OpenWide,
            ..WizardState::default()
        };
        assert!(!presentation_override_active(&explicit));
        assert_eq!(presentation_pose_id(&explicit), "magic_cast_begin");

        explicit.pose_id = None;
        explicit.locomotion = Locomotion::Walking;
        assert!(!presentation_override_active(&explicit));

        explicit.locomotion = Locomotion::Idle;
        explicit.facing = Direction::East;
        assert!(!presentation_override_active(&explicit));
    }
}
