# Persona, Memory, and Governance Signals for ASCILINE Animation

**Role:** PERS specialist signal research
**Source repository:** `/Users/paul/Documents/prism-geometry-talk`
**Observed branch:** `prism-gt-influence-integrated`
**Observed checkout state:** clean; local branch was 80 commits behind its remote when inspected
**Destination:** WizardJoeAvatar, ASCILINE Python runtime on port `8765`
**Research date:** 2026-07-13

## 1. Scope and non-negotiable boundary

This report describes signals present in the exact local Prism GT checkout. It does not treat the remote branch as authoritative and does not modify Prism GT.

The production animation runtime remains ASCILINE Python on port `8765`. Prism's Rust runtime, CDISS engine, memory stores, and governance system may only provide typed, sanitized semantic signals through a Python adapter. Rust must not own rendering, animation state, pose selection, timing, input handling, or delivery.

Signal labels used below:

- **EXISTS:** implemented and serialized or directly readable in the inspected checkout.
- **DERIVED:** safely computable in the Python adapter from existing serialized fields, but not currently emitted as its own Prism field.
- **PROPOSED:** a new contract or signal that does not yet exist.
- **DO NOT ANIMATE:** content or authority-bearing state that must not become expressive motion.

The core rule is simple: animation may reflect interaction posture, lifecycle, and bounded expression. It must never reveal private content, imply that recalled information is evidence, portray permission that has not been granted, or visually inflate model confidence into authority.

## 2. Executive finding

Prism GT already exposes enough safe state to drive a responsive cartoon character without transporting private prompts, memory bodies, raw embeddings, hidden deliberation, or internal governance rationale.

The strongest existing animation inputs are:

1. SSE turn-stage events with explicit `expression`, `mouth`, and `energy` fields.
2. The terminal reply with persona, verdict, confidence, topic change, expression snapshot, and pending approval.
3. Sanitized runtime status with CDISS scalar metrics and posture booleans.
4. Redacted thread inspection with counts, lifecycle, action-space booleans, and persistence timestamps.
5. Persona identity plus a complete persona-to-shape map and stable temperament fields.
6. Sanitized memory and knowledge-base diagnostics that expose counts, selected kinds, scores, match types, and provenance without requiring raw text.

The adapter should consume these surfaces and emit a smaller animation-intent envelope. The ASCILINE runtime should never consume raw Rust state or infer animation directly from user text.

## 3. Existing persona model

### 3.1 Canonical persona schema

**EXISTS.** The Rust loader models each persona as:

- `meta`: `id`, `version`, `role`
- `disclosures`: identity, runtime, and continuity truth rules
- `boundaries`: always, never, approval, and memory constraints
- `temperament`: warmth, playfulness, curiosity, directness, intensity, skepticism, continuity bias, approval caution
- `response_policy`: length, structure, cadence, expansion/compression triggers, serious-mode structure, eager behavior, and topic affinities
- `relationships`: audience and stance
- `renderer`: name, tagline, overlay, greeting, and voice

Source: `crates/prism-cdiss-cli/src/persona.rs:6-15`, `57-83`, `182-199`, `215-255`, `288-303`.

The loader validates renderer text against authority-bearing claims such as bypassing approval or governance. Those claims are rejected at load time, not merely discouraged in a prompt. Source: `crates/prism-cdiss-cli/src/persona.rs:401-457`.

Twenty-four persona IDs are canonical and embedded in the binary; disk overrides are accepted only for a canonical ID. Source: `crates/prism-cdiss-cli/src/persona.rs:495-554`, `572-624`.

### 3.2 Persona identity and shape mapping

**EXISTS.** The frontend maps every canonical persona to one of six geometry identities. Source: `src/lib/persona-expression.js:13-41`.

| Persona ID | Display identity | Existing Prism shape |
|---|---|---|
| `elara-voss` | Elara Voss | dodecahedron |
| `kai-renner` | Kai Renner | icosahedron |
| `liora-kane` | Liora Kane | cube |
| `thorne-vale` | Thorne Vale | octahedron |
| `serena-quill` | Serena Quill | star tetrahedron |
| `draven-holt` | Draven Holt | cube |
| `mira-solen` | Mira Solen | star tetrahedron |
| `rohan-slate` | Rohan Slate | tetrahedron |
| `aurelia-finch` | Aurelia Finch | icosahedron |
| `finn-calder` | Finn Calder | dodecahedron |
| `selene-hart` | Selene Hart | octahedron |
| `orion-vale` | Orion Vale | tetrahedron |
| `prism` | Dusty | star tetrahedron |
| `conspiracy` | Hunter | icosahedron |
| `vegan` | Sally | star tetrahedron |
| `zen` | Zen | tetrahedron |
| `bookie` | Bookie | cube |
| `crossfit` | Randy | octahedron |
| `ryland` | Ryland | dodecahedron |
| `elia` | Elianor / Elia | dodecahedron |
| `irena` | Irena | octahedron |
| `marisol` | Marisol | tetrahedron |
| `sabine` | Sabine | icosahedron |
| `thalia` | Thalia | cube |

