# CrystAIl Runtime Readiness Addendum

**Verified:** 2026-07-13  
**Implementation authority:** `research-sources/wizardjoeavatar-remote/research-sources/worktrees/crystail-implementation`  
**Branch:** `codex/crystail-character`  
**Scope:** updates the earlier one-character audit; it does not claim the branch is merged into the primary `WizardJoeAvatar` checkout.

## Verdict

CrystAIl is **runtime-ready on the dedicated implementation branch**. The registry exposes `wizard-joe-v1` and `crystail-v1`; CrystAIl has a versioned package, 63-pose library, animation graph, manifest, matrix, character-scoped server routes, browser character selection, locomotion, flight, expressions, speech visemes, action/performance states and containment recovery.

Focused verification:

```text
python3 -m unittest -v \
  tests.wizard.test_crystail_character \
  tests.wizard.test_character_package

Ran 9 tests in 3.424s — OK
```

The repository's `pytest` command was not available in the selected system Python, so the same unittest-based suites were run through Python's standard unittest runner.

## Package evidence

| Field | Verified value |
|---|---|
| Character ID | `crystail-v1` |
| Display name | `CrystAIl` |
| Renderer | `asciline_square_cells` |
| Pose count | 63 |
| Package canvas | 72×96 logical cells |
| Root | (36, 91) |
| Safe inset | left 4, right 4, top 4 |
| Default pose | `neutral_front` |
| Scale multiplier | 0.88 |
| Registry count on branch | 2 |

## Measured medium-stage footprint

Measured against the actual 240×135 cached background in the CrystAIl branch, centered and grounded:

| World Z | Changed-cell bounds | Footprint |
|---:|---:|---:|
| 1.5 | X 78–161, Y 35–131 | 84×97 |
| 3.0 | X 81–158, Y 43–131 | 78×89 |
| 5.0 | X 85–154, Y 50–129 | 70×80 |
| 7.0 | X 92–147, Y 49–113 | 56×65 |
| 10.0 | X 99–140, Y 41–89 | 42×49 |

CrystAIl is materially shorter on screen than Wizard Joe at the same Z, but her wide wing-safe canvas remains important for doors, seating, aisles and group spacing.

## Joeville consequence

- The environment scale authority now has two measured characters: Wizard Joe and CrystAIl.
- The remaining build gap is eleven characters, not twelve.
- Two-character dialogue and travel tests can begin after the CrystAIl branch is merged or chosen as the runtime base.
- Five-, eight- and thirteen-character blocking remain provisional.
- Scenic-runtime limitations from the original audit still apply: the branch adds character registry/scoped routes, not a layered Joeville environment loader or scene compositor.

## Merge/runtime gate

Before labeling the primary visualizer “two-character ready,” verify the merge target contains the registry/package/assets, run the complete test suite, launch that checkout, inspect `/api/avatar/characters`, select both characters in the browser, and capture movement/speech evidence for each.

