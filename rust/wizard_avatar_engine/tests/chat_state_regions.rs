#![allow(dead_code)]

mod chat_event {
    pub use wizard_avatar_engine::chat_event::*;
}

mod chat_performance {
    pub use wizard_avatar_engine::chat_performance::RenderedMouthPose;
}

mod state {
    pub use wizard_avatar_engine::state::*;
}

#[path = "../src/state_regions.rs"]
mod state_regions;

use chat_event::{
    AttentionTarget, ChatTurnState, Emotion, GestureKind, SessionId, SourceId, SourceKind, TurnId,
    UtteranceId, Viseme,
};
use chat_performance::RenderedMouthPose;
use sha2::{Digest, Sha256};
use state::{Direction, WizardState};
use state_regions::*;

fn id(value: &str) -> StateIdV1 {
    StateIdV1::new(value).expect("valid state ID")
}

fn header_bytes(state: &AvatarSemanticStateV1, kind: RegionKind) -> Vec<u8> {
    serde_json::to_vec(state.region_header(kind)).expect("header JSON")
}

fn region_bytes(state: &AvatarSemanticStateV1, kind: RegionKind) -> Vec<u8> {
    match kind {
        RegionKind::Session => serde_json::to_vec(&state.session),
        RegionKind::Conversation => serde_json::to_vec(&state.conversation),
        RegionKind::Speech => serde_json::to_vec(&state.speech),
        RegionKind::Mouth => serde_json::to_vec(&state.mouth),
        RegionKind::Face => serde_json::to_vec(&state.face),
        RegionKind::Gesture => serde_json::to_vec(&state.gesture),
        RegionKind::Pose => serde_json::to_vec(&state.pose),
        RegionKind::Staff => serde_json::to_vec(&state.staff),
        RegionKind::Wings => serde_json::to_vec(&state.wings),
        RegionKind::Effects => serde_json::to_vec(&state.effects),
        RegionKind::Mobility => serde_json::to_vec(&state.mobility),
        RegionKind::Control => serde_json::to_vec(&state.control),
    }
    .expect("region JSON")
}

fn mutation_for(kind: RegionKind) -> RegionMutationV1 {
    match kind {
        RegionKind::Session => RegionMutationV1::Session(SessionStateV1 {
            mode: SessionModeV1::Ready,
            session_id: Some(SessionId::new("session-1").unwrap()),
            turn_id: Some(TurnId::new("turn-1").unwrap()),
            attention_target: AttentionTarget::User,
        }),
        RegionKind::Conversation => RegionMutationV1::Conversation(ConversationStateV1 {
            turn_state: ChatTurnState::Listening,
        }),
        RegionKind::Speech => RegionMutationV1::Speech(SpeechStateV1 {
            mode: SpeechModeV1::Prepared,
            utterance_id: Some(UtteranceId::new("utterance-1").unwrap()),
            plan_hash64: Some(0x1234),
            start_tick: Some(SemanticTick(12)),
            cursor_tick: 3,
            suppressed: false,
        }),
        RegionKind::Mouth => RegionMutationV1::Mouth(MouthStateV1 {
            viseme: Viseme::A,
            rendered_pose: RenderedMouthPose::OpenWide,
            previous_pose: RenderedMouthPose::Closed,
            blend_percent: 75,
            cue_index: Some(2),
            confidence: 90,
        }),
        RegionKind::Face => RegionMutationV1::Face(FaceStateV1 {
            emotion: Emotion::Joy,
            transient_expression: Some(FaceExpressionV1::Happy),
            intensity: 80,
            confidence: 95,
            blink: BlinkStateV1::Closing,
            gaze: AttentionTarget::User,
        }),
        RegionKind::Gesture => RegionMutationV1::Gesture(GestureStateV1 {
            gesture: Some(GestureKind::Explain),
            phase: GesturePhaseV1::Commit,
            marker: GestureMarkerV1::Commit,
            interrupt_policy: GestureInterruptPolicyV1::AtSafeMarker,
            restoration_policy: GestureRestorationPolicyV1::RestorePrevious,
        }),
        RegionKind::Pose => RegionMutationV1::Pose(PoseStateV1 {
            clip_id: Some(id("explain-loop")),
            sample_index: Some(4),
            pose_id: Some(id("front-explain")),
            transition_id: Some(id("idle-to-explain")),
            transition_progress_percent: 60,
            visual_root_millicells: Point2iV1 { x: 10, y: -5 },
            contacts: vec![ContactPointV1::LeftFoot, ContactPointV1::StaffTip],
            presented_state_hash64: 0x55aa,
        }),
        RegionKind::Staff => RegionMutationV1::Staff(StaffStateV1 {
            mode: StaffModeV1::Planted,
            hand: HandV1::Right,
            contact: ContactStateV1::Planted,
        }),
        RegionKind::Wings => RegionMutationV1::Wings(WingStateV1 {
            mode: WingModeV1::Glide,
            phase_percent: 50,
            visible: true,
        }),
        RegionKind::Effects => RegionMutationV1::Effects(EffectsStateV1 {
            instances: vec![EffectInstanceV1 {
                effect_id: id("spark-1"),
                kind: EffectKindV1::Magic,
                generation: RegionGeneration(1),
                started_tick: SemanticTick(10),
                deadline_tick: SemanticTick(20),
            }],
        }),
        RegionKind::Mobility => RegionMutationV1::Mobility(MobilityStateV1 {
            mode: MobilityModeV1::GroundWalk,
            position_millicells: Point2iV1 { x: 1_000, y: 2_000 },
            velocity_millicells_per_tick: Point2iV1 { x: 20, y: 0 },
            facing: Direction::East,
            altitude_millicells: 0,
            contacts: vec![ContactPointV1::LeftFoot],
            locomotion_phase_tick: 7,
            wing_phase_tick: 0,
        }),
        RegionKind::Control => RegionMutationV1::Control(ControlStateV1 {
            source_watermarks: vec![SourceWatermarkStateV1 {
                source_kind: SourceKind::Chatbot,
                source_id: SourceId::new("chatbot-1").unwrap(),
                source_sequence: 9,
            }],
            active_mobility_lease: Some(RegionLeaseV1 {
                owner: RegionOwner::MobilityRuntime,
                generation: RegionGeneration(1),
                deadline_tick: SemanticTick(30),
            }),
            safety_clamp: false,
            queue_watermark: 11,
            reconnect_count: 2,
        }),
    }
}

