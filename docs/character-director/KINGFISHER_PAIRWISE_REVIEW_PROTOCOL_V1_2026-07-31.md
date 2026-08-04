# Kingfisher Pairwise Review Protocol V1

Date: 2026-07-31

## Decision

Kingfisher's 66 closed/open beak pairs are reviewed one pair at a time at full
projector size. Contact sheets and prior batch dispositions are retained as
history but cannot pass the current gate.

Protocol ID:

`kingfisher-full-size-pairwise-v1`

Machine authority:

`assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json`

## Pair Gate

For each ordinal:

1. Load only its closed and open alpha frames.
2. Compute one shared opaque bound and one presentation transform.
3. Inspect the closed frame at full observer size.
4. Inspect the open frame at the same size and registration.
5. Check one rear hinge, immutable upper beak, substantial connected lower
   mandible, coherent perspective, stable head/eyes/body, and no residual
   closed edge.
6. Save both projected screenshots under the pair's evidence directory.
7. Record exactly one `pass`, `needs_rebuild`, or `not_observable`
   disposition.
8. Recompile the review-only content-addressed artifact.
9. Keep `user_approved` and `runtime_admitted` false.

`pending` is the default and is not a passing state.

## Rebuild Gate

A failed pair is rebuilt independently. Generated art may provide a matched
lower-mandible source, but generated head, eye, clothing, body, and upper-beak
pixels are discarded. The deterministic compositor:

- restores the canonical upper beak;
- permits changes only inside declared mouth masks;
- requires a minimum mandible height;
- requires one connected mandible component;
- requires contact with the declared rear hinge;
- rejects changes outside the masks;
- preserves registered silhouette bounds; and
- writes checksummed source and output receipts.

The rebuilt pair returns to full-size closed/open review. Automated geometry
passing does not substitute for visual review.

## Current Queue

- pair count: 66;
- pairwise passes: 0;
- pending: 63;
- needs rebuild: 1 (pair 62);
- not observable: 2 (pairs 4 and 5);
- user approved: 0;
- runtime admitted: 0.

On 2026-08-01 the user reported visible beak misalignment across the all-pairs
observer. That report invalidated every prior visible internal pass, including
pair 59, without deleting its review record or evidence. Each superseded pass
is retained under `pairwise_full_size_review_history`; its current disposition
is `pending` with `source_disposition` set to
`user_reported_visual_recheck`. Geometry and registration checks may qualify a
frame as a candidate, but they cannot restore a visual pass.

Pair 59 demonstrates the complete workflow. The batch candidate was rejected
for a doubled upper edge. A source-pixel rotation was rejected for insufficient
mandible thickness. A one-pair speaking render was then reduced to a connected
lower-mandible patch, horizontally registered to the canonical upper bill, and
passed at full projector size.

Pair 13 demonstrated why the full-size pairwise gate is required even after a
batch close-up passed. Its speaking frame shifted the bill and mouth cavity
screen-left. The pair was rejected, its pre-repair speaking source was
preserved, and only a connected lower-mouth patch was moved 9 pixels right and
4 pixels down beneath immutable closed-frame upper-bill pixels. The rebuilt
pair passed with zero changes outside its declared articulation region.

Pairs 21 and 22 demonstrated why the remaining corpus must be handled one pair
at a time. Pair 21's batch mate contained a displaced lower mandible and a
detached double edge. It was rebuilt from its exact closed master with an
immutable upper bill and a connected local mandible patch. Pair 22 changed the
eye, face, and upper bill, and its first repair also exposed a black cavity
rectangle only when projected over white. The accepted replacement preserves
the closed-frame eye, face, and upper bill exactly and bounds both the cavity
and lower mandible inside the authored silhouette. Every remaining pair is now
inspected on both transparent close-up and white projector backgrounds.

Pairs 23-26 were processed as four independent closed/open jobs. In every
case, a dedicated one-pair speaking render was retained only as a lower-
mandible donor. The accepted frames keep the canonical eyes, head, upper bill,
throat, body, clothing, gesture, and registration unchanged. Pair 25 required
a second cavity-mask pass after white projection exposed rectangular spill;
pair 26 required a compact frontal V-shaped mask to prevent throat redraw.
The accepted audits report zero change outside each declared mouth region.

Pairs 27-29 continued the same one-pair gate. Pair 27 uses one dedicated
lower-mandible donor beneath an immutable tilted head and upper bill. Pair 28's
first synthetic cavity pass produced a white chevron at projector size and was
rejected; the accepted frame retains the donor-authored mouth under the exact
closed-frame upper bill. Pair 29's legacy candidate looked aligned at normal
size but changed thousands of eye, crown, cheek, and upper-bill pixels. Its
accepted confidential-whisper mate extracts only the measured 80 x 45 lower-
bill change from the body-registered source. All three final audits report
outside-mouth mean difference 0.0, silhouette IoU 1.0, and registration delta
0.

Pair 30 was inspected as an isolated closed/open projector pair and initially
passed with
one stable rear hinge, body registration, upper-bill axis, eyes, and silhouette
bounds. That disposition is now preserved only as superseded history. Pair
31's prior speaking candidate was rejected because its bill axis
and tip did not register cleanly to the closed master. Its replacement was
rendered as one isolated pair on a chroma field, then reduced to a connected
lower-mandible patch. The compositor restored the closed frame's upper bill and
all non-mouth pixels exactly. Its subsequent internal pass is also superseded,
and pair 31 remains pending for a fresh visual review.

Pair 32 is the first candidate produced after the user-wide invalidation. It
was generated as one isolated closed/open job. The generated render is retained
only as a lower-mandible donor; the canonical body and upper bill are restored
exactly. A compositor regression was found during its close-up review: donor
mouth pixels were being painted after the neutral cavity, allowing tongue and
throat colors to leak into the output. The compositor now paints the cavity
after the donor patch, and a regression test enforces that order. The pair-32
candidate reports outside-mouth mean difference 0.0, silhouette IoU 1.0,
registration delta 0, and connected-mandible ratio 1.0. It remains `pending`
until the isolated visual pair is accepted.

Beginning with pair 31, the compiler and final verifier reject a `pass` unless
the pair receipt proves `pair_specific_connected_mandible_patch_v1`, an integer
rear hinge, a substantial connected mandible, explicit mouth/upper-bill masks,
no changes outside those masks, and `immutable_source_pixels` for the upper
bill. This prevents a generous mouth rectangle from accepting a translated or
duplicated beak.

Evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/`

Evidence frames are rendered from the pair receipt's exact source PNGs at the
native canvas size, rather than captured from a browser compositor. This keeps
the visual receipt deterministic and avoids blank or stale canvas captures:

```bash
python3 tools/manage_kingfisher_pairwise_review.py capture \
  --ledger assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json \
  --ordinal 59 \
  --output-dir assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-059
```

## Viewer

`http://127.0.0.1:8667/?hd-pair-review=kingfisher-paired-beaks-review`

The status line includes pair number, pose label, closed/open state, and
pairwise disposition. Direct pair selection uses `&pair=N`.

The reviewer now defaults to a locked side-by-side comparison. Closed and open
frames use the same union registration, source-space crop, presentation scale,
and canvas size. The beak-focus crop is derived from the closed/open pixel
difference and is clipped before presentation, so unrelated body pixels cannot
hide hinge drift. The magnifier control toggles back to full-character context.
Beak focus may enlarge the shared crop, while full-character mode is allowed to
scale below 1:1 so wide poses remain completely visible inside each comparison
panel.

## One-pair rebuild loop

User review on 2026-08-01 found that several beaks previously accepted in a
rapid single-canvas toggle were visibly misaligned. Every earlier full-size
pass was invalidated without deleting its evidence. Rebuilds now proceed one
pair at a time:

1. Treat the closed alpha as the immutable body and upper-bill source.
2. Generate or author one matching open-mouth donor for that exact pose.
3. Composite only a connected lower mandible and mouth cavity.
4. Restore the canonical upper bill after all donor layers.
5. Require zero outside-mouth change, stable registration, silhouette overlap,
   and a connected rear hinge.
6. Inspect closed and open simultaneously in the beak-focus reviewer.
7. Capture native full-size evidence and record one explicit disposition.
8. Do not proceed to the next pair until the current pair is `pass`,
   `needs_rebuild`, or `not_observable`.

## 2026-08-03 Pairwise Reset

The user reported that many beaks in the current all-poses observer still read
as misaligned. All 64 visible internal passes were invalidated again without
deleting their evidence. Pairs 4 and 5 remain `not_observable`; all other
visible pairs returned to `pending` and remain excluded from runtime admission.

The isolated review server now redirects its legacy
`?hd-sequence=kingfisher-all` view into the locked side-by-side pair reviewer.
This prevents the bulk candidate loop from looking like an approved corpus.

Pairs 1 and 2 are the first fresh dispositions under this reset:

- Pair 1 passed a new isolated closed/open review without reconstruction.
- Pair 2 failed because its lower bill was overextended and did not follow the
  three-quarter upper-bill axis.
- Pair 2 was rebuilt as one pair. A generated full-body frame supplied only a
  compact connected lower-mandible and cavity donor. The canonical closed
  frame supplied every other pixel, including the eyes, crown, upper bill,
  chest, hoodie, and body.
- Pair 2's accepted candidate has zero changes outside its declared mouth
  masks, registration-bound delta `0`, silhouette IoU `1.0`, connected-
  mandible ratio `1.0`, and a lower bill that ends behind the upper tip.

Current fail-closed state after this checkpoint: 2 internal pairwise passes,
62 pending, 2 not observable, 0 user approved, and 0 runtime admitted.

Pair 32 (`cause-and-effect`) is the first candidate rebuilt under this stricter
loop. Candidate v8 uses a pose-specific generated cavity instead of a flat
solid fill, while the compositor preserves the canonical body and upper bill.
Its audit reports outside-mouth mean difference `0.0`, silhouette IoU `1.0`,
registration delta `0`, and connected-mandible ratio `1.0`. It has an internal
full-size `pass`; user approval and runtime admission remain false.

Evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-032-v8/`

## 2026-08-01 isolated review checkpoint

Pairs 1-3 and 6-12 passed a fresh locked beak-focus and full-character review.
Pairs 4 and 5 remain intentionally `not_observable`: their rear-facing bodies
hide the beak, their closed/open assets are pixel-identical, and the
choreographer must exclude them from visible lip-sync selection.

Pair 13 (`balance-two-ideas`) initially exposed clipped wing tips in
full-character context even though its beak was aligned. The replacement was
rebuilt from the retained complete closed/open full-render donors. Both donors
were converted to binary-alpha subjects and normalized to the canonical
960 x 540 canvas. The accepted open frame then used the registered closed frame
as its immutable body and upper-bill source and transplanted only the connected
mouth cavity and lower mandible. Its audit reports outside-mouth mean
difference `0.0`, silhouette IoU `1.0`, registration delta `0`, and complete
wing and foot silhouettes.

Pair 13 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-013-v3/`

