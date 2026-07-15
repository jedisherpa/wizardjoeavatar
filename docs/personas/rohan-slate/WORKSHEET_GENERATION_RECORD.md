# Rohan Slate — Canonical Worksheet Generation Record

Status: 124 accepted deterministic cells, visually audited. Generation used the built-in GPT Image workflow with `canonical-voxel.png` as the highest visual authority and the accepted identity sheet as a secondary lock. Approved sheets were normalized to 1260 × 1260 RGB PNG so every grid divides to integer cell geometry.

## Immutable input verification

| File | SHA-256 |
| --- | --- |
| `assets/reference/personas/rohan-slate/source-reference.png` | `b3711407b803d432c97233ec9680d5e394f8f109839265a3e03259aa890741e6` |
| `assets/reference/personas/rohan-slate/canonical-voxel.png` | `9669b00c83e1f7bc57b25b4611a440a4b3a1f6de12a1253c37de8158709b0114` |

Both files remained byte-for-byte unchanged after generation and normalization.

## Accepted sheets, geometry, mappings, and hashes

All mappings are row-major. The total is exactly `16 + 8 + 8 + 24 + 16 + 16 + 16 + 16 + 4 = 124` cells.

### 01 — Identity references

- File: `01-identity-sheet-approved-v1.png`
- Grid: 4 × 4 = 16; each cell 315 × 315 px
- SHA-256: `2215dc58e8eafecaff1992640851612b416d7bb2f1a62829e5a8d8cacb8b088b`
- Cells: 01 neutral front empty hands; 02 neutral front holding meter; 03 relaxed three-quarter left; 04 relaxed three-quarter right; 05 left profile; 06 right profile; 07 back three-quarter left; 08 back three-quarter right; 09 attentive front; 10 listening with meter lowered; 11 presenting open hand; 12 practical pointing; 13 meter scan; 14 tool-belt reach; 15 safety-stop palm; 16 settled neutral.

### 02 — Eight-view turnaround

- File: `02-turnaround-sheet-approved-v1.png`
- Grid: 4 × 2 = 8; each cell 315 × 630 px
- SHA-256: `de094d437ad783ef14af79c3501ce42750608ba65ddc531065168262d6e46eac`
- Cells: 01 front; 02 front three-quarter left; 03 left profile; 04 back three-quarter left; 05 back; 06 back three-quarter right; 07 right profile; 08 front three-quarter right.

### 03 — Neutral bases

- File: `03-neutral-base-poses-approved-v1.png`
- Grid: 4 × 2 = 8; each cell 315 × 630 px
- SHA-256: `5b44eb46f683deea314031fc9eb456c1dabed4591930d3ddf277deef692a5d6a`
- Cells: 01 neutral front; 02 neutral three-quarter left; 03 neutral left side; 04 neutral back; 05 relaxed idle; 06 attentive idle; 07 speaking idle; 08 listening idle with meter lowered.

### 04 — Full-body expressions

- File: `04-expression-sheet-approved-v1.png`
- Grid: 6 × 4 = 24; each cell 210 × 315 px
- SHA-256: `8851cdb367039e9d92c5512523a50671a5d5a42cafb21c469c94b3632e5fd70c`
- Cells: 01 neutral; 02 calm; 03 joy; 04 amusement; 05 excitement; 06 curiosity; 07 confidence; 08 compassion; 09 surprise; 10 confusion; 11 skepticism; 12 concern; 13 sadness; 14 shame; 15 embarrassment; 16 fear; 17 anxiety; 18 anger; 19 frustration; 20 determination; 21 fatigue; 22 contemplation; 23 neutral recovery; 24 attentive recovery.

### 05 — Full-body visemes and synchronized blinks

- File: `05-speech-viseme-sheet-approved-v3.png`
- Grid: 4 × 4 = 16; each cell 315 × 315 px
- SHA-256: `cd933e6566d518b10c5de69f58f122b2231aa7c2a78d1ad39b35ed0cb1598e19`
- Cells: 01 rest; 02 closed lips; 03 slightly open; 04 wide vowel; 05 open vowel; 06 rounded vowel; 07 teeth consonant; 08 lower-lip consonant; 09 tongue consonant; 10 speaking smile; 11 speaking frown; 12 emphasis; 13 breath/pause; 14 both eyes open; 15 symmetric half blink; 16 symmetric full blink.

### 06 — Full-body hands and meter

- File: `06-hand-prop-sheet-approved-v1.png`
- Grid: 4 × 4 = 16; each cell 315 × 315 px
- SHA-256: `7e66083113268ca1baf08b5f728ffffdfa1b8812c0e329f7e0b2bbca866a8ae2`
- Cells: 01 open relaxed hand; 02 closed relaxed hand; 03 fist; 04 practical point; 05 present; 06 reach; 07 meter grip; 08 meter scan; 09 meter lowered; 10 meter offered; 11 receive meter; 12 two-hand transfer; 13 stable two-hand hold; 14 readout emphasis; 15 release toward belt-side rest; 16 settled empty hands.

### 07 — Grounded motion

- File: `07-ground-motion-sheet-approved-v1.png`
- Grid: 4 × 4 = 16; each cell 315 × 315 px
- SHA-256: `d74ef406c6fca6d36ed6f6c4165ca88f6ae06f032b276c6312b7f6304f95906c`
- Cells: 01 walk contact left; 02 walk down/left support; 03 walk passing; 04 walk contact right; 05 run contact left; 06 run contact right; 07 start anticipation with rear boot planted; 08 braking stop with front boot planted; 09 turn left with left boot planted; 10 turn right with right boot planted; 11 crouch; 12 jump anticipation; 13 airborne jump; 14 fall; 15 landing contact; 16 landing recovery.

