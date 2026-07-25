# Aurelia Finch Technical Build Audit

Date: 2026-07-25
Candidate state: technically passed, product review pending

## Build

The candidate merges Aurelia's immutable 42 supplied pixel graphs with six
new full-size RGBA authoring sources. Chroma extraction produces transparent
PNG intermediates, and canonicalization uses integer translation only. No
authored frame is resampled during canonical placement.

The projector reads the compiled `.wjpose` artifact. Source PNGs are provenance
inputs, not runtime render assets.

## Determinism

Two consecutive builds produced:

- Artifact: `e7e44013b9356720357e9dc0114909ddaadee34a3e26d2de666751b7e7d136ad`
- Library index: `b4d19c01b0771a1ed49a52c42051a4a82c9e347efc6152d9023b2656f596e9b1`

The candidate contains 48 unique pose IDs on the 1254x1254 canonical canvas.
All six authored silhouettes land on baseline 1185 and remain inside the
minimum safety margin.

## Verification

The focused suite passed 25 tests covering:

- authored parity topology and immutability;
- Aurelia and Orion candidate hashes;
- canonical alpha placement;
- HD pose artifact loading;
- source reconstruction and parity tracking;
- observer fail-closed review projection.

Full-size browser evidence covers all six authored poses and the 8665
side-by-side observer. Runtime admission remains denied.

## Residual Risk

Image generation may introduce small stylistic variation between authored and
supplied frames. The full-size review found the candidate coherent, but only
explicit product approval can close that visual judgment gate.