#[test]
fn every_region_mutation_names_one_owner_and_preserves_unrelated_regions_byte_for_byte() {
    for kind in RegionKind::ALL {
        let mut state = AvatarSemanticStateV1::new("wizard-joe");
        let before = RegionKind::ALL.map(|region| region_bytes(&state, region));
        let owner = state.region_header(kind).owner;
        let context = RegionMutationContextV1 {
            owner,
            expected_generation: RegionGeneration(0),
            priority: RegionPriority(40),
            entered_tick: SemanticTick(10),
            deadline_tick: Some(SemanticTick(20)),
        };

        let receipt = state
            .apply_mutation(context, mutation_for(kind))
            .expect("region mutation");
        assert_eq!(receipt.region, kind);
        assert_eq!(receipt.owner, owner);
        assert_eq!(receipt.generation, RegionGeneration(1));
        assert_eq!(state.region_header(kind).generation, RegionGeneration(1));
        assert_eq!(state.region_header(kind).entered_tick, SemanticTick(10));
        assert_eq!(
            state.region_header(kind).deadline_tick,
            Some(SemanticTick(20))
        );

        for (index, other) in RegionKind::ALL.into_iter().enumerate() {
            if other == kind {
                assert_ne!(region_bytes(&state, other), before[index]);
            } else {
                assert_eq!(
                    region_bytes(&state, other),
                    before[index],
                    "{kind:?} changed {other:?}"
                );
                assert_eq!(state.region_header(other).generation, RegionGeneration(0));
            }
        }
    }
}

