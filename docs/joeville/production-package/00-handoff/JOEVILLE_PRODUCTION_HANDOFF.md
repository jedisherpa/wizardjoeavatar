# Joeville Production Environment Package — Handoff

**Prepared:** 2026-07-13  
**Package status:** comprehensive design-development and production-planning package; **not yet integration-ready**

## 1. Executive summary

Joeville is designed as a coherent, recurring foothill town with mountains to the west, a west-to-east creek spine, compact pedestrian downtown, meadow/trail threshold, wellness/food quarter, ordinary eastern neighborhoods and Castle Grace on a consequential southwest ridge. The scenic language is a crafted square-cell/block-diorama world derived from the actual Wizard Joe references: clear silhouettes, matte color blocks, limited texture clusters, playable ground, restrained rainbow/magic accents, and scenery quieter than the cast.

The package contains current Boulder research with 32-source ledger, a stable production map, a full world/set bible, 20-set register, 429-shot manifest, 120-clip manifest, 120 blocking tests, matching image/video prompt libraries, runtime audit, target technical spec, clearance/continuity documents, three diagrams, eleven generated and inspected concepts (including five Castle Grace translations), and a dependency-ordered roadmap.

The cast intake has advanced to two verified characters: Wizard Joe in the primary checkout and runtime-ready CrystAIl on the dedicated `codex/crystail-character` branch. Eleven character sources still await intake. The runtime still cannot load scenic stills/video or composite Joeville layers, so the package remains a production-ready **blueprint**, not a finished environment library or working Joeville visualizer.

## 2. Confirmed inputs and assumptions

Confirmed: Wizard Joe 89-pose primary package; CrystAIl 63-pose branch package and two-character registry; 240×135/24-fps medium stage; fixed affine X/Z projection; opaque glyph+RGB frames; current white/floor environment; Boulder primary-source research. Assumed pending approval: the other eleven cast members, crafted block-diorama scenic style for the whole cast, Castle design, physical scale, and environment runtime architecture.

See `../technical/VISUALIZER_AUDIT.md`, `../technical/CHARACTER_SCALE_EVIDENCE.md`, `../technical/CRYSTAIL_READINESS_ADDENDUM.md`, and `../design/OPEN_QUESTIONS_AND_ASSUMPTIONS.md`.

## 3. Research-team roster

- Lead coordinator/worldbuilding director: synthesis, dramatic function, handoff.
- Boulder Research Director + location/clearance: geography, culture, architecture, climate, current operations, source ledger.
- Production designer/art director/continuity supervisor: visual thesis, districts, set families, map and camera rules.
- Environment Technical Director + DP/previs auditor: live repo/runtime, scale, projection, layers, transport, integration gates.
- Root production team: manifests, prompts, diagrams, concepts, technical target, roadmap and validation.

Independent reports were completed before this synthesis.

## 4. Boulder research findings

The western mountain wall, creek cross-axis, remote canyon falls, four-block pedestrian center, distinct riparian/urban/meadow/ponderosa vegetation, historic-plus-contemporary architecture and variable snow/wet spring are the key production facts. Joeville translates these rather than copying landmarks. See `../research/BOULDER_RESEARCH_DOSSIER.md` and `../research/SOURCE_LEDGER.csv` for citations and reference status.

## 5. Joeville creative thesis

Joeville is a warm, legible town where civic and interior life touch nature: brick and sandstone gathering streets at the foot of bold western fins, creek bridges linking ordinary errands to reflective walks, and a growing communal Castle that observes rather than dominates. Magic is an occasional prism response; physical doors, paths, chairs and rooms remain coherent and stageable. Full thesis: `../design/WORLD_AND_SET_DESIGN.md`.

## 6. Town map and district structure

Districts: Downtown/Lantern Walk; Creek Corridor; Wellness/Food; Grace Meadow; Mountain/Trails; Castle Ridge; Sunward Residential. The map, routes, elevations, building orientations, sightlines and travel times are locked for v0.1 in `../design/MAP_SPEC.md`. Illustrated production map: `../maps/JOEVILLE_PRODUCTION_MAP.svg`.

## 7. Principal set overview

Principal families: townwide; Lantern & Lark coffee; Grace Meadow/Assembly Hall; Joeville Falls; Thirteen Stones; Current Hall; trail system; Castle Grace; Lantern Walk; Brightroot Juice; Juniper Tonic House; Riverstone Sushi; Joeville Commons Market. Supporting sets: creek path, residential street, Civic Weave Plaza, Rainbow Footbridge, Westlight Overlook, Meadow Trailhead and East Gate.

