# Python 8765 Transition Matrix Verification

- generated_at: `2026-07-15T17:50:54.400090+00:00`
- branch: `codex/persona-serena-quill`
- commit: `0a7f379b1d1e58541b7d8da53812cf7b3e0a9f03`
- scenarios: `32`
- passed: `32`
- with issues: `0`

## Scenario Summary

| Scenario | Passed | Boundary Root | Boundary Scale | Max Churn | Issues |
|---|---:|---:|---:|---:|---|
| idle_to_walk | yes | 0.072 | 0.000000 | 0.174 |  |
| walk_to_idle | yes | 0.000 | 0.000000 | 0.115 |  |
| walk_to_turn | yes | 0.900 | 0.000000 | 0.115 |  |
| turn_to_walk | yes | 0.072 | 0.000000 | 0.181 |  |
| front_to_diagonal | yes | 0.000 | 0.000000 | 0.178 |  |
| diagonal_to_side | yes | 0.000 | 0.000000 | 0.173 |  |
| side_to_back | yes | 0.000 | 0.000000 | 0.185 |  |
| forward_to_backward | yes | 0.237 | 0.000000 | 0.232 |  |
| clockwise_circle_reversal | yes | 0.254 | 0.000000 | 0.193 |  |
| counterclockwise_circle_reversal | yes | 0.254 | 0.000000 | 0.178 |  |
| figure_eight_start | yes | 0.018 | 0.000000 | 0.182 |  |
| walk_to_speak | yes | 0.900 | 0.000000 | 0.117 |  |
| speak_to_walk | yes | 0.072 | 0.000000 | 0.171 |  |
| idle_to_explain | yes | 0.000 | 0.000000 | 0.186 |  |
| idle_to_dash | yes | 0.000 | 0.000000 | 0.189 |  |
| dash_to_idle | yes | 0.000 | 0.000000 | 0.189 |  |
| explain_to_walk | yes | 0.072 | 0.000000 | 0.184 |  |
| walk_to_point | yes | 0.900 | 0.000000 | 0.115 |  |
| point_to_idle | yes | 0.000 | 0.000000 | 0.186 |  |
| idle_to_think | yes | 0.000 | 0.000000 | 0.000 |  |
| think_to_speak | yes | 0.000 | 0.000000 | 0.003 |  |
| idle_to_cast | yes | 0.000 | 0.000000 | 0.183 |  |
| cast_to_idle | yes | 0.000 | 0.000000 | 0.183 |  |
| reaction_to_previous | yes | 0.000 | 0.000000 | 0.001 |  |
| expression_during_locomotion | yes | 0.900 | 0.000000 | 0.115 |  |
| blink_during_speech | yes | 0.000 | 0.000000 | 0.003 |  |
| mouth_closure_after_speech | yes | 0.000 | 0.000000 | 0.003 |  |
| staff_during_turning | yes | 0.000 | 0.000000 | 0.001 |  |
| staff_during_gesture | yes | 0.000 | 0.000000 | 0.000 |  |
| depth_scaling_forward | yes | 0.021 | 0.000000 | 0.217 |  |
| root_position_view_change | yes | 0.000 | 0.000000 | 0.193 |  |
| animation_interruption_cancel | yes | 0.000 | 0.000000 | 0.183 |  |

