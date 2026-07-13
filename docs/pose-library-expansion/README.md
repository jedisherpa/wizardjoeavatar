# WizardJoe Pose Library Expansion

This directory is the execution record for integrating the pose archives supplied on 2026-07-12 and 2026-07-13. It must remain sufficient for a new agent to determine what exists, what is in progress, who owns it, what evidence is required, and what may be integrated next.

## Source archives

| Archive | SHA-256 | Contents | Disposition |
|---|---|---:|---|
| `/Users/paul/Downloads/Wizard Joe Poses.zip` | `eb57e0e8c2313a7404e3ec0dd3638ce770eedfafd42671888cd18f954f8d482c` | 11 PNGs | Ten current-library source poses plus the original target image; audit as baseline/duplicates. |
| `/Users/paul/Downloads/Wizard Joe Poses 2.zip` | `2d81094336d8151958056b635c77998b2143a596af76200e0dbba7a175551df6` | 10 PNGs | New candidate poses, tracked as `WJP2-01` through `WJP2-10`. |
| `/Users/paul/Downloads/Wizard Joe Poses Flying and Action.zip` | `c00e56b139c00c42d51652b3683109ae38263768dc959a25b17f83e533b5bfff` | 20 PNGs | Flying and action candidates, tracked as `WJFA-01` through `WJFA-20`. |
| `/Users/paul/Downloads/Wizard Joe Poses Feelings.zip` | `e2eaf187b8f01f4c955ab1659a6fa351129a8e2eb73eb3973f250bf6c6c4e6c7` | 60 PNGs | Deferred feelings/action references, tracked as `WJFL-01` through `WJFL-60`; 50 hashes are unique and ten sources are exact repeats. |

Baseline repository commit: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`.

Baseline manifest SHA-256: `784b0fb33776b28e82c8b8fe05ee48fbb05a147656077ee2b0c88545602c5fff`.

Baseline generated library SHA-256: `fb0cf0098df8435b39378113955d98aac275e25f72702f2a48e8880ec51522b8`.

## Truth surfaces

- [POSE_TRACKER.md](POSE_TRACKER.md) is the coordinator-owned summary ledger.
- `registry.json` is the coordinator-owned machine-readable ledger and integration-lock source.
- [FEELINGS_QUEUE.md](FEELINGS_QUEUE.md) and `feelings-queue.json` record the 60 deferred `WJFL` candidates without changing the compiled 30-pose archive.
- [WORKFLOW.md](WORKFLOW.md) defines status transitions, ownership, gates, and commands.
- `items/WJP2-XX.md` is the agent-owned record for one candidate pose.
- `evidence/pose-library-expansion/WJP2-XX/` contains generated visual and verification evidence.
- `evidence/pose-library-expansion/intake/manifest.json` is the reproducible hash and dimension catalog for all 30 source PNGs.
- `evidence/pose-library-expansion/intake/feelings-manifest.json` is the Rust-generated hash, dimension, order, and duplicate catalog for the 60 queued feelings PNGs.
- `evidence/pose-library-expansion/intake/contact-sheets/` contains labeled overviews of the supplied packs.
- `rust/wizard_avatar_pose_tool` owns deterministic source intake and procedural pose compilation.
- `rust/wizard_avatar_engine` owns the production pose library, motion rules, deterministic evidence, ASCILINE delivery, and browser runtime.

## Production integration rule

This program's production path is the Rust ASCILINE server. Integration is serial: exactly one pose may hold `INTEGRATING`, its reference is translated into procedural Rust cell geometry and motion rules, the deterministic library and frame evidence are regenerated, and all gates pass before the next candidate begins. Reference PNGs are never loaded at runtime.

## Completion definition

The completed 30-pose expansion remains frozen and verified. The feelings expansion is complete only when every `WJFL` candidate is terminal (`VERIFIED`, `DUPLICATE`, or `REJECTED`), Rust replay is byte-identical, the full Rust and browser gates pass, and the live browser presents every accepted pose while moving without frame breakup or console errors.
