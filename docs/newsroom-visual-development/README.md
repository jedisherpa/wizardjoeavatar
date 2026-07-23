# Wizard Joe Newsroom Visual Development

> Superseded visual direction: this v1 package is retained as historical evidence.
> New newsroom work uses the dimensional voxel sources and admission rules in
> `docs/newsroom-visual-development-v2/`.

This package is a modular visual reference set for building Wizard Joe newsroom scenes. It follows the immutable Rust news-anchor packet's 320x180 studio canvas, named shot profiles, foreground-occlusion rules, and bright colored-cell character language.

## Non-runtime boundary

Every PNG in `evidence/newsroom-visual-development/` is evidence and art-direction reference only. No PNG, SVG, generated character, or generated background is approved as a runtime render asset. Integration must first isolate each module, remove the white sheet/background, quantize it to the approved palette, convert occupied cells into transparent colored row runs, and pass visual and structural review.

Camera-board character appearances are composition placeholders only. The approved Rust pose graphs remain authoritative for Wizard Joe.

## Deliverables

### Character-free set plates

- `set-main-anchor-desk.png`: anchor-wide and desk-medium base.
- `set-standing-explainer-wall.png`: explainer-wide base.
- `set-cohost-interview.png`: discussion two-shot and interview base.
- `set-magical-breaking-field.png`: field, breaking-news, and magical correspondent base.

### Object sheets

- `props-studio-furniture-displays.png`: desk, chair, display, lectern, and practical-light studies.
- `props-broadcast-magic-overlays.png`: source-card, lower-third, two-box, portal, device, sparkle, and beacon studies.

### Camera boards

- `camera-board-a-core-coverage.png`: establishing wide, anchor medium, close-up, over-shoulder graphic, and two-shot.
- `camera-board-b-dynamic-inserts.png`: profile, high angle, low angle, dolly start/end, and cutaway inserts.

Full references are 1672x941. Matching `previews/` files are forced 320x180 audit reductions and are not tracing sources.

## Handoff order

1. Review `STYLE_BIBLE.md` and `CAMERA_COVERAGE.md`.
2. Use `scene-manifest.json` for categories, extraction targets, camera profiles, and occlusion intent.
3. Follow `CELL_GRAPH_CONVERSION.md`; never load these PNGs at runtime.
4. Resolve every item in `GENERATION_LOG.md` before art approval.
5. Audit at native reference size and at 320x180 before connecting a scene to animation.

## Files created

- `docs/newsroom-visual-development/README.md`
- `docs/newsroom-visual-development/STYLE_BIBLE.md`
- `docs/newsroom-visual-development/CAMERA_COVERAGE.md`
- `docs/newsroom-visual-development/CELL_GRAPH_CONVERSION.md`
- `docs/newsroom-visual-development/GENERATION_LOG.md`
- `evidence/newsroom-visual-development/scene-manifest.json`
- `evidence/newsroom-visual-development/CHECKSUMS.sha256`
- Eight full-size PNG references under `evidence/newsroom-visual-development/images/`
- Eight 320x180 review reductions under `evidence/newsroom-visual-development/previews/`
