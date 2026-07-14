use std::collections::BTreeSet;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};

use serde_json::{json, Value};
use wizard_avatar_engine::controller::WizardAvatarController;
use wizard_avatar_engine::frame_source::ProceduralWizardFrameSource;
use wizard_avatar_engine::newsroom::{
    build_actor_render_sample, resolve_newsroom_cue, runtime_binding_for_pose,
    ActorRenderSampleEnvelopeV1, ImplementationWorkItemStatusV1, ImplementationWorkItemV1,
    NewsCommand, NewsPerformanceCueV1, NewsProgram, NewsroomCatalogs, NewsroomError,
    NewsroomLifecycleState, NewsroomMotionPolicyV1, RuntimeBindingFidelityV1, SpeechMouthCueV1,
    SpeechTimelineV1, SpeechTimingSourceV1, StorySensitivity, UnitInterval,
    ACTOR_RENDER_SAMPLE_SCHEMA_VERSION, NEWSROOM_CUE_SCHEMA_VERSION, NEWSROOM_POSE_COUNT,
    NEWSROOM_SECTION_COUNT, NEWSROOM_TRANSITION_COUNT, SPEECH_TIMELINE_SCHEMA_VERSION,
};
use wizard_avatar_engine::pose_program::is_authored_pose_id;
use wizard_avatar_engine::server;
use wizard_avatar_engine::state::WizardState;

fn cue(command: NewsCommand) -> NewsPerformanceCueV1 {
    NewsPerformanceCueV1 {
        schema_version: NEWSROOM_CUE_SCHEMA_VERSION.to_string(),
        cue_id: format!("cue-{}", command.wire_name()),
        sequence: 1,
        program: NewsProgram::GeneralNews,
        command,
        target: None,
        count: (command == NewsCommand::Count).then_some(1),
        intensity: UnitInterval::ONE,
        sensitivity: StorySensitivity::Normal,
        start_ms: 0,
        duration_ms: 1_000,
        generation: 1,
        reduced_motion: false,
        speech_line_id: None,
        graphic_id: (command == NewsCommand::RevealGraphic).then(|| "graphic-1".to_string()),
        source_id: (command == NewsCommand::RevealSource).then(|| "source-1".to_string()),
        seed: Some(42),
    }
}

#[test]
fn embedded_catalogs_are_exact_closed_and_command_complete() {
    let catalogs = NewsroomCatalogs::embedded().expect("locked newsroom catalogs");
    assert_eq!(catalogs.poses.poses.len(), NEWSROOM_POSE_COUNT);
    assert_eq!(
        catalogs.transitions.transitions.len(),
        NEWSROOM_TRANSITION_COUNT
    );

    let sections: BTreeSet<_> = catalogs
        .poses
        .poses
        .iter()
        .map(|pose| pose.section.number)
        .collect();
    assert_eq!(sections, (1..=NEWSROOM_SECTION_COUNT as u8).collect());

    let commands: BTreeSet<_> = catalogs
        .poses
        .poses
        .iter()
        .map(|pose| pose.semantic_intent.as_str())
        .collect();
    for command in NewsCommand::ALL {
        assert!(
            commands.contains(command.wire_name()),
            "missing semantic command {}",
            command.wire_name()
        );
    }
}

#[test]
fn every_catalog_pose_has_an_explicit_authored_runtime_binding() {
    let catalogs = NewsroomCatalogs::embedded().unwrap();
    let bindings = catalogs
        .poses
        .poses
        .iter()
        .map(|pose| runtime_binding_for_pose(pose).unwrap())
        .collect::<Vec<_>>();
    assert_eq!(bindings.len(), NEWSROOM_POSE_COUNT);
    assert!(bindings
        .iter()
        .all(|binding| is_authored_pose_id(&binding.internal_pose_id)));
    assert_eq!(
        bindings
            .iter()
            .filter(|binding| { binding.fidelity == RuntimeBindingFidelityV1::ApprovedComposition })
            .count(),
        25
    );
}

