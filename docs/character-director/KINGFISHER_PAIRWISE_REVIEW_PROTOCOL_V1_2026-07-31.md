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

Pair 42 (`joy`) passed a fresh isolated full-source, 6x mouth, prior-candidate,
and live locked-beak review without another rebuild. The accepted joy opening
is one connected lower mandible aligned beneath the repaired immutable upper
bill; the tip and rear hinge remain coherent with the slight head turn. The
small screen-left blue patch is unchanged canonical cheek and upper-bill
detail, not transferred mandible residue. No duplicate mouth, imported throat
texture, or movement in the eyes, crest, cheeks, throat, hoodie, raised wings,
body, feet, scale, registration, or silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(442, 145)-(541, 186)`, mandible bounding box `(441, 145)-(541, 186)`, and
hinge `(443, 150)`. The strict audit reports 1,600 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh pair 42 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-042-recheck-2026-08-04/`

The current queue contains 40 fresh internal passes, 24 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 43 is the next isolated review gate.

Pair 43 (`full-laughter`) passed a fresh isolated full-source, 5x mouth, and
live locked-beak review without another rebuild. The intentionally extreme
laughter opening rotates from the same screen-left rear hinge, keeps the
connected lower mandible beneath the immutable upper bill, and ends slightly
behind the upper tip. No floating jaw, duplicate bill, imported throat texture,
or movement in the closed eyes, crest, cheeks, throat, hoodie, both extended
wings, feet, scale, registration, or silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(418, 113)-(568, 165)`, mandible bounding box `(414, 105)-(575, 165)`, and
hinge `(418, 116)`. The strict audit reports 2,542 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `0.999505`.

Fresh pair 43 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-043-recheck-2026-08-04/`

The current queue contains 41 fresh internal passes, 23 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 44 is the next isolated review gate.

Pair 44 (`excitement`) passed a fresh isolated full-source, 6x mouth, and live
locked-beak review without another rebuild. The compact excitement opening
remains centered beneath the immutable frontal upper bill, with a connected
lower mandible and stable bilateral mouth corners. No detached edge, duplicate
bill, imported throat texture, or movement in the eyes, crest, cheeks, throat,
hoodie, both raised wings, body, feet, scale, registration, or silhouette is
visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(454, 236)-(536, 279)`, mandible bounding box `(454, 236)-(540, 279)`, and
recorded hinge `(458, 239)`. The strict audit reports 1,050 changed rendered
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh pair 44 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-044-recheck-2026-08-04/`

The current queue contains 42 fresh internal passes, 22 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 45 is the next isolated review gate.

Pair 45 (`curiosity`) passed a fresh isolated full-source, 7x tilted-mouth,
and live locked-beak review without another rebuild. The compact lower
mandible remains attached to the canonical screen-left hinge and follows the
tilted upper-bill geometry without lateral drift. No detached edge, duplicate
bill, imported throat texture, or movement in the eyes, crest, cheeks, throat,
hoodie, wings, body, feet, scale, registration, or silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(444, 233)-(489, 275)`, mandible bounding box `(442, 230)-(489, 277)`, and
hinge `(446, 244)`. The strict audit reports 1,066 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh pair 45 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-045-recheck-2026-08-04/`

The current queue contains 43 fresh internal passes, 21 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 46 is the next isolated review gate.

Pair 46 (`confident-hero`) passed a fresh isolated full-source, 6x frontal-
mouth, and live locked-beak review without another rebuild. The opening stays
centered beneath the immutable upper bill, both mouth corners remain fixed,
and the lower mandible remains one connected component. No detached edge,
duplicate bill, imported throat texture, or movement in the eyes, crest,
cheeks, throat, hoodie, extended wings, body, feet, scale, registration, or
silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(447, 185)-(514, 229)`, mandible bounding box `(447, 181)-(514, 229)`, and
hinge `(450, 194)`. The strict audit reports 2,532 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh pair 46 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-046-recheck-2026-08-04/`

The current queue contains 44 fresh internal passes, 20 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 47 is the next isolated review gate.

Pair 47 (`compassion`) passed a fresh isolated full-source, 6x steep-angle
mouth, and live locked-beak review without another rebuild. The long lower
mandible rotates from the same screen-right rear hinge as the immutable upper
bill and converges at the same screen-left tip. No lateral drift, detached
edge, duplicate bill, imported throat texture, or movement in the eye, crest,
cheeks, throat, hoodie, extended wing, body, feet, scale, registration, or
silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(462, 234)-(528, 331)`, mandible bounding box `(462, 225)-(528, 331)`, and
hinge `(512, 238)`. The strict audit reports 2,537 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh pair 47 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-047-recheck-2026-08-04/`

The current queue contains 45 fresh internal passes, 19 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 48 is the next isolated review gate.

Pair 48 (`surprise`) failed its fresh isolated review and was rebuilt alone.
The rejected speaking mate was centered, but its oversized black cavity
visually replaced most of the canonical upper bill and read as a pasted
triangle rather than a hinged lower mandible. That failed disposition and its
full-source and live locked evidence remain preserved at:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-048-rejected-giant-cavity-2026-08-04/`

The accepted successor uses a new matched donor only for one connected lower
mandible and its shaded cavity. The canonical frame restores the upper bill
and owns the wide-eyed gaze, crest, cheeks, throat, hoodie, spread wings,
body, feet, canvas, registration, and silhouette. Full-source, 5x mouth,
full-character, and live locked review show the lower opening centered beneath
the stable upper bill and attached at both rear corners.

The accepted receipt records connected-mandible ratio `0.975081`, changed
bounding box `(470, 161)-(591, 226)`, mandible bounding box
`(470, 135)-(591, 226)`, and hinge `(574, 154)`. The strict audit reports
2,059 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Accepted pair 48 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-048-rebuilt-2026-08-04/`

The review recorder now archives any non-pending full-size disposition before
a later review supersedes it. This makes a `needs_rebuild` rejection and its
evidence durable when the repaired successor is subsequently marked `pass`.

The current queue contains 46 fresh internal passes, 18 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 49 is the next isolated review gate.

Pair 49 (`confusion`) passed a fresh isolated locked-beak, full-character, and
alternating-playback review without another rebuild. The upper bill remains
pixel-identical to the canonical closed frame while one narrow connected lower
mandible opens from the same screen-right hinge. No lateral beak drift,
detached edge, duplicate bill, imported throat texture, or movement in the
eyes, crest, cheeks, throat, hoodie, raised-wing gesture, body, feet, scale,
registration, or silhouette is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(492, 207)-(596, 250)`, mandible bounding box `(492, 194)-(596, 250)`, and
hinge `(584, 207)`. The strict audit reports 3,022 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `0.99991`.

Fresh pair 49 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-049-rechecked-2026-08-04/`

The current queue contains 47 fresh internal passes, 17 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 50 is the next isolated review gate.

Pair 50 (`skepticism`) passed a fresh isolated locked-beak, full-character,
and alternating-playback review without another rebuild. The pose's long
diagonal upper bill remains pixel-identical to the canonical closed frame,
while one connected lower mandible rotates beneath it from the same
screen-right rear hinge. The narrow speaking aperture reads cleanly at full
character scale without a doubled bill or detached edge.

The receipt records connected-mandible ratio `0.995865`, changed bounding box
`(409, 215)-(504, 272)`, mandible bounding box `(409, 215)-(504, 272)`, and
hinge `(497, 222)`. The strict audit reports 1,451 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `0.999969`.

Fresh pair 50 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-050-rechecked-2026-08-04/`

The current queue contains 48 fresh internal passes, 16 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 51 is the next isolated review gate.

Pair 51 (`concern`) passed a fresh isolated locked-beak, full-character, and
alternating-playback review without another rebuild. The steep downward upper
bill remains pixel-identical to the canonical closed frame, and one connected
lower mandible rotates beneath it from the same screen-right rear hinge. The
opening preserves the concerned expression and remains subtle at full-character
scale without a detached point or doubled edge.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(398, 239)-(507, 304)`, mandible bounding box `(399, 240)-(507, 304)`, and
hinge `(497, 247)`. The strict audit reports 2,792 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh pair 51 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-051-rechecked-2026-08-04/`

The current queue contains 49 fresh internal passes, 15 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 52 is the next isolated review gate.

Pair 52 (`sadness`) failed its fresh isolated review and was rebuilt as one
closed/open pair. The rejected speaking mate introduced a long diagonal oral
wedge across the canonical white throat, imported donor throat texture, and
made the lower bill read as a pasted blade. The rejected source, close-up,
full-character, and playback evidence remain preserved at:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-052-rejected-throat-wedge-2026-08-04/`

Whole-character generation and a neighboring-pose donor were both rejected
because they changed head scale or transferred incompatible throat geometry.
The accepted successor instead uses a dedicated head-only donor and transplants
only one tightly bounded lower mandible. The canonical closed frame owns the
upper bill, eyes, crest, face, throat patch, hoodie, body, feet, canvas,
registration, and silhouette. The lower tip now lands directly beneath the
upper tip and connects at the authored screen-right hinge without a duplicate
edge or throat replacement.

The accepted receipt records connected-mandible ratio `1.0`, changed bounding
box `(407, 261)-(478, 308)`, mandible bounding box
`(407, 252)-(488, 308)`, and hinge `(480, 256)`. The strict audit reports 541
changed rendered pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `1.0`.

Accepted pair 52 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-052-rebuilt-2026-08-04/`

The current queue contains 50 fresh internal passes, 14 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 53 is the next isolated review gate.

Pair 53 (`embarrassment`) failed its fresh isolated review and was rebuilt as
one closed/open pair. The rejected speaking mate contained two thin lower-bill
blades diverging from the mouth hinge and a white/orange insert that replaced
canonical throat and hoodie texture. The rejected full-character and 5x
close-up evidence remains preserved at:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-053-rejected-double-blade-2026-08-05/`

The accepted successor uses a dedicated head-only donor but transfers only one
tightly bounded lower mandible and its narrow cavity. The canonical resting
frame continues to own the upper bill, eye, brow patch, head feathers, white
neck feathers, hoodie, body, canvas, registration, and silhouette. Full-size
closed/open comparison and alternating playback show one lower tip aligned
beneath the upper tip and one continuous connection to the screen-right rear
hinge, with no second blade or imported throat pixels.

The accepted receipt records connected-mandible ratio `1.0`, changed bounding
box `(371, 232)-(437, 295)`, mandible bounding box
`(371, 231)-(442, 296)`, and hinge `(432, 236)`. The strict audit reports 884
changed rendered pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `0.99886`.

Accepted pair 53 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-053-rebuilt-2026-08-05/`

The current queue contains 51 fresh internal passes, 13 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 54 is the next isolated review gate.

Pair 54 (`shame`) failed its fresh isolated review and was rebuilt as one
closed/open pair. The rejected speaking mate opened as a long bright-red,
tongue-like vertical slit beside a detached dark bill edge, so the mouth no
longer read as one solid lower mandible rotating beneath the bowed upper bill.
The rejected source, full-character, and close-up evidence remains preserved
at:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-054-rejected-tongue-slit-2026-08-05/`

The accepted successor keeps the canonical closed frame in complete ownership
of the bowed upper bill, eye, crest, cheek, throat, hoodie, body, feet, canvas,
registration, and silhouette. A dedicated donor contributes only one connected
lower bill. A narrowly scoped oral-region neutralization removes warm donor
pixels that caused the tongue-like slit while preserving the orange facial and
plumage markings outside the mouth. Full-size comparison and live alternating
playback show one dark lower bill opening from the authored hinge with no
detached edge or bright oral stripe.

The accepted receipt records connected-mandible ratio `1.0`, changed bounding
box `(506, 240)-(530, 348)`, mandible bounding box
`(506, 240)-(534, 348)`, and hinge `(518, 248)`. The strict audit reports 2,138
changed rendered pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `1.0`.

Accepted pair 54 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-054-rebuilt-2026-08-05/`

The current queue contains 52 fresh internal passes, 12 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 55 is the next isolated review gate.

Pair 55 (`fear`) failed its fresh isolated review and was rebuilt as one
closed/open pair. The rejected speaking mate used an oversized triangular
lower jaw that crossed the canonical white throat, overwhelmed the upper bill,
and changed the fear expression's silhouette. The rejected full-character and
native-size closed/open evidence remains preserved at:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-055-rejected-oversized-jaw-2026-08-05/`

The accepted successor reuses the pair-specific donor only for one reduced,
shallow lower bill and its textured cavity. The canonical resting frame remains
the sole owner of the upper bill, eyes, head, throat, hoodie, raised-wing
gesture, body, feet, canvas, registration, and silhouette. Native-size
closed/open comparison and alternating playback show the lower bill opening
from the existing screen-right hinge without covering the throat or introducing
a second edge.

The accepted receipt records connected-mandible ratio `1.0`, changed bounding
box `(532, 228)-(601, 265)`, mandible bounding box
`(532, 221)-(614, 265)`, and hinge `(603, 225)`. The strict audit reports 975
changed rendered pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `0.999655`.

Accepted pair 55 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-055-rebuilt-2026-08-05/`

The current queue contains 53 fresh internal passes, 11 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 56 is the next isolated review gate.

Pair 56 (`anxiety`) passed a fresh isolated native-size, full-character, and
alternating-playback review without another rebuild. One compact lower bill
opens from the screen-left rear hinge toward the existing upper tip. The two
tips remain aligned, the anxious sideways glance and body pose remain intact,
and no duplicate edge, throat replacement, registration drift, or body change
is visible.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(442, 225)-(516, 274)`, mandible bounding box
`(438, 220)-(516, 274)`, and hinge `(443, 227)`. The strict audit reports 1,352
changed rendered pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `1.0`.

Fresh pair 56 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-056-rechecked-2026-08-05/`

The current queue contains 54 fresh internal passes, 10 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 57 is the next isolated review gate.

Pair 57 (`anger`) passed a fresh isolated native-size, full-character, and
alternating-playback review without another rebuild. The frontal speaking pose
opens as one centered, symmetrical lower bill connected at both rear corners
beneath the immutable upper bill. Its magnified gape remains appropriately
small at full-character scale, preserves the angry expression, and introduces
no duplicate edge, throat replacement, registration drift, or body change.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(436, 250)-(525, 305)`, mandible bounding box
`(430, 241)-(531, 305)`, and hinge `(437, 249)`. The strict audit reports 2,696
changed rendered pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `1.0`.

Fresh pair 57 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-057-rechecked-2026-08-05/`

The current queue contains 55 fresh internal passes, 9 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 58 is the next isolated review gate.

Pair 58 (`frustration`) passed a fresh isolated native-size, full-character,
and alternating-playback review without another rebuild. The diagonal lower
bill opens from the authored screen-right rear hinge beneath the bowed upper
bill and follows the original perspective toward the lower screen-left tip.
The apparent offset in the magnified crop disappears at full-character scale;
there is one connected lower edge, no duplicated tip, no throat replacement,
no registration drift, and no body change.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(420, 255)-(480, 321)`, mandible bounding box `(420, 254)-(480, 321)`, and
hinge `(471, 260)`. The strict audit reports 1,343 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh pair 58 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-058-rechecked-2026-08-05/`

The current queue contains 56 fresh internal passes, 8 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 59 is the next isolated review gate.

Pair 59 (`determination`) failed its fresh isolated review and was rebuilt as
one closed/open pair. The rejected speaking mate used a lower bill that stopped
roughly one quarter-beak behind the canonical upper tip, so alternating
playback read as a short blade opening beneath a full-length kingfisher bill.
The rejected full-character, close-up, and playback evidence remains preserved
at:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-059-rejected-short-mandible-2026-08-05/`

