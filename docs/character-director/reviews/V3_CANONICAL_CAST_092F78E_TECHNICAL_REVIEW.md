# V3 Canonical Cast `092f78e` Technical/Evidence Review

**Overall verdict: FAIL**

**Machine-result status:** the retained machine report says PASS, and its
reported measurements are corroborated by the retained manifest and truth
trace.

**Visual-judgment status:** PASS with limitations. The retained frames show a
clean, readable cast, but direct real-time video playback was unavailable to
this reviewer. Visual judgment used the native contact sheet and independently
extracted normal-speed key frames. The two videos were also inspected through
media metadata and frame-sequence comparison.

**Reviewer role:** independent character technical director and evidence
verifier
**Candidate:** `092f78e7ca58dae1a457b2646d04aa8ef776f646`
**Candidate tree:** `b8d69992438d1db85e571e56d7876c1239f944a1`
**Evidence package:**
`evidence/character-director/v3-canonical-cast-092f78e-2026-07-19/`
**Capture manifest SHA-256:**
`ec3e0c490295b5d6dc5a68dc5327857ac484366ab2167b367d1f0f15819d97cb`

## Decision

The cast implementation itself is on a sound technical path. The retained
trace establishes 240 contiguous scenario-owned frames, stable roots and grip,
a repeatable staff arc, correctly ordered markers, marker-gated effects, and
safe stage bounds. The retained visual material shows that the revised crook
clears Joe's face and hat, the hand remains planted on the staff, the effect is
readable, and the action returns cleanly toward neutral.

The evidence package is nevertheless rejected as an independently verifiable
V3 acceptance bundle. `manifest.json` declares 179 artifacts, but the checked-in
directory omits all 172 declared sample PNGs and both declared wire artifacts.
The repository's own analyzer therefore fails before analysis with
`ManifestValidationError: artifact does not exist` on the first sample. This
prevents independent hash replay, wire decoding, sample reconstruction, and
semantic validation of the package as published.

There is a second coverage gap. The source clip contains 32 atomic poses,
`cast_front_00` through `cast_front_31`, but no captured cast observes frame 31.
The first cast also skips frame 1 and ends at frame 29. The current analyzer
accepts observed poses without requiring every authored pose in every cast, so
its PASS does not prove complete per-cast traversal.

## Hash Audit

The eight top-level hashes listed in the bundle README match the files that are
present:

| Artifact | Verified SHA-256 |
| --- | --- |
| `manifest.json` | `ec3e0c490295b5d6dc5a68dc5327857ac484366ab2167b367d1f0f15819d97cb` |
| `scenario-program.json` | `fb4ca6d69ffbbd829ffaf98dd5bfc2234aca8b7f1df4617b050b871cb95f5108` |
| `animation_truth_trace.ndjson` | `872a30797d4de2d1ff7dbdedad500735783f3928a6e9a3c9345b5342e5c5070c` |
| `contact_verification.json` | `3bd2f97ef4eec8cdc408d9c8090ee46186031a707e8c70b742977f17ed6475c7` |
| `v3-machine-acceptance.json` | `426fadc97d2b37e60e86e383a78158536f51ea43b0bf020b3c47fef77d97e8a9` |
| normal-speed MP4 | `bb4b01970898a315f1177f27789f3122afa5096212c71264758dcf6180efc7a0` |
| quarter-speed MP4 | `5f03ad2db38e7e6622f1aa0afbbe96c3bfba557b85cdb122513ccbb9d7f81dcc` |
| contact sheet | `aa564eed80b85c41c0e163e7d61fcb4bc3da849b4401d75c25eb126d5cca4593` |

All five present non-sample artifacts registered inside `manifest.json` match
their declared byte counts and hashes. However, **174 of the 179 registered
artifacts are absent**: 172 sample PNGs plus `wire/frames.bin` and
`wire/index.ndjson`. Hash declarations without the corresponding bytes are not
replayable evidence.

