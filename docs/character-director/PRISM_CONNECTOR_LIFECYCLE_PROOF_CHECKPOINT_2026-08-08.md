# Prism Connector Lifecycle Proof Checkpoint

Date: 2026-08-08

Status: implementation and pure validation complete; focused tests passed; no live installed lifecycle run has been claimed

## Purpose

This checkpoint adds the missing opt-in proof path for the canonical Prism
connector lifecycle. It does not change the connector, controller, frame
stream, server, score compiler, or playback authority.

The ordinary governed-speech driver behaves as before unless
`--lifecycle-proof` is present.

## Proof Sequence

The lifecycle mode performs these observations and actions in order:

1. It uses a real Chrome pointer event on Prism's visible `Play` control.
2. It waits for audible `main` media and Wizard `source_slot=main` with clocks
   within 100 ms.
3. It submits the existing governed prompt and waits for audible `speech`, an
   active governed release, `media_alignment` mouth authority, and an open mouth
   shape.
4. It waits for the same main-media identity to return at a later media time,
   without directly starting, pausing, seeking, or restarting an audio element.
5. It invokes an explicit caller-supplied command that must restart only the
   disposable Wizard runtime.
6. It requires a changed Wizard runtime epoch, an observed `reconnect` snapshot,
   restored main authority, and cleared obsolete speech within the configured
   recovery budget.
7. It replays the retained old speech snapshot and requires a non-accepted
   disposition while main remains active and obsolete speech remains inactive.

The restart command is executed as an argument vector without a shell. The
command must be the final CLI option. Its text and output are not retained; only
a SHA-256 identity and duration are written to evidence.

## Content-Free Receipt

`tools/prism_connector_lifecycle_receipt.py` defines the pure receipt validator.
The lifecycle receipt contains only:

- opaque media IDs and media digests;
- a digest of the connector session ID;
- sequence, media epoch, cause, source slot, and playback state;
- browser and Wizard media times, playback rate, and absolute clock offset;
- visible character counts, never message content;
- mouth shape and mouth-authority identity;
- before/after runtime epochs and reconnect duration;
- stale replay disposition and sanitized error code;
- a digest of the restart command.

The validator recursively rejects private-bearing keys including prompt,
approved text, speech text, transcript, message collections, and generic text
fields. Validation is deterministic and performs no I/O.

## Invocation

The proof requires disposable loopback Prism and Wizard endpoints, the existing
connector token environment variable, a real main track, and a restart helper
that returns after replacing the disposable Wizard process.

```bash
python3 tools/drive_prism_governed_speech.py \
  --prism-url http://127.0.0.1:8890 \
  --wizard-url http://127.0.0.1:8896 \
  --receipt /absolute/path/connector-lifecycle-receipt.json \
  --lifecycle-proof \
  --lifecycle-restart-command /absolute/path/restart-disposable-wizard
```

`--lifecycle-restart-command` must be last because all remaining arguments are
passed to that command. Protected persistent ports remain rejected by the
driver.

## Acceptance Checks

The receipt passes only when all checks pass:

- exact lifecycle schema and content-free boundary;
- strictly ordered `main -> speech -> main` observations;
- active browser and Wizard authority in every phase;
- open, media-aligned speech mouth authority;
- identical and advanced main-media identity after speech;
- all three phase clocks within 100 ms;
- changed runtime epoch and accepted reconnect within the configured budget;
- obsolete speech inactive after reconnect;
- replayed old speech snapshot not accepted and unable to reclaim authority.

## Focused Verification

The focused unit suite covers:

- unchanged default CLI behavior;
- explicit lifecycle opt-in and required restart command;
- restart argument preservation without shell interpretation;
- real pointer dispatch and already-playing preservation;
- valid content-free receipt acceptance;
- private-text key rejection;
- rewound or substituted main-media rejection;
- missing runtime rotation rejection;
- accepted stale-turn rejection;
- validator input immutability.

No installed Prism application, real main track, real TTS turn, process restart,
or stale replay was exercised while creating this checkpoint. A passing unit
receipt is not production evidence. The canonical release gate remains open
until the opt-in mode produces a passing receipt from the installed processes.
