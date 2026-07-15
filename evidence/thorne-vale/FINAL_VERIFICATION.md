# Thorne Vale Runtime Verification

Verification date: 2026-07-15

Branch: `codex/persona-thorne-vale`

Base commit: `ae15f89`. This verification covers the completed, uncommitted
production worktree changes requested for review; this pass did not commit or
push.

## Exact 124-cell extraction gate

- Exact total: 124 transparent colored-node graphs.
- Identity/reference: 16 graphs from accepted identity revision 3 only.
- Pose/feature: 108 graphs from sheets 02–09.
- Motion: 16 graphs from accepted grounded-motion revision 2 only.
- Complete category split: 16 identity, 8 turnaround, 8 neutral, 24
  expression, 16 viseme/blink, 16 hand/prop, 16 motion, 16 signature, and 4
  interaction.
- Runtime image asset list: empty.
- Runtime data format: JSON colored pixel nodes; missing cells are transparent.
- No Thorne PNG or SVG exists in `wizard_avatar/definitions`.

Package loading recomputes all 124 graph hashes and validates their node counts,
bounds, RGB values, transparent-node encoding, and audit coverage. It also
revalidates the source-reference hash, canonical-reference hash, generated
asset hashes, approved worksheet hashes, and each audit item's worksheet hash
before the runtime profile is loaded.

## Human visual contact audit

Reviewed evidence:

`evidence/thorne-vale/THORNE_124_DIRECT_NODE_CONTACT_SHEET.png`

- Dimensions: 2560 by 1760.
- SHA-256:
  `a202f1880f3ae7f6228a761f19cfdaa85823645ac6320bb0c78eff2c32733a3b`.
- All 124 direct-node silhouettes were inspected on a checkerboard.
- No detached cyan/blue worksheet-background islands were present.
- Blue-gray pixels highlighted by an initial color heuristic were visually
  confirmed as localized antialiasing on the crown, facial edges, clothing, or
  gray sword—not background components.
- Crowns, green eyes, mustaches, gold jackets, hands, boots, parchment, and safe
  sword silhouettes remain intact across the set.

This contact PNG is review evidence only. It is not referenced by the package,
registry, pose controller, projector, or WebSocket runtime.

## Character and motion gate

- Identity lock: tall gold crenellated crown, gold knee-length jacket,
  rectangular green eyes, thick dark mustache, gray sword, and tan policy
  parchment.
- Cigar and smoke vocabulary are absent from the production package.
- The signature library includes anticipation, action, follow-through, and
  recovery for decision rights, tradeoff comparison, risk review, and
  incentive analysis.
- Semantic action mappings resolve only to full-body graphs. Hand/prop feature
  graphs remain audited donor data and cannot accidentally replace the body.
- Runtime motion is restrained, strategic, and authoritative.

## Live runtime gate

The focused suite exercises the actual character-scoped architecture:

- registry discovery for `thorne-vale-v1`;
- REST character listing, command routing, and static extraction-audit route;
- WebSocket acceptance, INIT metadata, subscription, and encoded frame output;
- movement, expression, speech, direct pose, and all Thorne semantic actions;
- forced `PIL.Image.open` failure while a complete runtime frame still renders.

The live projector paints the JSON cells directly into the ASCILINE canvas. It
does not decode any worksheet or contact-sheet image.

## Determinism and tests

Generator check:

```bash
uv run python tools/generate_voxel_persona_character.py \
  assets/reference/personas/thorne-vale/generation-profile.json --check
```

Result: `Thorne Vale generated assets are deterministic`.

Focused command:

```bash
uv run python -m unittest \
  tests.wizard.test_direct_cell_character \
  tests.wizard.test_thorne_vale_character -v
```

Result: 17 passed in 18.732 seconds; 0 failed, 0 skipped.

Full command:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 178 passed in 111.438 seconds; 0 failed, 0 skipped.

Final `git diff --check`: passed with no whitespace errors.
