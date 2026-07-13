# Rust Chatbot Visualizer Implementation Plan

Plan ID: `RCHAT-INT`

Coordinator: `INT`

Status: active

## 1. Outcome

Deliver a Rust-native Wizard Joe visualizer that performs a conversation rather
than cycling poses. It must visibly and naturally listen, think, prepare,
speak, clarify, wait for tools, recover from interruption, acknowledge errors,
and celebrate. It must use the full 89-geometry library through intentional
performance paths while preserving coherent square-cell silhouettes, planted
contacts, staff and wing attachment, facial identity, deterministic timing,
and repeatable replay.

## 2. Target architecture

```text
chatbot / TTS / browser / automation
    -> ChatEventEnvelopeV1 and CommandEnvelopeV1
    -> validated, bounded, idempotent Rust inbox
    -> exact 60 Hz AvatarRuntime
    -> orthogonal semantic state regions
    -> deterministic performance director
    -> authored motion graph and transition recipes
    -> speech visemes + gaze + blink + emotion + secondary motion
    -> immutable cell snapshot
    -> ASCILINE adaptive codec and Axum hub
    -> atomic browser presentation and causal diagnostics
```

The browser is a presenter and semantic input client. It does not choose poses,
advance animation, repair frames, or load source images.

## 3. Frozen contracts

### Canonical chat states

`idle`, `listening`, `thinking`, `preparing_response`, `speaking`,
`clarifying`, `tool_wait`, `error`, `celebrating`, and `interrupted`.

These ten values supersede the shorter enum sketches in the specialist plans.
They map ingress, runtime state, and motion performance as follows:

| Semantic event | Conversation region | Performance state |
|---|---|---|
| session ready / turn settled | `idle` | `idle` |
| `user_turn_started` | `listening` | `listening` |
| `assistant_thinking_started` | `thinking` | `thinking` |
| `assistant_response_planned` | `preparing_response` | `preparing_response` |
| `speech_started` / active | `speaking` | `speaking` |
| `clarification_requested` | `clarifying` | `clarifying` |
| `tool_wait_started` | `tool_wait` | `tool_wait` |
| `assistant_error` | `error` | `error` |
| `celebration_requested` | `celebrating` | `celebrating` |
| higher-priority turn or cancellation | `interrupted` | `interrupted`, then `listening` |

`tool_wait_ended`, `speech_completed`, and recovery markers settle into the
next explicit event state or `idle`. No adapter infers private model state.

### Orthogonal channels

`conversation`, `mobility`, `pose`, `gesture`, `face`, `gaze`, `blink`,
`mouth`, `speech`, `staff`, `wings`, `secondary_motion`, `effects`, and
`control`.

Every channel has an owner, priority, generation, entered tick, optional
deadline, and restoration policy. A writer may alter only its declared region
mask. Replacement starts from the presented state and reaches a safe recovery
marker before relinquishing owned regions unless an emergency stop requires an
immediate coherent home pose.

| Channel | Authoritative region |
|---|---|
| conversation | `ConversationRegion` |
| mobility | `MobilityRegion` |
| pose | `PoseRegion` |
| gesture | `GestureRegion` |
| face, gaze, blink | `FaceRegion` |
| mouth | `MouthRegion` |
| speech | `SpeechRegion` |
| staff | `StaffRegion` |
| wings | `WingRegion` |
| secondary motion | bounded substate owned by pose/staff/wings/face |
| effects | `EffectsRegion` |
| control | `ControlRegion` |

### Speech

Speech lifecycle is `prepared`, `started`, `paused`, `resumed`, `cancelled`,
`completed`, or `failed`. Timed TTS visemes are authoritative. The canonical
semantic set is `Rest`, `MBP`, `FV`, `TH`, `DTLN`, `KG`, `CHSH`, `SZ`, `R`,
`A`, `E`, `I`, `O`, and `U`. MOTION's smaller visual vocabulary is named
`RenderedMouthPose` and maps those 14 values to the existing seven cell-art
mouth shapes.