The accepted successor was generated from Pair 59's own isolated head and beak,
then reduced to an alpha donor. The deterministic compositor transfers only one
long lower mandible and its narrow cavity. The canonical resting frame remains
the sole owner of the upper bill, eyes, crest, cheek, throat, hoodie, wings,
body, feet, canvas, and registration. The lower tip now reaches the canonical
upper-tip boundary from the existing rear hinge without a detached edge,
duplicated bill, imported matte, or body change.

The accepted receipt records connected-mandible ratio `0.9978`, changed
bounding box `(535, 244)-(683, 292)`, mandible bounding box
`(530, 238)-(683, 292)`, and hinge `(540, 247)`. The strict audit reports
2,770 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.994619`.

Accepted pair 59 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-059-rebuilt-2026-08-05/`

The current queue contains 57 fresh internal passes, 7 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 60 is the next isolated review gate.

Pair 60 (`fatigue`) passed a fresh isolated native-size, full-character, and
alternating-playback review without another rebuild. One lower bill opens from
the authored screen-right hinge beneath the downward-facing upper bill. The
tips remain aligned and the narrow warm cavity stays inside the beak, with no
duplicate edge, throat replacement, registration drift, or body change.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(375, 252)-(455, 298)`, mandible bounding box `(375, 247)-(460, 298)`, and
hinge `(450, 258)`. The strict audit reports 2,092 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh pair 60 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-060-rechecked-2026-08-05/`

The current queue contains 58 fresh internal passes, 6 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 61 is the next isolated review gate.

Pair 61 (`deep contemplation`) passed a fresh isolated native-size,
full-character, and alternating-playback review without another rebuild. The
bill's steep downward angle belongs to the authored contemplative head pose.
One lower mandible opens from the existing screen-right rear hinge, follows
the upper-bill axis, and reaches the same screen-left tip. The transition adds
no duplicate edge, throat replacement, registration drift, or body change.

The receipt records connected-mandible ratio `1.0`, changed bounding box
`(412, 213)-(473, 282)`, mandible bounding box `(409, 207)-(480, 282)`, and
hinge `(468, 216)`. The strict audit reports 1,700 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh pair 61 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-061-rechecked-2026-08-05/`

The current queue contains 59 fresh internal passes, 5 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 62 is the next isolated review gate.

Pair 62 (`sudden idea`) failed its fresh isolated review and was rebuilt as one
closed/open pair. The rejected speaking frame kept the rear hinge attached but
used a short lower mandible that ended visibly behind the canonical upper tip.
That version's full-character, close-up, and playback evidence remains at:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-062-rejected-short-mandible-2026-08-05/`

The accepted successor uses Pair 62's own full-resolution head as the sole
generation reference. A pair-specific image-generation pass produced one long
open kingfisher bill on a removable chroma background. The deterministic
compositor then isolated only the lower mandible and bounded oral cavity over
the immutable canonical resting frame. The generated eye, crest, face,
feathers, raised wing, background, and body never enter the accepted frame.

The accepted receipt records connected-mandible ratio `1.0`, changed bounding
box `(477, 246)-(540, 263)`, mandible bounding box
`(477, 244)-(540, 263)`, and hinge `(480, 250)`. The strict audit reports 843
changed rendered pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `0.999939`.

Accepted pair 62 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-062-rebuilt-2026-08-05/`

The current queue contains 60 fresh internal passes, 4 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 63 is the next isolated review gate.

Pair 63 (`read a panel`) failed its fresh isolated review and was rebuilt as
one closed/open pair. The rejected speaking frame read as a short, outlined
blade placed over the canonical bill; its lower tip ended behind the upper tip
and the light border made the articulation look detached in playback.

Rejected pair 63 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-063-rejected-misaligned-2026-08-05/`

The accepted successor was generated from Pair 63's own isolated head. The
deterministic compositor transfers only one full-length lower mandible and its
bounded cavity, leaving the canonical upper bill, crest, eye, cheek, throat,
hoodie, body, stance, canvas, and registration unchanged. The lower tip now
lands directly beneath the upper tip with no floating edge or halo.

The accepted receipt records connected-mandible ratio `1.0`, changed bounding
box `(503, 207)-(598, 255)`, mandible bounding box
`(503, 205)-(598, 255)`, and hinge `(509, 214)`. The strict audit reports
1,498 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.996981`.

Accepted pair 63 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-063-rebuilt-2026-08-05/`

The current queue contains 61 fresh internal passes, 3 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 64 is the next isolated review gate.

Pair 64 (`study a diagram`) failed its fresh isolated review and was rebuilt
as one closed/open pair. The rejected speaking frame kept its rear hinge but
ended the lower bill well behind the canonical upper tip; it also exposed
stacked light and dark edges that read as a detached second beak during
alternating playback.

Rejected pair 64 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-064-rejected-misaligned-2026-08-05/`

The accepted successor was generated from Pair 64's own isolated head. The
deterministic compositor transfers only one full-length lower mandible and its
bounded oral cavity over the immutable resting frame. The lower bill now
rotates from the authored hinge and meets the upper-beak tip without a floating
edge, duplicated outline, throat replacement, registration drift, or body
change.

The accepted receipt records connected-mandible ratio `1.0`, changed bounding
box `(392, 209)-(515, 268)`, mandible bounding box
`(392, 207)-(515, 268)`, and hinge `(398, 216)`. The strict audit reports
2,989 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.998027`.

Accepted pair 64 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-064-rebuilt-2026-08-05/`

The current queue contains 62 fresh internal passes, 2 pending pairs, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 65 is the next isolated review gate.

Pair 65 (`write or tap`) failed its fresh isolated review and was rebuilt as
one closed/open pair. The rejected speaking mate remained connected at the
rear hinge, but its narrow lower bill stopped visibly behind the canonical
upper tip. At native focus it read as a short secondary blade rather than the
lower half of one articulated kingfisher beak.

Rejected pair 65 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-065-rejected-short-mandible-2026-08-05/`

The accepted successor was generated from Pair 65's own isolated closed head.
The deterministic compositor transfers only one tapered lower mandible and a
bounded warm oral cavity. The resting frame remains the sole owner of the
upper bill, eye, crest, cheek, throat, hoodie, writing wing, body, feet,
canvas, and registration. The lower bill now opens from the authored hinge and
reaches the upper-tip line while remaining readable at full-character scale.

The accepted receipt records connected-mandible ratio `1.0`, changed bounding
box `(552, 240)-(620, 357)`, mandible bounding box
`(552, 240)-(620, 357)`, and hinge `(560, 254)`. The strict audit reports
2,761 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.994563`.

Accepted pair 65 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-065-rebuilt-2026-08-05/`

The current queue contains 63 fresh internal passes, 1 pending pair, and 2
rear views marked not observable. User approval and runtime admission remain
zero; Pair 66 is the final isolated review gate.

Pair 66 (`select a control`) failed its fresh isolated review and was rebuilt
as one closed/open pair. The rejected speaking mate kept a plausible hinge but
ended its lower point behind the canonical upper point and retained a visible
stacked edge in the native beak view.

Rejected pair 66 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-066-rejected-short-mandible-2026-08-05/`

The accepted successor was generated from Pair 66's own isolated closed head.
The deterministic compositor transfers only one full-length lower mandible and
its bounded oral cavity. The canonical resting frame remains the sole owner of
the upper bill, eye, crest, cheek, throat, hoodie, raised control wing, body,
feet, canvas, and registration. The new lower bill opens from the authored
hinge and meets the upper-tip line without a detached edge or imported body
pixels.

The accepted receipt records connected-mandible ratio `1.0`, changed bounding
box `(435, 224)-(552, 270)`, mandible bounding box
`(435, 224)-(552, 270)`, and hinge `(441, 230)`. The strict audit reports
1,824 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.995926`.

Accepted pair 66 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-066-rebuilt-2026-08-05/`

The fresh pairwise queue is complete: 64 observable pairs have internal visual
passes, 2 exact rear views are marked not observable, and no pairs remain
pending or marked for rebuild. The compiled review artifact contains all 176
poses and a 132-frame closed/open review sequence. The review verifier passes;
user approval and runtime admission remain explicitly zero.

## 2026-08-05 user visual recheck and strict pair reset

Sequence playback exposed additional visibly misaligned beaks after the prior
internal pass had reached all 64 observable pairs. The failure mode is now
explicit: registration, silhouette, and outside-mouth stability checks can all
pass while the lower mandible is still anatomically misaligned inside the
allowed articulation region. The prior numeric and visual dispositions are
therefore evidence, not authority.

All 64 observable pairs were returned to `pending` with their earlier reviews
preserved in `pairwise_full_size_review_history`. The two exact rear views
remain `not_observable`. Runtime admission and user approval remain false.

The replacement workflow advances exactly one closed/open pair at a time:

1. The closed frame is the immutable authority for the body, head, eyes,
   throat, and complete upper bill.
2. A speaking candidate may contribute only one connected lower mandible and
   its bounded oral cavity.
3. Closed and open frames are inspected at native size, locked side by side,
   in alternating playback, and with the upper bill and hinge visually
   overlaid.
4. A candidate is rejected for any upper-bill shift, hinge slide, duplicate
   edge, detached mandible, throat seam, head movement, scale change, or canvas
   movement even when the numeric audit reports a pass.
5. The next pair does not begin until the current pair has a preserved rejected
   candidate when applicable, accepted evidence, and a new pairwise ledger
   disposition.

Pair 1 (`neutral-front`) is the first pair rechecked under this stricter loop.
A fresh generated candidate was rejected because constraining its donor back
onto the canonical frame left a gray seam and insufficient mouth aperture.
The existing open mate remains the accepted internal candidate: its bilateral
hinge is centered, the lower mandible is connected, and all pixels outside the
bounded articulation remain stable. This disposition does not imply user
approval or runtime admission.

Accepted Pair 1 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-001-one-pair-2026-08-05-v1/`

The corrected queue now contains 1 strict internal pass, 63 pending observable
pairs, and 2 exact rear views marked not observable. Pair 2 is the next and
only active art-generation and review unit.

## 2026-08-05 anatomy-specific admission gate

The user recheck also established that exact body registration is necessary
but insufficient. A speaking mate can preserve every pixel outside its mouth
region and still present a lower bill on the wrong axis. The pair-specific
compositor and compiler therefore now evaluate the declared upper-bill,
mandible, cavity, and hinge geometry before a new full-size pass can compile.

Beginning with Pair 2, every observable pass must prove:

- upper bill, lower mandible, and cavity share the declared hinge region;
- a profile or three-quarter mandible extends in the same longitudinal
  direction as the canonical upper bill;
- lower-bill length remains within a bounded ratio of the upper bill;
- the lower tip remains within a bounded perpendicular offset of the upper
  tip; or
- a frontal lower bill remains centered, plausibly wide, and below the upper
  bill.

New compositor receipts retain these measurements as `beak_anatomy`. The
compiler recomputes them from the primitive geometry instead of trusting a
stored pass flag. Pair 1 is the explicit reviewed template and remains the
only exception because its original local-articulation receipt predates the
pair-specific polygon contract.

Pair 2 remains pending. Its current candidate passes the new geometric screen
with a shared right-facing axis, `0.7857` mandible-to-upper length ratio,
`0.2902` normalized tip offset, and hinge distances below 3 pixels. Those
measurements qualify it only for the locked full-size visual review; they do
not create an internal pass, user approval, or runtime admission.

Focused verification after this change: 45 Kingfisher review tests pass. The
compiled review library still contains 176 review-only poses, and the final
verifier intentionally stops at Pair 2 with 1 pass, 63 pending pairs, and 2
not-observable rear views.

Pair 2 (`front-three-quarter-left`) then completed the tightened one-pair
review. The current open mate was inspected independently on transparency and
the deterministic white projector. The closed frame remains the authority for
the upper bill, eye, crown, cheek, throat, hoodie, body, stance, registration,
and canvas. The open mate contributes one connected lower mandible that shares
the rear hinge, follows the authored right-facing axis, and reaches beneath
the upper tip without a doubled edge or throat seam.

Its recomputed anatomy measurements report a `0.7857` lower-to-upper bill
length ratio, `0.2902` normalized tip offset, and upper, lower, and cavity hinge
distances below 3 pixels. The body-lock audit remains exact outside the mouth
region. The evidence is retained at:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-002-one-pair-2026-08-05-v1/`

The queue now contains 2 strict internal passes, 62 pending observable pairs,
and 2 not-observable rear views. The verifier intentionally stops at Pair 3;
user approval and runtime admission remain zero.

Pair 3 (`left-profile`) was rebuilt and reviewed as its own closed/open unit
rather than carried forward from the earlier batch. The closed ACT003 frame is
the immutable source for the body, head, eye, throat, and complete upper bill.
The prior speaking mate is used only as a lower-mandible donor inside declared
pair-specific masks.

The resulting lower bill joins rear hinge `(420, 234)`, follows the canonical
left-facing bill axis, and ends behind the upper tip. Recomputed anatomy reports
a `0.7658` mandible-to-upper length ratio, `0.3288` normalized tip offset, and
zero-distance upper, lower, and cavity hinge attachment. The strict image audit
reports 861 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.993`.

Fresh Pair 3 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-003-one-pair-2026-08-05-v2/`

The queue now contains 3 strict internal passes, 61 pending observable pairs,
and 2 not-observable rear views. The verifier intentionally advances to Pair 6,
the next observable pose; user approval and runtime admission remain zero.

Pair 6 (`right-profile`) was also rebuilt as one isolated pair. ACT006 remains
the immutable source for the body, head, eye, throat, and complete upper bill;
the earlier speaking mate contributes only the connected lower mandible and
bounded cavity inside the pair-specific masks.

The accepted lower bill joins rear hinge `(537, 246)`, follows the canonical
right-facing axis, and ends behind the upper tip. Its geometry reports a
`0.7611` lower-to-upper bill length ratio, `0.4513` normalized tip offset, and
1-pixel upper, lower, and cavity hinge distances. The strict image audit
reports 1,045 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and
silhouette IoU `0.988776`.

Fresh Pair 6 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-006-one-pair-2026-08-05-v2/`

The queue now contains 4 strict internal passes, 60 pending observable pairs,
and 2 not-observable rear views. Pair 7 is the next isolated review gate; user
approval and runtime admission remain zero.

Pair 7 (`front-three-quarter-right`) exposed a receipt defect rather than a
pixel defect. Its prior accepted frame looked coherent, but the declared upper
bill polygon missed the hinge by `14.364` pixels and therefore failed the new
anatomy gate. The pair was recomposed from its own closed frame and accepted
lower-bill donor with a corrected shared-hinge declaration. The output hash is
identical to the prior accepted speaking image, proving that the visual pixels
were preserved while the invalid geometry contract was replaced.

The corrected receipt places hinge `(449, 253)` on the immutable upper bill and
connected lower mandible. Recomputed anatomy reports a `0.6476`
mandible-to-upper length ratio, `0.519` normalized tip offset, upper hinge
distance `0.0`, lower hinge distance `2.121`, and cavity hinge distance `1.857`.
The strict image audit remains outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `0.99996`.

Fresh Pair 7 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-007-one-pair-2026-08-05-v2/`

The queue now contains 5 strict internal passes, 59 pending observable pairs,
and 2 not-observable rear views. Pair 8 is the next isolated gate; user approval
and runtime admission remain zero.

Pair 8 (`relaxed-idle`) passed a fresh isolated native-size, enlarged, and
full-projector review without requiring new art. Its existing pair-specific
lower mandible remains restrained for the relaxed pose, joins hinge `(439,
250)`, and follows the canonical left-facing upper-bill axis without a doubled
edge, throat seam, head shift, or scale change.

The compiler recomputes a `0.9302` mandible-to-upper length ratio, `0.3953`
normalized tip offset, and passing upper, lower, and cavity hinge attachment.
The strict image audit remains outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `0.995701`.

Fresh Pair 8 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-008-one-pair-2026-08-05-v2/`

