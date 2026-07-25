# Serena G1 Governed Static Performance Evidence

Date: 2026-07-24

## Captures

| File | SHA-256 | Scope |
| --- | --- | --- |
| `observer-desktop-serena-mentoring.png` | `eaa3249fdcd38d624fc7a0f778a9988e4f0e653a11db766c2047262afe260ca7` | 1440x900 isolated observer with HD Wizard Joe and Serena mentoring pose |
| `observer-serena-mentoring.png` | `e6e7d9ca4a6a55cfca236d8f5aef4f30071128d96fd33eb44d1eb94c27b617f7` | Narrow observer layout with both character stages visible |

## Evidence Boundary

These captures prove the local review surface can display the canonical HD
Wizard sequence and Serena's admitted mentoring pose side by side. They do not
prove score admission, accessibility behavior, interruption, or replay by
themselves; those properties are covered by
`tests/wizard/test_serena_governed_score.py`.

The observer uses isolated child runtimes on ports 8666 and 8667. The protected
service on port 8765 was not restarted or replaced.
