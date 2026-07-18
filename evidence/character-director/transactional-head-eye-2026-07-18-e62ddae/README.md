# Transactional Head-Eye Visual Review

Capture date: 2026-07-18 UTC  
Candidate: `e62ddaef8dd9124e4591529e4fb694d93b541c4d`  
Branch: `codex/character-director`  
Runtime: isolated Python visualizer on `127.0.0.1:8875`

## Result

**Capture valid; animation performance rejected.**

| Measurement | Result |
| --- | ---: |
| Duration | 14.922711 s |
| Presentation frames | 342 |
| Frame range | 0-341 |
| Presentation rate | 24 FPS |
| Queue high-water | 1/16 |
| Queue overruns | 0 |
| Decoded gaps | 0 |
| Decoder errors | 0 |
| Dropped frames | 0 |

The run proves that candidate `e62ddae` publishes coherent whole-sprite frames
through gaze, expression, locomotion, turns, casting, speech, and interruption.
It does not pass the visual-performance rubric. Two independent reviews found
skating locomotion, abrupt pose handoffs, weak cast recovery, and incomplete
scenario coverage. The observed categories normalize to approximately 50%,
below the 85/100 release gate, and several categories remain unscored.

## Evidence Binding

- `manifest.json` SHA-256:
  `647e4e6743037198afa5dfba800304c30593b693227469b173534e5aa155aef2`
- `visual-review-5bd90caa3c93-capture.mp4` SHA-256:
  `817b5d9c215e5f3aac6084090b8cff2f8989deb2ee4374cc3e523446268c13cb`
- `visual-review-5bd90caa3c93-contact-sheet.png` SHA-256:
  `1f7ac78663be5b3dabdfe5393be64e82f72f3037fa7e846935510e40274c37ab`
- `wire/frames.bin` SHA-256:
  `64522d8011aa08939003a091b443819efd54603d06348df14892a0c1c81b80ec`
- `wire/index.ndjson` SHA-256:
  `d8caeef9e26f7d1bd839cf27c5dd00ed4ae33a59c2e2b90e712de864e4185838`

The manifest binds the run to a clean worktree and full candidate commit. Its
HTTP state observations remain explicitly time-adjacent rather than atomic
frame/state pairs. The capture contains no browser-pixel or audio truth chain.

## Reviews

- `reviews/animation-director-review.md`: supervising animation direction.
- `reviews/technical-qa-review.md`: technical animation QA.
- `reviews/REVIEW_SYNTHESIS.md`: consensus, disagreement resolution, and next
  correction order.

This package is diagnostic evidence. It must not be cited as release
acceptance.
