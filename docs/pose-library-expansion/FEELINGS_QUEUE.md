# Wizard Joe Feelings Queue

Status: `INTEGRATED_RUST` on 2026-07-13. All 50 unique references are embedded as procedural Rust geometry; the ten repeated files remain reference-only duplicates.

## Intake summary

| Field | Value |
|---|---|
| Source archive | `/Users/paul/Downloads/Wizard Joe Poses Feelings.zip` |
| Archive SHA-256 | `e2eaf187b8f01f4c955ab1659a6fa351129a8e2eb73eb3973f250bf6c6c4e6c7` |
| Preserved PNGs | 60 |
| Unique PNG hashes | 50 |
| Candidate IDs | `WJFL-01` through `WJFL-60` |
| Rust catalog orders | 31 through 80 after exact-hash deduplication |
| Semantic IDs | Assigned for all 50 unique geometries and all 10 duplicate references |
| Runtime policy | Reference-only; Rust must procedurally generate accepted geometry and motion |

The full per-file ledger, including source filename, original order, Rust ownership, semantic ID, integration status, and exact-duplicate links, is in [feelings-queue.json](feelings-queue.json). Hashes, dimensions, repository paths, and source disposition are in `evidence/pose-library-expansion/intake/feelings-manifest.json`. The serial compiler ledger is in `evidence/pose-library-expansion/rust-v4/admission-ledger.json`.

## Visual index

![WJFL-01 through WJFL-60](../../evidence/pose-library-expansion/intake/contact-sheets/wizard-joe-poses-feelings.png)

The six contact-sheet rows are the integration batches:

1. `WJFL-01..10`: action and locomotion.
2. `WJFL-11..20`: action and gesture.
3. `WJFL-21..30`: conversation, reaction, and magic gesture.
4. `WJFL-31..40`: full-body joy, sadness, anger, fear, shame, disgust, surprise, pride, guilt, and love.
5. `WJFL-41..50`: byte-identical repeats of `WJFL-01..10` retained for archive fidelity.
6. `WJFL-51..60`: close-up versions of the ten labeled feelings.

## Reproduce the intake

After extracting only the non-`__MACOSX` PNGs to `evidence/pose-library-expansion/intake/feelings/`, run:

```bash
cd rust/wizard_avatar_pose_tool
cargo run --locked --bin wizard-avatar-feelings-intake -- \
  ../.. "/Users/paul/Downloads/Wizard Joe Poses Feelings.zip"
```

The Rust command regenerates `feelings-manifest.json`, `feelings-queue.json`, and the labeled contact sheet. It fails unless exactly 60 RGB PNGs are present.

Promote and revalidate the integrated v4 archive with:

```bash
cd rust/wizard_avatar_pose_tool
cargo run --locked --release --bin wizard-avatar-pose-promote -- ../..
```

## Completed integration gate

- 50 unique candidates were admitted one at a time; every admission records its cumulative catalog and geometry count.
- `WJFL-41..50` are marked `DUPLICATE_REFERENCE` and compile no duplicate geometry.
- `WJFL-51..60` are full-body facial variants of their matching emotion poses, preserving feet, staff, wings, contacts, and root topology.
- The runtime contains 89 geometries plus one alias and loads only the compressed v4 cell archive.
- All 621 authored directed transitions and all repeated WJFL clip frames pass the breakup gate.
- Source PNG paths and PNG bytes are absent from the runtime archive.
