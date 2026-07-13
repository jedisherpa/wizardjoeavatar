# Runtime Grouping Plan

Scope: read-only showcase map for non-duplicate pose-expansion candidates in `POSE_TRACKER.md` as of the 2026-07-12 coordinator update. This plan does not grant integration order, does not change action registry semantics, and does not replace per-item QA gates.

Included: all `ANALYZED` non-duplicate candidates plus already-verified `run_front_airborne_reach` as the currently integrated bridge pose. Excluded: `fly_front_hover_ready` / WJFA-10 because the tracker marks it `DUPLICATE`.

## Browser Play Contract

The browser Play demo must keep dynamically cycling every pose in the generated library while the avatar moves. Do not narrow Play to the curated clips below. The clips are labels and suggested runtime groupings for future action/showcase surfaces; the baseline Play contract remains a moving library-driven pose reel that discovers poses from the current library.

Recommended behavior:

- Play mode: continue cycling all library poses, including baseline, verified, and future accepted poses.
- Showcase mode: may offer named clips below, but only as optional filters or scripted reels.
- Action mode: may expose selected coherent clips as user-facing actions after integration and QA.
- Showcase-only poses: may appear in Play and curated reels but should not be selected by ordinary locomotion/action state without explicit runtime support.

## Ground Movement

Purpose: grounded locomotion, acceleration, charge, landing, and recovery. These poses should be the first movement family after baseline walking because they extend existing `walk_front_left` / `walk_front_right` without requiring full flight semantics.

Recommended transition order:

1. `front_idle`
2. `walk_front_right`
3. `walk_front_right_lift`
4. `walk_front_left`
5. `front_run_charge_right_plant`
6. `run_front_airborne_reach`
7. `run_front_airborne_drive`
8. `front_crouch_landing_staff_plant`
9. `front_crouch_guard`
10. `front_idle`

Exposure:

| Semantic ID | Candidate | Recommendation | Notes |
|---|---|---|---|
| `walk_front_right_lift` | WJP2-08 | Action: walking, if accepted | Use as a passing/lift sample, not a gesture. Watch centered staff/hand overlap. |
| `front_run_charge_right_plant` | WJFA-11 | Action: charge/run, after fit approval | Strong acceleration pose, but high width/fit risk. |
| `run_front_airborne_reach` | WJP2-01 | Action: run/dash bridge | Already verified; use as the safest airborne run bridge. |
| `run_front_airborne_drive` | WJP2-02 | Showcase-first, then action if loop reads cleanly | Pairs with WJP2-01 by torso/arm phase, but not a true alternating-foot run cycle. |
| `front_crouch_landing_staff_plant` | WJFA-12 | Showcase-only until contact metadata exists | Needs hand-contact versus foot-contact handling and major fit work. |
| `front_crouch_guard` | WJP2-03 | Action: guard/ready only after fit approval | Useful low stance; scale change risk is high. |

## Flight Cycle

Purpose: a coherent flight reel that separates hover, flap, bank, glide, and airborne action. Keep ordinary walking/running separate from this family because roots, foot contacts, and projected ground semantics differ.

Recommended transition order:

1. `front_idle`
2. `fly_front_hover_neutral`
3. `fly_front_knee_up`
4. `fly_front_wings_up`
5. `fly_front_wings_down`
6. `fly_front_hover_neutral`
7. `fly_southwest_banked_staff`
8. `fly_southeast_banked_staff`
9. `fly_southeast_forward_glide`
10. `fly_southeast_staff_forward`
11. `fly_southeast_banked_staff`
12. `fly_front_hover_neutral`
13. `front_crouch_landing_staff_plant`
14. `front_idle`

Exposure:

