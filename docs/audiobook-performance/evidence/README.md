# Audiobook Performance Evidence

This directory defines the redacted run manifest for protected audiobook-performance checks. Each evidence run copies `manifest.template.json` to its run directory, replaces every `REQUIRED` value, and records artifacts produced by the exact commands in that manifest.

## Required identity

- Record the Wizard and PrismGT repository URL, commit, branch, and dirty state. A dirty run also records a checksum of the patch without embedding the patch.
- Record UTC start/end times, workflow/run identity, hardware, power mode, OS, and relevant Python, Node, Rust, browser, and FFmpeg versions.
- Record lockfile checksums, fixture checksums, random seeds, command text, exit code, and stdout/stderr checksums.
- Record test counts, every waiver, and every artifact's repository-relative path, byte length, and SHA-256.
- Generate `SHA256SUMS` after the bundle is complete, then record its checksum in the manifest.

Paths in a published bundle must be repository-relative labels. Do not publish user home paths, copyrighted audio, transcript/manuscript text, tokens, provider payloads, raw URLs or query strings, or unredacted browser captures. Synthetic media and content-free hashes are allowed.

## Timing split

Scheduler correctness is owned by the fake-clock test:

```sh
python3 -m unittest tests.wizard.test_stream_hub.StreamHubTests.test_frame_loop_does_not_replay_missed_deadlines
```

That test executes 100 deterministic schedules and contains no real-time sleep assertion. It proves missed-deadline accounting, no replay burst, no simulation run-ahead, and future-aligned rescheduling through the production `WizardFrameHub._run` policy.

Real renderer cost is measured separately and does not decide scheduler correctness:

```sh
python3 tools/benchmark_stream_render.py \
  --profile medium \
  --fps 24 \
  --warmup 3 \
  --frames 30 \
  --output qa-evidence/<run-id>/performance/stream-render.json
```

The report separates simulation, cell render, frame encode, frame hash, queue wait, renderer-pipeline, and end-to-end percentiles. The reference 24 fps, 240x135 gate is renderer-pipeline p95 at most 33.3 ms and p99 at most 41.7 ms. A failed performance gate remains evidence; it must not be converted into a correctness retry or a weaker frame-count assertion.

## Finalization

1. Validate `manifest.json` as JSON and confirm no `REQUIRED` placeholders remain.
2. Verify every command has an exit code and every referenced artifact exists.
3. Recompute fixture and artifact SHA-256 values.
4. Scan the complete bundle for privacy canaries and record the scanner command/result.
5. Generate and verify `SHA256SUMS` last.
