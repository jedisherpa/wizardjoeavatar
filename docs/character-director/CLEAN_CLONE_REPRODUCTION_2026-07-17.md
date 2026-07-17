# Clean-Clone Reproduction Receipt

Date: 2026-07-17

## Source

The Python branch was cloned from GitHub into a new temporary directory:

```text
repository: https://github.com/jedisherpa/wizardjoeavatar.git
branch: codex/character-director
commit: cee9de821abe46ec8a91c8860426d85247a0353c
clone: /tmp/wizardjoe-character-director-clean
```

The source worktree and the persistent service on port `8765` were not used by
the cloned runtime.

## Environment Creation

`uv 0.11.7` created a new `.venv` from `uv.lock` with CPython 3.13.13:

```bash
uv sync --frozen
```

Twenty locked packages installed successfully.

## Repository Checkpoint Precondition

The first full test run used `git clone --single-branch`. One of 428 tests
failed closed because the program registry requires the historical remote
checkpoint `origin/codex/python-asciline-avatar`, which a single-branch clone
intentionally omits.

The missing declared checkpoint was fetched without changing the checked-out
source:

```bash
git fetch origin \
  codex/python-asciline-avatar:refs/remotes/origin/codex/python-asciline-avatar
```

The focused repository-contract test then passed. The complete suite was run
again:

```bash
.venv/bin/python -m unittest discover -s tests
```

Result: 428 tests passed in 125.654 seconds.

## Runtime Check

The clone was started independently on port `8876`:

```bash
.venv/bin/python tools/run_wizard_avatar_server.py \
  --host 127.0.0.1 --port 8876
```

The compatibility-mode server correctly did not expose the authenticated
packaged-app health route. Its actual documented contracts passed:

- `GET /api/avatar/wizard/state`: HTTP 200.
- `ws://127.0.0.1:8876/ws/avatar/wizard?codec=adaptive`: valid `INIT:`
  bootstrap followed by a 5,709-byte binary ASCILINE frame.
- Subsequent state: simulation tick 5,772, 24.0049 FPS, zero hub queue drops.

The cloned server then shut down normally. Port `8765` remained owned by the
pre-existing local service throughout.

## Finding

This proves installation, the complete automated suite, and a live ASCILINE
frame from a fresh GitHub clone under the current macOS user. It does not claim
an independent operating-system account, a clean machine, package installation,
or rollback drill; those stronger acceptance gates remain open.
