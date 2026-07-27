# Robin HD RGBA Runtime Candidate

Date: 2026-07-27

## Status

Robin now has a deterministic, package-bound, review-only HD RGBA runtime
candidate. It extends the existing Python visualizer. It does not create a
second runtime, server architecture, controller, score engine, media clock, or
Prism connector.

The candidate is intentionally not present in the production character
registry. `runtime_admitted` is `false`, and the registry rejects the package
until the remaining acceptance gates are satisfied.

## Frozen Bindings

| Binding | Value |
| --- | --- |
| Character | `robin` |
| Pose count | 200 |
| Canvas | 1920 x 1080 RGBA |
| Render adapter | `asciline.hd_rgba_pose.v1` |
| Source/candidate library index | `sha256:1924a28a486971146df522ee1bdb4e0488d9d27eaa1ab0b3b8b928db6bf8d15c` |
| Character package | `sha256:561c2cb8c1adfbcf035920ef3139a92c7b1bc362195a3b44bf32952cb820c2c6` |
| Bound package assets | 14 |
| Runtime admission | false |

The generated package is local evidence under
`assets/reference/characters/robin_speech/compiled/robin/runtime-candidate/`.
The deterministic builder is
`tools/build_hd_rgba_character_candidate.py`.

## Architecture

`HDPoseFrameSource` is a package-selected renderer adapter beneath
`ProceduralWizardFrameSource`. It uses the same:

- authoritative Python `WizardFrameHub`;
- ordered remote-command inbox;
- runtime clock and state reducer;
- package-owned animation graph;
- performance application and score admission path;
- REST and WebSocket surfaces;
- Prism media connector and governance boundaries.

The adapter loads package-bound `.wjpose` RGBA shards and projects their pixels
onto the existing canvas protocol. It never uses PNG or SVG files as runtime
render assets.

## Centering Contract

Robin is authored on the left half of a shared 1920 x 1080 source canvas. The
adapter applies an exact `+480`-pixel horizontal presentation translation:

`1920 / 2 - 960 / 2 = 480`

This places the authored half-canvas midpoint at screen `x=960`. It preserves:

- source bytes and SHA-256 identity;
- 1:1 pixels with no resampling;
- the full 1920 x 1080 canvas;
- per-pose vertical registration;
- silhouette proportions and internal motion.

Stage locomotion is added after this baseline offset, so Robin can still move
purposefully around the screen.

## Protocol And Diagnostics

The adaptive protocol supports dense RGBA frames. Unchanged holds use a
13-byte empty delta and reuse the prior browser buffer without copying,
rehashing, or repainting it. Changed HD frames are verified by the Python
frame hub with SHA-256. `/api/avatar/wizard/frame-hashes` truthfully reports
`sha256` for this render mode; the browser no longer performs a redundant
byte-wise legacy FNV pass over each 8,294,400-byte frame.

## Verification

The focused HD runtime suite passed 8 of 8 tests:

- RGBA keyframe round trip;
- 13-byte unchanged hold;
- periodic keyframe behavior;
- exact translation with no resampling;
- package binding and fail-closed state;
- registry rejection while review-only;
- centered 1920 x 1080 source and truth trace;
- looping path plus twelve authored poses through the shared frame hub.

The direct controller exercise held 23.97 fps with zero hub failures. A fresh
browser demo completed the previously failing turn/path transition with no
hub restart, no decode error, and no resynchronization error. Browser
presentation recovered to 24/24 fps after its initial backlog.
An additional command-admission sweep selected all 200 package pose IDs with
zero rejections and zero hub failures. Two complete candidate rebuilds produced
byte-identical artifact hashes.

Continuous translated HD locomotion is not yet an acceptance-grade throughput
result. One observed motion window ran at approximately 22.5 server fps and
21 browser fps before recovering, with full-frame compressed packets around
0.5-0.7 MB. That performance limitation remains explicit and blocks production
admission.

## Truthful Capabilities

Implemented in this candidate:

- seven authored directional views with a declared northeast fallback;
- source-backed whole-pose actions;
- four-frame ground locomotion;
- authored flight, bank, hover, and landing sequences;
- direct selection of all 200 review poses;
- centered HD presentation and normalized stage movement.

Not implemented or admitted:

- authored blink overlays;
- governed viseme or mouth-shape speech performance;
- independent animation and technical acceptance;
- sustained HD motion throughput acceptance;
- production registry entry;
- product approval.

The runtime does not fabricate these capabilities. Unsupported behavior remains
denied or uses an explicit package-declared fallback.

## Reproduction

Build the local candidate:

```bash
python3 tools/build_hd_rgba_character_candidate.py \
  assets/reference/characters/robin_speech/compiled/robin/library-index.json \
  assets/reference/characters/robin_speech/compiled/robin/runtime-candidate
```

Run the focused verification:

```bash
python3 -m unittest tests.wizard.test_hd_rgba_runtime -v
```

Launch the local review runtime:

```bash
python3 tools/run_wizard_avatar_server.py \
  --host 127.0.0.1 \
  --port 8670 \
  --character-package \
  assets/reference/characters/robin_speech/compiled/robin/runtime-candidate/robin-character-package-v2.json
```

The ordinary 8665 observer remains the product-review surface. Replacing it
with this package is a separate acceptance action, not an implicit consequence
of building the candidate.