The machine report and quarter-speed derivative are listed and hashed by the
README but are not registered in the capture manifest. They are useful review
aids, not artifacts cryptographically bound by that manifest.

## Provenance And Runtime Binding

The retained identity records are structurally consistent:

- start, end, and capture provenance all name commit
  `092f78e7ca58dae1a457b2646d04aa8ef776f646` and tree
  `b8d69992438d1db85e571e56d7876c1239f944a1`;
- the Git object and tree exist in the repository and match the current
  candidate checkout;
- start, end, and provenance report a clean worktree, empty status, and empty
  tracked diff, each represented by the SHA-256 of empty content;
- the recorded launcher hash
  `825775e1a67255da232ecf2a7c1d699817447a1ff09ecde835b8dae845f09bfe`
  matches `tools/run_wizard_avatar_server.py` at the candidate;
- start and end retain the same PID, process epoch, branch, render geometry,
  Python executable, and isolated `127.0.0.1:8896` endpoint;
- the runtime is recorded as `240 x 135`, 24 FPS, four-byte cells.

This supports attribution to the requested clean commit. It does not cure the
bundle failure: full runtime-binding validation is part of `validate_manifest`,
which cannot reach completion while declared artifacts are missing.

## Capture And Truth Trace

The retained manifest and trace independently agree on the following machine
facts:

- exactly 240 frames, indexed uniquely and contiguously from 0 through 239;
- 240 owned frames and zero unowned frames;
- presentation indexes 0 through 239;
- scenario counts of `12 + 36 + 48 + 36 + 48 + 36 + 24 = 240` in the required
  ready, cast, hold, cast, hold, cast, settle order;
- zero dropped frames, decoded gaps, decoder errors, or queue overruns;
- queue high-water mark 1 of 16;
- 240/240 exact pairings between manifest and truth trace by frame index,
  decoded-frame SHA-256, and codec tag;
- one `animation_truth_trace_v1` record for every frame.

These are strong retained metadata checks. The omitted wire bytes mean an
independent reviewer cannot redo adaptive-codec decoding or verify the declared
wire offsets and wire hashes.

## Poses, Markers, And Continuity

The candidate source defines 32 complete atomic pose graphs with fixed root
`(36,95)` and fixed local staff-hand anchor `(56,50)`. The authored staff-tip
path has a maximum adjacent-axis change of two local cells, and pose 31 is
graph-identical to pose 0.

Observed capture coverage is narrower:

- cast one: 29 `cast_front` records, authored frames `0,2..29`;
- cast two: 31 records, authored frames `0..30`;
- cast three: 31 records, authored frames `0..30`;
- `cast_front_31` is never observed.

Every observed authored frame maps to the correspondingly numbered atomic pose.
Each cast emits exactly this marker sequence:

1. `action_commit` at authored frame 10;
2. `action_effect` at authored frame 14;
3. `action_recoverable` at authored frame 23;
4. `action_settled` at authored frame 28.

Across all 91 observed cast records, world root remains `(0.0,5.0)` and
presented root remains `(120.0,126.82058823529412)`. The fixed pose anchor and
fixed presented root produce zero derived staff-hand drift. The standalone and
embedded contact reports are identical and pass all 240 frames with zero
planted drift, raster-span drift, and root residual.

The observed staff-tip path is repeatable across casts and stays within the
two-local-cell-per-authored-frame criterion. This is a local authored-space
criterion; the nonuniform stage scale can make a two-cell horizontal step
larger than two presented stage cells.

## Effects And Stage Bounds

All three casts start the effect at the authored frame-14 marker with positive
intensity and `stroke` phase. The retained trace contains 42 active effect
records and none lacks a stage-space staff-tip anchor. Stroke, hold, recovery,
and inactive phases are represented.

All 91 observed cast silhouettes remain within the canonical `240 x 135`
stage. Their aggregate span is `x=79..160`, `y=22..126`, leaving substantial
side and top margins and eight cells below the lowest occupied row. No observed
cast silhouette is clipped.

