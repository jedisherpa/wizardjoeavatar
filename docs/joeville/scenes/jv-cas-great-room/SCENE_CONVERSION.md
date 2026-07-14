# Castle Grace great room — visualizer scene branch

**Branch:** `codex/joeville-scene-castle-great-room`  
**Scene ID:** `JV-CAS-GREAT-ROOM`  
**Set ID:** `JV-CAS`  
**Source status:** `CANONICAL-INTERIOR-CONCEPT-RECOMPOSE-REQUIRED`

## Authority and source

The branch contains one scenic source at `assets/environments/joeville/jv-cas-great-room/source-reference.png`.

- Source dimensions: 1254×1254
- SHA-256: `ab194d81636e35096ca2d3337bf65e9625cacc0c1fead03c700b7cfff227a990`
- Production role: Intimate dialogue, firelight reflection and Castle group gathering
- Camera: Corner-wide interior master facing fireplace and terrace doors

Do not treat a concept marked rejected or correction-required as a final background. Complete the listed art gate first and record the replacement source hash.

## Actual visualizer boundary

The current renderer builds an opaque 240×135 square-cell stage at 24 fps and calls `build_background()` directly. It has no production environment registry, layer schema, alpha/depth channel, scene clock, still/video background loader, or multi-character environment compositor. This branch is therefore an implementation contract, not a claim that the image is already integrated.

## Required conversion workflow

1. Preserve this source unchanged as provenance evidence.
2. Complete every correction below and obtain art-direction approval.
3. Produce a 3840×2160 sRGB master and a 240×135 direct-cell proxy. Recompose or outpaint; never stretch.
4. Paint no characters into the master. Create blocking overlays separately.
5. Split the approved master into the ordered passes below with aligned dimensions and transparent RGBA where applicable.
6. Add a scene registry entry keyed by `JV-CAS-GREAT-ROOM` and a deterministic loader with checksum validation.
7. Define ground polygons, entry/exit anchors, occlusion masks and interactive props in scene-space coordinates normalized to 0–1.
8. Make scene selection explicit through a character-independent API/query parameter; do not hardcode this set in `frame_source.py`.
9. Composite: far/background → middle ground → character plane/shadow → foreground/occlusion → effects/lighting.
10. Add golden-frame, resize, checksum, missing-layer fallback and performance tests.

## Ordered layer contract

1. `window_and_door_exterior`
2. `stone_room`
3. `character_plane`
4. `seating_props`
5. `removable_coffee_table`
6. `foreground_ottoman`
7. `fire`
8. `firelight`
9. `practicals`

## Blocking and movement

Rug center is standing group zone; sofa, red chair and wing chair are seated anchors; French doors are exterior transition; coffee table is removable foreground prop.

Record every anchor as `{id, x, y, depth, facing, capacity}`. Validate at 1, 2, 3 and 5 characters; validate 13 only where the set contract requires it. No final scale approval is allowed until the complete cast lineup exists.

## Required art corrections

- Recompose square concept into 16:9 with approved side-wall extension
- Separate furniture and fire passes
- Validate full-cast layout against final 13-character lineup

## Required variants

- `day`
- `rainy_day`
- `sunset`
- `firelight_night`
- `celebration`
- `quiet_empty`

Every variant must preserve geometry, entrances, window views, prop positions and ground anchors. Lighting/weather passes may change; architecture may not.

## Recommended implementation files

- `wizard_avatar/environments/registry.py`
- `wizard_avatar/environments/models.py`
- `wizard_avatar/environments/loader.py`
- `wizard_avatar/definitions/environments/jv-cas-great-room.json`
- `assets/environments/joeville/jv-cas-great-room/master/`
- `assets/environments/joeville/jv-cas-great-room/layers/`
- `tests/wizard/test_environment_castle_great_room.py`

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
