# Protocol Baseline

## Framebuffer Structure

Primary mode is an ASCILINE-compatible color-cell stream. A framebuffer is a
row-major byte array:

```text
[char, R, G, B] repeated once per cell
```

`char` is a single ASCII-compatible mask byte: space means empty/background and
any non-space value means draw a visible square tile. `R`, `G`, and `B` are
unsigned 8-bit color channels. For a `240 x 135` stage the raw frame size is:

```text
240 * 135 * 4 = 129600 bytes
```

Pixel mode in upstream ASCILINE uses `[B, G, R]` cells, but WizardJoeAvatar does
not use pixel mode for its primary implementation.

## Adaptive Frame Envelope

Adaptive binary messages are:

```text
[uint32 frame_index big-endian][uint8 tag][payload]
```

Legacy non-adaptive binary messages are:

```text
[uint32 frame_index big-endian][raw framebuffer]
```

WizardJoeAvatar's dedicated endpoint defaults to adaptive mode.

## Tags

```text
0 RAW
  payload = raw framebuffer bytes

1 ZLIB
  payload = zlib(raw framebuffer bytes)

2 DELTA
  payload = zlib(indices ++ values)
  indices = changed cell indices as uint32 little-endian
  values = changed cell values, 4 bytes per changed color cell

3 RLE_FULL
  payload = zlib(runs)
  run = [uint16 count little-endian][cell bytes]
```

The decoder must process frames sequentially because deltas patch the previous
decoded full frame.

## Initialization

The browser receives a text initialization message before binary frames:

```text
INIT:{fps}:{render_mode}:{cols}:{rows}:{pixel_mode_int}:{source_index}:{duration_seconds}
```

WizardJoeAvatar uses:

```text
INIT:24:5:240:135:0:0:0.000
```

for the default medium profile.

## Keyframes and Resync

A full frame is required when:

- no previous decoded frame exists
- the frame shape changes
- the frame index is divisible by 48
- a reconnect or explicit resync occurs

The first frame sent to each new WebSocket connection is a keyframe.

## Browser Rendering Assumptions

The browser renderer:

- fills the Canvas background white before drawing
- uses a square tile grid
- reads cells in row-major order
- draws each non-space cell as a colored square tile
- keeps a text-selection buffer in sync with glyph bytes
- applies decoded frames in arrival order

This differs intentionally from upstream ASCILINE's dark default Canvas fill so
the WizardJoeAvatar fixed white studio environment is honored.
