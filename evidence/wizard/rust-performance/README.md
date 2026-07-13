# Rust Wizard Avatar Performance Evidence

| profile | grid | frames | measured fps | target fps | target met | wire/raw |
|---|---:|---:|---:|---:|---|---:|
| low | 180 x 101 | 90 | 138.0 | 15.0 | yes | 0.0011 |
| medium | 240 x 135 | 144 | 142.1 | 24.0 | yes | 0.0008 |
| high | 480 x 270 | 144 | 72.8 | 30.0 | yes | 0.0003 |

## Codec Tags

- `low`: tag `2` = `88`; tag `3` = `2`;
- `medium`: tag `2` = `141`; tag `3` = `3`;
- `high`: tag `2` = `141`; tag `3` = `3`;
