# Rust Wizard Avatar Demo Evidence

- mode: `full`
- websocket: `ws://127.0.0.1:49251/ws/avatar/wizard?codec=adaptive`
- init: `INIT:24:5:480:270:0:0:0.000:EPOCH:1:CELL_BYTES:4:CODEC:1`
- total frames: `1023`
- observed fps: `23.97`
- average wire/raw ratio: `0.0126`

## Codec Tags

- tag `2`: `936` frames
- tag `3`: `87` frames

## Steps

- `01-load-environment`: 12 frames, sequence `Some(0)` to `Some(11)` - Load fixed white environment and receive initial stream
- `02-spawn-center`: 12 frames, sequence `Some(12)` to `Some(23)` - Spawn wizard in the center
- `03-idle`: 72 frames, sequence `Some(24)` to `Some(95)` - Idle for three seconds
- `04-blink-window`: 6 frames, sequence `Some(96)` to `Some(101)` - Observe deterministic blink window
- `05-happy`: 12 frames, sequence `Some(102)` to `Some(113)` - Change to happy expression
- `06-speak`: 39 frames, sequence `Some(114)` to `Some(152)` - Speak one test line
- `07-walk-left`: 34 frames, sequence `Some(153)` to `Some(186)` - Walk left
- `08-walk-right`: 53 frames, sequence `Some(187)` to `Some(239)` - Turn and walk right
- `09-walk-away`: 34 frames, sequence `Some(240)` to `Some(273)` - Walk away from camera
- `10-walk-toward`: 34 frames, sequence `Some(274)` to `Some(307)` - Walk toward camera
- `11-walk-front-left`: 34 frames, sequence `Some(308)` to `Some(341)` - Walk front-left
- `12-walk-back-right`: 34 frames, sequence `Some(342)` to `Some(375)` - Walk back-right
- `13-clockwise-circle`: 72 frames, sequence `Some(376)` to `Some(447)` - Walk one clockwise circle
- `14-counterclockwise-circle`: 72 frames, sequence `Some(448)` to `Some(519)` - Walk one counterclockwise circle
- `15-figure-eight`: 72 frames, sequence `Some(520)` to `Some(591)` - Walk a figure-eight
- `16-stop-center`: 34 frames, sequence `Some(592)` to `Some(625)` - Stop in the center
- `17-think`: 29 frames, sequence `Some(626)` to `Some(654)` - Think
- `18-point`: 29 frames, sequence `Some(655)` to `Some(683)` - Point
- `19-explain`: 29 frames, sequence `Some(684)` to `Some(712)` - Explain
- `20-cast-magic`: 34 frames, sequence `Some(713)` to `Some(746)` - Cast magic
- `21-react`: 24 frames, sequence `Some(747)` to `Some(770)` - React
- `22-neutral-idle`: 12 frames, sequence `Some(771)` to `Some(782)` - Return to neutral idle
- `23-final-idle`: 240 frames, sequence `Some(783)` to `Some(1022)` - Continue idling for ten seconds
