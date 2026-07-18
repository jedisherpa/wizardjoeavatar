# Review Synthesis

Candidate: `e62ddaef8dd9124e4591529e4fb694d93b541c4d`  
Manifest SHA-256: `647e4e6743037198afa5dfba800304c30593b693227469b173534e5aa155aef2`

## Decision

**Reject for release; retain as a valid diagnostic capture.**

Both independent reviewers agree that the transactional renderer presents
complete, untorn rasters and that framing is readable. Both also score the
observed animation at approximately 50% normalized across the categories they
could judge. Neither issued a release score because the required V1-V10 matrix,
audio/browser truth chain, reduced/still variants, and 60-second material are
absent.

Consensus correction order:

1. Replace translation-only locomotion with contact-authored starts, cycles,
   reversal, stop, and follow-through.
2. Preserve root continuity through interruption and reset.
3. Execute graph transition recipes as timed handoffs instead of immediate
   whole-pose replacement.
4. Make eye lead, head follow, and settle visibly temporal.
5. Lengthen cast recovery and bind effect onset/release to authored markers.
6. Capture the full acceptance scenario matrix and truth chain.

## Resolved Disagreement

The technical QA review says frames 319-324 contain no visible root/body jump.
The animation-director review reports a large leftward displacement. Direct
inspection of the retained frame-319 and frame-324 PNGs confirms the latter:
the entire character, including feet and staff, shifts left by roughly 48
output pixels, or about 12 four-pixel cells. The manifest also records the
reset returning world X from approximately `0.5028` to `0.0`. Root continuity
on reset/interruption is therefore a P0 defect.

The original independent reports remain unedited so their judgments stay
attributable.
