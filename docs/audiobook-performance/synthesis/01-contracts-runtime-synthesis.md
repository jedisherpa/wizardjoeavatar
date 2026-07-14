# Synthesis A: Contracts, Runtime, and Python Slicing

Status: implementation-ready synthesis
Date: 2026-07-13
Scope: contracts, analysis pipelines, deterministic scheduling, character capabilities, cache identity, tests, dependencies, and Python implementation boundaries
Production edits made by this synthesis: none

Inputs reconciled: `CURRENT_STATE_ARCHITECTURE.md`, `PROGRAM_TRACKER.md`, all twelve reports under `research/01-*.md` through `research/12-*.md`, the complete attached implementation brief, and the current Python modules and tests named below. Technical research claims inherit the primary-source citations in the specialist reports; this document decides the implementation contract among them.

## Executive Decision

Keep the existing Python renderer, `WizardFrameHub`, fixed 60 Hz semantic runtime, ordered command inbox, atomic square-cell pose presentation, and PrismGT HTML media element. Add a score-driven performance layer between accepted media-session state and `WizardAvatarController`.

The core runtime rule is:

```text
resolved_state = evaluate(
    accepted_compiled_score,
    authoritative_media_time_ms,
    pinned_character_package,
    accessibility_profile,
    manual_override_state,
)
```

The result at media time `t` must be the same after linear playback, pause/resume, a cold seek, reconnect, or process restart. The scheduler therefore evaluates complete state from score intervals. It does not replay all crossed cues and does not load a chapter into the existing 1,024-entry command inbox.

Use the existing ordered inbox for user/system/API commands and short edge actions. Use a separate authenticated media-session snapshot path for authoritative playback correction. Apply both at a runtime tick boundary, with user and safety authority above score-owned channels.

Persisted score and connector time is integer milliseconds. Offline DSP may preserve integer canonical sample positions. The existing 60 Hz tick is a deterministic presentation/simulation grid, not the media clock. The same rule resolves the time-unit disagreement across the reports without introducing a second playback timeline.

## Confirmed Current Code Boundary

This design is constrained by the code that exists now, not by the desired end state:

- `ProceduralWizardFrameSource` loads one V1 package, creates `WizardAvatarController`, selects a pose, applies face overlays, root-projects it, and renders atomic cells (`wizard_avatar/frame_source.py:47-73`, `89-181`).
- `CharacterPackage` has only eight fields. `load_character_package()` checks path containment, default-pose presence, and graph sample references, then mutates a process-global graph map. It does not invoke strict graph-v2 validation or hash assets (`wizard_avatar/character_package.py:18-94`).
- The package advertises six broad strings, including `speech_overlay`; that does not reveal that speech-safe body layering is absent (`wizard_avatar/definitions/wizard_joe_character_package.json:1-17`).
- The graph parser exposes clips, markers, minimum holds, interruption policy, planted anchors, channels, successors, transitions, and recipes (`wizard_avatar/animation_graph.py:75-212`). Clip evaluation is deterministic integer arithmetic from 60 Hz ticks to 24 fps authored frames (`animation_graph.py:214-294`).
- Production pose selection records a selected transition, immediately swaps the target clip, and resets its tick. It does not execute the transition recipe, hold policy, legal-successor policy, or interrupt gate (`wizard_avatar/pose_selection.py:86-107`).
- Graph/asset failure is caught broadly and silently reduced to legacy pose fallback (`wizard_avatar/pose_selection.py:67-83`). `PoseSample` has no requested value, planted anchor, fallback path, or reason (`pose_selection.py:30-36`).
- Active speech suppresses the production body action (`wizard_avatar/pose_selection.py:141-150`). Speech receives text and duration only, while the controller and reference renderer use timers and a fixed mouth cycle (`wizard_avatar/controller.py:328-339`; `wizard_avatar/frame_source.py:351-362`).
- `WizardState` has no media, score, chapter, cue, scheduler, accessibility, or fallback identity (`wizard_avatar/models.py:123-169`).
- `CommandEnvelopeV1` is strict, idempotent, sequenced, priority-aware, and acknowledged, but has a 120-tick future horizon and no media-session fields (`wizard_avatar/commanding.py:11-47`, `118-242`, `329-399`).
- `OrderedCommandInbox.discard_pending()` can invalidate queued work by command kind (`wizard_avatar/commanding.py:467-480`).
- `AvatarRuntime` is a sound exact-tick single-writer reducer with immutable snapshots, state hashes, and replay evidence, but `advance_to()` follows local monotonic time (`wizard_avatar/runtime.py:176-351`).
- `WizardFrameHub` owns the real reducer boundary and advances it from `perf_counter_ns()`. Its frame loop renders synchronously and drops missed presentation deadlines instead of bursting (`wizard_avatar/stream.py:31-74`, `151-190`, `240-286`).
- The ordered HTTP endpoint is strict. The live WebSocket accepts before origin/auth validation and accepts legacy unversioned commands (`wizard_avatar/server.py:183-240`). It is not the connector transport.
- Current caches are path-keyed `lru_cache` instances for pose JSON, pose maps, canvases, and graphs (`wizard_avatar/reference_avatar.py:38-51`, `150-167`; `wizard_avatar/animation_graph.py:879-889`). Replacing bytes at the same path can retain stale process state.
- The audited art set contains 89 poses, 28 clips, 28 nodes, 47 directed transitions, and 5 transition recipes. Thirty-nine poses are clip samples; fifty are diagnostic-only. All current authored snapshots share root `[36,95]`; no authored cell has a `region` value.

These facts make an atomic-snapshot character adapter, strict package upgrade, media-time evaluator, and visible fallback record mandatory. A generic skeletal rig or arbitrary upper-body pixel blend is not justified by the current assets.

## Conflict Reconciliation

