# Character Director Current-State Audit

Date: 2026-07-25

## Audited Candidate

- Python repository: `jedisherpa/wizardjoeavatar`
- Python branch: `codex/character-director`
- Python commit: `f73a013614f75d389964a42637a45f20497e3140`
- Prism repository: `jedisherpa/prism-geometry-talk`
- Prism branch: `codex/character-director-prism`
- Prism commit: `dd503d0`
- Python architecture: the existing ASCILINE Python runtime, frame hub,
  projector, scheduler, controller, and server
- Prism architecture: the existing browser media observer and existing Rust
  loopback relay

This is an implementation audit, not a production-completion declaration.
Review-only character libraries are not production character packages, and
machine-passing evidence is not product approval.

The current branch, tree, and pushed commit are readable. A full `git fsck`
also found pre-existing broken local refs and reflog entries for abandoned
`codex/*` branches whose objects are no longer present. Those refs do not affect
the audited current branch, but repository-wide object integrity is not clean
and must be repaired before claiming complete local-history reproducibility.

## Verification Run

| Surface | Result |
| --- | --- |
| Python governed speech, Serena controls, parity compiler, observer, and alternate review libraries | 107 tests passed |
| Prism governed speech and media connector JavaScript | 53 tests passed |
| Prism CLI unit suite | 314 tests passed |
| Prism governed-reply integration suite | 28 tests passed |
| Prism production frontend build | Passed |

The Prism unit suite initially found the documented embedded-frontend
precondition (`miniapp.html` absent). Running the production frontend build and
then rerunning the suite produced 314/314 passing tests.

## Required Deliverables

| # | Deliverable | Status | Current evidence and remaining work |
| ---: | --- | --- | --- |
| 1 | Baseline and Provenance Report | Complete | `BASELINE_ENVIRONMENT.md`, `reports/03-commit-and-provenance.md`, and the repository history document both pinned commits and later integration points. |
| 2 | Connector Documentation Audit | Complete | `reports/04-prism-connector-specialist.md` maps the canonical connector document to code and records discrepancies. |
| 3 | Current-State Architecture Report | Partial | `CURRENT_STATE_AND_ARCHITECTURE.md`, `PHASE0_SYNTHESIS.md`, and `IMPLEMENTATION_WORKFLOW.md` map the real systems. The audited snapshot predates governed-receipt identity, Serena, the HD/Phazer intake, and the JoeVille merge, so counts and candidate commits are stale. |
| 4 | Independent Specialist Reports | Complete | Eleven reports exist under `docs/character-director/reports/`. Later acceptance reviews add implementation-specific findings. |
| 5 | Final Architecture | Substantially implemented | The approved single-runtime/single-connector design is implemented. Final diagrams must be refreshed to include package-driven characters, exact governed-speech receipts, and review-only library admission. |
| 6 | Character Capability Manifest | Partial | Runtime derivation, strict validation, a V1 schema, and focused tests exist. Wizard Joe's checked-in package still exposes six broad capability strings instead of linking a frozen current detailed manifest, the server does not expose the detailed inventory, and the other JoeVille libraries remain source-motion candidates rather than admitted capability manifests. |
| 7 | Performance Context Schema | Complete | `performance_context.py` and `performance_context_v1.schema.json` provide strict, versioned, hash-bound context. |
| 8 | Performance-Score Schema | Complete | `performance_score.py`, compiler/loader/repository code, and V1 schemas provide validation, versioning, examples, immutable publication, and replay. |
| 9 | Buffer-Space Performance Library | Implemented, visual acceptance partial | Truthful stage mappings and content-free advisories exist. Real wait, clarification, approval, timeout, error, and reconnect performances still need one current connected review package. |
| 10 | Context-to-Performance Compiler | Complete for the current controlled language | `direction_compiler.py`, `performance_compiler.py`, and character-bound compilation reject unsupported behavior or record explicit fallback. |
| 11 | Text, Voice, and Animation Synchronization | Partial | Text, mouth, whole-pose speech, pause/resume/seek, interruption, persona, voice, package, media, and reconciliation identity can share the authoritative media timeline. Normal live turns may still use the restrained `scoreless_v1` body fallback, and a current real Prism-to-Python audible recording is still required. |
| 12 | Completed PrismGT Connector | Implemented, current installed-pair proof missing | The existing connector now validates exact content-free Python registration receipts and reports authority loss. No parallel connector was introduced. |
| 13 | Director and Debug Tool | Complete for the required diagnostic surface | Diagnostics, score edits, permission-world simulation, scenario runners, analyzers, visual-review tooling, replay, and observer controls exist. Package admission remains a release workflow rather than an editor operation. |
| 14 | Automated Test Suite | Partial | Focused current suites pass. The latest retained broad Python result predates `f73a0136` and contained five inherited failures; a current full discovery, companion suite, clean-clone run, paired installed-runtime test, cross-system matrix, and long-duration soak remain release gates. |
| 15 | Visual Review Package | Strong but fragmented | V1-V10, connected E2E, soak, browser, and independent review evidence exists. Some candidates are superseded or rejected; the current paired commits do not yet have one consolidated audiovisual acceptance bundle. |
| 16 | Reproducible Setup Documentation | Partial | Setup, rollback, clean-clone, and supervisor documents exist. Independent-user packaged installation and rollback remain unproven for the current pair. |
| 17 | Production-Readiness Report | Partial | `PRODUCTION_VERIFICATION.md`, `FINAL_HANDOFF.md`, and the acceptance matrix are explicit that promotion is not complete. They require this audit's current commit and character-library updates. |

