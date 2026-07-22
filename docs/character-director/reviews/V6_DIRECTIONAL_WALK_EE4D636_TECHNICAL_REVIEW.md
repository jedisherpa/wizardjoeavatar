# Character Director V6 Directional Walk Technical Review

**Candidate:** `ee4d6360a169fab91f9680c7e0c12248fa439e49`  
**Candidate tree:** `86bbc8e857e9919e6b0e499da462c218f3591770`  
**Clean proof checkout:** `/tmp/wizardjoe-v6-proof-ee4d636`  
**Immutable evidence:** `/tmp/v6-capture-ee4d636`  
**Review role:** Independent senior real-time animation systems and evidence reviewer  
**Decision:** **FAIL - V6 MUST REMAIN OPEN**

## Executive Decision

Candidate `ee4d636` is a materially better and technically credible resubmission.
The proof checkout is clean and exactly bound to the pushed candidate. The
capture manifest, review bundle, retained frame stream, truth trace, contact
report, machine report, normal-speed video, quarter-speed derivative, and
browser evidence all pass their integrity checks. Re-running machine acceptance
from the clean checkout produces a byte-identical green report, and 119 focused
tests pass.

Those results do not establish V6 acceptance. The retained trace, graph data,
and media show three release-blocking defects:

1. `presented_facing` advances ahead of the rendered body during the 90-degree
   turn. The V6 analyzer checks the facing labels and the pose IDs separately,
   but never checks that a rendered pose's authored facing agrees with the
   presented sector.
2. The authored turn graphs contain very large adjacent staff/grip construction
   changes at the two most important pivot boundaries. Contact locking holds the
   foot, but the staff-hand-body package visibly pops around that foot.
3. `stop_left` is not an authored stopping performance. It substitutes the
   static `profile_left` graph for eight frames and then enters an identical
   idle hold. The current gate accepts the clip label, target arrival, and idle
   suffix without requiring visible braking or recovery.

The machine gate can therefore false-pass exactly the kinds of visible defects
that remain in this candidate. The immutable proof is valid evidence of a
failed V6 performance, not evidence that V6 has passed.

## Provenance And Clean Binding

### Result: PASS

- Proof `HEAD` is the full candidate SHA
  `ee4d6360a169fab91f9680c7e0c12248fa439e49`.
- Proof `HEAD^{tree}` is
  `86bbc8e857e9919e6b0e499da462c218f3591770`.
- `origin/codex/character-director` resolves to the same full candidate SHA.
- `git status --porcelain=v1 --untracked-files=all` is empty in the proof
  checkout.
- `git fsck --no-dangling --no-progress` and `git diff --check HEAD^ HEAD`
  complete without errors.
- The capture manifest records the same head and tree at capture start and end,
  with an empty status hash and tracked-diff hash equal to the SHA-256 of an
  empty byte stream.
- Runtime binding is verified at both ends of capture and identifies the clean
  proof branch, launcher hash, Python executable/hash, 240x135 logical raster,
  24 FPS rate, port 8928, and one runtime epoch.
- `/tmp` and `/private/tmp` resolve to the same macOS temporary-file namespace;
  the absolute `/private/tmp/wizardjoe-v6-proof-ee4d636` path retained by the
  runtime identity is consistent with the supplied `/tmp` checkout.

The evidence is not bound to a dirty developer checkout or an unpushed local
commit.

## Capture Manifest And Review Bundle

### Result: PASS

The strict capture validator and strict version-2 review-bundle validator both
pass directly from the candidate checkout.

The capture contains:

- 210 contiguous frames, indexes 0 through 209;
- 210 capture-owned frames and zero unowned frames;
- 210 `animation_truth_trace_v1` records;
- the exact five-scenario V6 program and expected 8.75-second duration;
- 137 hash-bound capture artifacts;
- a 960x540 H.264 normal-speed video, 210 frames at 24 FPS;
- no capture validation errors.

