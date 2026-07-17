# Local PrismGT Audio Connector

## Purpose

The connector makes the persistent Python Wizard Joe runtime animate from the
authoritative clocks of PrismGT's two real HTML audio elements:

- `main`: music, podcasts, audiobooks, and video audio
- `speech`: PrismGT TTS and speaker output

The connector observes playback. It never starts, pauses, seeks, or restarts
audio. Audible speech takes performance priority over main media. When speech
ends, pauses, or becomes inaudible, the latest main-media snapshot is restored.

## Local endpoints

- Wizard visualization: `http://127.0.0.1:8765/`
- Wizard ingress: `POST /api/avatar/wizard/media-session`
- Wizard status: `GET /api/avatar/wizard/media-session/status`
- Wizard runtime binding: `GET /api/avatar/wizard/performance-binding`
- Wizard performance context: `POST /api/avatar/wizard/performance-context`
- Wizard governed speech registration: `POST /api/avatar/wizard/governed-speech`
- Wizard governed speech revocation: `POST /api/avatar/wizard/governed-speech/revoke`
- Wizard permission-world authority: `POST /api/avatar/wizard/permission-world`
- Prism same-origin ingress: `POST /api/connectors/wizard/media-session`
- Prism runtime-binding bridge: `GET /api/connectors/wizard/performance-binding`
- Prism performance-context bridge: `POST /api/connectors/wizard/performance-context`
- Prism governed-speech bridge: `POST /api/connectors/wizard/governed-speech`
- Prism governed-speech revocation bridge: `POST /api/connectors/wizard/governed-speech/revoke`
- Prism connector status: `GET /api/connectors/wizard/status`

## User workflow

1. Open `/Applications/Prism GT.app` and the Wizard visualization at
   `http://127.0.0.1:8765/`.
2. In Prism, find the visible **Wizard Joe** status directly below the top action
   buttons. It must read **Connected** before playback begins.
3. Select **Player** from that status row or the bottom-right utility controls.
4. Choose a bundled track, open **Tracks**, or use **Link Audio** for local media.
5. Press **Play**. Prism changes to **Animating main audio** and the Wizard page
   changes to the matching green animation status.
6. TTS and speaker output switch both indicators to speech automatically. Main
   media resumes animation when speech pauses or ends; audio itself is never
   restarted by the connector.

The Prism sidecar port is intentionally dynamic in the packaged desktop app.
Launch Prism GT from `/Applications` instead of bookmarking a transient sidecar
URL. **Open Wizard** always targets the stable visualization port `8765`.

## One-time activation

Run the Wizard service installer once:

```bash
tools/install_local_wizard_service.sh
```

It generates or preserves one high-entropy shared token, installs the persistent
Wizard LaunchAgent, and writes Prism's private connector configuration to
`~/Library/Application Support/WizardJoeAvatar/prism-connector.env` with mode
`0600`. Quit and reopen Prism GT after first installation. No terminal-specific
environment is required for later desktop launches.

## Service configuration

The Wizard LaunchAgent is `com.jedisherpa.wizardjoeavatar`. Its local-only
environment requires:

```text
WIZARD_MEDIA_CONNECTOR_ENABLED=1
WIZARD_MEDIA_CONNECTOR_TOKEN=<shared random secret>
```

The PrismGT sidecar requires:

```text
PRISM_WIZARD_CONNECTOR_ENABLED=1
PRISM_WIZARD_BASE_URL=http://127.0.0.1:8765
PRISM_WIZARD_CONNECTOR_TOKEN=<same shared random secret>
```

The installer manages these values. Explicit process environment values still
override the private file for development and tests. Secrets must not be
committed, included in diagnostics, exposed to the browser, or placed on a
command line.

## Contract and privacy

Media Session V1 is a strict, full-state snapshot protocol shared by Python,
JavaScript, and Rust. It carries opaque IDs, playback time, source slot, media
kind, score binding, and motion preferences. It does not carry titles, URLs,
paths, transcripts, prompts, captions, or provider credentials.

Both ingress layers enforce exact JSON, a 16 KiB request limit, strict unknown
field rejection, and authentication. The Python boundary rejects requests with
a browser `Origin`. The Rust relay accepts only an explicit loopback base URL.

Governed conversational speech has an additional release boundary. Prism mints
an expiring approval only for exact final text that is neither pending nor a
clarification. TTS, its audio digest, provider timing when available, the active
Wizard runtime/package binding, the accepted media cursor, and the captured
performance context must all agree before Prism registers speech with Wizard or
starts the audio element. Progressive text and character performance then
project from that same audio element clock. Missing or invalid alignment uses a
deterministic local timing projection; it does not authorize different text.

Permission-world updates use the same connector instance, discovery identity,
and bearer token. The current Prism runtime does not yet own a generic user
permission-grant store, so its production producer sends a complete empty
authority snapshot on a bounded heartbeat. This fail-closed snapshot removes
only explicitly permission-managed scenery. It never infers grants from CDISS,
agreements, configured providers, memory availability, credentials, microphone
UI state, notifications, speech approval, or ledger history. Director
simulations are separately labeled and cannot control production projection.

## Runtime behavior

- Music without a compiled score uses a deterministic media-time groove.
- Podcasts and audiobooks without a compiled score use restrained speaking
  gestures and duration-driven mouth shapes.
- TTS uses the same speech fallback and preempts main-media performance only
  while its element is audible.
- Paused, ended, stopped, errored, or stale sessions release performance-owned
  state.
- Keyboard, gamepad, and remote control leases retain body authority.
- Reduced and still motion preferences are applied before controller mapping.

Compiled performance scores take precedence over scoreless fallbacks when a
matching score ID, revision, digest, character, package, and media binding is
available.

## Verification

```bash
python -m unittest discover -s tests
node --test src/pages/PrismDodecahedron/media/__tests__/*.test.js
cargo test --locked -p prism-cdiss-cli media_connector
cargo test --locked -p prism-cdiss-cli wizard_
npm run build
```

Governed speech verification must additionally prove:

1. Exact approved UTF-8 text is the only TTS input.
2. The browser-decoded audio digest matches the registered digest.
3. Runtime epoch, character, package, media cursor, context, speech, and timing
   identities all match before playback.
4. Text reveal follows the audio element's current time during play, pause,
   seek, and rate changes.
5. Revocation or a stale turn stops the obsolete performance.
6. Permission snapshots remain empty until a real permission authority is
   wired, and no browser route can create grants.

The local integration proof must observe all three states in order:

1. `source_slot=main` with music or narrative action.
2. `source_slot=speech` with speaking action and an active mouth shape.
3. `source_slot=main` at an advanced media time after speech ends.

## Recovery

If Prism reports `disabled`, rerun `tools/install_local_wizard_service.sh`, quit
Prism GT completely, and reopen it. If it reports `wizard_unavailable`, verify
the persistent listener and Wizard status.
If the Wizard returns `resync_required`, reload the Prism window so it creates a
new connector session and emits a full reconnect snapshot.

If the Wizard visualization is walking independently of audio, press its square
Stop button. Live media playback also cancels scripted demo paths automatically;
keyboard and gamepad control leases still retain body authority.
