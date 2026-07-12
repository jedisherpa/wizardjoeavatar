# Implement Independent Animation Channels

Do not use one mutually exclusive animation enum for everything.

Use these channels:

```text
locomotion:
  idle
  walk
  turn

upper_body_action:
  none
  explain
  point
  think
  cast
  react

face:
  expression
  blink

speech:
  mouth state
  speech timing

staff:
  held
  point
  cast
  rest
```

Resolve conflicts through priorities.

Example:

- walking controls legs and body bob
- explaining controls one arm
- speech controls mouth
- focused controls eyebrows
- staff channel controls the staff hand

This allows the wizard to walk, explain, and speak at the same time.
