# Role 8 Research: Performance Planning and LLM Systems

Date: 2026-07-13

## Scope and repository snapshot

This report audits the current implementation and proposes the planning contract for the Wizard Joe Audiobook Performance Engine and PrismGT Media Connector. It covers deterministic and editable narrative scores, optional LLM enrichment, prompt and cache design, semantic retrieval, offline behavior, governance, and reproducibility. It does not propose live inference during playback and does not treat model output as trusted control authority.

Audited revisions:

- Python: `WizardJoeAvatar-python` at `7781a67c97bfbfa16a64d5b9fb12bdf74bd4c032` on `codex/audiobook-performance-engine`.
- PrismGT: `prism-geometry-talk-current` at `0ce9f9bae665b1415cd776e4d6c9ee23565936ac` on `desktop/prism-gt-influence-integrated`.

The supplied research brief requires precomputation before playback, audio as the authoritative clock, deterministic behavior for an accepted score and fixed inputs, human editability, explicit fallback, privacy controls, and no automatic trust in LLM output. Those constraints are sound and should be treated as product acceptance requirements rather than implementation suggestions.

## Executive finding

The two repositories already contain several strong building blocks, but no performance planner or durable score contract exists today.

- Python has a deterministic 60 Hz, exact-tick, single-writer runtime with stable state hashing, replay events, bounded command ordering, deduplication, and acknowledgements (`wizard_avatar/runtime.py:27-67`, `wizard_avatar/runtime.py:176-275`, `wizard_avatar/commanding.py:11-47`, `wizard_avatar/commanding.py:254-425`).
- Python has a strict character package and a large animation graph containing capabilities, clip durations, markers, interrupt policies, nodes, and transitions (`wizard_avatar/character_package.py:30-88`, `wizard_avatar/definitions/wizard_joe_character_package.json:1-17`, `wizard_avatar/definitions/reference_avatar_animation_graph_v2.json:1010-3058`, `wizard_avatar/definitions/reference_avatar_animation_graph_v2.json:3060-3630`).
- PrismGT has an audiobook store, timed captions/alignment for generated speech, an HTML audio element whose `currentTime` drives the analyzer, provider dispatch permits, request/response audit hashes, local/OpenAI-compatible/Anthropic JSON model adapters, and vector plus lexical indexing surfaces (`crates/prism-cdiss-cli/src/audiobooks.rs:57-117`, `crates/prism-cdiss-cli/src/audiobooks.rs:242-470`, `src/pages/PrismDodecahedron/musicMotion.js:163-392`, `crates/prism-cdiss-core/src/models/json_model.rs:34-129`).
- Neither repository stores a media content hash, transcript/alignment version, character graph hash, score version, prompt bundle, provider revision, retrieved evidence, edit overlay, or validation report as one reproducible planning identity.
- PrismGT's current model adapters return a generic JSON object rather than a caller-supplied strict schema. Its Anthropic adapter still uses JSON-only prompting and prose stripping even though Anthropic now offers schema-constrained outputs on supported models (`crates/prism-cdiss-core/src/models/openai_compat.rs:25-129`, `crates/prism-cdiss-core/src/models/anthropic.rs:1-13`, `crates/prism-cdiss-core/src/models/anthropic.rs:133-197`).
- PrismGT's active CLI uses `MockEmbedder`, explicitly degrading file search to lexical hash space. The index records dimension but not model, revision, task prefix, or normalization version (`crates/prism-cdiss-cli/src/main.rs:1586-1597`, `crates/prism-cdiss-cli/src/main.rs:1978-1993`, `crates/prism-cdiss-core/src/index/file_index.rs:181-225`).

The recommended architecture is therefore a deterministic compiler pipeline with optional LLM candidate-generation passes. The accepted, compiled score is the playback input. A model response is never the playback input.

## Current capabilities and gaps

