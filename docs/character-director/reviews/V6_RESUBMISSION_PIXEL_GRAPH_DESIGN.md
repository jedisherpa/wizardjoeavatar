# V6 Resubmission Pixel-Graph Design

**Candidate reviewed:** `85c767ba9c39693536cf6c707a5716f93d08c963`  
**Role:** Pixel-animation technical director  
**Scope:** Source graphs and offline generation only; no runtime code changes  
**Decision:** V6 needs new authored motion graphs before it can be resubmitted.

## Executive Direction

The V6 controller, contact lock, transport, and evidence pipeline are worth
preserving. The motion content is not. The present profile cycle alternates an
idle graph with an exact one-cell translation, and the turn controller changes
facing labels without corresponding body orientations.

The current 160-pose library does not contain enough grounded side-walk and
turn material to solve those defects by clip timing alone. A credible V6
resubmission requires a minimum production set of:

- eight authored profile-walk graphs: two contacts and two passings in each
  direction;
- four authored grounded three-quarter pivot graphs: two toward east and two
  toward west;
- one authored front crossover/plant graph for the middle of a reversal.

That is **13 new authored source graphs**. Existing poses remain useful as
endpoints, references, and provisional timing tests. They are not substitutes
for the missing silhouettes.

All new sources must be baked by
`tools/generate_reference_avatar_pose_cells.py` into
`wizard_avatar/definitions/reference_avatar_pose_cells.json`. The visualizer
must continue to project colored cells only. Build-time reference images may
be used by the existing generator, but no PNG or SVG becomes a runtime render
asset.

## Current Architecture and Inventory

### Canonical graph contract

`assets/reference/motion_sources/manifest.json` and
`tools/generate_reference_avatar_pose_cells.py` currently define:

- a `72 x 96` local cell canvas;
- canonical root `[36, 95]`;
- required anchors for root, eyes, mouth, feet, hands, staff grip, and staff
  tip;
- root normalization before a graph enters the runtime library;
- complete colored-cell payloads as the runtime representation.

The generated library contains 160 graphs:

| Source class | Count | V6 use |
| --- | ---: | --- |
| Authored image source | 89 | Endpoints and source references |
| Landmark-warp derivative | 35 | Existing gestures and stops; not safe for inventing a body turn |
| Rigid staff derivative | 32 | Useful for an authored turn body's staff variants |
| Crisp blend derivative | 2 | Front-walk passing graphs only |
| Whole-graph translation | 2 | The failed profile passing graphs |

Every relevant authored source is a flattened graph. Its cells have no body
part `region` labels. Staff pixels can be resolved by the existing authored
staff mask, but legs, robe, torso, wings, and hands cannot generally be
separated without spatial and material guesses.

### Grounded directional material actually available

Only the following existing IDs are relevant to a grounded directional turn:

| Pose ID | Facing/role | Decision |
| --- | --- | --- |
| `front_idle` | South idle | Stable front endpoint only |
| `walk_front_left` | Southwest-labelled front contact | Usable front contact/anticipation |
| `walk_front_right` | Southeast-labelled front contact | Usable front contact/anticipation |
| `walk_front_left_to_right` | South front passing | Usable inside the front cycle, not as a body turn |
| `walk_front_right_to_left` | South front passing | Usable inside the front cycle, not as a body turn |
| `walk_front_right_lift` | Dynamic southeast-labelled front lift | Useful timing/reference pose; too large a lean to be the canonical reversal center without review |
| `profile_right` | East idle profile | Idle/settle endpoint only |
| `profile_left` | West idle profile | Idle/settle endpoint only |
| `back_right` | Northeast rear three-quarter | Not a south-to-east bridge |
| `back_left` | Northwest rear three-quarter | Not a south-to-west bridge |
| `back_idle` | North rear | Not a front-facing reversal center |

The flying southeast/southwest graphs are airborne, banked, and differently
staged. The crouch, guard, run-charge, and staff-windup graphs carry action
intent and large silhouette changes. None is an honest generic grounded turn.

### Existing generator operations and their limits

