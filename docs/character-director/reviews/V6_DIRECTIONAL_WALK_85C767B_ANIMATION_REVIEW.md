# V6 Directional Walk Independent Animation Review

**Candidate commit:** `85c767ba9c39693536cf6c707a5716f93d08c963`  
**Evidence:** `/tmp/v6-capture-47c7598`  
**Reviewer role:** Independent game animation director and movement reviewer  
**Decision:** **FAIL - DO NOT ACCEPT V6**

## Executive Judgment

The V6 candidate is technically coherent but not visually sufficient as a
directional-walk milestone. The capture, truth trace, browser presentation,
contact accounting, target arrival, and individual pixel-graph silhouettes are
clean. The machine report correctly proves that the controller visits the
requested compass sectors and reaches its target without numerical planted-foot
drift.

That is not what the audience sees. The rendered character does not perform the
90-degree turn or the 180-degree reversal. The front walk snaps to a full right
profile in one frame, and the right profile later swaps to a full left profile
in one frame while the truth trace still labels both sides of the cut
`southeast`. During sustained profile travel, the side-walk cycle alternates a
static profile graph with the exact same graph translated upward by one cell.
It reads as a rigid bob or glide, not a walk.

The limited side-walk therefore does **not** read acceptably for this milestone.
V6 should remain open.

## Evidence Reviewed

- `visual-review-e6a51fe3698b-capture.mp4`: 960x540, 210 frames,
  24 fps, exactly 8.75 seconds.
- `v6-quarter-speed.mp4`: 960x540, 840 frames, 24 fps, exactly
  35.00 seconds.
- `v6-browser-layout.mp4`: 1280x634, 210 frames, 24 fps, exactly
  8.75 seconds.
- `visual-review-e6a51fe3698b-contact-sheet.png`.
- Key source frames under `samples/`, especially frames 41, 46, 50, 90,
  91, 95, 99, 103, 179, 206, and 210.
- `animation_truth_trace.ndjson`.
- `contact_verification.json`.
- `v6-machine-acceptance.json`.
- `v6-browser-layout-metrics.json`.
- The profile-passing source declarations and generated pixel graphs in the
  candidate tree.

The browser recording reproduces the same animation defects at presentation
size. It shows no browser-specific clipping, overlap, decode corruption, or
layout obstruction that would explain them. The defects belong to the motion
content, not the review player.

## Blocking Findings

### 1. The 90-degree turn is a pose pop, not a performed turn

At normal speed, frames 41-45 (1.708-1.875 seconds) report
`presented_facing: southeast`, but continue to render the front-walk silhouette
`walk_front_left_to_right`. Frame 46 (1.917 seconds) changes directly to the
fully established `profile_right` silhouette and `walk_right` clip. There is no
visible three-quarter body orientation, pivot, counter-rotation, anticipation,
or recovery pose.

The frame 45-to-46 cut changes 6,994 cells. The wings collapse from a broad,
nearly symmetrical front presentation into an overlapped profile, the robe
width changes immediately, and the head, beard, hand, and staff relationship
all resolve at once. Every resulting pixel graph is intact, but the cut has no
staged action to make it read as intentional limited animation.

Quarter speed makes the issue conclusive. The source pose before the cut is
held for four output frames, then the complete profile appears at quarter-speed
frame 184 (7.667 seconds). There are no missing in-betweens hidden by normal
playback.

**Required for acceptance:** show an actual pivot through one or more coherent
turn silhouettes, or design a motivated plant/anticipation/cut/recovery phrase
whose pose change reads as a deliberate snap. Updating only the facing label is
not enough.

### 2. The 180-degree reversal visually contradicts the facing trace

Frames 91-94 (3.792-3.917 seconds) remain a full right-facing profile while the
trace advances from `east` to `southeast`. Frame 95 (3.958 seconds) hard-cuts to
the full left-facing `profile_left` graph, yet that frame is also labeled
`southeast`. The state then advances through `south` and `southwest` while the
rendered body is already fully left-facing. The controller's four-sector turn
is measurable in metadata but absent from the performance.

The frame 94-to-95 boundary changes 7,080 cells. The face, beard, robe opening,
staff, staff hand, and visible wing arrangement switch sides together. Most
damagingly, the staff teleports from in front of the character on screen-right
to screen-left without a hand path or a body pivot. The wing silhouette also
swaps occlusion order in the same frame. This is a mirrored asset substitution,
not a reversal.

The exact quarter-speed cut occurs between the repeated right-profile and
left-profile groups at approximately 15.833 seconds. Slowing the material does
not reveal weight transfer or turning action; it only holds each side of the
pop longer.

**Required for acceptance:** the body and the presented-facing state must tell
the same directional story. A 180-degree reversal needs a readable braking
plant, crossover/pivot or front/back bridge, and a re-acceleration beat. The
staff and wings must travel through that change rather than swap sides.

### 3. The profile locomotion cycle has no visible stride

The right side walk uses only `profile_right` and
`walk_profile_right_passing`; the left side walk uses only `profile_left` and
`walk_profile_left_passing`. The candidate source contract defines each passing
graph as an exact `(0, -1)` translation of its static profile source. Cell
counts are identical: 3,068 cells on the right pair and 2,749 cells on the left
pair. All non-root anchors move up one cell together.