The queue now contains 6 strict internal passes, 58 pending observable pairs,
and 2 not-observable rear views. Pair 9 is the next isolated gate; user approval
and runtime admission remain zero.

Pair 9 (`attentive-idle`) passed a fresh isolated native-size, enlarged-beak,
and full-projector review without changing its existing pair-specific art. The
open lower bill remains centered beneath the frontal upper bill, both mouth
corners share the declared hinge region, and the head, eyes, throat, hoodie,
body, stance, canvas, and registration remain sourced from the immutable
closed frame.

The original receipt used an obsolete `0.65` connectivity threshold. The same
pixels were deterministically recomposed from the closed frame and existing
lower-bill donor under the current `0.8` minimum; the candidate SHA-256 stayed
identical. The corrected receipt records hinge `(459, 230)`, right-facing
direction, a `0.9286` mandible-to-upper length ratio, and `0.1786` normalized
tip offset. Its strict audit remains outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 9 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-009-one-pair-2026-08-05-v2/`

The queue now contains 7 strict internal passes, 57 pending observable pairs,
and 2 not-observable rear views. Pair 10 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 10 (`ready-stance`) passed its isolated native-size, enlarged-beak, and
full-projector review. The accepted open mate is the compact centered version;
the wider legacy alternative remains rejected because it pulls the lower bill
away from the frontal axis. The closed ACT010 frame remains authoritative for
the upper bill, head, eyes, throat, hoodie, wings, body, feet, scale, and canvas.

The exact accepted pixels were deterministically recomposed under the current
`0.8` connectivity minimum and retained the same SHA-256 as the prior compact
candidate. The corrected receipt records hinge `(449, 244)`, right-facing
direction, a `0.8395` mandible-to-upper length ratio, and `0.4938` normalized
tip offset. Its strict audit reports 1,537 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh Pair 10 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-010-one-pair-2026-08-05-v2/`

The queue now contains 8 strict internal passes, 56 pending observable pairs,
and 2 not-observable rear views. Pair 11 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 11 (`neutral-speaking-gesture`) passed its isolated native-size,
enlarged-candidate, and full-projector review. The accepted v2 mate keeps the
open V centered under the frontal upper bill and preserves both mouth corners.
The broader v1 and right-drifting or clipped v3-v5 alternatives remain
rejected. The repaired closed ACT011 frame remains authoritative for the upper
bill, eyes, head, throat, raised presentation wing, clothing, body, feet,
scale, and canvas.

The exact accepted pixels were deterministically recomposed under the current
`0.8` connectivity minimum and retained their prior SHA-256. The corrected
receipt records hinge `(493, 237)`, right-facing direction, a `0.875`
mandible-to-upper length ratio, and `0.5` normalized tip offset. Its strict
audit reports 4,091 changed rendered pixels, outside-mouth mean difference
`0.0`, registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 11 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-011-one-pair-2026-08-05-v2/`

The queue now contains 9 strict internal passes, 55 pending observable pairs,
and 2 not-observable rear views. Pair 12 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 12 (`explain-one-point`) passed its isolated native-size, enlarged-pair,
and full-projector review. The accepted v1 mate retains a centered V-shaped
opening beneath the frontal upper bill, keeps both hinge corners attached, and
does not disturb the eyes, crown, throat, raised pointing wing, hoodie, body,
feet, scale, or canvas inherited from the closed ACT012 frame.

The exact accepted pixels were deterministically regenerated under the current
`0.8` connectivity minimum and retained the existing SHA-256. The measured
connected-mandible ratio is `0.81237`, so this pair passes narrowly but
truthfully. The corrected receipt also records hinge `(486, 235)`, right-facing
direction, a `0.828` mandible-to-upper length ratio, and `0.5699` normalized
tip offset. Its strict audit reports 2,768 changed rendered pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh Pair 12 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-012-one-pair-2026-08-05-v2/`

The queue now contains 10 strict internal passes, 54 pending observable pairs,
and 2 not-observable rear views. Pair 13 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 13 (`balance-two-ideas`) passed its isolated native-size, enlarged-beak,
and full-projector review. The apparent defect was in the inherited review
model rather than the rendered pixels: the old receipt treated this frontal
pose as right-facing and measured it from a false left-side hinge. Direct
comparison showed the existing open mate is centered correctly; experimental
offsets of -6, -10, -14, and -22 pixels all pulled the lower bill visibly left
and were rejected.

The accepted v3 receipt preserves the existing visible result while recording
the true frontal centerline at hinge `(485, 229)`. It reports a `0.0312`
normalized center offset, `0.9875` mandible-to-upper width ratio, both mouth
corners anchored, and a connected-mandible ratio of `1.0`. Its strict audit
reports 3,667 changed rendered pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 13 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-013-one-pair-2026-08-05-v2/`

The queue now contains 11 strict internal passes, 53 pending observable pairs,
and 2 not-observable rear views. Pair 14 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 14 (`present-screen-left`) passed its isolated native-size,
enlarged-beak, and full-projector review. Candidate v8 deterministically
reproduces the visually selected v6 pixels exactly from the preserved donor
under the current `0.8` connectivity minimum. Earlier v1-v5 variants remain
rejected because they clip the upper bill, leave a black residual wedge, or
exaggerate the gape.

The accepted left-facing lower bill opens from the rear hinge without moving
the upper bill, eye, crown, throat, presenting wing, hoodie, body, feet, scale,
or canvas. The corrected receipt records hinge `(538, 213)`, a `1.1075`
mandible-to-upper reach ratio, `0.2634` normalized tip offset, and `0.999499`
connected-mandible ratio. Its strict audit reports 2,331 changed rendered
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `0.993514`.

Fresh Pair 14 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-014-one-pair-2026-08-05-v2/`

The queue now contains 12 strict internal passes, 52 pending observable pairs,
and 2 not-observable rear views. Pair 15 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 15 (`present-screen-right`) passed its isolated native-size,
enlarged-beak, and full-projector review. Candidate v2 deterministically
reproduces the accepted v1 pixels exactly from the preserved pre-pairwise
donor while adding current right-facing anatomy evidence.

The lower bill remains connected at the rear hinge and follows the upper
bill's perspective without moving the eye, crown, throat, raised presentation
wing, hoodie, body, feet, scale, or canvas. The corrected receipt records hinge
`(402, 222)`, a `0.864` mandible-to-upper reach ratio, `0.308` normalized tip
offset, and connected-mandible ratio `1.0`. Its strict audit reports 974
changed rendered pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `0.99476`.

Fresh Pair 15 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-015-one-pair-2026-08-05-v2/`

The queue now contains 13 strict internal passes, 51 pending observable pairs,
and 2 not-observable rear views. Pair 16 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 16 (`point-to-viewer`) passed its isolated native-size, enlarged-beak,
and full-projector review. Candidate v2 deterministically reproduces the
accepted compact v1 pixels exactly from the preserved pre-pairwise donor while
adding current frontal anatomy evidence. The rejected prior gape remains
excluded because it was oversized vertically for this direct-address gesture.

The accepted opening remains centered beneath the immutable frontal upper bill
without moving the eyes, crown, throat, pointing wing, hoodie, body, feet,
scale, or canvas. The corrected receipt records hinge `(480, 228)`, normalized
center offset `0.0`, a `0.8871` mandible-to-upper width ratio, and
connected-mandible ratio `1.0`. Its strict audit reports 4,470 changed rendered
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 16 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-016-one-pair-2026-08-05-v2/`

The queue now contains 14 strict internal passes, 50 pending observable pairs,
and 2 not-observable rear views. Pair 17 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 17 (`insight-upward-point`) passed its isolated native-size,
enlarged-beak, and full-projector review. Candidate v2 deterministically
reproduces the restrained accepted v1 pixels exactly from the preserved
pre-pairwise donor under the current directional anatomy checker. The
oversized donor wedge remains excluded.

The lower bill opens from the rear hinge on the same left-facing axis as the
immutable upper bill without moving the eye, crown, throat, raised insight
wing, hoodie, body, feet, scale, or canvas. The corrected receipt records hinge
`(543, 221)`, mandible anchor distance `4.438`, a `0.9524`
mandible-to-upper reach ratio, `0.4286` normalized tip offset, and
connected-mandible ratio `0.999438`. Its strict audit reports 1,081 changed
rendered pixels, outside-mouth mean difference `0.0`, registration delta `0`,
and silhouette IoU `0.995961`.

Fresh Pair 17 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-017-one-pair-2026-08-05-v2/`

The queue now contains 15 strict internal passes, 49 pending observable pairs,
and 2 not-observable rear views. Pair 18 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 18 (`detail-downward-point`) passed its isolated native-size,
enlarged-beak, and full-projector review. Candidate v3 deterministically
reproduces the selected v2 pixels exactly from the preserved pre-pairwise donor
under the current directional anatomy checker. Candidate v1 remains rejected
because its short pink tip reads detached at enlarged scale, and the donor
remains rejected because its gape is oversized.

The accepted lower bill and cavity stay continuous to the rear hinge on the
same downward-left axis as the immutable upper bill without moving the eye,
crown, throat, downward-pointing wing, hoodie, body, feet, scale, or canvas.
The corrected receipt records hinge `(525, 249)`, mandible anchor distance
`16.153`, a `0.9697` mandible-to-upper reach ratio, `0.2652` normalized tip
offset, and connected-mandible ratio `1.0`. Its strict audit reports 4,186
changed rendered pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `0.999987`.

Fresh Pair 18 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-018-one-pair-2026-08-05-v2/`

The queue now contains 16 strict internal passes, 48 pending observable pairs,
and 2 not-observable rear views. Pair 19 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 19 (`neutral-listening`) passed its isolated native-size, enlarged-beak,
and full-projector review. Candidate v2 deterministically reproduces the
restrained accepted v1 pixels exactly from the preserved pre-pairwise donor
under the current directional anatomy checker. The oversized donor gape
remains excluded.

The lower bill opens from the left rear hinge on the same right-facing axis as
the immutable upper bill without moving the eyes, crown, throat, folded wings,
hoodie, body, feet, scale, or canvas. The restrained aperture remains
appropriate to neutral listening while still reading at projector scale. The
corrected receipt records hinge `(466, 252)`, mandible anchor distance
`10.221`, a `0.9746` mandible-to-upper reach ratio, `0.2966` normalized tip
offset, and connected-mandible ratio `1.0`. Its strict audit reports 4,146
changed rendered pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `1.0`.

Fresh Pair 19 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-019-one-pair-2026-08-05-v2/`

The queue now contains 17 strict internal passes, 47 pending observable pairs,
and 2 not-observable rear views. Pair 20 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 20 (`lean-in-listening`) passed its isolated native-size, enlarged-beak,
and full-projector review. Candidate v4 deterministically reproduces the
selected restrained v2 pixels exactly from the preserved pre-pairwise donor
under the current directional anatomy checker. Candidate v1 remains excluded
because its aperture is too close to the resting frame at projector scale;
candidate v3 and the rejected donor remain excluded because their broad gape
overstates the quiet listening performance.

The accepted lower bill opens from the left rear hinge on the same right-facing
axis as the immutable upper bill without moving the eyes, crown, throat, folded
wings, hoodie, body, feet, scale, or canvas. The corrected receipt records hinge
`(497, 267)`, mandible anchor distance `17.975`, a `0.9612`
mandible-to-upper reach ratio, `0.0291` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 5,469 changed rendered
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 20 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-020-one-pair-2026-08-05-v2/`

The queue now contains 18 strict internal passes, 46 pending observable pairs,
and 2 not-observable rear views. Pair 21 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 21 (`skeptical-listening`) passed its isolated native-size,
enlarged-beak, tight-tip, and full-projector review after a new silhouette
repair. The previous mate and candidate v2 retained a pale resting-edge
fragment behind the opened tip. Candidate v3 removed light-neutral donor
pixels but left that canonical silhouette residue, while candidate v4 left
small residual flecks. Candidate v5 clears only the stale tip region before
repainting the connected donor mandible.

The repaired lower bill opens from the left rear hinge on the same right-facing
axis and ends behind the upper tip without moving the eye line, crown, cheek,
throat, folded wing, hoodie, body, feet, scale, or canvas. The corrected receipt
records hinge `(452, 250)`, mandible anchor distance `5.0`, a `0.9612`
mandible-to-upper reach ratio, `0.3178` normalized tip offset, and
connected-mandible ratio `0.995983`. Its strict audit reports 4,640 changed
rendered pixels, outside-mouth mean difference `0.0`, registration delta `0`,
and silhouette IoU `0.998056`.

Fresh Pair 21 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-021-one-pair-2026-08-05-v2/`

The queue now contains 19 strict internal passes, 45 pending observable pairs,
and 2 not-observable rear views. Pair 22 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 22 (`small-acknowledgment`) passed its isolated native-size,
enlarged-beak, tight-tip, and full-projector review after removing a duplicate
interior contour. The prior admitted-looking mate and exact candidate v4
verification repainted donor cavity pixels after restoring the canonical upper
bill, creating a dark third edge. Candidate v5 keeps the same connected donor
mandible and immutable upper-bill geometry but omits that second cavity
overlay. Candidate v6 proves a solid cavity suppresses all donor contours, but
remains rejected because its broad black polygon reads as an artificial slab.

The selected lower bill shares the visible left rear hinge, follows the upper
bill on the same right-facing axis, and ends behind the upper tip. Its
restrained opening suits a small acknowledgment without moving the eye line,
crown, cheek, throat, folded wings, hoodie, body, feet, scale, or canvas. The
corrected receipt records hinge `(462, 266)`, upper anchor distance `11.0`,
mandible anchor distance `7.0`, cavity anchor distance `5.0`, a `0.9412`
mandible-to-upper reach ratio, `0.3934` normalized tip offset, and
connected-mandible ratio `0.97903`. Its strict audit reports 3,063 changed
rendered pixels, outside-mouth mean difference `0.0`, registration delta `0`,
and silhouette IoU `0.999766`.

Fresh Pair 22 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-022-one-pair-2026-08-05-v2/`

The queue now contains 20 strict internal passes, 44 pending observable pairs,
and 2 not-observable rear views. Pair 23 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 23 (`emphatic-agreement`) passed its isolated native-size,
enlarged-beak, tight-tip, and full-projector review without changing the image
pixels. Candidate v4 reproduces the existing speaking mate exactly from the
preserved pair-specific v3 donor under the current directional anatomy
checker. The larger aperture remains intentional for the emphatic performance,
but is now supported by current pair-level evidence instead of an inherited
batch disposition.

One connected lower mandible opens from the visible left rear hinge, follows
the immutable upper bill on the same right-facing axis, and ends beneath its
tip without a lateral jump, duplicate edge, or detached sliver. Crown, eyes,
cheek plates, throat, raised wings, hoodie, body, feet, scale, and canvas remain
unchanged. The upgraded receipt records hinge `(462, 280)`, upper anchor
distance `10.0`, mandible anchor distance `12.0`, cavity anchor distance `4.0`,
a `0.9248` mandible-to-upper reach ratio, `0.0113` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 8,881 changed rendered
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 23 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-023-one-pair-2026-08-05-v2/`

The queue now contains 21 strict internal passes, 43 pending observable pairs,
and 2 not-observable rear views. Pair 24 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 24 (`polite-interruption`) passed its isolated native-size,
enlarged-beak, tight-tip, and full-projector review without changing the image
pixels. Candidate v7 reproduces the selected donor-v6 speaking mate exactly
from the preserved pair-specific v3 render under the current directional
anatomy checker. Rejected v3 retains a rectangular donor patch, while rejected
v4 and donor v5 read as broad artificial black slabs; all remain excluded.

The selected modest diagonal lower bill shares the visible left rear hinge,
follows the immutable upper bill on the same right-facing axis, and terminates
beneath its tip. At projector scale it supports a polite interruption without
reading as detached. Eyes, crown, cheek, throat, raised signaling wing, hoodie,
body, feet, scale, and canvas remain unchanged. The upgraded receipt records
hinge `(470, 220)`, upper anchor distance `9.0`, mandible anchor distance
`4.0`, cavity anchor distance `1.0`, a `0.8102` mandible-to-upper reach ratio,
`0.4927` normalized tip offset, and connected-mandible ratio `1.0`. Its strict
audit reports 3,576 changed rendered pixels, outside-mouth mean difference
`0.0`, registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 24 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-024-one-pair-2026-08-05-v2/`

