# Serena Runtime Boot

Date: 2026-07-24

## Gate Result

Serena Quill now boots through the existing Python frame source, `WizardFrameHub`,
FastAPI server, command inbox, performance application, replay log, and
permission-world runtime. No Serena-specific server, connector, renderer, or
clock was introduced.

This is a runtime-foundation checkpoint. Serena remains outside the production
character registry and does not yet claim locomotion, speech, or performance
parity.

## Bound Candidate

- Character ID: `serena-quill-v1`
- Package SHA-256:
  `sha256:05797d7760d19e2698b4e9a1d168938ae71106b831dc531fb7a970c58086c428`
- Capability-profile SHA-256:
  `sha256:9519827d02aaa1cd2535074b3eb1d3c21cdd5f3a71c788d5126fc6e84294853d`
- Initial node: `node_neutral_front`
- Initial clip: `pose_neutral_front`
- Initial pose: `neutral_front`
- Pinned 96 by 54 first-frame hash: `fnv1a32:4348c1bb`

The hub uses the package's exact package and capability-profile digests.
Serena's runtime epoch uses the `serena_quill-*` namespace. Wizard Joe retains
the existing `wizard-*` namespace.

## Launch

The canonical launcher now accepts a hash-verified package path:

```bash
python3 tools/run_wizard_avatar_server.py \
  --host 127.0.0.1 \
  --port 8876 \
  --character-package \
  wizard_avatar/definitions/characters/serena_quill/serena_quill_character_package_v2.json
```

This command uses the same server and API routes as Wizard Joe. The
`/api/avatar/wizard/*` route prefix remains unchanged because it is an existing
connector compatibility contract, not a character identity claim. Runtime
identity and `/api/companion/health` report Serena's actual character ID and
epoch.

## Runtime Guarantees

- V2 package role assets remain SHA-256 verified at load.
- A versioned V2 capability profile is required for a real hub boot.
- The capability profile must match the package character, renderer adapter,
  runtime API, package capabilities, graph reachability, pose admission
  partition, and exact counts.
- The runtime identity binds the character ID and exact package SHA-256.
- Wizard HD review assets are exposed only when the loaded character package,
  pose library, and animation graph match the exact compatibility hashes bound
  by the HD manifest; Serena truthfully reports no Wizard HD projection.
- V2 whole-pose faces remain authored pixels. Wizard eye, mouth, and brow
  overlays are not painted onto Serena.
- Wizard staff removal is not applied to a profile that does not declare a
  staff.
- Effect permission evaluation remains independent from staff ownership.
- Lightweight frame-source test doubles retain their legacy zero-digest
  compatibility path.

## Verification

The checkpoint passed:

- 100 package, stream-hub, Serena boot, companion, permission, rendering,
  production-wiring, and runtime-identity tests;
- Python bytecode compilation for all changed runtime files;
- `git diff --check`;
- deterministic Serena first-frame comparison and pinned hash assertion;
- a copied Wizard package test proving canonical HD assets are not exposed by
  character ID alone;
- an internally inconsistent but re-hashed capability-profile rejection test;
- an independent technical review and correction pass.

The protected user server at `http://127.0.0.1:8765/side-by-side` remained
running and returned HTTP 200 throughout this work.

## Remaining Serena Gates

1. Package-profile-driven action, facing, blink, and speech control.
2. Truthful fallback for incomplete walk, run, flight, turn, and landing cycles.
3. Governed score and media-session parity through the existing connector.
4. Deterministic interruption, accessibility, and replay evidence.
5. Desktop and mobile visual review.
6. Independent animation review and product approval.
7. Exact package-hash registration and deployment proof.
