# Liora Kane Production Runtime

## Runtime contract

Liora is registered as `liora-kane-v1` through the shared character package and
registry architecture. The projector consumes only transparent colored pixel
nodes from JSON. The worksheet PNGs remain preserved derivation inputs and are
never decoded by the live renderer.

The production census is exact:

- 16 identity/reference graphs from sheet 01.
- 108 full-body pose and feature graphs from sheets 02 through 09.
- 124 audited isolated silhouettes and colored-node graphs in total.
- 0 PNG or SVG runtime render assets.

Every graph records its worksheet cell, worksheet hash, bounds, node count,
graph hash, isolation method, and successful pre-animation audit. Package load
recomputes the graph hashes before the runtime profile can be constructed.

## Background isolation

Liora's pale-blue studio floor was close to the gray hoodie and cream shoes.
The accepted extraction uses a background-distance threshold of 90, retains
the largest connected subject, then removes the residual bright cyan studio
hue. This preserves the gray hoodie, cream drawstrings and shoes, teal plaid
trousers, brown hair, skin, and navy notebook while removing the sheet, floor,
and contact shadows. Per-graph gray and teal color-cell gates protect the hoodie
and plaid silhouette from accidental fragmentation. The reviewed 124-up node render is
`evidence/liora-kane/124-graph-contact-sheet.png`.

## Semantic performance

The signature vocabulary follows the accepted worksheet exactly: compassionate
listening, family-communication planning, belonging check-in, privacy boundary,
safe escalation, notebook-guided support, supportive hand offer, protective
grounding, quiet reassurance, and slow recovery. Movement remains measured,
warm, protective, and grounded.

Existing controller actions map to Liora-specific production poses:

- `explaining` -> present support plan.
- `pointing` -> family-plan page indication.
- `thinking` -> safe-escalation assessment.
- `reaction` -> belonging check-in pause.
- `celebrating` -> supportive hand offer.
- `listening` -> compassionate listening start.
- `journal_hold` -> low privacy notebook shield.
- `journal_write` -> notebook-guided support writing.
- `journal_page_turn` -> family-plan page indication.
- `containment` -> calm privacy stop palm.
- `magic_cast` -> safe escalation next-step indication.
- Movement actions (`turn_left`, `turn_right`, `crouch`, `jump`, `fall`, and
  `land`) resolve to their exact authored motion cells.

Package loading validates every semantic pose reference and recomputes the
manifest hashes for the pose library, animation graph/matrix, extraction audit,
and pixel-graph library. Registry loading then verifies the package ID against
the registry entry, so changed or mismatched lineage fails before rendering.

The shared eight-direction, locomotion, expression, speech, blink, direct-pose,
static-asset, and WebSocket channels remain available. Feature-donor graphs
stay audited but only the full-body pose graphs enter the runtime controller.

## Repeatable checks

```bash
uv run python tools/generate_voxel_persona_character.py \
  assets/reference/personas/liora-kane/generation-profile.json --check

uv run python tools/render_direct_cell_contact_sheet.py \
  liora_kane evidence/liora-kane/124-graph-contact-sheet.png

uv run python -m unittest \
  tests.wizard.test_direct_cell_character \
  tests.wizard.test_liora_kane_character -v

uv run python -m unittest discover -s tests -v
```
