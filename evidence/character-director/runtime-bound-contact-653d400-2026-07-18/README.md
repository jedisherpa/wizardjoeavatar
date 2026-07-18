# Runtime-Bound Contact Evidence

This package is a strict external capture of the Python ASCILINE Character
Director served on isolated loopback port `8875`. It does not use or replace the
protected legacy process on port `8765`.

## Result

- Evidence status: `VALID`
- Runtime commit: `653d4002c9bc5764c6ebc20c0b5f56dcfef9dfb8`
- Runtime PID: `76433`
- Runtime identity stable from the first request through the final trace request
- Frames: `341` contiguous decoded frames
- Dropped frames: `0`
- Decode gaps: `0`
- Queue overruns: `0`
- Contact issues: `0`
- Maximum locked-anchor drift: `1.4210854715202004e-14` cells
- Maximum locked raster-span drift: `1.0` cell
- Root residual: `0.0` cells
- Presentation markers: commit, effect, recoverable, and settled, each delivered
  once and in authored order

The manifest references 46 byte-addressed artifacts. The complete MP4, contact
sheet, sampled PNGs, adaptive wire stream, frame index, atomic animation truth
trace, and contact report are all included in this directory.

Independent review decisions:

- `docs/character-director/reviews/RUNTIME_BOUND_CONTACT_653D400_TECHNICAL_REVIEW.md`
  accepts the package as engineering evidence.
- `docs/character-director/reviews/RUNTIME_BOUND_CONTACT_653D400_ANIMATION_REVIEW.md`
  rejects the captured motion for visual-performance release and identifies the
  next authored-transition work.

## Primary Artifacts

- `manifest.json`: capture validity, runtime identity, frame records, scenario
  ranges, and artifact hashes
- `visual-review-78b57f68726e-capture.mp4`: 24 FPS rendered capture
- `visual-review-78b57f68726e-contact-sheet.png`: sampled visual review sheet
- `animation_truth_trace.ndjson`: atomic accepted-frame animation truth
- `contact_verification.json`: decoded-raster and geometry contact report
- `wire/frames.bin` and `wire/index.ndjson`: original adaptive ASCILINE stream

## Reproduction

From a clean checkout of the recorded commit:

```bash
.venv/bin/python tools/run_wizard_avatar_server.py \
  --host 127.0.0.1 --port 8875 --cols 240 --rows 135 --fps 24 --quiet

.venv/bin/python tools/run_character_director_visual_review.py \
  --base-url http://127.0.0.1:8875 \
  --output-dir /tmp/wizardjoe-runtime-bound-contact-653d400
```

The output directory must remain outside the checkout during capture. The
runtime identity endpoint refreshes Git provenance at both boundaries, so
writing evidence into the checkout during capture correctly invalidates a clean
source claim.

## Interpretation

This package proves transport continuity, process and commit provenance,
presentation-marker delivery, contact-lock geometry, and visible planted-foot
pixels. It does not by itself certify studio-quality acting or interpolation.
The contact sheet and MP4 must receive a separate animation-direction review.
