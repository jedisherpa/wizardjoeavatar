# WizardJoeAvatar Visual Reference

The current PNG reference for this project is
`assets/reference/target_voxel_wizard.png`. It defines an elderly male
square-cell voxel wizard with:

- a tall blue hat with gold stars and a wide gold band
- warm tan skin, large eyebrows, and a thoughtful, slightly witty expression
- a brown beard and moustache
- bright blue eyes and white teeth
- rainbow block wings behind the body
- a blue robe
- a magenta inner robe
- brown boots
- a brown staff on viewer-right with a curled hook

## Required views

- front
- back
- left
- right
- front-left
- front-right
- back-left
- back-right

## Required expressions

- neutral
- happy
- thinking
- surprised
- worried
- amused
- confident
- focused
- skeptical
- explaining

## Required actions

- idle
- speaking
- explaining
- walking
- thinking
- pointing
- magic cast
- reaction

## Style

The character must look like a deliberately authored square-cell voxel avatar.
Use clear silhouettes, hard square cells, and a repeatable source-image to
cell-mask conversion. The runtime must not stream the source PNG directly; it
uses the generated JSON cell mask at
`wizard_avatar/definitions/reference_avatar_cells.json`.

The environment is fixed: pure white background, faint white checkerboard perspective floor, and a subtle contact shadow.
