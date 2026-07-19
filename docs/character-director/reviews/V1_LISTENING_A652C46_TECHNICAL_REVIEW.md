# Character Director V1 Independent Technical Review

**Reviewer:** Independent character technical director and pixel-raster evidence auditor  
**Decision:** **REJECT V1**  
**Candidate commit:** `a652c4606f9a25a7010e7414de240a27f7350d14`  
**Candidate tree:** `260345ed30b868db4d17d51f014d60fa16f9b355`  
**Run:** `visual-review-7dedbddee9b5`  
**Capture manifest SHA-256:** `969fae9cf44f3ab33a82f125edd710d3cde169ca4db1418339ea292c499d412c`  
**Review bundle SHA-256:** `b2efa72e41aa4023ddc1d5e727cc54d3766d0ebb3a1b0ad9dfb780a13865d9ac`  
**Contract:** `VISUAL_PERFORMANCE_ACCEPTANCE_2026-07-17.md`, V1  
**Scope:** The sealed V1 listening package only; no judgment is made about V2-V10.

## Decision

**REJECT.** The candidate has a valid source/runtime seal, exact 288-frame
ownership, clean planted-body compositing, visible bounded eyes, three visible
blinks, and a readable authored three-quarter head bridge. It nevertheless
fails V1 acceptance for the following independent reasons:

1. **Hard framing failure:** hat and staff pixels occupy decoded raster row
   `y=0` throughout the performance. The contract requires at least four cells
   of top margin and lists clipping as a hard failure.
2. **Blink timing failure:** the visible blink onsets are separated by
   `5.125 s` and `1.125 s`. The second interval is below the required
   `2.5-6.5 s` bound. The green machine check measures closure duration but
   does not test this interval.
3. **Evidence insufficiency:** neither MP4 is a real-browser layout recording,
   and the contact-sheet labels omit tick, time, command, state hash, and frame
   hash. Both are required by the evidence truth chain.

The first item is a hard failure by itself. The package must not advance as an
accepted V1 candidate on the strength of `v1-machine-acceptance.json`.

## Seal And Ownership

- Capture began from clean branch `codex/character-director` at the candidate
  commit and tree above. Tracked diff SHA-256 is the empty digest. The end
  worktree differs only by the generated untracked evidence package.
- Runtime binding is verified at both ends: launcher
  `tools/run_wizard_avatar_server.py` hashes to
  `825775e1a67255da232ecf2a7c1d699817447a1ff09ecde835b8dae845f09bfe`,
  matching the manifest. PID, Python executable, dimensions, FPS, repository,
  branch, commit, tree, and process identity remain stable.
- `identity_process_epoch` (`wizard-runtime-4df60e...`) and
  `command_runtime_epoch` (`wizard-75c066...`) are separate named identities,
  not an unexplained substitution. All five acknowledgments and all seven
  snapshots use one stable command-runtime epoch; subscriber count remains
  exactly one.
- Source ID is `character-director-visual-review`, source epoch is
  `visual-review-7dedbddee9b5`, source sequences are strictly `1..5`, command
  IDs are unique, and every acknowledgment is `applied`.
- Frame and presentation indices are exactly contiguous `0..287`. All 288 are
  capture-owned; none is unowned. Scenario ownership is exactly
  `60/60/60/6/102` frames over ranges `0-59`, `60-119`, `120-179`, `180-185`,
  and `186-287`.
- `wire/index.ndjson` contains 288 contiguous byte ranges covering all 57,627
  bytes of `wire/frames.bin`: six keyframes (`0,48,96,144,192,240`) and 282
  deltas. Every wire SHA-256, codec tag, decoded SHA-256, trace frame index,
  and manifest frame record reconciles.
- There are zero dropped frames, decoded gaps, decoder errors, queue overruns,
  reconnects, resyncs, hub queue drops, slow subscribers, schedule overruns,
  or frame-hub failures. Queue high-water mark is `1/16`.