The `/api/personas` response exposes only `{id, name, tagline}` plus the active ID. It does not expose role, voice ID, temperament, disclosures, boundaries, or backstory. Source: `crates/prism-cdiss-cli/src/web.rs:5477-5488`.

### 3.3 Safe persona animation interpretation

**DERIVED.** Persona identity may select an animation profile, but it should not replace Wizard Joe's visual identity or imply the persona is a real person.

Safe mappings:

- `shape` -> motion profile family, not a literal geometric transformation requirement.
- warmth -> softer settle and more open idle stance.
- playfulness -> optional secondary motion, only when `comedyAllowed` and not `seriousMode`.
- curiosity -> head tilt or attentive lean.
- directness -> faster anticipation and cleaner gesture endpoint.
- intensity -> larger but bounded gesture amplitude.
- skepticism -> measured pause or side glance, never contempt.
- continuity bias -> callback gesture frequency, not intimacy.
- approval caution -> lower flourish and stronger stop pose around approval boundaries.

The persona temperament affects CDISS configuration in Rust, so the adapter must avoid applying it twice at full strength. The Rust conversion is at `crates/prism-cdiss-cli/src/persona.rs:38-53`; the CDISS engine is built from that temperament at `crates/prism-cdiss-cli/src/main.rs:3075-3087`.

### 3.4 Identity, voice, style, and backstory boundaries

The persona files explicitly separate character expression from authority. For example:

- Elara's disclosures deny human educator or institutional authority, and her memory boundary says memory is not a student information system. Source: `personas/elara-voss/persona.toml:6-17`, `19-37`.
- Dusty's backstory may shape expression but is not proof, permission, approval, or human persistence. Source: `personas/prism/persona.toml:6-37`, `109-128`.
- Sabine separates fact, inference, suspicion, and unknown and forbids presenting suspicion as proof. Source: `personas/sabine/persona.toml:19-38`, `124-142`.
- Elia's mathematical or relational interpretation is explicitly not evidence or access to the user's interiority. Source: `personas/elia/persona.toml:6-38`, `126-144`.

**DO NOT ANIMATE:** renderer overlay text, greeting text, voice provider IDs, relationship audience text, backstory fragments, disclosure text, or boundary text. These are prompt/configuration data, not animation telemetry.

## 4. Existing expression and stage vocabulary

### 4.1 Expression presets

**EXISTS.** Prism defines six expression IDs:

| Expression | Existing mode | Existing geometric meaning | Safe cartoon mapping |
|---|---|---|---|
| `friendly` | idle | balanced, warm, open | relaxed idle, open shoulders, gentle blink |
| `focused` | thinking | narrow, work-oriented | attentive lean, reduced secondary motion |
| `angry` | error | sharp, defensive | **do not map to anger**; use bounded alert/error recoil |
| `constrained` | idle | rigid, calm, boxed-in | stillness, hands close, guarded anticipation |
| `expansive` | response | bright, enthusiastic | broad explanatory gesture or takeoff-ready pose |
| `mythic` | response | ceremonial, dramatic | staff flourish only under low risk and no approval wait |

Each preset includes numeric glow, motion, breakup, speed, attention, anticipation, settle, transform speed, and transform force values. Source: `src/pages/PrismHero/prismShapeState.js:65-181`.

The browser currently derives a terminal expression from verdict, governance risk, task readiness, confidence, and serious mode when an explicit preset is absent. Source: `src/lib/sse-cdiss.js:32-45`.

**Safety correction:** `angry` is a legacy geometry label. The Python adapter should rename it to `alert_error` in the animation envelope. A character should not appear angry at the user because a runtime error occurred.

### 4.2 Turn-stage SSE

**EXISTS.** `POST /api/chat/stream` returns SSE. The turn emits `stage` events while work is running, then a `reply` or `error`. Source: `crates/prism-cdiss-cli/src/web.rs:4343-4474`.

Stage payload fields:

```text
type: "stage"
stageId: string
stage: string
label: string
status: "active" | "done"
startedAt: integer milliseconds from turn start
safeSummary: string
expression: expression ID
mouth: number
energy: number
at_ms: integer
durationMs?: integer
finishedAt?: integer
missingDecision?: string
```

Producer: `stage_event` in `crates/prism-cdiss-cli/src/web.rs:6119-6147`.
Cadence: one `active` event at stage entry and one `done` event at stage exit; terminal stage is emitted before `reply`.
Provenance: deterministic server lifecycle metadata.
Confidence: categorical, not probabilistic.

Existing stage map, from `stage_meta` at `crates/prism-cdiss-cli/src/web.rs:6037-6111`:

| Stage ID | Expression | Mouth | Energy | Safe ASCILINE intent |
|---|---:|---:|---:|---|
| `queued` | focused | 0.04 | 0.22 | settle into attention |
| `understanding` | focused | 0.08 | 0.42 | listening/reading idle |
| `drafting` | friendly | 0.22 | 0.72 | thinking with light hand motion |
| `checking_safety` | constrained | 0.06 | 0.48 | slow, still verification pose |
| `reviewing` | mythic | 0.12 | 0.62 | measured decision gesture, not authority theater |
| `ready` | friendly | 0.10 | 0.40 | answer-ready settle |
| `needs_clarification` | focused | 0.08 | 0.40 | questioning gesture |
| `waiting_approval` | constrained | 0.06 | 0.40 | explicit stop-and-wait pose |
| fallback `working` | focused | 0.10 | 0.40 | generic work loop |

