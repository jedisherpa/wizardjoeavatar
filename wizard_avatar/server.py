from __future__ import annotations

import asyncio
import hmac
import inspect
import ipaddress
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlsplit

from .commanding import CommandEnvelopeV1, CommandValidationError
from .frame_source import ProceduralWizardFrameSource
from .models import WizardCommand
from .media_session import (
    MEDIA_SESSION_MAX_BODY_BYTES,
    MediaSessionError,
    MediaSessionSnapshotV1,
)
from .stream import WizardFrameHub

try:
    from fastapi import Request as FastAPIRequest
    from fastapi import WebSocket as FastAPIWebSocket
except ImportError:  # pragma: no cover - create_app reports the install command.
    FastAPIRequest = Any
    FastAPIWebSocket = Any


ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web" / "avatar"
DEFINITIONS_DIR = ROOT / "wizard_avatar" / "definitions"
COMPANION_HEALTH_SCHEMA_VERSION = 1
COMPANION_PROTOCOL_VERSION = 1


def is_literal_loopback_host(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _authority_is_literal_loopback(value: str) -> bool:
    if not value or any(character.isspace() for character in value):
        return False
    try:
        parsed = urlsplit("//" + value)
        parsed_port = parsed.port
    except ValueError:
        return False
    return (
        parsed.hostname is not None
        and is_literal_loopback_host(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and parsed.path == ""
        and parsed.query == ""
        and parsed.fragment == ""
        and (parsed_port is None or 0 < parsed_port <= 65535)
    )


def _origin_is_literal_loopback(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        parsed_port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme in {"http", "https"}
        and parsed.hostname is not None
        and is_literal_loopback_host(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and parsed.path == ""
        and parsed.query == ""
        and parsed.fragment == ""
        and (parsed_port is None or 0 < parsed_port <= 65535)
    )


def _loopback_error(connection: Any) -> Optional[str]:
    client = connection.client
    if client is None or not is_literal_loopback_host(client.host):
        return "Non-loopback clients are not allowed"
    if not _authority_is_literal_loopback(connection.headers.get("host", "")):
        return "Host must be a literal loopback address"
    origin = connection.headers.get("origin")
    if origin and not _origin_is_literal_loopback(origin):
        return "Origin must be a literal loopback address"
    return None


def _bearer_matches(authorization: str, token: str) -> bool:
    if not token:
        return False
    expected = "Bearer " + token
    return hmac.compare_digest(authorization.encode("utf-8"), expected.encode("utf-8"))


def create_app(
    source: ProceduralWizardFrameSource | None = None,
    *,
    companion_mode: Optional[bool] = None,
    app_token: Optional[str] = None,
    shutdown_signal: Optional[Callable[[], Any]] = None,
):
    try:
        from fastapi import FastAPI, HTTPException, WebSocketDisconnect
        from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
    except ImportError as exc:
        raise RuntimeError("Install server dependencies with: python3 -m pip install -r requirements.txt") from exc

    frame_source = source or ProceduralWizardFrameSource()
    frame_hub = WizardFrameHub(frame_source)
    started_at_monotonic_ms = time.monotonic_ns() // 1_000_000
    if companion_mode is None:
        companion_mode = os.environ.get("WIZARD_COMPANION_MODE", "").lower() in {
            "1", "true", "yes", "on"
        }
    if app_token is None:
        app_token = os.environ.get("WIZARD_COMPANION_APP_TOKEN", "")
    connector_enabled = os.environ.get("WIZARD_MEDIA_CONNECTOR_ENABLED", "").lower() in {
        "1", "true", "yes", "on"
    }
    connector_token = os.environ.get("WIZARD_MEDIA_CONNECTOR_TOKEN", "")
    if companion_mode and not app_token:
        raise ValueError("WIZARD_COMPANION_APP_TOKEN is required in companion mode")
    if companion_mode and connector_token and hmac.compare_digest(app_token, connector_token):
        raise ValueError("Companion app token must be separate from the media connector token")

    @asynccontextmanager
    async def lifespan(_app: Any):
        try:
            yield
        finally:
            await frame_hub.stop()

    app = FastAPI(title="WizardJoeAvatar", lifespan=lifespan)
    app.state.frame_hub = frame_hub
    app.state.shutdown_requested = False

    if companion_mode:
        @app.middleware("http")
        async def companion_security(request: FastAPIRequest, call_next: Callable[..., Any]):
            loopback_error = _loopback_error(request)
            if loopback_error:
                return JSONResponse(status_code=403, content={"detail": loopback_error})
            media_connector_route = request.url.path.startswith(
                "/api/avatar/wizard/media-session"
            )
            app_api_route = request.url.path.startswith("/api/avatar/wizard/")
            mutation = request.method in {"POST", "PUT", "PATCH", "DELETE"}
            if (mutation or (app_api_route and not media_connector_route)) and not (
                media_connector_route
                or _bearer_matches(request.headers.get("authorization", ""), app_token)
            ):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return await call_next(request)

    def require_connector(request: FastAPIRequest) -> None:
        if not connector_enabled or not connector_token:
            raise HTTPException(status_code=503, detail="Media connector unavailable")
        if request.headers.get("origin"):
            raise HTTPException(status_code=403, detail="Browser-origin requests are not allowed")
        authorization = request.headers.get("authorization", "")
        if not _bearer_matches(authorization, connector_token):
            raise HTTPException(status_code=401, detail="Unauthorized")

    async def bounded_json_body(request: FastAPIRequest) -> bytes:
        if request.headers.get("content-type") != "application/json":
            raise HTTPException(status_code=415, detail="Content-Type must be application/json")
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MEDIA_SESSION_MAX_BODY_BYTES:
                    raise HTTPException(status_code=413, detail="Request body too large")
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid Content-Length") from exc
        chunks = bytearray()
        async for chunk in request.stream():
            chunks.extend(chunk)
            if len(chunks) > MEDIA_SESSION_MAX_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Request body too large")
        return bytes(chunks)

    def result_or_400(result):
        if not result.ok:
            raise HTTPException(status_code=400, detail=result.message)
        return result.state

    async def public_media_status() -> Dict[str, Any]:
        diagnostics = await frame_hub.media_session_status()
        session = diagnostics["session"]
        application = diagnostics["application"]
        scheduler_state = session["scheduler_state"]
        if not connector_enabled or not connector_token:
            status = "disabled"
        elif application["active"]:
            status = "animating"
        elif session["active_session_suffix"] is None:
            status = "waiting"
        elif scheduler_state == "clock_uncertain":
            status = "stale"
        elif scheduler_state in {"paused", "stopped", "ended", "no_session"}:
            status = "paused"
        else:
            status = "ready"
        return {
            "status": status,
            "active": bool(application["active"]),
            "source": application["source_slot"] or session["active_source_slot"],
            "scheduler_state": scheduler_state,
            "action": application["action"],
        }

    @app.get("/")
    async def root():
        return HTMLResponse((WEB_DIR / "index.html").read_text(encoding="utf-8"))

    @app.get("/api/companion/health")
    async def companion_health(request: FastAPIRequest):
        loopback_error = _loopback_error(request)
        if loopback_error:
            raise HTTPException(status_code=403, detail=loopback_error)
        hub_task = frame_hub._task
        return {
            "schema_version": COMPANION_HEALTH_SCHEMA_VERSION,
            "status": "shutting_down" if app.state.shutdown_requested else "ready",
            "runtime_epoch": frame_hub.runtime_epoch,
            "protocol_version": COMPANION_PROTOCOL_VERSION,
            "character_id": frame_source.character_package.character_id,
            "pid": os.getpid(),
            "started_at_monotonic_ms": started_at_monotonic_ms,
            "frame_hub_running": hub_task is not None and not hub_task.done(),
            "connector_enabled": connector_enabled and bool(connector_token),
        }

    @app.post("/api/companion/shutdown")
    async def companion_shutdown(request: FastAPIRequest):
        if not companion_mode:
            raise HTTPException(status_code=404, detail="Not found")
        if request.headers.get("origin"):
            raise HTTPException(status_code=403, detail="Browser-origin requests are not allowed")
        app.state.shutdown_requested = True
        await frame_hub.stop()
        if shutdown_signal is not None:
            signal_result = shutdown_signal()
            if inspect.isawaitable(signal_result):
                await signal_result
        return {"status": "shutting_down"}

    @app.post("/api/companion/reactions")
    async def companion_reactions(payload: Dict[str, Any]):
        if not companion_mode:
            raise HTTPException(status_code=404, detail="Not found")
        paused = payload.get("paused")
        if not isinstance(paused, bool) or set(payload) != {"paused"}:
            raise HTTPException(status_code=400, detail="Expected exactly one boolean paused field")
        return await frame_hub.set_reactions_paused(paused)

    @app.get("/avatar/{filename}")
    async def avatar_static(filename: str):
        allowed = {
            "reference-avatar-pose-cells.json",
            "reference-avatar-animation-graph-v2.json",
            "wizard-joe-character-package.json",
            "wizardClient.ts",
            "wizardCanvas.ts",
            "wizardControls.ts",
            "wizardDiagnostics.ts",
            "wizardDemo.ts",
            "wizardCodec.ts",
            "style.css",
        }
        if filename not in allowed:
            raise HTTPException(status_code=404, detail="Not found")
        if filename == "reference-avatar-pose-cells.json":
            return FileResponse(
                DEFINITIONS_DIR / "reference_avatar_pose_cells.json",
                media_type="application/json",
            )
        if filename == "reference-avatar-animation-graph-v2.json":
            return FileResponse(
                DEFINITIONS_DIR / "reference_avatar_animation_graph_v2.json",
                media_type="application/json",
            )
        if filename == "wizard-joe-character-package.json":
            return FileResponse(
                DEFINITIONS_DIR / "wizard_joe_character_package.json",
                media_type="application/json",
            )
        media = "application/javascript" if filename.endswith(".ts") else None
        return FileResponse(WEB_DIR / filename, media_type=media)

    @app.get("/api/avatar/wizard/state")
    async def state():
        return {
            "state": frame_source.current_state().as_public_dict(),
            "diagnostics": frame_source.diagnostics_dict(),
            "media": await public_media_status(),
        }

    @app.get("/api/avatar/wizard/frame-hashes")
    async def frame_hashes():
        return {
            "algorithm": "fnv1a32",
            "history": frame_hub.source_hash_history(),
        }

    @app.get("/api/avatar/wizard/replay")
    async def replay():
        return Response(
            frame_hub.replay_log.to_ndjson_bytes(),
            media_type="application/x-ndjson",
            headers={"X-Replay-SHA256": frame_hub.replay_log.sha256()},
        )

    @app.get("/api/avatar/wizard/poses")
    async def poses():
        return {"poses": list(frame_source.pose_ids)}

    @app.get("/api/avatar/wizard/character")
    async def character():
        package = frame_source.character_package
        return {
            "schema_version": package.schema_version,
            "character_id": package.character_id,
            "display_name": package.display_name,
            "renderer": package.renderer,
            "default_pose_id": package.default_pose_id,
            "capabilities": list(package.capabilities),
        }

    @app.post("/api/avatar/wizard/media-session")
    async def media_session(request: FastAPIRequest):
        require_connector(request)
        body = await bounded_json_body(request)
        try:
            snapshot = MediaSessionSnapshotV1.from_json(body)
        except MediaSessionError as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": exc.code, "path": exc.path},
            ) from exc
        ack = await frame_hub.accept_media_session(snapshot)
        return dict(ack.to_dict())

    @app.get("/api/avatar/wizard/media-session/status")
    async def media_session_status(request: FastAPIRequest):
        require_connector(request)
        return await frame_hub.media_session_status()

    async def apply(command_type: str, payload: Dict[str, Any]):
        command = WizardCommand(command_type, payload)
        result = await frame_hub.apply_command(command)
        return result_or_400(result)

    @app.post("/api/avatar/wizard/move")
    async def move(payload: Dict[str, Any]):
        return await apply("move", payload)

    @app.post("/api/avatar/wizard/path")
    async def path(payload: Dict[str, Any]):
        return await apply("path", payload)

    @app.post("/api/avatar/wizard/circle")
    async def circle(payload: Dict[str, Any]):
        return await apply("circle", payload)

    @app.post("/api/avatar/wizard/figure-eight")
    async def figure_eight(payload: Dict[str, Any]):
        return await apply("figure_eight", payload)

    @app.post("/api/avatar/wizard/face")
    async def face(payload: Dict[str, Any]):
        return await apply("face", payload)

    @app.post("/api/avatar/wizard/action")
    async def action(payload: Dict[str, Any]):
        return await apply("action", payload)

    @app.post("/api/avatar/wizard/pose")
    async def pose(payload: Dict[str, Any]):
        return await apply("pose", payload)

    @app.post("/api/avatar/wizard/control")
    async def control(payload: Dict[str, Any]):
        return await apply("control", payload)

    @app.post("/api/avatar/wizard/prism-signal")
    async def prism_signal(payload: Dict[str, Any]):
        return await apply("prism_signal", payload)

    @app.post("/api/avatar/wizard/expression")
    async def expression(payload: Dict[str, Any]):
        return await apply("expression", payload)

    @app.post("/api/avatar/wizard/speak")
    async def speak(payload: Dict[str, Any]):
        return await apply("speak", payload)

    @app.post("/api/avatar/wizard/speech-stop")
    async def speech_stop(payload: Optional[Dict[str, Any]] = None):
        return await apply("speech_stop", payload or {})

    @app.post("/api/avatar/wizard/stop")
    async def stop(payload: Optional[Dict[str, Any]] = None):
        return await apply("stop", payload or {})

    @app.post("/api/avatar/wizard/reset")
    async def reset(payload: Optional[Dict[str, Any]] = None):
        state = await apply("reset", payload or {})
        frame_hub.force_keyframe()
        return state

    @app.post("/api/avatar/wizard/command")
    async def ordered_command(payload: Dict[str, Any]):
        try:
            envelope = CommandEnvelopeV1.from_mapping(payload)
        except CommandValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        ack, result = await frame_hub.apply_envelope(envelope)
        if not result.ok:
            raise HTTPException(
                status_code=400,
                detail={"ack": ack.to_dict(), "message": result.message},
            )
        return {"ack": ack.to_dict(), "state": result.state}

    @app.websocket("/ws/ping")
    async def ping_ws(websocket: FastAPIWebSocket):
        await websocket.accept()
        await websocket.send_text("pong")
        await websocket.close()

    @app.websocket("/ws/avatar/wizard")
    async def wizard_ws(websocket: FastAPIWebSocket):
        if companion_mode:
            if _loopback_error(websocket) or not _bearer_matches(
                websocket.headers.get("authorization", ""), app_token
            ):
                await websocket.close(code=1008)
                return
        await websocket.accept()
        _codec = websocket.query_params.get("codec", "adaptive")
        await websocket.send_text(
            f"INIT:{frame_source.fps}:5:{frame_source.cols}:{frame_source.rows}:0:0:0.000"
        )
        subscriber = await frame_hub.subscribe()

        async def receiver():
            try:
                while True:
                    message = await websocket.receive_text()
                    try:
                        payload = json.loads(message)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(payload, dict) or "type" not in payload:
                        continue
                    if payload["type"] == "resync":
                        await frame_hub.enqueue_keyframe(subscriber)
                    else:
                        await frame_hub.apply_command(
                            WizardCommand(str(payload["type"]), dict(payload.get("payload", {})))
                        )
            except Exception:
                return

        receiver_task = asyncio.create_task(receiver())
        try:
            while True:
                data = await subscriber.queue.get()
                await websocket.send_bytes(data)
        except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
            return
        finally:
            frame_hub.unsubscribe(subscriber)
            receiver_task.cancel()

    return app
