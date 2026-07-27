# Finn Calder Source-Identity and Provenance Audit

Date: 2026-07-26
Audit role: independent Character Identity and Provenance Auditor
Repository HEAD: `c5833c824b44de712c01740e7cf4305c15299e7f`

## Scope and Decision

This audit covers Finn Calder's supplied character portrait, supplied motion
sheets, reconstructed transparent pixel graphs, canonical frame contract, and
runtime-admission boundary. It establishes the immutable identity and source
requirements for completing poses `finn_calder_motion_037`-`048`.

Decision:

- **Source identity freeze: pass.** The portrait and all six supplied motion
  sheets describe one coherent character.
- **Supplied-pose preservation gate: pass.** All 36 records in the immutable
  `.wjpose` match the reconstruction manifest's raw RGBA hashes.
- **48-pose parity: blocked.** No complete, receipted, compiled `g7` or `g8`
  sequence exists.
- **Authored provenance: blocked.** Concurrent untracked G7 direction and
  chroma-source work began during this audit, but Finn still has no frozen
  authored manifest, extraction receipts, canonicalization receipts, parity
  reconstruction, motion contract, or deterministic 48-pose artifact.
- **Product approval and runtime admission: denied.** Finn is absent from the
  production character registry. Review projection is not admission.

This report freezes authority; it does not create, approve, or admit art.

## Evidence Inspected

All hashes below are lowercase SHA-256 digests of the exact inspected bytes.
Repository-relative paths are relative to the repository root.

| Evidence | SHA-256 | Finding |
| --- | --- | --- |
| `/Users/paul/Downloads/Sprites 1.zip` | `a26b2fb59fba19b494c97c278dc5da4cd0df5a2d58e989759da521804a1206a8` | Exact live source archive; 39,089,470 bytes |
| `assets/reference/joeville_48_parity/source-metadata/archive-census-v001.json` | `97e597e7dee837b20d9050529c2ddb15244c0d01b717b539280a87d447ad46fe` | Finn is an authority-roster character with one portrait and six unconflicted sheets |
| `assets/reference/joeville_48_parity/source-metadata/parity-tracker-v001.json` | `81787dc6cb83594b3e3c80b99f499c9d91cfa2584b9ec97473bc48ac49bd35a0` | Source-planning snapshot bound into the artifact; records 36 available and 12 missing slots |
| `assets/reference/joeville_48_parity/source-metadata/finn-calder/reconstruction-manifest-v001.json` | `b399a12b8b65dd5999ad0769f9250c139aef48b22f6734f3034112b530ebf30e` | Pose-level archive, member, frame, normalization, bounds, and RGBA receipts for poses 001-036 |
| `assets/reference/joeville_48_parity/compiled/finn-calder/finn-calder-candidate-source-motion-v001.wjpose` | `6172d80b6003c57317a4139fef8180a631752e91ff4d21e0f958cde0165a86f1` | Immutable 36-pose transparent RGBA source-motion artifact |
| `assets/reference/joeville_48_parity/compiled/finn-calder/library-index.json` | `ed99bff17eed17027f8b1eda8fe662f4f0ce1e2f1ed2e6577835f9fd05bd4249` | 36 candidates, zero approved, review projection enabled, runtime denied |
| `assets/reference/joeville_48_parity/source-metadata/finn-calder/source-motion-contact-sheet-v001.png` | `423e174b9ff64b3d5b5a9b6b96013b1faca4c51b32b314dedb53ef8e4533c3cc` | Full 36-pose visual review surface |
| `assets/reference/hd_canonical/manifest.json` | `740f35730f4aa1e6c6ef96be80115c5b0e117397f792d57fdf5360452bbe78c8` | Canonical 1254-square HD alpha profile |
| `wizard_avatar/definitions/character_registry.json` | `7a10a85116764be47e79a5d9f3d6ade9e6afa0e1b7a847b06c955f57194cff59` | Schema V2 registry contains only `wizard-joe-v1`; Finn is not admitted |
| `docs/character-director/CHARACTER_ADMISSION_CONTRACT_V1.md` | `1a124300104900536a110435d3427aab0a92f3452025113299fb18f91da29c1e` | Registry membership, not visual completeness, is runtime authority |
| `docs/character-director/JOEVILLE_12X48_PARITY_TRACKER_2026-07-25.md` | `c4bb1e02c1ed86aaac7b23532e16049d5038f06c117dcbc6c934dd167286beac` | Current human tracker records 36 candidate poses and 12 missing |

