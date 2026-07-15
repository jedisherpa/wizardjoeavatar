# Orion Vale Worksheet Generation Record

Mode: built-in GPT Image generation with identity-preserving canonical references.

The approved derivatives are preserved under `assets/reference/personas/orion-vale/canonical-worksheets/`:

1. Identity and construction sheet: accepted revision 2 is a strict 4-by-4
   grid of 16 complete full-body identity/reference silhouettes. Revision 1 is
   retained as rejected evidence because its nonuniform callout collage cannot
   be segmented into 16 complete equal cells.
2. Eight-view turnaround.
3. Neutral and conversational base poses.
4. Twenty-four-cell expression set. Revision 2 supplies panels 0–22; its
   blank panel 23 is replaced by the corresponding reviewed revision-1 panel.
5. Speech, viseme, and blink sheet.
6. Hand and question-journal construction sheet.
7. Ground locomotion, jump, fall, and landing sheet.
8. Conversational, inquiry, distress-recovery, and journal-action sheet.
9. Full-body open-hand, closed-hand, fist, and reaching interaction sheet.

Production extraction uses revision 2 of the identity, neutral, expression,
speech-viseme/blink, and ground-motion sheets. The only recorded fallback is
expression panel 23 because the matching revision-2 cell contains no subject.
All sixteen speech and blink graphs come from revision 2.

Before animation mapping, the generator isolates exactly 124 worksheet cells:
16 identity/reference cells plus 108 cells across sheets 02–09 (8 turnaround,
8 neutral, 24 expression, 16 viseme/blink, 16 hand/prop, 16 motion, 16
signature, and 4 interaction). Every cell receives a content hash, bounds,
background-removal result, node count, and source worksheet hash in
`orion_vale_extraction_audit.json`.

The PNGs are production references, not runtime sprites.
`tools/generate_voxel_persona_character.py` consumes the explicit panel map in
`generation-profile.json`, removes the approved studio background, normalizes
each subject to the shared 72 by 96 root space, validates the four-cell safety
inset, and writes transparent colored-pixel-node JSON. Missing nodes are
transparent. It emits no runtime PNG or SVG.
