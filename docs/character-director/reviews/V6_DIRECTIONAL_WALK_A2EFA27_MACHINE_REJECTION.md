# V6 Directional Walk `a2efa27` Machine Rejection

Status: **REJECTED** before promotion

The clean, branch-bound V6 capture from candidate
`a2efa279f295bc8656274b78a42c4c7df6b9048a` retained 211 contiguous frames
with zero transport drops, but machine acceptance v3 failed. The evidence was
not copied into the accepted evidence tree.

## Blocking findings

1. Frames 41-45 presented a southeast head/eye layer over the still-front
   `walk_front_left_to_right` body graph. Full-size frame inspection confirmed
   visible face and edge debris; the contact sheet alone was not used to judge
   the defect.
2. The east-facing hold ended after only the first half of the directional gait
   cycle, so it did not prove all four authored profile-walk phases.
3. The 33-to-67-percent pivot step moved the staff tip by 17.64 stage cells and
   the grip by 16.81 stage cells in one presented frame, exceeding the V6
   continuity limits.

## Required correction

- make grounded whole-pose locomotion present the pose catalog's authored
  facing rather than allowing path-facing to lead the body;
- add deterministic east and west 50-percent planted pixel graphs between the
  existing 33- and 67-percent turn graphs;
- lengthen the east-facing scenario hold to record a complete gait cycle;
- regenerate the pose library, update its truthful capability totals, and
  recapture from a new clean commit.

This record exists so the failed candidate cannot later be mistaken for an
accepted V6 checkpoint.
