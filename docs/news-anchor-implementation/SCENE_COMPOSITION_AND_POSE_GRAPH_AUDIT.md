# Scene Composition And Pose-Graph Audit

Updated: 2026-07-18

This document defines the Rust-owned scene boundary for Wizard Joe. It keeps the approved character rendering intact while making newsroom environments, props, characters, effects, foreground occlusion, and broadcast graphics independently composable.

## Runtime Asset Rule

Runtime scenes and actors are colored cell graphs. PNG, JPEG, SVG, CSS artwork, and source-sheet pixels are not runtime render assets.

Source images may be retained as evidence and visual direction. Admission into the engine requires:

1. remove the sheet and cell background;
2. isolate one silhouette or scene element;
3. quantize it to the governed palette and canonical cell grid;
4. encode only opaque colored cells as deterministic horizontal runs;
5. retain transparency by omitting cells, never by painting white around the subject;
6. hash and audit the graph before it can be selected by animation or scene composition;
7. let the Rust projector paint the graph into the final canvas.

## Scene Categories

`scene.rs` defines a closed, cinematic back-to-front order:

| Category | Responsibility | Examples |
|---|---|---|
| `background` | Distant environment that never occludes the set | skyline, wall, rear display field |
| `set_piece` | Structural studio geometry | platform, rear desk shell, explainer wall |
| `prop` | Movable story and performance objects | chair, lectern, source card, microphone |
| `character` | Actor shadow, body graph, facial and gesture details | Wizard Joe, cohost, guest |
| `effect` | Time-varying nonphysical imagery | magic, alert pulse, chart reveal |
| `foreground` | Intentional occluders in front of actors | desk fascia, near monitor, practical light |
| `broadcast_overlay` | Screen-space editorial graphics | lower third, locator, headline, captions |

Every `SceneElement` has a stable lowercase ID, category, local order, signed origin, local dimensions, visibility flag, and transparent horizontal cell runs. Input order cannot alter the frame: composition sorts by category, local order, and ID. Unknown serialized fields fail closed, preventing a hidden `png`, `svg`, or image-path shortcut.

The live renderer now submits the existing contact shadow, body, and performance-detail canvases as three ordered `character` elements. A parity test compares the categorized result byte-for-byte with the previous approved direct painter.

## Shot And Blocking Model

Scene packages should define reusable camera profiles rather than duplicate flattened frames:

- establishing wide;
- anchor medium;
- close-up and emotional close-up;
- over-shoulder graphic;
- cohost or guest two-shot;
- profile and three-quarter side;
- high and low angle;
- push-in start and end marks;
- insert and cutaway framing.

Blocking metadata belongs with characters and props: entrance mark, anchor mark, explainer mark, eyeline target, planted contact, staff clearance, desk occlusion line, and safe areas for captions and lower thirds. Acting intensity changes pose selection and timing, not the identity or camera-safe placement of the scene elements.

## Current Pose Census

The repository currently proves the following counts:

| Inventory | Count | Meaning |
|---|---:|---|
| Archived PNG records | 159 | Every source entry across the five archives is hash-inventoried without deduplication |
| Canonical style references | 1 | `WJSRC-0011` governs visual direction and is not misclassified as a pose candidate |
| Reviewed pose-candidate records | 158 | Every candidate received a terminal one-at-a-time disposition |
| Verified pose graphs | 120 | Exact isolated silhouettes promoted to graph-native runtime assets |
| Excluded non-poses | 38 | Boards, style references, or other non-pose records with exclusion evidence |
| Unique semantic pose IDs | 110 | Primary identities used by motion controls and clips |
| Explicit duplicate source graphs | 10 | Retained and independently addressable; never used to inflate semantic coverage |
| Canonical graph frame | 1536 x 1536 | Transparent edge padding only; source pixels are not resampled |
| Minimum visual alignment | 95% | Required silhouette and foreground-color fidelity |
| Current verified alignment | 100% | Every promoted graph has 1.0 silhouette IoU and 1.0 foreground-color fidelity |

`pose_graph_runtime.rs` embeds the promotion manifest, validates its content hash, indexes all 120 source identities and 110 primary semantic identities, and rehashes every compressed graph before release. `pose_graph_audit.rs` retains the old 89-item cell-library census only as a legacy compatibility audit; its former 108-target gate has been superseded by the authoritative 159-record source ledger, 158-record candidate admission ledger, and 120-graph promotion manifest.

Every unique semantic pose is now owned by a Rust motion clip or by the directional locomotion controller. Every verified source graph, including explicit duplicates, is addressable through its `WJSRC-*` runtime identity and the source-graph API.

## Runtime Frame Verification

The graph projector is verified from both ends. A live browser audit selects all 120 source identities, confirms the returned runtime identity and exact foreground-pixel count, and retains one nonempty frame for each source. A deterministic Rust evidence binary then renders every authored clip and four transformed walking scenarios frame by frame.

The current evidence census is 18 clips, four locomotion scenarios, and 1,491 complete frames. Every clip and scenario passes. Contact sheets cover every sequence, while the full frame archive preserves each individual PNG for breakup review. The newsroom audit additionally verifies that exact native desk and lectern foreground graphs paint after the actor, preserving intentional occlusion without flattening the scene into an image asset.

## Production Admission Checklist

An environment or actor graph is ready for runtime only when:

- its source and compiled graph hashes are recorded;
- its category and local order are explicit;
- transparency, dimensions, and bounds pass;
- repeated runs do not overlap;
- foreground occlusion is intentional at every supported camera profile;
- the actor remains readable at `320 x 180`;
- transition frames preserve contacts, silhouette continuity, and staff/wing attachments;
- deterministic replay produces identical frame hashes;
- generated references remain outside the runtime asset path.