| Operation | Safe V6 use | Unsafe V6 use |
| --- | --- | --- |
| `derived_translation` | Small whole-pose registration corrections after review | A passing pose or stride |
| `derived_blend` / `composite_anchor_transition` | Draft comparison and the already reviewed front passing family | A quarter-turn; it performs a deterministic cell authority wipe rather than rotating anatomy |
| `derived_landmark_warp` | Small changes between already compatible silhouettes | Front-to-profile invention; the flat graph has no wing, robe, or limb topology |
| `derived_landmark_warp` with `topology_splat` | Contact-timed handoff between authored endpoints | Creating missing in-betweens; the implementation intentionally holds one complete endpoint and switches authority |
| `derived_cast_rig` | Repositioning one complete staff around a verified grip on an already authored body pose | Repairing a missing hand, arm, body turn, or wing orientation |
| Reverse sample order | Reusing an authored pivot phrase in the opposite temporal direction | Mirroring east into west |

The generated `profile_right` anchors also demonstrate why anchor labels alone
cannot drive procedural legs: its declared `right_foot` currently lands on a
gray floor/shadow cell, not a verified brown boot component. New gait sources
must be anchored against the visible boot graph, and the audit must inspect the
pixels around every contact anchor.

## 1. Genuine Profile Contact and Passing Silhouettes

### Required source IDs

Author these eight complete source graphs. Do not derive any of them by moving
the full profile graph.

| New pose ID | Facing | Phase | Visible requirement |
| --- | --- | ---: | --- |
| `walk_profile_right_contact_left` | East | 0.00 | Left/support boot behind the root, right/free boot leading; hips at low contact height |
| `walk_profile_right_passing_left_to_right` | East | 0.25 | Left boot planted under the body, right boot visibly off the floor and passing it |
| `walk_profile_right_contact_right` | East | 0.50 | Right/support boot ahead, left/free boot trailing; opposite leg and robe opening from phase 0.00 |
| `walk_profile_right_passing_right_to_left` | East | 0.75 | Right boot planted, left boot visibly off the floor and passing it |
| `walk_profile_left_contact_left` | West | 0.00 | Left/support contact with west-facing body and staff construction |
| `walk_profile_left_passing_left_to_right` | West | 0.25 | Right/free boot clears the floor and passes the planted left boot |
| `walk_profile_left_contact_right` | West | 0.50 | Opposite contact silhouette with right support |
| `walk_profile_left_passing_right_to_left` | West | 0.75 | Left/free boot clears the floor and passes the planted right boot |

`profile_right` and `profile_left` remain idle and stop-settle poses. They must
not be relabelled as both gait contacts. The two failed IDs
`walk_profile_right_passing` and `walk_profile_left_passing` should remain in
the historical library only until compatibility allows their retirement; they
must not appear in the resubmitted V6 side-walk clips.

### Silhouette construction rules

Each four-pose direction cycle must satisfy all of the following before it is
wired to a clip:

1. **Leg opposition:** the two contact graphs have visibly different boot
   order and robe openings. A viewer must identify the lead foot with the
   contact labels hidden.
2. **Passing clearance:** the free boot in each passing graph is at least three
   local cells above the support baseline and crosses the support boot's screen
   x-position.
3. **Center-of-mass arc:** contacts are the low points; passings may raise the
   hat/root-relative body by one cell, but the support boot stays on its
   baseline. Never translate staff, wings, shadow, and both boots together.
4. **Robe reaction:** the leading hem opens in contact, narrows at passing, and
   opens on the opposite side at the next contact. The robe cannot remain a
   rigid rectangle while only a boot moves.
5. **Counteraction:** the free hand and visible wing move one or two cells
   opposite the passing leg. This is restrained secondary motion, not a new
   gesture.
6. **Staff continuity:** the hand remains attached to one complete shaft and
   hook. The tip may lag the body by one or two cells between phases, but it
   cannot change side, length, width, or palette.
7. **Clean graph:** omit sheet background, floor shadow, white fringe, and
   isolated quantization debris. A stage shadow belongs to the projector, not
   to the transparent character graph.

### Anchor contract

For every new gait graph:

