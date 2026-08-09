# Kingfisher Character Assets

## Shipping library

The current product library is `compiled/library-index.json`. It contains the
existing 110-pose Kingfisher repertoire and does not expose the unfinished
paired-beak review sequence.

## Deferred additional poses

The 66 additional open-beak mates are paused by user direction as of
2026-08-08. They remain preserved under `legacy-pairs-v1/` and
`pair-review-compiled/`, but they are review-only:

- User-approved pairs: 0
- Runtime-admitted pairs: 0
- Integrated additional speech pairs: 0
- Next review gate: Pair 1, `neutral-front`
- Required method: one isolated closed/open pair at a time

Do not batch-approve, regenerate, or runtime-admit these poses. Resume only
from the handoff in
`docs/character-director/KINGFISHER_ADDITIONAL_POSES_HANDOFF_2026-08-08.md`.

The release gate verifies both sides of this boundary: the existing 110-pose
library must remain loadable, and every deferred pair must remain excluded.