The queue now contains 22 strict internal passes, 42 pending observable pairs,
and 2 not-observable rear views. Pair 25 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 25 (`hand-over-the-floor`) passed its isolated native-size,
enlarged-beak, tight-tip, and full-projector review. Candidate v6 reproduces
the accepted tip-aligned v5 pixels exactly from the preserved pair-specific v2
donor under the current directional anatomy checker. The rejected
short-mandible frame stops mid-bill, rejected v2 contains displaced donor
content, and candidates v3/v4 retain shorter tips; all remain excluded.

The selected connected lower bill uses the authored left rear hinge, follows
the immutable upper bill on the same right-facing profile axis, and reaches
beneath its tip without a duplicate edge or detached sliver. Eye, crown,
cheek, throat, hoodie, body, feet, scale, canvas, and extended
hand-over-the-floor wing remain unchanged. The upgraded receipt records hinge
`(365, 220)`, upper anchor distance `4.0`, mandible anchor distance `4.509`,
cavity anchor distance `2.0`, a `0.9667` mandible-to-upper reach ratio,
`0.5067` normalized tip offset, and connected-mandible ratio `0.999583`. Its
strict audit reports 2,380 changed rendered pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `0.996829`.

Fresh Pair 25 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-025-one-pair-2026-08-05-v2/`

The queue now contains 23 strict internal passes, 41 pending observable pairs,
and 2 not-observable rear views. Pair 26 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 26 (`warm-welcome`) passed its isolated native-size, enlarged-beak,
tight-tip, and full-projector review. Candidate v5 reproduces the selected v4
speaking mate exactly from the preserved pair-specific v2 donor under the
current anatomy checker. The older double-mouth render retains the closed
throat contour beneath a second opening, candidate v3 carries a pale neutral
triangle below the lower bill, and the orange-interior render is unusable;
all remain excluded.

The selected speaking frame has one centered oral cavity and one connected
lower mandible. It opens from the authored frontal hinge, remains aligned
between the eyes and throat, and leaves the crown, eyes, cheeks, upper bill,
white throat, hoodie, wings, body, feet, scale, and canvas unchanged. The
verified frame retains SHA-256
`a3f95639a5b376d2095c7cbaf28ee4547617821e6ff6faf974298bcf7ad9ab61`.
The upgraded receipt records hinge `(466, 214)`, upper anchor distance
`7.891`, mandible anchor distance `2.824`, cavity anchor distance `1.622`, a
`0.8667` mandible-to-upper reach ratio, `0.05` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 646 changed
articulation pixels, 0 outside-region pixels, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 26 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-026-one-pair-2026-08-05-v2/`

The queue now contains 24 strict internal passes, 40 pending observable pairs,
and 2 not-observable rear views. Pair 27 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 27 (`intimate-confidence`) passed its isolated native-size,
enlarged-beak, tight-tip, and full-projector review. Candidate v5 reproduces
the selected v4 speaking mate exactly from the preserved pair-specific v2
donor under the current directional anatomy checker. The rejected earlier
frame leaves a dark hook across the screen-right white throat; candidate v3
and v4 remove that residue, and only the exact v4/v5 result is selected.

The restrained lower bill opens along the tilted head's left-facing axis from
the authored screen-right rear hinge. One connected mandible and one oral
cavity remain attached to the immutable upper bill without a duplicate edge,
detached sliver, lateral jump, or throat redraw. The selected frame retains
SHA-256
`d0327018802fa843e84fff77fd3581726bcc5b085c4a8442bdd4f5b7d05bc969`.
The upgraded receipt records hinge `(497, 263)`, upper anchor distance
`2.928`, mandible anchor distance `4.241`, cavity anchor distance `1.177`, a
`0.7313` mandible-to-upper reach ratio, `0.3731` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 998 changed rendered
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 27 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-027-one-pair-2026-08-05-v2/`

The queue now contains 25 strict internal passes, 39 pending observable pairs,
and 2 not-observable rear views. Pair 28 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 28 (`strong-declaration`) passed its isolated native-size,
enlarged-beak, tight-tip, and full-projector review. Candidate v5 reproduces
the selected v4 speaking mate exactly from the preserved pair-specific v2
donor under the current anatomy checker. Candidate v3 pastes white throat
feathers into a second dark mouth region, while the earlier rejected frame
leaves a detached smile below an otherwise closed bill; both remain excluded.

The selected broad declaration aperture is centered beneath the immutable
upper bill, with both rear corners attached to the same face geometry. One
connected lower mandible and one contained oral cavity support the forceful
raised-wing gesture without moving the eyes, crown, cheeks, throat, hoodie,
body, feet, scale, or canvas. The frame retains SHA-256
`a0972eee897e0a2a9811fe79c0352f827ca3ca3d659f11ae6739fa8d5c4d42ee`.
The upgraded receipt records hinge `(539, 222)`, upper anchor distance
`0.686`, mandible anchor distance `3.531`, cavity anchor distance `0.588`, a
`1.0513` mandible-to-upper reach ratio, `0.1026` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 887 changed rendered
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 28 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-028-one-pair-2026-08-05-v2/`

The queue now contains 26 strict internal passes, 38 pending observable pairs,
and 2 not-observable rear views. Pair 29 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 29 (`confidential-whisper`) passed its isolated native-size,
enlarged-beak, tight-tip, and full-projector review after correcting stale
receipt anatomy. Candidate v18 reproduces selected v17 pixels exactly from the
pair-specific v11 donor. Candidate v15 leaves a detached black bar across the
white throat, while v16 still reads as a misplaced lower strip; both remain
excluded.

The old receipt initially failed the current `bounded_tip_offset` gate because
its upper-bill polygon labeled a high cheek corner as the left-facing bill tip.
The corrected polygon follows the actual diagonal upper bill without changing
the rendered image. The selected lower mandible remains behind the foreground
wing, shares the true screen-right rear hinge, and creates a subtle whisper
opening without a throat-crossing bar, duplicate edge, or body drift. The
frame retains SHA-256
`3492430e974c6c8430a8aa59d5a1146f5751e2f035dc5df745ca8535eb4e3567`.
The upgraded receipt records hinge `(493, 261)`, upper anchor distance
`8.544`, mandible anchor distance `7.805`, cavity anchor distance `4.31`, a
`0.957` mandible-to-upper reach ratio, `0.1075` normalized tip offset, and
connected-mandible ratio `0.991361`. Its strict audit reports 2,106 changed
mouth pixels, outside-mouth mean difference `0.0`, registration delta `0`,
and silhouette IoU `1.0`.

Fresh Pair 29 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-029-one-pair-2026-08-05-v2/`

The queue now contains 27 strict internal passes, 37 pending observable pairs,
and 2 not-observable rear views. Pair 30 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 30 (`rhetorical-question`) passed its isolated native-size,
enlarged-beak, and full-projector review. Candidate v3 reproduces the selected
v2 speaking pixels exactly while upgrading the receipt to the current
directional anatomy contract. The immutable closed frame, eyes, crown, cheeks,
white throat, hoodie, raised wings, feet, canvas, and registration are
unchanged.

The centered lower mandible opens beneath the immutable upper bill with both
rear corners attached to the authored face geometry. One contained oral cavity
supports the rhetorical-question expression without a duplicate upper edge,
detached lower strip, throat patch, or lateral tip jump. The selected frame
retains SHA-256
`d203e24d38464fc5619fe3260ef7f92fb881bc00b2f7d900242ae12a032da39e`.
The upgraded receipt records hinge `(510, 164)`, upper anchor distance
`10.406`, mandible anchor distance `17.889`, cavity anchor distance `10.391`,
a `1.05` mandible-to-upper reach ratio, `0.4` normalized tip offset, and
connected-mandible ratio `0.995298`. Its strict audit reports 4,379 changed
mouth pixels, outside-mouth mean difference `0.0`, registration delta `0`,
and silhouette IoU `1.0`.

Fresh Pair 30 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-030-one-pair-2026-08-05-v1/`

The queue now contains 28 strict internal passes, 36 pending observable pairs,
and 2 not-observable rear views. Pair 31 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 31 (`compare-two-options`) passed its isolated native-size,
enlarged-beak, and full-projector review. Candidate v5 reproduces the selected
v4 speaking pixels exactly while upgrading the pair to the current directional
anatomy receipt. The right-facing closed frame, eye, crown, cheek, throat,
hoodie, opposed wing gesture, feet, scale, canvas, and registration remain
unchanged.

The lower mandible opens toward screen right from the authored screen-left rear
hinge. It stays beneath the immutable upper bill with one connected lower edge
and one contained cavity; there is no detached strip, duplicate bill, throat
residue, or sideways tip displacement. The selected frame retains SHA-256
`206e7b46bca5e33a50a9bf03a864d936bfac572d970b1567567d2fa3b74d4dd1`.
The upgraded receipt records hinge `(484, 222)`, upper anchor distance `1.729`,
mandible anchor distance `2.683`, cavity anchor distance `2.095`, a `0.6207`
mandible-to-upper reach ratio, `0.1724` normalized tip offset, and
connected-mandible ratio `0.999383`. Its strict audit reports 1,330 changed
mouth pixels, outside-mouth mean difference `0.0`, registration delta `0`,
and silhouette IoU `1.0`.

Fresh Pair 31 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-031-one-pair-2026-08-05-v1/`

The queue now contains 29 strict internal passes, 35 pending observable pairs,
and 2 not-observable rear views. Pair 32 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 32 (`cause-and-effect`) passed its isolated native-size,
enlarged-beak, and full-projector review. Candidate v9 reproduces the selected
v8 speaking pixels exactly while upgrading the pair to the current directional
anatomy receipt. The three-quarter right-facing closed frame, eyes, crown,
cheeks, white throat, hoodie, pointing wing gesture, feet, scale, canvas, and
registration remain unchanged.

The lower mandible opens toward screen right from the authored screen-left rear
hinge. It remains beneath the immutable upper bill with one connected lower
edge and one contained cavity; there is no detached strip, duplicate bill,
throat residue, or sideways tip displacement. The selected frame retains
SHA-256
`71b9ef6c47bd8d4716b4a874ab369b5d2d8e3d2300d0a4520eb1f1c133cb26b0`.
The upgraded receipt records hinge `(350, 219)`, upper anchor distance `0.348`,
mandible anchor distance `3.818`, cavity anchor distance `0.97`, a `0.8036`
mandible-to-upper reach ratio, `0.0893` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 1,862 changed mouth
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 32 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-032-one-pair-2026-08-05-v1/`

The queue now contains 30 strict internal passes, 34 pending observable pairs,
and 2 not-observable rear views. Pair 33 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 33 (`count-one`) passed its isolated native-size, enlarged-beak, and
full-projector review. Candidate v4 reproduces the selected v3 speaking pixels
exactly while upgrading the pair to the current directional anatomy receipt.
The right-facing closed frame, eye, crown, cheek, throat, hoodie, raised-wing
counting gesture, feet, scale, canvas, and registration remain unchanged.

The lower mandible opens toward screen right from the authored screen-left rear
hinge. It stays beneath the immutable upper bill with one connected lower edge
and one contained cavity; there is no detached strip, duplicate bill, throat
residue, or sideways tip displacement. The selected frame retains SHA-256
`6185e8add36517a0eb533fce296c6eca0aad2f353d0bd1824f29f447b3e354ae`.
The upgraded receipt records hinge `(437, 220)`, upper anchor distance `3.628`,
mandible anchor distance `5.082`, cavity anchor distance `4.187`, a `0.787`
mandible-to-upper reach ratio, `0.1111` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 944 changed mouth
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 33 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-033-one-pair-2026-08-05-v1/`

The queue now contains 31 strict internal passes, 33 pending observable pairs,
and 2 not-observable rear views. Pair 34 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 34 (`count-two`) passed its isolated native-size, enlarged-beak, and
full-projector review. Candidate v3 reproduces the selected v2 speaking pixels
exactly while upgrading the pair to the current directional anatomy receipt.
The shallow three-quarter closed frame, eyes, crown, cheeks, throat, hoodie,
bilateral raised-wing gesture, feet, scale, canvas, and registration remain
unchanged.

The lower mandible follows the authored bill toward screen right from the
screen-left rear hinge. It stays beneath the immutable upper bill with one
connected lower edge and one contained cavity; there is no detached strip,
duplicate bill, throat residue, or sideways tip displacement. The selected
frame retains SHA-256
`24dc3d34ba1cd02e0d4daa0871c605cae57373f0424a57a5f0a57e3808b32ff9`.
The upgraded receipt records hinge `(461, 174)`, upper anchor distance `2.324`,
mandible anchor distance `3.615`, cavity anchor distance `2.01`, a `0.8214`
mandible-to-upper reach ratio, `0.0952` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 913 changed mouth
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 34 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-034-one-pair-2026-08-05-v1/`

The queue now contains 32 strict internal passes, 32 pending observable pairs,
and 2 not-observable rear views. Pair 35 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 35 (`count-three`) passed its isolated native-size, enlarged-beak, and
full-projector review. Candidate v3 reproduces the selected v2 speaking pixels
exactly while upgrading the pair to the current anatomy receipt. The frontal
closed frame, eyes, crown, cheeks, white throat, hoodie, bilateral raised-wing
counting gesture, feet, scale, canvas, and registration remain unchanged.

The small opening remains centered beneath the immutable upper bill and reads
as one symmetric V-shaped mouth. It has one connected lower edge and a contained
cavity; there is no detached strip, duplicate bill, throat residue, or lateral
face drift. The selected frame retains SHA-256
`db7e40c7ed21af9fc670cca602fe0c317b92e5eaaa9e7f421b1e4aa50d844328`.
The upgraded receipt records hinge `(449, 166)`, upper anchor distance `5.618`,
mandible anchor distance `9.219`, cavity anchor distance `5.065`, a `0.8384`
mandible-to-upper reach ratio, `0.1869` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 2,146 changed mouth
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 35 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-035-one-pair-2026-08-05-v1/`

The queue now contains 33 strict internal passes, 31 pending observable pairs,
and 2 not-observable rear views. Pair 36 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 36 (`protective-boundary`) passed its isolated native-size,
enlarged-beak, and full-projector review. Candidate v4 reproduces the selected
v3 speaking pixels exactly while upgrading the pair to the current anatomy
receipt. The frontal closed frame, eyes, crown, cheeks, white throat, hoodie,
defensive raised-wing gesture, feet, scale, canvas, and registration remain
unchanged.

The restrained opening remains centered beneath the immutable upper bill. Its
lower edge stays connected through the rear hinge and the cavity remains
contained; there is no duplicate mouth, detached edge, throat import, or body
drift. The selected frame retains SHA-256
`c5b4671378abd15207cc5b4d988e87a6b9485492e046bc627e3a3d1f6a45956b`.
The upgraded receipt records hinge `(370, 225)`, upper anchor distance `6.877`,
mandible anchor distance `7.111`, cavity anchor distance `4.743`, a `0.8718`
mandible-to-upper reach ratio, `0.1795` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 1,878 changed mouth
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 36 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-036-one-pair-2026-08-05-v1/`

The queue now contains 34 strict internal passes, 30 pending observable pairs,
and 2 not-observable rear views. Pair 37 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 37 (`gentle-reassurance`) passed its isolated native-size,
enlarged-beak, and full-projector review. Candidate v16 reproduces the selected
v15 speaking pixels exactly while upgrading the pair to the current directional
anatomy receipt. The diagonal closed frame, eyes, crown, cheeks, throat,
hoodie, extended reassurance wing, feet, scale, canvas, and registration remain
unchanged.

