# Specialist Signal Research: Prism GT Influence Integrated and CDISS

Role: `PRSM`
Date: 2026-07-13
Source repository: `/Users/paul/Documents/prism-geometry-talk`
Source branch: `prism-gt-influence-integrated`
Inspected source commit: `cf793dba1cb6644960c3dd9d2ca3d1e7872563d3`
Destination runtime: ASCILINE Python at `http://127.0.0.1:8765/`

## Executive conclusion

Prism GT already produces enough governed, typed state to make Wizard Joe feel responsive to a conversation without giving the animation system access to private content or runtime authority. The strongest existing animation inputs are:

1. the live `POST /api/chat/stream` stage events (`stageId`, lifecycle status, timing, expression, mouth, and energy);
2. the terminal reply's verdict, confidence, topic-shift flag, persona, and sanitized `CdissExpressionSnapshot`;
3. the sanitized CDISS product posture exposed by `GET /api/runtime/status` and `GET /api/thread/inspect`;
4. bounded summaries of recall, knowledge retrieval, route readiness, pending approval, provider health, thread continuity, and runtime health;
5. static persona temperament values that can tune style while remaining subordinate to CDISS and governance clamps.

The current Prism APIs are not yet a complete animation-signal contract. Stage and reply frames are suitable for direct consumption after validation, but many other useful values are pull-only diagnostics, internal Rust structs, or private data. Several particularly tempting inputs must never cross the animation boundary: raw embeddings, vector subspaces, prompts, memory bodies, retrieved knowledge text, route exemplars, watcher interpretations, approval payloads, provider keys, hidden reasoning, and governance rationale text.

The recommended integration is a **versioned, sanitized, visual-only signal envelope emitted by Prism and consumed by a Python adapter inside WizardJoeAvatar**. Rust remains the producer in the separate Prism application. It does not become part of the avatar runtime, bind port 8765, render frames, own simulation state, or issue remote-control commands. The Python adapter translates accepted envelopes into bounded animation intents such as `listen`, `think`, `speak`, `recall`, `clarify`, `wait_for_approval`, `celebrate_softly`, or `degraded_idle`. It cannot translate a semantic signal into arbitrary movement, file/tool execution, approval, or external action.

## Audit provenance and repository instructions

This report inspected the checked-out working tree, not the remote branch tip.

- Prism `HEAD` was `cf793dba1cb6644960c3dd9d2ca3d1e7872563d3` on `prism-gt-influence-integrated`.
- The Prism worktree was clean at inspection.
- The local branch reported itself 80 commits behind `origin/prism-gt-influence-integrated`. No fetch, checkout, pull, rebase, or source modification was performed. This report therefore describes the exact checked-out tree, not uninspected remote work.
- No `AGENTS.md` or `AGENTS.override.md` exists anywhere under the inspected Prism repository. The destination repository's `AGENTS.md` requires the ASCILINE Python architecture and direct frame generation; this report respects that boundary.
- No Prism production code was changed. This report is the only assigned output.

All source references below are relative to `/Users/paul/Documents/prism-geometry-talk` and include exact line spans from the inspected commit.

## Non-negotiable integration boundary

```text
Prism GT Rust/CDISS process
    -> sanitized, versioned, visual-only signal envelopes
    -> authenticated loopback or explicitly secured transport
    -> WizardJoeAvatar Python PrismSignalAdapter
    -> bounded semantic animation intents
    -> Python animation state machine and remote-control arbitration
    -> Python ASCILINE cell compositor and stream on port 8765
```

The adapter must enforce these rules:

- Prism signals are advisory animation context, never simulation authority.
- Remote-control input remains a separate user-controlled channel. Prism cannot synthesize movement vectors, world targets, takeoff, landing, or tool execution from conversation state.
- Approval-related signals may place the character in a waiting pose; they cannot approve, deny, or execute anything.
- Memory and knowledge signals may trigger a generic recollection or reference gesture; content, titles, snippets, source paths, and embeddings must not reach the avatar runtime.
- CDISS values shape expression only. The source itself states that continuity cannot grant approval (`crates/prism-cdiss-core/src/cdiss.rs:640-641`) and that expression choices do not grant authority, evidence, permission, source access, or readiness (`crates/prism-cdiss-cli/src/main.rs:1766-1778`).
- Serious, blocked, approval-required, invariant-violation, and degraded states reduce motion amplitude. They never produce panic, shame, aggression, or celebratory behavior.
- Unknown schema versions, unknown signal kinds, stale events, invalid ranges, sequence regressions, and disallowed classifications fail closed to neutral idle.

## Actual end-to-end signal path today

The web face calls the same governed loop as the CLI and Telegram connectors (`crates/prism-cdiss-cli/src/web.rs:1-18`). A web turn is serialized, run through the runtime, and emitted as SSE (`crates/prism-cdiss-cli/src/web.rs:4343-4368`). Inside `run_turn_request` the actual sequence is:

1. `reading you` is emitted before prompt embedding, topic observation, and state load (`crates/prism-cdiss-cli/src/main.rs:3211-3243`).
2. CDISS transitions are built from parser, memory, agreement, route-hint, persona, and prompt-projection signals (`crates/prism-cdiss-cli/src/main.rs:3010-3088`).
3. Governed recall is planned and selected before the second CDISS transition (`crates/prism-cdiss-cli/src/main.rs:3292-3321`).
4. Watcher interpretation and optional self-knowledge/news retrieval run (`crates/prism-cdiss-cli/src/main.rs:3323-3445`).
5. `drafting a reply` is emitted before the chat provider call (`crates/prism-cdiss-cli/src/main.rs:3456-3487`).
6. The optional guardrail judges and may rewrite the draft (`crates/prism-cdiss-cli/src/main.rs:3497-3538`).
7. `auditing` is emitted before Auditor (`crates/prism-cdiss-cli/src/main.rs:3540-3561`).
8. `deciding` is emitted before Synthesizer (`crates/prism-cdiss-cli/src/main.rs:3563-3582`).
9. Skill readiness and CDISS dispatch are resolved; material work may become pending approval or be blocked (`crates/prism-cdiss-cli/src/main.rs:3700-3795`).
10. The turn and state patch are persisted, with optional Torus compaction (`crates/prism-cdiss-cli/src/main.rs:3597-3645`).
11. The runtime returns terminal verdict, confidence, topic shift, expression snapshot, timing, recall count, and ledger health internally (`crates/prism-cdiss-cli/src/main.rs:3670-3697`). Only a subset reaches the web reply.

