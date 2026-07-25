# Orion Vale Technical Build Audit

Date: 2026-07-25
Status: review candidate compiled; runtime admission denied

## Build Boundary

The safe implementation is a generic authored-parity merger. It combines
Orion's immutable 36-pose source artifact with 12 canonical RGBA inputs. It
does not alter the source ZIP census, production character registry, runtime
admission ledger, or ASCILINE transport.

## Enforced Invariants

- Exactly 48 unique poses and eight six-frame sequences.
- `g7` owns `037`-`042`; `g8` owns `043`-`048`.
- Existing poses `001`-`036` remain byte-identical.
- All new paths, PNG hashes, and RGBA hashes are distinct.
- Every new PNG is RGBA, 1254x1254, transparent, uncropped, margin-safe, and
  aligned to baseline 1185.
- Authority, existing reconstruction, existing artifact, authored source,
  library index, and output artifact are hash-bound.
- The artifact, index, shard, sequences, poses, reconstruction, and motion
  contract all retain `runtime_admitted: false`.
- The library index is published last.

## Determinism

Two clean-directory builds must match for:

1. `.wjpose` artifact bytes.
2. Library-index bytes.
3. Reconstruction-manifest bytes.
4. Contact-sheet bytes.
5. Review-motion-contract bytes.
6. All 48 decoded RGBA pose hashes.

The focused test suite exercises clean rebuilds, source checksum drift,
duplicate-source rejection, loop-contract contradictions, direct pixel
preservation, canonicalization, and observer admission boundaries.

## Projection

The 8665 observer runs approved HD Wizard Joe on the left and Orion's
review-only 48-pose artifact on the right. All 12 authored frames were frozen
and inspected through the actual canvas projector. The non-looping `g8`
sequence was also verified to stop and hold on pose `048`.

The contact sheet is navigation evidence only. Product visual approval remains
pending.
