# V3 Canonical Cast Evidence

Status: **ACCEPTED V3**. Machine analysis, primary normal-speed,
quarter-speed, contact-sheet, and browser-layout inspection, independent
animation review, and independent technical review all PASS.

This bundle was captured from the real Python ASCILINE projector at
`http://127.0.0.1:8896`, bound to clean candidate
`dba348be4ff0af21f868491cbd8de877c13d3ee2`. Protected services on ports 8765
and 8875 were not modified.

## Result

- 314 contiguous transport frames: exactly 312 scenario-owned frames and two
  bounded transition frames
- zero dropped frames, decoded gaps, decoder errors, or queue overruns
- 32 deterministic cast graphs with exact neutral endpoints
- complete recovery coverage, authored frames 23 through 30, in every cast
- exact marker order at commit 10, effect 14, recoverable 23, and settled 28
- complete source staff graph retained through the rigid arc; no synthetic prop
  replacement
- maximum adjacent staff-tip travel: two cells
- maximum full-raster nearest distance: three cells, the measured square-grid
  quantization bound for the asymmetric hook
- zero world-root, stage-root, staff-grip, contact, effect, or clipping failures
- browser replay: zero page or console errors, decode errors, drops, resyncs,
  skipped presentation slots, or ignored delta frames
- normal video: 312 frames at 24 FPS over 13 seconds
- quarter-speed video: 1,248 frames at 24 FPS over 52 seconds

The strengthened V3 analyzer passes all twelve checks. Independent reviewers
then evaluated this exact corrected bundle without substituting machine results
for animation judgment:

- `docs/character-director/reviews/V3_CANONICAL_CAST_DBA348B_ANIMATION_REVIEW.md`
  concludes `Verdict: PASS V3`.
- `docs/character-director/reviews/V3_CANONICAL_CAST_DBA348B_TECHNICAL_REVIEW.md`
  concludes `Verdict: PASS V3` after deterministic replay, hash validation,
  and adversarial fail-closed checks.

## Replay

Run validation from a clean checkout of candidate `dba348b` so the strict
runtime-binding check can resolve the recorded repository identity:

```bash
python3 tools/analyze_character_director_v3.py \
  --manifest evidence/character-director/v3-canonical-cast-dba348b-2026-07-19/manifest.json \
  --output /tmp/v3-dba348b-replay.json

cmp /tmp/v3-dba348b-replay.json \
  evidence/character-director/v3-canonical-cast-dba348b-2026-07-19/v3-machine-acceptance.json
```

Validate `review-bundle-manifest.json` with
`validate_review_bundle_manifest()` from
`tools/run_character_director_visual_review.py`. The review manifest binds the
machine report, quarter-speed derivative, browser replay, browser metrics, and
capture manifest. The capture manifest separately binds every retained sample,
the wire stream and index, truth trace, contact report, normal-speed video,
contact sheet, and scenario program.

## Artifact Hashes

| Artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `84a8e1bc50e684122e6275ce740d95b49985e8d54c8bdba2af4a2e686ec1e3a3` |
| `review-bundle-manifest.json` | `156491501d5b28c81e494d523eb368dd63ceb4bc2498aa3ae521615efddc594b` |
| `scenario-program.json` | `3655beceec5c696f881d607d8eeaf8e2613397b3a4249c49106a3d7ffbb983aa` |
| `animation_truth_trace.ndjson` | `2e06079628278687660eda8a3ddd4617f509ac7e3e35c91ac737629e95de9aec` |
| `contact_verification.json` | `166d6ae60c50a8e49fdeee2a9013774c258ff62bef95e44713b21c58c4539efe` |
| `v3-machine-acceptance.json` | `f922b90be54aee06bf36463a27c20866b09c61fe943b198b9d7fb88e769ddc8f` |
| `visual-review-0365dd9b28ac-capture.mp4` | `8171627169bd3c8e93b197f93b0b0d560ac47834df5ed190a0f896e809e5c9cf` |
| `v3-quarter-speed.mp4` | `62dc998b1eaf518a488d27fa241badc033f650cb2fa698b9310c0e4acaabaa3e` |
| `v3-browser-layout.mp4` | `fd08bb5e4cb8c2e07b95d14ecc9498b57839045ceec21c18380890535eca1fd9` |
| `v3-browser-layout-metrics.json` | `ee76a03771e2fd675d585ce90ee7e1ccd0ec0049756605b3c23b154c6220c58f` |
| `visual-review-0365dd9b28ac-contact-sheet.png` | `7363b18141a38cc70b3d1c6af0472589d42f03fea9ff2a5cfbaf1ae6af8d976a` |

The rejected `a72f791` bundle remains alongside this one as historical evidence
of the staff-construction and skipped-recovery defects that this candidate was
required to close.
