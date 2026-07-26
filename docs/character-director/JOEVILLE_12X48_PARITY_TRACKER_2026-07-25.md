# JoeVille 12x48 Motion Parity Tracker

Date: 2026-07-25

## Scope

This checkpoint freezes the source census and approval boundary for the three
user-supplied sprite archives:

- `Sprites 1.zip`
- `Sprites 2.zip`
- `Sprites 3.zip`

The target is 48 transparent, canonical-canvas motion poses for each of the 12
JoeVille authority-roster characters. Source discovery is not visual approval,
package compilation, or runtime admission.

The work is isolated on `codex/joeville-12-parity`. The preserved Serena
successor and Prism connector worktrees are not modified by this intake.

## Repeatable Receipts

Run:

```bash
python3 tools/census_joeville_sprite_archives.py \
  "/Users/paul/Downloads/Sprites 1.zip" \
  "/Users/paul/Downloads/Sprites 2.zip" \
  "/Users/paul/Downloads/Sprites 3.zip" \
  --output assets/reference/joeville_48_parity/source-metadata/archive-census-v001.json

python3 tools/build_joeville_48_parity_tracker.py \
  assets/reference/joeville_48_parity/source-metadata/archive-census-v001.json \
  --output assets/reference/joeville_48_parity/source-metadata/parity-tracker-v001.json
```

The census records archive and member hashes, decoded formats, dimensions,
image modes, alpha statistics, character ownership, sequences, and cross-pack
collisions. The parity tracker expands each authority character into 48
individually gated slots.

## Source Findings

- Three archives and 116 image members passed direct ZIP/Pillow decoding.
- Every member is a lossy VP8 WebP payload despite its `.png` filename.
- Every member is RGB. The apparent transparency is a baked near-white
  checkerboard; no source alpha channel exists.
- Each numbered `g`, `w`, or `p` sheet contains six horizontally arranged
  silhouettes.
- Fixed equal-width slicing is prohibited. Wide poses, wings, hair, props, and
  effects cross nominal cell boundaries.
- Background removal must preserve enclosed white clothing, eyes, teeth,
  highlights, microphones, books, and detached props.

## Coverage

| Character | Unique selected source slots | Missing authored slots | State |
| --- | ---: | ---: | --- |
| Serena Quill | 48 | 0 | Source-complete |
| Aurelia Finch | 42 | 6 | Supplemental strip requires deduplication; one six-pose sequence still missing |
| Selene Hart | 36 | 12 | Two six-pose sequences missing |
| Thorne Vale | 36 | 12 | Two six-pose sequences missing |
| Elara Voss | 36 | 12 | Two six-pose sequences missing |
| Kai Renner | 36 | 12 | Two six-pose sequences missing |
| Mira Solen | 48 | 0 | Source-complete |
| Draven Holt | 36 | 12 | Two six-pose sequences missing |
| Liora Kane | 36 | 12 | Two six-pose sequences missing |
| Rohan Slate | 36 | 12 | Two six-pose sequences missing |
| Finn Calder | 36 | 12 | Two six-pose sequences missing |
| Orion Vale | 36 | 12 | Two six-pose sequences missing |
| **Total** | **462** | **114** | **576 target slots** |

Aurelia's nine-pose strip overlaps earlier gait material. It is retained as
supplemental evidence but fills zero parity slots until pose-level
deduplication proves distinct motion. No repeated or near-duplicate pose may be
used as padding.

## Conflict Decisions

Three same-name members contained different artwork. Archive order is not
authority. Full-size visual review froze these winners:

| Character / sequence | Selected source | Selected member SHA-256 | Reason |
| --- | --- | --- | --- |
| Elara Voss `g3` | Sprites 3 | `e80460703d5d63a528a1f2ed39be1c8f244197ba46d9130c6ea6b8936d819957` | Microphone remains correctly held throughout the sequence |
| Liora Kane `g5` | Sprites 2 | `e5f9d614ab8bfc4fca38c5fb0a92d27758b4cd35bdf8ba0583e9aeae11776f8a` | Restores Liora's book and matches her surrounding authored vocabulary |
| Rohan Slate `g1` | Sprites 2 | `4ad839e30dee52f6e31c1be6a2969b7094a22121dabfb3d187958327efa85808` | Cleaner corrected gait progression |