```rust
pub enum RenderedMouthPose {
    Closed,
    OpenSmall,
    OpenMedium,
    OpenWide,
    Rounded,
    Smile,
    Frown,
}
```

| Semantic viseme | Rendered mouth pose |
|---|---|
| `Rest`, `MBP` | `Closed` |
| `FV`, `TH`, `DTLN`, `SZ` | `OpenSmall` |
| `KG`, `CHSH` | `OpenMedium` |
| `A` | `OpenWide` |
| `R`, `O`, `U` | `Rounded` |
| `E`, `I` | `Smile` |

`Frown` is an emotion/rest pose and never changes phoneme identity. The
compatibility boundary is one exhaustive
`impl From<RenderedMouthPose> for MouthShape`; legacy `MouthShape` is a state
projection, not the semantic speech contract.

Production animation does not receive or infer from private response text. If
timed cues are absent, `SpeechPlanV1` must include a duration and uses a
low-confidence deterministic duration envelope seeded by utterance ID. That
fallback animates readable open/rest cadence without claiming phonetic
accuracy. Adding text-derived phonemes later requires a new opt-in schema,
privacy review, and contract version.

### Motion selection

Chat clients cannot send raw pose IDs. The director scores authored behaviors
by semantic match, emotion, conversational state, contact compatibility,
channel conflicts, transition cost, cooldown, repetition, and deterministic
seed. Ties resolve by stable ID. Extreme gestures have cooldowns and always
recover through authored paths.

## 4. Accountable DAG

Only `ACCEPTED` work earns progress. Detailed lane subtasks and thresholds are
defined by the three specialist plans; `registry.json` is the live authority.

```text
RCHAT-FLOW-001  immutable pose checkpoint P0
  -> FLOW-010  planning checkpoint D0
      -> FLOW-020 registry/gate validators
      -> FLOW-030 aggregate contract freeze C0
           requires RCHAT-RUN-010 and RCHAT-ANIM-010..019
          -> FLOW-040 runtime child ledger RUN-010..100
          -> FLOW-050 motion child ledger ANIM-020..135
          -> FLOW-060 CI/evidence/browser harness foundation
              -> FLOW-070 runtime hotspot integration
                  -> FLOW-080 motion hotspot integration
                      -> FLOW-090 transport/browser integration
                          -> FLOW-100 deterministic and compatibility QA
                              -> FLOW-110 every-frame visual QA
                                  -> FLOW-120 real Chromium QA
                                      -> FLOW-130 soak/performance
                                          -> FLOW-140 clean-clone release
                                              -> FLOW-150 final manifest
                                                  -> FLOW-160 push exact SHA
                                                      -> FLOW-170 deploy SHA
                                                          -> FLOW-180 endpoint/rollback drill
                                                              -> FLOW-190 independent acceptance
```

The registry preserves every specialist work ID exactly. FLOW parent items earn
no progress until every listed RUNTIME or MOTION child is accepted. Shared
policy is split by ownership: RUNTIME owns semantic scoring and arbitration;
MOTION owns graph resolution and visual recovery recipes; INT alone wires them.

## 5. Execution waves

### Wave P0: immutable prerequisite

Record the 89/50/621/16 baseline, both identical 20,065-frame streams, asset
hash, tests, evidence manifests, commit SHA, and pushed ref. Freeze the v4 asset
for the chatbot pass.

### Wave C0: contracts and registries

In parallel, RUNTIME implements strict serde contracts and invalid fixtures;
MOTION authors the taxonomy, behavior vocabulary, markers, masks, and graph
schema; FLOW implements Rust-compatible registry and gate validation. The
coordinator cross-reviews and freezes all shared meanings before runtime wiring.

### Wave R1: parallel engines

RUNTIME builds integer timing, ordering, dedupe, state regions, speech,
visemes, replay, and metrics. MOTION builds the graph, director data, face/gaze,
blink policy, secondary constraints, transition recipes, reduced motion, and
focused animation tests. FLOW builds evidence schemas, scope checks, CI, and
browser scenario definitions.

### Wave I1: serial integration

