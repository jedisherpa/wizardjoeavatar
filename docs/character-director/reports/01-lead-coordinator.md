# Lead Coordinator Report

## Evidence Scope

- Python worktree and history through `293a2d8`.
- Prism connector baseline `189fbab`, corrective successor `5910601`, and the
  preserved dirty connector worktree at `bf229c2`.
- Canonical local connector documentation.
- Existing media session, scheduler, application, frame hub, score schemas,
  Prism governed-turn, TTS, and connector code.

## Finding

Character Director should be the single deterministic authority for
conversational performance inside the existing Python runtime. Prism remains
authoritative for governed turn state, approved language, speech production,
and audible timing. The existing connector is extended compatibly, not
replaced.

## Integration Boundary

`WizardFrameHub` already owns one fixed-tick semantic loop and bounded server
subscriber queues. Character Director must sit before `PerformanceApplication`
and feed the existing score scheduler/application/controller path. It must not
create another frame loop, socket family, or animation authority.

The existing Media Session V1 contract carries content-free playback state and
score selection. It does not carry turn identity, pipeline stage, response
approval, permissions, interruption, or approved-content identity. Those belong
in a new versioned governed direction/context message family using the same
authenticated relay and acknowledgement pattern.

## Dependency Graph

```text
healthy repositories and preserved dirty evidence
  -> provenance ledger and connector matrix
  -> authority/schema/clock/governance/lifecycle freeze
      -> capability manifest
      -> governed PerformanceContext projection
      -> turn and interruption identity
      -> authoritative speech timing
          -> deterministic conversational compiler
          -> Character Director runtime integration
          -> diagnostics and observability
              -> cross-language, governance, visual, package, and soak gates
```

## Primary Risks

1. Dirty worktrees contain valid but unaudited later work.
2. The original Prism worktree has unreliable Git objects.
3. Media Session V1 cannot express governed conversational direction.
4. Estimated text reveal can drift from audible speech and animation.
5. End-to-end cancellation and stale-turn rejection are missing.
6. Shadow direction and media scheduling could become competing authorities.
7. Cross-language contracts can drift without shared golden fixtures.
8. Current connector documentation presents compatibility lifecycle as normal
   packaged lifecycle.

## Rejected Alternatives

- A second connector, second performance runtime, or Rust Character Director.
- Raw drafts, transcripts, or evaluator text in Media Session V1.
- Treating uncommitted shadow modules as already authoritative.
- Frame-by-frame model calls.
- Importing unrelated RobbinPrism history wholesale.

## Synthesis Protocol

Freeze independent reports, normalize evidence into authority, schema, clock,
governance, and queue/lifecycle registers, allow one conflict-only response from
affected specialists, and resolve decisions in this order: governance,
deterministic authority, backward compatibility, runtime safety, performance
quality, tooling convenience.

## Verification Requirement

Phase 1 cannot begin until both repositories are healthy and isolated, dirty
work is preserved, connector lifecycle is reconciled, contract ownership is
frozen, and cross-language fixtures are approved.
