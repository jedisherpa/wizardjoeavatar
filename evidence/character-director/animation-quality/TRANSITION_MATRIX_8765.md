# Python 8765 Transition Matrix Verification

- generated_at: `2026-07-16T17:00:34.990693+00:00`
- branch: `codex/character-director`
- commit: `293a2d84d3376eca3084eb0db9b0cd04fee42f08`
- scenarios: `32`
- passed: `32`
- with issues: `0`

## Scenario Summary

| Scenario | Passed | Boundary Root | Boundary Scale | Max Churn | Issues |
|---|---:|---:|---:|---:|---|
| idle_to_walk | yes | 0.000 | 0.000000 | 0.174 |  |
| walk_to_idle | yes | 0.000 | 0.000000 | 0.115 |  |
| walk_to_turn | yes | 0.000 | 0.000000 | 0.115 |  |
| turn_to_walk | yes | 0.000 | 0.000000 | 0.181 |  |
| front_to_diagonal | yes | 0.000 | 0.000000 | 0.000 |  |
| diagonal_to_side | yes | 0.000 | 0.000000 | 0.177 |  |
| side_to_back | yes | 0.000 | 0.000000 | 0.185 |  |
| forward_to_backward | yes | 0.000 | 0.000000 | 0.248 |  |
| clockwise_circle_reversal | yes | 0.000 | 0.000000 | 0.193 |  |
| counterclockwise_circle_reversal | yes | 0.000 | 0.000000 | 0.203 |  |
| figure_eight_start | yes | 0.000 | 0.000000 | 0.196 |  |
| walk_to_speak | yes | 0.000 | 0.000000 | 0.115 |  |
| speak_to_walk | yes | 0.000 | 0.000000 | 0.174 |  |
| idle_to_explain | yes | 0.000 | 0.000000 | 0.185 |  |
| idle_to_dash | yes | 0.000 | 0.000000 | 0.182 |  |
| dash_to_idle | yes | 0.000 | 0.000000 | 0.186 |  |
| explain_to_walk | yes | 0.000 | 0.000000 | 0.185 |  |
| walk_to_point | yes | 0.000 | 0.000000 | 0.115 |  |
| point_to_idle | yes | 0.000 | 0.000000 | 0.196 |  |
| idle_to_think | yes | 0.000 | 0.000000 | 0.000 |  |
| think_to_speak | yes | 0.000 | 0.000000 | 0.002 |  |
| idle_to_cast | yes | 0.000 | 0.000000 | 0.203 |  |
| cast_to_idle | yes | 0.000 | 0.000000 | 0.203 |  |
| reaction_to_previous | yes | 0.000 | 0.000000 | 0.203 |  |
| expression_during_locomotion | yes | 0.000 | 0.000000 | 0.115 |  |
| blink_during_speech | yes | 0.000 | 0.000000 | 0.001 |  |
| mouth_closure_after_speech | yes | 0.000 | 0.000000 | 0.002 |  |
| staff_during_turning | yes | 0.000 | 0.000000 | 0.203 |  |
| staff_during_gesture | yes | 0.000 | 0.000000 | 0.196 |  |
| depth_scaling_forward | yes | 0.000 | 0.000000 | 0.217 |  |
| root_position_view_change | yes | 0.000 | 0.000000 | 0.193 |  |
| animation_interruption_cancel | yes | 0.000 | 0.000000 | 0.203 |  |