The implementation symbols inspected were:

- `tools/build_joeville_source_motion.py`: `EXTRACTION_PROFILE`,
  `_selected_source`, `_refine_checkerboard_matte`,
  `_trim_neutral_fringe`, `_library_index`, and `build_character`.
- `wizard_avatar/hd_pose_artifact.py`: `MAGIC`,
  `write_pose_artifact`, `HDPoseArtifact._read_index`,
  `HDPoseArtifact.load_rgba`, and `HDPoseLibrary.__init__`.
- `wizard_avatar/character_registry.py`: `CharacterAdmissionV1`,
  `CharacterRegistry`, `load_character_registry`, and the legacy Wizard-only
  admission constants.

The comparison model was taken from:

| Completed precedent | SHA-256 |
| --- | --- |
| `docs/character-director/reports/ROHAN_SLATE_SOURCE_IDENTITY_AUDIT_2026-07-26.md` | `ae4b84f1d7cc2cbbe4bf39217248794de2e25410dd0d10dcd3ce1cd5296960b6` |
| `docs/character-director/reports/ROHAN_SLATE_TECHNICAL_BUILD_AUDIT_2026-07-26.md` | `860039aea22ff00347aacfe0bee83a3b658866769750389ab0d3e723ae6c7e69` |
| `docs/character-director/reports/LIORA_KANE_TECHNICAL_BUILD_AUDIT_2026-07-26.md` | `66b13f59a16c1afceae6390c733b15ec4ec85aec8c955f2ada7b53bedeb539fe` |
| `docs/character-director/reports/LIORA_KANE_ANIMATION_DIRECTION_2026-07-26.md` | `8cfa8f93716965fbd5172240bec81416b8ccca9d6b196ee78200aa4a9519900d` |

## Frozen Source Members

The seven Finn members were extracted from the live archive and inspected at
their decoded dimensions. Their `.png` names are misleading: every member is
a lossy VP8 WebP payload, RGB only, with a baked near-white checkerboard and no
source alpha channel.

| Role | Member | Decoded size | SHA-256 |
| --- | --- | ---: | --- |
| Identity portrait | `char-finn-calder.png` | 1254x1254 | `7a466b219f1c35aace32c1eb7e9d1c8df904e02040c4836c8dd6988a54911d26` |
| `g1`, poses 001-006 | `sheet-finn-calder-g1.png` | 1942x809 | `274d197421ebe3a64d532ac5df7f8c8d1fc23ba2694ea5551e4639a9446e3c72` |
| `g2`, poses 007-012 | `sheet-finn-calder-g2.png` | 2172x724 | `621a6c5945160e7a3eae0c3bf030a09046e92dac441a2ffbe34c2d71616823ed` |
| `g3`, poses 013-018 | `sheet-finn-calder-g3.png` | 2172x724 | `d2a09b500ef289c82bf801d182b029f696f8c8d97affe62e016e3863dfe6d373` |
| `g4`, poses 019-024 | `sheet-finn-calder-g4.png` | 2095x751 | `199727d06a7afb3696238f9aa43d5bf737a04a8f3c9ca6c5f7a1a4e9cc35c7a3` |
| `g5`, poses 025-030 | `sheet-finn-calder-g5.png` | 2172x724 | `72cc16da5ddead3a30f37cac39f9699a0c8db667804f4af14b456554ed3266b8` |
| `g6`, poses 031-036 | `sheet-finn-calder-g6.png` | 2172x724 | `166ec4bd6569e02887b237eb9037d4351e875478e3f000c54f5c23112bf0c62e` |

