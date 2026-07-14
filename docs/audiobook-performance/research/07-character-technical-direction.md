# Character Technical Direction Audit

**Role:** Character Technical Director
**Project:** Wizard Joe Audiobook Performance Engine and PrismGT Media Connector
**Audit date:** 2026-07-13
**Python repository:** `WizardJoeAvatar-python` at `7781a67c97bfbfa16a64d5b9fb12bdf74bd4c032`
**PrismGT repository:** `prism-geometry-talk-current` at `0ce9f9bae665b1415cd776e4d6c9ee23565936ac`
**Ownership boundary:** Research and technical direction only. No production code was changed.

## Executive decision

Wizard Joe has a useful deterministic **pose-player foundation**, but it does not
yet have a reusable character rig or a production character-package contract.
The preferred renderer plays atomic 72x96 square-cell snapshots. All 89 poses
share one root and ten named anchors, and the v2 animation graph adds meaningful
clip, contact, channel, transition, and fallback metadata. The runtime also has
a strong 60 Hz ordered-command core with idempotent command IDs, per-source
sequence watermarks, acknowledgements, canonical state hashes, and replay logs.

Those are good ingredients. They are not yet wired into the system described by
the audiobook brief:

- The package manifest names files and six broad capability strings, but it does
  not declare a semantic rig, coordinate spaces, channel topology, animation
  mappings, structured fallbacks, asset hashes, compatibility versions, memory
  budgets, or preload policy.
- The reference asset is not a deforming skeleton. Its ten anchors are attachment
  and observation points, not a hierarchy of joints with rest or bind transforms.
- All 277,285 authored cells lack `region` labels. Therefore graph channel masks
  such as `body`, `staff`, `wings`, `mouth`, and `effect` are descriptive today;
  they cannot drive general per-region blending of the snapshot art.
- Graph transition and interrupt policy is parsed, but production selection only
  records a selected transition ID, resets the target clip to tick zero, and
  immediately evaluates it. Authored transition recipes are not performed.
- The fallback path catches graph and asset errors broadly and silently replaces
  the requested sample. It does not emit the fallback record required by the
  project brief.
- The avatar runtime advances from a monotonic wall clock. PrismGT reads the media
  element's `currentTime` during animation frames, but has no character connector,
  media-session contract, seek/rate/chapter event stream, or score-state
  reconciliation path.

**Readiness:** strong single-character snapshot assets; partial animation graph;
good deterministic command kernel; low multi-character and audiobook-scheduler
readiness.

**Direction:** keep the renderer, fixed-tick runtime, and atomic snapshot model.
Add a versioned semantic control-rig and `CharacterPackageV2` above them. Treat
each character as an adapter from shared performance intents to its own clips,
anchors, overlays, and explicit fallbacks. Drive runtime state from PrismGT media
time through idempotent reconciliation commands, not by trying to make the avatar
wall clock track the audiobook.

## Audit basis

### Confirmed repository state

At the final state check, the Python repository was on branch
`codex/audiobook-performance-engine` at
`7781a67c97bfbfa16a64d5b9fb12bdf74bd4c032`. Its only reported untracked scope
was `docs/audiobook-performance/`, which contains the parallel research reports.
The audited virtual environment is Python 3.9.6; `pyproject.toml` requires Python
3.9 or newer and declares FastAPI, Uvicorn, and Pillow.

PrismGT was on `desktop/prism-gt-influence-integrated` at
`0ce9f9bae665b1415cd776e4d6c9ee23565936ac` with no short-status output during
the audit.

These branch names can move while the 12-agent pass is active; the commit hashes
are the stable audit boundary.

### Verification performed

Repository data was counted structurally with `jq`, not inferred from prose:

| Asset or contract | Confirmed count/state |
|---|---:|
| Pose snapshots | 89 |
| Snapshot dimensions | 72x96 for all 89 |
| Root anchors | one value, `[36, 95]`, for all 89 |
| Named anchors per pose | 10 for all 89 |
| Sparse authored cells | 277,285 |
| Cells with a `region` value | 0 |
| Graph classifications | 89 |
| Poses reachable as clip samples | 39 |
| Poses classified `diagnostic_only` | 50 |
| Graph clips / nodes | 28 / 28 |
| Directed transitions | 47 |
| Transition recipes | 5 |
| Capability tiers A / B / C | 33 / 6 / 50 |

The following focused command passed:

```text
.venv/bin/python -m unittest \
  tests.wizard.test_character_package \
  tests.wizard.test_reference_avatar_pose_library \
  tests.wizard.test_anchor_continuity \
  tests.wizard.test_animation_channels \
  tests.wizard.test_production_animation_wiring \
  tests.wizard.test_commanding \
  tests.wizard.test_runtime \
  tests.wizard.test_transport \
  tests.wizard.test_projection \
  tests.wizard.test_locomotion
```

Result: **51 tests passed in 121.532 seconds**.

