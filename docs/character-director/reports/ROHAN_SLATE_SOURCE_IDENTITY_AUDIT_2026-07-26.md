# Rohan Slate Source and Visual-Identity Audit

Date: 2026-07-26

## Scope and Decision

This audit covers only Rohan Slate's immutable supplied poses
`rohan_slate_motion_001`-`036`. The source package is a 36-pose,
review-only authority for identity, scale, and the existing `g1`-`g6` motion
vocabulary. Poses `037`-`048` (`g7` and `g8`) are absent and require new,
separately receipted art. This audit does not admit any pose to runtime.

## Frozen Provenance

| Authority | SHA-256 |
| --- | --- |
| Archive census | `97e597e7dee837b20d9050529c2ddb15244c0d01b717b539280a87d447ad46fe` |
| 48-slot parity tracker snapshot | `81787dc6cb83594b3e3c80b99f499c9d91cfa2584b9ec97473bc48ac49bd35a0` |
| Rohan reconstruction manifest | `b768ae323f93774b8ad85cd307b68a6df86bcbd20b56a12c98f11529f7183225` |
| Immutable 36-pose `.wjpose` | `32e480baa58081811621cceac92c9cf7ada6c0d958afe390ab3eaedadce32def` |
| Review-only library index | `9be9aa44c9020666ac7580e4e35c3b4eabea3ac2ef52ad035f090ec8082eff54` |
| Full-size source contact sheet | `0848b4548dcfde3294bfa5207b8b913946bd3a6b8915a6288a3ed4515a6f610e` |

The source sheets are lossy VP8 WebP payloads declared with `.png` names.
They are RGB images with a baked near-white checkerboard and no alpha channel.
The immutable `.wjpose` contains the reconstructed transparent RGBA records;
the sheets remain provenance inputs, not projector assets.

| Sequence | Selected archive and archive SHA-256 | Selected member SHA-256 |
| --- | --- | --- |
| `g1`, poses 001-006 | `Sprites 2.zip` / `570d20086ad833b018188eee9c7d3368e5a156139e67c62b474f86cb50bfa749` | `4ad839e30dee52f6e31c1be6a2969b7094a22121dabfb3d187958327efa85808` |
| `g2`, poses 007-012 | `Sprites 1.zip` / `a26b2fb59fba19b494c97c278dc5da4cd0df5a2d58e989759da521804a1206a8` | `ffd6e9efc9d174294312486cc85b7eed923d5cbe1d88b0a823ed917439ade3a5` |
| `g3`, poses 013-018 | `Sprites 1.zip` / same as above | `59bc0aa63d58f65cc764729c1b4729ebdca5836a2694e813a035519f3e39021e` |
| `g4`, poses 019-024 | `Sprites 1.zip` / same as above | `f5ece1e0520f1bca2f1e103a952b46718a6d7641545c7641b83fd864a3ecb035` |
| `g5`, poses 025-030 | `Sprites 1.zip` / same as above | `c00e595d0b107f41e1f8adc6da9cc2705180f30b5d36839d82b82e30ef4604fe` |
| `g6`, poses 031-036 | `Sprites 1.zip` / same as above | `7f029fcaa5dc62713ea581d97bdf72b013d3f71eba665852022d0cf8da42ad33` |

Rohan's `g1` name collides across two archives. The displaced
`Sprites 1.zip` member is hash-visible as
`4b0d5c3952cba48d88556a103db9da3be806e722317ce99ce27ff342b949d215`
(1774x887). Full-size review selected the `Sprites 2.zip` member above
(2172x724) because it has the cleaner corrected gait progression. Archive
order is not authority, and the displaced variant must not be substituted.

## Frozen Visual Identity

- Adult masculine voxel character with warm dark-brown skin, a compact
  cuboid build, a slightly oversized square head, and consistent full-body
  proportions.
- Charcoal-black ribbed knit beanie, fitted close to the head. No brim,
  pom-pom, logo, exposed long hair, or alternate headwear.
- Rectangular dark frames worn in every view. The lenses/eye area retain the
  characteristic teal-green accent; the glasses must remain attached,
  aligned, and readable in profile, front, and rear-quarter motion.
- Short dark-brown/black beard and mustache framing the mouth and chin. Do not
  replace them with a clean shave, long beard, isolated goatee, or different
  facial-hair silhouette.
- Plain white short-sleeve shirt with a small open collar/neck detail, straight
  untucked hem, and light neutral voxel shading only. No print, logo, jacket,
  hoodie, long sleeves, or recolor.
- Dark forest-green straight-leg trousers with the supplied block structure
  and shading. No shorts, denim-blue substitution, belt ornament, or cargo
  additions.
- Brown low ankle boots with dark soles and warm highlights. No sneakers,
  sandals, or color change.
- **No-prop rule:** the 36-pose authority contains no handheld, worn, or
  detached prop and no magical/environmental effect. Poses 037-048 must remain
  prop-free unless a later, explicit product decision creates a new authority.
  Performance must come from gaze, expression, hands, torso, stance, and
  timing.

## Canonical Frame Contract

- Canvas: `1254x1254`, sRGB, straight alpha.
- Canonical baseline: `y=1185`.
- Minimum outer margin: `69` pixels.
- Existing reconstructed bounds span `x=311..943` and `y=69..1185`; observed
  normalization scales span `1.95104895..2.1`.
- Grounded authored poses must preserve believable shoe contact at the
  canonical baseline. Airborne or crouched beats may sit above it only as
  required by the authored motion arc; they must not be artificially stretched
  to the floor.
- Every authored silhouette, including hands, shoes, and any detached
  character-owned voxel, must remain inside the 69-pixel safe area. No crop,
  edge contact, arbitrary scale jump, or baseline drift is acceptable.

## Review and Runtime Boundary

The library index records `candidate_pose_count: 36`,
`approved_pose_count: 0`, `review_projection: true`, and
`runtime_admitted: false`. Every supplied pose and every future authored pose
remains review-only until full-size visual approval, deterministic package
receipts, exact artifact approval, and the separate character-admission gate
all pass. Review projection grants no gameplay, remote-control, semantic, or
production runtime authority.

## Rejection Criteria for Poses 037-048

Reject an authored pose if any of the following is true:

1. It alters Rohan's face, skin tone, beanie, glasses, teal-green eye/lens
   accent, beard/mustache silhouette, body proportions, or voxel rendering
   language.
2. It changes the white shirt, forest-green trousers, or brown boots, or adds
   logos, outerwear, jewelry, bags, props, particles, scenery, or effects.
3. It is cropped, close-up, partial-body, padded with a duplicate, or lacks a
   complete coherent silhouette.
4. It contains checkerboard/background residue, chroma or matte fringe,
   softened alpha, erased white shirt/eye detail, holes, floating anatomy, or
   unowned detached pixels.
5. It violates the 1254-square canvas, straight-alpha/sRGB profile, 69-pixel
   safe area, stable scale, baseline/contact rule, or full-size sharp voxel
   quality.
6. Its pose mechanics break joint continuity, foot contact, balance, facing,
   glasses attachment, garment continuity, or the readable transition into
   and out of neighboring frames.
7. Its provenance, extraction, canonicalization, RGBA hash, semantic role,
   motion contract, or deterministic rebuild receipt is missing or
   non-portable.
8. It modifies or replaces any immutable pose `001`-`036`, uses the displaced
   `Sprites 1` `g1`, claims approval without exact hashes, or sets
   `runtime_admitted: true`.

