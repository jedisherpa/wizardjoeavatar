# Aurelia Finch 48-Pose Candidate

Date: 2026-07-25
Decision: technical candidate accepted for product review
Runtime admission: denied

## Exact Candidate

- Artifact SHA-256: `e7e44013b9356720357e9dc0114909ddaadee34a3e26d2de666751b7e7d136ad`
- Library-index SHA-256: `b4d19c01b0771a1ed49a52c42051a4a82c9e347efc6152d9023b2656f596e9b1`
- Authored-manifest SHA-256: `9e479e3072030af885c4d9686ba32e2808d57212913e8f1651e6f26f8f62b51e`
- Reconstruction SHA-256: `74aaaef9de21cca18429eb87d9bde97491bf0ef650b4eecbc8ba8cca803c549f`
- Motion-contract SHA-256: `51057a8f201423174447c502d6760ec164c50e0141ff212e7bf929895ad42d4b`
- Contact-sheet SHA-256: `83b4b403d428950ebad8dad967d1a08df255ea60732a3285848dee8eb0b219b0`

## Authored Sequence

The six missing `g7` poses add a book-centered communication performance:

1. Attentive receipt with the closed book at her left hip.
2. Closed-book raise toward her sternum.
3. Open-book consultation.
4. Specific passage verification.
5. Viewer-facing open-palm explanation while retaining the open book.
6. Calm recovery with the closed book held close.

The sequence is dual-foot grounded, root fixed, marker-safe, and loops at
8 frames per second.

## Verification

- 48 poses decode through `HDPoseLibrary`.
- Poses `001`-`042` match the supplied-source RGBA records.
- Poses `043`-`048` match the canonical authored RGBA sources.
- Two consecutive builds produced identical candidate hashes.
- 25 focused and adjacent JoeVille/projector tests passed.
- Every new frame passed individual full-size projection on port 8667.
- Port 8665 reports `review_projection: true` and
  `runtime_admitted: false`.

## Remaining Gate

This document does not constitute product visual approval. The candidate stays
out of the production registry until the user approves this exact artifact and
library-index pair.