## 8. Complete set bible

The narrative, architecture, materials, entrances/exits, camera, blocking, props, variants, layers and continuity requirements are in `../design/WORLD_AND_SET_DESIGN.md`. The compact 20-set production register is `../manifests/SET_REGISTER.csv`.

## 9. Scenic concept-art index

Six town/set studies are in `../concept-art/`; five additional Castle Grace translations and their sources are in `../castle-grace/`. Inspection and rejection notes are in `../concept-art/CONCEPT_ART_INDEX.md`, with Castle continuity locked in `../castle-grace/CASTLE_GRACE_CANON.md`. No image is represented as a final production plate.

## 10. Still-shot manifest

`../manifests/STILL_SHOT_MANIFEST.csv` contains 429 planned still records covering establishing, exterior, reverse, interior, dialogue, OTS, group, ensemble, movement, POV, signage and clean plates, with time variants where required.

## 11. Environment-clip manifest

`../manifests/ENVIRONMENT_CLIP_MANIFEST.csv` contains 120 planned micro, establishing, ambient, dialogue, long and travel clips with duration, looping, camera, motion, sound, source art and current compatibility status.

## 12. Character blocking plan

`../manifests/CHARACTER_BLOCKING_MATRIX.csv` tests 1/2/3/5/8/13 cast sizes against every set's planned capacity. `../diagrams/MAJOR_SET_BLOCKING_PLANS.svg` covers major gathering/interior patterns. Wizard Joe and CrystAIl now supply two measured scale authorities, but actual two-character evidence waits on merge/runtime-base selection; larger configurations remain provisional. `../diagrams/CHARACTER_SCALE_INTAKE.svg` and `../manifests/CAST_BUILD_INTAKE.csv` track the remaining eleven.

## 13. Image-generation prompt library

`../prompts/IMAGE_PROMPT_LIBRARY.md` contains 429 production prompts aligned one-to-one with the still manifest, including composition, safe area, style, continuity, layers, output, file name and negative constraints.

## 14. Video-generation prompt library

`../prompts/VIDEO_PROMPT_LIBRARY.md` contains 120 prompts aligned one-to-one with the clip manifest, including duration, FPS, loop rule, camera, motion, source art, output and temporal exclusions.

## 15. Technical visualizer specification

Actual current behavior: `../technical/VISUALIZER_AUDIT.md`. Measured scale: `../technical/CHARACTER_SCALE_EVIDENCE.md`. Target layer/file/camera/anchor/validation contract: `../technical/TECHNICAL_ENVIRONMENT_SPEC.md`. No visualizer code was modified.

## 16. Brand and clearance report

Default policy is full fictionalization: Lantern Walk rather than Pearl Street storefront copies and Joeville Commons Market rather than Whole Foods. See `../design/CLEARANCE_AND_BRAND_REPORT.md`. Research-image provenance and usage purpose are tracked in `../research/SOURCE_LEDGER.csv`.

## 17. Continuity review

The continuity rules, light/season/weather contract and rejection checks are in `../design/CONTINUITY_BIBLE.md`; detailed landmark/camera/geography tests are in `../design/MAP_SPEC.md`.

## 18. Production roadmap

`../design/PRODUCTION_ROADMAP.md` defines gates G0–G11. Do not mass-produce scenery until the 13-cast intake and runtime scene contract pass. Castle reference development may proceed against the supplied canonical packet; the recommended first vertical slice spans downtown exterior, coffee interior, creek transition and Castle gathering.

## 19. Unresolved questions

The authoritative list is `../design/OPEN_QUESTIONS_AND_ASSUMPTIONS.md`. Highest priority: provide paths/names for the eleven ready-to-build character sources; decide whether to merge/use the CrystAIl branch; approve the supplied Castle packet and town map; choose scene-compositor architecture; approve fictional brands; choose the first story vertical slice.

## 20. Direct completion statement

**Not every required deliverable is complete.** The research, planning, maps/specifications, set bible, manifests, prompt libraries, diagrams, technical target, clearance/continuity work, roadmap and eleven inspected concept images are complete as design-development deliverables. Wizard Joe and CrystAIl are verified scale inputs, with CrystAIl ready on her dedicated branch; Falcor is being built separately as a vehicle character and is not counted toward the original 13-cast proof. The complete 13-character lineup, final floor plans and perspective guides tied to all characters, remaining scenic concepts, layered clean plates, blocking composites, environment clips, runtime-integrated scene and real 13-cast validation remain incomplete. These gaps are explicit rather than presented as finished.
