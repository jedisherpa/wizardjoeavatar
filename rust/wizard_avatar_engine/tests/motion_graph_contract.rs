#![allow(dead_code)]

#[path = "../src/chat_event.rs"]
mod chat_event;
#[path = "../src/chat_performance.rs"]
mod chat_performance;
#[path = "../src/command.rs"]
mod command;
#[path = "../src/motion_graph.rs"]
mod motion_graph;
#[path = "../src/state.rs"]
mod state;

use chat_event::{
    AttentionTarget, ChatTurnState, Emotion, GestureKind, MotionProfile, SpeechPlanV1, Viseme,
};
use chat_performance::{
    quantize_speech_plan_v1, ChatPerformanceContentV1, ChatPerformanceIntent, GazeIntentV1,
    PerformanceIntentError, QuantizedSpeechTrackV1, RenderedMouthPose, DURATION_FALLBACK_VERSION,
};
use command::{CommandEnvelopeV1, CommandRequestV1, RuntimeEpoch};
use motion_graph::{MotionGraphLoadError, MotionGraphV1, REQUIRED_RECIPE_IDS};
use serde_json::{json, Value};
use state::MouthShape;

const GOOD_GRAPH: &str = include_str!("fixtures/motion/good_graph_v1.json");
const BAD_UNKNOWN_FIELD: &str = include_str!("fixtures/motion/bad_unknown_field.patch.json");
const BAD_MISSING_REFERENCE: &str =
    include_str!("fixtures/motion/bad_missing_reference.patch.json");
const BAD_MARKED_LOOP: &str = include_str!("fixtures/motion/bad_marked_loop.patch.json");

fn good_graph_value() -> Value {
    serde_json::from_str(GOOD_GRAPH).expect("good graph fixture is JSON")
}

fn merge_top_level_patch(patch: &str) -> String {
    let mut graph = good_graph_value();
    let patch: Value = serde_json::from_str(patch).expect("patch fixture is JSON");
    graph
        .as_object_mut()
        .expect("graph fixture is an object")
        .extend(
            patch
                .as_object()
                .expect("patch fixture is an object")
                .clone(),
        );
    serde_json::to_string(&graph).expect("serialize patched graph")
}

fn timed_speech_plan() -> SpeechPlanV1 {
    serde_json::from_value(json!({
        "utterance_id": "utterance-0001",
        "text_hash": "0000000000000000000000000000000000000000000000000000000000000000",
        "text_length": 42,
        "duration_ms": 100,
        "timing_source": "timed_visemes",
        "cues": [
            {"start_ms": 0, "end_ms": 8, "viseme": "mbp", "weight": 90},
            {"start_ms": 8, "end_ms": 25, "viseme": "a", "weight": 70}
        ],
        "markers": [
            {"at_ms": 0, "kind": "phrase_start"},
            {"at_ms": 17, "kind": "accent"},
            {"at_ms": 100, "kind": "turn_end"}
        ]
    }))
    .expect("timed speech plan")
}

fn duration_only_speech_plan() -> SpeechPlanV1 {
    serde_json::from_value(json!({
        "utterance_id": "utterance-duration-only",
        "text_hash": "1111111111111111111111111111111111111111111111111111111111111111",
        "text_length": 0,
        "duration_ms": 500,
        "timing_source": "duration_only",
        "cues": [],
        "markers": [
            {"at_ms": 0, "kind": "phrase_start"},
            {"at_ms": 500, "kind": "turn_end"}
        ]
    }))
    .expect("duration-only speech plan")
}

fn command_envelope() -> CommandEnvelopeV1 {
    let value = json!({
        "schema_version": 1,
        "command_id": "command-0001",
        "source_id": "chatbot-0001",
        "source_kind": "chatbot",
        "source_sequence": 7,
        "requested_apply_tick": null,
        "ttl_ms": 1000,
        "command": {
            "type": "set_motion_intent",
            "payload": {
                "state": "preparing_response",
                "intensity": 50,
                "profile": "full"
            }
        }
    });
    let request =
        CommandRequestV1::from_json(&serde_json::to_vec(&value).expect("serialize command"), 100)
            .expect("valid command request");
    CommandEnvelopeV1::assign(request, 41, 100).expect("assign command")
}

fn performance_intent(speech: Option<QuantizedSpeechTrackV1>) -> ChatPerformanceIntent {
    let envelope = command_envelope();
    ChatPerformanceIntent::from_command_envelope(
        &envelope,
        RuntimeEpoch(3),
        ChatPerformanceContentV1 {
            turn_state: ChatTurnState::PreparingResponse,
            emotion: Emotion::Neutral,
            intensity: 50,
            confidence: 100,
            urgency: 20,
            speech,
            gaze: GazeIntentV1 {
                target: AttentionTarget::User,
                hold_ticks: 30,
                return_to_user: true,
            },
            gesture_hint: Some(GestureKind::Explain),
            motion_profile: MotionProfile::Full,
            deterministic_seed: 42,
            minimum_hold_ticks: 6,
        },
    )
}