The lower mandible follows the authored bill toward screen left from the
screen-right rear hinge. It remains beneath the immutable upper bill with one
connected lower edge and one contained cavity; there is no detached strip,
duplicate mouth, throat import, or lateral tip jump. The selected frame retains
SHA-256
`7a47f38d13a7dba02b4de1290095dcd01a511ba01de9a481c850167077a523f7`.
The upgraded receipt records hinge `(562, 235)`, upper anchor distance `2.078`,
mandible anchor distance `7.588`, cavity anchor distance `0.686`, a `0.9176`
mandible-to-upper reach ratio, `0.2471` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 2,064 changed mouth
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 37 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-037-one-pair-2026-08-05-v1/`

The queue now contains 35 strict internal passes, 29 pending observable pairs,
and 2 not-observable rear views. Pair 38 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 38 (`invitation-to-follow`) passed its isolated native-size,
enlarged-beak, and full-projector review. Candidate v3 reproduces the selected
v2 speaking pixels exactly while upgrading the pair to the current directional
anatomy receipt. The right-facing closed frame, eyes, crown, cheeks, throat,
hoodie, invitation wing, feet, scale, canvas, and registration remain
unchanged.

The restrained lower mandible follows the authored bill toward screen right
from the screen-left rear hinge. It remains beneath the immutable upper bill
with one connected edge and a contained cavity; there is no detached strip,
duplicate mouth, throat import, or lateral tip jump. The selected frame retains
SHA-256
`9edb881bcba212f75d4e465e317c5b4d5c25db8b81c5ad5f39f67d31b8f62ef7`.
The upgraded receipt records hinge `(443, 229)`, upper anchor distance `5.301`,
mandible anchor distance `3.041`, cavity anchor distance `1.973`, a `0.9155`
mandible-to-upper reach ratio, `0.1197` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit reports 1,413 changed mouth
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `0.999873`.

Fresh Pair 38 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-038-one-pair-2026-08-05-v1/`

The queue now contains 36 strict internal passes, 28 pending observable pairs,
and 2 not-observable rear views. Pair 39 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 39 (`describe-a-vast-scene`) passed its isolated native-size,
enlarged-beak, and full-projector review. Candidate v8 reproduces the selected
v7 speaking pixels exactly while upgrading the pair to the current directional
anatomy receipt. The long right-facing closed frame, eye, crown, cheek, throat,
hoodie, spread-wing storytelling gesture, feet, scale, canvas, and registration
remain unchanged.

The lower mandible follows the authored long bill toward screen right from the
screen-left rear hinge. It is one fully connected component beneath the
immutable upper bill, with one contained cavity and no detached donor pixel,
duplicate edge, throat import, or lateral tip jump. The selected frame retains
SHA-256
`e18373160b61c0596ffbd881e59861a4131aedfd733ed4b33e4c2d4e3e50e5ab`.
The upgraded receipt records hinge `(484, 175)`, upper anchor distance `11.169`,
mandible anchor distance `5.72`, cavity anchor distance `0.868`, a `0.9453`
mandible-to-upper reach ratio, `0.1523` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit uses the current compliant
140-pixel-wide articulation region and reports 2,147 changed mouth pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `0.997842`.

Fresh Pair 39 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-039-one-pair-2026-08-06-v1/`

The queue now contains 37 strict internal passes, 27 pending observable pairs,
and 2 not-observable rear views. Pair 40 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 40 (`describe-a-tiny-detail`) passed its isolated native-size,
nearest-neighbor beak close-up, and full-projector review. Candidate v4
reproduces the selected v3 speaking pixels byte-for-byte while upgrading the
pair to the current directional anatomy receipt. The closed frame, eye, crown,
cheek, throat, hoodie, raised-wing detail gesture, feet, scale, canvas, and
registration remain unchanged.

The lower mandible stays attached at the screen-left rear hinge, follows the
immutable upper bill toward screen right, and terminates beneath the same tip.
It is one fully connected component with a contained oral cavity; there is no
detached line, duplicated beak edge, throat import, or lateral drift. The
selected frame retains SHA-256
`4edd761deb03fdcc0adc87deed9b2dbc041474d733ba6ca189e7c4258e93973c`.
The upgraded receipt records hinge `(446, 231)`, upper anchor distance `3.098`,
mandible anchor distance `5.452`, cavity anchor distance `4.0`, a `0.9928`
mandible-to-upper reach ratio, `0.0942` normalized tip offset, and
connected-mandible ratio `1.0`. Its strict audit uses a 147-by-65-pixel
articulation region and reports 2,698 changed mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 40 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-040-one-pair-2026-08-06-v1/`

The queue now contains 38 strict internal passes, 26 pending observable pairs,
and 2 not-observable rear views. Pair 41 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 41 (`centered-calm`) failed its first isolated visual inspection even
though the previous automated audit was green. The old speaking mate replaced
too much of the frontal upper bill with a tall black diamond, causing the open
frame to read as a second beak suspended below the face. That v3 geometry was
rejected rather than carried forward.

Candidate v9 is a fresh pair-specific rebuild. It compresses only the lower-jaw
donor and confines the oral cavity to a compact V-shaped band inside the
canonical bill footprint. The two mouth corners remain balanced around the
character centerline, the immutable upper bill stays visually intact, and the
lower rim remains one connected component. The closed frame, eyes, crest,
cheeks, throat, hoodie, body, feet, scale, canvas, and registration remain
unchanged.

The accepted internal candidate has SHA-256
`0afb6f3aefb0ba9334156ab961345976415a9dbadbfce67659c6a73a88a70942`.
Its anatomy receipt records hinge `(480, 250)`, zero normalized center offset,
a `0.6098` mandible-to-upper width ratio, upper anchor distance `16.506`,
mandible anchor distance `19.799`, cavity anchor distance `14.142`, and
connected-mandible ratio `1.0`. The strict 60-by-45 articulation audit reports
812 changed mouth pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `1.0`.

Fresh Pair 41 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-041-one-pair-2026-08-06-v1/`

The queue now contains 39 strict internal passes, 25 pending observable pairs,
and 2 not-observable rear views. Pair 42 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 42 (`joy`) passed its isolated native-size, nearest-neighbor beak
close-up, and full-projector review. Candidate v6 reproduces the selected v5
speaking pixels byte-for-byte while upgrading the pair to the current
directional anatomy receipt. The small screen-left blue patch is unchanged
canonical cheek and upper-bill detail; it is not transferred lower-jaw
residue. The actual lower jaw stays attached at the screen-left rear hinge and
opens toward screen right. The closed frame, eyes, crown, cheeks, throat,
hoodie, raised joy wings, feet, scale, canvas, and registration remain
unchanged.

The lower mandible follows the immutable upper bill, terminates beneath the
same tip, and remains one connected component with a contained oral cavity.
There is no detached strip, duplicate beak edge, throat import, or lateral tip
jump. The selected frame retains SHA-256
`5094d4d966aa20378e13405d3324677b2e2b7ce59923f7dc2c759135f5e00709`.
The upgraded receipt records hinge `(443, 150)`, upper anchor distance `1.0`,
mandible anchor distance `2.121`, cavity anchor distance `1.611`, upper reach
`95`, mandible reach `97`, a `1.0211` mandible-to-upper reach ratio, `0.0105`
normalized tip offset, and connected-mandible ratio `1.0`. Its strict audit
reports 1,600 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 42 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-042-one-pair-2026-08-06-v1/`

The queue now contains 40 strict internal passes, 24 pending observable pairs,
and 2 not-observable rear views. Pair 43 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 43 (`full-laughter`) passed its isolated native-size, enlarged-beak, and
full-projector review. Candidate v3 reproduces the selected v2 speaking pixels
byte-for-byte while upgrading the pair to the current directional anatomy
receipt. This pair intentionally uses a broad laughter opening, but the lower
bill rotates from the same screen-left rear hinge and remains beneath the
immutable upper bill. The closed eyes, crest, cheeks, throat, hoodie, extended
wings, body, feet, scale, canvas, and registration remain unchanged.

The lower mandible has the same longitudinal reach as the upper bill and ends
beneath the same tip. It remains one connected component with a contained oral
cavity; there is no detached strip, duplicate bill edge, throat import, or
lateral drift. The selected frame retains SHA-256
`1c4b618e3ea97d665e6bcf53bb8fdf24213d8fa977ab96527487f8545beaf0a2`.
The upgraded receipt records hinge `(418, 116)`, upper anchor distance `0.503`,
mandible anchor distance `2.258`, cavity anchor distance `1.998`, equal upper
and mandible reach of `172`, a `1.0` mandible-to-upper reach ratio, `0.0087`
normalized tip offset, and connected-mandible ratio `1.0`. Its strict audit
reports 2,542 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.999505`.

Fresh Pair 43 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-043-one-pair-2026-08-06-v1/`

The queue now contains 41 strict internal passes, 23 pending observable pairs,
and 2 not-observable rear views. Pair 44 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 44 (`excitement`) passed its isolated native-size, enlarged frontal-beak,
and full-projector review. Candidate v2 reproduces the selected speaking pixels
byte-for-byte while upgrading the pair to the current directional anatomy
receipt. The compact lower bill remains attached to the canonical frontal bill
with a contained oral cavity and one continuous lower edge. The eyes, crest,
cheeks, throat, hoodie, raised wings, body, feet, scale, canvas, and
registration remain unchanged.

The lower mandible follows the immutable upper bill toward screen right from
the screen-left rear hinge. There is no detached strip, duplicate edge, throat
import, or lateral drift. The selected frame retains SHA-256
`f89f4e688930d96a2bda186e7d5d0e6d33ae198a8c9c20cea5404f0fddb58c74`.
The upgraded receipt records hinge `(458, 239)`, upper anchor distance `0.0`,
mandible anchor distance `1.764`, cavity anchor distance `0.0`, upper reach
`73`, mandible reach `81`, a `1.1096` mandible-to-upper reach ratio, `0.1644`
normalized tip offset, and connected-mandible ratio `1.0`. Its strict audit
reports 1,050 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 44 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-044-one-pair-2026-08-06-v1/`

The queue now contains 42 strict internal passes, 22 pending observable pairs,
and 2 not-observable rear views. Pair 45 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 45 (`curiosity`) passed its isolated native-size, enlarged tilted-beak,
and full-projector review. Candidate v2 reproduces the selected speaking pixels
byte-for-byte while upgrading the pair to the current directional anatomy
receipt. The compact lower bill follows the authored head tilt from the same
screen-left rear hinge and stays beneath the immutable upper bill. The eyes,
crest, cheeks, throat, hoodie, folded wings, body, feet, scale, canvas, and
registration remain unchanged.

The lower mandible remains one connected component with a contained oral
cavity. There is no detached strip, duplicate bill edge, throat import, or
lateral drift. The selected frame retains SHA-256
`5f8e423483da2ef3aa66b68f41c7a72463472a8905e202c46df1e1cd8ab0c5cf`.
The upgraded receipt records hinge `(446, 244)`, upper anchor distance `3.167`,
mandible anchor distance `2.598`, cavity anchor distance `13.124`, upper reach
`46`, mandible reach `42`, a `0.913` mandible-to-upper reach ratio, `0.087`
normalized tip offset, and connected-mandible ratio `1.0`. Its strict audit
reports 1,066 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 45 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-045-one-pair-2026-08-06-v1/`

The queue now contains 43 strict internal passes, 21 pending observable pairs,
and 2 not-observable rear views. Pair 46 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 46 (`confident-hero`) passed its isolated native-size, enlarged
frontal-beak, and full-projector review. Candidate v3 corrects the older
left-corner hinge description to the actual frontal centerline while
reproducing the selected speaking pixels byte-for-byte. The compact lower bill
is centered beneath the immutable upper bill with balanced mouth corners. The
eyes, crest, cheeks, throat, hoodie, extended wings, body, feet, scale, canvas,
and registration remain unchanged.

The frontal lower mandible remains one connected component with a contained
oral cavity. There is no detached strip, duplicate edge, throat import, or
lateral drift. The selected frame retains SHA-256
`889dab0f3f3845016cfd02a44cf2c6fa9079187b632a0c2c1db9fbd8ea6a59fc`.
The upgraded receipt records centerline hinge `(480, 184)`, center offset ratio
`0.0`, mandible width ratio `0.7857`, upper anchor distance `0.0`, mandible
anchor distance `3.0`, cavity anchor distance `0.0`, and connected-mandible
ratio `1.0`. Its strict audit reports 2,532 changed mouth pixels, outside-mouth
mean difference `0.0`, registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 46 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-046-one-pair-2026-08-06-v1/`

The queue now contains 44 strict internal passes, 20 pending observable pairs,
and 2 not-observable rear views. Pair 47 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 47 (`compassion`) passed its isolated native-size, enlarged directional-
beak, and full-projector review. Candidate v2 reproduces the selected speaking
pixels byte-for-byte while upgrading the pair to the current anatomy receipt.
The bowed head and long opening retain the canonical eye, crest, face,
complete upper bill, throat, hoodie, extended wing, body, feet, canvas, and
registration. Only the connected lower mandible and bounded oral cavity
change.

The lower bill follows the immutable upper bill toward screen left from the
same screen-right rear hinge. The selected frame retains SHA-256
`e55e383be358770553564669c47914154b2e52a6fe417667de120edd9da0e2a0`.
The upgraded receipt records hinge `(512, 238)`, upper reach `87`, mandible
reach `50`, a `0.5747` mandible-to-upper reach ratio, `0.5172` normalized tip
offset, upper anchor distance `5.047`, mandible anchor distance `9.836`, cavity
anchor distance `3.684`, and connected-mandible ratio `1.0`. Its strict audit
reports 2,537 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 47 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-047-one-pair-2026-08-06-v1/`

The queue now contains 45 strict internal passes, 19 pending observable pairs,
and 2 not-observable rear views. Pair 48 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 48 (`surprise`) passed its isolated native-size, enlarged frontal-mouth,
and full-projector review. Candidate v7 preserves the selected speaking pixels
byte-for-byte while correcting the old screen-right hinge declaration to the
actual frontal centerline. The compact surprised opening sits beneath the
immutable upper bill; the eyes, crest, face, throat, hoodie, spread wings,
body, feet, canvas, registration, and silhouette remain unchanged.

The selected frame retains SHA-256
`2379d0fd414f2d020bbdb3ac6679d60ecf30c7ab0e5c23e9f2eb3f14ed7a7fae`.
The upgraded receipt records centerline hinge `(528, 161)`, center offset ratio
`0.0143`, mandible width ratio `0.8571`, upper anchor distance `26.0`,
mandible anchor distance `26.0`, cavity anchor distance `11.0`, and connected-
mandible ratio `0.975081`. Its strict audit reports 2,059 changed mouth pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Fresh Pair 48 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-048-one-pair-2026-08-06-v1/`

The queue now contains 46 strict internal passes, 18 pending observable pairs,
and 2 not-observable rear views. Pair 49 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 49 (`confusion`) passed its isolated native-size, enlarged directional-
beak, and full-projector review. Candidate v2 preserves the selected speaking
pixels byte-for-byte while correcting the old tip-side hinge to the actual
screen-left beak root. The lower mandible now declares motion toward screen
right, matching the bird's head and immutable upper bill. The eye, crest,
face, throat, hoodie, raised wing, body, feet, canvas, registration, and
silhouette remain unchanged.

The selected frame retains SHA-256
`290a8b5664bc6cf6633b62042da7e0337c35fb69602a5bf6e504525c714d5336`.
The upgraded receipt records hinge `(500, 207)`, upper reach `96`, mandible
reach `95`, a `0.9896` mandible-to-upper reach ratio, `0.2188` normalized tip
offset, upper anchor distance `2.683`, mandible anchor distance `8.0`, cavity
anchor distance `3.058`, and connected-mandible ratio `1.0`. Its strict audit
reports 3,022 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.99991`.

