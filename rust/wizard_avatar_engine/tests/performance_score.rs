use serde::de::DeserializeOwned;
use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use wizard_avatar_engine::capability_manifest::{
    build_wizard_capability_manifest, CapabilityKind, CapabilityStatus, QualityStatusV1,
};
use wizard_avatar_engine::performance_score::{
    ActiveCueCheckpointV1, CapabilityId, CueId, CuePayloadV1, DirectionV1, GazeTargetV1,
    PerformanceScoreV1, ReducedMotionProfileV1, RegionLayerV1, ScoreEmotionV1, ScoreErrorCode,
    ScoreVisemeV1, Sha256Hex, TrackId, TransitionKindV1, MAX_ACTIVE_CUES, MAX_SCORE_BYTES,
    MAX_SCORE_CHECKPOINTS, MAX_SCORE_CUES, MAX_SCORE_DURATION_US, MAX_SCORE_TRACKS,
};

const FIXTURE: &[u8] = include_bytes!("fixtures/media/performance-score-v1.minimal.json");
const FIXTURE_FILE_SHA256: &str =
    "2af1f3e2ce87fdd68d38cc1deca18d3fadcd5420f80cac54289793a37b2f05cc";
const FIXTURE_SCORE_ID: &str = "de08c30cb0b24302a352f7b75cbeccf328ff8f35fe76a6cd732e7ca90c9e0f69";
const FIXTURE_CAPABILITY_MANIFEST_SHA256: &str =
    "c23ac67eb8c493df980165a3776b081a6bbe2074c5b0731fcdd8db587ffbc36a";
const FIXTURE_MEDIA_SHA256: &str =
    "4ec95cd27fbef0d944a8040cb0ab6e766dc19f89cd6a074b94a07fb0f81a1722";
const FIXTURE_ANIMATION_LIBRARY_SHA256: &str =
    "675feeb8c30f2e028c0e5bfab1de9c9e2f97f608a276a9b308406e12bdb39a9e";
const FIXTURE_MOTION_GRAPH_SHA256: &str =
    "6d22052dc3a43da683c09d3a7da71fa4a4228eaf53bf98a3633205a5f0898a4d";

fn fixture_score() -> PerformanceScoreV1 {
    PerformanceScoreV1::from_json(FIXTURE).expect("canonical fixture must parse")
}

fn expect_invalid(score: &PerformanceScoreV1, code: ScoreErrorCode) {
    let error = score.validate().expect_err("score must reject");
    assert_eq!(error.code, code, "unexpected error: {error}");
}

fn bind_to_runtime_manifest() -> PerformanceScoreV1 {
    let manifest = build_wizard_capability_manifest().expect("manifest");
    let mut score = fixture_score();
    let active_poses = manifest
        .capabilities
        .iter()
        .filter(|entry| {
            entry.kind == CapabilityKind::Pose
                && entry.status == CapabilityStatus::ActiveLegacy
                && entry.quality_status == QualityStatusV1::RuntimeGeometryValidated
        })
        .take(2)
        .collect::<Vec<_>>();
    assert_eq!(active_poses.len(), 2);
    let cue = &mut score.tracks[0].cues[0];
    cue.cue_type = wizard_avatar_engine::performance_score::CueTypeV1::BodyPose;
    cue.capability_id = CapabilityId::new(active_poses[0].id.clone()).unwrap();
    cue.fallback_capability_ids = vec![CapabilityId::new(active_poses[1].id.clone()).unwrap()];
    cue.payload = CuePayloadV1::BodyPose {
        weight_shift_percent: 0,
    };
    score.checkpoints[0].regions[2].active_cues[0].resolved_capability_id =
        cue.capability_id.clone();
    score.header.character_id =
        wizard_avatar_engine::performance_score::CharacterId::new(manifest.character_id.clone())
            .unwrap();
    score.header.capability_manifest_sha256 = Sha256Hex::new(manifest.sha256().unwrap()).unwrap();
    score.header.animation_library_sha256 =
        Sha256Hex::new(manifest.runtime_geometry_authority_sha256.clone()).unwrap();
    score.header.motion_graph_sha256 =
        Sha256Hex::new(manifest.motion_graph_sha256.clone()).unwrap();
    score.recompute_score_id().unwrap();
    score
}