There is exactly one source candidate for each supplied Finn sequence. The
source-planning tracker leaves `selected_source` null, but
`_selected_source` deterministically accepts a single candidate with one
unique member hash. Finn has no same-name member conflict and no displaced
variant.

The portrait is direct identity authority but is not a projector asset. The
future Finn authored manifest must bind its hash explicitly; relying only on
its indirect inclusion in the archive-census hash is weaker provenance.

## Verified Artifact State

The source artifact originated in commit
`12317d04c7805b527c425cf538c6c1bf8ab0c3cf` (`Build JoeVille
12-character HD parity intake`, 2026-07-25).

The artifact was materialized from `HEAD` and decoded through
`HDPoseArtifact`, not inferred from the contact sheet:

- magic: `WJPOSE2\0`;
- payload encoding: `rgba8-zlib`;
- canvas: 1254x1254;
- record count: 36;
- pose IDs: exactly `finn_calder_motion_001`-`036`;
- all 36 decoded raw RGBA hashes match the reconstruction manifest;
- all 36 raw RGBA hashes are unique;
- all records are nonempty RGBA graphs;
- all four canvas corners are transparent in every record;
- every alpha-zero pixel has zero hidden RGB;
- union of upper-exclusive alpha bounds: `[275, 69, 979, 1185]`;
- recorded source normalization scales:
  `1.88513514`, `1.9109589`, `1.97173145`, `2.02173913`,
  `2.08598131`, and `2.1`.

The checked-out artifact is currently a dataless sparse placeholder:
`stat` reports its logical 28,989,856-byte size but zero allocated blocks.
A direct read can therefore produce an empty stream even though the Git object
is valid. The exact Git object materialized to an ordinary temporary file as
28,989,856 bytes and hashed to the declared
`6172d80b6003c57317a4139fef8180a631752e91ff4d21e0f958cde0165a86f1`.
Any build or test must materialize the object or use a verified cache before
opening it. The SHA-256 of an empty sparse read is not evidence about the
artifact.

The JSON parity-tracker snapshot is a source-planning receipt, not current
build status: it predates reconstruction and still records zero compiled
poses. The reconstruction manifest, immutable artifact, library index, and
current Markdown tracker are the later evidence for the 36-pose checkpoint.

## Immutable Visual Identity

The following traits are consistent across the portrait, front and
three-quarter poses, profile locomotion, and rear poses. They are immutable
for authored poses 037-048.

- Humanoid alien with vivid chartreuse/lime-green skin and green hands.
- Very large rounded-ovoid voxel head, stepped cranial contour, compact jaw,
  lateral temple/ear plates, and no hair, hat, helmet, horns, or antennae.
- Two oversized solid-black slanted almond/teardrop eyes. There is no visible
  white sclera, colored iris, pupil, eyelash, eyebrow, eyewear, or eye glow.
- Two tiny black square nostril marks and a short, narrow black horizontal
  mouth. Do not add human lips, teeth, a large nose, or a broad cartoon smile.
- Compact narrow torso and shoulders beneath the oversized head, with long
  straight trouser legs and block-built green hands.
- Saturated orange two-piece suit: notch-lapel jacket, matching straight-leg
  trousers, black center shirt/placket, black breast and hip welt details, and
  a small silver-gray square belt/buckle accent.
- Heavy black low block shoes/boots with layered, ridged soles. No sneakers,
  colored soles, sandals, or bare feet.
- Dense high-definition micro-voxel construction, visible square cell grid,
  hard stepped silhouette, and restrained directional shading. Do not replace
  it with smooth vector art, low-resolution pixel art, plastic 3D realism, or
  a different voxel scale.
