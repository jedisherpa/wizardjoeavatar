# WizardJoe Pose Library Expansion

This directory is the execution record for integrating the pose archives supplied on 2026-07-12. It must remain sufficient for a new agent to determine what exists, what is in progress, who owns it, what evidence is required, and what may be integrated next.

## Source archives

| Archive | SHA-256 | Contents | Disposition |
|---|---|---:|---|
| `/Users/paul/Downloads/Wizard Joe Poses.zip` | `eb57e0e8c2313a7404e3ec0dd3638ce770eedfafd42671888cd18f954f8d482c` | 11 PNGs | Ten current-library source poses plus the original target image; audit as baseline/duplicates. |
| `/Users/paul/Downloads/Wizard Joe Poses 2.zip` | `2d81094336d8151958056b635c77998b2143a596af76200e0dbba7a175551df6` | 10 PNGs | New candidate poses, tracked as `WJP2-01` through `WJP2-10`. |
| `/Users/paul/Downloads/Wizard Joe Poses Flying and Action.zip` | `c00e56b139c00c42d51652b3683109ae38263768dc959a25b17f83e533b5bfff` | 20 PNGs | Flying and action candidates, tracked as `WJFA-01` through `WJFA-20`. |

Baseline repository commit: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`.

Baseline manifest SHA-256: `784b0fb33776b28e82c8b8fe05ee48fbb05a147656077ee2b0c88545602c5fff`.

Baseline generated library SHA-256: `fb0cf0098df8435b39378113955d98aac275e25f72702f2a48e8880ec51522b8`.

## Truth surfaces

- [POSE_TRACKER.md](POSE_TRACKER.md) is the coordinator-owned summary ledger.
- `registry.json` is the coordinator-owned machine-readable ledger and integration-lock source.
- [WORKFLOW.md](WORKFLOW.md) defines status transitions, ownership, gates, and commands.
- `items/WJP2-XX.md` is the agent-owned record for one candidate pose.
- `evidence/pose-library-expansion/WJP2-XX/` contains generated visual and verification evidence.
- `evidence/pose-library-expansion/intake/manifest.json` is the reproducible hash and dimension catalog for all 30 source PNGs.
- `evidence/pose-library-expansion/intake/contact-sheets/` contains labeled overviews of both supplied packs.
- `assets/reference/motion_sources/manifest.json` is the Python server's production pose manifest.
- `tools/integrate_pose_candidate.py` is the rollback-safe, one-candidate integration operator.
- `tools/integrate_pose_queue.py` runs those transactions serially.
- `wizard_avatar/definitions/reference_avatar_pose_cells.json` is the deterministic Python runtime library.

## Production integration rule

This program's production path is the ASCILINE Python server on port 8765. Integration is serial: exactly one pose may hold `INTEGRATING`, its manifest entry and source are applied transactionally, the Python library is regenerated, and all gates pass before the next candidate begins.

## Completion definition

The expansion is complete when every candidate is terminal (`VERIFIED`, `DUPLICATE`, or `REJECTED`), repeat generation is byte-identical, the full Python tests and strict transition matrix pass, and the live port-8765 browser presents every accepted pose while moving without console errors.
