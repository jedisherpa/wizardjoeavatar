# Speech Mouth Authority

## Problem

The renderer previously treated every non-null `speech_id` as legacy local
speech and replaced `state.mouth` with an unrelated simulation-time cycle.
Governed Prism speech also carries a speech ID, so accepted phoneme shapes and
intentional silence could be overwritten after the media scheduler had resolved
them. The local fallback itself was a global 10 Hz loop with no relationship to
the utterance or its punctuation.

## Authority Contract

`WizardState.speech_mouth_authority` now makes ownership explicit:

| Authority | Clock and rendered source | Lifecycle owner |
| --- | --- | --- |
| `media_alignment` | Accepted provider/local alignment evaluated from authoritative media time; renderer uses `state.mouth` unchanged | `PerformanceApplication` and the media lifecycle |
| `local_fallback` | Deterministic utterance-relative text rhythm | Local `speak` / `speech_stop` commands and simulation timeout |
| `none` | Expression or authored base pose | Character state |

The controller expires only `local_fallback` speech. Governed speech is cleared
only by pause, stop, revocation, binding change, expiry, or another authoritative
media event. This prevents a simulation tick from cancelling valid aligned
speech between connector updates.

## Local Fallback

The fallback remains explicitly degraded because it does not claim audio or
phoneme alignment. It now:

- starts and ends relative to the individual utterance rather than global
  simulation time;
- weights words with a bounded syllable/length proxy;
- derives varied but deterministic mouth patterns from each word;
- inserts closed rests for punctuation;
- resumes after internal sentence stops;
- settles closed before the utterance lease ends; and
- produces the same sequence when the same utterance starts at a different
  simulation time.

No body pose is selected from mouth cadence. Speech continues to coexist with
locomotion, and cast interruption retains the authored precommit/postcommit
rules.

## Presented Diagnostics

`WizardPresentationState.rendered_mouth_shape` records the shape used by the
committed raster. `/api/avatar/wizard/state` now exposes:

- `diagnostics.mouth_state`: the presented shape;
- `diagnostics.mouth_command_state`: the authoritative command/state value; and
- `diagnostics.speech_mouth_authority`: the active ownership path.

This closes the former observability gap where diagnostics reported the local
seed value even while the projector painted another shape.

## Verification

Focused mouth, frame-source, controller-channel, governed-release,
render-commit, and snapshot-purity tests passed. The full 548-test Wizard suite
has one unrelated pre-existing golden-hash failure: clean commit `923200b`
reproduces the same expected `7f3f...` versus derived `dd277...` capability
manifest mismatch. The Python production validator checked 140 paths with zero
violations.

`evidence/character-director/speech-continuity-a29ba96-2026-07-18/` is bound to
clean commit `a29ba96`. It contains 335 contiguous decoded frames with zero
drops, gaps, or decoder errors, including 35 speaking frames and 23 explicit
speech-interruption frames. Runtime identity remained stable. Contact
verification passed with zero issues and zero root residual.

- manifest SHA-256: `30e91ddf256832837dd6c91632ee5d02d5c3838e539a38f59e37f725c3582324`
- contact report SHA-256: `fc658b4852733891236a34593dabee81a2a13f63317ace1cfcad8233e5b1c7dc`
- truth trace SHA-256: `a688cccf48120e90ad9b2545ae34c224e80891c9c8675ea1764ed7b1f6d0ef29`
- capture SHA-256: `fb48bc13acaa3f4834d39bae0e20161ab95fbcaa8ca25498e9d4a9496b56b893`
- contact sheet SHA-256: `a3bbde16c95db51e8e5486997e7dda7c7a6122182cbe8952b42a0a7348447935`

This evidence verifies local fallback projection and interruption continuity. It
does not replace the remaining connected Prism AV-sync, rate/seek/reconnect,
long-form acting, accessibility, or complete V1-V10 acceptance matrix.
