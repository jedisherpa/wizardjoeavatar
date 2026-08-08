# Character Director Release Gate Checkpoint

Date: 2026-08-08

## Purpose

`tools/verify_character_director_release.py` is the commit-bound release
closure gate for the Python Character Director. It verifies an immutable Git
commit, not the active working tree. Concurrent local work can remain present,
but no untracked file can satisfy a declared or manifest-discovered release
input.

The gate emits a schema-v1 JSON receipt and exits nonzero on every incomplete,
untracked, undeclared, checksum-mismatched, unlocked, timed-out, or failed
phase.

## Fast mode

Fast mode performs only deterministic commit/input checks and is suitable for
focused tests and fixture repositories:

```sh
python3 tools/verify_character_director_release.py \
  --mode fast \
  --revision HEAD \
  --output /tmp/character-director-release-fast.json
```

It resolves the selected revision to a commit, inventories that commit's Git
tree, validates required files and trees, follows the declared character and
review-library manifests, verifies committed checksums (including Git LFS
object IDs), and confirms verifier imports are represented in
`pyproject.toml`, `requirements.txt`, and `uv.lock`.

A schema-v1 fixture contract may be supplied with `--contract`. This is the
unit-test path used to prove that tracked-but-undeclared and local-only inputs
fail closed without running asset builds or servers.

## Full mode

Run full mode only against the exact candidate commit to be promoted:

```sh
python3 tools/verify_character_director_release.py \
  --mode full \
  --revision <full-commit-sha> \
  --output /tmp/character-director-release-full.json
```

Full mode first requires fast closure, then:

1. Clones and detaches the exact candidate commit in a disposable checkout.
2. Materializes the declared historical remote ref from the real upstream.
3. Runs `uv sync --frozen` and probes all verifier imports.
4. Rebuilds Dragon and Robin/Speech review libraries from tracked sources.
5. Runs the Kingfisher pair-review verifier.
6. Runs the focused gate tests, Python-scope boundary, and complete Python
   suite with explicit time limits.
7. Starts the real loopback server and requires health plus an `INIT` message
   and binary WebSocket frame for Wizard Joe, Kingfisher, Dragon, Robin, and
   Speech.
8. Requires the isolated checkout to remain free of unignored generated files.

Use `--offline` only when every declared remote-tracking ref already exists in
the source repository. Use `--keep-checkout <new-path>` only to retain a failed
isolated checkout for diagnosis.

## Current checkpoint

All eight focused fixture/unit tests pass. The full gate has **not** been run
for this uncommitted checkpoint and no production-release claim is made.

Before a full receipt can pass, the scoped gate changes must be committed so
they exist in the selected Git tree. The candidate must also close any input
reported by fast mode, provide the referenced Git LFS objects and upstream
historical ref, complete both generated-library rebuilds, pass the complete
suite within its bound, and pass all five real-server smoke checks.
