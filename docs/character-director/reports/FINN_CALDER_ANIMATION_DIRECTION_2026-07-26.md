# Finn Calder Animation Direction

Date: 2026-07-26
Scope: authored poses `037`-`048`
Candidate state: direction approved for authoring; product approval pending

## Evidence And Supplied Vocabulary

This direction is based on direct inspection of Finn's supplied transparent
pixel-graph reconstruction and its 36-pose contact sheet. The supplied
vocabulary already covers:

- profile idle and walking (`001`-`010`);
- profile run, compression, launch, airborne travel, and descent
  (`011`-`018`);
- landing, recovery, a directional balance action, front settle, and one
  compact raised-hand greeting (`019`-`024`);
- front idle, toward-camera gait, and a forward airborne pose (`025`-`030`);
- rear idle, departure gait, and a rear airborne pose (`031`-`036`).

G7 and G8 must add conversational acting that is absent from this locomotion
set. They must not add another walk, run, jump, landing, wave, or generic idle.
The parity target remains one six-pose G7 sequence and one six-pose G8
sequence, bringing Finn to 48 unique poses without duplicating supplied
silhouettes.

## Character Performance Identity

Finn reads as an exact, courteous observer. He is curious without being
naive, alert without being alarmed, and economical without being inert. His
acting starts in visual acquisition: the head finds the person or idea first,
the torso follows by a smaller amount, and a compact hand gesture completes
the thought. He does not pantomime being an alien, marvel broadly at ordinary
objects, or substitute constant head tilts for personality.

Finn's oversized head and large pupil-less black eyes make small changes of
face direction unusually legible. Because the eye design has no moving pupil,
iris, sclera, or brow, authored gaze must be communicated by coherent
head-and-face orientation. Do not add pupils, eye highlights, eyelids,
eyebrows, antennae, ears, or human eye whites to manufacture expression.

Every authored pose must preserve:

- the bright-green rounded voxel head and its established cranial volume;
- two solid black tapered eyes at their supplied size, spacing, and angle;
- the small centered nose and restrained horizontal mouth;
- the orange two-piece suit, lapels, black shirt/tie line, pocket details,
  cuffs, and trouser break;
- green hands, black shoes, crisp voxel construction, and Finn's established
  proportions;
- the supplied front-view camera, scale relationship, lighting direction,
  palette, and pixel density.

The raised hand in supplied pose `024` is Finn's lead conversational hand
(screen-right in the canonical front view). G7 preserves that preference.
G8 may use both hands, but the lead hand initiates and resolves the action.

## Acting Grammar

Each six-pose sequence uses a readable
`preparation -> stroke -> hold -> recovery` grammar:

- **Preparation** acquires the target and creates anticipation without
  spending the main gesture.
- **Stroke** carries the semantic point and creates the largest purposeful
  change in the hand silhouette.
- **Hold** leaves the idea readable long enough for speech or direction.
- **Recovery** releases muscular effort, restores conversational availability,
  and creates a legal handoff. It must not snap directly to a supplied idle.

The head may lead a hand action by one pose, but it may never face a different
subject from the gesture. Shoulder and hip counteraction must remain smaller
than the head cue. Finn's emotional range comes from timing, orientation, and
stillness rather than new facial anatomy.

## G7 Careful Comprehension

Intent:
`acquire -> invite -> distinguish -> test -> acknowledge -> settle`

Purpose: Finn receives unfamiliar information, separates what he understands
from what needs clarification, tests one interpretation, and returns the
floor. The sequence should feel attentive and intelligently curious, never
confused, suspicious, comic, or childlike.

| Pose | Beat | Motion phase | Pose and silhouette direction | Gaze, stance, and hand logic |
| --- | --- | --- | --- | --- |
| `037` | Acquire | Preparation | Front three-quarter attention with the head turning a small amount before the chest. Both arms remain low, with the lead hand slightly released from the thigh to create anticipation. | Face the conversational partner. Keep the chin nearly level, both shoes planted, and the center of mass between the feet. This must read as active receipt rather than a duplicate of `023` or `025`. |
| `038` | Invite | Stroke | The lead forearm arcs forward and opens palm-up at lower-rib height. The elbow stays close enough that the compact body silhouette is preserved. | Maintain partner gaze. The free hand stays low and relaxed. The gesture means "go on" or "show me," not "give me an object." |
| `039` | Distinguish | Hold | Retain the lead palm while the support hand rises nearer the torso at a clearly different height, creating two unequal idea positions. | Let the face check the lead-hand side through a small head turn, then settle between the two ideas. Feet, pelvis, and root remain fixed. Hands must not form a symmetrical shrug or imply holding a box. |
| `040` | Test | Recovery and re-preparation | The lead hand retracts toward center as the support hand rotates outward in one compact, edge-led question. The torso follows only enough to preserve a clean arm-body gap. | Return gaze to the partner before the support-hand question completes. A slight head inclination is allowed; a deep side tilt, chin clutch, or hand-to-face contact is not. |
| `041` | Acknowledge | Stroke and hold | The lead hand opens toward the partner again, lower and calmer than `038`, while the support hand settles near the jacket seam. A small chest release marks understanding. | Hold direct partner orientation. The pose should read "I follow" rather than approval, applause, celebration, surrender, or a wave. |
| `042` | Settle | Recovery | Both hands descend into a quiet asymmetrical rest, with the lead palm retaining a trace of openness. Head and chest return toward front on a restrained nod. | Restore a balanced dual-foot stance and level chin. Preserve enough residual asymmetry to avoid duplicating front idle while enabling a clean transition to idle, G8, or departure. |

