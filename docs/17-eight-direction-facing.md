# Implement Eight-Direction Facing

Calculate heading from velocity:

```python
angle = atan2(velocity_x, -velocity_z)
```

Map the angle to one of eight directions.

Use directional hysteresis of approximately 8 degrees so the view does not rapidly flicker near a boundary.

When stopped:

- preserve the previous facing direction
- or turn toward an explicitly requested target

Turning must not teleport the feet.

The root anchor must remain stable across view changes.
