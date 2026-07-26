# Kai Renner Technical Build Audit

Date: 2026-07-25
Candidate state: review artifact assembled; product approval pending

## Build

The parity candidate combines Kai's existing 36-pose source artifact with
twelve authored frames, `037`-`048`, to produce a 48-pose artifact on the
1254x1254 canonical canvas. The current reconstruction manifest records no
missing sequence and binds the existing source artifact, authored manifest,
compiled candidate, library index, contact sheet, and review motion contract by
SHA-256.

The authored pipeline starts with flat-chroma PNG sources. Twelve alpha
extraction receipts record border-sampled key colors, tolerance `110`, a
one-pixel edge contraction, source-canvas normalization where required, and
transparent 1254x1254 RGBA intermediates. Twelve canonicalization receipts then
record source, fitted, and destination boxes, translation, scale, filter, and
output hashes. Every authored destination lands on baseline `1185`.

## Canonical Fits

Nine frames use integer translation without resampling. Three oversize frames
use the explicit `--fit-oversize` path and remain below a two-percent reduction:

| Pose | Scale | Reduction | Filter | Destination box |
| --- | ---: | ---: | --- | --- |
| `044` | `0.9858657243816255` | `1.4134%` | LANCZOS | `[420, 69, 834, 1185]` |
| `046` | `0.9858657243816255` | `1.4134%` | LANCZOS | `[372, 69, 883, 1185]` |
| `047` | `0.9806678383128296` | `1.9332%` | LANCZOS | `[416, 69, 837, 1185]` |

The fit implementation crops the silhouette, converts it to premultiplied
alpha, applies deterministic LANCZOS reduction, and finishes with integer
placement. The strict canonicalizer still rejects an oversize silhouette unless
the fit option is explicitly selected.

## Deterministic Current-File Hashes

- Artifact: `2e15a54fda170005919711a0d9177253880cd169cd5d300349845d6b48569873`
- Library index: `768854f8c57528f51768198bc126d75dd61199cd372b6abca41e2aa8a35ab980`
- Authored manifest: `1150cb6d315823b0899e41ad2e7701ca038bca05b8ab648819c47d570551cc6b`
- Authoring brief: `e50fb9aace346b169c736f4728aead77f5bfb5b87fd05051b06d903688db2208`
- Alpha-extraction receipts: `46c6c458f911423bb244df328b1780fd4a54b1b0a506d80d38f4e150f88f1828`
- Canonicalization receipts: `3249ece047e6c14330aae17d162de8de24383be5e18591ab222c07cd78c7ce31`
- Reconstruction manifest: `f300216c7c571cf29bc488bf939e9ca0d4d0bc4483964e56f44671e5413a32b8`
- Review motion contract: `0e4c99b1c398f7666362e26992b9e8be2d2206d66dcab697207eead2796580be`
- Contact sheet: `2ec923cf6b3bc0ea45eee4d6bf065feb0f39fdfa5e35e6bc74f885da0e95bfe2`

These deterministic identifiers are SHA-256 measurements of the current files.
Two consecutive builds reproduced the artifact and library-index hashes
byte-for-byte.

## Review Boundary

The static contact sheet passes the review-projection visual identity gate:
Kai's `BAKE` cap, glasses, beard, mustard sweater, blue trousers, black shoes,
voxel proportions, and warm palette remain recognizable across the twelve
authored frames. All twelve authored IDs were also projected individually
through the alternate HD review server, and the persistent port-8665 observer
displayed the candidate beside approved HD Wizard Joe. Product visual approval
is still pending.

The current library index and motion contract state
`review_projection: true` and `runtime_admitted: false`. The focused JoeVille
provenance, build, prior-candidate, and Kai suites passed 37 tests. The separate
observer/companion integration run passed 25 of 26 tests; the existing
`prepare-score` bearer-order assertion returned `503` instead of `401` and is
outside this character-art change. No product approval or runtime admission is
claimed here.
