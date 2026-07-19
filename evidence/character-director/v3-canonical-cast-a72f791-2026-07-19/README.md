# V3 Canonical Cast Evidence

Status: machine PASS; primary normal-speed, quarter-speed, and browser-layout
review PASS; independent animation and technical reviews pending at bundle
publication.

This bundle was captured from the real Python ASCILINE projector at
`http://127.0.0.1:8896`, bound to clean candidate
`a72f7915479787ba8cd65da2f5075ec99400c16c`. The protected services on ports
8765 and 8875 were not modified.

## Result

- 242 contiguous transport frames, including exactly 240 scenario-owned frames
- two bounded unowned frames between scenario windows; no pre/post-window spill
- zero dropped frames, decoded gaps, decoder errors, or queue overruns
- 32 deterministic atomic cast graphs; frames 0 and 31 equal `front_idle`
- full authored-frame coverage from 0 through 30 across three real casts
- exact marker events at commit 10, effect 14, recoverable 23, and settled 28
- every hold after a cast renders authoritative `front_idle`
- zero world-root, presented-root, staff-grip, continuity, effect, or clipping failures
- browser replay: zero page/console errors, decode errors, drops, resyncs, or skipped slots
- normal/quarter-speed frame-sequence SSIM: `0.999916`

The earlier `092f78e` candidate is preserved separately. Its outward staff arc
passed primary visual review, but independent technical review rejected the
published evidence and exposed a renderer feedback bug: idle holds retained
`cast_front_29` or `cast_front_30`. Candidate `a72f791` makes authoritative
state the only pose authority, proves the return to neutral in a regression
test, strengthens the V3 analyzer, and publishes every declared sample and wire
artifact.

## Replay

Run validation from a clean checkout of candidate `a72f791` so the strict
runtime-binding check can resolve the recorded repository identity:

```bash
.venv/bin/python tools/analyze_character_director_v3.py \
  --manifest evidence/character-director/v3-canonical-cast-a72f791-2026-07-19/manifest.json \
  --output /tmp/v3-a72f791-replay.json

cmp /tmp/v3-a72f791-replay.json \
  evidence/character-director/v3-canonical-cast-a72f791-2026-07-19/v3-machine-acceptance.json
```

Validate the bound review products with
`validate_review_bundle_manifest()` from
`tools/run_character_director_visual_review.py`. The bundle manifest binds the
capture manifest, machine report, quarter-speed derivative, browser replay,
and browser metrics. The capture manifest separately binds all 170 samples,
wire stream and index, truth trace, contact report, normal-speed video, contact
sheet, and scenario program.

## Artifact Hashes

| Artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `438d0e3525a679a5da78324bfa0ade7dbeb182cbcb0c4afd408ca2b6fe994004` |
| `review-bundle-manifest.json` | `2ff8ebe60f4865d2c44e7ebb1f930d646e6637e7234950ef3f405531a719267e` |
| `scenario-program.json` | `fb4ca6d69ffbbd829ffaf98dd5bfc2234aca8b7f1df4617b050b871cb95f5108` |
| `animation_truth_trace.ndjson` | `1249c8ade3702954c3f4f0650c5625f5a890d4fda6aa644599f8df5fb2887ec8` |
| `contact_verification.json` | `f8461163cf18da05f7cc0d1399d92dc3fe8d3d2a5bd5949dba7e274a5239e96d` |
| `v3-machine-acceptance.json` | `ea9c11748fb90fef93cb35b2edd710a70758c56fcc943a7c55eba6ee01605a2b` |
| `visual-review-b66a400b5e64-capture.mp4` | `b7d28babdc9dd62dd8b427e6f8bb61d49c330f74a71ee81d767ede5a72d89d7a` |
| `v3-quarter-speed.mp4` | `b120b9de83e759123dc25a9e483a54ba35a08c29220d04a37e4ec36b408bbf11` |
| `v3-browser-layout.mp4` | `9656b2b8fcbe1d647b61d953818d4de856b38b909445745788642f9363b89843` |
| `v3-browser-layout-metrics.json` | `259d29cc118020db11349de086e29a0da57df356bc57b709064b988fe7a96b14` |
| `visual-review-b66a400b5e64-contact-sheet.png` | `bd72460495e01b98475faf3383db00f2dff93dfa4fbb06ba177e945e85ea6126` |

Machine acceptance does not substitute for visual acting judgment. The normal,
quarter-speed, browser-layout, and contact-sheet artifacts are retained so that
judgment can be repeated against the same immutable frames.
