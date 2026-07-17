# Context and Performance Compiler Architect Report

## Verdict

Implement a typed authoring compiler that terminates in the existing runtime:

```text
semantic intent
  -> PerformancePlanV1
  -> capability binding
  -> CompiledPerformanceScoreV2
  -> contract and semantic validation
  -> CompiledScoreLoader
  -> PerformanceScheduler
  -> PerformanceApplication
  -> WizardAvatarController
```

Live keyboard/gamepad/remote control remains in command validation, leases,
channel arbitration, and phrase execution. It is not misrepresented as a media
score.

## Existing Authority

- `performance_compiler.py` produces portable `PerformanceScoreV1`.
- `compiled_performance_score_v1.schema.json` anticipates character binding but
  lacks several execution values the scheduler reads.
- `CompiledScoreLoader`, `PerformanceScheduler.evaluate`, and
  `PerformanceApplication.apply` are the production path to preserve.
- Shadow acting/control/phrase modules are post-baseline, diagnostics-only, and
  must remain parity instrumentation until independently admitted.
- Capability truth is split between the coarse character package and the richer
  animation graph.

## Proposed Contracts

`PerformanceContextV1` is immutable, canonical-JSON-compatible, content
addressed, versioned, and digest-bound to character package, pose library,
animation graph, phrase catalog, compiler/policy, media/score identity,
accessibility variants, and evidence references. It must not contain caller-
asserted authority, raw pixels, controller objects, URLs, or hidden drafts.

`PerformancePlanV1` is an internal typed IR containing source cue, intent,
timing, channel requests, ranked candidates, phase schedule, continuity
requirements, and deterministic decision key.

`CapabilitySnapshotV1` derives only from validated package, graph, pose library,
and admitted phrase catalog. It exposes roles, channels, support/contact,
facings, legal successors, interrupt policy, overlays, accessibility variants,
and quality status.

## Compiler Layers

1. Preserve semantic intent and fallbacks.
2. Rank plans without choosing runtime IDs.
3. Intersect plans with the digest-bound capability snapshot.
4. Materialize character-bound tracks, checkpoints, mappings, nodes, fallbacks,
   and per-cue hashes.
5. Validate schema, references, transitions, channels, accessibility, and
   deterministic replay before acceptance.

Cache by portable score hash, context hash, and compiler version. Runtime
playback must add no planner work to the frame loop.

## Risks

- Compiled V1 does not type all scheduler execution fields.
- Scheduler, shadow resolver, and a new compiler could diverge.
- Phase, interrupt, and channel vocabularies already differ.
- Package metadata lacks semantic mappings and detailed capabilities.
- Stateful phrase execution during scored media would break cold-seek equality.
- Current semantic validation does not reject missing mappings, illegal clips,
  diagnostic-only poses, or bad package bindings.

## Rejected Alternatives

- A second context runtime.
- Modifying V1 schemas in place.
- Runtime clip choice in `stream.py` or by a model.
- Treating remote packets as scores.
- Caller-provided capability or authority claims.
- Stateful scored-media progression instead of media-time-pure evaluation.
- Another independent ownership policy.

## Verification

Strict schema/canonicalization tests, byte-identical repeated compilation,
digest sensitivity, fallback completeness, diagnostic-pose rejection,
vocabulary parity, ownership parity, cold-seek/reconnect equivalence, contact
and recovery simulation, and authority-injection tests are required. The
specialist's focused current set passed 81 tests.
