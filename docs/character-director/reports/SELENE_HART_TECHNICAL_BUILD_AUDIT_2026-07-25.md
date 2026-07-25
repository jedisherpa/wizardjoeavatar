# Selene Hart Technical Build Audit

Date: 2026-07-25
Candidate state: technically passed, product review pending

## Build

The candidate merges Selene's immutable 36 supplied pixel graphs with twelve
new full-size RGBA authoring sources. Chroma extraction produces transparent
PNG intermediates, and canonicalization uses integer translation only. No
authored frame is resampled during canonical placement.

The projector reads the compiled `.wjpose` artifact. Source PNGs are provenance
inputs, not runtime render assets.

## Visual Gate Correction

Individual full-size projection found partial-alpha damage in motions `042`,
`043`, `044`, `045`, and `048` that was not obvious on the contact sheet. Those
intermediates were rejected. The affected frames were extracted again with a
hard border-sampled key, canonicalized again, and rebuilt before acceptance.

The corrected images preserve fully opaque character colors and transparent
backgrounds without changing the authored chroma sources.

## Determinism

Two consecutive corrected builds produced:

- Artifact: `1e9b791070658d79d1a517557c819d900d5c656429f3b643bb268e2fe4374781`
- Library index: `86f5ff6587bf1714991e8a0ac66d40007bc25b5c5a0ecef0a960e5f7a12439b4`

The candidate contains 48 unique pose IDs on the 1254x1254 canonical canvas.
All twelve authored silhouettes land on baseline 1185 and remain inside the
minimum safety margin.

## Verification

The focused suite covers:

- authored parity topology and supplied-frame immutability;
- Selene, Aurelia, and Orion candidate hashes;
- canonical alpha placement;
- HD pose artifact loading;
- source reconstruction and parity tracking;
- observer fail-closed review projection.

Full-size browser evidence covers all twelve authored poses and the 8665
side-by-side observer. Runtime admission remains denied.

## Residual Risk

Image generation may introduce small stylistic variation between authored and
supplied frames. Full-size review found the candidate coherent, but only
explicit product approval can close that visual judgment gate.
