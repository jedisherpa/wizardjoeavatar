# V3 Canonical Cast Evidence

Status: machine PASS; primary visual review PASS; independent reviews pending at
bundle creation.

This bundle was captured from the real Python ASCILINE projector at
`http://127.0.0.1:8896`, bound to clean commit
`092f78e7ca58dae1a457b2646d04aa8ef776f646` on
`codex/character-director`. The protected services on ports 8765 and 8875 were
not modified.

## Result

- 240 captured and owned frames at 24 fps over exactly 10 seconds
- zero dropped, missing, clipped, or unpaired truth frames
- three complete canonical casts
- canonical `cast_front_XX` pose matched every observed authored frame
- marker order was commit 10, effect 14, recoverable 23, settled 28 in each cast
- zero world-root, presented-root, or staff-grip drift
- zero staff-tip continuity violations at the two-cell-per-authored-frame limit
- effect start and active phases retained a valid staff-tip anchor
- contact verification passed and every silhouette remained inside 240 by 135

The first machine-passing implementation at `2308571` was visually rejected
because the crook crossed Joe's right eye and hat brim during the effect hold.
Commit `092f78e` redirects the same fixed-grip arc outward. The accepted normal
and quarter-speed artifacts show face clearance, a stable hand, a readable tip
effect, and an exact return to neutral.

## Reproduction

```bash
.venv/bin/python tools/run_character_director_visual_review.py \
  --base-url http://127.0.0.1:8896 \
  --output-dir /tmp/v3-canonical-092f78e-run2 \
  --scenarios-file tools/character_director_scenarios/v3-canonical-cast.json \
  --sample-every-frames 2

.venv/bin/python tools/analyze_character_director_v3.py \
  --manifest /tmp/v3-canonical-092f78e-run2/manifest.json \
  --output /tmp/v3-canonical-092f78e-run2/v3-machine-acceptance.json
```

## Artifact Hashes

| Artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `ec3e0c490295b5d6dc5a68dc5327857ac484366ab2167b367d1f0f15819d97cb` |
| `scenario-program.json` | `fb4ca6d69ffbbd829ffaf98dd5bfc2234aca8b7f1df4617b050b871cb95f5108` |
| `animation_truth_trace.ndjson` | `872a30797d4de2d1ff7dbdedad500735783f3928a6e9a3c9345b5342e5c5070c` |
| `contact_verification.json` | `3bd2f97ef4eec8cdc408d9c8090ee46186031a707e8c70b742977f17ed6475c7` |
| `v3-machine-acceptance.json` | `426fadc97d2b37e60e86e383a78158536f51ea43b0bf020b3c47fef77d97e8a9` |
| `visual-review-050ab52e8764-capture.mp4` | `bb4b01970898a315f1177f27789f3122afa5096212c71264758dcf6180efc7a0` |
| `v3-quarter-speed.mp4` | `5f03ad2db38e7e6622f1aa0afbbe96c3bfba557b85cdb122513ccbb9d7f81dcc` |
| `visual-review-050ab52e8764-contact-sheet.png` | `aa564eed80b85c41c0e163e7d61fcb4bc3da849b4401d75c25eb126d5cca4593` |

Machine acceptance does not substitute for visual acting judgment. The normal
and quarter-speed files are retained specifically so that judgment can be
repeated against the same immutable frames.
