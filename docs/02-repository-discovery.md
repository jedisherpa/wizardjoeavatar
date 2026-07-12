# Inspect the Repository Before Coding

Before implementation:

1. Read every repository instruction file.
2. Locate all existing ASCILINE code.
3. Locate the current Python server.
4. Locate the browser player.
5. Locate `codec.py` and `codec.js`, or their current equivalents.
6. Locate the current WebSocket route.
7. Identify the exact cell layout used by color ASCII modes.
8. Determine whether each cell is encoded as:
   - glyph plus RGB
   - RGB plus glyph
   - palette index plus glyph
   - another structure
9. Verify the result from production source code and tests.
10. Identify how the browser renders glyphs and colors.
11. Verify the adaptive codec’s supported tags.
12. Verify whether frames must be decoded sequentially.
13. Verify how keyframes reset decoder state.
14. Preserve all existing video-playback behavior.
15. Add the avatar as a new frame source and route rather than breaking the existing ASCILINE player.

Write:

```text
docs/wizard/ASCILINE_REPOSITORY_AUDIT.md
docs/wizard/IMPLEMENTATION_PLAN.md
docs/wizard/PROTOCOL_BASELINE.md
```

Continue autonomously after these documents are complete.