`missingDecision` contains user-facing text and must not be sent to animation. Only its presence may become `needs_clarification=true`.

### 4.3 Terminal reply signal

**EXISTS.** The terminal `reply` payload contains:

```text
type: "reply"
reply: string
verdict: string
confidence: number
persona: string
lens: string | null
new_topic: boolean
expression: CdissExpressionSnapshot
pendingApproval: object | null
```

Producer: `web_reply_payload`, `crates/prism-cdiss-cli/src/web.rs:5974-6018`.
Cadence: once per completed governed turn.
Provenance: governed turn outcome.
Privacy: `reply` is user content and must not cross the animation adapter. `lens` is safe as a category only after allow-listing. `pendingApproval.payload` may contain material content and must be stripped.

Safe mappings:

- `verdict=clarify` -> question/listen clip.
- pending approval present -> hard wait pose; no celebratory or execution motion.
- `new_topic=true` -> brief reorientation/turn, not memory erasure theater.
- `confidence` -> tiny settle-duration adjustment only. Never map confidence to character size, dominance, brightness, flight height, or certainty gestures.

## 5. CDISS signals that genuinely exist

### 5.1 Safe product metrics

**EXISTS.** The safe CDISS product view exposes:

- status
- user-visible headline and optional reason
- allowed action booleans
- governance gates
- scalar metrics: clarity, task readiness, memory relevance, governance risk, authority level, urgency
- deltas
- signal counts/sources/fallback flag
- projection metadata
- update timestamp
- evidence-only flag
- authority invariant

Source: `crates/prism-cdiss-core/src/cdiss.rs:569-638`.

The authority invariant is explicit: conversation continuity cannot grant approval; explicit user approval is required before material work runs. Source: `crates/prism-cdiss-core/src/cdiss.rs:640-641`.

### 5.2 Sanitized runtime status API

**EXISTS.** `GET /api/runtime/status` intentionally excludes raw vectors, hidden prompts, private deliberation, and turn content. It exposes scalar metrics and posture booleans. Source: `crates/prism-cdiss-cli/src/web.rs:3114-3145`.

Payload fields include:

```text
activePersonaId, personaName, constitutionVersion
chatProvider, chatModel, chatLabel
govProvider, govModel, govLabel
embedderProvider
comedyEnabled, eagerEnabled, gatesEnabled, voiceEnabled, memoryEnabled
hasContinuity
lastTurnId, lastTurnAt, stateUpdatedAt
ledgerAuditFailures, auditHealthy
disposition, dispositionStatus
clarity, readiness, memoryRelevance, risk, authorityLevel, urgency
approvalPosture
seriousMode, memoryAllowed, backstoryAllowed, comedyAllowed
projectionDegraded, cdissUpdatedAt
```

Producer: `build_runtime_status`, `crates/prism-cdiss-cli/src/web.rs:3175-3247`; handler projection at `3249-3308`.
Cadence: pull/read model, generally once on connect and after terminal events; polling should be bounded.
Confidence/provenance: scalar CDISS state rounded to three decimals; provider/model labels are current runtime configuration.
Privacy: safe by design, but model/provider names should influence diagnostics, not character emotion.

Safe mappings:

- `seriousMode` -> strongest animation clamp: no comedy, no flourishes, lower speed and amplitude.
- `approvalPosture=approval_required` -> stationary waiting pose.
- `approvalPosture=read_only_advisory` -> subdued inspect/read gesture; never imply execution.
- `projectionDegraded=true` -> small uncertainty indicator or reduced animation confidence, not character distress.
- `auditHealthy=false` -> diagnostics badge only; animation may enter neutral alert idle, never panic.
- `memoryAllowed` / `backstoryAllowed` -> permit a subtle continuity gesture but never reveal which memory.
- `comedyAllowed` -> permits, but does not force, playful secondary motion.
- `clarity` -> focus/hesitation blend.
- `urgency` -> locomotion cadence within strict bounds.
- `risk` -> stillness and caution, not aggression.
- `readiness` -> preparation/settle, not permission to act.
- `authorityLevel` -> **DO NOT ANIMATE** as dominance, stature, glow, power, or command.

### 5.3 Raw vector state

**EXISTS internally; DO NOT EXPORT.** CDISS internally stores eight-dimensional intent, topic, emotional, agreement, temporal, and relational vectors plus scalar authority, clarity, urgency, memory relevance, readiness, risk, and completion. Source: `crates/prism-cdiss-core/src/cdiss.rs:238-254`.

The persisted snapshot also carries governance projection, oscillation detection, invariant violations, action signature history, and timestamps. Source: `crates/prism-cdiss-core/src/cdiss.rs:1401-1430`.

Raw vectors and invariant rationale are deliberately omitted from the web inspector. Source: `crates/prism-cdiss-cli/src/web.rs:3838-3848`, `3867-3887`.

The Python adapter must consume the sanitized product view or runtime status, never `IntentStateSnapshot` directly.

## 6. Memory, recall, and relationship persistence

### 6.1 Local memory store

