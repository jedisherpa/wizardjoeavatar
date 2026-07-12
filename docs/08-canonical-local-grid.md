# Define the Wizard’s Canonical Local Grid

Use this logical character grid:

```text
width: 34 cells
height: 52 cells
feet/root anchor: (17, 51)
```

The canonical front-facing wizard at scale 1.0 should occupy approximately:

```text
34 stage columns
52 stage rows
```

Use nearest-neighbor cell resampling for depth scaling.

Do not blur, antialias, or interpolate glyph cells.

Quantize display scale to one-eighth increments:

```python
display_scale = round(projected_scale * 8) / 8
```

This prevents constant resampling flicker while moving forward and backward.