The SSE wrapper emits an active frame when each stage begins and a done frame when it ends. The final terminal stage is `ready`, `needs_clarification`, or `waiting_approval`, followed by `reply`; failures produce `error` (`crates/prism-cdiss-cli/src/web.rs:4371-4474`). The current frontend already parses these event types (`src/api/stream.js:13-55`) and maps stage and CDISS posture to visual modes (`src/lib/sse-cdiss.js:27-45`).

## Signal inventory: signals that truly cross a boundary today

### Turn-stream and expression signals

| Existing signal | Producer and exact source | Actual payload and type | Cadence / lifecycle | Confidence and provenance | Privacy / governance | Safe animation mapping |
|---|---|---|---|---|---|---|
| Turn stage | `stream_governed_turn` and `stage_event`, `crates/prism-cdiss-cli/src/web.rs:4371-4459`, `6025-6148` | SSE event `stage`; `type:string`, `stageId:string`, `stage:string`, `label:string`, `status:"active"|"done"`, `startedAt:number(ms)`, optional `durationMs:number`, optional `finishedAt:number`, `safeSummary:string`, `expression:string`, `mouth:number`, `energy:number`, `at_ms:number`, optional `missingDecision:string` | Multiple events per governed turn. Every nonterminal stage gets active then done; terminal stage is emitted done-only. SSE keepalive is enabled. | Deterministic metadata selected by server stage name. Timing is monotonic elapsed time from turn start. No probabilistic confidence field. | Intended sanitized UI contract. `missingDecision` contains user-facing clarification text and should be stripped before the avatar adapter. | Direct: `queued -> attentive_idle`; `understanding -> listen`; `drafting -> speak/compose`; `checking_safety -> constrained_review`; `reviewing -> decide`; terminal stages -> settle/clarify/wait. Clamp `mouth` and `energy` to configured ranges and treat them as style targets, not frame commands. |
| Terminal reply posture | `web_reply_payload`, `crates/prism-cdiss-cli/src/web.rs:5974-6018` | SSE/JSON `reply`; `type`, `reply`, `verdict:"action"|"chat"|"clarify"`, `confidence:f32`, `persona:string`, `lens:string|null`, `new_topic:bool`, `expression:CdissExpressionSnapshot`, `pendingApproval:object|null` | Once per successful governed turn. | `confidence` comes from Synthesizer (`crates/prism-cdiss-cli/src/main.rs:3670-3684`). Persona is active runtime state. `new_topic` comes from lexical cue or embedding drift. | `reply`, `lens`, and approval payload may contain user/private content and must not enter the animation adapter. Use only whitelisted fields. | `verdict` selects settle/clarify/action-ready posture; confidence may scale pose commitment modestly. `new_topic` permits a short reset/reorientation. Persona selects a style profile. Expression drives face/body style. Never animate reply text or lens content. |
| CDISS expression snapshot | `CdissExpressionPlan::snapshot`, `crates/prism-cdiss-cli/src/main.rs:1697-1712`, `1835-1863` | camelCase object: `disposition:string`, `clarity:f32`, `taskReadiness:f32`, `memoryRelevance:f32`, `governanceRisk:f32`, `authorityLevel:f32`, `urgency:f32`, `seriousMode:bool`, `allowPersonaHistory:bool`, `allowPersonaRenderer:bool`, `allowComedy:bool`, `reasons:string[]` | Once in terminal reply; also stored after each governed Telegram turn. | Derived from persisted CDISS product metrics and explicit thresholds. Scalar values are normalized to `[0,1]` by CDISS. | `reasons` expose internal policy language and must be dropped. `authorityLevel` must never be interpreted as avatar or execution authority. | Use scalars only through bounded curves: clarity -> steadiness; readiness -> commitment; memory relevance -> generic recollection cue; risk/serious -> reduced amplitude; urgency -> tempo cap; comedy boolean -> permits or suppresses playful idle. Do not animate authority level. |
| Telegram visual snapshot | `VisualState` and `/api/tg/state`, `crates/prism-cdiss-cli/src/telegram_miniapp.rs:57-73`, `294-336` | `ok`, `uid`, `updatedUnix`, `verdict`, `confidence`, `expression` | Poll-based latest-state snapshot after a governed Telegram turn; absent before first turn. | Same expression/verdict/confidence as the desktop visualizer. | UID is user-identifying and must not be forwarded. Endpoint is session-bound to the authenticated Telegram user. | If Telegram is an approved source, translate only verdict/confidence/expression and timestamp; never UID. Prefer the common Prism signal envelope rather than polling this surface directly. |

The current stage catalog and authored visual metadata are:

| Input stage | Emitted `stageId` | Expression | Mouth | Energy | Recommended Wizard intent |
|---|---:|---:|---:|---:|---|
| `queued` | `queued` | `focused` | 0.04 | 0.22 | neutral attentive hold |
| `reading you` | `understanding` | `focused` | 0.08 | 0.42 | listening / slight forward attention |
| `drafting a reply` | `drafting` | `friendly` | 0.22 | 0.72 | composition/speech preparation |
| `auditing` | `checking_safety` | `constrained` | 0.06 | 0.48 | restrained review pose |
| `deciding` | `reviewing` | `mythic` | 0.12 | 0.62 | measured decision gesture |
| `ready` | `ready` | `friendly` | 0.10 | 0.40 | settle and face user |
| terminal clarify | `needs_clarification` | `focused` | 0.08 | 0.40 | one bounded questioning gesture |
| terminal approval | `waiting_approval` | `constrained` | 0.06 | 0.40 | planted waiting pose; no action |
| unknown stage | `working` | `focused` | 0.10 | 0.40 | neutral thinking fallback |

Values are defined at `crates/prism-cdiss-cli/src/web.rs:6037-6111`. They are real authored values, not inferred recommendations.

### Sanitized read models and operational signals

