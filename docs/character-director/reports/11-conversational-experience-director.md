# Conversational Experience Director

## Audit basis

Role: Conversational Experience Director  
Scope: PrismGT submission, governed-turn progress, final-response entrance, text and speech presentation, completion, errors, and interruption as observed by Wizard Joe  
Python runtime baseline: `556701a0dfd8c9c553de7159bc2d747b43fa9bd8`  
Prism connector baseline: `189fbabc4f59af5d53e352c6bf9c692ee7382214`  
Canonical connector document: `docs/audiobook-performance/LOCAL_PRISMGT_AUDIO_CONNECTOR.md` as present in the working tree; its user workflow and installer guidance were added by `408825a`, while the runtime contract originated at `556701a`  
Method: static, read-only inspection of the exact commit trees plus the canonical working-tree document. No runtime code, tests, existing documentation, manifests, generated artifacts, or other specialist reports were changed.

## Executive finding

The complete conversational experience is **not implemented end to end**.

PrismGT already has a truthful governed-turn stage stream, a visible stage rail, and a final `reply` event. Wizard Joe already has a strict content-free visual-advisory contract and stage-to-animation mapping. The media connector already observes the real speech `<audio>` element and makes its clock authoritative for TTS animation. These are three strong implemented pieces.

The missing piece is the conversation-event bridge between PrismGT and Wizard Joe. At `189fbab`, Prism exposes only the Wizard media-session and status routes. It contains no `visual_advisory_only`, `prism-signal`, or animation-signal producer or relay. Therefore Wizard Joe cannot currently observe prompt acknowledgment, governed stages, final-response release, ordinary turn errors, or completion/listening return from Prism.

The current Prism frontend also has no user-facing interruption path. It disables the prompt for the whole request, text reveal, and speech operation. Dropping the SSE response would not truthfully cancel the server turn because the server runs it in a detached task and ignores failed event sends.

## Status definitions

- **Implemented**: code exists at the stated baseline and the observed event directly supports the behavior.
- **Partial**: some required code or observation exists, but the end-to-end claim would overstate what is observable.
- **Missing**: no production path connects the required behavior at the stated baselines.
- **Unverified**: static evidence exists or a claim is documented, but this audit did not execute it and no inspected test proves the complete behavior.

## Status matrix

