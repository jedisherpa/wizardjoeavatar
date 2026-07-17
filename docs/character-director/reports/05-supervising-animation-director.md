# Supervising Animation Director Report

## Verdict

Wizard Joe is a capable procedural avatar and pose instrument, not yet a
professional character-performance runtime.

## Critical Findings

1. An 8-second live sample delivered about 10 FPS with 80 schedule overruns;
   target presentation is 24 FPS.
2. `ActingDirector` and `PhraseExecutor` are deterministic shadow systems with
   no frame authority.
3. Normal pose controls expose all 89 IDs, including 50 `diagnostic_only` poses.
4. Transition metadata exists, but the renderer hard-cuts atomic pose graphs.
5. Current release evidence predates dirty HEAD and untracked director modules.

## Professional Standard

- Staging: canonical desktop/mobile safe areas, integer nearest-neighbor cells,
  complete silhouettes, no smoothing/crop/stretch.
- Locomotion: two-tick input response, distance-driven reciprocal gait, planted
  drift no greater than one output cell, authored starts/stops/turns/reversals.
- Gestures: prepare, anticipate, stroke, hold, release, settle; one principal
  stroke per thought group and family cooldown.
- Gaze: target-driven, eyes lead head turns, stable listening fixation, no
  random gaze.
- Face: coordinated eyes/brows/mouth with speech evidence precedence and
  anatomically coherent emotion transitions.
- Timing: fixed 60 Hz simulation, stable 24 FPS presentation, deterministic
  seeks/replay, no sustained queue drops.
- Stillness: neutral body for most ordinary speech; purposeful listening and
  conclusion holds.
- Interruption: legal recovery without idle snaps; stale gestures/speech do not
  finish after a new turn.

## Confirmed Code Surfaces

- Runtime: `WizardFrameHub`, `AvatarRuntime`, and `_reduce_runtime_tick`.
- Graph selection: `_select_graph_v2_sample` and `_select_node_id`.
- Hard cut: `_reference_pose_canvas_for_sample`.
- Face/gaze/mouth: `_apply_reference_face_channels`, `_reference_eye_aim`, and
  `_reference_mouth_shape`.
- Visible media mapping: `PerformanceApplication.apply`.
- Shadow acting: `ActingDirector.evaluate` and
  `build_default_shadow_phrase_executor`.
- Carousel controls: `playDemo` and `toggleRepeat`.

## Asset Blocks

- 89 pose IDs represent only 79 distinct geometries; 50 are diagnostic-only.
- Walk lacks full reciprocal contact/up/down/passing graphs.
- Diagonal idles/turns lack full independent admission.
- All ten close-up proposals remain quarantined; none passes both visual and
  motion review.
- Emotional, pointing, listening, and thought poses need independent anchor,
  contact, and occlusion admission before phrase use.

## Gates

Pass 24 FPS framing, asset truth/admission, behavioral phrase/interruption
evidence, reciprocal ground/flight cycles, distinct listening/processing/
speaking behavior, two-tick controls, cold-run determinism, and independent
review before granting frame authority. Diagnostic poses must be unreachable
outside explicit Audit mode.

Independent verification passed 337 Python tests, 107 focused tests, 23 browser
and Companion tests, both scope validators, pose rebuild/hash checks, and a
32-scenario offline transition matrix. Those green gates do not prove
professional motion.
