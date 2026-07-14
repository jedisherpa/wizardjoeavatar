# Wizard Joe Companion Discovery and Lifecycle Protocol

Status: locked for local macOS implementation

## Purpose

Wizard Joe Companion and Prism GT are separate applications. Prism GT owns audio,
persona speech, governance, and media state. Wizard Joe owns deterministic avatar
performance. This protocol lets those applications find each other without a
fixed port, launch order, terminal command, or secret in a packaged frontend.

## Rendezvous File

Wizard Joe Companion is the only writer. It atomically replaces:

`~/Library/Application Support/Wizard Joe Companion/connector-v1.json`

The parent directory and file must be user-only. The file mode is `0600` on
Unix. The writer creates a temporary sibling, flushes it, applies permissions,
and renames it over the destination. Symlinks, non-regular files, files larger
than 16 KiB, group/world-readable files, and malformed documents are rejected.

The V1 document is strict JSON:

```json
{
  "schemaVersion": 1,
  "baseUrl": "http://127.0.0.1:49152",
  "mediaToken": "<opaque per-launch secret>",
  "runtimeEpoch": "<opaque non-secret runtime identity>",
  "pid": 12345,
  "issuedAtUnixMs": 1784052000000,
  "expiresAtUnixMs": 1784052120000
}
```

No unknown fields are accepted. `baseUrl` must use plain HTTP, a literal
loopback address, no user information, query, fragment, or path, and a nonzero
dynamic port. `mediaToken` is 32-1024 non-whitespace ASCII bytes and is never
returned by diagnostics. `runtimeEpoch` is bounded opaque ASCII. The issue and
expiry timestamps use wall-clock time only for freshness checks; media timing
continues to use monotonic clocks.

## Writer Lifecycle

1. The Companion reserves an available loopback port.
2. It mints distinct app-control and media-relay credentials.
3. It starts the packaged Python runtime with those credentials passed only in
   the child environment.
4. It verifies the versioned health response, runtime epoch, PID, and protocol.
5. It publishes the rendezvous file with a short rolling expiry.
6. It refreshes the file while the verified child remains healthy.
7. On graceful quit it removes only a file whose runtime epoch it owns.
8. On crash, the short expiry makes the file unusable without trusting PID reuse.

The app-control token is never written to this file. Prism receives only the
media-relay token required for numeric performance snapshots.

## Reader Lifecycle

Prism GT may start before or after Wizard Joe Companion. Its local backend keeps
the connector available in a discovery state and refreshes the rendezvous file
before status and relay operations. A valid document replaces the active relay
transport when its runtime epoch or endpoint changes. Missing, expired, invalid,
or unreadable discovery produces `unavailable`, never `connected`.

Prism may retain the historical environment configuration as an explicit
development compatibility override. It must not copy a discovered token into a
browser bundle, WebView global, URL, log line, error message, or status payload.

## Health and Recovery

The Companion validates `GET /api/companion/health` before publication. The
response is privacy-safe and includes the health schema version, protocol
version, runtime epoch, PID, readiness, frame-hub state, and connector-enabled
flag. It contains no token, media identity, transcript, URL, or local path.

Ordinary recovery is bounded:

- an unhealthy child receives an authenticated graceful shutdown request;
- the supervisor waits, then terminates only the child it spawned;
- automatic restarts use exponential backoff and a finite retry budget;
- a manual Restart action resets the budget;
- token rotation publishes a new runtime epoch and invalidates the old file;
- Prism treats stale acknowledgements, scheduler errors, and transport changes
  as degraded or unavailable until a fresh successful acknowledgement arrives.

## Privacy Boundary

The connector carries the existing bounded media-session contract: identifiers,
timing, playback state, performance mode, intensity, motion preference, and
disabled channels. It does not carry audio bytes, transcript or persona text,
file paths, URLs, private media metadata, memory contents, or governed actions.
Wizard Joe cannot invoke Prism actions or bypass approval and policy boundaries.

## Compatibility and Rollback

The existing `com.jedisherpa.wizardjoeavatar` LaunchAgent and fixed-port service
remain untouched during isolated verification. Compatibility configuration under
`WizardJoeAvatar/prism-connector.env` remains supported for the legacy service
when selected with `PRISM_WIZARD_CONNECTOR_CONFIG`, but a valid explicit
environment override wins over Companion discovery. The historical file is not
an implicit override because that would permanently mask a running Companion.

Rollback is removal of the new Companion application and its own Application
Support directory. It does not require changing Prism data, governance state,
the preserved Prism application, or the historical LaunchAgent.
