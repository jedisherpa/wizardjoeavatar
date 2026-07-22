# V6 Directional Walk Independent Animation Review

**Candidate commit:** `ee4d6360a169fab91f9680c7e0c12248fa439e49`  
**Immutable proof:** `/tmp/v6-capture-ee4d636`  
**Clean proof checkout:** `/tmp/wizardjoe-v6-proof-ee4d636`  
**Reviewer role:** Independent game-animation, choreography, acting, and body-language reviewer  
**Decision:** **FAIL - DO NOT ACCEPT V6**

## Executive Judgment

Candidate `ee4d636` is a major and credible improvement over the rejected V6
submission. It replaces the rigid profile glide with four genuinely distinct
gait phases in each direction, performs both turns through authored diagonal
and crossover silhouettes, keeps feet locked to declared contacts, reaches the
exact target, and remains inside the canonical stage. The movement now reads as
a character walking and changing direction rather than as a translated static
sprite.

It does not yet pass V6. The normal-speed performance still exposes three
blocking continuity defects, and quarter speed makes them unambiguous:

1. the facing state leads the rendered body during the 90-degree turn;
2. the staff and whole-body placement jump at authored pivot boundaries,
   especially frames 47-48 and 90-91; and
3. the final stop changes from an active stride to the static `profile_left`
   endpoint without a visible braking/compression/recovery settle.

The reversal has the correct pose order and is readable as a 180-degree change,
but its central staff crossover is not physically continuous. Machine
acceptance is correctly green for topology, contact, target, and framing; its
own review boundary says those checks do not replace this visual judgment.

## Evidence And Provenance Reviewed

- `visual-review-aed33d82b2dc-capture.mp4`: 960x540, 210 frames, 24 fps,
  8.75 seconds, reviewed at normal speed.
- `v6-quarter-speed.mp4`: 960x540, 840 frames, 24 fps, 35.00 seconds,
  reviewed for held contacts, pivot boundaries, prop paths, and settle timing.
- `v6-browser-layout.mp4`: 1280x634, 210 frames, 24 fps, 8.75 seconds.
- `visual-review-aed33d82b2dc-contact-sheet.png`.
- All ordinary and event-selected frames under `samples/`, with focused review
  around frames 35-58, 68-105, and 151-169.
- `animation_truth_trace.ndjson`, 210 contiguous records, frames 0-209.
- `contact_verification.json`.
- `v6-machine-acceptance.json`.
- `v6-browser-layout-metrics.json`.
- `scenario-program.json`, `manifest.json`, and
  `review-bundle-manifest.json`.

Both the working tree and proof checkout resolve to the full candidate SHA. The
proof checkout is clean. The reviewer made no runtime or source changes.

## What Now Passes

### Directional gait and cadence

Both profile directions now use four authored phases: left contact, passing to
the opposite foot, right contact, and return passing. The right-facing phrase
at frames 58-75 and sustained left-facing phrase at frames 101-160 show clear
leg opposition, changing robe shapes, and alternating support. This is no
longer the one-cell rigid bob rejected in candidate `85c767b`.

At normal speed, the side walk has a readable limited-animation rhythm. At
quarter speed, each held drawing remains complete and the order is coherent.
The longer westbound phrase loops cleanly without phase reset at the reversal
handoff.

### Readable 90-degree and 180-degree directional ideas

The 90-degree phrase visibly includes `turn_south_east_33` and
`turn_south_east_67` before the east profile. The 180-degree phrase visibly
orders:

`walk_profile_right_contact_right` -> `turn_south_east_67` ->
`turn_south_east_33` -> `turn_front_crossover_plant` ->
`turn_south_west_33` -> `turn_south_west_67` ->
`walk_profile_left_contact_left`.

There is no adjacent full-right-profile to full-left-profile substitution. The
front crossover gives the reversal a visible center and the silhouette tells a
clear east-to-west story.

### Contact, target, and framing

The declared-contact evidence is strong. Across 190 contact-bearing frames and
18 stances, maximum planted-anchor drift is effectively zero
(`2.842170943040401e-14` cells), raster-span drift is one cell, and the report
contains no issues. The root reaches `(-2.4, 3.8)` with zero target error and
finishes with 49 zero-speed frames.