| Experience requirement | Status | Evidence and consequence |
|---|---|---|
| Server-accepted submission acknowledgment | **Partial** | Prism locally appends the user message and sets `Queued` before `fetch` in `executeCdissPrompt` (`index.jsx:2710-2736`). The server emits `queued/active` only after request validation and task creation in `stream_governed_turn` (`web.rs:6506-6548`). The latter is truthful acknowledgment, but it is not relayed to Wizard Joe. |
| Waiting while another turn owns the runtime | **Implemented in Prism; missing in Wizard** | `stream_governed_turn` emits `queued/active` before awaiting `turn_lock` (`web.rs:6539-6552`). This makes `Queued` a truthful wait state. No conversation relay forwards it. |
| Governed stage transitions | **Implemented in Prism; missing end to end** | `run_turn_request` emits `reading you`, `drafting a reply`, `auditing`, and `deciding` (`main.rs:3313-3324`, `3567`, `3650`, `3673`). `stage_meta` sanitizes them into `understanding`, `drafting`, `checking_safety`, and `reviewing` (`web.rs:8329-8370`). Wizard accepts all corresponding stage vocabulary, but Prism does not send it there. |
| Visible Prism stage history | **Implemented** | `applyCdissStage` upserts active/done rows (`index.jsx:2251-2280`); `StageRail` presents active stage, completed stages, durations, and clarification (`StageRail.jsx:10-79`). |
| Governed final-response release | **Partial** | The `reply` SSE event is sent only after the governed turn returns and a terminal stage is selected (`web.rs:6589-6622`). This is the correct presentation-release boundary. Prism has no explicit Wizard event for that boundary, and `ready/done` is emitted before `reply`. |
| Distinguishing response release from action approval | **Implemented in Prism data; at risk in experience design** | Terminal `waiting_approval` means a pending protected action, while `reply` still carries the user-facing response (`web.rs:6597-6622`). Treating `waiting_approval` as response approval would be false. |
| Final-response entrance in Wizard Joe | **Missing** | Python maps `ready` to a restrained speak/explain cue (`semantic_animation_map.json:126-146`), but no Prism producer sends `ready`, and the Python mapper does not distinguish `active` from `completed`. |
| Audible TTS clock sync | **Implemented for the real speech element** | `createMediaElementConnector` activates speech only when the speech element is audible, samples its `currentTime`, emits heartbeat snapshots, and restores main media on pause/end/error (`useMediaSessionConnector.js:297-304`, `340-347`, `461-474`, `509-555`). Python prioritizes nonterminal speech snapshots and applies media-time mouth/action state (`media_session.py:759-775`; `performance_application.py:69-121`). |
| Text-to-word audio alignment | **Missing** | `revealCdissText` uses token-length and punctuation delays (`speech-animation.js:27-40`; `index.jsx:2661-2672`) while speech generation and playback run independently in `Promise.all` (`index.jsx:2763-2771`). No word timestamps or alignment are observed. |
| Browser TTS and Web Audio observability by Wizard | **Missing** | `speakCdissReply` can fall back from the speech element to Web Audio, browser speech synthesis, or synthetic motion (`index.jsx:2526-2535`, `2590-2618`). The media connector observes only `speechAudioRef`, so those fallback paths cannot truthfully drive remote audible-speech state. |
| Completion and return to listening | **Partial** | Prism sets `Idle` after both text reveal and speech promise settle (`index.jsx:2772-2784`). The speech media connector truthfully restores main media after pause/end/error. No content-free completion or listening signal is sent to Wizard Joe, and `Idle` is local UI state rather than a server event. |
| Turn errors | **Partial** | The server emits an SSE `error` with time and error text (`web.rs:6624-6633`); the client presents `Error` and a system message (`index.jsx:2775-2781`). No sanitized failed-stage event is relayed to Wizard. Raw error text must not enter the strict visual-advisory contract. |
| TTS-only errors | **Partial and currently obscured** | TTS fetch/decode/play failures silently cascade through fallback paths (`index.jsx:2590-2618`). A successful text response can therefore look like speaking even when no remotely observable audio exists. |
| Output interruption | **Missing in the normal product path** | The prompt, mic, and send control are disabled while `cdissBusy` (`PromptRow.jsx:39-46`, `109-136`). Audio is paused/cancelled only in unrelated controls or unmount cleanup (`index.jsx:3151-3178`). |
| Governed-turn cancellation | **Missing** | `chat_stream` spawns `stream_governed_turn` (`web.rs:6523-6527`), and `send_sse` discards send failure (`web.rs:8313-8315`). Client disconnect is not proof that model/governance work stopped. |
| Conversation bridge authentication/privacy | **Missing** | Prism has only media connector routes at `web.rs:105-106` and `486-487`. Python's `/api/avatar/wizard/prism-signal` route (`server.py:217-219`) does not use the media connector's `require_connector` or bounded body reader. The parser is strict, but the transport boundary is not ready for Prism production use. |
| Stage status and TTL release | **Partial in Python** | Python validates stage status and TTL (`prism_signals.py:43-66`, `321-337`, `440-474`) but `map_signal_to_animation_intent` and `_cmd_prism_signal` do not use status to release a completed/cancelled/failed cue, and no runtime expiry is stored (`semantic_animation.py:336-373`; `controller.py:262-310`). |
| End-to-end conversation verification | **Unverified** | Inspected tests cover strict signal parsing, semantic mapping, movement authority, and media speech preemption/restoration. No inspected test covers Prism SSE -> authenticated relay -> Python stage animation -> speech -> completion/interruption. |

## Actual observable path

### 1. Submission and server acknowledgment

1. `PromptRow` submits through `submitCdissPrompt` and disables editing, persona/model changes, mic, and send while `cdissBusy` is true (`PromptRow.jsx:33-46`, `61-68`, `83-90`, `109-136`).
2. `executeCdissPrompt` clears the prompt, appends the user message, sets local `Queued`, and inserts a local queued stage before sending the request (`index.jsx:2710-2736`). This proves only that the browser began an attempt.
3. `chat_stream` rejects forbidden mutations and empty prompts before creating the SSE stream (`web.rs:6506-6527`).
4. `stream_governed_turn` emits server `queued/active` before awaiting the serialized turn lock (`web.rs:6534-6552`). This is the first event that proves Prism accepted the prompt for governed processing.

