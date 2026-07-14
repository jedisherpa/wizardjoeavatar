use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use wizard_avatar_engine::capability_manifest::{
    build_wizard_capability_document, build_wizard_capability_manifest, CapabilityDocumentV1,
    CapabilityKind, CapabilityStatus, RuntimePolicyV1, RuntimeProfileV1, RuntimeSurfaceV1,
    RuntimeTransportV1, CAPABILITY_API_VERSION, CAPABILITY_MANIFEST_SCHEMA_VERSION,
    RUNTIME_POLICY_VERSION, RUNTIME_PROFILE_VERSION, RUNTIME_TRANSPORT_VERSION,
};
use wizard_avatar_engine::chat_event::{
    AttentionTarget, ChatTurnState, Emotion, GestureKind, Viseme, CHAT_EVENT_SCHEMA_VERSION,
};
use wizard_avatar_engine::chat_performance::{
    RenderedMouthPose, CHAT_PERFORMANCE_SCHEMA_VERSION, DURATION_FALLBACK_VERSION,
};
use wizard_avatar_engine::command::COMMAND_SCHEMA_VERSION;
use wizard_avatar_engine::controller::RUNTIME_PROCEDURAL_BEHAVIOR_IDS;
use wizard_avatar_engine::frame_source::ProceduralWizardFrameSource;
use wizard_avatar_engine::motion_catalog::{embedded_motion_graph_json, shadow_motion_catalog};
use wizard_avatar_engine::motion_graph::{CapabilityTier, MOTION_GRAPH_SCHEMA_VERSION};
use wizard_avatar_engine::pose::PoseLibrary;
use wizard_avatar_engine::pose_clip::POSE_CLIPS;
use wizard_avatar_engine::server;
use wizard_avatar_engine::state::{Direction, Expression, WizardState};

const EXPECTED_MANIFEST_SHA256: &str =
    "c2e00c7ece170b731351734b5662d552496a7bef3c75bba3ee5146c12a9bc725";

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
    assert_eq!(manifest.character_id, WizardState::default().character_id);
    assert_eq!(manifest.pose_geometry_count, library.pose_ids().count());
    assert_eq!(manifest.pose_alias_count, library.alias_count());
    assert_eq!(manifest.imported_pose_archive_sha256.len(), 64);
    assert_eq!(manifest.runtime_geometry_authority_sha256.len(), 64);
    assert_eq!(manifest.motion_graph_sha256.len(), 64);
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
        RUNTIME_PROCEDURAL_BEHAVIOR_IDS
            .into_iter()
            .map(str::to_string)
            .collect()
    );
    assert_eq!(
        RUNTIME_PROCEDURAL_BEHAVIOR_IDS
            .into_iter()
            .collect::<BTreeSet<_>>(),
        [
            "behavior.circle",
            "behavior.figure_eight",
            "behavior.move",
            "behavior.path",
            "behavior.periodic_blink",
            "behavior.return_to_center",
            "behavior.speaking_duration",
            "behavior.walk_backward",
            "behavior.walk_forward",
            "behavior.walk_left",
            "behavior.walk_right",
        ]
        .into_iter()
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
                    entry.fallback_ids.as_slice(),
                    std::slice::from_ref(&expected.fallback_pose_id)
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
        .fallback_ids = vec!["missing.pose".to_string()];
    cases.push(("unresolved fallback", unresolved_fallback));

    let mut self_fallback = valid.clone();
    let entry = self_fallback
        .capabilities
        .iter_mut()
        .find(|entry| entry.kind == CapabilityKind::MotionClip)
        .expect("motion clip");
    entry.fallback_ids = vec![entry.id.clone()];
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

    let mut unordered_text = valid;
    unordered_text.capabilities[0].narrative_uses = vec!["z".to_string(), "a".to_string()];
    cases.push(("metadata order", unordered_text));

    for (name, malformed) in cases {
        assert!(malformed.validate().is_err(), "{name} must reject");
    }
}

#[test]
fn serde_is_closed_and_document_hash_mismatch_rejects() {
    let document = build_wizard_capability_document().expect("document");
    let mut value = serde_json::to_value(&document).expect("document JSON");
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
async fn axum_versioned_route_and_unversioned_adapter_serve_identical_document() {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind test server");
    let addr = listener.local_addr().expect("test address");
    let app = server::app(ProceduralWizardFrameSource::default());
    let server_task = tokio::spawn(async move {
        axum::serve(listener, app).await.expect("serve test router");
    });

    let versioned = raw_http_get(addr, "/api/avatar/wizard/v1/capabilities").await;
    let adapter = raw_http_get(addr, "/api/avatar/wizard/capabilities").await;
    server_task.abort();

    assert!(versioned.starts_with("HTTP/1.1 200 OK\r\n"));
    assert!(versioned
        .to_ascii_lowercase()
        .contains("content-type: application/json"));
    assert!(adapter.starts_with("HTTP/1.1 200 OK\r\n"));
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