**EXISTS.** Prism memory is SQLite with fields `id`, `kind`, `text`, `source`, embedding BLOB, creation timestamp, and persona scope. Source: `crates/prism-cdiss-cli/src/memory.rs:54-74`.

Embedding order is local Nomic, local compatible fallback, optional cloud only when configured, then a native in-process fallback. Source: `crates/prism-cdiss-cli/src/memory.rs:90-157`, `245-273`.

Recall records contain only `text`, `kind`, and cosine score in the CLI layer. Source: `crates/prism-cdiss-cli/src/memory.rs:48-52`.

Persona isolation is explicit: normal retrieval searches global atoms and the active persona, excluding other personas and excluding backstory; backstory has a separate gated retriever. Source: `crates/prism-cdiss-cli/src/memory.rs:423-472`.

### 6.2 CDISS recall decision

**EXISTS.** Recall kinds are fact, note, episode, and persona backstory. Candidate fields are ID, kind, relevance score, and source. Source: `crates/prism-cdiss-core/src/cdiss.rs:643-659`.

Default thresholds distinguish ordinary memory from backstory. Backstory requires higher state relevance and clarity and a lower governance-risk ceiling. Source: `crates/prism-cdiss-core/src/cdiss.rs:661-689`.

The decision exposes selected candidate IDs, per-candidate selected/reason, memory allowed, backstory allowed, serious mode, and the authority invariant. Source: `crates/prism-cdiss-core/src/cdiss.rs:917-935`.

Selection requires both state permission and candidate score. Backstory is suppressed unless clarity, semantic resonance, and low risk are stronger. Source: `crates/prism-cdiss-core/src/cdiss.rs:945-1032`.

Safe adapter fields:

```text
candidateCount: integer
selectedCount: integer
selectedKinds: enum[]
maxSelectedScore: number | null
memoryAllowed: boolean
backstoryAllowed: boolean
seriousMode: boolean
projectionDegraded: boolean
```

**DO NOT EXPORT:** recalled text, snippets, query text, candidate reasons, source database paths, embeddings, or candidate IDs that could become stable user-content identifiers.

### 6.3 Memory read-model APIs

**EXISTS.** Private mode routes include:

- `GET /api/memory/status`
- `GET /api/memory/recent`
- `POST /api/memory/test`
- `GET /api/thread/inspect`

Source: `crates/prism-cdiss-cli/src/web.rs:340-359`.

`memory/status` exposes enabled state, redacted database basename, record counts, active persona, embedder chain, degradation, last write, and last error. It honestly leaves last recall as null because tracking is not wired. Source: `crates/prism-cdiss-cli/src/web.rs:3640-3733`.

`memory/test` returns only selected records, with kinds, scores, sources, and sanitized snippets; suppressed candidates are counted but not detailed. Source: `crates/prism-cdiss-cli/src/web.rs:3760-3797`.

For animation, use only counts, kinds, scores, and degraded status. Even sanitized snippets are unnecessary and should be dropped.

### 6.4 Backstory and relationship continuity

**EXISTS.** Persona backstory is split into `---`-delimited atoms and seeded once per persona. Source: `crates/prism-cdiss-cli/src/main.rs:2136-2155`.

When a topic closes, Prism stores a persona-scoped episode and may create one or two persona-scoped reflection notes. Reflections are instructed to capture observable preferences, constraints, phrases, and decisions, and to avoid diagnosing motives, emotions, attachment, wounds, or “the bond.” Source: `crates/prism-cdiss-cli/src/main.rs:2158-2230`.

Relationship stage is based on count of persona-scoped episodes and reflections:

- 0: brand new
- 1-5: getting acquainted
- 6-20: established
- 21+: deep

Source: `crates/prism-cdiss-cli/src/main.rs:4562-4571`.

**DERIVED safe signal:** expose only `relationshipStage` as `new | acquainted | established | deep` and `historyPresent: boolean`. Do not export counts, reflections, episode text, or backstory.

Animation mapping should be restrained: established continuity can slightly reduce idle hesitation or allow a familiar greeting gesture. It must never become romantic proximity, touch, obedience, emotional dependence, or a visual claim of personal intimacy.

## 7. Thread and session persistence

### 7.1 Topic-scoped working memory

**EXISTS.** A session is one process or explicit new session. Each topic receives its own thread ID. Topic shifts occur from explicit lexical cues or embedding drift against a running centroid. The closing topic is summarized into episodic memory rather than replayed verbatim. Source: `crates/prism-cdiss-cli/src/conversation.rs:1-15`, `20-55`, `67-111`.

Safe signals:

- `new_topic` from reply payload.
- thread `revision` and `updatedAt` from redacted inspection.
- `recentTurnsCount` and `promptTokensEstimate` as operational pressure indicators.
- presence, not body, of condensed summary and pinned facts.

### 7.2 Persisted thread state

**EXISTS.** Thread state contains mode, perspective, project, topic stack, domains, constraints, facts, artifacts, approvals, recent turns, governance hash, condensed summary, pinned facts/constraints, Torus metadata, optional CDISS snapshot/product metadata, execution context, route hint, and source-continuity hiding. Source: `crates/prism-cdiss-core/src/state/thread.rs:25-121`.

