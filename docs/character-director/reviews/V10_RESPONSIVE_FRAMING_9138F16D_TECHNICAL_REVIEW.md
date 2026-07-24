# V10 Responsive Framing Technical Review

Date: 2026-07-24

Candidate implementation commit:
`9138f16d18ff822b885f4b4ed385c7373a40741f`

Evidence:
`evidence/character-director/v10-responsive-framing-9138f16d-2026-07-24/`

Reviewer role: independent technical acceptance reviewer

## Verdict

**PASS**

- Framing score: **4/4**
- Hard failures: **none**
- Blockers: **none**
- Product-approval-ready: **yes**

## Findings

### Stale first-frame defect: closed

The literal first encoded frame in all three browser videos starts at
`x 0.00 / z 5.00`, facing south, idle, neutral, and mouth closed, with
logical hash `fnv1a32:99face05`. No stale east-facing or edge-position frame
remains.

### Provenance: pass

The manifest binds to the exact commit and tree with a clean tracked worktree.
All 228 declared artifact sizes and SHA-256 hashes independently matched.

### Truthfulness and transport: pass

The trace is contiguous. All browser captures contain 528 frames at 24 FPS
with zero decoded drops, raw drops, resyncs, decoder failures, page errors, or
console errors.

### Responsive framing: pass

The exact profiles are desktop 1280x720 DPR1, desktop 1280x720 DPR2, and
mobile 390x844 DPR3. Physical cells resolve to integer sizes of four, eight,
and four pixels respectively, with smoothing disabled.

### Crop and overlap: pass

Observed minimum margins are 17 left, 6 right, 6 top, and 7 bottom cells,
exceeding the required side/top margin of four cells and bottom margin of six
cells. All profiles pass canvas containment, aspect, letterboxing, and
control-overlap checks.

### Contact: pass

There are 359 contact frames across 65 stances. Maximum planted raster drift
is exactly one cell, numerical planted drift is effectively zero, and no
contact issues were reported.

### Synchronization: pass

The recorder waits for two consecutive synchronized snapshots, clears prior
screencast state, and validates the first encoded identity. The stale-frame
regression fails closed.

### Focused tests: pass

The reviewer ran 36 focused V10 recorder, acceptance, and contact tests.

## Residual

Browser evidence includes 70-74 held presentation slots and duplicate sampled
frames. This is disclosed and does not undermine V10 framing. These browser
captures must not be used as proof of flawless 24 Hz motion cadence.

## Scope

Commit `9138f16d` is ready to enter V10 product approval. This technical
review does not by itself grant aggregate Character Director release
acceptance.