## Video And Hash Binding

Normal speed is H.264, `720x404`, 24 FPS, exactly 288 frames and 12.000 s.
Quarter speed is H.264, `720x404`, 24 FPS, exactly 1,152 frames and 48.000 s.
Frame-by-frame inspection of both videos found no reordering, interpolation,
black/white flash, or transition image absent from the normal capture. Each of
the four quarter-speed phases decimates to the 288-frame normal ordering; the
1,152 per-frame comparisons have SSIM `0.998986` or better. Small decoded
differences within held groups are expected from the second H.264 encode and
are not source-raster changes.

Recomputed output hashes match the sealed records:

| Artifact | SHA-256 |
| --- | --- |
| Normal MP4 | `8967735e8854a1f76ddb322c97f75db193b3c46ebcfce8bfa278dd6307907fe4` |
| Quarter-speed MP4 | `aea06c705e6a5302cfde9605b5590828ebad308d8b8f8db7a02a149efb4724c8` |
| Contact sheet | `2486eb10701b98d0ecc05178f0ed831df525df774e7b140643159eae78772317` |
| Machine acceptance | `29c40fedd0e219ec0e1831c43d5b9a2a6cd59310bedbc99c14f76cf36a7f8241` |
| Contact verification | `1d92f29a01577553743bc6eda37b50e3af9b957bac3deadfb2aaa9b03c6e569f` |
| Wire index | `5152eaa049710fbdb276ea0edfae72db1f301ba17841526faa09f8c65254d5a0` |
| Wire bytes | `19a0771f6c5566db3327f4ee7edfed47b6165984c3eca00859e7a028fc5015bb` |
| Animation truth trace | `b912a8b08d8587f2105b41918755449b6f8c946a5e40aa50212bba0117b66458` |

Both capture-manifest semantic validation and review-bundle validation pass.

## Frame-Exact Performance Findings

| Normal / quarter speed | Finding |
| --- | --- |
| `0.000-2.458 / 0.000-9.833 s` | Viewer fixation is stable. The authored one-cell head bob at frames `14-18` is confined to the head mask and introduces no eye, collar, or body tear. |
| `2.500 / 10.000 s` | Left gaze appears on frame `60`, the first owned target frame. Exactly 15 source cells change, all inside the eye/head region. |
| `2.833-2.958 / 11.333-11.833 s` | Frames `68-70`: visible three-frame blink, 125 ms. Pupils are absent while closed and restore exactly on frame `71`. |
| `5.000 / 20.000 s` | Viewer gaze returns on frame `120`, again with a 15-cell head-only change and no stale left-gaze pixels. |
| `7.500-7.708 / 30.000-30.833 s` | Frames `180-185`: automatic gaze release is visually stable. |
| `7.750-7.792 / 31.000-31.167 s` | Frames `186-187`: eyes lead left for two frames while the head and body remain front, satisfying the 1-4-frame lead requirement. |
| `7.833-8.000 / 31.333-32.000 s` | Frames `188-192`: authored `walk_front_left` **head-only** bridge is held for five frames over the unchanged `front_idle` body. It reads as a three-quarter head follow, not a locomotion pose. Frames `191-192` are blink-closed. |
| `8.042-8.333 / 32.167-33.333 s` | Frame `193` presents the closed-eye profile; frame `194` opens; frames `197-199` complete the one-cell settle; frame `200` is steady. No old front-head remnant, white hole/flash, duplicate eye pixel, beard break, neck gap, collar seam, or hat discontinuity is visible. |
| `9.083-9.250 / 36.333-37.000 s` | Frames `218-221`: visible four-frame profile blink, 166.667 ms, with exact open-raster restoration at frame `222`. Its onset is only 1.125 s after the turn blink onset and therefore fails interval acceptance. |
| `9.792-9.958 / 39.167-39.833 s` | Frames `235-238`: one-cell profile listening bob remains confined to the head mask and restores on frame `239`. |