- `left_foot` and `right_foot` must point to colored boot cells, not floor
  shadow or empty space;
- the active `planted_anchor` must lie on the lowest connected run of the
  support boot;
- `staff_hand` must lie on skin at the grip and `staff_tip` on the staff hook;
- eye and mouth anchors must remain inside the visible facial graph;
- root remains `[36, 95]` after canonical normalization.

The source anchor offsets can differ by phase. Contact lock compensates for a
different local support-foot coordinate; forcing every foot anchor to the same
local point would erase the stride.

### Why deterministic derivation is not sufficient here

A new offline lower-body transform could theoretically flood-fill boot
components below the robe and move them around foot anchors. The current
graphs do not provide reliable foot components or semantic regions, and one
profile foot anchor already intersects shadow material. Such a transform would
need new region authoring, boot seed validation, staff exclusion, hem repair,
and collision rules. That is more risk than authoring eight small canonical
graphs and still would not create convincing robe and wing counteraction.

Therefore the V6 resubmission should require authored gait graphs. Procedural
leg generation can be a later tooling project, not the basis of this gate.

## 2. Visible 90-Degree Pivot Bridge

### Required source IDs

Author two grounded southeast pivot graphs and two southwest counterparts:

| New pose ID | Presented facing | Rotation intent |
| --- | --- | --- |
| `turn_south_east_33` | Southeast | Front-dominant three-quarter; torso has begun rotating and far wing has started to close |
| `turn_south_east_67` | Southeast | Profile-dominant three-quarter; near shoulder, beard, and staff hand lead into east profile |
| `turn_south_west_33` | Southwest | Front-dominant west turn with coherent west-side staff/wing path |
| `turn_south_west_67` | Southwest | Profile-dominant west turn approaching the left profile |

These are body-orientation graphs, not eye/head overlays. Hat, face, torso,
robe, feet, staff, and both wing masses must agree on the same angle.

### East pivot phrase

The resubmitted south-to-east phrase should use this visible order:

1. `walk_front_right` for a two-frame right-foot plant/anticipation.
2. `turn_south_east_33` for three frames with the right support boot locked.
3. `turn_south_east_67` for three frames; the left foot crosses or closes while
   the right boot remains the pivot.
4. `walk_profile_right_contact_left` or
   `walk_profile_right_contact_right`, selected to preserve the actual support
   phase, for four recovery frames before the side cycle advances.

The `presented_facing` sequence must match the rendered graphs:

- south only while the front-family graph is visible;
- southeast while either southeast pivot graph is visible;
- east only after a right-profile graph is visible.

Reverse sample order provides an east-to-south phrase without generating new
graphs. It does not provide an east-to-west reversal by itself.

### Pivot continuity requirements

- The pivot boot's stage position may drift no more than one raster cell.
- The second boot must visibly release, cross, and recover; metadata-only foot
  changes fail.
- The far wing progressively occludes or narrows from `walk_front_right` to
  `turn_south_east_67`; it cannot disappear at the profile handoff.
- The staff grip travels continuously with the hand. Resolve the actual staff
  geometry with `resolve_authored_staff_anchors` before comparing anchors,
  because legacy mirrored offsets are not sufficient.
- The staff tip should move monotonically through the pivot with no adjacent
  authored jump above three local cells.

`derived_cast_rig` may create reviewed staff-tip variants of these newly
authored body graphs if the grip is already correct. It cannot create the
quarter body or wing orientation.

## 3. Visible 180-Degree Reversal Phrase

### Required center graph

Author one additional graph:

`turn_front_crossover_plant`

It must show a grounded front-facing compression with:

- one clear support foot;
- the free foot crossing beneath the robe;
- staff close to the centerline rather than already resolved to either side;
- wings compressed but still individually readable;
- torso and head arriving at front before continuing toward the opposite
  profile.

`walk_front_right_lift` is the closest existing timing/reference pose because
it has a lifted boot, centered staff, and visible weight shift. It is not the
production answer by default: its large lateral lean, wide stance, robe shape,
and action-sized arm motion are too pronounced for a generic reversal. It may
be used in a provisional proof only if normal- and quarter-speed review finds
that the phrase reads as a deliberate crossover rather than an unrelated pose
insert.

