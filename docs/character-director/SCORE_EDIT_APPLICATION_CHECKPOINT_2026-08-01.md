# Character Director Score-Edit Application Checkpoint

Date: 2026-08-01

Branch: `codex/character-director`

Base checkpoint: `a50ab149d4e18034518b1d69333ce0f4f4603648`

## Scope

This checkpoint closes the missing core application path between the immutable
`ScoreEditsV1` contract and the existing character-bound performance compiler.
It does not claim that the Companion director UI or a versioned HTTP edit route
is complete.

Implemented behavior:

- deterministic application of timing, duration, intensity, semantic mapping,
  and cue-disable edits;
- exact base-score, character-package, cue-value, and cue-lock preconditions;
- immutable parent-score and edit-set provenance on the revised portable score;
- revision increment, schema validation, context rebinding, character-bound
  recompilation, and atomic repository publication;
- fail-closed presentation and semantic-governance checks at the lowest
  character compiler boundary, including callers below the high-level
  direction parser;
- disabled cues omitted from authority evaluation and executable compiled
  tracks;
- production `PerformanceApplication` methods for applying and publishing
  edits through the admitted runtime and repository.

## Source Changes

| Path | Role |
| --- | --- |
| `wizard_avatar/score_edit_application.py` | Deterministic edit application, context rebinding, recompilation, and publication |
| `wizard_avatar/score_edits.py` | Adds the bounded boolean `disabled` operation to the closed edit vocabulary |
| `wizard_avatar/definitions/character_director_score_edits_v1.schema.json` | Defines the corresponding strict JSON Schema operation |
| `wizard_avatar/performance_compiler.py` | Enforces approval/governance at the lowest compiler boundary and omits disabled cues |
| `wizard_avatar/directed_performance.py` | Retains the compiler context and portable score needed for safe post-compile edits |
| `wizard_avatar/performance_application.py` | Exposes admitted apply and atomic publish methods |
| `tests/wizard/test_score_edit_application.py` | Covers deterministic replay, conflicts, locks, ranges, disabling, recompilation, and publication |
| `tests/wizard/test_character_bound_compiler.py` | Covers unapproved, denied, and disabled-denied compiler behavior |

## Safety Properties

1. The edit set must bind to the exact canonical base-score hash, character ID,
   and package digest.
2. Every operation must bind to the exact current target-value hash. An earlier
   operation in the same edit set changes the precondition for later operations
   against the same field.
3. Locked cues cannot be edited.
4. Timing edits cannot leave the media interval, and duration edits preserve
   ordered, non-empty phase ranges.
5. The revised score is schema-validated before compilation.
6. The context is rebound to the revised score hash and revision before the
   character compiler runs.
7. The character compiler independently requires presentation approval and
   rejects denied or unallowed semantic actions.
8. Publication uses the existing immutable-generation and atomic-current-pointer
   repository.

## Verification

Focused acceptance command:

```bash
python3 -m unittest \
  tests.wizard.test_character_bound_compiler \
  tests.wizard.test_score_edits \
  tests.wizard.test_score_edit_application \
  tests.wizard.test_directed_performance \
  tests.wizard.test_live_speech_score \
  tests.wizard.test_serena_governed_score \
  tests.wizard.test_performance_compiler \
  tests.wizard.test_performance_scheduler \
  tests.wizard.test_score_runtime \
  tests.wizard.test_contract_schemas
```

Result: 80 tests passed in 106.284 seconds.

The complete Wizard test discovery was also run from the current worktree:

```text
Ran 1070 tests in 1563.938s
FAILED (failures=112, errors=7)
```

That broad suite is not green. Most failures are existing source/evidence hash
drift in Dragon and visual-evidence fixtures, with additional head/eye/contact
and reference-overlay failures. This checkpoint does not rewrite or delete that
unrelated pose evidence.

The directed-performance cancellation fixture now advances the scheduler's
authoritative reconciliation generation. Its former direct mutation of a
render-controller state copy could be overwritten by the single-writer runtime
on the next tick, making the test intermittent without exercising a production
mutation path.

## Remaining Work

- Add a versioned, authenticated director API that exposes safe cue inspection,
  edit precondition hashes, apply/preview, and fenced publication without
  returning approved language or unrestricted renderer identifiers.
- Add Companion UI controls for those API operations.
- Replace truth-bearing defaults in `capture_performance_context()` with an
  authoritative context request and observation path.
- Carry character-neutral runtime identity through the complete release path.
- Complete current-commit audiovisual Prism evidence and long-duration drift
  measurement.
- Admit and verify non-Wizard character packages one at a time.
