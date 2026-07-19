# V1 Listening Provenance Refresh: aa4ca2f

Status: **PASSED**

## Purpose

This package refreshes V1 evidence after commit `aa4ca2f` corrected the
permission-world visual test's obsolete hard-coded projection scale. That test
change does not modify renderer, scheduler, pose, browser, or capture behavior.

## Evidence

- Source commit: `aa4ca2f9dfc64d0a0b55622413e2284ca8e67291`
- Package: `evidence/character-director/v1-listening-aa4ca2f-2026-07-18/`
- Atomic capture: 288 contiguous frames, zero dropped frames, zero gaps, zero
  queue overruns
- Machine acceptance: passed all 13 checks
- Browser layout: 288 frames, zero client drops, zero decode errors, zero page
  exceptions
- Review bundle: complete with machine, quarter-speed, and Chrome-layout roles
- Blink closures: 125 ms and 125 ms, with 5.128-second onset spacing
- Head sequence: `front_idle -> walk_front_left -> profile_left`
- Root span and planted drift: 0.0 cells

## Relationship To Independent Acceptance

The immediately preceding renderer-identical candidate `8fb8c4b` received two
fresh independent **ACCEPTED** verdicts:

- `V1_LISTENING_8FB8C4B_ANIMATION_REVIEW.md`
- `V1_LISTENING_8FB8C4B_TECHNICAL_REVIEW.md`

The refresh repeats the complete machine and browser gates against current
branch provenance. It does not broaden those reviews beyond V1 Listening.
