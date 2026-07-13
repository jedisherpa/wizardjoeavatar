# Pose Integration Workflow

## Roles and write ownership

| Role | May edit | Must not edit |
|---|---|---|
| Coordinator | `POSE_TRACKER.md`, assignment fields, integration order | Candidate analysis owned by another agent without a handoff |
| Intake agent | Its assigned `items/WJP2-XX.md` and matching evidence directory | Manifest, generated library, another item record |
| Integrator | One claimed source PNG, manifest, selection/runtime code, focused tests | A second pose before the current pose reaches a terminal gate |
| QA agent | Matching evidence directory and QA section of the item record | Production code unless explicitly reassigned |

Agents are not alone in the repository. They must preserve concurrent work, avoid broad formatting or generated-file churn, and record every changed path in the item handoff.

## Status model

`QUEUED -> CLAIMED -> ANALYZED -> READY -> INTEGRATING -> GENERATED -> TESTED -> VERIFIED`

Terminal alternatives:

- `DUPLICATE`: materially duplicates an existing pose; record the matching pose and evidence.
- `REJECTED`: inconsistent character, unusable crop, missing anatomy, or no semantic runtime value; record the reason and evidence.
- `BLOCKED`: non-terminal; record the exact blocker and next operator action.

Only the coordinator changes the summary status in `POSE_TRACKER.md`. An agent proposes a status in its item record and returns a handoff. Only one item may be `INTEGRATING` at a time.

## Phase A: parallel intake

1. Claim one candidate ID in the tracker.
2. Extract only that candidate to a temporary inspection location or its evidence directory.
3. Inspect the full image and compare it with current poses.
4. Assign a stable semantic ID using `snake_case`, direction, action, locomotion, phase, and tags.
5. Identify subject bounds, baseline, root, eyes, mouth, hands, feet, staff hand, and staff tip.
6. Record character-consistency risks and whether the pose is a duplicate.
7. Produce a source preview and proposed canonical preview.
8. Move the item to `ANALYZED`, then request coordinator review for `READY`.

## Phase B: serial integration gate

1. Coordinator grants the integration lock by marking exactly one item `INTEGRATING`.
2. Run `python3 tools/integrate_pose_candidate.py <candidate-id>`; do not hand-edit multiple candidates together.
3. The transaction copies one approved source, adds exactly one Python pose-manifest entry, regenerates the canonical library, validates anchors, runs tests and the strict transition matrix, and records evidence.
4. Require deterministic repeat generation and confirm existing pose IDs remain unchanged except the new entry and aggregate metadata.
5. Record the generated library hash and changed paths in the item record.
6. On failure, require the operator's rollback and mark only that candidate `BLOCKED` with the exact failing gate.

## Phase C: independent QA

Required gates for each accepted pose:

- Deterministic generator passes twice with identical output.
- All required anchors exist and remain inside the canonical `72 x 96` canvas.
- The root remains `[36, 95]` and the character baseline does not jump.
- Face, staff, hands, feet, robe stripe, and wings remain coherent.
- Entry and exit transitions contain no severe speckling, tearing, double staff, floating facial features, or baseline snap.
- `python3 -m unittest discover tests` passes.
- `python3 tools/verify_animation_quality.py --strict` passes.
- Live browser evidence is captured at idle, entry midpoint, held pose, exit midpoint, and restored idle.

The QA agent records `PASS` or `FAIL` for every gate. A failed item returns to `READY` or `BLOCKED`; it does not advance to the next pose.

## Required handoff format

Every agent response must state:

- Candidate ID and proposed semantic ID.
- Previous status and proposed next status.
- Files changed.
- Evidence produced.
- Commands run and exact result.
- Risks, uncertainty, and the next operator action.

## Final program gate

After all candidates are terminal:

1. Regenerate the complete library deterministically.
2. Run all Python, ASCILINE, and browser verification required by the repository.
3. Run the strict transition matrix.
4. Render a contact sheet labeled with every accepted semantic pose ID.
5. Record a live motion reel that enters and exits every accepted pose.
6. Update the tracker totals and publish a final expansion report.

## Demo acceptance contract

The browser Play control must fetch the generated pose library at runtime, move the character continuously around the stage, and present every production pose in library order through the normal pose compositor. Adding a verified pose to the generated library must automatically add it to the next demo run. The demo must not teleport the character between poses, replace the stream with prerecorded media, or maintain a separate hardcoded pose list.