All displaced variants remain hash-visible in the census and tracker. They are
not deleted or silently overwritten.

## Admission Gates

Every one of the 576 slots must independently preserve:

1. Source archive, member, and selected-variant identity.
2. Character identity and authored sequence/frame index.
3. A complete silhouette with detached owned components.
4. Transparent alpha without checkerboard residue or erased light details.
5. Canonical 1254x1254 canvas, baseline, margins, and stable scale.
6. Raw RGBA SHA-256 and deterministic rebuild evidence.
7. Full-size visual-parity approval.
8. Semantic role, contacts, transitions, and interruption behavior.
9. Package-local `.wjpose`, graph, profile, and capability bindings.
10. Product approval against exact artifact and package hashes.

The default for every slot is `runtime_admitted: false`.

The generic persona/character/package admission protocol now exists in
`CHARACTER_ADMISSION_CONTRACT_V1.md`. That protocol is an available release
gate, not an automatic promotion: none of these alternate libraries has been
added to the production registry.

## Compiled Source Checkpoint

All 462 supplied authority-roster poses have now been reconstructed as
transparent 1254x1254 RGBA pixel graphs and stored in character-local
`.wjpose` artifacts. The source sheets are provenance inputs only; the
projector decodes and paints RGBA records from these artifacts.

| Character | Compiled poses | Artifact SHA-256 | State |
| --- | ---: | --- | --- |
| Serena Quill | 48 | `e9059d646a778a1684f090c14bf32bfe737f2bc093d1526a07c1f4d43b6fdc51` | Candidate visual parity |
| Aurelia Finch | 42 | `66efd7f3450e768ef3ec5426ff590aaddfc83d26838ad42c29689faf8eeb5f8d` | Candidate source partial |
| Selene Hart | 36 | `15679165338fd94a38188172d7532c23514918edf8a99e7656994f77c51ae8ad` | Candidate source partial |
| Thorne Vale | 36 | `c48f3ccaea95580c41ca70dd6a9a3fd43fe232278875db3ccd02e9406f84cb82` | Candidate source partial |
| Elara Voss | 36 | `d68194459adb3dd095bcec159a005cbb5276adf82bfc312af2c2ce3f5cfed858` | Candidate source partial |
| Kai Renner | 36 | `7b73ec39dc91c0b1ac50e444bd786c893687880645b59ca6cc26b6f27b9d69e1` | Candidate source partial |
| Mira Solen | 48 | `34b19008f97fa081da6a138432b397e69529e5b7ed9a13c33eeeceaa192bac0f` | Candidate visual parity |
| Draven Holt | 36 | `244627668d46ad2c552d2ec2d7f5d24ce4ef4750c3a423d097bee1929c01e724` | Candidate source partial |
| Liora Kane | 36 | `7b98b6ce927ab24457920b7e3d15a0b87e3e3d456a3af11ab339ada160ca03a7` | Candidate source partial |
| Rohan Slate | 36 | `32e480baa58081811621cceac92c9cf7ada6c0d958afe390ab3eaedadce32def` | Candidate source partial |
| Finn Calder | 36 | `6172d80b6003c57317a4139fef8180a631752e91ff4d21e0f958cde0165a86f1` | Candidate source partial |
| Orion Vale | 36 | `e621945a608fd599f7a277fe4dd54e05886667795addb853485f06cc7fb804c9` | Candidate source partial |
| **Total** | **462** | | **114 authored poses remain** |

Each character has a reconstruction manifest, pose-level RGBA hashes, source
archive/member hashes, normalization measurements, a review contact sheet,
and a review-only library index under
`assets/reference/joeville_48_parity/`. Serena and Mira were rebuilt twice
with identical artifact and library-index hashes.

The persistent observer at `http://127.0.0.1:8665/` keeps approved HD Wizard
Joe on the left and the character currently under work on the right. The
alternate projector accepts only indexes with `review_projection: true` and
`runtime_admitted: false`; admitted indexes fail closed.

## Authored Parity Progress

Orion Vale was the first incomplete roster character to reach a complete
48-pose review candidate. His immutable supplied poses `001`-`036` were merged
with 12 new full-size RGBA poses for:

