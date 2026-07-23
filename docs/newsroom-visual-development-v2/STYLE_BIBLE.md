# Newsroom V2 Style Bible

## Visual thesis

The newsroom is a physical voxel stage that Wizard Joe inhabits. It is not a flat
pixel mosaic behind him. Furniture, screens, towers, shelves, and magical devices
must have enough depth to cast contact shadows and create useful occlusion while
remaining legible as chunky blocks.

## Construction

- Match the apparent voxel size of the approved character sources.
- Prefer substantial stepped volumes over thin rectangular outlines.
- Use cube-face shading to describe orientation and depth.
- Preserve source bevels, highlights, and material variation in the graph.
- Keep clean white negative space around the set and in every editorial screen.
- Keep modules visually separable for graph isolation.
- Avoid broad surfaces covered by a decorative tiny grid.

## Materials and color

Source colors are authoritative. Do not quantize newsroom art to the old twelve-color
palette.

- Cobalt and azure form the main architecture and upholstery.
- Gold marks important edges, controls, and visual hierarchy.
- Cyan is luminous but must retain visible cube boundaries.
- Magenta is a restrained state or focus accent.
- Warm brown gives furniture, shelves, and devices physical warmth.
- White is both the studio field and a valid object color; transparency is stored
  separately and must never be inferred from RGB after isolation.

## Scene composition

Compose in this order:

1. `background`
2. `set_piece`
3. rear `prop`
4. `character`
5. `effect`
6. `foreground`
7. `broadcast_overlay`

The desk face, chair fronts, lectern front, and platform lip may occlude the lower
body only. No set element may hide Joe's face, hat brim, required hand gesture,
source attribution, or captions.

## Performance space

- Preserve left and right walk-on lanes.
- Preserve staff clearance beside desks, chairs, and lecterns.
- Leave enough open floor for anticipation, planted poses, turns, and recovery.
- Keep screens inside natural pointing and over-shoulder bounds.
- Keep seated furniture broad enough for Joe's robe and folded wings.
- Make optional magic particles independent effect graphs.

## Camera behavior

The master sets support wide, medium, and modest high or low angles. Camera moves must
not expose missing set backs, crop the hat accidentally, or turn a foreground mask
into a face occluder. Camera-board character renderings are planning-only references.