| Semantic ID | Candidate | Recommendation | Notes |
|---|---|---|---|
| `fly_front_hover_neutral` | WJFA-01 | Action: hover/fly idle | Canonical hover base; duplicate WJFA-10 should stay excluded. |
| `fly_front_knee_up` | WJFA-02 | Action: fly cycle | Keep metadata clearly flying so it is not mistaken for walking. |
| `fly_front_wings_up` | WJFA-03 | Action: fly cycle | Upstroke sample; crop/scale must protect tall wings. |
| `fly_front_wings_down` | WJFA-04 | Action: fly cycle | Downstroke sample; low wings may collide visually with ground/baseline. |
| `fly_southwest_banked_staff` | WJFA-06 | Action: bank/turn if fit passes | Good left-bank transition; watch staff-side popping. |
| `fly_southeast_banked_staff` | WJFA-07 | Action: bank/turn if fit passes | Good right-bank transition; watch staff lower crop. |
| `fly_southeast_forward_glide` | WJFA-05 | Action: forward flight, high priority | Best forward glide expansion beyond hover. |
| `fly_southeast_staff_forward` | WJFA-09 | Showcase-first | Related to WJFA-05; accept only if staff-forward variant adds clear value. |
| `fly_southeast_cheer` | WJFA-08 | Showcase-only or airborne reaction | Do not select for ordinary flight; use as a midair celebration beat. |
| `front_airborne_fall_back_staff` | WJFA-14 | Showcase-only until airborne/fall semantics exist | Needs non-contact foot semantics and explicit fall transition. |

## Reaction And Celebration

Purpose: visible emotional punctuation: jump, cheer, victory, impact recovery. These are good for demos and scripted moments, but many should not be ordinary autonomous states until baseline/root and contact semantics are reviewed.

Recommended transition order:

1. `front_idle`
2. `front_reaction_jump_fist_staff`
3. `front_celebrate_jump_staff_up`
4. `front_celebrate_wings_staff_up`
5. `front_victory_cast`
6. `front_crouch_reaction_staff_planted`
7. `front_kneel_staff_brace`
8. `front_idle`

Exposure:

| Semantic ID | Candidate | Recommendation | Notes |
|---|---|---|---|
| `front_reaction_jump_fist_staff` | WJP2-04 | Showcase-only first | Airborne root/feet risk; useful as a punchy reaction frame. |
| `front_celebrate_jump_staff_up` | WJFA-18 | Showcase-only first | Airborne celebration; needs non-contact foot handling. |
| `front_celebrate_wings_staff_up` | WJFA-15 | Action: celebrate, after near-fit validation | Strongest grounded celebration candidate in the batch. |
| `front_victory_cast` | WJP2-10 | Action: victory/reaction if distinct from `magic_cast` | Runtime semantics must keep it from being a duplicate cast. |
| `front_crouch_reaction_staff_planted` | WJP2-09 | Showcase-first, possible reaction action | Large vertical posture change; root/baseline lock required. |
| `front_kneel_staff_brace` | WJP2-05 | Showcase-first, possible brace/reaction action | Low-body-height transitions may snap; use as recovery/impact beat. |

## Staff Combat

Purpose: staff-oriented guard, block, thrust, flourish, and cast variants. These should be evaluated as a staff channel, not just body poses, because several carry wide or crossing staff silhouettes that can double during blends.

Recommended transition order:

1. `front_idle`
2. `front_staff_guard_windup`
3. `front_staff_guard_low`
4. `front_staff_block_horizontal`
5. `front_magic_staff_thrust`
6. `magic_cast`
7. `front_staff_spin_flourish`
8. `front_staff_guard_low`
9. `front_idle`

Exposure:

| Semantic ID | Candidate | Recommendation | Notes |
|---|---|---|---|
| `front_staff_guard_windup` | WJP2-06 | Action: guard/cast windup | Good entry into `magic_cast`; watch diagonal staff double-artifacts. |
| `front_staff_guard_low` | WJP2-07 | Action: guard hold | Strong low guard, but staff crosses face/chest. |
| `front_staff_block_horizontal` | WJFA-16 | Action: block/guard after staff-end metadata | Horizontal staff needs more than one staff-tip assumption. |
| `front_magic_staff_thrust` | WJFA-13 | Showcase-first or cast variant | High fit risk; spark/staff may belong in effect metadata. |
| `front_staff_spin_flourish` | WJFA-20 | Showcase-only first | Motion arc likely belongs to effect layer rather than stable body silhouette. |

## Gestures

Purpose: conversational, social, and instruction-like gestures. These are the best candidates for direct action exposure because they are mostly front-facing and semantically crisp.

Recommended transition order:

1. `front_idle`
2. `explaining`
3. `front_point_direct_staff_held`
4. `front_shush_secret_staff_held`
5. `front_point_direct_staff_held`
6. `explaining`
7. `front_idle`

