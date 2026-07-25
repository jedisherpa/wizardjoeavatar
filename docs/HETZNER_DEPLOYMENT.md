# Wizard Joe Hetzner Deployments

The Rust avatar server deploys from `codex/build-repeatable-avatar-animation` to an isolated service on `root@5.78.137.112`.

| Surface | Value |
|---|---|
| Credential environment | `jedisherpa/prism-geometry-talk` / `hetzner` |
| Required secret | `CRX41_HETZNER_SSH` |
| Deployment bridge branch | `codex/wizardjoe-avatar-deploy-bridge-v2` |
| Remote root | `/opt/wizardjoe-avatar` |
| systemd unit | `wizardjoe-avatar.service` |
| Internal listener | `127.0.0.1:18787` |
| Public endpoint | `https://wizardjoe.5.78.137.112.sslip.io/` |

The isolated bridge workflow checks out `jedisherpa/wizardjoeavatar` at `codex/build-repeatable-avatar-animation`, builds the server on Linux, runs Rust and browser-module checks, uploads only the compiled server, installs a dedicated unprivileged service, adds an isolated Nginx virtual host with WebSocket proxying, provisions its dedicated Let's Encrypt certificate, and then verifies both the state API and rendered page over HTTPS.

`CRX41_HETZNER_SSH` is read only by the bridge job from the existing `hetzner` environment. The key is never copied into the Wizard Joe repository.

The deployment does not modify the Prism repository's production branches or reuse another application's process, port, directory, or systemd unit.

## Python Character Director

The Python/ASCILINE Character Director is deployed beside the Rust server. It
does not replace, restart, or share the Rust process.

| Surface | Value |
|---|---|
| Source branch | `codex/character-director` |
| Credential environment | `jedisherpa/prism-geometry-talk` / `hetzner` |
| Deployment bridge branch | `codex/wizardjoe-python-deploy-bridge` |
| Remote root | `/opt/wizardjoe-avatar-python` |
| systemd unit | `wizardjoe-avatar-python.service` |
| Internal listener | `127.0.0.1:18788` |
| Public endpoint | `https://wizardjoe-python.5.78.137.112.sslip.io/` |
| Runtime proof | `/api/avatar/wizard/runtime-identity` |
| Persistent score root | `/var/lib/wizardjoe-avatar-python/scores` |

The bridge accepts an exact Wizard Joe commit SHA, verifies the Python runtime
checkpoint before upload, installs an immutable release, and requires the
public runtime identity to report that SHA with a clean worktree. The Python
listener remains loopback-only behind its dedicated Nginx host. The bridge
also verifies that `wizardjoe-avatar.service` and the Rust public state API
remain healthy before it reports success.

The Python systemd unit must create the persistent score root with ownership
restricted to its unprivileged service account and export
`WIZARD_SCORE_ROOT=/var/lib/wizardjoe-avatar-python/scores`. Governed speech is
fail closed when that repository is unavailable; a deploy is not complete
until live score preparation, exact-generation reload, and a score-bound
registration receipt have been exercised through the private connector. The
same smoke test must prove that an altered turn or utterance cannot redeem a
published score and that a successful registration consumes its one-use
preparation grant. It must also prove exact next-epoch admission, 30-second
monotonic expiry, supersession invalidation, and bounded generated-live-score
retention.
