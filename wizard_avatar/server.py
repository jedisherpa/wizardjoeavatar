from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .frame_source import ProceduralWizardFrameSource
from .character_registry import load_character_registry
from .models import WizardCommand
from .stream import WizardFrameHub

try:
    from fastapi import WebSocket as FastAPIWebSocket
except ImportError:  # pragma: no cover - create_app reports the install command.
    FastAPIWebSocket = Any


ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web" / "avatar"
DEFINITIONS_DIR = ROOT / "wizard_avatar" / "definitions"


def create_app(
    source: ProceduralWizardFrameSource | None = None,
    *,
    cols: int = 240,
    rows: int = 135,
    fps: float = 24.0,
):
    try:
        from fastapi import FastAPI, HTTPException, WebSocketDisconnect
        from fastapi.responses import FileResponse, HTMLResponse
    except ImportError as exc:
        raise RuntimeError("Install server dependencies with: python3 -m pip install -r requirements.txt") from exc

    registry = load_character_registry()
    if source is None:
        sources = {
            character_id: ProceduralWizardFrameSource(
                cols=cols,
                rows=rows,
                fps=fps,
                character_package_path=package.pose_library.parent / ("crystail_character_package.json" if character_id == "crystail-v1" else "wizard_joe_character_package.json"),
            )
            for character_id, package in registry.packages.items()
        }
        frame_source = sources[registry.default_character_id]
    else:
        frame_source = source
        sources = {source.character_package.character_id: source}
    frame_hub = WizardFrameHub(frame_source)
    frame_hubs = {character_id: (frame_hub if candidate is frame_source else WizardFrameHub(candidate)) for character_id, candidate in sources.items()}
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
            "reference-avatar-animation-graph-v2.json",
            "wizard-joe-character-package.json",
            "crystail-character-package.json",
            "crystail-pose-cells.json",
            "crystail-animation-graph.json",
            "crystail-character-manifest.json",
            "crystail-animation-matrix.json",
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
        crystail_files = {
            "crystail-character-package.json": "crystail_character_package.json",
            "crystail-pose-cells.json": "crystail_pose_cells.json",
            "crystail-animation-graph.json": "crystail_animation_graph.json",
            "crystail-character-manifest.json": "crystail_character_manifest.json",
            "crystail-animation-matrix.json": "crystail_animation_matrix.json",
        }
        if filename in crystail_files:
            return FileResponse(DEFINITIONS_DIR / crystail_files[filename], media_type="application/json")
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

    async def apply(command_type: str, payload: Dict[str, Any]):
        command = WizardCommand(command_type, payload)
        result = await frame_hub.apply_command(command)
        return result_or_400(result)

    def character_source(character_id: str) -> ProceduralWizardFrameSource:
        if character_id == "wizard":
            return frame_source
        candidate = sources.get(character_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Unknown character")
        return candidate

    def character_hub(character_id: str) -> WizardFrameHub:
        if character_id == "wizard":
            return frame_hub
        character_source(character_id)
        return frame_hubs[character_id]

    @app.get("/api/avatar/characters")
    async def characters():
        available = {entry["character_id"]: entry for entry in registry.public_entries()}
        return {
            "default_character_id": registry.default_character_id,
            "characters": [available[character_id] for character_id in sources],
        }

    @app.get("/api/avatar/{character_id}/state")
    async def character_state(character_id: str):
        candidate = character_source(character_id)
        return {"state": candidate.current_state().as_public_dict(), "diagnostics": candidate.diagnostics_dict()}

    @app.get("/api/avatar/{character_id}/frame-hashes")
    async def character_frame_hashes(character_id: str):
        return {"algorithm": "fnv1a32", "history": character_hub(character_id).source_hash_history()}

    @app.get("/api/avatar/{character_id}/poses")
    async def character_poses(character_id: str):
        return {"poses": list(character_source(character_id).pose_ids)}

    @app.get("/api/avatar/{character_id}/character")
    async def character_metadata(character_id: str):
        package = character_source(character_id).character_package
        return {
            "schema_version": package.schema_version,
            "character_id": package.character_id,
            "display_name": package.display_name,
            "renderer": package.renderer,
            "default_pose_id": package.default_pose_id,
            "capabilities": list(package.capabilities),
        }

    @app.post("/api/avatar/{character_id}/{command_type}")
    async def character_command(character_id: str, command_type: str, payload: Optional[Dict[str, Any]] = None):
        command_aliases = {"prism-signal": "prism_signal", "speech-stop": "speech_stop", "figure-eight": "figure_eight"}
        command_name = command_aliases.get(command_type, command_type.replace("-", "_"))
        result = await character_hub(character_id).apply_command(WizardCommand(command_name, payload or {}))
        if command_name == "reset":
            character_hub(character_id).force_keyframe()
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

    @app.websocket("/ws/avatar/{character_id}")
    async def character_ws(websocket: FastAPIWebSocket, character_id: str):
        if character_id not in sources:
            await websocket.close(code=4404)
            return
        candidate = character_source(character_id)
        hub = character_hub(character_id)
        await websocket.accept()
        await websocket.send_text(
            f"INIT:{candidate.fps}:5:{candidate.cols}:{candidate.rows}:0:0:0.000"
        )
        subscriber = await hub.subscribe()

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
                        await hub.enqueue_keyframe(subscriber)
                    else:
                        await hub.apply_command(WizardCommand(str(payload["type"]), dict(payload.get("payload", {}))))
            except Exception:
                return

        receiver_task = asyncio.create_task(receiver())
        try:
            while True:
                await websocket.send_bytes(await subscriber.queue.get())
        except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
            return
        finally:
            hub.unsubscribe(subscriber)
            receiver_task.cancel()

    return app
