# Dragon Alpha Source Audit

Date: 2026-07-27

## Decision

The supplied DRG001 source declares 91 approved assets:

- 11 canonical poses (`CAN001`-`CAN011`);
- 80 action poses (`ACT001`-`ACT080`).

Only 84 assets are structurally valid and match their approved opaque-pixel
counts. Seven PNG streams are truncated. The Dragon set is therefore preserved
as an incomplete, review-disabled source set and is not compiled, registered,
or runtime-admitted.

Machine-readable authority:

`assets/reference/characters/dragon/source/source-manifest-v001.json`

Manifest SHA-256:

`024a5643d3e8442fdb3de0c2abf4198ff5c004e4ae35f6a5f42e75bc6d67d93f`

## Source Archives

| Role | File | SHA-256 | Declared |
| --- | --- | --- | ---: |
| Main | `DRG001_All_Approved_Alphas_CAN001-CAN011_ACT001-ACT065_2026-07-19.zip` | `35277f5dc01505343921bfcb6ac22b5c733e2e871ee4c3103fea3178eb941689` | 76 |
| Supplement | `DRG001_Approved_Alphas_ACT066-ACT080_2026-07-19.zip` | `1b0d5f59cea9940b30ca6aa4fb3f4f20b43d7870bab02ef2c08aab3121a86a3c` | 15 |

The separately supplied `(1)` supplement is byte-for-byte identical to the
supplement above. It adds no frames.

## Standalone Canonicals

The 11 separately supplied `CAN001`-`CAN011` files are byte-for-byte identical
to the 11 canonical payloads in the main archive. They confirm provenance and
filenames, but do not add or repair imagery. In particular, standalone
`CAN007` has the same SHA-256 as the truncated archive payload:

`9854168332a296a653cac25a6b5ccb3398a27e2d5b0c15c4bc82f5af72d6b950`

Ten standalone canonicals are valid. `CAN007` is not.

## Required Replacements

| Asset | Expected opaque pixels | Truncated decode pixels | Deficit |
| --- | ---: | ---: | ---: |
| `CAN007` | 298,752 | 275,329 | 23,423 |
| `ACT007` | 280,696 | 265,803 | 14,893 |
| `ACT011` | 308,914 | 239,683 | 69,231 |
| `ACT025` | 338,850 | 146,401 | 192,449 |
| `ACT032` | 279,680 | 240,592 | 39,088 |
| `ACT044` | 226,220 | 205,820 | 20,400 |
| `ACT060` | 343,791 | 215,869 | 127,922 |

The diagnostic pixel counts above come from permissive truncated decoding only
to quantify loss. Those decodes are not accepted or stored as source art.

## Validation Contract

`tools/import_dragon_alpha_source.py` enforces:

- exact archive SHA-256;
- a complete declared 11-canonical and 80-action inventory;
- 1920 x 1080 RGBA PNG;
- binary alpha values;
- zero RGB beneath fully transparent pixels;
- exact agreement with the embedded approved opaque-pixel count;
- supplement SHA-256 agreement where supplied;
- byte-for-byte standalone canonical comparison;
- no copying of failed payloads;
- `review_projection: false`;
- `runtime_admitted: false`.

The 84 valid PNGs are preserved byte-for-byte under:

`assets/reference/characters/dragon/source/alphas/`

The seven failed filenames exist only as blocked manifest records. A complete
Dragon source candidate requires undamaged replacements with the exact
filenames and approval metrics above, followed by a fresh deterministic ingest
and visual review.

## Historical Evidence

Twenty Dragon-looking frames previously found inside a mislabeled Robin archive
remain quarantined under:

`assets/reference/characters/dragon/source-evidence/contaminated-robin-archive-011-030/`

They are evidence, not substitutes. Their identity, geometry, and approved
pixel counts do not establish equivalence with the seven damaged DRG001 files.
