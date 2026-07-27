# Speech HD RGBA Runtime Candidate

Date: 2026-07-27

## Status

Speech now has a deterministic, package-bound, review-only HD RGBA runtime
candidate. It extends the existing Python visualizer and the same renderer
adapter used by Robin. It does not create a second runtime, server
architecture, controller, score engine, media clock, or Prism connector.

The candidate is intentionally absent from the production character registry.
`runtime_admitted` is `false`, and the registry rejects the package until the
remaining acceptance gates are satisfied.

## Frozen Bindings

| Binding | Value |
| --- | --- |
| Character | `speech` |
| Pose count | 200 |
| Canvas | 1920 x 1080 RGBA |
| Render adapter | `asciline.hd_rgba_pose.v1` |
| Source/candidate library index | `sha256:b0d93a1a019bd77671868616f800ed242a5e6e9e22539e82018f081ce6bd34ce` |
| Character package | `sha256:405a87e3047fb153395c2c28081c4f5c3c076f6aded2080771176ba3aa75fccc` |
| Bound package assets | 14 |
| Runtime admission | false |

The generated package is local evidence under
`assets/reference/characters/robin_speech/compiled/speech/runtime-candidate/`.
The deterministic builder is
`tools/build_hd_rgba_character_candidate.py`.

## Shared Architecture

The builder accepts only the audited `robin` and `speech` shared-canvas
libraries. It resolves action, expression, facing, locomotion, and flight poses
from the character-owned catalog rather than substituting Robin pose IDs.

`HDPoseFrameSource` remains a package-selected renderer adapter beneath
`ProceduralWizardFrameSource`. Speech therefore uses the existing:

- authoritative Python `WizardFrameHub`;
- ordered remote-command inbox;
- runtime clock and state reducer;
- package-owned animation graph;
- performance application and score admission path;
- REST and WebSocket surfaces;
- Prism media connector and governance boundaries.

The adapter loads package-bound `.wjpose` RGBA shards and projects their pixels
onto the existing canvas protocol. PNG and SVG files are not runtime render
assets.

## Centering Contract

Speech is authored on the right half of a shared 1920 x 1080 source canvas. The
adapter applies an exact `-480`-pixel horizontal presentation translation:

`1920 / 2 - (960 + 1920) / 2 = -480`

This places the authored right-half midpoint at screen `x=960`. It preserves:

- source bytes and SHA-256 identity;
- 1:1 pixels with no resampling;
- the full 1920 x 1080 canvas;
- per-pose vertical registration;
- silhouette proportions and internal motion.

Stage locomotion is applied after the baseline translation, so Speech remains
centered at rest and can move purposefully around the stage.

## Verification

The shared-canvas HD runtime suite passed 9 of 9 focused tests. It builds both
Robin and Speech from their tracked source indexes in a temporary directory,
then verifies:

- RGBA keyframe and delta protocol behavior;
- package binding and fail-closed registry state;
- exact `+480` Robin and `-480` Speech translations;
- an exact presented root at screen `x=960`;
- no resampling of the 1920 x 1080 source;
- path and pose commands through the shared frame hub;
- command admission for all 200 poses per character.

The complete 400-pose sweep produced zero command rejections and zero frame-hub
failures. Two complete Speech candidate rebuilds produced byte-identical
artifact hashes.

A fresh local server launched from the package on port 8671. Browser review
confirmed centered idle and walking frames, authored directional changes, and
zero browser decode, resynchronization, or render errors. The observed walking
window reached approximately 13-15 browser fps while moving dense HD frames.
That throughput is review evidence, not an acceptance result, and remains a
production-admission blocker.

## Truthful Capabilities

Implemented in this candidate:

- seven authored directional views with a declared northeast fallback;
- source-backed whole-pose actions and expressions;
- four-frame ground locomotion;
- authored flight, bank, hover, and landing sequences;
- direct selection of all 200 review poses;
- centered HD presentation and normalized stage movement.

Not implemented or admitted:

- authored blink overlays;
- governed viseme or mouth-shape speech performance;
- motion and semantic contact-anchor acceptance;
- sustained HD motion throughput acceptance;
- independent animation and technical acceptance;
- rights, governance, and product approval;
- production registry entry.

Unsupported capabilities remain denied or use an explicit package-declared
fallback. Presentation cannot grant runtime authority.

## Reproduction

Build the local candidate:

```bash
python3 tools/build_hd_rgba_character_candidate.py \
  assets/reference/characters/robin_speech/compiled/speech/library-index.json \
  assets/reference/characters/robin_speech/compiled/speech/runtime-candidate
```

Run the focused verification:

```bash
python3 -m unittest tests.wizard.test_hd_rgba_runtime -v
```

Launch the local review runtime:

```bash
python3 tools/run_wizard_avatar_server.py \
  --host 127.0.0.1 \
  --port 8671 \
  --character-package \
  assets/reference/characters/robin_speech/compiled/speech/runtime-candidate/speech-character-package-v2.json
```

The persistent 8665 observer is the product-review surface. It projects Speech
beside the accepted HD Wizard Joe baseline without adding Speech to the
production registry.