| Conflict in reports | Decision | Reason |
| --- | --- | --- |
| Milliseconds, microseconds, or score ticks as canonical time | Persist integer milliseconds for media, transcript, connector, and score contracts. Preserve integer sample positions inside canonical PCM/DSP artifacts. Derive 60 Hz clip ticks with one specified floor rule. | Current Prism metadata and captions already use millisecond-scale time; acceptance tolerances are tens of milliseconds. Sample indices retain DSP precision without leaking a new runtime clock. |
| Dispatch a rolling queue of score commands versus evaluate full state | Evaluate full desired state every runtime tick; dispatch only user/system commands and rare idempotent edge effects through the ordered inbox. Lookahead is for preload, not future choreography. | It guarantees seek/reconnect equivalence, avoids the 120-tick/1,024-command limits, and prevents stale one-shot bursts. |
| HTTP snapshots versus WebSocket connector | Use authenticated loopback HTTP full-state snapshots for V1. Do not use the current mixed frame/legacy-command WebSocket. | HTTP already fits both stacks, gives an acknowledgement per correction, and avoids the current WebSocket origin/auth gap. |
| One performance score versus analysis/semantic/compiled artifacts | Keep separate immutable `NarrativeScoreV1` or `MusicScoreV1`, portable `PerformanceScoreV1`, character-bound `CompiledPerformanceScoreV1`, and append-only `ScoreEditsV1`. | Model analysis, editorial intent, executable character resolution, and human edits have different invalidation and trust boundaries. |
| LLM chooses clips versus semantic compiler chooses clips | LLM output stops at bounded semantic intent or `no_decision`. Deterministic Python compilation selects package mappings and explicit fallback. | A model must not invent graph IDs or become playback authority. |
| Seeded runtime variation versus persisted takes | Seeded selection is allowed during deterministic compilation only. The accepted compiled score persists the selected mapping/take. Runtime performs no new aesthetic random choice. | Replays and reviews must refer to one approved performance, while the compiler can still avoid repetition. |
| CharacterPackageV2 as a skeleton contract versus current snapshots | V2 defines a renderer-neutral semantic control rig, but Wizard Joe declares `asciline_atomic_snapshot_v1` and semantic remapping, not skeletal retargeting. Skeletal fields are optional and forbidden unless the adapter supports them. | The ten flat anchors are correspondence points, not a joint hierarchy. |
| General channel layering versus speech-safe full-body poses | Current snapshots own the full body. Only declared face/mouth overlays compose independently. Speech-safe acting initially uses curated full-body phrase clips while stationary. | No current cells carry region labels; row-cut blending would be dishonest and visually unsafe. |
| Continuous interpolation versus atomic presentation | Keep whole-pose handoffs. Execute transitions as authored phase sequences, marker gates, holds, and contact-preserving root correction. | Per-cell dissolves produce false anatomy; atomic art does not require atomic dramatic timing. |
| Whisper, faster-whisper, WhisperX, MFA, or whisper.cpp as master | Preserve provider-native timing when bound to exact audio; use approved-transcript forced alignment next; use faster-whisper for local verification/ASR; evaluate pinned WhisperX first and MFA as release fallback. Keep whisper.cpp for live STT only. | This preserves authoritative text and isolates heavy authoring dependencies from playback. |
| `librosa`, Beat This!, All-In-One, Essentia, madmom, or Web Audio | Adopt pinned FFmpeg + SoundFile/NumPy/SciPy/librosa for baseline offline analysis. Beat This! is optional after an in-domain gate. Keep Web Audio only as cosmetic live texture. Reject the other tools as production defaults. | This is the smallest local deterministic baseline with acceptable licensing and maintenance posture. |
| Universal numeric motion quotas versus artistic judgment | Schema enforces hard safety/overlap/cooldown rules. Gesture-density thresholds are named fixture/profile policy, not universal constants. | Reports agree on restraint but correctly warn against turning research averages into universal acting laws. |
| Freeze all motion on pause versus allow idle life | Score-owned body, face, mouth, gaze, locomotion, and micro-motion are functions of media time and therefore freeze on pause. Non-media UI chrome may continue independently. | This is the only replay-stable rule and avoids mouth/body drift during pauses. |

## Contract Conventions

All new persisted JSON schemas use JSON Schema Draft 2020-12, `additionalProperties: false` at every object boundary, and an exact integer `schema_version`. Unknown versions and unknown fields fail closed.

Normative scalar rules:

- IDs match `^[a-z0-9][a-z0-9._:-]{0,127}$`.
- SHA-256 values match `^sha256:[0-9a-f]{64}$`.
- Persisted times are integers in `[0, 9007199254740991]` and use `_ms` suffixes.
- PCM positions use integer `_sample` or `_samples` suffixes.
- Rates, confidence, valence, intensity, and normalized values use fixed-point integers: `_milli` in `[0,1000]`; signed values use `[-1000,1000]`. `rate_milli=1000` means 1.0x.
- Time ranges are half-open: `start_ms <= t < end_ms`. `end_ms` must be greater than `start_ms`. At `t == duration_ms`, only terminal state applies.
- Identity-bearing accepted artifacts contain no binary floating-point values. Provider raw responses may contain floats but are stored and hashed as raw evidence, not canonical accepted contracts.
- Human-facing timestamps such as `created_at` are provenance metadata and are excluded from content identity by hashing a declared `identity` object, not by deleting fields ad hoc.
- Text-bearing transcript/analysis artifacts remain local. Connector, runtime replay, and fallback records contain opaque span IDs and hashes, never manuscript text.

### Canonical hashing

Add `wizard_avatar/artifact_hashing.py` with:

```python
def canonical_json_v1(value: object) -> bytes: ...
def sha256_ref(data: bytes) -> str: ...
def artifact_identity_hash(identity: Mapping[str, object]) -> str: ...
```

`canonical_json_v1` accepts only null, bool, integer, UTF-8 string, array, and string-keyed object; sorts object keys by Unicode code point; preserves array order; emits compact UTF-8 JSON; and rejects floats, bytes, sets, duplicate JSON keys, lone surrogates, and non-string map keys. Cross-language golden vectors are required.

Do not silently replace `runtime.canonical_json_bytes()`. That function intentionally wraps Python floats as hexadecimal objects for runtime state hashing (`wizard_avatar/runtime.py:27-67`). Artifact hashing is a new versioned contract.

## Exact Artifact Schemas

The following shapes are normative. The implementation should materialize them as schema files in `wizard_avatar/definitions/` and frozen Python value objects. Every listed field is required unless marked optional.

### `MediaAssetV1`

```json
{
  "schema_version": 1,
  "media_id": "media:sha256:<hex>",
  "identity": {
    "source_sha256": "sha256:<hex>",
    "byte_length": 123,
    "mime_type": "audio/mpeg",
    "duration_ms": 123000,
    "media_kind": "audiobook"
  },
  "storage_ref": "prism-media:opaque-id",
  "display": {
    "title": "...",
    "creator": null,
    "collection": null,
    "chapter_id": null
  },
  "canonical_pcm": null,
  "external": {
    "canonical_url": null,
    "url_source": null
  },
  "status": {
    "transcript": "missing",
    "analysis": "missing",
    "performance": "missing"
  }
}
```

Enums:

- `media_kind`: `audiobook | music | video | speech | unknown`.
- status values: `missing | queued | processing | ready | ready_with_warnings | failed | stale`.
- `storage_ref` is an opaque local resolver key. A raw path is permitted only in a private job manifest, never in this portable record or the connector.
- `canonical_pcm`, when present, requires `pcm_sha256`, `sample_rate_hz`, `channels`, `sample_format`, `duration_samples`, decoder build hash, and exact decoder argument hash.
- `external.canonical_url` is optional metadata for governed Whiz behavior. It is not the playable URL and never crosses to Python in `MediaSessionSnapshotV1`.

`media_id` is derived only from source bytes: `media:sha256:<source hex>`. UI selection IDs are aliases, not processing identity.

### `TranscriptV1`

```json
{
  "schema_version": 1,
  "transcript_id": "transcript:<hash-prefix>",
  "media_id": "media:sha256:<hex>",
  "source_sha256": "sha256:<hex>",
  "display_sha256": "sha256:<hex>",
  "spoken_normalized_sha256": "sha256:<hex>",
  "revision": 1,
  "language": "en",
  "source_kind": "provided",
  "chapters": [
    {"chapter_id": "ch-001", "order": 0, "title": null, "block_ids": ["b-0001"]}
  ],
  "blocks": [
    {
      "block_id": "b-0001",
      "chapter_id": "ch-001",
      "order": 0,
      "kind": "paragraph",
      "display_text": "...",
      "spoken_normalized_text": "..."
    }
  ],
  "provenance": {
    "importer_id": "provided-text-v1",
    "normalizer_version": "transcript-normalizer-v1",
    "parent_transcript_id": null
  }
}
```

`source_kind`: `provided | provider_tts | local_asr | human_corrected`. Synthesis/SSML source is preserved separately in a private source artifact; display text contains no synthesis tags. Corrections create a new immutable revision.

### `AlignmentV1`

