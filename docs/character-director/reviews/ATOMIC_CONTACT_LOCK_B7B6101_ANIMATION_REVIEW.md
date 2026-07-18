# Atomic Contact Lock B7B6101 Animation Review

## Review Identity

- Reviewer role: independent supervising animation director
- Review basis: visual performance and motion judgment; machine validity is supporting evidence, not aesthetic proof
- Acceptance contract: `docs/character-director/VISUAL_PERFORMANCE_ACCEPTANCE_2026-07-17.md`
- Candidate branch: `codex/character-director`
- Exact candidate: `b7b6101c86b6abd04622935331684b76e3ce8591`
- Evidence package: `evidence/character-director/atomic-contact-lock-b7b6101-2026-07-18`
- Manifest SHA-256: `687cb9319c3b5f595e11b559ded9e10ee18dbba42dc1c1caf32521eddeed7c17`
- Capture: `visual-review-e68d0dc840a8-capture.mp4`, SHA-256 `f19e98279a0e10e5ece944aa9181c1198e611e8d7c09e67f256585956ecee19f`
- Contact sheet SHA-256: `3456fd08c56657cbdd2c820168f9ea9a1db82a328c21fbb365efcea179a8ac96`
- Animation trace SHA-256: `ad232627872e2a5982691b9969a648a137cf806e8c1c5f2a9c8f5d1ff97df537`
- Contact verification SHA-256: `db88ed1444a510b113a960fa945b421f0f27939772d9b20b35785c75aa20efce`

## Decision

**Release recommendation: REJECT for visual-performance release. Retain as valid engineering evidence for atomic trace pairing and contact lock.**

The package is a clean, attributable 340-frame capture at 24 FPS. It proves a meaningful contact-lock improvement, but it does not meet the aesthetic bar or the required V1-V10 release matrix. The observed performance remains a sequence of held full-pose substitutions rather than a polished continuous character performance.

## Scores

| Category | Score (0-4) | Weighted | Evidence-grounded judgment |
| --- | ---: | ---: | --- |
| Gaze and head-eye coordination | 2 | 6.0/12 | Left/right eye changes are readable, but there is no required 90-degree head-turn performance, eye-lead timing proof, or convincing head-eye settle. |
| Blink | 0 | 0.0/8 | No qualifying blink sequence or interval evidence is present. |
| Hand acting | 1 | 3.5/14 | The cast idea reads, but the staff/hand changes pop. Staff-tip motion jumps about 66 cells at frame 252, 65 at 257, 34 at 258, and 24 at later recovery changes; recovery is only frames 262-263 before the frame-264 idle snap. |
| Locomotion | 2 | 9.0/18 | Contact is locked and feet alternate, but weight and continuity are repeatedly distracting. Full silhouettes swap between walk poses and `front_idle`; reversal has no anticipation or directional reorganization; stop resolves through an unmotivated profile turn. |
| Stillness | 2 | 5.0/10 | Frames 281-315 are stable during speech, but the body reads closer to frozen playback than active listening/speaking. The required 20-second governed performance and two-second conclusion hold are absent. |
| Interruption | 2 | 5.0/10 | The simple speech stop at frame 316 closes without a root jump or stale body action. The required pre-commit and post-commit cast interruptions are not demonstrated. |
| Reduced motion | 0 | 0.0/8 | Full/reduced/still comparison is absent. |
| Framing | 3 | 7.5/10 | This 960x540 render is uncropped, crisp, and clear of overlap. The character is undersized for performance review, and desktop DPR/mobile edge-pass evidence is absent. |
| Repetition | 2 | 5.0/10 | The short capture cannot prove the 60-second gate. The visible locomotion cadence already repeats the same four full-pose holds mechanically. |
| **Total** |  | **41.0/100** | Below 85; six categories are below the required minimum of 3. |

## Blocking Findings

1. **The release evidence matrix is incomplete.** This 14.17-second diagnostic reel does not provide V1-V10, quarter-speed review, real-browser capture, synchronized audio, three spaced casts, cast interruption before/after commit, 60-second repetition review, motion-profile comparison, or desktop/mobile DPR passes. Missing required review evidence is a hard failure under the contract.
2. **Locomotion still pops between incompatible whole-body drawings.** During walk and reversal, the trace switches through `walk_front_left`, `front_idle`, `walk_front_right`, and `walk_front_right_lift` as held blocks. Examples are frames 113-118, 119-121, 122-126, and 127-130. The upright idle insertion reads as a reset inside the stride, not a passing position.
3. **Reversal lacks anticipation and weight.** Frames 142-190 continue the same front-walk loop after direction changes. The result reads as the stage trajectory reversing under an unchanged cadence rather than the character catching weight, redirecting the pelvis, and pushing into the new direction.
4. **The walk stop changes intention after stopping.** Frames 198-206 brake through walk/idle poses, then frames 207-211 rotate into `profile_right`. That turn is not motivated by the stop command and prevents a clean travel-facing settle.
5. **Cast hand/staff continuity is far outside tolerance.** The staff tip moves from approximately `(101.2, 33.4)` to `(163.6, 54.8)` at frame 252, then to `(99.9, 67.2)` at frame 257. Subsequent hold/recovery changes also jump by tens of cells. The prepare/stroke/hold idea is legible, but it plays as pose replacement. Frames 262-263 provide only two captured recovery frames before snapping to idle at 264, below the three-frame minimum.

## Nonblocking Strengths

- The contact verifier reports 13 stances, zero issues, maximum planted drift of approximately `1.4e-14` cells, and zero root residual. No visible skating was found while a contact was declared planted.
- Individual key-pose silhouettes are colorful, appealing, and readable. The wings, robe, face, and staff remain identifiable at this scale.
- The cast has a clear broad shape: guarded preparation, forceful stroke, magical hold, and attempted recovery. The staging idea is worth preserving while continuity is rebuilt.
- The simple speech interruption is spatially stable, and the square-cell projection remains crisp.

## Remaining Limits

This review does not infer quality outside the immutable package. It cannot approve blink behavior, AV sync, long-form speech acting, reduced/still motion, repeated-cast consistency, cast interruption recovery, browser layout, mobile framing, or repetition fatigue. A new evidence package should first correct the locomotion passing poses, authored stop settle, and staff/hand arcs, then execute the complete V1-V10 matrix with the same atomic trace/contact provenance.
