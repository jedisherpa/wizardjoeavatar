# Aurelia Finch Runtime Integration

Status: production direct-cell runtime implemented and verified on 2026-07-15.

## Runtime contract

- Character ID: `aurelia-finch-v1`.
- Accepted worksheet count: exactly 124 cells: 16 identity reference graphs and 108 runtime pose/feature graphs.
- Runtime format: transparent colored pixel nodes in JSON. PNG worksheets and evidence images are provenance/audit inputs only and are never decoded by the runtime renderer.
- Canonical canvas: 72 by 96, root `[36, 91]`, safe occupied bounds `x=4..67`, `y=4..91`.
- Background isolation explicitly rejects the soft-blue worksheet studio, lower-panel neutral floor/contact shadows, and post-resize blue fringe pixels.
- The runtime profile maps only Aurelia worksheet semantics. No Orion/inquiry or another persona's action IDs remain.

## Persona semantic actions

The character-scoped action API supports partnership pitch, stakeholder translation, proof presentation, public promise check, leadership briefing, leadership recovery, and diplomatic recovery. These resolve only to Aurelia's accepted signature-action panels.

## Integration surfaces

- Registry: `wizard_avatar/definitions/character_registry.json`.
- Package: `wizard_avatar/definitions/aurelia_finch_character_package.json`.
- REST: `/api/avatar/characters`, `/api/avatar/aurelia-finch-v1/state`, `/api/avatar/aurelia-finch-v1/poses`, and `/api/avatar/aurelia-finch-v1/{command_type}`.
- Static production assets: `/avatar/characters/aurelia-finch-v1/{asset_name}`.
- WebSocket: `/ws/avatar/aurelia-finch-v1`.

The manifest binds source and canonical reference hashes, every accepted worksheet revision, all generated package assets, the exact extraction count, and the absence of flattened runtime art. Package loading revalidates lineage, generated hashes, per-graph hashes/counts/bounds, integer coordinates, safe bounds, and RGB channel ranges before animation mapping.
