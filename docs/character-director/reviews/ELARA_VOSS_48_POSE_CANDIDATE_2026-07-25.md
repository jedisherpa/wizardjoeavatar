# Elara Voss 48-Pose Candidate

Date: 2026-07-25
Decision: technical candidate accepted for product review
Runtime admission: denied

## Exact Candidate

- Artifact SHA-256: `8fd74202c038028af63e6fff9a9e8b8c2d82261bc3e30b5d2447a93af632f53c`
- Library-index SHA-256: `7fd020cb347ec6726e1dd60939166d9659775fe626ce8511108f38441708bde2`
- Authored-manifest SHA-256: `e773d36a6e33a2abfc36ea3066a363ff93471a0a50eb7bff2b876e8e97698392`
- Reconstruction SHA-256: `7405ceedb3936dcb7571b1e4b8ea56bcbf1a8a9470f2760c52155cdf58ec796e`
- Motion-contract SHA-256: `a24a1597aad39c522b3f77356ca141e427fa3b8b8f8b022fcffc19072a697b0b`
- Contact-sheet SHA-256: `fcef489937907925a0db255fcfedce3480f87a87367ee20638f0fe642f361b7a`
- Canonicalization-receipts SHA-256: `ec5b6f4ed2410c0f0afc56a79c3c0811ab1554f372221488f3e70da5306c5dfb`

## Authored Sequences

The twelve missing poses add two six-frame performances:

1. `g7` receives a cue, offers the microphone, listens, reclaims the floor,
   clarifies one point, and invites the response.
2. `g8` takes an editorial breath, states the headline, delivers one fact,
   compares alternatives, concludes, and signs off.

Both sequences keep dual-foot support, a fixed root, marker-safe
interruptibility, and continuous ownership of exactly one microphone.

## Verification

- 48 poses decode through `HDPoseLibrary`.
- Poses `001`-`036` match the supplied-source RGBA records.
- Poses `037`-`048` match the canonical authored RGBA sources.
- Two consecutive corrected builds produced identical candidate hashes.
- Every new frame passed individual full-size projection on port 8667.
- Dark-background review rejected a chroma-fringe intermediate before rebuild.
- Seven oversize silhouettes use a small, explicit, receipted canonical fit.
- Port 8665 reports `review_projection: true` and
  `runtime_admitted: false`.

## Remaining Gate

This document does not constitute product visual approval. The candidate stays
out of the production registry until the user approves this exact artifact and
library-index pair.
