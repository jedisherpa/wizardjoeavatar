# ASCILINE Repository Audit

Audit date: 2026-07-12

Reference inspected:

- `external/ASCILINE/README.md`
- `external/ASCILINE/LICENSE`
- `external/ASCILINE/stream_server.py`
- `external/ASCILINE/codec.py`
- `external/ASCILINE/codec.js`
- `external/ASCILINE/app.js`
- `external/ASCILINE/test/`

The requested `jedisherpa/asciline` and `jedisherpa/ASCILINE` repositories were
not found. The public ASCILINE implementation located during discovery is
`YusufB5/ASCILINE`; it is used here only as protocol reference material.

## Repository Shape

ASCILINE is a Python/FastAPI server with a vanilla browser player. The production
server is `stream_server.py`. It decodes ordinary video sources through OpenCV,
maps frames to ASCII/pixel framebuffers, and streams binary frames over
WebSockets. The browser uses `app.js`, `codec.js`, and Canvas rendering.

WizardJoeAvatar is implemented as a direct procedural frame source instead of
using ASCILINE's video decoder path.

## Important Files

- `stream_server.py`: production HTTP/WebSocket server and video frame producer.
- `codec.py`: Python adaptive frame encoder.
- `codec.js`: browser and Node adaptive frame decoder.
- `app.js`: browser WebSocket client and Canvas renderer.
- `test/`: existing upstream protocol and playback tests.

## License Caution

The referenced ASCILINE repository is labeled "MIT License (with
Anti-Advertisement Restriction)." The added restriction excludes use for
delivering advertisements, sponsored content, or commercial marketing to
end-users. Treat it as a non-standard permissive license. WizardJoeAvatar avoids
copying upstream source wholesale and implements its own procedural frame source,
codec, and browser renderer from the audited protocol behavior.

## Integration Decision

The avatar integration follows the observed ASCILINE frame model:

- row-major cell framebuffers
- full-color ASCII cells
- one WebSocket binary frame per rendered avatar frame
- adaptive keyframes and deltas
- a dedicated `/ws/avatar/wizard?codec=adaptive` endpoint

The ordinary upstream `/ws` video behavior is not modified by this repository.
