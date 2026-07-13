# Pose Expansion Tracker

Last coordinator update: 2026-07-13.

## Program status

| Metric | Count |
|---|---:|
| Current production poses | 39 |
| Completed archive candidates | 30 |
| Feelings archive references | 60 |
| Unique feelings source hashes | 50 |
| Queued | 60 |
| Claimed for intake | 0 |
| Analyzed | 0 |
| In integration | 0 |
| Verified new poses | 29 |
| Duplicate/rejected new poses | 1 |

Integration lock: `UNCLAIMED`.

## Existing baseline audit

| Archive entry | Current semantic ID | Status |
|---|---|---|
| `02_41_29 PM (1)` | `front_idle` | BASELINE_EXISTING |
| `02_41_29 PM (2)` | `back_idle` | BASELINE_EXISTING |
| `02_41_29 PM (3)` | `profile_left` | BASELINE_EXISTING |
| `02_41_32 PM (4)` | `profile_right` | BASELINE_EXISTING |
| `02_41_32 PM (5)` | `walk_front_left` | BASELINE_EXISTING |
| `02_41_32 PM (6)` | `walk_front_right` | BASELINE_EXISTING |
| `02_41_34 PM (7)` | `back_left` | BASELINE_EXISTING |
| `02_41_34 PM (8)` | `back_right` | BASELINE_EXISTING |
| `02_41_34 PM (9)` | `explaining` | BASELINE_EXISTING |
| `02_41_35 PM (10)` | `magic_cast` | BASELINE_EXISTING |
| `01_57_13 PM` | canonical target image | BASELINE_EXISTING |

## New candidate queue

| Order | Candidate | Archive entry | Owner | Proposed semantic ID | Status | Item record |
|---:|---|---|---|---|---|---|
| 1 | WJP2-01 | `08_03_21 PM (1)` | coordinator | `run_front_airborne_reach` | VERIFIED | [WJP2-01](items/WJP2-01.md) |
| 2 | WJP2-02 | `08_03_21 PM (2)` | coordinator | `run_front_airborne_drive` | VERIFIED | [WJP2-02](items/WJP2-02.md) |
| 3 | WJP2-03 | `08_03_21 PM (3)` | coordinator | `front_crouch_guard` | VERIFIED | [WJP2-03](items/WJP2-03.md) |
| 4 | WJP2-04 | `08_03_22 PM (4)` | coordinator | `front_reaction_jump_fist_staff` | VERIFIED | [WJP2-04](items/WJP2-04.md) |
| 5 | WJP2-05 | `08_03_22 PM (5)` | coordinator | `front_kneel_staff_brace` | VERIFIED | [WJP2-05](items/WJP2-05.md) |
| 6 | WJP2-06 | `08_03_22 PM (6)` | coordinator | `front_staff_guard_windup` | VERIFIED | [WJP2-06](items/WJP2-06.md) |
| 7 | WJP2-07 | `08_03_22 PM (7)` | coordinator | `front_staff_guard_low` | VERIFIED | [WJP2-07](items/WJP2-07.md) |
| 8 | WJP2-08 | `08_03_23 PM (8)` | coordinator | `walk_front_right_lift` | VERIFIED | [WJP2-08](items/WJP2-08.md) |
| 9 | WJP2-09 | `08_03_23 PM (9)` | coordinator | `front_crouch_reaction_staff_planted` | VERIFIED | [WJP2-09](items/WJP2-09.md) |
| 10 | WJP2-10 | `08_03_23 PM (10)` | coordinator | `front_victory_cast` | VERIFIED | [WJP2-10](items/WJP2-10.md) |
| 11 | WJFA-01 | `08_15_09 PM (1)` | coordinator | `fly_front_hover_neutral` | VERIFIED | [WJFA-01](items/WJFA-01.md) |
| 12 | WJFA-02 | `08_15_09 PM (2)` | coordinator | `fly_front_knee_up` | VERIFIED | [WJFA-02](items/WJFA-02.md) |
| 13 | WJFA-03 | `08_15_09 PM (3)` | coordinator | `fly_front_wings_up` | VERIFIED | [WJFA-03](items/WJFA-03.md) |
| 14 | WJFA-04 | `08_15_10 PM (4)` | coordinator | `fly_front_wings_down` | VERIFIED | [WJFA-04](items/WJFA-04.md) |
| 15 | WJFA-05 | `08_15_10 PM (5)` | coordinator | `fly_southeast_forward_glide` | VERIFIED | [WJFA-05](items/WJFA-05.md) |
| 16 | WJFA-06 | `08_15_10 PM (6)` | coordinator | `fly_southwest_banked_staff` | VERIFIED | [WJFA-06](items/WJFA-06.md) |
| 17 | WJFA-07 | `08_15_10 PM (7)` | coordinator | `fly_southeast_banked_staff` | VERIFIED | [WJFA-07](items/WJFA-07.md) |
| 18 | WJFA-08 | `08_15_11 PM (8)` | coordinator | `fly_southeast_cheer` | VERIFIED | [WJFA-08](items/WJFA-08.md) |
| 19 | WJFA-09 | `08_15_11 PM (9)` | coordinator | `fly_southeast_staff_forward` | VERIFIED | [WJFA-09](items/WJFA-09.md) |
| 20 | WJFA-10 | `08_15_11 PM (10)` | Hooke | `fly_front_hover_ready` | DUPLICATE | [WJFA-10](items/WJFA-10.md) |
| 21 | WJFA-11 | `08_15_41 PM (1)` | coordinator | `front_run_charge_right_plant` | VERIFIED | [WJFA-11](items/WJFA-11.md) |
| 22 | WJFA-12 | `08_15_41 PM (2)` | coordinator | `front_crouch_landing_staff_plant` | VERIFIED | [WJFA-12](items/WJFA-12.md) |
| 23 | WJFA-13 | `08_15_41 PM (3)` | coordinator | `front_magic_staff_thrust` | VERIFIED | [WJFA-13](items/WJFA-13.md) |
| 24 | WJFA-14 | `08_15_41 PM (4)` | coordinator | `front_airborne_fall_back_staff` | VERIFIED | [WJFA-14](items/WJFA-14.md) |
| 25 | WJFA-15 | `08_15_41 PM (5)` | coordinator | `front_celebrate_wings_staff_up` | VERIFIED | [WJFA-15](items/WJFA-15.md) |
| 26 | WJFA-16 | `08_15_42 PM (6)` | coordinator | `front_staff_block_horizontal` | VERIFIED | [WJFA-16](items/WJFA-16.md) |
| 27 | WJFA-17 | `08_15_42 PM (7)` | coordinator | `front_point_direct_staff_held` | VERIFIED | [WJFA-17](items/WJFA-17.md) |
| 28 | WJFA-18 | `08_15_42 PM (8)` | coordinator | `front_celebrate_jump_staff_up` | VERIFIED | [WJFA-18](items/WJFA-18.md) |
| 29 | WJFA-19 | `08_15_42 PM (9)` | coordinator | `front_shush_secret_staff_held` | VERIFIED | [WJFA-19](items/WJFA-19.md) |
| 30 | WJFA-20 | `08_15_42 PM (10)` | coordinator | `front_staff_spin_flourish` | VERIFIED | [WJFA-20](items/WJFA-20.md) |

