# Thorne Vale Worksheet Generation Record

Status: nine-sheet canonical production package generated and visually inspected, 2026-07-14.

Mode: built-in GPT Image generation using `canonical-voxel.png` as the sole production visual reference. The historical source was preserved and used only to document derivation. All accepted outputs were copied from the Codex generated-images store into `assets/reference/personas/thorne-vale/canonical-worksheets/`.

## Derivation chain

1. Historical source: `source-reference.png`, SHA-256 `ad40f76a8b086711f3b3b44dcca63c8829a96e665fb15d5cedf588301e8e77d8`.
2. Approved cleaned canonical: `canonical-voxel.png`, SHA-256 `13a8eca0379f2957174fa48c44bd9d2342a22ad06c92952f5f915867a6bb9599`.
3. Identity lock and uncertainty log freeze production interpretation.
4. Nine canonical worksheets below provide human-readable pose and articulation authorities.
5. Runtime implementers must isolate exactly 124 cells and reconstruct them as transparent colored-node pixel graphs; the PNGs are never runtime render assets.

## Sheet inventory and panel mappings

### 01 Identity — `01-identity-sheet-v3.png`

SHA-256: `ca1e46c7d0a8e9a5a2578a06bbf7e8dc92a16237744528ef39ba1dc1e57d6e21`.

4x4 row-major: neutral front; front three-quarter with safe vertical sword; strict left profile; exact back; full-body face/crown/mustache invariant; back-three-quarter crown/hair invariant; wardrobe invariant; boot/crown side invariant; parchment held at torso; parchment safely offered; open left hand; open right hand; proportion-neutral front; palette/material full-body reference; guarded policy stance with sword low; restrained parchment approval.

`01-identity-sheet-v1.png` is rejected because its 2x2 callout layout does not provide 16 deterministic extraction cells. `01-identity-sheet-v2.png` is rejected because cell 5 is a floating head and cell 14 changes the gold jacket to brown. V3 is authoritative: all 16 cells are complete full-body silhouettes with the canonical gold jacket.

### 02 Turnaround — `02-turnaround-sheet-v1.png`

SHA-256: `92c43a81e2bcac5e51e082f36c081087893140a866510cf85c92197bbdbafbc8`.

4x2, left-to-right: front; front three-quarter left; left profile; back three-quarter left; back; back three-quarter right; right profile; front three-quarter right.

### 03 Neutral bases — `03-neutral-base-poses-v1.png`

SHA-256: `0ee8ba06372fa1e496e558bc49faff2db6787a24e0a421b653280755de9186bf`.

4x2: neutral front; neutral front three-quarter; neutral left side; neutral back; relaxed idle; attentive idle; speaking idle; listening idle.

### 04 Full-body expressions — `04-full-body-expression-sheet-v1.png`

SHA-256: `1ce2066dddb667679718c0349a06d3ee9aa231cc23329fc2da1e010364f28502`.

6x4: neutral, calm, joy, amusement, excitement, curiosity; confidence, compassion, surprise, confusion, skepticism, concern; sadness, shame, embarrassment, fear, anxiety, anger; frustration, determination, fatigue, contemplation, guarded approval, firm disapproval.

### 05 Full-body visemes and blinks — `05-full-body-viseme-blink-sheet-v1.png`

SHA-256: `d2756c28f7a2ea1d80e9991ef10e0609cba9cf879164580c277ed091edf16304`.

4x4: rest/open eyes, closed lips, slightly open, wide vowel; open vowel, rounded vowel, teeth consonant, lower-lip consonant; tongue consonant, speaking smile, speaking frown, emphasis; breath/pause, half blink, full blink, reopen/settle.

### 06 Hands and props — `06-hand-prop-sheet-v1.png`

SHA-256: `c48b6a4c06b9757bc526fec89fff90a4680ea603b9dbff4e6158354c7e70a649`.

4x4: open relaxed, closed relaxed, fist, point; presenting palm, grip, upright sword, rolled parchment; reach, two-hand policy presentation, sword guard low, formal sword upright; scroll read, tradeoff comparison, risk-review point, guarded approval.

### 07 Grounded motion — `07-grounded-motion-sheet-v2.png`

SHA-256: `b5bf4b4617e136d54debdeb90758fc4dffecc70e82d92ec85908fee30606cf9f`.

4x4 row-major: walk-left contact; walk-left passing; walk-right contact; walk-right passing; run reach; run drive; start anticipation; stop recovery; planted-left-foot turn left; planted-right-foot turn right; deep crouch; jump anticipation; jump airborne; controlled fall; landing contact; landing recovery.

V1 is rejected from production mapping because it substituted extra run and turn frames for required start, stop, jump-anticipation, and landing-recovery keys. V2 contains the complete required arc and visibly opposite planted turns.

### 08 Signature actions — `08-signature-actions-sheet-v1.png`

SHA-256: `a66308fd38a35816dbe18a4c3eec9021b70784c54f934e862a3cc16a717ad793`.

4x4, four action arcs: decision-rights ruling; tradeoff comparison; risk review/policy presentation; incentive analysis/guarded approval. Each row is ordered anticipation, primary action, follow-through, recovery.

### 09 Open/closed/fist/reach articulation — `09-articulation-open-closed-fist-reach-v1.png`

SHA-256: `970e50296c47fc81c2180f1eae43a024ad5451b8a6d2dee4ca617e87f1c85ae3`.

2x2: both hands open; both fists; forward reach; asymmetric present/open plus closed relaxed hand.

## Visual inspection record

- All nine requested accepted sheet types are present as integer-divisible contact sheets totaling exactly **124 cells**: 16 + 8 + 8 + 24 + 16 + 16 + 16 + 16 + 4.
- Full-body production panels retain crown-to-boot silhouettes; no accepted panel is a portrait-only replacement.
- Crown, green eyes, mustache, gold coat, white shirt, belt/buckle, tan trousers, brown boots, adult proportions, voxel scale, blue studio logic, sword, and parchment remain recognizable throughout.
- Turnaround includes all eight required views with a coherent rear interpretation.
- Ground motion includes planted turning poses and complete crouch/jump/fall/landing states.
- Expression, viseme, blink, hand, prop, and signature sheets use the body as well as face or hand detail.
- No cigar, cigarette, pipe, smoke, throne, cape, armor, shield, jewelry, extra character, or unapproved prop appears in the accepted package.
- Sword tips, parchment edges, crown tips, hands, and boots remain inside their panel boundaries.

## Prompt set summary

Every prompt repeated the complete immutable identity, high-detail 3D voxel style, blue studio environment, full-body requirement, stable scale/baseline/camera, safety margins, approved sword/parchment constraint, and forbidden smoking/royal-invention list. Sheet-specific prompts supplied exact grid dimensions and ordered mappings. Grounded motion explicitly required planted turns; signature actions explicitly supplied four-frame anticipation/action/follow-through/recovery arcs.

## Runtime conversion gate

Before animation is reconnected, process all 124 accepted cells. Remove each cell background, isolate its pose/reference silhouette, create one transparent pixel graph per cell, and store colored pixel nodes/runs only—never PNG or SVG runtime render assets. The visualizer projector paints graph pixels onto canvas for each frame. Re-audit all 124 isolated silhouettes and all 124 pixel graphs against the canonical identity, exact mapping, pose-local bounds, stable root/baseline, four-cell safety inset, and zero clipped crown/boot/hand/sword/parchment bounds. Only graph records that pass this 124/124 + 124/124 gate may connect to animation. Reject rather than silently approximate identity, costume, prop, scale, contact, or baseline drift.
