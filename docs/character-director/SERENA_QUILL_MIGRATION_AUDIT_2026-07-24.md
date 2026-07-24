# Serena Quill Migration Audit

Date: 2026-07-24

## Decision

Serena Quill is the first non-Wizard architecture-parity candidate. Her
authored pixel graphs and provenance are suitable migration inputs. Her former
runtime is not suitable for direct integration because it bypasses the current
strict animation graph, governed performance, and transactional presentation
pipeline.

Serena is not registered in the production character registry until every gate
in this document passes.

## Frozen Source

- Repository worktree:
  `/Users/paul/Documents/WizardJoeAsci/persona-worktrees/serena-quill`
- Source commit:
  `196c2389c71ca5276eed594d822d29b76310dd2f`
- Historical package SHA-256:
  `1973d1c7a726c0daf23ab56b22491c74b704c4aa6764546df93dbbfe20598de9`

The frozen source contains the package, pose cells, animation graph, runtime
profile, animation matrix, manifest, extraction audit, pixel-graph library,
generation code, tests, reference assets, and historical acceptance evidence.

## Asset Census

| Item | Count |
| --- | ---: |
| Runtime poses | 108 |
| Full-body poses | 92 |
| Feature-only poses | 16 |
| Pose cells | 275,233 |
| Reference graphs | 16 |
| Reference graph nodes | 37,625 |
| Audited pose and reference items | 124 |
| Audited nodes | 312,858 |
| Exact historical projection matches | 124 / 124 |
| Legacy clips | 10 |
| Legacy clip samples | 45 |
| Legacy graph nodes | 0 |
| Legacy graph transitions | 0 |
| Animation matrix rows | 87 |

Core source hashes:

| Artifact | SHA-256 |
| --- | --- |
| Runtime profile | `43e06748c51f1d3b9896ce396329146e751efe13e0a737542ca982c8491f504e` |
| Pose library | `8aaa6fc0ba3fb0a2a92a0d3ba5f95101b0ea06deba625b9e3f17ad36368c22e4` |
| Animation graph | `25cd9eb67320d31182a58b0bec0e6b9e037e9ce948d4b00c78096fd2c8ace23e` |
| Animation matrix | `bb9731d964e936a448f8348981bf89fb86df48cf6bf65e685871826568ea8263` |
| Extraction audit | `577eb6f58dd03ce95a08243cbd40dc5f1f1309cc532e1ae5c433f5adc3bd790f` |
| Pixel graphs | `0f6da5165d029632edba67a12791ca545a5d74d3c81b2c1a98922c7e2f0232fa` |
| Manifest | `2ed81123cce1ac7a6cc2a1c2f22de550f5edb8cd68f1284affec2469d035003a` |

These values identify intake material. They do not constitute target-runtime
acceptance.

## Anchor Audit

All 108 pose records use the same 72 by 96 authored grid and root anchor
`[36, 91]`. Every record is non-empty, has unique cell coordinates, and
contains the eight core anchors required by Serena's package:

- `root`
- `mouth`
- `left_eye`
- `right_eye`
- `left_foot`
- `right_foot`
- `left_hand`
- `right_hand`

The optional `orb` anchor appears in 45 records: 35 full-body graphs and 10
feature graphs. Staff anchors are absent and are not added by migration.

The 92 full-body graphs are structurally suitable for whole-pose rendering.
The 16 feature graphs are audit-only until they receive explicit base-pose
ownership, semantic regions, masks, and z-order. Wings, halo, and orb remain
baked whole-pose geometry in this checkpoint; the migration does not pretend
that they are independently composable overlays.

Contact evidence is intentionally conservative. Only these exact source states
have contact semantics admitted from their names:

- `walk_contact_left`: grounded, left foot planted
- `run_contact_left`: grounded, left foot planted
- `jump_airborne`: airborne, no planted anchor

Other locomotion, turn, crouch, landing, and recovery poses remain diagnostic
until their contacts and phases are authored and reviewed.

## Compatibility Findings

1. The legacy graph is not AnimationGraphV2. It lacks classifications, nodes,
   transitions, contacts, markers, channel ownership, recipes, and fallbacks.
2. The legacy `DirectCellRuntimeProfile` selects pose cells outside the strict
   graph. That bypass is forbidden in the Character Director.
3. The current target graph loader still cross-checks against Wizard Joe's
   fixed manifest. It must accept a package-owned pose manifest and catalog.
4. Current capability derivation assumes Wizard expressions, mouth cells,
   staff, wings, notebook permission prop, and evidence paths.
5. Serena has orb and wing semantics but no truthful staff contract. Missing
   staff anchors must not be fabricated.
6. The archived 32-scenario transition evidence includes Wizard Joe states and
   cannot be reused as Serena acceptance evidence.