- `g7`: listen, consider, explain, and recover.
- `g8`: alert, hold, boundary, verify, redirect, and grounded exit prep.

The build preserves the supplied 36 RGBA records byte-for-byte. New inputs are
canonical 1254x1254 transparent PNG authoring sources; the projector reads the
compiled `.wjpose`, not those PNGs. Two clean-directory builds produced
matching artifact, index, contact-sheet, reconstruction, and motion-contract
hashes. All 12 new poses passed individual full-size projection on port 8665.
Product visual approval is still pending and runtime admission remains false.

Aurelia Finch is now the second incomplete roster character to reach a
complete 48-pose review candidate. Her immutable supplied poses `001`-`042`
were merged with six new full-size RGBA poses for a book-centered communication
sequence:

- `g7`: receive, raise the source, consult, verify a passage, explain, recover.

Two consecutive builds produced matching artifact and library-index hashes.
All six authored poses passed individual full-size projection on port 8667.
Port 8665 now presents the complete candidate beside approved HD Wizard Joe.
Product visual approval is still pending and runtime admission remains false.

Selene Hart is now the third incomplete roster character to reach a complete
48-pose review candidate. Her immutable supplied poses `001`-`036` were merged
with twelve new full-size RGBA poses for:

- `g7`: receive, raise, frame, indicate, explain, and resolve with the hoop.
- `g8`: establish a visible standard, set a calm boundary, verify, redirect,
  and hand off.

The individual full-size gate rejected five damaged soft-matte intermediates.
Those frames were extracted again with a hard key and rebuilt before technical
acceptance. Two consecutive corrected builds produced matching artifact and
library-index hashes. Port 8665 presents the corrected candidate beside
approved HD Wizard Joe. Product visual approval is still pending and runtime
admission remains false.

Thorne Vale is now the fourth incomplete roster character to reach a complete
48-pose review candidate. His immutable supplied poses `001`-`036` were merged
with twelve new full-size RGBA poses for:

- `g7`: receive, invite, listen, weigh, acknowledge, and reopen.
- `g8`: retrieve, open, inspect, verify, close, and commission with one scroll.

The prop-continuity gate rejected a duplicated-scroll intermediate. Canonical
placement rejected two oversize silhouettes, and dark-background review found
a thin chroma fringe. All affected frames were corrected before the final
deterministic rebuild. Port 8665 presents the corrected candidate beside
approved HD Wizard Joe. Product visual approval is still pending and runtime
admission remains false.

Elara Voss is now the fifth incomplete roster character to reach a complete
48-pose review candidate. Her immutable supplied poses `001`-`036` were merged
with twelve new full-size RGBA poses for:

- `g7`: receive, offer, listen, reclaim, clarify, and invite.
- `g8`: intake, headline, first fact, compare, conclude, and sign off.

Microphone ownership remains continuous in one dedicated hand and both heels
remain grounded. Dark-background review rejected a chroma-fringe intermediate.
Seven slightly oversize silhouettes were then edge-contracted and reduced by
3.1-3.9 percent through the explicit receipted path; the canonicalizer's strict
default was not weakened. Port 8665 presents the corrected candidate beside
approved HD Wizard Joe. Product visual approval is still pending and runtime
admission remains false.

Kai Renner is now the sixth incomplete roster character to reach a complete
48-pose review candidate. His immutable supplied poses `001`-`036` were merged
with twelve new full-size RGBA poses for:

- `g7`: receive, welcome, listen, confirm, acknowledge, and reopen a
  counter-service exchange.
- `g8`: collect, frame, identify, compare, show precision, and offer a
  craft-quality explanation.

The authored silhouettes preserve the `BAKE` cap, rectangular glasses, beard,
mustard sweater, cobalt jeans, and grounded black shoes without introducing
props. Three oversize frames were reduced by 1.4-1.9 percent through the
explicit receipted path; the strict canonicalizer remains unchanged. Two
consecutive builds produced identical artifact and library-index hashes. All
twelve authored IDs passed direct full-size projection and port 8665 presents
the candidate beside approved HD Wizard Joe. Product visual approval is still
pending and runtime admission remains false.

