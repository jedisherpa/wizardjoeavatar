# Implement Movement in World Space

Use a fixed 60 Hz simulation step.

Render at the selected ASCILINE frame rate.

State:

```python
class MovementState:
    position_x: float
    position_z: float
    velocity_x: float
    velocity_z: float
    target_x: float | None
    target_z: float | None
    speed: float
    acceleration: float
    deceleration: float
```

Defaults:

```text
walk speed: 1.25 world units per second
acceleration: 4.0 units per second squared
deceleration: 5.0 units per second squared
turn speed: 360 degrees per second
arrival tolerance: 0.05 world units
```

Implement:

```python
move_to(x, z)
move_relative(dx, dz)
walk_left(distance)
walk_right(distance)
walk_forward(distance)
walk_backward(distance)
follow_path(points)
walk_circle(center_x, center_z, radius, clockwise)
stop()
face(direction)
return_to_center()
```

Forward means decreasing `z`, toward the camera.

Backward means increasing `z`, away from the camera.

Use world bounds.

Do not allow the wizard, hat, staff, or robe to leave the visible stage.

Calculate allowed x bounds from:

- projected scale
- character width
- staff width
- screen padding

Use at least four stage-cell columns of visible padding.