## Current Runtime Truth

The latest integrated behavior now guarantees:

- non-Wizard governed speech must carry persona and voice identity;
- the voice identity must match the timing artifact;
- Serena is bound to her exact character and package;
- the browser, Rust relay, and Python runtime validate an exact registration
  receipt before synchronized playback;
- the receipt binds approval, alignment, turn, speech, character, package,
  media, reconciliation, revocation, and mouth-presentation policy;
- a stale speech-stop callback cannot cancel a replacement utterance;
- Serena speech uses package-authored whole-pose visemes instead of a competing
  body projection;
- the 12 JoeVille source archives compile deterministically into transparent
  1254-by-1254 review pixel graphs;
- 462 supplied motions are represented without invented padding;
- 114 motions remain genuinely unauthored;
- all JoeVille parity libraries remain `review_projection: true` and
  `runtime_admitted: false`.

## Acceptance-Evidence Truth

There is no consolidated audiovisual acceptance bundle for the exact current
pair `f73a0136` and `dd503d0`. Earlier accepted receipts remain valid for their
own frozen candidates, but they do not automatically transfer across later
runtime, projector, package, identity, governed-speech, or connector changes.

Current disposition:

- V1 listening/eyes/blink was accepted at `8fb8c4b`;
- V3 canonical cast phases were accepted at `dba348b`;
- V4 thought-group gestures have machine and technical acceptance at
  `1fe705e`, without a separate independent animation receipt;
- V5 front walk was accepted at `7fc5b2a`;
- V7 interruption was accepted at `8217ccc2`;
- V9 reduced/still motion has explicit product-owner approval at `c46d4ec`;
- V6 directional locomotion still needs normal-speed, quarter-speed, and
  frame-by-frame human review;
- V8 purposefulness and audiovisual performance still need product-owner
  approval;
- V10 responsive framing still needs product-owner approval;
- eight-hour and 24-hour current-harness soak runs remain open;
- independent-user packaged install and rollback remain open.

Rejected candidates, including atomic `b7b6101`, V3 `a72f791`, V6
`85c767b`/`a2efa27`/`ee4d636`, and V8 `19c808d9`, must not be promoted. The
untracked alternate V3, V8, V10, and directional-pose directories remain
diagnostic until each receives an explicit disposition.

The older `ACCEPTANCE_CRITERIA_MATRIX.md` is stale and internally miscounts its
rows. Its table contains 28 implemented-and-verified rows, five
implemented-but-not-visually-verified rows, and eight partial rows; its summary
reports 26, seven, and eight. It must be regenerated from the current pair
rather than edited as though it were current evidence.

## Highest-Impact Runtime Gap: Remediated

The normal governed-speech path now uses an explicit two-pass score handshake:

1. Python captures a scoreless preliminary context (`C0`) for the accepted
   speech cursor.
2. The character-bound compiler creates a deterministic, content-free score
   against the active capability manifest; Python reacquires the session lock,
   revalidates the accepted snapshot, and only then atomically publishes it.
