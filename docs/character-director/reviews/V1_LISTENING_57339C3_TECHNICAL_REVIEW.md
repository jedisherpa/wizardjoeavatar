# Character Director V1 Independent Technical Review

**Reviewer:** Independent animation technical director and pixel-raster QA reviewer  
**Decision:** **ACCEPT V1 technical evidence**  
**Candidate runtime commit:** `57339c3c4286e198b13a1802efbc2741e9269aeb`  
**Capture manifest SHA-256:** `7547ab24df348744a2808ec0d751586f7b8d6fc6308922766c3a69621dbb8c0f`  
**Review bundle SHA-256:** `d63bdb85fb43a6dca5bf909c7c12561156057da7949f156295f941301ee6dc69`  
**Scope:** V1 listening technical/raster integrity only.

## Decision

**Technical evidence is fit to advance, but overall V1 remains rejected by the
independent animation review.** No blocking raster, compositing, ownership,
contact, blink, or capture-timing defects were found.

## Timestamped Findings

| Normal / quarter speed | Severity | Finding |
|---|---:|---|
| 0.375-0.792 / 1.500-3.167 s | Minor | One-pixel stepped idle head bob. Eyes remain intact. Slightly mechanical at quarter speed, acceptable at normal speed. It repeats cleanly at 3.375-3.792 and 6.375-6.792 seconds. |
| 2.500 / 10.000 s | Pass | Viewer-to-left gaze transfers on the first owned frame with no eye flash, duplicate paint, or body disturbance. |
| 2.833-2.958 / 11.333-11.833 s | Pass | Three-frame blink closes and reopens symmetrically; aperture and pupils restore completely. |
| 5.000 / 20.000 s | Pass | Left-to-viewer return is clean and contains no stale gaze pixels. |
| 7.500 / 30.000 s | Pass | Automatic-gaze release has no unintended visible pop. |
| 7.750-8.125 / 31.000-32.500 s | Pass | Eye lead, blink-masked head swap, profile reopening, and two-step settle contain no old-head remnants, white flash, collar seam, or duplicated pixels. |
| 9.083-9.250 / 36.333-37.000 s | Pass | Four-frame profile blink restores the identical open-eye raster. |
| 8.125-12.000 / 32.500-48.000 s | Pass | Feet, robe, wings, hand, staff, shadow, and contact points remain stable. |

All 288 normal frames have coherent ownership. Quarter speed preserves the
same ordering, holding each normal frame for four frames without dropped,
reordered, or interpolated transition imagery.

## Machine Corroboration

- 288 contiguous owned frames and 288 paired truth records.
- Zero dropped frames, queue overruns, or frame gaps.
- Three visible blink runs: 125, 125, and 166.667 milliseconds.
- Ten unique presentation-frame hashes.
- One declared stance with 0.0-cell continuous and raster planted drift.
- Stable `front_idle` body pose and `front_idle -> profile_left` head sequence.

Machine evidence corroborates this technical review but did not replace visual
inspection of the normal and quarter-speed videos.

