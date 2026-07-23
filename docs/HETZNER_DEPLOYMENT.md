# Wizard Joe Hetzner Deployment

The Rust avatar server deploys from `codex/rust-pixelgraph-primary` to an isolated service on `root@5.78.137.112`.

| Surface | Value |
|---|---|
| Credential environment | `jedisherpa/prism-geometry-talk` / `hetzner` |
| Required secret | `CRX41_HETZNER_SSH` |
| Deployment bridge branch | `codex/wizardjoe-avatar-deploy-bridge-v2` |
| Remote root | `/opt/wizardjoe-avatar` |
| systemd unit | `wizardjoe-avatar.service` |
| Internal listener | `127.0.0.1:18787` |
| Public endpoint | `https://wizardjoe.5.78.137.112.sslip.io/` |

The isolated bridge workflow checks out `jedisherpa/wizardjoeavatar` at the exact
pushed commit on `codex/rust-pixelgraph-primary`, proves that commit belongs to the
authorized branch, builds the server on Linux, and runs both Rust workspaces plus the
browser tests. It packages the compiled server and all 260 v6 graphs only after
checking the exact ID census, every manifest invariant, every compressed graph hash,
and every stored-graph identity and frame.

Activation uses an immutable release directory and atomic `current` link. The bridge
first smokes the candidate on a private loopback port, then verifies the state API,
full native pose-graph catalog, graph payloads, clips, newsroom layers, WebSocket
stream, rendered page, and exact Git SHA over HTTPS. Interrupted retries recover stale
activation markers before switching. A failed public smoke restores the previous
release and must prove both local and public health at the previous SHA.

`CRX41_HETZNER_SSH` is read only by the bridge job from the existing `hetzner` environment. The key is never copied into the Wizard Joe repository.

The deployment does not modify the Prism repository's production branches or reuse
another application's process, port, directory, or systemd unit. Third-party GitHub
Actions are pinned to immutable commit SHAs.
