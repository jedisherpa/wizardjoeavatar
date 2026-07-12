# Add Semantic Control Routes

Implement:

```text
GET  /api/avatar/wizard/state

POST /api/avatar/wizard/move
POST /api/avatar/wizard/path
POST /api/avatar/wizard/circle
POST /api/avatar/wizard/face
POST /api/avatar/wizard/action
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
