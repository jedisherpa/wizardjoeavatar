# Wizard Joe Phazer Motion Intake

Date: 2026-07-24

## Scope

This intake pauses the Serena Quill rollout without altering or discarding its
worktree. It adds the user-supplied `WizardJoePhazerSprites.zip` motions to the
existing Python Wizard Joe HD projector as gated candidates. It does not
replace the Python runtime, create a second connector, or admit reconstructed
art as production art.

## Source Census

- Archive SHA-256:
  `636b9ddf8a5edff9db9de8f2eaa9ecf930b73bfe2b1d428b5111195ff4aec450`
- Eight image members, six poses per member, 48 poses total.
- The first six sheets are 2172x724, except `w3` at 2182x721.
- Two sheets are 1983x793.
- The members use WebP/VP8 payloads despite `.png` names.
- The sheets contain a baked light checkerboard and no source alpha channel.
- The isolated actors have less native pixel detail than the approved
  1254x1254 production masters.

The exact inventory and extraction settings live in
`assets/reference/hd_canonical/source-metadata/phazer/phazer_sprite_manifest_v001.json`.

## Reconstruction

`tools/build_hd_phazer_pose_masters.py` performs a deterministic rebuild:

1. Verify the archive digest, member inventory, and sheet dimensions.
2. Flood-fill only light neutral background connected to a sheet edge. This
   preserves enclosed white eye and tooth pixels.
3. Remove isolated components below the declared evidence threshold.
4. Assign whole connected components to the nearest authored pose center.
   This avoids slicing wings, staffs, and motion effects at nominal cell
   boundaries.
5. Normalize each six-frame sheet with one scale and one baseline transform.
6. Place every recovered pose on the canonical 1254x1254 transparent canvas.
7. Compile raw RGBA pixels into the existing `.wjpose` projector format.
8. Emit per-frame source boxes, output boxes, RGBA hashes, a contact sheet, and
   a reconstruction manifest.

The first nominal-column slicing approach was rejected because it clipped
cross-cell wing components. No artifact from that attempt is authoritative.

## Library Result

- 250 approved production alpha frames.
- 10 forward-flight review candidates.
- 48 Phazer visual-parity candidates.
- 308 total projector-review frames.
- `approved_hd_frames`: approved 250-frame comparison baseline.
- `phazer_all`: continuous 48-frame Phazer review reel.
- Eight named six-frame source-sheet sequences for focused inspection.

The Phazer shard is
`assets/reference/hd_canonical/compiled/candidate-phazer-motion-v001.wjpose`.
It stores colored RGBA pixel nodes, not PNG or SVG runtime assets.

## Approval Boundary

The following checks are mechanical and repeatable:

- archive identity;
- full member inventory;
- 48 complete silhouettes;
- transparent canvas and corners;
- canonical dimensions and baseline;
- no component cropping at sheet-cell boundaries;
- deterministic artifact and index hashes;
- projector decoding.

Visual parity remains a human gate. Upscaling and sharpening cannot restore
detail absent from a contact-sheet source. Until the candidate is judged
against approved HD Joe at full projector size, every Phazer pose remains
`candidate_visual_parity` with `runtime_admitted: false`.

## Review

Run:

```bash
python3 tools/run_character_observer.py \
  --review-sequence phazer_all \
  --current-label "Wizard Joe Phazer motion" \
  --current-meta "48 reconstructed alpha candidates"
```

The observer shows `approved_hd_frames` on the left and `phazer_all` on the
right at `http://127.0.0.1:8665/`. Approval or rejection must reference the
candidate shard hash and should record any frame IDs requiring recreation.

## Verification Receipt

- Candidate shard SHA-256:
  `78847931f1f2a529de5aae7c17c07f5cf93b437d7a7492c7d0ee944371be3f46`
- Library index SHA-256:
  `1a3735f8ade0082f89b21786a3a02059609d5f13aac2f8944d2d94a873bc9a05`
- Two consecutive rebuilds produced both exact hashes.
- Six focused reconstruction/observer tests passed.
- The 23-test companion-server and reconstruction run passed.
- All 48 compiled frames decoded at 1254x1254, contained foreground alpha,
  and retained four transparent corners.
- A rebuild completed while the persistent review reel was requesting frames;
  atomic file replacement kept the projector ready with no `8666` error.
- Browser evidence showed both panels, a native 1254x1254 canvas in each
  runtime view, changing projected samples, and no console error from `8666`.

The full Wizard suite ran 844 tests: 839 passed and five failed. The same five
tests failed unchanged at clean parent `44844a900eefb885704a599d45e355c28b085559`,
so they are recorded as inherited baseline failures rather than Phazer intake
regressions:

- stale expected Python pose count, 186 versus existing 193;
- two existing head/breath contact assertions;
- an existing permission-world reduced-motion assertion;
- an existing reference-overlay settled-marker assertion.