Draven Holt is now the seventh incomplete roster character to reach a complete
48-pose review candidate. His immutable supplied poses `001`-`036` were merged
with twelve new full-size RGBA poses for:

- `g7`: receive, grant the floor, listen, probe, assign, and confirm a
  foreman status exchange.
- `g8`: detect, stop, contain, reroute, verify, and release a site-safety
  intervention.

Exactly one checklist clipboard and pencil remain continuously owned by
Draven's left hand while the free right hand performs every gesture. All
twelve oversize silhouettes were reduced by 0.18-3.96 percent through the
explicit receipted path; the canonicalizer's strict default remains unchanged.
Two consecutive builds produced identical artifact and library-index hashes.
All twelve authored IDs passed direct full-size projection and port 8665
presents the candidate beside approved HD Wizard Joe. Product visual approval
is still pending and runtime admission remains false.

Liora Kane is now the eighth incomplete roster character to reach a complete
48-pose review candidate. Her immutable supplied poses `001`-`036` were merged
with twelve new full-size RGBA poses for:

- `g7`: notice, invite, receive, empathize, offer support, and return agency.
- `g8`: frame a question, open the source, locate a passage, realize, share an
  insight, and close while retaining one blue book.

The authored silhouettes preserve Liora's long brown curls, gray hoodie,
drawstrings and pockets, teal plaid trousers, grounded white shoes, and warm
voxel proportions. Exactly one blue book remains continuously owned throughout
G8. Poses `042`, `043`, and `045` use integer translation only; the remaining
authored silhouettes use the explicit receipted oversize-fit path with a
minimum scale of 97.13 percent. Two consecutive builds produced identical
artifact and library-index hashes. All twelve authored IDs passed direct
full-size projection and port 8665 presents the candidate beside approved HD
Wizard Joe. Product visual approval is still pending and runtime admission
remains false.

Rohan Slate is now the ninth incomplete roster character to reach a complete
48-pose review candidate. His immutable supplied poses `001`-`036` were merged
with twelve new full-size RGBA poses for:

- `g7`: register, check, state, define, allow, and resolve a measured boundary.
- `g8`: frame, compare, locate, propose, confirm, and commit to a practical
  collaborative decision.

The authored silhouettes preserve Rohan's warm dark-brown skin, charcoal
ribbed beanie, dark rectangular glasses with teal eye accents, short beard and
mustache, white open-collar shirt, forest-green trousers, and brown boots. A
first-principles canonicalization correction aligns asymmetrical gestures by
their bottom support band rather than their full silhouette. All twelve frames
remain at scale `1.0`, use no resampling, land on baseline `1185`, and hold
their support center within one pixel of canvas center. Two consecutive builds
produced identical artifact and library-index hashes. All twelve authored IDs
passed direct full-size projection and port 8665 presents the candidate beside
approved HD Wizard Joe. Product visual approval is still pending and runtime
admission remains false.

| Character | Candidate poses | Missing poses | State |
| --- | ---: | ---: | --- |
| Orion Vale | 48 | 0 | Full-size technical review passed; product visual approval pending |
| Aurelia Finch | 48 | 0 | Full-size technical review passed; product visual approval pending |
| Selene Hart | 48 | 0 | Full-size technical review passed; product visual approval pending |
| Thorne Vale | 48 | 0 | Full-size technical review passed; product visual approval pending |
| Elara Voss | 48 | 0 | Full-size technical review passed; product visual approval pending |
| Kai Renner | 48 | 0 | Full-size technical review passed; product visual approval pending |
| Draven Holt | 48 | 0 | Full-size technical review passed; product visual approval pending |
| Liora Kane | 48 | 0 | Full-size technical review passed; product visual approval pending |
| Rohan Slate | 48 | 0 | Full-size technical review passed; product visual approval pending |
| Remaining roster | 132 | 12 | Finn Calder authoring/review required; Serena Quill and Mira Solen are source-complete |
| **Total** | **564** | **12** | **576 target slots** |

Orion candidate receipts:

