# V10 Production Acceptance Candidate

Date: 2026-07-24

Candidate implementation commit:
`9138f16d18ff822b885f4b4ed385c7373a40741f`

Evidence:
`evidence/character-director/v10-responsive-framing-9138f16d-2026-07-24/`

## Status

V10 is a machine-passing, independently reviewed product-approval candidate.
Product-owner approval remains pending. The product owner's V9 rubber stamp is
recorded only for V9 and is not reused here.

## Machine Verdict

**PASS**

- 528 scenario-owned frames at 24 FPS.
- Five scenarios in exact order: center, near, far, left edge, right edge.
- Scenario counts: 48, 96, 144, 120, and 120 frames.
- All transport frame indexes are contiguous.
- No silhouette crop; minimum required margins are four cells on the top and
  sides and six cells on the bottom.
- Terminal targets are exact and stable for the final 24 frames.
- Mean terminal scales are near `1.2842`, center `1.125`, and far `0.6750`.
- Left and right passes reach the safe framing boundary without crossing it.
- Contact verification passes across 359 contact frames and 65 stances.
- Maximum planted-anchor drift is effectively zero
  (`1.4210854715202004e-14` cells); raster-span drift is at most one cell.
- Desktop 1280x720 DPR1, desktop 1280x720 DPR2, and mobile 390x844 DPR3 all
  pass exact viewport, aspect/letterbox, integer physical-pixel projection,
  control-overlap, runtime-integrity, and synchronized first-frame checks.
- Every browser capture starts from the declared logical frame hash
  `fnv1a32:99face05` at `(0.0, 5.0)`, facing south, idle, neutral, and
  mouth closed.

## Independent Review

The animation review passes V10 with a framing score of **3/4**, no blocker,
and no hard failure. The sole minor note is that the fixed 16:9 stage produces
vertical whitespace on a portrait mobile viewport and intentionally small
facial detail during the far shot. The silhouette and action remain readable,
with no crop or UI collision.

The independent technical re-review passes V10 at **4/4**, with no blocker or
hard failure. It confirms that the prior stale first-frame defect is closed in
the literal first encoded frame of all three browser videos. It also
independently verifies provenance, all 228 manifest artifact hashes,
contiguous transport, integer physical cells, crop and overlap margins,
contact locking, and fail-closed start synchronization.

The technical review discloses 70-74 held browser presentation slots and
duplicate sampled frames. That residual does not undermine responsive-framing
acceptance, but the browser captures are not claimed as proof of flawless
24 Hz motion cadence.

Both required independent V10 reviews are complete. Their framing scores are
3/4 and 4/4. V10 has no scenario blocker or hard failure and is ready for the
product-owner decision. Aggregate Character Director release scoring remains
a later matrix-level obligation.

## Review Artifacts

- `manifest.json`
- `v10-machine-acceptance.json`
- `visual-review-2523503818bc-capture.mp4`
- `v10-quarter-speed.mp4`
- `visual-review-2523503818bc-contact-sheet.png`
- `v10-browser-desktop-dpr1.mp4`
- `v10-browser-desktop-dpr1-metrics.json`
- `v10-browser-desktop-dpr2.mp4`
- `v10-browser-desktop-dpr2-metrics.json`
- `v10-browser-mobile-dpr3.mp4`
- `v10-browser-mobile-dpr3-metrics.json`
- `animation_truth_trace.ndjson`
- `contact_verification.json`
- `docs/character-director/reviews/V10_RESPONSIVE_FRAMING_9138F16D_ANIMATION_REVIEW.md`
- `docs/character-director/reviews/V10_RESPONSIVE_FRAMING_9138F16D_TECHNICAL_REVIEW.md`

## Artifact Hashes

- Capture manifest:
  `cdc1595fbb010f1ea71858af04498b4c12daa1ebcc603c0945f1406c7a065277`
- Machine acceptance:
  `fd3241e001c1035e8a5e7676ff960f1c78ae966dd0c01783936511eeeb658dfc`
- Normal-speed atomic capture:
  `9714083dc033dbf7c656ec0bd60d29337af89656ae491e5528d387b9cc7870f3`
- Quarter-speed capture:
  `23044abdf443f045265eb464402d75ad274ebace66f995cee19c60d04c875720`
- Contact sheet:
  `2b5e7f636c8042dac777e315efdd2b14a8edb410bbdd4f052cc9ccc22b282b16`
- Desktop DPR1 video:
  `2c01149cfa79ca371be46cffce9ad67ce02662a1f601d5ba55303b238d34e310`
- Desktop DPR1 metrics:
  `f4dd4b2948ba9b59677823d602b9f1d8861a0016e99f607db329ac5fbeab3a52`
- Desktop DPR2 video:
  `d77f930c024cd31d13628296dbf3f7faaf3a271f83a4528a7a3b92d82b4e0e39`
- Desktop DPR2 metrics:
  `8fb9433cbce5dc12baa4238557a443418cb1229c233cb7df95cdcc963e6d3240`
- Mobile DPR3 video:
  `375add9681a7d1f17373bc441a05529ac90c0574715d7feb1a112517a6e3fbea`
- Mobile DPR3 metrics:
  `a14455983ba2f327a5d8715ac6d09c34a60c2e6607e89ebc068c0503d8743354`
- Contact verification:
  `33f4dce366e92de79404dccc8aa2c7089e9b04dcb8b14a6336c9c2581c428ffa`
- Animation truth trace:
  `9b05ccbdc3f486e87b160b3c31bd08ed0058b04850c2e8a49b140f9ec584f66d`

## Reproduction

Run the analyzer from a clean checkout of the candidate commit:

```bash
.venv/bin/python tools/analyze_character_director_v10.py \
  --manifest /absolute/path/to/evidence/character-director/v10-responsive-framing-9138f16d-2026-07-24/manifest.json \
  --browser-metrics /absolute/path/to/evidence/character-director/v10-responsive-framing-9138f16d-2026-07-24/v10-browser-desktop-dpr1-metrics.json \
  --browser-metrics /absolute/path/to/evidence/character-director/v10-responsive-framing-9138f16d-2026-07-24/v10-browser-desktop-dpr2-metrics.json \
  --browser-metrics /absolute/path/to/evidence/character-director/v10-responsive-framing-9138f16d-2026-07-24/v10-browser-mobile-dpr3-metrics.json \
  --output /absolute/path/to/v10-machine-acceptance.json
```

The evidence was captured from a clean proof checkout at commit `9138f16d`,
not from the persistent user server. The disposable proof server was stopped
after capture. The protected local server at `127.0.0.1:8765` remained
running and responsive.
