# Character Director V3 Canonical Cast Animation Review

**Reviewer:** Independent animation and motion director
**Decision:** **FAIL V3**
**Candidate runtime commit:** `a72f7915479787ba8cd65da2f5075ec99400c16c`
**Candidate tree:** `aba163cc72456d91c784474a5d12a295f822ec09`
**Evidence bundle:** `evidence/character-director/v3-canonical-cast-a72f791-2026-07-19`
**Capture manifest SHA-256:** `438d0e3525a679a5da78324bfa0ade7dbeb182cbcb0c4afd408ca2b6fe994004`
**Review bundle manifest SHA-256:** `2ff8ebe60f4865d2c44e7ebb1f930d646e6637e7234950ef3f405531a719267e`
**Scope:** V3 canonical front cast only. The prior `092f78e` review is
historical and is not incorporated into this decision.

## Review Method And Playback Limitation

I independently recalculated the hashes of the capture manifest, review bundle
manifest, scenario, truth trace, contact report, machine report, normal-speed
video, quarter-speed video, browser-layout video and metrics, and contact
sheet. I also checked all 177 capture-manifest artifact records and all review
bundle records for path containment, byte count, and SHA-256. No retained file
or declared source hash mismatch was found.

I inspected the complete contact sheet; the exact retained PNG samples around
cast entry, effect, recovery, and settle; decoded frame sequences for all three
casts; corresponding quarter-speed frames; a browser-layout storyboard and
the browser entry/settle sequences; the 242 truth records; machine acceptance;
browser metrics; and the candidate pose graphs. Direct real-time video
playback was unavailable in this review environment. The motion judgment is
therefore based on decoded ordered frames rather than live playback.

The normal artifact contains 240 frames at 24 FPS over 10.000 seconds, the
quarter-speed artifact contains the same 240-frame sequence at 6 FPS over
40.000 seconds, and the browser artifact contains 240 frames at 24 FPS over
10.000 seconds. Normal-to-quarter decoded SSIM is `0.999916`. The defects below
are present in the exact retained PNGs, the normal frames, the quarter-speed
frames, and the browser frames; they are not encoding noise.

The documented strict replay command is not portable to the supplied review
location. Both `validate_manifest()` and the V3 analyzer stop with `runtime
repository root does not match the evidence checkout` because the capture is
bound to `/private/tmp/wizardjoe-v3-capture-7774534` while the reviewer is in
the provided candidate worktree. I therefore performed the independent hash,
record, trace, and visual verification described above. This tooling defect is
listed as a residual evidence risk and is not the reason for the animation
failure.

## Blocking Findings

### 1. The Entire Staff Pops Between Two Different Render Constructions

Every cast begins with the long, tan neutral staff. Between authored frames 2
and 3, the complete prop abruptly becomes a shorter, dark-outlined staff. The
tip moves only one local cell, but the shaft, hook, length, outline, palette,
and lower endpoint all change on one presented frame. At settle, authored
frames 27 to 28 perform the reverse swap back to the long tan staff.

This is a whole-prop replacement, not a controlled pixel step. A source-graph
comparison reports **361 changed cells** across local bounds `x=51..60`,
`y=11..94` for both `cast_front_02 -> cast_front_03` and
`cast_front_27 -> cast_front_28`. The swap takes 41.7 ms at normal speed and is
held for 166.7 ms per frame in the quarter-speed artifact. It is conspicuous
at both rates and reads as the staff changing identity and length in Joe's
hand.

The three entry swaps occur at transport/authored frames `15/3`, `100/3`, and
`184/3`. The three settle swaps occur at `37/28`, `125/28`, and `209/28`.
Tracking only `staff_tip_local` misses this defect because the tip remains
within the two-cell threshold while hundreds of other staff cells change.

### 2. The First Cast Skips Its Final Recovery

The first cast presents authored frame 24 at transport frame 36, with the
staff still dark and angled and effect intensity `0.8`. The next transport
frame is authored frame 28, already the long tan neutral staff with effect
intensity `0.0`. Authored recovery frames 25, 26, and 27 are absent from that
cast. The source-graph difference for `cast_front_24 -> cast_front_28` is 392
cells across `x=50..63`, `y=11..94`.

This produces an unmistakable one-frame recovery cut at presentation frames
35 to 36, approximately `1.458-1.500 s` in the normal video. The machine report
exposes the omission in `observed_by_cast.v3-cast-one` but accepts it because
the union across all three casts covers the authored range. Union coverage is
not sufficient for animation acceptance: each performed cast must complete
its own recovery and settle.

These two defects violate the V3 director requirements for a coherent arc,
authored recovery, neutral settle, and absence of frame popping. They block
acceptance even though the endpoint state and anchor measurements pass.

## Passing Observations