#[test]
fn shared_semantic_types_are_the_runtime_types() {
    let envelope = command_envelope();
    let intent = performance_intent(None);
    let state: ChatTurnState = intent.turn_state;
    let emotion: Emotion = intent.emotion;
    let profile: MotionProfile = intent.motion_profile;
    let gaze: AttentionTarget = intent.gaze.target;
    let gesture: GestureKind = intent.gesture_hint.expect("gesture");

    assert_eq!(state, ChatTurnState::PreparingResponse);
    assert_eq!(emotion, Emotion::Neutral);
    assert_eq!(profile, MotionProfile::Full);
    assert_eq!(gaze, AttentionTarget::User);
    assert_eq!(gesture, GestureKind::Explain);
    assert_eq!(intent.command_id, envelope.command_id);
    assert_eq!(intent.server_sequence, envelope.server_sequence);
    assert_eq!(intent.apply_tick, envelope.apply_tick);
    assert_eq!(intent.expires_tick, envelope.expires_tick);
    assert_eq!(intent.runtime_epoch, RuntimeEpoch(3));
}

#[test]
fn canonical_turn_states_have_exact_snake_case_wire_values() {
    let expected = [
        "idle",
        "listening",
        "thinking",
        "preparing_response",
        "speaking",
        "clarifying",
        "tool_wait",
        "error",
        "celebrating",
        "interrupted",
    ];
    let encoded = ChatTurnState::ALL.map(|state| {
        serde_json::to_value(state)
            .expect("serialize state")
            .as_str()
            .expect("state is a string")
            .to_string()
    });
    assert_eq!(encoded, expected);
    for shorthand in ["listen", "think", "speak", "clarify", "celebrate"] {
        assert!(serde_json::from_value::<ChatTurnState>(json!(shorthand)).is_err());
    }
}

#[test]
fn semantic_visemes_map_exhaustively_through_the_legacy_boundary() {
    let expected = [
        (Viseme::Rest, RenderedMouthPose::Closed, MouthShape::Closed),
        (Viseme::MBP, RenderedMouthPose::Closed, MouthShape::Closed),
        (
            Viseme::FV,
            RenderedMouthPose::OpenSmall,
            MouthShape::OpenSmall,
        ),
        (
            Viseme::TH,
            RenderedMouthPose::OpenSmall,
            MouthShape::OpenSmall,
        ),
        (
            Viseme::DTLN,
            RenderedMouthPose::OpenSmall,
            MouthShape::OpenSmall,
        ),
        (
            Viseme::KG,
            RenderedMouthPose::OpenMedium,
            MouthShape::OpenMedium,
        ),
        (
            Viseme::CHSH,
            RenderedMouthPose::OpenMedium,
            MouthShape::OpenMedium,
        ),
        (
            Viseme::SZ,
            RenderedMouthPose::OpenSmall,
            MouthShape::OpenSmall,
        ),
        (Viseme::R, RenderedMouthPose::Rounded, MouthShape::Rounded),
        (Viseme::A, RenderedMouthPose::OpenWide, MouthShape::OpenWide),
        (Viseme::E, RenderedMouthPose::Smile, MouthShape::Smile),
        (Viseme::I, RenderedMouthPose::Smile, MouthShape::Smile),
        (Viseme::O, RenderedMouthPose::Rounded, MouthShape::Rounded),
        (Viseme::U, RenderedMouthPose::Rounded, MouthShape::Rounded),
    ];
    assert_eq!(expected.len(), Viseme::ALL.len());
    for (viseme, rendered, legacy) in expected {
        assert_eq!(RenderedMouthPose::from(viseme), rendered);
        assert_eq!(MouthShape::from(rendered), legacy);
    }
    assert_eq!(RenderedMouthPose::ALL.len(), 7);
    assert_eq!(
        MouthShape::from(RenderedMouthPose::Frown),
        MouthShape::Frown
    );
}

