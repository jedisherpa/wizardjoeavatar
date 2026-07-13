# CrystAIl Runtime Integration

CrystAIl is registered as `crystail-v1` beside `wizard-joe-v1`. The browser character selector reconnects to a character-scoped WebSocket and sends commands to character-scoped HTTP routes, so state, frame cadence, commands, and encoder history remain isolated per character.

The production renderer consumes deterministic direct-cell poses extracted from the canonical worksheets. The source worksheets are never decoded or displayed at runtime: `tools/generate_crystail_character.py` segments each approved panel, normalizes it to the shared 72 by 96 root space, and records its voxel lighting as ASCILINE cell colors. `wizard_avatar/crystail.py` selects those cells from semantic state and retains procedural effects and secondary-motion control.

Generated assets:

- `crystail_pose_cells.json`: 63 worksheet-quality key poses and anchors, including 22 named expressions.
- `crystail_animation_graph.json`: grounded, flight, conversational, performance, and turnaround clips plus the accepted movement profile.
- `crystail_animation_matrix.json`: 98 production behavior mappings, including 22 expressions and 13 speech shapes.
- `crystail_character_manifest.json`: identity, origin, attachments, derivation, and content hashes.
- `crystail_character_package.json`: registration package consumed by the existing loader.

Regenerate with `python3 tools/generate_crystail_character.py`. Verify deterministic output with `python3 tools/generate_crystail_character.py --check`.
