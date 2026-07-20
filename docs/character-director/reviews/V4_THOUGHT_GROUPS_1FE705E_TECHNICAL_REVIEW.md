# V4 Thought Groups Technical Review

**Scope:** V4 thought-group gesture evidence only  
**Runtime candidate:** `1fe705e3e60c3dac612c6d5c2aa7a98392cfaae9`  
**Analyzer correction:** `c009607fdc8b9a49d47d066e4690f07c529a8fc3`  
**Evidence publication:** `43dbaa306b3f18c159ec230571bc85624820cb1f`  
**Evidence run:** `visual-review-ed4d9343d974`  
**Evidence directory:** `evidence/character-director/v4-thought-groups-1fe705e-2026-07-19`

## Decision Summary

The retained V4 package is internally consistent and technically sufficient for
V4 acceptance. The runtime capture is bound to a clean checkout of the stated
candidate and tree, all 168 transport frames are contiguous across the capture
manifest, truth trace, and wire index, and the six unowned frames occur exactly
at the six scenario boundaries. The 162 scenario-owned frames have the required
counts and order. A replay of the corrected analyzer against the original
capture produced a byte-identical 6,948-byte machine report with all eight gates
passing.

The post-capture analyzer commit is not a runtime change. It corrects owned-frame
coverage around the bounded transition that carries authored frame zero, while
also making the point recovery check stricter. The correction is appropriate,
has a focused regression test, and leaves the runtime tree, frame data, graph,
poses, timing, and media unchanged.

## Commands And Checks Performed

I performed the following read-only checks from the canonical worktree and the
original capture/runtime locations:

```text
git show --format=fuller --no-patch <runtime|analyzer|evidence commit>
git merge-base --is-ancestor <runtime> <analyzer>
git merge-base --is-ancestor <analyzer> <evidence>
git diff 1fe705e c009607 -- tools/analyze_character_director_v4.py
git diff 1fe705e c009607 -- tests/wizard/test_character_director_v4_acceptance.py
git diff --exit-code 1fe705e c009607 -- assets wizard_avatar visualizer
git rev-parse <commit>^{tree}
git diff --quiet 43dbaa3 -- evidence/character-director/v4-thought-groups-1fe705e-2026-07-19
shasum -a 256 <retained evidence files>
cmp -s <published file> <original capture file>
ffprobe -count_frames <normal|quarter-speed|browser-layout video>
python3 -m unittest <V1-V4 acceptance, visual-review, pose-library, capability tests>
```

I also ran the repository's `validate_manifest` and
`validate_review_bundle_manifest` functions in the original runtime-bound
location, independently parsed all manifest/trace/wire records, recomputed all
declared artifact byte counts and SHA-256 hashes, and replayed the corrected V4
analyzer in memory without modifying the original capture.

## Git Provenance

The ancestry is linear and verified:

```text
1fe705e3e60c3dac612c6d5c2aa7a98392cfaae9  runtime
  -> c009607fdc8b9a49d47d066e4690f07c529a8fc3  analyzer and test only
  -> 43dbaa306b3f18c159ec230571bc85624820cb1f  evidence publication
```

- `git merge-base --is-ancestor` returned success for both links.
- The runtime commit tree is
  `dc2a8039abdece6d9e973213f2f126d03b73b9bd`, exactly matching
  `manifest.json.provenance.head_tree`.
- The original runtime checkout at
  `/tmp/wizardjoe-v4-localized-1fe705e` remains at the exact runtime commit
  and tree.
- The capture records branch `codex/v4-localized-1fe705e`, empty status and
  tracked-diff hashes, and `worktree_clean: true` at both runtime-binding
  endpoints.
- Between the runtime and analyzer commits, only
  `tools/analyze_character_director_v4.py` and
  `tests/wizard/test_character_director_v4_acceptance.py` change. No asset,
  graph, pose, renderer, visualizer, or runtime module changes.
- The evidence working tree matches evidence commit `43dbaa3`. Concurrent
  untracked work elsewhere in the repository is outside this review and was
  not touched.

This distinction is material: `1fe705e` is the code that rendered the captured
frames, while `c009607` is the code used to interpret their owned-frame
coverage. `43dbaa3` publishes the immutable products of that analysis.

## Review Bundle Integrity

`review-bundle-manifest.json` has exactly the strict version 2 fields and
declares the required unique roles:

- `quarter_speed`
- `machine_acceptance`
- `browser_layout`

The strict validator passed in the original capture location
`/tmp/v4-canonical-gestures-1fe705e-run1`. It verified field sets, path
containment, media types, byte counts, hashes, run and candidate binding,
capture-manifest binding, source binding, role completeness, browser metrics,
and runtime capture integrity.

