# Wizard Joe Companion Rollback

## Safety Baseline

Wizard Joe Companion does not replace or control:

- `/Applications/Prism GT.app`
- `/Applications/Prism GT.pre-wizard-connector.app`
- LaunchAgent `com.jedisherpa.wizardjoeavatar`
- the legacy Wizard Joe process on `127.0.0.1:8765`

The primary rollback is to quit the Companion and remove only its own new
application and support data after preserving logs needed for diagnosis.

## Stop the Companion

Quit **Wizard Joe Companion** normally. It sends an authenticated shutdown to
its child, waits up to three seconds, removes only the discovery document it
owns, and kills only that child if graceful shutdown times out.

If the window is unresponsive, use Force Quit on **Wizard Joe Companion**. Do
not kill by a generic Python or port-8765 pattern because that can target the
preserved legacy service.

## Disable Login Launch

Turn off **Launch at login** in the app before removal. If the app cannot open,
remove its login item using macOS System Settings > General > Login Items.

## Remove the Local Test Build

Remove only the specific new `Wizard Joe Companion.app` path that was installed.
Do not rename, delete, or overwrite either Prism GT application.

Application support is under:

```text
~/Library/Application Support/Wizard Joe Companion/
```

Preserve `logs/` before deleting support data when investigating a fault.
`connector-v1.json` is ephemeral and may be removed after confirming the
Companion and its child are not running.

## Restore Prism Connector Selection

The current Prism build prefers Companion discovery. An operator can explicitly
select the legacy private connector configuration by setting
`PRISM_WIZARD_CONNECTOR_CONFIG` for that Prism process. There is no implicit
fallback to a historical config path because that could mask a stale service.

## Repository Rollback

Use normal Git revert commits on the specific Companion or Prism integration
commits. Do not use `git reset --hard`, discard untracked pose evidence, or
restore whole files over unrelated user work. The original repository commits
and preservation baseline are recorded in `PROGRAM_TRACKER.md`.
