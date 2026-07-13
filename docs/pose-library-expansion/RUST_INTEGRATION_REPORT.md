# Rust Pose Integration Report

Status: implementation, deterministic source-frame verification, and final live-browser validation complete on 2026-07-13. Independent verification is recorded in the animation-quality reports.

## Integrated library

| Surface | Result |
|---|---:|
| New catalog records | 30 |
| New unique geometries | 29 |
| New aliases | 1 |
| Runtime unique geometries, including baseline | 39 |
| Runtime catalog frames, including alias | 40 |
| Canonical grid | 72 x 96 cells |
| Canonical root | `[36, 95]` |

`WJFA-10` / `fly_front_hover_ready` is an intentional alias of `WJFA-01` / `fly_front_hover_neutral`. It adds a semantic catalog entry without duplicating geometry.

The Rust compiler output is:

```text
rust/wizard_avatar_pose_tool/target/pose-tool/compiled-30-poses-v3.json
SHA-256 ab99ca25347d8eab035dd231a11ad2eff1f12f2838752c277732ab5bf4cb9cf8
```

The production engine embeds the deterministic gzip asset:

```text
rust/wizard_avatar_engine/assets/future_pose_library.v3.json.gz
SHA-256 32b7620b6848ca8cdf619278445d553cbfd25673e44f5ef21859fcb4a0c55ef4
```

The compiler records archive SHA-256 `cd9548b5eb68634bf7bdcf0f02b775361cbc30083b28a8616b87b49fd525b334` and palette SHA-256 `3779555a8324110685673259ea1e9bb88dff2b0b36818b898df0660a88b77f8e`.

## Motion runtime

Rust owns 11 pose clips: `ground_walk`, `ground_run`, `hover_flap`, `bank_glide`, `staff_combo`, `reaction_recover`, `celebrate`, `conversation`, `explain`, `point`, and `think`. Together they exercise all 30 new catalog records.

Clip replacement and direct-pose replacement wait for the current contact-aware handoff to become stable. Restoration ownership survives clip replacement: an interrupted explicit pose is restored explicitly, while an implicit direction pose returns through the current direction and releases the override. Looped locomotion clips retain their phase until replaced or cleared.

Semantic actions map to Rust clips as follows:

| Action | Rust clip |
|---|---|
| `explaining` | `explain` |
| `thinking` | `think` |
| `pointing` | `point` |
| `magic_cast` | `staff_combo` |
| `reaction` | `reaction_recover` |
| `idle` | clears the active clip and transitions smoothly to the current direction pose |

## Deterministic frame result

The Rust evidence runner captured every simulation frame at 60 Hz for every clip, all 170 authored directed transitions, speech/expression overlays, locomotion, and interruption/replacement/restoration.

| Metric | Result |
|---|---:|
| Captured PNG frames per pass | 7,173 |
| Consecutive frame pairs checked | 6,991 |
| Complete passes | 2 |
| Rust clips | 11 |
| Authored transitions | 170 |
| Static catalog frames | 40 |
| Quality failures | 0 |
| Frames with all 25 semantic anchors and contacts | 7,173 |
| Adaptive source/decode parity | PASS |
| Presentation-accepted logical parity | PASS |
| Presented sequence | contiguous `0..7172` |
| Deterministic parity | PASS |

Both complete animation passes produced stream SHA-256:

```text
c53e11ae34aca237be2325b44005ecf6698ecc62001d2461b24ca90d4dd65a1b
```

Primary evidence:

```text
evidence/pose-library-expansion/rust-final/static-census/manifest.json
evidence/pose-library-expansion/rust-final/static-census/contact-sheet.png
evidence/pose-library-expansion/rust-final/animation-verification/manifest.json
evidence/pose-library-expansion/rust-final/animation-verification/frame-ledger.ndjson
evidence/pose-library-expansion/rust-final/animation-verification/animation.mp4
evidence/pose-library-expansion/rust-final/animation-verification/timeline-contact-sheet.png
```

## Reproduce

```bash
cd rust/wizard_avatar_pose_tool
cargo fmt --all -- --check
cargo test
cargo clippy --all-targets -- -D warnings

cd ../wizard_avatar_engine
cargo fmt --all -- --check
cargo test
cargo clippy --all-targets -- -D warnings
cargo run --release --bin wizard-avatar-pose-evidence
```

The evidence run is intentionally strict: one failed frame, unequal replay hash, missing or extra PNG, mismatched ledger path, unresolved catalog record, invalid staff topology, detached semantic anchor, or unexplained region fragmentation fails the command. Transition capture length is derived from authored anchor travel, so every matrix entry is recorded through completion rather than for a fixed window.

## Live browser result

The final debug server was rebuilt from the verified sources and served on `http://127.0.0.1:8787`. The adaptive WebSocket remained live, the semantic state API returned the expected neutral south-facing state with no stale explicit pose after an interrupted action restored, and the browser console contained no warnings or errors.

Responsive checks passed at 1280 x 800 and 390 x 844. The page had no horizontal overflow, the toolbar remained inside the viewport, and every movement, expression, action, speech, and tour control remained visible at the mobile breakpoint. All 18 browser-client module tests passed, including the no-PNG-runtime assertion and repeat-until-Stop motion-tour coverage.
