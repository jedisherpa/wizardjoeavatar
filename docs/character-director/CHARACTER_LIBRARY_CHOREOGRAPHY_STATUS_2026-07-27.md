# Character Library Choreography Status

Date: 2026-07-27

## Decision

Every character library owns a separate choreography dictionary. A dictionary
is an interpretation contract for one exact library, not a universal list of
pose names.

The current corpus has three materially different shapes:

- **comprehensive performance** libraries support broad acting, speech,
  locomotion, and transition selection;
- **focused performance** libraries support a deliberately narrower set of
  speaking and listening beats; and
- **game motion** libraries expose controller-oriented cycles and must not be
  treated as general acting vocabularies.

The Character Director must resolve the active admitted character package,
load only that package's digest-bound dictionary, and apply the instructions in
that dictionary. It must never borrow semantics from another character.

## Current Inventory

| Library | Intended class | Current usable scope | Dictionary/package status |
| --- | --- | --- | --- |
| Wizard Joe production package | comprehensive performance | 236 poses, 162 graph-bound poses, 15 actions, 40 clips | Admitted package has a required, digest-bound dictionary. |
| Wizard Joe HD source library | comprehensive performance | 308 reviewed source poses | Remains source/review material until represented by an admitted package with exact IDs. |
| Robin | comprehensive performance | 200 graph-bound candidate poses, 15 actions, 28 clips | Reproducible V2 candidate builder emits its own package-bound dictionary; candidate output remains review-only. |
| Speech | comprehensive performance | 200 graph-bound candidate poses, 15 actions, 28 clips | Reproducible V2 candidate builder emits its own package-bound dictionary; candidate output remains review-only. |
| Dragon | comprehensive performance | 134 graph-bound review poses, including 15 flight poses, 31 speech poses, and 24 storytelling poses | Reproducible V2 review-candidate package and digest-bound dictionary now exist. The package remains unapproved, `runtime_admitted: false`, and outside the production registry. |
| Kingfisher | comprehensive performance | 176-pose review candidate with 88 exact resting/speaking pairs | Reproducible V2 candidate package and digest-bound dictionary exist; runtime profile V3 preserves each authored body pose while switching beak mates. Candidate remains review-only with 0 user approvals and no registry admission. |
| Serena Quill production candidate | focused performance | 108 poses, 79 graph-bound poses, 15 actions, 79 clips | V2 package contains its own focused-performance dictionary. |
| Serena Quill 48-pose parity review library | game motion | 48 controller-oriented review poses | Own review-only game dictionary. This is a different library from Serena's focused V2 package. |
| Aurelia Finch | game motion | 48 review poses | Own review-only game dictionary. |
| Draven Holt | game motion | 48 review poses | Own review-only game dictionary. |
| Elara Voss | game motion | 48 review poses | Own review-only game dictionary. |
| Finn Calder | game motion | 48 review poses | Own review-only game dictionary. |
| Kai Renner | game motion | 48 review poses | Own review-only game dictionary. |
| Liora Kane | game motion | 48 review poses | Own review-only game dictionary. |
| Mira Solen | game motion | 48 review poses | Own review-only game dictionary. |
| Orion Vale | game motion | 48 review poses | Own review-only game dictionary. |
| Rohan Slate | game motion | 48 review poses | Own review-only game dictionary. |
| Selene Hart | game motion | 48 review poses | Own review-only game dictionary. |
| Thorne Vale | game motion | 48 review poses | Own review-only game dictionary. |
| Liana | game motion | 48 motion poses plus separate identity references | Own review-only game dictionary. |

Counts describe the checked-out artifacts and are not production-admission
claims. Review-only dictionaries make the current limitations explicit; they
do not turn review libraries into admitted runtime packages.

## Interpretation Rules By Class

### Comprehensive Performance

- Interpret at phrase scale.
- Select among authored semantic variants.
- Permit speech/body layering only when the package declares compatible
  channels.
- Permit speech during locomotion only when declared.
- Use authored graph transitions and authored recovery intents.
- Apply repetition windows, stillness, and gesture-density limits.
- Fall back to a characterful neutral rather than an unrelated action.

### Focused Performance

- Interpret at beat scale.
- Prefer speaking, listening, reaction, and neutral beats.
- Use a neutral bridge when no authored transition exists.
- Restrict simultaneous locomotion and speech.
- Reject or neutralize intents outside the focused vocabulary.

### Game Motion

- Interpret at command scale.
- Treat the library as a controller cycle, not an acting repertoire.
- Do not infer speech gestures, facial acting, or conversational locomotion.
- Use the authored first pose as neutral/recovery.
- Use only local pose IDs and a neutral bridge.
- Resolve unsupported acting intents to the declared default pose.

## Production Gates

1. Freeze stable pose, action, clip, and layer IDs for the exact library.
2. Author semantic bindings using only those IDs.
3. Validate closed fields, duplicate keys, sorted uniqueness, recovery
   references, and package membership.
4. Hash the dictionary and include it as the package's
   `choreography_dictionary` asset.
5. Run class-specific acting acceptance:
   comprehensive phrase performance, focused beat performance, or game command
   determinism.
6. Admit a new package digest. Never widen an existing digest in place.

Dragon and Kingfisher remain correctly classified as comprehensive libraries,
but neither should be production-admitted from this tracking document alone.
Both now have exact review-candidate package identities and local dictionaries;
neither package has completed the independent visual, approval, governance, or
registry-admission gates. Review-candidate execution does not confer production
authority.
