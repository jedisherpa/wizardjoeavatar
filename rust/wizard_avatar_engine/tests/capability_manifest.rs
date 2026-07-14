use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use wizard_avatar_engine::capability_manifest::{
    build_wizard_capability_document, build_wizard_capability_manifest, ApplicabilityV1,
    CapabilityDocumentV1, CapabilityKind, CapabilityStatus, FallbackTopologyV1, NarrativeUseV1,
    PropRequirementV1, RuntimePolicyV1, RuntimeProfileV1, RuntimeSurfaceV1, RuntimeTransportV1,
    CAPABILITY_API_VERSION, CAPABILITY_MANIFEST_SCHEMA_VERSION, RUNTIME_POLICY_VERSION,
    RUNTIME_PROFILE_VERSION, RUNTIME_TRANSPORT_VERSION,
};
use wizard_avatar_engine::chat_event::{
    AttentionTarget, ChatTurnState, Emotion, GestureKind, Viseme, CHAT_EVENT_SCHEMA_VERSION,
};
use wizard_avatar_engine::chat_performance::{
    RenderedMouthPose, CHAT_PERFORMANCE_SCHEMA_VERSION, DURATION_FALLBACK_VERSION,
};
use wizard_avatar_engine::command::COMMAND_SCHEMA_VERSION;
use wizard_avatar_engine::controller::{
    ControllerCommandKind, WizardAvatarController, WizardCommand, PROCEDURAL_CONTROLLER_COMMANDS,
};
use wizard_avatar_engine::frame_source::ProceduralWizardFrameSource;
use wizard_avatar_engine::motion_catalog::{embedded_motion_graph_json, shadow_motion_catalog};
use wizard_avatar_engine::motion_graph::{CapabilityTier, MOTION_GRAPH_SCHEMA_VERSION};
use wizard_avatar_engine::pose::PoseLibrary;
use wizard_avatar_engine::pose_clip::POSE_CLIPS;
use wizard_avatar_engine::server;
use wizard_avatar_engine::state::{
    Action, Direction, EffectState, Expression, Locomotion, MouthShape, StaffState,
    UpperBodyAction, WizardState, WorldPoint,
};

const EXPECTED_MANIFEST_SHA256: &str =
    "4ef14b34a6ce9b8b81c89e59a25b9f5fd142aff19757069d692b39422650b482";

fn ids_for(
    manifest: &wizard_avatar_engine::capability_manifest::CapabilityManifestV1,
    kind: CapabilityKind,
) -> BTreeSet<String> {
    manifest
        .capabilities
        .iter()
        .filter(|entry| entry.kind == kind)
        .map(|entry| entry.id.clone())
        .collect()
}

fn wire_name<T: serde::Serialize>(value: T) -> String {
    serde_json::to_value(value)
        .expect("wire serialization")
        .as_str()
        .expect("string wire enum")
        .to_string()
}

fn prefixed_ids<T: Copy + serde::Serialize>(prefix: &str, values: &[T]) -> BTreeSet<String> {
    values
        .iter()
        .map(|value| format!("{prefix}.{}", wire_name(*value)))
        .collect()
}

