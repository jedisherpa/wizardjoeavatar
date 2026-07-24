# V9 Accessibility Profile Acceptance

Date: 2026-07-24

Accepted implementation commit:
`c46d4ec707716f76d98baeb6dd59707494b7efef`

Evidence:
`evidence/character-director/v9-accessibility-profiles-c46d4ec-2026-07-24/`

## Verdict

V9 is accepted for animation behavior.

- Machine acceptance: **PASS**, eight of eight checks.
- Product-owner visual acceptance: **PASS**, explicitly approved on
  2026-07-24 with "you have my rubber stamp for v9."
- Independent artifact review: the inspected comparison frame was clean,
  centered, unclipped, and showed the intended full-versus-suppressed body
  distinction. That reviewer did not complete a full temporal review and
  therefore returned an incomplete evidence-review result rather than an
  animation rejection.

The product-owner approval closes the V9 human animation gate. It does not
turn this video-only package into proof of audiovisual synchronization. AV
lip-sync remains an integrated-production obligation for V10.

## Measured Result

- 648 scenario-owned frames at 24 FPS.
- 216 frames for each of `full`, `reduced`, and `still`.
- 652 transport frames total and zero dropped frames.
- Full profile: 22 body hashes, six authored actions, 32.67 cells of walk
  travel, and 17 cast-effect frames.
- Reduced profile: one body hash, one root, no effect frames, and only
  speech/face/mouth/gaze channels retained.
- Still profile: one body hash, one root, no effect frames, and only
  speech/face/mouth/gaze channels retained.
- No clipped frames.
- Contact verification passed.
- One authenticated, score-bound media replay with 27 accepted sequences.
- Runtime observations use schema
  `character_director_runtime_observations_v2`.
- The active proof correctly records only `runtime_epoch` and
  `wizard_runtime_epoch`; no inactive character epochs were fabricated.

The four unowned transport frames are indexes `0`, `1`, `218`, and `435`.
Frames `0` and `1` precede the first armed capture window. Frames `218` and
`435` are the single published boundary frames between profile windows. They
have no scenario or presentation-frame ownership and are excluded from the
648-frame acceptance video by the capture-window contract.

## Artifact Hashes

- Capture manifest:
  `b74d87d20a432891a97d2d9279d9f9dfd26cdb1fa84111525eeb83371fc011f5`
- Machine acceptance:
  `5824aaf25e27209065bd3fa702d82ab14863cbacb9a6e68f560ebf3c1aa0da51`
- Normal-speed capture:
  `590f6f713f5c96a3beba198da6de354b3f0d571b54f9254fdba7e52fe8e80dfa`
- Quarter-speed capture:
  `a3d31a02944d96f69b282a8703266b1d2e356aeff9026d34e6d809ce97ec56aa`
- Synchronized profile comparison:
  `d708f2d7740aed846cb212e6fe3e0331a63f13a87cea5fa6ac3dbecd375d9a8d`
- Comparison still:
  `c71a1a85a9705906aa5a3b21a5a49190991e942be3987837fc45f5d462a9b6d2`
- Contact sheet:
  `84bdd1e9cda755e81163cdc618f9ae5ccd405601f41f11e5a7f22a1d2b630411`

## Reproduction

The capture is bound to the clean proof checkout recorded in its runtime
identity. Revalidate it from that checkout:

```bash
.venv/bin/python tools/analyze_character_director_v9.py \
  --manifest /absolute/path/to/evidence/character-director/v9-accessibility-profiles-c46d4ec-2026-07-24/manifest.json \
  --output /absolute/path/to/evidence/character-director/v9-accessibility-profiles-c46d4ec-2026-07-24/v9-machine-acceptance.json
```

The retained package includes the scenario program, wire capture, atomic
truth trace, decoded samples, contact report, normal-speed video,
quarter-speed video, synchronized three-profile comparison, comparison still,
contact sheet, and machine report.
