# Newsroom Style Bible

> Superseded: the flat-palette and small-grid rules below apply only to the archived
> v1 references. The active art direction is
> `docs/newsroom-visual-development-v2/STYLE_BIBLE.md`.

## Visual thesis

Wizard Joe's newsroom is a bright, friendly broadcast stage assembled from the same visible square-cell grammar as the approved character. It should feel credible enough for news and playful enough for a wizard host. The white field is active negative space, not an unfinished background.

## Construction rules

- Design on a 320x180 logical canvas.
- Build silhouettes from crisp, axis-aligned square cells.
- Use flat cell colors. Do not reproduce generated gradients, gloss, soft shadows, antialiasing, or texture.
- Prefer one-cell and two-cell steps over smoothed diagonals.
- Keep important shapes readable in the 320x180 previews.
- Use disconnected cells only for intentional magic, indicators, or broadcast particles.
- Keep reusable background plates character-free.
- Keep screen interiors blank; editorial content arrives as a verified overlay.

## Palette

Use only versioned Wizard Joe palette IDs during tracing:

| Role | Hex |
| --- | --- |
| outline | `#17191C` |
| shadow gray | `#363A3E` |
| white | `#F4F4F1` |
| brown dark | `#4C2912` |
| brown | `#874719` |
| cobalt | `#082D59` |
| blue | `#0E4C89` |
| blue light | `#176DB5` |
| gold | `#EFA000` |
| gold light | `#FFD247` |
| magenta | `#C51E72` |
| cyan magic | `#26D7E8` |

Sets should be mostly white, cobalt, blue, and cyan. Gold defines important edges and landmarks. Magenta is a sparse state or focus accent. Brown is reserved for furniture warmth and magical devices. Near-black is structural, not a dominant field.

## Scale and proportion

- Desk top: near elbow height for a seated or standing Wizard Joe profile.
- Display target: large enough for a clear over-shoulder graphic at 320x180.
- Chair: broad, friendly, and visibly separate from beard, robe, and folded wings.
- Lectern: narrow enough to preserve both hand gestures and staff clearance.
- Practical lights: simple vertical rhythm; never visual noise.
- Lower thirds and source cards: large flat regions with no generated glyphs.

## Depth grammar

Compose in this order: `background`, `set_piece`, rear `prop`, `character`, `effect`, `foreground`, `broadcast_overlay`. Captions and verified editorial graphics remain outside the actor engine's authority.

Foreground shapes must have a stated purpose. Desk face and chair front may hide legs and lower robe; the desk lip may cross the lowest hand cells only when the hand is explicitly behind it. No foreground element may hide the face, hat brim, beard expression, required gesture, source attribution, or caption.

## Motion cues

Static geometry should support motion without creating accidental tangencies:

- Preserve clear staff-parking lanes beside desks and lecterns.
- Leave entry and exit paths at frame edges.
- Keep over-shoulder graphics inside verified pointing bounds.
- Make magical particles separate effect graphs so they can be disabled for serious or reduced-motion stories.
- Treat portal, beacon, and light animation as low-amplitude secondary action; Joe remains the focal performer.