#[test]
fn manifest_is_an_exact_census_of_runtime_and_contract_registries() {
    let manifest = build_wizard_capability_manifest().expect("manifest should build");
    let library = PoseLibrary::reference().expect("pose library should load");
    let graph = &shadow_motion_catalog()
        .expect("motion graph should load")
        .graph;

    assert_eq!(manifest.schema_version, CAPABILITY_MANIFEST_SCHEMA_VERSION);
    assert_eq!(manifest.capabilities.len(), 209);
    assert_eq!(manifest.character_id, WizardState::default().character_id);
    assert_eq!(manifest.pose_geometry_count, library.pose_ids().count());
    assert_eq!(manifest.pose_alias_count, library.alias_count());
    assert_eq!(manifest.imported_pose_archive_sha256.len(), 64);
    assert_eq!(manifest.runtime_geometry_authority_sha256.len(), 64);
    assert_eq!(manifest.motion_graph_sha256.len(), 64);
    assert_eq!(manifest.safe_idle.idle_turn_state, ChatTurnState::Idle);
    assert_eq!(manifest.safe_idle.stop_behavior_id, "behavior.stop");
    assert_eq!(
        manifest.safe_idle.neutral_expression_id,
        "expression.neutral"
    );
    assert_eq!(manifest.safe_idle.rest_mouth_pose_id, "mouth.closed");
    assert_eq!(
        manifest.imported_pose_archive_sha256,
        format!(
            "{:x}",
            Sha256::digest(include_bytes!("../assets/wizard_pose_library.v4.json.gz"))
        )
    );
    assert_eq!(
        manifest.motion_graph_sha256,
        format!(
            "{:x}",
            Sha256::digest(embedded_motion_graph_json().as_bytes())
        )
    );

    assert_eq!(
        ids_for(&manifest, CapabilityKind::Pose),
        library
            .pose_ids()
            .map(str::to_string)
            .collect::<BTreeSet<_>>()
    );
    assert_eq!(
        ids_for(&manifest, CapabilityKind::PoseAlias),
        ["fly_front_hover_ready".to_string()].into_iter().collect()
    );
    assert_eq!(
        ids_for(&manifest, CapabilityKind::LegacyClip),
        POSE_CLIPS
            .iter()
            .map(|clip| clip.id.to_string())
            .collect::<BTreeSet<_>>()
    );
    assert_eq!(
        ids_for(&manifest, CapabilityKind::MotionClip),
        graph
            .clips
            .iter()
            .map(|clip| clip.clip_id.clone())
            .collect::<BTreeSet<_>>()
    );
    assert_eq!(
        ids_for(&manifest, CapabilityKind::Expression),
        Expression::ALL
            .into_iter()
            .map(|expression| format!("expression.{}", expression.as_str()))
            .collect()
    );
    assert_eq!(
        ids_for(&manifest, CapabilityKind::MouthPose),
        prefixed_ids("mouth", &RenderedMouthPose::ALL)
    );
    assert_eq!(
        ids_for(&manifest, CapabilityKind::ChatState),
        prefixed_ids("chat_state", &ChatTurnState::ALL)
    );
    let non_neutral = Emotion::ALL
        .into_iter()
        .filter(|emotion| *emotion != Emotion::Neutral)
        .collect::<Vec<_>>();
    assert_eq!(manifest.feelings, non_neutral);
    assert_eq!(manifest.feelings.len(), 10);
    assert_eq!(
        ids_for(&manifest, CapabilityKind::Emotion),
        prefixed_ids("emotion", &manifest.feelings)
    );
    assert_eq!(
        ids_for(&manifest, CapabilityKind::GestureIntent),
        prefixed_ids("gesture", &GestureKind::ALL)
    );
    assert_eq!(
        ids_for(&manifest, CapabilityKind::GazeIntent),
        prefixed_ids("gaze", &AttentionTarget::ALL)
    );
    assert_eq!(
        ids_for(&manifest, CapabilityKind::VisemeIntent),
        prefixed_ids("viseme", &Viseme::ALL)
    );
    assert_eq!(
        ids_for(&manifest, CapabilityKind::ProceduralBehavior),
        [
            "behavior.action",
            "behavior.circle",
            "behavior.face",
            "behavior.figure_eight",
            "behavior.move",
            "behavior.move_relative",
            "behavior.path",
            "behavior.periodic_blink",
            "behavior.reset",
            "behavior.return_to_center",
            "behavior.speaking_duration",
            "behavior.stop",
            "behavior.walk_backward",
            "behavior.walk_forward",
            "behavior.walk_left",
            "behavior.walk_right",
        ]
        .into_iter()
        .map(str::to_string)
        .collect()
    );
}

#[test]
fn every_pose_joins_exact_graph_tier_facing_surface_and_showcase_fallback_truth() {
    let manifest = build_wizard_capability_manifest().expect("manifest should build");
    let graph = &shadow_motion_catalog().expect("motion catalog").graph;
    let entries = manifest
        .capabilities
        .iter()
        .filter(|entry| entry.kind == CapabilityKind::Pose)
        .map(|entry| (entry.id.as_str(), entry))
        .collect::<BTreeMap<_, _>>();

    assert_eq!(entries.len(), graph.pose_coverage.len());
    let mut statuses = BTreeSet::new();
    let mut showcase_count = 0usize;
    for row in &graph.pose_coverage {
        let entry = entries.get(row.pose_id.as_str()).expect("joined pose row");
        let coverage = entry.pose_coverage.as_ref().expect("typed pose coverage");
        assert_eq!(
            coverage.capability_tier, row.capability_tier,
            "{}",
            row.pose_id
        );
        assert_eq!(
            coverage.use_kinds.iter().copied().collect::<BTreeSet<_>>(),
            row.use_kinds.iter().copied().collect::<BTreeSet<_>>(),
            "{}",
            row.pose_id
        );
        assert_eq!(
            coverage
                .approved_facings
                .iter()
                .copied()
                .collect::<BTreeSet<_>>(),
            row.approved_facings
                .iter()
                .copied()
                .collect::<BTreeSet<_>>(),
            "{}",
            row.pose_id
        );
        assert!(entry
            .runtime_surfaces
            .contains(&RuntimeSurfaceV1::DirectPoseCommand));
        assert!(entry
            .runtime_surfaces
            .contains(&RuntimeSurfaceV1::ShadowMotionGraph));
        statuses.insert(entry.status);

        match (&row.showcase_approval, &coverage.showcase_approval) {
            (Some(expected), Some(actual)) => {
                showcase_count += 1;
                assert_eq!(entry.status, CapabilityStatus::ShowcaseOnly);
                assert_eq!(actual.owner, expected.owner);
                assert_eq!(actual.rationale, expected.rationale);
                assert_eq!(actual.fallback_pose_id, expected.fallback_pose_id);
                assert_eq!(
                    entry.fallback,
                    FallbackTopologyV1::Fallbacks(vec![expected.fallback_pose_id.clone()])
                );
            }
            (None, None) => assert_ne!(row.capability_tier, CapabilityTier::ShowcaseOnly),
            _ => panic!("{} showcase approval drift", row.pose_id),
        }
    }
    assert_eq!(showcase_count, 10);
    assert_eq!(
        statuses,
        [
            CapabilityStatus::ActiveLegacy,
            CapabilityStatus::ShadowValidated,
            CapabilityStatus::ShowcaseOnly,
        ]
        .into_iter()
        .collect()
    );
}