#[test]
fn ownership_takeover_stale_generation_priority_conflict_and_overflow_are_atomic() {
    let mut state = AvatarSemanticStateV1::new("wizard-joe");
    let before = serde_json::to_vec(&state).unwrap();
    let conflict = state
        .apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::SafetyOverride,
                expected_generation: RegionGeneration(0),
                priority: RegionPriority(0),
                entered_tick: SemanticTick(1),
                deadline_tick: None,
            },
            mutation_for(RegionKind::Conversation),
        )
        .expect_err("equal-priority different owner conflicts");
    assert_eq!(
        conflict,
        StateRegionError::ConflictingOwner {
            region: RegionKind::Conversation,
            current_owner: RegionOwner::ConversationRuntime,
            current_priority: RegionPriority(0),
            requested_owner: RegionOwner::SafetyOverride,
            requested_priority: RegionPriority(0),
        }
    );
    assert_eq!(serde_json::to_vec(&state).unwrap(), before);

    state
        .apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::ConversationRuntime,
                expected_generation: RegionGeneration(0),
                priority: RegionPriority(40),
                entered_tick: SemanticTick(1),
                deadline_tick: None,
            },
            mutation_for(RegionKind::Conversation),
        )
        .expect("current owner may raise priority");
    assert_eq!(
        state.conversation.header.owner,
        RegionOwner::ConversationRuntime
    );

    let after_first = serde_json::to_vec(&state).unwrap();
    assert_eq!(
        state.apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::SafetyOverride,
                expected_generation: RegionGeneration(1),
                priority: RegionPriority(39),
                entered_tick: SemanticTick(2),
                deadline_tick: None,
            },
            mutation_for(RegionKind::Conversation),
        ),
        Err(StateRegionError::ConflictingOwner {
            region: RegionKind::Conversation,
            current_owner: RegionOwner::ConversationRuntime,
            current_priority: RegionPriority(40),
            requested_owner: RegionOwner::SafetyOverride,
            requested_priority: RegionPriority(39),
        })
    );
    assert_eq!(serde_json::to_vec(&state).unwrap(), after_first);

    assert_eq!(
        state.apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::ConversationRuntime,
                expected_generation: RegionGeneration(0),
                priority: RegionPriority(40),
                entered_tick: SemanticTick(2),
                deadline_tick: None,
            },
            mutation_for(RegionKind::Conversation),
        ),
        Err(StateRegionError::StaleGeneration {
            region: RegionKind::Conversation,
            expected: RegionGeneration(0),
            actual: RegionGeneration(1),
        })
    );
    assert_eq!(serde_json::to_vec(&state).unwrap(), after_first);

    assert_eq!(
        state.apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::ConversationRuntime,
                expected_generation: RegionGeneration(1),
                priority: RegionPriority(39),
                entered_tick: SemanticTick(2),
                deadline_tick: None,
            },
            mutation_for(RegionKind::Conversation),
        ),
        Err(StateRegionError::PriorityConflict {
            region: RegionKind::Conversation,
            current_priority: RegionPriority(40),
            requested_priority: RegionPriority(39),
        })
    );
    assert_eq!(serde_json::to_vec(&state).unwrap(), after_first);

    let mut takeover = AvatarSemanticStateV1::new("wizard-joe");
    let before_takeover = RegionKind::ALL.map(|region| region_bytes(&takeover, region));
    let receipt = takeover
        .apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::SafetyOverride,
                expected_generation: RegionGeneration(0),
                priority: RegionPriority(1),
                entered_tick: SemanticTick(2),
                deadline_tick: Some(SemanticTick(8)),
            },
            mutation_for(RegionKind::Conversation),
        )
        .expect("strictly higher priority acquires atomically");
    assert_eq!(receipt.region, RegionKind::Conversation);
    assert_eq!(receipt.owner, RegionOwner::SafetyOverride);
    assert_eq!(receipt.generation, RegionGeneration(1));
    assert_eq!(
        takeover.conversation.header.owner,
        RegionOwner::SafetyOverride
    );
    assert_eq!(takeover.conversation.header.priority, RegionPriority(1));
    for (index, region) in RegionKind::ALL.into_iter().enumerate() {
        if region == RegionKind::Conversation {
            assert_ne!(region_bytes(&takeover, region), before_takeover[index]);
            assert_eq!(
                takeover.region_header(region).generation,
                RegionGeneration(1)
            );
        } else {
            assert_eq!(region_bytes(&takeover, region), before_takeover[index]);
            assert_eq!(
                takeover.region_header(region).generation,
                RegionGeneration(0)
            );
        }
    }

    state.face.header.generation = RegionGeneration(u64::MAX);
    let before_overflow = serde_json::to_vec(&state).unwrap();
    let overflow = state
        .apply_mutation(
            RegionMutationContextV1 {
                owner: state.face.header.owner,
                expected_generation: RegionGeneration(u64::MAX),
                priority: state.face.header.priority,
                entered_tick: SemanticTick(2),
                deadline_tick: None,
            },
            mutation_for(RegionKind::Face),
        )
        .expect_err("generation cannot wrap");
    assert_eq!(
        overflow,
        StateRegionError::GenerationOverflow {
            region: RegionKind::Face
        }
    );
    assert_eq!(serde_json::to_vec(&state).unwrap(), before_overflow);
}

