# Integrated Animation-Quality Implementation Plan

## Purpose

This is the implementation lead's execution contract. It integrates:

- [`01_ANIMATION_GRAPH_AND_POSE_BLENDING_PLAN.md`](01_ANIMATION_GRAPH_AND_POSE_BLENDING_PLAN.md)
- [`02_SIMULATION_PATHING_PROJECTION_PLAN.md`](02_SIMULATION_PATHING_PROJECTION_PLAN.md)
- [`03_ASCILINE_BROWSER_VERIFICATION_PLAN.md`](03_ASCILINE_BROWSER_VERIFICATION_PLAN.md)

No wave may be declared complete from unit tests alone. Each gate names the
runtime evidence required before the next wave.

## Preserved Product Contract

- procedural editable character data and deterministic Rust rendering
- server-authoritative semantic commands/state
- direct ASCILINE glyph/RGB cell frames; no intermediary video
- current character identity, proportions, colors, and block language
- fixed white stage, faint checker floor, and contact shadow
- eight-direction depth-aware movement and all path types
- independent locomotion, upper body, staff, expression, blink, and speech
- adaptive RAW/ZLIB/DELTA/RLE codec compatibility
- deterministic replay and real browser verification

No PNG, sprite sheet, prerecorded clip, motion blur, slowed playback, or app
rewrite is an acceptable substitute.

## Ownership

One implementation lead owns all runtime code during this pass. The lead must
not create parallel clocks, controllers, renderers, decoder histories, or pose
representations. The three track plans define module ownership, but integration
occurs in this order.

## Wave 0: Lock the Baseline and Add Failing Quality Tests

Add test scaffolding before behavior changes:

1. multi-client viewer-count independence
2. reconnect isolation and missing-delta recovery
3. fixed 60 Hz exact-step assertions
4. source/decoded/presented A/B/C hash capture
5. temporal root/foot/staff/face metrics
6. fixed viewport and rAF-only Canvas instrumentation

Do not regenerate or alter `evidence/animation-quality/baseline/`.

Gate:

- tests reproduce `ANIM-GLITCH-001`, `003`, `005`, `006`, `007`, `009`,
  `011`, and `016`
- current green feature tests remain runnable

## Wave 1: Authoritative Runtime and Canonical Frame Hub

Implement `runtime.rs`, exact tick-stamped commands, previous/current snapshots,
and one render producer. Implement `hub.rs`, immutable canonical packet fanout,
cached full frame, bootstrap, and lag resync. Remove simulation advancement and
encoder reset from socket handlers.

Required code order:

1. `WizardAvatarController::step_tick`
2. `AvatarRuntime` and scheduled command queue
3. frame source sampling API
4. pure `encode_full_frame`
5. `AvatarFrameHub` producer/broadcast/latest snapshot
6. WebSocket bootstrap/resync state

Gate:

- identical simulation state for 0/1/2/4/8 viewers
- two healthy clients receive byte-identical canonical packets
- reconnecting one client does not alter another client's decoded hashes
- slow client does not alter healthy cadence or grow unbounded state
- no `Delta frame without previous frame` in injected reconnect/gap tests

Closes: `ANIM-GLITCH-001`, `003`, `011`; enables trustworthy later evidence.

## Wave 2: Fixed-Stage Browser Presentation

Split the browser into shared codec, bounded stream client, fixed-stage renderer,
and thin controls. Use generation/epoch/sequence gates, a four-message/2 MiB
encoded queue, a two-frame complete queue, and rAF-only atomic commits.

Remove dynamic content bounds, client visual transforms, duplicate mouth/eye/
shadow/effect animation, and automatic tour start. Render the full ASCILINE stage
as exact RGB blocks through `ImageData` and nearest-neighbor scaling.

Gate:

- A == B == C hashes for 1,000 idle/walk/action frames
- visible Canvas is always complete N or N+1, never a mixture
- fixed root/depth produces fixed viewport across all views/effects
- presented sequence strictly increases
- connection sends no semantic tour command until explicit user action
- no console errors during reconnect/hidden-resume test

Closes: `ANIM-GLITCH-002`, `004`, `005`; separates source animation defects from
transport/presentation defects.

## Wave 3: Pose Schema, Anchors, Regions, and Exact Rasterization

Add pose schema v2, explicit regions/anchors/contact markers/stable cell IDs/
z-order, and loader validation. Extend the generator to emit reviewed metadata.
Add `pose.rs`, correspondence caches, and destination-driven pose rasterization.

Migrate all eight directions before enabling new motion. Remove the
`ceil(scale) + 1` footprint and runtime RGB/saturation anatomy classifiers.
Move expression, mouth, staff, and effects to per-view semantic anchors.

Gate:

- every pose validates v2 metadata and required anchors
- one logical source cell has exact destination footprint
- no runtime anatomy classification by color
- fixed-state staff/face/root anchors match reviewed cells
- static visual identity remains approved against current reference