The coordinator wires modules in this order: runtime clock/inbox, semantic
state projection, performance director, speech and facial channels, motion
graph, controller/playback, renderer, hub/server, browser. Every hotspot change
must pass focused and existing regression tests before the next integration.

### Wave Q1: exhaustive verification

Run contract fixtures, all graph edges, loops, interruptions, speech timing,
channel ownership, reduced motion, replay, decode/presentation parity, static
89-pose census, 621 existing transition regressions, and the new chatbot
scenario matrix. Produce one numbered PNG and one ledger row per acceptance
frame, then repeat the deterministic render and compare hashes.

### Wave Q2: browser and soak

Use real Chromium against port 8787 for every chat state, rapid interruption,
speech cancellation, reconnect, resync, Stop, reduced motion, multiclient
fanout, and diagnostics. Require zero console errors and exact source/decode/
presented hashes. Run performance profiles and a ten-minute mixed-state soak.

### Wave F0: release

Build from a clean clone of the immutable pushed SHA. Record binary, asset,
graph, policy, browser, and evidence hashes. Deploy that SHA to the isolated
Hetzner service, verify the public endpoint reports the same identity, perform
a rollback and re-promotion drill, and retain the receipt.

## 6. Acceptance gates

| Gate | Blocking acceptance |
|---|---|
| `P0` | 89/50/621/16; 89 static; 20,065 x2 identical; zero failures; pushed SHA |
| `C0` | strict schemas; invalid fixtures reject; no raw production pose field |
| `R1` | exact ticks; deterministic ordering; duplicate/stale/TTL rules; immutable snapshots |
| `A1` | all geometries classified; all 50 WJFL reachable intentionally; graph, speech/face, and recovery behavior valid |
| `R1` | speech lifecycle, viseme timing, cancellation-to-rest, chat state, priority, and arbitration deterministic |
| `I1` | legacy APIs still pass; new route/WS acks; one runtime authority |
| `Q1` | every graph edge and acceptance frame passes structural checks twice |
| `Q2` | real-browser parity, reconnect, multiclient, Stop, reduced motion, soak pass |
| `F0` | clean SHA, all checks, independent score >=90%, rollback and endpoint proof |

The canonical gate namespace is `P0`, `D0`, `C0`, `R1`, `A1`, `Q0`, `I1`,
`I2`, `T1`, `Q1`, `Q2`, `Q3`, `S1`, `R0`, and `F0`. Granular specialist
subgates such as runtime `R2`, `R3`, `B1..B3`, `D1`, and `O1` are evidence
labels aggregated into `R1`; they are not independent promotion gates.

Automatic failure conditions include a missing pose, broken topology, detached
staff/wing, planted-contact violation, nondeterminism, missing terminal ack,
runtime PNG access, raw-pose chatbot ingress, browser console error,
decode/presentation mismatch, stale deployed SHA, or skipped behavioral test.

## 7. Scorecard

Structural gates are binary and must all pass. The independent product score is
weighted separately:

| Dimension | Weight |
|---|---:|
| Conversational readability and appropriateness | 20 |
| Motion continuity, weight, and interruption recovery | 20 |
| Speech, facial acting, gaze, blink, and coarticulation | 15 |
| Pose coverage and authored transition quality | 15 |
| Determinism, replay, transport, and browser parity | 15 |
| Accessibility, Stop, reduced motion, and resilience | 10 |
| Performance, deployment, rollback, and observability | 5 |

Final acceptance requires at least 90/100 and no structural blocker.

## 8. Rollback

Runtime profiles are `legacy`, `chatbot_shadow`, and `chatbot_default`.
Legacy clips remain available until F0. Each family is promoted independently:
contracts, runtime, speech/face, graph, chatbot policy, browser, deployment. A
failure returns only the affected family to its previous accepted profile,
records the exact event/tick/frame and hash, reopens the responsible work item,
and blocks later promotion.

## 9. Definition of done

The program is done only when every registry item is `ACCEPTED`, all structural
gates pass, the independent score is at least 90, the final manifests contain
no skipped behavioral checks, the branch is pushed, the public endpoint serves
the exact accepted Rust build, and rollback plus re-promotion have been proved.
