# Orion Vale 48-Pose Candidate

Date: 2026-07-25
Decision: technical candidate accepted for product review
Runtime admission: denied

## Exact Candidate

- Artifact SHA-256: `53b769a5a6c1ef2ed9c129e750699614f4ed3d87cd21436ada4e0cd60bdd70ab`
- Library-index SHA-256: `4e2333aedde7d48edae5b9431c97f275d4aeab38441211a6fdaa26c87a93a943`
- Authored-manifest SHA-256: `f53e8fd2f16a29b70e57fb7fa70863ef633e1911f36f23ade2d7edb195e6adca`
- Reconstruction SHA-256: `9bdeabec0c0691d9b8bee258932ed80927605b16ebc5c9458369c85cde2f89df`
- Motion-contract SHA-256: `ce5ebba539f5511ba70e089e4e9840ce22b536fd0a039eb7f37edbf09fed1738`
- Contact-sheet SHA-256: `389f03a1a742366df723510809be0d1466699976fa768c73ad8444b60b3e0271`

## Verification

- 48 poses decode through `HDPoseLibrary`.
- Poses `001`-`036` match the supplied-source RGBA records.
- Poses `037`-`048` match the canonical authored RGBA sources.
- 39 focused and adjacent tests passed.
- Every new frame passed individual full-size projection.
- `g8` holds pose `048` instead of looping to pose `043`.
- The 8665 health contract reports `review_projection: true` and
  `runtime_admitted: false`.

## Remaining Gate

This document does not constitute product visual approval. The candidate stays
out of the production registry until the user approves this exact artifact and
library-index pair.