| Existing signal surface | Producer and exact source | Actual payload and type | Cadence / lifecycle | Confidence and provenance | Privacy / governance | Safe animation mapping |
|---|---|---|---|---|---|---|
| Runtime health | `health`, `crates/prism-cdiss-cli/src/web.rs:458-466` | `ok:bool`, `service:string`, `runtime:string`, `publicWeb:bool` | Pull snapshot; cheap health probe. | Process-local constants, not a deep dependency check. | Public-safe but not proof that models, memory, or governance are healthy. | `ok=false` or transport loss -> neutral disconnected idle. Do not celebrate `ok=true`. |
| Runtime readiness | `readiness_payload`, `crates/prism-cdiss-cli/src/web.rs:468-501` | `ok`, service/runtime/publicWeb, checks for static assets, media root, library, and disk | Pull snapshot; operational readiness. | Direct filesystem/bundle/disk checks. | May expose readiness details; adapter should retain only aggregate status and stable reason code. | Degraded/failing -> low-energy safe idle or status badge. Do not map disk/media failures to emotion. |
| Sanitized runtime/CDISS status | `runtime_status`, `build_runtime_status`, `crates/prism-cdiss-cli/src/web.rs:3115-3314` | Persona IDs/names; constitution version; chat/gov provider, model and label; embedder provider; feature toggles; continuity booleans/timestamps; ledger failure count/audit health; CDISS disposition/status; clarity, readiness, memory relevance, risk, authority, urgency; approval posture; serious/comedy/memory/backstory gates; projection degraded | Pull snapshot; reflects latest persisted web-topic state between turns. Cold start reports no continuity. | CDISS product view is re-derived from durable `ThreadState`; metrics rounded to three decimals. Provider labels and toggles are direct runtime state. | Explicitly excludes raw vectors, prompts, deliberation, and turn content. Still drop model names, constitution details, and authority from body animation. | Excellent resync source after reconnect. Map posture scalars and booleans as above. `projectionDegraded` clamps motion; `auditHealthy=false` freezes celebratory/action gestures. Provider/model fields should be diagnostics only. |
| Persona catalog/current persona | `personas`, `set_persona`, `crates/prism-cdiss-cli/src/web.rs:5480-5513` | GET: `active:string`, `personas:[{id,name,tagline}]`; POST result: `ok`, `id`, `persona` | Pull catalog and explicit user-driven change; change serialized behind turn lock and persisted. | Loaded from local persona TOML. | Taglines are public character metadata. A persona change is user intent, but still not approval for external action. | Transition to persona style baseline over a minimum blend duration. Never hard-cut locomotion or world position. |
| Provider discovery | `local_providers`, `crates/prism-cdiss-cli/src/web.rs:175-197`, `2286-2307` | Preferred/selected provider/model labels plus per-provider availability, models, selected/preferred models, redacted error | Pull; performs concurrent provider discovery. | Live provider/model discovery. Errors may be transient. | Model lists and error strings are operational data; do not send to avatar. Public mode exposes this GET route. | Only aggregate `available/degraded/failed` may alter a non-diegetic status cue. Never change personality or movement based on vendor/model. |
| Provider test | `provider_test`, `crates/prism-cdiss-cli/src/web.rs:2228-2284` | `ok`, `provider`, `state`, `available`, `modelCount`, `message`, `checkedAt`, `lastVerified` | Explicit POST probe. | Live model-list/health check; successful checks persist `lastVerified`. | Same-origin/session-token protected in private mode; provider and message are not animation inputs. | Optional one-shot neutral success/failure indicator only. No character emotion. |
| Setup posture | `build_setup_status`, `crates/prism-cdiss-cli/src/web.rs:2854-2967` | Redacted chat/gov/embedder/voice/STT/memory/X/updater readiness, provider key presence/storage/verification, warnings and next action | Pull; private loopback read model. | Runtime configuration and key presence, not secret values. | Intentionally redacted, but still operational/security posture. | Use only aggregate ready/degraded. Never animate key presence, usernames, warnings, or provider identity. |
| Skill/route readiness | `build_skill_status`, `crates/prism-cdiss-cli/src/web.rs:3317-3470` | Per skill: `routeId`, `displayName`, risk/write/approval/authority classes, provider/model, `status:ready|needs_approval|unavailable|dev_only`, reason, null `lastTest` | Pull snapshot; policy + contract + tool-health join. | Deterministic projection from skill registry, constitution policy, and current X tool health. It does not execute readiness against live turn context. | Matcher exemplars and schemas are deliberately excluded. Route IDs can still reveal capability; adapter should reduce them to an allowlisted animation category. | A sanitized route category may select a preparatory gesture (`search`, `create`, `speak`, `publish_wait`). Status controls whether that gesture may begin. Never imply a route executed merely because it is ready. |
| Memory health | `build_memory_status`, `crates/prism-cdiss-cli/src/web.rs:3652-3733` | `enabled`, status, redacted DB basename, record counts, active persona, embedder provider/dimension/chain, degraded, last write/recall/error | Pull snapshot. `lastRecallTime` is explicitly always null in this revision. | Counts and runtime memory object state; degradation inferred from embedder/projection posture. | Do not forward DB name, provider chain, counts per persona, or errors unless reduced to generic posture. | `enabled && !degraded` permits generic recall animation when a turn says recall was selected. Health alone must not trigger recall. |
| Memory recent | `build_memory_recent`, `crates/prism-cdiss-cli/src/web.rs:3687-3705` | `count` and items with kind/persona/source/timestamp/sanitized snippet | Pull; recent stored atoms. | SQLite memory rows; snippets credential-redacted and truncated. | Still private user continuity. **Must not be consumed by animation.** | No animation input. Use only a separate sanitized recall-summary event. |
| Governed recall probe | `build_memory_test`, `memory_test`, `crates/prism-cdiss-cli/src/web.rs:3746-3835` | Query, embedder/degraded, candidate/selected counts, authority invariant, selected records with id/kind/score/source/snippet | Explicit privileged POST diagnostic. | Same governed CDISS recall service used by turns. Scores are actual retrieval relevance. | Query, IDs, sources, snippets, and scores are private and can leak topic/content. | Do not consume this endpoint directly. A producer-side reducer may emit only `selectedCount`, broad kind set, degraded flag, and short TTL. |
| Knowledge-base status | `KbStatus`, `crates/prism-cdiss-cli/src/knowledge_base.rs:422-438`; handler `web.rs:3485-3487` | Schema and document/chunk/embedding/news/relationship/persona counts plus access policy and domains | Pull snapshot. | Direct KB SQLite counts. | Operational/catalog data. | Aggregate availability may permit a reference gesture; counts/domains must not drive motion. |
| Knowledge retrieval report | `KbQueryReport` / `KbSearchResult`, `crates/prism-cdiss-cli/src/knowledge_base.rs:183-232`; retrieval `1720-1797`; handler `web.rs:3541-3562` | Query/mode/count/vector availability/match policy/results with source pointers, access/authority, scores/ranks, and chunk text | Explicit POST query. Retrieval uses access/authority/domain gates, vector + FTS, reciprocal-rank fusion, authority boost, and optional persona focus. | Scores and ranks are real retrieval outputs; vector availability states whether semantic search participated. | Query, chunk text, source pointers, titles, and ranking are private/source-sensitive. **Do not send to avatar.** | Producer-side summary only: `retrievalOccurred`, result-count bucket, vector-degraded, and authority class bucket. Generic `consult_reference` gesture; never reenact content. |
| Thread inspector | `build_thread_inspect`, `crates/prism-cdiss-cli/src/web.rs:3839-4018`; handler `4025-4059` | Summary revision/mode/perspective/project/topic/domain state, timestamps, governance hash prefix, turn/token counts; approvals; memory counts; sanitized CDISS product; last route hint; artifacts; ledger status | Pull snapshot, default redacted; current web topic only. | Durable `ThreadState`, live approval card, product-view projection, and signed ledger status. | `redacted=false` reveals user-facing text, facts, targets and paths; raw vectors/prompts/deliberation remain excluded. Adapter must always use a narrower producer-side projection, never the revealed form. | Safe subset: revision, current mode, active-domain count, continuity present, pending approval count, artifact lifecycle counts, ledger valid. Use for resync and subtle persistence/return cues only. |
| Ledger timeline | `build_ledger_events`, `crates/prism-cdiss-cli/src/web.rs:4062-4125` | Newest-first event summaries: sequence, thread ID, type, timestamp, actor role, trace ID, approval decision, payload hash | Pull snapshot. | Signed ledger replay; payload bodies and signatures excluded. | Thread/trace/hash are correlators and must not reach animation. Event types may reveal actions. | Producer may reduce specific approval outcomes or lifecycle classes to one-shot visual acknowledgements. Never animate raw event type, actor, IDs, or hash. |
| Ledger verification | `build_ledger_verify`, `crates/prism-cdiss-cli/src/web.rs:4127-4149` | Aggregate verified flag/count and per-thread validity/error sequence/error | Pull snapshot. | Cryptographic chain verification results. | Errors and thread IDs remain diagnostic. | Invalid/unverified -> suppress action/celebration and enter neutral degraded posture. Valid status alone causes no performance. |
| Approval card/resolution | Card `crates/prism-cdiss-cli/src/web.rs:5951-5971`; resolution `5219-5294` | Card core: type, route ID, skill display, question, summary, risk level, payload hash, payload; X adds draft content. Resolution returns approved bool, route, message, display result/audit | Per material action; explicit user resolution. | Governed skill decision plus payload hash. | Contains private target/content and executable payload. **Never forward card body, hash, draft, display result, or audit payload.** | Reduce to `pending`, `approved`, `denied`, `stale`, or `failed` plus broad animation category. Pending -> wait; approved -> brief acknowledgement; denied -> neutral release, never shame. |
| Error SSE | `stream_governed_turn`, `crates/prism-cdiss-cli/src/web.rs:4461-4470` | `type:"error"`, raw `error:string`, `at_ms:number` | Terminal on turn failure. | Runtime error string. | Error text may contain sensitive operational details. | Drop text; emit classified `turn_failed` with low-energy neutral reset. Do not dramatize or retry actions automatically. |