Pairs 14-21 then passed the same isolated gate. This set covers mirrored
screen presentations, viewer and upward/downward pointing, neutral listening,
a close listening lean, and skeptical listening. Each pair was checked in beak
focus and fitted full-character context before its native evidence was
captured.

Pair 22 (`small-acknowledgment`) passed without reconstruction after its locked
beak-focus and full-character comparisons confirmed a stable upper bill, rear
hinge, head, body, feet, scale, and placement.

Pair 23 (`emphatic-agreement`) demonstrates why automated registration is not
the visual gate. Its first isolated candidate reported outside-mouth mean
difference `0.0`, silhouette IoU `1.0`, registration delta `0`, and one
connected mandible, but the native comparison still showed an overextended
triangular lower bill. That candidate was recorded as `needs_rebuild` and its
evidence was retained. Candidate v3 was then generated for pair 23 alone and
used only as a lower-mandible and cavity donor. The compositor restored the
closed frame's body and upper bill, and the replacement passed both locked
views with the lower bill terminating beneath the upper tip.

Rejected pair 23 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-023-v2/`

Accepted internal pair 23 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-023-v3/`

Pair 24 (`polite-interruption`) was rebuilt one pair at a time after the fresh
full-size review found that its lower mandible curled upward and met the upper
bill near the tip. Two early replacements passed the automated locality,
silhouette, registration, and connected-component checks but failed the locked
visual views: one imported white throat pixels and another produced an
oversized horizontal cavity. Both remain rejected evidence. The accepted v6
candidate uses the dedicated pair render only inside a tightly traced mouth
region, restores the canonical closed frame's upper bill and body, retains the
donor's mouth shading, and terminates the lower bill beneath the upper tip.

Rejected pair 24 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-024-v2/`

Accepted internal pair 24 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-024-v3/`

Pair 25 (`hand-over-the-floor`) failed its fresh review because the open lower
bill was detached from the rear hinge and extended horizontally across the
throat beyond the upper-bill tip. The retained one-pair render was suitable,
but its previous transform registered the body instead of the mouth. Candidate
v4 first aligns that donor around the authored beak hinge, then composites only
the connected cavity and lower bill while restoring the canonical upper bill
and entire body. The accepted locked views show a restrained opening beneath
the upper bill with the presenting wing and registration unchanged.

Rejected pair 25 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-025-v2/`

Accepted internal pair 25 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-025-v3/`

Pair 26 (`warm-welcome`) passed without reconstruction. Its locked close-up
shows the frontal lower bill centered beneath the immutable upper bill in both
states, while the full-character view confirms that the open-wing welcome
silhouette, baseline, and scale do not change.

Accepted internal pair 26 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-026-v2/`

Pair 27 (`intimate-confidence`) also passed without reconstruction. The
restrained lower-mandible opening remains attached at the same right-side
hinge as the closed bill, terminates beneath the upper tip, and does not move
the tilted head, held-in wings, body, feet, scale, or registration.

Accepted internal pair 27 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-027-v2/`

Pair 28 (`strong-declaration`) exposed another false automated pass. Its first
fresh close-up kept the canonical beak shut while painting a disconnected
V-shaped mouth in the white throat. That version was recorded as
`needs_rebuild` before work continued. The accepted v4 replacement was built
for pair 28 alone from a dedicated matching open-mouth donor. A compact mask
transplants only the connected lower mandible and cavity, then restores the
closed frame's central upper bill. The locked close-up now shows one centered
beak articulation, and the full-character comparison preserves the raised
wing, hoodie, body, feet, scale, and registration. Its audit reports outside-
mouth mean difference `0.0`, silhouette IoU `1.0`, and registration delta `0`.

Rejected pair 28 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-028-v2/`

Accepted internal pair 28 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-028-v3/`

Pair 29 (`confidential-whisper`) initially failed because its nominal speaking
mate left the visible beak effectively closed. A first donor transplant made
the lower bill visible but opened it too widely and read as a separate blade
in the locked close-up. The accepted v6 candidate compresses the matching
donor vertically around the fixed rear hinge and uses a narrower pair-specific
mask. The resulting gap is largest at the partially screened tip and closes at
the canonical hinge, which preserves the quiet whisper intention while keeping
the raised wing, head angle, body, scale, and registration fixed. Its audit
reports outside-mouth mean difference `0.0`, silhouette IoU `1.0`, and
registration delta `0`.

Rejected pair 29 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-029-v2/`

Accepted internal pair 29 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-029-v3/`

Pair 30 (`rhetorical-question`) required no art change. Locked beak-focus
review shows the speaking lower mandible opening from the same rear hinge while
the canonical upper bill, eyes, and face remain fixed. Full-character review
also preserves the raised-wing gesture, body silhouette, scale, and
registration. It was therefore recorded as an unchanged internal pass rather
than rebuilt.

Accepted internal pair 30 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-030-v2/`

Pair 31 (`compare-two-options`) failed the fresh isolated gate because the v3
lower mandible was overlong, dropped forward from the face, and did not read as
connected to the closed frame's rear hinge. The accepted v4 candidate rebuilds
this pair alone from its canonical closed frame and dedicated matching source
render. It shortens and vertically compresses the donor lower mandible around
the fixed hinge, then restores immutable canonical upper-bill pixels. Locked
close-up and full-character review show a connected presenting articulation
with the eyes, face, raised wings, body silhouette, scale, and registration
unchanged. Its audit reports outside-mouth mean difference `0.0`, silhouette
IoU `1.0`, and registration delta `0`.

Rejected pair 31 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-031-v2/`

Accepted internal pair 31 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-031-v3/`

Pair 33 (`count-one`) was visually aligned in the isolated reviewer, but the
strict compiler rejected its legacy receipt because it could not prove an
immutable upper bill and pair-specific connected-mandible patch. The accepted
v3 candidate preserves the registered legacy articulation by using that open
frame only as a dedicated donor. It transplants a connected cavity and lower
mandible at the canonical rear hinge, then restores the upper bill from the
closed frame. Locked close-up and full-character review preserve the face,
raised counting wing, body silhouette, scale, and registration. Its audit
reports outside-mouth mean difference `0.0`, silhouette IoU `1.0`, and
registration delta `0`.

Rejected legacy-provenance pair 33 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-033-v2/`

Accepted internal pair 33 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-033-v3/`

Pair 34 (`count-two`) was registered correctly, but its legacy opening was too
broad for the counting gesture and its receipt could not prove the stricter
pair-specific construction. The accepted v2 candidate uses the registered open
frame only as a dedicated donor, vertically compresses its lower mandible
around the fixed central hinge, transplants only the connected cavity and lower
bill, and restores immutable upper-bill pixels from the closed frame. Locked
close-up and full-character review show a restrained speaking beat with the
face, raised wings, body silhouette, scale, and registration unchanged. Its
audit reports outside-mouth mean difference `0.0`, silhouette IoU `1.0`, and
registration delta `0`.

Rejected pair 34 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-034-v2/`

Accepted internal pair 34 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-034-v3/`

Pair 35 (`count-three`) was visually aligned, but its legacy local-composite
receipt changed a broad face rectangle and could not prove the stricter
pair-specific mouth construction. The accepted v2 candidate preserves that
registered open frame only as a dedicated donor. It transplants one connected
V-shaped cavity and lower mandible at the fixed rear hinge, then restores the
closed frame's upper bill and every non-mouth pixel. Locked close-up and
full-character review show a centered opening with stable eyes, head,
raised-wing count-three gesture, body silhouette, scale, and registration. Its
audit reports outside-mouth mean difference `0.0`, silhouette IoU `1.0`, and
registration delta `0`.

Rejected legacy-provenance pair 35 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-035-v2/`

Accepted internal pair 35 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-035-v3/`

Pair 36 (`protective-boundary`) was visually aligned, but its legacy receipt
permitted a broad rectangular face composite. The first isolated patch
candidate traced the inner V instead of the mouth's outer boundary and clipped
away too much cavity; it was retained as rejected work and was not admitted.
The accepted v3 candidate uses the registered open frame only as a dedicated
donor, transplants the complete connected lower-mouth region, and restores the
closed frame's upper bill and every non-mouth pixel. Locked close-up and
full-character review show a restrained defensive speaking beat with stable
eyes, head, raised boundary wing, silhouette, scale, and registration. Its
audit reports outside-mouth mean difference `0.0`, silhouette IoU `1.0`, and
registration delta `0`.

Rejected legacy-provenance pair 36 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-036-v2/`

Accepted internal pair 36 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-036-v3/`

Pair 37 (`gentle-reassurance`) exposed a failure mode specific to diagonal
three-quarter beaks. Its registered legacy mate extended the forward tip and
could not prove a pair-specific lower-mandible transplant. Seven local patch
attempts were rejected because they collapsed into a flat stripe, a triangular
wedge, or a nearly closed line. Broader generated-donor masks were also
rejected when locked close-up review showed stretched white throat feathers
inside the moving mandible.

The accepted v15 candidate was rebuilt from the exact canonical closed frame
and one dedicated pair render. The render is evidence and a donor only. Its
lower bill is vertically articulated around the fixed rear hinge, clipped to a
contour that follows the actual mandible edge, and composited beneath immutable
canonical upper-bill pixels. A new explicit `generated_overlay` cavity mode
then restores only the bounded authored red/dark oral texture after the upper
bill is locked. Locked beak-focus and full-character review show a restrained
opening on the authored diagonal axis with no eye, crown, cheek, throat,
hoodie, wing, scale, or registration drift. The audit reports outside-mouth
mean difference `0.0`, silhouette IoU `1.0`, and registration delta `0`.

Rejected initial pair 37 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-037-v2/`

Accepted internal pair 37 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-037-v3/`

Pair 38 (`invitation-to-follow`) demonstrated why a passing coarse audit is
not sufficient. The prior batch candidate changed only pixels inside its
declared articulation region, but that region covered most of the face and
therefore allowed generated upper-bill and facial-edge pixels to drift. The
native close-up was rejected even though its older audit reported outside-mouth
mean difference `0.0`.

The accepted v2 pairwise candidate uses the exact canonical closed frame as
the body and upper-bill authority. Its preserved matched speaking frame is only
a donor for one connected lower mandible and a tightly bounded oral cavity.
The replacement mask is `75 x 45` pixels, the lower mandible remains connected
to one rear hinge, and the upper-bill polygon is restored from canonical source
pixels after compositing. Locked beak-focus and full-character projector review
show aligned right-facing perspective, a restrained invitation-level opening,
and no crown, eye, cheek, throat, hoodie, wing, foot, scale, or registration
drift. The tighter audit reports `1,413` changed rendered pixels, outside-mouth
mean difference `0.0`, silhouette IoU `0.999873`, and registration delta `0`.

Rejected initial pair 38 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-038-v2/`