fn assert_wire_domain<T>(accepted: &[&str], rejected: &[&str])
where
    T: DeserializeOwned + Serialize,
{
    for value in accepted {
        let decoded: T = serde_json::from_str(&format!("\"{value}\""))
            .unwrap_or_else(|error| panic!("{value} must decode: {error}"));
        assert_eq!(
            serde_json::to_string(&decoded).unwrap(),
            format!("\"{value}\"")
        );
    }
    for value in rejected {
        assert!(
            serde_json::from_str::<T>(&format!("\"{value}\"")).is_err(),
            "{value} must reject"
        );
    }
}

#[test]
fn canonical_fixture_parses_hashes_and_round_trips_deterministically() {
    assert_eq!(
        format!("{:x}", Sha256::digest(FIXTURE)),
        FIXTURE_FILE_SHA256
    );
    let first = fixture_score();
    let second = fixture_score();
    assert_eq!(first, second);
    assert_eq!(first.header.score_id.as_str(), FIXTURE_SCORE_ID);
    assert_eq!(
        first.header.capability_manifest_sha256.as_str(),
        FIXTURE_CAPABILITY_MANIFEST_SHA256
    );
    assert_eq!(first.header.duration_us, 12_833_333);
    assert_eq!(first.header.media_sha256.as_str(), FIXTURE_MEDIA_SHA256);
    assert_eq!(
        first.header.animation_library_sha256.as_str(),
        FIXTURE_ANIMATION_LIBRARY_SHA256
    );
    assert_eq!(
        first.header.motion_graph_sha256.as_str(),
        FIXTURE_MOTION_GRAPH_SHA256
    );
    assert_eq!(
        first.header.provenance.source_artifact_sha256.as_str(),
        FIXTURE_MEDIA_SHA256
    );
    assert_eq!(first.tracks[0].cues[0].capability_id.as_str(), "front_idle");
    assert_eq!(
        first.tracks[0].cues[0].fallback_capability_ids[0].as_str(),
        "back_idle"
    );
    assert_eq!(
        first.checkpoints[0].regions[2].active_cues[0]
            .resolved_capability_id
            .as_str(),
        "front_idle"
    );
    assert_eq!(
        first.computed_score_id().unwrap().as_str(),
        FIXTURE_SCORE_ID
    );
    assert_eq!(
        format!("{:x}", Sha256::digest(first.canonical_body_json().unwrap())),
        FIXTURE_SCORE_ID
    );
    let canonical = first.canonical_json().unwrap();
    assert_eq!(canonical, second.canonical_json().unwrap());
    assert!(canonical.starts_with(br#"{"checkpoints":"#));
    assert_eq!(PerformanceScoreV1::from_json(&canonical).unwrap(), first);

    let value: Value = serde_json::from_slice(&canonical).unwrap();
    let cue = &value["tracks"][0]["cues"][0];
    assert!(cue.get("start_us").is_some());
    assert!(cue.get("end_us").is_some());
    assert!(cue.get("interval").is_none());
    assert!(value["checkpoints"][0]["regions"][2]["active_cues"].is_array());
}

#[test]
fn frozen_v1_scalar_domains_accept_only_the_repaired_wire_values() {
    assert_wire_domain::<ReducedMotionProfileV1>(
        &["full", "reduced", "minimal"],
        &["none", "low", "FULL"],
    );
    assert_wire_domain::<DirectionV1>(
        &[
            "south",
            "southwest",
            "west",
            "northwest",
            "north",
            "northeast",
            "east",
            "southeast",
        ],
        &["front", "back", "south_west"],
    );
    assert_wire_domain::<GazeTargetV1>(
        &[
            "user",
            "content",
            "staff",
            "down",
            "away_left",
            "away_right",
            "neutral",
        ],
        &["screen", "away", "away-left"],
    );
    assert_wire_domain::<ScoreEmotionV1>(
        &[
            "neutral", "joy", "sadness", "anger", "fear", "shame", "disgust", "surprise", "pride",
            "guilt", "love",
        ],
        &["happy", "focused", "JOY"],
    );
    assert_wire_domain::<ScoreVisemeV1>(
        &[
            "rest", "mbp", "fv", "th", "dtln", "kg", "chsh", "sz", "r", "a", "e", "i", "o", "u",
        ],
        &["silence", "m_b_p", "aa"],
    );
}

#[test]
fn parser_rejects_unknown_fields_old_shapes_floats_and_malformed_scalars() {
    let mut cases = Vec::new();

    let mut unknown: Value = serde_json::from_slice(FIXTURE).unwrap();
    unknown["unknown"] = json!(true);
    cases.push(("unknown field", unknown));

    let mut old_interval: Value = serde_json::from_slice(FIXTURE).unwrap();
    old_interval["tracks"][0]["cues"][0]["interval"] = json!({"start_us": 0, "end_us": 2_000_000});
    cases.push(("old interval", old_interval));

    let mut old_checkpoint: Value = serde_json::from_slice(FIXTURE).unwrap();
    old_checkpoint["checkpoints"][0]["regions"][2]["active_cue_ids"] = json!(["c1"]);
    cases.push(("old checkpoint", old_checkpoint));

    let mut float: Value = serde_json::from_slice(FIXTURE).unwrap();
    float["header"]["duration_us"] = json!(2_000_000.0);
    cases.push(("float", float));

    let mut long_id: Value = serde_json::from_slice(FIXTURE).unwrap();
    long_id["header"]["media_id"] = json!("x".repeat(129));
    cases.push(("long id", long_id));

    let mut uppercase_hash: Value = serde_json::from_slice(FIXTURE).unwrap();
    uppercase_hash["header"]["media_sha256"] = json!("A".repeat(64));
    cases.push(("uppercase hash", uppercase_hash));

    let mut unknown_enum: Value = serde_json::from_slice(FIXTURE).unwrap();
    unknown_enum["header"]["reduced_motion_profile"] = json!("low");
    cases.push(("unknown enum", unknown_enum));

    for (name, value) in cases {
        let bytes = serde_json::to_vec(&value).unwrap();
        assert!(
            PerformanceScoreV1::from_json(&bytes).is_err(),
            "{name} must reject"
        );
    }

    let oversized = vec![b' '; MAX_SCORE_BYTES + 1];
    let error = PerformanceScoreV1::from_json(&oversized).unwrap_err();
    assert_eq!(error.code, ScoreErrorCode::PayloadTooLarge);
}

#[test]
fn header_cue_transition_payload_and_fallback_bounds_fail_closed() {
    let valid = fixture_score();

    let mut cases = Vec::new();
    let mut schema = valid.clone();
    schema.header.schema_version = 2;
    cases.push((ScoreErrorCode::UnsupportedSchemaVersion, schema));

    let mut duration = valid.clone();
    duration.header.duration_us = 0;
    cases.push((ScoreErrorCode::InvalidRange, duration));

    let mut long_duration = valid.clone();
    long_duration.header.duration_us = MAX_SCORE_DURATION_US + 1;
    cases.push((ScoreErrorCode::InvalidRange, long_duration));

    let mut timebase = valid.clone();
    timebase.header.timebase_hz = 1_000;
    cases.push((ScoreErrorCode::InvalidRange, timebase));

    let mut negative_start = valid.clone();
    negative_start.tracks[0].cues[0].start_us = -1;
    cases.push((ScoreErrorCode::InvalidRange, negative_start));

    let mut empty_interval = valid.clone();
    empty_interval.tracks[0].cues[0].end_us = 0;
    cases.push((ScoreErrorCode::InvalidRange, empty_interval));

    let mut cut_duration = valid.clone();
    cut_duration.tracks[0].cues[0].transition_in.duration_us = 1;
    cases.push((ScoreErrorCode::InvalidRange, cut_duration));

    let mut no_fallback = valid.clone();
    no_fallback.tracks[0].cues[0]
        .fallback_capability_ids
        .clear();
    cases.push((ScoreErrorCode::InvalidFallback, no_fallback));

    let mut duplicate_fallback = valid.clone();
    duplicate_fallback.tracks[0].cues[0]
        .fallback_capability_ids
        .push(CapabilityId::new("back_idle").unwrap());
    cases.push((ScoreErrorCode::InvalidFallback, duplicate_fallback));

    let mut primary_fallback = valid.clone();
    primary_fallback.tracks[0].cues[0].fallback_capability_ids[0] =
        CapabilityId::new("front_idle").unwrap();
    cases.push((ScoreErrorCode::InvalidFallback, primary_fallback));

    let mut five_fallbacks = valid.clone();
    five_fallbacks.tracks[0].cues[0].fallback_capability_ids = (0..5)
        .map(|index| CapabilityId::new(format!("fallback-{index}")).unwrap())
        .collect();
    cases.push((ScoreErrorCode::InvalidFallback, five_fallbacks));

    let mut payload_mismatch = valid.clone();
    payload_mismatch.tracks[0].cues[0].payload = CuePayloadV1::BodyPose {
        weight_shift_percent: 10,
    };
    cases.push((ScoreErrorCode::InvalidPayload, payload_mismatch));

    let mut bad_percent = valid.clone();
    bad_percent.tracks[0].cues[0].payload = CuePayloadV1::BodyPose {
        weight_shift_percent: 101,
    };
    cases.push((ScoreErrorCode::InvalidRange, bad_percent));

    let mut bad_coordinate = valid.clone();
    bad_coordinate.tracks[0].cues[0].payload = CuePayloadV1::Locomotion {
        target_x_millicells: 1_000_001,
        target_y_millicells: 0,
        facing: DirectionV1::South,
        speed_percent: 50,
    };
    cases.push((ScoreErrorCode::InvalidRange, bad_coordinate));

    let mut bad_locks = valid.clone();
    bad_locks.tracks[0].cues[0].payload = CuePayloadV1::Stillness {
        locked_layers: vec![RegionLayerV1::Body, RegionLayerV1::Body],
    };
    cases.push((ScoreErrorCode::InvalidPayload, bad_locks));

    let mut mode_lock = valid.clone();
    mode_lock.tracks[0].cues[0].payload = CuePayloadV1::Stillness {
        locked_layers: vec![RegionLayerV1::Mode],
    };
    cases.push((ScoreErrorCode::InvalidPayload, mode_lock));

    let mut secondary = valid;
    secondary.tracks[0].layer = RegionLayerV1::SecondaryMotion;
    secondary.tracks[0].cues[0].layer = RegionLayerV1::SecondaryMotion;
    cases.push((ScoreErrorCode::InvalidLayer, secondary));

    for (code, score) in cases {
        expect_invalid(&score, code);
    }
}

fn score_with_payload(
    cue_type: wizard_avatar_engine::performance_score::CueTypeV1,
    layer: RegionLayerV1,
    payload: CuePayloadV1,
) -> PerformanceScoreV1 {
    let mut score = fixture_score();
    score.tracks[0].layer = layer;
    score.tracks[0].cues[0].layer = layer;
    score.tracks[0].cues[0].cue_type = cue_type;
    score.tracks[0].cues[0].payload = payload;
    score.checkpoints[0].regions[2].active_cues.clear();
    score.checkpoints[0].regions[2].owner_generation = 0;
    let region_index = RegionLayerV1::ALL
        .iter()
        .position(|candidate| *candidate == layer)
        .unwrap();
    score.checkpoints[0].regions[region_index].owner_generation = 1;
    score.checkpoints[0].regions[region_index].active_cues = vec![ActiveCueCheckpointV1 {
        cue_id: CueId::new("c1").unwrap(),
        resolved_capability_id: CapabilityId::new("front_idle").unwrap(),
        cue_local_time_us: 0,
        fallback_index: 0,
    }];
    score.recompute_score_id().unwrap();
    score
}

#[test]
fn all_payload_variants_obey_the_frozen_cue_and_layer_compatibility_table() {
    use wizard_avatar_engine::performance_score::{
        BlinkStateV1, CueTypeV1, GesturePhaseV1, PerformanceModeV1,
    };

    let cases = vec![
        (
            CueTypeV1::Mode,
            RegionLayerV1::Mode,
            CuePayloadV1::Mode {
                mode: PerformanceModeV1::Audiobook,
            },
        ),
        (
            CueTypeV1::Locomotion,
            RegionLayerV1::Root,
            CuePayloadV1::Locomotion {
                target_x_millicells: -1_000_000,
                target_y_millicells: 1_000_000,
                facing: DirectionV1::Southeast,
                speed_percent: 100,
            },
        ),
        (
            CueTypeV1::BodyPose,
            RegionLayerV1::Body,
            CuePayloadV1::BodyPose {
                weight_shift_percent: 100,
            },
        ),
        (
            CueTypeV1::Gesture,
            RegionLayerV1::Gesture,
            CuePayloadV1::Gesture {
                phase: GesturePhaseV1::Recover,
                intensity_percent: 100,
            },
        ),
        (
            CueTypeV1::Gaze,
            RegionLayerV1::Gaze,
            CuePayloadV1::Gaze {
                target: GazeTargetV1::AwayRight,
                head_weight_percent: 100,
                eye_weight_percent: 0,
            },
        ),
        (
            CueTypeV1::Expression,
            RegionLayerV1::Face,
            CuePayloadV1::Expression {
                emotion: ScoreEmotionV1::Love,
                intensity_percent: 100,
            },
        ),
        (
            CueTypeV1::Viseme,
            RegionLayerV1::Speech,
            CuePayloadV1::Viseme {
                viseme: ScoreVisemeV1::MBP,
                weight_percent: 100,
            },
        ),
        (
            CueTypeV1::Blink,
            RegionLayerV1::Blink,
            CuePayloadV1::Blink {
                state: BlinkStateV1::Closed,
            },
        ),
        (
            CueTypeV1::PropEffect,
            RegionLayerV1::PropEffect,
            CuePayloadV1::PropEffect {
                intensity_percent: 100,
            },
        ),
        (
            CueTypeV1::DancePhrase,
            RegionLayerV1::Body,
            CuePayloadV1::DancePhrase {
                beat_phase_q32: u32::MAX,
                energy_percent: 100,
            },
        ),
        (
            CueTypeV1::Stillness,
            RegionLayerV1::Body,
            CuePayloadV1::Stillness {
                locked_layers: vec![RegionLayerV1::Body],
            },
        ),
    ];

    for (cue_type, layer, payload) in cases {
        let valid = score_with_payload(cue_type, layer, payload.clone());
        valid.validate().unwrap();

        let mut wrong_layer = valid;
        wrong_layer.tracks[0].cues[0].payload = payload;
        wrong_layer.tracks[0].cues[0].cue_type = cue_type;
        wrong_layer.tracks[0].cues[0].layer = RegionLayerV1::Stillness;
        expect_invalid(&wrong_layer, ScoreErrorCode::InvalidLayer);
    }

    let mut transitions = fixture_score();
    transitions.tracks[0].cues[0].transition_in.kind = TransitionKindV1::Linear;
    transitions.tracks[0].cues[0].transition_in.duration_us = 10_000_000;
    transitions.tracks[0].cues[0].transition_out.kind = TransitionKindV1::Authored;
    transitions.tracks[0].cues[0].transition_out.duration_us = 10_000_000;
    transitions.recompute_score_id().unwrap();
    transitions.validate().unwrap();
}

#[test]
fn ordering_uniqueness_overlap_and_collection_bounds_are_enforced() {
    let valid = fixture_score();

    let mut duplicate_track = valid.clone();
    duplicate_track
        .tracks
        .push(duplicate_track.tracks[0].clone());
    expect_invalid(&duplicate_track, ScoreErrorCode::DuplicateId);

    let mut track_order = valid.clone();
    let mut earlier = track_order.tracks[0].clone();
    earlier.track_id = TrackId::new("aaa").unwrap();
    track_order.tracks.push(earlier);
    expect_invalid(&track_order, ScoreErrorCode::InvalidOrder);

    let mut duplicate_cue = valid.clone();
    let copied_cue = duplicate_cue.tracks[0].cues[0].clone();
    duplicate_cue.tracks[0].cues.push(copied_cue);
    expect_invalid(&duplicate_cue, ScoreErrorCode::DuplicateId);

    let mut cue_order = valid.clone();
    let mut earlier_cue = cue_order.tracks[0].cues[0].clone();
    earlier_cue.cue_id = CueId::new("c0").unwrap();
    cue_order.tracks[0].cues.push(earlier_cue);
    expect_invalid(&cue_order, ScoreErrorCode::InvalidOrder);

    let mut overlap = valid.clone();
    let mut second = overlap.tracks[0].cues[0].clone();
    second.cue_id = CueId::new("c2").unwrap();
    second.start_us = 1;
    overlap.tracks[0].cues.push(second);
    expect_invalid(&overlap, ScoreErrorCode::InvalidOverlap);

    let mut interleaved_tracks = valid.clone();
    interleaved_tracks.tracks[0].cues[0].end_us = 10;
    let mut late = interleaved_tracks.tracks[0].cues[0].clone();
    late.cue_id = CueId::new("c3").unwrap();
    late.start_us = 100;
    late.end_us = 110;
    interleaved_tracks.tracks[0].cues.push(late);
    let mut middle_track = interleaved_tracks.tracks[0].clone();
    middle_track.track_id = TrackId::new("body-middle").unwrap();
    middle_track.cues.truncate(1);
    middle_track.cues[0].cue_id = CueId::new("c2").unwrap();
    middle_track.cues[0].start_us = 50;
    middle_track.cues[0].end_us = 60;
    interleaved_tracks.tracks.push(middle_track);
    interleaved_tracks.checkpoints[0].next_cue_indices = vec![1, 0];
    interleaved_tracks.recompute_score_id().unwrap();
    interleaved_tracks.validate().unwrap();

    let mut priority_layering = valid.clone();
    let mut higher = priority_layering.tracks[0].cues[0].clone();
    higher.cue_id = CueId::new("c2").unwrap();
    higher.start_us = 1;
    higher.priority = 1;
    priority_layering.tracks[0].cues.push(higher);
    priority_layering.recompute_score_id().unwrap();
    priority_layering.validate().unwrap();

    let mut too_many_tracks = fixture_score();
    too_many_tracks
        .tracks
        .resize(MAX_SCORE_TRACKS + 1, too_many_tracks.tracks[0].clone());
    expect_invalid(&too_many_tracks, ScoreErrorCode::InvalidRange);

    let mut too_many_checkpoints = fixture_score();
    too_many_checkpoints.checkpoints.resize(
        MAX_SCORE_CHECKPOINTS + 1,
        too_many_checkpoints.checkpoints[0].clone(),
    );
    expect_invalid(&too_many_checkpoints, ScoreErrorCode::InvalidRange);

    let mut too_many_cues = fixture_score();
    let template = too_many_cues.tracks[0].cues[0].clone();
    too_many_cues.tracks[0].cues = (0..=MAX_SCORE_CUES)
        .map(|index| {
            let mut cue = template.clone();
            cue.cue_id = CueId::new(format!("c{index:06}")).unwrap();
            cue.start_us = index as i64;
            cue.end_us = 2_000_000;
            cue
        })
        .collect();
    expect_invalid(&too_many_cues, ScoreErrorCode::InvalidRange);
}

fn composed_prop_score() -> PerformanceScoreV1 {
    let mut score = fixture_score();
    let track = &mut score.tracks[0];
    track.layer = RegionLayerV1::PropEffect;
    track.track_id = TrackId::new("prop-main").unwrap();
    let first = &mut track.cues[0];
    first.layer = RegionLayerV1::PropEffect;
    first.cue_type = wizard_avatar_engine::performance_score::CueTypeV1::PropEffect;
    first.capability_id = CapabilityId::new("effect-a").unwrap();
    first.fallback_capability_ids = vec![CapabilityId::new("effect-b").unwrap()];
    first.payload = CuePayloadV1::PropEffect {
        intensity_percent: 60,
    };
    let mut second = first.clone();
    second.cue_id = CueId::new("c2").unwrap();
    second.capability_id = CapabilityId::new("effect-c").unwrap();
    second.fallback_capability_ids = vec![CapabilityId::new("effect-d").unwrap()];
    second.payload = CuePayloadV1::PropEffect {
        intensity_percent: 70,
    };
    track.cues.push(second);

    let checkpoint = &mut score.checkpoints[0];
    checkpoint.next_cue_indices[0] = 2;
    checkpoint.regions[2].active_cues.clear();
    checkpoint.regions[2].owner_generation = 0;
    let prop = &mut checkpoint.regions[8];
    prop.owner_generation = 1;
    prop.active_cues = vec![
        ActiveCueCheckpointV1 {
            cue_id: CueId::new("c1").unwrap(),
            resolved_capability_id: CapabilityId::new("effect-a").unwrap(),
            cue_local_time_us: 0,
            fallback_index: 0,
        },
        ActiveCueCheckpointV1 {
            cue_id: CueId::new("c2").unwrap(),
            resolved_capability_id: CapabilityId::new("effect-d").unwrap(),
            cue_local_time_us: 0,
            fallback_index: 1,
        },
    ];
    score.recompute_score_id().unwrap();
    score
}

#[test]
fn prop_effect_composition_keeps_per_cue_checkpoint_resolution() {
    let score = composed_prop_score();
    score.validate().unwrap();
    assert_eq!(score.checkpoints[0].regions[8].active_cues.len(), 2);

    let mut unsorted = score.clone();
    unsorted.checkpoints[0].regions[8].active_cues.swap(0, 1);
    expect_invalid(&unsorted, ScoreErrorCode::InvalidCheckpoint);

    let mut wrong_fallback = score.clone();
    wrong_fallback.checkpoints[0].regions[8].active_cues[1].fallback_index = 0;
    expect_invalid(&wrong_fallback, ScoreErrorCode::InvalidCheckpoint);

    let mut too_many_active = score;
    let template = too_many_active.tracks[0].cues[0].clone();
    too_many_active.tracks[0].cues = (0..=MAX_ACTIVE_CUES)
        .map(|index| {
            let mut cue = template.clone();
            cue.cue_id = CueId::new(format!("c{index:04}")).unwrap();
            cue.capability_id = CapabilityId::new(format!("effect-{index:04}")).unwrap();
            cue
        })
        .collect();
    expect_invalid(&too_many_active, ScoreErrorCode::InvalidRange);
}

#[test]
fn checkpoints_are_complete_ordered_half_open_and_seekable() {
    let valid = fixture_score();

    let (index, checkpoint) = valid.checkpoint_at_or_before(1_999_999).unwrap();
    assert_eq!(index, 0);
    assert_eq!(checkpoint.at_us, 0);
    assert_eq!(
        valid.checkpoint_at_or_before(-1).unwrap_err().code,
        ScoreErrorCode::InvalidRange
    );
    assert_eq!(
        valid
            .checkpoint_at_or_before(valid.header.duration_us + 1)
            .unwrap_err()
            .code,
        ScoreErrorCode::InvalidRange
    );

    let mut end_boundary = valid.clone();
    let mut end = end_boundary.checkpoints[0].clone();
    end.at_us = end_boundary.header.duration_us;
    end.regions[2].active_cues.clear();
    end.regions[2].owner_generation = 0;
    end_boundary.checkpoints.push(end);
    end_boundary.recompute_score_id().unwrap();
    assert_eq!(
        end_boundary
            .checkpoint_at_or_before(end_boundary.header.duration_us)
            .unwrap()
            .0,
        1
    );

    let mut cases = Vec::new();
    let mut first = valid.clone();
    first.checkpoints[0].at_us = 1;
    cases.push(first);

    let mut missing_region = valid.clone();
    missing_region.checkpoints[0].regions.pop();
    cases.push(missing_region);

    let mut region_order = valid.clone();
    region_order.checkpoints[0].regions.swap(0, 1);
    cases.push(region_order);

    let mut next_index = valid.clone();
    next_index.checkpoints[0].next_cue_indices[0] = 0;
    cases.push(next_index);

    let mut local_time = valid.clone();
    local_time.checkpoints[0].regions[2].active_cues[0].cue_local_time_us = 1;
    cases.push(local_time);

    let mut no_owner = valid.clone();
    no_owner.checkpoints[0].regions[2].owner_generation = 0;
    cases.push(no_owner);

    let mut orphan_owner = valid.clone();
    orphan_owner.checkpoints[0].regions[0].owner_generation = 1;
    cases.push(orphan_owner);

    let mut bad_fallback_index = valid.clone();
    bad_fallback_index.checkpoints[0].regions[2].active_cues[0].fallback_index = 2;
    cases.push(bad_fallback_index);

    let mut gap = valid;
    gap.header.duration_us = 30_000_001;
    gap.tracks[0].cues[0].end_us = 30_000_001;
    cases.push(gap);

    for score in cases {
        expect_invalid(&score, ScoreErrorCode::InvalidCheckpoint);
    }
}

#[test]
fn runtime_manifest_binding_resolves_primary_and_ordered_fallbacks() {
    let manifest = build_wizard_capability_manifest().expect("manifest");
    let fixture = fixture_score();
    fixture.validate_against_manifest(&manifest).unwrap();

    let bound = bind_to_runtime_manifest();
    bound.validate_against_manifest(&manifest).unwrap();

    let mut selected_fallback = bound.clone();
    let selected_fallback_id =
        selected_fallback.tracks[0].cues[0].fallback_capability_ids[0].clone();
    selected_fallback.checkpoints[0].regions[2].active_cues[0].fallback_index = 1;
    selected_fallback.checkpoints[0].regions[2].active_cues[0].resolved_capability_id =
        selected_fallback_id;
    selected_fallback.recompute_score_id().unwrap();
    selected_fallback
        .validate_against_manifest(&manifest)
        .unwrap();

    let mut unknown = bound.clone();
    unknown.tracks[0].cues[0].fallback_capability_ids[0] =
        CapabilityId::new("missing-capability").unwrap();
    unknown.recompute_score_id().unwrap();
    assert_eq!(
        unknown
            .validate_against_manifest(&manifest)
            .unwrap_err()
            .code,
        ScoreErrorCode::UnknownCapability
    );

    let showcase = manifest
        .capabilities
        .iter()
        .find(|entry| entry.status == CapabilityStatus::ShowcaseOnly)
        .unwrap();
    let mut inactive = bound.clone();
    inactive.tracks[0].cues[0].fallback_capability_ids[0] =
        CapabilityId::new(showcase.id.clone()).unwrap();
    inactive.recompute_score_id().unwrap();
    assert_eq!(
        inactive
            .validate_against_manifest(&manifest)
            .unwrap_err()
            .code,
        ScoreErrorCode::InactiveCapability
    );

    let under_quality = manifest
        .capabilities
        .iter()
        .find(|entry| {
            entry.status == CapabilityStatus::ActiveLegacy
                && entry.quality_status == QualityStatusV1::RuntimeActiveUnscored
        })
        .unwrap();
    let mut weak = bound.clone();
    weak.tracks[0].cues[0].fallback_capability_ids[0] =
        CapabilityId::new(under_quality.id.clone()).unwrap();
    weak.recompute_score_id().unwrap();
    assert_eq!(
        weak.validate_against_manifest(&manifest).unwrap_err().code,
        ScoreErrorCode::UnderQualityCapability
    );

    let incompatible_capability = manifest
        .capabilities
        .iter()
        .find(|entry| {
            entry.status == CapabilityStatus::ActiveLegacy
                && entry.quality_status == QualityStatusV1::RuntimeRendered
        })
        .unwrap();
    let mut incompatible = bound;
    incompatible.tracks[0].cues[0].fallback_capability_ids[0] =
        CapabilityId::new(incompatible_capability.id.clone()).unwrap();
    incompatible.recompute_score_id().unwrap();
    assert_eq!(
        incompatible
            .validate_against_manifest(&manifest)
            .unwrap_err()
            .code,
        ScoreErrorCode::IncompatibleCapability
    );
}

#[test]
fn score_hash_changes_for_material_bytes_and_omits_only_score_id() {
    let original = fixture_score();
    let body = original.canonical_body_json().unwrap();

    let mut changed = original.clone();
    changed.header.seed = 1;
    changed.recompute_score_id().unwrap();
    assert_ne!(changed.header.score_id, original.header.score_id);
    assert_ne!(changed.canonical_body_json().unwrap(), body);

    let mut score_id_only = original;
    score_id_only.header.score_id = Sha256Hex::new("f".repeat(64)).unwrap();
    assert_eq!(score_id_only.canonical_body_json().unwrap(), body);
    assert_eq!(
        score_id_only.validate().unwrap_err().code,
        ScoreErrorCode::InvalidScoreHash
    );
}
