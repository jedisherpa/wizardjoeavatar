# Joeville Technical Environment Specification

**Status:** target contract for engineering review; current runtime does not implement it  
**Evidence authority:** `VISUALIZER_AUDIT.md` and `CHARACTER_SCALE_EVIDENCE.md`

## Current compatibility baseline

| Item | Verified current value |
|---|---|
| Logical stage | 240×135 medium, 320×180 high, 180×101 low |
| Primary aspect | 16:9 |
| FPS | 24 medium, 30 high, 15 low |
| Horizon | normalized Y 0.56 |
| Near floor | normalized Y 0.95 |
| World | X -5…+5, Z 1.5…10; fixed affine projection |
| Cell payload | 4 opaque bytes: glyph, R, G, B |
| Current environment | cached white field + faint procedural floor |
| Scenic still/video/layers | not supported |
| Integrated cast | one Wizard Joe package |

## Authoring master

- Master still: 3840×2160, 16-bit or 8-bit PNG per pass, sRGB IEC61966-2.1 unless the pipeline approves ACEScg.
- Logical preview: 240×135 cell-aligned PNG plus JSON camera metadata; retain the high-resolution source.
- Safe crop: keep critical action inside normalized X 0.05–0.95 and Y 0.05–0.93; reserve the lower center for captions/UI validation.
- Fixed-camera sets: one camera ID per authored plate. Mirroring is prohibited.
- Video master: 3840×2160, 24 fps; ProRes 4444 for alpha passes, ProRes 422 HQ for opaque clean plates; H.264 proxy permitted only for review.
- Loop lengths: micro 2–4 s; establishing 5–10 s; ambient 8–20 s; dialogue 15–30 s; long 30–60 s.
- Color: no baked global grade. Deliver neutral master plus lighting overlay/LUT metadata.

## Required layer package

1. `far_bg` — sky, distant ridge, town mass.
2. `bg` — architecture/vegetation behind every character.
3. `ground` — walkable receiver plane and ground mask.
4. `rear_interactive` — furniture/props behind characters.
5. `character_plane` — empty metadata plane; characters are never baked here.
6. `front_interactive` — counters, table edges and door frames that may occlude.
7. `foreground` — removable near silhouettes.
8. `shadow_receiver` — grayscale receiver/strength map.
9. `depth` — 16-bit linear normalized depth.
10. `occlusion` — binary or graded per-camera matte.
11. `reflection` — optional separate pass.
12. `weather_fx` — rain, snow, mist, leaves; alpha.
13. `lighting` — practicals and motivated light overlays.

Flat-background fallback may use only `bg+ground`, but must preserve unoccluded movement zones and cannot claim counter/door/foreground interaction.

## Camera metadata

Every camera JSON requires: `set_id`, `camera_id`, map coordinate/elevation, look bearing, shot class, aspect, logical grid, horizon, vanishing point, ground polygon, safe polygon, anchors, paths, entry/exit edges, visible/occluded landmarks, season/time/weather, map version, and `mirror_prohibited:true`.

## Character and set coordinates

- Current runtime root is a stage-cell anchor projected from X/Z. Future scene packages must store anchors in stable set-local world units plus a camera projection matrix or approved fixed-camera mapping.
- Required anchor types: stand, seat, counter, door threshold, prop handoff, path waypoint, ensemble mark, camera focus, shadow receiver.
- Each anchor includes position, facing, capacity, clearance radius, allowed character IDs, and associated occlusion/depth region.
- Final dimensions remain blocked until all 13 characters provide root, eye, head, hip/seat, hand, prop, widest and tallest pose envelopes.

## Naming and organization

```text
JOEVILLE/
  sets/JV-{SET}/cameras/JV-{SET}-C###/
  maps/JV-MAP-{TYPE}-v###/
  graphics/signs|menus|posters/
  shared/vegetation|street_furniture|weather|materials/
  manifests/stills|clips|anchors|continuity/
```

Canonical asset stem:

```text
JV-{SET}-{KIND}-{ANGLE}-{TIME}-{SEASON}-{WEATHER}-V###
```

`KIND`: `STL`, `CLP`, `FG`, `OCC`, `DEP`, `LGT`, `SFX`, `SHD`, `REF`. IDs never depend on display names.

## Validation

- file hash and schema validation;
- dimensions, aspect, color profile, alpha and codec checks;
- empty-plate person/character inspection;
- map bearing, creek flow, window view, sun and Castle silhouette review;
- 1/2/3/5/8/13-cast overlay tests where capacity permits;
- foreground matte edge and depth-order tests;
- loop first/last-frame difference and temporal-warp inspection;
- 240×135 cell-proxy readability test;
- medium-profile 24-fps bandwidth, reconnect and keyframe reconstruction test in the actual runtime.

## Runtime engineering dependency

Integration requires a scene package loader, character registry/array, multi-entity depth sort, environment/prop layers, alpha or keyed-cell semantics, scene clock, camera contract, anchor/path model, and reconnect-safe serialization. This specification does not authorize or implement those code changes.