- Artifact: `53b769a5a6c1ef2ed9c129e750699614f4ed3d87cd21436ada4e0cd60bdd70ab`
- Library index: `4e2333aedde7d48edae5b9431c97f275d4aeab38441211a6fdaa26c87a93a943`
- Reconstruction: `9bdeabec0c0691d9b8bee258932ed80927605b16ebc5c9458369c85cde2f89df`
- Review motion contract: `ce5ebba539f5511ba70e089e4e9840ce22b536fd0a039eb7f37edbf09fed1738`
- Contact sheet: `389f03a1a742366df723510809be0d1466699976fa768c73ad8444b60b3e0271`

Aurelia candidate receipts:

- Artifact: `e7e44013b9356720357e9dc0114909ddaadee34a3e26d2de666751b7e7d136ad`
- Library index: `b4d19c01b0771a1ed49a52c42051a4a82c9e347efc6152d9023b2656f596e9b1`
- Reconstruction: `74aaaef9de21cca18429eb87d9bde97491bf0ef650b4eecbc8ba8cca803c549f`
- Review motion contract: `51057a8f201423174447c502d6760ec164c50e0141ff212e7bf929895ad42d4b`
- Contact sheet: `83b4b403d428950ebad8dad967d1a08df255ea60732a3285848dee8eb0b219b0`

Selene candidate receipts:

- Artifact: `1e9b791070658d79d1a517557c819d900d5c656429f3b643bb268e2fe4374781`
- Library index: `86f5ff6587bf1714991e8a0ac66d40007bc25b5c5a0ecef0a960e5f7a12439b4`
- Reconstruction: `22ede6b8587d329a30d80fcf40f8d99bfa48e04ffc72428b4aa2562b9e077f39`
- Review motion contract: `8ca2f01db315099fd2c469a750c54a421201b29521440c0304a73bc7d3869075`
- Contact sheet: `fe3cffec7b288b0d24b0b7b708e169bdaa6d2c7cf0dbab375997f15740a4c730`

Thorne candidate receipts:

- Artifact: `787f6745558e2d33683c42ea84a7b81b5883ea8192862d921b917de1b26a67cc`
- Library index: `937abf76db2da70cb85d36237b9124a2e5dd59b3bfc19f240563e20a71abcde2`
- Reconstruction: `a57b7886f20b0a2fd18af8fc7fe4df95bccb127075bf84e902ffb158d1ace54c`
- Review motion contract: `1c403584f625f1e533538c516c7e00fc803b8dfbc8623e7b3379afd6149bb037`
- Contact sheet: `e46389068cf2f9faa0374b2dbe84799b293a100214a64748c6d952e9866c8646`

Elara candidate receipts:

- Artifact: `8fd74202c038028af63e6fff9a9e8b8c2d82261bc3e30b5d2447a93af632f53c`
- Library index: `7fd020cb347ec6726e1dd60939166d9659775fe626ce8511108f38441708bde2`
- Reconstruction: `7405ceedb3936dcb7571b1e4b8ea56bcbf1a8a9470f2760c52155cdf58ec796e`
- Review motion contract: `a24a1597aad39c522b3f77356ca141e427fa3b8b8f8b022fcffc19072a697b0b`
- Contact sheet: `fcef489937907925a0db255fcfedce3480f87a87367ee20638f0fe642f361b7a`
- Canonicalization receipts: `ec5b6f4ed2410c0f0afc56a79c3c0811ab1554f372221488f3e70da5306c5dfb`

Kai candidate receipts:

- Artifact: `2e15a54fda170005919711a0d9177253880cd169cd5d300349845d6b48569873`
- Library index: `768854f8c57528f51768198bc126d75dd61199cd372b6abca41e2aa8a35ab980`
- Reconstruction: `f300216c7c571cf29bc488bf939e9ca0d4d0bc4483964e56f44671e5413a32b8`
- Review motion contract: `0e4c99b1c398f7666362e26992b9e8be2d2206d66dcab697207eead2796580be`
- Contact sheet: `2ec923cf6b3bc0ea45eee4d6bf065feb0f39fdfa5e35e6bc74f885da0e95bfe2`
- Alpha-extraction receipts: `46c6c458f911423bb244df328b1780fd4a54b1b0a506d80d38f4e150f88f1828`
- Canonicalization receipts: `3249ece047e6c14330aae17d162de8de24383be5e18591ab222c07cd78c7ce31`