**Experience decision:** show the locally appended message as pending until the server `queued/active` event arrives. Only that SSE event may drive Wizard Joe's acknowledgment/listen pose. A network failure before it arrives is a submission failure, not a completed acknowledgment.

### 2. Waits and governed processing

Prism's observable stage sequence is:

| Raw runtime note | Sanitized SSE stage ID | Truthful meaning | Wizard stage value |
|---|---|---|---|
| `queued` | `queued` | Accepted by Prism; waiting for or entering serialized turn processing | `queued` |
| `reading you` | `understanding` | Runtime began prompt observation, conversation state, recall, and Watcher work | `understanding` |
| `drafting a reply` | `drafting` | The chat provider is drafting; this is not approved final text | `drafting` |
| `auditing` | `checking_safety` | Auditor is reviewing the draft and feasibility | `checking_safety` |
| `deciding` | `reviewing` | Synthesizer is finalizing the verdict | `reviewing` |
| terminal `ready` | `ready` | Governed turn completed without clarification or pending action approval | `ready` |
| terminal `needs_clarification` | `needs_clarification` | The final reply asks for the one surfaced decision | `needs_clarification` |
| terminal `waiting_approval` | `waiting_approval` | The final reply accompanies a protected action waiting for approval | `waiting_approval` |

The SSE status vocabulary is `active` and `done` (`web.rs:8406-8439`). The Python contract requires `started`, `active`, `completed`, `cancelled`, or `failed` (`prism_signals.py:64-81`). A Prism bridge must map `active -> active` and `done -> completed`; it must not forward `done` unchanged.

Intermediate `done` events are immediately followed by the next `active` event in the normal stream (`web.rs:6574-6587`). Until Python becomes status-aware, sending completed events would retrigger rather than release the same cue. Production enablement therefore requires the Python status/expiry correction described below, or a documented bridge rule that only forwards active intermediate stages and converts terminal completion into a terminal posture.

### 3. Approved final-response entrance

The release boundary is the `reply` SSE event, not the `ready` stage and not `waiting_approval`.

- `ready`, `needs_clarification`, or `waiting_approval` is selected after the governed turn returns (`web.rs:6596-6617`).
- The `reply` event follows the terminal stage in the same server branch (`web.rs:6618-6622`).
- The frontend does not create the agent message until it has a nonempty `replyPayload.reply` (`index.jsx:2743-2762`).

**Experience decision:** buffer the terminal stage for presentation and authorize Wizard Joe's final-response entrance only when the matching `reply` event arrives. This avoids celebrating a `ready/done` event if the stream disconnects before the response payload reaches the client. It also prevents a draft-stage animation from being mistaken for approved text.

For `waiting_approval`, the response may enter and may be spoken, but the post-response posture must return to waiting for approval, not ordinary listening. For `needs_clarification`, it must return to an attentive clarification/listening posture. For ordinary `ready`, it may settle and return to listening.

### 4. Text and speech presentation

The current frontend inserts an empty agent message, sets local `Speaking`, and starts text reveal and speech concurrently (`index.jsx:2758-2771`). This is visually coordinated but not synchronized:

- Text pacing is derived from token length and punctuation, not audio time (`speech-animation.js:27-40`).
- TTS has a six-second request timeout before playback can begin (`index.jsx:2593-2603`). Text reveal can advance during that wait.
- The real speech element exposes `playing`, `pause`, `ended`, `error`, `currentTime`, and `duration`, and the media connector already observes them (`index.jsx:2429-2523`; `useMediaSessionConnector.js:518-555`).
- No inspected response carries word timing.

**Experience decision for current capabilities:**

1. Present the complete final text when the `reply` event authorizes entrance, or treat the existing token reveal as a purely visual text effect with no claim of word/audio alignment.
2. Do not send Wizard `speaking/active` when TTS is requested or when text reveal starts.
3. Enter audible speaking only on the speech element's actual `playing` event. Let Media Session V1 remain authoritative for mouth timing and speech duration.
4. Complete speaking on actual `ended`, `pause`, `emptied`, or `error`. The existing media connector then restores main media without restarting it (`useMediaSessionConnector.js:509-555`; canonical connector document lines 11-13 and 89-97).
5. When speech uses Web Audio, browser speech synthesis, or synthetic motion, do not claim remote audible speaking. Either present text only, or first add an observable media-element path. Exact word synchronization remains unavailable until Prism produces real alignment metadata.

