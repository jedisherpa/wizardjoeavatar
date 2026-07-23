# Newsroom V2 Layer Admission

## Result

The Rust layer-admission pass is complete for every admissible v2 newsroom source.
All 27 target graphs use the full native `1672x941` coordinate frame and preserve the
source RGBA pixels without resizing, cropping, resampling, palette reduction, PNG
runtime references, or SVG runtime references.

| Source | Targets | Occupied pixels | IoU | Color fidelity | Review |
| --- | ---: | ---: | ---: | ---: | --- |
| `main_anchor_desk_v2` | 2 | 960,134 | 1.0 | 1.0 | approved |
| `standing_explainer_wall_v2` | 2 | 682,485 | 1.0 | 1.0 | approved |
| `cohost_interview_v2` | 4 | 894,223 | 1.0 | 1.0 | approved |
| `magical_breaking_field_v2` | 3 | 638,632 | 1.0 | 1.0 | approved |
| `studio_furniture_displays_v2` | 8 | 606,749 | 1.0 | 1.0 | approved |
| `broadcast_magic_overlays_v2` | 8 | 451,407 | 1.0 | 1.0 | approved |

Total occupied pixels assigned exactly once: `4,233,630`.

## Evidence per source

Every source directory under
`evidence/newsroom-visual-development-v2/layer-admission/` contains:

- one compressed palette-and-row-run pixel graph per target;
- one independent projected render per target;
- `layer-map.png`, a false-color ownership audit;
- `recomposed-render.png`, the exact sum of the target graphs;
- `transparent-overlay.png`, the numeric comparison visualization;
- `recomposed-over-source-png.png`, the required transparent graph-over-PNG review;
- `verification.json`, including all artifact hashes, metrics, and the visual finding.

The review command rehashes every artifact and independently projects all target
graphs again before it can record approval.

## Fail-closed behavior exercised

The process rejected and corrected five real specification defects:

1. The original anchor-desk rectangle claimed floor and rear-platform pixels.
2. The original explainer rectangle claimed part of the left tower and stage.
3. The original interview rectangles overlapped on 777 occupied pixels.
4. The original breaking-news lectern and platform rectangles overlapped on 10,827 pixels.
5. The original source-card rectangle left 66 crystal pixels unassigned.

Silhouette masks and exact pixel ownership replaced those broad selections. The
compiler does not use target priority to hide collisions and does not discard gaps.

## Hash bindings

- Source manifest SHA-256:
  `0bddadf7b3c7fd943d7dad82f6be04270414c3f21d4657eb9304b5d8e0793e3a`
- Target-spec package SHA-256:
  `c50c7bdb7f532d7b10dc7521c94a14489dfa3ffba82a6a1abe0fa36f65b36db8`
- Source-admission ledger SHA-256:
  `09bf54612394b0c8514c7213aea609f2b7d71bf9321ee2b2ace9714b2ce65f6a`

Each ledger entry also binds its source graph and its own serialized target spec. A
queued source spec can be refined without invalidating previously approved sources;
an approved source spec cannot change without forcing regeneration.

## Promotion boundary

Visual approval changes evidence state only. Runtime promotion is performed by the
separate `wizard-avatar-newsroom-promote` Rust command. It rehashes the approval ledger,
verification report, target graph, target render, layer map, recomposition, transparent
overlay, and graph-over-source comparison before it copies a graph. The 27 promoted
files are byte-identical to their approved evidence and remain native `1672x941`
palette-and-row-run graphs. Scaling occurs only in the runtime projector.
