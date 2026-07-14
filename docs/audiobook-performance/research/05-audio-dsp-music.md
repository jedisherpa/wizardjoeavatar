# Audio DSP and Music Analysis Audit

- **Date:** 2026-07-13
- **Role:** Audio DSP and Music Analysis Engineer
- **Scope:** Read-only audit of WizardJoeAvatar-python and Prism Geometry Talk (PrismGT), plus primary-source dependency research.
- **Change boundary:** This report is the only file produced. No production code or dependency manifests were changed.

## Executive recommendation

Neither audited application currently performs semantic music analysis. WizardJoe has a deterministic 60 Hz simulation and a browser speech trigger, but no decoded-audio path. PrismGT performs useful real-time Web Audio measurements (RMS-like level, three broad spectrum bands, and positive spectral flux), but its UI-facing `pulse` is a heuristic, not a detected beat. PrismGT does not estimate tempo, downbeats, meter, musical sections, calibrated loudness, or a replay-stable energy timeline.

Build one local, offline analysis pipeline that emits a versioned sidecar keyed by the source-audio hash. Use:

1. **FFmpeg** with a pinned LGPL-compatible build to decode and canonicalize input to fixed-rate PCM.
2. **SoundFile** for simple WAV/FLAC PCM access, and **librosa 0.11** plus NumPy/SciPy for baseline onset, RMS/energy, tempo, beat, and structural-boundary features.
3. **FFmpeg `ebur128`** for the canonical ITU-R BS.1770 / EBU R128 loudness measurements.
4. **Beat This! 1.1.0** as an optional, higher-accuracy local beat/downbeat model. Pin both package and model checksum; prefer CPU inference when exact repeatability matters.
5. Treat meter as an inference from stable beat/downbeat intervals with confidence and an explicit `unknown` state. Do not ship Essentia's `Meter` algorithm as the answer: its own reference labels it experimental and says not to use it.
6. Treat functional section labels (verse/chorus/etc.) as optional research output, not baseline truth. All-In-One Music Structure Analyzer is the strongest scoped candidate found, but its heavy model stack and transitive `madmom` dependency require a separate licensing and packaging gate.

At runtime, visuals should query the sidecar using the current media time on every animation frame. Beat/bar/section phase must be derived from event timestamps, never accumulated from `requestAnimationFrame`, `performance.now()`, or `setTimeout`. Keep PrismGT's current analyser only as a low-latency cosmetic layer for micro-reactivity.

## Audit method and code bases

The audit inspected the current files on disk at:

- WizardJoe: `/Users/paul/Documents/WizardJoeAsci/WizardJoeAvatar-python`
- PrismGT: `/Users/paul/Documents/Codex/2026-06-28/jedisherpa-prism-geometry-talk-https-github/work/prism-geometry-talk-current`

Code references below are absolute paths and line spans from the audited snapshot. Dependency and standards claims link to official specifications, project documentation, repositories, or papers.

## Current implementation

### WizardJoeAvatar-python

WizardJoe has a good deterministic consumer for precomputed animation data, but no audio-analysis producer:

- `wizard_avatar/runtime.py:15-19,176-220,257-350` defines an exact 60 Hz, single-writer simulation, advances from monotonic nanoseconds, hashes canonical state, and bounds catch-up.
- `wizard_avatar/stream.py:151-190` uses `perf_counter_ns()` and drops missed presentation deadlines rather than bursting stale frames.
- `wizard_avatar/controller.py:42-60` derives state time from `simulation_tick * SIMULATION_DT`, which is suitable for reproducible playback of a known timeline.
- `wizard_avatar/controller.py:104-109,328-339`, `wizard_avatar/mouth.py:24-26`, and `wizard_avatar/layers.py:246` use a duration timer and a 10 Hz fallback mouth cycle. These are animation heuristics, not waveform analysis or phoneme alignment.
- `web/avatar/wizardControls.ts:216-229` creates a browser `SpeechSynthesisUtterance`, estimates a command duration, and waits for `onend`/`onerror`. It receives no PCM, word boundary timeline, or audio-device clock mapping.
- `pyproject.toml:1-10` and `requirements.txt:1-4` contain FastAPI, Uvicorn, and Pillow only. There is no decoder, DSP, MIR, or loudness dependency.

