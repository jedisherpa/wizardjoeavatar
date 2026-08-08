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
object IDs), and confirms the NumPy and SciPy verifier dependencies are
represented in `pyproject.toml`, `requirements.txt`, and `uv.lock`.

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
2. Fetches and checks out the selected commit's Git LFS objects, then rejects
   any path that remains a pointer.
3. Materializes the declared historical remote ref from the real upstream.
4. Runs `uv sync --frozen` and probes all verifier imports.
5. Rebuilds Dragon and Robin/Speech review libraries from tracked sources.
6. Runs the Kingfisher pair-review verifier.
7. Runs the focused gate tests, Python-scope boundary, and complete Python
   suite with explicit time limits.
8. Starts the real loopback server and requires health plus an `INIT` message
   and binary WebSocket frame for Wizard Joe, Kingfisher, Dragon, Robin, and
   Speech.
9. Requires the isolated checkout to remain free of unignored generated files.

Use `--offline` only when every declared remote-tracking ref already exists in
the source repository. Use `--keep-checkout <new-path>` only to retain a failed
isolated checkout for diagnosis.

## Current checkpoint

All eight focused fixture/unit tests pass. The first full-gate run against
commit `4471483641d3606f70731123a7296fc4ccf02389` correctly failed in the
disposable environment because SciPy, imported by a tracked visual verifier,
was not declared. The dependency contract now includes SciPy; a passing full
receipt is still required before a production-release claim can be made. The
next run exposed unmaterialized Git LFS pointers in the Dragon source corpus;
full mode now performs and verifies LFS materialization before invoking any
asset builder.

Before a full receipt can pass, the scoped gate changes must be committed so
they exist in the selected Git tree. The candidate must also close any input
reported by fast mode, provide the referenced Git LFS objects and upstream
historical ref, complete both generated-library rebuilds, pass the complete
suite within its bound, and pass all five real-server smoke checks.
