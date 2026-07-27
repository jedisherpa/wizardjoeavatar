# Liana Jump Scale Normalization

Date: 2026-07-26

## Decision

The Liana review projection showed camera-scale drift inside the jump phrase:

- `liana_motion_014` (pre-jump compression) read too large.
- `liana_motion_017` (apex clearance) read too small.
- `liana_motion_020` (landing absorption) read too large.

The correction is a review-only projector normalization. It does not alter the
authored PNGs, identity authority, approval state, or production registry.

## Normalization Contract

The authoring brief and frozen motion manifest now carry an explicit
`per_pose_uniform_scale_v1` policy:

| Pose | Phase | Uniform scale |
| --- | --- | ---: |
| `liana_motion_014` | jump compression | 94% |
| `liana_motion_017` | apex clearance | 110% |
| `liana_motion_020` | landing absorption | 90% |

All scale values use integer basis points. The compiler applies nearest-neighbor
resampling to the visible RGBA crop, centers the result on the canonical
horizontal axis, locks its bottom to baseline `1185`, clears hidden RGB, and
fails if the result violates canvas margins. No other pose is transformed.

Each transformed pose record preserves both source and compiled RGBA hashes,
source and compiled bounding boxes, and its exact normalization receipt.

## Frozen Candidate

- Authoring brief SHA-256:
  `a4469ff6d3beccd621faa78e26e4eb08182fe8636c3c7a6ef69b3ba7701f510f`
- Motion manifest SHA-256:
  `aa45a59d75f22c68d23ea74169605ad3fa1ad20b2ce367f8724d78008edbacf3`
- Artifact SHA-256:
  `c282f3845cfea4225d265fbff62eb95a9dc7e97db1aaa65068cfba3be7aa0339`
- Library index SHA-256:
  `0473c369ecf1867f4209c98259a1a86af2d093e33123ddfcec339113178d0eaa`
- Build receipt SHA-256:
  `f9d8d053697488c217bd10b7a24174964f508244fc3ebf3a7f97c37f0ae2137a`

## Live Verification

The persistent observer at `http://127.0.0.1:8665/` was restarted with the
corrected library. The live projector returned the frozen artifact hash for all
three poses and these compiled bounds:

| Pose | Compiled bbox | Compiled RGBA SHA-256 |
| --- | --- | --- |
| `liana_motion_014` | `[362, 288, 891, 1185]` | `21420f8ea84400623c365e9612ab3513b4be430372fd7ee39cefc57ea92d3605` |
| `liana_motion_017` | `[324, 255, 929, 1185]` | `d0623d3dfb53aac2ac1ed935ecb3543cf3544d3b30656e8d4ede56b54e5622a3` |
| `liana_motion_020` | `[376, 383, 878, 1185]` | `6a03dfa780a8109c9dc9acee0868605773ff233adcb6679a4ec2548be22b74ae` |

The evidence contact sheet is stored at
`evidence/character-director/liana-jump-scale-normalization-2026-07-26/live-corrected-jump-poses.jpg`.

## Verification

The focused Liana identity, motion, supplemental builder, deterministic rebuild,
path portability, and fail-closed tests pass. The candidate remains
`review_projection: true`, `runtime_admitted: false`, and
`approval_state: pending_visual_parity`.