The redacted inspector intentionally exposes counts and safe lifecycle fields while withholding bodies unless explicitly revealed; raw vectors and hidden prompts are never exposed. Source: `crates/prism-cdiss-cli/src/web.rs:3851-4017`.

Safe animation mapping:

- revision change -> no motion by itself.
- new topic -> reorientation transition.
- active mode `Chat/Inquire/Execute` -> conversational/listening/preparation family, but execute motion remains gated by approval posture.
- pending approval count -> wait pose.
- artifact lifecycle -> optional work-complete gesture only after a verified completed lifecycle.
- prompt token pressure -> **DO NOT ANIMATE** as distress; at most diagnostics UI.

## 8. Knowledge-base and self-knowledge recall

### 8.1 Knowledge-base query result

**EXISTS.** A KB query includes query, limit, mode, persona ID, domain/access/authority filters, retrieval profile, and archived/private flags. Results expose chunk/document IDs, title, source package/pointer, domain, knowledge type, authority/access level, retrieval score, match type, vector/keyword ranks, and chunk text. Source: `crates/prism-cdiss-cli/src/knowledge_base.rs:183-232`.

Query execution applies metadata access gates, vector and keyword search, reciprocal-rank fusion, authority boost, optional persona focus, and citation results. Source: `crates/prism-cdiss-cli/src/knowledge_base.rs:1720-1797`.

Persona focus multiplies retrieval score based on configured source/domain/tag focus. Source: `crates/prism-cdiss-cli/src/knowledge_base.rs:4627-4660`.

Safe adapter fields:

```text
queryActive: boolean
resultCount: integer
vectorAvailable: boolean
matchTypes: enum[]        # hybrid | vector | keyword | metadata | related
topScore: number | null
authorityBands: enum[]    # allow-listed labels only
accessGateApplied: true
personaFocusApplied: boolean | null
```

**DO NOT EXPORT:** query, chunk text, titles, source pointers, source paths, document/chunk IDs, private flags, or content-derived concept tags.

`retrievalScore` is ranking provenance, not truth confidence. It may produce a “searching/reading” gesture, but never a nod of factual certainty.

### 8.2 Product self-knowledge

**EXISTS.** Prism seeds a local product-reference library describing Prism GT identity, the complete persona roster, runtime architecture, governance, memory, providers, and desktop behavior. Source: `crates/prism-cdiss-cli/src/self_knowledge.rs:5-30`.

The self-knowledge text explicitly says personas are constructed AI personas, not staff, clinicians, lawyers, mandated reporters, or holders of student records. Source: `crates/prism-cdiss-cli/src/self_knowledge.rs:51-110`, `114-127`.

Safe signal: `selfKnowledgeContextUsed: boolean` or `knowledgeDomain="product_self"`.

**PROPOSED.** That boolean is not present in the inspected web animation payloads. It should be added to the Rust-to-Python adapter only after a sanitized producer field is implemented. Until then, do not infer it from response text.

## 9. Governance, approval, refusal, and contact-lens boundaries

### 9.1 Action-space and gate states

**EXISTS.** Allowed actions are `respond`, `askClarification`, `callTool`, `executeHighRisk`, `materialActionsRequireApproval`, `forceClarification`, and `blocked`, plus reasons. Source: `crates/prism-cdiss-core/src/cdiss.rs:494-519`.

CDISS product statuses are:

- `noState`
- `stable`
- `clarificationNeeded`
- `approvalRequired`
- `blocked`
- `degradedProjection`
- `invariantViolation`
- `oscillationDetected`

Source: `crates/prism-cdiss-core/src/cdiss.rs:569-580`.

Safe animation mapping:

- clarification needed -> question pose.
- approval required -> full stop/wait.
- blocked -> neutral boundary pose; no shame, anger, or threat.
- degraded projection -> subdued uncertainty.
- invariant violation -> neutral safety halt plus diagnostics indicator.
- oscillation -> small indecision loop with a strict timeout, never frantic jitter.
- stable -> normal idle/response flow.

### 9.2 Approval cards

**EXISTS.** A generic approval payload includes route ID, skill display, question, summary, risk level, payload hash, and route payload. Source: `crates/prism-cdiss-cli/src/web.rs:5950-5971`.

Only X posting is captured as a live web approval card in the inspected implementation; other gated actions are denied on the web face and directed to the desktop REPL. Source: `crates/prism-cdiss-cli/src/web.rs:5989-6004`, `5855-5863`.

Animation may consume only:

- `pending: boolean`
- allow-listed `riskLevel`
- `resolution: pending | approved | denied | expired`

**DO NOT EXPORT:** route payload, question, summary, draft text, payload hash, username, credentials, or target.

Approved does not mean “celebrate.” It means the runtime may proceed to the next governed lifecycle state. Denied should return to neutral without disappointment, guilt, or persuasion.

### 9.3 Constitution

**EXISTS.** The constitution states that honesty outranks helpfulness and conversational tone, uncertainty must be surfaced, and work must not be fabricated. Source: `constitution/constitution.toml:14-36`.

Hard rules require explicit mode transitions, disclosure before external model/tool/disk operations, and approval for material work. Source: `constitution/constitution.toml:302-337`.

