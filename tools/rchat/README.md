# Wizard Joe RCHAT Validator

Standalone Rust validation for `wizardjoe-rchat-registry/v1` and
`wizardjoe-rchat-gate/v1` records.

```bash
cargo run --manifest-path tools/rchat/Cargo.toml -- \
  registry docs/cartoon-animation-program/rust-chatbot/registry.json

cargo run --manifest-path tools/rchat/Cargo.toml -- \
  gate evidence/cartoon-animation-program/rust-chatbot/gates/Q2.json \
  --registry docs/cartoon-animation-program/rust-chatbot/registry.json

cargo run --manifest-path tools/rchat/Cargo.toml -- \
  scope docs/cartoon-animation-program/rust-chatbot/registry.json \
  RCHAT-FLOW-060 --base <base-sha> --head HEAD

cargo run --manifest-path tools/rchat/Cargo.toml -- \
  evidence write tools/rchat/tests/fixtures/evidence-run.json \
  --ledger target/rchat-evidence/frames.ndjson \
  --manifest target/rchat-evidence/manifest.json

cargo run --manifest-path tools/rchat/Cargo.toml -- \
  evidence validate target/rchat-evidence/frames.ndjson \
  target/rchat-evidence/manifest.json
```

Registry CLI validation includes both structural checks and material checks for
every `ACCEPTED` receipt. Material checks resolve the base and result commits,
read evidence bytes from the result commit, recompute SHA-256 values, and verify
that every path changed by the commit range is covered by the work item's
`path_allowlist`. Accepted items sharing both `gate_id` and `result_sha` form an
aggregate receipt cohort: changed paths may be covered by the union of that
cohort's allowlists, but each item must still own at least one changed path or
material evidence path through its individual allowlist. A one-item cohort
retains strict per-item coverage. The in-memory `validate_registry` API performs
structural validation only; use `validate_registry_path` or the CLI for a
release audit.

Successful validation prints a compact PASS line and exits zero. Contract and
material violations are sorted by JSON path, stable error code, and message,
then printed and returned with exit code one. File, JSON, Git invocation, and
usage failures exit two. Every violation identifies the receipt and corrective
action so live-registry failures can be repaired without changing status
implicitly.

The scope command requires the registry branch to match the checked-out branch
and validates committed, staged, unstaged, and untracked paths by default.
`--committed-only` restricts CI checks to the requested commit range.

The evidence writer emits deterministic LF-delimited per-frame NDJSON and a
compact manifest containing ledger, stream, count, status, and failure
receipts. PASS is derived only from one or more contiguous valid frames with no
quality failures. Empty runs are rejected unless they record an explicit SKIP;
SKIP exits 77 and FAIL exits 1.