#[test]
fn every_semantic_command_resolves_deterministically_to_locked_assets() {
    let catalogs = NewsroomCatalogs::embedded().unwrap();
    let policy = NewsroomMotionPolicyV1::default();
    for (index, command) in NewsCommand::ALL.into_iter().enumerate() {
        let mut input = cue(command);
        input.sequence = index as u64 + 1;
        input.generation = 9;
        let first = resolve_newsroom_cue(&input, &policy, &catalogs).unwrap();
        let second = resolve_newsroom_cue(&input, &policy, &catalogs).unwrap();
        assert_eq!(first, second, "non-deterministic command {command:?}");
        assert!(catalogs.pose(&first.semantic_pose_id).is_some());
        assert!(catalogs.transition(&first.transition_id).is_some());
        assert!(!first.internal_pose_id.is_empty());
        assert!(!first.motion_recipe_id.is_empty());
    }
}

#[test]
fn every_catalog_pose_is_reachable_through_governed_semantic_variants() {
    let catalogs = NewsroomCatalogs::embedded().unwrap();
    let policy = NewsroomMotionPolicyV1::default();
    let mut reached = BTreeSet::new();
    for command in NewsCommand::ALL {
        for seed in 0..NEWSROOM_POSE_COUNT as u64 {
            let mut input = cue(command);
            input.seed = Some(seed);
            input.sensitivity = StorySensitivity::Light;
            input.count = (command == NewsCommand::Count).then_some((seed % 3 + 1) as u8);
            let resolved = resolve_newsroom_cue(&input, &policy, &catalogs).unwrap();
            let pose = catalogs.pose(&resolved.semantic_pose_id).unwrap();
            let transition = catalogs.transition(&resolved.transition_id).unwrap();
            assert_eq!(pose.semantic_intent, command.wire_name());
            assert!(transition.legal_target_poses.contains(&pose.pose_id));
            let declared_entry_is_legal = pose.entry_transitions.iter().any(|transition_id| {
                catalogs
                    .transition(transition_id)
                    .is_some_and(|entry| entry.legal_target_poses.contains(&pose.pose_id))
            });
            assert_eq!(
                resolved
                    .policy_clamps
                    .contains(&"transition_compatibility_fallback".to_string()),
                !declared_entry_is_legal
            );
            reached.insert(resolved.semantic_pose_id);
        }
    }
    let expected = catalogs
        .poses
        .poses
        .iter()
        .map(|pose| pose.pose_id.clone())
        .collect::<BTreeSet<_>>();
    assert_eq!(reached, expected);
}

#[test]
fn cue_ingress_rejects_raw_controls_unknown_fields_and_confusables() {
    for forbidden in [
        "pose_id",
        "clip_id",
        "path",
        "effect_program",
        "raw_command",
    ] {
        let mut value = serde_json::to_value(cue(NewsCommand::Anchor)).unwrap();
        value[forbidden] = json!("front_idle_wings");
        assert!(
            serde_json::from_value::<NewsPerformanceCueV1>(value).is_err(),
            "accepted forbidden field {forbidden}"
        );
    }

    let mut value = serde_json::to_value(cue(NewsCommand::Anchor)).unwrap();
    value["cue_id"] = json!("cue-wizard-а");
    let parsed: NewsPerformanceCueV1 = serde_json::from_value(value).unwrap();
    assert!(matches!(
        parsed.validate(),
        Err(NewsroomError::InvalidIdentifier { field: "cue_id" })
    ));

    let mut value = serde_json::to_value(cue(NewsCommand::Anchor)).unwrap();
    value["cue_id"] = json!("x".repeat(97));
    assert!(serde_json::from_value::<NewsPerformanceCueV1>(value)
        .unwrap()
        .validate()
        .is_err());
}

