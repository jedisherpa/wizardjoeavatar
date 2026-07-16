# Aurelia Finch Final Verification

Verification date: 2026-07-15

Branch: `codex/persona-aurelia-finch`.

## 124-cell isolation and visual audit

- Accepted total: 124/124.
- `isolated_silhouettes`: 124/124 pass.
- `pixel_graphs`: 124/124 pass.
- 16 transparent identity/reference graphs plus 108 transparent pose/feature graphs.
- Total colored nodes: 239,398; distinct RGB triples: 110,562.
- Every graph is nonempty (1,013 to 3,997 nodes), unique, and inside `x=4..67`, `y=4..91`.
- Blue-background node predicate count: 0. Floor/contact-shadow rejection is true on all 124 extraction audit items.
- Runtime assets are colored JSON nodes only; audit runtime references contain no PNG or SVG path.
- Brown skin, very dark curls, cream wide-brim hat, navy band, right-side orange accent, pearls, burnt-orange wrap dress, brown heels, and dark-brown/gold-corner folio remain visible across the reviewed sheets.
- Both 124-up sheets were visually inspected at original resolution. The isolated and projected sheets are pixel-identical, confirming zero projection loss.

Evidence:

- `aurelia-finch-124-isolated-silhouettes.png`: `c862d5f20617a7376ec740f9474318eb6ff91b835dacc887bcd2267eca562b38`.
- `aurelia-finch-124-pixel-graph-renders.png`: `c862d5f20617a7376ec740f9474318eb6ff91b835dacc887bcd2267eca562b38`.
- `aurelia-finch-124-visual-audit.json`: 124 comparisons, zero failed, zero different nodes.

## Lineage and package integrity

- Original reference: `bd8bc74059e57f8edafb0161bcbc7b70dd52ddddc59ec72dd1808f8287c87f41`.
- Canonical voxel: `462dbff7c21e06c4450bf620f13f0bb7c923f57dd4819cb11eb9bfcc8853a821`.
- Generation profile: `522ae810ad56a156be6ccb6ba5e1c400374316b659aa60da9907020114bc39c3`.
- Pose library: `bef043eb4db2e7916776917ed9ea9efe2981f363b0b61f25da2ff92857f1cdad`.
- Pixel graph library: `dd35a3acb67cac7d8e7228fb12f6efae43e9e66d9859a625992cf8b0b34285a3`.
- Extraction audit: `6221c34d98a009f3512ac610c4c18b2adf95538de80fe5d6c8ee49f750773bc3`.
- Animation graph: `42c56a3025e63aab04d45b0698af7b36507d16a8c317be9dd00e42326964fd33`.
- Animation matrix: `69d3b3ec9b60484c0cf0bc7b526899ffd6eaa1b576d13bb42452a7a2c155589d`.
- Character package: `2a2f320aa55ff835b0d04cdc56fc403da1ad20f9ef3c7ab8e6174ea7a157b8f8`.
- Runtime profile: `8296e88a81beec787cffec13ebe105d1fb13be3e76d00c8e100ab77025caed22`.
- Manifest: `c08212ac840ca9eda60add3a6c38ebe60a1d8354c93473bb6a5caa687ba526eb`.

Package tests prove rejection of post-audit graph tampering and independent
tampering of the original reference, canonical voxel reference, or any accepted
worksheet. Load-time validation checks those full provenance hashes, exact
count, per-item hash/count/bounds, canonical safety bounds, and RGB values.

## Runtime and API verification

- Persona-specific actions are runtime reachable: partnership pitch, stakeholder translation, proof presentation, public promise check, leadership briefing, leadership recovery, and diplomatic recovery.
- Turn, crouch, jump, controlled fall, landing, locomotion, expression, speech, and blink paths render direct cells.
- Runtime render passes while `PIL.Image.open` is forced to fail.
- Live HTTP on `127.0.0.1:8879`: characters `200/2015 bytes`, state `200/1776`, poses `200/2216`, pixel graph library `200/5722550`, manifest `200/3636`, runtime profile `200/2640`.
- Live WebSocket: `INIT:24.0:5:240:135:0:0:0.000`, followed by an 8,596-byte
  binary frame; a partnership-pitch command then produced a 9,266-byte frame.

## Automated verification

- Deterministic generation: pass, `Aurelia Finch generated assets are deterministic`.
- Focused suite: 13 passed, 0 failed, 0 skipped.
- Full suite: 174 passed in 110.682 seconds, 0 failed, 0 skipped.
- Production Python scope: 50 files scanned, 0 violations.
- Strict animation quality: 32/32 scenarios passed, 0 issues.
- `git diff --check`: pass.
