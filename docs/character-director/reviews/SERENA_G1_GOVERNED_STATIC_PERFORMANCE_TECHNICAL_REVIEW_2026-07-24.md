# Serena G1 Governed Static Performance Technical Review

Date: 2026-07-24

## Review Scope

Independent review covers the uncommitted Serena G1 static-performance
checkpoint:

- verified V2 capability-manifest derivation;
- preservation of the legacy Wizard Joe V1 manifest;
- Serena-owned graph, runtime-profile, permission, and provenance identities;
- governed compilation of `mentoring_invitation`;
- production hub execution and release;
- reduced-motion suppression;
- deterministic replay;
- regression tests and evidence documentation.

## Decision

**ACCEPT.** The final independent review found no P0-P2 findings.

## Findings

The first review rejected the candidate with one P2:

- The compiler derived `package_version` from capability-manifest schema V1,
  causing Serena's verified V2 package to publish the false version `1.0.0`.
  Digest-based admission remained secure, but the metadata could mislead
  downstream version checks and caches.

The correction:

- adds optional `package_schema_version` to CharacterCapabilityManifestV1;
- emits it for verified V2 packages while leaving Wizard Joe V1 unchanged;
- compiles Serena as package version `2.0.0`;
- asserts the exact version in Serena's production compiler test.

The reviewer also identified two P3 coverage gaps. Both were closed before the
second review:

- Serena V2 derivation is now explicitly tested with workstation source-image
  lookup prohibited;
- Serena-specific negative tests reject foreign character, package, and
  capability-manifest identities.

The second review found no remaining material P3 gap.

## Verification

- Independent focused and related pass: 85 tests passed.
- Lead broad performance and schema pass: 180 tests passed.
- Serena focused gate: 10 tests passed.
- Python bytecode compilation: passed.
- Acceptance JSON parse: passed.
- `git diff --check`: passed.
- Wizard Joe legacy capability-manifest golden digest remained
  `sha256:0cdf29861befacf05f0fe3bb01ffcd8103d5b20bc812818a0626f75c6ee9de74`.
- Serena compiled package identity is `2.0.0`.

The reviewer edited no files.

## Explicit Limits

Acceptance of this checkpoint would not prove Serena locomotion, flight,
permission-world visuals, governed speech generation, live Prism audiovisual
synchronization, or registry admission. Those remain independently gated.