```json
{
  "schema_version": 1,
  "alignment_id": "alignment:<hash-prefix>",
  "media_id": "media:sha256:<hex>",
  "media_sha256": "sha256:<hex>",
  "pcm_sha256": "sha256:<hex>",
  "transcript_id": "transcript:<id>",
  "transcript_revision": 1,
  "duration_ms": 123000,
  "source_kind": "forced_alignment",
  "units": [
    {
      "unit_id": "w-000001",
      "parent_block_id": "b-0001",
      "kind": "word",
      "text": "Paul",
      "normalized": "paul",
      "start_ms": 42,
      "end_ms": 381,
      "confidence_milli": 940,
      "review": "accepted"
    }
  ],
  "silences": [
    {"silence_id": "s-0001", "start_ms": 0, "end_ms": 42, "kind": "technical_room_tone"}
  ],
  "engine": {
    "adapter": "whisperx",
    "adapter_version": "pinned",
    "model_id": "pinned",
    "model_sha256": "sha256:<hex>",
    "parameters_sha256": "sha256:<hex>",
    "offline": true
  },
  "qa": {
    "wer_milli": 6,
    "cer_milli": 2,
    "timed_word_coverage_milli": 1000,
    "low_confidence_count": 2,
    "unaligned_count": 0,
    "disposition": "pass"
  }
}
```

`source_kind`: `provider_native | forced_alignment | asr_word_timing | manual`. Provider-native timing is accepted only when its audio hash matches. Units are monotonic; lexical word overlap is invalid. `qa.disposition` is `pass | review | fail`. Captions and compact mouth tracks derive from this artifact; neither is an independent timing source.

### `NarrativeScoreV1`

This is local, content-free direction after manuscript analysis. It may cite transcript span IDs but contains no prose.

```json
{
  "schema_version": 1,
  "narrative_score_id": "narrative:<hash-prefix>",
  "media_id": "media:sha256:<hex>",
  "transcript_id": "transcript:<id>",
  "alignment_id": "alignment:<id>",
  "duration_ms": 123000,
  "book_profile": {
    "genre_family": "fiction",
    "narration_form": "fiction",
    "pov_system": "third_limited",
    "narrator_role": "storyteller",
    "baseline_distance": "middle",
    "baseline_energy_milli": 350,
    "performance_ceiling_milli": 700
  },
  "chapter_envelopes": [],
  "beats": [
    {
      "beat_id": "beat-0042",
      "chapter_id": "ch-001",
      "scene_id": "scene-003",
      "source_span_ids": ["b-0087"],
      "start_ms": 81240,
      "apex_ms": 82610,
      "end_ms": 83900,
      "performer_mode": "narration",
      "beat_function": "reveal",
      "chapter_phase": "turn",
      "tension_milli": 820,
      "valence_milli": 0,
      "activation_milli": 460,
      "intimacy_milli": 200,
      "information_density_milli": 350,
      "stillness_target": "held",
      "gesture_intent": "react",
      "visual_salience": "medium",
      "spoiler_sensitive": true,
      "confidence_milli": 910,
      "review_status": "accepted"
    }
  ],
  "provenance": {"pipeline_hash": "sha256:<hex>", "validation_hash": "sha256:<hex>"}
}
```

Allowed `performer_mode`: `narration | dialogue | interior_thought | scene_action | exposition | reflection | quotation | paratext`. The full beat-function, silence, stance, and boundary enums should follow report 04, but no field directly names a pose, action command, world coordinate, or model rationale.

### `MusicScoreV1`

```json
{
  "schema_version": 1,
  "music_score_id": "music:<hash-prefix>",
  "media_id": "media:sha256:<hex>",
  "media_sha256": "sha256:<hex>",
  "pcm_sha256": "sha256:<hex>",
  "sample_rate_hz": 44100,
  "duration_samples": 0,
  "analysis": {
    "pipeline_version": "music-analysis-v1",
    "decoder_build_sha256": "sha256:<hex>",
    "config_sha256": "sha256:<hex>",
    "packages_sha256": "sha256:<hex>",
    "model_sha256": null
  },
  "beats": [{"sample": 0, "confidence_milli": 900}],
  "downbeats": [{"sample": 0, "confidence_milli": 850}],
  "tempo_regions": [{"start_sample": 0, "end_sample": 441000, "bpm_milli": 120000, "confidence_milli": 900}],
  "meter_regions": [{"start_sample": 0, "end_sample": 441000, "numerator": 4, "denominator": null, "confidence_milli": 620}],
  "sections": [{"section_id": "sec-001", "start_sample": 0, "end_sample": 441000, "label": "unknown", "confidence_milli": 500}],
  "onsets": [{"sample": 0, "strength_milli": 800}],
  "loudness": {"integrated_lufs_centi": -1600, "lra_lu_centi": 800, "true_peak_dbtp_centi": -120},
  "envelopes": {"hop_samples": 441, "rms_dbfs_centi": [], "onset_strength_milli": [], "bands_db_centi": []}
}
```

`unknown` is a valid section/meter outcome. Sample positions are canonical; consumers convert with `floor(sample * 1000 / sample_rate_hz)`. Functional labels are optional and cannot be fabricated from boundary detection.

### `PerformanceScoreV1`

This is the portable, character-independent editorial score assembled from narrative or music analysis.

```json
{
  "schema_version": 1,
  "score_id": "performance:<hash-prefix>",
  "revision": 1,
  "status": "accepted",
  "mode": "audiobook",
  "media": {"media_id": "media:sha256:<hex>", "media_sha256": "sha256:<hex>", "duration_ms": 123000},
  "analysis_ref": {"kind": "narrative", "artifact_id": "narrative:<id>", "artifact_sha256": "sha256:<hex>"},
  "tracks": [
    {
      "track_id": "body-base",
      "kind": "body_base",
      "exclusive": true,
      "max_active": 1,
      "gap_policy": "characterful_neutral",
      "cues": []
    }
  ],
  "provenance": {
    "pipeline_version": "performance-assembly-v1",
    "prompt_bundle_sha256": null,
    "provider_run_sha256": null,
    "seed": 0,
    "parent_score_sha256": null,
    "edit_set_sha256": null
  },
  "validation": {"policy_sha256": "sha256:<hex>", "report_sha256": "sha256:<hex>", "decision": "accepted"}
}
```

Track kinds are exactly:

`narrative_state`, `body_base`, `locomotion`, `stage`, `gesture`, `face`, `gaze`, `speech`, `blink`, `dance`, `effects`, `transition`, `manual_override`.

Every cue uses this base contract:

```json
{
  "cue_id": "ch-003.beat-014.gesture-001",
  "start_ms": 418220,
  "end_ms": 420100,
  "intent": "explain_light",
  "source_ids": ["beat-014"],
  "priority": 40,
  "amplitude_milli": 450,
  "phase_ranges": {
    "anticipation": [418220, 418500],
    "stroke": [418500, 418720],
    "hold": [418720, 419400],
    "release": [419400, 419760],
    "settle": [419760, 420100]
  },
  "capability_requirements": ["body.explain_light"],
  "fallback_intents": ["face.attentive", "body.characterful_neutral", "still"],
  "interrupt_policy": "at_phase_boundary",
  "cooldown_class": "ordinary_gesture",
  "motif_id": null,
  "confidence": {"alignment_milli": 980, "evidence_milli": 910, "planner_milli": 740},
  "manual": {"locked": false, "disabled": false}
}
```

