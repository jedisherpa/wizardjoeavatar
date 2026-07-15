# Finn Calder — Canonical Worksheet Generation Record

## Scope and production rule

This package contains exactly **124 accepted deterministic cells**, not 108. The accepted cells are visual references for extraction only. Runtime animation must not load, decode, display, or ship these PNG worksheets or any SVG substitute.

All sheets were generated with the built-in GPT Image workflow using `canonical-voxel.png` as the highest visual authority and the identity sheet as a hard secondary reference. Generated source candidates are preserved beside approved normalized derivatives. Normalization changed dimensions only so every accepted grid divides into exact integer cells.

## Accepted sheets, geometry, and hashes

| Sheet | Accepted file | Grid | Cells | Exact image | Exact cell | SHA-256 |
|---|---|---:|---:|---:|---:|---|
| 01 identity | `01-identity-sheet-approved-v1.png` | 4×4 | 16 | 1248×1248 | 312×312 | `4457fd834b64c2cc1440fa1317f52df11c91d2bddab10a45895af8d4c1641724` |
| 02 turnaround | `02-turnaround-sheet-approved-v1.png` | 4×2 | 8 | 1776×888 | 444×444 | `e5ef341fd92ef0c548aadb88b6235eed572592bec37ff51283e008367f317c49` |
| 03 neutral bases | `03-neutral-base-poses-approved-v1.png` | 4×2 | 8 | 1672×940 | 418×470 | `4da98de07a151b0a6160d9f32d1dcb8c21a07db291d41ef9c05656ad132a095d` |
| 04 expressions | `04-expression-sheet-approved-v1.png` | 6×4 | 24 | 1620×972 | 270×243 | `bad740bfbe09d6d544daf46f581ef857fce4c681e31cb48c394eb692007f57a0` |
| 05 visemes/blinks | `05-speech-viseme-sheet-approved-v2.png` | 4×4 | 16 | 1256×1256 | 314×314 | `ff68617c922f354157ee3f1af886add72a6cb1b102460f18b7854a30f5c23739` |
| 06 hand/prop | `06-hand-prop-sheet-approved-v1.png` | 4×4 | 16 | 1256×1256 | 314×314 | `17ec0c04a93119b560bb7677102c06bfafc69b8e64c7eea406ecf78627681f8b` |
| 07 motion | `07-ground-motion-sheet-approved-v1.png` | 4×4 | 16 | 1256×1256 | 314×314 | `d6a7dcae3381f3ba43aba20ab9bf1a2cfe483dbef6b5bbe3fd4f2f0cf33938e2` |
| 08 signature | `08-signature-actions-sheet-approved-v1.png` | 4×4 | 16 | 1256×1256 | 314×314 | `e3f230896a6ce28b894cd19d4dcddcd3877bcdb059b9ec1746c4a9f54d309311` |
| 09 interaction | `09-interaction-poses-approved-v1.png` | 2×2 | 4 | 1254×1254 | 627×627 | `5cfc3a6ad3bbb158321363145207ad94f2472aa56d0f3d4ead6a284e52ea1c9f` |
| **Total** |  |  | **124** |  |  |  |

## Exact panel maps

Cells are indexed row-major, starting at 1.

### 01 — Identity (16)

1 neutral full-body front; 2 full-body front three-quarter; 3 full-body left profile; 4 full-body back; 5 face front; 6 face three-quarter; 7 jacket/shirt/belt front; 8 jacket back; 9 open hand; 10 closed/fist hand; 11 shoe front/side; 12 microphone; 13 microphone grip; 14 silhouette front; 15 silhouette side; 16 silhouette back.

### 02 — Turnaround (8)

1 front; 2 front three-quarter left; 3 left profile; 4 back three-quarter left; 5 back; 6 back three-quarter right; 7 right profile; 8 front three-quarter right.

### 03 — Neutral bases (8)

1 neutral front; 2 neutral three-quarter; 3 neutral side; 4 neutral back; 5 relaxed idle; 6 attentive idle; 7 speaking idle; 8 listening idle.

### 04 — Full-body expressions (24)

1 neutral; 2 calm; 3 joy; 4 amusement; 5 excitement; 6 curiosity; 7 confidence; 8 compassion; 9 surprise; 10 confusion; 11 skepticism; 12 concern; 13 sadness; 14 shame; 15 embarrassment; 16 fear; 17 anxiety; 18 anger; 19 frustration; 20 determination; 21 fatigue; 22 contemplation; 23 speech emphasis; 24 settled recovery.

### 05 — Full-body visemes and blinks (16)

1 rest; 2 closed lips; 3 slightly open; 4 wide vowel; 5 open vowel; 6 rounded vowel; 7 teeth consonant; 8 lower-lip consonant; 9 tongue consonant; 10 smile speaking; 11 frown speaking; 12 speech emphasis; 13 breath/pause; 14 eyes open; 15 half blink; 16 full blink.

### 06 — Hands and microphone (16)

