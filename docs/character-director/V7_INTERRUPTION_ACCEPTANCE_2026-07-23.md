# V7 Cast Interruption Acceptance

Date: 2026-07-23

Accepted implementation commit:
`8217ccc2`

Evidence:
`evidence/character-director/v7-cast-interruption-8217ccc2-2026-07-23/`

## Verdict

V7 passes its machine gate and normal-speed, quarter-speed, and frame-by-frame
review. A new speech turn before cast commitment cancels the cast without a
stale effect. A new speech turn after commitment preserves the authored
stroke, effect, recovery, and settle before the replacement speech becomes
visible.

## Measured Result

- 10 of 10 V7 machine checks passed.
- 173 transport frames were contiguous with zero drops.
- 167 scenario-owned frames were paired to atomic animation truth.
- Pre-commit interruption was dispatched from accepted `cast_front@8`.
- Post-commit interruption was dispatched from accepted
  `action_commit@10`.
- Marker order and authored frames were exactly commit 10, effect 14,
  recoverable 23, and settled 28.
- Every authored recovery drawing 23 through 30 was visibly presented.
- The replacement speech was `v7-postcommit-new-turn`.
- Recovery-to-speech latency was within 12 presentation frames.
- Maximum presented-root axis step was 0 cells.
- Stage-clipped frames: 0.
- Contact verification passed across 167 frames and five stances with zero
  planted drift, raster-span drift, root residual, or issues.

`cast_front` now declares a clip-local 20 FPS cadence. The projector remains
24 FPS. This temporal headroom prevents command-phase jitter from duplicating
one 24 FPS source drawing and skipping the next; no art or marker frame numbers
were changed.

## Artifact Hashes

- Normal-speed MP4:
  `8d79c844068e54f326be03ee019deb48fdf8b14c17eedfb317281e460940eb10`
- Quarter-speed MP4:
  `11a574b5c1bf5672ecbfb598bbce0ef459fb7043cc1296735e2dbb5e8cb87c26`
- Contact sheet:
  `68acfa50c20121c0565ada4315631decc9e0fe8c8912557fc105489aaa93c1b6`
- Machine acceptance:
  `3eedc7cc658db55f05ed625be010954586fac6107e4f8349030291fe5d4b4cc6`

## Reproduction

Run the capture against an isolated server:

```bash
.venv/bin/python tools/run_character_director_visual_review.py \
  --base-url http://127.0.0.1:8879 \
  --output-dir evidence/character-director/v7-cast-interruption-8217ccc2-2026-07-23 \
  --scenarios-file tools/character_director_scenarios/v7-cast-interruption.json
```

Then run the independent analyzer:

```bash
.venv/bin/python tools/analyze_character_director_v7.py \
  --manifest evidence/character-director/v7-cast-interruption-8217ccc2-2026-07-23/manifest.json \
  --output evidence/character-director/v7-cast-interruption-8217ccc2-2026-07-23/machine-acceptance.json
```

The version-2 scenario program fails closed if its accepted-trace triggers do
not appear within their declared frame bounds. The retained bundle includes
the program, wire capture, paired trace, decoded samples, contact report,
normal-speed MP4, quarter-speed MP4, contact sheet, and machine report.