Rules:

- Phase ranges are optional only for tracks that do not perform a phrase. If present they are contiguous, ordered, lie inside the cue, and use half-open ranges.
- Exclusive tracks may not overlap. `body_base`, `stage`, and `speech` must cover their declared ready ranges or use an explicit gap policy.
- `must_hold` is represented by a `still`/hold cue, not by absence.
- LLM candidates may use only registered semantic intents. Raw pose/clip/node/transition IDs are forbidden here.
- A cue may be disabled by an edit but remains addressable by stable ID.

### `ScoreEditsV1`

```json
{
  "schema_version": 1,
  "edit_set_id": "edits:<hash-prefix>",
  "base_score_sha256": "sha256:<hex>",
  "revision": 1,
  "operations": [
    {
      "operation_id": "op-0001",
      "op": "replace",
      "cue_id": "ch-003.beat-014.gesture-001",
      "field": "intent",
      "old_value_sha256": "sha256:<hex>",
      "value": "sincere",
      "reason_code": "director_choice",
      "locked": true
    }
  ],
  "parent_edit_set_sha256": null,
  "actor": {"kind": "human", "actor_id": "local:opaque"}
}
```

Allowed operations: `add_cue | remove_cue | replace | disable | enable | lock | unlock | select_take`. Operations are applied in array order. A mismatched `old_value_sha256` is a deterministic rebase conflict; it is never silently ignored.

### `CharacterPackageV2`

```json
{
  "schema_version": 2,
  "character_id": "wizard-joe",
  "package_version": "2.0.0",
  "display_name": "Wizard Joe",
  "renderer_adapter": "asciline_atomic_snapshot_v1",
  "compatibility": {
    "runtime_api_min": 2,
    "runtime_api_max": 2,
    "compiled_score_schema_min": 1,
    "compiled_score_schema_max": 1
  },
  "assets": [
    {"asset_id": "poses", "role": "pose_library", "uri": "reference_avatar_pose_cells.json", "sha256": "sha256:<hex>", "byte_length": 1, "media_type": "application/json"}
  ],
  "coordinate_spaces": {
    "stage": {"id": "stage_v1", "x_axis": "right", "y_axis": "up", "z_axis": "away_from_camera", "units": "stage_unit"},
    "pose": {"id": "pose_cell_v1", "x_axis": "right", "y_axis": "down", "origin": "top_left", "units": "cell"}
  },
  "semantic_rig": {
    "required_controls": ["root", "facing", "locomotion_phase", "support_contact", "expression", "mouth_shape"],
    "optional_controls": ["gaze_target", "head_intent", "staff_hand", "staff_tip", "wing_state", "effect_socket"],
    "required_anchors": ["root", "left_eye", "right_eye", "mouth", "left_foot", "right_foot"]
  },
  "channels": [
    {"channel": "body", "topology": "atomic_full_body", "composition": "exclusive"},
    {"channel": "face", "topology": "validated_overlay", "composition": "additive_if_supported"},
    {"channel": "mouth", "topology": "validated_overlay", "composition": "speech_over_affect"}
  ],
  "capabilities": [],
  "mappings": [],
  "fallbacks": [],
  "preload": {"startup_asset_ids": ["poses", "graph"], "lookahead_ms": 2000, "memory_budget_bytes": 67108864},
  "default_intent": "body.characterful_neutral"
}
```

Each capability is exact:

```json
{
  "capability_id": "body.explain_light",
  "kind": "body_intent",
  "supported_facings": ["south"],
  "mobility_modes": ["grounded_idle"],
  "owned_channels": ["body", "staff", "wings"],
  "compatible_channels": ["face", "mouth"],
  "quality_tier": "reviewed",
  "interrupt_policy": "at_phase_boundary",
  "required_anchors": ["root"],
  "reduced_motion_allowed": true
}
```

Each mapping is ordered and deterministic:

```json
{
  "intent": "explain_light",
  "candidates": [
    {"mapping_id": "explain-open-hand", "clip_id": "audiobook_explain_open_hand", "weight": 100, "amplitude_min_milli": 0, "amplitude_max_milli": 700}
  ]
}
```

Fallbacks form an acyclic chain and end in `body.characterful_neutral` or `still`. Package validation rejects duplicate `(character_id, package_version)`, hash mismatch, missing required asset, unknown mapping target, unsupported channel claim, cyclic fallback, and an atomic snapshot claiming a generic region blend.

Wizard Joe V2 initially promotes only reviewed narration families: `characterful_neutral`, `greeting`, `think`, `explain_light`, `explain_broad`, `point_reference`, `sincere`, and restrained emotion states. Magic, combat, flight, celebration, shush, and flourish remain literal/peak-only. Poses 40-59 remain diagnostic until canonicalized. `_close` emotion poses are intensity alternatives, not camera shots.

### `CompiledPerformanceScoreV1`

```json
{
  "schema_version": 1,
  "compiled_score_id": "compiled:<hash-prefix>",
  "performance_score_sha256": "sha256:<hex>",
  "character": {
    "character_id": "wizard-joe",
    "package_version": "2.0.0",
    "package_digest": "sha256:<hex>",
    "pose_library_digest": "sha256:<hex>",
    "graph_digest": "sha256:<hex>"
  },
  "mapping_policy_sha256": "sha256:<hex>",
  "runtime_api_version": 2,
  "tracks": [],
  "checkpoints": [],
  "fallback_records": [],
  "validation": {"decision": "accepted", "report_sha256": "sha256:<hex>"}
}
```

Compiled cues preserve semantic cue IDs and add only validated execution fields: `mapping_id`, `clip_id`, `node_id`, phase-to-authored-marker mapping, exact channel ownership, resolved fallback path, preload asset IDs, and deterministic `resolution_hash`.

Checkpoints are emitted at time zero, every chapter boundary, every hard setup/source discontinuity, and at most every 10,000 ms. A checkpoint contains the complete score-owned semantic state, not rendered cells. It accelerates diagnostics and validates reconstruction; interval lookup remains authoritative.

### `MediaSessionSnapshotV1`

```json
{
  "schema_version": 1,
  "connector_session_id": "session:uuid",
  "sequence": 42,
  "cause": "seeked",
  "sampled_at_monotonic_us": 937510250,
  "media_epoch": 3,
  "media": {
    "media_id": "media:sha256:<hex>",
    "media_sha256": "sha256:<hex>",
    "kind": "audiobook",
    "chapter_id": "ch-004",
    "duration_ms": 1284220
  },
  "playback": {
    "state": "playing",
    "position_ms": 418220,
    "rate_milli": 1000,
    "ready_state": 4
  },
  "performance": {
    "character_id": "wizard-joe",
    "character_package_digest": "sha256:<hex>",
    "compiled_score_id": "compiled:<id>",
    "compiled_score_sha256": "sha256:<hex>",
    "intensity_milli": 700,
    "motion_profile": "system",
    "disabled_channels": []
  }
}
```

`cause`: `initial | loadedmetadata | play | playing | pause | waiting | stalled | seeking | seeked | ratechange | durationchange | ended | emptied | error | stop | trackchange | chapterchange | visibilitychange | heartbeat | reconnect`.

`playback.state`: `empty | loading | paused | playing | buffering | seeking | ended | stopped | error`.

Forbidden fields include URL, path, transcript/caption text, provider/model prompt, API key, and canonical external URL. `media_epoch` increments on source/track/chapter replacement, hard seek, explicit stop/reset, or restored-session discontinuity.

