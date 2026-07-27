# Finn Calder Technical Build Audit

Date: 2026-07-26
Candidate state: 48-pose review artifact assembled; product approval pending

## Authority Boundary

Finn has two complementary authorities:

1. Supplied JoeVille sheets `g1`-`g6` govern identity and the immutable first
   36 motion poses.
2. `assets/reference/hd_canonical/manifest.json` governs the canonical
   1254x1254 canvas and projection profile.

The HD authority manifest has SHA-256
`740f35730f4aa1e6c6ef96be80115c5b0e117397f792d57fdf5360452bbe78c8`.
The supplied source artifact has SHA-256
`6172d80b6003c57317a4139fef8180a631752e91ff4d21e0f958cde0165a86f1`.
Neither authority replaces the other.

## Verified Source State

- Source artifact:
  `6172d80b6003c57317a4139fef8180a631752e91ff4d21e0f958cde0165a86f1`
- Source reconstruction:
  `assets/reference/joeville_48_parity/source-metadata/finn-calder/reconstruction-manifest-v001.json`
- Source reconstruction SHA-256:
  `b399a12b8b65dd5999ad0769f9250c139aef48b22f6734f3034112b530ebf30e`
- Source library-index SHA-256:
  `ed99bff17eed17027f8b1eda8fe662f4f0ce1e2f1ed2e6577835f9fd05bd4249`
- Source contact-sheet SHA-256:
  `423e174b9ff64b3d5b5a9b6b96013b1faca4c51b32b314dedb53ef8e4533c3cc`

The parity build loads supplied poses `001`-`036` as decoded RGBA graphs,
preserves their byte identity and order, and appends only the 12 authored
graphs. The source artifact hash was verified before and after both candidate
builds.

## Independent Direction Pass

Before authoring, an identity/provenance specialist and an animation-direction
specialist independently inspected the supplied artifact, contact sheet,
existing parity contracts, and runtime boundary. Their reports are:

- `FINN_CALDER_SOURCE_IDENTITY_AUDIT_2026-07-26.md`
  (`55071afc7b1b6f19dc89a9bfa5b8f67e8f11042a8e5ac8bb9dd1ce35878e07f3`)
- `FINN_CALDER_ANIMATION_DIRECTION_2026-07-26.md`
  (`8a8832b0c004589dc3a298b7b385d4d130fb6108949f83df4337a2d309a368c0`)

The source audit found 36 unique supplied RGBA graphs and no existing Finn
production admission. The direction report defined two grounded, prop-free
performances that preserve Finn's deliberately unfamiliar eye anatomy and
restrained physical vocabulary.

## Authored Deliverable Contract

Every pose from `finn_calder_motion_037` through
`finn_calder_motion_048` has:

- a full-size chroma source;
- an extracted-alpha intermediate;
- a canonical RGBA frame;
- a portable alpha-extraction receipt; and
- a portable canonicalization receipt.

The receipt path root is the project root, so no receipt embeds an absolute
workspace path. The aggregate receipt bundles, authored manifest, 48-pose
artifact, library index, parity reconstruction manifest, contact sheet, and
motion contract bind the same candidate.

## Canonical Placement

All twelve Finn frames use an 18-pixel ground-support band. Their support
centers remain within one half pixel of canvas center. Every frame ends on
baseline `1185`, keeps the canonical safety margins, uses scale `1.0`, and is
translated without resampling.

The fixed-root direction avoids synthetic locomotion, root drift, and
unsupported airborne states. Both feet remain grounded throughout G7 and G8.

## Receipt-Chain Gate

The candidate test validates:

`chroma hash -> extraction receipt -> extracted PNG/RGBA hash ->
canonicalization receipt -> final PNG/RGBA hash -> authored manifest`

Every final PNG is RGBA 1254x1254 with straight alpha, transparent corners,
zero hidden RGB under alpha zero, canonical baseline `1185`, and the required
top and horizontal safety margins. All extractions use the recorded hard-key
settings and all canonical destinations remain unscaled.

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
  `240c931919db952dc6ed7179d3b5b2836adffea37a1ee5e47daec2e62b3e4a88`
- Library index:
  `7975ac7d5b879893cc3d44940cee8962b641ad7475d1f5bd286d3277bd7b54d0`
- Authored manifest:
  `60deaf0ea6348832d7cc97f531b3af00291e817f15298eea3b7593bd3048e947`
- Authoring brief:
  `8912476f468093852ff1df470b0e7346932efa9aadf3ac92b4998c003e06bea2`
- Alpha receipt bundle:
  `b7569bf6a3f3c33ae4e6aec770fc4470a559f854dce2e7f805ddd2120731e73d`
- Canonical receipt bundle:
  `a668d3b640652a1c11a52e7618b9b376b13c0e02ade909aa8522cd40bfcde020`
- Parity reconstruction:
  `38cdf2af9977fb1cadd3fea383711593d3b47af41706a7f88fee28a340a7354d`
- Review motion contract:
  `0ba976285ffef9db71b0a099cbea957aaa10091ccc9323e7579ca781538cfc58`
- Contact sheet:
  `21ff968f6f148515dd336542002ee77c1350a7e4cd98b86bc94cca6335221a40`

The focused canonicalization, parity, provenance, receipt-chain, manifest, and
observer suite passed all 11 tests. Direct projection of poses `037`-`048`
returned the exact pose hashes from the candidate artifact, at 1254x1254, with
`pending_visual_parity` and `runtime_admitted: false` response headers.

The persistent port-8665 observer presents the exact Finn candidate beside the
approved local HD Wizard Joe baseline. Product visual approval remains pending.
