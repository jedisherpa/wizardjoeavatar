# Integrate with ASCILINE as a Direct Frame Source

Create:

```python
class ProceduralWizardFrameSource:
    def __init__(
        self,
        cols: int,
        rows: int,
        fps: float,
    ): ...

    async def next_frame(self) -> WizardCellFrame: ...

    def current_state(self) -> WizardState: ...

    async def apply_command(
        self,
        command: WizardCommand,
    ) -> CommandResult: ...
```

The frame source must generate ASCILINE cells directly.

Do not:

- render to MP4
- invoke OpenCV’s video decoder
- create temporary video files
- pass the procedural frames through the ordinary video source

Add a dedicated route:

```text
/ws/avatar/wizard?codec=adaptive
```

Keep the existing `/ws` video behavior intact.

Send:

- initialization
- immediate keyframe
- ordered delta frames
- periodic keyframes
- resync keyframes

Use one encoded frame per channel and fan it out to all viewers.
