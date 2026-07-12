# Implement a Perspective Floor Procedurally

Treat the floor as a world plane.

Use world coordinates:

```text
x: horizontal position
z: depth from the camera
```

Default world limits:

```text
x minimum: -5.0
x maximum: 5.0
z near: 1.5
z far: 10.0
```

Use this reference projection:

```python
def project_world_to_screen(
    x: float,
    z: float,
    width: int,
    height: int,
) -> tuple[float, float, float]:
    horizon_y = height * 0.56
    near_y = height * 0.95

    z_near = 1.5
    z_far = 10.0

    depth = (z_far - z) / (z_far - z_near)
    depth = clamp(depth, 0.0, 1.0)

    scale = 0.55 + depth * 0.75

    screen_x = width * 0.5 + x * width * 0.075 * scale
    screen_y = horizon_y + depth * (near_y - horizon_y)

    return screen_x, screen_y, scale
```

Tune values only when visual tests prove a better result.

Use the same projection for:

- wizard position
- wizard scale
- contact shadow
- floor intersections
- future props

Generate floor tiles in world space.

For each floor tile:

```python
tile_color = (
    FLOOR_LIGHT
    if (tile_x + tile_z) % 2 == 0
    else FLOOR_ALTERNATE
)
```

Project the four corners.

Fill the projected quadrilateral.

Reduce contrast with distance.

At the horizon, both tile colors should approach white.
