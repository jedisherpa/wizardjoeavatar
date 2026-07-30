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
states. Generated mouth art is registered at build time by transferring only
the reviewed mouth region onto the complete canonical frame. The builder rejects
any candidate whose outer alpha bounds differ from canonical or whose pixels
outside the mouth region are not byte-identical to canonical. Runtime playback
still swaps complete frames; it never composites a mouth patch.

## Playback Rules

- The HTML audio clock is authoritative.
- `WJ_INTRO_001` flies toward the camera from a distant first word, brakes, and
  arrives in a centered hover on its final word.
- `WJ_INTRO_002` remains in a flying hover while alternating restrained
  explanatory hand gestures and wing beats. Its speech vocabulary is restricted
  to authored flight and hover poses that keep the staff on its canonical
  screen-right side.
- Grounded clips use one stable authored camera-approach frame for the first 20
  percent of the recording, capped at 2,800 ms, ease into the intimate hold,
  and never cycle through a retreat frame while moving forward.
- Body changes occur on audio accents and remain at least 1,450 ms apart.
- A posture may not recur within the previous four motion beats.
- The same directed pose transition may not recur within a clip.
- Long spoken passages receive a semantic bridge before a body-pose hold can
  exceed 4,800 ms, including the final hold before the audio ends.
- Semantic pose selection matches complete words and phrases. Substrings such
  as `hat` inside `that` or `what` cannot accidentally trigger physical comedy.
- Books, spells, physical comedy, and hero declarations require transcript
  support; they are not generic filler poses.
- Generic celebration is intentionally restrained. Large excited and triumphant
  silhouettes remain available to explicitly authored hero moments, but cannot
  be selected merely because a line contains positive language.
- Book postures remain cataloged but are excluded from automatic performance
  selection. Both current book sources detach or relocate the staff, so they
  must be corrected and pass the visual gate before choreography can use them.
- Every clip has a distinct deterministic motion signature.
- Full-body posture changes use a 160 ms cubic blend, preserving the active
  mouth state on both complete frames.
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
python3 tools/audit_wizard_joe_performance_geometry.py
```

The generated `performance-audit.json` contains one result per clip for audio
integrity, continuous cue coverage, pose validity, motion spacing, four-beat
repetition, repeated transition pairs, gesture density, body-blend timing, and
mouth-pair coverage. It also evaluates the projector-visible initial and
terminal holds after camera approach has been applied.

`performance-geometry-audit.json` follows the pose order that the projector can
actually display. It checks silhouette-center displacement and apparent-size
changes for every full-frame transition. Lowest-visible-pixel changes are
diagnostic only because staffs, wings, tails, and flying poses do not share a
meaningful ground-contact line. The two reviewed acceleration/braking
transitions in Intro 001 are explicit authored exceptions; the global
thresholds remain strict.

Render large per-clip review sheets without changing the live viewer:

```bash
python3 tools/render_wizard_joe_performance_contact_sheet.py \
  --all \
  --output-dir /tmp/wizard-joe-performance-all-review \
  --tile-size 420 \
  --columns 2
```

Automated passage does not approve choreography or admit assets to production.
Use the reviewer’s `Needs changes` and `Approve choreography` controls to record
the visual gate in `review-state.json`.

The committed `visual-audit-pass-1.json` records the four-reviewer baseline for
all 95 clips before systemic corrections. Subsequent visual audit files use the
same schema and retain every clip-level verdict, rationale, and offending
transition so improvements and regressions remain accountable.

`visual-audit-final.json` is the current acceptance record. Four reviewers
inspected all 95 full-resolution, projector-visible contact sheets. The six
clips changed by the final exclusion of unsafe book art were rendered again and
received a targeted follow-up review. Final result: 95 pass, 0 review. This
visual result complements, rather than replaces, the 95/95 structural audit and
95/95 geometry audit.