Accepted internal pair 38 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-038-v3/`

Pair 39 (`describe-a-vast-scene`) initially appeared coherent, but its batch
receipt still delegated a `146 x 116` face region to generated pixels. That
could not prove that the long upper bill remained canonical, so the batch
candidate was rejected as an admitted source even though it had no obvious
full-body registration error.

The accepted v6 pairwise candidate restores the complete head and upper bill
from the exact closed frame. Its preserved matched speaking frame contributes
only one connected lower mandible and bounded oral cavity. Two early masks were
rejected because they restored through the mouth line and left a nearly closed
bill with stray tip pixels. A third clean contour was readable only at close-up.
The final contour moves the same lower-bill donor four pixels downward around
its fixed rear hinge, providing a readable storytelling opening while retaining
canonical upper-bill geometry. Locked close-up and full-character projector
review show aligned long-beak perspective, no head or eye drift, stable wings
and body, and exact registration. The audit reports `2,158` changed rendered
pixels, outside-mouth mean difference `0.0`, silhouette IoU `0.997842`, and
registration delta `0`.

Rejected initial pair 39 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-039-v2/`

Accepted internal pair 39 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-039-v3/`

Pair 40 (`describe-a-tiny-detail`) also passed its older bounded-change audit,
but the batch receipt delegated a `141 x 96` face region to generated pixels.
Native close-up comparison showed that the replacement covered the eye edge
and upper bill as well as the speaking mouth. The batch result was therefore
rejected even though its body registration remained stable.

The accepted v3 pairwise candidate starts from the exact canonical closed
frame and uses the preserved speaking frame only as a lower-mandible donor.
The compositor moves that donor three pixels downward around one rear hinge,
restores the complete canonical upper bill, and overlays only a narrow oral
cavity. Locked close-up and full-character projector review show a restrained
detail-telling opening with stable eye, head, raised wing, body, and feet. The
audit reports `2,698` changed rendered pixels, outside-mouth mean difference
`0.0`, silhouette IoU `1.0`, connected-mandible ratio `1.0`, and registration
delta `0`.

Rejected initial pair 40 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-040-v2/`

Accepted internal pair 40 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-040-v3/`

Pair 41 (`centered-calm`) presented a convincing frontal open beak at thumbnail
scale, but its batch receipt delegated a `121 x 97` face region spanning both
eyes, both cheek edges, and the upper bill. That broad generated composite was
rejected because stable registration alone could not prove facial identity.

The accepted v3 pairwise candidate uses the exact canonical closed frame for
the crest, eyes, cheeks, body, and frontal upper bill. The preserved speaking
frame contributes one connected V-shaped lower mandible and a bounded
donor-textured cavity. An earlier solid-cavity experiment was rejected because
it read as a flat black mark over the white chest. Locked close-up and
full-character projector review show a readable centered gape, preserved
bilateral facial symmetry, stable hoodie and feet, and exact registration. The
audit reports `2,284` changed rendered pixels, outside-mouth mean difference
`0.0`, silhouette IoU `1.0`, connected-mandible ratio `1.0`, and registration
delta `0`.

Rejected initial pair 41 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-041-v2/`

Accepted internal pair 41 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-041-v3/`

Pair 42 (`joy`) exposed the same structural weakness more clearly. Its batch
candidate looked expressive, but the receipt delegated a `121 x 106` region
covering the upper bill and central face. That result was rejected because a
stable full-body registration box did not prove that the eyes, cheeks, and
upper bill remained the same authored pixels.

The accepted pairwise candidate was rendered and rebuilt as one isolated
closed/open pair. The exact repaired closed frame remains authoritative for the
crest, eyes, cheeks, upper bill, raised wings, hoodie, feet, canvas, and
registration. A dedicated open-beak render contributes only one connected
lower mandible and the bounded dark/red oral cavity. Two deterministic donor
experiments were rejected because they either produced a nearly closed line or
copied white throat pixels into the moving bill. The accepted contour stays
under the immutable canonical upper bill and reads as a joyful speaking shape
at both native close-up and full-character scale. Its audit reports `1,600`
changed rendered pixels, outside-mouth mean difference `0.0`, silhouette IoU
`1.0`, connected-mandible ratio `1.0`, and registration delta `0`.

Rejected initial pair 42 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-042-v2/`

Accepted internal pair 42 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-042-v3/`

Pair 43 (`full-laughter`) already contained a visually useful open long beak,
but its batch receipt delegated a `214 x 113` region covering the upper bill,
closed-eye face, and surrounding head. The result was rejected as an admitted
source because the broad composite could not prove that the laughter
expression and long upper-bill registration remained canonical.

The accepted v2 pairwise candidate starts from the exact canonical closed
full-laughter frame. Its preserved matched open frame contributes only one
connected lower mandible and bounded oral cavity; the complete long upper bill,
closed eyes, crest, cheeks, throat, wings, hoodie, feet, canvas, and registration
come from the closed frame. Locked beak-focus playback shows the lower bill
rotating from a single rear hinge without a head jump, and full-character review
shows an unchanged raised-wing silhouette. The tighter audit reports `2,542`
changed rendered pixels, outside-mouth mean difference `0.0`, silhouette IoU
`0.999505`, connected-mandible ratio `1.0`, and registration delta `0`.

Rejected initial pair 43 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-043-v2/`

Accepted internal pair 43 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-043-v3/`

Pair 44 (`excitement`) had a readable batch-generated gape, but its receipt
delegated a `117 x 104` region and replaced the long downward upper bill with a
shorter generated shape. The batch frame was rejected because the apparent
mouth motion came with a changed bill identity even though the body-level
registration checks passed.

The accepted pairwise candidate keeps the exact canonical closed frame for the
crest, eyes, cheeks, long frontal upper bill, raised wings, hoodie, body, feet,
canvas, and registration. Its preserved matched speaking frame contributes
only one connected lower mandible and donor-textured cavity beneath that
immutable bill. A stronger solid-cavity experiment passed the numeric gate but
was rejected visually because it read as a flat geometric mark. Locked
beak-focus playback and full-character comparison show a centered opening with
no face or body jump. The pose-specific audit region contains every changed
pixel and reports `1,050` changed rendered pixels, outside-mouth mean
difference `0.0`, silhouette IoU `1.0`, connected-mandible ratio `1.0`, and
registration delta `0`.

Rejected initial pair 44 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-044-v2/`

Accepted internal pair 44 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-044-v3/`

Pair 45 (`curiosity`) also passed the legacy batch audit while changing a
`131 x 115` face region. Full-size comparison showed that the generated open
frame shortened and rotated the tilted upper bill along with the lower-beak
motion, so that batch composite was rejected.

The accepted pair was rebuilt independently. The canonical closed frame owns
the complete tilted upper bill, eyes, crest, cheeks, throat, hoodie, body,
wings, feet, canvas, and registration. A pair-specific image-edit render was
used only as a donor for a small connected lower V and oral cavity. Broad donor
masks were rejected because they copied an eye or throat feathers; a solid
cavity was rejected because it looked pasted on; and a nearly closed donor
mask was rejected because the motion did not read. The accepted mask is
bounded to the lower bill, restores canonical source pixels around it, and
uses donor texture only where the cavity must remain visible. Locked close-up,
full-character, and transition review show a centered hinge with no head or
body jump. Its audit reports `1,066` changed rendered pixels, outside-mouth
mean difference `0.0`, silhouette IoU `1.0`, connected-mandible ratio `1.0`,
and registration delta `0`.

Rejected initial pair 45 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-045-v2/`

Accepted internal pair 45 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-045-v3/`

Pair 46 (`confident hero`) exposed another false positive from the legacy
batch audit. The prior speaking frame replaced the compact closed bill with a
large black diamond. Although the broad articulation-region metrics passed,
the result did not preserve the approved bill construction and was rejected at
native-size pair review.

The accepted replacement was produced as one isolated closed/open pair. The
exact closed frame remains authoritative for the eyes, crest, face, complete
upper bill, throat, hoodie, wings, body, feet, canvas, and registration. A
pair-specific image edit contributes only the connected lower mandible and its
bounded mouth interior. The compositor restores canonical source pixels above
the mouth opening and excludes every regenerated body pixel. Locked side-by-
side playback shows a centered lower bill with no head or body jump. Its audit
reports `2,532` changed rendered pixels, outside-mouth mean difference `0.0`,
silhouette IoU `1.0`, connected-mandible ratio `1.0`, and registration delta
`0`.

Rejected initial pair 46 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-046-v2/`

Accepted internal pair 46 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-046-v3/`

Pair 47 (`compassion`) used a legacy `129 x 131` articulation region. Native
comparison showed that the batch composite copied the regenerated eye, crest,
face, and most of the upper bill along with the speaking mouth. That result was
rejected even though its registration and silhouette metrics passed.

The replacement starts from the exact canonical closed compassion frame. The
matched raw render supplies only one connected, angled lower mandible and the
bounded cavity beside the downward-pointing upper bill. A pose-specific
non-rectangular mask follows the bill axis, while a second source-restoration
mask returns every upper-bill pixel to the canonical frame. Locked close-up and
playback preserve the lowered head, eye, crest, throat, wing gesture, hoodie,
body, feet, canvas, and registration. The accepted audit reports `2,537`
changed rendered pixels, outside-mouth mean difference `0.0`, silhouette IoU
`1.0`, connected-mandible ratio `1.0`, and registration delta `0`.

Rejected initial pair 47 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-047-v2/`

Accepted internal pair 47 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-047-v3/`

Pair 48 (`surprise`) demonstrated why silhouette and registration checks alone
cannot approve a speaking mate. The legacy batch frame scored silhouette IoU
`1.0`, yet visibly redirected both eyes and replaced the central face and bill.
That frame was rejected at the native-size pair gate.

The accepted replacement uses the exact closed surprise frame for the wide-
eyed gaze, crest, face, upper-bill root, throat, hoodie, spread-wing body,
feet, canvas, and registration. A tightly bounded donor mask supplies the
centered open lower bill and dark cavity required by the surprise expression.
Locked beak-focus and full-character review show no eye, head, or body jump.
The accepted audit reports `4,596` changed rendered pixels, outside-mouth mean
difference `0.0`, silhouette IoU `1.0`, connected-mandible ratio `1.0`, and
registration delta `0`.

Rejected initial pair 48 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-048-v2/`

Accepted internal pair 48 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-048-v3/`

Pair 49 (`confusion`) repeated the same failure mode in a subtler three-quarter
pose. The legacy `149 x 116` articulation composite replaced both eyes, the
forehead and crest texture, the face, and the upper bill along with the mouth.
Its silhouette and registration checks were nearly perfect, but the result was
not the same confused performance and was rejected at the native-size gate.

The accepted replacement starts from the exact closed confusion frame. The
matched raw render contributes only one connected lower mandible and the narrow
dark cavity beneath the immutable upper bill. Locked beak-focus, full-character,
and playback review preserve the puzzled gaze, crest, head angle, throat,
hoodie, raised-wing gesture, body, feet, canvas, and registration. The accepted
audit reports `3,022` changed rendered pixels, outside-mouth mean difference
`0.0`, silhouette IoU `0.99991`, connected-mandible ratio `1.0`, and
registration delta `0`.

Rejected initial pair 49 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-049-v2/`