Fresh Pair 49 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-049-one-pair-2026-08-06-v1/`

The queue now contains 47 strict internal passes, 17 pending observable pairs,
and 2 not-observable rear views. Pair 50 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 50 (`skepticism`) passed its isolated native-size, enlarged directional-
beak, and full-projector review. Candidate v2 preserves the selected speaking
pixels byte-for-byte while separating the broad immutable-source restoration
mask from the tight anatomical upper-bill outline. This prevents forehead or
face pixels needed for restoration from distorting the beak-axis measurement.
The lower bill opens toward screen left from the same screen-right root as the
immutable upper bill. The narrowed gaze, crest, face, throat, hoodie, crossed-
wing posture, body, feet, canvas, registration, and silhouette remain fixed.

The selected frame retains SHA-256
`445a6763232d5c49b54b00f7f7bae0d6d55ace2373fb8d59223c9a65aca0ac72`.
The upgraded receipt records hinge `(497, 222)`, upper reach `98`, mandible
reach `88`, a `0.898` mandible-to-upper reach ratio, `0.0816` normalized tip
offset, upper anchor distance `8.171`, mandible anchor distance `2.236`, cavity
anchor distance `1.114`, and connected-mandible ratio `0.995865`. Its strict
audit reports 1,451 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.999969`.

Fresh Pair 50 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-050-one-pair-2026-08-06-v1/`

The queue now contains 48 strict internal passes, 16 pending observable pairs,
and 2 not-observable rear views. Pair 51 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 51 (`concern`) passed its isolated native-size, enlarged directional-
beak, and full-projector review. Candidate v2 preserves the selected speaking
pixels byte-for-byte while measuring the actual upper-bill anatomy separately
from the broader immutable-source restoration mask. The lower bill follows the
steep screen-left perspective from the same screen-right root. The concerned
gaze, crest, face, throat, hoodie, hand-to-chest gesture, body, feet, canvas,
registration, and silhouette remain unchanged.

The selected frame retains SHA-256
`6bcec86adbc554170785fe07a54e390187b891e504d01736cac6dda8b2b2795f`.
The upgraded receipt records hinge `(497, 247)`, upper reach `100`, mandible
reach `98`, a `0.98` mandible-to-upper reach ratio, `0.01` normalized tip
offset, upper anchor distance `1.693`, mandible anchor distance `2.828`, cavity
anchor distance `2.236`, and connected-mandible ratio `1.0`. Its strict audit
reports 2,792 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 51 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-051-one-pair-2026-08-06-v1/`

The queue now contains 49 strict internal passes, 15 pending observable pairs,
and 2 not-observable rear views. Pair 52 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 52 (`sadness`) passed its isolated native-size, enlarged directional-
beak, and full-projector review. Candidate v14 preserves the selected speaking
pixels byte-for-byte while replacing the broad restoration mask as the source
of anatomical measurements with a tight upper-bill outline. The restrained
sad aperture keeps the upper and lower tips aligned toward screen left. The
downcast gaze, crest, face, immutable upper bill, white-and-orange throat,
hoodie, lowered wings, body, feet, canvas, registration, and silhouette remain
unchanged. The previously rejected throat-wedge attempt remains rejected in
the pair history.

The selected frame retains SHA-256
`586b845cfc3458416caa103de5cb7c1d4165999ec392cfcae1e2333481e0f226`.
The upgraded receipt records hinge `(480, 256)`, upper reach `71`, mandible
reach `73`, a `1.0282` mandible-to-upper reach ratio, `0.0141` normalized tip
offset, upper anchor distance `2.925`, mandible anchor distance `2.08`, cavity
anchor distance `0.0`, and connected-mandible ratio `1.0`. Its strict audit
reports 541 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 52 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-052-one-pair-2026-08-06-v1/`

The queue now contains 50 strict internal passes, 14 pending observable pairs,
and 2 not-observable rear views. Pair 53 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 53 (`embarrassment`) passed its isolated native-size, enlarged
directional-beak, and full-projector review. Candidate v4 preserves the
selected speaking pixels byte-for-byte while measuring a tight upper-bill
outline independently from the larger immutable-source restoration mask. Both
bill tips converge toward screen left from the same screen-right root; the
previously rejected double-blade and throat-overlay attempts remain rejected
in pair history. The side glance, crest, face, immutable upper bill, throat,
hoodie turn-away pose, body, feet, canvas, registration, and silhouette remain
unchanged.

The selected frame retains SHA-256
`63878f45e68f26192ff84fbd8ef56909fbe9327d164511ea5b3de0ba2d396b4c`.
The upgraded receipt records hinge `(432, 236)`, upper reach `62`, mandible
reach `63`, a `1.0161` mandible-to-upper reach ratio, `0.0968` normalized tip
offset, upper anchor distance `3.662`, mandible anchor distance `3.861`, cavity
anchor distance `2.353`, and connected-mandible ratio `1.0`. Its strict audit
reports 884 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.99886`.

Fresh Pair 53 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-053-one-pair-2026-08-06-v1/`

The queue now contains 51 strict internal passes, 13 pending observable pairs,
and 2 not-observable rear views. Pair 54 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 54 (`shame`) passed its isolated native-size, enlarged downward-beak,
and full-projector review. Candidate v10 preserves the selected speaking
pixels byte-for-byte while separating the tight anatomical upper-bill outline
from the broader immutable-source restoration mask. This nearly vertical pose
also exposed a limitation in the prior horizontal-only anatomy measurement.
The receipt now declares an explicit downward anatomy vector `[0, 1]`, so the
compiler measures both bills along their authored axis instead of treating the
pose as a sideways profile. The eye, bowed head, hood, immutable upper bill,
folded posture, body, feet, canvas, registration, and silhouette remain fixed.

The selected frame retains SHA-256
`126ba30998876662cb34058b4b40ffddf4148fa450f205a22f1ad0ca923b88c7`.
The upgraded receipt records hinge `(518, 248)`, upper reach `100`, mandible
reach `99`, a `0.99` mandible-to-upper reach ratio, `0.27` normalized tip
offset, upper anchor distance `0.0`, mandible anchor distance `5.363`, cavity
anchor distance `5.458`, and connected-mandible ratio `1.0`. Its strict audit
reports 2,138 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 54 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-054-one-pair-2026-08-06-v1/`

The queue now contains 52 strict internal passes, 12 pending observable pairs,
and 2 not-observable rear views. Pair 55 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 55 (`fear`) passed its isolated native-size, enlarged directional-beak,
and full-projector review. Candidate v5 preserves the selected speaking pixels
byte-for-byte while measuring the actual narrow upper-bill outline separately
from the broader immutable-source restoration mask. The shallow lower bill
opens toward screen left from the same screen-right hinge without recreating
the previously rejected oversized jaw or covering the white throat. The
fearful eyes, crest, face, immutable upper bill, raised-wing gesture, hoodie,
body, feet, canvas, registration, and silhouette remain fixed.

The selected frame retains SHA-256
`fbd8f362b920791253fa05440be8db6f0acaca42167c23f71c2d7a2e7f549eb9`.
The upgraded receipt records hinge `(603, 225)`, upper reach `93`, mandible
reach `71`, a `0.7634` mandible-to-upper reach ratio, `0.3333` normalized tip
offset, upper anchor distance `0.0`, mandible anchor distance `2.1`, cavity
anchor distance `4.243`, and connected-mandible ratio `1.0`. Its strict audit
reports 975 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.999655`.

Fresh Pair 55 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-055-one-pair-2026-08-06-v1/`

The queue now contains 53 strict internal passes, 11 pending observable pairs,
and 2 not-observable rear views. Pair 56 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 56 (`anxiety`) passed its isolated native-size, enlarged directional-
beak, and full-projector review. Candidate v2 preserves the selected speaking
pixels byte-for-byte while replacing the broad restoration region as the
anatomy source with the actual upper-bill outline. Both bills extend toward
screen right from one screen-left hinge and terminate together without a
doubled edge. The anxious side glance, crest, face, immutable upper bill,
white throat, hand-to-chest gesture, hoodie, body, feet, canvas, registration,
and silhouette remain fixed.

The selected frame retains SHA-256
`4a93031d11233865c091fa5c81d98da2f54edbd009018f9dcf7317a2e28ff029`.
The upgraded receipt records hinge `(443, 227)`, equal upper and mandible
reach `72`, a `1.0` mandible-to-upper reach ratio, `0.0625` normalized tip
offset, upper anchor distance `0.049`, mandible anchor distance `4.314`,
cavity anchor distance `0.256`, and connected-mandible ratio `1.0`. Its strict
audit reports 1,352 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 56 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-056-one-pair-2026-08-06-v1/`

The queue now contains 54 strict internal passes, 10 pending observable pairs,
and 2 not-observable rear views. Pair 57 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 57 (`anger`) passed its isolated native-size, enlarged frontal-beak, and
full-projector review. Candidate v2 preserves the selected speaking pixels
byte-for-byte while replacing the old left-corner proxy hinge with a frontal
centerline pivot and tight upper-bill outline. The open lower bill stays
centered beneath the immutable upper bill and remains connected across the
frontal mouth. The angry eyes, crest, face, white throat, squared stance,
hoodie, body, feet, canvas, registration, and silhouette remain fixed.

The selected frame retains SHA-256
`92d0e7db7b3a6edcabb813713348263740dbffbc3c333553d68f6f9dbf40d8b6`.
The upgraded receipt records centerline hinge `(480, 238)`, frontal width
ratio `1.0753`, center offset ratio `0.0376`, upper anchor distance `18.57`,
mandible anchor distance `8.936`, cavity anchor distance `16.838`, and
connected-mandible ratio `1.0`. Its strict audit reports 2,696 changed mouth
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Fresh Pair 57 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-057-one-pair-2026-08-06-v1/`

The queue now contains 55 strict internal passes, 9 pending observable pairs,
and 2 not-observable rear views. Pair 58 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 58 (`frustration`) passed its isolated native-size, enlarged down-left
beak, and full-projector review. Candidate v2 preserves the selected speaking
pixels byte-for-byte while replacing the legacy broad-mask anatomy assumption
with a tight upper-bill outline and explicit direction vector `[-6, 5]`. The
connected lower bill opens from the authored screen-right hinge along the same
axis as the immutable upper bill. The frustrated gaze, bowed crest, forehead
wing, face, white throat, hoodie, body, feet, canvas, registration, and
silhouette remain fixed.

The selected frame retains SHA-256
`9fe19bc2b57b262af8679f7c5d93614b68c4f9d649c73acb81532297c4e7d455`.
The upgraded receipt records hinge `(471, 260)`, upper reach `87.5772`,
mandible reach `77.5903`, a `0.886` mandible-to-upper reach ratio, `0.1842`
normalized tip offset, upper anchor distance `3.494`, mandible anchor distance
`5.571`, cavity anchor distance `0.43`, and connected-mandible ratio `1.0`.
Its strict audit reports 1,343 changed mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 58 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-058-one-pair-2026-08-06-v1/`

The queue now contains 56 strict internal passes, 8 pending observable pairs,
and 2 not-observable rear views. Pair 59 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 59 (`determination`) passed only after its first same-day successor was
rejected during enlarged beak review. Candidate v14 reached the correct upper-
bill tip but collapsed into a needle-thin lower line, demonstrating that the
directional anatomy metrics are necessary but not sufficient. The accepted
v17 rebuild uses a newly rendered one-pair mouth donor and transfers only the
connected lower mandible and bounded cavity onto the immutable canonical body.
The result preserves the determined gaze, crest, face, upper bill, throat,
hoodie, wings, stance, feet, canvas, and registration while giving the lower
bill a readable textured surface from the rear hinge to the tip.

The selected frame has SHA-256
`110c8295dced728b4639e7272807cd2fcf62f37b18e118fb35bff447833d9a14`.
Its receipt records hinge `(540, 247)`, upper reach `154`, mandible reach
`160`, a `1.039` mandible-to-upper reach ratio, `0.3636` normalized tip
offset, upper anchor distance `7.424`, mandible anchor distance `9.61`, cavity
anchor distance `2.046`, and connected-mandible ratio `1.0`. The strict audit
reports 4,499 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.992247`.

Fresh Pair 59 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-059-one-pair-2026-08-06-v2/`

The queue now contains 57 strict internal passes, 7 pending observable pairs,
and 2 not-observable rear views. Pair 60 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 60 (`fatigue`) passed its isolated native-size, enlarged down-left beak,
and full-projector review without changing the selected speaking frame. The
existing open pixels already form one coherent tired speaking aperture. The
receipt was upgraded to measure the actual upper bill independently from its
broader restoration mask and to declare the authored direction vector
`[-3, 2]`. The lower bill remains connected to the screen-right rear hinge,
tracks the steep perspective of the immutable upper bill, and keeps the warm
oral surface inside the cavity. The fatigued eyes, crest, cheek, throat,
hoodie, body, feet, canvas, registration, and silhouette remain fixed.

The selected frame retains SHA-256
`ddb869ec3244ee0d9b65fc1a61d8190cf22dbee626cb89cdb4f8b70ae0332d2c`.
The upgraded receipt records hinge `(450, 258)`, upper reach `90.4161`,
mandible reach `78.4901`, a `0.8681` mandible-to-upper reach ratio, `0.1779`
normalized tip offset, upper anchor distance `6.708`, mandible anchor distance
`7.82`, cavity anchor distance `1.572`, and connected-mandible ratio `1.0`.
Its strict audit retains 2,092 changed mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 60 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-060-one-pair-2026-08-06-v1/`

The queue now contains 58 strict internal passes, 6 pending observable pairs,
and 2 not-observable rear views. Pair 61 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 61 (`deep-contemplation`) passed its isolated native-size, enlarged
down-left beak, and full-projector review without changing the selected
speaking pixels. The receipt now separates a tight upper-bill outline from the
larger immutable restoration mask and declares direction vector `[-1, 1]`.
The lower mandible opens from the same screen-right rear hinge, follows the
steep authored bill axis, and remains legible beside the hand-on-chin gesture.
The contemplative eye, crest, face, throat, upper bill, hand, hoodie, body,
feet, canvas, registration, and silhouette remain fixed.

The selected frame retains SHA-256
`45fc98159a2852cb4fc349a2c0e9a69d71f1815c00f9896f3b5deeedbaf366c5`.
The upgraded receipt records hinge `(468, 216)`, upper reach `92.631`,
mandible reach `79.9031`, a `0.8626` mandible-to-upper reach ratio, `0.0267`
normalized tip offset, upper anchor distance `8.246`, mandible anchor distance
`6.548`, cavity anchor distance `1.052`, and connected-mandible ratio `1.0`.
Its strict audit retains 1,700 changed mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `1.0`.

Fresh Pair 61 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-061-one-pair-2026-08-06-v1/`

The queue now contains 59 strict internal passes, 5 pending observable pairs,
and 2 not-observable rear views. Pair 62 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 62 (`sudden-idea`) failed its isolated native-size and enlarged beak
review even though the previous automated geometry checks had passed. The
selected open frame reduced the lower mandible to a needle-thin line crossing
the throat, so it did not read as a hinged bill in projector playback. The
replacement was rebuilt only from Pair 62's own full-resolution head donor.
The deterministic compositor transfers one thicker, textured lower mandible
and its bounded cavity onto the immutable canonical resting body. The raised
wing, crest, eye, cheek, throat, hoodie, body, feet, upper bill, canvas, and
registration remain unchanged.

The selected replacement has SHA-256
`abcd9b2e4acbc3a8f3bbdda226eac05e4a0d96948017eeb95acffe0ace49640b`.
Its receipt records hinge `(480, 250)`, upper reach `70`, mandible reach `65`,
a `0.9286` mandible-to-upper reach ratio, `0.1643` normalized tip offset,
upper anchor distance `1.789`, mandible anchor distance `6.0`, cavity anchor
distance `2.737`, and connected-mandible ratio `1.0`. The strict audit reports
1,304 changed mouth pixels, outside-mouth mean difference `0.0`, registration
delta `0`, and silhouette IoU `1.0`.

Fresh Pair 62 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-062-one-pair-2026-08-06-v1/`