- No environmental scenery, particles, magic, wings, bag, jewelry, or worn
  accessory appears in the supplied motion authority.

The rear authority is equally binding: the green head remains plain and
unbroken, the orange jacket has a clean back panel, and no hidden hair,
backpack, tail, or accessory may be introduced.

## Microphone Boundary

The identity portrait contains one handheld microphone: a black handle with a
silver-gray spherical voxel grille. None of the 36 supplied motion poses
contains a microphone or any other prop.

Therefore:

1. The microphone is a **character-compatible optional prop**, not a mandatory
   component of Finn's body or default wardrobe.
2. Prop-free G7/G8 art is valid if its performance direction does not call for
   a microphone.
3. A microphone sequence is valid only if the Finn-specific animation brief
   explicitly chooses it and every relevant frame preserves exactly one
   continuously owned microphone with the portrait's form and colors.
4. It may not appear for one isolated beat, teleport between hands, duplicate,
   fuse into the hand, change grille/handle color, or disappear before a
   readable recovery.
5. The portrait's checkerboard is not alpha and the portrait itself may not be
   projected as a motion frame.

## Supplied-Pose Preservation Ledger

The first 36 raw RGBA graphs are immutable. A parity build must load them from
the verified source artifact, retain their order and byte identity, and append
only poses 037-048.

