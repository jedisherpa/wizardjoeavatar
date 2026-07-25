# Serena Locomotion Evidence Audit

Date: 2026-07-24

## Verdict

Serena Quill has eight admitted static facings and sixteen frozen ground-motion
drawings, but she does not yet have a truthful runtime locomotion cycle. Walk,
run, turn, stop, takeoff, flight, and landing remain disabled in the shared
Python controller.

The source drawings prove pixel extraction, not phase, support-foot, contact,
loop-closure, or transition semantics. Static turnarounds are not turn
animation, and the isolated airborne drawing is not a complete jump.

## Evidence Inventory

- Walk: four drawings, with only `walk_contact_left` admitted.
- Run: two drawings, with only `run_contact_left` admitted.
- Start and stop: one drawing each, without reviewed contact semantics.
- Turn: left and right drawings, without a reviewed transition sequence.
- Jump: crouch, anticipation, and airborne drawings, without takeoff or landing
  continuity.
- Flight: no authored hover, travel, bank, ascent, or descent cycle.
- Landing: fall, contact, and recovery drawings, without reviewed support-foot
  or incoming-phase semantics.

The graph therefore retains one-sample diagnostic holds and zero-duration
coherent cuts. The runtime profile keeps all locomotion-cycle arrays empty.

## Smallest Truthful Locomotion Gate

`SQ-L0 South Walk Contact and Loop Validation`:

1. Review the four south-walk panels at full resolution.
2. Assign phase, support foot, planted anchor, and root policy.
3. Require reciprocal right-foot stance and believable loop closure.
4. Commission missing art rather than mirror or infer it.
5. Prove three graph-only loops at normal and quarter speed.
6. Keep runtime walk disabled until reviewed start and stop behavior also pass.

This gate is intentionally deferred while governed static performance can
advance with already-admitted assets.
