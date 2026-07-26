# Draven Holt 48-Pose Candidate

Date: 2026-07-25
Decision: static visual identity gate passed for product review
Product approval: pending
Projection: review-only
Runtime admission: denied

## Exact Candidate

- Artifact SHA-256: `ac51bba7f40bd42b374857b3070d62716f878894b99190d76cd434f08a843e82`
- Library-index SHA-256: `6fc822bf34011fa0d3e110a1c261851c04ceadab35184e9e95db378b11ce0069`
- Authored-manifest SHA-256: `9fed5b1dc78ffab132885742589ba5021a8602a33c5ca804ede562870897271c`
- Authoring-brief SHA-256: `af2fd2a038d0317e7a7d8b86c9339baa3af740fea35e748cd229759226dc6342`
- Alpha-extraction-receipts SHA-256: `23cb83653f8a9de2bc4c71f96c6d303d732c481c868e883a136022c29789de26`
- Canonicalization-receipts SHA-256: `b6ed2386bb2a372581b5ca680e23e1529a71dbf57db2443b35a918b39bf45273`
- Reconstruction SHA-256: `0aecf781a48b5bc4862cc6ce50a29fb2a91406a7ebe2f6941e9bfe604f08eebe`
- Motion-contract SHA-256: `10a9678fdcc13a902f7ad32c000e1ac3bfd8d5904c14b3e15903510c746b98b4`
- Contact-sheet SHA-256: `b40ffd132a58e8e69bf5d7a93e1fdbce6a72d482c88966282399e6396451d797`

## Authored Sequences

The twelve authored frames add two six-frame performances:

1. `g7`, `foreman_status_exchange`: receive, grant the floor, listen, probe,
   assign, and confirm. The sequence loops.
2. `g8`, `site_safety_intervention`: detect, stop, contain, reroute, verify,
   and release. The sequence holds pose `048`.

Both sequences run at 8 fps with a fixed root, dual-foot grounded support, and
marker-safe interruption.

## Artifact Evidence

- The supplied 36 RGBA pixel graphs remain byte-for-byte unchanged.
- Authored poses `037`-`048` have chroma sources, extracted-alpha
  intermediates, canonical RGBA frames, and complete per-frame receipt chains.
- Every canonical destination ends on baseline `1185` and respects the
  69-pixel top margin.
- Explicit receipted fits reduced the silhouettes by 0.18-3.96 percent. The
  strict canonicalizer was not weakened.
- Two consecutive builds reproduced the artifact and library-index hashes.
- The review metadata records `review_projection: true` and retains
  `runtime_admitted: false` across the artifact, library, sequences, and
  motion contract.

## Visual Identity Gate

Full-size inspection finds Draven recognizable throughout the authored set:
the black flat cap and suit, orange shirt and tie line, bright-green
rectangular glasses, beard, black shoes, voxel proportions, and grounded
silhouette remain coherent.

Draven's left hand continuously owns exactly one brown clipboard, an unchanged
white four-item checklist, and one yellow-orange pencil. His free right hand
performs every conversational and safety gesture. No frame duplicates,
transfers, or loses the prop.

All twelve authored pose IDs were projected directly through the alternate HD
review server and captured under
`evidence/character-director/draven-holt-48-parity-2026-07-25/`. The persistent
port-8665 observer also displays this exact candidate beside approved HD
Wizard Joe. The 32-test focused parity, provenance, receipt-chain, and observer
suite passed.

## Remaining Gate

This document does not constitute product visual approval. Product approval is
pending for this exact artifact and library-index pair. Until that approval is
recorded, the candidate remains review-only and runtime admission remains
false.
