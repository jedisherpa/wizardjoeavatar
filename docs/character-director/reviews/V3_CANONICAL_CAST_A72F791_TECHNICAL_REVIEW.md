# V3 Canonical Cast `a72f791` Technical/Evidence Review

**Overall verdict: PASS**

**Machine-evidence verdict:** PASS
**Technical visual-evidence verdict:** PASS with the playback limitation stated
below
**Prior review:** the `092f78e` technical FAIL remains historical and was not
modified

**Reviewer role:** independent character technical director and evidence
verifier
**Candidate:** `a72f7915479787ba8cd65da2f5075ec99400c16c`
**Candidate tree:** `aba163cc72456d91c784474a5d12a295f822ec09`
**Evidence package:**
`evidence/character-director/v3-canonical-cast-a72f791-2026-07-19/`
**Capture manifest SHA-256:**
`438d0e3525a679a5da78324bfa0ade7dbeb182cbcb0c4afd408ca2b6fe994004`

## Decision

Candidate `a72f791` closes the two hard defects from the `092f78e` technical
review without relaxing V3's behavioral gates:

1. The published capture is complete. All 177 manifest-declared artifacts are
   present, byte-count correct, and SHA-256 correct, including all 170 sample
   PNGs and both wire artifacts.
2. The stale post-cast pose is gone. Every owned frame in `v3-hold-one`,
   `v3-hold-two`, and `v3-settle` renders authoritative `front_idle` under
   `idle_front`.
3. The authored graph contract is explicit and exact. It contains 32 atomic
   graphs; frames 0 and 31 are cell-identical to `front_idle`; all staff grips
   are fixed; and every adjacent authored staff-tip step is within two local
   cells.
4. Real capture observes the complete nonterminal authored set `0..30` across
   three casts, including one cast that observes every nonterminal frame.
   Terminal frame 31 is intentionally represented by the following exact
   neutral graph and is followed by a sustained neutral hold.
5. Capture-manifest validation, semantic wire replay, machine analysis, and
   review-bundle validation all pass from the exact recorded clean checkout.
   The regenerated machine report is byte-identical to the retained report.

The remaining observations are portability and review-depth risks, not V3
acceptance failures.

## Validation Replay

The capture records runtime root
`/private/tmp/wizardjoe-v3-capture-7774534`. That clean checkout still exists at
the exact candidate commit. Running its candidate analyzer against the
published bundle produced:

- process exit code: `0`;
- capture-manifest validation: PASS;
- semantic artifact replay: PASS;
- V3 analyzer result: PASS;
- regenerated report SHA-256:
  `ea9c11748fb90fef93cb35b2edd710a70758c56fcc943a7c55eba6ee01605a2b`;
- byte comparison with retained `v3-machine-acceptance.json`: identical;
- review-bundle validation: PASS.

The same replay correctly fails when the analyzer is run from a different or
dirty repository root, because runtime identity includes the absolute capture
checkout. I did not bypass that gate. The successful replay was executed from
the recorded clean root using the recorded candidate source.

## Hash And Inventory Audit

All top-level artifact hashes match their files:

| Artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `438d0e3525a679a5da78324bfa0ade7dbeb182cbcb0c4afd408ca2b6fe994004` |
| `review-bundle-manifest.json` | `2ff8ebe60f4865d2c44e7ebb1f930d646e6637e7234950ef3f405531a719267e` |
| `scenario-program.json` | `fb4ca6d69ffbbd829ffaf98dd5bfc2234aca8b7f1df4617b050b871cb95f5108` |
| `animation_truth_trace.ndjson` | `1249c8ade3702954c3f4f0650c5625f5a890d4fda6aa644599f8df5fb2887ec8` |
| `contact_verification.json` | `f8461163cf18da05f7cc0d1399d92dc3fe8d3d2a5bd5949dba7e274a5239e96d` |
| `v3-machine-acceptance.json` | `ea9c11748fb90fef93cb35b2edd710a70758c56fcc943a7c55eba6ee01605a2b` |
| normal-speed MP4 | `b7d28babdc9dd62dd8b427e6f8bb61d49c330f74a71ee81d767ede5a72d89d7a` |
| quarter-speed MP4 | `b120b9de83e759123dc25a9e483a54ba35a08c29220d04a37e4ec36b408bbf11` |
| browser-layout MP4 | `9656b2b8fcbe1d647b61d953818d4de856b38b909445745788642f9363b89843` |
| browser metrics | `259d29cc118020db11349de086e29a0da57df356bc57b709064b988fe7a96b14` |
| contact sheet | `bd72460495e01b98475faf3383db00f2dff93dfa4fbb06ba177e945e85ea6126` |

