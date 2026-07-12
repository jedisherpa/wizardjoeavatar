# Implement Procedural Walking

Use a distance-driven walk phase.

```python
walk_phase += distance_travelled / stride_length
walk_phase %= 1.0
```

Recommended stride length:

```text
0.85 world units
```

Use:

```python
swing = sin(walk_phase * 2π)
lift = max(0, sin(walk_phase * 2π))
opposite_lift = max(0, sin(walk_phase * 2π + π))
```

Apply:

- one leg forward while the other moves back
- opposite arm swing
- one-cell body bob
- subtle hat lag
- subtle beard lag
- small staff lag
- one-cell boot lift during the forward portion

Keep movement stepped and cell-aligned.

Do not use subpixel blur.

The walking animation must be derived from phase, not from wall-clock frame numbers, so it remains stable at different frame rates.
