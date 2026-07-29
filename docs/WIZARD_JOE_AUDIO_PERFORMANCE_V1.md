# Wizard Joe Prerecorded Audio Performance V1

## Scope

The review program covers all 95 MP3 files in the corrected Wizard Joe voice
package. Each clip has deterministic choreography, an audio-derived speech
envelope, a walk-toward-camera entrance, semantic body cues, accent-timed motion
beats, and an explicit human review decision.

Run the local reviewer:

```bash
python3 tools/run_character_observer.py \
  --port 8655 \
  --joe-port 8656 \
  --performance-review-manifest \
  assets/reference/characters/wizard-joe/audio-performances-v1/manifest.json
```

Open `http://127.0.0.1:8655/`.

## Mouth-State Contract

`mouth-state-ledger.json` records the canonical mouth state for each of the 250
approved HD postures:

- 184 canonical open mouths
- 61 canonical closed mouths
- 5 rear-facing postures where the mouth is not visible
- 0 unresolved postures

`mouth-pair-manifest.json` maps every approved posture to both `open` and
`closed`. Derived variants alter only the recorded articulation region. The five
rear-facing variants are byte-identical aliases because no mouth is visible.

The canonical approved library remains unchanged. The local reviewer uses
`assets/reference/wizard-joe-mouth-review-library-index.json`, a review-only,
non-runtime-admitted index that layers the 250 complementary mouth candidates
over the canonical library.

## Playback Rules

- The HTML audio clock is authoritative.
- Joe approaches the camera using the authored front-walk cycle.
- Body changes occur on audio accents and remain at least 950 ms apart.
- Adjacent motion beats may not repeat the same posture.
- Quiet envelope windows close the mouth.
- Vocal windows use a restrained 170 ms open/closed cadence.
- A pose without a complete pair would fall back to canonical art. Current
  approved-pose coverage is 250 of 250.

## Verification

Rebuild the corpus and mouth candidates:

```bash
python3 tools/import_wizard_joe_audio_performances.py
python3 tools/audit_wizard_joe_hd_mouth_states.py
python3 tools/build_wizard_joe_hd_mouth_pairs.py
python3 tools/audit_wizard_joe_audio_performances.py
```

The generated `performance-audit.json` contains one result per clip for audio
integrity, continuous cue coverage, pose validity, motion spacing, adjacent
repetition, and mouth-pair coverage.

Automated passage does not approve choreography or admit assets to production.
Use the reviewer’s `Needs changes` and `Approve choreography` controls to record
the visual gate in `review-state.json`.
