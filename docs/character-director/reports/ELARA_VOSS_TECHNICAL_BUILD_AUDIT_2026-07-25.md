# Elara Voss Technical Build Audit

Date: 2026-07-25
Candidate state: technically passed, product review pending

## Build

The candidate merges Elara's immutable 36 supplied pixel graphs with twelve
new full-size RGBA authoring sources. Chroma extraction produces transparent
PNG intermediates, canonicalization lands every silhouette on baseline 1185,
and the projector reads the compiled `.wjpose` artifact. Source PNGs remain
provenance inputs rather than runtime render assets.

Frames `037`-`041` use integer translation only. Frames `042`-`048` exceeded
the canonical safety box and use a 3.1-3.9 percent reduction through the explicit
`--fit-oversize` path: premultiplied-alpha LANCZOS reduction followed by
integer placement. Every scale, source box, fitted box, destination box, and
filter is recorded in `canonicalization-receipts-v001.json`. The
canonicalizer's default remains strict and rejects oversize art unless this
option is deliberately selected.

## Visual Gate Corrections

The first fitted frames exposed a thin magenta key fringe against a dark
background. Frames `042`-`048` were extracted again with a border-sampled hard
key and a one-pixel edge contraction before the deterministic fit. A more
aggressive tolerance was rejected because it removed cream blouse detail.

The corrected frames preserve the blouse, clean premultiplied alpha edge,
microphone ownership, planted heels, and complete silhouettes. Full-size
browser projection found no crop damage or remaining chroma fringe.

## Determinism

Two consecutive corrected builds produced:

- Artifact: `8fd74202c038028af63e6fff9a9e8b8c2d82261bc3e30b5d2447a93af632f53c`
- Library index: `7fd020cb347ec6726e1dd60939166d9659775fe626ce8511108f38441708bde2`

The candidate contains 48 unique pose IDs on the 1254x1254 canonical canvas.
All twelve authored silhouettes land on baseline 1185 and remain inside the
69-pixel minimum safety margin.

## Verification

The focused suite covers:

- authored parity topology and supplied-frame immutability;
- Elara and the earlier accepted technical candidates;
- strict and opt-in canonical alpha placement;
- HD pose artifact loading;
- source reconstruction and parity tracking;
- observer fail-closed review projection.

Full-size browser evidence covers all twelve authored poses and the persistent
8665 side-by-side observer. Runtime admission remains denied.

## Residual Risk

Image generation introduces small scale and style variation between authored
and supplied frames. Seven frames required a small, documented resample to
meet the shared safety profile. Full-size review found the sequences coherent,
but only explicit product approval can close that visual judgment gate.
