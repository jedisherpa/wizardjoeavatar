# Dragon Interim 48-Pose Plan

Date: 2026-07-27

## Decision

The original smallest useful Dragon expansion was 12 poses. The user then
requested twelve additional flight-performance poses. The user subsequently
requested 24 combined hand-and-mouth storytelling poses.
The locked interim expansion is therefore 48 poses, raising the currently
projectable set from 86 to 134 without pretending to replace the later full
corpus.

The current source already covers:

- seven-direction staging once the damaged right three-quarter view is repaired;
- listening, explanation, presentation, counting, reassurance, and interruption;
- a broad emotional range;
- interface and object interaction;
- a four-pose bidirectional walk;
- jump-compatible compression, spread, and ready poses.

The material gaps are one damaged directional pair, three damaged semantic
poses, a second run phase, sustained flight, and mouth articulation.

## Required Poses

| Asset | Purpose | Production method |
| --- | --- | --- |
| `CAN007` | canonical front three-quarter right | deterministic mirror of `CAN002` |
| `ACT007` | acting front three-quarter right | deterministic mirror of `ACT002` |
| `ACT032` | cause and effect | identity-locked generated candidate |
| `ACT044` | excitement | identity-locked generated candidate |
| `ACT060` | fatigue | identity-locked generated candidate |
| `ACT081` | run passing phase | identity-locked generated candidate |
| `ACT082` | flight downstroke | identity-locked generated candidate |
| `ACT083` | flight upstroke | identity-locked generated candidate |
| `ACT084` | glide or hover | identity-locked generated candidate |
| `ACT085` | speech, small open mouth | identity-locked generated candidate |
| `ACT086` | speech, wide open mouth | identity-locked generated candidate |
| `ACT087` | speech, rounded mouth | identity-locked generated candidate |
| `ACT088` | flight bank left | identity-locked generated candidate |
| `ACT089` | flight bank right | identity-locked generated candidate |
| `ACT090` | flight ascend | identity-locked generated candidate |
| `ACT091` | flight descend | identity-locked generated candidate |
| `ACT092` | flight brake | identity-locked generated candidate |
| `ACT093` | flight takeoff | identity-locked generated candidate |
| `ACT094` | flight landing | identity-locked generated candidate |
| `ACT095` | hover listening | identity-locked generated candidate |
| `ACT096` | hover speech, small open | identity-locked generated candidate |
| `ACT097` | hover speech, wide open | identity-locked generated candidate |
| `ACT098` | hover speech, rounded | identity-locked generated candidate |
| `ACT099` | hover emphatic speaking | identity-locked generated candidate |
| `ACT100`-`ACT123` | combined storytelling hand and mouth performances | identity-locked generated candidates |

## Intentional Reuse

No new interim jump frames are required:

- anticipation: `CAN011` maximum compression;
- airborne apex: `CAN010` maximum spread;
- landing and recovery: `ACT010` ready stance.

No additional turn frames are required. The canonical view ring supplies the
turn sequence after `CAN007` is repaired.

No closed-mouth speech frame is required. `CAN001` and `ACT001` provide the
rest closure.

## Candidate Contract

Every new frame must:

- preserve the approved Dragon identity, palette, proportions, materials, and
  eye design;
- contain one complete character with no crop damage;
- use a 1920 x 1080 RGBA canvas;
- have transparent corners and zero RGB beneath transparent pixels;
- remain a review candidate;
- remain `runtime_admitted: false`;
- record source references, prompt, generation method, source hash, alpha hash,
  visible bounds, and opaque-pixel count;
- pass a full-size visual review before entering any package;
- pass motion-order review with its neighboring poses before sequence use.

The interim set is not a substitute for the later full Dragon corpus.

## 2026-07-27 Build Checkpoint

- Built all 48 interim candidates: two deterministic mirrors and 46
  identity-locked generated candidates.
- Added 24 simultaneous hand-and-mouth storytelling poses as `ACT100` through
  `ACT123`.
- Extracted every generated source through the standard chroma-key helper and
  normalized each result to a 1920 x 1080 RGBA canvas.
- Verified binary alpha, zero RGB beneath transparent pixels, transparent
  corners, nonempty silhouettes, and non-contact with all four canvas edges.
- Compiled a 134-pose full-resolution review projection containing 84 validated
  source frames and 50 explicitly unapproved candidates.
- Preserved `runtime_admitted: false` at manifest, shard, index, sequence, and
  acceptance-audit levels.
- Passed 12 focused deterministic, provenance, fail-closed, and byte-exact
  reconstruction tests.
- Verified the persistent observer at `http://127.0.0.1:8665/` and the Dragon
  review runtime at `http://127.0.0.1:8667/`.

Visual evidence:

- `docs/character-director/reviews/dragon-storytelling-act100-123-contact-2026-07-27.png`

## 2026-08-07 Runtime-Candidate Checkpoint

The 134-pose review corpus now compiles through the shared HD RGBA character
package builder. The generated package is deterministic, digest-bound, and
loadable by the existing Python `HDPoseFrameSource`; it remains a review
candidate and is not registered for production runtime use.

The candidate defines:

- 15 flight poses;
- a three-pose grounded speech cycle;
- a five-pose hover/listen/speech group;
- a 24-pose storytelling speech group;
- three explicit resting-to-speaking pose pairs;
- a Dragon-owned comprehensive-performance choreography dictionary; and
- named full-corpus, flight, grounded-speech, hover-speech, and storytelling
  review sequences.

The isolated desktop and mobile-landscape review showed complete silhouettes,
working alpha projection, and no browser errors. Portrait projection remains
legible but too small because the current review stage preserves a 16:9 source
canvas inside a tall viewport. That is a presentation-adaptation limitation,
not a source-art or package-admission success claim.

Exact receipt and conservative gate:

- package SHA-256:
  `sha256:2a23fc9ae5379e6489a9b52e34297d9e78250f09b9968df43f9e7493caff5d02`;
- source/candidate library-index SHA-256:
  `301ce8dfda7547a48f8fe85960bd79cfb18453374f20e07bbb4faeba042f24ac`;
- 22 Dragon-focused tests passed;
- nine shared Robin/Speech HD RGBA regression tests passed; and
- `runtime_admitted` remains `false` throughout the review index and package.

See `DRAGON_RUNTIME_CANDIDATE_2026-08-07.md` for the exact package contract,
verification commands, review URLs, and unresolved gates.