### 5. Completion and listening return

Normal completion should be derived from observables in this order:

1. Final reply received and presented.
2. If audible speech started, its real element reached a terminal playback event.
3. Text presentation completed or was deliberately made immediate.
4. Prism re-enabled input after local cleanup.
5. Wizard received a terminal posture matching the governed outcome, followed by listening only where listening is truthful.

Use these terminal postures already accepted by Python:

- Normal response: `terminal_posture` with `posture=settled`.
- Clarification response: `terminal_posture` with `posture=needs_clarification`, then `stage=listening,status=active` when input is enabled.
- Pending protected action: `terminal_posture` with `posture=waiting`; do not overwrite it with generic listening.
- Failed turn: `terminal_posture` with `posture=degraded` only when the turn could not produce a response.

The current frontend's `Idle` assignment (`index.jsx:2772-2784`) is not sufficient evidence for Wizard because it is not transported. The media connector's speech terminal snapshot is sufficient only for audio ownership, not for the governed conversation outcome.

### 6. Errors

Three failures need different treatment:

1. **Submission or governed-turn failure:** keep/show the user's pending message, present the sanitized Prism error locally, send the current content-free stage with `status=failed`, then settle Wizard into degraded/attentive posture. Never forward the error string.
2. **Speech failure after a valid text reply:** preserve the text response and mark voice delivery unavailable locally. Do not mark the conversation failed and do not emit speaking unless real playback began.
3. **Wizard connector failure:** Prism conversation and speech continue. The UI reports Wizard unavailable; no animation state is claimed. On reconnect, send current full media state and the current content-free conversation posture, not a replay of old stages.

The strict Python contract already rejects prompt, reply, message, content, provider, model, route, path, secret, authority, command, and movement vocabulary (`prism_signals.py:145-191`, `223-237`). The bridge must construct an allowlisted envelope rather than sanitize arbitrary SSE/error objects after the fact.

### 7. Interruption

Interruption has two separately provable outcomes:

- **Output stopped:** text reveal, TTS request, speech element, browser speech, Web Audio/synthetic animation, and pending speech are stopped locally. This can be acknowledged immediately after those local resources are actually cancelled. The speech element's `pause`/`emptied` event lets the media connector release speech ownership and restore main media.
- **Governed turn cancelled:** the Rust task stopped and will not mutate conversation state or later emit/persist a reply. This cannot be claimed at `189fbab` because disconnect does not cancel the detached server task.

Required interruption sequence:

1. Expose an explicit stop-response control while generation, reveal, or speech is active. Do not depend on sending another prompt while the form is disabled.
2. Cancel the frontend stream reader/fetch, text-reveal loop, six-second TTS fetch, speech `<audio>` playback, browser speech synthesis, Web Audio source, synthetic animation frame loop, and pending speech.
3. Emit `stage=speaking,status=cancelled` only when output had actually started; otherwise cancel the current active governed stage.
4. Add server cancellation that is correlated to the active turn and produces a confirmed terminal cancellation event. Until that exists, label the local result as output stopped, not turn cancelled.
5. Discard any late reply from the interrupted generation and prevent it from entering the message log or starting speech.
6. Return to listening only after local output has stopped and, where claimed, server cancellation is confirmed.

## Required changes

### Prism changes

1. **Add a local-only conversation-signal relay.** Place it beside the existing Wizard media connector routes in `crates/prism-cdiss-cli/src/web.rs` and the Rust connector module. It must use the configured loopback destination and backend-held token, never browser-to-Wizard networking. Public web must not expose it.
2. **Build signals from structured lifecycle data.** Convert only `stage_event` fields and known frontend media-element events into the strict Python envelope. Generate a process/page source epoch, monotonically increasing sequence, UUID event ID, bounded TTL, `visual_advisory_only` classification, and allowlisted payload. Do not forward prompt, reply, labels, summaries, missing-decision text, model/provider details, or error text.
3. **Use server acknowledgment.** Forward `queued/active` received from SSE, not the frontend's optimistic queued insertion.
4. **Translate stage identifiers and statuses explicitly.** Use the sanitized `stageId` values and map `done` to `completed`. Do not derive behavior from labels such as `Understanding request`.
5. **Gate final entrance on `reply`.** Terminal stage completion alone is not enough. The final message may enter only after `reply` is received.
6. **Use actual speech events.** Keep the speech media element as the audible clock. Emit speaking lifecycle only from `playing` and terminal media events, and let Media Session V1 own mouth timing.
7. **Make fallbacks honest.** Text-only success is valid. Browser TTS, Web Audio, and synthetic motion must not masquerade as speech visible to Wizard unless Prism first routes them through an observable media element.
8. **Add interruption controls and cancellation semantics.** Separate locally confirmed output stop from backend-confirmed turn cancellation. Stop late replies from entering the UI.
9. **Expose connector state without blocking conversation.** Conversation-stage relay failure should be visible in Wizard diagnostics/status but must not stop Prism chat or audio.