The three closure runs are `68-70`, `191-193`, and `218-221`, with durations
`125`, `125`, and `166.667 ms`. Every open frame has visible blue eye cells;
every closed frame has none. Front and bridge poses have two apertures and four
open-eye cells; profile has one aperture and two open-eye cells. No eye cell
escapes its declared aperture in any of 288 frames.

## Body, Contact, And Composite Integrity

- Exact decoded RGB comparison finds **no changed cell outside head region
  `x=70..112, y=0..36` in any of 288 frames**. Staff, gripping hand, free hand,
  both wings, robe, feet, and shadow are source-pixel stable through gaze,
  blink, bridge, profile swap, and settle.
- `rendered_pose_id` remains `front_idle`; action and locomotion remain `idle`;
  mouth remains `closed`; speech authority remains `none`.
- Presented root remains `(90.0, 93.0)`, world root remains `(0.0, 5.0)`,
  support remains `both_feet`, planted anchor remains `left_foot`, planted
  raster span remains exactly `(80,92)-(80,92)`, and staff-tip span remains
  `(61,0)-(61,0)`.
- `contact_verification.json` covers all 288 frames with one stance and reports
  `0.0` continuous planted drift, raster-span drift, and root residual. Visual
  review agrees: there is no foot slide, robe pop, hand/grip slip, wing jump,
  or staff wobble.
- Head replacement is clean at source-cell scale. There are no duplicate
  pupils, eyelids, hat edges, beard blocks, old-head remnants, mask holes, or
  single-frame white flashes.

## Blocking Framing Finding

The framing machine report does not test the contract's required margins.
Independent source-raster inspection does:

- At frame `0`, decoded row `y=0` contains 27 non-white cells in runs
  `x=80..97` (hat) and `x=113..121` (staff).
- The same top-row contact persists in front, bob, three-quarter, profile, and
  settled states. The profile samples contain 29-30 non-white top-row cells.
- The trace independently places the staff-tip raster span at `y=0` on every
  frame.

There is therefore zero top margin and visible top-edge silhouette clipping,
not the required four cells. This is a hard failure under the acceptance
contract regardless of root/contact stability or the green machine result.

## Evidence Sufficiency

The atomic command/state/wire/decoded/trace chain is strong enough to support
the raster and timing findings above, but the package is **not sufficient for
acceptance**:

1. `visual-review-7dedbddee9b5-capture.mp4` is the exact-frame FFmpeg output
   derived from decoded cells. `v1-quarter-speed.mp4` is its derivative. No
   real-browser recording proves browser layout, scaling, presentation, or UI
   overlap as required by Evidence Truth Chain item 7.
2. The contact sheet samples only every 12 frames and visibly labels only run,
   sample, scenario, and frame. Its labels omit tick, time, command, state
   hash, and frame hash required by item 9. The manifest sample records add a
   frame hash but do not make the rendered labels compliant.
3. This is one independent review. The release contract still requires a
   second independent reviewer and aggregate review record even after the
   blocking defects are corrected.

## Residual Risks And Required Correction

- `stale_render_discard_count` rises from `0` to `1` at the first gaze command
  boundary and remains there. The owned published sequence is lossless, so it
  is not counted as a frame gap, but a future fail-closed package should explain
  or eliminate this counter transition.
- The turn-triggered blink and scheduled profile blink interact to create the
  1.125-second interval. Retiming or suppressing the scheduled blink must retain
  at least the two intended visible V1 blinks, 100-200 ms closures, and
  2.5-6.5-second onset spacing.
- Reframe the renderer so every state has at least four cells top/side and six
  cells bottom margin, with no hat or staff pixel on the boundary.
- Recapture both review speeds, add the required real-browser recording, and
  generate a contact sheet with complete per-sample attribution.

**Final determination: REJECT V1.**