### `MediaSessionAckV1`

```json
{
  "schema_version": 1,
  "connector_session_id": "session:uuid",
  "accepted_sequence": 42,
  "media_epoch": 3,
  "disposition": "accepted",
  "wizard_runtime_epoch": "wizard:<id>",
  "resync_required": false,
  "error_code": null,
  "scheduler_state": "playing",
  "capabilities": {"max_snapshot_hz": 8, "supported_rate_milli": [500, 750, 1000, 1250, 1500, 2000]}
}
```

Dispositions: `accepted | duplicate | stale | rejected | resync_required`. The same `(session, sequence)` is duplicate with no second effect; lower sequence or older epoch is stale. A new Wizard runtime epoch requires one newest full reconnect snapshot.

### Internal `ResolvedCharacterState`

This is a frozen Python dataclass, not a public connector schema:

```python
@dataclass(frozen=True)
class ResolvedCharacterState:
    media_time_ms: int
    score_cue_ids: tuple[str, ...]
    body_mapping_id: str
    clip_id: str
    clip_elapsed_ticks: int
    pose_id: str
    world_position_milli: tuple[int, int]
    facing: str
    expression: str
    gaze_target: str
    mouth_shape: str
    speaking: bool
    owned_channels: frozenset[str]
    suppressed_requests: tuple[SuppressionRecord, ...]
    fallback_records: tuple[FallbackRecord, ...]
    resolution_hash: str
```

`FallbackRecord` requires `cue_id`, requested intent, selected intent/mapping, complete fallback path, reason code, package digest, media time, severity, and whether review is required.

## Runtime Algorithms

### Score validation and interval index

`CompiledScoreLoader.load()` performs these gates in order:

1. Parse JSON while rejecting duplicate object keys.
2. Validate the exact schema and unknown-field policy.
3. Verify media, performance score, package, pose-library, graph, mapping-policy, and compiled-score hashes.
4. Require `validation.decision == accepted`.
5. Validate cue IDs, references, half-open ranges, media bounds, phase ordering, exclusive overlaps, gap policies, cooldown exceptions, and fallback termination.
6. Verify every mapped clip/node/marker/channel against the pinned `CharacterPackageV2` and strict graph-v2 parser.
7. Build one immutable `TrackIntervalIndex` per track.

For non-overlapping exclusive tracks, store parallel sorted `starts` and cues and locate with `bisect_right(starts, t) - 1`. For overlay tracks, store a balanced interval index built from sorted boundaries; query returns all cues where `start <= t < end`, sorted by `(priority desc, start_ms, cue_id)`. Runtime complexity is `O(log n + k)` and never depends on replaying prior cues.

Boundary policy is exact:

- At a shared boundary, the ending cue is inactive and the starting cue is active.
- At media time zero, all required baseline tracks resolve.
- At duration, the scheduler emits terminal/ended state and no nonterminal cue.
- Empty optional tracks resolve to declared `clear`, `hold`, or `neutral`; absence has no implicit meaning.

### Media clock estimation

`MediaClockEstimator.observe(snapshot, receipt_monotonic_us)` stores the newest accepted sample. `position_at(now_us)` returns:

```text
if state == playing and age_us <= 1_500_000:
    position_ms + floor((now_us - receipt_us) * rate_milli / 1_000_000)
else:
    position_ms
```

Clamp to `[0,duration_ms]`. Local elapsed time only interpolates between authoritative snapshots. It is never persisted as media truth.

Correction rules:

- Generation/source/seek/reconnect/runtime-epoch change: hard reconcile.
- Ordinary heartbeat error `<=100 ms`: replace the interpolation anchor; do not replay edges.
- Error `>100 ms`: increment an internal reconciliation generation, discard score-owned pending edge work, and cold-evaluate current state.
- No fresh sample for 1.5 seconds: scheduler becomes `clock_uncertain`, holds the last safe continuous state, closes/suspends speech according to the last authoritative state, and launches no new expressive one-shot.
- Pause, buffering, seeking, stopped, ended, empty, and error do not interpolate.

### State-at-time evaluation

`PerformanceScheduler.evaluate(media_time_ms)`:

1. Query each score track at `media_time_ms`.
2. Reconstruct chapter/scene/beat/setup and explicit stillness.
3. Apply deterministic track priority and channel ownership.
4. Project through `AccessibilityMotionProfile` (`full`, `reduced`, or `still`) without mutating the score.
5. Resolve semantic intents through the pinned character mappings.
6. Evaluate phrase phase directly from media time.
7. Evaluate locomotion/stage position as a pure trajectory function.
8. Emit complete `ResolvedCharacterState`, suppressions, fallbacks, and preload requests.

Clip tick conversion is:

```text
clip_elapsed_ticks = floor((media_time_ms - phrase_phase_origin_ms) * 60 / 1000)
```

Playback rate is deliberately absent. Media time already advances at the selected rate. For a 2x player, score and clip phase advance twice as fast in wall time while remaining identical at the same media timestamp.

Locomotion cannot rely on integrating from chapter start. A compiled locomotion cue includes source mark, destination mark, arrival facing, path type, and easing ID. Position is evaluated in fixed-point stage units:

```text
u = clamp((t - start_ms) / (end_ms - start_ms), 0, 1)
u2 = easing_v1(u)
position = source + (destination - source) * u2
```

Implement easing with integer rational arithmetic or a versioned lookup table. On seek, position is computed directly. Existing `LocomotionController` remains authoritative for manual control outside score mode; score mode applies its resolved stage position through a new controller seam.

### Channel arbitration

One `PerformanceArbiter` resolves requests in this order:

1. safety/reset/reconnect reconciliation;
2. explicit manual director/user override;
3. full-body transition/action;
4. locomotion/support contact;
5. speech-safe gesture when package compatibility permits;
6. prop/wing/effect;
7. gaze/head/face;
8. mouth/viseme;
9. optional micro-motion.

Every rejected request creates `SuppressionRecord(reason_code, winning_owner, losing_owner, cue_id)`. Renderer code does not decide precedence.

For current Wizard Joe assets, `body` is exclusive full-body ownership. Face and mouth are allowed only when per-pose metadata declares the overlay safe. No generic region blend is attempted.

### Transition evaluator

Replace `_select_graph_v2_sample()`'s node-change reset with `GraphPhraseEvaluator.evaluate(resolved, media_time_ms)`. It owns:

- phrase phase and active clip;
- minimum hold and phase boundary;
- crossed marker calculation;
- legal successor and interrupt gate;
- contact/planted anchor;
- transition recipe or explicit coherent-cut reason;
- fallback resolution.

Supported V1 snapshot transitions are only:

1. marker-timed whole-pose handoff;
2. hold/release at a declared sample;
3. contact-preserving root correction using the declared planted anchor;
4. approved face/mouth overlay;
5. explicit hard cut with a reason code.

Region overlay recipes fail validation for current atomic assets. Per-cell dissolve remains prohibited.

### Seek and reconnect

On a new `media_epoch` or hard correction:

1. Mark prior epoch inactive before accepting new non-neutral state.
2. `OrderedCommandInbox.discard_pending()` only for score-owned edge kinds; never delete user/system commands.
3. Clear previous score ownership and preload requests.
4. Cold-evaluate score at supplied position.
5. Apply the complete resolved state atomically at the next runtime tick.
6. Use `coherent_cut: seek_reconcile`; do not perform a transition from a state that did not occur at the destination.
7. Return the new resolution hash and scheduler state in diagnostics.

