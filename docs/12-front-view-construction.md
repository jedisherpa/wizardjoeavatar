# Construct the Front View

Use these starting proportions in the 34 × 52 local grid.

## Hat

Hat brim:

```text
x: 6 through 28
y: 10 through 13
```

Hat crown silhouette, approximately:

```text
(8,10)
(9,5)
(13,2)
(17,0)
(22,2)
(27,6)
(25,10)
```

Add a drooping tip extending toward the viewer’s right.

Use:

- blue dark for shadow
- blue mid for body
- blue light for highlights
- gold and gold light for stars and brim

Do not distribute stars randomly at runtime.

Author a fixed, deliberate star pattern.

## Face

Main face:

```text
x: 10 through 24
y: 13 through 24
```

Ears:

```text
left:  x 8 through 10
right: x 24 through 26
```

Use darker skin on the sides and lighter skin in the center.

## Eyes and eyebrows

Eyes should be large enough to remain visible at reduced scale.

Place approximately:

```text
left eye center:  (13, 18)
right eye center: (21, 18)
```

Eyebrows:

```text
left eyebrow:  y 16
right eyebrow: y 16
```

## Beard

Beard silhouette:

```text
(9,21)
(25,21)
(25,27)
(22,32)
(18,35)
(14,34)
(10,30)
```

Use beard dark around the edge, beard mid internally, and beard light for highlights.

The beard must remain readable from all views.

## Robe

Robe base:

```text
top left:     (7,28)
top right:    (27,28)
bottom right: (29,47)
bottom left:  (5,47)
```

Inner robe:

```text
x: 14 through 20
y: 30 through 47
```

Use magenta for the inner robe.

Use one-cell gold trim around the opening.

Add a gold belt around y 35 with a central buckle.

## Arms

Shoulders:

```text
left:  (8,30)
right: (26,30)
```

Hands should end approximately around y 39–41 in idle.

## Boots

Left boot:

```text
x: 8 through 15
y: 47 through 51
```

Right boot:

```text
x: 19 through 26
y: 47 through 51
```

## Staff

The staff should appear on the viewer’s left in the canonical front pose, matching the design board.

Create:

- brown shaft
- curled top
- cyan orb
- small cyan spark cells for magic states

The staff must use a hand anchor rather than an absolute stage position.
