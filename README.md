# WizardJoeAvatar

Procedural ASCILINE wizard-avatar implementation specification.

The project is designed around a server-authoritative, editable character assembled from ASCII cell masks, color palettes, semantic layers, skeletal anchors, directional views, procedural locomotion, independent expression/speech channels, a fixed white studio background, and a faint perspective checkerboard floor.

## Start here

- [Codex goal entry point](CODEX_GOAL.md)
- [Section index](docs/INDEX.md)
- [Visual reference specification](assets/reference/README.md)

## Core constraints

- No prerecorded video.
- No runtime flattened character PNG.
- No generated animation frames as the implementation.
- No wings.
- Fixed white background.
- Very faint checkerboard floor.
- Eight-direction movement.
- Forward/back depth projection.
- Circular and figure-eight pathing.
- Direct procedural ASCILINE frame generation.
- Full codec, reconnect, visual, locomotion, environment, and speech testing.

## Repository purpose

This repository is intended to be cloned or referenced from any development machine and supplied directly to Codex as the authoritative implementation specification.
