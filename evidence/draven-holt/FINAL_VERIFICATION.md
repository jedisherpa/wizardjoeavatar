# Draven Holt Runtime Verification

Verification date: 2026-07-15

Branch: `codex/persona-draven-holt`

## Exact extraction and graph gate

- 124/124 accepted cells serialized and audited: 16 identity/reference, 8
  turnaround, 8 neutral, 24 expression, 16 viseme/blink, 16 hand/prop, 16
  motion, 16 signature, and 4 interaction.
- 124 unique graph IDs and 124 unique graph hashes; every graph is nonempty,
  uses integer three-channel RGB nodes, and stays inside the 72-by-96 safe
  canvas.
- Exactly 92 full-body production graphs are controller-reachable. Exactly 16
  hand/prop feature graphs and all 16 identity references remain audit-only.
- Original, canonical, generation profile, and nine approved worksheet hashes
  are manifest-locked. Rejected candidates do not enter runtime lineage.
- Studio background, sheet boundaries, floor, cast/contact shadows, and cyan
  edge fringe are absent. Draven's full identity, green eyes, orange tie,
  clipboard, abstract checklist, silver clip, and orange pencil remain intact.
- Cigar, smoke, tobacco, readable text, foreign props, and other persona
  vocabulary are absent.
- Clipboard and pencil anchors occur only on the profile-declared graphs and
  resolve to occupied colored nodes.

## Human-readable visual audit

All 124 graphs were inspected in both retained contact sheets for clipping,
background remnants, identity drift, prop continuity, scale, baseline, limbs,
turn direction, airborne margins, and action readability.

- `124-isolated-transparent-graphs.png` — transparent isolated graphs, SHA-256
  `14b6e142913b17f11e4e6aaf83474ba64c22d9e40c198bfd58b5867baa0deec5`.
- `124-projected-canvas-graphs.png` — colored nodes projected onto a dark
  visualizer-style canvas, SHA-256
  `a0e631d8c7f21549675130b66fbfaa9de1e129504b132c9301ba4a06cb6ebf29`.
- `CONTACT_SHEET_HASHES.json` preserves the exact 124-entry order and both
  evidence hashes.

These PNG files are review evidence only. Live rendering uses JSON nodes.

## Runtime and tamper gates

- Registry, static assets, REST state/poses/metadata/actions, and
  character-scoped WebSocket streaming are implemented.
- Assign owner, deadline emphasis, resource allocation, blocker escalation,
  clipboard handoff, locomotion, expressions, speech, and blink channels are
  reachable through Draven's runtime profile.
- Package loading rejects post-audit graph, count, bounds, generated-file,
  profile, source, canonical, and worksheet tampering.
- Runtime rendering succeeds while `PIL.Image.open` is forced to fail.

## Determinism and automated tests

```bash
python3 tools/generate_voxel_persona_character.py \
  assets/reference/personas/draven-holt/generation-profile.json --check
```

Result: `Draven Holt generated assets are deterministic`.

Focused command:

```bash
python3 -m unittest \
  tests.wizard.test_draven_holt_character \
  tests.wizard.test_direct_cell_character -v
```

Result: 17/17 passed in 24.131 seconds; 0 failed, 0 skipped.

Full regression command:

```bash
python3 -m unittest discover -s tests
```

Result: 178/178 passed in 176.178 seconds; 0 failed, 0 skipped.
`git diff --check` also passed.

## Live REST/WebSocket smoke

The live server on `127.0.0.1:8892` returned HTTP 200 for the character list,
Draven state, 92-pose list, metadata, 5,907,464-byte reference graph library,
and `clipboard_handoff` action. The registry listed `draven-holt-v1`; metadata
identified the same character; the reference library reported 16 graphs. The
character-scoped WebSocket returned `INIT:24.0:5:240:135:0:0:0.000` followed by
a 7,853-byte binary action frame. Live state confirmed action
`clipboard_handoff` selected pose `handoff_extend_clipboard`.

Final production hashes:

- Pose library: `51b90b154ed2657deb00f8f163b7a7fc8e1cd90d28068c5b6e3f68269220427b`.
- Reference graph library: `d7543d6a725c7daa5e5f2d2aa170f64b6c40d6d086e1ce1baffce60f3f1cc1a3`.
- Extraction audit: `efdf7d56185e7297cf3b1c1eb3b7054f001c51e9c314326f6fb4789326ceba09`.