The queue now contains 60 strict internal passes, 4 pending observable pairs,
and 2 not-observable rear views. Pair 63 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 63 (`read-a-panel`) failed its first isolated native-size and enlarged
beak review even though the previous geometry receipt passed. The old open
frame read as a narrow black blade with an ambiguous hinge rather than as an
articulated bill. The accepted v14 rebuild uses only Pair 63's own
full-resolution head donor. It transfers one thicker connected lower mandible
and its bounded mouth cavity onto the immutable canonical body. The reading
pose, panel, crest, eye, cheek, throat, hoodie, feet, upper bill, canvas, and
registration remain unchanged.

The selected replacement has SHA-256
`2cfcd0089ad63444348753fc76313b067a0396567816d9c3e659389e8295b562`.
Its receipt records hinge `(509, 214)`, upper reach `99.6117`, mandible reach
`110.3635`, a `1.1079` mandible-to-upper reach ratio, `0.4825` normalized tip
offset, upper anchor distance `0.392`, mandible anchor distance `9.0`, cavity
anchor distance `5.676`, and connected-mandible ratio `0.998986`. The strict
audit reports 2,574 changed mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.9929`.

Fresh Pair 63 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-063-one-pair-2026-08-06-v1/`

The queue now contains 61 strict internal passes, 3 pending observable pairs,
and 2 not-observable rear views. Pair 64 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 64 (`study-a-diagram`) passed its isolated native-size, enlarged beak,
and live-projector review without changing the selected speaking pixels. The
existing open frame already forms one broad connected lower mandible with a
bounded warm oral cavity at the authored screen-left hinge. The upgraded
receipt measures the immutable upper bill independently along direction
vector `[4, 1]`; this prevents the broad restoration mask from standing in for
actual beak anatomy. The crest, eye, face, cheek, throat, hoodie, fishbone
mark, pointing wing, body, stance, feet, upper bill, canvas, registration, and
silhouette remain fixed.

The selected frame retains SHA-256
`4768451f594a04cadf90aa1f5c78709de65675544e3a37728d2dbf56bd9e3b81`.
The upgraded receipt records hinge `(398, 216)`, upper reach `116.9022`,
mandible reach `121.9954`, a `1.0436` mandible-to-upper reach ratio, `0.139`
normalized tip offset, upper anchor distance `0.343`, mandible anchor distance
`6.0`, cavity anchor distance `3.682`, and connected-mandible ratio `1.0`.
Its strict audit retains 2,989 changed mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `0.998027`.

Fresh Pair 64 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-064-one-pair-2026-08-06-v1/`

The queue now contains 62 strict internal passes, 2 pending observable pairs,
and 2 not-observable rear views. Pair 65 is the next isolated gate; user
approval and runtime admission remain zero.

Pair 65 (`write-or-tap`) passed its isolated native-size, enlarged beak, and
live-projector review without changing the selected speaking pixels. The
existing lower mandible already opens from the authored upper-left hinge,
follows the steep down-right bill axis, reaches the immutable upper-tip line,
and contains one bounded warm oral cavity. The upgraded receipt independently
measures the upper bill along direction vector `[2, 3]`. The bowed crest, eye,
face, cheek, throat, hoodie, fishbone mark, writing wing, body, stance, feet,
upper bill, canvas, registration, and silhouette remain fixed.

The selected frame retains SHA-256
`3fa1c854c576e8a9957ab5716f7d76726ac594bbf828947070d09d742d8959f9`.
The upgraded receipt records hinge `(560, 254)`, upper reach `99.846`,
mandible reach `113.1588`, a `1.1333` mandible-to-upper reach ratio, `0.1194`
normalized tip offset, upper anchor distance `11.18`, mandible anchor distance
`5.423`, cavity anchor distance `2.433`, and connected-mandible ratio `1.0`.
Its strict audit retains 2,761 changed mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `0.994563`.

Fresh Pair 65 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-065-one-pair-2026-08-06-v1/`

The queue now contains 63 strict internal passes, 1 pending observable pair,
and 2 not-observable rear views. Pair 66 is the final isolated gate; user
approval and runtime admission remain zero.

Pair 66 (`select-a-control`) passed its isolated native-size, enlarged beak,
and live-projector review without changing the selected speaking pixels. One
connected lower mandible opens from the authored screen-left hinge, follows
the shallow rightward bill axis, reaches the immutable upper-tip line, and
contains one bounded warm oral cavity. The upgraded receipt independently
measures the upper bill along direction vector `[5, 1]`. The crest, eye, face,
cheek, throat, hoodie, fishbone mark, raised control wing, body, stance, feet,
upper bill, canvas, registration, and silhouette remain fixed.

The selected frame retains SHA-256
`85b3f3028e9a1c28eb63af23eeb162f152989ec63a7c96713f6e2a4f29badc33`.
The upgraded receipt records hinge `(441, 230)`, upper reach `110.8056`,
mandible reach `114.3357`, a `1.0319` mandible-to-upper reach ratio, `0.1133`
normalized tip offset, upper anchor distance `1.793`, mandible anchor distance
`3.915`, cavity anchor distance `2.774`, and connected-mandible ratio `1.0`.
Its strict audit retains 1,824 changed mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `0.995926`.

Fresh Pair 66 evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-066-one-pair-2026-08-06-v1/`

The reopened strict corpus audit now contains 64 observable internal passes,
0 pending observable pairs, and 2 not-observable rear views. User approval and
runtime admission remain zero; those are separate gates and are not implied by
completion of this internal visual review.

The production completion verifier passed against compiled artifact
`kingfisher_act_001_066_111_176_pair_review-a535f9fe6f5b89d4.wjpose`
with SHA-256
`a535f9fe6f5b89d48ca91d8977656ae1b855991de579a14ea339d141e5815a9f`.
It confirms 66 authored pairs, 176 poses, 132 closed/open sequence frames, 176
binary-alpha poses on the canonical `960x540` canvas, registration-bound delta
`0`, minimum pair silhouette IoU `0.988776`, 64 observable full-size passes,
2 not-observable rear views, 0 user approvals, and 0 runtime admissions.

## 2026-08-07 visual re-open and sequence quarantine

The user reported that many beaks still looked visibly misaligned in
`kingfisher-all`. That observation invalidates the prior internal completion
claim. All 64 observable closed/open pairs were returned to `pending`; the two
rear views remain `not_observable`. User approval and runtime admission remain
zero.

The correction changes both the art workflow and the projector contract:

1. Rebuild and inspect one closed/open pair at a time.
2. Use the pair's exact closed frame as the body, head, eye, upper-beak,
   canvas, scale, and registration authority.
3. Render or articulate only that pair's connected lower mandible and bounded
   oral cavity.
4. Inspect the two-frame loop at native size and enlarged beak framing.
5. Restore an internal `pass` only for that single pair.
6. Keep every pending or failed speaking mate out of `kingfisher-all`.

The dedicated `kingfisher-paired-beaks-review` sequence continues to expose
all candidate pairs for review. The normal `kingfisher-all` reel now includes
every resting pose but admits a speaking mate only when that exact pair has a
`pairwise_full_size_review.state` of `pass`. A pending candidate can therefore
be inspected without being presented as integrated animation.

Pair 7 (`front-three-quarter-right`) is the first visibly rejected drawing in
the reopened queue. Its current lower bill descends on a substantially steeper
axis than the fixed upper bill and reads as a pasted jaw in alternating
playback. It remains quarantined pending a new pair-specific speaking mate.

### Pair 7 isolated hinge repair

Pair 7 was rebuilt as an isolated closed/open pair. The exact resting frame is
the body, head, eye, crest, upper-bill, canvas, scale, and registration
authority. The repair reuses the textured lower mandible from the former open
mate, removes light neutral throat contamination, and rotates that mandible
`-18` degrees around the authored hinge `(449, 253)`. The bounded oral cavity
is repainted behind the mandible and the resting upper-bill pixels are restored
exactly after composition.

The corrected speaking frame retains SHA-256
`4b59e7f133af357c44a7557b1822f03722c88f3a0f33125959699b5463a4fd28`.
Its receipt records one connected lower mandible with connected ratio `1.0`,
opening angle `20.9304` degrees, mandible-to-upper reach ratio `0.7493`, and no
change outside the mouth articulation region. The strict audit reports
outside-mouth mean difference `0.0`, registration delta `0`, silhouette IoU
`0.996078`, and 1,407 changed rendered pixels.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-007-hinge-refined-2026-08-07-v1/`

This is an internal visual pass for Pair 7 only. It does not imply user
approval or runtime admission. The reopened queue now contains 1 internal
pass, 63 pending observable pairs, and 2 not-observable rear views. Every
unpassed speaking mate remains excluded from `kingfisher-all`.

### Pair 1 isolated neutral-front review

Pair 1 (`neutral-front`) was then reviewed independently at full-projector
size and in a six-second closed/open loop. Its existing speaking mate was
retained rather than redrawn: the lower bill opens symmetrically on the
vertical facial centerline from the bilateral hinge `(480, 240)`, while the
crown, eyes, upper bill, throat, hoodie, body, scale, canvas, and registration
remain fixed.

The speaking frame retains SHA-256
`fce4d995abd80f2c964f7c83f9db741cfd3d498a4c26251cf632c5d72460475c`.
Its frontal anatomy receipt records center offset ratio `0.0`, lower-to-upper
width ratio `1.1875`, and a passing symmetric hinge check. The body-lock audit
reports 5,806 changed rendered mouth pixels, outside-mouth mean difference
`0.0`, registration delta `0`, and silhouette IoU `1.0`.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-001-one-pair-2026-08-07-v3/`

This is an internal visual pass only. The reopened queue now contains 2
internal passes, 62 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 2 isolated three-quarter review

Pair 2 (`front-three-quarter-left`) was reviewed independently at full-projector
size and in a six-second closed/open loop. The selected speaking mate has one
connected lower mandible opening from hinge `(493, 242)` on the same
screen-right axis as the immutable upper bill. The earlier thin gray-seam
candidate remains rejected and was not substituted.

The selected speaking frame retains SHA-256
`36fbe2b4532d242eef9237e0fb0129fafe2fa59269eb2bebf5ac88d6faed83da`.
Its anatomy measures a `13.474` degree opening, `0.8013`
mandible-to-upper reach ratio, `0.192` normalized tip offset, and connected
mandible ratio `1.0`. The body-lock audit reports 2,452 changed rendered mouth
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-002-one-pair-2026-08-07-v3/`

This is an internal visual pass only. The reopened queue now contains 3
internal passes, 61 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 3 isolated left-profile review

Pair 3 (`left-profile`) was reviewed independently at full-projector size and
in a six-second closed/open loop. The selected speaking mate retains one
connected lower mandible opening from hinge `(420, 234)` on the same
screen-left axis as the immutable upper bill. The lower tip remains behind the
upper tip, preserving the authored profile and avoiding the pasted-jaw reading
seen in the rejected bulk pass.

Its anatomy measures a `23.5183` degree opening, `0.7897`
mandible-to-upper reach ratio, and `0.3437` normalized tip offset. The audit
reports 861 changed rendered mouth pixels, outside-mouth mean difference
`0.0`, registration delta `0`, and silhouette IoU `0.993`. The crown, eye,
head, throat, hoodie, body, scale, and canvas remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-003-one-pair-2026-08-07-v3/`

This is an internal visual pass only. The reopened queue now contains 4
internal passes, 60 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 6 isolated right-profile rebuild

Pair 6 (`right-profile`) exposed why the previous batch process was not
trustworthy. Its nominally passing mate presented a thin dark wedge beneath the
white throat instead of a complete lower bill. That mate and three derivative
candidates were rejected during the isolated review.

The replacement copies only the exact authored open-mouth region from the
original right-profile donor onto the exact resting body. This preserves the
natural upper bill, lower bill, oral cavity, and shared rear hinge near
`(533, 239)`, while every pixel outside the bounded mouth region remains owned
by the closed frame.

The selected frame retains SHA-256
`a9cb089f119136ce0478ded4b721adcff589eeea7a3d6baa1d8b7cd351537b7f`.
Its anatomy records a `30.6206` degree opening, `0.7888`
mandible-to-upper reach ratio, and `0.4669` normalized tip offset. The strict
audit reports 2,739 changed rendered mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `0.978873`.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-006-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 5
internal passes, 59 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 8 isolated relaxed-idle review

Pair 8 (`relaxed-idle`) was reviewed independently at enlarged beak scale,
full-projector size, and in a six-second closed/open loop. The retained
tight-anatomy mate uses one connected lower mandible opening from hinge
`(439, 250)` on the same screen-left axis as the immutable upper bill. The
lower tip remains behind the upper tip and the deliberately restrained opening
fits the relaxed performance state.

The speaking frame retains SHA-256
`628efc0df78675867d03cd52a97ff4afa33e43511728ff1c767339ca3a1a4e95`.
Its anatomy measures a `22.3205` degree opening, `0.9124`
mandible-to-upper reach ratio, and `0.3746` normalized tip offset. The audit
reports 1,645 changed rendered mouth pixels, outside-mouth mean difference
`0.0`, registration delta `0`, and silhouette IoU `0.995701`.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-008-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 6
internal passes, 58 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 9 isolated attentive-idle review

Pair 9 (`attentive-idle`) was reviewed independently at enlarged beak scale,
full-projector size, and in a six-second closed/open loop. Its existing
authored speaking mate was retained. The open mouth forms a bilateral V beneath
the immutable frontal upper bill while the crown, eyes, throat, hoodie, body,
feet, canvas, scale, and registration remain fixed.

The earlier receipt incorrectly evaluated this frontal drawing as a
right-facing profile. The corrected receipt now separates the composition
hinge from a centered frontal anatomy hinge at `(481, 224)`. Its frontal gate
records center offset ratio `0.0074`, lower-to-upper width ratio `0.8676`, and
passing upper-bill, mandible, cavity, vertical-order, and symmetry checks. The
strict audit reports 1,038 changed rendered mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `1.0`.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-009-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 7
internal passes, 57 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 10 isolated ready-stance review

Pair 10 (`ready-stance`) was reviewed independently at enlarged beak scale,
full-projector size, and in a six-second closed/open loop. Its existing
authored speaking mate was retained. Both lower-bill corners attach beneath
the immutable frontal upper bill, and the slight texture asymmetry inside the
mouth does not move the beak centerline.

The frontal anatomy gate uses the centered hinge `(480, 238)` and records
center offset ratio `0.0094`, lower-to-upper width ratio `1.3962`, and passing
upper-bill, mandible, cavity, vertical-order, and symmetry checks. The strict
audit reports 1,537 changed rendered mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `1.0`. The crown,
eyes, throat, hoodie, wings, stance, feet, canvas, and scale remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-010-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 8
internal passes, 56 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 11 isolated neutral-speaking-gesture review

Pair 11 (`neutral-speaking-gesture`) was reviewed independently at enlarged
beak scale, full-projector size, and in a six-second closed/open loop. Every
local speaking candidate was compared against the repaired resting master.
Candidate v3 and v4 introduce a hard rectangular white seam through the throat,
while v5 deletes half of the mouth. Those derivatives remain rejected. The
current v2/v6 speaking mate is retained as the only complete centered opening.

The selected mate preserves the authored hand-to-beak overlap while opening
one connected V beneath the immutable frontal upper bill. Its frontal anatomy
gate records center offset ratio `0.0062`, lower-to-upper width ratio `1.0370`,
and mandible connected ratio `0.995627`. The strict audit reports 4,091 changed
rendered mouth pixels, outside-mouth mean difference `0.0`, registration delta
`0`, and silhouette IoU `1.0`; the crown, eyes, gesture, hoodie, body, feet,
canvas, and scale remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-011-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 9
internal passes, 55 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 12 isolated explain-one-point review

Pair 12 (`explain-one-point`) was reviewed independently at enlarged beak
scale, full-projector size, and in a six-second closed/open loop. The rejected
pre-pairwise donor changes the eyes and broader facial rendering and remains
excluded. The current body-locked speaking mate retains the exact closed-frame
crown, eyes, upper bill, pointing wing, hoodie, body, legs, and feet.

The selected mate opens one compact centered V beneath the immutable frontal
upper bill. Its frontal gate records center offset ratio `0.0086`,
lower-to-upper width ratio `0.7414`, and mandible connected ratio `0.81237`.
The strict audit reports 2,768 changed rendered mouth pixels, outside-mouth
mean difference `0.0`, registration delta `0`, and silhouette IoU `1.0`.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-012-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 10
internal passes, 54 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 13 isolated balance-two-ideas review

Pair 13 (`balance-two-ideas`) was reviewed independently at native size,
enlarged beak scale, full-projector size, and in a six-second closed/open loop.
The zero-offset frontal mate was retained. Four alternative placements shifted
the lower mandible 6, 10, 14, or 22 pixels toward screen left; each displaced
the mouth from the resting frame's beak hinge and remains excluded.

The selected mate opens one connected frontal mouth beneath the immutable
upper bill at hinge `(485, 229)`. Its frontal anatomy gate records center
offset ratio `0.0312`, lower-to-upper width ratio `0.9875`, and mandible
connected ratio `1.0`. The strict audit reports 3,667 changed rendered mouth
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`. The crown, eyes, throat, wings, hoodie, body, legs, feet,
canvas, and scale remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-013-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 11
internal passes, 53 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 14 isolated present-screen-left review