This proves the current deterministic kernel, asset wiring, and tested fallback
behavior. It does not prove graph-policy execution, media-clock synchronization,
multi-character retargeting, content-addressed caching, or audiobook performance.

## Current character architecture

### 1. Character package and asset loading

`CharacterPackage` currently contains eight fields: schema version, character
ID, display name, renderer, pose-library path, animation-graph path, default pose,
and a tuple of capability strings (`wizard_avatar/character_package.py:18-27`).
The only accepted renderer is `asciline_square_cells`; package assets must resolve
to files beneath the package directory, which is a useful path-containment rule
(`character_package.py:30-76`, `97-103`).

The package loader confirms only that the default pose exists and that pose IDs
found in graph samples are a subset of the pose library. It does not invoke the
strict graph-v2 parser, apply the bundled JSON Schema, verify hashes, check a
semantic mapping, or validate runtime compatibility. Loading mutates a process
global dictionary from `character_id` to graph path; a duplicate character ID
silently overwrites the prior registration (`character_package.py:74-94`).

The package JSON advertises `ground_locomotion`, `flight_locomotion`, `actions`,
`speech_overlay`, `pose_showcase`, and `semantic_visual_advice`. These are labels,
not machine-queryable capability records with supported facings, clips, channels,
limits, quality tiers, or fallback behavior
(`definitions/wizard_joe_character_package.json:1-16`).

### 2. Snapshot rig and procedural fallback

The production-preferred path loads 89 `ReferencePose` objects. Each contains
dimensions, one root anchor, a map of anchors, and colored cells
(`wizard_avatar/reference_avatar.py:20-35`, `50-92`). It lazily caches the parsed
library, pose map, and rendered local canvas by resolved path and pose ID, then
copies a canvas before applying face overlays (`reference_avatar.py:38-47`,
`150-167`).

This is a **snapshot rig**:

```text
world root (x,z,altitude)
  -> perspective projection and quantized scale
  -> one complete authored 72x96 pose canvas
  -> eye, brow, and mouth pixel overlays when detectable
  -> root-anchored nearest-neighbor stage blit
```

It is not a conventional articulated rig. There are no parent-child joint paths,
rest transforms, bind transforms, joint rotations, skin weights, per-joint limits,
or IK chains. The file named `skeleton.py` belongs to the procedural fallback: it
computes independent integer offsets and hard-coded wrist targets from a front
anchor table (`wizard_avatar/skeleton.py:9-64`; `anchors.py:6-34`). Those targets
do not deform the 89 authored snapshots.

The authored-pose anchors are still valuable. `root`, eyes, mouth, feet, hands,
staff hand, and staff tip can support attachment, face overlay, contact tests, and
semantic correspondence. They are insufficient for general arm, spine, head,
or leg retargeting because shoulders, elbows, hips, knees, neck, and a hierarchy
are absent.

### 3. Pose graph and runtime selection

Graph v2 is richer than the runtime behavior. It models:

- pose role, altitude, support contact, planted anchor, wing/staff mode, and tier;
- clips with family, facings, loop mode, phase source, root policy, minimum hold,
  interrupt policy, channel ownership, samples, markers, curves, and legal
  successors;
- nodes with mobility and actions;
- transitions with timing, phase, contact, root, region, interrupt, and fallback
  policy (`wizard_avatar/animation_graph.py:75-212`).

Clip evaluation is deterministic integer math from 60 Hz ticks to 24 fps authored
frames, while walk clips can evaluate from normalized distance phase
(`animation_graph.py:214-294`). The parser strictly validates many graph
cross-references and computes a canonical SHA-256 of graph JSON
(`animation_graph.py:661-875`).

Production selection does less. A diagnostic pose override wins first. Otherwise
action wins over airborne state, airborne state over ground locomotion, and ground
locomotion over facing idle. On a node change, the selector chooses a transition
record, stores its ID, resets the target clip, and immediately evaluates the target
clip (`wizard_avatar/pose_selection.py:50-107`, `110-193`). The frame source then
forces transition progress to 1.0 because partial cell dissolves create false
limbs (`wizard_avatar/frame_source.py:159-181`).

That whole-pose policy is appropriate for the current art. The gap is that graph
fields implying marker-gated interruption, minimum holds, contact locks, region
masks, secondary curves, and transition recipes are not runtime policy. Metadata
must either become executable or be labeled non-operative so downstream score
planning cannot overestimate the rig.

### 4. Layering and state precedence

Current effective precedence is:

1. diagnostic pose override;
2. selected full-body action;
3. flight mobility;
4. ground locomotion;
5. facing idle;
6. face, eye, brow, and mouth pixel overlays.

The graph declares channel masks for body, staff, wings, mouth, and effect. None
of the 277,285 pose cells has a `region` field, even though the pose schema allows
one (`reference_avatar_pose_cells.schema.json:180-207`). Therefore only the
specialized face overlay is presently composited independently. There is no
general upper-body layer, staff layer, wing layer, or region-aware blend.

