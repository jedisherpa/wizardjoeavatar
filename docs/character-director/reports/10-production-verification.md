# Production Verification Lead Report

## Verdict

Not release-ready. Source tests are substantial, but no immutable remotely
recoverable candidate passes package, cross-process, long-duration, visual,
privacy, and rollback gates.

## Current Evidence

- Persistent compatibility server: PID `55990`, `127.0.0.1:8765`, ready,
  connector enabled, LaunchAgent KeepAlive.
- Live 10-second sample: simulation about 60 Hz, presentation about 10.5 FPS,
  continuous overruns; about 56% idle CPU and 516 MB RSS with two subscribers.
- Compatibility log exceeded 71 MB and 956,000 lines in roughly eight hours.
- Installed Companion is ad-hoc signed but not a current accepted candidate.
- Installed Prism contains legacy fixed-port connector behavior, not proven
  Companion discovery behavior. Preserve the notarized pre-connector rollback.

The QA launch crash observed earlier in the audit was subsequently fixed in the
preserved dirty worktree with explicit app-data/discovery overrides and a
validated macOS resource fallback. A bounded QA run proved private discovery,
single instance, child recovery with epoch rotation, graceful cleanup, and
unchanged PID `55990`. That is local dirty-worktree evidence, not an immutable
release candidate.

## Blocking Findings

1. No clean remote candidate contains all current Wizard or Prism work.
2. The preserved Prism worktree has damaged Git objects; the healthy clone at
   `5910601` is now the integration base.
3. Packaged real main-media -> persona-speech -> restored-main E2E is absent.
4. Live cadence, CPU, and memory fail production thresholds.
5. Sidecar provenance uses `git diff --quiet`, which ignores untracked files.
6. Wizard and Prism logs are unbounded.
7. Python, Rust, and JavaScript duplicate fixtures instead of consuming one
   corpus with a hash gate.
8. Prism CI omits connector JavaScript tests; Wizard has no CI workflow.
9. Evidence ledgers contain stale and contradictory test counts.

## Release Thresholds

- Clean repositories, remote SHAs, clean `git fsck`, no alternates.
- Simulation 59-61 Hz and presentation 23-25 FPS in every 60-second window.
- Command p95 <=100 ms; zero decode/sequence errors and queue drops.
- Media drift p95 <=50 ms, maximum <=100 ms over two hours.
- Seek settlement <=500 ms; reconnect/discovery recovery <=3 seconds.
- No crash, orphan, discovery leak, or exhausted restart policy.
- RSS growth <5% per hour and idle CPU <15% on the reference Mac.
- Rotating privacy-safe logs <=25 MB/day per process.
- Full-frame desktop/minimum/Retina evidence, visible mouth motion, and recorded
  speech preemption/restoration.

## Required Test Layers

Fresh Python tests; Node browser/Companion tests; strict Rust format/test/Clippy;
locked Prism workspace; one cross-language fixture corpus; packaged lifecycle
in both launch orders; real media/persona speech; crash/reconnect; desktop,
minimum, Retina, VoiceOver, and reduced-motion visual review; two-hour PR,
eight-hour nightly, and 24-hour release soaks.

## Missing Harnesses

- Shared protocol manifest and fixture corpus.
- Isolated Companion QA builder.
- Cross-language E2E runner.
- Fault matrix.
- Soak runner.
- Visual review runner.
- Hashed evidence manifest.

## Rejected Alternatives

- Mutating or soaking persistent `8765`.
- Replacing installed or notarized rollback apps.
- Accepting dirty cached bundles.
- Unit tests or ad-hoc signing as package acceptance.
- Temporary `HOME` for macOS isolation.
- Separately hard-coded fixtures called parity.
- Generic process killing, implicit fallback, or destructive Git rollback.