### Python changes required before production stage bridging

1. Protect `/api/avatar/wizard/prism-signal` with the same loopback, bearer-token, browser-Origin rejection, and bounded-body principles used by `/media-session` (`server.py:161-178` versus `217-219`).
2. Make stage `status` operational. `completed`, `cancelled`, and `failed` must release or transition the active advisory instead of replaying the stage cue.
3. Store and enforce advisory expiry in runtime state so a lost connector cannot leave a stale semantic cue or expression after TTL. One-shot actions have their own timeout and must remain separate from advisory expiry.
4. Define precedence between semantic `speaking` and Media Session speech. Media time must own mouth shape whenever the speech source is active; stage signals may provide only bounded expression/body entrance.
5. Preserve current authority limits: visual signals must remain unable to move the character or execute actions (`AnimationIntent` at `semantic_animation.py:18-45`; movement-authority test at `test_game_control.py:111-160`).

## Risks

| Severity | Risk | Evidence | Required control |
|---|---|---|---|
| High | Shipping stage UX while no Prism-to-Wizard bridge exists creates false confidence from two separately implemented halves. | No signal vocabulary or route exists in Prism at `189fbab`; only media and status routes exist. | End-to-end proof from SSE event to visible Wizard state before claiming completion. |
| High | A completed or expired stage can remain sticky in Wizard. | Parser validates status/TTL, but controller stores only cue/gesture/amplitude and no expiry. | Status-aware release and runtime TTL expiry. |
| High | `ready` can be mistaken for action approval or audible speech. | `waiting_approval` is a distinct terminal; `ready` maps to speak cue; `reply` arrives after terminal stage. | Treat `reply` as response release; preserve action-approval semantics; audio `playing` alone starts audible speech. |
| High | User believes a turn was cancelled while the server continues and mutates state. | Detached task plus ignored SSE send failure. | Backend cancellation confirmation and late-result discard. |
| High | Conversation-signal transport bypasses the hardened connector boundary. | Python prism-signal endpoint lacks connector auth/body handling. | Authenticated sidecar relay and hardened Python ingress. |
| Medium | Text races ahead of delayed TTS and appears word-synchronized when it is not. | Fixed token delays run concurrently with TTS request/playback. | Immediate full text or explicitly decorative reveal; alignment only with real timing data. |
| Medium | Browser/Web Audio fallback produces local speaking visuals but no remote speech state. | Media connector observes only `speechAudioRef`. | Text-only remote behavior or route all audible output through the observed element. |
| Medium | Optimistic queued animation acknowledges a request Prism rejected before SSE. | Local queued stage is inserted before `fetch`. | Pending local state; Wizard acknowledgment only from server SSE. |
| Medium | Raw backend error text leaks private/provider data if reused as a signal. | SSE error includes `error.to_string()`; Python contract forbids content/provider/model fields. | Fixed failed/degraded enums only. |
| Medium | Connector disabled or unavailable makes all designed behavior absent. | Prism connector enablement defaults false in `index.jsx:542-578`; canonical setup requires environment and service installation. | Installed-app verification of connected status before experience acceptance. |

## Rejected alternatives