Accepted internal pair 49 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-049-v3/`

Pair 50 (`skepticism`) exposed another batch-composite failure that the legacy
numeric gate had accepted. The open frame replaced the narrowed eyes, changed
the crest silhouette and texture, and regenerated most of the upper bill and
face inside a broad `123 x 99` articulation region. That result was rejected
at native size.

The accepted replacement starts from the exact closed skepticism frame. The
matched raw render contributes only one tightly masked diagonal lower mandible
and its bounded cavity. The source-restoration mask follows the closed upper
bill down to the mouth seam so the donor cannot alter the eye line, crest,
face, or bill root. Locked beak-focus, full-character, and playback review
preserve the skeptical gaze, crest silhouette, head angle, throat, hoodie,
crossed-wing posture, body, feet, canvas, and registration. The accepted audit
reports `1,451` changed rendered pixels, outside-mouth mean difference `0.0`,
silhouette IoU `0.999969`, connected-mandible ratio `0.995865`, and
registration delta `0`.

Rejected initial pair 50 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-050-v2/`

Accepted internal pair 50 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-050-v3/`

Pair 51 (`concern`) confirmed why the review must proceed one pair at a time.
The legacy open frame passed its numeric audit while replacing the eyes,
forehead and crest texture, face, upper bill, and cheek inside a broad
`126 x 118` composite. Its long regenerated beak no longer read as the exact
closed performance opening at one stable hinge, so the frame was rejected at
native size.

The accepted replacement starts from the exact closed concern frame. A
pair-specific anisotropic alignment shortens the donor opening while retaining
the canonical hinge; tightly bounded masks admit one connected lower mandible
and a narrow matched oral line, then restore every upper-bill source pixel.
Locked beak-focus, full-character, and playback review preserve the concerned
gaze, crest, face, upper bill, throat, hoodie, folded-wing gesture, body, feet,
canvas, and registration. The accepted audit reports `2,792` changed rendered
pixels, outside-mouth mean difference `0.0`, silhouette IoU `1.0`,
connected-mandible ratio `1.0`, and registration delta `0`.

Rejected initial pair 51 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-051-v2/`

Accepted internal pair 51 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-051-v3/`

Pair 52 (`sadness`) repeated the batch-composite defect on a steeper,
downward-facing bill. The legacy `93 x 127` articulation region regenerated
the forehead feathers, downcast eye, face, upper bill, cheek, and mouth at
once. Its extra-long open bill passed the old silhouette check but no longer
preserved the exact sad performance, so it was rejected at native size.

The accepted replacement again begins with the exact closed frame. A
pair-specific vertical compression retains the authored bill tip and hinge
while reducing the donor opening; a connected lower-mandible mask and narrow
dark cavity are the only admitted changes. Locked beak-focus, full-character,
and playback review preserve the downcast eye line, crest, face, upper bill,
throat, hoodie, hanging wings, body, feet, canvas, and registration. The
accepted audit reports `1,134` changed rendered pixels, outside-mouth mean
difference `0.0`, silhouette IoU `1.0`, connected-mandible ratio `1.0`, and
registration delta `0`.

Rejected initial pair 52 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-052-v2/`

Accepted internal pair 52 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-052-v3/`

Pair 53 (`embarrassment`) demonstrated a second failure mode in the batch
workflow. The legacy `99 x 94` composite replaced the eye, forehead and crest
texture, face, upper bill, cheek, and throat while reporting a numeric pass.
Initial body-locked replacements also failed visual review: scale-only
alignment produced a nearly closed mouth, anisotropic stretching attached an
angular dark wedge to the hoodie, and an untapered cavity left a square cap at
the bill tip. Those candidates remain recorded as rejected evidence and were
never admitted.

The accepted replacement was rendered and reviewed as one isolated pair. The
exact closed frame remains the canonical body and upper bill. The pair-specific
render contributes only a tapered lower mandible and oral detail; a recorded
eight-degree hinge rotation aligns that donor with the authored mouth corner.
The compositor now supports hinge rotation plus a solid cavity underlay with a
generated-detail overlay, allowing the narrow mouth interior to remain opaque
without flattening its red and charcoal texture. Locked beak-focus,
full-character, and playback review preserve the embarrassed gaze, crest,
face, upper bill, white throat feathers, hoodie, folded-wing posture, body,
feet, canvas, and registration. The accepted audit reports `974` changed
rendered pixels, outside-mouth mean difference `0.0`, silhouette IoU `0.999`,
connected-mandible ratio `0.996951`, and registration delta `0`.

Rejected legacy and intermediate pair 53 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-053-v2/`

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-053-v3/`

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-053-v4/`

Accepted internal pair 53 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-053-v5/`

Pair 54 (`shame`) exposed the same false-positive pattern at a near-vertical
bill angle. The legacy candidate changed `11,644` rendered pixels across a
`96 x 148` region, replacing the eye, crest, face, cheek, upper bill, and
adjacent folded-wing texture while still passing the broad rectangle audit.
Its nominal speaking frame also remained visually closed. That donor was
rejected and preserved before any replacement was attempted.

The accepted replacement was rendered as one isolated closed/open pair. The
first pair-specific render was also rejected because its opening disappeared
at the canonical `960 x 540` scale. A second render supplied a clearly attached
lower bill and narrow red oral surface at the authored downward hinge. The
compositor restores the exact closed frame everywhere except the recorded
lower-mandible and cavity masks, then restores the closed upper bill before
applying the mouth interior. Locked beak-focus, full-character, and playback
review preserve the bowed eye line, crest, face, upper bill, hoodie, folded
wings, body, feet, canvas, and registration. The accepted audit reports
`2,138` changed rendered pixels, outside-mouth mean difference `0.0`,
silhouette IoU `1.0`, connected-mandible ratio `1.0`, and registration delta
`0`.

Rejected legacy pair 54 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-054-v2/`

Accepted internal pair 54 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-054-v3/`

Pair 55 (`fear`) began with a visually useful open-mouth render, but its legacy
batch composite replaced `13,626` pixels across a `137 x 109` face-and-bill
rectangle. The first isolated donor also carried a bright lower-bill rim that
became distracting in the native-size nearest-neighbor review. A new one-pair
render repeated that bright-rim defect and was preserved as rejected evidence
rather than admitted.

The accepted replacement reuses the best matched fear mandible only after
neutral matte highlights are removed from its keyed donor. The exact closed
frame supplies the body, eyes, crest, cheek, throat, hoodie, wings, and upper
bill. A connected lower-mandible mask converges at the authored screen-right
hinge, while a dark cavity underlay and donor oral detail preserve the fearful
speaking read. The transparent cutouts already present below the canonical
closed bill remain identical in both states. Locked beak-focus,
full-character, and playback review report no body or registration movement.
The accepted audit reports `3,015` changed rendered pixels, outside-mouth mean
difference `0.0`, silhouette IoU `0.994902`, connected-mandible ratio `1.0`,
and registration delta `0`.

Rejected legacy pair 55 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-055-v2/`

Accepted internal pair 55 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-055-v3/`

Pair 56 (`anxiety`) confirmed the user's report that the legacy batch workflow
could leave a visibly misaligned beak while still reporting a numeric pass.
The legacy candidate changed `12,134` rendered pixels across a `119 x 111`
face-and-bill rectangle. It replaced the face and upper bill with an oversized
open render whose lower bill no longer read as a natural hinge articulation.
That candidate was rejected and retained before replacement.

The accepted replacement was generated and composed as one isolated pair. The
exact closed anxiety frame remains the body and upper-bill authority. A matched
pair-specific render contributes only a connected lower mandible and narrow
dark oral cavity, aligned at the authored screen-left hinge. Native beak-focus,
full-character, and closed/open playback review preserve the anxious gaze,
crest, face, upper bill, throat, hoodie, folded-wing pose, body, feet, canvas,
and registration. The accepted audit reports `1,352` changed rendered pixels,
outside-mouth mean difference `0.0`, silhouette IoU `1.0`, connected-mandible
ratio `1.0`, and registration delta `0`.

Rejected legacy pair 56 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-056-v2/`

Accepted internal pair 56 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-056-v3/`

Pair 57 (`anger`) exposed the same batch-review failure at a larger scale. The
legacy candidate changed `13,440` rendered pixels across a `113 x 126`
face-and-bill rectangle, replacing the authored angry face and upper bill even
though its automated audit reported a pass. Attempts to salvage that donor
also produced a diagonal throat seam, so both the batch candidate and donor
salvage were rejected and retained as evidence.

The accepted replacement was rebuilt as one isolated closed/open pair from a
fresh pair-specific render. The exact closed anger frame remains authoritative
for the eyes, crest, cheeks, face, body, and upper bill. Only a centered,
connected V-shaped lower mandible and narrow dark oral cavity are composited
for the speaking state. Native beak-focus, full-character, and closed/open
playback review preserve the angry expression and registration without the old
face shift or throat seam. The accepted audit reports `2,696` changed rendered
pixels, outside-mouth mean difference `0.0`, silhouette IoU `1.0`,
connected-mandible ratio `1.0`, and registration delta `0`.

Rejected legacy pair 57 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-057-v2/`

Accepted internal pair 57 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-057-v3/`

Pair 58 (`frustration`) showed why even visually plausible batch output must be
reduced to one pair before admission. The legacy candidate changed `13,859`
rendered pixels across a `117 x 126` face-and-bill rectangle. Close inspection
showed that the open state replaced the brow, eye, crest edge, cheek, throat,
and both beak halves rather than articulating one lower mandible. That candidate
was rejected and retained before replacement.

The accepted replacement uses a fresh render made only for the frustration
pair as lower-mandible donor material. The exact closed frame remains
authoritative for the bowed crest, frustrated eye, forehead wing, orange cheek,
throat, hoodie, full body, and upper beak. A tight connected mask excludes the
throat feathers and admits only the lower mandible plus a narrow oral cavity at
the authored screen-right hinge. Native beak-focus, full-character, and
closed/open playback review show no head jump, duplicate edge, or registration
movement. The accepted audit reports `1,343` changed rendered pixels,
outside-mouth mean difference `0.0`, silhouette IoU `1.0`,
connected-mandible ratio `1.0`, and registration delta `0`.

Rejected legacy pair 58 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-058-v2/`

