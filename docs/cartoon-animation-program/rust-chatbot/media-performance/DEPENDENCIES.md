# Dependency Decisions

Status: decisions are in review. No dependency is considered shipped until its
lockfile, source checksum, transitive license/advisory report, Rust 1.75 build,
three-platform package plan, security tests, and runtime evidence pass.

## D-001: Audio Decode - Symphonia 0.5.x Compatibility Line

- Purpose: probe and decode MP3, M4A/M4B/AAC, WAV, FLAC, metadata, duration, and
  normalized PCM for offline analysis.
- Maintenance: active project; 0.6 is current but requires Rust 1.85.
- Platform support: pure Rust across macOS, Linux, and Windows for enabled codecs.
- License: MPL-2.0; source-file obligations must be reviewed for distribution.
- Security: use bounded file sizes, packet/sample counts, duration, channel count,
  and decoded-memory budgets; treat media as hostile input.
- Binary size: feature-gate only required formats/codecs; do not use `all`.
- Native build: none for supported pure-Rust codecs.
- Runtime resources: offline worker only; stream analysis windows rather than
  decoding an entire audiobook into memory.
- Alternatives: FFmpeg subprocess, GStreamer, rodio wrapper, Symphonia 0.6.
- Decision: prototype against the latest 0.5.x compatible with PrismGT's declared
  Rust 1.75. The candidate is exactly `symphonia = 0.5.5`, crates.io checksum
  `5773a4c030a19d9bfaa090f49746ff35c75dfddfa700df7a5939d5e076a57039`,
  with `default-features = false` and features `aac`, `alac`, `flac`, `isomp4`,
  `mp3`, `ogg`, `pcm`, `vorbis`, and `wav`. Do not enable `all`, change this pin,
  or raise the workspace MSRV without a new decision receipt. Use FFmpeg only as
  the separately governed compatibility fallback in D-008.
- Sources: https://docs.rs/symphonia/latest/symphonia/ and
  https://github.com/pdeljanov/Symphonia

## D-002: Managed Transcription - Reuse Existing Server Whisper CLI

- Purpose: explicitly authorized transcription, timestamps, confidence/token
  diagnostics, language detection, and deterministic preprocessing inputs.
- Maintenance: active upstream under ggml-org, with release artifacts and broad
  platform backends.
- Platform support: macOS, Linux, and Windows; Metal/GPU options are packaging
  profiles, not correctness requirements.
- License: MIT.
- Security: invoke without a shell, canonicalize paths, use private job dirs,
  restrict environment, cap output, timeout/cancel process groups, verify binary
  and model hashes, and parse structured output strictly.
- Binary size: native binary plus user-selected model; models are separate managed
  artifacts with visible disk requirements.
- Native build: CMake/C++ if built locally. Prefer a pinned packaged artifact with
  recorded upstream version and hash.
- Runtime resources: worker concurrency, threads, model, and chunk size are
  configurable and bounded. Never run on the render thread.
- Alternatives: archived `whisper-rs`, Python Whisper, third-party remote STT,
  direct FFI, or installing another local Whisper copy.
- Decision: extend PrismGT's existing `whisper-cli` subprocess boundary and reuse
  the installation already deployed on `root@5.78.137.112` when its inventory
  satisfies this contract. Do not install or download another copy during normal
  deployment. If a future migration is explicitly approved, the source candidate
  is whisper.cpp tag `v1.9.1`, commit
  `f049fff95a089aa9969deb009cdd4892b3e74916`; release packaging must build or
  acquire from that commit and record the per-platform executable SHA-256. The
  default model is `ggml-small.en.bin` from
  `https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-small.en.bin`,
  size `487614201` bytes, SHA-256
  `c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d`.
  Packaging must preserve the upstream model provenance/license record, verify
  size and hash before atomic installation, and make the 465 MiB download
  explicit. These download requirements apply only to an approved migration, not
  to the existing server. Use full
  JSON/VTT output, offset/duration options, word splitting, and timestamp/confidence
  data. Implement resumable overlap-aware chunking in Rust. Direct FFI may be
  reconsidered only after the subprocess implementation is measured and packaged.
- Deployment reuse: `root@5.78.137.112` already has a Whisper installation. The
  deployment preflight must inventory its absolute executable path, version
  output, executable SHA-256, model paths, model sizes/hashes, service account,
  and accelerator/runtime configuration. Reuse the existing installation when it
  satisfies this contract; do not download, overwrite, or install a second copy.
  A version/hash mismatch is reported as an unmanaged dependency and requires an
  explicit migration decision. Server-side transcription is opt-in because media
  leaves the user's device, even when the server is self-hosted; transport,
  retention, deletion, and audit behavior must be visible before upload.
- Runtime transport: production playback never shells out over SSH. A dedicated
  Rust HTTPS transcription worker on that host invokes the inventoried executable
  without a shell. Prism uploads bounded PCM chunks with TLS certificate validation
  and a separate least-privilege transcription credential provisioned outside job
  payloads; the deployment-only `CRX41_HETZNER_SSH` secret is never shipped to the
  app or used as a runtime credential. Server job directories are owner-only. Media,
  PCM, CLI output, and transcript fragments are deleted immediately after successful
  result acknowledgement or cancellation; abandoned/failed jobs have a hard one-hour
  retention ceiling enforced by a Rust janitor. Audit records retain hashes, tool/model
  identity, byte counts, timing, disposition, and deletion receipt, never media or
  transcript content.
- Sources: https://github.com/ggml-org/whisper.cpp,
  https://github.com/ggml-org/whisper.cpp/tree/master/examples/cli, and
  https://github.com/ggml-org/whisper.cpp/blob/master/LICENSE

