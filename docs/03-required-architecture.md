# Required Architecture

Implement this path:

```text
Avatar control command
        ↓
Wizard world state
        ↓
Locomotion controller
        ↓
Directional view resolver
        ↓
Procedural body and layer renderer
        ↓
Expression and mouth overlays
        ↓
Fixed environment compositor
        ↓
ASCILINE cell framebuffer
        ↓
Adaptive frame encoder
        ↓
WebSocket
        ↓
Browser decoder
        ↓
Canvas
```

The authoritative state must be semantic.

Example:

```json
{
  "character_id": "asciline-wizard-v1",
  "world_position": {"x": 1.2, "z": 4.8},
  "velocity": {"x": -0.4, "z": 0.2},
  "facing": "southwest",
  "locomotion": "walking",
  "action": "explaining",
  "expression": "focused",
  "mouth": "open_small",
  "walk_phase": 0.42,
  "blink_phase": 0.0,
  "staff_state": "held",
  "speech_id": null
}
```

The renderer must generate visible cells from this state.

The state must not contain arbitrary drawing code.
