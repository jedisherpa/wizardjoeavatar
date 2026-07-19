# Authored Cast Continuity

## Problem

The original front cast mixed full-height and width-fitted pose graphs at one
projection scale. Joe visibly shrank during the wide staff poses, then the
staff jumped from the far right side of the frame directly into a leftward
thrust. Unit timing was valid, but the performance did not read as one body
carrying one prop through a continuous action.

## Pose-Density Contract

Wide source poses now declare an explicit rational `presentation_scale` in the
source manifest. The deterministic pose generator copies that metadata into
the square-cell library, and the projector applies it around the canonical
root. This restores the source's authored cell density without changing the
pixel graph, flattening a PNG at runtime, or moving a planted contact.

The current cast family uses these density ratios:

| Pose graph | Scale ratio |
| --- | --- |
| `front_staff_guard_low` | `96 / 94` |
| `front_staff_guard_windup` | `96 / 78` |
| `front_magic_staff_thrust` | `96 / 73` |

`front_staff_block_horizontal` also carries `96 / 75` for its independent
defensive use. Its foot anchors were recalibrated against colored boot cells,
but it is deliberately excluded from the cast because its rightward guard is
not a coherent intermediate for the leftward spell release.

## Choreography Contract

The V3 correction replaces the eight full-body snapshots with 32 complete
`cast_front_00` through `cast_front_31` pixel graphs. Each graph is generated
offline from the stable `front_idle` body. The generator removes the flattened
staff and inverse-nearest rotates the complete neutral staff pixel graph around
one fixed grip. The source hook, shaft width, length, and palette therefore
remain authoritative instead of being replaced by a synthetic line; every
output is stored as colored pixel nodes in the canonical pose library. A
`cast_staff_rigid` region tag gives offline acceptance an exact prop raster
without changing the projected pixels.

The live visualizer still projects one complete pixel graph for every frame.
It does not load the PNG reference, dissolve between images, or construct
partial limbs at runtime.

The 32 frames retain the existing performance phases:

1. neutral and preparation, frames 0-5
2. windup and commitment, frames 6-10
3. recoil into the stroke, frames 11-13
4. effect stroke, frames 14-17
5. effect hold, frames 18-22
6. recovery, frames 23-27
7. settled neutral, frames 28-31

Markers occur at authored frames 10 (`action_commit`), 14
(`action_effect`), 23 (`action_recoverable`), and 28 (`action_settled`). Speech
before commit may cancel the cast; speech after commit waits through recovery.
The magic effect follows the per-frame staff-tip anchor and fades over recovery.

Adjacent authored staff-tip coordinates differ by at most two local cells. The
staff hand remains fixed at local cell `(56, 50)`, so the grip cannot switch
hands or teleport across the silhouette. Root, feet, body, face, robe, and
wings remain structurally identical through the cast; only the authored prop
appendage and effect change.

Regression tests require the exact 32-frame graph sequence, one authored frame
per sample, a fixed grip, and no more than two cells of adjacent staff-tip
travel. The asymmetric hook can move at most three cells at its outside edge
during an inverse-nearest rotation; this measured square-grid bound is checked
separately together with exact neutral endpoints, source-palette preservation,
and a narrow staff-cell-count ratio. The old overhead `magic_cast`, horizontal
defensive pose, guard, and thrust snapshots are no longer used by `cast_front`.

## Verification

The current focused V3/V4 pose, generator, analyzer, and capability suite
passes 37 of 37 tests. The deterministic offline rebuild command is:

```bash
.venv/bin/python tools/generate_reference_avatar_pose_cells.py \
  --reuse-authored-library --check-deterministic
```

The strict runtime proof uses
`tools/character_director_scenarios/v3-canonical-cast.json`, then evaluates the
capture with:

```bash
.venv/bin/python tools/analyze_character_director_v3.py \
  --manifest <capture>/manifest.json \
  --output <capture>/v3-machine-acceptance.json
```

The analyzer fails closed unless the transport is contiguous, exactly 312
scenario-owned frames form individually contiguous scenario blocks, and any
unowned frame is a bounded transition between those blocks. Every owned frame
must pair with a truth record; all three casts must use the canonical atomic
pose for their presented authored frame; every cast must include every recovery
frame from 23 through 30; frame 31 must equal the following neutral graph;
roots and the staff grip must remain fixed; staff-tip travel must stay within
two local cells and the complete staff raster within three local cells per
authored frame; all four markers must occur once and in order in every cast;
effect phases must begin at the staff event; contact must verify; and every
cast silhouette must remain inside the 240 by 135 stage. Normal-speed,
quarter-speed, and browser-layout review remain separate gates.

The `a72f791` proof bundle is retained as rejected audit evidence. Its machine
and technical reviews passed, but independent animation review found two
blocking defects: the staff changed construction inside each cast and the first
cast capture skipped late recovery frames. The current implementation directly
addresses both findings by transforming the complete source staff graph and by
capturing 60 owned frames for every cast. It is not accepted until a fresh,
clean-commit capture passes the strengthened analyzer and both independent
reviewers issue explicit PASS verdicts.

The earlier `092f78e` bundle also remains rejected audit evidence. Independent technical
review found that its hold scenarios rendered stale final cast poses even after
the controller settled to `front_idle`; it also found the initially published
bundle incomplete. The final candidate removes that feedback path, adds an
end-to-end settle regression, and includes every declared sample and wire file.

The previous `a8d0e28` evidence predates this authored rig and is retained only
as historical comparison. It is not acceptance evidence for the current V3
implementation.