The review bundle is complete and binds exactly one artifact for each required
role: machine acceptance, quarter speed, and browser layout. Its candidate,
run ID, capture-manifest hash, artifact sizes, artifact hashes, source paths,
and source hashes all validate.

Important artifact hashes:

| Artifact | SHA-256 |
| --- | --- |
| Capture manifest | `b826efe162150a67e2ee9407b92ca75077b56a215e59cb5f2c8988e991597f9b` |
| Review-bundle manifest | `74e84bc27494d7aec65a641eb6e0238dbe51f656b2d1326920f97cd213674c35` |
| Truth trace | `8e4d51dc8e624a5cb1c44db6420e1631b23e8cffdc5f6703cab3c5dd0428672c` |
| Contact report | `4671ba85c61ead0543ba1c72c31401b7fe8664261093177b5806bceb31d96307` |
| Machine acceptance | `97cf31afebdf81380228c167f278abe3df74e6944edd1a8758900f803c42d838` |
| Normal-speed video | `1fa56a03975f7e92811102969a7638974c8602577cddabedc99664054666c503` |
| Quarter-speed video | `b0026e55e1d50686caae4d94ab7454606ea4e1c8eaa965521ae826711d54463a` |
| Browser metrics | `c9dc2d0513fa4dc291c5e979ae32ee58498cb4997d065bc550c84057c4020c3b` |
| Browser video | `32aac59e411e6616f9bc171107d2778e52d6b4b04452d2093b221da8ba426c45` |
| Contact sheet | `ea320f219815950fe2d8882f6718889cb79663d8fb3eb5c957d6ec5882a95d23` |

## Machine Acceptance V2

### Reproduction: PASS

`tools/analyze_character_director_v6.py` validates the immutable manifest and
recomputes `v6-machine-acceptance.json` byte for byte. Both retained and
recomputed reports hash to:

`97cf31afebdf81380228c167f278abe3df74e6944edd1a8758900f803c42d838`

All 12 machine checks are green. They correctly prove scenario identity/order,
capture continuity, command response, facing-label sector progression, four
named profile phases per side, named turn/reversal topology, support-label
alternation, contact/root limits, exact target arrival, static suffix, and
stage containment.

### Acceptance strength: FAIL

The report's own `review_boundary` correctly says that machine checks do not
replace review of anticipation, weight, silhouette readability, reversal, and
foot skating. Three implementation details make that limitation release
significant:

1. `readable_90_degree_turn` and `readable_180_degree_reversal` inspect only
   `presented_facing` labels and simulation-tick spacing.
2. `authored_turn_reversal_pose_topology` compares only collapsed pose ID
   strings. It never resolves those IDs to pixel graphs or authored facing.
3. `target_stop_and_profile_settle` requires the `stop_left` clip to appear and
   an `idle_left/profile_left` suffix to hold. It does not require a distinct
   stopping graph or visible deceleration phrase.

The V2 unit fixture also contains no decoded pixel graphs. A candidate can pass
with the expected IDs while their pixel content is identical, minimally
different, incorrectly oriented, or discontinuous. The separate pose-library
test proves four JSON cell arrays differ and their anchors occupy colored
cells, but it does not implement the resubmission design's raster-derived boot
lead/clearance, rigid-translation rejection, pose-facing agreement, staff/grip
continuity, wing continuity, or authored stop gates.

This is a concrete false-pass risk, not a theoretical concern: this exact
candidate passes while the mismatches below remain present in immutable proof.

## Blocking Findings

### [High] Presented facing and rendered orientation disagree during the accepted turn

Resolving each retained `rendered_pose_id` against
`reference_avatar_pose_cells.json` finds 24 mismatched motion frames between
frames 36 and 168. The decisive 90-degree section is:

| Frames | Presented facing | Authored pose facing | Rendered pose |
| --- | --- | --- | --- |
| 41-44 | southeast | south | `walk_front_left_to_right` |
| 45 | east | south | `walk_front_left_to_right` |
| 46-47 | east | southeast | `walk_front_right` |
| 48-50 | east | southeast | `turn_south_east_33` |
| 51-53 | east | southeast | `turn_south_east_67` |
| 54 onward | east | east | `walk_profile_right_contact_left` |

