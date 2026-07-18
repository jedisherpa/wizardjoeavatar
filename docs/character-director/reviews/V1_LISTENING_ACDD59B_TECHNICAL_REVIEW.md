# Character Director V1 Independent Review

**Reviewer:** Reviewer B, real-time character technical director and evidence auditor  
**Decision:** **REJECT V1**  
**Candidate runtime commit:** `acdd59bd3e26e9730735c8169116f23d6bc8bca9`  
**Manifest SHA-256:** `2371dc8a7ccbc300f20aa23d6955c07b0f66eefaf9e28f405684642562c48a4e`  
**Contract:** [VISUAL_PERFORMANCE_ACCEPTANCE_2026-07-17.md](../VISUAL_PERFORMANCE_ACCEPTANCE_2026-07-17.md)  
**Scope:** V1 only. No files were edited.

## Executive Finding

The package proves a contiguous 290-frame atomic trace and good correspondence among wire records, decoded hashes, samples, contact sheet, and normal H.264 video. It does **not** support V1 acceptance.

The decisive failures are:

1. The second trace-declared blink has no corresponding raster change.
2. The 90-degree turn reads as a two-frame pose substitution, including a one-frame locomotion pose, rather than authored head follow and settle.
3. The planted `left_foot` contact moves substantially while its contact generation remains unchanged; `contact_verification.json` passes vacuously with `stance_count: 0`.
4. The character reads as frozen playback rather than listening: only five source raster hashes occur across all 290 frames.
5. Required evidence binding and provenance contain unresolved conflicts.

## Scores

| Applicable category | Weight | Score | Finding |
|---|---:|---:|---|
| Gaze and head-eye coordination | 12 | **2/4** | Front gaze changes are prompt and contained, but the turn pops through one locomotion pose with no readable settle at normal speed. |
| Blink | 8 | **1/4** | First blink is valid and visible; second is trace-only and visually absent. |
| Stillness | 10 | **1/4** | Root is numerically fixed, but the body is raster-static for long holds and reads frozen, not attentively listening. |
| Framing | 10 | **3/4** | Decoded-canvas framing is balanced and uncropped; browser layout/UI overlap is not evidenced. |

**Applicable weighted result:** `18/40`, equivalent to **45/100**.  
This fails the `85/100` threshold and the requirement that every applicable category score at least `3`.

## Frame-Specific Findings

Times use normal-video PTS, `(frame_index - 474) / 24`.

- **Frame 534, 2.500 s:** left-target gaze appears on the first captured post-application frame, changing 15 cells. Response latency passes.
- **Frames 539-541, 2.708-2.792 s:** first blink is visibly closed. Frame 542 opens at 2.833 s, giving **125 ms** closure. Pass.
- **Frame 595, 5.042 s:** gaze returns to viewer immediately, again changing 15 cells. Pass.
- **Frame 656, 7.583 s:** automatic gaze authority is visibly released in the trace.
- **Frame 663, 7.875 s:** eyes lead left while facing remains south; this provides a one-frame eye lead.
- **Frame 664, 7.917 s:** body switches wholesale to `walk_front_left`, facing southwest. This is a locomotion silhouette inside a stationary head-turn performance.
- **Frame 665, 7.958 s:** body switches wholesale to `profile_left`, facing west; gaze resets to relative center.
- **Frame 666, 8.000 s:** phase becomes `steady` without another raster change. The semantic `settling` label at frame 665 does not correspond to a visible settle.
- **Frames 687-690, 8.875-9.000 s:** trace says `blink_closed: true` for four frames, nominally **166.667 ms**, but every frame retains profile raster SHA-256 `0593e304...`, with `changed_cells: 0`. Frame extraction likewise shows no eyelid change. V1 therefore contains only **one visually presented blink**.
- Trace blink starts are 6.167 s apart, nominally within interval bounds, but the second event is not rendered.

Front-view eye positions remain visibly inside their apertures. However, `v1-machine-acceptance.json` contains no explicit quantitative eye-aperture/bounds measurement.

## Contact and Root

Presented root and world root remain constant for all 290 frames:

- Presented root: `(120.0, 126.820588...)`
- World root: `(0.0, 5.0)`

The planted contact does not remain stable:

- Frames 474-663: left foot `(109.38, 125.6956)`
- Frame 664: `(120.0, 123.4456)`, a `+10.62` horizontal-cell jump
- Frames 665-763: `(113.3625, 125.6956)`, remaining `+3.9825` cells from the original contact

Throughout this change, `contact_generation` remains `1`, the planted anchor remains `left_foot`, and support remains `both_feet`. This exceeds the one-cell planted-drift limit for substantially more than two frames and is a **hard contact failure**.

`contact_verification.json` reports zero drift but also `stance_count: 0`; it therefore does not test the visible stance transition and cannot support its pass claim.

## Scenario and Media Audit

The nominal program is 12.000 s. The normal H.264 is 290 frames at 24 FPS, **12.083 s**. Manifest ranges contain `60/61/60/8/101` frames, while machine acknowledged windows contain `60/61/60/7/100`, totaling the expected 288 frames but not matching the individual nominal windows.

Frame 655 is labeled as release-gaze before command application; frame 763 arrives after the turn capture-completion timestamp. Both remain in the normal video. The video is therefore not an exact 288-frame representation of the five nominal windows.

The quarter-speed artifact is 1160 frames at 24 FPS, **48.333 s**, exactly four times the normal frame count. Four-phase comparisons against the normal capture yielded SSIM `0.999530-0.999533`, supporting video correspondence.

## Integrity and Limitations

- The supplied manifest hash is correct.
- Runtime commit and clean start/end worktree binding match the candidate.
- All 59 manifest-listed artifacts match their declared hashes.
- All 290 wire records are contiguous; wire offsets, byte extent, hashes, codec tags, sizes, and trace indices reconcile.
- All 52 contact-sheet sample frame hashes reconcile with the atomic trace.
- Selected normal-video frames correspond closely to source sample PNGs: SSIM `0.999779-0.999947`.
- `v1-quarter-speed.mp4` and `v1-machine-acceptance.json` are **not listed in the manifest**, so the supplied manifest hash does not bind them. Reviewed hashes are respectively `57933a95...` and `913c7aad...`.
- Runtime binding reports epoch `wizard-runtime-ae7b...`; all acknowledgments and diagnostics report `wizard-48715b...`. The package does not explain this mismatch.
- Manifest subscriber count is `1`; every command snapshot reports `2`. The package does not reconcile the conflict.
- No real-browser recording is manifest-listed, so browser scaling, layout, and UI overlap are not proven.
- The contact sheet samples roughly every six frames and cannot establish blink or turn mechanics without the trace and extracted frames.
- This review makes no claim about scenarios V2-V10 or quality outside this immutable package.

## V1 Decision

**REJECT.** Machine and visual evidence do not jointly support two presented blinks, readable head follow/settle, contact stability, or listening presence. The planted-contact discontinuity is a hard failure, and the unresolved epoch/subscriber conflicts plus unbound derivative artifacts prevent fail-closed evidence acceptance.