### East-to-west phrase

Use the following complete silhouette sequence:

1. `walk_profile_right_contact_right`: braking contact, three frames.
2. `turn_south_east_67`: reverse playback, two to three frames.
3. `turn_south_east_33`: reverse playback, two to three frames.
4. `turn_front_crossover_plant`: front compression/crossover, three to four
   frames.
5. `turn_south_west_33`: two to three frames.
6. `turn_south_west_67`: two to three frames.
7. `walk_profile_left_contact_left`: west-facing recovery, four frames.
8. Continue at the matching 0.00 or 0.50 phase of the left profile gait.

The phrase must decelerate into steps 1-4 and accelerate out of steps 5-8.
World-root velocity can continue to use the existing director, but the local
graphs must visibly show the brake, transfer, and recovery.

### Staff and wing path

The reversal must not mirror the complete character at one boundary. Require:

- one fixed physical grip throughout the phrase;
- staff tip and shaft moving through center with the hand, not teleporting
  from screen-right to screen-left;
- no shaft identity change, shortening, or hook reversal;
- front crossover as the only frame family where both wings are broadly
  visible;
- progressive wing occlusion on entry and the inverse progression on exit;
- no single-frame swap of near/far wing order.

If staff placement on an authored turn body needs adjustment, generate a small
ordered family with `derived_cast_rig` and explicit target grip/tip offsets.
The body source ID must remain the same for those variants, the grip must stay
within one cell, and adjacent tip movement must stay within three cells.

## Deterministic Reuse and Authorship Boundary

### Approved reuse

- `walk_front_right` and `walk_front_left` as contact anticipation poses.
- `profile_right` and `profile_left` as idle/stop endpoints.
- Reverse playback of the east or west pivot graph sequence.
- `derived_cast_rig` for a complete staff on an already acceptable authored
  turn body.
- Root/contact normalization already provided by the generator and director.

### Preview-only reuse

- `walk_front_right_lift` as a temporary reversal-center test.
- `derived_landmark_warp` between a front and profile endpoint to estimate
  where anchors might travel. Its output is not final art.
- `derived_blend` contact sheets used to compare endpoint occupancy.

### Explicitly rejected shortcuts

- Translating `profile_left` or `profile_right` to claim a passing pose.
- Using the same profile graph for both left and right contacts.
- Relabelling a full profile as southeast/southwest.
- Using `back_left`, `back_right`, or a flying bank as a grounded front pivot.
- Hiding a full-body swap behind a blink, metadata sector, or contact marker.
- Mirroring the whole right-facing graph to make the left family without an
  explicit handedness, staff-side, textural, and wing-occlusion audit.

A future offline `derived_horizontal_mirror` could reduce authored work, but
it does not exist today. The current `profile_left` and `profile_right` sources
also differ materially in cell count and construction, so V6 should not depend
on an unproven mirror transform. If such a transform is added later, it must
reflect every cell and anchor about canonical root x=36, preserve root, then
pass a parity review for grip hand, staff hook, robe opening, facial direction,
and wing order. A failed parity audit means keeping independently authored
left graphs.

## Source and Manifest Specification

For each of the 13 new sources:

1. Author at canonical square-cell resolution or at an integer multiple with
   nearest/box downsampling that preserves square runs.
2. Remove the sheet/cell background and floor shadow before admission.
3. Add one manifest entry before any derivative that references it.
4. Set `facing`, `locomotion`, `phase`, tags, and every anchor offset explicitly.
5. Generate the library twice from a clean tree and require identical graph
   and palette hashes.
6. Retain the build-time source and crop provenance in the generated entry.

Recommended tags:

- gait contacts: `profile`, direction, `walk`, `contact`, support foot,
  `authored_pixel_graph`, `wings`, `staff_held`;
- gait passings: `profile`, direction, `walk`, `passing`, free foot,
  `authored_pixel_graph`, `wings`, `staff_held`;
- turn graphs: `ground_turn`, sector, angle family, support foot,
  `authored_pixel_graph`, `wings`, `staff_held`.

