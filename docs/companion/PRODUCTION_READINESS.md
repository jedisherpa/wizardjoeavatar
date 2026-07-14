# Wizard Joe Companion Production Readiness

Assessment: **conditionally ready for isolated local acceptance; not ready for
public distribution**

## Ready

- The product architecture is implemented without replacing the Python
  animation engine or weakening Prism governance.
- Companion owns only its packaged child and does not target the legacy 8765
  process or LaunchAgent.
- Dynamic discovery supports either launch order and runtime credential
  rotation.
- Credentials stay out of the WebView, URLs, assets, diagnostics, and Git.
- Media and speech paths have truthful clocks, explicit error degradation,
  preemption, and restoration behavior.
- The app provides status, recovery, diagnostics, full pose access, continuous
  repeat, scoped keyboard controls, VoiceOver labels, and reduced-motion modes.
- All source-level verification gates pass.
- A local unsigned draft `.app` builds successfully.

## Release Blockers

1. Rebuild the sidecar and app from the clean implementation commit and record
   provenance and hashes.
2. Complete the packaged-runtime matrix in `VERIFICATION_EVIDENCE.md`.
3. Capture a real packaged Prism persona utterance with audible output and
   changing mouth states, including speech-to-main restoration.
4. Obtain independent verification of lifecycle, privacy, and media behavior.

## Explicitly Out of Scope

- Apple Developer ID signing
- notarization and stapling
- public release or artifact upload
- automatic updates
- replacement of the installed Prism GT app
- migration or removal of the legacy Wizard Joe LaunchAgent
- Windows or Linux packaging

These are future milestones, not hidden failures of the local artifact.

## Decision

Proceed with clean-commit packaging and isolated acceptance. Do not distribute,
replace installed applications, alter the LaunchAgent, or call the product
production-ready until all four blockers are closed.
