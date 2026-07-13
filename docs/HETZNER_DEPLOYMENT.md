# Wizard Joe Hetzner Deployment

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