#[test]
fn state_facing_fallbacks_are_the_exact_graph_10_by_8_topology() {
    let manifest = build_wizard_capability_manifest().expect("manifest should build");
    let graph = &shadow_motion_catalog().expect("motion catalog").graph;
    let actual = manifest
        .state_facing_fallbacks
        .iter()
        .map(|fallback| {
            (
                fallback.turn_state,
                fallback.requested_facing,
                fallback.fallback_pose_id.as_str(),
            )
        })
        .collect::<BTreeSet<_>>();
    let expected = graph
        .state_facing_fallbacks
        .iter()
        .map(|fallback| {
            (
                fallback.turn_state,
                fallback.requested_facing,
                fallback.fallback_pose_id.as_str(),
            )
        })
        .collect::<BTreeSet<_>>();

    assert_eq!(manifest.state_facing_fallbacks.len(), 10 * 8);
    assert_eq!(actual, expected);
    assert_eq!(actual.len(), 10 * 8);
    for state in ChatTurnState::ALL {
        for facing in Direction::ALL {
            assert!(actual.iter().any(|row| row.0 == state && row.1 == facing));
        }
    }
}

#[test]
fn versions_and_unsupported_flags_publish_only_current_runtime_truth() {
    let manifest = build_wizard_capability_manifest().expect("manifest should build");
    assert_eq!(CAPABILITY_MANIFEST_SCHEMA_VERSION, 2);
    assert_eq!(CAPABILITY_API_VERSION, 2);
    assert_eq!(manifest.schema_version, 2);
    assert_eq!(
        manifest.versions.capability_api_version,
        CAPABILITY_API_VERSION
    );
    assert_eq!(manifest.versions.runtime_profile, RuntimeProfileV1::Legacy);
    assert_eq!(
        manifest.versions.runtime_profile_version,
        RUNTIME_PROFILE_VERSION
    );
    assert_eq!(
        manifest.versions.runtime_policy,
        RuntimePolicyV1::LegacyController
    );
    assert_eq!(
        manifest.versions.runtime_policy_version,
        RUNTIME_POLICY_VERSION
    );
    assert_eq!(
        manifest.versions.runtime_transport,
        RuntimeTransportV1::AxumHttpWebSocketAdaptiveCodec
    );
    assert_eq!(
        manifest.versions.runtime_transport_version,
        RUNTIME_TRANSPORT_VERSION
    );
    assert_eq!(
        manifest.versions.command_schema_version,
        COMMAND_SCHEMA_VERSION
    );
    assert_eq!(
        manifest.versions.chat_event_schema_version,
        CHAT_EVENT_SCHEMA_VERSION
    );
    assert_eq!(
        manifest.versions.chat_performance_schema_version,
        CHAT_PERFORMANCE_SCHEMA_VERSION
    );
    assert_eq!(
        manifest.versions.duration_fallback_policy_version,
        DURATION_FALLBACK_VERSION
    );
    assert_eq!(
        manifest.motion_graph_schema_version,
        MOTION_GRAPH_SCHEMA_VERSION
    );
    assert!(!manifest.support.deterministic_media_scores);
    assert!(!manifest.support.authored_dance);
    assert!(!manifest.support.rendered_gaze);
    assert!(!manifest.support.timed_visemes);
}

#[test]
fn runtime_alias_is_a_stable_resolvable_capability_with_exact_topology() {
    let manifest = build_wizard_capability_manifest().expect("manifest should build");
    let alias = manifest
        .capabilities
        .iter()
        .find(|entry| entry.kind == CapabilityKind::PoseAlias)
        .expect("pose alias capability");
    assert_eq!(alias.id, "fly_front_hover_ready");
    assert_eq!(alias.status, CapabilityStatus::ActiveLegacy);
    assert_eq!(
        alias
            .pose_alias
            .as_ref()
            .expect("alias target")
            .target_pose_id,
        "fly_front_hover_neutral"
    );
    assert_eq!(
        alias.fallback,
        FallbackTopologyV1::Fallbacks(vec!["fly_front_hover_neutral".to_string()])
    );
    let library = PoseLibrary::reference().expect("pose library");
    assert_eq!(
        library.for_id(&alias.id).expect("alias resolves").id,
        library
            .for_id("fly_front_hover_neutral")
            .expect("target resolves")
            .id
    );
    let target = manifest
        .capabilities
        .iter()
        .find(|entry| entry.id == "fly_front_hover_neutral")
        .expect("alias target capability");
    assert_eq!(alias.emotional_uses, target.emotional_uses);
    assert_eq!(alias.energy, target.energy);
    assert_eq!(alias.directions, target.directions);
    assert_eq!(alias.duration, target.duration);
    assert_eq!(alias.loop_behavior, target.loop_behavior);
    assert_eq!(alias.interruptibility, target.interruptibility);
    assert_eq!(alias.valid_entry_states, target.valid_entry_states);
    assert_eq!(alias.valid_exit_states, target.valid_exit_states);
    assert_eq!(alias.face_policy, target.face_policy);
    assert_eq!(alias.compatible_face_states, target.compatible_face_states);
    assert_eq!(
        alias.compatible_locomotion_states,
        target.compatible_locomotion_states
    );
    assert_eq!(
        alias.compatible_motion_profiles,
        target.compatible_motion_profiles
    );
    assert_eq!(alias.controller_commands, target.controller_commands);
    assert_eq!(alias.prop_requirements, target.prop_requirements);
    assert_eq!(
        alias.prop_requirements,
        vec![PropRequirementV1::StaffAllSamples]
    );
    assert_eq!(alias.runtime_cost, target.runtime_cost);
    assert_eq!(alias.transition_limitations, target.transition_limitations);
    assert_eq!(alias.narrative_uses, target.narrative_uses);
    assert_eq!(alias.inappropriate_uses, target.inappropriate_uses);
}

