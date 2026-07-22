# Character Director V6 Directional Walk Technical Review

**Candidate:** `85c767ba9c39693536cf6c707a5716f93d08c963`  
**Baseline:** `bc388c0`  
**Evidence:** `/tmp/v6-capture-47c7598`  
**Review role:** Independent senior real-time animation systems reviewer  
**Verdict:** **FAIL - V6 is not ready for acceptance**

## Executive Verdict

The candidate's runtime provenance, transport capture, contact/root arithmetic,
browser delivery, and immutable evidence binding are credible. The supplied
machine report is reproducible from the clean proof checkout and all 57 focused
tests pass. Those facts do not prove the visible directional performance.

V6 fails on two release-blocking animation defects:

1. The new profile walk cycles do not animate a step. Each "passing" graph is
   exactly the corresponding idle profile translated upward by one cell. The
   same rigid standing silhouette is used for both left-foot and right-foot
   contacts while the root travels across the stage. The result reads as a
   bobbing glide, not an alternating side walk.
2. The 90-degree turn and 180-degree reversal are state-machine turns, not
   rendered turns. `presented_facing` advances through sectors, but the visible
   pose holds and then hard-cuts between front, right-profile, and left-profile
   silhouettes. During the reversal, the staff, wings, body, and facing swap
   sides in one frame while the trace still reports an intermediate facing.

The machine acceptance report explicitly says visual review remains required;
normal-speed, quarter-speed, contact-sheet, and frame-by-frame review expose the
defects that its current predicates do not measure.

## Findings

### [High] The profile "walk" is a rigid translated idle pose with synthetic contact alternation

The V6 source manifest defines:

- `walk_profile_left_passing` as
  `derived_translation:profile_left@0,-1`.
- `walk_profile_right_passing` as
  `derived_translation:profile_right@0,-1`.

Independent graph comparison confirms that every colored cell in each passing
pose is the source profile cell at `(x, y - 1)`, with identical cell counts:

| Direction | Idle cells | Passing cells | Exact transform |
| --- | ---: | ---: | --- |
| left | 2,749 | 2,749 | all cells translated `(0, -1)` |
| right | 3,068 | 3,068 | all cells translated `(0, -1)` |

The clips in
`wizard_avatar/definitions/reference_avatar_animation_graph_v2.json` then use
the same idle profile pose for both the left-foot and right-foot contact
samples. Only the declared contact and planted anchor change. No leg, foot,
pelvis, robe, arm, wing, or staff pixels exchange position between those two
contacts. The passing sample only lifts the entire rigid silhouette one cell.

The retained trace makes the semantic mismatch explicit:

- `walk_left`: 84 frames, 42 `profile_left`, 42 translated passing frames;
  metadata reports 21 left contacts and 21 right contacts.
- `walk_right`: 49 frames, 28 `profile_right`, 21 translated passing frames;
  metadata reports both left and right contacts.
- The contact verifier reports 22 stances and zero planted-anchor drift, but it
  verifies the declared anchors and their raster spans. It does not prove that
  the visible legs alternated or that a planted foot visually remained fixed.

At normal speed the character slides laterally with a two-height bob. At
quarter speed the lack of stride, toe-off, passing-leg separation, and weight
transfer is unambiguous. This does not satisfy the V6 requirement for an
alternating directional walk without skating.

**Required correction:** Author or deterministically derive distinct left
contact, passing, right contact, and opposite passing pixel graphs for each
profile direction. Each contact graph must show a visibly different support
leg and foot placement. Add a visible-foot occupancy/trajectory gate that
tracks the actual colored foot component, rather than accepting contact labels
alone.

### [High] The 90-degree and 180-degree turns are hard silhouette cuts hidden by facing metadata

The 90-degree turn records the following trace progression:

| Frame | Presented facing | Clip | Rendered pose |
| ---: | --- | --- | --- |
| 36 | south | `walk_front` | `walk_front_left` |
| 41 | southeast | `walk_front` | `walk_front_left_to_right` |
| 46 | east | `walk_right` | `profile_right` |

The visible character therefore remains in the front family until frame 45 and
hard-cuts to the full right profile at frame 46. There is no locomotion turn
pose that renders the southeast sector as a coherent body orientation.

The 180-degree reversal is more severe:

| Frame | Presented facing | Clip | Rendered pose |
| ---: | --- | --- | --- |
| 91-94 | southeast | `walk_right` | right-profile passing |
| 95 | southeast | `walk_left` | `profile_left` |
| 96-98 | south | `walk_left` | `profile_left` |
| 99-100 | south | `walk_left` | left-profile passing |
| 101-102 | southwest | `walk_left` | left-profile passing |