1. **Direct browser POST to Wizard:** rejected because it exposes a localhost control boundary and connector secret to browser code. The canonical contract requires same-origin Prism ingress and server-to-server loopback relay.
2. **Infer stages from `cdissBusy`, elapsed timers, visualizer motion, or labels:** rejected because only structured SSE stages describe actual governed progress.
3. **Treat local `Queued` as server acceptance:** rejected because it occurs before `fetch` succeeds.
4. **Treat `ready/done` as final text arrival:** rejected because `reply` is a later event and can be lost on disconnect.
5. **Treat `waiting_approval` as permission to present or execute:** rejected because it means the opposite: a protected action is still waiting.
6. **Start speaking when TTS is requested or text reveal begins:** rejected because neither proves audible playback.
7. **Claim word-level synchronization from proportional text/audio progress:** rejected because no word alignment is observed. Approximation must not be labeled synchronization.
8. **Forward reply text, prompt text, stage summaries, clarification text, or raw errors to Wizard:** rejected by privacy and strict schema boundaries.
9. **Use synthetic mouth motion as evidence of speech:** rejected because it can run with no audio and is not observed by the media connector.
10. **Treat SSE disconnect as cancellation:** rejected because the detached server task continues unless explicitly cancelled.
11. **Restart or seek main media after speech:** rejected because the existing connector correctly restores the latest main snapshot without controlling audio.
12. **Send completed stages without changing Python:** rejected because status is currently ignored and can retrigger/stick the cue.

## Verification requirements

No tests were run in this audit because the assignment allowed writes only to this report, and test/build execution can create caches or generated artifacts. The following are required before implementation can be called complete.

### Prism unit and integration tests

1. Prove stage sequences for success, serialized wait, command short-circuit, clarification, pending approval, governed error, and stream disconnect.
2. Prove only server `queued/active` produces Wizard acknowledgment; optimistic browser state never does.
3. Prove exact mapping of sanitized stage IDs and `active/done` statuses to the Python contract.
4. Prove the relay rejects/omits prompt, reply, message, summaries, missing-decision text, error text, provider/model, URLs, paths, credentials, and unknown fields.
5. Prove the conversation-signal route is local-only, same-origin on browser ingress, loopback-pinned on relay, authenticated, body-bounded, and absent from public web.
6. Prove `reply` is the only final-response entrance boundary, including disconnect after terminal stage but before reply.
7. Prove speech enters only after the actual speech element's `playing`, and completes on `ended`, `pause`, `emptied`, and `error`.
8. Prove browser TTS/Web Audio/synthetic fallback does not emit false remote speaking.
9. Prove stop-response cancels reveal and every output mechanism, rejects late reply entrance, and distinguishes local output stop from confirmed backend cancellation.

### Python tests

1. Extend parser/controller tests so stage `completed`, `cancelled`, and `failed` produce defined release/terminal behavior.
2. Add deterministic TTL-expiry tests with no later event.
3. Add auth, Origin, body-size, unknown-field, stale, duplicate, sequence, and source-epoch tests for the production signal ingress.
4. Prove active media-session speech owns mouth timing over semantic stage cues.
5. Prove semantic cues never displace keyboard/gamepad/remote locomotion or gain execution authority.
6. Prove connector loss settles safely rather than leaving an indefinite active cue.

### End-to-end installed-app proof

Record one sanitized evidence run from the installed Prism GT app and persistent Wizard service that shows:

1. Pending local submit, then server-acknowledged queued/listen.
2. Understanding -> drafting -> safety check -> reviewing in observed SSE order.
3. Final response does not enter before `reply`.
4. Actual speech element `playing` causes `source_slot=speech`, a live mouth shape, and speech-priority body behavior.
5. Text remains truthful when audio is disabled or TTS fails; no false speaking appears.
6. Speech end returns to advanced `source_slot=main` without restart, or settles/listens when no main media is active.
7. Clarification returns attentive/listening; pending approval returns waiting; normal completion returns settled/listening.
8. Governed error produces failed/degraded posture without leaking error text.
9. Output stop halts sound and reveal immediately; confirmed turn cancel prevents late response/state mutation.
10. Wizard unavailable leaves Prism conversation and audio functional and visibly reports connector degradation.

The existing canonical media proof remains required: main media, speech preemption, then advanced main media after speech (`LOCAL_PRISMGT_AUDIO_CONNECTOR.md:105-119`).

## Files and symbols inspected

### PrismGT at `189fbab`

- `crates/prism-cdiss-cli/src/main.rs`
  - `CliApp::run_turn_request`
  - progress notes `reading you`, `drafting a reply`, `auditing`, `deciding`
- `crates/prism-cdiss-cli/src/web.rs`
  - `chat`, `chat_stream`, `stream_governed_turn`
  - `send_sse`, `StageMeta`, `stage_meta`, `stage_event`
  - local router constants/routes `WIZARD_MEDIA_SESSION_ROUTE`, `WIZARD_CONNECTOR_STATUS_ROUTE`