No frame clips the 240x135 canonical stage. The 960x540 projector image and the
1280x634 browser composition remain unobstructed. Hat, face, robe, feet, wings,
hand, and staff are complete in all sampled drawings.

## Blocking Findings

### 1. Facing leads the body during the 90-degree turn

Frames 41-44 are labeled `southeast` while still rendering
`walk_front_left_to_right`. Frames 45-47 are labeled `east` while rendering the
front-family `walk_front_left_to_right` and `walk_front_right` drawings. The
first authored diagonal body drawing does not appear until frame 48.

The audience therefore sees the front-facing walk continue after the travel
path has already bent east, followed by a late pivot. The authored turn itself
is readable, but the state/body timing makes the action feel reactive and
slippery rather than led by gaze, torso, and planted foot. It also violates the
resubmission contract that rendered graph orientation match every
`presented_facing` sector.

**Required correction:** delay the presented sector changes until the matching
diagonal/profile drawings appear, or begin the authored pivot before the
sector changes. The character's chest, face, and facing truth must agree on
every presented frame.

### 2. Staff and body continuity break at pivot boundaries

The staff remains complete, but it does not follow one continuous physical
arc. At frame 47-to-48, the staff tip moves about `46.88` stage cells and the
presented root changes about `21.90` stage cells as the first diagonal graph is
introduced. At frame 90-to-91, the staff tip crosses about `42.80` stage cells
and the presented root changes about `13.14` stage cells between the front
crossover and west-diagonal graph.

Contact locking keeps the declared foot stable, so these are not world-root
teleports. They are local construction jumps around that foot. At normal speed
they read as a pop in the staff/hand/torso package. At quarter speed the staff
clearly disappears from one side of the body and reappears on the other without
an intermediate hand path through center.

Wing topology is intact and its front-to-profile occlusion order is broadly
correct, but the same boundaries change wing width and overlap as one rigid
package. There is no secondary lag or recovery to soften the swap. The robe
also changes volume abruptly at those boundaries.

**Required correction:** normalize adjacent turn graphs around the same planted
foot and physical grip, then author or rig intermediate staff placements so the
tip advances in a short ordered arc. Preserve shaft length and hook identity;
carry wing and robe overlap through the same progression instead of resolving
all layers on one frame.

### 3. The final stop holds, but does not settle

The west walk is strong through frame 160. Frame 161 replaces
`walk_profile_left_passing_left_to_right` with static `profile_left` under
`stop_left`; support becomes both feet at frame 164, and `idle_left` begins at
frame 169 with the same visible profile graph. Frames 169-209 are an exact
static hold.

The target arrival and absence of drift pass. The acting does not. There is no
visible shortening step, braking plant, knee/robe compression, upper-body
follow-through, staff recovery, or modest rebound into idle. The body simply
ceases cycling and adopts the endpoint. That is functional game control, but
not the authored stop/settle performance required by V6.

**Required correction:** add a brief west stop phrase that lands from the
actual incoming gait phase, absorbs momentum while the root remains at the
target, and recovers into `profile_left`. A small two- or three-drawing settle
is enough if the weight change is visible and staff/wing follow-through remains
coherent.

## Criterion Decisions

