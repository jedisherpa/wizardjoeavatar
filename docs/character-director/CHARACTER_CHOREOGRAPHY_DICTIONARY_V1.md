# Character Choreography Dictionary V1

Date: 2026-07-27

## Purpose

A character package describes the art and motion it actually owns. Its
choreography dictionary describes how the Character Director may interpret that
specific vocabulary.

There is deliberately no global pose dictionary. Wizard Joe, Robin, Speech, the
Dragon, and the Kingfisher have broad performance libraries. Other JoeVille
characters currently have smaller, game-oriented libraries. Treating both
groups as interchangeable produces fabricated capabilities, repetitive acting,
and broken transitions.

The dictionary is a required, digest-bound package asset for admitted package
V2 characters. The loader verifies that every referenced pose, action, and clip
exists in that exact package.

## Library Classes

### Comprehensive Performance

Use for Wizard Joe, Robin, Speech, the Dragon, and the Kingfisher once each
canonical package is admitted.

- selection unit: phrase;
- transition policy: authored graph;
- speech motion: layered when the package supports simultaneous body and mouth
  motion;
- locomotion while speaking: allowed only when declared;
- unsupported intent: characterful neutral;
- repetition is controlled across multiple phrases; and
- gestures recover through an authored speaking or neutral intent.

The choreographer may select from semantic variants, but may never invent a
pose, clip, layer, or transition absent from the package.

### Focused Performance

Use for a character with deliberate listening and speaking coverage but without
a complete locomotion and acting repertoire.

- selection unit: beat;
- transition policy: neutral bridge;
- speech motion: whole-pose unless a layered speech channel is declared;
- locomotion while speaking: restricted; and
- unsupported intent: characterful neutral.

Serena Quill is the current reference package for this class.

### Game Motion

Use for compact libraries built primarily around controller actions.

- selection unit: command;
- transition policy: neutral bridge;
- speech motion: mouth-only or unsupported, exactly as declared;
- locomotion while speaking: restricted or unsupported;
- unsupported intent: default pose or reject; and
- gestures per phrase: zero unless the package explicitly provides a compatible
  action.

The Character Director must not map a missing acting intent to a vaguely similar
game move merely to keep the body busy.

## Contract Shape

```json
{
  "schema_version": 1,
  "dictionary_id": "choreography:character-v1",
  "character_id": "character-v1",
  "library_class": "comprehensive_performance",
  "instructions": {
    "selection_unit": "phrase",
    "transition_policy": "authored_graph",
    "speech_motion_policy": "layered",
    "locomotion_speech_policy": "allowed",
    "unsupported_intent_policy": "characterful_neutral",
    "repetition_window_ms": 12000,
    "minimum_stillness_ms": 700,
    "maximum_gestures_per_phrase": 2
  },
  "intent_bindings": {
    "neutral": {
      "roles": ["neutral", "recovery"],
      "pose_ids": ["front_idle"],
      "action_ids": ["idle"],
      "clip_ids": ["idle_front"],
      "speech_compatible": true,
      "interrupt_policy": "immediate",
      "minimum_hold_ms": 700,
      "recovery_intent": null
    }
  }
}
```

Objects are closed and JSON duplicate keys are rejected. Identifier, enum,
integer, ordering, uniqueness, required-intent, recovery-reference, and package
reference checks fail closed.

## Choreographer Rules

1. Resolve the current admitted package before interpreting an intent.
2. Load only the dictionary hash-bound to that package.
3. Select at the package's declared unit: phrase, beat, or command.
4. Filter candidates by speech compatibility and active channel restrictions.
5. Respect minimum holds and interrupt policy.
6. Follow authored transitions when available; otherwise use the declared
   neutral bridge.
7. Enforce stillness and repetition windows.
8. Recover through the binding's declared recovery intent.
9. Apply the declared unsupported-intent policy without cross-character
   borrowing.
10. Never use review-only art or another package's semantic map in production.

## Onboarding

For every character:

1. audit the exact package pose, action, clip, and layer IDs;
2. assign the honest library class;
3. author semantic bindings from those IDs only;
4. validate the dictionary against the package;
5. hash and add it as the package's `choreography_dictionary` asset;
6. run malformed, missing-reference, unsupported-intent, and determinism tests;
7. capture acting acceptance evidence appropriate to the library class; and
8. admit the package only after the dictionary and evidence pass review.

More source art can expand a dictionary later through a new package digest. It
must not silently widen the vocabulary of an already admitted package.

The current per-library classification and admission status is tracked in
`CHARACTER_LIBRARY_CHOREOGRAPHY_STATUS_2026-07-27.md`.
