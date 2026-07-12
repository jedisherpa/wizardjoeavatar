# Create the Module Structure

Create or adapt this structure:

```text
wizard_avatar/
├── __init__.py
├── models.py
├── palette.py
├── glyphs.py
├── geometry.py
├── masks.py
├── layers.py
├── anchors.py
├── skeleton.py
├── views.py
├── expressions.py
├── mouth.py
├── blink.py
├── gestures.py
├── locomotion.py
├── pathing.py
├── projection.py
├── floor.py
├── shadow.py
├── compositor.py
├── controller.py
├── frame_source.py
├── protocol.py
└── diagnostics.py

wizard_avatar/definitions/
├── wizard.json
├── front.json
├── front_left.json
├── left.json
├── back_left.json
├── back.json
├── back_right.json
├── right.json
├── front_right.json
└── expressions.json

web/avatar/
├── wizardClient.ts
├── wizardCanvas.ts
├── wizardControls.ts
├── wizardDiagnostics.ts
└── wizardDemo.ts

tests/wizard/
├── test_palette.py
├── test_geometry.py
├── test_views.py
├── test_expressions.py
├── test_locomotion.py
├── test_pathing.py
├── test_projection.py
├── test_floor.py
├── test_compositor.py
├── test_frame_source.py
├── test_codec.py
├── test_websocket.py
├── test_visuals.py
└── test_e2e.py
```

Use the existing language and directory conventions where the repository already has equivalent modules.
