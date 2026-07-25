# Falcor implementation pass

Falcor is registered as `falcor-v1` beside Wizard Joe and CrystAIl. It uses the same square-cell stream, deterministic controller, character-scoped HTTP API and browser selector, while adding explicit vehicle state. Like the corrected CrystAIl implementation, its runtime poses are direct square cells rasterized deterministically from approved canonical worksheets; no hand-drawn placeholder renderer is used.

## Commands

`POST /api/avatar/falcor-v1/engine` with `{"state":"off|starting|idle|running"}`.

`POST /api/avatar/falcor-v1/drive-mode` with `{"mode":"parked|road|off_road"}`.

`POST /api/avatar/falcor-v1/door` with `{"door":"driver|front_passenger|rear_left|rear_right|liftgate|hood","state":"open|closed"}`.

`POST /api/avatar/falcor-v1/cabin-view` with `{"view":"exterior|driver|front_passenger|rear_left|rear_center|rear_right|engine_bay"}`.

Standard `control` input drives Falcor across the world plane. Off-road mode adds deterministic suspension bounce; door/hood/liftgate safety rejects opening while moving mode is selected.

The browser toolbar appears only when Falcor is selected and switches the three looped audio beds from state. Browser audio still requires a user gesture, satisfied by the Engine/drive controls.
