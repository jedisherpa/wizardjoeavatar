# Character Admission Contract V1

Date: 2026-07-25

## Purpose

Character admission answers one narrow question: which persona is authorized to
perform through which character package?

The contract is separate from visual-review status, motion parity, score
approval, voice approval, and deployment. A source archive, review projection,
or complete motion library is not runtime admission.

## Canonical Admission

The canonical V1 admission content is:

```json
{
  "schema_version": 1,
  "persona_id": "persona:wizard-joe",
  "character_id": "wizard-joe-v1",
  "package_digest": "sha256:..."
}
```

`admission_sha256` is the lowercase SHA-256 reference of the UTF-8 bytes of the
repository's canonical JSON V1 encoding of that object. The hash is not
self-inclusive.

The production registry is schema version 2. Each entry stores the exact
persona, character, package digest, and admission digest. The loader rejects:

- unknown or missing fields;
- malformed identifiers or digests;
- package paths outside the registry directory;
- package-byte digest mismatches;
- admission-digest mismatches;
- duplicate persona or character identities; and
- a default character absent from the registry.

Registry membership is the runtime-admission decision. Review libraries and
candidate packages remain denied until a product-approved registry change is
committed and deployed.

`CharacterRegistry` objects are loader-issued and sealed. Runtime applications
cannot obtain admission by directly constructing a registry or passing a raw
admission object. Tests exercise the same file-loaded authority path as
production.

## Performance Binding

Python publishes an active performance binding V2:

```json
{
  "schema_version": 2,
  "wizard_runtime_epoch": 1,
  "admission": {
    "schema_version": 1,
    "persona_id": "persona:wizard-joe",
    "character_id": "wizard-joe-v1",
    "package_digest": "sha256:..."
  },
  "admission_sha256": "sha256:...",
  "reconciliation_generation": 0,
  "revocation_generation": 0,
  "binding_sha256": "sha256:..."
}
```

`binding_sha256` hashes the canonical JSON V1 encoding of every field except
itself. Browser and Rust consumers independently recompute both hashes.

The accepted tuple must remain exact at:

1. reply approval;
2. performance-context capture;
3. live-score compilation and publication;
4. browser TTS preparation;
5. post-score binding refresh;
6. governed registration;
7. Rust relay;
8. Python registration receipt;
9. serialized browser registration ownership; and
10. the browser's final pre-play check and correlated cleanup.

Any persona, character, package, admission, reconciliation, revocation, or
binding drift fails closed.

## Legacy Migration

Performance binding V1 is accepted only for this exact frozen tuple:

- persona: `persona:wizard-joe` (derived);
- character: `wizard-joe-v1`;
- package:
  `sha256:e35d9fee572e8f984a25a3776e2be51e1920b2a09f568170f12ccd3f0851b387`.

V1 is not a generic compatibility path. No non-Wizard persona or package may
use it.

## Character Onboarding Gate

Admit one character at a time:

1. finish and approve the canonical transparent pixel-graph package;
2. freeze its package bytes and digest;
3. choose one stable persona ID;
4. compute and independently verify the admission digest;
5. add exactly one production-registry entry;
6. run Python, browser, and Rust negative and positive contract tests;
7. capture a governed audiovisual acceptance bundle for the exact commits; and
8. deploy with a preserved rollback release.

Removing or changing an admission is a breaking authority change and requires a
new binding, revocation, acceptance evidence, and deployment record.

## Current Status

Only Wizard Joe is production-admitted. Serena Quill and all JoeVille parity
libraries remain review-only. The observer at `http://127.0.0.1:8665/` is a
visual comparison surface and confers no runtime authority.

The governed-speech and media-session V2 paths carry the admission tuple end to
end. Media-session V2 embeds the admission content plus its digest in every
snapshot. A V2 acknowledgement is trusted only when its runtime admission is
identical to the snapshot admission. V1 remains frozen to the exact Wizard Joe
migration tuple above and is never inferred for another character.

Admission does not imply that every character has the same movement vocabulary.
Each admitted package also carries a hash-bound choreography dictionary. See
`CHARACTER_CHOREOGRAPHY_DICTIONARY_V1.md`.