### Important public/private route distinction

The router has two materially different surfaces (`crates/prism-cdiss-cli/src/web.rs:291-392`):

- Public-web mode exposes health, readiness, library, public session, chat/stream, voice, eager, persona, and provider discovery.
- Private loopback mode additionally exposes session token, approvals, model/key changes, setup/runtime/skills/KB/news/memory/thread/ledger/audit diagnostics, and update status. Mutating methods are guarded by a per-launch capability token.

The animation adapter must not assume diagnostics are available on a hosted Prism instance, and the solution must not broaden the public router to expose private read models. A dedicated animation stream should have its own minimized schema and scoped authentication.

## Signal inventory: real internal signals that do not currently form a safe API

These signals exist in the checked-out Rust code. They are not automatically safe merely because they are serializable.

| Internal signal | Producer and exact source | Internal fields / lifecycle | Confidence / provenance | Boundary decision and possible safe reduction |
|---|---|---|---|---|
| Full intent-state vector | `IntentStateVector`, `crates/prism-cdiss-core/src/cdiss.rs:238-350` | Six 16-dimensional subspaces (intent, topic, emotional, agreement, temporal, relational) plus authority, clarity, urgency, memory relevance, readiness, risk, completion. Normalized on transition. | Fused parser, memory, agreement, continuity, persona, and semantic projections. | Raw subspaces and completion state do not egress. Only the six existing product metrics may be emitted, rounded and clamped. Emotional vectors must not become inferred emotion animation. |
| Intent-state snapshot/transition | `IntentStateSnapshot` / `IntentStateTransition`, `crates/prism-cdiss-core/src/cdiss.rs:1401-1430` | Version, vectors, governance projection, projection metadata, oscillation, invariant violations, action signatures, timestamps; transition includes parser/memory/agreement signals, conflict penalty, and deltas. Per CDISS transition, currently up to twice per turn. | Direct CDISS engine output. | Emit only product status, bounded metrics, optional rounded deltas, oscillation/invariant booleans, and signal counts. Never emit violations, action signatures, evidence, claims, or vector material. |
| Parser signal | `ParserSignal`, `crates/prism-cdiss-core/src/cdiss.rs:180-190` | Label, confidence, strength, evidence, volatility, persistence class, required action. | Prompt parser and route hints. | Evidence/labels can reveal prompt intent. Reduce only to count and optional aggregate confidence bucket. Do not animate parser guesses directly. |
| Memory signal | `MemorySignal`, `crates/prism-cdiss-core/src/cdiss.rs:192-201`; constructed in `main.rs:2962-3049` | Label, relevance, timestamp, decay, source, 16-D projection. Includes recall, backstory, persona baseline, prompt semantic projection, recent turns, and task continuity. | Semantic embedder/projector, with fallback metadata. | Reduce to selected recall count/kinds and projection-degraded boolean after CDISS selection. Never emit labels, source, timestamps per record, or projection. |
| Agreement signal | `AgreementSignal`, `crates/prism-cdiss-core/src/cdiss.rs:203-214` | ID, claim, scope, confidence, active, authority-granted scalar, permissions, projection. | Governed agreement store and scope. | Never emit claim, permissions, IDs, or authority. At most emit `agreementContextPresent:bool` to stabilize style; it must not imply permission. |
| CDISS product status/metrics/action space | `CdissProductView`, `crates/prism-cdiss-core/src/cdiss.rs:569-638`; projection `1035-1123` | Status enum; headline/reason; allowed actions; gates; six metrics; deltas; signal counts/sources; projection meta; update time; authority invariant. Built after transition. | Deterministic safe projection of snapshot. | This is the right producer-side source. Emit status, metrics, safe action booleans, deltas, counts, fallback flag, timestamp, invariant constant. Drop reasons, gate rationales, source list, profile seed/dimension, and authority internals. |
| CDISS dispatch decision | `CdissDispatchDecision`, `crates/prism-cdiss-core/src/cdiss.rs:1126-1258`; set in `main.rs:3750-3775` | Subject surface/route/action/authority/material/write/prompt summary/hash; outcome; advisory flag; authority requirement; reasons. Per selected skill. | CDISS consultation against current snapshot. | Reduce outcome to `read_only_allowed|approval_required|clarification_required|blocked` and broad route animation category. Drop route ID unless allowlisted, all subject text/hash, reasons, and authority values. |
| Governed recall plan/decision | `CdissRecallQueryPlan`, `CdissRecallServiceOutput`, `CdissRecallDecision`, `crates/prism-cdiss-core/src/cdiss.rs:643-704`, `798-943` | Search permission, thresholds/top-k, candidates, selected records, kind, scores, serious mode, authority invariant. Per turn before drafting. | CDISS thresholds: memory state 0.16, candidate 0.18, clarity 0.25, risk ceiling 0.85; backstory state 0.26, candidate 0.22, clarity 0.35, risk ceiling 0.55 (`cdiss.rs:676-689`). | Emit only whether memory/backstory was selected, selected-count bucket, broad kinds, serious mode, degraded. Never emit query, record IDs/text/source/scores/thresholds. |
| Semantic projection provenance | `CdissProjector`, `CdissProjectionMeta`, `crates/prism-cdiss-core/src/cdiss.rs:30-159` | Provider source profile, source/target dimensions, deterministic matrix seed, fallback flag. Per projected text. | Embedder plus deterministic projection; hashed projection fallback on error. | Emit only `degraded:bool` and an opaque provider class (`local|cloud|fallback`) if operationally needed. Never emit seed, dimensions, embedding, endpoint, or text. Degraded clamps animation amplitude. |
| Watcher interpretations and route matching | `WatcherOutput`, `crates/prism-cdiss-core/src/governance/watcher.rs:25-55`; produced `main.rs:3339-3355` | Model, timestamp, ordered interpretations, context used, note; semantic route hints carry route and confidence. Per turn. | Deterministic-first watcher, optionally semantic matcher, then LLM fallback. | Do not emit interpretations, note, user context, exemplars, or raw route confidence. Only a post-Synthesizer, policy-checked broad animation category may egress. |
| Approval prediction | `ApprovalPrediction`, `crates/prism-cdiss-core/src/governance/approval_prediction.rs:37-71`, `82-240` | Decision, route, confidence, reasons, advisory-only. Combines Synthesizer, policy, Auditor, skill contract and CDISS. | Advisory prediction, not authorization. | If surfaced, emit only decision class and confidence after policy checks. Never animate it as completed work; `likely_requires_approval` maps only to waiting preparation. |
| Topic drift | `Conversation::observe`, `crates/prism-cdiss-cli/src/conversation.rs:1-15`, `67-95` | Explicit lexical cue or cosine similarity below 0.6 after two turns rotates topic/thread; closing prompts seed episodic memory. | Embedding drift or high-precision lexical cues. | Only the existing terminal `new_topic:bool` is safe. Do not emit centroid, similarity, cue text, seed prompts, session ID, or topic ID. |
| Durable thread continuity | `ThreadState`, `crates/prism-cdiss-core/src/state/thread.rs:25-121`; SQLite store `state/sqlite_store.rs:40-129` | Revision, modes, domains, facts, artifacts, approvals, recent turns, condensed summary, pinned context, CDISS, execution context, route hint, hidden source continuity. Saved after turn. | Durable JSON keyed by workspace/thread/user and governed hash. | Emit only revision, continuity present, age, current mode, counts, pending approval count, and ledger validity. Never expose prompts, responses, summaries, facts, targets, paths, source IDs, or thread key. |
| Persona temperament | `PersonaTemperament`, `crates/prism-cdiss-cli/src/persona.rs:236-285`; each `personas/*/persona.toml` | Warmth, playfulness, curiosity, directness, intensity, skepticism, continuity bias, approval caution; static per persona. | Authored configuration, not inferred user emotion. | Safe as a static style profile after validation. Use warmth/playfulness/curiosity/directness/intensity for bounded animation tuning. Skepticism, continuity bias, and approval caution remain policy/context values, not body motion controls. CDISS serious/risk clamps always win. |
| Persona response policy | `PersonaResponsePolicy`, `crates/prism-cdiss-cli/src/persona.rs:57-152`; persona TOML | Length/structure/cadence, expand/compress cues, eager policy, topic affinities. Static plus prompt matching. | Authored persona configuration. | Do not emit cue lists, instructions, or prompt matches. At most expose `proactiveTurnBudget` and a normalized cadence class through a dedicated style profile. |
| Knowledge retrieval detail | `KbQueryReport`, retrieval `crates/prism-cdiss-cli/src/knowledge_base.rs:1720-1797` | Access-gated vector/keyword ranks, RRF score, authority boost, persona focus, citations and chunk text. Per explicit or turn-triggered retrieval. | Embedding and FTS retrieval with logged match policy. | Producer must reduce before egress. Only occurrence/count bucket/vector-degraded/authority bucket may animate. |
| Provider dispatch permit | Created before chat call at `crates/prism-cdiss-cli/src/main.rs:3463-3475` | Provider kind/model, constitution and policy hashes, prompt hash, dispatch purpose. Per model call. | Runtime dispatch guard. | Diagnostic/audit only. Do not animate provider identity, model, hashes, prompt hash, or spend. A generic `model_waiting` stage is already represented by drafting. |
| Guardrail result | `main.rs:3497-3538`; internal `TurnOutcome.gates` at `1671-1689` | Pass, revised(rule list), or flagged(rule list). Per turn when gates enabled. Omitted from `web_reply_payload`. | Guardrail model/judge and optional rewrite. | Rule names and notes may expose sensitive classification. If a future safe boolean is emitted, it may only clamp motion. Never represent a safety intervention as anger, guilt, or accusation. |
| Turn performance/ledger status | `TurnOutcome`, `main.rs:1671-1689`, populated `3679-3697` | Calls, total milliseconds, tokens/second, ledger event count and validity. Per turn. Mostly omitted from web reply. | Measured runtime and ledger verification. | Operational telemetry. Use timing only for monitoring; stage timings already cover animation pacing. Ledger invalid may suppress celebratory/action animation. |

