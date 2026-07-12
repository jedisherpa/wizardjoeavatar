# Required ASCILINE Tests

Implement:

```text
WIZ-ASC-001 direct procedural frame source works
WIZ-ASC-002 no video decoder is invoked
WIZ-ASC-003 raw frame round-trips
WIZ-ASC-004 compressed frame round-trips
WIZ-ASC-005 delta frame round-trips
WIZ-ASC-006 production Python frame decodes in production browser decoder
WIZ-ASC-007 initial keyframe reconstructs the stage
WIZ-ASC-008 periodic keyframe reconstructs the stage
WIZ-ASC-009 dropped frame triggers resync
WIZ-ASC-010 reconnect receives fresh keyframe
WIZ-ASC-011 frames remain in sequence
WIZ-ASC-012 idle delta changes remain small
WIZ-ASC-013 walking delta contains expected changed cells
WIZ-ASC-014 fixed background is not repeatedly retransmitted as changes
WIZ-ASC-015 medium profile sustains 24 FPS
WIZ-ASC-016 high profile targets 30 FPS
```

Use the shipped browser decoder in tests.

Do not build a separate test-only decoder.