The character's state claims the turn before the chest, face, wings, and staff
have reached that orientation. The machine turn check is green because the
labels progress `south -> southeast -> east`; the topology check is green
because the expected pose names appear later. Neither check compares the two.

The reversal is much better staged, but it also contains smaller timing
disagreements at frames 81-82, 87, 91-92, and 97. This violates the explicit V6
resubmission contract that rendered graph orientation agree with every
`presented_facing` sector.

**Required correction:** drive `presented_facing` from the authored turn sample
actually being rendered, or retime the turn samples so state and body agree on
every accepted frame. Add a machine check that resolves pose IDs through the
candidate pose library and fails any unapproved facing mismatch.

### [High] Contact locking hides large staff/grip construction jumps

The 90-degree boundary from frame 47 to 48 changes
`walk_front_right -> turn_south_east_33`. In source-graph coordinates:

- staff tip changes from `[14,12]` to `[61,9]`, delta `[+47,-3]`;
- staff grip changes from `[16,50]` to `[53,51]`, delta `[+37,+1]`;
- relative to the planted right foot, the tip still changes by `[+32,-3]` and
  the grip by `[+22,+1]`.

The reversal boundary from frame 90 to 91 changes
`turn_front_crossover_plant -> turn_south_west_33`:

- staff tip delta is `[-38,+5]`;
- staff grip delta is `[-36,+6]`;
- relative to the planted left foot, the tip changes by `[-29,+5]` and the
  grip by `[-27,+6]`.

Root-aligned occupancy IoU remains above the proposed 0.55 floor at these
boundaries (`0.6299` and `0.5728` respectively), so a whole-silhouette overlap
threshold alone does not catch the prop teleport. Normal and quarter-speed
media visibly confirm the staff/hand/torso package popping around the locked
foot.

The contact report correctly verifies the declared foot and world-root math;
it does not verify a continuous staff path. The machine topology check accepts
these same boundaries because the pose IDs are in the expected order.

**Required correction:** normalize adjacent turn graphs around both planted
foot and physical staff grip, add intermediate staff placements where needed,
and gate adjacent grip/tip displacement after contact-root resolution. Recheck
wing and robe occlusion at the same boundaries.

### [High] The stop gate accepts a static substitution as a stopping performance

The final west stride renders
`walk_profile_left_passing_left_to_right` through frame 160. Frame 161 changes
directly to `stop_left/profile_left`. Frames 161-168 all render that same
static profile graph; only support metadata changes from `right_foot` to
`both_feet`. Frame 169 enters `idle_left/profile_left`, which is visually
identical, and frames 169-209 remain an exact hold.

Target error is genuinely zero and the stopped root genuinely remains fixed.
What is absent is a braking plant, shortened step, compression, robe/wing
follow-through, staff recovery, or rebound into idle. Machine acceptance
records 49 zero-speed suffix frames and calls this a pass because it evaluates
the destination and labels, not the stopping action.

**Required correction:** author a short `stop_left` phrase selected from the
actual incoming gait phase, preserve the target and planted support, and show
visible absorption and recovery before `profile_left` idle. Add a topology gate
requiring at least one distinct authored stop drawing and a negative test where
every stop sample is `profile_left`.

## Contact And Root Evidence

### Result: PASS for declared contact arithmetic; not a complete visual-motion gate

The contact report contains 210 frames, 190 contact-bearing frames, and 18
stances with no issues. Maximum planted-anchor drift is
`2.842170943040401e-14` cells, maximum decoded-raster-span drift is one cell,
and maximum root residual is zero. The machine report independently limits the
largest world-root step to `0.06250000000000044`, reports exact arrival at
`[-2.4,3.8]`, and finds no stage clipping.

