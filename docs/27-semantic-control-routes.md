# Add Semantic Control Routes

Implement:

```text
GET  /api/avatar/wizard/state

POST /api/avatar/wizard/move
POST /api/avatar/wizard/path
POST /api/avatar/wizard/circle
POST /api/avatar/wizard/face
POST /api/avatar/wizard/action
POST /api/avatar/wizard/pose
POST /api/avatar/wizard/expression
POST /api/avatar/wizard/speak
POST /api/avatar/wizard/stop
POST /api/avatar/wizard/reset
```

Example move request:

```json
{
  "x": 2.0,
  "z": 5.0,
  "speed": 1.25
}
```

Circle request:

```json
{
  "center_x": 0,
  "center_z": 5,
  "radius": 2,
  "clockwise": true,
  "duration_seconds": 10
}
```

Action request:

```json
{
  "action": "explaining",
  "duration_ms": 2400
}
```

Timed pose-showcase request:

```json
{
  "pose_id": "front_idle",
  "duration_ms": 900
}
```

The pose ID must exist in the generated reference library. Passing `null` clears the showcase override. This channel changes presentation pose only; locomotion continues so the automated demo can move while cycling the full library.

Validate all values.

Reject:

- unknown actions
- unsupported expressions
- out-of-bounds coordinates
- negative speeds
- oversized paths
- stale commands
- arbitrary code
- arbitrary file paths