This means the legs do not pass, the feet do not exchange lead, the hips do not
shift, the robe does not react, the free arm does not counter-swing, and the
staff has no inertial follow-through. Frames 49-50 (2.042-2.083 seconds) and
98-99 (4.083-4.125 seconds) show the entire character lifted as one rigid unit.
The semantic support contact alternates correctly in the trace, but the visible
shape does not communicate those contacts.

The contact verifier's `0.0` maximum planted drift is valuable, but it does not
remove the perceptual glide. The figure holds a standing profile during support
and advances through a whole-body lift during passing. At normal speed this
reads as a low-amplitude hop/glide; at quarter speed it reads as repeated image
translation.

**Required for acceptance:** provide at least two genuinely distinct side-walk
contact silhouettes and a true passing silhouette per direction, with opposing
leg shapes, a controlled center-of-mass arc, and consistent staff-hand/wing
secondary motion. A translated static profile cannot serve as the passing pose.

### 4. The turn and contact cuts lack weight and continuity

The numerical root path is smooth: the largest world-root step is
`0.0625`, target error is `0.0`, and the machine report finds no planted-anchor
drift. Visually, however, the two major clip boundaries are unsupported hard
cuts. There is no compression before direction change, no torso lead, no head
or prop lag, and no recovery after the new facing appears.

This creates a game-feel problem even apart from missing intermediate angles:
input direction changes, but the character does not appear to generate or
absorb momentum. The consistent timing becomes mechanical because every part
of the silhouette changes as a single rigid package.

**Required for acceptance:** preserve the strong root/contact accounting while
adding visible anticipation, plant, transfer, and recovery beats. Staff and
wings should remain topologically intact but should not be temporally rigid.

## Criterion Decisions

| Criterion | Verdict | Review |
| --- | --- | --- |
| Individual pose silhouette | PASS | Each sampled pixel graph is complete, readable, uncropped, and free of malformed intermediate geometry. |
| 90-degree turn | FAIL | Facing metadata advances, but the rendered body jumps from front to full profile at frames 45-46. |
| 180-degree reversal | FAIL | Frames 94-95 mirror the full character in one frame; the rendered orientation contradicts the `southeast` trace label at the cut. |
| Facing clarity | FAIL | Cardinal end poses are clear, but diagonal facing states have no corresponding body presentation. |
| Cadence | FAIL | Front cadence is readable; profile cadence is a repeated rigid lift without a leg cycle. |
| Weight and momentum | FAIL | No visible braking plant, pivot, compression, counteraction, or re-acceleration phrase. |
| Foot skating | FAIL (perceptual) | Numerical planted drift passes, but the static profile advances via whole-body translation and reads as gliding. |
| Contact cuts | FAIL | Contact-gated timing is technically correct, but the large silhouette substitutions are not motivated by visible action. |
| Staff continuity | FAIL | Staff topology remains intact, but it swaps sides at the reversal without a hand path and moves rigidly with the side cycle. |
| Wing continuity | FAIL | Wings remain complete, but their overlap/order pops at both directional cuts with no rotational bridge or secondary follow-through. |
| Stop settle | MARGINAL | Frames 179-190 reach and hold `profile_left`, then frames 191-210 remain the same visible graph under `idle_left`. The stop is stable and exact, but the settle is essentially a static hold. |
| Limited side-walk suitability | FAIL | A one-cell translation of a standing profile does not yet meet a directional-walk milestone. |
| Browser presentation | PASS | The 210-frame browser recording is clean and unobstructed and faithfully reproduces the same motion defects. |

## Positive Results To Preserve

- The capture bundle is complete and bound to the stated candidate commit.
- Normal, quarter-speed, and browser videos have exact expected durations and
  frame counts.
- All 211 truth records are contiguous; 210 are scenario-owned and the single
  unowned boundary frame is bounded.
- The machine layer reaches the exact target `(-2.4, 3.8)` with zero target
  error and a 31-frame zero-speed suffix.
- Planted drift is `0.0` cells; maximum planted raster-span drift is one cell;
  no contact-verification issues are reported.
- Support contacts alternate 20 times and clip handoffs occur on contact.
- No sampled silhouette clips the canonical 240x135 stage.
- The staff, wings, robe, face, and hat remain structurally complete inside
  every individual graph.

These are strong foundations. They establish that the next pass can focus on
animation content without weakening transport, contact, provenance, or stage
discipline.

## Resubmission Bar

V6 should be resubmitted only when all of the following are visible in both
normal and quarter-speed playback:

1. The 90-degree turn includes a readable pivot or an intentionally staged
   limited-animation turn phrase.
2. The 180-degree reversal no longer mirrors the character in one unsupported
   frame and keeps rendered orientation synchronized with facing state.
3. Side travel has real contact and passing silhouettes with leg opposition,
   not whole-graph vertical translations.
4. The staff hand, staff shaft, wing overlap, head, and torso preserve a
   motivated path across both direction changes.
5. The stop shows at least a modest visible plant/compression and recovery into
   idle while retaining the current exact target and contact metrics.

## Final Verdict

**FAIL.** Candidate `85c767b` proves the directional controller and evidence
pipeline, but it does not yet prove a visually acceptable directional walk.
The turning and reversal performance is represented in state rather than in
the projected character, and the profile locomotion does not contain a visible
stride. V6 must remain unaccepted until those blocking animation defects are
corrected and recaptured.

