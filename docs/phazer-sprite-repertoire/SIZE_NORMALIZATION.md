# Phazer Size Normalization

## Result

Wizard Joe no longer changes camera scale when the Phazer repertoire crosses source-sheet or
clip boundaries. Intentional pose changes such as crouching, leaping, banking, and wing extension
remain unchanged. The complete Phazer group receives an additional 8% catalog-scale lift so its
camera size matches the established pose library.

## Method

The Rust normalizer:

1. Loads each approved native-detail `WJPS-####` source.
2. Locates Joe's central gold hat brim using the blue crown above it as the disambiguating feature.
3. Computes a median brim width for each camera facing, then applies the shared 1.08 catalog
   factor: east 294 pixels, south 274 pixels, and north 259 pixels.
4. Scales the complete silhouette around its existing ground-contact or airborne body anchor.
5. Adds 141 transparent pixels on every edge, producing a common 1536 by 1536 frame.
6. Recompiles and reprojects every normalized PixelGraph byte-for-byte.
7. Migrates the existing 260 runtime graphs by coordinate translation only.

The largest required scale correction was 42.029%, no frame-fit translation was required, and
all 48 normalized brim measurements landed exactly on their facing target.

## Runtime

- Compiler: `wizard-avatar-production-alpha-plus-normalized-phazer-v4`
- Runtime: `rust/wizard_avatar_engine/assets/pose_graphs/v9`
- Existing graphs padded losslessly: 260
- Normalized Phazer graphs: 48
- Total graphs: 308
- Runtime frame: 1536 by 1536

The browser projector compensates for the larger transparent frame, preserving the established
260-pose on-screen scale.

## Evidence

- Normalization manifest:
  `evidence/phazer-native-regeneration/normalized-v2/normalization-manifest.json`
- Fixed-canvas before:
  `evidence/phazer-native-regeneration/normalized-v2/review/fixed-canvas-before.png`
- Fixed-canvas after:
  `evidence/phazer-native-regeneration/normalized-v2/review/fixed-canvas-after.png`
- Live 48-frame runtime contact sheet:
  `evidence/phazer-native-regeneration/normalized-v2/review/live-runtime-contact-sheet.png`
- Live capture manifest:
  `evidence/phazer-native-regeneration/normalized-v2/live-loop/live-capture-manifest.json`

The live capture manifest contains all 48 pose IDs exactly once at a common 640 by 888 browser
viewport. Its contact-sheet SHA-256 is
`ac43c646a6ea47e97c0e6dd895fb41314cf46691f552cf88d6dfb9737293ff7f`.
The normalization receipt is marked `approved_fixed_canvas_and_live_frame_review` after reviewing
the fixed-canvas comparison and every live capture.
