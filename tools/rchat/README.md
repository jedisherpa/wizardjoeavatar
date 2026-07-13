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

Successful validation prints a compact PASS line and exits zero. Contract
violations are printed with stable error codes and JSON-style paths, then exit
one. File, JSON, and usage failures exit two.
