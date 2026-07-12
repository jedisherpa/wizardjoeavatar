# Implement Circular Walking

Implement circle movement as a generated path.

```python
x = center_x + radius * cos(theta)
z = center_z + radius * sin(theta)
```

For clockwise motion:

```python
theta -= angular_speed * dt
```

For counterclockwise motion:

```python
theta += angular_speed * dt
```

The wizard’s facing must follow the tangent of the circle.

Do not face toward the center unless explicitly requested.

Support:

- full circles
- partial arcs
- configurable radius
- configurable duration
- clockwise
- counterclockwise
- stop at starting point
- continue into another path

Create a demo with:

1. one clockwise circle
2. one counterclockwise circle
3. one figure-eight path