#[test]
fn cue_validation_enforces_command_specific_fields_and_bounds() {
    let mut input = cue(NewsCommand::Count);
    for invalid in [None, Some(0), Some(4)] {
        input.count = invalid;
        assert_eq!(input.validate(), Err(NewsroomError::InvalidCount));
    }
    input.count = Some(2);
    input.validate().unwrap();

    let mut input = cue(NewsCommand::Anchor);
    input.count = Some(1);
    assert_eq!(input.validate(), Err(NewsroomError::InvalidCount));

    let mut input = cue(NewsCommand::RevealGraphic);
    input.graphic_id = None;
    assert_eq!(input.validate(), Err(NewsroomError::InvalidGraphic));

    let mut input = cue(NewsCommand::RevealSource);
    input.source_id = None;
    assert_eq!(input.validate(), Err(NewsroomError::InvalidSource));

    let mut input = cue(NewsCommand::Anchor);
    input.sequence = 0;
    assert_eq!(
        input.validate(),
        Err(NewsroomError::InvalidSequenceOrGeneration)
    );
    input.sequence = 1;
    input.duration_ms = 30_001;
    assert_eq!(input.validate(), Err(NewsroomError::InvalidDuration));
}

#[test]
fn implementation_work_item_schema_is_closed_and_bounded() {
    let item = ImplementationWorkItemV1 {
        work_item_id: "WJ-020".to_string(),
        phase: 2,
        lane: "rust".to_string(),
        title: "Implement strict Rust schema boundary".to_string(),
        dependencies: vec!["WJ-001".to_string()],
        files: vec!["rust/wizard_avatar_engine/src/newsroom.rs".to_string()],
        acceptance: "Focused tests pass with retained evidence.".to_string(),
        human_approval_required: false,
        status: ImplementationWorkItemStatusV1::PlannedNotStarted,
    };
    item.validate().unwrap();

    let mut unknown = serde_json::to_value(&item).unwrap();
    unknown["result_sha"] = json!("not-allowed-in-v1");
    assert!(serde_json::from_value::<ImplementationWorkItemV1>(unknown).is_err());

    let mut invalid = item;
    invalid.work_item_id = "WJ-20".to_string();
    assert!(invalid.validate().is_err());
    invalid.work_item_id = "WJ-020".to_string();
    invalid.phase = 10;
    assert!(invalid.validate().is_err());
}

#[test]
fn sensitivity_and_reduced_motion_policy_clamp_performance() {
    let catalogs = NewsroomCatalogs::embedded().unwrap();
    let policy = NewsroomMotionPolicyV1::default();

    let mut serious = cue(NewsCommand::RevealGraphic);
    serious.sensitivity = StorySensitivity::Serious;
    serious.reduced_motion = true;
    serious.seed = None;
    let resolved = resolve_newsroom_cue(&serious, &policy, &catalogs).unwrap();
    assert_eq!(resolved.semantic_pose_id, "trace_timeline");
    assert!(resolved.applied_intensity.permille() <= 250);
    assert!(resolved.transition_ms <= policy.reduced_motion.maximum_transition_ms);
    assert_eq!(resolved.motion_recipe_id, "reduced_motion_handoff");
    assert!(resolved
        .policy_clamps
        .contains(&"reduced_motion".to_string()));

    for command in [
        NewsCommand::React,
        NewsCommand::RevealGraphic,
        NewsCommand::RevealSource,
        NewsCommand::Welcome,
    ] {
        for seed in 0..NEWSROOM_POSE_COUNT as u64 {
            let mut input = cue(command);
            input.sensitivity = StorySensitivity::Serious;
            input.seed = Some(seed);
            let resolved = resolve_newsroom_cue(&input, &policy, &catalogs).unwrap();
            let pose = catalogs.pose(&resolved.semantic_pose_id).unwrap();
            assert!(!pose.story_sensitivity_limit.starts_with("light/"));
        }
    }

    let mut correction = cue(NewsCommand::Break);
    correction.sensitivity = StorySensitivity::Correction;
    correction.seed = None;
    let resolved = resolve_newsroom_cue(&correction, &policy, &catalogs).unwrap();
    assert_eq!(resolved.semantic_pose_id, "breaking_composed");
    assert!(!resolved.semantic_pose_id.contains("magic"));
    assert!(resolved.applied_intensity.permille() <= 150);
}

