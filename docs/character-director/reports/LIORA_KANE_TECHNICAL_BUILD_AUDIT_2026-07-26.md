# Liora Kane Technical Build Audit

Date: 2026-07-26
Candidate state: 48-pose review artifact assembled; product approval pending

## Authority Boundary

Liora has two complementary authorities:

1. Supplied JoeVille sheets `g1`-`g6` govern identity and the immutable first
   36 motion poses.
2. `assets/reference/hd_canonical/manifest.json` governs the canonical
   1254x1254 canvas and projection profile.

The HD authority manifest has SHA-256
`740f35730f4aa1e6c6ef96be80115c5b0e117397f792d57fdf5360452bbe78c8`.
The supplied source artifact has SHA-256
`7b98b6ce927ab24457920b7e3d15a0b87e3e3d456a3af11ab339ada160ca03a7`.
Neither authority replaces the other.

## Verified Source State

- Source artifact:
  `7b98b6ce927ab24457920b7e3d15a0b87e3e3d456a3af11ab339ada160ca03a7`
- Source reconstruction:
  `assets/reference/joeville_48_parity/source-metadata/liora-kane/reconstruction-manifest-v001.json`
- Source contact sheet:
  `3acbf2808439e16ce99ceb5249ea535cbe080dae4232b231904a9f36474124d8`

The source artifact contains the supplied poses `001`-`036`. The parity build
loads those decoded RGBA graphs directly, preserves their byte identity and
order, and appends only the 12 authored graphs. The source library remains a
review projection and is runtime-denied.

## Authored Deliverable Contract

Every pose from `liora_kane_motion_037` through
`liora_kane_motion_048` has:

- a full-size chroma source;
- an extracted-alpha intermediate;
- a canonical RGBA frame;
- a portable alpha-extraction receipt; and
- a portable canonicalization receipt.

The receipt path root is the project root, so no receipt embeds an absolute
workspace path. The aggregate receipt bundles, authored manifest, 48-pose
artifact, library index, parity reconstruction manifest, contact sheet, and
motion contract bind the same candidate.

## Receipt-Chain Gate

The candidate test validates:

`chroma hash -> extraction receipt -> extracted PNG/RGBA hash ->
canonicalization receipt -> final PNG/RGBA hash -> authored manifest`

Every final PNG is RGBA 1254x1254 with straight alpha, transparent corners,
zero hidden RGB under alpha zero, canonical baseline `1185`, and at least the
69-pixel horizontal and top safety margin. All extractions use tolerance `110`
and edge contraction `1`.

Poses `042`, `043`, and `045` required integer translation only. The other
authored silhouettes used the explicit receipted LANCZOS oversize-fit path.
The scale range is `0.9712793733681462` through `1.0`; no authored frame falls
below the `0.95` hard review threshold.

## Determinism And Admission Gate

All 48 RGBA hashes are unique. Two consecutive builds reproduced the artifact
and library-index hashes exactly while the supplied source artifact remained
unchanged.

The candidate retains `review_projection: true` and
`runtime_admitted: false` at library, shard, sequence, provenance, and motion
contract boundaries. Product approval must bind the exact artifact/index pair
before runtime admission can be considered.

## Deterministic Candidate

- Artifact:
  `811b8c9f954dbd72f901f464ce7e9fba53cbf6183a4ab4f33afb7aec45f62cb4`
- Library index:
  `b4f3bf1416e9c1f49f732b5731b227bb5e71d75191d5774f85262c2f2167597d`
- Authored manifest:
  `032f89e379e8db2812882482da7c854c5ed9e50839b389a731be7cf49f95e73a`
- Alpha receipt bundle:
  `f8894a0e6b6ba378b42688e9bd575cc8c8c850e933191a8c307b7325472cc77b`
- Canonical receipt bundle:
  `f2f4fe3e644ff8747576e62f0b2e61e28fedd68db69f99bc04633cb09c49a7e6`
- Parity reconstruction:
  `9bab86d931edc37e3a6a63616b15897309ca777313dbf875f7e492b7b58c4df3`
- Review motion contract:
  `e3a270f2e78e18ac029417a53feb4d86de9832b33e598fe9a72ab46b79000d2b`
- Contact sheet:
  `f0af7a18e1e72291f82ef04033e7017ca0fec9fb6e965e02f945fb40ab7d2c54`

The focused parity, provenance, receipt-chain, manifest, and observer suite
passed all 12 tests. Direct projection of poses `037`-`048` returned the exact
candidate artifact in ready state with no render errors, and the persistent
port-8665 observer reports `character_id: liora-kane`,
`review_projection: true`, and `runtime_admitted: false`.

A broader 37-test companion-server sweep exposed one unrelated authentication
ordering failure on `/api/avatar/wizard/performance-context/prepare-score`:
service readiness returned `503` before the expected unauthenticated `401`.
That route does not load, project, or admit this candidate and is tracked
separately rather than being hidden inside the Liora result.

Product visual approval remains pending.