#[test]
fn deadlines_reject_validation_at_equality_but_allow_atomic_fresh_replacement() {
    let mut state = AvatarSemanticStateV1::new("wizard-joe");
    state
        .apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::ConversationRuntime,
                expected_generation: RegionGeneration(0),
                priority: RegionPriority(0),
                entered_tick: SemanticTick(5),
                deadline_tick: Some(SemanticTick(10)),
            },
            mutation_for(RegionKind::Conversation),
        )
        .unwrap();
    assert!(state.validate_at(SemanticTick(9)).is_ok());
    assert_eq!(
        state.validate_at(SemanticTick(10)),
        Err(StateRegionError::ExpiredRegion {
            region: RegionKind::Conversation,
            deadline_tick: SemanticTick(10),
            current_tick: SemanticTick(10),
        })
    );

    let expired_state = serde_json::to_vec(&state).unwrap();
    assert_eq!(
        state.apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::ConversationRuntime,
                expected_generation: RegionGeneration(1),
                priority: RegionPriority(0),
                entered_tick: SemanticTick(10),
                deadline_tick: Some(SemanticTick(10)),
            },
            mutation_for(RegionKind::Conversation),
        ),
        Err(StateRegionError::ExpiredDeadline {
            region: RegionKind::Conversation,
            deadline_tick: SemanticTick(10),
            current_tick: SemanticTick(10),
        })
    );
    assert_eq!(serde_json::to_vec(&state).unwrap(), expired_state);

    assert_eq!(
        state.apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::ConversationRuntime,
                expected_generation: RegionGeneration(0),
                priority: RegionPriority(0),
                entered_tick: SemanticTick(10),
                deadline_tick: Some(SemanticTick(20)),
            },
            mutation_for(RegionKind::Conversation),
        ),
        Err(StateRegionError::StaleGeneration {
            region: RegionKind::Conversation,
            expected: RegionGeneration(0),
            actual: RegionGeneration(1),
        })
    );
    assert_eq!(serde_json::to_vec(&state).unwrap(), expired_state);

    let recovered = state
        .apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::SafetyOverride,
                expected_generation: RegionGeneration(1),
                priority: RegionPriority(1),
                entered_tick: SemanticTick(10),
                deadline_tick: Some(SemanticTick(20)),
            },
            mutation_for(RegionKind::Conversation),
        )
        .expect("expired generation can be replaced at the exact deadline");
    assert_eq!(recovered.generation, RegionGeneration(2));
    assert_eq!(recovered.owner, RegionOwner::SafetyOverride);
    assert_eq!(
        state.conversation.header.deadline_tick,
        Some(SemanticTick(20))
    );
    assert!(state.validate_at(SemanticTick(19)).is_ok());
    assert!(matches!(
        state.validate_at(SemanticTick(20)),
        Err(StateRegionError::ExpiredRegion {
            region: RegionKind::Conversation,
            ..
        })
    ));

    let recovered_state = serde_json::to_vec(&state).unwrap();
    assert_eq!(
        state.apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::SafetyOverride,
                expected_generation: RegionGeneration(1),
                priority: RegionPriority(1),
                entered_tick: SemanticTick(21),
                deadline_tick: Some(SemanticTick(30)),
            },
            mutation_for(RegionKind::Conversation),
        ),
        Err(StateRegionError::StaleGeneration {
            region: RegionKind::Conversation,
            expected: RegionGeneration(1),
            actual: RegionGeneration(2),
        })
    );
    assert_eq!(serde_json::to_vec(&state).unwrap(), recovered_state);
}

