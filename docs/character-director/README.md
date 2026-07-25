# Character Director Program

This directory is the accountable implementation record for the Python Wizard
Joe Character Director objective. The program extends the existing Python
performance engine and existing Prism media connector. It does not introduce a
parallel animation runtime or connector.

## Authority

1. Python performance baseline `556701a0dfd8c9c553de7159bc2d747b43fa9bd8`.
2. Prism connector baseline `189fbabc4f59af5d53e352c6bf9c692ee7382214`.
3. `docs/audiobook-performance/LOCAL_PRISMGT_AUDIO_CONNECTOR.md`.
4. Verified corrective successors `408825a` and `5910601`.
5. Current runtime evidence and independently reviewed later work.

## Working Rule

Phase 0 freezes provenance, architecture, connector behavior, governance,
timing, capability truth, and verification gates before implementation. Every
implemented claim must link to code and behavioral evidence. Planned behavior
must remain labelled as planned.

## Local Character Observer

Run the approved HD Wizard Joe baseline beside the character package currently
under development without touching the protected service on port 8765:

```bash
python3 tools/run_character_observer.py
```

The observer opens on `http://127.0.0.1:8665/`, with isolated character
runtimes on ports 8666 and 8667. Select another candidate package with
`--current-package PATH --current-label NAME`. The observer is loopback-only
and terminates both child runtimes when it stops.

For a Wizard-to-Wizard source-art gate, run one isolated Joe runtime and place
an approved baseline sequence beside a candidate sequence:

```bash
python3 tools/run_character_observer.py \
  --review-sequence phazer_all \
  --current-label "Wizard Joe Phazer motion" \
  --current-meta "48 reconstructed alpha candidates"
```

## Documentation Map

- `PRIMARY_RESEARCH.md`: primary-source research record.
- `HD_ALPHA_SOURCE_ADOPTION.md`: HD source authority and projector boundary.
- `WIZARD_JOE_PHAZER_INTAKE_2026-07-24.md`: 48-frame Phazer archive census,
  reconstruction, gate status, and review procedure.
- `reports/README.md`: specialist reports and ownership map.
- `PHASE0_TRACKER.md`: accountable design and implementation gates.
- `PHASE0_SYNTHESIS.md`: binding cross-repository architecture.
- `IMPLEMENTATION_WORKFLOW.md`: multi-agent execution waves and dependencies.
- `CURRENT_STATE_AND_ARCHITECTURE.md`: current source and authority map.
- `ACCEPTANCE_CRITERIA_MATRIX.md`: all 41 done-when criteria with conservative
  statuses and evidence.
- `PRODUCTION_VERIFICATION.md`: fresh automated, package, cadence, security, and
  visual verification results.
- `ATOMIC_ANIMATION_TRUTH_2026-07-18.md`: exact frame/trace, contact-lock,
  authored stop/reversal/cast implementation and clean-candidate evidence.
- `reviews/RUNTIME_BOUND_CONTACT_653D400_TECHNICAL_REVIEW.md`: independent
  acceptance of the 341-frame runtime, transport, marker, and contact proof.
- `reviews/RUNTIME_BOUND_CONTACT_653D400_ANIMATION_REVIEW.md`: independent visual
  rejection with frame-specific cast, gait, turn, and speech blockers.
- `LOCOMOTION_TRANSITION_GRAPHS.md`: deterministic no-idle gait transitions and
  atomic staff-slice generation contract.
- `AUTHORED_TURN_CONTINUITY.md`: eight-direction authored view mapping, turn
  timing contract, and clean runtime evidence.
- `V6_DIRECTIONAL_ACCEPTANCE_2026-07-23.md`: accepted 222-frame directional
  turn, reversal, profile gait, contact, and stop/settle proof at commit
  `17637c53`.
- `V7_INTERRUPTION_ACCEPTANCE_2026-07-23.md`: accepted trace-triggered
  pre-commit cancellation and post-commit cast recovery proof at commit
  `8217ccc2`.