No crossed cue fires. A backward seek can legitimately make the same cue active again because it is a new media epoch; idempotency keys include epoch.

### Runtime application seam

Add `WizardAvatarController.apply_performance_state(resolved)` and call it inside `WizardFrameHub._reduce_runtime_tick()` after due safety/user commands are interpreted and before `advance_tick()`.

The method applies only score-owned channels not held by a higher-authority lease. It sets clip phase from the resolved media-time tick instead of incrementing `animation_clip_tick`; it sets score-mode stage position directly; and it preserves existing manual/controller behavior when no accepted media session is active.

Do not mutate `CommandEnvelopeV1` into a media protocol. Add a separate `MediaSessionCoordinator` owned by the hub. This keeps existing command tests and API compatibility intact.

## Analysis Pipelines and Cache Keys

All authoring work lives outside the FastAPI render process in a separately locked Python 3.11 tool project at `tools/performance_authoring/`. Jobs write to a private job directory, validate, atomically rename a complete generation, then atomically update `current.json`. A stale job rechecks input hashes before publish and may never replace newer accepted output.

### Proposed authoring modules

| Module | Required symbols | Responsibility |
| --- | --- | --- |
| `tools/performance_authoring/media.py` | `probe_media`, `canonicalize_pcm`, `build_media_asset` | FFprobe inspection, pinned FFmpeg decode, source/PCM hashes, duration and format validation. |
| `transcript.py` | `import_transcript`, `normalize_display_text`, `normalize_spoken_text`, `revise_transcript` | Preserve synthesis/display/spoken forms and immutable revisions. |
| `asr.py` | `AsrAdapter`, `FasterWhisperAdapter`, `transcribe_missing_text`, `verify_transcript` | Local VAD-aware ASR evidence; never auto-rewrite approved text. |
| `alignment.py` | `AlignmentAdapter`, `ProviderNativeAdapter`, `WhisperXAdapter`, `MfaAdapter`, `align_transcript`, `realign_window` | Source-priority timing, forced alignment, localized correction, QA. |
| `captions.py` | `project_webvtt`, `project_srt`, `validate_caption_projection` | Delivery projections from canonical alignment only. |
| `narrative.py` | `build_book_map`, `build_chapter_map`, `build_beat_candidates`, `assemble_narrative_score` | Hierarchical, evidence-citing, content-free direction. |
| `planner.py` | `PlannerAdapter`, `DeterministicBaselinePlanner`, `StructuredPlanner`, `run_pass_graph` | Optional structured LLM candidates and always-available baseline. |
| `music.py` | `extract_fixed_hop_features`, `estimate_beats`, `estimate_sections`, `measure_loudness`, `build_music_score` | Deterministic offline DSP and optional gated model tier. |
| `performance.py` | `assemble_performance_score`, `apply_score_edits`, `compile_for_character`, `validate_compiled_score` | Semantic assembly, immutable edits, deterministic capability resolution. |
| `cache.py` | `CacheKey`, `ArtifactStore`, `publish_generation`, `quarantine_corrupt_entry` | Content-addressed immutable cache and generation publication. |
| `jobs.py` | `JobManifest`, `JobRunner`, `JobState`, `CancellationToken` | Resumable phase graph, progress, cancellation, stale protection. |
| `cli.py` | `main` | `inspect`, `transcribe`, `align`, `analyze-story`, `analyze-music`, `compile`, `validate`, `status`, `resume`. |

### Pipeline order

Audiobook:

```text
source bytes
 -> MediaAssetV1 + canonical PCM
 -> TranscriptV1
 -> local ASR verification evidence
 -> AlignmentV1
 -> NarrativeScoreV1
 -> PerformanceScoreV1 + ScoreEditsV1
 -> CompiledPerformanceScoreV1(character package digest)
 -> runtime load
```

Music:

```text
source bytes
 -> MediaAssetV1 + canonical PCM
 -> fixed-hop DSP/loudness
 -> beats/downbeats/tempo/meter/sections
 -> MusicScoreV1
 -> deterministic dance PerformanceScoreV1
 -> CompiledPerformanceScoreV1
```

### Transcript source precedence

1. Provider-native timing bound to exact final audio bytes.
2. Forced alignment of approved transcript to final audio.
3. Local ASR plus word alignment when no trustworthy transcript exists.
4. Duration/speech-activity fallback, labeled `fallback`, for mouth activity only.

ASR mismatch creates review evidence. It never silently changes authored text.

### Narrative pass graph

1. `ingest-v1`: deterministic segmentation, hashes, speech/silence features.
2. `book-map-v1`: optional model, source-span citations, no cues.
3. `chapter-map-v1`: optional model, scene/arc candidates.
4. `beat-analysis-v1`: optional model, bounded enums or `no_decision`.
5. `score-assembly-v1`: deterministic density, contradiction, cooldown, stillness, and spoiler rules.
6. `character-compile-v1`: deterministic package resolution.
7. `critic-v1`: optional patch suggestions only.
8. `accept-publish-v1`: validation, edits, hashes, atomic publication.

Playback never calls a model. Failed optional passes fall back by region to `DeterministicBaselinePlanner`; missing alignment produces neutral/speech-activity fallback and no narrative locomotion.

### Exact cache identities

Every key is `artifact_identity_hash({"cache_type": ..., "version": 1, ...})` using `canonical_json_v1`.

| Cache | Identity fields |
| --- | --- |
| PCM | source audio SHA-256, FFmpeg binary/build SHA-256, exact arguments, sample rate, channel policy, sample format, resampler config |
| ASR | PCM SHA-256, ASR adapter/version, model ID/SHA-256/license record, language, VAD/chunk/decoder parameters, transcript normalizer version |
| Alignment | PCM SHA-256, approved spoken transcript SHA-256/revision, aligner/version/model SHA-256, lexicon SHA-256, segmentation and normalization versions |
| Captions | alignment artifact SHA-256, display transcript SHA-256, formatter version, language profile, line/duration/reading-speed policy hash |
| Narrative pass | pass ID/version, ordered dependency hashes, input span hashes, prompt/schema/validator hashes, provider/model/revision/backend, sampling config, retrieval evidence hashes, privacy policy/consent hash |
| Music | PCM SHA-256, pipeline version, numerical lock hash, fixed-hop config, algorithm/model SHA-256, deterministic thread/device policy |
| Performance score | narrative or music artifact SHA-256, assembly policy hash, edit-set hash, seed, accessibility-independent direction policy |
| Character compilation | performance score SHA-256, character/package/pose/graph/capability digests, mapping/compiler/validator versions |
| Runtime preload | compiled score SHA-256, package digest, checkpoint/range, renderer adapter version, presentation profile |

Changing a character package invalidates compilation/preload, not transcript, alignment, narrative, or music analysis. Changing caption layout invalidates captions only. Changing display punctuation does not invalidate alignment if spoken-normalized tokens are identical. Changing one media byte invalidates every downstream artifact.

## Error and State Taxonomy

All exceptions crossing a module/API boundary use stable snake-case codes. Human messages may change; codes and structured details are contract.

### Contract/load errors

`schema_version_unsupported`, `unknown_field`, `missing_field`, `invalid_type`, `invalid_enum`, `invalid_id`, `invalid_hash`, `duplicate_json_key`, `non_integer_identity_value`, `time_out_of_bounds`, `range_invalid`, `exclusive_overlap`, `track_gap`, `dangling_reference`, `hash_mismatch`, `artifact_not_accepted`.

