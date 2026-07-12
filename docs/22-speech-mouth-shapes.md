# Implement Speech Mouth Shapes

Create:

```text
closed
open_small
open_medium
open_wide
rounded
smile
frown
```

The mouth layer must sit between the beard and nose layers.

Use provider timing in this order:

1. viseme timing
2. phoneme timing
3. word timing
4. audio amplitude
5. deterministic fallback cycle

The mouth must:

- open when speech begins
- close during meaningful silence
- stop immediately when interrupted
- return to neutral when speech ends

The wizard must be capable of walking and speaking simultaneously.

Locomotion and speech must be separate animation channels.
