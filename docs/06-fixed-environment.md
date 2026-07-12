# Define the Fixed Environment

The environment must never scroll.

The upper background must be pure or nearly pure white.

Use:

```text
background: #FFFFFF
floor light tile: #FCFCFB
floor alternate tile: #F5F5F3
floor grid line: #ECECEA
contact shadow: rgba(0, 0, 0, 0.08)
```

The floor begins at approximately 56% of the stage height.

For a 240 × 135 stage:

```text
horizon row: 76
near floor row: 128
```

Do not draw a dark horizon line.

Fade the floor pattern toward pure white as it approaches the horizon.

The floor must look like a very faint white studio checkerboard, not a black-and-white chessboard.

The background must contain no:

- walls
- furniture
- trees
- sky
- windows
- logos
- decorative objects

The only environment elements are:

- white void
- faint floor
- subtle contact shadow

Render the background once and cache it.

Every frame should begin by copying the cached background.

This fixed background is important because it makes ASCILINE delta encoding efficient.
