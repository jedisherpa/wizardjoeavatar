# Use Multiple Coordinated Agents

Use several Codex agents under one integration lead.

## Agent 1: ASCILINE repository investigator

Inspect the complete ASCILINE repository.

Read:

- README
- LICENSE
- stream server
- WebSocket routes
- frame source logic
- encoder
- adaptive codec
- browser decoder
- Canvas renderer
- tests
- cross-language codec vectors
- player initialization handshake

Document:

- exact framebuffer structure
- exact byte order
- character-cell format
- color format
- frame header format
- codec tags
- keyframe behavior
- delta behavior
- WebSocket initialization
- browser rendering assumptions

Do not guess any wire format.

## Agent 2: Procedural character artist

Author:

- palette
- cell masks
- character proportions
- front view
- back view
- left view
- right view
- diagonal views
- face features
- beard
- robe
- hat
- hands
- boots
- staff
- magic effects

## Agent 3: Animation and locomotion engineer

Implement:

- body skeleton
- walking
- directional facing
- depth movement
- turning
- circular movement
- path following
- idle animation
- procedural limb motion
- stopping and starting
- state blending

## Agent 4: Expression and speech engineer

Implement:

- eyes
- eyebrows
- blinking
- mouth shapes
- facial expressions
- speaking animation
- TTS timing hooks
- gesture overlays

## Agent 5: Environment and projection engineer

Implement:

- white fixed background
- faint checkered floor
- perspective projection
- depth scaling
- contact shadow
- screen bounds
- movement coordinates

## Agent 6: ASCILINE integration engineer

Implement:

- procedural frame source
- adaptive frame encoding
- WebSocket streaming
- keyframes
- delta frames
- browser rendering
- reconnect
- resynchronization
- frame fanout

## Agent 7: Test and verification engineer

Implement:

- unit tests
- visual golden tests
- path tests
- codec tests
- movement tests
- long-running tests
- browser end-to-end tests

## Integration lead

The integration lead must:

- maintain one shared architecture
- own all public schemas
- prevent parallel duplicate renderers
- review visual consistency
- run the full suite after each phase
- reject placeholders and untested code
- produce final verification evidence