Exposure:

| Semantic ID | Candidate | Recommendation | Notes |
|---|---|---|---|
| `front_point_direct_staff_held` | WJFA-17 | Action: pointing/explaining | Low fit risk; clean semantic distinction from `explaining`. |
| `front_shush_secret_staff_held` | WJFA-19 | Action: shush/secret/thinking if mouth masking exists | Finger-to-mouth conflicts with mouth/speech overlays. |

## Showcase Reel Order

For a curated, non-production showcase that touches every non-duplicate candidate once, use this order:

1. `front_idle`
2. `walk_front_right`
3. `walk_front_right_lift`
4. `walk_front_left`
5. `front_run_charge_right_plant`
6. `run_front_airborne_reach`
7. `run_front_airborne_drive`
8. `front_crouch_landing_staff_plant`
9. `front_crouch_guard`
10. `fly_front_hover_neutral`
11. `fly_front_knee_up`
12. `fly_front_wings_up`
13. `fly_front_wings_down`
14. `fly_southwest_banked_staff`
15. `fly_southeast_banked_staff`
16. `fly_southeast_forward_glide`
17. `fly_southeast_staff_forward`
18. `fly_southeast_cheer`
19. `front_airborne_fall_back_staff`
20. `front_crouch_landing_staff_plant`
21. `front_reaction_jump_fist_staff`
22. `front_celebrate_jump_staff_up`
23. `front_celebrate_wings_staff_up`
24. `front_victory_cast`
25. `front_crouch_reaction_staff_planted`
26. `front_kneel_staff_brace`
27. `front_staff_guard_windup`
28. `front_staff_guard_low`
29. `front_staff_block_horizontal`
30. `front_magic_staff_thrust`
31. `front_staff_spin_flourish`
32. `explaining`
33. `front_point_direct_staff_held`
34. `front_shush_secret_staff_held`
35. `front_idle`

## Exposure Summary

Recommended action candidates after integration and QA:

- Movement: `walk_front_right_lift`, `front_run_charge_right_plant`, `run_front_airborne_reach`, possibly `run_front_airborne_drive`.
- Flight: `fly_front_hover_neutral`, `fly_front_knee_up`, `fly_front_wings_up`, `fly_front_wings_down`, `fly_southwest_banked_staff`, `fly_southeast_banked_staff`, `fly_southeast_forward_glide`.
- Reactions: `front_celebrate_wings_staff_up`, possibly `front_victory_cast`.
- Staff: `front_staff_guard_windup`, `front_staff_guard_low`, `front_staff_block_horizontal` after staff-end metadata.
- Gestures: `front_point_direct_staff_held`, `front_shush_secret_staff_held` after mouth-overlay masking.

Recommended showcase-only until further semantics/metadata:

- `front_crouch_landing_staff_plant`
- `front_crouch_guard`
- `fly_southeast_staff_forward`
- `fly_southeast_cheer`
- `front_airborne_fall_back_staff`
- `front_reaction_jump_fist_staff`
- `front_celebrate_jump_staff_up`
- `front_crouch_reaction_staff_planted`
- `front_kneel_staff_brace`
- `front_magic_staff_thrust`
- `front_staff_spin_flourish`

## Risks

- Fit policy risk: many candidates exceed the canonical `72 x 96` frame before normalization. Any runtime grouping should wait for integration evidence, not assume source PNGs will fit unchanged.
- Contact semantics risk: airborne, hover, fall, jump, crouch, kneel, and landing poses need explicit contact/non-contact handling so foot/root QA does not force false baseline contacts.
- Staff metadata risk: horizontal, thrust, spin, and flourish poses need staff-end or staff-region metadata; a single `staff_tip` default is not enough for all combat poses.
- Overlay conflict risk: `front_shush_secret_staff_held` and several staff-crossing poses can collide with mouth, speech, face, and staff overlays.
- Looping risk: `run_front_airborne_reach` and `run_front_airborne_drive` are not a complete reciprocal-foot run cycle; use them as dash/airborne beats unless QA proves the loop.
- Demo contract risk: curated clips must not replace the browser Play behavior that cycles every generated library pose while moving.