#[test]
fn deterministic_replay_and_serde_are_byte_stable() {
    fn replay() -> Vec<Vec<u8>> {
        let mut state = AvatarSemanticStateV1::new("wizard-joe");
        let mut snapshots = vec![serde_json::to_vec(&state).unwrap()];
        for (offset, kind) in RegionKind::ALL.into_iter().enumerate() {
            let owner = state.region_header(kind).owner;
            state
                .apply_mutation(
                    RegionMutationContextV1 {
                        owner,
                        expected_generation: RegionGeneration(0),
                        priority: RegionPriority(25),
                        entered_tick: SemanticTick(offset as u64 + 1),
                        deadline_tick: None,
                    },
                    mutation_for(kind),
                )
                .unwrap();
            snapshots.push(serde_json::to_vec(&state).unwrap());
        }
        snapshots
    }

    let first = replay();
    let second = replay();
    assert_eq!(first, second);
    let first_hashes: Vec<_> = first.iter().map(Sha256::digest).collect();
    let second_hashes: Vec<_> = second.iter().map(Sha256::digest).collect();
    assert_eq!(first_hashes, second_hashes);
    for bytes in first {
        let decoded: AvatarSemanticStateV1 = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(serde_json::to_vec(&decoded).unwrap(), bytes);
    }
}

#[test]
fn legacy_protocol_v1_projection_preserves_every_wizard_state_field_and_is_one_way() {
    let default_projection: WizardState = (&AvatarSemanticStateV1::new("wizard-joe")).into();
    let default_projection_value = serde_json::to_value(default_projection).unwrap();
    let legacy_default = serde_json::to_value(WizardState::default()).unwrap();
    let default_projection_fields = default_projection_value.as_object().unwrap();
    let default_fields = legacy_default.as_object().unwrap();
    assert_eq!(default_projection_fields.len(), default_fields.len());
    for (field, default_value) in default_fields {
        let projected_value = default_projection_fields
            .get(field)
            .unwrap_or_else(|| panic!("missing legacy field {field}"));
        assert_eq!(
            json_type(projected_value),
            json_type(default_value),
            "legacy type for {field}"
        );
    }

    let mut state = AvatarSemanticStateV1::new("wizard-joe");
    for (offset, kind) in RegionKind::ALL.into_iter().enumerate() {
        let owner = state.region_header(kind).owner;
        state
            .apply_mutation(
                RegionMutationContextV1 {
                    owner,
                    expected_generation: RegionGeneration(0),
                    priority: RegionPriority(10),
                    entered_tick: SemanticTick(offset as u64 + 1),
                    deadline_tick: None,
                },
                mutation_for(kind),
            )
            .unwrap();
    }
    let projected: WizardState = (&state).into();
    let value = serde_json::to_value(&projected).unwrap();
    let projected_fields = value.as_object().unwrap();
    assert_eq!(projected_fields.len(), default_fields.len());
    for field in default_fields.keys() {
        assert!(
            projected_fields.contains_key(field),
            "missing legacy field {field}"
        );
    }
    assert_eq!(value["character_id"], "wizard-joe");
    assert_eq!(value["facing"], "east");
    assert_eq!(value["locomotion"], "walking");
    assert_eq!(value["action"], "explaining");
    assert_eq!(value["expression"], "happy");
    assert_eq!(value["mouth"], "open_wide");
    assert_eq!(value["staff_state"], "rest");
    assert_eq!(value["effect_state"], "cast");
    assert_eq!(value["speech_id"], "utterance-1");
    assert_eq!(value["simulation_tick"], 12);
    assert_eq!(value["pose_id"], "front-explain");
    assert_eq!(value["pose_clip_id"], "explain-loop");
    assert_eq!(value["pose_clip_step"], 4);
    assert_eq!(value["reconnect_count"], 2);

    let bytes = serde_json::to_vec(&projected).unwrap();
    let decoded: WizardState = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(serde_json::to_vec(&decoded).unwrap(), bytes);

    let source = include_str!("../src/state_regions.rs");
    assert!(!source.contains("From<WizardState> for AvatarSemanticStateV1"));
    assert!(!source.contains("TryFrom<WizardState> for AvatarSemanticStateV1"));
}

fn json_type(value: &serde_json::Value) -> &'static str {
    match value {
        serde_json::Value::Null => "null",
        serde_json::Value::Bool(_) => "bool",
        serde_json::Value::Number(number) if number.is_i64() => "i64",
        serde_json::Value::Number(number) if number.is_u64() => "u64",
        serde_json::Value::Number(_) => "float",
        serde_json::Value::String(_) => "string",
        serde_json::Value::Array(_) => "array",
        serde_json::Value::Object(_) => "object",
    }
}

