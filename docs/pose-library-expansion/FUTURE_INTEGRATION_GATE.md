# Deferred Pose Integration Gate

The 30 images supplied in `Wizard Joe Poses 2.zip` and `Wizard Joe Poses Flying and Action.zip` are preserved as visual references. They are not runtime sprites and must not be loaded, traced frame-by-frame, or substituted for procedural ASCILINE output.

## Saved source material

- The 30 extracted source PNGs are stored under `evidence/pose-library-expansion/intake/`.
- `evidence/pose-library-expansion/intake/manifest.json` records the source archive hash, stable candidate ID, semantic ID, source filename, dimensions, color mode, repository path, and SHA-256 for every PNG.
- Labeled contact sheets are stored under `evidence/pose-library-expansion/intake/contact-sheets/`.
- [POSE_TRACKER.md](POSE_TRACKER.md) and the files under `items/` hold the visual analysis, proposed anchors, transition neighbors, risks, and current disposition for every candidate.

Run `cargo run --manifest-path rust/wizard_avatar_engine/Cargo.toml --bin wizard-avatar-pose-catalog` to verify all 30 source files, hashes, archive counts, and the reference-only policy. Python pose tools belong to other agents and are not part of the Rust implementation or acceptance path.

## Runtime freeze

Do not integrate another candidate while the current seam/contact repair is open. The pose archive may be inspected and documented, but production pose geometry, pose selection, transition behavior, and generated libraries remain frozen until all of these conditions are true:

1. The full deterministic Rust replay reports no horizontal body seams, vertical robe cracks, disconnected staff segments, or unexpected component fragmentation.
2. All Rust, browser-client, and ASCILINE integration tests pass from a clean invocation.
3. Regenerated evidence has a valid integrity manifest.
4. A new real-browser recording confirms the repaired character remains connected during turns and locomotion.
5. Independent verification changes the animation-quality verdict from `FAIL` to `PASS`.

## Integration order

After the freeze is lifted, integrate serially in this order:

1. **Locomotion continuity:** `WJP2-02`, `WJP2-08`, then the remaining run/walk candidates. Use them to improve readable foot contacts and airborne/passing phases before adding new action vocabulary.
2. **Grounded reactions and staff actions:** crouch, kneel, guard, block, pointing, magic thrust, celebration, and secret/shush candidates. Each must enter and exit through the existing action-channel state machine without changing the root unexpectedly.
3. **Airborne actions:** jump, fall-back, and landing candidates. Add explicit takeoff, airborne, landing, and recovery phases with contact metadata.
4. **Flight:** hover and wing-cycle candidates, followed by directional banks and glides. Flight requires its own locomotion mode, wing phase, vertical root channel, shadow response, and landing transition; it must not be modeled as a floating idle transform.

Only one candidate may hold the integration lock. Complete generation, transition, browser, and deterministic checks for that candidate before selecting the next one.

## Translation contract

For each approved reference:

1. Define canonical local-grid geometry and semantic regions for hat, face, beard, torso, robe, arms, hands, feet, staff, wings, and effects.
2. Record root, face, foot, hand, staff-hand, staff-tip, and wing anchors explicitly.
3. Define facing, locomotion/action meaning, contact state, phase neighbors, z-order, and entry/exit transitions.
4. Rebuild the procedural cell library deterministically. The PNG remains reference evidence only.
5. Test topology, anchor continuity, silhouette stability, staff connectivity, temporal variation, and restoration of the prior state.
6. Capture entry midpoint, held pose, exit midpoint, restored state, and a real-browser motion clip before marking the pose verified.

This gate keeps the source art useful without allowing the reference PNGs to become an alternate rendering system.

## Rust-only ownership

Rust owns source validation, canonicalization, color reduction, semantic region generation, anchors, contact markers, animation graphs, deterministic replay, frame capture, topology checks, ASCILINE encoding, and browser delivery. A pose is not integrated if any required generation or verification step invokes Python.
