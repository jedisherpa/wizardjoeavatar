# Wizard Joe Phazer Sprite Repertoire

## Status

Approved and integrated into the Rust PixelGraph runtime.

## Source

- Archive: `WizardJoePhazerSprites.zip`
- Archive SHA-256: `636b9ddf8a5edff9db9de8f2eaa9ecf930b73bfe2b1d428b5111195ff4aec450`
- Source sheets: 8
- Authored frames per sheet: 6
- Added poses: 48 (`WJPS-0001` through `WJPS-0048`)
- Runtime catalog: v7, 308 total poses

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
2. Normalized by transparent padding onto the existing 1254 by 1254 frame.
3. Stored as native colored PixelGraph runs.
4. Serialized, reopened, projected, and compared byte-for-byte with its admitted transparent source.
5. Compared against retained source pixels at 1,000,000 millionths.
6. Visually reviewed in projected and transparent-overlay contact sheets.

Evidence lives in:

- `evidence/phazer-sprite-admission/projected-contact-sheet.png`
- `evidence/phazer-sprite-admission/transparent-overlay-contact-sheet.png`
- `evidence/phazer-sprite-admission/visual-review.json`
- `evidence/phazer-sprite-admission/WJPS-####/`

The approved 260-pose v6 catalog remains intact. Runtime v7 is an additive promotion containing
the original 260 graphs plus the 48 new Phazer graphs.
