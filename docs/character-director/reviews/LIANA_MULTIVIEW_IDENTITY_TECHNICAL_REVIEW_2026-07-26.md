# Liana Multiview Identity Technical Review

Date: 2026-07-26

## Decision

The front identity authorized by the user has been expanded into independently
authored front, left-profile, left-three-quarter, and rear identity anchors.
The four views are technically suitable to guide candidate motion production.
They are not a production-runtime admission.

## Bound Identity

- Character: `liana`
- Front PNG SHA-256:
  `1579f0adb7f4c69184c8d45011a201c7fb3369d09af183a1d2f384acc07ea886`
- Front RGBA SHA-256:
  `69feb97676636b20ba11dfe022002947532eec6d8d29edf4af423215e9651437`
- Identity manifest SHA-256:
  `c81767d883ea377b5f6f68fef55efd8c0cd25db81f0aac3eed25922ce23b112c`

## Technical Findings

- All four sources are independent full-size voxel renders.
- All four canonical frames are RGBA PNGs at `1254 x 1254`.
- Every silhouette ends on canonical baseline `1185`.
- Transparent corners are present and receipt paths are project-relative.
- Face, skin tone, curl length, adult proportions, teal top, high charcoal
  waistband, alpine-blue leg detail, and gray-blue shoes remain recognizable
  across the turn.
- Profile, three-quarter, and rear silhouettes are complete and uncropped.
- No props, text, logos, scenery, shadows, or Liora wardrobe elements appear.

The profile and rear sources required small deterministic oversize fitting to
respect canonical margins. Both transformations are recorded in their
canonicalization receipts.

## Review Projection

- Artifact SHA-256:
  `dcef84ac393baf73d6c3a1de4799043602ce65dc8d7d3290d70e53b089d2f531`
- Library index SHA-256:
  `8c21b9c776203ff10ca8589c61241d245f77c5409c00b4405c8ef505b451eeec`
- Build receipt SHA-256:
  `c4bad35c48747fcf7d5128e5f2eb7b9ad61bc2c45e54100f43d939480569c8e0`
- Observer: `http://127.0.0.1:8665/`
- Review projection: `true`
- Runtime admitted: `false`

## Gate Status

`gate-02-identity-anchors` has passed technical review for candidate motion
authoring. Product approval remains pending, and exact-hash runtime admission
remains blocked behind the complete 48-pose visual, motion, determinism, and
side-by-side acceptance gates.