The verifier uses decoded raster evidence and rejects missing/blank planted
spans in strict mode. It also enforces alternating single-foot stance labels
within locomotion phrases. Those are meaningful improvements over the rejected
V6 proof.

The verifier cannot establish that a visible free leg passes correctly, that a
declared left/right foot component is anatomically the intended component, or
that staff/wing/robe motion is continuous. A static pose can also change
support labels during `stop_left` because stop clips are outside the default
locomotion set. The green contact report must therefore remain scoped to
contact/root integrity.

## Media And Browser Evidence

### Normal and quarter speed: PASS for integrity and linkage

- Normal: 960x540 H.264, 24 FPS, 210 frames, 8.75 seconds.
- Quarter speed: 960x540 H.264, 24 FPS, 840 frames, 35.00 seconds.
- Time-compressing the quarter-speed video by four and comparing it to the
  normal video yields aggregate SSIM `0.998841`. The derivative is therefore a
  genuine slowed presentation of the retained normal capture, not merely a
  hash record pointing at an unrelated video.
- The contact sheet and event samples cover the gait, 90-degree turn,
  reversal, and stop boundaries. The retained media exposes rather than hides
  the findings above.

The review-bundle validator binds the quarter-speed artifact to the normal
video's path and hash, but does not itself derive or decode-compare the two.
The independent SSIM check closes that evidentiary gap for this bundle only.

### Browser layout: PASS as layout/delivery evidence, not frame-exact animation evidence

The browser video is 1280x634, 24 FPS, 210 frames, and 8.75 seconds. The 240x135
logical canvas is shown at 960x540 with a matching 960x540 backing store. There
are no page or console errors, decode errors, raw-message drops, decoder drops,
or resyncs. Queue high-water marks remain bounded.

The client presents 192 frames at 22.682 FPS during the sampled interval, with
21 held frames, 57 duplicate screencast samples, and 173 screencast events.
That is sufficient to demonstrate stable layout and usable delivery, but not
to replace the frame-exact normal capture and truth trace.

The version-2 bundle validator does not require zero `droppedFrames`, zero
`rawMessagesDropped`, zero resyncs, a minimum presented FPS, or complete
presented-frame coverage. A future browser run could regress those fields and
still validate if dimensions, expected output video frame count, decode-error
count, and page errors remain acceptable. This is another false-pass surface
to close before integrated production acceptance.

## Graph And Runtime Topology

### Prior rigid gait failure: RESOLVED

Each side now has four authored `_v2.png`-derived pixel graphs with different
cell arrays and phases `0.0`, `0.25`, `0.5`, and `0.75`. The rejected
`profile_*` plus one-cell translated `walk_profile_*_passing` pair is not
observed by the V6 runtime. The retained trace completes the expected four-pose
right cycle and repeatedly completes the four-pose left cycle. The media reads
as actual opposing leg shapes rather than a rigid vertical bob.

### Prior hard-cut reversal failure: RESOLVED at topology level

The retained 90-degree phrase traverses:

`walk_front_right -> turn_south_east_33 -> turn_south_east_67 -> walk_profile_right_contact_left`.

The retained reversal traverses:

`walk_profile_right_contact_right -> turn_south_east_67 -> turn_south_east_33 -> turn_front_crossover_plant -> turn_south_west_33 -> turn_south_west_67 -> walk_profile_left_contact_left`.

There is no direct adjacent full-right-profile to full-left-profile
substitution. The remaining failure is timing and physical continuity, not
absence of authored turn states.

### Runtime routing: PASS for the captured scenario

The animation graph includes dedicated left/right gait, front-to-side turn,
east/west reversal, and side stop nodes. Transition clips are uninterruptible,
contact locked, and have explicit legal successors. The captured runtime uses
the authored clips in the expected order, preserves gait phase across the
turn/reversal handoffs, reaches the target, and resets into a stable idle.