| Area | Confirmed capability | Gap or risk | Required response |
|---|---|---|---|
| Runtime determinism | Python canonicalizes state, hashes snapshots, advances exact ticks, and records command acknowledgements (`wizard_avatar/runtime.py:27-67`, `wizard_avatar/runtime.py:176-275`). | There is no score identity in replay records and no mapping from media time to score revision. | Include score, media, transcript, and compiler hashes in the playback session and replay log. |
| Command scheduling | Commands are idempotent, ordered, bounded to 1,024 queued entries, and rejected beyond 120 future ticks, or about two seconds (`wizard_avatar/commanding.py:11-15`, `wizard_avatar/commanding.py:306-399`). | A chapter or book cannot be loaded into this queue in advance. Queue overflow or horizon rejection would be likely. | Keep the score outside the inbox. A connector dispatches through a rolling lookahead no greater than the current horizon and verifies every acknowledgement. |
| Character truth | Package loading rejects unknown fields and verifies pose and graph references. The graph carries durations, markers, interrupt policies, nodes, and transitions (`wizard_avatar/character_package.py:38-87`, `wizard_avatar/definitions/reference_avatar_animation_graph_v2.json:1010-3630`). | A planner could invent unsupported gestures or ignore transition and interrupt constraints. | LLM passes emit semantic intent only. A deterministic compiler resolves intent against the exact package and graph hashes, or selects an explicit fallback. |
| Prism advisory input | `PrismSignalParser` rejects content, prompt, provider, model, path, hash, command, movement, and authority fields; it intentionally has no URL, socket, callback, or command API (`wizard_avatar/prism_signals.py:145-191`, `wizard_avatar/prism_signals.py:405-477`). | Reusing this signal format for transcripts or score cues would violate its privacy and authority boundary. | Create a separate governed media connector and use the normal command endpoint only after compilation. Keep visual advisory behavior unchanged. |
| Python transport | `/api/avatar/command` accepts `CommandEnvelopeV1` and returns an acknowledgement (`wizard_avatar/server.py:183-195`). | There is no media session, score negotiation, capability query, seek reset, or score cancellation protocol. | Add these as a later connector contract, not as ad hoc fields on visual signals. |
| Media and captions | PrismGT stores generated audio, VTT captions, alignment JSON, and metadata atomically (`crates/prism-cdiss-cli/src/audiobooks.rs:449-470`). | `AudiobookTrack` lacks content hashes and score/transcript state. Studio chapter caching is provider-ID based, not content-addressed (`crates/prism-cdiss-cli/src/audiobooks.rs:75-101`, `crates/prism-cdiss-cli/src/audiobooks.rs:353-447`). | Add a versioned planning sidecar keyed by actual media bytes, normalized transcript/alignment, and character inputs. Do not overload provider IDs as identity. |
| Uploaded media | PrismGT accepts local MP3 files and builds object URLs (`src/lib/media-normalize.js:7-39`). | Track IDs include random UUID/time and browser metadata, not byte content. The same file can acquire a different identity. | Compute a media SHA-256 during ingestion and make ephemeral UI IDs aliases of a stable media record. |
| Manifest generation | The manifest generator recognizes audio, transcript, and caption extensions and emits stable formatted JSON (`scripts/generate_media_manifest.mjs:5-8`, `scripts/generate_media_manifest.mjs:423-443`). | Validation checks only basic IDs, names, URLs, and podcast transcript presence; `generatedAt` changes every run and no content hashes or schema version are present (`scripts/generate_media_manifest.mjs:407-439`). | Version and hash planning inputs separately from display metadata. Exclude volatile timestamps from content identity. |
| Player clock | The audio analyzer reads `audio.currentTime` and `audio.duration` continuously (`src/pages/PrismDodecahedron/musicMotion.js:163-392`). | Timed speech uses `setTimeout` schedules computed from one `currentTime` sample. The observed effects do not explicitly reschedule on seek or playback-rate changes (`src/pages/PrismDodecahedron/index.jsx:2067-2104`, `src/pages/PrismDodecahedron/index.jsx:2972-2985`). | Drive cue state from sampled authoritative media time. On seek, rate change, pause, track change, or discontinuity, cancel pending commands and reconstruct active state. |
| Provider governance | PrismGT scopes model calls with `ModelProviderDispatchPermit` and records route, action, provider, model, policy, prompt, request, response, and error hashes (`crates/prism-cdiss-core/src/models/json_model.rs:94-129`, `crates/prism-cdiss-core/src/models/json_model.rs:245-429`). Audiobook generation already uses this pattern (`crates/prism-cdiss-cli/src/web.rs:6233-6283`). | The permit does not by itself capture planner pass, schema, input spans, consent receipt, model revision, sampling settings, parsed candidate, or validation outcome. | Extend the audit payload for planning while preserving the existing governed dispatch boundary. |
| Structured output | `LocalJsonModel` provides a provider-neutral JSON-object interface (`crates/prism-cdiss-core/src/models/json_model.rs:34-92`). | OpenAI-compatible calls request only JSON object mode; Anthropic uses prompt coaxing. Both omit a per-call schema and structured refusal/finish handling (`crates/prism-cdiss-core/src/models/openai_compat.rs:114-129`, `crates/prism-cdiss-core/src/models/anthropic.rs:133-197`). | Add a planner-specific structured-output contract with native schema use where supported and mandatory local validation everywhere. |
| Retrieval | Prism has deterministic lexical embedders, a swappable embedder trait, and vector index plumbing (`crates/prism-cdiss-core/src/index/embedder.rs:20-125`). | The current CLI uses a mock hash embedder; the cache keys only raw text; the DB guards dimension only (`crates/prism-cdiss-core/src/index/embedder.rs:182-228`, `crates/prism-cdiss-core/src/index/file_index.rs:181-225`). | Use a dedicated performance index with a complete embedder fingerprint and purpose-specific beat documents. Never silently reuse an index across model or prefix changes. |

## Recommended artifact model

Use three immutable artifacts and one edit layer. This separation makes model output inspectable without confusing it with executable behavior.