Closes: `ANIM-GLITCH-007`, `010`; prepares phase/contact motion.

## Wave 4: Locomotion, Steering, Paths, Projection, and Contact

Implement persistent distance gait phase, marker-aware pose sampling, adjacent
direction transitions, braking-distance arrival, rate-limited heading/hysteresis,
analytical circles, arc-length figure-eight/splines, projection hysteresis, one
projection context, integer planted-foot correction, cached floor, and
contact-driven shadow.

Remove hard quarter-cycle pose IDs, static profile/diagonal motion, polyline
circle/figure-eight helpers, blank reference background, and root-level speech
bob.

Gate:

- root and planted-foot jump are zero through all movement transitions
- side/diagonal gait has alternating contact and no rigid slide
- gait phase equals traveled distance across speed/direction/path changes
- direction changes are adjacent, rate-limited, and hysteretic
- circle speed/tangent and figure-eight crossover are continuous
- scale cannot chatter and browser preserves server world/depth motion
- shadow center follows only root/contact state

Closes: `ANIM-GLITCH-006`, `008`, `012`, `013`, `014`, and locomotion part of
`015`.

## Wave 5: Independent Animation Graph and Interruption

Implement `animation.rs` channel states, generation-safe expiry, priorities,
restoration, presented-pose snapshots, and masked anchor transitions. Preserve
locomotion through speech/actions; cast owns only approved upper-body/staff/effect
regions; reaction restores prior stable states; speech closes immediately on
cancel/end.

Remove bundled `set_action` semantics and any global action timer capable of
resetting unrelated channels.

Gate:

- all baseline action/speech/expression transitions preserve root/contact
- stale timers cannot cancel newer generations
- reaction restores previous stable state
- blink/speech/expression writes remain inside masks
- point/explain/cast interruptions begin from presented anchors
- walking, speaking, explaining, expression, blink, and staff coexist

Closes: `ANIM-GLITCH-009`, `015` and remaining channel-related `010`.

## Wave 6: Temporal Quality, Performance, and Compatibility

Run the complete transition matrix from the baseline objective. Generate final
recordings, frame sequences, state logs, pacing/queue metrics, A/B/C hashes,
multi-client evidence, and visual diffs.

Required automated gates:

- all existing Rust/Python tests
- all `WIZ-ANIM`, `WIZ-LOCO`, `WIZ-STEER`, `WIZ-PATH`, `WIZ-PROJ`,
  `WIZ-CONTACT`, `WIZ-PACE`, `WIZ-RESYNC`, `WIZ-DECODE`, `WIZ-PRESENT`, and
  `WIZ-CLASSIFY` tests
- production ASCILINE codec vector parity
- 30-minute CI soak; two-hour nightly soak configuration
- Chromium, Firefox, Safari matrix; 1x/2x DPR; hidden/resume/context restore
- medium profile sustains 24 FPS without queue growth

Closes: `ANIM-GLITCH-016` and proves every prior closure.

## Required Transition Acceptance Matrix

For every transition listed in the baseline ledger, capture at least 12 source
frames before and after the boundary and assert:

```text
root jump                  = 0 cells
planted foot jump          = 0 cells
staff-hand error           <= 1 during transition, 0 stable
face-anchor jump           <= 1 on adjacent view transition
unexpected mask writes     = 0
presented sequence         strictly increasing
source hash                = decoded hash = logical presented hash
viewport/root/scale source = browser-visible viewport/root/scale
```

Use reviewed region-churn thresholds for pose transitions; magic effects are
measured under a separate effect mask.

## Rollback and Migration Rules

- Keep compatibility adapters only inside tests or temporary internal flags.
- Never keep two active production clocks/renderers/decoders as a fallback.
- Do not delete old code until replacement tests pass, then remove it in the
  same wave.
- Preserve semantic HTTP/WebSocket command names and core codec tags.
- If a wave fails visual approval, fix that wave's invariant rather than hiding
  the defect with timing, blur, crop, or smoothing.

## Implementation Lead Checklist

- [ ] Read baseline, all research, and all track plans
- [ ] Record pre-edit git status and preserve unrelated changes
- [ ] Implement waves in order
- [ ] Update plan/evidence after each gate
- [ ] Run formatting, tests, clippy, JS syntax/module tests after each wave
- [ ] Keep the real local server running for browser checks
- [ ] Compare final recordings against baseline contact sheets
- [ ] Hand off to an independent verification agent with no implementation role

## Final Deliverables

- runtime modules and migrated production code
- complete named temporal/multi-client/browser tests
- `evidence/animation-quality/final/` artifact set
- `docs/animation-quality/05_IMPLEMENTATION_REPORT.md`
- `evidence/animation-quality/final/FINAL_ANIMATION_QUALITY_VERIFICATION.md`

The implementation is not complete until an independent verification agent
confirms every defect and transition requirement against current runtime
evidence.