Pair 14 (`present-screen-left`) was reviewed independently at native size,
enlarged beak scale, full-projector size, and in a six-second closed/open loop.
The retained strict frame is pixel-identical to the verified v6 and v7 result.
The rejected pre-pairwise donor replaces and lengthens the upper bill, while
intermediate v2 and v3 frames expose a black throat void; none enter the
compiled sequence.

The selected lower bill opens from rear hinge `(538, 213)` along the authored
screen-left axis while the upper bill remains fixed. Its directional anatomy
records a `1.1075` lower-to-upper reach ratio and `0.2634` normalized tip
offset. The strict audit reports 2,331 changed rendered mouth pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `0.993514`. The crown, eye, throat, presenting wing, hoodie, body, legs,
feet, canvas, and scale remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-014-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 12
internal passes, 52 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 15 isolated present-screen-right review

Pair 15 (`present-screen-right`) was reviewed independently at native size,
enlarged beak scale, full-projector size, and in a six-second closed/open loop.
The retained verified frame is pixel-identical to the body-locked canonical
mate. The original source changes the head and beak construction, while the
rejected pre-pairwise frame exaggerates the gape; both remain excluded.

The selected lower bill opens from rear hinge `(402, 222)` along the authored
screen-right axis, with its tip remaining behind the upper tip. Its directional
anatomy records a `0.864` lower-to-upper reach ratio, `0.308` normalized tip
offset, and mandible connected ratio `1.0`. The strict audit reports 974
changed rendered mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.99476`. The crown, eye, upper
bill, throat, presenting wing, hoodie, body, legs, feet, canvas, and scale
remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-015-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 13
internal passes, 51 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 16 isolated point-to-viewer review

Pair 16 (`point-to-viewer`) was reviewed independently at native size,
enlarged beak scale, full-projector size, and in a six-second closed/open loop.
That review rejected the previously retained v2 frame: it preserved the closed
upper bill while placing a detached second V-shaped mouth on the throat. This
was visually wrong despite passing the earlier geometric checks.

The replacement v3 mate was rebuilt from the anatomically connected donor.
Only the mouth opening was compressed around the fixed frontal hinge
`(480, 228)`, producing one continuous upper-bill-to-cavity-to-mandible
articulation. Its frontal anatomy records center offset ratio `0.0`,
lower-to-upper width ratio `0.8871`, and mandible connected ratio `1.0`. The
strict audit reports 5,281 changed rendered mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `1.0`. The crown,
eyes, pointing wing, hoodie, body, legs, feet, canvas, and scale remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-016-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 14
internal passes, 50 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 17 isolated insight-upward-point review

Pair 17 (`insight-upward-point`) was reviewed independently at native size,
enlarged beak scale, full-projector size, and in a six-second closed/open loop.
The previously retained v2 mate was rejected because its lower bill remained
nearly horizontal beneath an upward-pitched head. It passed pixel connectivity
checks but did not share the upper bill's visible axis.

The replacement v3 mate retains the closed frame's head and upper bill and
rotates one connected donor mandible by `-5` degrees around the shared rear
hinge `(543, 221)`. Its directional anatomy records a `22.645` degree opening,
`0.7354` lower-to-upper reach ratio, `0.3068` normalized tip offset, and
`0.99533` mandible connected ratio. The strict audit reports 1,054 changed
rendered mouth pixels, outside-mouth mean difference `0.0`, registration delta
`0`, and silhouette IoU `0.993236`. The eye, crown, throat, raised insight
wing, hoodie, body, legs, feet, canvas, and scale remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-017-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 15
internal passes, 49 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 18 isolated detail-downward-point review

Pair 18 (`detail-downward-point`) was reviewed independently at native size,
nearest-neighbor enlarged beak scale, full-projector size, and in a six-second
closed/open loop. Candidate v1 remains rejected because it leaves only a
detached pink sliver. The pre-pairwise donor remains rejected because it
changes the upper mouth and opens too far. The retained verified v3 frame is
pixel-identical to the previously body-locked result.

An inspection-background artifact initially made the selected frame look
detached: its dark lower mandible disappears against black. On the actual
white projector, the mandible is visibly continuous from the shared rear hinge
`(525, 249)`, and the pink oral surface remains contained inside the bill. Its
directional anatomy records a `5.2753` degree opening, `0.9778`
lower-to-upper reach ratio, `0.0903` normalized tip offset, and mandible
connected ratio `1.0`. The strict audit reports 4,186 changed rendered mouth
pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `0.999987`. The closed eye, crown, head, upper bill, throat,
downward-pointing wing, hoodie, body, legs, feet, canvas, and scale remain
fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-018-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 16
internal passes, 48 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 19 isolated neutral-listening review

Pair 19 (`neutral-listening`) was reviewed independently at native size,
nearest-neighbor enlarged beak scale, full-projector size, and in a six-second
closed/open loop. The previously retained v2 mate was rejected even though it
passed the older geometry checks: its lower bill began too far forward and read
as a detached blade. The preserved donor established the correct rear hinge but
its original gape was too large for neutral listening.

The replacement v15 mate vertically compresses the approved donor around the
rear hinge while preserving the closed frame and upper-bill pixels exactly.
On the white projector field it reads as one connected, restrained speaking
articulation with a contained warm oral cavity. Its directional anatomy records
a `15.1808` degree opening, `0.8906` lower-to-upper reach ratio, `0.2417`
normalized tip offset, and mandible connected ratio `1.0`. The strict audit
reports 3,719 changed rendered mouth pixels, outside-mouth mean difference
`0.0`, registration delta `0`, and silhouette IoU `0.99993`. The crown, eye,
head, upper bill, throat, hoodie, wings, body, legs, feet, canvas, and scale
remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-019-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 17
internal passes, 47 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 20 isolated lean-in-listening review

Pair 20 (`lean-in-listening`) was reviewed independently at native size,
nearest-neighbor enlarged beak scale, full-projector size, and in a six-second
closed/open loop. The retained v4 pixels read as one centered V-shaped mouth:
the upper bill is unchanged, both mouth corners converge coherently, the warm
cavity remains contained, and no duplicate lower edge appears on the throat.

The earlier receipt incorrectly evaluated this near-frontal pose from a
one-sided directional hinge. The fresh review records the actual centerline at
`(538, 268)` and validates the same pixels with frontal anatomy. The lower bill
has center offset ratio `0.0081`, lower-to-upper width ratio `0.9516`, and
connected ratio `1.0`. The strict image audit reports 5,469 changed rendered
mouth pixels, outside-mouth mean difference `0.0`, registration delta `0`, and
silhouette IoU `1.0`. The eyes, crown, head, upper bill, throat, hoodie, wings,
body, legs, feet, canvas, and scale remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-020-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 18
internal passes, 46 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 21 isolated skeptical-listening review

Pair 21 (`skeptical-listening`) was reviewed independently at native size,
nearest-neighbor enlarged beak scale, tight-tip scale, full-projector size,
and in a six-second closed/open loop. The review compared the original,
candidates v2 through v5, the preserved source, and the raw render. Candidate
v5 was retained because it removes the stale pale tip silhouette and leaves
clean projector background through the gape instead of a duplicate bill edge.

The selected lower bill remains connected at rear hinge `(452, 250)`, follows
the authored screen-right upper-bill axis, and ends behind the upper tip. Its
directional anatomy records a `0.9612` lower-to-upper reach ratio, `0.3178`
normalized tip offset, and `0.995983` mandible connected ratio. The strict
audit reports 4,640 changed rendered mouth pixels, outside-mouth mean
difference `0.0`, registration delta `0`, and silhouette IoU `0.998056`. The
eye line, crown, cheek, throat, folded wing, hoodie, body, feet, canvas, and
scale remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-021-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 19
internal passes, 45 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 22 isolated small-acknowledgment review

Pair 22 (`small-acknowledgment`) was reviewed independently at native size,
nearest-neighbor enlarged beak scale, tight-tip scale, full-projector size,
and in a six-second closed/open loop. The review compared the original,
candidates v3 through v6, the preserved source, the raw render, and a fresh
closed-frame rotation experiment. Candidate v4 was rejected for a duplicate
dark interior contour, v6 for an artificial black slab, and the rotation
experiment for extending a cavity stripe beyond the bill.

Candidate v5 remains the only coherent mate. One restrained lower bill opens
from rear hinge `(462, 266)`, follows the authored down-right upper-bill axis,
and ends behind the upper tip. Its directional anatomy records a `0.9615`
lower-to-upper reach ratio, `0.2778` normalized tip offset, `16.1141` degree
opening, and `0.97903` mandible connected ratio. The strict audit reports
3,063 changed rendered mouth pixels, outside-mouth mean difference `0.0`,
registration delta `0`, and silhouette IoU `0.999766`. The eye line, crown,
cheek, throat, folded wings, hoodie, body, feet, scale, canvas, and upper bill
remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-022-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 20
internal passes, 44 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 23 isolated emphatic-agreement review

Pair 23 (`emphatic-agreement`) was reviewed independently at native size,
nearest-neighbor enlarged beak scale, tight-tip scale, full-projector size,
and in a six-second closed/open loop. The canonical mate, verified v4,
preserved source, and pairwise v2/v3 renders were compared. Verified v4 and
the current speaking mate are pixel-identical and remain the selected frame.

The emphatic opening is one connected lower mandible from rear hinge
`(462, 280)`. It follows the immutable upper bill on the same screen-right
axis, and its tip remains directly beneath and behind the upper tip without a
lateral jump, duplicate edge, detached sliver, or throat spill. Its
directional anatomy records a `0.9248` lower-to-upper reach ratio, `0.0113`
normalized tip offset, and mandible connected ratio `1.0`. The strict audit
reports 8,881 changed rendered mouth pixels, outside-mouth mean difference
`0.0`, registration delta `0`, and silhouette IoU `1.0`. The larger aperture
matches the emphatic performance while the crown, eyes, cheek plates, throat,
raised wings, hoodie, body, feet, scale, canvas, and upper bill remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-023-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 21
internal passes, 43 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 24 isolated polite-interruption review

Pair 24 (`polite-interruption`) was reviewed independently at native size,
nearest-neighbor enlarged beak scale, full-projector size, and in a six-second
closed/open loop. The canonical speaking mate, verified v7, rejected v3/v4,
donor v5/v6, procedural v4, preserved sources, and pairwise renders were
compared. Verified v7 and the current speaking mate are pixel-identical and
remain the selected frame.

The screen-right upper bill remains immutable while one lower mandible rotates
from the rear hinge. The gape has one connected cavity and the lower tip stays
beneath and behind the upper tip without a lateral jump, duplicate contour,
detached sliver, throat spill, or facial registration shift. The directional
anatomy records an `18.4149` degree opening and connected-mandible ratio `1.0`.
The strict audit reports 3,576 changed rendered mouth pixels, outside-mouth
mean difference `0.0`, registration delta `0`, and silhouette IoU `1.0`. The
crown, eyes, cheek plates, throat, raised wing, hoodie, body, feet, scale,
canvas, and upper bill remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-024-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 22
internal passes, 42 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 25 isolated hand-over-the-floor rebuild

Pair 25 (`hand-over-the-floor`) failed its fresh enlarged review. The active
v7 mate visibly stopped short of the upper-bill tip even though the legacy
numeric report classified it as tip-locked. Inspection showed that the old
extent check had included throat and body pixels in the mandible measurement,
creating a false pass. The closed frame, v5 through v7 candidates, prior
rejected frames, pairwise renders, and raw render were compared before the
mate was rebuilt.

A new full-size open-bill render was produced for this pair only and treated
strictly as a donor. Candidate v11 composites only its narrow lower bill and
mouth cavity onto the immutable closed frame; none of the generated body is
used. The upper bill remains fixed, the lower bill rotates from the authored
rear hinge, and its tip ends naturally beneath and slightly behind the upper
tip. Directional anatomy records a `0.9459` lower-to-upper reach ratio,
`0.2231` normalized tip offset, `13.2703` degree opening, and `0.998396`
connected-mandible ratio. The strict audit reports 1,540 changed rendered
mouth pixels, outside-mouth mean difference `0.0`, registration delta `0`,
and silhouette IoU `0.997888`. The eye, crown, cheek, throat, hoodie, body,
feet, scale, canvas, and extended presenting wing remain fixed.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-025-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 23
internal passes, 41 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero.

### Pair 26 isolated warm-welcome review

Pair 26 (`warm-welcome`) was reviewed as one independent closed/open job at
native size, nearest-neighbor enlarged beak scale, on a white field, at full
projector size, and in a six-second alternating loop. The canonical speaking
mate and verified v5 are pixel-identical. The earlier source and candidates
v3 and v4 were retained for comparison, but no generated body pixels were
introduced during this review.

The accepted opening remains centered beneath the immutable frontal upper
bill. Both mouth corners stay fixed, one connected lower mandible opens on the
same centerline, and the alternation shows no lateral jump, duplicate contour,
cheek drift, throat spill, or body-registration shift. The prior receipt had
incorrectly classified this frontal pose as right-facing directional anatomy.
That metadata was corrected to a separate centered frontal hinge `(482, 214)`
without changing the accepted image pixels. The frontal gate records a
`0.0909` center-offset ratio, `0.6364` lower-to-upper width ratio, and connected
mandible ratio `1.0`. The strict audit remains 646 changed articulation pixels,
outside-mouth mean difference `0.0`, registration delta `0`, and silhouette
IoU `1.0`.

Full-size evidence:

`assets/reference/characters/kingfisher/legacy-pairs-v1/evidence/pairwise-full-size/pair-026-one-pair-2026-08-07-v4/`

This is an internal visual pass only. The reopened queue now contains 24
internal passes, 40 pending observable pairs, and 2 not-observable rear views.
User approval and runtime admission remain zero; Pair 27 is the next isolated
hard stop.