#[test]
fn controller_command_and_procedural_census_is_derived_and_behaviorally_resolvable() {
    let manifest = build_wizard_capability_manifest().expect("manifest should build");
    assert_eq!(
        manifest.controller_command_surface,
        ControllerCommandKind::ALL
            .into_iter()
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect::<Vec<_>>()
    );
    for command in ControllerCommandKind::ALL {
        let mut controller = WizardAvatarController::default();
        let result = controller.apply_command(WizardCommand::new(
            wire_name(command),
            serde_json::json!({}),
        ));
        assert!(
            !result.message.starts_with("unsupported command"),
            "{command:?} must resolve through the controller registry"
        );
    }
    let alias = WizardAvatarController::default()
        .apply_command(WizardCommand::new("figure-eight", serde_json::json!({})));
    assert!(!alias.message.starts_with("unsupported command"));

    let procedural = manifest
        .capabilities
        .iter()
        .filter(|entry| entry.kind == CapabilityKind::ProceduralBehavior)
        .collect::<Vec<_>>();
    assert_eq!(procedural.len(), PROCEDURAL_CONTROLLER_COMMANDS.len() + 3);
    for command in PROCEDURAL_CONTROLLER_COMMANDS {
        assert_eq!(
            procedural
                .iter()
                .filter(|entry| {
                    matches!(
                        &entry.controller_commands,
                        ApplicabilityV1::Applicable(commands) if commands == &[command]
                    )
                })
                .count(),
            1,
            "{command:?} must have one procedural capability"
        );
    }
    assert!(
        ids_for(&manifest, CapabilityKind::ProceduralBehavior).contains("behavior.move_relative")
    );
    assert!(ids_for(&manifest, CapabilityKind::ProceduralBehavior).contains("behavior.face"));

    let entry_command_union = manifest
        .capabilities
        .iter()
        .flat_map(|entry| match &entry.controller_commands {
            ApplicabilityV1::Applicable(commands) => commands.as_slice(),
            ApplicabilityV1::NotApplicable => &[],
        })
        .copied()
        .collect::<BTreeSet<_>>();
    assert_eq!(
        entry_command_union,
        ControllerCommandKind::ALL.into_iter().collect()
    );
    let action_entries = manifest
        .capabilities
        .iter()
        .filter(|entry| {
            matches!(
                &entry.controller_commands,
                ApplicabilityV1::Applicable(commands)
                    if commands.contains(&ControllerCommandKind::Action)
            )
        })
        .map(|entry| entry.id.as_str())
        .collect::<BTreeSet<_>>();
    assert_eq!(action_entries, ["behavior.action"].into_iter().collect());
    for action in Action::ALL {
        let result = WizardAvatarController::default().apply_command(WizardCommand::new(
            "action",
            serde_json::json!({"action": action.as_str(), "duration_ms": 1}),
        ));
        assert!(
            result.ok,
            "{} action must resolve: {}",
            action.as_str(),
            result.message
        );
    }

    let mut moving = WizardAvatarController::default();
    assert!(
        moving
            .apply_command(WizardCommand::new(
                "move_relative",
                serde_json::json!({"dx": 1.0, "dz": 0.0}),
            ))
            .ok
    );
    moving.advance(1.0);
    assert!(moving.current_state().world_position.x > 0.0);

    let mut facing = WizardAvatarController::default();
    assert!(
        facing
            .apply_command(WizardCommand::new(
                "face",
                serde_json::json!({"direction": "west"}),
            ))
            .ok
    );
    facing.advance(0.5);
    assert_eq!(facing.current_state().facing, Direction::West);
}

#[test]
fn applicability_is_explicit_and_face_locomotion_metadata_is_typed() {
    let manifest = build_wizard_capability_manifest().expect("manifest should build");
    for entry in &manifest.capabilities {
        assert_explicit(&entry.emotional_uses, "emotional_uses", &entry.id);
        assert_explicit(&entry.valid_entry_states, "valid_entry_states", &entry.id);
        assert_explicit(&entry.valid_exit_states, "valid_exit_states", &entry.id);
        assert_explicit(
            &entry.compatible_face_states,
            "compatible_face_states",
            &entry.id,
        );
        assert_explicit(
            &entry.compatible_locomotion_states,
            "compatible_locomotion_states",
            &entry.id,
        );
        assert_explicit(
            &entry.transition_limitations,
            "transition_limitations",
            &entry.id,
        );
        assert_explicit(&entry.narrative_uses, "narrative_uses", &entry.id);
        assert_explicit(&entry.inappropriate_uses, "inappropriate_uses", &entry.id);
        if let FallbackTopologyV1::Fallbacks(ids) = &entry.fallback {
            assert!(!ids.is_empty(), "{} fallback topology", entry.id);
        }
    }

    let pose = manifest
        .capabilities
        .iter()
        .find(|entry| entry.kind == CapabilityKind::Pose)
        .expect("pose");
    assert_eq!(
        pose.compatible_face_states,
        ApplicabilityV1::Applicable(Expression::ALL.to_vec())
    );
    assert_eq!(
        pose.compatible_locomotion_states,
        ApplicabilityV1::Applicable(Locomotion::ALL.to_vec())
    );
}