**Result:** WizardJoe can deterministically render a supplied event envelope, but today it cannot extract one. Its speech timer is not synchronized to a measurable media clock.

### PrismGT

PrismGT's main music path is a browser-local, real-time feature mapper:

- `src/pages/PrismDodecahedron/musicMotion.js:163-238` connects the HTML media element to an `AudioContext` and `AnalyserNode`, with `fftSize = 2048` and `smoothingTimeConstant = 0.76`.
- `musicMotion.js:88-110,240-336` averages byte-valued frequency bins into 28-180 Hz, 180-2200 Hz, and 2200-12000 Hz bands; computes an RMS-like time-domain level; computes positive spectral flux; adaptively peak-normalizes the values; and blends them into `transient` and `pulse` controls.
- `musicMotion.js:70-82,188-193,323-329` exposes level/bands/transient/pulse plus `audio.currentTime`, duration, and normalized progress.
- `src/pages/PrismDodecahedron/index.jsx:2858-2896` sends each analysis frame to the Three.js scene and throttles UI metric updates to roughly 90 ms.
- `index.jsx:180-193,201-204` combines music and speech reactivity by taking per-field maxima.
- `index.jsx:3585-3596` uses hidden HTML `<audio>` elements with metadata preload.
- `index.jsx:2049-2104` schedules caption-token pulses from `audio.currentTime`, then uses `setTimeout` for future tokens and clearing.
- `src/pages/PrismHero/createPrismHeroScene.js:1174-1175,1596-1622` advances scene elapsed time from `performance.now()` deltas.
- `createPrismHeroScene.js:1844-1894` combines measured audio values with a synthetic `musicPhase` based chiefly on accumulated elapsed time. `beatBreakPattern` is a sine-derived animation oscillator, not a beat-grid lookup.
- `package.json:21-30` includes React, Three.js, Vite, lil-gui, and Tauri tooling, but no music-information-retrieval library.

