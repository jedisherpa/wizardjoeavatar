# Wizard Joe Prerecorded Audio Performance V1

## Scope

The review program covers all 95 MP3 files in the corrected Wizard Joe voice
package. Each clip has deterministic choreography, an audio-derived speech
envelope, semantic body cues, accent-timed motion beats, and an explicit human
review decision. Locomotion is authored per clip instead of being imposed on
every performance.

Run the local reviewer:

```bash
python3 tools/run_character_observer.py \
  --port 8655 \
  --joe-port 8656 \
  --performance-review-manifest \
  assets/reference/characters/wizard-joe/audio-performances-v1/manifest.json \
  --joe-sequence approved_hd_frames \
  --joe-meta "250 approved HD poses + full-frame mouth review"
```

Open `http://127.0.0.1:8655/`.

## Mouth-State Contract

`mouth-state-ledger.json` records the canonical mouth state for each of the 250
approved HD postures:

- 184 canonical open mouths
- 61 canonical closed mouths
- 5 rear-facing postures where the mouth is not visible
- 0 unresolved postures

The V2 `mouth-pair-manifest.json` maps every approved posture to both `open` and
`closed`. Nine performance-critical postures use complete 1254 by 1254 frame
alternates with transparent backgrounds. These are whole authored frames, not
mouth patches. Remaining postures retain the V1 review candidates until their
full-frame alternates pass the same visual gate. The five rear-facing variants
are byte-identical aliases because no mouth is visible.

The canonical approved library remains unchanged. The local reviewer uses
`assets/reference/wizard-joe-mouth-full-frame-review-library-index.json`, a
review-only, non-runtime-admitted index that layers the complementary candidates
over the canonical library.

The V2 full-frame sources and processed alphas live under
`assets/reference/characters/wizard-joe/mouth-pairs-full-frame-v2/`. Frames that
already match the canonical 1254 by 1254 canvas are never normalized from their
silhouette bounds; this preserves authored scale and registration between mouth
states.

## Playback Rules

- The HTML audio clock is authoritative.
- `WJ_INTRO_001` flies toward the camera from a distant first word, brakes, and
  arrives in a centered hover on its final word.
- `WJ_INTRO_002` remains in a flying hover while alternating restrained
  explanatory hand gestures.
- Other clips use their authored locomotion and performance styles.
- Body changes occur on audio accents and remain at least 950 ms apart.
- Adjacent motion beats may not repeat the same posture.
- Quiet envelope windows close the mouth.
- Vocal windows blend complete open and closed frames through short transition
  windows. The projector never overlays a cropped mouth patch.
- A pose without a complete pair would fall back to canonical art. Current
  approved-pose coverage is 250 of 250.

## Verification

Rebuild the corpus and mouth candidates:

```bash
python3 tools/import_wizard_joe_audio_performances.py
python3 tools/audit_wizard_joe_hd_mouth_states.py
python3 tools/build_wizard_joe_hd_mouth_pairs.py
python3 tools/build_wizard_joe_full_frame_mouth_pairs.py
python3 tools/audit_wizard_joe_audio_performances.py \
  --mouth-pairs \
  assets/reference/characters/wizard-joe/mouth-pairs-full-frame-v2/mouth-pair-manifest.json \
  --library-index \
  assets/reference/wizard-joe-mouth-full-frame-review-library-index.json
```

The generated `performance-audit.json` contains one result per clip for audio
integrity, continuous cue coverage, pose validity, motion spacing, adjacent
repetition, and mouth-pair coverage.

Automated passage does not approve choreography or admit assets to production.
Use the reviewer’s `Needs changes` and `Approve choreography` controls to record
the visual gate in `review-state.json`.