The character must therefore never animate an action before the signal envelope says it is allowed. Anticipation is acceptable; simulated completion is not.

### 9.4 Signed runtime contact lens

**EXISTS.** `constitution/contact_lenses/local_runtime.toml` is a signed capability/surface scope, not a character perspective. It lists approved routes and dispatch surfaces and carries signer, approval date, and validity period. Source: `constitution/contact_lenses/local_runtime.toml:1-91`.

**DO NOT ANIMATE:** signer identity, key/signature material, route list, or approval validity as personality.

Safe derived state is only:

- `contactLensValid: boolean`
- `surfaceAuthorized: boolean`
- `routeInScope: boolean`

Even these are governance inputs, not visual authority. Invalid/out-of-scope should produce a neutral stop, not alarm theater.

### 9.5 Conversational perspective lens

**EXISTS and distinct from the signed contact lens.** The conversational lens has `id`, `title`, `voice_character`, and summary, rotates with topical fit and freshness, and persists recent selection history. Source: `crates/prism-cdiss-cli/src/lens.rs:16-22`, `54-87`, `138-185`.

However, an active persona suppresses rotating lens overlays because both compete for the “how do I sound” slot. Source: `crates/prism-cdiss-cli/src/main.rs:2612-2618`.

Animation should therefore prioritize active persona. A conversational lens can add a tiny style modifier only for the base voice and only from an allow-listed category such as `practical`, `warm`, `forensic`, or `playful`.

## 10. Provider and route signals

### 10.1 Provider state

**EXISTS.** Runtime status exposes chat provider/model, governance provider/model, and embedder provider. Source: `crates/prism-cdiss-cli/src/web.rs:3181-3204`.

Safe use: diagnostics and latency adaptation only. Provider identity must not change character personality, trustworthiness, intelligence, authority, or emotional appearance.

### 10.2 Route readiness

**EXISTS.** Route capability includes route ID, risk level, write mode, approval requirement, and availability. Projection context also includes confirmed agreements, chamber level, pending approvals, and validated identity. Source: `crates/prism-cdiss-core/src/cdiss.rs:426-455`.

The thread inspector may expose a safe `lastActionableRoute` with route ID, display name, authority class, source, and revision expiry. Source: `crates/prism-cdiss-core/src/state/thread.rs:123-138`; web projection at `crates/prism-cdiss-cli/src/web.rs:3980-3982`.

Safe animation mapping is route-family preparation only after allow-listing:

- read/search -> inspect/read gesture
- draft/create -> writing/casting preparation
- speak -> mouth/speech channel
- move/navigation -> locomotion
- external/material -> wait until approved

Never animate route execution from route recognition, semantic similarity, readiness, or `lastActionableRoute` alone.

## 11. Signal catalog for the Python adapter

| Signal | Status | Producer | Type/cadence | Provenance/confidence | Governance/privacy | Safe animation use |
|---|---|---|---|---|---|---|
| turn stage | EXISTS | `web.rs::stage_event` | categorical, stage entry/exit | deterministic lifecycle | safe labels only | clip/state-machine phase |
| stage mouth | EXISTS | `web.rs::stage_meta` | float per stage | authored preset, not audio | no speech content | low-amplitude mouth idle |
| stage energy | EXISTS | `web.rs::stage_meta` | float per stage | authored preset | clamp 0..1 | speed/amplitude blend |
| terminal verdict | EXISTS | `TurnOutcome` / reply payload | string once/turn | governed outcome | allow-list | clarify/wait/answer family |
| terminal confidence | EXISTS | reply payload | float once/turn | model/governance result | not authority | subtle settle only |
| active persona | EXISTS | runtime/persona APIs | ID/name on change/poll | runtime config | allow-list canonical IDs | animation profile |
| persona temperament | EXISTS internally | persona TOML/parser | config at persona load | authored profile | do not expose prose | bounded style modifiers |
| expression snapshot | EXISTS | `CdissExpressionPlan::snapshot` | object once/turn | product metrics | safe scalars/booleans only | expression blend/clamps |
| serious mode | EXISTS | CDISS plan/runtime status | boolean per turn/poll | deterministic threshold | safety priority | suppress flourishes/comedy |
| approval posture | EXISTS | runtime status/stage | enum per turn/poll | action-space projection | never infer approval | hard wait/neutral stop |
| memory allowed | EXISTS | CDISS plan/runtime status | boolean per turn | state threshold | no content | permit subtle callback gesture |
| backstory allowed | EXISTS | CDISS plan/runtime status | boolean per turn | stricter threshold | no fragments | permit character-color motion |
| recall selected count/kinds | EXISTS in diagnostic | memory test | query diagnostic | CDISS selected | strip query/snippets/IDs | search-to-recognition transition |
| relationship stage | DERIVED | persona memory count | changes after topic close | count bands | strip count/text | familiarity timing only |
| new topic | EXISTS | reply payload | boolean once/turn | topic cue/embedding drift | no topic text | reorientation transition |
| KB result count/match types | EXISTS | KB query report | per query | retrieval pipeline | strip content and pointers | reading/search gesture |
| KB retrieval score | EXISTS | KB result | float per hit | ranking score, not truth | never portray certainty | tiny search-strength blend |
| self-knowledge used | PROPOSED | retrieval pipeline | boolean per turn | would need explicit producer | do not infer from text | product-explanation gesture |
| contact lens valid/in scope | DERIVED | signed scope verifier | config/route change | cryptographic verification | strip signer/key/routes | neutral allow/stop gate |
| audit healthy | EXISTS | runtime status | boolean/poll | ledger persistence health | diagnostics only | neutral alert clamp |
| provider labels | EXISTS | runtime status | config/poll | runtime config | no keys/endpoints | diagnostics only |
| raw embeddings/vectors | EXISTS internally | CDISS/memory/KB | high-dimensional | internal state | DO NOT EXPORT | none |
| raw memory/backstory/thread text | EXISTS internally | SQLite/thread/persona | sensitive content | user/private/persona data | DO NOT EXPORT | none |
| gate rationale/hidden deliberation | EXISTS internally | governance | sensitive/internal | policy/model internals | DO NOT EXPORT | none |

