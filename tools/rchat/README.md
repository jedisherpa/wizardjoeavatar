# Wizard Joe RCHAT Validator

Standalone Rust validation for `wizardjoe-rchat-registry/v1` and
`wizardjoe-rchat-gate/v1` records.

```bash
cargo run --manifest-path tools/rchat/Cargo.toml -- \
  registry docs/cartoon-animation-program/rust-chatbot/registry.json

cargo run --manifest-path tools/rchat/Cargo.toml -- \
  gate evidence/cartoon-animation-program/rust-chatbot/gates/Q2.json \
  --registry docs/cartoon-animation-program/rust-chatbot/registry.json
```

Registry CLI validation includes both structural checks and material checks for
every `ACCEPTED` receipt. Material checks resolve the base and result commits,
read evidence bytes from the result commit, recompute SHA-256 values, and verify
that every path changed by the commit range is covered by the work item's
`path_allowlist`. The in-memory `validate_registry` API performs structural
validation only; use `validate_registry_path` or the CLI for a release audit.

Successful validation prints a compact PASS line and exits zero. Contract and
material violations are sorted by JSON path, stable error code, and message,
then printed and returned with exit code one. File, JSON, Git invocation, and
usage failures exit two. Every violation identifies the receipt and corrective
action so live-registry failures can be repaired without changing status
implicitly.
