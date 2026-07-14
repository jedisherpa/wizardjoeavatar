# Legacy Castle exterior study — visualizer scene branch

**Branch:** `codex/joeville-scene-castle-legacy-exterior`  
**Scene ID:** `JV-CAS-EXTERIOR-GOLD-LEGACY`  
**Set ID:** `JV-CAS`  
**Source status:** `REJECTED-REFERENCE-ONLY`

## Authority and source

The branch contains one scenic source at `assets/environments/joeville/jv-cas-exterior-gold-legacy/source-reference.png`.

- Source dimensions: 1254×1254
- SHA-256: `e63eaf5d729aec9382cc87854f41b93d4954261a61bb8962b5c80aafbbf638a1`
- Production role: Negative reference documenting the superseded church-like Castle direction
- Camera: Exterior garden master; do not implement as current Castle Grace

Do not treat a concept marked rejected or correction-required as a final background. Complete the listed art gate first and record the replacement source hash.

## Actual visualizer boundary

The current renderer builds an opaque 240×135 square-cell stage at 24 fps and calls `build_background()` directly. It has no production environment registry, layer schema, alpha/depth channel, scene clock, still/video background loader, or multi-character environment compositor. This branch is therefore an implementation contract, not a claim that the image is already integrated.

## Required conversion workflow

1. Preserve this source unchanged as provenance evidence.
2. Complete every correction below and obtain art-direction approval.
3. Produce a 3840×2160 sRGB master and a 240×135 direct-cell proxy. Recompose or outpaint; never stretch.
4. Paint no characters into the master. Create blocking overlays separately.
5. Split the approved master into the ordered passes below with aligned dimensions and transparent RGBA where applicable.
6. Add a scene registry entry keyed by `JV-CAS-EXTERIOR-GOLD-LEGACY` and a deterministic loader with checksum validation.
7. Define ground polygons, entry/exit anchors, occlusion masks and interactive props in scene-space coordinates normalized to 0–1.
8. Make scene selection explicit through a character-independent API/query parameter; do not hardcode this set in `frame_source.py`.
9. Composite: far/background → middle ground → character plane/shadow → foreground/occlusion → effects/lighting.
10. Add golden-frame, resize, checksum, missing-layer fallback and performance tests.

## Ordered layer contract

1. `reference_only`

## Blocking and movement

No runtime character anchors until redesigned against the canonical Castle Grace packet.

Record every anchor as `{id, x, y, depth, facing, capacity}`. Validate at 1, 2, 3 and 5 characters; validate 13 only where the set contract requires it. No final scale approval is allowed until the complete cast lineup exists.

## Required art corrections

- Replace church/institution silhouette
- Use canonical sandstone terraces, gables, iron rails and monumental pine
- Rebuild approach and terrace continuity from Castle Grace references

## Required variants

- `none_until_redesign`

Every variant must preserve geometry, entrances, window views, prop positions and ground anchors. Lighting/weather passes may change; architecture may not.

## Recommended implementation files

- `wizard_avatar/environments/registry.py`
- `wizard_avatar/environments/models.py`
- `wizard_avatar/environments/loader.py`
- `wizard_avatar/definitions/environments/jv-cas-exterior-gold-legacy.json`
- `assets/environments/joeville/jv-cas-exterior-gold-legacy/master/`
- `assets/environments/joeville/jv-cas-exterior-gold-legacy/layers/`
- `tests/wizard/test_environment_castle_legacy_exterior.py`

Build shared environment infrastructure in a prerequisite foundation branch and rebase this branch onto it. Do not duplicate a one-off loader in every scene branch.

## Acceptance gate

- Source hash and replacement-art hash recorded.
- No baked characters, generated text or unapproved brand marks.
- 16:9 master visually inspected at full resolution.
- Layer stack reproduces the approved flat master within the agreed pixel tolerance.
- Ground anchors and occlusion behavior verified with real runtime characters.
- Scene remains deterministic at 240×135 and scales correctly on resize/high DPI.
- Missing optional effects degrade safely; missing required layers fail clearly.
- Day/weather variants retain identical geometry.
- Evidence images and exact test commands committed before merge.
