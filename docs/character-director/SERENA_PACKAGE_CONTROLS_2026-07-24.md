# Serena Package-Driven Controls

Date: 2026-07-24

## Gate Result

Serena Quill now receives facing, action, blink, and speech-pose control from
her hash-verified CharacterPackageV2 assets inside the existing Python
controller, frame source, frame hub, performance application, and FastAPI
server.

This checkpoint does not register Serena for production and does not claim
locomotion or audiovisual performance parity.

## Bound Candidate

- Character ID: `serena-quill-v1`
- Character package SHA-256:
  `sha256:30b5540c8d13cf579776961ce1b31839513a4e184355ec7a35cd16b4a98bc4e5`
- Runtime-profile V2 SHA-256:
  `sha256:7d0cd620b907634f8743e9d08992ae1f591017dfae2a662d7e8e051ab91aa230`
- Capability profile SHA-256:
  `sha256:9519827d02aaa1cd2535074b3eb1d3c21cdd5f3a71c788d5126fc6e84294853d`

## Implemented Contract

- The shared controller receives the package's already-verified animation
  graph and runtime profile.
- Serena actions are admitted from `action_poses`. Wizard-only actions are
  rejected before Prism ownership or controller state is changed.
- Generic graph nodes may declare `grounded` or `airborne` mobility without
  inheriting Wizard-specific node names.
- Serena's `magic_cast` uses ordinary package action timing. It does not invoke
  Wizard Joe's marker-bound cast protocol unless the loaded graph actually
  contains that protocol and its required markers.
- The performance application resolves actions against Serena's graph and
  profile rather than loading Wizard Joe's graph.
- The runtime profile explicitly maps all seven runtime mouth shapes to
  package-owned speech poses. Empty speech capability remains representable by
  an empty speech-pose list and empty map.
- The explicit speech-pose map is a V2 runtime-profile contract. Existing V1
  profiles remain loadable without that field and retain an empty map, avoiding
  a silent breaking change to the published V1 shape.
- Stable idle or speaking blinks select the package-owned closed-blink pose.
  Authored action poses are not replaced by an ambient blink.
- The isolated `jump_airborne` drawing remains graph-admitted evidence but is
  not exposed as an action command. It has no complete takeoff/landing semantic,
  and presenting it as a grounded action would select the wrong drawing.
- Serena's empty walk, run, and flight cycle declarations cause commands to
  fail before movement state, control leases, or targets are mutated.
- Invalid action and speech durations fail before Prism channel ownership,
  queued speech, suspension state, or visible character state is changed.
- Local Serena speech uses her whole-pose speech contract and does not publish
  Wizard-only upper-body or staff state.
- The shared public staff-state vocabulary includes the explicit `none` state
  used by packages that do not own a staff; Wizard Joe's default remains
  `held`.
- Wizard Joe retains the existing action vocabulary, movement behavior, cast
  markers, graph, and face-layer implementation.

## Verification

The corrected checkpoint passed:

- 38 focused runtime-profile V1/V2, CharacterPackageV2, Serena migration, and
  package-control tests;
- 78 Serena-control plus Wizard controller, animation-channel,
  performance-application, and pose-selection regression tests;
- 253 broad package, registry, Serena boot, hub, production wiring,
  permission-world, companion-server, render-atomicity, controller,
  performance, scheduler, frame-source, capability, and pose-selection tests;
- deterministic Serena migration generation with `--check`;
- `git diff --check`;
- an independent technical re-review with an `ACCEPT` verdict and no remaining
  P0-P2 findings;
- protected local service check at
  `http://127.0.0.1:8765/side-by-side`.

## Remaining Serena Gates

1. Author and admit complete walk, run, turn, stop, takeoff, flight, and landing
   cycles before enabling movement.
2. Prove governed speech and media-session timing through the existing Prism
   connector, including interruption and stale-input behavior.
3. Prove package-scoped expression, gaze, semantic-score, permission-world,
   accessibility, and deterministic replay behavior.
4. Complete desktop and mobile visual review.
5. Complete independent animation and technical reviews.
6. Obtain product approval, update the exact registry hash, and produce
   deployment and rollback proof.