#[test]
fn legacy_clip_props_include_exact_staff_and_effect_coverage() {
    let manifest = build_wizard_capability_manifest().expect("manifest should build");
    let library = PoseLibrary::reference().expect("pose library");
    for clip in POSE_CLIPS {
        let entry = manifest
            .capabilities
            .iter()
            .find(|entry| entry.kind == CapabilityKind::LegacyClip && entry.id == clip.id)
            .expect("legacy clip capability");
        let staff_count = clip
            .steps
            .iter()
            .filter(|step| {
                library
                    .for_id(step.pose_id)
                    .expect("step pose")
                    .motion
                    .staff_present
            })
            .count();
        let effect_count = clip
            .steps
            .iter()
            .filter(|step| {
                library
                    .for_id(step.pose_id)
                    .expect("step pose")
                    .motion
                    .effect_present
            })
            .count();
        let mut expected = BTreeSet::new();
        add_expected_prop(
            &mut expected,
            PropRequirementV1::StaffAllSamples,
            PropRequirementV1::StaffSomeSamples,
            staff_count,
            clip.steps.len(),
        );
        add_expected_prop(
            &mut expected,
            PropRequirementV1::EffectAllSamples,
            PropRequirementV1::EffectSomeSamples,
            effect_count,
            clip.steps.len(),
        );
        assert_eq!(
            entry
                .prop_requirements
                .iter()
                .copied()
                .collect::<BTreeSet<_>>(),
            expected,
            "{} prop coverage",
            clip.id
        );
    }
    let staff_combo = manifest
        .capabilities
        .iter()
        .find(|entry| entry.id == "staff_combo")
        .expect("staff combo");
    assert!(staff_combo
        .prop_requirements
        .contains(&PropRequirementV1::EffectSomeSamples));
}

#[test]
fn closed_world_validation_rejects_invented_missing_and_reclassified_runtime_ids() {
    let valid = build_wizard_capability_manifest().expect("manifest should build");

    let mut missing = valid.clone();
    missing.capabilities.remove(0);
    assert!(missing.validate().is_err());

    let mut invented = valid.clone();
    let mut fake = invented.capabilities[0].clone();
    fake.id = "invented.capability".to_string();
    invented.capabilities.push(fake);
    invented
        .capabilities
        .sort_by(|left, right| left.id.cmp(&right.id));
    assert!(invented.validate().is_err());

    let mut missing_command = valid.clone();
    missing_command.controller_command_surface.pop();
    assert!(missing_command.validate().is_err());

    let mut unadvertised_action = valid.clone();
    unadvertised_action
        .capabilities
        .iter_mut()
        .find(|entry| entry.id == "behavior.action")
        .expect("action capability")
        .controller_commands = ApplicabilityV1::NotApplicable;
    assert!(unadvertised_action.validate().is_err());

    let mut changed_alias = valid;
    changed_alias
        .capabilities
        .iter_mut()
        .find(|entry| entry.kind == CapabilityKind::PoseAlias)
        .expect("alias")
        .id = "fly_front_hover_invented".to_string();
    changed_alias
        .capabilities
        .sort_by(|left, right| left.id.cmp(&right.id));
    assert!(changed_alias.validate().is_err());
}

#[test]
fn safe_idle_profile_is_exactly_runtime_resolvable() {
    let manifest = build_wizard_capability_manifest().expect("manifest should build");
    let profile = &manifest.safe_idle;

    assert_eq!(profile.idle_turn_state, ChatTurnState::Idle);
    assert_eq!(profile.stop_behavior_id, "behavior.stop");
    assert_eq!(profile.neutral_expression_id, "expression.neutral");
    assert_eq!(profile.rest_mouth_pose_id, "mouth.closed");
    assert!(profile.preserve_mode);
    assert!(profile.preserve_root_position);
    assert!(profile.preserve_facing);
    assert!(profile.clear_gesture);
    assert!(profile.clear_gaze_override);
    assert!(profile.clear_viseme_override);
    assert!(profile.clear_blink_override);
    assert!(profile.clear_prop_effects);
    assert!(profile.settle_secondary_motion);

    let idle_fallbacks = manifest
        .state_facing_fallbacks
        .iter()
        .filter(|fallback| fallback.turn_state == profile.idle_turn_state)
        .collect::<Vec<_>>();
    assert_eq!(idle_fallbacks.len(), Direction::ALL.len());
    assert_eq!(
        idle_fallbacks
            .iter()
            .map(|fallback| fallback.requested_facing)
            .collect::<BTreeSet<_>>(),
        Direction::ALL.into_iter().collect()
    );
    for fallback in idle_fallbacks {
        let target = manifest
            .capabilities
            .iter()
            .find(|entry| entry.id == fallback.fallback_pose_id)
            .expect("safe idle fallback target");
        assert_eq!(target.kind, CapabilityKind::Pose);
        assert_eq!(target.status, CapabilityStatus::ActiveLegacy);
    }
}

