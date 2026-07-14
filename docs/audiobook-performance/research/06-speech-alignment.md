# Speech Recognition and Alignment for Audiobook Performance

**Role:** Speech Recognition and Alignment Engineer
**Date:** 2026-07-13
**Scope:** Read-only audit of `WizardJoeAvatar-python` and the adjacent PrismGT checkout, plus primary-source research. No production code or dependency files were changed.

## Executive decision

Build speech recognition and alignment as a **separate, local, deterministic authoring pipeline**, not as an import inside the Wizard Joe FastAPI process.

The preferred timing source order is:

1. **Provider-native alignment for generated TTS**, when it is available and bound to the exact audio bytes. PrismGT already receives ElevenLabs character timestamps for locally cached generated tracks. Preserve these timestamps, verify the resulting transcript locally, and do not replace good source timing with Whisper timing.
2. **Forced alignment of the approved transcript to the final audio** for imported or externally recorded chapters. Use a pinned local aligner and keep the approved transcript authoritative.
3. **Local ASR plus word alignment** only when no trustworthy transcript exists. ASR is evidence about what was spoken; it must not silently overwrite authored text.
4. **Duration-only mouth motion** remains a last-resort playback fallback. It is not an acceptable source for release captions or word-synchronous performance.

For the practical first implementation, use a locked Python 3.11 authoring environment with **faster-whisper** for local ASR/VAD and **WhisperX alignment** for an initial word-timing implementation. Keep **Montreal Forced Aligner (MFA)** as the release-quality fallback/evaluation candidate for approved English transcripts. Continue using the existing `whisper.cpp` binary for short live PrismGT STT, but do not promote its explicitly experimental word timestamps into the audiobook master.

The output should be one canonical, versioned `alignment.v1.json` containing word times, provenance, confidence evidence, transcript revision, hashes, and QA disposition. Generate WebVTT/SRT and the avatar's compact speech-performance track from that artifact. Never make captions and animation consume separate unversioned timing calculations.

## 1. Code-grounded audit

### 1.1 Python repository dependency boundary

The Python project currently declares only:

- `fastapi>=0.111`
- `uvicorn[standard]>=0.30`
- `pillow>=10`

This is identical in `pyproject.toml:6-10` and `requirements.txt:1-3`. There is no ASR, audio decoder, numerical, ML, forced-alignment, subtitle, or evaluation dependency. `uv lock --check` succeeds. The lock contains separate resolutions for Python 3.9 and Python 3.10+, which is expected because `requires-python = ">=3.9"` is broad and the direct requirements have no upper bounds. On the audited machine, `python3` and the repository `.venv` resolve to Python 3.9.6.

That boundary should remain intact:

- Current WhisperX requires Python `>=3.10,<3.14` and directly brings CTranslate2, faster-whisper, PyTorch, TorchAudio, TorchVision, TorchCodec, Transformers, pandas, NLTK, and pyannote-audio ([WhisperX `pyproject.toml`](https://github.com/m-bain/whisperX/blob/main/pyproject.toml)).
- faster-whisper itself supports Python 3.9+, but still introduces CTranslate2, model assets, and audio decoding ([faster-whisper README](https://github.com/SYSTRAN/faster-whisper)).
- None of that belongs on the avatar server's startup, deployment, or live rendering path.

**Dependency recommendation:** create a separately locked tool environment such as `tools/speech-alignment/` with Python 3.11. Invoke it as an offline command/subprocess. The production package and `requirements.txt` should not import or install the ML stack.

### 1.2 Wizard Joe's current speech and caption path

The Python avatar has a speech lifecycle, not a recognition/alignment system:

1. `WizardState` stores only `speech_id`, the entire `speech_text`, and `speech_until`; it has no audio identity, segment list, word times, confidence, transcript revision, or alignment provenance (`wizard_avatar/models.py:123-143`).
2. `_cmd_speak` derives a fallback duration as `max(1200, len(text) * 70)`, stores the whole text, opens a small mouth, and marks the body as speaking (`wizard_avatar/controller.py:328-339`).
3. Timer expiry clears speech and caption text (`wizard_avatar/controller.py:94-109`); `speech_stop` does the same immediately (`wizard_avatar/controller.py:312-318`).
4. `POST /api/avatar/wizard/speak` and `/speech-stop` only forward semantic commands (`wizard_avatar/server.py:120-123,165-171`).
5. The browser polls state every 125 ms and assigns `state.speech_text` directly to one live-region element (`web/avatar/wizardControls.ts:41,194-201`). Browser TTS and server speech timing are started separately, and browser voice timing varies (`web/avatar/wizardControls.ts:216-229`).
6. The speech/caption lifecycle has focused test coverage (`tests/wizard/test_game_control.py:162-179`), but no test exercises audio, words, cue boundaries, seeking, transcript correction, or confidence.

This is sufficient for short demo lines. It cannot drive release captions, seekable audiobook playback, word emphasis, or viseme timing.

### 1.3 Prism visual advisory is intentionally not a transcript channel

Prism signals are content-free animation advice. The parser accepts bounded enums and counters but explicitly rejects keys containing `prompt`, `reply`, `message`, `content`, `snippet`, `retrieved_text`, `path`, `hash`, and other sensitive or authority-bearing fragments (`wizard_avatar/prism_signals.py:12-31,64-143,161-191,223-230`).

That boundary is correct. Do not put audiobook transcript text, words, alignment records, file paths, or audio hashes into `visual_advisory_only` messages. The audiobook player or speech-performance scheduler should read a local timing artifact and send only the minimal playback state the renderer needs.

### 1.4 PrismGT static media path

The adjacent `prism-geometry-talk-persona-visuals` checkout defines hosted media outside the Git checkout:

```text
/var/lib/prism-gt/media/
  library.json
  music/
  podcasts/
  stories/
  transcripts/
```

`PRISM_MEDIA_ROOT` makes `/api/library` load `library.json` and `/media/*` serve bounded relative files (`media/README.md:1-22`; `crates/prism-cdiss-cli/src/web.rs:1117-1202,4704-4792`). Podcast chapter source layout is:

```text
media/podcasts/<show>/<chapter>/
  metadata.json
  audio.wav | audio.mp3
  transcript.txt
  captions.srt | captions.vtt   # optional today
```

The checked-in `why-i-wrote-the-constitution` show has 14 chapters and all four files (`audio.wav`, `transcript.txt`, `captions.srt`, `metadata.json`) in every chapter. A chapter's metadata names those files but contains no duration, audio hash, transcript hash/revision, generator, model, alignment source, confidence summary, or QA disposition. See `media/podcasts/why-i-wrote-the-constitution/00-why-i-wrote-the-constitution/metadata.json:1-10`.

Important wiring detail: chapter-local `metadata.json` is not auto-discovered by `/api/library`. The endpoint only reads the root `library.json`, a configured manifest, or `library.example.json` (`web.rs:1117-1194`). The checked-in example does not list the 14 constitution chapters (`media/library.example.json:1-80`). Deployment may supply a separate live manifest, but repository-local chapter presence alone does not make a track selectable.

### 1.5 PrismGT caption consumption

The media UI normalizes manifest fields `captionsUrl` and `transcriptUrl` (`src/pages/PrismDodecahedron/musicLibrary.js:33-77`). The miniapp:

1. Fetches only `captionsUrl`, not `transcriptUrl`, for timed display (`src/miniapp/main.js:1067-1093`).
2. Accepts SRT-like comma timestamps because `parseVttTime` converts commas to periods; `parseTimedText` otherwise treats the file as WebVTT (`src/lib/captions-vtt.js:3-45,86-101`).
3. Flattens each cue's text lines and does not remove arbitrary SSML (`captions-vtt.js:29-42`).
4. Simulates word reveal within a cue by distributing whitespace tokens over cue duration (`src/miniapp/main.js:954-973,1338-1350`). Those reveal times are typography heuristics, not word timestamps.

This last point is crucial: a caption cue that spans five seconds does not provide five seconds of word alignment. The current UI manufactures word progress from text length and punctuation.

### 1.6 Static caption evidence

A structural audit of all 14 checked-in SRT files found:

| Check | Result |
|---|---:|
| Total cues | 467 |
| Non-monotonic/overlapping cues | 0 |
| More than two text lines | 0 |
| Maximum line length | 41 characters |
| Final caption end versus audio duration | within about 20 ms for all 14 chapters |
| Cues shorter than 5/6 second | 23 |
| Cues longer than 7 seconds | 1 |
| Cues above proposed 20 characters/second | 39 |
| Minimum/maximum cue duration | 0.164 s / 7.912 s |
| Cues containing SSML-like tags | 14 |

The timing envelope and line layout are orderly, but the files are not release-clean:

- Every chapter leaks at least one `<break time="..."/>` token into visible SRT text. The sample does so at `captions.srt:7-8`, and the current parser will render it as text.
- The files have no preserved word alignment or generation provenance. Their close match to audio duration proves structural consistency, not acoustic word-boundary accuracy.
- 24 cues violate Netflix's official 5/6-second minimum or seven-second maximum, and 39 exceed the project's proposed reading-speed gate. Netflix's general timed-text guide specifies a 5/6-second minimum, seven-second maximum, and two lines maximum ([Netflix Timed Text Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements)).
- WebVTT requires ordered starts and an end greater than the start; it is the web-native time-aligned text container PrismGT should emit ([W3C WebVTT](https://www.w3.org/TR/webvtt1/)).

### 1.7 PrismGT generated and imported audiobook paths

PrismGT has a second, dynamic audiobook store under:

```text
<app_data>/audiobooks/
  index.json
  tracks/<track_id>/
    audio.mp3
    metadata.json
    captions.vtt       # when alignment exists
    alignment.json     # when alignment exists
```

This comes from `AudiobookStore::new(data_dir).root = data_dir/audiobooks` and `tracks_root()` (`crates/prism-cdiss-cli/src/audiobooks.rs:242-251,537-548`). Writes use a temporary sibling plus rename (`audiobooks.rs:990-997`), which is a good atomic-publication pattern.

There are two materially different ingestion paths:

**Direct ElevenLabs generation:** PrismGT calls the provider's `with-timestamps` endpoint, receives character start/end arrays, groups them into caption cues, writes `alignment.json` and `captions.vtt`, and exposes `/api/audiobooks/:track_id/captions.vtt` (`audiobooks.rs:277-350,835-953`; `web.rs:7101-7115`). This is alignment tied to the generated audio and should be retained.

**ElevenLabs Studio chapter import:** the cache key includes project, chapter, and snapshot ID and supports `force`, but the imported audio is stored with `duration_seconds: None`, `captions_url: None`, no transcript preview, no `captions.vtt`, and no `alignment.json` (`audiobooks.rs:353-445`). This is the clearest immediate alignment gap.

Direct generation also lacks content-addressed reuse: every generation creates a random UUID even for identical text/voice/model/settings. Studio import deduplicates by snapshot identity, but neither path records the final audio SHA-256 or an alignment toolchain fingerprint.

### 1.8 Existing PrismGT live STT is separate

PrismGT already supports short speech input through hosted OpenAI STT or local `whisper.cpp` (`crates/prism-cdiss-cli/src/voice.rs:1-4,64-86`). The local path discovers a `whisper-cli` binary and GGML model, converts input with FFmpeg, transcribes, then returns cleaned text (`voice.rs:109-149,208-222,296-338,795-807`). Its output contract is a transcript string, not timed words or a reusable caption artifact.

Do not overload `/api/stt` for multi-minute chapter alignment. Keep live prompt recognition low-latency and disposable; keep audiobook alignment resumable, content-addressed, auditable, and batch-oriented.

## 2. What the primary sources establish

### 2.1 Local Whisper and confidence evidence

OpenAI Whisper processes audio in 30-second model windows. Its current transcriber can emit word timestamps by applying cross-attention patterns and dynamic time warping; it also emits per-segment `avg_logprob`, `compression_ratio`, and `no_speech_prob` ([OpenAI `transcribe.py`](https://github.com/openai/whisper/blob/main/whisper/transcribe.py)). The same source uses defaults of:

- compression ratio threshold `2.4`
- average log-probability threshold `-1.0`
- no-speech probability threshold `0.6`, in combination with low log probability
- temperature fallback `(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)`

These are decoding/fallback diagnostics, not calibrated guarantees that a word is correct. Treat them as reasons to review or retry, never as sole auto-approval criteria.

OpenAI Whisper's code and model weights are MIT licensed ([official repository](https://github.com/openai/whisper)). Loading a named model downloads it into `~/.cache/whisper` by default and verifies the SHA-256 embedded in the model URL; loading a local checkpoint path avoids that fetch ([official loader source](https://github.com/openai/whisper/blob/main/whisper/__init__.py)). A process is not strictly offline merely because inference is local: models must be staged first and network access must be disabled during the run.

### 2.2 Word timestamps are not all forced alignment

Three categories must remain distinct:

1. **Decoder/token timing:** native Whisper segment timestamps and `whisper.cpp` token timing. Useful and lightweight, but not constrained to an approved transcript.
2. **Attention-derived word timing:** OpenAI Whisper and faster-whisper word timestamps. Better granularity, still based on ASR output.
3. **Forced alignment:** fit known transcript tokens/phones to acoustic evidence. This is the correct operation when narration text is already approved.

The project must not label all three `alignment` without a provenance field.

### 2.3 Long-audio chunking

The WhisperX paper identifies buffered/sliding long-form Whisper failure modes including drift, hallucination, and repetition. Its method uses VAD cut-and-merge plus forced phoneme alignment and reports improved long-form quality and much faster batched inference ([Bain et al., *WhisperX: Time-Accurate Speech Transcription of Long-Form Audio*](https://arxiv.org/abs/2303.00747)). The maintained implementation uses VAD-based segment transcription, disables previous-text conditioning by default to reduce hallucination, and then aligns words ([WhisperX repository](https://github.com/m-bain/whisperX)).

faster-whisper exposes word timestamps and integrates Silero VAD; its conservative default removes silence longer than two seconds, and its batched mode enables VAD by default ([faster-whisper README](https://github.com/SYSTRAN/faster-whisper)).

For an audiobook, chunking should therefore be acoustic first and text-aware second:

- detect speech regions locally;
- add 250 ms context on each side without crossing file bounds;
- target 15-25 second ASR chunks;
- hard cap ASR chunks at 30 seconds unless the selected engine documents a different safe limit;
- split at silence/punctuation anchors, not fixed wall-clock boundaries alone;
- retain absolute sample offsets and reconcile overlap deterministically;
- never condition an entire book on all prior decoded text;
- align approved text within bounded chapter/paragraph windows, not as one hours-long trellis.

### 2.4 Transcript verification

ASR verification compares the approved display transcript with a local ASR hypothesis after two explicit normalizations:

- **semantic normalization:** case, Unicode normalization, whitespace, quote variants, and approved spoken forms for numerals/abbreviations;
- **display normalization:** remove synthesis-only SSML such as `<break>`, but preserve punctuation and wording used for captions.

Compute WER and CER with a pinned transform pipeline. JiWER provides WER, CER, MER, WIL, and edit details using minimum edit distance and is Apache-2.0 licensed ([JiWER repository](https://github.com/jitsi/jiwer)). Store the transform name/version and the actual insertion/deletion/substitution spans. A single WER scalar is insufficient for names, numbers, negation, or quoted language.

Verification must be asymmetric:

- The authored transcript is the reference.
- ASR is the hypothesis.
- A mismatch creates a review item; it does not rewrite the reference.
- Exact-match classes such as names, numbers, URLs, negations, and chapter titles receive separate checks.
- Silence regions are tested for hallucinated insertions.

### 2.5 Forced alignment options

WhisperX combines faster-whisper ASR, VAD, and language-specific wav2vec2 forced alignment. It is convenient and BSD-2-Clause licensed, but its own documentation notes that unsupported dictionary characters may be unaligned, overlapping speech is weak, and a language-specific alignment model is required ([WhisperX limitations](https://github.com/m-bain/whisperX#limitations-)). Current releases require Python 3.10+ and a substantial Torch stack.

MFA aligns a corpus using a pronunciation dictionary and acoustic model, can generate JSON/CSV/TextGrid, can flag out-of-vocabulary words, and supports alignment analysis and comparison to gold references ([MFA alignment guide](https://montreal-forced-aligner.readthedocs.io/en/latest/user_guide/workflows/alignment.html)). MFA code is MIT licensed; its maintained model collection is CC BY 4.0 ([MFA repository](https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner), [MFA models](https://github.com/MontrealCorpusTools/mfa-models)). It has more operational machinery than WhisperX but is a strong final-alignment and benchmark candidate when a clean transcript exists.

Do not build directly on TorchAudio's forced-alignment API for a new implementation: the official docs deprecated those APIs in 2.8 and scheduled removal in 2.9 ([TorchAudio forced alignment tutorial](https://docs.pytorch.org/audio/2.8.0/tutorials/ctc_forced_alignment_api_tutorial.html)). WhisperX may currently pin TorchAudio 2.8 internally, but that is an upstream compatibility risk to isolate behind the tool adapter.

### 2.6 Privacy is a runtime property

Strict-local mode requires all of the following:

- model and tokenizer artifacts staged from an approved source before processing;
- model file hash and model revision recorded;
- `HF_HUB_OFFLINE=1` for Hugging Face-backed tools; official Hub docs state this prevents HTTP calls and fails when an artifact is absent ([Hugging Face offline mode](https://huggingface.co/docs/huggingface_hub/package_reference/utilities));
- no diarization model or token when the audiobook is single-speaker;
- no OpenAI/ElevenLabs call from verification/alignment jobs;
- subprocess environment allowlist and network-denied execution where feasible;
- temporary PCM/chunks under a mode-0700 job directory, deleted after atomic publication;
- logs containing IDs, hashes, counts, and metrics, never transcript bodies;
- no transcript or word payload through the Prism visual-advisory channel.

Direct ElevenLabs generation is intentionally remote TTS and therefore not a strict-local creation path. Local verification can still occur after audio generation. The report's local guarantee applies to ASR/alignment, not to the pre-existing TTS provider call.

## 3. Practical tool and licensing comparison

| Tool | Best role here | Word timing/alignment | Local/macOS practicality | License notes | Decision |
|---|---|---|---|---|---|
| OpenAI Whisper | Reference implementation and verification baseline | Cross-attention + DTW word timestamps; ASR-derived | Python/PyTorch/FFmpeg; supports Python 3.9 | Code and official weights MIT | Keep as benchmark, not default production tool |
| faster-whisper | Default local ASR, VAD, confidence evidence | Word timestamps; ASR-derived, not forced to approved text | Python 3.9+; CTranslate2; PyAV bundles FFmpeg libraries; local model directory supported | MIT code; record model artifact license/revision separately | **Adopt for verification** |
| whisper.cpp | Existing live PrismGT STT and low-footprint fallback | Repository labels `-ml 1` word timestamps **experimental** | Excellent Apple Silicon support through NEON, Accelerate, Metal, and optional Core ML | MIT code; converted Whisper weights retain model terms | Keep for live STT; reject as release master timing ([official repo](https://github.com/ggml-org/whisper.cpp)) |
| WhisperX | First practical ASR + VAD + word-forcing adapter | wav2vec2 forced alignment after ASR/VAD | CPU works on macOS, but current Python 3.10+ and Torch stack are heavy | BSD-2-Clause code; transitive/model licenses vary; pyannote diarization is unnecessary here | **Adopt in isolated authoring environment, pin exact version** |
| Montreal Forced Aligner | Approved-transcript alignment, difficult/OOV chapters, gold evaluation | Dictionary/acoustic-model phone and word alignment | Conda/Kaldi/Pynini setup is heavier; strong corpus tooling | MIT code; maintained models CC BY 4.0 and require attribution | **Evaluate as release fallback and benchmark** |
| JiWER | Verification metrics and edit spans | No timing | Small Python dependency, Python 3.8+ | Apache-2.0 | **Adopt in authoring environment** |
| aeneas | Legacy text/audio synchronization | Primarily fragment-level; docs warn word alignment can be inferior to ASR aligners | Old 2017 release, eSpeak/FFmpeg/native extensions | AGPL-3.0 | Reject for this product ([official repo](https://github.com/readbeyond/aeneas)) |
| Direct TorchAudio forced align | Low-level experimental implementation | CTC forced alignment | API removed/deprecated across current versions | BSD-style PyTorch ecosystem, but API lifecycle is the blocker | Reject as a direct new dependency |

FFmpeg remains useful for deterministic decoding/normalization, but distribution terms depend on build configuration: FFmpeg is LGPL 2.1+ by default and becomes GPL when GPL components are enabled ([FFmpeg legal page](https://ffmpeg.org/legal.html)). Record `ffmpeg -version` and configure flags in build evidence; do not assume every bundled binary has the same license posture.

**Licensing gate:** code license, model license, pronunciation dictionary license, and FFmpeg build license are separate inventory rows. A permissive Python package license does not grant terms for automatically downloaded models.

## 4. Canonical artifact contract

Use one JSON source of timing truth. SRT/VTT are delivery projections, not masters.

```json
{
  "schema_version": 1,
  "asset_id": "why-i-wrote-the-constitution-00",
  "generation_id": "sha256:<full alignment cache key>",
  "audio": {
    "source_sha256": "...",
    "pcm_sha256": "...",
    "sample_rate_hz": 16000,
    "channels": 1,
    "samples": 1969632,
    "duration_ms": 123102
  },
  "transcript": {
    "source_sha256": "...",
    "display_sha256": "...",
    "revision": 3,
    "normalizer_version": 1,
    "language": "en"
  },
  "engine": {
    "asr": "faster-whisper",
    "asr_version": "pinned",
    "asr_model": "pinned-id-or-local-path",
    "asr_model_sha256": "...",
    "aligner": "whisperx|mfa|elevenlabs-native",
    "aligner_version": "pinned",
    "alignment_model": "pinned-id",
    "alignment_model_sha256": "...",
    "offline": true,
    "parameters_sha256": "..."
  },
  "words": [
    {
      "index": 0,
      "text": "Paul",
      "normalized": "paul",
      "start_ms": 42,
      "end_ms": 381,
      "source": "forced_alignment",
      "asr_probability": 0.94,
      "alignment_score": null,
      "review": "accepted"
    }
  ],
  "qa": {
    "wer": 0.006,
    "cer": 0.002,
    "timed_word_coverage": 1.0,
    "low_confidence_word_count": 2,
    "unaligned_word_count": 0,
    "caption_gate": "pass",
    "reviewed_by": null,
    "reviewed_at": null
  }
}
```

Contract rules:

- Times are integer milliseconds relative to the exact decoded PCM start.
- Words are ordered and non-overlapping after deterministic normalization.
- Preserve raw engine output separately for debugging; consumers use only canonical output.
- Do not store only rounded SRT times; preserve word precision in JSON.
- Record both source audio hash and normalized PCM hash so codec/container-only changes are distinguishable from acoustic changes.
- Record transcript source, display, and spoken-normalized hashes separately. SSML affects synthesis but must not appear in display captions.
- Record tool versions, model revisions/hashes, parameters, and offline disposition.
- The compact avatar track is derived from words/phonemes and may omit text entirely once built.

## 5. Thresholds and release gates

These are **initial project gates**, chosen for clean, mostly single-speaker audiobook narration. They must be calibrated on a hand-checked in-domain benchmark before production approval. Model probabilities are not assumed calibrated.

### 5.1 Input and structural gates

| Metric | Pass | Review | Fail |
|---|---:|---:|---:|
| Decoded duration vs source probe | <= 50 ms difference | 51-100 ms | > 100 ms |
| Word timestamps outside `[0, duration + 50 ms]` | 0 | n/a | >= 1 |
| `end_ms <= start_ms` | 0 | n/a | >= 1 |
| Word overlap after normalization | 0 | <= 20 ms punctuation/coarticulation repair | > 20 ms or lexical overlap |
| Timed lexical-word coverage | >= 99.5% | 98.0-99.49% | < 98.0% |
| Unaligned critical token (name, number, negation, title) | 0 | n/a | >= 1 |
| Final word end vs audio duration | <= 250 ms when speech reaches tail | 251-750 ms | > 750 ms without known trailing room tone |

### 5.2 Transcript verification gates

| Metric | Auto-pass | Human review | Fail/rework |
|---|---:|---:|---:|
| Normalized chapter WER | <= 2.0% | > 2.0% to 5.0% | > 5.0% |
| Normalized chapter CER | <= 1.0% | > 1.0% to 2.0% | > 2.0% |
| Critical-token errors | 0 | 1 with explicit approval | > 1 |
| Hallucinated words in known silence > 1.0 s | 0 | 1 isolated | repeated/contiguous |

Also gate each paragraph. A good chapter average must not hide one badly aligned paragraph.

### 5.3 Confidence triage

- OpenAI-compatible segment `avg_logprob < -1.0`, compression ratio `> 2.4`, or the documented no-speech/low-logprob combination creates a hard review flag; these mirror upstream fallback defaults, not acceptance guarantees.
- Word probability `< 0.50` creates a hard review item.
- Word probability `0.50-0.75` creates a soft review item.
- Auto-pass requires the WER/CER/coverage gates even when all probabilities are high.
- Never average away a low-confidence proper noun, number, negation, or chapter title.
- Build a reliability plot on the gold corpus before changing these probability bands. Keep raw scores so future calibration does not require rerunning inference.

### 5.4 Boundary-accuracy benchmark

Create at least 10 minutes of manually checked audiobook audio spanning clean narration, pauses, names, numbers, quoted dialogue, breaths, SSML breaks, and music/room-tone transitions. Against gold word boundaries:

| Metric | Initial acceptance |
|---|---:|
| Median absolute start-boundary error | <= 80 ms |
| 95th percentile absolute start-boundary error | <= 200 ms |
| Median absolute end-boundary error | <= 100 ms |
| Boundary errors > 400 ms | 0 critical words; <= 0.2% all words |
| Chapter offset/drift | <= 100 ms at beginning, middle, and end checkpoints |

Compare at least faster-whisper word timing, WhisperX alignment, and MFA on the same gold set. Select by measured quality and operational cost, not README claims.

### 5.5 Caption projection gates

| Metric | Gate |
|---|---:|
| Cue duration | 5/6 second to 7 seconds; allow shorter only for a documented shot/transport constraint |
| Lines | <= 2 |
| Characters per line | <= 42 for the current Prism presentation |
| Reading speed | <= 20 characters/second initial project threshold |
| Cue overlap | 0 for this single-speaker player |
| Cue order | monotonic starts; every end > start |
| SSML/XML not allowed by WebVTT cue grammar | 0 |
| Caption text versus approved display transcript | exact after whitespace/line-break normalization |
| Last cue end | <= audio duration + 100 ms |

Caption segmentation should break at sentence/phrase boundaries and then satisfy display gates. It must not alter word timestamps to make layout convenient.

## 6. Correction workflow

### 6.1 Preserve three texts

Do not use one mutable text file for three jobs:

1. **Synthesis source:** may contain approved SSML and pronunciation controls.
2. **Approved display transcript:** human-readable words and punctuation; no synthesis markup.
3. **Spoken normalization:** deterministic token form used for WER and alignment, with an audit map back to display text.

The current `transcript.txt` files mix display prose and `<break>` tags. Migration should split those concerns without losing source text.

### 6.2 Review unit

Present review by paragraph/segment with:

- local audio playback and 1-2 seconds of context;
- approved text versus ASR hypothesis diff;
- word boundaries and confidence flags;
- explicit actions: accept timing, correct display text, mark pronunciation variant, split/merge, mark non-speech, rerun segment;
- immutable old revision and reviewer identity/time;
- keyboard-accessible nudge controls in 10 ms and 50 ms increments;
- a reason code for manual timing overrides.

Never edit generated SRT as the primary correction. Edit the approved transcript or word timing revision, then regenerate all delivery projections.

### 6.3 Localized realignment

After a transcript correction:

1. Find unchanged word anchors before and after the edited span.
2. Expand to the nearest stable silence/paragraph boundary, with at least 500 ms context.
3. Re-align only that bounded window.
4. Require the replacement window to preserve monotonicity and boundary continuity.
5. Rebuild affected caption cues and performance cues.
6. Re-run chapter structural QA and transcript hashes.

If fewer than two trustworthy anchors remain, realign the paragraph. If paragraph WER exceeds 5%, critical tokens remain unaligned, or drift exceeds 400 ms, realign the chapter rather than interpolating.

### 6.4 Source-of-truth conflict policy

- Audio changed, transcript did not: reverify and realign.
- Transcript corrected, audio did not: retain reusable PCM/ASR evidence, invalidate alignment and downstream projections.
- Provider character alignment and local forced alignment disagree: retain both as evidence; select one canonical source through QA, never merge silently.
- ASR wording disagrees with approved wording: flag for review; do not substitute automatically.
- Manual boundary edit: record override separately from machine output and keep it across caption-only rebuilds.

## 7. Cache invalidation design

Use layered content-addressed caches so a caption style change does not rerun ASR, while an audio change can never reuse stale timing.

### 7.1 Cache keys

```text
pcm_key = sha256(
  source_audio_sha256,
  decoder_name_version_and_build,
  sample_rate,
  channel_policy,
  sample_format,
  normalization_parameters
)

asr_key = sha256(
  pcm_sha256,
  asr_engine_version,
  model_id_and_sha256,
  language,
  vad_version_and_parameters,
  chunking_version_and_parameters,
  decoding_parameters,
  normalizer_version
)

alignment_key = sha256(
  pcm_sha256,
  approved_spoken_transcript_sha256,
  transcript_revision,
  aligner_version,
  alignment_model_id_and_sha256,
  pronunciation_lexicon_sha256,
  segmentation_version_and_parameters
)

caption_key = sha256(
  alignment_generation_id,
  approved_display_transcript_sha256,
  caption_formatter_version,
  language_style_profile,
  line_and_duration_limits
)

performance_key = sha256(
  alignment_generation_id,
  performance_reducer_version,
  viseme_map_version,
  simulation_tick_rate,
  quantization_parameters
)
```

### 7.2 Invalidation matrix

| Change | PCM | ASR | Alignment | Captions | Performance |
|---|---:|---:|---:|---:|---:|
| Container metadata only, decoded PCM unchanged | keep | keep | keep | keep | keep |
| Audio samples/edit/master changed | rebuild | rebuild | rebuild | rebuild | rebuild |
| Approved wording changed | keep | keep as evidence | rebuild affected scope | rebuild | rebuild affected scope |
| Punctuation/line-break display-only change | keep | keep | keep if spoken tokens unchanged | rebuild | keep unless phrase markers derive from punctuation |
| ASR engine/model/parameters changed | keep | rebuild | keep if independent forced alignment; otherwise rebuild | conditional | conditional |
| Aligner/model/lexicon changed | keep | keep | rebuild | rebuild | rebuild |
| Caption layout rule changed | keep | keep | keep | rebuild | keep |
| Viseme/performance reducer changed | keep | keep | keep | keep | rebuild |
| Manual word-boundary override | keep | keep | new alignment revision | rebuild affected cues | rebuild affected cues |

### 7.3 Publication and stale-result protection

- Run under `jobs/<job_id>/` and write outputs only there.
- Before publish, recompute the current source hashes. If they no longer match the job inputs, mark the job stale and do not publish.
- Validate JSON schema and every threshold before promotion.
- Publish the complete generation directory with atomic rename.
- Update one small `current.json` pointer atomically only after all files exist.
- Keep the previous accepted generation for rollback.
- Garbage-collect only generations not referenced by `current.json`, review records, or release manifests.
- Do not let a filename such as `captions.srt` imply freshness; its generation ID must match audio and transcript metadata.

The existing audiobook store's temporary-write-and-rename helper is a sound primitive (`audiobooks.rs:990-997`), but it needs generation-level atomicity and hash identity rather than independent file replacement.

## 8. Implementation plan

### Phase 0: freeze and measure

1. Preserve the 14 existing chapter sets unchanged as baseline evidence.
2. Add a read-only audit command that reports duration, cue structure, SSML leakage, text coverage, and manifest reachability.
3. Build the hand-checked 10-minute boundary/word benchmark.
4. Capture runtime, peak RSS, WER/CER, word coverage, boundary error, and model disk size for every candidate.

**Exit:** reproducible baseline report and gold data exist; no tool is selected from anecdote alone.

### Phase 1: isolated local toolchain

1. Create a Python 3.11 `uv` project for alignment tooling, separate from the avatar package.
2. Pin exact faster-whisper, WhisperX, JiWER, and transitive versions; record lock hash.
3. Stage models into an explicit local model directory with SHA-256 and license metadata.
4. Run with `HF_HUB_OFFLINE=1`; fail closed if any model is absent.
5. Add an optional MFA environment/adapter for comparison and fallback.

**Exit:** a network-denied smoke test processes one local WAV without changing the production environment.

### Phase 2: canonical text and artifact schema

1. Define synthesis source, display transcript, and spoken-normalized transcript.
2. Strip/translate SSML deterministically and retain a source-to-display map.
3. Implement `alignment.v1.json` schema and validator.
4. Add audio/PCM/transcript/model/toolchain hashes and generation IDs.
5. Import ElevenLabs character alignment into the same schema with `source = elevenlabs_native`.

**Exit:** provider and local alignment outputs validate against one consumer contract.

### Phase 3: local ASR verification

1. Normalize audio to mono 16 kHz PCM with recorded FFmpeg build/configuration.
2. Run faster-whisper with fixed language, VAD, chunking, and decoding parameters.
3. Compute WER/CER and critical-token diffs against the approved transcript.
4. Store segment diagnostics and word probabilities as evidence.
5. Generate review items; never auto-edit approved text.

**Exit:** clean chapters meet verification gates; seeded names/numbers/deletions produce deterministic review failures.

### Phase 4: forced alignment and long-audio reconciliation

1. Prefer native provider timing when audio hash and alignment source match.
2. For imports, align approved transcript in paragraph/VAD windows with overlap and absolute sample offsets.
3. Compare WhisperX and MFA on the gold corpus.
4. Implement OOV/pronunciation overrides and localized rerun.
5. Reject unanchored interpolation across long mismatches.

**Exit:** selected aligner meets boundary gates and has no critical unaligned words on the release corpus.

### Phase 5: caption and correction outputs

1. Segment canonical words into phrase/sentence cues.
2. Generate WebVTT as the browser delivery master and SRT as an export.
3. Enforce duration, line, reading-speed, monotonicity, and SSML gates.
4. Add local correction/review with immutable revisions and manual override provenance.
5. Regenerate captions from corrected canonical data.

**Exit:** the current 14-chapter defects are either corrected or explicitly waived; no synthesis tags render.

### Phase 6: cache and PrismGT integration

1. Implement layered cache keys and generation directories.
2. Add stale-job checks and atomic `current.json` promotion.
3. Add alignment status/provenance to chapter metadata and `/api/library` track data.
4. Ensure manifest generation includes every intended chapter; do not rely on directory discovery that does not exist.
5. Backfill Studio imports with local duration, transcript when available, alignment, and captions.
6. Keep `/api/stt` unchanged for live prompt recognition.

**Exit:** audio/transcript edits invalidate exactly the required layers, and a stale job cannot replace a newer accepted generation.

### Phase 7: Wizard Joe performance handoff

1. Derive a compact tick-quantized speech track from canonical timing.
2. Send word/viseme indices and emphasis/pause markers, not raw transcript, through the playback boundary.
3. Preserve duration-only fallback when no track is available.
4. Test seek, pause, resume, interruption, replacement, and chapter transition.
5. Prove captions, mouth state, and audio use the same generation ID and playback clock.

**Exit:** mouth closes on silence/interruption, seeks are deterministic, stale cues never return, and transcript content never enters Prism visual advisory messages.

## 9. Required tests

### Unit

- SSML-to-display normalization and source mapping.
- WER/CER transforms, including empty-silence hypotheses.
- Word monotonicity, coverage, overlap, and duration bounds.
- VAD/chunk offset reconciliation and overlap deduplication.
- Caption segmentation and WebVTT escaping.
- Every cache-key field and invalidation matrix row.
- Model/hash mismatch and offline missing-model failure.
- Manual correction revision and localized invalidation.

### Integration

- Existing ElevenLabs alignment import preserves character/word timing.
- Studio import gains a local alignment without calling a remote ASR service.
- 2+ hour chapter/book fixture resumes after interruption without duplicate words.
- Audio changes while a job runs; stale output is refused at publish.
- Transcript correction rebuilds alignment/captions but reuses unchanged PCM evidence.
- Browser seek selects the correct caption and speech cue from the same clock.
- SRT/VTT round-trip keeps approved text and legal cue timing.

### Adversarial corpus

- long silence and room tone;
- music under speech and music-only intervals;
- breaths, mouth noise, false starts, and repeated phrases;
- names, acronyms, numerals, currency, hyphenation, and quotations;
- SSML breaks and pronunciation tags;
- deliberate transcript insertion, deletion, and substitution;
- one corrupted/truncated audio file;
- multilingual phrase in an English chapter;
- overlapping speech, even if the expected disposition is manual review.

## 10. Risks and explicit non-goals

- **Probability misuse:** ASR probabilities are triage features, not truth. Release gates require transcript comparison and structural QA.
- **Model drift:** a model name without revision/hash is not reproducible.
- **Automatic downloads:** local inference can still make first-run network requests. Strict-local mode must fail closed.
- **WhisperX churn:** current dependencies include APIs already in maintenance/deprecation transition. Isolate and pin the adapter.
- **Model licensing:** package license and model license differ. Inventory both.
- **False precision:** millisecond JSON does not imply millisecond acoustic accuracy; benchmark actual boundary error.
- **Static media reachability:** chapter files are not selectable unless the root library manifest names them.
- **Content boundary:** transcript text belongs to media authoring/playback, not Prism's content-free visual advisory protocol.
- **No diarization by default:** current audiobooks are single-narrator. Diarization adds models, licenses, tokens, and error modes without present value.
- **No production dependency edits in this phase:** this report defines the work; implementation should proceed in the isolated tool environment after benchmark approval.

## 11. Final recommendation

Adopt a two-pass, local authoring workflow:

1. **Verify** final audio against the approved transcript with faster-whisper, VAD-aware long-audio chunking, JiWER diffs, and critical-token checks.
2. **Align** approved text using native ElevenLabs timing when available; otherwise use a pinned WhisperX adapter initially and evaluate MFA as the release-quality fallback on a gold corpus.
3. **Publish once** into a content-addressed `alignment.v1.json`, then derive WebVTT/SRT and avatar performance cues from that same generation.
4. **Review by exception**, with immutable transcript/timing revisions and localized realignment.
5. **Keep it private and reproducible** by staging hashed models, enforcing offline execution, minimizing logs, and retaining the existing Prism content-free advisory boundary.

This approach fills the current imported-chapter and static-caption gaps without burdening the avatar server, preserves high-value provider alignment, and makes correction, confidence, privacy, and cache freshness testable rather than implicit.

## Primary sources

1. OpenAI. [Whisper official repository and model license](https://github.com/openai/whisper).
2. OpenAI. [`transcribe.py`: 30-second windows, fallback diagnostics, and DTW word timestamps](https://github.com/openai/whisper/blob/main/whisper/transcribe.py).
3. OpenAI. [`load_model`: cache path, local path, download, and SHA-256 verification](https://github.com/openai/whisper/blob/main/whisper/__init__.py).
4. Radford, A. et al. [Robust Speech Recognition via Large-Scale Weak Supervision](https://arxiv.org/abs/2212.04356).
5. SYSTRAN. [faster-whisper official repository](https://github.com/SYSTRAN/faster-whisper).
6. Bain, M., Huh, J., Han, T., & Zisserman, A. [WhisperX: Time-Accurate Speech Transcription of Long-Form Audio](https://arxiv.org/abs/2303.00747).
7. Bain, M. et al. [WhisperX official repository, limitations, dependencies, and BSD-2-Clause license](https://github.com/m-bain/whisperX).
8. ggml-org. [whisper.cpp official repository, Apple acceleration, experimental word timestamps, and MIT license](https://github.com/ggml-org/whisper.cpp).
9. MontrealCorpusTools. [Montreal Forced Aligner official repository](https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner).
10. MontrealCorpusTools. [MFA alignment workflow and output/analysis options](https://montreal-forced-aligner.readthedocs.io/en/latest/user_guide/workflows/alignment.html).
11. MontrealCorpusTools. [MFA pretrained model collection and CC BY 4.0 license](https://github.com/MontrealCorpusTools/mfa-models).
12. PyTorch Audio. [CTC forced-alignment API tutorial and deprecation notice](https://docs.pytorch.org/audio/2.8.0/tutorials/ctc_forced_alignment_api_tutorial.html).
13. Jitsi. [JiWER metrics and Apache-2.0 license](https://github.com/jitsi/jiwer).
14. Hugging Face. [Hub offline mode](https://huggingface.co/docs/huggingface_hub/package_reference/utilities).
15. W3C. [WebVTT Recommendation](https://www.w3.org/TR/webvtt1/).
16. Netflix. [Timed Text Style Guide: General Requirements](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements).
17. FFmpeg. [License and Legal Considerations](https://ffmpeg.org/legal.html).
18. ReadBeyond. [aeneas official repository, limitations, and AGPL-3.0 license](https://github.com/readbeyond/aeneas).