## Persona signals in the checked-out tree

The loader schema is explicit in `crates/prism-cdiss-cli/src/persona.rs:6-55`, `57-152`, and `182-356`. Each persona can define identity disclosures, runtime/continuity disclosures, boundaries, temperament, response policy, relationships, renderer name/tagline/overlay/greeting/voice, backstory, and jokes.

The inspected tree contains 25 persona directories. Their animator-relevant authored fields are the static `id`, `version`, `role`, renderer identity, and eight temperament scalars. Representative exact files:

- Default Prism/Dusty: `personas/prism/persona.toml:1-48`, renderer at `110-112`.
- Elara Voss: `personas/elara-voss/persona.toml:1-48`, renderer at `96-98`.
- Kai Renner: `personas/kai-renner/persona.toml:1-46`, renderer at `94-96`.
- Liora Kane: `personas/liora-kane/persona.toml:1-46`, renderer at `94-96`.
- Irena: `personas/irena/persona.toml:1-49`, renderer at `125-128`.
- Elianor/Elia: `personas/elia/persona.toml:1-49`, renderer at `126-129`.
- Randy/CrossFit: `personas/crossfit/persona.toml:1-45`, renderer at `109-111`.
- Zen: `personas/zen/persona.toml:1-47`, renderer at `111-113`.