## Deferred feelings queue

The 60 references in `Wizard Joe Poses Feelings.zip` are queued as `WJFL-01` through `WJFL-60`, with global integration orders 31 through 90. Semantic IDs and owners remain unassigned until visual intake. The exact queue is recorded in [FEELINGS_QUEUE.md](FEELINGS_QUEUE.md), `feelings-queue.json`, and the labeled Rust-generated contact sheet.

| Queue range | Global orders | Sources | Status | Notes |
|---|---:|---:|---|---|
| `WJFL-01..10` | 31-40 | 10 | QUEUED | First action/locomotion batch. |
| `WJFL-11..20` | 41-50 | 10 | QUEUED | Second action/gesture batch. |
| `WJFL-21..30` | 51-60 | 10 | QUEUED | Conversation, reaction, and magic gesture batch. |
| `WJFL-31..40` | 61-70 | 10 | QUEUED | Full-body labeled feelings: joy, sadness, anger, fear, shame, disgust, surprise, pride, guilt, and love. |
| `WJFL-41..50` | 71-80 | 10 | QUEUED | Exact source duplicates of `WJFL-01..10`; retain for archive fidelity and resolve as aliases or duplicates during intake. |
| `WJFL-51..60` | 81-90 | 10 | QUEUED | Close-up labeled feelings matching the same ten-emotion vocabulary. |

## Decision log

| Timestamp | Candidate | Decision | Owner | Evidence |
|---|---|---|---|---|
| 2026-07-12 | PROGRAM | Tracking system created before asset integration | coordinator | Source archive listings and SHA-256 values in [README.md](README.md) |
| 2026-07-12 | WJP2-01..03 | Intake assigned | Einstein | Per-pose item records |
| 2026-07-12 | WJP2-04..07 | Intake assigned | Pauli | Per-pose item records |
| 2026-07-12 | WJP2-08..10 | Intake assigned | Socrates | Per-pose item records |
| 2026-07-12 | WJFA-01..10 | Flying/action intake assigned | Hooke | Per-pose item records |
| 2026-07-12 | WJFA-11..20 | Flying/action intake assigned | Ramanujan | Per-pose item records |
| 2026-07-12 | WJP2-01 | Promoted to serial integration with per-pose `generation_rows: 91` fit policy | coordinator | [WJP2-01](items/WJP2-01.md) |
| 2026-07-12 | WJFA-01..20 | Intake completed: 19 analyzed, WJFA-10 duplicate of WJFA-01 | Hooke / Ramanujan | Per-pose item records and evidence directories |
| 2026-07-12 | WJP2-01 | Verified and released integration lock | coordinator | Deterministic library hash, 57 tests, 32/32 transition matrix, live browser evidence |
| 2026-07-12 | PROGRAM | Play demo changed to moving, library-driven pose reel | coordinator | [Demo Play Verification](../../evidence/pose-library-expansion/DEMO_PLAY_VERIFICATION.md): 11/11 poses, 78 positions, transitions observed, 0 console errors |
| 2026-07-12 | PROGRAM | Expansion completed: 29 distinct candidates verified, WJFA-10 recorded as a duplicate, and the Rust production library reached 39 unique geometries | coordinator | [Rust Integration Report](RUST_INTEGRATION_REPORT.md) |
| 2026-07-13 | WJFL-01..60 | Added feelings archive to the deferred Rust queue; preserved all 60 sources, identified 50 unique hashes and ten exact repeats, and left production runtime unchanged | coordinator | [Feelings Queue](FEELINGS_QUEUE.md) and `evidence/pose-library-expansion/intake/feelings-manifest.json` |
