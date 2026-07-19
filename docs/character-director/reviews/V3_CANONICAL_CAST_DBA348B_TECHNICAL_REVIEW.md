# V3 Canonical Cast `dba348b` Technical Review

**Reviewer role:** independent technical verifier  
**Candidate:** `dba348be4ff0af21f868491cbd8de877c13d3ee2`  
**Candidate tree:** `8bdcbd2bf4bd5333fabf79bb2615090780f52b48`  
**Evidence:** `evidence/character-director/v3-canonical-cast-dba348b-2026-07-19/`  
**Review date:** 2026-07-19

## Decision

The corrected evidence bundle is complete, hash-clean, bound to the exact clean
candidate, semantically replayable, and fail-closed for the V3 defects under
review. All 12 machine checks pass. The retained analyzer report reproduces
byte for byte from the candidate source.

This candidate closes the two defects that caused the independent animation
rejection of `a72f791`:

1. Every cast presents the complete contiguous recovery window `23..30`.
2. The analyzer now audits the complete staff raster, not only its tip anchor,
   and the retained staff stays within the measured rigid-grid continuity
   bounds without a palette, shaft, hook, or length replacement.

## Publication Correction

The initially published `review-bundle-manifest.json` ended with the two
literal bytes `\` and `n` after its closing brace. Those superseded bytes are
not the artifact reviewed here. The publication correction removed only those
two invalid trailing bytes and updated the README hash. The corrected file:

- ends with the valid byte sequence `0a 7d 0a`;
- parses as strict JSON;
- has SHA-256
  `156491501d5b28c81e494d523eb368dd63ceb4bc2498aa3ae521615efddc594b`;
- passes `validate_review_bundle_manifest()` from the clean candidate.

The corrected manifest and README are present at repository commit `f096cbd`
(`Repair V3 review bundle JSON terminator`). The runtime candidate remains
`dba348b`; the correction changes no capture, trace, media, machine result, or
candidate code.

## Candidate And Runtime Binding

The clean candidate worktree resolves to
`/private/tmp/wizardjoe-v3-capture-747f59d` and independently reports:

- HEAD `dba348be4ff0af21f868491cbd8de877c13d3ee2`;
- tree `8bdcbd2bf4bd5333fabf79bb2615090780f52b48`;
- empty porcelain status and tracked diff, both hashing to the SHA-256 of an
  empty stream, `e3b0c442...b855`;
- branch `codex/v3-capture-747f59d`.

Capture provenance, runtime-binding start, and runtime-binding end agree on
that commit, tree, branch, clean status, resolved worktree, launcher hash,
Python 3.9.6 runtime, PID `31810`, runtime epoch
`wizard-runtime-9d38e3dc532d4bd1947535dd570c5276`, renderer `240 x 135`
at 24 FPS, and isolated endpoint `127.0.0.1:8896`. Runtime binding is recorded
as verified with no failure reason. All seven source-sequenced commands have
applied acknowledgements in one command-runtime epoch.

## Hash And Inventory Audit

Both strict validators pass from the clean candidate:

- capture-manifest validation: PASS;
- review-bundle validation: PASS.

The capture manifest declares 216 unique artifacts with no missing file,
byte-count mismatch, duplicate path, or SHA-256 mismatch: 209 retained sample
PNGs, two wire artifacts, the truth trace, contact report, scenario program,
normal-speed video, and contact sheet. The review manifest additionally binds
the capture manifest, machine report, quarter-speed derivative, browser video,
and browser metrics.

| Artifact | Verified SHA-256 |
| --- | --- |
| `manifest.json` | `84a8e1bc50e684122e6275ce740d95b49985e8d54c8bdba2af4a2e686ec1e3a3` |
| corrected `review-bundle-manifest.json` | `156491501d5b28c81e494d523eb368dd63ceb4bc2498aa3ae521615efddc594b` |
| `scenario-program.json` | `3655beceec5c696f881d607d8eeaf8e2613397b3a4249c49106a3d7ffbb983aa` |
| `animation_truth_trace.ndjson` | `2e06079628278687660eda8a3ddd4617f509ac7e3e35c91ac737629e95de9aec` |
| `contact_verification.json` | `166d6ae60c50a8e49fdeee2a9013774c258ff62bef95e44713b21c58c4539efe` |
| `v3-machine-acceptance.json` | `f922b90be54aee06bf36463a27c20866b09c61fe943b198b9d7fb88e769ddc8f` |
| normal-speed MP4 | `8171627169bd3c8e93b197f93b0b0d560ac47834df5ed190a0f896e809e5c9cf` |
| quarter-speed MP4 | `62dc998b1eaf518a488d27fa241badc033f650cb2fa698b9310c0e4acaabaa3e` |
| browser-layout MP4 | `fd08bb5e4cb8c2e07b95d14ecc9498b57839045ceec21c18380890535eca1fd9` |
| browser metrics | `ee76a03771e2fd675d585ce90ee7e1ccd0ec0049756605b3c23b154c6220c58f` |
| contact sheet | `7363b18141a38cc70b3d1c6af0472589d42f03fea9ff2a5cfbaf1ae6af8d976a` |

## Deterministic Replay

Running `tools/analyze_character_director_v3.py` from the clean candidate
against the published absolute manifest reproduces the retained report
byte-for-byte. Both regenerated and retained report SHA-256 values are
`f922b90be54aee06bf36463a27c20866b09c61fe943b198b9d7fb88e769ddc8f`.
The replay reports overall PASS and all 12 named checks PASS.

## Capture, Wire, And Scenario Accounting

The manifest, wire index, and truth trace each contain 314 contiguous records,
covering transport indexes `0..313`. `wire/frames.bin` contains 101,183 bytes.
Every captured frame has a truth record and wire record.

Exactly 312 frames are scenario-owned. The only unowned frames are indexes
`120` and `229`; both are null-owned, bounded command-transition frames at
legal scenario boundaries. Owned counts exactly match the 13-second scenario:

| Scenario | Frames |
| --- | ---: |
| `v3-ready` | 12 |
| `v3-cast-one` | 60 |
| `v3-hold-one` | 48 |
| `v3-cast-two` | 60 |
| `v3-hold-two` | 48 |
| `v3-cast-three` | 60 |
| `v3-settle` | 24 |

Scenario blocks and transport indexes are contiguous. Capture validity is
true, with zero decoded gaps, decoder errors, dropped frames, or queue
overruns; queue high-water mark is one of 512.

## Cast Contract And Recovery

The candidate defines 32 canonical cast graphs, `cast_front_00..31`. Frames 0
and 31 are exact cell-equal neutral endpoints. The capture contains 91 cast
truth records and observes every nonterminal authored frame `0..30`.

Most importantly, every repetition independently contains the complete
recovery sequence with no gaps:

- `v3-cast-one`: `23,24,25,26,27,28,29,30`;
- `v3-cast-two`: `23,24,25,26,27,28,29,30`;
- `v3-cast-three`: `23,24,25,26,27,28,29,30`.

The first following frame for each cast is authoritative `front_idle`, and
terminal authored frame 31 is exact neutral. This directly corrects the
`a72f791` first-cast omission of recovery frames 25 through 27.

Every cast emits the same ordered marker sequence exactly once:

1. `action_commit` at authored frame 10;
2. `action_effect` at authored frame 14;
3. `action_recoverable` at authored frame 23;
4. `action_settled` at authored frame 28.

## Staff, Contact, Effects, And Clipping

The complete staff raster has 313 neutral cells and ranges from 312 to 321
cells across the rigid arc, a ratio of `0.997..1.026` to neutral. Its maximum
adjacent symmetric nearest-cell distance is three cells, exactly the declared
square-grid quantization limit; there are zero raster failures. The authored
staff-tip rate remains at or below two cells per authored frame, all repeated
authored frames agree, and the staff-hand anchor remains `(56,50)` throughout.

This is a stronger contract than `a72f791`, whose analyzer tracked the tip but
did not reject a wholesale shaft/hook/palette construction swap. Representative
retained recovery frames and the contact sheet also show the same long tan
staff construction throughout.

World-root, stage-root, staff-hand, planted-foot, planted-raster-span, and root
residual drift are all `0.0`. The contact verifier passes all 314 frames with
no issues. Every active effect has a valid staff-tip anchor and begins at the
authored effect marker. There are zero effect failures and zero clipped cast
frames on the canonical `240 x 135` stage.

## Browser And Media Verification

Independent media probing reports:

| Artifact | Raster | Frames | Rate | Duration |
| --- | --- | ---: | ---: | ---: |
| normal | `960 x 540` | 312 | 24 FPS | 13 s |
| quarter speed | `960 x 540` | 1,248 | 24 FPS | 52 s |
| browser | `1440 x 728` | 312 | 24 FPS | 13 s |

Browser counters advance by exactly 312 decoded, presented, and drawn frames.
The final metrics report zero decode errors, frame drops, raw-message drops,
resyncs, resync skips, ignored delta frames, or skipped presentation slots;
the WebSocket is open and not waiting for a keyframe. There are zero page
errors and zero console events.

The logical canvas is `240 x 135`, rendered at five device pixels per cell to
`1200 x 675`. Canvas, media status, and toolbar bounds are contained within the
measured `1440 x 727` page viewport. The one-pixel difference between the
measured page height and the encoded `1440 x 728` capture is capture rounding,
not content clipping.

## Fail-Closed Verification

The six focused V3 acceptance tests pass. They include negative tests for a
missing marker, excessive staff-tip movement, missing per-cast recovery,
full-staff-raster discontinuity, and invalid boundary ownership.

Additional in-memory adversarial checks against this exact published bundle
confirmed:

- changing a review artifact hash is rejected with `review artifact SHA-256 mismatch`;
- changing a source hash is rejected with `review artifact source SHA-256 mismatch`;
- changing the review candidate is rejected as differing from the capture;
- removing authored recovery frame 26 from cast one alone makes both the
  per-cast recovery check and overall V3 result fail;
- forcing one cast raster span outside column 239 fails the clipping gate;
- setting contact verification to false fails the planted-root/grip gate.

No validation gate was bypassed or weakened for this review.

## Residual Boundary

This is a technical/evidence verdict. It verifies the immutable capture,
runtime binding, deterministic replay, transport behavior, authored contract,
prop continuity, contact, effects, clipping, browser delivery, and fail-closed
logic. Final acting appeal and motion taste remain the independent animation
reviewer's responsibility.

Verdict: PASS V3