Accepted internal pair 58 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-058-v3/`

Pair 59 (`determination`) was already marked `needs_rebuild` by the earlier
full-size reviewer, but several subsequent pair attempts still left detached
needle lines or an opaque black rectangle extending beyond the screen-right
beak tip. The last legacy candidate changed `2,544` rendered pixels and passed
its bounded-region audit despite the obvious matte artifact. All of those
attempts remain preserved; the live candidate was rejected before replacement.

The accepted replacement starts from a fresh render made for this right-facing
pair only. The exact closed determination frame remains authoritative for the
eyes, crest, cheeks, throat, stance, hoodie, body, and upper beak. Only the
screen-left-hinged lower mandible and narrow cavity are admitted. Native
beak-focus, full-character, and closed/open playback review show no rectangle,
detached line, head shift, or registration movement. The accepted audit reports
`1,264` changed rendered pixels, outside-mouth mean difference `0.0`,
silhouette IoU `1.0`, connected-mandible ratio `0.998663`, and registration
delta `0`.

Rejected legacy pair 59 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-059-v2/`

Accepted internal pair 59 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-059-v3/`

Pair 60 (`fatigue`) demonstrates why the pairwise gate replaced the earlier
batch disposition. The legacy speaking candidate passed its bounded-region
audit while visibly pasting a second oversized upper beak across the face. The
candidate changed `2,444` rendered pixels, but the close-up made the anatomical
failure unambiguous, so that result remains only as rejected evidence.

The replacement was rendered from the exact fatigued closed frame as a single
pair-specific job. The generated frame is retained only as a lower-mandible
donor. The compositor restores the closed frame's upper beak, eyes, crest,
cheek, throat, hoodie, body, stance, and registration exactly, then admits a
connected lower mandible and narrow oral cavity at the screen-right hinge.
Native beak-focus, full-character, and closed/open playback review show one
hinge, no duplicated upper beak, and no head or body movement. The accepted
audit reports `2,092` changed rendered pixels, outside-mouth mean difference
`0.0`, silhouette IoU `1.0`, connected-mandible ratio `1.0`, and registration
delta `0`.

Rejected legacy pair 60 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-060-v2/`

Accepted internal pair 60 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-060-v3/`

Pair 61 (`deep contemplation`) showed a different form of batch failure. The
legacy speaking candidate placed a long rectangular dark strip diagonally
across the face from the bill toward the eye. Its bounded-region audit could
not establish that the strip was a plausible lower mandible, so the candidate
was preserved as rejected evidence before replacement.

The accepted replacement was handled as one isolated pair. A fresh matched
render made specifically for the contemplative hand-on-chin pose supplies
only lower-mandible and oral-cavity pixels. The exact closed frame remains
authoritative for the crest, eye, cheek, throat, hand gesture, hoodie, body,
stance, and upper beak. Native beak-focus and full-character review show one
connected screen-right hinge and no facial strip, duplicate upper edge, head
jump, or body movement. The accepted audit reports `1,700` changed rendered
pixels, outside-mouth mean difference `0.0`, silhouette IoU `1.0`,
connected-mandible ratio `1.0`, and registration delta `0`.

Rejected legacy pair 61 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-061-v2/`

Accepted internal pair 61 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-061-v3/`

Pair 62 (`sudden idea`) was the last explicit rebuild blocker. Its historical
geometry experiments left stacked bill edges and an ambiguous hinge. A fresh
matched render was therefore produced for this raised-wing pose alone. The
closed master remains authoritative everywhere except the connected lower
mandible and bounded cavity. Full-size review shows one screen-left hinge and
no duplicate bill edge. The accepted audit reports `1,086` changed rendered
pixels, outside-mouth mean difference `0.0`, silhouette IoU `1.0`,
connected-mandible ratio `1.0`, and registration delta `0`.

Rejected pair 62 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-062-v2/`

Accepted internal pair 62 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-062-v3/`

## Verification

Focused mandible-compositor tests: 9 passed. The added regressions prove solid
cavity underlays and generated oral detail can be layered after canonical
upper-bill restoration without changing legacy `solid`, `generated`, or
`generated_overlay` behavior.

Pair 63 (`read a panel`) confirmed the user's concern about the old batch
process. Its legacy speaking frame extended the bill far past the closed tip
and split the mouth into multiple competing edges. The first deterministic
rotation replacement was also rejected after playback because its cavity read
as a heavy black bar. Both failures remain preserved as evidence.

The accepted replacement was rebuilt as one isolated pair. A fresh matched
render supplies only a tightly masked lower mandible and its oral detail. The
closed frame remains authoritative for the crest, eye, face, cheek, throat,
hoodie, body, stance, registration, and upper beak. The admitted mask excludes
all donor throat feathers; the lower tip remains behind the immutable upper
tip. Native beak-focus, white-background full-character, and alternating
playback review show one fixed hinge and no duplicate edge or head movement.
The accepted audit reports `1,180` changed rendered pixels, outside-mouth mean
difference `0.0`, silhouette IoU `0.997219`, connected-mandible ratio `1.0`,
and registration delta `0`.

Rejected legacy pair 63 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-063-v2/`

Rejected heavy-cavity pair 63 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-063-v3/`

Accepted internal pair 63 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-063-v4/`

Pair 64 (`study a diagram`) showed why the prior broad rectangle audit was
insufficient: its generated lower bill was a long, steep blade whose hinge
began behind the authored mouth corner. That candidate remained numerically
bounded and registered, but failed full-size visual review and is preserved as
rejected evidence.

The accepted replacement was rebuilt as one isolated closed/open pair. A new
pair-specific render contributes only one compact lower mandible and its
bounded oral cavity. The exact closed frame remains authoritative for the
crest, eye, face, cheek, throat, hoodie, fishbone mark, pointing wing, body,
feet, registration, and upper bill. The lower bill rotates from the authored
screen-left hinge and ends behind the immutable upper-bill tip. Native beak
focus, white-background full-character, and alternating playback review show
no duplicate edge, donor throat pixels, head movement, or body drift. The
accepted audit reports `1,942` changed rendered pixels, outside-mouth mean
difference `0.0`, silhouette IoU `1.0`, connected-mandible ratio `1.0`, and
registration delta `0`.

Rejected legacy pair 64 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-064-v2/`

Accepted internal pair 64 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-064-v3/`

Pair 65 (`write or tap`) failed despite its previous broad audit because the
open frame presented two long, nearly parallel downward bill blades. The old
candidate is retained as rejected evidence. Its replacement was built and
reviewed as this pair alone from a new matched render with a clearly open
lower mandible.

The exact closed frame remains authoritative for the crest, eye, face, cheek,
throat, hoodie, fishbone mark, crossed wings, body, feet, registration, and
upper bill. Only the connected lower mandible and bounded oral cavity come
from the matched render. Native beak-focus, white-background full-character,
and alternating playback review show one fixed hinge, a lower tip behind the
upper tip, and no duplicate blade, head movement, or body drift. The accepted
audit reports `1,906` changed rendered pixels, outside-mouth mean difference
`0.0`, silhouette IoU `0.999975`, connected-mandible ratio `1.0`, and
registration delta `0`.

Rejected legacy pair 65 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-065-v2/`

Accepted internal pair 65 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-065-v3/`

Pair 66 (`select a control`) failed its native close-up review with two long,
competing bill edges, an oversized white opening, and a lower tip that nearly
matched the upper tip. The legacy frame is preserved as rejected evidence.
The replacement was rendered and admitted as one isolated pair.

The original closed frame remains authoritative for the crest, eye, face,
cheek, throat, hoodie, fishbone mark, extended wing, body, feet, registration,
and upper bill. A matched render supplies only one shorter connected lower
mandible and its bounded oral cavity. Native beak-focus, white-background
full-character, and alternating playback review show one fixed hinge, no
duplicate edge, no white gap, and no head or body movement. The accepted audit
reports `1,370` changed rendered pixels, outside-mouth mean difference `0.0`,
silhouette IoU `0.997451`, connected-mandible ratio `1.0`, and registration
delta `0`.

Rejected legacy pair 66 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-066-v2/`

Accepted internal pair 66 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-066-v3/`

Complete Kingfisher-focused suite after the pair 66 rebuild: 71 passed. The
reviewer UI tests are included in that run.

The strict verifier now passes because all observable pairs have an internal
full-size pass and both rear views are explicitly `not_observable`. It writes
the structured verification receipt here:

`assets/reference/characters/kingfisher/legacy-pairs-v1/review-evidence/pair-review-verification.json`

Current review artifact:

`kingfisher_act_001_066_111_176_pair_review-7b5e3f2683708423.wjpose`

Artifact SHA-256:

`7b5e3f26837084239f09a020fecde5d513ef8e45409fb7986a7e979efcd1f104`

Library-index SHA-256:

`7b39c6b14594369347910c330dfda75968dd1039b62bd1a24bbca5567ca194c6`

Queue state: 64 internal full-size passes, 0 pending, 0 needs rebuild, and
2 not observable. Runtime-admitted and user-approved counts remain zero.

The verifier reports `passed: true`. This is an internal visual-review result;
it does not imply user approval or runtime admission.

## 2026-08-03 Pairwise Reset Continuation

The user-reported beak misalignment invalidated the earlier bulk completion
state above. The ledger, compiled review sequence, and verifier receipt are the
authoritative current state; historical passes remain documented only as
superseded evidence.

Pair 3 (`left-profile`) was recaptured and inspected as one locked full-size
closed/open pair. The lower bill opens from the rear mouth corner along the
authored left-facing bill axis, remains behind the upper tip, and leaves the
eye, crown, throat, hoodie, feet, body, and registration unchanged. Its audit
reports outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `0.979838`.

Fresh pair 3 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-003-recheck-2026-08-03/`

After this isolated review, the queue contains 3 fresh internal passes,
61 pending pairs, and 2 rear-view pairs marked `not_observable`. User-approved
and runtime-admitted counts remain zero. The verifier remains intentionally
blocked by the next pending observable pair.

Pair 6 (`right-profile`) was then recaptured and inspected independently. Its
lower bill shares the closed frame's rear hinge and right-facing bill axis,
ends behind the upper tip, and introduces no duplicate edge or non-mouth body
change. The automated audit reports outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.978551`.

Fresh pair 6 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-006-recheck-2026-08-03/`

The current queue therefore contains 4 fresh internal passes, 60 pending
pairs, and 2 not-observable rear views. User approval and runtime admission
remain closed.

Pair 7 (`front-three-quarter-right`) failed the fresh locked comparison even
though its legacy broad-region audit was green. The speaking frame had redrawn
the upper bill on a higher axis, producing a one-pixel registration expansion
and a visible closed/open snap. That frame and its receipts are preserved as
rejected evidence.

The replacement uses the closed frame for all body pixels and the complete
upper bill. The old speaking render contributes only a translated, connected
lower-mandible patch and bounded cavity. The accepted audit reports
outside-mouth mean difference `0.0`, registration delta `0`, silhouette IoU
`0.999960`, and connected-mandible ratio `1.0`.

Rejected pair 7 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-007-rejected-pre-pairwise-2026-08-03/`

