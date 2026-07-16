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
- Every `source_cell` retains the exact accepted `.png` filename plus panel
  index; all 124 resolve to files in `canonical-worksheets`.
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
- Package loading rejects post-audit graph, count, bounds, character-package,
  runtime-profile, generated-file, profile, source, canonical, and every
  accepted-worksheet tamper.
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
  tests.wizard.test_crystail_character
```

Result after the package-provenance repair: 21/21 passed in 22.492
seconds; 0 failed, 0 skipped. The focused verification includes the Draven and
CrystAIl regression suites.

Full regression command:

```bash
python3 -m unittest discover -s tests
```

Result: 179/179 passed in 116.622 seconds; 0 failed, 0 skipped.
`git diff --check` also passed.

Production Python scope scanned 50 files with zero violations. The strict
animation-quality matrix passed 32/32 scenarios with zero issues.

## Live REST/WebSocket smoke

The live server on `127.0.0.1:8892` returned HTTP 200 for the character list,
Draven state, 92-pose list, metadata, 5,907,464-byte reference graph library,
and `clipboard_handoff` action. The registry listed `draven-holt-v1`; metadata
identified the same character; the reference library reported 16 graphs. The
character-scoped WebSocket returned `INIT:24.0:5:240:135:0:0:0.000` followed by
a 7,853-byte binary action frame. Live state confirmed action
`clipboard_handoff` selected pose `handoff_extend_clipboard`.

Final production hashes:

- Pose library: `46fac72ee95a66e812f48c9f1b76447c8d1e6a0f94905a0587443925a7447362`.
- Reference graph library: `b2cc64c15b737d111f3998bf892661a84bc35cb71d227d4cdaf8f0aa068f1daa`.
- Extraction audit: `5a75b9fee8fac5546fc20b3fea668fafeb58fdb5187e65d74ae1df39b82a94f9`.
- Character manifest: `149db3be428089ee3fb2b0ee21cba69ffb4f5470f741f547d862475e0486f431`.