### Character/compile errors

`package_invalid`, `package_duplicate`, `package_digest_mismatch`, `asset_missing`, `asset_hash_mismatch`, `renderer_incompatible`, `graph_invalid`, `graph_field_advisory`, `capability_unavailable`, `mapping_missing`, `mapping_unreachable`, `channel_unsupported`, `fallback_cycle`, `fallback_exhausted`, `transition_illegal`, `marker_missing`, `preload_miss`.

Required character asset failure is fatal before session readiness. Optional capability failure degrades through the declared chain and emits a fallback record. `preload_miss` holds the previous stable pose and reports a warning; it never selects an unrelated pose.

### Pipeline/job errors

`media_probe_failed`, `decode_failed`, `pcm_mismatch`, `transcript_mismatch`, `alignment_failed`, `alignment_review_required`, `model_unavailable_offline`, `network_forbidden`, `provider_denied`, `provider_timeout`, `structured_output_invalid`, `budget_exhausted`, `job_cancelled`, `job_stale`, `publish_failed`, `cache_corrupt`.

Job states: `queued | running | cancelling | cancelled | ready | ready_with_warnings | review_required | failed_recoverable | failed_terminal | stale`.

### Media scheduler states/errors

Scheduler states: `no_session | loading_score | ready | playing | paused | buffering | seeking | clock_uncertain | stopped | ended | degraded_neutral | error`.

Errors/dispositions: `duplicate_snapshot`, `stale_sequence`, `stale_media_epoch`, `session_conflict`, `resync_required`, `media_mismatch`, `score_mismatch`, `unsupported_rate`, `position_out_of_bounds`, `clock_stale`, `reconcile_required`, `score_not_ready`, `user_override_active`.

Audio playback is never stopped by a performance error. Hash/package/score mismatch prevents non-neutral performance and produces `degraded_neutral` with an actionable diagnostic.

## Python Runtime Modules and Symbols

Add these modules without relocating existing renderer code in the first implementation:

| File | Symbols |
| --- | --- |
| `wizard_avatar/artifact_hashing.py` | `canonical_json_v1`, `sha256_ref`, `artifact_identity_hash` |
| `wizard_avatar/schema_validation.py` | `SchemaRegistry`, `ContractValidationError`, `load_and_validate_json` |
| `wizard_avatar/character_capabilities.py` | `CharacterPackageV2`, `Capability`, `MappingCandidate`, `FallbackRule`, `CharacterRegistry`, `load_character_package_v2`, `adapt_v1_package` |
| `wizard_avatar/performance_score.py` | `PerformanceScore`, `CompiledPerformanceScore`, `ScoreCue`, `TrackIntervalIndex`, `CompiledScoreLoader` |
| `wizard_avatar/character_resolution.py` | `CharacterResolver`, `ResolvedCharacterState`, `FallbackRecord`, `SuppressionRecord`, `resolve_intent` |
| `wizard_avatar/graph_phrase.py` | `GraphPhraseEvaluator`, `PhrasePhase`, `GraphPresentationSample`, `evaluate_at_media_time` |
| `wizard_avatar/media_session.py` | `MediaSessionSnapshotV1`, `MediaSessionAckV1`, `MediaSessionCoordinator`, `MediaClockEstimator`, `MediaSessionError` |
| `wizard_avatar/performance_scheduler.py` | `PerformanceScheduler`, `SchedulerState`, `AccessibilityMotionProfile`, `SchedulerDiagnostics` |
| `wizard_avatar/performance_application.py` | `PerformanceArbiter`, `PerformanceStateApplier`, `apply_to_controller` |

Modify existing files narrowly:

- `character_package.py`: retain V1 loader; route new sessions through `CharacterRegistry`; stop silent duplicate overwrite for V2.
- `animation_graph.py`: expose strict operative/advisory metadata and planted-anchor presentation result; keep parser/evaluation compatibility.
- `pose_selection.py`: retain legacy behavior for non-score mode; score mode consumes `GraphPresentationSample`; replace silent fallback with structured compatibility diagnostics.
- `controller.py`: add `apply_performance_state()` and score-owned channel markers; preserve all current commands.
- `models.py`: add only compact public scheduler diagnostics to `WizardState` or a parallel `PerformanceRuntimeState`; do not place transcript text in it.
- `stream.py`: own `MediaSessionCoordinator`, accept snapshots at a tick boundary, evaluate score before controller advance, include media/score hashes in replay header/records.
- `server.py`: add bearer-authenticated loopback `POST /api/avatar/wizard/media-session`, score load/status, capability query, and read-only diagnostics. Reject browser `Origin` on the connector route. Do not add permissive CORS.
- `frame_source.py`: consume resolved pose/face/mouth state only; keep atomic rendering and stop inventing timing.

## Dependency Decisions

### Live Python runtime (Python 3.9+)

Keep FastAPI, Uvicorn, and Pillow. Add only:

- `jsonschema>=4.23,<5` for Draft 2020-12 structural validation, locked exactly in `uv.lock`.

Do not import FFmpeg bindings, NumPy, Torch, Whisper, librosa, or provider SDKs into the live avatar package. Authentication, hashing, interval lookup, scheduler evaluation, and fixed-point math use the standard library.

### Isolated authoring environment (Python 3.11)

Required baseline, exact versions locked after the gold-corpus spike:

- external pinned FFmpeg/ffprobe build;
- `numpy`, `scipy`, `soundfile`, `librosa==0.11.*`;
- `jiwer`;
- `faster-whisper` for local ASR/VAD verification.

Conditional extras:

- pinned WhisperX adapter for first forced-alignment implementation, only if it clears the boundary benchmark and offline/package gate;
- MFA as a separately managed fallback/benchmark environment;
- Beat This! 1.1.* with vendored verified model weights, canonical CPU mode, and deterministic settings only after in-domain evaluation.

Explicitly rejected as production defaults:

- Essentia: AGPL/product decision and its meter algorithm is explicitly experimental.
- madmom: old runtime and non-commercial bundled model/data terms.
- aubio: old GPL release and weaker fit than the selected baseline.
- aeneas: AGPL, old release, and weak word-alignment fit.
- direct TorchAudio forced alignment: deprecated/removal path.
- All-In-One: heavy stack and transitive/model licensing; R&D only.
- PyAV: optional only if measured need justifies ABI/build coupling; FFmpeg subprocess is the baseline.
- cloud transcription or planning SDKs in playback: prohibited.

Model downloads are never implicit. Models are staged, hashed, licensed in a manifest, and run with offline flags/network denial. Missing assets fail closed with `model_unavailable_offline`.

## Test Plan

### New Python unit suites

| Test file | Required coverage |
| --- | --- |
| `tests/wizard/test_artifact_hashing.py` | Cross-language canonical vectors, Unicode, integer limits, float/duplicate-key rejection. |
| `test_contract_schemas.py` | Valid/invalid fixture matrix for every schema; unknown fields/versions; stable error codes. |
| `test_character_package_v2.py` | Asset hashes, duplicate IDs, channels, mappings, fallback cycles, V1 adapter, truthful second character. |
| `test_track_interval_index.py` | Exact boundaries, overlap queries, gaps, 10,000 generated positions. |
| `test_compiled_score.py` | Hash binding, accepted status, graph reachability, phase ranges, checkpoints, edit rebases. |
| `test_media_session.py` | Auth-independent parser, sequence/epoch dedupe, stale/reconnect, clock freshness, state transitions. |
| `test_performance_scheduler.py` | Linear/cold-seek equality, pause/rate/buffer, accessibility projection, deterministic resolution hashes. |
| `test_graph_phrase.py` | Holds, markers, interrupt gates, legal successors, planted anchors, explicit hard cuts. |
| `test_character_resolution.py` | Capability mapping, deterministic compile-time variation, fallback records, suppressed-channel reasons. |
| `test_performance_application.py` | User lease precedence, score ownership, reset/reconcile, legacy mode no regression. |
| `test_media_session_server.py` | Bearer auth, browser-origin rejection, body cap, typed ack/errors, no CORS wildcard. |

