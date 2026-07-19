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
staff and authors a rigid staff appendage around one fixed grip; every output
is then stored as colored pixel nodes in the canonical pose library.

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
travel. The old overhead `magic_cast`, horizontal defensive pose, guard, and
thrust snapshots are no longer used by `cast_front`.

## Verification

Focused runtime, pose, channel, marker, overlay, contact, permission, and V3
tests passed 96 of 96. The capture and review-contract suite subsequently
passed 33 of 33. The deterministic offline rebuild command is:

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

The analyzer fails closed unless the transport is contiguous, exactly 240
scenario-owned frames form individually contiguous scenario blocks, and any
unowned frame is a bounded transition between those blocks. Every owned frame
must pair with a truth record; all three casts must use the canonical atomic
pose for their presented authored frame; the repeated casts must collectively
cover frames 0 through 30; frame 31 must equal the following neutral graph;
roots and the staff grip must remain fixed; staff-tip travel must stay within
two local cells per authored frame; all four markers must occur once and in
order in every cast; effect phases must begin at the staff event; contact must
verify; and every cast silhouette must remain inside the 240 by 135 stage.
Normal-speed, quarter-speed, and browser-layout review remain separate gates.

The final V3 candidate proof is
`evidence/character-director/v3-canonical-cast-a72f791-2026-07-19/`, bound to
clean commit `a72f7915479787ba8cd65da2f5075ec99400c16c`. Its machine report passes
all eleven V3 checks over 242 contiguous transport frames and exactly 240 owned
frames, with zero drift, continuity, effect, clipping, decode, or queue
failures. The complete review manifest binds the machine report, normal and
quarter-speed videos, browser replay, and browser metrics. Browser replay has
zero page or console errors and zero presentation faults.

The `092f78e` bundle remains as rejected audit evidence. Independent technical
review found that its hold scenarios rendered stale final cast poses even after
the controller settled to `front_idle`; it also found the initially published
bundle incomplete. The final candidate removes that feedback path, adds an
end-to-end settle regression, and includes every declared sample and wire file.

The previous `a8d0e28` evidence predates this authored rig and is retained only
as historical comparison. It is not acceptance evidence for the current V3
implementation.