#[test]
fn stop_behavior_executes_the_published_safe_idle_policy() {
    let mut controller = WizardAvatarController::default();
    controller.state_mut().world_position = WorldPoint { x: 2.0, z: 7.0 };
    controller.state_mut().facing = Direction::East;
    controller.apply_command(WizardCommand::new(
        "action",
        serde_json::json!({"action": "magic_cast", "duration_ms": 10_000}),
    ));
    controller.apply_command(WizardCommand::new(
        "speak",
        serde_json::json!({"text": "active", "duration_ms": 10_000}),
    ));
    controller.apply_command(WizardCommand::new(
        "expression",
        serde_json::json!({"expression": "happy"}),
    ));
    controller.apply_command(WizardCommand::new(
        "mouth",
        serde_json::json!({"mouth": "open_wide"}),
    ));
    let root = controller.current_state().world_position;
    let facing = controller.current_state().facing;

    let result = controller.apply_command(WizardCommand::new("stop", serde_json::json!({})));
    assert!(result.ok);
    assert_eq!(result.state.world_position, root);
    assert_eq!(result.state.facing, facing);
    assert_eq!(result.state.locomotion, Locomotion::Idle);
    assert_eq!(result.state.action, Action::Idle);
    assert_eq!(result.state.upper_body_action, UpperBodyAction::None);
    assert_eq!(result.state.expression, Expression::Neutral);
    assert_eq!(result.state.mouth, MouthShape::Closed);
    assert_eq!(result.state.staff_state, StaffState::Held);
    assert_eq!(result.state.effect_state, EffectState::None);
    assert!(result.state.speech_id.is_none());
    assert!(result.state.pose_clip_id.is_none());
    assert!(result.state.target_point.is_none());

    controller.advance(1.0);
    assert_eq!(controller.current_state().world_position, root);
    assert_eq!(controller.current_state().facing, facing);
    assert_eq!(
        wizard_avatar_engine::animation::reference_pose_id_for_state(controller.current_state()),
        "profile_right"
    );
}

#[test]
fn stop_behavior_supersedes_an_in_flight_raw_pose_transition() {
    let mut controller = WizardAvatarController::default();
    let started = controller.apply_command(WizardCommand::new(
        "pose",
        serde_json::json!({
            "pose_id": "front_magic_staff_thrust",
            "transition_ms": 1_000
        }),
    ));
    assert!(started.ok);
    assert_eq!(
        started.state.pose_id.as_deref(),
        Some("front_magic_staff_thrust")
    );

    let stopped = controller.apply_command(WizardCommand::new("stop", serde_json::json!({})));
    assert!(stopped.ok);
    assert_ne!(
        stopped.state.pose_id.as_deref(),
        Some("front_magic_staff_thrust")
    );
    for _ in 0..60 {
        controller.step_tick();
        assert_ne!(
            controller.current_state().pose_id.as_deref(),
            Some("front_magic_staff_thrust")
        );
    }
    assert_eq!(
        wizard_avatar_engine::animation::reference_pose_id_for_state(controller.current_state()),
        "front_idle"
    );
}

#[test]
fn safe_idle_profile_rejects_wrong_references_policy_and_facing_coverage() {
    let valid = build_wizard_capability_manifest().expect("manifest should build");

    let mut wrong_state = valid.clone();
    wrong_state.safe_idle.idle_turn_state = ChatTurnState::Listening;
    assert!(wrong_state.validate().is_err());

    let mut wrong_stop = valid.clone();
    wrong_stop.safe_idle.stop_behavior_id = "behavior.reset".to_string();
    assert!(wrong_stop.validate().is_err());

    let mut wrong_expression = valid.clone();
    wrong_expression.safe_idle.neutral_expression_id = "expression.happy".to_string();
    assert!(wrong_expression.validate().is_err());

    let mut wrong_mouth = valid.clone();
    wrong_mouth.safe_idle.rest_mouth_pose_id = "mouth.open_small".to_string();
    assert!(wrong_mouth.validate().is_err());

    let mut missing_reference = valid.clone();
    missing_reference.safe_idle.stop_behavior_id = "behavior.missing".to_string();
    assert!(missing_reference.validate().is_err());

    let mut inactive_reference = valid.clone();
    inactive_reference
        .capabilities
        .iter_mut()
        .find(|entry| entry.id == "expression.neutral")
        .expect("neutral expression")
        .status = CapabilityStatus::ShadowValidated;
    assert!(inactive_reference.validate().is_err());

    let mut reclassified_reference = valid.clone();
    reclassified_reference
        .capabilities
        .iter_mut()
        .find(|entry| entry.id == "behavior.stop")
        .expect("stop behavior")
        .category = wizard_avatar_engine::capability_manifest::CapabilityCategoryV1::RootMotion;
    assert!(reclassified_reference.validate().is_err());

    let mut wrong_command = valid.clone();
    wrong_command
        .capabilities
        .iter_mut()
        .find(|entry| entry.id == "mouth.closed")
        .expect("rest mouth pose")
        .controller_commands = ApplicabilityV1::NotApplicable;
    assert!(wrong_command.validate().is_err());

    let mut false_policies = Vec::new();
    let mut policy = valid.clone();
    policy.safe_idle.preserve_mode = false;
    false_policies.push(policy);
    let mut policy = valid.clone();
    policy.safe_idle.preserve_root_position = false;
    false_policies.push(policy);
    let mut policy = valid.clone();
    policy.safe_idle.preserve_facing = false;
    false_policies.push(policy);
    let mut policy = valid.clone();
    policy.safe_idle.clear_gesture = false;
    false_policies.push(policy);
    let mut policy = valid.clone();
    policy.safe_idle.clear_gaze_override = false;
    false_policies.push(policy);
    let mut policy = valid.clone();
    policy.safe_idle.clear_viseme_override = false;
    false_policies.push(policy);
    let mut policy = valid.clone();
    policy.safe_idle.clear_blink_override = false;
    false_policies.push(policy);
    let mut policy = valid.clone();
    policy.safe_idle.clear_prop_effects = false;
    false_policies.push(policy);
    let mut policy = valid.clone();
    policy.safe_idle.settle_secondary_motion = false;
    false_policies.push(policy);
    for malformed in false_policies {
        assert!(malformed.validate().is_err());
    }

    let mut missing_idle_facing = valid;
    missing_idle_facing
        .state_facing_fallbacks
        .retain(|fallback| {
            fallback.turn_state != ChatTurnState::Idle
                || fallback.requested_facing != Direction::South
        });
    assert!(missing_idle_facing.validate().is_err());
}