Backstory and jokes are content sources, not animation signals. They are semantically recalled and governed; the avatar may receive only a generic `backstory_selected` boolean or count bucket after CDISS selection. It must never read `backstory.md`, `jokes.md`, persona overlay text, topic affinity cues, or recalled text.

### Recommended temperament-to-animation projection

| Authored field | Safe animation use | Clamp / prohibition |
|---|---|---|
| `warmth` | softer idle, open-hand gesture probability, relaxed settle | Does not override serious mode or risk. |
| `playfulness` | permits playful idle variants and wider anticipation | Forced to zero when `allowComedy=false` or serious mode. |
| `curiosity` | head tilt/listen weighting and exploratory glance | Never used to infer user state or invade privacy. |
| `directness` | shorter gesture lead-in and firmer pose selection | Does not increase movement speed or execution authority. |
| `intensity` | bounded gesture amplitude and speech beat strength | Hard maximum; reduced by risk/degraded/approval posture. |
| `skepticism` | No direct body mapping | Policy/conversation style only; a skeptical pose risks misrepresenting the user. |
| `continuity_bias` | No direct body mapping | Used by CDISS/memory; animation consumes selected recall summary instead. |
| `approval_caution` | No direct body mapping | Governance input only; waiting posture comes from actual approval state. |

## Proposed versioned Python signal-envelope schema

