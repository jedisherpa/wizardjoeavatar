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

## Documentation Map

- `PRIMARY_RESEARCH.md`: primary-source research record.
- `reports/README.md`: specialist reports and ownership map.
- `PHASE0_TRACKER.md`: accountable design and implementation gates.
- `PHASE0_SYNTHESIS.md`: binding cross-repository architecture.
- `IMPLEMENTATION_WORKFLOW.md`: multi-agent execution waves and dependencies.
- `CURRENT_STATE_AND_ARCHITECTURE.md`: current source and authority map.
- `ACCEPTANCE_CRITERIA_MATRIX.md`: all 41 done-when criteria with conservative
  statuses and evidence.
- `PRODUCTION_VERIFICATION.md`: fresh automated, package, cadence, security, and
  visual verification results.
- `REPRODUCIBLE_SETUP_AND_ROLLBACK.md`: setup, startup order, troubleshooting,
  rollback, and coexistence procedure.
- `BASELINE_ENVIRONMENT.md`: pinned implementation boundaries.

The legacy service on `127.0.0.1:8765` remains a separate live process. The
packaged Companion selects a dynamic loopback port and publishes its private
discovery document; it must never replace or assume ownership of port 8765.