Accepted pair 7 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-007-rebuilt-v1/`

The queue now contains 5 fresh internal passes, 59 pending pairs, and 2 rear
views marked not observable. User approval and runtime admission remain zero.

Pair 8 (`relaxed-idle`) also failed its legacy candidate. The old broad mask
changed the upper bill and a large white/orange throat region while still
reporting zero change outside that oversized rectangle. Two bounded
reconstruction attempts were retained but rejected: the first was too close
to closed at presentation size, and the second restored the closed lower edge
along with the upper bill, creating a three-line beak in the magnified crop.

The accepted third candidate narrows the immutable upper-bill mask, explicitly
clears the old closed lower edge, and composites one restrained connected
mandible and cavity. Its audit reports outside-mouth mean difference `0.0`,
registration delta `0`, silhouette IoU `0.995701`, and connected-mandible
ratio `1.0`.

Rejected pair 8 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-008-rejected-pre-pairwise-2026-08-03/`

Accepted pair 8 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-008-rebuilt-v1/`

The current queue contains 6 fresh internal passes, 58 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero.

Pair 9 (`attentive-idle`) exposed the same false-positive pattern in a frontal
pose. The legacy speaking mate looked centered at presentation size, but the
old articulation rectangle had replaced most of the white and orange throat.
The first bounded reconstruction was also rejected because its opaque polygon
copied pale throat pixels and left two dark vertical mask edges.

The accepted reconstruction starts from the immutable closed frame and uses a
compact donor mask that excludes light, low-chroma throat pixels while keeping
the dark beak rim, orange lower mandible, and pink cavity. No clearing polygon
is used. Full-size and magnified inspection show one centered opening with a
clean hinge and unchanged surrounding throat. The audit reports outside-mouth
mean difference `0.0`, registration delta `0`, silhouette IoU `1.0`, and a
connected-mandible ratio of `0.974833`.

Rejected pair 9 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-009-rejected-pre-pairwise-2026-08-03/`

Accepted pair 9 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-009-rebuilt-v1/`

The current queue contains 7 fresh internal passes, 57 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 10 is the next isolated review gate.

Pair 10 (`ready-stance`) had a visually centered legacy opening, but its green
audit concealed another oversized articulation patch: 5,806 rendered pixels
and most of the central throat were replaced inside a 93 by 83 rectangle. The
legacy mate was therefore preserved as a false-positive rejection rather than
passed on beak alignment alone.

The accepted reconstruction transfers only the color-filtered mouth geometry
onto the immutable closed frame. It retains the original upper beak, eyes,
throat, hoodie, wings, feet, and canvas registration. The replacement changes
1,537 pixels, with outside-mouth mean difference `0.0`, registration delta
`0`, silhouette IoU `1.0`, and connected-mandible ratio `0.904784`.

Rejected pair 10 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-010-rejected-pre-pairwise-2026-08-03/`

Accepted pair 10 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-010-rebuilt-v1/`

The current queue contains 8 fresh internal passes, 56 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 11 is the next isolated review gate.

Pair 11 (`neutral-speaking-gesture`) failed with the largest false-positive
region in this continuation: 10,209 rendered pixels across a 102 by 129 box,
including a broad throat wedge. The acting pose itself was retained exactly.

Five compact candidates were inspected. Candidate 1 remained too broad;
candidates 3 through 5 cut across the diagonal right beak rim and produced a
visible vertical edge. Candidate 2 is the accepted reconstruction because it
keeps the complete centered V-shaped rim without restoring the legacy throat
wedge. It changes 4,091 pixels, with outside-mouth mean difference `0.0`,
registration delta `0`, silhouette IoU `1.0`, and connected-mandible ratio
`0.995627`. Every candidate remains in pair work as rejection evidence.

Rejected pair 11 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-011-rejected-pre-pairwise-2026-08-03/`

Accepted pair 11 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-011-rebuilt-v1/`

The current queue contains 9 fresh internal passes, 55 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 12 is the next isolated review gate.

Pair 12 (`explain-one-point`) looked centered at presentation size, but its
legacy green audit was another broad-mask false positive: 9,288 rendered
pixels across a 93 by 126 region replaced the lower face and throat along with
the mouth. The raised one-point gesture and every non-mouth body pixel were
kept unchanged.

The accepted reconstruction starts from the immutable closed frame and
transfers only the color-filtered lower mandible and cavity. Full-size and
magnified inspection show one centered V-shaped opening, a complete upper-beak
rim, an unchanged feathered throat, and no duplicate or rectangular beak
artifact. The replacement changes 2,768 rendered pixels, with outside-mouth
mean difference `0.0`, registration delta `0`, silhouette IoU `1.0`, and
connected-mandible ratio `0.812370`.

Rejected pair 12 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-012-rejected-pre-pairwise-2026-08-04/`

Accepted pair 12 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-012-rebuilt-v1/`

The current queue contains 10 fresh internal passes, 54 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 13 is the next isolated review gate.

Pair 13 (`balance-two-ideas`) did not require another reconstruction. Its
existing frame is already a pair-specific connected-mandible composite rather
than a broad legacy mask. Full-size and nearest-neighbor inspection confirm
that the upper bill, eyes, crown, wings, hoodie, feet, canvas, and body
registration remain locked. The lower mandible's diagonal perspective is
authored anatomy: it stays hinge-connected and its tip remains centered, with
no detached duplicate edge.

The existing audit reports 3,643 changed rendered pixels, outside-mouth mean
difference `0.0`, registration delta `0`, silhouette IoU `1.0`, and
connected-mandible ratio `1.0`.

Fresh pair 13 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-013-fresh-pass-2026-08-04/`

The current queue contains 11 fresh internal passes, 53 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 14 is the next isolated review gate.

Pair 14 (`present-screen-left`) failed the fresh profile comparison. The legacy
open frame lengthened and redrew the upper bill several pixels left of the
closed silhouette, while its green audit treated a 6,250-pixel lower-face
rectangle as one permissible mouth region.

Five replacements were retained and rejected before acceptance. Candidate 1
left the closed lower-edge fringe as a third bill line. Candidate 2 cleared
that fringe but exposed a transparent rear-hinge notch. Candidate 3 filled the
notch with an artificial dark slab. Candidate 4 restored the donor mouth but
kept the closed fringe. Candidate 5 removed the fringe and then reintroduced
the donor's overlong upper edge during its final cavity overlay.

Accepted Candidate 6 replaces one compact lower-beak/cavity polygon, clears
the closed lower-edge residual, and makes a tight closed-upper-bill restore the
final operation. Full-size and magnified inspection show the exact closed
upper-bill length, one continuous cavity, one lower bill, and unchanged
throat/body geometry. Its audit reports 2,331 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, silhouette IoU
`0.993514`, and connected-mandible ratio `0.999499`.

Rejected pair 14 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-014-rejected-pre-pairwise-2026-08-04/`

Accepted pair 14 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-014-rebuilt-v1/`

The current queue contains 12 fresh internal passes, 52 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 15 is the next isolated review gate.

Pair 15 (`present-screen-right`) also failed the fresh profile comparison. Its
legacy open frame looked plausible at fitted size, but the magnified difference
view showed that the full upper bill had been regenerated inside an 8,142-pixel
articulation rectangle. The old automated audit therefore proved only that the
large edit was bounded; it did not prove that the upper bill stayed registered.

Accepted Candidate 1 uses the rejected open render only as a lower-mandible
donor. It restores the resting upper bill pixel-for-pixel as the final visual
authority, keeps the authored rear hinge and right-facing perspective axis, and
introduces no duplicate bill edge or body movement. Full-size and nearest-
neighbor inspection show one attached lower bill and a continuous, restrained
mouth cavity. Its audit reports 974 changed rendered pixels, outside-mouth mean
difference `0.0`, registration delta `0`, silhouette IoU `0.994760`, and
connected-mandible ratio `1.0`.

Rejected pair 15 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-015-rejected-pre-pairwise-2026-08-04/`

Accepted pair 15 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-015-rebuilt-v1/`

The current queue contains 13 fresh internal passes, 51 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 16 is the next isolated review gate.

Pair 16 (`point-to-viewer`) failed the fresh frontal comparison. The legacy
open frame regenerated both side plates and the central upper bill inside an
8,693-pixel face rectangle. This made the whole beak assembly expand during
speech even though the body-registration audit remained green.

Accepted Candidate 1 uses the legacy open frame only for the lower V-shaped
mandible and cavity. The closed frame supplies the immutable eyes, cheeks,
side plates, and central upper bill. Full-size and magnified review show a
centered lower opening with bilateral hinge alignment, no duplicate edge, no
face expansion, and no body movement. Its audit reports 4,470 changed rendered
pixels, outside-mouth mean difference `0.0`, registration delta `0`,
silhouette IoU `1.0`, and connected-mandible ratio `1.0`.

Rejected pair 16 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-016-rejected-pre-pairwise-2026-08-04/`

Accepted pair 16 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-016-rebuilt-v1/`

The current queue contains 14 fresh internal passes, 50 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 17 is the next isolated review gate.

Pair 17 (`insight-upward-point`) failed the fresh upward-profile comparison.
The legacy open frame regenerated the complete upper bill inside a 6,555-pixel
articulation rectangle, allowing the upper silhouette and texture to slide
during the mouth change.

Accepted Candidate 1 restores the resting upward-left upper bill, eye-side
hinge, face, and throat pixel-for-pixel. Only one connected lower mandible and
its restrained cavity come from the rejected donor. Full-size and magnified
review show a coherent downward jaw rotation, no upper-bill slide, no duplicate
edge, and no body movement. Its audit reports 1,081 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, silhouette IoU
`0.995961`, and connected-mandible ratio `0.999438`.

Rejected pair 17 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-017-rejected-pre-pairwise-2026-08-04/`

Accepted pair 17 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-017-rebuilt-v1/`

The current queue contains 15 fresh internal passes, 49 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 18 is the next isolated review gate.

Pair 18 (`detail-downward-point`) failed the fresh downward-profile
comparison. The legacy open frame regenerated the complete upper bill,
nostril, cheek edge, and throat boundary inside an 11,928-pixel lower-face
rectangle. The old green audit therefore bounded the redraw without proving
that the closed-frame head structures remained fixed.

Candidate 1 correctly restored the upper bill and head, but its protection
polygon extended through the mouth and erased almost all of the donor lower
mandible, leaving a detached sliver. Candidate 2 narrows the immutable restore
to the approved resting upper bill and starts every other pixel from the
resting frame. It transfers only one rear-hinge-connected lower mandible and a
restrained cavity. Full-size and magnified review show the correct downward
perspective, no detached sliver, no upper-bill redraw, no duplicate edge, and
no body movement. Its audit reports 4,186 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, silhouette IoU
`0.999987`, and connected-mandible ratio `1.0`.

