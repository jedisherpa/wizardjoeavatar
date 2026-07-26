# Thorne Vale Technical Build Audit

Date: 2026-07-25
Candidate state: technically passed, product review pending

## Build

The candidate merges Thorne's immutable 36 supplied pixel graphs with twelve
new full-size RGBA authoring sources. Chroma extraction produces hard-edged
transparent PNG intermediates, and canonicalization uses integer translation
only. No canonical authored frame is resampled.

The projector reads the compiled `.wjpose` artifact. Source PNGs are provenance
inputs, not runtime render assets.

## Visual Gate Corrections

The first open-charter frame was rejected because it duplicated the parchment
in the left-hip carrier. It was regenerated with a visibly empty carrier.

The first canonicalization attempt also rejected poses `047` and `048` because
their silhouettes exceeded the 69-pixel safety margin. Those poses were
recomposed at the neighboring sequence scale, extracted again, and accepted
without relaxing the canonical profile.

A dark-background alpha review found a thin magenta key fringe. All twelve
frames were extracted again with a hard border-sampled key and a stricter
tolerance. The final canonical frames contain no partially transparent pixels.

## Determinism

Two consecutive corrected builds produced:

- Artifact: `787f6745558e2d33683c42ea84a7b81b5883ea8192862d921b917de1b26a67cc`
- Library index: `937abf76db2da70cb85d36237b9124a2e5dd59b3bfc19f240563e20a71abcde2`

The candidate contains 48 unique pose IDs on the 1254x1254 canonical canvas.
All twelve authored silhouettes land on baseline 1185 and remain inside the
minimum safety margin.

## Verification

The focused suite covers:

- authored parity topology and supplied-frame immutability;
- Thorne, Selene, Aurelia, and Orion candidate hashes;
- canonical alpha placement;
- HD pose artifact loading;
- source reconstruction and parity tracking;
- observer fail-closed review projection.

Full-size browser evidence covers all twelve authored poses and the 8665
side-by-side observer. Runtime admission remains denied.

## Residual Risk

Image generation introduces small scale and style variation between authored
and supplied frames. Full-size review found the sequence coherent, but only
explicit product approval can close that visual judgment gate.
