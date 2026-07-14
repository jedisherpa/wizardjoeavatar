# Castle Grace garden circulation — visualizer scene branch

**Branch:** `codex/joeville-scene-castle-garden-terraces`  
**Scene ID:** `JV-CAS-GARDEN-TERRACES`  
**Set ID:** `JV-CAS`  
**Source status:** `CANONICAL-CONCEPT-CLEAN-PLATE`

## Authority and source

The branch contains one scenic source at `assets/environments/joeville/jv-cas-garden-terraces/source-reference.png`.

- Source dimensions: 1536×1024
- SHA-256: `ee50aa8f5db98ce449b79dd81123fe2650e35fe6dbcb122ac5e664ad865ee8ba`
- Production role: Garden walking conversations, small patio meetings and connective Castle geography
- Camera: Upper-landing view down the curved garden path

Do not treat a concept marked rejected or correction-required as a final background. Complete the listed art gate first and record the replacement source hash.

## Actual visualizer boundary

The current renderer builds an opaque 240×135 square-cell stage at 24 fps and calls `build_background()` directly. It has no production environment registry, layer schema, alpha/depth channel, scene clock, still/video background loader, or multi-character environment compositor. This branch is therefore an implementation contract, not a claim that the image is already integrated.

## Required conversion workflow

1. Preserve this source unchanged as provenance evidence.
2. Complete every correction below and obtain art-direction approval.
3. Produce a 3840×2160 sRGB master and a 240×135 direct-cell proxy. Recompose or outpaint; never stretch.
4. Paint no characters into the master. Create blocking overlays separately.
5. Split the approved master into the ordered passes below with aligned dimensions and transparent RGBA where applicable.
6. Add a scene registry entry keyed by `JV-CAS-GARDEN-TERRACES` and a deterministic loader with checksum validation.
7. Define ground polygons, entry/exit anchors, occlusion masks and interactive props in scene-space coordinates normalized to 0–1.
8. Make scene selection explicit through a character-independent API/query parameter; do not hardcode this set in `frame_source.py`.
9. Composite: far/background → middle ground → character plane/shadow → foreground/occlusion → effects/lighting.
10. Add golden-frame, resize, checksum, missing-layer fallback and performance tests.

## Ordered layer contract

1. `sky_forest`
2. `castle_wall`
3. `garden_background`
4. `character_path`
5. `chairs_and_table`
6. `rail_occlusion`
7. `foreground_pillar`
8. `foliage`
9. `lighting`

## Blocking and movement

Curved pale path is the movement spline; four-chair patio is a seated group zone; rail gates define entrances; planted beds are non-walkable.

Record every anchor as `{id, x, y, depth, facing, capacity}`. Validate at 1, 2, 3 and 5 characters; validate 13 only where the set contract requires it. No final scale approval is allowed until the complete cast lineup exists.

## Required art corrections

- Create 16:9 master without changing path geometry
- Separate chairs for optional prop interaction
- Author matching reverse toward the Castle

## Required variants

- `spring`
- `summer`
- `autumn`
- `winter`
- `rain`
- `evening_practicals`

Every variant must preserve geometry, entrances, window views, prop positions and ground anchors. Lighting/weather passes may change; architecture may not.

## Recommended implementation files

- `wizard_avatar/environments/registry.py`
- `wizard_avatar/environments/models.py`
- `wizard_avatar/environments/loader.py`
- `wizard_avatar/definitions/environments/jv-cas-garden-terraces.json`
- `assets/environments/joeville/jv-cas-garden-terraces/master/`
- `assets/environments/joeville/jv-cas-garden-terraces/layers/`
- `tests/wizard/test_environment_castle_garden_terraces.py`

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
