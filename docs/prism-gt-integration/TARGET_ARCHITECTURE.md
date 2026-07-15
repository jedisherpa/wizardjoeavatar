# Target Architecture

**Justification.** Target internal architecture is justified solely by the synthesis and frozen report evidence at `e3c5c5d8fa39b16a2da6a48215a28dc84eee38e5`. It retains the current working Rust-first architecture on the analyzed branch while adding the narrow animation frame source contract.

**Components.** 
- `rust/wizard_avatar_engine`: runtime server, semantic command inbox, orthogonal state regions, performance director, authored motion graph, speech/gaze/blink/emotion/secondary motion, immutable cell snapshot, ASCILINE adaptive codec, Axum hub.
- `rust/wizard_avatar_pose_tool`: offline asset compiler, feelings intake, promotion tooling.
- Browser client: adaptive decoder, Canvas renderer, semantic command sender.
- rchat validator and CI workflow (`.github/workflows/rust-chatbot-ci.yml`).

**State ownership.** Browser is only presenter; semantic input client. All pose selection, animation advance, frame repair, and source image loading occur server-side in Rust (`docs/cartoon-animation-program/rust-chatbot/IMPLEMENTATION_PLAN.md:00035-00036`). Orthogonal semantic state regions: conversation, mobility, pose, gesture, face, gaze, blink, mouth, speech, staff, wings, secondary motion, effects, control (`docs/cartoon-animation-program/rust-chatbot/IMPLEMENTATION_PLAN.md:00064-00090`).

**Interfaces.** WebSocket endpoint `/ws/avatar/wizard?codec=adaptive`. Semantic HTTP routes under `/api/avatar/wizard/*`. Frame format: row-major `[char, R, G, B]` cell buffer wrapped as `[uint32 frame_index big-endian][uint8 tag][payload]` (`docs/wizard/PROTOCOL_BASELINE.md:00003-00060`).

**Data flows.** Semantic chat/TTS/browser/automation ingress → validated Rust inboxes → exact 60 Hz runtime → performance director → motion graph → speech/gaze/blink/emotion/secondary motion → immutable cell snapshot → ASCILINE adaptive codec → Axum hub → WebSocket → browser decoder → Canvas. Deterministic 60 Hz simulation required; chat ingress prohibited from selecting production pose IDs (`docs/cartoon-animation-program/rust-chatbot/README.md:00070-00082`).

**Governance boundaries.** PrismAnimationSignalV1 is content-free, visual-advisory-only metadata granting no movement, execution, or world authority (`wizard_avatar/definitions/prism_animation_signal.schema.json:00003-00006`). No CDISS/constitutional enforcement layer implemented. Media-performance Whiz/source-link governance planned/incomplete.

**Migration.** Branch-specific authority document required to reconcile Python `8765` vs Rust `8787`. rchat gate records must be generated for analyzed commit. Public endpoint labeled as target until deployment receipt exists.

**Explicit non-goals.** No Joeville implementation. No governance bypass. No shared runtime state with other repositories. No crates.io publication without pinned external checkout. No assumption that animation state changes precede live deployment verification.
