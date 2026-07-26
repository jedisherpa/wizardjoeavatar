# Liana 48-Pose Candidate Technical Review

Date: 2026-07-26

## Decision

Liana's supplemental 48-pose package passes technical review as a complete,
review-only candidate. It is not product approved and is not runtime admitted.
The production registry remains unchanged.

The candidate is available beside approved HD Wizard Joe at:

- `http://127.0.0.1:8665/`

The observer must identify the right-hand character as `Liana`, describe the
set as `48-pose motion candidate - review only`, and report both
`review_projection: true` and `runtime_admitted: false`.

## Governed Inputs And Outputs

| Asset | SHA-256 |
| --- | --- |
| Authoring brief | `9d4198ae6cc2fc5acdd16386d9dab544e499fed58cd06c9932b71b1d38c05346` |
| Supplemental tracker | `5c1776cf7c438e869ea618e6f65374deb9a38d28cd5e4c7f1ad9c61e511ddbcf` |
| Motion manifest | `9d2306c87009fb5971c5c5811ba0d2d245c64079952c516aad56bc1153cf59bf` |
| Compiled pixel-graph artifact | `79535e1b310848bf23d3c8f5db170fdfc6657865a6fa8e0f03040d80630bafee` |
| Library index | `ff6972de47681a8e3a710b880fff53ca8da205e51f01f314073db409ff4a9d19` |
| Build receipt | `ae18bbe68a6945a45aaabbc66ca4634afc0fbc32af68725997d890ff5b5042e5` |
| 48-pose contact sheet | `dbd77e60149c3fa2eca80671ced02a3ec46541db632340820b78947b9699f02e` |

The compiled artifact contains 48 independently authored RGBA pixel graphs in
eight six-pose performance groups. It is 28,725,043 bytes. No rendered PNG or
SVG is used as the runtime projection payload.

## Gate Results

| Gate | Result |
| --- | --- |
| Front identity | User authorized exact front identity to proceed; not runtime approval |
| Multiview identity | Profile, three-quarter, and rear anchors passed technical review |
| Eight six-frame groups | 48/48 independently authored technical candidates complete |
| Pixel integrity | Passed |
| Motion integrity | Technical review passed for candidate |
| Two-build determinism | Passed |
| Full sequence review | Technical review passed; product approval pending |
| Runtime admission | Fail-closed pending explicit product approval |

## Pixel And Physical QA

Every canonical frame was decoded and checked individually:

- PNG, RGBA, 1254 by 1254 pixels.
- Alpha silhouette bottom is exactly baseline `1185`.
- Minimum observed left margin is `130`.
- Minimum observed top margin is `69`.
- Minimum observed right margin is `129`.
- All fully transparent pixels have zero RGB.
- All 48 PNG file hashes are unique.
- All 48 raw RGBA hashes are unique.
- Every indexed pose decodes byte-for-byte to its governed canonical frame.
- Every pose and sequence remains `runtime_admitted: false`.

The ordered contact sheet was inspected for identity, outfit, silhouette,
facing, action readability, hair continuity, complete hands and feet, and
absence of props or crop damage. Nine observer captures provide representative
Joe side-by-side playback evidence across the full looping sequence.

## Determinism

Two clean output directories were built independently from the frozen motion
manifest. Both produced:

- Artifact SHA-256:
  `79535e1b310848bf23d3c8f5db170fdfc6657865a6fa8e0f03040d80630bafee`
- Library index SHA-256:
  `ff6972de47681a8e3a710b880fff53ca8da205e51f01f314073db409ff4a9d19`

Temporary build receipts differ only because each receipt truthfully records
its distinct output directory. Governed payload and index bytes are identical.

## Test Evidence

Focused verification covers:

- Real Liana package topology, exact hashes, alpha policy, margins, baseline,
  unique graphs, decoded pixels, and fail-closed registry behavior.
- Two-clean-build determinism.
- Liana multiview identity.
- Generic supplemental compiler behavior and rejection cases.
- HD pose artifact and cross-character graph portability.
- Character observer escaping and fail-closed health semantics.

## Remaining Product Gate

Product approval must cite the exact motion manifest, artifact, library index,
and evidence-manifest hashes. Until that happens:

- `approved_pose_count` remains `0`.
- `runtime_admitted` remains `false`.
- Liana may appear only in the local review observer.
- The production character registry must not include Liana.
