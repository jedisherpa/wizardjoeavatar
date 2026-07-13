# Integrated Cartoon Animation Implementation Plan

Status: planning checkpoint candidate

Production target: ASCILINE Python service at `http://127.0.0.1:8765/`

## 1. Outcome

Turn the current 39-pose showcase into one server-authoritative cartoon character that:

- responds continuously to keyboard, gamepad, HTTP, and WebSocket control intents;
- starts, walks, runs, turns, stops, takes off, hovers, flaps, glides, banks, and lands with coherent timing;
- plays actions, expressions, blinking, speech, staff motion, and effects without cancelling locomotion unnecessarily;
- chooses poses through a data-driven clip and transition graph instead of a timed showcase override;
- preserves crisp square cells, root placement, foot contact, wings, staff attachment, facial anchors, and ASCILINE delta efficiency;
- optionally responds to sanitized Prism GT/CDISS posture signals without receiving private semantic content or surrendering user-control authority;
- remains deterministic, replayable, observable, and backwards compatible with the current port-8765 API.

## 2. Binding architecture

```text
remote input / semantic command / optional Prism visual signal
    -> strict Python boundary adapters
    -> ordered command and signal inboxes
    -> 60 Hz integer-tick AvatarRuntime
    -> control lease and animation-intent arbitration
    -> orthogonal locomotion, flight, action, face, speech, prop, effect regions
    -> graph-v2 clip evaluator and authored transition recipe
    -> immutable presentation snapshot
    -> Python direct-cell ASCILINE compositor
    -> adaptive codec and shared WebSocket stream
    -> atomic browser canvas presentation
```

Python owns every box after ingress. Rust is not a WizardJoe dependency, sidecar, renderer, clock, server, test gate, or release artifact. Prism's separate Rust process may eventually emit sanitized envelopes, but WizardJoe consumes them as optional visual advice through Python.

## 3. Contract decisions

1. The accepted character is winged. Flying is a production locomotion family.
2. The 39 generated pose IDs and library hash are the asset baseline.
3. Pose PNGs are build inputs only. Runtime frames remain procedural cell compositions.
4. Simulation uses integer ticks at exactly 60 Hz. Rendering defaults to 24 FPS and never advances simulation itself.
5. User control has priority over demos and external semantic animation signals.
6. Ground contact, altitude, flight phase, clip phase, transition progress, and channel ownership are explicit state.
7. Whole-character coordinate-hash dissolves are not a production transition technique.
8. Transition recipes use authored pose holds, breakdown poses, contact/phase matching, and small integer secondary offsets.
9. Prism data is content-free, versioned, sequenced, expiring, and fail-closed.
10. Existing HTTP routes remain valid through compatibility adapters.

## 4. Frozen interfaces

### 4.1 Command envelope

`CommandEnvelopeV1` contains:

- `schema_version`, fixed to `1`;
- `command_id`, client-generated idempotency key;
- `source_id`, stable controller identity;
- `source_sequence`, strictly increasing per source and epoch;
- `source_epoch`, changes after reconnect/reset;
- `issued_tick` or null;
- `kind`;
- validated `payload`;
- optional `lease_id`;
- optional `duration_ticks`;
- `priority_class`: `user`, `system`, `demo`, or `visual_signal`.

The runtime returns `CommandAckV1` with accepted/rejected/duplicate/stale status, authoritative tick, state revision, lease state, and a stable error code.

### 4.2 Continuous control intent

`ControlIntentV1` contains normalized `move_x`, `move_z`, `speed`, `run`, `flight`, `ascend`, `descend`, optional facing aim, buttons/actions, lease ID, sequence, and a short TTL. Release, blur, disconnect, visibility loss, and TTL expiry all neutralize the intent.

### 4.3 Runtime state regions

- `GroundRegion`: idle/start/walk/run/turn/stop/land and gait phase/contact.
- `FlightRegion`: grounded/takeoff/hover/flap/glide/bank/landing, altitude, vertical velocity, wing phase.
- `ActionRegion`: none/anticipation/commit/hold/recovery with interrupt window.
- `FaceRegion`: expression, blink, eye aim, mouth owner.
- `PropRegion`: staff mode, hand owner, attachment anchor.
- `EffectRegion`: effect ID, phase, TTL, coverage budget.
- `PresentationState`: clip, sample, transition, roots, contacts, channel writers, interpolation alpha.

### 4.4 Animation graph v2

The versioned JSON graph contains:

- complete metadata for all 39 poses;
- clip definitions with ordered samples and integer durations;
- markers such as contact, toe-off, takeoff commit, apex, wing beat, impact, release, and recovery;
- legal successor edges, interrupt policy, fallback clip, phase carry, and contact requirements;
- transition recipes with source/target compatibility, optional breakdowns, duration, root policy, wing/staff policy, and effect timing;
- capability tiers that expose directional limitations honestly rather than fabricating mirrored anatomy.

### 4.5 Prism visual signal envelope

`PrismAnimationSignalV1` contains only:

- `schema_version`, `event_id`, `source_epoch`, `source_sequence`, `emitted_at_ms`, `ttl_ms`;
- `kind`: stage, terminal posture, persona style, recall summary, retrieval summary, approval posture, continuity, topic shift, or health;
- bounded numeric posture fields and enums;
- `classification: visual_advisory_only`;
- provenance class and sanitization version.

It must not contain prompt/reply text, retrieved text, memory bodies, embeddings, source or user IDs, rationales, approval payloads, model/provider names, routes, paths, hashes, secrets, or authority claims.

## 5. Motion vocabulary

### Ground

- idle front/back/profile/diagonal families;
- start, walk contacts, passing pose, run drive/reach, turn, stop, crouch, recovery;
- distance-driven phase with phase carry between walk and run;
- planted-foot drift at most one local cell during contact windows.