### 08 — Persona-specific action arcs

- File: `08-signature-actions-sheet-approved-v1.png`
- Grid: 4 × 4 = 16; each cell 315 × 315 px
- SHA-256: `243a406826cdfe1fc06f7c895e08c20764f9fc7162d75551fba4fc2a6ab8460a`
- Cells: 01 observe symptom; 02 inspect low cause; 03 meter-scan anticipation; 04 meter-scan reading; 05 indicate result; 06 safety-stop anticipation; 07 safety-stop hold; 08 safety-stop recovery; 09 reset anticipation; 10 precise meter reset; 11 watch-and-wait; 12 reset-success nod; 13 walkthrough direction; 14 wrench presentation; 15 call-qualified-help signal without phone; 16 settled ready with tools returned.

### 09 — Minimal interaction hand states

- File: `09-interaction-poses-approved-v1.png`
- Grid: 2 × 2 = 4; each cell 630 × 630 px
- SHA-256: `0aff8a8681e2dc25a1156969f64b4623bcd31b37ea87f1d8d4fb51d8b49d4c9e`
- Cells: 01 open; 02 closed; 03 fist; 04 reach.

## Visual audit: all 124 accepted cells

Each numbered cell above was inspected at contact-sheet scale and by row/column boundary. The audit checked complete silhouette, safety margin, full-body framing, identity, age, face, hair, beard, glasses, teal eyes, voxel scale, costume, belt/tool placement, approved prop use, limb count, hand readability, baseline logic, action distinction, and absence of labels or unapproved objects.

- Identity 01–16: **PASS 16/16**.
- Turnaround 01–08: **PASS 8/8**; all eight facings are distinct and back view has no invented face.
- Neutral 01–08: **PASS 8/8**.
- Expressions 01–24: **PASS 24/24**; all are full body and retain fixed identity.
- Viseme/blink 01–16: **PASS 16/16** on approved v3; cells 01–14 keep both eyes open, cell 15 is a symmetric half blink, cell 16 is a symmetric full blink.
- Hand/prop 01–16: **PASS 16/16**; only the approved diagnostic meter is held.
- Ground motion 01–16: **PASS 16/16**; cells 09–10 are opposite planted-foot turns, cells 12–16 form a readable jump/fall/land arc.
- Signature actions 01–16: **PASS 16/16**; no phone or invented device appears.
- Interaction 01–04: **PASS 4/4**.

Total visual audit: **124/124 PASS**. No accepted cell is a bust portrait or cropped silhouette.

## Rejected candidates

| File | SHA-256 | Rejection reason |
| --- | --- | --- |
| `rejected/05-speech-viseme-sheet-rejected-v1-wink.png` | `58a2ed9193981c949a929764a09df4e07957dd688d36c4828050db8e470a90fa` | Blink cell read as an asymmetric wink. |
| `rejected/05-speech-viseme-sheet-rejected-v2-eyes-closed-in-cell-2.png` | `b24be06482cceb0f17b293d6bbe5b528a3cd17f163e76684c0224549455b2a95` | Closed-lips viseme incorrectly closed both eyes. |

Rejected candidates are evidence only and must never enter cell extraction or runtime manifests.

## Mandatory 124-cell runtime handoff

The worksheet PNGs are reference and extraction inputs only. Runtime rendering must follow this sequence exactly:

1. Slice only the nine approved sheets at the documented integer cell boundaries, producing exactly 124 isolated source cells in the documented row-major order.
2. Remove each cell's pale-cyan sheet/background independently. Preserve the full character, props, internal color regions, and voxel-edge antialiasing while eliminating ground/contact shadows and all exterior background.
3. Normalize every isolated silhouette to the character package's canonical canvas, stable root, baseline, and pivot rules with the required transparent safety inset. Do not rescale cells independently in a way that changes body size.
4. Convert each isolated pose into its own **transparent pixel graph**.
5. Store only colored pixel nodes/runs and graph metadata in the direct-cell pose library. **Never store or load PNG or SVG render assets at runtime.**
6. The visualizer projector paints those colored pixel nodes/runs onto its canvas for every animation frame.
7. Before reconnecting any animation graph, re-audit **all 124 isolated silhouettes** for clipping, background remnants, identity drift, scale, root, baseline, pivots, and prop integrity.
8. Separately re-audit **all 124 transparent pixel graphs** against their isolated silhouettes for exact color/run coverage, bounds, alpha holes, and attachment anchors.
9. Reconnect animation only after both gates report 124/124 PASS. Any failed silhouette or graph remains disconnected and cannot silently fall back to a reference PNG/SVG.

## Validation evidence

- Nine accepted PNGs decode as 8-bit RGB PNG at 1260 × 1260.
- Every grid dimension divides the raster exactly: 4 × 4 → 315 × 315; 4 × 2 → 315 × 630; 6 × 4 → 210 × 315; 2 × 2 → 630 × 630.
- Accepted deterministic cell count is exactly 124.
- Original and canonical hashes match the pre-generation hashes recorded above.
- Runtime assets were intentionally not created in this worksheet-only phase.
