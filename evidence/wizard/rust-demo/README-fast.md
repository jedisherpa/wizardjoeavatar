# Rust Wizard Avatar Demo Evidence

- mode: `fast`
- websocket: `ws://127.0.0.1:49237/ws/avatar/wizard?codec=adaptive`
- init: `INIT:24:5:480:270:0:0:0.000:EPOCH:1:CELL_BYTES:4:CODEC:1`
- total frames: `123`
- observed fps: `23.72`
- average wire/raw ratio: `0.0160`

## Codec Tags

- tag `2`: `109` frames
- tag `3`: `14` frames

## Steps

- `01-load-environment`: 3 frames, sequence `Some(0)` to `Some(2)` - Load fixed white environment and receive initial stream
- `02-spawn-center`: 3 frames, sequence `Some(3)` to `Some(5)` - Spawn wizard in the center
- `03-idle`: 5 frames, sequence `Some(6)` to `Some(10)` - Idle for three seconds
- `04-blink-window`: 3 frames, sequence `Some(11)` to `Some(13)` - Observe deterministic blink window
- `05-happy`: 3 frames, sequence `Some(14)` to `Some(16)` - Change to happy expression
- `06-speak`: 5 frames, sequence `Some(17)` to `Some(21)` - Speak one test line
- `07-walk-left`: 5 frames, sequence `Some(22)` to `Some(26)` - Walk left
- `08-walk-right`: 5 frames, sequence `Some(27)` to `Some(31)` - Turn and walk right
- `09-walk-away`: 5 frames, sequence `Some(32)` to `Some(36)` - Walk away from camera
- `10-walk-toward`: 5 frames, sequence `Some(37)` to `Some(41)` - Walk toward camera
- `11-walk-front-left`: 5 frames, sequence `Some(42)` to `Some(46)` - Walk front-left
- `12-walk-back-right`: 5 frames, sequence `Some(47)` to `Some(51)` - Walk back-right
- `13-clockwise-circle`: 10 frames, sequence `Some(52)` to `Some(61)` - Walk one clockwise circle
- `14-counterclockwise-circle`: 10 frames, sequence `Some(62)` to `Some(71)` - Walk one counterclockwise circle
- `15-figure-eight`: 10 frames, sequence `Some(72)` to `Some(81)` - Walk a figure-eight
- `16-stop-center`: 5 frames, sequence `Some(82)` to `Some(86)` - Stop in the center
- `17-think`: 5 frames, sequence `Some(87)` to `Some(91)` - Think
- `18-point`: 5 frames, sequence `Some(92)` to `Some(96)` - Point
- `19-explain`: 5 frames, sequence `Some(97)` to `Some(101)` - Explain
- `20-cast-magic`: 5 frames, sequence `Some(102)` to `Some(106)` - Cast magic
- `21-react`: 5 frames, sequence `Some(107)` to `Some(111)` - React
- `22-neutral-idle`: 3 frames, sequence `Some(112)` to `Some(114)` - Return to neutral idle
- `23-final-idle`: 8 frames, sequence `Some(115)` to `Some(122)` - Continue idling for ten seconds
