# V8 Purposeful Performance Acceptance Candidate

Date: 2026-07-24

Candidate commit:
`b34368e9166aeb71dfe50b7b31c71165f1a35151`

Evidence:
`evidence/character-director/v8-purposeful-performance-b34368e9-2026-07-24/`

## Current Verdict

V8 is **machine-passed and product-owner review pending**.

- Machine acceptance: **PASS**, all checks.
- Atomic capture integrity: **PASS**.
- Governed audiovisual capture: **PASS**.
- Replacement real-browser presentation: **PASS**, zero drops.
- Independent still and machine review: animation evidence is strong, but the
  reviewer could not play or hear media and therefore returned **FAIL** for
  unconditional production acceptance.
- Product-owner approval for this exact candidate: **PENDING**.

The schema-version-3 review bundle is intentionally `complete: false` because
the required `product_owner_approval` artifact is absent. The V9 product-owner
approval is not reused as V8 approval.

## Prior Blocker Resolution

The rejected `19c808d9` evidence remains preserved separately. Its four
technical blockers are resolved for this candidate:

1. The retained analyzer is bound by SHA-256 and Git provenance to the exact
   clean capture candidate.
2. The machine report and derivative review products are bound by a validated
   review-bundle manifest.
3. The evidence includes authenticated Prism governed speech, retained audio,
   an AV timeline, an audible review, and a real-browser presentation.
4. Every detected blink closure has one body hash and one root, and prolonged
   input cannot stretch a closure beyond four presentation frames.

The first browser derivative reported four presentation drops. A clean replay
of the same scenario against the same candidate replaced that derivative with
zero-drop browser evidence. The immutable animation capture did not change.

## Measured Result

- Canonical V8 window: 1,440 owned frames at 24 FPS.
- Governed AV preroll: 960 owned frames.
- Combined immutable capture: 2,400 owned frames.
- Transport drops: zero.
- Decoder errors: zero.
- Clipped frames: zero.
- Blink closures: 13, each four frames.
- Distinct blink intervals: 12.
- Blink body/root stability failures: zero.
- Gesture effects: three.
- Body stillness ratio: 95.62%.
- Nonconstant short exact loop: none detected.
- Maximum root-axis step: zero.
- Final hold: one body hash, one head offset, and one root.
- Browser replay: 2,400 of 2,400 frames captured, 2,402 decoded and
  presented, zero presentation drops, zero raw-message drops, zero resyncs,
  zero page errors, and zero console events.
- AV timeline: 886 samples, including 240 active playing samples.
- Governed mouth authority: `media_alignment`.
- Observed active AV absolute offset: 2-100 ms, approximately 35.4 ms mean.
- Media source slot: `speech`.
- Permission world: ready.

## Review Targets

- Normal combined performance:
  `visual-review-f8d7726254c4-capture.mp4`
- Complete V8 performance at quarter speed:
  `v8-quarter-speed.mp4`
- Governed speech with synchronized retained audio:
  `v8-audible-review.mp4`
- Zero-drop real-browser presentation:
  `v8-browser-layout.mp4`
- Full contact sheet:
  `visual-review-f8d7726254c4-contact-sheet.png`

Product-owner acceptance must explicitly name candidate `b34368e9` or the
evidence directory above. Once accepted, add a self-sourced approval record
and rebuild `review-bundle-manifest.json`; its `complete` field must then
validate as `true`.

## Artifact Hashes

- Capture manifest:
  `cafdebfd3c7d24511603dcaa49cb316613c280168c47168626f400a4646d398e`
- Machine acceptance:
  `06015ac8f208062bc4b5a701cd53453d210b02f198ae0bfc2415efe417ae5fcb`
- Browser presentation:
  `c41e23ffbc8b2c3072cb1ba8f3abd79035b55aeda5dbef8aaf45136f70018a39`
- Browser metrics:
  `fecae2d85956723d36f13afc042cc4eaddc90fd04e883d041c5f3a6e5a2a1d3f`
- Quarter-speed review:
  `799e626598ccd5c4bca64470f50af589deffaae7cb979527d64e2f0f7dd4fd58`
- Audible review:
  `a1f55ac51cd06e502a17ee2333fa789c744fdb1f211548d67b4f4ec714ac8cd7`
- Retained audio:
  `24ea0ac0fa27fde7746c1731c7146669714de78c71a4088d20eb3fc49bd512b7`
- AV timeline:
  `0a0f6b9485e5282f6360277dfb83eeb09a3aa7c0665d33c3f8a7f58313c3aac9`
- Review bundle:
  `53be69d0c70f225b788f147950a3b7b80470257a77c8fcd877ae417f7e7b705b`

## Verification

The focused runtime, V8 acceptance, evidence-bundle, and browser-recorder
suite passed 81 tests on 2026-07-24.

The review bundle must be validated using the retained candidate checkout,
because the capture manifest deliberately binds the runtime repository root,
tree, clean state, and analyzer provenance.
