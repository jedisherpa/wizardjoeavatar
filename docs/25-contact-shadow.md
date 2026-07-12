# Create the Contact Shadow

Draw a subtle projected contact shadow under the feet.

The shadow must:

- follow world position
- scale with depth
- remain aligned with the feet
- remain faint
- never become dark gray or black
- slightly widen during a grounded idle pose
- narrow when a boot is lifted

Use very light gray glyphs or background-cell changes.

Do not introduce transparency assumptions unsupported by the ASCILINE framebuffer.
