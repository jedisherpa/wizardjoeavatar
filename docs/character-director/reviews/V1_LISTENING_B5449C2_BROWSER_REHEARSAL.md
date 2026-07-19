# V1 Listening Browser Rehearsal: b5449c2

Status: **REVIEW BUNDLE REJECTED**

## Candidate

- Source commit: `b5449c2db47c38b8887073957622ad666259d11e`
- Evidence: `evidence/character-director/v1-listening-b5449c2-2026-07-18/`
- Atomic capture manifest: valid
- Machine acceptance: passed, 13 of 13 checks

## Passed

- 288 contiguous ASCILINE frames with no capture gaps or queue overruns
- Viewer-left-viewer gaze choreography
- Eye lead, authored three-quarter bridge, profile arrival, and settle
- Two visible blinks with bounded duration and 5.125-second onset spacing
- Canonical silhouette margins of at least 4 cells top/side and 6 cells bottom
- Planted-root and listening-stillness checks

## Rejection

The new real-browser pass reached Chrome and collected its full frame budget, but
Chrome exposed a `1280x633` screencast surface. The first encoder invocation used
`yuv420p` without padding, so H.264 rejected the odd frame height. The review
bundle is therefore incomplete and must not be submitted for independent visual
acceptance.

## Correction

Pad only the browser recording's encoded raster to the next even width and
height. Do not resize, smooth, or alter the ASCILINE canvas. Rebuild from a clean
commit and recapture the complete V1 package.