#[test]
fn ingress_speech_quantizes_half_up_and_drops_content_metadata() {
    let plan = timed_speech_plan();
    let track = quantize_speech_plan_v1(&plan).expect("quantize speech");
    assert_eq!(track.duration_ticks, 6);
    assert_eq!(track.utterance_id, plan.utterance_id);
    assert_eq!(track.cues.len(), 2);
    assert_eq!(
        (
            track.cues[0].start_tick,
            track.cues[0].peak_tick,
            track.cues[0].end_tick
        ),
        (0, 1, 1)
    );
    assert_eq!(
        (
            track.cues[1].start_tick,
            track.cues[1].peak_tick,
            track.cues[1].end_tick
        ),
        (1, 2, 2)
    );
    assert_eq!(track.cues[0].strength, 90);
    assert_eq!(
        track
            .markers
            .iter()
            .map(|marker| marker.tick)
            .collect::<Vec<_>>(),
        [0, 1, 6]
    );

    let value = serde_json::to_value(&track).expect("serialize quantized track");
    assert!(value.get("text_hash").is_none());
    assert!(value.get("text_length").is_none());
    assert!(value.get("text").is_none());
    track.validate().expect("quantized track validates");
}

#[test]
fn duration_only_fallback_is_repeatable_and_seeded_by_utterance_id() {
    assert_eq!(DURATION_FALLBACK_VERSION, 1);
    let plan = duration_only_speech_plan();
    let first = quantize_speech_plan_v1(&plan).expect("first quantization");
    let second = quantize_speech_plan_v1(&plan).expect("second quantization");
    assert_eq!(first, second);
    assert_eq!(first.duration_ticks, 30);
    assert!(!first.cues.is_empty());
    assert_eq!(first.cues.first().expect("first cue").start_tick, 0);
    assert_eq!(first.cues.last().expect("last cue").end_tick, 30);
    assert!(first
        .cues
        .windows(2)
        .all(|pair| pair[0].end_tick == pair[1].start_tick));
    assert!(first
        .cues
        .iter()
        .all(|cue| matches!(cue.viseme, Viseme::Rest | Viseme::A | Viseme::E | Viseme::O)));
}

#[test]
fn performance_intent_has_only_server_provenance_and_is_strict() {
    let track = quantize_speech_plan_v1(&timed_speech_plan()).expect("speech track");
    let intent = performance_intent(Some(track));
    intent.validate().expect("intent validates");
    let value = serde_json::to_value(&intent).expect("serialize intent");
    for forbidden in [
        "source_sequence",
        "source_id",
        "source_kind",
        "requested_apply_tick",
        "ttl_ms",
        "pose_id",
        "text",
        "text_hash",
        "text_length",
    ] {
        assert!(
            value.get(forbidden).is_none(),
            "forbidden field {forbidden}"
        );
    }

    let mut raw_pose = value.clone();
    raw_pose["pose_id"] = json!("front_magic_staff_thrust");
    assert!(serde_json::from_value::<ChatPerformanceIntent>(raw_pose).is_err());

    let mut private_text = value;
    private_text["speech"]["text"] = json!("private response content");
    assert!(serde_json::from_value::<ChatPerformanceIntent>(private_text).is_err());
}

#[test]
fn performance_expiry_is_exclusive() {
    let intent = performance_intent(None);
    intent
        .validate_at(intent.expires_tick - 1)
        .expect("last live tick is valid");
    assert!(matches!(
        intent.validate_at(intent.expires_tick),
        Err(PerformanceIntentError::Expired {
            expires_tick: 161,
            current_tick: 161
        })
    ));
}

#[test]
fn good_graph_fixture_round_trips_and_validates_deterministically() {
    let graph = MotionGraphV1::from_json(GOOD_GRAPH).expect("good graph validates");
    assert_eq!(graph.pose_coverage.len(), 89);
    assert_eq!(graph.turn_state_profiles.len(), 10);
    assert_eq!(graph.emotion_profiles.len(), 11);
    let recipe_ids = graph
        .transition_recipes
        .iter()
        .map(|recipe| recipe.recipe_id.as_str())
        .collect::<std::collections::BTreeSet<_>>();
    assert_eq!(
        recipe_ids,
        REQUIRED_RECIPE_IDS
            .into_iter()
            .collect::<std::collections::BTreeSet<_>>()
    );

    let encoded = serde_json::to_vec(&graph).expect("serialize graph");
    let decoded: MotionGraphV1 = serde_json::from_slice(&encoded).expect("decode graph");
    decoded.validate().expect("round-tripped graph validates");
    assert_eq!(
        serde_json::to_vec(&decoded).expect("serialize again"),
        encoded
    );
}

#[test]
fn edges_must_use_recipes_that_admit_both_clip_families() {
    let mut graph = good_graph_value();
    graph["transition_recipes"][0]["source_families"] = json!(["speaking"]);
    let graph: MotionGraphV1 = serde_json::from_value(graph).expect("schema is valid");
    let error = graph.validate().expect_err("family mismatch must fail");
    assert!(error
        .issues
        .iter()
        .any(|issue| issue.contains("source family is not admitted")));
}

