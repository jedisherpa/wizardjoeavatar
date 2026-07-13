# Python 8765 Transition Matrix Verification

- generated_at: `2026-07-13T05:28:55.645109+00:00`
- branch: `codex/build-repeatable-avatar-animation`
- commit: `1b63db9ca24c4e8baae3ef10bc68935dbbcfefe1`
- scenarios: `32`
- passed: `32`
- with issues: `0`

## Scenario Summary

| Scenario | Passed | Boundary Root | Boundary Scale | Max Churn | Issues |
|---|---:|---:|---:|---:|---|
| idle_to_walk | yes | 0.102 | 0.000000 | 0.146 |  |
| walk_to_idle | yes | 0.000 | 0.000000 | 0.115 |  |
| walk_to_turn | yes | 1.125 | 0.000000 | 0.115 |  |
| turn_to_walk | yes | 0.102 | 0.000000 | 0.179 |  |
| front_to_diagonal | yes | 0.000 | 0.000000 | 0.045 |  |
| diagonal_to_side | yes | 0.000 | 0.000000 | 0.044 |  |
| side_to_back | yes | 0.000 | 0.000000 | 0.047 |  |
| forward_to_backward | yes | 0.293 | 0.000000 | 0.232 |  |
| clockwise_circle_reversal | yes | 0.314 | 0.000000 | 0.193 |  |
| counterclockwise_circle_reversal | yes | 0.314 | 0.000000 | 0.176 |  |
| figure_eight_start | yes | 0.031 | 0.000000 | 0.177 |  |
| walk_to_speak | yes | 1.125 | 0.000000 | 0.115 |  |
| speak_to_walk | yes | 0.102 | 0.000000 | 0.146 |  |
| idle_to_explain | yes | 0.000 | 0.000000 | 0.046 |  |
| idle_to_dash | yes | 0.000 | 0.000000 | 0.048 |  |
| dash_to_idle | yes | 0.000 | 0.000000 | 0.048 |  |
| explain_to_walk | yes | 0.102 | 0.000000 | 0.154 |  |
| walk_to_point | yes | 1.125 | 0.000000 | 0.115 |  |
| point_to_idle | yes | 0.000 | 0.000000 | 0.046 |  |
| idle_to_think | yes | 0.000 | 0.000000 | 0.000 |  |
| think_to_speak | yes | 0.000 | 0.000000 | 0.003 |  |
| idle_to_cast | yes | 0.000 | 0.000000 | 0.047 |  |
| cast_to_idle | yes | 0.000 | 0.000000 | 0.047 |  |
| reaction_to_previous | yes | 0.000 | 0.000000 | 0.001 |  |
| expression_during_locomotion | yes | 1.125 | 0.000000 | 0.115 |  |
| blink_during_speech | yes | 0.000 | 0.000000 | 0.003 |  |
| mouth_closure_after_speech | yes | 0.000 | 0.000000 | 0.003 |  |
| staff_during_turning | yes | 0.000 | 0.000000 | 0.001 |  |
| staff_during_gesture | yes | 0.000 | 0.000000 | 0.000 |  |
| depth_scaling_forward | yes | 0.029 | 0.000000 | 0.217 |  |
| root_position_view_change | yes | 0.000 | 0.000000 | 0.048 |  |
| animation_interruption_cancel | yes | 0.000 | 0.000000 | 0.047 |  |

