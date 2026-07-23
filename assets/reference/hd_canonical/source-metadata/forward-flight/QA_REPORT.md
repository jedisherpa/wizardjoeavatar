# Wizard Joe Forward-Camera Flight Cycle — QA Report

## Verdict

**PASS AS REVIEW CANDIDATE — HUMAN APPROVAL PENDING**

## Technical checks

- 10/10 ordered PNG frames present.
- 10/10 are 1254 × 1254 RGBA sRGB PNGs.
- All canvas corners are transparent.
- All silhouettes remain inside the 5.5% safe-margin target.
- Ten unique output hashes are recorded in `flight_cycle_manifest_v001.json`.
- A single common cycle scale is applied to all ten frames.
- The camera-facing head anchor is aligned across the sequence.
- A deliberate small vertical bob is preserved; no ground-line alignment is used for flight.
- Independent PNG and preview decoders read all ten frames after clean re-encoding.

## Visual checks

- Wizard Joe looks directly toward the camera in every key.
- Frontal flight orientation is maintained.
- Wing phases read in order: top recovery, early/mid/late powerstroke, bottom powerstroke, early/mid/late recovery, near-top recovery, loop closure.
- Exactly two rainbow wings remain present with stable color order.
- Exactly one continuous crook staff remains on the canonical screen-right side.
- Full hat, shoes, hands, staff, and both wings remain visible.
- No scenery, text, watermark, spell effect, particle, shadow, or extra prop is present.
- Chroma background is removed; connected-component extraction protects enclosed green wing pixels.
- Partial-alpha edge colors are decontaminated to avoid a green fringe.

## Loop check

- Intended order: `001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 009 → 010 → 001`.
- Frame 010 approaches the same high-V wing path and low body-bob state completed by frame 001.
- Suggested playback is 100 ms per frame (10 fps); the runtime may retime the downstroke faster than recovery for added force.
- Forward motion must be authored as continuous root/Z translation or camera-relative scale outside this loop. Do not restart scale at frame 001.

## Approval note

This is a new optional flight phrase and does not replace or inflate the accepted base-250 repertoire. Human approval is required before canonical promotion.

