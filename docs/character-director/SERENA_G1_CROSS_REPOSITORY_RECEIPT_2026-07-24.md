# Serena G1 Cross-Repository Receipt

Date: 2026-07-24

## Accepted Commits

- Wizard Joe Python Character Director:
  `ddd756e7` on `codex/character-director`
- Prism media connector:
  `19313bd` on `codex/character-director-prism`

Both commits are pushed to their respective GitHub remotes.

## Integrated Behavior

- The Python runtime rejects foreign character and package identities before
  coordinator mutation.
- Score-bound sessions require the exact active package and canonical
  compiled-score asset identities.
- Legacy scoreless V1 sessions remain compatible with a null package field.
- Prism resolves the active character and package from the existing
  performance-binding route.
- Main media and governed speech publish the same active identity.
- Runtime, character, and package changes reconcile without pausing browser
  playback.
- Failed, overlapping, stale, and destroyed binding refreshes are bounded,
  recoverable, and fail-closed.

No second connector, Python runtime, or media-session protocol was introduced.

## Verification

- Python focused review: 50 tests passed.
- Python broad regression: 176 tests passed.
- Prism media and governed-speech suite: 51 tests passed.
- Prism production Vite build: passed.
- Independent review: no P0-P2 findings in either repository.
- Local health after publication:
  - protected Wizard runtime `127.0.0.1:8765`: HTTP 200;
  - parity observer `127.0.0.1:8665`: HTTP 200;
  - Serena runtime `127.0.0.1:8667`: HTTP 200.

The protected 8765 process was not restarted or replaced. Unrelated untracked
pose and historical evidence remained untouched.

## Remaining G1 Work

This receipt closes the identity and connector foundation only. Serena static
score authoring, governed-speech generation/revocation precision, interruption
and accessibility scenarios, replay evidence, and eventual registry admission
remain separately gated.
