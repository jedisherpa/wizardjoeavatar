# V1 Listening Candidate `6c2767a` Machine Review

Date: 2026-07-18  
Decision: **Rejected before human review**

## Candidate

- Source commit: `6c2767a53189b07f6cd9b12d73a4b41dc4b9c65d`
- Evidence: `evidence/character-director/v1-listening-6c2767a-2026-07-18/`
- Manifest SHA-256: `85977b432f5ce28057464efc93cb73fcb9058556a78fad2ccd855919a0256294`
- Review-bundle SHA-256: `e857776887e1cbeef94c298088b068a0eb21e3c034fb6b3f54b1aa2a045b7cb5`
- Machine-report SHA-256: `f6fb60811c06d8f2c0924ac94cd578e7e658070bef3c599b15d6e00d5189d480`
- Normal-speed video SHA-256: `2eb5ce9ade9f6822ccd6d1aea34c3b7e1f2a6009a6cf909bd65c7cf237349505`
- Quarter-speed video SHA-256: `c1264f9e39a5ce8437d361edb2c34e713ef32131fe21f82af48c0b6c9492f813`

## Passing Evidence

- 288 of 288 scenario-owned frames, indexed 0 through 287.
- Zero dropped frames, decode gaps, queue overruns, or unowned frames.
- Runtime/source binding verified from a clean worktree.
- Queue high-water mark 1 of 16.
- Contact verifier passed all 288 frames with one stance and zero planted,
  raster, or root-residual drift.
- Turn facings: `south`, `southwest`, `west`.
- Head views: `front_idle`, `walk_front_left`, `profile_left` while the body
  remained `front_idle`.
- Turn phases: `leading`, `turning`, `settling`, `steady`.
- Twelve unique presented frame hashes.

## Rejection

`two_blinks_with_bounded_closure` failed. The measured closures were 125 ms,
83.333 ms, and 166.667 ms. The turn blink is below the canonical 100-200 ms
closure range. This candidate is retained as negative evidence and must not be
submitted for animation or technical acceptance.

## Required Correction

Increase the deterministic turn-blink closure by one simulation tick, rerun the
focused timing tests, seal a new clean source commit, and capture a new bundle.
Do not weaken the 100-200 ms acceptance interval.
