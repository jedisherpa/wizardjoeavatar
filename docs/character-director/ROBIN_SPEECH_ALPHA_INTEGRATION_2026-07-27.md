# Robin and Speech Alpha Integration

Date: 2026-07-27

## Current Candidate

The corrected shared-canvas source contains 200 continuous approved frames:

- `ACT001`-`ACT100`;
- `FLY001`-`FLY050`;
- `INT001`-`INT050`.

Robin is always the orange-and-green bird on the left. Speech is always the
blue-and-yellow bird on the right. The source is preserved on its original
1920 x 1080 transparent canvas.

Source manifest:

`assets/reference/characters/robin_speech/source/source-manifest-v003.json`

Source manifest SHA-256:

`2c33d3e078b6cb731c1269e5db35dcc0af419b232e59d4882e912a6ec4d124f9`

## Source Authority

| Role | File | SHA-256 | Frames |
| --- | --- | --- | ---: |
| Base | `Robin_Alpha_PNGs_RobinOnly_001-160_2026-07-19.zip` | `138750624356c7ddc8e56cd277da1e213df74eff0a72938e0c3c59a4a9dc5cfd` | 160 |
| Tail | `Robin_Pair_Batches031-040_Alphas.zip` | `95a951a765ee3098342a0a5d385b7386716919c44241fc0c1d76f8223a7ff720` | 50 |

Frames 151-160 overlap and are byte-identical, yielding 200 unique frames.
The similarly named 155-frame archive is not used because frames 11-30 contain
Dragon imagery mislabeled as Robin.

## Identity Partition

The importer does not cut each frame at one fixed x-coordinate. It:

1. locates significant Robin-green and Speech-blue chromatic seeds;
2. keeps detached alpha components whole when one identity owns them;
3. assigns unseeded detached components by spatial evidence;
4. partitions genuinely touching components with multi-source geodesic
   propagation;
5. reconstructs the source from the two masks and requires zero overlap.

This preserves feet, wings, props, and contact gestures that cross the canvas
midline. Focused hard-frame checks cover 24, 25, 65, 109, 155, 176, 192, and
195.

## Output State

The deterministic review-only artifacts contain:

- 200 Robin poses in eight shards;
- 200 Speech poses in eight shards;
- full 1920 x 1080 coordinate authority;
- no PNG/SVG runtime render assets;
- exact source reconstruction and zero identity overlap;
- `runtime_admitted: false`.

The corrected Robin review sequence is published to the local observer at
[http://127.0.0.1:8665/](http://127.0.0.1:8665/). Product review and package
admission remain separate gates.

Because Robin remains authored on the left half of the shared source canvas,
the observer requests a fixed `+480`-pixel horizontal presentation translation.
This centers the isolated character without changing source bytes, rescaling,
per-pose cropping, vertical registration, or internal motion. The same projector
contract supports a corresponding fixed translation for a declared right-side
identity.