Independent recalculation also found:

| File | SHA-256 |
| --- | --- |
| `review-bundle-manifest.json` | `c936ae5683f6ea0b5994176c2753789e3b45f7213ab773c07893c2f98f825479` |
| `manifest.json` | `19f33079b95b976854569a69edc2d6eeb2a0c2d1dc80fbf2267ea4f5fce3ce37` |
| `animation_truth_trace.ndjson` | `6a88d87513dcef002abd78727bef54f3ca4fe90c0ca79c91724ed198f3897d6e` |
| `contact_verification.json` | `598580024db54023a2b44c32a85347be3c4380fb935f88360e981ba1a16af` |
| `scenario-program.json` | `76966a3bf4b19c43800e49e697e921e35231aa3f2c4097bb6af9186e9277a5ce` |
| `v4-machine-acceptance.json` | `09ad102d692848b97fab02f64de7e72d9b56ff53963ae50c8a00bac021915546` |
| normal-speed MP4 | `39c55a0cc16a9e436f51d6681a711cb646017d951e1bd447c13555a3d275a4ea` |
| quarter-speed MP4 | `425c3cdc2a8d5452e1926d2d24337a1418b1bdd2cc05968254e9ea6fe471ea47` |
| browser-layout MP4 | `bdcf5770cfde78b383e2bf698d606a004f1b4fb48ca643b20e35bcb4d885846a` |
| browser-layout metrics | `8845cd6c2f0a5be4736a7d9e8de098884dda35cd5fdadd390e7d68331b8a3319` |

All 169 capture-manifest artifact records pass independent existence, byte-count,
and hash checks. All 175 original capture files are present in the published
evidence with identical relative paths and hashes; the only additional
published file is its README.

## Frame And Scenario Integrity

The manifest, truth trace, and wire index each contain 168 records with identical
strictly contiguous frame indexes `0..167`. The capture reports zero dropped
frames, no decoded gaps, no decoder errors, queue high-water mark 1 of 16, and
zero queue overruns.

There are exactly 162 owned frames and six unowned transition frames:

```text
12, 43, 62, 93, 112, 143
```

Each transition has `scenario: null` and sits singly between adjacent owned
scenario ranges. The exact owned order, ranges, and counts are:

| Scenario | Transport range | Owned frames |
| --- | ---: | ---: |
| `v4-ready` | 0-11 | 12 |
| `v4-thought-one-explain` | 13-42 | 30 |
| `v4-thought-one-hold` | 44-61 | 18 |
| `v4-thought-two-explain` | 63-92 | 30 |
| `v4-thought-two-hold` | 94-111 | 18 |
| `v4-thought-three-point` | 113-142 | 30 |
| `v4-settle` | 144-167 | 24 |

Boundary frames 12, 62, and 112 carry authored frame zero of the following
explain, explain, and point clips. Their first owned frames 13, 63, and 113
therefore begin at authored frame one. The other three boundary frames carry
neutral idle. This directly supports the analyzer correction.

The authored marker order is exact:

- Explain 1: commit 2, speech open/effect 6, speech close 13, recoverable 18,
  settled 19.
- Explain 2: the same authored sequence.
- Point: commit 2, effect 7, recoverable 18, settled 19.

The corresponding transport marker frames are `14/18/25/30/31`,
`64/68/75/80/81`, and `114/119/130/131`. Both hold scenarios and the final
settle remain `front_idle` on `idle_front`.

## Eight Machine Gates

The retained report and independent replay both pass all eight named gates:

1. `scenario_program_identity`: exact V4 program, seven scenarios, 6.75 s.
2. `scenario_order`: exact authored order listed above.
3. `complete_contiguous_capture`: 168 trace-paired contiguous frames, 162
   owned frames, exact counts, and six bounded transitions.
4. `three_motivated_strokes_in_authored_order`: two explain strokes and one
   point stroke with exact marker order.
5. `thought_group_holds_and_recovery`: owned authored coverage 1-19 for all
   gestures, complete recovery, and neutral holds.
6. `atomic_landmark_warp_graph_contract`: exact explain and point pose
   sequences, including the point 70 percent bridge, with no palette failures.
7. `planted_root_during_all_gestures`: contact pass with zero planted,
   stage-root, and world-root drift.
8. `gesture_silhouettes_within_canonical_stage`: zero clipped action frames
   on the `240 x 135` logical stage.

The report metrics are 168 total frames, 162 owned frames, 81 owned action trace
records, three strokes, zero stage-root drift, zero world-root drift, and zero
clipped frames. Independent trace inspection found one root tuple across all
gesture records. Action silhouette extrema are `x=76..160`, `y=22..126`,
leaving the character inside every stage edge.

