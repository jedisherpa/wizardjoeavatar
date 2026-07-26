# Kai Renner 48-Pose Candidate

Date: 2026-07-25
Decision: static visual identity gate passed for product review
Product approval: pending
Projection: review-only
Runtime admission: denied

## Exact Candidate

- Artifact SHA-256: `2e15a54fda170005919711a0d9177253880cd169cd5d300349845d6b48569873`
- Library-index SHA-256: `768854f8c57528f51768198bc126d75dd61199cd372b6abca41e2aa8a35ab980`
- Authored-manifest SHA-256: `1150cb6d315823b0899e41ad2e7701ca038bca05b8ab648819c47d570551cc6b`
- Authoring-brief SHA-256: `e50fb9aace346b169c736f4728aead77f5bfb5b87fd05051b06d903688db2208`
- Alpha-extraction-receipts SHA-256: `46c6c458f911423bb244df328b1780fd4a54b1b0a506d80d38f4e150f88f1828`
- Canonicalization-receipts SHA-256: `3249ece047e6c14330aae17d162de8de24383be5e18591ab222c07cd78c7ce31`
- Reconstruction SHA-256: `f300216c7c571cf29bc488bf939e9ca0d4d0bc4483964e56f44671e5413a32b8`
- Motion-contract SHA-256: `0e4c99b1c398f7666362e26992b9e8be2d2206d66dcab697207eead2796580be`
- Contact-sheet SHA-256: `2ec923cf6b3bc0ea45eee4d6bf065feb0f39fdfa5e35e6bc74f885da0e95bfe2`

## Authored Sequences

The twelve authored frames add two six-frame performances:

1. `g7`, `counter_service_exchange`: receive, welcome, listen, confirm,
   acknowledge, and reopen. The sequence loops.
2. `g8`, `craft_quality_explanation`: collect, frame the subject, state the
   first criterion, compare, check precision, and approve. The sequence holds
   pose `048`.

Both sequences run at 8 fps with a fixed root, dual-foot grounded support, and
marker-safe interruption.

## Artifact Evidence

- The reconstruction manifest records 48 poses in eight six-frame sequences.
- Authored poses `037`-`048` have chroma sources, extracted-alpha
  intermediates, canonical RGBA frames, and per-frame receipts.
- Poses `044`, `046`, and `047` use explicit receipted oversize fits of
  `1.4134%`, `1.4134%`, and `1.9332%`; the other nine authored poses use
  translation only.
- All twelve authored destination boxes end on baseline `1185`.
- The review metadata records `review_projection: true`.
- The authored manifest, reconstruction, library index, sequences, and review
  motion contract retain `runtime_admitted: false`.

## Visual Identity Gate

Full-size inspection finds Kai recognizable across all twelve
authored poses: the black `BAKE` cap remains readable and unmirrored, and the
rectangular glasses, beard, mustard sweater, blue trousers, black shoes, voxel
construction, and warm palette remain coherent. The silhouettes are complete,
and no chroma fringe is visible on the transparent full-size frames.

All twelve authored pose IDs were projected directly through the alternate HD
review server and captured under
`evidence/character-director/kai-renner-48-parity-2026-07-25/`. Port 8665 also
displayed the exact candidate beside approved HD Wizard Joe. The 37-test
focused parity/provenance suite passed. These are technical-review receipts,
not product approval.

## Remaining Gate

This document does not constitute product visual approval. Product approval is
pending for this exact artifact and library-index pair. Until that approval is
recorded, the candidate remains review-only and runtime admission remains
false.