## 12. Proposed versioned Python signal envelope

**PROPOSED.** This contract does not currently exist. Rust should emit only sanitized source fields; a Python-side adapter should validate, normalize, expire, and map them into ASCILINE animation intent.

```json
{
  "schemaVersion": "wizardjoe.animation-signal.v1",
  "envelopeId": "uuid",
  "sequence": 184,
  "emittedAt": "2026-07-13T07:12:31.442Z",
  "expiresAt": "2026-07-13T07:12:36.442Z",
  "source": {
    "system": "prism-gt",
    "surface": "web_local",
    "transport": "sse",
    "eventType": "stage",
    "eventId": null,
    "producerVersion": "unknown-local-checkout",
    "projectionDegraded": false
  },
  "identity": {
    "personaId": "elara-voss",
    "displayName": "Elara Voss",
    "profileVersion": "1",
    "motionProfile": "warm_architect",
    "shapeHint": "dodecahedron"
  },
  "lifecycle": {
    "turnId": null,
    "threadRevision": null,
    "stage": "understanding",
    "stageStatus": "active",
    "startedAtMs": 32,
    "durationMs": null,
    "newTopic": false
  },
  "expression": {
    "preset": "focused",
    "energy": 0.42,
    "mouth": 0.08,
    "clarity": null,
    "urgency": null,
    "seriousMode": false,
    "comedyAllowed": false,
    "confidence": null
  },
  "continuity": {
    "hasContinuity": true,
    "memoryAllowed": false,
    "backstoryAllowed": false,
    "historyPresent": false,
    "relationshipStage": "new",
    "recallSelectedCount": 0,
    "recallKinds": []
  },
  "knowledge": {
    "queryActive": false,
    "resultCount": 0,
    "matchTypes": [],
    "topScore": null,
    "vectorAvailable": null,
    "accessGateApplied": true,
    "selfKnowledgeContextUsed": null
  },
  "governance": {
    "status": "stable",
    "approvalPosture": "chat_only",
    "pendingApproval": false,
    "blocked": false,
    "forceClarification": false,
    "projectionDegraded": false,
    "auditHealthy": true,
    "contactLensValid": null,
    "routeInScope": null
  },
  "intent": {
    "locomotion": "idle",
    "gesture": "listen",
    "transition": "settle_to_focus",
    "canFlourish": false,
    "mustHold": false
  },
  "provenance": {
    "fields": {
      "lifecycle.stage": "prism_sse.stageId",
      "expression.energy": "prism_sse.energy",
      "expression.preset": "prism_sse.expression"
    },
    "contentStripped": true,
    "rawVectorsStripped": true,
    "authorityInvariant": "continuity_never_grants_approval"
  }
}
```

### 12.1 Envelope requirements

1. Reject unknown `schemaVersion` major versions.
2. Require monotonically increasing sequence per source connection.
3. Expire stage and locomotion intents; never leave the character stuck in a stale active state.
4. Allow-list persona IDs, stage IDs, expression IDs, verdicts, match types, and governance statuses.
5. Clamp every numeric value to a documented range and reject NaN/infinity.
6. Strip all user text, assistant text, memory text, backstory, KB content, prompts, source pointers, paths, credentials, hashes, and approval payloads.
7. Preserve null as “unknown”; do not convert missing confidence or state into zero confidence.
8. Give governance clamps priority over persona and expressive motion.
9. Require explicit approval-resolution state before any material-action animation.
10. Log only envelope metadata, never stripped content.

## 13. Deterministic animation-intent precedence

The Python adapter should resolve competing signals in this order:

1. connection loss / expired envelope -> neutral idle
2. invariant violation / blocked -> safety halt
3. waiting approval -> stationary wait
4. serious mode -> suppress comedy, mythic flourish, broad flight, and exaggerated reactions
5. clarification -> question/listen
6. active lifecycle stage -> stage clip
7. speaking/audio channel -> mouth and speech gesture overlay
8. explicit remote locomotion -> walk/fly/run clip compatible with governance state
9. persona profile -> timing and gesture style modifiers
10. continuity/knowledge hints -> optional low-amplitude secondary gesture
11. baseline idle

