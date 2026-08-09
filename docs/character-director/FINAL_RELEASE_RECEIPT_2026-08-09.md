# Character Director Final Release Receipt

Date: 2026-08-09

## Decision

The Python Character Director release scope is complete at commit
`0a237c6bd396716a65be160292be94cd68b3f4a7` on
`codex/character-director`.

The user explicitly deferred the Kingfisher 66-pair additional-pose program.
That deferral is part of the release contract: the existing 110-pose
Kingfisher library ships, while every added paired-beak pose remains
unapproved, unadmitted, and unintegrated. The resumable review procedure is in
`KINGFISHER_ADDITIONAL_POSES_HANDOFF_2026-08-08.md`.

This receipt closes the commit-bound Python source, asset, dependency, test,
and runtime-smoke gates. It does not retroactively approve the held Kingfisher
poses or erase the separately documented limits of historical audiovisual,
long-soak, and independent-user package evidence.

## Immutable Candidate

| Field | Value |
| --- | --- |
| Repository | `https://github.com/jedisherpa/wizardjoeavatar.git` |
| Branch | `codex/character-director` |
| Candidate commit | `0a237c6bd396716a65be160292be94cd68b3f4a7` |
| Gate | `tools/verify_character_director_release.py --mode full` |
| Result | **PASS** |
| Finished | `2026-08-09T08:27:41.697115Z` |
| Issues | none |
| Isolated checkout | clean before and after verification |

The committed full-gate receipt is:

`evidence/character-director/release-gate/character-director-release-full-0a237c6b.json`

SHA-256:

`a6900fec95ace677b413754650e6cdc5fb97ee4dc9867d001ff95ed5b6cd42d8`

The committed complete-suite shard receipt is:

`evidence/character-director/release-gate/character-director-python-suite-shards-0a237c6b.json`

SHA-256:

`1868976d31a3ce76c76b34e3f534adeb1a9df91d9d2909496161127507f84f71`

## Verified Closure

The full gate performed all of the following from a disposable clone of the
exact candidate commit:

1. Checked out the exact commit and initialized Git LFS locally.
2. Fetched and materialized all required LFS objects; no pointer was accepted
   as an asset.
3. Installed the frozen `uv.lock` environment and imported every verifier
   dependency.
4. Rebuilt the Dragon and Robin/Speech review libraries from tracked sources.
5. Verified the Kingfisher hold: 66 added pairs, zero approvals, zero runtime
   admissions, zero integrations, and the existing 110-pose shipping index.
6. Passed focused release tests and the Python-scope boundary.
7. Executed all 164 discovered Python test files across four deterministic
   subprocess shards. No file was omitted and all four shards passed.
8. Started the real loopback server and passed HTTP plus binary-WebSocket
   smokes for Wizard Joe, the existing Kingfisher library, Dragon, Robin, and
   Speech.
9. Confirmed the isolated checkout remained clean after every build and smoke.

## Complete Python Suite

| Shard | Test files | Duration | Result |
| ---: | ---: | ---: | --- |
| 1 | 40 | 86.846 s | pass |
| 2 | 42 | 222.549 s | pass |
| 3 | 41 | 3146.831 s | pass |
| 4 | 41 | 282.931 s | pass |
| **Total** | **164** | process-overlapped | **pass** |

The slow third shard completed normally and did not time out. Sharding changes
only process placement; the receipt records the complete deterministic file
inventory and proves that every discovered test file executed exactly once.

## Runtime Smokes

All five runtime smokes passed health, initial protocol state, and binary frame
delivery:

- Wizard Joe default runtime.
- Existing 110-pose Kingfisher library.
- Dragon review library.
- Robin review library.
- Speech review library.

The shared server health envelope retains the Wizard service identity. The
non-Wizard smokes are bound by their tracked review-library indexes in the
receipt; they are package-selection smokes, not claims that the health
`character_id` field changes dynamically.

## Kingfisher Boundary

The release must continue to satisfy:

```sh
python3 tools/verify_deferred_kingfisher_scope.py \
  --shipping-index assets/reference/characters/kingfisher/compiled/library-index.json \
  --review-index assets/reference/characters/kingfisher/pair-review-compiled/library-index.json \
  --ledger assets/reference/characters/kingfisher/legacy-pairs-v1/pair-review-ledger.json
```

Do not promote the held 66-pair expansion by editing a manifest directly. When
work resumes, use the one-pair-at-a-time native-size approval workflow in the
Kingfisher handoff and rerun the complete release gate against a new immutable
candidate commit.

## Reproduction

From a clean clone with Git LFS, `uv`, and the locked Python toolchain
available:

```sh
python3 tools/verify_character_director_release.py \
  --mode full \
  --revision 0a237c6bd396716a65be160292be94cd68b3f4a7 \
  --output /tmp/character-director-release-full-0a237c6b.json
```

The command must exit zero, report `passed: true`, report no issues, execute
all 164 test files, pass all five runtime smokes, and leave its isolated
checkout clean.
