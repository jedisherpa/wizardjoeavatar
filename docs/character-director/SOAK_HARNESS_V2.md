# ASCILINE Soak Harness V2

Date: 2026-07-17

## Purpose

`tools/run_python_avatar_soak.py` verifies the live Python ASCILINE service
without replacing the visualizer or introducing another runtime. Version 2
closes three gaps in the original harness: WebSocket clients are bounded,
process RSS is sampled from the server PID, and cadence is evaluated throughout
the run instead of only at the endpoints.

The harness obtains the server PID and runtime epoch from
`/api/companion/health`. RSS verification only accepts literal loopback URLs,
and an explicit `--server-pid` must match the health response. This prevents a
remote or unrelated process from being reported as the measured server.

## Measurements

- fixed-capacity WebSocket receive queues and maximum message size;
- normal-viewer errors plus slow-viewer reconnect pressure;
- command latency through a fixed full-run histogram and bounded recent window;
- simulation and presentation cadence in non-overlapping rolling windows;
- hub queue drops and schedule overruns;
- harness event-loop scheduling lag;
- warm-up-aware RSS baseline, peak growth, final growth, and least-squares slope;
- server PID, runtime epoch, and final health continuity.

All sample and error collections are bounded. The CLI rejects a duration and
sample interval that would exceed `--max-runtime-samples`, so a long run cannot
silently discard the history used for its resource claim.

## Strict Defaults

| Gate | Default |
| --- | ---: |
| Simulation cadence | 55-65 Hz |
| Presentation cadence | 21-27 FPS |
| Rolling cadence breach fraction | <= 5% |
| Command latency p95 upper bound | <= 100 ms |
| Event-loop lag p95 | <= 250 ms |
| Schedule overruns | <= 60/min |
| Normal-viewer queue drops | 0/min |
| Slow-viewer queue drops | <= 1,500/min |
| Slow-viewer reconnects | <= 6/min |
| Peak RSS growth | <= 64 MiB |
| RSS growth slope | <= 8 MiB/hour after 600 measured seconds |

Queue drops are permitted only when `--slow-viewer` is enabled. The deliberate
slow viewer is expected to expose bounded backpressure; normal viewers must not
disconnect, regress sequence, or fail to decode.

## Staged V2 Receipt

An isolated companion-mode candidate on port `8877` was run while the legacy
service on `127.0.0.1:8765` remained live:

```bash
python3 tools/run_python_avatar_soak.py \
  --url http://127.0.0.1:8877 \
  --duration-seconds 720 \
  --viewers 4 \
  --slow-viewer \
  --sample-interval-seconds 5 \
  --rolling-window-seconds 30 \
  --resource-warmup-seconds 120 \
  --app-token "$WIZARD_COMPANION_APP_TOKEN" \
  --media-token "$WIZARD_MEDIA_CONNECTOR_TOKEN" \
  --strict \
  --output evidence/character-director/soak-v2-12m-2026-07-17.json
```

The strict run passed after 721.110 seconds.

| Measurement | Result |
| --- | ---: |
| Simulation cadence | 59.995 Hz |
| Final presentation window | 24.007 FPS |
| Complete 30-second windows | 22 |
| Simulation/presentation breach fraction | 0 / 0 |
| Requests | 6,191 |
| Command latency p95 upper bound | 50 ms |
| Maximum command latency | 131.394 ms |
| Normal-viewer errors | 0 |
| Decode/sequence errors | 0 / 0 |
| Slow-viewer reconnects | 12 |
| Hub queue drops | 73.220/min |
| Schedule overruns | 3.495/min |
| Event-loop lag p95 | 1.871 ms |
| Post-warm-up RSS interval | 601.096 s |
| RSS growth/peak growth | 1,916,928 / 1,916,928 bytes |
| RSS slope | 8,038,419.286 bytes/hour |

Evidence SHA-256:

```text
f4c306bc79525f9374726650f290105f0d11d2f450609b4c36e411bc48e9e0de  evidence/character-director/soak-v2-12m-2026-07-17.json
```

This staged run proves the V2 measurement and failure gates operate against the
real Python server. It does not replace the required eight-hour and 24-hour
runs, so long-duration production acceptance remains partial.
