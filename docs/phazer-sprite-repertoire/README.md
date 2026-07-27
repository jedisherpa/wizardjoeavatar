# Wizard Joe Phazer Sprite Repertoire

## Status

Approved and integrated into the Rust PixelGraph runtime.

## Source

- Archive: `WizardJoePhazerSprites.zip`
- Archive SHA-256: `636b9ddf8a5edff9db9de8f2eaa9ecf930b73bfe2b1d428b5111195ff4aec450`
- Source sheets: 8
- Authored frames per sheet: 6
- Added poses: 48 (`WJPS-0001` through `WJPS-0048`)
- Runtime catalog: v9, 308 total poses

The files use `.png` names but contain lossy WebP data with a baked checkerboard. The Rust intake
compiler detects the actual format, verifies the archive and every member hash, removes only the
edge-connected neutral matte, and recovers six complete figure components from each sheet. This
component pass is necessary because adjacent figures overlap in horizontal extent.

## Runtime Clips

| Clip | Frames | Loop |
| --- | ---: | --- |
| `phazer_side_walk_takeoff` | 6 | No |
| `phazer_side_run` | 6 | Yes |
| `phazer_side_leap` | 6 | No |
| `phazer_side_wing_open` | 6 | No |
| `phazer_side_flap_cycle` | 6 | Yes |
| `phazer_side_flight_transition` | 6 | No |
| `phazer_front_walk_hover` | 6 | No |
| `phazer_rear_walk_hover` | 6 | No |
| `phazer_repertoire_loop` | 48 | Yes |

## Verification

Every pose is:

1. Isolated from its source sheet without a PNG or WebP runtime dependency.
2. Regenerated as a native-detail transparent source and verified against the authored mask.
3. Measured from Joe's central hat brim and normalized by camera facing around the runtime body
   anchor.
4. Padded onto the shared 1536 by 1536 runtime frame without clipping wings or staff.
5. Stored as native colored PixelGraph runs.
6. Serialized, reopened, projected, and compared byte-for-byte with its admitted transparent source.
7. Compared against retained source pixels at 1,000,000 millionths.
8. Visually reviewed in fixed-canvas source and live-runtime contact sheets.

Evidence lives in:

- `evidence/phazer-sprite-admission/projected-contact-sheet.png`
- `evidence/phazer-sprite-admission/transparent-overlay-contact-sheet.png`
- `evidence/phazer-sprite-admission/visual-review.json`
- `evidence/phazer-sprite-admission/WJPS-####/`
- `evidence/phazer-native-regeneration/normalized-v2/normalization-manifest.json`
- `evidence/phazer-native-regeneration/normalized-v2/review/fixed-canvas-before.png`
- `evidence/phazer-native-regeneration/normalized-v2/review/fixed-canvas-after.png`
- `evidence/phazer-native-regeneration/normalized-v2/review/live-runtime-contact-sheet.png`

The approved v7 catalog remains intact as the rollback baseline. Runtime v9 losslessly pads its
260 established graphs and installs the 48 normalized native-detail Phazer graphs.
