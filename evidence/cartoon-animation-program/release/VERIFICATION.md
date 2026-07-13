# Final Verification

Tested implementation: `a5f0cc1eea3d75f6f69b8d5221e6eb2da249d48f`

Production runtime: ASCILINE Python on `127.0.0.1:8765`

## Result

The production driver passed 153 Python tests, Python-only scope validation,
program/ownership validation, real-browser interaction and visual review, and a
600-second mixed-control soak.

The soak held 59.986 simulation Hz and 23.994 presentation FPS. It processed
5,767 control/action/speech/Prism requests at 25.914 ms p95 latency. Three normal
viewers decoded 14,401 frames apiece to the same final SHA-256; the deliberately
slow viewer decoded 2,470 frames. There were zero command errors, decode errors,
sequence regressions, or hub queue drops.

## Browser Matrix

- Repeat continuously moved through shuffled pose cycles while traversing world space.
- Takeoff, hover, free flight, altitude scaling, and landing remained on-screen.
- The popup exposed Auto plus all 39 authored poses.
- A pose override remained active while direct movement continued.
- Sanitized Prism review cues changed expression/gesture without changing control ownership.
- Speech opened the authored mouth region and displayed matching bottom captions.
- A forced service restart recovered the WebSocket automatically without decode errors.

## Reusability

Character identity and pose content now enter through a versioned character
package. A second fixture character with a distinct pose library renders through
the same frame source, controller, world projection, codec, and transport tests.

## Persistent Service

`tools/install_local_wizard_service.sh` renders and installs a portable macOS
launch agent with `RunAtLoad` and `KeepAlive`. The installed service remains live
until `tools/stop_local_wizard_service.sh` is run.
