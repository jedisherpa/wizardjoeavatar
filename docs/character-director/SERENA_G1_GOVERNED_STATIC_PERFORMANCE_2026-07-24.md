# Serena G1 Governed Static Performance

Date: 2026-07-24

## Decision Boundary

This checkpoint proves that a verified Serena Quill V2 package can derive its
own capability manifest, compile one governed body-performance cue, execute
that cue through the existing Python score runtime and frame hub, release it
on pause, and replay it deterministically.

This is a static-performance gate. It does not claim Serena locomotion,
flight, permission-world visuals, independent expression or mouth overlays,
live Prism audiovisual synchronization, or production registry admission.

## Canonical Identities

- Character: `serena-quill-v1`
- Package:
  `sha256:30b5540c8d13cf579776961ce1b31839513a4e184355ec7a35cd16b4a98bc4e5`
- Capability manifest:
  `sha256:de5fa711d8cec6cd4050bee9793cc14958f030ccd086eba24e529c3af3a1466e`
- Package schema version: `2` (compiled identity `2.0.0`)
- Runtime vocabulary:
  `sha256:11d2977fe0dddbee799ee7c882495aeab96f9e984d2f289ad146a57a6ac19208`
- Runtime mapping:
  `sha256:c61e6da543c11be1541c70a681c5ec98220479753e458910ba51c9275879ca18`
- Portable score:
  `sha256:fd6e925b0755a799d69c3561f5326e8c6f6ea88436cc6f2b389107a651a80f94`
- Compiled score: `compiled:091f31a8b0382e516f289fe7`
- Compiled artifact:
  `sha256:4e75bc5e6d77ebbdb6e742fe800d7ae4467b0d77df0e1fc51ecd0f6090a054c5`
- Mapping policy:
  `sha256:060043dff4ba5a1cf2b3bf7c3c4347a35de4ee5c7654e58cd634c2ba61b1c9c2`
- Cue resolution:
  `sha256:52e77746c765ef252a3ceea15e25f884d699d3b6dc9eee399a92dc46ced25bb0`

## Implemented Path

1. `derive_character_capability_manifest()` accepts the legacy Wizard Joe V1
   package unchanged or a verified V2 package.
2. Serena's capability provenance comes from her package assets and runtime
   profile. It does not inherit Wizard Joe's expression, mouth, staff, wings,
   semantic-map, or permission-prop inventory.
3. The V2 package schema identity is carried separately from capability
   manifest schema V1, so compiled scores truthfully publish package version
   `2.0.0`; Wizard Joe's legacy package remains `1.0.0`.
4. The admitted `mentoring_invitation` action resolves to:
   - capability `clip:pose_mentoring_invitation`;
   - clip `pose_mentoring_invitation`;
   - node `node_mentoring_invitation`;
   - pose `mentoring_invitation`;
   - body ownership only.
5. `compile_character_bound_performance()` compiles semantic intent `explain`
   only after governance and package identity agree.
6. `CompiledScoreLoader` validates the compiler output and
   `CompiledScoreRepository` publishes it.
7. The existing `WizardFrameHub` and `ProceduralWizardFrameSource` preload and
   apply the Serena cue through `ScoreRuntime`; no parallel runtime was added.
8. A paused media snapshot releases the whole-pose action to Serena's
   `neutral_front` state.

## Accessibility

Serena's whole-pose mentoring action cannot be reduced by dropping an
independent motion channel because the source art has body ownership only.
Under `reduced` motion, the compiler therefore emits no cue and records both:

- `motion_profile_projection`
- `motion_profile_suppressed`

This is an explicit deterministic suppression, not an unrelated animation
fallback. `still` behavior remains governed by the existing compiler contract.

## Determinism And Regression Evidence

Focused gate:

```bash
python3 -m unittest \
  tests.wizard.test_character_capability_portability \
  tests.wizard.test_serena_governed_score
```

Result: 10 tests passed.

Broad performance regression:

```bash
python3 -m unittest \
  tests.wizard.test_contract_schemas \
  tests.wizard.test_character_package \
  tests.wizard.test_character_runtime_profile \
  tests.wizard.test_character_registry \
  tests.wizard.test_character_graph_portability \
  tests.wizard.test_character_capabilities \
  tests.wizard.test_character_capability_portability \
  tests.wizard.test_serena_quill_migration \
  tests.wizard.test_serena_runtime_boot \
  tests.wizard.test_serena_package_controls \
  tests.wizard.test_serena_governed_score \
  tests.wizard.test_performance_context \
  tests.wizard.test_performance_compiler \
  tests.wizard.test_character_bound_compiler \
  tests.wizard.test_performance_score \
  tests.wizard.test_score_runtime \
  tests.wizard.test_performance_scheduler \
  tests.wizard.test_performance_application \
  tests.wizard.test_governed_performance \
  tests.wizard.test_character_director_v9_fixture \
  tests.wizard.test_character_director_v9_acceptance
```

Result: 180 tests passed.

The focused replay test constructs two cold Serena sources, accepts the same
canonical score snapshot, and compares the rendered cell arrays exactly. The
arrays are identical. The legacy Wizard Joe capability-manifest golden digest
remains
`sha256:0cdf29861befacf05f0fe3bb01ffcd8103d5b20bc812818a0626f75c6ee9de74`.

## Visual Evidence

Evidence directory:
`evidence/character-director/serena-g1-governed-performance-2026-07-24`

- `observer-desktop-serena-mentoring.png`
  (`sha256:eaa3249fdcd38d624fc7a0f778a9988e4f0e653a11db766c2047262afe260ca7`)
- `observer-serena-mentoring.png`
  (`sha256:e6e7d9ca4a6a55cfca236d8f5aef4f30071128d96fd33eb44d1eb94c27b617f7`)

The desktop capture shows approved HD Wizard Joe beside Serena's
`mentoring_invitation` pose in the isolated observer. The narrow capture proves
the same observer stacks without clipping the character stages. Screenshots
prove presentation only; the automated runtime tests prove score identity,
application, release, accessibility, and deterministic replay.

## Runtime Isolation

- Protected service `127.0.0.1:8765`: preserved and not restarted.
- Observer `127.0.0.1:8665`: healthy.
- HD Wizard child `127.0.0.1:8666`: healthy.
- Serena child `127.0.0.1:8667`: healthy and returned to `neutral_front`.

The observer is a review surface around the same Python server entry point. It
does not replace the protected runtime or introduce a second performance
engine.

## Remaining Serena Gates

- Governed speech generation, alignment, and revocation evidence.
- Purposeful locomotion admission from approved motion evidence.
- Live Prism text, voice, and animation synchronization.
- Permission-world capability and visual review.
- Long-duration, failure-injection, and production registry acceptance.
