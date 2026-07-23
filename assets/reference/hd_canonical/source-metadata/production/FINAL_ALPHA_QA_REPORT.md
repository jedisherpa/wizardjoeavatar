# Final Production Alpha QA Report

## Verdict

**PASS — production-ready transparent alpha image set.**

The Wizard Joe Base-250 set contains 250 approved transparent masters and no missing, duplicate, or failed asset IDs.

## Acceptance results

| Check | Result |
|---|---:|
| Expected assets | 250 |
| Present assets | 250 |
| Technical passes | 250 |
| Technical failures | 0 |
| Unique output hashes | 250 |
| Canvas | 1254×1254 |
| PNG format | RGBA |
| Color metadata | Explicit sRGB |
| Minimum normalized safe margin | 69 px (5.5%) |
| Transparent corner check | 250/250 pass |
| Transparent RGB sanitation | 250/250 pass |
| Strict PNG decode | 250/250 pass |
| Visual category review | 250/250 pass |

## Alpha construction

The 248 unchanged-content assets use border-connected near-white matte segmentation. This removes only background regions connected to the canvas boundary, protecting enclosed white character details such as eyes, teeth, staff wraps, and highlights. Edge colors were unmatted and sanitized to prevent light halos, and fully transparent pixels were zeroed.

All outputs were normalized onto the original 1254×1254 canvas with a 5.5% minimum safe margin. The source images remain unchanged and are hash-frozen in `SOURCE_SHA256SUMS_OPAQUE.txt`.

## Content repairs

Two source poses were repaired before alpha extraction:

- `124_staff_raise_vertical` — corrected from an underscaled figure to a production-scale, fully framed vertical-staff pose.
- `205_magic_cast_hold` — corrected to a sustained effect-free post-release hold that reads distinctly between `204_magic_cast_release` and `206_magic_cast_recoil`.

Their source and output hashes are recorded in the manifest and `CORRECTION_LEDGER.md`.

## Visual evidence

The all-asset overview and nine category sheets were reviewed for white matte remnants, clipped alpha, halo contamination, missing enclosed whites, silhouette damage, topology errors introduced during extraction, and sequence readability. No blocking issue remains.

## Scope

This verdict certifies the production alpha still-image set only. It does not certify animation clips, in-betweens, transition graphs, effect layers, speech synchronization, or the complete runtime actor package.
