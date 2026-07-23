# HD Alpha Source Adoption

Date: 2026-07-22

## Decision

Wizard Joe's HD actor is built from the two user-supplied transparent-alpha
archives. Work that attempted to redesign or regenerate the staff is
disregarded. The supplied pixels, including their authored staff, identity,
costume, wings, proportions, expressions, and pose composition, are immutable
source art.

## Source Status

- `wizard_joe_base_250_alpha` v001: 250 full-resolution 1254x1254 RGBA frames,
  all marked `approved_production_alpha`, with 250 technical passes and 250
  unique output hashes.
- `wizard_joe_forward_camera_flight_cycle` v001: ten full-resolution 1254x1254
  RGBA frames. The source is available to the library, but its manifest status
  is `candidate_review`, so animation/runtime admission remains closed.

Archive and per-frame hashes are enforced by the build. The authoritative
release manifests and QA reports are preserved under
`assets/reference/hd_canonical/source-metadata/`.

## Runtime Contract

The Python build converts source PNG pixels into independently compressed RGBA
pixel-node records in sharded `.wjpose` artifacts. The projector receives raw
RGBA bytes and paints them directly to a native 1254x1254 canvas. PNG and SVG
files are not served as runtime render assets.

The source-art approval and runtime-animation approval are intentionally
separate. The 250 frames may be reviewed through the projector immediately;
motion clips, transitions, root motion, contact continuity, and the new flight
cycle remain subject to the existing character-director gates.
