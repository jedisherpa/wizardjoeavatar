# Build a Joint Skeleton

Define local anchors:

```text
root / feet center
pelvis
chest
neck
head
left shoulder
left elbow
left wrist
right shoulder
right elbow
right wrist
left hip
left knee
left ankle
right hip
right knee
right ankle
staff hand
staff top
```

Example front-view anchors:

```python
ANCHORS_FRONT = {
    "root": (17, 51),
    "pelvis": (17, 39),
    "chest": (17, 30),
    "neck": (17, 26),
    "head": (17, 18),
    "left_shoulder": (8, 30),
    "left_elbow": (6, 35),
    "left_wrist": (7, 40),
    "right_shoulder": (26, 30),
    "right_elbow": (28, 35),
    "right_wrist": (27, 40),
    "left_hip": (13, 41),
    "left_knee": (12, 46),
    "left_ankle": (12, 49),
    "right_hip": (21, 41),
    "right_knee": (22, 46),
    "right_ankle": (22, 49),
    "staff_hand": (7, 37)
}
```

Define separate anchor sets for each canonical direction.

Draw limbs between joints using integer-grid line or polygon algorithms.

Use Bresenham-style cell segments and configured thickness.

Do not rotate raster arms.
