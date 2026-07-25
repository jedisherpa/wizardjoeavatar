# Selene Hart 48-Pose Candidate

Date: 2026-07-25
Decision: technical candidate accepted for product review
Runtime admission: denied

## Exact Candidate

- Artifact SHA-256: `1e9b791070658d79d1a517557c819d900d5c656429f3b643bb268e2fe4374781`
- Library-index SHA-256: `86f5ff6587bf1714991e8a0ac66d40007bc25b5c5a0ecef0a960e5f7a12439b4`
- Authored-manifest SHA-256: `ccd96e8a8285811450ccc56a642e0fa17a819428a8166f58eae143d1a298234f`
- Reconstruction SHA-256: `22ede6b8587d329a30d80fcf40f8d99bfa48e04ffc72428b4aa2562b9e077f39`
- Motion-contract SHA-256: `8ca2f01db315099fd2c469a750c54a421201b29521440c0304a73bc7d3869075`
- Contact-sheet SHA-256: `fe3cffec7b288b0d24b0b7b708e169bdaa6d2c7cf0dbab375997f15740a4c730`

## Authored Sequences

The twelve missing poses add two six-frame performances:

1. `g7` makes the criterion visible by receiving, raising, framing, indicating,
   explaining, and resolving with the striped hoop.
2. `g8` establishes a calm boundary, verifies the visible criterion, offers the
   next step, and returns to a grounded handoff.

Both sequences keep dual-foot support, a fixed root, marker-safe
interruptibility, and continuous hoop ownership.

## Verification

- 48 poses decode through `HDPoseLibrary`.
- Poses `001`-`036` match the supplied-source RGBA records.
- Poses `037`-`048` match the canonical authored RGBA sources.
- Two consecutive corrected builds produced identical candidate hashes.
- Every new frame passed individual full-size projection on port 8667.
- Full-size review rejected five soft-matte-contaminated intermediates before
  the final hard-key extraction and deterministic rebuild.
- Port 8665 reports `review_projection: true` and
  `runtime_admitted: false`.

## Remaining Gate

This document does not constitute product visual approval. The candidate stays
out of the production registry until the user approves this exact artifact and
library-index pair.
