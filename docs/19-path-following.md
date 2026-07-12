# Add a Path-Following Controller

Represent paths as:

```json
{
  "points": [
    {"x": -2.0, "z": 4.0},
    {"x": 2.0, "z": 4.0},
    {"x": 2.0, "z": 7.0},
    {"x": -2.0, "z": 7.0}
  ],
  "loop": false,
  "speed": 1.25
}
```

The controller must:

- move to each point
- slow down before sharp corners
- select a new facing direction
- maintain walk-cycle continuity
- stop cleanly
- support cancellation
- reject out-of-bounds paths

Do not generate new path points every render frame.