#[test]
fn corrupt_catalog_references_and_duplicate_identities_are_rejected() {
    let catalogs = NewsroomCatalogs::embedded().unwrap();

    let mut poses = catalogs.poses.clone();
    poses.poses[1].pose_id = poses.poses[0].pose_id.clone();
    assert!(NewsroomCatalogs::new(poses, catalogs.transitions.clone()).is_err());

    let mut transitions = catalogs.transitions.clone();
    transitions.transitions[0].legal_target_poses[0] = "missing_pose".to_string();
    assert!(NewsroomCatalogs::new(catalogs.poses.clone(), transitions).is_err());

    let mut poses = catalogs.poses.clone();
    poses.poses.pop();
    assert!(NewsroomCatalogs::new(poses, catalogs.transitions.clone()).is_err());
}

#[test]
fn actor_samples_are_cell_aligned_hashed_and_tamper_evident() {
    let state = WizardState {
        pose_id: Some("front_idle_wings".to_string()),
        pose_generation: 7,
        simulation_tick: 120,
        ..WizardState::default()
    };
    let (metadata, buffers) =
        build_actor_render_sample(&state, "anchor_neutral_front", 7, "deadbeef").unwrap();

    assert_eq!(metadata.schema_version, ACTOR_RENDER_SAMPLE_SCHEMA_VERSION);
    assert_eq!(metadata.simulation_tick, 120);
    assert_eq!(
        buffers.rgb.len(),
        usize::from(metadata.width) * usize::from(metadata.height) * 3
    );
    assert_eq!(
        buffers.coverage_mask.len(),
        usize::from(metadata.width) * usize::from(metadata.height)
    );
    assert!(buffers.coverage_mask.iter().all(|value| *value <= 1));
    assert!(!metadata.contact_points.is_empty());
    assert_eq!(
        metadata.diagnostics.get("coordinate_space"),
        Some(&json!("actor_local_cell_grid"))
    );
    metadata.validate_with_buffers(&buffers).unwrap();
    let envelope = ActorRenderSampleEnvelopeV1::new(metadata.clone(), &buffers);
    assert_eq!(envelope.decode_and_validate().unwrap(), buffers);

    let mut corrupt = buffers.clone();
    corrupt.rgb[0] ^= 0xff;
    assert!(metadata.validate_with_buffers(&corrupt).is_err());

    let mut corrupt = buffers.clone();
    corrupt.coverage_mask[0] = 2;
    assert!(metadata.validate_with_buffers(&corrupt).is_err());

    let mut corrupt_metadata = metadata.clone();
    corrupt_metadata.actor_layer_hash = "0".repeat(64);
    assert!(corrupt_metadata.validate_with_buffers(&buffers).is_err());

    let mut corrupt_metadata = metadata.clone();
    corrupt_metadata.staff_bounds = Some(wizard_avatar_engine::newsroom::ActorRectV1 {
        x: i32::from(corrupt_metadata.width),
        y: 0,
        width: 2,
        height: 2,
    });
    assert!(corrupt_metadata.validate_with_buffers(&buffers).is_err());

    let mut controller = WizardAvatarController::default();
    for tick in 0..180 {
        let (metadata, buffers) = build_actor_render_sample(
            controller.current_state(),
            "anchor_neutral_front",
            1,
            "deadbeef",
        )
        .unwrap_or_else(|error| panic!("idle actor sample failed at tick {tick}: {error}"));
        metadata
            .validate_with_buffers(&buffers)
            .unwrap_or_else(|error| panic!("idle actor sample invalid at tick {tick}: {error}"));
        controller.step_tick();
    }
}