- `src/pages/PrismDodecahedron/index.jsx`
  - state refs for speech and turn stages
  - `applyCdissStage`, `handleCdissStream`, `executeCdissPrompt`
  - `playCdissAudioBuffer`, `playCdissAudioElement`, `playCdissAudio`
  - `queuePendingSpeech`, `flushPendingSpeech`, `driveSyntheticSpeech`
  - `speakCdissReply`, `speakWithBrowserTts`, `revealCdissText`
  - `useMediaSessionConnector` integration and unmount cleanup
- `src/pages/PrismDodecahedron/shell/PromptRow.jsx`
  - busy-state control disabling and submit surface
- `src/pages/PrismDodecahedron/shell/StageRail.jsx`
  - active/done stage presentation and clarification announcement
- `src/pages/PrismDodecahedron/shell/CdissMessageList.jsx`
  - live message-log presentation
- `src/lib/sse-cdiss.js`
  - `parseSseBlock`, `stageMode`, `expressionFromCdiss`
- `src/lib/speech-animation.js`
  - `speechFrame`, `splitSpeechTokens`, `getSpeechTokenDelay`
- `src/pages/PrismDodecahedron/media/useMediaSessionConnector.js`
  - `createMediaElementConnector`, `isAudible`, speech/main handlers, `finishSpeech`, `useMediaSessionConnector`
- `src/pages/PrismDodecahedron/media/mediaSessionProtocol.js`
  - `buildMediaDescriptor`, `buildPerformanceDescriptor`, `inferPlaybackState`, `createMediaSessionSnapshot`
- `src/pages/PrismDodecahedron/media/__tests__/useMediaSessionConnector.test.js`
  - speech preemption, pause/end restoration, audibility, and heartbeat coverage

### Python at `556701a` unless noted

- Working tree `docs/audiobook-performance/LOCAL_PRISMGT_AUDIO_CONNECTOR.md`
  - authoritative two-element clock, privacy, service setup, runtime behavior, and three-state proof
- `wizard_avatar/prism_signals.py`
  - `PRISM_SIGNAL_KINDS`, `_STAGES`, `_ENUM_FIELDS`, `_PAYLOAD_RULES`
  - `PrismAnimationSignalV1`, `PrismSignalParser`, `PrismSignalAdapter`
- `wizard_avatar/definitions/prism_animation_signal.schema.json`
  - closed Prism animation signal schema
- `wizard_avatar/definitions/semantic_animation_map.json`
  - stage, terminal, approval, health, and bounded cue mappings
- `wizard_avatar/semantic_animation.py`
  - `AnimationIntent`, `map_signal_to_animation_intent`, `arbitrate_animation_intents`, `map_prism_signal`
- `wizard_avatar/controller.py`
  - `WizardAvatarController._cmd_prism_signal`, `_cmd_speech_stop`
- `wizard_avatar/server.py`
  - media-session authenticated routes and `/api/avatar/wizard/prism-signal`
- `wizard_avatar/media_session.py`
  - `MediaSessionCoordinator._select_active_snapshot`, `accept_with_result`
- `wizard_avatar/performance_application.py`
  - `PerformanceApplication.apply`, `_is_live`, `_resolve_action`, `_release_owned_state`
- `tests/wizard/test_prism_signals.py`
  - closed schema, forbidden content, ordering, expiry, deduplication, and no-network adapter tests
- `tests/wizard/test_semantic_animation.py`
  - stage mapping, no-op failures, governance clamps, and movement preservation tests
- `tests/wizard/test_game_control.py`
  - visual advice cannot take movement authority; local speech lifecycle test
- `tests/wizard/test_media_session.py`
  - TTS preemption, stale terminal rejection, and main restoration tests

## Final recommendation

Approve the existing Prism SSE stages and real speech media clock as the only current sources of truth. Do not invent a richer emotional or conversational state machine around them. Implement the authenticated, content-free conversation relay; make Python status and TTL operational; gate response entrance on `reply`; gate audible speaking on the speech element's `playing`; and add a two-level interruption model that distinguishes stopped output from confirmed cancelled work.

Until those changes and the end-to-end installed-app proof pass, describe the system as **Prism stage UX implemented, Wizard semantic receiver implemented, audio speech sync implemented, conversation bridge and interruption missing**.


