# Alpha Release Correction Ledger

Release: `wizard_joe_base_250_alpha/v001`

The 250 opaque Drive masters were preserved unchanged. Two approved content substitutions were introduced in the alpha release to resolve known production blockers.

| ID | Asset | Reason | Original source SHA-256 | Corrected alpha source SHA-256 | Final normalized alpha SHA-256 |
|---|---|---|---|---|---|
| 124 | `staff_raise_vertical` | Original figure was substantially underscaled. Rebuilt at production scale with the complete vertical staff, hat, wings, and shoes inside the safe frame. | `a16cc241ec4489df61548388571f7382b3b23547f5509385b807ad7ccbc0d75a` | `ff20d089734285a058c19d24391cd77a20eda63bf5b2e4773bc14f7970286624` | `c0e542674b4899cec728a1dcf4be3f63e432918ee483343714cd9089d6ff749d` |
| 205 | `magic_cast_hold` | Original pose did not read as a distinct sustained hold after release. Rebuilt as an effect-free, staff-forward hold between release and recoil. | `0a2cd4862077e4dea85d313003f4c6d216fea448ff0cea02fb01b5b721517f6c` | `7b16a99484a29ff6b75c8c2bb31c3bd22f221bcb781821d40207dbceac1f3feb` | `f0fc9c74be3f7b87e65e363c5142f172b258a0c21bd809b8c708d763485cc18c` |

No other asset received a semantic redraw. Alpha extraction, edge cleanup, safe-margin normalization, sRGB tagging, and derivative generation were deterministic release-processing steps.
