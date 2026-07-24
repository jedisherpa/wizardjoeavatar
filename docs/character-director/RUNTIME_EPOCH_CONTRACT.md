# Character Runtime Epoch Contract

## Purpose

Runtime observations must distinguish the remote-command process from every
active character runtime. This prevents evidence from accidentally binding a
Wizard acknowledgement to Robin, Speech, Dragon, Kingfisher, or another
Joeville character that restarted independently.

The evidence schema is `character_director_runtime_observations_v2`.

## Fields

The shared remote-command authority continues to use:

- `runtime_epoch`

Character authorities use:

- `wizard_runtime_epoch`
- `robin_runtime_epoch`
- `speech_runtime_epoch`
- `dragon_runtime_epoch`
- `kingfisher_runtime_epoch`
- `crystail_runtime_epoch`
- `falcor_runtime_epoch`
- `serena_quill_runtime_epoch`
- `aurelia_finch_runtime_epoch`
- `selene_hart_runtime_epoch`
- `thorne_vale_runtime_epoch`
- `elara_voss_runtime_epoch`
- `kai_renner_runtime_epoch`
- `mira_solen_runtime_epoch`
- `draven_holt_runtime_epoch`
- `liora_kane_runtime_epoch`
- `rohan_slate_runtime_epoch`
- `finn_calder_runtime_epoch`
- `orion_vale_runtime_epoch`

The parser accepts any future field matching `*_runtime_epoch`; adding a
character does not require weakening or replacing the evidence schema.

## Rules

1. Multiple character epochs may coexist in one acknowledgement and may have
   different values.
2. Each named authority must remain stable across the acknowledgements in one
   capture.
3. An empty, non-string, or changing epoch invalidates the capture.
4. The evidence manifest preserves the complete field-to-epoch map under
   `runtime_observations.runtime_epochs`.
5. The legacy singular `command_runtime_epoch` remains the remote-command
   epoch for backward compatibility.
6. A connector emits a character epoch only when that character runtime is
   active and supplied the acknowledgement. Evidence must never fabricate
   epochs for characters that were not involved.
7. Version 1 manifests remain readable. New captures use version 2.

## Verification

`tests/wizard/test_character_director_visual_review.py` includes an exhaustive
roster test and mixed-authority tests. The roster test proves that all fields
listed above can coexist with distinct values. The mixed-authority tests prove
that the remote-command and character epochs are reconciled independently and
that a changed value is rejected.

The current V9 Wizard proof therefore records only `runtime_epoch` and
`wizard_runtime_epoch`. Robin, Speech, Dragon, Kingfisher, and the remaining
Joeville characters will add their own real epochs as each runtime is brought
to parity; their values will not be synthesized in advance.
