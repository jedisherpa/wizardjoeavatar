# Joeville Character Build Contract

Use this contract for cast slots 03–13 so each character enters the same runtime and environment-scale pipeline as Wizard Joe and CrystAIl.

## Minimum intake per character

1. Stable `character_id` and display name.
2. Highest-authority original reference, preserved byte-for-byte with checksum.
3. Approved front, three-quarter, profile and back turnaround.
4. Neutral standing, widest action, tallest action, seated, crouched, dance and airborne references as applicable.
5. Explicit uncertainties: unseen rear construction, digits/toes, props, wings/tail/hair, materials and asymmetry.
6. Rights/provenance statement for every source image.

## Required runtime package

```text
assets/reference/{character_id}/original-reference.*
assets/reference/{character_id}/canonical-worksheets/*
wizard_avatar/definitions/{character_id}_character_package.json
wizard_avatar/definitions/{character_id}_pose_cells.json
wizard_avatar/definitions/{character_id}_animation_graph.json
wizard_avatar/definitions/{character_id}_character_manifest.json
wizard_avatar/definitions/{character_id}_animation_matrix.json
wizard_avatar/{character_module}.py
tests/wizard/test_{character_module}_character.py
```

Register the package in `character_registry.json`; do not add character-specific conditionals to every general route. Existing Wizard Joe and CrystAIl behavior must remain passing.

## Scale record

Each package must declare and validate:

- logical canvas and safe inset;
- root, eyes, mouth, hands, feet, hip/seat and prop anchors;
- wing/tail/hair/held-prop bounds;
- scale multiplier and any horizontal multiplier;
- occupied bounds for all poses;
- measured 240×135 footprints at Z 1.5, 3, 5, 7 and 10;
- pose-aware safe X bounds by depth;
- standing, seated and doorway-clearance overlays against the current cast.

## Capability families

Required unless anatomically/story-inapplicable: idle, blink, eight-direction facing, walk/run, stop/turn, speaking/visemes, expressions, explain/listen/react, entrance/exit, seated interaction, dance, weather/ground contact and deterministic recovery. Flight, wings, tail, magic, staff or other signature systems are character-specific capabilities rather than universal assumptions.

## Acceptance tests

- package schema and registry load;
- duplicate/missing/path-escape rejection;
- original checksum preservation;
- every graph pose exists;
- canonical safe inset and root consistency;
- motion changes live cells;
- speech changes mouth cells and closes on stop;
- expression/action changes live cells;
- character-scoped state/pose/command/WebSocket routes;
- browser selection through the real UI;
- deterministic frame hashes/replay;
- Wizard Joe and CrystAIl regression;
- scale capture and Joeville doorway/counter/ensemble overlay.

## Build order for slots 03–13

1. Populate `CAST_BUILD_INTAKE.csv` with source path and name.
2. Canon review and uncertainty lock.
3. Turnaround/pose worksheet approval.
4. Package/generator/registry implementation.
5. Focused tests, then full runtime regression.
6. Live browser selection and movement/speech capture.
7. Scale measurement and update to the Joeville lineup.
8. Only then mark `READY-PRIMARY` or `READY-ON-BRANCH`.

The eleven characters may be built in parallel in isolated branches, but registry/schema ownership must be coordinated to avoid conflicting edits.