| Pose | Seq. | Raw RGBA SHA-256 |
| --- | --- | --- |
| `finn_calder_motion_001` | `g1` | `60f059f9498297bd64fa6bc18e0131c396a1dce880782b67c0f97ea722063c44` |
| `finn_calder_motion_002` | `g1` | `1b29a5b97c1c1e6757a40e6490dd087d57b4da6e68690e7a7d62a65d83c28cb3` |
| `finn_calder_motion_003` | `g1` | `5608cc73b506c37b4939d69bcfbab411c6d4cbf8c25c124d891f92346f641ae6` |
| `finn_calder_motion_004` | `g1` | `21e866e8988c4ffc451272141d91270c47f8e8b428c00e36101c91bbd9bacb7a` |
| `finn_calder_motion_005` | `g1` | `aeee8a50f4aae417f8e05bb863b1b17d19aff1d038d241168bcc18c5da7fe2e0` |
| `finn_calder_motion_006` | `g1` | `a12a55d4d0992ae6ac76a891338aa71fb401aee3397ba8f07b9fff60d477b738` |
| `finn_calder_motion_007` | `g2` | `12bb04986ff437e721f2fb6bc108de16c149607588d599daad3ba0e3fb417cdc` |
| `finn_calder_motion_008` | `g2` | `40077f29f0e39b46f7ec2498cae9f10b34ccdedddf24c2d4e281ae255696c57b` |
| `finn_calder_motion_009` | `g2` | `a918e359b6a19bceeb577c70ab9aa5b38988b17f308f501749d3a8de8dfa2e29` |
| `finn_calder_motion_010` | `g2` | `91180b33c4d679b9d3607f3c428d046b096dfc35aa0d05440eea2b01c6ad0246` |
| `finn_calder_motion_011` | `g2` | `a8082bc44ab715582af99648b70c2ae36868a57c0830a6446b3c18d754ba16d4` |
| `finn_calder_motion_012` | `g2` | `bb188d045f133e0d5cbff3f70a767864e07406ea8cc8e8020a7520f4b6046c41` |
| `finn_calder_motion_013` | `g3` | `ed6b4f8ce629c32414d73ff7490872c7c2151d9a68a8ba2facaf860f61440d1a` |
| `finn_calder_motion_014` | `g3` | `e701caa2d52efef02879baee95cd93e99ab8fb432ea14d8a43d957d7c1d74c8d` |
| `finn_calder_motion_015` | `g3` | `6e081b4b4a6d077ca383ac733678b182862a9a8444afd14d39a591ef22e28b75` |
| `finn_calder_motion_016` | `g3` | `721bc5e9f0c29f3f0d4ddeb805a2931962f588d2ced2149c094712cb833dc15b` |
| `finn_calder_motion_017` | `g3` | `518aba3912bbbd8bc2d22e62349ad01fe72487ebf122b0890b825b4ac5984a23` |
| `finn_calder_motion_018` | `g3` | `829b0e8c413eeb0c266bccd49fe63dc9577b7cfc457e8e785be0dd50da537a39` |
| `finn_calder_motion_019` | `g4` | `f7d33240716d96bcc7f9f94c1536cf5da1ec5f5b6ae17a331fc380cbbf4cefd6` |
| `finn_calder_motion_020` | `g4` | `45d2435ac8634709f4a8c25926386367fd40c88ed870fce27be57e0632cb641f` |
| `finn_calder_motion_021` | `g4` | `8682ab9b590c1ce7c8ebb38acd27a9bb988ac8a01442af342371b6ad90b68403` |
| `finn_calder_motion_022` | `g4` | `8191a688226498833ee7d52633e11a269946ec7bc488b6f3d35049dbe743a6f1` |
| `finn_calder_motion_023` | `g4` | `f7ea0a68f5688184d19608ababbd5f528bf62c23db3e0e334019d94c7e6834e6` |
| `finn_calder_motion_024` | `g4` | `d2f7a8a9f399c51c81504ff470070fb1eaeef383430ee73d166f0f4e26e828bc` |
| `finn_calder_motion_025` | `g5` | `5861eecebfb9c2c41518a3f0ec088248edc208549fa2e7fa42ea5b3a1374d4bd` |
| `finn_calder_motion_026` | `g5` | `9fd20aa77fdbcc5e1ef6bb86ed0049ff80689577d3d388d008012b374e150257` |
| `finn_calder_motion_027` | `g5` | `7c976cecc02ded0ff472cedc7a026b7b08e093d53c3415ee1c7ea0166246f024` |
| `finn_calder_motion_028` | `g5` | `45df8f61241cea4316aee5a7e04be4d25b4ab12477eb1dfbbdbce736ab5c1d25` |
| `finn_calder_motion_029` | `g5` | `6407fad15d6b6ccdd800853304619cf9db6bfc88d8d69d88575c647cde89338e` |
| `finn_calder_motion_030` | `g5` | `723adc88d6304a023d4ee7d5da4ebb9d8199508ccf47d4ab806c63d176bdf76e` |
| `finn_calder_motion_031` | `g6` | `64391867d830b654b13f466de2250336cf281b2f2cb45eba3da080394beb8130` |
| `finn_calder_motion_032` | `g6` | `358fc1ef40874a3f5b5fa47e9028386d540f96c4254a7be0a01ca0ceb9816845` |
| `finn_calder_motion_033` | `g6` | `f74207790712a3a86e3ca4e07f2434f37782d86008605c599d6aa06ad84673f1` |
| `finn_calder_motion_034` | `g6` | `1d49619c1818bd89439eaf55b3abb16282019d3d11cb5e633b514bb2275db503` |
| `finn_calder_motion_035` | `g6` | `06980ad2884789cdf1d8ddd9bde09da8d9c3bbefe6b3d40596a1d7d4919f5cde` |
| `finn_calder_motion_036` | `g6` | `981080065b6b8150cfa464fde5d885dd7cbb462172ed253d77e3c6c626aafa13` |

The source movement vocabulary already includes side/profile locomotion,
running, crouch and launch, airborne beats, recovery, a wave, front locomotion,
rear locomotion, and rear airborne motion. These observations are visual
inferences, not semantic capability admission. G7 and G8 must add distinct,
Finn-specific performance material rather than mirror, flip, rename, or pad
the supplied poses.

## Canonical Frame and Alpha Contract