### Flight

- takeoff anticipation, commit, lift, hover neutral, wing up/down, knee-up accent;
- glide and bank families with explicit facing capability;
- landing anticipation, root descent, first contact, crouch absorption, recovery;
- no foot-contact claims while airborne; shadow scale/offset reflects altitude.

### Actions

- explain, point, think, shush, magic cast/thrust, staff guards/block/spin, reaction, celebration, victory;
- anticipation/action/hold/recovery timing with interruption rules;
- speech, mouth, expression, blink, and eye aim remain independent when compatible;
- staff and hand are single-writer channels with attachment checks.

## 6. Prism-to-animation mapping

Existing safe signals map to bounded intent, never direct pose or movement:

| Signal | Animation intent | Constraint |
|---|---|---|
| queued/understanding | attentive idle/listen | no displacement |
| drafting | prepare to speak | user locomotion continues |
| checking safety/auditing | restrained review | motion amplitude decreases |
| deciding/reviewing | measured thinking | no authority implication |
| ready | settle/friendly | short, low-amplitude |
| needs clarification | one questioning gesture | no frustration |
| waiting approval | planted waiting posture | cannot approve or execute |
| memory relevance/recall summary | generic recollection cue | only sanitized producer summary |
| retrieval summary | reference gesture | no source/content display |
| topic shift | brief reset/reorientation | no world target change |
| degraded health | degraded neutral idle | suppress flourish |
| persona style | timing/amplitude profile | cannot replace Wizard identity |

Priority order is safety/governance clamps, user locomotion, explicit user action, speech lifecycle, Prism visual posture, deterministic idle variation.

## 7. Work packages

### Contract checkpoint

- `CAP-000`: ratify winged/flying Python contract.
- `CAP-001`: record clean staging allowlist and baseline hashes.
- `CAP-010`: save six research reports, four planning reports, this plan, and workflow.
- `CAP-011`: commit and push planning checkpoint before code work.

### Runtime contracts

- `CAP-100`: typed command, ack, control-intent, runtime-state, and presentation interfaces.
- `CAP-110`: metadata-complete loader and deterministic 39-pose census.
- `CAP-120`: graph-v2 schema, taxonomy, clips, transitions, and strict validator.
- `CAP-130`: scope/ownership/Rust-exclusion validator.

### Parallel implementation

- `CAP-200`: integer fixed-tick clock, accumulator, bounded catch-up, immutable snapshots.
- `CAP-210`: ordered command inbox, deduplication, acks, replay log, state hashes.
- `CAP-220`: lease and priority arbiter for continuous control.
- `CAP-230`: ground/run/flight semantic physics.
- `CAP-300`: graph evaluator, samples, markers, exactly-once events.
- `CAP-310`: complete clip inventory and legal topology.
- `CAP-320`: authored transitions and interruption from the actual presented snapshot.
- `CAP-330`: face, speech, wing, robe, hat, beard, staff, and effect channels.
- `CAP-400`: backwards-compatible HTTP/WebSocket adapters.
- `CAP-410`: hub cadence, epochs, metrics, bounded fanout, resync.
- `CAP-420`: browser keyboard/gamepad continuous-input lifecycle.
- `CAP-440`: strict optional Prism signal schema, parser, TTL/order/dedup diagnostics.
- `CAP-450`: content-free signal-to-animation-intent mapper and arbitration tests.
- `CAP-500`: Python-only CI and compact evidence tooling.

### Serial promotion

- `CAP-600`: wire runtime, graph, transport, and signal adapter behind compatibility switches.
- `CAP-610`: promote idle/start/walk/run/turn/stop.
- `CAP-620`: promote takeoff/hover/flap/glide/bank/land.
- `CAP-630`: promote actions, reactions, speech, expressions, staff, and effects.
- `CAP-640`: promote continuous keyboard/gamepad/HTTP/WebSocket control.
- `CAP-650`: promote optional Prism visual-signal input with disconnect fallback.

### Verification and release

- `CAP-700`: deterministic replay and full Python suite.
- `CAP-710`: real Chromium visual and control matrix on port 8765.
- `CAP-720`: mixed-control, reconnect, slow-subscriber, and signal-staleness soak.
- `CAP-800`: compact evidence manifest and completion report.
- `CAP-810`: clean-clone verification, final commit/push, and live restart.

## 8. Acceptance gates

- Same seed, graph, command log, and pose library produce identical state and frame hashes.
- Exactly 60 simulation ticks per simulated second; no fractional step.
- Renderer cadence changes do not alter state hashes.
- User input latency is below 100 ms locally at p95.
- Key/gamepad release, blur, disconnect, and TTL expiry stop input within two simulation ticks plus transport latency.
- Every production pose is reachable from a clip or documented showcase-only fallback.
- No illegal graph edge, dead end, unknown pose, duplicate channel writer, or production hash dissolve.
- Ground contact drift is at most one local cell; root discontinuity is at most two cells except authored airborne arcs.
- Staff remains attached; eyes, mouth, face, wings, hat, beard, and robe remain coherent.
- Airborne states never claim planted feet; landing contact fires exactly once.
- Remote locomotion continues through compatible speech, expression, and Prism posture signals.
- Prism unavailable, malformed, stale, reordered, private, or unsupported events have no unsafe visual effect.
- ASCILINE source, decoded, and presented frame hashes agree; medium mode sustains 24 FPS.
- Full Python tests, strict animation matrix, browser console, reconnect/resync, and 10-minute soak pass.

## 9. Rollback

Every family promotion has a compatibility switch. On failure, disable only the failing family, preserve the fixed runtime and validated graph, restore the last verified family checkpoint, record the exact failed frame/tick/command, and continue no further promotion until its gate passes.