Rejected pair 18 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-018-rejected-pre-pairwise-2026-08-04/`

Accepted pair 18 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-018-rebuilt-v1/`

The current queue contains 16 fresh internal passes, 48 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 19 is the next isolated review gate.

Pair 19 (`neutral-listening`) looked plausible at fitted size but failed the
magnified structural comparison. Its legacy 7,253-pixel articulation rectangle
replaced the complete upper bill together with the lower mandible. The green
audit therefore proved that the edit stayed inside a broad face box, not that
the approved upper bill remained fixed.

Accepted Candidate 1 starts from the approved resting character and restores
the complete resting upper bill pixel-for-pixel after transferring one
connected lower mandible and restrained cavity from the rejected donor.
Full-size and magnified inspection show a shared rear hinge, readable but
subtle speech motion, no upper-bill redraw, no duplicate edge, and no body
movement. Its audit reports 4,146 changed rendered pixels, outside-mouth mean
difference `0.0`, registration delta `0`, silhouette IoU `1.0`, and
connected-mandible ratio `1.0`.

Rejected pair 19 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-019-rejected-pre-pairwise-2026-08-04/`

Accepted pair 19 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-019-rebuilt-v1/`

The current queue contains 17 fresh internal passes, 47 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 20 is the next isolated review gate.

Pair 20 (`lean-in-listening`) retained a strong expression but failed the
strict structural comparison. Its legacy 9,412-pixel face patch regenerated
the central upper-bill triangle together with the lower V mouth. The edit was
bounded, but the approved closed bill was not immutable.

Candidates 1 and 2 restored too much of the central bill and compressed the
speaking mouth into a thin line. Accepted Candidate 3 tightens the immutable
restore to the actual resting upper-bill triangle and retains the donor's
centered V-shaped lower mouth. Full-size and magnified review show bilateral
hinge coherence, a readable opening, no upper-bill redraw, no duplicate line,
and no body movement. Its audit reports 5,837 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, silhouette IoU
`1.0`, and connected-mandible ratio `1.0`.

Rejected pair 20 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-020-rejected-pre-pairwise-2026-08-04/`

Accepted pair 20 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-020-rebuilt-v1/`

The current queue contains 18 fresh internal passes, 46 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 21 is the next isolated review gate.

Pair 21 (`skeptical-listening`) required a fresh review but not another
rebuild. Unlike the legacy broad-mask pairs, its current speaking mate already
comes from the pair-specific connected-mandible compositor. The receipt records
an immutable upper-beak source region, a connected-mandible ratio of `1.0`, and
zero changes outside the articulation region.

Fresh full-size and magnified inspection confirms that the skeptical eye line,
crown, cheek, throat, folded wing, hoodie, body, scale, and registration remain
fixed. One lower bill opens from the visible rear hinge beneath a stable upper
silhouette, with no detached sliver, duplicate edge, or body drift. Its existing
audit reports 5,621 changed rendered pixels, outside-mouth mean difference
`0.0`, registration delta `0`, and silhouette IoU `0.999443`.

Fresh pair 21 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-021-recheck-2026-08-04/`

The current queue contains 19 fresh internal passes, 45 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 22 is the next isolated review gate.

Pair 22 (`small-acknowledgment`) failed the fresh full-size and magnified
comparison even though its previous localization audit was green. The opaque
donor mask treated pale throat feathers inside the broad lower-face polygon as
mandible pixels, producing a false white triangular projection beneath the
otherwise stable upper bill. The audit proved that the edit was localized; it
did not prove that every localized pixel belonged to the beak.

Accepted Candidate 3 starts from the approved closed frame and keeps its body,
head, eye line, and upper bill pixel-for-pixel. Its donor mask excludes light
neutral throat pixels and transfers only one connected dark lower mandible and
the visible mouth cavity around the shared rear hinge. Full-size and magnified
review show no pale projection, duplicate tip, detached sliver, upper-bill
redraw, or body drift. Its tightened audit reports 4,283 changed rendered
pixels, outside-mouth mean difference `0.0`, registration delta `0`,
silhouette IoU `0.999766`, and connected-mandible ratio `0.979030`.

Rejected pair 22 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-022-rejected-pre-pairwise-2026-08-04/`

Accepted pair 22 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-022-rebuilt-v3-neutral-exclusion/`

The current queue contains 20 fresh internal passes, 44 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 23 is the next isolated review gate.

Pair 23 (`emphatic-agreement`) required a fresh isolated review but not another
rebuild. Its current speaking mate already comes from the pair-specific
connected-mandible compositor rather than a broad generated face patch. The
receipt records an immutable closed-frame upper bill, connected-mandible ratio
`1.0`, and zero changes outside the articulation region.

Fresh full-size and 4x beak inspection confirms that the crown, eyes, cheek
plates, throat, torso, wings, feet, scale, and registration remain fixed. One
centered lower mandible opens from the authored hinge beneath the unchanged
upper bill, with no lateral tip jump, duplicate edge, detached sliver, or body
drift. Its existing audit reports 8,881 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh pair 23 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-023-recheck-2026-08-04/`

The current queue contains 21 fresh internal passes, 43 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 24 is the next isolated review gate.

Pair 24 (`polite-interruption`) also required a fresh perspective-aware review
but not another rebuild. Its current speaking mate already uses the
pair-specific connected-mandible compositor and preserves the approved closed
frame as the authority for the complete upper bill and body.

Fresh full-size and 4x inspection confirms that the three-quarter lower bill
correctly travels diagonally across the throat toward screen-right. It shares
the authored rear hinge, ends beneath the stable upper tip, and does not move
the eyes, crown, cheek, throat, raised wing, torso, feet, scale, or registration.
There is no duplicate edge or detached sliver. Its existing audit reports
3,576 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, silhouette IoU `1.0`, and connected-mandible ratio
`1.0`.

Fresh pair 24 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-024-recheck-2026-08-04/`

The current queue contains 22 fresh internal passes, 42 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 25 is the next isolated review gate.

Pair 25 (`hand-over-the-floor`) failed its fresh full-size, 4x, and live
locked-pair review even though its previous automated audit was green. The
lower mandible remained connected to the authored hinge, but it stopped
noticeably short of the approved upper-bill tip. During speech the profile bill
therefore appeared to telescope instead of opening as one hinged structure.

Accepted Candidate 5 starts from the approved closed frame and leaves the body,
head, eye line, and complete upper bill pixel-for-pixel unchanged. The isolated
lower-mandible donor uses scale `0.502`, horizontal scale `0.65`, translation
`(-78, 52)`, and the authored hinge `(365, 220)`. Its connected lower mandible
runs along the existing profile axis and terminates beneath the stable upper
tip. The compositor reports a mandible bounding box of `(360, 214)-(511, 279)`,
a changed bounding box of `(360, 217)-(511, 279)`, and connected-mandible ratio
`0.999583`. The tightened audit reports 2,380 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette IoU
`0.996829`.

Rejected pair 25 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-025-rejected-short-mandible-2026-08-04/`

Accepted pair 25 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-025-rebuilt-v5-tip-aligned/`

The current queue contains 23 fresh internal passes, 41 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 26 is the next isolated review gate.

Pair 26 (`warm-welcome`) failed its fresh locked-pair and 4x review despite a
green localization audit. The previous compositor changed only rows `272-306`,
well below the true front-facing bill. It therefore left the closed mouth in
place and added a second orange/red mouth beneath the white throat. The old
audit proved that the edit was bounded; it did not prove that the bounded edit
was attached to the character's actual mouth.

Accepted Candidate 4 starts from the approved closed frame and leaves the
crown, eyes, cheeks, complete upper bill, throat, hoodie, body, symmetrical
welcome wings, and feet pixel-for-pixel unchanged. The matched donor remains at
scale `0.574` and horizontal translation `-2`, but its vertical translation is
corrected from `50` to `0`, moving the articulation to the true frontal hinge
`(466, 214)`. A neutral-light exclusion removes the donor's pale throat edge.
The resulting connected lower mandible is centered beneath the upper bill,
with a changed bounding box of `(464, 222)-(506, 252)` and connected-mandible
ratio `1.0`. The tighter true-mouth audit reports 646 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette IoU
`1.0`.

Rejected pair 26 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-026-rejected-double-mouth-2026-08-04/`

Accepted pair 26 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-026-rebuilt-v4-true-hinge/`

The current queue contains 24 fresh internal passes, 40 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 27 is the next isolated review gate.

Pair 27 (`intimate-confidence`) failed its fresh locked-pair and 4x review. Its
main lower mandible was connected, but the donor mask extended past the
screen-right rear hinge and left a thin dark hook in the white throat. The old
receipt also labeled `(455, 263)`, near the bill tip, as the hinge even though
the tilted pose's anatomical rear hinge is on screen-right.

Accepted Candidate 4 starts from the approved closed frame and preserves the
tilted crown, eyes, cheeks, complete upper bill, throat, hoodie, held-in wings,
body, feet, scale, and registration. Its donor polygon is tightened from a
screen-right extent of `516` to `503`, neutral-light throat pixels are excluded,
and the receipt records the actual rear hinge at `(497, 263)` with radius `14`.
The connected lower mandible terminates at that hinge without a dark sliver or
duplicate edge. The tighter audit reports 998 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, silhouette IoU
`1.0`, and connected-mandible ratio `1.0`.

Rejected pair 27 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-027-rejected-right-hinge-sliver-2026-08-04/`

Accepted pair 27 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-027-rebuilt-v4-true-rear-hinge/`

The current queue contains 25 fresh internal passes, 39 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 28 is the next isolated review gate.

Pair 28 (`strong-declaration`) passed a fresh isolated full-size, 4x, and live
locked-pair review without another rebuild. The larger opening is appropriate
to the emphatic pose, remains centered beneath the immutable upper bill, and
meets the same face geometry at both rear corners. The crown, eyes, cheeks,
throat feathers, raised wing, hoodie, body, feet, scale, and registration remain
fixed, with no second mouth, detached edge, or imported texture.

Its existing pair-specific receipt records hinge `(539, 222)`, mandible and
changed bounding box `(534, 218)-(581, 269)`, and connected-mandible ratio
`1.0`. The existing audit reports 887 changed rendered pixels, outside-mouth
mean difference `0.0`, registration delta `0`, and silhouette IoU `1.0`.

Fresh pair 28 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-028-recheck-2026-08-04/`

The current queue contains 26 fresh internal passes, 38 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 29 is the next isolated review gate.

Pair 29 (`confidential-whisper`) failed its fresh isolated full-size, 4x, and
live locked-pair review. The previous lower bill read as a long detached bar
crossing the white throat and ended in a sharp rear sliver instead of joining
the face at one clean mouth hinge. Its green localization audit proved only
that the defect was bounded to the declared mouth region.

