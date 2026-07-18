# Authored Transition Visual Review

Capture date: 2026-07-18 UTC

Candidate: `4a5af34bef9166e5ffe3fe9651aa7de50935bf9b`

Branch: `codex/character-director`
Runtime: isolated Python visualizer on `127.0.0.1:8875`

## Result

**Capture valid; independent review rejects release with material improvement.**

| Measurement | Result |
| --- | ---: |
| Presentation frames | 341 |
| Frame range | 0-340 |
| Presentation rate | 24 FPS |
| Queue high-water | 1/16 |
| Queue overruns | 0 |
| Decoded gaps | 0 |
| Decoder errors | 0 |
| Dropped frames | 0 |

The candidate adds a simulation-owned transition lifecycle, contact/marker
gates, whole-sprite handoff, ground-distance phase rebasing, a deterministic
stopped-contact settle, rear-walk transition edges, and complete front-walk
poses for horizontal stage travel. Rendering consumes committed animation
state and cannot advance a transition.

The capture reduces static profile sliding with complete stride poses and
removes the former reset displacement from the speech-interruption scene.
The speaking and interruption snapshots both retain world position
`(0.5006686019107497, 5.0)`; the interruption closes the mouth and clears the
speech ID without moving the root. This is evidence of improvement, not a
release claim. Planted-foot drift has not yet been measured to the required
zero-cell standard, and the complete V1-V10, browser, audio, reduced-motion,
and real Prism performance matrix remains open.

## Evidence Binding

- `manifest.json` SHA-256:
  `9b62cf3967d5faa8c04e744977ab38ab75874016fbdee78c134af6c331892522`
- `visual-review-d5a6a414361c-capture.mp4` SHA-256:
  `f2eb06ae2d48aebfded94ea810bb566c62b29be9dc027de4cc46ab663d9bdd97`
- `visual-review-d5a6a414361c-contact-sheet.png` SHA-256:
  `d9e9aed68558c2f06d319dcc9859e721d75e6b0722b3c9fe659219b8fe602dbd`
- `wire/frames.bin` SHA-256:
  `2e1393f3ca7ffc59918144d325e6a3e1c5d95a86333b2f927ac7e5df7ec96b12`
- `wire/index.ndjson` SHA-256:
  `8817687fabb3d289c036d5dec65adc27f9a0d5ed0d0c68473e6decdcf77775dc`

The manifest binds the run to a clean worktree at the full candidate commit.
HTTP state observations remain explicitly time-adjacent rather than atomic
frame/state pairs. The package contains no real Prism audio truth chain.

## Reviews

Independent animation-direction and technical-QA reviews are recorded under
`reviews/`. Their synthesis retains this package as regression evidence and
rejects it for release. The observed-only animation score improved from 50.0%
to 65.9%, but locomotion continuity, planted-foot measurement, turn/stop pops,
cast-effect timing, and the complete audiovisual scenario matrix remain open.