#[test]
fn every_approved_semantic_variant_emits_valid_actor_samples_across_motion_phases() {
    let catalogs = NewsroomCatalogs::embedded().unwrap();
    for pose in &catalogs.poses.poses {
        let binding = runtime_binding_for_pose(pose).unwrap();
        for simulation_tick in [0, 15, 30, 45, 60] {
            let state = WizardState {
                pose_id: Some(binding.internal_pose_id.clone()),
                pose_generation: 1,
                simulation_tick,
                ..WizardState::default()
            };
            let (metadata, buffers) =
                build_actor_render_sample(&state, &pose.pose_id, 1, "deadbeef").unwrap_or_else(
                    |error| {
                        panic!(
                            "actor sample failed for {} at tick {simulation_tick}: {error}",
                            pose.pose_id
                        )
                    },
                );
            metadata
                .validate_with_buffers(&buffers)
                .unwrap_or_else(|error| {
                    panic!(
                        "actor sample invalid for {} at tick {simulation_tick}: {error}",
                        pose.pose_id
                    )
                });
        }
    }
}

#[test]
fn actor_samples_remain_valid_through_live_semantic_transitions() {
    let mut controller = WizardAvatarController::default();
    for sequence in 1..=(NewsCommand::ALL.len() as u64 * 2) {
        let command = NewsCommand::ALL[((sequence - 1) as usize) % NewsCommand::ALL.len()];
        let mut input = cue(command);
        input.cue_id = format!("transition-{sequence}-{}", command.wire_name());
        input.sequence = sequence;
        input.count = (command == NewsCommand::Count).then_some((sequence % 3 + 1) as u8);
        input.duration_ms = 400;
        input.reduced_motion = sequence.is_multiple_of(7);
        input.seed = Some(sequence);
        let receipt = controller.apply_newsroom_cue(input).unwrap();

        for phase_tick in 0..30 {
            controller.step_tick();
            if phase_tick % 5 != 0 {
                continue;
            }
            let (metadata, buffers) = build_actor_render_sample(
                controller.current_state(),
                &receipt.performance.semantic_pose_id,
                receipt.generation,
                "deadbeef",
            )
            .unwrap_or_else(|error| {
                panic!(
                    "live actor sample failed for {} at phase {phase_tick}: {error}",
                    receipt.performance.semantic_pose_id
                )
            });
            metadata
                .validate_with_buffers(&buffers)
                .unwrap_or_else(|error| {
                    panic!(
                        "live actor sample invalid for {} at phase {phase_tick}: {error}",
                        receipt.performance.semantic_pose_id
                    )
                });
        }
    }
}

#[test]
fn speech_timeline_is_ordered_non_overlapping_and_closes_between_cues() {
    let timeline = SpeechTimelineV1 {
        schema_version: SPEECH_TIMELINE_SCHEMA_VERSION.to_string(),
        utterance_id: "utterance-1".to_string(),
        generation: 2,
        start_ms: 500,
        duration_ms: 600,
        timing_source: SpeechTimingSourceV1::ProviderViseme,
        cues: vec![
            SpeechMouthCueV1 {
                start_ms: 0,
                end_ms: 100,
                mouth: "open".to_string(),
                weight: Some(80),
            },
            SpeechMouthCueV1 {
                start_ms: 200,
                end_ms: 400,
                mouth: "round".to_string(),
                weight: None,
            },
        ],
        caption_cues: Vec::new(),
    };
    timeline.validate().unwrap();
    assert_eq!(timeline.mouth_at_ms(50), "open");
    assert_eq!(timeline.mouth_at_ms(150), "closed");
    assert_eq!(timeline.mouth_at_ms(250), "round");
    assert_eq!(timeline.mouth_at_ms(600), "closed");

    let mut overlap = timeline.clone();
    overlap.cues[1].start_ms = 99;
    assert!(overlap.validate().is_err());

    let mut unknown: Value = serde_json::to_value(timeline).unwrap();
    unknown["clip_id"] = json!("do-not-accept");
    assert!(serde_json::from_value::<SpeechTimelineV1>(unknown).is_err());
}

