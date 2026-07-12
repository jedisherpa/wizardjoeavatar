# WizardJoeAvatar Compliance Gap Audit

Audit date: 2026-07-12

This document corrects the implementation status. The current codebase is a
first procedural implementation pass, not a completed implementation of all
requirements in `docs/00-goal-and-visual-contract.md` through
`docs/37-completion-gate.md`.

## Status Summary

Implemented or partially implemented:

- Procedural full-color square-tile cell renderer over an ASCII-compatible frame protocol.
- Fixed white background and faint floor.
- Editable palette, glyph roles, JSON view definitions, and layer renderer.
- Eight directional view definitions with distinct render output.
- Basic expressions, blink, mouth shapes, actions, walking, pathing, circles,
  and figure-eight commands.
- Dedicated semantic API routes.
- Dedicated `/ws/avatar/wizard?codec=adaptive` direct frame source.
- Python adaptive codec with RAW, ZLIB, DELTA, and RLE_FULL support.
- Browser demo with Canvas rendering and keyboard controls.
- Focused unit tests and generated evidence snapshots.

Not fully implemented:

- Full 38-document completion gate.
- Exhaustive required named test matrix.
- Production ASCILINE repository integration that preserves an existing `/ws`
  video route. This repo is currently standalone.
- Browser automated demo through a real browser harness.
- Cross-language browser decoder test using a shipped JS decoder under Node.
- Robust reconnect, dropped-frame resync, and late-join recovery tests.
- Real TTS/viseme/phoneme/word/amplitude timing hooks.
- Golden-image visual diff thresholding and reviewed baselines.
- Long-running broadcast stability tests.
- Complete diagnostics around dropped frames and reconnect counts from real
  clients.
- Evidence folders for all categories in `docs/36-evidence-package.md`.

## Document-by-Document Status

| Doc | Status | Notes |
| --- | --- | --- |
| 00 Goal and Visual Contract | Partial | Procedural no-video renderer exists; visual fidelity still needs iteration. |
| 01 Multi-Agent Coordination | Partial | Sidecar audit agents were used; not a full seven-agent implementation workflow. |
| 02 Repository Discovery | Partial | Audit docs exist; no actual target ASCILINE repo was provided, so standalone protocol reference was used. |
| 03 Required Architecture | Partial | Semantic state to renderer to WebSocket exists; production ASCILINE browser integration is standalone. |
| 04 Module Structure | Partial | Python/web/test structure exists; some listed modules are collapsed or simplified. |
| 05 Output Grid | Implemented | Medium/high/low concepts exist; visible output is square-tile cell art over an ASCII-compatible frame stream. |
| 06 Fixed Environment | Implemented | White cached background and faint floor exist. |
| 07 Perspective Floor | Partial | Procedural floor exists, but not true projected quadrilateral world tiles. |
| 08 Canonical Local Grid | Implemented | 34x52 local grid with root anchor exists. |
| 09 Color Palette | Implemented | Palette values are versioned in code. |
| 10 Glyph Language | Partial | Semantic mask roles exist; glyph bytes remain protocol masks while browser/evidence output renders square tiles. |
| 11 Ordered Layers | Partial | Layer order exists and renderer is layered; layer data is not fully externalized. |
| 12 Front View Construction | Partial | Front view anatomy exists; visual polish still ongoing. |
| 13 Directional Views | Partial | Eight definitions exist; diagonals are parameterized, not fully hand-authored correction masks. |
| 14 Joint Skeleton | Partial | Anchors and procedural limbs exist; per-direction skeletons are simplified. |
| 15 Procedural Walking | Partial | Distance-driven phase exists; limb motion is basic. |
| 16 World-Space Movement | Partial | Movement commands exist; edge clipping and full bounds are not exhaustively proven. |
| 17 Eight-Direction Facing | Partial | Velocity heading and hysteresis exist; turning polish remains. |
| 18 Circular Walking | Partial | Circle path command exists; arc/duration coverage is basic. |
| 19 Path Following | Partial | Path controller exists; corner slowdown is simplified. |
| 20 Expressions | Partial | Ten expressions exist; overlays need richer authored review. |
| 21 Blinking | Partial | Deterministic blink exists; double blink not implemented. |
| 22 Speech Mouth Shapes | Partial | Mouth shapes/fallback cycle exist; no real provider timing integration. |
| 23 Animation Channels | Partial | Separate semantic channels exist; conflict priority system is basic. |
| 24 Design-Board Actions | Partial | All actions exist in basic form; gestures need more authored nuance. |
| 25 Contact Shadow | Implemented | Faint root-following shadow exists. |
| 26 ASCILINE Frame Source | Partial | Direct frame source exists; not integrated into an existing production ASCILINE repo. |
| 27 Semantic Control Routes | Implemented | Required core routes exist with validation. |
| 28 Browser Demo Controls | Partial | Keyboard controls exist; UI needs better discoverability and full route coverage. |
| 29 Diagnostics | Partial | Diagnostics panel exists; dropped/reconnect client metrics are incomplete. |
| 30 Visual Tests | Partial | Snapshot evidence exists; golden diff tests are not complete. |
| 31 Locomotion Tests | Partial | Focused locomotion tests exist; not the full WIZ-MOVE matrix. |
| 32 Environment Tests | Partial | Focused environment tests exist; not the full WIZ-ENV matrix. |
| 33 ASCILINE Tests | Partial | Python codec/frame-source tests exist; not the full WIZ-ASC matrix. |
| 34 Speech/Expression Tests | Partial | Expression tests exist; full WIZ-FACE matrix is incomplete. |
| 35 Automated Demo | Partial | Scripted procedural demo snapshots exist; not a real browser automation run. |
| 36 Evidence Package | Partial | Evidence folders and key artifacts exist; several categories remain incomplete. |
| 37 Completion Gate | Not complete | The completion gate is not satisfied yet. |

## Next Work Order

1. Improve visual fidelity until the avatar reads clearly at live browser scale.
2. Replace parameterized diagonals with reviewed correction masks.
3. Add full named test IDs and fail if any required ID is missing.
4. Add real browser automation and screenshot/canvas checks.
5. Add JS decoder parity tests and dropped-frame/reconnect scenarios.
6. Add speech timing adapters for viseme/phoneme/word/amplitude/fallback modes.
7. Fill out the evidence package and only then re-evaluate `docs/37`.
