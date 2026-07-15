# Elara Voss Runtime Verification

Verification date: 2026-07-15

Branch: `codex/persona-elara-voss`

Verification covers the uncommitted production worktree. This pass did not
commit or push.

## Extraction and identity gate

- Exact audited graph count: 124.
- Identity/reference graphs: 16, from accepted identity worksheet revision 3.
- Pose/feature graphs: 108 (8 turnaround, 8 neutral, 24 expression,
  16 viseme/blink, 16 hand/prop, 16 motion, 16 signature, 4 interaction).
- Ground motion uses accepted revision 2; all remaining production sheets use
  the explicitly selected revision recorded in the manifest.
- Original and canonical references remain byte-preserved and hash-locked.
- Every graph is nonempty, detailed, unique, inside the 72-by-96 safe canvas,
  and recorded as transparent colored pixel nodes rather than image assets.
- Direct-node contact renders of all 16 identity graphs and all 108 pose/feature
  graphs were visually reviewed at canonical resolution. All silhouettes are
  complete; no identity panel is a chopped callout or non-grid fragment.
- The retained human-review contact sheet is
  `evidence/elara-voss/124-graph-contact-sheet.png` (SHA-256
  `22685bad5b85577be661ec2c7bfebb5b191de1df69cc887154cc2f040b6f05c3`).
  It is evidence only; the runtime continues to load colored JSON nodes rather
  than PNG or SVG render assets.
- Microphone anchors occur only on the graphs declared by the generation
  profile; other poses do not receive a fabricated prop anchor.
- Package load rejects post-audit graph changes, node-count/bounds changes,
  generated-file changes, source changes, and accepted-worksheet changes.

## Runtime gate

- Elara is registered as `elara-voss-v1` through the shared registry.
- Curriculum, sequencing, reflection, microphone, correction, containment,
  listening, turn, crouch, jump, fall, and landing graphs are runtime reachable.
- Full-body interaction poses are addressable; close feature graphs are audit
  and donor data and are excluded from the controller’s body-pose list.
- Blink and speech composition preserve the active walking/action body graph.
- Runtime rendering succeeds when `PIL.Image.open` is forced to fail, proving
  that the live path does not decode PNG or SVG assets.

## Determinism and automated tests

Determinism command:

```bash
python3 tools/generate_voxel_persona_character.py \
  assets/reference/personas/elara-voss/generation-profile.json --check
```

Result: `Elara Voss generated assets are deterministic`.

Focused command:

```bash
python3 -m unittest \
  tests.wizard.test_direct_cell_character \
  tests.wizard.test_elara_voss_character -v
```

Result: 18 passed, 0 failed, 0 skipped.

Full command:

```bash
python3 -m unittest discover -s tests -v
```

Result: 179 passed in 177.688 seconds, 0 failed, 0 skipped. This includes the
Wizard Joe, CrystAIl, transport, controller, projection, stream, browser,
rendering, and Elara regression coverage.

## Live REST/WebSocket smoke

The live server on `127.0.0.1:8878` returned HTTP 200 for the character list,
Elara state, poses, metadata, and pixel-graph library. The registry response
listed `elara-voss-v1`. The character-scoped WebSocket returned
`INIT:24.0:5:240:135:0:0:0.000` followed by a 10,649-byte binary frame.