The envelope should be produced after Prism's privacy/governance projection and validated again by Python. It is not a mirror of any Rust struct.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:prism-gt:avatar-signal-envelope:v1",
  "title": "PrismAvatarSignalEnvelopeV1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schemaVersion", "eventId", "sequence", "kind", "lifecycle",
    "occurredAt", "observedAt", "ttlMs", "source", "correlation",
    "confidence", "governance", "payload"
  ],
  "properties": {
    "schemaVersion": { "const": "prism.avatar-signal.v1" },
    "eventId": { "type": "string", "format": "uuid" },
    "sequence": { "type": "integer", "minimum": 0 },
    "kind": {
      "enum": [
        "turn.stage", "turn.result", "conversation.topic_shift",
        "persona.changed", "cdiss.posture", "recall.summary",
        "knowledge.retrieval_summary", "route.posture",
        "approval.posture", "provider.posture", "runtime.health",
        "thread.continuity", "turn.error"
      ]
    },
    "lifecycle": { "enum": ["snapshot", "started", "updated", "completed", "cancelled", "failed"] },
    "occurredAt": { "type": "string", "format": "date-time" },
    "observedAt": { "type": "string", "format": "date-time" },
    "ttlMs": { "type": "integer", "minimum": 0, "maximum": 300000 },
    "source": {
      "type": "object",
      "additionalProperties": false,
      "required": ["system", "runtimeVersion", "surface", "producer"],
      "properties": {
        "system": { "const": "prism-gt" },
        "runtimeVersion": { "type": "string", "maxLength": 64 },
        "surface": { "enum": ["web_local", "web_public", "telegram", "cli", "unknown"] },
        "producer": { "type": "string", "maxLength": 128 }
      }
    },
    "correlation": {
      "type": "object",
      "additionalProperties": false,
      "required": ["turnRef"],
      "properties": {
        "turnRef": { "type": ["string", "null"], "maxLength": 96 },
        "threadRef": { "type": ["string", "null"], "maxLength": 96 },
        "supersedesEventId": { "type": ["string", "null"], "format": "uuid" }
      }
    },
    "confidence": {
      "type": "object",
      "additionalProperties": false,
      "required": ["value", "basis"],
      "properties": {
        "value": { "type": "number", "minimum": 0, "maximum": 1 },
        "basis": { "enum": ["deterministic", "synthesizer", "retrieval", "health_probe", "authored", "unknown"] }
      }
    },
    "governance": {
      "type": "object",
      "additionalProperties": false,
      "required": ["classification", "animationAllowed", "authority", "contentRedacted"],
      "properties": {
        "classification": { "enum": ["public", "operational", "private_aggregate"] },
        "animationAllowed": { "type": "boolean" },
        "authority": { "const": "visual_advisory_only" },
        "contentRedacted": { "const": true },
        "suppressionReasonCode": { "type": ["string", "null"], "maxLength": 64 }
      }
    },
    "payload": {
      "type": "object",
      "maxProperties": 32
    }
  }
}
```

### Payload contracts by kind

The top-level schema alone is insufficient. Python must validate `kind` against a discriminated payload model.

| Kind | Allowed payload fields | Default TTL | Animation authority |
|---|---|---:|---|
| `turn.stage` | `stageId`, `status`, `startedAtMs`, `durationMs?`, `expression`, `mouth`, `energy` | 15 s | Temporary stage layer only. |
| `turn.result` | `verdict`, `confidence`, `personaId`, `newTopic`, sanitized expression metrics/booleans | 30 s | Terminal settle/expression; no movement. |
| `conversation.topic_shift` | `changed:true`, `cause:"explicit"|"semantic"|"unknown"` | 5 s | Brief reset/reorientation. Do not expose similarity or topic. |
| `persona.changed` | `personaId`, `personaVersion`, validated style scalars | snapshot | Style baseline only. |
| `cdiss.posture` | status, six safe metrics except authority may be omitted, safe action booleans, serious/comedy/recall gates, degraded, oscillation/invariant booleans | 30 s | Expression/gesture clamp only. |
| `recall.summary` | `memorySelected`, `backstorySelected`, `selectedCountBucket:"0"|"1"|"2_plus"`, `kinds:string[]`, `degraded` | 5 s | One generic recollection cue; no content. |
| `knowledge.retrieval_summary` | `occurred`, `resultCountBucket`, `vectorAvailable`, `authorityBucket`, `degraded` | 5 s | Generic consult/reference gesture. |
| `route.posture` | `category`, `status`, `approvalRequired`, `confidenceBucket` | 10 s | Preparatory gesture only; never completion. |
| `approval.posture` | `state:"pending"|"approved"|"denied"|"stale"|"failed"`, `category` | 60 s pending, 4 s terminal | Waiting or brief acknowledgement; no execution. |
| `provider.posture` | `state:"ready"|"degraded"|"unavailable"`, `fallbackUsed` | 30 s | Status/clamp only; never personality. |
| `runtime.health` | `state:"ready"|"degraded"|"unavailable"`, `auditHealthy`, `signalAgeMs` | 10 s | Fail-safe neutral/disconnected posture. |
| `thread.continuity` | `present`, `revision`, `ageBucket`, `pendingApprovalCount`, `recentTurnsBucket`, `ledgerValid` | 30 s | Resync and subtle resume cue. |
| `turn.error` | `class:"transport"|"provider"|"governance"|"persistence"|"unknown"`, `retryable` | 5 s | Neutral reset/error indicator; no raw message. |

### Example safe stage envelope

```json
{
  "schemaVersion": "prism.avatar-signal.v1",
  "eventId": "cfb4b7e5-4881-4878-89e1-377b343f8af2",
  "sequence": 1042,
  "kind": "turn.stage",
  "lifecycle": "started",
  "occurredAt": "2026-07-13T06:10:00Z",
  "observedAt": "2026-07-13T06:10:00.018Z",
  "ttlMs": 15000,
  "source": {
    "system": "prism-gt",
    "runtimeVersion": "0.1.0",
    "surface": "web_local",
    "producer": "web::stage_event"
  },
  "correlation": {
    "turnRef": "opaque-turn-ref",
    "threadRef": "opaque-thread-ref",
    "supersedesEventId": null
  },
  "confidence": { "value": 1.0, "basis": "deterministic" },
  "governance": {
    "classification": "operational",
    "animationAllowed": true,
    "authority": "visual_advisory_only",
    "contentRedacted": true,
    "suppressionReasonCode": null
  },
  "payload": {
    "stageId": "understanding",
    "status": "active",
    "startedAtMs": 35,
    "expression": "focused",
    "mouth": 0.08,
    "energy": 0.42
  }
}
```

## Python adapter behavior

The production implementation belongs in WizardJoeAvatar and should be idiomatic Python.

### Ingress and validation

1. `PrismSignalAdapter` connects to an explicitly configured Prism URL; it is disabled by default.
2. Prefer a dedicated minimized Prism animation SSE endpoint. Until one exists, a compatibility adapter may consume `/api/chat/stream` only for the same user session that initiated the turn.
3. Use a scoped secret or authenticated same-user session. Do not scrape Prism SQLite files, ledger files, memory DBs, or thread-state JSON directly.
4. Parse the envelope into typed Python models. Reject unknown versions/kinds, extra fields, nonfinite scalars, out-of-range metrics, excessive strings, stale TTL, sequence regression, duplicate event IDs, or invalid lifecycle transitions.
5. Hash or replace source correlation IDs before logging in WizardJoeAvatar. Do not persist payloads by default.

### Arbitration and animation translation

The adapter produces a separate `semantic_context` channel. It does not call movement commands.

Priority should be:

1. user remote-control locomotion and explicit user action commands;
2. safety/governance clamps (`blocked`, `approval`, serious mode, degraded health);
3. explicit speech/turn stage;
4. terminal verdict/clarification;
5. recall/reference gesture;
6. persona baseline and idle variation.

The semantic channel may request only allowlisted intents with maximum durations and interrupt rules. Examples:

- `listen`: upper-body/head pose; locomotion continues if user is moving.
- `think`: reduced mouth, focused expression, no world-space displacement.
- `speak`: mouth/speech beat channel; locomotion and flight remain independently controlled.
- `recall`: one short glance/hand gesture, never repeated from a persistent snapshot.
- `wait_for_approval`: planted hold that suppresses anticipatory action but does not stop user-controlled locomotion unless product design explicitly chooses that behavior.
- `degraded_idle`: neutral low-amplitude idle, preserving remote-control responsiveness.

Every semantic intent needs `source_event_id`, accepted simulation tick, expiry tick, priority, channel ownership, and cancellation behavior. On disconnect or TTL expiry, it releases cleanly to the prior user-driven state.

### Resynchronization

SSE can reconnect after missed events. A dedicated Prism animation surface should expose:

- a monotonic source sequence;
- `Last-Event-ID` resume where retained history permits;
- a current sanitized snapshot endpoint;
- an explicit `stream_epoch` that changes after Prism restart;
- lifecycle-complete events so Python can release temporary channels;
- periodic heartbeat carrying only source time, sequence, and health.

After reconnect, Python should request the latest `persona.changed`, `cdiss.posture`, `runtime.health`, `thread.continuity`, and pending `approval.posture` snapshots. It must not replay expired stage, recall, route, or acknowledgement gestures.

## Signals that must not animate

The following are explicit prohibitions, not merely deferred ideas:

- raw prompt, reply, clarification text, memory snippet, KB chunk, source title/path/URI, persona backstory, joke text, or overlay;
- any embedding, projection vector, centroid, matrix seed, semantic similarity value, action signature, parser evidence, agreement claim, or permission list;
- chain-of-thought, scratchpad, hidden prompt, Watcher note, Auditor rationale, Synthesizer rationale, guardrail note/rule names, or gate rationale;
- API key presence by provider, key storage location, username, provider/model identity, endpoint URL, error string, or cost/spend;
- approval payload, draft text, target, payload hash, audit payload, or display result;
- thread/user/Telegram IDs, trace IDs, ledger hashes, source continuity IDs, file paths, or database paths;
- authority level as apparent dominance, confidence as emotional certainty, governance risk as fear, denial as disappointment, or blocked state as anger;
- route readiness as if an action has executed;
- memory relevance as if the character truly remembers content unless the governed recall decision selected a sanitized recall summary.

## Current gaps and contradictions to resolve before implementation

1. **No versioned animation envelope exists.** Current SSE stage payloads are useful but have no schema version, event ID, source sequence, stream epoch, wall-clock timestamp, TTL, or governance metadata.
2. **Stage timing is turn-relative.** `startedAt`/`at_ms` are elapsed milliseconds, not globally comparable timestamps (`web.rs:6127-6146`).
3. **Terminal stages are emitted done-only.** Consumers must not assume every lifecycle has a started event (`web.rs:4433-4459`). A new contract should make terminal snapshots explicit.
4. **The frontend parser silently drops malformed SSE.** `parseSseBlock` returns null on JSON failure (`src/lib/sse-cdiss.js:5-24`). The Python adapter needs observable validation counters and fail-closed state.
5. **The generic approval comments overstate current web behavior.** `pending_approval_payload` is route-agnostic, but `capture_pending_approval` returns `None` unless `route_id == "x.post"` (`web.rs:5855-5863`). Non-X material actions are denied for the web face (`web.rs:5992-6005`). The signal adapter must report actual current behavior, not generic intent.
6. **Public mode omits private diagnostics and approval resolution.** Integration cannot rely on `/api/runtime/status`, `/api/memory/*`, `/api/thread/inspect`, or `/api/approval` when Prism runs in public-web mode (`web.rs:291-392`).
7. **Recall occurrence is not in the web reply.** `TurnOutcome.recalled` exists (`main.rs:1680`, populated at `3688`) but `web_reply_payload` omits it (`web.rs:6008-6018`). A safe recall summary must be added producer-side.
8. **Guardrail posture is not in the web reply.** Internal `gates` exists but is omitted. Any future signal should be a boolean/class clamp, not rule names.
9. **Turn performance and ledger health are omitted from reply.** Do not infer health from a successful reply; use explicit safe health snapshots.
10. **Thread selected-route persistence is weak in this revision.** The pushed `Turn.selected_route_id` is set to `"n/a"` only when a state-patch mode exists (`main.rs:3597-3606`), rather than reliably storing the selected route. Use the governed skill/dispatch outcome, not this field, for a future route posture event.
11. **Memory status reports no last recall time.** The code explicitly sets it to null (`web.rs:3727-3731`). Do not fabricate freshness.
12. **Projection fallback is real but not stage-streamed.** It is available through product/runtime projection state; Python should receive a safe degraded flag before increasing animation amplitude.
13. **There is no current cross-process authentication contract for Wizard Joe.** Reusing a browser session token out of process would be brittle. Define a scoped visual-signal credential or authenticated local bridge.
14. **No delivery guarantee is specified.** The adapter needs sequence, epoch, deduplication, resume, snapshot, TTL, and lifecycle semantics before it can safely own temporary animation channels.

## Recommended producer changes in Prism

These are proposals, not claims about current code:

1. Add a producer-side `AvatarSignalProjector` that accepts existing stage/product/recall/route/approval/health inputs and emits only the versioned envelope.
2. Add `GET /api/avatar-signals/snapshot` and `GET /api/avatar-signals/stream` to the **private or explicitly secured** router. Do not add diagnostic endpoints wholesale to public mode.
3. Give each stream an epoch and monotonic sequence; retain a small bounded event history for `Last-Event-ID` resume.
4. Emit stage started/completed, sanitized terminal result, topic shift, persona change, CDISS posture, recall summary, retrieval summary, route posture, approval posture, runtime health, and continuity snapshot.
5. Classify producer errors before emission and drop raw messages.
6. Unit-test that forbidden field names and secret canaries never serialize, extending the read-model sentinel approach already used at `crates/prism-cdiss-cli/src/web.rs:2800-2828`.
7. Property-test scalar finiteness/ranges, lifecycle ordering, monotonic sequence, TTL, deduplication, and content-free payloads.
8. Keep the authority invariant literal in the envelope contract and test that every event reports `visual_advisory_only`.

## Acceptance criteria for the eventual integration

1. WizardJoeAvatar remains a Python/FastAPI/ASCILINE process on port 8765; no Rust crate, binary, sidecar, extension, or WASM module is added to its runtime.
2. Prism is optional. With Prism unavailable, remote controls and all ordinary avatar behavior remain fully functional.
3. Every accepted signal validates against the exact supported schema and kind payload. Unknown data increments a diagnostic counter and has no visual effect.
4. No accepted payload contains prompt/reply text, snippets, paths, source IDs, user/thread IDs, embeddings, model names, provider names, route exemplars, rationales, hashes, keys, or approval payloads.
5. Duplicate, reordered, stale, expired, or previous-epoch events cannot retrigger gestures.
6. Stage lifecycle transitions are deterministic and temporary channels release on completion, cancellation, failure, disconnect, and TTL expiry.
7. User remote-control locomotion remains responsive while listen/think/speak/recall/approval layers play.
8. Prism cannot create world-space displacement or begin an action that the user did not command.
9. Risk, serious mode, blocked, invariant, approval-required, and degraded health only reduce or constrain animation.
10. Recall and KB gestures are triggered only by producer-side governed summaries, never by polling private content endpoints.
11. Persona transitions blend style without changing position, locomotion phase, flight state, staff attachment, or remote-control ownership.
12. Reconnect snapshot restores persistent posture without replaying transient gestures.
13. Automated tests prove signal-to-intent mapping, privacy rejection, schema-version rejection, TTL, deduplication, ordering, arbitration, disconnect recovery, and deterministic replay.
14. Browser evidence shows walking, flying, speaking, thinking, recalling, clarifying, waiting for approval, provider degradation, and reconnect while maintaining crisp squares, stable anatomy, and remote-control responsiveness.

## Final recommendation

Build the integration around **semantic animation intent, not semantic content**. Prism already knows when it is listening, drafting, auditing, deciding, clarifying, waiting for approval, recalling context, changing topic, operating with degraded projection, or switching persona. Those are useful cartoon direction cues. The avatar does not need, and should not receive, what the user said, what was recalled, which source ranked highest, which model ran, why a gate fired, or what action payload is pending.

The clean architecture is therefore a narrow Prism producer projection plus a strict Python consumer adapter. That gives Wizard Joe a convincing governed inner rhythm while preserving ASCILINE Python ownership, remote-control authority, privacy, and the hard separation between looking alive and claiming powers the character does not have.