Remote movement remains an ASCILINE control-plane concern. Prism semantic signals may modify how Wizard Joe moves, but they must not seize positional control from the user.

## 14. Required privacy and anti-overstatement tests

Before connecting Prism to the avatar, add tests proving:

1. No prompt, reply, memory snippet, backstory fragment, KB chunk, source title/path/pointer, approval question/payload, model key, endpoint, signature, or raw vector can appear in an envelope.
2. Memory relevance alone cannot set readiness, execution, approval, or completion animation.
3. KB retrieval score cannot select a certainty, victory, authority, or completion pose.
4. `authorityLevel` cannot alter size, height, brightness, dominance, or command gestures.
5. `approvalRequired`, `blocked`, and `invariantViolation` always suppress execution and flourish.
6. Approval denial returns neutrally without disappointment, pleading, or guilt.
7. Serious mode suppresses comedy and mythic motion regardless of persona.
8. Projection degradation reduces expressive confidence and never increases activity.
9. Unknown persona/stage/expression values fail closed to neutral idle.
10. Stale and out-of-order envelopes are ignored.
11. Reconnection cannot replay a completed action.
12. Persona switch closes the previous animation profile cleanly and does not carry its private continuity into the new profile.
13. Relationship stage changes timing only and never produces intimacy-coded motion.
14. The adapter functions with all text fields replaced by redacted placeholders.
15. Python port `8765` remains the sole animation runtime and delivery surface.

## 15. Known unknowns and proposed work

The timeboxed inspection did not establish the following as current serialized contracts:

- **PROPOSED:** a dedicated Rust-to-Python animation endpoint or stream.
- **PROPOSED:** `relationshipStage` as an API field.
- **PROPOSED:** `selfKnowledgeContextUsed` in terminal/runtime telemetry.
- **PROPOSED:** explicit `knowledgeQueryStarted/Completed` lifecycle events.
- **PROPOSED:** contact-lens verification result in the web read model.
- **PROPOSED:** generic approval resolution events for all routes on the web surface.
- **UNKNOWN:** a stable server-generated SSE event ID suitable for resume. The inspected stage event sets no explicit event ID.
- **UNKNOWN:** an externally stable producer semantic version for the local checkout. The envelope must not invent one.
- **UNKNOWN:** whether every KB authority/access label is suitable for cross-runtime export. Use an allow-list after a dedicated governance review.
- **UNKNOWN:** whether relationship-stage counts are intended as a public product surface. Prefer a boolean or coarse band only after approval.
- **UNKNOWN:** whether provider latency telemetry exists elsewhere. Do not infer it from stage duration.

These unknowns must remain null or absent. They must not be guessed from text, UI labels, timing, or model behavior.

## 16. Recommended implementation boundary

The safe architecture is:

```text
Prism GT Rust/CDISS
  -> existing sanitized SSE + read-model APIs
  -> narrow signal collector
  -> schema validation + text/content stripping
  -> versioned animation-signal envelope
  -> ASCILINE Python adapter on port 8765
  -> animation intent arbiter
  -> locomotion / gesture / expression / mouth channels
  -> direct-cell compositor
```

The collector should prefer push events for lifecycle and use read-model pulls only at connection, terminal turn, persona change, and bounded recovery. The Python arbiter should own blending, interruption, transition graph selection, remote-control priority, dead reckoning, and stale-signal recovery.

This preserves the useful intelligence in Prism GT while keeping animation deterministic, testable, private, and subordinate to user control.

## 17. Source index

Primary local sources used:

- `crates/prism-cdiss-cli/src/persona.rs:6-53`, `57-83`, `182-303`, `359-457`, `495-624`
- `personas/elara-voss/persona.toml:1-112`
- `personas/prism/persona.toml:1-135`
- `personas/sabine/persona.toml:1-143`
- `personas/elia/persona.toml:1-145`
- `src/lib/persona-expression.js:7-87`
- `src/pages/PrismHero/prismShapeState.js:1-201`
- `src/lib/sse-cdiss.js:5-45`
- `crates/prism-cdiss-core/src/cdiss.rs:163-254`, `426-565`, `569-704`, `798-915`, `917-1123`, `1307-1430`
- `crates/prism-cdiss-core/src/state/thread.rs:25-138`
- `crates/prism-cdiss-cli/src/main.rs:171-340`, `1697-1863`, `2110-2262`, `2520-2789`, `2880-3146`, `4103-4255`, `4562-4579`
- `crates/prism-cdiss-cli/src/memory.rs:1-52`, `54-157`, `245-353`, `368-536`
- `crates/prism-cdiss-cli/src/conversation.rs:1-171`
- `crates/prism-cdiss-cli/src/knowledge_base.rs:108-232`, `1530-1797`, `4435-4502`, `4627-4660`
- `crates/prism-cdiss-cli/src/self_knowledge.rs:5-30`, `51-127`
- `crates/prism-cdiss-cli/src/web.rs:275-370`, `3114-3308`, `3640-4059`, `4343-4474`, `5477-5513`, `5855-6147`
- `crates/prism-cdiss-cli/src/lens.rs:1-195`
- `constitution/constitution.toml:1-115`, `302-385`
- `constitution/contact_lenses/local_runtime.toml:1-91`
