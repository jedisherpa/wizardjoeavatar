# Orion Vale Runtime Verification

Verification date: 2026-07-15

Branch: `codex/persona-orion-vale`

Publication: this closure pass is committed and pushed on
`codex/persona-orion-vale`. This statement supersedes the earlier provisional
note that described the implementation as an uncommitted worktree.

## Extraction gate

- Exact audited graph count: 124.
- Identity/reference graphs from sheet 01: 16.
- The identity source is the audited 4-by-4 revision-2 sheet; revision 1 was
  rejected because its nonuniform callout layout produced incomplete equal-cell
  slices.
- Pose and feature graphs from sheets 02–09: 108.
- Category counts: 8 turnaround, 8 neutral, 24 expression, 16 viseme/blink,
  16 hand/prop, 16 motion, 16 signature, and 4 interaction.
- Runtime format: transparent colored pixel nodes in JSON. Missing nodes are
  transparent; no PNG or SVG is a runtime render asset.
- `orion_vale_extraction_audit.json` records source worksheet hashes, source
  cells, isolation method, bounds, node counts, and graph hashes.
- Package loading recomputes every one of the 124 graph hashes before the
  animation profile and controller are constructed.
- Package loading also recomputes the character-package, runtime-profile,
  original-reference, canonical-reference, generation-profile, all 10 accepted
  worksheet-revision, pose-library, animation-graph, animation-matrix,
  extraction-audit, and reference-graph library hashes. The accepted worksheet
  filenames and per-item worksheet hashes must exactly match the extraction
  audit.
- The retained human-review render is
  `evidence/orion-vale/124-graph-contact-sheet.png` (SHA-256
  `c17b74c5b8777c0cae6ef85bc2d449b01756276e6a817a44d4b96c52aa55881f`).
  It is evidence only; the runtime continues to consume transparent colored
  JSON nodes rather than PNG or SVG render assets.

The approved revision-2 neutral, expression, speech/blink, and ground-motion
sheets are used. Expression revision-2 panel 23 is blank, so its corresponding
reviewed revision-1 cell is used as the single explicit fallback. This fallback
is named and hashed in the audit.

## Runtime gate

- Orion is registered as `orion-vale-v1` through the shared character registry.
- Character-scoped state, commands, poses, WebSocket streaming, and static JSON
  assets use the shared server architecture.
- The ASCILINE projector reads direct cells and paints square colored nodes into
  the framebuffer each frame.
- Seeded simulation reaches the authored revision-2 blink graph.
- Speech and blink overlays preserve the active locomotion body graph.
- Turn, crouch, jump, fall, land, listen, journal hold, journal write, and page
  turn are semantically addressable.
- Hand/prop feature graphs are audited donors and are excluded from the
  pose-capable controller list; full-body interaction graphs remain addressable.
- Runtime rendering succeeds while `PIL.Image.open` is forced to fail, proving
  the live path does not decode worksheet PNGs.

## Determinism

Command:

```bash
uv run python tools/generate_voxel_persona_character.py \
  assets/reference/personas/orion-vale/generation-profile.json --check
```

Result: `Orion Vale generated assets are deterministic`.

## Tests

Focused command:

```bash
uv run python -m unittest \
  tests.wizard.test_direct_cell_character \
  tests.wizard.test_orion_vale_character -v
```

Result after the provenance closure: 24 tests passed in 28.209 seconds,
0 failed, 0 skipped. This includes forced `PIL.Image.open` failure while Orion
renders successfully.

Full command:

```bash
uv run python -m unittest discover -s tests -v
```

Result after the provenance closure: 185 tests passed in 124.637 seconds,
0 failed, 0 skipped. The run
includes Wizard Joe, CrystAIl, codec, transport, controller, stream, browser
contract, projection, locomotion, and Orion regression coverage.

## Destructive provenance tests

- Byte tampering is rejected for the source reference and canonical reference.
- Byte tampering is rejected independently for every accepted worksheet file,
  including both the approved expression-v2 sheet and the single explicitly
  retained expression-v1 fallback sheet.
- Byte tampering is rejected for the generation profile, character package,
  runtime profile, pose library, animation graph, animation matrix, extraction
  audit, and 16-graph identity reference library.
- Node tampering is rejected independently for each of the 16 reference graphs
  and each of the 108 pose/feature graphs by the validator used during package
  loading.
- Audit node counts, nonempty graphs, bounds, graph hashes, accepted worksheet
  revisions, and per-item worksheet hashes are all fail-closed.

## Live smoke verification

A local production server registered `orion-vale-v1` through
`GET /api/avatar/characters`, returned its character-scoped state with HTTP
200, and accepted `ws://127.0.0.1:18766/ws/avatar/orion-vale-v1`. The socket
returned `INIT:24.0:5:160:100:0:0:0.000` followed by a 10,628-byte binary
projected frame.

## Known reviewed fallback

Revision-2 expression panel 23 contains no subject pixels. The production
profile uses the corresponding revision-1 expression cell rather than
fabricating a silhouette. No other v1 fallback is used in the revision-2
neutral, expression, speech/blink, or ground-motion groups.
