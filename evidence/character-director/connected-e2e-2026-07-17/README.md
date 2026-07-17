# Connected Prism Performance Capture

## Scope

This evidence was recorded on 2026-07-17 from two isolated source runtimes:

- Prism GT: `http://127.0.0.1:8890/`
- ASCILINE Python visualizer: `http://127.0.0.1:8875/`

The persistent local service on port `8765` remained running and was not used
as the recording target.

The submitted display request was:

> A complete fictional display request. In one concise sentence, warmly tell
> the audience that Wizard Joe is ready to begin the show.

Prism returned the governed display reply `The wizard steps forward with
purpose.` The Python media-session cursor advanced during the turn. The
sanitized transition receipt is `protocol-transitions.json`.

## Files

- `governed-speech-performance.mp4`: 25.49-second H.264 screen recording,
  1280x720, 116 frames. The recording is silent because no authorized system
  audio capture device was available.
- `capture-timing.json`: browser frame timestamps and capture costs. Capture
  began when the accepted media-session sequence advanced.
- `contact-sheet.png`: two-frame-per-second visual index of the recording.
- `protocol-transitions.json`: sanitized public status transitions sampled
  around the turn. Credentials, session suffixes, and content hashes are not
  retained.

SHA-256:

```text
0400880bb0062d31dffa676d352643fd3e83838e1c1060f5646314f3c8238b46  capture-timing.json
34e40da28b6227f64bb7411ddb83842e0591fe9653576d20d6a38e0133b85714  contact-sheet.png
612ef7ea5acd13e1b34ad4b754c63e516d4011058a05051d71d856ea47a0594a  governed-speech-performance.mp4
dc3d119e4aef6f19a6db544b232073febf0bec91cd2f238c66ba6fed1aaed597  protocol-transitions.json
```

## Interpretation

This package proves that a real Prism browser session connected to the Python
visualizer, accepted a governed display turn, advanced the authoritative media
cursor, restored the main media slot, and kept rendering live character
motion. It is useful connected-system evidence.

It is not a complete audiovisual acting-review artifact. The public status
route exposed the pre-turn and post-turn states but collapsed the short
intermediate speech lifecycle before the polling observer saw it. The MP4 also
contains no audio track. A longer connected utterance with authorized system
audio capture and a scored human lip-sync/body-language review remains an open
production acceptance gate.