The Web Audio analyser is a legitimate low-cost signal-reactivity mechanism. Per the [Web Audio specification](https://www.w3.org/TR/webaudio-1.1/#AnalyserNode), byte frequency data is the analyser's decibel range mapped to 0-255, and byte time-domain data maps the current waveform to 0-255. Averaging those frequency bytes is therefore a display-oriented spectral magnitude, not physical band power. It should not be called calibrated energy or loudness.

**Result:** PrismGT responds to audio locally and with low latency, but its `pulse` and `beatBreakPattern` names overstate the analysis. The current system has no musical event grid and cannot replay identical feature values after a seek or under a different render cadence.

## Findings

### Critical: no true beat, tempo, meter, or section analysis

The current `pulse` combines bass, level, and spectral flux. It can look musically responsive, but it does not solve beat tracking: there is no onset-strength history, tempo hypothesis, beat sequence, downbeat model, bar state, or confidence. `musicPhase` is a visual oscillator. Track progress contributes only two synthetic phase turns across the whole file (`progress * 4pi`), unrelated to BPM.

This distinction matters most for audiobooks with incidental music, sparse textures, rubato, or speech over music. A bass peak is not necessarily a beat, a beat is not necessarily a downbeat, and a regular downbeat sequence does not by itself prove a meter.

### Critical: animation phase is not locked to the media clock

PrismGT samples `audio.currentTime`, but the scene's musical phase advances from wall-clock frame deltas. Pause, seek, playback-rate changes, background-tab throttling, and dropped frames can therefore leave phase unrelated to the audio position. Caption-token timers inherit similar seek and throttling risks.

The [HTML media specification](https://html.spec.whatwg.org/multipage/media.html#dom-media-currenttime-dev) defines `HTMLMediaElement.currentTime` as the official playback position. The [Web Audio specification](https://www.w3.org/TR/webaudio-1.1/#dom-baseaudiocontext-currenttime) separately defines `AudioContext.currentTime` as the audio rendering timeline and warns that it is not necessarily synchronized with other clocks. [`getOutputTimestamp()`](https://www.w3.org/TR/webaudio-1.1/#dom-audiocontext-getoutputtimestamp) provides the intended mapping between audio-context time and `performanceTime` for output-aware synchronization.

### High: current feature values depend on render cadence and history

`musicMotion.js` applies fixed per-callback peak decay and custom smoothing on top of the analyser's own smoothing. Because analysis runs under `requestAnimationFrame`, the effective time constants change with display refresh rate, load, and tab visibility. Adaptive peaks also make the result path-dependent: seeking into the same point after different preceding material yields different normalized values.

This is suitable for ephemeral visual texture, not for an authored or testable performance timeline. A deterministic timeline needs fixed audio-frame windows and hops, explicit units, and no dependence on how often the UI painted.

### High: loudness and energy are conflated

The RMS-like waveform level is useful for animation, but it is not programme loudness. The current spectrum-band values are quantized analyser bytes, not linear power. A production schema should keep at least these concepts separate:

- sample peak and true peak;
- RMS or log-RMS short-time energy;
- ITU-R BS.1770 momentary, short-term, and integrated loudness;
- EBU loudness range (LRA);
- broad-band spectral energy or perceptual bands;
- onset/transient strength.

[ITU-R BS.1770-5](https://www.itu.int/rec/R-REC-BS.1770-5-202311-I/en) is the current in-force recommendation for objective programme loudness and true-peak estimation. [EBU Tech 3341](https://tech.ebu.ch/publications/tech3341) specifies EBU Mode metering, and [EBU Tech 3342](https://tech.ebu.ch/publications/tech3342) specifies Loudness Range.

### Medium: there is no analysis provenance or cache contract

Neither application has a schema tying analysis to source bytes, decoder, sample-rate conversion, algorithm/model version, configuration, or result checksum. Without that contract, a dependency update or decoder difference can silently shift event timestamps.

Compressed-audio decode details matter. The All-In-One project explicitly reports decoder-dependent MP3 offsets on the order of 20-40 ms and recommends standard WAV for reproducibility in its [official repository documentation](https://github.com/mir-aidj/all-in-one). The safe boundary is to canonicalize once, analyze canonical PCM, and store sample-index events plus provenance.

## Capability recommendations

### Decode and canonicalization

**Recommended:** invoke a pinned FFmpeg build as an explicit subprocess boundary. Decode once to canonical PCM with fixed channel policy, sample rate, sample format, and resampler settings. Analyze the canonical PCM and bind the sidecar to both source and canonical hashes.

- FFmpeg covers the widest practical set of audiobook/music containers and codecs; its [format support](https://ffmpeg.org/general.html#File-Formats) is maintained by the project.
- FFmpeg is primarily LGPL 2.1-or-later, but enabling GPL components changes the combined build's license obligations. The project's [legal page](https://ffmpeg.org/legal.html) provides the compliance checklist and notes possible codec patent concerns. Record the exact build configuration; licensing conclusions are a release/legal gate, not a code assumption.
- For WAV/FLAC and canonical PCM access from Python, [SoundFile](https://python-soundfile.readthedocs.io/en/latest/) is a small, NumPy-friendly option. The Python package is BSD-3-Clause; it wraps libsndfile, whose license and bundled-binary notices must remain in the distribution.
- [PyAV](https://github.com/PyAV-Org/PyAV) is a capable BSD-3-Clause Python binding to FFmpeg, but it couples the process to FFmpeg ABI/build details. Use it only if in-process packet/frame control is worth the larger packaging and crash boundary. A subprocess is easier to pin, inspect, and replace.

Canonicalization policy should be explicit, for example: preserve source channels for loudness; separately generate mono float32 at 44.1 kHz for MIR; use fixed resampler parameters; store original duration, canonical frame count, encoder delay/padding treatment, and all command arguments.

### Onsets, tempo, and baseline beats

**Recommended baseline:** [librosa 0.11](https://librosa.org/doc/0.11.0/index.html) with pinned NumPy/SciPy versions.

- [`onset_strength`](https://librosa.org/doc/main/generated/librosa.onset.onset_strength.html) computes a spectral-flux onset envelope, and [`onset_detect`](https://librosa.org/doc/main/generated/librosa.onset.onset_detect.html) peak-picks onset events.
- [`beat_track`](https://librosa.org/doc/latest/generated/librosa.beat.beat_track.html) estimates tempo from onset autocorrelation and selects beats with dynamic programming.
- The [feature API](https://librosa.org/doc/latest/feature.html) provides RMS, tempograms, spectral descriptors, chroma, and related building blocks.
- The project uses the permissive [ISC license](https://github.com/librosa/librosa/blob/main/LICENSE.md). Version 0.11.0 is the current stable release shown by the project's [PyPI record](https://pypi.org/project/librosa/) as of this audit.

Use librosa for a transparent baseline and feature extraction, not as a claim of universally accurate meter or downbeats. Parameters must be fixed, event times must be stored as integer canonical-sample indices, and regression fixtures must pin results.

**Recommended accuracy tier:** [Beat This!](https://github.com/CPJKU/beat_this), version 1.1.0, for joint beat and downbeat inference.

- Its [primary paper](https://arxiv.org/abs/2407.21658) reports state-of-the-art beat/downbeat F-measure across multiple datasets without a dynamic Bayesian postprocessor, while also documenting harder genres and continuity limitations.
- The official project provides an approximately 8 MB small model and approximately 78 MB full model, and can run locally on CPU or GPU.
- Code and released model weights are MIT-licensed according to the project. Training-data files have separate terms; do not redistribute training material by implication.
- The current [PyPI release](https://pypi.org/project/beat-this/) is 1.1.0, published 2026-04-14. This is much fresher than madmom or aubio, but still requires pinned Torch/runtime versions and model checksums.

For reproducibility, default release analysis to CPU, fixed thread counts, deterministic Torch settings, and a vendored weight file whose SHA-256 is in the sidecar. GPU inference may be offered as a faster, tolerance-tested mode rather than the canonical build path.

### Meter

There is no low-risk drop-in meter detector among the inspected mature libraries.

- Derive candidate meter regions from Beat This! downbeats and the count/stability of intervening beats.
- Emit `numerator`, start/end sample, confidence, and evidence. Permit `unknown`, and avoid pretending this determines denominator or notated meter.
- Detect changes only after sustained evidence; do not rewrite the entire track from one anomalous bar.
- Evaluate 3/4, 4/4, 6/8, compound-meter, pickup, rubato, and speech-plus-music fixtures separately.

Essentia's official [`Meter`](https://essentia.upf.edu/reference/std_Meter.html) reference marks the algorithm experimental, unevaluated, and “do not use.” That is disqualifying for a production truth source. `madmom` has a DBN downbeat processor that supports candidate beats-per-bar, but its model/data licensing makes it a poor commercial default (see matrix).

### Musical sections

Separate two different products:

1. **Structural boundaries:** changes in timbre/harmony/texture, without naming the section.
2. **Functional labels:** intro, verse, chorus, bridge, outro, etc.

For baseline boundaries, compute beat-synchronous chroma/MFCC/energy features, a recurrence or self-similarity representation, and deterministic segmentation. Librosa exposes [recurrence and agglomerative segmentation tools](https://librosa.org/doc/0.11.0/segment.html). The resulting boundaries remain estimates and should carry confidence.

For functional labels, [All-In-One Music Structure Analyzer](https://github.com/mir-aidj/all-in-one) is the most directly scoped candidate: its [paper](https://arxiv.org/abs/2307.16425) jointly predicts tempo, beats, downbeats, section boundaries, and functional labels. It is not recommended as the baseline because it brings PyTorch, NATTEN, Demucs, Hydra/OmegaConf, Hugging Face tooling, librosa, and a Git-installed madmom dependency. Its model/domain assumptions are aimed at songs, so audiobook beds, underscore, and non-pop forms need an in-domain evaluation. Treat it as an optional offline experiment behind a separate bundle-size, model, transitive-license, and maintenance review.

Essentia [`SBic`](https://essentia.upf.edu/reference/streaming_SBic.html) can find statistically homogeneous feature segments. It does not produce trustworthy verse/chorus semantics and should be labeled accordingly.

### Loudness and energy

**Recommended canonical loudness:** FFmpeg's [`ebur128` filter](https://ffmpeg.org/ffmpeg-filters.html#ebur128). It exposes momentary, short-term, integrated loudness, LRA, and optional true-peak analysis, and can emit metadata at 100 ms intervals. Preserve multichannel canonical audio for this pass.

**Recommended animation energy:** fixed-hop float PCM features, stored independently of loudness:

- RMS and dBFS RMS;
- peak absolute sample;
- log-power bands using a documented FFT window and bin weighting;
- spectral flux/onset strength;
- optional mel-band or perceptual-band summaries.

Use fixed-size windows and hops in samples, not one calculation per rendered frame. Define center/padding behavior and whether timestamps refer to window start or center. Apply attack/release smoothing only at presentation time with seconds-based coefficients, so smoothing feels similar at 60 Hz and 120 Hz.

### Media-clock synchronization

For the existing HTML `<audio>` architecture:

1. Treat `audio.currentTime` as the authoritative media position.
2. On every animation frame, binary-search the sidecar for enclosing beat, bar, onset, section, and envelope samples.
3. Compute phase directly: `beatPhase = (t - beat[i]) / (beat[i+1] - beat[i])`. Derive bar phase from downbeat and beat index.
4. On `seeking`, `seeked`, `pause`, `play`, `ratechange`, `ended`, source replacement, and visibility recovery, discard presentation transients and recompute from the current media position.
5. Never schedule future musical events with long-lived `setTimeout` calls. Timers may wake late; the next frame should query present truth.

If playback later moves fully into Web Audio, anchor source start/offset to `AudioContext.currentTime`. Use `getOutputTimestamp()` to map context time to `performance.now()` for output-aware visual scheduling. A `MediaElementAudioSourceNode` remains slaved to the media element and is resampled to the context sample rate as specified by [Web Audio](https://www.w3.org/TR/webaudio-1.1/#MediaElementAudioSourceNode).

The visual layer may interpolate and ease values, but event identity must always come from media/sample time. This makes pause, seek, replay, dropped frames, and refresh-rate differences converge to the same state.

## Dependency comparison

| Dependency | Best use | Accuracy / determinism | Local-first privacy | License considerations | Maintenance signal (2026-07-13) | Disposition |
|---|---|---|---|---|---|---|
| FFmpeg | Decode, resample, EBU R128 loudness | Mature and highly configurable; deterministic only when build, arguments, and thread behavior are pinned | Fully local | LGPL 2.1+ baseline; GPL options and possible patents require build-specific review | Active, broad format/filter support | **Adopt**, pinned subprocess build |
| SoundFile + libsndfile | WAV/FLAC/canonical PCM I/O | Straightforward sample-accurate block reads | Fully local | Python BSD-3; libsndfile LGPL notices/terms apply | SoundFile 0.13.1 docs/current release line | **Adopt** for PCM I/O |
| PyAV | In-process FFmpeg decode | Precise frame access; more ABI/build coupling than subprocess | Fully local | BSD-3 binding plus linked FFmpeg obligations | Active wheels track stable FFmpeg | **Optional**, only for justified in-process needs |
| librosa 0.11 | Onsets, tempo/beat baseline, RMS/features, structural boundaries | Transparent algorithms and fixed-hop repeatability; not best-in-class downbeat/meter | Fully local | ISC | Current stable release is 0.11.0 | **Adopt** baseline, pin full numerical stack |
| Beat This! 1.1.0 | Beat and downbeat inference | Strong published accuracy; model/runtime must be pinned; CPU is easiest canonical path | Fully local after weights are installed | MIT code/released weights; training data is separate | Release 1.1.0 published 2026-04-14 | **Adopt optional accuracy tier** |
| All-In-One | Joint beats/downbeats and functional song sections | Broad model output; domain and decoder offsets require evaluation | Local after model install, but model downloads must be controlled | Project MIT; transitive model/dependency terms, including madmom, need audit | Active research project; heavy stack | **R&D only**, separate gate |
| Essentia | Broad DSP/MIR, rhythm, onsets, EBU loudness, boundaries | Strong breadth; meter algorithm explicitly unevaluated; release/config pinning needed | Fully local | AGPL-3; commercial/proprietary use requires legal/product decision | Active repository/docs, but beta-style release history complicates pinning | **Do not use by default** |
| madmom 0.16.1 | Beat/downbeat/tempo neural models | Historically strong, but old runtime/model stack | Fully local | Source BSD-like; bundled model/data files CC BY-NC-SA 4.0, a commercial blocker without permission | Latest PyPI package published 2018-11-14 | **Reject production default** |
| aubio 0.4.9 | Lightweight streaming onsets/tempo | Useful low-latency DSP, but older algorithms/tooling | Fully local | GPL-3 | Latest PyPI release published 2019-02-08 | **Reject production default** |
| Native Web Audio `AnalyserNode` | Live cosmetic spectrum/RMS/transient texture | Low latency; analyser bytes, adaptive normalization, and RAF cadence are not a canonical analysis | Fully local | Browser platform API | Standards-backed and maintained by browsers | **Keep as cosmetic overlay**, rename claims |

License notes are engineering risk flags, not legal advice. Distribution must inventory the exact binaries, model weights, notices, build flags, and transitive dependencies actually shipped.

## Proposed sidecar contract

Store integer sample positions as canonical truth and derive seconds for convenience. A minimal JSON shape is:

```json
{
  "schema_version": 1,
  "source_sha256": "...",
  "canonical_pcm_sha256": "...",
  "sample_rate_hz": 44100,
  "duration_samples": 0,
  "decoder": {
    "name": "ffmpeg",
    "version": "...",
    "build_configuration_sha256": "...",
    "arguments": ["..."]
  },
  "analysis": {
    "pipeline_version": "...",
    "packages": {"librosa": "0.11.0"},
    "model_sha256": null,
    "config_sha256": "..."
  },
  "beats_samples": [],
  "downbeats_samples": [],
  "tempo_regions": [],
  "meter_regions": [],
  "onsets_samples": [],
  "sections": [],
  "loudness": {
    "integrated_lufs": null,
    "lra_lu": null,
    "true_peak_dbtp": null
  },
  "envelopes": {
    "hop_samples": 441,
    "rms_dbfs": [],
    "onset_strength": [],
    "bands_db": []
  }
}
```

Every inferred region/event should include method and confidence where the schema permits. Unknown is a valid result. Do not make cache validity depend only on file name, modification time, or duration.

## Determinism and privacy controls

- Decode to canonical PCM once; never compare results produced from different implicit browser/OS MP3 decoders.
- Pin decoder build, Python lockfile, numerical libraries, algorithm parameters, model bytes, and sample/channel policy.
- Use fixed windows/hops and integer sample indices throughout analysis.
- Set and record thread counts. Use deterministic Torch controls and CPU for the canonical Beat This! artifact; separately tolerance-test accelerated modes.
- Serialize finite values with a specified precision and ordering, then hash the sidecar.
- Vendor approved model weights or install them explicitly. Disable runtime auto-downloads and verify checksums before load.
- Make an offline test fail any unexpected network attempt. None of the recommended analysis requires cloud audio upload.
- Keep raw audio and analysis in the local project/data boundary. Logs should contain hashes and diagnostics, not extracted speech or audio payloads.

## Acceptance tests

1. **Decode fixture:** each supported container decodes to the expected canonical PCM hash, frame count, and channel layout with the release FFmpeg build.
2. **Repeatability:** the same input analyzed twice in clean processes produces byte-identical event indices and sidecar metadata. ML outputs may use an explicit numeric tolerance only if the canonical CPU mode cannot be exact.
3. **Seek convergence:** randomized seeks, pause/resume, playback-rate changes, and source reloads yield the same visual state as starting directly at that media time.
4. **Render-cadence independence:** 30, 60, 120, and irregular frame schedules select identical beat/bar/section events at the same media times.
5. **Background recovery:** after simulated RAF suspension, the first resumed frame queries current media time; it does not replay queued pulses.
6. **Clock mapping:** Web Audio playback tests compare `getOutputTimestamp()` context/performance mapping against scheduled visual events and record output-latency bounds.
7. **Beat/downbeat corpus:** measure precision, recall, F-measure, and continuity on in-domain audiobook music beds, speech-over-music, sparse/rubato material, and common song meters.
8. **Meter abstention:** ambiguous/polymetric/pickup examples return low confidence or `unknown`, not forced 4/4.
9. **Section evaluation:** score boundary tolerance separately from functional-label agreement; include non-pop and audiobook underscore.
10. **Loudness conformance:** verify integrated loudness, LRA, and true peak with official/known EBU test material and the pinned FFmpeg build.
11. **Privacy:** analysis succeeds with network disabled and fails closed if an unverified model is missing.
12. **Licensing:** generated bill of materials records FFmpeg configuration, shared libraries, Python packages, model files, checksums, licenses, notices, and redistribution decision.

## Delivery order

1. Define the sidecar schema, canonical decode command, hashes, and fixture corpus.
2. Implement fixed-hop RMS/bands/onset plus FFmpeg EBU R128 output.
3. Add librosa tempo/beat and deterministic structural boundaries.
4. Make PrismGT consume the sidecar from `audio.currentTime`; retain the live analyser as a separately named texture layer.
5. Make WizardJoe consume the same event/envelope model through its deterministic simulation timeline.
6. Evaluate Beat This! on the in-domain corpus, then enable it as the optional canonical beat/downbeat provider if it clears accuracy, latency, packaging, and repeatability gates.
7. Evaluate meter inference and All-In-One section labels only after the event-clock and baseline pipeline are proven.

## Primary source index

- [W3C Web Audio API 1.1](https://www.w3.org/TR/webaudio-1.1/)
- [WHATWG HTML media element playback position](https://html.spec.whatwg.org/multipage/media.html#dom-media-currenttime-dev)
- [W3C Media Timed Events](https://www.w3.org/TR/media-timed-events/)
- [ITU-R BS.1770-5](https://www.itu.int/rec/R-REC-BS.1770-5-202311-I/en)
- [EBU Tech 3341: Loudness Metering](https://tech.ebu.ch/publications/tech3341)
- [EBU Tech 3342: Loudness Range](https://tech.ebu.ch/publications/tech3342)
- [FFmpeg formats](https://ffmpeg.org/general.html#File-Formats), [`ebur128`](https://ffmpeg.org/ffmpeg-filters.html#ebur128), and [legal/licensing](https://ffmpeg.org/legal.html)
- [SoundFile documentation](https://python-soundfile.readthedocs.io/en/latest/)
- [PyAV official repository](https://github.com/PyAV-Org/PyAV) and [license documentation](https://pyav.org/docs/stable/development/license.html)
- [librosa documentation](https://librosa.org/doc/0.11.0/index.html), [segmentation API](https://librosa.org/doc/0.11.0/segment.html), and [license](https://github.com/librosa/librosa/blob/main/LICENSE.md)
- [Beat This! repository](https://github.com/CPJKU/beat_this), [paper](https://arxiv.org/abs/2407.21658), and [PyPI release](https://pypi.org/project/beat-this/)
- [All-In-One repository](https://github.com/mir-aidj/all-in-one) and [paper](https://arxiv.org/abs/2307.16425)
- [Essentia RhythmExtractor2013](https://essentia.upf.edu/reference/std_RhythmExtractor2013.html), [Onsets](https://essentia.upf.edu/reference/std_Onsets.html), [Meter](https://essentia.upf.edu/reference/std_Meter.html), [SBic](https://essentia.upf.edu/reference/streaming_SBic.html), and [LoudnessEBUR128](https://essentia.upf.edu/reference/std_LoudnessEBUR128.html)
- [madmom repository](https://github.com/CPJKU/madmom), [license](https://github.com/CPJKU/madmom/blob/master/LICENSE), [releases](https://github.com/CPJKU/madmom/releases), and [PyPI record](https://pypi.org/project/madmom/)
- [aubio repository](https://github.com/aubio/aubio), [releases](https://github.com/aubio/aubio/releases), and [PyPI record](https://pypi.org/project/aubio/)