Draven candidate receipts:

- Artifact: `ac51bba7f40bd42b374857b3070d62716f878894b99190d76cd434f08a843e82`
- Library index: `6fc822bf34011fa0d3e110a1c261851c04ceadab35184e9e95db378b11ce0069`
- Reconstruction: `0aecf781a48b5bc4862cc6ce50a29fb2a91406a7ebe2f6941e9bfe604f08eebe`
- Review motion contract: `10a9678fdcc13a902f7ad32c000e1ac3bfd8d5904c14b3e15903510c746b98b4`
- Contact sheet: `b40ffd132a58e8e69bf5d7a93e1fdbce6a72d482c88966282399e6396451d797`
- Alpha-extraction receipts: `23cb83653f8a9de2bc4c71f96c6d303d732c481c868e883a136022c29789de26`
- Canonicalization receipts: `b6ed2386bb2a372581b5ca680e23e1529a71dbf57db2443b35a918b39bf45273`

Liora candidate receipts:

- Artifact: `811b8c9f954dbd72f901f464ce7e9fba53cbf6183a4ab4f33afb7aec45f62cb4`
- Library index: `b4f3bf1416e9c1f49f732b5731b227bb5e71d75191d5774f85262c2f2167597d`
- Reconstruction: `9bab86d931edc37e3a6a63616b15897309ca777313dbf875f7e492b7b58c4df3`
- Review motion contract: `e3a270f2e78e18ac029417a53feb4d86de9832b33e598fe9a72ab46b79000d2b`
- Contact sheet: `f0af7a18e1e72291f82ef04033e7017ca0fec9fb6e965e02f945fb40ab7d2c54`
- Alpha-extraction receipts: `f8894a0e6b6ba378b42688e9bd575cc8c8c850e933191a8c307b7325472cc77b`
- Canonicalization receipts: `f2f4fe3e644ff8747576e62f0b2e61e28fedd68db69f99bc04633cb09c49a7e6`

Rohan candidate receipts:

- Artifact: `005e1776a74acf7f63fccb1a8d93c2451ecc661ce58fac25d7c14f87741e8ce5`
- Library index: `442a03c4fa5c82f592dc0f0426fd13df3e2b9e99be252a4c57a3b12ce0e3d424`
- Reconstruction: `ef45a8a517a7fcd7c74b1fbac0fdeefc06b70aee4d0fce236970a688d956f5c2`
- Review motion contract: `b1ffb566a9ce99302f8611be60d1af11bbb000b78efbc6be31833b90cd827af4`
- Contact sheet: `7dbf7ea22b6d6b83164af29d17d623b9b9ef26bd41f197f00f1eee0aac78ee47`
- Alpha-extraction receipts: `bbcdc72afa5ccdd9d359b5802e8a7f65c991c2b89746bf9689c4cd4f33f1b705`
- Canonicalization receipts: `818307146bcf9140fb0e4e39ba1f9ced9e31112de23331d6c230bbfc9c08a081`

## Roster Boundary

The archives also contain Crystail. Crystail remains
`supplied_extra_not_admitted`, outside this 12-character matrix, as required by
`CHARACTER_PARITY_ROLLOUT.md`. Its art is preserved and will require a separate
explicit intake and approval decision.

Wizard Joe remains the comparison baseline. His 48-frame Phazer set is itself
`candidate_visual_parity`, not production admission, so it supplies workflow
and count parity rather than an automatic quality waiver.

## Next Build Order

1. Author the 12 remaining frames as explicitly new art, one character at a
   time, using the character's compiled supplied set as visual authority.
2. Rebuild each completed 48-pose artifact twice and require identical hashes.
3. Review every full-size frame and motion sequence beside approved HD Wizard
   Joe on port 8665.
4. Record product approval against the exact artifact and library-index hashes.
5. Preserve review motion contracts during authoring; compile admitted
   character packages and production semantic graphs only after visual
   approval.
6. Create the character's exact persona/character/package admission only after
   package-level acceptance passes.
7. Keep runtime admission denied until the admission digest, governed
   audiovisual acceptance bundle, and rollback deployment are approved.
