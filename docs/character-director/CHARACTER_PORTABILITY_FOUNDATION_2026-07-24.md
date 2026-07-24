# Character Portability Foundation

Date: 2026-07-24

## Scope

This checkpoint establishes the fail-closed package and registry boundary
needed before any non-Wizard character is admitted. It does not claim Serena
Quill or any other character has runtime parity.

## Implemented

- CharacterPackageV2 with:
  - supported runtime API range;
  - explicit supported renderer adapter;
  - package-owned pose library, pose manifest, animation graph, runtime
    profile, and capability manifest roles;
  - lowercase role identifiers;
  - exact SHA-256 binding for every asset;
  - containment, symlink-escape, and absolute-path rejection;
  - strict package-owned AnimationGraphV2 validation.
- Strict V1 compatibility adapter for the existing Wizard Joe package.
- Character registry with:
  - exact package SHA-256 binding;
  - identity matching;
  - duplicate and unknown-character rejection;
  - immutable returned package mapping;
  - atomic publication only after the complete registry validates.
- Package-owned graph loading:
  - explicit manifest and pose-library paths;
  - no fixed Wizard manifest comparison for a V2 package;
  - successful V2 admission invalidates parsed graph, default graph wrapper,
    parsed pose, and rendered pose caches.
- Capability derivation fails closed for V2 packages until the package-local
  capability contract is implemented. It cannot silently inject Wizard staff,
  wings, mouth, notebook, or evidence into another character.

The production registry still contains only Wizard Joe.

## Independent Review

Three review passes found and closed:

1. stale graph validation through a path-only cache;
2. rejected packages mutating the admitted graph selector;
3. accidental coupling to the audiobook schema registry;
4. Wizard-specific capability derivation for V2 packages;
5. unsupported adapter and runtime ranges being accepted;
6. absolute paths being accepted by runtime loaders;
7. stale parsed graph and pose data after package replacement;
8. externally mutable registry contents;
9. schema/runtime disagreement on relative paths;
10. an uncleared default-graph wrapper cache.

No finding was waived.

## Verification

Fresh focused result:

```text
Ran 72 tests in 36.913s
OK
```

The run covers package V1/V2 loading, asset and package tamper rejection,
runtime and adapter admission, path containment, immutable registry state,
package-owned graph loading, cache replacement, contract regressions,
capability fail-closed behavior, production animation wiring, and pose
selection.

The protected local visualizer at `127.0.0.1:8765/side-by-side` remained
running and returned HTTP 200 throughout this checkpoint.

## Remaining Before Serena Admission

1. Import Serena's immutable intake assets.
2. Produce target package-local runtime profile and capability manifest
   contracts.
3. Generalize anchor requirements and prop semantics without fabricating staff
   data.
4. Author Serena's strict AnimationGraphV2 and scoped vocabulary/mappings.
5. Render Serena through the existing transactional frame pipeline.
6. Pass the full per-character parity matrix and independent visual review.
7. Obtain explicit product approval for the exact frozen Serena candidate.
8. Add Serena's exact package hash to the production registry.