Speech demonstrates the limitation. If a real `speech_id` is active, production
pose selection suppresses the explaining body action
(`wizard_avatar/pose_selection.py:141-150`). This avoids destructive whole-body
replacement, but it also means the manifest's `speech_overlay` capability is more
specific than a consumer could know: mouth/face overlay works; body gesture
layering does not.

### 5. Deterministic command and runtime core

The ordered command system is a real capability. `CommandEnvelopeV1` carries a
stable command ID, source identity and epoch, increasing source sequence, command
kind, immutable payload, optional issue time/tick and TTL, lease, duration ticks,
and priority (`wizard_avatar/commanding.py:118-169`). The inbox provides bounded
capacity, deduplication, stale-sequence rejection, deterministic same-tick ordering,
and acknowledgements (`commanding.py:306-425`).

The runtime uses exact 60 Hz ticks, canonical float-preserving state hashes,
immutable snapshots, and an NDJSON replay log (`wizard_avatar/runtime.py:15-67`,
`90-173`, `176-301`). This is an excellent base for reproducibility.

It is not yet the audiobook scheduler:

- `COMMAND_KINDS` has no media session, character selection, score load, seek,
  playback-rate, gaze, cue cancellation, or state-reconciliation command
  (`commanding.py:30-46`).
- The command envelope has no `session_id`, `media_id`, `character_id`, `score_id`,
  `cue_id`, media timestamp, media epoch, or media-time expiration.
- The inbox accepts commands no more than 120 simulation ticks ahead, or two
  seconds (`commanding.py:11-15`, `360-368`). A full score must not be pushed into
  this queue.
- Public HTTP and WebSocket commands normally apply on the next avatar tick. The
  `apply_tick` capability exists internally, but is not an envelope field and is
  not exposed by the server path (`runtime.py:242-255`; `stream.py:119-126`).
- The runtime advances from `time.perf_counter_ns()`, not media time
  (`stream.py:151-190`). That is correct for simulation, but it cannot be treated
  as the authoritative audiobook clock.

### 6. PrismGT boundary

PrismGT already has useful media primitives:

- a single hidden HTML audio element is the player (`src/pages/PrismDodecahedron/index.jsx:3585-3590`);
- normalized tracks carry ID, type, URL, source, captions, lyrics, and transcript
  URLs (`musicLibrary.js:33-77`);
- the live analyzer reads the audio element's actual `currentTime` and duration
  every analysis frame (`musicMotion.js:314-329`);
- bundled and managed media are represented by `/api/library`, while generated
  ElevenLabs tracks persist metadata, audio, captions, and alignment under a local
  audiobook store (`crates/prism-cdiss-cli/src/audiobooks.rs:83-117`, `242-275`,
  `319-350`, `449-470`).

The current boundary is visualizer-specific audio reactivity, not a connector.
The analyzer listens only for play, pause, ended, and loaded metadata
(`musicMotion.js:351-385`). It does not emit seeking/seeked, ratechange, waiting,
playing-after-buffering, chapter, track-session, or monotonic sequence events.
The UI derives progress from React audio metrics and throttles those updates to
about 90 ms (`index.jsx:611-620`, `2858-2878`). That throttled display state must
not become scheduler authority.

Prism media metadata is also not yet a stable processing identity. Browser uploads
are MP3-only and receive a random selection UUID rather than a file-content hash
(`src/lib/media-normalize.js:7-39`). The library shape has no package/character,
score version, canonical external URL, or performance-cache references. Studio
chapters do have a useful project/chapter/snapshot-derived cache ID, but generated
tracks use a fresh UUID and are not content-deduplicated
(`audiobooks.rs:319-342`, `379-388`).

## Professional and primary-source standard

These sources are used as architecture references, not as a recommendation to
replace the square-cell renderer with a 3D engine.

1. **A rig contract distinguishes hierarchy, ordering, and transform spaces.**
   The current glTF 2.0 specification defines a right-handed coordinate system,
   units, ordered joints, a common skeleton root, and inverse bind matrices. This
   is the minimum kind of explicitness needed if a future character adapter claims
   skeletal retargeting. [Khronos glTF 2.0 Specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)
