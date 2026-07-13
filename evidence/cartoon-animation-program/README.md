# Cartoon Animation Evidence

This directory retains compact, commit-bound proof for the WizardJoe cartoon-animation program. Production acceptance is exclusively the ASCILINE Python service on port `8765`. Rust code, Cargo output, Rust-side ports, and Rust evidence cannot approve a production gate.

## Contract

Each machine-readable gate record conforms to:

`wizard_avatar/definitions/cartoon_animation_evidence.schema.json`

Every record identifies:

- one `CAP-NNN` work item and gate;
- the full pushed planning-checkpoint commit;
- the exact tested commit;
- the `asciline_python` architecture and port `8765`;
- every verification command, exit code, duration, result, and concise output hash;
- every retained artifact, its SHA-256, size, storage tier, and retention period;
- changed paths, residual risks, and optional independent review.

Evidence is invalid when it was generated from a different commit than the code under review, refers to an unpushed planning checkpoint, substitutes Rust results for Python behavior, or omits a failed command.

## Validation

Validate the current program, ownership declarations, planning checkpoint, wing contract, Python production boundary, and evidence schema:

```bash
python3 tools/validate_cartoon_animation_program.py --root .
```

Write a compact validation report atomically:

```bash
python3 tools/validate_cartoon_animation_program.py \
  --root . \
  --json evidence/cartoon-animation-program/checkpoints/program-validation.json
```

Validate one or more evidence records as part of the same gate:

```bash
python3 tools/validate_cartoon_animation_program.py \
  --root . \
  --evidence evidence/cartoon-animation-program/checkpoints/Q0.json
```

Normal repository and CI validation must not use `--skip-git-checks`. That option exists only for isolated test fixtures without a Git remote. A release report is not valid unless the validator confirms that the recorded planning commit exists, is an ancestor of `HEAD`, and is contained by the baseline branch's `origin` remote-tracking ref.

## Layout

Use stable, gate-oriented paths:

```text
evidence/cartoon-animation-program/
  checkpoints/     compact checkpoint and contract reports
  deterministic/   replay hashes and aggregate comparisons
  motion/          compact contact, root, marker, and transition summaries
  browser/         browser matrix summaries and selected small images
  soak/            aggregate performance and reliability summaries
  release/         final manifest, checksums, artifact links, and review
```

Do not commit empty placeholder directories. Create a directory when its first valid record is produced.

## Retention

| Evidence | Git | Workflow artifact | Retention |
|---|---|---|---:|
| Schemas, thresholds, scenario definitions | yes | optional | repository lifetime |
| Gate summaries, hashes, aggregate metrics | yes, under 5 MiB per file | optional | repository lifetime |
| Unit and JUnit logs | totals only | full logs | 14 days on PRs, 90 days on release |
| Replay traces | hashes and aggregate comparison | full trace | 30 days on PRs, 90 days on release |
| Browser screenshots | at most curated images under 2 MiB | full set | 14 days on PRs, 90 days on release |
| Browser recordings | no | yes | 14 days on PRs, 90 days on release |
| Raw RGB, frame dumps, and NDJSON | no | yes | 7 days on PRs, 30 days on release |
| Soak samples | aggregate JSON only | raw samples and logs | 14 days on PRs, 90 days on release |
| Final evidence bundle | index, hashes, and artifact URLs | full bundle | at least 90 days |

Files stored in Git must be deterministic, reviewable, and compact. Raw `.rgb`, `.ndjson`, and `.mp4` artifacts use `workflow_artifact` storage. The semantic validator rejects a Git artifact over 5 MiB and rejects raw capture formats declared as Git evidence.

## Failure Records

Do not erase failed evidence. Preserve the exact command result and artifact hash, set the top-level result to `failed` or `blocked`, record the residual risk, and link the replacement record from the coordinator ledger. A later pass does not rewrite the failed raw logs; it produces a new commit-bound record.

Evidence must not include prompts, private Prism content, retrieved text, memory bodies, secrets, tokens, machine-specific credentials, or unredacted user data. Prefer bounded metrics, stable error codes, hashes, and artifact URLs.