- Profile: `wizardjoe_hd_alpha_1254_v001`.
- Canvas: 1254x1254.
- Color: sRGB.
- Alpha: straight.
- Canonical baseline: `y=1185`.
- Minimum top and horizontal safety margin: 69 pixels.
- Source-sheet extraction profile:
  `background_min_channel=210`,
  `background_max_channel_spread=64`,
  `minimum_component_area=24`,
  `maximum_source_scale=2.1`, and
  `nearest_expected_center_by_component_centroid` grouping.

The existing source motion includes grounded, crouched, and airborne beats.
Its recorded lower alpha bound ranges from 931 through 1185. The supplied
vertical arcs and small source contact offsets are immutable and must not be
"repaired" by resampling or forcing every old frame to the baseline.

New grounded poses must have readable planted support and stable body-root
registration. New airborne poses may rise above the baseline only as required
by an authored motion arc. Every new silhouette, including fingers and any
continuously owned microphone, must remain inside the safety area. Neutral
checkerboard fringe, erased black facial marks, erased silver buckle detail,
opaque corners, hidden RGB under alpha zero, cropping, and matte haze are
rejection defects.

## Authored-Asset and Receipt Status

At repository HEAD, Finn has only four tracked parity files: the source
artifact, source library index, reconstruction manifest, and source contact
sheet. HEAD contains no tracked
`assets/reference/joeville_48_parity/authored-source/finn-calder/` directory.

At the explicit concurrent-work snapshot
`2026-07-26T18:32:34-06:00`, another worker had added an untracked animation
direction report and six untracked RGB chroma-source candidates:

| Concurrent untracked input | SHA-256 |
| --- | --- |
| `docs/character-director/reports/FINN_CALDER_ANIMATION_DIRECTION_2026-07-26.md` | `8a8832b0c004589dc3a298b7b385d4d130fb6108949f83df4337a2d309a368c0` |
| `assets/reference/joeville_48_parity/authored-source/finn-calder/chroma-source/finn_calder_motion_037.png` | `551958ffd9b6b21118b33878c6c12df26862ba3fbb8698aa53ae5d3d53f99bcd` |
| `assets/reference/joeville_48_parity/authored-source/finn-calder/chroma-source/finn_calder_motion_038.png` | `e00aaeb9d45bc8222aaf911d313fa6494a4379ffea961859e5134b5e8de994d4` |
| `assets/reference/joeville_48_parity/authored-source/finn-calder/chroma-source/finn_calder_motion_039.png` | `1177b34c149e1ba5e160ce260d95737ad82ec3aac0d7dfe4aea057b1a8083fea` |
| `assets/reference/joeville_48_parity/authored-source/finn-calder/chroma-source/finn_calder_motion_040.png` | `be3864041339a0721e2b63ba95e506aefd9f1bc017185515edbe353424a7227f` |
| `assets/reference/joeville_48_parity/authored-source/finn-calder/chroma-source/finn_calder_motion_041.png` | `50837ab98417472768f775d2f1b54b8b3697f52e8e3d8649bfae1bb1f68de55d` |
| `assets/reference/joeville_48_parity/authored-source/finn-calder/chroma-source/finn_calder_motion_042.png` | `9ad791d0b1a1148f81bf1b49d930f7640c6f68dee89c93ba1a1f172a6c725cd1` |

All six chroma candidates are 1254x1254 RGB PNGs on a magenta key. Full-size
inspection finds their head, face, suit, hands, shoes, proportions, voxel
density, and prop-free decision visually consistent with the frozen identity.
That observation is not alpha approval, uniqueness approval, sequence
approval, or provenance approval. The files are mutable, untracked,
incomplete, and not bound by receipts; they are excluded from the source
identity pass above.

The following complete deliverables remain absent and may not be claimed by
inference:

| Required authored evidence | Current state |
| --- | --- |
| Finn-specific G7/G8 animation-direction report | Untracked concurrent draft; not frozen or bound |
| Authoring brief binding portrait and source artifact hashes | Missing |
| Twelve full-size authored source images | Six untracked G7 chroma candidates observed; G8 and frozen 12-frame set missing |
| Twelve extracted-alpha intermediates | Missing |
| Twelve canonical 1254x1254 RGBA frames | Missing |
| Pose-level alpha-extraction receipts | Missing |
| Pose-level canonicalization receipts | Missing |
| Aggregate receipt bundles | Missing |
| `authored-g7-g8-v001.json` equivalent | Missing |
| 48-pose parity reconstruction manifest | Missing |
| 48-pose review motion contract | Missing |
| 48-pose contact sheet | Missing |
| Deterministic 48-pose `.wjpose` and library index | Missing |
| Finn-specific parity/provenance test | Missing |
| Product approval bound to exact artifact and index | Missing |

## Missing-Pose Risks

1. **Alien-face drift.** Human sclera, pupils, brows, lips, teeth, a human
   nose, antennae, or altered head geometry would change Finn's identity.
2. **Wardrobe drift.** Orange prison-coverall simplification, missing lapels,
   missing black shirt/pocket details, alternate footwear, or inconsistent
   buckle treatment would break the supplied formal-suit identity.
3. **Voxel-language drift.** Coarser pixels, smooth illustration, glossy
   plastic, or mismatched cell density would make authored poses read as a
   different asset set.
4. **Microphone ambiguity.** The portrait proves compatibility, not continuous
   ownership in the source-motion library. Unplanned appearance or
   disappearance would look like a rendering defect.
5. **Scale and root mismatch.** The supplied groups use different receipted
   normalization scales. New art must match apparent head/body proportions
   and stable support, not merely occupy the same canvas.
6. **Duplicate padding.** Flips, near-duplicates, time-shifted copies, or
   renamed source poses do not satisfy the missing twelve slots.
7. **Source mutation.** Re-extracting or regenerating poses 001-036 can change
   edge alpha, facial marks, clothing details, and raw hashes.
8. **Receipt substitution.** A contact sheet or PNG directory is not a
   portable extraction/canonicalization chain.
9. **Stale evidence.** The source-planning tracker says zero compiled poses;
   using it as current status would contradict the verified 36-pose artifact.
10. **Authority conflation.** `finn_calder_runtime_epoch` appears in the
    evidence contract, but an epoch field does not create a character package,
    persona binding, product approval, or registry admission.
11. **Dataless artifact reads.** Hashing the current sparse placeholder without
    materialization can falsely produce the empty-file digest.
12. **Semantic imitation.** Reusing Rohan's or Liora's authored performance
    concepts without a Finn-specific animation-direction decision would meet a
    numeric slot count while failing character authorship.

## Rejected Alternatives

| Alternative | Decision | Reason |
| --- | --- | --- |
| Regenerate all 48 poses from the portrait | Rejected | Replaces 36 verified supplied graphs and invents motion continuity |
| Project the portrait or source sheets directly | Rejected | They are RGB VP8 WebP images with baked checkerboards, not alpha render assets |
| Make the microphone permanent in every pose | Rejected | The six supplied motion sequences are consistently prop-free |
| Ban the microphone from all future Finn art | Rejected | The identity portrait explicitly establishes it as compatible |
| Mirror or duplicate existing poses for G7/G8 | Rejected | Violates uniqueness, authorship, and transition requirements |
| Recolor another JoeVille character into Finn | Rejected | Does not preserve Finn's anatomy, face, suit construction, or voxel proportions |
| Force all supplied frames to one new scale/baseline | Rejected | Mutates immutable source RGBA and damages authored airborne/contact arcs |
| Treat review projection or runtime epoch as admission | Rejected | Production authority comes only from a product-approved registry entry |
| Set `runtime_admitted: true` in the review index | Rejected | Bypasses package, persona, admission-digest, governance, and acceptance gates |