2. **Rest, bind, local, skeleton, and world spaces must not be conflated.** OpenUSD
   describes ordered joints, world-space bind transforms, and local-space rest
   transforms; its introduction explains how local joint transforms accumulate
   into skeleton and world spaces. [OpenUSD `UsdSkelSkeleton`](https://openusd.org/release/api/class_usd_skel_skeleton.html),
   [OpenUSD UsdSkel Introduction](https://openusd.org/25.05/api/_usd_skel__intro.html)
3. **Retargeting is an explicit source-to-target mapping problem.** Epic's current
   IK Rig documentation supports transfer between characters with different
   proportions and skeletons through source and target rig assets. Wizard Joe
   needs an equivalent semantic map, even when the target is a snapshot set
   rather than a deforming mesh. [Epic Games, IK Rig](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-ik-rig),
   [Epic Games, Retargeting Bipeds with IK Rig](https://dev.epicgames.com/documentation/unreal-engine/retargeting-bipeds-with-ik-rig-in-unreal-engine?lang=en-US)
4. **Layers require declared ownership and masks.** Epic's animation slots and
   layered-blend documentation distinguish full-body overrides from upper-body
   slots and define blend masks/branch filters. The analogous square-cell system
   needs actual region data or an explicit declaration that a clip is whole-body
   only. [Epic Games, Animation Slots](https://dev.epicgames.com/documentation/unreal-engine/animation-slots-in-unreal-engine),
   [Epic Games, Animation Blueprint Blend Nodes](https://dev.epicgames.com/documentation/unreal-engine/animation-blueprint-blend-nodes-in-unreal-engine?lang=en-US)
5. **The media element owns playback position.** The WHATWG HTML media model
   defines `currentTime` as the official playback position and specifies seek,
   waiting, and rate behavior. PrismGT should publish that state; the character
   scheduler should not integrate a parallel clock. [WHATWG HTML Standard, Media Elements](https://html.spec.whatwg.org/multipage/media.html)
6. **Timed-event delivery needs measurement and lookahead.** W3C's media timed
   events requirements discuss synchronization of web content to media timelines
   and the limitations of ordinary event delivery. This supports a state resolver
   plus bounded lookahead rather than one wall-clock timeout per cue.
   [W3C, Requirements for Media Timed Events](https://www.w3.org/TR/media-timed-events/)
7. **Asset schemas should be executable validation contracts.** JSON Schema Draft
   2020-12 provides structural validation, array constraints, and schema bundling.
   The repository already declares this draft but often performs separate, weaker
   hand validation. [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12),
   [Validation Vocabulary](https://json-schema.org/draft/2020-12/json-schema-validation)
8. **Caching should preserve consistent asset resolution.** OpenUSD's asset
   resolver documentation explains that scoped resolution caches reduce repeated
   work and ensure the same asset path resolves consistently within a scope. A
   character session likewise needs a pinned package digest and immutable resolved
   asset view. [OpenUSD Ar Asset Resolution](https://openusd.org/release/api/ar_page_front.html)

## Findings and required direction

### F1. Critical: the package is a file list, not a reusable character contract

The existing `CharacterPackage` is enough to boot one renderer with alternate
files. It cannot answer the scheduler's essential questions: Can this character
walk while speaking? Which semantic gestures exist? Which clips are full-body?
Which anchors are required? What is the fallback from `hand_to_heart`? Which
facings are supported? Is the package compatible with score schema 2? Has an
asset changed since analysis?

The test named `test_second_character_uses_same_loader_without_runtime_changes`
is useful but overstates production extensibility. Its second character has a
3x3 pose, only `root` and `mouth` anchors, and a minimal graph containing only a
`clips` list. That graph is not graph v2. Rendering succeeds because strict graph
loading fails and `select_reference_pose_sample` catches the exception and falls
back to an idle pose (`tests/wizard/test_character_package.py:21-79`;
`pose_selection.py:67-83`). The test proves alternate snapshot rendering, not
multi-character animation or score portability.

**Required direction:** introduce `CharacterPackageV2` and keep V1 as a migration
adapter. V2 should include:

```text
identity: character_id, package_version, display_name
compatibility: package_schema, score_schema range, runtime_api range
renderer_adapter: asciline_snapshot_v1 | procedural_cells_v1 | future adapter
assets[]: logical role, relative URI, media type, byte size, SHA-256
coordinate_spaces: handedness, axes, units, origins, local canvas convention
semantic_rig: required/optional controls, anchors, joints, rest/bind data if any
capabilities: structured actions, facings, channels, limits, quality tiers
animation_mappings: semantic intent -> ordered clip/pose candidates
channels: ownership, masks, compatibility, blend or handoff policy
fallbacks: requested capability -> fallback chain -> terminal stillness
preload: startup set, lookahead policy, memory budget
validation: package digest and generated validation report
```

Package registration must reject duplicate IDs or require an explicit versioned
selection. The server must expose a registry and `set_character` operation rather
than constructing one source with one optional package path at startup.

### F2. Critical: there is no retargetable control rig

The ten snapshot anchors are a good correspondence layer, but they are not enough
to retarget joint animation. There are no source/target chains, rest pose, bind
pose, joint orientation, limits, scale compensation, or IK goals. The procedural
fallback's shoulder/elbow/hip/knee anchors are hard-coded to Wizard Joe's front
view and are not package data.

**Required direction:** define a renderer-neutral **semantic control rig** first:

```text
root
facing
locomotion_phase
support_contact
gaze_target
head_intent
left_hand_intent / right_hand_intent
staff_hand / staff_tip
mouth_shape or viseme
expression
wing_state (optional)
effect_socket (optional)
```

Each package maps those controls to what it can truly perform:

- Snapshot adapter: choose a coherent pose, then apply only declared overlays.
- Procedural-cell adapter: solve supported anchors and draw ordered layers.
- Future skeletal adapter: map semantic chains to ordered joints and optional IK.

Do not call snapshot pose substitution “retargeting.” Call it semantic remapping.
Only claim skeletal retargeting when a package supplies hierarchy and transform
contracts and passes source-to-target chain tests.

### F3. Critical: declared graph policy is not executable policy

The graph is rich enough to guide a professional scheduler, but the runtime does
not enforce most of it. A score planner that reads `interrupt_policy`,
`minimum_hold_ticks`, `legal_successors`, transition recipes, contact policies,
and channel ownership will expect behavior that production selection does not
deliver.

**Required direction:** create one graph evaluator that owns node state,
transition state, clip phase, markers, holds, interrupt gates, and fallbacks.
Pose selection should consume its immutable presentation result rather than infer
transitions from a changed pose ID. For snapshot art, supported transition
operations should be deliberately small:

- marker-timed whole-pose handoff;
- hold/release at a declared sample;
- contact-preserving root offset;
- approved face/mouth overlay;
- approved region overlay only when region data exists;
- hard cut with an explicit diagnostic reason.

Unsupported recipe types must fail package validation or be downgraded visibly,
not remain inert metadata.

### F4. High: channel ownership exceeds the actual art topology

The graph says clips own body, staff, wings, mouth, and effects, but the pose cells
have no region labels. A generic compositor cannot isolate an arm, staff, wing,
or torso without pixel heuristics. Pixel heuristics are already fragile in the
face path, which searches for eye-colored regions around approximate anchors.

**Required direction:** choose one contract per asset family:

1. **Atomic snapshot:** full-body ownership; only named, validated overlays are
   allowed. This should remain the default for the existing 89 poses.
2. **Regioned snapshot:** every cell has a stable region from a package-declared
   vocabulary; masks are validated for coverage and overlap.
3. **Procedural/skeletal:** channels own named layers or joints with explicit
   composition order.

Do not synthesize a general upper-body blend by cutting existing snapshots at an
arbitrary row. Promote speech-safe full-body poses first, or author regioned
variants with reviewed hand, staff, beard, robe, and wing boundaries.

### F5. High: fallback is silent and can hide broken packages

`select_reference_pose_sample` catches validation, file, key, type, and value
errors around graph loading/evaluation and silently uses legacy pose selection.
It also substitutes the first available fallback pose when a graph sample is
missing. The returned `PoseSample` has no requested ID, fallback reason, fallback
depth, or diagnostic event (`pose_selection.py:67-83`).

**Required direction:** fallback must return and log a structured resolution:

```text
requested_semantic_action
requested_clip_or_pose
resolved_clip_or_pose
fallback_chain
reason_code
package_digest
score_cue_id
media_time_us
severity
```

Package-load failure should be fatal before playback unless the session explicitly
selects a validated compatibility mode. Runtime absence of an optional gesture
may resolve through a package fallback chain ending in `characterful_neutral` or
stillness. An unrelated action is never a valid terminal fallback.

### F6. High: state precedence is hard-coded and blocks portable layering

Action, mobility, locomotion, and facing precedence lives in Python branches.
Speech suppression is another hard-coded exception. A second character with no
wings, no staff, or a true upper-body layer needs different compatibility rules,
but package capabilities cannot express them.

**Required direction:** define precedence in shared engine policy with package
compatibility declarations:

```text
safety/reset/reconnect reconciliation
manual director override
full-body transition or action
locomotion and support contact
upper-body gesture, when package says compatible
prop/wing/effect channels
gaze/head/face
mouth/viseme
```

At each tick, one arbiter should produce a `ResolvedCharacterState` containing
the winning request per channel plus rejected/suppressed requests and reasons.
The renderer consumes that state; it does not decide precedence.

### F7. Critical: the deterministic runtime is not media-time deterministic

The avatar kernel is deterministic for a given command order and tick progression.
The complete experience is not deterministic because PrismGT has not defined a
media session stream and the avatar advances independently from a monotonic clock.
Dispatching score cues with JavaScript timers would reproduce the exact drift the
brief prohibits.

**Required direction:** separate three clocks:

- `media_time_us`: authority from PrismGT's media element;
- `simulation_tick`: avatar's deterministic 60 Hz integration step;
- `presentation_time`: local frame delivery and diagnostics only.

The scheduler should evaluate score state at `media_time_us` and send idempotent
state reconciliation, not an unbounded queue of future cue firings. A bounded
lookahead window is for preload and transition preparation only.

Recommended connector envelope additions:

```text
protocol_version
session_id
media_epoch                 # changes on load/seek/restart discontinuity
media_id
character_id
character_package_digest
score_id / score_version
cue_id
source_sequence
event                       # load/play/pause/seek/rate/chapter/reconcile
media_time_us
playback_rate
playing / seeking / buffering
priority
expires_media_time_us
```

On seek or reconnect, cancel pending work from older `media_epoch` values, query
the score interval index at the new media time, and atomically reconstruct active
locomotion target, facing, pose/clip phase, expression, gaze, speaking state, and
enabled overlays. Do not replay every cue from chapter start.

### F8. High: coordinate spaces are implicit and incompatible with interchange

The present coordinate model can be inferred from code:

- world stage is `(x,z)`, bounded x `[-5,5]` and z `[1.5,10]`;
- positive screen x is viewer-right;
- decreasing world z moves toward the camera;
- local pose coordinates use top-left integer cells with y increasing downward;
- all authored snapshots root at local `[36,95]`;
- projection maps world depth to screen y and a scale quantized to one eighth
  (`wizard_avatar/projection.py:8-40`; `docs/16-world-space-movement.md:48-50`).

The manifest does not state handedness, unit meaning, origin, forward vector,
camera convention, or transforms between stage, character-local, pose-local,
screen, and media-editor coordinates. The older canonical-grid document still
describes a 34x52 character with root `(17,51)`, while current authored assets are
72x96 with root `(36,95)` (`docs/08-canonical-local-grid.md:3-18`). Both can be
historically valid, but a package consumer cannot guess which is authoritative.

**Required direction:** version and name every space. For example:

```text
stage_v1: x right, z away from camera, y up, units = stage units
character_root_v1: origin at projected floor contact, inherited facing
pose_cell_v1: x right, y down, integer cells, origin top-left
screen_cell_v1: x right, y down, integer stage cells
gaze_stage_v1: target point in stage coordinates
```

Each package must declare `pose_local_to_root`, extents, root/contact anchors, and
optional scale calibration. The connector should send normalized stage targets
or explicitly named stage coordinates, never browser pixels. Tests must cover all
eight facings, front/back semantics, root continuity, bounds, and round-trip
serialization.

### F9. High: caches are fast in-process but not content-addressed

Current Python caches are useful:

- background canvases cache by dimensions;
- pose JSON, pose maps, and rendered pose canvases cache by resolved file path;
- parsed animation graphs cache by resolved path;
- a graph carries a canonical JSON SHA-256.

The cache key does not include file content, modification time, package digest, or
schema/runtime version. Replacing a file at the same path leaves stale objects in
a long-running process. There is no package-scoped invalidation, explicit preload,
lookahead API, memory budget, or cache diagnostic. The graph hash is computed
after loading but is not pinned by the character package.

**Required direction:** resolve a session to an immutable asset view keyed by a
package digest. The digest should cover canonical package data plus every declared
asset hash. Use separate caches for validated metadata, decoded pose canvases, and
runtime presentation products. Preload default pose, recovery pose, current score
state, and bounded lookahead candidates. Expose hit/miss, bytes, load latency,
eviction, and digest diagnostics.

Offline performance caches should include at least:

```text
media_content_hash
transcript_content_hash and alignment_version
score_schema and score_content_hash
planner/model/prompt versions and seed
character_id and package_digest
pose_library_digest and graph_digest
runtime_mapping_version
user intensity/reduced-motion profile version
```

A changed character package should normally invalidate only character resolution
and derived preload products, not transcription or narrative analysis.

### F10. Medium: runtime budgets and preload failure behavior are unspecified

Lazy canvas caching avoids repeated rasterization after first use, but the first
use of an unseen pose can occur on a performance beat. There are no measured
budgets for package validation, pose decode, cache memory, graph evaluation,
connector reconciliation, or a multi-character switch. PrismGT's analyzer and
React UI also share the browser main thread with the Three.js scene.

**Required direction:** establish budgets through measurement rather than an
unverified frame-rate claim. At minimum, record package validation time, cold and
warm pose resolution time, preload time, cache size, avatar tick time, render time,
connector dispatch-to-ack time, media-time error at application, and missed frame
or simulation deadlines. A preload miss must preserve the previous stable pose
and emit a diagnostic instead of blocking playback or showing an unrelated pose.

## Target architecture

```text
PrismGT HTML media element
  -> MediaSessionEventV1 (official media time, epoch, sequence)
  -> PerformanceScore interval index
  -> Character-independent desired state
  -> CharacterResolver(package digest, capabilities, mappings, fallbacks)
  -> ResolvedCharacterState + preload requests + diagnostics
  -> idempotent AvatarCommandV2 / acknowledgement
  -> fixed 60 Hz graph and locomotion runtime
  -> renderer adapter
       - Wizard Joe atomic snapshot adapter
       - procedural cell adapter
       - future skeletal adapter
  -> frame hashes, fallback log, timing telemetry
```

### Character-independent score vocabulary

The score should ask for meaning and timing, not Wizard Joe pose IDs:

```text
locomotion: hold | walk_to | turn | enter | exit | optional flight
body_intent: neutral | explain | point | think | sincere | react | celebrate
gesture_phase: prepare | stroke | hold | recover
emotion: named state plus intensity and transition duration
gaze: semantic target or named stage point
speech: active span plus optional viseme track
prop_intent: neutral | plant | present | cast, only when relevant
stillness: explicit hold with allowed micro-motion channels
```

The character package maps this vocabulary to clips and constraints. A score may
carry a preferred semantic action and acceptable alternatives, but never silently
substitute a character-specific clip from another package.

### Package resolution result

Every resolution should return:

```text
requested intent
selected package mapping
selected clip/pose and phase rule
channel ownership
preload asset IDs
fallback path, possibly empty
warnings and quality tier
deterministic resolution hash
```

This artifact makes score editing portable and allows a director to see exactly
why a character did or did not perform a requested beat.

## Acceptance criteria

### CTD-01: strict package validation

Given any package, startup validates the actual JSON Schema plus semantic
cross-references, hashes, renderer compatibility, required anchors/regions, graph
compatibility, and fallback termination. Unknown fields follow an explicit schema
policy. Duplicate character ID/version pairs fail. No playback session can select
an invalid package.

### CTD-02: truthful capability query

`query_capabilities(character_id, package_digest)` returns structured supported
semantic actions, facings, channels, locomotion modes, overlay compatibility,
quality tier, and explicit fallbacks. The response is derived from validated
assets and mappings, not hand-maintained broad strings.

### CTD-03: real second-character portability

A second package with different dimensions, root calibration, missing staff and
wings, and a smaller action set can run the same representative score without a
Python code change. Unsupported intents resolve through declared fallbacks and
produce fallback records. The test must use a valid production graph/adapter; a
strict-graph failure followed by legacy idle does not pass.

### CTD-04: semantic rig conformance

Every package declares required semantic controls and coordinate spaces. Snapshot
packages validate all required anchors on every pose that claims the related
capability. Skeletal packages additionally validate ordered joints, hierarchy,
rest/bind transforms, and chain mappings. Claims distinguish semantic remapping
from skeletal retargeting.

### CTD-05: executable graph policy

Automated tests prove minimum holds, interrupt gates, legal successors, marker
crossings, contact/root policy, phase preservation, and fallback transitions for
representative locomotion, speech, action, flight, interruption, and seek cases.
Every graph field is either executed or schema-marked advisory.

### CTD-06: channel and blend truthfulness

An atomic snapshot package cannot claim a general body-region layer. Regioned
packages prove complete region coverage, legal overlap, deterministic composition
order, and no detached hand/staff/wing artifacts. Speech plus locomotion uses only
declared-compatible channels.

### CTD-07: deterministic media-time resolution

Across two fresh processes, identical media hash, score version, package digest,
seed, and ordered media-event trace produce identical resolution hashes, command
logs, runtime state hashes, selected pose/clip IDs, and frame hashes at sampled
media timestamps. Wall-clock scheduling jitter does not alter cue choice.

### CTD-08: seek and reconnect reconstruction

For forward seek, backward seek, chapter jump, PrismGT restart, and avatar restart,
the first accepted reconciliation for the new media epoch produces the same active
character state as cold evaluation of the score at that media timestamp. No cue
from an older epoch applies, no obsolete gesture replays, and the transition or
hard-cut reason is logged.

### CTD-09: pause and rate behavior

Pause freezes score-driven clip, locomotion, gesture, and speech phase at an
explicit media timestamp. Resume continues from media state, not elapsed wall
time. Playback rates below and above 1.0 preserve cue boundaries and use declared
clip phase/rate policy. Unsupported time scaling falls back explicitly.

### CTD-10: cache invalidation and pinning

Changing one asset byte at the same path changes the package digest and cannot
reuse the old validated or decoded asset view. Unchanged assets hit cache across
repeated loads. A running session remains pinned to one digest until an explicit
package switch. Cache keys and invalidation reasons are visible in diagnostics.

### CTD-11: coordinate conformance

Tests serialize and apply named stage, character-root, pose-cell, and screen-cell
coordinates. All eight facings preserve root contact. Gaze and walk targets sent
through the connector land on the expected side/depth. Character extents, staff,
wings, robe, and effect sockets remain within declared stage bounds or emit a
clamp/fallback event.

### CTD-12: preload and runtime budget

A representative 30-minute playback run records zero simulation catch-up drops
caused by package resolution or preload. Cold asset resolution never blocks a
presentation deadline without a logged miss; the previous stable pose remains
visible. Character switching and lookahead preload report duration and memory,
and stay within project-approved measured budgets.

### CTD-13: fallback observability

Every runtime fallback is queryable by session, media epoch, cue, package digest,
requested capability, selected result, reason, and severity. Acceptance samples
include absent optional gesture, absent facing, corrupt optional asset, corrupt
required asset, incompatible graph, preload miss, and reduced-motion override.

### CTD-14: no-regression boundary

Existing package, pose, anchor, graph-wiring, command, runtime, transport,
projection, locomotion, and visual tests continue to pass. New connector and
package tests do not replace or weaken the existing deterministic replay and frame
hash evidence.

## Recommended implementation order

### P0: make current truth observable

1. Add a package audit command that emits resolved paths, hashes, graph census,
   anchor/region census, operative channels, and fallback risks.
2. Replace silent selector fallback with structured diagnostics while preserving
   existing behavior behind a compatibility flag.
3. Mark current graph fields as operative or advisory in generated capability
   output.

### P1: freeze contracts before adding audiobook cues

1. Define `CharacterPackageV2`, semantic control rig, coordinate-space schema,
   capability schema, mapping schema, and fallback schema.
2. Add a V1-to-V2 Wizard Joe migration adapter and digest calculation.
3. Add registry/query/set-character commands and package-pinned sessions.
4. Define `MediaSessionEventV1`, `AvatarCommandV2`, and acknowledgement fields.

### P2: make the graph real

1. Move node/transition/interrupt/hold/contact ownership into one evaluator.
2. Produce immutable `ResolvedCharacterState` per tick.
3. Keep existing snapshots atomic; enable only validated face/mouth overlays.
4. Promote or author a restrained speech-safe pose set before attempting generic
   upper-body blending.

### P3: connect media-time scheduling and caches

1. Publish PrismGT media events directly from the audio element, including seek,
   rate, waiting, playing, ended, track, and chapter discontinuities.
2. Build score interval lookup, media-epoch cancellation, cold state evaluation,
   and reconnect reconstruction.
3. Add package-digest asset caches and bounded lookahead preload.
4. Measure dispatch, acknowledgement, applied media time, cache, and frame/tick
   behavior.

### P4: prove extensibility

1. Build one deliberately different second character package.
2. Run the same quiet, dialogue, locomotion, emotion, action, music, seek, and
   restart score fixtures against both packages.
3. Review resolution and fallback reports before adding more characters.

## Risk register

| Risk | Severity | Evidence | Mitigation |
|---|---|---|---|
| Broken graph appears to work through idle fallback | Critical | Broad exception fallback; minimal second-character test | Strict startup validation and explicit compatibility mode |
| Planner emits unsupported layered gestures | Critical | Zero pose cells have regions | Truthful channel capabilities; atomic snapshot default |
| Media and avatar clocks drift | Critical | Avatar uses monotonic time; Prism has no connector events | Media-time state resolver and epoch reconciliation |
| Character change reuses stale assets | High | Caches key resolved paths, not content | Package digest, pinned immutable asset view, invalidation tests |
| Package ID collision changes graph globally | High | Mutable global map overwrites by ID | Versioned registry and duplicate rejection |
| Retargeting claim exceeds anchor topology | High | Ten flat anchors; no hierarchy/rest/bind data | Semantic remapping terminology and optional skeletal contract |
| Graph metadata gives false confidence | High | Transition recipe selected but not executed | Operative/advisory declaration and evaluator tests |
| Coordinate mismatch flips depth or gaze | High | Implicit world/cell spaces; legacy 34x52 docs | Named, versioned spaces and conversion tests |
| Cold pose load causes visible hitch | Medium | Lazy unbounded canvas cache; no preload metric | Bounded lookahead preload and stable-pose fallback |
| Multi-character state leaks Wizard Joe assumptions | High | Hard-coded staff, wings, speech suppression, default IDs | Renderer adapter plus package-driven mappings/compatibility |

## Capability and gap summary

| Area | Current capability | Blocking gap |
|---|---|---|
| Rig architecture | Stable root and ten anchors on every authored pose | No articulated hierarchy or semantic control-rig contract |
| Pose graph | Deterministic clip sampling, markers, contacts, transitions as data | Most transition/hold/interrupt policy is not executed |
| Retargeting | Alternate pose library can render through same source class | No valid second-character production graph or semantic mapping proof |
| Layering | Face/eye/brow/mouth overlay on detectable front-facing art | No cell regions; no general upper-body/prop/wing blending |
| Asset contracts | Relative-path containment; default and sample pose checks | No hashes, compatibility, strict schema application, or registry integrity |
| Scheduling | Ordered 60 Hz inbox, dedup, sequence, ACK, replay hash | No media identity/time/epoch; two-second horizon; wall-clock runtime |
| Caching | Lazy JSON, graph, canvas, and background caches | Path-keyed stale cache, no preload/budget/diagnostics |
| Coordinates | Tested world projection and root-stable facings | Spaces and units are not package or connector contracts |
| PrismGT boundary | Real media `currentTime`, local tracks/captions/alignment | No connector event model, character package, score, seek/rate/chapter state |

## Direct conclusion

The correct next step is **not** to build a universal bone rig beneath the current
art. Wizard Joe's atomic snapshots are a valid renderer target and should remain
stable. The required technical-direction work is to put a truthful semantic rig,
strict versioned package, executable pose graph, content-addressed asset view, and
media-time reconciliation interface above that target.

Once those contracts exist, Wizard Joe can use his authored snapshots, a future
procedural character can use joint-like anchors, and a later skeletal character
can use real retargeting without forcing the audiobook score or PrismGT connector
to know which renderer is underneath. Until the second-character and media-time
acceptance tests pass, the goal is **partially supported, not multi-character or
audiobook-production ready**.