Use property-generated event traces without adding Hypothesis initially if dependency minimization is preferred; a deterministic standard-library generator with persisted seeds is sufficient. Add Hypothesis only if the generated-state coverage materially improves.

### Required deterministic oracles

1. For 1,000 random media times, linear evaluation and cold seek produce identical `resolution_hash`, state hash, selected clip/pose, and frame hash.
2. The same accepted score/package/seed in two fresh processes produces byte-identical normalized cue decisions, fallback records, state samples, and selected frame hashes.
3. 24/30/60 presentation fps produce identical semantic states at fixed media times.
4. 0.5x/1x/1.5x/2x playback produce identical states at identical media times.
5. One hundred rapid seeks apply zero old-epoch actions and converge to the final destination.
6. A deliberately different second character package runs the same score without Python conditionals; unsupported staff/wing/gesture intents produce declared fallbacks.
7. Reduced motion dispatches zero locomotion, dance, flight, camera, spin, or whole-body audio-reactive activity while preserving audio-time speech/caption state.
8. Local authoring with egress denied emits zero non-loopback traffic and no transcript/path canaries in logs.

### Performance and timing gates

- Connector event-to-ack loopback p95 `<=25 ms`, p99 `<=50 ms` on declared hardware.
- Correct post-seek resolved state on the first post-seek update and within `100 ms` for the Python core; full browser/render recovery may use the broader `250 ms` product gate.
- Cue-to-audio visible stroke error over 15 minutes: p95 `<=50 ms`, max `<=100 ms` outside a declared discontinuity recovery window.
- Scheduler/contract/interval work adds no browser main-thread burden and no Python simulation catch-up drops.
- Split the known stream deadline test: deterministic fake clock + cheap frame source for policy, instrumented real-render benchmark for the actual 24 fps budget. Do not weaken the existing assertion to hide renderer cost.

### Existing regression gate

All current package, graph, pose, anchor, face, command, runtime, transport, locomotion, projection, stream, frame, and server tests remain. Legacy HTTP/WebSocket/manual/demo behavior stays available when no media session is accepted.

## Implementation Slices

Each slice is independently reviewable and should change only the listed ownership surface. Do not begin model integration before slices 1-6 are green.

### Slice 1: Canonical contracts and fixtures

Add artifact hashing, schema registry, all schema files, frozen contract values, stable error codes, and golden fixtures. No runtime behavior changes.

Exit: Python validates every shared fixture; canonical hashes are frozen and ready for PrismGT/Rust/JS parity.

### Slice 2: CharacterPackageV2 and truthful capability census

Add V2 loader/registry/digest, V1 adapter, Wizard Joe V2 manifest, package audit command, structured mappings/fallbacks, and a valid minimal second character fixture. Mark every graph field operative or advisory.

Exit: capability query is derived from validated assets; duplicate IDs, stale hashes, region overclaims, and silent graph fallback fail visibly.

### Slice 3: Score loader, edits, compiler, and interval evaluator

Implement `PerformanceScoreV1`, `ScoreEditsV1`, compilation, `CompiledPerformanceScoreV1`, checkpoint generation, validators, and `TrackIntervalIndex`. Use hand-authored synthetic scores only.

Exit: state-at-time semantic evaluation is pure, hash-bound, and seek-equivalent before touching the live server.

### Slice 4: Media-session coordinator and authenticated endpoint

Implement snapshot/ack parsing, bearer auth, origin rejection, sequence/epoch handling, `MediaClockEstimator`, scheduler diagnostics, and replay records. The accepted score response remains neutral.

Exit: play/pause/seek/rate/buffer/reconnect traces are deterministic and never change audio or expose private fields.

### Slice 5: Scheduler, accessibility projection, and controller application

Implement `PerformanceScheduler`, `PerformanceArbiter`, complete state resolution, `apply_performance_state()`, direct media-time clip phase, fixed-point stage trajectories, reduced/still profiles, and user-lease precedence.

Exit: one neutral-plus-speech fixture and one restrained gesture fixture pass linear/seek/rate/pause/reconnect/frame-hash tests through the real `WizardFrameHub`.

### Slice 6: Executable graph policy and Wizard Joe narration mappings

Implement phrase phases, minimum holds, marker/interrupt/legal-successor policy, planted-anchor correction, visible fallback records, and the curated narration pose families. Keep snapshots atomic.

Exit: active speech reaches reviewed narration phrases while stationary; unsupported layering fails closed; no diagnostic pose becomes autonomous without a clip and mapping.

### Slice 7: Media/transcript/alignment authoring foundation

Create the isolated Python 3.11 project, canonical FFmpeg decode, `MediaAssetV1`, transcript normalization/revisions, faster-whisper verification, provider-native import, forced-alignment adapter spike, `AlignmentV1`, caption projection, job/caching/publication.

Exit: an egress-denied fixture publishes one complete hash-valid generation; correction invalidates only required layers; stale publish is refused.

### Slice 8: Deterministic narrative baseline and optional structured planning

Implement hierarchical segmentation, baseline score assembly, prompt bundles, planner result provenance, `no_decision`, optional local structured adapter, critic patches, and edit preservation.

Exit: no-model mode produces an accepted sparse score; malformed/adversarial model output cannot create runtime authority or unknown capabilities.

### Slice 9: Music DSP and deterministic dance compilation

Implement fixed-hop features, FFmpeg EBU R128, librosa baseline beats/tempo/boundaries, meter abstention, `MusicScoreV1`, section-aware dance intent, and reduced-motion projection. Gate Beat This! separately.

Exit: repeated clean-process analysis is byte-identical; seek/render-cadence tests select identical musical events at the same media sample/time.

### Slice 10: Facial/speech timing and long-form evidence

Derive compact mouth/silence/viseme groups from `AlignmentV1`, add pose-safe face metadata, deterministic gaze/blink events, expression envelopes, and long-form replay/evidence capture.

Exit: mouth closes in aligned silence, blinks are deterministic but non-periodic and phrase-aware, unsupported pose overlays fail closed, and representative chapter evidence passes technical plus director review.

## Non-Negotiable Acceptance Statement

The implementation is not audiobook-performance-ready until an accepted compiled score, pinned character package, and authoritative PrismGT media snapshot can produce the same resolved and rendered state at arbitrary time after linear playback, seek, reconnect, and restart. A successful LLM response, imported transcript, green build, or moving avatar is not substitute evidence.

The first production milestone is intentionally restrained: one validated Wizard Joe package, one real second-character fixture, supplied/provider transcript paths, deterministic baseline narrative and music scores, exact seek/reconnect behavior, characterful neutral, sparse narration phrases, aligned mouth/silence, explicit fallbacks, and inspectable replay evidence. Richer motion comes after those contracts are true.