## Verification Gates for Poses 037-048

All gates are conjunctive.

1. **Materialization gate**
   - Materialize the immutable source artifact to ordinary readable storage.
   - Verify exact size `28,989,856` and SHA-256
     `6172d80b6003c57317a4139fef8180a631752e91ff4d21e0f958cde0165a86f1`.
   - Decode 36 records with `WJPOSE2\0`; reject an empty or truncated read.

2. **Source-preservation gate**
   - Preserve pose IDs, order, and every raw RGBA hash in the ledger above.
   - Build by decoding poses 001-036 and appending only 037-048.
   - Prove the source artifact hash is unchanged before and after the build.

3. **Identity-authority gate**
   - Bind the archive, portrait, six sheet, source artifact, source
     reconstruction, and HD profile hashes in the Finn authoring brief.
   - Pass full-size front, profile/three-quarter, and rear identity review.
   - Record an explicit prop decision for each authored sequence.

4. **Authored-receipt gate**
   - Provide twelve full-size source frames, alpha intermediates, and canonical
     RGBA destinations.
   - Provide portable pose-level extraction and canonicalization receipts.
   - Bind source bytes, output PNG bytes, raw RGBA bytes, settings,
     translations/scales, bounds, and profile without absolute workspace paths.

5. **Frame-quality gate**
   - Require RGBA 1254x1254, sRGB, straight alpha, transparent corners, zero
     hidden RGB, nonempty silhouette, safe margins, and no checkerboard/matte
     residue.
   - Require complete head, eyes, nostrils, mouth, hands, jacket, trousers,
     shoes, and any continuously owned prop.
   - Require stable apparent scale, body root, support, and readable balance.

6. **Motion-authorship gate**
   - Approve a Finn-specific G7/G8 animation-direction report before semantic
     capability binding.
   - Require six distinct beats per sequence, coherent preparation/stroke/
     hold/recovery, valid entry/exit poses, and marker-safe interruption points.
   - Reject duplicates, isolated key art without transitions, floating
     anatomy, foot sliding, prop teleportation, or contradictory facing.

7. **Determinism gate**
   - Require 48 unique raw RGBA hashes.
   - Rebuild twice from the same inputs and reproduce exact artifact and
     library-index hashes.
   - Verify the complete chain:
     `source hash -> extraction receipt -> alpha hash -> canonicalization
     receipt -> canonical PNG/RGBA hash -> authored manifest -> parity
     artifact/index`.

8. **Review-projection gate**
   - Keep `approved_pose_count: 0`, `review_projection: true`, and
     `runtime_admitted: false` at library, shard, sequence, provenance, and
     motion-contract boundaries.
   - Project all twelve authored pose IDs through the real isolated HD
     projector and bind response headers to the exact candidate artifact and
     pose hashes.
   - Capture full-size visual evidence beside approved HD Wizard Joe.

9. **Product and admission gate**
   - Product approval must name the exact 48-pose artifact and library-index
     hashes.
   - Product approval still does not admit Finn.
   - Runtime admission requires a frozen Finn character package, stable
     persona ID, independently verified admission digest, production-registry
     entry, governed audiovisual acceptance evidence, deployment record, and
     rollback release.

## Final Authority Statement

Finn Calder's current immutable motion authority is exactly the 36-record
artifact
`6172d80b6003c57317a4139fef8180a631752e91ff4d21e0f958cde0165a86f1`.
His direct visual-identity portrait is exactly
`7a466b219f1c35aace32c1eb7e9d1c8df904e02040c4836c8dd6988a54911d26`.
Neither hash authorizes alteration, parity padding, product approval, or
runtime admission.

Poses 037-048 must be newly authored, Finn-specific, independently receipted,
and appended without changing poses 001-036. Until every gate above passes,
Finn remains a 36-pose review-only source candidate with no production runtime
authority.
