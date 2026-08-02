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

## Verification

Focused generated-overlay compositor tests: 7 passed. The added regression
proves generated cavity texture is applied after canonical upper-bill
restoration without changing legacy `solid` or `generated` behavior.

Complete Kingfisher-focused suite after the pair 41 rebuild: 69 passed, six
subtests passed, in 11.20 seconds. The reviewer UI tests are included in that
run. Pillow emitted only known `getdata` deprecation warnings.

The strict verifier intentionally exits nonzero until all observable pairs
pass and all rear views are explicitly `not_observable`. It writes a structured
failure receipt even while blocked:

`assets/reference/characters/kingfisher/legacy-pairs-v1/review-evidence/pair-review-verification.json`

Current blocker:

`pair 42 lacks a passing full-size pairwise disposition`

Current review artifact:

`kingfisher_act_001_066_111_176_pair_review-c2b63e74d76cc758.wjpose`

Artifact SHA-256:

`c2b63e74d76cc758d9db00a562817b0e5ba518bffcfde7d2809b591a4b202f15`

Library-index SHA-256:

`854a5ec00927b93417a658a032caab70ea453767ed2867a5f8c1e58a37952b59`

Queue state: 39 internal full-size passes, 24 pending, 1 needs rebuild, and
2 not observable. Runtime-admitted and user-approved counts remain zero.

This failure is expected and proves the queue is fail-closed.
