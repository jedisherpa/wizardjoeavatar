# WizardJoeAvatar First-Pass Verification

- status: first procedural implementation pass, not completion-gate approval
- base commit SHA: 59f17bb2e534e987242b5c7ae2b47f42f95c8792
- source reference image path: assets/reference/target_voxel_wizard.png
- local run command: python3 tools/run_wizard_avatar_server.py --port 8000
- test command: python3 -m unittest discover -s tests
- production build command: not applicable; procedural Python/browser app
- test totals: 31 passed, 0 failed, 0 skipped in the current focused suite
- generated visual evidence: evidence/wizard/golden-images/ rendered as colored square tiles
- generated visual footprint evidence: evidence/wizard/visual-diffs/visual_footprint.json
- generated movement evidence: evidence/wizard/movement-traces/movement_traces.json
- generated codec evidence: covered by tests/wizard/test_codec.py
- cached background hash: 4908c985b10bdf16eaa0e916d253a6209615af414451952c7f3115f674698799
- known gap audit: docs/wizard/COMPLIANCE_GAP_AUDIT.md
- remaining limitations: the full 38-document completion gate is not satisfied yet; browser automation, full named test matrix, real TTS timing hooks, reconnect/resync tests, and complete evidence categories remain.
