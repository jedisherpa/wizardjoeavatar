# Character Director Visual Performance Acceptance

Date: 2026-07-17  
Branch: `codex/character-director`  
Status: active implementation and verification contract

## Purpose

This document turns the Character Director visual review into a repeatable,
attributable release gate. Automated checks establish timing, containment,
continuity, and provenance. Human director review establishes intent, weight,
appeal, clarity, and whether repetition feels mechanical.

The Python visualizer remains the production renderer. Rust evidence tools may
inform record formats and analysis, but they are not the rendered output or a
replacement runtime.

## Current Finding

The animation graph already declares clips, contacts, markers, channel
ownership, interrupt policies, and transition recipes. The current presenter
does not yet execute all of that authored transition intent. In particular,
node changes restart target clips and complete pose rasters are presented as
atomic snapshots. Existing retained evidence is therefore insufficient for
release acceptance:

- deterministic stills cannot establish motion quality;
- the prior connected recording sampled about 4.6 frames per second rather
  than the 24 FPS presentation stream;
- the prior recording has no audio and cannot prove lip-sync;
- state snapshots, commands, wire frames, and visible pixels were not captured
  on one attributable timeline.

## Evidence Truth Chain

Every accepted run must bind the following records to one immutable run ID and
candidate commit:

1. Ordered command envelope and authoritative applied acknowledgment.
2. State revision and state hash associated with the command result.
3. Original ASCILINE wire message bytes, sequence, codec tag, and SHA-256.
4. Decoded cell buffer, expected byte length, sequence continuity, and SHA-256.
5. Presented logical canvas pixels and SHA-256 from the real browser renderer.
6. Exact-frame video derived from decoded cells.
7. Real-browser recording proving layout, scaling, and presentation behavior.
8. Audio artifact and synchronization timeline for speech scenarios.
9. Contact sheets whose labels identify scenario, frame, tick, time, command,
   state hash, and frame hash.
10. Independent review records bound to the run manifest SHA-256.

Capture and review facts are separate. A reviewer may score an immutable run,
but must not rewrite its capture manifest.

## Fail-Closed Capture Rules

- Never contact, restart, replace, or terminate port `8765` from the harness.
- Launch only a harness-owned child runtime on an isolated loopback port.
- Use one ASCILINE subscriber and the ordered HTTP command endpoint.
- Maintain one source ID and source epoch, strictly increasing source sequence,
  unique command IDs, and at most one outstanding command.
- Use bounded queues. Queue overflow terminates and invalidates the run.
- A missing frame index invalidates lossless evidence. A later keyframe may
  restore viewing, but it cannot make the run lossless retroactively.
- Enforce decoded length equal to `cols * rows * 4`.
- Never treat operational metrics or a separately fetched state response as an
  atomic frame/state pair.
- Never silently retry an indeterminate timed-out command under a new ID.
- Any unexplained drop, decoder error, console error, provenance mismatch,
  checksum mismatch, redaction leak, or truncated replay fails the run.

## Scored Rubric

Score each category from 0 to 4. A score of 4 is release quality, 3 is
acceptable with minor notes, 2 is repeatedly distracting, 1 is substantially
broken, and 0 is absent or unsafe. Weighted score is `weight * score / 4`.

