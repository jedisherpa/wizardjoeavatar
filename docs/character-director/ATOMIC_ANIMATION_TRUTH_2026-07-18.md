# Atomic Animation Truth And Contact-Lock Receipt

Date: 2026-07-18

Candidate: `b7b6101c86b6abd04622935331684b76e3ce8591` on
`codex/character-director`

## Implemented

- Each accepted presentation frame now carries one immutable
  `animation_truth_trace_v1` record with exact authored sample/frame indices,
  markers, contact generation, root transform, staff/effect geometry, frame
  hashes, and transport metadata.
- Stale render candidates cannot append trace records or advance presentation
  contact state.
- Connect and resync request the next globally committed keyframe. They no
  longer synthesize a subscriber-only codec truth for an existing frame index.
- Grounded contact-locked samples preserve one transformed planted anchor.
  Contact correction is committed in the same accepted presentation
  transaction as the pixels.
- Horizontal reversal remains in the front-walk family. Authored left/right
  stop clips provide braking, transfer, both-foot settle, and recoverable
  markers before idle.
- Cast timing is marker-owned. Effect onset/recovery follows authored frames
  and the current staff tip; committed casts complete recovery; the final
  `action_settled` sample is held on screen before the action retires.

## Automated Verification

- Full Python discovery: 517/517 passing in 289.669 seconds.
- Focused lifecycle suite: 7/7 passing after the final lease rule.
- Production-scope validator: 67 files scanned, zero violations.
- `git diff --check`: pass before the candidate commit.

## Clean External Capture

The clean candidate was launched on isolated port 8875. Legacy port 8765 was
not restarted or replaced.

Evidence directory:
`evidence/character-director/atomic-contact-lock-b7b6101-2026-07-18/`

- 340 contiguous 24 FPS frames, indices 0-339.
- Zero dropped frames.
- Exact trace record for every captured frame.
- 302 grounded contact frames across 13 contact generations.
- Maximum planted-anchor drift:
  `1.4210854715202004e-14` output cells.
- Maximum unexplained root residual: `0.0` output cells.
- Contact verification: pass with zero issues.
- Worktree provenance at capture: clean.

Artifact hashes:

| Artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `687cb9319c3b5f595e11b559ded9e10ee18dbba42dc1c1caf32521eddeed7c17` |
| H.264 capture | `f19e98279a0e10e5ece944aa9181c1198e611e8d7c09e67f256585956ecee19f` |
| Contact sheet | `3456fd08c56657cbdd2c820168f9ea9a1db82a328c21fbb365efcea179a8ac96` |
| Atomic trace | `ad232627872e2a5982691b9969a648a137cf806e8c1c5f2a9c8f5d1ff97df537` |
| Contact report | `db88ed1444a510b113a960fa945b421f0f27939772d9b20b35785c75aa20efce` |

## Scope Of This Receipt

This package proves the implementation and external rendering path for front
idle, two gaze changes, two expressions, front walking, horizontal reversal,
authored stop, front/back facing, one cast, speech, and speech interruption.
It is not the complete V1-V10 acceptance package.

## Independent Review

Two independent reviewers examined the immutable package against
`VISUAL_PERFORMANCE_ACCEPTANCE_2026-07-17.md`:

- Supervising animation director: 41/100, reject for visual-performance
  release.
- Animation systems / production verification: 42/100, request changes.

They accepted the package as useful engineering evidence, not release proof.
The shared correction ledger is:

1. Bind the external runtime process/executable/configuration to the candidate
   commit rather than recording only the harness checkout.
2. Verify visible decoded raster contact and support alternation, not only the
   continuous anchor coordinates emitted by the same transform.
3. Preserve authored marker events until at least one 24 FPS presentation
   record can carry them.
4. Remove the remaining subscriber-local overflow keyframe path or represent
   every delivered transport truth explicitly.
5. Replace the idle reset inside the walk cycle, add reversal anticipation,
   remove the unmotivated profile tail from stop, and author staff/hand
   in-betweens for cast.
6. Execute the complete V1-V10 matrix with browser, audio, quarter-speed,
   accessibility, duration, DPR, and mobile evidence.

Reports:

- `reviews/ATOMIC_CONTACT_LOCK_B7B6101_ANIMATION_REVIEW.md`
- `reviews/ATOMIC_CONTACT_LOCK_B7B6101_TECHNICAL_REVIEW.md`

Still required:

- V1 long listening/blink sequence.
- V2 real governed speech with audible AV timing.
- V3 three-cast repetition review.
- V4 thought-group explain/hold/point performance.
- V7 visual pre-commit and post-commit interruption variants.
- V8 60-second repetition/stillness review.
- V9 full/reduced/still comparison.
- V10 desktop/mobile DPR and edge-composition matrix.
- Real PrismGT audio evidence, eight-hour and 24-hour V2 soaks, and an
  independent clean-user package/rollback run.