The capture manifest registers 177 artifacts: 170 samples, two wire files, and
five principal capture artifacts. Independent inventory checking found zero
missing files and zero byte-count or hash mismatches. `wire/index.ndjson` and
the truth trace each contain 242 records. `wire/frames.bin` contains 80,885
bytes.

Strict semantic replay did more than inventory checking: it re-decoded the wire
stream, verified offsets, codec tags, decoded lengths, decoded SHA-256 values,
FNV-1a frame hashes, atomic truth pairings, and recomputed contact evidence.
The stored contact report and embedded contact summary match that replay.

The version-2 review-bundle manifest separately binds:

- machine acceptance to the immutable capture-manifest hash;
- quarter-speed review to the normal-speed video hash;
- browser video to browser metrics, candidate, run ID, and capture-manifest
  hash.

This directly closes the prior unbound machine/quarter-speed concern.

## Runtime Provenance

Start, end, and capture provenance agree on:

- commit `a72f7915479787ba8cd65da2f5075ec99400c16c`;
- tree `aba163cc72456d91c784474a5d12a295f822ec09`;
- branch `codex/v3-capture-7774534`;
- clean worktree with empty status and tracked-diff hashes;
- repository and working root
  `/private/tmp/wizardjoe-v3-capture-7774534`;
- PID `86374` and process epoch
  `wizard-runtime-1822367da5394b3f8b3f71702a4d9a06`;
- launcher SHA-256
  `825775e1a67255da232ecf2a7c1d699817447a1ff09ecde835b8dae845f09bfe`;
- Python 3.9.6 and a `240 x 135`, 24 FPS, four-byte-cell renderer;
- isolated endpoint `127.0.0.1:8896`.

All seven capture commands have contiguous source sequences, applied
acknowledgments, and one command-runtime epoch. Runtime snapshots and browser
commands retain consistent process and command epochs. No protected service is
part of this evidence.

## Capture Ownership And Contiguity

The transport contains 242 unique contiguous frames indexed `0..241`. Exactly
240 are scenario-owned and presentation-indexed `0..239`. Two frames, transport
indexes 12 and 181, are explicitly unowned with null scenario and presentation
ownership. They occur only at command boundaries and are excluded from the
normal-speed 240-frame review video.

Owned scenario counts are exactly:

`12 + 36 + 48 + 36 + 48 + 36 + 24 = 240`.

The expected scenario order and every scenario block are contiguous. There are
zero dropped frames, decoded gaps, decoder errors, queue overruns, or scenario
window spill. Queue high-water mark is 1 of 16. The analyzer's bounded
transition-frame support is stricter than silently assigning boundary frames:
unowned frames must be null-owned and occupy legal inter-scenario boundaries.

## Authored Coverage And Exact Neutral Terminal

The static library contains exactly `cast_front_00` through `cast_front_31`.
Independent canonical cell hashing produced the same digest for all three
neutral graphs:

| Pose | Cells | Root | Staff hand | Staff tip | Canonical-cell SHA-256 |
| --- | ---: | --- | --- | --- | --- |
| `front_idle` | 3430 | `(36,95)` | `(56,50)` | `(58,12)` | `f690b1621dd8d37c5d25ff29547d215f943726f99d21b69ef773ddae3f7449f0` |
| `cast_front_00` | 3430 | `(36,95)` | `(56,50)` | `(58,12)` | `f690b1621dd8d37c5d25ff29547d215f943726f99d21b69ef773ddae3f7449f0` |
| `cast_front_31` | 3430 | `(36,95)` | `(56,50)` | `(58,12)` | `f690b1621dd8d37c5d25ff29547d215f943726f99d21b69ef773ddae3f7449f0` |

Observed dynamic coverage is transparent rather than overstated:

- cast one observes `1..24` and `28..30`;
- cast two observes every nonterminal frame `0..30`;
- cast three observes `1..30`;
- the observed union is exactly `0..30`.

Frame 31 is not required to appear as a separate cast-labeled transport frame
because it is exactly the authoritative neutral graph. The analyzer now
requires the complete nonterminal union, exact static frame-31 neutrality, all
markers, and an immediate neutral following scenario. This is a stronger and
more explicit contract than the prior analyzer's acceptance of any nonempty
matching subset.

## Stale Hold-Pose Closure

The stale `cast_front_29`/`cast_front_30` hold bug is closed in both runtime
evidence and focused regression coverage:

- all 48 `v3-hold-one` frames render pose `front_idle` under clip
  `idle_front`;
- all 48 `v3-hold-two` frames render pose `front_idle` under clip
  `idle_front`;
- all 24 `v3-settle` frames render pose `front_idle` under clip `idle_front`;
- `test_cast_settle_renders_authoritative_neutral_pose` drives the real frame
  source through a cast and requires authored pose, rendered pose, and display
  authority all to settle to `front_idle`.

An adversarial re-analysis that changed the first hold frame back to
`cast_front_30` failed the overall report and the
`authored_coverage_and_terminal_neutral` gate. This is genuine fail-closed
behavior, not a documentation assertion.

## Markers, Roots, Grip, Staff, Effects, And Bounds

Each of the three real casts emits exactly:

1. `action_commit` at authored frame 10;
2. `action_effect` at authored frame 14;
3. `action_recoverable` at authored frame 23;
4. `action_settled` at authored frame 28.

Across all 88 observed `cast_front` truth records:

- world root is fixed at `(0.0,5.0)`;
- presented root is fixed at `(120.0,126.82058823529412)`;
- derived staff-hand drift is `0.0` cells;
- all 32 static staff-hand anchors are `(56,50)`;
- maximum adjacent authored staff-tip movement is two local cells;
- repeated authored frames have no conflicting staff-tip location;
- 39 active effect records cover stroke, hold, and recovery;
- every active effect has positive intensity and a valid stage staff-tip;
- character silhouette bounds remain `x=79..160`, `y=22..126` on the
  `240 x 135` stage;
- clipped cast frames: zero.

Contact replay passes all 242 transport frames with zero planted drift, zero
planted-raster-span drift, and zero root residual.

## Browser And Media Evidence

The normal-speed artifact is H.264/yuv420p, `960 x 540`, 240 frames at 24 FPS,
and exactly 10.000 seconds. The quarter-speed artifact is H.264/yuv420p,
`960 x 540`, 240 frames at 6 FPS, and exactly 40.000 seconds. Timestamp-normalized
frame-sequence comparison yields SSIM `0.999916`, confirming a lightly
re-encoded four-times-duration derivative of the same frame order.

The browser-layout artifact is H.264, `1440 x 814`, 240 frames at 24 FPS, and
10.000 seconds. Browser evidence is bound to this candidate, run ID, process
epoch, and capture-manifest hash. It records:

- 240 expected and 240 output video frames;
- zero page errors and zero console events;
- zero decode errors, client drops, raw-message drops, resyncs, resync skips,
  or skipped presentation slots;