At frame 95 the entire silhouette flips from right profile to left profile,
including the staff and wing arrangement, while `presented_facing` still says
`southeast`. The metadata continues through south and southwest while the
rendered graph is already fully left-facing. The 90-degree and 180-degree
machine checks in `tools/analyze_character_director_v6.py` count sector changes
from `presented_facing`; they do not compare those sectors with the rendered
pose orientation or measure silhouette continuity.

Baseline `bc388c0` had no `walk_left` or `walk_right` clips and routed horizontal
travel through the front walk. Thus the pre-V6 runtime also lacked a valid
directional turn, but it did not contain these new side-walk handoffs. V6 adds
direction-aware clip selection without supplying the visual bridge needed to
meet its own acceptance requirement.

**Required correction:** Add coherent quarter-turn and reversal bridges, or an
explicit authored atomic-turn design whose cut is motivated by an anticipation
and planted pivot. The evidence must show the rendered orientation agreeing
with every claimed facing sector. A V6 gate should fail when a full-profile
pose is emitted for south/southeast/southwest or when whole-silhouette change
exceeds the approved turn-cut bound.

### [Medium] The V6 acceptance gate encodes the flawed implementation instead of the visible requirement

`tools/analyze_character_director_v6.py` considers a directional clip valid
when its pose set is exactly:

- `{profile_left, walk_profile_left_passing}`, or
- `{profile_right, walk_profile_right_passing}`.

It also accepts contact continuity when contact strings alternate and clip
switches land on a declared contact. The test fixture in
`tests/wizard/test_character_director_v6_acceptance.py` reproduces this same
two-pose structure. Consequently, a rigid idle silhouette with alternating
labels is the expected passing fixture.

The analyzer's `review_boundary` correctly states that machine checks do not
replace visual judgment. The resulting green report is internally consistent,
but its headline `passed: true` is too easy to misread as V6 performance
acceptance.

**Required correction:** Separate `machine_integrity_passed` from
`animation_acceptance_passed`, and add raster-derived predicates for visible
foot alternation, rendered-facing agreement, and silhouette change at turn
handoffs. Keep independent normal/quarter-speed review as a mandatory final
gate.

## Passing Areas

### Deterministic pixel-graph provenance

- The candidate adds only two derived side-walk graphs; both retain explicit
  `derived_translation:` provenance.
- The loader rejects translated graphs that lose that provenance.
- Deterministic generation completed successfully.
- The generated graphs are runtime colored-cell data, not PNG/SVG render
  assets.
- All cells remain within the canonical 72x96 pose canvas, and the canonical
  root remains `[36, 95]`.

This provenance is deterministic and auditable. The failure is the artistic
and kinematic content of the derived graphs, not their reproducibility.

### Contact and world-root arithmetic

The retained contact report passes with:

- 211 trace frames;
- 128 contact frames;
- 22 stances;
- maximum planted-anchor drift: `0.0` cells;
- maximum planted raster-span drift: `1.0` cell;
- maximum root residual: `0.0` cells.

The V6 report measures a maximum world-root step of
`0.06250000000000044`, final target error `0.0`, 31 zero-speed suffix frames,
and no stage clipping. The stop reaches `(-2.4, 3.8)` and settles to
`idle_left/profile_left`. Commit `85c767b` changing profile idle/stop root
handling to contact-locked behavior corrects the arithmetic drift seen before
that fix. It does not create visible stepping or turning.

### Transport and browser integrity

The normal evidence is contiguous and usable:

- 211 trace/manifest frames: 210 capture-owned plus one unowned frame at index
  78;
- 210-frame H.264 normal video, 960x540, 24 FPS, 8.75 seconds;
- no decoded gaps, decoder errors, or dropped frames;
- atomic frame/state pairing;
- clean runtime checkout at the candidate commit and tree.

The browser evidence also passes its intended delivery checks:

- 210-frame H.264 capture, 1280x634, 24 FPS, 8.75 seconds;
- correct 240x135 logical canvas and 960x540 backing store;
- zero decode errors, zero dropped frames, zero resyncs, and no page/console
  errors;
- queue high-water mark of two frames.

The browser recorder reports 45 duplicate samples, 18 held frames, and 195
presented frames during its sampling interval. That makes it layout/delivery
evidence rather than frame-exact animation evidence. The immutable normal
capture and trace provide the frame-exact source of truth, so this is a
residual limitation rather than an additional failure.

