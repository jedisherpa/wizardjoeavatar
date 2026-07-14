# Accessibility and UX Audit for Audiobook Performance and PrismGT

**Role:** 12, Accessibility and User-Experience Reviewer
**Date:** 2026-07-13
**Scope:** Read-only audit of `WizardJoeAvatar-python` and the adjacent PrismGT checkout, plus current official and professional accessibility research. No production code or dependency files were changed.

## Executive verdict

The current applications contain useful accessibility foundations, but the proposed audiobook performance experience is **not ready for an accessibility claim or broad release**.

The most important architectural decision is that accessibility preferences must be runtime inputs to the same deterministic performance scheduler as media time. Reduced motion cannot be a CSS-only presentation preference, captions cannot be the only text alternative, and privacy cannot be inferred from whether an output is ultimately stored locally.

Release-blocking findings are:

1. **Reduced motion is incomplete.** PrismGT detects `prefers-reduced-motion`, but still constructs a continuously moving Three.js scene; its CSS media query only suppresses selected transitions and one command-deck animation. The Python visualizer has no reduced-motion input at all.
2. **The player does not expose a full transcript.** PrismGT normalizes `transcriptUrl` but never fetches or renders it. The only media alternative is a transient caption overlay. For prerecorded audio-only books and podcasts, an equivalent text alternative is a WCAG 2.2 Level A requirement.
3. **External processing is not disclosed at the moment of action.** PrismGT can select OpenAI STT automatically when an OpenAI key exists, while the user-visible status says only “Whisper.” Pasted audiobook text is sent to ElevenLabs, but nearby copy emphasizes that generated tracks are stored locally. Provider, payload, purpose, and destination must be disclosed before transmission.
4. **Core media operations are incomplete for keyboard and assistive-technology users.** The player progress indicator is a read-only `role="meter"`; there is no seek control, playback-rate control, chapter navigation contract, or transcript-based seeking.
5. **The planned Whiz action has no implementation surface.** Current normalized media records have neither canonical external URL nor Whiz state, and no governed media-link opener exists.
6. **No accessibility regression suite exists.** PrismGT has no browser test or accessibility dependency in `package.json`; the Python tests exercise control semantics but not DOM, keyboard focus, reduced motion, captions, contrast, zoom, or screen-reader status.

Target **WCAG 2.2 AA** for the web and desktop webview surfaces, and adopt **WCAG 2.3.3 Animation from Interactions (AAA)** as a product requirement because this product intentionally creates extensive motion. For macOS, honor the platform Reduce Motion preference and preserve platform focus, contrast, and text preferences where technically available.

## Audit boundaries and evidence

### Wizard Joe Python surface

- `web/avatar/index.html:10-33` contains the canvas, diagnostics, caption live region, toolbar, and native pose-picker dialog.
- `web/avatar/wizardControls.ts:55-85` installs global movement and action shortcuts.
- `web/avatar/wizardControls.ts:194-206` polls complete speech text into the caption live region every 125 ms.
- `web/avatar/wizardControls.ts:232-295` runs continuous demo/repeat motion without checking a motion preference.
- `web/avatar/wizardDiagnostics.ts:16-50` replaces one unstructured diagnostics block every second.
- `web/avatar/style.css:43-79,130-151` defines diagnostics, captions, 34 px controls, and a visible but low-information border-only focus treatment.
- `wizard_avatar/controller.py`, `runtime.py`, and `stream.py` provide deterministic semantic control and diagnostics but no user accessibility profile or motion-projection layer.

### PrismGT surface