- open WebSocket and no wait-for-keyframe state at completion;
- DPR1 `1440 x 900` requested viewport;
- `1440 x 810` canvas with `240 x 135` logical cells and six device pixels per
  cell;
- toolbar and media status contained by the measured `1440 x 813` page
  viewport.

The browser's initial-to-final counters advance by 242 decoded frames and 241
presented/drawn frames while the fixed output video contains 240 scenario
frames. This reflects live boundary transport and sampling, not one browser
screenshot per owned truth frame. It is retained as a residual limitation; the
separate wire/trace ledger supplies exact 242-frame transport truth.

## Technical Visual Review

Direct continuous video playback was unavailable in this review environment.
I inspected the native contact sheet plus independently extracted chronological
normal-speed and browser-layout key frames, including every cast/hold boundary.
I also verified video metadata and normal/quarter frame correspondence. This
technical visual pass does not replace a director watching the normal and
quarter-speed clips in real time.

The retained frames show:

- no face or hat collision from the revised outward crook;
- stable hand attachment and a coherent staff arc;
- readable effect placement at the crook;
- exact visual return to the lighter neutral staff graph after every cast;
- no stale dark cast staff during either two-second hold or final settle;
- stable feet, wings, robe, root, and framing;
- no stage or browser crop.

The body acting remains intentionally restrained, with most cast motion carried
by the staff and effect. That is a future performance-quality opportunity, not
a continuity or V3 evidence defect.

## Fail-Closed Verification

Candidate test replay produced 46 passing actual tests across V3 acceptance,
capture/review validation, runtime identity, pose-library integrity, cast-staff
generation, and real-render settle behavior. Relevant negative coverage proves
rejection of:

- missing or malformed artifacts;
- hashed artifacts that do not semantically replay;
- runtime commit, process, render, or repository-root mismatch;
- queue overflow, decoder gaps, scenario spill, and snapshot conflicts;
- a missing marker or oversized staff jump;
- missing required nonterminal authored coverage;
- stale post-cast hold pose.

Independent mutations against the retained trace confirmed that removing
authored frame 25 from all casts fails the coverage gate and changing the first
hold to `cast_front_30` fails terminal-neutral acceptance. Running validation
from the wrong dirty checkout also fails. No acceptance check was disabled to
make this package pass.

## Residual Risks

1. Runtime replay is absolute-path bound. The recorded clean checkout remains
   available and validation succeeds there, but a future verifier must recreate
   that exact resolved path or the strict root-identity gate will reject the
   otherwise identical commit. The README's phrase "a clean checkout" should be
   read as the recorded checkout, not any arbitrary path.
2. Not every cast exposes every authored nonterminal frame at the 24 FPS
   presentation boundary. Cast two supplies complete `0..30` dynamic coverage;
   the other two repetitions, static 32-graph audit, markers, and repeatability
   checks supply corroboration.
3. Browser screencast sampling is not a frame-for-frame parity ledger. It has
   249 screencast events, 18 duplicate samples, and two decoded frames queued at
   the final metrics snapshot. No error/drop/resync symptom is present.
4. The analyzer proves effect phase, intensity, tip availability, and character
   silhouette bounds. It does not independently report a complete raster bound
   for every effect pixel.
5. Final acting appeal remains separate from this technical/evidence verdict,
   particularly because direct continuous playback was unavailable here.

## Final Verdict

**PASS.** Candidate `a72f791` provides a complete, hash-clean, semantically
replayable V3 package bound to a clean runtime commit. The prior missing
sample/wire evidence is restored; the review products are now bound; the full
nonterminal authored set and exact neutral terminal graph are proven; every
post-cast hold is authoritative neutral; marker, root, grip, staff, effect,
contact, stage, media, and browser gates pass; and adversarial checks fail
closed. The historical `092f78e` technical FAIL remains valid for that older
bundle and is not overwritten by this acceptance.