### Evidence binding

Strict bundle validation passes. The capture manifest binds 73 artifacts and
all recorded hashes match. The runtime binding identifies:

- head `85c767ba9c39693536cf6c707a5716f93d08c963`;
- tree `e81673e69ebbd4abe3a40e0f8a89b738b3a87604`;
- clean proof branch `codex/v6-proof-47c7598` at capture start and end;
- runtime epoch `wizard-runtime-af77e3419cca41538746fc1146afe525`.

The review-bundle manifest binds the capture manifest, machine report,
quarter-speed derivative, browser metrics, and browser video. Re-running the
V6 analyzer from the exact proof checkout produced a byte-identical machine
report with SHA-256
`890b20006b30c150e435203adf50af863ee1a15f683e809d8cdba0af967bdc98`.

## Media Review

| Artifact | Probe result | Review result |
| --- | --- | --- |
| `visual-review-e6a51fe3698b-capture.mp4` | 960x540, 24 FPS, 210 frames, 8.75 s | Exposes front-to-profile and profile-to-profile cuts; side travel reads as glide/bob. |
| `v6-quarter-speed.mp4` | 960x540, 24 FPS, 840 frames, 35.0 s | Confirms no hidden stride or pivot frames. Sampled normal/slow decoded-frame MAE was 0.149-0.319 due to light re-encoding, with matching content. |
| `v6-browser-layout.mp4` | 1280x634, 24 FPS, 210 frames, 8.75 s | Canvas, controls, and WebSocket delivery remain stable; not a frame-exact motion source because of held/duplicate screencast samples. |
| Contact sheet and event PNGs | 66 retained samples | Frames 41/46 and 91/95 make the hard silhouette handoffs visible. |

## Commands and Evidence Examined

The review used, among other inspections:

```text
git log --oneline bc388c0..85c767b
git diff --stat bc388c0..85c767b
git diff bc388c0..85c767b -- <runtime, graph, generator, analyzer, tests>
git diff --check bc388c0..85c767b

python3 -m unittest \
  tests.wizard.test_character_director_v6_acceptance \
  tests.wizard.test_contact_verifier \
  tests.wizard.test_pose_selection \
  tests.wizard.test_reference_avatar_pose_library
# 57 tests: PASS

python3 tools/generate_reference_avatar_pose_cells.py \
  --check-deterministic --reuse-authored-library
# Deterministic generation: PASS

python3 /private/tmp/wizardjoe-v6-proof-47c7598/tools/analyze_character_director_v6.py \
  --manifest /tmp/v6-capture-47c7598/manifest.json
# Byte-identical machine report: PASS

ffprobe -show_entries \
  format=filename,duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames \
  /tmp/v6-capture-47c7598/*.mp4

ffmpeg -i <normal-video> -vf select=<turn/reversal/stop-ranges>,tile=<grid> <sheet.png>
shasum -a 256 /tmp/v6-capture-47c7598/<artifact>
```

The evidence reviewed includes `manifest.json`,
`animation_truth_trace.ndjson`, `contact_verification.json`,
`v6-machine-acceptance.json`, `review-bundle-manifest.json`, normal/quarter/
browser videos, browser metrics, contact sheet, all event PNGs, wire index/data,
scenario program, candidate source, and baseline source.

## Residual Risks After Required Fixes

1. The left and right authored profile sources are not symmetric (2,749 versus
   3,068 cells). A direct profile swap will remain visually discontinuous even
   after valid gait frames exist unless turn bridges account for the different
   staff, wing, hat, and body topology.
2. Contact verification can still be gamed accidentally by plausible anchor
   metadata over the wrong visible foot. Raster connected-component tracking
   or explicit foot masks are needed for stronger proof.
3. The stop clip changes declared support from left to right while rendering
   the same `profile_left` graph. It is mathematically grounded but does not
   communicate a visible weight settle.
4. The browser screencast sampler is suitable for integration/layout review,
   but its duplicate/held frames should not be used to judge one-frame turn
   timing.

## Explicit Acceptance Decision

**FAIL. Do not accept V6 or advance this candidate as proof of directional
walking, a 90-degree turn, or a 180-degree reversal.**

The candidate may be retained as a deterministic transport/state-machine
prototype. V6 should be recaptured and independently reviewed only after the
side gait contains visibly distinct foot phases and the turn/reversal is
rendered coherently rather than inferred from `presented_facing` metadata.
