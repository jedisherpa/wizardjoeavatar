# V8 Independent Review

Verdict: **FAIL**

Candidate:
`b34368e9166aeb71dfe50b7b31c71165f1a35151`

Evidence:
`evidence/character-director/v8-purposeful-performance-b34368e9-2026-07-24`

## Machine Facts

- Machine acceptance passes every check across 1,440 canonical V8 frames.
- 13 blinks, each exactly four frames, with 12 distinct intervals and stable
  body/root during closure.
- Three deliberate gestures were detected. Body stillness is 95.62%, with no
  short exact loop.
- Root movement is stable; zero clipped frames were detected.
- AV authority is `media_alignment`. Across 240 active samples, measured
  offset was 2-100 ms, averaging 35.6 ms.
- Audio was unmuted and playing; the permission world was ready.
- Browser decoding recorded zero errors and zero resyncs.
- Browser presentation nevertheless recorded four dropped frames, eight held
  frames, and 2,391 presented frames from 2,395 decoded.

## Visual Judgment

- The contact sheet shows consistent character scale, grounding, staff
  placement, and silhouette.
- Explaining, pointing, and gaze poses are recognizable and remain inside the
  canonical stage.
- Blink frames do not visibly displace or corrupt the body.
- No obvious cropping, layer separation, or facial corruption appears in the
  inspected still evidence.

## Limitations

Direct video playback and audible monitoring were blocked by the available
review tooling. The reviewer therefore could not honestly judge real-time
easing, transition pops, subjective blink cadence, voice intelligibility, or
perceived lip-sync by watching and listening to the supplied MP4s.

## Production Blockers

1. The four browser presentation drops require either a zero-drop recapture
   or an explicitly documented production tolerance.
2. A human reviewer must directly watch the normal and quarter-speed videos
   and listen to `v8-audible-review.mp4`.

The underlying animation and AV measurements are strong and look ready for
that final human gate, but the reviewer did not grant unconditional
production acceptance without direct playback and resolution of the
dropped-frame evidence.

No files were modified by the reviewer.