#[test]
fn malformed_schema_status_bounds_order_and_fallbacks_are_rejected() {
    let valid = build_wizard_capability_manifest().expect("manifest should build");
    let mut cases = Vec::new();

    let mut wrong_character = valid.clone();
    wrong_character.character_id = "wizard_joe".to_string();
    cases.push(("character", wrong_character));

    let mut wrong_schema = valid.clone();
    wrong_schema.schema_version += 1;
    cases.push(("schema", wrong_schema));

    let mut wrong_version = valid.clone();
    wrong_version.versions.runtime_transport_version += 1;
    cases.push(("version", wrong_version));

    let mut promoted_flag = valid.clone();
    promoted_flag.support.timed_visemes = true;
    cases.push(("flag", promoted_flag));

    let mut neutral_feeling = valid.clone();
    neutral_feeling.feelings.insert(0, Emotion::Neutral);
    cases.push(("neutral feeling", neutral_feeling));

    let mut missing_feeling = valid.clone();
    missing_feeling.feelings.pop();
    cases.push(("missing feeling", missing_feeling));

    let mut unordered = valid.clone();
    unordered.capabilities.swap(0, 1);
    cases.push(("capability order", unordered));

    let mut missing_coverage = valid.clone();
    missing_coverage
        .capabilities
        .iter_mut()
        .find(|entry| entry.kind == CapabilityKind::Pose)
        .expect("pose")
        .pose_coverage = None;
    cases.push(("pose coverage", missing_coverage));

    let mut wrong_status = valid.clone();
    wrong_status
        .capabilities
        .iter_mut()
        .find(|entry| entry.status == CapabilityStatus::ShowcaseOnly)
        .expect("showcase")
        .status = CapabilityStatus::ActiveLegacy;
    cases.push(("status", wrong_status));

    let mut unresolved_fallback = valid.clone();
    unresolved_fallback
        .capabilities
        .iter_mut()
        .find(|entry| entry.status == CapabilityStatus::ShowcaseOnly)
        .expect("showcase")
        .fallback = FallbackTopologyV1::Fallbacks(vec!["missing.pose".to_string()]);
    cases.push(("unresolved fallback", unresolved_fallback));

    let mut self_fallback = valid.clone();
    let entry = self_fallback
        .capabilities
        .iter_mut()
        .find(|entry| entry.kind == CapabilityKind::MotionClip)
        .expect("motion clip");
    entry.fallback = FallbackTopologyV1::Fallbacks(vec![entry.id.clone()]);
    cases.push(("self fallback", self_fallback));

    let mut missing_topology = valid.clone();
    missing_topology.state_facing_fallbacks.pop();
    cases.push(("fallback topology", missing_topology));

    let mut zero_duration = valid.clone();
    zero_duration
        .capabilities
        .iter_mut()
        .find_map(|entry| entry.duration.as_mut())
        .expect("clip duration")
        .nominal_ticks = 0;
    cases.push(("duration bound", zero_duration));

    let mut empty_applicability = valid.clone();
    empty_applicability.capabilities[0].narrative_uses = ApplicabilityV1::Applicable(Vec::new());
    cases.push(("empty applicability", empty_applicability));

    let mut unordered_text = valid;
    unordered_text.capabilities[0].narrative_uses = ApplicabilityV1::Applicable(vec![
        NarrativeUseV1::DeliberateStageTravel,
        NarrativeUseV1::UrgentTravelOrAction,
    ]);
    cases.push(("metadata order", unordered_text));

    for (name, malformed) in cases {
        assert!(malformed.validate().is_err(), "{name} must reject");
    }
}