#[test]
fn controller_enforces_idempotency_ordering_and_interruption_attribution() {
    let mut controller = WizardAvatarController::default();
    let mut first = cue(NewsCommand::Anchor);
    first.duration_ms = 1_000;
    let accepted = controller.apply_newsroom_cue(first.clone()).unwrap();
    assert!(!accepted.duplicate);
    assert_eq!(
        accepted.performance.lifecycle,
        NewsroomLifecycleState::Applied
    );

    let duplicate = controller.apply_newsroom_cue(first.clone()).unwrap();
    assert!(duplicate.duplicate);
    assert_eq!(controller.newsroom_receipts().len(), 1);

    let mut conflict = first.clone();
    conflict.intensity = UnitInterval::ZERO;
    assert_eq!(
        controller.apply_newsroom_cue(conflict),
        Err(NewsroomError::SequenceConflict)
    );

    let mut replacement = cue(NewsCommand::Explain);
    replacement.sequence = 2;
    replacement.generation = 1;
    let replacement = controller.apply_newsroom_cue(replacement).unwrap();
    assert_eq!(
        replacement.interrupted_cue_id.as_deref(),
        Some("cue-anchor")
    );
    assert_eq!(
        controller.newsroom_receipts()[0].performance.lifecycle,
        NewsroomLifecycleState::Interrupted
    );

    assert!(matches!(
        controller.apply_newsroom_cue(first),
        Err(NewsroomError::StaleCue { .. })
    ));

    let mut next_generation = cue(NewsCommand::Correct);
    next_generation.generation = 2;
    next_generation.sequence = 1;
    controller.apply_newsroom_cue(next_generation).unwrap();
    assert_eq!(controller.latest_newsroom_receipt().unwrap().generation, 2);
}

#[test]
fn controller_restores_timed_cues_and_bounds_receipt_history() {
    let mut controller = WizardAvatarController::default();
    let mut timed = cue(NewsCommand::Think);
    timed.duration_ms = 200;
    controller.apply_newsroom_cue(timed).unwrap();
    controller.advance(1.0);
    assert_eq!(
        controller
            .latest_newsroom_receipt()
            .unwrap()
            .performance
            .lifecycle,
        NewsroomLifecycleState::Completed
    );

    for sequence in 2..=70 {
        let mut input = cue(NewsCommand::Anchor);
        input.sequence = sequence;
        input.duration_ms = 0;
        controller.apply_newsroom_cue(input).unwrap();
    }
    assert_eq!(controller.newsroom_receipts().len(), 64);
    assert_eq!(controller.newsroom_receipts().front().unwrap().sequence, 7);
    assert_eq!(controller.newsroom_receipts().back().unwrap().sequence, 70);
}

#[test]
fn queued_newsroom_replacement_becomes_applied_only_at_its_safe_handoff() {
    let mut controller = WizardAvatarController::default();
    let mut first = cue(NewsCommand::Welcome);
    first.seed = Some(2);
    first.duration_ms = 500;
    assert_eq!(
        controller
            .apply_newsroom_cue(first)
            .unwrap()
            .performance
            .lifecycle,
        NewsroomLifecycleState::Applied
    );

    let mut replacement = cue(NewsCommand::Explain);
    replacement.sequence = 2;
    replacement.duration_ms = 200;
    assert_eq!(
        controller
            .apply_newsroom_cue(replacement)
            .unwrap()
            .performance
            .lifecycle,
        NewsroomLifecycleState::Scheduled
    );

    let mut saw_applied = false;
    for _ in 0..120 {
        controller.step_tick();
        let lifecycle = controller
            .latest_newsroom_receipt()
            .unwrap()
            .performance
            .lifecycle;
        saw_applied |= lifecycle == NewsroomLifecycleState::Applied;
        if lifecycle == NewsroomLifecycleState::Completed {
            break;
        }
    }
    assert!(saw_applied);
    assert_eq!(
        controller
            .latest_newsroom_receipt()
            .unwrap()
            .performance
            .lifecycle,
        NewsroomLifecycleState::Completed
    );
}

