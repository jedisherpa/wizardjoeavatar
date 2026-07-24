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

## Current Result

Serena is **intake-audited, migration pending, not production-registered**.
