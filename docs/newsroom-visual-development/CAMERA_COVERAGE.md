# Camera Coverage Board

The boards use character imagery only to describe composition. Runtime shots must project the approved Rust actor graph into these profiles.

## Board A: core coverage

| Panel | Shot | Profile | Composition intent | Occlusion intent |
| --- | --- | --- | --- | --- |
| A1 top-left | Establishing wide | `anchor-wide` | Full set identity, clear desk and actor scale, room for an opening title. | Desk face may hide legs and lower robe. |
| A2 top-center | Anchor medium | `desk-medium` | Face, hat, beard, one hand, and staff remain readable. | Desk face hides lower body; desk lip stays below active hand. |
| A3 top-right | Close-up | `close-up` | Prioritize eyes, mouth, beard, and hat brim. | Staff and outer wings crop before face or expression. |
| A4 bottom-left | Over-shoulder graphic | `explainer-wide` | Joe's shoulder creates depth while the blank display remains the target. | Rear display stays behind actor; no foreground crosses pointing hand. |
| A5 bottom-right | Two-shot | `discussion-two-shot` | Balanced eyelines and conversational negative space. | Desk hides lower bodies; hands and faces remain above it. |

## Board B: dynamic coverage and inserts

| Panel | Shot | Profile | Composition intent | Occlusion intent |
| --- | --- | --- | --- | --- |
| B1 top-left | Side/profile | `explainer-wide` | Clean profile, staff vertical, blank wall in gaze direction. | Display stays rear; no set edge cuts face or staff hand. |
| B2 top-center | High angle | `anchor-wide-high` | Modest overhead geography, not comic diminishment. | Circular desk masks lower robe; hat remains fully separated. |
| B3 top-right | Low angle | `field-low` | Friendly authority for a field or breaking-news beat. | Lectern masks lower torso only; face and staff tip remain clear. |
| B4 bottom-left | Dolly start | `anchor-wide` | Establish axis, set, and body before emphasis. | Same desk mask as B5. |
| B5 bottom-center | Dolly end | `desk-medium` | Land on face and delivery without restarting actor state. | Crop wings/staff perimeter before face or required gesture. |
| B6 bottom-right | Cutaway inserts | `insert-triptych` | Staff hand, blank source card, and magic beacon for editorial punctuation. | Each insert is isolated; no overlay is baked into actor pixels. |

## Camera rules

- Deterministic shot selection only; no browser-random camera cuts.
- Normal projection changes use a 180-500 ms bounded transition.
- The dolly pair preserves axis, eyeline, semantic actor state, mouth generation, and caption generation.
- High and low angles are specialty coverage, not default delivery.
- Cutaways must return to the same actor state and timeline position.
- At mobile widths, collapse multi-actor layouts to the active speaker and preserve captions outside the face safe zone.
