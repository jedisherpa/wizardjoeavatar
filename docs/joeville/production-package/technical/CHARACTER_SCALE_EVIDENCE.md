# Character Scale Evidence

## Evidence boundary

The audited runtime provides measurable evidence for **Wizard Joe only**. No other integrated character package exists in `WizardJoeAvatar` or `ASCILINE`, so this document must not be read as a 13-character lineup. Twelve cast scale records remain missing.

## Canonical Wizard Joe dimensions

| Measure | Verified value |
|---|---:|
| Runtime character package | `wizard-joe-v1` |
| Generated pose count | 89 |
| Source canvas per pose | 72 x 96 logical cells |
| Root/feet anchor | (36, 95) |
| Horizontal center at root | 36 cells |
| Maximum source height above root | 95 cells |
| Runtime reference scale multiplier | 0.90 |
| Runtime horizontal multiplier | 1.18 |
| Ground world range | x = -5.0..+5.0, z = 1.5..10.0 |
| Default world position | (x 0.0, z 5.0) |

All 89 entries in the current JSON library use the same 72 x 96 canvas and root. Their occupied-cell silhouettes vary substantially by pose, so the canvas is a packaging envelope rather than a body measurement.

## Projection and render scale

The projected scale before reference multiplication is:

```text
depth = clamp((10 - z) / 8.5, 0, 1)
projected_scale = quantize_to_1/8(0.70 + 0.85 * depth)
render_scale_y = projected_scale * 0.90
render_scale_x = render_scale_y * 1.18
```

When flying, both axes are multiplied by `max(0.76, 1 - 0.07 * altitude)`.

### Centered grounded measurements on the medium 240 x 135 stage

These figures were measured from actual rendered frames by comparing each frame to the cached procedural background. Bounds include Wizard Joe plus the contact shadow and any runtime overlays.

| World z | Projected screen root (x, y) | Quantized projected scale | Final Y scale | Measured changed-cell bounds | Measured footprint |
|---:|---:|---:|---:|---:|---:|
| 1.5 | (120.0, 128.25) | 1.50 | 1.350 | x 71..169, y 1..131 | 99 x 131 |
| 3.0 | (120.0, 118.96) | 1.375 | 1.2375 | x 75..164, y 11..131 | 90 x 121 |
| 5.0 default | (120.0, 106.57) | 1.25 | 1.125 | x 79..160, y 22..130 | 82 x 109 |
| 7.0 | (120.0, 94.18) | 1.00 | 0.900 | x 88..153, y 26..113 | 66 x 88 |
| 10.0 | (120.0, 75.60) | 0.75 | 0.675 | x 95..144, y 25..90 | 50 x 66 |

Because the pose is anchored at the feet, `screen_y` is not the final feet row. The reference path computes a grounded root with `min(rows - 8, screen_y + 18 * render_scale)`. This caps the grounded root near row 127 on the medium stage.

## Camera-safe width evidence

The nominal x world bounds are not safe framing bounds. Actual centered/default and extreme-position renders produced:

| World position | Projected center x | Final Y scale | Visible changed-cell bounds | Finding |
|---|---:|---:|---:|---|
| (-5, 1.5) | -19.5 | 1.350 | x 0..29, y 12..127 | Most of character is off left edge |
| (+5, 1.5) | 259.5 | 1.350 | x 210..239, y 35..125 | Most of character is off right edge |
| (-5, 5.0) | 12.0 | 1.125 | x 0..52, y 22..130 | Substantial left clipping |
| (+5, 5.0) | 228.0 | 1.125 | x 187..239, y 22..130 | Substantial right clipping |
| (-5, 10.0) | 57.0 | 0.675 | x 32..81, y 25..90 | Fully visible |
| (+5, 10.0) | 183.0 | 0.675 | x 158..207, y 25..90 | Fully visible |

The measured footprint is pose-dependent. The production camera-safe region must be computed from each selected pose's occupied bounds, not only the 72 x 96 package canvas.

## Practical environment scale guide

Until a formal physical-height convention exists, use **Wizard Joe default grounded height at z=5** as the runtime-relative unit:

```text
1 Joe-default screen height = approximately 109 logical rows including shadow
1 Joe-default screen width  = approximately 82 logical columns including shadow
```

This is roughly 81% of the 135-row stage height and 34% of its width. It is deliberately large, suitable for a hero/host shot, but leaves little vertical room for architecture or full-cast staging.

For production design previews:

- Hero/medium staging: use z near 5, with about 82 x 109 cells occupied.
- Two-character dialogue: z 7 is a more credible starting point; one character is about 66 x 88 cells before pose variance. Two characters still require careful horizontal staging.
- Small group/ensemble: z 10 yields about 50 x 66 cells per Wizard Joe, but thirteen figures of this width cannot fit in one 240-column row. Multi-row depth blocking and overlap are mandatory.
- Thirteen equal Wizard-Joe-width figures at z 10 would require 650 columns without overlap. The stage has 240. Even at far depth, a full-cast lineup needs approximately 63% overlap, multiple depth rows, a wider/higher profile, or smaller character scaling.
- The current projection clamps at z 10, so simply moving characters farther away cannot make them smaller.

The previous bullets are staging inferences from the measured Wizard Joe envelope, not evidence about the missing characters' true proportions.

## Set-dimension implications

Joeville set art should reserve the following logical zones in 240 x 135 previews:

- Horizon reference: row 75.6.
- Near floor reference: row 128.25.
- Caption/UI risk zone: browser captions occupy the lower center around 22 CSS pixels above the viewport edge; production plates should not place indispensable action there.
- Default Wizard Joe head/top: approximately row 22 at z 5 in `front_idle`.
- Default Wizard Joe feet/shadow: approximately row 130 at z 5.
- Far Wizard Joe vertical extent: approximately rows 25..90 at z 10.
- Near Wizard Joe can touch row 1 at z 1.5, so overhead scenery will be obscured or the pose will clip.

Doors, counters, seats, stairs, and props cannot yet be assigned honest world-unit dimensions. The runtime contains no conversion between world units and human meters and no seated-body measurements. Any such metric before character lineup review would be invented.

## Missing evidence required for the 13-character cast

Create one record per character with:

1. canonical package ID and display name;
2. source and runtime pose-library paths;
3. canonical standing canvas and occupied silhouette bounds;
4. root, head, hand, hip, seat, foot, and eye-line anchors;
5. default scale multiplier and horizontal multiplier;
6. measured footprints at z 1.5, 3, 5, 7, and 10;
7. widest action pose and tallest action pose;
8. seated, crouched, airborne, and dancing bounds;
9. collision radius and personal-space radius;
10. camera-safe x bounds by depth;
11. prop reach and hand-off range;
12. approved relative-height lineup against Wizard Joe;
13. two-, five-, and thirteen-character blocking captures from the real runtime.

## Scale acceptance gate

Do not approve Joeville doors, furniture, counters, trail widths, dance-floor capacity, Castle Grace ensemble rooms, or group camera plans as production-final until:

- all 13 packages are located or created;
- the real lineup is rendered on one shared ground plane;
- their roots and eye lines are normalized;
- the widest/tallest pose envelopes are measured;
- safe x/z blocking regions are computed from occupied bounds;
- the 13-character ensemble is rendered without unintended clipping;
- foreground occlusion and multi-character depth sorting exist in the runtime.