3. Prism republishes the exact score ID, revision, and digest in a newer loading
   media epoch.
4. Python captures the final score-bound context (`C1`).
5. Approval, registration, and playback proceed only when `C1`, the accepted
   cursor, and the content-free registration receipt carry the same score
   identity.

Compilation, publication, media drift, epoch drift, context mismatch, and
receipt mismatch fail closed. Runtime resolution loads the exact immutable score
generation named by the accepted ID, revision, digest, package, and media
binding rather than consulting the mutable current-score pointer. Publication
also creates a bounded, one-use server-side grant. Registration must advance
to exactly the next accepted sequence and media epoch while retaining the exact
connector session, media, turn, utterance, approval artifact, character, and
package from `C0`. Grants expire after 30 seconds, are invalidated by a
superseding speech cursor or revocation, and are consumed by successful
registration. Historical, skipped-epoch, and cross-turn score replay therefore
fail closed. Generated `compiled:speech:*` artifacts have a 2,048-generation
global retention cap that protects outstanding grants and the currently
accepted speech score while excluding authored scores. Scoreless governed
speech is disabled by default.
During a staggered local upgrade it is available only when Python explicitly
sets `WIZARD_ALLOW_SCORELESS_GOVERNED_SPEECH=1` and the Prism controller
explicitly sets `allowScorelessCompatibility: true`; a `404` or `501` response
without both opt-ins fails closed. The LaunchAgent installer now provisions a
persistent app-owned `WIZARD_SCORE_ROOT`.

## Highest-Impact Roster Architecture Gap

Persona-to-character identity is still implemented as a Serena-specific
constant in both Python and Prism. The production registry binds character
packages but does not declare persona identity. That is sufficient for the
Serena gate and unsafe as a roster architecture.

The scalable successor must:

1. declare persona identity in a strict, hash-bound character admission
   contract;
2. derive allowed persona/character/package tuples from that contract;
3. publish the active tuple through the existing performance binding;
4. validate it at approval, timing, registration, receipt, and playback
   boundaries;
5. fail closed for review-only or unregistered characters;
6. preserve Wizard Joe V1 compatibility without weakening non-Wizard checks.

No additional character should enter the production registry before this
identity contract exists. This gate is independent from automatic score
attachment: identity controls who may perform, while score attachment controls
what purposeful performance they execute.

## Character Parity State

| Character | Supplied motions | Missing motions | Runtime state |
| --- | ---: | ---: | --- |
| Serena Quill | 48 | 0 | Package-driven candidate; not production registered |
| Mira Solen | 48 | 0 | Review-only source-motion library |
| Aurelia Finch | 42 | 6 | Review-only source-motion library |
| Selene Hart | 36 | 12 | Review-only source-motion library |
| Thorne Vale | 36 | 12 | Review-only source-motion library |
| Elara Voss | 36 | 12 | Review-only source-motion library |
| Kai Renner | 36 | 12 | Review-only source-motion library |
| Draven Holt | 36 | 12 | Review-only source-motion library |
| Liora Kane | 36 | 12 | Review-only source-motion library |
| Rohan Slate | 36 | 12 | Review-only source-motion library |
| Finn Calder | 36 | 12 | Review-only source-motion library |
| Orion Vale | 36 | 12 | Review-only source-motion library |

The observer at `http://127.0.0.1:8665/` remains the review surface. It does
not imply package or registry admission.

## Preserved Untracked Evidence

The merge did not delete, move, or stage the pre-existing untracked V3, V8,
V10, and directional-pose evidence. Those artifacts remain in the Python
worktree for provenance-aware review. They must be classified as accepted,
superseded, rejected, or diagnostic before any evidence commit.

## Next Gates

The next runtime implementation gate is automatic live character-bound score
compilation, publication, and snapshot attachment. The next roster-admission
gate is the generic persona/character/package identity contract. The next
acceptance gate after both is a current audible
Prism-to-Python governed-speech scenario that proves:

- exact identity receipt correlation;
- progressive approved text;
- whole-pose speech animation;
- pause/resume/seek;
- interruption by a new prompt;
- stale-callback rejection;
- return to listening;
- no unapproved output;
- synchronized desktop and mobile presentation.