## D-003: DSP Primitive - RustFFT

- Purpose: STFT/spectral flux, band energy, novelty curves, autocorrelation input,
  and deterministic feature extraction.
- Maintenance: active pure-Rust project.
- Platform support: Rust targets with optional automatic SIMD.
- License: MIT OR Apache-2.0.
- Security: bounded FFT sizes and input allocation; reject malformed configuration.
- Binary size: modest; feature selection measured in release builds.
- Native build: none.
- Runtime resources: offline windowed analysis with bounded scratch buffers.
- Alternatives: aubio, FFTW, realfft, custom DFT.
- Decision: use exactly `rustfft = 6.2.0`, crates.io checksum
  `43806561bc506d0c5d160643ad742e3161049ac01027b5e6d7524091fd401d86`,
  with default SIMD features. Do not add `realfft` in V1; project-owned windowing
  and real-to-complex packing keeps the dependency graph smaller. Build beat,
  downbeat-candidate, energy, onset, and section features in project-owned Rust
  code with golden fixtures and algorithm-version metadata.
- Source: https://github.com/ejmahler/RustFFT

## D-004: aubio - Rejected For Embedded Production Use

- Purpose considered: beat, onset, tempo, pitch, and MFCC extraction.
- Maintenance: mature but latest upstream release is old.
- Platform support: broad native C builds.
- License: GPL-3.0.
- Native build: required.
- Decision: reject as an embedded/default dependency because it creates licensing,
  packaging, FFI, and maintenance costs inconsistent with the Apache-2.0 PrismGT
  workspace. It may be used only as an external research oracle for fixture
  comparison if legal review permits and never as a hidden runtime dependency.
- Source: https://github.com/aubio/aubio

## D-005: Serialization And Hashing - Existing serde/serde_json/sha2

- Purpose: versioned contracts, canonical score representation, fixture IO, and
  content addressing.
- Maintenance/platform/license: already accepted in both repositories.
- Security: strict closed enums, bounded collections/strings, explicit schema
  versions, payload limits, duplicate-ID checks, and canonical hash tests.
- Decision: reuse the Prism lockfile pins: `serde 1.0.228` checksum
  `9a8e94ea7f378bd32cbbd37198a4a91436180c5bb472411e48b5ec2e2124ae9e`,
  `serde_json 1.0.150` checksum
  `e8014e44b4736ed0538adeecded0fce2a272f22dc9578a7eb6b2d9993c74cfb9`,
  and `sha2 0.10.9` checksum
  `a7507d819769d01a365ab707794a4084392c824f54a7a6a7862f8c3d0892b283`.
  Do not add a second score encoding in the first production version.

## D-006: URL Validation - Existing `url` Crate In PrismGT Workspace

- Purpose: parse and validate canonical external URLs for Whiz.
- Decision: promote `url` from the isolated `x-connector` manifest to the shared
  workspace dependency table and pin the existing lockfile version `2.5.8`,
  checksum `ff67a8a4397373c3ef660812acab3268222035010ab8680ec4215f38ba3d0eed`.
  Permit
  `https` by default; `http` requires explicit product policy. Reject credentials,
  control characters, non-network schemes, missing host, and overlong values.

## D-007: LLM Provider - Existing Governed Prism Dispatch

- Purpose: optional structured narrative passes and critique/correction.
- Decision: no new provider SDK. Use PrismGT's existing provider abstraction,
  permission/governance model, audit path, and explicit user configuration.
  Deterministic local analysis remains available; playback has no LLM dependency.

## D-008: FFmpeg Compatibility Boundary

- Purpose: optional decode/probe fallback for containers unsupported by the
  pinned Symphonia feature set and existing microphone/transcription conversion.
- License/distribution: FFmpeg license depends on configured components. Prism
  will not silently bundle a Homebrew or system binary. Each packaged build must
  record the exact upstream version, configuration flags, source URL, executable
  SHA-256, LGPL/GPL determination, notices, and redistribution basis.
- Security: invoke by absolute managed path without a shell, clear unneeded
  environment, enforce timeout/output/file/duration limits, and use private job
  directories. System-path discovery is developer mode only and is surfaced to
  the user.
- V1 decision: FFmpeg is excluded from the media-performance product, release
  bundle, acceptance matrix, and supported-format claim. Prism decodes supported
  media with the pinned Symphonia feature set and writes Whisper-compatible PCM/WAV
  in project-owned Rust. A file requiring FFmpeg fails the format probe with
  `unsupported_container`; no PATH lookup or fallback subprocess occurs. Prism's
  pre-existing FFmpeg use outside this product boundary is not promoted or treated
  as media-performance evidence.
- Future gate: adding FFmpeg requires a new dependency decision that freezes exact
  upstream source tag and commit, source archive SHA-256, configure flags, compiler,
  per-platform executable SHA-256, license determination, notices, redistribution
  basis, and a registered package receipt before code may call it.

## Reproducibility Gate

Before dependency promotion, CI must run `cargo build --locked` and tests with
Rust `1.75.0` on macOS 26.3 arm64, Ubuntu 24.04 x86_64, and Windows 11 24H2
x86_64; generate `cargo metadata --locked`,
`cargo tree -e features`, license inventory, RustSec advisory results, and release
binary-size deltas; and hash every native binary/model. Any changed crate,
feature, checksum, toolchain, native flag, model, or source commit reopens this
decision set. Linux and Windows are dependency/build/contract gates, not claims of
a packaged desktop product. The V1 packaged runtime gate is macOS 26.3 arm64; a
Windows or Linux package requires its own signed packaging and runtime acceptance
receipt.
