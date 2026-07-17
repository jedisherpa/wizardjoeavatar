# Permission and Governance Review

## Scope Note

The specialist traced the later RobbinPrism governance implementation as the
available concrete Prism governance surface and compared it with Wizard Joe's
live compatibility server and media connector. Findings affecting the canonical
connector clone must be revalidated there before porting code.

## Critical Findings

1. A failed guardrail rewrite can leave the original model response visible and
   speakable even when it is flagged or clarification is required.
2. Prism TTS endpoints authorize the caller but do not require a governed
   response ID, approved content hash, sink eligibility, or approval receipt.
3. The live `8765` compatibility profile leaves direct state, speech, animation,
   and WebSocket commands unauthenticated; only media endpoints are bearer-
   protected.
4. Material execution can proceed when audit-ledger recording fails because a
   caller-created boolean is trusted instead of a verified receipt.
5. Generic approval covers only registered skills, while several material
   direct handlers rely solely on possession of the local session token.
6. Approval payload binding is optional at resolution.
7. Runtime status can overstate readiness by conflating conversational posture
   with material permission.

## Authoritative Permission Signals

- Server-held pending action and exact payload hash.
- Human sovereign authority created at approval resolution.
- Registered skill contract and live tool health.
- Persisted memory enabled state and scope.
- Prism session-token possession for transport authentication only.
- Wizard app/media bearer possession for their distinct transport scopes.
- Connector freshness, sequence, schema, and verified ledger health.

CDISS metrics, recalled memory, persona overlays, route hints, visual posture,
animation intent, source priority, and performance metadata are advisory. They
must never grant authority.

## Required Contract

Introduce a backend-issued, single-use `GovernedContentEnvelope` binding content
hash, sink eligibility (`text`, `speech`, `animation`), policy verdict,
approval class, expiry, and verified ledger receipt. Every visible or audible
sink verifies it. Guardrail/rewrite failure emits a fixed safe response, never
the original candidate.

Material execution requires a successful ledger receipt. Approval requires
pending ID, exact payload hash, nonce, single use, and expiry. Permission-world
visuals consume a sanitized, non-authoritative projection of real grants.

## Rejected Alternatives

- Prompt-only safety.
- Loopback or session-token possession as content approval.
- Caller-supplied `approved: true`.
- Visual approval state as execution authority.
- Reusing the content-free media connector for transcripts or commands.
- Executing during ledger degradation and repairing the audit trail later.

## Adversarial Verification

Force rewrite failure and prove the candidate is absent from HTTP, history,
memory, and TTS. Reject arbitrary TTS without a governed envelope. Fail ledger
append and prove no skill runs. Reject missing/mismatched/replayed approval
hashes. Require authentication on every deployed Wizard mutation and WebSocket
command. Prove app/media bearers are non-interchangeable. Reject text,
authority, commands, and world targets in content-free Prism signals.

The specialist observed 48 focused Wizard, 33 CDISS, and 13 Prism approval tests
passing. Prism runtime conclusions were code-path verified, not live-endpoint
verified.