- `V8_ACCEPTANCE_CANDIDATE_2026-07-24.md`: machine-passed purposeful
  performance, authenticated governed AV, zero-drop browser replay, and the
  explicit pending product-owner gate for candidate `b34368e9`.
- `V9_ACCESSIBILITY_ACCEPTANCE_2026-07-24.md`: accepted full, reduced, and
  still motion profiles, with machine proof, product-owner approval, and an
  explicit audiovisual evidence boundary.
- `V10_PRODUCTION_ACCEPTANCE_CANDIDATE_2026-07-24.md`: frozen responsive
  framing candidate `9138f16d` and its still-pending product-owner gate.
- `CHARACTER_PARITY_ROLLOUT.md`: one-character-at-a-time package, runtime,
  governance, evidence, review, and registration gates.
- `CHARACTER_PORTABILITY_FOUNDATION_2026-07-24.md`: implemented hash-bound
  package and registry boundary, closed review findings, verification, and
  remaining Serena admission work.
- `SERENA_QUILL_MIGRATION_AUDIT_2026-07-24.md`: frozen Serena source census,
  compatibility findings, rejected shortcuts, and first-candidate admission
  sequence.
- `SERENA_RUNTIME_BOOT_2026-07-24.md`: Serena's hash-bound boot through the
  existing Python hub, server, renderer, and runtime identity.
- `SERENA_PACKAGE_CONTROLS_2026-07-24.md`: package-owned facing, actions,
  whole-pose blink and speech mappings, truthful locomotion denial, and
  focused regression evidence.
- `SERENA_LOCOMOTION_EVIDENCE_AUDIT_2026-07-24.md`: full Serena motion-art
  inventory, rejected inference shortcuts, and the deferred SQ-L0 gate.
- `SERENA_GOVERNED_PERFORMANCE_AUDIT_2026-07-24.md`: active identity and score
  admission findings plus the bounded Serena G1 plan.
- `reviews/SERENA_G1_SCORE_IDENTITY_TECHNICAL_REVIEW_2026-07-24.md`: independent
  acceptance of mutation-free identity checks and canonical score admission.
- `SERENA_G1_CROSS_REPOSITORY_RECEIPT_2026-07-24.md`: paired Python and Prism
  commit, review, verification, and protected-runtime publication receipt.
- `SERENA_G1_GOVERNED_STATIC_PERFORMANCE_2026-07-24.md`: Serena-owned
  capability derivation, deterministic governed-score compilation, production
  hub execution, reduced-motion suppression, replay, and visual evidence.
- `reviews/SERENA_G1_GOVERNED_STATIC_PERFORMANCE_TECHNICAL_REVIEW_2026-07-24.md`:
  independent review of the Serena static-performance checkpoint.
- `GAZE_SETTLE_CONTINUITY.md`: eye-lead, target-arrival re-centering, stable
  fixation, focused tests, and clean runtime evidence.
- `SPEECH_MOUTH_AUTHORITY.md`: aligned-versus-local mouth ownership,
  phrase-relative fallback rhythm, presented diagnostics, and clean runtime
  evidence.
- `RUNTIME_EPOCH_CONTRACT.md`: remote-command and per-character process
  identity fields for Wizard, Robin, Speech, Dragon, Kingfisher, and the full
  Joeville roster.
- `LIVE_E2E_2026-07-16.md`: isolated live connector, browser, and cursor-fix
  receipt with explicit evidence limits.
- `FINAL_HANDOFF.md`: ordered 33-section implementation and acceptance handoff.
- `REPRODUCIBLE_SETUP_AND_ROLLBACK.md`: setup, startup order, troubleshooting,
  rollback, and coexistence procedure.
- `BASELINE_ENVIRONMENT.md`: pinned implementation boundaries.

The legacy service on `127.0.0.1:8765` remains a separate live process. The
packaged Companion selects a dynamic loopback port and publishes its private
discovery document; it must never replace or assume ownership of port 8765.