Accepted Candidate 17 uses a new pair-specific whisper donor generated from
the immutable closed frame. The compositor extracts only the connected lower
mandible and cavity, restores the approved upper bill pixel-for-pixel, and
rotates the opening around the measured rear hinge `(493, 261)`. The small
opening remains partially occluded by the already raised foreground wing, as
required by the confidential gesture, while the crown, eye, cheek, white
throat, hoodie, body, feet, scale, and registration remain fixed. The accepted
audit reports 2,106 changed rendered pixels, outside-mouth mean difference
`0.0`, registration delta `0`, silhouette IoU `1.0`, and connected-mandible
ratio `0.991361`.

Rejected pair 29 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-029-rejected-detached-throat-bar-2026-08-04/`

Accepted pair 29 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-029-rebuilt-v17-pair-specific-donor/`

The current queue contains 27 fresh internal passes, 37 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 30 is the next isolated review gate.

Pair 30 (`rhetorical-question`) looked plausible at normal size, but failed the
new one-pair-at-a-time immutable-source audit. The previous compositor declared
the broad region `(403, 120)-(545, 251)` as mouth articulation and changed
pixels above the true opening. A tighter audit exposed nonzero change outside
the actual lower bill, so the old result was rejected even though its silhouette
and registration were stable.

Accepted Candidate 2 starts from the approved closed frame and uses the aligned
speaking render only as a connected lower-mandible and cavity donor. The
compositor restores the complete upper bill from the closed source and confines
all 4,379 changed rendered pixels to `(400, 135)-(535, 220)`. Full-size and 4x
inspection confirms that the opening follows the head tilt and joins the face
without a detached edge; the crown, eyes, cheeks, throat, hoodie, raised wings,
body, feet, scale, registration, and silhouette remain unchanged. The strict
audit reports outside-mouth mean difference `0.0`, registration delta `0`,
silhouette IoU `1.0`, and connected-mandible ratio `0.995027`.

Rejected pair 30 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-030-rejected-broad-face-composite-2026-08-04/`

Accepted pair 30 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-030-rebuilt-v2-connected-mandible/`

The current queue contains 28 fresh internal passes, 36 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 31 is the next isolated review gate.

Pair 31 (`compare-two-options`) passed a fresh isolated full-size, 4x, and live
locked-pair review without another rebuild. The existing pair-specific
connected-mandible composite opens from rear hinge `(484, 222)`, remains
directly beneath the immutable upper bill, and ends without a detached edge,
throat sliver, duplicate mouth, or tip offset. The eye, crown, cheek, throat,
hoodie, presenting wings, body, feet, scale, registration, and silhouette remain
fixed.

The accepted receipt records changed bounding box `(481, 221)-(557, 252)` and
connected-mandible bounding box `(478, 216)-(557, 252)`. Its strict audit
reports 1,330 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh pair 31 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-031-recheck-2026-08-04/`

The current queue contains 29 fresh internal passes, 35 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 32 is the next isolated review gate.

Pair 32 (`cause-and-effect`) passed a fresh isolated full-source, 4x, and live
locked-pair review without another rebuild. Its existing pair-specific
immutable-source composite opens one connected lower mandible from rear hinge
`(350, 219)` beneath the fixed upper bill. The beak axis, tip, and rear joint
remain coherent, with no detached edge, throat sliver, duplicate mouth,
imported face texture, or movement in the eyes, crown, cheeks, throat, hoodie,
body, feet, scale, registration, or silhouette.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(346, 220)-(440, 253)`, and mandible bounding box
`(345, 211)-(441, 253)`. The strict audit reports 1,862 changed rendered
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh pair 32 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-032-recheck-2026-08-04/`

The current queue contains 30 fresh internal passes, 34 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 33 is the next isolated review gate.

Pair 33 (`count-one`) passed a fresh isolated full-source, 4x, and live
locked-pair review without another rebuild. Its long side-facing lower bill
joins the canonical rear hinge `(437, 220)`, follows the fixed upper-bill axis,
and terminates beneath the approved tip. No detached edge, duplicate mouth,
throat sliver, imported face texture, or movement in the eye, crown, cheek,
throat, hoodie, raised wing, body, feet, scale, registration, or silhouette is
visible.

The receipt records connected-mandible ratio `1.0`, changed and mandible
bounding box `(430, 214)-(515, 254)`. The strict audit reports 944 changed
rendered pixels, outside-mouth mean difference `0.0`, registration delta `0`,
and silhouette IoU `1.0`.

Fresh pair 33 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-033-recheck-2026-08-04/`

The current queue contains 31 fresh internal passes, 33 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 34 is the next isolated review gate.

Pair 34 (`count-two`) passed a fresh isolated full-source, 4x, and live
locked-pair review without another rebuild. The head is nearly frontal while
the authored bill points toward screen-right; the connected lower mandible
follows that same axis from rear hinge `(461, 174)` and remains beneath the
immutable upper bill. No detached edge, duplicate mouth, throat sliver,
imported face texture, or movement in the eyes, crown, cheeks, throat, hoodie,
body, feet, scale, registration, or silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed and mandible
bounding box `(455, 169)-(531, 202)`. The strict audit reports 913 changed
rendered pixels, outside-mouth mean difference `0.0`, registration delta `0`,
and silhouette IoU `1.0`.

Fresh pair 34 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-034-recheck-2026-08-04/`

The current queue contains 32 fresh internal passes, 32 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 35 is the next isolated review gate.

Pair 35 (`count-three`) passed a fresh isolated full-source, 4x, and live
locked-pair review without another rebuild. Both rear mouth corners remain
anchored while the restrained lower mandible drops symmetrically beneath the
immutable centered upper bill. No lateral beak slide, detached edge, duplicate
mouth, imported throat texture, or movement in the eyes, crown, cheeks, throat,
hoodie, raised-wing gesture, body, feet, scale, registration, or silhouette is
visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(438, 161)-(531, 206)`, mandible bounding box
`(437, 155)-(533, 206)`, and hinge `(449, 166)`. The strict audit reports
2,146 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh pair 35 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-035-recheck-2026-08-04/`

The current queue contains 33 fresh internal passes, 31 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 36 is the next isolated review gate.

Pair 36 (`protective-boundary`) passed a fresh isolated full-source, 4x face,
16x rear-hinge, and live locked-pair review without another rebuild. The small
brown mark at the screen-left mouth corner is present in the approved closed
frame and is canonical beak-corner detail, not a detached donor remnant. The
lower mandible stays connected through the dark rear hinge and drops beneath
the immutable upper bill. No duplicate mouth, imported throat texture, or
movement in the eyes, crown, cheeks, throat, hoodie, defensive wing gesture,
body, feet, scale, registration, or silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(361, 217)-(438, 271)`, mandible bounding box
`(360, 213)-(439, 271)`, and hinge `(370, 225)`. The strict audit reports
1,878 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh pair 36 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-036-recheck-2026-08-04/`

The current queue contains 34 fresh internal passes, 30 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 37 is the next isolated review gate.

Pair 37 (`gentle-reassurance`) passed a fresh isolated full-source, 4x face,
full-character projector, and live locked-pair review without another rebuild.
The connected lower bill shares the canonical rear hinge, follows the same
screen-left diagonal perspective beneath the immutable upper bill, and ends at
the approved tip. No detached edge, duplicate mouth, imported throat texture,
or movement in the eyes, crown, cheeks, throat, hoodie, extended-wing gesture,
body, feet, scale, registration, or silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(484, 233)-(584, 313)`, mandible bounding box
`(484, 226)-(584, 313)`, and hinge `(562, 235)`. The strict audit reports
2,064 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh pair 37 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-037-recheck-2026-08-04/`

The current queue contains 35 fresh internal passes, 29 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 38 is the next isolated review gate.

Pair 38 (`invitation-to-follow`) passed a fresh isolated full-source, 6x face,
full-character projector, and live locked-pair review without another rebuild.
The intentionally restrained lower bill remains joined to the canonical
screen-left hinge and follows the right-facing upper-bill axis. No detached
edge, duplicate mouth, imported throat texture, or movement in the eyes,
crown, cheeks, throat, hoodie, extended-wing gesture, body, feet, scale,
registration, or silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(439, 223)-(502, 258)`, mandible bounding box
`(438, 219)-(502, 258)`, and hinge `(443, 229)`. The strict audit reports
1,413 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.999873`.

Fresh pair 38 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-038-recheck-2026-08-04/`

The current queue contains 36 fresh internal passes, 28 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 39 is the next isolated review gate.

Pair 39 (`describe-a-vast-scene`) required a fresh isolated rebuild after the
4x face and 12x tip review exposed one detached donor pixel at `(550, 146)`.
The accepted speaking frame removes that remnant and keeps the lower mandible
as one connected component. It shares the canonical rear hinge, follows the
long screen-right upper-bill axis, and leaves the eyes, crown, cheeks, throat,
hoodie, both spread wings, body, feet, scale, registration, and silhouette
unchanged.

The rebuilt receipt records connected-mandible ratio `1.0`, changed bounding
box `(477, 133)-(597, 189)`, mandible bounding box `(477, 133)-(597, 189)`, and
hinge `(484, 175)`. The strict audit reports 2,147 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `0.997842`.

Fresh pair 39 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-039-recheck-2026-08-04/`

The current queue contains 37 fresh internal passes, 27 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 40 is the next isolated review gate.

Pair 40 (`describe-a-tiny-detail`) passed a fresh isolated full-source, 6x
mouth, and live locked-beak review without another rebuild. The connected lower
bill stays attached to the canonical rear hinge, follows the same screen-right
axis as the immutable upper bill, and terminates beneath the same tip. No
lateral slide, detached edge, duplicate mouth, imported throat texture, or
movement in the eyes, crown, cheeks, throat, hoodie, raised-wing gesture, body,
feet, scale, registration, or silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(439, 216)-(584, 245)`, mandible bounding box `(439, 224)-(584, 245)`, and
hinge `(446, 231)`. The strict audit reports 2,698 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh pair 40 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-040-recheck-2026-08-04/`

The current queue contains 38 fresh internal passes, 26 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 41 is the next isolated review gate.

Pair 41 (`centered-calm`) passed a fresh isolated full-source, 6x frontal
mouth, and live locked-beak review without another rebuild. Both mouth corners
remain fixed while the connected V-shaped lower mandible opens symmetrically
on the character centerline beneath the immutable frontal upper bill. No
lateral drift, detached edge, duplicate mouth, imported throat texture, or
movement in the eyes, crest, cheeks, throat, hoodie, body, feet, scale,
registration, or silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(443, 231)-(518, 293)`, mandible bounding box `(442, 224)-(519, 297)`, and
recorded hinge `(447, 232)`. The strict audit reports 2,284 changed rendered
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh pair 41 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-041-recheck-2026-08-04/`

The current queue contains 39 fresh internal passes, 25 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 42 is the next isolated review gate.
