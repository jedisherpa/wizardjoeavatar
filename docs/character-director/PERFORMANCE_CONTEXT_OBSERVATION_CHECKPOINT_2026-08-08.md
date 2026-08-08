# Performance Context Observation Checkpoint

Date: 2026-08-08
Branch: `codex/character-director`
Status: implemented locally; focused verification passed; broader Character Director work remains open

## Purpose

This checkpoint removes unobserved claims from the immutable performance context used by live speech and directed performances. It does not change the private-content boundary or grant new authority.

## Corrected Claims

Before this checkpoint, every captured context reported all of the following even when the runtime had not observed them:

- Prism pipeline `ready/completed`.
- Direct viewer gaze.
- Session memory scope.
- Current-surface notification scope.
- Ready voice alignment before the governed registration supplied alignment.

The runtime now:

- Accepts pipeline stage and status only from a fresh Prism V2 advisory correlated to the same turn and compatible utterance.
- Ignores expired, legacy, wrong-turn, and wrong-utterance advisories for context capture.
- Uses active speech playback as the only local fallback proof of a `speaking/active` stage.
- Reports `none/none` when neither Prism nor playback proves a stage.
- Reports the controller's actual gaze authority as `automatic`, `direct_viewer`, `left`, `right`, `up`, or `down`.
- Reports the currently visible authoritative permission-world state when one exists; otherwise it retains the compositing default.
- Uses fail-closed `none` values for memory and notifications until a permission authority supplies an exact compatible observation.
- Reports speech alignment as `pending` during preliminary context capture. The later governed registration remains the alignment authority.

The presentation approval binding is intentionally unchanged in this checkpoint because it participates in the existing two-pass governed approval and score-publication protocol. Reworking that binding requires a separately versioned contract and migration proof.

## Verification

Focused director, live-speech, and score-edit suites:

- 21 tests passed.

Broader context, governed release, Prism advisory, control, and permission-world suites:

- 90 tests passed.

Final merged runtime, connector, choreography, governance, release-gate, score-runtime, and frame-hub suite:

- 200 tests passed.

New regression coverage proves:

- A matching Prism stage is captured.
- A different turn is ignored.
- An advisory that expires before the next simulation tick is ignored.
- Automatic and explicit controller gaze are reported without fabricated eye contact.
- Unproven memory and notification scopes remain absent.

## Multi-Agent Audit Delta

The same current-code audit identified the next two P1 implementation items:

1. Score repository publication previously occurred while the frame-hub writer lock was held. This checkpoint batch adds a bounded single-writer score-authoring lane, publishes outside the runtime lock, revalidates authority before returning a binding, and exposes sanitized queue diagnostics. Saturation fails with a retryable `503` response.
2. Ordinary live speech previously routed through a generic `speaks -> body.explain` path. This checkpoint batch now resolves the character dictionary's exact `speak` binding, rejects speech-incompatible capabilities, and includes the choreography policy identity in replayable score artifacts.

The connector audit also confirmed that unit contracts are strong but the repository still lacks one current real-process receipt proving main-media playback, governed-speech preemption, restored advanced main playback, runtime restart, reconnect, and stale-session rejection in one run.

## Remaining Gates

- Run installed audiovisual acceptance for the bounded score-authoring and dictionary-bound live-speech paths.
- Produce the connected lifecycle/reconnect acceptance receipt.
- Complete installed audiovisual and long-duration production proof.
- Preserve per-character admission and human visual approval gates; Kingfisher remains excluded from runtime admission until explicitly approved.
