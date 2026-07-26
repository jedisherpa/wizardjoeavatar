# Rohan Slate Technical Build Audit

Date: 2026-07-26
Candidate state: 48-pose review artifact assembled; product approval pending

## Authority Boundary

Rohan has two complementary authorities:

1. Supplied JoeVille sheets `g1`-`g6` govern identity and the immutable first
   36 motion poses.
2. `assets/reference/hd_canonical/manifest.json` governs the canonical
   1254x1254 canvas and projection profile.

The HD authority manifest has SHA-256
`740f35730f4aa1e6c6ef96be80115c5b0e117397f792d57fdf5360452bbe78c8`.
The supplied source artifact has SHA-256
`32e480baa58081811621cceac92c9cf7ada6c0d958afe390ab3eaedadce32def`.
Neither authority replaces the other.

## Verified Source State

- Source artifact:
  `32e480baa58081811621cceac92c9cf7ada6c0d958afe390ab3eaedadce32def`
- Source reconstruction:
  `assets/reference/joeville_48_parity/source-metadata/rohan-slate/reconstruction-manifest-v001.json`
- Source reconstruction SHA-256:
  `b768ae323f93774b8ad85cd307b68a6df86bcbd20b56a12c98f11529f7183225`
- Source library-index SHA-256:
  `9be9aa44c9020666ac7580e4e35c3b4eabea3ac2ef52ad035f090ec8082eff54`
- Source contact-sheet SHA-256:
  `0848b4548dcfde3294bfa5207b8b913946bd3a6b8915a6288a3ed4515a6f610e`

The parity build loads supplied poses `001`-`036` as decoded RGBA graphs,
preserves their byte identity and order, and appends only the 12 authored
graphs. The source artifact hash was verified before and after both candidate
builds.

## Authored Deliverable Contract

Every pose from `rohan_slate_motion_037` through
`rohan_slate_motion_048` has:

- a full-size chroma source;
- an extracted-alpha intermediate;
- a canonical RGBA frame;
- a portable alpha-extraction receipt; and
- a portable canonicalization receipt.

The receipt path root is the project root, so no receipt embeds an absolute
workspace path. The aggregate receipt bundles, authored manifest, 48-pose
artifact, library index, parity reconstruction manifest, contact sheet, and
motion contract bind the same candidate.

## Root-Alignment Correction

The original canonicalizer centered the complete silhouette. That rule moves a
character's body root when one arm extends farther than the other. Rohan's
wide practical gestures exposed the defect.

`tools/canonicalize_joeville_authored_alpha.py` now supports an optional
`ground_support_band_height`. When present, horizontal placement is derived
from visible support pixels in the bottom support band rather than the full
silhouette. The default silhouette-centering behavior is unchanged for
existing callers.

All twelve Rohan frames use an 18-pixel support band. Their support centers are
between `626.5` and `627.5` on the 1254-pixel canvas. Every frame ends on
baseline `1185`, retains the 69-pixel safety margin, uses scale `1.0`, and is
translated without resampling.

The receipts record:

- `alignment_mode`;
- source and destination support bounding boxes;
- alignment source and target centers; and
- the support-band height.

Focused tests cover lopsided silhouettes and invalid nonpositive support-band
values.

## Receipt-Chain Gate

The candidate test validates:

`chroma hash -> extraction receipt -> extracted PNG/RGBA hash ->
canonicalization receipt -> final PNG/RGBA hash -> authored manifest`

Every final PNG is RGBA 1254x1254 with straight alpha, transparent corners,
zero hidden RGB under alpha zero, canonical baseline `1185`, and at least the
69-pixel horizontal and top safety margin. All extractions use the recorded
hard-key settings and all canonical destinations remain unscaled.

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
  `005e1776a74acf7f63fccb1a8d93c2451ecc661ce58fac25d7c14f87741e8ce5`
- Library index:
  `442a03c4fa5c82f592dc0f0426fd13df3e2b9e99be252a4c57a3b12ce0e3d424`
- Authored manifest:
  `f4ee0875fe2b2ca59b121b8400a21dfb92ffa04b6df9243d5eced5c3a83fe5bc`
- Authoring brief:
  `74750fe8267360973926dad1c9de043c3a64f09d7f2d8597c0aeb516ad6a8e4c`
- Alpha receipt bundle:
  `bbcdc72afa5ccdd9d359b5802e8a7f65c991c2b89746bf9689c4cd4f33f1b705`
- Canonical receipt bundle:
  `818307146bcf9140fb0e4e39ba1f9ced9e31112de23331d6c230bbfc9c08a081`
- Parity reconstruction:
  `ef45a8a517a7fcd7c74b1fbac0fdeefc06b70aee4d0fce236970a688d956f5c2`
- Review motion contract:
  `b1ffb566a9ce99302f8611be60d1af11bbb000b78efbc6be31833b90cd827af4`
- Contact sheet:
  `7dbf7ea22b6d6b83164af29d17d623b9b9ef26bd41f197f00f1eee0aac78ee47`

The focused canonicalization, parity, provenance, receipt-chain, manifest, and
observer suite passed all 11 tests. Direct projection of poses `037`-`048`
returned the exact pose hashes from the candidate artifact, at 1254x1254, with
`pending_visual_parity` and `runtime_admitted: false` response headers.

The persistent port-8665 observer presents the exact Rohan candidate beside the
approved local HD Wizard Joe baseline. Product visual approval remains pending.
