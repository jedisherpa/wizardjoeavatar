# Independent Animation-Quality Verification

Verification date: 2026-07-12  
Repository: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar`  
Branch: `codex/build-repeatable-avatar-animation`  
Role: independent verification only; no runtime, test, asset, or evidence edits

## Verdict

**FAIL - NO SHIP**

The Rust animation and transport implementation is materially improved and its
unit/integration suites are healthy. The original shredded-silhouette failure is
absent from the regenerated source-frame contact sheets and is rejected by a
fresh exhaustive topology test. However, the pass does not satisfy its own final
verification contract:

1. The read-only evidence integrity check fails.
2. The claimed 36/36 transition-boundary gate does not measure the animated
   transition after time advances, and two advertised fields are hard-coded.
3. No controlled browser demonstration, compositor capture, cross-browser run,
   DPR matrix, browser console capture, or browser recording exists.
4. The 30-minute and two-hour soaks are configured but were not run.
5. Direction changes intentionally use a midpoint whole-pose handoff. This
   prevents shredding but leaves an abrupt topology snap rather than a continuous
   turn transition.

The implementation is suitable for another verification/fix iteration, not a
completion declaration.

## Blocking Findings

### 1. Evidence integrity fails

Command:

```text
cargo run --quiet --bin wizard-avatar-evidence -- --check-integrity
```

Result: exit 1, `Error: evidence integrity mismatch`.

A separate read-only recomputation checked all 1,038 manifest entries and found
exactly two mismatches:

| Path | Manifest | Current |
| --- | --- | --- |
| `face-mouth-cleanup-crop.png` | 6,341 bytes; hash64 `c3910aca17f45a2f`; CRC32 `fb5cad61` | 6,380 bytes; hash64 `ef1c9a903c60d410`; CRC32 `2e50cf67` |
| `face-mouth-cleanup-full.png` | 20,835 bytes; hash64 `cf305443a60bb469`; CRC32 `051ccdfa` | 20,887 bytes; hash64 `5a34d75c34631248`; CRC32 `4fe98d08` |

Both current files were modified after `evidence-integrity.json`. The final
evidence package therefore cannot be treated as sealed or complete.

### 2. The transition acceptance metric is not a temporal gate

`src/evidence_main.rs:290-293` measures state immediately before and after
applying boundary commands at the same runtime tick. It does not advance the
simulation before calculating root, planted-foot, staff, face, or scale jumps.
This explains why all 36 stored metrics are exactly zero, including commands
that only begin a turn or transition.

Additionally, `src/evidence_main.rs:541-542` writes
`unexpected_mask_writes: 0` and `source_decoded_equal: true` as constants in the
boundary record. Source/decode equality is checked for emitted frames elsewhere,
but the boundary record does not calculate either field.

The replay does emit 12 pre-boundary and 16 post-boundary frames, but the stated
acceptance matrix is not evaluated across those frames. The 36/36 metric claim
is therefore **artifact-only, not automated transition proof**.

### 3. Browser completion remains unverified

The stored `browser-console.json` explicitly records module-only scope,
`console_errors: null`, and no real browser control. I attempted an independent
controlled in-app-browser session against a fresh local server on port 8792, but
the browser surface did not attach. No controlled-browser pass is claimed here.

The Node tests prove decoder, queue, generation, fixed-viewport, and atomic
renderer behavior as modules. They do not prove real Chromium/Firefox/Safari
compositor timing, DPR behavior, visibility lifecycle, context restoration, or
the complete browser demo required by the numbered specification.

### 4. Long-soak release gates are configured only

The stored 15-second short soak covers 0/1/2/4/8 viewers and reports healthy
60 Hz simulation, 24 FPS rendering, no sequence gaps, no lag, and no canonical
hash mismatches. `soak/configurations.json` defines 1,800-second CI and
7,200-second nightly modes, but neither long run was executed.

## Independent Command Results

| Command/check | Result | Scope |
| --- | --- | --- |
| `cargo fmt --all -- --check` | PASS | Rust formatting |
| `cargo test` | PASS: 57 tests, 0 failed/ignored | Rust unit and integration |
| `cargo clippy --all-targets -- -D warnings` | PASS | All Rust targets |
| `node --test web/tests/*.test.mjs` | PASS: 16 tests, 0 failed/skipped/todo | Browser modules, not a real browser |
| Fresh read-only ASCILINE vector decoder | PASS: 52 vectors | Tags 0/1/2/3; source equals decoded; five-byte envelope |
| Replay artifact consistency | PASS | Manifest hash recomputed; run summaries equal; 1,008 logged frames |
| `wizard-avatar-evidence -- --check-integrity` | **FAIL** | Two changed PNGs |
| Four MP4 decode checks with `ffmpeg` | PASS | Files decode; 1,008 total frames at 24 FPS |
| Snapshot manifest test | PASS | 30 declared PPM snapshots exist |
| Snapshot generator binary | NOT RUN | It overwrites generated evidence; verifier was permitted to write only this report |
| Full deterministic evidence generator | NOT RUN | It resets and rewrites the evidence bundle |
| Controlled browser demo | UNAVAILABLE | Browser did not attach |
| 30-minute CI / two-hour nightly soak | NOT RUN | Configured only |

The stored replay artifacts are internally consistent: manifest hash
`ba1afe183d3f31b8`, semantic hash `31741f6b4fb7494c`, raw hash
`8325812ab749a650`, equal summaries, 1,008 state frames, and category counts
308/476/84/140. This is not equivalent to a fresh replay regeneration.

## Runtime Architecture Audit

### Verified automated or by source inspection

- One central `AvatarRuntime` owns fixed 60 Hz semantic steps.
- `SimulationAccumulator` uses whole ticks and caps catch-up at eight steps.
- One `AvatarFrameHub` renders/encodes canonical frames and broadcasts immutable
  packets; socket handlers do not advance simulation or reset global history.
- Bootstrap/resync emits a non-delta full frame; healthy-client history remains
  decodable during reconnect and lag recovery.
- Browser encoded queue is bounded to four messages, 2 MiB, and 250 ms; complete
  presentation queue is bounded to two frames.
- Generation changes and resync clear encoded and complete-frame queues.
- Visible Canvas commits occur through the rAF renderer from a complete logical
  back buffer with smoothing disabled.
- Production runtime/browser source contains no `<img>`, PNG runtime path,
  reference overlay, `new Image`, or `reference-avatar.png`; the old PNG is absent.
- ASCILINE tags remain RAW=0, ZLIB=1, DELTA=2, RLE=3 with the five-byte
  `[u32 big-endian sequence][u8 tag]` envelope.
- Fresh decoding of all 52 stored vectors passed with tag counts 1/1/39/11.
- Eight distinct directional poses, distance gait phase, side/diagonal stride
  axes, analytical circle, arc-length figure-eight table, spline traversal,
  depth hysteresis, and contact correction have passing focused tests.
- Speech, action, expression, effect, staff, locomotion, and facing generations
  are separated enough for the tested overlap/replacement/restoration cases.

### Residual architecture risks

- The render producer samples only the current fixed state; it does not use the
  runtime's previous/current snapshots and accumulator alpha for interpolation.
- Direction topology changes at `facing_blend == 0.5` by replacing the complete
  pose. This is coherent and non-shredded, but visually discrete.
- The transition test permits up to six local staff-anchor cells between some
  samples, while the plan's stable target is zero and transition target is one.
- The final transition metric does not calculate temporal mask writes.

## Visual and Recording Audit

I visually compared the baseline and final locomotion contact sheets and
inspected all four final contact sheets plus representative source frames.

- Baseline: multiple frames visibly shred the head, torso, wings/robe, and staff
  into horizontal fragments.
- Final: complete coherent silhouettes are present; no shredded torso/head,
  duplicated staff, or detached face is visible in the sampled sheets.
- Walking frames show alternating boot placement, robe opening, torso/root rise,
  arm counter-motion, translation, side/diagonal views, and a stable staff grip.
- White fixed stage, faint perspective floor, and contact shadow are present.
- All four MP4s decode without errors and have the recorded frame counts:
  308, 476, 84, and 140 at 24 FPS.

This visual result is **source-output evidence**, not controlled-browser video.
The shredded transition defect is absent from regenerated outputs, but the
midpoint whole-pose handoff remains a visible continuity limitation.

## Defect Ledger Audit

Evidence classes: **Automated** = fresh executable test; **Visual** = contact
sheet/source-frame inspection; **Module-only** = shipped JS exercised without a
browser; **Configured-only** = declared but not run; **Unverified** = no adequate
proof in this audit.

| Defect | Verification | Status |
| --- | --- | --- |
| ANIM-GLITCH-001 viewer advances simulation | Automated fixed-clock, fanout, short-soak evidence | PASS |
| ANIM-GLITCH-002 automatic client tours | Module-only source assertion and code inspection | PASS at module level |
| ANIM-GLITCH-003 reconnect corrupts encoder | Automated hub and WebSocket reconnect/resync tests | PASS |
| ANIM-GLITCH-004 unbounded/decode-driven browser paint | Module-only queue/rAF/atomic-render tests | PARTIAL; real browser unverified |
| ANIM-GLITCH-005 per-frame crop/scale popping | Module-only fixed viewport; Visual fixed-stage frames | PARTIAL; real browser unverified |
| ANIM-GLITCH-006 hard unrelated pose switches | Automated coherent-topology test; Visual no shredding | PARTIAL; midpoint whole-pose snap remains |
| ANIM-GLITCH-007 color-classified tearing | Automated semantic-region/topology tests; Visual | PASS |
| ANIM-GLITCH-008 incomplete side/diagonal gait | Automated stride-axis/gait/contact tests; Visual | PASS at source level |
| ANIM-GLITCH-009 destructive shared action state | Automated generation/overlap/restore tests | PASS |
| ANIM-GLITCH-010 unanchored overlays/staff | Automated schema/anchor and action tests; source inspection | PASS at source level |
| ANIM-GLITCH-011 render-coupled simulation | Automated accumulator/fanout tests; short soak | PASS |
| ANIM-GLITCH-012 missing floor | Automated renderer test; Visual | PASS |
| ANIM-GLITCH-013 unrelated root/shadow offsets | Automated projection/contact tests; Visual | PASS at source level |
| ANIM-GLITCH-014 path heading snaps | Automated circle/figure-eight/spline and heading tests | PASS at module level |
| ANIM-GLITCH-015 speech moves whole root | Automated channel/locomotion test; source inspection | PASS |
| ANIM-GLITCH-016 tests miss temporal/multiclient quality | Many new automated tests, but flawed transition metric and no browser/long soak | **FAIL** |

## Transition Category Audit

All 32 baseline transition/invariant rows appear in the 36-recipe replay
manifest; four recovery/fanout scenarios were added. Presence in the manifest
and generated frames is verified. Acceptance is classified as follows:

| Category | Evidence | Result |
| --- | --- | --- |
| idle/walk/turn and eight-direction changes | Focused Rust tests + source contact sheets | Automated/Visual, but per-transition jump gate unverified |
| clockwise/counterclockwise/figure-eight | Path unit tests + source recording/contact sheet | Automated/Visual, browser unverified |
| speech/action/expression/blink/mouth/staff | Channel tests + source recording/contact sheet | Automated/Visual, temporal mask gate unverified |
| depth/root/shadow/contact | Projection/contact tests + source frames | Automated/Visual, browser viewport parity unverified |
| interruption/reaction restore | Generation/restore tests | Automated |
| reconnect/fanout/missing delta | Rust integration + JS module tests | Automated/Module-only |
| hidden/resume/context restore | JS module tests only | Module-only |

The generated metrics must be redesigned to compare actual consecutive emitted
frames throughout each transition window before the transition matrix can be
accepted as a release gate.

## Specification Conflict

`docs/00-goal-and-visual-contract.md` and the supplied reference require rainbow
wings, while `docs/37-completion-gate.md` still says the character has no wings.
The implementation follows the current reference and updated visual contract.
This contradiction should be resolved in the numbered specification before a
formal completion declaration.

## Git State

The branch contains a large dirty worktree: the Rust engine/evidence are
untracked, while Python/TypeScript/runtime files and documentation are modified.
No unrelated changes were reverted or edited during verification. The only file
written by this verifier is this report.

## Ship Recommendation

**Do not ship or declare the animation-quality pass complete yet.**

Minimum re-verification requirements:

1. Regenerate or deliberately update the evidence bundle and pass the read-only
   integrity check.
2. Replace the zero-time boundary metric with real pre/post temporal assertions
   over emitted frames; calculate mask writes and equality instead of constants.
3. Run and record the complete browser demo in at least one controlled browser,
   including console, rAF presentation, resync, hidden/resume, and context restore.
4. Run the 30-minute CI soak; retain the two-hour mode as nightly if necessary.
5. Decide whether the coherent midpoint direction snap is acceptable or author a
   continuous topology-safe transition.
6. Reconcile the wing requirement conflict in the numbered docs.

After those items pass, the strong existing Rust, codec, gait, channel, and
transport tests provide a credible base for a final ship audit.
