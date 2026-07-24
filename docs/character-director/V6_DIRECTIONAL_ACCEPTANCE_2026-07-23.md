# V6 Directional Turn, Reversal, And Stop Acceptance

Date: 2026-07-23

Accepted implementation commit:
`17637c53cc539056e660e3248f5850abcef902da`

Evidence:
`evidence/character-director/v6-directional-17637c53-2026-07-23/`

## Verdict

V6 passes its independent machine acceptance gate. The accepted capture proves
the authored south approach, 90-degree east turn, 180-degree west reversal, and
profile stop/settle sequence on the existing Python pixel-graph runtime.

This receipt accepts V6 engineering behavior. It does not replace normal-speed,
quarter-speed, or frame-by-frame human animation review.

## Measured Result

- 15 of 15 V6 machine checks passed.
- 222 of 222 frames were scenario-owned and contiguous.
- Transport drops: 0.
- Stage-clipped frames: 0.
- Final target error: 0 cells.
- Maximum world-root step: 0.0625 cells.
- Contact verifier: passed with 115 contact frames across 17 stances.
- Maximum planted-anchor drift: `2.842170943040401e-14` cells.
- Maximum planted raster-span drift: 1 cell.
- Maximum root residual: 0 cells.
- Contact verifier issues: none.

The accepted topology includes:

- a three-sector south-to-east facing progression;
- a five-sector east-to-west reversal progression;
- complete authored left and right 16-pose profile gait cycles;
- explicit contact-release phases;
- bounded staff-tip and staff-grip paths;
- a six-pose profile stop/settle sequence.

## Reproduction

Run the visual capture against an isolated server:

```bash
.venv/bin/python tools/run_character_director_visual_review.py \
  --base-url http://127.0.0.1:8879 \
  --output-dir evidence/character-director/v6-directional-17637c53-2026-07-23 \
  --sample-every-frames 2 \
  --scenarios-file tools/character_director_scenarios/v6-directional-walk.json
```

Then run the independent analyzer:

```bash
.venv/bin/python tools/analyze_character_director_v6.py \
  --manifest evidence/character-director/v6-directional-17637c53-2026-07-23/manifest.json \
  --output evidence/character-director/v6-directional-17637c53-2026-07-23/machine-acceptance.json
```

The retained bundle includes the exact scenario program, frame trace, wire
capture, decoded samples, MP4, contact sheet, contact-verification report, and
machine-acceptance report.
