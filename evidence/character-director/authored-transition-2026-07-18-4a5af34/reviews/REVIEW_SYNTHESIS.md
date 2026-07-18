# Authored Transition Review Synthesis

Candidate: `4a5af34bef9166e5ffe3fe9651aa7de50935bf9b`

Evidence: `authored-transition-2026-07-18-4a5af34`
Decision: **retain as regression evidence; reject for release**

## Consensus

The candidate is a material improvement over the prior rejected capture. The
animation director's observed-only score increased from 50.0% to 65.9%, and
both reviewers agree that the former terminal reset displacement is eliminated
for the captured `speech_stop` path. Whole-sprite integrity is sound, and the
horizontal walk now contains varied authored stride poses instead of one
static profile sliding across the stage.

The capture does not establish release quality. Start, stop, turn, and
reversal behavior still reads as pose replacement rather than continuous
weighted motion. A back-facing flash appears during reversal, the stop pops to
a profile pose, and planted-foot drift cannot be measured from the retained
evidence. The cast phrase has a clearer preparation, stroke, hold, and recovery
than the prior capture, but its effect begins early and remains detached after
the body settles. The interruption is technically clean but lacks an acted
response and settle.

The package also lacks the complete V1-V10 scenario matrix, real Prism audio,
and atomic per-frame state/contact truth. It is diagnostic evidence, not a
production acceptance receipt.

## Next Priority

1. Emit a frame-indexed transition, pose, phase, contact, root, and effect
   truth trace alongside the visual capture.
2. Add measured planted-foot/root correction with a zero-cell drift gate.
3. Author start anticipation, braking, reversal, final plant, overshoot, lag,
   and settle instead of relying on abrupt pose substitution.
4. Bind cast-effect onset and release to commit/recovery markers and record
   interrupted cast variants.
5. Capture the complete V1-V10 matrix with real Prism audiovisual timing and
   repeat the two independent reviews.

## Source Reviews

- `animation-director-review.md`: **reject**, 65.9% observed-only normalized
  score; locomotion 2/4, hand acting 3/4, interruption 3/4.
- `technical-qa-review.md`: **release rejected**; narrow pass for elimination
  of terminal reset displacement, partial pass for reduced side skating, and
  insufficient contact/audiovisual evidence.