#[test]
fn serde_is_closed_and_document_hash_mismatch_rejects() {
    let document = build_wizard_capability_document().expect("document");
    let mut value = serde_json::to_value(&document).expect("document JSON");
    assert_eq!(value["manifest"]["schema_version"], 2);
    assert_eq!(value["manifest"]["versions"]["capability_api_version"], 2);
    assert_eq!(value["manifest"]["safe_idle"]["idle_turn_state"], "idle");
    assert_eq!(
        value["manifest"]["safe_idle"]["stop_behavior_id"],
        "behavior.stop"
    );
    let mut unknown_safe_idle = value.clone();
    unknown_safe_idle["manifest"]["safe_idle"]
        .as_object_mut()
        .expect("safe idle object")
        .insert("unknown_policy".to_string(), serde_json::json!(true));
    assert!(serde_json::from_value::<CapabilityDocumentV1>(unknown_safe_idle).is_err());
    value
        .get_mut("manifest")
        .and_then(serde_json::Value::as_object_mut)
        .expect("manifest object")
        .insert("unknown_field".to_string(), serde_json::json!(true));
    assert!(serde_json::from_value::<CapabilityDocumentV1>(value).is_err());

    let mut wrong_hash = document;
    wrong_hash.manifest_sha256 = "0".repeat(64);
    assert!(wrong_hash.validate().is_err());
}

#[test]
fn stale_v1_manifest_and_api_expectations_are_rejected() {
    let valid = build_wizard_capability_manifest().expect("manifest");

    let mut stale_schema = valid.clone();
    stale_schema.schema_version = 1;
    assert!(stale_schema.validate().is_err());

    let mut stale_api = valid;
    stale_api.versions.capability_api_version = 1;
    assert!(stale_api.validate().is_err());
}

#[test]
fn canonical_manifest_hash_is_independently_verified_and_frozen() {
    let first = build_wizard_capability_manifest().expect("first manifest");
    let second = build_wizard_capability_manifest().expect("second manifest");
    let first_json = first.canonical_json().expect("first canonical JSON");
    let second_json = second.canonical_json().expect("second canonical JSON");
    let independent_hash = format!("{:x}", Sha256::digest(&first_json));

    assert_eq!(first_json, second_json);
    assert_eq!(first.sha256().expect("manifest hash"), independent_hash);
    assert_eq!(independent_hash, EXPECTED_MANIFEST_SHA256);
    assert!(first
        .capabilities
        .windows(2)
        .all(|pair| pair[0].id < pair[1].id));

    let document = build_wizard_capability_document().expect("document");
    assert_eq!(document.manifest_sha256, independent_hash);
    document.validate().expect("document should validate");
}

#[tokio::test]
async fn axum_v2_route_and_unversioned_adapter_serve_identical_document() {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind test server");
    let addr = listener.local_addr().expect("test address");
    let app = server::app(ProceduralWizardFrameSource::default());
    let server_task = tokio::spawn(async move {
        axum::serve(listener, app).await.expect("serve test router");
    });

    let versioned = raw_http_get(addr, "/api/avatar/wizard/v2/capabilities").await;
    let adapter = raw_http_get(addr, "/api/avatar/wizard/capabilities").await;
    let stale_v1 = raw_http_get(addr, "/api/avatar/wizard/v1/capabilities").await;
    server_task.abort();

    assert!(versioned.starts_with("HTTP/1.1 200 OK\r\n"));
    assert!(versioned
        .to_ascii_lowercase()
        .contains("content-type: application/json"));
    assert!(adapter.starts_with("HTTP/1.1 200 OK\r\n"));
    assert!(stale_v1.starts_with("HTTP/1.1 404 Not Found\r\n"));
    let versioned_body = versioned.split("\r\n\r\n").nth(1).expect("versioned body");
    let adapter_body = adapter.split("\r\n\r\n").nth(1).expect("adapter body");
    assert_eq!(versioned_body, adapter_body);
    let document: CapabilityDocumentV1 =
        serde_json::from_str(versioned_body).expect("route document JSON");
    assert_eq!(
        document.manifest.character_id,
        WizardState::default().character_id
    );
    assert_eq!(document.manifest_sha256, EXPECTED_MANIFEST_SHA256);
    assert_eq!(
        document.manifest.safe_idle.idle_turn_state,
        ChatTurnState::Idle
    );
    assert_eq!(
        document.manifest.safe_idle.stop_behavior_id,
        "behavior.stop"
    );
    assert_eq!(
        document.manifest.safe_idle.neutral_expression_id,
        "expression.neutral"
    );
    assert_eq!(
        document.manifest.safe_idle.rest_mouth_pose_id,
        "mouth.closed"
    );
    document.validate().expect("route document validates");
}

async fn raw_http_get(addr: SocketAddr, path: &'static str) -> String {
    tokio::task::spawn_blocking(move || {
        let mut stream = TcpStream::connect(addr).expect("connect test router");
        stream
            .write_all(
                format!("GET {path} HTTP/1.1\r\nHost: {addr}\r\nConnection: close\r\n\r\n")
                    .as_bytes(),
            )
            .expect("write HTTP request");
        let mut response = String::new();
        stream
            .read_to_string(&mut response)
            .expect("read HTTP response");
        response
    })
    .await
    .expect("blocking HTTP client")
}

fn assert_explicit<T>(value: &ApplicabilityV1<T>, field: &str, id: &str) {
    if let ApplicabilityV1::Applicable(values) = value {
        assert!(!values.is_empty(), "{id} has empty applicable {field}");
    }
}

fn add_expected_prop(
    expected: &mut BTreeSet<PropRequirementV1>,
    all: PropRequirementV1,
    some: PropRequirementV1,
    count: usize,
    total: usize,
) {
    if count == total {
        expected.insert(all);
    } else if count > 0 {
        expected.insert(some);
    }
}
