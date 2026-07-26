# Liora Kane 48-Pose Candidate

Date: 2026-07-26
Decision: static visual identity gate passed for product review
Product approval: pending
Projection: review-only
Runtime admission: denied

## Exact Candidate

- Artifact SHA-256: `811b8c9f954dbd72f901f464ce7e9fba53cbf6183a4ab4f33afb7aec45f62cb4`
- Library-index SHA-256: `b4f3bf1416e9c1f49f732b5731b227bb5e71d75191d5774f85262c2f2167597d`
- Authored-manifest SHA-256: `032f89e379e8db2812882482da7c854c5ed9e50839b389a731be7cf49f95e73a`
- Authoring-brief SHA-256: `d43d0c299592fb5fc2ae87e326cad08cfa881a72ce8530021b95734e98fc1291`
- Alpha-extraction-receipts SHA-256: `f8894a0e6b6ba378b42688e9bd575cc8c8c850e933191a8c307b7325472cc77b`
- Canonicalization-receipts SHA-256: `f2f4fe3e644ff8747576e62f0b2e61e28fedd68db69f99bc04633cb09c49a7e6`
- Reconstruction SHA-256: `9bab86d931edc37e3a6a63616b15897309ca777313dbf875f7e492b7b58c4df3`
- Motion-contract SHA-256: `e3a270f2e78e18ac029417a53feb4d86de9832b33e598fe9a72ab46b79000d2b`
- Contact-sheet SHA-256: `f0af7a18e1e72291f82ef04033e7017ca0fec9fb6e965e02f945fb40ab7d2c54`

## Authored Sequences

The twelve authored frames add two six-frame performances:

1. `g7`, `empathetic_dialogue`: notice, invite, receive, empathize, offer
   support, and return agency.
2. `g8`, `book_explanation`: frame a question, open the source, locate a
   passage, realize, share the insight, and close while retaining the book.

Both sequences run at 10 fps, hold the final pose, use a fixed root and
dual-foot grounded support, and expose marker-safe interruption points.

## Artifact Evidence

- The supplied 36 RGBA pixel graphs remain byte-for-byte unchanged.
- Authored poses `037`-`048` have full-size chroma sources, extracted-alpha
  intermediates, canonical RGBA frames, and complete portable receipt chains.
- Every canonical destination ends on baseline `1185` and respects the
  69-pixel top and horizontal margins.
- Poses `042`, `043`, and `045` use integer translation only. The remaining
  authored silhouettes use the explicit receipted LANCZOS oversize-fit path;
  the minimum scale is `0.9712793733681462`.
- Two consecutive builds reproduced the artifact and library-index hashes.
- Review metadata records `review_projection: true` and
  `runtime_admitted: false` across the artifact, library, sequences, and motion
  contract.

## Visual Identity Gate

Full-size inspection finds Liora recognizable throughout the authored set:
long brown curls, warm face, gray hoodie with drawstrings and pockets, teal
plaid trousers, white shoes, voxel proportions, and a grounded silhouette all
remain coherent.

G7 uses soft, asymmetrical hand and torso acting without introducing props or
root drift. G8 continuously owns exactly one blue book. The book moves from a
closed right-side carry to an open center-chest explanation and returns to the
same retained carry without duplication, hand ambiguity, or color drift.

All twelve authored pose IDs were projected directly through the isolated HD
review server at 1280x720 and captured under
`evidence/character-director/liora-kane-48-parity-2026-07-26/`. The persistent
port-8665 observer displays this exact candidate beside approved HD Wizard
Joe. The 12-test focused parity, provenance, receipt-chain, manifest, and
observer suite passed.

A broader 37-test companion-server sweep had one unrelated existing failure:
`/api/avatar/wizard/performance-context/prepare-score` returned service
unavailable before the expected bearer rejection. That route is outside the
Liora artifact and review projector path and is not counted as a Liora gate.

## Remaining Gate

This document does not constitute product visual approval. Product approval is
pending for this exact artifact and library-index pair. Until that approval is
recorded, the candidate remains review-only and runtime admission remains
false.