### G7 Timing And Transition Intent

- Playback: `8 fps`, `hold_last`.
- Intentional hold markers: `039`, `041`, `042`.
- Safe interruption markers: `037`, `039`, `041`, `042`.
- Protected spans: `038 -> 039` and `040 -> 041`. Do not interrupt while
  invitation becomes comparison or while the tested interpretation becomes
  acknowledgment.
- Entry handoffs: front idle `023` or `025`, front-walk settle `029`, or a
  neutral front three-quarter conversational pose.
- Exit handoffs: front idle `023` or `025`, G8 pose `043`, or profile walk
  only after the recovery hold at `042`.
- On interruption during a protected span, finish at the next safe marker,
  lower both hands, reacquire the new speaker, and never complete an obsolete
  acknowledgment.

## G8 Shared Orientation

Intent:
`establish -> bracket -> trace -> reveal -> verify -> handoff`

Purpose: Finn helps another person understand a spatial relationship or
sequence. The acting uses open air as a shared field, not as an imaginary
screen or device. Finn's precision should feel useful and collaborative,
without becoming a lecture, command, magic effect, or technological scan.

| Pose | Beat | Motion phase | Pose and silhouette direction | Gaze, stance, and hand logic |
| --- | --- | --- | --- | --- |
| `043` | Establish | Preparation | Both forearms release from rest, with the lead hand arriving first at a low shared-work height and the support hand remaining nearer the jacket. | Acquire the near shared field, then the partner. Maintain a tall grounded stance; do not crouch or translate the root. |
| `044` | Bracket | Stroke and hold | Hands separate into an asymmetrical open bracket, the lead hand slightly higher and farther out. Preserve visible air between each hand and the torso. | Face through the center of the bracket. Hands define a relationship, not a physical container; fingers remain open and neither wrist curls into a grip. |
| `045` | Trace | Stroke | The lead hand travels through a shallow diagonal toward one side while the support hand holds the starting area. The torso rotates only a few degrees to sustain the arc. | Head direction follows the lead hand without tipping. The path must read from silhouette alone, with no drawn trail, beam, particles, map, hologram, or pointer finger. |
| `046` | Reveal | Hold | The lead palm rotates outward at the route's destination and becomes the clearest pose in the sequence. The support hand retracts to a quiet open position near center. | Shift face orientation from the destination back toward the partner during the hold. Keep shoulders relaxed so the pose reads as disclosure, not a stop signal or command. |
| `047` | Verify | Recovery and re-preparation | The lead hand remains offered but lowers slightly; the support palm opens in a compact check near the lower chest. | Partner gaze is primary. The two hands must have different jobs and heights; avoid a shrug, two-handed plea, applause preparation, or symmetrical presentation. |
| `048` | Handoff | Recovery | The support hand settles first and the lead hand follows to a low, open finish angled toward the shared field. The head returns level with one restrained confirmation nod. | Re-center weight within the unchanged footprint. Final silhouette must preserve conversational availability and support idle, G7, or profile-departure handoffs after the hold. |

### G8 Timing And Transition Intent

- Playback: `9 fps`, `hold_last`.
- Intentional hold markers: `044`, `046`, `047`, `048`.
- Safe interruption markers: `043`, `044`, `046`, `047`, `048`.
- Protected span: `044 -> 045 -> 046`. Preserve the complete bracket, trace,
  and reveal thought.
- Entry handoffs: front idle `023` or `025`, G7 pose `042`, or a completed
  front-walk settle.
- Exit handoffs: front idle `023` or `025`, G7 pose `037` when a new question
  reopens the exchange, or profile walk only after `048` completes its hold.
- On interruption during the protected span, resolve to `046`, retract through
  `047`, then acquire the new speaker. Do not leave a hand frozen at the route
  destination.

## Gaze And Head-Axis Rules

1. Use face direction, not invented pupils, to establish gaze.
2. Head rotation must precede or accompany the hand target and never oppose
   it.
3. Lateral head inclination is limited to a restrained conversational angle;
   the eye line must stay coherent and the neck must remain structurally
   attached.
4. The large head may not bob, scale, squash, stretch, or drift independently
   of the torso.
5. Hold poses keep a stable face axis. No procedural eye dart, blink drawing,
   or frame-to-frame eye-shape change belongs in these authored graphs.
6. Partner-facing holds must read at full size and thumbnail size without
   relying on facial details that the supplied identity does not possess.

## Root, Support, And Contact Invariants

All twelve poses are fixed-root conversational actions:

