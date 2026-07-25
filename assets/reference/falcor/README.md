# Falcor Vehicle-Character Reference Packet

Falcor is a fictional Joeville vehicle character based on the project owner's black lifted 4Runner reference. The exterior identity lock is dark green-black paint, four doors, rear liftgate, roof basket, gray fender flares, lifted suspension, oversized all-terrain tires, black wheels, rectangular lamps and a rugged bumper. Manufacturer badges are excluded from production assets.

## Coverage

- `source/`: preserved source reference.
- `concepts/01`: voxel hero direction.
- `concepts/02`: six-view turnaround.
- `concepts/03`: closed, hood-open, side-door-open and liftgate-open articulation.
- `concepts/04`: engine-bay design proposal.
- `seat-views/01` through `05`: driver, front passenger, rear left, rear center and rear right viewpoints.

The seat and engine-bay images are inferred design proposals, not photographic documentation of the owner's actual cabin or engine. Runtime art is a deterministic direct-cell library rasterized from the canonical worksheets, matching the corrected CrystAIl pipeline. It does not use the former simplified procedural silhouette.

## Runtime state contract

- Engine: `off`, `starting`, `idle`, `running`.
- Drive: `parked`, `road`, `off_road`; road modes require a running engine.
- Articulation: driver, front passenger, rear left, rear right, liftgate and hood; openings are rejected unless parked.
- View: exterior, all five seats and engine bay.
- Sound: original loopable synthesized idle, road and off-road beds in `assets/audio/falcor/`.