1. `analysis.bundle.json`: evidence-grounded book, chapter, and beat analysis. It may contain model-generated candidates, but no executable clip or command IDs.
2. `performance-score.json`: the human-readable semantic score. It contains timed intents, source evidence, confidence components, and explicit stillness.
3. `compiled-score.json`: character-specific resolution of semantic cues to known graph nodes/clips/actions, transitions, and fallbacks. It is produced only by deterministic code.
4. `score-edits.json`: an append-only patch layer referencing stable cue IDs. Regeneration creates a new base score and rebases or reports conflicts; it never silently overwrites human edits.

The accepted score revision is the tuple of the base score hash, ordered edit-set hash, compiler version, package hash, graph hash, and validation-policy hash. Playback must reject a compiled score whose declared inputs do not match the selected media and loaded character.

This design fits the current code: the strict Python package loader and graph are appropriate compiler inputs, while the existing runtime and command envelope are appropriate dispatch targets. Neither should become a document store or LLM host.

### Root score fields

The schema should use JSON Schema Draft 2020-12, reject unknown properties, and be checked by both structural and application-level semantic validators. JSON Schema defines structural vocabulary, but timeline reachability and narrative consistency remain application rules ([JSON Schema Core](https://json-schema.org/draft/2020-12/json-schema-core.html), [JSON Schema Validation](https://json-schema.org/draft/2020-12/json-schema-validation.html)).

Required root fields:

| Field | Purpose |
|---|---|
| `schema_version` | Exact score schema version, not merely a major family. |
| `score_id`, `revision`, `status` | Stable logical identity, immutable revision, and `candidate`, `accepted`, `rejected`, or `fallback`. |
| `media` | SHA-256 of bytes, duration in integer milliseconds, MIME type, channel/sample metadata when known, and non-authoritative display aliases. |
| `transcript` | SHA-256 of normalized transcript, transcript schema/version, language, alignment hash, alignment provenance, and timing coverage. |
| `character` | Character ID, package SHA-256, pose-library SHA-256, animation-graph SHA-256, and capability digest. |
| `planner` | Pipeline version, prompt-bundle hash, pass graph hash, provider/model/revision, local/cloud classification, sampling settings, seed when supported, backend build, and schema hash. |
| `tracks` | Ordered semantic tracks with explicit exclusivity and blend rules. |
| `provenance` | Input entities, pass activities, retrieved evidence IDs/scores, request/response hashes, validator report hash, and parent score/edit hashes. |
| `validation` | Validator version, timestamp excluded from content identity, errors, warnings, density metrics, and acceptance decision. |

Use integer milliseconds for persisted media time because Prism's caption/alignment surfaces already use timed text and Rust `u64`-style millisecond boundaries, while the browser exposes floating-point seconds. Conversion to Python ticks should occur at dispatch with one specified rounding rule. Do not persist binary floating-point timestamps as identity-bearing values.

### Track model

Recommended tracks:

- `narrative_state`: chapter, scene, beat, tension, energy, valence, focus, and narrator stance. This is analysis, not an animation request.
- `body_base`: one exclusive full-body semantic state at a time, including `still`.
- `gesture`: sparse, bounded upper-body intents that may overlay a compatible base.
- `face`: expression intents with attack, hold, and release.
- `gaze`: target class and intensity, never an arbitrary external coordinate from an LLM.
- `speech`: narration-active state and mouth-shape policy; fine lip motion remains audio/alignment driven.
- `transition`: entrances, exits, resets, and seek checkpoints.
- `effects`: optional approved visual effects, kept separate from body authority.

Each track declares `exclusive`, maximum simultaneous cues, minimum gap, maximum cue density, default fallback, and whether silence means hold, clear, or neutral. This prevents ambiguous absence and makes stillness a deliberate score decision.

### Cue contract

Every semantic cue should contain:

```json
{
  "cue_id": "chapter-003.beat-014.gesture-001",
  "track": "gesture",
  "start_ms": 418220,
  "end_ms": 420100,
  "intent": "explain_emphasis",
  "source_spans": ["chapter-003.span-087"],
  "evidence": ["beat-014", "retrieval:motif-002"],
  "confidence": {
    "alignment": 0.98,
    "evidence_coverage": 0.91,
    "planner_consistency": 0.74,
    "self_reported": 0.62
  },
  "priority": 40,
  "capability_requirements": ["upper_body_actions"],
  "interrupt_policy": "at_marker",
  "fallback_intents": ["small_acknowledge", "still"],
  "manual": {"locked": false, "disabled": false},
  "generation": {"pass_id": "beat-enrichment-v1", "candidate_id": "..."}
}
```

`self_reported` model confidence must never be used as the acceptance gate. Alignment confidence, evidence coverage, deterministic compiler validity, cross-pass agreement, and human review status are separate dimensions. A low-confidence planner may emit `no_decision`; it must not fill uncertainty with motion.

The compiled cue adds only known values such as `resolved_node_id`, `resolved_clip_id`, `transition_id`, `duration_ticks`, marker policy, and the chosen fallback. The compiler must fail closed if any reference is absent from the exact graph revision.

### Structural and semantic validation

Validation is an ordered gate, not a retry prompt:

1. Parse and enforce the exact JSON Schema with unknown fields rejected.
2. Verify every declared input hash and schema version.
3. Verify cue IDs, source-span references, ordering, integer time bounds, and media duration.
4. Reject forbidden overlaps on exclusive tracks and enforce density, minimum-gap, and stillness budgets.
5. Resolve semantic intent only through a versioned allowlist derived from the character package and animation graph.
6. Verify capability requirements, graph reachability, transition duration, interrupt windows, and fallback chains.
7. Simulate chapter boundaries, rapid adjacent cues, seek reconstruction, pause/resume, and end-of-media cleanup.
8. Produce a deterministic validation report. Only an `accepted` compiled score can be selected for playback.

Schema-constrained decoding reduces malformed output but does not remove these gates. OpenAI distinguishes JSON mode from schema adherence and requires handling refusals or incomplete responses ([OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)). Anthropic similarly documents refusal and token-limit cases that may not match the schema ([Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)). Ollama recommends schema reuse and low temperature but still requires application validation ([Ollama Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs)).

## Planning pipeline

The pipeline should be a dependency graph of small, cacheable passes. Whole-book prompting should not produce low-level movement. Research on long-context models shows that relevant information can be used less reliably when it appears in the middle of long inputs, supporting hierarchical passes over one monolithic prompt ([Lost in the Middle](https://arxiv.org/abs/2307.03172)).

### Pass 0: deterministic ingestion

- Hash media bytes.
- Normalize and hash transcript/alignment without destroying source offsets.
- Segment chapters, paragraphs, sentences, pauses, and aligned timing deterministically.
- Extract deterministic audio/timing features such as speech activity, silence, pause length, energy envelope, and alignment coverage.
- Hash the character package, graph, prompt bundle, schemas, and validator policy.

No LLM is needed or allowed in this pass. A changed input must be visible before any cache lookup.

### Pass 1: book map

Optional LLM output: book-level characters, motifs, tone ranges, narrator stance, recurring locations, and chapter relationships. Each assertion cites source span IDs. The pass may summarize but may not create score cues.

For large books, use deterministic rolling chapter summaries and a final reducer. Persist every intermediate and its evidence. Do not repeatedly resend the full book.

### Pass 2: chapter map

Optional LLM output: scene boundaries, narrative function, local arc, speaker/narrator changes, and beat candidates. Input includes the chapter text, adjacent chapter summaries, relevant book-map items, and exact timing coverage.

### Pass 3: beat analysis

Optional LLM output: a constrained semantic proposal for emotion, energy, focus, gesture opportunity, and explicit stillness. The model selects from semantic enums or `no_decision`; it does not select graph clips or issue commands.

### Pass 4: deterministic score assembly

Merge accepted beat candidates with deterministic timing/audio features. Apply track density, cooldown, precedence, contradiction, and stillness rules. Resolve ties with stable ordering and a seed derived from the cache key, never wall-clock time.

### Pass 5: deterministic character compilation

Resolve semantic intents against the exact capability package and animation graph. Calculate transitions and interrupt behavior. Produce explicit fallbacks. This pass must be byte-stable for canonical identical inputs.

### Pass 6: critic and repair suggestions

An optional LLM critic may identify unsupported, repetitive, tonally inconsistent, or overactive sections. It receives the semantic score and validator findings, not command authority. It emits proposed patch operations against cue IDs. Deterministic validation decides whether a patch can become a new candidate revision.

### Pass 7: acceptance and publish

Run validators and simulations, apply locked human edits, calculate canonical hashes, and atomically publish the accepted artifacts. Playback sees only accepted artifacts.

## Prompt architecture

Each pass should have a versioned prompt bundle rather than an inline string embedded in code. The bundle contains:

- `pass_id` and prompt semantic version.
- Static system rules and authority limits.
- The exact output schema and schema hash.
- Allowed enums and a capability summary hash.
- Positive and negative examples with stable IDs.
- A variable data envelope containing span-addressed transcript and features.
- A declaration that transcript, metadata, retrieved text, and prior model text are untrusted data, not instructions.
- A required `no_decision` path and evidence requirements.

Put stable instructions and examples before variable content. This also aligns with provider prompt-cache prefix behavior, but provider prompt caching is only a latency/cost optimization. OpenAI requires exact prefix matches and recommends static content first ([OpenAI Prompt Caching](https://developers.openai.com/api/docs/guides/prompt-caching)); Anthropic similarly caches prompt prefixes at explicit breakpoints ([Anthropic Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)). Neither cache proves artifact reproducibility.

The transcript may contain adversarial text such as instructions to ignore the schema. The planner must have no tools, network browsing, file access, command execution, or runtime authority. Separate instructions from untrusted data, constrain output, validate every field, and use least privilege, consistent with OWASP's prompt-injection guidance ([OWASP Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)).

Provider-specific adaptations belong below the common pass contract:

- Native schema-constrained output when a provider and model support the required schema subset.
- `llama.cpp` JSON Schema or grammar constraints for supported local models; its grammar documentation notes that only a subset of JSON Schema is accepted, so compatibility must be tested at bundle build time ([llama.cpp grammars](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)).
- Ollama `format` schema for local structured output.
- JSON-object prompting only as a degraded adapter, never as equivalent to strict output.

The current `LocalJsonModel.complete_json(messages)` interface cannot express schema, seed, finish/refusal status, usage, request ID, or model revision (`crates/prism-cdiss-core/src/models/json_model.rs:34-92`). A planner-specific result type should carry those fields without breaking conversational callers.

### Cost and quota policy

Cost is an input to planning, not an after-the-fact dashboard number. Before a run, calculate a deterministic pass budget from normalized input size, selected passes, context limits, maximum output tokens, provider pricing snapshot, and retry ceiling. Persist the estimate and pricing-snapshot hash in the run manifest. A hard user budget stops new provider dispatch; it does not discard completed artifacts or prevent deterministic baseline compilation.

Prefer chapter-level cache reuse, batch only independent requests with stable item IDs, and skip critic or cross-book retrieval before sacrificing core beat coverage. Record input/output tokens, cached tokens, latency, attempts, and actual cost per pass when the provider exposes them. Missing usage metadata is `unknown`, never zero. The existing provider audit records request and response hashes but its generic result contract does not expose usage (`crates/prism-cdiss-core/src/models/json_model.rs:34-129`), so this belongs in the planner-specific result and provenance manifest.

## Provenance and cache design

### Canonical identity

Define each pass cache key as the SHA-256 of canonical JSON containing:

```text
pass_id + pass_version
+ ordered dependency artifact hashes
+ normalized input span hashes
+ media/transcript/alignment hashes
+ character package/graph/capability hashes
+ prompt bundle/schema/validator hashes
+ provider/model/model-revision/backend-build
+ sampling parameters/seed/context-window policy
+ retrieval index and retrieved-evidence hashes
+ privacy and policy mode
```

Use one cross-language canonicalization specification. Python already has stable JSON hashing for runtime state (`wizard_avatar/runtime.py:27-67`), but a persisted Python/Rust/JavaScript artifact needs a shared representation. RFC 8785 defines a JSON Canonicalization Scheme for repeatable cryptographic hashing ([RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html)). Either adopt it or freeze and test an equivalent project-specific format across all three languages.

### Cache contents

Store these separately and immutably:

- Provider request manifest with payload hash and redacted metadata.
- Raw provider response bytes and transport metadata.
- Parsed candidate JSON.
- Structural validation report.
- Semantic validation and compiler report.
- Accepted artifact.
- Error record with class and bounded retry policy.

Write to a temporary path and atomically rename after hashing. A retry creates a new attempt record; it never overwrites evidence. Corrupt entries fail hash verification and are quarantined. Error caches need short explicit TTLs; accepted content-addressed artifacts do not.

The existing Prism audit path already hashes provider request/response/error payloads (`crates/prism-cdiss-core/src/models/json_model.rs:346-429`), and the audiobook store already uses atomic writes (`crates/prism-cdiss-cli/src/audiobooks.rs:449-470`). Reuse these patterns while adding pass and artifact relationships.

### Honest reproducibility

Promise two levels, not one:

1. **Artifact reproducibility:** identical normalized inputs and pass identity return the same previously accepted bytes from the content-addressed cache without a provider call. Deterministic compilation of the same accepted analysis is byte-identical.
2. **Generation traceability:** a cache miss records enough inputs to explain and compare a fresh generation, but a hosted or GPU model is not guaranteed to reproduce identical tokens.

Temperature zero and a seed reduce variance but are not a proof. PyTorch explicitly warns that complete reproducibility is not guaranteed across releases, commits, platforms, or devices ([PyTorch Reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html)). Backend revision, quantization, grammar implementation, batching, and provider-side updates must therefore be part of provenance.

Human edits are immutable provenance too. Record author or local actor, time, reason, parent revision, patch operations, and lock state. Keep display timestamps outside content hashes when they are not semantically meaningful.

A lightweight provenance model can use the W3C PROV concepts of entity, activity, and agent without requiring RDF storage: inputs and artifacts are entities, planning passes are activities, and local/provider/model/human actors are agents ([W3C PROV-O](https://www.w3.org/TR/prov-o/)).

## Semantic retrieval inputs

Semantic retrieval is optional and should solve narrow continuity problems, not replace ordered chapter context.

### Documents to index

Create dedicated, immutable planning documents:

- Beat document: `book_id`, `chapter_id`, `beat_id`, `start_ms`, `end_ms`, normalized text, adjacent context summary, speaker/narrator, deterministic audio features, source span hashes, and privacy class.
- Motif document: evidence-backed motif or character-state summary with chapter range and source spans.
- Capability document: semantic intent ID, capability requirements, compatible base states, expected duration, interrupt behavior, fallback intents, and package/graph hash.
- Approved-example document: human-accepted planning example, score revision, intended use, and character compatibility.

Do not embed raw filesystem paths, secrets, provider metadata, or an entire private library into a shared index. Namespace by book and consent boundary. Exact filters for book, character, graph revision, track, locomotion state, and privacy class run before ranking.

### Query strategy

- Direct ordered chapter and beat context remains primary.
- Retrieval supports recurring motifs, a character's prior state, distant setup/payoff, and approved examples.
- Use hybrid lexical/vector retrieval and persist every retrieved ID, rank, score, model fingerprint, and text hash.
- Generate query and document embeddings with the same model, revision, normalization, dimensionality, and task-prefix policy. Ollama's embedding guidance likewise says to use the same embedding model for indexing and querying ([Ollama Embeddings](https://docs.ollama.com/capabilities/embeddings)). Nomic's model card requires different `search_document:` and `search_query:` task prefixes for retrieval roles, so the prefix policy must be identity-bearing ([nomic-embed-text-v1.5 model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5)).

The current Prism `CachingEmbedder` keys only the raw string, and `FileIndex` records only dimension (`crates/prism-cdiss-core/src/index/embedder.rs:182-228`, `crates/prism-cdiss-core/src/index/file_index.rs:181-225`). A performance index must reject or rebuild on any embedder-fingerprint mismatch even when dimensions happen to match. The current CLI's `MockEmbedder` is suitable for deterministic plumbing tests, not semantic narrative retrieval (`crates/prism-cdiss-cli/src/main.rs:1586-1597`).

Retrieval output is evidence, not authority. A retrieved performance example cannot bypass current character capabilities, score density rules, or source grounding.

## Offline and degraded behavior

Planning must complete without an LLM and playback must never require one.

### Deterministic baseline planner

Use transcript alignment and audio features to generate a sparse baseline:

- Neutral/still body base by default.
- Audio-driven speech state while narration is active.
- Chapter-boundary settle and reset cues.
- Pause- and punctuation-derived acknowledgement or thought opportunities with fixed thresholds and cooldowns.
- Conservative face changes from deterministic lexical rules only when evidence is unambiguous.
- No locomotion, world targeting, or elaborate action from heuristic inference.
- Stable tie-breaking from input hashes, never randomness from wall-clock state.

Python's static semantic animation map is an appropriate source of versioned semantic vocabulary (`wizard_avatar/definitions/semantic_animation_map.json`), but the final compiler must still validate against the loaded package and graph.

If transcript or alignment is missing, publish a clearly labeled `fallback` score with audio-reactive narration state, neutral idle, and chapter/media boundaries only. It must not pretend to be narrative understanding.

### Failure ladder

1. Use a compatible accepted score from the exact content-addressed key.
2. If optional enrichment fails, finish with deterministic baseline candidates for affected passes.
3. If a candidate is malformed or semantically invalid, retain raw evidence, reject it, and compile the baseline for that region.
4. If compilation fails after a package/graph change, do not play a stale compiled score; recompile the semantic score or fall back to safe minimal behavior.
5. If the connector loses the media clock or Python acknowledgements, stop future dispatch, issue a safe reset when transport recovers, and reconstruct from the current media position.
6. If no valid artifact exists, audio continues with the avatar neutral. Performance enhancement must never block audiobook playback.

No provider retry may occur from the playback loop. Planning retries are bounded, visible, cancellable, and resumable by pass.

## Playback boundary

The connector should act as a deterministic score player, not a planner.

- PrismGT's audio element is the authoritative clock (`src/pages/PrismDodecahedron/index.jsx:3585-3590`; `src/pages/PrismDodecahedron/musicMotion.js:184-195`).
- Sample media position, paused/ended state, track identity, and a monotonic observation time. Detect backward/forward discontinuities rather than assuming continuous progress.
- Convert score milliseconds to Python ticks only inside the connector using a specified rounding rule and current synchronization epoch.
- Dispatch within a rolling window below Python's 120-tick future limit (`wizard_avatar/commanding.py:360-368`). Do not preload a chapter into the 1,024-entry inbox.
- Derive command IDs from score revision, cue ID, synchronization epoch, and resolved action so retries are idempotent.
- Verify `accepted` and `applied` acknowledgements and expose rejection/late/dropped metrics (`wizard_avatar/commanding.py:254-295`).
- On seek, change synchronization epoch, clear connector pending state, calculate the score state at the new media position, and send the minimal reset plus active-state command set.
- On pause, stop dispatching future cues. On resume, re-anchor against current audio time. On end or track change, reset score-owned overlays.
- User input retains higher authority than performance cues. The existing priority table gives user actions precedence over demo/visual signal classes (`wizard_avatar/commanding.py:60-65`, `wizard_avatar/commanding.py:298-303`); the new source/priority class must preserve that policy.

Do not route this through `PrismSignalParser`. That adapter is deliberately content-free, advisory-only, and denied movement/authority fields (`wizard_avatar/prism_signals.py:161-191`, `wizard_avatar/prism_signals.py:405-411`).

## Privacy and governance

Local deterministic planning is the default. External enrichment is opt-in per media item and pass class.

Before cloud dispatch, show and record:

- Provider, model, endpoint class, and local/cloud status.
- Exact chapter/span scope and data categories, with a preview where practical.
- Whether transcript, summaries, alignment, or retrieval evidence leaves the machine.
- Retention policy information supplied by the provider configuration.
- Estimated token/cost range and cancellation behavior.

Create a consent receipt keyed by media hash, provider/model, pass ID, payload class, and policy version. Consent for one chapter or provider must not silently authorize another. Revocation prevents future dispatch but does not falsify prior provenance.

Route all provider calls through Prism's existing dispatch permit and audit path. The audiobook generation handler demonstrates the current policy/prompt-hash gate (`crates/prism-cdiss-cli/src/web.rs:6233-6283`). Extend it with pass ID, schema hash, consent receipt hash, input-span hashes, and validation outcome. Do not put transcript text in routine logs; retain encrypted content only in the user-controlled artifact store when configured.

The planner model receives no tools and has no command or network authority. The deterministic compiler is the only bridge from semantic proposal to known character behavior. This satisfies least privilege and limits prompt-injection impact. Use NIST AI RMF guidance for documented testing, content provenance, human oversight, and incident handling ([NIST AI RMF Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)).

## Failure modes and controls

| Failure mode | Consequence | Required control |
|---|---|---|
| Schema-valid narrative nonsense | Wrong tone or unsupported interpretation despite valid JSON. | Evidence spans, `no_decision`, semantic validators, sparse defaults, critic suggestions, and human review. |
| Hallucinated capabilities | Unknown clip or impossible movement reaches runtime. | Models emit semantic enums only; deterministic graph compiler and fallback chain. |
| Cue overload | Constant motion, distraction, queue pressure. | Per-track density, cooldown, simultaneous-cue limits, stillness budget, and stress tests. |
| Contradictory tracks | Face/body/gaze or adjacent gestures conflict. | Explicit exclusivity/blend matrix, precedence, graph simulation, and deterministic repair. |
| Prompt injection in book text | Text attempts to alter system rules or request commands. | Untrusted-data envelope, no tools, strict output, allowlists, validation, and no direct runtime path. |
| False determinism claim | Fresh generation differs despite identical visible settings. | Promise byte identity on accepted cache hits and deterministic compilation; record backend/model revision for misses. |
| Cache collision or poisoning | Wrong score reused for different media/model/graph. | Canonical complete keys, content verification, atomic writes, immutable entries, and quarantine on mismatch. |
| Stale compiled score | Character graph changed after score generation. | Package and graph hashes in identity; reject mismatch and recompile semantic score. |
| Retrieval contamination | Another book or private source changes a chapter plan. | Book/consent namespaces, exact filters, persisted evidence, and no cross-library retrieval by default. |
| Embedding drift | Same dimension but changed vector space silently reuses index. | Full embedder fingerprint, task-prefix hash, and mandatory rebuild. |
| Partial pass failure | Some chapters have opaque or missing plans. | Pass dependency manifest, resumable state, per-region baseline fallback, and explicit coverage report. |
| Human edits lost | Regeneration overwrites authored performance. | Immutable patch layer, stable cue IDs, locks, rebase/conflict report, and parent hashes. |
| Seek/rate discontinuity | Timers fire cues at the wrong narrative moment. | Clock-sampled state evaluation, synchronization epochs, cancellation, and seek reconstruction. |
| Provider privacy breach | Transcript leaves the machine without informed consent. | Local default, scoped receipt, governed dispatch, redacted audit, and deny-by-default external calls. |

## Acceptance criteria

The feature is not ready until all of these are automated or demonstrably inspectable.

1. **Schema fixtures:** Valid score fixtures pass; unknown fields, floats for time, invalid enums, dangling span IDs, and missing provenance fail with stable error codes.
2. **Semantic fixtures:** Exclusive overlaps, excessive density, unsupported capabilities, unreachable transitions, invalid interrupt windows, media overrun, and missing fallbacks fail deterministically.
3. **Canonical hash parity:** Python, Rust, and JavaScript calculate the same artifact hash for a shared fixture, including Unicode and numeric edge cases.
4. **Cache-hit determinism:** Running the same accepted pass identity twice makes zero provider calls and returns byte-identical artifact and validation hashes.
5. **Selective invalidation:** Changing one chapter transcript invalidates that chapter and dependent book/critic outputs, but not unrelated chapter candidates. Changing the graph invalidates compilation, not transcript analysis.
6. **Generation trace:** Every model candidate records prompt/schema/input/request/response hashes, provider/model/revision, sampling settings, stop/refusal state, attempt ID, and validator result.
7. **Structured-output degradation:** Native schema, local grammar, JSON-only, refusal, max-token, malformed JSON, timeout, cancellation, and rate-limit paths each produce a classified result and deterministic fallback.
8. **Prompt-injection fixture:** Transcript instructions cannot add unknown fields, commands, tools, external URLs, unlisted capability IDs, or policy changes to an accepted artifact.
9. **No-model mode:** With all provider networking disabled and empty caches, a book with valid alignment produces an accepted deterministic baseline score and can play.
10. **Missing-transcript mode:** Audio without transcript produces only the labeled safe fallback policy; no narrative claims or locomotion cues appear.
11. **Retrieval fingerprinting:** Reopening an index with a different model, revision, dimension, normalization, or query/document prefix is rejected and requests rebuild. Current mock embeddings are never labeled semantic.
12. **Retrieval provenance:** Every retrieval-influenced candidate identifies the exact document hash, rank, score, filters, and embedder fingerprint; deleting retrieval use yields a plan that remains compilable.
13. **Capability compilation:** Every resolved node, clip, transition, marker, and capability exists in the exact declared package/graph. Unsupported intent resolves through a declared fallback or fails.
14. **Edit preservation:** Regeneration preserves locked cues, rebases compatible edits, reports conflicts, and never mutates the prior accepted revision.
15. **Clock discontinuities:** Seek forward/back, pause/resume, rapid scrubbing, track change, and end-of-media tests cancel stale work and reconstruct the same active state for the same media timestamp.
16. **Bounded dispatch:** A one-hour stress score never submits beyond the 120-tick horizon or overflows the 1,024-command inbox; every dispatched cue has an accepted/applied/rejected terminal record.
17. **Authority:** User controls interrupt or suppress score-owned behavior according to policy, and performance cues cannot acquire movement authority through visual-signal fields.
18. **Privacy deny path:** Without a matching consent receipt, cloud planning makes zero outbound requests. Audit records hashes and decision metadata without plaintext transcript content.
19. **Recovery:** Kill/restart during each planning pass. The next run verifies completed artifacts, resumes from the first missing dependency, and does not overwrite prior attempts or edits.
20. **Reproducibility report:** Export one machine-readable manifest showing which outputs are byte-reproducible cache artifacts and which are traceable but potentially variable fresh model generations.
21. **Budget enforcement:** A fixed low budget stops optional dispatch at the declared boundary, reports complete/partial/baseline coverage, preserves reusable artifacts, and never records unavailable usage as zero cost.

## Recommended implementation order

1. **Contract first:** Define schemas, canonical hashing, immutable revision rules, validation error taxonomy, and cross-language fixtures.
2. **Deterministic baseline:** Build transcript/audio segmentation, sparse baseline scoring, graph compiler, and offline acceptance tests before any LLM integration.
3. **Connector protocol:** Add media session identity, bounded dispatch, acknowledgements, seek epochs, reconstruction, and user-override behavior.
4. **Local optional enrichment:** Add a planner-specific structured-output adapter and one beat-analysis pass using a local model, with raw/parsed/validated artifacts.
5. **Governed cloud adapters:** Extend provider permits, consent receipts, redacted audit, refusal/finish handling, and provider-specific schema capabilities.
6. **Hierarchical planning and edits:** Add book/chapter passes, critic patches, edit overlays, conflict handling, and coverage UI.
7. **Purpose-specific retrieval:** Add retrieval only after embedder fingerprinting, provenance, namespaces, and non-retrieval baselines are measurable.

This order matches the repository's strongest existing properties: Python is already deterministic at runtime, the graph already carries animation constraints, Prism already has provider governance, and Prism's audio element already exposes the authoritative position. The missing work is to connect them through versioned artifacts and validation, not to place a generative model inside the live control loop.

## Primary and professional sources

- JSON Schema Draft 2020-12: [Core](https://json-schema.org/draft/2020-12/json-schema-core.html) and [Validation](https://json-schema.org/draft/2020-12/json-schema-validation.html).
- OpenAI: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and [Prompt Caching](https://developers.openai.com/api/docs/guides/prompt-caching).
- Anthropic: [Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) and [Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).
- Ollama: [Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs) and [Embeddings](https://docs.ollama.com/capabilities/embeddings).
- llama.cpp: [JSON Schema and grammar constraints](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md).
- IETF: [RFC 8785 JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html).
- W3C: [PROV-O provenance ontology](https://www.w3.org/TR/prov-o/).
- NIST: [AI RMF Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence).
- OWASP: [LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).
- Nomic AI: [nomic-embed-text-v1.5 model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5).
- PyTorch: [Reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html).
- Liu et al.: [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172).
