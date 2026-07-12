# Define the Visual Output Grid

Use a wide 16:9 ASCILINE stage.

Default medium profile:

```text
columns: 240
rows: 135
target FPS: 24
render mode: full-color ASCII
pixel mode: false
codec: adaptive
```

High profile:

```text
columns: 320
rows: 180
target FPS: 30
```

Low profile:

```text
columns: 180
rows: 101
target FPS: 15
```

Use full-color ASCII mode rather than ASCILINE pixel mode for the primary implementation.

The wizard should be formed from colored glyph cells.

A pixel-mode fallback may be added later, but it must not replace the primary procedural ASCII implementation.

Use the exact byte structure expected by the checked-out ASCILINE browser decoder.