- `src/features/visualizer/useReducedMotionPreference.js:5-17` observes `prefers-reduced-motion`.
- `src/features/visualizer/usePrismScene.js:27-77` recreates the Three.js controller when the preference changes, passing `reducedMotion` into the scene.
- `src/pages/PrismDodecahedron/index.css:2919-2943` removes only selected CSS transitions, one animation, and hover transforms.
- `src/pages/PrismDodecahedron/index.jsx:628-645,2920-2970` loads timed captions and exposes coarse caption status.
- `src/pages/PrismDodecahedron/index.jsx:3797-3804` places every current cue in `aria-live="polite"`.
- `src/pages/PrismDodecahedron/musicLibrary.js:47-77` retains `captionsUrl` and `transcriptUrl`, but only captions are consumed by the UI.
- `src/pages/PrismDodecahedron/studio/StageUtilityCards.jsx:376-389` presents progress as a meter, not an operable seek slider.
- `src/pages/PrismDodecahedron/studio/StageUtilityCards.jsx:423-457` exposes tracks, CC, and file linking, but no transcript, rate, stop, seek, or Whiz command.
- `src/pages/PrismDodecahedron/studio/FloatingPanel.jsx:29-58` supports pointer dragging and collapse, but no keyboard move/resize alternative or panel focus contract.
- `src/pages/PrismDodecahedron/index.jsx:985-1037` sends pasted text for ElevenLabs generation.
- `crates/prism-cdiss-cli/src/voice.rs:56-101,369-443` defaults STT to OpenAI when a key exists and posts recorded audio to OpenAI's transcription endpoint.
- `crates/prism-cdiss-cli/src/audiobooks.rs:83-101` has no canonical external URL field in stored audiobook metadata.
- `src/pages/PrismDodecahedron/index.css:207-234` renders utility triggers with `opacity: 0.28` and text alpha `0.18`; over the declared `#070707` page background the nominal composited text contrast is about **1.08:1**. `index.css:510-545` gives enabled player buttons a nominal contrast of about **4.33:1** against their declared panel stack, below the 4.5:1 threshold for normal text.

### Existing strengths to preserve

- PrismGT hides its decorative canvas from the accessibility tree and has a strong page-wide `:focus-visible` outline rule.
- Most PrismGT commands are native buttons with `aria-expanded`, `aria-pressed`, `aria-controls`, or explicit names.
- The player reports time with `aria-valuetext`; errors and statuses already use `role="status"` or `role="alert"` in several surfaces.
- Local linked audio uses browser object URLs and explicitly says it remains local to the browser session.
- The Python surface uses native buttons and a native modal `dialog`; its 34 px toolbar targets meet WCAG 2.2's 24 px minimum.
- Both systems already have deterministic command/state diagnostics that can support accessibility acceptance evidence.

## Standards and research baseline

The following sources were checked on 2026-07-13:

- [WCAG 2.2 Recommendation](https://www.w3.org/TR/WCAG22/), especially 1.2.1, 1.2.2, 1.4.3, 1.4.11, 2.1.1, 2.2.2, 2.3.1, 2.4.3, 2.4.7, 2.4.11, 2.5.8, 4.1.2, and 4.1.3.
- [W3C: Audio-only and Video-only (Prerecorded)](https://www.w3.org/WAI/WCAG22/Understanding/audio-only-and-video-only-prerecorded) requires an equivalent alternative for prerecorded audio-only media at Level A.
- [W3C: Captions (Prerecorded)](https://www.w3.org/WAI/WCAG22/Understanding/captions-prerecorded) defines captions as speech plus meaningful non-speech information, speaker identification, and sound effects, not dialogue-only subtitles.
- [W3C: Transcripts](https://www.w3.org/WAI/media/av/transcripts/) recommends basic and descriptive transcripts and describes interactive transcript-to-seek behavior.
- [W3C: Accessible Media Players](https://www.w3.org/WAI/media/av/player/) calls for keyboard operation, visible focus, clear labels, sufficient contrast, caption customization, and interactive transcripts.
- [W3C: Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide) requires user control for nonessential automatic motion lasting more than five seconds alongside other content.
- [W3C: Animation from Interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions) specifically identifies nausea, dizziness, headaches, and distraction, and recommends honoring reduced-motion preferences.
- [W3C: Three Flashes or Below Threshold](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold) prohibits more than three flashes per second unless the defined general/red-flash area thresholds are met.
- [W3C: Contrast (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum) requires 4.5:1 for normal text and 3:1 for large text; [Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast) requires 3:1 for essential control and state graphics.
- [W3C: Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum) sets a 24 by 24 CSS px Level AA minimum, subject to its spacing exceptions.
- [WAI-ARIA APG modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) requires initial focus inside a modal, contained tab order, Escape close, and focus return.
- [Apple Reduced Motion evaluation criteria](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/reduced-motion-evaluation-criteria/) says scaling, spinning, peripheral, multi-axis, multi-speed, depth, and ongoing motion should be stopped or changed when Reduce Motion is enabled.
- [Apple AppKit Reduce Motion API](https://developer.apple.com/documentation/appkit/nsworkspace/accessibilitydisplayshouldreducemotion) says to avoid large animations, especially simulated 3D motion, when the preference is true.
- [ETSI EN 301 549 V3.2.1](https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_20/en_301549v030201a.pdf), clauses 11.6.2 and 11.7, requires software not to disrupt platform accessibility features and to follow relevant platform preferences when available.
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) provides the privacy-risk basis for granular control and transparent data-processing practices.
- Provider disclosures must link to current provider terms, including [OpenAI API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint) and [ElevenLabs privacy policy](https://elevenlabs.io/privacy-policy).

WCAG is a conformance standard, not a complete product design specification. The stricter product requirements below deliberately go beyond minimum conformance where the experience involves prolonged animation, private books, and dense editing tools.

## Prioritized findings and recommendations

### P0. Reduced motion must change the performance, not just the chrome

**Current behavior.** PrismGT passes a boolean into `createPrismHeroScene`, but its reduced path still permits continuous scene motion. The CSS query does not affect character locomotion, dance, flight, camera movement, audio reactivity, blinking, or the Python runtime. The Python demo's repeat loop and paths always run.

**Required contract.** Add one persisted `AccessibilityMotionProfile` to the PrismGT media session and connector handshake:

| Mode | Runtime behavior |
| --- | --- |
| `system` | Resolve from the current platform/browser preference and react to changes during playback. |
| `full` | Authored performance, subject to flash safety and user intensity controls. This is an explicit opt-in when the platform requests reduced motion. |
| `reduced` | Disable locomotion, dance, flight, camera motion, simulated depth, spins, scale pulses, rapid turns, and audio-reactive whole-body motion. Preserve timing with stable poses, deliberate holds, low-amplitude facial/mouth changes, and caption/transcript progression. |
| `still` | Freeze the stage at a stable representative pose. Audio, transport, captions, transcript, processing, Whiz, and editor controls continue normally. |

Expose separate controls for `locomotion`, `dance`, `generated gestures`, `facial motion`, and `eye motion`, plus an overall intensity setting. An unavailable channel must become a deterministic safe fallback, not a random animation. The score remains unchanged; the runtime projects it through the active accessibility profile so seeking and versioning stay deterministic.

Changing the profile must not restart audio, change media time, regenerate a score, or lose editor work. The connector should report the resolved profile and disabled channels in diagnostics.

### P0. Add a motion-safety gate independent of reduced motion

Generated cues, audio-reactive pulses, magic effects, scene cuts, and user-supplied video can create flashes even when no authored animation is named “flash.” A user-facing toggle is not sufficient because a seizure can occur before the user can stop playback.

- Validate all shipped and generated visual samples at the largest supported/full-screen presentation.
- Reject or automatically suppress any sequence that violates WCAG 2.3.1 general or red-flash thresholds.
- Treat high-contrast pulse, opacity, emissive, and rapid palette changes as flash candidates.
- Record the analyzer version, viewport, frame rate, result, and altered cue IDs with the score evidence.
- If arbitrary user video cannot be pre-analyzed, provide a clearly labeled “Dim flashing lights” capability where the platform supports it and document the residual limitation. This does not replace the shipped-content gate.

### P0. Captions and transcripts need separate, complete UX

**Current behavior.** `captionsUrl` is fetched into transient cues. `transcriptUrl` survives normalization but has no consumer. The caption overlay is always an `aria-live="polite"` region, which can cause a screen reader to speak the narration again over the audiobook. Caption failure only becomes a short label; there is no retry, transcript fallback, or correction path.

**Required player design.** Provide all of the following:

1. A closed-caption toggle with a full accessible name such as “Show captions,” not `CC` alone.
2. A persistent, selectable transcript panel for every prerecorded audiobook/podcast. Include chapter headings, speaker names, meaningful non-speech audio, timestamps, search, copy/export, and a download/open action where policy allows.
3. Interactive transcript cues that seek the real audio element. Mark the active cue with text and `aria-current`, but never move keyboard focus automatically.
4. A “Follow playback” toggle. If the user scrolls or focuses an older cue, suspend automatic scrolling until they resume following.
5. Caption presentation controls for text size, foreground/background color, opacity, and position. Defaults must retain an opaque-enough backing over every visualizer frame.
6. Caption status with retry and fallback: `loading`, `ready`, `draft`, `unavailable`, `failed`, and `out of date` relative to the media hash.
7. Automatic captions remain visibly marked `draft` until a human verification gate passes. A successful ASR process is not evidence that names, negation, speakers, or meaningful sounds are correct.
8. Keep the visual caption overlay out of the live region by default. Offer a separate explicit “Announce captions with screen reader” preference for users who want it; do not force duplicate speech on every screen-reader user.

For Wizard Joe, `state.speech_text` is a demo status, not a transcript. Future playback should consume the same versioned cue artifact as PrismGT. Do not poll and replace the full book sentence in a live region every 125 ms.

### P0. Make provider and privacy boundaries visible before transmission

**Current behavior.** `openai_stt_mode_allows_openai(None, true)` returns true, so merely configuring an OpenAI key can route microphone audio externally. The UI says “Transcribing ... with Whisper,” which names a model family but not a provider or destination. ElevenLabs generation sends the entire pasted text in the request body; the copy says only that generated tracks are stored locally.

**Required preflight disclosure.** Before the first external processing action for a media job, show:

- provider and model;
- exact payload category and scope, for example “27 seconds of microphone audio,” “Chapter 3 transcript, 18,420 words,” or “audio and transcript”;
- what is not being sent;
- purpose;
- whether output and caches are stored locally;
- a link to current provider data controls/privacy terms;
- available local alternative and expected quality/time tradeoff;
- `Process externally`, `Use local`, and `Cancel` commands.

Consent is scoped to provider, media ID/hash, payload category, and operation. It may cover resumable chunks of the same approved job, but not another book or a changed provider. The ledger stores authorization metadata and hashes, never full book text. “Local mode” must be demonstrably network-silent and must fail closed when required local models are absent.

The default should be local for transcript/alignment and performance analysis. Presence of a cloud API key is capability discovery, not authorization.

### P1. Complete the media-control model

The read-only meter in `StageUtilityCards.jsx` cannot seek. Add a native range input or an APG-conformant slider with:

- accessible name, current/total time, and chapter context;
- Left/Right small seek, Page Up/Page Down larger seek, Home/End boundaries;
- a direct time-entry alternative for long books;
- chapter previous/next and chapter list;
- playback-rate menu with current value;
- play/pause, stop, skip back/forward, mute/volume, captions, transcript, motion, and Whiz controls;
- deterministic acknowledgement after seek and rate changes.

Do not use `aria-pressed` on the Play/Pause command merely to duplicate the visible changing label. The accessible name should match the action that will occur (“Play” or “Pause”), and state belongs in the player's status.

Global shortcuts must not fire when focus is in an input, textarea, select, contenteditable region, dialog, transcript search, or score editor unless the shortcut is explicitly documented for that control. Provide a shortcut reference and a user option to disable single-character shortcuts.

### P1. Establish focus behavior for panels, dialogs, and async work

PrismGT conditionally inserts utility cards before their trigger row while leaving focus on the trigger. The next Tab can skip the newly opened card. Floating panels are visually reordered by coordinates and z-index without a corresponding reading/focus model.

- Opening a utility card moves focus to its heading or first primary control; closing returns focus to its trigger.
- Escape closes the active utility card unless an inner control owns Escape.
- Use a modal only when background interaction must stop; otherwise do not trap focus.
- Opening a transcript or editor may retain focus on the invoking button if the panel is immediately next in DOM and announced via `aria-expanded`; otherwise move focus predictably.
- Collapsing a floating panel moves focus to its Expand control and applies `inert`/hidden semantics to the body.
- Provide Move Left/Right/Up/Down, Resize, Reset Position, and “Dock panels” commands as alternatives to pointer dragging.
- Never encode reading order in x/y window position. Offer a stable DOM order and panel landmark names.
- On asynchronous failure, announce the error without unexpectedly stealing focus. On user-submitted invalid forms, focus an error summary that links to affected fields.

The Python native pose dialog is a good base, but the opener and all toolbar buttons need real names. Verify initial focus, Escape, backdrop close, and focus return in Safari/VoiceOver and the desktop webview.

### P1. Repair names, roles, and canvas semantics

The Python toolbar buttons contain glyphs such as `▶`, `↻`, `↥`, and `▦` and rely on `title`. Their computed names can be the glyph rather than “Play demo,” “Repeat poses,” “Fly,” or “Choose pose.” Add explicit names and make dynamic names/states update together.

Treat the performance canvas consistently:

- During ordinary playback the visual performance is supplementary to the narrated book, so hide the raw canvas from assistive technology and expose media/player state separately.
- If a visual-only cue conveys editorial information, provide that information in the transcript or a dedicated “performance description” status/list, not as a generic canvas label.
- In the editor, expose cue, position, expression, fallback, and warning data through semantic controls/table rows. The waveform and stage canvas remain visual companions.

Use a real `<progress>` or `role="progressbar"` for determinate processing, not `meter`; use `meter` only for a scalar measurement. Names like “CC,” “11Labs,” and “Whiz” require either visible explanatory text or an accessible name that states the command.

### P1. Make processing status actionable and calm

Current states are scattered strings such as `loading`, `generating`, `importing`, and `failed`. The complete pipeline needs one user-visible job model:

`Inspecting media -> Reading metadata -> Checking transcript -> Transcribing -> Aligning -> Verifying -> Mapping chapters -> Analyzing narrative -> Generating performance -> Validating cues -> Preparing character -> Ready / Ready with warnings / Recoverable failure`.

Each job exposes phase, determinate percentage when honest, completed/total chapters, elapsed time, current provider/local mode, and the next available action. Support Cancel, Retry phase, Resume, Use cached result, Replace transcript, and View details. Never show a fabricated percentage for an indeterminate provider call.

Announce phase changes, warnings, completion, and failure. Do not announce every percent, audio frame, cue, diagnostic refresh, or heartbeat. Keep the job operable while processing and retain completed chapter results after cancellation.

### P1. Define Whiz as a governed accessible state machine

No current player or metadata code implements Whiz. Add `canonicalExternalUrl` to normalized media metadata and preserve provenance. Do not reuse the local audio URL, transcript URL, title search, or filename.

| State | Visual/assistive behavior | Action |
| --- | --- | --- |
| No media or unsupported media type | Hidden outside the applicable song/video context | None |
| Missing canonical URL | Visible unavailable state: “Whiz unavailable: no source link” | No navigation |
| Invalid or disallowed URL | Unavailable plus error detail; log validation failure | No navigation |
| Available | Button name “Open source page for {title}”; expose destination domain and external-browser behavior in description | Explicit click/keyboard activation only |
| Opening | Brief busy state only if the governed opener is asynchronous | Preserve playback and app focus state |
| Opened | Polite status “Opened {domain} in your browser” | No playback mutation |
| Blocked/failed | Alert with domain, reason, and Retry | Remain in app |

Parse with a standards-based URL API and allow only exact `http:` and `https:` schemes. Reject credentials in URLs, local file schemes, script/data schemes, malformed hosts, and guessed destinations. A native disabled button is not focusable, so an unavailable reason must be persistent visible text; alternatively use a guarded, focusable `aria-disabled="true"` control. Never rely on a hover-only tooltip.

### P1. Contrast, focus, target size, and zoom need a design-system gate

PrismGT's deliberately faint utility controls fail in their normal state. Translucent controls over a dynamic canvas also make contrast frame-dependent. Use a sufficiently opaque backing and tokens whose worst-case composited colors pass:

- 4.5:1 for normal text;
- 3:1 for large text;
- 3:1 for control boundaries, meaningful icons, selected state, and focus indicators against adjacent colors;
- information conveyed by text/icon/shape as well as color.

Increase the 20 by 20 px stage-close button to at least 24 by 24 px; use 44 by 44 px as the product target for primary transport and destructive commands. Retain a 2 px or stronger focus indicator and ensure floating panels, captions, and bottom controls never cover it.

At 200% browser zoom and at a 320 CSS px reflow viewport (typical 400% desktop equivalence), transport, captions, transcript, processing, Whiz status, and editor commands must remain readable and operable without two-dimensional scrolling. Do not hide diagnostics solely because the viewport is narrow; provide a compact disclosure instead.

### P1. Make the score editor and diagnostics work without a canvas or pointer

The editor needs two equivalent views:

1. visual waveform/timeline for direct manipulation;
2. semantic cue table/list with chapter, start, end, track, intent, animation, confidence, fallback, manual state, and validation errors.

Every drag operation needs keyboard/numeric alternatives. Provide step controls at 10 ms, 100 ms, and 1 s; start/end time inputs; move before/after; duplicate; disable; replace; undo; and restore generated value. Announce saves and validation failures. Keep unsaved edits across panel changes and motion-profile previews.

Diagnostics should use grouped headings and description lists, with stable labels for media time, drift, connection, cue, animation, expression, gaze, stage position, queue, acknowledgement, fallback, and score version. Default updates are visual only. Offer Pause updates, Copy snapshot, and an opt-in polite announcement for selected metrics. Never place a 60 Hz value stream in a live region.

The Python `WizardDiagnostics` block is useful developer evidence but is currently an unstructured string refreshed every second and silently ignores fetch failure. Give it connection/error state and a manual refresh/pause model before treating it as the audiobook debugger.

## Measurable acceptance tests

The following are release gates, not optional polish.

| ID | Acceptance test | Pass threshold |
| --- | --- | --- |
| AX-MOTION-01 | Start PrismGT with `prefers-reduced-motion: reduce`, load a performance, then inspect connector/runtime logs. | Resolved mode is `reduced` before the first performance cue; locomotion, dance, flight, camera, 3D spin/scale, and audio-reactive whole-body channels dispatch zero active cues. |
| AX-MOTION-02 | Change Full -> Reduced -> Still during playback. | Each mode is applied within 250 ms; audio position is continuous within the synchronization tolerance; no score regeneration, track restart, or focus loss. |
| AX-MOTION-03 | Relaunch both apps and reconnect. | Persisted preference and per-channel overrides survive restart; reconnect handshake reports the same resolved profile. |
| AX-MOTION-04 | Run every shipped/generated visual sample full-screen through a flash-analysis gate. | Zero WCAG 2.3.1 general-flash or red-flash violations; evidence records analyzer/version/viewport/frame rate. |
| AX-MEDIA-01 | Select each prerecorded audiobook/podcast fixture. | 100% expose an adjacent full transcript; transcript has media hash/version, chapter structure, speaker/non-speech information, and an accessible name. |
| AX-MEDIA-02 | Compare approved captions with reference audio. | No known material omissions; 100% meaningful speech/non-speech events represented; at least 95% of approved cue boundaries are within 250 ms of reference. Automatic-only output remains `draft`. |
| AX-MEDIA-03 | Keyboard through transcript, activate cue, search, suspend/resume Follow playback. | Cue activation seeks the real audio clock; focus never moves automatically; user scroll/focus is not overridden while Follow is suspended. |
| AX-MEDIA-04 | Use VoiceOver during normal captioned playback. | Visual captions are not automatically double-spoken. Opt-in caption announcements speak each cue once and never interrupt critical errors. |
| AX-PLAYER-01 | Operate the complete player using only Tab, Shift+Tab, Enter/Space, arrows, Home/End, and Escape. | Play/pause, stop, seek, chapter, rate, captions, transcript, motion, Whiz, volume, and track selection are all reachable, named, and operable; no trap. |
| AX-PLAYER-02 | Focus every media/editor text input and press all global single-character shortcuts. | No stage/action shortcut fires unless explicitly scoped to that control; user can disable single-key shortcuts. |
| AX-FOCUS-01 | Open/close each utility card, transcript, pose dialog, privacy preflight, and editor. | Focus enters in a logical place, remains contained only for true modals, Escape works, and close returns to the invoking control. |
| AX-FOCUS-02 | Use every floating-panel command at desktop and 320 CSS px. | Panel can be moved, resized, collapsed, reset, and docked without pointer; focused item is never obscured. |
| AX-NAME-01 | Inspect the accessibility tree for every control/state. | Zero unnamed controls; no glyph-only or title-only names; visible command text is contained in the accessible name; dynamic name/state agree. |
| AX-CONTRAST-01 | Test all control, caption, transcript, status, focus, and editor states over worst-case visualizer frames. | Text >=4.5:1 (or >=3:1 for large text); meaningful non-text UI/focus >=3:1. No pass based only on hover/focus. |
| AX-TARGET-01 | Measure all pointer targets and spacing. | WCAG 2.2 24 px minimum/spacing passes; primary transport, Whiz, close, and destructive actions are at least 44 px product targets. |
| AX-ZOOM-01 | Test at 200% zoom and 320 CSS px width with long track/chapter/provider names. | No clipped commands or text, no overlap, no lost functionality, and no two-dimensional page scrolling. |
| AX-STATUS-01 | Process a cached chapter and an uncached book; inject a recoverable failure. | Phase, honest progress, local/provider mode, completed chapters, Cancel/Retry/Resume, warnings, and error details remain visible and programmatically determinable. |
| AX-STATUS-02 | Record screen-reader speech during a 10-minute processing run. | Announcements occur on phase change, warning, failure, and completion only; no per-frame, per-second, or per-percent flood. |
| AX-PRIVACY-01 | Run local transcription/alignment/performance analysis with outbound traffic captured. | Zero external connections and zero transcript/audio bodies in logs; absent local model fails closed with an actionable message. |
| AX-PRIVACY-02 | Initiate OpenAI STT, ElevenLabs TTS, and an external LLM analysis. | Before network transmission, preflight names provider/model, exact payload scope, purpose, storage, terms link, local alternative, and cancel. Authorization is ledgered by hashes/metadata. |
| AX-WHIZ-01 | Test no media, audiobook, song/video without URL, malformed URL, `file:`, `data:`, `javascript:`, and valid HTTP(S). | Hidden only when inapplicable; all unavailable cases perform zero navigation and expose a reason; only valid canonical HTTP(S) opens. |
| AX-WHIZ-02 | Activate available Whiz with mouse, Enter, and Space; simulate opener failure. | One governed open per activation, destination domain announced, playback state unchanged, focus retained/returned, and failure offers Retry. |
| AX-EDITOR-01 | Edit, validate, save, undo, and version a score with keyboard and VoiceOver using only the semantic cue view. | Every operation available without waveform/canvas/drag; errors identify cue and field; save/version status announced once; original generated score remains unchanged. |
| AX-DIAG-01 | Run diagnostics for five minutes with VoiceOver. | Metrics are structured and readable on demand; Pause/Resume and Copy snapshot work; no unsolicited metric stream. |
| AX-AUTOMATION-01 | Run DOM accessibility automation on player, transcript, processing, privacy, Whiz, and editor states. | Zero serious/critical axe violations; snapshots include accessible names, roles, states, and focus order. |
| AX-MANUAL-01 | Manual pass in installed macOS app and hosted browser with VoiceOver, keyboard-only, Reduce Motion, Increase Contrast, and 200% zoom. | All primary workflows complete without pointer or vision-only information; findings and versions recorded as release evidence. |

Automation cannot prove caption accuracy, motion comfort, sensible focus order, or usable screen-reader speech. Those gates require human review, including at least one user with relevant assistive-technology experience before a public accessibility claim.

## Recommended implementation order

1. Establish the shared accessibility profile, reduced/still runtime projection, and flash gate before generating performance scores.
2. Add the full transcript model and complete transport/seek/rate/chapter controls before connector polish.
3. Make every cloud path explicit and authorized; remove key-presence-as-consent behavior.
4. Add canonical URL metadata and the governed Whiz state machine.
5. Build focus contracts, contrast/target tokens, and processing semantics into the shared PrismGT components.
6. Build the editor as waveform plus semantic cue table from its first usable version.
7. Add browser automation, accessibility-tree snapshots, motion/flash evidence, and installed-app VoiceOver checks to release gates.

## Production-readiness statement

This audit does not claim that the current UI conforms to WCAG 2.2 or that current captions are publication quality. It is a static code and standards audit, not a completed VoiceOver, browser automation, flash-analysis, or user-testing pass. The acceptance suite above defines the evidence required before those claims can be made.
