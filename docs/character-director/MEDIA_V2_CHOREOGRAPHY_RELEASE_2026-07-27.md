# Media V2 and Choreography Release Record

Date: 2026-07-27

Python branch: `codex/character-director`

Prism branch: `codex/character-director-prism`

## Scope

This release extends the existing Python performance engine and the existing
Prism media connector. It does not add a second connector or a Rust animation
runtime.

Delivered:

- strict Media Session V2 snapshots and acknowledgements carrying the admitted
  persona, character, package digest, and admission hash;
- frozen Media Session V1 compatibility for the exact legacy Wizard Joe
  package only;
- same-version acknowledgements and exact admission reconciliation across
  browser, Rust relay, and Python runtime;
- a closed, duplicate-safe, package-bound choreography dictionary contract;
- enforced comprehensive, focused, and game-motion interpretation classes;
- package dictionaries for Wizard Joe and Serena Quill;
- reproducible comprehensive candidate dictionaries for Robin and Speech;
- distinct review dictionaries for all twelve 48-pose JoeVille libraries and
  Liana; and
- inventory and admission documentation for Dragon and Kingfisher without
  fabricating package IDs.

## Frozen Hashes

| Artifact | SHA-256 |
| --- | --- |
| Wizard Joe choreography dictionary | `53067d3ef426bbfcc3c3498dbde702c64dc85ba00e39cc3b6c7c62b24960f672` |
| Serena Quill choreography dictionary | `df4425f85560489bb02290007b2e4fd1b7234403bc1a29e564435d34a40499b0` |
| Serena Quill V2 character package | `33b37cfb14f95664992f9bd01d7a8b8474500f092a72d74d3cba53f96404e4d0` |
| Serena Quill capability manifest | `1091df47baf476ea34051fc124e484291c3919212704dc4eb34536249eae42f1` |

## Verification

Green release checks:

- Python affected-contract group: 78 tests;
- Python HD, performance, media V2, and server group: 38 tests;
- Python dictionary/package rerun after class invariants: 37 tests;
- Python frozen-V1 permission propagation: 1 test;
- Python capability manifest with tracked evidence materialized: 9 tests;
- Prism browser media suite: 75 tests;
- Rust media connector regression: 29 tests;
- Rust V2 HTTP and schema-focused checks: 5 tests;
- `cargo check -p prism-cdiss-cli`;
- `cargo fmt --all -- --check`; and
- `git diff --check` in both worktrees.

Both local observation servers returned HTTP 200 on ports 8665 and 8765 after
the changes.

The broad sparse-worktree discovery executed 778 tests. Its import phase
reported 41 errors for tracked tools omitted from this sparse checkout. After
materializing the tracked animation-quality evidence, the two capability
assertions from that run passed. Three existing head/eye/contact/overlay
assertions remain outside this release's modified modules and are not used as
its release gate. The affected contract and runtime suites above are the
release evidence.

## Preserved Review Material

The ignored Robin and Speech runtime-candidate directories remain present.
Their generator is tracked, and their review output was not deleted, replaced,
or silently production-admitted.

Dragon remains classified as comprehensive performance but requires stable
graph/package IDs before its dictionary can be executable. Kingfisher remains
an intake blocker until its comprehensive source library is present in the
tracked worktree.