7. The current minimal second-character test stops before a real hub boot and
   is not parity proof.

## Preserved Inputs

The following source material may remain byte-for-byte:

- original and canonical reference imagery;
- accepted worksheets;
- identity lock and uncertainty log;
- extraction and pixel-graph audits;
- matching contact sheets;
- the 108-pose cell library as immutable intake.

The runtime package, pose-source manifest, graph, runtime profile, capability
manifest, vocabulary, mappings, calibration, tests, and acceptance evidence
must be migrated or regenerated against the current architecture.

## Rejected Shortcuts

- Do not copy the legacy frame source or server.
- Do not retain direct-cell selection as a graph bypass.
- Do not add Serena vocabulary to global Wizard constants.
- Do not fake staff anchors or staff capabilities.
- Do not equate extracted assets with admitted runtime capabilities.
- Do not hash workstation PNGs during runtime startup.
- Do not register Serena before real hub, server, connector, and browser proof.

## Admission Sequence

1. Copy immutable intake assets and verify every declared source hash.
2. Produce a CharacterPackageV2 with hash-bound role assets.
3. Produce a package-owned pose manifest and strict pose catalog.
4. Author a complete AnimationGraphV2 with interruption and fallback behavior.
5. Produce package-scoped vocabulary, mapping, capabilities, permissions, and
   presentation profile.
6. Render through the existing snapshot, candidate, and commit pipeline.
7. Pass deterministic graph, contact, interruption, accessibility, and framing
   tests.
8. Pass governed score and media admission, including package mismatch denial.
9. Boot a Serena-pinned hub, server, WebSocket stream, and existing connector.
10. Capture fresh desktop and mobile evidence for independent animation and
    technical review.
11. Obtain explicit product approval for the exact frozen Serena candidate.
12. Add the exact package hash to the production registry.

## Migration Candidate

The first deterministic target package now includes:

- the immutable 108-pose source cell library;
- a package-owned pose manifest;
- a strict AnimationGraphV2 migration graph;
- a character runtime profile with Serena-owned facings, actions, expressions,
  cycles, speech, blinks, anchors, presentation scale, and orb semantics;
- a capability manifest and frozen intake manifest;
- a CharacterPackageV2 binding all ten role assets by SHA-256.

The generator is
`tools/migrate_serena_quill_character.py`. Its `--check` mode is read-only and
verifies byte-for-byte reproducibility. All copied JSON and reference-art
inputs are pinned to the frozen source hashes, and unexpected or missing input
files fail generation.

Current generated census:

| State | Count |
| --- | ---: |
| Total pose graphs | 108 |
| Full-body whole-pose graphs | 92 |
| Feature graphs held diagnostic-only | 16 |
| Graph-admitted states | 79 |
| Diagnostic-only states | 29 |
| Evidence-backed admitted motion states | 3 |

The graph-admitted count is not a parity claim. This checkpoint uses
single-sample whole-pose nodes and coherent cuts to prove package ownership,
strict loading, and truthful capability separation. Full gait cycles, authored
turns, interruption choreography, feature composition, semantic performance,
connector proof, and visual acceptance remain later gates.

The runtime profile exposes only poses that occur in graph clips owned by
runtime nodes; orphan clips are not selectable.
Incomplete walk/run cycles and unreviewed turns, crouch, fall, and landing
states remain outside runtime mappings. Unreviewed static poses use no planted
contact; only the two exact left-contact states claim a support foot, while the
airborne state claims none.

V2 graph and pose-library parsing is bound to package-admitted SHA-256 values,
including after cache invalidation. V2 selection fails closed on graph errors;
diagnostic pose overrides are denied, and the direct-pose fallback remains
available only to legacy V1 packages.
Registry graph publication uses one immutable mapping replacement rather than
an observable clear-and-update sequence.

## Verification

The migration-focused suite passes 66 tests covering the runtime profile,
CharacterPackageV2, registry isolation, graph portability, capability
portability, deterministic generation, frozen-source rejection, intake census,
anchor contracts, admission policy, package loading, post-admission tamper
rejection, strict-selection behavior, and Wizard/Serena semantic separation.

The full Wizard suite ran 794 tests. It reported three failures and one error:

- two existing head/eye planted-contact assertions;
- one existing cast-overlay marker assertion;
- one existing pose-expansion count guard expecting 186 poses while the
  baseline contains 193.

Each failure reproduces unchanged in a detached worktree at pre-migration
commit `2a4feb2c`. They are recorded baseline debt, not Serena migration
regressions. The Serena checkpoint does not alter those tests or claim they
pass.

## Current Result

Serena is **intake-audited, strict migration candidate generated, not
production-registered**.
