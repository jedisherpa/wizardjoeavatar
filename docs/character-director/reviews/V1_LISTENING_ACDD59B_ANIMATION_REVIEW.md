# Character Director V1 Listening Review

**Reviewer:** Reviewer A, supervising animation director and acting coach  
**Decision:** **REJECT V1**  
**Scope:** V1 listening only. No judgment is made about V2-V10 or overall release quality.

## Evidence Binding

- Candidate runtime commit: `acdd59bd3e26e9730735c8169116f23d6bc8bca9`
- Candidate tree: `2465f9d48abfd1cdd4cb71971fdb5d5b034d5a57`
- Manifest SHA-256: `2371dc8a7ccbc300f20aa23d6955c07b0f66eefaf9e28f405684642562c48a4e`
- The supplied manifest hash matches.
- All 59 manifest-listed artifacts match their recorded hashes.
- Manifest runtime identity at capture start and end identifies the candidate commit and a clean worktree.
- Normal capture: H.264, 960x540, 24 FPS, 290 frames, 12.083 seconds.
- Quarter-speed derivative: 1160 frames, 48.333 seconds, SHA-256 `57933a953f01968768fc7647b96794a90e3a35d53d197d143c41257a07bb5d08`.
- Machine report SHA-256: `913c7aad3ca3b269d681d732c482a1ee308e3a7ecc6ada8513b95cd689222371`.

The quarter-speed video and machine report are not listed in the manifest's artifact table. I treated them as review aids, not independently manifest-bound evidence.

## Scores

| Applicable category | Weight | Score | Director finding |
|---|---:|---:|---|
| Gaze and head-eye coordination | 12 | **2/4** | Fixations are legible and timely, but the turn reads as a rapid pose switch through a walking silhouette rather than directed head-eye acting. |
| Blink | 8 | **1/4** | Two channel closures are recorded, but only the first changes visible pixels. The required second blink is not presented to the viewer. |
| Stillness | 10 | **2/4** | Root stability is excellent, but prolonged pixel-identical holds read as frozen playback. The turn also inserts an unrelated whole-body walking pose. |
| Framing | 10 | **4/4** | Strong margins, no crop or overlap, grounded feet, and readable front/profile silhouettes. |

Applicable weighted result: **23/40, normalized to 57.5/100**. This normalization is informational and is not a full-matrix release score.

Hand acting, locomotion, interruption, reduced motion, and repetition are not scored because V1 does not exercise their prescribed scenario contracts.

## Frame-Specific Findings

| Trace frame | MP4 time | Finding |
|---:|---:|---|
| 474-533 | 0.000-2.458 s | Viewer fixation. All 60 frames have one identical presented-frame hash. Clear but inert. |
| 534 | 2.500 s | Left gaze appears on the first captured target frame, about 30 ms after command acknowledgment. Pupils remain visually inside the apertures. |
| 539-541 | 2.708-2.792 s | First blink is visibly closed for three frames, 125 ms. Timing is natural and root/body pixels remain stable. |
| 542-594 | 2.833-5.000 s | Left fixation resumes and remains pixel-identical. Target is clear, but there is no residual settle or attentive modulation. |
| 595 | 5.042 s | Viewer return appears on the first captured return frame, again about 30 ms after acknowledgment. |
| 656 | 7.583 s | Gaze authority releases without a visible discontinuity. |
| 663 | 7.875 s | One-frame eye lead toward screen left. This satisfies the numeric 1-4-frame lead requirement at its minimum. |
| 664 | 7.917 s | Head follow is represented by `walk_front_left`: the entire robe, feet, wings, arms, and staff relationship change into a walking/stepping silhouette. This is not a convincing stationary head turn. |
| 665 | 7.958 s | Full profile appears immediately and is marked `settling`. |
| 666 | 8.000 s | Profile becomes `steady`. There is no visible ease, counteraction, overshoot, or settle beyond the state change. |
| 687-690 | 8.875-9.000 s | Trace records a four-frame, 166.667 ms second blink. The presented-frame SHA-256 remains identical to surrounding open-eye frames, and extracted video frames show no visible closure. |
| 691-763 | 9.042-12.042 s | Profile hold remains exactly pixel-identical through the end. The endpoint silhouette is clean, but listening presence is absent. |

Only **five unique presented-frame hashes** occur across all 290 frames. Quarter speed confirms that the intermediary is a held walking pose, not additional turn articulation.

## Contract Assessment

- **12-second order:** Pass. Viewer, left target, viewer, release, then west turn are correctly ordered.
- **Gaze latency/order:** Pass technically. Each target response is visible on the first captured frame after acknowledgment.
- **Eye bounds:** No visible aperture escape, but the package supplies no explicit eye-bound measurement. The machine report checks gaze values, not geometric eye containment.
- **Blink duration/interval:** Channel timing passes: 125 ms and 166.667 ms, with approximately 6.167 seconds between onsets.
- **Two visible blinks:** **Fail.** Only one blink reaches presented pixels.
- **Root stability:** Pass. Trace root span and contact report residual are zero. The contact report's `stance_count` is zero, however, limiting its stance-specific evidentiary value.
- **Eye lead/head follow/settle:** **Fail director review.** The labels occur in order, but the visible motion is too compressed and uses a whole-body locomotion pose.
- **Listening presence:** **Fail.** The performance communicates commanded states, not an attentive character processing an unseen speaker.
- **Silhouette/framing:** Pass.

## Evidence Limitations

1. The contact sheet labels show run/sample, scenario, and frame, but omit tick, time, command, state hash, and frame hash required by the acceptance document.
2. Required geometric eye-bound measurements are absent.
3. The quarter-speed derivative and machine report are outside the manifest artifact inventory.
4. No separate real-browser layout recording is included in this package.
5. This is one reviewer record; it cannot satisfy the two-independent-reviewer release gate.
6. The package is external and untracked at the candidate worktree, so its commit binding rests on the verified manifest and runtime identity rather than Git containment.

## V1 Decision

**Reject V1.** Provenance, duration, command order, root stability, basic fixation, and framing are credible. Acceptance is blocked by the invisible second blink, the full-body walking-pose substitution for a directed head turn, frozen listening holds, missing eye-bound evidence, and incomplete contact-sheet attribution.