The generated `source` field must identify an authored build-time source or a
specific approved derivative. No resubmitted gait graph may have
`derived_translation:` provenance.

## Pre-Runtime Graph Gates

The art/generator pass should fail closed before animation wiring if any of the
following is false:

1. **Distinct phases:** all four graphs in each profile cycle have different
   cell hashes; neither passing graph is a rigid translation of a contact.
2. **Visible foot alternation:** raster-derived boot centroids exchange lead
   order between contacts, and each passing free boot has at least three cells
   of baseline clearance.
3. **Anchor occupancy:** every foot anchor lands on its named boot component;
   every staff anchor lands on the complete staff/grip component.
4. **Support continuity:** the support boot's lowest raster run changes by no
   more than one cell during its contact interval.
5. **Turn orientation:** south, diagonal, and profile graph families have
   different hashes and visually distinct torso/wing depth order.
6. **Adjacent silhouette continuity:** neighboring turn graphs retain at least
   55 percent occupied-cell intersection-over-union after root alignment.
   Falling below this threshold requires an added bridge graph, not a waiver.
7. **Staff continuity:** adjacent resolved grip movement is at most one cell;
   adjacent tip movement is at most three cells; staff pixel count and shaft
   length stay within the reviewed tolerance.
8. **Wing continuity:** each turn graph contains the expected near/far wing
   masses; no adjacent graph loses a wing component in one frame.
9. **No background:** no admitted cells belong to exterior white, floor gray,
   or source-sheet artifacts.
10. **Stage fit:** every graph and every resolved staff tip remains inside the
    canonical canvas with reviewable clearance.

The 55 percent silhouette threshold is a starting fail-closed bound, not a
substitute for animation review. It should be calibrated against the accepted
V3 cast and front-walk handoffs, then tightened if those accepted transitions
score higher.

## Runtime Resubmission Contract

Once the graph family passes the pre-runtime gate, the V6 runtime evidence must
show:

- four distinct side-walk phases per direction;
- rendered graph orientation matching every `presented_facing` sector;
- the 90-degree phrase visibly traversing both southeast pivot graphs;
- the 180-degree phrase visibly traversing east pivot, front crossover, west
  pivot, and west profile in that order;
- no direct adjacent frame pair from full right profile to full left profile;
- no direct front-family-to-full-profile cut;
- contact lock and target arrival remaining at least as strong as candidate
  `85c767b`;
- staff, hand, wings, robe, face, and feet remaining complete in normal and
  quarter-speed videos.

`tools/analyze_character_director_v6.py` must eventually stop encoding the
failed two-pose profile sets as the expected result. Its replacement machine
gate should enumerate the four authored IDs per direction, derive foot motion
from visible cells, and compare rendered pose orientation with
`presented_facing`. Independent normal- and quarter-speed review remains the
final acceptance authority.

## Recommended Work Order

1. Author and audit the four right-profile gait graphs.
2. Prove one right-facing cycle in a graph-only contact sheet and loop before
   creating left-facing material.
3. Author the four left-profile gait graphs; do not mirror them unless the
   proposed parity gate passes.
4. Author `turn_south_east_33` and `turn_south_east_67`; prove the 90-degree
   east pivot.
5. Author `turn_front_crossover_plant`, `turn_south_west_33`, and
   `turn_south_west_67`; prove the complete reversal as a graph-only phrase.
6. Bake all 13 sources into the deterministic cell library and run the
   pre-runtime gates.
7. Only then reconnect clips, contact markers, and facing states.
8. Capture normal, quarter-speed, contact-sheet, truth-trace, and browser
   evidence from a clean commit for independent technical and animation
   review.

## Final Technical-Director Judgment

V6 is recoverable without changing the projector or abandoning the current
contact architecture. It is not recoverable from the existing 160 graphs by
metadata, timing, whole-graph translation, or global blending alone. The
missing information is artistic: opposing profile strides, grounded diagonal
body orientations, and a staff/wing crossover through front. Those silhouettes
must be authored as complete pixel graphs, then the existing deterministic
pipeline can carry them reliably.