The analyzer checks the character silhouette span, not a separately measured
effect-pixel span. Its effect gate proves a valid staff-tip anchor during active
phases, but not pixel-level coincidence between every effect pixel and that
anchor.

## Visual Judgment

Direct real-time playback was unavailable. I therefore used the retained
native contact sheet and independently extracted chronological key frames from
the normal-speed MP4. This limitation means the visual result is not a
substitute for a director watching both clips at speed.

Within that limitation, the visual action passes:

- the revised crook remains outside the face and hat silhouette;
- the grip is visually stable and the staff describes a coherent outward arc;
- the spark appears near the crook during the effect beat;
- the body, feet, wings, and stage placement do not pop or crop;
- the three casts are visually repeatable and return toward the same neutral
  silhouette.

The normal artifact is H.264/yuv420p, `960 x 540`, 240 frames at 24 FPS, and
10.000 seconds. The quarter-speed derivative is H.264/yuv420p, `960 x 540`,
240 frames at 6 FPS, and 39.875 seconds. After normalizing timestamps, decoded
frame-sequence comparison yields SSIM `0.999856`, supporting that the
quarter-speed file is a lightly re-encoded timing derivative of the same frame
order.

The acting remains restrained: nearly all visible performance is in the rigid
staff pivot and small effect, while the torso, arm silhouette, and wings stay
static. That is not a V3 continuity blocker, but it is a residual quality risk
for a high-end character-performance target.

## Analyzer Fail-Closed Audit

Positive fail-closed behavior:

- `load_and_analyze()` invokes the strict manifest validator before semantic
  analysis;
- the validator requires every registered artifact to exist and match its byte
  count and SHA-256;
- the checked-in package therefore fails immediately rather than silently
  accepting missing samples;
- focused analyzer tests pass and prove rejection of a large staff jump and a
  missing marker.

Coverage limitations:

- canonical-pose acceptance checks only observed records for matching IDs and
  a range of 0 through 31; it does not require all 32 poses or complete
  per-cast coverage;
- continuity divides movement by an authored-frame delta, so skipped authored
  frames can pass without proving the omitted intermediate presentations;
- effect acceptance checks event presence, phase, positive intensity, and a
  non-null tip, but not complete phase duration or effect-pixel placement;
- cast bounds use `silhouette_raster_span` for authored cast records only;
- grip location is reconstructed from the pose library loaded by the analyzer,
  rather than carried as an immutable hand anchor in each truth record;
- the analyzer does not bind or validate the separately supplied machine report
  or quarter-speed derivative.

## Residual Risks And Required Closure

1. Restore all 172 sample PNGs and both wire artifacts exactly matching the
   manifest, or publish a new complete evidence package whose manifest
   truthfully inventories every retained artifact. V3 wire replay cannot be
   waived while the contract requires semantic capture evidence.
2. Rerun `tools/analyze_character_director_v3.py` against the published bundle
   and retain a byte-identical machine report from that successful run.
3. Strengthen the analyzer to require the intended authored-frame set for each
   cast. Either capture `0..31` three times or explicitly revise the contract
   and analyzer to document why terminal pose 31 may be represented by the
   following identical neutral frame.
4. Bind the quarter-speed derivative and machine report to the accepted bundle,
   preferably through a review manifest or signed hash ledger.
5. Complete independent normal-speed and quarter-speed direct-playback review;
   the frame-based visual PASS here is explicitly limited.
6. Consider adding immutable `staff_hand_stage` and effect raster bounds to the
   truth schema so grip and effect placement do not depend on mutable local
   definitions during later audits.

## Final Verdict

**FAIL.** The retained machine data strongly supports the revised cast's
continuity, marker causality, contact, effects, and framing, and the available
visual frames are acceptable. The published evidence package is not complete
or independently replayable, and its analyzer does not prove complete
per-cast traversal of all 32 canonical pose graphs. V3 should not be marked
accepted until those evidence and coverage defects are closed.