The contact report covers all 168 frames and reports:

- `maximum_planted_drift_cells: 0.0`
- `maximum_planted_raster_span_drift_cells: 0.0`
- `maximum_root_residual_cells: 0.0`
- no issues

## Media Verification

Independent `ffprobe -count_frames` results exactly match the evidence claims:

| Artifact | Codec | Dimensions | Frames | Rate | Duration | Bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| normal speed | H.264 | 960x540 | 162 | 24 fps | 6.750 s | 47,065 |
| quarter speed | H.264 | 960x540 | 648 | 24 fps | 27.000 s | 89,746 |
| browser layout | H.264 | 1280x634 | 162 | 24 fps | 6.750 s | 83,911 |

The quarter-speed product is exactly four times the normal duration and frame
count at the same output rate. The browser product has the exact expected 162
frames.

## Browser Runtime And Layout

The browser metrics bind the same run ID, runtime candidate, capture-manifest
hash, browser-video path, byte count, and video hash. They report:

- 162 expected and 162 output frames;
- zero decode errors, dropped frames, raw-message drops, resyncs, resync skips,
  and skipped presentation slots;
- zero console events and zero page errors;
- open WebSocket state and no wait-for-keyframe state at completion;
- canvas backing size `960 x 540`, logical grid `240 x 135`, DPR 1;
- command acknowledgement latency from 20.903 to 50.827 ms.

Both measured UI rectangles are contained by the `1280 x 633` content
viewport:

- canvas edges: `(160, 46.5)..(1120, 586.5)`;
- toolbar edges: `(414, 569)..(866, 621)`.

The rectangles overlap by 17.5 vertical pixels, so the evidence README's literal
phrase "without overlap" is too broad. The overlap is confined to the canvas's
empty bottom stage margin. With action pixels ending at logical row 126 and a
four-pixel device cell, the lowest occupied character cell ends before the
toolbar begins. No avatar pixels are clipped or covered. This documentation
wording issue does not invalidate V4 animation evidence.

The browser sampler records 33 duplicate screencast samples, while its fixed
output remains 162 frames and all decode/presentation loss counters remain zero.
The initial-to-final decoded, presented, and drawn counters each advance by 163,
consistent with one live boundary transport frame around the 162-frame owned
program. These are capture-sampling observations, not dropped-frame evidence.

## Analyzer Correction And Tests

At runtime commit `1fe705e`, the recovery gate required explain coverage
`0..19` and point coverage `1..17`. The real strict capture shows that
authored frame zero for each gesture is the bounded transition immediately
before scenario ownership begins. Analyzer commit `c009607` changes the
required owned coverage to `1..19` for both gesture classes.

This is appropriate for two reasons:

1. It no longer demands an unowned transition frame inside an owned-scenario
   coverage set.
2. It strengthens point recovery by adding required authored frames 18 and 19,
   rather than merely relaxing the check.

The added
`test_first_owned_gesture_frame_may_follow_bounded_transition` regression
proves the missing-owned-frame-zero case passes. Existing fail-closed tests
still reject missing strokes, non-neutral holds, root drift, clipping, and
missing observed point frames. I independently ran 81 relevant acceptance,
visual-review, pose-library, and capability tests; all passed.

Executing the corrected analyzer in memory against the original runtime-bound
capture produced bytes identical to the retained machine report:
`6,948` bytes, SHA-256
`09ad102d692848b97fab02f64de7e72d9b56ff53963ae50c8a00bac021915546`.

## Residual Risks

- Strict capture validation is intentionally bound to the original runtime
  repository root. Running it directly against the relocated published copy
  fails the repository-root check. Validation passes at the original read-only
  location, and all 175 published capture files are independently byte-identical.
- The review-bundle schema identifies the runtime candidate but has no separate
  analyzer-commit field. Analyzer provenance therefore depends on the evidence
  README, Git ancestry, report hash, and reproducible replay. A future schema
  version should bind analyzer commit and tree directly.
- The new unit test models owned coverage beginning at frame one but does not
  itself construct all six unowned boundary records. The immutable capture and
  corrected analyzer replay exercise the real six-boundary case; a dedicated
  negative unit test for misplaced boundary frames would improve fail-closed
  coverage.
- The browser canvas and toolbar bounding rectangles overlap in an empty stage
  margin. Active character pixels are clear, but future browser evidence should
  report content-occlusion bounds explicitly instead of saying the rectangles
  do not overlap.
- This review establishes systems behavior and evidence integrity only. Gesture
  motivation, acting rhythm, restraint, silhouette appeal, and visible pop
  detection remain the independent animation reviewer's responsibility.

Verdict: PASS V4