1 open relaxed; 2 closed relaxed; 3 fist; 4 point; 5 present; 6 reach; 7 microphone grip; 8 speaking-height grip; 9 lowered grip; 10 offered microphone; 11 receiving hand; 12 transfer; 13 two-hand hold; 14 emphasis lift; 15 release; 16 settled hold.

### 07 — Ground and airborne motion (16)

1 walk left contact; 2 walk down; 3 walk passing; 4 walk right contact; 5 run contact; 6 run airborne passing; 7 start anticipation; 8 stop/brake; 9 planted turn left; 10 planted turn right; 11 crouch; 12 jump anticipation; 13 jump airborne; 14 fall; 15 land contact; 16 land recovery.

Cells 9 and 10 were visually audited as opposite directional silhouettes with distinct planted feet. Cells 12–16 form compression, airborne, descent, contact, and recovery keys without changing character scale.

### 08 — Signature performance arcs (16)

1 welcome anticipation; 2 inclusive opening; 3 microphone welcome; 4 welcome recovery; 5 announcement breath; 6 energetic announcement; 7 participation cue; 8 ritual hold; 9 scan/listen; 10 accessibility check; 11 transition direction; 12 ready confirmation; 13 celebration anticipation; 14 celebration; 15 hand-to-heart appreciation; 16 community sign-off.

### 09 — Full-body interaction (4)

1 open; 2 closed; 3 fist; 4 reach.

## Rejections and corrections

- `05-speech-viseme-sheet-rejected-v1.png` (SHA-256 `40d54afb178e853b4d39f40d1f9e5ba92972a870aed403cb4bcc14e170a641a2`) is retained as a rejected candidate. Its half-blink did not separate clearly enough from the open-eye state.
- `05-speech-viseme-sheet-approved-v2.png` replaces it with visibly distinct cells 14–16: open eyes, vertically compressed half blink, and thin-line full blink.
- Original generated candidates with non-divisible outer dimensions remain provenance only. The `approved` files above are the sole extraction inputs.

## 124-cell audit evidence

The approved files were decoded as RGB PNGs and split in memory using the declared exact grids. The audit proved:

- total decoded cells: **124**;
- cells with integer geometry: **124/124**;
- non-empty/non-flat cells: **124/124**;
- unique raw-pixel crops within each sheet: **124/124**;
- minimum within-sheet pairwise mean pixel difference was positive for every sheet;
- full-body sheets retain head, hands, shoes, microphone, and outer safety margin;
- expressions and visemes are full-body rather than bust substitutions;
- no accepted sheet contains labels or runtime text;
- no unapproved prop appears; Finn's microphone is the only prop;
- identity, suit construction, eye grammar, microphone scale, voxel style, and camera family remain stable;
- no accepted silhouette is visibly clipped by its cell boundary.

Audit metrics by sheet:

| Sheet | Unique | Minimum variance | Minimum pair difference |
|---|---:|---:|---:|
| 01 | 16/16 | 2234.11 | 9.39 |
| 02 | 8/8 | 2728.10 | 10.49 |
| 03 | 8/8 | 2531.29 | 9.07 |
| 04 | 24/24 | 3501.54 | 8.22 |
| 05 | 16/16 | 4253.65 | 3.59 |
| 06 | 16/16 | 3019.83 | 6.75 |
| 07 | 16/16 | 3904.95 | 8.01 |
| 08 | 16/16 | 4102.55 | 11.08 |
| 09 | 4/4 | 3907.68 | 13.05 |

## Mandatory pixel-graph handoff

The next implementation stage must perform these steps in this order for **all 124 accepted cells**:

1. Verify the approved worksheet SHA-256 before extraction.
2. Slice each sheet by its exact integer geometry and declared row-major map.
3. Remove the pale-blue sheet/cell background from every isolated cell before deriving runtime data. Gutters, studio field, floor, and shadows are not character pixels.
4. Re-audit **124/124 isolated transparent silhouettes** for complete anatomy, complete microphone, safety bounds, stable baseline/root, stable scale, identity, and absence of blue/background contamination.
5. Convert every approved isolated pose into its own transparent **pixel graph** in the canonical character canvas.
6. Store only colored pixel nodes or deterministic horizontal runs plus anchors/bounds/attachments. Do not store a PNG, SVG, data URL, raster byte stream, or render-asset path in runtime definitions.
7. Reconstruct each graph through the visualizer's existing projector, which paints the colored nodes/runs onto a canvas for each animation frame.
8. Re-audit **124/124 reconstructed pixel graphs** against the corresponding isolated silhouettes before any animation graph is reconnected.
9. Only after both 124-item audits pass may states, transitions, timing, anticipation, action, follow-through, recovery, pivots, contacts, and fallback mapping be connected.

The worksheets are production references, not runtime sprites. Any implementation that displays these PNGs or converts them to SVG render assets violates the character build contract.

## Status

Canonical worksheet package: **ready for deterministic background removal and pixel-graph extraction**. Runtime integration, animation reconnection, commit, and push are intentionally outside this package task.
