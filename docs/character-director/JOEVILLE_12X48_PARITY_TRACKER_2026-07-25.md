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

## Roster Boundary

The archives also contain Crystail. Crystail remains
`supplied_extra_not_admitted`, outside this 12-character matrix, as required by
`CHARACTER_PARITY_ROLLOUT.md`. Its art is preserved and will require a separate
explicit intake and approval decision.

Wizard Joe remains the comparison baseline. His 48-frame Phazer set is itself
`candidate_visual_parity`, not production admission, so it supplies workflow
and count parity rather than an automatic quality waiver.

## Next Build Order

1. Author the 114 missing frames as explicitly new art, one character at a
   time, using the character's compiled supplied set as visual authority.
2. Rebuild each completed 48-pose artifact twice and require identical hashes.
3. Review every full-size frame and motion sequence beside approved HD Wizard
   Joe on port 8665.
4. Record product approval against the exact artifact and library-index hashes.
5. Compile character packages, semantic motion graphs, contacts, transitions,
   and interruption behavior only after visual approval.
6. Keep runtime admission denied until package-level acceptance passes.