#[tokio::test]
async fn versioned_http_adapter_accepts_semantics_and_rejects_raw_pose_ingress() {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind newsroom test server");
    let addr = listener.local_addr().unwrap();
    let app = server::app(ProceduralWizardFrameSource::default());
    let server_task = tokio::spawn(async move {
        axum::serve(listener, app)
            .await
            .expect("serve newsroom router");
    });

    let body = serde_json::to_string(&cue(NewsCommand::Welcome)).unwrap();
    let accepted = raw_http_post(addr, "/api/avatar/wizard/v2/newsroom/cue", body.clone()).await;
    assert!(accepted.starts_with("HTTP/1.1 200 OK\r\n"));
    assert!(accepted.contains("\"semantic_pose_id\":\"enter_from_left\""));
    let actor_sample = raw_http_get(addr, "/api/avatar/wizard/v2/newsroom/actor-sample").await;
    assert!(actor_sample.starts_with("HTTP/1.1 200 OK\r\n"));
    assert!(actor_sample.contains("\"semantic_pose\":\"enter_from_left\""));
    assert!(actor_sample.contains("\"coverage_mask_base64\":"));
    let state = raw_http_get(addr, "/api/avatar/wizard/state").await;
    assert!(state.starts_with("HTTP/1.1 200 OK\r\n"));
    assert!(state.contains("\"build\":{\"git_sha\":"));

    let mut raw = serde_json::to_value(cue(NewsCommand::Anchor)).unwrap();
    raw["sequence"] = json!(2);
    raw["pose_id"] = json!("front_idle_wings");
    let rejected = raw_http_post(
        addr,
        "/api/avatar/wizard/v2/newsroom/cue",
        serde_json::to_string(&raw).unwrap(),
    )
    .await;
    assert!(rejected.starts_with("HTTP/1.1 422 Unprocessable Entity\r\n"));
    assert!(rejected.contains("unknown field `pose_id`"));

    let oversized = raw_http_post(
        addr,
        "/api/avatar/wizard/v2/newsroom/cue",
        format!("{}{}", " ".repeat(17 * 1_024), body),
    )
    .await;
    assert!(oversized.starts_with("HTTP/1.1 413 Payload Too Large\r\n"));
    server_task.abort();
}

async fn raw_http_post(addr: SocketAddr, path: &'static str, body: String) -> String {
    tokio::task::spawn_blocking(move || {
        let mut stream = TcpStream::connect(addr).expect("connect newsroom test router");
        stream
            .write_all(
                format!(
                    "POST {path} HTTP/1.1\r\nHost: {addr}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
                    body.len()
                )
                .as_bytes(),
            )
            .expect("write newsroom HTTP request");
        let mut response = String::new();
        stream
            .read_to_string(&mut response)
            .expect("read newsroom HTTP response");
        response
    })
    .await
    .expect("blocking newsroom HTTP client")
}

async fn raw_http_get(addr: SocketAddr, path: &'static str) -> String {
    tokio::task::spawn_blocking(move || {
        let mut stream = TcpStream::connect(addr).expect("connect newsroom test router");
        stream
            .write_all(
                format!("GET {path} HTTP/1.1\r\nHost: {addr}\r\nConnection: close\r\n\r\n")
                    .as_bytes(),
            )
            .expect("write newsroom HTTP request");
        let mut response = String::new();
        stream
            .read_to_string(&mut response)
            .expect("read newsroom HTTP response");
        response
    })
    .await
    .expect("blocking newsroom HTTP client")
}
