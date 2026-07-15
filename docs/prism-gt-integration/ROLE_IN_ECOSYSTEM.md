# Role in Ecosystem

**Current role.** The repository owns the Wizard Joe avatar/visualizer: character assets, pose compilation, procedural rendering, animation runtime, ASCILINE encoding/streaming, browser presentation, and verification artifacts. On the analyzed `codex/rust-chatbot-animation-engine` branch, `rust/wizard_avatar_engine` is the production authority and `rust/wizard_avatar_pose_tool` is the offline asset authority (`docs/cartoon-animation-program/rust-chatbot/README.md:00003-00012`).

**Target role.** Reusable character visualizer supplying the animation frame source contract to `jedisherpa/joe-newsroom` for segment cues while preserving content-free Prism animation signals (`wizard_avatar/definitions/prism_animation_signal.schema.json:00003-00006`).

**Responsibilities.** Character capability manifest, deterministic score validation, cue scheduling, animation execution, rendering, and frame evidence for Wizard Joe media performance (`docs/cartoon-animation-program/rust-chatbot/media-performance/README.md:00010-00024`). Versioned avatar animation schemas, cell/pose assets, and evidence validation. Server endpoints `/ws/avatar/wizard?codec=adaptive` and `/api/avatar/wizard/*` (`rust/wizard_avatar_engine/README.md:00013-00024`).

**Non-responsibilities.** PrismGT media identity, browser media element, durable media metadata, user media controls, preprocessing orchestration, and governed external actions remain assigned to `prism-geometry-talk` (`docs/cartoon-animation-program/rust-chatbot/media-performance/README.md:00014-00024`). Constitutional/CDISS policy engines and approval ledgers are not implemented here. No Joeville behavior is present.

**Upstream dependencies.** None verified at frozen commits. ASCILINE protocol referenced but implemented locally (`docs/wizard/ASCILINE_REPOSITORY_AUDIT.md:00015-00018`). Rust dependencies declared in `rust/wizard_avatar_engine/Cargo.toml:00043-00058`.

**Downstream consumers.** Planned: `jedisherpa/joe-newsroom` for segment event consumption via future animation frame source contract. No current runtime consumers verified.

**Integration boundaries.** Prism signals limited to visual-advisory-only metadata granting no movement authority. Media-performance Whiz/source-link governance is planned/incomplete (`docs/cartoon-animation-program/rust-chatbot/media-performance/README.md:00061-00068`). Browser is only presenter and semantic input client; does not choose poses or repair frames (`docs/cartoon-animation-program/rust-chatbot/IMPLEMENTATION_PLAN.md:00035-00036`). Orthogonal channels: conversation, mobility, pose, gesture, face, gaze, blink, mouth, speech, staff, wings, secondary motion, effects, control.