This proof exercises front-to-east and east-to-west only. The graph contains
the mirrored west-to-east and front-to-west paths, and focused tests cover
their selection, but immutable V6 media does not visually prove those mirrored
paths.

## Tests And Determinism

### Result: PASS within reviewed scope

The following focused suite passes from the clean proof checkout:

```text
python3 -m unittest \
  tests.wizard.test_character_director_v6_acceptance \
  tests.wizard.test_contact_verifier \
  tests.wizard.test_pose_selection \
  tests.wizard.test_frame_source \
  tests.wizard.test_locomotion \
  tests.wizard.test_pathing \
  tests.wizard.test_reference_avatar_pose_library \
  tests.wizard.test_character_director_visual_review

Ran 119 tests: PASS
```

Deterministic authored-cell generation also passes:

```text
python3 tools/generate_reference_avatar_pose_cells.py \
  --check-deterministic --reuse-authored-library
```

The generated library reports 173 poses and SHA-256
`0c64be06c55e11d4eb3fd633aed5f802ebdd1f15e64dd5e03ec92b1f14cfba00`.

No skipped or expected-failure test was used to reach this result. The focused
suite does not erase the machine-gate omissions documented above.

## Protected Unrelated Evidence

### Result: PASS

The unrelated V3 evidence directory
`evidence/character-director/v3-canonical-cast-a063993-2026-07-19/` remains
untracked in the canonical worktree. The three unrelated untracked turn source
crops also remain present. No path under that V3 evidence directory appears in
the candidate's final commit diff, and this review did not stage, delete,
rewrite, or otherwise alter those files.

The proof checkout itself remains clean after all review commands.

## False-Pass Audit Summary

| Gate | What it proves | False-pass remaining |
| --- | --- | --- |
| Strict capture manifest | Hashes, frame/trace pairing, provenance, scenario ownership, runtime binding | Does not judge animation quality. |
| Review bundle v2 | Hashes and source linkage for machine, slow, and browser artifacts | Does not decode-compare the slow derivative; browser thresholds omit several delivery fields. |
| V6 facing checks | Ordered sector labels with bounded per-tick change | Does not compare sector labels with rendered graph orientation. |
| V6 topology checks | Expected pose ID order appears | Does not resolve or compare pixel content, anchors, or prop paths. |
| Directional gait check | One expected four-ID cycle appears per side | Does not derive visible boot lead/clearance or reject minimally different impostor graphs. |
| Contact verifier | Declared anchor/root lock, decoded foreground span, stance-label alternation | Does not prove anatomy, free-leg motion, or prop/robe/wing continuity. |
| Stop/settle check | Target, stop clip label, zero-speed suffix, idle endpoint | Accepts a static profile substitution with no authored stop action. |

## Resubmission Requirements

1. Align `presented_facing` with the authored facing of every rendered turn
   sample; add a graph-resolved negative test.
2. Normalize the two pivot boundaries around planted foot and staff grip, then
   add bounded grip/tip continuity checks using resolved output coordinates.
3. Author a visible side-stop absorption and recovery phrase selected from the
   incoming gait phase; reject stop clips made entirely of the idle profile.
4. Preserve the current four-phase gait, contact drift, root-step, exact-target,
   stage-fit, deterministic generation, and immutable evidence results.
5. Recapture normal, quarter-speed, browser, trace, contact, and event samples
   from a new clean pushed commit and repeat both independent reviews.

## Final Verdict

**FAIL.** Candidate `ee4d636` conclusively fixes the rejected V6 submission's
rigid two-pose side glide and direct profile-swap reversal. Its provenance,
evidence integrity, four-phase gait, authored directional topology, contact
lock, target arrival, framing, browser stability, tests, and deterministic
generation are credible.

V6 still cannot be accepted because body orientation temporarily contradicts
presented facing, staff/grip continuity breaks at the authored pivot
boundaries, and the stop is a static endpoint substitution rather than a
performed settle. Machine acceptance v2 passes all three defects. V6 remains
open until a new clean candidate and immutable proof resolve them.
