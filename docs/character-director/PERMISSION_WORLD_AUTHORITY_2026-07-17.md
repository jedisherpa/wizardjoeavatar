# Permission-World Authority Receipt

Date: 2026-07-17

Python code receipt:
`4903699c3f6a9a627fd9b52ee3e5058f5e9c2629`

Prism code receipt:
`a53b48d6626c5494336406aaa9b48bd52460d55e`

## Decision

The Character Director now uses the existing Prism `AgreementStore` as the
canonical producer for production character permission facts. It does not use
the Python simulator, browser state, an animation-side grant, or a parallel
authority database.

The initial production capability is deliberately narrow:

| Field | Exact value |
| --- | --- |
| Prism authority scope | `local_character_runtime` |
| Capability | `prop:memory_notebook` |
| Required/granted scope class | `current_character` |
| Purpose | `conversation_continuity` |
| Surface | `wizard.stage` |

The relay contains only this content-free tuple, status/timestamps, surfaces,
and canonical hashes. Agreement statements, user identity, memory contents,
prompts, replies, tokens, paths, and model/provider data do not cross the
permission-world boundary.

## End-To-End Flow

1. `/rag on` proposes and confirms a typed permission in the canonical
   `AgreementStore`. `/rag off` revokes that authority.
2. The existing Prism media connector reads current authority records for the
   internal character-runtime scope and maps only the allowlisted exact tuple
   into Permission World V1.
3. Python accepts the snapshot only after strict schema, canonical hash,
   source-epoch, monotonic observation, and receipt-time checks.
4. The character capability manifest binds the notebook to the same exact
   scope, purpose, and surface. A missing, duplicate, wrong, or unbound rule
   fails manifest/index construction or projection closed.
5. The existing square-cell frame projector paints the admitted notebook as a
   7x7, 49-cell overlay. No PNG or SVG is introduced into runtime rendering.
6. The connector accepts success only when the Python ACK matches source epoch
   SHA, observed time, state SHA, and permission count exactly.

## Revocation And Race Semantics

- Memory reads return empty without the exact current confirmed authority.
- Memory writes revalidate after asynchronous embedding and perform the insert
  while holding the same authority-store lock used by revoke and expiry. A
  write therefore completes before revocation or does not happen.
- Current-time authority queries sample the clock after acquiring that lock,
  preventing contention from carrying a pre-expiry timestamp past expiry.
- Python updates permission policy during snapshot ingestion, reprojects it
  after off-thread rendering, and discards the rendered frame when authority
  changed or expired before publication.
- Discovery/runtime rotation cannot accept an old ACK: connector generation
  validation remains locked through status publication.

## Verification

Fresh commands at the paired code receipts:

```text
# Prism
cargo test -q -p prism-cdiss-core
# 674 primary tests passed; all integration/doc targets passed

cargo test -q -p prism-cdiss-cli
# 297 unit tests and 10 integration tests passed

cargo fmt --check
# passed

# Python
python3 -m unittest discover -s tests
# 450 tests passed

python3 tools/validate_python_scope.py .
# 64 files scanned; zero violations
```

Regression coverage includes exact tuple matching, wrong-purpose rejection,
grant/revoke, elapsed expiry, unlink and scope mismatch, malformed authority,
49-cell visual bounds, stale authority during render, expiry during render,
revoke during asynchronous embedding, contention across expiry, obsolete
connector-generation ACKs, and the `/rag on` to relay to `/rag off` path.

Two independent review passes identified and then rechecked the write/revoke,
generation-publication, and lock-wait/expiry races. The final review reported
no remaining P1/P2 findings for acceptance criteria 27 and 28.

## Boundary And Remaining Work

This receipt closes the missing canonical permission-producer gap for the local
character runtime. It does not claim multi-user Telegram authority, arbitrary
third-party capability mapping, professional animation review, clean-user
package rollback, or the outstanding 8-hour and 24-hour V2 soaks. Those remain
separate acceptance work in `ACCEPTANCE_CRITERIA_MATRIX.md`.
