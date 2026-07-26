# Draven Holt Technical Build Audit

Date: 2026-07-25
Candidate state: 48-pose review artifact assembled; product approval pending

## Authority Boundary

Draven has two complementary authorities:

1. `Sprites 1.zip`, member `char-draven-holt.png` and sheets `g1`-`g6`,
   governs visual identity and supplied motion.
2. `assets/reference/hd_canonical/manifest.json` governs the canonical
   1254x1254 canvas and projection profile.

The source identity member has SHA-256
`e6944d0df2c142724661d84b1ba120db07fd7d7e0ea49b438880cb46eff7c343`.
The HD authority manifest has SHA-256
`740f35730f4aa1e6c6ef96be80115c5b0e117397f792d57fdf5360452bbe78c8`.
Neither authority replaces the other.

The final authored artifact binds the HD authority manifest directly in its
provenance. The older 36-pose source artifact does not contain that direct
binding, so its census, tracker, reconstruction, and identity-source hashes
remain part of the source authority chain.

## Verified Source State

- Source artifact:
  `244627668d46ad2c552d2ec2d7f5d24ce4ef4750c3a423d097bee1929c01e724`
- Library index:
  `d4019b89144a8b81de688f2a0653e748bf1f08bb931dc613fae4e65bad3510e2`
- Reconstruction manifest:
  `55fd78882e1b8226a543e285591932cd73b354a71ea9550e5c7cfb4fdba6ad5f`
- Source contact sheet:
  `8760454c6cce10388185fcb36c6b737f2f59b30bb0965f57ae2e2396a0feaaf2`

All 36 decoded RGBA hashes and bounding boxes match the source reconstruction
manifest. Artifact, index, and manifest pose ordering agree. Transparent
corners are clean. The source library is a review projection and remains
runtime-denied.

## Authored Deliverable Contract

Every pose from `draven_holt_motion_037` through
`draven_holt_motion_048` requires:

- a full-size chroma source;
- an extracted-alpha intermediate;
- a canonical RGBA frame;
- an alpha-extraction receipt; and
- a canonicalization receipt.

The aggregate receipt files, authored manifest, 48-pose artifact, library
index, parity reconstruction manifest, contact sheet, motion contract,
full-size pose captures, side-by-side capture, and visual-review decision are
also required.

## Receipt-Chain Gate

Draven's candidate test must validate the full chain rather than merely the
final frame:

`chroma hash -> extraction receipt -> extracted file/RGBA hash ->
canonicalization receipt -> final file/RGBA hash -> authored manifest`

Every canonical receipt must bind the HD authority hash. Final PNGs must be
RGBA 1254x1254, use straight alpha, have transparent corners, and contain zero
RGB under zero alpha. Grounded silhouettes must end on baseline `1185` and
respect the 69-pixel canonical margin.

Translation is preferred. An oversize silhouette may use only the explicit,
receipted premultiplied-LANCZOS fit path. Scale `0.98` is the soft authoring
target; smaller fits require full-size projector review and must remain above
`0.95`. Extraction tolerance and edge contraction are accepted only after
full-size inspection confirms that the thin pencil, clipboard marks, glasses,
and beard tips remain intact.

## Determinism And Admission Gate

Poses `001`-`036` must remain byte-for-byte RGBA-identical to the source
artifact. All 48 pose hashes must be unique. Two consecutive builds must
reproduce the artifact, index, reconstruction, contact sheet, and motion
contract byte-for-byte.

The candidate must retain `review_projection: true` and
`runtime_admitted: false` at every library, shard, sequence, provenance, and
contract boundary. Product approval must bind the exact artifact/index pair
before runtime admission can be considered.

The JSON parity tracker is a planning snapshot and is not treated as current
compiled-state authority.

## Deterministic Candidate

- Artifact:
  `ac51bba7f40bd42b374857b3070d62716f878894b99190d76cd434f08a843e82`
- Library index:
  `6fc822bf34011fa0d3e110a1c261851c04ceadab35184e9e95db378b11ce0069`
- Authored manifest:
  `9fed5b1dc78ffab132885742589ba5021a8602a33c5ca804ede562870897271c`
- Alpha receipt bundle:
  `23cb83653f8a9de2bc4c71f96c6d303d732c481c868e883a136022c29789de26`
- Canonical receipt bundle:
  `b6ed2386bb2a372581b5ca680e23e1529a71dbf57db2443b35a918b39bf45273`
- Parity reconstruction:
  `0aecf781a48b5bc4862cc6ce50a29fb2a91406a7ebe2f6941e9bfe604f08eebe`
- Review motion contract:
  `10a9678fdcc13a902f7ad32c000e1ac3bfd8d5904c14b3e15903510c746b98b4`
- Contact sheet:
  `b40ffd132a58e8e69bf5d7a93e1fdbce6a72d482c88966282399e6396451d797`

Two consecutive builds reproduced the artifact and library-index hashes.
Every authored destination ends on baseline `1185`; the receipted scale range
is `0.9604130808950087` through `0.998211091234347`. The focused parity,
provenance, complete receipt-chain, and observer suite passed 32 tests.