#[test]
fn canonical_state_has_no_float_wall_clock_or_private_text_fields() {
    let source = include_str!("../src/state_regions.rs");
    for forbidden in [
        "SystemTime",
        "Instant",
        "response_text",
        "private_text",
        "utterance_text",
    ] {
        assert!(
            !source.contains(forbidden),
            "forbidden canonical state token: {forbidden}"
        );
    }
    fn assert_integer_numbers(value: &serde_json::Value) {
        match value {
            serde_json::Value::Number(number) => assert!(!number.is_f64()),
            serde_json::Value::Array(values) => values.iter().for_each(assert_integer_numbers),
            serde_json::Value::Object(values) => values.values().for_each(assert_integer_numbers),
            _ => {}
        }
    }
    assert_integer_numbers(
        &serde_json::to_value(AvatarSemanticStateV1::new("wizard-joe")).unwrap(),
    );
}

#[test]
fn bounded_effects_and_percent_fields_reject_invalid_values_without_mutation() {
    let mut state = AvatarSemanticStateV1::new("wizard-joe");
    let before = serde_json::to_vec(&state).unwrap();
    let mut effects = Vec::new();
    for index in 0..=MAX_EFFECT_INSTANCES {
        effects.push(EffectInstanceV1 {
            effect_id: id(&format!("effect-{index}")),
            kind: EffectKindV1::Emphasis,
            generation: RegionGeneration(index as u64),
            started_tick: SemanticTick(1),
            deadline_tick: SemanticTick(2),
        });
    }
    assert_eq!(
        state.apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::EffectsRuntime,
                expected_generation: RegionGeneration(0),
                priority: RegionPriority(0),
                entered_tick: SemanticTick(1),
                deadline_tick: None,
            },
            RegionMutationV1::Effects(EffectsStateV1 { instances: effects }),
        ),
        Err(StateRegionError::CapacityExceeded {
            region: RegionKind::Effects,
            maximum: MAX_EFFECT_INSTANCES,
        })
    );
    assert_eq!(serde_json::to_vec(&state).unwrap(), before);

    let mut invalid_mouth = match mutation_for(RegionKind::Mouth) {
        RegionMutationV1::Mouth(value) => value,
        _ => unreachable!(),
    };
    invalid_mouth.confidence = 101;
    assert_eq!(
        state.apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::SpeechRuntime,
                expected_generation: RegionGeneration(0),
                priority: RegionPriority(0),
                entered_tick: SemanticTick(1),
                deadline_tick: None,
            },
            RegionMutationV1::Mouth(invalid_mouth),
        ),
        Err(StateRegionError::InvalidPercent {
            region: RegionKind::Mouth,
            field: "confidence",
            value: 101,
        })
    );
    assert_eq!(serde_json::to_vec(&state).unwrap(), before);
}

#[test]
fn duplicate_control_source_watermark_identities_are_rejected_without_mutation() {
    let mut state = AvatarSemanticStateV1::new("wizard-joe");
    let before = serde_json::to_vec(&state).unwrap();
    let watermark = SourceWatermarkStateV1 {
        source_kind: SourceKind::Chatbot,
        source_id: SourceId::new("chatbot-1").unwrap(),
        source_sequence: 10,
    };
    let duplicate = SourceWatermarkStateV1 {
        source_sequence: 11,
        ..watermark.clone()
    };
    let error = state
        .apply_mutation(
            RegionMutationContextV1 {
                owner: RegionOwner::ControlRuntime,
                expected_generation: RegionGeneration(0),
                priority: RegionPriority(0),
                entered_tick: SemanticTick(1),
                deadline_tick: None,
            },
            RegionMutationV1::Control(ControlStateV1 {
                source_watermarks: vec![watermark, duplicate],
                active_mobility_lease: None,
                safety_clamp: false,
                queue_watermark: 0,
                reconnect_count: 0,
            }),
        )
        .expect_err("duplicate source identity is ambiguous");
    assert_eq!(
        error,
        StateRegionError::DuplicateSourceWatermark { index: 1 }
    );
    assert_eq!(serde_json::to_vec(&state).unwrap(), before);
}