#[test]
fn region_masks_and_recovery_values_are_strict() {
    let mut duplicate_region = good_graph_value();
    duplicate_region["clips"][0]["owned_channels"]["regions"] = json!(["base_body", "base_body"]);
    let graph: MotionGraphV1 = serde_json::from_value(duplicate_region).expect("schema is valid");
    assert!(graph
        .validate()
        .expect_err("duplicate regions must fail")
        .issues
        .iter()
        .any(|issue| issue.contains("owned regions contains duplicate values")));

    let mut unknown_recovery = good_graph_value();
    unknown_recovery["transition_recipes"][0]["interrupt_windows"][0]["recovery_policy"] =
        json!("teleport");
    assert!(serde_json::from_value::<MotionGraphV1>(unknown_recovery).is_err());
}

#[test]
fn runtime_images_and_cyclic_recipe_fallbacks_are_rejected() {
    let mut runtime_image = good_graph_value();
    runtime_image["pose_coverage"][0]["pose_id"] = json!("reference/avatar.png");
    let graph: MotionGraphV1 = serde_json::from_value(runtime_image).expect("schema is valid");
    assert!(graph
        .validate()
        .expect_err("runtime image pose must fail")
        .issues
        .iter()
        .any(|issue| issue.contains("not a runtime image path")));

    let mut cycle = good_graph_value();
    let reduced_index = cycle["transition_recipes"]
        .as_array()
        .expect("recipes")
        .iter()
        .position(|recipe| recipe["recipe_id"] == "reduced_motion_handoff")
        .expect("reduced recipe");
    cycle["transition_recipes"][reduced_index]["fallback_recipe_id"] = json!("coherent_handoff");
    let graph: MotionGraphV1 = serde_json::from_value(cycle).expect("schema is valid");
    assert!(graph
        .validate()
        .expect_err("fallback cycle must fail")
        .issues
        .iter()
        .any(|issue| issue.contains("fallback cycle")));
}

#[test]
fn reduced_motion_table_must_match_the_clip_declaration() {
    let mut graph = good_graph_value();
    graph["clips"][0]["reduced_motion_clip_id"] = Value::Null;
    let graph: MotionGraphV1 = serde_json::from_value(graph).expect("schema is valid");
    assert!(graph
        .validate()
        .expect_err("mismatched reduced-motion declarations must fail")
        .issues
        .iter()
        .any(|issue| issue.contains("disagrees with its source clip")));
}

#[test]
fn strict_graph_schema_rejects_unknown_fields() {
    let json = merge_top_level_patch(BAD_UNKNOWN_FIELD);
    let error = MotionGraphV1::from_json(&json).expect_err("unknown field must fail");
    assert!(matches!(error, MotionGraphLoadError::Decode(_)));
    assert!(error.to_string().contains("unknown field"));
}

#[test]
fn graph_validation_reports_missing_references_in_stable_order() {
    let json = merge_top_level_patch(BAD_MISSING_REFERENCE);
    let graph: MotionGraphV1 = serde_json::from_str(&json).expect("schema is valid");
    let first = graph.validate().expect_err("missing clip must fail");
    let second = graph
        .validate()
        .expect_err("same input must fail identically");
    assert_eq!(first, second);
    assert!(first
        .issues
        .iter()
        .any(|issue| issue.contains("default_clip_id missing_clip")));
    assert!(first.issues.windows(2).all(|pair| pair[0] < pair[1]));
}

#[test]
fn marked_loop_fixture_requires_ordered_indexes_and_markers() {
    let mutation: Value = serde_json::from_str(BAD_MARKED_LOOP).expect("mutation fixture");
    let mut graph = good_graph_value();
    let clip_id = mutation["clip_id"].as_str().expect("clip_id");
    let clip = graph["clips"]
        .as_array_mut()
        .expect("clips")
        .iter_mut()
        .find(|clip| clip["clip_id"] == clip_id)
        .expect("target clip");
    clip["loop_start_sample"] = mutation["loop_start_sample"].clone();
    clip["loop_end_sample"] = mutation["loop_end_sample"].clone();

    let graph: MotionGraphV1 = serde_json::from_value(graph).expect("schema is valid");
    let error = graph.validate().expect_err("invalid loop must fail");
    assert!(error
        .issues
        .iter()
        .any(|issue| issue.contains("invalid marked_segment")));
}

#[test]
fn airborne_samples_cannot_claim_planted_contacts() {
    let mut graph = good_graph_value();
    graph["clips"][0]["samples"][0]["support"]["mode"] = json!("airborne");
    let graph: MotionGraphV1 = serde_json::from_value(graph).expect("schema is valid");
    let error = graph.validate().expect_err("airborne contact must fail");
    assert!(error
        .issues
        .iter()
        .any(|issue| issue.contains("airborne but claims contacts")));
}