| Area | Director finding |
| --- | --- |
| Face and hat clearance | **Pass.** During the dark-staff action, the outward crook remains to the right of the face and hat brim. Effect pixels occupy the intended negative space and do not cover the eyes. |
| Staff arc inside the active construction | **Pass.** Between the hard construction swaps, the crook follows a restrained outward-and-back path without tip teleportation or reversal. |
| Planted grip and root | **Pass.** The hand anchor remains fixed at local `(56, 50)`. Visual review and machine evidence show `0.0` staff-hand, planted, stage-root, and world-root drift. |
| Effect attachment and readability | **Pass within the uninterrupted middle action.** The blue, gold, and white particles originate around the crook and follow the tip. The first cast's abrupt `0.8 -> 0.0` termination is part of the blocking recovery failure. |
| Silhouette and staging | **Pass.** Joe remains centered and grounded. The cast span remains `x=79..160`, `y=22..126` on the `240 x 135` stage, leaving 79-cell side margins, 22 cells above, and 8 below. No avatar crop is present. |
| Neutral hold after each cast | **Endpoint pass, transition fail.** Candidate `a72f791` corrects the historical stale cast-pose feedback: all following holds are authoritative `front_idle` and stable. The transition into that hold still contains the whole-staff pop, and the first cast also loses recovery frames. |
| Browser layout | **Pass.** The `1440 x 814` browser recording is clear and stable. The character remains above the bottom toolbar; no page errors, console errors, decode errors, dropped frames, resyncs, or skipped presentation slots are reported. |
| Acting coherence | **Fail.** The static body can support a restrained wrist-led spell, but the prop shortening, palette swap, and first-cast recovery cut break object permanence and destroy the intended prepare-stroke-hold-recover phrase. |
| Repetition | **Fail.** The same construction pop repeats in all three casts, and the first repetition has a materially different, truncated recovery. |

Applicable rubric judgment: **hand acting 2/4**, **framing 4/4**, and
**repetition 2/4**. V3 cannot pass while an exercised category is below 3 or
while a conspicuous prop pop remains.

## Machine Report Gap

The machine report correctly proves transport continuity, fixed anchors,
marker order, effect-tip association, endpoint neutrality, and containment.
It does not prove visual continuity of the complete staff raster:

- `continuous_repeatable_staff_arc` measures staff-tip travel, not the shaft,
  hook, palette, or full prop footprint;
- `complete_static_cast_graph_contract` proves frames 0 and 31 equal neutral,
  but does not constrain the 361-cell swap at frames 2 to 3 and 27 to 28;
- `authored_coverage_and_terminal_neutral` accepts union coverage across three
  casts, allowing the first cast to omit recovery frames 25 to 27;
- silhouette bounds stay constant because Joe's body and feet dominate the
  bounding box, so they do not reveal the staff shortening.

The machine PASS is internally consistent with its checks, but those checks do
not cover the blocking visible defects.

## Required Before Re-Review

1. Preserve one staff design across neutral and cast: same length, width,
   outline language, palette, hook construction, and lower endpoint. Motion
   may rotate the prop, but it must not replace the entire object on one frame.
2. Present a continuous recovery in every cast. Do not accept per-run union
   coverage as a substitute for per-cast authored coverage.
3. Add full staff-raster continuity checks between adjacent authored frames,
   including changed-cell count and changed-region extent, in addition to the
   existing tip-anchor threshold.
4. Fail the capture if an active effect falls from a recovery intensity such
   as `0.8` directly to inactive because late recovery frames were skipped.
5. Recapture normal, quarter-speed, contact-sheet, and browser evidence from
   the corrected immutable candidate.

## Residual Risks

1. The review-bundle validator's absolute checkout binding prevents the
   documented independent replay from this supplied worktree. The evidence
   records themselves hash correctly, but portable validation should be fixed.
2. The body and arm remain structurally still while the staff moves. That can
   serve a restrained canonical cast after the prop continuity is corrected,
   but it has limited anticipation and weight for a future hero-cast variant.
3. The pale effect is readable on the white evidence stage but may need a
   contrast treatment over bright or complex backgrounds in later staging
   acceptance.

## Artifact Binding

| Artifact | Verified SHA-256 |
| --- | --- |
| `manifest.json` | `438d0e3525a679a5da78324bfa0ade7dbeb182cbcb0c4afd408ca2b6fe994004` |
| `review-bundle-manifest.json` | `2ff8ebe60f4865d2c44e7ebb1f930d646e6637e7234950ef3f405531a719267e` |
| `scenario-program.json` | `fb4ca6d69ffbbd829ffaf98dd5bfc2234aca8b7f1df4617b050b871cb95f5108` |
| `animation_truth_trace.ndjson` | `1249c8ade3702954c3f4f0650c5625f5a890d4fda6aa644599f8df5fb2887ec8` |
| `contact_verification.json` | `f8461163cf18da05f7cc0d1399d92dc3fe8d3d2a5bd5949dba7e274a5239e96d` |
| `v3-machine-acceptance.json` | `ea9c11748fb90fef93cb35b2edd710a70758c56fcc943a7c55eba6ee01605a2b` |
| `visual-review-b66a400b5e64-capture.mp4` | `b7d28babdc9dd62dd8b427e6f8bb61d49c330f74a71ee81d767ede5a72d89d7a` |
| `v3-quarter-speed.mp4` | `b120b9de83e759123dc25a9e483a54ba35a08c29220d04a37e4ec36b408bbf11` |
| `v3-browser-layout.mp4` | `9656b2b8fcbe1d647b61d953818d4de856b38b909445745788642f9363b89843` |
| `v3-browser-layout-metrics.json` | `259d29cc118020db11349de086e29a0da57df356bc57b709064b988fe7a96b14` |
| `visual-review-b66a400b5e64-contact-sheet.png` | `bd72460495e01b98475faf3383db00f2dff93dfa4fbb06ba177e945e85ea6126` |

## V3 Acceptance

**FAIL.** Candidate `a72f7915479787ba8cd65da2f5075ec99400c16c`
establishes correct neutral authority, stable contact, face clearance, effect
attachment, framing, and browser presentation. It nevertheless cannot be
accepted as coherent animation because the whole staff changes construction
twice per cast and the first cast cuts over three recovery frames. These are
visible object-continuity and settle failures, not minor pixel stepping.
