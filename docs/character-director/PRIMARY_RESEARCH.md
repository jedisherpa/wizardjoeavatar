# Primary-Source Technical Research

Research checked on 2026-07-15. Repository evidence remains authoritative when
it differs from generic guidance.

## Deterministic Contracts

[RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html) defines JSON
Canonicalization Scheme (JCS) for invariant hashing/signing. It requires the
I-JSON subset, including no duplicate object names and finite IEEE-754 numeric
values, with deterministic primitive serialization and property ordering.

Character Director content identities, context hashes, capability snapshots,
score hashes, and governed-content receipts should use one audited canonical
implementation. Python's ordinary `json.dumps(sort_keys=True)` is not by itself
a cross-language JCS guarantee. Every decoder must reject duplicate keys,
`NaN`, and `Infinity` before canonicalization.

[JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) separates
core and validation vocabularies and supports explicit dialect/version
declarations. Character Director schemas should declare the exact dialect,
disallow unevaluated properties where appropriate, and supplement structural
validation with semantic checks for graph references, permissions, stale IDs,
timing, and transitions.

## Async Runtime and Backpressure

Python's [asyncio queue documentation](https://docs.python.org/3.12/library/asyncio-queue.html)
states that `maxsize <= 0` is infinite, while positive `maxsize` applies
backpressure. Every command, frame, cue, diagnostic, and cross-thread queue must
therefore declare a positive capacity and an explicit full-queue policy.

Python's [asyncio task documentation](https://docs.python.org/3.12/library/asyncio-task.html)
describes structured task ownership through `TaskGroup` and requires related
tasks to be awaited on exit. `TaskGroup` starts at Python 3.11, while the
current project permits Python 3.9. The first implementation must either keep
3.9-compatible explicit task tracking/cancel-and-await or deliberately raise
the minimum version with package and migration evidence.

The same documentation describes `asyncio.to_thread()` as primarily intended
for blocking I/O; CPU-bound benefit depends on extensions releasing the GIL.
Frame rendering must be made pure and benchmarked before choosing a worker
thread or process. A worker does not excuse unbounded queues or out-of-order
presentation.

## Authoritative Audio and Alignment

The [WHATWG media element specification](https://html.spec.whatwg.org/multipage/media.html)
defines media timeline changes, seeking, playback rate, and the "time marches
on" steps; timed cue events should be delivered as close as possible to their
timeline positions, ideally within 20 ms. The existing Prism audio element
remains the product's authoritative clock. Connector samples may be
interpolated only while fresh and must snap/reseek on authoritative changes.

The [Web Audio specification](https://www.w3.org/TR/webaudio-1.0/) defines all
scheduled Web Audio times relative to `AudioContext.currentTime`. If Prism later
uses a Web Audio graph, scheduling must remain derived from the actual audible
playback clock rather than a separate animation timer.

ElevenLabs provides [TTS with character timestamps](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)
and a [forced-alignment API](https://elevenlabs.io/docs/overview/capabilities/forced-alignment)
returning character/word timing. Provider alignment should be preserved with
the governed content identity. Missing timing may use the approved local
alignment path; external forced alignment remains explicit, configurable, and
permission-aware rather than an implicit playback dependency.

## Reduced Motion

W3C technique [C39](https://www.w3.org/WAI/WCAG21/Techniques/css/C39) requires
honoring `prefers-reduced-motion` for interaction-triggered motion. Character
Director also needs an explicit in-product reduced-motion preference because
performance channels are not limited to CSS. The reduced variant must preserve
meaning, captions, approvals, errors, and interruption while suppressing
nonessential locomotion and large gestures.

## Architecture Consequences

1. Use strict, versioned, canonical contracts with separate semantic validators.
2. Keep all ordinary playback deterministic and free of live model calls.
3. Make every queue bounded and observable.
4. Track and await every task/worker during shutdown.
5. Drive text, mouth, gaze, and body cues from the audible Prism timeline and
   alignment data, not wall-clock guesses.
6. Preserve reduced-motion equivalence as a compiled capability variant.
