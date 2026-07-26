# Thorne Vale 48-Pose Candidate

Date: 2026-07-25
Decision: technical candidate accepted for product review
Runtime admission: denied

## Exact Candidate

- Artifact SHA-256: `787f6745558e2d33683c42ea84a7b81b5883ea8192862d921b917de1b26a67cc`
- Library-index SHA-256: `937abf76db2da70cb85d36237b9124a2e5dd59b3bfc19f240563e20a71abcde2`
- Authored-manifest SHA-256: `fe2bf2282573bb4186bc9f39b822ac0d46d80a82349e370e2cad343e3ba99321`
- Reconstruction SHA-256: `a57b7886f20b0a2fd18af8fc7fe4df95bccb127075bf84e902ffb158d1ace54c`
- Motion-contract SHA-256: `1c403584f625f1e533538c516c7e00fc803b8dfbc8623e7b3379afd6149bb037`
- Contact-sheet SHA-256: `e46389068cf2f9faa0374b2dbe84799b293a100214a64748c6d952e9866c8646`

## Authored Sequences

The twelve missing poses add two six-frame performances:

1. `g7` receives a speaker, invites them to continue, listens, weighs the
   petition, acknowledges it, and reopens the floor.
2. `g8` retrieves one scroll, opens and verifies the charter, closes it,
   restores it to the carrier, and commissions the next action.

Both sequences keep dual-foot support, a fixed root, marker-safe
interruptibility, and continuous ownership of the scroll and sheathed tool.

## Verification

- 48 poses decode through `HDPoseLibrary`.
- Poses `001`-`036` match the supplied-source RGBA records.
- Poses `037`-`048` match the canonical authored RGBA sources.
- Two consecutive corrected builds produced identical candidate hashes.
- Every new frame passed individual full-size projection on port 8667.
- Prop continuity rejected one duplicated-scroll intermediate before rebuild.
- Canonical-margin and chroma-fringe failures were corrected without weakening
  the canonical profile.
- Port 8665 reports `review_projection: true` and
  `runtime_admitted: false`.

## Remaining Gate

This document does not constitute product visual approval. The candidate stays
out of the production registry until the user approves this exact artifact and
library-index pair.
