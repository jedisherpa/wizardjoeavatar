# Wizard Joe Companion Verification Evidence

Updated: 2026-07-14

## Source Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| Python full suite | passed | `264` tests, `unittest discover -s tests`, 156.477 s |
| Companion frontend | passed | `17` Node tests |
| Companion Rust | passed | `12` tests |
| Companion formatting | passed | `cargo fmt --check` |
| Companion lint | passed | strict `cargo clippy --all-targets -- -D warnings` |
| Prism media connector | passed | `21` focused Node tests |
| Prism production frontend | passed | Vite build; existing >500 kB chunk warning only |
| Prism Rust workspace | passed | locked workspace, including `275` CLI and `662` core tests plus integration/doc suites |

## Source-Level Acceptance

| Requirement | Status | Evidence |
| --- | --- | --- |
| App-control and media credentials are separate | verified | Lifecycle tests and discovery serialization test |
| Frontend never receives a credential | verified | Descriptor/event tests; URL credential support removed |
| Dynamic literal-loopback port | verified | Port selection and URL validation tests |
| Private, expiring, ownership-checked discovery | verified | Rust publication and Prism validation tests |
| Either launch order and runtime rotation | verified in integration tests | Prism discovery refresh test |
| Bounded child recovery | verified | 250/500/1000/2000 ms policy; four crashes per 60 s |
| Graceful authenticated shutdown | verified at component level | Shell and Python runner/server tests |
| Stale/error acknowledgements cannot present healthy | verified | Prism connector and Companion state tests |
| Analyzer failure preserves the audible media graph | verified | Prism Web Audio tests |
| Speech clock progresses beyond mouth threshold | verified | AudioBuffer and synthesis monotonic-clock tests |
| Speech preempts main and pause/end/error restores main | verified | Prism media-session tests |
| Reaction pause preserves the media clock | verified | Python performance tests |
| Stage shortcuts do not capture unrelated controls | verified | Companion frontend tests |

## Draft Packaging

A draft unsigned local bundle was produced at 81 MB after narrowing packaged
resources to runtime definitions, legacy web assets, and the motion manifest.
It was built from a dirty implementation tree and is build feedback, not the
final provenance artifact. The first clean copy exposed a missing bundle
resource envelope when launched from Applications; the build now applies and
strictly verifies a local ad-hoc bundle signature before acceptance.

## Packaged-Runtime Matrix

| Scenario | Status | Required evidence |
| --- | --- | --- |
| Launch outside repository without terminal/server | pending | App window, app-owned child, ready state |
| Existing 8765 service remains untouched | pending | Before/after PID and listener identity |
| Single instance | pending | Two launches, one app process, one child |
| Discovery permissions/freshness/redaction | pending | Safe metadata inspection without credential output |
| Child crash and bounded recovery | pending | PID/runtime epoch rotation and ready recovery |
| Graceful quit/no orphan/discovery cleanup | pending | Process and file inspection |
| Companion first, Prism second | pending | Fresh accepted media acknowledgements |
| Prism first, Companion second | pending | Automatic transition from unavailable to ready |
| Main music/podcast/audiobook | pending | Audible playback and source/motion evidence |
| Persona speech | pending | Audible speech plus changing non-closed mouth samples |
| Speech preemption/restoration | pending | Main -> speech -> main state sequence |
| Independent verifier | pending | Separate report against clean artifact |

The user has manually confirmed that the physical speakers and audible output
are working. That does not replace packaged persona-mouth evidence.
