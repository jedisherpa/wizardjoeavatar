# Implementation Plan

## Principles

- Keep the avatar procedural and editable.
- Store reusable visual definition data in `wizard_avatar/definitions/`.
- Render from semantic state, not from flattened sprites or prerecorded frames.
- Use a fixed white background and cached procedural floor.
- Stream direct ASCILINE-compatible cell frames, with visible renderers treating
  non-empty cells as colored square tiles.
- Keep NFT-project reuse straightforward: replace or extend definition JSON,
  palette values, view parameters, masks, and layer renderers without changing
  the server contract.

## Phases

1. Establish protocol and repository audit documents.
2. Add core model, palette, glyph, geometry, projection, floor, shadow, and
   compositor modules.
3. Add view definitions and procedural wizard layer renderer.
4. Add expression, blink, mouth, gesture, locomotion, pathing, and controller
   modules.
5. Add direct frame source and adaptive codec.
6. Add semantic HTTP/WebSocket server and browser demo controls.
7. Add deterministic tests and evidence generation.

## Repeatable Asset Conversion Path

Future NFT characters should follow this path:

1. Create a versioned palette file.
2. Create or update `wizard.json`-style character proportions and anchors.
3. Author eight directional view definition files.
4. Define expression overlays and mouth shapes.
5. Reuse the shared controller, projection, floor, frame source, codec, server,
   browser controls, tests, and evidence tooling.

No future character should be converted into runtime video, flattened PNG
animation, or a frame dump.