- canonical canvas: `1254 x 1254`, straight-alpha RGBA, sRGB;
- canonical ground baseline: `y = 1185`;
- root/support center: `x = 627 +/- 1 px`;
- both black shoes remain planted on the baseline in every pose;
- shoe spacing, sole thickness, front-view scale, and camera perspective remain
  consistent with supplied front idle;
- no shoe may slide, lift, cross, pivot, reverse facing, or imply a step;
- the center of mass remains inside the two-shoe support polygon;
- head and torso inclines are counterbalanced through shoulders and hips
  without translating the root;
- arms remain connected at the shoulders, and hands never float, duplicate,
  penetrate the head, or pass through the jacket.

The preparation and recovery poses may shift apparent weight inside the
footprint, but contact pixels and root position must remain stable. A
transition may not use a planted conversational pose as an unmarked walk
contact.

## Prop And Hand Rules

Finn owns no prop in G7 or G8. Do not invent a scanner, tablet, map, console,
communicator, orb, tool, weapon, badge, beam, hologram, particle effect, or
detached light. Open-air geometry in G8 is purely gestural.

The lead hand is the source-established raised hand from pose `024`. It
initiates both sequences and performs the main semantic stroke. The support
hand may distinguish, bracket, or verify but never mirrors the lead hand
exactly. Green hand color, voxel volume, cuff attachment, and palm orientation
must remain readable. No single-finger point, fused fist, human fingernail, or
extra digit may be introduced.

## Exact Visual Acceptance Gates

An authored Finn candidate fails unless every gate below is demonstrated:

1. **Count and identity:** exactly 12 new pose IDs, `037`-`048`, exist and all
   48 Finn RGBA graphs are unique. No authored pose is a byte duplicate,
   silhouette duplicate, or near-duplicate padding of `001`-`036`.
2. **Immutable source:** supplied records `001`-`036` remain byte-for-byte
   unchanged in the merged candidate.
3. **Canvas and alpha:** every authored graph decodes to straight-alpha RGBA
   on the canonical `1254 x 1254` sRGB canvas, with zero RGB beneath fully
   transparent pixels and no checkerboard, white halo, matte fringe, or
   accidental interior transparency.
4. **Framing:** the complete head, hands, elbows, jacket, trouser hems, and
   shoes remain inside the canonical 69-pixel safety margin. No silhouette is
   cropped, edge-tangent, or resized between adjacent authored poses.
5. **Grounding:** both shoes terminate on baseline `1185`; support center stays
   within `x = 627 +/- 1 px`; contact footprints do not skate; no opaque pixel
   appears below the ground line.
6. **Head identity:** head volume, green palette, eye size/spacing/angle, nose,
   mouth, jaw contour, and neck attachment match the supplied front identity.
   No pupils, eye whites, brows, lids, antennae, ears, or new facial marks
   appear.
7. **Costume identity:** orange jacket and trousers, black center line, lapels,
   pocket marks, cuffs, trouser breaks, and black shoes remain coherent and do
   not flicker, mirror, change hue, or disappear across G7/G8.
8. **Anatomy:** exactly two connected arms and two connected hands are
   present; no hand floats, fuses into the jacket, swaps sides, intersects the
   head, or changes voxel density.
9. **Gesture continuity:** adjacency review proves one continuous lead-hand
   arc through each protected span. Preparation is smaller than stroke, hold
   preserves the semantic silhouette, and recovery visibly releases without
   snapping to idle.
10. **Gaze continuity:** face direction acquires the target before or with the
    corresponding hand, remains stable through holds, and returns to the
    partner or neutral without a head pop, scale pulse, or contradictory axis.
11. **Semantic read:** G7 reads at thumbnail size as careful comprehension;
    G8 reads as shared spatial orientation. G7 may not read as confusion,
    begging, or surrender. G8 may not read as magic, scanning, stop-command,
    invisible-device use, or threat.
12. **Forbidden motion:** no wave, salute, dance, clap, fist pump, shrug,
    accusatory point, run, jump, crouch, landing, airborne action, or locomotor
    silhouette appears in the authored sequences.
13. **Prop truth:** no prop or effect appears, and hand spacing never creates
    a grip that visually requires a missing object.
14. **Transition proof:** full-size adjacency and slowed playback show legal
    entry from supplied front idle, continuous protected spans, stable holds,
    marker-safe interruption recovery, and a clean exit without root pop or
    foot displacement.
15. **Determinism:** two clean builds produce identical authored-pose,
    artifact, index, manifest, motion-contract, and contact-sheet hashes.
16. **Review boundary:** full-size individual frames, thumbnail contact sheet,
    sequence playback, and side-by-side review with approved HD Wizard Joe are
    recorded. Technical passage does not imply product approval or runtime
    admission.

## Rejection Summary

Reject any candidate with identity drift, altered eyes, a floating or
independently bobbing head, broad comic confusion, constant head tilting,
generic alien pantomime, invented technology, magic effects, symmetric
shrugging, threatening gestures, limb defects, costume flicker, crop damage,
scale breathing, root translation, foot skating, unstable support, duplicate
poses, opaque background residue, or an unreviewed transition.

These twelve poses are authored review material only. This direction grants
neither visual approval, product approval, package registration, nor runtime
admission.
