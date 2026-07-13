from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .frame_source import ProceduralWizardFrameSource
from .models import WizardCommand
from .stream import WizardFrameHub

try:
    from fastapi import WebSocket as FastAPIWebSocket
except ImportError:  # pragma: no cover - create_app reports the install command.
    FastAPIWebSocket = Any


ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web" / "avatar"
DEFINITIONS_DIR = ROOT / "wizard_avatar" / "definitions"


def create_app(source: ProceduralWizardFrameSource | None = None):
    try:
        from fastapi import FastAPI, HTTPException, WebSocketDisconnect
        from fastapi.responses import FileResponse, HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install server dependencies with: python3 -m pip install -r requirements.txt") from exc

    frame_source = source or ProceduralWizardFrameSource()
    frame_hub = WizardFrameHub(frame_source)
    app = FastAPI(title="WizardJoeAvatar")

    def result_or_400(result):
        if not result.ok:
            raise HTTPException(status_code=400, detail=result.message)
        return result.state

    @app.get("/")
    async def root():
        return HTMLResponse((WEB_DIR / "index.html").read_text(encoding="utf-8"))

    @app.get("/avatar/{filename}")
    async def avatar_static(filename: str):
        allowed = {
            "reference-avatar-pose-cells.json",
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
        media = "application/javascript" if filename.endswith(".ts") else None
        return FileResponse(WEB_DIR / filename, media_type=media)

    @app.get("/api/avatar/wizard/state")
    async def state():
        return {
            "state": frame_source.current_state().as_public_dict(),
            "diagnostics": frame_source.diagnostics_dict(),
        }

    @app.get("/api/avatar/wizard/frame-hashes")
    async def frame_hashes():
        return {
            "algorithm": "fnv1a32",
            "history": frame_hub.source_hash_history(),
        }

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

    @app.post("/api/avatar/wizard/expression")
    async def expression(payload: Dict[str, Any]):
        return await apply("expression", payload)

    @app.post("/api/avatar/wizard/speak")
    async def speak(payload: Dict[str, Any]):
        return await apply("speak", payload)

    @app.post("/api/avatar/wizard/stop")
    async def stop(payload: Optional[Dict[str, Any]] = None):
        return await apply("stop", payload or {})

    @app.post("/api/avatar/wizard/reset")
    async def reset(payload: Optional[Dict[str, Any]] = None):
        state = await apply("reset", payload or {})
        frame_hub.force_keyframe()
        return state

    @app.websocket("/ws/ping")
    async def ping_ws(websocket: FastAPIWebSocket):
        await websocket.accept()
        await websocket.send_text("pong")
        await websocket.close()

    @app.websocket("/ws/avatar/wizard")
    async def wizard_ws(websocket: FastAPIWebSocket):
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