| Category | Weight | Automatic checks | Director judgment |
| --- | ---: | --- | --- |
| Gaze and head-eye coordination | 12 | Eye pixels stay in the aperture; response within two presented frames; eyes lead head by 1-4 frames on turns over 45 degrees | Target is readable; clean settle; no darting or dead stare |
| Blink | 8 | Closure 100-200 ms; intervals 2.5-6.5 s; at least three interval lengths in 60 s; no root/body change | Natural rhythm around thought and gaze; no metronomic quality |
| Hand acting | 14 | Prepare at least 3 frames; stroke 1-4; hold at least 3; recovery at least 3; ordered markers; hand/staff discontinuity at most 2 cells | Intent, arc, silhouette, grip, spacing, and settle feel authored |
| Locomotion | 18 | Response within two ticks; planted drift at most 1 output cell; alternating contacts; facing change at most one sector/tick; target error at most 0.08 | Weight, cadence, starts, stops, turns, reversals, robe and staff follow-through |
| Stillness | 10 | Body/prop pixels stable, excluding face, for at least 70% of ordinary speech; conclusion hold at least 2 s | Stillness reads as listening or thought, not frozen playback |
| Interruption | 10 | Interrupt window honored; no stale stroke/effect replay; root jump at most 1 cell; recovery within 12 frames | No idle snap, pose pop, unfinished thought, or emotional discontinuity |
| Reduced motion | 8 | Zero stage/root travel; no dynamic effects or large-pose cycling; mouth and face remain functional | Meaning remains clear and genuinely calm |
| Framing | 10 | No silhouette crop; at least 4-cell top/side and 6-cell bottom margins; fixed aspect; no UI overlap | Character remains readable, grounded, and balanced |
| Repetition | 10 | No non-locomotion gesture more than twice consecutively; one principal stroke per thought group; no exact body loop under 8 s in a 60 s scene | Performance stays purposeful and avoids mechanical alternation |

Release requires all of the following:

- weighted score at least 85/100;
- every category at least 3;
- two independent reviewers;
- median review score at least 4;
- no truthfulness, accessibility, contact, synchronization, or provenance
  blocker;
- no hard failure.

Hard failures are clipping, anatomy break, planted drift above one cell for two
frames, stale post-interruption action, moving reduced-motion scenery/body, or
missing review evidence.

## Required Scenario Matrix

| ID | Scenario | Required measurements | Director focus |
| --- | --- | --- | --- |
| V1 | 12 s listening: viewer, left target, viewer, then 90-degree head turn; include two blinks | Gaze latency/order, eye bounds, blink duration/interval, root stability | Fixation, eye lead, settle, listening presence |
| V2 | 20 s governed speech with gaze returns and a blink during speech | Mouth/blink independence, body-still percentage, AV timing | Face coordination; no stare or blink punctuation |
| V3 | Canonical `cast_front` three times with 2 s between casts | Phase/marker order, phase duration, hand/staff/root anchors | Prepare, stroke, hold, recovery, grip, arc |
| V4 | Explain, hold, then point across three thought groups | Stroke count, holds, recovery, repeated-action sequence | Gesture motivation, accents, silhouette, restraint |
| V5 | Front walk: idle, three full cycles, decelerated stop | Start latency, contact alternation, planted drift, target error | Weight transfer, cadence, stop settle |
| V6 | Walk with 90-degree turn, 180-degree turn, reversal, stop | Facing steps, phase continuity, contact/root continuity | Anticipation, readable direction, no skating |
| V7 | Interrupt cast before commit and after commit with a new speech turn | Interrupt compliance, stale effect, recovery time, root jump | Recovery logic and emotional continuity |
| V8 | 60 s speech/listening with three repeated phrases | Stillness ratio, gesture frequency, exact-loop detection, blink variation | Purposefulness, holds, repetition fatigue |
| V9 | Replay V3-V5 excerpt in full, reduced, and still modes | Root/effect/body suppression; face/mouth preservation | Accessibility retains intent without agitation |
| V10 | Near/far/edge pass at desktop DPR1/DPR2 and 390x844 DPR3 | Avatar-only bounds, letterbox aspect, overlap, crisp pixels | Scale, grounding, portrait balance, readability |

Each scenario requires a connected 24 FPS capture, a frame-indexed trace, normal
speed review, quarter-speed review, and a labeled contact sheet.

## Runtime Safety Notes

The current frame hub is event-loop owned. Evidence code must not call hub or
frame-source mutation methods from another loop or thread. The production
subscriber queue favors liveness: on overflow it can replace queued deltas with
a fresh keyframe. External evidence must detect frame-index gaps and invalidate
lossless claims. Future in-process lossless capture, if added, must permit only
one subscriber, use immutable published-frame records, and terminate on
overflow without blocking the frame loop.

PNG encoding, hashing beyond the publication contract, FFmpeg writes, contact
sheet generation, and filesystem work must stay off the frame-publication
critical path.

## Completion Record

This document is the acceptance contract, not proof that the criteria passed.
The final evidence package must include candidate commit, environment,
commands, checksums, machine results, reviewer identities, correction records,
and the aggregate release decision.