| Criterion | Verdict | Independent review |
| --- | --- | --- |
| Anticipation | **Marginal** | The reversal receives a two-frame profile plant at frames 76-77 and a contact-led entry, but the 90-degree turn begins after facing/path changes and does not clearly anticipate them. |
| Weight transfer | **Marginal** | Opposed stride drawings and exact contacts create credible gait weight; large local construction jumps at turn boundaries and the unperformed final settle weaken it. |
| Readable 90-degree turn | **Fail** | The authored diagonal drawings are readable, but frames 41-47 present southeast/east state with front-family bodies before the late pivot. |
| Readable 180-degree reversal | **Pass with continuity defect** | The seven-drawing east/front/west phrase is unmistakable and correctly ordered. Staff/hand continuity still fails independently. |
| Gait continuity | **Pass** | Four distinct phases per direction, correct ordering, coherent west loop, and no profile-cycle reset. |
| Foot skating | **Pass** | No perceptible planted-foot slide in the reviewed sequences; machine drift is effectively zero with only one-cell raster-span variation. |
| Staff continuity | **Fail** | Complete drawings, but approximately 46.88-cell and 42.80-cell adjacent tip jumps break the physical arc. |
| Wing continuity | **Marginal** | Complete and directionally ordered, but overlap and volume resolve too abruptly at the same pivot cuts. |
| Robe continuity | **Marginal** | Gait hems communicate stepping; turn-boundary volume changes and the stop endpoint substitution still pop. |
| Stop/settle | **Fail** | Exact stop and stable hold, but no visible absorption or recovery phrase. |
| Canonical framing | **Pass** | Zero clipped frames; character and props remain complete in capture and browser presentation. |
| Machine acceptance | **Pass** | All 12 checks pass; this does not supersede the visual gate. |

## Residual Risks And Next Review Focus

1. Once facing timing is corrected, recapture must prove that the change does
   not reintroduce a front-to-profile cut or delay control response beyond the
   two-frame response gate.
2. Staff normalization can preserve the tip while accidentally sliding the
   grip in the hand. The next trace/review should measure both grip and tip,
   not tip alone.
3. Additional stop drawings can break the currently excellent contact and
   exact-target result. The stopping foot must remain locked while the upper
   body, robe, wings, and staff settle locally.
4. The right-facing gait receives only one cycle in this scenario. After the
   blockers are fixed, include enough rightward travel to judge a repeated loop
   boundary as confidently as the westward loop.
5. The browser capture reports 22.68 presented fps for this short run despite
   no drops or decode errors. It does not visibly corrupt this proof, but later
   integrated acceptance should still enforce the production cadence window.

## Resubmission Bar

V6 may pass only after a clean immutable recapture demonstrates all of the
following at normal and quarter speed:

1. presented facing and rendered body orientation agree throughout the
   90-degree and 180-degree phrases;
2. staff grip and tip travel continuously through both pivot sequences without
   the current large adjacent jumps;
3. wing and robe occlusion progress through the turns without a package pop;
4. the final westbound stride performs a visible braking plant and recovery
   into idle;
5. four-phase gait order, planted-foot lock, exact target arrival, and zero
   clipping remain at least as strong as this candidate.

## Artifact Hashes

| Artifact | SHA-256 |
| --- | --- |
| Normal-speed video | `1fa56a03975f7e92811102969a7638974c8602577cddabedc99664054666c503` |
| Quarter-speed video | `b0026e55e1d50686caae4d94ab7454606ea4e1c8eaa965521ae826711d54463a` |
| Contact sheet | `ea320f219815950fe2d8882f6718889cb79663d8fb3eb5c957d6ec5882a95d23` |
| Truth trace | `8e4d51dc8e624a5cb1c44db6420e1631b23e8cffdc5f6703cab3c5dd0428672c` |
| Machine acceptance | `97cf31afebdf81380228c167f278abe3df74e6944edd1a8758900f803c42d838` |
| Contact verification | `4671ba85c61ead0543ba1c72c31401b7fe8664261093177b5806bceb31d96307` |
| Capture manifest | `b826efe162150a67e2ee9407b92ca75077b56a215e59cb5f2c8988e991597f9b` |
| Browser video | `32aac59e411e6616f9bc171107d2778e52d6b4b04452d2093b221da8ba426c45` |
| Browser metrics | `c9dc2d0513fa4dc291c5e979ae32ee58498cb4997d065bc550c84057c4020c3b` |

## Final Verdict

**FAIL.** Candidate `ee4d636` solves the prior V6 submission's largest content
defects: it has real directional gait graphs, a readable authored 90-degree
pivot, and a readable authored 180-degree reversal with excellent planted-foot
and target discipline. V6 remains unaccepted because the body and facing truth
are temporarily out of sync, the staff/hand path visibly teleports at pivot
boundaries, and the final stop does not perform a settle. These are focused
animation-content corrections; the gait library, contact architecture,
evidence pipeline, and canonical framing should be preserved.
