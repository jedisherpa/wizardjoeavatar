# Integration Contracts

**Applicable APIs.** Semantic HTTP routes `/api/avatar/wizard/*` for movement, pathing, face/action/expression/speak/stop/reset (`docs/27-semantic-control-routes.md:00003-00018`). WebSocket `/ws/avatar/wizard?codec=adaptive`. Validation requirements for unknown actions, unsupported expressions, out-of-bounds coordinates, negative speeds, oversized paths, stale commands (`docs/27-semantic-control-routes.md:00062-00073`).

**Events.** Chat event lifecycle, semantic actions. Segment event schema Proposed — interface lock required.

**Schemas.** 
- `wizard_avatar/definitions/prism_animation_signal.schema.json:00001-00070` (content-free visual-advisory-only).
- `wizard_avatar/definitions/character_package.schema.json:00001-00017`.
- `schemas/rchat/registry-v1.schema.json:00029-00035`, `gate-v1.schema.json:00013-00018`, `evidence-frame-v1.schema.json:00017-00053`, `evidence-manifest-v1.schema.json:00014-00035`.
- ASCILINE cell and adaptive frame protocol (`docs/wizard/PROTOCOL_BASELINE.md:00003-00060`).
- Reference avatar animation graph and pose cells schemas.

**IPC.** None verified. Proposed — interface lock required.

**Media.** ASCILINE cell framebuffer with adaptive encoding. Frame desync triggers resync.

**Identity.** None verified. Proposed — interface lock required.

**Authentication.** None verified on public routes. Proposed — interface lock required.

**Versioning.** Semantic versioning for new contracts. Proposed — interface lock required.

**Errors.** Explicit denial on authority violation. Frame desync triggers resync. 401 on invalid token (proposed). Rejection on schema mismatch (proposed).

**Retry.** Rate limits and cost metering in X connector lineage; not implemented here.

**Privacy.** Sanitized CDISS summary only for Prism signals. Frame metadata only. No raw model output or private Prism content in evidence (`evidence/cartoon-animation-program/README.md:00081-00085`).

**Governance.** Prism signals grant no movement authority. Material actions require explicit human approval. No inline execution of agent plans. CDISS dispatch event schema Proposed — interface lock required. Animation frame source contract Proposed — interface lock required.

All unsupported details marked Proposed — interface lock required. No contract may bypass governance or identity boundaries.
